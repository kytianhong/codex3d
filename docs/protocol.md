# Protocol Schema

Round 02 implements the first concrete Codex3D protocol layer in `packages/protocol/codex3d_protocol`.

The protocol is intentionally local-first and dependency-free. It uses Python standard-library `dataclasses`, `enum`, `typing`, `datetime`, `uuid`, and `json`. It does not use Pydantic yet.

The goal is to give future API, Scene IR, Agent Runtime, Blender Connector, Job, Asset, and Validator modules a shared language without binding them to raw Blender internals.

## Modules

| Module | Purpose |
|---|---|
| `common.py` | Shared primitive types, units, timestamps, and readable unique IDs |
| `scene.py` | Scene, object, relation, and constraint protocol data |
| `actions.py` | Structured action and tool-call protocol between planning and execution |
| `jobs.py` | Local asynchronous job data and status transitions |
| `assets.py` | Asset records, source details, license, and provenance |
| `connectors.py` | Connector registration, heartbeat, ping, and inspection protocol data |
| `bridge.py` | Versioned localhost request/response envelopes for cross-process execution |
| `errors.py` | Serializable protocol error data |
| `serialization.py` | JSON-friendly dataclass and enum serialization helpers |

## Common Types

`UnitSystem` currently uses meters.

`Vector3` stores `x`, `y`, and `z`.

`Transform` stores:

- `location`
- `rotation_euler`
- `scale`

`Dimensions` stores:

- `width`
- `depth`
- `height`

`Metadata` is a `dict[str, Any]` escape valve for non-core data while schemas are still stabilizing.

`utc_now_iso()` creates UTC timestamps.

`new_id(prefix)` creates readable unique IDs such as `scene_<uuid>` or `object_<uuid>` without needing a database.

## Scene Schema

`Scene` is the top-level semantic scene record:

- `id`
- `name`
- `unit_system`
- `objects`
- `relations`
- `constraints`
- `version`
- `created_at`
- `updated_at`
- `metadata`

`SceneObject` represents a stable semantic object:

- `id`
- `label`
- `semantic_type`
- `source_type`
- `blender_uuid`
- `transform`
- `dimensions`
- `parent_id`
- `part_ids`
- `metadata`

`Relation` describes object-to-object relationships with types such as:

- `on_top_of`
- `inside`
- `near`
- `facing`
- `attached_to`
- `left_of`
- `right_of`

`Constraint` describes requirements the system should preserve or validate:

- `lock_position`
- `lock_scale`
- `lock_material`
- `preserve_relation`
- `avoid_collision`
- `keep_visible`

## Action Schema

`Action` describes a structured operation derived from user intent. Supported action types include:

- `create_object`
- `modify_object`
- `delete_object`
- `transform_object`
- `assign_material`
- `place_object`
- `import_asset`
- `render_preview`
- `inspect_scene`
- `snapshot_scene`
- `restore_snapshot`
- `list_snapshots`
- `delete_snapshot`
- `reconcile_object_ids`
- `configure_scene`
- `configure_world`
- `set_parent`
- `keyframe_object`
- `save_checkpoint`

`ToolCall` describes the concrete tool invocation associated with an action. It records a tool name, action ID, arguments, timestamp, and metadata.

`ActionResult` records whether the action succeeded or failed, which objects were created, modified, or deleted, any output data, and optional `ProtocolError`.

Hackathon Sprint 01 defines executable parameter contracts for:

- `create_object`
- `transform_object`
- `modify_object`
- `delete_object`
- `assign_material`

The protocol model is still the same `Action` and `ActionResult`; execution lives in the connector and API dispatch layers.

## Job Schema

`Job` represents a local asynchronous unit of work. Job types include:

- `agent_turn`
- `blender_action`
- `render_preview`
- `asset_search`
- `asset_generation`
- `asset_import`
- `validation`

Job statuses include:

- `queued`
- `running`
- `waiting`
- `succeeded`
- `failed`
- `cancelled`

The dataclass includes small state helpers such as `mark_running()`, `mark_succeeded()`, `mark_failed()`, and `cancel()`. These helpers only update local job data; they do not run a real queue.

## Asset Schema

`Asset` records reusable or imported 3D assets:

- `id`
- `name`
- `format`
- `source_type`
- `local_path`
- `source_url`
- `dimensions`
- `provenance`
- `tags`
- `metadata`

Supported source types:

- `local`
- `external_search`
- `generated`

`Provenance` captures:

- `source_url`
- `author`
- `license`
- `provider`
- `prompt`
- `search_query`
- `cost_usd`
- `metadata`

Round 02 models provider-related fields but does not connect to any provider.

## Error Schema

`ProtocolError` is a serializable error record, not a replacement for Python exceptions.

Supported error codes include:

- `invalid_schema`
- `object_not_found`
- `action_failed`
- `job_failed`
- `provider_failed`
- `validation_failed`
- `render_failed`
- `unsupported_operation`

Supported severities:

- `info`
- `warning`
- `error`
- `fatal`

## Connector Schema

Round 04 adds `connectors.py` for the API to Blender connector handshake.

`ConnectorRegistration` records a local connector:

- `id`
- `connector_type`
- `name`
- `version`
- `capabilities`
- `status`
- `created_at`
- `last_seen_at`
- `metadata`

Connector types include:

- `blender_addon`
- `blender_worker`
- `local_simulated`

Connector statuses include:

- `registered`
- `online`
- `stale`
- `offline`
- `error`

Supported Round 04 capabilities:

- `ping`
- `heartbeat`
- `inspect_scene`
- `report_version`

Current later-sprint capabilities:

- `execute_action`
- `render_preview`
- `snapshot_scene`
- `restore_snapshot`

`ConnectorHeartbeat` updates connector liveness and `last_seen_at`.

`ConnectorPing` and `ConnectorPingResult` describe local ping/pong checks. Missing connectors return a failed result with a `ProtocolError`.

`ConnectorSceneInspection` wraps a `Scene` produced by connector inspection. In Round 04 this can be an empty no-Blender scene or a fake-bpy scene used for tests.

`ConnectorActionRequest` and `ConnectorActionResponse` wrap an `Action` and `ActionResult` for future connector transport. Hackathon Sprint 01 still uses direct local dispatch, not HTTP/WebSocket transport.

## Serialization

`to_dict(value)` converts dataclasses, enums, lists, tuples, dictionaries, and primitives into JSON-friendly data.

`to_json(value)` serializes protocol objects to JSON strings.

`from_dict(cls, data)` supports simple dataclass reconstruction for the current schema set, including nested dataclasses, enums, lists, dictionaries, and optional values.

## Current Non-Goals

Round 02 does not implement:

- FastAPI routes
- OpenAPI generation
- Pydantic models
- Blender action execution calls
- GPT or provider calls
- Real job runner
- Scene reconciliation against Blender
- Validation logic
- Render execution
- Asset download or import

Round 04 adds connector handshake protocol only. It still does not execute Blender actions or mutate real Blender scenes.

Hackathon Sprint 01 adds action execution through fake backend and guarded bpy backend paths. Later sprints add render, localhost transport, minimal snapshots, and persistent Blender object UUIDs without changing the core `Action`/`ActionResult` boundary.

Hackathon Sprint 02A1 adds bridge protocol `1.0`. `BridgeRequest` carries a correlated request ID, message type, token, timestamp, and payload. `BridgeResponse` repeats the request ID and carries a JSON-friendly payload or `ProtocolError`. Supported messages are `hello`, `ping`, `inspect_scene`, `execute_action`, and `execute_action_batch`.

The wire adapter reuses `Action`, `ActionResult`, `ConnectorSceneInspection`, `ProtocolError`, `to_dict`, and `from_dict`; it does not create a second action model or use pickle.

## MCP Adapter

Hackathon Sprint 02A2 exposes the existing protocol through STDIO MCP without adding protocol dataclasses or another planner. The MCP tools produce the existing `Action` types and return serialized `ActionResult` and `ConnectorSceneInspection` records.

The MCP boundary adds JSON Schema descriptions and tool safety annotations, but connector-side Action validation remains authoritative. `blender_execute_batch` accepts the allowlisted execution/render/snapshot Action types and returns ordered results, counts, and a final scene inspection.

Hackathon Sprint 02D uses `SceneObject.blender_uuid` for the persistent `codex3d_uuid` custom property and includes the UUID in inspection and `ActionResult.output`. Snapshot Actions carry generated snapshot IDs rather than arbitrary paths; connector results include fingerprint, object UUID inventory, file size, active camera, and post-restore inspection. Full Scene IR reconciliation remains outside this protocol increment.

## Round 03 Usage

Round 03 should use these protocol dataclasses as the shared data contract for the first local API surface:

- Session creation can reference `Scene`.
- Message submission can create an `agent_turn` `Job`.
- Mock planning can return an `Action`.
- Job polling can expose `JobStatus` and `ActionResult`.
- API errors can return `ProtocolError`.

The API layer may later add Pydantic adapters, but the internal protocol should remain a small, testable, dependency-free core until the need is clear.

## Hackathon Sprint 01 Action Contract

`dimensions` take precedence over `scale` for mesh primitive physical size when both are provided. `scale` is still recorded and applied, but final intended physical size is expressed by `dimensions`.

All vector fields must contain exactly three finite numbers:

- `location`
- `rotation`
- `scale`
- `dimensions`

`dimensions` must be positive when provided.

Material color, roughness, and metallic values must be inside `[0, 1]`.

Light color values must be inside `[0, 1]`, and energy must be finite and non-negative.

Unsupported primitives, missing targets, invalid vectors, invalid colors, invalid dimensions, and missing target objects return `ActionResult(status=FAILED, error=ProtocolError(...))`.

## Round 05 Usage

Round 05 is now completed by Hackathon Sprint 01. The next work should use these action contracts to add render preview and snapshot/undo around batches.
