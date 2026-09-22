# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The ``compile`` stage (sketch §5.2): load, resolve, validate, select,
emit. Produces a canonical ``dal:CompiledProfile`` graph, per target, with
no SPARQL text and no dependency on a live backend anywhere in the
pipeline (ADR-A79).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rdflib import RDF, BNode, Graph, Literal as RdfLiteral, URIRef
from rdflib.collection import Collection

from . import validator
from .capability import (
    CapabilityCheckResult,
    CapabilitySpec,
    CapabilityRequirement,
    check_requirement,
    compute_requirement,
    load_capability_spec,
)
from .model import DIMENSIONS, Diagnostic, ResolvedDimension
from .namespaces import DAL
from .operations import GeneratedOperation, select_operations
from .resolver import resolve_dimension, resolve_uniqueness
from .scopes import Target, discover_targets


@dataclass
class CompiledTarget:
    target: Target
    dimensions: dict[str, ResolvedDimension]
    uniqueness: list[dict]
    operations: list[GeneratedOperation]
    requirement: CapabilityRequirement
    capability_spec: CapabilitySpec | None
    check: CapabilityCheckResult | None
    diagnostics: list[Diagnostic] = field(default_factory=list)


class CompileError(Exception):
    """Wraps a validation failure with the target it occurred for, so a
    caller can report which target's configuration is unsatisfiable
    without losing the original named exception."""

    def __init__(self, target: Target, cause: Exception):
        self.target = target
        self.cause = cause
        super().__init__(f"compile failed for {target}: {cause}")


def compile_targets(
    graph: Graph,
    classes: set[URIRef] | None = None,
    fail_on_capability_mismatch: bool = True,
) -> list[CompiledTarget]:
    """Resolve, validate, and select operations for every discovered
    target. Raises :class:`CompileError` on the first hard failure,
    wrapping whichever named exception (``ProfileAmbiguityError``,
    ``CrossAxisViolation``, ``BoundaryConflict``, ``MissingBoundaryShapeError``)
    the underlying check raised."""
    targets = discover_targets(graph, classes)
    compiled: list[CompiledTarget] = []
    resolved_by_target: dict[Target, dict[str, ResolvedDimension]] = {}

    try:
        validator.check_boundary_conflicts(graph)
    except Exception as e:  # BoundaryConflict
        raise CompileError(Target(cls=URIRef("urn:x-persistence:whole-graph")), e) from e

    for target in targets:
        try:
            spec = load_capability_spec(graph, target)
            dimensions = {
                dim: resolve_dimension(graph, target, dim, spec) for dim in DIMENSIONS
            }
            uniqueness = resolve_uniqueness(graph, target)
            resolved_by_target[target] = dimensions

            diagnostics = validator.check_cross_axis(graph, target, dimensions, uniqueness)

            requirement = compute_requirement(dimensions, uniqueness)
            check = check_requirement(requirement, spec) if spec is not None else None
            if fail_on_capability_mismatch:
                validator.check_capability(check)

            operations = select_operations(target, dimensions, uniqueness)

            compiled.append(
                CompiledTarget(
                    target=target,
                    dimensions=dimensions,
                    uniqueness=uniqueness,
                    operations=operations,
                    requirement=requirement,
                    capability_spec=spec,
                    check=check,
                    diagnostics=diagnostics,
                )
            )
        except Exception as e:
            raise CompileError(target, e) from e

    mixed_receipt_warnings = validator.check_mixed_receipt_model(graph, resolved_by_target)
    by_target_iri = {str(ct.target): ct for ct in compiled}
    for warning in mixed_receipt_warnings:
        # attached to every compiled target this graph family covers, so
        # each target's own diagnostics list is self-contained
        for ct in compiled:
            if ct.target.deployment is not None and str(ct.target.deployment) == warning.target:
                ct.diagnostics.append(warning)

    return compiled


def _local(value) -> str:
    return str(value).rsplit("#", 1)[-1] if value is not None else ""


def emit_compiled_profile(out: Graph, compiled: CompiledTarget) -> URIRef:
    """Serialise one :class:`CompiledTarget` into ``out`` as a
    ``dal:CompiledProfile`` individual. Never writes literal SPARQL text
    (ADR-A79 point 2): only resolved values, provenance, template
    identifiers, and reified parameter bindings."""
    profile = BNode()
    out.add((profile, RDF.type, DAL.CompiledProfile))
    out.add((profile, DAL.forTarget, compiled.target.cls))
    if compiled.target.deployment is not None:
        out.add((profile, DAL.forDeployment, compiled.target.deployment))

    for dim in DIMENSIONS:
        rd = compiled.dimensions[dim]
        node = BNode()
        out.add((node, DAL.dimension, RdfLiteral(dim)))
        if rd.value is not None:
            value = rd.value if isinstance(rd.value, URIRef) else DAL[str(rd.value)]
            out.add((node, DAL.resolvedValue, value))
        if rd.won_by is not None:
            out.add((node, DAL.wonBy, URIRef(rd.won_by)))
        out.add((node, DAL.candidateCount, RdfLiteral(rd.candidate_count)))
        out.add((profile, DAL.resolvedDimension, node))

    for constraint in compiled.uniqueness:
        out.add((profile, DAL.appliedUniquenessConstraint, URIRef(constraint["constraint"])))

    for op in compiled.operations:
        op_node = BNode()
        out.add((op_node, RDF.type, DAL.GeneratedOperation))
        out.add((op_node, DAL.forOperation, RdfLiteral(op.operation)))
        template_node = BNode()
        out.add((template_node, RDF.type, DAL.Template))
        out.add((template_node, DAL.templateId, RdfLiteral(op.template_id)))
        out.add((template_node, DAL.templatePath, RdfLiteral(op.template_id)))
        out.add((op_node, DAL.usesTemplate, template_node))
        for binding in op.bindings:
            binding_node = BNode()
            out.add((binding_node, RDF.type, DAL.ParameterBinding))
            out.add((binding_node, DAL.paramName, RdfLiteral(binding.name)))
            out.add((binding_node, DAL.paramType, RdfLiteral(binding.param_type)))
            out.add((binding_node, DAL.paramValue, RdfLiteral(str(binding.value))))
            out.add((op_node, DAL.hasParameterBinding, binding_node))
        out.add((profile, DAL.generatedOperation, op_node))

    req_node = BNode()
    out.add((req_node, RDF.type, DAL.CapabilityRequirement))
    if compiled.requirement.requires_cas:
        out.add((req_node, DAL.requiresCas, RdfLiteral(compiled.requirement.requires_cas)))
    if compiled.requirement.requires_uniqueness_level:
        out.add(
            (
                req_node,
                DAL.requiresUniquenessLevel,
                DAL[compiled.requirement.requires_uniqueness_level],
            )
        )
    if compiled.requirement.requires_reasoning_for:
        list_node = BNode()
        Collection(out, list_node, [URIRef(s) for s in compiled.requirement.requires_reasoning_for])
        out.add((req_node, DAL.requiresReasoningFor, list_node))
    out.add((profile, DAL.capabilityRequirement, req_node))

    if compiled.check is not None:
        check_node = BNode()
        out.add((check_node, RDF.type, DAL.CapabilityCheck))
        out.add((check_node, DAL.checkedAgainst, URIRef(compiled.check.against)))
        out.add((check_node, DAL.verdict, RdfLiteral(compiled.check.verdict)))
        out.add((profile, DAL.capabilityCheck, check_node))

    for diag in compiled.diagnostics:
        diag_node = BNode()
        out.add((diag_node, RDF.type, DAL.Diagnostic))
        out.add((diag_node, DAL.diagnosticKind, RdfLiteral(diag.kind)))
        out.add((diag_node, DAL.diagnosticMessage, RdfLiteral(diag.message)))
        out.add((diag_node, DAL.diagnosticSeverity, RdfLiteral(diag.severity)))
        out.add((profile, DAL.diagnostic, diag_node))

    return profile


def compile_to_graph(
    graph: Graph,
    classes: set[URIRef] | None = None,
    fail_on_capability_mismatch: bool = True,
) -> tuple[Graph, list[CompiledTarget]]:
    compiled = compile_targets(graph, classes, fail_on_capability_mismatch)
    out = Graph()
    out.bind("dal", DAL)
    for ct in compiled:
        emit_compiled_profile(out, ct)
    return out, compiled


__all__ = ["CompiledTarget", "CompileError", "compile_targets", "emit_compiled_profile", "compile_to_graph"]
