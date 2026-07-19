from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
CONNECTION_PATH = Path("/tmp/codex3d_sprint02d_gui_connection.json")
PLAYBACK_PATH = Path("/tmp/codex3d_sprint02d_gui_playback.json")
BUILDING_PATH = Path("/tmp/codex3d_sprint02d_gui_building")
PLAY_PATH = Path("/tmp/codex3d_sprint02d_gui_play")


def main() -> int:
    deadline = time.monotonic() + 45
    while not CONNECTION_PATH.is_file():
        if time.monotonic() >= deadline:
            print(json.dumps({"status": "FAILED", "reason": "isolated Blender GUI bridge did not become ready"}))
            return 1
        time.sleep(0.2)
    connection = json.loads(CONNECTION_PATH.read_text(encoding="utf-8"))
    BUILDING_PATH.touch()
    PLAY_PATH.unlink(missing_ok=True)
    PLAYBACK_PATH.unlink(missing_ok=True)
    env = dict(os.environ)
    env.update(
        {
            "CODEX3D_BRIDGE_HOST": "127.0.0.1",
            "CODEX3D_BRIDGE_PORT": str(connection["port"]),
            "CODEX3D_BRIDGE_TOKEN": connection["token"],
            "CODEX3D_ARTIFACT_ROOT": str(ROOT / "artifacts/hackathon_sol_demo"),
            "CODEX3D_FFMPEG_PATH": "/opt/homebrew/bin/ffmpeg",
        }
    )
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "examples/sol_scene_demo.py"),
            "--pause",
            "1.0",
            "--render-live",
            "--replace-demo-collection",
            "--artifact-root",
            str(ROOT / "artifacts/hackathon_sol_demo"),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=420,
    )
    result_path = ROOT / "artifacts/hackathon_sol_demo/demo_result.json"
    result = json.loads(result_path.read_text(encoding="utf-8")) if completed.returncode in {0, 2} and result_path.is_file() else {}
    ready = (
        completed.returncode in {0, 2}
        and result.get("codex_followup", {}).get("status") == "PASSED"
        and result.get("snapshot_restore", {}).get("status") == "PASSED"
    )
    BUILDING_PATH.unlink(missing_ok=True)
    if ready:
        PLAY_PATH.touch()
    playback_deadline = time.monotonic() + 20
    while not PLAYBACK_PATH.is_file() and time.monotonic() < playback_deadline:
        time.sleep(0.2)
    playback = json.loads(PLAYBACK_PATH.read_text(encoding="utf-8")) if PLAYBACK_PATH.is_file() else {}
    summary = {
        "status": "READY_FOR_HUMAN_CONFIRMATION" if ready and playback.get("timeline_playing") is True else "FAILED",
        "runner_returncode": completed.returncode,
        "object_count": result.get("object_count"),
        "curve_count": result.get("curve_count"),
        "codex_followup": result.get("codex_followup", {}).get("status"),
        "snapshot_restore": result.get("snapshot_restore", {}).get("status"),
        "playback": playback,
        "stderr_tail": completed.stderr[-500:] if completed.returncode not in {0, 2} else "",
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "READY_FOR_HUMAN_CONFIRMATION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
