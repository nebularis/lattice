# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""H1.5: a compiled profile serialises to the same bytes every time (formal-methods track H, TD-09).
Validation Pack: docs/developer/validation/FMH-H1-5.md. Test IDs are H1.5-Tn.

Until H1.5 the blank nodes of a compiled profile had fresh labels per run, so the Turtle was
isomorphic between runs and never identical, and a compiled profile could not be committed or diffed."""

from __future__ import annotations

import os
import random
import re
import subprocess
import sys

import pytest
from rdflib import BNode, Graph

from persistence import witness
from persistence.compiler import CompileError, compile_to_graph

from conftest import EXAMPLES_DIR

SPEC = EXAMPLES_DIR.parent / "spec" / "persistence.ttl"
REPO_ROOT = EXAMPLES_DIR.parents[2]
STABLE_LABEL = re.compile(r"^p[0-9a-f]{12}(-.+)?$")


def _compiling_examples() -> list[str]:
    names = []
    for path in sorted(EXAMPLES_DIR.glob("*.ttl")):
        if path.name.startswith("invalid-") or path.name == "capability-spec-example.ttl":
            continue
        try:
            compile_to_graph(witness._load_fixture(path))
        except CompileError:
            continue
        names.append(path.name)
    return names


EXAMPLES = _compiling_examples()


def _turtle(graph: Graph) -> bytes:
    return graph.serialize(format="turtle").encode("utf-8")


def _compile(name: str, shuffle_seed: int | None = None) -> Graph:
    source = witness._load_fixture(EXAMPLES_DIR / name)
    if shuffle_seed is not None:
        triples = sorted(source, key=str)
        random.Random(shuffle_seed).shuffle(triples)
        source = Graph()
        for triple in triples:
            source.add(triple)
    out, _ = compile_to_graph(source)
    return out


def test_h1_5_t0_the_examples_under_test_are_not_empty():
    assert len(EXAMPLES) >= 15


@pytest.mark.parametrize("name", EXAMPLES)
def test_h1_5_t1_two_compiles_of_one_example_are_byte_identical(name):
    assert _turtle(_compile(name)) == _turtle(_compile(name))


@pytest.mark.parametrize("name", EXAMPLES)
def test_h1_5_t2_the_order_the_configuration_was_loaded_in_does_not_change_the_bytes(name):
    assert _turtle(_compile(name, shuffle_seed=1)) == _turtle(_compile(name, shuffle_seed=2))


@pytest.mark.parametrize("name", EXAMPLES)
def test_h1_5_t3_every_blank_node_has_a_label_derived_from_its_target(name):
    nodes = {n for triple in _compile(name) for n in triple if isinstance(n, BNode)}
    assert nodes
    assert all(STABLE_LABEL.match(str(n)) for n in nodes), sorted(str(n) for n in nodes if not STABLE_LABEL.match(str(n)))[:3]


def test_h1_5_t4_the_labels_of_two_targets_in_one_compile_do_not_collide():
    out = _compile("identity-minting-anchors.ttl")
    stems = {str(n).split("-", 1)[0] for triple in out for n in triple if isinstance(n, BNode)}
    assert len(stems) == 7  # one per target


@pytest.mark.parametrize(
    "name", ["composite-property-boundary-shacl.ttl", "identity-epoch-privacy-profile.ttl", "identity-minting-anchors.ttl"]
)
def test_h1_5_t5_separate_processes_with_different_hash_seeds_write_the_same_bytes(name, tmp_path):
    written = []
    for seed in ("1", "2"):
        out = tmp_path / f"{seed}.ttl"
        env = {**os.environ, "PYTHONHASHSEED": seed}
        subprocess.run(
            [sys.executable, "-m", "persistence", "compile", str(SPEC), str(EXAMPLES_DIR / name), "--out", str(out)],
            check=True, capture_output=True, env=env, cwd=REPO_ROOT,
        )
        written.append(out.read_bytes())
    assert written[0] == written[1]


def test_h1_5_t5b_a_capability_check_node_is_stable_too():
    """Only a configuration compiled with a capability spec has a capability check node."""
    def compiled() -> Graph:
        source = witness._load_fixture(EXAMPLES_DIR / "baseline-single-class.ttl")
        source.parse(EXAMPLES_DIR / "capability-spec-example.ttl", format="turtle")
        out, targets = compile_to_graph(source)
        assert any(t.check is not None for t in targets)
        return out

    first, second = compiled(), compiled()
    assert _turtle(first) == _turtle(second)
    assert any(str(n).endswith("-check") for triple in first for n in triple if isinstance(n, BNode))


def test_h1_5_t6_the_stable_labels_keep_the_profile_a_valid_graph_instantiate_reads(tmp_path):
    from persistence.instantiate import instantiate_to_directory

    out = _compile("composite-property-boundary-shacl.ttl")
    profile = tmp_path / "p.ttl"
    profile.write_text(out.serialize(format="turtle"))
    reread = Graph().parse(profile, format="turtle")
    written = instantiate_to_directory(reread, tmp_path / "sparql")
    assert {p.name for p in written} >= {"cas-replace.rq", "gap-scan-audit.rq"}
