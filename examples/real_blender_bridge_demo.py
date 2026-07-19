from __future__ import annotations

import argparse
import json
import os
import sys
import time

from codex3d_api import ConnectorTransportError, SocketConnectorClient, plan_demo_prompt
from codex3d_protocol import Action, ActionType


PROMPT = "Create a cozy wooden desk scene with a chair, lamp, and warm lighting."
IMPORTANT_OBJECTS = {
    "C3D_Floor",
    "C3D_DeskTop",
    "C3D_ChairSeat",
    "C3D_LampBase",
    "C3D_WarmLampLight",
}


def run_demo(host: str, port: int, token: str) -> dict:
    started = time.perf_counter()
    with SocketConnectorClient(host=host, port=port, token=token) as client:
        hello = client.hello()
        client.ping()
        before = client.inspect_scene()
        old_names = sorted(obj.label for obj in before.scene.objects if obj.label.startswith("C3D_"))
        if old_names:
            cleanup = [
                Action(
                    type=ActionType.DELETE_OBJECT,
                    description=f"Remove previous demo object {name}.",
                    parameters={"target_name": name},
                    metadata={"demo_cleanup": True},
                )
                for name in old_names
            ]
            client.execute_action_batch(cleanup)

        plan = plan_demo_prompt(PROMPT)
        batch = client.execute_action_batch(plan.actions)
        after = client.inspect_scene()

    names = {obj.label for obj in after.scene.objects if obj.label.startswith("C3D_")}
    succeeded = int(batch["succeeded_count"])
    failed = int(batch["failed_count"])
    summary = {
        "bridge_connected": True,
        "backend": hello.get("backend"),
        "connector_version": hello.get("connector_version"),
        "blender_version": hello.get("blender_version"),
        "planned_action_count": len(plan.actions),
        "succeeded_action_count": succeeded,
        "failed_action_count": failed,
        "codex3d_object_count": len(names),
        "important_objects_present": IMPORTANT_OBJECTS.issubset(names),
        "round_trip_ms": round((time.perf_counter() - started) * 1000.0, 2),
    }
    summary["ok"] = (
        plan.supported
        and len(plan.actions) == 31
        and succeeded == 31
        and failed == 0
        and len(names) == 16
        and summary["important_objects_present"]
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Drive a running Blender Codex3D bridge.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9876)
    parser.add_argument("--token", default=os.environ.get("CODEX3D_BLENDER_TOKEN", ""))
    parser.add_argument("--connection-info", help="Read host, port, and token from a protected JSON file.")
    args = parser.parse_args(argv)
    if args.connection_info:
        try:
            with open(args.connection_info, encoding="utf-8") as handle:
                connection_info = json.load(handle)
            args.host = connection_info["host"]
            args.port = int(connection_info["port"])
            args.token = connection_info["token"]
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            print(f"Could not read connection info: {exc}", file=sys.stderr)
            return 2
    if not args.token:
        print("Missing token. In Blender, open the Codex3D panel, Connect, then copy connection info.", file=sys.stderr)
        return 2
    try:
        summary = run_demo(args.host, args.port, args.token)
    except (ConnectorTransportError, ValueError) as exc:
        print(
            f"Could not complete the Blender bridge demo: {exc}. "
            "Open Blender, enable the Codex3D extension, and click Connect.",
            file=sys.stderr,
        )
        return 1
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
