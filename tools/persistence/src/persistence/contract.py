# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The contract of a generated operation (formal-methods track H, slice H2.6, ADR-A123 decisions 4 and 6, H2-Q5 and H2-Q6).

:func:`contract_of` reads an :class:`~persistence.ir.Operation` and returns what a caller, a relational realisation, a model
checker and the compiled profile need to know about it, with no SPARQL text: the logical kind of the operation, its
parameters, the logical resources it touches with the mode and key of each access, the columns an audit returns, the payload and
the request digest it takes, and whether its parameter guard is on. Everything is derived from the operation, apart from three
tables kept here and nowhere else (H2.6 step 1):

* :data:`OPERATION_KINDS`, the logical kind of each builder,
* :func:`resource_of`, which maps a graph role (and, where a role holds two resources, a predicate) to a logical resource,
* :data:`BUILDER_VERSIONS`, which a golden check ties to the text each builder renders.

The kinds are closed enumerations. The compiled profile will name their members as individuals, never as classes (H2.7), and
nothing here is SPARQL, so the contract stays valid for a realisation that is not SPARQL.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .ir import AccessMode, Kind, Operation, Projected, SLOT_KINDS, Var
from .ir_render import Access, access_sets
from .namespaces import PAT


class OperationKind(Enum):
    """The logical kind of an operation. A relational realisation and a model compare operations by kind, not by the SPARQL a
    builder writes."""

    CREATE = "Create"
    BOOTSTRAP = "Bootstrap"
    REPLACE = "Replace"
    TOMBSTONE = "Tombstone"
    APPEND = "Append"
    UNCONDITIONAL_WRITE = "UnconditionalWrite"
    VALUE_GUARDED_REPLACE = "ValueGuardedReplace"
    KEY_CLAIM_WRITE = "KeyClaimWrite"
    KEY_CLAIM_WRITE_DUAL = "KeyClaimWriteDual"
    KEY_CLAIM_RETIRE = "KeyClaimRetire"
    QUARANTINE = "Quarantine"
    MERGE_REWRITE = "MergeRewrite"
    AUDIT = "Audit"


class ResourceKind(Enum):
    """A logical resource an operation reads or writes. Its SPARQL realisation is the graph role the builders name, and its
    relational realisation is in the paper check of the H2.6 Validation Pack."""

    AGGREGATE = "Aggregate"
    VERSION_ROW = "VersionRow"
    TRANSACTION_CLAIM = "TransactionClaim"
    RECEIPT = "Receipt"
    EVENT = "Event"
    KEY_CLAIM = "KeyClaim"
    MERGE_RECORD = "MergeRecord"
    KEY_QUARANTINE = "KeyQuarantine"
    DATASET_EPOCH = "DatasetEpoch"
    RETENTION_MARK = "RetentionMark"
    PROPERTY_VALUE = "PropertyValue"


LOGICAL_KEYS: dict[ResourceKind, tuple[str, ...]] = {
    ResourceKind.AGGREGATE: ("root",),
    ResourceKind.VERSION_ROW: ("root",),
    ResourceKind.TRANSACTION_CLAIM: ("transaction id",),
    ResourceKind.RECEIPT: ("target", "epoch", "seq"),
    ResourceKind.EVENT: ("stream", "seq"),
    ResourceKind.KEY_CLAIM: ("claim",),
    ResourceKind.MERGE_RECORD: ("owner",),
    ResourceKind.KEY_QUARANTINE: ("claim", "owner"),
    ResourceKind.DATASET_EPOCH: ("dataset",),
    ResourceKind.RETENTION_MARK: ("target",),
    ResourceKind.PROPERTY_VALUE: ("root", "property"),
}
"""The logical key of each resource, as the names of its parts. A stream is the root of its version row, and a bucket month is a
realisation and never part of a key (design review 2.2)."""

_KEY_CLAIM_PREDICATES = frozenset({
    "a", f"<{PAT.claimedBy}>", f"<{PAT.constraint}>", f"<{PAT.retiredBy}>", f"<{PAT.retiredAt}>",
})

_ROLE_RESOURCE: dict[str, ResourceKind] = {
    "data": ResourceKind.AGGREGATE,
    "meta": ResourceKind.VERSION_ROW,
    "txn": ResourceKind.TRANSACTION_CLAIM,
    "log": ResourceKind.RECEIPT,
    "pinned": ResourceKind.RECEIPT,  # the SPARQL realisation of receipt retention, not a resource of its own (plan 4.3, NQ2)
    "event": ResourceKind.EVENT,
    "quarantine": ResourceKind.KEY_QUARANTINE,
    "retention": ResourceKind.RETENTION_MARK,
    "dataset": ResourceKind.DATASET_EPOCH,
}


def resource_of(role: str, predicate: str) -> ResourceKind:
    """The logical resource a pattern touches. The keys graph holds two resources, told apart by predicate: a claim's own
    predicates, and any other predicate, which can only be the adopter's merge relation. No other role holds two."""
    if role == "keys":
        return ResourceKind.KEY_CLAIM if predicate in _KEY_CLAIM_PREDICATES else ResourceKind.MERGE_RECORD
    return _ROLE_RESOURCE[role]


# The logical kind of each builder. A dataset-guard variant has the kind of its base operation.
_STEM_KIND: dict[str, OperationKind] = {
    "bootstrap-version-row": OperationKind.BOOTSTRAP,
    "append-event": OperationKind.APPEND,
    "create-if-absent-named-graph": OperationKind.CREATE,
    "create-if-absent-composite": OperationKind.CREATE,
    "cas-replace-named-graph": OperationKind.REPLACE,
    "cas-replace-composite-property": OperationKind.REPLACE,
    "cas-replace-value-guard": OperationKind.VALUE_GUARDED_REPLACE,
    "tombstone-delete-named-graph": OperationKind.TOMBSTONE,
    "tombstone-delete-composite": OperationKind.TOMBSTONE,
    "unconditional-write": OperationKind.UNCONDITIONAL_WRITE,
    "key-claim-write": OperationKind.KEY_CLAIM_WRITE,
    "key-claim-write-dual": OperationKind.KEY_CLAIM_WRITE_DUAL,
    "key-claim-retire": OperationKind.KEY_CLAIM_RETIRE,
    "key-claim-quarantine": OperationKind.QUARANTINE,
    "key-claim-merge-rewrite": OperationKind.MERGE_REWRITE,
    "key-claim-duplicate-audit": OperationKind.AUDIT,
    "fork-detection-audit": OperationKind.AUDIT,
    "gap-scan-audit": OperationKind.AUDIT,
    "revision-multi-txn-audit": OperationKind.AUDIT,
    "txn-multi-revision-audit": OperationKind.AUDIT,
}
OPERATION_KINDS = _STEM_KIND
DATASET_GUARD_SUFFIX = "-dataset-guard"


def stem_of(operation_id: str) -> str:
    """The builder an operation id belongs to, without the dataset-guard suffix."""
    return operation_id.removesuffix(DATASET_GUARD_SUFFIX)


BUILDER_VERSIONS: dict[str, int] = {**{stem: 1 for stem in sorted(_STEM_KIND)}, "append-event": 2}
"""The version of each builder, which any change to the text it renders must bump. A golden check
(`tests/test_builder_versions.py`) holds the version to the text, and it is a number kept here, never computed, so that a
change to a builder is a change a reviewer sees. A dataset-guard variant shares its base operation's version. `append-event` is at 2
since its events became request-time slots (formal-methods H2.6b)."""


class GuardStatus(Enum):
    GUARDED = "Guarded"
    GUARDS_OFF = "GuardsOff"
    NO_REQUIRED_PARAMETER = "NoRequiredParameter"
    NOT_GENERATED = "NotGenerated"


class GraphNaming(Enum):
    QUERY_NAMED = "QueryNamed"
    CALLER_NAMED = "CallerNamed"


class DeclarationSource(Enum):
    BUILDER_DERIVED = "BuilderDerived"
    HAND_DECLARED = "HandDeclared"


@dataclass(frozen=True, order=True)
class ParameterContract:
    name: str
    kind: str
    required: bool
    equals_graph_name: bool = False
    sourced_from_registry: bool = False


@dataclass(frozen=True, order=True)
class AccessContract:
    resource: str
    mode: str
    keyed_by: Optional[str] = None


@dataclass(frozen=True, order=True)
class ResultColumn:
    name: str
    kind: str
    separator: Optional[str] = None


@dataclass(frozen=True)
class PayloadContract:
    parameter: str
    root: Optional[str]


@dataclass(frozen=True)
class DigestContract:
    """What the request digest is taken over (the patterns guide, remediation A5): the kind of the operation, the target it
    names, the sequence it expects, and the sorted canonical N-Triples of what the request asserts. That last part is one slot
    per kind of content, in a fixed order, so a triple's role is part of what is hashed (formal-methods H2.6b, Q5): the payload of
    a write, or for an append the events, which are its rows slot and its triples slot together. A part an operation does not
    have is ``None`` or empty. The hash and the encoding are fixed by the contract, and the algorithm is built in H2.8."""

    target: Optional[str]
    expected: Optional[str]
    payload: Optional[str]
    event: tuple = ()


@dataclass(frozen=True)
class OperationContract:
    id: str
    kind: OperationKind
    version: int
    guard_status: GuardStatus
    graph_naming: Optional[GraphNaming]
    parameters: tuple
    accesses: tuple
    results: tuple
    payload: Optional[PayloadContract]
    digest: Optional[DigestContract]
    source: DeclarationSource = DeclarationSource.BUILDER_DERIVED


HAND_DECLARED: dict[str, OperationContract] = {
    # The value-based compare-and-set of a dal:NoBoundary target. It reads and writes the default graph and the typed IR cannot
    # express it (TD-43), so it has no builder and its contract is written here. It has no generated parameter guard.
    "cas-replace-value-guard": OperationContract(
        id="cas-replace-value-guard", kind=OperationKind.VALUE_GUARDED_REPLACE, version=1, guard_status=GuardStatus.NOT_GENERATED,
        graph_naming=None,
        parameters=(
            ParameterContract("newValue", Kind.IRI_OR_LITERAL.value, True),
            ParameterContract("oldValue", Kind.IRI_OR_LITERAL.value, True),
            ParameterContract("root", Kind.IRI.value, True),
        ),
        accesses=(
            AccessContract(ResourceKind.PROPERTY_VALUE.value, AccessMode.DELETE.value, "root"),
            AccessContract(ResourceKind.PROPERTY_VALUE.value, AccessMode.INSERT.value, "root"),
            AccessContract(ResourceKind.PROPERTY_VALUE.value, AccessMode.POINT_READ.value, "root"),
        ),
        results=(), payload=None, digest=None, source=DeclarationSource.HAND_DECLARED,
    ),
}


def _keyed_by(access: Access, resource: ResourceKind, params: dict) -> Optional[str]:
    """The parameter whose value is the key of the resource, when the pattern is about one given subject. A computed or minted
    subject (a receipt, an event) and a scan have none."""
    if resource is ResourceKind.AGGREGATE:
        return "root" if "root" in params else None
    if access.subject.startswith("$"):
        name = access.subject[1:]
        if name in params and params[name].kind not in SLOT_KINDS and resource in (
            ResourceKind.VERSION_ROW, ResourceKind.TRANSACTION_CLAIM, ResourceKind.KEY_CLAIM, ResourceKind.PROPERTY_VALUE,
        ):
            return name
    return None


def _result_columns(operation: Operation) -> tuple:
    if operation.select is None:
        return ()
    columns = []
    for item in operation.select.projection:
        if isinstance(item, Var):
            kind = {Kind.IRI: "Iri", Kind.POSITION: "Position", Kind.STRING: "String"}.get(item.kind, "Term")
            columns.append(ResultColumn(item.name, kind))
        else:
            assert isinstance(item, Projected)
            expr = item.expr
            name = getattr(expr, "name", "")
            if name == "COUNT":
                columns.append(ResultColumn(item.var.name, "Count"))
            elif name == "GROUP_CONCAT":
                columns.append(ResultColumn(item.var.name, "Concatenation", expr.separator if expr.separator is not None else " "))
            else:
                columns.append(ResultColumn(item.var.name, "Term"))
    return tuple(columns)


def contract_of(operation: Operation) -> OperationContract:
    """The contract of ``operation``, derived from it and from the three tables of this module."""
    stem = stem_of(operation.id)
    params = {p.name: p for p in operation.params}
    sets = access_sets(operation)
    accesses = set()
    for access in sets.reads | sets.writes:
        resource = resource_of(access.role, access.predicate)
        accesses.add(AccessContract(resource.value, access.mode, _keyed_by(access, resource, params)))
    graph_texts = {a.graph for a in sets.reads | sets.writes}
    naming = (
        GraphNaming.CALLER_NAMED if "$g" in graph_texts
        else GraphNaming.QUERY_NAMED if "?g" in graph_texts else None
    )
    guard = operation.guard
    if guard is not None and guard.off:
        status = GuardStatus.GUARDS_OFF
    elif guard is not None and guard.params:
        status = GuardStatus.GUARDED
    else:
        status = GuardStatus.NO_REQUIRED_PARAMETER
    parameters = tuple(sorted(
        ParameterContract(
            p.name, p.kind.value, p.required, p.equals is not None, p.kind is Kind.REGISTRY_LIST,
        )
        for p in operation.params
    ))
    kind = _STEM_KIND[stem]
    payload_name = next((p.name for p in operation.params if p.kind is Kind.PAYLOAD), None)
    # An append's triples slot holds its events' domain triples, which are not the aggregate's payload and have no boundary shape.
    event = tuple(sorted(p.name for p in operation.params if p.kind in SLOT_KINDS and p.kind is not Kind.REGISTRY_LIST)) if kind is OperationKind.APPEND else ()
    payload_name = None if kind is OperationKind.APPEND else payload_name
    payload = PayloadContract(payload_name, "root" if "root" in params else None) if payload_name else None
    digest = None
    if "requestDigest" in params:
        target = next((a.keyed_by for a in sorted(accesses) if a.resource == ResourceKind.VERSION_ROW.value and a.keyed_by), None)
        digest = DigestContract(target, "expectedSeq" if "expectedSeq" in params else None, payload_name, event)
    return OperationContract(
        id=operation.id, kind=kind, version=BUILDER_VERSIONS[stem], guard_status=status, graph_naming=naming,
        parameters=parameters, accesses=tuple(sorted(accesses)), results=_result_columns(operation), payload=payload, digest=digest,
    )


__all__ = [
    "OperationKind", "ResourceKind", "AccessMode", "LOGICAL_KEYS", "OPERATION_KINDS", "BUILDER_VERSIONS", "GuardStatus",
    "GraphNaming", "DeclarationSource", "ParameterContract", "AccessContract", "ResultColumn", "PayloadContract",
    "DigestContract", "OperationContract", "HAND_DECLARED", "resource_of", "stem_of", "contract_of",
]
