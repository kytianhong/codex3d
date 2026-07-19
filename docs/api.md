# Local API

Round 03 adds the first local API core boundary for Codex3D.

The core is dependency-free and testable without FastAPI. It is designed to sit between future local UI/API callers and the protocol layer created in Round 02.

## Goals

The Round 03 API core can:

- Create sessions
- Store messages
- Track session scene state
- Create and query local jobs
- Run a mock agent turn
- Return JSON-friendly API responses
- Offer an optional FastAPI adapter
- Register, list, lookup, heartbeat, and ping Blender connectors

It does not call Blender, GPT APIs, providers, renderers, databases, or real async workers.

## Local-First Principles

All Round 03 state is in memory and single-process only. This keeps the API boundary easy to test before persistence is introduced.

The protocol package remains the shared language for scene, action, job, asset, and error data.

## Package Layout

```text
apps/api/codex3d_api/
  models.py         # API session/message dataclasses
  store.py          # in-memory session and job stores
  service.py        # API service boundary
  mock_agent.py     # local mock agent turn
  demo_planner.py   # deterministic hackathon prompt planner
  action_store.py   # in-memory planned action and result store
  action_dispatcher.py
  serialization.py  # JSON-friendly API serialization
  fastapi_app.py    # optional FastAPI adapter
  smoke.py          # local no-network smoke demo
  connector_store.py
  connector_service.py
```

## Service, Store, Mock Agent

`Codex3DApiService` is the main entry point. It owns the high-level operations:

- `health()`
- `create_session(name)`
- `get_session(session_id)`
- `list_sessions()`
- `submit_message(session_id, request)`
- `get_job(job_id)`
- `list_session_jobs(session_id)`
- `get_session_scene(session_id)`

`InMemorySessionStore` and `InMemoryJobStore` hold local state for tests and smoke demos. They do not write to disk.

`ConnectorService` and `InMemoryConnectorStore` hold local connector registrations. They support:

- `register_connector()`
- `get_connector()`
- `list_connectors()`
- `heartbeat()`
- `ping()`

Connector registration, ping, and heartbeat do not perform network requests. They only validate and update local handshake state.

`InMemoryActionStore` saves planned `Action` objects and `ActionResult` records by session and job.

`LocalActionDispatcher` binds a connector ID to a local callable handler:

```text
Callable[[Action], ActionResult]
```

The API package does not import the Blender connector package. Examples act as the composition root and bind a connector executor to the dispatcher.

`Codex3DApiService` now also supports:

- `plan_demo_message(session_id, request)`
- `get_action(action_id)`
- `list_session_actions(session_id)`
- `list_job_actions(job_id)`
- `get_action_result(action_id)`
- `bind_connector_action_handler(connector_id, handler)`
- `execute_action(connector_id, action_id)`
- `execute_session_plan(session_id, connector_id)`

`mock_agent.py` exists only to prove the API to protocol to job to action path:

- Prompts containing `desk` or `书桌` create a mock/proposed desk object in session scene state.
- Other prompts create an `inspect_scene` mock action.
- The mock job is marked as `agent_turn` and `succeeded`.

Mock objects are marked with `metadata.mock = True` and `metadata.proposed = True`.

## Optional FastAPI Adapter

`fastapi_app.py` attempts to import FastAPI. If FastAPI is not installed, importing the module still works, but `create_app()` raises a clear runtime error.

FastAPI is not a hard dependency in Round 03.

## Endpoint Design

When FastAPI is available, the adapter exposes:

```text
GET  /health
POST /sessions
GET  /sessions
GET  /sessions/{session_id}
POST /sessions/{session_id}/messages
GET  /sessions/{session_id}/scene
GET  /sessions/{session_id}/jobs
GET  /jobs/{job_id}
POST /connectors
GET  /connectors
GET  /connectors/{connector_id}
POST /connectors/{connector_id}/heartbeat
GET  /connectors/{connector_id}/ping
```

The tests do not require a running HTTP server or FastAPI test client.

## Serialization

`api_to_dict(value)` and `api_to_json(value)` reuse the protocol serializer so API models, protocol Scene objects, Jobs, and responses can become JSON-friendly data.

## Current Non-Goals

Round 03 does not implement:

- Real HTTP server startup as a required path
- Real LLM calls
- Real Blender scene mutation or action execution
- Blender Python mutation scripts
- Web UI
- Database persistence
- Real async worker
- Provider integration
- Rendering
- Authentication or user accounts

Round 04 added connector handshake only. Later Hackathon sprints add local action dispatch, render, stable connector object UUIDs, and minimal artifact-root snapshots. The API remains independent of `bpy`; socket/MCP composition forwards the same protocol Actions to Blender.

Hackathon Sprint 02A1 adds `SocketConnectorClient` as an optional cross-process transport. It only depends on the protocol package and Python stdlib, restricts connections to `127.0.0.1`, supports hello/ping/inspection/action/batch requests, and handles correlation, partial reads, timeout, EOF, and connector-offline failures.

`LocalActionDispatcher` remains unchanged for in-process fake demos. The API does not import the Blender add-on or `bpy`; the MCP adapter reuses `SocketConnectorClient`.

Hackathon Sprint 02A2 implements that adapter in `apps/mcp`. The API transport remains the sole external-process client; MCP adds no socket or authentication implementation.

## Round 04 Usage

Round 04 connected the first Blender connector handshake boundary.

Round 05 / Hackathon Sprint 01 used the API and connector registry to introduce basic Blender action contracts. The API can support the next sprint by:

- Recording render preview jobs.
- Recording richer transaction/undo history beyond the implemented snapshot boundary.
- Returning connector health and execution capability through service methods.
- Reusing `ProtocolError` for failed dispatch or backend states.
