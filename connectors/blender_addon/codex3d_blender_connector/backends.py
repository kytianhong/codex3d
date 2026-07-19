from __future__ import annotations

import math
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Protocol

from .protocol_compat import ConnectorSceneInspection, new_id, to_dict, utc_now_iso
from .artifact_paths import resolve_artifact_path
from .composition_validation import evaluate_composition


class BlenderBackend(Protocol):
    backend_name: str

    def object_exists(self, name: str) -> bool:
        ...

    def object_uuid(self, identifier: str) -> str | None:
        ...

    def create_object(self, params: dict[str, Any]) -> str:
        ...

    def transform_object(self, params: dict[str, Any]) -> str:
        ...

    def modify_object(self, params: dict[str, Any]) -> str:
        ...

    def delete_object(self, params: dict[str, Any]) -> str:
        ...

    def assign_material(self, params: dict[str, Any]) -> str:
        ...

    def set_parent(self, params: dict[str, Any]) -> str:
        ...

    def configure_world(self, params: dict[str, Any]) -> dict[str, Any]:
        ...

    def configure_scene(self, params: dict[str, Any]) -> dict[str, Any]:
        ...

    def keyframe_object(self, params: dict[str, Any]) -> dict[str, Any]:
        ...

    def render(self, params: dict[str, Any]) -> dict[str, Any]:
        ...

    def save_checkpoint(self, params: dict[str, Any]) -> dict[str, Any]:
        ...

    def create_snapshot(self, params: dict[str, Any]) -> dict[str, Any]:
        ...

    def list_snapshots(self, params: dict[str, Any]) -> dict[str, Any]:
        ...

    def restore_snapshot(self, params: dict[str, Any]) -> dict[str, Any]:
        ...

    def delete_snapshot(self, params: dict[str, Any]) -> dict[str, Any]:
        ...

    def reconcile_object_ids(self, params: dict[str, Any]) -> dict[str, Any]:
        ...

    def inspect(self, connector_id: str = "") -> ConnectorSceneInspection:
        ...


class BpyUnavailableError(RuntimeError):
    pass


class BpyBlenderBackend:
    backend_name = "bpy"

    def __init__(
        self,
        bpy_module: Any | None = None,
        artifact_root: str | Path | None = None,
        session_id: str | None = None,
    ) -> None:
        self.bpy = bpy_module or self._load_bpy()
        self.artifact_root = artifact_root or os.environ.get("CODEX3D_ARTIFACT_ROOT")
        self.session_id = session_id or os.environ.get("CODEX3D_SESSION_ID") or "local_session"

    def _load_bpy(self):
        try:
            import bpy  # type: ignore
        except ImportError as exc:
            raise BpyUnavailableError("bpy is not available outside Blender.") from exc
        return bpy

    def object_exists(self, name: str) -> bool:
        return self._get_object(name) is not None

    def object_uuid(self, identifier: str) -> str | None:
        obj = self._get_object(identifier)
        return str(obj.get("codex3d_uuid")) if obj is not None and obj.get("codex3d_uuid") else None

    def create_object(self, params: dict[str, Any]) -> str:
        primitive = params["primitive"]
        name = params["name"]
        location = tuple(params.get("location", (0.0, 0.0, 0.0)))
        rotation = tuple(params.get("rotation", (0.0, 0.0, 0.0)))
        scale = tuple(params.get("scale", (1.0, 1.0, 1.0)))

        if primitive in {"point_light", "area_light"}:
            light_data = self.bpy.data.lights.new(name=name, type="POINT" if primitive == "point_light" else "AREA")
            light_data.energy = params.get("light", {}).get("energy", 10.0)
            light_data.color = tuple(params.get("light", {}).get("color", (1.0, 1.0, 1.0)))
            if primitive == "area_light":
                light_data.shape = "DISK"
                light_data.size = params.get("light", {}).get("size", 5.0)
            obj = self.bpy.data.objects.new(name, light_data)
            self._link_object(obj, params.get("collection"))
        elif primitive == "curve":
            obj = self._create_curve(params)
        elif primitive == "camera":
            camera_data = self.bpy.data.cameras.new(name=name)
            camera_data.lens = params.get("focal_length", 50.0)
            obj = self.bpy.data.objects.new(name, camera_data)
            self._link_object(obj, params.get("collection"))
        elif primitive == "empty":
            obj = self.bpy.data.objects.new(name, None)
            obj.empty_display_type = "PLAIN_AXES"
            obj.empty_display_size = params.get("display_size", 1.0)
            self._link_object(obj, params.get("collection"))
        else:
            self._add_mesh_primitive(primitive, location, rotation)
            obj = self.bpy.context.object
            obj.name = name
            self._move_to_collection(obj, params.get("collection"))

        obj.location = location
        obj.rotation_euler = rotation
        obj.scale = scale
        if "dimensions" in params and primitive not in {"point_light", "area_light", "curve", "camera", "empty"}:
            obj.dimensions = tuple(params["dimensions"])
            self._update_view_layer()
        if "look_at" in params:
            self._look_at(obj, params["look_at"])
        if primitive == "camera" and params.get("active", True):
            self.bpy.context.scene.camera = obj
        obj["codex3d_semantic_type"] = params.get("semantic_type", primitive)
        obj["codex3d_uuid"] = params.get("object_uuid") or new_id("object")
        return obj.name

    def transform_object(self, params: dict[str, Any]) -> str:
        obj = self._require_object(self._target(params))
        if "location" in params:
            obj.location = tuple(params["location"])
        if "rotation" in params:
            obj.rotation_euler = tuple(params["rotation"])
        if "scale" in params:
            obj.scale = tuple(params["scale"])
        if "dimensions" in params:
            obj.dimensions = tuple(params["dimensions"])
            self._update_view_layer()
        if "look_at" in params:
            self._look_at(obj, params["look_at"])
        return obj.name

    def modify_object(self, params: dict[str, Any]) -> str:
        obj = self._require_object(self._target(params))
        if "light" in params:
            if getattr(obj, "type", "") != "LIGHT":
                raise ValueError(f"Target is not a light: {obj.name}")
            light = params["light"]
            if "energy" in light:
                obj.data.energy = light["energy"]
            if "color" in light:
                obj.data.color = tuple(light["color"])
            if "size" in light and hasattr(obj.data, "size"):
                obj.data.size = light["size"]
        if "camera" in params:
            camera = params["camera"]
            if getattr(obj, "type", "") != "CAMERA":
                raise ValueError(f"Target is not a camera: {obj.name}")
            if "focal_length" in camera:
                obj.data.lens = camera["focal_length"]
            if "look_at" in camera:
                self._look_at(obj, camera["look_at"])
        if "new_name" in params:
            obj.name = params["new_name"]
        return obj.name

    def delete_object(self, params: dict[str, Any]) -> str:
        obj = self._require_object(self._target(params))
        name = obj.name
        self.bpy.data.objects.remove(obj, do_unlink=True)
        return name

    def assign_material(self, params: dict[str, Any]) -> str:
        obj = self._require_object(self._target(params))
        material_params = params["material"]
        material = self.bpy.data.materials.get(material_params["name"])
        if material is None:
            material = self.bpy.data.materials.new(material_params["name"])
        material.use_nodes = True
        principled = material.node_tree.nodes.get("Principled BSDF")
        if principled is not None:
            self._set_principled_input(principled, "Base Color", material_params["base_color"])
            self._set_principled_input(principled, "Roughness", material_params["roughness"])
            self._set_principled_input(principled, "Metallic", material_params["metallic"])
            self._set_principled_input_any(
                principled,
                ("Emission Color", "Emission"),
                material_params.get("emission_color", (0.0, 0.0, 0.0, 1.0)),
            )
            self._set_principled_input(principled, "Emission Strength", material_params.get("emission_strength", 0.0))
            self._set_principled_input_any(
                principled,
                ("Transmission Weight", "Transmission"),
                material_params.get("transmission", 0.0),
            )
            self._set_principled_input(principled, "Alpha", material_params.get("alpha", 1.0))
        material.diffuse_color = tuple(material_params["base_color"])
        if hasattr(material, "surface_render_method") and material_params.get("alpha", 1.0) < 1.0:
            material.surface_render_method = "DITHERED"
        obj.data.materials.clear()
        obj.data.materials.append(material)
        return obj.name

    def set_parent(self, params: dict[str, Any]) -> str:
        obj = self._require_object(self._target(params))
        parent = self._require_object(params["parent_name"])
        matrix_world = obj.matrix_world.copy()
        obj.parent = parent
        if params.get("keep_transform", True):
            obj.matrix_world = matrix_world
        return obj.name

    def configure_world(self, params: dict[str, Any]) -> dict[str, Any]:
        world = self.bpy.context.scene.world
        if world is None:
            world = self.bpy.data.worlds.new("C3D_World")
            self.bpy.context.scene.world = world
        world.use_nodes = True
        background = world.node_tree.nodes.get("Background")
        if background is not None:
            background.inputs["Color"].default_value = (*params["color"], 1.0)
            background.inputs["Strength"].default_value = params["strength"]
        world.color = tuple(params["color"])
        return {"world_color": list(params["color"]), "world_strength": params["strength"]}

    def configure_scene(self, params: dict[str, Any]) -> dict[str, Any]:
        scene = self.bpy.context.scene
        requested_engine = params.get("engine", "BLENDER_EEVEE")
        available_engines = {
            item.identifier for item in scene.render.bl_rna.properties["engine"].enum_items
        }
        if requested_engine not in available_engines:
            requested_engine = "BLENDER_EEVEE" if "BLENDER_EEVEE" in available_engines else "BLENDER_EEVEE_NEXT"
        scene.render.engine = requested_engine
        scene.render.resolution_x = params["resolution_x"]
        scene.render.resolution_y = params["resolution_y"]
        scene.render.resolution_percentage = 100
        scene.render.film_transparent = params.get("transparent", False)
        scene.render.fps = params.get("fps", 24)
        scene.frame_start = params.get("frame_start", 1)
        scene.frame_end = params.get("frame_end", 72)
        if hasattr(scene, "render"):
            scene.render.image_settings.color_mode = "RGBA"
        if hasattr(scene, "eevee"):
            scene.eevee.taa_render_samples = params.get("samples", 32)
        return self._scene_settings()

    def keyframe_object(self, params: dict[str, Any]) -> dict[str, Any]:
        obj = self._require_object(self._target(params))
        scene = self.bpy.context.scene
        current_frame = scene.frame_current
        inserted = 0
        channels: set[str] = set()
        for item in params["keyframes"]:
            frame = item["frame"]
            for field, data_path in (("location", "location"), ("rotation", "rotation_euler"), ("scale", "scale")):
                if field in item:
                    setattr(obj, data_path, tuple(item[field]))
                    obj.keyframe_insert(data_path=data_path, frame=frame)
                    inserted += 1
                    channels.update(f"{data_path}[{index}]" for index in range(3))
            if "emission_strength" in item:
                socket = self._material_socket(obj, "Emission Strength")
                socket.default_value = item["emission_strength"]
                socket.keyframe_insert(data_path="default_value", frame=frame)
                inserted += 1
                channels.add("material.emission_strength")
        self._set_action_interpolation(obj, params.get("interpolation", "BEZIER"), params.get("cycle", False))
        if any("emission_strength" in item for item in params["keyframes"]):
            material = obj.active_material
            if material and material.node_tree:
                self._set_action_interpolation(material.node_tree, params.get("interpolation", "BEZIER"), params.get("cycle", False))
        scene["codex3d_keyframe_count"] = int(scene.get("codex3d_keyframe_count", 0)) + inserted
        scene["codex3d_fcurve_count"] = int(scene.get("codex3d_fcurve_count", 0)) + len(channels)
        scene["codex3d_animated_object_count"] = len(
            [candidate for candidate in scene.objects if getattr(candidate, "animation_data", None)]
        )
        scene.frame_set(current_frame)
        return {"object_name": obj.name, "inserted_keyframes": inserted, **self._animation_stats()}

    def render(self, params: dict[str, Any]) -> dict[str, Any]:
        kind = params.get("kind", "still")
        suffixes = {".png"} if kind == "still" else {".mp4"}
        path, relative = resolve_artifact_path(self.artifact_root, params["path"], allowed_suffixes=suffixes)
        scene = self.bpy.context.scene
        if scene.camera is None:
            raise ValueError("An active camera is required before rendering.")
        if kind == "still":
            scene.render.image_settings.file_format = "PNG"
            scene.render.filepath = str(path)
            self.bpy.ops.render.render(write_still=True)
            result = self._render_result(path, relative, "image/png", kind="still")
            if Path(relative).name == "preview_final.png":
                validation_path = path.with_suffix(".validation.json")
                validation_path.write_text(json.dumps(result["composition"], indent=2, sort_keys=True), encoding="utf-8")
                if not result["composition"]["passed"]:
                    failures = ", ".join(result["composition"]["failures"])
                    raise ValueError(f"Composition guard failed: {failures}. Adjust the camera or subject and render again.")
            return result
        return self._render_animation(path, relative)

    def save_checkpoint(self, params: dict[str, Any]) -> dict[str, Any]:
        requested = params.get("path") or f"checkpoints/{self.session_id}.blend"
        path, relative = resolve_artifact_path(self.artifact_root, requested, allowed_suffixes={".blend"})
        path, relative = self._versioned_artifact_path(path, relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        summary = self._canonical_scene_summary()
        before_fingerprint = _fingerprint(summary)
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.stem}_", suffix=".blend", dir=path.parent)
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            temporary.unlink(missing_ok=True)
            self.bpy.ops.wm.save_as_mainfile(
                filepath=str(temporary),
                check_existing=False,
                copy=True,
            )
            if not temporary.is_file() or temporary.stat().st_size == 0:
                raise ValueError("Blender did not create the checkpoint copy.")
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        after_fingerprint = _fingerprint(self._canonical_scene_summary())
        if after_fingerprint != before_fingerprint:
            path.unlink(missing_ok=True)
            raise ValueError("Checkpoint save unexpectedly changed the live scene.")
        return {
            "path": relative,
            "mime": "application/x-blender",
            "file_size": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "scene_fingerprint": before_fingerprint,
            "uuid_count": sum(bool(item["uuid"]) for item in summary["objects"]),
            "versioned": relative != requested,
            "session_id": self.session_id,
        }

    def create_snapshot(self, params: dict[str, Any]) -> dict[str, Any]:
        snapshot_id = params.get("snapshot_id") or new_id("snapshot")
        blend_path, blend_relative = self._snapshot_path(snapshot_id, ".blend")
        metadata_path, metadata_relative = self._snapshot_path(snapshot_id, ".json")
        if blend_path.exists() or metadata_path.exists():
            raise FileExistsError(f"Snapshot already exists and cannot be overwritten: {snapshot_id}")
        summary = self._canonical_scene_summary()
        fingerprint = _fingerprint(summary)
        scene = self.bpy.context.scene
        scene["codex3d_accepted_snapshot_id"] = snapshot_id
        scene["codex3d_accepted_snapshot_fingerprint"] = fingerprint
        self.bpy.ops.wm.save_as_mainfile(
            filepath=str(blend_path),
            check_existing=False,
            copy=True,
        )
        metadata = {
            "snapshot_id": snapshot_id,
            "session_id": self.session_id,
            "created_at": utc_now_iso(),
            "source_action_id": params.get("source_action_id"),
            "source_turn": params.get("source_turn"),
            "scene_fingerprint": fingerprint,
            "object_uuids": [item["uuid"] for item in summary["objects"] if item["uuid"]],
            "object_count": len(summary["objects"]),
            "active_camera": summary["active_camera"],
            "blend_path": blend_relative,
            "metadata_path": metadata_relative,
            "file_size": blend_path.stat().st_size,
            "scene_summary": summary,
        }
        metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
        return metadata

    def list_snapshots(self, params: dict[str, Any]) -> dict[str, Any]:
        root = self._snapshot_root()
        snapshots = []
        for path in sorted(root.glob("snapshot_*.json")):
            try:
                snapshots.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
        return {"snapshots": snapshots, "snapshot_count": len(snapshots)}

    def restore_snapshot(self, params: dict[str, Any]) -> dict[str, Any]:
        snapshot_id = params["snapshot_id"]
        blend_path, _ = self._snapshot_path(snapshot_id, ".blend", create_parent=False)
        metadata_path, _ = self._snapshot_path(snapshot_id, ".json", create_parent=False)
        if not blend_path.is_file() or not metadata_path.is_file():
            raise KeyError(f"Snapshot not found: {snapshot_id}")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("session_id") != self.session_id:
            raise PermissionError("Snapshot belongs to a different Codex3D session.")
        current_summary = self._canonical_scene_summary()
        current_fingerprint = _fingerprint(current_summary)
        expected_fingerprint = metadata["scene_fingerprint"]
        if params.get("current_fingerprint") != current_fingerprint:
            raise ValueError("current_fingerprint does not match the live scene.")
        if params.get("snapshot_fingerprint") != expected_fingerprint:
            raise ValueError("snapshot_fingerprint does not match the registered snapshot.")

        safety_id = new_id("snapshot_pre_restore")
        safety = self.create_snapshot(
            {
                "snapshot_id": safety_id,
                "source_action_id": params.get("source_action_id"),
                "source_turn": "pre_restore",
            }
        )
        try:
            self.bpy.ops.wm.open_mainfile(filepath=str(blend_path))
            summary = self._canonical_scene_summary()
            restored_fingerprint = _fingerprint(summary)
            if restored_fingerprint != expected_fingerprint:
                raise ValueError("Restored scene does not match the snapshot fingerprint.")
        except Exception:
            safety_path, _ = self._snapshot_path(safety_id, ".blend", create_parent=False)
            self.bpy.ops.wm.open_mainfile(filepath=str(safety_path))
            raise
        return {
            "snapshot_id": snapshot_id,
            "restored": True,
            "scene_fingerprint": restored_fingerprint,
            "object_count": len(summary["objects"]),
            "active_camera": summary["active_camera"],
            "scene_summary": summary,
            "inspection": to_dict(self.inspect()),
            "safety_snapshot_id": safety_id,
            "safety_snapshot_fingerprint": safety["scene_fingerprint"],
            "scene_diff": _scene_summary_diff(current_summary, summary),
            "session_id": self.session_id,
        }

    def delete_snapshot(self, params: dict[str, Any]) -> dict[str, Any]:
        snapshot_id = params["snapshot_id"]
        removed = []
        for suffix in (".blend", ".json"):
            path, relative = self._snapshot_path(snapshot_id, suffix, create_parent=False)
            if path.exists():
                path.unlink()
                removed.append(relative)
        if not removed:
            raise KeyError(f"Snapshot not found: {snapshot_id}")
        return {"snapshot_id": snapshot_id, "deleted": True, "removed_paths": removed}

    def reconcile_object_ids(self, params: dict[str, Any]) -> dict[str, Any]:
        prefix = params.get("prefix", "C3D_")
        assigned = []
        existing = []
        for obj in self.bpy.context.scene.objects:
            if not obj.name.startswith(prefix):
                continue
            if obj.get("codex3d_uuid"):
                existing.append({"name": obj.name, "uuid": str(obj["codex3d_uuid"])})
                continue
            obj["codex3d_uuid"] = new_id("object")
            assigned.append({"name": obj.name, "uuid": str(obj["codex3d_uuid"])})
        return {"prefix": prefix, "assigned": assigned, "existing": existing, "assigned_count": len(assigned)}

    def inspect(self, connector_id: str = "") -> ConnectorSceneInspection:
        from .inspection import inspect_scene

        inspection = inspect_scene(self.bpy, connector_id=connector_id)
        fingerprint = _fingerprint(self._canonical_scene_summary())
        inspection.metadata["scene_fingerprint"] = fingerprint
        inspection.metadata["session_id"] = self.session_id
        inspection.scene.metadata["scene_fingerprint"] = fingerprint
        return inspection

    def _add_mesh_primitive(self, primitive: str, location, rotation) -> None:
        if primitive == "cube":
            self.bpy.ops.mesh.primitive_cube_add(size=1.0, location=location, rotation=rotation)
        elif primitive == "cylinder":
            self.bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.5, depth=1.0, location=location, rotation=rotation)
        elif primitive == "sphere":
            self.bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.5, location=location, rotation=rotation)
        elif primitive == "plane":
            self.bpy.ops.mesh.primitive_plane_add(size=1.0, location=location, rotation=rotation)
        else:
            raise ValueError(f"Unsupported primitive: {primitive}")

    def _get_object(self, identifier: str):
        by_name = self.bpy.data.objects.get(identifier)
        if by_name is not None:
            return by_name
        for obj in self.bpy.data.objects:
            if str(obj.get("codex3d_uuid", "")) == identifier:
                return obj
        return None

    def _require_object(self, name: str):
        obj = self._get_object(name)
        if obj is None:
            raise KeyError(name)
        return obj

    def _target(self, params: dict[str, Any]) -> str:
        return params.get("target_uuid") or params["target_name"]

    def _snapshot_root(self) -> Path:
        path, _ = resolve_artifact_path(self.artifact_root, "snapshots/.keep", allowed_suffixes={".keep"})
        return path.parent

    def _snapshot_path(
        self,
        snapshot_id: str,
        suffix: str,
        *,
        create_parent: bool = True,
    ) -> tuple[Path, str]:
        if not snapshot_id.startswith("snapshot_") or not all(
            char.isalnum() or char == "_" for char in snapshot_id
        ):
            raise ValueError("snapshot_id must use the generated snapshot_ identifier format.")
        path, relative = resolve_artifact_path(
            self.artifact_root,
            f"snapshots/{snapshot_id}{suffix}",
            allowed_suffixes={suffix},
        )
        if create_parent:
            path.parent.mkdir(parents=True, exist_ok=True)
        return path, relative

    def _versioned_artifact_path(self, path: Path, relative: str) -> tuple[Path, str]:
        if not path.exists():
            return path, relative
        index = 2
        while True:
            candidate = path.with_name(f"{path.stem}_v{index:03d}{path.suffix}")
            if not candidate.exists():
                root = Path(self.artifact_root).expanduser().resolve()
                return candidate, candidate.relative_to(root).as_posix()
            index += 1

    def _canonical_scene_summary(self) -> dict[str, Any]:
        scene = self.bpy.context.scene
        objects = []
        for obj in sorted(scene.objects, key=lambda item: (str(item.get("codex3d_uuid", "")), item.name)):
            material = getattr(obj, "active_material", None)
            objects.append(
                {
                    "uuid": str(obj.get("codex3d_uuid", "")) or None,
                    "name": obj.name,
                    "type": obj.type,
                    "location": _rounded_vector(obj.location),
                    "rotation": _rounded_vector(obj.rotation_euler),
                    "scale": _rounded_vector(obj.scale),
                    "dimensions": _rounded_vector(obj.dimensions),
                    "material": getattr(material, "name", None),
                }
            )
        return {
            "objects": objects,
            "active_camera": scene.camera.name if scene.camera else None,
            "frame_start": scene.frame_start,
            "frame_end": scene.frame_end,
            "animation": self._animation_stats(),
        }

    def _update_view_layer(self) -> None:
        view_layer = getattr(self.bpy.context, "view_layer", None)
        if view_layer is not None:
            view_layer.update()

    def _set_principled_input(self, principled, input_name: str, value) -> None:
        socket = principled.inputs.get(input_name)
        if socket is not None:
            socket.default_value = value

    def _set_principled_input_any(self, principled, input_names: tuple[str, ...], value) -> None:
        for name in input_names:
            socket = principled.inputs.get(name)
            if socket is not None:
                socket.default_value = value
                return

    def _create_curve(self, params: dict[str, Any]):
        curve_data = self.bpy.data.curves.new(params["name"], type="CURVE")
        curve_data.dimensions = "3D"
        curve_data.fill_mode = params.get("fill_mode", "FULL")
        curve_data.bevel_depth = params.get("bevel_depth", 0.02)
        curve_data.bevel_resolution = params.get("bevel_resolution", 3)
        curve_data.resolution_u = params.get("resolution", 12)
        curve_type = params.get("curve_type", "bezier")
        spline = curve_data.splines.new("BEZIER" if curve_type == "bezier" else "POLY")
        points = params["points"]
        if curve_type == "bezier":
            spline.bezier_points.add(len(points) - 1)
            for point, coordinate in zip(spline.bezier_points, points):
                point.co = tuple(coordinate)
                point.handle_left_type = "AUTO"
                point.handle_right_type = "AUTO"
        else:
            spline.points.add(len(points) - 1)
            for point, coordinate in zip(spline.points, points):
                point.co = (*coordinate, 1.0)
        spline.use_cyclic_u = params.get("cyclic", False)
        obj = self.bpy.data.objects.new(params["name"], curve_data)
        self._link_object(obj, params.get("collection"))
        return obj

    def _collection(self, name: str | None):
        if not name:
            return self.bpy.context.collection
        collection = self.bpy.data.collections.get(name)
        if collection is None:
            collection = self.bpy.data.collections.new(name)
            self.bpy.context.scene.collection.children.link(collection)
        return collection

    def _link_object(self, obj, collection_name: str | None) -> None:
        self._collection(collection_name).objects.link(obj)

    def _move_to_collection(self, obj, collection_name: str | None) -> None:
        if not collection_name:
            return
        target = self._collection(collection_name)
        if target not in obj.users_collection:
            target.objects.link(obj)
        for collection in list(obj.users_collection):
            if collection != target:
                collection.objects.unlink(obj)

    def _look_at(self, obj, target: str | list[float]) -> None:
        if isinstance(target, str):
            target_location = self._require_object(target).matrix_world.translation
        else:
            target_location = self.bpy.mathutils.Vector(target) if hasattr(self.bpy, "mathutils") else None
            if target_location is None:
                from mathutils import Vector  # type: ignore

                target_location = Vector(target)
        direction = target_location - obj.location
        if direction.length == 0:
            raise ValueError("look_at target must differ from object location.")
        obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

    def _material_socket(self, obj, input_name: str):
        material = getattr(obj, "active_material", None)
        if material is None or material.node_tree is None:
            raise ValueError(f"Object has no node material: {obj.name}")
        principled = material.node_tree.nodes.get("Principled BSDF")
        if principled is None or principled.inputs.get(input_name) is None:
            raise ValueError(f"Material input unavailable: {input_name}")
        return principled.inputs[input_name]

    def _set_action_interpolation(self, owner, interpolation: str, cycle: bool) -> None:
        animation_data = getattr(owner, "animation_data", None)
        action = getattr(animation_data, "action", None)
        fcurves = getattr(action, "fcurves", ()) if action else ()
        for fcurve in fcurves:
            for point in fcurve.keyframe_points:
                point.interpolation = interpolation
            if cycle and not any(modifier.type == "CYCLES" for modifier in fcurve.modifiers):
                fcurve.modifiers.new("CYCLES")

    def _scene_settings(self) -> dict[str, Any]:
        scene = self.bpy.context.scene
        return {
            "engine": scene.render.engine,
            "resolution": [scene.render.resolution_x, scene.render.resolution_y],
            "transparent": bool(scene.render.film_transparent),
            "fps": scene.render.fps,
            "frame_start": scene.frame_start,
            "frame_end": scene.frame_end,
        }

    def _animation_stats(self) -> dict[str, Any]:
        scene = self.bpy.context.scene
        return {
            "frame_start": scene.frame_start,
            "frame_end": scene.frame_end,
            "fps": scene.render.fps,
            "keyframe_count": int(scene.get("codex3d_keyframe_count", 0)),
            "fcurve_count": int(scene.get("codex3d_fcurve_count", 0)),
            "animated_object_count": int(scene.get("codex3d_animated_object_count", 0)),
        }

    def _render_animation(self, path: Path, relative: str) -> dict[str, Any]:
        scene = self.bpy.context.scene
        build_options = getattr(self.bpy.app, "build_options", None)
        if bool(getattr(build_options, "ffmpeg", False)):
            scene.render.image_settings.file_format = "FFMPEG"
            scene.render.ffmpeg.format = "MPEG4"
            scene.render.ffmpeg.codec = "H264"
            scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
            scene.render.filepath = str(path)
            self.bpy.ops.render.render(animation=True)
            produced = path if path.exists() else path.with_suffix(".mp4")
            if not produced.exists():
                raise ValueError("Blender reported animation completion but no MP4 was created.")
            return {
                "path": relative,
                "mime": "video/mp4",
                "file_size": produced.stat().st_size,
                "animation_format": "mp4",
                "fallback": False,
                **self._scene_settings(),
                **self._animation_stats(),
            }

        frames_relative = (Path(relative).parent / "frames/frame_0001.png").as_posix()
        frames_path, _ = resolve_artifact_path(self.artifact_root, frames_relative, allowed_suffixes={".png"})
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = str(frames_path.parent / "frame_")
        self.bpy.ops.render.render(animation=True)
        frames = sorted(frames_path.parent.glob("frame_*.png"))
        if len(frames) != scene.frame_end - scene.frame_start + 1:
            raise ValueError("PNG animation fallback did not produce every frame.")
        return {
            "path": (Path(relative).parent / "frames").as_posix() + "/",
            "mime": "image/png-sequence",
            "file_size": sum(item.stat().st_size for item in frames),
            "frame_count": len(frames),
            "animation_format": "png_sequence",
            "fallback": True,
            **self._scene_settings(),
            **self._animation_stats(),
        }

    def _render_result(self, path: Path, relative: str, mime: str, *, kind: str) -> dict[str, Any]:
        scene = self.bpy.context.scene
        image = self.bpy.data.images.load(str(path), check_existing=False)
        pixels = list(image.pixels) if image is not None else []
        sample_step = max(4, (len(pixels) // (64 * 64 * 4)) * 4) if pixels else 4
        luminance_total = 0.0
        nonblack = 0
        nontransparent = 0
        overexposed = 0
        samples = 0
        for index in range(0, len(pixels), sample_step):
            if index + 3 >= len(pixels):
                break
            red, green, blue, alpha = pixels[index:index + 4]
            luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
            luminance_total += luminance
            nonblack += int(luminance > 0.01)
            nontransparent += int(alpha > 0.01)
            overexposed += int(alpha > 0.01 and (luminance >= 0.95 or max(red, green, blue) >= 0.995))
            samples += 1
        visible_count = self._visible_subject_count()
        if image is not None:
            self.bpy.data.images.remove(image)
        overexposed_ratio = overexposed / max(samples, 1)
        composition = self._composition_metrics(overexposed_ratio)
        return {
            "path": relative,
            "mime": mime,
            "width": scene.render.resolution_x,
            "height": scene.render.resolution_y,
            "file_size": path.stat().st_size,
            "active_camera": scene.camera.name,
            "mean_luminance": luminance_total / max(samples, 1),
            "nonblack_pixel_ratio": nonblack / max(samples, 1),
            "nontransparent_pixel_ratio": nontransparent / max(samples, 1),
            "overexposed_pixel_ratio": overexposed_ratio,
            "visible_subject_count": visible_count,
            "subject_visible": visible_count > 0,
            "render_kind": kind,
            "composition": composition,
            **self._scene_settings(),
            **self._animation_stats(),
        }

    def _visible_subject_count(self) -> int:
        scene = self.bpy.context.scene
        camera = scene.camera
        if camera is None:
            return 0
        try:
            from bpy_extras.object_utils import world_to_camera_view  # type: ignore
        except ImportError:
            return 0
        visible = 0
        for obj in scene.objects:
            if not obj.name.startswith("C3D_SOL_") or obj.type not in {"MESH", "CURVE"}:
                continue
            coordinate = world_to_camera_view(scene, camera, obj.matrix_world.translation)
            if coordinate.z > 0 and 0.0 <= coordinate.x <= 1.0 and 0.0 <= coordinate.y <= 1.0:
                visible += 1
        return visible

    def _composition_metrics(self, overexposed_ratio: float) -> dict[str, Any]:
        scene = self.bpy.context.scene
        camera = scene.camera
        target_name = str(scene.get("codex3d_target_collection", ""))
        target = self.bpy.data.collections.get(target_name) if target_name else None
        if camera is None or target is None:
            return {
                "passed": False,
                "failures": ["ACTIVE_CAMERA_MISSING" if camera is None else "TARGET_COLLECTION_MISSING"],
                "target_collection": target_name or None,
            }
        try:
            from bpy_extras.object_utils import world_to_camera_view  # type: ignore
            from mathutils import Vector  # type: ignore
        except ImportError:
            return {"passed": False, "failures": ["CAMERA_PROJECTION_UNAVAILABLE"], "target_collection": target_name}

        def projection(obj) -> dict[str, Any] | None:
            if obj.type not in {"MESH", "CURVE"} or getattr(obj, "hide_render", False):
                return None
            coordinates = [world_to_camera_view(scene, camera, obj.matrix_world @ Vector(corner)) for corner in obj.bound_box]
            front = [point for point in coordinates if point.z > 0]
            if not front:
                return {"inside_ratio": 0.0, "intersects": False, "bounds": None}
            inside = sum(0.0 <= point.x <= 1.0 and 0.0 <= point.y <= 1.0 for point in front)
            xs = [point.x for point in front]
            ys = [point.y for point in front]
            bounds = [min(xs), min(ys), max(xs), max(ys)]
            intersects = bounds[2] >= 0 and bounds[0] <= 1 and bounds[3] >= 0 and bounds[1] <= 1
            return {"inside_ratio": inside / len(front), "intersects": intersects, "bounds": bounds}

        target_objects = [obj for obj in target.all_objects if obj.type in {"MESH", "CURVE"} and not obj.hide_render]
        main_objects = [obj for obj in target_objects if "Orbit_" in obj.name or "Core" in obj.name]
        projected = [(obj, projection(obj)) for obj in main_objects]
        projected = [(obj, item) for obj, item in projected if item is not None]
        inside_ratio = sum(item["inside_ratio"] for _, item in projected) / max(len(projected), 1)
        bounds = [item["bounds"] for _, item in projected if item["bounds"]]
        if bounds:
            minimum_x = min(item[0] for item in bounds)
            minimum_y = min(item[1] for item in bounds)
            maximum_x = max(item[2] for item in bounds)
            maximum_y = max(item[3] for item in bounds)
            clipped_width = max(0.0, min(1.0, maximum_x) - max(0.0, minimum_x))
            clipped_height = max(0.0, min(1.0, maximum_y) - max(0.0, minimum_y))
            coverage = clipped_width * clipped_height
            center_offset = math.dist(((minimum_x + maximum_x) / 2, (minimum_y + maximum_y) / 2), (0.5, 0.5))
        else:
            coverage = 0.0
            center_offset = 1.0

        curve_visibility = []
        for obj, item in projected:
            if "Orbit_" in obj.name:
                curve_visibility.append(
                    {
                        "name": obj.name,
                        "uuid": str(obj.get("codex3d_uuid", "")) or None,
                        "inside_frame_ratio": round(item["inside_ratio"], 4),
                        "intersects_frame": bool(item["intersects"]),
                    }
                )
        unwanted = []
        target_set = set(target.all_objects)
        for obj in scene.objects:
            if obj in target_set or obj.type not in {"MESH", "CURVE"} or obj.hide_render:
                continue
            item = projection(obj)
            if item and item["intersects"]:
                unwanted.append({"name": obj.name, "uuid": str(obj.get("codex3d_uuid", "")) or None})

        result = evaluate_composition(
            inside_frame_ratio=inside_ratio,
            subject_frame_coverage=coverage,
            center_offset=center_offset,
            overexposed_pixel_ratio=overexposed_ratio,
            unwanted_visible_objects=unwanted,
            curve_visibility=curve_visibility,
        )
        return {
            **result,
            "target_collection": target_name,
            "main_structure_count": len(main_objects),
            "inside_frame_ratio": round(inside_ratio, 4),
            "subject_frame_coverage": round(coverage, 4),
            "center_offset": round(center_offset, 4),
            "edge_touch_crop_ratio": round(max(0.0, 1.0 - inside_ratio), 4),
            "overexposed_pixel_ratio": round(overexposed_ratio, 6),
            "unwanted_visible_objects": unwanted,
            "curve_visibility": curve_visibility,
        }


def _rounded_vector(value: Any) -> list[float]:
    return [round(float(value[index]), 6) for index in range(3)]


def _fingerprint(summary: dict[str, Any]) -> str:
    payload = json.dumps(summary, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _scene_summary_diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    left = {item.get("uuid") or item["name"]: item for item in before.get("objects", [])}
    right = {item.get("uuid") or item["name"]: item for item in after.get("objects", [])}
    return {
        "added": [right[key]["name"] for key in sorted(right.keys() - left.keys())],
        "removed": [left[key]["name"] for key in sorted(left.keys() - right.keys())],
        "changed": [
            {"before": left[key]["name"], "after": right[key]["name"]}
            for key in sorted(left.keys() & right.keys())
            if left[key] != right[key]
        ],
        "active_camera_changed": before.get("active_camera") != after.get("active_camera"),
    }
