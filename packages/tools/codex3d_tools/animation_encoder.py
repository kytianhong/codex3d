from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
from typing import Callable, Sequence


class EncoderError(ValueError):
    pass


@dataclass(frozen=True)
class FrameSequence:
    directory: Path
    pattern: str
    first_number: int
    frame_count: int
    width: int
    height: int


def find_ffmpeg(configured_path: str | None = None) -> Path | None:
    candidate = configured_path or os.environ.get("CODEX3D_FFMPEG_PATH") or shutil.which("ffmpeg")
    if not candidate:
        return None
    resolved = Path(candidate).expanduser().resolve()
    if resolved.name not in {"ffmpeg", "ffmpeg.exe"}:
        raise EncoderError("Configured encoder must resolve to an ffmpeg executable.")
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise EncoderError("Configured ffmpeg executable is unavailable or not executable.")
    return resolved


class AnimationEncoder:
    def __init__(
        self,
        artifact_root: str | Path,
        *,
        ffmpeg_path: str | Path | None = None,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self.artifact_root = Path(artifact_root).expanduser().resolve()
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_path = find_ffmpeg(str(ffmpeg_path) if ffmpeg_path else None)
        self._runner = runner

    def encode(
        self,
        frames_directory: str | Path,
        output_path: str | Path,
        *,
        fps: int = 24,
    ) -> dict[str, object]:
        if self.ffmpeg_path is None:
            raise EncoderError(
                "ffmpeg is unavailable. Install it separately or set CODEX3D_FFMPEG_PATH to a trusted executable."
            )
        if not isinstance(fps, int) or isinstance(fps, bool) or not 1 <= fps <= 120:
            raise EncoderError("fps must be an integer in [1, 120].")

        frames_path = self._inside_root(frames_directory, must_exist=True)
        output = self._inside_root(output_path, must_exist=False)
        if output.suffix.lower() != ".mp4":
            raise EncoderError("Animation output must use the .mp4 extension.")
        output.parent.mkdir(parents=True, exist_ok=True)
        sequence = self._inspect_sequence(frames_path)

        command: Sequence[str] = (
            str(self.ffmpeg_path),
            "-y",
            "-framerate",
            str(fps),
            "-start_number",
            str(sequence.first_number),
            "-i",
            str(sequence.directory / sequence.pattern),
            "-frames:v",
            str(sequence.frame_count),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output),
        )
        completed = self._runner(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            shell=False,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "ffmpeg failed").strip()
            raise EncoderError(f"ffmpeg failed with exit code {completed.returncode}: {detail[-500:]}")
        if not output.is_file() or output.stat().st_size == 0:
            raise EncoderError("ffmpeg returned success without producing a non-empty MP4.")

        return {
            "path": output.relative_to(self.artifact_root).as_posix(),
            "mime": "video/mp4",
            "codec": "h264",
            "pixel_format": "yuv420p",
            "fps": fps,
            "frame_count": sequence.frame_count,
            "duration_seconds": sequence.frame_count / fps,
            "width": sequence.width,
            "height": sequence.height,
            "file_size": output.stat().st_size,
            "sha256": _sha256(output),
            "faststart": True,
        }

    def _inside_root(self, value: str | Path, *, must_exist: bool) -> Path:
        raw = Path(value)
        candidate = raw.resolve() if raw.is_absolute() else (self.artifact_root / raw).resolve()
        try:
            candidate.relative_to(self.artifact_root)
        except ValueError as exc:
            raise EncoderError("Path must stay inside the configured artifact root.") from exc
        if must_exist and not candidate.is_dir():
            raise EncoderError("Frame input must be an existing directory inside the artifact root.")
        return candidate

    def _inspect_sequence(self, directory: Path) -> FrameSequence:
        expression = re.compile(r"^frame_(\d+)\.png$")
        numbered: list[tuple[int, Path]] = []
        for path in directory.iterdir():
            match = expression.match(path.name)
            if match:
                numbered.append((int(match.group(1)), path))
        numbered.sort()
        if not numbered:
            raise EncoderError("No frame_####.png files were found.")
        expected = list(range(numbered[0][0], numbered[0][0] + len(numbered)))
        actual = [number for number, _ in numbered]
        if actual != expected:
            raise EncoderError("PNG frame numbers must be continuous with no gaps or duplicates.")
        widths = {len(path.stem.removeprefix("frame_")) for _, path in numbered}
        if len(widths) != 1:
            raise EncoderError("PNG frame numbers must use a consistent zero-padded width.")
        width, height = _png_dimensions(numbered[0][1])
        return FrameSequence(
            directory=directory,
            pattern=f"frame_%0{widths.pop()}d.png",
            first_number=numbered[0][0],
            frame_count=len(numbered),
            width=width,
            height=height,
        )


def _png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise EncoderError(f"Invalid PNG frame: {path.name}")
    return struct.unpack(">II", header[16:24])


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
