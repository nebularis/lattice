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
    if epoch_guard is not None and _local(_value(dimensions, "epochAuthority")) == "StoreLocalEpoch":
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

    diagnostics.extend(_check_slice_2(target, dimensions))
    diagnostics.extend(_check_slice_4(target, dimensions))
    _check_slice_5(target, uniqueness)

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


def _value(dimensions: dict[str, ResolvedDimension], name: str):
    rd = dimensions.get(name)
    return rd.value if rd is not None else None


def _warning(kind: str, target: Target, message: str) -> Diagnostic:
    return Diagnostic(kind=kind, severity="WARNING", target=str(target), message=message)


def _check_slice_2(target: Target, dimensions: dict[str, ResolvedDimension]) -> list[Diagnostic]:
    """persistence-compiler-iri-sync Slice 2: the extension-property checks.
    Each runs on resolved values, so it also catches two properties
    declared on different profile nodes, which the node-local SHACL shapes
    cannot see. Raises :class:`CrossAxisViolation` for the two
    configurations that produce wrong reads; returns warnings otherwise."""
    out: list[Diagnostic] = []
    concurrency = _local(_value(dimensions, "concurrencyProfile"))
    global_read = _local(_value(dimensions, "globalReadStrategy"))

    # Mirrors dal:AsOfFloorRetentionCompatibilityShape.
    if _local(_value(dimensions, "retentionMode")) == "BucketAnyRetention" and _value(dimensions, "asOfFloorSource") is not None:
        raise CrossAxisViolation(
            "AsOfFloorRetentionConflict",
            str(target),
            "dal:retentionMode dal:BucketAnyRetention with an as-of floor (dal:asOfFloorSource): pruning a "
            "retraction's bucket while its assertion's bucket survives resurrects a deleted triple in "
            "as-of replay. Select dal:PrefixOnlyRetention (guide §24.2).",
        )

    # Mirrors dal:LagWindowRequiredShape.
    if global_read == "LagWindowRead":
        window = _value(dimensions, "lagWindowMillis")
        if window is None or int(window) <= 0:
            raise CrossAxisViolation(
                "LagWindowMissing",
                str(target),
                "dal:globalReadStrategy dal:LagWindowRead without a positive dal:lagWindowMillis: the "
                "read has no upper bound and skips writes that commit after a reader passed their HLC. "
                "The window covers the server-enforced maximum transaction duration plus clock skew, "
                "replica lag and a margin (guide §21.3).",
            )

    # Mirrors dal:WeakEtagCasWarningShape, across nodes.
    if _local(_value(dimensions, "etagForm")) == "WeakEtag" and concurrency == "Optimistic":
        out.append(_warning(
            "WeakEtagCas", target,
            "dal:etagForm dal:WeakEtag with dal:Optimistic concurrency: RFC 9110 §13.1.1 requires strong "
            "comparison for If-Match, so every conditional write over HTTP fails (guide §15.4).",
        ))

    # Mirrors dal:NoGlobalReadWarningShape.
    if global_read == "NoGlobalRead":
        out.append(_warning(
            "NoGlobalRead", target,
            "dal:globalReadStrategy dal:NoGlobalRead: confirm this family has no dataset-tier consumer, "
            "otherwise a cross-stream reader can skip late-committing writes (guide §21.3).",
        ))

    # Plan decision 2: a dataset tier with no declared way to read it safely.
    ordering = dimensions.get("orderingGrain")
    if ordering is not None and ordering.extra.get("datasetTierModel") is not None and global_read is None:
        out.append(_warning(
            "DatasetTierWithoutGlobalRead", target,
            "a dal:datasetTierModel is declared but no dal:globalReadStrategy: select dal:WatermarkedRead, "
            "dal:LagWindowRead or dal:DenseFeedRead so cross-stream readers are bounded (guide §21.3), or "
            "dal:NoGlobalRead if there is no such reader.",
        ))

    # Mirrors dal:AdvisoryContiguityWarningShape.
    if _local(_value(dimensions, "contiguityCheckMode")) == "AdvisoryContiguityCheck":
        out.append(_warning(
            "AdvisoryContiguity", target,
            "dal:contiguityCheckMode dal:AdvisoryContiguityCheck only raises a metric on a gap; "
            "dal:BlockingContiguityCheck stops the consumer before a gap is absorbed (guide §21.3).",
        ))

    # Guide §19.6: sorted acquisition is meaningful only where the client
    # issues separate acquisition steps (multi-request transactions,
    # external locks), never inside one guarded SPARQL Update.
    if _local(_value(dimensions, "deadlockPolicy")) == "SortedAcquisition" and concurrency in ("Optimistic", "AppendOnly"):
        out.append(_warning(
            "SortedAcquisitionIneffective", target,
            f"dal:deadlockPolicy dal:SortedAcquisition with dal:{concurrency}: a single guarded SPARQL "
            "Update specifies no acquisition order, so sorting targets in the query text orders nothing. "
            "Use dal:EngineDetectAndRetry or dal:PartitionedWriter (guide §19.6).",
        ))

    # Plan decision 3: shard counts are resolved but no template shards yet.
    for name, graph in (("txnShards", "urn:g:txn"), ("logShards", "urn:g:txlog/{month}"), ("keyShards", "urn:g:keys")):
        count = _value(dimensions, name)
        if count is not None and int(count) > 1:
            out.append(_warning(
                "ShardingNotHonoured", target,
                f"dal:{name} is {int(count)}, but the generated SPARQL writes a single {graph} graph. "
                "The declaration is recorded in the compiled profile and not yet applied.",
            ))
    return out


def _check_slice_4(target: Target, dimensions: dict[str, ResolvedDimension]) -> list[Diagnostic]:
    """persistence-compiler-iri-sync Slice 4: the privacy/erasure checks.

    Both mirrored shapes (``dal:PersonalDataRequiresErasureShape``,
    ``dal:PersonalDataReceiptCompatibilityShape``) declare no
    ``sh:severity``, so both default to ``sh:Violation``: an unreachable
    erasure obligation is a correctness failure, not a discouraged-but-
    valid trade-off, and both are raised as :class:`CrossAxisViolation`
    rather than returned as warnings, matching every other un-severitied
    shape this compiler mirrors (``DigestSchemeRequired``,
    ``AsOfFloorRetentionConflict``, and so on).

    The second check joins ``dal:PrivacyProfile``'s dimensions with
    ``dal:ReceiptProfile``'s on resolved values, which also catches the
    two profile classes declared on separate nodes -- something the
    node-local SHACL shape (matched only by a shared ``dal:appliesTo``
    scope) cannot see. This is the first check in this module to join two
    dimensions that come from genuinely different profile classes, rather
    than two properties of the same one."""
    privacy_class = _local(_value(dimensions, "privacyClass"))
    if privacy_class != "PersonalData":
        return []

    erasure_strategy = _local(_value(dimensions, "erasureStrategy"))

    # Mirrors dal:PersonalDataRequiresErasureShape.
    if erasure_strategy == "NoErasure":
        raise CrossAxisViolation(
            "PersonalDataRequiresErasure",
            str(target),
            "dal:privacyClass dal:PersonalData with dal:erasureStrategy dal:NoErasure has no lawful "
            "erasure path. Select dal:PerSubjectGraphDrop or dal:CryptoShred (ADR-A68).",
        )

    # Mirrors dal:PersonalDataReceiptCompatibilityShape.
    receipt_model = _local(_value(dimensions, "receiptModel"))
    if receipt_model in ("PatchLog", "SnapshotPerRevision"):
        per_subject_scoped = bool(_value(dimensions, "perSubjectScoped"))
        if not per_subject_scoped and erasure_strategy != "CryptoShred":
            raise CrossAxisViolation(
                "PersonalDataReceiptConflict",
                str(target),
                f"dal:privacyClass dal:PersonalData with dal:receiptModel dal:{receipt_model} and "
                "neither dal:perSubjectScoped true nor dal:erasureStrategy dal:CryptoShred: the delta "
                "or snapshot graphs are a second, immutable copy of the personal data that per-subject "
                "graph drop cannot reach (guide §20.4, ADR-A68 point 7).",
            )
    return []


def _check_slice_5(target: Target, uniqueness: list[dict]) -> None:
    """persistence-compiler-iri-sync Slice 5: mirrors
    dal:MergeRelationRequiredShape on resolved values. A hard refusal, like
    every other un-severitied shape this compiler mirrors: a merge policy
    that names no relation would write an undefined term."""
    for constraint in uniqueness:
        if _local(constraint.get("onViolation")) == "Merge" and constraint.get("mergeRelation") is None:
            raise CrossAxisViolation(
                "MergeRelationRequired",
                str(target),
                f"uniqueness constraint {constraint['constraintId']!r}: dal:onViolation dal:Merge requires "
                "dal:mergeRelation naming the relation the merge writes (for example fnd:replacedBy, if the "
                "adopter's ontology defines it). A merge policy that names no relation writes an undefined term.",
            )


DIGEST_ENCODINGS = frozenset({"lowercase-hex", "base32", "base64url"})


def check_identity(
    graph: Graph,
    target: Target,
    dimensions: dict[str, ResolvedDimension],
    identity: dict[str, ResolvedDimension],
    uniqueness: list[dict],
) -> list[Diagnostic]:
    """persistence-compiler-iri-sync Slice 3: checks on the resolved,
    role-qualified identity dimensions. Raises :class:`CrossAxisViolation`
    for a configuration that cannot mint a correct IRI; returns warnings
    otherwise. The first four mirror SHACL shapes on one dal:IdentityProfile
    node; the last two join the identity profile to other resolved
    dimensions, which SHACL cannot do."""
    out: list[Diagnostic] = []
    for name, rd in identity.items():
        strategy = _local(rd.value)
        extra = rd.extra
        where = f"{name} (won by {rd.won_by})"

        # Mirrors dal:DigestSchemeRequiredShape and dal:DigestSchemeWellFormedShape.
        if strategy in ("DerivedHashIdentity", "ContentAddressedIdentity"):
            scheme = extra.get("digestScheme")
            # persistence-compiler-iri-sync Slice 5: a registry-token
            # namespace is never digest-derived, so no digest scheme is
            # ever used for this exact role -- requiring one would be
            # requiring a value nothing reads (identity-minting M3 found
            # this in identity-minting-coverage.ttl). A scheme declared
            # anyway is still checked for well-formedness below; only the
            # "must be present" branch is exempted.
            digest_unused = (
                _local(extra.get("eventIdentityStrategy")) == "PositionDerivedEvent"
                and _local(extra.get("occurrenceNamespaceDerivation")) == "RegistryTokenDerivation"
            )
            if not (scheme is None and digest_unused):
                function = graph.value(scheme, DAL.digestFunction) if scheme is not None else None
                width = graph.value(scheme, DAL.digestWidthBits) if scheme is not None else None
                encoding = graph.value(scheme, DAL.digestEncoding) if scheme is not None else None
                if function is None or width is None or encoding is None:
                    raise CrossAxisViolation(
                        "DigestSchemeRequired", str(target),
                        f"{where}: dal:{strategy} requires a dal:digestScheme with dal:digestFunction, "
                        "dal:digestWidthBits and dal:digestEncoding. An unstated width or encoding lets two "
                        "implementations mint different IRIs for one input (iri-identity-patterns.md §7.4). "
                        "Exempt when dal:eventIdentityStrategy is dal:PositionDerivedEvent and "
                        "dal:occurrenceNamespaceDerivation is dal:RegistryTokenDerivation: the namespace is a "
                        "registry-allocated token, not digest-derived.",
                    )
                try:
                    width_ok = int(width) > 0 and int(width) % 8 == 0
                except (TypeError, ValueError):
                    width_ok = False
                if not width_ok or str(encoding) not in DIGEST_ENCODINGS:
                    raise CrossAxisViolation(
                        "DigestSchemeMalformed", str(target),
                        f"{where}: dal:digestWidthBits must be a positive multiple of 8 (got {width!s}) and "
                        f"dal:digestEncoding one of {sorted(DIGEST_ENCODINGS)} (got {encoding!s}).",
                    )

        event_strategy = _local(extra.get("eventIdentityStrategy"))
        if event_strategy == "PositionDerivedEvent":
            # Mirrors dal:UniquenessWitnessRequiredShape.
            if not bool(extra.get("uniquenessWitnessRequired", False)):
                raise CrossAxisViolation(
                    "UniquenessWitnessRequired", str(target),
                    f"{where}: dal:PositionDerivedEvent requires dal:uniquenessWitnessRequired true. Two "
                    "writers that both win merge into one occurrence subject, so only a per-occurrence "
                    "witness (txn-claim cardinality) reveals the fork (guide F5).",
                )
            # Mirrors dal:OccurrenceNamespaceDerivationRequiredShape.
            if extra.get("occurrenceNamespaceDerivation") is None:
                raise CrossAxisViolation(
                    "OccurrenceNamespaceDerivationRequired", str(target),
                    f"{where}: dal:PositionDerivedEvent requires dal:occurrenceNamespaceDerivation, so that "
                    "two targets never share an occurrence namespace (iri-identity-patterns.md §10.1).",
                )
            # Joins the epoch dimension: position-derived IRIs are reused after
            # a double restore unless the epoch is durable and guarded.
            epoch_guard_scope = dimensions.get("epochGuardScope")
            epoch_authority = dimensions.get("epochAuthority")  # Slice 4: its own dimension, not an extra
            unsafe = []
            if epoch_guard_scope is not None and _local(epoch_guard_scope.value) == "RowLevelGuardOnly":
                unsafe.append("dal:RowLevelGuardOnly")
            if epoch_authority is not None and _local(epoch_authority.value) == "StoreLocalEpoch":
                unsafe.append("dal:StoreLocalEpoch")
            if unsafe:
                out.append(_warning(
                    "PositionEventUnsafeEpoch", target,
                    f"{where}: position-derived occurrence IRIs with {' and '.join(unsafe)}: a restore can "
                    "reissue a position already used in an IRI that left the dataset "
                    "(iri-identity-patterns.md §10.3).",
                ))

        # A claimed surrogate's key is checked exactly by persistence.recipes,
        # through dal:claimsConstraint (identity-minting M1), which replaced
        # Slice 3's interim "at least one uniqueness constraint" check here.

        # identity-minting sketch §6a: the obligation reaches the compile output too.
        if strategy == "ContentAddressedIdentity":
            out.append(_warning(
                "ContentAddressedCallerObligations", target,
                f"{where}: minters hash canonical bytes the caller supplies and never canonicalize RDF. The "
                "caller must use an RDFC-1.0 implementation that passes the W3C test suite, apply the "
                "self-reference rule first, enforce the work budget, and compare full digests where declared "
                "(identity-minting-specification.md §7). Two callers who canonicalize differently mint "
                "different IRIs for one graph, and no conformance vector can detect it.",
            ))
    return out


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
