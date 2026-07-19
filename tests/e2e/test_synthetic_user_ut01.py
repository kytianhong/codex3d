from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]


pytestmark = pytest.mark.skipif(
    os.environ.get("CODEX3D_RUN_SYNTHETIC_UT01") != "1",
    reason="Set CODEX3D_RUN_SYNTHETIC_UT01=1 to run Blender plus a real persistent Target Codex session.",
)


def test_synthetic_user_ut01(tmp_path: Path) -> None:
    artifact_root = tmp_path / "ut01_synthetic"
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_synthetic_user_test_ut01.py"),
            "--artifact-root",
            str(artifact_root),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=2400,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads((artifact_root / "result.json").read_text(encoding="utf-8"))
    assert result["status"] == "SYNTHETIC_PASS"
    assert result["score"] >= 80
    assert result["restore_validation"]["canonical_summary_match"] is True
    assert result["delivery_state"] == "delivered"
    assert result["assertions"]["isolated_scene_has_no_factory_objects"] is True
    assert result["assertions"]["turn_8_composition_guard"] is True
    assert result["mp4_validation"]["status"] == "PASSED"
    assert result["cleanup"]["bridge_port_released"] is True
    assert result["cleanup"]["global_codex_config_unchanged"] is True
    assert result["cleanup"]["token_absent_from_artifacts"] is True
    for name in (
        "final_scene.blend",
        "preview_turn_3.png",
        "preview_turn_4.png",
        "preview_final.png",
        "codex_space_animation.mp4",
        "conversation.jsonl",
        "tool_trace.jsonl",
        "scene_diffs.json",
        "restore_validation.json",
        "synthetic_scorecard.json",
        "final_manifest.json",
        "result.json",
    ):
        assert (artifact_root / name).is_file(), name
