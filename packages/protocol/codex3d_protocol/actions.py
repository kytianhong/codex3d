from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .common import Metadata, new_id, utc_now_iso
from .errors import ProtocolError


class ActionStatus(str, Enum):
    PLANNED = "planned"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ActionType(str, Enum):
    CREATE_OBJECT = "create_object"
    MODIFY_OBJECT = "modify_object"
    DELETE_OBJECT = "delete_object"
    TRANSFORM_OBJECT = "transform_object"
    ASSIGN_MATERIAL = "assign_material"
    PLACE_OBJECT = "place_object"
    IMPORT_ASSET = "import_asset"
    RENDER_PREVIEW = "render_preview"
    INSPECT_SCENE = "inspect_scene"
    SNAPSHOT_SCENE = "snapshot_scene"
    RESTORE_SNAPSHOT = "restore_snapshot"
    LIST_SNAPSHOTS = "list_snapshots"
    DELETE_SNAPSHOT = "delete_snapshot"
    RECONCILE_OBJECT_IDS = "reconcile_object_ids"
    CONFIGURE_SCENE = "configure_scene"
    CONFIGURE_WORLD = "configure_world"
    SET_PARENT = "set_parent"
    KEYFRAME_OBJECT = "keyframe_object"
    SAVE_CHECKPOINT = "save_checkpoint"


@dataclass
class ToolCall:
    id: str = field(default_factory=lambda: new_id("tool_call"))
    tool_name: str = ""
    action_id: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now_iso)
    metadata: Metadata = field(default_factory=dict)


@dataclass
class Action:
    id: str = field(default_factory=lambda: new_id("action"))
    type: ActionType = ActionType.INSPECT_SCENE
    description: str = ""
    object_id: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    tool_calls: list[ToolCall] = field(default_factory=list)
    status: ActionStatus = ActionStatus.PLANNED
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    metadata: Metadata = field(default_factory=dict)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def add_tool_call(self, tool_call: ToolCall) -> ToolCall:
        tool_call.action_id = self.id
        self.tool_calls.append(tool_call)
        self.touch()
        return tool_call


@dataclass
class ActionResult:
    id: str = field(default_factory=lambda: new_id("action_result"))
    action_id: str = ""
    status: ActionStatus = ActionStatus.SUCCEEDED
    created_object_ids: list[str] = field(default_factory=list)
    modified_object_ids: list[str] = field(default_factory=list)
    deleted_object_ids: list[str] = field(default_factory=list)
    output: dict[str, Any] = field(default_factory=dict)
    error: ProtocolError | None = None
    created_at: str = field(default_factory=utc_now_iso)
    metadata: Metadata = field(default_factory=dict)
