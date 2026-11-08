# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The ledger's shapes at scale (ADR-A124, STD-155): LG1-09's tree of 10,000 account definitions and LG2-10's pass of 5,000 postings
and 10,000 balance records, every shape run through pySHACL on rdflib and the runtime laws as plain SELECTs on Oxigraph too, the
time of each recorded as a pytest property (`--junit-xml` shows it) and never asserted. A broken record is then found, so a clean
result is not an empty query. The small versions `check` runs are in `tools/test_ledger.py`, which also holds why two of the
runtime shapes find nothing on Oxigraph (TD-158) and what the heavy ones cost (TD-159)."""

from __future__ import annotations

import time
from pathlib import Path

import pyoxigraph as ox
from ledger_corpus import LDG, XSD, account_tree, one_pass
from pyshacl import validate
from rdflib import Graph
from rdflib.namespace import SH

ROOT = Path(__file__).resolve().parents[2]
ONTOLOGY = ROOT / "ontology"
LEDGER = ONTOLOGY / "ledger"


def _graph(*paths: Path) -> Graph:
    g = Graph()
    for path in paths:
        g.parse(path)
    return g


MODEL = _graph(ONTOLOGY / "foundation" / "spec" / "foundation.ttl", ONTOLOGY / "vocabulary" / "spec" / "vocabulary.ttl",
               ONTOLOGY / "quantification" / "spec" / "quantification.ttl", LEDGER / "spec" / "ledger.ttl",
               LEDGER / "spec" / "ledger-runtime.ttl", LEDGER / "vocab" / "ledger-vocab.ttl")
SHAPES = _graph(LEDGER / "shapes" / "structural.ttl", LEDGER / "shapes" / "constraints.ttl", LEDGER / "shapes" / "runtime.ttl")
RUNTIME = _graph(LEDGER / "shapes" / "runtime.ttl")


def _violating(report: Graph) -> set[str]:
    return {str(report.value(r, SH.sourceShape)) for r in report.subjects(SH.resultSeverity, SH.Violation)}


def _runtime_selects() -> list[tuple[str, str]]:
    """Each class-targeted runtime shape as the plain SELECT its one run is, `$this` the class (CAP-64, as `tools/test_ledger.py`)."""
    found = []
    for shape in sorted(RUNTIME.subjects(SH.targetNode, None)):
        for target in RUNTIME.objects(shape, SH.targetNode):
            for constraint in RUNTIME.objects(shape, SH.sparql):
                text = str(RUNTIME.value(constraint, SH.select)).replace("SELECT $this ", "SELECT ").replace("GROUP BY $this ", "GROUP BY ")
                found.append((str(shape), text.replace("$this", f"<{target}>")))
    return found


def _on_oxigraph(store: ox.Store) -> set[tuple[str, str]]:
    return {(shape, row["value"].value) for shape, query in _runtime_selects() for row in store.query(query)}


def test_lg1_09_every_shape_finishes_on_a_tree_of_ten_thousand_definitions(record_property) -> None:
    g = MODEL + account_tree(10_000)
    started = time.monotonic()
    conforms, report, _ = validate(g, shacl_graph=SHAPES, inference="none", advanced=True)
    record_property("shapes_10000_definitions_pyshacl_seconds", time.monotonic() - started)
    assert conforms, _violating(report)


def test_lg2_10_every_shape_finishes_on_a_pass_of_five_thousand_postings(record_property) -> None:
    g = MODEL + one_pass(5_000)
    started = time.monotonic()
    conforms, report, _ = validate(g, shacl_graph=SHAPES, inference="none", advanced=True)
    record_property("shapes_5000_postings_10000_balances_pyshacl_seconds", time.monotonic() - started)
    assert conforms, _violating(report)
    started = time.monotonic()
    store = ox.Store()
    store.load(input=g.serialize(format="nt").encode("utf-8"), format=ox.RdfFormat.N_TRIPLES)
    found = _on_oxigraph(store)
    record_property("runtime_shapes_5000_postings_10000_balances_oxigraph_seconds", time.monotonic() - started)
    assert found == set()
    leaf = ox.NamedNode("https://example.org/lattice/ledger/runtime-scale/posting0")
    effective = ox.NamedNode(str(LDG.effectivePosition))
    for quad in list(store.quads_for_pattern(leaf, effective, None, None)):
        store.remove(quad)
    store.add(ox.Quad(leaf, effective, ox.Literal("2", datatype=ox.NamedNode(XSD + "integer")), ox.DefaultGraph()))
    assert _on_oxigraph(store) == {(str(LDG.NotForwardDatedShape), leaf.value)}
