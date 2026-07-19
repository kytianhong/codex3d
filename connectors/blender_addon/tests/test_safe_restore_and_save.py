from pathlib import Path

from codex3d_blender_connector import BlenderActionExecutor, FakeBlenderBackend
from codex3d_protocol import Action, ActionStatus, ActionType


def _execute(executor, action_type, **parameters):
    return executor.execute(Action(type=action_type, parameters=parameters))


def test_restore_rejects_wrong_session_and_fingerprints_without_mutation(tmp_path: Path) -> None:
    backend = FakeBlenderBackend(tmp_path, session_id="session_a")
    executor = BlenderActionExecutor(backend)
    _execute(executor, ActionType.CREATE_OBJECT, primitive="sphere", name="C3D_Core")
    snapshot = _execute(executor, ActionType.SNAPSHOT_SCENE, snapshot_id="snapshot_confirmed")
    _execute(executor, ActionType.TRANSFORM_OBJECT, target_name="C3D_Core", location=[1, 2, 3])
    current = backend.inspect().metadata["scene_fingerprint"]

    wrong_fingerprint = _execute(
        executor,
        ActionType.RESTORE_SNAPSHOT,
        snapshot_id="snapshot_confirmed",
        current_fingerprint="0" * 64,
        snapshot_fingerprint=snapshot.output["scene_fingerprint"],
    )
    assert wrong_fingerprint.status is ActionStatus.FAILED
    assert backend.objects["C3D_Core"].location == [1, 2, 3]
    assert backend.list_snapshots({})["snapshot_count"] == 1

    backend.session_id = "session_b"
    wrong_session = _execute(
        executor,
        ActionType.RESTORE_SNAPSHOT,
        snapshot_id="snapshot_confirmed",
        current_fingerprint=current,
        snapshot_fingerprint=snapshot.output["scene_fingerprint"],
    )
    assert wrong_session.status is ActionStatus.FAILED
    assert backend.objects["C3D_Core"].location == [1, 2, 3]


def test_restore_creates_non_overwriting_safety_snapshot_and_diff(tmp_path: Path) -> None:
    backend = FakeBlenderBackend(tmp_path, session_id="session_a")
    executor = BlenderActionExecutor(backend)
    _execute(executor, ActionType.CREATE_OBJECT, primitive="sphere", name="C3D_Core")
    snapshot = _execute(executor, ActionType.SNAPSHOT_SCENE, snapshot_id="snapshot_confirmed")
    _execute(executor, ActionType.TRANSFORM_OBJECT, target_name="C3D_Core", location=[3, 0, 0])
    current = backend.inspect().metadata["scene_fingerprint"]
    restored = _execute(
        executor,
        ActionType.RESTORE_SNAPSHOT,
        snapshot_id="snapshot_confirmed",
        current_fingerprint=current,
        snapshot_fingerprint=snapshot.output["scene_fingerprint"],
    )
    assert restored.status is ActionStatus.SUCCEEDED
    assert restored.output["safety_snapshot_id"].startswith("snapshot_pre_restore_")
    assert restored.output["scene_diff"]["changed"]
    assert backend.objects["C3D_Core"].location == [0.0, 0.0, 0.0]


def test_versioned_checkpoint_never_overwrites_and_reports_integrity(tmp_path: Path) -> None:
    backend = FakeBlenderBackend(tmp_path)
    executor = BlenderActionExecutor(backend)
    _execute(executor, ActionType.CREATE_OBJECT, primitive="cube", name="C3D_Box")
    fingerprint = backend.inspect().metadata["scene_fingerprint"]
    first = _execute(executor, ActionType.SAVE_CHECKPOINT, path="final_scene.blend")
    second = _execute(executor, ActionType.SAVE_CHECKPOINT, path="final_scene.blend")
    assert first.status is second.status is ActionStatus.SUCCEEDED
    assert first.output["path"] == "final_scene.blend"
    assert second.output["path"] == "final_scene_v002.blend"
    assert first.output["sha256"] == second.output["sha256"]
    assert first.output["scene_fingerprint"] == second.output["scene_fingerprint"] == fingerprint
    assert first.output["uuid_count"] == 1
