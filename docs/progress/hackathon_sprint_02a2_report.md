# Hackathon Sprint 02A2 Report

Date: 2026-07-19

Sprint: Hackathon Sprint 02A2 - Codex MCP Adapter + Direct Natural-Language Blender Control

Status: DONE

## Completed

- Added a dependency-free STDIO MCP server at `apps/mcp/codex3d_mcp`.
- Added initialize, ping, tools/list, tools/call, JSON-RPC errors, notifications, and module entrypoint support.
- Added nine documented structured Blender tools with closed JSON Schemas, units, ranges, enums, and MCP safety annotations.
- Reused `SocketConnectorClient` and existing `Action`, `ActionResult`, bridge, validation, executor, and backend boundaries.
- Added structured tool errors and recursive token redaction.
- Added deterministic stub and real fake-socket MCP tests.
- Added real Blender STDIO MCP and real Codex natural-language demos.
- Added verified optional `codex mcp add/get/list/remove` documentation without changing the user's global configuration.

## Architecture Result

```text
Natural language Codex
  -> local STDIO MCP
  -> SocketConnectorClient
  -> authenticated localhost bridge
  -> Blender main-thread executor
  -> bpy
  -> inspection
```

No second Agent Runtime or Blender transport was introduced.

## Automated Tests

Status: PASSED

Command: `python -m pytest`

Result: `123 passed`

Coverage includes MCP initialize/list/call, module STDIO entrypoint, every tool's validation and Action mapping, batch success/fail-fast, bridge offline/authentication/timeout/malformed response, token redaction, fake socket execution, and all previous tests.

## Real Blender MCP Demo

Status: PASSED

- Blender version: 5.1.1
- MCP protocol: 2025-06-18
- Tool count: 9
- Created: `C3D_MCP_DemoCube`
- Final deterministic location: approximately `[0.35, 0, 1]`
- Final scale: approximately `[1.25, 0.8, 1.5]`
- Material: `C3D_MCP_DemoMaterial`
- Final inspection: PASSED

## Codex Natural-Language Demo

Status: PASSED

An ephemeral, read-only `codex exec` run used only the one-off MCP configuration. Codex inspected the live scene, moved `C3D_MCP_DemoCube` to approximately `[0.6, 0, 1.2]`, assigned `C3D_MCP_FollowUpMaterial`, inspected again, and reported the verified result.

Initial non-interactive attempts revealed missing MCP safety annotations and were cancelled before scene mutation. After adding accurate read-only/destructive/idempotent/open-world annotations, the final run passed.

## Codex CLI Verification

Status: PASSED

The installed CLI reported support for `mcp add/get/list/remove`. The exact STDIO add command was exercised in an isolated `/private/tmp` `CODEX_HOME` with a fake token, inspected with get/list, then removed. The real global Codex configuration was not modified.

## Security Checks

- Bind/connect host remains `127.0.0.1` only.
- Token absent from logs, tool output, errors, and test snapshots.
- No `bpy` import in MCP/API/protocol packages.
- No arbitrary Python, `eval`, `exec`, or shell execution tool.
- MCP failures return structured errors without terminating the server.
- Blender Actions still pass through connector validation and main-thread execution.

## Known Limitations

- The bridge token is a local shared secret; optional `codex mcp add --env` stores its value in Codex configuration.
- Stable object UUID, render preview, snapshot/undo, camera composition, and advanced geometry remain open.
- Sprint 02A1's manual visual Install from Disk/Panel walkthrough remains separately pending.

## Next Sprint

Hackathon Sprint 02B: Creative Geometry + Materials + Camera + Render Preview.
