from codex3d_api import Codex3DApiService, MessageRole, SubmitMessageRequest
from codex3d_api.serialization import api_to_dict, api_to_json
from codex3d_protocol import ActionType


def test_submit_message_saves_user_message_and_mock_job() -> None:
    service = Codex3DApiService()
    session = service.create_session("Message demo")
    response = service.submit_message(
        session.id,
        SubmitMessageRequest(
            content="Make a small wooden desk for a beginner-friendly studio.",
            metadata={"source": "test"},
        ),
    )

    fetched = service.get_session(session.id)
    job = service.get_job(response.job_id)

    assert fetched.messages[0].role is MessageRole.USER
    assert fetched.messages[0].content.startswith("Make a small wooden desk")
    assert fetched.messages[0].metadata["source"] == "test"
    assert response.action_ids
    assert job.action_id == response.action_ids[0]


def test_desk_prompt_produces_create_object_like_mock_action() -> None:
    service = Codex3DApiService()
    session = service.create_session("Desk demo")
    response = service.submit_message(
        session.id,
        SubmitMessageRequest(content="请创建一个小书桌，适合温暖的工作室。"),
    )
    job = service.get_job(response.job_id)
    scene = service.get_session_scene(session.id)

    assert scene.objects
    assert scene.objects[0].semantic_type == "desk"
    assert scene.objects[0].metadata["mock"] is True
    assert job.result["actions"][0]["type"] == ActionType.CREATE_OBJECT.value
    assert "desk" in response.summary


def test_api_serialization_outputs_json_friendly_payloads() -> None:
    service = Codex3DApiService()
    session = service.create_session("Serialization demo")
    response = service.submit_message(
        session.id,
        SubmitMessageRequest(content="Inspect the current scene."),
    )

    response_dict = api_to_dict(response)
    response_json = api_to_json(response)
    session_dict = api_to_dict(service.get_session(session.id))

    assert response_dict["session_id"] == session.id
    assert response_dict["job_id"] == response.job_id
    assert '"job_id"' in response_json
    assert session_dict["status"] == "active"
    assert session_dict["messages"][0]["role"] == "user"

