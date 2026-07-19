# Architecture

Round 01 establishes the first architecture boundary for Codex3D.

```text
User / Local UI or API
  -> Agent Runtime
  -> Scene IR
  -> Structured Tools
  -> Blender Connector
  -> Blender
  -> Preview / Validation / Feedback
```

## Principles

### Blender-first

Blender is the first execution backend because it is scriptable, widely used, local, and capable of modeling, materials, lighting, cameras, rendering, and asset import.

Codex3D should prove the creative loop in Blender before expanding into other runtimes or providers.

### Modular Monolith

The early project should remain a modular monolith. Package boundaries should be clear, but local development should stay simple:

- `apps/api` for the future backend surface
- `packages/protocol` for shared data contracts
- `packages/scene_ir` for semantic world state
- `packages/agent_runtime` for planning and feedback loops
- `packages/tools` for structured operations
- `connectors/blender_addon` and `connectors/blender_worker` for Blender execution

### MCP Is A Future Adapter

MCP may become useful as an adapter surface later, especially for external tools or interoperability. It is not the internal core of Codex3D. The internal core should remain ordinary typed data, local files, and structured Python modules.

### Dumb Blender Connector

The Blender connector should stay small and predictable. It should execute structured commands, inspect scene state, render previews, and return errors.

It should not decide user intent, route providers, own business logic, or maintain long-term project memory.

### Arbitrary Python Is An Escape Hatch

Generated or arbitrary Blender Python can be useful for unusual operations, but it should not be the main path. The main path should be structured tools that can be validated, logged, tested, and rolled back.

## Near-Term Flow

The first ten rounds should move from repository scaffold to a mockable protocol, then to a local API, a Blender handshake, basic actions, preview rendering, snapshot/undo, and finally a multi-turn feedback loop.

## Live Process Boundary

Hackathon Sprint 02A1 adds the first real cross-process execution boundary:

```text
External API / future MCP adapter
  -> SocketConnectorClient
  -> 127.0.0.1 JSON-lines bridge
  -> Blender network thread (parse/auth/queue only)
  -> bpy.app.timers main-thread pump
  -> BlenderActionExecutor
  -> BpyBlenderBackend
  -> Blender
```

The API still depends only on protocol types and stdlib transport. The Blender package still does not import the API. Examples remain the composition root. The socket transport coexists with the in-process dispatcher so deterministic fake tests stay fast.

## Codex MCP Boundary

Hackathon Sprint 02A2 adds `apps/mcp` as an adapter above the API transport:

```text
Codex natural language
  -> STDIO MCP tool schemas
  -> existing Action models
  -> SocketConnectorClient
  -> live Blender bridge
```

Codex owns planning. The MCP adapter owns tool protocol, validation, forwarding, and structured errors only. It does not introduce another Agent Runtime and does not import the Blender connector or `bpy`.
