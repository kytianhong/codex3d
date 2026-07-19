from __future__ import annotations

import math
from typing import Any

from codex3d_protocol import Action, ActionStatus, ActionType


PRIMITIVES = {"cube", "cylinder", "sphere", "plane", "point_light", "area_light", "empty"}
CREATABLE_OBJECTS = PRIMITIVES | {"curve", "camera"}
EXECUTABLE_ACTION_TYPES = {
    ActionType.CREATE_OBJECT,
    ActionType.TRANSFORM_OBJECT,
    ActionType.MODIFY_OBJECT,
    ActionType.DELETE_OBJECT,
    ActionType.ASSIGN_MATERIAL,
    ActionType.CONFIGURE_SCENE,
    ActionType.CONFIGURE_WORLD,
    ActionType.SET_PARENT,
    ActionType.KEYFRAME_OBJECT,
    ActionType.RENDER_PREVIEW,
    ActionType.SAVE_CHECKPOINT,
}


class ToolValidationError(ValueError):
    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


def require_object(arguments: Any) -> dict[str, Any]:
    if not isinstance(arguments, dict):
        raise ToolValidationError("Tool arguments must be a JSON object.")
    return arguments


def reject_unknown(arguments: dict[str, Any], allowed: set[str]) -> None:
    unknown = sorted(set(arguments) - allowed)
    if unknown:
        raise ToolValidationError("Unknown tool arguments.", details={"unknown": unknown})


def require_name(arguments: dict[str, Any], field: str) -> str:
    value = arguments.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ToolValidationError(f"{field} must be a non-empty string.")
    return value


def optional_vector(arguments: dict[str, Any], field: str, *, positive: bool = False) -> None:
    if field not in arguments:
        return
    vector(arguments[field], field, positive=positive)


def vector(value: Any, field: str, *, positive: bool = False) -> list[float]:
    if not isinstance(value, list) or len(value) != 3:
        raise ToolValidationError(f"{field} must be an array of exactly three finite numbers.")
    for item in value:
        finite_number(item, field)
        if positive and item <= 0:
            raise ToolValidationError(f"{field} values must be positive.")
    return value


def color(value: Any, field: str, length: int) -> list[float]:
    if not isinstance(value, list) or len(value) != length:
        raise ToolValidationError(f"{field} must contain exactly {length} numbers in [0, 1].")
    for item in value:
        finite_number(item, field)
        if item < 0 or item > 1:
            raise ToolValidationError(f"{field} values must be in [0, 1].")
    return value


def finite_number(value: Any, field: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise ToolValidationError(f"{field} must be a finite number.")
    return float(value)


def unit_number(value: Any, field: str) -> float:
    number = finite_number(value, field)
    if number < 0 or number > 1:
        raise ToolValidationError(f"{field} must be in [0, 1].")
    return number


def validate_action_data(raw: Any, index: int) -> Action:
    if not isinstance(raw, dict):
        raise ToolValidationError("Each batch action must be an object.", details={"index": index})
    reject_unknown(raw, {"type", "description", "parameters", "metadata"})
    try:
        action_type = ActionType(raw.get("type"))
    except ValueError as exc:
        raise ToolValidationError("Unsupported batch action type.", details={"index": index}) from exc
    if action_type not in EXECUTABLE_ACTION_TYPES:
        raise ToolValidationError(
            "Batch only accepts executable structured Blender actions.",
            details={"index": index, "action_type": action_type.value},
        )
    parameters = raw.get("parameters")
    if not isinstance(parameters, dict):
        raise ToolValidationError("Batch action parameters must be an object.", details={"index": index})
    action = Action(
        type=action_type,
        description=str(raw.get("description", "")),
        parameters=dict(parameters),
        status=ActionStatus.PLANNED,
        metadata=dict(raw.get("metadata", {})) if isinstance(raw.get("metadata", {}), dict) else {},
    )
    validate_action_shape(action, index=index)
    return action


def validate_action_shape(action: Action, *, index: int | None = None) -> None:
    params = action.parameters
    details = {} if index is None else {"index": index}
    if action.type is ActionType.CREATE_OBJECT:
        primitive = params.get("primitive")
        if primitive not in CREATABLE_OBJECTS:
            raise ToolValidationError("Unknown primitive.", details={**details, "primitive": primitive})
        require_name(params, "name")
        for field in ("location", "rotation", "scale"):
            optional_vector(params, field)
        optional_vector(params, "dimensions", positive=True)
        if "light" in params:
            if primitive not in {"point_light", "area_light"} or not isinstance(params["light"], dict):
                raise ToolValidationError("light is only valid for light objects.", details=details)
            _validate_light(params["light"])
        if primitive == "curve":
            points = params.get("points")
            if not isinstance(points, list) or len(points) < 2:
                raise ToolValidationError("curve requires at least two points.", details=details)
            for point in points:
                vector(point, "points")
        if primitive == "camera" and "look_at" in params and not isinstance(params["look_at"], str):
            vector(params["look_at"], "look_at")
        return
    if action.type is ActionType.TRANSFORM_OBJECT:
        _require_target(params)
        provided = False
        for field in ("location", "rotation", "scale"):
            if field in params:
                provided = True
                optional_vector(params, field)
        if "dimensions" in params:
            provided = True
            optional_vector(params, "dimensions", positive=True)
        if "look_at" in params:
            provided = True
            if not isinstance(params["look_at"], str):
                vector(params["look_at"], "look_at")
        if not provided:
            raise ToolValidationError("Transform requires at least one transform field.", details=details)
        return
    if action.type is ActionType.DELETE_OBJECT:
        _require_target(params)
        return
    if action.type is ActionType.MODIFY_OBJECT:
        _require_target(params)
        if "new_name" in params:
            require_name(params, "new_name")
        if "light" in params:
            if not isinstance(params["light"], dict):
                raise ToolValidationError("light must be an object.", details=details)
            _validate_light(params["light"], require_any=True)
        if "camera" in params and not isinstance(params["camera"], dict):
            raise ToolValidationError("camera must be an object.", details=details)
        if "new_name" not in params and "light" not in params and "camera" not in params:
            raise ToolValidationError("Modify requires new_name, light, or camera.", details=details)
        return
    if action.type is ActionType.ASSIGN_MATERIAL:
        _require_target(params)
        material = params.get("material")
        if not isinstance(material, dict):
            raise ToolValidationError("material must be an object.", details=details)
        require_name(material, "name")
        color(material.get("base_color"), "material.base_color", 4)
        unit_number(material.get("roughness"), "material.roughness")
        unit_number(material.get("metallic"), "material.metallic")
        if "emission_color" in material:
            color(material["emission_color"], "material.emission_color", 4)
        if "emission_strength" in material and finite_number(material["emission_strength"], "material.emission_strength") < 0:
            raise ToolValidationError("material.emission_strength must be non-negative.")
        if "transmission" in material:
            unit_number(material["transmission"], "material.transmission")
        if "alpha" in material:
            unit_number(material["alpha"], "material.alpha")
        return
    if action.type is ActionType.SET_PARENT:
        require_name(params, "target_name")
        require_name(params, "parent_name")
        return
    if action.type is ActionType.CONFIGURE_WORLD:
        color(params.get("color"), "world.color", 3)
        if finite_number(params.get("strength"), "world.strength") < 0:
            raise ToolValidationError("world.strength must be non-negative.")
        return
    if action.type is ActionType.CONFIGURE_SCENE:
        _validate_scene(params)
        return
    if action.type is ActionType.KEYFRAME_OBJECT:
        _require_target(params)
        keyframes = params.get("keyframes")
        if not isinstance(keyframes, list) or not keyframes:
            raise ToolValidationError("keyframes must be a non-empty list.")
        return
    if action.type is ActionType.RENDER_PREVIEW:
        _validate_artifact_path(params.get("path"), {".png", ".mp4"})
        if params.get("kind", "still") not in {"still", "animation"}:
            raise ToolValidationError("kind must be still or animation.")
        return
    if action.type is ActionType.SAVE_CHECKPOINT:
        _validate_artifact_path(params.get("path"), {".blend"})
        return
    if action.type is ActionType.SNAPSHOT_SCENE:
        if "snapshot_id" in params:
            require_name(params, "snapshot_id")
        return
    if action.type is ActionType.RESTORE_SNAPSHOT:
        require_name(params, "snapshot_id")
        for field in ("current_fingerprint", "snapshot_fingerprint"):
            value = require_name(params, field)
            if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
                raise ToolValidationError(f"{field} must be a lowercase SHA-256 fingerprint.")
        return
    if action.type is ActionType.DELETE_SNAPSHOT:
        require_name(params, "snapshot_id")
        return
    if action.type is ActionType.LIST_SNAPSHOTS:
        return
    if action.type is ActionType.RECONCILE_OBJECT_IDS:
        if "prefix" in params:
            require_name(params, "prefix")
        return


def _require_target(params: dict[str, Any]) -> str:
    if isinstance(params.get("target_uuid"), str) and params["target_uuid"]:
        return params["target_uuid"]
    return require_name(params, "target_name")


def _validate_light(light: dict[str, Any], require_any: bool = False) -> None:
    if require_any and not any(key in light for key in ("color", "energy", "size")):
        raise ToolValidationError("Light update requires color, energy, or size.")
    if "color" in light:
        color(light["color"], "light.color", 3)
    if "energy" in light:
        energy = finite_number(light["energy"], "light.energy")
        if energy < 0:
            raise ToolValidationError("light.energy must be non-negative.")
    if "size" in light and finite_number(light["size"], "light.size") <= 0:
        raise ToolValidationError("light.size must be positive.")


def _validate_scene(params: dict[str, Any]) -> None:
    if params.get("engine") not in {"BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"}:
        raise ToolValidationError("engine must select a Blender Eevee engine.")
    for field in ("resolution_x", "resolution_y"):
        value = params.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or not 64 <= value <= 2048:
            raise ToolValidationError(f"{field} must be an integer in [64, 2048].")
    for field, minimum, maximum in (("samples", 1, 1024), ("fps", 1, 120)):
        value = params.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
            raise ToolValidationError(f"{field} must be an integer in [{minimum}, {maximum}].")
    if not isinstance(params.get("frame_start"), int) or not isinstance(params.get("frame_end"), int):
        raise ToolValidationError("frame_start and frame_end must be integers.")
    if params["frame_end"] < params["frame_start"]:
        raise ToolValidationError("frame range is invalid.")


def _validate_artifact_path(value: Any, suffixes: set[str]) -> None:
    from pathlib import PurePosixPath

    if not isinstance(value, str) or not value:
        raise ToolValidationError("path must be a non-empty relative artifact path.")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.suffix.lower() not in suffixes:
        raise ToolValidationError("path must stay inside the configured artifact root.")
