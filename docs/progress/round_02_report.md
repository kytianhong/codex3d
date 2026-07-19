# Round 02 Report

Date: 2026-07-18

Round: 02 - Protocol / Schema

Status: DONE

Completed:

- Implemented the first dependency-free protocol/schema layer using Python standard-library dataclasses and enums.
- Added common primitives for units, vectors, transforms, dimensions, metadata, timestamps, and readable IDs.
- Added Scene, SceneObject, Relation, and Constraint schema.
- Added Action, ToolCall, and ActionResult schema.
- Added Job schema with local status transition helpers.
- Added Asset and Provenance schema.
- Added ProtocolError schema.
- Added JSON-friendly `to_dict`, `to_json`, and simple `from_dict` serialization helpers.
- Expanded protocol exports from `codex3d_protocol.__init__`.
- Added focused tests for import, scene, action, job, asset, error, and serialization behavior.
- Updated `docs/protocol.md` from planning notes into the Round 02 protocol description.
- Updated `docs/project_tracker.md` to mark Round 02 as DONE and Round 03 as NEXT.

Changed files:

- `packages/protocol/codex3d_protocol/__init__.py`
- `packages/protocol/codex3d_protocol/common.py`
- `packages/protocol/codex3d_protocol/scene.py`
- `packages/protocol/codex3d_protocol/actions.py`
- `packages/protocol/codex3d_protocol/jobs.py`
- `packages/protocol/codex3d_protocol/assets.py`
- `packages/protocol/codex3d_protocol/errors.py`
- `packages/protocol/codex3d_protocol/serialization.py`
- `packages/protocol/tests/test_import.py`
- `packages/protocol/tests/test_scene_schema.py`
- `packages/protocol/tests/test_action_schema.py`
- `packages/protocol/tests/test_job_schema.py`
- `packages/protocol/tests/test_asset_schema.py`
- `packages/protocol/tests/test_error_schema.py`
- `packages/protocol/tests/test_serialization.py`
- `docs/protocol.md`
- `docs/project_tracker.md`
- `docs/development_plan.md`
- `docs/progress/round_02_report.md`

Tests:

- `python -m pytest` passed with 11 tests.

Demo result:

- Successfully constructed a sample Scene with desk and lamp objects, one relation, and one constraint.
- Successfully constructed an Action, ToolCall, ActionResult, Job, Asset, Provenance, and ProtocolError.
- Successfully serialized sample protocol objects to JSON-friendly dictionaries and JSON strings.
- Successfully reconstructed a simple Scene from a dictionary using `from_dict`.

Open issues:

- No FastAPI app exists yet.
- No real job runner exists yet.
- No Blender connector, provider, render, validation, or Scene IR reconciliation logic exists yet.
- Future API work may introduce Pydantic adapters, but the protocol core is intentionally dependency-free for now.

Next recommended round:

- Round 03: FastAPI session/job API

