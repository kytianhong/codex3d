import json

from codex3d_mcp.tools import TOOL_DEFINITIONS, _compact_inspection


def test_restore_and_save_annotations_match_reversible_non_overwrite_semantics() -> None:
    tools = {item["name"]: item for item in TOOL_DEFINITIONS}
    restore = tools["blender_restore_snapshot"]
    save = tools["blender_save_checkpoint"]
    assert restore["annotations"] == {
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    }
    assert save["annotations"]["destructiveHint"] is False
    assert set(restore["inputSchema"]["required"]) == {"snapshot_id", "current_fingerprint", "snapshot_fingerprint"}


def test_compact_inspection_is_less_than_half_full_payload() -> None:
    objects = []
    for index in range(40):
        objects.append(
            {
                "label": f"C3D_Item_{index:02d}",
                "semantic_type": "curve" if index < 6 else "mesh",
                "blender_uuid": f"object_{index:032x}",
                "transform": {"location": {"x": index, "y": 0, "z": 0}, "rotation_euler": {"x": 0, "y": 0, "z": 0}, "scale": {"x": 1, "y": 1, "z": 1}},
                "dimensions": {"width": 1, "depth": 1, "height": 1},
                "metadata": {"collections": ["C3D_TEST"], "material_name": "C3D_Metal", "material": {"base_color": [0.1, 0.2, 0.3, 1], "roughness": 0.4}},
            }
        )
    full = {"scene": {"name": "Scene", "objects": objects, "metadata": {"active_camera": "Camera", "scene_fingerprint": "a" * 64}}, "metadata": {}}
    compact = _compact_inspection(full, {"collection": "C3D_TEST"})
    assert len(json.dumps(compact)) < len(json.dumps(full)) * 0.5
    assert compact["object_count"] == 40
    assert compact["scene_fingerprint"] == "a" * 64
