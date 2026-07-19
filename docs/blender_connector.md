# Blender Connector

The Blender connector began as the Round 04 handshake boundary and now executes the structured Hackathon 02BC creative/render action set.

The goal is not to edit Blender scenes yet. The goal is to let the local API register, track, heartbeat, ping, and inspect a connector without requiring Blender to be installed for tests.

## Dumb Connector Principle

The Blender connector must stay small and predictable.

It may:

- Register itself with the API
- Report version and capabilities
- Send heartbeat
- Respond to ping
- Inspect basic scene object state
- Execute the narrow structured action set from Hackathon Sprint 01 when explicitly bound through the API dispatcher

It must not contain:

- Agent Runtime logic
- Provider logic
- Creative decision-making
- Business rules
- LLM calls
- Agent/provider logic or arbitrary Python execution

## Handshake Flow

```text
Blender connector
  -> build ConnectorRegistration
  -> API ConnectorService.register_connector
  -> API InMemoryConnectorStore
  -> heartbeat updates last_seen_at
  -> ping returns ConnectorPingResult
  -> inspection returns ConnectorSceneInspection
```

The Round 04 implementation is local and direct-service based. It does not require a real HTTP server.

## Current Capabilities

Supported:

- `ping`
- `heartbeat`
- `inspect_scene`
- `report_version`
- `execute_action`
- 3D curve, camera, Empty, Point/Area light creation
- Advanced Principled material subset and object parenting
- World/scene configuration and timeline keyframes
- Static render, animation render/fallback, render validation, and `.blend` checkpoint
- Stable per-object `codex3d_uuid` identity in Fake and bpy backends
- Snapshot create/list/restore/delete with canonical scene fingerprint verification
- Explicit UUID reconciliation for legacy prefixed objects

Reserved for later:

- Full Scene IR reconciliation and version history

## Package Layout

```text
connectors/blender_addon/codex3d_blender_connector/
  addon.py       # guarded Blender add-on entry points
  client.py      # registration, heartbeat, ping payload builders
  inspection.py  # empty/fake scene inspection
  manifest.py    # name, version, capabilities
  action_validation.py
  action_executor.py
  backends.py
  fake_backend.py
  bridge_server.py
  bridge_runtime.py
  request_queue.py
  protocol_compat.py
  artifact_paths.py
  smoke.py       # local direct-service handshake demo
```

## Testing Without Blender

The connector does not import `bpy` at package import time.

`addon.register()` follows Blender's lifecycle convention and returns `None`. In ordinary Python it safely performs no registration. The testable `AddonLifecycleController` owns Connect/Disconnect cleanup without requiring `bpy` at import time.

`inspect_scene(None)` returns an empty `Scene` and marks:

```text
metadata.blender_available = False
```

Tests can pass a fake bpy-like object with `context.scene.objects` to create `SceneObject` records without a real Blender runtime.

## Connector Payload Smoke

From the repository root:

```bash
PYTHONPATH=packages/protocol:connectors/blender_addon python -m codex3d_blender_connector.smoke
```

The demo:

- Builds a connector registration payload.
- Builds heartbeat and ping payloads.
- Inspects an empty scene without Blender.

## Current Non-Goals

Current non-goals are full Scene IR/version history, arbitrary Python, generalized Geometry Nodes, and remote rendering.

Hackathon Sprint 02A1 adds an authenticated localhost server, request queue, bounded `bpy.app.timers` pump, Extension Preferences/operators/Panel, and vendored packaging. Real Blender 5.1.1 verification completed with 31 successful actions and 16 inspected objects.

## Hackathon Sprint 01 Direction

The next recommended path is:

- Add snapshot/undo around action batches.
- Add stable object identity and scene reconciliation.
- Add higher-level creative primitives without bypassing structured Actions.
- Keep arbitrary Python as an escape hatch, not the primary action path.

Hackathon Sprint 02A2 adds the MCP adapter outside this package. It calls `SocketConnectorClient`; the Blender connector remains unaware of Codex, MCP, natural language, and Agent Runtime logic.

Hackathon Sprint 02BC keeps that boundary. All `bpy` reads, curve/camera creation, keyframes, rendering, pixel statistics, and checkpoint writes occur in the Blender main-thread executor. The bridge never carries image bytes and artifact paths are validated against `CODEX3D_ARTIFACT_ROOT`.

Hackathon Sprint 02D adds stable execution identity and minimal snapshots without moving business logic into the add-on. New objects receive a `codex3d_uuid` custom property; name and UUID are both inspected, while UUID is preferred for follow-up targeting. Snapshot `.blend` and JSON metadata live only under the artifact root. Restore reloads the saved file on Blender's main thread, recomputes the canonical scene fingerprint, and returns a fresh inspection. Real Blender 5.1.1 validation confirms UUID persistence through rename/save/reload and exact transform/material/camera restoration.
