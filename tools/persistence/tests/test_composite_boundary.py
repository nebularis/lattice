# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""H1.4a: a composite boundary that leads to more than one other node is refused
(formal-methods track H, decision H-D4), and the property the generated replace
follows is the one that leads to a node, whatever order the shape was written in.
Validation Pack: docs/developer/validation/FMH-H1-4a.md. Test IDs are H1.4a-Tn."""

from __future__ import annotations

import itertools
import re
import warnings

import pytest
from rdflib import RDF, BNode, Dataset, Graph, Literal, URIRef, Variable
from rdflib.namespace import XSD

from persistence import templatecheck, witness
from persistence.boundary import walk_boundary_shape
from persistence.compiler import CompileError, compile_to_graph, compile_targets

from conftest import EXAMPLES_DIR

EX = "https://example.org/lending#"
SH = "http://www.w3.org/ns/shacl#"
SHAPE = URIRef(EX + "OrderAggregateShape")
KIND = "CompositeBoundaryMultipleProperties"

# property key -> (path, node shape or None for a plain value property)
PROPERTIES = {
    "audit": (EX + "audit", None),  # sorts before lineItem, so a first-path binding would pick it
    "lineItem": (EX + "lineItem", EX + "LineItemShape"),
    "payment": (EX + "payment", EX + "PaymentShape"),
}


def _example() -> Graph:
    return witness._load_fixture(EXAMPLES_DIR / "composite-property-boundary-shacl.ttl")


def _with_properties(order: tuple[str, ...], nested: str | None = None) -> Graph:
    """The shipped composite example with its root shape's properties replaced by
    ``order``, written in that order. ``nested`` adds a node property to the
    line item shape as well."""
    g = Graph()
    for triple in _example():
        g.add(triple)
    for ps in list(g.objects(SHAPE, URIRef(SH + "property"))):
        g.remove((SHAPE, URIRef(SH + "property"), ps))
    for key in order:
        path, node = PROPERTIES[key]
        ps = BNode()
        g.add((SHAPE, URIRef(SH + "property"), ps))
        g.add((ps, URIRef(SH + "path"), URIRef(path)))
        if node:
            g.add((ps, URIRef(SH + "node"), URIRef(node)))
    for shape in (EX + "PaymentShape", EX + "DetailShape"):
        g.add((URIRef(shape), RDF.type, URIRef(SH + "NodeShape")))
    if nested:
        ps = BNode()
        g.add((URIRef(EX + "LineItemShape"), URIRef(SH + "property"), ps))
        g.add((ps, URIRef(SH + "path"), URIRef(EX + nested)))
        g.add((ps, URIRef(SH + "node"), URIRef(EX + "DetailShape")))
    return g


def _bound_property(graph: Graph) -> str:
    (compiled,) = compile_targets(graph)
    operation = next(o for o in compiled.operations if o.template_id.startswith("cas-replace-composite"))
    return next(b.value for b in operation.bindings if b.name == "compositeProperty")


def _refusal(graph: Graph):
    with pytest.raises(CompileError) as error:
        compile_targets(graph)
    return error.value.cause


def test_h1_4a_t1_the_shipped_composite_example_binds_its_one_node_property():
    assert _bound_property(_example()) == f"<{EX}lineItem>"


@pytest.mark.parametrize("order", [("audit", "lineItem"), ("lineItem", "audit")])
def test_h1_4a_t2_a_plain_property_that_sorts_or_is_declared_first_is_not_the_bound_property(order):
    """Before the fix, ("audit", "lineItem") bound ``audit`` and the line item was never swept."""
    assert _bound_property(_with_properties(order)) == f"<{EX}lineItem>"


@pytest.mark.parametrize("order", list(itertools.permutations(["lineItem", "payment"])))
def test_h1_4a_t3_two_node_properties_are_refused_in_either_order(order):
    cause = _refusal(_with_properties(order))
    assert cause.kind == KIND


def test_h1_4a_t4_the_refusal_is_identical_whatever_order_the_shape_was_written_in():
    first, second = (str(_refusal(_with_properties(o))) for o in (("lineItem", "payment"), ("payment", "lineItem")))
    assert first == second
    assert str(SHAPE) in first and EX + "lineItem" in first and EX + "payment" in first


def test_h1_4a_t5_a_node_property_on_a_member_counts_too():
    assert _refusal(_with_properties(("lineItem",), nested="detail")).kind == KIND


def test_h1_4a_t6_a_shape_with_only_plain_properties_compiles_as_before():
    assert _bound_property(_with_properties(("audit",))) == f"<{EX}audit>"


def test_h1_4a_t7_the_closure_does_not_depend_on_the_order_the_triples_were_written_in():
    results = {
        tuple(map(str, (c.composite_properties, c.node_properties)))
        for order in itertools.permutations(["audit", "lineItem", "payment"])
        for c in [walk_boundary_shape(_with_properties(order), SHAPE)]
    }
    assert len(results) == 1


def test_h1_4a_t8_node_properties_hold_only_the_paths_that_lead_to_a_node():
    closure = walk_boundary_shape(_example(), SHAPE)
    assert [str(p) for p in closure.node_properties] == [EX + "lineItem"]
    assert {str(p) for p in closure.composite_properties} == {EX + "lineItem", EX + "sku"}


def test_h1_4a_t9_the_witness_triggers_exactly_this_refusal():
    observed = witness.observe_compile([witness.WITNESS_DIR / f"refusal-{KIND}.ttl"])
    assert set(observed) == {witness.Rule(witness.REFUSAL, KIND)}


# ---- why: what a replace leaves behind. Runs the generated update on rdflib's in-memory store.
# The same scenarios were cross-checked on Oxigraph (spikes/persistence-oxigraph) with identical results.


def _replace_and_count_left(bound_property: str, with_payment: bool) -> list[str]:
    """Run the generated ``cas-replace-composite-property`` update on an order and return the
    subjects that still have triples in the default graph afterwards."""
    compiled, _ = compile_to_graph(_example())
    text = next(o for o in templatecheck.operations(compiled) if o.template == "cas-replace-composite-property").text
    meta = re.search(r"GRAPH <(urn:g:meta/\d+)>", text).group(1)
    pat = "https://example.org/lattice/patterns#"
    root = URIRef("urn:order:1")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        dataset = Dataset()
        dataset.graph(URIRef(meta)).add((root, URIRef(pat + "epoch"), Literal(1)))
        dataset.graph(URIRef(meta)).add((root, URIRef(pat + "seq"), Literal(1, datatype=XSD.long)))
        rows = [
            (root, "status", Literal("open")),
            (root, "lineItem", URIRef("urn:li:1")),
            (URIRef("urn:li:1"), "sku", Literal("ABC")),
        ]
        if with_payment:
            rows += [(root, "payment", URIRef("urn:pay:1")), (URIRef("urn:pay:1"), "amount", Literal("10"))]
        for subject, predicate, obj in rows:
            dataset.default_context.add((subject, URIRef(EX + predicate), obj))
        values = {
            "root": root, "epoch": Literal(1), "expectedSeq": Literal(1, datatype=XSD.long),
            "nextSeq": Literal(2, datatype=XSD.long), "newRev": URIRef("urn:rev:2"),
            "txnId": URIRef("urn:txn:a"), "requestDigest": Literal("d"),
        }
        dataset.update(
            text.replace(f"<{EX}lineItem>", f"<{EX}{bound_property}>"),
            initBindings={Variable(k): v for k, v in values.items()},
        )
        return sorted({str(s) for s, _, _ in dataset.default_context})


def test_h1_4a_t10_one_node_property_leaves_nothing_behind():
    assert _replace_and_count_left("lineItem", with_payment=False) == []


@pytest.mark.parametrize("bound,left", [("lineItem", "urn:pay:1"), ("payment", "urn:li:1")])
def test_h1_4a_t11_with_two_node_properties_the_unbound_ones_members_are_left_behind(bound, left):
    """The reason for the refusal. Whichever property is bound, the other's member keeps its triples."""
    assert _replace_and_count_left(bound, with_payment=True) == [left]
