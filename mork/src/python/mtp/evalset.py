"""Deferred placeholder for Phase 7 backend-dependent model evaluation."""

from __future__ import annotations


def unavailable() -> None:
    raise NotImplementedError("MTP evalset is deferred until the LLM backend interface exists")