from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from enum import Enum
from types import UnionType
from typing import Any, Union, get_args, get_origin, get_type_hints


def to_dict(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value

    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: to_dict(getattr(value, field.name))
            for field in fields(value)
        }

    if isinstance(value, list):
        return [to_dict(item) for item in value]

    if isinstance(value, tuple):
        return [to_dict(item) for item in value]

    if isinstance(value, dict):
        return {str(key): to_dict(item) for key, item in value.items()}

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    return value


def to_json(value: Any) -> str:
    return json.dumps(to_dict(value), sort_keys=True)


def from_dict(cls: type[Any], data: dict[str, Any]) -> Any:
    return _from_value(cls, data)


def _from_value(expected_type: Any, value: Any) -> Any:
    if value is None or expected_type is Any:
        return value

    origin = get_origin(expected_type)
    args = get_args(expected_type)

    if origin is list:
        item_type = args[0] if args else Any
        return [_from_value(item_type, item) for item in value]

    if origin is dict:
        value_type = args[1] if len(args) > 1 else Any
        return {key: _from_value(value_type, item) for key, item in value.items()}

    if origin in {Union, UnionType}:
        non_none_args = [arg for arg in args if arg is not type(None)]
        for arg in non_none_args:
            try:
                return _from_value(arg, value)
            except (TypeError, ValueError):
                continue
        return value

    if isinstance(expected_type, type) and issubclass(expected_type, Enum):
        return expected_type(value)

    if isinstance(expected_type, type) and is_dataclass(expected_type):
        type_hints = get_type_hints(expected_type)
        kwargs = {}
        for field in fields(expected_type):
            if field.name in value:
                field_type = type_hints.get(field.name, field.type)
                kwargs[field.name] = _from_value(field_type, value[field.name])
        return expected_type(**kwargs)

    return value

