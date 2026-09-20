"""Teaching-pack word-budget checks."""

from __future__ import annotations


def token_estimate(text: str) -> int:
    return len(text.split())


def require_budget(text: str, limit: int, label: str) -> None:
    actual = token_estimate(text)
    if actual > limit:
        raise ValueError(f"budget exceeded for {label}: {actual} > {limit}")