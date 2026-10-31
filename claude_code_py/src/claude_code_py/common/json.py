import json
from typing import Any


def to_json(data: Any, *, indent: int | None = None) -> str:
    return json.dumps(data, ensure_ascii=False, indent=indent, sort_keys=True)


def from_json(data: str) -> Any:
    return json.loads(data)
