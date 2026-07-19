# UT-01 Reliability Repair Report

Date: 2026-07-19  
Status: DONE  
Rerun result: SYNTHETIC_PASS, 100/100

This remains a synthetic test. It proves the automated multi-turn path can execute; it does not prove that a real novice understands, trusts, or likes Codex3D.

## Scope Completed

- Made restore session-bound and artifact-root confined, requiring both current and registered snapshot SHA-256 fingerprints.
- Added an immutable `snapshot_pre_restore_*` safety snapshot before mutation, automatic rollback on post-restore mismatch, fresh inspection and scene diff.
- Made checkpoint delivery non-overwriting and versioned, using a temporary Blender copy plus atomic move; returns checksum, size, fingerprint and UUID count without changing the live Scene.
- Corrected MCP annotations: restore/save are mutating and non-idempotent, not read-only; both are non-destructive only under the enforced reversible/non-overwriting constraints.
- Added `WORKING -> USER_ACCEPTED -> USER_REJECTED -> RESTORING -> USER_ACCEPTED -> DELIVERED` orchestration. Turn 8 cannot run after a failed restore.
- Created and activated an empty isolated Blender Scene while leaving the factory Scene and user projects untouched.
- Added compact inspection filters for scene, collection, UUID and semantic group. Full inspection remains explicit.
- Added collection-aware camera projection and pixel validation for crop, center, coverage, overexposure, unwanted objects and six-curve visibility.

## Approval Regression

The original restore/save failures occurred before the Bridge: Codex tool events had `result=null`, and both tools advertised `destructiveHint=true`. No Blender error existed.

The unchanged rerun completed one granular `blender_restore_snapshot` call with the current fingerprint, target fingerprint and registered snapshot id. It created one safety snapshot and returned successfully. `blender_save_checkpoint` also completed and created `final_scene.blend`; no approval cancellation occurred.

Two broad `blender_execute_batch` attempts were still auto-cancelled early in Turns 1 and 2. Target Codex recovered through granular tools. No restore, checkpoint or final-delivery operation was cancelled.

## Fingerprint Repair Audit

The first repaired rerun correctly stopped at Turn 7B instead of delivering a rejected scene. Restore reached Blender, but saved/reloaded transforms differed because keyframe insertion left objects at the last inserted value while `.blend` reload evaluated the current Timeline frame.

The executor now re-evaluates the current frame after every keyframe operation, and canonical snapshots include animation statistics. A real Blender regression then passed, followed by the successful unchanged UT-01 rerun.

## Tests

- Baseline before repair: `144 passed, 3 skipped`.
- Final default suite: `153 passed, 3 skipped`.
- Real Blender Sol snapshot/render regression: `1 passed in 27.46s`.
- Real persistent Target Codex UT-01: `SYNTHETIC_PASS`, process exit code 0.
- Compile smoke: all packages, apps, connectors, scripts, examples and tests compiled.

New coverage includes wrong session/path/fingerprint rejection, no-mutation failure behavior, safety snapshot creation, exact transform/material/camera/animation restore, versioned non-overwrite save/checksum, delivery-state rejection, compact/full size comparison, MCP annotations/schema, and positive/negative composition cases.

## Unchanged UT-01 Result

| Turn | Time | First visible update |
|---|---:|---:|
| 1 | 29.48 s | none required |
| 2 | 267.73 s | 92.28 s |
| 3 | 250.99 s | 22.91 s |
| 4 | 116.62 s | 25.44 s |
| 5 | 124.85 s | 29.55 s |
| 6 | 90.33 s | 21.63 s |
| 7A | 58.79 s | 21.13 s |
| 7B | 18.99 s | 13.05 s |
| 8 | 91.76 s | 12.56 s |

Total elapsed: 1,049.54 seconds (17.49 minutes). Target Codex made 133 MCP calls with 2 recoverable batch cancellations.

## Before / After

| Metric | Original UT-01 | Repaired UT-01 |
|---|---:|---:|
| Status | SYNTHETIC_FAIL | SYNTHETIC_PASS |
| Score | 82/100 | 100/100 |
| Duration | 21.9 min | 17.49 min |
| MCP calls | 212 | 133 |
| Failed calls | 14 | 2 |
| Inspection response characters | 1,348,589 | 119,722 |
| Inspection reduction | baseline | 91.1% |
| Restore | 3 approval cancellations | 1 successful reversible restore |
| Final `.blend` | missing | present, 145,100 bytes |
| Factory objects in active Scene | visible Cube | none |
| Six-curve inside-frame ratio | cropped | 1.0 for all six |
| Center offset | visibly displaced | 0.0088 |
| Overexposed pixel ratio | visibly clipped core | 0.000244 |
| Unwanted visible objects | Factory Cube | 0 |

Turn 6 and Turn 7B canonical fingerprints both equal `c29e724f1eb3a1f110a3e84c2a825193d9f2c997eb886c01e716fb12c1d50bf7`. Six curve UUIDs, confirmed materials and animation state match exactly after restore.

## Final Artifacts

- `artifacts/user_tests/ut01_synthetic/final_scene.blend`
- `artifacts/user_tests/ut01_synthetic/preview_final.png`
- `artifacts/user_tests/ut01_synthetic/preview_final.validation.json`
- `artifacts/user_tests/ut01_synthetic/codex_space_animation.mp4`
- `artifacts/user_tests/ut01_synthetic/final_manifest.json`
- `artifacts/user_tests/ut01_synthetic/result.json`

MP4 validation: H.264, yuv420p, 1200x1200, 24 FPS, 72 frames, 3.0 seconds, 437,322 bytes, full decode PASSED, SHA-256 `a07183f349b3013ee146afa472fe119f07c91c13dee07e84b909addc810876c4`.

Visual observer review: PASSED. The six curves are complete and centered, the core is readable without clipping, and no factory object is visible. The translucent background planes still look like technical-demo art direction and should be treated as polish feedback, not a reliability failure.

## Safety

- User `.blend` opened, changed or overwritten: NO.
- Global Codex configuration changed: NO.
- Arbitrary Python, shell MCP or approval bypass: NONE.
- Bridge: random `127.0.0.1` port with one-time token.
- Token leakage: NOT FOUND.
- Blender/Codex/MCP processes: REAPED.
- Bridge port after test: RELEASED.
- Existing artifacts: archived before each rerun.

## Remaining Risks

- Synthetic success is not human usability evidence.
- The 17.5-minute flow and 92-second first visible update in Turn 2 remain too slow for a polished novice experience.
- Broad batch mutations may still trigger unattended approval cancellation; granular allowlisted tools provide the validated path.
- Full Scene IR reconciliation remains outside this repair sprint.

Recommended next step: run a moderated novice study and profile turn latency. Do not add new modeling capability until those findings are understood.
