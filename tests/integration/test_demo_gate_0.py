from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


pytestmark = pytest.mark.skipif(
    os.environ.get("CODEX3D_RUN_REAL_BLENDER_TESTS") != "1",
    reason="Set CODEX3D_RUN_REAL_BLENDER_TESTS=1 to run the isolated real-Blender Gate 0 test.",
)


def test_demo_gate_0_real_blender(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "demo_gate_0"
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_demo_gate_0.py"),
            "--skip-baseline",
            "--artifact-dir",
            str(artifact_dir),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads((artifact_dir / "gate_0_result.json").read_text(encoding="utf-8"))
    readiness = json.loads((artifact_dir / "readiness.json").read_text(encoding="utf-8"))
    assert result["gate_status"] == "PASS"
    assert result["mcp"]["gate_object_count"] == 8
    assert result["cleanup"]["bridge_port_released"] is True
    assert (artifact_dir / "codex3d_gate0.blend").is_file()
    assert {item["status"] for item in readiness["capabilities"]} <= {
        "READY",
        "PARTIAL",
        "MISSING",
        "NOT_RUN",
    }
