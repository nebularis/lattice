# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI
"""The structural OWL 2 DL check: each rule on a small graph, and the corpus against its baseline."""

from __future__ import annotations

import sys
from pathlib import Path

from rdflib import Graph

sys.path.insert(0, str(Path(__file__).resolve().parent))

import owl_profile  # noqa: E402

PREFIXES = """
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix ex: <https://example.org/t#> .
"""


def _kinds(turtle: str) -> set[str]:
    return {f.kind for f in owl_profile.findings_in(Graph().parse(data=PREFIXES + turtle, format="turtle"), "t.ttl")}


def test_reserved_vocabulary_redeclared_is_a_finding():
    assert _kinds("rdf:Property a owl:Class .") == {"reserved"}


def test_a_class_used_as_a_predicate_is_a_finding():
    assert _kinds("ex:Thing a owl:Class . ex:a ex:Thing ex:b .") == {"class-as-predicate"}


def test_two_property_kinds_and_class_and_datatype_are_findings():
    assert _kinds("ex:p a owl:ObjectProperty, owl:DatatypeProperty .") == {"two-property-kinds"}
    assert _kinds("ex:D a owl:Class, rdfs:Datatype .") == {"class-and-datatype"}


def test_a_clean_graph_has_no_finding():
    assert _kinds("ex:Thing a owl:Class . ex:p a owl:ObjectProperty ; rdfs:domain ex:Thing .") == set()


def test_the_corpus_has_no_finding_outside_the_baseline():
    baseline = owl_profile.excepted()
    new = [f for f in owl_profile.scan() if f.key not in baseline]
    assert not new, [f"{f.path}: {f.kind} {f.iri}" for f in new]
