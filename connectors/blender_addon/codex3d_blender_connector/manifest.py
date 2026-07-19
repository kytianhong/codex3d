from .protocol_compat import ConnectorCapability

CONNECTOR_NAME = "Codex3D Blender Connector"
CONNECTOR_VERSION = "0.1.0"
CONNECTOR_CAPABILITIES = [
    ConnectorCapability.PING,
    ConnectorCapability.HEARTBEAT,
    ConnectorCapability.INSPECT_SCENE,
    ConnectorCapability.REPORT_VERSION,
    ConnectorCapability.EXECUTE_ACTION,
]
RESERVED_CAPABILITIES = [
    ConnectorCapability.RENDER_PREVIEW,
    ConnectorCapability.SNAPSHOT_SCENE,
    ConnectorCapability.RESTORE_SNAPSHOT,
]
