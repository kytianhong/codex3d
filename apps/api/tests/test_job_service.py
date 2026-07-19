from codex3d_api import Codex3DApiService, SubmitMessageRequest
from codex3d_protocol import JobStatus, JobType


def test_submit_message_creates_gettable_session_job() -> None:
    service = Codex3DApiService()
    session = service.create_session("Job demo")
    response = service.submit_message(
        session.id,
        SubmitMessageRequest(content="Please inspect this scene."),
    )

    job = service.get_job(response.job_id)
    session_jobs = service.list_session_jobs(session.id)

    assert job.type is JobType.AGENT_TURN
    assert job.status is JobStatus.SUCCEEDED
    assert job.id in session.job_ids
    assert session_jobs == [job]
    assert job.result["summary"] == response.summary

