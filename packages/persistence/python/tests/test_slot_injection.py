# SPDX-License-Identifier: MPL-2.0
# NB: This file has been produced using GenAI
"""H2.9-Q3: the injection corpus over the library's slot filling. A slot is where text enters a generated operation, so every value the library puts
into one is run through the encoders with adversarial input. A value the encoder refuses is a pass. One it accepts must come back out of the
store as exactly the term that went in, and the filled text must still be one operation."""
from __future__ import annotations

import pytest
from rdflib import Dataset, Literal as RdfLiteral, URIRef
from rdflib.plugins.sparql import prepareQuery
from rdflib.plugins.sparql.algebra import translateUpdate
from rdflib.plugins.sparql.parser import parseUpdate

from lattice_persistence import EventRow, Iri, Lit, Payload, Rows, Triple
from lattice_persistence.audit import registry_text
from lattice_persistence.payload import PayloadError
from lattice_persistence.terms import SparqlTermError

ADVERSARIAL_IRIS = [
    'urn:g:orders> } ; DROP GRAPH <urn:g:keys> ; ASK { <urn:g:x',
    "urn:g:orders/{ INSERT DATA { <urn:x> <urn:y> <urn:z> } }",
    "urn:g:orders/​",
    "urn:g:orders/‮",
    'urn:g:orders/"; DELETE WHERE { ?s ?p ?o } #',
    "urn:g:orders/<script>",
    "urn:g:orders/\n\rDELETE",
    "urn:g:orders/|pipe",
    "urn:g:orders/`backtick`",
    "urn:g:orders/{{{eventRows}}}",
    "",
]
ADVERSARIAL_LITERALS = [
    'value" ; DROP GRAPH <urn:g:keys> ; INSERT DATA { <urn:x> <urn:y> "',
    "value\\\" } } DELETE { ?s ?p ?o",
    "line1\nline2\rline3\ttabbed",
    "back\\slash",
    "\\u0041",
    "{{{payloadTriples}}}",
    "unicode​zero‮width",
    "",
]
S, P = "urn:s:1", "urn:p:1"


def _operations(text: str) -> int:
    return len(translateUpdate(parseUpdate(text)).algebra)


def _stored(text: str) -> set:
    dataset = Dataset()
    dataset.update(text)
    return {(s, p, o) for s, p, o, _ in dataset.quads((None, None, None, URIRef("urn:g:data")))}


@pytest.mark.parametrize("value", ADVERSARIAL_LITERALS)
def test_a_payload_literal_comes_back_as_the_same_literal_or_is_refused(value):
    try:
        payload = Payload.of(Triple(Iri.encode(S), Iri.encode(P), Lit(value)))
    except (PayloadError, SparqlTermError):
        return
    text = "INSERT DATA { GRAPH <urn:g:data> { " + payload.sparql() + " } }"
    assert _operations(text) == 1
    assert _stored(text) == {(URIRef(S), URIRef(P), RdfLiteral(value))}


@pytest.mark.parametrize("value", ADVERSARIAL_IRIS)
def test_a_payload_iri_comes_back_as_the_same_iri_or_is_refused(value):
    try:
        payload = Payload.of(Triple(Iri.encode(S), Iri.encode(P), Iri.encode(value)))
    except (PayloadError, SparqlTermError):
        return
    text = "INSERT DATA { GRAPH <urn:g:data> { " + payload.sparql() + " } }"
    assert _operations(text) == 1
    assert _stored(text) == {(URIRef(S), URIRef(P), URIRef(value))}


@pytest.mark.parametrize("value", ADVERSARIAL_IRIS)
def test_a_listed_log_graph_is_one_graph_or_is_refused(value):
    try:
        filled = "SELECT ?log WHERE { VALUES ?log { <urn:g:txlog/pinned> " + registry_text([value]) + " } }"
    except SparqlTermError:
        return
    prepareQuery(filled)
    dataset = Dataset()
    assert sorted(str(row[0]) for row in dataset.query(filled)) == sorted(["urn:g:txlog/pinned", value])


@pytest.mark.parametrize("value", ADVERSARIAL_LITERALS)
def test_an_event_row_is_one_row_or_is_refused(value):
    try:
        row = EventRow(Iri.encode("urn:e:1"), Iri.encode("urn:t:1"), 1, Lit(value, "http://www.w3.org/2001/XMLSchema#dateTime"))
    except (PayloadError, SparqlTermError):
        return
    query = "SELECT * WHERE { VALUES (?event ?type ?opSeq ?at) { " + Rows((row,)).sparql() + " } }"
    rows = list(Dataset().query(query))
    assert len(rows) == 1 and str(rows[0]["event"]) == "urn:e:1"
    assert rows[0]["at"] == RdfLiteral(value, datatype=URIRef("http://www.w3.org/2001/XMLSchema#dateTime"))
