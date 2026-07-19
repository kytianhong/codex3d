# Round 01 Report

Date: 2026-07-18

Round: 01 - Repo Scaffold + Local Progress System

Status: DONE

Completed:

- Created the `codex3d/` local project directory.
- Added monorepo-style folders for apps, connectors, packages, docs, and examples.
- Added a minimal Python workspace configuration.
- Added the importable `codex3d_protocol` package with version `0.1.0`.
- Added a minimal smoke test for package import and version.
- Added project documentation for architecture, local-first workflow, development plan, protocol planning, tracker, and ADR.
- Updated the local tracker to mark Round 01 as DONE and Round 02 as NEXT.

Changed files:

- `README.md`
- `pyproject.toml`
- `.gitignore`
- `apps/api/README.md`
- `apps/web/README.md`
- `connectors/blender_addon/README.md`
- `connectors/blender_worker/README.md`
- `packages/protocol/codex3d_protocol/__init__.py`
- `packages/protocol/codex3d_protocol/version.py`
- `packages/protocol/tests/test_import.py`
- `packages/*/README.md`
- `docs/architecture.md`
- `docs/development_plan.md`
- `docs/local_first_workflow.md`
- `docs/project_tracker.md`
- `docs/protocol.md`
- `docs/progress/round_01_report.md`
- `docs/decisions/ADR-0001-blender-first-modular-monolith.md`
- `examples/prompts/mvp_demo_prompts.md`
- `examples/scenes/README.md`
- `examples/assets/README.md`

Tests:

- `python -m pytest` passed with 1 test.

Demo result:

- The protocol package can be imported locally.
- `codex3d_protocol.__version__` returns `0.1.0`.

Open issues:

- No full protocol schema exists yet.
- No API, Web UI, Blender connector, Scene IR, provider, or render path is implemented yet.
- The outer workspace is not currently a Git repository.

Next recommended round:

- Round 02: Protocol/schema
