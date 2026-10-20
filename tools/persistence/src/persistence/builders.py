# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The operation builders (formal-methods track H, slice H2.2, ADR-A123 decision 1).

One builder per operation id takes the compile-time bindings of a generated operation, the same values a
template is rendered with, and returns the typed :class:`~persistence.ir.Operation` that
:func:`persistence.ir_render.render` turns into SPARQL. A builder is a port of one Mustache template and
changes nothing about the query. The equivalence harness of the tests holds it to that, and the templates
stay in use until H2.9.

The ported operations are listed in :data:`BUILDERS`. Each keeps the template's variable names, so the
two renderings can be compared as SPARQL algebra.
"""

from __future__ import annotations

from typing import Callable, Mapping

from rdflib import URIRef

from .ir import (
    A, Bind, Binding, Compare, Const, Filter, Func, Graph, GraphBlock, GraphRole, Group, Kind, NotExists, Op, Operation,
    Optional_, Param, ParamRef, PayloadSlot, Path, Projected, RegistrySlot, RowsSlot, RowValues, Select, SubSelect, TermGuard, Triple, Union_, ValueGuard, Values, Var,
)
from .paths import Star, Step
from .namespaces import PAT
from .terms import Integer, Iri, Literal, PropertyPath

XSD_LONG = "http://www.w3.org/2001/XMLSchema#long"
XSD_BOOLEAN = "http://www.w3.org/2001/XMLSchema#boolean"


GRAPH_ROLES: dict[str, GraphRole] = {
    # compile-time bindings that name a graph
    "metaGraphPrefix": GraphRole.META,
    "txnGraph": GraphRole.TXN,
    "datasetGraph": GraphRole.DATASET,
    "dataGraph": GraphRole.DATA,
    "payloadGraph": GraphRole.DATA,  # the caller's local copy of the payload, which is the aggregate's new state (H2.8b)
    "keysGraph": GraphRole.KEYS,
    "keyQuarantineGraph": GraphRole.QUARANTINE,
    "retentionGraph": GraphRole.RETENTION,
    "pinnedGraph": GraphRole.PINNED,
    # variables a query binds to a graph, each with one meaning in every template
    "g": GraphRole.DATA,
    "log": GraphRole.LOG,
    "logGraph": GraphRole.LOG,
    "logGraph2": GraphRole.LOG,
    # the delta graphs of a patch-log write, named from the receipt (H2.6d)
    "addGraph": GraphRole.PATCH,
    "delGraph": GraphRole.PATCH,
    "eventGraph": GraphRole.EVENT,
}
"""The role of every graph a builder names, by binding or variable name. A builder never chooses a role itself, so
it cannot put a pattern in the wrong part of the store, and the read and write sets derived from the roles
(ADR-A123 decision 3) are right by construction. A name with no entry is refused."""


class Bindings:
    """The compile-time bindings of one operation. Records which names a builder read, so a test can check
    that a builder uses exactly the bindings its template does."""

    def __init__(self, context: Mapping) -> None:
        self._context = context
        self.read: set[str] = set()

    def _value(self, name: str):
        self.read.add(name)
        return self._context[name]

    def const(self, name: str) -> Const:
        """The binding as a constant. :func:`persistence.instantiate.operation_context` has already wrapped the
        profile's encoded text by its declared ``dal:paramType``, so the value is used as it is, never encoded a
        second time, and :class:`~persistence.ir.Const` checks its type and form."""
        value = self._value(name)
        if isinstance(value, bool):
            raise TypeError(f"binding {name!r} is a bool")
        if isinstance(value, int):
            return Const(Integer.encode(value))
        if isinstance(value, PropertyPath):
            raise TypeError(f"binding {name!r} is a property path, read it with path()")
        return Const(value)

    def path(self, name: str) -> Path:
        """A ``PropertyPath`` binding, such as a composite family's owned path."""
        return Path(self._value(name))

    def has(self, name: str) -> bool:
        """Whether the operation has the binding. Reading it with :meth:`const` or :meth:`path` records the read."""
        return name in self._context

    def graph(self, name: str) -> Graph:
        """The graph a binding names, with its role from :data:`GRAPH_ROLES`."""
        return Graph(GRAPH_ROLES[name], self.const(name))


def graph_var(name: str, binding: Binding | None = None) -> Graph:
    """A graph the query binds to a variable, with its role from :data:`GRAPH_ROLES`. ``binding`` tags the variable
    for a ``DELETE`` or ``INSERT`` template."""
    return Graph(GRAPH_ROLES[name], Var(name, binding=binding))


def _pat(local: str) -> Const:
    return Const(Iri.encode(str(PAT[local])))


def _string(value: str) -> Const:
    return Const(Literal.encode(value))


def _int(value: int) -> Const:
    return Const(Integer.encode(value))


def _long(value: str) -> Const:
    return Const(Literal.encode(value, datatype=XSD_LONG))


_TRUE = Const(Literal.encode("true", datatype=XSD_BOOLEAN))
_ANY = Var("any")


def _bound(name: str) -> Var:
    return Var(name, binding=Binding.BOUND)


def _optional(name: str) -> Var:
    return Var(name, binding=Binding.OPTIONAL_ALLOWED)


# ---- bootstrap-version-row


def _bootstrap(b: Bindings, *, guards: bool, dataset_guard: bool) -> Operation:
    meta = b.graph("metaGraphPrefix")
    target, epoch = ParamRef("target"), ParamRef("epoch")
    where: list = []
    if dataset_guard:
        where.append(GraphBlock(b.graph("datasetGraph"), (Triple(b.const("datasetNode"), _pat("epoch"), epoch),)))
    where.append(NotExists(Group((GraphBlock(meta, (Triple(target, _pat("seq"), _ANY),)),))))
    insert = (GraphBlock(meta, (
        Triple(target, A, _pat("VersionRow")),
        Triple(target, _pat("epoch"), epoch),
        Triple(target, _pat("seq"), _long("0")),
    )),)
    return Operation.build(
        "bootstrap-version-row-dataset-guard" if dataset_guard else "bootstrap-version-row",
        (Param("target", Kind.IRI), Param("epoch", Kind.LONG)),
        Group(tuple(where)),
        guards=guards,
        insert=insert,
    )


# ---- append-event


def _append(b: Bindings, *, guards: bool, dataset_guard: bool) -> Operation:
    meta = b.graph("metaGraphPrefix")
    txn = b.graph("txnGraph")
    stream, epoch, txn_id = ParamRef("stream"), ParamRef("epoch"), ParamRef("txnId")
    n, n1, rev, prev = Var("n"), Var("n1"), Var("rev"), Var("prev")
    row_epoch = Var("rowEpoch")

    # The events come first, as rows the caller supplies (the guide's batch, formal-methods H2.6b). Every row joins the one counter
    # row, so k events give k solutions that write the same version row, claim and receipt, and each event its own triples.
    where: list = [RowValues((Var("event"), Var("eventType"), Var("opSeq"), Var("occurredAt")), RowsSlot("eventRows"))]
    if dataset_guard:
        where.append(GraphBlock(b.graph("datasetGraph"), (Triple(b.const("datasetNode"), _pat("epoch"), epoch),)))
        where.append(GraphBlock(meta, (Triple(stream, _pat("epoch"), row_epoch), Triple(stream, _pat("seq"), n))))
    else:
        where.append(GraphBlock(meta, (Triple(stream, _pat("epoch"), epoch), Triple(stream, _pat("seq"), n))))
    where += [
        Optional_(Group((GraphBlock(meta, (Triple(stream, _pat("head"), prev),)),))),
        NotExists(Group((GraphBlock(meta, (Triple(stream, _pat("deleted"), _TRUE),)),))),
        NotExists(Group((GraphBlock(txn, (Triple(txn_id, _pat("rev"), _ANY),)),))),
        Bind(Func("STRDT", (Func("STR", (Op("+", n, _int(1)),)), Const(Iri.encode(XSD_LONG)))), n1),
        Bind(Func("IRI", (Func("CONCAT", (
            Func("STR", (ParamRef("revBase"),)),
            Func("SUBSTR", (Func("CONCAT", (_string("0000000000000000000"), Func("STR", (n1,)))), Op("+", Func("STRLEN", (Func("STR", (n1,)),)), _int(1)))),
        )),)), rev),
        Bind(Func("SUBSTR", (Func("STR", (Func("NOW"),)), _int(1), _int(7))), Var("month")),
        Bind(Func("IRI", (Func("CONCAT", (Func("STR", (b.const("logGraphPrefix"),)), Var("month"))),)), Var("logGraph")),
        Bind(Func("IRI", (Func("CONCAT", (Func("STR", (b.const("eventGraphPrefix"),)), Var("month"))),)), Var("eventGraph")),
        Bind(Func("STR", (txn_id,)), Var("txnKey")),
        Bind(Func("NOW"), Var("now")),
    ]
    delete_triples = (
        (Triple(stream, _pat("epoch"), _bound("rowEpoch")),) if dataset_guard else ()
    ) + (
        Triple(stream, _pat("seq"), _bound("n")),
        Triple(stream, _pat("head"), _optional("prev")),
    )
    insert = (
        GraphBlock(meta, (
            *((Triple(stream, _pat("epoch"), epoch),) if dataset_guard else ()),
            Triple(stream, _pat("seq"), _bound("n1")),
            Triple(stream, _pat("head"), _bound("rev")),
        )),
        GraphBlock(txn, (
            Triple(txn_id, _pat("rev"), _bound("rev")),
            Triple(txn_id, _pat("requestDigest"), ParamRef("requestDigest")),
        )),
        GraphBlock(graph_var("eventGraph", Binding.BOUND), (
            Triple(_bound("event"), A, _bound("eventType")),
            Triple(_bound("event"), _pat("revision"), _bound("rev")),
            Triple(_bound("event"), _pat("opSeq"), _bound("opSeq")),
            Triple(_bound("event"), _pat("occurredAt"), _bound("occurredAt")),
            PayloadSlot("eventTriples"),
        )),
        GraphBlock(graph_var("logGraph", Binding.BOUND), (
            Triple(_bound("rev"), A, _pat("Revision")),
            Triple(_bound("rev"), _pat("target"), stream),
            Triple(_bound("rev"), _pat("epoch"), epoch),
            Triple(_bound("rev"), _pat("seq"), _bound("n1")),
            Triple(_bound("rev"), _pat("prevRev"), _optional("prev")),
            Triple(_bound("rev"), _pat("txn"), _bound("txnKey")),
            Triple(_bound("rev"), _pat("recordedAt"), _bound("now")),
        )),
    )
    return Operation.build(
        "append-event-dataset-guard" if dataset_guard else "append-event",
        (
            Param("stream", Kind.IRI), Param("epoch", Kind.LONG), Param("revBase", Kind.STRING),
            Param("txnId", Kind.IRI), Param("requestDigest", Kind.DIGEST), Param("eventRows", Kind.ROWS),
            Param("eventTriples", Kind.PAYLOAD),
        ),
        Group(tuple(where)),
        guards=guards,
        insert=insert,
        delete=(GraphBlock(meta, delete_triples),),
    )


# ---- the named-graph row writers


def _graph_name(b: Bindings) -> Func:
    """The rule of ADR-A122 decision 8, `IRI(CONCAT(prefix, ENCODE_FOR_URI(STR($root)), suffix))`."""
    return Func("IRI", (Func("CONCAT", (b.const("graphPrefix"), Func("ENCODE_FOR_URI", (Func("STR", (ParamRef("root"),)),)), b.const("graphSuffix"))),))


GRAPH_NAMES = ("query", "caller")
"""Who names a root's graph (ADR-A123, second addendum of 2026-10-12)."""


def _check_graph_names(graph_names: str) -> None:
    if graph_names not in GRAPH_NAMES:
        raise ValueError(f"graph_names is 'query' or 'caller', not {graph_names!r}")


class _Named:
    """How an operation names the root's graph. By default the query computes `?g` from `$root`. When the caller
    names it (ADR-A123, second addendum of 2026-10-12) the operation declares `$g`, whose `equals` is the naming rule,
    so the guard checks it, and every `GRAPH ?g` is `GRAPH $g`."""

    def __init__(self, b: Bindings, graph_names: str) -> None:
        _check_graph_names(graph_names)
        self.caller = graph_names == "caller"
        self.rule = _graph_name(b)

    def params(self) -> tuple:
        return (Param("g", Kind.IRI, equals=self.rule),) if self.caller else ()

    def binds(self) -> tuple:
        return () if self.caller else (Bind(self.rule, Var("g")),)

    def graph(self, binding: Binding | None = None) -> Graph:
        return Graph(GRAPH_ROLES["g"], ParamRef("g")) if self.caller else graph_var("g", binding)


def _log_binds(b: Bindings) -> tuple:
    return (
        Bind(Func("IRI", (Func("CONCAT", (Func("STR", (b.const("logGraphPrefix"),)), Func("SUBSTR", (Func("STR", (Func("NOW"),)), _int(1), _int(7))))),)), Var("logGraph")),
    )


def _claim_binds() -> tuple:
    return (Bind(Func("STR", (ParamRef("txnId"),)), Var("txnKey")), Bind(Func("NOW"), Var("now")))


RECEIPT_MODELS = ("receipt", "patch-log", "none")
"""What an in-place write records (formal-methods H2.6d). `receipt` is a receipt (`dal:ReceiptOnly`, and `dal:SnapshotPerRevision`, which is
not honoured). `patch-log` is a receipt that names the delta graphs the same update writes (`dal:PatchLog`). `none` writes neither a receipt nor
a head (`dal:NoReceipt`), and keeps the transaction claim, which a retry needs."""


def _check_receipt(receipt: str) -> None:
    if receipt not in RECEIPT_MODELS:
        raise ValueError(f"receipt is one of {RECEIPT_MODELS}, not {receipt!r}")


def _delta_binds(*names: str) -> tuple:
    """The delta graphs of a patch-log write, named from the receipt (H2.6b-Q2): `IRI(CONCAT(STR($newRev), "/add"))` and `"/del"`, so a
    caller cannot name one wrongly. `names` is `add`, `del` or both."""
    return tuple(
        Bind(Func("IRI", (Func("CONCAT", (Func("STR", (ParamRef("newRev"),)), _string("/" + name))),)), Var(name + "Graph"))
        for name in names
    )


def _delta_block(name: str, *elements) -> GraphBlock:
    return GraphBlock(graph_var(name + "Graph", Binding.BOUND), elements)


def _dataset_guard(b: Bindings) -> tuple:
    return (GraphBlock(b.graph("datasetGraph"), (Triple(b.const("datasetNode"), _pat("epoch"), ParamRef("epoch")),)),)


_ROW_PARAMS = (
    Param("root", Kind.IRI), Param("epoch", Kind.LONG), Param("newRev", Kind.IRI), Param("txnId", Kind.IRI),
    Param("requestDigest", Kind.DIGEST),
)
_CAS_PARAMS = (
    Param("root", Kind.IRI), Param("epoch", Kind.LONG), Param("expectedSeq", Kind.POSITION),
    Param("nextSeq", Kind.POSITION), Param("newRev", Kind.IRI), Param("txnId", Kind.IRI),
    Param("requestDigest", Kind.DIGEST),
)


def _claim_block(b: Bindings) -> GraphBlock:
    return GraphBlock(b.graph("txnGraph"), (
        Triple(ParamRef("txnId"), _pat("rev"), ParamRef("newRev")),
        Triple(ParamRef("txnId"), _pat("requestDigest"), ParamRef("requestDigest")),
    ))


def _suffix(dataset_guard: bool, receipt: str) -> str:
    return {"receipt": "", "patch-log": "-patch-log", "none": "-no-receipt"}[receipt] + ("-dataset-guard" if dataset_guard else "")


def _create(b: Bindings, *, guards: bool, dataset_guard: bool, graph_names: str, receipt: str = "receipt") -> Operation:
    _check_receipt(receipt)
    named = _Named(b, graph_names)
    meta = b.graph("metaGraphPrefix")
    root, epoch, new_rev = ParamRef("root"), ParamRef("epoch"), ParamRef("newRev")
    has_receipt, patch = receipt != "none", receipt == "patch-log"
    where = (
        *named.binds(),
        *(_log_binds(b) if has_receipt else ()),
        *(_delta_binds("add") if patch else ()),
        *(_dataset_guard(b) if dataset_guard else ()),
        NotExists(Group((GraphBlock(meta, (Triple(root, _pat("seq"), _ANY),)),))),
        NotExists(Group((GraphBlock(b.graph("txnGraph"), (Triple(ParamRef("txnId"), _pat("rev"), _ANY),)),))),
        *(_claim_binds() if has_receipt else ()),
    )
    insert = (
        GraphBlock(named.graph(Binding.BOUND), (PayloadSlot("payloadTriples"),)),
        # a create's add graph is its payload, which the same slot fills (H2.6b-Q1)
        *((_delta_block("add", PayloadSlot("payloadTriples")),) if patch else ()),
        GraphBlock(meta, (
            Triple(root, A, _pat("VersionRow")), Triple(root, _pat("epoch"), epoch),
            Triple(root, _pat("seq"), _long("1")), *((Triple(root, _pat("head"), new_rev),) if has_receipt else ()),
        )),
        _claim_block(b),
        *((GraphBlock(graph_var("logGraph", Binding.BOUND), (
            Triple(new_rev, A, _pat("Revision")), Triple(new_rev, _pat("target"), root), Triple(new_rev, _pat("epoch"), epoch),
            Triple(new_rev, _pat("seq"), _long("1")), Triple(new_rev, _pat("txn"), _bound("txnKey")),
            Triple(new_rev, _pat("recordedAt"), _bound("now")),
            *((Triple(new_rev, _pat("asserts"), _bound("addGraph")),) if patch else ()),
        )),) if has_receipt else ()),
    )
    return Operation.build(
        "create-if-absent-named-graph" + _suffix(dataset_guard, receipt),
        (*_ROW_PARAMS, Param("payloadTriples", Kind.PAYLOAD), *named.params()),
        Group(where), guards=guards, insert=insert,
    )


def _row_delete(b: Bindings, *, dataset_guard: bool, receipt: str) -> tuple:
    """The version row's triples a replace or tombstone removes, which are its seq, its head when a receipt names one, and under the
    dataset guard its epoch."""
    root = ParamRef("root")
    row = ((Triple(root, _pat("epoch"), _bound("rowEpoch")),) if dataset_guard else ())
    head = ((Triple(root, _pat("head"), _optional("prevRev")),) if receipt != "none" else ())
    return GraphBlock(b.graph("metaGraphPrefix"), (*row, Triple(root, _pat("seq"), ParamRef("expectedSeq")), *head))


def _sweep_delete(b: Bindings, named: _Named, *, dataset_guard: bool, receipt: str = "receipt") -> tuple:
    return (
        GraphBlock(named.graph(Binding.BOUND), (Triple(_optional("s"), _optional("p"), _optional("o")),)),
        _row_delete(b, dataset_guard=dataset_guard, receipt=receipt),
    )


def _row_where(b: Bindings, *, binds: tuple, dataset_guard: bool, sweep, receipt: str = "receipt") -> tuple:
    """The `WHERE` of replace and tombstone, which differ only in their templates. `binds` come first, then the
    optional dataset guard, the version row, the claim check, and last the `sweep` of what the aggregate holds."""
    root = ParamRef("root")
    epoch = Var("rowEpoch") if dataset_guard else ParamRef("epoch")
    meta = b.graph("metaGraphPrefix")
    return (
        *binds,
        *(_dataset_guard(b) if dataset_guard else ()),
        GraphBlock(meta, (
            Triple(root, _pat("epoch"), epoch),
            Triple(root, _pat("seq"), ParamRef("expectedSeq")),
            *((Optional_(Group((Triple(root, _pat("head"), Var("prevRev")),))),) if receipt != "none" else ()),
            NotExists(Group((GraphBlock(meta, (Triple(root, _pat("deleted"), _TRUE),)),))),
        )),
        NotExists(Group((GraphBlock(b.graph("txnGraph"), (Triple(ParamRef("txnId"), _pat("rev"), _ANY),)),))),
        *(_claim_binds() if receipt != "none" else ()),
        sweep,
    )


def _named_where(b: Bindings, named: _Named, *, dataset_guard: bool, receipt: str = "receipt", deltas: tuple = ()) -> tuple:
    sweep = Optional_(Group((GraphBlock(named.graph(), (Triple(Var("s"), Var("p"), Var("o")),)),)))
    binds = (*named.binds(), *(_log_binds(b) if receipt != "none" else ()), *_delta_binds(*deltas))
    return _row_where(b, binds=binds, dataset_guard=dataset_guard, sweep=sweep, receipt=receipt)


def _replace_insert(b: Bindings, data: Graph, *, receipt: str, log: str) -> tuple:
    """The `INSERT` of a replace, whichever family. A patch log writes the caller's delta, in two slots, into the two graphs the receipt
    names (H2.6b-Q1 and Q2)."""
    root, epoch, new_rev = ParamRef("root"), ParamRef("epoch"), ParamRef("newRev")
    has_receipt, patch = receipt != "none", receipt == "patch-log"
    return (
        GraphBlock(data, (PayloadSlot("payloadTriples"),)),
        *((_delta_block("add", PayloadSlot("assertTriples")), _delta_block("del", PayloadSlot("retractTriples"))) if patch else ()),
        GraphBlock(b.graph("metaGraphPrefix"), (
            Triple(root, _pat("epoch"), epoch), Triple(root, _pat("seq"), ParamRef("nextSeq")),
            *((Triple(root, _pat("head"), new_rev),) if has_receipt else ()),
        )),
        _claim_block(b),
        *((GraphBlock(graph_var(log, Binding.BOUND), (
            Triple(new_rev, A, _pat("Revision")), Triple(new_rev, _pat("target"), root), Triple(new_rev, _pat("epoch"), epoch),
            Triple(new_rev, _pat("seq"), ParamRef("nextSeq")), Triple(new_rev, _pat("prevRev"), _optional("prevRev")),
            Triple(new_rev, _pat("txn"), _bound("txnKey")), Triple(new_rev, _pat("recordedAt"), _bound("now")),
            *((Triple(new_rev, _pat("asserts"), _bound("addGraph")), Triple(new_rev, _pat("retracts"), _bound("delGraph"))) if patch else ()),
        )),) if has_receipt else ()),
    )


def _tombstone_insert(b: Bindings, *, receipt: str) -> tuple:
    """The `INSERT` of a tombstone, whichever family. A patch log copies what the sweep found into the del graph (H2.6b-Q1)."""
    root, epoch, new_rev = ParamRef("root"), ParamRef("epoch"), ParamRef("newRev")
    has_receipt, patch = receipt != "none", receipt == "patch-log"
    return (
        *((_delta_block("del", Triple(_optional("s"), _optional("p"), _optional("o"))),) if patch else ()),
        GraphBlock(b.graph("metaGraphPrefix"), (
            Triple(root, _pat("epoch"), epoch), Triple(root, _pat("seq"), ParamRef("nextSeq")),
            *((Triple(root, _pat("head"), new_rev),) if has_receipt else ()), Triple(root, _pat("deleted"), _TRUE),
        )),
        _claim_block(b),
        *((GraphBlock(graph_var("logGraph", Binding.BOUND), (
            Triple(new_rev, A, _pat("Revision")), Triple(new_rev, A, _pat("Deletion")), Triple(new_rev, _pat("target"), root),
            Triple(new_rev, _pat("epoch"), epoch), Triple(new_rev, _pat("seq"), ParamRef("nextSeq")),
            Triple(new_rev, _pat("prevRev"), _optional("prevRev")), Triple(new_rev, _pat("txn"), _bound("txnKey")),
            Triple(new_rev, _pat("recordedAt"), _bound("now")), Triple(new_rev, _pat("cause"), ParamRef("cause")),
            Triple(new_rev, _pat("actor"), ParamRef("actor")),
            *((Triple(new_rev, _pat("retracts"), _bound("delGraph")),) if patch else ()),
        )),) if has_receipt else ()),
    )


def _replace_params(receipt: str) -> tuple:
    return (*_CAS_PARAMS, Param("payloadTriples", Kind.PAYLOAD), *((Param("assertTriples", Kind.PAYLOAD), Param("retractTriples", Kind.PAYLOAD)) if receipt == "patch-log" else ()))


def _tombstone_params(receipt: str) -> tuple:
    return (*_CAS_PARAMS, *((Param("cause", Kind.IRI), Param("actor", Kind.IRI)) if receipt != "none" else ()))


def _replace(b: Bindings, *, guards: bool, dataset_guard: bool, graph_names: str, receipt: str = "receipt") -> Operation:
    _check_receipt(receipt)
    named = _Named(b, graph_names)
    deltas = ("add", "del") if receipt == "patch-log" else ()
    return Operation.build(
        "cas-replace-named-graph" + _suffix(dataset_guard, receipt),
        (*_replace_params(receipt), *named.params()),
        Group(_named_where(b, named, dataset_guard=dataset_guard, receipt=receipt, deltas=deltas)), guards=guards,
        insert=_replace_insert(b, named.graph(Binding.BOUND), receipt=receipt, log="logGraph"),
        delete=_sweep_delete(b, named, dataset_guard=dataset_guard, receipt=receipt),
    )


def _tombstone(b: Bindings, *, guards: bool, dataset_guard: bool, graph_names: str, receipt: str = "receipt") -> Operation:
    _check_receipt(receipt)
    named = _Named(b, graph_names)
    deltas = ("del",) if receipt == "patch-log" else ()
    return Operation.build(
        "tombstone-delete-named-graph" + _suffix(dataset_guard, receipt),
        (*_tombstone_params(receipt), *named.params()),
        Group(_named_where(b, named, dataset_guard=dataset_guard, receipt=receipt, deltas=deltas)), guards=guards,
        insert=_tombstone_insert(b, receipt=receipt),
        delete=_sweep_delete(b, named, dataset_guard=dataset_guard, receipt=receipt),
    )


def _unconditional(b: Bindings, *, guards: bool, graph_names: str) -> Operation:
    named = _Named(b, graph_names)
    return Operation.build(
        "unconditional-write",
        (Param("root", Kind.IRI), Param("payloadTriples", Kind.PAYLOAD), *named.params()),
        Group(named.binds()), guards=guards,
        insert=(GraphBlock(named.graph(Binding.BOUND), (PayloadSlot("payloadTriples"),)),),
    )


# ---- the composite family


def _composite_sweep(b: Bindings) -> Optional_:
    """The root and every member the owned path reaches, in the data graph. The path can match no steps, so the first
    `?s` is the root itself."""
    return Optional_(Group((GraphBlock(b.graph("dataGraph"), (
        Triple(ParamRef("root"), b.path("ownedPath"), Var("s")),
        Triple(Var("s"), Var("p"), Var("o")),
    )),)))


def _composite_delete(b: Bindings, *, dataset_guard: bool, receipt: str = "receipt") -> tuple:
    return (
        GraphBlock(b.graph("dataGraph"), (Triple(_optional("s"), _optional("p"), _optional("o")),)),
        _row_delete(b, dataset_guard=dataset_guard, receipt=receipt),
    )


def _composite_create(b: Bindings, *, guards: bool, dataset_guard: bool, receipt: str = "receipt") -> Operation:
    _check_receipt(receipt)
    meta = b.graph("metaGraphPrefix")
    root, epoch, new_rev = ParamRef("root"), ParamRef("epoch"), ParamRef("newRev")
    has_receipt, patch = receipt != "none", receipt == "patch-log"
    where = (
        *(_log_binds(b) if has_receipt else ()),
        *(_delta_binds("add") if patch else ()),
        *(_dataset_guard(b) if dataset_guard else ()),
        NotExists(Group((GraphBlock(meta, (Triple(root, _pat("seq"), _ANY),)),))),
        NotExists(Group((GraphBlock(b.graph("dataGraph"), (Triple(root, Var("anyP"), Var("anyO")),)),))),
        NotExists(Group((GraphBlock(b.graph("txnGraph"), (Triple(ParamRef("txnId"), _pat("rev"), _ANY),)),))),
        *(_claim_binds() if has_receipt else ()),
    )
    insert = (
        GraphBlock(b.graph("dataGraph"), (PayloadSlot("payloadTriples"),)),
        *((_delta_block("add", PayloadSlot("payloadTriples")),) if patch else ()),
        GraphBlock(meta, (
            Triple(root, A, _pat("VersionRow")), Triple(root, _pat("epoch"), epoch),
            Triple(root, _pat("seq"), _long("1")), *((Triple(root, _pat("head"), new_rev),) if has_receipt else ()),
        )),
        _claim_block(b),
        *((GraphBlock(graph_var("logGraph", Binding.BOUND), (
            Triple(new_rev, A, _pat("Revision")), Triple(new_rev, _pat("target"), root), Triple(new_rev, _pat("epoch"), epoch),
            Triple(new_rev, _pat("seq"), _long("1")), Triple(new_rev, _pat("txn"), _bound("txnKey")),
            Triple(new_rev, _pat("recordedAt"), _bound("now")),
            *((Triple(new_rev, _pat("asserts"), _bound("addGraph")),) if patch else ()),
        )),) if has_receipt else ()),
    )
    return Operation.build(
        "create-if-absent-composite" + _suffix(dataset_guard, receipt),
        (*_ROW_PARAMS, Param("payloadTriples", Kind.PAYLOAD)),
        Group(where), guards=guards, insert=insert,
    )


def _composite_replace(b: Bindings, *, guards: bool, dataset_guard: bool, receipt: str = "receipt") -> Operation:
    _check_receipt(receipt)
    # the receipt goes to ?logGraph2, a copy of ?logGraph that the templates have always had (plan 4.2, fact 4)
    binds = (*(_log_binds(b) + (Bind(Var("logGraph"), Var("logGraph2")),) if receipt != "none" else ()), *_delta_binds(*(("add", "del") if receipt == "patch-log" else ())))
    return Operation.build(
        "cas-replace-composite-property" + _suffix(dataset_guard, receipt),
        _replace_params(receipt),
        Group(_row_where(b, binds=binds, dataset_guard=dataset_guard, sweep=_composite_sweep(b), receipt=receipt)),
        guards=guards, insert=_replace_insert(b, b.graph("dataGraph"), receipt=receipt, log="logGraph2"),
        delete=_composite_delete(b, dataset_guard=dataset_guard, receipt=receipt),
    )


def _composite_tombstone(b: Bindings, *, guards: bool, dataset_guard: bool, receipt: str = "receipt") -> Operation:
    _check_receipt(receipt)
    binds = (*(_log_binds(b) if receipt != "none" else ()), *_delta_binds(*(("del",) if receipt == "patch-log" else ())))
    return Operation.build(
        "tombstone-delete-composite" + _suffix(dataset_guard, receipt),
        _tombstone_params(receipt),
        Group(_row_where(b, binds=binds, dataset_guard=dataset_guard, sweep=_composite_sweep(b), receipt=receipt)),
        guards=guards, insert=_tombstone_insert(b, receipt=receipt), delete=_composite_delete(b, dataset_guard=dataset_guard, receipt=receipt),
    )


def _append_version(b: Bindings, *, guards: bool, dataset_guard: bool, delta: bool = False) -> Operation:
    """The write of a family that appends versions (formal-methods H2.6c, `dal:AppendVersions`). The guard is the version row of the
    identity at the expected seq, and the txn claim. Nothing is swept or deleted. The new version's own triples come from the payload
    slot, the new version is linked to the prior current one with `pat:previousVersion` (R2, never `fnd:supersededBy`), the row moves its seq, head and current version, and the receipt is
    written. The version names its receipt with `pat:revision`, as an event does. A member the caller does not restate stays where it
    is and is reached from the new version by reference (VH-Q2), so the payload holds only the new version's own triples."""
    meta = b.graph("metaGraphPrefix")
    root, epoch, new_rev, new_version = ParamRef("root"), ParamRef("epoch"), ParamRef("newRev"), ParamRef("newVersion")
    row_epoch = Var("rowEpoch") if dataset_guard else epoch
    where = (
        *_log_binds(b),
        *(_dataset_guard(b) if dataset_guard else ()),
        GraphBlock(meta, (
            Triple(root, _pat("epoch"), row_epoch),
            Triple(root, _pat("seq"), ParamRef("expectedSeq")),
            Optional_(Group((Triple(root, _pat("head"), Var("prevRev")),))),
            Optional_(Group((Triple(root, _pat("currentVersion"), Var("priorVersion")),))),
            NotExists(Group((GraphBlock(meta, (Triple(root, _pat("deleted"), _TRUE),)),))),
        )),
        NotExists(Group((GraphBlock(b.graph("txnGraph"), (Triple(ParamRef("txnId"), _pat("rev"), _ANY),)),))),
        *_claim_binds(),
    )
    row = (Triple(root, _pat("epoch"), _bound("rowEpoch")),) if dataset_guard else ()
    delete = (GraphBlock(meta, (
        *row, Triple(root, _pat("seq"), ParamRef("expectedSeq")), Triple(root, _pat("head"), _optional("prevRev")),
        Triple(root, _pat("currentVersion"), _optional("priorVersion")),
    )),)
    insert = (
        GraphBlock(b.graph("dataGraph"), (
            Triple(new_version, _pat("revision"), new_rev),
            Triple(new_version, _pat("previousVersion"), _optional("priorVersion")),
            PayloadSlot("payloadTriples"),
            *((PayloadSlot("addedMembers"), PayloadSlot("droppedMembers")) if delta else ()),
        )),
        GraphBlock(meta, (
            Triple(root, _pat("epoch"), epoch), Triple(root, _pat("seq"), ParamRef("nextSeq")), Triple(root, _pat("head"), new_rev),
            Triple(root, _pat("currentVersion"), new_version),
        )),
        _claim_block(b),
        GraphBlock(graph_var("logGraph", Binding.BOUND), (
            Triple(new_rev, A, _pat("Revision")), Triple(new_rev, _pat("target"), root), Triple(new_rev, _pat("epoch"), epoch),
            Triple(new_rev, _pat("seq"), ParamRef("nextSeq")), Triple(new_rev, _pat("prevRev"), _optional("prevRev")),
            Triple(new_rev, _pat("txn"), _bound("txnKey")), Triple(new_rev, _pat("recordedAt"), _bound("now")),
        )),
    )
    return Operation.build(
        "append-version" + ("-delta" if delta else "") + ("-dataset-guard" if dataset_guard else ""),
        (
            *_CAS_PARAMS, Param("newVersion", Kind.IRI), Param("payloadTriples", Kind.PAYLOAD),
            *((Param("addedMembers", Kind.PAYLOAD), Param("droppedMembers", Kind.PAYLOAD)) if delta else ()),
        ),
        Group(where), guards=guards, insert=insert, delete=delete,
    )


def _members(b: Bindings, *, guards: bool) -> Operation:
    """The members of a version of a family under `dal:DeltaMembership` (formal-methods H2.6f), from the chain back to the nearest
    checkpoint. A member is listed by an event at a version `?w` of the chain, from `$version` back to the checkpoint `?cp`: under
    the domain's membership property (a checkpoint's full list) or by `pat:addsMember`. It is a member of `$version` unless a later
    version of the chain, nearer to `$version`, drops it. A member dropped and added again is listed by the later add. A version
    that adds and drops one member lists it, since the drop must be later. The nearest checkpoint is the one with no other checkpoint
    between it and `$version`, found in a sub-select so that a store finds the one checkpoint before it joins the chain and the members (H2.8c,
    TD-68). Every `NOT EXISTS` names its graph, which the sub-select form needs on rdflib (TSD-34). A step and a closure, `pat:previousVersion ?y . ?y pat:previousVersion* ?w`, is written for "strictly before", since rdflib evaluates the one path `pat:previousVersion/pat:previousVersion*` about six times slower (FMH-H2-6f). A version with no checkpoint before it has no members, so the first version of a family must be one.
    `$membershipProperty` names the domain's membership property, for example `aeo:hasLocation`, as a parameter because a family
    declares none. A domain shape runs over these results and never over the stored delta (H2.6f-Q4)."""
    version, prop = ParamRef("version"), ParamRef("membershipProperty")
    cp, later, w, x, y, z, member = Var("cp"), Var("later"), Var("w"), Var("x"), Var("y"), Var("z"), Var("member", kind=Kind.IRI)
    previous = Step(URIRef(str(PAT["previousVersion"])))
    before = Path(PropertyPath.encode(Star(previous)))
    data = b.graph("dataGraph")
    return Operation.build(
        "members",
        (Param("version", Kind.IRI), Param("membershipProperty", Kind.IRI)),
        Group((GraphBlock(data, (
            SubSelect(Select((cp,)), Group((
                Triple(cp, _pat("checkpoint"), _TRUE),
                Triple(version, before, cp),
                NotExists(Group((GraphBlock(data, (
                    Triple(later, _pat("checkpoint"), _TRUE), Triple(later, _pat("previousVersion"), y), Triple(y, before, cp), Triple(version, before, later),
                )),))),
            ))),
            Triple(version, before, w),
            Triple(w, before, cp),
            Union_((
                Group((Triple(w, prop, member),)),
                Group((Triple(w, _pat("addsMember"), member),)),
            )),
            NotExists(Group((GraphBlock(data, (
                Triple(x, _pat("dropsMember"), member), Triple(x, _pat("previousVersion"), z), Triple(z, before, w), Triple(version, before, x),
            )),))),
        )),)),
        guards=guards,
        select=Select((member,), distinct=True),
    )


def _payload_check(b: Bindings, *, guards: bool) -> Operation:
    """The subjects of a payload outside the aggregate (formal-methods H2.8b, ADR-A123 decision 6, PL-B). A caller loads its payload into a local
    graph, binds `$root` to the node the payload starts at, and runs this. Every subject must be the root or be reached from it by the owned
    path, which can take no steps, so a family that owns nothing admits the root alone. An empty result passes. The path is walked over the
    payload alone, from a node that is the subject of a triple, so the result does not depend on how a store reads a zero-length path from a
    term in no triple (TSD-08). It reads no store."""
    graph = b.graph("payloadGraph")
    s, root = Var("s", kind=Kind.IRI), ParamRef("root")
    outside = (
        NotExists(Group((GraphBlock(graph, (Triple(root, b.path("ownedPath"), s),)),)))
        if b.has("ownedPath") else Filter(TermGuard(s, root, negated=True))
    )
    return Operation.build(
        "payload-check",
        (Param("root", Kind.IRI),),
        Group((GraphBlock(graph, (Triple(s, Var("p"), Var("o")), outside)),)),
        guards=guards,
        select=Select((s,), distinct=True),
    )


# ---- the key claims

_KEY_CLAIM = "KeyClaim"


def _other_owner(b: Bindings, claim: ParamRef, owner: ParamRef, other: str) -> NotExists:
    """`FILTER NOT EXISTS { GRAPH keys { claim pat:claimedBy ?other . FILTER(?other != owner) } }`. That `?other` is an IRI is a
    data invariant, from the patterns guide's shape on `pat:claimedBy` (`sh:nodeKind sh:IRI`), assumed here and not proved by the
    types."""
    var = Var(other, kind=Kind.IRI)
    return NotExists(Group((GraphBlock(b.graph("keysGraph"), (
        Triple(claim, _pat("claimedBy"), var),
        Filter(ValueGuard("!=", var, owner)),
    )),)))


def _claim_triples(b: Bindings, claim: ParamRef, owner: ParamRef) -> tuple:
    return (
        Triple(claim, A, _pat(_KEY_CLAIM)),
        Triple(claim, _pat("constraint"), b.const("constraintId")),
        Triple(claim, _pat("claimedBy"), owner),
    )


def _key_claim_write(b: Bindings, *, guards: bool) -> Operation:
    claim, owner = ParamRef("claim"), ParamRef("owner")
    return Operation.build(
        "key-claim-write",
        (Param("claim", Kind.IRI), Param("owner", Kind.IRI)),
        Group((_other_owner(b, claim, owner, "other"),)),
        guards=guards,
        insert=(GraphBlock(b.graph("keysGraph"), _claim_triples(b, claim, owner)),),
    )


def _key_claim_write_dual(b: Bindings, *, guards: bool) -> Operation:
    current, following, owner = ParamRef("claimCurrent"), ParamRef("claimNext"), ParamRef("owner")
    return Operation.build(
        "key-claim-write-dual",
        (Param("claimCurrent", Kind.IRI), Param("claimNext", Kind.IRI), Param("owner", Kind.IRI)),
        Group((_other_owner(b, current, owner, "otherCurrent"), _other_owner(b, following, owner, "otherNext"))),
        guards=guards,
        insert=(GraphBlock(b.graph("keysGraph"), (*_claim_triples(b, current, owner), *_claim_triples(b, following, owner))),),
    )


def _key_claim_retire(b: Bindings, *, guards: bool) -> Operation:
    claim, owner = ParamRef("claim"), ParamRef("owner")
    keys = b.graph("keysGraph")
    return Operation.build(
        "key-claim-retire",
        (Param("claim", Kind.IRI), Param("owner", Kind.IRI), Param("now", Kind.LITERAL)),
        Group((GraphBlock(keys, (Triple(claim, _pat("claimedBy"), owner),)),)),
        guards=guards,
        delete=(GraphBlock(keys, (Triple(claim, _pat("claimedBy"), owner),)),),
        insert=(GraphBlock(keys, (Triple(claim, _pat("retiredBy"), owner), Triple(claim, _pat("retiredAt"), ParamRef("now")))),),
    )


def _duplicated_claims(b: Bindings, *, project) -> SubSelect:
    """The claims with more than one owner, from the keys graph, scoped to one constraint."""
    claim, owner = Var("claim"), Var("owner")
    return SubSelect(
        Select(project, group_by=(claim,), having=(ValueGuard(">", Func("COUNT", (owner,)), _int(1)),)),
        Group((GraphBlock(b.graph("keysGraph"), (
            Triple(claim, A, _pat(_KEY_CLAIM)), Triple(claim, _pat("constraint"), b.const("constraintId")),
            Triple(claim, _pat("claimedBy"), owner),
        )),)),
    )


def _key_claim_quarantine(b: Bindings, *, guards: bool) -> Operation:
    claim, other, now = Var("claim"), Var("other"), Var("now")
    quarantine = b.graph("keyQuarantineGraph")
    return Operation.build(
        "key-claim-quarantine",
        (),
        Group((
            _duplicated_claims(b, project=(claim,)),
            GraphBlock(b.graph("keysGraph"), (Triple(claim, _pat("claimedBy"), other),)),
            NotExists(Group((GraphBlock(quarantine, (Triple(claim, _pat("quarantinedOwner"), other),)),))),
            Bind(Func("NOW"), now),
        )),
        guards=guards,
        insert=(GraphBlock(quarantine, (
            Triple(_bound("claim"), _pat("quarantinedOwner"), _bound("other")),
            Triple(_bound("claim"), _pat("quarantinedAt"), _bound("now")),
            Triple(_bound("claim"), _pat("constraint"), b.const("constraintId")),
        )),),
    )


def _key_claim_merge_rewrite(b: Bindings, *, guards: bool) -> Operation:
    """The canonical owner is the lowest owner IRI, taken over the IRI text and turned back into an IRI, because rdflib's `MIN` over
    IRIs returns a plain literal (TSD-16, decided in FMH-H2-5, decision 1). The Mustache template says the same."""
    claim, owner, canonical = Var("claim"), Var("owner"), Var("canonical")
    other = Var("other", kind=Kind.IRI)
    relation = b.const("mergeRelation")
    keys = b.graph("keysGraph")
    return Operation.build(
        "key-claim-merge-rewrite",
        (),
        Group((
            _duplicated_claims(b, project=(claim, Projected(Func("IRI", (Func("MIN", (Func("STR", (owner,)),)),)), canonical))),
            GraphBlock(keys, (Triple(claim, _pat("claimedBy"), other),)),
            Filter(ValueGuard("!=", other, Var("canonical", kind=Kind.IRI))),
            NotExists(Group((GraphBlock(keys, (Triple(other, relation, canonical),)),))),
        )),
        guards=guards,
        insert=(GraphBlock(keys, (Triple(_bound("other"), relation, _bound("canonical")),)),),
    )


# ---- the audits

_VALUE = dict(compare=Compare.VALUE)


def _count(name: str, argument: Var, alias: str, *, distinct: bool = False) -> Projected:
    return Projected(Func(name, (argument,), distinct=distinct), Var(alias))


def _key_claim_duplicate_audit(b: Bindings, *, guards: bool) -> Operation:
    claim, owner = Var("claim", kind=Kind.IRI), Var("owner")
    return Operation.build(
        "key-claim-duplicate-audit",
        (),
        Group((GraphBlock(b.graph("keysGraph"), (
            Triple(claim, A, _pat(_KEY_CLAIM)), Triple(claim, _pat("constraint"), b.const("constraintId")),
            Triple(claim, _pat("claimedBy"), owner),
        )),)),
        guards=guards,
        select=Select(
            (claim, _count("COUNT", owner, "n"), Projected(Func("GROUP_CONCAT", (Func("STR", (owner,)),), separator=" "), Var("owners"))),
            group_by=(claim,),
            having=(ValueGuard(">", Func("COUNT", (owner,)), _int(1)),),
        ),
    )


def _fork_detection_audit(b: Bindings, *, guards: bool) -> Operation:
    rev, txn = Var("rev", kind=Kind.IRI), Var("t")
    return Operation.build(
        "fork-detection-audit",
        (),
        Group((GraphBlock(b.graph("txnGraph"), (Triple(txn, _pat("rev"), rev),)),)),
        guards=guards,
        select=Select(
            (rev, _count("COUNT", txn, "n", distinct=True)),
            group_by=(rev,),
            having=(ValueGuard(">", Func("COUNT", (txn,), distinct=True), _int(1)),),
        ),
    )


def _log_values(b: Bindings) -> Values:
    """`VALUES ?log { <pinned graph> {{{logGraphs}}} }`. The pinned head is the SPARQL realisation of receipt retention, so ?log
    ranges over receipts and has the role LOG (plan 4.3, NQ2)."""
    return Values(Var("log"), (b.const("pinnedGraph"), RegistrySlot("logGraphs")))


_LOG_GRAPHS = Param("logGraphs", Kind.REGISTRY_LIST)


def _revision_multi_txn_audit(b: Bindings, *, guards: bool) -> Operation:
    rev, txn = Var("rev", kind=Kind.IRI), Var("t")
    return Operation.build(
        "revision-multi-txn-audit",
        (_LOG_GRAPHS,),
        Group((_log_values(b), GraphBlock(graph_var("log"), (Triple(rev, A, _pat("Revision")), Triple(rev, _pat("txn"), txn))))),
        guards=guards,
        select=Select(
            (rev, _count("COUNT", txn, "n", distinct=True)),
            group_by=(rev,),
            having=(ValueGuard(">", Func("COUNT", (txn,), distinct=True), _int(1)),),
        ),
    )


def _txn_multi_revision_audit(b: Bindings, *, guards: bool) -> Operation:
    rev, txn = Var("rev"), Var("t", kind=Kind.STRING)
    return Operation.build(
        "txn-multi-revision-audit",
        (_LOG_GRAPHS,),
        Group((_log_values(b), GraphBlock(graph_var("log"), (Triple(rev, A, _pat("Revision")), Triple(rev, _pat("txn"), txn))))),
        guards=guards,
        select=Select(
            (txn, _count("COUNT", rev, "n", distinct=True)),
            group_by=(txn,),
            having=(ValueGuard(">", Func("COUNT", (rev,), distinct=True), _int(1)),),
        ),
    )


def _gap_scan_audit(b: Bindings, *, guards: bool) -> Operation:
    """For each version row with sequence S and retention low-water mark L, the receipts with seq in the closed range L to S
    must number exactly S - L + 1. Positions are compared as terms in guards and as values in audits (plan 4.3, step 12), so
    `?seq`, `?S` and `?L` declare `Compare.VALUE`: the stored positions are `xsd:long`, and a receipt written by hand with another
    integer type would otherwise be missed."""
    target = Var("target", kind=Kind.IRI)
    seq, last, low, lwm = (Var(n, Kind.POSITION, Compare.VALUE) for n in ("seq", "S", "L", "lwm"))
    return Operation.build(
        "gap-scan-audit",
        (_LOG_GRAPHS,),
        Group((
            GraphBlock(b.graph("metaGraphPrefix"), (Triple(target, A, _pat("VersionRow")), Triple(target, _pat("seq"), last))),
            Optional_(Group((GraphBlock(b.graph("retentionGraph"), (Triple(target, _pat("retentionLowWaterMark"), lwm),)),))),
            Bind(Func("COALESCE", (lwm, _long("1"))), low),
            Optional_(Group((
                _log_values(b),
                GraphBlock(graph_var("log"), (
                    Triple(Var("r"), A, _pat("Revision")), Triple(Var("r"), _pat("target"), target), Triple(Var("r"), _pat("seq"), seq),
                )),
                Filter(Op("&&", ValueGuard(">=", seq, low), ValueGuard("<=", seq, last))),
            ))),
        )),
        guards=guards,
        select=Select(
            (target, last, low, _count("COUNT", seq, "n", distinct=True)),
            group_by=(target, last, low),
            having=(ValueGuard("!=", Func("COUNT", (seq,), distinct=True), Op("+", Op("-", last, low), _int(1))),),
        ),
    )


def _value_guard(b: Bindings, *, guards: bool) -> Operation:
    """The value-based compare-and-set of a ``dal:NoBoundary`` target (guide §14.2, TD-43): replace the old value of one property of a
    root with a new one, only if the old value is still there. Every pattern sits in the family's ``dal:dataGraph``, which a family with
    no boundary must declare (H2.7-Q1), so the write no longer depends on what a store's default graph holds."""
    pattern = (Triple(ParamRef("root"), b.const("guardProperty"), ParamRef("oldValue")),)
    data = b.graph("dataGraph")
    return Operation.build(
        "cas-replace-value-guard",
        (Param("root", Kind.IRI), Param("oldValue", Kind.IRI_OR_LITERAL), Param("newValue", Kind.IRI_OR_LITERAL)),
        Group((GraphBlock(data, pattern),)),
        guards=guards,
        delete=(GraphBlock(data, pattern),),
        insert=(GraphBlock(data, (Triple(ParamRef("root"), b.const("guardProperty"), ParamRef("newValue")),)),),
    )


Builder = Callable[[Bindings, bool, str], Operation]

BUILDERS: dict[str, Builder] = {
    "bootstrap-version-row": lambda b, guards, names: _bootstrap(b, guards=guards, dataset_guard=False),
    "bootstrap-version-row-dataset-guard": lambda b, guards, names: _bootstrap(b, guards=guards, dataset_guard=True),
    "append-event": lambda b, guards, names: _append(b, guards=guards, dataset_guard=False),
    "append-event-dataset-guard": lambda b, guards, names: _append(b, guards=guards, dataset_guard=True),
    "create-if-absent-named-graph": lambda b, guards, names: _create(b, guards=guards, dataset_guard=False, graph_names=names),
    "create-if-absent-named-graph-dataset-guard": lambda b, guards, names: _create(b, guards=guards, dataset_guard=True, graph_names=names),
    "cas-replace-named-graph": lambda b, guards, names: _replace(b, guards=guards, dataset_guard=False, graph_names=names),
    "cas-replace-named-graph-dataset-guard": lambda b, guards, names: _replace(b, guards=guards, dataset_guard=True, graph_names=names),
    "tombstone-delete-named-graph": lambda b, guards, names: _tombstone(b, guards=guards, dataset_guard=False, graph_names=names),
    "tombstone-delete-named-graph-dataset-guard": lambda b, guards, names: _tombstone(b, guards=guards, dataset_guard=True, graph_names=names),
    "unconditional-write": lambda b, guards, names: _unconditional(b, guards=guards, graph_names=names),
    "cas-replace-value-guard": lambda b, guards, names: _value_guard(b, guards=guards),
    "create-if-absent-composite": lambda b, guards, names: _composite_create(b, guards=guards, dataset_guard=False),
    "create-if-absent-composite-dataset-guard": lambda b, guards, names: _composite_create(b, guards=guards, dataset_guard=True),
    "cas-replace-composite-property": lambda b, guards, names: _composite_replace(b, guards=guards, dataset_guard=False),
    "cas-replace-composite-property-dataset-guard": lambda b, guards, names: _composite_replace(b, guards=guards, dataset_guard=True),
    "append-version": lambda b, guards, names: _append_version(b, guards=guards, dataset_guard=False),
    "append-version-dataset-guard": lambda b, guards, names: _append_version(b, guards=guards, dataset_guard=True),
    "append-version-delta": lambda b, guards, names: _append_version(b, guards=guards, dataset_guard=False, delta=True),
    "append-version-delta-dataset-guard": lambda b, guards, names: _append_version(b, guards=guards, dataset_guard=True, delta=True),
    "members": lambda b, guards, names: _members(b, guards=guards),
    "payload-check": lambda b, guards, names: _payload_check(b, guards=guards),
    "tombstone-delete-composite": lambda b, guards, names: _composite_tombstone(b, guards=guards, dataset_guard=False),
    "tombstone-delete-composite-dataset-guard": lambda b, guards, names: _composite_tombstone(b, guards=guards, dataset_guard=True),
    "key-claim-write": lambda b, guards, names: _key_claim_write(b, guards=guards),
    "key-claim-write-dual": lambda b, guards, names: _key_claim_write_dual(b, guards=guards),
    "key-claim-retire": lambda b, guards, names: _key_claim_retire(b, guards=guards),
    "key-claim-quarantine": lambda b, guards, names: _key_claim_quarantine(b, guards=guards),
    "key-claim-merge-rewrite": lambda b, guards, names: _key_claim_merge_rewrite(b, guards=guards),
    "key-claim-duplicate-audit": lambda b, guards, names: _key_claim_duplicate_audit(b, guards=guards),
    "fork-detection-audit": lambda b, guards, names: _fork_detection_audit(b, guards=guards),
    "gap-scan-audit": lambda b, guards, names: _gap_scan_audit(b, guards=guards),
    "revision-multi-txn-audit": lambda b, guards, names: _revision_multi_txn_audit(b, guards=guards),
    "txn-multi-revision-audit": lambda b, guards, names: _txn_multi_revision_audit(b, guards=guards),
}


def _receipt_variants() -> dict:
    """The writes of a family that records a patch log or no receipt (formal-methods H2.6d), each with its dataset-guard variant, keyed by stem."""
    out: dict = {}
    for receipt, tag in (("patch-log", "-patch-log"), ("none", "-no-receipt")):
        for stem, build_one, named in (
            ("create-if-absent-named-graph", _create, True), ("cas-replace-named-graph", _replace, True),
            ("tombstone-delete-named-graph", _tombstone, True), ("create-if-absent-composite", _composite_create, False),
            ("cas-replace-composite-property", _composite_replace, False), ("tombstone-delete-composite", _composite_tombstone, False),
        ):
            for guard in (False, True):
                key = stem + tag + ("-dataset-guard" if guard else "")
                if named:
                    out[key] = lambda b, guards, names, f=build_one, g=guard, r=receipt: f(b, guards=guards, dataset_guard=g, graph_names=names, receipt=r)
                else:
                    out[key] = lambda b, guards, names, f=build_one, g=guard, r=receipt: f(b, guards=guards, dataset_guard=g, receipt=r)
    return out


BUILDERS.update(_receipt_variants())
"""The ported operations, keyed by template stem. A template with no entry is still rendered by Mustache."""


def build(template: str, context: Mapping, *, guards: bool = True, graph_names: str = "query") -> Operation:
    """The typed operation for the template named ``template``, from the operation's compile-time bindings.
    ``guards`` is false for a caller whose own code checks every parameter (ADR-A123, addendum of 2026-10-12).
    ``graph_names`` is ``caller`` for an operation that names the root's graph, to have the caller name it as ``$g``
    (second addendum of 2026-10-12). It changes only the operations that name a graph, and is the one place the
    output is a change and not a port. An unknown value is refused for every builder, not only those that name a graph."""
    _check_graph_names(graph_names)
    return BUILDERS[template](Bindings(context), guards, graph_names)


def build_recording(
    template: str, context: Mapping, *, guards: bool = True, graph_names: str = "query"
) -> tuple[Operation, set[str]]:
    """As :func:`build`, with the names of the bindings the builder read."""
    _check_graph_names(graph_names)
    bindings = Bindings(context)
    return BUILDERS[template](bindings, guards, graph_names), bindings.read


__all__ = ["BUILDERS", "GRAPH_ROLES", "Bindings", "build", "build_recording", "graph_var"]
