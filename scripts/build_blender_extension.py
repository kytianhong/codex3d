from __future__ import annotations

import argparse
import shutil
import tempfile
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONNECTOR_SOURCE = PROJECT_ROOT / "connectors" / "blender_addon" / "codex3d_blender_connector"
PROTOCOL_SOURCE = PROJECT_ROOT / "packages" / "protocol" / "codex3d_protocol"
MANIFEST_SOURCE = PROJECT_ROOT / "connectors" / "blender_addon" / "extension" / "blender_manifest.toml"
DEFAULT_OUTPUT = PROJECT_ROOT / "dist" / "codex3d_blender_connector-0.1.0.zip"
REQUIRED_FILES = {"__init__.py", "blender_manifest.toml"}


def build_extension(output_path: Path = DEFAULT_OUTPUT) -> Path:
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="codex3d_extension_") as temporary:
        staging = Path(temporary)
        _copy_python_tree(CONNECTOR_SOURCE, staging)
        shutil.copy2(MANIFEST_SOURCE, staging / "blender_manifest.toml")
        vendor = staging / "vendor"
        vendor.mkdir()
        (vendor / "__init__.py").write_text("\"\"\"Vendored runtime dependencies.\"\"\"\n", encoding="utf-8")
        _copy_python_tree(PROTOCOL_SOURCE, vendor / "codex3d_protocol")
        _write_deterministic_zip(staging, output_path)
    validate_extension_zip(output_path)
    return output_path


def validate_extension_zip(path: Path) -> list[str]:
    path = Path(path)
    with zipfile.ZipFile(path) as archive:
        names = sorted(archive.namelist())
        missing = REQUIRED_FILES.difference(names)
        if missing:
            raise ValueError(f"Extension ZIP is missing required files: {sorted(missing)}")
        if not any(name.startswith("vendor/codex3d_protocol/") for name in names):
            raise ValueError("Extension ZIP is missing the vendored protocol package.")
        forbidden = [
            name
            for name in names
            if "__pycache__" in name
            or name.endswith(".pyc")
            or "/tests/" in f"/{name}"
            or name.endswith(".DS_Store")
        ]
        if forbidden:
            raise ValueError(f"Extension ZIP contains excluded files: {forbidden}")
        project_path = str(PROJECT_ROOT).encode("utf-8")
        for name in names:
            if project_path in archive.read(name):
                raise ValueError(f"Extension ZIP leaks an absolute development path in {name}.")
    return names


def _copy_python_tree(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for path in sorted(source.rglob("*.py")):
        if "__pycache__" in path.parts or "tests" in path.parts:
            continue
        relative = path.relative_to(source)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def _write_deterministic_zip(source: Path, output_path: Path) -> None:
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(item for item in source.rglob("*") if item.is_file()):
            relative = path.relative_to(source).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the local Codex3D Blender Extension ZIP.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = build_extension(args.output)
    names = validate_extension_zip(output)
    print(f"Built {output}")
    print(f"Validated {len(names)} files including the extension manifest and vendored protocol.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
