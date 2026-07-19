from __future__ import annotations

from codex3d_protocol import (
    ConnectorHeartbeat,
    ConnectorRegistration,
    ConnectorStatus,
    utc_now_iso,
)

from .store import StoreNotFoundError


class InMemoryConnectorStore:
    def __init__(self) -> None:
        self._connectors: dict[str, ConnectorRegistration] = {}

    def register(self, registration: ConnectorRegistration) -> ConnectorRegistration:
        self._connectors[registration.id] = registration
        return registration

    def get(self, connector_id: str) -> ConnectorRegistration:
        try:
            return self._connectors[connector_id]
        except KeyError as exc:
            raise StoreNotFoundError("connector", connector_id) from exc

    def list(self) -> list[ConnectorRegistration]:
        return sorted(self._connectors.values(), key=lambda connector: connector.created_at)

    def update_heartbeat(
        self,
        heartbeat: ConnectorHeartbeat,
    ) -> ConnectorRegistration:
        connector = self.get(heartbeat.connector_id)
        connector.status = heartbeat.status
        connector.last_seen_at = heartbeat.sent_at
        connector.metadata["last_heartbeat"] = dict(heartbeat.metadata)
        self._connectors[connector.id] = connector
        return connector

    def mark_stale(self, connector_id: str) -> ConnectorRegistration:
        connector = self.get(connector_id)
        connector.status = ConnectorStatus.STALE
        connector.last_seen_at = utc_now_iso()
        self._connectors[connector.id] = connector
        return connector

