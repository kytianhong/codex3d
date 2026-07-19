from codex3d_protocol import (
    ConnectorCapability,
    ConnectorHeartbeat,
    ConnectorPing,
    ConnectorPingResult,
    ConnectorRegistration,
    ConnectorSceneInspection,
    ConnectorStatus,
    ConnectorType,
    Scene,
    SceneObject,
    to_dict,
)


def test_connector_schema_constructs_and_serializes() -> None:
    registration = ConnectorRegistration(
        connector_type=ConnectorType.BLENDER_ADDON,
        name="Local Blender",
        version="0.1.0",
        capabilities=[
            ConnectorCapability.PING,
            ConnectorCapability.HEARTBEAT,
            ConnectorCapability.INSPECT_SCENE,
        ],
    )
    heartbeat = ConnectorHeartbeat(
        connector_id=registration.id,
        status=ConnectorStatus.ONLINE,
    )
    ping = ConnectorPing(connector_id=registration.id)
    result = ConnectorPingResult(
        connector_id=registration.id,
        ok=True,
        status=ConnectorStatus.ONLINE,
        message="pong",
    )
    scene = Scene(name="Connector scene")
    scene.add_object(SceneObject(label="Cube", semantic_type="mesh"))
    inspection = ConnectorSceneInspection(connector_id=registration.id, scene=scene)

    data = to_dict(
        {
            "registration": registration,
            "heartbeat": heartbeat,
            "ping": ping,
            "result": result,
            "inspection": inspection,
        }
    )

    assert data["registration"]["connector_type"] == "blender_addon"
    assert "ping" in data["registration"]["capabilities"]
    assert data["heartbeat"]["status"] == "online"
    assert data["result"]["ok"] is True
    assert data["inspection"]["scene"]["objects"][0]["label"] == "Cube"

