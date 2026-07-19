# ADR-0002: Localhost Bridge With Main-Thread Execution

Date: 2026-07-19

Status: Accepted

## Context

The Sprint 01 dispatcher invokes a connector handler in the same Python process. A real Blender GUI and the Codex3D API run in separate processes, and Blender scene reads and mutations are not safe from an arbitrary socket thread.

## Decision

- Use versioned UTF-8 JSON-lines over TCP on `127.0.0.1` only.
- Authenticate every request with a locally generated token compared by `hmac.compare_digest`.
- Let network threads accept, parse, authenticate, enqueue, wait, and write responses only.
- Execute all `bpy` work from a bounded `bpy.app.timers` main-thread pump.
- Reuse existing `Action`, `ActionResult`, validation, executor, and backend contracts.
- Keep `SocketConnectorClient` outside the Blender package so a future MCP adapter can reuse it.
- Retain the in-process dispatcher for deterministic fake tests.

## Consequences

The Blender UI remains responsive and the socket boundary is independently testable without `bpy`. Batch execution is ordered and fail-fast. The bridge is intentionally local and does not provide remote transport, TLS, or arbitrary Python execution.

Shutdown must coordinate the timer, listener, client sockets, pending requests, and bounded thread joins. Any future transport must preserve the main-thread execution guarantee.
