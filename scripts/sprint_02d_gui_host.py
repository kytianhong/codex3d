from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import stat

import bpy  # type: ignore


CONNECTION_PATH = Path("/tmp/codex3d_sprint02d_gui_connection.json")
PLAYBACK_PATH = Path("/tmp/codex3d_sprint02d_gui_playback.json")
STOP_PATH = Path("/tmp/codex3d_sprint02d_gui_stop")
BUILDING_PATH = Path("/tmp/codex3d_sprint02d_gui_building")
PLAY_PATH = Path("/tmp/codex3d_sprint02d_gui_play")
PACKAGE_NAME = "bl_ext.user_default.codex3d_blender_connector"


def _load_extension():
    import importlib

    extension = importlib.import_module(PACKAGE_NAME)
    if not hasattr(bpy.types, "CODEX3D_PT_bridge"):
        extension.register()
    return extension


def _set_panel_preferences(extension, port: int, token: str) -> None:
    addon = bpy.context.preferences.addons.get(PACKAGE_NAME)
    if addon is None:
        raise RuntimeError("Installed Codex3D Extension preferences are unavailable.")
    addon.preferences.port = port
    addon.preferences.auth_token = token
    bpy.ops.wm.save_userpref()


def _show_camera_and_sidebar() -> bool:
    scene = bpy.context.scene
    camera = bpy.data.objects.get("C3D_SOL_Camera")
    if camera is None:
        return False
    scene.camera = camera
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            space = area.spaces.active
            space.show_region_ui = True
            space.region_3d.view_perspective = "CAMERA"
            with bpy.context.temp_override(window=window, screen=screen, area=area):
                if not screen.is_animation_playing:
                    bpy.ops.screen.animation_play()
            return bool(screen.is_animation_playing)
    return False


def _stop_playback() -> None:
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        if not screen.is_animation_playing:
            continue
        area = next((item for item in screen.areas if item.type == "VIEW_3D"), screen.areas[0])
        with bpy.context.temp_override(window=window, screen=screen, area=area):
            bpy.ops.screen.animation_cancel(restore_frame=False)


def main() -> None:
    extension = _load_extension()
    token = secrets.token_urlsafe(32)
    controller = extension.get_runtime_controller()
    host, port = controller.connect(bpy, port=0, token=token)
    _set_panel_preferences(extension, port, token)
    CONNECTION_PATH.write_text(
        json.dumps({"host": host, "port": port, "token": token}),
        encoding="utf-8",
    )
    CONNECTION_PATH.chmod(stat.S_IRUSR | stat.S_IWUSR)
    STOP_PATH.unlink(missing_ok=True)
    BUILDING_PATH.unlink(missing_ok=True)
    PLAY_PATH.unlink(missing_ok=True)
    PLAYBACK_PATH.unlink(missing_ok=True)

    def monitor() -> float | None:
        if STOP_PATH.exists():
            _stop_playback()
            controller.disconnect()
            CONNECTION_PATH.unlink(missing_ok=True)
            PLAYBACK_PATH.unlink(missing_ok=True)
            STOP_PATH.unlink(missing_ok=True)
            BUILDING_PATH.unlink(missing_ok=True)
            PLAY_PATH.unlink(missing_ok=True)
            bpy.ops.wm.quit_blender()
            return None
        if BUILDING_PATH.exists():
            _stop_playback()
            PLAYBACK_PATH.unlink(missing_ok=True)
            return 0.25
        root = bpy.data.objects.get("C3D_SOL_KineticRoot")
        scene = bpy.context.scene
        if PLAY_PATH.exists() and root is not None and scene.frame_start == 1 and scene.frame_end == 72:
            scene.frame_set(1)
            playing = _show_camera_and_sidebar()
            PLAYBACK_PATH.write_text(
                json.dumps(
                    {
                        "timeline_playing": playing,
                        "frame_start": scene.frame_start,
                        "frame_end": scene.frame_end,
                        "collection_present": bpy.data.collections.get("C3D_SOL_DEMO") is not None,
                        "panel_registered": hasattr(bpy.types, "CODEX3D_PT_bridge"),
                        "bridge_status": controller.refresh_state().status.value,
                    }
                ),
                encoding="utf-8",
            )
            return 0.5
        return 0.25

    bpy.app.timers.register(monitor, first_interval=0.25, persistent=True)


main()
