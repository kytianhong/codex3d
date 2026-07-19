from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .common import Dimensions, Metadata, new_id, utc_now_iso


class AssetFormat(str, Enum):
    BLEND = "blend"
    GLB = "glb"
    GLTF = "gltf"
    FBX = "fbx"
    OBJ = "obj"
    USD = "usd"
    USDZ = "usdz"
    UNKNOWN = "unknown"


class AssetSourceType(str, Enum):
    LOCAL = "local"
    EXTERNAL_SEARCH = "external_search"
    GENERATED = "generated"


class LicenseType(str, Enum):
    UNKNOWN = "unknown"
    CC0 = "cc0"
    CC_BY = "cc_by"
    CC_BY_SA = "cc_by_sa"
    ROYALTY_FREE = "royalty_free"
    PROPRIETARY = "proprietary"
    CUSTOM = "custom"


@dataclass
class Provenance:
    id: str = field(default_factory=lambda: new_id("provenance"))
    source_type: AssetSourceType = AssetSourceType.LOCAL
    source_url: str | None = None
    author: str | None = None
    license: LicenseType = LicenseType.UNKNOWN
    provider: str | None = None
    prompt: str | None = None
    search_query: str | None = None
    cost_usd: float | None = None
    created_at: str = field(default_factory=utc_now_iso)
    metadata: Metadata = field(default_factory=dict)


@dataclass
class Asset:
    id: str = field(default_factory=lambda: new_id("asset"))
    name: str = ""
    format: AssetFormat = AssetFormat.UNKNOWN
    source_type: AssetSourceType = AssetSourceType.LOCAL
    local_path: str | None = None
    source_url: str | None = None
    dimensions: Dimensions | None = None
    provenance: Provenance = field(default_factory=Provenance)
    tags: list[str] = field(default_factory=list)
    metadata: Metadata = field(default_factory=dict)

