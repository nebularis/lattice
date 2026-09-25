# SPDX-License-Identifier: MPL-2.0

"""MORK's order relations in OWL 2 DL (ADR-A97): the acyclicity shapes, and
Mork and Executable loading consistently under HermiT through the ADR-A83
harness (the `eligibility-compiler` unit's A2 reasoner half)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import Graph
from rdflib.namespace import SH

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "mork_compilers" / "src"))

from mork_compilers import reasoning  # noqa: E402
from ontology_catalog import Catalog, closure  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SHAPES = Graph().parse(ROOT / "ontology/mork/shapes/constraints.ttl")
PREFIX = "@prefix : <http://www.nebularis.org/ontologies/Mork#> .\n@prefix ex: <https://example.org/m/> .\n"


def violations(data: str) -> set:
    _, report, _ = validate(Graph().parse(data=PREFIX + data, format="turtle"), shacl_graph=SHAPES, inference="none")
    return {str(node).rsplit("/", 1)[-1] for node in report.objects(None, SH.focusNode)}


@pytest.mark.parametrize("data, expected", [
    # a -> b -> c -> a, through a materialised edge and two derivations (P1, P3)
    ("ex:a :precedes ex:b . ex:c :compositeBroaderMapping ex:b . ex:a :dependentMapping ex:c .", {"a", "b", "c"}),
    ("ex:a :precedes ex:b . ex:c :compositeBroaderMapping ex:b .", set()),
    ("ex:a :softPrecedes ex:b . ex:a :hypothesisMapping ex:b .", {"a", "b"}),
    # a hard and a soft edge are checked separately
    ("ex:a :precedes ex:b . ex:b :softPrecedes ex:a .", set()),
    ("ex:i :refinesIntent ex:j . ex:j :refinesIntent ex:i .", {"i", "j"}),
    ("ex:i :refinesIntent ex:j .", set()),
])
def test_acyclicity_shapes(data: str, expected: set) -> None:
    assert violations(data) == expected


@pytest.mark.skipif(not reasoning.available(), reason="reasoning-testkit jar not built")
@pytest.mark.parametrize("iri", ["http://www.nebularis.org/ontologies/Mork", "https://www.nebularis.org/neuro-semantic/lattice/executable"])
def test_consistent_under_hermit(iri: str) -> None:
    graph = closure(Catalog(ROOT / "ontology" / "catalog-v001.xml"), iri)
    assert reasoning.run("consistent", graphs=[graph]) is True
