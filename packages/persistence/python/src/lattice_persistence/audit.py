# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The outcome of an audit, and the minimal SPARQL client the library needs (ADR-A132 decisions 2 and 3, ADR-A123 addendum of 2026-10-20).

An audit's query returns the rows that violate an invariant, so no row can mean two things. A dataset that is clean returns none, and so does
a query that read nothing, because no log graph was listed or none held a receipt (FMH-H2-5, non-coverage). :func:`audit_outcome` tells them
apart with three values. The library makes no store call of its own. :class:`SparqlClient` is the one method it asks of the adopter's client.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Optional, Protocol, Sequence

from .contract import OperationKind, ProfileOperation
from .namespaces import PAT
from .terms import Iri

LOG_GRAPHS_SLOT = "{{{logGraphs}}}"


class AuditOutcome(Enum):
    """What an audit reports. The names are the individuals of ``dal:AuditOutcome``."""

    CLEAN = "Clean"
    FAILED = "Failed"
    NOTHING_EXAMINED = "NothingExamined"


def audit_outcome(rows: Sequence, *, log_graphs: Optional[Sequence] = None, examined: Optional[int] = None) -> AuditOutcome:
    """The outcome of an audit that returned ``rows``.

    * ``FAILED`` if it returned a row, since a row means it read something.
    * ``NOTHING_EXAMINED`` if it returned none and ``log_graphs`` is an empty list (an audit over no listed graph), or ``examined`` is zero (the
      listed graphs held no receipt for it to read).
    * ``CLEAN`` otherwise.

    ``log_graphs`` is ``None`` for an audit that lists none, such as the key-claim and fork audits, which read fixed graphs. ``examined`` is the
    count :func:`examined_query` returns, or ``None`` where the caller did not count."""
    if len(rows):
        return AuditOutcome.FAILED
    if (log_graphs is not None and len(log_graphs) == 0) or examined == 0:
        return AuditOutcome.NOTHING_EXAMINED
    return AuditOutcome.CLEAN


def registry_text(log_graphs: Sequence) -> str:
    """The text of the ``logGraphs`` slot, from typed IRIs only."""
    return " ".join(str(g) if isinstance(g, Iri) else str(Iri.encode(g)) for g in log_graphs)


def examined_query(operation: ProfileOperation, log_graphs: Sequence) -> str:
    """The query that counts the receipts an audit over ``log_graphs`` can read, the pinned graph of the operation and the listed graphs. A
    count of zero means the audit examined nothing."""
    pinned = operation.binding("pinnedGraph")
    graphs = " ".join(g for g in (pinned, registry_text(log_graphs)) if g)
    return (
        "SELECT (COUNT(?r) AS ?n) WHERE { VALUES ?log { " + graphs + " } "
        "GRAPH ?log { ?r a <" + str(PAT.Revision) + "> } }"
    )


class SparqlClient(Protocol):
    """The adopter's client, behind the one method the library asks of it. Each row maps a variable name to its value, as text or a number."""

    def select(self, query: str) -> Sequence[Mapping[str, object]]: ...


@dataclass(frozen=True)
class AuditResult:
    outcome: AuditOutcome
    rows: tuple = ()
    examined: Optional[int] = None


def run_audit(client: SparqlClient, operation: ProfileOperation, query: str, log_graphs: Optional[Sequence] = None) -> AuditResult:
    """Run ``query``, the instantiated text of the audit ``operation``, and report its outcome. ``log_graphs`` fills the ``logGraphs`` slot of an
    audit that has one, and is counted with :func:`examined_query` so that an audit that read no receipt is not reported clean."""
    if operation.kind is not OperationKind.AUDIT:
        raise ValueError(f"{operation.template_id} is not an audit")
    if operation.examines is not None:
        if log_graphs is None:
            raise ValueError(f"{operation.template_id} examines {operation.examines}, which must be given, empty if it lists none")
        query = query.replace(LOG_GRAPHS_SLOT, registry_text(log_graphs))
    rows = tuple(client.select(query))
    examined = None
    if operation.examines is not None and len(log_graphs or ()) > 0 and not rows:
        counted = client.select(examined_query(operation, log_graphs))
        examined = int(next(iter(counted[0].values()))) if counted else 0
    return AuditResult(audit_outcome(rows, log_graphs=log_graphs if operation.examines else None, examined=examined), rows, examined)


__all__ = ["AuditOutcome", "audit_outcome", "registry_text", "examined_query", "SparqlClient", "AuditResult", "run_audit", "LOG_GRAPHS_SLOT"]
