from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .common import Metadata, new_id, utc_now_iso


class ErrorSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


class ErrorCode(str, Enum):
    INVALID_SCHEMA = "invalid_schema"
    OBJECT_NOT_FOUND = "object_not_found"
    ACTION_FAILED = "action_failed"
    JOB_FAILED = "job_failed"
    PROVIDER_FAILED = "provider_failed"
    VALIDATION_FAILED = "validation_failed"
    RENDER_FAILED = "render_failed"
    UNSUPPORTED_OPERATION = "unsupported_operation"
    AUTHENTICATION_FAILED = "authentication_failed"
    CONNECTOR_OFFLINE = "connector_offline"
    REQUEST_TIMEOUT = "request_timeout"
    BRIDGE_SHUTDOWN = "bridge_shutdown"
    FRAME_TOO_LARGE = "frame_too_large"


@dataclass
class ProtocolError:
    id: str = field(default_factory=lambda: new_id("error"))
    code: ErrorCode = ErrorCode.ACTION_FAILED
    message: str = ""
    severity: ErrorSeverity = ErrorSeverity.ERROR
    source: str | None = None
    retryable: bool = False
    details: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)
    metadata: Metadata = field(default_factory=dict)
