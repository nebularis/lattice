# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Each enumerated class of Persistence is closed in OWL (``owl:oneOf``) and in SHACL (``sh:in``), and the two lists are the individuals
the spec types with the class. The examples and the expected profiles are validated against the shapes by test_compiler_integration.py
and test_contract_shapes.py, which this file relies on."""

from __future__ import annotations

import pytest
from rdflib import OWL, RDF, RDFS, Graph, URIRef
from rdflib.collection import Collection
from rdflib.namespace import SH

from persistence.namespaces import DAL
from persistence.witness import SHAPES_TTL, SPEC_TTL

SPEC = Graph().parse(SPEC_TTL, format="turtle")
SHAPES = Graph().parse(SHAPES_TTL, format="turtle")

# A parameter with no source has no dal:sourcedFrom, so the shape lists dal:RegistryGraph and leaves out dal:NoSource.
SHAPE_LEAVES_OUT = {DAL.sourcedFrom: {DAL.NoSource}}


def _enumerations() -> dict[URIRef, set]:
    out = {}
    for cls in SPEC.subjects(RDF.type, OWL.Class):
        equivalent = SPEC.value(cls, OWL.equivalentClass)
        one_of = SPEC.value(equivalent, OWL.oneOf) if equivalent is not None else None
        if one_of is not None:
            out[cls] = set(Collection(SPEC, one_of))
    return out


ENUMERATIONS = _enumerations()
CLASSES = sorted(ENUMERATIONS)
RANGES = sorted((p, c) for c in CLASSES for p in SPEC.subjects(RDFS.range, c))


def test_enumerations_were_found():
    assert len(ENUMERATIONS) >= 40


@pytest.mark.parametrize("cls", CLASSES, ids=lambda c: str(c).rsplit("#", 1)[-1])
def test_oneof_is_the_individuals_typed_with_the_class(cls):
    typed = {s for s in SPEC.subjects(RDF.type, cls) if isinstance(s, URIRef)}
    assert ENUMERATIONS[cls] == typed
    assert len(list(Collection(SPEC, SPEC.value(SPEC.value(cls, OWL.equivalentClass), OWL.oneOf)))) == len(typed)  # no repeated member


@pytest.mark.parametrize("prop,cls", RANGES, ids=lambda x: str(x).rsplit("#", 1)[-1])
def test_every_property_ranging_over_an_enumeration_has_the_shape_list(prop, cls):
    lists = [
        set(Collection(SHAPES, SHAPES.value(ps, SH["in"])))
        for ps in SHAPES.subjects(SH.path, prop)
        if SHAPES.value(ps, SH["in"]) is not None
    ]
    assert ENUMERATIONS[cls] - SHAPE_LEAVES_OUT.get(prop, set()) in lists
