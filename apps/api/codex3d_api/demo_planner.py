from __future__ import annotations

from dataclasses import dataclass, field

from codex3d_protocol import Action, ActionStatus, ActionType


STANDARD_HACKATHON_PROMPT = "Create a cozy wooden desk scene with a chair, lamp, and warm lighting."


@dataclass
class DemoPlan:
    prompt: str
    planner: str = "deterministic_demo"
    supported: bool = False
    summary: str = ""
    actions: list[Action] = field(default_factory=list)


def plan_demo_prompt(prompt: str) -> DemoPlan:
    lowered = prompt.lower()
    keywords = {
        "desk": "desk" in lowered or "书桌" in prompt or "桌子" in prompt,
        "cozy": "cozy" in lowered or "温馨" in prompt,
        "wood": "wooden" in lowered or "木质" in prompt or "木头" in prompt,
        "chair": "chair" in lowered or "椅子" in prompt,
        "lamp": "lamp" in lowered or "台灯" in prompt or "灯" in prompt,
        "warm_lighting": "warm lighting" in lowered or "暖光" in prompt or "暖色灯光" in prompt,
    }
    if keywords["desk"] and keywords["chair"] and keywords["lamp"]:
        actions = _standard_scene_actions(include_warm_light=keywords["warm_lighting"])
        return DemoPlan(
            prompt=prompt,
            supported=True,
            summary="Deterministic demo plan: cozy wooden desk scene with chair, lamp, and warm lighting.",
            actions=actions,
        )

    return DemoPlan(
        prompt=prompt,
        supported=False,
        summary="Deterministic demo planner does not support this prompt yet; planned scene inspection only.",
        actions=[
            _action(
                ActionType.INSPECT_SCENE,
                "Inspect current scene because the deterministic demo planner cannot model this prompt.",
                {"reason": "unsupported_prompt"},
            )
        ],
    )


def normalize_action_business_fields(actions: list[Action]) -> list[dict]:
    return [
        {
            "type": action.type.value,
            "description": action.description,
            "parameters": action.parameters,
            "metadata": {
                key: value
                for key, value in action.metadata.items()
                if key in {"planner", "demo", "model_used", "plan_order"}
            },
        }
        for action in actions
    ]


def _standard_scene_actions(*, include_warm_light: bool) -> list[Action]:
    actions: list[Action] = []

    def add(action_type: ActionType, description: str, parameters: dict) -> None:
        actions.append(_action(action_type, description, parameters, plan_order=len(actions) + 1))

    add(
        ActionType.CREATE_OBJECT,
        "Create floor plane.",
        _create("plane", "C3D_Floor", [0.0, 0.0, 0.0], [4.0, 3.0, 0.01], "floor"),
    )
    add(ActionType.ASSIGN_MATERIAL, "Assign matte floor material.", _material("C3D_Floor", "C3D_FloorMat", [0.55, 0.52, 0.46, 1.0], 0.8, 0.0))

    add(ActionType.CREATE_OBJECT, "Create wooden desktop.", _create("cube", "C3D_DeskTop", [0.0, 0.0, 0.75], [1.4, 0.7, 0.08], "desk_top"))
    for name, x, y in [
        ("C3D_DeskLeg_FL", -0.6, 0.28),
        ("C3D_DeskLeg_FR", 0.6, 0.28),
        ("C3D_DeskLeg_BL", -0.6, -0.28),
        ("C3D_DeskLeg_BR", 0.6, -0.28),
    ]:
        add(ActionType.CREATE_OBJECT, f"Create desk leg {name}.", _create("cube", name, [x, y, 0.365], [0.08, 0.08, 0.73], "desk_leg"))
    for target in ["C3D_DeskTop", "C3D_DeskLeg_FL", "C3D_DeskLeg_FR", "C3D_DeskLeg_BL", "C3D_DeskLeg_BR"]:
        add(ActionType.ASSIGN_MATERIAL, f"Assign walnut material to {target}.", _material(target, "C3D_Walnut", [0.30, 0.12, 0.045, 1.0], 0.48, 0.0))

    add(ActionType.CREATE_OBJECT, "Create chair seat.", _create("cube", "C3D_ChairSeat", [0.0, -1.0, 0.45], [0.52, 0.50, 0.07], "chair_seat"))
    add(ActionType.CREATE_OBJECT, "Create chair back.", _create("cube", "C3D_ChairBack", [0.0, -1.22, 0.82], [0.52, 0.08, 0.72], "chair_back"))
    for name, x, y in [
        ("C3D_ChairLeg_FL", -0.21, -0.82),
        ("C3D_ChairLeg_FR", 0.21, -0.82),
        ("C3D_ChairLeg_BL", -0.21, -1.18),
        ("C3D_ChairLeg_BR", 0.21, -1.18),
    ]:
        add(ActionType.CREATE_OBJECT, f"Create chair leg {name}.", _create("cube", name, [x, y, 0.225], [0.06, 0.06, 0.45], "chair_leg"))
    for target in ["C3D_ChairSeat", "C3D_ChairBack", "C3D_ChairLeg_FL", "C3D_ChairLeg_FR", "C3D_ChairLeg_BL", "C3D_ChairLeg_BR"]:
        add(ActionType.ASSIGN_MATERIAL, f"Assign chair wood material to {target}.", _material(target, "C3D_ChairWood", [0.36, 0.16, 0.07, 1.0], 0.55, 0.0))

    add(ActionType.CREATE_OBJECT, "Create lamp base.", _create("cylinder", "C3D_LampBase", [0.48, 0.12, 0.82], [0.18, 0.18, 0.05], "lamp_base"))
    add(ActionType.CREATE_OBJECT, "Create lamp stem.", _create("cylinder", "C3D_LampStem", [0.48, 0.12, 1.04], [0.035, 0.035, 0.42], "lamp_stem"))
    add(ActionType.CREATE_OBJECT, "Create lamp shade.", _create("sphere", "C3D_LampShade", [0.48, 0.12, 1.28], [0.24, 0.24, 0.18], "lamp_shade"))
    for target in ["C3D_LampBase", "C3D_LampStem", "C3D_LampShade"]:
        add(ActionType.ASSIGN_MATERIAL, f"Assign lamp material to {target}.", _material(target, "C3D_BrushedLampMetal", [0.72, 0.62, 0.48, 1.0], 0.32, 0.2))

    if include_warm_light:
        add(
            ActionType.CREATE_OBJECT,
            "Create warm lamp point light.",
            {
                "primitive": "point_light",
                "name": "C3D_WarmLampLight",
                "location": [0.48, 0.12, 1.22],
                "rotation": [0.0, 0.0, 0.0],
                "scale": [1.0, 1.0, 1.0],
                "dimensions": [0.1, 0.1, 0.1],
                "semantic_type": "warm_point_light",
                "light": {"color": [1.0, 0.72, 0.45], "energy": 650.0},
            },
        )

    return actions


def _create(
    primitive: str,
    name: str,
    location: list[float],
    dimensions: list[float],
    semantic_type: str,
) -> dict:
    return {
        "primitive": primitive,
        "name": name,
        "location": location,
        "rotation": [0.0, 0.0, 0.0],
        "scale": [1.0, 1.0, 1.0],
        "dimensions": dimensions,
        "semantic_type": semantic_type,
    }


def _material(
    target_name: str,
    name: str,
    base_color: list[float],
    roughness: float,
    metallic: float,
) -> dict:
    return {
        "target_name": target_name,
        "material": {
            "name": name,
            "base_color": base_color,
            "roughness": roughness,
            "metallic": metallic,
        },
    }


def _action(
    action_type: ActionType,
    description: str,
    parameters: dict,
    *,
    plan_order: int = 1,
) -> Action:
    return Action(
        type=action_type,
        description=description,
        parameters=parameters,
        status=ActionStatus.PLANNED,
        metadata={
            "planner": "deterministic_demo",
            "demo": True,
            "model_used": "none",
            "plan_order": plan_order,
        },
    )

