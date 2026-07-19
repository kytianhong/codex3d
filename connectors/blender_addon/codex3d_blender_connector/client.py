from __future__ import annotations

from .protocol_compat import (
    ConnectorHeartbeat,
    ConnectorPing,
    ConnectorRegistration,
    ConnectorStatus,
    ConnectorType,
)

from .manifest import CONNECTOR_CAPABILITIES, CONNECTOR_NAME, CONNECTOR_VERSION


def build_registration(
    name: str | None = None,
    version: str | None = None,
    metadata: dict | None = None,
) -> ConnectorRegistration:
    return ConnectorRegistration(
        connector_type=ConnectorType.BLENDER_ADDON,
        name=name or CONNECTOR_NAME,
        version=version or CONNECTOR_VERSION,
        capabilities=list(CONNECTOR_CAPABILITIES),
        status=ConnectorStatus.REGISTERED,
        metadata=metadata or {"blender_addon": True},
    )


def build_heartbeat(
    connector_id: str,
    status: ConnectorStatus = ConnectorStatus.ONLINE,
    metadata: dict | None = None,
) -> ConnectorHeartbeat:
    return ConnectorHeartbeat(
        connector_id=connector_id,
        status=status,
        metadata=metadata or {"source": "codex3d_blender_connector"},
    )


def build_ping(connector_id: str, metadata: dict | None = None) -> ConnectorPing:
    return ConnectorPing(
        connector_id=connector_id,
        metadata=metadata or {"source": "codex3d_blender_connector"},
    )


def register_with_service(service, name: str | None = None) -> ConnectorRegistration:
    registration = build_registration(name=name)
    return service.register_connector(registration)
