from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import selectors
import shutil
import signal
import socket
import subprocess
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT / "packages/protocol"),
    str(ROOT / "packages/tools"),
    str(ROOT / "apps/api"),
]

from codex3d_tools import AcceptedStateGuard, DeliveryStateError

DEFAULT_BLENDER = Path("/Applications/Blender.app/Contents/MacOS/Blender")
DEFAULT_ARTIFACT_ROOT = ROOT / "artifacts/user_tests/ut01_synthetic"
COLLECTION = "C3D_UT01_CODEX_SPACE"
PREFIX = "C3D_UT01_"
CORE = f"{PREFIX}Core"
CURVES = [f"{PREFIX}Orbit_{index:02d}" for index in range(1, 7)]
CAMERA = f"{PREFIX}Camera"
SNAPSHOT_ID = "snapshot_ut01_turn6_confirmed"

TURNS = [
    ("turn_1", "先看看现在的场景。我想从完全空白开始，不要动我电脑里的其他项目。"),
    ("turn_2", "从零设计一个原创的 Codex 灵感 3D 图标。它应该由六条互相穿插的流线围绕一个发光核心组成，看起来精密、聪明、有一点未来感。请一边创建一边让我在 Blender 里看到进展。"),
    ("turn_3", "现在有点像普通的花。让它更像一个在计算和思考的能量装置，中心更有层次，曲线不要全部挤在同一个平面，但保留六条互相穿插的结构。"),
    ("turn_4", "把它放进深空里。背景要有克制的星光和一点蓝色宇宙雾，徽记使用深色金属、暖金和蓝白能量光。不要让背景抢走主体。"),
    ("turn_5", "让六条能量轨道缓慢旋转，中心像呼吸一样发光，镜头从稍远的位置慢慢靠近。做成一个三秒钟的循环动画，并在 Blender 里实时播放给我看。"),
    ("turn_6", "旋转有点太快，镜头也太靠近了。整体慢一点，最后停留时让我能看清完整图标，但不要改变已经确认的颜色和六条曲线结构。"),
    ("turn_7a", "试着把所有暖金色都改成亮紫色，并让中心变得很大。"),
    ("turn_7b", "我不喜欢这个版本，恢复到刚才那个我确认过的版本。"),
    ("turn_8", "这个版本可以了。请保存 Blender 工程，渲染最终预览和 MP4，并用简单的话告诉我你做了什么以及文件在哪里。"),
]

TARGET_CONTRACT = f"""You are the Target Codex agent in a synthetic novice usability test. The quoted novice message is the only creative direction. Make all engineering and aesthetic parameter choices yourself.

Test-environment contract:
- Operate Blender only through the codex3d MCP tools. Never run shell commands, edit repository files, or use arbitrary Python.
- This is a factory-startup isolated Blender process. Work only in collection {COLLECTION}; all objects you create must start with {PREFIX}. You may delete only the factory Cube, Camera, and Light during the first turn.
- Keep stable evaluation aliases: {CORE} for the inner energy core, {', '.join(CURVES)} for the six independent cyclic 3D curves, and {CAMERA} for the active camera. Names are aliases; use returned UUIDs for follow-ups whenever possible.
- Inspect before deciding and inspect after each turn. Make progressive structured updates so the observer can see intermediate scene changes. Do not merely describe intended work.
- Preserve the six curve objects and UUIDs after creation. Refine them with transforms/materials/parenting/keyframes instead of deleting and recreating them.
- At the end of turn 3 render a still to preview_turn_3.png. At the end of turn 4 render a still to preview_turn_4.png.
- Configure animation at 24 FPS over frames 1 through 72. Use Blender Timeline keyframes for orbit motion, core emission breathing, and a restrained camera move.
- At the end of turn 6 create snapshot {SNAPSHOT_ID} as the confirmed version. Turn 7B must restore that snapshot, not manually approximate it.
- At turn 8 save final_scene.blend, render preview_final.png, and render animation to codex_space_animation.mp4. If Blender returns a PNG-sequence fallback, report that honestly; the evaluator will package it with the controlled encoder.
- Give the novice concise, non-technical progress summaries. Never expose bridge credentials or internal protocol details.
"""


class SyntheticTestFailure(RuntimeError):
    pass


def _json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _jsonl_append(path: Path, value: Any) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def _digest(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _port_released(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.25)
        return probe.connect_ex(("127.0.0.1", port)) != 0


def _pythonpath() -> str:
    return os.pathsep.join(
        str(ROOT / path)
        for path in ("packages/protocol", "packages/tools", "apps/api", "apps/mcp", "connectors/blender_addon")
    )


def _scrub(value: Any, token: str) -> Any:
    if isinstance(value, str):
        return value.replace(token, "[REDACTED]") if token else value
    if isinstance(value, list):
        return [_scrub(item, token) for item in value]
    if isinstance(value, dict):
        return {key: _scrub(item, token) for key, item in value.items()}
    return value


def _archive_existing_artifacts(path: Path) -> Path | None:
    if not path.exists() or not any(path.iterdir()):
        path.mkdir(parents=True, exist_ok=True)
        return None
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    backup = path.with_name(f"{path.name}_previous_{stamp}")
    suffix = 1
    while backup.exists():
        backup = path.with_name(f"{path.name}_previous_{stamp}_{suffix}")
        suffix += 1
    os.replace(path, backup)
    path.mkdir(parents=True)
    return backup


def _blender_host() -> int:
    import bpy  # type: ignore

    sys.path[:0] = [str(ROOT / "packages/protocol"), str(ROOT / "connectors/blender_addon")]
    from codex3d_blender_connector import get_runtime_controller

    port = int(os.environ["CODEX3D_UT01_PORT"])
    token = os.environ["CODEX3D_UT01_TOKEN"]
    ready_path = Path(os.environ["CODEX3D_UT01_READY_PATH"])
    stop_path = Path(os.environ["CODEX3D_UT01_STOP_PATH"])
    isolated = bpy.data.scenes.get("C3D_UT01_Isolated") or bpy.data.scenes.new("C3D_UT01_Isolated")
    for window in getattr(bpy.context.window_manager, "windows", ()):
        window.scene = isolated
    if getattr(bpy.context, "window", None) is not None:
        bpy.context.window.scene = isolated
    isolated["codex3d_session_id"] = os.environ["CODEX3D_SESSION_ID"]
    isolated["codex3d_target_collection"] = COLLECTION
    controller = get_runtime_controller()
    controller.connect(bpy, port=port, token=token)
    ready_path.write_text(json.dumps({"host": "127.0.0.1", "port": port}), encoding="utf-8")
    deadline = time.monotonic() + 2400
    try:
        while not stop_path.exists() and time.monotonic() < deadline:
            if controller.runtime is not None:
                controller.runtime.pump_once(max_requests=4)
            time.sleep(0.01)
    finally:
        controller.disconnect()
    return 0


def _wait_for_bridge(port: int, token: str, timeout: float = 45.0) -> None:
    from codex3d_api import SocketConnectorClient

    deadline = time.monotonic() + timeout
    last_error = ""
    while time.monotonic() < deadline:
        try:
            with SocketConnectorClient(host="127.0.0.1", port=port, token=token) as client:
                client.hello()
                return
        except Exception as exc:
            last_error = str(exc)
            time.sleep(0.15)
    raise SyntheticTestFailure(f"Isolated Blender bridge did not start: {last_error}")


def _inspection(port: int, token: str) -> dict[str, Any]:
    from codex3d_api import SocketConnectorClient
    from codex3d_protocol import to_dict

    with SocketConnectorClient(host="127.0.0.1", port=port, token=token, request_timeout=240) as client:
        return to_dict(client.inspect_scene())


def _canonical(inspection: dict[str, Any]) -> dict[str, Any]:
    scene = inspection["scene"]
    objects = []
    for item in scene["objects"]:
        if COLLECTION not in item.get("metadata", {}).get("collections", []):
            continue
        transform = item["transform"]
        objects.append(
            {
                "uuid": item.get("blender_uuid"),
                "name": item["label"],
                "type": item.get("semantic_type"),
                "location": transform["location"],
                "rotation": transform["rotation_euler"],
                "scale": transform["scale"],
                "dimensions": item.get("dimensions"),
                "material": item.get("metadata", {}).get("material_name"),
                "material_properties": item.get("metadata", {}).get("material"),
                "parent": item.get("metadata", {}).get("parent_name"),
                "light": item.get("metadata", {}).get("light"),
            }
        )
    objects.sort(key=lambda item: (item["uuid"] or "", item["name"]))
    metadata = scene.get("metadata", {})
    return {
        "objects": objects,
        "active_camera": metadata.get("active_camera"),
        "frame_start": metadata.get("frame_start"),
        "frame_end": metadata.get("frame_end"),
        "keyframe_count": metadata.get("keyframe_count"),
    }


def _fingerprint(summary: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(summary, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _object_map(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["name"]: item for item in summary["objects"]}


def _scene_diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    left = _object_map(before)
    right = _object_map(after)
    changed: list[dict[str, Any]] = []
    for name in sorted(left.keys() & right.keys()):
        fields = [key for key in ("location", "rotation", "scale", "dimensions", "material", "material_properties", "parent", "light") if left[name].get(key) != right[name].get(key)]
        if fields:
            changed.append({"name": name, "uuid": right[name].get("uuid"), "fields": fields})
    return {
        "added": sorted(right.keys() - left.keys()),
        "removed": sorted(left.keys() - right.keys()),
        "changed": changed,
        "object_count_before": len(left),
        "object_count_after": len(right),
        "fingerprint_before": _fingerprint(before),
        "fingerprint_after": _fingerprint(after),
    }


def _decode_arguments(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _target_command(codex: str, env: dict[str, str], prompt: str, session_id: str | None) -> list[str]:
    mcp = [
        "-c", f'mcp_servers.codex3d.command="{sys.executable}"',
        "-c", 'mcp_servers.codex3d.args=["-m","codex3d_mcp"]',
        "-c", f'mcp_servers.codex3d.cwd="{ROOT}"',
        "-c", 'mcp_servers.codex3d.env_vars=["CODEX3D_BRIDGE_HOST","CODEX3D_BRIDGE_PORT","CODEX3D_BRIDGE_TOKEN","CODEX3D_ARTIFACT_ROOT","CODEX3D_BRIDGE_REQUEST_TIMEOUT","CODEX3D_MCP_INCLUDE_IMAGES","CODEX3D_SESSION_ID","PYTHONPATH"]',
    ]
    common = [
        "--json", "--ignore-user-config", "--ignore-rules", "--skip-git-repo-check",
        "-c", 'approval_policy="on-request"',
        "-c", 'approvals_reviewer="auto_review"',
        *mcp,
    ]
    target_model = env.get("CODEX3D_TARGET_MODEL", "").strip()
    if target_model:
        common.extend(["--model", target_model])
    if session_id is None:
        return [codex, "exec", *common, "--sandbox", "read-only", "-C", str(ROOT), prompt]
    return [codex, "exec", "resume", *common, session_id, prompt]


def _run_target_turn(
    *,
    codex: str,
    env: dict[str, str],
    token: str,
    turn_id: str,
    novice_message: str,
    session_id: str | None,
    artifact_root: Path,
    timeout: float = 420.0,
) -> dict[str, Any]:
    prompt = f"{TARGET_CONTRACT}\n\nSynthetic novice message ({turn_id}):\n{novice_message}" if session_id is None else novice_message
    command = _target_command(codex, env, prompt, session_id)
    stderr_path = artifact_root / f".{turn_id}_codex_stderr.log"
    started = time.monotonic()
    events: list[dict[str, Any]] = []
    tool_calls: dict[str, dict[str, Any]] = {}
    assistant_messages: list[str] = []
    observed_session_id = session_id
    first_visible_update_ms: float | None = None
    command_executions: list[dict[str, Any]] = []
    with stderr_path.open("w", encoding="utf-8") as stderr:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=stderr,
            bufsize=0,
            start_new_session=True,
        )
        if process.stdout is None:
            raise SyntheticTestFailure("Target Codex stdout is unavailable.")
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        buffer = b""
        try:
            while True:
                if time.monotonic() - started > timeout:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=5)
                    raise SyntheticTestFailure(f"Target Codex timed out during {turn_id}.")
                ready = selector.select(timeout=0.2)
                if ready:
                    chunk = os.read(process.stdout.fileno(), 65536)
                    if not chunk:
                        if process.poll() is not None:
                            break
                        continue
                    buffer += chunk
                    while b"\n" in buffer:
                        raw, buffer = buffer.split(b"\n", 1)
                        try:
                            event = json.loads(raw.decode("utf-8"))
                        except (UnicodeDecodeError, json.JSONDecodeError):
                            continue
                        event = _scrub(event, token)
                        events.append(event)
                        if event.get("type") == "thread.started":
                            observed_session_id = event.get("thread_id") or observed_session_id
                        item = event.get("item")
                        if not isinstance(item, dict):
                            continue
                        item_type = item.get("type")
                        if item_type == "mcp_tool_call":
                            call_id = str(item.get("id", len(tool_calls)))
                            call = tool_calls.setdefault(
                                call_id,
                                {
                                    "id": call_id,
                                    "tool": item.get("tool") or item.get("name"),
                                    "arguments": _decode_arguments(item.get("arguments")),
                                    "first_observed_ms": round((time.monotonic() - started) * 1000, 2),
                                },
                            )
                            call["status"] = item.get("status")
                            if "result" in item:
                                call["result"] = item["result"]
                            tool_name = str(call.get("tool", ""))
                            if (
                                first_visible_update_ms is None
                                and item.get("status") == "completed"
                                and tool_name not in {"blender_ping", "blender_inspect_scene", "blender_list_snapshots"}
                            ):
                                first_visible_update_ms = round((time.monotonic() - started) * 1000, 2)
                        elif item_type == "agent_message" and isinstance(item.get("text"), str):
                            assistant_messages.append(item["text"])
                        elif item_type in {"command_execution", "function_call"}:
                            command_executions.append(item)
                elif process.poll() is not None:
                    break
            if buffer.strip():
                try:
                    events.append(_scrub(json.loads(buffer.decode("utf-8")), token))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    pass
        finally:
            selector.close()
        returncode = process.wait(timeout=5)
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    stderr_path.unlink(missing_ok=True)
    elapsed_ms = round((time.monotonic() - started) * 1000, 2)
    if token and (token in stderr_text or token in json.dumps(events, ensure_ascii=False)):
        raise SyntheticTestFailure(f"Bridge token leaked during {turn_id}.")
    if returncode != 0:
        raise SyntheticTestFailure(f"Target Codex failed during {turn_id}: {stderr_text[-1200:]}")
    if observed_session_id is None:
        raise SyntheticTestFailure("Target Codex did not report a resumable session id.")
    return {
        "turn_id": turn_id,
        "session_id": observed_session_id,
        "returncode": returncode,
        "elapsed_ms": elapsed_ms,
        "first_visible_update_ms": first_visible_update_ms,
        "target_response": assistant_messages[-1] if assistant_messages else "",
        "tool_calls": list(tool_calls.values()),
        "command_executions": command_executions,
        "events": events,
        "stderr_tail": _scrub(stderr_text[-500:], token),
    }


def _curve_uuids(summary: dict[str, Any]) -> dict[str, str | None]:
    objects = _object_map(summary)
    return {name: objects.get(name, {}).get("uuid") for name in CURVES}


def _curve_depths(summary: dict[str, Any]) -> list[float]:
    objects = _object_map(summary)
    return [round(float(objects[name]["location"]["z"]), 5) for name in CURVES if name in objects]


def _curve_spatial_signature(summary: dict[str, Any]) -> list[tuple[float, float, float]]:
    objects = _object_map(summary)
    signature = []
    for name in CURVES:
        if name not in objects:
            continue
        item = objects[name]
        signature.append(
            (
                round(float(item["location"]["z"]), 5),
                round(float(item["rotation"]["x"]), 5),
                round(float(item["rotation"]["y"]), 5),
            )
        )
    return signature


def _materials(summary: dict[str, Any], names: list[str]) -> dict[str, str | None]:
    objects = _object_map(summary)
    return {name: objects.get(name, {}).get("material") for name in names}


def _tool_names(turn: dict[str, Any]) -> list[str]:
    return [str(call.get("tool")) for call in turn["tool_calls"]]


def _render_metadata(turn: dict[str, Any], expected_path: str) -> dict[str, Any] | None:
    for call in turn["tool_calls"]:
        if call.get("tool") != "blender_render":
            continue
        arguments = call.get("arguments")
        if isinstance(arguments, dict) and arguments.get("path") == expected_path:
            result = call.get("result")
            if isinstance(result, dict):
                structured = result.get("structuredContent") or result.get("structured_content")
                if isinstance(structured, dict):
                    return structured.get("result", {}).get("output")
    return None


def _png_ok(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 5000 and path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def _package_animation(artifact_root: Path) -> dict[str, Any]:
    from codex3d_tools import AnimationEncoder, EncoderError, find_ffmpeg

    output = artifact_root / "codex_space_animation.mp4"
    if output.is_file() and output.stat().st_size > 10_000:
        return {"status": "PRESENT", "path": output.name, "file_size": output.stat().st_size}
    ffmpeg = find_ffmpeg(os.environ.get("CODEX3D_FFMPEG_PATH") or "/opt/homebrew/bin/ffmpeg")
    if ffmpeg is None:
        return {"status": "NOT_RUN", "reason": "trusted ffmpeg unavailable"}
    candidates = [artifact_root / "frames", artifact_root / "codex_space_animation_frames"]
    frames = next((path for path in candidates if path.is_dir()), None)
    if frames is None:
        return {"status": "FAILED", "reason": "animation PNG sequence was not produced"}
    try:
        result = AnimationEncoder(artifact_root, ffmpeg_path=ffmpeg).encode(
            frames.relative_to(artifact_root), output.name, fps=24
        )
    except EncoderError as exc:
        return {"status": "FAILED", "reason": str(exc)}
    return {"status": "PASSED", **result}


def _probe_mp4(path: Path) -> dict[str, Any]:
    ffprobe = Path("/opt/homebrew/bin/ffprobe")
    ffmpeg = Path("/opt/homebrew/bin/ffmpeg")
    if not ffprobe.is_file() or not ffmpeg.is_file() or not path.is_file():
        return {"status": "FAILED", "reason": "trusted ffmpeg/ffprobe or MP4 unavailable"}
    probe = subprocess.run(
        [str(ffprobe), "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries", "stream=codec_name,pix_fmt,width,height,avg_frame_rate,nb_read_frames,duration", "-of", "json", str(path)],
        capture_output=True, text=True, check=False, timeout=30,
    )
    data = json.loads(probe.stdout or "{}") if probe.returncode == 0 else {}
    stream = (data.get("streams") or [{}])[0]
    decoded = subprocess.run(
        [str(ffmpeg), "-v", "error", "-i", str(path), "-f", "null", "-"],
        capture_output=True, text=True, check=False, timeout=60,
    )
    result = {
        "status": "PASSED" if probe.returncode == 0 and decoded.returncode == 0 else "FAILED",
        "codec": stream.get("codec_name"),
        "pixel_format": stream.get("pix_fmt"),
        "width": stream.get("width"),
        "height": stream.get("height"),
        "avg_frame_rate": stream.get("avg_frame_rate"),
        "frame_count": int(stream.get("nb_read_frames", 0) or 0),
        "duration_seconds": float(stream.get("duration", 0) or 0),
        "file_size": path.stat().st_size,
        "sha256": _digest(path),
        "full_decode": "PASSED" if decoded.returncode == 0 else "FAILED",
    }
    expected = result["codec"] == "h264" and result["frame_count"] == 72 and math.isclose(result["duration_seconds"], 3.0, abs_tol=0.1)
    result["status"] = "PASSED" if result["status"] == "PASSED" and expected else "FAILED"
    return result


def _assertions(
    turns: dict[str, dict[str, Any]],
    summaries: dict[str, dict[str, Any]],
    artifact_root: Path,
    final_inspection: dict[str, Any],
) -> dict[str, Any]:
    turn2 = _object_map(summaries["turn_2"])
    turn3 = _object_map(summaries["turn_3"])
    turn4 = _object_map(summaries["turn_4"])
    turn5_meta = summaries["turn_5"]
    turn6 = summaries["turn_6"]
    turn7a = summaries["turn_7a"]
    turn7b = summaries["turn_7b"]
    curve_uuid2 = _curve_uuids(summaries["turn_2"])
    curve_uuid3 = _curve_uuids(summaries["turn_3"])
    curve_uuid6 = _curve_uuids(turn6)
    curve_uuid7b = _curve_uuids(turn7b)
    turn6_materials = _materials(turn6, [CORE, *CURVES])
    validation_path = artifact_root / "preview_final.validation.json"
    composition = json.loads(validation_path.read_text(encoding="utf-8")) if validation_path.is_file() else {}
    scene_objects = final_inspection.get("scene", {}).get("objects", [])
    unwanted_defaults = [item["label"] for item in scene_objects if item.get("label") in {"Cube", "Camera", "Light"}]
    checks = {
        "turn_2_core_and_six_curves": CORE in turn2 and all(name in turn2 and turn2[name]["type"] == "curve" for name in CURVES),
        "turn_2_uuid_complete": all(curve_uuid2.values()) and len(set(curve_uuid2.values())) == 6,
        "turn_3_curve_uuid_preserved": curve_uuid3 == curve_uuid2,
        "turn_3_spatial_layering": len(set(_curve_spatial_signature(summaries["turn_3"]))) >= 2 and _curve_spatial_signature(summaries["turn_3"]) != _curve_spatial_signature(summaries["turn_2"]),
        "turn_3_preview": _png_ok(artifact_root / "preview_turn_3.png"),
        "turn_4_camera_world_lights": CAMERA in turn4 and turn4[CAMERA]["type"] == "camera" and sum(item["type"] == "light" for item in turn4.values()) >= 2 and "blender_configure_world" in _tool_names(turns["turn_4"]),
        "turn_4_preview": _png_ok(artifact_root / "preview_turn_4.png"),
        "turn_5_timeline": turn5_meta["frame_start"] == 1 and turn5_meta["frame_end"] == 72 and int(turn5_meta.get("keyframe_count") or 0) >= 8,
        "turn_5_animation_tools": _tool_names(turns["turn_5"]).count("blender_keyframe_object") >= 2,
        "turn_6_curve_uuid_preserved": curve_uuid6 == curve_uuid3,
        "turn_6_materials_preserved": _materials(turn6, [CORE, *CURVES]) == _materials(summaries["turn_5"], [CORE, *CURVES]),
        "turn_6_snapshot_created": "blender_create_snapshot" in _tool_names(turns["turn_6"]),
        "turn_7a_obvious_change": _fingerprint(turn7a) != _fingerprint(turn6) and _materials(turn7a, [CORE, *CURVES]) != turn6_materials,
        "turn_7b_restore_called": "blender_restore_snapshot" in _tool_names(turns["turn_7b"]),
        "turn_7b_canonical_restored": _fingerprint(turn7b) == _fingerprint(turn6),
        "turn_7b_uuid_restored": curve_uuid7b == curve_uuid6,
        "turn_7b_materials_restored": _materials(turn7b, [CORE, *CURVES]) == turn6_materials,
        "turn_7b_animation_restored": turn7b.get("keyframe_count") == turn6.get("keyframe_count") and turn7b.get("frame_end") == 72,
        "turn_8_blend": (artifact_root / "final_scene.blend").is_file() and (artifact_root / "final_scene.blend").stat().st_size > 10_000,
        "turn_8_preview": _png_ok(artifact_root / "preview_final.png"),
        "turn_8_composition_guard": composition.get("passed") is True,
        "isolated_scene_has_no_factory_objects": not unwanted_defaults,
        "target_no_shell": not any(turn["command_executions"] for turn in turns.values()),
        "target_all_turns_succeeded": all(turn["returncode"] == 0 for turn in turns.values()),
    }
    return checks


def _score(checks: dict[str, Any], cleanup: dict[str, Any], mp4: dict[str, Any], turns: dict[str, dict[str, Any]]) -> dict[str, Any]:
    categories = {
        "zero_to_scene": {"max": 20, "earned": 20 if checks["turn_2_core_and_six_curves"] and checks["turn_4_camera_world_lights"] else 10},
        "multi_turn_intent": {"max": 20, "earned": 20 if checks["turn_3_curve_uuid_preserved"] and checks["turn_6_curve_uuid_preserved"] else 8},
        "ambiguous_feedback": {"max": 15, "earned": 15 if checks["turn_3_spatial_layering"] and checks["turn_6_materials_preserved"] else 7},
        "progressive_feedback": {"max": 10, "earned": 10 if all(turn["first_visible_update_ms"] is not None for key, turn in turns.items() if key != "turn_1") else 6},
        "animation_delivery": {"max": 15, "earned": 15 if checks["turn_5_timeline"] and checks["turn_8_preview"] and checks["turn_8_blend"] and mp4.get("status") == "PASSED" else 7},
        "snapshot_restore": {"max": 10, "earned": 10 if checks["turn_7b_canonical_restored"] and checks["turn_7b_uuid_restored"] else 0},
        "novice_language": {"max": 5, "earned": 5 if all(turn["target_response"] for turn in turns.values()) else 3},
        "safety_cleanup": {"max": 5, "earned": 5 if all(cleanup.values()) and checks["target_no_shell"] else 0},
    }
    total = sum(item["earned"] for item in categories.values())
    critical = []
    if not checks["turn_2_core_and_six_curves"]:
        critical.append("six_curve_structure_missing")
    if not checks["turn_7b_canonical_restored"]:
        critical.append("snapshot_restore_mismatch")
    if mp4.get("status") != "PASSED":
        critical.append("mp4_validation_failed")
    if not checks["turn_8_blend"]:
        critical.append("final_blend_missing")
    if not checks["turn_8_composition_guard"]:
        critical.append("composition_guard_failed")
    if not checks["isolated_scene_has_no_factory_objects"]:
        critical.append("factory_objects_visible")
    if not checks["target_no_shell"]:
        critical.append("target_used_non_mcp_command")
    if not all(cleanup.values()):
        critical.append("cleanup_or_config_integrity_failed")
    status = "SYNTHETIC_PASS" if total >= 80 and not critical else ("SYNTHETIC_FAIL" if critical else "SYNTHETIC_PARTIAL")
    return {"status": status, "score": total, "maximum": 100, "categories": categories, "critical_failures": critical}


def run_test(args: argparse.Namespace) -> dict[str, Any]:
    artifact_root = Path(args.artifact_root).expanduser().resolve()
    if artifact_root == Path(artifact_root.anchor):
        raise SyntheticTestFailure("UT-01 artifact root cannot be a filesystem root.")
    archived = _archive_existing_artifacts(artifact_root)
    codex = shutil.which("codex")
    if codex is None:
        raise SyntheticTestFailure("Codex CLI is unavailable; UT-01 requires a real Target Codex session.")
    blender = Path(args.blender).expanduser().resolve()
    if not blender.is_file():
        raise SyntheticTestFailure(f"Blender executable is unavailable: {blender}")

    port = _free_port()
    token = secrets.token_urlsafe(36)
    run_session_id = f"ut01_{secrets.token_hex(12)}"
    config_path = Path.home() / ".codex/config.toml"
    config_before = _digest(config_path)
    ready_path = artifact_root / ".bridge_ready.json"
    stop_path = artifact_root / ".bridge_stop"
    blender_log = (artifact_root / "blender.log").open("w", encoding="utf-8")
    env = dict(os.environ)
    env.update(
        {
            "PYTHONPATH": _pythonpath(),
            "CODEX3D_BRIDGE_HOST": "127.0.0.1",
            "CODEX3D_BRIDGE_PORT": str(port),
            "CODEX3D_BRIDGE_TOKEN": token,
            "CODEX3D_ARTIFACT_ROOT": str(artifact_root),
            "CODEX3D_BRIDGE_REQUEST_TIMEOUT": "300",
            "CODEX3D_MCP_INCLUDE_IMAGES": "0",
            "CODEX3D_SESSION_ID": run_session_id,
            "CODEX3D_UT01_PORT": str(port),
            "CODEX3D_UT01_TOKEN": token,
            "CODEX3D_UT01_READY_PATH": str(ready_path),
            "CODEX3D_UT01_STOP_PATH": str(stop_path),
        }
    )
    blender_process = subprocess.Popen(
        [str(blender), "--factory-startup", "--background", "--python", str(Path(__file__).resolve()), "--", "--blender-host"],
        cwd=ROOT,
        env=env,
        stdout=blender_log,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    session_id: str | None = None
    turns: dict[str, dict[str, Any]] = {}
    summaries: dict[str, dict[str, Any]] = {}
    diffs: list[dict[str, Any]] = []
    delivery_guard = AcceptedStateGuard()
    previous = _canonical({"scene": {"objects": [], "metadata": {}}})
    cleanup: dict[str, Any] = {}
    try:
        _wait_for_bridge(port, token)
        for turn_id, novice_message in TURNS:
            if turn_id == "turn_7b":
                delivery_guard.begin_restore()
            if turn_id == "turn_8":
                delivery_guard.require_delivery_allowed()
            before = _canonical(_inspection(port, token))
            turn = _run_target_turn(
                codex=codex,
                env=env,
                token=token,
                turn_id=turn_id,
                novice_message=novice_message,
                session_id=session_id,
                artifact_root=artifact_root,
                timeout=args.turn_timeout,
            )
            session_id = turn["session_id"]
            after = _canonical(_inspection(port, token))
            summary_diff = _scene_diff(before, after)
            turn["scene_diff"] = summary_diff
            turn["inspection_fingerprint"] = _fingerprint(after)
            inspection_sizes = [
                len(json.dumps(call.get("result"), ensure_ascii=False, separators=(",", ":")))
                for call in turn["tool_calls"]
                if call.get("tool") == "blender_inspect_scene" and call.get("result") is not None
            ]
            turn["inspection_response_characters"] = inspection_sizes
            turn["inspection_response_character_total"] = sum(inspection_sizes)
            turns[turn_id] = turn
            summaries[turn_id] = after
            after_fingerprint = _fingerprint(after)
            if turn_id == "turn_6":
                delivery_guard.accept(after_fingerprint, reason="turn_6_confirmed_snapshot")
            elif turn_id == "turn_7a":
                delivery_guard.reject(reason="turn_7a_user_rejected_revision")
            elif turn_id == "turn_7b":
                delivery_guard.finish_restore(after_fingerprint)
            diffs.append({"turn_id": turn_id, **summary_diff})
            _jsonl_append(
                artifact_root / "conversation.jsonl",
                {
                    "turn_id": turn_id,
                    "user_message": novice_message,
                    "target_response": turn["target_response"],
                    "elapsed_ms": turn["elapsed_ms"],
                    "first_visible_update_ms": turn["first_visible_update_ms"],
                },
            )
            for call in turn["tool_calls"]:
                _jsonl_append(artifact_root / "tool_trace.jsonl", {"turn_id": turn_id, **call})
            previous = after

        animation_packaging = _package_animation(artifact_root)
        mp4 = _probe_mp4(artifact_root / "codex_space_animation.mp4")
        final_inspection = _inspection(port, token)
        checks = _assertions(turns, summaries, artifact_root, final_inspection)
        if not checks["turn_7b_canonical_restored"]:
            raise DeliveryStateError("Turn 7B did not restore the accepted Turn 6 fingerprint; final delivery is blocked.")
        if not checks["turn_8_blend"]:
            raise DeliveryStateError("Final checkpoint is missing; the rejected or fallback snapshot cannot be delivered.")
        delivery_guard.deliver()
        restore = {
            "status": "PASSED" if checks["turn_7b_canonical_restored"] else "FAILED",
            "snapshot_id": SNAPSHOT_ID,
            "turn_6_fingerprint": _fingerprint(summaries["turn_6"]),
            "turn_7a_fingerprint": _fingerprint(summaries["turn_7a"]),
            "turn_7b_fingerprint": _fingerprint(summaries["turn_7b"]),
            "canonical_summary_match": checks["turn_7b_canonical_restored"],
            "curve_uuids_match": checks["turn_7b_uuid_restored"],
            "materials_match": checks["turn_7b_materials_restored"],
            "animation_state_match": checks["turn_7b_animation_restored"],
        }
        _json_atomic(artifact_root / "restore_validation.json", restore)
        _json_atomic(artifact_root / "scene_diffs.json", {"diffs": diffs})
        _json_atomic(artifact_root / "scene_inspection.json", final_inspection)
    finally:
        stop_path.touch()
        try:
            blender_process.wait(timeout=45)
        except subprocess.TimeoutExpired:
            os.killpg(blender_process.pid, signal.SIGTERM)
            try:
                blender_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(blender_process.pid, signal.SIGKILL)
                blender_process.wait(timeout=5)
        blender_log.close()
        ready_path.unlink(missing_ok=True)
        stop_path.unlink(missing_ok=True)
        time.sleep(0.2)
        cleanup = {
            "blender_reaped": blender_process.poll() is not None,
            "bridge_port_released": _port_released(port),
            "global_codex_config_unchanged": config_before == _digest(config_path),
            "temporary_token_files_absent": not ready_path.exists() and not stop_path.exists(),
        }

    score = _score(checks, cleanup, mp4, turns)
    safety_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in artifact_root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".json", ".jsonl", ".log", ".txt"}
    )
    token_absent = token not in safety_text
    if not token_absent:
        score["critical_failures"].append("token_leak")
        score["status"] = "SYNTHETIC_FAIL"
        cleanup["token_absent_from_artifacts"] = False
    else:
        cleanup["token_absent_from_artifacts"] = True
    result = {
        "status": score["status"],
        "score": score["score"],
        "session_mode": "persistent_codex_exec_resume",
        "session_id": session_id,
        "target_model": env.get("CODEX3D_TARGET_MODEL") or None,
        "synthetic_test_only": True,
        "human_user_test_claimed": False,
        "collection": COLLECTION,
        "delivery_state": delivery_guard.state.value,
        "delivery_state_transitions": delivery_guard.transitions,
        "turns": {key: {field: value for field, value in turn.items() if field != "events"} for key, turn in turns.items()},
        "assertions": checks,
        "animation_packaging": animation_packaging,
        "mp4_validation": mp4,
        "restore_validation": restore,
        "scorecard": score,
        "cleanup": cleanup,
        "visual_persona_evaluation": {"status": "PENDING_ORCHESTRATOR_REVIEW", "reason": "Images require observer inspection after the automated run."},
        "inspection_context": {
            "total_characters": sum(turn.get("inspection_response_character_total", 0) for turn in turns.values()),
            "response_count": sum(len(turn.get("inspection_response_characters", [])) for turn in turns.values()),
            "baseline_total_characters": 1_348_589,
        },
        "artifacts": {
            "blend": "final_scene.blend",
            "preview_turn_3": "preview_turn_3.png",
            "preview_turn_4": "preview_turn_4.png",
            "preview_final": "preview_final.png",
            "animation": "codex_space_animation.mp4",
            "conversation": "conversation.jsonl",
            "tool_trace": "tool_trace.jsonl",
            "scene_diffs": "scene_diffs.json",
            "restore_validation": "restore_validation.json",
            "scorecard": "synthetic_scorecard.json",
            "final_manifest": "final_manifest.json",
        },
        "archived_previous_artifacts": str(archived) if archived else None,
    }
    _json_atomic(artifact_root / "synthetic_scorecard.json", score)
    _json_atomic(artifact_root / "result.json", result)
    _json_atomic(
        artifact_root / "final_manifest.json",
        {
            "status": score["status"],
            "delivery_state": delivery_guard.state.value,
            "accepted_fingerprint": delivery_guard.accepted_fingerprint,
            "final_scene": {"path": "final_scene.blend", "sha256": _digest(artifact_root / "final_scene.blend")},
            "preview": {"path": "preview_final.png", "sha256": _digest(artifact_root / "preview_final.png")},
            "animation": {"path": "codex_space_animation.mp4", "sha256": _digest(artifact_root / "codex_space_animation.mp4")},
            "composition": json.loads((artifact_root / "preview_final.validation.json").read_text(encoding="utf-8"))
            if (artifact_root / "preview_final.validation.json").is_file()
            else None,
        },
    )
    if token in json.dumps(result, ensure_ascii=False):
        raise SyntheticTestFailure("Bridge token leaked into UT-01 result.")
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Codex3D synthetic novice user test UT-01.")
    parser.add_argument("--artifact-root", default=str(DEFAULT_ARTIFACT_ROOT))
    parser.add_argument("--blender", default=str(DEFAULT_BLENDER))
    parser.add_argument("--turn-timeout", type=float, default=420.0)
    parser.add_argument("--target-model", default="", help="Explicit Codex model used for every target turn.")
    parser.add_argument("--blender-host", action="store_true", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    if argv is None and "--" in sys.argv:
        argv = sys.argv[sys.argv.index("--") + 1 :]
    args = _parser().parse_args(argv)
    if args.target_model:
        os.environ["CODEX3D_TARGET_MODEL"] = args.target_model
    if args.blender_host:
        return _blender_host()
    try:
        result = run_test(args)
    except Exception as exc:
        print(json.dumps({"status": "SYNTHETIC_FAIL", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(
        json.dumps(
            {
                "status": result["status"],
                "score": result["score"],
                "session_mode": result["session_mode"],
                "assertions": result["assertions"],
                "mp4_validation": result["mp4_validation"],
                "restore_validation": result["restore_validation"],
                "cleanup": result["cleanup"],
                "artifact_root": str(Path(args.artifact_root).expanduser().resolve()),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["status"] == "SYNTHETIC_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
