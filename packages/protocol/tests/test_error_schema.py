from codex3d_protocol import ErrorCode, ErrorSeverity, ProtocolError


def test_protocol_error_is_data_not_exception() -> None:
    error = ProtocolError(
        code=ErrorCode.OBJECT_NOT_FOUND,
        message="Object was not found in the scene.",
        severity=ErrorSeverity.WARNING,
        source="scene_lookup",
        retryable=False,
        details={"object_id": "object_missing"},
    )

    assert error.code is ErrorCode.OBJECT_NOT_FOUND
    assert error.severity is ErrorSeverity.WARNING
    assert error.details["object_id"] == "object_missing"
    assert error.created_at

