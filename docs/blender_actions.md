# Blender Actions

Hackathon Sprint 01 adds the first executable Blender action contract.

The same `codex3d_protocol.Action` and `ActionResult` dataclasses are used. No duplicate action model was introduced.

## Supported Action Types

Supported in Sprint 01:

- `create_object`
- `transform_object`
- `modify_object`
- `delete_object`
- `assign_material`

Not supported yet:

- `render_preview`
- `snapshot_scene`
- `restore_snapshot`
- arbitrary Python execution

## CREATE_OBJECT

```json
{
  "primitive": "cube | cylinder | sphere | plane | point_light",
  "name": "C3D_DeskTop",
  "location": [0.0, 0.0, 0.75],
  "rotation": [0.0, 0.0, 0.0],
  "scale": [1.0, 1.0, 1.0],
  "dimensions": [1.4, 0.7, 0.08],
  "semantic_type": "desk_top",
  "light": {
    "color": [1.0, 0.72, 0.45],
    "energy": 650.0
  }
}
```

`light` only applies to `point_light`.

For mesh primitives, `dimensions` express intended final physical size and take priority over `scale`.

## TRANSFORM_OBJECT

```json
{
  "target_name": "C3D_DeskTop",
  "location": [0.0, 0.0, 0.78],
  "rotation": [0.0, 0.0, 0.0],
  "scale": [1.0, 1.0, 1.0],
  "dimensions": [1.5, 0.72, 0.08]
}
```

Only provided fields are changed. `target_name` is required.

## MODIFY_OBJECT

Sprint 01 supports rename and point-light color/energy updates:

```json
{
  "target_name": "C3D_LampLight",
  "new_name": "C3D_WarmLampLight",
  "light": {
    "color": [1.0, 0.65, 0.35],
    "energy": 420.0
  }
}
```

## DELETE_OBJECT

```json
{
  "target_name": "C3D_TemporaryCube"
}
```

## ASSIGN_MATERIAL

```json
{
  "target_name": "C3D_DeskTop",
  "material": {
    "name": "C3D_Walnut",
    "base_color": [0.30, 0.12, 0.045, 1.0],
    "roughness": 0.48,
    "metallic": 0.0
  }
}
```

The bpy backend uses a basic Principled BSDF material path. The fake backend records the same material fields for inspection and tests.

## Validation

Validation rejects:

- Unknown primitives
- Missing `target_name`
- Non-three-element transform vectors
- NaN or infinity
- Non-positive dimensions
- Colors outside `[0, 1]`
- Roughness or metallic outside `[0, 1]`
- Missing target objects

Failures return:

```text
ActionResult(status=FAILED, error=ProtocolError(...))
```

They do not raise unhandled exceptions and do not return fake success.

## Backends

`BlenderActionExecutor` dispatches supported actions to a backend.

`FakeBlenderBackend` is the stable no-Blender test and demo path. It stores objects, transforms, dimensions, materials, and light properties in memory.

`BpyBlenderBackend` is guarded. It loads `bpy` only inside Blender or when a bpy-like module is explicitly passed.

## Identity Limitation

Sprint 01 uses object names as temporary identity. Stable object UUIDs are still deferred to Round 09 / a later sprint.

