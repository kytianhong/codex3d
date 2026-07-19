from types import SimpleNamespace

from codex3d_blender_connector.inspection import inspect_scene


def test_inspect_scene_without_bpy_returns_empty_scene() -> None:
    inspection = inspect_scene(None)

    assert inspection.metadata["blender_available"] is False
    assert inspection.scene.metadata["object_count"] == 0
    assert inspection.scene.objects == []


def test_inspect_fake_bpy_scene_creates_scene_objects() -> None:
    fake_object = SimpleNamespace(
        name="Fake Cube",
        type="MESH",
        location=(1.0, 2.0, 3.0),
        rotation_euler=(0.1, 0.2, 0.3),
        scale=(1.0, 1.0, 1.0),
        dimensions=(2.0, 3.0, 4.0),
        uuid="fake-cube-uuid",
    )
    fake_scene = SimpleNamespace(name="Fake Scene", objects=[fake_object])
    fake_bpy = SimpleNamespace(context=SimpleNamespace(scene=fake_scene))

    inspection = inspect_scene(fake_bpy, connector_id="connector_fake")

    assert inspection.connector_id == "connector_fake"
    assert inspection.metadata["blender_available"] is True
    assert len(inspection.scene.objects) == 1
    assert inspection.scene.objects[0].label == "Fake Cube"
    assert inspection.scene.objects[0].semantic_type == "mesh"
    assert inspection.scene.objects[0].dimensions.height == 4.0


def test_smoke_direct_service_handshake_runs(capsys) -> None:
    from codex3d_blender_connector.smoke import main

    main()
    captured = capsys.readouterr()

    assert "connector_name: Codex3D Blender Connector" in captured.out
    assert "ping_payload_connector_id:" in captured.out
    assert "inspected_scene_object_count: 0" in captured.out
