"""Single protocol import boundary for workspace and packaged extension use."""

try:
    from codex3d_protocol import *  # noqa: F403
except ImportError:  # pragma: no cover - exercised inside the packaged extension
    from .vendor.codex3d_protocol import *  # type: ignore  # noqa: F403
