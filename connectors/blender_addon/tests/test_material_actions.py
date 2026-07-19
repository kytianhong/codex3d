from codex3d_blender_connector import BlenderActionExecutor, FakeBlenderBackend
from codex3d_protocol import Action, ActionStatus, ActionType


def test_assign_material_records_principled_values() -> None:
    backend = FakeBlenderBackend()
    executor = BlenderActionExecutor(backend)
    executor.execute(
        Action(
            type=ActionType.CREATE_OBJECT,
            parameters={
                "primitive": "cube",
                "name": "C3D_DeskTop",
                "dimensions": [1.4, 0.7, 0.08],
                "semantic_type": "desk_top",
            },
        )
    )

    result = executor.execute(
        Action(
            type=ActionType.ASSIGN_MATERIAL,
            parameters={
                "target_name": "C3D_DeskTop",
                "material": {
                    "name": "C3D_Walnut",
                    "base_color": [0.30, 0.12, 0.045, 1.0],
                    "roughness": 0.48,
                    "metallic": 0.0,
                },
            },
        )
    )

    assert result.status is ActionStatus.SUCCEEDED
    assert backend.objects["C3D_DeskTop"].material["name"] == "C3D_Walnut"
    assert backend.objects["C3D_DeskTop"].material["roughness"] == 0.48


def test_material_and_light_validation_failures() -> None:
    backend = FakeBlenderBackend()
    executor = BlenderActionExecutor(backend)
    executor.execute(
        Action(
            type=ActionType.CREATE_OBJECT,
            parameters={"primitive": "point_light", "name": "C3D_Light"},
        )
    )

    bad_material = executor.execute(
        Action(
            type=ActionType.ASSIGN_MATERIAL,
            parameters={
                "target_name": "C3D_Light",
                "material": {
                    "name": "Bad",
                    "base_color": [1.2, 0.0, 0.0, 1.0],
                    "roughness": 0.5,
                    "metallic": 0.0,
                },
            },
        )
    )
    bad_light = executor.execute(
        Action(
            type=ActionType.MODIFY_OBJECT,
            parameters={
                "target_name": "C3D_Light",
                "light": {"color": [1.0, 0.5, 2.0], "energy": 420.0},
            },
        )
    )

    assert bad_material.status is ActionStatus.FAILED
    assert bad_light.status is ActionStatus.FAILED


def test_light_energy_and_color_can_be_modified() -> None:
    backend = FakeBlenderBackend()
    executor = BlenderActionExecutor(backend)
    executor.execute(
        Action(
            type=ActionType.CREATE_OBJECT,
            parameters={
                "primitive": "point_light",
                "name": "C3D_LampLight",
                "light": {"color": [1.0, 0.72, 0.45], "energy": 650.0},
            },
        )
    )

    result = executor.execute(
        Action(
            type=ActionType.MODIFY_OBJECT,
            parameters={
                "target_name": "C3D_LampLight",
                "new_name": "C3D_WarmLampLight",
                "light": {"color": [1.0, 0.65, 0.35], "energy": 420.0},
            },
        )
    )

    assert result.status is ActionStatus.SUCCEEDED
    assert "C3D_LampLight" not in backend.objects
    assert backend.objects["C3D_WarmLampLight"].light["energy"] == 420.0
    assert backend.objects["C3D_WarmLampLight"].light["color"] == [1.0, 0.65, 0.35]

