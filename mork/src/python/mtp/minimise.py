"""Minimal teaching-core reduction hook."""

from __future__ import annotations

from typing import Callable


def minimise(lines: list[str], preserves: Callable[[list[str]], bool]) -> list[str]:
    result = list(lines)
    for line in list(lines):
        candidate = [item for item in result if item != line]
        if candidate and preserves(candidate):
            result = candidate
    return result