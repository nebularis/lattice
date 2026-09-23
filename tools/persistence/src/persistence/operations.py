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
from .terms import Integer, Iri, Literal


@dataclass(frozen=True)
class ParameterBinding:
    name: str
    param_type: str  # "Iri" | "Literal" | "Integer" | "String"
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
        template = boundary_dim.extra.get("graphIriTemplate", f"urn:g:{target.cls}/")
        graph_prefix = str(template).split("{", 1)[0]
        common_bindings = common_bindings + [
            # A string fragment interpolated inside an existing CONCAT(...),
            # not a standalone IRI term: Literal, not Iri.
            ParameterBinding("graphPrefix", "String", Literal.encode(graph_prefix)),
        ]

    if concurrency == "Optimistic":
        if boundary == "NamedGraphBoundary":
            cas_template = (
                "cas-replace-named-graph-dataset-guard.mustache" if dataset_level_guard
                else "cas-replace-named-graph.mustache"
            )
            tombstone_template = (
                "tombstone-delete-named-graph-dataset-guard.mustache" if dataset_level_guard
                else "tombstone-delete-named-graph.mustache"
            )
            if pre_created_row:
                ops.append(GeneratedOperation(bootstrap_op.operation, bootstrap_op.template_id, common_bindings))
            else:
                ops.append(GeneratedOperation(
                    "create-if-absent", f"create-if-absent-named-graph{guard_suffix}.mustache", common_bindings
                ))
            ops.append(GeneratedOperation("cas-replace", cas_template, common_bindings))
            ops.append(GeneratedOperation("tombstone-delete", tombstone_template, common_bindings))
        elif boundary == "CompositePropertyBoundary":
            # SPARQL 1.1 property paths support only *, +, ? repetition, not
            # bounded {n,m} (there is no such production in the grammar),
            # and a path cannot itself be a variable. The composite
            # property is therefore a compile-time Mustache slot, not a
            # request-time $-variable, populated in resolver.py once the
            # boundary shape is walked (persistence.resolver,
            # persistence.boundary). Depth is enforced at compile time by
            # the shape walk's own cycle detection, not by a runtime bound.
            boundary_dim = dimensions["aggregateBoundary"]
            composite_properties = boundary_dim.extra.get("compositeProperties", [])
            first_property = composite_properties[0] if composite_properties else None
            bindings = common_bindings + (
                [ParameterBinding("compositeProperty", "Iri", Iri.encode(str(first_property)))]
                if first_property is not None
                else []
            )
            composite_template = (
                "cas-replace-composite-property-dataset-guard.mustache" if dataset_level_guard
                else "cas-replace-composite-property.mustache"
            )
            if pre_created_row:
                ops.append(GeneratedOperation(bootstrap_op.operation, bootstrap_op.template_id, bindings))
            ops.append(GeneratedOperation("cas-replace", composite_template, bindings))
        elif boundary == "NoBoundary":
            guard_prop = dimensions["concurrencyProfile"].extra.get("valueGuardProperty")
            bindings = common_bindings + (
                [ParameterBinding("guardProperty", "Iri", Iri.encode(str(guard_prop)))]
                if guard_prop is not None
                else []
            )
            ops.append(GeneratedOperation("cas-replace", "cas-replace-value-guard.mustache", bindings))
    elif concurrency == "AppendOnly" or ordering == "EventGrain":
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
        ops.append(
            GeneratedOperation(
                f"key-claim-write:{constraint['constraintId']}", "key-claim-write.mustache", key_bindings
            )
        )
        ops.append(
            GeneratedOperation(
                f"key-claim-retire:{constraint['constraintId']}", "key-claim-retire.mustache", key_bindings
            )
        )

    # dal:registryGraph (Slice 2) rides on every audit as a binding, so the
    # caller that renders the logGraphs request-time slot knows which
    # registry lists the family's log buckets (guide §24.2).
    audit_bindings = list(common_bindings)
    registry = dimensions["registryGraph"].value
    if registry is not None:
        audit_bindings.append(ParameterBinding("registryGraph", "Iri", Iri.encode(str(registry))))
    ops.append(GeneratedOperation("gap-scan-audit", "gap-scan-audit.mustache", audit_bindings))
    ops.append(GeneratedOperation("fork-detection-audit", "fork-detection-audit.mustache", audit_bindings))
    # Receipt-side forms of the fork audit, which survive txn-claim pruning
    # (guide §24.2).
    ops.append(GeneratedOperation("revision-multi-txn-audit", "revision-multi-txn-audit.mustache", audit_bindings))
    ops.append(GeneratedOperation("txn-multi-revision-audit", "txn-multi-revision-audit.mustache", audit_bindings))

    return ops


__all__ = ["ParameterBinding", "GeneratedOperation", "select_operations", "DEFAULT_META_SHARDS"]
