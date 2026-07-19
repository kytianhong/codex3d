from codex3d_api import Codex3DApiService
from codex3d_api.serialization import api_to_dict
from codex3d_blender_connector import build_heartbeat, build_ping, build_registration
from codex3d_protocol import ConnectorCapability


def test_direct_connector_handshake_flow() -> None:
    service = Codex3DApiService()
    registration = service.register_connector(build_registration(name="Flow Connector"))
    heartbeat = service.connector_heartbeat(build_heartbeat(registration.id))
    ping = service.ping_connector(registration.id, build_ping(registration.id))

    data = api_to_dict({"registration": registration, "heartbeat": heartbeat, "ping": ping})

    assert registration.name == "Flow Connector"
    assert ConnectorCapability.INSPECT_SCENE in registration.capabilities
    assert heartbeat.id == registration.id
    assert ping.ok is True
    assert data["ping"]["status"] == "online"

