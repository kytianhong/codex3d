from codex3d_api import Codex3DApiService
from codex3d_blender_connector import (
    build_heartbeat,
    build_ping,
    build_registration,
    register_with_service,
)
from codex3d_protocol import ConnectorCapability, ConnectorStatus


def test_build_registration_contains_handshake_capabilities() -> None:
    registration = build_registration(name="Unit Test Connector")

    assert registration.name == "Unit Test Connector"
    assert ConnectorCapability.PING in registration.capabilities
    assert ConnectorCapability.HEARTBEAT in registration.capabilities
    assert ConnectorCapability.INSPECT_SCENE in registration.capabilities
    assert ConnectorCapability.REPORT_VERSION in registration.capabilities


def test_register_with_service_heartbeat_and_ping() -> None:
    service = Codex3DApiService()
    registration = register_with_service(service)
    updated = service.connector_heartbeat(build_heartbeat(registration.id))
    ping = service.ping_connector(registration.id, build_ping(registration.id))

    assert service.get_connector(registration.id) is registration
    assert updated.status is ConnectorStatus.ONLINE
    assert ping.ok is True

