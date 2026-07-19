from __future__ import annotations

import base64
from collections.abc import Callable
from pathlib import Path
from typing import Any

from codex3d_api import ConnectorTransportError, SocketConnectorClient
from codex3d_protocol import Action, ActionStatus, ActionType, ErrorCode, ProtocolError, to_dict

from .config import BridgeConfig, ConfigurationError
from .validation import (
    PRIMITIVES,
    ToolValidationError,
    color,
    finite_number,
    optional_vector,
    reject_unknown,
    require_name,
    require_object,
    unit_number,
    validate_action_data,
    validate_action_shape,
)


VECTOR3_SCHEMA = {
    "type": "array",
    "minItems": 3,
    "maxItems": 3,
    "items": {"type": "number"},
    "description": "Exactly three finite numbers [x, y, z]. Distances are meters; rotations are radians.",
}
COLOR3_SCHEMA = {
    "type": "array",
    "minItems": 3,
    "maxItems": 3,
    "items": {"type": "number", "minimum": 0, "maximum": 1},
    "description": "Linear RGB color [r, g, b], each component in [0, 1].",
}
COLOR4_SCHEMA = {
    "type": "array",
    "minItems": 4,
    "maxItems": 4,
    "items": {"type": "number", "minimum": 0, "maximum": 1},
    "description": "RGBA color [r, g, b, a], each component in [0, 1].",
}
EMPTY_SCHEMA = {"type": "object", "properties": {}, "additionalProperties": False}
LOOK_AT_SCHEMA = {
    "oneOf": [VECTOR3_SCHEMA, {"type": "string", "minLength": 1}],
    "description": "A target point in meters or an existing object name.",
}
MATERIAL_PROPERTIES = {
    "target_name": {"type": "string", "minLength": 1},
    "target_uuid": {"type": "string", "minLength": 1, "description": "Stable Codex3D object UUID. Preferred over target_name when supplied."},
    "material_name": {"type": "string", "minLength": 1},
    "base_color": COLOR4_SCHEMA,
    "roughness": {"type": "number", "minimum": 0, "maximum": 1},
    "metallic": {"type": "number", "minimum": 0, "maximum": 1},
    "emission_color": COLOR4_SCHEMA,
    "emission_strength": {"type": "number", "minimum": 0},
    "transmission": {"type": "number", "minimum": 0, "maximum": 1},
    "alpha": {"type": "number", "minimum": 0, "maximum": 1},
}


def _annotations(*, read_only: bool, destructive: bool, idempotent: bool) -> dict[str, bool]:
    return {
        "readOnlyHint": read_only,
        "destructiveHint": destructive,
        "idempotentHint": idempotent,
        "openWorldHint": False,
    }


def _tool(
    name: str,
    description: str,
    properties: dict[str, Any],
    required: list[str] | None = None,
    *,
    destructive: bool = False,
    idempotent: bool = False,
    any_of: list[dict[str, Any]] | None = None,
) -> dict:
    schema = {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }
    if any_of:
        schema["anyOf"] = any_of
    return {
        "name": name,
        "description": description,
        "annotations": _annotations(read_only=False, destructive=destructive, idempotent=idempotent),
        "inputSchema": schema,
    }


TOOL_DEFINITIONS = [
    {"name": "blender_ping", "description": "Check the authenticated localhost Blender bridge and report connector/backend versions. Takes no arguments.", "annotations": _annotations(read_only=True, destructive=False, idempotent=True), "inputSchema": EMPTY_SCHEMA},
    {
        "name": "blender_inspect_scene",
        "description": "Inspect Blender with a compact collection-oriented summary by default. Filter by collection, UUID, semantic group, or scene. Use full mode only when all object transforms are genuinely needed. Returns the current fingerprint and accepted snapshot metadata.",
        "annotations": _annotations(read_only=True, destructive=False, idempotent=True),
        "inputSchema": {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": ["compact", "full"], "default": "compact"},
                "collection": {"type": "string", "minLength": 1},
                "object_uuid": {"type": "string", "minLength": 1},
                "semantic_group": {"type": "string", "minLength": 1},
                "scene_name": {"type": "string", "minLength": 1},
            },
            "additionalProperties": False,
        },
    },
    _tool(
        "blender_create_primitive",
        "Create one allowlisted Blender primitive. Location and dimensions are meters; rotation is Euler radians. For meshes, dimensions define final physical size and take precedence over scale. light is valid only for point_light.",
        {
            "primitive": {"type": "string", "enum": sorted(PRIMITIVES)},
            "name": {"type": "string", "minLength": 1, "description": "Unique Blender object name."},
            "location": VECTOR3_SCHEMA,
            "rotation": VECTOR3_SCHEMA,
            "scale": VECTOR3_SCHEMA,
            "dimensions": {**VECTOR3_SCHEMA, "items": {"type": "number", "exclusiveMinimum": 0}, "description": "Final width/depth/height in positive meters."},
            "semantic_type": {"type": "string", "minLength": 1},
            "collection": {"type": "string", "minLength": 1},
            "display_size": {"type": "number", "exclusiveMinimum": 0},
            "light": {
                "type": "object",
                "properties": {"color": COLOR3_SCHEMA, "energy": {"type": "number", "minimum": 0, "description": "Light power in Blender watts."}, "size": {"type": "number", "exclusiveMinimum": 0}},
                "additionalProperties": False,
            },
        },
        ["primitive", "name"],
    ),
    _tool(
        "blender_transform_object",
        "Update only supplied transform fields. Prefer stable target_uuid; target_name is a readable fallback. Location/dimensions are meters, rotation is Euler radians, scale is unitless.",
        {
            "target_name": {"type": "string", "minLength": 1},
            "target_uuid": {"type": "string", "minLength": 1},
            "location": VECTOR3_SCHEMA,
            "rotation": VECTOR3_SCHEMA,
            "scale": VECTOR3_SCHEMA,
            "dimensions": {**VECTOR3_SCHEMA, "items": {"type": "number", "exclusiveMinimum": 0}},
            "look_at": LOOK_AT_SCHEMA,
        },
        [],
        any_of=[{"required": ["target_uuid"]}, {"required": ["target_name"]}],
    ),
    _tool("blender_rename_object", "Rename an existing Blender object. The old name stops resolving after success.", {"target_name": {"type": "string", "minLength": 1}, "new_name": {"type": "string", "minLength": 1}}, ["target_name", "new_name"]),
    _tool("blender_delete_object", "Delete exactly one existing Blender object by name. Does not clear unrelated scene objects.", {"target_name": {"type": "string", "minLength": 1}}, ["target_name"], destructive=True, idempotent=False),
    _tool(
        "blender_assign_material",
        "Create or reuse a basic Principled BSDF material and assign it to an existing mesh. Colors use linear RGBA in [0,1].",
        MATERIAL_PROPERTIES,
        ["material_name", "base_color", "roughness", "metallic"],
        any_of=[{"required": ["target_uuid"]}, {"required": ["target_name"]}],
    ),
    _tool(
        "blender_set_point_light",
        "Update color and/or energy on an existing point-light object. Color is linear RGB [0,1]; energy is non-negative Blender watts.",
        {"target_name": {"type": "string", "minLength": 1}, "color": COLOR3_SCHEMA, "energy": {"type": "number", "minimum": 0}},
        ["target_name"],
    ),
    _tool(
        "blender_create_curve",
        "Create a general 3D polyline or Bezier curve. Points and bevel depth are meters. Cyclic curves form closed loops; this is a general curve tool, not a logo generator.",
        {
            "name": {"type": "string", "minLength": 1},
            "points": {"type": "array", "minItems": 2, "items": VECTOR3_SCHEMA},
            "curve_type": {"type": "string", "enum": ["bezier", "poly"]},
            "cyclic": {"type": "boolean"},
            "bevel_depth": {"type": "number", "minimum": 0},
            "bevel_resolution": {"type": "integer", "minimum": 0, "maximum": 12},
            "fill_mode": {"type": "string", "enum": ["FULL", "HALF", "BACK", "FRONT"]},
            "location": VECTOR3_SCHEMA,
            "rotation": VECTOR3_SCHEMA,
            "scale": VECTOR3_SCHEMA,
            "collection": {"type": "string", "minLength": 1},
            "semantic_type": {"type": "string", "minLength": 1},
        },
        ["name", "points"],
    ),
    _tool(
        "blender_create_camera",
        "Create and activate a camera. Location is meters, focal_length is millimeters, and look_at accepts a target point or object name.",
        {
            "name": {"type": "string", "minLength": 1},
            "location": VECTOR3_SCHEMA,
            "focal_length": {"type": "number", "exclusiveMinimum": 0},
            "look_at": LOOK_AT_SCHEMA,
            "collection": {"type": "string", "minLength": 1},
            "active": {"type": "boolean"},
        },
        ["name", "location", "look_at"],
    ),
    _tool(
        "blender_set_light",
        "Update color, energy, and optional area size on an existing Point or Area light.",
        {"target_name": {"type": "string", "minLength": 1}, "color": COLOR3_SCHEMA, "energy": {"type": "number", "minimum": 0}, "size": {"type": "number", "exclusiveMinimum": 0}},
        ["target_name"],
    ),
    _tool(
        "blender_set_parent",
        "Parent one existing object to another while preserving its world transform by default.",
        {"target_name": {"type": "string", "minLength": 1}, "parent_name": {"type": "string", "minLength": 1}, "keep_transform": {"type": "boolean"}},
        ["target_name", "parent_name"],
    ),
    _tool(
        "blender_configure_world",
        "Set the Blender World background color and strength using linear RGB values.",
        {"color": COLOR3_SCHEMA, "strength": {"type": "number", "minimum": 0}},
        ["color", "strength"],
    ),
    _tool(
        "blender_configure_scene",
        "Configure a bounded Eevee render scene: square or rectangular resolution, samples, transparency, FPS, and timeline range.",
        {
            "engine": {"type": "string", "enum": ["BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"]},
            "resolution_x": {"type": "integer", "minimum": 64, "maximum": 2048},
            "resolution_y": {"type": "integer", "minimum": 64, "maximum": 2048},
            "samples": {"type": "integer", "minimum": 1, "maximum": 1024},
            "transparent": {"type": "boolean"},
            "fps": {"type": "integer", "minimum": 1, "maximum": 120},
            "frame_start": {"type": "integer", "minimum": 0},
            "frame_end": {"type": "integer", "minimum": 1},
        },
        ["engine", "resolution_x", "resolution_y", "samples", "transparent", "fps", "frame_start", "frame_end"],
    ),
    _tool(
        "blender_keyframe_object",
        "Insert transform and/or Principled emission-strength keyframes. Animation is evaluated by Blender Timeline; cycle adds a cycles modifier when supported.",
        {
            "target_name": {"type": "string", "minLength": 1},
            "keyframes": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "properties": {"frame": {"type": "integer", "minimum": 0}, "location": VECTOR3_SCHEMA, "rotation": VECTOR3_SCHEMA, "scale": VECTOR3_SCHEMA, "emission_strength": {"type": "number", "minimum": 0}},
                    "required": ["frame"],
                    "additionalProperties": False,
                },
            },
            "interpolation": {"type": "string", "enum": ["BEZIER", "LINEAR"]},
            "cycle": {"type": "boolean"},
        },
        ["target_name", "keyframes"],
    ),
    _tool(
        "blender_render",
        "Render a still PNG or an animation MP4 under CODEX3D_ARTIFACT_ROOT. Returns only validated relative paths and render statistics; still PNG may also be returned as MCP image content.",
        {"kind": {"type": "string", "enum": ["still", "animation"]}, "path": {"type": "string", "minLength": 1}},
        ["kind", "path"],
        destructive=False,
        idempotent=True,
    ),
    _tool(
        "blender_save_checkpoint",
        "Create a new, versioned .blend delivery under CODEX3D_ARTIFACT_ROOT. The tool never overwrites an existing file and verifies that saving did not change the live scene.",
        {"path": {"type": "string", "minLength": 1}},
        ["path"],
        destructive=False,
        idempotent=False,
    ),
    _tool(
        "blender_create_snapshot",
        "Create a restorable .blend snapshot under CODEX3D_ARTIFACT_ROOT with a canonical scene fingerprint and stable object UUID inventory.",
        {"snapshot_id": {"type": "string", "pattern": "^snapshot_[A-Za-z0-9_]+$"}, "source_action_id": {"type": "string"}, "source_turn": {"type": "string"}},
        destructive=False,
        idempotent=False,
    ),
    {"name": "blender_list_snapshots", "description": "List snapshots stored inside the configured artifact root. Takes no arguments.", "annotations": _annotations(read_only=True, destructive=False, idempotent=True), "inputSchema": EMPTY_SCHEMA},
    _tool(
        "blender_restore_snapshot",
        "Reversibly restore a snapshot registered by the current session. Requires the live and target fingerprints, creates a non-overwriting pre-restore safety snapshot first, then returns inspection and scene diff.",
        {
            "snapshot_id": {"type": "string", "pattern": "^snapshot_[A-Za-z0-9_]+$"},
            "current_fingerprint": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
            "snapshot_fingerprint": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
        },
        ["snapshot_id", "current_fingerprint", "snapshot_fingerprint"],
        destructive=False,
        idempotent=False,
    ),
    _tool("blender_delete_snapshot", "Delete one snapshot .blend and metadata record from the configured artifact root.", {"snapshot_id": {"type": "string", "pattern": "^snapshot_[A-Za-z0-9_]+$"}}, ["snapshot_id"], destructive=True),
    _tool("blender_reconcile_object_ids", "Assign stable codex3d_uuid properties to legacy objects with an explicit name prefix. Does not rename or modify geometry.", {"prefix": {"type": "string", "minLength": 1}}, ["prefix"], destructive=True, idempotent=True),
    _tool(
        "blender_execute_batch",
        "Execute an ordered, fail-fast batch of allowlisted Codex3D Action objects, then inspect the final scene. Supports creation, transform, material, parenting, scene/world configuration, keyframes, render, and checkpoint actions.",
        {
            "actions": {
                "type": "array",
                "minItems": 1,
                "maxItems": 100,
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": sorted(item.value for item in (
                            ActionType.CREATE_OBJECT,
                            ActionType.TRANSFORM_OBJECT,
                            ActionType.MODIFY_OBJECT,
                            ActionType.DELETE_OBJECT,
                            ActionType.ASSIGN_MATERIAL,
                            ActionType.SET_PARENT,
                            ActionType.CONFIGURE_WORLD,
                            ActionType.CONFIGURE_SCENE,
                            ActionType.KEYFRAME_OBJECT,
                            ActionType.RENDER_PREVIEW,
                            ActionType.SAVE_CHECKPOINT,
                            ActionType.SNAPSHOT_SCENE,
                            ActionType.LIST_SNAPSHOTS,
                            ActionType.RESTORE_SNAPSHOT,
                            ActionType.DELETE_SNAPSHOT,
                            ActionType.RECONCILE_OBJECT_IDS,
                        ))},
                        "description": {"type": "string"},
                        "parameters": {"type": "object"},
                        "metadata": {"type": "object"},
                    },
                    "required": ["type", "parameters"],
                    "additionalProperties": False,
                },
            }
        },
        ["actions"],
        destructive=True,
    ),
]


class McpToolService:
    def __init__(
        self,
        config: BridgeConfig | None = None,
        client_factory: Callable[[BridgeConfig], Any] | None = None,
    ) -> None:
        self.config = config or BridgeConfig.from_env()
        self.client_factory = client_factory or self._default_client

    def list_tools(self) -> list[dict[str, Any]]:
        return TOOL_DEFINITIONS

    def call_tool(self, name: str, arguments: Any) -> dict[str, Any]:
        try:
            args = require_object(arguments)
            handler = getattr(self, f"_call_{name}", None)
            if handler is None:
                raise ToolValidationError("Unknown MCP tool.", details={"tool": name})
            return self._scrub(handler(args))
        except ToolValidationError as exc:
            return self._error("invalid_arguments", str(exc), exc.details)
        except ConfigurationError as exc:
            return self._error("configuration_error", str(exc))
        except ConnectorTransportError as exc:
            return self._error(exc.error.code.value, exc.error.message, exc.error.details)
        except Exception as exc:  # defensive MCP boundary
            return self._error("internal_error", f"MCP tool failed: {exc}")

    def _call_blender_ping(self, args: dict[str, Any]) -> dict[str, Any]:
        reject_unknown(args, set())
        return self._with_client(lambda client: {"ok": True, "tool": "blender_ping", "bridge": client.hello(), "ping": client.ping()})

    def _call_blender_inspect_scene(self, args: dict[str, Any]) -> dict[str, Any]:
        reject_unknown(args, {"mode", "collection", "object_uuid", "semantic_group", "scene_name"})
        mode = args.get("mode", "compact")
        if mode not in {"compact", "full"}:
            raise ToolValidationError("mode must be compact or full.")

        def inspect(client) -> dict[str, Any]:
            full = to_dict(client.inspect_scene())
            return {
                "ok": True,
                "tool": "blender_inspect_scene",
                "inspection": full if mode == "full" else _compact_inspection(full, args),
            }

        return self._with_client(inspect)

    def _call_blender_create_primitive(self, args: dict[str, Any]) -> dict[str, Any]:
        allowed = {"primitive", "name", "location", "rotation", "scale", "dimensions", "semantic_type", "light", "collection", "display_size"}
        reject_unknown(args, allowed)
        action = Action(type=ActionType.CREATE_OBJECT, description="Create primitive through Codex3D MCP.", parameters=dict(args), metadata={"source": "codex3d_mcp"})
        validate_action_shape(action)
        return self._execute_one("blender_create_primitive", action)

    def _call_blender_transform_object(self, args: dict[str, Any]) -> dict[str, Any]:
        reject_unknown(args, {"target_name", "target_uuid", "location", "rotation", "scale", "dimensions", "look_at"})
        self._target_parameters(args)
        action = Action(type=ActionType.TRANSFORM_OBJECT, description="Transform object through Codex3D MCP.", parameters=dict(args), metadata={"source": "codex3d_mcp"})
        validate_action_shape(action)
        return self._execute_one("blender_transform_object", action)

    def _call_blender_rename_object(self, args: dict[str, Any]) -> dict[str, Any]:
        reject_unknown(args, {"target_name", "new_name"})
        action = Action(type=ActionType.MODIFY_OBJECT, parameters={"target_name": require_name(args, "target_name"), "new_name": require_name(args, "new_name")}, metadata={"source": "codex3d_mcp"})
        return self._execute_one("blender_rename_object", action)

    def _call_blender_delete_object(self, args: dict[str, Any]) -> dict[str, Any]:
        reject_unknown(args, {"target_name"})
        action = Action(type=ActionType.DELETE_OBJECT, parameters={"target_name": require_name(args, "target_name")}, metadata={"source": "codex3d_mcp"})
        return self._execute_one("blender_delete_object", action)

    def _call_blender_assign_material(self, args: dict[str, Any]) -> dict[str, Any]:
        reject_unknown(args, set(MATERIAL_PROPERTIES))
        parameters = {
            **self._target_parameters(args),
            "material": self._material_parameters(args),
        }
        return self._execute_one("blender_assign_material", Action(type=ActionType.ASSIGN_MATERIAL, parameters=parameters, metadata={"source": "codex3d_mcp"}))

    def _call_blender_set_point_light(self, args: dict[str, Any]) -> dict[str, Any]:
        reject_unknown(args, {"target_name", "color", "energy"})
        target_name = require_name(args, "target_name")
        light: dict[str, Any] = {}
        if "color" in args:
            light["color"] = color(args["color"], "color", 3)
        if "energy" in args:
            energy = finite_number(args["energy"], "energy")
            if energy < 0:
                raise ToolValidationError("energy must be non-negative.")
            light["energy"] = energy
        if not light:
            raise ToolValidationError("Provide color and/or energy.")
        return self._execute_one("blender_set_point_light", Action(type=ActionType.MODIFY_OBJECT, parameters={"target_name": target_name, "light": light}, metadata={"source": "codex3d_mcp"}))

    def _call_blender_create_curve(self, args: dict[str, Any]) -> dict[str, Any]:
        allowed = {"name", "points", "curve_type", "cyclic", "bevel_depth", "bevel_resolution", "fill_mode", "location", "rotation", "scale", "collection", "semantic_type"}
        reject_unknown(args, allowed)
        parameters = {"primitive": "curve", **args}
        action = Action(type=ActionType.CREATE_OBJECT, parameters=parameters, metadata={"source": "codex3d_mcp"})
        validate_action_shape(action)
        return self._execute_one("blender_create_curve", action)

    def _call_blender_create_camera(self, args: dict[str, Any]) -> dict[str, Any]:
        reject_unknown(args, {"name", "location", "focal_length", "look_at", "collection", "active"})
        if "location" not in args or "look_at" not in args:
            raise ToolValidationError("Camera requires location and look_at.")
        parameters = {"primitive": "camera", **args, "semantic_type": "render_camera"}
        action = Action(type=ActionType.CREATE_OBJECT, parameters=parameters, metadata={"source": "codex3d_mcp"})
        validate_action_shape(action)
        return self._execute_one("blender_create_camera", action)

    def _call_blender_set_light(self, args: dict[str, Any]) -> dict[str, Any]:
        reject_unknown(args, {"target_name", "color", "energy", "size"})
        target_name = require_name(args, "target_name")
        light: dict[str, Any] = {}
        if "color" in args:
            light["color"] = color(args["color"], "color", 3)
        for field in ("energy", "size"):
            if field in args:
                number = finite_number(args[field], field)
                if number < 0 or (field == "size" and number <= 0):
                    raise ToolValidationError(f"{field} is outside its allowed range.")
                light[field] = number
        if not light:
            raise ToolValidationError("Provide color, energy, and/or size.")
        return self._execute_one("blender_set_light", Action(type=ActionType.MODIFY_OBJECT, parameters={"target_name": target_name, "light": light}, metadata={"source": "codex3d_mcp"}))

    def _call_blender_set_parent(self, args: dict[str, Any]) -> dict[str, Any]:
        reject_unknown(args, {"target_name", "parent_name", "keep_transform"})
        parameters = {
            "target_name": require_name(args, "target_name"),
            "parent_name": require_name(args, "parent_name"),
            "keep_transform": bool(args.get("keep_transform", True)),
        }
        return self._execute_one("blender_set_parent", Action(type=ActionType.SET_PARENT, parameters=parameters, metadata={"source": "codex3d_mcp"}))

    def _call_blender_configure_world(self, args: dict[str, Any]) -> dict[str, Any]:
        reject_unknown(args, {"color", "strength"})
        strength = finite_number(args.get("strength"), "strength")
        if strength < 0:
            raise ToolValidationError("strength must be non-negative.")
        parameters = {"color": color(args.get("color"), "color", 3), "strength": strength}
        return self._execute_one("blender_configure_world", Action(type=ActionType.CONFIGURE_WORLD, parameters=parameters, metadata={"source": "codex3d_mcp"}))

    def _call_blender_configure_scene(self, args: dict[str, Any]) -> dict[str, Any]:
        reject_unknown(args, {"engine", "resolution_x", "resolution_y", "samples", "transparent", "fps", "frame_start", "frame_end"})
        action = Action(type=ActionType.CONFIGURE_SCENE, parameters=dict(args), metadata={"source": "codex3d_mcp"})
        validate_action_shape(action)
        return self._execute_one("blender_configure_scene", action)

    def _call_blender_keyframe_object(self, args: dict[str, Any]) -> dict[str, Any]:
        reject_unknown(args, {"target_name", "keyframes", "interpolation", "cycle"})
        action = Action(type=ActionType.KEYFRAME_OBJECT, parameters=dict(args), metadata={"source": "codex3d_mcp"})
        validate_action_shape(action)
        return self._execute_one("blender_keyframe_object", action)

    def _call_blender_render(self, args: dict[str, Any]) -> dict[str, Any]:
        reject_unknown(args, {"kind", "path"})
        action = Action(type=ActionType.RENDER_PREVIEW, parameters=dict(args), metadata={"source": "codex3d_mcp"})
        payload = self._execute_one("blender_render", action)
        if payload.get("ok") and args.get("kind") == "still":
            relative = payload.get("result", {}).get("output", {}).get("path")
            image = self._read_mcp_image(relative)
            if image is not None:
                payload["_mcp_image"] = image
        return payload

    def _call_blender_save_checkpoint(self, args: dict[str, Any]) -> dict[str, Any]:
        reject_unknown(args, {"path"})
        action = Action(type=ActionType.SAVE_CHECKPOINT, parameters=dict(args), metadata={"source": "codex3d_mcp"})
        return self._execute_one("blender_save_checkpoint", action)

    def _call_blender_create_snapshot(self, args: dict[str, Any]) -> dict[str, Any]:
        reject_unknown(args, {"snapshot_id", "source_action_id", "source_turn"})
        action = Action(type=ActionType.SNAPSHOT_SCENE, parameters=dict(args), metadata={"source": "codex3d_mcp"})
        return self._execute_one("blender_create_snapshot", action)

    def _call_blender_list_snapshots(self, args: dict[str, Any]) -> dict[str, Any]:
        reject_unknown(args, set())
        return self._execute_one(
            "blender_list_snapshots",
            Action(type=ActionType.LIST_SNAPSHOTS, parameters={}, metadata={"source": "codex3d_mcp"}),
        )

    def _call_blender_restore_snapshot(self, args: dict[str, Any]) -> dict[str, Any]:
        reject_unknown(args, {"snapshot_id", "current_fingerprint", "snapshot_fingerprint"})
        action = Action(
            type=ActionType.RESTORE_SNAPSHOT,
            parameters={
                "snapshot_id": require_name(args, "snapshot_id"),
                "current_fingerprint": require_name(args, "current_fingerprint"),
                "snapshot_fingerprint": require_name(args, "snapshot_fingerprint"),
            },
            metadata={"source": "codex3d_mcp"},
        )
        return self._execute_one("blender_restore_snapshot", action)

    def _call_blender_delete_snapshot(self, args: dict[str, Any]) -> dict[str, Any]:
        reject_unknown(args, {"snapshot_id"})
        action = Action(
            type=ActionType.DELETE_SNAPSHOT,
            parameters={"snapshot_id": require_name(args, "snapshot_id")},
            metadata={"source": "codex3d_mcp"},
        )
        return self._execute_one("blender_delete_snapshot", action)

    def _call_blender_reconcile_object_ids(self, args: dict[str, Any]) -> dict[str, Any]:
        reject_unknown(args, {"prefix"})
        action = Action(
            type=ActionType.RECONCILE_OBJECT_IDS,
            parameters={"prefix": require_name(args, "prefix")},
            metadata={"source": "codex3d_mcp"},
        )
        return self._execute_one("blender_reconcile_object_ids", action)

    def _call_blender_execute_batch(self, args: dict[str, Any]) -> dict[str, Any]:
        reject_unknown(args, {"actions"})
        raw_actions = args.get("actions")
        if not isinstance(raw_actions, list) or not raw_actions or len(raw_actions) > 100:
            raise ToolValidationError("actions must contain between 1 and 100 Action objects.")
        actions = [validate_action_data(item, index) for index, item in enumerate(raw_actions)]

        def execute(client):
            batch = client.execute_action_batch(actions)
            inspection = client.inspect_scene()
            payload = {
                "ok": int(batch.get("failed_count", 0)) == 0,
                "tool": "blender_execute_batch",
                "actions": to_dict(actions),
                "results": to_dict(batch.get("results", [])),
                "executed_count": int(batch.get("executed_count", 0)),
                "succeeded_count": int(batch.get("succeeded_count", 0)),
                "failed_count": int(batch.get("failed_count", 0)),
                "unexecuted_count": int(batch.get("unexecuted_count", 0)),
                "inspection": to_dict(inspection),
            }
            if not payload["ok"]:
                payload["error"] = {"code": "action_failed", "message": "Batch stopped after the first failed action."}
            return payload

        return self._with_client(execute)

    def _execute_one(self, tool_name: str, action: Action) -> dict[str, Any]:
        validate_action_shape(action)

        def execute(client):
            result = client.execute_action(action)
            ok = result.status is ActionStatus.SUCCEEDED
            payload = {"ok": ok, "tool": tool_name, "action": to_dict(action), "result": to_dict(result)}
            if not ok:
                payload["error"] = to_dict(result.error or ProtocolError(code=ErrorCode.ACTION_FAILED, message="Blender action failed."))
            return payload

        return self._with_client(execute)

    def _with_client(self, operation):
        self.config.require_token()
        client = self.client_factory(self.config)
        try:
            return operation(client)
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                close()

    def _default_client(self, config: BridgeConfig) -> SocketConnectorClient:
        return SocketConnectorClient(
            host=config.host,
            port=config.port,
            token=config.token,
            connect_timeout=config.connect_timeout,
            request_timeout=config.request_timeout,
        )

    def _material_parameters(self, args: dict[str, Any]) -> dict[str, Any]:
        material = {
            "name": require_name(args, "material_name"),
            "base_color": color(args.get("base_color"), "base_color", 4),
            "roughness": unit_number(args.get("roughness"), "roughness"),
            "metallic": unit_number(args.get("metallic"), "metallic"),
        }
        if "emission_color" in args:
            material["emission_color"] = color(args["emission_color"], "emission_color", 4)
        if "emission_strength" in args:
            strength = finite_number(args["emission_strength"], "emission_strength")
            if strength < 0:
                raise ToolValidationError("emission_strength must be non-negative.")
            material["emission_strength"] = strength
        for field in ("transmission", "alpha"):
            if field in args:
                material[field] = unit_number(args[field], field)
        return material

    def _target_parameters(self, args: dict[str, Any]) -> dict[str, str]:
        if isinstance(args.get("target_uuid"), str) and args["target_uuid"]:
            return {"target_uuid": args["target_uuid"]}
        return {"target_name": require_name(args, "target_name")}

    def _read_mcp_image(self, relative: Any) -> dict[str, str] | None:
        if not self.config.include_images or self.config.artifact_root is None or not isinstance(relative, str):
            return None
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts or candidate.suffix.lower() != ".png":
            return None
        root = self.config.artifact_root.resolve()
        path = (root / candidate).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            return None
        if not path.is_file():
            return None
        return {"type": "image", "mimeType": "image/png", "data": base64.b64encode(path.read_bytes()).decode("ascii")}

    def _error(self, code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._scrub({"ok": False, "error": {"code": code, "message": message, "details": details or {}}})

    def _scrub(self, value: Any) -> Any:
        if isinstance(value, str):
            return value.replace(self.config.token, "[REDACTED]") if self.config.token else value
        if isinstance(value, list):
            return [self._scrub(item) for item in value]
        if isinstance(value, dict):
            return {str(key): self._scrub(item) for key, item in value.items() if str(key).lower() not in {"token", "auth_token"}}
        return value


def _compact_inspection(full: dict[str, Any], filters: dict[str, Any]) -> dict[str, Any]:
    scene = full.get("scene", {})
    metadata = scene.get("metadata", {})
    objects = list(scene.get("objects", []))
    collection = filters.get("collection")
    object_uuid = filters.get("object_uuid")
    semantic_group = filters.get("semantic_group")
    scene_name = filters.get("scene_name")
    if scene_name and scene.get("name") != scene_name:
        objects = []
    if collection:
        objects = [
            item for item in objects
            if collection in item.get("metadata", {}).get("collections", [])
            or item.get("metadata", {}).get("collection") == collection
        ]
    if object_uuid:
        objects = [item for item in objects if item.get("blender_uuid") == object_uuid]
    if semantic_group:
        lowered = semantic_group.lower()
        objects = [
            item for item in objects
            if str(item.get("semantic_type", "")).lower() == lowered
            or lowered in str(item.get("label", "")).lower()
        ]

    type_counts: dict[str, int] = {}
    materials: set[str] = set()
    lights: list[dict[str, Any]] = []
    visible_ids: list[str] = []
    pairs: list[dict[str, Any]] = []
    for item in objects:
        item_type = str(item.get("semantic_type", "object"))
        type_counts[item_type] = type_counts.get(item_type, 0) + 1
        uuid = item.get("blender_uuid")
        pairs.append({"uuid": uuid, "name": item.get("label"), "type": item_type})
        material = item.get("metadata", {}).get("material_name")
        if material:
            materials.add(material)
        if item_type == "light":
            lights.append({"uuid": uuid, "name": item.get("label"), "light": item.get("metadata", {}).get("light")})
        if item_type in {"mesh", "curve"} and uuid:
            visible_ids.append(uuid)

    result = {
        "mode": "compact",
        "scene_name": scene.get("name"),
        "target_collection": collection or metadata.get("target_collection"),
        "object_count": len(objects),
        "type_counts": type_counts,
        "objects": pairs,
        "active_camera": metadata.get("active_camera"),
        "materials": sorted(materials),
        "lights": lights,
        "animation": {
            "frame_start": metadata.get("frame_start"),
            "frame_end": metadata.get("frame_end"),
            "keyframe_count": metadata.get("keyframe_count"),
        },
        "accepted_snapshot": {
            "snapshot_id": metadata.get("accepted_snapshot_id"),
            "fingerprint": metadata.get("accepted_snapshot_fingerprint"),
        },
        "scene_fingerprint": metadata.get("scene_fingerprint") or full.get("metadata", {}).get("scene_fingerprint"),
        "visible_renderable_object_ids": visible_ids,
        "warnings": metadata.get("warnings", []),
        "recent_scene_diff": metadata.get("recent_scene_diff"),
    }
    if object_uuid and objects:
        result["object_detail"] = objects[0]
    return result
