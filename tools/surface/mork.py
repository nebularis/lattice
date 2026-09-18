# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
MORK interoperation.

Surface and MORK meet at one place and only one: MORK may *propose* that a
relationship is worth restating locally, and it may *record* that a restatement
happened. It never generates symbols. Symbol generation sits entirely
downstream of MORK's validation gate and is fully deterministic, which is the
strongest row in MORK's own non-LLM degradation table.

Two directions are supported here.

**Lowering** takes a ``mrk:ProjectionMapping`` — the fourth sibling in MORK's
``GenerativeMapping`` family, alongside ShapeMapping, RuleMapping and
TransformMapping — and writes the equivalent ``srf:`` contract declaration.
This is the path a proposed mapping takes to become a governed contract: it is
authored in MORK, validated at MORK's gate, and lowered into the substrate,
where it is a semantic declaration in its own right and remains usable without
MORK at all (ADR-A15).

**Lifting** takes a compiled surface and writes the ``mrk:ProjectionMapping``
record that accounts for it, so that a generated class traces back through a
mapping, to an intent, to the source text — MORK's provenance compositionality
claim applied to generated symbols.

Where the profile declares ``srf:WrappedSymbols``, the lifted record wraps each
generated class in an ``mrk:OwlClass`` individual linked by ``owl:sameAs``,
which is the convention MORK already uses for environments that reject an
individual and a class sharing an IRI. Under ``srf:PunnedSymbols`` the class
IRI is referenced directly.

The ``mrk:ProjectionMapping`` vocabulary used here is declared in
``mork/spec/Mork.ttl``.

**Relationship to ``tools/surface/lowering.py``.** That module lowers a bare
declaration — a ``srf:ProjectionContract`` always, a Promotion/Index contract
where configured (ADR-A18) — with no compiled surface involved. ``lift``
below is the compiled-surface case: it reuses the same parameter-binding
shape (``lowering.contract_parameter_bindings``) so a mapping produced either
way looks the same to ``lower()``, but mints its ``mrk:ProjectionMapping``
record under a different IRI stem, so the two never collide over one
contract key.
"""

from __future__ import annotations

from typing import Dict, Optional

from rdflib import Graph, Literal, URIRef

from .compile import CLOSURE, DIRECT, MEMBERSHIP, NOMINAL, CompiledSurface
from .lowering import contract_parameter_bindings
from .model import Contract, ContractError
from .namespaces import DCTERMS, MORK, OWL, RDF, RDFS, SH, SRF, XSD
from .naming import Minter, local_name

PROJECTION_MAPPING = MORK.ProjectionMapping
GENERATES_CLASS_DEFINITION = MORK.generatesClassDefinition
PROJECTION_PROVENANCE = MORK.ProjectionProvenance
HAS_PROJECTION_PROVENANCE = MORK.hasProjectionProvenance


# ---------------------------------------------------------------------------
# Lifting: compiled surface -> MORK mapping record
# ---------------------------------------------------------------------------


def _parameter(graph: Graph, node: URIRef, name: str, kind: str, value) -> None:
    graph.add((node, RDF.type, MORK.ParameterBinding))
    graph.add((node, MORK.paramName, Literal(name)))
    graph.add((node, MORK.paramType, Literal(kind)))
    graph.add((node, MORK.paramValue, value))


def lift(compiled: CompiledSurface, mapping_scheme: Optional[URIRef] = None) -> Graph:
    """Write the ``mrk:ProjectionMapping`` record accounting for a compiled surface."""
    contract = compiled.contract
    minter = Minter(
        target_namespace=contract.target_namespace,
        contract_key=contract.key,
        carrier=str(contract.carrier),
        normalisation=contract.profile.naming_normalisation,
        naming_policy=contract.naming_policy or "",
        naming_prefix=contract.naming_prefix,
    )

    graph = Graph()
    graph.bind("mork", MORK)
    graph.bind("srf", SRF)
    graph.bind("sh", SH)

    mapping = minter.projection_mapping()
    graph.add((mapping, RDF.type, PROJECTION_MAPPING))
    graph.add((mapping, RDF.type, MORK.DataMapping))
    if mapping_scheme is not None:
        graph.add((mapping, MORK.mappingScheme, mapping_scheme))
    graph.add((mapping, MORK.mappingFor, contract.iri))
    graph.add(
        (
            mapping,
            MORK.mappingNote,
            Literal(
                f"Projection of {contract.carrier} over the read path declared by "
                f"{contract.iri}. Compiled, not proposed: the symbols below were produced "
                f"deterministically from the contract's read set."
            ),
        )
    )

    # Targeting: the carrier is the target class, which is exactly what
    # sh:targetClass means in MORK's existing TargetingSpec.
    target = minter.targeting_spec()
    graph.add((mapping, MORK.hasTargetingSpec, target))
    graph.add((target, RDF.type, MORK.TargetingSpec))
    graph.add((target, SH.targetClass, contract.carrier))

    # Parameters: everything the compiler read out of the contract. Shared
    # with tools/surface/lowering.py::lower_contract, so a mapping produced
    # either way has the same parameter shape and tools/surface/mork.py's own
    # lower() below can read either back.
    for name, kind, value in contract_parameter_bindings(contract):
        node = minter.parameter_binding(name)
        graph.add((mapping, MORK.hasParameterBinding, node))
        _parameter(graph, node, name, kind, value)

    # Generated classes, wrapped or punned according to the profile.
    punned = contract.profile.punned
    for symbol in compiled.symbols:
        if symbol.form != NOMINAL:
            continue
        if punned:
            graph.add((mapping, GENERATES_CLASS_DEFINITION, symbol.term))
            graph.add((symbol.term, RDF.type, MORK.OwlClass))
        else:
            wrapper = URIRef(f"{symbol.term}_owlclass")
            graph.add((mapping, GENERATES_CLASS_DEFINITION, wrapper))
            graph.add((wrapper, RDF.type, MORK.OwlClass))
            graph.add((wrapper, OWL.sameAs, symbol.term))
            graph.add((wrapper, RDFS.seeAlso, symbol.term))
            graph.add((wrapper, MORK.conceptName, Literal(local_name(str(symbol.term)))))
            graph.add((wrapper, MORK.iri, Literal(str(symbol.term), datatype=XSD.anyURI)))

    # Provenance: the surface record is the detail; this is the MORK-side handle.
    provenance = minter.projection_provenance()
    graph.add((mapping, HAS_PROJECTION_PROVENANCE, provenance))
    graph.add((provenance, RDF.type, PROJECTION_PROVENANCE))
    if compiled.produced_at:
        graph.add(
            (
                provenance,
                MORK.provenanceCreated,
                Literal(compiled.produced_at, datatype=XSD.dateTime),
            )
        )
    graph.add((provenance, SRF.coversContract, contract.iri))
    graph.add((provenance, SRF.generatedByProfile, contract.profile.iri))
    graph.add((provenance, SRF.derivationAuthority, compiled.authority))
    graph.add((provenance, SRF.signatureScope, compiled.signature_scope))
    graph.add((provenance, SRF.artefactHash, Literal(compiled.artefact_hash)))
    graph.add((provenance, SRF.semanticContentHash, Literal(compiled.semantic_hash)))
    graph.add((provenance, RDFS.seeAlso, compiled.record))
    graph.add(
        (
            provenance,
            MORK.reviewStatus,
            Literal("APPROVED" if not contract.lossy else "DRAFT"),
        )
    )
    return graph


# ---------------------------------------------------------------------------
# Lowering: MORK mapping -> surface contract declaration
# ---------------------------------------------------------------------------


def _parameters(graph: Graph, mapping: URIRef) -> Dict[str, object]:
    found: Dict[str, object] = {}
    for node in graph.objects(mapping, MORK.hasParameterBinding):
        name = graph.value(node, MORK.paramName)
        value = graph.value(node, MORK.paramValue)
        if name is not None:
            found[str(name)] = value
    return found


def lower(graph: Graph, mapping: URIRef, contract_iri: URIRef, profile: URIRef) -> Graph:
    """Write the ``srf:`` contract declaration a projection mapping stands for.

    The lowered contract is an authored declaration from that point on: it is
    governed, versioned, and evaluable without MORK. The mapping remains as the
    record of where it came from.
    """
    params = _parameters(graph, mapping)
    target = graph.value(mapping, MORK.hasTargetingSpec)
    carrier = graph.value(target, SH.targetClass) if target is not None else None
    if carrier is None:
        carrier = params.get("carrier")
    if carrier is None:
        raise ContractError(f"{mapping} names no carrier, by targeting spec or parameter")

    out = Graph()
    out.bind("srf", SRF)

    forms = [
        URIRef(str(value))
        for name, value in params.items()
        if name.startswith("indexForm_") and value is not None
    ]
    is_index = bool(forms)

    out.add((contract_iri, RDF.type, SRF.IndexContract if is_index else SRF.PromotionContract))
    out.add((contract_iri, SRF.carrier, carrier))
    out.add((contract_iri, SRF.surfaceProfile, profile))
    out.add((contract_iri, SRF.contractKey, Literal(local_name(str(contract_iri)))))
    if "targetNamespace" in params:
        out.add(
            (
                contract_iri,
                SRF.targetNamespace,
                Literal(str(params["targetNamespace"]), datatype=XSD.anyURI),
            )
        )
    if "realisationMode" in params:
        out.add((contract_iri, SRF.realisationMode, URIRef(str(params["realisationMode"]))))

    # Read path. A single-hop path lowers to srf:readProperty; anything longer
    # lowers to indexed steps, because the step list is what hashes.
    raw_path = str(params.get("readPath", "")).strip()
    segments = [segment.strip() for segment in raw_path.split(" / ") if segment.strip()]
    if len(segments) == 1 and not segments[0].startswith("^"):
        out.add((contract_iri, SRF.readProperty, URIRef(segments[0])))
    else:
        for index, segment in enumerate(segments):
            inverse = segment.startswith("^")
            step = URIRef(f"{contract_iri}_step_{index}")
            out.add((contract_iri, SRF.hasPathStep, step))
            out.add((step, RDF.type, SRF.PathStep))
            out.add((step, SRF.stepIndex, Literal(index, datatype=XSD.nonNegativeInteger)))
            out.add((step, SRF.stepProperty, URIRef(segment.lstrip("^"))))
            out.add((step, SRF.stepDirection, SRF.Inverse if inverse else SRF.Forward))

    if is_index:
        for form in forms:
            out.add((contract_iri, SRF.indexForm, form))
        if "namingPolicy" in params:
            out.add((contract_iri, SRF.namingPolicy, URIRef(str(params["namingPolicy"]))))
        if "closureBasis" in params:
            out.add((contract_iri, SRF.closureBasis, URIRef(str(params["closureBasis"]))))
    else:
        if "promotesTo" in params:
            out.add((contract_iri, SRF.promotesTo, URIRef(str(params["promotesTo"]))))
        if "sourceFidelity" in params:
            out.add((contract_iri, SRF.sourceFidelity, URIRef(str(params["sourceFidelity"]))))
        if "viaMatchRelation" in params:
            out.add(
                (contract_iri, SRF.viaMatchRelation, URIRef(str(params["viaMatchRelation"])))
            )
    return out
