# Local-First Workflow

Codex3D early development is fully local. This keeps the project inspectable, repeatable, and safe to iterate without depending on chat history or remote services.

## Local Project Memory

Project state lives in repository files:

- `docs/project_tracker.md` is the current progress board.
- `docs/progress/` stores round-by-round reports.
- `docs/decisions/` stores architecture decision records.
- Package READMEs describe module boundaries.

The chat can help drive work, but the repository files are the durable memory.

## Round Reports

Every development round should create or update one report:

```text
docs/progress/round_XX_report.md
```

Each report records date, status, completed work, changed files, tests, demo result, open issues, and the next recommended round.

## Smoke Tests

Each round should include at least one local smoke test. Round 01 uses a minimal protocol package import test.

Future rounds should add tests near the package that owns the behavior.

## Local Blender Connector

Later rounds should connect Blender through localhost. Blender should not be required for Round 01, and the connector should remain optional until the handshake round.

## Provider Boundary

External providers are out of scope until the project explicitly enters the provider phase. Provider integration must not introduce hidden remote state, real keys, or forced third-party login during the local-first MVP.

