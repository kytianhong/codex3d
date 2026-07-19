from codex3d_api import Codex3DApiService, SubmitMessageRequest
from codex3d_api.demo_planner import STANDARD_HACKATHON_PROMPT
from codex3d_blender_connector import BlenderActionExecutor, FakeBlenderBackend
from codex3d_protocol import (
    ActionStatus,
    ConnectorCapability,
    ConnectorRegistration,
    ConnectorStatus,
    ConnectorType,
)


def test_end_to_end_fake_action_execution_flow() -> None:
    service = Codex3DApiService()
    session = service.create_session("Fake E2E")
    connector = service.register_connector(
        ConnectorRegistration(
            connector_type=ConnectorType.LOCAL_SIMULATED,
            capabilities=[
                ConnectorCapability.EXECUTE_ACTION,
                ConnectorCapability.INSPECT_SCENE,
            ],
            status=ConnectorStatus.ONLINE,
        )
    )
    backend = FakeBlenderBackend()
    executor = BlenderActionExecutor(backend)
    service.bind_connector_action_handler(connector.id, executor.execute)

    response = service.plan_demo_message(
        session.id,
        SubmitMessageRequest(content=STANDARD_HACKATHON_PROMPT),
    )
    actions = service.list_session_actions(session.id)
    results = service.execute_session_plan(session.id, connector.id)
    inspection = backend.inspect(connector_id=connector.id)
    object_names = {obj.label for obj in inspection.scene.objects}

    assert response.metadata["planner"] == "deterministic_demo"
    assert len(actions) == len(response.action_ids)
    assert len(results) == len(actions)
    assert all(result.status is ActionStatus.SUCCEEDED for result in results)
    assert {
        "C3D_DeskTop",
        "C3D_ChairSeat",
        "C3D_LampBase",
        "C3D_WarmLampLight",
    }.issubset(object_names)
    assert len(inspection.scene.objects) >= 16
    assert service.get_action_result(actions[0].id).status is ActionStatus.SUCCEEDED
