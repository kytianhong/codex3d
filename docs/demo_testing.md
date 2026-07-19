# Codex3D Demo Testing

Demo Gate 0 is the automated preflight for the current local chain:

```text
Natural language -> Codex -> STDIO MCP -> localhost bridge
  -> Blender main-thread executor -> bpy -> scene inspection
```

It validates the capabilities already implemented. Later render, animation, snapshot, and identity additions are covered by their own explicit regressions rather than changing the original Gate 0 contract.

## Sprint 02BC Vertical Slice

Run the complete isolated scene, render, animation, and real Codex follow-up:

```bash
python examples/sol_scene_demo.py --isolated
```

The canonical output is `artifacts/hackathon_sol_demo/`. Static validation checks dimensions, bytes, active camera, mean luminance, nonblack/nontransparent ratios, and projected subject visibility. Animation validation checks frame range, frame count, keyframe count, fcurve count, and total bytes.

The explicit real-Blender test omits Codex to keep the integration layer deterministic:

```bash
CODEX3D_RUN_SOL_DEMO_TESTS=1 \
python -m pytest tests/integration/test_sol_scene_demo.py
```

If Blender was built without FFmpeg, the backend produces all 72 PNG frames in `frames/` and marks the animation fallback. The Sprint remains `PARTIAL` rather than claiming MP4 success.

## Sprint 02D Hardening

The same isolated command now also verifies:

- every `C3D_SOL_` object has a persistent `codex3d_uuid`;
- a deliberate core/camera mutation changes canonical state;
- snapshot restore returns the original fingerprint, object transforms, materials, and active camera;
- `preview_polished.png` passes the existing render validator without relaxed thresholds;
- real Codex performs inspect, material, transform, render, inspect;
- child processes stop and the random bridge port is released.

MP4 packaging is a separate controlled boundary, never an MCP shell tool:

```bash
CODEX3D_FFMPEG_PATH=/trusted/path/to/ffmpeg \
PYTHONPATH=packages/tools python scripts/package_sol_animation.py
```

The command rejects path escape, frame gaps, non-PNG inputs, untrusted executable names, and outputs outside `artifacts/hackathon_sol_demo/`. Sprint 02D closeout used the explicitly authorized Homebrew FFmpeg 8.1.2 installation, verified all 72 decoded frames with `ffprobe`, performed a full decode, and wrote the MP4 metadata/checksum to the final manifest.

For visible GUI acceptance, connect the Extension in a Blender GUI and run:

```bash
python examples/sol_scene_demo.py --pause 1.0
```

Use `--replace-demo-collection` only after confirming the existing `C3D_SOL_DEMO` collection is demo-owned. Sprint 02D closeout completed the human-visible staged viewport and 72-frame Timeline acceptance in an isolated Blender configuration. Headless frame rendering was not used as evidence.

## Ordinary Test Suite

Run the dependency-free suite without starting Blender:

```bash
python -m pytest
```

The real Blender integration test is skipped unless explicitly enabled.

## Full Gate

Run the baseline, isolated Blender test, STDIO MCP flow, and ephemeral Codex acceptance:

```bash
python scripts/run_demo_gate_0.py
```

The runner requires Blender at `/Applications/Blender.app/Contents/MacOS/Blender` by default. Use `--blender PATH` for another local executable.

The runner starts Blender with `--factory-startup --background`, chooses a temporary loopback port, creates a one-time token, and never opens an existing `.blend`. It does not write Codex MCP configuration.

## Explicit Integration Test

To exercise the same real integration through pytest:

```bash
CODEX3D_RUN_REAL_BLENDER_TESTS=1 \
python -m pytest tests/integration/test_demo_gate_0.py
```

Without that environment variable, the test is skipped. The test uses a temporary artifact directory and invokes the Gate runner with its nested baseline disabled.

## Test Scene

The isolated scene contains only these Gate-created objects in addition to Blender factory defaults:

- `C3D_GATE0_Core`: sphere at the center.
- `C3D_GATE0_Ray_01` through `C3D_GATE0_Ray_06`: six stable cube-based radial parts.
- `C3D_GATE0_WarmLight`: warm point light.

The geometry is an original radial systems check, not a reproduction of any official logo. All test-owned objects and materials use the `C3D_GATE0_` prefix.

## Artifacts

The default run creates:

```text
artifacts/demo_gate_0/codex3d_gate0.blend
artifacts/demo_gate_0/readiness.json
artifacts/demo_gate_0/gate_0_result.json
artifacts/demo_gate_0/blender.log
```

`readiness.json` uses only `READY`, `PARTIAL`, `MISSING`, and `NOT_RUN`. The result JSON records test counts, MCP call evidence, scene assertions, configuration integrity, and cleanup status. Neither artifact contains the bridge token.

## Safety And Cleanup

- Bridge binding is fixed to `127.0.0.1`.
- The socket port is randomly selected for each run.
- The HMAC token exists only in child-process environments.
- MCP exposes structured Blender tools only; no Python or shell tool exists.
- MCP, API, and protocol packages do not import `bpy`.
- Blender is stopped even when a check fails, and the runner verifies port release.
- The global `~/.codex/config.toml` digest must remain unchanged.
- The `.blend` artifact is written to the dedicated artifact directory and never overwrites a user file.

If Codex CLI is unavailable, real Blender and direct MCP checks can still run, but natural-language control is `NOT_RUN` and the Gate result is `PARTIAL`.
