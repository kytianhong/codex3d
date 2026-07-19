from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from codex3d_tools import AnimationEncoder, EncoderError


def _trusted_ffprobe(ffmpeg_path: Path, configured: str | None) -> Path:
    candidate = Path(configured).expanduser().resolve() if configured else ffmpeg_path.with_name("ffprobe")
    if candidate.name not in {"ffprobe", "ffprobe.exe"} or not candidate.is_file() or not os.access(candidate, os.X_OK):
        raise EncoderError("A trusted ffprobe executable next to ffmpeg or supplied by --ffprobe is required.")
    return candidate


def _probe_video(ffmpeg_path: Path, ffprobe_path: Path, video_path: Path) -> dict[str, object]:
    probe = subprocess.run(
        [
            str(ffprobe_path),
            "-v",
            "error",
            "-count_frames",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name,pix_fmt,width,height,avg_frame_rate,nb_frames,nb_read_frames,duration",
            "-show_entries",
            "format=duration,size,format_name",
            "-of",
            "json",
            str(video_path),
        ],
        check=False,
        capture_output=True,
        text=True,
        shell=False,
    )
    if probe.returncode != 0:
        raise EncoderError(f"ffprobe failed: {(probe.stderr or 'unknown error').strip()[-500:]}")
    payload = json.loads(probe.stdout)
    streams = payload.get("streams", [])
    if len(streams) != 1:
        raise EncoderError("MP4 must contain exactly one selected video stream.")
    stream = streams[0]
    format_data = payload.get("format", {})
    verified = {
        "codec": stream.get("codec_name"),
        "pixel_format": stream.get("pix_fmt"),
        "width": int(stream.get("width", 0)),
        "height": int(stream.get("height", 0)),
        "avg_frame_rate": stream.get("avg_frame_rate"),
        "frame_count": int(stream.get("nb_frames") or stream.get("nb_read_frames") or 0),
        "decoded_frame_count": int(stream.get("nb_read_frames") or 0),
        "duration_seconds": float(format_data.get("duration", stream.get("duration", 0))),
        "file_size": int(format_data.get("size", 0)),
        "format_name": format_data.get("format_name"),
    }
    expected = (
        verified["codec"] == "h264",
        verified["pixel_format"] == "yuv420p",
        verified["width"] == 512,
        verified["height"] == 512,
        verified["avg_frame_rate"] == "24/1",
        verified["frame_count"] == 72,
        verified["decoded_frame_count"] == 72,
        abs(float(verified["duration_seconds"]) - 3.0) < 0.01,
        verified["file_size"] > 0,
    )
    if not all(expected):
        raise EncoderError(f"ffprobe metadata did not match the Sprint 02D contract: {verified}")

    decode = subprocess.run(
        [str(ffmpeg_path), "-v", "error", "-i", str(video_path), "-f", "null", "-"],
        check=False,
        capture_output=True,
        text=True,
        shell=False,
    )
    if decode.returncode != 0:
        raise EncoderError(f"Full MP4 decode failed: {(decode.stderr or 'unknown error').strip()[-500:]}")
    verified["full_decode"] = "PASSED"
    return verified


def _update_manifest(artifact_root: Path, result: dict[str, object], probe: dict[str, object], ffmpeg: Path, ffprobe: Path) -> None:
    manifest_path = artifact_root / "final_demo_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    manifest.setdefault("artifacts", {})["animation_mp4"] = "sol_animation.mp4"
    manifest["mp4_packaging"] = {
        "status": "PASSED",
        "source": "Homebrew official ffmpeg formula",
        "ffmpeg_path": str(ffmpeg),
        "ffprobe_path": str(ffprobe),
        **result,
        "ffprobe": probe,
    }
    manifest["status"] = "DONE" if manifest.get("gui_timeline") == "PASSED" else "PARTIAL"
    temporary = manifest_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, manifest_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Package Codex3D PNG frames as a controlled H.264 MP4.")
    parser.add_argument("--artifact-root", default="artifacts/hackathon_sol_demo")
    parser.add_argument("--frames", default="frames")
    parser.add_argument("--output", default="sol_animation.mp4")
    parser.add_argument("--ffmpeg")
    parser.add_argument("--ffprobe")
    parser.add_argument("--fps", type=int, default=24)
    args = parser.parse_args()
    try:
        encoder = AnimationEncoder(
            Path(args.artifact_root),
            ffmpeg_path=args.ffmpeg,
        )
        result = encoder.encode(args.frames, args.output, fps=args.fps)
        if encoder.ffmpeg_path is None:
            raise EncoderError("ffmpeg resolution failed.")
        ffprobe = _trusted_ffprobe(encoder.ffmpeg_path, args.ffprobe)
        artifact_root = Path(args.artifact_root).resolve()
        probe = _probe_video(encoder.ffmpeg_path, ffprobe, artifact_root / args.output)
        _update_manifest(artifact_root, result, probe, encoder.ffmpeg_path, ffprobe)
    except EncoderError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 2
    print(json.dumps({"ok": True, "result": result, "ffprobe": probe}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
