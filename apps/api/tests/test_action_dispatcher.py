from codex3d_api import Codex3DApiService
from codex3d_protocol import (
    Action,
    ActionResult,
    ActionStatus,
    ActionType,
    ConnectorCapability,
    ConnectorRegistration,
    ConnectorStatus,
)


def _action() -> Action:
    return Action(
        type=ActionType.CREATE_OBJECT,
        parameters={"primitive": "cube", "name": "C3D_TestCube"},
    )


def _handler(action: Action) -> ActionResult:
    return ActionResult(
        action_id=action.id,
        status=ActionStatus.SUCCEEDED,
        created_object_ids=[action.parameters["name"]],
    )


def test_dispatcher_rejects_unknown_connector() -> None:
    service = Codex3DApiService()
    result = service.action_dispatcher.dispatch("connector_missing", _action())

    assert result.status is ActionStatus.FAILED
    assert result.error is not None
    assert result.error.code.value == "object_not_found"


def test_dispatcher_rejects_missing_execute_action_capability() -> None:
    service = Codex3DApiService()
    connector = service.register_connector(
        ConnectorRegistration(
            capabilities=[ConnectorCapability.PING],
            status=ConnectorStatus.ONLINE,
        )
    )

    result = service.action_dispatcher.dispatch(connector.id, _action())

    assert result.status is ActionStatus.FAILED
    assert "execute_action" in result.error.message


def test_dispatcher_rejects_offline_connector() -> None:
    service = Codex3DApiService()
    connector = service.register_connector(
        ConnectorRegistration(
            capabilities=[ConnectorCapability.EXECUTE_ACTION],
            status=ConnectorStatus.OFFLINE,
        )
    )

    result = service.action_dispatcher.dispatch(connector.id, _action())

    assert result.status is ActionStatus.FAILED
    assert "not online" in result.error.message


def test_dispatcher_rejects_unbound_handler() -> None:
    service = Codex3DApiService()
    connector = service.register_connector(
        ConnectorRegistration(
            capabilities=[ConnectorCapability.EXECUTE_ACTION],
            status=ConnectorStatus.ONLINE,
        )
    )

    result = service.action_dispatcher.dispatch(connector.id, _action())

    assert result.status is ActionStatus.FAILED
    assert "no action handler" in result.error.message


def test_dispatcher_advances_action_status_to_success() -> None:
    service = Codex3DApiService()
    connector = service.register_connector(
        ConnectorRegistration(
            capabilities=[ConnectorCapability.EXECUTE_ACTION],
            status=ConnectorStatus.ONLINE,
        )
    )
    service.bind_connector_action_handler(connector.id, _handler)
    action = _action()

    assert action.status is ActionStatus.PLANNED
    result = service.action_dispatcher.dispatch(connector.id, action)

    assert result.status is ActionStatus.SUCCEEDED
    assert action.status is ActionStatus.SUCCEEDED


def test_dispatch_many_fail_fast_records_unexecuted_count() -> None:
    service = Codex3DApiService()
    connector = service.register_connector(
        ConnectorRegistration(
            capabilities=[ConnectorCapability.EXECUTE_ACTION],
            status=ConnectorStatus.ONLINE,
        )
    )

    def failing_handler(action: Action) -> ActionResult:
        return ActionResult(action_id=action.id, status=ActionStatus.FAILED)

    service.bind_connector_action_handler(connector.id, failing_handler)
    actions = [_action(), _action(), _action()]

    results = service.action_dispatcher.dispatch_many(connector.id, actions)

    assert len(results) == 1
    assert results[0].status is ActionStatus.FAILED
    assert results[0].metadata["fail_fast"] is True
    assert results[0].metadata["unexecuted_count"] == 2
    assert actions[1].status is ActionStatus.PLANNED
