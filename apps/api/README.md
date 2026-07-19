# API App

Round 03 implements the local API core boundary without external dependencies.

The package in `codex3d_api/` provides:

- In-memory sessions
- In-memory jobs
- Message submission
- Mock agent turns
- Session scene lookup
- JSON-friendly response serialization
- Optional FastAPI adapter

The core service does not require FastAPI, Blender, GPT APIs, providers, a database, or a Web UI.

Run the local smoke demo from the repository root:

```bash
python -m codex3d_api.smoke
```

Run tests from the repository root:

```bash
python -m pytest
```

