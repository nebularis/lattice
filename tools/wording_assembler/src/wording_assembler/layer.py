# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The layer's own specification and shapes, found through the repository catalogue reader (STD-273).
This is the only read from disk, and a caller who passes a `Layer` to a function reads nothing."""

from __future__ import annotations

import functools
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rdflib import Graph

# The layers whose specifications the wording shapes read through, in the order of ADR-A01.
SPEC_MODULES = ("foundation", "vocabulary", "quantification", "eligibility", "wording")


@dataclass(frozen=True)
class Layer:
    spec: Graph    # the specifications, and Wording's vocabulary, as the data graph of a validation
    shapes: Graph  # Wording's structural and constraint shapes


def catalogue() -> Any:
    """The repository catalogue, from the reader that `tools/` holds. The reader is standard library only and
    not an installed package, so it must be importable, as it is under pytest from the repository root. A
    caller who cannot import it builds a `Layer` and passes it."""
    try:
        import lattice_repo_catalogue as reader
    except ImportError as error:
        raise RuntimeError("the repository catalogue reader is not importable: put tools/ on the path, or pass a Layer") from error
    return reader.load()


@functools.lru_cache(maxsize=None)
def _load() -> Layer:
    catalogue_ = catalogue()
    base = catalogue_.root

    def parse(*paths: Path) -> Graph:
        graph = Graph()
        for path in paths:
            graph.parse(path, format="turtle")
        return graph

    spec_files = [p for m in SPEC_MODULES for p in sorted((base / catalogue_.module(m).directory("spec")).glob("*.ttl"))]
    wording = catalogue_.module("wording")
    spec_files += sorted((base / wording.directory("vocab")).glob("*.ttl"))
    shape_files = [base / wording.directory("shapes") / name for name in ("structural.ttl", "constraints.ttl")]
    return Layer(spec=parse(*spec_files), shapes=parse(*shape_files))


def load_layer() -> Layer:
    """The layer of the repository found from `LATTICE_ROOT` or the working directory. Cached, so a caller
    must never change either graph."""
    return _load()
