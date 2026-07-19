import json
import socket
import threading
import time
from contextlib import contextmanager

import pytest

from codex3d_api import ConnectorTransportError, SocketConnectorClient
from codex3d_blender_connector import (
    BlenderActionExecutor,
    BlenderBridgeRuntime,
    BridgeServer,
    FakeBlenderBackend,
)
from codex3d_protocol import (
    Action,
    ActionStatus,
    ActionType,
    BridgeResponse,
    ErrorCode,
    to_json,
)


TOKEN = "socket-client-test"


@contextmanager
def _running_bridge():
    backend = FakeBlenderBackend()
    runtime = BlenderBridgeRuntime(BlenderActionExecutor(backend), blender_version="test-blender")
    server = BridgeServer(runtime, request_timeout=1.0)
    address = server.start(port=0, token=TOKEN)
    stopping = threading.Event()

    def pump() -> None:
        while not stopping.is_set():
            runtime.pump_once()
            stopping.wait(0.002)

    pump_thread = threading.Thread(target=pump, name="TestBlenderMainThread")
    pump_thread.start()
    try:
        yield address, backend, runtime
    finally:
        stopping.set()
        server.stop()
        pump_thread.join(1.0)


def _create(name: str, primitive: str = "cube") -> Action:
    return Action(
        type=ActionType.CREATE_OBJECT,
        parameters={"primitive": primitive, "name": name, "dimensions": [1.0, 1.0, 1.0]},
    )


def test_client_hello_ping_inspect_and_execute_one_action() -> None:
    with _running_bridge() as (address, backend, runtime):
        with SocketConnectorClient(port=address[1], token=TOKEN) as client:
            hello = client.hello()
            ping = client.ping()
            result = client.execute_action(_create("C3D_SocketCube"))
            inspection = client.inspect_scene()

    assert hello["backend"] == "fake"
    assert ping["message"] == "pong"
    assert result.status is ActionStatus.SUCCEEDED
    assert inspection.metadata["object_count"] == 1
    assert backend.object_exists("C3D_SocketCube")
    assert runtime.last_execution_thread_id is not None


def test_client_batch_returns_structured_fail_fast_result() -> None:
    with _running_bridge() as (address, backend, _):
        client = SocketConnectorClient(port=address[1], token=TOKEN)
        batch = client.execute_action_batch(
            [
                _create("C3D_First"),
                Action(type=ActionType.DELETE_OBJECT, parameters={"target_name": "Missing"}),
                _create("C3D_Last"),
            ]
        )

    assert batch["executed_count"] == 2
    assert batch["failed_count"] == 1
    assert batch["unexecuted_count"] == 1
    assert batch["results"][-1].status is ActionStatus.FAILED
    assert not backend.object_exists("C3D_Last")


def test_client_wrong_token_does_not_leak_secret() -> None:
    secret = "wrong-secret-that-must-not-leak"
    with _running_bridge() as (address, _, _):
        client = SocketConnectorClient(port=address[1], token=secret)
        with pytest.raises(ConnectorTransportError) as caught:
            client.ping()

    assert caught.value.error.code is ErrorCode.AUTHENTICATION_FAILED
    assert secret not in str(caught.value)
    assert secret not in json.dumps(caught.value.error.details)


def test_client_rejects_non_loopback_and_reports_offline() -> None:
    with pytest.raises(ValueError):
        SocketConnectorClient(host="0.0.0.0", token=TOKEN)

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    listener.close()
    with pytest.raises(ConnectorTransportError) as caught:
        SocketConnectorClient(port=port, token=TOKEN, connect_timeout=0.1).ping()
    assert caught.value.error.code is ErrorCode.CONNECTOR_OFFLINE


def test_client_handles_partial_tcp_response_reads() -> None:
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    address = listener.getsockname()

    def fragmented_server() -> None:
        connection, _ = listener.accept()
        with connection:
            request = json.loads(connection.makefile("rb").readline())
            wire = to_json(
                BridgeResponse(
                    request_id=request["request_id"],
                    type="ping_result",
                    ok=True,
                    payload={"message": "pong"},
                )
            ).encode() + b"\n"
            for chunk in (wire[:3], wire[3:17], wire[17:]):
                connection.sendall(chunk)
                time.sleep(0.002)
        listener.close()

    thread = threading.Thread(target=fragmented_server)
    thread.start()
    result = SocketConnectorClient(port=address[1], token=TOKEN).ping()
    thread.join(1.0)

    assert result["message"] == "pong"


def test_client_timeout_is_distinct_from_offline() -> None:
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    address = listener.getsockname()

    def slow_server() -> None:
        connection, _ = listener.accept()
        with connection:
            connection.recv(4096)
            time.sleep(0.2)
        listener.close()

    thread = threading.Thread(target=slow_server)
    thread.start()
    with pytest.raises(ConnectorTransportError) as caught:
        SocketConnectorClient(port=address[1], token=TOKEN, request_timeout=0.03).ping()
    thread.join(1.0)

    assert caught.value.error.code is ErrorCode.REQUEST_TIMEOUT
