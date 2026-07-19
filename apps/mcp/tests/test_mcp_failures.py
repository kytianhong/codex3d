import pytest

from codex3d_api import ConnectorTransportError
from codex3d_mcp import BridgeConfig, ConfigurationError, McpToolService
from codex3d_protocol import ErrorCode, ProtocolError


class FailingClient:
    def __init__(self, error):
        self.error = error

    def hello(self):
        if isinstance(self.error, Exception):
            raise self.error
        raise ConnectorTransportError(self.error)

    def close(self):
        pass


@pytest.mark.parametrize(
    "code",
    [ErrorCode.CONNECTOR_OFFLINE, ErrorCode.AUTHENTICATION_FAILED, ErrorCode.REQUEST_TIMEOUT, ErrorCode.INVALID_SCHEMA],
)
def test_transport_failures_become_structured_tool_errors(code) -> None:
    error = ProtocolError(code=code, message=f"transport failed: {code.value}")
    service = McpToolService(BridgeConfig(token="secret"), client_factory=lambda config: FailingClient(error))

    result = service.call_tool("blender_ping", {})

    assert result["ok"] is False
    assert result["error"]["code"] == code.value


def test_missing_token_is_reported_without_startup_failure() -> None:
    service = McpToolService(BridgeConfig(token=""))

    result = service.call_tool("blender_ping", {})

    assert result["error"]["code"] == "configuration_error"


def test_token_is_redacted_from_unexpected_errors_and_details() -> None:
    token = "very-private-token"
    service = McpToolService(
        BridgeConfig(token=token),
        client_factory=lambda config: FailingClient(RuntimeError(f"unexpected {token}")),
    )

    result = service.call_tool("blender_ping", {})

    assert token not in str(result)
    assert "[REDACTED]" in result["error"]["message"]


def test_environment_configuration_is_loopback_only() -> None:
    with pytest.raises(ConfigurationError):
        BridgeConfig.from_env({"CODEX3D_BRIDGE_HOST": "0.0.0.0"})
    with pytest.raises(ConfigurationError):
        BridgeConfig.from_env({"CODEX3D_BRIDGE_PORT": "bad"})


def test_unknown_tool_is_structured_error() -> None:
    service = McpToolService(BridgeConfig(token="secret"))

    result = service.call_tool("run_python", {"code": "pass"})

    assert result["ok"] is False
    assert result["error"]["code"] == "invalid_arguments"
