import threading

from codex3d_blender_connector import BlenderActionExecutor, BlenderBridgeRuntime, FakeBlenderBackend
from codex3d_protocol import (
    Action,
    ActionStatus,
    ActionType,
    BridgeMessageType,
    BridgeRequest,
    ErrorCode,
)


def _runtime(max_requests_per_tick: int = 4) -> BlenderBridgeRuntime:
    return BlenderBridgeRuntime(
        BlenderActionExecutor(FakeBlenderBackend()),
        max_requests_per_tick=max_requests_per_tick,
        blender_version="5.1.1",
    )


def _create(name: str) -> Action:
    return Action(
        type=ActionType.CREATE_OBJECT,
        parameters={"primitive": "cube", "name": name, "dimensions": [1.0, 1.0, 1.0]},
    )


def test_runtime_handles_hello_ping_and_inspection() -> None:
    runtime = _runtime()

    hello = runtime.execute_request(BridgeRequest(type=BridgeMessageType.HELLO))
    ping = runtime.execute_request(BridgeRequest(type=BridgeMessageType.PING))
    inspection = runtime.execute_request(BridgeRequest(type=BridgeMessageType.INSPECT_SCENE))

    assert hello.payload["blender_version"] == "5.1.1"
    assert ping.payload["message"] == "pong"
    assert inspection.payload["inspection"]["metadata"]["object_count"] == 0


def test_runtime_executes_single_action() -> None:
    runtime = _runtime()
    action = _create("C3D_BridgeCube")

    response = runtime.execute_request(
        BridgeRequest(type=BridgeMessageType.EXECUTE_ACTION, payload={"action": action})
    )

    assert response.ok is True
    assert response.payload["result"]["status"] == "succeeded"
    assert runtime.executor.backend.object_exists("C3D_BridgeCube")


def test_runtime_batch_is_fail_fast() -> None:
    runtime = _runtime()
    actions = [
        _create("C3D_First"),
        Action(type=ActionType.DELETE_OBJECT, parameters={"target_name": "Missing"}),
        _create("C3D_Unexecuted"),
    ]

    response = runtime.execute_request(
        BridgeRequest(type=BridgeMessageType.EXECUTE_ACTION_BATCH, payload={"actions": actions})
    )

    assert response.ok is False
    assert response.payload["executed_count"] == 2
    assert response.payload["failed_count"] == 1
    assert response.payload["unexecuted_count"] == 1
    assert not runtime.executor.backend.object_exists("C3D_Unexecuted")


def test_pump_limits_requests_per_tick() -> None:
    runtime = _runtime(max_requests_per_tick=2)
    pending = [runtime.enqueue(BridgeRequest(type=BridgeMessageType.PING), 1.0) for _ in range(3)]

    assert runtime.pump_once(max_requests=99) == 2
    assert sum(item.event.is_set() for item in pending) == 2
    assert runtime.pending_count == 1


def test_executor_runs_on_pump_thread() -> None:
    runtime = _runtime()
    pending = runtime.enqueue(
        BridgeRequest(type=BridgeMessageType.EXECUTE_ACTION, payload={"action": _create("C3D_Threaded")}),
        1.0,
    )
    handler_thread_id = threading.get_ident()
    pump_thread = threading.Thread(target=runtime.pump_once)
    pump_thread.start()
    pump_thread.join()

    assert pending.event.is_set()
    assert runtime.last_execution_thread_id == pump_thread.ident
    assert runtime.last_execution_thread_id != handler_thread_id


def test_shutdown_wakes_pending_requests() -> None:
    runtime = _runtime()
    pending = runtime.enqueue(BridgeRequest(type=BridgeMessageType.PING), 60.0)

    runtime.shutdown("test shutdown")

    assert pending.event.is_set()
    assert pending.response is not None
    assert pending.response.error is not None
    assert pending.response.error.code is ErrorCode.BRIDGE_SHUTDOWN


class _FakeTimers:
    def __init__(self) -> None:
        self.callback = None

    def register(self, callback, **kwargs) -> None:
        self.callback = callback

    def unregister(self, callback) -> None:
        assert callback == self.callback
        self.callback = None

    def is_registered(self, callback) -> bool:
        return callback == self.callback


def test_timer_lifecycle_is_idempotent() -> None:
    runtime = _runtime()
    timers = _FakeTimers()
    bpy = type("FakeBpy", (), {"app": type("App", (), {"timers": timers})()})()

    runtime.start_timer(bpy)
    runtime.start_timer(bpy)
    runtime.stop_timer()
    runtime.stop_timer()

    assert runtime.timer_registered is False
    assert timers.callback is None
