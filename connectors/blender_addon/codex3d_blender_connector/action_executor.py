from __future__ import annotations

from typing import Any

from .protocol_compat import (
    Action,
    ActionResult,
    ActionStatus,
    ActionType,
    ErrorCode,
    ProtocolError,
)

from .action_validation import ActionValidationError, validate_action_parameters
from .backends import BlenderBackend


class BlenderActionExecutor:
    def __init__(self, backend: BlenderBackend) -> None:
        self.backend = backend

    def execute(self, action: Action) -> ActionResult:
        action.status = ActionStatus.RUNNING
        action.touch()
        try:
            validate_action_parameters(action, self.backend.object_exists)
            return self._execute_validated(action)
        except ActionValidationError as exc:
            return self._failed(action, exc.protocol_error)
        except (KeyError, ValueError) as exc:
            return self._failed(
                action,
                ProtocolError(
                    code=ErrorCode.ACTION_FAILED,
                    message=str(exc),
                    source="codex3d_blender_connector.action_executor",
                ),
            )
        except Exception as exc:  # pragma: no cover - defensive boundary for Blender runtime
            return self._failed(
                action,
                ProtocolError(
                    code=ErrorCode.ACTION_FAILED,
                    message=f"Unexpected executor failure: {exc}",
                    source="codex3d_blender_connector.action_executor",
                    retryable=False,
                ),
            )

    def _execute_validated(self, action: Action) -> ActionResult:
        if action.type is ActionType.CREATE_OBJECT:
            name = self.backend.create_object(action.parameters)
            object_uuid = self.backend.object_uuid(name)
            action.status = ActionStatus.SUCCEEDED
            action.touch()
            return ActionResult(
                action_id=action.id,
                status=ActionStatus.SUCCEEDED,
                created_object_ids=[name],
                output={"object_name": name, "object_uuid": object_uuid, "backend": self.backend.backend_name},
                metadata={"backend": self.backend.backend_name},
            )

        if action.type is ActionType.TRANSFORM_OBJECT:
            name = self.backend.transform_object(action.parameters)
            return self._modified(action, name)

        if action.type is ActionType.MODIFY_OBJECT:
            name = self.backend.modify_object(action.parameters)
            return self._modified(action, name)

        if action.type is ActionType.DELETE_OBJECT:
            identifier = action.parameters.get("target_uuid") or action.parameters["target_name"]
            object_uuid = self.backend.object_uuid(identifier)
            name = self.backend.delete_object(action.parameters)
            action.status = ActionStatus.SUCCEEDED
            action.touch()
            return ActionResult(
                action_id=action.id,
                status=ActionStatus.SUCCEEDED,
                deleted_object_ids=[name],
                output={"object_name": name, "object_uuid": object_uuid, "backend": self.backend.backend_name},
                metadata={"backend": self.backend.backend_name},
            )

        if action.type is ActionType.ASSIGN_MATERIAL:
            name = self.backend.assign_material(action.parameters)
            return self._modified(action, name)

        if action.type is ActionType.SET_PARENT:
            name = self.backend.set_parent(action.parameters)
            return self._modified(action, name)

        if action.type is ActionType.CONFIGURE_WORLD:
            return self._operation(action, self.backend.configure_world(action.parameters))

        if action.type is ActionType.CONFIGURE_SCENE:
            return self._operation(action, self.backend.configure_scene(action.parameters))

        if action.type is ActionType.KEYFRAME_OBJECT:
            return self._operation(action, self.backend.keyframe_object(action.parameters))

        if action.type is ActionType.RENDER_PREVIEW:
            return self._operation(action, self.backend.render(action.parameters))

        if action.type is ActionType.SAVE_CHECKPOINT:
            return self._operation(action, self.backend.save_checkpoint(action.parameters))

        if action.type is ActionType.SNAPSHOT_SCENE:
            return self._operation(action, self.backend.create_snapshot(action.parameters))

        if action.type is ActionType.LIST_SNAPSHOTS:
            return self._operation(action, self.backend.list_snapshots(action.parameters))

        if action.type is ActionType.RESTORE_SNAPSHOT:
            return self._operation(action, self.backend.restore_snapshot(action.parameters))

        if action.type is ActionType.DELETE_SNAPSHOT:
            return self._operation(action, self.backend.delete_snapshot(action.parameters))

        if action.type is ActionType.RECONCILE_OBJECT_IDS:
            return self._operation(action, self.backend.reconcile_object_ids(action.parameters))

        return self._failed(
            action,
            ProtocolError(
                code=ErrorCode.UNSUPPORTED_OPERATION,
                message=f"Unsupported action type: {action.type.value}",
                source="codex3d_blender_connector.action_executor",
            ),
        )

    def _modified(self, action: Action, name: str) -> ActionResult:
        object_uuid = self.backend.object_uuid(name)
        action.status = ActionStatus.SUCCEEDED
        action.touch()
        return ActionResult(
            action_id=action.id,
            status=ActionStatus.SUCCEEDED,
            modified_object_ids=[name],
            output={"object_name": name, "object_uuid": object_uuid, "backend": self.backend.backend_name},
            metadata={"backend": self.backend.backend_name},
        )

    def _operation(self, action: Action, output: dict[str, Any]) -> ActionResult:
        action.status = ActionStatus.SUCCEEDED
        action.touch()
        return ActionResult(
            action_id=action.id,
            status=ActionStatus.SUCCEEDED,
            output={**output, "backend": self.backend.backend_name},
            metadata={"backend": self.backend.backend_name},
        )

    def _failed(self, action: Action, error: ProtocolError) -> ActionResult:
        action.status = ActionStatus.FAILED
        action.touch()
        return ActionResult(
            action_id=action.id,
            status=ActionStatus.FAILED,
            error=error,
            output={"backend": self.backend.backend_name},
            metadata={"backend": self.backend.backend_name},
        )
