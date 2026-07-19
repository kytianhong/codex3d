import zipfile
import subprocess
import sys

from scripts.build_blender_extension import build_extension, validate_extension_zip


def test_extension_zip_has_required_root_files_and_vendored_protocol(tmp_path) -> None:
    output = build_extension(tmp_path / "codex3d.zip")
    names = validate_extension_zip(output)

    assert "__init__.py" in names
    assert "blender_manifest.toml" in names
    assert "vendor/__init__.py" in names
    assert "vendor/codex3d_protocol/bridge.py" in names


def test_extension_zip_excludes_tests_caches_and_absolute_paths(tmp_path) -> None:
    output = build_extension(tmp_path / "codex3d.zip")
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        combined = b"".join(archive.read(name) for name in names)

    assert not any("tests" in name or "__pycache__" in name or name.endswith(".pyc") for name in names)
    assert b"/Users/kytianhong/CodeProject/Codex3D" not in combined


def test_extension_build_is_deterministic(tmp_path) -> None:
    first = build_extension(tmp_path / "first.zip")
    second = build_extension(tmp_path / "second.zip")

    assert first.read_bytes() == second.read_bytes()


def test_manifest_declares_local_bridge_permissions(tmp_path) -> None:
    output = build_extension(tmp_path / "codex3d.zip")
    with zipfile.ZipFile(output) as archive:
        manifest = archive.read("blender_manifest.toml").decode()

    assert 'network = "Accept structured actions from localhost"' in manifest
    assert 'clipboard = "Copy localhost connection details"' in manifest
    assert 'blender_version_min = "4.2.0"' in manifest


def test_extracted_extension_imports_without_workspace_pythonpath(tmp_path) -> None:
    output = build_extension(tmp_path / "codex3d.zip")
    package = tmp_path / "installed" / "codex3d_blender_connector"
    package.mkdir(parents=True)
    with zipfile.ZipFile(output) as archive:
        archive.extractall(package)
    command = (
        "import sys; "
        f"sys.path.insert(0, {str(package.parent)!r}); "
        "import codex3d_blender_connector as addon; "
        "assert addon.CONNECTOR_NAME == 'Codex3D Blender Connector'"
    )

    completed = subprocess.run(
        [sys.executable, "-I", "-c", command],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
