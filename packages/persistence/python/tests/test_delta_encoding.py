# SPDX-License-Identifier: MPL-2.0
# NB: This file has been produced using GenAI
"""DR2: the delta replace (dal:ChangedTriples) in the caller library. Its request carries the triples retracted and asserted and no whole state,
so its digest has no payload part and the caller check refuses an overlap and an empty delta, and checks the aggregate only against the next
state the caller passes (obligation 8 of tools/persistence/README.md). Validation Pack: docs/developer/validation/persistence-delta-replace.md. Test IDs are DR2-Ln."""
from __future__ import annotations

from dataclasses import replace as dc_replace

import pytest

from lattice_persistence import Iri, Lit, OperationKind, Payload, Triple, read_contracts, refusals, request_digest, check_request
from lattice_persistence.check import CallerCheckError

EX = "https://example.org/projects#"
A, NAME, AGE = Iri.encode("urn:example:person/1"), Iri.encode("urn:example:name"), Iri.encode("urn:example:age")


def iri(x: str) -> Iri:
    return Iri.encode(x if ":" in x else EX + x)


def t(s, p, o) -> Triple:
    return Triple(iri(s), iri(p), o if isinstance(o, (Iri, Lit)) else iri(o))


def delta_op(profiles, example: str, template: str):
    return next(o for o in read_contracts(profiles[example]) if o.template_id == template)


@pytest.fixture(scope="module")
def named(profiles):
    return delta_op(profiles, "replace-encoding", "cas-replace-named-graph-delta-patch-log")


@pytest.fixture(scope="module")
def composite(profiles):
    return delta_op(profiles, "composite-project-ownership", "cas-replace-composite-property-delta-patch-log")


def request(add=(), delete=(), **over):
    base = {
        "root": iri("urn:p1"), "epoch": 1, "expectedSeq": 3, "nextSeq": 4, "newRev": iri("urn:rev:4"), "txnId": iri("urn:txn:1"),
        "requestDigest": "0" * 64, "assertTriples": Payload.of(*add), "retractTriples": Payload.of(*delete),
    }
    base.update(over)
    return base


def codes(op, values, **options) -> list:
    return [r.code for r in refusals(op, values, **options)]


def test_dr2_l1_the_contract_is_a_delta_replace_whose_digest_has_the_change_and_no_payload_part(named):
    assert named.kind is OperationKind.DELTA_REPLACE and named.payload.parameter == "assertTriples" and named.payload.encoding == "GroundNTriples"
    assert [(p.role, p.sources) for p in named.digest.parts] == [
        ("OperationKindPart", ()), ("TargetPart", ("root",)), ("ExpectedSeqPart", ("expectedSeq",)), ("AddPart", ("assertTriples",)),
        ("DelPart", ("retractTriples",)),
    ]
    assert "payloadTriples" not in {p.name for p in named.parameters}


def test_dr2_l2_the_request_digest_of_a_delta_is_the_openssl_vector(named, vectors):
    v = next(v for v in vectors["digests"] if v["id"] == "digest-delta-replace")
    def payload(part: str) -> Payload:
        triples = next(p for p in v["parts"] if p["role"] == part)["triples"]
        return Payload.of(*(Triple(Iri.encode(x["s"]["iri"]), Iri.encode(x["p"]["iri"]), Lit(x["o"]["literal"], x["o"].get("datatype"))) for x in triples))
    add, delete = payload("AddPart"), payload("DelPart")
    values = {"root": v["target"], "expectedSeq": v["expected"], "assertTriples": add, "retractTriples": delete}
    assert request_digest(named, values) == v["sha256"]
    swapped = {**values, "assertTriples": delete, "retractTriples": add}
    assert request_digest(named, swapped) != v["sha256"], "a triple's role is part of what is hashed"


def test_dr2_l3_a_delta_with_a_change_passes_without_the_next_state_and_the_bound_is_not_run_over_the_asserted_triples(named, composite):
    ok = request(add=[t("urn:p1", "name", Lit("B"))], delete=[t("urn:p1", "name", Lit("A"))])
    assert refusals(named, ok) == ()
    # a member reached through an edge that is already stored is outside the asserted triples alone, so nothing refuses it here
    assert refusals(composite, request(add=[t("urn:t9", "assignee", "urn:alice")])) == ()


def test_dr2_l4_an_overlap_is_refused_and_named(named):
    both = t("urn:p1", "name", Lit("A"))
    found = refusals(named, request(add=[both, t("urn:p1", "name", Lit("B"))], delete=[both]))
    assert [(r.code, r.where) for r in found] == [("DeltaOverlap", "assertTriples")]
    with pytest.raises(CallerCheckError, match="DeltaOverlap"):
        check_request(named, request(add=[both], delete=[both]))


def test_dr2_l5_a_delta_that_asserts_and_retracts_nothing_is_refused_and_one_that_does_either_is_not(named):
    assert codes(named, request()) == ["EmptyDelta"]
    assert codes(named, request(add=[t("urn:p1", "name", Lit("A"))])) == []
    assert codes(named, request(delete=[t("urn:p1", "name", Lit("A"))])) == []


def test_dr2_l6_the_next_state_holds_every_asserted_triple_and_no_retracted_one(named):
    old, new = t("urn:p1", "name", Lit("A")), t("urn:p1", "name", Lit("B"))
    state = Payload.of(new, t("urn:p1", "note", Lit("k")))
    assert refusals(named, request(add=[new], delete=[old]), next_state=state) == ()
    assert codes(named, request(add=[new, t("urn:p1", "name", Lit("C"))], delete=[old]), next_state=state) == ["AssertOutsideNextState"]
    assert codes(named, request(add=[new], delete=[old]), next_state=Payload.of(new, old)) == ["RetractInNextState"]


def test_dr2_l7_the_next_state_is_held_to_the_boundary_and_a_whole_state_replace_ignores_the_option(composite, profiles):
    inside = Payload.of(t("urn:p1", "name", Lit("B")), t("urn:p1", "hasMilestone", "urn:m1"), t("urn:m1", "name", Lit("M")))
    add = [t("urn:p1", "name", Lit("B"))]
    assert refusals(composite, request(add=add), next_state=inside) == ()
    stray = Payload.of(*inside.triples, t("urn:other", "name", Lit("X")))
    found = refusals(composite, request(add=add), next_state=stray)
    assert [(r.code, r.where) for r in found] == [("PayloadOutsideBound", "nextState")]
    whole = delta_op(profiles, "composite-whole-state", "cas-replace-composite-property-patch-log")
    assert refusals(whole, {**request(), "payloadTriples": inside}, next_state=stray) == ()


def test_dr2_l8_the_reference_modes_of_the_next_state_are_checked_where_the_caller_can_say_what_is_a_version(composite):
    edges = tuple(dc_replace(e, reference_mode="Pinned") if e.predicate == EX + "forClient" else e for e in composite.payload.edges)
    pinned = dc_replace(composite, payload=dc_replace(composite.payload, edges=edges))
    versions = {EX + "org/v2": True, EX + "org": False}
    version_of = lambda x: versions.get(str(x)[1:-1])
    add = [t("urn:p1", "name", Lit("B"))]
    good = Payload.of(*add, t("urn:p1", "forClient", iri(EX + "org/v2")))
    bad = Payload.of(*add, t("urn:p1", "forClient", iri(EX + "org")))
    assert refusals(pinned, request(add=add), next_state=good, version_of=version_of) == ()
    assert codes(pinned, request(add=add), next_state=bad, version_of=version_of) == ["ReferenceModeViolation"]
    assert refusals(pinned, request(add=add), next_state=bad) == (), "without a classifier the mode is not checked"
