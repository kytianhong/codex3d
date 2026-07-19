from __future__ import annotations

from codex3d_protocol import (
    ConnectorCapability,
    ConnectorHeartbeat,
    ConnectorPing,
    ConnectorPingResult,
    ConnectorRegistration,
    ConnectorStatus,
    ConnectorType,
    ErrorCode,
    ProtocolError,
    utc_now_iso,
)

from .connector_store import InMemoryConnectorStore
from .store import StoreNotFoundError


DEFAULT_CONNECTOR_CAPABILITIES = [
    ConnectorCapability.PING,
    ConnectorCapability.HEARTBEAT,
    ConnectorCapability.INSPECT_SCENE,
    ConnectorCapability.REPORT_VERSION,
]


class ConnectorService:
    def __init__(self, store: InMemoryConnectorStore | None = None) -> None:
        self.store = store or InMemoryConnectorStore()

    def register_connector(
        self,
        registration: ConnectorRegistration | None = None,
        *,
        name: str | None = None,
        version: str = "0.1.0",
        connector_type: ConnectorType = ConnectorType.BLENDER_ADDON,
        capabilities: list[ConnectorCapability] | None = None,
        metadata: dict | None = None,
    ) -> ConnectorRegistration:
        created = registration or ConnectorRegistration(
            connector_type=connector_type,
            name=name or "Codex3D Blender Connector",
            version=version,
            capabilities=capabilities or list(DEFAULT_CONNECTOR_CAPABILITIES),
            metadata=metadata or {},
        )
        if not created.capabilities:
            created.capabilities = list(DEFAULT_CONNECTOR_CAPABILITIES)
        created.status = (
            created.status
            if created.status in {ConnectorStatus.ONLINE, ConnectorStatus.REGISTERED}
            else ConnectorStatus.REGISTERED
        )
        created.last_seen_at = created.last_seen_at or utc_now_iso()
        return self.store.register(created)

    def get_connector(self, connector_id: str) -> ConnectorRegistration:
        return self.store.get(connector_id)

    def list_connectors(self) -> list[ConnectorRegistration]:
        return self.store.list()

    def heartbeat(
        self,
        heartbeat: ConnectorHeartbeat | None = None,
        *,
        connector_id: str | None = None,
        status: ConnectorStatus = ConnectorStatus.ONLINE,
        metadata: dict | None = None,
    ) -> ConnectorRegistration:
        event = heartbeat or ConnectorHeartbeat(
            connector_id=connector_id or "",
            status=status,
            metadata=metadata or {},
        )
        return self.store.update_heartbeat(event)

    def ping(
        self,
        connector_id: str,
        ping: ConnectorPing | None = None,
    ) -> ConnectorPingResult:
        try:
            connector = self.store.get(connector_id)
        except StoreNotFoundError:
            error = ProtocolError(
                code=ErrorCode.OBJECT_NOT_FOUND,
                message=f"connector not found: {connector_id}",
                source="codex3d_api.connector_service",
                details={"connector_id": connector_id},
            )
            return ConnectorPingResult(
                connector_id=connector_id,
                ok=False,
                status=ConnectorStatus.ERROR,
                message=error.message,
                error=error,
                metadata={"ping_sent_at": ping.sent_at if ping else None},
            )

        connector.last_seen_at = utc_now_iso()
        if connector.status in {ConnectorStatus.REGISTERED, ConnectorStatus.STALE}:
            connector.status = ConnectorStatus.ONLINE
            self.store.register(connector)

        return ConnectorPingResult(
            connector_id=connector.id,
            ok=connector.status is not ConnectorStatus.ERROR,
            status=connector.status,
            message="pong",
            metadata={
                "connector_name": connector.name,
                "connector_version": connector.version,
                "ping_sent_at": ping.sent_at if ping else None,
            },
        )

