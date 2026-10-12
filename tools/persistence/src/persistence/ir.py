# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The typed operation IR (formal-methods track H, slice H2.1, ADR-A123).

An :class:`Operation` is a frozen value built by a builder, one per operation id, and rendered to
SPARQL by :mod:`persistence.ir_render`, which refuses what the types here forbid. Nothing in this
module produces text. The values hold three kinds of thing.

Parameters
    ``Param(name, kind, required)``, declared once on the operation. A parameter is a SPARQL ``$name``
    that the caller binds per request. The kinds are the renderer's whole domain.
Compile-time constants
    :class:`Const`, which wraps an already encoded term from :mod:`persistence.terms`. A bare ``str`` is
    refused, so configuration cannot reach the query's structure (ADR-A79 point 4, unchanged).
Structure
    graph blocks, optional and negated groups, ``BIND``, ``FILTER`` and ``VALUES``. Every triple sits
    in a :class:`GraphBlock`, which names a :class:`GraphRole`, so there is no way to write a pattern
    for the default graph. No term constructor makes a blank node.

The module follows the hazard table of the specification sketch, §3. Each row is one refusal in
:mod:`persistence.ir_render`, named in :data:`persistence.ir_render.RULES`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union

from .terms import Integer, Iri, Literal, PropertyPath, SparqlTerm


class IrError(ValueError):
    """An IR value, or an operation, that the types refuse. ``rule`` names the refusal."""

    def __init__(self, rule: str, message: str) -> None:
        super().__init__(f"{rule}: {message}")
        self.rule = rule


# ---- parameters


class Kind(Enum):
    """What a parameter or variable holds. The set of parameter kinds is the renderer's whole domain."""

    IRI = "Iri"
    LONG = "Long"
    STRING = "String"
    LANG_STRING = "LangString"
    POSITION = "Position"
    DIGEST = "Digest"
    PAYLOAD = "Payload"
    REGISTRY_LIST = "RegistryList"


SLOT_KINDS = frozenset({Kind.PAYLOAD, Kind.REGISTRY_LIST})
"""Kinds that are Mustache-style request-time slots and not SPARQL variables. A set of triples or of graph
IRIs is not one RDF term, so the caller fills the slot with text before sending."""


class Compare(Enum):
    """How a position is compared. A stored position such as ``seq`` is pinned to ``xsd:long`` and matches by
    term. A value-compared position is read through ``FILTER`` and may match across numeric datatypes. The
    two are not interchangeable (review §8.2)."""

    TERM = "term"
    VALUE = "value"


class Binding(Enum):
    """Whether a variable used in a ``DELETE`` or ``INSERT`` template is bound in every solution."""

    BOUND = "Bound"
    OPTIONAL_ALLOWED = "OptionalAllowed"


_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class Param:
    name: str
    kind: Kind
    required: bool = True
    compare: Compare = Compare.TERM

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not _NAME.match(self.name):
            raise IrError("InvalidName", f"parameter name {self.name!r} is not a SPARQL variable name")
        if not isinstance(self.kind, Kind):
            raise IrError("InvalidParameterKind", f"parameter {self.name!r} has kind {self.kind!r}, not a Kind")


# ---- terms


@dataclass(frozen=True)
class Var:
    """A SPARQL variable. ``kind`` and ``compare`` say what it holds when a guard compares it. ``binding``
    is required on every use in a ``DELETE`` or ``INSERT`` template."""

    name: str
    kind: Optional[Kind] = None
    compare: Compare = Compare.TERM
    binding: Optional[Binding] = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not _NAME.match(self.name):
            raise IrError("InvalidName", f"variable name {self.name!r} is not a SPARQL variable name")


@dataclass(frozen=True)
class ParamRef:
    """A use of a declared parameter, rendered ``$name``."""

    name: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not _NAME.match(self.name):
            raise IrError("InvalidName", f"parameter name {self.name!r} is not a SPARQL variable name")


_ENCODED = (Iri, Literal, Integer)
# The characters Iri.encode refuses, so a term built without an encoder, such as Iri("<urn:x\\u003E>"), is
# refused here too. A backslash matters most, since SPARQL processes \u escapes over the whole query text.
_IRI_REF = r'<[^<>"{}|^`\\\x00-\x20]*>'
_ENCODED_FORM = re.compile(
    rf'^({_IRI_REF}|"(?:[^"\\\n\r]|\\.)*"(?:\^\^{_IRI_REF}|@[A-Za-z]+(?:-[A-Za-z0-9]+)*)?|-?[0-9]+)$'
)
_PATH_FORM = re.compile(rf'^(?:{_IRI_REF}|[\^/|*+?()!\s])+$')


@dataclass(frozen=True)
class Const:
    """A compile-time constant. It holds only a term made by :meth:`Iri.encode`, :meth:`Literal.encode` or
    :meth:`Integer.encode`, never a bare ``str`` and never a blank node."""

    term: SparqlTerm

    def __post_init__(self) -> None:
        if type(self.term) not in _ENCODED:
            raise IrError(
                "UnencodedConstant",
                f"a constant must be an Iri, Literal or Integer from persistence.terms, got {type(self.term).__name__}",
            )
        if not _ENCODED_FORM.match(str(self.term)):
            raise IrError("UnencodedConstant", f"{str(self.term)!r} is not a well formed encoded term")


@dataclass(frozen=True)
class RdfType:
    """The predicate ``a``."""


A = RdfType()


@dataclass(frozen=True)
class Path:
    """A property path. It is legal only in a ``WHERE`` pattern, since SPARQL allows no path in a template."""

    path: PropertyPath

    def __post_init__(self) -> None:
        if type(self.path) is not PropertyPath:
            raise IrError("UnencodedConstant", "a path must be made by PropertyPath.encode")
        if not _PATH_FORM.match(str(self.path)):
            raise IrError("UnencodedConstant", f"{str(self.path)!r} is not a well formed encoded path")


Node = Union[Var, ParamRef, Const]
Predicate = Union[Const, RdfType, Path, Var, ParamRef]


@dataclass(frozen=True)
class Triple:
    subject: Node
    predicate: Predicate
    object: Node


@dataclass(frozen=True)
class PayloadSlot:
    """Where the caller's payload triples go. It names a declared parameter of kind ``Payload``, and is
    rendered as the Mustache tag ``{{{name}}}``, so an unrendered slot is a syntax error and fails closed."""

    param: str


@dataclass(frozen=True)
class RegistrySlot:
    """Where the caller's list of registry-listed graph IRIs goes, inside a ``VALUES`` block."""

    param: str


# ---- graphs


class GraphRole(Enum):
    """The part of the store a graph belongs to. A pattern without a role does not exist."""

    DATA = "data"
    META = "meta"
    TXN = "txn"
    LOG = "log"
    EVENT = "event"
    KEYS = "keys"
    QUARANTINE = "quarantine"
    RETENTION = "retention"
    PINNED = "pinned"
    DATASET = "dataset"


@dataclass(frozen=True)
class Graph:
    role: GraphRole
    term: Union[Var, ParamRef, Const]

    def __post_init__(self) -> None:
        if not isinstance(self.role, GraphRole):
            raise IrError("MissingGraphRole", f"a graph needs a GraphRole, got {self.role!r}")
        if not isinstance(self.term, (Var, ParamRef, Const)):
            raise IrError("MissingGraphRole", f"a graph term must be a Var, ParamRef or Const, got {self.term!r}")


# ---- expressions


@dataclass(frozen=True)
class Func:
    """A built-in call from the fixed set in :data:`persistence.ir_render.FUNCTIONS`."""

    name: str
    args: tuple = ()
    distinct: bool = False
    separator: Optional[str] = None


@dataclass(frozen=True)
class Op:
    """An arithmetic or boolean operator. A comparison is a guard and never an ``Op``."""

    op: str
    left: "Expr"
    right: "Expr"


@dataclass(frozen=True)
class Not:
    arg: "Expr"


@dataclass(frozen=True)
class TermGuard:
    """``sameTerm``. It compares terms, so it is the guard for a position pinned to a datatype."""

    left: "Expr"
    right: "Expr"
    negated: bool = False


@dataclass(frozen=True)
class ValueGuard:
    """A value comparison, ``=``, ``!=``, ``<``, ``<=``, ``>`` or ``>=``."""

    op: str
    left: "Expr"
    right: "Expr"


Expr = Union[Var, ParamRef, Const, Func, Op, Not, TermGuard, ValueGuard]


# ---- patterns


@dataclass(frozen=True)
class Group:
    elements: tuple = ()


@dataclass(frozen=True)
class GraphBlock:
    """``GRAPH g { ... }``. Its elements are triples, a payload slot and the inner forms of a group. A
    group inside it matches in the same graph."""

    graph: Graph
    elements: tuple = ()


@dataclass(frozen=True)
class Optional_:
    group: Group


@dataclass(frozen=True)
class NotExists:
    """``FILTER NOT EXISTS { ... }``."""

    group: Group


@dataclass(frozen=True)
class Bind:
    expr: Expr
    var: Var


@dataclass(frozen=True)
class Filter:
    expr: Expr


@dataclass(frozen=True)
class Values:
    """``VALUES ?var { item ... }``. Items are constants or one registry slot."""

    var: Var
    items: tuple = ()


@dataclass(frozen=True)
class Union_:
    groups: tuple = ()


# ---- the operation


@dataclass(frozen=True)
class Projected:
    """``(expr AS ?var)`` in a ``SELECT`` list."""

    expr: Expr
    var: Var


@dataclass(frozen=True)
class Select:
    projection: tuple = ()
    group_by: tuple = ()
    having: tuple = ()


@dataclass(frozen=True)
class ParameterGuard:
    """The required-parameter guard, one type test per required parameter, such as ``isIRI($root)`` or
    ``DATATYPE($epoch) = xsd:long``, in its own group at the top of ``WHERE`` (TD-34, H2-Q4, ADR-A123 decision 5
    and its addendum). An unbound parameter makes its test an error, so the filter fails and nothing is written.
    In its own group the test runs before any pattern of ``WHERE`` could bind a missing parameter from the data.
    A type test, unlike ``BOUND``, still parses when a caller substitutes the parameter's text.

    It is derived from the parameter list by :meth:`derive`, or is :data:`GUARDS_OFF` when the caller's own code
    checks the parameters. The renderer refuses any other guard, and refuses an operation with none, so a builder
    cannot leave it out by accident."""

    params: tuple = ()
    off: bool = False

    @staticmethod
    def derive(params: tuple) -> "ParameterGuard":
        return ParameterGuard(tuple(p for p in params if p.required and p.kind not in SLOT_KINDS))


GUARDS_OFF = ParameterGuard(off=True)
"""No guard in the query. The compiled profile records it, and the caller's code must check every parameter."""


@dataclass(frozen=True)
class Operation:
    """One generated operation. ``id`` is the builder's identity, the ``dal:templateId`` of the compiled profile."""

    id: str
    params: tuple
    where: Group
    insert: tuple = ()
    delete: tuple = ()
    select: Optional[Select] = None
    guard: Optional[ParameterGuard] = None

    @classmethod
    def build(cls, id: str, params: tuple, where: Group, *, guards: bool = True, **parts) -> "Operation":
        """An operation with the guard derived from its parameters, or :data:`GUARDS_OFF` when ``guards`` is false.
        Builders use this."""
        guard = ParameterGuard.derive(params) if guards else GUARDS_OFF
        return cls(id=id, params=params, where=where, guard=guard, **parts)


__all__ = [
    "IrError", "Kind", "SLOT_KINDS", "Compare", "Binding", "Param", "Var", "ParamRef", "Const", "RdfType", "A",
    "Path", "Triple", "PayloadSlot", "RegistrySlot", "GraphRole", "Graph", "Func", "Op", "Not", "TermGuard",
    "ValueGuard", "Group", "GraphBlock", "Optional_", "NotExists", "Bind", "Filter", "Values", "Union_",
    "Projected", "Select", "ParameterGuard", "GUARDS_OFF", "Operation",
]
