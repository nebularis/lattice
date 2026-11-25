# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
Surface-to-MORK lowering (ADR-A18).

A ``srf:ProjectionContract`` declares mapping intent; it never emits SPARQL,
SHACL, SWRL, or anything else directly (ADR-A17). Lowering takes the contract
and writes the MORK mapping graph a downstream compiler family (ADR-A19,
ADR-A23) reads to produce an executable artefact. Promotion and Index have
their own working direct-emit path (``compile.py``) and keep it as their
default (ADR-A16); ``lower_contract`` below exists for the *configured* case
where a deployment also wants a Promotion or Index contract mirrored into
MORK's mapping graph — delivery-plan Phase 3 item 2 — and is never invoked
automatically.

This is deliberately not the same code path as ``tools/surface/mork.py``'s
``lift``/``lower`` pair. Those functions handle a MORK ``mrk:ProjectionMapping``
in its original sense — a proposal to generate a lookup-surface class
definition, either lifted from an already-*compiled* Promotion/Index surface
or lowered from MORK into a Promotion/Index contract declaration. What this
module lowers runs in the *opposite* direction and, for ``lower_projection``,
on a *different* contract kind: a declared contract in, a MORK mapping graph
out, with no compiled surface in between. The two mechanisms mint distinct
IRI stems for exactly this reason (``Minter.lowered_mapping`` versus
``Minter.projection_mapping``), so a deployment that runs both over one
contract key never collides. The parameter-binding shape for Promotion and
Index, however, is intentionally identical between the two — see
``contract_parameter_bindings`` — so that ``tools/surface/mork.py``'s existing
``lower()`` can read a mapping either mechanism produced.

**What this stage does not decide.** MORK's ``ShapeMapping``, ``RuleMapping``,
``TransformMapping``, and ``ProjectionMapping`` are each defined as the base
``mrk:DataMapping`` plus the presence of a specific generated artefact
property (``generatesShapeDefinition``, ``generatesRuleDefinition``,
``generatesTransformDefinition``, ``generatesClassDefinition`` respectively) —
see ``ontology/mork/spec/Mork.ttl``. None of those exist yet at lowering time: nothing
has compiled the mapping into an artefact. So every mapping this module emits
is a bare ``mork:DataMapping``, not yet classified into any
``GenerativeMapping`` subtype; classification follows naturally, by
entailment, once a Phase 5 backend compiler (ADR-A23) attaches the artefact it
produced. ``hasTargetingSpec``, ``hasParameterBinding``, and
``dependsOnMapping`` all declare ``rdfs:domain :GenerativeMapping`` in
``ontology/mork/spec/Mork.ttl``, so asserting any of them (as this module and the
pre-existing ``mork.py::lift`` both already do) already entails
``rdf:type mork:GenerativeMapping`` under RDFS domain semantics — an untyped,
not-yet-specific member of that class, which is the honest state of a mapping
before a backend has compiled it into anything.

**A derivation lowers into a scheme.** A derivation projection states its operation as an expression (``srf:P6``),
so its lowering is more than a record of intent. ``lower_projection`` writes a ``mork:MappingScheme`` with a root datum
that iterates the carrier class and takes the source node as its identity (``mork:SourceNodeIdentity``, so no node is
minted or typed), a typed reference for each evidence role the expression reads, and an assertion of the result
property whose value is the expression, carried across node by node into MORK's typed value expressions. The root also
holds what the bare lowering below holds, the targeting spec and a parameter binding for every role binding and
backend-policy field, so nothing the contract declared is lost. The contract names what it lowered into with ``srf:producesMapping``, for a scheme and for a bare mapping alike, and no note carries its IRI. Nothing here compiles the scheme.

**A graph construction lowers into a scheme too.** It states the node it writes on its result-target binding
(``srf:P10`` to ``srf:P13``), so ``lower_projection`` writes a scheme whose root takes the source node as its identity,
beneath it a contextual datum that mints and types the constructed node, is glued to the instance by the link, and is
guarded by every required-evidence binding, and beneath that an assertion for each value the node writes
(``_lower_construction``).

**A join lowers into a scheme too.** It states the relation on its result-target binding (``srf:P14`` to ``srf:P17``), so
``lower_projection`` writes a scheme whose root takes the source node as its identity, and beneath it a datum that takes
the second carrier's node from the source as its own, states each equality of values as a condition with the comparison
of its pair, how many nodes a value may name, how many links an instance may have, and how an instance with no match is
reported, and is glued to the instance by the link
(``_lower_join``). It is guarded by every required-evidence binding of the contract's own carrier, and writes the link and
nothing else.

**An expansion lowers into a scheme too.** It states the members it restates on its result-target binding (``srf:P18`` to
``srf:P20``), as a SHACL property path from the instance, or as one of two named sources the lowering writes as their paths,
a list's members and a property's transitive closure. ``lower_projection`` writes a scheme whose root takes the source node
as its identity, and beneath it one assertion of the result property whose reference is the path, so each member is
restated as a statement on the instance and nothing is minted (``_lower_expansion``). It is guarded by every
required-evidence binding of the contract's own carrier. Every projection kind now lowers into a scheme.

**Dependency graph.** ``link_dependencies`` recognises exactly two declared
cross-references within one lowering batch: a projection role binding's
``bindsCarrier`` naming another contract's own carrier, and a role binding's
``bindsProperty`` naming a value another contract's ``promotesTo`` mints. Both
become ``mork:dependsOnMapping`` edges. Anything else — a promotion's
``viaMatchRelation`` crosswalk, a bound scheme contract, a dependency on a
contract outside the batch — is not resolved, because none of those name
another Surface contract directly; resolving them is future work, not stated
here as done.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Set, Tuple
from urllib.parse import quote

from rdflib import Graph, Literal, URIRef

from .expression import ARITHMETIC_KINDS, CHOICE, ROUNDING, TYPED_LITERAL
from .model import ConstructedNode, Contract, ExpansionStatement, Expression, JoinStatement, ProjectionContract, RoleBinding
from .namespaces import MORK, RDF, SH, SRF
from .naming import Minter, local_name


def _parameter(graph: Graph, node: URIRef, name: str, kind: str, value) -> None:
    graph.add((node, RDF.type, MORK.ParameterBinding))
    graph.add((node, MORK.paramName, Literal(name)))
    graph.add((node, MORK.paramType, Literal(kind)))
    graph.add((node, MORK.paramValue, value))


def _minter_for(contract) -> Minter:
    return Minter(
        target_namespace=contract.target_namespace,
        contract_key=contract.key,
        carrier=str(contract.carrier),
        normalisation=contract.profile.naming_normalisation,
        naming_policy=getattr(contract, "naming_policy", None) or "",
        naming_prefix=getattr(contract, "naming_prefix", ""),
    )


def contract_parameter_bindings(contract: Contract) -> List[Tuple[str, str, object]]:
    """The parameter-binding shape common to a Promotion or Index declaration.

    Shared between ``lower_contract`` (below) and ``tools/surface/mork.py``'s
    ``lift`` — the same shape, whether the source is a bare declaration or an
    already-compiled surface — so that ``mork.py``'s existing ``lower()``
    round-trips a mapping from either origin without caring which produced it.
    """
    read_path = " / ".join(
        (f"^{step.prop}" if step.inverse else str(step.prop)) for step in contract.path
    )
    bindings: List[Tuple[str, str, object]] = [
        ("carrier", "Concept", contract.carrier),
        ("readPath", "Path", Literal(read_path)),
        ("targetNamespace", "String", Literal(contract.target_namespace)),
        ("realisationMode", "Concept", URIRef(contract.realisation_mode)),
    ]
    if contract.is_index:
        bindings.append(("namingPolicy", "Concept", URIRef(contract.naming_policy)))
        for form in contract.index_forms:
            bindings.append((f"indexForm_{local_name(form)}", "Concept", URIRef(form)))
        if contract.closure_basis is not None:
            bindings.append(("closureBasis", "Path", Literal(str(contract.closure_basis))))
    else:
        bindings.append(("promotesTo", "Concept", contract.promotes_to))
        bindings.append(("sourceFidelity", "Concept", URIRef(contract.source_fidelity)))
        if contract.via_match_relation is not None:
            bindings.append(("viaMatchRelation", "Concept", contract.via_match_relation))
    return bindings


def _projection_bindings(contract: ProjectionContract) -> List[Tuple[str, str, object]]:
    """Every role binding and backend-policy field of a projection, as the parameter bindings that record it."""
    bindings: List[Tuple[str, str, object]] = [
        ("projectionKind", "Concept", contract.projection_kind),
        ("targetNamespace", "String", Literal(contract.target_namespace)),
        ("realisationMode", "Concept", URIRef(contract.realisation_mode)),
    ]

    for index, role in enumerate(contract.role_bindings):
        role_name = f"role_{index}_{local_name(str(role.role_kind))}"
        bindings.append((role_name, "Concept", role.role_kind))
        if role.binds_property is not None:
            bindings.append((f"{role_name}_property", "Concept", role.binds_property))
        if role.binds_carrier is not None:
            bindings.append((f"{role_name}_carrier", "Concept", role.binds_carrier))

    policy = contract.backend_policy
    if policy is not None:
        for backend in policy.allowed_backends:
            bindings.append((f"allowedBackend_{local_name(str(backend))}", "Concept", backend))
        for backend in policy.denied_backends:
            bindings.append((f"deniedBackend_{local_name(str(backend))}", "Concept", backend))
        bindings.append(("deterministicOnly", "Boolean", Literal(policy.deterministic_only)))
        if policy.llm_completion_policy is not None:
            bindings.append(("llmCompletionPolicy", "Concept", policy.llm_completion_policy))
        for template in policy.approved_templates:
            safe_name = local_name(template) if "://" in template else template
            bindings.append((f"approvedTemplate_{safe_name}", "String", Literal(template)))
    return bindings


def _record_contract(graph: Graph, minter: Minter, contract: ProjectionContract, head: URIRef) -> None:
    """Write the link from the contract to ``head``, its targeting spec and its parameter bindings.

    ``head`` is the node that stands for the contract. ``srf:producesMapping`` is how the lowered scheme or bare mapping
    names its contract, as structure a reader follows, so no note carries the contract's IRI.
    """
    graph.add((contract.iri, SRF.producesMapping, head))
    target = minter.lowered_mapping_target()
    graph.add((head, MORK.hasTargetingSpec, target))
    graph.add((target, RDF.type, MORK.TargetingSpec))
    graph.add((target, SH.targetClass, contract.carrier))

    for name, kind, value in _projection_bindings(contract):
        node = minter.lowered_mapping_param(name)
        graph.add((head, MORK.hasParameterBinding, node))
        _parameter(graph, node, name, kind, value)


def lowers_to_scheme(contract: ProjectionContract) -> bool:
    """Whether a projection lowers into a mapping scheme, which is every kind that states what it writes: a derivation that
    states its expression, a graph construction its node, a join its relation and an expansion its members."""
    return (
        contract.expression is not None
        or contract.construction is not None
        or contract.join is not None
        or contract.expansion is not None
    )


def lowered_head(contract: ProjectionContract) -> URIRef:
    """The node of a lowered projection that stands for the contract, the one a dependency edge leaves from."""
    minter = _minter_for(contract)
    return minter.lowered_root() if lowers_to_scheme(contract) else minter.lowered_mapping()


def lower_projection(contract: ProjectionContract) -> Graph:
    """Write what a projection contract lowers into.

    A derivation, a graph construction, a join and an expansion lower into a mapping scheme (``_lower_derivation``,
    ``_lower_construction``, ``_lower_join``, ``_lower_expansion``). A contract that states none of them lowers into one bare
    ``mork:DataMapping`` per contract. Every role binding and every backend-policy field becomes a parameter binding,
    so nothing the contract declared is lost in translation and a later compiler stage can read it back without
    re-parsing the Surface declaration graph.
    """
    minter = _minter_for(contract)

    graph = Graph()
    graph.bind("mork", MORK)
    graph.bind("srf", SRF)
    graph.bind("sh", SH)

    if contract.construction is not None:
        _lower_construction(graph, minter, contract, contract.construction)
        return graph
    if contract.join is not None:
        _lower_join(graph, minter, contract, contract.join)
        return graph
    if contract.expansion is not None:
        _lower_expansion(graph, minter, contract, contract.expansion)
        return graph
    if contract.expression is not None:
        _lower_derivation(graph, minter, contract)
        return graph

    mapping = minter.lowered_mapping()
    graph.add((mapping, RDF.type, MORK.DataMapping))
    graph.add((mapping, MORK.mappingFor, contract.iri))
    graph.add(
        (
            mapping,
            MORK.mappingNote,
            Literal(
                f"Lowered from a srf:ProjectionContract "
                f"(projection kind {local_name(str(contract.projection_kind))}). "
                f"Backend-specific compilation (ADR-A19, ADR-A23) has not yet run; "
                f"this mapping records intent and role bindings only, and is not yet "
                f"classified as any GenerativeMapping subtype."
            ),
        )
    )
    _record_contract(graph, minter, contract, mapping)
    return graph


def _lower_derivation(graph: Graph, minter: Minter, contract: ProjectionContract) -> None:
    """A derivation as a mapping scheme (ADR-A18).

    The root iterates the carrier class and is identified by the source node itself, so the assertion beneath it writes
    the result property on the carrier instance and no datum is minted or typed. Each evidence role the expression
    reads is a typed reference, shared by every operand that names it.
    """
    expression = contract.expression
    assert expression is not None
    role_index = {str(role.iri): index for index, role in enumerate(contract.role_bindings)}

    scheme = minter.lowered_scheme()
    concept = minter.lowered_carrier_concept()
    root = minter.lowered_root()
    assertion = minter.lowered_assertion()

    graph.add((scheme, RDF.type, MORK.MappingScheme))

    graph.add((concept, RDF.type, MORK.DataConcept))
    graph.add((concept, MORK.representedAs, contract.carrier))

    graph.add((root, RDF.type, MORK.DataMapping))
    graph.add((root, RDF.type, MORK.Datum))
    graph.add((root, MORK.mappingScheme, scheme))
    graph.add((root, MORK.mappingFor, concept))
    graph.add((root, MORK.identityRule, MORK.SourceNodeIdentity))
    graph.add((root, MORK.compositeNarrowerMapping, assertion))
    graph.add(
        (
            root,
            MORK.mappingNote,
            Literal(
                f"Lowered from a srf:ProjectionContract "
                f"(projection kind {local_name(str(contract.projection_kind))}) into a mapping scheme. "
                f"Backend-specific compilation (ADR-A19, ADR-A23) has not yet run."
            ),
        )
    )
    _record_contract(graph, minter, contract, root)

    target = contract.roles(SRF.ResultTargetRole)[0]
    graph.add((assertion, RDF.type, MORK.DataMapping))
    graph.add((assertion, MORK.mappingScheme, scheme))
    graph.add((assertion, MORK.exactRBoxMatch, target.binds_property))
    graph.add((assertion, MORK.valueExpression, _lower_expression(graph, minter, expression, "0", role_index)))


def _lower_construction(graph: Graph, minter: Minter, contract: ProjectionContract, node: ConstructedNode) -> None:
    """A graph construction as a mapping scheme (ADR-A18).

    The root iterates the carrier class and is identified by the source node, as a derivation's is, so nothing is minted
    for the instance. Beneath it a contextual datum mints and types the constructed node and is glued to the instance by
    the link the result-target binding binds, and an assertion beneath that writes each value from its evidence
    binding. The datum is guarded by every required-evidence binding, so an instance that lacks one contributes nothing
    at all, no node, no link and no value (the guard sits on the datum's frame, which each query beneath inherits).

    The node's identity is the contract's choice. A node for each instance is named from a hash of the instance's
    identifier, and a keyed node from the key's values, an identifier concatenation over the key bindings in the order of
    their properties. Both carry the contract's key and the class in the identifier, so two contracts never reach one
    node. A keyed node merges every instance that shares the key, which a reader of the scheme finds in its identity
    template and ``mork_rdf`` reports as a mapping review.
    """
    scheme = minter.lowered_scheme()
    concept = minter.lowered_carrier_concept()
    root = minter.lowered_root()
    datum = minter.lowered_node()

    graph.add((scheme, RDF.type, MORK.MappingScheme))
    graph.add((concept, RDF.type, MORK.DataConcept))
    graph.add((concept, MORK.representedAs, contract.carrier))

    graph.add((root, RDF.type, MORK.DataMapping))
    graph.add((root, RDF.type, MORK.Datum))
    graph.add((root, MORK.mappingScheme, scheme))
    graph.add((root, MORK.mappingFor, concept))
    graph.add((root, MORK.identityRule, MORK.SourceNodeIdentity))
    graph.add((root, MORK.compositeNarrowerMapping, datum))
    graph.add(
        (
            root,
            MORK.mappingNote,
            Literal(
                f"Lowered from a srf:ProjectionContract "
                f"(projection kind {local_name(str(contract.projection_kind))}) into a mapping scheme. "
                f"Backend-specific compilation (ADR-A19, ADR-A23) has not yet run."
            ),
        )
    )
    _record_contract(graph, minter, contract, root)

    # The node is made, typed and linked from the instance, and only for an instance that holds every required value.
    stem = f"{quote(contract.key, safe='')}/{quote(local_name(str(node.constructed_class)), safe='')}"
    graph.add((datum, RDF.type, MORK.DataMapping))
    graph.add((datum, MORK.mappingScheme, scheme))
    graph.add((datum, MORK.broaderApplicative, root))
    graph.add((datum, MORK.exactTBoxMatch, node.constructed_class))
    graph.add((datum, MORK.inverseRBoxMatch, node.link.binds_property))

    required = sorted(
        {str(b.binds_property) for b in contract.roles(SRF.RequiredEvidenceRole) if b.binds_property is not None}
    )
    if required:
        guard = minter.lowered_guard()
        graph.add((datum, MORK.appliesWhen, guard))
        graph.add((guard, RDF.type, SH.NodeShape))
        for index, path in enumerate(required):
            constraint = minter.lowered_guard_property(index)
            graph.add((guard, SH.property, constraint))
            graph.add((constraint, SH.path, URIRef(path)))
            graph.add((constraint, SH.minCount, Literal(1)))

    if node.keyed:
        _lower_key_identity(graph, minter, datum, stem, node)
    else:
        graph.add((datum, MORK.conceptName, Literal(stem)))

    for index, written in enumerate(node.writes):
        assertion = minter.lowered_write(index)
        graph.add((datum, MORK.compositeNarrowerMapping, assertion))
        graph.add((assertion, RDF.type, MORK.DataMapping))
        graph.add((assertion, MORK.mappingScheme, scheme))
        graph.add((assertion, MORK.exactRBoxMatch, written.property))
        graph.add((assertion, MORK.dataRef, Literal(f"<{written.binding.binds_property}>")))


def _own_required(contract: ProjectionContract) -> List[str]:
    """The properties of the contract's own carrier that a required-evidence binding reads, sorted. A binding that names a
    second carrier reads that carrier's instances and not the instance, so it is no part of what an instance must hold."""
    return sorted(
        {
            str(b.binds_property)
            for b in contract.roles(SRF.RequiredEvidenceRole)
            if b.binds_property is not None
            and (b.binds_carrier is None or str(b.binds_carrier) == str(contract.carrier))
        }
    )


def _lower_join(graph: Graph, minter: Minter, contract: ProjectionContract, join: JoinStatement) -> None:
    """A join as a mapping scheme (ADR-A18).

    The root iterates the carrier class and is identified by the source node, as a derivation's is. Beneath it a datum
    iterates the second carrier's class and takes the node it finds as its own, so nothing is minted or typed, and is glued
    to the instance by the link the result-target binding binds. Each equality the statement names is a condition of the
    datum, the instance's property on the left and the second carrier's on the right, in the order of the properties. The
    datum states how many nodes one value may name and how many links one instance may have, each written whether the
    contract states it or means its default, and that an instance that holds the values and finds no match is reported, as a
    warning on required evidence and as information on candidate evidence, so the scheme leaves none of them implicit.

    The datum is guarded by every required-evidence binding of the contract's own carrier, which is tested on the instance
    and not on the node found, so an instance that lacks one contributes nothing. Each condition states its own comparison,
    a cast to the datatype its right binding states, joined as the same term, and the same term where it states none
    (law ``srf:P17``), so one key may compare a string pair and an integer pair.
    """
    scheme = minter.lowered_scheme()
    concept = minter.lowered_carrier_concept()
    second = minter.lowered_second_concept()
    root = minter.lowered_root()
    datum = minter.lowered_node()

    graph.add((scheme, RDF.type, MORK.MappingScheme))
    graph.add((concept, RDF.type, MORK.DataConcept))
    graph.add((concept, MORK.representedAs, contract.carrier))
    graph.add((second, RDF.type, MORK.DataConcept))
    graph.add((second, MORK.representedAs, join.second_carrier))

    graph.add((root, RDF.type, MORK.DataMapping))
    graph.add((root, RDF.type, MORK.Datum))
    graph.add((root, MORK.mappingScheme, scheme))
    graph.add((root, MORK.mappingFor, concept))
    graph.add((root, MORK.identityRule, MORK.SourceNodeIdentity))
    graph.add((root, MORK.compositeNarrowerMapping, datum))
    graph.add(
        (
            root,
            MORK.mappingNote,
            Literal(
                f"Lowered from a srf:ProjectionContract "
                f"(projection kind {local_name(str(contract.projection_kind))}) into a mapping scheme. "
                f"Backend-specific compilation (ADR-A19, ADR-A23) has not yet run."
            ),
        )
    )
    _record_contract(graph, minter, contract, root)

    graph.add((datum, RDF.type, MORK.DataMapping))
    graph.add((datum, RDF.type, MORK.Datum))
    graph.add((datum, MORK.mappingScheme, scheme))
    graph.add((datum, MORK.broaderApplicative, root))
    graph.add((datum, MORK.mappingFor, second))
    graph.add((datum, MORK.identityRule, MORK.SourceNodeIdentity))
    graph.add((datum, MORK.inverseRBoxMatch, join.link.binds_property))
    graph.add(
        (datum, MORK.joinCardinality, MORK.AtMostOneMatch if join.at_most_one else MORK.AnyNumberOfMatches)
    )
    graph.add(
        (datum, MORK.linkCardinality, MORK.AtMostOneMatch if join.at_most_one_link else MORK.AnyNumberOfMatches)
    )
    # An instance that holds the values and finds no match is reported either way. On required evidence it is a warning, since
    # a value a contract asks for found nothing, and on candidate evidence it is information.
    graph.add((datum, MORK.reportsUnmatched, Literal(True)))
    graph.add((datum, MORK.unmatchedSeverity, MORK.WarningFinding if join.required else MORK.InfoFinding))

    required = _own_required(contract)
    if required:
        guard = minter.lowered_guard()
        graph.add((datum, MORK.appliesWhen, guard))
        graph.add((guard, RDF.type, SH.NodeShape))
        for index, path in enumerate(required):
            constraint = minter.lowered_guard_property(index)
            graph.add((guard, SH.property, constraint))
            graph.add((constraint, SH.path, URIRef(path)))
            graph.add((constraint, SH.minCount, Literal(1)))

    for index, pair in enumerate(join.pairs):
        condition = minter.lowered_condition(index)
        graph.add((datum, MORK.joinsOn, condition))
        graph.add((condition, RDF.type, MORK.JoinCondition))
        graph.add((condition, MORK.parentRef, Literal(f"<{pair.left.binds_property}>")))
        graph.add((condition, MORK.ownRef, Literal(f"<{pair.right.binds_property}>")))
        # Each pair is compared as it says. A pair whose second carrier states a datatype casts the instance's value to it and
        # joins the same term, and a pair that states none joins the same term as it is.
        if pair.datatype is None:
            graph.add((condition, MORK.lookupComparison, MORK.TermComparison))
        else:
            graph.add((condition, MORK.lookupComparison, MORK.CastComparison))
            graph.add((condition, MORK.lookupDatatype, pair.datatype))


def _lower_expansion(graph: Graph, minter: Minter, contract: ProjectionContract, expansion: ExpansionStatement) -> None:
    """An expansion as a mapping scheme (ADR-A18).

    The root iterates the carrier class and is identified by the source node, as a derivation's is, so nothing is minted
    for the instance and nothing for a member. Beneath it one assertion writes the property the result-target binding binds
    on the instance, with the members' path as its reference, so it writes one statement for each node the path reaches. The
    path is the contract's own SHACL path, or the one a named source gives (``srf:ListMembers``, ``srf:TransitiveClosure``),
    written in full IRIs. The compiled query is the assertion's, so an instance with no members writes nothing.

    The assertion is guarded by every required-evidence binding of the contract's own carrier, so an instance that lacks one
    contributes nothing and is reported. An expansion on candidate evidence has no guard, and an instance with no members is
    reported as an empty collection whichever way it came to have none.
    """
    scheme = minter.lowered_scheme()
    concept = minter.lowered_carrier_concept()
    root = minter.lowered_root()
    assertion = minter.lowered_assertion()

    graph.add((scheme, RDF.type, MORK.MappingScheme))
    graph.add((concept, RDF.type, MORK.DataConcept))
    graph.add((concept, MORK.representedAs, contract.carrier))

    graph.add((root, RDF.type, MORK.DataMapping))
    graph.add((root, RDF.type, MORK.Datum))
    graph.add((root, MORK.mappingScheme, scheme))
    graph.add((root, MORK.mappingFor, concept))
    graph.add((root, MORK.identityRule, MORK.SourceNodeIdentity))
    graph.add((root, MORK.compositeNarrowerMapping, assertion))
    graph.add(
        (
            root,
            MORK.mappingNote,
            Literal(
                f"Lowered from a srf:ProjectionContract "
                f"(projection kind {local_name(str(contract.projection_kind))}) into a mapping scheme. "
                f"Backend-specific compilation (ADR-A19, ADR-A23) has not yet run."
            ),
        )
    )
    _record_contract(graph, minter, contract, root)

    graph.add((assertion, RDF.type, MORK.DataMapping))
    graph.add((assertion, MORK.mappingScheme, scheme))
    graph.add((assertion, MORK.exactRBoxMatch, expansion.link.binds_property))
    graph.add((assertion, MORK.dataRef, Literal(expansion.path_text)))

    required = _own_required(contract)
    if required:
        guard = minter.lowered_guard()
        graph.add((assertion, MORK.appliesWhen, guard))
        graph.add((guard, RDF.type, SH.NodeShape))
        for index, path in enumerate(required):
            constraint = minter.lowered_guard_property(index)
            graph.add((guard, SH.property, constraint))
            graph.add((constraint, SH.path, URIRef(path)))
            graph.add((constraint, SH.minCount, Literal(1)))


def _lower_key_identity(graph: Graph, minter: Minter, datum: URIRef, stem: str, node: ConstructedNode) -> None:
    """A keyed node's identifier, the stem and then the key's values separated by a slash, each value encoded for an IRI.

    The parts are the stem, then each key value with a slash before every one after the first. They are joined from the
    last pair outwards, so the outermost concatenation is the identity the datum names.
    """
    parts: List[URIRef] = []
    literal = minter.lowered_identity_part(0)
    graph.add((literal, RDF.type, MORK.LiteralExpression))
    graph.add((literal, MORK.dataInline, Literal(f"{stem}/")))
    parts.append(literal)
    for index, binding in enumerate(node.key):
        if index:
            separator = minter.lowered_identity_part(len(parts))
            graph.add((separator, RDF.type, MORK.LiteralExpression))
            graph.add((separator, MORK.dataInline, Literal("/")))
            parts.append(separator)
        reference = minter.lowered_identity_part(len(parts))
        graph.add((reference, RDF.type, MORK.RefExpression))
        graph.add((reference, MORK.dataRef, Literal(f"<{binding.binds_property}>")))
        parts.append(reference)

    right = parts[-1]
    for position in range(len(parts) - 2, -1, -1):
        joined = minter.lowered_identity(position)
        graph.add((joined, RDF.type, MORK.ConcatExpression))
        graph.add((joined, MORK.concatLeft, parts[position]))
        graph.add((joined, MORK.concatRight, right))
        right = joined
    graph.add((datum, MORK.identityTemplateMapping, right))


def _lower_reference(graph: Graph, minter: Minter, role: RoleBinding, index: int) -> URIRef:
    node = minter.lowered_reference(index)
    graph.add((node, RDF.type, MORK.TypedRefExpression))
    graph.add((node, MORK.resultDatatype, role.datatype))
    # An absolute IRI in angle brackets is a SPARQL 1.1 path of one step, so no prefix needs declaring.
    graph.add((node, MORK.dataRef, Literal(f"<{role.binds_property}>")))
    return node


def _lower_expression(
    graph: Graph, minter: Minter, expression: Expression, position: str, role_index: Dict[str, int]
) -> URIRef:
    """Carry an expression into MORK's typed value expressions, naming each node by its position."""
    node = minter.lowered_expression(position)
    kind = expression.kind
    graph.add((node, RDF.type, MORK[local_name(str(kind))]))
    graph.add((node, MORK.resultDatatype, expression.datatype))

    operands: List[URIRef] = []
    for offset, operand in enumerate(expression.operands):
        if isinstance(operand, RoleBinding):
            operands.append(_lower_reference(graph, minter, operand, role_index[str(operand.iri)]))
        else:
            operands.append(_lower_expression(graph, minter, operand, f"{position}_{offset}", role_index))

    if kind in ARITHMETIC_KINDS:
        graph.add((node, MORK.leftOperand, operands[0]))
        graph.add((node, MORK.rightOperand, operands[1]))
    elif kind == ROUNDING:
        graph.add((node, MORK.roundedOperand, operands[0]))
        graph.add((node, MORK.roundingScale, Literal(expression.scale)))
    elif kind == TYPED_LITERAL:
        graph.add((node, MORK.typedValue, expression.literal))
    else:
        assert kind == CHOICE
        graph.add((node, MORK.comparisonOperator, MORK[local_name(str(expression.comparison))]))
        graph.add((node, MORK.comparedLeft, operands[0]))
        graph.add((node, MORK.comparedRight, operands[1]))
        graph.add((node, MORK.whenTrue, operands[2]))
        graph.add((node, MORK.whenFalse, operands[3]))
    return node


def lower_contract(contract: Contract) -> Graph:
    """Write the ``mork:DataMapping`` a Promotion or Index contract lowers into.

    Reads no source graph, enumerates no population, mints no symbol: this is
    the declaration mirrored into MORK, not a compiled surface accounted for
    in MORK. ``tools/surface/mork.py``'s ``lift`` covers the latter, for a
    contract that has actually been compiled, and can therefore also record an
    authority and hashes this function has no basis to claim.
    """
    minter = _minter_for(contract)

    graph = Graph()
    graph.bind("mork", MORK)
    graph.bind("srf", SRF)
    graph.bind("sh", SH)

    mapping = minter.lowered_mapping()
    graph.add((mapping, RDF.type, MORK.DataMapping))
    graph.add((mapping, MORK.mappingFor, contract.iri))
    kind = "an index" if contract.is_index else "a promotion"
    graph.add(
        (
            mapping,
            MORK.mappingNote,
            Literal(
                f"Lowered from {kind} contract {contract.iri}, configured to mirror into "
                f"MORK alongside its direct-emit path (ADR-A18). Not yet classified as any "
                f"GenerativeMapping subtype."
            ),
        )
    )

    target = minter.lowered_mapping_target()
    graph.add((mapping, MORK.hasTargetingSpec, target))
    graph.add((target, RDF.type, MORK.TargetingSpec))
    graph.add((target, SH.targetClass, contract.carrier))

    for name, kind_label, value in contract_parameter_bindings(contract):
        node = minter.lowered_mapping_param(name)
        graph.add((mapping, MORK.hasParameterBinding, node))
        _parameter(graph, node, name, kind_label, value)

    return graph


# ---------------------------------------------------------------------------
# Mapping dependency graph
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LoweredMapping:
    """One lowered mapping, tagged with enough of its source contract to link
    cross-contract dependencies once every contract in a batch has lowered.
    """

    contract_iri: URIRef
    mapping: URIRef
    carrier: URIRef
    promotes_to: Optional[URIRef] = None


def link_dependencies(
    mappings: Sequence[LoweredMapping], projections: Sequence[ProjectionContract]
) -> Graph:
    """Compute ``mork:dependsOnMapping`` edges across one lowering batch.

    Only a projection's role bindings carry a declared cross-reference to
    another contract (``bindsCarrier``, ``bindsProperty``); Promotion and
    Index contracts have no comparable field naming another Surface contract,
    so they can be a dependency target here but never a dependant.
    """
    graph = Graph()
    by_contract: Dict[str, LoweredMapping] = {str(m.contract_iri): m for m in mappings}
    by_carrier: Dict[str, List[URIRef]] = {}
    by_promoted_property: Dict[str, List[URIRef]] = {}
    for entry in mappings:
        by_carrier.setdefault(str(entry.carrier), []).append(entry.mapping)
        if entry.promotes_to is not None:
            by_promoted_property.setdefault(str(entry.promotes_to), []).append(entry.mapping)

    for projection in projections:
        dependant = by_contract.get(str(projection.iri))
        if dependant is None:
            continue
        targets: Set[str] = set()
        for role in projection.role_bindings:
            if role.binds_carrier is not None:
                targets.update(str(t) for t in by_carrier.get(str(role.binds_carrier), []))
            if role.binds_property is not None:
                targets.update(
                    str(t) for t in by_promoted_property.get(str(role.binds_property), [])
                )
        targets.discard(str(dependant.mapping))
        for target in sorted(targets):
            graph.add((dependant.mapping, MORK.dependsOnMapping, URIRef(target)))
    return graph


def lower_all(
    contracts: Sequence[Contract] = (),
    projections: Sequence[ProjectionContract] = (),
) -> Graph:
    """Lower every given contract and projection into one MORK mapping graph,
    then link cross-contract dependencies declared within the batch.

    ``contracts`` is Promotion/Index declarations lowered under the
    "configured" case (delivery-plan Phase 3 item 2); pass none to lower
    projections only, which is the common case, since Promotion and Index
    already have a working direct-emit path.
    """
    combined = Graph()
    combined.bind("mork", MORK)
    combined.bind("srf", SRF)
    combined.bind("sh", SH)

    lowered: List[LoweredMapping] = []
    for contract in contracts:
        graph = lower_contract(contract)
        mapping = next(graph.subjects(RDF.type, MORK.DataMapping))
        for triple in graph:
            combined.add(triple)
        lowered.append(
            LoweredMapping(
                contract_iri=contract.iri,
                mapping=mapping,
                carrier=contract.carrier,
                promotes_to=None if contract.is_index else contract.promotes_to,
            )
        )
    for projection in projections:
        graph = lower_projection(projection)
        for triple in graph:
            combined.add(triple)
        lowered.append(
            LoweredMapping(
                contract_iri=projection.iri, mapping=lowered_head(projection), carrier=projection.carrier
            )
        )

    for triple in link_dependencies(lowered, projections):
        combined.add(triple)
    return combined
