from codex3d_api.action_store import InMemoryActionStore
from codex3d_protocol import Action, ActionResult, ActionStatus, ActionType


def test_action_store_saves_actions_and_results_by_session_and_job() -> None:
    store = InMemoryActionStore()
    action = Action(type=ActionType.CREATE_OBJECT, parameters={"name": "C3D_Test"})
    result = ActionResult(action_id=action.id, status=ActionStatus.SUCCEEDED)

    store.save(action, session_id="session_1", job_id="job_1")
    store.save_result(result)

    assert store.get(action.id) is action
    assert store.list_for_session("session_1") == [action]
    assert store.list_for_job("job_1") == [action]
    assert store.get_result(action.id) is result

