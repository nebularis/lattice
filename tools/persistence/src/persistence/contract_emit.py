# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The contract of every generated operation, as the triples of a compiled profile (formal-methods track H, slice H2.7).

:func:`persistence.contract.contract_of` derives what a caller, a relational realisation and a model checker need to know about an
operation. This module writes it into the profile, under two rules (design review 2.6) that the shapes of
``ontology/persistence/shapes/constraints.ttl`` enforce:

* no blank node. Every declaration node has an IRI derived from the target, the deployment, the operation and the part
  (:func:`mint`), so two compiles give the same IRIs and a reviewer can read a diff,
* no SPARQL text in any value. Kinds, modes and resources are individuals of ``persistence/spec/persistence.ttl``, a caller-named
  graph's rule refers to the family's ``dal:graphIriTemplate`` and never repeats it, and the owned path stays in the ``ownedPath``
  binding.
"""

from __future__ import annotations

import re
from urllib.parse import quote

from rdflib import RDF, Graph, Literal, URIRef
from rdflib.namespace import XSD

from .builders import BUILDERS, build
from .contract import HAND_DECLARED, OperationContract, OperationKind, contract_of
from .instantiate import operation_context
from .landing import Place
from .namespaces import DAL



AUDIT_OUTCOMES = ("Clean", "Failed", "NothingExamined")
"""What an audit can report (H2.8b, ADR-A123 addendum). A query returns the rows that violate, so a caller derives the outcome from them."""


def mint(target: URIRef, operation: str, part: str, deployment: URIRef | None = None) -> URIRef:
    """The IRI of a declaration node, derived from the target, the deployment where there is one, the operation's name and the part,
    and never from an order. Two deployments of one class each get their own declarations."""
    base = str(target).replace("#", "/")
    if deployment is not None:
        base += "/" + re.sub(r"[^A-Za-z0-9._-]+", "-", str(deployment).rsplit("#", 1)[-1].rstrip("/").rsplit("/", 1)[-1])
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", operation).strip("-")
    return URIRef(f"{base}/compiled/{slug}#{part}")


PROFILE_PART = "profile"
"""The segment under which a profile's own declarations are minted, in place of an operation's name. No generated operation has this name."""


def mint_edge(target: URIRef, index: int, deployment: URIRef | None = None) -> URIRef:
    """The IRI of the profile's ``index``-th ``dal:ReferenceEdge``, in the order of :func:`persistence.contract.edge_contracts`. The payload
    contract of each operation points at these nodes and never restates them (H2.8c, H2.6e (2))."""
    return mint(target, PROFILE_PART, f"edge-{index:02d}", deployment)


def mint_place(target: URIRef, place: Place, deployment: URIRef | None = None) -> URIRef:
    """The IRI of the ``dal:GraphPlace`` of ``place`` in the profile of ``target``, from its role and its graph or template, percent-encoded. A
    profile states each distinct place once, and every access that lands there points at it. The compiled profile itself is a blank node,
    so a place is minted as the profile's other declarations are."""
    return mint(target, PROFILE_PART, f"place-{place.role}-{quote(place.text, safe='')}", deployment)


GRAPH_ROLES = {
    "data": "DataRole", "meta": "MetaRole", "txn": "TxnRole", "log": "LogRole", "event": "EventRole", "keys": "KeysRole",
    "quarantine": "QuarantineRole", "retention": "RetentionRole", "pinned": "PinnedRole", "dataset": "DatasetRole", "patch": "PatchRole",
}
"""The ``dal:GraphRole`` individual of each `persistence.ir.GraphRole` value. The IR's ``derived`` role is the surface compiler's and has none."""


def emit_place(g: Graph, node: URIRef, place: Place) -> None:
    """The role of ``place`` and its graph or template, on ``node``."""
    g.add((node, RDF.type, DAL.GraphPlace))
    g.add((node, DAL.inGraphRole, DAL[GRAPH_ROLES[place.role]]))
    if place.graph:
        g.add((node, DAL.inGraph, URIRef(place.graph)))
    else:
        g.add((node, DAL.inGraphNamed, Literal(place.named)))


def is_declaration(node) -> bool:
    return isinstance(node, URIRef) and "/compiled/" in str(node)


def kind_name(kind: str) -> str:
    return f"{kind}Kind"


def column_name(kind: str) -> str:
    return f"{kind}Column"


def contract_for(compiled: Graph, node, *, guards: bool, graph_names: str, shape: URIRef | None = None) -> OperationContract | None:
    """The contract of the operation ``node`` of ``compiled``, from its builder, or from the hand declarations of operations that have
    none. ``None`` when there is neither."""
    stem = str(compiled.value(compiled.value(node, DAL.usesTemplate), DAL.templateId))
    if stem in BUILDERS:
        return contract_of(build(stem, operation_context(compiled, node), guards=guards, graph_names=graph_names), None if shape is None else str(shape))
    return HAND_DECLARED.get(stem)


def emit_contract(
    g: Graph, node, target_iri: URIRef, name: str, c: OperationContract, shape: URIRef | None, deployment: URIRef | None = None,
    edges: tuple = (), constraint: URIRef | None = None,
) -> None:
    """Add the contract ``c`` of the generated operation ``node`` to ``g``. ``edges`` are the profile's ``dal:ReferenceEdge`` nodes
    (:func:`mint_edge`), which a payload contract points at. ``constraint`` is the ``dal:UniquenessConstraint`` the operation serves, which
    each of its key claim accesses names."""

    def m(part: str) -> URIRef:
        return mint(target_iri, name, part, deployment)

    g.add((node, DAL.operationKind, DAL[c.kind.value]))
    g.add((node, DAL.templateVersion, Literal(c.version, datatype=XSD.integer)))
    g.add((node, DAL.guardStatus, DAL[c.guard_status.value]))
    if c.graph_naming is not None:
        g.add((node, DAL.graphNaming, DAL[c.graph_naming.value]))
    g.add((node, DAL.declarationSource, DAL[c.source.value]))
    for p in c.parameters:
        pn = m(f"param-{p.name}")
        g.add((node, DAL.parameter, pn))
        g.add((pn, RDF.type, DAL.ParameterDeclaration))
        g.add((pn, DAL.parameterName, Literal(p.name)))
        g.add((pn, DAL.parameterKind, DAL[kind_name(p.kind)]))
        g.add((pn, DAL.required, Literal(p.required)))
        if p.equals_graph_name:
            g.add((pn, DAL.mustEqual, DAL.GraphNameOfRoot))
            g.add((pn, DAL.mustEqualFor, m("param-root")))
        if p.sourced_from_registry:
            g.add((pn, DAL.sourcedFrom, DAL.RegistryGraph))
    for i, a in enumerate(c.accesses, 1):
        an = m(f"access-{i}")
        g.add((node, DAL.access, an))
        g.add((an, RDF.type, DAL.ResourceAccess))
        g.add((an, DAL.resourceKind, DAL[a.resource]))
        g.add((an, DAL.accessMode, DAL[a.mode]))
        if a.keyed_by:
            g.add((an, DAL.keyedBy, m(f"param-{a.keyed_by}")))
        if a.place is not None:
            place_node = mint_place(target_iri, a.place, deployment)
            emit_place(g, place_node, a.place)
            g.add((an, DAL.landsIn, place_node))
        if a.direction is not None:
            g.add((an, DAL.patchDirection, DAL[a.direction]))
        if constraint is not None and a.resource == "KeyClaim":
            g.add((an, DAL.forConstraint, constraint))
    for i, col in enumerate(c.results, 1):
        cn = m(f"result-{col.name}")
        g.add((node, DAL.resultColumn, cn))
        g.add((cn, RDF.type, DAL.ResultColumn))
        g.add((cn, DAL.columnName, Literal(col.name)))
        g.add((cn, DAL.columnPosition, Literal(i, datatype=XSD.integer)))
        g.add((cn, DAL.columnKind, DAL[column_name(col.kind)]))
        if col.separator is not None:
            g.add((cn, DAL.columnSeparator, Literal(col.separator)))
    if c.kind is OperationKind.AUDIT:
        for outcome in AUDIT_OUTCOMES:
            g.add((node, DAL.reportsOutcome, DAL[outcome]))
        if c.examines:
            g.add((node, DAL.examinedParameter, m(f"param-{c.examines}")))
    if c.payload is not None:
        pc = m("payload")
        g.add((node, DAL.payloadContract, pc))
        g.add((pc, RDF.type, DAL.PayloadContract))
        g.add((pc, DAL.payloadParameter, m(f"param-{c.payload.parameter}")))
        if c.payload.root:
            g.add((pc, DAL.payloadRoot, m(f"param-{c.payload.root}")))
        g.add((pc, DAL.payloadEncoding, DAL[c.payload.encoding]))
        g.add((pc, DAL.boundaryShape, shape if shape is not None else DAL.NoBoundaryShape))
        for edge in edges:
            g.add((pc, DAL.referenceEdge, edge))
    if c.digest is not None:
        dc = m("digest")
        g.add((node, DAL.digestContract, dc))
        g.add((dc, RDF.type, DAL.DigestContract))
        g.add((dc, DAL.digestAlgorithm, Literal("SHA-256")))
        parts = c.digest.parts()
        for i, (role, sources) in enumerate(parts, 1):
            dp = m(f"digest-part-{i}")
            g.add((dc, DAL.digestPart, dp))
            g.add((dp, RDF.type, DAL.DigestPart))
            g.add((dp, DAL.partOrder, Literal(i, datatype=XSD.integer)))
            g.add((dp, DAL.partRole, DAL[role]))
            if sources:
                for source in sources:
                    g.add((dp, DAL.partSource, m(f"param-{source}")))
            else:
                g.add((dp, DAL.partSource, DAL.NoSource))


def add_edge_facts(out: Graph, node, edge) -> None:
    """What the compiled profile and the contract both say of one edge: where it leaves, its step, its ownership, the class it leads to
    and its reference mode."""
    out.add((node, DAL.edgeSource, URIRef(edge.source_shape)))
    out.add((node, DAL.edgePredicate, URIRef(edge.predicate)))
    out.add((node, DAL.edgeInverse, Literal(edge.inverse)))
    out.add((node, DAL.edgeOwnership, DAL[edge.ownership]))
    if edge.target_class is not None:
        out.add((node, DAL.edgeTargetClass, URIRef(edge.target_class)))
    if edge.target_shape is not None:
        out.add((node, DAL.edgeTargetShape, URIRef(edge.target_shape)))
    out.add((node, DAL.referenceMode, DAL[edge.reference_mode]))


__all__ = ["PROFILE_PART", "GRAPH_ROLES", "mint", "mint_edge", "mint_place", "emit_place", "is_declaration", "kind_name", "column_name", "contract_for", "emit_contract", "add_edge_facts"]
