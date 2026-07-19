from codex3d_api import Codex3DApiService
from codex3d_protocol import (
    ConnectorCapability,
    ConnectorHeartbeat,
    ConnectorRegistration,
    ConnectorStatus,
)


def test_connector_service_registers_lists_and_gets_connector() -> None:
    service = Codex3DApiService()
    registration = service.register_connector(
        ConnectorRegistration(
            name="Test Blender",
            capabilities=[ConnectorCapability.PING, ConnectorCapability.HEARTBEAT],
        )
    )

    connectors = service.list_connectors()
    fetched = service.get_connector(registration.id)

    assert fetched is registration
    assert connectors == [registration]
    assert fetched.status is ConnectorStatus.REGISTERED


def test_connector_heartbeat_updates_status_and_last_seen() -> None:
    service = Codex3DApiService()
    registration = service.register_connector()
    updated = service.connector_heartbeat(
        ConnectorHeartbeat(
            connector_id=registration.id,
            status=ConnectorStatus.ONLINE,
            sent_at="2026-07-18T12:00:00Z",
            metadata={"source": "test"},
        )
    )

    assert updated.status is ConnectorStatus.ONLINE
    assert updated.last_seen_at == "2026-07-18T12:00:00Z"
    assert updated.metadata["last_heartbeat"]["source"] == "test"


def test_ping_registered_and_missing_connector() -> None:
    service = Codex3DApiService()
    registration = service.register_connector()

    ok_result = service.ping_connector(registration.id)
    missing_result = service.ping_connector("connector_missing")

    assert ok_result.ok is True
    assert ok_result.status is ConnectorStatus.ONLINE
    assert ok_result.message == "pong"
    assert missing_result.ok is False
    assert missing_result.error is not None
    assert "not found" in missing_result.message

