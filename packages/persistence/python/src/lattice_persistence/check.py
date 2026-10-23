# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The caller check (ADR-A132 decision 2, ADR-A123 decision 5 and its addenda, plan 4.8 step 4).

:func:`refusals` tests a request against the contract of its operation before anything is sent, and says why for each failure, since a
guard that fails in the store reads as a lost race. It checks what the store cannot, or can only when the compile left the guards on:

* every required parameter is present, none is unknown, and each is of its kind. A ``Long`` or ``Position`` is an ``xsd:long`` exactly,
  on any store, so an ``xsd:integer`` is refused where a store's guard might pass it, and a literal is never an IRI,
* a caller-named ``$g`` equals the naming rule of the family,
* ``logGraphs`` holds IRIs and is not empty, unless the caller allows an audit over no graph, which then reports ``NothingExamined``,
* a payload names no subject outside the aggregate, and an append's event triples name no subject outside its events (the bound of
  :mod:`lattice_persistence.bound`),
* where the caller can say what is a version, an object on a pinned edge is one and an object on an identity edge is not (H2.6e, TD-67),
* on a version of a family under delta membership, a checkpoint lists the full set of members.

A caller who bypasses it is still checked by the guards of the store, which are the same tests where the profile has them on.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Mapping, Optional
from urllib.parse import quote

from rdflib import Graph
from rdflib import Literal as RdfLiteral
from rdflib.namespace import XSD

from .bound import outside_bound, outside_events, plain, reach
from .contract import OperationKind, ProfileOperation
from .namespaces import PAT
from .payload import Lit, Payload, PayloadError, Rows
from .terms import Iri, SparqlTermError

_XSD_LONG = str(XSD.long)
_LONG_LEXICAL = re.compile(r"^[+-]?[0-9]+$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_LONG_RANGE = range(-(2**63), 2**63)
_SLOT_KINDS = {"Payload", "Rows", "RegistryList"}


@dataclass(frozen=True, order=True)
class Refusal:
    """One reason a request is refused. ``code`` is a stable name, ``where`` the parameter or part it is about."""

    code: str
    where: str
    reason: str

    def __str__(self) -> str:
        return f"{self.code} ({self.where}): {self.reason}"


class CallerCheckError(ValueError):
    """A request the caller check refuses. ``refusals`` holds every reason, in a stable order."""

    def __init__(self, operation: ProfileOperation, refusals: tuple) -> None:
        self.refusals = refusals
        super().__init__(f"{operation.template_id} refused before sending: " + "; ".join(str(r) for r in refusals))


@dataclass(frozen=True)
class Membership:
    """What the caller says of the version it appends under delta membership: the domain's membership property, the members the version has
    once its changes are applied, and whether it is a checkpoint."""

    property: object
    members: frozenset
    checkpoint: bool = False


def _iri(value) -> Optional[str]:
    """The IRI a value is, or ``None``. A typed ``Iri`` or a plain string that is a valid IRI."""
    if isinstance(value, Iri):
        return plain(value)
    if isinstance(value, str) and not isinstance(value, Lit):
        try:
            Iri.encode(value)
        except SparqlTermError:
            return None
        return value
    return None


def _long(value) -> Optional[Refusal]:
    """A refusal text for a value that is not an ``xsd:long``, or ``None`` if it is one. Exactly ``xsd:long``, on any store."""
    if isinstance(value, bool):
        return Refusal("WrongKind", "", "a boolean is not an xsd:long")
    if isinstance(value, int):
        return None if value in _LONG_RANGE else Refusal("IllTypedLiteral", "", f"{value} is outside the range of xsd:long")
    if isinstance(value, RdfLiteral):
        datatype, lexical = (None if value.datatype is None else str(value.datatype)), str(value)
    elif isinstance(value, Lit):
        datatype, lexical = value.datatype, value.value
    else:
        return Refusal("WrongKind", "", f"{value!r} is not an xsd:long literal or an int")
    if datatype != _XSD_LONG:
        return Refusal("NotXsdLong", "", f"the datatype is {datatype or 'xsd:string'}, and a position or epoch is exactly xsd:long on every store")
    if not _LONG_LEXICAL.match(lexical) or int(lexical) not in _LONG_RANGE:
        return Refusal("IllTypedLiteral", "", f"{lexical!r} is not a valid xsd:long")
    return None


def _kind_problem(kind: str, value) -> Optional[Refusal]:
    """Why ``value`` is not of ``kind``, as a refusal with no parameter yet, or ``None``."""
    if kind == "Iri":
        return None if _iri(value) is not None else Refusal("WrongKind", "", f"{value!r} is not an IRI")
    if kind in ("Long", "Position"):
        return _long(value)
    if kind == "Digest":
        ok = isinstance(value, str) and not isinstance(value, Lit) and _DIGEST.match(value)
        return None if ok else Refusal("WrongKind", "", "a digest is 64 lower-case hexadecimal characters")
    if kind == "String":
        return None if isinstance(value, str) and not isinstance(value, Iri) else Refusal("WrongKind", "", f"{value!r} is not a string")
    if kind == "LangString":
        return None if isinstance(value, Lit) and value.lang else Refusal("WrongKind", "", "a language string is a Lit with a language tag")
    if kind == "Literal":
        return None if isinstance(value, Lit) else Refusal("WrongKind", "", "this parameter is a literal, and an IRI is not one")
    if kind == "IriOrLiteral":
        return None if isinstance(value, (Iri, Lit)) else Refusal("WrongKind", "", "this parameter is an Iri or a Lit, and a bare string is neither")
    if kind == "Payload":
        return None if isinstance(value, Payload) else Refusal("WrongKind", "", "a payload is a Payload, and a bare string is not one")
    if kind == "Rows":
        return None if isinstance(value, Rows) else Refusal("WrongKind", "", "event rows are a Rows")
    if kind == "RegistryList":
        if isinstance(value, (str, bytes)) or not hasattr(value, "__iter__"):
            return Refusal("WrongKind", "", "a list of graph IRIs is a sequence of Iri")
        return None
    return Refusal("WrongKind", "", f"unknown parameter kind {kind!r}")


def decode_literal(text: str) -> str:
    """The value of a SPARQL string literal as the compile encoded it, for a binding such as ``graphPrefix``."""
    graph = Graph().parse(data=f"<urn:x:s> <urn:x:p> {text} .", format="nt")
    return str(next(iter(graph.objects())))


def graph_name(operation: ProfileOperation, root) -> Optional[str]:
    """The graph of ``root`` by the family's naming rule (ADR-A122 decision 8): the prefix, the root encoded as ``ENCODE_FOR_URI`` does, and the
    suffix. ``None`` where the operation records no rule."""
    prefix, suffix = operation.binding("graphPrefix"), operation.binding("graphSuffix")
    if prefix is None or suffix is None:
        return None
    return decode_literal(prefix) + quote(plain(root), safe="-_.~") + decode_literal(suffix)


def refusals(
    operation: ProfileOperation,
    values: Mapping[str, object],
    *,
    allow_empty_log_graphs: bool = False,
    version_of: Optional[Callable] = None,
    membership: Optional[Membership] = None,
) -> tuple:
    """Every reason the request ``values`` for ``operation`` is refused, as a sorted tuple of :class:`Refusal`. Empty when it passes."""
    out: list = []

    def refuse(code: str, where: str, reason: str) -> None:
        out.append(Refusal(code, where, reason))

    declared = {p.name: p for p in operation.parameters}
    for name in sorted(set(values) - set(declared)):
        refuse("UnknownParameter", name, f"{operation.template_id} declares no parameter {name!r}")
    typed: dict = {}
    for name, param in sorted(declared.items()):
        if name not in values or values[name] is None:
            if param.required:
                refuse("MissingParameter", name, "a required parameter is not given")
            continue
        problem = _kind_problem(param.kind, values[name])
        if problem is not None:
            refuse(problem.code, name, problem.reason)
        else:
            typed[name] = values[name]
        if param.kind == "RegistryList" and name in typed:
            members = list(values[name])
            if not members and not allow_empty_log_graphs:
                refuse("EmptyLogGraphs", name, "an audit over no graph examines nothing and would report clean. Pass allow_empty_log_graphs to have it report NothingExamined")
            bad = [m for m in members if not isinstance(m, Iri) and _iri(m) is None]
            if bad:
                refuse("LogGraphNotIri", name, f"{bad[0]!r} is not an IRI")

    # a caller-named graph is the one the naming rule gives for the root (ADR-A123, addendum of 2026-10-12)
    for name, param in declared.items():
        if param.equals_graph_name and name in typed and "root" in typed:
            expected = graph_name(operation, typed["root"])
            if expected is None:
                refuse("GraphNameMismatch", name, "the profile records no naming rule (dal:graphIriTemplate) to check it against")
            elif _iri(typed[name]) != expected:
                refuse("GraphNameMismatch", name, f"the graph of {plain(typed['root'])} is {expected}, not {_iri(typed[name])}")

    # a payload names no subject outside the aggregate
    contract = operation.payload
    if contract is not None and contract.parameter in typed and contract.root in typed:
        payload, root = typed[contract.parameter], typed[contract.root]
        stray = outside_bound(contract, root, payload)
        if stray:
            refuse("PayloadOutsideBound", contract.parameter, f"{len(stray)} subject(s) are neither {plain(root)} nor reached from it by an owned edge, for example {stray[0]}")
        if version_of is not None:
            out.extend(_reference_modes(contract, root, payload, version_of))
        if membership is not None:
            out.extend(_membership(contract.parameter, root, payload, membership))

    # an append: rows of events, and triples about the events alone
    if operation.kind is OperationKind.APPEND:
        rows_name = next((p.name for p in operation.parameters if p.kind == "Rows"), None)
        triples_name = next((p.name for p in operation.parameters if p.kind == "Payload"), None)
        if rows_name in typed:
            rows = typed[rows_name].rows
            if not rows:
                refuse("NoEvents", rows_name, "an append holds at least one event")
            if len({r.event for r in rows}) != len(rows):
                refuse("DuplicateEvent", rows_name, "each event of a batch has its own IRI")
            if len({r.op_seq for r in rows}) != len(rows):
                refuse("DuplicateOpSeq", rows_name, "opSeq is distinct within a batch")
            if triples_name in typed:
                stray = outside_events([r.event for r in rows], typed[triples_name])
                if stray:
                    refuse("EventOutsideBound", triples_name, f"{stray[0]} is neither an event of the batch nor minted under one ({{event}}/part/...), so the append would describe it")
    return tuple(sorted(set(out)))


def _reference_modes(contract, root, payload, version_of) -> list:
    """TD-67: an object on a pinned edge is a version, and on an identity edge it is not. Every edge of every node the owned walk reaches."""
    out, by_source = [], {}
    for e in contract.edges:
        by_source.setdefault(e.source_shape, []).append(e)
    for node, shape in sorted(reach(contract, root, payload), key=str):
        for e in by_source.get(shape, ()):
            for t in payload.triples:
                if plain(t.predicate) != e.predicate or not isinstance(t.object, Iri):
                    continue
                if (plain(t.object) == node) if e.inverse else (plain(t.subject) == node):
                    target = t.subject if e.inverse else t.object
                    if isinstance(target, Iri) is False:
                        continue
                    known = version_of(target)
                    if e.reference_mode == "Pinned" and known is not True:
                        out.append(Refusal("ReferenceModeViolation", e.predicate, f"{plain(target)} is on a pinned edge and is not known to be a version"))
                    elif e.reference_mode == "ByIdentity" and known is True:
                        out.append(Refusal("ReferenceModeViolation", e.predicate, f"{plain(target)} is a version, and this edge is by identity"))
    return out


def _membership(parameter: str, version, payload: Payload, m: Membership) -> list:
    """Under delta membership a checkpoint version lists every member and states ``pat:checkpoint true``, and any other version lists none."""
    version, prop = plain(version), plain(m.property)
    listed = {plain(t.object) for t in payload.triples if plain(t.subject) == version and plain(t.predicate) == prop and isinstance(t.object, Iri)}
    marked = any(
        plain(t.subject) == version and plain(t.predicate) == str(PAT.checkpoint) and isinstance(t.object, Lit) and t.object.value == "true"
        for t in payload.triples
    )
    members = {plain(x) for x in m.members}
    if m.checkpoint and not (marked and listed == members):
        return [Refusal("CheckpointNotFull", parameter, f"a checkpoint states pat:checkpoint true and lists all {len(members)} member(s), and this lists {len(listed)}{'' if marked else ' with no pat:checkpoint'}")]
    if not m.checkpoint and (marked or listed):
        return [Refusal("UnexpectedFullList", parameter, "a version that is not a checkpoint states its changes only, and lists no member and no pat:checkpoint")]
    return []


def check_request(operation: ProfileOperation, values: Mapping[str, object], **options) -> None:
    """Raise :class:`CallerCheckError` naming every reason, or return when the request passes. The options are those of :func:`refusals`."""
    found = refusals(operation, values, **options)
    if found:
        raise CallerCheckError(operation, found)


__all__ = ["Refusal", "CallerCheckError", "Membership", "refusals", "check_request", "graph_name", "decode_literal"]
