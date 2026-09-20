"""Cassette fidelity and rendering helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rdflib import Graph

from .mcnio import InProcessTool


def fidelity(source: Path, mcn_text: str, tool: InProcessTool) -> tuple[bool, tuple[str, ...]]:
    decoded = tool.decode(mcn_text)
    if not decoded.ok:
        return False, tuple(diagnostic.code for diagnostic in decoded.diagnostics)
    source_graph = Graph().parse(source, format="turtle")
    return tool.graphs_equal(source_graph, decoded.graph), ()


def validate(cassette: dict[str, Any], root: Path, tool: InProcessTool) -> tuple[bool, tuple[str, ...]]:
    source = root / cassette["source"]
    if not source.exists():
        return False, ("cassette.source-missing",)
    if cassette.get("knownSourceDefect"):
        decoded = tool.decode(cassette["mcn"])
        return decoded.ok, tuple(diagnostic.code for diagnostic in decoded.diagnostics)
    return fidelity(source, cassette["mcn"], tool)