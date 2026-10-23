# SPDX-License-Identifier: MPL-2.0
from __future__ import annotations

import pytest
from rdflib import BNode, Graph, Literal as RdfLiteral, URIRef
from rdflib.namespace import XSD

from lattice_persistence import EventRow, Iri, Lit, Payload, PayloadError, Rows, Triple

S, P, O = (Iri.encode(f"urn:example:{x}") for x in "spo")


def test_a_blank_node_is_refused():
    graph = Graph()
    graph.add((BNode("b0"), URIRef("urn:example:p"), URIRef("urn:example:o")))
    with pytest.raises(PayloadError, match="blank node"):
        Payload.from_rdflib(graph)
    graph = Graph()
    graph.add((URIRef("urn:example:s"), URIRef("urn:example:p"), BNode()))
    with pytest.raises(PayloadError, match="blank node"):
        Payload.from_rdflib(graph)


def test_a_blank_node_cannot_be_built_by_hand():
    for bad in ("_:b0", BNode("b0")):
        with pytest.raises(PayloadError):
            Triple(bad, P, O)
        with pytest.raises(PayloadError):
            Triple(S, P, bad)


def test_only_typed_terms_are_accepted():
    with pytest.raises(PayloadError):
        Triple("<urn:example:s>", P, O)  # a plain str is not an Iri, however it looks
    with pytest.raises(PayloadError):
        Triple(Lit("x"), P, O)
    with pytest.raises(PayloadError):
        Payload(frozenset({("urn:example:s", "urn:example:p", "urn:example:o")}))


def test_an_iri_with_a_forbidden_character_is_refused():
    graph = Graph()
    graph.add((URIRef("urn:example:s"), URIRef("urn:example:p"), URIRef("urn:example:o> . <urn:x> <urn:y> <urn:z")))
    with pytest.raises(PayloadError):
        Payload.from_rdflib(graph)


def test_a_literal_stays_a_literal():
    text = '} } ; DROP ALL'
    p = Payload.of(Triple(S, P, Lit(text + '" . <urn:evil> <urn:p> <urn:o>')))
    assert len(p.lines()) == 1
    assert p.sparql().count("<urn:evil>") == 1 and p.sparql().startswith("<urn:example:s> <urn:example:p> \"} } ; DROP ALL\\\" .")


def test_canonical_text_escapes_a_backslash_once():
    assert Lit("\\u0041").nt() == '"\\\\u0041"'


@pytest.mark.parametrize("value", ["\\u0041", "\\U0001F600", "a\\\\u0041", "\\u00e9\\u00e9", 'q"uo\\te\n', "\\"])
def test_slot_text_round_trips_through_an_engine(value):
    """The SPARQL text keeps the value where an engine reads \\uXXXX before parsing, which the canonical text would not."""
    graph = Graph()
    graph.update("INSERT DATA { " + Payload.of(Triple(S, P, Lit(value))).sparql() + " }")
    assert [str(o) for o in graph.objects()] == [value]


def test_xsd_string_is_plain_and_language_is_lower_case():
    assert Lit("x", str(XSD.string)).nt() == '"x"'
    assert Lit("x", lang="EN-GB").nt() == '"x"@en-gb'
    assert Lit("x") == Lit("x", str(XSD.string))


def test_lines_are_sorted_and_unique():
    t1, t2 = Triple(S, P, O), Triple(O, P, S)
    assert Payload.of(t1, t2, t1).lines() == tuple(sorted({t1.nt(), t2.nt()}))
    assert Payload.from_rdflib([(URIRef("urn:example:s"), URIRef("urn:example:p"), RdfLiteral("1", datatype=XSD.long))]).lines() == (
        '<urn:example:s> <urn:example:p> "1"^^<http://www.w3.org/2001/XMLSchema#long> .',)


def test_rows_text_and_triples():
    when = Lit("2026-10-20T10:00:00Z", str(XSD.dateTime))
    rows = Rows((EventRow(Iri.encode("urn:e:2"), Iri.encode("urn:T"), 2, when), EventRow(Iri.encode("urn:e:1"), Iri.encode("urn:T"), 1, when)))
    assert rows.sparql().splitlines()[0].startswith('(<urn:e:1> <urn:T> "1"^^<http://www.w3.org/2001/XMLSchema#long> ')
    assert len(rows.payload()) == 6


@pytest.mark.parametrize("bad", [True, "1", 2**63, -(2**63) - 1, 1.0])
def test_op_seq_must_be_a_long(bad):
    with pytest.raises(PayloadError):
        EventRow(Iri.encode("urn:e:1"), Iri.encode("urn:T"), bad, Lit("2026-10-20T10:00:00Z", str(XSD.dateTime)))


def test_rows_hold_rows_only():
    with pytest.raises(PayloadError):
        Rows(("(<urn:e:1> <urn:T> 1 2)",))
