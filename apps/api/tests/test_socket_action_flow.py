import threading

from codex3d_api import SocketConnectorClient, plan_demo_prompt
from codex3d_blender_connector import BlenderActionExecutor, BlenderBridgeRuntime, BridgeServer, FakeBlenderBackend


def test_fake_bridge_integration_creates_expected_demo_scene() -> None:
    token = "fake-integration-token"
    backend = FakeBlenderBackend()
    runtime = BlenderBridgeRuntime(BlenderActionExecutor(backend))
    server = BridgeServer(runtime, request_timeout=2.0)
    address = server.start(port=0, token=token)
    stopping = threading.Event()

    def pump() -> None:
        while not stopping.is_set():
            runtime.pump_once()
            stopping.wait(0.002)

    pump_thread = threading.Thread(target=pump)
    pump_thread.start()
    try:
        plan = plan_demo_prompt("Create a cozy wooden desk scene with a chair, lamp, and warm lighting.")
        client = SocketConnectorClient(port=address[1], token=token)
        batch = client.execute_action_batch(plan.actions)
        inspection = client.inspect_scene()
    finally:
        stopping.set()
        server.stop()
        pump_thread.join(1.0)

    names = {item.label for item in inspection.scene.objects}
    assert batch["succeeded_count"] == 31
    assert batch["failed_count"] == 0
    assert len(inspection.scene.objects) == 16
    assert {"C3D_DeskTop", "C3D_ChairSeat", "C3D_LampBase", "C3D_WarmLampLight"} <= names
