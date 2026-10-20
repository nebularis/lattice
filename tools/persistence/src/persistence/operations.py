# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Template selection (sketch §5.2 "Select" stage): a fixed lookup table
keyed by resolved dimension values, never a live template file read. This
stage cannot fail once validation has passed (ADR-A79 point 3): it is a
lookup, not a decision with its own failure modes.

Every operation's parameter bindings are configuration-time constants only
(a shard number, a graph-IRI prefix, a log-bucket property IRI). Genuine
SPARQL variables (``$root``, ``$expectedSeq``, the payload) are never
computed here; they stay unbound in the emitted templates for the
``instantiate`` stage to leave untouched (sketch §5.2, ADR-A79 point 3).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

from rdflib import URIRef

from .model import ResolvedDimension
from .scopes import Target
from .terms import Integer, Iri, Literal, PropertyPath


@dataclass(frozen=True)
class ParameterBinding:
    name: str
    param_type: str  # "Iri" | "Literal" | "Integer" | "String" | "PropertyPath"
    value: Any


@dataclass(frozen=True)
class GeneratedOperation:
    operation: str
    template_id: str
    bindings: list[ParameterBinding] = field(default_factory=list)


DEFAULT_META_SHARDS = 64


def _local(value) -> str | None:
    return str(value).rsplit("#", 1)[-1] if value is not None else None


def _family_token(cls) -> str:
    """A class IRI's local name as a lowercase ``[a-z0-9-]`` token, for
    the fixed event-graph prefix (guide §2.3)."""
    local = re.split(r"[#/:]", str(cls).rstrip("/#"))[-1]
    return re.sub(r"[^a-z0-9-]", "-", local.lower()) or "family"


def default_graph_template(cls) -> str:
    """The graph template of a named-graph family that declares none: ``urn:g:<family token>/{id}``."""
    return f"urn:g:{_family_token(cls)}/{{id}}"


def _shard_for(target: Target, shard_count: int) -> int:
    key = str(target)
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") % max(shard_count, 1)


def select_operations(
    target: Target,
    dimensions: dict[str, ResolvedDimension],
    uniqueness: list[dict],
) -> list[GeneratedOperation]:
    boundary = _local(dimensions["aggregateBoundary"].value)
    concurrency = _local(dimensions["concurrencyProfile"].value)
    ordering = _local(dimensions["orderingGrain"].value)
    # dal:writeDiscipline (H2.6c). The default, dal:InPlace, is every selection below that is not one of the two branches it names.
    discipline = _local(dimensions["writeDiscipline"].value)
    # dal:receiptModel (H2.6d). dal:PatchLog selects the variants that write delta graphs, and dal:NoReceipt the variants that write no
    # receipt. The validator has refused dal:NoReceipt with an append discipline. Any other model writes the receipt, as it always has.
    receipt_model = _local(dimensions["receiptModel"].value)
    receipt_tag = {"PatchLog": "-patch-log", "NoReceipt": "-no-receipt"}.get(receipt_model, "")
    meta = dimensions["metaTopology"]
    shard_count = int(meta.extra.get("metaShards", DEFAULT_META_SHARDS))
    shard = _shard_for(target, shard_count)
    # dal:epochGuardScope (persistence-compiler-iri-sync Slice 1). "urn:g:dataset"
    # is a fixed, well-known graph and subject IRI, exactly like the
    # existing "urn:g:txn"/"urn:g:txlog/" constants below: it is not
    # per-target, so it is not derived from any dal: property, matching
    # guide §19.1's worked example. Not independently configurable in
    # this slice -- see persistence-compiler-iri-sync's status record.
    dataset_level_guard = _local(dimensions["epochGuardScope"].value) == "DatasetLevelGuard"
    guard_suffix = "-dataset-guard" if dataset_level_guard else ""
    # dal:firstWrite (Slice 2): a pre-created row exists from id allocation,
    # so the target never gets create-if-absent. It gets the bootstrap
    # operation instead, which the caller runs when the id is allocated.
    pre_created_row = _local(dimensions["firstWrite"].value) == "PreCreatedRow"
    bootstrap_op = GeneratedOperation(
        "bootstrap-version-row", f"bootstrap-version-row{guard_suffix}.mustache", []
    )

    ops: list[GeneratedOperation] = []
    # Fixed, well-known infrastructure graphs (rdf-sparql-patterns-guide.md
    # §2.3). None is derived from a dal: property yet; see
    # tools/persistence/README.md "Known limitations".
    common_bindings = [
        ParameterBinding("shard", "Integer", Integer.encode(shard)),
        ParameterBinding(
            "logGraphPrefix", "Iri", Iri.encode("urn:g:txlog/")
        ),
        ParameterBinding("txnGraph", "Iri", Iri.encode("urn:g:txn")),
        ParameterBinding("keysGraph", "Iri", Iri.encode("urn:g:keys")),
        # persistence-compiler-iri-sync Slice 5: a fixed constant, like
        # every other infrastructure graph above -- no dal: property names
        # it yet (tools/persistence/README.md "Known limitations").
        ParameterBinding("keyQuarantineGraph", "Iri", Iri.encode("urn:g:key-quarantine")),
        ParameterBinding("retentionGraph", "Iri", Iri.encode("urn:g:retention")),
        ParameterBinding("pinnedGraph", "Iri", Iri.encode("urn:g:txlog/pinned")),
        ParameterBinding(
            "eventGraphPrefix", "Iri", Iri.encode(f"urn:g:events/{_family_token(target.cls)}/")
        ),
        ParameterBinding("metaGraphPrefix", "Iri", Iri.encode(f"urn:g:meta/{shard}")),
        ParameterBinding("datasetGraph", "Iri", Iri.encode("urn:g:dataset")),
        ParameterBinding("datasetNode", "Iri", Iri.encode("urn:g:dataset")),
    ]

    # Computed unconditionally whenever the boundary is NamedGraphBoundary,
    # so it is available to every operation that needs it, not only the
    # Optimistic/CAS ones (an unconditional write under ProvidedConcurrency
    # or LockingConcurrency to a NamedGraphBoundary target still needs to
    # know which graph to write into).
    if boundary == "NamedGraphBoundary":
        boundary_dim = dimensions["aggregateBoundary"]
        # The graph is the prefix, the root IRI encoded with ENCODE_FOR_URI, and the suffix, so
        # distinct roots name distinct graphs (ADR-A122 decision 8). The validator has already
        # checked that the template holds one {id} and that its suffix starts with a character the
        # encoding never emits.
        template = str(boundary_dim.extra.get("graphIriTemplate", default_graph_template(target.cls)))
        graph_prefix, _, graph_suffix = template.partition("{id}")
        common_bindings = common_bindings + [
            # String fragments interpolated inside an existing CONCAT(...),
            # not standalone IRI terms: Literals, not Iris.
            ParameterBinding("graphPrefix", "String", Literal.encode(graph_prefix)),
            ParameterBinding("graphSuffix", "String", Literal.encode(graph_suffix)),
        ]

    if discipline == "AppendVersions":
        # Nothing is swept, so there is no boundary path and no tombstone, which would sweep the history. The validator has refused
        # every configuration this cannot serve (AppendVersionsUnsupported): optimistic concurrency, and a composite family or a
        # family with no boundary and a data graph. The first version is written at seq 0 onto a row that bootstrap-version-row
        # created, so the version row's current version is only ever set by one operation, whatever dal:firstWrite says.
        data_graph = ParameterBinding("dataGraph", "Iri", Iri.encode(str(dimensions["aggregateBoundary"].extra["dataGraph"])))
        ops.append(GeneratedOperation(bootstrap_op.operation, bootstrap_op.template_id, common_bindings))
        # dal:membershipEncoding (H2.6f). Under dal:DeltaMembership the write states what changed, and the family gets the query that
        # resolves a version's members from the chain, which holds the data graph and nothing else.
        delta = _local(dimensions["membershipEncoding"].value) == "DeltaMembership"
        delta_tag = "-delta" if delta else ""
        ops.append(GeneratedOperation("append-version", f"append-version{delta_tag}{guard_suffix}.mustache", common_bindings + [data_graph]))
        if delta:
            ops.append(GeneratedOperation("members", "members.mustache", [data_graph]))
    elif concurrency == "Optimistic" and discipline != "AppendRecords":
        if boundary == "NamedGraphBoundary":
            cas_template = (
                f"cas-replace-named-graph{receipt_tag}-dataset-guard.mustache" if dataset_level_guard
                else f"cas-replace-named-graph{receipt_tag}.mustache"
            )
            tombstone_template = (
                f"tombstone-delete-named-graph{receipt_tag}-dataset-guard.mustache" if dataset_level_guard
                else f"tombstone-delete-named-graph{receipt_tag}.mustache"
            )
            if pre_created_row:
                ops.append(GeneratedOperation(bootstrap_op.operation, bootstrap_op.template_id, common_bindings))
            else:
                ops.append(GeneratedOperation(
                    "create-if-absent", f"create-if-absent-named-graph{receipt_tag}{guard_suffix}.mustache", common_bindings
                ))
            ops.append(GeneratedOperation("cas-replace", cas_template, common_bindings))
            ops.append(GeneratedOperation("tombstone-delete", tombstone_template, common_bindings))
        elif boundary == "CompositePropertyBoundary":
            # A property path cannot be a variable, so the path that reaches the aggregate's
            # members is a compile-time slot, not a request-time $-variable. It is compiled from
            # the owned edges of the boundary shape's classified tree (persistence.boundary,
            # persistence.paths), and the validator has already refused a composite profile with
            # no data graph, no shape or no owned edge. Every composite pattern sits in the
            # profile's data graph and never in the default graph (static check S-1).
            boundary_dim = dimensions["aggregateBoundary"]
            owned_path = boundary_dim.extra["ownershipTree"].owned_path()
            data_graph = ParameterBinding("dataGraph", "Iri", Iri.encode(str(boundary_dim.extra["dataGraph"])))
            bindings = common_bindings + [ParameterBinding("ownedPath", "PropertyPath", PropertyPath.encode(owned_path)), data_graph]
            composite_template = (
                f"cas-replace-composite-property{receipt_tag}-dataset-guard.mustache" if dataset_level_guard
                else f"cas-replace-composite-property{receipt_tag}.mustache"
            )
            tombstone_template = (
                f"tombstone-delete-composite{receipt_tag}-dataset-guard.mustache" if dataset_level_guard
                else f"tombstone-delete-composite{receipt_tag}.mustache"
            )
            if pre_created_row:
                ops.append(GeneratedOperation(bootstrap_op.operation, bootstrap_op.template_id, bindings))
            else:
                # a create sweeps nothing, so it needs the data graph and no path
                create_bindings = common_bindings + [data_graph]
                ops.append(GeneratedOperation(
                    "create-if-absent", f"create-if-absent-composite{receipt_tag}{guard_suffix}.mustache", create_bindings
                ))
            ops.append(GeneratedOperation("cas-replace", composite_template, bindings))
            ops.append(GeneratedOperation("tombstone-delete", tombstone_template, bindings))
        elif boundary == "NoBoundary":
            guard_prop = dimensions["concurrencyProfile"].extra.get("valueGuardProperty")
            bindings = common_bindings + (
                [ParameterBinding("guardProperty", "Iri", Iri.encode(str(guard_prop)))]
                if guard_prop is not None
                else []
            )
            ops.append(GeneratedOperation("cas-replace", "cas-replace-value-guard.mustache", bindings))
    elif concurrency == "AppendOnly" or ordering == "EventGrain" or discipline == "AppendRecords":
        # A stream's version row is bootstrapped eagerly before any append
        # (guide §10.1): a lazy first write would reintroduce the race.
        ops.append(GeneratedOperation(bootstrap_op.operation, bootstrap_op.template_id, common_bindings))
        ops.append(GeneratedOperation("append", f"append-event{guard_suffix}.mustache", common_bindings))
    else:
        # ProvidedConcurrency or LockingConcurrency (a marker only, sketch
        # §3.3.1): no guard is generated either way.
        ops.append(GeneratedOperation("unconditional-write", "unconditional-write.mustache", common_bindings))

    for constraint in uniqueness:
        key_bindings = common_bindings + [
            ParameterBinding("constraintId", "String", Literal.encode(constraint["constraintId"])),
        ]
        # persistence-compiler-iri-sync Slice 5: dal:ClaimScheme rotation
        # (guide §6.1). Two active scheme versions mean the guarded write
        # must guard-and-insert both claim IRIs in one operation.
        write_template = (
            "key-claim-write-dual.mustache" if constraint.get("dualClaimScheme") else "key-claim-write.mustache"
        )
        ops.append(
            GeneratedOperation(f"key-claim-write:{constraint['constraintId']}", write_template, key_bindings)
        )
        ops.append(
            GeneratedOperation(
                f"key-claim-retire:{constraint['constraintId']}", "key-claim-retire.mustache", key_bindings
            )
        )
        # persistence-compiler-iri-sync Slice 5 (decision 1, Option A): the
        # guarded write above always prevents the race regardless of
        # dal:onViolation; the policy instead selects which reconciler
        # operation runs to detect, and where named, remediate whatever
        # slips past it anyway -- bulk loads, administrative LOAD, restores
        # (guide §7.5: "the reconciler is never the only strategy, and it
        # is never absent"). Undeclared dal:onViolation defaults to
        # dal:Reject, the same explicit-baseline-default convention as
        # every other dimension in this compiler.
        on_violation = _local(constraint.get("onViolation")) or "Reject"
        if on_violation == "Merge":
            merge_bindings = key_bindings + [
                ParameterBinding("mergeRelation", "Iri", Iri.encode(str(constraint["mergeRelation"]))),
            ]
            ops.append(
                GeneratedOperation(
                    f"key-claim-merge-rewrite:{constraint['constraintId']}",
                    "key-claim-merge-rewrite.mustache", merge_bindings,
                )
            )
        elif on_violation == "Quarantine":
            ops.append(
                GeneratedOperation(
                    f"key-claim-quarantine:{constraint['constraintId']}",
                    "key-claim-quarantine.mustache", key_bindings,
                )
            )
        else:
            ops.append(
                GeneratedOperation(
                    f"key-claim-duplicate-audit:{constraint['constraintId']}",
                    "key-claim-duplicate-audit.mustache", key_bindings,
                )
            )

    # dal:registryGraph (Slice 2) rides on every audit as a binding, so the
    # caller that renders the logGraphs request-time slot knows which
    # registry lists the family's log buckets (guide §24.2).
    audit_bindings = list(common_bindings)
    registry = dimensions["registryGraph"].value
    if registry is not None:
        audit_bindings.append(ParameterBinding("registryGraph", "Iri", Iri.encode(str(registry))))
    # The audits that read receipts have nothing to read for a family that writes none (dal:NoReceipt), and the gap scan would report every
    # one of its version rows as a gap. The fork audit reads the claims, which such a family still writes.
    has_receipts = receipt_model != "NoReceipt"
    if has_receipts:
        ops.append(GeneratedOperation("gap-scan-audit", "gap-scan-audit.mustache", audit_bindings))
    ops.append(GeneratedOperation("fork-detection-audit", "fork-detection-audit.mustache", audit_bindings))
    if has_receipts:
        # Receipt-side forms of the fork audit, which survive txn-claim pruning
        # (guide §24.2).
        ops.append(GeneratedOperation("revision-multi-txn-audit", "revision-multi-txn-audit.mustache", audit_bindings))
        ops.append(GeneratedOperation("txn-multi-revision-audit", "txn-multi-revision-audit.mustache", audit_bindings))

    return ops


__all__ = ["ParameterBinding", "GeneratedOperation", "select_operations", "DEFAULT_META_SHARDS"]
