from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from typing import Any


OBJECT_NAME = "C3D_MCP_DemoCube"
MATERIAL_NAME = "C3D_MCP_DemoMaterial"


class StdioMcpClient:
    def __init__(self) -> None:
        self._next_id = 1
        env = dict(os.environ)
        self.process = subprocess.Popen(
            [sys.executable, "-m", "codex3d_mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            bufsize=1,
        )

    def close(self) -> None:
        if self.process.stdin:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=2.0)

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        message = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}
        assert self.process.stdin is not None and self.process.stdout is not None
        self.process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        self.process.stdin.flush()
        response = json.loads(self.process.stdout.readline())
        if response.get("id") != request_id or "error" in response:
            raise RuntimeError(f"MCP request failed: {response.get('error', 'correlation error')}")
        return response["result"]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = self.request("tools/call", {"name": name, "arguments": arguments})
        return result["structuredContent"]


def run_demo() -> dict[str, Any]:
    client = StdioMcpClient()
    try:
        initialized = client.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "codex3d-real-demo", "version": "0.1.0"}})
        tools = client.request("tools/list")["tools"]
        before = client.call_tool("blender_inspect_scene", {"mode": "full"})
        existing_names = {item["label"] for item in before["inspection"]["scene"]["objects"]}
        if OBJECT_NAME in existing_names:
            client.call_tool("blender_delete_object", {"target_name": OBJECT_NAME})
        create = client.call_tool(
            "blender_create_primitive",
            {"primitive": "cube", "name": OBJECT_NAME, "location": [0.0, 0.0, 0.5], "dimensions": [1.0, 1.0, 1.0], "semantic_type": "mcp_demo_cube"},
        )
        transform = client.call_tool(
            "blender_transform_object",
            {"target_name": OBJECT_NAME, "location": [0.0, 0.0, 1.0], "scale": [1.25, 0.8, 1.5]},
        )
        material = client.call_tool(
            "blender_assign_material",
            {"target_name": OBJECT_NAME, "material_name": MATERIAL_NAME, "base_color": [0.12, 0.42, 0.8, 1.0], "roughness": 0.35, "metallic": 0.1},
        )
        follow_up = client.call_tool(
            "blender_transform_object",
            {"target_name": OBJECT_NAME, "location": [0.35, 0.0, 1.0]},
        )
        final = client.call_tool("blender_inspect_scene", {"mode": "full"})
    finally:
        client.close()

    objects = final["inspection"]["scene"]["objects"]
    cube = next((item for item in objects if item["label"] == OBJECT_NAME), None)
    ok = bool(
        cube
        and create["ok"]
        and transform["ok"]
        and material["ok"]
        and follow_up["ok"]
        and math.isclose(cube["transform"]["location"]["x"], 0.35, abs_tol=1e-5)
        and math.isclose(cube["transform"]["location"]["y"], 0.0, abs_tol=1e-5)
        and math.isclose(cube["transform"]["location"]["z"], 1.0, abs_tol=1e-5)
        and cube["metadata"].get("material_name") == MATERIAL_NAME
    )
    return {
        "ok": ok,
        "mcp_protocol_version": initialized["protocolVersion"],
        "tool_count": len(tools),
        "object_name": OBJECT_NAME,
        "final_location": cube["transform"]["location"] if cube else None,
        "final_scale": cube["transform"]["scale"] if cube else None,
        "material_name": cube["metadata"].get("material_name") if cube else None,
        "backend": final["inspection"]["scene"]["metadata"].get("blender_backend", "bpy"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Codex3D STDIO MCP adapter against a live Blender bridge.")
    parser.add_argument("--connection-info", help="Protected JSON file containing bridge host, port, and token.")
    args = parser.parse_args(argv)
    if args.connection_info:
        try:
            with open(args.connection_info, encoding="utf-8") as handle:
                info = json.load(handle)
            os.environ["CODEX3D_BRIDGE_HOST"] = info["host"]
            os.environ["CODEX3D_BRIDGE_PORT"] = str(info["port"])
            os.environ["CODEX3D_BRIDGE_TOKEN"] = info["token"]
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
            print(f"Could not read bridge connection info: {exc}", file=sys.stderr)
            return 2
    try:
        summary = run_demo()
    except Exception as exc:
        print(f"Codex3D MCP demo failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
