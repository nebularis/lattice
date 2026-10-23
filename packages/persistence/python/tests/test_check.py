# SPDX-License-Identifier: MPL-2.0
# NB: This file has been produced using GenAI
"""H2.8b: the payload bound, the caller check and the audit outcome, over compiled profiles read by the library alone."""
from __future__ import annotations

import pytest
from rdflib import Literal as RdfLiteral
from rdflib.namespace import XSD

from lattice_persistence import (
    AuditOutcome, EventRow, Iri, Lit, Membership, Payload, Rows, SparqlClient, Triple, audit_outcome, check_request, outside_bound,
    outside_events, read_contracts, refusals, run_audit,
)
from lattice_persistence.audit import examined_query, registry_text
from lattice_persistence.check import graph_name

EX = "https://example.org/projects#"
XSD_LONG = str(XSD.long)


def iri(x: str) -> Iri:
    return Iri.encode(x if ":" in x else EX + x)


def t(s, p, o) -> Triple:
    return Triple(iri(s), iri(p), o if isinstance(o, (Iri, Lit)) else iri(o))


def op(profiles, example: str, template: str):
    return next(o for o in read_contracts(profiles[example]) if o.template_id == template)


@pytest.fixture(scope="module")
def replace(profiles):
    return op(profiles, "composite-project-ownership", "cas-replace-composite-property-patch-log")


def request(**over):
    base = {
        "root": iri("urn:p1"), "epoch": 1, "expectedSeq": 3, "nextSeq": 4, "newRev": iri("urn:rev:4"), "txnId": iri("urn:txn:1"),
        "requestDigest": "0" * 64, "assertTriples": Payload.of(), "retractTriples": Payload.of(), "payloadTriples": Payload.of(t("urn:p1", "name", Lit("A")), t("urn:p1", "hasMilestone", "urn:m1"), t("urn:m1", "due", Lit("2026-01-01", "http://www.w3.org/2001/XMLSchema#date"))),
    }
    base.update(over)
    return base


# ---- the payload bound

def test_a_payload_within_the_aggregate_passes(replace):
    assert refusals(replace, request()) == ()


def test_a_subject_outside_the_aggregate_is_refused_and_named(replace):
    stray = Payload.of(t("urn:p1", "name", Lit("A")), t("urn:other", "name", Lit("B")))
    found = refusals(replace, request(payloadTriples=stray))
    assert [r.code for r in found] == ["PayloadOutsideBound"] and "urn:other" in found[0].reason
    assert outside_bound(replace.payload, iri("urn:p1"), stray) == (iri("urn:other"),)


def test_a_node_reached_only_through_a_reference_edge_is_outside(replace):
    # ex:forClient is a Reference edge, so the organisation it names is not the aggregate's to describe
    p = Payload.of(t("urn:p1", "forClient", "urn:org"), t("urn:org", "name", Lit("Org")))
    assert outside_bound(replace.payload, iri("urn:p1"), p) == (iri("urn:org"),)


def test_the_walk_follows_inverse_recursive_and_nested_edges(replace):
    p = Payload.of(
        t("urn:p1", "hasMilestone", "urn:m1"), t("urn:m1", "hasTask", "urn:t1"), t("urn:t1", "hasSubtask", "urn:t2"),
        t("urn:t2", "hasSubtask", "urn:t3"), t("urn:t3", "attachment", "urn:d1"), t("urn:d1", "title", Lit("x")),
        t("urn:c1", "onTask", "urn:t3"), t("urn:c1", "text", Lit("hello")),
    )
    assert outside_bound(replace.payload, iri("urn:p1"), p) == ()
    # the same comment hangs off a task nothing reaches
    q = Payload.of(t("urn:p1", "hasMilestone", "urn:m1"), t("urn:c1", "onTask", "urn:t9"), t("urn:c1", "text", Lit("hello")))
    assert set(outside_bound(replace.payload, iri("urn:p1"), q)) == {iri("urn:c1")}


def test_a_cycle_terminates(replace):
    p = Payload.of(t("urn:p1", "hasMilestone", "urn:m1"), t("urn:m1", "hasTask", "urn:t1"), t("urn:t1", "hasSubtask", "urn:t1"))
    assert outside_bound(replace.payload, iri("urn:p1"), p) == ()


def test_a_family_with_no_shape_bounds_nothing(profiles):
    create = op(profiles, "baseline-single-class", "create-if-absent-named-graph-patch-log")
    assert create.payload.shape is None
    assert outside_bound(create.payload, iri("urn:a"), Payload.of(t("urn:z", "name", Lit("x")))) == ()


# ---- the parameters

def test_a_missing_and_an_unknown_parameter_are_named(replace):
    values = request()
    del values["epoch"]
    values["epock"] = 1
    assert {(r.code, r.where) for r in refusals(replace, values)} == {("MissingParameter", "epoch"), ("UnknownParameter", "epock")}


@pytest.mark.parametrize("epoch", [Lit("1", "http://www.w3.org/2001/XMLSchema#integer"), RdfLiteral(1, datatype=XSD.integer), RdfLiteral("1")])
def test_an_epoch_that_is_not_exactly_xsd_long_is_refused(replace, epoch):
    assert [r.code for r in refusals(replace, request(epoch=epoch))] == ["NotXsdLong"]


@pytest.mark.parametrize("epoch", [1, Lit("1", XSD_LONG), RdfLiteral(1, datatype=XSD.long)])
def test_an_xsd_long_in_any_form_passes(replace, epoch):
    assert refusals(replace, request(epoch=epoch)) == ()


@pytest.mark.parametrize("epoch,code", [
    (Lit("abc", XSD_LONG), "IllTypedLiteral"), (2**63, "IllTypedLiteral"), (True, "WrongKind"), (iri("urn:x"), "WrongKind"), ("1", "WrongKind"),
], ids=["ill-typed", "out-of-range", "bool", "iri", "string"])
def test_an_ill_typed_or_misplaced_long_is_refused(replace, epoch, code):
    assert [r.code for r in refusals(replace, request(epoch=epoch))] == [code]


def test_a_literal_is_not_an_iri_and_an_iri_is_not_a_literal(replace):
    assert [r.code for r in refusals(replace, request(root=Lit("urn:p1")))][0] == "WrongKind"
    assert any(r.code == "WrongKind" and r.where == "root" for r in refusals(replace, request(root=42)))


def test_a_digest_is_sixty_four_lower_case_hex_characters(replace):
    assert [r.code for r in refusals(replace, request(requestDigest="ABC"))] == ["WrongKind"]


def test_a_bare_string_is_not_a_payload(replace):
    assert [r.code for r in refusals(replace, request(payloadTriples="<urn:a> <urn:b> <urn:c> ."))] == ["WrongKind"]


def test_the_check_raises_with_every_reason(replace):
    with pytest.raises(Exception) as caught:
        check_request(replace, request(epoch=RdfLiteral(1, datatype=XSD.integer), payloadTriples=Payload.of(t("urn:z", "name", Lit("x")))))
    assert {r.code for r in caught.value.refusals} == {"NotXsdLong", "PayloadOutsideBound"} and "refused before sending" in str(caught.value)


# ---- a caller-named graph

@pytest.fixture(scope="module")
def caller_named(profiles):
    return op(profiles, "baseline-single-class", "cas-replace-named-graph-patch-log")


def test_the_naming_rule_is_read_from_the_bindings_of_the_profile(caller_named):
    assert caller_named.parameter("g") is None and graph_name(caller_named, iri("urn:a")) == "urn:g:loan-application/urn%3Aa"


def test_a_caller_named_graph_must_equal_the_rule(profiles):
    from dataclasses import replace as dc_replace

    from lattice_persistence.contract import ParameterContract

    base = op(profiles, "baseline-single-class", "cas-replace-named-graph-patch-log")
    named = dc_replace(
        base, parameters=(*base.parameters, ParameterContract("g", "Iri", True, equals_graph_name=True)),
        bindings=tuple(b for b in base.bindings if b[0] not in ("graphPrefix", "graphSuffix")) + (("graphPrefix", '"urn:g:loan/"'), ("graphSuffix", '""')),
    )
    values = {p.name: None for p in named.parameters}
    root = iri("urn:a/b?c")
    assert graph_name(named, root) == "urn:g:loan/urn%3Aa%2Fb%3Fc"
    good = [r for r in refusals(named, {"root": root, "g": iri("urn:g:loan/urn%3Aa%2Fb%3Fc")}) if r.code == "GraphNameMismatch"]
    bad = [r for r in refusals(named, {"root": root, "g": iri("urn:g:loan/urn:a/b?c")}) if r.code == "GraphNameMismatch"]
    assert good == [] and len(bad) == 1


# ---- the log graphs and the audit outcome

@pytest.fixture(scope="module")
def gap(profiles):
    return op(profiles, "baseline-single-class", "gap-scan-audit")


def test_an_empty_log_graphs_is_refused_unless_the_caller_allows_it(gap):
    assert [r.code for r in refusals(gap, {"logGraphs": []})] == ["EmptyLogGraphs"]
    assert refusals(gap, {"logGraphs": []}, allow_empty_log_graphs=True) == ()
    assert refusals(gap, {"logGraphs": [iri("urn:g:txlog/2026-10")]}) == ()
    assert [r.code for r in refusals(gap, {"logGraphs": ["not an iri"]})] == ["LogGraphNotIri"]
    assert [r.code for r in refusals(gap, {})] == ["MissingParameter"]


def test_the_outcome_has_three_values():
    assert audit_outcome([("row",)]) is AuditOutcome.FAILED
    assert audit_outcome([], log_graphs=[iri("urn:g:a")], examined=7) is AuditOutcome.CLEAN
    assert audit_outcome([], log_graphs=[]) is AuditOutcome.NOTHING_EXAMINED
    assert audit_outcome([], log_graphs=[iri("urn:g:a")], examined=0) is AuditOutcome.NOTHING_EXAMINED
    assert audit_outcome([]) is AuditOutcome.CLEAN  # an audit that lists no graph reads fixed ones
    assert audit_outcome([("row",)], log_graphs=[]) is AuditOutcome.FAILED


def test_the_profile_declares_what_an_audit_examines(profiles):
    ops = {o.template_id: o for o in read_contracts(profiles["baseline-single-class"])}
    assert ops["gap-scan-audit"].examines == "logGraphs" and ops["fork-detection-audit"].examines is None
    assert all(o.outcomes == ("Clean", "Failed", "NothingExamined") for o in ops.values() if o.template_id.endswith("-audit"))
    assert ops["create-if-absent-named-graph-patch-log"].outcomes == ()


class FakeClient:
    def __init__(self, rows, counted):
        self.rows, self.counted, self.seen = rows, counted, []

    def select(self, query):
        self.seen.append(query)
        return self.counted if query.startswith("SELECT (COUNT(?r)") else self.rows


def test_run_audit_reports_nothing_examined_for_an_empty_registry_and_for_buckets_with_no_receipt(gap):
    query = "SELECT * WHERE { VALUES ?log { <urn:g:txlog/pinned> {{{logGraphs}}} } }"
    empty = run_audit(FakeClient([], []), gap, query, [])
    assert empty.outcome is AuditOutcome.NOTHING_EXAMINED
    assert run_audit(FakeClient([], [{"n": "0"}]), gap, query, [iri("urn:g:txlog/2026-10")]).outcome is AuditOutcome.NOTHING_EXAMINED
    client = FakeClient([], [{"n": "12"}])
    assert run_audit(client, gap, query, [iri("urn:g:txlog/2026-10")]).outcome is AuditOutcome.CLEAN
    assert "<urn:g:txlog/2026-10>" in client.seen[0] and "{{{" not in client.seen[0]
    assert run_audit(FakeClient([{"target": "x"}], []), gap, query, [iri("urn:g:txlog/2026-10")]).outcome is AuditOutcome.FAILED
    with pytest.raises(ValueError):
        run_audit(FakeClient([], []), gap, query)


def test_the_examined_query_counts_the_pinned_graph_and_the_listed_ones(gap):
    text = examined_query(gap, [iri("urn:g:a")])
    assert "<urn:g:txlog/pinned> <urn:g:a>" in text and registry_text([iri("urn:g:a")]) == "<urn:g:a>"


# ---- events

@pytest.fixture(scope="module")
def append(profiles):
    return op(profiles, "append-stream-dataset-guard", "append-event-dataset-guard")


def row(n, event=None, seq=None):
    return EventRow(iri(event or f"urn:ev:{n}"), iri("urn:type:Opened"), seq if seq is not None else n, Lit("2026-10-20T00:00:00Z", "http://www.w3.org/2001/XMLSchema#dateTime"))


def events(**over):
    base = {"stream": iri("urn:s"), "epoch": 1, "revBase": "urn:rev:", "txnId": iri("urn:txn:1"), "requestDigest": "0" * 64,
            "eventRows": Rows((row(1), row(2))), "eventTriples": Payload.of(t("urn:ev:1", "about", "urn:agg"), t("urn:ev:2/part/a", "note", Lit("x")))}
    base.update(over)
    return base


def test_an_event_may_name_an_aggregate_and_never_describe_one(append):
    assert refusals(append, events()) == ()
    bad = events(eventTriples=Payload.of(t("urn:agg", "name", Lit("changed"))))
    found = refusals(append, bad)
    assert [r.code for r in found] == ["EventOutsideBound"] and "urn:agg" in found[0].reason
    assert [r.code for r in refusals(append, events(eventTriples=Payload.of(t("urn:ev:10", "x", Lit("y")))))] == ["EventOutsideBound"]  # a prefix of the name is not a part
    assert outside_events([iri("urn:ev:1")], Payload.of(t("urn:ev:1/part/a/b", "p", Lit("v")))) == ()


def test_the_rows_of_a_batch(append):
    assert [r.code for r in refusals(append, events(eventRows=Rows(()), eventTriples=Payload.of()))] == ["NoEvents"]
    assert [r.code for r in refusals(append, events(eventRows=Rows((row(1), row(2, event="urn:ev:1"))), eventTriples=Payload.of()))] == ["DuplicateEvent"]
    assert [r.code for r in refusals(append, events(eventRows=Rows((row(1), row(2, seq=1))), eventTriples=Payload.of()))] == ["DuplicateOpSeq"]


# ---- reference modes (TD-67)

@pytest.fixture(scope="module")
def pinned(replace):
    from dataclasses import replace as dc_replace

    edges = tuple(dc_replace(e, reference_mode="Pinned") if e.predicate == EX + "forClient" else e for e in replace.payload.edges)
    contract = dc_replace(replace.payload, edges=edges)
    return dc_replace(replace, payload=contract)


def test_an_object_on_a_pinned_edge_must_be_a_version_and_on_an_identity_edge_must_not(pinned):
    versions = {EX + "org/v2": True, EX + "org": False}
    version_of = lambda x: versions.get(str(x)[1:-1])
    pins = Payload.of(t("urn:p1", "forClient", iri(EX + "org/v2")))
    assert refusals(pinned, request(payloadTriples=pins), version_of=version_of) == ()
    by_identity = Payload.of(t("urn:p1", "forClient", iri(EX + "org")))
    assert [r.code for r in refusals(pinned, request(payloadTriples=by_identity), version_of=version_of)] == ["ReferenceModeViolation"]
    unknown = Payload.of(t("urn:p1", "forClient", iri("urn:never-seen")))
    assert [r.code for r in refusals(pinned, request(payloadTriples=unknown), version_of=version_of)] == ["ReferenceModeViolation"]
    # an identity edge to a version
    version_on_identity = Payload.of(t("urn:p1", "hasMilestone", "urn:m1"), t("urn:m1", "hasTask", "urn:t1"), t("urn:t1", "assignee", iri(EX + "org/v2")))
    assert [r.code for r in refusals(pinned, request(payloadTriples=version_on_identity), version_of=version_of)] == ["ReferenceModeViolation"]
    # without a classifier the mode is not checked
    assert refusals(pinned, request(payloadTriples=by_identity)) == ()


# ---- delta membership checkpoints

@pytest.fixture(scope="module")
def delta(profiles):
    return op(profiles, "write-discipline-delta-membership", "append-version-delta-dataset-guard")


def test_the_root_of_a_new_version_is_the_version(delta):
    assert delta.payload.root == "newVersion"


def test_a_checkpoint_lists_every_member_and_says_so(delta):
    from lattice_persistence.namespaces import PAT

    prop, version = "https://example.org/location#hasLocation", iri("urn:v:17")
    members = frozenset({iri("urn:loc:1"), iri("urn:loc:2")})
    full = Payload.of(*(Triple(version, iri(prop), m) for m in members), Triple(version, Iri.encode(str(PAT.checkpoint)), Lit("true", "http://www.w3.org/2001/XMLSchema#boolean")))
    partial = Payload.of(Triple(version, iri(prop), iri("urn:loc:1")), Triple(version, Iri.encode(str(PAT.checkpoint)), Lit("true", "http://www.w3.org/2001/XMLSchema#boolean")))
    unmarked = Payload.of(*(Triple(version, iri(prop), m) for m in members))
    plain_version = Payload.of(Triple(version, iri("urn:p"), Lit("x")))

    def found(payload, checkpoint):
        return [r.code for r in refusals(delta, {"newVersion": version, "payloadTriples": payload}, membership=Membership(iri(prop), members, checkpoint)) if r.code in ("CheckpointNotFull", "UnexpectedFullList")]

    assert found(full, True) == [] and found(partial, True) == ["CheckpointNotFull"] and found(unmarked, True) == ["CheckpointNotFull"]
    assert found(plain_version, False) == [] and found(full, False) == ["UnexpectedFullList"]
