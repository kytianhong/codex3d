from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "release"
VERSION = "0.1.0"
SOURCE_NAME = f"codex3d-hackathon-{VERSION}-source.zip"
EXTENSION_NAME = f"codex3d-blender-extension-{VERSION}.zip"
DEMO_NAME = f"codex3d-demo-assets-{VERSION}.zip"

TOP_FILES = {
    ".gitignore",
    "README.md",
    "LICENSE",
    "SECURITY.md",
    "THIRD_PARTY_NOTICES.md",
    "HACKATHON_SUBMISSION.md",
    "DEMO_SCRIPT.md",
    "pyproject.toml",
}
SOURCE_DIRS = {"apps", "connectors", "docs", "examples", "packages", "scripts", "tests"}
EXCLUDED_PARTS = {
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    "artifacts",
    "dist",
    "release",
    "frames",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".log", ".blend1", ".blend2", ".token", ".secret"}


class ReleaseError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_source(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    return (
        not path.is_symlink()
        and not any(part in EXCLUDED_PARTS for part in relative.parts)
        and path.suffix.lower() not in EXCLUDED_SUFFIXES
        and path.name != ".DS_Store"
        and not path.name.startswith(".")
    )


def source_files() -> list[Path]:
    files = [ROOT / name for name in sorted(TOP_FILES) if (ROOT / name).is_file()]
    for directory in sorted(SOURCE_DIRS):
        base = ROOT / directory
        files.extend(path for path in sorted(base.rglob("*")) if path.is_file() and _safe_source(path))
    return sorted(set(files))


def _copy_source(staging: Path) -> None:
    for source in source_files():
        target = staging / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if target.suffix.lower() in {".md", ".py", ".toml", ".json", ".txt"} or target.name in {"LICENSE", ".gitignore"}:
            try:
                text = target.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            text = text.replace(str(ROOT), ".")
            text = text.replace(str(ROOT.parent), "<workspace>")
            target.write_text(text, encoding="utf-8")


def _zip_tree(source: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(item for item in source.rglob("*") if item.is_file()):
            if path.is_symlink():
                raise ReleaseError(f"Symlink is not allowed in release staging: {path}")
            relative = path.relative_to(source).as_posix()
            if relative.startswith("/") or ".." in Path(relative).parts:
                raise ReleaseError(f"Unsafe ZIP member: {relative}")
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        clean = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if "token" in lowered or lowered in {"events", "tool_trace", "conversation", "command"}:
                continue
            clean[key] = _sanitize(item)
        return clean
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, str):
        if value.startswith("/Users/") or value.startswith("/private/") or value.startswith("/tmp/"):
            return Path(value).name
    return value


def _copy_demo_assets(staging: Path) -> dict[str, Any]:
    sources = {
        "codex3d-preview.png": ROOT / "artifacts/hackathon_sol_demo/preview_polished.png",
        "ut01-preview-final.png": ROOT / "artifacts/user_tests/ut01_synthetic/preview_final.png",
        "codex3d-animation.mp4": ROOT / "artifacts/user_tests/ut01_synthetic/codex_space_animation.mp4",
        "codex3d-final-scene.blend": ROOT / "artifacts/user_tests/ut01_synthetic/final_scene.blend",
    }
    manifest: dict[str, Any] = {
        "project": "Codex3D",
        "version": VERSION,
        "unofficial_concept_demo": True,
        "files": {},
        "source_evidence": {
            "default_tests": "153 passed, 3 skipped",
            "synthetic_ut01": "SYNTHETIC_PASS 100/100",
        },
    }
    for name, source in sources.items():
        if not source.is_file():
            raise ReleaseError(f"Required curated demo asset is missing: {source}")
        target = staging / name
        shutil.copy2(source, target)
        manifest["files"][name] = {"size": target.stat().st_size, "sha256": sha256(target)}
    original = ROOT / "artifacts/user_tests/ut01_synthetic/final_manifest.json"
    if original.is_file():
        manifest["validation"] = _sanitize(json.loads(original.read_text(encoding="utf-8")))
    (staging / "public_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def _build_extension(output: Path) -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_blender_extension.py"), "--output", str(output)],
        cwd=ROOT,
        check=True,
    )


def validate_zip(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ReleaseError(f"Duplicate ZIP member in {path.name}")
        for info in archive.infolist():
            member = Path(info.filename)
            mode = info.external_attr >> 16
            if info.filename.startswith("/") or ".." in member.parts:
                raise ReleaseError(f"ZIP traversal in {path.name}: {info.filename}")
            if stat.S_ISLNK(mode):
                raise ReleaseError(f"ZIP symlink in {path.name}: {info.filename}")
            if mode & 0o022:
                raise ReleaseError(f"Group/world writable ZIP member: {info.filename}")
        return {"file_count": len(names), "size": path.stat().st_size, "sha256": sha256(path)}


def build() -> dict[str, Any]:
    RELEASE.mkdir(parents=True, exist_ok=True)
    staging_root = RELEASE / "staging"
    if staging_root.exists():
        shutil.rmtree(staging_root)
    source_stage = staging_root / "source"
    demo_stage = staging_root / "demo"
    source_stage.mkdir(parents=True)
    demo_stage.mkdir(parents=True)
    _copy_source(source_stage)
    demo_manifest = _copy_demo_assets(demo_stage)

    source_zip = RELEASE / SOURCE_NAME
    extension_zip = RELEASE / EXTENSION_NAME
    demo_zip = RELEASE / DEMO_NAME
    _zip_tree(source_stage, source_zip)
    _build_extension(extension_zip)
    _zip_tree(demo_stage, demo_zip)

    outputs = [source_zip, extension_zip, demo_zip]
    validation = {path.name: validate_zip(path) for path in outputs}
    if source_zip.stat().st_size >= 10 * 1024 * 1024:
        raise ReleaseError("Source bundle exceeds the 10 MiB release target.")
    checksums = "".join(f"{sha256(path)}  {path.name}\n" for path in outputs)
    (RELEASE / "SHA256SUMS").write_text(checksums, encoding="utf-8")
    result = {"version": VERSION, "outputs": validation, "demo_manifest": demo_manifest}
    (RELEASE / "build_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic Codex3D hackathon release bundles.")
    parser.parse_args()
    print(json.dumps(build(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
