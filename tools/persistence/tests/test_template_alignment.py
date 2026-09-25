# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Template alignment with the remediated patterns guide
(iri-patterns-post-3866b21-remediation, 2026-09-23): lazy epoch rebase
under dal:DatasetLevelGuard, request digests on txn claims, optional heads,
typed version rows, key claims in the keys graph, txn-cardinality and
receipt-side audits, and a row-driven gap scan. Each assertion names the
guide section it checks."""

from __future__ import annotations

from pathlib import Path

import pytest
from rdflib import Graph, URIRef
from rdflib.plugins.sparql import prepareQuery, prepareUpdate

from persistence.compiler import compile_to_graph
from persistence.instantiate import instantiate_profile
from persistence.render import REQUEST_TIME_SLOTS, load_template, render
from persistence.terms import Iri, Literal

REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_TTL = REPO_ROOT / "ontology" / "persistence" / "spec" / "persistence.ttl"
EXAMPLES_DIR = REPO_ROOT / "ontology" / "persistence" / "examples"
TEMPLATE_DIR = REPO_ROOT / "tools" / "persistence" / "src" / "persistence" / "templates"

from request_slots import fill_request_slots

ALL_TEMPLATES = sorted(p.name for p in TEMPLATE_DIR.glob("*.mustache"))
DATASET_GUARD_ROW_WRITERS = [
    "cas-replace-named-graph-dataset-guard.mustache",
    "cas-replace-composite-property-dataset-guard.mustache",
    "tombstone-delete-named-graph-dataset-guard.mustache",
    "append-event-dataset-guard.mustache",
]
CAS_AND_TOMBSTONE = [
    "cas-replace-named-graph.mustache",
    "cas-replace-named-graph-dataset-guard.mustache",
    "cas-replace-composite-property.mustache",
    "cas-replace-composite-property-dataset-guard.mustache",
    "tombstone-delete-named-graph.mustache",
    "tombstone-delete-named-graph-dataset-guard.mustache",
]


def _full_context() -> dict:
    return {
        "shard": 17,
        "logGraphPrefix": Iri.encode("urn:g:txlog/"),
        "txnGraph": Iri.encode("urn:g:txn"),
        "keysGraph": Iri.encode("urn:g:keys"),
        "keyQuarantineGraph": Iri.encode("urn:g:key-quarantine"),
        "retentionGraph": Iri.encode("urn:g:retention"),
        "pinnedGraph": Iri.encode("urn:g:txlog/pinned"),
        "eventGraphPrefix": Iri.encode("urn:g:events/order/"),
        "metaGraphPrefix": Iri.encode("urn:g:meta/17"),
        "datasetGraph": Iri.encode("urn:g:dataset"),
        "datasetNode": Iri.encode("urn:g:dataset"),
        "graphPrefix": Literal.encode("urn:g:orders/"),
        "guardProperty": Iri.encode("https://example.org/lending#status"),
        "compositeProperty": Iri.encode("https://example.org/lending#lineItem"),
        "constraintId": Literal.encode("example-constraint"),
        # persistence-compiler-iri-sync Slice 5.
        "mergeRelation": Iri.encode("https://example.org/lending#supersededBy"),
    }


def _parse(text: str) -> None:
    text = fill_request_slots(text)
    if any(k in text for k in ["INSERT", "DELETE"]):
        prepareUpdate(text)
    else:
        prepareQuery(text)


def _raw(name: str) -> str:
    return load_template(name)


@pytest.mark.parametrize("template", ALL_TEMPLATES)
def test_every_template_parses_with_a_complete_context(template):
    """Stricter than the injection corpus, which accepts a parse failure as
    a safe outcome: with every slot bound, every template must parse."""
    _parse(render(_raw(template), _full_context()))


@pytest.mark.parametrize("template", ALL_TEMPLATES)
def test_request_time_slots_are_the_only_mustache_left_after_instantiate(template):
    """Slice 2: the instantiated SPARQL carries standard Mustache tags for
    request-time values and nothing else a second Mustache pass could
    misread."""
    text = render(_raw(template), _full_context())
    stripped = text
    for slot in REQUEST_TIME_SLOTS:
        stripped = stripped.replace("{{{" + slot + "}}}", "")
    assert "{{" not in stripped and "}}" not in stripped


@pytest.mark.parametrize(
    "template", [t for t in ALL_TEMPLATES if any("{{{" + s + "}}}" in _raw(t) for s in REQUEST_TIME_SLOTS)]
)
def test_unrendered_request_time_slot_fails_closed(template):
    """A caller that forgets to render a request-time slot gets a parse
    error, never a silently empty payload or an empty VALUES block."""
    text = render(_raw(template), _full_context())
    with pytest.raises(Exception):
        if any(k in text for k in ["INSERT", "DELETE"]):
            prepareUpdate(text)
        else:
            prepareQuery(text)


def test_request_time_slot_cannot_be_bound_at_compile_time():
    ctx = _full_context()
    ctx["payloadTriples"] = Literal.encode("x")
    with pytest.raises(ValueError):
        render(_raw("unconditional-write.mustache"), ctx)


@pytest.mark.parametrize("template", DATASET_GUARD_ROW_WRITERS)
def test_dataset_guard_rebases_row_epoch_instead_of_guarding_it(template):
    """Guide §10.1, §19.1 (review A1): guarding on dataset epoch and row
    epoch together wedges every row after a bump."""
    text = _raw(template)
    assert "{{{datasetGraph}}} { {{{datasetNode}}} pat:epoch $epoch }" in text
    assert "pat:epoch ?rowEpoch" in text
    assert "pat:epoch $epoch ; pat:seq $expectedSeq" not in text
    assert "{ $stream pat:epoch $epoch ; pat:seq ?n }" not in text


@pytest.mark.parametrize("template", CAS_AND_TOMBSTONE)
def test_head_is_read_optionally(template):
    """Guide §14.2, §24.1 (review B2): a pre-created row has no head."""
    assert "OPTIONAL { $root pat:head ?prevRev }" in _raw(template)


@pytest.mark.parametrize(
    "template",
    [t for t in ALL_TEMPLATES if "INSERT" in _raw(t) and ("pat:rev $newRev" in _raw(t) or "pat:rev ?rev" in _raw(t))],
)
def test_every_txn_claim_records_the_request_digest(template):
    """Guide §15.2 (review A5)."""
    assert "pat:requestDigest $requestDigest" in _raw(template)


@pytest.mark.parametrize("template", [t for t in ALL_TEMPLATES if "pat:txn" in _raw(t)])
def test_receipt_txn_is_a_string(template):
    """Appendix B pins pat:txn to xsd:string; the claim subject is an IRI."""
    text = _raw(template)
    assert "pat:txn $txnId" not in text


@pytest.mark.parametrize(
    "template",
    [
        "create-if-absent-named-graph.mustache",
        "create-if-absent-named-graph-dataset-guard.mustache",
        "bootstrap-version-row.mustache",
        "bootstrap-version-row-dataset-guard.mustache",
    ],
)
def test_row_creation_types_the_version_row(template):
    """Guide Appendix B (review A6): shapes target pat:VersionRow."""
    assert "a pat:VersionRow" in _raw(template)


@pytest.mark.parametrize(
    "template",
    [
        "create-if-absent-named-graph-dataset-guard.mustache",
        "bootstrap-version-row-dataset-guard.mustache",
    ],
)
def test_dataset_guard_row_creation_checks_the_epoch(template):
    """Guide §14.2, §19.3 (review B3)."""
    assert "{{{datasetGraph}}} { {{{datasetNode}}} pat:epoch $epoch }" in _raw(template)


@pytest.mark.parametrize(
    "template",
    [
        "key-claim-write.mustache",
        "key-claim-write-dual.mustache",
        "key-claim-retire.mustache",
        "key-claim-duplicate-audit.mustache",
        "key-claim-merge-rewrite.mustache",
        "key-claim-quarantine.mustache",
    ],
)
def test_key_claims_live_in_the_keys_graph(template):
    text = _raw(template)
    assert "{{{keysGraph}}}" in text
    assert "{{{txnGraph}}}" not in text


def test_fork_audit_counts_txn_claims_not_shared_predecessors():
    """Guide F5 (review A6): deterministic revision IRIs make a
    shared-prevRev grouping unable to fire."""
    text = _raw("fork-detection-audit.mustache")
    assert "prevRev" not in text.split("}}", 1)[1]
    assert "COUNT(DISTINCT ?t)" in text


@pytest.mark.parametrize("template", ALL_TEMPLATES)
def test_no_template_scans_graphs_by_prefix(template):
    """Guide S3, F6: enumerate registry-listed graphs, never STRSTARTS."""
    assert "STRSTARTS" not in _raw(template)


def test_gap_scan_is_row_driven_with_low_water_mark():
    """Guide S3 (review B7)."""
    text = _raw("gap-scan-audit.mustache")
    assert "?target a pat:VersionRow ; pat:seq ?S" in text
    assert "pat:retentionLowWaterMark" in text
    assert 'COALESCE(?lwm, "1"^^xsd:long)' in text
    assert "HAVING (COUNT(DISTINCT ?seq) != ?S - ?L + 1)" in text
    assert "$epoch" not in text


def test_append_uses_portable_typing_and_padded_revision_iri():
    """Guide §10.1 (review B14): STRDT, not ?n + 1; 19-digit padding."""
    for name in ["append-event.mustache", "append-event-dataset-guard.mustache"]:
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
    assert by_op["append"] == "append-event-dataset-guard.mustache"
    assert by_op["bootstrap-version-row"] == "bootstrap-version-row-dataset-guard.mustache"
    rendered = instantiate_profile(out)
    assert "<urn:g:events/decisionstream/>" in rendered["append"]
    _parse(rendered["append"])


def test_named_graph_under_dataset_guard_selects_guarded_create():
    _, compiled = _compile("epoch-dataset-level-guard.ttl", "https://example.org/lending#LoanApplication")
    by_op = {o.operation: o.template_id for o in compiled[0].operations}
    assert by_op["create-if-absent"] == "create-if-absent-named-graph-dataset-guard.mustache"


def test_every_profile_gets_the_receipt_side_audits():
    """Guide §24.2 (review A4)."""
    _, compiled = _compile("baseline-single-class.ttl", "https://example.org/lending#LoanApplication")
    ops = {o.operation for o in compiled[0].operations}
    assert {"fork-detection-audit", "revision-multi-txn-audit", "txn-multi-revision-audit", "gap-scan-audit"} <= ops
