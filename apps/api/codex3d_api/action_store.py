from __future__ import annotations

from codex3d_protocol import Action, ActionResult

from .store import StoreNotFoundError


class InMemoryActionStore:
    def __init__(self) -> None:
        self._actions: dict[str, Action] = {}
        self._results_by_action_id: dict[str, ActionResult] = {}
        self._session_action_ids: dict[str, list[str]] = {}
        self._job_action_ids: dict[str, list[str]] = {}

    def save(
        self,
        action: Action,
        *,
        session_id: str | None = None,
        job_id: str | None = None,
    ) -> Action:
        self._actions[action.id] = action
        if session_id is not None:
            ids = self._session_action_ids.setdefault(session_id, [])
            if action.id not in ids:
                ids.append(action.id)
        if job_id is not None:
            ids = self._job_action_ids.setdefault(job_id, [])
            if action.id not in ids:
                ids.append(action.id)
        return action

    def get(self, action_id: str) -> Action:
        try:
            return self._actions[action_id]
        except KeyError as exc:
            raise StoreNotFoundError("action", action_id) from exc

    def list_for_session(self, session_id: str) -> list[Action]:
        return [self.get(action_id) for action_id in self._session_action_ids.get(session_id, [])]

    def list_for_job(self, job_id: str) -> list[Action]:
        return [self.get(action_id) for action_id in self._job_action_ids.get(job_id, [])]

    def save_result(self, result: ActionResult) -> ActionResult:
        self._results_by_action_id[result.action_id] = result
        return result

    def get_result(self, action_id: str) -> ActionResult:
        try:
            return self._results_by_action_id[action_id]
        except KeyError as exc:
            raise StoreNotFoundError("action_result", action_id) from exc

