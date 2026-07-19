from codex3d_protocol import (
    Asset,
    AssetFormat,
    AssetSourceType,
    Dimensions,
    LicenseType,
    Provenance,
)


def test_asset_and_provenance_record_source_details() -> None:
    provenance = Provenance(
        source_type=AssetSourceType.GENERATED,
        source_url="https://example.invalid/assets/desk",
        author="Example Author",
        license=LicenseType.CC_BY,
        provider="example-provider",
        prompt="A compact mid-century writing desk",
        cost_usd=0.0,
    )
    asset = Asset(
        name="Mid-century desk",
        format=AssetFormat.GLB,
        source_type=AssetSourceType.GENERATED,
        local_path="assets/mid_century_desk.glb",
        source_url=provenance.source_url,
        dimensions=Dimensions(width=1.2, depth=0.6, height=0.75),
        provenance=provenance,
        tags=["desk", "wood"],
    )

    assert asset.format is AssetFormat.GLB
    assert asset.provenance.provider == "example-provider"
    assert asset.provenance.license is LicenseType.CC_BY
    assert asset.dimensions is not None
    assert asset.dimensions.width == 1.2

