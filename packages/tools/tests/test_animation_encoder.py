from __future__ import annotations

import os
from pathlib import Path
import struct
import subprocess

import pytest

from codex3d_tools import AnimationEncoder, EncoderError, find_ffmpeg


def _png(path: Path, width: int = 64, height: int = 32) -> None:
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", width, height))


def _fake_ffmpeg(path: Path) -> None:
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(0o755)


def test_encoder_uses_safe_argv_and_reports_metadata(tmp_path: Path) -> None:
    frames = tmp_path / "frames"
    frames.mkdir()
    for number in range(1, 4):
        _png(frames / f"frame_{number:04d}.png")
    binary = tmp_path / "ffmpeg"
    _fake_ffmpeg(binary)
    seen: dict[str, object] = {}

    def runner(command, **kwargs):
        seen["command"] = command
        seen["kwargs"] = kwargs
        Path(command[-1]).write_bytes(b"FAKE_MP4")
        return subprocess.CompletedProcess(command, 0, "", "")

    result = AnimationEncoder(tmp_path, ffmpeg_path=binary, runner=runner).encode("frames", "movie.mp4")
    assert result["frame_count"] == 3
    assert result["duration_seconds"] == 0.125
    assert result["width"] == 64 and result["height"] == 32
    assert result["codec"] == "h264"
    assert seen["kwargs"]["shell"] is False
    assert seen["command"][-1] == str(tmp_path / "movie.mp4")


def test_encoder_rejects_escape_and_frame_gaps(tmp_path: Path) -> None:
    binary = tmp_path / "ffmpeg"
    _fake_ffmpeg(binary)
    encoder = AnimationEncoder(tmp_path, ffmpeg_path=binary)
    with pytest.raises(EncoderError, match="inside"):
        encoder.encode(tmp_path.parent, "movie.mp4")

    frames = tmp_path / "frames"
    frames.mkdir()
    _png(frames / "frame_0001.png")
    _png(frames / "frame_0003.png")
    with pytest.raises(EncoderError, match="continuous"):
        encoder.encode("frames", "movie.mp4")


def test_ffmpeg_path_must_be_explicitly_trusted_executable(tmp_path: Path) -> None:
    wrong = tmp_path / "encoder"
    wrong.write_text("", encoding="utf-8")
    wrong.chmod(0o755)
    with pytest.raises(EncoderError, match="ffmpeg"):
        find_ffmpeg(str(wrong))

    missing = tmp_path / "ffmpeg"
    with pytest.raises(EncoderError, match="unavailable"):
        find_ffmpeg(str(missing))
