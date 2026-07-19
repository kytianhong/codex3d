from __future__ import annotations

import hmac
import json
import socket
import threading
from typing import Any

from .bridge_runtime import BlenderBridgeRuntime
from .protocol_compat import (
    BRIDGE_PROTOCOL_VERSION,
    BridgeMessageType,
    BridgeRequest,
    BridgeResponse,
    ErrorCode,
    ProtocolError,
    from_dict,
    to_json,
)


LOOPBACK_HOST = "127.0.0.1"
DEFAULT_PORT = 9876
MAX_FRAME_BYTES = 2 * 1024 * 1024


class BridgeServerError(RuntimeError):
    def __init__(self, error: ProtocolError) -> None:
        super().__init__(error.message)
        self.error = error


class BridgeServer:
    def __init__(
        self,
        runtime: BlenderBridgeRuntime,
        *,
        request_timeout: float = 60.0,
        join_timeout: float = 2.0,
        max_frame_bytes: int = MAX_FRAME_BYTES,
    ) -> None:
        self.runtime = runtime
        self.request_timeout = request_timeout
        self.join_timeout = join_timeout
        self.max_frame_bytes = max_frame_bytes
        self.last_error = ""
        self._token = ""
        self._listener: socket.socket | None = None
        self._accept_thread: threading.Thread | None = None
        self._client_threads: set[threading.Thread] = set()
        self._client_sockets: set[socket.socket] = set()
        self._lock = threading.Lock()
        self._running = threading.Event()
        self._bound_address: tuple[str, int] | None = None

    @property
    def is_running(self) -> bool:
        return self._running.is_set()

    @property
    def bound_address(self) -> tuple[str, int] | None:
        return self._bound_address

    def start(self, host: str = LOOPBACK_HOST, port: int = DEFAULT_PORT, token: str = "") -> tuple[str, int]:
        if host != LOOPBACK_HOST:
            raise BridgeServerError(
                ProtocolError(
                    code=ErrorCode.UNSUPPORTED_OPERATION,
                    message="Codex3D bridge only permits 127.0.0.1.",
                    source="codex3d_blender_connector.bridge_server",
                )
            )
        if not token:
            raise BridgeServerError(
                ProtocolError(
                    code=ErrorCode.AUTHENTICATION_FAILED,
                    message="A non-empty bridge token is required.",
                    source="codex3d_blender_connector.bridge_server",
                )
            )
        if self.is_running and self._bound_address is not None:
            return self._bound_address
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind((host, port))
            listener.listen()
            listener.settimeout(0.2)
        except OSError as exc:
            listener.close()
            self.last_error = f"Could not bind {host}:{port}: {exc}"
            raise BridgeServerError(
                ProtocolError(
                    code=ErrorCode.CONNECTOR_OFFLINE,
                    message=self.last_error,
                    source="codex3d_blender_connector.bridge_server",
                    details={"host": host, "port": port},
                )
            ) from exc
        self._listener = listener
        self._token = token
        self._bound_address = listener.getsockname()
        self.runtime.resume()
        self._running.set()
        self._accept_thread = threading.Thread(target=self._accept_loop, name="Codex3DBridgeAccept", daemon=True)
        self._accept_thread.start()
        return self._bound_address

    def stop(self) -> None:
        if not self.is_running and self._listener is None:
            return
        self._running.clear()
        listener, self._listener = self._listener, None
        if listener is not None:
            try:
                listener.close()
            except OSError:
                pass
        self.runtime.shutdown()
        with self._lock:
            sockets = list(self._client_sockets)
            threads = list(self._client_threads)
        for thread in threads:
            if thread is not threading.current_thread():
                thread.join(min(0.1, self.join_timeout))
        for client in sockets:
            try:
                client.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                client.close()
            except OSError:
                pass
        if self._accept_thread is not None and self._accept_thread is not threading.current_thread():
            self._accept_thread.join(self.join_timeout)
        for thread in threads:
            if thread is not threading.current_thread() and thread.is_alive():
                thread.join(self.join_timeout)
        self._accept_thread = None
        self._bound_address = None
        self._token = ""

    def _accept_loop(self) -> None:
        while self.is_running:
            listener = self._listener
            if listener is None:
                break
            try:
                client, _ = listener.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            thread = threading.Thread(
                target=self._handle_client,
                args=(client,),
                name="Codex3DBridgeClient",
                daemon=True,
            )
            with self._lock:
                self._client_sockets.add(client)
                self._client_threads.add(thread)
            thread.start()

    def _handle_client(self, client: socket.socket) -> None:
        try:
            client.settimeout(self.request_timeout + 1.0)
            reader = client.makefile("rb")
            while self.is_running:
                frame = reader.readline(self.max_frame_bytes + 2)
                if not frame:
                    break
                if len(frame) > self.max_frame_bytes or not frame.endswith(b"\n"):
                    self._send(client, self._error_response("", "error", ErrorCode.FRAME_TOO_LARGE, "Bridge frame exceeds 2 MiB."))
                    break
                response = self._process_frame(frame[:-1])
                self._send(client, response)
        except (OSError, TimeoutError):
            pass
        finally:
            try:
                client.close()
            except OSError:
                pass
            with self._lock:
                self._client_sockets.discard(client)
                self._client_threads.discard(threading.current_thread())

    def _process_frame(self, frame: bytes) -> BridgeResponse:
        try:
            data = json.loads(frame.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return self._error_response("", "error", ErrorCode.INVALID_SCHEMA, "Malformed JSON request.")
        if not isinstance(data, dict):
            return self._error_response("", "error", ErrorCode.INVALID_SCHEMA, "Bridge request must be a JSON object.")
        request_id = str(data.get("request_id", ""))
        raw_type = str(data.get("type", "error"))
        if data.get("protocol_version") != BRIDGE_PROTOCOL_VERSION:
            return self._error_response(request_id, raw_type, ErrorCode.INVALID_SCHEMA, "Unsupported bridge protocol version.")
        supplied_token = data.get("auth_token")
        if not isinstance(supplied_token, str) or not hmac.compare_digest(supplied_token, self._token):
            return self._error_response(request_id, raw_type, ErrorCode.AUTHENTICATION_FAILED, "Bridge authentication failed.")
        try:
            message_type = BridgeMessageType(raw_type)
        except ValueError:
            return self._error_response(request_id, raw_type, ErrorCode.UNSUPPORTED_OPERATION, "Unsupported bridge message type.")
        try:
            request = from_dict(BridgeRequest, {**data, "type": message_type.value})
        except (TypeError, ValueError):
            return self._error_response(request_id, raw_type, ErrorCode.INVALID_SCHEMA, "Invalid bridge request schema.")
        pending = self.runtime.enqueue(request, self.request_timeout)
        if not pending.event.wait(self.request_timeout):
            return self._error_response(request_id, raw_type, ErrorCode.REQUEST_TIMEOUT, "Bridge request timed out waiting for Blender.")
        return pending.response or self._error_response(request_id, raw_type, ErrorCode.ACTION_FAILED, "Bridge produced no response.")

    def _send(self, client: socket.socket, response: BridgeResponse) -> None:
        client.sendall(to_json(response).encode("utf-8") + b"\n")

    def _error_response(self, request_id: str, raw_type: str, code: ErrorCode, message: str) -> BridgeResponse:
        safe_type = raw_type if raw_type else "error"
        return BridgeResponse(
            request_id=request_id,
            type=f"{safe_type}_result",
            ok=False,
            error=ProtocolError(code=code, message=message, source="codex3d_blender_connector.bridge_server"),
        )
