import pytest

from codex3d_mcp import BridgeConfig, McpToolService, TOOL_DEFINITIONS
from codex3d_protocol import (
    ActionResult,
    ActionStatus,
    ActionType,
    ConnectorSceneInspection,
    ErrorCode,
    ProtocolError,
    Scene,
    SceneObject,
)


class StubClient:
    def __init__(self, fail_batch: bool = False) -> None:
        self.actions = []
        self.closed = False
        self.fail_batch = fail_batch

    def hello(self):
        return {"backend": "fake", "blender_version": "test"}

    def ping(self):
        return {"message": "pong"}

    def inspect_scene(self):
        scene = Scene(name="Stub scene", metadata={"object_count": 1})
        scene.add_object(SceneObject(label="C3D_Stub", semantic_type="cube"))
        return ConnectorSceneInspection(connector_id="stub", scene=scene, metadata={"object_count": 1})

    def execute_action(self, action):
        self.actions.append(action)
        return ActionResult(action_id=action.id, status=ActionStatus.SUCCEEDED, modified_object_ids=[action.parameters.get("target_name", action.parameters.get("name", ""))])

    def execute_action_batch(self, actions):
        self.actions.extend(actions)
        results = [ActionResult(action_id=action.id, status=ActionStatus.SUCCEEDED) for action in actions]
        if self.fail_batch:
            results = [results[0], ActionResult(action_id=actions[1].id, status=ActionStatus.FAILED, error=ProtocolError(code=ErrorCode.OBJECT_NOT_FOUND, message="missing"))]
            return {"results": results, "executed_count": 2, "succeeded_count": 1, "failed_count": 1, "unexecuted_count": len(actions) - 2}
        return {"results": results, "executed_count": len(actions), "succeeded_count": len(actions), "failed_count": 0, "unexecuted_count": 0}

    def close(self):
        self.closed = True


def _service(client=None):
    stub = client or StubClient()
    return McpToolService(BridgeConfig(token="test-token"), client_factory=lambda config: stub), stub


def test_ping_and_inspect_map_to_connector_client() -> None:
    service, stub = _service()

    ping = service.call_tool("blender_ping", {})
    inspection = service.call_tool("blender_inspect_scene", {})

    assert ping["ok"] is True and ping["ping"]["message"] == "pong"
    assert inspection["inspection"]["mode"] == "compact"
    assert inspection["inspection"]["objects"][0]["name"] == "C3D_Stub"
    assert stub.closed is True


@pytest.mark.parametrize(
    ("tool", "arguments", "action_type", "expected"),
    [
        ("blender_create_primitive", {"primitive": "cube", "name": "Cube", "location": [0, 0, 1], "dimensions": [1, 1, 1]}, ActionType.CREATE_OBJECT, {"primitive": "cube"}),
        ("blender_transform_object", {"target_name": "Cube", "location": [1, 2, 3]}, ActionType.TRANSFORM_OBJECT, {"target_name": "Cube"}),
        ("blender_rename_object", {"target_name": "Cube", "new_name": "Renamed"}, ActionType.MODIFY_OBJECT, {"new_name": "Renamed"}),
        ("blender_delete_object", {"target_name": "Cube"}, ActionType.DELETE_OBJECT, {"target_name": "Cube"}),
        ("blender_assign_material", {"target_name": "Cube", "material_name": "Blue", "base_color": [0.1, 0.2, 0.8, 1.0], "roughness": 0.4, "metallic": 0.2}, ActionType.ASSIGN_MATERIAL, {"target_name": "Cube"}),
        ("blender_set_point_light", {"target_name": "Light", "color": [1.0, 0.5, 0.2], "energy": 400}, ActionType.MODIFY_OBJECT, {"target_name": "Light"}),
    ],
)
def test_tools_map_to_existing_action_contract(tool, arguments, action_type, expected) -> None:
    service, stub = _service()

    result = service.call_tool(tool, arguments)

    assert result["ok"] is True
    assert stub.actions[-1].type is action_type
    for key, value in expected.items():
        assert stub.actions[-1].parameters[key] == value


def test_batch_success_returns_results_counts_and_final_inspection() -> None:
    service, stub = _service()
    actions = [
        {"type": "create_object", "parameters": {"primitive": "cube", "name": "One", "dimensions": [1, 1, 1]}},
        {"type": "transform_object", "parameters": {"target_name": "One", "location": [0, 0, 1]}},
    ]

    result = service.call_tool("blender_execute_batch", {"actions": actions})

    assert result["ok"] is True
    assert result["succeeded_count"] == 2
    assert result["failed_count"] == 0
    assert result["inspection"]["metadata"]["object_count"] == 1
    assert all(action.status is ActionStatus.PLANNED for action in stub.actions)


def test_batch_partial_failure_is_structured_and_still_inspects() -> None:
    service, _ = _service(StubClient(fail_batch=True))
    actions = [
        {"type": "create_object", "parameters": {"primitive": "cube", "name": "One", "dimensions": [1, 1, 1]}},
        {"type": "delete_object", "parameters": {"target_name": "Missing"}},
        {"type": "create_object", "parameters": {"primitive": "cube", "name": "Never", "dimensions": [1, 1, 1]}},
    ]

    result = service.call_tool("blender_execute_batch", {"actions": actions})

    assert result["ok"] is False
    assert result["executed_count"] == 2
    assert result["failed_count"] == 1
    assert result["unexecuted_count"] == 1
    assert "inspection" in result


def test_tool_schemas_include_units_enums_and_closed_objects() -> None:
    definitions = {tool["name"]: tool for tool in TOOL_DEFINITIONS}
    create = definitions["blender_create_primitive"]

    assert "meters" in create["description"]
    assert create["inputSchema"]["properties"]["primitive"]["enum"] == ["area_light", "cube", "cylinder", "empty", "plane", "point_light", "sphere"]
    assert all(tool["inputSchema"].get("additionalProperties") is False for tool in TOOL_DEFINITIONS)
    assert definitions["blender_inspect_scene"]["annotations"]["readOnlyHint"] is True
    assert definitions["blender_delete_object"]["annotations"]["destructiveHint"] is True


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        ("blender_ping", {"extra": True}),
        ("blender_inspect_scene", {"extra": True}),
        ("blender_create_primitive", {"primitive": "torus", "name": "Bad"}),
        ("blender_create_primitive", {"primitive": "cube", "name": "Bad", "dimensions": [1, -1, 1]}),
        ("blender_transform_object", {"target_name": "Cube"}),
        ("blender_transform_object", {"target_name": "Cube", "location": [0, 1]}),
        ("blender_rename_object", {"target_name": "Cube", "new_name": ""}),
        ("blender_delete_object", {}),
        ("blender_assign_material", {"target_name": "Cube", "material_name": "Bad", "base_color": [2, 0, 0, 1], "roughness": 0.5, "metallic": 0}),
        ("blender_set_point_light", {"target_name": "Light"}),
        ("blender_set_point_light", {"target_name": "Light", "energy": -1}),
        ("blender_execute_batch", {"actions": []}),
        ("blender_execute_batch", {"actions": [{"type": "render_preview", "parameters": {}}]}),
        ("blender_create_curve", {"name": "Bad", "points": [[0, 0, 0]]}),
        ("blender_create_camera", {"name": "Camera", "location": [0, 0, 1]}),
        ("blender_set_light", {"target_name": "Light", "size": 0}),
        ("blender_configure_world", {"color": [2, 0, 0], "strength": 0.1}),
        ("blender_configure_scene", {"engine": "CYCLES"}),
        ("blender_render", {"kind": "still", "path": "../escape.png"}),
        ("blender_save_checkpoint", {"path": "/tmp/escape.blend"}),
    ],
)
def test_every_tool_rejects_invalid_arguments_without_transport_call(tool, arguments) -> None:
    service, stub = _service()

    result = service.call_tool(tool, arguments)

    assert result["ok"] is False
    assert result["error"]["code"] == "invalid_arguments"
    assert stub.actions == []
