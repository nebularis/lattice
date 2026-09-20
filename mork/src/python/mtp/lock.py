"""Read, write, and compare hash-pinned MTP inputs."""

from __future__ import annotations

import json
from pathlib import Path


def read(path: Path) -> dict[str, str]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def write(path: Path, pins: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(sorted(pins.items())), indent=2) + "\n", encoding="utf-8")


def drift(expected: dict[str, str], actual: dict[str, str]) -> list[str]:
    return [key for key in sorted(set(expected) | set(actual)) if expected.get(key) != actual.get(key)]