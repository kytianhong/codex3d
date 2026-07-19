from codex3d_protocol import (
    Constraint,
    ConstraintType,
    Dimensions,
    Relation,
    RelationType,
    Scene,
    SceneObject,
    SceneObjectSourceType,
    Transform,
    Vector3,
)


def test_scene_can_hold_objects_relations_and_constraints() -> None:
    scene = Scene(name="Tiny studio")
    desk = SceneObject(
        label="Writing desk",
        semantic_type="desk",
        source_type=SceneObjectSourceType.PROCEDURAL,
        transform=Transform(location=Vector3(x=1.0, y=0.0, z=0.4)),
        dimensions=Dimensions(width=1.2, depth=0.6, height=0.75),
    )
    lamp = SceneObject(label="Desk lamp", semantic_type="lamp")

    scene.add_object(desk)
    scene.add_object(lamp)
    relation = scene.add_relation(
        Relation(
            type=RelationType.ON_TOP_OF,
            source_object_id=lamp.id,
            target_object_id=desk.id,
        )
    )
    constraint = scene.add_constraint(
        Constraint(
            type=ConstraintType.KEEP_VISIBLE,
            subject_object_id=lamp.id,
            description="Keep the lamp visible in preview renders.",
            parameters={"camera": "main"},
        )
    )

    assert scene.name == "Tiny studio"
    assert scene.objects == [desk, lamp]
    assert relation.type is RelationType.ON_TOP_OF
    assert constraint.type is ConstraintType.KEEP_VISIBLE
    assert desk.dimensions.height == 0.75
    assert scene.updated_at

