from __future__ import annotations

from dataclasses import dataclass, field

from codex3d_protocol import (
    Action,
    ActionStatus,
    ActionType,
    Dimensions,
    Job,
    JobType,
    Scene,
    SceneObject,
    SceneObjectSourceType,
    ToolCall,
)

from .models import Message


@dataclass
class MockAgentTurn:
    job: Job
    actions: list[Action] = field(default_factory=list)
    summary: str = ""


def run_mock_agent_turn(message: Message, scene: Scene) -> MockAgentTurn:
    content = message.content.lower()
    if "desk" in content or "书桌" in message.content:
        proposed_object = SceneObject(
            label="Mock proposed desk",
            semantic_type="desk",
            source_type=SceneObjectSourceType.USER_DEFINED,
            dimensions=Dimensions(width=1.2, depth=0.6, height=0.75),
            metadata={
                "mock": True,
                "proposed": True,
                "source_message_id": message.id,
                "note": "Created by mock agent only; not executed in Blender.",
            },
        )
        scene.add_object(proposed_object)
        action = Action(
            type=ActionType.CREATE_OBJECT,
            description="Mock plan: create a beginner-friendly desk object.",
            object_id=proposed_object.id,
            parameters={
                "semantic_type": "desk",
                "label": proposed_object.label,
                "mock": True,
                "proposed_object_id": proposed_object.id,
            },
            status=ActionStatus.SUCCEEDED,
            metadata={"mock": True},
        )
        action.add_tool_call(
            ToolCall(
                tool_name="mock_create_object",
                arguments={
                    "semantic_type": "desk",
                    "label": proposed_object.label,
                    "not_executed_in_blender": True,
                },
                metadata={"mock": True},
            )
        )
        summary = "Mock agent proposed a desk object and added it to local scene state."
    else:
        action = Action(
            type=ActionType.INSPECT_SCENE,
            description="Mock plan: inspect current local scene state.",
            parameters={"object_count": len(scene.objects), "mock": True},
            status=ActionStatus.SUCCEEDED,
            metadata={"mock": True},
        )
        action.add_tool_call(
            ToolCall(
                tool_name="mock_inspect_scene",
                arguments={"object_count": len(scene.objects)},
                metadata={"mock": True},
            )
        )
        summary = "Mock agent inspected the local scene state."

    job = Job(
        type=JobType.AGENT_TURN,
        scene_id=scene.id,
        action_id=action.id,
        input={"message_id": message.id, "content": message.content},
        metadata={"mock": True},
    )
    job.mark_succeeded(
        {
            "summary": summary,
            "action_ids": [action.id],
            "actions": [
                {
                    "id": action.id,
                    "type": action.type.value,
                    "description": action.description,
                }
            ],
        }
    )
    return MockAgentTurn(job=job, actions=[action], summary=summary)

