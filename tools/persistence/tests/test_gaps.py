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
from rdflib import Graph

from persistence import witness
from persistence.cli import main
from persistence.compiler import compile_targets
from persistence.gaps import RULES, find_gaps

from conftest import EXAMPLES_DIR



def _load(name: str) -> Graph:
    return witness._load_fixture(EXAMPLES_DIR / name)


def _ids(graph: Graph) -> set[str]:
    return {g.gap for g in find_gaps(compile_targets(graph))}


def _gaps(graph: Graph):
    return find_gaps(compile_targets(graph))


def _example(name: str) -> set[str]:
    return _ids(_load(name))


# ---- the entries present today

# A slice that closes one of these removes it here and in persistence.gaps. HO5 removed the three
# about ownership, the inverse path and the default graph (TD-35, TD-37, TD-40), and HO7 the missing
# composite create and tombstone delete (TD-04), and HO8 the graph named from the root's local name (TD-38).
COMPOSITE: set[str] = set()
EVERY_WRITING_TARGET = {"InfrastructureGraphsFixed", "RetentionAndEpochBumpNotGenerated"}


def test_h1_4b_t1_the_composite_example_reports_no_composite_gap():
    assert _example("composite-property-boundary-shacl.ttl") == COMPOSITE | EVERY_WRITING_TARGET


def test_h1_4b_t2_a_named_graph_example_reports_only_what_every_writing_target_does():
    assert _example("baseline-single-class.ttl") == EVERY_WRITING_TARGET


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
    """No rule is vacuous: each is reached by a fixture in this module."""
    reached: set[str] = set()
    for name in ("baseline-single-class.ttl", "append-stream-dataset-guard.ttl", "identity-epoch-privacy-profile.ttl"):
        reached |= _example(name)
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
    assert "GAP [InfrastructureGraphsFixed]" in text and "TD-05" in text
    assert main(["gaps", "--json", spec, example]) == 0
    data = json.loads(capsys.readouterr().out)
    assert {entry["gap"] for entry in data} == COMPOSITE | EVERY_WRITING_TARGET
    assert {"gap", "target", "obligation", "reference", "closes_in", "message"} <= set(data[0])


def test_h1_4b_t11_the_cli_exits_nonzero_when_the_configuration_does_not_compile(capsys):
    broken = str(EXAMPLES_DIR / "invalid-compositeboundary-receiptonly.ttl")
    spec = str(EXAMPLES_DIR.parent / "spec" / "persistence.ttl")
    assert main(["gaps", spec, broken]) == 1
    assert "does not compile" in capsys.readouterr().err


def test_h1_4b_t12_a_declaration_the_compiler_cannot_honour_is_not_a_gap():
    """A shard count above one is the warning ShardingNotHonoured, and an unconditional write for a boundary
    with no named graph is a refusal. Neither is left to the report."""
    assert {"ShardCountNotHonoured", "UnconditionalWriteNamedGraphOnly"}.isdisjoint(RULES)
