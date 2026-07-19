from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT / "packages/protocol"),
    str(ROOT / "apps/api"),
    str(ROOT / "apps/mcp"),
    str(ROOT / "connectors/blender_addon"),
]
DEFAULT_BLENDER = Path("/Applications/Blender.app/Contents/MacOS/Blender")
PREFIX = "C3D_GATE0_"
CORE_NAME = f"{PREFIX}Core"
RAY_NAMES = [f"{PREFIX}Ray_{index:02d}" for index in range(1, 7)]
LIGHT_NAME = f"{PREFIX}WarmLight"
CORE_MATERIAL = f"{PREFIX}CoreGold"
RAY_MATERIAL = f"{PREFIX}RayAmber"
ACCENT_MATERIAL = f"{PREFIX}AccentGold"
CODEX_MATERIAL = f"{PREFIX}BrightWarmGold"
EXPECTED_TOOLS = {
    "blender_ping",
    "blender_inspect_scene",
    "blender_create_primitive",
    "blender_transform_object",
    "blender_rename_object",
    "blender_delete_object",
    "blender_assign_material",
    "blender_set_point_light",
    "blender_create_curve",
    "blender_create_camera",
    "blender_set_light",
    "blender_set_parent",
    "blender_configure_world",
    "blender_configure_scene",
    "blender_keyframe_object",
    "blender_render",
    "blender_save_checkpoint",
    "blender_create_snapshot",
    "blender_list_snapshots",
    "blender_restore_snapshot",
    "blender_delete_snapshot",
    "blender_reconcile_object_ids",
    "blender_execute_batch",
}
READY_STATUSES = {"READY", "PARTIAL", "MISSING", "NOT_RUN"}


class GateFailure(RuntimeError):
    pass


class StdioMcpClient:
    def __init__(self, env: dict[str, str]) -> None:
        self._next_id = 1
        self.responses: list[dict[str, Any]] = []
        self.process = subprocess.Popen(
            [sys.executable, "-m", "codex3d_mcp"],
            cwd=ROOT,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        request = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}
        if self.process.stdin is None or self.process.stdout is None:
            raise GateFailure("MCP STDIO streams are unavailable.")
        self.process.stdin.write(json.dumps(request, separators=(",", ":")) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            stderr = self.process.stderr.read()[-1000:] if self.process.stderr else ""
            raise GateFailure(f"MCP server exited without a response: {stderr}")
        response = json.loads(line)
        self.responses.append(response)
        if response.get("jsonrpc") != "2.0" or response.get("id") != request_id:
            raise GateFailure("MCP JSON-RPC response correlation failed.")
        if "error" in response:
            raise GateFailure(f"MCP request failed: {response['error']}")
        return response["result"]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = self.request("tools/call", {"name": name, "arguments": arguments})
        payload = result.get("structuredContent")
        if not isinstance(payload, dict):
            raise GateFailure(f"MCP tool {name} returned no structured content.")
        if not payload.get("ok"):
            raise GateFailure(f"MCP tool {name} failed: {payload.get('error', {})}")
        return payload

    def close(self) -> None:
        if self.process.stdin and not self.process.stdin.closed:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)


def _pythonpath() -> str:
    return os.pathsep.join(
        str(ROOT / path)
        for path in ("packages/protocol", "apps/api", "apps/mcp", "connectors/blender_addon")
    )


def _file_digest(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def _available_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _port_is_released(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.25)
        return probe.connect_ex(("127.0.0.1", port)) != 0


def _wait_for_bridge(port: int, token: str, timeout: float = 30.0) -> dict[str, Any]:
    from codex3d_api import SocketConnectorClient

    deadline = time.monotonic() + timeout
    last_error = ""
    while time.monotonic() < deadline:
        try:
            with SocketConnectorClient(host="127.0.0.1", port=port, token=token) as client:
                return client.hello()
        except Exception as exc:
            last_error = str(exc)
            time.sleep(0.1)
    raise GateFailure(f"Isolated Blender bridge did not start: {last_error}")


def _blender_host() -> int:
    import bpy  # type: ignore

    sys.path[:0] = [str(ROOT / "packages/protocol"), str(ROOT / "connectors/blender_addon")]
    from codex3d_blender_connector import get_runtime_controller

    port = int(os.environ["CODEX3D_GATE0_PORT"])
    token = os.environ["CODEX3D_GATE0_TOKEN"]
    stop_path = Path(os.environ["CODEX3D_GATE0_STOP_PATH"])
    blend_path = Path(os.environ["CODEX3D_GATE0_BLEND_PATH"])
    ready_path = Path(os.environ["CODEX3D_GATE0_READY_PATH"])
    controller = get_runtime_controller()
    controller.connect(bpy, port=port, token=token)
    ready_path.write_text(json.dumps({"host": "127.0.0.1", "port": port}), encoding="utf-8")
    deadline = time.monotonic() + 300
    try:
        while not stop_path.exists() and time.monotonic() < deadline:
            if controller.runtime is not None:
                controller.runtime.pump_once()
            time.sleep(0.01)
        blend_path.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), check_existing=False)
    finally:
        controller.disconnect()
    return 0


def _run_baseline() -> dict[str, Any]:
    env = dict(os.environ)
    env["CODEX3D_RUN_REAL_BLENDER_TESTS"] = "0"
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    combined = completed.stdout + completed.stderr
    matches = re.findall(r"(\d+) passed", combined)
    passed = int(matches[-1]) if matches else 0
    if completed.returncode != 0:
        raise GateFailure(f"Baseline tests failed:\n{combined[-3000:]}")
    return {"status": "PASSED", "passed": passed}


def _source_safety_audit() -> dict[str, Any]:
    forbidden_imports: list[str] = []
    for relative in ("packages/protocol", "apps/api", "apps/mcp"):
        for path in (ROOT / relative).rglob("*.py"):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if re.match(r"^\s*(?:import\s+bpy\b|from\s+bpy\b)", line):
                    forbidden_imports.append(f"{path.relative_to(ROOT)}:{number}")
    if forbidden_imports:
        raise GateFailure(f"Non-connector bpy imports found: {forbidden_imports}")
    return {"bpy_imports_outside_connector": [], "arbitrary_tools": []}


def _scene_actions() -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = [
        {
            "type": "create_object",
            "description": "Create the original radial prototype core.",
            "parameters": {
                "primitive": "sphere",
                "name": CORE_NAME,
                "location": [0.0, 0.0, 0.8],
                "dimensions": [1.0, 1.0, 1.0],
                "semantic_type": "radial_core",
            },
        }
    ]
    radius = 0.95
    for index, name in enumerate(RAY_NAMES):
        angle = math.radians(index * 60)
        actions.append(
            {
                "type": "create_object",
                "description": "Create one original radial prototype part.",
                "parameters": {
                    "primitive": "cube",
                    "name": name,
                    "location": [round(radius * math.cos(angle), 6), round(radius * math.sin(angle), 6), 0.8],
                    "rotation": [0.0, 0.0, angle],
                    "dimensions": [0.65, 0.22, 0.18],
                    "semantic_type": "radial_part",
                },
            }
        )
    actions.append(
        {
            "type": "create_object",
            "description": "Create the warm test point light.",
            "parameters": {
                "primitive": "point_light",
                "name": LIGHT_NAME,
                "location": [2.0, -2.0, 3.0],
                "semantic_type": "warm_point_light",
                "light": {"color": [1.0, 0.62, 0.28], "energy": 700.0},
            },
        }
    )
    actions.append(_material_action(CORE_NAME, CORE_MATERIAL, [0.72, 0.28, 0.05, 1.0], 0.3, 0.25))
    for name in RAY_NAMES:
        actions.append(_material_action(name, RAY_MATERIAL, [0.38, 0.07, 0.025, 1.0], 0.42, 0.08))
    return actions


def _material_action(
    target: str,
    material_name: str,
    color: list[float],
    roughness: float,
    metallic: float,
) -> dict[str, Any]:
    return {
        "type": "assign_material",
        "description": "Assign a deterministic Gate 0 material.",
        "parameters": {
            "target_name": target,
            "material": {
                "name": material_name,
                "base_color": color,
                "roughness": roughness,
                "metallic": metallic,
            },
        },
    }


def _objects(inspection_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    scene = inspection_payload["inspection"]["scene"]
    return {item["label"]: item for item in scene["objects"]}


def _assert_vector(actual: dict[str, Any], expected: list[float], label: str) -> None:
    values = [actual[axis] for axis in ("x", "y", "z")]
    if not all(math.isclose(left, right, abs_tol=1e-4) for left, right in zip(values, expected)):
        raise GateFailure(f"{label} was {values}, expected {expected}.")


def _run_mcp_scene(env: dict[str, str], token: str) -> tuple[dict[str, Any], dict[str, Any]]:
    client = StdioMcpClient(env)
    try:
        initialized = client.request(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "codex3d-demo-gate-0", "version": "0.1.0"},
            },
        )
        client.request("ping")
        tools = client.request("tools/list")["tools"]
        tool_names = {tool["name"] for tool in tools}
        if tool_names != EXPECTED_TOOLS:
            raise GateFailure(f"Unexpected MCP tools: {sorted(tool_names)}")
        forbidden = [
            name
            for name in tool_names
            if any(word in name.lower() for word in ("python", "shell", "command", "arbitrary"))
        ]
        if forbidden:
            raise GateFailure(f"Forbidden MCP tools exposed: {forbidden}")
        client.call_tool("blender_ping", {})
        before = client.call_tool("blender_inspect_scene", {"mode": "full"})
        for name in sorted(item for item in _objects(before) if item.startswith(PREFIX)):
            client.call_tool("blender_delete_object", {"target_name": name})

        batch = client.call_tool("blender_execute_batch", {"actions": _scene_actions()})
        planned_count = len(_scene_actions())
        if (
            batch["executed_count"] != planned_count
            or batch["succeeded_count"] != planned_count
            or batch["failed_count"] != 0
            or batch["unexecuted_count"] != 0
        ):
            raise GateFailure("Gate 0 creation batch counts were incorrect.")

        transform = client.call_tool(
            "blender_transform_object",
            {"target_name": CORE_NAME, "location": [0.0, 0.0, 1.05], "scale": [1.15, 1.15, 1.15]},
        )
        material = client.call_tool(
            "blender_assign_material",
            {
                "target_name": RAY_NAMES[0],
                "material_name": ACCENT_MATERIAL,
                "base_color": [0.92, 0.42, 0.08, 1.0],
                "roughness": 0.24,
                "metallic": 0.3,
            },
        )
        light = client.call_tool(
            "blender_set_point_light",
            {"target_name": LIGHT_NAME, "color": [1.0, 0.5, 0.18], "energy": 900.0},
        )
        final = client.call_tool("blender_inspect_scene", {"mode": "full"})
    finally:
        client.close()

    if token in json.dumps(client.responses, ensure_ascii=False):
        raise GateFailure("Authentication token leaked into an MCP response.")
    objects = _objects(final)
    gate_objects = {name: value for name, value in objects.items() if name.startswith(PREFIX)}
    expected_names = {CORE_NAME, *RAY_NAMES, LIGHT_NAME}
    if set(gate_objects) != expected_names:
        raise GateFailure(f"Gate object names differ: {sorted(gate_objects)}")
    _assert_vector(objects[CORE_NAME]["transform"]["location"], [0.0, 0.0, 1.05], "Core location")
    _assert_vector(objects[CORE_NAME]["transform"]["scale"], [1.15, 1.15, 1.15], "Core scale")
    if objects[CORE_NAME]["metadata"].get("material_name") != CORE_MATERIAL:
        raise GateFailure("Core material assignment was not preserved.")
    if objects[RAY_NAMES[0]]["metadata"].get("material_name") != ACCENT_MATERIAL:
        raise GateFailure("Follow-up radial material assignment failed.")
    if any(objects[name]["metadata"].get("material_name") != RAY_MATERIAL for name in RAY_NAMES[1:]):
        raise GateFailure("One or more radial parts lost their material assignment.")
    light_data = objects[LIGHT_NAME]["metadata"].get("light") or {}
    if not math.isclose(float(light_data.get("energy", -1)), 900.0, abs_tol=1e-4):
        raise GateFailure("Point-light energy did not match the follow-up action.")
    if not all(
        math.isclose(float(left), right, abs_tol=1e-4)
        for left, right in zip(light_data.get("color", []), [1.0, 0.5, 0.18])
    ):
        raise GateFailure("Point-light color did not match the follow-up action.")
    return (
        {
            "status": "PASSED",
            "protocol_version": initialized["protocolVersion"],
            "tool_count": len(tools),
            "jsonrpc_response_count": len(client.responses),
            "mcp_process_returncode": client.process.returncode,
            "mcp_process_reaped": client.process.poll() is not None,
            "planned_action_count": planned_count,
            "succeeded_action_count": planned_count + 3,
            "failed_action_count": 0,
            "gate_object_count": len(gate_objects),
            "gate_object_names": sorted(gate_objects),
            "follow_up_results": [transform["ok"], material["ok"], light["ok"]],
        },
        final,
    )


def _extract_codex_tool_sequence(output: str) -> list[str]:
    sequence: list[str] = []
    seen_ids: set[str] = set()
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item") if isinstance(event, dict) else None
        if not isinstance(item, dict) or item.get("type") != "mcp_tool_call":
            continue
        name = item.get("tool") or item.get("name")
        item_id = str(item.get("id", f"{len(sequence)}:{name}"))
        if isinstance(name, str) and item_id not in seen_ids:
            seen_ids.add(item_id)
            sequence.append(name)
    return sequence


def _contains_subsequence(values: list[str], expected: list[str]) -> bool:
    position = 0
    for value in values:
        if position < len(expected) and value == expected[position]:
            position += 1
    return position == len(expected)


def _run_codex_acceptance(env: dict[str, str], port: int, token: str) -> dict[str, Any]:
    codex = shutil.which("codex")
    if codex is None:
        return {"status": "NOT_RUN", "reason": "Codex CLI unavailable"}
    prompt = (
        "只使用 codex3d MCP Blender 工具，不要运行 shell、不要编辑文件，也不要使用 blender_execute_batch。"
        "必须严格按顺序各调用一次这四个工具：blender_inspect_scene、blender_transform_object、"
        "blender_assign_material、blender_inspect_scene。先检查当前 Blender 场景。"
        f"然后把 {CORE_NAME} 稍微向上移动并放大：位置设为 [0.0, 0.0, 1.25] 米，缩放设为 [1.3, 1.3, 1.3]。"
        f"接着把它的材质调整为更明亮的暖金色，材质名 {CODEX_MATERIAL}，base color [0.95, 0.48, 0.08, 1.0]，"
        "roughness 0.22，metallic 0.35。最后再次检查场景并报告最终位置、缩放和材质。"
    )
    command = [
        codex,
        "exec",
        "--json",
        "--ephemeral",
        "--ignore-user-config",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "-c",
        'approval_policy="never"',
        "-C",
        str(ROOT),
        "-c",
        f'mcp_servers.codex3d.command="{sys.executable}"',
        "-c",
        'mcp_servers.codex3d.args=["-m","codex3d_mcp"]',
        "-c",
        f'mcp_servers.codex3d.cwd="{ROOT}"',
        "-c",
        'mcp_servers.codex3d.env_vars=["CODEX3D_BRIDGE_HOST","CODEX3D_BRIDGE_PORT","CODEX3D_BRIDGE_TOKEN","PYTHONPATH"]',
        prompt,
    ]
    completed = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, check=False, timeout=180)
    if token in completed.stdout or token in completed.stderr:
        raise GateFailure("Authentication token leaked into Codex output.")
    sequence = _extract_codex_tool_sequence(completed.stdout)
    expected = [
        "blender_inspect_scene",
        "blender_transform_object",
        "blender_assign_material",
        "blender_inspect_scene",
    ]

    from codex3d_api import SocketConnectorClient

    with SocketConnectorClient(host="127.0.0.1", port=port, token=token) as client:
        inspection = client.inspect_scene()
    core = next((item for item in inspection.scene.objects if item.label == CORE_NAME), None)
    verified = bool(core and core.metadata.get("material_name") == CODEX_MATERIAL)
    if core:
        verified = verified and all(
            math.isclose(value, expected_value, abs_tol=1e-4)
            for value, expected_value in zip(
                (core.transform.location.x, core.transform.location.y, core.transform.location.z),
                (0.0, 0.0, 1.25),
            )
        )
        verified = verified and all(
            math.isclose(value, 1.3, abs_tol=1e-4)
            for value in (core.transform.scale.x, core.transform.scale.y, core.transform.scale.z)
        )
    ok = completed.returncode == 0 and verified and _contains_subsequence(sequence, expected)
    return {
        "status": "PASSED" if ok else "FAILED",
        "returncode": completed.returncode,
        "tool_sequence": sequence,
        "required_sequence_observed": _contains_subsequence(sequence, expected),
        "scene_verified": verified,
        "final_location": (
            [core.transform.location.x, core.transform.location.y, core.transform.location.z] if core else None
        ),
        "final_scale": [core.transform.scale.x, core.transform.scale.y, core.transform.scale.z] if core else None,
        "material_name": core.metadata.get("material_name") if core else None,
        "error_tail": completed.stderr[-800:] if completed.returncode else "",
    }


def _readiness(codex_status: str) -> dict[str, Any]:
    statuses = {
        "Natural-language MCP control": "READY" if codex_status == "PASSED" else "NOT_RUN",
        "Primitive creation": "READY",
        "Transform": "READY",
        "Basic material": "READY",
        "Point light": "READY",
        "Curve creation": "MISSING",
        "Advanced material": "MISSING",
        "Camera": "MISSING",
        "World lighting": "MISSING",
        "Static render": "MISSING",
        "Render image return": "MISSING",
        "Keyframe animation": "MISSING",
        "Timeline playback": "MISSING",
        "Video export": "MISSING",
        "Snapshot / Undo": "MISSING",
        "Stable UUID / Scene IR": "PARTIAL",
    }
    if not set(statuses.values()) <= READY_STATUSES:
        raise GateFailure("Readiness matrix contains an invalid status.")
    return {
        "gate": "Demo Gate 0",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "capabilities": [{"capability": name, "status": status} for name, status in statuses.items()],
    }


def run_gate(args: argparse.Namespace) -> dict[str, Any]:
    blender = Path(args.blender)
    if not blender.is_file():
        raise GateFailure(f"Blender executable unavailable: {blender}")
    artifact_dir = Path(args.artifact_dir).resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    blend_path = artifact_dir / "codex3d_gate0.blend"
    ready_path = artifact_dir / ".bridge-ready.json"
    stop_path = artifact_dir / ".bridge-stop"
    for path in (ready_path, stop_path):
        path.unlink(missing_ok=True)

    config_path = Path.home() / ".codex" / "config.toml"
    config_before = _file_digest(config_path)
    baseline = {"status": "SKIPPED"} if args.skip_baseline else _run_baseline()
    port = _available_port()
    token = secrets.token_urlsafe(32)
    env = dict(os.environ)
    env.update(
        {
            "PYTHONPATH": _pythonpath(),
            "CODEX3D_BRIDGE_HOST": "127.0.0.1",
            "CODEX3D_BRIDGE_PORT": str(port),
            "CODEX3D_BRIDGE_TOKEN": token,
            "CODEX3D_GATE0_PORT": str(port),
            "CODEX3D_GATE0_TOKEN": token,
            "CODEX3D_GATE0_STOP_PATH": str(stop_path),
            "CODEX3D_GATE0_READY_PATH": str(ready_path),
            "CODEX3D_GATE0_BLEND_PATH": str(blend_path),
        }
    )
    blender_log = (artifact_dir / "blender.log").open("w", encoding="utf-8")
    process = subprocess.Popen(
        [str(blender), "--factory-startup", "--background", "--python", str(Path(__file__).resolve()), "--", "--blender-host"],
        cwd=ROOT,
        env=env,
        stdout=blender_log,
        stderr=subprocess.STDOUT,
        text=True,
    )
    cleanup: dict[str, Any] = {}
    result: dict[str, Any] | None = None
    try:
        hello = _wait_for_bridge(port, token)
        mcp_result, final_inspection = _run_mcp_scene(env, token)
        codex_result = _run_codex_acceptance(env, port, token)
        if codex_result["status"] == "FAILED":
            raise GateFailure(f"Codex natural-language acceptance failed: {codex_result}")
        inspection_text = json.dumps(final_inspection, ensure_ascii=False)
        if token in inspection_text:
            raise GateFailure("Authentication token leaked into scene inspection.")
        readiness = _readiness(codex_result["status"])
        (artifact_dir / "readiness.json").write_text(
            json.dumps(readiness, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        result = {
            "gate_status": "PASS" if codex_result["status"] == "PASSED" else "PARTIAL",
            "baseline": baseline,
            "mcp": mcp_result,
            "codex_natural_language": codex_result,
            "blender": {
                "status": "PASSED",
                "version": hello.get("blender_version"),
                "backend": hello.get("backend"),
                "bind_address": "127.0.0.1",
                "port": port,
                "blend_artifact": str(blend_path),
            },
            "safety": {
                **_source_safety_audit(),
                "isolated_factory_startup": True,
                "global_codex_config_unchanged": False,
                "token_absent_from_results": True,
                "arbitrary_python_enabled": False,
            },
            "readiness_artifact": str(artifact_dir / "readiness.json"),
        }
    finally:
        stop_path.touch()
        try:
            process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        blender_log.close()
        ready_path.unlink(missing_ok=True)
        stop_path.unlink(missing_ok=True)
        cleanup = {
            "blender_returncode": process.returncode,
            "bridge_port_released": _port_is_released(port),
            "ready_sentinel_removed": not ready_path.exists(),
            "stop_sentinel_removed": not stop_path.exists(),
        }

    config_after = _file_digest(config_path)
    if result is None:
        raise GateFailure("Gate ended before producing a result.")
    result["safety"]["global_codex_config_unchanged"] = config_before == config_after
    result["cleanup"] = cleanup
    if process.returncode != 0 or not cleanup["bridge_port_released"]:
        raise GateFailure(f"Isolated Blender cleanup failed: {cleanup}")
    if not blend_path.is_file():
        raise GateFailure("Isolated Blender did not save the Gate 0 .blend artifact.")
    if config_before != config_after:
        raise GateFailure("Global Codex config changed during the ephemeral acceptance test.")
    serialized = json.dumps(result, indent=2, sort_keys=True)
    if token in serialized:
        raise GateFailure("Authentication token leaked into the Gate 0 result.")
    (artifact_dir / "gate_0_result.json").write_text(serialized + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    if "--blender-host" in sys.argv:
        try:
            return _blender_host()
        except Exception as exc:
            print(f"Gate 0 Blender host failed: {exc}", file=sys.stderr)
            return 1
    parser = argparse.ArgumentParser(description="Run Codex3D Demo Gate 0 against an isolated Blender process.")
    parser.add_argument("--blender", default=str(DEFAULT_BLENDER))
    parser.add_argument("--artifact-dir", default=str(ROOT / "artifacts/demo_gate_0"))
    parser.add_argument("--skip-baseline", action="store_true", help="Used by the env-gated integration test.")
    args = parser.parse_args(argv)
    try:
        result = run_gate(args)
    except Exception as exc:
        print(f"Demo Gate 0 failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["gate_status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
