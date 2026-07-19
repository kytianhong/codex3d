# Demo Gate 0 Report

Date: 2026-07-19  
Gate: Local End-to-End Automated Test  
Status: PASS

## Completed

- Added one-command Gate orchestration with an isolated Blender CLI host.
- Verified MCP initialize, JSON-RPC ping, tools/list, tools/call, and all nine expected tool definitions.
- Audited protocol, API, and MCP sources for direct `bpy` imports and audited the MCP list for Python/shell tools.
- Created an original radial prototype with one core, six stable radial parts, two initial material assignments, and one warm point light.
- Applied deterministic follow-up transform, material, light color, and light energy edits.
- Ran ephemeral Codex natural-language acceptance without changing global MCP configuration.
- Generated a readiness matrix and an isolated `.blend` artifact.
- Verified Blender exit and loopback port release.

## Automated Tests

Baseline command: `python -m pytest -q`  
Result: PASSED, 123 tests.

Ordinary suite after Gate additions: 123 passed, 1 real-Blender test skipped unless explicitly enabled.

Real integration command: `CODEX3D_RUN_REAL_BLENDER_TESTS=1 python -m pytest -q tests/integration/test_demo_gate_0.py`  
Result: PASSED, 1 test in 17.41 seconds on the final run.

## Real Blender Result

- Blender version: 5.1.1
- Backend: `bpy`
- Startup mode: isolated `--factory-startup --background`
- Bridge: authenticated random port on `127.0.0.1`
- Planned creation/material actions: 15
- Creation/material actions succeeded: 15
- Follow-up actions succeeded: 3
- Failed actions: 0
- Gate-owned objects: 8
- Saved scene: `artifacts/demo_gate_0/codex3d_gate0.blend`

## Codex Natural-Language Result

Status: PASSED

Observed real MCP sequence:

```text
blender_inspect_scene
blender_transform_object
blender_assign_material
blender_inspect_scene
```

Final verified core state:

- Location: `[0.0, 0.0, 1.25]`
- Scale: approximately `[1.3, 1.3, 1.3]`
- Material: `C3D_GATE0_BrightWarmGold`

## Safety And Cleanup

- Existing Blender files opened: none.
- Global Codex config changed: no; digest unchanged.
- Token present in MCP, Codex, inspection, or result output: no.
- Arbitrary Python/shell tool: none.
- `bpy` imports outside connector: none.
- Blender return code: 0.
- Bridge port released: yes.
- Residual MCP process: none.
- Ready/stop sentinel files removed: yes.

## Readiness

| Capability | Status |
|---|---|
| Natural-language MCP control | READY |
| Primitive creation | READY |
| Transform | READY |
| Basic material | READY |
| Point light | READY |
| Curve creation | MISSING |
| Advanced material | MISSING |
| Camera | MISSING |
| World lighting | MISSING |
| Static render | MISSING |
| Render image return | MISSING |
| Keyframe animation | MISSING |
| Timeline playback | MISSING |
| Video export | MISSING |
| Snapshot / Undo | MISSING |
| Stable UUID / Scene IR | PARTIAL |

Machine-readable matrix: `artifacts/demo_gate_0/readiness.json`.

## Gate Decision

The implemented natural-language modeling foundation is stable enough to enter Sprint 02B. Render, camera, advanced material, and world-lighting gaps are expected Sprint inputs and do not fail Gate 0.

Recommended next scope: Creative Geometry + Materials + Camera + Render Preview, while retaining structured allowlisted actions and this isolated Gate as a regression check.
