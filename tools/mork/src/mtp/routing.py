"""Compile and verify static task/signal-to-lens routing."""

from __future__ import annotations


def check(routes: list[dict], lens_ids: set[str]) -> list[str]:
    reachable = {route["lens"] for route in routes}
    return [f"routing.unreachable:{lens}" for lens in sorted(lens_ids - reachable)]