from codex3d_protocol import Action, ActionType, from_dict, to_dict, to_json


def test_creative_action_types_round_trip() -> None:
    for action_type in (
        ActionType.CONFIGURE_SCENE,
        ActionType.CONFIGURE_WORLD,
        ActionType.SET_PARENT,
        ActionType.KEYFRAME_OBJECT,
        ActionType.RENDER_PREVIEW,
        ActionType.SAVE_CHECKPOINT,
    ):
        action = Action(type=action_type, parameters={"purpose": "creative_vertical_slice"})
        restored = from_dict(Action, to_dict(action))

        assert restored.type is action_type
        assert action_type.value in to_json(action)
