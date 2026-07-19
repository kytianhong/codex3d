from __future__ import annotations

import json
from typing import Any

from codex3d_protocol import to_dict


def api_to_dict(value: Any) -> Any:
    return to_dict(value)


def api_to_json(value: Any) -> str:
    return json.dumps(api_to_dict(value), sort_keys=True)

