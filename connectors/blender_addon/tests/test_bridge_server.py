import json
import socket
import threading
import time

import pytest

from codex3d_blender_connector import (
    BlenderActionExecutor,
    BlenderBridgeRuntime,
    BridgeServer,
    BridgeServerError,
    FakeBlenderBackend,
)
from codex3d_protocol import BRIDGE_PROTOCOL_VERSION, BridgeMessageType, BridgeRequest, ErrorCode, to_dict


TOKEN = "unit-test-secret"


def _runtime() -> BlenderBridgeRuntime:
    return BlenderBridgeRuntime(BlenderActionExecutor(FakeBlenderBackend()))


def _raw_request(address, payload: bytes) -> dict:
    with socket.create_connection(address, timeout=1.0) as client:
        client.sendall(payload + b"\n")
        data = bytearray()
        while b"\n" not in data:
            chunk = client.recv(4096)
            if not chunk:
                break
            data.extend(chunk)
    return json.loads(bytes(data).split(b"\n", 1)[0])


def _request_data(**updates) -> dict:
    data = to_dict(BridgeRequest(type=BridgeMessageType.PING, auth_token=TOKEN))
    data.update(updates)
    return data


def test_server_rejects_non_loopback_and_requires_token() -> None:
    server = BridgeServer(_runtime())

    with pytest.raises(BridgeServerError):
        server.start("0.0.0.0", 0, TOKEN)
    with pytest.raises(BridgeServerError):
        server.start("127.0.0.1", 0, "")


def test_server_start_stop_is_idempotent_and_loopback_only() -> None:
    server = BridgeServer(_runtime())
    first = server.start(port=0, token=TOKEN)
    second = server.start(port=0, token=TOKEN)

    assert first == second
    assert first[0] == "127.0.0.1"
    server.stop()
    server.stop()
    assert server.is_running is False


def test_server_reports_port_conflict() -> None:
    first = BridgeServer(_runtime())
    second = BridgeServer(_runtime())
    address = first.start(port=0, token=TOKEN)
    try:
        with pytest.raises(BridgeServerError) as caught:
            second.start(port=address[1], token=TOKEN)
        assert caught.value.error.code is ErrorCode.CONNECTOR_OFFLINE
    finally:
        first.stop()


@pytest.mark.parametrize(
    ("updates", "expected_code"),
    [
        ({"protocol_version": "9.9"}, "invalid_schema"),
        ({"type": "run_python"}, "unsupported_operation"),
        ({"auth_token": ""}, "authentication_failed"),
        ({"auth_token": "wrong"}, "authentication_failed"),
    ],
)
def test_server_returns_structured_validation_errors(updates, expected_code) -> None:
    server = BridgeServer(_runtime(), request_timeout=0.5)
    address = server.start(port=0, token=TOKEN)
    try:
        response = _raw_request(address, json.dumps(_request_data(**updates)).encode())
    finally:
        server.stop()

    assert response["ok"] is False
    assert response["error"]["code"] == expected_code
    assert TOKEN not in json.dumps(response)


def test_server_handles_malformed_json_without_stopping() -> None:
    server = BridgeServer(_runtime(), request_timeout=0.5)
    address = server.start(port=0, token=TOKEN)
    try:
        malformed = _raw_request(address, b"{not-json")
        assert server.is_running is True
    finally:
        server.stop()

    assert malformed["error"]["code"] == "invalid_schema"


def test_server_rejects_oversized_frame_and_closes_connection() -> None:
    server = BridgeServer(_runtime(), max_frame_bytes=128)
    address = server.start(port=0, token=TOKEN)
    try:
        response = _raw_request(address, b"x" * 129)
    finally:
        server.stop()

    assert response["error"]["code"] == "frame_too_large"


def test_server_shutdown_returns_error_to_pending_request() -> None:
    runtime = _runtime()
    server = BridgeServer(runtime, request_timeout=5.0)
    address = server.start(port=0, token=TOKEN)
    result = {}

    def call_server() -> None:
        result.update(_raw_request(address, json.dumps(_request_data()).encode()))

    caller = threading.Thread(target=call_server)
    caller.start()
    deadline = time.monotonic() + 1.0
    while runtime.pending_count == 0 and time.monotonic() < deadline:
        time.sleep(0.005)
    server.stop()
    caller.join(1.0)

    assert result["error"]["code"] == "bridge_shutdown"
