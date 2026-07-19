# Round 03 Report

Date: 2026-07-18

Round: 03 - Local API Session / Job Boundary

Status: DONE

Completed:

- Implemented the dependency-free `codex3d_api` package.
- Added API dataclasses for sessions, messages, session summaries, and message submission responses.
- Added in-memory session and job stores.
- Added `Codex3DApiService` for health, session, message, job, and scene lookup operations.
- Added local mock agent turn flow using Round 02 protocol `Action` and `Job`.
- Added mock desk prompt handling for English `desk` and Chinese `书桌`.
- Added API serialization helpers using the protocol serializer.
- Added optional FastAPI adapter that does not break core imports when FastAPI is unavailable.
- Added local smoke demo.
- Expanded pytest configuration to cover both protocol and API tests.
- Updated README, API docs, development plan, and project tracker.

Changed files:

- `README.md`
- `pyproject.toml`
- `apps/api/README.md`
- `apps/api/codex3d_api/__init__.py`
- `apps/api/codex3d_api/version.py`
- `apps/api/codex3d_api/models.py`
- `apps/api/codex3d_api/store.py`
- `apps/api/codex3d_api/service.py`
- `apps/api/codex3d_api/mock_agent.py`
- `apps/api/codex3d_api/serialization.py`
- `apps/api/codex3d_api/fastapi_app.py`
- `apps/api/codex3d_api/smoke.py`
- `apps/api/tests/test_api_import.py`
- `apps/api/tests/test_session_service.py`
- `apps/api/tests/test_job_service.py`
- `apps/api/tests/test_message_flow.py`
- `apps/api/tests/test_fastapi_optional.py`
- `docs/api.md`
- `docs/project_tracker.md`
- `docs/development_plan.md`
- `docs/progress/round_03_report.md`

Tests:

- `python -m pytest` passed with 19 tests.
- `PYTHONPATH=packages/protocol:apps/api python -m codex3d_api.smoke` completed successfully.

Demo result:

- Created a local session.
- Submitted a beginner-style desk prompt.
- Created a mock agent job.
- Produced a mock action summary.
- Retrieved session scene and job state through the service layer.
- Serialized the response to JSON.

Open issues:

- No Blender connector exists yet.
- No real FastAPI server is required or tested yet.
- No real LLM, provider, render, database, or async worker exists yet.
- Mock scene objects are local proposed state only and do not represent Blender execution.

Next recommended round:

- Round 04: Blender connector handshake
