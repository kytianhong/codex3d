from pathlib import Path

from codex3d_mcp import BridgeConfig, Codex3DMcpServer, McpToolService
from codex3d_protocol import ActionResult, ActionStatus, ActionType


class CreativeStubClient:
    def __init__(self) -> None:
        self.actions = []

    def execute_action(self, action):
        self.actions.append(action)
        return ActionResult(
            action_id=action.id,
            status=ActionStatus.SUCCEEDED,
            output={"path": action.parameters.get("path", ""), "width": 512, "height": 512},
        )

    def close(self):
        pass


def _service(tmp_path: Path):
    stub = CreativeStubClient()
    config = BridgeConfig(token="secret", artifact_root=tmp_path, include_images=False)
    return McpToolService(config, client_factory=lambda _: stub), stub


def test_creative_tools_map_to_allowlisted_actions(tmp_path: Path) -> None:
    service, stub = _service(tmp_path)
    calls = [
        ("blender_create_curve", {"name": "Curve", "points": [[0, 0, 0], [1, 0, 0]], "cyclic": False}, ActionType.CREATE_OBJECT),
        ("blender_create_camera", {"name": "Camera", "location": [0, -6, 2], "look_at": [0, 0, 0]}, ActionType.CREATE_OBJECT),
        ("blender_set_parent", {"target_name": "Curve", "parent_name": "Root"}, ActionType.SET_PARENT),
        ("blender_configure_world", {"color": [0.01, 0.02, 0.03], "strength": 0.1}, ActionType.CONFIGURE_WORLD),
        ("blender_configure_scene", {"engine": "BLENDER_EEVEE_NEXT", "resolution_x": 512, "resolution_y": 512, "samples": 32, "transparent": False, "fps": 24, "frame_start": 1, "frame_end": 72}, ActionType.CONFIGURE_SCENE),
        ("blender_keyframe_object", {"target_name": "Root", "keyframes": [{"frame": 1, "rotation": [0, 0, 0]}]}, ActionType.KEYFRAME_OBJECT),
        ("blender_render", {"kind": "still", "path": "preview.png"}, ActionType.RENDER_PREVIEW),
        ("blender_save_checkpoint", {"path": "scene.blend"}, ActionType.SAVE_CHECKPOINT),
        ("blender_create_snapshot", {"snapshot_id": "snapshot_demo"}, ActionType.SNAPSHOT_SCENE),
        ("blender_list_snapshots", {}, ActionType.LIST_SNAPSHOTS),
        (
            "blender_restore_snapshot",
            {"snapshot_id": "snapshot_demo", "current_fingerprint": "0" * 64, "snapshot_fingerprint": "1" * 64},
            ActionType.RESTORE_SNAPSHOT,
        ),
        ("blender_delete_snapshot", {"snapshot_id": "snapshot_demo"}, ActionType.DELETE_SNAPSHOT),
        ("blender_reconcile_object_ids", {"prefix": "C3D_"}, ActionType.RECONCILE_OBJECT_IDS),
    ]
    for tool, arguments, action_type in calls:
        result = service.call_tool(tool, arguments)
        assert result["ok"] is True, result
        assert stub.actions[-1].type is action_type


def test_advanced_material_maps_emission_and_transmission(tmp_path: Path) -> None:
    service, stub = _service(tmp_path)
    result = service.call_tool(
        "blender_assign_material",
        {"target_name": "Core", "material_name": "Glow", "base_color": [0.1, 0.2, 0.4, 1], "roughness": 0.2, "metallic": 0.4, "emission_color": [0.2, 0.5, 1, 1], "emission_strength": 6, "transmission": 0.1},
    )

    assert result["ok"] is True
    assert stub.actions[-1].parameters["material"]["emission_strength"] == 6
    assert stub.actions[-1].parameters["material"]["transmission"] == 0.1


def test_uuid_is_preferred_for_transform_and_material(tmp_path: Path) -> None:
    service, stub = _service(tmp_path)
    transformed = service.call_tool(
        "blender_transform_object",
        {"target_uuid": "object_abc", "location": [0, 0, 1]},
    )
    assert transformed["ok"] is True
    assert stub.actions[-1].parameters["target_uuid"] == "object_abc"

    material = service.call_tool(
        "blender_assign_material",
        {"target_uuid": "object_abc", "material_name": "Warm", "base_color": [1, 0.5, 0.1, 1], "roughness": 0.3, "metallic": 0.5},
    )
    assert material["ok"] is True
    assert stub.actions[-1].parameters["target_uuid"] == "object_abc"


def test_still_render_can_return_validated_mcp_image_content(tmp_path: Path) -> None:
    (tmp_path / "preview.png").write_bytes(b"\x89PNG\r\n\x1a\nFAKE")
    stub = CreativeStubClient()
    service = McpToolService(
        BridgeConfig(token="secret", artifact_root=tmp_path, include_images=True),
        client_factory=lambda _: stub,
    )
    response = Codex3DMcpServer(service).handle_message(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "blender_render", "arguments": {"kind": "still", "path": "preview.png"}},
        }
    )

    content = response["result"]["content"]
    assert content[1]["type"] == "image"
    assert content[1]["mimeType"] == "image/png"
    assert "data" not in response["result"]["structuredContent"]
