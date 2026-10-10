# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""HO1: the composite replace writes the new payload where it deletes from, and sweeps in
linear time (formal-methods track H, slice HO1, technical debt TD-39 and TD-36).
Validation Pack: docs/developer/validation/FMH-HO1.md. Test IDs are HO1-Tn.

HO5 moved the aggregates from the default graph to the profile's data graph (ADR-A122 decision 3), so
these tests load the data into that graph and look for the payload there. What each asserts, that the
payload lands where the sweep deletes from, is unchanged (FMH-HO5 lists the change).

The generated update runs on rdflib's in-memory ``Dataset``. The request-time payload slot is
filled with the payload under test, in place of the stand-in ``templatecheck`` uses."""

from __future__ import annotations

import re
import warnings
from functools import lru_cache

import pytest
from rdflib import RDF, Dataset, Literal, URIRef, Variable
from rdflib.namespace import XSD

from persistence import templatecheck, witness
from persistence.cli import main
from persistence.compiler import compile_to_graph

from conftest import EXAMPLES_DIR

EX = "https://example.org/lending#"
PAT = "https://example.org/lattice/patterns#"
ROOT = URIRef("urn:order:1")
DATA_GRAPH = URIRef("urn:g:orders")
PLAIN = "cas-replace-composite-property"
DATASET_GUARD = "cas-replace-composite-property-dataset-guard"
FIXTURES = {
    PLAIN: EXAMPLES_DIR / "composite-property-boundary-shacl.ttl",
    DATASET_GUARD: witness.WITNESS_DIR / "template-cas-replace-composite-property-dataset-guard.ttl",
}
PAYLOAD = (
    f'<urn:order:1> <{EX}status> "paid" . <urn:order:1> <{EX}lineItem> <urn:li:1> . '
    f'<urn:li:1> <{EX}sku> "ABC" . '
)


@lru_cache(maxsize=None)
def _text(template: str) -> str:
    compiled, _ = compile_to_graph(witness._load_fixture(FIXTURES[template]))
    return next(o for o in templatecheck.operations(compiled) if o.template == template).text


def _values(expected_seq: int = 1) -> dict:
    return {
        Variable("root"): ROOT, Variable("epoch"): Literal(1),
        Variable("expectedSeq"): Literal(expected_seq, datatype=XSD.long),
        Variable("nextSeq"): Literal(2, datatype=XSD.long), Variable("newRev"): URIRef("urn:rev:2"),
        Variable("txnId"): URIRef("urn:txn:a"), Variable("requestDigest"): Literal("d"),
    }


def _dataset(template: str, line_items: int = 2, triples_per_item: int = 2) -> Dataset:
    """An order and ``line_items`` line items in the data graph, and the version row."""
    text = _text(template)
    meta = URIRef(re.search(r"GRAPH <(urn:g:meta/\d+)>", text).group(1))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        ds = Dataset()
        ds.graph(meta).add((ROOT, URIRef(PAT + "epoch"), Literal(1)))
        ds.graph(meta).add((ROOT, URIRef(PAT + "seq"), Literal(1, datatype=XSD.long)))
        if template == DATASET_GUARD:
            dataset_graph = URIRef(re.search(r"GRAPH <(urn:g:dataset)>", text).group(1))
            ds.graph(dataset_graph).add((dataset_graph, URIRef(PAT + "epoch"), Literal(1)))
        data = ds.graph(DATA_GRAPH)
        data.add((ROOT, URIRef(EX + "status"), Literal("open")))
        data.add((ROOT, RDF.type, URIRef(EX + "Order")))
        for n in range(1, line_items + 1):
            item = URIRef(f"urn:li:{n}")
            data.add((ROOT, URIRef(EX + "lineItem"), item))
            for k in range(triples_per_item):
                data.add((item, URIRef(EX + f"attr{k}"), Literal(f"{n}-{k}")))
    return ds


def _quads(ds: Dataset) -> set:
    return {(s, p, o, str(getattr(g, "identifier", g))) for s, p, o, g in ds.quads((None, None, None, None))}


def _replace(ds: Dataset, template: str, payload: str = PAYLOAD, expected_seq: int = 1) -> None:
    text = _text(template).replace(templatecheck._SLOT_STAND_INS["payloadTriples"], payload)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        ds.update(text, initBindings=_values(expected_seq))


def _graphs_holding(ds: Dataset, obj: Literal) -> set[str]:
    return {g for s, p, o, g in _quads(ds) if o == obj}


DATA_GRAPH_NAME = "urn:g:orders"


def test_ho1_t1_the_payload_lands_in_the_data_graph_and_nowhere_else():
    ds = _dataset(PLAIN)
    _replace(ds, PLAIN)
    assert _graphs_holding(ds, Literal("paid")) == {DATA_GRAPH_NAME}


def test_ho1_t2_the_old_payload_is_gone_and_no_payload_triple_is_in_a_log_graph():
    ds = _dataset(PLAIN)
    _replace(ds, PLAIN)
    assert _graphs_holding(ds, Literal("open")) == set()
    payload_in_log = [q for q in _quads(ds) if q[3].startswith("urn:g:txlog/") and str(q[1]).startswith(EX)]
    assert payload_in_log == []


def test_ho1_t3_one_revision_for_sequence_two_is_in_a_log_graph():
    ds = _dataset(PLAIN)
    _replace(ds, PLAIN)
    revisions = [q for q in _quads(ds) if q[1] == RDF.type and q[2] == URIRef(PAT + "Revision")]
    assert len(revisions) == 1 and revisions[0][3].startswith("urn:g:txlog/")
    seqs = [q for q in _quads(ds) if q[0] == revisions[0][0] and q[1] == URIRef(PAT + "seq")]
    assert [q[2] for q in seqs] == [Literal(2, datatype=XSD.long)]


def test_ho1_t4_the_dataset_guard_variant_does_the_same():
    ds = _dataset(DATASET_GUARD)
    _replace(ds, DATASET_GUARD)
    assert _graphs_holding(ds, Literal("paid")) == {DATA_GRAPH_NAME}
    assert _graphs_holding(ds, Literal("open")) == set()
    assert len([q for q in _quads(ds) if q[1] == RDF.type and q[2] == URIRef(PAT + "Revision")]) == 1


@pytest.mark.parametrize("template", [PLAIN, DATASET_GUARD])
def test_ho1_t5_the_sweep_does_work_linear_in_the_aggregate(template):
    """A root of 5 triples and 3 line items of 4 triples each. One solution per triple of the
    root and of each member is 5 + 12 = 17. Two independent OPTIONALs gave 5 x 12 = 60."""
    ds = _dataset(template, line_items=3, triples_per_item=4)
    text = _text(template)
    prefixes = "\n".join(re.findall(r"^PREFIX .*$", text, re.M))
    where = text[text.index("WHERE {"):]
    query = f"{prefixes}\nSELECT (COUNT(*) AS ?n) {where}"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        (row,) = list(ds.query(query, initBindings=_values()))
    assert int(row[0]) == 17


def test_ho1_t6_a_stale_sequence_changes_nothing():
    ds = _dataset(PLAIN)
    before = _quads(ds)
    _replace(ds, PLAIN, expected_seq=7)
    assert _quads(ds) == before


@pytest.mark.parametrize("template", [PLAIN, DATASET_GUARD])
def test_ho1_t7_the_changed_templates_pass_the_static_checks(template):
    compiled, _ = compile_to_graph(witness._load_fixture(FIXTURES[template]))
    assert templatecheck.check_compiled(compiled) == []
    assert main(["hygiene", str(FIXTURES[PLAIN])]) == 0
