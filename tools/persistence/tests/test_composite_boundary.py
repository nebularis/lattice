# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""HO5: the compiler uses the classified ownership tree (formal-methods track H, slice HO5, ADR-A122).
Validation Pack: docs/developer/validation/FMH-HO5.md. Test IDs are HO5-Tn.

It rewrites the tests of H1.4a, which asserted the refusal of several node properties and the
first-property binding that ADR-A122 supersedes. The Validation Pack lists each with its replacement.

The generated replace runs on rdflib's in-memory ``Dataset``. The aggregates sit in the family's data
graph, as the profile declares. The payload slot is filled with the payload under test, in place of the
stand-in ``templatecheck`` uses."""

from __future__ import annotations

import random
import re
import warnings
from functools import lru_cache
from pathlib import Path

import pytest
from rdflib import BNode, Dataset, Graph, Literal, URIRef, Variable
from rdflib.namespace import RDF, XSD

from persistence import templatecheck, witness
from persistence.compiler import CompileError, compile_targets, compile_to_graph

from conftest import EXAMPLES_DIR

PAT = "https://example.org/lattice/patterns#"
SH = "http://www.w3.org/ns/shacl#"
DAL = "https://www.nebularis.org/neuro-semantic/lattice/persistence#"
EX = "https://example.org/lending#"
PX = "https://example.org/projects#"
PROJECT_EXAMPLE = EXAMPLES_DIR / "composite-project-ownership.ttl"
PROJECT_DATA = Path(__file__).resolve().parent / "fixtures" / "project-data.ttl"
ORDER_EXAMPLE = EXAMPLES_DIR / "composite-property-boundary-shacl.ttl"
TEMPLATE = "cas-replace-composite-property"
ROOT = URIRef(PX + "p1")
MEMBERS = {"m1", "m2", "plan1", "t1", "t2", "t3", "docOwned", "c1"}
OUTSIDE = {"acme", "alice", "docShared", "InProgress", "Done", "TaskStatuses", "report1", "p2", "m9"}


def _px(name: str) -> URIRef:
    return URIRef(PX + name)


def _compile(graph: Graph):
    (compiled,) = compile_targets(graph)
    return compiled


def _binding(compiled, name: str) -> str:
    operation = next(o for o in compiled.operations if o.template_id.startswith(TEMPLATE))
    return next(b.value for b in operation.bindings if b.name == name)


def _refusal(graph: Graph):
    with pytest.raises(CompileError) as error:
        compile_targets(graph)
    return error.value.cause


@lru_cache(maxsize=None)
def _project_text() -> str:
    compiled, _ = compile_to_graph(witness._load_fixture(PROJECT_EXAMPLE))
    return next(o for o in templatecheck.operations(compiled) if o.template == TEMPLATE).text


def _text(graph: Graph) -> str:
    compiled, _ = compile_to_graph(graph)
    return next(o for o in templatecheck.operations(compiled) if o.template == TEMPLATE).text


def _values() -> dict:
    return {
        Variable("root"): ROOT, Variable("epoch"): Literal(1),
        Variable("expectedSeq"): Literal(1, datatype=XSD.long), Variable("nextSeq"): Literal(2, datatype=XSD.long),
        Variable("newRev"): URIRef("urn:rev:2"), Variable("txnId"): URIRef("urn:txn:a"), Variable("requestDigest"): Literal("d"),
    }


def _nt(triples) -> str:
    return "".join(f"{s.n3()} {p.n3()} {o.n3()} . " for s, p, o in triples)


def _replace(graph: Graph, text: str, data: Graph, data_graph: str, root: URIRef = ROOT, payload=(), *, copy_to_default=False) -> Dataset:
    """Load ``data`` into ``data_graph``, a version row at sequence 1, and run the replace with ``payload``."""
    text = text.replace(templatecheck._SLOT_STAND_INS["payloadTriples"], _nt(payload))
    meta = URIRef(re.search(r"GRAPH <(urn:g:meta/\d+)>", text).group(1))
    values = {**_values(), Variable("root"): root}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        ds = Dataset()
        ds.graph(meta).add((root, URIRef(PAT + "epoch"), Literal(1)))
        ds.graph(meta).add((root, URIRef(PAT + "seq"), Literal(1, datatype=XSD.long)))
        target = ds.graph(URIRef(data_graph))
        for triple in data:
            target.add(triple)
            if copy_to_default:
                ds.default_context.add(triple)
        ds.update(text, initBindings=values)
    return ds


def _graph_triples(ds: Dataset, name: str) -> set:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return set(ds.graph(URIRef(name)))


def _project_data() -> Graph:
    return Graph().parse(PROJECT_DATA, format="turtle")


def _delete_set(data: Graph) -> set:
    """Every triple whose subject is the project or one of its eight members, written down by hand
    from the sketch's table and not computed by the path under test."""
    subjects = {ROOT, *(_px(m) for m in MEMBERS)}
    return {t for t in data if t[0] in subjects}


# ---- what the compiler binds


def test_ho5_t0_the_reference_fixture_has_the_sketch_delete_set():
    data = _project_data()
    assert len(_delete_set(data)) == 28
    assert {str(s).rsplit("#", 1)[-1] for s, _, _ in data} >= MEMBERS | OUTSIDE | {"p1"}


def test_ho5_t1a_the_shipped_composite_example_binds_its_owned_path_and_data_graph():
    """Rewrites H1.4a-T1, which asserted the single bound property."""
    compiled = _compile(witness._load_fixture(ORDER_EXAMPLE))
    assert _binding(compiled, "ownedPath") == f"(<{EX}lineItem>)?"
    assert _binding(compiled, "dataGraph") == "<urn:g:orders>"
    assert all(b.name != "compositeProperty" for o in compiled.operations for b in o.bindings)


@pytest.mark.parametrize("seed", range(6))
def test_ho5_t7_the_owned_path_does_not_depend_on_the_order_the_shape_was_written_in(seed):
    """Rewrites H1.4a-T7, which compared the closures of every declaration order."""
    base = witness._load_fixture(PROJECT_EXAMPLE)
    triples = sorted(base, key=str)
    random.Random(seed).shuffle(triples)
    shuffled = Graph()
    names: dict = {}
    for s, p, o in triples:
        shuffled.add(tuple(names.setdefault(t, BNode(f"b{seed}x{len(names)}")) if isinstance(t, BNode) else t for t in (s, p, o)))
    assert _binding(_compile(shuffled), "ownedPath") == _binding(_compile(base), "ownedPath")


# ---- what a replace does to the data graph


def test_ho5_t2a_a_value_property_declared_first_is_not_followed():
    """Rewrites H1.4a-T2, which asserted that a plain property that sorts first is not the bound property."""
    graph = witness._load_fixture(ORDER_EXAMPLE)
    shape = URIRef(EX + "OrderAggregateShape")
    audit = BNode()
    graph.add((shape, URIRef(SH + "property"), audit))
    graph.add((audit, URIRef(SH + "path"), URIRef(EX + "audit")))
    graph.add((audit, URIRef(SH + "datatype"), XSD.string))
    assert _binding(_compile(graph), "ownedPath") == f"(<{EX}lineItem>)?"


def test_ho5_t1_a_replace_removes_exactly_the_delete_set_and_writes_the_payload():
    data = _project_data()
    payload = {t for t in _delete_set(data) if t[1] != _px("status") or t[0] != _px("t3")}
    payload.add((_px("t3"), _px("status"), _px("InProgress")))
    graph = witness._load_fixture(PROJECT_EXAMPLE)
    ds = _replace(graph, _project_text(), data, "urn:g:projects", payload=payload)
    expected = (set(data) - _delete_set(data)) | payload
    assert _graph_triples(ds, "urn:g:projects") == expected
    outside = {t for t in data if t[0] in {_px(n) for n in OUTSIDE}}
    assert outside <= _graph_triples(ds, "urn:g:projects")


def test_ho5_t2_an_empty_payload_leaves_no_triple_of_the_project_or_its_members():
    data = _project_data()
    ds = _replace(witness._load_fixture(PROJECT_EXAMPLE), _project_text(), data, "urn:g:projects")
    left = _graph_triples(ds, "urn:g:projects")
    gone_subjects = {ROOT, *(_px(m) for m in MEMBERS)}
    assert not any(s in gone_subjects for s, _, _ in left)
    assert left == set(data) - _delete_set(data)


def test_ho5_t3_a_reference_given_sh_node_is_not_swept():
    """Review F1. A validation shape puts sh:node on a reference, which the old walk read as ownership."""
    graph = witness._load_fixture(ORDER_EXAMPLE)
    shape = URIRef(EX + "OrderAggregateShape")
    placed = BNode()
    graph.add((shape, URIRef(SH + "property"), placed))
    for p, o in (
        (URIRef(SH + "path"), URIRef(EX + "placedBy")),
        (URIRef(SH + "node"), URIRef(EX + "CustomerShape")),
        (URIRef(DAL + "ownership"), URIRef(DAL + "Reference")),
    ):
        graph.add((placed, p, o))
    graph.add((URIRef(EX + "CustomerShape"), RDF.type, URIRef(SH + "NodeShape")))
    order, customer = URIRef("urn:order:1"), URIRef("urn:customer:1")
    data = Graph()
    for triple in (
        (order, URIRef(EX + "lineItem"), URIRef("urn:li:1")), (URIRef("urn:li:1"), URIRef(EX + "sku"), Literal("ABC")),
        (order, URIRef(EX + "placedBy"), customer), (customer, URIRef(EX + "name"), Literal("Ada")),
    ):
        data.add(triple)
    ds = _replace(graph, _text(graph), data, "urn:g:orders", root=order)
    left = _graph_triples(ds, "urn:g:orders")
    assert (customer, URIRef(EX + "name"), Literal("Ada")) in left
    assert not any(s in {order, URIRef("urn:li:1")} for s, _, _ in left)


def test_ho5_t4_a_comment_linked_by_an_inverse_edge_goes_with_the_project():
    """Review F4. The comment points at its task, and the path reaches it with an inverse step."""
    data = _project_data()
    payload = {t for t in _delete_set(data) if t[0] != _px("c1")}
    ds = _replace(witness._load_fixture(PROJECT_EXAMPLE), _project_text(), data, "urn:g:projects", payload=payload)
    left = _graph_triples(ds, "urn:g:projects")
    assert not any(s == _px("c1") for s, _, _ in left)
    assert (_px("c1"), _px("onTask"), _px("t1")) not in left


def test_ho5_t5_the_shipped_composite_example_leaves_nothing_behind():
    """Rewrites H1.4a-T10."""
    graph = witness._load_fixture(ORDER_EXAMPLE)
    order = URIRef("urn:order:1")
    data = Graph()
    for triple in (
        (order, URIRef(EX + "status"), Literal("open")), (order, URIRef(EX + "lineItem"), URIRef("urn:li:1")),
        (URIRef("urn:li:1"), URIRef(EX + "sku"), Literal("ABC")),
    ):
        data.add(triple)
    ds = _replace(graph, _text(graph), data, "urn:g:orders", root=order)
    assert _graph_triples(ds, "urn:g:orders") == set()


def test_ho5_t6_two_owned_edges_from_the_root_both_sweep():
    """Rewrites H1.4a-T11, which showed the other member left behind and is now refused no longer."""
    graph = witness._load_fixture(ORDER_EXAMPLE)
    shape = URIRef(EX + "OrderAggregateShape")
    payment = BNode()
    graph.add((shape, URIRef(SH + "property"), payment))
    for p, o in (
        (URIRef(SH + "path"), URIRef(EX + "payment")), (URIRef(SH + "node"), URIRef(EX + "PaymentShape")),
        (URIRef(DAL + "ownership"), URIRef(DAL + "Owned")),
    ):
        graph.add((payment, p, o))
    graph.add((URIRef(EX + "PaymentShape"), RDF.type, URIRef(SH + "NodeShape")))
    order = URIRef("urn:order:1")
    data = Graph()
    for triple in (
        (order, URIRef(EX + "lineItem"), URIRef("urn:li:1")), (URIRef("urn:li:1"), URIRef(EX + "sku"), Literal("ABC")),
        (order, URIRef(EX + "payment"), URIRef("urn:pay:1")), (URIRef("urn:pay:1"), URIRef(EX + "amount"), Literal("10")),
    ):
        data.add(triple)
    ds = _replace(graph, _text(graph), data, "urn:g:orders", root=order)
    assert _graph_triples(ds, "urn:g:orders") == set()


# ---- what the validator refuses


def _project_with(extra_ttl: str, removing: tuple = ()) -> Graph:
    graph = witness._load_fixture(PROJECT_EXAMPLE)
    for triple in removing:
        graph.remove(triple)
    graph.parse(
        data="@prefix dal: <%s> . @prefix ex: <%s> . @prefix sh: <%s> . @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n%s" % (DAL, PX, SH, extra_ttl),
        format="turtle",
    )
    return graph


def test_ho5_t8_a_key_on_a_property_of_the_shape_is_accepted_and_a_key_outside_it_is_refused():
    accepted = _project_with(
        'ex:DocTitleUnique a dal:UniquenessConstraint ; dal:constraintId "doc-title" ; dal:appliesTo ex:ProjectClass ; '
        "dal:keyProperty ( ex:title ) ; dal:onViolation dal:Reject ."
    )
    assert _compile(accepted)
    outside = _project_with(
        'ex:SerialUnique a dal:UniquenessConstraint ; dal:constraintId "serial" ; dal:appliesTo ex:ProjectClass ; '
        "dal:keyProperty ( ex:serialNumber ) ; dal:onViolation dal:Reject ."
    )
    assert _refusal(outside).kind == "UniquenessOutsideBoundary"


def test_ho5_t9_a_member_class_at_depth_three_that_declares_its_own_boundary_is_refused():
    graph = _project_with(
        "ex:CommentClass a dal:ClassScope ; dal:targetClass ex:Comment . "
        "ex:CommentBoundary a dal:AggregateBoundaryProfile ; dal:appliesTo ex:CommentClass ; dal:strategy dal:NamedGraphBoundary ."
    )
    cause = _refusal(graph)
    assert type(cause).__name__ == "BoundaryConflict" and f"{PX}Comment" in str(cause)


def test_ho5_t10a_a_composite_profile_without_a_data_graph_is_refused():
    graph = witness._load_fixture(PROJECT_EXAMPLE)
    graph.remove((URIRef(PX + "ProjectBoundaryProfile"), URIRef(DAL + "dataGraph"), None))
    assert _refusal(graph).kind == "MissingDataGraph"


def test_ho5_t10_the_default_graph_copy_of_the_data_is_untouched_by_a_replace():
    data = _project_data()
    ds = _replace(witness._load_fixture(PROJECT_EXAMPLE), _project_text(), data, "urn:g:projects", copy_to_default=True)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        assert set(ds.default_context) == set(data)
    assert not any(s == ROOT for s, _, _ in _graph_triples(ds, "urn:g:projects"))


def test_ho5_t11_a_shape_that_owns_no_edge_is_refused():
    """Rewrites H1.4a-T6, which asserted that a shape with only plain properties compiled."""
    graph = witness._load_fixture(ORDER_EXAMPLE)
    for ps in list(graph.objects(URIRef(EX + "OrderAggregateShape"), URIRef(SH + "property"))):
        graph.remove((URIRef(EX + "OrderAggregateShape"), URIRef(SH + "property"), ps))
    audit = BNode()
    graph.add((URIRef(EX + "OrderAggregateShape"), URIRef(SH + "property"), audit))
    graph.add((audit, URIRef(SH + "path"), URIRef(EX + "audit")))
    graph.add((audit, URIRef(SH + "datatype"), XSD.string))
    assert _refusal(graph).kind == "CompositeBoundaryWithoutOwnedEdges"


@pytest.mark.parametrize("kind", ["MissingDataGraph", "CompositeBoundaryWithoutOwnedEdges"])
def test_ho5_t12_each_new_witness_triggers_exactly_its_own_refusal(kind):
    observed = witness.observe_compile([witness.WITNESS_DIR / f"refusal-{kind}.ttl"])
    assert set(observed) == {witness.Rule(witness.REFUSAL, kind)}


def test_ho5_t13_the_old_refusals_are_gone():
    source = (Path(witness.PACKAGE_DIR) / "validator.py").read_text(encoding="utf-8")
    assert "CompositeBoundaryMultipleProperties" not in source
    assert not (witness.WITNESS_DIR / "refusal-CompositeBoundaryMultipleProperties.ttl").exists()
    assert not (witness.WITNESS_DIR / "refusal-BoundaryCycleError.ttl").exists()
