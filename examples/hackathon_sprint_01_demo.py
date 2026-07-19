from __future__ import annotations

import json
import sys

from codex3d_api import Codex3DApiService, SubmitMessageRequest
from codex3d_blender_connector import BlenderActionExecutor, FakeBlenderBackend
from codex3d_protocol import (
    ActionStatus,
    ConnectorCapability,
    ConnectorRegistration,
    ConnectorStatus,
    ConnectorType,
)

PROMPT = "Create a cozy wooden desk scene with a chair, lamp, and warm lighting."
IMPORTANT_OBJECT_NAMES = [
    "C3D_Floor",
    "C3D_DeskTop",
    "C3D_ChairSeat",
    "C3D_LampBase",
    "C3D_WarmLampLight",
]


def run_demo() -> dict:
    service = Codex3DApiService()
    session = service.create_session("Hackathon Sprint 01 Demo")
    registration = service.register_connector(
        ConnectorRegistration(
            connector_type=ConnectorType.LOCAL_SIMULATED,
            name="Hackathon Fake Blender",
            capabilities=[
                ConnectorCapability.PING,
                ConnectorCapability.HEARTBEAT,
                ConnectorCapability.INSPECT_SCENE,
                ConnectorCapability.REPORT_VERSION,
                ConnectorCapability.EXECUTE_ACTION,
            ],
            status=ConnectorStatus.ONLINE,
            metadata={"blender_backend": "fake"},
        )
    )
    backend = FakeBlenderBackend()
    executor = BlenderActionExecutor(backend)
    service.bind_connector_action_handler(registration.id, executor.execute)

    response = service.plan_demo_message(session.id, SubmitMessageRequest(content=PROMPT))
    planned_actions = service.list_session_actions(session.id)
    results = service.execute_session_plan(session.id, registration.id)
    inspection = backend.inspect(connector_id=registration.id)
    object_names = [obj.label for obj in inspection.scene.objects]
    succeeded_count = sum(result.status is ActionStatus.SUCCEEDED for result in results)
    failed_count = sum(result.status is ActionStatus.FAILED for result in results)
    missing = [name for name in IMPORTANT_OBJECT_NAMES if name not in object_names]

    summary = {
        "session_id": session.id,
        "connector_id": registration.id,
        "planner": response.metadata["planner"],
        "planned_action_count": len(planned_actions),
        "succeeded_action_count": succeeded_count,
        "failed_action_count": failed_count,
        "object_count": len(inspection.scene.objects),
        "important_object_names": [name for name in IMPORTANT_OBJECT_NAMES if name in object_names],
        "missing_important_object_names": missing,
        "blender_backend": backend.backend_name,
    }
    summary["ok"] = (
        not missing
        and failed_count == 0
        and succeeded_count == len(planned_actions)
        and len(inspection.scene.objects) >= len(IMPORTANT_OBJECT_NAMES)
    )
    return summary


def main() -> int:
    summary = run_demo()
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

