# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Cross-axis consistency checks (sketch §3.5) and boundary-strategy
conflicts (sketch §4.6). Every check is a named exception type or a named
:class:`~persistence.model.Diagnostic`, never free text, so a CI gate can
assert on the type (ADR-A79 is explicit that this compiler never silently
downgrades a configuration it cannot satisfy)."""

from __future__ import annotations

from rdflib import RDF, Graph, URIRef

from .boundary import MissingBoundaryShapeError, reachable_properties
from .capability import CapabilityCheckResult
from .model import BoundaryConflict, CrossAxisViolation, Diagnostic, ResolvedDimension
from .namespaces import DAL, SH
from .scopes import Target


def _local(value) -> str | None:
    return str(value).rsplit("#", 1)[-1] if value is not None else None


def check_cross_axis(
    graph: Graph,
    target: Target,
    dimensions: dict[str, ResolvedDimension],
    uniqueness: list[dict],
) -> list[Diagnostic]:
    """Runs every row of sketch §3.5 for one target. Raises
    :class:`CrossAxisViolation` on the first hard failure (rows 1-5);
    returns a list of :class:`Diagnostic` warnings for soft findings
    (the mixed-receipt-model check is scope-wide and run separately, see
    :func:`check_mixed_receipt_model`)."""
    diagnostics: list[Diagnostic] = []
    boundary = dimensions.get("aggregateBoundary")
    concurrency = dimensions.get("concurrencyProfile")
    receipts = dimensions.get("receiptModel")
    ordering = dimensions.get("orderingGrain")

    boundary_local = _local(boundary.value) if boundary else None
    concurrency_local = _local(concurrency.value) if concurrency else None

    # Row 1: NoBoundary + Optimistic with no value guard.
    if boundary_local == "NoBoundary" and concurrency_local == "Optimistic":
        if not concurrency.extra.get("valueGuardProperty"):
            raise CrossAxisViolation(
                "NoBoundaryConcurrencyConflict",
                str(target),
                "dal:NoBoundary combined with dal:Optimistic and no dal:valueGuardProperty: "
                "there is no aggregate to whole-graph replace. Declare a dal:valueGuardProperty "
                "for a value-based guard (guide §14.2), or declare a real boundary.",
            )

    # Row 2: CompositePropertyBoundary + ReceiptOnly.
    if boundary_local == "CompositePropertyBoundary" and _local(receipts.value if receipts else None) == "ReceiptOnly":
        raise CrossAxisViolation(
            "CompositeBoundaryReceiptConflict",
            str(target),
            "dal:CompositePropertyBoundary with dal:ReceiptOnly: a composite-property aggregate's "
            "write is a bounded closure sweep, not a single named-graph replace, so a receipt-only "
            "model cannot audit what changed within the closure. Require at least dal:PatchLog.",
        )

    # Row 3: metaShards changed without an acknowledged epoch bump.
    meta = dimensions.get("metaTopology")
    if meta is not None:
        prior = meta.extra.get("priorMetaShards")
        current = meta.extra.get("metaShards")
        if prior is not None and current is not None and int(prior) != int(current):
            if not bool(meta.extra.get("epochBumpAcknowledged", False)):
                raise CrossAxisViolation(
                    "UnacknowledgedShardMigration",
                    str(target),
                    f"dal:metaShards changed from {prior} to {current} without "
                    "dal:epochBumpAcknowledged. This is a migration event (guide §24.4). "
                    "Acknowledge the epoch bump explicitly.",
                )

    # Row 4: CommitGrain + opSeqRequired.
    if ordering is not None and _local(ordering.value) == "CommitGrain":
        if bool(ordering.extra.get("opSeqRequired", False)):
            raise CrossAxisViolation(
                "CommitGrainOpSeqConflict",
                str(target),
                "dal:CommitGrain declared alongside dal:opSeqRequired true: opSeq is meaningless "
                "at commit grain. Drop the flag, or move to dal:EventGrain.",
            )

    # New row (persistence-compiler-iri-sync Slice 1, 2026-09-23): epoch
    # guard scope. Mirrors dal:RowLevelGuardOnlyWarningShape. Fires
    # whether the value came from an explicit dal:EpochProfile or from
    # BASELINE_DEFAULTS, so the discouraged shape is never generated
    # silently (sketch note in model.py's BASELINE_DEFAULTS comment).
    # Warning severity, matching the SHACL shape: this is a documented,
    # adopter-facing trade-off (ADR-A82), never a hard refusal.
    epoch_guard = dimensions.get("epochGuardScope")
    if epoch_guard is not None and _local(epoch_guard.value) == "RowLevelGuardOnly":
        diagnostics.append(
            Diagnostic(
                kind="RowLevelGuardOnly",
                severity="WARNING",
                target=str(target),
                message=(
                    "dal:epochGuardScope is dal:RowLevelGuardOnly (either explicitly declared or "
                    "the platform baseline default): a write guarded only on the version row's own "
                    "epoch can still match an unrestored row after a dataset-level bump that never "
                    "reaches that row. dal:DatasetLevelGuard is required for restore safety to "
                    "actually hold (iri-identity-patterns.md §10.3)."
                ),
            )
        )
    if epoch_guard is not None and _local(epoch_guard.extra.get("epochAuthority")) == "StoreLocalEpoch":
        diagnostics.append(
            Diagnostic(
                kind="StoreLocalEpoch",
                severity="WARNING",
                target=str(target),
                message=(
                    "dal:epochAuthority is dal:StoreLocalEpoch: unsafe under a double restore from "
                    "the same backup, since the second restore reuses the epoch the first one just "
                    "allocated inside the same dataset (iri-identity-patterns.md §10.3)."
                ),
            )
        )

    # Row 5: a uniqueness key property outside the declared boundary.
    if boundary_local == "CompositePropertyBoundary" and boundary is not None:
        boundary_shape = boundary.extra.get("boundaryShape")
        if boundary_shape is None:
            raise MissingBoundaryShapeError(
                f"dal:CompositePropertyBoundary at {target} declares no dal:boundaryShape"
            )
        max_depth = int(boundary.extra.get("maxTraversalDepth", 8))
        reachable = reachable_properties(graph, boundary_shape, max_depth)
        for constraint in uniqueness:
            for key_prop in constraint["keyProperty"]:
                if URIRef(key_prop) not in reachable:
                    raise CrossAxisViolation(
                        "UniquenessOutsideBoundary",
                        str(target),
                        f"uniqueness constraint {constraint['constraintId']!r}'s key property "
                        f"{key_prop!r} is not reachable within the declared boundary shape "
                        f"{boundary_shape!r}. Narrow the key property, or widen the shape.",
                    )

    return diagnostics


def check_mixed_receipt_model(graph: Graph, resolved_by_target: dict[Target, dict[str, ResolvedDimension]]) -> list[Diagnostic]:
    """Row 6 (sketch §3.5): a warning, not an error. Two targets covered by
    the same GraphPatternScope resolving to different receipt models."""
    diagnostics: list[Diagnostic] = []
    from .scopes import all_scopes

    for scope in all_scopes(graph):
        if scope.kind != "GraphPatternScope":
            continue
        models: dict[str, list[Target]] = {}
        for target, dims in resolved_by_target.items():
            if target.deployment != scope.iri:
                continue
            receipts = dims.get("receiptModel")
            if receipts is None or receipts.value is None:
                continue
            models.setdefault(_local(receipts.value), []).append(target)
        if len(models) > 1:
            detail = ", ".join(f"{model}: {[str(t) for t in ts]}" for model, ts in models.items())
            diagnostics.append(
                Diagnostic(
                    kind="MixedReceiptModel",
                    severity="WARNING",
                    target=str(scope.iri),
                    message=(
                        f"graph family {scope.iri} covers targets resolving to different receipt "
                        f"models: {detail}. A downstream consumer subscribing to this graph family "
                        "must be told, not left to assume uniformity."
                    ),
                )
            )
    return diagnostics


def check_boundary_conflicts(graph: Graph) -> list[Diagnostic]:
    """sketch §4.6, best-effort: a class that is both declared as a
    composite member of another target's boundary shape, and carries its
    own, different, non-baseline boundary strategy, cannot coherently
    belong to both."""
    diagnostics: list[Diagnostic] = []
    own_strategy: dict[URIRef, URIRef] = {}
    for profile in graph.subjects(RDF.type, DAL.AggregateBoundaryProfile):
        scope = graph.value(profile, DAL.appliesTo)
        if scope is None:
            continue
        cls = graph.value(scope, DAL.targetClass)
        strategy = graph.value(profile, DAL.strategy)
        if cls is not None and strategy is not None:
            own_strategy[cls] = strategy

    for profile in graph.subjects(RDF.type, DAL.AggregateBoundaryProfile):
        strategy = graph.value(profile, DAL.strategy)
        if strategy != DAL.CompositePropertyBoundary:
            continue
        shape = graph.value(profile, DAL.boundaryShape)
        if shape is None:
            continue
        for prop_shape in graph.objects(shape, SH.property):
            node_shape = graph.value(prop_shape, SH.node)
            if node_shape is None:
                continue
            member_cls = graph.value(node_shape, SH.targetClass)
            if member_cls is None:
                continue
            member_strategy = own_strategy.get(member_cls)
            if member_strategy and member_strategy != DAL.NoBoundary:
                raise BoundaryConflict(
                    f"{member_cls} is a composite member of {shape}'s closure, but also declares "
                    f"its own boundary strategy {member_strategy}. A resource cannot belong to two "
                    "aggregates under incompatible boundary strategies (sketch §4.6)."
                )
    return diagnostics


def check_capability(check: CapabilityCheckResult | None) -> None:
    if check is not None and check.verdict == "FAIL":
        raise CrossAxisViolation(
            "CapabilityCheckFailed",
            check.against,
            f"the supplied dal:CapabilitySpec does not satisfy this configuration's own "
            f"requirements: {'; '.join(check.failures)}",
        )


__all__ = [
    "check_cross_axis",
    "check_mixed_receipt_model",
    "check_boundary_conflicts",
    "check_capability",
]
