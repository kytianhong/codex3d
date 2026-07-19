from codex3d_api import Codex3DApiService


def test_create_list_and_get_session() -> None:
    service = Codex3DApiService()
    session = service.create_session("Tiny studio")

    summaries = service.list_sessions()
    fetched = service.get_session(session.id)
    scene = service.get_session_scene(session.id)

    assert fetched is session
    assert summaries[0].id == session.id
    assert summaries[0].name == "Tiny studio"
    assert summaries[0].object_count == 0
    assert scene.id == session.scene.id
    assert scene.metadata["session_id"] == session.id


def test_health_returns_local_core_status() -> None:
    service = Codex3DApiService()

    assert service.health() == {"status": "ok", "service": "codex3d-api-core"}

