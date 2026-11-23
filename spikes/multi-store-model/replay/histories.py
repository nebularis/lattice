# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The histories of the behaviour tests of the four operations, replayed on the RDF realisation and written for the exported interpreter.

Each history is a seed and a list of commands, transcribed from a behaviour test of ``tools/persistence/tests`` that runs one of the
four builders the paper lowering of MSA-I4 reads: ``create-if-absent-named-graph-patch-log``, ``cas-replace-named-graph-delta-patch-log``,
``append-event-dataset-guard`` and ``key-claim-write``. Each history names its test. The RDF side renders each builder once, fills its
request-time slots and runs it on Oxigraph through the test-support store, as the tests do. The model side is a file of tab-separated
records the Scala driver reads.

Both sides read their state back into the same lines, one resource a line, so the two can be compared after every command. The time a
receipt was recorded and the month of a bucket come from the store's clock and are left out, as the tests leave them out.
"""

from __future__ import annotations

import time
import urllib.parse
from dataclasses import dataclass, field

import pyoxigraph as ox
from lattice_testing_oxigraph import OxigraphStore
from persistence.builders import build
from persistence.ir_render import render
from persistence.terms import Iri, Literal

PAT = "https://www.nebularis.org/neuro-semantic/lattice/persistence-store#"
XSD = "http://www.w3.org/2001/XMLSchema#"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

META, TXN, LOG, EVENTS, ORDERS, KEYS, DATASET, DATASET_NODE = (
    "urn:g:meta", "urn:g:txn", "urn:g:txlog/", "urn:g:events/order/", "urn:g:orders/", "urn:g:keys", "urn:g:dataset", "urn:g:dataset-node",
)
CONSTRAINT = "c1"

# One context for the four builders, the union of the contexts of test_patch_log, test_builders and test_key_claims_and_audits, with
# one meta graph for every family. A graph's name is a layout and no guard reads it.
CONTEXT = {
    "metaGraphPrefix": Iri.encode(META), "txnGraph": Iri.encode(TXN), "logGraphPrefix": Iri.encode(LOG),
    "eventGraphPrefix": Iri.encode(EVENTS), "datasetGraph": Iri.encode(DATASET), "datasetNode": Iri.encode(DATASET_NODE),
    "graphPrefix": Literal.encode(ORDERS), "graphSuffix": Literal.encode(""), "dataGraph": Iri.encode("urn:g:orders"),
    "keysGraph": Iri.encode(KEYS), "keyQuarantineGraph": Iri.encode("urn:g:key-quarantine"), "retentionGraph": Iri.encode("urn:g:retention"),
    "pinnedGraph": Iri.encode("urn:g:txlog/pinned"), "constraintId": Literal.encode(CONSTRAINT), "mergeRelation": Iri.encode("urn:rel:supersededBy"),
}
BUILDERS = {
    "create": "create-if-absent-named-graph-patch-log", "replace": "cas-replace-named-graph-delta-patch-log",
    "append": "append-event-dataset-guard", "claim": "key-claim-write",
}


def iri(value: str) -> ox.NamedNode:
    return ox.NamedNode(value)


def long(n: int) -> ox.Literal:
    return ox.Literal(str(n), datatype=ox.NamedNode(XSD + "long"))


def string(value: str) -> ox.Literal:
    return ox.Literal(value)


def nt(triple: tuple) -> str:
    """One triple as an N-Triples line, the text of a fact on both sides."""
    s, p, o = triple
    return f"{s} {p} {o} ."


@dataclass(frozen=True)
class Command:
    op: str
    bindings: dict
    slots: dict
    model: tuple  # (record, pname, value) for the Scala driver
    expect: str   # the outcome the test states


@dataclass(frozen=True)
class History:
    name: str
    test: str
    vrows: tuple = ()   # (root, epoch, seq, head or "")
    aggs: tuple = ()    # (root, triple)
    depoch: int | None = None
    commands: tuple = field(default_factory=tuple)


def _atom(pname: str, term) -> tuple:
    return ("PA", pname, term.value)


def _facts(pname: str, facts: list[str]) -> list[tuple]:
    return [("PF", pname, f) for f in facts] or [("PE", pname, "")]


# ---- test_patch_log: the create and the delta replace of a named-graph family under a patch log -------------------------

ROOT, P, Q = "urn:order:1", "urn:p:status", "urn:p:note"
OLD_PREV = "urn:rev:order/1/prev"
DIGEST = "ab" * 32


def t(s: str, p: str, o: str) -> tuple:
    return (iri(s), iri(p), string(o))


OLD = (t(ROOT, P, "old"), t(ROOT, Q, "keep"))
ADDED, REMOVED = t(ROOT, P, "new"), t(ROOT, P, "old")
PAYLOAD = (t(ROOT, P, "new"), t(ROOT, Q, "keep"))
SEEDED = {"vrows": ((ROOT, 1, 1, OLD_PREV),), "aggs": tuple((ROOT, x) for x in OLD)}


def create(n: int, payload, *, txn: str | None = None, expect: str) -> Command:
    b = {"root": iri(ROOT), "epoch": long(1), "newRev": iri(f"urn:rev:order/1/{n}"), "txnId": iri(txn or f"urn:txn:{n}"), "requestDigest": string(DIGEST)}
    facts = [nt(x) for x in payload]
    model = (_atom("Root", b["root"]), ("PN", "EpochP", "1"), _atom("NewRev", b["newRev"]), _atom("TxnId", b["txnId"]),
             _atom("RequestDigest", b["requestDigest"]), *_facts("Payload", facts))
    return Command("create", b, {"payloadTriples": " ".join(facts)}, model, expect)


def replace(seq: int, n: int, asserted, retracted, *, txn: str | None = None, expect: str) -> Command:
    b = {"root": iri(ROOT), "epoch": long(1), "expectedSeq": long(seq), "nextSeq": long(seq + 1), "newRev": iri(f"urn:rev:order/1/{n}"),
         "txnId": iri(txn or f"urn:txn:{n}"), "requestDigest": string(DIGEST)}
    add, delete = [nt(x) for x in asserted], [nt(x) for x in retracted]
    model = (_atom("Root", b["root"]), ("PN", "EpochP", "1"), ("PN", "ExpectedSeq", str(seq)), _atom("NewRev", b["newRev"]),
             _atom("TxnId", b["txnId"]), _atom("RequestDigest", b["requestDigest"]), *_facts("Asserted", add), *_facts("Retracted", delete))
    return Command("replace", b, {"assertTriples": " ".join(add), "retractTriples": " ".join(delete)}, model, expect)


# ---- test_append_events: the append of several events in one request, on the dataset-guard variant --------------------

STREAM, REV_BASE = "urn:stream:orders/1", "urn:rev:orders/1/e3/"
AT = "2026-10-12T10:00:00Z"
DOMAIN = (t("urn:event:1", "urn:ex:amount", "10"), t("urn:event:2", "urn:ex:amount", "20"), t("urn:event:3", "urn:ex:amount", "30"))
THREE = tuple((f"urn:event:{n}", f"urn:type:T{n}", n, AT) for n in (1, 2, 3))
STREAM_SEED = {"vrows": ((STREAM, 3, 0, ""),), "depoch": 3}


def append(rows, triples=(), *, txn: str = "urn:txn:1", expect: str) -> Command:
    b = {"stream": iri(STREAM), "epoch": long(3), "revBase": string(REV_BASE), "txnId": iri(txn), "requestDigest": string(DIGEST)}
    row_text = " ".join(f'(<{e}> <{ty}> "{op}"^^<{XSD}long> "{at}"^^<{XSD}dateTime>)' for e, ty, op, at in rows)
    facts = [f"ROW {e} {ty} {op} {at}" for e, ty, op, at in rows] + [nt(x) for x in triples]
    model = (_atom("Stream", b["stream"]), ("PN", "EpochP", "3"), _atom("RevBase", b["revBase"]), _atom("TxnId", b["txnId"]),
             _atom("RequestDigest", b["requestDigest"]), *_facts("EventRows", facts))
    return Command("append", b, {"eventRows": row_text, "eventTriples": " ".join(nt(x) for x in triples)}, model, expect)


# ---- test_key_claims_and_audits: the key claim write ------------------------------------------------------------------------

def claim(c: str, o: str, *, expect: str) -> Command:
    b = {"claim": iri(c), "owner": iri(o)}
    return Command("claim", b, {}, (_atom("ClaimP", b["claim"]), _atom("OwnerP", b["owner"])), expect)


HISTORIES = (
    History("H01", "test_patch_log.py::test_h2_6d_t1 (named-graph, row guard)", **SEEDED,
            commands=(replace(1, 2, [ADDED], [REMOVED], expect="Applied"),)),
    History("H02", "test_patch_log.py::test_h2_6d_t2 (named-graph)", **SEEDED,
            commands=(replace(1, 2, [t(ROOT, "urn:p:other", "only in the delta")], [], expect="Applied"),)),
    History("H03", "test_patch_log.py::test_h2_6d_t4 (named-graph)",
            commands=(create(1, PAYLOAD, expect="Applied"),)),
    History("H04", "test_patch_log.py::test_h2_6d_t5 (create, named-graph)",
            commands=(create(1, PAYLOAD, expect="Applied"), create(1, PAYLOAD, expect="Duplicate"))),
    History("H05", "test_patch_log.py::test_h2_6d_t5 (replace, named-graph)", **SEEDED,
            commands=(replace(1, 2, [ADDED], [REMOVED], expect="Applied"), replace(1, 2, [ADDED], [REMOVED], expect="Duplicate"))),
    History("H06", "test_patch_log.py::test_h2_6d_t6 (create, named-graph)", **SEEDED,
            commands=(create(9, PAYLOAD, expect="Conflict Exists"),)),
    History("H07", "test_patch_log.py::test_h2_6d_t6 (replace, named-graph)", **SEEDED,
            commands=(replace(5, 9, [ADDED], [REMOVED], expect="Conflict Stale"),)),
    History("H08", "test_patch_log.py::test_h2_6d_t9 (named-graph)", **SEEDED,
            commands=(replace(1, 2, [], [], expect="Applied"),)),
    History("H09", "test_patch_log.py::test_h2_6d_t10 (named-graph, the create and the replace)",
            commands=(create(1, [t(ROOT, P, "v1"), t(ROOT, Q, "keep")], expect="Applied"),
                      replace(1, 2, [t(ROOT, P, "v2")], [t(ROOT, P, "v1")], expect="Applied"))),
    History("H10", "test_append_events.py::test_h2_6b_t1", **STREAM_SEED,
            commands=(append(THREE, DOMAIN, expect="Applied"),)),
    History("H11", "test_append_events.py::test_h2_6b_t3", **STREAM_SEED,
            commands=(append(THREE, DOMAIN, expect="Applied"), append(THREE, DOMAIN, expect="Duplicate"))),
    History("H12", "test_append_events.py::test_h2_6b_t5", **STREAM_SEED,
            commands=(append([("urn:event:9", "urn:type:Placed", 7, AT)], expect="Applied"),)),
    History("H13", "test_append_events.py::test_h2_6b_t7", **STREAM_SEED,
            commands=(append(THREE, expect="Applied"), append([("urn:event:4", "urn:type:T4", 1, AT)], txn="urn:txn:2", expect="Applied"))),
    History("H14", "test_append_events.py::test_h2_6b_t8 (the dataset epoch matches)", **STREAM_SEED,
            commands=(append(THREE, expect="Applied"),)),
    History("H15", "test_append_events.py::test_h2_6b_t8 (the dataset epoch has moved)", vrows=((STREAM, 3, 0, ""),), depoch=4,
            commands=(append(THREE, expect="Refused EpochMismatch"),)),
    History("H16", "test_key_claims_and_audits.py::test_h2_5_t15",
            commands=(claim("urn:c:1", "urn:o:1", expect="Applied"), claim("urn:c:1", "urn:o:2", expect="Conflict HeldByOther"))),
    History("H17", "test_key_claims_and_audits.py::test_h2_5_t16",
            commands=(claim("urn:c:1", "urn:o:1", expect="Applied"), claim("urn:c:1", "urn:o:1", expect="Applied"),
                      claim("urn:c:2", "urn:o:2", expect="Applied"))),
)


# ---- the model's side ---------------------------------------------------------------------------------------------------------

def to_tsv(histories=HISTORIES) -> str:
    """The histories as the Scala driver reads them, one record a line."""
    lines = []
    for h in histories:
        lines.append(f"H\t{h.name}")
        lines += [f"SV\t{root}\t{epoch}\t{seq}\t{head}" for root, epoch, seq, head in h.vrows]
        lines += [f"SA\t{root}\t{nt(x)}" for root, x in h.aggs]
        if h.depoch is not None:
            lines.append(f"SD\t{h.depoch}")
        for c in h.commands:
            lines.append(f"C\t{c.op}\t{CONSTRAINT if c.op == 'claim' else ''}")
            lines += ["\t".join(record) for record in c.model]
    return "\n".join(lines) + "\n"


# ---- the RDF side -------------------------------------------------------------------------------------------------------------

def templates() -> dict:
    """Each builder rendered once, with its parameter guards on, as the compiler gives it."""
    return {op: render(build(name, CONTEXT, guards=True)) for op, name in BUILDERS.items()}


def seeded(h: History) -> OxigraphStore:
    store = OxigraphStore()
    for root, epoch, seq, head in h.vrows:
        store.add(iri(root), iri(PAT + "epoch"), long(epoch), iri(META))
        store.add(iri(root), iri(PAT + "seq"), long(seq), iri(META))
        if head:
            store.add(iri(root), iri(PAT + "head"), iri(head), iri(META))
    for root, (s, p, o) in h.aggs:
        store.add(s, p, o, iri(ORDERS + urllib.parse.quote(root, safe="")))
    if h.depoch is not None:
        store.add(iri(DATASET_NODE), iri(PAT + "epoch"), long(h.depoch), iri(DATASET))
    return store


def run(store: OxigraphStore, text: str, c: Command) -> None:
    for slot, value in c.slots.items():
        text = text.replace("{{{" + slot + "}}}", value)
    store.update(text, c.bindings, strict=False)


def rdf_state(store: OxigraphStore) -> list[str]:
    """The store read back as the model's resources, one line each, sorted."""
    by_graph: dict[str, list] = {}
    for q in store.quads():
        name = "" if isinstance(q.graph_name, ox.DefaultGraph) else q.graph_name.value
        by_graph.setdefault(name, []).append(q)

    def objects(quads, s, p):
        return [q.object for q in quads if q.subject == s and q.predicate.value == p]

    def one(quads, s, p):
        found = objects(quads, s, p)
        return found[0].value if found else "-"

    out: list[str] = []
    meta = by_graph.get(META, [])
    for s in sorted({q.subject for q in meta if q.predicate.value == PAT + "seq"}, key=str):
        deleted = "true" if one(meta, s, PAT + "deleted") == "true" else "false"
        out.append(f"vrow\t{s.value}\tepoch={one(meta, s, PAT + 'epoch')}\tseq={one(meta, s, PAT + 'seq')}\thead={one(meta, s, PAT + 'head')}\tdeleted={deleted}")
    txn = by_graph.get(TXN, [])
    for s in sorted({q.subject for q in txn}, key=str):
        out.append(f"txn\t{s.value}\trev={one(txn, s, PAT + 'rev')}\tdigest={one(txn, s, PAT + 'requestDigest')}")
    receipts: dict[str, tuple] = {}
    for name, quads in by_graph.items():
        if name.startswith(LOG):
            for s in {q.subject for q in quads if q.predicate.value == PAT + "target"}:
                key = (one(quads, s, PAT + "target"), one(quads, s, PAT + "epoch"), one(quads, s, PAT + "seq"))
                receipts[s.value] = key
                out.append(f"rcpt\t{key[0]}\t{key[1]}\t{key[2]}\trev={s.value}\tprev={one(quads, s, PAT + 'prevRev')}\ttxn={one(quads, s, PAT + 'txn')}")
    for rev, (target, epoch, seq) in receipts.items():
        for direction in ("add", "del"):
            out += [f"patch\t{target}\t{epoch}\t{seq}\t{direction}\t{nt((q.subject, q.predicate, q.object))}" for q in by_graph.get(f"{rev}/{direction}", [])]
    for name, quads in by_graph.items():
        if name.startswith(ORDERS):
            root = urllib.parse.unquote(name[len(ORDERS):])
            out += [f"agg\t{root}\t{nt((q.subject, q.predicate, q.object))}" for q in quads]
        if name.startswith(EVENTS):
            row_predicates = {RDF_TYPE, PAT + "revision", PAT + "opSeq", PAT + "occurredAt"}
            for s in {q.subject for q in quads if q.predicate.value == PAT + "revision"}:
                target, _, seq = receipts.get(one(quads, s, PAT + "revision"), ("?", "?", "?"))
                out.append(f"evrow\t{target}\t{seq}\t{s.value} {one(quads, s, RDF_TYPE)} {one(quads, s, PAT + 'opSeq')} {one(quads, s, PAT + 'occurredAt')}")
            out += [f"evfact\t{nt((q.subject, q.predicate, q.object))}" for q in quads if q.predicate.value not in row_predicates]
    keys = by_graph.get(KEYS, [])
    for s in sorted({q.subject for q in keys if q.predicate.value == PAT + "claimedBy"}, key=str):
        out.append(f"claim\t{s.value}\tconstraint={one(keys, s, PAT + 'constraint')}\towner={one(keys, s, PAT + 'claimedBy')}")
    for q in by_graph.get(DATASET, []):
        out.append(f"depoch\t{q.object.value}")
    return sorted(set(out))


def rdf_check(histories=HISTORIES) -> list[str]:
    """The state after every command, in the form the Scala driver's check mode writes, less the outcome, which the RDF side does not return."""
    texts, lines = templates(), []
    for h in histories:
        store = seeded(h)
        lines.append(f"H\t{h.name}")
        for i, c in enumerate(h.commands, 1):
            run(store, texts[c.op], c)
            lines += [f"S\t{i}\t{line}" for line in rdf_state(store)]
    return lines


def rdf_time(rounds: int, histories=HISTORIES) -> list[int]:
    """The time of each round, in nanoseconds: every history's commands, each on a fresh store seeded outside the clock."""
    texts, result = templates(), []
    for _ in range(rounds):
        total = 0
        for h in histories:
            store = seeded(h)
            t0 = time.perf_counter_ns()
            for c in h.commands:
                run(store, texts[c.op], c)
            total += time.perf_counter_ns() - t0
        result.append(total)
    return result
