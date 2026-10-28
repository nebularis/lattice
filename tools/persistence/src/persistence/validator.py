# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Cross-axis consistency checks (sketch §3.5) and boundary-strategy
conflicts (sketch §4.6). Every check is a named exception type or a named
:class:`~persistence.model.Diagnostic`, never free text, so a CI gate can
assert on the type (ADR-A79 is explicit that this compiler never silently
downgrades a configuration it cannot satisfy)."""

from __future__ import annotations

import string
from itertools import combinations

from rdflib import RDF, RDFS, SKOS, Graph, Literal, URIRef

from .functional import functional_value
from .boundary import BY_IDENTITY, PINNED, REFERENCE, MissingBoundaryShapeError, walk_ownership
from .capability import CapabilityCheckResult
from .model import BoundaryConflict, CrossAxisViolation, Diagnostic, ResolvedDimension
from .namespaces import DAL, FND, SH
from .operations import PAYLOAD_TEMPLATES
from .scopes import Target


def _is_versioned(graph: Graph, cls) -> bool:
    """A subclass of ``fnd:Versioned`` by IRI in the loaded graphs. Foundation is not imported."""
    return cls is not None and FND.Versioned in set(graph.transitive_objects(cls, RDFS.subClassOf))


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
    discipline = _local(_value(dimensions, "writeDiscipline"))
    appends = discipline in ("AppendVersions", "AppendRecords")

    # H2.6c, VH-Q3 and H2.6c-Q4: a class the loaded graphs make a subclass of fnd:Versioned, written by replace. Foundation is not
    # imported, the class is found by its IRI. A replace deletes the version before it, which fnd:supersededBy and ADR-A67 keep.
    if discipline == "InPlace" and _is_versioned(graph, target.cls):
        diagnostics.append(
            Diagnostic(
                kind="VersionedClassWrittenInPlace",
                severity="WARNING",
                target=str(target),
                message=(
                    "this target's class is a subclass of fnd:Versioned and dal:writeDiscipline is dal:InPlace, so every write "
                    "replaces the version before it and deletes it. Declare dal:AppendVersions to keep each version, or "
                    "dal:InPlace deliberately for a working draft that is not cited (H2.6c, VH-Q3)."
                ),
            )
        )

    # H2.6c: appending versions has no variant for a named-graph family (a graph per version is not built), writes under a
    # version row and so needs optimistic concurrency, and with no boundary needs a graph to hold the versions.
    if discipline == "AppendVersions":
        problem = None
        if boundary_local == "NamedGraphBoundary":
            problem = "a named-graph family would append one graph per version, which is not built"
        elif concurrency_local != "Optimistic":
            problem = f"the write is guarded by the identity's version row, so it needs dal:Optimistic and not dal:{concurrency_local}"
        elif boundary_local == "NoBoundary" and (boundary is None or boundary.extra.get("dataGraph") is None):
            problem = "a family with no boundary declares no dal:dataGraph to hold its versions, and the default graph is never written"
        if problem is not None:
            raise CrossAxisViolation(
                "AppendVersionsUnsupported",
                str(target),
                f"dal:AppendVersions is declared, and {problem}. Use dal:CompositePropertyBoundary, or dal:NoBoundary with a "
                "dal:dataGraph, under dal:Optimistic, or write in place.",
            )

    # H2.6f: the membership encoding. A delta is stored against the version before it, so it needs a family that appends versions,
    # and a checkpoint interval that makes sense.
    encoding = _local(_value(dimensions, "membershipEncoding"))
    if encoding not in ("FullMembership", "DeltaMembership"):
        raise CrossAxisViolation(
            "MembershipEncodingUnknown",
            str(target),
            f"dal:membershipEncoding is {encoding}, and the encodings are dal:FullMembership and dal:DeltaMembership (H2.6f).",
        )
    if encoding == "DeltaMembership" and discipline != "AppendVersions":
        raise CrossAxisViolation(
            "DeltaMembershipNeedsAppendVersions",
            str(target),
            "dal:DeltaMembership states a version's members as changes against the version before it, which only a family that "
            "declares dal:AppendVersions keeps. Declare dal:AppendVersions, or dal:FullMembership (H2.6f).",
        )
    interval = _value(dimensions, "checkpointEvery")
    value = interval.toPython() if hasattr(interval, "toPython") else interval
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise CrossAxisViolation(
            "CheckpointEveryInvalid",
            str(target),
            f"dal:checkpointEvery is {interval}, and it must be an integer of at least 1, the number of versions between full "
            "lists of members (H2.6f).",
        )

    # H2.6d, VH-Q5a: a family that wants no receipt writes in place. A version or a record takes its position and its transaction time
    # from the receipt, so an append discipline cannot do without one, and a stream (an append-only or event-grain family) is such a family.
    ordering_local = _local(ordering.value) if ordering else None
    if _local(receipts.value if receipts else None) == "NoReceipt" and (
        appends or concurrency_local == "AppendOnly" or (ordering_local == "EventGrain" and concurrency_local != "Optimistic")
    ):
        raise CrossAxisViolation(
            "NoReceiptWithAppendDiscipline",
            str(target),
            "dal:receiptModel dal:NoReceipt writes no receipt and no head, and this family appends (dal:AppendVersions, "
            "dal:AppendRecords, an append-only concurrency or a stream), where a version or a record takes its position and its "
            "transaction time from the receipt. Use dal:ReceiptOnly, or write in place (H2.6d, VH-Q5a).",
        )

    # H2.8c, D-9: a family that writes no receipt keeps no record of when each write took effect. A versioned class or a record class is
    # cited for what it said at a time, so writing it with no receipt is allowed and warned.
    if _local(receipts.value if receipts else None) == "NoReceipt" and (_is_versioned(graph, target.cls) or target.cls in record_classes(graph)):
        diagnostics.append(
            Diagnostic(
                kind="NoReceiptForRecord",
                severity="WARNING",
                target=str(target),
                message=(
                    f"dal:receiptModel dal:NoReceipt writes no receipt, and {target.cls} is "
                    f"{'versioned (a subclass of fnd:Versioned)' if _is_versioned(graph, target.cls) else 'a record class (dal:recordClass)'}, "
                    "whose instances are cited for what they said at a time. With no receipt nothing records when a write took effect or "
                    "which transaction made it. Use dal:ReceiptOnly, or dal:NoReceipt deliberately (H2.8c, D-9)."
                ),
            )
        )

    # Row 1: NoBoundary + Optimistic with no value guard. Appending versions guards on the version row instead.
    if boundary_local == "NoBoundary" and concurrency_local == "Optimistic" and discipline != "AppendVersions":
        if not concurrency.extra.get("valueGuardProperty"):
            raise CrossAxisViolation(
                "NoBoundaryConcurrencyConflict",
                str(target),
                "dal:NoBoundary combined with dal:Optimistic and no dal:valueGuardProperty: "
                "there is no aggregate to whole-graph replace. Declare a dal:valueGuardProperty "
                "for a value-based guard (guide §14.2), or declare a real boundary.",
            )
        # The values the guard reads and writes live in one named graph, never in the default graph, whose contents differ between
        # stores (static check S-1, H2.7-Q1, TD-43).
        if discipline != "AppendRecords" and (boundary is None or boundary.extra.get("dataGraph") is None):
            raise CrossAxisViolation(
                "MissingDataGraph",
                str(target),
                "dal:NoBoundary combined with dal:Optimistic and a dal:valueGuardProperty declares no dal:dataGraph. The value-based "
                "guard reads and writes the values of one named graph and never the default graph, since stores differ on what the "
                "default graph holds. Declare dal:dataGraph on the profile.",
            )

    # Row 2: CompositePropertyBoundary + ReceiptOnly. Not for a family that appends, where the history is in the data and a patch
    # log would repeat it (H2.6c-Q5, VH-Q5).
    if boundary_local == "CompositePropertyBoundary" and not appends and _local(receipts.value if receipts else None) == "ReceiptOnly":
        raise CrossAxisViolation(
            "CompositeBoundaryReceiptConflict",
            str(target),
            "dal:CompositePropertyBoundary with dal:ReceiptOnly: a composite-property aggregate's "
            "write is a bounded closure sweep, not a single named-graph replace, so a receipt-only "
            "model cannot audit what changed within the closure. Require at least dal:PatchLog.",
        )

    # H2.9, D-12 (a): the receipt-only writes of a composite family were reached only through dal:SnapshotPerRevision, which no
    # generated operation honours. They are deleted, so that model is refused on a composite family written in place until snapshots
    # are built (TD-46).
    if (
        boundary_local == "CompositePropertyBoundary" and not appends and concurrency_local == "Optimistic"
        and _local(receipts.value if receipts else None) == "SnapshotPerRevision"
    ):
        raise CrossAxisViolation(
            "CompositeBoundarySnapshotNotBuilt",
            str(target),
            "dal:CompositePropertyBoundary with dal:SnapshotPerRevision: no generated operation writes a snapshot of the aggregate per "
            "revision, and a composite family written in place has no write that records a receipt only. Use dal:PatchLog, or "
            "dal:NoReceipt deliberately, until snapshots are built (TD-46).",
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
        # The data graph comes first: it is what every composite operation reads and writes
        # (ADR-A122 decision 3, static check S-1).
        if boundary.extra.get("dataGraph") is None:
            raise CrossAxisViolation(
                "MissingDataGraph",
                str(target),
                "dal:CompositePropertyBoundary declares no dal:dataGraph. A composite family's aggregates live "
                "in one named graph, and every composite operation reads and writes that graph only, since "
                "stores differ on what the default graph holds. Declare dal:dataGraph on the profile.",
            )
        boundary_shape = boundary.extra.get("boundaryShape")
        if boundary_shape is None:
            raise MissingBoundaryShapeError(
                f"dal:CompositePropertyBoundary at {target} declares no dal:boundaryShape"
            )
        tree = boundary.extra["ownershipTree"]
        _check_tree(graph, target, boundary, tree, composite=True)
        diagnostics += check_reference_modes(graph, target, tree)
        reachable = tree.predicates()
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
    elif boundary_local == "NamedGraphBoundary" and boundary is not None:
        _check_graph_template(target, boundary)
    if boundary_local == "NamedGraphBoundary" and boundary is not None and boundary.extra.get("ownershipTree") is not None:
        # A named-graph profile that names a boundary shape is checked by the same rules, since the
        # shape defines the subjects a payload may contain (ADR-A122 decision 6).
        _check_tree(graph, target, boundary, boundary.extra["ownershipTree"], composite=False)
        diagnostics += check_reference_modes(graph, target, boundary.extra["ownershipTree"])

    # Last, so that a fixture written to isolate another row still reaches it. An unconditional write
    # (dal:ProvidedConcurrency or dal:LockingConcurrency, with a grain that is not event grain) names its graph from the root, so it needs a named-graph boundary. Any other
    # boundary used to fail to render at instantiate (TD-02). It is refused here instead.
    if (
        concurrency_local in ("ProvidedConcurrency", "LockingConcurrency")
        and _local(ordering.value if ordering else None) != "EventGrain"
        and boundary_local != "NamedGraphBoundary"
    ):
        raise CrossAxisViolation(
            "UnconditionalWriteRequiresNamedGraph",
            str(target),
            f"dal:{concurrency_local} generates an unconditional write into the root's named graph, and this "
            f"target's boundary is dal:{boundary_local}, which has no such graph. Use dal:NamedGraphBoundary, "
            "or dal:Optimistic with a version row and a guard.",
        )

    return diagnostics


# The characters ENCODE_FOR_URI leaves alone, and the percent sign it writes. A suffix that begins with
# one of these could be read as a continuation of the encoded root (ADR-A122 decision 8).
_ENCODED_ALPHABET = frozenset(string.ascii_letters + string.digits + "-._~%")


def _check_graph_template(target: Target, boundary: ResolvedDimension) -> None:
    """A named-graph family's ``dal:graphIriTemplate`` holds ``{id}`` exactly once, and any text after it
    starts with a character the encoding of the root never emits, so equal graph IRIs imply equal roots."""
    template = boundary.extra.get("graphIriTemplate")
    if template is None:
        return
    text = str(template)
    if text.count("{id}") != 1:
        raise CrossAxisViolation(
            "GraphIriTemplateInvalid",
            str(target),
            f"dal:graphIriTemplate {text!r} must contain {{id}} exactly once, where the root IRI, percent-encoded, goes.",
        )
    suffix = text.split("{id}", 1)[1]
    if suffix and suffix[0] in _ENCODED_ALPHABET:
        raise CrossAxisViolation(
            "GraphIriTemplateInvalid",
            str(target),
            f"dal:graphIriTemplate {text!r} continues after {{id}} with {suffix[0]!r}, which the encoding of a root can also "
            "produce, so two roots could name one graph. Start the text after {id} with a character such as '/'.",
        )


def check_graph_naming(families: dict[str, tuple[str, str]]) -> None:
    """Across named-graph families the text before ``{id}`` forms an antichain, so a graph IRI names one family
    and one root (ADR-A122 decision 8). ``families`` maps a family key to its label and prefix."""
    ordered = sorted(families.items(), key=lambda item: item[0])
    for (_, (label_a, prefix_a)), (_, (label_b, prefix_b)) in combinations(ordered, 2):
        if prefix_a.startswith(prefix_b) or prefix_b.startswith(prefix_a):
            raise CrossAxisViolation(
                "GraphIriTemplateOverlap",
                label_a,
                f"the graph prefixes {prefix_a!r} of {label_a} and {prefix_b!r} of {label_b} are nested or equal, so one graph "
                "could belong to either family. Give each family a prefix that is not a prefix of another's.",
            )


def reference_data_classes(graph: Graph) -> set[URIRef]:
    """The classes whose instances are reference data (ADR-A122 decision 4): ``skos:Concept``,
    ``skos:ConceptScheme``, every class a ``dal:ReferenceData`` declaration covers, and the classes the
    configuration asserts to be ``rdfs:subClassOf+`` any of these."""
    covered = {SKOS.Concept, SKOS.ConceptScheme}
    for declaration in graph.subjects(RDF.type, DAL.ReferenceData):
        covered.update(c for c in graph.objects(declaration, DAL.coversClass) if isinstance(c, URIRef))
    classes: set[URIRef] = set()
    for cls in covered:
        classes.update(c for c in graph.transitive_subjects(RDFS.subClassOf, cls) if isinstance(c, URIRef))
    return classes


def _owns_reference_data(boundary: ResolvedDimension) -> bool:
    value = boundary.extra.get("ownsReferenceData")
    return value is not None and str(value).lower() in {"true", "1"}


def _check_tree(graph: Graph, target: Target, boundary: ResolvedDimension, tree, *, composite: bool) -> None:
    """Rules 2 to 6 of sketch §5, in that order, over one classified boundary shape. A composite
    boundary must own an edge (rule 5). A named-graph boundary that names a shape may own none. The
    messages name a property shape by its predicate and shape and never by its blank node label, so a
    refusal reads the same on every run."""
    shape = tree.root_shape
    if tree.complex_paths:
        owner, _ = tree.complex_paths[0]
        raise CrossAxisViolation(
            "ComplexBoundaryPath",
            str(target),
            f"a property shape on {owner} has an sh:path that is neither an IRI nor [ sh:inversePath IRI ]. "
            "A boundary shape allows one step per property shape.",
        )
    if tree.unclassified:
        owner, _, predicate = tree.unclassified[0]
        raise CrossAxisViolation(
            "UnclassifiedBoundaryEdge",
            str(target),
            f"the property shape for {predicate} on {owner} leads to a node but declares no dal:ownership. "
            "Classify it as dal:Owned, dal:Reference or dal:Vocabulary.",
        )
    if tree.ownership_on_values:
        owner, _, predicate = tree.ownership_on_values[0]
        raise CrossAxisViolation(
            "OwnershipOnValueProperty",
            str(target),
            f"the property shape for {predicate} on {owner} is a value property (sh:datatype or "
            "sh:nodeKind sh:Literal) and cannot carry dal:ownership.",
        )
    if tree.unknown_modes:
        owner, predicate, declared = tree.unknown_modes[0]
        raise CrossAxisViolation(
            "ReferenceModeUnknown",
            str(target),
            f"the property shape for {predicate} on {owner} declares dal:referenceMode {declared}. "
            "Use dal:ByIdentity, or dal:Pinned on an edge to a versioned class.",
        )
    for edge in tree.edges:
        # A meaning-bearing edge from a versioned class is owned or pinned, never by identity (Foundation §4, ADR-A137).
        source_class = tree.root_class if edge.source_shape == tree.root_shape else graph.value(edge.source_shape, SH.targetClass)
        if (edge.kind == REFERENCE and edge.reference_mode == BY_IDENTITY
                and (edge.step.predicate, FND.meaningBearing, Literal(True)) in graph
                and _is_versioned(graph, source_class)):
            raise CrossAxisViolation(
                "MeaningBearingEdgeByIdentity",
                str(target),
                f"the property shape for {edge.step.predicate} on {edge.source_shape} is a reference by identity, "
                f"the predicate is fnd:meaningBearing and {source_class} is versioned, so editing the node at its end "
                "would change what a past version meant. Own the edge (dal:Owned), or pin it (dal:referenceMode dal:Pinned) "
                "to a version of its target.",
            )
        # H2.6e-Q2: an edge pinned to a version needs a target that has versions. A value property has no target class.
        if edge.reference_mode == PINNED and not _is_versioned(graph, edge.target_class):
            raise CrossAxisViolation(
                "PinnedReferenceToUnversionedClass",
                str(target),
                f"the property shape for {edge.step.predicate} on {edge.source_shape} is dal:Pinned, and its target class "
                f"{edge.target_class} is not a subclass of fnd:Versioned, so there is no version to pin to. "
                "Leave the edge dal:ByIdentity, or make the target class versioned.",
            )
    if composite and not tree.owned_edges():
        raise CrossAxisViolation(
            "CompositeBoundaryWithoutOwnedEdges",
            str(target),
            f"boundary shape {shape} owns no edge, so the aggregate is its root alone. "
            "Use dal:NamedGraphBoundary or dal:NoBoundary, or classify an edge dal:Owned.",
        )
    if not _owns_reference_data(boundary):
        reference_data = reference_data_classes(graph)
        for edge in tree.owned_edges():
            if edge.target_class in reference_data:
                raise CrossAxisViolation(
                    "OwnedReferenceData",
                    str(target),
                    f"the property shape for {edge.step.predicate} on {edge.source_shape} owns {edge.target_class}, "
                    "which is reference data. Classify the edge dal:Vocabulary, or declare dal:ownsReferenceData true "
                    "on the profile if this aggregate manages that vocabulary.",
                )


def record_classes(graph: Graph) -> set[URIRef]:
    """The classes whose instances are evidence of what they saw, as a configuration names them (H2.8c, D-15 (b)): every object of
    ``dal:recordClass`` on a profile, and the classes the configuration asserts to be ``rdfs:subClassOf+`` one of them. Read beside the
    subclasses of ``fnd:Evidence`` and ``fnd:DerivedArtefact``, for a class that is a record and is not modelled as evidence."""
    out: set[URIRef] = set()
    for named in graph.objects(None, DAL.recordClass):
        if isinstance(named, URIRef):
            out.update(c for c in graph.transitive_subjects(RDFS.subClassOf, named) if isinstance(c, URIRef))
    return out


def family_record_classes(graph: Graph, target: Target, tree) -> tuple:
    """The record classes (:func:`record_classes`) a family touches, its target class and the subject class of each edge of its boundary shape,
    in IRI order. The compiled profile states them (``dal:recordClass``), so a caller reads them without the configuration."""
    records = record_classes(graph)
    if not records:
        return ()
    touched = {target.cls}
    if tree is not None:
        touched.update(functional_value(graph, e.source_shape, SH.targetClass) for e in tree.node_edges())
    return tuple(sorted(str(c) for c in touched if c in records))


def check_reference_modes(graph: Graph, target: Target, tree) -> list[Diagnostic]:
    """The warning of H2.6e-Q3: an edge from a class that is evidence of what it saw (a subclass of ``fnd:Evidence`` or
    ``fnd:DerivedArtefact``, by IRI, or a record class the configuration names, H2.8c) to a versioned class, and by identity. A later
    version of the target changes what the evidence appears to have seen. A warning, so a deliberate choice compiles."""
    out: list[Diagnostic] = []
    records = record_classes(graph)
    for edge in tree.node_edges():
        if edge.reference_mode != BY_IDENTITY or not _is_versioned(graph, edge.target_class):
            continue
        source_class = functional_value(graph, edge.source_shape, SH.targetClass)
        ancestors = set(graph.transitive_objects(source_class, RDFS.subClassOf)) if source_class is not None else set()
        if not ancestors & {FND.Evidence, FND.DerivedArtefact} and source_class not in records:
            continue
        out.append(
            Diagnostic(
                kind="EvidenceEdgeByIdentity",
                severity="WARNING",
                target=str(target),
                message=(
                    f"the property shape for {edge.step.predicate} on {edge.source_shape} is by identity, its subject class "
                    f"{source_class} is evidence (a subclass of fnd:Evidence or fnd:DerivedArtefact, or a dal:recordClass) and its target class "
                    f"{edge.target_class} is versioned, so the evidence names whichever version is current and not the one it saw. "
                    "Declare dal:referenceMode dal:Pinned, or dal:ByIdentity deliberately (H2.6e)."
                ),
            )
        )
    return out


def check_references_to_owned(graph: Graph, target: Target, boundary: ResolvedDimension) -> list[Diagnostic]:
    """The warning of sketch §5: a property shape outside an aggregate's owned shapes points at a class the
    aggregate owns, other than its root. A deleted member leaves such a reference dangling, so references
    from outside should target the root (ADR-A122 decision 5)."""
    tree = boundary.extra.get("ownershipTree")
    if tree is None:
        return []
    inside = set(tree.shapes)
    owned = tree.member_classes() - ({tree.root_class} if tree.root_class is not None else set())
    out: list[Diagnostic] = []
    for shape in sorted(set(graph.subjects(SH.property, None)), key=str):
        if shape in inside:
            continue
        for property_shape in graph.objects(shape, SH.property):
            path = functional_value(graph, property_shape, SH.path)
            named = functional_value(graph, property_shape, SH["class"])
            node = functional_value(graph, property_shape, SH.node)
            pointed = {named} | ({functional_value(graph, node, SH.targetClass)} if node is not None else set())
            for cls in sorted((c for c in pointed if c in owned), key=str):
                label = path if isinstance(path, URIRef) else "a property"
                out.append(
                    Diagnostic(
                        kind="ReferenceToOwnedClass",
                        severity="WARNING",
                        target=str(target),
                        message=(
                            f"the property shape for {label} on {shape} points at {cls}, which {tree.root_shape} owns. "
                            f"References from outside an aggregate should target its root ({tree.root_class}), since a "
                            "deleted member leaves the reference dangling."
                        ),
                    )
                )
    return sorted(out, key=lambda d: d.message)


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

    # TD-46: the receipt model that no template honours. A snapshot copies the aggregate per revision and no template writes one, so a
    # profile that chooses it still records a receipt only. H1.4c: a declaration the compiler cannot honour is a warning or a refusal,
    # never silent. dal:PatchLog is honoured by the in-place writes since H2.6d, and dal:NoReceipt is a model of its own.
    receipt_model = _local(_value(dimensions, "receiptModel"))
    if receipt_model == "SnapshotPerRevision":
        out.append(_warning(
            "ReceiptModelNotHonoured", target,
            "dal:receiptModel dal:SnapshotPerRevision declares a snapshot of the aggregate per revision, but no generated operation "
            "writes it. The compiled profile records the declaration and the operations write a receipt only (TD-46). "
            "Do not rely on as-of reads from this profile.",
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
                function = functional_value(graph, scheme, DAL.digestFunction) if scheme is not None else None
                width = functional_value(graph, scheme, DAL.digestWidthBits) if scheme is not None else None
                encoding = functional_value(graph, scheme, DAL.digestEncoding) if scheme is not None else None
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


def check_patch_log_written(target: Target, dimensions: dict[str, ResolvedDimension], operations) -> list[Diagnostic]:
    """D-10 (H2.8b): a family that declares dal:PatchLog but has no generated operation that writes a patch log. Only the in-place writes of
    an optimistic named-graph or composite family do. An append discipline, an append-only concurrency, an unconditional write and a value-guarded
    write record a receipt at most, so the declaration is recorded and not honoured (TD-46)."""
    if _local(_value(dimensions, "receiptModel")) != "PatchLog" or any("-patch-log" in op.template_id for op in operations):
        return []
    return [_warning(
        "PatchLogNotWritten", target,
        "dal:receiptModel dal:PatchLog declares that each change is recorded as added and retracted triples, but no generated operation of this "
        "family writes a patch log. Only the create, replace and tombstone of an optimistic named-graph or composite family do. An append "
        "discipline, an append-only concurrency, an unconditional write and a value-guarded write do not. The declaration is recorded in the "
        "compiled profile and not applied.",
    )]


def check_payload_bound(
    target: Target, dimensions: dict[str, ResolvedDimension], operations, *, warn: bool, graph_names: str = ""
) -> list[Diagnostic]:
    """H2.8b (ADR-A123 decision 6, H2-Q2): a named-graph family with a payload operation and no ``dal:boundaryShape`` has the form checks of
    a payload and not the check that every subject belongs to the aggregate. ``INFO`` by default, ``WARNING`` under
    ``compile --warn-unbounded-payload``."""
    boundary = dimensions["aggregateBoundary"]
    if not str(boundary.value).endswith("NamedGraphBoundary") or boundary.extra.get("ownershipTree") is not None:
        return []
    if not any(op.template_id.startswith(PAYLOAD_TEMPLATES) for op in operations):
        return []
    message = (
        f"{target} is a named-graph family with payload operations and no dal:boundaryShape, so a caller can check the form of a payload and "
        "not that every subject belongs to the aggregate. Declare a dal:boundaryShape to have the payload-check query generated."
    )
    if warn:
        return [Diagnostic(kind="UnboundedPayload", severity="WARNING", target=str(target), message=message)]
    return [Diagnostic(kind="UnboundedPayload", severity="INFO", target=str(target), message=message)]


def check_guards_off(target: Target) -> list[Diagnostic]:
    """H2.8b (ADR-A123, addendum of 2026-10-12): a run with the parameter guards off names the caller's obligation."""
    return [Diagnostic(
        kind="ParameterGuardsOff", severity="INFO", target=str(target),
        message=(
            "compiled with --no-parameter-guards, so no generated operation tests its parameters. The caller must check every one before "
            "sending: each present and of its declared kind, an xsd:long exactly, a literal and not an IRI where the contract says so, and a "
            "caller-named graph equal to the naming rule. A request that leaves out $root can write every aggregate whose version row matches. "
            "The caller library (lattice_persistence.check) does these checks (TD-34, TD-44)."
        ),
    )]


def check_no_receipt_meta_shards(compiled) -> None:
    """D-11 (H2.8b): a dal:NoReceipt family keeps its version row in a meta graph and writes no receipt for it. The gap scan of another
    family that shares the meta graph reads every version row there and counts receipts for it, so it reports each row of the NoReceipt family as
    a gap. Refused, since the audit would fail on every run."""
    by_graph: dict[str, list] = {}
    for ct in compiled:
        for op in ct.operations:
            binding = next((b for b in op.bindings if b.name == "metaGraphPrefix"), None)
            if binding is not None:
                by_graph.setdefault(str(binding.value), []).append(ct)
                break
    for graph_name, targets in sorted(by_graph.items()):
        quiet = [t for t in targets if _local(t.dimensions["receiptModel"].value) == "NoReceipt"]
        scanned = [t for t in targets if t not in quiet and any(op.template_id.startswith("gap-scan-audit") for op in t.operations)]
        if quiet and scanned:
            raise CrossAxisViolation(
                "NoReceiptSharesMetaShard", str(quiet[0].target),
                f"the family writes no receipt (dal:NoReceipt) and shares the meta graph {graph_name} with {scanned[0].target}, whose gap scan reads every "
                "version row of that graph and would report each row of this family as a gap. Give them different meta shards (dal:metaShards) or the "
                "same receipt model.",
            )


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
    trees: list[tuple[URIRef, object]] = []  # (boundary shape, tree) of every composite profile
    own_strategy: dict[URIRef, URIRef] = {}
    for profile in graph.subjects(RDF.type, DAL.AggregateBoundaryProfile):
        scope = functional_value(graph, profile, DAL.appliesTo)
        if scope is None:
            continue
        cls = functional_value(graph, scope, DAL.targetClass)
        strategy = functional_value(graph, profile, DAL.strategy)
        if cls is not None and strategy is not None:
            own_strategy[cls] = strategy

    for profile in sorted(graph.subjects(RDF.type, DAL.AggregateBoundaryProfile), key=str):
        strategy = functional_value(graph, profile, DAL.strategy)
        if strategy != DAL.CompositePropertyBoundary:
            continue
        shape = functional_value(graph, profile, DAL.boundaryShape)
        if shape is None:
            continue
        # every member class at any depth of the classified tree (ADR-A122 decision 2)
        tree = walk_ownership(graph, shape)
        trees.append((shape, tree))
        for member_cls in sorted(tree.member_classes(), key=str):
            member_strategy = own_strategy.get(member_cls)
            if member_strategy and member_strategy != DAL.NoBoundary:
                raise BoundaryConflict(
                    f"{member_cls} is a composite member of {shape}'s closure, but also declares "
                    f"its own boundary strategy {member_strategy}. A resource cannot belong to two "
                    "aggregates under incompatible boundary strategies (sketch §4.6)."
                )
    # Rule 9, after rule 8 so that one fixture trips one rule: no class belongs to two composite
    # aggregates, whether as a member of both or as a member of one and the root of the other.
    for (shape_a, tree_a), (shape_b, tree_b) in combinations(trees, 2):
        roots_b = {tree_b.root_class} if tree_b.root_class is not None else set()
        roots_a = {tree_a.root_class} if tree_a.root_class is not None else set()
        shared = (tree_a.member_classes() & (tree_b.member_classes() | roots_b)) | (tree_b.member_classes() & roots_a)
        if shared:
            raise CrossAxisViolation(
                "OverlappingOwnership",
                str(shape_a),
                f"{', '.join(sorted(str(c) for c in shared))} is owned by both {shape_a} and {shape_b}. "
                "A node belongs to one aggregate.",
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
    "check_graph_naming",
    "check_capability",
]
