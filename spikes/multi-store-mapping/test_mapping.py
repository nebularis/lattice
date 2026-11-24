# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Tests of MSA-I10's mapping check. Run with ``python -m pytest spikes/multi-store-mapping -q -p no:cacheprovider`` from
inside the repository. The first test is the slice's result. The rest show that each check fails on the break it names."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

sys.path.insert(0, str(Path(__file__).resolve().parent))  # the spike is a directory of scripts, not a package

import mapping as m  # noqa: E402

CUT = Namespace("https://example.org/lattice/ledger/credit-cut-at-parent/")
PASS = Namespace("https://example.org/lattice/ledger/credit-cut-at-parent/ledger-holder/pass/")


@pytest.fixture(scope="module")
def inputs() -> m.Inputs:
    return m.read_inputs()


@pytest.fixture(scope="module")
def result(inputs) -> m.Result:
    return m.run(inputs)


def _example(inputs: m.Inputs, name: str) -> Graph:
    found = dict(inputs.ledger_examples)[name]
    g = Graph()
    for t in found:
        g.add(t)
    return g


def _mapping_graph(inputs: m.Inputs, name: str) -> Graph:
    return Graph().parse(inputs.spike / f"{name}.r2rml.ttl")


def test_one_vocabulary_and_the_mapping_holds(result):
    assert result.one_vocabulary, result.outside
    assert result.mapping_holds, m.report(result)
    with_records = [t for t in result.trips["ledger"] if t.triples]
    assert len(with_records) >= 10
    assert all(t.holds and not t.lexical for t in with_records)
    assert {table for t in with_records for table in t.rows} == set(result.ledger.places)


def test_every_column_holds_a_key_part_a_field_or_a_derived_value(result):
    for mapping in (result.ledger, result.promotion):
        for place in mapping.places.values():
            for col in place.columns.values():
                assert col.key_parts or col.fields or col.derived, f"{place.table}.{col.name}"
            for name in place.primary_key:
                assert place.columns[name].key_parts, f"{place.table}.{name}"


def test_the_promotion_reads_both_ways(result):
    [trip] = result.trips["promotion"]
    assert trip.holds and trip.triples == 2 and trip.rows == {"subscription_currency": 2}


def test_the_supersession_is_held_and_named(result):
    trip = next(t for t in result.trips["ledger"] if t.example == "supersession-raised-amount.ttl")
    assert trip.held == 7 and trip.holds
    assert "ldg:Supersession, the record" in result.held
    assert "ldg:supersedingVersion on ldg:Supersession" in result.held


def test_a_dropped_column_is_reported_missing(inputs):
    g = _mapping_graph(inputs, "ledger")
    pom = next(g.subjects(m.RR.predicate, m.LDG.runningBalance))
    g.remove((None, m.RR.predicateObjectMap, pom))
    result = m.run(inputs, ledger_graph=g)
    assert "ldg:runningBalance on ldg:Posting has no column" in result.missing
    assert not result.mapping_holds
    assert any("no column holds it" in p for t in result.trips["ledger"] for p in t.problems)


def test_a_key_column_with_no_key_part_is_reported(inputs):
    g = _mapping_graph(inputs, "ledger")
    table = next(g.subjects(m.RR.tableName, Literal("posting")))
    for kp in list(g.objects(table, m.RP.keyPart)):
        if (kp, m.RP.column, Literal("posting")) in g:
            g.remove((table, m.RP.keyPart, kp))
    result = m.run(inputs, ledger_graph=g, ledger_examples=[])
    assert "posting.posting is a key column and holds no key part of a logical resource" in result.columns["ledger"]


def test_a_term_outside_the_vocabulary_fires_the_falsifier(inputs):
    g = _mapping_graph(inputs, "promotion")
    om = next(g.objects(None, m.RR.objectMap))
    g.remove((om, m.RR.termType, None))
    g.add((om, m.RR.termType, URIRef("http://w3id.org/rml/UnsafeIRI")))
    result = m.run(inputs, promotion_graph=g, ledger_examples=[])
    assert not result.one_vocabulary
    assert any("UnsafeIRI" in t for t in result.outside["promotion"])


def test_an_unsupported_construct_is_refused(inputs):
    g = _mapping_graph(inputs, "promotion")
    table = next(g.subjects(m.RR.tableName, None))
    g.add((table, m.RR.sqlQuery, Literal("SELECT 1")))
    with pytest.raises(m.MappingRefused, match="sqlQuery"):
        m.load_mapping("promotion", g)


def test_an_r2rml_template_percent_encodes_an_iri_it_inserts():
    ledger = "https://example.org/lattice/ledger/credit-cut-at-parent/ledger-holder"
    term = m.generated_term(m.TermMap(template="{ledger}/pass/{key}"), {"ledger": ledger, "key": "debit-1"})
    assert term == URIRef("https%3A%2F%2Fexample.org%2Flattice%2Fledger%2Fcredit-cut-at-parent%2Fledger-holder/pass/debit-1")
    assert term != PASS["debit-1"]


def test_a_non_canonical_decimal_comes_back_canonical(inputs):
    g = _example(inputs, "credit-cut-at-parent.ttl")
    g.remove((CUT["debit-1-posting"], m.LDG.amountValue, None))
    g.add((CUT["debit-1-posting"], m.LDG.amountValue, Literal("5.0", datatype=XSD.decimal)))
    result = m.run(inputs, ledger_examples=[("credit-cut-at-parent.ttl", g)])
    [trip] = result.trips["ledger"]
    assert trip.holds
    assert trip.lexical == ["ldg:amountValue 5.0 became 5"]


def test_a_record_derived_into_another_ledger_fails_a_foreign_key(inputs):
    g = _example(inputs, "credit-cut-at-parent.ttl")
    other, other_ledger = CUT["other-holder"], CUT["ledger-other"]
    g.remove((CUT["account-child"], m.LDG.forOwner, None))
    g.add((CUT["account-child"], m.LDG.forOwner, other))
    g.add((other_ledger, RDF.type, m.LDG.Ledger))
    g.add((other_ledger, m.LDG.forOwner, other))
    g.add((other_ledger, m.LDG.ledgerProfile, CUT["ledger-profile"]))
    g.add((other_ledger, m.LDG.revision, Literal("0", datatype=XSD.nonNegativeInteger)))
    result = m.run(inputs, ledger_examples=[("credit-cut-at-parent.ttl", g)])
    [trip] = result.trips["ledger"]
    assert not trip.holds
    assert any("has no row of pass" in p for p in trip.problems)
    assert any("has no row of account" in p for p in trip.problems)


def test_a_property_given_twice_is_not_functional(inputs):
    g = _example(inputs, "credit-cut-at-parent.ttl")
    g.add((CUT["debit-1-posting"], m.LDG.amountValue, Literal("6", datatype=XSD.decimal)))
    result = m.run(inputs, ledger_examples=[("credit-cut-at-parent.ttl", g)])
    [trip] = result.trips["ledger"]
    assert any("is not functional here" in p for p in trip.problems)


def test_an_exactly_one_field_left_empty_fails(inputs):
    g = _example(inputs, "credit-cut-at-parent.ttl")
    g.remove((CUT["debit-1-posting"], m.LDG.runningBalance, None))
    result = m.run(inputs, ledger_examples=[("credit-cut-at-parent.ttl", g)])
    [trip] = result.trips["ledger"]
    assert any(p.startswith("posting.running_balance is empty") for p in trip.problems)


def test_the_committed_places_are_the_ones_the_mapping_emits(inputs, result):
    committed = (inputs.spike / "results" / "places.md").read_text(encoding="utf-8")
    assert committed == m.places_markdown(result)


def test_two_runs_emit_the_same_places(inputs, result):
    again = m.run(copy.copy(inputs))
    assert m.places_markdown(again) == m.places_markdown(result)
