from codex3d_blender_connector import BlenderActionExecutor, FakeBlenderBackend
from codex3d_protocol import Action, ActionStatus, ActionType


def test_executor_creates_all_supported_primitives() -> None:
    backend = FakeBlenderBackend()
    executor = BlenderActionExecutor(backend)

    for primitive in ["cube", "cylinder", "sphere", "plane", "point_light"]:
        action = Action(
            type=ActionType.CREATE_OBJECT,
            parameters={
                "primitive": primitive,
                "name": f"C3D_{primitive}",
                "location": [0.0, 0.0, 0.5],
                "rotation": [0.0, 0.0, 0.0],
                "scale": [1.0, 1.0, 1.0],
                "dimensions": [1.0, 1.0, 1.0],
                "semantic_type": primitive,
                "light": {"color": [1.0, 0.72, 0.45], "energy": 650.0}
                if primitive == "point_light"
                else None,
            },
        )
        if primitive != "point_light":
            action.parameters.pop("light")

        result = executor.execute(action)

        assert result.status is ActionStatus.SUCCEEDED
        assert action.status is ActionStatus.SUCCEEDED
        assert f"C3D_{primitive}" in backend.objects


def test_executor_transform_only_updates_given_fields() -> None:
    backend = FakeBlenderBackend()
    executor = BlenderActionExecutor(backend)
    executor.execute(
        Action(
            type=ActionType.CREATE_OBJECT,
            parameters={
                "primitive": "cube",
                "name": "C3D_Box",
                "location": [0.0, 0.0, 0.5],
                "dimensions": [1.0, 1.0, 1.0],
            },
        )
    )

    result = executor.execute(
        Action(
            type=ActionType.TRANSFORM_OBJECT,
            parameters={"target_name": "C3D_Box", "location": [2.0, 0.0, 0.5]},
        )
    )

    assert result.status is ActionStatus.SUCCEEDED
    assert backend.objects["C3D_Box"].location == [2.0, 0.0, 0.5]
    assert backend.objects["C3D_Box"].dimensions == [1.0, 1.0, 1.0]


def test_executor_returns_failed_for_invalid_primitive_missing_target_and_bad_values() -> None:
    backend = FakeBlenderBackend()
    executor = BlenderActionExecutor(backend)
    invalid_primitive = executor.execute(
        Action(
            type=ActionType.CREATE_OBJECT,
            parameters={"primitive": "torus", "name": "C3D_Bad"},
        )
    )
    missing_target = executor.execute(
        Action(
            type=ActionType.DELETE_OBJECT,
            parameters={"target_name": "C3D_Missing"},
        )
    )
    bad_vector = executor.execute(
        Action(
            type=ActionType.CREATE_OBJECT,
            parameters={
                "primitive": "cube",
                "name": "C3D_BadVector",
                "location": [0.0, 1.0],
            },
        )
    )
    bad_dimensions = executor.execute(
        Action(
            type=ActionType.CREATE_OBJECT,
            parameters={
                "primitive": "cube",
                "name": "C3D_BadDimensions",
                "dimensions": [1.0, -1.0, 1.0],
            },
        )
    )
    bad_infinity = executor.execute(
        Action(
            type=ActionType.CREATE_OBJECT,
            parameters={
                "primitive": "cube",
                "name": "C3D_Infinite",
                "location": [0.0, float("inf"), 0.0],
            },
        )
    )

    assert invalid_primitive.status is ActionStatus.FAILED
    assert missing_target.status is ActionStatus.FAILED
    assert bad_vector.status is ActionStatus.FAILED
    assert bad_dimensions.status is ActionStatus.FAILED
    assert bad_infinity.status is ActionStatus.FAILED
