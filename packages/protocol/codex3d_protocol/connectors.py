from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .common import Metadata, new_id, utc_now_iso
from .actions import Action, ActionResult
from .errors import ProtocolError
from .scene import Scene


class ConnectorType(str, Enum):
    BLENDER_ADDON = "blender_addon"
    BLENDER_WORKER = "blender_worker"
    LOCAL_SIMULATED = "local_simulated"


class ConnectorStatus(str, Enum):
    REGISTERED = "registered"
    ONLINE = "online"
    STALE = "stale"
    OFFLINE = "offline"
    ERROR = "error"


class ConnectorCapability(str, Enum):
    PING = "ping"
    HEARTBEAT = "heartbeat"
    INSPECT_SCENE = "inspect_scene"
    REPORT_VERSION = "report_version"
    EXECUTE_ACTION = "execute_action"
    RENDER_PREVIEW = "render_preview"
    SNAPSHOT_SCENE = "snapshot_scene"
    RESTORE_SNAPSHOT = "restore_snapshot"


@dataclass
class ConnectorRegistration:
    id: str = field(default_factory=lambda: new_id("connector"))
    connector_type: ConnectorType = ConnectorType.BLENDER_ADDON
    name: str = "Codex3D Blender Connector"
    version: str = "0.1.0"
    capabilities: list[ConnectorCapability] = field(default_factory=list)
    status: ConnectorStatus = ConnectorStatus.REGISTERED
    created_at: str = field(default_factory=utc_now_iso)
    last_seen_at: str = field(default_factory=utc_now_iso)
    metadata: Metadata = field(default_factory=dict)


@dataclass
class ConnectorHeartbeat:
    connector_id: str = ""
    status: ConnectorStatus = ConnectorStatus.ONLINE
    sent_at: str = field(default_factory=utc_now_iso)
    metadata: Metadata = field(default_factory=dict)


@dataclass
class ConnectorPing:
    connector_id: str = ""
    sent_at: str = field(default_factory=utc_now_iso)
    metadata: Metadata = field(default_factory=dict)


@dataclass
class ConnectorPingResult:
    connector_id: str = ""
    ok: bool = False
    status: ConnectorStatus = ConnectorStatus.ERROR
    received_at: str = field(default_factory=utc_now_iso)
    message: str = ""
    error: ProtocolError | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass
class ConnectorSceneInspection:
    connector_id: str = ""
    scene: Scene = field(default_factory=Scene)
    inspected_at: str = field(default_factory=utc_now_iso)
    metadata: Metadata = field(default_factory=dict)


@dataclass
class ConnectorActionRequest:
    connector_id: str = ""
    action: Action = field(default_factory=Action)
    requested_at: str = field(default_factory=utc_now_iso)
    metadata: Metadata = field(default_factory=dict)


@dataclass
class ConnectorActionResponse:
    connector_id: str = ""
    result: ActionResult = field(default_factory=ActionResult)
    completed_at: str = field(default_factory=utc_now_iso)
    metadata: Metadata = field(default_factory=dict)
