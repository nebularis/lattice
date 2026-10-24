# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Tests that the design-shape scheme stays usable for recall.

A taxonomy decays in two directions. It grows near-synonyms until nobody tags consistently, and it
loses the synonyms that let a question reach a concept at all. These tests hold both ends.
"""

from __future__ import annotations

from pathlib import Path

import pyoxigraph as ox
import pytest
import rdflib
from rdflib.namespace import SKOS

SCHEME_FILE = Path(__file__).resolve().parent / "design-shapes.ttl"
SHAPE = rdflib.Namespace("https://www.nebularis.org/neuro-semantic/lattice/dev/design-shapes#")


@pytest.fixture(scope="module")
def graph() -> rdflib.Graph:
    g = rdflib.Graph()
    g.parse(SCHEME_FILE, format="turtle")
    return g


@pytest.fixture(scope="module")
def concepts(graph: rdflib.Graph) -> set:
    return set(graph.subjects(rdflib.RDF.type, SKOS.Concept))


@pytest.fixture(scope="module")
def facets(graph: rdflib.Graph) -> set:
    return set(graph.subjects(SKOS.topConceptOf, None))


def _local(term) -> str:
    return str(term).rsplit("#", 1)[-1]


def test_the_scheme_parses_in_the_strict_store(graph: rdflib.Graph):
    store = ox.Store()
    store.load(path=str(SCHEME_FILE), format=ox.RdfFormat.TURTLE)
    assert len(list(store.quads_for_pattern(None, None, None, None))) == len(graph)


def test_every_shape_carries_a_synonym(concepts: set, facets: set, graph: rdflib.Graph):
    """The requirement of knowledge-index sketch §9.2, and the reason the scheme exists rather than
    free text. A question for "versioning" matches neither `fnd:Version`, a noun, nor MEC-01's own
    phrasing, so without a declared synonym the right row cannot be reached. A concept with no
    altLabel is reachable only by someone who already knows its name, which is nobody who needs it.
    """
    bare = sorted(_local(c) for c in concepts - facets if not list(graph.objects(c, SKOS.altLabel)))
    assert not bare


def test_the_known_miss_is_now_bridged(graph: rdflib.Graph):
    """The measured failure of §9.2, asserted so it cannot come back. "versioning" has to reach the
    concept that MEC-01 is about."""
    alts = {str(o).lower() for o in graph.objects(SHAPE["versioning-an-entity-over-time"], SKOS.altLabel)}
    assert "versioning" in alts


def test_every_shape_reaches_a_facet_and_no_parent_is_missing(concepts: set, facets: set, graph):
    """A concept outside the hierarchy is never found by a broader query, and a `broader` pointing
    at nothing silently truncates one."""
    assert len(facets) >= 8
    for concept in concepts - facets:
        parents = list(graph.objects(concept, SKOS.broader))
        assert parents, _local(concept)
        for parent in parents:
            assert parent in concepts, f"{_local(concept)} -> {_local(parent)}"


def test_the_hierarchy_stays_shallow(concepts: set, facets: set, graph: rdflib.Graph):
    """At most three levels. Deeper and a tagger cannot hold the scheme in mind, which is the
    failure that matters more than coarseness."""

    def depth(concept, seen=()) -> int:
        if concept in facets or concept in seen:
            return 1
        parents = list(graph.objects(concept, SKOS.broader))
        return 1 + max(depth(p, seen + (concept,)) for p in parents) if parents else 1

    deepest = max((depth(c), _local(c)) for c in concepts)
    assert deepest[0] <= 3, deepest


def test_the_scheme_stays_small_enough_to_tag_consistently(concepts: set):
    """40 to 70 concepts (ADR-A134 decision 9). Fewer makes retrieval coarse, more makes consistent
    tagging impossible, and an inconsistently tagged corpus is worse than an untagged one because
    it looks complete."""
    assert 40 <= len(concepts) <= 70, len(concepts)


def test_every_concept_defines_itself_as_a_problem(concepts: set, graph: rdflib.Graph):
    """A definition naming a technique would invite tagging by solution, which defeats the point:
    an agent matches before it knows the solution."""
    for concept in concepts:
        definitions = list(graph.objects(concept, SKOS.definition))
        assert definitions, _local(concept)
        assert len(str(definitions[0])) > 25, _local(concept)


def test_the_domain_shapes_are_one_marked_subtree(graph: rdflib.Graph, concepts: set):
    """This repository is public and domain shapes carry a confidentiality rule, so they sit under
    one facet that says so rather than being scattered through the scheme."""
    facet = SHAPE["insurance-domain"]
    assert facet in concepts
    children = set(graph.subjects(SKOS.broader, facet))
    assert children
    for child in children:
        assert list(graph.objects(child, rdflib.RDFS.comment)), _local(child)


def test_no_two_concepts_share_a_label(graph: rdflib.Graph):
    """Two concepts answering one phrase is the near-synonym decay this scheme is sized to avoid,
    and it makes a tagger's choice arbitrary."""
    seen: dict[str, str] = {}
    clashes = []
    for predicate in (SKOS.prefLabel, SKOS.altLabel):
        for subject, _, label in graph.triples((None, predicate, None)):
            key = str(label).lower()
            if key in seen and seen[key] != _local(subject):
                clashes.append((key, seen[key], _local(subject)))
            seen[key] = _local(subject)
    assert not clashes
