import codex3d_protocol


def test_protocol_package_imports() -> None:
    assert codex3d_protocol.__version__ == "0.1.0"
    assert codex3d_protocol.Scene
    assert codex3d_protocol.SceneObject
    assert codex3d_protocol.Action
    assert codex3d_protocol.ToolCall
    assert codex3d_protocol.ActionResult
    assert codex3d_protocol.Job
    assert codex3d_protocol.ConnectorRegistration
    assert codex3d_protocol.ConnectorPingResult
    assert codex3d_protocol.Asset
    assert codex3d_protocol.Provenance
    assert codex3d_protocol.ProtocolError
