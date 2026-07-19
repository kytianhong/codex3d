# Hackathon Demo

Hackathon Sprint 01 provides a deterministic, local, no-GPT demo path.

## Goal

Show the first real modeling loop:

```text
Prompt
  -> Deterministic Demo Planner
  -> Action Store
  -> Local Dispatcher
  -> BlenderActionExecutor
  -> FakeBlenderBackend
  -> Scene Inspection
```

## Standard Prompt

```text
Create a cozy wooden desk scene with a chair, lamp, and warm lighting.
```

## Command

From the repository root:

```bash
PYTHONPATH=packages/protocol:apps/api:connectors/blender_addon python examples/hackathon_sprint_01_demo.py
```

Expected summary:

```text
planner = deterministic_demo
planned_action_count = 31
succeeded_action_count = 31
failed_action_count = 0
object_count = 16
blender_backend = fake
```

Important objects:

- `C3D_Floor`
- `C3D_DeskTop`
- `C3D_ChairSeat`
- `C3D_LampBase`
- `C3D_WarmLampLight`

## Real Blender Bridge Demo

Sprint 02A1 packages the connector as a Blender Extension and exposes the same action executor over localhost.

Build and install the extension, click Connect in the Codex3D Panel, then run:

```bash
PYTHONPATH=packages/protocol:apps/api python examples/real_blender_bridge_demo.py \
  --host 127.0.0.1 --port 9876 --token "$CODEX3D_BLENDER_TOKEN"
```

Verified result on Blender 5.1.1:

```text
bridge_connected = true
backend = bpy
planned_action_count = 31
succeeded_action_count = 31
failed_action_count = 0
codex3d_object_count = 16
important_objects_present = true
```

## Hardened Sol Demo

Sprint 02D provides the current isolated presentation artifact:

```bash
python examples/sol_scene_demo.py --isolated
```

It produces an original unofficial six-way kinetic concept with 14 stable UUID objects, a layered blue energy core, six cyclic curves, studio lighting, a 72-frame Timeline, three validated previews, snapshot restore evidence, a `.blend`, and a real Codex follow-up. It does not reproduce an official logo.

Canonical files are under `artifacts/hackathon_sol_demo/`. `final_demo_manifest.json` records automated Blender validation, independently probed MP4 metadata, and the user-confirmed visible GUI Timeline acceptance.

## Not Included Yet

- GPT or broad natural-language parsing
- Full Scene IR reconciliation and version history
- Web UI
- Provider or asset download
