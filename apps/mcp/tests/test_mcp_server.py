import io
import json
import os
import subprocess
import sys
from pathlib import Path

from codex3d_mcp import BridgeConfig, Codex3DMcpServer, McpToolService


class _PingClient:
    def hello(self):
        return {"backend": "fake", "connector_version": "0.1.0"}

    def ping(self):
        return {"message": "pong"}

    def close(self):
        pass


def _server() -> Codex3DMcpServer:
    service = McpToolService(BridgeConfig(token="test-token"), client_factory=lambda config: _PingClient())
    return Codex3DMcpServer(service)


def test_initialize_negotiates_protocol_and_declares_tools() -> None:
    response = _server().handle_message(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}}
    )

    assert response["result"]["protocolVersion"] == "2025-06-18"
    assert response["result"]["serverInfo"]["name"] == "codex3d-mcp"
    assert response["result"]["capabilities"]["tools"]["listChanged"] is False


def test_tools_list_exposes_structured_creative_tools() -> None:
    response = _server().handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    tools = response["result"]["tools"]

    assert len(tools) == 23
    assert {tool["name"] for tool in tools} == {
        "blender_ping",
        "blender_inspect_scene",
        "blender_create_primitive",
        "blender_transform_object",
        "blender_rename_object",
        "blender_delete_object",
        "blender_assign_material",
        "blender_set_point_light",
        "blender_create_curve",
        "blender_create_camera",
        "blender_set_light",
        "blender_set_parent",
        "blender_configure_world",
        "blender_configure_scene",
        "blender_keyframe_object",
        "blender_render",
        "blender_save_checkpoint",
        "blender_create_snapshot",
        "blender_list_snapshots",
        "blender_restore_snapshot",
        "blender_delete_snapshot",
        "blender_reconcile_object_ids",
        "blender_execute_batch",
    }
    assert all(tool["description"] and tool["inputSchema"]["type"] == "object" for tool in tools)


def test_tools_call_returns_text_and_structured_content() -> None:
    response = _server().handle_message(
        {"jsonrpc": "2.0", "id": "call-1", "method": "tools/call", "params": {"name": "blender_ping", "arguments": {}}}
    )
    result = response["result"]

    assert result["isError"] is False
    assert result["structuredContent"]["ping"]["message"] == "pong"
    assert json.loads(result["content"][0]["text"])["ok"] is True


def test_notifications_do_not_emit_responses() -> None:
    assert _server().handle_message({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_parse_and_method_errors_are_jsonrpc_errors() -> None:
    parse_error = _server().handle_line(b"{bad json\n")
    method_error = _server().handle_message({"jsonrpc": "2.0", "id": 4, "method": "unknown"})

    assert parse_error["error"]["code"] == -32700
    assert method_error["error"]["code"] == -32601


def test_stdio_run_processes_initialize_list_and_call() -> None:
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "blender_ping", "arguments": {}}},
    ]
    stdin = io.BytesIO(b"".join(json.dumps(item).encode() + b"\n" for item in messages))
    stdout = io.BytesIO()

    assert _server().run(stdin, stdout) == 0
    responses = [json.loads(line) for line in stdout.getvalue().splitlines()]

    assert [item["id"] for item in responses] == [1, 2, 3]
    assert responses[-1]["result"]["structuredContent"]["ok"] is True


def test_module_entrypoint_serves_initialize_over_stdio() -> None:
    request = json.dumps({"jsonrpc": "2.0", "id": 9, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}}) + "\n"
    root = Path(__file__).resolve().parents[3]
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(root / "packages" / "protocol"), str(root / "apps" / "api"), str(root / "apps" / "mcp")]
    )
    completed = subprocess.run(
        [sys.executable, "-m", "codex3d_mcp"],
        input=request,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    response = json.loads(completed.stdout)
    assert completed.returncode == 0
    assert response["result"]["serverInfo"]["name"] == "codex3d-mcp"
    assert completed.stderr == ""
