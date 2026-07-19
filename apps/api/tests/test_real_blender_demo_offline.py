import socket

from examples.real_blender_bridge_demo import main


def test_external_demo_returns_nonzero_when_bridge_is_offline() -> None:
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    listener.close()

    assert main(["--port", str(port), "--token", "offline-test-token"]) != 0
