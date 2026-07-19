from pathlib import Path

from codex3d_blender_connector import BlenderActionExecutor, FakeBlenderBackend
from codex3d_protocol import Action, ActionStatus, ActionType


def _execute(executor, action_type, **parameters):
    result = executor.execute(Action(type=action_type, parameters=parameters))
    assert result.status is ActionStatus.SUCCEEDED, result.error
    return result


def test_uuid_survives_rename_and_can_target_followup(tmp_path: Path) -> None:
    backend = FakeBlenderBackend(tmp_path)
    executor = BlenderActionExecutor(backend)
    created = _execute(executor, ActionType.CREATE_OBJECT, primitive="sphere", name="C3D_Core")
    object_uuid = created.output["object_uuid"]

    renamed = _execute(executor, ActionType.MODIFY_OBJECT, target_uuid=object_uuid, new_name="C3D_Core_Renamed")
    assert renamed.output["object_uuid"] == object_uuid
    assert backend.object_exists("C3D_Core") is False
    assert backend.object_exists(object_uuid) is True
    inspection = backend.inspect()
    assert inspection.scene.objects[0].blender_uuid == object_uuid
    assert inspection.scene.objects[0].metadata["codex3d_uuid"] == object_uuid


def test_snapshot_restore_recovers_transform_material_and_camera(tmp_path: Path) -> None:
    backend = FakeBlenderBackend(tmp_path)
    executor = BlenderActionExecutor(backend)
    core = _execute(executor, ActionType.CREATE_OBJECT, primitive="sphere", name="C3D_Core")
    _execute(
        executor,
        ActionType.ASSIGN_MATERIAL,
        target_uuid=core.output["object_uuid"],
        material={"name": "C3D_Gold", "base_color": [0.8, 0.5, 0.1, 1.0], "roughness": 0.3, "metallic": 0.7},
    )
    _execute(executor, ActionType.CREATE_OBJECT, primitive="camera", name="C3D_Camera", active=True)
    snapshot = _execute(executor, ActionType.SNAPSHOT_SCENE, snapshot_id="snapshot_test", source_turn="unit-test")
    expected = snapshot.output["scene_fingerprint"]

    _execute(executor, ActionType.TRANSFORM_OBJECT, target_uuid=core.output["object_uuid"], location=[4, 5, 6])
    current = backend.inspect().metadata["scene_fingerprint"]
    restored = _execute(
        executor,
        ActionType.RESTORE_SNAPSHOT,
        snapshot_id="snapshot_test",
        current_fingerprint=current,
        snapshot_fingerprint=expected,
    )
    assert restored.output["scene_fingerprint"] == expected
    assert backend.objects["C3D_Core"].location == [0.0, 0.0, 0.0]
    assert backend.objects["C3D_Core"].material["name"] == "C3D_Gold"
    assert restored.output["active_camera"] == "C3D_Camera"
    assert restored.output["safety_snapshot_id"].startswith("snapshot_pre_restore_")

    listed = _execute(executor, ActionType.LIST_SNAPSHOTS)
    assert listed.output["snapshot_count"] == 2
    _execute(executor, ActionType.DELETE_SNAPSHOT, snapshot_id="snapshot_test")
    assert not (tmp_path / "snapshots" / "snapshot_test.blend").exists()


def test_reconcile_assigns_uuid_to_legacy_objects(tmp_path: Path) -> None:
    backend = FakeBlenderBackend(tmp_path)
    executor = BlenderActionExecutor(backend)
    _execute(executor, ActionType.CREATE_OBJECT, primitive="cube", name="C3D_Legacy")
    backend.objects["C3D_Legacy"].codex3d_uuid = ""
    result = _execute(executor, ActionType.RECONCILE_OBJECT_IDS, prefix="C3D_")
    assert result.output["assigned_count"] == 1
    assert backend.objects["C3D_Legacy"].codex3d_uuid.startswith("object_")
