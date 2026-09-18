# src/spc/encoder/refinement_encoder.py
"""Encode refinement predicates as RDF individuals."""

from __future__ import annotations
from rdflib import Graph, URIRef, Literal, RDF
from spc.processle import ast_nodes as ast
from spc.util.namespaces import SPC
from spc.util.iri import mint_ext_iri


def encode_refinement(
    graph: Graph,
    protocol_name: str,
    refinement: ast.Refinement,
    path: list[str],
) -> URIRef:
    """Encode a refinement predicate and return its IRI."""

    if isinstance(refinement, ast.ConceptMembership):
        iri = mint_ext_iri(protocol_name, "refinement", *path)
        graph.add((iri, RDF.type, SPC.ConceptMembershipPredicate))
        # Parse the concept IRI (prefix:local format)
        concept_iri = _resolve_concept_iri(refinement.concept_iri)
        graph.add((iri, SPC.hasTargetConcept, concept_iri))
        return iri

    elif isinstance(refinement, ast.RoleAssertion):
        iri = mint_ext_iri(protocol_name, "refinement", *path, "role")
        graph.add((iri, RDF.type, SPC.RoleAssertionPredicate))
        role_iri = _resolve_concept_iri(refinement.role_iri)
        graph.add((iri, SPC.hasTargetRole, role_iri))
        return iri

    elif isinstance(refinement, ast.ConjunctionRef):
        iri = mint_ext_iri(protocol_name, "refinement", *path, "conj")
        graph.add((iri, RDF.type, SPC.ConjunctionPredicate))
        left_iri = encode_refinement(
            graph, protocol_name, refinement.left, path + ["left"])
        right_iri = encode_refinement(
            graph, protocol_name, refinement.right, path + ["right"])
        graph.add((iri, SPC.hasLeftPredicate, left_iri))
        graph.add((iri, SPC.hasRightPredicate, right_iri))
        return iri

    else:
        raise ValueError(f"Unknown refinement: {type(refinement).__name__}")


def _resolve_concept_iri(prefixed: str) -> URIRef:
    """Resolve a prefixed IRI like 'ins:ValidQuote' to a full URI."""
    from spc.util.namespaces import INS  # Default domain namespace
    if ":" in prefixed:
        prefix, local = prefixed.split(":", 1)
        # Map known prefixes. In production, this would use
        # the namespace bindings from the ontology imports.
        prefix_map = {
            "ins": str(INS),
            "spc": str(SPC),
        }
        base = prefix_map.get(prefix, f"http://example.org/{prefix}#")
        return URIRef(f"{base}{local}")
    return URIRef(prefixed)