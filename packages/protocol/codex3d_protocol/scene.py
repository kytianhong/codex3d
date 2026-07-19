from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .common import Dimensions, Metadata, Transform, UnitSystem, new_id, utc_now_iso


class RelationType(str, Enum):
    ON_TOP_OF = "on_top_of"
    INSIDE = "inside"
    NEAR = "near"
    FACING = "facing"
    ATTACHED_TO = "attached_to"
    LEFT_OF = "left_of"
    RIGHT_OF = "right_of"


class ConstraintType(str, Enum):
    LOCK_POSITION = "lock_position"
    LOCK_SCALE = "lock_scale"
    LOCK_MATERIAL = "lock_material"
    PRESERVE_RELATION = "preserve_relation"
    AVOID_COLLISION = "avoid_collision"
    KEEP_VISIBLE = "keep_visible"


class SceneObjectSourceType(str, Enum):
    PROCEDURAL = "procedural"
    IMPORTED_ASSET = "imported_asset"
    GENERATED_ASSET = "generated_asset"
    EXISTING_BLENDER_OBJECT = "existing_blender_object"
    USER_DEFINED = "user_defined"


@dataclass
class Relation:
    id: str = field(default_factory=lambda: new_id("relation"))
    type: RelationType = RelationType.NEAR
    source_object_id: str = ""
    target_object_id: str = ""
    metadata: Metadata = field(default_factory=dict)


@dataclass
class Constraint:
    id: str = field(default_factory=lambda: new_id("constraint"))
    type: ConstraintType = ConstraintType.PRESERVE_RELATION
    subject_object_id: str = ""
    description: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    metadata: Metadata = field(default_factory=dict)


@dataclass
class SceneObject:
    id: str = field(default_factory=lambda: new_id("object"))
    label: str = ""
    semantic_type: str = "object"
    source_type: SceneObjectSourceType = SceneObjectSourceType.PROCEDURAL
    blender_uuid: str | None = None
    transform: Transform = field(default_factory=Transform)
    dimensions: Dimensions = field(default_factory=Dimensions)
    parent_id: str | None = None
    part_ids: list[str] = field(default_factory=list)
    metadata: Metadata = field(default_factory=dict)


@dataclass
class Scene:
    id: str = field(default_factory=lambda: new_id("scene"))
    name: str = "Untitled Scene"
    unit_system: UnitSystem = UnitSystem.METERS
    objects: list[SceneObject] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    constraints: list[Constraint] = field(default_factory=list)
    version: int = 1
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    metadata: Metadata = field(default_factory=dict)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def add_object(self, scene_object: SceneObject) -> SceneObject:
        self.objects.append(scene_object)
        self.touch()
        return scene_object

    def add_relation(self, relation: Relation) -> Relation:
        self.relations.append(relation)
        self.touch()
        return relation

    def add_constraint(self, constraint: Constraint) -> Constraint:
        self.constraints.append(constraint)
        self.touch()
        return constraint

