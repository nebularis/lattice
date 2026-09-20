"""Structural, non-semantic MCN line token manipulation."""

from __future__ import annotations


def tokens(line: str) -> list[str]:
    return line.strip().split()


def replace_token(line: str, old: str, new: str) -> str:
    return " ".join(new if token == old else token for token in tokens(line))