from codex3d_blender_connector import FakeBlenderBackend


def test_fake_backend_creates_transforms_renames_and_deletes_object() -> None:
    backend = FakeBlenderBackend()
    backend.create_object(
        {
            "primitive": "cube",
            "name": "C3D_Box",
            "location": [0.0, 0.0, 0.5],
            "rotation": [0.0, 0.0, 0.0],
            "scale": [1.0, 1.0, 1.0],
            "dimensions": [1.0, 1.0, 1.0],
            "semantic_type": "box",
        }
    )

    backend.transform_object({"target_name": "C3D_Box", "location": [1.0, 2.0, 3.0]})
    assert backend.objects["C3D_Box"].location == [1.0, 2.0, 3.0]
    assert backend.objects["C3D_Box"].dimensions == [1.0, 1.0, 1.0]

    backend.modify_object({"target_name": "C3D_Box", "new_name": "C3D_RenamedBox"})
    assert "C3D_Box" not in backend.objects
    assert "C3D_RenamedBox" in backend.objects

    backend.delete_object({"target_name": "C3D_RenamedBox"})
    assert backend.objects == {}


def test_fake_backend_inspection_exposes_object_summary() -> None:
    backend = FakeBlenderBackend()
    backend.create_object(
        {
            "primitive": "cube",
            "name": "C3D_DeskTop",
            "dimensions": [1.4, 0.7, 0.08],
            "semantic_type": "desk_top",
        }
    )
    backend.assign_material(
        {
            "target_name": "C3D_DeskTop",
            "material": {
                "name": "C3D_Walnut",
                "base_color": [0.3, 0.12, 0.045, 1.0],
                "roughness": 0.48,
                "metallic": 0.0,
            },
        }
    )

    inspection = backend.inspect()

    assert inspection.metadata["object_count"] == 1
    assert inspection.scene.objects[0].label == "C3D_DeskTop"
    assert inspection.scene.objects[0].metadata["material_name"] == "C3D_Walnut"

