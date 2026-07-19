import threading

from codex3d_blender_connector import BlenderActionExecutor, BlenderBridgeRuntime, BridgeServer, FakeBlenderBackend
from codex3d_mcp import BridgeConfig, McpToolService


def test_mcp_tools_drive_existing_socket_bridge_and_fake_executor() -> None:
    token = "mcp-socket-integration"
    backend = FakeBlenderBackend()
    runtime = BlenderBridgeRuntime(BlenderActionExecutor(backend))
    server = BridgeServer(runtime, request_timeout=2.0)
    address = server.start(port=0, token=token)
    stopping = threading.Event()

    def pump() -> None:
        while not stopping.is_set():
            runtime.pump_once()
            stopping.wait(0.002)

    pump_thread = threading.Thread(target=pump, name="FakeBlenderMainThread")
    pump_thread.start()
    try:
        service = McpToolService(BridgeConfig(port=address[1], token=token))
        batch = service.call_tool(
            "blender_execute_batch",
            {
                "actions": [
                    {"type": "create_object", "parameters": {"primitive": "cube", "name": "C3D_MCP_Test", "dimensions": [1, 1, 1]}},
                    {"type": "transform_object", "parameters": {"target_name": "C3D_MCP_Test", "location": [0, 0, 1], "scale": [1.2, 0.8, 1.5]}},
                    {"type": "assign_material", "parameters": {"target_name": "C3D_MCP_Test", "material": {"name": "C3D_MCP_Blue", "base_color": [0.1, 0.2, 0.8, 1.0], "roughness": 0.4, "metallic": 0.1}}},
                ]
            },
        )
    finally:
        stopping.set()
        server.stop()
        pump_thread.join(1.0)

    assert batch["ok"] is True
    assert batch["succeeded_count"] == 3
    assert batch["inspection"]["scene"]["objects"][0]["label"] == "C3D_MCP_Test"
    assert batch["inspection"]["scene"]["objects"][0]["metadata"]["material_name"] == "C3D_MCP_Blue"
