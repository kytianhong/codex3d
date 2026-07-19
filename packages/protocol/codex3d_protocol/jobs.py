from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .common import Metadata, new_id, utc_now_iso
from .errors import ErrorCode, ProtocolError


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING = "waiting"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    AGENT_TURN = "agent_turn"
    BLENDER_ACTION = "blender_action"
    RENDER_PREVIEW = "render_preview"
    ASSET_SEARCH = "asset_search"
    ASSET_GENERATION = "asset_generation"
    ASSET_IMPORT = "asset_import"
    VALIDATION = "validation"


@dataclass
class Job:
    id: str = field(default_factory=lambda: new_id("job"))
    type: JobType = JobType.AGENT_TURN
    status: JobStatus = JobStatus.QUEUED
    scene_id: str | None = None
    action_id: str | None = None
    input: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)
    error: ProtocolError | None = None
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    started_at: str | None = None
    finished_at: str | None = None
    metadata: Metadata = field(default_factory=dict)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def mark_running(self) -> None:
        now = utc_now_iso()
        self.status = JobStatus.RUNNING
        self.started_at = self.started_at or now
        self.updated_at = now

    def mark_succeeded(self, result: dict[str, Any] | None = None) -> None:
        now = utc_now_iso()
        self.status = JobStatus.SUCCEEDED
        self.result = result or {}
        self.finished_at = now
        self.updated_at = now

    def mark_failed(
        self,
        message: str,
        code: ErrorCode = ErrorCode.JOB_FAILED,
        retryable: bool = False,
    ) -> None:
        now = utc_now_iso()
        self.status = JobStatus.FAILED
        self.error = ProtocolError(code=code, message=message, retryable=retryable)
        self.finished_at = now
        self.updated_at = now

    def cancel(self) -> None:
        now = utc_now_iso()
        self.status = JobStatus.CANCELLED
        self.finished_at = now
        self.updated_at = now

