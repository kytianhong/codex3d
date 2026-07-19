from __future__ import annotations

from .models import SubmitMessageRequest
from .serialization import api_to_json
from .service import Codex3DApiService


def main() -> None:
    service = Codex3DApiService()
    health = service.health()
    session = service.create_session("Smoke Demo")
    response = service.submit_message(
        session.id,
        SubmitMessageRequest(content="Create a small wooden desk for a cozy studio."),
    )
    job = service.get_job(response.job_id)
    scene = service.get_session_scene(session.id)

    print(f"health: {health['status']}")
    print(f"created_session_id: {session.id}")
    print(f"submitted_message_id: {response.message_id}")
    print(f"created_job_id: {job.id}")
    print(f"mock_action_summary: {response.summary}")
    print(f"scene_object_count: {len(scene.objects)}")
    print(f"response_json: {api_to_json(response)}")


if __name__ == "__main__":
    main()

