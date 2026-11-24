# src/spc/util/json_ser.py
"""JSON serialisation helpers for generated configuration artifacts."""

import json
from pathlib import Path
from typing import Any


def write_json(data: Any, path: Path, indent: int = 2) -> None:
    """Write data as formatted JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=indent, default=str, ensure_ascii=False)


def read_json(path: Path) -> Any:
    """Read JSON from file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)