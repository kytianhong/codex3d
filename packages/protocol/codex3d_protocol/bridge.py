from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .common import Metadata, new_id, utc_now_iso
from .errors import ProtocolError


BRIDGE_PROTOCOL_VERSION = "1.0"


class BridgeProtocolVersion(str, Enum):
    V1_0 = BRIDGE_PROTOCOL_VERSION


class BridgeMessageType(str, Enum):
    HELLO = "hello"
    PING = "ping"
    INSPECT_SCENE = "inspect_scene"
    EXECUTE_ACTION = "execute_action"
    EXECUTE_ACTION_BATCH = "execute_action_batch"


class BridgeStatus(str, Enum):
    DISCONNECTED = "disconnected"
    STARTING = "starting"
    CONNECTED = "connected"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class BridgeRequest:
    protocol_version: str = BRIDGE_PROTOCOL_VERSION
    request_id: str = field(default_factory=lambda: new_id("request"))
    type: BridgeMessageType = BridgeMessageType.PING
    auth_token: str = ""
    sent_at: str = field(default_factory=utc_now_iso)
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: Metadata = field(default_factory=dict)


@dataclass
class BridgeResponse:
    protocol_version: str = BRIDGE_PROTOCOL_VERSION
    request_id: str = ""
    type: str = "response"
    ok: bool = False
    received_at: str = field(default_factory=utc_now_iso)
    completed_at: str = field(default_factory=utc_now_iso)
    payload: dict[str, Any] = field(default_factory=dict)
    error: ProtocolError | None = None
    metadata: Metadata = field(default_factory=dict)
