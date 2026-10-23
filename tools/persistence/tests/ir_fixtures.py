# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Shared builders for the IR tests (H2.1). A valid operation of the shape of a guarded replace, with
knobs, so a refusal test changes one thing."""

from __future__ import annotations

from persistence.ir import (
    A, Bind, Binding, Const, Filter, Func, Graph, GraphBlock, GraphRole, Group, Kind, NotExists, Operation,
    Optional_, Param, ParamRef, PayloadSlot, Triple, Var,
)
from persistence.namespaces import PAT
from persistence.terms import Integer, Iri, Literal

XSD_LONG = "http://www.w3.org/2001/XMLSchema#long"


def iri(value: str) -> Const:
    return Const(Iri.encode(value))


def pat(local: str) -> Const:
    return Const(Iri.encode(str(PAT[local])))


def string(value: str) -> Const:
    return Const(Literal.encode(value))


def integer(value: int) -> Const:
    return Const(Integer.encode(value))


def true() -> Const:
    return Const(Literal.encode("true", datatype="http://www.w3.org/2001/XMLSchema#boolean"))


def graph(role: GraphRole, name: str) -> Graph:
    return Graph(role, iri(f"urn:g:{name}"))


META = graph(GraphRole.META, "meta")
TXN = graph(GraphRole.TXN, "txn")
DATA = graph(GraphRole.DATA, "data")

ROOT, EPOCH, EXPECTED, NEXT, REV, TXN_ID = (ParamRef(n) for n in ("root", "epoch", "expectedSeq", "nextSeq", "newRev", "txnId"))

PARAMS = (
    Param("root", Kind.IRI),
    Param("epoch", Kind.LONG),
    Param("expectedSeq", Kind.POSITION),
    Param("nextSeq", Kind.POSITION),
    Param("newRev", Kind.IRI),
    Param("txnId", Kind.IRI),
    Param("payloadTriples", Kind.PAYLOAD),
)


def where() -> tuple:
    """A WHERE of the shape of a guarded replace. It binds ?logGraph and ?now, and ?prevRev only optionally."""
    return (
        Bind(Func("IRI", (Func("CONCAT", (string("urn:g:log/"), Func("SUBSTR", (Func("STR", (Func("NOW"),)), integer(1), integer(7))))),)), Var("logGraph")),
        GraphBlock(META, (
            Triple(ROOT, pat("epoch"), EPOCH),
            Triple(ROOT, pat("seq"), EXPECTED),
            Optional_(Group((Triple(ROOT, pat("head"), Var("prevRev")),))),
            NotExists(Group((GraphBlock(META, (Triple(ROOT, pat("deleted"), true()),)),))),
        )),
        NotExists(Group((GraphBlock(TXN, (Triple(TXN_ID, pat("rev"), Var("any")),)),))),
        Bind(Func("NOW"), Var("now")),
    )


def delete() -> tuple:
    return (GraphBlock(META, (Triple(ROOT, pat("seq"), EXPECTED),)),)


def insert(prev: Binding = Binding.OPTIONAL_ALLOWED, now: Binding = Binding.BOUND) -> tuple:
    bound = lambda name: Var(name, binding=Binding.BOUND)
    return (
        GraphBlock(DATA, (PayloadSlot("payloadTriples"),)),
        GraphBlock(META, (Triple(ROOT, pat("seq"), NEXT), Triple(ROOT, pat("head"), REV))),
        GraphBlock(TXN, (Triple(TXN_ID, pat("rev"), REV),)),
        GraphBlock(Graph(GraphRole.LOG, bound("logGraph")), (
            Triple(REV, A, pat("Revision")),
            Triple(REV, pat("prevRev"), Var("prevRev", binding=prev)),
            Triple(REV, pat("recordedAt"), Var("now", binding=now)),
        )),
    )


def valid(*, params=PARAMS, where_=None, delete_=None, insert_=None, **parts) -> Operation:
    return Operation.build(
        "test-replace",
        params,
        Group(where() if where_ is None else where_),
        insert=insert() if insert_ is None else insert_,
        delete=delete() if delete_ is None else delete_,
        **parts,
    )
