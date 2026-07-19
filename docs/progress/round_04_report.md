# Round 04 Report

Date: 2026-07-18

Round: 04 - Blender Connector Handshake

Status: DONE

Completed:

- Added connector protocol/schema for registration, heartbeat, ping, ping result, and scene inspection.
- Added API connector store and connector service.
- Integrated connector registration, list, lookup, heartbeat, and ping methods into `Codex3DApiService`.
- Added optional FastAPI connector endpoints without making FastAPI a hard dependency.
- Added minimal Blender connector package with guarded `bpy` loading.
- Added connector client helpers to build registration, heartbeat, and ping payloads.
- Added empty and fake scene inspection helpers that work without Blender.
- Added local direct-service connector smoke demo.
- Added tests across protocol, API connector service, connector flow, package import, registration, inspection, and smoke behavior.
- Updated README, API docs, protocol docs, Blender connector docs, development plan, and project tracker.

Changed files:

- `README.md`
- `pyproject.toml`
- `packages/protocol/codex3d_protocol/__init__.py`
- `packages/protocol/codex3d_protocol/connectors.py`
- `packages/protocol/tests/test_import.py`
- `packages/protocol/tests/test_connector_schema.py`
- `apps/api/codex3d_api/__init__.py`
- `apps/api/codex3d_api/connector_store.py`
- `apps/api/codex3d_api/connector_service.py`
- `apps/api/codex3d_api/service.py`
- `apps/api/codex3d_api/fastapi_app.py`
- `apps/api/tests/test_connector_service.py`
- `apps/api/tests/test_connector_flow.py`
- `connectors/blender_addon/README.md`
- `connectors/blender_addon/codex3d_blender_connector/__init__.py`
- `connectors/blender_addon/codex3d_blender_connector/addon.py`
- `connectors/blender_addon/codex3d_blender_connector/client.py`
- `connectors/blender_addon/codex3d_blender_connector/inspection.py`
- `connectors/blender_addon/codex3d_blender_connector/manifest.py`
- `connectors/blender_addon/codex3d_blender_connector/smoke.py`
- `connectors/blender_addon/tests/test_connector_import.py`
- `connectors/blender_addon/tests/test_connector_registration.py`
- `connectors/blender_addon/tests/test_scene_inspection.py`
- `docs/api.md`
- `docs/blender_connector.md`
- `docs/development_plan.md`
- `docs/project_tracker.md`
- `docs/protocol.md`
- `docs/progress/round_04_report.md`

Tests:

- `python -m pytest` passed with 30 tests.
- `PYTHONPATH=packages/protocol:apps/api:connectors/blender_addon python -m codex3d_blender_connector.smoke` completed successfully.

Demo result:

- Created a local API service.
- Built a Blender connector registration payload.
- Registered connector with API service.
- Sent heartbeat.
- Pinged connector successfully.
- Inspected an empty scene without requiring Blender.

Open issues:

- No basic Blender create/transform/material/delete actions exist yet.
- No real Blender scene mutation exists yet.
- No render preview, snapshot/undo, real worker, GPT API, Web UI, or provider exists yet.
- Connector inspection only reads empty/fake basic object state in ordinary Python tests.

Next recommended round:

- Round 05: Basic Blender actions

