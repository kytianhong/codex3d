from __future__ import annotations

import json
import os
import secrets
from dataclasses import dataclass
from typing import Any, Callable

from .action_executor import BlenderActionExecutor
from .backends import BpyBlenderBackend
from .bridge_runtime import BlenderBridgeRuntime
from .bridge_server import DEFAULT_PORT, LOOPBACK_HOST, BridgeServer, BridgeServerError
from .manifest import CONNECTOR_NAME, CONNECTOR_VERSION
from .protocol_compat import BridgeStatus

bl_info = {
    "name": CONNECTOR_NAME,
    "author": "Codex3D",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "location": "3D View > Sidebar > Codex3D",
    "description": "Authenticated localhost bridge for structured Codex3D actions.",
    "category": "3D View",
}


def _load_bpy():
    try:
        import bpy  # type: ignore
    except ImportError:
        return None
    return bpy


@dataclass
class AddonRuntimeState:
    status: BridgeStatus = BridgeStatus.DISCONNECTED
    host: str = LOOPBACK_HOST
    port: int = DEFAULT_PORT
    pending_count: int = 0
    last_request_summary: str = ""
    last_error: str = ""


class AddonLifecycleController:
    def __init__(
        self,
        backend_factory: Callable[[Any], Any] = BpyBlenderBackend,
        server_factory: Callable[[BlenderBridgeRuntime], BridgeServer] = BridgeServer,
    ) -> None:
        self.state = AddonRuntimeState()
        self.backend_factory = backend_factory
        self.server_factory = server_factory
        self.runtime: BlenderBridgeRuntime | None = None
        self.server: BridgeServer | None = None

    def connect(self, bpy_module: Any, *, port: int = DEFAULT_PORT, token: str) -> tuple[str, int]:
        if self.server is not None and self.server.is_running and self.server.bound_address is not None:
            return self.server.bound_address
        self.state.status = BridgeStatus.STARTING
        self.state.last_error = ""
        try:
            backend = self.backend_factory(bpy_module)
            executor = BlenderActionExecutor(backend)
            version = str(getattr(getattr(bpy_module, "app", None), "version_string", "unknown"))
            runtime = BlenderBridgeRuntime(
                executor,
                connector_version=CONNECTOR_VERSION,
                blender_version=version,
            )
            server = self.server_factory(runtime)
            if hasattr(server, "request_timeout"):
                server.request_timeout = float(os.environ.get("CODEX3D_BRIDGE_REQUEST_TIMEOUT", server.request_timeout))
            address = server.start(host=LOOPBACK_HOST, port=port, token=token)
            runtime.start_timer(bpy_module)
            self.runtime = runtime
            self.server = server
            self.state.status = BridgeStatus.CONNECTED
            self.state.host, self.state.port = address
            return address
        except Exception as exc:
            if "runtime" in locals():
                runtime.stop_timer()
            if "server" in locals():
                server.stop()
            self.runtime = None
            self.server = None
            self.state.status = BridgeStatus.ERROR
            self.state.last_error = str(exc)
            raise

    def disconnect(self) -> None:
        if self.server is None and self.runtime is None:
            self.state.status = BridgeStatus.DISCONNECTED
            return
        self.state.status = BridgeStatus.STOPPING
        if self.runtime is not None:
            self.runtime.stop_timer()
        if self.server is not None:
            self.server.stop()
        self.runtime = None
        self.server = None
        self.state.status = BridgeStatus.DISCONNECTED
        self.state.pending_count = 0

    def refresh_state(self) -> AddonRuntimeState:
        if self.runtime is not None:
            self.state.pending_count = self.runtime.pending_count
            self.state.last_request_summary = self.runtime.last_request_summary
            if self.runtime.last_error:
                self.state.last_error = self.runtime.last_error
        return self.state


_controller = AddonLifecycleController()


def get_runtime_controller() -> AddonLifecycleController:
    return _controller


def generate_token() -> str:
    return secrets.token_urlsafe(32)


_bpy = _load_bpy()
_CLASSES: tuple[type, ...] = ()

if _bpy is not None:
    from bpy.props import IntProperty, StringProperty  # type: ignore

    _ADDON_ID = __package__

    class CODEX3D_AddonPreferences(_bpy.types.AddonPreferences):
        bl_idname = _ADDON_ID

        port: IntProperty(name="Port", default=DEFAULT_PORT, min=1024, max=65535)
        auth_token: StringProperty(name="Token", subtype="PASSWORD", default="")

        def draw(self, context):
            layout = self.layout
            layout.label(text=f"Host: {LOOPBACK_HOST}")
            layout.prop(self, "port")
            layout.prop(self, "auth_token")

    class CODEX3D_OT_connect(_bpy.types.Operator):
        bl_idname = "codex3d.connect_bridge"
        bl_label = "Connect"
        bl_description = "Start the authenticated localhost Codex3D bridge"

        def execute(self, context):
            preferences = _get_preferences(context)
            if not preferences.auth_token:
                preferences.auth_token = generate_token()
            try:
                _controller.connect(_bpy, port=preferences.port, token=preferences.auth_token)
            except BridgeServerError as exc:
                self.report({"ERROR"}, exc.error.message)
                return {"CANCELLED"}
            except Exception as exc:
                self.report({"ERROR"}, str(exc))
                return {"CANCELLED"}
            return {"FINISHED"}

    class CODEX3D_OT_disconnect(_bpy.types.Operator):
        bl_idname = "codex3d.disconnect_bridge"
        bl_label = "Disconnect"
        bl_description = "Stop the Codex3D bridge and clean up its timer"

        def execute(self, context):
            _controller.disconnect()
            return {"FINISHED"}

    class CODEX3D_OT_copy_connection_info(_bpy.types.Operator):
        bl_idname = "codex3d.copy_connection_info"
        bl_label = "Copy Connection Info"
        bl_description = "Copy localhost bridge details and token to the clipboard"

        def execute(self, context):
            preferences = _get_preferences(context)
            if not preferences.auth_token:
                preferences.auth_token = generate_token()
            context.window_manager.clipboard = json.dumps(
                {"host": LOOPBACK_HOST, "port": preferences.port, "token": preferences.auth_token},
                separators=(",", ":"),
            )
            self.report({"INFO"}, "Codex3D connection info copied.")
            return {"FINISHED"}

    class CODEX3D_PT_bridge(_bpy.types.Panel):
        bl_label = "Codex3D"
        bl_idname = "CODEX3D_PT_bridge"
        bl_space_type = "VIEW_3D"
        bl_region_type = "UI"
        bl_category = "Codex3D"

        def draw(self, context):
            state = _controller.refresh_state()
            preferences = _get_preferences(context)
            layout = self.layout
            layout.label(text=f"Status: {state.status.value.title()}")
            layout.label(text=f"Host: {LOOPBACK_HOST}")
            layout.prop(preferences, "port")
            layout.prop(preferences, "auth_token")
            row = layout.row(align=True)
            row.operator(CODEX3D_OT_connect.bl_idname, icon="PLAY")
            row.operator(CODEX3D_OT_disconnect.bl_idname, icon="PAUSE")
            layout.operator(CODEX3D_OT_copy_connection_info.bl_idname, icon="COPYDOWN")
            layout.label(text=f"Pending: {state.pending_count}")
            if state.last_request_summary:
                layout.label(text=f"Last: {state.last_request_summary}")
            if state.last_error:
                layout.label(text=f"Error: {state.last_error[:120]}", icon="ERROR")

    def _get_preferences(context):
        addon = context.preferences.addons.get(_ADDON_ID)
        if addon is None:
            raise RuntimeError("Codex3D add-on preferences are unavailable.")
        return addon.preferences

    _CLASSES = (
        CODEX3D_AddonPreferences,
        CODEX3D_OT_connect,
        CODEX3D_OT_disconnect,
        CODEX3D_OT_copy_connection_info,
        CODEX3D_PT_bridge,
    )


def register() -> None:
    bpy_module = _load_bpy()
    if bpy_module is None:
        return
    for cls in _CLASSES:
        bpy_module.utils.register_class(cls)


def unregister() -> None:
    _controller.disconnect()
    bpy_module = _load_bpy()
    if bpy_module is None:
        return
    for cls in reversed(_CLASSES):
        try:
            bpy_module.utils.unregister_class(cls)
        except RuntimeError:
            pass
