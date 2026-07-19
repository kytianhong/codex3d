import pytest

from codex3d_api import fastapi_app


def test_fastapi_adapter_is_optional() -> None:
    assert hasattr(fastapi_app, "create_app")

    if fastapi_app.FastAPI is None:
        with pytest.raises(RuntimeError, match="FastAPI is not installed"):
            fastapi_app.create_app()
    else:
        app = fastapi_app.create_app()
        assert app.title == "Codex3D Local API"

