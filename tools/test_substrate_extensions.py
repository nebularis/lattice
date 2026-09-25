# SPDX-License-Identifier: MPL-2.0

"""Phase C substrate extensions: shapes for derived rate spaces, calendar units
and alternative bounds (ADR-A93, ADR-A94, ADR-A95), and provision attachment
(ADR-A96)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pyshacl import validate
from rdflib import Graph, Namespace
from rdflib.namespace import OWL, RDF

INS = Namespace("https://www.nebularis.org/neuro-semantic/lattice/instrument#")

SHAPES = Graph().parse(Path(__file__).resolve().parents[1] / "ontology/quantification/shapes/constraints.ttl")
PREFIXES = """
@prefix qnt: <https://www.nebularis.org/neuro-semantic/lattice/quantification#> .
@prefix ex: <https://example.org/q/> .
ex:mass a qnt:ValueSpace . ex:weight a qnt:ValueSpace . ex:money a qnt:ValueSpace .
ex:usd a qnt:Quantity ; qnt:inUnit ex:USD . ex:eur a qnt:Quantity ; qnt:inUnit ex:EUR . ex:usd2 a qnt:Quantity ; qnt:inUnit ex:USD .
ex:day a qnt:Unit . ex:business-day a qnt:CalendarUnit .
"""


def conforms(text: str) -> bool:
    return validate(Graph().parse(data=PREFIXES + text, format="turtle"), shacl_graph=SHAPES, advanced=True)[0]


def bound(name: str, value: str, sense: str = "Upper") -> str:
    return f"ex:{name} a qnt:Bound ; qnt:onSpace ex:money ; qnt:boundValue ex:{value} ; qnt:boundSense qnt:{sense} ; qnt:boundClosure qnt:Closed .\n"


@pytest.mark.parametrize("text, expected", [
    ("ex:dose a qnt:DerivedValueSpace ; qnt:numeratorSpace ex:mass ; qnt:denominatorSpace ex:weight .", True),
    ("ex:dose a qnt:DerivedValueSpace ; qnt:numeratorSpace ex:mass .", False),
    ("ex:c a qnt:Conversion ; qnt:fromUnit ex:business-day ; qnt:toUnit ex:day ; qnt:conversionKind qnt:Contextual .", True),
    ("ex:c a qnt:Conversion ; qnt:fromUnit ex:business-day ; qnt:toUnit ex:day ; qnt:conversionKind qnt:Defined .", False),
    (bound("a", "usd") + bound("b", "eur") + "ex:a qnt:alternativeBound ex:b .", True),
    (bound("a", "usd") + bound("b", "eur", "Lower") + "ex:a qnt:alternativeBound ex:b .", False),
    (bound("a", "usd") + bound("b", "usd2") + "ex:a qnt:alternativeBound ex:b .", False),
])
def test_shapes(text: str, expected: bool) -> None:
    assert conforms(text) is expected


def test_obligation_in_two_provisions_is_refused_only_by_the_optional_shape() -> None:
    root = Path(__file__).resolve().parents[1] / "ontology/instrument"
    spec = Graph().parse(root / "spec/instrument.ttl")
    assert (INS.inProvision, RDF.type, OWL.FunctionalProperty) not in spec
    data = Graph().parse(data="""
        @prefix ins: <https://www.nebularis.org/neuro-semantic/lattice/instrument#> .
        @prefix ex: <https://example.org/i/> .
        ex:uptime a ins:Obligation ; ins:inProvision ex:clause-en , ex:clause-fr .
    """, format="turtle")
    assert validate(data, shacl_graph=Graph().parse(root / "shapes/single-provision.ttl"))[0] is False
