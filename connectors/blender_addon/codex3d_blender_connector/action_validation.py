from __future__ import annotations

import math
from typing import Any

from .protocol_compat import Action, ActionType, ErrorCode, ProtocolError

SUPPORTED_PRIMITIVES = {
    "cube",
    "cylinder",
    "sphere",
    "plane",
    "point_light",
    "area_light",
    "curve",
    "camera",
    "empty",
}
TRANSFORM_VECTOR_FIELDS = {"location", "rotation", "scale"}


class ActionValidationError(ValueError):
    def __init__(
        self,
        message: str,
        *,
        code: ErrorCode = ErrorCode.INVALID_SCHEMA,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.protocol_error = ProtocolError(
            code=code,
            message=message,
            source="codex3d_blender_connector.action_validation",
            details=details or {},
        )
        super().__init__(message)


def validate_action_parameters(action: Action, object_exists) -> None:
    params = action.parameters
    if action.type is ActionType.CREATE_OBJECT:
        _validate_create(params)
        return

    if action.type is ActionType.TRANSFORM_OBJECT:
        target = _require_target(params)
        _require_existing_target(target, object_exists)
        _validate_transform(params, require_any_transform=True)
        return

    if action.type is ActionType.MODIFY_OBJECT:
        target = _require_target(params)
        _require_existing_target(target, object_exists)
        _validate_modify(params)
        return

    if action.type is ActionType.DELETE_OBJECT:
        target = _require_target(params)
        _require_existing_target(target, object_exists)
        return

    if action.type is ActionType.ASSIGN_MATERIAL:
        target = _require_target(params)
        _require_existing_target(target, object_exists)
        _validate_material(params.get("material"))
        return

    if action.type is ActionType.SET_PARENT:
        target_name = _require_target(params)
        _require_existing_target(target_name, object_exists)
        parent_name = params.get("parent_name")
        if not isinstance(parent_name, str) or not parent_name:
            raise ActionValidationError("SET_PARENT requires parent_name.")
        _require_existing_target(parent_name, object_exists)
        if parent_name == target_name:
            raise ActionValidationError("An object cannot parent itself.")
        return

    if action.type is ActionType.CONFIGURE_WORLD:
        _validate_color(params.get("color"), "world.color", length=3)
        _validate_nonnegative(params.get("strength"), "world.strength")
        return

    if action.type is ActionType.CONFIGURE_SCENE:
        _validate_scene(params)
        return

    if action.type is ActionType.KEYFRAME_OBJECT:
        target_name = _require_target(params)
        _require_existing_target(target_name, object_exists)
        _validate_keyframes(params)
        return

    if action.type is ActionType.RENDER_PREVIEW:
        _validate_artifact_relative_path(params.get("path"), {".png", ".mp4"})
        if params.get("kind", "still") not in {"still", "animation"}:
            raise ActionValidationError("render kind must be still or animation.")
        return

    if action.type is ActionType.SAVE_CHECKPOINT:
        _validate_artifact_relative_path(params.get("path"), {".blend"})
        return

    if action.type is ActionType.SNAPSHOT_SCENE:
        snapshot_id = params.get("snapshot_id")
        if snapshot_id is not None and (not isinstance(snapshot_id, str) or not snapshot_id):
            raise ActionValidationError("snapshot_id must be a non-empty string when supplied.")
        return

    if action.type is ActionType.RESTORE_SNAPSHOT:
        if not isinstance(params.get("snapshot_id"), str) or not params["snapshot_id"]:
            raise ActionValidationError("snapshot_id is required.")
        for field in ("current_fingerprint", "snapshot_fingerprint"):
            value = params.get(field)
            if not isinstance(value, str) or len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
                raise ActionValidationError(f"{field} must be a lowercase SHA-256 fingerprint.")
        return

    if action.type is ActionType.DELETE_SNAPSHOT:
        if not isinstance(params.get("snapshot_id"), str) or not params["snapshot_id"]:
            raise ActionValidationError("snapshot_id is required.")
        return

    if action.type is ActionType.LIST_SNAPSHOTS:
        return

    if action.type is ActionType.RECONCILE_OBJECT_IDS:
        prefix = params.get("prefix", "C3D_")
        if not isinstance(prefix, str) or not prefix:
            raise ActionValidationError("reconcile prefix must be a non-empty string.")
        return

    raise ActionValidationError(
        f"Unsupported action type for Blender executor: {action.type.value}",
        code=ErrorCode.UNSUPPORTED_OPERATION,
        details={"action_type": action.type.value},
    )


def _validate_create(params: dict[str, Any]) -> None:
    primitive = params.get("primitive")
    if primitive not in SUPPORTED_PRIMITIVES:
        raise ActionValidationError(
            f"Unknown primitive: {primitive}",
            details={"primitive": primitive, "supported": sorted(SUPPORTED_PRIMITIVES)},
        )

    if not params.get("name"):
        raise ActionValidationError("CREATE_OBJECT requires a non-empty name.")

    _validate_transform(params)
    if "dimensions" in params:
        _validate_dimensions(params["dimensions"])

    if primitive in {"point_light", "area_light"}:
        _validate_light(params.get("light", {}), require_any=False)
        if primitive == "area_light" and "size" in params.get("light", {}):
            _validate_nonnegative(params["light"]["size"], "light.size", positive=True)
    elif "light" in params:
        raise ActionValidationError("light parameters are only valid for light objects.")
    if primitive == "curve":
        _validate_curve(params)
    if primitive == "camera":
        _validate_camera(params)


def _validate_transform(
    params: dict[str, Any],
    *,
    require_any_transform: bool = False,
) -> None:
    provided = False
    for field in TRANSFORM_VECTOR_FIELDS:
        if field in params:
            provided = True
            _validate_vector3(params[field], field)
    if "dimensions" in params:
        provided = True
        _validate_dimensions(params["dimensions"])
    if "look_at" in params:
        provided = True
        _validate_look_at(params["look_at"])
    if require_any_transform and not provided:
        raise ActionValidationError("TRANSFORM_OBJECT requires at least one transform field.")


def _validate_modify(params: dict[str, Any]) -> None:
    if "new_name" in params and not params["new_name"]:
        raise ActionValidationError("new_name must be non-empty when provided.")
    if "light" in params:
        _validate_light(params["light"], require_any=True)
    if "camera" in params:
        _validate_camera(params["camera"], require_name=False)
    if "new_name" not in params and "light" not in params and "camera" not in params:
        raise ActionValidationError("MODIFY_OBJECT requires new_name, light, or camera.")


def _validate_material(material: Any) -> None:
    if not isinstance(material, dict):
        raise ActionValidationError("ASSIGN_MATERIAL requires material object.")
    if not material.get("name"):
        raise ActionValidationError("material.name is required.")
    _validate_color(material.get("base_color"), "material.base_color", length=4)
    _validate_unit_number(material.get("roughness"), "material.roughness")
    _validate_unit_number(material.get("metallic"), "material.metallic")
    if "emission_color" in material:
        _validate_color(material["emission_color"], "material.emission_color", length=4)
    if "emission_strength" in material:
        _validate_nonnegative(material["emission_strength"], "material.emission_strength")
    if "transmission" in material:
        _validate_unit_number(material["transmission"], "material.transmission")
    if "alpha" in material:
        _validate_unit_number(material["alpha"], "material.alpha")


def _validate_light(light: Any, *, require_any: bool) -> None:
    if not isinstance(light, dict):
        raise ActionValidationError("light must be an object.")
    if require_any and not any(key in light for key in {"color", "energy", "size"}):
        raise ActionValidationError("light update requires color, energy, or size.")
    if "color" in light:
        _validate_color(light["color"], "light.color", length=3)
    if "energy" in light:
        _validate_nonnegative(light["energy"], "light.energy")
    if "size" in light:
        _validate_nonnegative(light["size"], "light.size", positive=True)


def _validate_curve(params: dict[str, Any]) -> None:
    points = params.get("points")
    if not isinstance(points, list) or len(points) < 2:
        raise ActionValidationError("curve.points requires at least two 3D points.")
    for point in points:
        _validate_vector3(point, "curve.points")
    if params.get("curve_type", "bezier") not in {"poly", "bezier"}:
        raise ActionValidationError("curve_type must be poly or bezier.")
    if params.get("fill_mode", "FULL") not in {"FULL", "HALF", "BACK", "FRONT"}:
        raise ActionValidationError("fill_mode is unsupported.")
    _validate_nonnegative(params.get("bevel_depth", 0.02), "bevel_depth")
    resolution = params.get("bevel_resolution", 3)
    if not isinstance(resolution, int) or isinstance(resolution, bool) or not 0 <= resolution <= 12:
        raise ActionValidationError("bevel_resolution must be an integer in [0, 12].")
    if "cyclic" in params and not isinstance(params["cyclic"], bool):
        raise ActionValidationError("cyclic must be boolean.")


def _validate_camera(params: dict[str, Any], *, require_name: bool = True) -> None:
    if require_name and not params.get("name"):
        raise ActionValidationError("camera name is required.")
    if "focal_length" in params:
        _validate_nonnegative(params["focal_length"], "camera.focal_length", positive=True)
    if "look_at" in params:
        _validate_look_at(params["look_at"])


def _validate_look_at(value: Any) -> None:
    if isinstance(value, str) and value:
        return
    _validate_vector3(value, "look_at")


def _validate_scene(params: dict[str, Any]) -> None:
    if params.get("engine", "BLENDER_EEVEE") not in {"BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"}:
        raise ActionValidationError("Only Blender Eevee engines are supported in this sprint.")
    for field in ("resolution_x", "resolution_y"):
        value = params.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or not 64 <= value <= 2048:
            raise ActionValidationError(f"{field} must be an integer in [64, 2048].")
    samples = params.get("samples", 32)
    if not isinstance(samples, int) or isinstance(samples, bool) or not 1 <= samples <= 1024:
        raise ActionValidationError("samples must be an integer in [1, 1024].")
    fps = params.get("fps", 24)
    if not isinstance(fps, int) or isinstance(fps, bool) or not 1 <= fps <= 120:
        raise ActionValidationError("fps must be an integer in [1, 120].")
    frame_start = params.get("frame_start", 1)
    frame_end = params.get("frame_end", 72)
    if not isinstance(frame_start, int) or not isinstance(frame_end, int) or frame_end < frame_start:
        raise ActionValidationError("frame range is invalid.")
    if "transparent" in params and not isinstance(params["transparent"], bool):
        raise ActionValidationError("transparent must be boolean.")


def _validate_keyframes(params: dict[str, Any]) -> None:
    keyframes = params.get("keyframes")
    if not isinstance(keyframes, list) or len(keyframes) < 1:
        raise ActionValidationError("keyframes must be a non-empty list.")
    for item in keyframes:
        if not isinstance(item, dict) or not isinstance(item.get("frame"), int):
            raise ActionValidationError("Each keyframe requires an integer frame.")
        present = False
        for field in TRANSFORM_VECTOR_FIELDS:
            if field in item:
                present = True
                _validate_vector3(item[field], f"keyframe.{field}")
        if "emission_strength" in item:
            present = True
            _validate_nonnegative(item["emission_strength"], "keyframe.emission_strength")
        if not present:
            raise ActionValidationError("Each keyframe requires transform or emission data.")
    if params.get("interpolation", "BEZIER") not in {"BEZIER", "LINEAR"}:
        raise ActionValidationError("interpolation must be BEZIER or LINEAR.")
    if "cycle" in params and not isinstance(params["cycle"], bool):
        raise ActionValidationError("cycle must be boolean.")


def _validate_artifact_relative_path(value: Any, suffixes: set[str]) -> None:
    if not isinstance(value, str) or not value:
        raise ActionValidationError("path must be a non-empty relative artifact path.")
    from pathlib import PurePosixPath

    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.suffix.lower() not in suffixes:
        raise ActionValidationError("path must stay inside the artifact root with an allowed extension.")


def _validate_nonnegative(value: Any, field_name: str, *, positive: bool = False) -> None:
    _validate_finite_number(value, field_name)
    if value < 0 or (positive and value <= 0):
        qualifier = "positive" if positive else "non-negative"
        raise ActionValidationError(f"{field_name} must be {qualifier}.")


def _require_target(params: dict[str, Any]) -> str:
    target = params.get("target_uuid") or params.get("target_name")
    if not isinstance(target, str) or not target:
        raise ActionValidationError("target_uuid or target_name is required.")
    return target


def _require_existing_target(target: str, object_exists) -> None:
    if not object_exists(target):
        raise ActionValidationError(
            f"Target object does not exist: {target}",
            code=ErrorCode.OBJECT_NOT_FOUND,
            details={"target": target},
        )


def _validate_vector3(value: Any, field_name: str) -> None:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ActionValidationError(f"{field_name} must be a three-element vector.")
    for item in value:
        _validate_finite_number(item, field_name)


def _validate_dimensions(value: Any) -> None:
    _validate_vector3(value, "dimensions")
    if any(item <= 0 for item in value):
        raise ActionValidationError("dimensions must contain positive numbers.")


def _validate_color(value: Any, field_name: str, *, length: int) -> None:
    if not isinstance(value, (list, tuple)) or len(value) != length:
        raise ActionValidationError(f"{field_name} must have {length} components.")
    for item in value:
        _validate_unit_number(item, field_name)


def _validate_unit_number(value: Any, field_name: str) -> None:
    _validate_finite_number(value, field_name)
    if value < 0 or value > 1:
        raise ActionValidationError(f"{field_name} must be in [0, 1].")


def _validate_finite_number(value: Any, field_name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ActionValidationError(f"{field_name} must be a number.")
    if not math.isfinite(float(value)):
        raise ActionValidationError(f"{field_name} must be finite.")
