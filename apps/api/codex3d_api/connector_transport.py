from __future__ import annotations

import json
import socket
from typing import Any

from codex3d_protocol import (
    BRIDGE_PROTOCOL_VERSION,
    Action,
    ActionResult,
    BridgeMessageType,
    BridgeRequest,
    BridgeResponse,
    ConnectorSceneInspection,
    ErrorCode,
    ProtocolError,
    from_dict,
    to_json,
)


LOOPBACK_HOST = "127.0.0.1"
DEFAULT_PORT = 9876
MAX_FRAME_BYTES = 2 * 1024 * 1024


class ConnectorTransportError(RuntimeError):
    def __init__(self, error: ProtocolError) -> None:
        super().__init__(error.message)
        self.error = error


class SocketConnectorClient:
    def __init__(
        self,
        *,
        host: str = LOOPBACK_HOST,
        port: int = DEFAULT_PORT,
        token: str,
        connect_timeout: float = 2.0,
        request_timeout: float = 60.0,
        max_frame_bytes: int = MAX_FRAME_BYTES,
    ) -> None:
        if host != LOOPBACK_HOST:
            raise ValueError("SocketConnectorClient only permits 127.0.0.1.")
        self.host = host
        self.port = port
        self._token = token
        self.connect_timeout = connect_timeout
        self.request_timeout = request_timeout
        self.max_frame_bytes = max_frame_bytes
        self._closed = False

    def __enter__(self) -> SocketConnectorClient:
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def close(self) -> None:
        self._closed = True

    def hello(self) -> dict[str, Any]:
        return self.request(BridgeMessageType.HELLO).payload

    def ping(self) -> dict[str, Any]:
        return self.request(BridgeMessageType.PING).payload

    def inspect_scene(self) -> ConnectorSceneInspection:
        response = self.request(BridgeMessageType.INSPECT_SCENE)
        return from_dict(ConnectorSceneInspection, response.payload["inspection"])

    def execute_action(self, action: Action) -> ActionResult:
        response = self.request(BridgeMessageType.EXECUTE_ACTION, {"action": action}, raise_on_error=False)
        if "result" not in response.payload:
            self._raise_response_error(response)
        return from_dict(ActionResult, response.payload["result"])

    def execute_action_batch(self, actions: list[Action]) -> dict[str, Any]:
        response = self.request(
            BridgeMessageType.EXECUTE_ACTION_BATCH,
            {"actions": actions},
            raise_on_error=False,
        )
        if "results" not in response.payload:
            self._raise_response_error(response)
        payload = dict(response.payload)
        payload["results"] = [from_dict(ActionResult, item) for item in payload.get("results", [])]
        return payload

    def request(
        self,
        message_type: BridgeMessageType,
        payload: dict[str, Any] | None = None,
        *,
        raise_on_error: bool = True,
    ) -> BridgeResponse:
        if self._closed:
            raise ConnectorTransportError(
                ProtocolError(code=ErrorCode.CONNECTOR_OFFLINE, message="Socket connector client is closed.")
            )
        request = BridgeRequest(type=message_type, auth_token=self._token, payload=payload or {})
        wire = to_json(request).encode("utf-8") + b"\n"
        try:
            with socket.create_connection((self.host, self.port), timeout=self.connect_timeout) as connection:
                connection.settimeout(self.request_timeout)
                connection.sendall(wire)
                frame = self._read_frame(connection)
        except socket.timeout as exc:
            raise ConnectorTransportError(
                ProtocolError(
                    code=ErrorCode.REQUEST_TIMEOUT,
                    message=f"Blender bridge timed out at {self.host}:{self.port}.",
                    source="codex3d_api.connector_transport",
                    retryable=True,
                )
            ) from exc
        except (ConnectionError, OSError, TimeoutError, ValueError) as exc:
            raise ConnectorTransportError(
                ProtocolError(
                    code=ErrorCode.CONNECTOR_OFFLINE,
                    message=f"Blender bridge is offline at {self.host}:{self.port}.",
                    source="codex3d_api.connector_transport",
                    retryable=True,
                )
            ) from exc
        try:
            response = from_dict(BridgeResponse, json.loads(frame.decode("utf-8")))
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ConnectorTransportError(
                ProtocolError(
                    code=ErrorCode.INVALID_SCHEMA,
                    message="Blender bridge returned an invalid response.",
                    source="codex3d_api.connector_transport",
                )
            ) from exc
        if response.request_id != request.request_id:
            raise ConnectorTransportError(
                ProtocolError(
                    code=ErrorCode.INVALID_SCHEMA,
                    message="Blender bridge response request_id did not match the request.",
                    source="codex3d_api.connector_transport",
                )
            )
        if not response.ok and raise_on_error:
            self._raise_response_error(response)
        return response

    def _raise_response_error(self, response: BridgeResponse) -> None:
        raise ConnectorTransportError(
            response.error
            or ProtocolError(
                code=ErrorCode.ACTION_FAILED,
                message="Blender bridge request failed.",
                source="codex3d_api.connector_transport",
            )
        )

    def _read_frame(self, connection: socket.socket) -> bytes:
        chunks = bytearray()
        while True:
            chunk = connection.recv(min(65536, self.max_frame_bytes + 1 - len(chunks)))
            if not chunk:
                raise ConnectionError("Bridge closed before sending a complete response.")
            chunks.extend(chunk)
            newline = chunks.find(b"\n")
            if newline >= 0:
                return bytes(chunks[:newline])
            if len(chunks) > self.max_frame_bytes:
                raise ValueError("Bridge response frame is too large.")
