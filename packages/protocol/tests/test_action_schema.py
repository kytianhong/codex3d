from codex3d_protocol import (
    Action,
    ActionResult,
    ActionStatus,
    ActionType,
    ErrorCode,
    ProtocolError,
    ToolCall,
)


def test_action_tool_call_and_success_result() -> None:
    action = Action(
        type=ActionType.CREATE_OBJECT,
        description="Create a small wooden desk.",
        parameters={"semantic_type": "desk", "material": "wood"},
    )
    tool_call = action.add_tool_call(
        ToolCall(
            tool_name="create_box_object",
            arguments={"width": 1.2, "depth": 0.6, "height": 0.75},
        )
    )
    result = ActionResult(
        action_id=action.id,
        status=ActionStatus.SUCCEEDED,
        created_object_ids=["object_desk"],
    )

    assert tool_call.action_id == action.id
    assert action.type is ActionType.CREATE_OBJECT
    assert result.status is ActionStatus.SUCCEEDED
    assert result.created_object_ids == ["object_desk"]


def test_action_result_can_hold_error() -> None:
    error = ProtocolError(
        code=ErrorCode.UNSUPPORTED_OPERATION,
        message="The requested operation is not available yet.",
    )
    result = ActionResult(
        action_id="action_missing",
        status=ActionStatus.FAILED,
        error=error,
    )

    assert result.error is error
    assert result.error.code is ErrorCode.UNSUPPORTED_OPERATION

