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

from .ir import (
    A, Bind, Binding, Const, Filter, Func, Graph, GraphBlock, GraphRole, Group, Kind, NotExists, Op, Operation,
    Optional_, Param, ParamRef, Path, Triple, Var,
)
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
    "keysGraph": GraphRole.KEYS,
    "keyQuarantineGraph": GraphRole.QUARANTINE,
    "retentionGraph": GraphRole.RETENTION,
    "pinnedGraph": GraphRole.PINNED,
    # variables a query binds to a graph, each with one meaning in every template
    "g": GraphRole.DATA,
    "log": GraphRole.LOG,
    "logGraph": GraphRole.LOG,
    "logGraph2": GraphRole.LOG,
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

    where: list = []
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
            Triple(ParamRef("event"), A, ParamRef("eventType")),
            Triple(ParamRef("event"), _pat("revision"), _bound("rev")),
            Triple(ParamRef("event"), _pat("opSeq"), ParamRef("opSeq")),
            Triple(ParamRef("event"), _pat("occurredAt"), ParamRef("occurredAt")),
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
            Param("txnId", Kind.IRI), Param("requestDigest", Kind.DIGEST), Param("event", Kind.IRI),
            Param("eventType", Kind.IRI), Param("opSeq", Kind.POSITION), Param("occurredAt", Kind.IRI_OR_LITERAL),
        ),
        Group(tuple(where)),
        guards=guards,
        insert=insert,
        delete=(GraphBlock(meta, delete_triples),),
    )


Builder = Callable[[Bindings, bool], Operation]

BUILDERS: dict[str, Builder] = {
    "bootstrap-version-row": lambda b, guards: _bootstrap(b, guards=guards, dataset_guard=False),
    "bootstrap-version-row-dataset-guard": lambda b, guards: _bootstrap(b, guards=guards, dataset_guard=True),
    "append-event": lambda b, guards: _append(b, guards=guards, dataset_guard=False),
    "append-event-dataset-guard": lambda b, guards: _append(b, guards=guards, dataset_guard=True),
}
"""The ported operations, keyed by template stem. A template with no entry is still rendered by Mustache."""


def build(template: str, context: Mapping, *, guards: bool = True) -> Operation:
    """The typed operation for the template named ``template``, from the operation's compile-time bindings.
    ``guards`` is false for a caller whose own code checks every parameter (ADR-A123, addendum of 2026-10-12)."""
    return BUILDERS[template](Bindings(context), guards)


def build_recording(template: str, context: Mapping, *, guards: bool = True) -> tuple[Operation, set[str]]:
    """As :func:`build`, with the names of the bindings the builder read."""
    bindings = Bindings(context)
    return BUILDERS[template](bindings, guards), bindings.read


__all__ = ["BUILDERS", "GRAPH_ROLES", "Bindings", "build", "build_recording", "graph_var"]
