from pathlib import Path

import pytest

from codex3d_blender_connector import BlenderActionExecutor, FakeBlenderBackend
from codex3d_blender_connector.artifact_paths import ArtifactPathError, resolve_artifact_path
from codex3d_protocol import Action, ActionStatus, ActionType


def _execute(executor, action_type, parameters):
    result = executor.execute(Action(type=action_type, parameters=parameters))
    assert result.status is ActionStatus.SUCCEEDED, result.error
    return result


def test_artifact_path_stays_inside_root(tmp_path: Path) -> None:
    path, relative = resolve_artifact_path(tmp_path, "renders/preview.png", allowed_suffixes={".png"})

    assert path == tmp_path / "renders/preview.png"
    assert relative == "renders/preview.png"
    with pytest.raises(ArtifactPathError):
        resolve_artifact_path(tmp_path, "../escape.png", allowed_suffixes={".png"})
    with pytest.raises(ArtifactPathError):
        resolve_artifact_path(tmp_path, "/tmp/escape.png", allowed_suffixes={".png"})
    with pytest.raises(ArtifactPathError):
        resolve_artifact_path(tmp_path, "preview.exe", allowed_suffixes={".png"})


def test_fake_backend_creative_scene_state_and_artifacts(tmp_path: Path) -> None:
    backend = FakeBlenderBackend(tmp_path)
    executor = BlenderActionExecutor(backend)
    _execute(
        executor,
        ActionType.CREATE_OBJECT,
        {
            "primitive": "curve",
            "name": "C3D_SOL_Curve",
            "points": [[0, 0, 0], [1, 0, 0], [1, 1, 0]],
            "curve_type": "bezier",
            "cyclic": True,
            "bevel_depth": 0.05,
            "bevel_resolution": 3,
            "fill_mode": "FULL",
            "collection": "C3D_SOL_DEMO",
        },
    )
    _execute(
        executor,
        ActionType.CREATE_OBJECT,
        {"primitive": "empty", "name": "C3D_SOL_Root", "display_size": 1.0},
    )
    _execute(
        executor,
        ActionType.CREATE_OBJECT,
        {"primitive": "camera", "name": "C3D_SOL_Camera", "location": [0, -8, 2], "look_at": [0, 0, 0], "focal_length": 52},
    )
    _execute(executor, ActionType.SET_PARENT, {"target_name": "C3D_SOL_Curve", "parent_name": "C3D_SOL_Root"})
    _execute(executor, ActionType.CONFIGURE_WORLD, {"color": [0.01, 0.02, 0.04], "strength": 0.15})
    _execute(
        executor,
        ActionType.CONFIGURE_SCENE,
        {"engine": "BLENDER_EEVEE_NEXT", "resolution_x": 512, "resolution_y": 512, "samples": 32, "transparent": False, "fps": 24, "frame_start": 1, "frame_end": 72},
    )
    keyframes = _execute(
        executor,
        ActionType.KEYFRAME_OBJECT,
        {"target_name": "C3D_SOL_Root", "keyframes": [{"frame": 1, "rotation": [0, 0, 0]}, {"frame": 72, "rotation": [0, 0, 6.283185]}], "interpolation": "LINEAR", "cycle": True},
    )
    render = _execute(executor, ActionType.RENDER_PREVIEW, {"kind": "still", "path": "preview.png"})
    checkpoint = _execute(executor, ActionType.SAVE_CHECKPOINT, {"path": "scene.blend"})

    assert backend.objects["C3D_SOL_Curve"].curve["cyclic"] is True
    assert backend.objects["C3D_SOL_Curve"].parent_name == "C3D_SOL_Root"
    assert keyframes.output["keyframe_count"] == 2
    assert keyframes.output["fcurve_count"] > 0
    assert render.output["width"] == 512 and render.output["subject_visible"] is True
    assert checkpoint.output["path"] == "scene.blend"
    assert (tmp_path / "preview.png").is_file()
    assert (tmp_path / "scene.blend").is_file()


def test_executor_rejects_unsafe_artifact_paths_and_invalid_curve(tmp_path: Path) -> None:
    executor = BlenderActionExecutor(FakeBlenderBackend(tmp_path))
    unsafe = executor.execute(Action(type=ActionType.RENDER_PREVIEW, parameters={"kind": "still", "path": "../bad.png"}))
    bad_curve = executor.execute(Action(type=ActionType.CREATE_OBJECT, parameters={"primitive": "curve", "name": "Bad", "points": [[0, 0, 0]]}))

    assert unsafe.status is ActionStatus.FAILED
    assert bad_curve.status is ActionStatus.FAILED
