# Synthetic User Test UT-01 Report

Date: 2026-07-19  
Test: Codex-Orchestrated Zero-to-Space Demo  
Status: SYNTHETIC_FAIL  
Score: 82/100

This is a synthetic user test. It demonstrates executable multi-turn behavior and product failures; it is not evidence of real-user comprehension, trust, or satisfaction.

## Baseline

- Default suite before implementation: `144 passed, 2 skipped`.
- Default suite after adding the gated E2E test: `144 passed, 3 skipped`.
- Real UT-01 execution: COMPLETED with `SYNTHETIC_FAIL` result.
- Target Codex mode: one persistent `codex exec resume` session with ephemeral MCP command-line configuration.
- Blender: isolated factory-startup Blender 5.1.1 on a random loopback Bridge port.

## Actual Chain

```text
Synthetic novice turn
  -> persistent Target Codex
  -> codex3d STDIO MCP
  -> SocketConnectorClient
  -> authenticated 127.0.0.1 Bridge
  -> Blender main-thread executor
  -> bpy
  -> read-only deterministic inspection/diff evaluator
```

The observer sent no Blender Actions. All creative mutations in the scene appear in the Target Codex MCP trace.

## Turn Results

| Turn | Total time | First successful visible update | MCP calls | Failed calls | Result |
|---|---:|---:|---:|---:|---|
| 1 | 23.94 s | NONE | 3 | 1 | Inspection passed; factory deletion was cancelled |
| 2 | 221.07 s | 103.26 s | 37 | 2 | Core, six cyclic curves, camera, lights and materials created |
| 3 | 258.08 s | 33.59 s | 67 | 0 | Six UUIDs preserved; depth/tilt layering and preview completed |
| 4 | 148.21 s | 35.05 s | 45 | 0 | Space background, warm/dark/blue-white palette and preview completed |
| 5 | 74.98 s | 25.46 s | 12 | 0 | 24 FPS, frames 1-72, orbit/emission/camera keyframes completed |
| 6 | 110.05 s | 30.11 s | 12 | 0 | Slower animation, wider camera and confirmed snapshot completed |
| 7A | 125.07 s | 77.33 s | 19 | 2 | Bright-purple and oversized-core trial visibly applied |
| 7B | 25.65 s | NONE | 4 | 3 | Restore requested three times and cancelled three times |
| 8 | 325.93 s | 22.87 s | 13 | 6 | Preview and frames completed; checkpoint save cancelled |

Total: 212 MCP calls, 14 failed calls. The persistent session compacted once and retained the snapshot identifier, but the approval layer still blocked restoration.

## Deterministic Evaluation

Passed:

- `C3D_UT01_Core` and all six stable `C3D_UT01_Orbit_01..06` objects exist.
- The six curve UUIDs are unique and survive Turns 2 through 7B.
- Turn 3 changes the curves' 3D depth/tilt without replacing them.
- Turn 4 creates a camera, World update, multiple lights, space elements and a render.
- Turn 5 reports frames 1-72 and 298 cumulative keyframe operations in the final inspection.
- Turn 6 preserves confirmed curve material aliases and creates `snapshot_ut01_turn6_confirmed`.
- Turn 7A produces a different canonical fingerprint and visible purple/scale changes.
- Three still PNG files are non-empty.
- The controlled encoder packages 72 frames as H.264/yuv420p at 24 FPS for 3.0 seconds.
- The resulting 800x800 MP4 fully decodes; size is 466,908 bytes and SHA-256 is `89d2419613325b7bfb419dc7ffb312ff04c28da02c14a9cd89c134f4feb04517`.

Failed:

- Turn 1 could not remove factory `Cube`, `Camera`, and `Light` because the destructive MCP call was cancelled.
- Turn 7B could not restore the confirmed snapshot. Its canonical fingerprint remained the Turn 7A fingerprint.
- Confirmed materials and animation state therefore were not restored.
- Turn 8 could not save `final_scene.blend`; three checkpoint attempts were cancelled.
- The Target Codex created `snapshots/snapshot_final_scene.blend` as a fallback, but it contains the rejected Turn 7A state and does not satisfy the requested final artifact contract.

Critical failures: `snapshot_restore_mismatch`, `final_blend_missing`.

## Scene And Identity

- Final isolated collection object count: 37.
- Objects with stable UUID: 37/37.
- Required orbit curves: 6/6 with unchanged UUIDs.
- Total curves: 9, including extra space/background curve elements.
- Lights: 3.
- Active camera: `C3D_UT01_Camera`.
- Timeline: frames 1-72.
- Final scene is the rejected purple/oversized-core trial because restore did not execute.

## Visual Observer Review

Visual evaluation was run on all three PNGs.

- Turn 3 visibly adds spatially layered orbit curves and a multi-part center.
- Turn 4 visibly introduces warm metal, blue-white energy, sparse stars and restrained blue nebula forms.
- Several orbit curves are clipped by the camera in all previews.
- The undeleted factory Cube is prominently visible at the left edge.
- The final core is oversized and overexposed, obscuring center detail.
- The final image visibly confirms that the disliked Turn 7A state was not restored.

Visual persona evaluation: FAILED.

## Scorecard

| Category | Score |
|---|---:|
| From empty scene to target | 20/20 |
| Multi-turn intent preservation | 20/20 |
| Ambiguous feedback mapping | 15/15 |
| Progressive visible feedback | 10/10 |
| Animation and final delivery | 7/15 |
| Snapshot restore | 0/10 |
| Novice-language response | 5/5 |
| Safety and cleanup | 5/5 |
| **Total** | **82/100** |

The numeric score exceeds 80, but critical restore and final delivery failures force `SYNTHETIC_FAIL`.

## Safety And Cleanup

- User `.blend` files opened or modified: NO.
- Global Codex `config.toml` changed: NO; before/after digest matched.
- Bridge bind: random `127.0.0.1` port.
- Token in artifacts/logs/results: NOT FOUND.
- Target shell or arbitrary Python calls: NONE.
- Blender and MCP/Codex child processes: REAPED.
- Bridge port after run: RELEASED.
- Existing UT artifacts: archived rather than deleted.

## Product Findings

1. **Blocking:** non-interactive Target Codex cannot complete explicit, user-requested destructive MCP operations. Factory deletion, snapshot restore and checkpoint save were cancelled even with `auto_review` and a read-only shell sandbox.
2. **Blocking:** rollback failure leaves the rejected design active, yet the agent can continue into final render and report completion. Final-delivery gating must require successful restore/save results.
3. **High:** MCP inspection and ActionResult payloads are large. The 212-call session triggered context compaction and made early creative turns take 2-4 minutes.
4. **High:** the render visibility validator is hard-coded to `C3D_SOL_`, so UT objects report `subject_visible=false` despite being visible.
5. **Medium:** the agent anticipated animation in Turn 2 and overworked Turn 3. A turn-scoped completion policy and compact collection-filtered inspection are needed.
6. **Medium:** camera composition allowed clipped curves and a factory object to dominate the left edge.

## Minimal Next Sprint

Do not add new modeling capability. Fix only the test blockers:

1. Add a narrowly scoped, auditable approval path for an explicitly requested artifact-root checkpoint and named snapshot restore, without enabling shell or arbitrary Python.
2. Require Target Codex to stop final delivery when restore or checkpoint returns a failed/cancelled tool result.
3. Make visibility validation prefix- or collection-driven instead of `C3D_SOL_`-specific.
4. Add compact, collection-filtered inspection output and a per-turn action budget.
5. Rerun UT-01 unchanged. `SYNTHETIC_PASS` requires exact Turn 6 restore and `final_scene.blend`.

## Artifacts

```text
artifacts/user_tests/ut01_synthetic/preview_turn_3.png
artifacts/user_tests/ut01_synthetic/preview_turn_4.png
artifacts/user_tests/ut01_synthetic/preview_final.png
artifacts/user_tests/ut01_synthetic/codex_space_animation.mp4
artifacts/user_tests/ut01_synthetic/conversation.jsonl
artifacts/user_tests/ut01_synthetic/tool_trace.jsonl
artifacts/user_tests/ut01_synthetic/scene_diffs.json
artifacts/user_tests/ut01_synthetic/restore_validation.json
artifacts/user_tests/ut01_synthetic/synthetic_scorecard.json
artifacts/user_tests/ut01_synthetic/result.json
```

`final_scene.blend` is intentionally absent because the Target Codex checkpoint call did not execute. No success is claimed for the fallback snapshot.
