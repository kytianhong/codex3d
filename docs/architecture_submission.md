# Submission Architecture

## Product Loop

```text
Natural-language feedback
  -> Codex with GPT-5.6
  -> local STDIO MCP tools
  -> SocketConnectorClient
  -> authenticated 127.0.0.1 JSON-lines bridge
  -> bounded Blender main-thread pump
  -> structured BpyBlenderBackend
  -> compact inspection / render validation / snapshots
  -> next feedback turn
```

## Key Decisions

1. **Blender-first, local-first.** The creative state stays in a local `.blend`; no provider, login, or cloud database is required.
2. **Structured Actions over generated scripts.** The adapter exposes typed geometry, material, camera, render, animation, identity, and recovery tools. Arbitrary Python and shell execution are absent.
3. **A deliberately simple connector.** Agent reasoning remains in Codex. The Blender extension validates and executes actions, inspects state, and returns structured results.
4. **Main-thread correctness.** The network thread only authenticates, parses, queues, and waits. A bounded `bpy.app.timers` pump performs every Blender read and mutation.
5. **Recoverable iteration.** Stable UUIDs survive rename/save/reload. Session snapshots carry fingerprints; restore creates an immutable safety snapshot and verifies the restored scene.
6. **Delivery needs evidence.** The validator measures camera framing, collection visibility, crop, luminance, overexposure, keyframes, and output metadata rather than accepting a file merely because it exists.

## Trust Boundaries

The bridge is localhost-only. The token is an ephemeral capability and must not enter logs or release artifacts. Artifact paths are resolved beneath a configured root. MCP/API code does not import `bpy`; the extension does not import the API package.

## Judge Path

The release includes an installable Blender Extension ZIP, source bundle, curated media, installation guide, and deterministic fake-backend smoke demo. A judge can inspect the system without rebuilding, while a real Blender evaluation uses the same extension source and protocol implementation.
