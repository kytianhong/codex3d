from codex3d_api.demo_planner import (
    STANDARD_HACKATHON_PROMPT,
    normalize_action_business_fields,
    plan_demo_prompt,
)
from codex3d_protocol import ActionStatus, ActionType


def test_standard_hackathon_prompt_generates_deterministic_plan() -> None:
    first = plan_demo_prompt(STANDARD_HACKATHON_PROMPT)
    second = plan_demo_prompt(STANDARD_HACKATHON_PROMPT)

    assert first.supported is True
    assert all(action.status is ActionStatus.PLANNED for action in first.actions)
    assert normalize_action_business_fields(first.actions) == normalize_action_business_fields(second.actions)


def test_plan_contains_desk_chair_lamp_warm_light_and_materials() -> None:
    plan = plan_demo_prompt("Create a cozy wooden desk scene with a chair, lamp, and warm lighting.")
    names = [
        action.parameters.get("name") or action.parameters.get("target_name")
        for action in plan.actions
    ]
    action_types = [action.type for action in plan.actions]
    material_targets = [
        action.parameters["target_name"]
        for action in plan.actions
        if action.type is ActionType.ASSIGN_MATERIAL
    ]

    assert "C3D_DeskTop" in names
    assert "C3D_ChairSeat" in names
    assert "C3D_LampBase" in names
    assert "C3D_WarmLampLight" in names
    assert action_types.count(ActionType.ASSIGN_MATERIAL) >= 3
    assert {"C3D_Floor", "C3D_DeskTop", "C3D_LampBase"}.issubset(set(material_targets))
