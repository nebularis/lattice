# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI
"""A binding ends by a closure record, never by editing its validity (ADR-A137, ontology remediation OR-7b)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from rdflib import Graph, URIRef

from vocabulary import NoApplicableBindingError, resolve

EX = "https://example.org/lattice/vocabulary/examples#"
TURTLE = """
@prefix voc: <https://www.nebularis.org/neuro-semantic/lattice/vocabulary#> .
@prefix fnd: <https://www.nebularis.org/neuro-semantic/lattice/foundation#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <https://example.org/lattice/vocabulary/examples#> .

ex:contract a voc:SchemeContract .
ex:scheme a voc:ConceptScheme .
ex:binding a voc:SchemeBinding ; voc:forContract ex:contract ; voc:bindsScheme ex:scheme ;
    fnd:hasTemporalScope [ a fnd:TemporalScope ; fnd:validFrom "2026-01-01T00:00:00Z"^^xsd:dateTime ] .
ex:closure a voc:BindingClosure ; voc:closesBinding ex:binding ; voc:closedAt "2026-06-01T00:00:00Z"^^xsd:dateTime .
"""


def _at(iso: str) -> datetime:
    return datetime.fromisoformat(iso).replace(tzinfo=timezone.utc)


def test_a_closed_binding_resolves_before_its_closure_and_not_at_or_after_it():
    g = Graph().parse(data=TURTLE, format="turtle")
    contract = URIRef(EX + "contract")
    assert resolve(g, contract, context=[], at=_at("2026-03-01T00:00:00")).scheme == URIRef(EX + "scheme")
    with pytest.raises(NoApplicableBindingError):
        resolve(g, contract, context=[], at=_at("2026-06-01T00:00:00"))
    with pytest.raises(NoApplicableBindingError):
        resolve(g, contract, context=[], at=_at("2026-07-01T00:00:00"))
