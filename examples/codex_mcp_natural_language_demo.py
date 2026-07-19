from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

from codex3d_api import SocketConnectorClient


ROOT = Path(__file__).resolve().parents[1]
OBJECT_NAME = "C3D_MCP_DemoCube"
FOLLOW_UP_MATERIAL = "C3D_MCP_FollowUpMaterial"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Codex natural-language use of the local Codex3D MCP server.")
    parser.add_argument("--connection-info", required=True)
    args = parser.parse_args(argv)
    try:
        with open(args.connection_info, encoding="utf-8") as handle:
            info = json.load(handle)
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"Could not read bridge connection info: {exc}", file=sys.stderr)
        return 2

    codex = shutil.which("codex")
    if codex is None:
        print("Codex CLI is unavailable.", file=sys.stderr)
        return 2

    pythonpath = os.pathsep.join(
        [str(ROOT / "packages" / "protocol"), str(ROOT / "apps" / "api"), str(ROOT / "apps" / "mcp")]
    )
    env = dict(os.environ)
    env.update(
        {
            "CODEX3D_BRIDGE_HOST": info["host"],
            "CODEX3D_BRIDGE_PORT": str(info["port"]),
            "CODEX3D_BRIDGE_TOKEN": info["token"],
            "PYTHONPATH": pythonpath,
        }
    )
    prompt = (
        "Use only the codex3d MCP Blender tools for this task. Do not edit files or run shell commands. "
        f"Inspect the scene, move {OBJECT_NAME} to [0.6, 0.0, 1.2] meters, assign a new material named "
        f"{FOLLOW_UP_MATERIAL} with base color [0.8, 0.16, 0.1, 1.0], roughness 0.28, metallic 0.05, "
        "then inspect again and briefly report the final location and material."
    )
    command = [
        codex,
        "exec",
        "--json",
        "--ephemeral",
        "--ignore-user-config",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "-c",
        'approval_policy="never"',
        "-C",
        str(ROOT),
        "-c",
        f'mcp_servers.codex3d.command="{sys.executable}"',
        "-c",
        'mcp_servers.codex3d.args=["-m","codex3d_mcp"]',
        "-c",
        f'mcp_servers.codex3d.cwd="{ROOT}"',
        "-c",
        'mcp_servers.codex3d.env_vars=["CODEX3D_BRIDGE_HOST","CODEX3D_BRIDGE_PORT","CODEX3D_BRIDGE_TOKEN","PYTHONPATH"]',
        prompt,
    ]
    completed = subprocess.run(command, capture_output=True, text=True, env=env, check=False, timeout=180)

    with SocketConnectorClient(host=info["host"], port=int(info["port"]), token=info["token"]) as client:
        inspection = client.inspect_scene()
    cube = next((item for item in inspection.scene.objects if item.label == OBJECT_NAME), None)
    verified = bool(
        cube
        and math.isclose(cube.transform.location.x, 0.6, abs_tol=1e-5)
        and math.isclose(cube.transform.location.y, 0.0, abs_tol=1e-5)
        and math.isclose(cube.transform.location.z, 1.2, abs_tol=1e-5)
        and cube.metadata.get("material_name") == FOLLOW_UP_MATERIAL
    )
    summary = {
        "ok": completed.returncode == 0 and verified,
        "codex_returncode": completed.returncode,
        "scene_verified": verified,
        "final_location": (
            {"x": cube.transform.location.x, "y": cube.transform.location.y, "z": cube.transform.location.z}
            if cube
            else None
        ),
        "material_name": cube.metadata.get("material_name") if cube else None,
        "codex_output_tail": completed.stdout[-2000:],
        "codex_error_tail": completed.stderr[-1000:],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
