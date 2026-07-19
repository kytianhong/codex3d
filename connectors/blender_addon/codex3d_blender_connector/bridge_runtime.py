from __future__ import annotations

import queue
import threading
from typing import Any

from .action_executor import BlenderActionExecutor
from .protocol_compat import (
    Action,
    ActionStatus,
    BridgeMessageType,
    BridgeRequest,
    BridgeResponse,
    ErrorCode,
    ProtocolError,
    from_dict,
    to_dict,
    utc_now_iso,
)
from .request_queue import PendingBridgeRequest


class BlenderBridgeRuntime:
    def __init__(
        self,
        executor: BlenderActionExecutor,
        *,
        connector_id: str = "codex3d_blender",
        connector_version: str = "0.1.0",
        blender_version: str = "unknown",
        timer_interval: float = 0.1,
        max_requests_per_tick: int = 4,
    ) -> None:
        if max_requests_per_tick < 1:
            raise ValueError("max_requests_per_tick must be positive")
        self.executor = executor
        self.connector_id = connector_id
        self.connector_version = connector_version
        self.blender_version = blender_version
        self.timer_interval = timer_interval
        self.max_requests_per_tick = max_requests_per_tick
        self.last_error = ""
        self.last_request_summary = ""
        self.last_execution_thread_id: int | None = None
        self._queue: queue.Queue[PendingBridgeRequest] = queue.Queue()
        self._accepting = True
        self._timer_registered = False
        self._timer_owner: Any | None = None

    @property
    def pending_count(self) -> int:
        return self._queue.qsize()

    @property
    def timer_registered(self) -> bool:
        return self._timer_registered

    def enqueue(self, request: BridgeRequest, timeout: float) -> PendingBridgeRequest:
        pending = PendingBridgeRequest(request=request, timeout=timeout)
        if not self._accepting:
            pending.complete(self._error_response(request, ErrorCode.BRIDGE_SHUTDOWN, "Bridge is shutting down."))
            return pending
        self._queue.put(pending)
        return pending

    def pump_once(self, max_requests: int | None = None) -> int:
        limit = self.max_requests_per_tick if max_requests is None else min(max_requests, self.max_requests_per_tick)
        processed = 0
        self.last_execution_thread_id = threading.get_ident()
        while processed < limit:
            try:
                pending = self._queue.get_nowait()
            except queue.Empty:
                break
            if pending.event.is_set():
                continue
            try:
                pending.complete(self.execute_request(pending.request))
            except Exception as exc:  # pragma: no cover - defensive Blender boundary
                self.last_error = str(exc)
                pending.complete(
                    self._error_response(
                        pending.request,
                        ErrorCode.ACTION_FAILED,
                        f"Bridge request failed: {exc}",
                    )
                )
            processed += 1
        return processed

    def execute_request(self, request: BridgeRequest) -> BridgeResponse:
        self.last_request_summary = f"{request.type.value} ({request.request_id})"
        if request.type is BridgeMessageType.HELLO:
            payload = {
                "connector_id": self.connector_id,
                "connector_version": self.connector_version,
                "blender_version": self.blender_version,
                "backend": self.executor.backend.backend_name,
            }
            return self._ok_response(request, payload)
        if request.type is BridgeMessageType.PING:
            return self._ok_response(request, {"message": "pong", "connector_id": self.connector_id})
        if request.type is BridgeMessageType.INSPECT_SCENE:
            inspection = self.executor.backend.inspect(connector_id=self.connector_id)
            return self._ok_response(request, {"inspection": to_dict(inspection)})
        if request.type is BridgeMessageType.EXECUTE_ACTION:
            raw_action = request.payload.get("action", {})
            action = raw_action if isinstance(raw_action, Action) else from_dict(Action, raw_action)
            result = self.executor.execute(action)
            return self._ok_response(
                request,
                {"result": to_dict(result)},
                ok=result.status is ActionStatus.SUCCEEDED,
                error=result.error,
            )
        if request.type is BridgeMessageType.EXECUTE_ACTION_BATCH:
            return self._execute_batch(request)
        return self._error_response(request, ErrorCode.UNSUPPORTED_OPERATION, "Unsupported bridge message type.")

    def start_timer(self, bpy_module: Any) -> None:
        if self._timer_registered:
            return
        timers = bpy_module.app.timers
        timers.register(self._timer_callback, first_interval=self.timer_interval, persistent=True)
        self._timer_owner = timers
        self._timer_registered = True

    def stop_timer(self) -> None:
        if not self._timer_registered:
            return
        timers = self._timer_owner
        try:
            if timers is not None and hasattr(timers, "is_registered") and timers.is_registered(self._timer_callback):
                timers.unregister(self._timer_callback)
        except (ReferenceError, RuntimeError, ValueError):
            pass
        self._timer_owner = None
        self._timer_registered = False

    def shutdown(self, message: str = "Bridge server stopped.") -> None:
        self._accepting = False
        while True:
            try:
                pending = self._queue.get_nowait()
            except queue.Empty:
                break
            pending.complete(self._error_response(pending.request, ErrorCode.BRIDGE_SHUTDOWN, message))

    def resume(self) -> None:
        self._accepting = True

    def _timer_callback(self) -> float | None:
        if not self._timer_registered:
            return None
        self.pump_once()
        return self.timer_interval

    def _execute_batch(self, request: BridgeRequest) -> BridgeResponse:
        raw_actions = request.payload.get("actions")
        if not isinstance(raw_actions, list):
            return self._error_response(request, ErrorCode.INVALID_SCHEMA, "payload.actions must be a list.")
        results = []
        failed_count = 0
        for raw_action in raw_actions:
            action = raw_action if isinstance(raw_action, Action) else from_dict(Action, raw_action)
            result = self.executor.execute(action)
            results.append(result)
            if result.status is ActionStatus.FAILED:
                failed_count = 1
                break
        executed_count = len(results)
        unexecuted_count = len(raw_actions) - executed_count
        payload = {
            "results": to_dict(results),
            "executed_count": executed_count,
            "succeeded_count": executed_count - failed_count,
            "failed_count": failed_count,
            "unexecuted_count": unexecuted_count,
        }
        error = results[-1].error if failed_count else None
        return self._ok_response(request, payload, ok=failed_count == 0, error=error)

    def _ok_response(
        self,
        request: BridgeRequest,
        payload: dict[str, Any],
        *,
        ok: bool = True,
        error: ProtocolError | None = None,
    ) -> BridgeResponse:
        return BridgeResponse(
            request_id=request.request_id,
            type=f"{request.type.value}_result",
            ok=ok,
            payload=payload,
            error=error,
        )

    def _error_response(self, request: BridgeRequest, code: ErrorCode, message: str) -> BridgeResponse:
        return BridgeResponse(
            request_id=request.request_id,
            type=f"{request.type.value}_result",
            ok=False,
            completed_at=utc_now_iso(),
            error=ProtocolError(code=code, message=message, source="codex3d_blender_connector.bridge_runtime"),
        )
