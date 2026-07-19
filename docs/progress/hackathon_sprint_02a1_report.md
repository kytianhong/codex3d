# Hackathon Sprint 02A1 Report

Date: 2026-07-19

Sprint: Hackathon Sprint 02A1 - Installable Blender Add-on + Localhost Live Bridge

Status: PARTIAL - implementation and real bridge execution passed; manual Install from Disk and visual Panel walkthrough remain pending.

## Completed

- Added bridge protocol v1.0 with correlated hello, ping, inspection, single-action, and batch requests.
- Added authenticated JSON-lines server bound only to `127.0.0.1`.
- Added a bounded Blender main-thread request pump using `bpy.app.timers`.
- Added stdlib `SocketConnectorClient` with timeout, partial-read, EOF, and offline handling.
- Upgraded the add-on lifecycle with Preferences, Connect/Disconnect/Copy operators, and a 3D View Panel.
- Added deterministic Extension ZIP build with vendored protocol and no workspace path dependency.
- Added external real-Blender demo and protected connection-info smoke host.

## Architecture Decisions

- Network threads only authenticate, parse, enqueue, wait, and write responses.
- All real `bpy` inspection and mutation runs from the main-thread pump.
- The bridge accepts structured Actions only and exposes no Python or shell execution.
- Development and packaged extensions share the same connector source through `protocol_compat.py`.
- LocalActionDispatcher remains available for fake/in-process tests; socket transport is additive.
- Recorded the boundary in `ADR-0002-localhost-main-thread-bridge.md`.

## Changed Files

- `packages/protocol/codex3d_protocol/bridge.py`
- `apps/api/codex3d_api/connector_transport.py`
- `connectors/blender_addon/codex3d_blender_connector/bridge_server.py`
- `connectors/blender_addon/codex3d_blender_connector/bridge_runtime.py`
- `connectors/blender_addon/codex3d_blender_connector/request_queue.py`
- `connectors/blender_addon/codex3d_blender_connector/addon.py`
- `scripts/build_blender_extension.py`
- `examples/real_blender_bridge_demo.py`
- `examples/blender_bridge_host_smoke.py`
- bridge, client, lifecycle, build, and integration tests

## Automated Tests

Status: PASSED

Command: `python -m pytest`

Result: `84 passed`

The suite includes the original 49 tests plus bridge protocol, authentication, malformed/oversized frames, port conflict, timeout/offline, partial TCP reads, pump thread identity, bounded pump work, shutdown wakeup, add-on lifecycle, deterministic packaging, packaged import, and 31-action fake bridge integration.

## ZIP Build

Status: PASSED

Pure Python build: `dist/codex3d_blender_connector-0.1.0.zip`

Validation: 27 files; required root files and vendored protocol present; tests, caches, and absolute workspace paths absent.

## Blender CLI Extension Build

Status: PASSED

- Blender official validate: PASSED
- Blender official build: PASSED
- Preserved output: `dist/codex3d_blender_connector-0.1.0-blender-cli.zip`

## Blender GUI Install

Status: PARTIAL

The official `extension install-file -r user_default -e` command installed and enabled the package. A Blender 5.1.1 GUI process loaded the extension, and a headless check confirmed the add-on and `CODEX3D_PT_bridge` Panel class were registered. The manual Preferences `Install from Disk` click path and visual Panel walkthrough were not performed.

## Real Bridge Connection

Status: PASSED

The external process connected to the running Blender GUI bridge at `127.0.0.1:9876`, completed hello/ping, and reported Blender 5.1.1 with backend `bpy`.

## Real 31-Action Execution

Status: PASSED

Result: 31 succeeded, 0 failed, 16 Codex3D objects, all important object names present. Final measured round trip: 441.22 ms.

## Disconnect Cleanup

Status: PASSED

The Blender main thread called `controller.disconnect()`, removed the timer, closed the listener, exited cleanly, and a post-disconnect client attempt confirmed port 9876 was offline.

## Known Limitations

- Manual visual Panel acceptance remains pending.
- The internal LicenseRef is not a confirmed public release license.
- Transport is localhost TCP only; there is no MCP adapter yet.
- Render preview, camera framing, snapshot/undo, and stable object identity remain unimplemented.
- Object names remain the temporary identity for the deterministic demo.

## Hackathon Readiness

The real external-process-to-Blender modeling path is working. The next user-facing gap is direct Codex/MCP invocation; the next safety gap is snapshot/undo before broader editing.

## Next Sprint

Hackathon Sprint 02A2: Codex MCP Adapter + Direct Natural-Language Blender Control.
