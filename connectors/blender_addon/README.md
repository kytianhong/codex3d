# Blender Add-on Connector

Round 04 adds the first minimal Blender-side connector package.

The connector stays deliberately small. It can build registration, heartbeat, ping, and scene inspection payloads. It does not contain Agent Runtime logic, provider logic, product decision-making, scene mutation, or rendering.

The package guards `bpy` imports so tests can run in ordinary Python without Blender.

Run the local no-Blender smoke demo from the repository root:

```bash
PYTHONPATH=packages/protocol:apps/api:connectors/blender_addon python -m codex3d_blender_connector.smoke
```

