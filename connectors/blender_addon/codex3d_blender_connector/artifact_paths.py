from __future__ import annotations

from pathlib import Path


class ArtifactPathError(ValueError):
    pass


def resolve_artifact_path(
    artifact_root: str | Path | None,
    relative_path: str,
    *,
    allowed_suffixes: set[str],
) -> tuple[Path, str]:
    if artifact_root is None or not str(artifact_root).strip():
        raise ArtifactPathError("CODEX3D_ARTIFACT_ROOT is required for artifact actions.")
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise ArtifactPathError("Artifact path must be a non-empty relative path.")
    candidate = Path(relative_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ArtifactPathError("Artifact path must stay inside CODEX3D_ARTIFACT_ROOT.")
    if candidate.suffix.lower() not in allowed_suffixes:
        raise ArtifactPathError(
            f"Artifact extension must be one of: {sorted(allowed_suffixes)}"
        )
    root = Path(artifact_root).expanduser().resolve()
    resolved = (root / candidate).resolve()
    try:
        normalized = resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise ArtifactPathError("Artifact path escaped CODEX3D_ARTIFACT_ROOT.") from exc
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved, normalized
