from codex3d_blender_connector import (
    AddonLifecycleController,
    FakeBlenderBackend,
    generate_token,
)
from codex3d_protocol import BridgeStatus


class _Timers:
    def __init__(self) -> None:
        self.callback = None

    def register(self, callback, **kwargs) -> None:
        self.callback = callback

    def unregister(self, callback) -> None:
        self.callback = None

    def is_registered(self, callback) -> bool:
        return self.callback == callback


class _FakeBpy:
    app = type("App", (), {"timers": _Timers(), "version_string": "5.1.1-test"})()


class _FakeServer:
    def __init__(self, runtime) -> None:
        self.runtime = runtime
        self.is_running = False
        self.bound_address = None
        self.stop_count = 0

    def start(self, host, port, token):
        self.is_running = True
        self.bound_address = (host, 19000 if port == 0 else port)
        return self.bound_address

    def stop(self) -> None:
        self.stop_count += 1
        self.is_running = False
        self.runtime.shutdown()


def test_lifecycle_connect_disconnect_cleans_server_and_timer() -> None:
    created = []

    def server_factory(runtime):
        server = _FakeServer(runtime)
        created.append(server)
        return server

    controller = AddonLifecycleController(
        backend_factory=lambda bpy: FakeBlenderBackend(),
        server_factory=server_factory,
    )
    address = controller.connect(_FakeBpy(), port=0, token="token")

    assert address == ("127.0.0.1", 19000)
    assert controller.state.status is BridgeStatus.CONNECTED
    assert controller.runtime is not None and controller.runtime.timer_registered

    controller.disconnect()
    controller.disconnect()

    assert controller.state.status is BridgeStatus.DISCONNECTED
    assert _FakeBpy.app.timers.callback is None
    assert created[0].stop_count == 1


def test_repeated_connect_reuses_running_server() -> None:
    created = []

    def server_factory(runtime):
        server = _FakeServer(runtime)
        created.append(server)
        return server

    controller = AddonLifecycleController(
        backend_factory=lambda bpy: FakeBlenderBackend(),
        server_factory=server_factory,
    )
    first = controller.connect(_FakeBpy(), port=9876, token="token")
    second = controller.connect(_FakeBpy(), port=9876, token="token")
    controller.disconnect()

    assert first == second
    assert len(created) == 1


def test_generated_tokens_are_nonempty_and_unique() -> None:
    first = generate_token()
    second = generate_token()

    assert len(first) >= 32
    assert first != second
