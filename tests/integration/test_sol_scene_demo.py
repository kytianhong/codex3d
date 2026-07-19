from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


pytestmark = pytest.mark.skipif(
    os.environ.get("CODEX3D_RUN_SOL_DEMO_TESTS") != "1",
    reason="Set CODEX3D_RUN_SOL_DEMO_TESTS=1 to run the real Blender render and animation slice.",
)


def test_real_blender_sol_vertical_slice(tmp_path: Path) -> None:
    artifact_root = tmp_path / "sol_demo"
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "examples/sol_scene_demo.py"),
            "--isolated",
            "--skip-codex",
            "--artifact-root",
            str(artifact_root),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=420,
    )
    assert completed.returncode in {0, 2}, completed.stdout + completed.stderr
    result = json.loads((artifact_root / "demo_result.json").read_text(encoding="utf-8"))
    assert result["curve_count"] == 6
    assert result["initial_render"]["subject_visible"] is True
    assert result["initial_render"]["nonblack_pixel_ratio"] > 0.01
    assert result["animation"]["keyframe_count"] > 0
    assert result["snapshot_restore"]["status"] == "PASSED"
    assert result["snapshot_restore"]["canonical_summary_match"] is True
    assert result["snapshot_restore"]["uuid_count"] == result["object_count"]
    assert result["polished_render"]["subject_visible"] is True
    assert result["polished_render"]["active_camera"] == "C3D_SOL_Camera"
    assert result["cleanup"]["bridge_port_released"] is True
    assert (artifact_root / "sol_demo.blend").is_file()
    assert (artifact_root / "preview_initial.png").is_file()
    assert (artifact_root / "preview_polished.png").is_file()
    assert (artifact_root / "snapshot_restore_result.json").is_file()
    assert (artifact_root / "final_demo_manifest.json").is_file()
