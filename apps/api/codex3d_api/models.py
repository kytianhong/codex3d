from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from codex3d_protocol import Metadata, Scene, new_id, utc_now_iso


class SessionStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    ERROR = "error"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Message:
    id: str = field(default_factory=lambda: new_id("message"))
    role: MessageRole = MessageRole.USER
    content: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    metadata: Metadata = field(default_factory=dict)


@dataclass
class SessionSummary:
    id: str = ""
    name: str = ""
    status: SessionStatus = SessionStatus.ACTIVE
    message_count: int = 0
    job_count: int = 0
    object_count: int = 0
    created_at: str = ""
    updated_at: str = ""
    metadata: Metadata = field(default_factory=dict)


@dataclass
class Session:
    id: str = field(default_factory=lambda: new_id("session"))
    name: str = "Untitled Session"
    status: SessionStatus = SessionStatus.ACTIVE
    scene: Scene = field(default_factory=Scene)
    messages: list[Message] = field(default_factory=list)
    job_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    metadata: Metadata = field(default_factory=dict)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def add_message(self, message: Message) -> Message:
        self.messages.append(message)
        self.touch()
        return message

    def add_job_id(self, job_id: str) -> str:
        self.job_ids.append(job_id)
        self.touch()
        return job_id

    def summary(self) -> SessionSummary:
        return SessionSummary(
            id=self.id,
            name=self.name,
            status=self.status,
            message_count=len(self.messages),
            job_count=len(self.job_ids),
            object_count=len(self.scene.objects),
            created_at=self.created_at,
            updated_at=self.updated_at,
            metadata=dict(self.metadata),
        )


@dataclass
class SubmitMessageRequest:
    content: str = ""
    metadata: Metadata = field(default_factory=dict)


@dataclass
class SubmitMessageResponse:
    session_id: str = ""
    message_id: str = ""
    job_id: str = ""
    action_ids: list[str] = field(default_factory=list)
    summary: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    metadata: Metadata = field(default_factory=dict)

