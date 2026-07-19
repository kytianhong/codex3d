from __future__ import annotations

from .client import build_heartbeat, build_ping, build_registration
from .inspection import inspect_scene
from .manifest import CONNECTOR_NAME


def main() -> None:
    registration = build_registration()
    heartbeat = build_heartbeat(registration.id)
    ping = build_ping(registration.id)
    inspection = inspect_scene(connector_id=registration.id)

    print(f"connector_name: {CONNECTOR_NAME}")
    print(f"registration_id: {registration.id}")
    print(f"capabilities: {','.join(capability.value for capability in registration.capabilities)}")
    print(f"ping_payload_connector_id: {ping.connector_id}")
    print(f"heartbeat_status: {heartbeat.status.value}")
    print(f"inspected_scene_object_count: {len(inspection.scene.objects)}")


if __name__ == "__main__":
    main()
