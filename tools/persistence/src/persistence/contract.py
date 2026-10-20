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
    APPEND_VERSION = "AppendVersion"
    UNCONDITIONAL_WRITE = "UnconditionalWrite"
    VALUE_GUARDED_REPLACE = "ValueGuardedReplace"
    KEY_CLAIM_WRITE = "KeyClaimWrite"
    KEY_CLAIM_WRITE_DUAL = "KeyClaimWriteDual"
    KEY_CLAIM_RETIRE = "KeyClaimRetire"
    QUARANTINE = "Quarantine"
    MERGE_REWRITE = "MergeRewrite"
    AUDIT = "Audit"
    MEMBERS_READ = "MembersRead"
    PAYLOAD_CHECK = "PayloadCheck"
    """The check of a payload against the family's boundary shape, as a query a caller in any language gets from ``instantiate`` (ADR-A123
    decision 6, H2.7-Q3). H2.7 adds the kind and H2.8 emits the operation, so no builder has this kind yet."""


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
    PATCH_CONTENT = "PatchContent"


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
    ResourceKind.PATCH_CONTENT: ("target", "epoch", "seq", "direction"),
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
    "patch": ResourceKind.PATCH_CONTENT,  # the add and del graphs of a patch log, named from the receipt (H2.6d)
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
    "append-version": OperationKind.APPEND_VERSION,
    "append-version-delta": OperationKind.APPEND_VERSION,
    "members": OperationKind.MEMBERS_READ,
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
# The patch-log and no-receipt variants of the in-place writes (H2.6d) have the kind of their base operation.
for _stem, _kind in tuple(_STEM_KIND.items()):
    if _stem.startswith(("create-if-absent-", "cas-replace-named", "cas-replace-composite", "tombstone-delete-")):
        _STEM_KIND[_stem + "-patch-log"] = _kind
        _STEM_KIND[_stem + "-no-receipt"] = _kind
OPERATION_KINDS = _STEM_KIND
DATASET_GUARD_SUFFIX = "-dataset-guard"


def stem_of(operation_id: str) -> str:
    """The builder an operation id belongs to, without the dataset-guard suffix."""
    return operation_id.removesuffix(DATASET_GUARD_SUFFIX)


_NOT_EXISTS_NAMES_ITS_GRAPH = (
    "append-version", "append-version-delta", "members",
    *(f"{base}{tag}" for base in ("cas-replace-composite-property", "cas-replace-named-graph", "tombstone-delete-composite", "tombstone-delete-named-graph")
      for tag in ("", "-no-receipt", "-patch-log")),
)
"""The builders whose `NOT EXISTS` inside a `GRAPH` block gained a `GRAPH` of its own in H2.6g (TSD-34). Each is one version above where it was."""

BUILDER_VERSIONS: dict[str, int] = {
    stem: {"append-event": 2, "append-version": 2, "cas-replace-named-graph": 2, "cas-replace-value-guard": 2}.get(stem, 1) + (stem in _NOT_EXISTS_NAMES_ITS_GRAPH)
    for stem in sorted(_STEM_KIND)
}
"""The version of each builder, which any change to the text it renders must bump. A golden check
(`tests/test_builder_versions.py`) holds the version to the text, and it is a number kept here, never computed, so that a
change to a builder is a change a reviewer sees. A dataset-guard variant shares its base operation's version. `append-event` is at 2
since its events became request-time slots (formal-methods H2.6b). `append-version` is at 2 since it links versions with `pat:previousVersion`
(R2, H2.6d), and `cas-replace-named-graph` since it no longer names delta graphs from caller parameters, which a patch-log variant now writes.
`cas-replace-value-guard` is at 2 since its patterns moved from the default graph into the family's data graph (H2.7, TD-43). The builders in
`_NOT_EXISTS_NAMES_ITS_GRAPH` are one higher since a `NOT EXISTS` inside a `GRAPH` block names its graph (H2.6g, TSD-34)."""


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


@dataclass(frozen=True, order=True)
class EdgeContract:
    """One edge of the boundary shape that leads to a node, as a caller's check reads it (H2.6e): where it leaves, the step, its
    ownership, the class it leads to and its reference mode (``ByIdentity`` or ``Pinned``). H2.8 refuses a payload whose object on a
    pinned edge is not a version, and on an identity edge is a version of a versioned class."""

    source_shape: str
    predicate: str
    inverse: bool
    ownership: str
    target_class: Optional[str]
    reference_mode: str


def edge_contracts(tree) -> tuple:
    """The edges of an ownership tree (``persistence.boundary.OwnershipTree``) that lead to a node, as contracts, in a total order."""
    if tree is None:
        return ()
    return tuple(sorted(
        EdgeContract(
            str(e.source_shape), str(e.step.predicate), e.step.inverse, e.kind,
            None if e.target_class is None else str(e.target_class), e.reference_mode,
        )
        for e in tree.node_edges()
    ))


@dataclass(frozen=True)
class PayloadContract:
    parameter: str
    root: Optional[str]
    edges: tuple = ()


@dataclass(frozen=True)
class DigestContract:
    """What the request digest is taken over (the patterns guide, remediation A5): the kind of the operation, the target it
    names, the sequence it expects, and the sorted canonical N-Triples of what the request asserts. That last part is one slot
    per kind of content, in a fixed order, so a triple's role is part of what is hashed (formal-methods H2.6b, Q5): the payload of
    a write, or for an append the events, which are its rows slot and its triples slot together, and for a replace that writes a patch
    log the asserted and the retracted triples, in the order payload, add, del (formal-methods H2.6d), and for an append of versions under delta membership the added and the dropped members in the same two parts (H2.6f). A part an operation does not have
    is ``None`` or empty. A create's add graph is its payload and a tombstone's del graph is copied from its sweep, so neither has a part
    of its own. The hash and the encoding are fixed by the contract, and the algorithm is built in H2.8."""

    target: Optional[str]
    expected: Optional[str]
    payload: Optional[str]
    event: tuple = ()
    add: Optional[str] = None
    delete: Optional[str] = None


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


HAND_DECLARED: dict[str, OperationContract] = {}
"""The contracts of operations that have no builder, written by hand and marked ``dal:HandDeclared``. Empty since H2.7, which gave the one
operation that had none, the value-based compare-and-set of a ``dal:NoBoundary`` family, a builder (TD-43). A new entry needs a reason a
builder cannot express the operation, and the vocabulary keeps ``dal:HandDeclared`` for it."""


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


def contract_of(operation: Operation, edges: tuple = ()) -> OperationContract:
    """The contract of ``operation``, derived from it and from the three tables of this module. ``edges`` is the family's
    :func:`edge_contracts`, which an operation cannot know, and is carried on the payload contract of an operation that has one."""
    stem = stem_of(operation.id)
    params = {p.name: p for p in operation.params}
    sets = access_sets(operation)
    accesses = set()
    for access in sets.reads | sets.writes:
        resource = resource_of(access.role, access.predicate)
        if stem == "cas-replace-value-guard" and resource is ResourceKind.AGGREGATE:
            resource = ResourceKind.PROPERTY_VALUE  # a family with no boundary has no aggregate. Its data graph holds one value per (root, property)
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
    payload = PayloadContract(payload_name, "root" if "root" in params else None, tuple(edges)) if payload_name else None
    digest = None
    if "requestDigest" in params:
        target = next((a.keyed_by for a in sorted(accesses) if a.resource == ResourceKind.VERSION_ROW.value and a.keyed_by), None)
        digest = DigestContract(
            target, "expectedSeq" if "expectedSeq" in params else None, payload_name, event,
            "assertTriples" if "assertTriples" in params else "addedMembers" if "addedMembers" in params else None,
            "retractTriples" if "retractTriples" in params else "droppedMembers" if "droppedMembers" in params else None,
        )
    return OperationContract(
        id=operation.id, kind=kind, version=BUILDER_VERSIONS[stem], guard_status=status, graph_naming=naming,
        parameters=parameters, accesses=tuple(sorted(accesses)), results=_result_columns(operation), payload=payload, digest=digest,
    )


__all__ = [
    "OperationKind", "ResourceKind", "AccessMode", "LOGICAL_KEYS", "OPERATION_KINDS", "BUILDER_VERSIONS", "GuardStatus",
    "GraphNaming", "DeclarationSource", "ParameterContract", "AccessContract", "ResultColumn", "PayloadContract",
    "DigestContract", "EdgeContract", "edge_contracts", "OperationContract", "HAND_DECLARED", "resource_of", "stem_of", "contract_of",
]
