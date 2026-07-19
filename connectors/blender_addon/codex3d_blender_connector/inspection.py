from __future__ import annotations

from typing import Any

from .protocol_compat import (
    ConnectorSceneInspection,
    Dimensions,
    Scene,
    SceneObject,
    SceneObjectSourceType,
    Transform,
    Vector3,
)


def inspect_scene(
    bpy_module: Any | None = None,
    connector_id: str = "",
) -> ConnectorSceneInspection:
    if hasattr(bpy_module, "inspect"):
        return bpy_module.inspect(connector_id=connector_id)

    if bpy_module is None:
        scene = Scene(
            name="Blender unavailable scene",
            metadata={
                "blender_available": False,
                "object_count": 0,
            },
        )
        return ConnectorSceneInspection(
            connector_id=connector_id,
            scene=scene,
            metadata={
                "blender_available": False,
                "object_count": 0,
            },
        )

    raw_objects = _extract_objects(bpy_module)
    context_scene = getattr(getattr(bpy_module, "context", None), "scene", None)
    scene = Scene(
        name=_extract_scene_name(bpy_module),
        metadata={
            "blender_available": True,
            "object_count": len(raw_objects),
            "active_camera": getattr(getattr(getattr(bpy_module, "context", None), "scene", None), "camera", None).name
            if getattr(getattr(getattr(bpy_module, "context", None), "scene", None), "camera", None)
            else None,
            "frame_start": getattr(getattr(getattr(bpy_module, "context", None), "scene", None), "frame_start", None),
            "frame_end": getattr(getattr(getattr(bpy_module, "context", None), "scene", None), "frame_end", None),
            "keyframe_count": int(getattr(getattr(getattr(bpy_module, "context", None), "scene", None), "get", lambda *_: 0)("codex3d_keyframe_count", 0)),
            "target_collection": _custom_property(context_scene, "codex3d_target_collection"),
            "accepted_snapshot_id": _custom_property(context_scene, "codex3d_accepted_snapshot_id"),
            "accepted_snapshot_fingerprint": _custom_property(context_scene, "codex3d_accepted_snapshot_fingerprint"),
        },
    )
    for raw_object in raw_objects:
        scene.add_object(_scene_object_from_bpy_object(raw_object))

    return ConnectorSceneInspection(
        connector_id=connector_id,
        scene=scene,
        metadata={
            "blender_available": True,
            "object_count": len(scene.objects),
        },
    )


def _extract_scene_name(bpy_module: Any) -> str:
    scene = getattr(getattr(bpy_module, "context", None), "scene", None)
    return getattr(scene, "name", "Blender Scene")


def _extract_objects(bpy_module: Any) -> list[Any]:
    context_scene = getattr(getattr(bpy_module, "context", None), "scene", None)
    if context_scene is not None and hasattr(context_scene, "objects"):
        return list(context_scene.objects)

    data = getattr(bpy_module, "data", None)
    if data is not None and hasattr(data, "objects"):
        return list(data.objects)

    return []


def _scene_object_from_bpy_object(raw_object: Any) -> SceneObject:
    object_name = getattr(raw_object, "name", "Blender object")
    object_type = str(getattr(raw_object, "type", "object")).lower()
    active_material = getattr(raw_object, "active_material", None)
    object_data = getattr(raw_object, "data", None)
    light_metadata = None
    if object_type == "light" and object_data is not None:
        light_metadata = {
            "energy": float(getattr(object_data, "energy", 0.0)),
            "color": [float(item) for item in getattr(object_data, "color", ())],
            "size": float(getattr(object_data, "size", 0.0)),
        }
    camera_metadata = None
    if object_type == "camera" and object_data is not None:
        camera_metadata = {"focal_length": float(getattr(object_data, "lens", 0.0))}
    material_metadata = _material_metadata(active_material)
    return SceneObject(
        label=object_name,
        semantic_type=object_type,
        source_type=SceneObjectSourceType.EXISTING_BLENDER_OBJECT,
        blender_uuid=_custom_property(raw_object, "codex3d_uuid"),
        transform=Transform(
            location=_vector3(getattr(raw_object, "location", None)),
            rotation_euler=_vector3(getattr(raw_object, "rotation_euler", None)),
            scale=_vector3(getattr(raw_object, "scale", None), default=1.0),
        ),
        dimensions=_dimensions(getattr(raw_object, "dimensions", None)),
        metadata={
            "blender_name": object_name,
            "blender_type": object_type,
            "codex3d_uuid": _custom_property(raw_object, "codex3d_uuid"),
            "material_name": getattr(active_material, "name", None),
            "material": material_metadata,
            "light": light_metadata,
            "camera": camera_metadata,
            "parent_name": getattr(getattr(raw_object, "parent", None), "name", None),
            "collections": [item.name for item in getattr(raw_object, "users_collection", ())],
        },
    )


def _custom_property(raw_object: Any, key: str) -> Any:
    getter = getattr(raw_object, "get", None)
    if callable(getter):
        return getter(key)
    return getattr(raw_object, key, None)


def _material_metadata(material: Any) -> dict[str, Any] | None:
    if material is None:
        return None
    result: dict[str, Any] = {"name": getattr(material, "name", None)}
    node_tree = getattr(material, "node_tree", None)
    principled = node_tree.nodes.get("Principled BSDF") if node_tree is not None else None
    if principled is None:
        return result
    for key, names in {
        "base_color": ("Base Color",),
        "metallic": ("Metallic",),
        "roughness": ("Roughness",),
        "emission_color": ("Emission Color", "Emission"),
        "emission_strength": ("Emission Strength",),
        "transmission": ("Transmission Weight", "Transmission"),
        "alpha": ("Alpha",),
    }.items():
        for name in names:
            socket = principled.inputs.get(name)
            if socket is not None:
                value = socket.default_value
                result[key] = list(value) if hasattr(value, "__len__") else float(value)
                break
    return result


def _vector3(value: Any, default: float = 0.0) -> Vector3:
    if value is None:
        return Vector3(default, default, default)
    return Vector3(
        x=float(_component(value, 0, "x", default)),
        y=float(_component(value, 1, "y", default)),
        z=float(_component(value, 2, "z", default)),
    )


def _dimensions(value: Any) -> Dimensions:
    if value is None:
        return Dimensions()
    return Dimensions(
        width=float(_component(value, 0, "x", 0.0)),
        depth=float(_component(value, 1, "y", 0.0)),
        height=float(_component(value, 2, "z", 0.0)),
    )


def _component(value: Any, index: int, attr: str, default: float) -> float:
    if hasattr(value, attr):
        return getattr(value, attr)
    try:
        return value[index]
    except (IndexError, KeyError, TypeError):
        return default
