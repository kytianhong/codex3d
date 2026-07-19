# Codex3D Codex MCP Adapter

Hackathon Sprint 02A2 adds a local STDIO MCP server that lets Codex plan in natural language and invoke the existing structured Blender Actions.

## Architecture

```text
Codex natural language planning
  -> codex3d_mcp STDIO JSON-RPC server
  -> SocketConnectorClient
  -> authenticated 127.0.0.1 bridge
  -> Blender main-thread pump
  -> BlenderActionExecutor
  -> bpy
```

The MCP adapter has no Agent Runtime, socket implementation, HMAC code, Blender executor, or `bpy` import. It validates tool arguments, creates existing `Action` objects, calls `SocketConnectorClient`, and returns structured results.

## Start Directly

```bash
export CODEX3D_BRIDGE_HOST=127.0.0.1
export CODEX3D_BRIDGE_PORT=9876
export CODEX3D_BRIDGE_TOKEN="<token copied from Blender>"
export CODEX3D_ARTIFACT_ROOT="/absolute/path/to/a/dedicated/artifact/root"
export PYTHONPATH="/Users/kytianhong/CodeProject/Codex3D/codex3d/packages/protocol:/Users/kytianhong/CodeProject/Codex3D/codex3d/apps/api:/Users/kytianhong/CodeProject/Codex3D/codex3d/apps/mcp"
/opt/anaconda3/bin/python -m codex3d_mcp
```

The process waits for newline-delimited MCP JSON-RPC messages on stdin. It writes protocol messages only to stdout.

## Optional Codex Registration

The following command shape was verified against the installed local `codex mcp add --help` and executed successfully in an isolated temporary `CODEX_HOME`. It was not applied to the user's real global Codex configuration.

```bash
export CODEX3D_BRIDGE_TOKEN="<token copied from Blender>"

codex mcp add codex3d \
  --env CODEX3D_BRIDGE_HOST=127.0.0.1 \
  --env CODEX3D_BRIDGE_PORT=9876 \
  --env CODEX3D_BRIDGE_TOKEN="$CODEX3D_BRIDGE_TOKEN" \
  --env PYTHONPATH=/Users/kytianhong/CodeProject/Codex3D/codex3d/packages/protocol:/Users/kytianhong/CodeProject/Codex3D/codex3d/apps/api:/Users/kytianhong/CodeProject/Codex3D/codex3d/apps/mcp \
  -- /opt/anaconda3/bin/python -m codex3d_mcp
```

This stores the provided environment values in Codex MCP configuration. Treat the local bridge token as a secret and rotate it from Blender when needed.

Verified inspection commands:

```bash
codex mcp list --json
codex mcp get codex3d --json
```

Optional removal:

```bash
codex mcp remove codex3d
```

## Tools

| Tool | Purpose |
|---|---|
| `blender_ping` | Verify bridge/backend versions and liveness |
| `blender_inspect_scene` | Read live object names, transforms, dimensions, materials, and lights |
| `blender_create_primitive` | Create cube, cylinder, sphere, plane, or point light |
| `blender_transform_object` | Update transform fields and optional camera/light `look_at` |
| `blender_rename_object` | Rename an existing object |
| `blender_delete_object` | Delete one named object |
| `blender_assign_material` | Assign Principled base, metal, roughness, emission, transmission, and alpha subset |
| `blender_set_point_light` | Update point-light color and/or energy |
| `blender_create_curve` | Create general polyline/Bezier 3D curves with cyclic and bevel controls |
| `blender_create_camera` | Create and activate a focal-length camera with structured `look_at` |
| `blender_set_light` | Update Point/Area light color, energy, and Area size |
| `blender_set_parent` | Parent an object while preserving its world transform |
| `blender_configure_world` | Set World background color and strength |
| `blender_configure_scene` | Configure Eevee resolution, samples, FPS, transparency, and frame range |
| `blender_keyframe_object` | Insert transform or emission keyframes with interpolation/cycle settings |
| `blender_render` | Render still PNG or animation under the artifact root and return validation statistics |
| `blender_save_checkpoint` | Save a `.blend` checkpoint under the artifact root |
| `blender_create_snapshot` | Save a restorable `.blend` plus canonical fingerprint and UUID inventory |
| `blender_list_snapshots` | List artifact-root snapshot metadata |
| `blender_restore_snapshot` | Restore a snapshot and return verified state plus fresh inspection |
| `blender_delete_snapshot` | Delete one snapshot and its metadata |
| `blender_reconcile_object_ids` | Explicitly assign UUIDs to legacy objects matching a name prefix |
| `blender_execute_batch` | Run ordered Action objects fail-fast, then inspect |

Distances and dimensions are meters. Rotations are Euler radians. Scale is unitless. Material and light colors are linear values in `[0, 1]`. Creation results and inspection include stable `codex3d_uuid` values. Transform and material tools prefer `target_uuid` when supplied and retain `target_name` as a readable fallback.

Tools include MCP safety annotations. Ping and inspection are read-only; delete, checkpoint, and generic batch are marked destructive. Render is non-destructive and idempotent because it cannot write outside `CODEX3D_ARTIFACT_ROOT`. All tools declare a closed JSON Schema with explicit enums and ranges.

Artifact actions reject absolute paths, `..`, unsupported suffixes, and resolved paths outside `CODEX3D_ARTIFACT_ROOT`. The Blender bridge returns only relative paths and metadata. For still PNGs, MCP can additionally return image content after validating the same root boundary; set `CODEX3D_MCP_INCLUDE_IMAGES=0` to disable this for large automated runs.

## Natural-Language Examples

```text
Inspect the Blender scene and create a cube named C3D_MCP_DemoCube at [0, 0, 1] meters.
```

```text
Move C3D_MCP_DemoCube to [0.6, 0, 1.2] and give it a red material with roughness 0.28.
```

Codex remains the planner. The MCP adapter never interprets broad prompts itself.

## Demo

With the Blender bridge connected:

```bash
PYTHONPATH=packages/protocol:apps/api:apps/mcp \
python examples/mcp_real_blender_demo.py \
  --connection-info /private/tmp/codex3d_blender_bridge.json
```

The real demo initializes MCP, lists tools, creates `C3D_MCP_DemoCube`, transforms and scales it, assigns material, applies a follow-up position change, and verifies the final scene.

## Errors And Security

Tool failures use `isError=true` with structured `code`, `message`, and scrubbed `details`. Offline, authentication, timeout, malformed bridge responses, invalid arguments, and failed Actions do not crash the STDIO server.

- Host is restricted to `127.0.0.1`.
- Token is never returned from MCP tools or included in errors.
- No arbitrary Python, `eval`, `exec`, shell, or file tools exist.
- The MCP package does not import `bpy` or the Blender connector package.
- Blender validation and main-thread execution remain authoritative.
- Render, checkpoint, and snapshot paths are confined to the configured artifact root.
- Snapshot tools use generated IDs and never accept arbitrary filesystem paths.
