import codex3d_blender_connector


def test_blender_connector_imports_without_bpy() -> None:
    status = codex3d_blender_connector.register()

    assert codex3d_blender_connector.CONNECTOR_NAME == "Codex3D Blender Connector"
    assert status is None
    assert codex3d_blender_connector.unregister() is None
