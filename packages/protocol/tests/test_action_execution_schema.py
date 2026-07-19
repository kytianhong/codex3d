from codex3d_protocol import (
    Action,
    ActionResult,
    ActionStatus,
    ActionType,
    ConnectorActionRequest,
    ConnectorActionResponse,
    to_dict,
)


def test_connector_action_request_response_serialize() -> None:
    action = Action(
        type=ActionType.CREATE_OBJECT,
        parameters={"primitive": "cube", "name": "C3D_TestCube"},
    )
    request = ConnectorActionRequest(connector_id="connector_fake", action=action)
    response = ConnectorActionResponse(
        connector_id="connector_fake",
        result=ActionResult(
            action_id=action.id,
            status=ActionStatus.SUCCEEDED,
            created_object_ids=["C3D_TestCube"],
        ),
    )

    data = to_dict({"request": request, "response": response})

    assert data["request"]["action"]["type"] == "create_object"
    assert data["response"]["result"]["status"] == "succeeded"
    assert data["response"]["result"]["created_object_ids"] == ["C3D_TestCube"]

