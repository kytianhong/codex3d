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
BLENDER = Path("/Applications/Blender.app/Contents/MacOS/Blender")
ARTIFACT_ROOT = ROOT / "artifacts/hackathon_sol_demo"
COLLECTION = "C3D_SOL_DEMO"
PREFIX = "C3D_SOL_"
CORE = f"{PREFIX}EnergyCore"
CORE_SHELL = f"{PREFIX}CoreShell"
ROOT_EMPTY = f"{PREFIX}KineticRoot"
PETALS = [f"{PREFIX}Orbit_{index:02d}" for index in range(1, 7)]
OUTER_RING = f"{PREFIX}OuterRing"
SHADOW = f"{PREFIX}ShadowPlane"
CAMERA = f"{PREFIX}Camera"
AREA_LIGHT = f"{PREFIX}KeyArea"
RIM_LIGHT = f"{PREFIX}RimLight"
CORE_MATERIAL = f"{PREFIX}CoreEmission"
SHELL_MATERIAL = f"{PREFIX}CoreShellGlass"
WARM_MATERIAL = f"{PREFIX}WarmMetal"
DARK_MATERIAL = f"{PREFIX}DarkMetal"
FOLLOWUP_CORE_MATERIAL = f"{PREFIX}CoreEmissionBright"
FOLLOWUP_RING_MATERIAL = f"{PREFIX}OuterWarmMetal"


class DemoFailure(RuntimeError):
    pass


class StdioMcpClient:
    def __init__(self, env: dict[str, str]) -> None:
        self._next_id = 1
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
        message = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}
        if self.process.stdin is None or self.process.stdout is None:
            raise DemoFailure("MCP process streams are unavailable.")
        self.process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            stderr = self.process.stderr.read()[-1200:] if self.process.stderr else ""
            raise DemoFailure(f"MCP process exited without a response: {stderr}")
        response = json.loads(line)
        if response.get("id") != request_id or "error" in response:
            raise DemoFailure(f"MCP JSON-RPC failure: {response.get('error', 'correlation mismatch')}")
        return response["result"]

    def call_tool(self, name: str, arguments: dict[str, Any], *, allow_failure: bool = False) -> dict[str, Any]:
        result = self.request("tools/call", {"name": name, "arguments": arguments})
        payload = result.get("structuredContent")
        if not isinstance(payload, dict):
            raise DemoFailure(f"{name} returned no structured content.")
        if not payload.get("ok") and not allow_failure:
            raise DemoFailure(f"{name} failed: {payload.get('error')}")
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
        for path in ("packages/protocol", "packages/tools", "apps/api", "apps/mcp", "connectors/blender_addon")
    )


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _port_released(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.25)
        return probe.connect_ex(("127.0.0.1", port)) != 0


def _digest(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _action(action_type: str, parameters: dict[str, Any], description: str) -> dict[str, Any]:
    return {
        "type": action_type,
        "description": description,
        "parameters": parameters,
        "metadata": {"demo": True, "concept": "unofficial_sol_inspired", "model_used": "none"},
    }


def _curve_points() -> list[list[float]]:
    return [
        [0.30, 0.0, 0.12],
        [0.74, -0.42, -0.02],
        [1.47, -0.46, 0.09],
        [2.08, 0.0, 0.22],
        [1.47, 0.46, 0.09],
        [0.74, 0.42, -0.02],
    ]


def _circle_points(radius: float, count: int, z: float) -> list[list[float]]:
    return [
        [radius * math.cos(index * 2 * math.pi / count), radius * math.sin(index * 2 * math.pi / count), z]
        for index in range(count)
    ]


def geometry_actions() -> list[dict[str, Any]]:
    actions = [
        _action("create_object", {"primitive": "empty", "name": ROOT_EMPTY, "display_size": 0.8, "collection": COLLECTION, "semantic_type": "kinetic_root"}, "Create a neutral animation root."),
        _action("create_object", {"primitive": "sphere", "name": CORE, "location": [0, 0, 0.20], "dimensions": [0.72, 0.72, 0.72], "collection": COLLECTION, "semantic_type": "energy_core_inner"}, "Create the compact blue-white energy core."),
        _action("create_object", {"primitive": "sphere", "name": CORE_SHELL, "location": [0, 0, 0.20], "dimensions": [1.16, 1.16, 1.16], "collection": COLLECTION, "semantic_type": "energy_core_shell"}, "Create a soft glass-metal shell around the core."),
    ]
    for index, name in enumerate(PETALS):
        actions.append(
            _action(
                "create_object",
                {
                    "primitive": "curve",
                    "name": name,
                    "points": _curve_points(),
                    "curve_type": "bezier",
                    "cyclic": True,
                    "bevel_depth": 0.085,
                    "bevel_resolution": 5,
                    "fill_mode": "FULL",
                    "location": [0, 0, 0.06 if index % 2 == 0 else -0.06],
                    "rotation": [0.055 if index % 2 == 0 else -0.055, 0, index * math.pi / 3],
                    "collection": COLLECTION,
                    "semantic_type": "kinetic_orbit",
                },
                "Create one independent radial orbit curve.",
            )
        )
    actions.extend(
        [
            _action("create_object", {"primitive": "curve", "name": OUTER_RING, "points": _circle_points(2.45, 48, -0.12), "curve_type": "poly", "cyclic": True, "bevel_depth": 0.052, "bevel_resolution": 4, "fill_mode": "FULL", "collection": COLLECTION, "semantic_type": "kinetic_boundary"}, "Create a functional warm boundary ring."),
            _action("create_object", {"primitive": "plane", "name": SHADOW, "location": [0, 0, -0.48], "dimensions": [10.0, 10.0, 0.01], "collection": COLLECTION, "semantic_type": "studio_backdrop"}, "Create a broad studio shadow receiver without visible hard edges."),
        ]
    )
    return actions


def _material(name: str, color: list[float], roughness: float, metallic: float, **extra: Any) -> dict[str, Any]:
    return {"name": name, "base_color": color, "roughness": roughness, "metallic": metallic, **extra}


def material_actions() -> list[dict[str, Any]]:
    core = _material(CORE_MATERIAL, [0.012, 0.055, 0.28, 1], 0.18, 0.16, emission_color=[0.015, 0.12, 0.9, 1], emission_strength=1.8, transmission=0.04)
    shell = _material(SHELL_MATERIAL, [0.055, 0.11, 0.19, 0.42], 0.18, 0.62, emission_color=[0.03, 0.14, 0.28, 1], emission_strength=0.6, transmission=0.38, alpha=0.42)
    warm = _material(WARM_MATERIAL, [0.42, 0.12, 0.025, 1], 0.26, 0.82, emission_color=[0.15, 0.025, 0.005, 1], emission_strength=0.35)
    dark = _material(DARK_MATERIAL, [0.018, 0.025, 0.045, 1], 0.32, 0.9)
    actions = [
        _action("assign_material", {"target_name": CORE, "material": core}, "Assign the blue-white inner core material."),
        _action("assign_material", {"target_name": CORE_SHELL, "material": shell}, "Assign the soft glass-metal shell material."),
    ]
    for index, name in enumerate(PETALS):
        actions.append(_action("assign_material", {"target_name": name, "material": warm if index % 2 == 0 else dark}, "Assign alternating kinetic metal."))
    actions.extend(
        [
            _action("assign_material", {"target_name": OUTER_RING, "material": warm}, "Make the outer boundary visually connect the warm orbit rhythm."),
            _action("assign_material", {"target_name": SHADOW, "material": _material(f"{PREFIX}StudioMat", [0.012, 0.018, 0.032, 1], 0.82, 0.02)}, "Assign a soft dark studio surface."),
        ]
    )
    for name in [CORE, CORE_SHELL, *PETALS, OUTER_RING]:
        actions.append(_action("set_parent", {"target_name": name, "parent_name": ROOT_EMPTY, "keep_transform": True}, "Parent the emblem element to the animation root."))
    return actions


def lighting_camera_actions() -> list[dict[str, Any]]:
    return [
        _action("configure_world", {"color": [0.006, 0.011, 0.024], "strength": 0.18}, "Set a low-strength blue-black studio world."),
        _action("create_object", {"primitive": "area_light", "name": AREA_LIGHT, "location": [1.4, -2.2, 5.8], "look_at": [0, 0, 0], "light": {"color": [1.0, 0.58, 0.30], "energy": 820, "size": 6.0}, "collection": COLLECTION, "semantic_type": "key_light"}, "Create a broad soft warm Area Light."),
        _action("create_object", {"primitive": "point_light", "name": RIM_LIGHT, "location": [-3.8, 2.8, 3.4], "light": {"color": [0.22, 0.50, 1.0], "energy": 680}, "collection": COLLECTION, "semantic_type": "rim_light"}, "Create the cool depth-separating rim light."),
        _action("create_object", {"primitive": "camera", "name": CAMERA, "location": [0, -7.2, 7.8], "focal_length": 58, "look_at": [0, 0, 0.0], "active": True, "collection": COLLECTION, "semantic_type": "render_camera"}, "Create a centered, studio-filling square camera with stable safe margins."),
        _action("configure_scene", {"engine": "BLENDER_EEVEE_NEXT", "resolution_x": 512, "resolution_y": 512, "samples": 48, "transparent": False, "fps": 24, "frame_start": 1, "frame_end": 72}, "Configure the 3-second Eevee timeline and output."),
    ]


def animation_actions() -> list[dict[str, Any]]:
    actions = [
        _action("keyframe_object", {"target_name": ROOT_EMPTY, "keyframes": [{"frame": 1, "rotation": [0, 0, 0]}, {"frame": 72, "rotation": [0, 0, 2 * math.pi]}], "interpolation": "LINEAR", "cycle": True}, "Animate one full kinetic rotation."),
        _action("keyframe_object", {"target_name": CORE, "keyframes": [{"frame": 1, "emission_strength": 1.6}, {"frame": 36, "emission_strength": 3.2}, {"frame": 72, "emission_strength": 1.6}], "interpolation": "BEZIER", "cycle": True}, "Animate a soft core emission pulse."),
    ]
    for index, name in enumerate(PETALS):
        offset = 0.025 * math.sin(index * math.pi / 3)
        actions.append(
            _action(
                "keyframe_object",
                {"target_name": name, "keyframes": [{"frame": 1, "scale": [1 + offset, 1 + offset, 1]}, {"frame": 36, "scale": [1.045 - offset, 1.045 - offset, 1.025]}, {"frame": 72, "scale": [1 + offset, 1 + offset, 1]}], "interpolation": "BEZIER", "cycle": True},
                "Animate a phase-offset orbit breath.",
            )
        )
    return actions


def _run_stage(client: StdioMcpClient, name: str, actions: list[dict[str, Any]], pause: float) -> dict[str, Any]:
    started = time.monotonic()
    result = client.call_tool("blender_execute_batch", {"actions": actions}, allow_failure=True)
    if result["failed_count"] or result["succeeded_count"] != len(actions):
        raise DemoFailure(f"Stage {name} did not complete: {result}")
    inspection = client.call_tool("blender_inspect_scene", {"mode": "full"})
    if pause > 0:
        time.sleep(pause)
    return {
        "stage": name,
        "action_count": len(actions),
        "succeeded_count": result["succeeded_count"],
        "object_count": inspection["inspection"]["scene"]["metadata"].get("object_count"),
        "elapsed_ms": round((time.monotonic() - started) * 1000, 2),
    }


def _validate_render(result: dict[str, Any], *, animation: bool = False) -> None:
    if animation:
        if result.get("file_size", 0) < 10_000 or result.get("keyframe_count", 0) < 1:
            raise DemoFailure(f"Animation validation failed: {result}")
        if result.get("frame_end", 0) - result.get("frame_start", 0) + 1 not in {72, 73}:
            raise DemoFailure("Animation frame range is not the expected 72-frame loop.")
        return
    checks = (
        result.get("width") == 512,
        result.get("height") == 512,
        result.get("file_size", 0) > 5_000,
        result.get("mean_luminance", 0) > 0.002,
        result.get("nonblack_pixel_ratio", 0) > 0.01,
        result.get("nontransparent_pixel_ratio", 0) > 0.01,
        result.get("subject_visible") is True,
        result.get("visible_subject_count", 0) >= 7,
        result.get("active_camera") == CAMERA,
    )
    if not all(checks):
        raise DemoFailure(f"Static render validation failed: {result}")


def _extract_tool_sequence(output: str) -> list[str]:
    sequence: list[str] = []
    seen: set[str] = set()
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item") if isinstance(event, dict) else None
        if not isinstance(item, dict) or item.get("type") != "mcp_tool_call":
            continue
        item_id = str(item.get("id", len(sequence)))
        tool = item.get("tool") or item.get("name")
        if isinstance(tool, str) and item_id not in seen:
            seen.add(item_id)
            sequence.append(tool)
    return sequence


def _extract_tool_calls(output: str) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item") if isinstance(event, dict) else None
        if not isinstance(item, dict) or item.get("type") != "mcp_tool_call":
            continue
        item_id = str(item.get("id", len(calls)))
        if item_id in seen:
            continue
        seen.add(item_id)
        calls.append({"tool": item.get("tool") or item.get("name"), "arguments": item.get("arguments")})
    return calls


def _subsequence(values: list[str], expected: list[str]) -> bool:
    cursor = 0
    for value in values:
        if cursor < len(expected) and value == expected[cursor]:
            cursor += 1
    return cursor == len(expected)


def _codex_followup(env: dict[str, str], render_path: str) -> dict[str, Any]:
    codex = shutil.which("codex")
    if codex is None:
        return {"status": "NOT_RUN", "reason": "Codex CLI unavailable"}
    prompt = (
        "只使用 codex3d MCP Blender 工具，不运行 shell、不编辑文件、不改变六条 C3D_SOL_Orbit 曲线的结构。"
        "先调用 blender_inspect_scene。然后调用 blender_assign_material，让中心 C3D_SOL_EnergyCore 更明亮，"
        f"材质名 {FOLLOWUP_CORE_MATERIAL}，base_color [0.025,0.14,0.48,1]，roughness 0.14，metallic 0.24，"
        "emission_color [0.025,0.22,1,1]，emission_strength 3.4。再调用 blender_assign_material，让外环 "
        f"C3D_SOL_OuterRing 稍微偏暖，材质名 {FOLLOWUP_RING_MATERIAL}，base_color [0.34,0.08,0.018,1]，"
        "roughness 0.24，metallic 0.88。再调用 blender_transform_object 把 C3D_SOL_Camera 降低到 "
        "[0,-7.2,7.1] 并 look_at [0,0,0.0]。调用 blender_render 输出 still 到本次 artifact root 内的 "
        f"{render_path}。blender_render 的 path 参数必须精确等于字符串 {render_path}，不能省略 run 目录。"
        "最后再次调用 blender_inspect_scene 并报告。必须严格按上述顺序调用这些工具，"
        "不要使用 blender_execute_batch。"
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
        'mcp_servers.codex3d.env_vars=["CODEX3D_BRIDGE_HOST","CODEX3D_BRIDGE_PORT","CODEX3D_BRIDGE_TOKEN","CODEX3D_ARTIFACT_ROOT","CODEX3D_BRIDGE_REQUEST_TIMEOUT","CODEX3D_MCP_INCLUDE_IMAGES","PYTHONPATH"]',
        prompt,
    ]
    completed = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, check=False, timeout=300)
    sequence = _extract_tool_sequence(completed.stdout)
    calls = _extract_tool_calls(completed.stdout)
    expected = [
        "blender_inspect_scene",
        "blender_assign_material",
        "blender_assign_material",
        "blender_transform_object",
        "blender_render",
        "blender_inspect_scene",
    ]
    return {
        "status": "PASSED" if completed.returncode == 0 and _subsequence(sequence, expected) else "FAILED",
        "returncode": completed.returncode,
        "tool_sequence": sequence,
        "tool_calls": calls,
        "required_sequence_observed": _subsequence(sequence, expected),
        "error_tail": completed.stderr[-800:] if completed.returncode else "",
    }


def _objects(inspection: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["label"]: item for item in inspection["inspection"]["scene"]["objects"]}


def _canonical_inspection_summary(inspection: dict[str, Any]) -> dict[str, Any]:
    scene = inspection["inspection"]["scene"]
    objects = []
    for item in scene["objects"]:
        if not item["label"].startswith(PREFIX):
            continue
        transform = item["transform"]
        objects.append(
            {
                "uuid": item.get("blender_uuid"),
                "name": item["label"],
                "location": transform["location"],
                "rotation": transform["rotation_euler"],
                "scale": transform["scale"],
                "material": item.get("metadata", {}).get("material_name"),
            }
        )
    objects.sort(key=lambda item: (item["uuid"] or "", item["name"]))
    return {
        "objects": objects,
        "active_camera": scene.get("metadata", {}).get("active_camera"),
    }


def _package_animation(run_dir: Path) -> dict[str, Any]:
    tools_path = str(ROOT / "packages/tools")
    if tools_path not in sys.path:
        sys.path.insert(0, tools_path)
    from codex3d_tools import AnimationEncoder, EncoderError, find_ffmpeg

    ffmpeg = find_ffmpeg()
    if ffmpeg is None:
        return {
            "status": "NOT_RUN",
            "reason": "ffmpeg unavailable; set CODEX3D_FFMPEG_PATH to a trusted ffmpeg executable",
        }
    try:
        encoded = AnimationEncoder(run_dir, ffmpeg_path=ffmpeg).encode(
            "frames",
            "sol_animation.mp4",
            fps=24,
        )
    except EncoderError as exc:
        return {"status": "FAILED", "reason": str(exc)}
    return {"status": "PASSED", **encoded}


def _write_json_atomic(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _promote(run_dir: Path, artifact_root: Path, animation: dict[str, Any]) -> dict[str, str]:
    outputs: dict[str, str] = {}
    for name in (
        "sol_demo.blend",
        "preview_initial.png",
        "preview_followup.png",
        "preview_polished.png",
        "snapshot_restore_result.json",
    ):
        source = run_dir / name
        if not source.is_file():
            raise DemoFailure(f"Expected artifact is missing: {source}")
        destination = artifact_root / name
        os.replace(source, destination)
        outputs[name] = name
    if animation.get("animation_format") == "mp4":
        source = run_dir / "sol_animation.mp4"
        destination = artifact_root / "sol_animation.mp4"
        os.replace(source, destination)
        outputs["animation"] = "sol_animation.mp4"
    else:
        source = run_dir / "frames"
        destination = artifact_root / "frames"
        if destination.exists():
            backup = artifact_root / f"frames_previous_{int(time.time())}"
            os.replace(destination, backup)
        os.replace(source, destination)
        outputs["animation"] = "frames/"
        encoded = run_dir / "sol_animation.mp4"
        if encoded.is_file():
            destination = artifact_root / "sol_animation.mp4"
            os.replace(encoded, destination)
            outputs["animation_mp4"] = "sol_animation.mp4"
    return outputs


def run_demo(args: argparse.Namespace) -> dict[str, Any]:
    artifact_root = Path(args.artifact_root).resolve()
    artifact_root.mkdir(parents=True, exist_ok=True)
    run_id = time.strftime("run_%Y%m%dT%H%M%SZ", time.gmtime()) + f"_{secrets.token_hex(3)}"
    run_dir = artifact_root / run_id
    run_dir.mkdir()
    codex_config_path = Path.home() / ".codex/config.toml"
    codex_config_before = _digest(codex_config_path)
    isolated = bool(args.isolated)
    port = _free_port() if isolated else int(os.environ.get("CODEX3D_BRIDGE_PORT", "9876"))
    token = secrets.token_urlsafe(32) if isolated else os.environ.get("CODEX3D_BRIDGE_TOKEN", "")
    if not token:
        raise DemoFailure("CODEX3D_BRIDGE_TOKEN is required for live mode.")
    env = dict(os.environ)
    env.update(
        {
            "PYTHONPATH": _pythonpath(),
            "CODEX3D_BRIDGE_HOST": "127.0.0.1",
            "CODEX3D_BRIDGE_PORT": str(port),
            "CODEX3D_BRIDGE_TOKEN": token,
            "CODEX3D_BRIDGE_REQUEST_TIMEOUT": "240",
            "CODEX3D_ARTIFACT_ROOT": str(artifact_root),
            "CODEX3D_MCP_INCLUDE_IMAGES": "0",
        }
    )
    blender_process: subprocess.Popen[str] | None = None
    stop_path = run_dir / ".stop"
    if isolated:
        env.update(
            {
                "CODEX3D_GATE0_PORT": str(port),
                "CODEX3D_GATE0_TOKEN": token,
                "CODEX3D_GATE0_STOP_PATH": str(stop_path),
                "CODEX3D_GATE0_READY_PATH": str(run_dir / ".ready.json"),
                "CODEX3D_GATE0_BLEND_PATH": str(run_dir / "host_shutdown.blend"),
            }
        )
        log = (run_dir / "blender.log").open("w", encoding="utf-8")
        blender_process = subprocess.Popen(
            [str(args.blender), "--factory-startup", "--background", "--python", str(ROOT / "scripts/run_demo_gate_0.py"), "--", "--blender-host"],
            cwd=ROOT,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
        )
    else:
        log = None

    client = StdioMcpClient(env)
    result: dict[str, Any] | None = None
    try:
        deadline = time.monotonic() + 45
        while True:
            ping = client.call_tool("blender_ping", {}, allow_failure=True)
            if ping.get("ok"):
                break
            if time.monotonic() >= deadline:
                raise DemoFailure(f"Blender bridge did not become ready: {ping.get('error')}")
            time.sleep(0.2)
        before = client.call_tool("blender_inspect_scene", {"mode": "full"})
        before_objects = _objects(before)
        if isolated:
            for name in sorted(before_objects):
                client.call_tool("blender_delete_object", {"target_name": name})
            existing = []
        else:
            existing = sorted(name for name in before_objects if name.startswith(PREFIX))
            collection_members = sorted(
                name
                for name, item in before_objects.items()
                if COLLECTION in item.get("metadata", {}).get("collections", [])
            )
            foreign_members = [name for name in collection_members if not name.startswith(PREFIX)]
            if foreign_members:
                raise DemoFailure(
                    f"{COLLECTION} contains non-demo objects and will not be modified: {foreign_members}"
                )
            if collection_members and not args.replace_demo_collection:
                raise DemoFailure(
                    f"{COLLECTION} is not empty. Use --replace-demo-collection to replace only {PREFIX} objects."
                )
        if existing and not args.replace_demo_collection:
            raise DemoFailure(
                f"The {COLLECTION} demo namespace is not empty. Use --replace-demo-collection to replace only {PREFIX} objects."
            )
        for name in existing:
            client.call_tool("blender_delete_object", {"target_name": name})

        stages = []
        stages.append(_run_stage(client, "geometry", geometry_actions(), args.pause))
        stages.append(_run_stage(client, "materials", material_actions(), args.pause))
        stages.append(_run_stage(client, "lighting_camera", lighting_camera_actions(), args.pause))
        stages.append(_run_stage(client, "animation", animation_actions(), args.pause))

        if not isolated and not args.render_live:
            inspection = client.call_tool("blender_inspect_scene", {"mode": "full"})
            result = {
                "status": "MANUAL_ACCEPTANCE_PENDING",
                "mode": "live_gui",
                "stages": stages,
                "object_count": len([name for name in _objects(inspection) if name.startswith(PREFIX)]),
                "timeline_playback": "MANUAL_ACCEPTANCE_PENDING",
                "unofficial_concept_demo": True,
            }
            return result

        initial_payload = client.call_tool("blender_render", {"kind": "still", "path": f"{run_id}/preview_initial.png"})
        initial = initial_payload["result"]["output"]
        _validate_render(initial)
        stages.append({"stage": "render_initial", "result": initial})

        animation_payload = client.call_tool("blender_render", {"kind": "animation", "path": f"{run_id}/sol_animation.mp4"})
        animation = animation_payload["result"]["output"]
        _validate_render(animation, animation=True)
        stages.append({"stage": "render_animation", "result": animation})

        followup_relative = f"{run_id}/preview_followup.png"
        codex = _codex_followup(env, followup_relative) if not args.skip_codex else {"status": "NOT_RUN", "reason": "--skip-codex"}
        _write_json_atomic(run_dir / "codex_followup.json", codex)
        if codex["status"] == "FAILED":
            raise DemoFailure(f"Codex follow-up failed: {codex}")
        followup_path = run_dir / "preview_followup.png"
        if codex["status"] == "NOT_RUN":
            followup_payload = client.call_tool("blender_render", {"kind": "still", "path": followup_relative})
            followup = followup_payload["result"]["output"]
        else:
            if not followup_path.is_file():
                raise DemoFailure(f"Codex did not produce preview_followup.png: {codex}")
            followup_payload = client.call_tool("blender_render", {"kind": "still", "path": followup_relative})
            followup = followup_payload["result"]["output"]
        _validate_render(followup)

        if codex["status"] == "PASSED":
            rebound = client.call_tool(
                "blender_keyframe_object",
                {
                    "target_name": CORE,
                    "keyframes": [
                        {"frame": 1, "emission_strength": 2.4},
                        {"frame": 36, "emission_strength": 4.2},
                        {"frame": 72, "emission_strength": 2.4},
                    ],
                    "interpolation": "BEZIER",
                    "cycle": True,
                },
            )
            stages.append({"stage": "followup_animation_rebind", "result": rebound["result"]["output"]})

        before_snapshot = client.call_tool("blender_inspect_scene", {"mode": "full"})
        before_summary = _canonical_inspection_summary(before_snapshot)
        missing_uuids = [item["name"] for item in before_summary["objects"] if not item["uuid"]]
        if missing_uuids:
            raise DemoFailure(f"Stable object UUIDs are missing before snapshot: {missing_uuids}")
        snapshot_payload = client.call_tool(
            "blender_create_snapshot",
            {"source_action_id": "sol_demo_polish", "source_turn": "hackathon_sprint_02d"},
        )
        snapshot = snapshot_payload["result"]["output"]
        core_uuid = next(item["uuid"] for item in before_summary["objects"] if item["name"] == CORE)
        camera_uuid = next(item["uuid"] for item in before_summary["objects"] if item["name"] == CAMERA)
        client.call_tool("blender_transform_object", {"target_uuid": core_uuid, "location": [1.8, 0.0, 1.8], "scale": [1.5, 1.5, 1.5]})
        client.call_tool("blender_transform_object", {"target_uuid": camera_uuid, "location": [3.0, -4.0, 2.0], "look_at": [0, 0, 0]})
        mutated = client.call_tool("blender_inspect_scene", {"mode": "full"})
        mutated_summary = _canonical_inspection_summary(mutated)
        if mutated_summary == before_summary:
            raise DemoFailure("Intentional pre-restore mutation did not change the canonical scene summary.")
        restored_payload = client.call_tool(
            "blender_restore_snapshot",
            {
                "snapshot_id": snapshot["snapshot_id"],
                "current_fingerprint": mutated["inspection"]["metadata"]["scene_fingerprint"],
                "snapshot_fingerprint": snapshot["scene_fingerprint"],
            },
        )
        restored = restored_payload["result"]["output"]
        after_snapshot = client.call_tool("blender_inspect_scene", {"mode": "full"})
        after_summary = _canonical_inspection_summary(after_snapshot)
        snapshot_restore_result = {
            "status": "PASSED" if before_summary == after_summary else "FAILED",
            "snapshot_id": snapshot["snapshot_id"],
            "scene_fingerprint": snapshot["scene_fingerprint"],
            "restored_fingerprint": restored.get("scene_fingerprint"),
            "canonical_summary_match": before_summary == after_summary,
            "object_count": len(after_summary["objects"]),
            "active_camera": after_summary["active_camera"],
            "uuid_count": len({item["uuid"] for item in after_summary["objects"]}),
        }
        if snapshot_restore_result["status"] != "PASSED":
            raise DemoFailure("Snapshot restore did not recover the canonical scene summary.")
        _write_json_atomic(run_dir / "snapshot_restore_result.json", snapshot_restore_result)
        stages.append({"stage": "snapshot_restore", "result": snapshot_restore_result})

        polished_payload = client.call_tool("blender_render", {"kind": "still", "path": f"{run_id}/preview_polished.png"})
        polished = polished_payload["result"]["output"]
        _validate_render(polished)
        stages.append({"stage": "render_polished", "result": polished})

        checkpoint = client.call_tool("blender_save_checkpoint", {"path": f"{run_id}/sol_demo.blend"})["result"]["output"]
        final_inspection = client.call_tool("blender_inspect_scene", {"mode": "full"})
        objects = _objects(final_inspection)
        curves = [name for name in PETALS if name in objects]
        if codex["status"] == "PASSED":
            camera_location = objects.get(CAMERA, {}).get("transform", {}).get("location", {})
            followup_ok = (
                len(curves) == 6
                and objects.get(CORE, {}).get("metadata", {}).get("material_name") == FOLLOWUP_CORE_MATERIAL
                and objects.get(OUTER_RING, {}).get("metadata", {}).get("material_name") == FOLLOWUP_RING_MATERIAL
                and math.isclose(float(camera_location.get("z", 0)), 7.1, abs_tol=1e-4)
            )
            if not followup_ok:
                raise DemoFailure("Codex follow-up scene state did not match its requested edit.")
        result = {
            "status": "DONE" if codex["status"] == "PASSED" and not animation.get("fallback") else "PARTIAL",
            "mode": "isolated" if isolated else "live_gui",
            "unofficial_concept_demo": True,
            "stages": stages,
            "codex_followup": codex,
            "object_count": len([name for name in objects if name.startswith(PREFIX)]),
            "curve_count": len(curves),
            "initial_render": initial,
            "followup_render": followup,
            "polished_render": polished,
            "animation": animation,
            "snapshot_restore": snapshot_restore_result,
            "checkpoint": checkpoint,
            "timeline_playback": "MANUAL_ACCEPTANCE_PENDING",
        }
        _write_json_atomic(run_dir / "scene_inspection.json", final_inspection)
        _write_json_atomic(
            run_dir / "render_result.json",
            {"initial": initial, "followup": followup, "polished": polished, "animation": animation},
        )
    finally:
        client.close()
        if blender_process is not None:
            stop_path.touch()
            try:
                blender_process.wait(timeout=45)
            except subprocess.TimeoutExpired:
                blender_process.terminate()
                try:
                    blender_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    blender_process.kill()
                    blender_process.wait(timeout=5)
            if log is not None:
                log.close()
            (run_dir / ".ready.json").unlink(missing_ok=True)
            stop_path.unlink(missing_ok=True)

    if result is None:
        raise DemoFailure("Demo finished without a result.")
    if result["animation"].get("fallback"):
        result["mp4_packaging"] = _package_animation(run_dir)
    else:
        result["mp4_packaging"] = {"status": "PASSED", **result["animation"]}
    cleanup = {
        "mcp_process_reaped": client.process.poll() is not None,
        "blender_returncode": blender_process.returncode if blender_process is not None else None,
        "bridge_port_released": _port_released(port) if isolated else None,
    }
    codex_config_after = _digest(codex_config_path)
    result["cleanup"] = cleanup
    result["safety"] = {
        "isolated_factory_startup": isolated,
        "global_codex_config_unchanged": codex_config_before == codex_config_after,
        "artifact_root_enforced": True,
        "token_absent_from_results": True,
        "arbitrary_python_enabled": False,
        "user_blend_opened": False if isolated else None,
    }
    if isolated and (blender_process is None or blender_process.returncode != 0 or not cleanup["bridge_port_released"]):
        raise DemoFailure(f"Isolated Blender cleanup failed: {cleanup}")
    token_text = json.dumps(result, ensure_ascii=False)
    if token in token_text:
        raise DemoFailure("Bridge token leaked into demo results.")
    if codex_config_before != codex_config_after:
        raise DemoFailure("Global Codex config changed during the ephemeral follow-up.")
    outputs = _promote(run_dir, artifact_root, result["animation"])
    result["artifacts"] = outputs
    result["initial_render"]["path"] = "preview_initial.png"
    result["followup_render"]["path"] = "preview_followup.png"
    result["polished_render"]["path"] = "preview_polished.png"
    result["checkpoint"]["path"] = "sol_demo.blend"
    result["animation"]["path"] = outputs["animation"]
    for call in result.get("codex_followup", {}).get("tool_calls", []):
        if call.get("tool") == "blender_render" and isinstance(call.get("arguments"), dict):
            call["arguments"]["path"] = "preview_followup.png"
    inspection = json.loads((run_dir / "scene_inspection.json").read_text(encoding="utf-8"))
    render_result = json.loads((run_dir / "render_result.json").read_text(encoding="utf-8"))
    render_result["initial"]["path"] = "preview_initial.png"
    render_result["followup"]["path"] = "preview_followup.png"
    render_result["polished"]["path"] = "preview_polished.png"
    render_result["animation"]["path"] = outputs["animation"]
    _write_json_atomic(artifact_root / "scene_inspection.json", inspection)
    _write_json_atomic(artifact_root / "render_result.json", render_result)
    _write_json_atomic(artifact_root / "demo_result.json", result)
    live_acceptance = {
        "status": "MANUAL_ACCEPTANCE_PENDING",
        "timeline_frame_range": [1, 72],
        "progressive_live_runner": True,
        "human_visible_timeline_confirmed": False,
        "snapshot_restore_available": True,
    }
    _write_json_atomic(artifact_root / "live_gui_acceptance.json", live_acceptance)
    manifest = {
        "status": result["status"],
        "unofficial_concept_demo": True,
        "artifacts": result["artifacts"],
        "mp4_packaging": result["mp4_packaging"],
        "snapshot_restore": result["snapshot_restore"],
        "polished_render": result["polished_render"],
        "stable_uuid_count": result["snapshot_restore"]["uuid_count"],
        "gui_timeline": live_acceptance["status"],
        "safety": result["safety"],
    }
    _write_json_atomic(artifact_root / "final_demo_manifest.json", manifest)
    shutil.rmtree(run_dir)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the unofficial Codex3D Sol-inspired kinetic concept through structured MCP tools.")
    parser.add_argument("--isolated", action="store_true", help="Launch a factory-default headless Blender process.")
    parser.add_argument("--blender", default=str(BLENDER))
    parser.add_argument("--artifact-root", default=str(ARTIFACT_ROOT))
    parser.add_argument("--replace-demo-collection", action="store_true")
    parser.add_argument("--pause", type=float, default=0.0, help="Pause between stages for a live GUI presentation.")
    parser.add_argument("--render-live", action="store_true", help="Render and save when connected to an existing GUI scene.")
    parser.add_argument("--skip-codex", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = run_demo(args)
    except Exception as exc:
        print(f"Sol scene demo failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] in {"DONE", "MANUAL_ACCEPTANCE_PENDING"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
