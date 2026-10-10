# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""H1.4b: the declaration/implementation gap report (formal-methods track H).
Validation Pack: docs/developer/validation/FMH-H1-4b.md. Test IDs are H1.4b-Tn.

The expected entries are the ones present at the time the test runs. A slice that closes a gap
removes its rule from ``persistence.gaps`` and its entry from the expectations below, in the same
commit (plan §3, "H1.4b and H1.5 after the aggregate-ownership review")."""

from __future__ import annotations

import json

import pytest
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import XSD

from persistence import witness
from persistence.cli import main
from persistence.compiler import compile_targets
from persistence.gaps import RULES, find_gaps

from conftest import EXAMPLES_DIR

EX = "https://example.org/lending#"
SH = "http://www.w3.org/ns/shacl#"
DAL = "https://www.nebularis.org/neuro-semantic/lattice/persistence#"


def _load(name: str) -> Graph:
    return witness._load_fixture(EXAMPLES_DIR / name)


def _ids(graph: Graph) -> set[str]:
    return {g.gap for g in find_gaps(compile_targets(graph))}


def _gaps(graph: Graph):
    return find_gaps(compile_targets(graph))


def _example(name: str) -> set[str]:
    return _ids(_load(name))


# ---- the entries present today

# A slice that closes one of these removes it here and in persistence.gaps.
COMPOSITE = {
    "CompositeNoLifecycleOperations",  # TD-04, HO7
    "CompositeOwnershipAssumed",  # TD-35, HO5
    "CompositeUsesDefaultGraph",  # TD-40, HO5
}
EVERY_WRITING_TARGET = {"InfrastructureGraphsFixed", "RetentionAndEpochBumpNotGenerated"}


def test_h1_4b_t1_the_composite_example_reports_each_composite_gap_naming_the_shape_and_property():
    gaps = {g.gap: g for g in _gaps(_load("composite-property-boundary-shacl.ttl"))}
    assert set(gaps) == COMPOSITE | EVERY_WRITING_TARGET
    assert "OrderAggregateShape" in gaps["CompositeOwnershipAssumed"].message
    assert "lineItem" in gaps["CompositeOwnershipAssumed"].message
    assert gaps["CompositeOwnershipAssumed"].reference == "TD-35" and gaps["CompositeOwnershipAssumed"].closes_in == "HO5"
    assert gaps["CompositeNoLifecycleOperations"].reference == "TD-04"
    assert gaps["CompositeUsesDefaultGraph"].reference == "TD-40"
    assert all(g.obligation == "unimplemented" for k, g in gaps.items() if k in COMPOSITE)


def test_h1_4b_t2_a_named_graph_example_reports_the_graph_naming_gap_and_no_composite_gap():
    assert _example("baseline-single-class.ttl") == {"NamedGraphNamedFromLocalName"} | EVERY_WRITING_TARGET


def test_h1_4b_t3_text_after_the_id_is_named_as_dropped():
    graph = _load("baseline-single-class.ttl")
    profile = URIRef(EX + "LoanApplicationStrongProfile")
    graph.set((profile, URIRef(DAL + "graphIriTemplate"), Literal("urn:g:loan-application/{id}/data")))
    (gap,) = [g for g in _gaps(graph) if g.gap == "NamedGraphNamedFromLocalName"]
    assert "'/data'" in gap.message and "dropped" in gap.message


def test_h1_4b_t4_an_inverse_path_in_a_composite_shape_is_reported():
    graph = _load("composite-property-boundary-shacl.ttl")
    shape = URIRef(EX + "OrderAggregateShape")
    prop, path = BNode(), BNode()
    graph.add((shape, URIRef(SH + "property"), prop))
    graph.add((prop, URIRef(SH + "path"), path))
    graph.add((path, URIRef(SH + "inversePath"), URIRef(EX + "ofOrder")))
    graph.add((prop, URIRef(SH + "class"), URIRef(EX + "Payment")))
    (gap,) = [g for g in _gaps(graph) if g.gap == "CompositeInversePathMisread"]
    assert gap.reference == "TD-37" and "OrderAggregateShape" in gap.message


def test_h1_4b_t5_a_declared_shard_count_above_one_is_reported():
    graph = _load("baseline-single-class.ttl")
    graph.add((URIRef(EX + "LoanApplicationStrongProfile"), URIRef(DAL + "txnShards"), Literal(4, datatype=XSD.long)))
    (gap,) = [g for g in _gaps(graph) if g.gap == "ShardCountNotHonoured"]
    assert "txnShards 4" in gap.message


def test_h1_4b_t6_an_unconditional_write_to_a_target_that_is_not_a_named_graph_is_reported():
    graph = _load("value-based-cas.ttl")
    profile = URIRef(EX + "OrderStatusConcurrencyProfile")
    graph.set((profile, URIRef(DAL + "concurrencyProfile"), URIRef(DAL + "ProvidedConcurrency")))
    graph.remove((profile, URIRef(DAL + "valueGuardProperty"), None))
    assert "UnconditionalWriteNamedGraphOnly" in _ids(graph)


@pytest.mark.parametrize(
    ("example", "expected"),
    [
        ("append-stream-dataset-guard.ttl", "VersionRowCreatedByCaller"),
        ("identity-epoch-privacy-profile.ttl", "RestoreRunbookBindingsUnread"),
        ("baseline-single-class.ttl", "RetentionAndEpochBumpNotGenerated"),
    ],
)
def test_h1_4b_t7_the_caller_and_housekeeping_obligations_are_reported(example, expected):
    gaps = {g.gap: g for g in _gaps(_load(example))}
    assert gaps[expected].obligation in {"caller", "housekeeping"}


def test_h1_4b_t8_every_rule_fires_somewhere():
    """No rule is vacuous: each of the eleven is reached by a fixture in this module."""
    reached: set[str] = set()
    for name in ("composite-property-boundary-shacl.ttl", "baseline-single-class.ttl", "append-stream-dataset-guard.ttl",
                 "identity-epoch-privacy-profile.ttl"):
        reached |= _example(name)
    reached |= {"CompositeInversePathMisread", "ShardCountNotHonoured", "UnconditionalWriteNamedGraphOnly"}  # t4, t5, t6
    assert reached == set(RULES)


def test_h1_4b_t9_the_report_is_identical_across_runs_and_independent_of_triple_order():
    graph = _load("composite-property-boundary-shacl.ttl")
    shuffled = Graph()
    for triple in sorted(graph, key=lambda t: tuple(reversed([str(x) for x in t]))):
        shuffled.add(triple)
    assert _gaps(graph) == _gaps(shuffled) == _gaps(graph)
    assert _gaps(graph) == sorted(_gaps(graph))


def test_h1_4b_t10_the_cli_prints_the_report_as_text_and_as_json(capsys):
    example = str(EXAMPLES_DIR / "composite-property-boundary-shacl.ttl")
    spec = str(EXAMPLES_DIR.parent / "spec" / "persistence.ttl")
    assert main(["gaps", spec, example]) == 0
    text = capsys.readouterr().out
    assert "GAP [CompositeOwnershipAssumed]" in text and "TD-35" in text
    assert main(["gaps", "--json", spec, example]) == 0
    data = json.loads(capsys.readouterr().out)
    assert {entry["gap"] for entry in data} == COMPOSITE | EVERY_WRITING_TARGET
    assert {"gap", "target", "obligation", "reference", "closes_in", "message"} <= set(data[0])


def test_h1_4b_t11_the_cli_exits_nonzero_when_the_configuration_does_not_compile(capsys):
    broken = str(EXAMPLES_DIR / "invalid-compositeboundary-receiptonly.ttl")
    spec = str(EXAMPLES_DIR.parent / "spec" / "persistence.ttl")
    assert main(["gaps", spec, broken]) == 1
    assert "does not compile" in capsys.readouterr().err
