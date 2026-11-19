# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The confirmation read of a write, and how it classifies the write (ADR-A132, STD-312, the "confirmation" section of ``contracts/persistence/README.md``).

A ``204`` from the endpoint does not say whether a write's guard matched. After a write the caller reads the transaction claim and the few
facts each guard of the operation tests, on the writer, and :func:`classify` turns them into one of three outcomes. The write ``applied``
(on this attempt or an earlier one), was ``refused`` because its transaction id already claims a different request, or lost a race, and a
lost race names the guard that failed, which is its cause.

:func:`confirm_query` is the read, one ``SELECT`` of ``?fact`` and ``?value`` built from typed IRIs only, so no value is read as SPARQL
(PRI-55). :func:`classify` decides from the rows alone, and :func:`confirm` runs the one and the other through the adopter's client. The
library makes no store call of its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Optional, Sequence

from .audit import SparqlClient
from .bound import plain
from .contract import OperationKind, ProfileOperation
from .namespaces import PAT
from .payload import Lit
from .terms import Iri

DATASET_GUARD_SUFFIX = "-dataset-guard"
"""A template id that ends with it guards on the dataset's epoch. Any other write guards on the version row's own epoch."""

_CLAIMING = frozenset({
    OperationKind.CREATE, OperationKind.REPLACE, OperationKind.DELTA_REPLACE, OperationKind.TOMBSTONE, OperationKind.APPEND,
    OperationKind.APPEND_VERSION,
})
_ROW_GUARDED = _CLAIMING - {OperationKind.CREATE}
_KEY_CLAIMING = frozenset({OperationKind.KEY_CLAIM_WRITE, OperationKind.KEY_CLAIM_WRITE_DUAL})


class Outcome(Enum):
    """What a confirmation says of a write. The values are the names the studio's run contract uses."""

    APPLIED = "applied"
    REFUSED = "refused"
    LOST_RACE = "lostRace"


class Classification(Enum):
    """The classification of a write. For a lost race it is the cause, and each cause answers one guard of the generated operations."""

    APPLIED = "Applied"
    IDEMPOTENCY_KEY_REUSE = "IdempotencyKeyReuse"
    EPOCH_CHANGED = "EpochChanged"
    GONE = "Gone"
    PRECONDITION_FAILED = "PreconditionFailed"
    ALREADY_EXISTS = "AlreadyExists"
    KEY_CLAIM_HELD = "KeyClaimHeld"
    NOT_APPLIED = "NotApplied"

    @property
    def outcome(self) -> Outcome:
        if self is Classification.APPLIED:
            return Outcome.APPLIED
        if self is Classification.IDEMPOTENCY_KEY_REUSE:
            return Outcome.REFUSED
        return Outcome.LOST_RACE


@dataclass(frozen=True)
class Confirmation:
    """The result of a confirmation. ``revision`` is the revision the transaction claimed, or ``None`` where it claimed none, and ``reason`` says
    in words which guard the classification answers and what the read found."""

    classification: Classification
    revision: Optional[str]
    reason: str

    @property
    def outcome(self) -> Outcome:
        return self.classification.outcome


class ConfirmationError(ValueError):
    """A write that cannot be confirmed, because its operation records no claim to read or the request lacks what the read needs."""


def confirms(operation: ProfileOperation) -> bool:
    """Whether the confirmation reads this operation. It does for an operation that records a transaction claim, and for a key-claim write."""
    return operation.kind in _KEY_CLAIMING or (operation.kind in _CLAIMING and operation.parameter("txnId") is not None)


def _graph(operation: ProfileOperation, name: str) -> Optional[Iri]:
    text = operation.binding(name)
    if text is None:
        return None
    if not (text.startswith("<") and text.endswith(">")):
        raise ConfirmationError(f"the binding {name} of {operation.template_id} is not an IRI")
    return Iri.encode(text[1:-1])


def _need_graph(operation: ProfileOperation, name: str) -> Iri:
    found = _graph(operation, name)
    if found is None:
        raise ConfirmationError(f"{operation.template_id} has no binding {name}, so the write cannot be confirmed")
    return found


def _need_iri(values: Mapping, name: str) -> Iri:
    value = values.get(name)
    if value is None:
        raise ConfirmationError(f"the request has no {name}, which the confirmation reads")
    try:
        return Iri.encode(plain(value))
    except ValueError as e:
        raise ConfirmationError(f"{name} is not an IRI: {e}") from e


def _long(values: Mapping, name: str) -> Optional[int]:
    value = values.get(name)
    if value is None:
        return None
    if isinstance(value, bool):
        raise ConfirmationError(f"{name} is not an xsd:long")
    if isinstance(value, int):
        return value
    text = value.value if isinstance(value, Lit) else str(value)
    try:
        return int(text)
    except ValueError as e:
        raise ConfirmationError(f"{name} is not an xsd:long") from e


def _target(operation: ProfileOperation, values: Mapping) -> Iri:
    name = "stream" if operation.kind is OperationKind.APPEND else "root"
    return _need_iri(values, name)


def _branch(graph: Iri, subject, predicate: str, fact: str) -> str:
    return f'{{ GRAPH {graph} {{ {subject} <{PAT}{predicate}> ?value }} BIND("{fact}" AS ?fact) }}'


def confirm_query(operation: ProfileOperation, values: Mapping) -> str:
    """The confirmation read of the write ``operation`` took ``values`` for, as one ``SELECT`` of ``?fact`` and ``?value``. Run it on the writer.

    A row is one fact the store holds. The facts the read asks for follow the guards of the operation, and the contract in
    ``contracts/persistence/README.md`` lists them. Every graph is a binding of the operation and every subject a typed IRI of the request."""
    if not confirms(operation):
        raise ConfirmationError(f"{operation.template_id} records no transaction claim and is not a key-claim write, so this read does not confirm it")
    branches: list = []
    if operation.kind in _KEY_CLAIMING:
        keys = _need_graph(operation, "keysGraph")
        names = ("claimCurrent", "claimNext") if operation.kind is OperationKind.KEY_CLAIM_WRITE_DUAL else ("claim",)
        for name, fact in zip(names, ("claimOwner", "claimNextOwner")):
            branches.append(_branch(keys, _need_iri(values, name), "claimedBy", fact))
    else:
        txn_graph, txn_id, target = _need_graph(operation, "txnGraph"), _need_iri(values, "txnId"), _target(operation, values)
        meta = _need_graph(operation, "metaGraphPrefix")
        branches.append(_branch(txn_graph, txn_id, "rev", "claimRev"))
        branches.append(_branch(txn_graph, txn_id, "requestDigest", "claimDigest"))
        if operation.template_id.endswith(DATASET_GUARD_SUFFIX):
            branches.append(_branch(_need_graph(operation, "datasetGraph"), _need_graph(operation, "datasetNode"), "epoch", "datasetEpoch"))
        branches.append(_branch(meta, target, "seq", "rowSeq"))
        if operation.kind in _ROW_GUARDED:
            branches.append(_branch(meta, target, "epoch", "rowEpoch"))
            branches.append(_branch(meta, target, "deleted", "rowDeleted"))
        data = _graph(operation, "dataGraph")
        if operation.kind is OperationKind.CREATE and data is not None:
            branches.append(
                f'{{ {{ SELECT ?p WHERE {{ GRAPH {data} {{ {target} ?p ?o }} }} LIMIT 1 }} BIND(STR(?p) AS ?value) BIND("dataPresent" AS ?fact) }}')
    return "SELECT ?fact ?value WHERE {\n  " + "\n  UNION ".join(branches) + "\n}"


def _facts(rows: Sequence[Mapping[str, object]]) -> dict:
    out: dict = {}
    for row in rows:
        out.setdefault(str(row["fact"]), []).append(plain(row["value"]) if isinstance(row["value"], str) else str(row["value"]))
    return out


def _as_long(text: str) -> Optional[int]:
    try:
        return int(text)
    except ValueError:
        return None


def _key_claim(operation: ProfileOperation, values: Mapping, facts: dict) -> Confirmation:
    owner = plain(_need_iri(values, "owner"))
    names = ("claimCurrent", "claimNext") if operation.kind is OperationKind.KEY_CLAIM_WRITE_DUAL else ("claim",)
    held = []
    for name, fact in zip(names, ("claimOwner", "claimNextOwner")):
        others = sorted(o for o in facts.get(fact, []) if o != owner)
        if others:
            held.append((plain(_need_iri(values, name)), others[0]))
    if held:
        claim, other = held[0]
        return Confirmation(Classification.KEY_CLAIM_HELD, None,
                            f"The key claim <{claim}> is held by <{other}>, not by <{owner}>, so the guard on another owner failed and the write changed nothing.")
    if all(owner in facts.get(fact, []) for fact in ("claimOwner", "claimNextOwner")[:len(names)]):
        return Confirmation(Classification.APPLIED, None, f"The key claim is held by <{owner}>, so the write applied, on this attempt or an earlier attempt.")
    return Confirmation(Classification.NOT_APPLIED, None, "The key claim has no owner and no guard of the operation can be read as the one that failed.")


def classify(operation: ProfileOperation, values: Mapping, rows: Sequence[Mapping[str, object]]) -> Confirmation:
    """Classify the write from the rows :func:`confirm_query` returned. The first of these that holds decides, in the order of the contract."""
    if not confirms(operation):
        raise ConfirmationError(f"{operation.template_id} records no transaction claim and is not a key-claim write, so this read does not confirm it")
    facts = _facts(rows)
    if operation.kind in _KEY_CLAIMING:
        return _key_claim(operation, values, facts)

    digest = values.get("requestDigest")
    epoch, expected = _long(values, "epoch"), _long(values, "expectedSeq")
    revs = sorted(facts.get("claimRev", []))
    if revs:
        same = facts.get("claimDigest", []) == [digest]
        if same:
            return Confirmation(Classification.APPLIED, revs[0],
                                "The claim of the transaction is on the transaction graph with this request's digest, so the write applied, on this attempt or an earlier attempt.")
        return Confirmation(Classification.IDEMPOTENCY_KEY_REUSE, revs[0], "The transaction id already claims a revision with the digest of a different request.")

    seqs = sorted(n for n in (_as_long(s) for s in facts.get("rowSeq", [])) if n is not None)
    row_guarded = operation.kind in _ROW_GUARDED
    if operation.template_id.endswith(DATASET_GUARD_SUFFIX):
        current = sorted(facts.get("datasetEpoch", []))
        if epoch is not None and epoch not in [_as_long(e) for e in current]:
            stated = f"is {current[0]}" if current else "is not stated"
            return Confirmation(Classification.EPOCH_CHANGED, None, f"The dataset's epoch {stated}, not {epoch}, so the guard on it failed.")
    elif row_guarded and epoch is not None and facts.get("rowEpoch") and epoch not in [_as_long(e) for e in facts["rowEpoch"]]:
        return Confirmation(Classification.EPOCH_CHANGED, None,
                            f"The version row's epoch is {sorted(facts['rowEpoch'])[0]}, not {epoch}, so the guard on it failed.")
    if row_guarded and any(v in ("true", "1") for v in facts.get("rowDeleted", [])):
        return Confirmation(Classification.GONE, None, "The aggregate's version row is tombstoned, so the write found nothing to change.")
    if row_guarded and (expected not in seqs if expected is not None else not seqs):
        if not seqs:
            what = f"The aggregate has no version row, so the guard on position {expected} failed." if expected is not None \
                else "The stream has no version row, so the guard on it failed. Was it bootstrapped?"
        else:
            what = f"The version row is at position {seqs[0]}, not {expected}, so another writer moved it and the guard failed."
        return Confirmation(Classification.PRECONDITION_FAILED, None, what)
    if operation.kind is OperationKind.CREATE and (seqs or facts.get("dataPresent")):
        what = f"The aggregate already has a version row at position {seqs[0]}, so the create wrote nothing." if seqs \
            else "The root already has triples in the data graph, so the create wrote nothing."
        return Confirmation(Classification.ALREADY_EXISTS, None, what)
    return Confirmation(Classification.NOT_APPLIED, None, "The transaction has no claim and no guard of the operation can be read as the one that failed.")


def confirm(client: SparqlClient, operation: ProfileOperation, values: Mapping) -> Confirmation:
    """Read the write's confirmation through ``client`` and classify it. ``values`` are the values the request was built from, including its
    ``requestDigest`` (:func:`lattice_persistence.request_digest`)."""
    return classify(operation, values, client.select(confirm_query(operation, values)))


__all__ = ["Outcome", "Classification", "Confirmation", "ConfirmationError", "DATASET_GUARD_SUFFIX", "confirms", "confirm_query", "classify", "confirm"]
