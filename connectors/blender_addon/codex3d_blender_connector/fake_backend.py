from __future__ import annotations

from dataclasses import asdict, dataclass, field
import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .protocol_compat import (
    ConnectorSceneInspection,
    Dimensions,
    Scene,
    SceneObject,
    SceneObjectSourceType,
    Transform,
    Vector3,
    new_id,
    utc_now_iso,
)
from .artifact_paths import resolve_artifact_path


@dataclass
class FakeBlenderObject:
    name: str
    primitive: str
    semantic_type: str
    codex3d_uuid: str = field(default_factory=lambda: new_id("object"))
    location: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale: list[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    dimensions: list[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    material: dict[str, Any] | None = None
    light: dict[str, Any] | None = None
    curve: dict[str, Any] | None = None
    camera: dict[str, Any] | None = None
    parent_name: str | None = None
    collection: str | None = None
    keyframes: list[dict[str, Any]] = field(default_factory=list)


class FakeBlenderBackend:
    backend_name = "fake"

    def __init__(self, artifact_root: str | Path | None = None, session_id: str | None = None) -> None:
        self.objects: dict[str, FakeBlenderObject] = {}
        self.artifact_root = artifact_root or os.environ.get("CODEX3D_ARTIFACT_ROOT")
        self.session_id = session_id or os.environ.get("CODEX3D_SESSION_ID") or "local_session"
        self.world: dict[str, Any] = {"color": [0.0, 0.0, 0.0], "strength": 0.0}
        self.scene_settings: dict[str, Any] = {
            "engine": "BLENDER_EEVEE_NEXT",
            "resolution_x": 512,
            "resolution_y": 512,
            "samples": 32,
            "transparent": False,
            "fps": 24,
            "frame_start": 1,
            "frame_end": 72,
        }
        self._snapshots: dict[str, dict[str, Any]] = {}

    def object_exists(self, name: str) -> bool:
        return self._find_object(name) is not None

    def object_uuid(self, identifier: str) -> str | None:
        obj = self._find_object(identifier)
        return obj.codex3d_uuid if obj else None

    def create_object(self, params: dict[str, Any]) -> str:
        primitive = params["primitive"]
        name = params["name"]
        dimensions = list(params.get("dimensions", _default_dimensions(primitive)))
        obj = FakeBlenderObject(
            name=name,
            primitive=primitive,
            semantic_type=params.get("semantic_type", primitive),
            codex3d_uuid=params.get("object_uuid") or new_id("object"),
            location=list(params.get("location", [0.0, 0.0, 0.0])),
            rotation=list(params.get("rotation", [0.0, 0.0, 0.0])),
            scale=list(params.get("scale", [1.0, 1.0, 1.0])),
            dimensions=dimensions,
            light=dict(params.get("light", {})) if primitive in {"point_light", "area_light"} else None,
            curve={
                key: params[key]
                for key in ("points", "curve_type", "cyclic", "bevel_depth", "bevel_resolution", "fill_mode")
                if key in params
            } or None,
            camera={"focal_length": params.get("focal_length", 50.0), "look_at": params.get("look_at")}
            if primitive == "camera"
            else None,
            collection=params.get("collection"),
        )
        self.objects[name] = obj
        return name

    def transform_object(self, params: dict[str, Any]) -> str:
        obj = self._require_object(self._target(params))
        if "location" in params:
            obj.location = list(params["location"])
        if "rotation" in params:
            obj.rotation = list(params["rotation"])
        if "scale" in params:
            obj.scale = list(params["scale"])
        if "dimensions" in params:
            obj.dimensions = list(params["dimensions"])
        if "look_at" in params:
            obj.camera = obj.camera or {}
            obj.camera["look_at"] = params["look_at"]
        return obj.name

    def modify_object(self, params: dict[str, Any]) -> str:
        obj = self._require_object(self._target(params))
        if "light" in params:
            if obj.primitive not in {"point_light", "area_light"}:
                raise ValueError(f"Target is not a light: {obj.name}")
            obj.light = obj.light or {}
            obj.light.update(params["light"])
        if "camera" in params:
            if obj.primitive != "camera":
                raise ValueError(f"Target is not a camera: {obj.name}")
            obj.camera = obj.camera or {}
            obj.camera.update(params["camera"])
        if "new_name" in params:
            new_name = params["new_name"]
            self.objects.pop(obj.name)
            obj.name = new_name
            self.objects[new_name] = obj
        return obj.name

    def delete_object(self, params: dict[str, Any]) -> str:
        obj = self._require_object(self._target(params))
        self.objects.pop(obj.name)
        return obj.name

    def assign_material(self, params: dict[str, Any]) -> str:
        obj = self._require_object(self._target(params))
        obj.material = dict(params["material"])
        return obj.name

    def set_parent(self, params: dict[str, Any]) -> str:
        obj = self._require_object(self._target(params))
        self._require_object(params["parent_name"])
        obj.parent_name = params["parent_name"]
        return obj.name

    def configure_world(self, params: dict[str, Any]) -> dict[str, Any]:
        self.world = {"color": list(params["color"]), "strength": params["strength"]}
        return {"world_color": list(params["color"]), "world_strength": params["strength"]}

    def configure_scene(self, params: dict[str, Any]) -> dict[str, Any]:
        self.scene_settings.update(params)
        return dict(self.scene_settings)

    def keyframe_object(self, params: dict[str, Any]) -> dict[str, Any]:
        obj = self._require_object(self._target(params))
        obj.keyframes = [dict(item) for item in params["keyframes"]]
        return {
            "object_name": obj.name,
            "inserted_keyframes": sum(len(item) - 1 for item in obj.keyframes),
            "frame_start": self.scene_settings["frame_start"],
            "frame_end": self.scene_settings["frame_end"],
            "keyframe_count": sum(len(item.keyframes) for item in self.objects.values()),
            "fcurve_count": sum(
                len({field for keyframe in item.keyframes for field in keyframe if field != "frame"})
                for item in self.objects.values()
            ),
            "animated_object_count": sum(bool(item.keyframes) for item in self.objects.values()),
        }

    def render(self, params: dict[str, Any]) -> dict[str, Any]:
        kind = params.get("kind", "still")
        path, relative = resolve_artifact_path(
            self.artifact_root,
            params["path"],
            allowed_suffixes={".png"} if kind == "still" else {".mp4"},
        )
        path.write_bytes(b"CODEX3D_FAKE_RENDER")
        result = {
            "path": relative,
            "mime": "image/png" if kind == "still" else "video/mp4",
            "file_size": path.stat().st_size,
            "width": self.scene_settings["resolution_x"],
            "height": self.scene_settings["resolution_y"],
            "active_camera": next((obj.name for obj in self.objects.values() if obj.primitive == "camera"), None),
            "mean_luminance": 0.5,
            "nonblack_pixel_ratio": 1.0,
            "nontransparent_pixel_ratio": 1.0,
            "visible_subject_count": len(self.objects),
            "subject_visible": bool(self.objects),
            "render_kind": kind,
            "fallback": False,
            "animation_format": "mp4" if kind == "animation" else None,
            "overexposed_pixel_ratio": 0.0,
            "composition": {
                "passed": True,
                "failures": [],
                "inside_frame_ratio": 1.0,
                "subject_frame_coverage": 0.5,
                "center_offset": 0.0,
                "edge_touch_crop_ratio": 0.0,
                "overexposed_pixel_ratio": 0.0,
                "unwanted_visible_objects": [],
                "curve_visibility": [],
            },
        }
        result.update(self.scene_settings)
        return result

    def save_checkpoint(self, params: dict[str, Any]) -> dict[str, Any]:
        requested = params.get("path") or f"checkpoints/{self.session_id}.blend"
        path, relative = resolve_artifact_path(self.artifact_root, requested, allowed_suffixes={".blend"})
        path, relative = self._versioned_artifact_path(path, relative)
        summary = self._canonical_scene_summary()
        fingerprint = _fingerprint(summary)
        temporary = path.with_name(f".{path.name}.tmp")
        payload = json.dumps({"objects": [asdict(item) for item in self.objects.values()]}, sort_keys=True)
        temporary.write_text(payload, encoding="utf-8")
        os.replace(temporary, path)
        return {
            "path": relative,
            "mime": "application/x-blender",
            "file_size": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "scene_fingerprint": fingerprint,
            "uuid_count": sum(bool(item["uuid"]) for item in summary["objects"]),
            "versioned": relative != requested,
            "session_id": self.session_id,
        }

    def create_snapshot(self, params: dict[str, Any]) -> dict[str, Any]:
        snapshot_id = params.get("snapshot_id") or new_id("snapshot")
        blend_path, blend_relative = self._snapshot_path(snapshot_id, ".blend")
        metadata_path, metadata_relative = self._snapshot_path(snapshot_id, ".json")
        if snapshot_id in self._snapshots or blend_path.exists() or metadata_path.exists():
            raise FileExistsError(f"Snapshot already exists and cannot be overwritten: {snapshot_id}")
        summary = self._canonical_scene_summary()
        fingerprint = _fingerprint(summary)
        self.scene_settings["accepted_snapshot_id"] = snapshot_id
        self.scene_settings["accepted_snapshot_fingerprint"] = fingerprint
        state = {
            "objects": copy.deepcopy(self.objects),
            "world": copy.deepcopy(self.world),
            "scene_settings": copy.deepcopy(self.scene_settings),
        }
        blend_path.write_text(json.dumps({"objects": [asdict(item) for item in self.objects.values()]}), encoding="utf-8")
        metadata = {
            "snapshot_id": snapshot_id,
            "session_id": self.session_id,
            "created_at": utc_now_iso(),
            "source_action_id": params.get("source_action_id"),
            "source_turn": params.get("source_turn"),
            "scene_fingerprint": fingerprint,
            "object_uuids": [item["uuid"] for item in summary["objects"]],
            "object_count": len(summary["objects"]),
            "active_camera": summary["active_camera"],
            "blend_path": blend_relative,
            "metadata_path": metadata_relative,
            "file_size": blend_path.stat().st_size,
            "scene_summary": summary,
        }
        metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
        self._snapshots[snapshot_id] = {"metadata": metadata, "state": state}
        return metadata

    def list_snapshots(self, params: dict[str, Any]) -> dict[str, Any]:
        snapshots = [copy.deepcopy(item["metadata"]) for _, item in sorted(self._snapshots.items())]
        return {"snapshots": snapshots, "snapshot_count": len(snapshots)}

    def restore_snapshot(self, params: dict[str, Any]) -> dict[str, Any]:
        snapshot_id = params["snapshot_id"]
        if snapshot_id not in self._snapshots:
            raise KeyError(f"Snapshot not found: {snapshot_id}")
        item = self._snapshots[snapshot_id]
        if item["metadata"].get("session_id") != self.session_id:
            raise PermissionError("Snapshot belongs to a different Codex3D session.")
        current_summary = self._canonical_scene_summary()
        current_fingerprint = _fingerprint(current_summary)
        expected = item["metadata"]["scene_fingerprint"]
        if params.get("current_fingerprint") != current_fingerprint:
            raise ValueError("current_fingerprint does not match the live scene.")
        if params.get("snapshot_fingerprint") != expected:
            raise ValueError("snapshot_fingerprint does not match the registered snapshot.")
        safety_id = new_id("snapshot_pre_restore")
        safety = self.create_snapshot({"snapshot_id": safety_id, "source_turn": "pre_restore"})
        self.objects = copy.deepcopy(item["state"]["objects"])
        self.world = copy.deepcopy(item["state"]["world"])
        self.scene_settings = copy.deepcopy(item["state"]["scene_settings"])
        summary = self._canonical_scene_summary()
        fingerprint = _fingerprint(summary)
        if fingerprint != expected:
            safety_item = self._snapshots[safety_id]
            self.objects = copy.deepcopy(safety_item["state"]["objects"])
            self.world = copy.deepcopy(safety_item["state"]["world"])
            self.scene_settings = copy.deepcopy(safety_item["state"]["scene_settings"])
            raise ValueError("Restored scene does not match the snapshot fingerprint.")
        return {
            "snapshot_id": snapshot_id,
            "restored": True,
            "scene_fingerprint": fingerprint,
            "object_count": len(self.objects),
            "active_camera": summary["active_camera"],
            "scene_summary": summary,
            "safety_snapshot_id": safety_id,
            "safety_snapshot_fingerprint": safety["scene_fingerprint"],
            "scene_diff": _scene_summary_diff(current_summary, summary),
            "session_id": self.session_id,
        }

    def delete_snapshot(self, params: dict[str, Any]) -> dict[str, Any]:
        snapshot_id = params["snapshot_id"]
        if snapshot_id not in self._snapshots:
            raise KeyError(f"Snapshot not found: {snapshot_id}")
        self._snapshots.pop(snapshot_id)
        removed = []
        for suffix in (".blend", ".json"):
            path, relative = self._snapshot_path(snapshot_id, suffix)
            if path.exists():
                path.unlink()
                removed.append(relative)
        return {"snapshot_id": snapshot_id, "deleted": True, "removed_paths": removed}

    def reconcile_object_ids(self, params: dict[str, Any]) -> dict[str, Any]:
        prefix = params.get("prefix", "C3D_")
        assigned = []
        existing = []
        for obj in self.objects.values():
            if not obj.name.startswith(prefix):
                continue
            if obj.codex3d_uuid:
                existing.append({"name": obj.name, "uuid": obj.codex3d_uuid})
            else:
                obj.codex3d_uuid = new_id("object")
                assigned.append({"name": obj.name, "uuid": obj.codex3d_uuid})
        return {"prefix": prefix, "assigned": assigned, "existing": existing, "assigned_count": len(assigned)}

    def inspect(self, connector_id: str = "") -> ConnectorSceneInspection:
        scene = Scene(
            name="Fake Blender Scene",
            metadata={
                "blender_available": False,
                "blender_backend": "fake",
                "object_count": len(self.objects),
                "world": dict(self.world),
                "render": dict(self.scene_settings),
                "accepted_snapshot_id": self.scene_settings.get("accepted_snapshot_id"),
                "accepted_snapshot_fingerprint": self.scene_settings.get("accepted_snapshot_fingerprint"),
            },
        )
        for obj in self.objects.values():
            scene.add_object(_to_scene_object(obj))
        inspection = ConnectorSceneInspection(
            connector_id=connector_id,
            scene=scene,
            metadata={
                "blender_available": False,
                "blender_backend": "fake",
                "object_count": len(scene.objects),
                "object_names": [obj.name for obj in self.objects.values()],
            },
        )
        fingerprint = _fingerprint(self._canonical_scene_summary())
        inspection.metadata["scene_fingerprint"] = fingerprint
        inspection.metadata["session_id"] = self.session_id
        inspection.scene.metadata["scene_fingerprint"] = fingerprint
        return inspection

    def _find_object(self, identifier: str) -> FakeBlenderObject | None:
        if identifier in self.objects:
            return self.objects[identifier]
        return next((item for item in self.objects.values() if item.codex3d_uuid == identifier), None)

    def _require_object(self, identifier: str) -> FakeBlenderObject:
        obj = self._find_object(identifier)
        if obj is None:
            raise KeyError(identifier)
        return obj

    def _target(self, params: dict[str, Any]) -> str:
        return params.get("target_uuid") or params["target_name"]

    def _snapshot_path(self, snapshot_id: str, suffix: str) -> tuple[Path, str]:
        if not snapshot_id.startswith("snapshot_") or not all(char.isalnum() or char == "_" for char in snapshot_id):
            raise ValueError("snapshot_id must use the generated snapshot_ identifier format.")
        return resolve_artifact_path(
            self.artifact_root,
            f"snapshots/{snapshot_id}{suffix}",
            allowed_suffixes={suffix},
        )

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
        objects = []
        for obj in sorted(self.objects.values(), key=lambda item: (item.codex3d_uuid, item.name)):
            objects.append(
                {
                    "uuid": obj.codex3d_uuid,
                    "name": obj.name,
                    "type": obj.primitive,
                    "location": [round(value, 6) for value in obj.location],
                    "rotation": [round(value, 6) for value in obj.rotation],
                    "scale": [round(value, 6) for value in obj.scale],
                    "dimensions": [round(value, 6) for value in obj.dimensions],
                    "material": obj.material.get("name") if obj.material else None,
                }
            )
        active_camera = next((item.name for item in self.objects.values() if item.primitive == "camera"), None)
        return {
            "objects": objects,
            "active_camera": active_camera,
            "frame_start": self.scene_settings["frame_start"],
            "frame_end": self.scene_settings["frame_end"],
            "animation": {
                "keyframes": {
                    item.codex3d_uuid: copy.deepcopy(item.keyframes)
                    for item in sorted(self.objects.values(), key=lambda candidate: candidate.codex3d_uuid)
                    if item.keyframes
                }
            },
        }


def _to_scene_object(obj: FakeBlenderObject) -> SceneObject:
    return SceneObject(
        label=obj.name,
        semantic_type=obj.semantic_type,
        source_type=SceneObjectSourceType.EXISTING_BLENDER_OBJECT,
        blender_uuid=obj.codex3d_uuid,
        transform=Transform(
            location=Vector3(*obj.location),
            rotation_euler=Vector3(*obj.rotation),
            scale=Vector3(*obj.scale),
        ),
        dimensions=Dimensions(*obj.dimensions),
        metadata={
            "blender_backend": "fake",
            "codex3d_uuid": obj.codex3d_uuid,
            "primitive": obj.primitive,
            "material_name": obj.material.get("name") if obj.material else None,
            "material": dict(obj.material) if obj.material else None,
            "light": dict(obj.light) if obj.light else None,
            "curve": dict(obj.curve) if obj.curve else None,
            "camera": dict(obj.camera) if obj.camera else None,
            "parent_name": obj.parent_name,
            "collection": obj.collection,
            "keyframe_count": len(obj.keyframes),
        },
    )


def _default_dimensions(primitive: str) -> list[float]:
    if primitive == "plane":
        return [1.0, 1.0, 0.0]
    if primitive == "point_light":
        return [0.0, 0.0, 0.0]
    return [1.0, 1.0, 1.0]


def _fingerprint(summary: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(summary, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


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
