import json

from codex3d_protocol import (
    Action,
    ActionType,
    Asset,
    AssetFormat,
    AssetSourceType,
    Constraint,
    ConstraintType,
    Dimensions,
    Job,
    JobType,
    LicenseType,
    Provenance,
    Relation,
    RelationType,
    Scene,
    SceneObject,
    ToolCall,
    from_dict,
    to_dict,
    to_json,
)


def test_scene_serializes_to_json_friendly_dict() -> None:
    scene = Scene(name="Serialization demo")
    desk = scene.add_object(
        SceneObject(
            label="Desk",
            semantic_type="desk",
            dimensions=Dimensions(width=1.2, depth=0.6, height=0.75),
        )
    )
    lamp = scene.add_object(SceneObject(label="Lamp", semantic_type="lamp"))
    scene.add_relation(
        Relation(
            type=RelationType.ON_TOP_OF,
            source_object_id=lamp.id,
            target_object_id=desk.id,
        )
    )
    scene.add_constraint(
        Constraint(
            type=ConstraintType.LOCK_POSITION,
            subject_object_id=desk.id,
            description="Keep the desk fixed during style edits.",
        )
    )

    data = to_dict(scene)

    assert data["unit_system"] == "meters"
    assert data["objects"][0]["dimensions"]["width"] == 1.2
    assert data["relations"][0]["type"] == "on_top_of"
    assert data["constraints"][0]["type"] == "lock_position"


def test_scene_round_trips_from_dict() -> None:
    scene = Scene(name="Round trip demo")
    scene.add_object(SceneObject(label="Desk", semantic_type="desk"))
    data = to_dict(scene)

    restored = from_dict(Scene, data)

    assert restored.name == scene.name
    assert restored.unit_system == scene.unit_system
    assert restored.objects[0].label == "Desk"
    assert isinstance(restored.objects[0], SceneObject)


def test_core_protocol_objects_serialize_to_json() -> None:
    action = Action(type=ActionType.RENDER_PREVIEW)
    action.add_tool_call(ToolCall(tool_name="render_preview", arguments={"view": "front"}))
    job = Job(type=JobType.RENDER_PREVIEW, action_id=action.id)
    asset = Asset(
        name="Generated desk",
        format=AssetFormat.GLB,
        source_type=AssetSourceType.GENERATED,
        provenance=Provenance(
            source_type=AssetSourceType.GENERATED,
            license=LicenseType.UNKNOWN,
            prompt="A compact desk",
        ),
    )

    payload = {
        "action": to_dict(action),
        "job": to_dict(job),
        "asset": to_dict(asset),
    }
    encoded = json.dumps(payload, sort_keys=True)
    action_json = to_json(action)

    assert '"render_preview"' in encoded
    assert json.loads(action_json)["type"] == "render_preview"

