# Hackathon Sprint 02BC Report

Date: 2026-07-19  
Sprint: Accelerated Sol-inspired Scene, Render and Animation Vertical Slice  
Status: PARTIAL

The output is an unofficial concept demo made from original six-way radial geometry. It does not copy or trace an official OpenAI logo.

## Implemented

- Added general 3D polyline/Bezier curve creation with cyclic, bevel, resolution, and fill controls.
- Added Camera creation, focal length, active camera, and structured point/object `look_at`.
- Added Empty roots, object parenting, Point/Area lights, and World background configuration.
- Added advanced Principled base/metal/roughness/emission/transmission/alpha subset.
- Added bounded Eevee render configuration, FPS/frame range, transform/emission keyframes, interpolation, and cycle intent.
- Added still render, animation render with PNG fallback, `.blend` checkpoints, and artifact-root path confinement.
- Added render statistics: dimensions, bytes, active camera, luminance, nonblack/nontransparent ratios, projected subject count, frame range, keyframes, and fcurves.
- Expanded MCP from 9 to 18 structured tools and added optional validated PNG image content.
- Added deterministic isolated and progressive live GUI runner paths.

## Automated Tests

- Baseline before work: 123 passed, 1 skipped.
- Final default suite: 137 passed, 2 skipped.
- Explicit real Sol test: PASSED, 1 test in 26.92 seconds.
- Protocol round trip, path escape rejection, Fake backend state, executor failures, MCP schema/mapping/image content, batch fail-fast, and legacy tests pass.

## Extension Build

- Python build: PASSED, 28 validated files.
- Artifact: `dist/codex3d_blender_connector-0.1.0.zip`.
- Blender 5.1.1 official `extension build`: PASSED.
- Vendored protocol and new connector modules are included.

## Real Blender Vertical Slice

- Blender: 5.1.1, backend `bpy`, isolated factory startup.
- Scene: 13 `C3D_SOL_` objects, including 6 independent cyclic curves, energy core, outer ring, shadow plane, Area/Point lights, camera, and animation root.
- Geometry/material/lighting/animation structured actions: 40/40 succeeded.
- Initial preview: 512x512, 290,726 bytes, mean luminance 0.1426, nonblack ratio 0.6509, 9 projected subjects visible.
- Follow-up preview: 512x512, 292,124 bytes, mean luminance 0.1448, nonblack ratio 0.6394, 9 projected subjects visible.
- Animation: 72/72 PNG frames, 24 FPS, 21,146,623 total bytes, 23 keyframes and 22 fcurves at render time.
- Final checkpoint rebinds the brighter core pulse, reporting 26 inserted keyframe operations and 23 fcurves.

## Real Codex Follow-up

Status: PASSED.

Observed sequence:

```text
inspect_scene
assign_material (brighter core)
assign_material (warmer outer ring)
transform_object (lower camera + look_at)
render (follow-up preview)
inspect_scene
```

Global Codex configuration was unchanged; the one-off MCP configuration was ephemeral.

## Animation And GUI Status

- MP4: NOT PRODUCED. Blender reports no FFmpeg build support.
- PNG sequence fallback: PASSED, complete and playable as frames.
- Automatic headless Timeline evaluation: PASSED through rendered frames.
- Live GUI progressive runner: IMPLEMENTED.
- GUI Panel connection and visible Timeline playback: MANUAL_ACCEPTANCE_PENDING.

Per Sprint rules, FFmpeg fallback keeps the overall status PARTIAL even though the complete PNG sequence passed.

## Safety

- Bridge bound only to random `127.0.0.1` port.
- Token absent from structured results and artifacts.
- Global Codex config digest unchanged.
- No user `.blend` opened in isolated mode.
- Render/checkpoint paths confined to `CODEX3D_ARTIFACT_ROOT`; absolute paths and `..` rejected.
- No arbitrary Python, shell, `eval`, or `exec` MCP capability.
- MCP/API/protocol packages do not import `bpy`.
- Blender return code 0, MCP process reaped, and bridge port released.

## Artifacts

```text
artifacts/hackathon_sol_demo/sol_demo.blend
artifacts/hackathon_sol_demo/preview_initial.png
artifacts/hackathon_sol_demo/preview_followup.png
artifacts/hackathon_sol_demo/frames/
artifacts/hackathon_sol_demo/scene_inspection.json
artifacts/hackathon_sol_demo/render_result.json
artifacts/hackathon_sol_demo/demo_result.json
```

## Next

Complete manual live GUI playback acceptance, add snapshot/undo, then add stable object identity and Scene IR reconciliation. MP4 can become DONE either by validating a Blender build with FFmpeg or by adding a separately approved media-encoding boundary outside MCP.
