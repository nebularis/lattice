# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""H2.6b, the event half: an append takes its events as request-time slots, several to a request (formal-methods track H, plan 4.6).
The builder is held to its template by the harness of `test_builders.py`. These tests run what it writes, on each engine and under
several hash seeds. Validation Pack: docs/developer/validation/FMH-H2-6b.md. Test IDs are H2.6b-Tn."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

import pytest
from rdflib import RDF, XSD, Literal as RdfLiteral, URIRef

import engines
from persistence.builders import build
from persistence.ir_render import render

from test_builders import APPEND, CONTEXT, LONG, PAT, STREAM, _store, event_row, fill_events

U = URIRef
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REV1 = "urn:rev:orders/1/e3/0000000000000000001"
THREE = " ".join(event_row(f"urn:event:{n}", f"urn:type:T{n}", n) for n in (1, 2, 3))
DOMAIN = '<urn:event:1> <urn:ex:amount> "10" . <urn:event:2> <urn:ex:amount> "20" . <urn:event:3> <urn:ex:amount> "30" .'


def run_append(ds, *, stem: str = "append-event", bindings: dict | None = None, rows: str = THREE, triples: str = "", guards: bool | None = None):
    text = fill_events(render(build(stem, CONTEXT, guards=engines.guards(guards))), rows, triples)
    ds.update(text, initBindings=bindings or APPEND)
    return ds


def dump(ds) -> list:
    """Every quad as text, with the month of a bucket name and the time of a receipt left out, since both come from the clock."""
    out = []
    for g in ds.graphs():
        name = re.sub(r"\d{4}-\d{2}$", "YYYY-MM", str(g.identifier))
        for s, p, o in g:
            o = "T" if str(p).endswith("recordedAt") else str(o)
            out.append(f"{name} {s} {str(p).removeprefix(PAT)} {o}")
    return sorted(out)


def graph_holding(ds, subject: str):
    return next(g for g in ds.graphs() if (U(subject), None, None) in g)


# ---- several events in one request ------------------------------------------------------------------------------------


@engines.each_engine_and_guards
def test_h2_6b_t1_a_three_row_append_steps_the_seq_once_and_writes_one_receipt_one_claim_and_three_events():
    ds = run_append(_store(), triples=DOMAIN)
    meta = {(str(s), str(p).removeprefix(PAT), str(o)) for s, p, o in ds.graph(U("urn:g:meta"))}
    assert (str(STREAM), "seq", "1") in meta and (str(STREAM), "head", REV1) in meta and (str(STREAM), "seq", "0") not in meta
    assert len(ds.graph(U("urn:g:txn"))) == 2  # one claim: the revision and the digest
    receipts = [g for g in ds.graphs() if str(g.identifier).startswith("urn:g:txlog/")]
    assert len(receipts) == 1 and len(list(receipts[0].objects(None, U(PAT + "recordedAt")))) == 1
    assert len([s for s, p, o in receipts[0] if p == RDF.type]) == 1
    events = graph_holding(ds, "urn:event:1")
    for n in (1, 2, 3):
        e = U(f"urn:event:{n}")
        assert (e, RDF.type, U(f"urn:type:T{n}")) in events and (e, U(PAT + "revision"), U(REV1)) in events
        assert (e, U(PAT + "opSeq"), engines.canon(LONG(n))) in events


def test_h2_6b_t2_the_three_row_append_is_the_same_under_every_hash_seed_on_rdflib():
    """TSD-01: rdflib applies the solutions one at a time in an order that follows the hash seed. Every solution writes the same
    version row, claim and receipt, so the order must not matter."""
    script = (
        "import sys, json; sys.path.insert(0, %r)\n"
        "import test_append_events as t\n"
        "import engines\n"
        "print(json.dumps(t.dump(t.run_append(t._store(), triples=t.DOMAIN))))\n"
    ) % TESTS_DIR
    seen = set()
    for seed in range(8):
        env = {**os.environ, "PYTHONHASHSEED": str(seed)}
        out = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True, check=True).stdout.strip().splitlines()[-1]
        seen.add(out)
    assert len(seen) == 1
    written = json.loads(seen.pop())
    assert any(line.endswith("opSeq 3") for line in written) and sum(line.endswith("opSeq 1") or line.endswith("opSeq 2") for line in written) == 2


@engines.each_engine_and_guards
def test_h2_6b_t3_a_retry_with_the_same_transaction_id_writes_nothing():
    ds = run_append(_store(), triples=DOMAIN)
    before = dump(ds)
    run_append(ds, triples=DOMAIN)
    assert dump(ds) == before


@engines.each_engine_and_guards
def test_h2_6b_t4_the_event_triples_land_in_the_events_bucket_once_and_an_empty_slot_writes_the_events_only():
    with_domain = run_append(_store(), triples=DOMAIN)
    events = graph_holding(with_domain, "urn:event:1")
    amounts = {(str(s), str(o)) for s, p, o in events if str(p) == "urn:ex:amount"}
    assert amounts == {("urn:event:1", "10"), ("urn:event:2", "20"), ("urn:event:3", "30")}
    assert len([1 for s, p, o in events if str(p) == "urn:ex:amount"]) == 3  # each row writes the same ground triples, which are one set
    bare = run_append(_store())
    assert not any(str(p) == "urn:ex:amount" for g in bare.graphs() for s, p, o in g)
    assert len(graph_holding(bare, "urn:event:3")) == 4 * 3


@engines.each_engine_and_guards
def test_h2_6b_t5_a_one_row_append_writes_the_four_triples_the_single_event_form_wrote():
    ds = run_append(_store(), rows=event_row("urn:event:9", "urn:type:Placed", 7, "2026-10-12T10:00:00Z"))
    events = graph_holding(ds, "urn:event:9")
    e = U("urn:event:9")
    assert len(events) == 4
    assert {(s, p, o) for s, p, o in events if str(p).removeprefix(PAT) != "occurredAt"} == {
        (e, RDF.type, U("urn:type:Placed")), (e, U(PAT + "revision"), U(REV1)), (e, U(PAT + "opSeq"), engines.canon(LONG(7))),
    }
    (at,) = [o for s, p, o in events if str(p).removeprefix(PAT) == "occurredAt"]
    assert at.toPython() == RdfLiteral("2026-10-12T10:00:00Z", datatype=XSD.dateTime).toPython()  # rdflib writes the offset as +00:00


@engines.each_engine_and_guards
def test_h2_6b_t6_an_empty_rows_slot_writes_nothing_and_rdflib_raises_where_oxigraph_gives_no_solution():
    """TSD-21: rdflib 7.6.0 raises an AttributeError for any empty VALUES block, before it changes anything. Oxigraph gives no solution.
    Either way nothing is written, and H2.8's caller check refuses an empty slot before sending."""
    ds = _store()
    before = dump(ds)
    if engines.CURRENT == "rdflib":
        with pytest.raises(AttributeError):
            run_append(ds, rows="", triples=DOMAIN)
    else:
        run_append(ds, rows="", triples=DOMAIN)
    assert dump(ds) == before


@engines.each_engine_and_guards
def test_h2_6b_t7_a_second_append_chains_to_the_first_and_each_events_position_is_its_epoch_seq_and_opseq():
    ds = run_append(_store())
    run_append(ds, bindings={**APPEND, "txnId": U("urn:txn:2")}, rows=event_row("urn:event:4", "urn:type:T4", 1))
    meta = {(str(s), str(p).removeprefix(PAT), str(o)) for s, p, o in ds.graph(U("urn:g:meta"))}
    assert (str(STREAM), "seq", "2") in meta
    log = next(g for g in ds.graphs() if str(g.identifier).startswith("urn:g:txlog/"))
    assert (U("urn:rev:orders/1/e3/0000000000000000002"), U(PAT + "prevRev"), U(REV1)) in log
    events = graph_holding(ds, "urn:event:4")
    assert (U("urn:event:4"), U(PAT + "revision"), U("urn:rev:orders/1/e3/0000000000000000002")) in events
    assert (U("urn:event:4"), U(PAT + "opSeq"), engines.canon(LONG(1))) in events  # opSeq restarts per request, the seq orders requests


@engines.each_engine_and_guards
def test_h2_6b_t8_the_dataset_guard_variant_writes_a_batch_only_while_the_dataset_epoch_matches():
    wrote = run_append(_store(dataset_epoch=3), stem="append-event-dataset-guard")
    assert (U("urn:event:3"), U(PAT + "revision"), U(REV1)) in graph_holding(wrote, "urn:event:3")
    refused = run_append(_store(dataset_epoch=4), stem="append-event-dataset-guard")
    assert not any(str(g.identifier).startswith("urn:g:events/") for g in refused.graphs() if len(g))


@pytest.mark.parametrize("missing", sorted(set(APPEND) - {"stream"}))
@engines.each_engine
def test_h2_6b_t9_with_the_guard_on_a_batch_missing_any_parameter_writes_nothing(missing):
    ds = _store()
    before = dump(ds)
    run_append(ds, bindings={k: v for k, v in APPEND.items() if k != missing}, guards=True)
    assert dump(ds) == before


# ---- the warning for the receipt models that are declared and not honoured (TD-46) -------------------------------------------


def test_h2_6b_t11_a_snapshot_per_revision_warns_and_names_itself_and_a_patch_log_no_longer_does():
    """Since H2.6d the in-place writes honour dal:PatchLog, so only the snapshot, which no template writes, is reported."""
    from persistence import witness
    from persistence.compiler import compile_targets

    def messages(graph):
        return [d.message for t in compile_targets(graph) for d in t.diagnostics if d.kind == "ReceiptModelNotHonoured"]

    (message,) = messages(witness._load_fixture(witness.WITNESS_DIR / "warning-ReceiptModelNotHonoured.ttl"))
    assert "dal:SnapshotPerRevision" in message and "TD-46" in message
    assert not messages(witness._load_fixture(witness.WITNESS_DIR / "_base-thing.ttl"))  # the base declares dal:PatchLog


def test_h2_6b_t12_a_receipt_only_profile_does_not_warn():
    from persistence import witness
    from persistence.compiler import compile_targets

    graph = witness._load_fixture(witness.WITNESS_DIR / "_base-thing.ttl")
    graph.set((URIRef("https://example.org/lending#ThingProfile"), URIRef("https://www.nebularis.org/neuro-semantic/lattice/persistence#receiptModel"), URIRef("https://www.nebularis.org/neuro-semantic/lattice/persistence#ReceiptOnly")))
    assert not [d for t in compile_targets(graph) for d in t.diagnostics if d.kind == "ReceiptModelNotHonoured"]
