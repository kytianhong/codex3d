from __future__ import annotations

from codex3d_protocol import Job, JobType

from .models import Session


class StoreNotFoundError(LookupError):
    def __init__(self, entity_type: str, entity_id: str) -> None:
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type} not found: {entity_id}")


class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create_session(self, name: str | None = None) -> Session:
        session = Session(name=name or "Untitled Session")
        session.scene.name = f"{session.name} Scene"
        session.scene.metadata["session_id"] = session.id
        self._sessions[session.id] = session
        return session

    def get_session(self, session_id: str) -> Session:
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise StoreNotFoundError("session", session_id) from exc

    def list_sessions(self) -> list[Session]:
        return sorted(self._sessions.values(), key=lambda session: session.created_at)

    def save_session(self, session: Session) -> Session:
        session.touch()
        self._sessions[session.id] = session
        return session


class InMemoryJobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._session_job_ids: dict[str, list[str]] = {}

    def create_job(
        self,
        job: Job | None = None,
        *,
        session_id: str | None = None,
        job_type: JobType = JobType.AGENT_TURN,
    ) -> Job:
        created = job or Job(type=job_type)
        self._jobs[created.id] = created
        if session_id is not None:
            self._session_job_ids.setdefault(session_id, []).append(created.id)
        return created

    def get_job(self, job_id: str) -> Job:
        try:
            return self._jobs[job_id]
        except KeyError as exc:
            raise StoreNotFoundError("job", job_id) from exc

    def list_jobs(self) -> list[Job]:
        return sorted(self._jobs.values(), key=lambda job: job.created_at)

    def list_jobs_by_session_id(self, session_id: str) -> list[Job]:
        return [self.get_job(job_id) for job_id in self._session_job_ids.get(session_id, [])]

    def save_job(self, job: Job) -> Job:
        job.touch()
        self._jobs[job.id] = job
        return job

