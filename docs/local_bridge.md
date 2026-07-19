# Local Blender Bridge

Hackathon Sprint 02A1 adds a process boundary between an external Codex3D client and an open Blender process.

## Flow

```text
External Python process
  -> SocketConnectorClient
  -> UTF-8 JSON-lines over 127.0.0.1
  -> BridgeServer network thread
  -> authenticated PendingBridgeRequest queue
  -> bpy.app.timers main-thread pump
  -> BlenderActionExecutor / BpyBlenderBackend
  -> BridgeResponse
```

The socket thread never calls the executor, reads live Blender scene state, or mutates `bpy`. `BlenderBridgeRuntime.pump_once()` is the only request execution entry point and is registered with `bpy.app.timers` at a default 0.1 second interval. A tick processes at most four requests.

## Wire Protocol

Protocol version: `1.0`.

Each frame is one JSON object followed by one newline. Frames are limited to 2 MiB. Supported request types are:

- `hello`
- `ping`
- `inspect_scene`
- `execute_action`
- `execute_action_batch`

Every response repeats the request's `request_id`. Batch execution is ordered and fail-fast, and reports executed, succeeded, failed, and unexecuted counts.

## Authentication

- The server only accepts `127.0.0.1`; `0.0.0.0`, LAN, and public binds are rejected.
- Every request carries a non-empty token.
- Tokens are compared with `hmac.compare_digest`.
- Tokens are not included in responses, error details, or normal logs.
- The Blender Panel masks the token and copies it only when the user explicitly requests connection info.

This is a local process boundary, not a remote security protocol. Sprint 02A1 does not add TLS, OAuth, LAN access, or public access.

## Lifecycle

Connect creates one listener and one main-thread timer. Repeated Connect calls reuse the running server. Disconnect and add-on unregister stop the timer, close the listener and client sockets, wake pending requests with a shutdown error, and join network threads with a timeout.

Default settings:

```text
host = 127.0.0.1
port = 9876
connect timeout = 2 seconds
request timeout = 60 seconds
timer interval = 0.1 seconds
max requests per tick = 4
max frame = 2 MiB
```

## External Client

```python
from codex3d_api import SocketConnectorClient

with SocketConnectorClient(port=9876, token="...") as client:
    print(client.hello())
    print(client.ping())
    inspection = client.inspect_scene()
```

`SocketConnectorClient` uses only Python's standard library and correctly handles partial TCP reads, EOF, timeouts, offline connectors, and response correlation.

## Next Adapter

Sprint 02A2 can expose MCP tools that call `SocketConnectorClient`. The MCP layer must not duplicate the Blender transport, executor, or action validation.
