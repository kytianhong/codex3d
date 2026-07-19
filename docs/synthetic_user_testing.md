# Synthetic User Testing

UT-01 is a black-box synthetic novice test for Codex3D's existing local workflow. It is not evidence that a real person is comfortable with or trusts the product.

## Roles

```text
UT-01 orchestrator and observer
  -> exact novice-language turn
  -> persistent Target Codex session
  -> ephemeral codex3d STDIO MCP configuration
  -> authenticated localhost Bridge
  -> isolated factory-startup Blender
  -> deterministic inspection and artifact evaluator
```

The observer never sends Blender Actions. It starts and stops the isolated environment, sends one novice message at a time, records Target Codex JSONL events, and performs read-only scene inspections. Every creative mutation must appear as a Target Codex MCP tool call. The Target Codex process remains in a read-only shell sandbox. Restore is annotated as reversible/non-destructive only because it is session-bound, fingerprint-checked, artifact-root confined, and automatically creates a non-overwriting safety snapshot first. It is never described as read-only.

## Run

The ordinary suite skips this long real integration test:

```bash
python -m pytest
```

Run UT-01 directly:

```bash
python scripts/run_synthetic_user_test_ut01.py
```

Run it through pytest explicitly:

```bash
CODEX3D_RUN_SYNTHETIC_UT01=1 \
python -m pytest tests/e2e/test_synthetic_user_ut01.py
```

The installed Codex CLI supports `codex exec resume <SESSION_ID>`. UT-01 therefore keeps one Target Codex session across all turns. MCP settings are injected per invocation with `--ignore-user-config`; the global Codex configuration is hashed before and after.

## Isolation

- Blender starts with `--factory-startup --background`, creates a separate empty `C3D_UT01_Isolated` Scene, and never opens or edits a user `.blend`.
- The Bridge binds a random `127.0.0.1` port and uses a one-time token.
- Target objects live in `C3D_UT01_CODEX_SPACE` and use the `C3D_UT01_` prefix.
- The target process has a read-only sandbox and is instructed to use only Codex3D MCP tools.
- Outputs are confined to `artifacts/user_tests/ut01_synthetic/`.
- Existing UT-01 artifacts are archived, not deleted.
- Blender and Target Codex child processes are reaped and the Bridge port is checked after shutdown.

## Evidence

Each turn records the novice message, Target Codex response, MCP tool calls, elapsed time, first mutating tool time, compact-inspection character count, canonical scene fingerprint, and scene diff. Compact mode reports names/UUIDs, type counts, collection, camera, materials, lights, animation and fingerprint; a UUID-specific request returns detailed transforms. The evaluator separately uses full read-only inspection.

Final delivery uses the target collection's evaluated bounding-box projections and rendered pixels. It requires at least 0.95 inside-frame ratio, no unwanted visible objects, controlled center/coverage and overexposure, and all six named curves intersecting the frame. Failure codes include `SUBJECT_CROPPED`, `CAMERA_TOO_CLOSE`, `CORE_OVEREXPOSED`, and `UNWANTED_OBJECT_VISIBLE`.

The orchestrator enforces `WORKING -> USER_ACCEPTED -> USER_REJECTED -> RESTORING -> USER_ACCEPTED -> DELIVERED`. A failed or mismatched Turn 7B restore prevents Turn 8 from running, and a fallback snapshot is never reported as the final scene.

## Status Vocabulary

Results use only:

- `SYNTHETIC_PASS`
- `SYNTHETIC_PARTIAL`
- `SYNTHETIC_FAIL`

No synthetic result may be described as a real user-test pass.
