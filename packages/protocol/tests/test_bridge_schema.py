from codex3d_protocol import (
    BRIDGE_PROTOCOL_VERSION,
    BridgeMessageType,
    BridgeRequest,
    BridgeResponse,
    ErrorCode,
    ProtocolError,
    from_dict,
    to_dict,
)


def test_bridge_request_response_round_trip_and_correlation() -> None:
    request = BridgeRequest(type=BridgeMessageType.PING, auth_token="local-secret")
    response = BridgeResponse(
        request_id=request.request_id,
        type="ping_result",
        ok=True,
        payload={"message": "pong"},
    )

    restored_request = from_dict(BridgeRequest, to_dict(request))
    restored_response = from_dict(BridgeResponse, to_dict(response))

    assert restored_request.protocol_version == BRIDGE_PROTOCOL_VERSION
    assert restored_request.type is BridgeMessageType.PING
    assert restored_response.request_id == request.request_id
    assert restored_response.payload == {"message": "pong"}


def test_bridge_response_round_trips_protocol_error() -> None:
    response = BridgeResponse(
        request_id="request_bad",
        type="error",
        error=ProtocolError(code=ErrorCode.INVALID_SCHEMA, message="bad request"),
    )

    restored = from_dict(BridgeResponse, to_dict(response))

    assert restored.error is not None
    assert restored.error.code is ErrorCode.INVALID_SCHEMA
