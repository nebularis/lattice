# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""H2.6e: how references between versions are declared (formal-methods track H, plan 4.11). `dal:referenceMode` sits on a property shape of a
boundary shape beside `dal:ownership`. These tests cover the vocabulary, the walk, the compiled profile, the refusal and the warning, and the
contract. Validation Pack: docs/developer/validation/FMH-H2-6e.md. Test IDs are H2.6e-Tn."""

from __future__ import annotations

import pytest
from rdflib import RDF, URIRef

from persistence import witness
from persistence.boundary import BY_IDENTITY, PINNED, walk_ownership
from persistence.builders import build
from persistence.compiler import CompileError, compile_targets, compile_to_graph
from lattice_persistence import read_contracts
from persistence.contract import contract_of
from persistence.instantiate import operation_context
from persistence.model import CrossAxisViolation
from persistence.namespaces import DAL

from conftest import EXAMPLES_DIR

EX = "https://example.org/lending#"
SHAPE = URIRef(EX + "OrderAggregateShape")
PREFIXES = f"""
@prefix dal:  <{DAL}> .
@prefix ex:   <{EX}> .
@prefix fnd:  <https://www.nebularis.org/neuro-semantic/lattice/foundation#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix sh:   <http://www.w3.org/ns/shacl#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
"""
BASE = EXAMPLES_DIR / "composite-property-boundary-shacl.ttl"


def _config(extra: str = ""):
    graph = witness._load_fixture(BASE)
    graph.parse(data=PREFIXES + extra, format="turtle")
    return graph


def _edge(path: str, cls: str, mode: str = "", ownership: str = "dal:Reference") -> str:
    return f"ex:OrderAggregateShape sh:property [ sh:path ex:{path} ; sh:class ex:{cls} ; dal:ownership {ownership} {mode} ] ."


def _kind(extra: str) -> str:
    with pytest.raises(CompileError) as caught:
        compile_targets(_config(extra))
    assert isinstance(caught.value.cause, CrossAxisViolation)
    return caught.value.cause.kind


def _warnings(extra: str) -> set[str]:
    (ct,) = compile_targets(_config(extra))
    return {d.kind for d in ct.diagnostics}


def test_h2_6e_t1_the_vocabulary_declares_the_property_and_its_two_individuals():
    spec = witness.SPEC_TTL
    from rdflib import Graph

    g = Graph().parse(spec, format="turtle")
    assert (DAL.referenceMode, RDF.type, URIRef("http://www.w3.org/2002/07/owl#ObjectProperty")) in g
    assert {s for s in g.subjects(RDF.type, DAL.ReferenceMode)} == {DAL.ByIdentity, DAL.Pinned}
    assert list(g.objects(DAL.referenceMode, URIRef("http://www.w3.org/2000/01/rdf-schema#domain"))) == []


def test_h2_6e_t2_an_edge_with_no_mode_is_by_identity_and_a_declared_one_is_read():
    tree = walk_ownership(_config(_edge("referee", "Versioned", "; dal:referenceMode dal:Pinned")), SHAPE)
    modes = {str(e.step.predicate).rsplit("#", 1)[-1]: e.reference_mode for e in tree.node_edges()}
    assert modes["customer"] == BY_IDENTITY and modes["referee"] == PINNED
    assert all(e.reference_mode == BY_IDENTITY for e in walk_ownership(_config(), SHAPE).edges)


def test_h2_6e_t3_the_compiled_profile_records_each_edge_with_its_mode():
    out, _ = compile_to_graph(_config(_edge("referee", "Versioned", "; dal:referenceMode dal:Pinned") + "ex:Versioned rdfs:subClassOf fnd:Versioned ."))
    (profile,) = out.subjects(RDF.type, DAL.CompiledProfile)
    nodes = list(out.objects(profile, DAL.referenceEdge))  # stated once, by the profile, which payload contracts point at (H2.8c)
    assert len(nodes) == 3  # the base's two (an owned edge and a reference) and the pinned one
    assert all(isinstance(n, URIRef) for n in nodes)  # an IRI since H2.8c, so a contract can point at it
    by_predicate = {str(out.value(n, DAL.edgePredicate)).rsplit("#", 1)[-1]: n for n in nodes}
    assert out.value(by_predicate["referee"], DAL.referenceMode) == DAL.Pinned
    assert out.value(by_predicate["referee"], DAL.edgeOwnership) == DAL.Reference
    assert out.value(by_predicate["customer"], DAL.referenceMode) == DAL.ByIdentity
    assert str(out.value(by_predicate["referee"], DAL.edgeTargetClass)) == EX + "Versioned"


def test_h2_6e_t4_a_pinned_edge_to_a_versioned_class_compiles_and_the_mode_does_not_change_what_is_generated():
    pinned = _edge("referee", "Versioned", "; dal:referenceMode dal:Pinned") + "ex:Versioned rdfs:subClassOf fnd:Versioned ."
    identity = _edge("referee", "Versioned") + "ex:Versioned rdfs:subClassOf fnd:Versioned ."
    ops = lambda extra: [(o.operation, o.template_id, [(b.name, b.value) for b in o.bindings]) for o in compile_targets(_config(extra))[0].operations]
    assert ops(pinned) == ops(identity)


def test_h2_6e_t5_a_pinned_edge_to_an_unversioned_class_is_refused():
    assert _kind(_edge("referee", "Unversioned", "; dal:referenceMode dal:Pinned")) == "PinnedReferenceToUnversionedClass"


def test_h2_6e_t6_a_pinned_edge_with_no_target_class_or_on_a_value_property_is_refused():
    no_class = "ex:OrderAggregateShape sh:property [ sh:path ex:x ; dal:ownership dal:Reference ; dal:referenceMode dal:Pinned ] ."
    value = "ex:OrderAggregateShape sh:property [ sh:path ex:y ; sh:datatype xsd:string ; dal:referenceMode dal:Pinned ] ."
    assert _kind(no_class) == "PinnedReferenceToUnversionedClass"
    assert _kind(value) == "PinnedReferenceToUnversionedClass"


def test_h2_6e_t7_a_mode_that_is_neither_individual_is_refused():
    assert _kind(_edge("referee", "Versioned", "; dal:referenceMode ex:Other") + "ex:Versioned rdfs:subClassOf fnd:Versioned .") == "ReferenceModeUnknown"


def test_h2_6e_t8_a_pinned_owned_edge_is_checked_like_any_other():
    owned = "ex:OrderAggregateShape sh:property [ sh:path ex:part ; sh:node ex:PartShape ; dal:ownership dal:Owned ; dal:referenceMode dal:Pinned ] ."
    part = "ex:PartShape a sh:NodeShape ; sh:targetClass ex:Part ."
    assert _kind(owned + part) == "PinnedReferenceToUnversionedClass"
    assert "EvidenceEdgeByIdentity" not in _warnings(owned + part + "ex:Part rdfs:subClassOf fnd:Versioned .")


EVIDENCE = "ex:Order rdfs:subClassOf fnd:Evidence . ex:Customer rdfs:subClassOf fnd:Versioned ."


def test_h2_6e_t9_an_evidence_class_that_refers_by_identity_to_a_versioned_class_is_warned():
    assert "EvidenceEdgeByIdentity" in _warnings(EVIDENCE)
    assert "EvidenceEdgeByIdentity" in _warnings("ex:Order rdfs:subClassOf fnd:DerivedArtefact . ex:Customer rdfs:subClassOf fnd:Versioned .")
    assert "EvidenceEdgeByIdentity" in _warnings("ex:Order rdfs:subClassOf ex:Record . ex:Record rdfs:subClassOf fnd:Evidence . ex:Customer rdfs:subClassOf fnd:Versioned .")


def test_h2_6e_t10_the_warning_is_not_given_when_the_edge_is_pinned_or_a_class_is_not_what_it_needs_to_be():
    pinned = EVIDENCE.replace("ex:Customer", "ex:Referee") + _edge("referee", "Referee", "; dal:referenceMode dal:Pinned")
    assert "EvidenceEdgeByIdentity" not in _warnings(pinned)
    assert "EvidenceEdgeByIdentity" not in _warnings("ex:Customer rdfs:subClassOf fnd:Versioned .")  # the subject is no evidence
    assert "EvidenceEdgeByIdentity" not in _warnings("ex:Order rdfs:subClassOf fnd:Evidence .")  # the target is not versioned
    # the edge to the unversioned customer is by identity and warns nothing, while one to a versioned class does, so the warning is per edge
    both = EVIDENCE + _edge("referee", "Referee", "; dal:referenceMode dal:Pinned") + "ex:Referee rdfs:subClassOf fnd:Versioned ."
    (ct,) = compile_targets(_config(both))
    assert [d.kind for d in ct.diagnostics].count("EvidenceEdgeByIdentity") == 1


def test_h2_6e_t11_the_warning_message_names_the_edge_and_is_a_warning():
    (ct,) = compile_targets(_config(EVIDENCE))
    (d,) = [d for d in ct.diagnostics if d.kind == "EvidenceEdgeByIdentity"]
    assert d.severity == "WARNING" and "customer" in d.message and "dal:Pinned" in d.message


def _payload(extra: str):
    """The payload contract of the first operation that has one, as the caller library reads it, which follows the contract's pointers to the
    profile's edges (H2.8c), the compiled graph, and the ownership tree."""
    graph = _config(extra)
    compiled, targets = compile_to_graph(graph)
    (ct,) = targets
    tree = ct.dimensions["aggregateBoundary"].extra["ownershipTree"]
    (op,) = [o for o in read_contracts(compiled) if o.payload is not None][:1]
    return op.payload, compiled, tree


def test_h2_6e_t12_the_contract_carries_the_edges_modes_on_its_payload():
    payload, _, tree = _payload(_edge("referee", "Versioned", "; dal:referenceMode dal:Pinned") + "ex:Versioned rdfs:subClassOf fnd:Versioned .")
    modes = {e.predicate.rsplit("#", 1)[-1]: e.reference_mode for e in payload.edges}
    assert modes["referee"] == "Pinned" and {m for k, m in modes.items() if k != "referee"} == {"ByIdentity"}
    assert len(payload.edges) == len(tree.node_edges()) and payload.edges == tuple(sorted(payload.edges))


def test_h2_6e_t13_each_edge_is_stated_once_by_the_profile_and_every_payload_contract_points_at_those_edges():
    """Changed in H2.8c (H2.6e (2), the middle ground). The contract derived from an operation copies no edge, and the emitted payload contract
    points at the profile's own `dal:ReferenceEdge` nodes, so each edge's facts are stated once."""
    graph = _config()
    compiled, _ = compile_to_graph(graph)
    (profile,) = compiled.subjects(RDF.type, DAL.CompiledProfile)
    stated = set(compiled.objects(profile, DAL.referenceEdge))
    assert stated and all(isinstance(e, URIRef) for e in stated) and set(compiled.subjects(RDF.type, DAL.ReferenceEdge)) == stated
    pointers = [set(compiled.objects(pc, DAL.referenceEdge)) for pc in compiled.subjects(RDF.type, DAL.PayloadContract)]
    assert pointers and all(p == stated for p in pointers)
    for node in compiled.objects(None, DAL.generatedOperation):
        stem = str(compiled.value(compiled.value(node, DAL.usesTemplate), DAL.templateId))
        c = contract_of(build(stem, operation_context(compiled, node)))
        assert c.payload is None or c.payload.edges == ()


def test_h2_6e_t14_a_family_with_no_boundary_shape_records_no_edge():
    out, _ = compile_to_graph(witness._load_fixture(EXAMPLES_DIR / "baseline-single-class.ttl"))
    assert list(out.subjects(RDF.type, DAL.ReferenceEdge)) == []


# ---- H2.8c: record classes (plan 4.18 step 3, D-15 (b), D-9). Test IDs are H2.8c-Tn ---------------------------------------

RECORD = "ex:OrderBoundaryProfile dal:recordClass ex:Order . ex:Customer rdfs:subClassOf fnd:Versioned ."


def _no_receipt(extra: str = ""):
    graph = _config(extra)
    profile = next(graph.subjects(DAL.receiptModel, None))
    graph.set((profile, DAL.receiptModel, DAL.NoReceipt))
    (ct,) = compile_targets(graph)
    return ct


def test_h2_8c_t8_a_record_class_named_by_a_profile_is_read_as_evidence_by_the_identity_warning():
    assert "EvidenceEdgeByIdentity" in _warnings(RECORD)
    # a subclass of a named record class is a record, as the configuration asserts it
    assert "EvidenceEdgeByIdentity" in _warnings("ex:OrderBoundaryProfile dal:recordClass ex:Record . ex:Order rdfs:subClassOf ex:Record . ex:Customer rdfs:subClassOf fnd:Versioned .")
    # the control: the same edge with no record class, and a record class whose edge is pinned
    assert "EvidenceEdgeByIdentity" not in _warnings("ex:Customer rdfs:subClassOf fnd:Versioned .")
    pinned = "ex:OrderBoundaryProfile dal:recordClass ex:Order . ex:Referee rdfs:subClassOf fnd:Versioned ." + _edge("referee", "Referee", "; dal:referenceMode dal:Pinned")
    assert "EvidenceEdgeByIdentity" not in _warnings(pinned)


def test_h2_8c_t9_no_receipt_on_a_family_whose_target_is_a_record_class_or_versioned_warns_and_otherwise_does_not():
    assert "NoReceiptForRecord" in {d.kind for d in _no_receipt("ex:OrderBoundaryProfile dal:recordClass ex:Order .").diagnostics}
    assert "NoReceiptForRecord" in {d.kind for d in _no_receipt("ex:Order rdfs:subClassOf fnd:Versioned .").diagnostics}
    plain = _no_receipt()
    assert "NoReceiptForRecord" not in {d.kind for d in plain.diagnostics}
    (d,) = [d for d in _no_receipt("ex:OrderBoundaryProfile dal:recordClass ex:Order .").diagnostics if d.kind == "NoReceiptForRecord"]
    assert d.severity == "WARNING" and "dal:recordClass" in d.message


def test_h2_8c_t10_the_profile_states_the_record_classes_the_family_touches_and_the_library_reads_them():
    from lattice_persistence import read_contracts

    compiled, _ = compile_to_graph(_config(RECORD + "ex:OrderBoundaryProfile dal:recordClass ex:Unrelated ."))
    (profile,) = compiled.subjects(RDF.type, DAL.CompiledProfile)
    assert set(compiled.objects(profile, DAL.recordClass)) == {URIRef(EX + "Order")}  # ex:Unrelated is touched by no edge of this family
    payloads = [o.payload for o in read_contracts(compiled) if o.payload is not None]
    assert payloads and all(p.record_classes == (EX + "Order",) for p in payloads)
    plain, _ = compile_to_graph(_config())
    assert list(plain.objects(None, DAL.recordClass)) == []


def test_h2_8c_t11_the_vocabulary_declares_record_class_with_no_domain():
    from rdflib import Graph

    g = Graph().parse(witness.SPEC_TTL, format="turtle")
    assert (DAL.recordClass, RDF.type, URIRef("http://www.w3.org/2002/07/owl#ObjectProperty")) in g
    assert list(g.objects(DAL.recordClass, URIRef("http://www.w3.org/2000/01/rdf-schema#domain"))) == []
