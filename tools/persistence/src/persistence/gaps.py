# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""What the generated SPARQL does not do, as data (formal-methods track H, slice H1.4b).

For each compiled target this lists the standing facts and obligations that hold whatever the
configuration says, and whose obligation each is:

``unimplemented``
    the compiler or its templates do not do something a reader might expect. A register row is named.
``caller``
    the generated SPARQL assumes the caller does something it cannot enforce.
``housekeeping``
    the work belongs to the housekeeping component (ADR-A80), which this compiler does not generate.

A configuration that asks for something the compiler cannot honour is not a gap. It is a compile
diagnostic or a refusal, so a profile is never produced that quietly drops a declaration (ADR-A79). A
declared shard count above one is the warning ``ShardingNotHonoured``, and an unconditional write
for a boundary with no named graph is the refusal ``UnconditionalWriteRequiresNamedGraph``. So the
report is informational and never a gate: every entry holds for almost every configuration.

It reads compiled targets, needs no backend, and is sorted so two runs are byte-identical. Each rule
is a function over one :class:`CompiledTarget`, kept in :data:`RULES` so a test can name every entry.
A slice that closes a gap removes its rule here, and the entry it expected from the test, in the same
commit.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable, Iterable

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


def _operation_names(ct: CompiledTarget) -> set[str]:
    return {op.operation for op in ct.operations}


def _gap(ct: CompiledTarget, gap: str, obligation: str, reference: str, closes_in: str, message: str) -> Gap:
    return Gap(gap, str(ct.target), obligation, reference, closes_in, message)


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
