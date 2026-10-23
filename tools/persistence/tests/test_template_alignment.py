# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Builder alignment with the remediated patterns guide
(iri-patterns-post-3866b21-remediation, 2026-09-23): lazy epoch rebase
under dal:DatasetLevelGuard, request digests on txn claims, optional heads,
typed version rows, key claims in the keys graph, txn-cardinality and
receipt-side audits, and a row-driven gap scan. Each assertion names the
guide section it checks. Since H2.9 the text read is the rendered output of
each builder, where it was the Mustache template."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from rdflib import Graph, URIRef
from rdflib.plugins.sparql import prepareQuery, prepareUpdate

from persistence.builders import BUILDERS, build
from persistence.compiler import compile_to_graph
from persistence.instantiate import instantiate_profile
from persistence.ir_render import render


REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_TTL = REPO_ROOT / "ontology" / "persistence" / "spec" / "persistence.ttl"
EXAMPLES_DIR = REPO_ROOT / "ontology" / "persistence" / "examples"

from builder_goldens import CANONICAL_CONTEXT
from request_slots import fill_request_slots

ALL_BUILDERS = sorted(BUILDERS)
DATASET_GUARD_ROW_WRITERS = [
    "cas-replace-named-graph-dataset-guard",
    "cas-replace-composite-property-patch-log-dataset-guard",
    "tombstone-delete-named-graph-dataset-guard",
    "append-event-dataset-guard",
]
CAS_AND_TOMBSTONE = [
    "cas-replace-named-graph",
    "cas-replace-named-graph-dataset-guard",
    "cas-replace-composite-property-patch-log",
    "cas-replace-composite-property-patch-log-dataset-guard",
    "tombstone-delete-named-graph",
    "tombstone-delete-named-graph-dataset-guard",
]
_SLOT_MARKER = re.compile(r"\{\{\{[A-Za-z_]\w*\}\}\}")


def _full_context() -> dict:
    return dict(CANONICAL_CONTEXT)


def _parse(text: str) -> None:
    text = fill_request_slots(text)
    if any(k in text for k in ["INSERT", "DELETE"]):
        prepareUpdate(text)
    else:
        prepareQuery(text)


def _raw(name: str) -> str:
    """The rendered text of the builder ``name``, with its request-time slots still marked."""
    return render(build(name, _full_context()))


@pytest.mark.parametrize("builder", ALL_BUILDERS)
def test_every_builder_parses_with_a_complete_context(builder):
    """Stricter than the injection corpus, which accepts a parse failure as
    a safe outcome: with every slot filled, every builder's text must parse."""
    _parse(_raw(builder))


@pytest.mark.parametrize("builder", ALL_BUILDERS)
def test_request_time_slots_are_the_only_markers_left_after_instantiate(builder):
    """Slice 2: the instantiated SPARQL carries plain-text markers for
    request-time values and nothing else a substitution could misread."""
    stripped = _SLOT_MARKER.sub("", _raw(builder))
    assert "{{" not in stripped and "}}" not in stripped


@pytest.mark.parametrize("builder", [b for b in ALL_BUILDERS if _SLOT_MARKER.search(_raw(b))])
def test_unrendered_request_time_slot_fails_closed(builder):
    """A caller that forgets to fill a request-time slot gets a parse
    error, never a silently empty payload or an empty VALUES block."""
    text = _raw(builder)
    with pytest.raises(Exception):
        if any(k in text for k in ["INSERT", "DELETE"]):
            prepareUpdate(text)
        else:
            prepareQuery(text)


@pytest.mark.parametrize("builder", DATASET_GUARD_ROW_WRITERS)
def test_dataset_guard_rebases_row_epoch_instead_of_guarding_it(builder):
    """Guide §10.1, §19.1 (review A1): guarding on dataset epoch and row
    epoch together wedges every row after a bump."""
    text = _raw(builder)
    assert "GRAPH <urn:g:dataset> { <urn:g:dataset> pat:epoch $epoch }" in text
    assert "pat:epoch ?rowEpoch" in text
    assert "pat:epoch $epoch ; pat:seq $expectedSeq" not in text
    assert "{ $stream pat:epoch $epoch ; pat:seq ?n }" not in text


@pytest.mark.parametrize("builder", CAS_AND_TOMBSTONE)
def test_head_is_read_optionally(builder):
    """Guide §14.2, §24.1 (review B2): a pre-created row has no head."""
    assert "OPTIONAL { $root pat:head ?prevRev }" in _raw(builder)


@pytest.mark.parametrize(
    "builder",
    [t for t in ALL_BUILDERS if "INSERT" in _raw(t) and ("pat:rev $newRev" in _raw(t) or "pat:rev ?rev" in _raw(t))],
)
def test_every_txn_claim_records_the_request_digest(builder):
    """Guide §15.2 (review A5)."""
    assert "pat:requestDigest $requestDigest" in _raw(builder)


@pytest.mark.parametrize("builder", [t for t in ALL_BUILDERS if "pat:txn" in _raw(t)])
def test_receipt_txn_is_a_string(builder):
    """Appendix B pins pat:txn to xsd:string; the claim subject is an IRI."""
    assert "pat:txn $txnId" not in _raw(builder)


@pytest.mark.parametrize(
    "builder",
    [
        "create-if-absent-named-graph",
        "create-if-absent-named-graph-dataset-guard",
        "bootstrap-version-row",
        "bootstrap-version-row-dataset-guard",
    ],
)
def test_row_creation_types_the_version_row(builder):
    """Guide Appendix B (review A6): shapes target pat:VersionRow."""
    assert "a pat:VersionRow" in _raw(builder)


@pytest.mark.parametrize(
    "builder",
    [
        "create-if-absent-named-graph-dataset-guard",
        "bootstrap-version-row-dataset-guard",
    ],
)
def test_dataset_guard_row_creation_checks_the_epoch(builder):
    """Guide §14.2, §19.3 (review B3)."""
    assert "GRAPH <urn:g:dataset> { <urn:g:dataset> pat:epoch $epoch }" in _raw(builder)


@pytest.mark.parametrize(
    "builder",
    [
        "key-claim-write",
        "key-claim-write-dual",
        "key-claim-retire",
        "key-claim-duplicate-audit",
        "key-claim-merge-rewrite",
        "key-claim-quarantine",
    ],
)
def test_key_claims_live_in_the_keys_graph(builder):
    text = _raw(builder)
    assert "<urn:g:keys>" in text
    assert "<urn:g:txn>" not in text


def test_fork_audit_counts_txn_claims_not_shared_predecessors():
    """Guide F5 (review A6): deterministic revision IRIs make a
    shared-prevRev grouping unable to fire."""
    text = _raw("fork-detection-audit")
    assert "prevRev" not in text
    assert "COUNT(DISTINCT ?t)" in text


@pytest.mark.parametrize("builder", ALL_BUILDERS)
def test_no_builder_scans_graphs_by_prefix(builder):
    """Guide S3, F6: enumerate registry-listed graphs, never STRSTARTS."""
    assert "STRSTARTS" not in _raw(builder)


def test_gap_scan_is_row_driven_with_low_water_mark():
    """Guide S3 (review B7)."""
    text = _raw("gap-scan-audit")
    assert "?target a pat:VersionRow ; pat:seq ?S" in text
    assert "pat:retentionLowWaterMark" in text
    assert 'COALESCE(?lwm, "1"^^xsd:long)' in text
    assert "HAVING (COUNT(DISTINCT ?seq) != ((?S - ?L) + 1))" in text
    assert "$epoch" not in text


def test_append_uses_portable_typing_and_padded_revision_iri():
    """Guide §10.1 (review B14): STRDT, not ?n + 1; 19-digit padding."""
    for name in ["append-event", "append-event-dataset-guard"]:
        text = _raw(name)
        assert "STRDT(STR(?n + 1), xsd:long)" in text
        assert '"0000000000000000000"' in text
        assert "pat:prevRev ?prev" in text


def _compile(fixture: str, cls: str):
    g = Graph()
    g.parse(SPEC_TTL, format="turtle")
    g.parse(EXAMPLES_DIR / fixture, format="turtle")
    return compile_to_graph(g, classes={URIRef(cls)})


def test_append_stream_under_dataset_guard_selects_guarded_variants():
    out, compiled = _compile("append-stream-dataset-guard.ttl", "https://example.org/lending#DecisionStream")
    by_op = {o.operation: o.template_id for o in compiled[0].operations}
    assert by_op["append"] == "append-event-dataset-guard"
    assert by_op["bootstrap-version-row"] == "bootstrap-version-row-dataset-guard"
    rendered = instantiate_profile(out)
    assert "<urn:g:events/decisionstream/>" in rendered["append"]
    _parse(rendered["append"])


def test_named_graph_under_dataset_guard_selects_guarded_create():
    _, compiled = _compile("epoch-dataset-level-guard.ttl", "https://example.org/lending#LoanApplication")
    by_op = {o.operation: o.template_id for o in compiled[0].operations}
    assert by_op["create-if-absent"] == "create-if-absent-named-graph-patch-log-dataset-guard"  # dal:PatchLog (H2.6d)


def test_every_profile_gets_the_receipt_side_audits():
    """Guide §24.2 (review A4)."""
    _, compiled = _compile("baseline-single-class.ttl", "https://example.org/lending#LoanApplication")
    ops = {o.operation for o in compiled[0].operations}
    assert {"fork-detection-audit", "revision-multi-txn-audit", "txn-multi-revision-audit", "gap-scan-audit"} <= ops
