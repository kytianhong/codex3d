"""Start the installed Codex3D bridge inside Blender for a local smoke test."""

from __future__ import annotations

import json
import os
import secrets

import bpy
from bl_ext.user_default import codex3d_blender_connector


INFO_PATH = os.environ.get("CODEX3D_BRIDGE_INFO_PATH", "/private/tmp/codex3d_blender_bridge.json")
STOP_PATH = os.environ.get("CODEX3D_BRIDGE_STOP_PATH", "/private/tmp/codex3d_blender_bridge.stop")
PORT = int(os.environ.get("CODEX3D_BLENDER_PORT", "9876"))


def _write_private_connection_info(data: dict) -> None:
    descriptor = os.open(INFO_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(data, handle)


token = secrets.token_urlsafe(32)
controller = codex3d_blender_connector.get_runtime_controller()
host, port = controller.connect(bpy, port=PORT, token=token)
_write_private_connection_info({"host": host, "port": port, "token": token})
print(f"Codex3D bridge connected at {host}:{port}; connection info is in {INFO_PATH}")


def _stop_when_requested():
    if not os.path.exists(STOP_PATH):
        return 0.2
    os.unlink(STOP_PATH)
    controller.disconnect()
    if os.path.exists(INFO_PATH):
        os.unlink(INFO_PATH)
    print("Codex3D bridge disconnected cleanly.")
    bpy.ops.wm.quit_blender()
    return None


bpy.app.timers.register(_stop_when_requested, first_interval=0.2)
