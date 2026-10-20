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
from persistence.contract import contract_of, edge_contracts
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
    out, _ = compile_to_graph(_config(_edge("referee", "Versioned", "; dal:referenceMode dal:Pinned") + "ex:Versioned rdfs:subClassOf fnd:Version ."))
    nodes = list(out.subjects(RDF.type, DAL.ReferenceEdge))
    assert len(nodes) == len(list(out.objects(None, DAL.referenceEdge))) == 3  # the base's two (an owned edge and a reference) and the pinned one
    by_predicate = {str(out.value(n, DAL.edgePredicate)).rsplit("#", 1)[-1]: n for n in nodes}
    assert out.value(by_predicate["referee"], DAL.referenceMode) == DAL.Pinned
    assert out.value(by_predicate["referee"], DAL.edgeOwnership) == DAL.Reference
    assert out.value(by_predicate["customer"], DAL.referenceMode) == DAL.ByIdentity
    assert str(out.value(by_predicate["referee"], DAL.edgeTargetClass)) == EX + "Versioned"


def test_h2_6e_t4_a_pinned_edge_to_a_versioned_class_compiles_and_the_mode_does_not_change_what_is_generated():
    pinned = _edge("referee", "Versioned", "; dal:referenceMode dal:Pinned") + "ex:Versioned rdfs:subClassOf fnd:Version ."
    identity = _edge("referee", "Versioned") + "ex:Versioned rdfs:subClassOf fnd:Version ."
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
    assert _kind(_edge("referee", "Versioned", "; dal:referenceMode ex:Other") + "ex:Versioned rdfs:subClassOf fnd:Version .") == "ReferenceModeUnknown"


def test_h2_6e_t8_a_pinned_owned_edge_is_checked_like_any_other():
    owned = "ex:OrderAggregateShape sh:property [ sh:path ex:part ; sh:node ex:PartShape ; dal:ownership dal:Owned ; dal:referenceMode dal:Pinned ] ."
    part = "ex:PartShape a sh:NodeShape ; sh:targetClass ex:Part ."
    assert _kind(owned + part) == "PinnedReferenceToUnversionedClass"
    assert "EvidenceEdgeByIdentity" not in _warnings(owned + part + "ex:Part rdfs:subClassOf fnd:Version .")


EVIDENCE = "ex:Order rdfs:subClassOf fnd:Evidence . ex:Customer rdfs:subClassOf fnd:Version ."


def test_h2_6e_t9_an_evidence_class_that_refers_by_identity_to_a_versioned_class_is_warned():
    assert "EvidenceEdgeByIdentity" in _warnings(EVIDENCE)
    assert "EvidenceEdgeByIdentity" in _warnings("ex:Order rdfs:subClassOf fnd:DerivedArtefact . ex:Customer rdfs:subClassOf fnd:Version .")
    assert "EvidenceEdgeByIdentity" in _warnings("ex:Order rdfs:subClassOf ex:Record . ex:Record rdfs:subClassOf fnd:Evidence . ex:Customer rdfs:subClassOf fnd:Version .")


def test_h2_6e_t10_the_warning_is_not_given_when_the_edge_is_pinned_or_a_class_is_not_what_it_needs_to_be():
    pinned = EVIDENCE.replace("ex:Customer", "ex:Referee") + _edge("referee", "Referee", "; dal:referenceMode dal:Pinned")
    assert "EvidenceEdgeByIdentity" not in _warnings(pinned)
    assert "EvidenceEdgeByIdentity" not in _warnings("ex:Customer rdfs:subClassOf fnd:Version .")  # the subject is no evidence
    assert "EvidenceEdgeByIdentity" not in _warnings("ex:Order rdfs:subClassOf fnd:Evidence .")  # the target is not versioned
    # the edge to the unversioned customer is by identity and warns nothing, while one to a versioned class does, so the warning is per edge
    both = EVIDENCE + _edge("referee", "Referee", "; dal:referenceMode dal:Pinned") + "ex:Referee rdfs:subClassOf fnd:Version ."
    (ct,) = compile_targets(_config(both))
    assert [d.kind for d in ct.diagnostics].count("EvidenceEdgeByIdentity") == 1


def test_h2_6e_t11_the_warning_message_names_the_edge_and_is_a_warning():
    (ct,) = compile_targets(_config(EVIDENCE))
    (d,) = [d for d in ct.diagnostics if d.kind == "EvidenceEdgeByIdentity"]
    assert d.severity == "WARNING" and "customer" in d.message and "dal:Pinned" in d.message


def _payload(extra: str):
    graph = _config(extra)
    compiled, targets = compile_to_graph(graph)
    (ct,) = targets
    tree = ct.dimensions["aggregateBoundary"].extra["ownershipTree"]
    node = next(compiled.objects(None, DAL.generatedOperation))
    operation = build(str(compiled.value(compiled.value(node, DAL.usesTemplate), DAL.templateId)).removesuffix(".mustache"), operation_context(compiled, node))
    return contract_of(operation, edge_contracts(tree)), tree


def test_h2_6e_t12_the_contract_carries_the_edges_modes_on_its_payload():
    contract, tree = _payload(_edge("referee", "Versioned", "; dal:referenceMode dal:Pinned") + "ex:Versioned rdfs:subClassOf fnd:Version .")
    modes = {e.predicate.rsplit("#", 1)[-1]: e.reference_mode for e in contract.payload.edges}
    assert modes["referee"] == "Pinned" and {m for k, m in modes.items() if k != "referee"} == {"ByIdentity"}
    assert len(contract.payload.edges) == len(tree.node_edges()) and contract.payload.edges == tuple(sorted(contract.payload.edges))


def test_h2_6e_t13_a_contract_given_no_edges_has_none_and_an_operation_with_no_payload_carries_none():
    graph = _config()
    compiled, _ = compile_to_graph(graph)
    for node in compiled.objects(None, DAL.generatedOperation):
        stem = str(compiled.value(compiled.value(node, DAL.usesTemplate), DAL.templateId)).removesuffix(".mustache")
        c = contract_of(build(stem, operation_context(compiled, node)))
        assert c.payload is None or c.payload.edges == ()


def test_h2_6e_t14_a_family_with_no_boundary_shape_records_no_edge():
    out, _ = compile_to_graph(witness._load_fixture(EXAMPLES_DIR / "baseline-single-class.ttl"))
    assert list(out.subjects(RDF.type, DAL.ReferenceEdge)) == []
