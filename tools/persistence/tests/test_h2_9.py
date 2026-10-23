# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""H2.9: Mustache retired (formal-methods track H, plan 4.15). Every generated operation is rendered from its builder, the template id is the
builder's identity, the receipt-only writes of a composite family are gone and `dal:SnapshotPerRevision` is refused for one written in place
(D-12 (a), TD-46). Validation Pack: docs/developer/validation/FMH-H2-9.md. Test IDs are H2.9-Tn. T1 is in test_builder_versions.py, T5 in
test_terms.py and T6 in test_templatecheck.py."""

from __future__ import annotations

import pytest
from rdflib import Graph, Literal as RdfLiteral, URIRef

from builder_goldens import CANONICAL_CONTEXT
from conftest import EXAMPLES_DIR
from persistence import instantiate, witness
from persistence.builders import BUILDERS, build
from persistence.compiler import CompileError, compile_targets, compile_to_graph
from persistence.instantiate import instantiate_by_target
from persistence.ir_render import fill_slots, slot_marker
from persistence.namespaces import DAL

DAL_NS = "https://www.nebularis.org/neuro-semantic/lattice/persistence#"
SNAPSHOT_COMPOSITE = witness.WITNESS_DIR / "refusal-CompositeBoundarySnapshotNotBuilt.ttl"
ORDER_EXAMPLE = EXAMPLES_DIR / "composite-property-boundary-shacl.ttl"


def _refused(graph) -> str | None:
    try:
        compile_targets(graph)
    except CompileError as error:
        return getattr(error.cause, "kind", type(error.cause).__name__)
    return None


def _with_snapshot(path, **extra) -> Graph:
    graph = witness._load_fixture(path)
    for subject in list(graph.subjects(DAL.receiptModel, None)):
        graph.set((subject, DAL.receiptModel, DAL.SnapshotPerRevision))
    for predicate, value in extra.items():
        for subject in list(graph.subjects(DAL.receiptModel, None)):
            graph.set((subject, URIRef(DAL_NS + predicate), value))
    return graph


def test_h2_9_t2_snapshot_per_revision_is_refused_for_a_composite_family_written_in_place_with_either_guard():
    assert _refused(witness._load_fixture(SNAPSHOT_COMPOSITE)) == "CompositeBoundarySnapshotNotBuilt"
    assert _refused(_with_snapshot(ORDER_EXAMPLE)) == "CompositeBoundarySnapshotNotBuilt"
    guarded = _with_snapshot(ORDER_EXAMPLE)
    assert _refused(guarded) == "CompositeBoundarySnapshotNotBuilt"
    assert _refused(witness._load_fixture(witness.WITNESS_DIR / "template-cas-replace-composite-property-dataset-guard.ttl")) is None


def test_h2_9_t3_the_receipt_only_composite_writes_have_no_builder_and_a_named_graph_family_keeps_its_snapshot_warning():
    for stem in ("create-if-absent-composite", "cas-replace-composite-property", "tombstone-delete-composite"):
        for suffix in ("", "-dataset-guard"):
            assert stem + suffix not in BUILDERS
            assert stem + "-patch-log" + suffix in BUILDERS and stem + "-no-receipt" + suffix in BUILDERS
    from persistence.builders import _composite_create

    with pytest.raises(ValueError, match="snapshots are not built"):
        _composite_create(None, guards=True, dataset_guard=False, receipt="receipt")
    (ct,) = compile_targets(witness._load_fixture(witness.WITNESS_DIR / "write-discipline-snapshot-named-graph.ttl"))
    assert "ReceiptModelNotHonoured" in {d.kind for d in ct.diagnostics}
    assert {o.operation: o.template_id for o in ct.operations}["cas-replace"] == "cas-replace-named-graph"


def test_h2_9_t4_a_template_id_is_the_builders_identity_in_memory_and_in_the_profile_and_every_operation_is_built():
    seen = 0
    for path in witness.compile_fixtures():
        try:
            compiled = compile_targets(witness._load_fixture(path))
            profile, _ = compile_to_graph(witness._load_fixture(path))
        except CompileError:
            continue
        for ct in compiled:
            assert all(op.template_id in BUILDERS and "." not in op.template_id for op in ct.operations), path.name
            seen += len(ct.operations)
        ids = {str(o) for o in profile.objects(None, DAL.templateId)}
        assert ids <= set(BUILDERS), path.name
        for operations in instantiate_by_target(profile).values():
            assert all(text.startswith(("PREFIX", "SELECT", "ASK", "INSERT", "DELETE")) or "WHERE" in text for text in operations.values())
    assert seen > 100


def test_h2_9_t4b_the_template_machinery_is_gone():
    assert not hasattr(instantiate, "BUILDER_ONLY") and not hasattr(instantiate, "TEMPLATE_SUFFIX")
    with pytest.raises(ImportError):
        import persistence.render  # noqa: F401
    text = (witness.PACKAGE_DIR.parent.parent / "pyproject.toml").read_text(encoding="utf-8")
    assert "chevron" not in text and "mustache" not in text


def test_h2_9_t4c_an_operation_that_names_a_builder_that_does_not_exist_is_refused_by_name():
    graph, _ = compile_to_graph(witness._load_fixture(EXAMPLES_DIR / "baseline-single-class.ttl"))
    for node in graph.objects(None, DAL.templateId):
        graph.set((next(graph.subjects(DAL.templateId, node)), DAL.templateId, RdfLiteral("no-such-builder")))
        break
    with pytest.raises(ValueError, match="no-such-builder"):
        instantiate_by_target(graph)


def test_h2_9_t4d_a_slot_marker_is_filled_in_one_pass_and_a_marker_with_no_value_is_left_alone():
    assert slot_marker("payloadTriples") == "{{{payloadTriples}}}"
    text = "A {{{a}}} B {{{b}}} C {{{c}}}"
    assert fill_slots(text, {"a": "{{{b}}}", "b": "X"}) == "A {{{b}}} B X C {{{c}}}"
    assert fill_slots(text, {}) == text
    one = build("cas-replace-named-graph", dict(CANONICAL_CONTEXT))
    assert one.id == "cas-replace-named-graph"
