"""DR4: the bulk load and the recorded state digest (persistence delta replace unit), carried over from the studio line's slice DR2.
Validation Pack: docs/developer/validation/DR2.md, the studio line's, whose test IDs are DR2-Tn.

A bulk load is one request of, for each aggregate, its create and its whole replace, under one transaction id, so whichever half
applies claims it and the other does nothing. A family that records its state digest sends `record-state-digest` after its write in
the same request, and `state-digest-audit` returns what a caller needs to recompute the digest."""

from __future__ import annotations

import re
import warnings
from urllib.parse import quote

import engines
from rdflib import RDF, Literal, URIRef
from rdflib.namespace import XSD

from builder_goldens import CANONICAL_CONTEXT
from lattice_persistence import Iri, Lit, Payload, Triple, compose, state_digest
from persistence.builders import build
from persistence.ir_render import render

EX = "https://example.org/lending#"
PAT = "https://www.nebularis.org/neuro-semantic/lattice/persistence-store#"
META, TXN = URIRef("urn:g:meta/17"), URIRef("urn:g:txn")
OLD, NEW = URIRef("urn:order:1"), URIRef("urn:order:2")
STATUS = URIRef(EX + "status")


def _graph_of(root: URIRef) -> URIRef:
    return URIRef("urn:g:orders/" + quote(str(root), safe="") + "/data")


def _nt(triples) -> str:
    return " ".join(f"{s.n3()} {p.n3()} {o.n3()} ." for s, p, o in sorted(triples))


def _op(template: str, values: dict, **slots) -> str:
    """A filled request: the slots by marker and the parameters by name. Tests only, since a caller binds parameters through its own
    prepared query."""
    text = render(build(template, CANONICAL_CONTEXT, guards=engines.guards()))
    for name, triples in slots.items():
        text = text.replace("{{{" + name + "}}}", _nt(triples))
    for name in sorted(values, key=len, reverse=True):
        text = re.sub(r"\$" + name + r"\b", values[name].n3(), text)
    assert "{{{" not in text and not re.search(r"\$[A-Za-z]", text)
    return text


def _row(root: URIRef, seq: int, rev: str, txn: str) -> dict:
    return {
        "root": root, "epoch": Literal(1, datatype=XSD.long), "expectedSeq": Literal(seq, datatype=XSD.long),
        "nextSeq": Literal(seq + 1, datatype=XSD.long), "newRev": URIRef(rev), "txnId": URIRef(txn), "requestDigest": Literal("d"),
    }


def _load(root: URIRef, believed_seq: int, state: set, txn: str) -> list[str]:
    """One aggregate's half of a bulk load, its create and its whole replace under one transaction id."""
    create = {k: v for k, v in _row(root, 0, f"urn:rev:{root}:new", txn).items() if k not in ("expectedSeq", "nextSeq")}
    return [
        _op("create-if-absent-named-graph", create, payloadTriples=state),
        _op("cas-replace-named-graph", _row(root, believed_seq, f"urn:rev:{root}:next", txn), payloadTriples=state),
    ]


def _dataset():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        ds = engines.dataset()
    ds.graph(META).add((OLD, URIRef(PAT + "epoch"), Literal(1, datatype=XSD.long)))
    ds.graph(META).add((OLD, URIRef(PAT + "seq"), Literal(1, datatype=XSD.long)))
    ds.graph(_graph_of(OLD)).add((OLD, STATUS, Literal("open")))
    return ds


def _update(ds, text: str) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        ds.update(text)


def _graph(ds, name) -> set:
    return {(s, p, o) for s, p, o in ds.graph(name)}


def _seq(ds, root):
    return {o for s, p, o in ds.graph(META) if s == root and p == URIRef(PAT + "seq")}


PAID = {(OLD, STATUS, Literal("paid")), (OLD, RDF.type, URIRef(EX + "Order"))}
FRESH = {(NEW, STATUS, Literal("open")), (NEW, RDF.type, URIRef(EX + "Order"))}
canon = lambda triples: {tuple(engines.canon(t) for t in triple) for triple in triples}


@engines.each_engine_and_guards
def test_dr2_t1_a_bulk_load_creates_the_new_aggregate_and_replaces_the_existing_one_in_one_request():
    ds = _dataset()
    _update(ds, compose(*_load(OLD, 1, PAID, "urn:txn:1"), *_load(NEW, 0, FRESH, "urn:txn:2")))
    assert _graph(ds, _graph_of(OLD)) == canon(PAID) and _graph(ds, _graph_of(NEW)) == canon(FRESH)
    assert _seq(ds, OLD) == {engines.canon(Literal(2, datatype=XSD.long))} and _seq(ds, NEW) == {engines.canon(Literal(1, datatype=XSD.long))}


@engines.each_engine_and_guards
def test_dr2_t2_an_aggregate_whose_row_moved_is_left_as_it_was_and_the_others_load():
    ds = _dataset()
    _update(ds, compose(*_load(OLD, 5, PAID, "urn:txn:1"), *_load(NEW, 0, FRESH, "urn:txn:2")))
    assert _graph(ds, _graph_of(OLD)) == canon({(OLD, STATUS, Literal("open"))}) and _seq(ds, OLD) == {engines.canon(Literal(1, datatype=XSD.long))}
    assert _graph(ds, _graph_of(NEW)) == canon(FRESH)


def _payload(triples) -> Payload:
    return Payload.of(*(Triple(Iri.encode(str(s)), Iri.encode(str(p)), Iri.encode(str(o)) if isinstance(o, URIRef) else Lit(str(o)))
                        for s, p, o in triples))


@engines.each_engine_and_guards
def test_dr2_t3_a_recorded_state_digest_matches_the_state_and_an_edit_outside_the_operations_is_found():
    ds = _dataset()
    row = _row(OLD, 1, "urn:rev:2", "urn:txn:1")
    digest = state_digest(_payload(PAID))
    record = {k: row[k] for k in ("root", "nextSeq", "newRev", "txnId")} | {"stateDigest": Literal(digest)}
    _update(ds, compose(_op("cas-replace-named-graph", row, payloadTriples=PAID), _op("record-state-digest", record)))
    audit = render(build("state-digest-audit-named-graph", CANONICAL_CONTEXT, guards=engines.guards())).replace("$root", OLD.n3())

    def recomputed():
        rows = list(ds.query(audit))
        assert {str(r[0]) for r in rows} == {digest}
        return state_digest(_payload({(r[1], r[2], r[3]) for r in rows if r[1] is not None}))

    assert recomputed() == digest
    ds.graph(_graph_of(OLD)).add((OLD, URIRef(EX + "note"), Literal("by hand")))
    assert recomputed() != digest


@engines.each_engine_and_guards
def test_dr2_t4_a_digest_after_a_stale_write_records_nothing():
    ds = _dataset()
    row = _row(OLD, 5, "urn:rev:6", "urn:txn:1")
    record = {k: row[k] for k in ("root", "nextSeq", "newRev", "txnId")} | {"stateDigest": Literal("x")}
    _update(ds, compose(_op("cas-replace-named-graph", row, payloadTriples=PAID), _op("record-state-digest", record)))
    assert not [o for s, p, o in ds.graph(META) if p == URIRef(PAT + "stateDigest")]


def test_dr2_t5_compose_hoists_one_prologue_and_refuses_a_prefix_bound_twice():
    import pytest

    joined = compose("PREFIX a: <urn:a#>\nINSERT DATA { GRAPH <urn:g> { a:x a:y a:z } }", "PREFIX a: <urn:a#>\nPREFIX b: <urn:b#>\nINSERT DATA { GRAPH <urn:g> { b:x b:y a:z } } ;")
    assert joined.splitlines()[:2] == ["PREFIX a: <urn:a#>", "PREFIX b: <urn:b#>"] and joined.count("PREFIX") == 2 and joined.count(" ;\n") == 1
    with pytest.raises(ValueError):
        compose("PREFIX a: <urn:a#>\nINSERT DATA { }", "PREFIX a: <urn:other#>\nINSERT DATA { }")
    with pytest.raises(ValueError):
        compose()
