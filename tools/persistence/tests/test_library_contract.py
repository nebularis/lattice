# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The caller library and the compiler agree (formal-methods H2.8a, ADR-A132 decision 3).

The library reads the contract a compile emits, and the compiler derives it from the builders. Here the two are compared for every
operation of every configuration with an expected profile, so a change to a part, a parameter or a payload contract that the library does
not read is caught in the compiler's own check. The compiled profiles the library's tests read are held to what compile emits now."""

from __future__ import annotations

from pathlib import Path

import pytest
from rdflib import Graph
from rdflib.compare import isomorphic

from expected_profiles import CONFIGURATIONS, emit
from lattice_persistence import read_contracts
from persistence.contract_emit import contract_for

LIBRARY_DATA = Path(__file__).resolve().parents[3] / "packages" / "persistence" / "python" / "tests" / "data"
LIBRARY_FIXTURES = ("baseline-single-class", "append-stream-dataset-guard", "write-discipline-delta-membership", "composite-project-ownership")


@pytest.mark.parametrize("name,example,options", CONFIGURATIONS, ids=[c[0] for c in CONFIGURATIONS])
def test_library_reads_what_the_compiler_derives(name, example, options):
    profile = emit(example, **options)
    operations = read_contracts(profile)
    assert operations
    for op in operations:
        derived = contract_for(profile, op.node, guards=options.get("guards", True), graph_names=options.get("graph_names", "query"))
        assert derived is not None, op.template_id
        assert op.kind is derived.kind and op.version == derived.version
        assert op.parameters == derived.parameters, op.template_id
        assert (op.digest.as_pairs() if op.digest else None) == (derived.digest.parts() if derived.digest else None), op.template_id
        assert (op.payload is None) == (derived.payload is None)
        if op.payload:
            assert (op.payload.parameter, op.payload.root) == (derived.payload.parameter, derived.payload.root)


def test_library_reads_the_reference_edges_of_a_composite_family():
    ops = read_contracts(emit("composite-project-ownership"))
    edges = [e for op in ops if op.payload for e in op.payload.edges]
    assert edges and {e.reference_mode for e in edges} <= {"ByIdentity", "Pinned"}
    assert all(e.ownership and e.predicate for e in edges)


@pytest.mark.parametrize("name", LIBRARY_FIXTURES)
def test_the_library_fixture_is_what_compile_emits(name):
    fixture = Graph().parse(LIBRARY_DATA / f"{name}.compiled.ttl")
    assert isomorphic(fixture, emit(name)), f"{name}.compiled.ttl is stale, regenerate it with persistence compile"
