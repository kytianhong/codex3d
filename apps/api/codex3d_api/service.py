from __future__ import annotations

from codex3d_protocol import (
    Action,
    ActionResult,
    ConnectorHeartbeat,
    ConnectorPing,
    ConnectorPingResult,
    ConnectorRegistration,
    ErrorCode,
    Job,
    JobType,
    ProtocolError,
    Scene,
)

from .action_dispatcher import LocalActionDispatcher
from .action_store import InMemoryActionStore
from .connector_service import ConnectorService
from .connector_store import InMemoryConnectorStore
from .mock_agent import run_mock_agent_turn
from .demo_planner import plan_demo_prompt
from .models import (
    Message,
    MessageRole,
    Session,
    SessionSummary,
    SubmitMessageRequest,
    SubmitMessageResponse,
)
from .store import InMemoryJobStore, InMemorySessionStore, StoreNotFoundError


class Codex3DApiService:
    def __init__(
        self,
        session_store: InMemorySessionStore | None = None,
        job_store: InMemoryJobStore | None = None,
        action_store: InMemoryActionStore | None = None,
        connector_store: InMemoryConnectorStore | None = None,
        connector_service: ConnectorService | None = None,
        action_dispatcher: LocalActionDispatcher | None = None,
    ) -> None:
        self.session_store = session_store or InMemorySessionStore()
        self.job_store = job_store or InMemoryJobStore()
        self.action_store = action_store or InMemoryActionStore()
        self.connector_service = connector_service or ConnectorService(connector_store)
        self.action_dispatcher = action_dispatcher or LocalActionDispatcher(self.connector_service)

    def health(self) -> dict[str, str]:
        return {"status": "ok", "service": "codex3d-api-core"}

    def create_session(self, name: str | None = None) -> Session:
        return self.session_store.create_session(name=name)

    def get_session(self, session_id: str) -> Session:
        return self._wrap_missing("session", session_id, self.session_store.get_session)

    def list_sessions(self) -> list[SessionSummary]:
        return [session.summary() for session in self.session_store.list_sessions()]

    def submit_message(
        self,
        session_id: str,
        request: SubmitMessageRequest,
    ) -> SubmitMessageResponse:
        session = self.get_session(session_id)
        message = Message(
            role=MessageRole.USER,
            content=request.content,
            metadata=dict(request.metadata),
        )
        session.add_message(message)

        agent_turn = run_mock_agent_turn(message, session.scene)
        job = self.job_store.create_job(agent_turn.job, session_id=session.id)
        session.add_job_id(job.id)
        session.metadata["last_mock_action_ids"] = [action.id for action in agent_turn.actions]
        self.session_store.save_session(session)

        return SubmitMessageResponse(
            session_id=session.id,
            message_id=message.id,
            job_id=job.id,
            action_ids=[action.id for action in agent_turn.actions],
            summary=agent_turn.summary,
            metadata={"mock": True},
        )

    def get_job(self, job_id: str) -> Job:
        return self._wrap_missing("job", job_id, self.job_store.get_job)

    def list_session_jobs(self, session_id: str) -> list[Job]:
        self.get_session(session_id)
        return self.job_store.list_jobs_by_session_id(session_id)

    def get_session_scene(self, session_id: str) -> Scene:
        return self.get_session(session_id).scene

    def register_connector(
        self,
        registration: ConnectorRegistration | None = None,
        **kwargs,
    ) -> ConnectorRegistration:
        return self.connector_service.register_connector(registration, **kwargs)

    def get_connector(self, connector_id: str) -> ConnectorRegistration:
        return self._wrap_missing("connector", connector_id, self.connector_service.get_connector)

    def list_connectors(self) -> list[ConnectorRegistration]:
        return self.connector_service.list_connectors()

    def connector_heartbeat(
        self,
        heartbeat: ConnectorHeartbeat | None = None,
        **kwargs,
    ) -> ConnectorRegistration:
        try:
            return self.connector_service.heartbeat(heartbeat, **kwargs)
        except StoreNotFoundError as exc:
            connector_id = heartbeat.connector_id if heartbeat else kwargs.get("connector_id", "")
            raise ValueError(
                ProtocolError(
                    code=ErrorCode.OBJECT_NOT_FOUND,
                    message=f"connector not found: {connector_id}",
                    source="codex3d_api.service",
                    details={"entity_type": "connector", "entity_id": connector_id},
                )
            ) from exc

    def ping_connector(
        self,
        connector_id: str,
        ping: ConnectorPing | None = None,
    ) -> ConnectorPingResult:
        return self.connector_service.ping(connector_id, ping=ping)

    def plan_demo_message(
        self,
        session_id: str,
        request: SubmitMessageRequest,
    ) -> SubmitMessageResponse:
        session = self.get_session(session_id)
        message = Message(
            role=MessageRole.USER,
            content=request.content,
            metadata=dict(request.metadata),
        )
        session.add_message(message)
        plan = plan_demo_prompt(request.content)
        job = Job(
            type=JobType.AGENT_TURN,
            scene_id=session.scene.id,
            input={"message_id": message.id, "content": request.content},
            metadata={
                "planner": plan.planner,
                "demo": True,
                "model_used": "none",
                "supported": plan.supported,
            },
        )
        job.mark_succeeded(
            {
                "summary": plan.summary,
                "action_ids": [action.id for action in plan.actions],
                "planner": plan.planner,
            }
        )
        self.job_store.create_job(job, session_id=session.id)
        session.add_job_id(job.id)
        for action in plan.actions:
            self.action_store.save(action, session_id=session.id, job_id=job.id)
        self.session_store.save_session(session)
        return SubmitMessageResponse(
            session_id=session.id,
            message_id=message.id,
            job_id=job.id,
            action_ids=[action.id for action in plan.actions],
            summary=plan.summary,
            metadata={
                "planner": plan.planner,
                "demo": True,
                "model_used": "none",
                "supported": plan.supported,
            },
        )

    def get_action(self, action_id: str) -> Action:
        return self._wrap_missing("action", action_id, self.action_store.get)

    def list_session_actions(self, session_id: str) -> list[Action]:
        self.get_session(session_id)
        return self.action_store.list_for_session(session_id)

    def list_job_actions(self, job_id: str) -> list[Action]:
        self.get_job(job_id)
        return self.action_store.list_for_job(job_id)

    def get_action_result(self, action_id: str) -> ActionResult:
        return self._wrap_missing("action_result", action_id, self.action_store.get_result)

    def bind_connector_action_handler(self, connector_id: str, handler) -> None:
        self.action_dispatcher.bind_handler(connector_id, handler)

    def execute_action(self, connector_id: str, action_id: str) -> ActionResult:
        action = self.get_action(action_id)
        result = self.action_dispatcher.dispatch(connector_id, action)
        self.action_store.save(action)
        self.action_store.save_result(result)
        return result

    def execute_session_plan(self, session_id: str, connector_id: str) -> list[ActionResult]:
        actions = self.list_session_actions(session_id)
        results = self.action_dispatcher.dispatch_many(connector_id, actions)
        for action, result in zip(actions, results):
            self.action_store.save(action)
            self.action_store.save_result(result)
        return results

    def _wrap_missing(self, entity_type: str, entity_id: str, getter):
        try:
            return getter(entity_id)
        except StoreNotFoundError as exc:
            raise ValueError(
                ProtocolError(
                    code=ErrorCode.OBJECT_NOT_FOUND,
                    message=f"{entity_type} not found: {entity_id}",
                    source="codex3d_api.service",
                    details={"entity_type": entity_type, "entity_id": entity_id},
                )
            ) from exc
