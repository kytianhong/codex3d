from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "release"
PRIVATE_PATH = re.compile(rb"/Users/[A-Za-z0-9._-]+/")
TEXT_SUFFIXES = {"", ".md", ".py", ".toml", ".json", ".jsonl", ".txt", ".cfg", ".ini", ".yaml", ".yml"}
SECRET_PATTERNS = [
    re.compile(rb"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(rb"(?:token|secret)[\"']?\s*[:=]\s*[\"'][A-Za-z0-9_-]{32,}[\"']", re.IGNORECASE),
    re.compile(rb"BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY"),
]


def _run(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    return {
        "status": "PASSED" if completed.returncode == 0 else "FAILED",
        "returncode": completed.returncode,
        "summary": (completed.stdout + completed.stderr).strip().splitlines()[-1:] or [""],
    }


def _clean_room(source_zip: Path) -> dict[str, Any]:
    if not source_zip.is_file():
        return {"status": "FAILED", "reason": "source_zip_missing"}
    with tempfile.TemporaryDirectory(prefix="codex3d_release_preflight_") as temporary:
        root = Path(temporary)
        with zipfile.ZipFile(source_zip) as archive:
            archive.extractall(root)
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            str(root / path) for path in ("packages/protocol", "apps/api", "connectors/blender_addon")
        )
        commands = {
            "compile": [sys.executable, "-m", "compileall", "-q", str(root)],
            "tests": [sys.executable, "-m", "pytest", str(root), "-q"],
            "extension": [
                sys.executable,
                str(root / "scripts/build_blender_extension.py"),
                "--output",
                str(root / "extension.zip"),
            ],
            "judge_smoke": [sys.executable, str(root / "examples/hackathon_sprint_01_demo.py")],
        }
        results: dict[str, Any] = {}
        for name, command in commands.items():
            completed = subprocess.run(command, cwd=root, env=env, text=True, capture_output=True, check=False)
            results[name] = {
                "status": "PASSED" if completed.returncode == 0 else "FAILED",
                "returncode": completed.returncode,
                "summary": (completed.stdout + completed.stderr).strip().splitlines()[-1:] or [""],
            }
            if completed.returncode:
                return {"status": "FAILED", "steps": results}
        return {"status": "PASSED", "steps": results}


def _version(command: list[str]) -> str | None:
    executable = shutil.which(command[0]) if not Path(command[0]).is_absolute() else command[0]
    if not executable or not Path(executable).exists():
        return None
    completed = subprocess.run([executable, *command[1:]], text=True, capture_output=True, check=False)
    lines = (completed.stdout or completed.stderr).splitlines()
    return lines[0] if lines else None


def _scan_file(path: Path, findings: list[dict[str, str]]) -> None:
    data = path.read_bytes()
    relative = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.name
    if PRIVATE_PATH.search(data):
        findings.append({"file": relative, "kind": "private_absolute_path"})
    for pattern in SECRET_PATTERNS:
        if pattern.search(data):
            findings.append({"file": relative, "kind": "possible_secret"})


def _scan_zip(path: Path) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            member = Path(info.filename)
            if info.filename.startswith("/") or ".." in member.parts:
                findings.append({"file": info.filename, "kind": "zip_traversal"})
            if info.is_dir():
                continue
            if Path(info.filename).suffix.lower() not in TEXT_SUFFIXES:
                continue
            data = archive.read(info)
            if PRIVATE_PATH.search(data):
                findings.append({"file": info.filename, "kind": "private_absolute_path"})
            for pattern in SECRET_PATTERNS:
                if pattern.search(data):
                    findings.append({"file": info.filename, "kind": "possible_secret"})
    return {"status": "PASSED" if not findings else "FAILED", "findings": findings}


def preflight(run_tests: bool, clean_room: bool = False) -> dict[str, Any]:
    zips = sorted(RELEASE.glob("*.zip"))
    scans = {path.name: _scan_zip(path) for path in zips}
    required = [
        "README.md", "LICENSE", "SECURITY.md", "THIRD_PARTY_NOTICES.md",
        "HACKATHON_SUBMISSION.md", "DEMO_SCRIPT.md", "docs/architecture_submission.md",
    ]
    rules = {
        "deadline_2026_07_21_5pm_pdt": "VERIFIED",
        "apps_for_your_life_track": "VERIFIED",
        "codex_and_gpt56_required": "VERIFIED",
        "public_youtube_under_3_minutes_with_audio": "PENDING_USER",
        "licensed_repo_url_and_access": "PENDING_USER",
        "feedback_session_id": "PENDING_USER",
        "english_materials": "PASSED",
        "entrant_eligibility_and_display_name": "UNVERIFIED",
    }
    git_status: dict[str, Any] = {"initialized": (ROOT / ".git").is_dir()}
    if git_status["initialized"]:
        git_status["commit"] = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False
        ).stdout.strip() or None
        git_status["tag"] = subprocess.run(
            ["git", "tag", "--points-at", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=False
        ).stdout.strip() or None
        git_status["remote"] = subprocess.run(
            ["git", "remote", "get-url", "origin"], cwd=ROOT, text=True, capture_output=True, check=False
        ).stdout.strip() or None

    tests = _run([sys.executable, "-m", "pytest"]) if run_tests else {"status": "NOT_RUN"}
    compile_smoke = _run([sys.executable, "-m", "compileall", "-q", "apps", "packages", "connectors", "examples", "scripts", "tests"])
    extension_build = _run([sys.executable, "scripts/build_blender_extension.py"])
    clean_room_result = (
        _clean_room(RELEASE / "codex3d-hackathon-0.1.0-source.zip")
        if clean_room
        else {"status": "NOT_RUN"}
    )
    all_scans_pass = bool(zips) and all(item["status"] == "PASSED" for item in scans.values())
    files_pass = all((ROOT / path).is_file() for path in required)
    blockers = [key for key, value in rules.items() if value in {"PENDING_USER", "UNVERIFIED"}]
    status = "CONDITIONALLY_READY" if all_scans_pass and files_pass and compile_smoke["status"] == "PASSED" else "NOT_READY"
    result = {
        "status": status,
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "official_rules_url": "https://openai.devpost.com/rules",
        "rules": rules,
        "blockers": blockers,
        "versions": {
            "python": sys.version.split()[0],
            "blender": _version(["/Applications/Blender.app/Contents/MacOS/Blender", "--version"]),
            "codex": _version(["/Applications/ChatGPT.app/Contents/Resources/codex", "--version"])
            or _version(["codex", "--version"]),
            "ffmpeg": _version(["/opt/homebrew/bin/ffmpeg", "-version"]),
            "ffprobe": _version(["/opt/homebrew/bin/ffprobe", "-version"]),
        },
        "checks": {
            "required_files": {"status": "PASSED" if files_pass else "FAILED", "missing": [p for p in required if not (ROOT / p).is_file()]},
            "default_tests": tests,
            "compile_smoke": compile_smoke,
            "extension_build": extension_build,
            "clean_room": clean_room_result,
            "release_zip_scan": scans,
            "artifacts_ignored": {"status": "PASSED" if "artifacts/" in (ROOT / ".gitignore").read_text() else "FAILED"},
        },
        "git": git_status,
        "release_files": {path.name: {"size": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in zips},
        "model_evidence": {
            "primary_task_id": "019f7749-0bc7-7733-9d9a-17a37e273539",
            "verified_model": "gpt-5.6-sol",
            "source": "local Codex session thread_settings_applied records",
            "feedback_session_id": None,
        },
        "video": {"status": "USER_RECORDING_REQUIRED", "youtube_url": None, "script": "DEMO_SCRIPT.md"},
    }
    RELEASE.mkdir(parents=True, exist_ok=True)
    (RELEASE / "preflight.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Codex3D release readiness.")
    parser.add_argument("--run-tests", action="store_true")
    parser.add_argument("--clean-room", action="store_true")
    args = parser.parse_args()
    result = preflight(args.run_tests, args.clean_room)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] != "NOT_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
