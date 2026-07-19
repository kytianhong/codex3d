from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


LOOPBACK_HOST = "127.0.0.1"


class ConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class BridgeConfig:
    host: str = LOOPBACK_HOST
    port: int = 9876
    token: str = ""
    connect_timeout: float = 2.0
    request_timeout: float = 60.0
    artifact_root: Path | None = None
    include_images: bool = True

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> BridgeConfig:
        values = os.environ if environ is None else environ
        host = values.get("CODEX3D_BRIDGE_HOST", LOOPBACK_HOST)
        if host != LOOPBACK_HOST:
            raise ConfigurationError("CODEX3D_BRIDGE_HOST must be 127.0.0.1.")
        try:
            port = int(values.get("CODEX3D_BRIDGE_PORT", "9876"))
        except ValueError as exc:
            raise ConfigurationError("CODEX3D_BRIDGE_PORT must be an integer.") from exc
        if port < 1 or port > 65535:
            raise ConfigurationError("CODEX3D_BRIDGE_PORT must be between 1 and 65535.")
        try:
            connect_timeout = float(values.get("CODEX3D_BRIDGE_CONNECT_TIMEOUT", "2"))
            request_timeout = float(values.get("CODEX3D_BRIDGE_REQUEST_TIMEOUT", "60"))
        except ValueError as exc:
            raise ConfigurationError("Bridge timeouts must be numeric.") from exc
        if connect_timeout <= 0 or request_timeout <= 0:
            raise ConfigurationError("Bridge timeouts must be positive.")
        artifact_root_value = values.get("CODEX3D_ARTIFACT_ROOT")
        artifact_root = Path(artifact_root_value).expanduser().resolve() if artifact_root_value else None
        include_images = values.get("CODEX3D_MCP_INCLUDE_IMAGES", "1") not in {"0", "false", "False"}
        return cls(
            host=host,
            port=port,
            token=values.get("CODEX3D_BRIDGE_TOKEN", ""),
            connect_timeout=connect_timeout,
            request_timeout=request_timeout,
            artifact_root=artifact_root,
            include_images=include_images,
        )

    def require_token(self) -> None:
        if not self.token:
            raise ConfigurationError("CODEX3D_BRIDGE_TOKEN is required before calling Blender tools.")
