from __future__ import annotations

from collections.abc import Callable

from codex3d_protocol import (
    Action,
    ActionResult,
    ActionStatus,
    ConnectorCapability,
    ConnectorStatus,
    ErrorCode,
    ProtocolError,
)

from .connector_service import ConnectorService
from .store import StoreNotFoundError

ActionHandler = Callable[[Action], ActionResult]


class LocalActionDispatcher:
    def __init__(self, connector_service: ConnectorService) -> None:
        self.connector_service = connector_service
        self._handlers: dict[str, ActionHandler] = {}

    def bind_handler(self, connector_id: str, handler: ActionHandler) -> None:
        self._handlers[connector_id] = handler

    def unbind_handler(self, connector_id: str) -> None:
        self._handlers.pop(connector_id, None)

    def dispatch(self, connector_id: str, action: Action) -> ActionResult:
        preflight = self._preflight(connector_id, action)
        if preflight is not None:
            return preflight

        action.status = ActionStatus.RUNNING
        action.touch()
        result = self._handlers[connector_id](action)
        action.status = (
            ActionStatus.SUCCEEDED
            if result.status is ActionStatus.SUCCEEDED
            else ActionStatus.FAILED
        )
        action.touch()
        return result

    def dispatch_many(self, connector_id: str, actions: list[Action]) -> list[ActionResult]:
        results: list[ActionResult] = []
        for index, action in enumerate(actions):
            result = self.dispatch(connector_id, action)
            results.append(result)
            if result.status is ActionStatus.FAILED:
                result.metadata["fail_fast"] = True
                result.metadata["unexecuted_count"] = len(actions) - index - 1
                break
        return results

    def _preflight(self, connector_id: str, action: Action) -> ActionResult | None:
        try:
            connector = self.connector_service.get_connector(connector_id)
        except StoreNotFoundError:
            return _failed_result(
                action,
                f"connector not found: {connector_id}",
                code=ErrorCode.OBJECT_NOT_FOUND,
                details={"connector_id": connector_id},
            )

        if connector.status is not ConnectorStatus.ONLINE:
            return _failed_result(
                action,
                f"connector is not online: {connector_id}",
                details={"connector_id": connector_id, "status": connector.status.value},
            )

        if ConnectorCapability.EXECUTE_ACTION not in connector.capabilities:
            return _failed_result(
                action,
                f"connector lacks execute_action capability: {connector_id}",
                code=ErrorCode.UNSUPPORTED_OPERATION,
                details={"connector_id": connector_id},
            )

        if connector_id not in self._handlers:
            return _failed_result(
                action,
                f"no action handler bound for connector: {connector_id}",
                code=ErrorCode.UNSUPPORTED_OPERATION,
                details={"connector_id": connector_id},
            )

        return None


def _failed_result(
    action: Action,
    message: str,
    *,
    code: ErrorCode = ErrorCode.ACTION_FAILED,
    details: dict | None = None,
) -> ActionResult:
    action.status = ActionStatus.FAILED
    action.touch()
    return ActionResult(
        action_id=action.id,
        status=ActionStatus.FAILED,
        error=ProtocolError(
            code=code,
            message=message,
            source="codex3d_api.action_dispatcher",
            details=details or {},
        ),
        metadata={"dispatcher": "local"},
    )

