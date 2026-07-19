from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

Metadata = dict[str, Any]


class UnitSystem(str, Enum):
    METERS = "meters"


@dataclass
class Vector3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass
class Transform:
    location: Vector3 = field(default_factory=Vector3)
    rotation_euler: Vector3 = field(default_factory=Vector3)
    scale: Vector3 = field(default_factory=lambda: Vector3(1.0, 1.0, 1.0))


@dataclass
class Dimensions:
    width: float = 0.0
    depth: float = 0.0
    height: float = 0.0


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    cleaned = "".join(
        char if char.isalnum() or char in {"_", "-"} else "_"
        for char in prefix.strip().lower()
    ).strip("_")
    readable_prefix = cleaned or "id"
    return f"{readable_prefix}_{uuid4().hex}"

