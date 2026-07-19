import codex3d_api


def test_api_package_imports() -> None:
    assert codex3d_api.__version__ == "0.1.0"
    assert codex3d_api.Codex3DApiService
    assert codex3d_api.Session
    assert codex3d_api.SubmitMessageRequest

