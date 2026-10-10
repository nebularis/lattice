# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The declaration/implementation gap, as data (formal-methods track H, slice H1.4b).

A configuration declares more than the generated SPARQL implements. A declared shard count is
recorded and not applied, a boundary shape is read for one property, and a restore runbook is
named and never run. This module lists, for each compiled target, every such gap that applies, and
says whose obligation it is:

``unimplemented``
    the compiler or its templates do not do what the declaration says. A register row and the
    slice that removes it are named.
``caller``
    the generated SPARQL assumes the caller does something it cannot enforce.
``housekeeping``
    the work belongs to the housekeeping component (ADR-A80), which this compiler does not generate.

The report is informational. It reads compiled targets, needs no backend, and is sorted so two runs
are byte-identical. Each rule is a function over one :class:`CompiledTarget`, kept in :data:`RULES`
so a test can name every entry. A slice that closes a gap removes its rule here, and the entry it
expected from the test, in the same commit.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable, Iterable

from rdflib import BNode

from .compiler import CompiledTarget
from .operations import _local

UNIMPLEMENTED = "unimplemented"
CALLER = "caller"
HOUSEKEEPING = "housekeeping"


@dataclass(frozen=True, order=True)
class Gap:
    """One entry of the report."""

    gap: str
    target: str
    obligation: str
    reference: str  # the register row, ADR or README section that records it
    closes_in: str  # the slice that removes it, or "not planned"
    message: str

    def __str__(self) -> str:
        return f"GAP [{self.gap}] {self.target}: {self.message} ({self.obligation}, {self.reference}, closes in {self.closes_in})"


Rule = Callable[[CompiledTarget], Iterable[Gap]]


def _boundary(ct: CompiledTarget) -> str | None:
    return _local(ct.dimensions["aggregateBoundary"].value)


def _operation_names(ct: CompiledTarget) -> set[str]:
    return {op.operation for op in ct.operations}


def _gap(ct: CompiledTarget, gap: str, obligation: str, reference: str, closes_in: str, message: str) -> Gap:
    return Gap(gap, str(ct.target), obligation, reference, closes_in, message)


def _short(iri) -> str:
    text = str(iri)
    return text.rsplit("#", 1)[-1].rsplit("/", 1)[-1] or text


def _composite_ownership_assumed(ct: CompiledTarget) -> Iterable[Gap]:
    dim = ct.dimensions["aggregateBoundary"]
    if _boundary(ct) != "CompositePropertyBoundary":
        return
    edges = [e for e in dim.extra.get("compositeEdgeProperties", []) if not isinstance(e, BNode)]
    if edges:
        yield _gap(
            ct, "CompositeOwnershipAssumed", UNIMPLEMENTED, "TD-35", "HO5",
            f"the replace follows {_short(edges[0])} from {_short(dim.extra.get('boundaryShape'))}, which is assumed owned. "
            "Nothing declares ownership, so a reference given sh:node is swept with the aggregate",
        )


def _composite_inverse_path_misread(ct: CompiledTarget) -> Iterable[Gap]:
    dim = ct.dimensions["aggregateBoundary"]
    if _boundary(ct) != "CompositePropertyBoundary":
        return
    if any(isinstance(p, BNode) for p in dim.extra.get("compositeProperties", [])):
        yield _gap(
            ct, "CompositeInversePathMisread", UNIMPLEMENTED, "TD-37", "HO5",
            f"a property shape under {_short(dim.extra.get('boundaryShape'))} has an sh:path that is not an IRI "
            "(for example an sh:inversePath), which the walk records as a property and the template renders as one",
        )


def _composite_default_graph(ct: CompiledTarget) -> Iterable[Gap]:
    if _boundary(ct) == "CompositePropertyBoundary" and "cas-replace" in _operation_names(ct):
        yield _gap(
            ct, "CompositeUsesDefaultGraph", UNIMPLEMENTED, "TD-40", "HO5",
            "the composite replace sweeps and writes the default graph, whose contents differ between stores (static check S-1)",
        )


def _composite_lifecycle(ct: CompiledTarget) -> Iterable[Gap]:
    if _boundary(ct) != "CompositePropertyBoundary" or _local(ct.dimensions["concurrencyProfile"].value) != "Optimistic":
        return
    missing = ["tombstone-delete"]
    if _local(ct.dimensions["firstWrite"].value) != "PreCreatedRow":
        missing.insert(0, "create-if-absent")
    yield _gap(
        ct, "CompositeNoLifecycleOperations", UNIMPLEMENTED, "TD-04", "HO7",
        f"a composite aggregate has no {' and no '.join(missing)} operation",
    )


def _graph_named_from_local_name(ct: CompiledTarget) -> Iterable[Gap]:
    if _boundary(ct) != "NamedGraphBoundary":
        return
    if not any(b.name == "graphPrefix" for op in ct.operations for b in op.bindings):
        return
    template = str(ct.dimensions["aggregateBoundary"].extra.get("graphIriTemplate", ""))
    dropped = ""
    if "}" in template and template.split("}", 1)[1]:
        dropped = f" and the text after {{id}} ({template.split('}', 1)[1]!r}) is dropped"
    yield _gap(
        ct, "NamedGraphNamedFromLocalName", UNIMPLEMENTED, "TD-38", "HO8",
        "the graph is named from the root's local name, so two roots with one local name share a graph" + dropped,
    )


def _unconditional_write_named_graph_only(ct: CompiledTarget) -> Iterable[Gap]:
    if "unconditional-write" in _operation_names(ct) and _boundary(ct) != "NamedGraphBoundary":
        yield _gap(
            ct, "UnconditionalWriteNamedGraphOnly", UNIMPLEMENTED, "TD-02", "not planned",
            f"unconditional-write targets a named graph, and this target's boundary is {_boundary(ct)}, so it fails to render",
        )


def _shard_counts_not_honoured(ct: CompiledTarget) -> Iterable[Gap]:
    declared = []
    for name in ("txnShards", "logShards", "keyShards"):
        value = ct.dimensions[name].value
        try:
            if value is not None and int(str(value)) > 1:
                declared.append(f"{name} {int(str(value))}")
        except ValueError:
            continue
    if declared:
        yield _gap(
            ct, "ShardCountNotHonoured", UNIMPLEMENTED, "TD-06", "not planned",
            f"{', '.join(declared)} resolves but every template writes one txn, keys and log-bucket graph",
        )


def _infrastructure_graphs_fixed(ct: CompiledTarget) -> Iterable[Gap]:
    if ct.operations:
        yield _gap(
            ct, "InfrastructureGraphsFixed", UNIMPLEMENTED, "TD-05", "not planned",
            "the transaction, key, log, retention, dataset and event graph IRIs are compiler constants, whatever the configuration says",
        )


_WRITING = {"create-if-absent", "cas-replace", "tombstone-delete", "append"}


def _retention_and_epoch_bump_not_generated(ct: CompiledTarget) -> Iterable[Gap]:
    if _operation_names(ct) & _WRITING:
        yield _gap(
            ct, "RetentionAndEpochBumpNotGenerated", HOUSEKEEPING, "ADR-A80", "not planned",
            "the retention job (low-water marks, pinned-head copies, bucket drops) and the epoch bump are not generated",
        )


def _restore_runbook_unread(ct: CompiledTarget) -> Iterable[Gap]:
    extras = ct.dimensions["epochAuthority"].extra
    named = sorted(k for k in ("epochCoordinatorBinding", "erasureRegisterBinding", "erasureReplayOnRestore") if k in extras)
    if named:
        yield _gap(
            ct, "RestoreRunbookBindingsUnread", HOUSEKEEPING, "TD-08", "not planned",
            f"{', '.join(named)} resolve and are emitted, but no check reads them and no template writes them",
        )


def _version_row_created_by_caller(ct: CompiledTarget) -> Iterable[Gap]:
    if "bootstrap-version-row" in _operation_names(ct):
        yield _gap(
            ct, "VersionRowCreatedByCaller", CALLER, "tools/persistence/README.md, obligation 1", "not planned",
            "the version row must be created with bootstrap-version-row when the id is allocated, or every write is a no-op that looks like a lost race",
        )


RULES: dict[str, Rule] = {
    "CompositeOwnershipAssumed": _composite_ownership_assumed,
    "CompositeInversePathMisread": _composite_inverse_path_misread,
    "CompositeUsesDefaultGraph": _composite_default_graph,
    "CompositeNoLifecycleOperations": _composite_lifecycle,
    "NamedGraphNamedFromLocalName": _graph_named_from_local_name,
    "UnconditionalWriteNamedGraphOnly": _unconditional_write_named_graph_only,
    "ShardCountNotHonoured": _shard_counts_not_honoured,
    "InfrastructureGraphsFixed": _infrastructure_graphs_fixed,
    "RetentionAndEpochBumpNotGenerated": _retention_and_epoch_bump_not_generated,
    "RestoreRunbookBindingsUnread": _restore_runbook_unread,
    "VersionRowCreatedByCaller": _version_row_created_by_caller,
}


def find_gaps(compiled: Iterable[CompiledTarget]) -> list[Gap]:
    """Every gap that applies to any compiled target, sorted."""
    return sorted(gap for ct in compiled for rule in RULES.values() for gap in rule(ct))


def as_data(gaps: Iterable[Gap]) -> list[dict]:
    return [asdict(g) for g in gaps]


__all__ = ["Gap", "RULES", "UNIMPLEMENTED", "CALLER", "HOUSEKEEPING", "find_gaps", "as_data"]
