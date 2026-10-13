# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""H2.5, gates 4 and 5: the five key-claim operations and the five audits, run on each engine (plan 4.3). The ports are held to
their templates by the harness of `test_builders.py`. These tests run what they write and find. Validation Pack:
docs/developer/validation/FMH-H2-5.md. Test IDs are H2.5-Tn."""

from __future__ import annotations

import pytest
from rdflib import RDF, XSD, Literal as RdfLiteral, URIRef

import engines
from persistence.builders import build
from persistence.ir_render import render
from persistence.terms import Iri, Literal

from test_builders import CONTEXT as BASE, LONG, PAT

U = URIRef
KEYS, QUARANTINE, RETENTION, PINNED, META, TXN = (U(f"urn:g:{n}") for n in ("keys", "key-quarantine", "retention", "txlog/pinned", "meta", "txn"))
BUCKETS = ("urn:g:txlog/2026-09", "urn:g:txlog/2026-10")
CONTEXT = {
    **BASE,
    "keysGraph": Iri.encode("urn:g:keys"), "keyQuarantineGraph": Iri.encode("urn:g:key-quarantine"),
    "retentionGraph": Iri.encode("urn:g:retention"), "pinnedGraph": Iri.encode("urn:g:txlog/pinned"),
    "constraintId": Literal.encode("c1"), "mergeRelation": Iri.encode("urn:rel:supersededBy"),
}
C1, C2, C3 = U("urn:c:1"), U("urn:c:2"), U("urn:c:3")
O1, O2, O3 = U("urn:o:1"), U("urn:o:2"), U("urn:o:3")
RELATION = U("urn:rel:supersededBy")
RETIRED_AT = RdfLiteral("2026-10-13T09:00:00Z", datatype=XSD.dateTime)


def sparql(stem: str, guards: bool | None = None, buckets=BUCKETS) -> str:
    text = render(build(stem, CONTEXT, guards=engines.guards(guards)))
    return text.replace("{{{logGraphs}}}", " ".join(f"<{b}>" for b in buckets))


def update(stem: str, ds, args: dict | None = None, guards: bool | None = None):
    ds.update(sparql(stem, guards), initBindings=args or {})
    return ds


def rows(stem: str, ds, buckets=BUCKETS) -> list:
    return sorted(tuple(None if t is None else str(t) for t in row) for row in ds.query(sparql(stem, True, buckets)))


def graph_of(ds, name: URIRef) -> set:
    return {(s, p, o) for s, p, o in ds.graph(name)}


def claimed(claim: URIRef, owner: URIRef, constraint: str = "c1") -> set:
    return {(claim, RDF.type, U(PAT + "KeyClaim")), (claim, U(PAT + "constraint"), RdfLiteral(constraint)), (claim, U(PAT + "claimedBy"), owner)}


def with_claims(*claims, constraint: str = "c1"):
    """A dataset whose keys graph holds each `(claim, owner)` as the guarded write leaves it."""
    ds = engines.dataset()
    keys = ds.graph(KEYS)
    for claim, owner in claims:
        for triple in claimed(claim, owner, constraint):
            keys.add(triple)
    return ds


def everything(ds) -> set:
    return {(str(g.identifier), str(s), str(p), str(o)) for g in ds.graphs() for s, p, o in g}


# ---- key-claim-write and its dual ----------------------------------------------------------------------------------------


@engines.each_engine_and_guards
def test_h2_5_t15_a_claim_is_written_once_and_refused_to_a_second_owner():
    ds = update("key-claim-write", engines.dataset(), {"claim": C1, "owner": O1})
    assert graph_of(ds, KEYS) == claimed(C1, O1)
    update("key-claim-write", ds, {"claim": C1, "owner": O2})
    assert graph_of(ds, KEYS) == claimed(C1, O1)


@engines.each_engine_and_guards
def test_h2_5_t16_the_owner_may_claim_again_and_another_claim_is_independent():
    ds = update("key-claim-write", engines.dataset(), {"claim": C1, "owner": O1})
    update("key-claim-write", ds, {"claim": C1, "owner": O1})
    update("key-claim-write", ds, {"claim": C2, "owner": O2})
    assert graph_of(ds, KEYS) == claimed(C1, O1) | claimed(C2, O2)


@engines.each_engine_and_guards
def test_h2_5_t17_the_dual_form_writes_both_claims_for_one_owner():
    ds = update("key-claim-write-dual", engines.dataset(), {"claimCurrent": C1, "claimNext": C2, "owner": O1})
    assert graph_of(ds, KEYS) == claimed(C1, O1) | claimed(C2, O1)


@engines.each_engine_and_guards
@pytest.mark.parametrize("held", ["claimCurrent", "claimNext"])
def test_h2_5_t18_the_dual_form_writes_nothing_when_either_claim_is_held_by_another_owner(held):
    """When the next claim is held and the current one is free, nothing is written, so the key is never claimed under one
    scheme version only."""
    taken = {"claimCurrent": C1, "claimNext": C2}[held]
    ds = with_claims((taken, O2))
    before = graph_of(ds, KEYS)
    update("key-claim-write-dual", ds, {"claimCurrent": C1, "claimNext": C2, "owner": O1})
    assert graph_of(ds, KEYS) == before


# ---- retire --------------------------------------------------------------------------------------------------------------


@engines.each_engine_and_guards
def test_h2_5_t19_the_owner_retires_its_claim_and_the_retirement_is_recorded():
    ds = with_claims((C1, O1))
    update("key-claim-retire", ds, {"claim": C1, "owner": O1, "now": RETIRED_AT})
    triples = graph_of(ds, KEYS)
    assert (C1, U(PAT + "claimedBy"), O1) not in triples
    assert (C1, U(PAT + "retiredBy"), O1) in triples and (C1, U(PAT + "retiredAt"), RETIRED_AT) in triples


@engines.each_engine_and_guards
def test_h2_5_t20_another_owner_cannot_retire_a_claim():
    ds = with_claims((C1, O1))
    update("key-claim-retire", ds, {"claim": C1, "owner": O2, "now": RETIRED_AT})
    assert graph_of(ds, KEYS) == claimed(C1, O1)


@engines.each_engine
def test_h2_5_t21_retire_accepts_a_timestamp_of_any_datatype_and_refuses_an_iri_or_a_language_string_with_the_guard_on():
    for value, written in ((RdfLiteral("2026-10-13", datatype=XSD.date), True), (RdfLiteral("2026-10-13T09:00:00Z", datatype=XSD.dateTimeStamp), True),
                           (RdfLiteral("yesterday"), True), (U("urn:when"), False), (RdfLiteral("hier", lang="fr"), False)):
        ds = with_claims((C1, O1))
        update("key-claim-retire", ds, {"claim": C1, "owner": O1, "now": value}, guards=True)
        assert ((C1, U(PAT + "retiredBy"), O1) in graph_of(ds, KEYS)) is written, value


# ---- missing and mistyped parameters -------------------------------------------------------------------------------------

_ARGS = {
    "key-claim-write": {"claim": C1, "owner": O1},
    "key-claim-write-dual": {"claimCurrent": C1, "claimNext": C2, "owner": O1},
    "key-claim-retire": {"claim": C1, "owner": O1, "now": RETIRED_AT},
}
_MISSING = [(stem, name) for stem, args in _ARGS.items() for name in args]


def _start(stem: str):
    """The retire starts with two claims, so that a retire which names no claim shows what it would reach."""
    return with_claims((C1, O1), (C2, O2)) if stem == "key-claim-retire" else engines.dataset()


def _short(quad) -> str:
    graph, s, p, o = quad
    local = lambda t: t.removeprefix(PAT).removeprefix("urn:").removeprefix("c:").replace("2026-10-13T09:00:00+00:00", "T")
    return " ".join(local(t) for t in (graph.removeprefix("urn:g:"), s, p.removeprefix("http://www.w3.org/1999/02/22-rdf-syntax-ns#"), o))


@engines.each_engine
@pytest.mark.parametrize("stem, missing", _MISSING, ids=[f"{s}-no-{m}" for s, m in _MISSING])
def test_h2_5_t22_with_the_guard_on_a_key_claim_operation_missing_any_parameter_writes_nothing(stem, missing):
    ds = _start(stem)
    before = everything(ds)
    update(stem, ds, {k: v for k, v in _ARGS[stem].items() if k != missing}, guards=True)
    assert everything(ds) == before


# What each engine writes with the guard off when a parameter is left out. A claim with no owner is the harm the guard
# prevents. The two engines agree on every case, so the table has no engine column.
_UNGUARDED: dict = {
    ("key-claim-write", "claim"): ([], []),
    ("key-claim-write", "owner"): (["keys 1 constraint c1", "keys 1 type KeyClaim"], []),
    ("key-claim-write-dual", "claimCurrent"): (["keys 2 claimedBy o:1", "keys 2 constraint c1", "keys 2 type KeyClaim"], []),
    ("key-claim-write-dual", "claimNext"): (["keys 1 claimedBy o:1", "keys 1 constraint c1", "keys 1 type KeyClaim"], []),
    ("key-claim-write-dual", "owner"): (["keys 1 constraint c1", "keys 1 type KeyClaim", "keys 2 constraint c1", "keys 2 type KeyClaim"], []),
    # a retire that names no claim, or no owner, matches the claims of the owner it does name, or the claim with any owner
    ("key-claim-retire", "claim"): (["keys 1 retiredAt T", "keys 1 retiredBy o:1"], ["keys 1 claimedBy o:1"]),
    ("key-claim-retire", "owner"): (["keys 1 retiredAt T", "keys 1 retiredBy o:1"], ["keys 1 claimedBy o:1"]),
    # a retire without a time retires the claim and records who, and not when
    ("key-claim-retire", "now"): (["keys 1 retiredBy o:1"], ["keys 1 claimedBy o:1"]),
}


@engines.each_engine
@pytest.mark.parametrize("stem, missing", _MISSING, ids=[f"{s}-no-{m}" for s, m in _MISSING])
def test_h2_5_t23_with_the_guard_off_a_key_claim_operation_missing_a_parameter_writes_what_the_table_records(stem, missing):
    ds = _start(stem)
    before = everything(ds)
    update(stem, ds, {k: v for k, v in _ARGS[stem].items() if k != missing}, guards=False)
    after = everything(ds)
    assert (sorted(map(_short, after - before)), sorted(map(_short, before - after))) == _UNGUARDED[(stem, missing)]


@engines.each_engine_and_guards
def test_h2_5_t24_a_stored_literal_owner_blocks_every_other_owner_and_is_not_an_error():
    """The patterns guide's shape makes `pat:claimedBy` an IRI. A literal that got past it is a stored value the comparison
    `?other != $owner` handles as any other term, and the claim stays with it."""
    ds = engines.dataset()
    ds.graph(KEYS).add((C1, U(PAT + "claimedBy"), RdfLiteral("someone")))
    before = graph_of(ds, KEYS)
    update("key-claim-write", ds, {"claim": C1, "owner": O1})
    assert graph_of(ds, KEYS) == before


# ---- quarantine ----------------------------------------------------------------------------------------------------------

DUPLICATED = ((C1, O1), (C1, O2), (C2, O3))


@engines.each_engine_and_guards
def test_h2_5_t25_quarantine_records_every_owner_of_a_duplicated_claim_and_deletes_nothing():
    ds = with_claims(*DUPLICATED)
    before = graph_of(ds, KEYS)
    update("key-claim-quarantine", ds)
    held = graph_of(ds, QUARANTINE)
    assert {(s, o) for s, p, o in held if p == U(PAT + "quarantinedOwner")} == {(C1, O1), (C1, O2)}
    assert any(p == U(PAT + "quarantinedAt") for _, p, _ in held) and (C1, U(PAT + "constraint"), RdfLiteral("c1")) in held
    assert not any(s == C2 for s, _, _ in held)
    assert graph_of(ds, KEYS) == before


@engines.each_engine_and_guards
def test_h2_5_t26_a_second_quarantine_run_writes_nothing_so_no_timestamp_repeats():
    ds = with_claims(*DUPLICATED)
    update("key-claim-quarantine", ds)
    first = graph_of(ds, QUARANTINE)
    update("key-claim-quarantine", ds)
    assert graph_of(ds, QUARANTINE) == first


@engines.each_engine_and_guards
def test_h2_5_t27_quarantine_is_scoped_to_its_constraint():
    ds = with_claims(*DUPLICATED, constraint="c2")
    update("key-claim-quarantine", ds)
    assert graph_of(ds, QUARANTINE) == set()


@engines.each_engine_and_guards
def test_h2_5_t28_a_third_owner_joining_later_is_recorded_without_repeating_the_first_two():
    ds = with_claims(*DUPLICATED)
    update("key-claim-quarantine", ds)
    first = graph_of(ds, QUARANTINE)
    ds.graph(KEYS).add((C1, U(PAT + "claimedBy"), O3))
    update("key-claim-quarantine", ds)
    added = graph_of(ds, QUARANTINE) - first
    assert {(s, o) for s, p, o in added if p == U(PAT + "quarantinedOwner")} == {(C1, O3)}


# ---- merge-rewrite -------------------------------------------------------------------------------------------------------

MERGED = ((C1, O1), (C1, O2), (C1, O3), (C2, O3))


def links(ds) -> set:
    """The merge links in the keys graph as (owner, canonical) text pairs."""
    return {(str(s), str(o)) for s, p, o in graph_of(ds, KEYS) if p == RELATION}


def _expected_links(canonical: URIRef, others) -> set:
    return {(str(o), str(canonical)) for o in others}


@engines.each_engine_and_guards
def test_h2_5_t29_merge_links_every_non_canonical_owner_to_the_lowest_one_in_the_keys_graph_once():
    ds = with_claims(*MERGED)
    update("key-claim-merge-rewrite", ds)
    assert links(ds) == _expected_links(O1, (O2, O3))  # no link from the canonical owner to itself, on either engine
    update("key-claim-merge-rewrite", ds)
    assert links(ds) == _expected_links(O1, (O2, O3))


@engines.each_engine
def test_h2_5_t30_the_canonical_owner_is_an_iri_on_both_engines():
    """TSD-16, decided in FMH-H2-5 (decision 1, option B). `IRI(MIN(STR(?owner)))` gives an IRI where rdflib's `MIN(?owner)` gave a
    literal, so the links are the same on both engines."""
    ds = with_claims(*MERGED)
    update("key-claim-merge-rewrite", ds)
    assert {type(o) for s, p, o in graph_of(ds, KEYS) if p == RELATION} == {URIRef}


@engines.each_engine_and_guards
def test_h2_5_t30b_a_lower_owner_joining_later_changes_the_canonical_owner_and_earlier_links_stay():
    """NQ5, a known property outside the port: how the canonical owner is chosen is `MIN`, and a link written earlier does not
    follow a later choice."""
    ds = with_claims(*MERGED)
    update("key-claim-merge-rewrite", ds)
    low = U("urn:o:0")
    ds.graph(KEYS).add((C1, U(PAT + "claimedBy"), low))
    update("key-claim-merge-rewrite", ds)
    assert links(ds) == _expected_links(O1, (O2, O3)) | _expected_links(low, (O1, O2, O3))


@engines.each_engine_and_guards
def test_h2_5_t31_a_claim_with_one_owner_is_left_alone():
    ds = with_claims((C2, O3))
    before = graph_of(ds, KEYS)
    update("key-claim-merge-rewrite", ds)
    assert graph_of(ds, KEYS) == before


# ---- the audits ----------------------------------------------------------------------------------------------------------


@engines.each_engine
def test_h2_5_t32_the_duplicate_audit_names_a_claim_with_several_owners_and_nothing_on_a_clean_store():
    assert rows("key-claim-duplicate-audit", with_claims((C1, O1), (C2, O2))) == []
    found = rows("key-claim-duplicate-audit", with_claims(*MERGED))
    assert len(found) == 1 and found[0][0] == str(C1) and found[0][1] == "3"
    assert set(found[0][2].split(" ")) == {str(O1), str(O2), str(O3)}  # a set, never the order of GROUP_CONCAT


@engines.each_engine
def test_h2_5_t33_the_duplicate_audit_is_scoped_to_its_constraint():
    assert rows("key-claim-duplicate-audit", with_claims(*MERGED, constraint="c2")) == []


@engines.each_engine
def test_h2_5_t34_the_fork_audit_reports_two_transaction_claims_on_one_revision():
    ds = engines.dataset()
    claims = ds.graph(TXN)
    for txn, rev in (("t1", "r1"), ("t2", "r1"), ("t3", "r2")):
        claims.add((U(f"urn:txn:{txn}"), U(PAT + "rev"), U(f"urn:rev:{rev}")))
    assert rows("fork-detection-audit", ds) == [("urn:rev:r1", "2")]
    assert rows("fork-detection-audit", engines.dataset()) == []


def _receipt(ds, bucket: str, rev: str, *, target: str = "urn:stream:1", seq=None, txn: str | None = None) -> None:
    g, r = ds.graph(U(bucket)), U(f"urn:rev:{rev}")
    g.add((r, RDF.type, U(PAT + "Revision")))
    g.add((r, U(PAT + "target"), U(target)))
    if seq is not None:
        g.add((r, U(PAT + "seq"), seq))
    if txn:
        g.add((r, U(PAT + "txn"), RdfLiteral(txn)))


@engines.each_engine
def test_h2_5_t35_the_receipt_audits_find_a_merged_fork_and_a_request_applied_twice_across_the_listed_buckets_and_the_pinned_graph():
    ds = engines.dataset()
    _receipt(ds, BUCKETS[0], "a", txn="x")
    _receipt(ds, BUCKETS[1], "a", txn="y")                 # one revision, two transactions, in two buckets
    _receipt(ds, "urn:g:txlog/pinned", "p", txn="z")
    _receipt(ds, "urn:g:txlog/pinned", "p", txn="w")      # the pinned graph is always scanned
    _receipt(ds, "urn:g:txlog/2026-08", "u", txn="s")
    _receipt(ds, "urn:g:txlog/2026-08", "u", txn="t")     # a bucket the registry does not list is not scanned
    _receipt(ds, BUCKETS[0], "b", txn="same")
    _receipt(ds, BUCKETS[1], "c", txn="same")              # one transaction, two revisions
    assert rows("revision-multi-txn-audit", ds) == [("urn:rev:a", "2"), ("urn:rev:p", "2")]
    assert rows("txn-multi-revision-audit", ds) == [("same", "2")]
    assert rows("revision-multi-txn-audit", engines.dataset()) == [] and rows("txn-multi-revision-audit", engines.dataset()) == []


@engines.each_engine
def test_h2_5_t36b_a_receipt_held_in_the_pinned_graph_and_in_its_bucket_is_one_receipt_to_the_receipt_audits():
    """The pinned graph keeps the head receipt, which its bucket holds as well. Without `COUNT(DISTINCT ...)` the same
    transaction would be counted twice and a clean store reported as a merged fork."""
    ds = engines.dataset()
    for bucket in (BUCKETS[0], "urn:g:txlog/pinned"):
        _receipt(ds, bucket, "head", txn="only")
    assert rows("revision-multi-txn-audit", ds) == [] and rows("txn-multi-revision-audit", ds) == []


def _row(ds, target: str, seq: int, low: int | None = None) -> None:
    ds.graph(META).add((U(target), RDF.type, U(PAT + "VersionRow")))
    ds.graph(META).add((U(target), U(PAT + "seq"), LONG(seq)))
    if low is not None:
        ds.graph(RETENTION).add((U(target), U(PAT + "retentionLowWaterMark"), LONG(low)))


def _receipts(ds, target: str, seqs, bucket: str = BUCKETS[0]) -> None:
    for n in seqs:
        _receipt(ds, bucket, f"{target}/{n}", target=target, seq=LONG(n))


STREAM = "urn:stream:1"


@engines.each_engine
@pytest.mark.parametrize("name, seq, low, receipts, pinned, expected", [
    ("a complete run of receipts", 3, None, (1, 2, 3), (), []),
    ("a missing receipt", 3, None, (1, 3), (), [(STREAM, "3", "1", "2")]),
    ("no receipt at all", 3, None, (), (), [(STREAM, "3", "1", "0")]),
    ("receipts below the retention low-water mark are not required", 3, 2, (2, 3), (), []),
    ("a gap above the low-water mark", 3, 2, (3,), (), [(STREAM, "3", "2", "1")]),
    ("the head kept in the pinned graph", 3, None, (1, 2), (3,), []),
    ("the head kept in the pinned graph and in its bucket", 3, None, (1, 2, 3), (3,), []),
    ("a bootstrapped row has no receipts", 0, None, (), (), []),
], ids=lambda v: v if isinstance(v, str) else "")
def test_h2_5_t36_the_gap_scan_reports_a_target_whose_receipts_do_not_number_s_minus_l_plus_one(name, seq, low, receipts, pinned, expected):
    ds = engines.dataset()
    _row(ds, STREAM, seq, low)
    _receipts(ds, STREAM, receipts)
    _receipts(ds, STREAM, pinned, "urn:g:txlog/pinned")
    assert rows("gap-scan-audit", ds) == expected


@engines.each_engine
def test_h2_5_t37_the_gap_scan_does_not_count_a_receipt_outside_the_range_or_of_another_target():
    ds = engines.dataset()
    _row(ds, STREAM, 2)
    _receipts(ds, STREAM, (1, 2, 7))                       # a receipt above S is outside the closed range
    _receipts(ds, "urn:stream:other", (1, 2, 3, 4))
    assert rows("gap-scan-audit", ds) == []


@engines.each_engine
def test_h2_5_t38_an_append_then_a_replace_on_one_stream_gives_a_clean_gap_scan():
    import test_named_graph_builders as named
    from test_builders import APPEND, _store

    stream = APPEND["stream"]
    ds = _store()
    ds.update(render(build("append-event", CONTEXT, guards=engines.guards())), initBindings=APPEND)
    buckets = sorted(str(g.identifier) for g in ds.graphs() if str(g.identifier).startswith("urn:g:txlog/"))
    assert buckets
    args = {**named.replace_args(root=stream, expected=1), "epoch": LONG(3)}
    named.run("cas-replace-named-graph", ds, args)
    assert rows("gap-scan-audit", ds, buckets=buckets) == []
    assert (stream, U(PAT + "seq"), engines.canon(LONG(2))) in graph_of(ds, META)


# ---- gate 3: the graph roles ---------------------------------------------------------------------------------------------

_ROLE_NAMES = {"<urn:g:keys>": "keys", "<urn:g:key-quarantine>": "quarantine", "<urn:g:retention>": "retention", "<urn:g:txn>": "txn",
               "<urn:g:meta>": "meta", "?log": "log"}
_ROLES = {
    "key-claim-write": ({"keys"}, {"keys"}), "key-claim-write-dual": ({"keys"}, {"keys"}), "key-claim-retire": ({"keys"}, {"keys"}),
    "key-claim-quarantine": ({"keys", "quarantine"}, {"quarantine"}), "key-claim-merge-rewrite": ({"keys"}, {"keys"}),
    "key-claim-duplicate-audit": ({"keys"}, set()), "fork-detection-audit": ({"txn"}, set()),
    "gap-scan-audit": ({"meta", "retention", "log"}, set()), "revision-multi-txn-audit": ({"log"}, set()),
    "txn-multi-revision-audit": ({"log"}, set()),
}


@pytest.mark.parametrize("stem", sorted(_ROLES))
def test_h2_5_t39_the_ported_operations_read_and_write_only_the_roles_their_graphs_have(stem):
    """Gate 3. No new role is needed, and `?log` ranges over receipts only, so every access to it has the role `log`."""
    from persistence.ir_render import access_sets

    sets = access_sets(build(stem, CONTEXT))
    reads, writes = _ROLES[stem]
    assert {a.role for a in sets.reads} == reads and {a.role for a in sets.writes} == writes
    for access in sets.reads | sets.writes:
        assert _ROLE_NAMES[access.graph] == access.role, access


def test_h2_5_t40_the_role_table_gained_no_entry_in_this_slice():
    from persistence.builders import GRAPH_ROLES

    assert set(GRAPH_ROLES) == {
        "metaGraphPrefix", "txnGraph", "datasetGraph", "dataGraph", "keysGraph", "keyQuarantineGraph", "retentionGraph", "pinnedGraph",
        "g", "log", "logGraph", "logGraph2", "eventGraph",
    }


# ---- gate 6: what each engine does with the audits' functions (TSD-Q6, Q7, Q10, TSD-16 to TSD-18) ---------------------------------


def _scalar(ds, text: str):
    return [tuple(t for t in row) for row in ds.query(text)][0]


@engines.each_engine
def test_h2_5_t41_min_and_max_over_iris_return_the_lowest_and_highest_by_text_as_an_iri_on_oxigraph_and_as_a_literal_on_rdflib():
    """TSD-16. `urn:o:10` sorts before `urn:o:2` on both, since the comparison is of the IRI text."""
    ds = engines.dataset()
    ds.update("INSERT DATA { GRAPH <urn:g> { <urn:c> <urn:p> <urn:o:2> , <urn:o:10> , <urn:o:1> } }")
    low, high = _scalar(ds, "SELECT (MIN(?o) AS ?l) (MAX(?o) AS ?h) WHERE { GRAPH <urn:g> { <urn:c> <urn:p> ?o } }")
    assert (str(low), str(high)) == ("urn:o:1", "urn:o:2")
    assert type(low) is (RdfLiteral if engines.CURRENT == "rdflib" else URIRef)
    (wrapped,) = _scalar(ds, "SELECT (IRI(MIN(STR(?o))) AS ?l) WHERE { GRAPH <urn:g> { <urn:c> <urn:p> ?o } }")
    assert wrapped == U("urn:o:1")  # the store independent form, on both


@engines.each_engine
def test_h2_5_t42_count_distinct_counts_xsd_long_and_xsd_integer_terms_apart_on_rdflib_and_together_on_oxigraph():
    """TSD-18, the answer to TSD-Q10 for the counts. The gap scan counts distinct `seq` terms, so a receipt written with another
    integer type adds to the count on rdflib and not on Oxigraph."""
    ds = engines.dataset()
    ds.update(
        'INSERT DATA { GRAPH <urn:g> { <urn:s> <urn:p> "1"^^<http://www.w3.org/2001/XMLSchema#long> , "1"^^<http://www.w3.org/2001/XMLSchema#integer> , '
        '"2"^^<http://www.w3.org/2001/XMLSchema#long> } }'
    )
    (stored,) = _scalar(ds, "SELECT (COUNT(DISTINCT ?o) AS ?n) WHERE { GRAPH <urn:g> { <urn:s> <urn:p> ?o } }")
    assert int(stored) == (3 if engines.CURRENT == "rdflib" else 2)
    (valued,) = _scalar(ds, 'SELECT (COUNT(DISTINCT ?o) AS ?n) WHERE { VALUES ?o { "1"^^<http://www.w3.org/2001/XMLSchema#long> "1"^^<http://www.w3.org/2001/XMLSchema#integer> } }')
    assert int(valued) == (2 if engines.CURRENT == "rdflib" else 1)


@engines.each_engine
def test_h2_5_t43_a_duplicate_seq_written_with_another_integer_type_is_reported_by_the_gap_scan_on_rdflib_only():
    ds = engines.dataset()
    _row(ds, STREAM, 1)
    _receipt(ds, BUCKETS[0], "a", target=STREAM, seq=LONG(1))
    _receipt(ds, BUCKETS[0], "b", target=STREAM, seq=RdfLiteral(1))  # the same position as an xsd:integer
    assert rows("gap-scan-audit", ds) == ([(STREAM, "1", "1", "2")] if engines.CURRENT == "rdflib" else [])


@engines.each_engine
def test_h2_5_t44_a_chain_of_additions_and_subtractions_is_grouped_from_the_left_on_rdflib_and_from_the_right_on_oxigraph():
    """TSD-17. The gap scan's `?S - ?L + 1` would count wrongly on Oxigraph, so the renderer writes the parentheses."""
    ds = engines.dataset()
    flat = [int(_scalar(ds, f"SELECT ({e} AS ?x) WHERE {{}}")[0]) for e in ("10 - 3 + 2", "10 - 3 - 2", "8 / 4 / 2")]
    assert flat == ([9, 5, 1] if engines.CURRENT == "rdflib" else [5, 9, 4])
    assert [int(_scalar(ds, f"SELECT ({e} AS ?x) WHERE {{}}")[0]) for e in ("(10 - 3) + 2", "(10 - 3) - 2")] == [9, 5]
    assert "(?S - ?L) + 1" in sparql("gap-scan-audit")


def test_h2_5_t45_group_concat_keeps_the_stores_scan_order_whatever_the_hash_seed_on_rdflib():
    """TSD-Q7 for the query shape of the duplicate audit. The order is the order the owners were stored in, which is no
    guarantee, so the audit tests compare a set."""
    import os
    import subprocess
    import sys

    script = (
        "import sys; sys.path.insert(0, %r)\n"
        "import test_key_claims_and_audits as t\n"
        "from rdflib import URIRef as U\n"
        "ds = t.with_claims(*[(t.C1, U('urn:o:%%d' %% n)) for n in (5, 3, 6, 1, 4, 2)])\n"
        "print([str(r[2]) for r in ds.query(t.sparql('key-claim-duplicate-audit', True))][0])\n"
    ) % os.path.dirname(os.path.abspath(__file__))
    seen = set()
    for seed in range(6):
        env = {**os.environ, "PYTHONHASHSEED": str(seed)}
        seen.add(subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True, check=True).stdout.strip())
    assert seen == {"urn:o:5 urn:o:3 urn:o:6 urn:o:1 urn:o:4 urn:o:2"}


def test_h2_5_t46_now_never_binds_the_name_of_a_declared_parameter():
    import dataclasses

    from persistence.ir import Bind, Func, Group, IrError, Var
    from persistence.ir_render import check

    retire = build("key-claim-retire", CONTEXT)
    clash = dataclasses.replace(retire, where=Group((*retire.where.elements, Bind(Func("NOW"), Var("now")))))
    with pytest.raises(IrError) as caught:
        check(clash)
    assert caught.value.rule == "NameCollision"


# ---- the harness catches a changed query -----------------------------------------------------------------------------------


@pytest.mark.parametrize("stem, old, new", [
    ("key-claim-duplicate-audit", "HAVING (COUNT(?owner) > 1)", "HAVING (COUNT(?owner) >= 1)"),
    ("fork-detection-audit", "COUNT(DISTINCT ?t) AS ?n", "COUNT(?t) AS ?n"),
    ("gap-scan-audit", "FILTER(", "FILTER(!"),
    ("gap-scan-audit", "(?S - ?L) + 1", "?S - (?L + 1)"),
    ("key-claim-merge-rewrite", "MIN(STR(?owner))", "MAX(STR(?owner))"),
    ("key-claim-quarantine", "SELECT ?claim", "SELECT ?claim ?owner"),
    ("key-claim-merge-rewrite", "GROUP BY ?claim", "GROUP BY ?claim ?owner"),
])
def test_h2_5_t47_the_harness_fails_when_a_query_or_a_sub_select_is_changed(stem, old, new):
    import equivalence as eq
    from test_builders import _first

    _, _, _, context = _first(stem)
    template = eq.load_template(stem + ".mustache")
    mustache = eq.fill_request_slots(eq.mustache_render(template, context))
    built = eq.fill_request_slots(render(build(stem, context, guards=False)))
    assert old in built, (old, built)
    eq.compare(mustache, built, "unchanged")
    with pytest.raises(eq.Mismatch):
        eq.compare(mustache, built.replace(old, new, 1), "changed")
