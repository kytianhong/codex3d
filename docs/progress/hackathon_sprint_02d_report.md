# Hackathon Sprint 02D Report

Date: 2026-07-19  
Sprint: Demo Hardening  
Status: DONE

The visual output remains an original, unofficial Sol-inspired concept demo. It does not copy or trace an official logo.

## Completed

- Added a controlled offline PNG-sequence encoder boundary with artifact-root confinement, continuous frame validation, trusted `ffmpeg` resolution, fixed argv invocation, H.264/yuv420p/24 FPS/faststart settings, and SHA-256 metadata.
- Added snapshot create/list/restore/delete Actions and MCP tools. Snapshot `.blend` and JSON records include fingerprint, UUID inventory, timestamp, source turn/action, file size, active camera, and canonical scene summary.
- Added stable `codex3d_uuid` custom properties to every created Fake/bpy object and exposed UUIDs through inspection and ActionResult output.
- Added UUID-first transform/material targeting while preserving object names as readable aliases.
- Added explicit legacy prefix reconciliation without implementing full Scene IR.
- Polished the original six-way scene with a smaller blue emission core, glass-metal shell, alternating curve depth, functional warm outer boundary, broad studio floor, softer lighting, and safer camera framing.
- Added deliberate core/camera corruption followed by real snapshot restore and canonical comparison to the isolated demo.
- Added canonical `preview_polished.png`, restore evidence, GUI acceptance state, and final demo manifest artifacts.

## Automated Tests

- Baseline: `137 passed, 2 skipped`.
- Final default suite: `144 passed, 2 skipped`.
- Explicit isolated Blender Sol regression: PASSED, `1 passed`.
- Encoder argv/path/frame-gap tests: PASSED.
- Fake UUID rename/targeting, snapshot restore, delete/list, and reconcile tests: PASSED.
- MCP schema/mapping and legacy regression tests: PASSED.

## Extension Build

- Python deterministic ZIP build: PASSED, 28 validated files.
- Artifact: `dist/codex3d_blender_connector-0.1.0.zip`.
- Blender 5.1.1 official extension build from the staged package: PASSED.
- Direct build from the manifest-only source directory: FAILED as expected because that directory is not the staged package; no success is claimed for that incorrect invocation.

## Stable Identity

- Fake backend rename: PASSED, UUID unchanged.
- UUID-first transform/material targeting: PASSED.
- Real Blender creation: PASSED, 14/14 demo objects have UUIDs.
- Real `.blend` save/reload during snapshot restore: PASSED, 14 UUIDs preserved.
- Legacy `C3D_` reconciliation: PASSED in deterministic tests.
- Full Scene IR: NOT IMPLEMENTED, intentionally outside this sprint.

## Snapshot Restore

- Real snapshot creation: PASSED.
- Deliberate core and camera mutation: PASSED and canonical summary changed.
- Real restore through Blender main-thread executor: PASSED.
- Fingerprint before/after: identical.
- Restored object count: 14.
- Restored active camera: `C3D_SOL_Camera`.
- Transform/material/camera canonical summary: identical.
- Bridge remained responsive after `.blend` reload and shut down cleanly.

## Visual Result

- Scene: 14 objects, including six independent cyclic curves and a two-layer center.
- Polished preview: 512x512, 336,244 bytes.
- Mean luminance: 0.1523.
- Nonblack ratio: 0.9736.
- Nontransparent ratio: 1.0.
- Projected visible subjects: 10.
- Active camera: `C3D_SOL_Camera`.
- Automated validator: PASSED without threshold relaxation.
- Assistant visual inspection: PASSED for centered composition, safe margins, layered core, curve depth, and reduced empty black area.
- Real Codex follow-up: PASSED with inspect, core material, ring material, camera transform, render, inspect sequence.

## Animation And MP4

- Timeline: 1-72 at 24 FPS.
- PNG sequence: PASSED, 72/72 frames, 24,226,384 bytes in the final run.
- Keyframe operations: 26 after follow-up pulse rebind.
- Fcurves: 23 after follow-up pulse rebind.
- Homebrew official `ffmpeg` formula: INSTALLED with explicit user authorization.
- FFmpeg/ffprobe version: 8.1.2.
- Trusted paths: `/opt/homebrew/Cellar/ffmpeg/8.1.2_1/bin/ffmpeg` and sibling `ffprobe` (linked from `/opt/homebrew/bin`).
- Controlled MP4 encoder implementation/tests: PASSED.
- Canonical `sol_animation.mp4`: PASSED.
- Codec/pixel format: H.264 / yuv420p.
- Resolution/rate/frames: 512x512, 24 FPS, 72 frames.
- Duration: 3.000 seconds.
- File size: 138,965 bytes.
- SHA-256: `8529760344b4cc39d8cbbd85cc4b5547c5d1fbae320c263c7893f0448c8aa709`.
- ffprobe metadata validation: PASSED.
- Full ffmpeg decode to null output: PASSED.

## GUI Acceptance

- Progressive live runner: IMPLEMENTED and retained.
- Independent `C3D_SOL_DEMO` collection guard: IMPLEMENTED.
- Extension installed and enabled in an isolated temporary Blender configuration: PASSED.
- Visible Extension Panel and connected state: PASSED.
- Progressive geometry/materials/lighting/animation stages in `C3D_SOL_DEMO`: PASSED.
- Human-observed 1-72 Timeline playback and visible looping: PASSED, explicitly confirmed by the user.
- Live real Codex follow-up: PASSED.
- Live erroneous core/camera edit plus snapshot restore: PASSED.
- An initial harness attempt started playback before snapshot comparison and correctly failed; the harness was corrected to pause during construction/restore and start playback only after all checks passed.
- User scene unchanged: PASSED.

Headless frame rendering was not used as evidence for GUI acceptance. The final Timeline result is based on the user's explicit confirmation of the visible isolated Blender window.

## Safety

- Blender ran with factory startup and never opened the user's current `.blend`.
- Bridge used a random `127.0.0.1` port and one-time token.
- Token is absent from results and artifacts.
- Global Codex configuration digest remained unchanged.
- Artifact paths remained confined to the configured root.
- No arbitrary Python, shell MCP tool, `eval`, or `exec` was added.
- Encoder uses a fixed argument array with `shell=False`.
- Blender and MCP processes exited; bridge port release passed.
- GUI used temporary Blender config/scripts/datafiles/extensions roots under `/tmp`; the user's current Blender project and normal extension configuration were not opened or modified.
- GUI Bridge port `54201` was released and the temporary connection/token files were removed after confirmation.

## Artifacts

```text
artifacts/hackathon_sol_demo/sol_demo.blend
artifacts/hackathon_sol_demo/preview_polished.png
artifacts/hackathon_sol_demo/sol_animation.mp4
artifacts/hackathon_sol_demo/frames/
artifacts/hackathon_sol_demo/scene_inspection.json
artifacts/hackathon_sol_demo/render_result.json
artifacts/hackathon_sol_demo/demo_result.json
artifacts/hackathon_sol_demo/snapshot_restore_result.json
artifacts/hackathon_sol_demo/live_gui_acceptance.json
artifacts/hackathon_sol_demo/final_demo_manifest.json
```

## Closeout

Both remaining acceptance items are complete: the canonical MP4 is independently probed and fully decoded, and the visible Blender GUI Timeline was explicitly confirmed by the user. Cleanup and safety checks passed. Sprint 02D is `DONE`.
