# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Where the writes of an operation land, stated as the compiled profile states them.

A write access of a generated operation lands in one graph, or in one family of graphs named when the operation runs. This
module reads that graph from the operation's own typed IR, from the expression of each graph block's term and the ``Bind`` of
each variable it names, and states it as a :class:`Place`. A place is a graph role and exactly one of two things:

* ``graph``, an IRI, where the graph is fixed,
* ``named``, a string template, where the graph is named when the operation runs. Its placeholders are a closed set
  (:data:`PLACEHOLDERS`), each defined once in ``ontology/persistence``.

An expression that cannot be stated that way raises :class:`LandingError`, naming the operation and the graph term. Nothing here
invents a placeholder, and nothing is a guess from an IRI pattern.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, fields, is_dataclass
from typing import Any, Iterator
from urllib.parse import quote

from .ir import Bind, Const, Func, GraphBlock, Operation, ParamRef, Var
from .terms import Iri, Literal

PLACEHOLDERS = ("root", "newRev", "month")
"""The placeholders of a graph template. `{root}` is the operation's root parameter, percent-encoded as ``ENCODE_FOR_URI`` encodes it,
`{newRev}` is its new revision parameter as it is, and `{month}` is the month of the transaction time, as ``YYYY-MM``."""

PATCH_DIRECTIONS: dict[str, str] = {"addGraph": "Added", "delGraph": "Removed"}
"""The direction of a patch log's graph, by the variable a builder binds it to. Both have the role ``patch`` (`builders.GRAPH_ROLES`)."""

_TEMPLATE_HOLE = re.compile(r"\{([^{}]*)\}")
_PLAIN_LITERAL = re.compile(r'^"([^"\\]*)"$')


class LandingError(Exception):
    """A graph an operation writes that is neither a fixed IRI nor a template of the closed placeholders."""

    def __init__(self, operation: str, graph: str, reason: str) -> None:
        self.operation = operation
        self.graph = graph
        self.reason = reason
        super().__init__(f"the operation {operation} writes a graph, {graph}, that a compiled profile cannot state as a place: {reason}")


@dataclass(frozen=True, order=True)
class Place:
    """One graph, or one family of graphs, in which an operation's data lands. ``role`` is a :class:`persistence.ir.GraphRole` value.
    Exactly one of ``graph`` and ``named`` is set, and the other is the empty string, which keeps places in a total order."""

    role: str
    graph: str = ""
    named: str = ""

    def __post_init__(self) -> None:
        if bool(self.graph) == bool(self.named):
            raise ValueError("a place states exactly one of graph and named")

    @property
    def text(self) -> str:
        """The graph or the template, whichever the place states."""
        return self.graph or self.named


@dataclass(frozen=True)
class _Hole:
    name: str
    encoded: bool = False


def _walk(node: Any) -> Iterator[Any]:
    """Every dataclass of an operation's tree, in order."""
    if is_dataclass(node) and not isinstance(node, type):
        yield node
        for f in fields(node):
            yield from _walk(getattr(node, f.name))
    elif isinstance(node, (tuple, list)):
        for item in node:
            yield from _walk(item)


class _Reader:
    """Reads the text of an expression as a list of constant strings and holes."""

    def __init__(self, operation: Operation) -> None:
        self.operation = operation
        self.params = {p.name: p for p in operation.params}
        self.binds: dict[str, Any] = {}
        for node in _walk((operation.where, operation.insert, operation.delete)):
            if isinstance(node, Bind):
                self.binds.setdefault(node.var.name, node.expr)

    def refusal(self, graph: str, reason: str) -> LandingError:
        return LandingError(self.operation.id, graph, reason)

    def parts(self, expr: Any, graph: str, seen: frozenset = frozenset()) -> list:
        if isinstance(expr, Const):
            term = expr.term
            text = str(term)
            if isinstance(term, Iri):
                return [text[1:-1]]
            if isinstance(term, Literal):
                match = _PLAIN_LITERAL.match(text)
                if match:
                    return [match.group(1)]
            raise self.refusal(graph, f"the constant {text} is not an IRI or a plain string")
        if isinstance(expr, ParamRef):
            param = self.params.get(expr.name)
            if param is not None and param.equals is not None:
                if expr.name in seen:
                    raise self.refusal(graph, f"the rule of ${expr.name} refers to itself")
                return self.parts(param.equals, graph, seen | {expr.name})
            if expr.name in ("root", "newRev"):
                return [_Hole(expr.name)]
            raise self.refusal(graph, f"${expr.name} names the graph and states no rule for it")
        if isinstance(expr, Var):
            bound = self.binds.get(expr.name)
            if bound is None or expr.name in seen:
                raise self.refusal(graph, f"?{expr.name} is not bound to an expression of constants and the closed placeholders")
            return self.parts(bound, graph, seen | {expr.name})
        if isinstance(expr, Func):
            return self._func(expr, graph, seen)
        raise self.refusal(graph, f"{type(expr).__name__} is not an expression a graph name is built from")

    def _func(self, expr: Func, graph: str, seen: frozenset) -> list:
        name, args = expr.name, expr.args
        if name in ("STR", "IRI") and len(args) == 1:
            return self.parts(args[0], graph, seen)
        if name == "CONCAT":
            return [part for arg in args for part in self.parts(arg, graph, seen)]
        if name == "ENCODE_FOR_URI" and len(args) == 1:
            inner = self.parts(args[0], graph, seen)
            if all(isinstance(p, str) for p in inner):
                return [quote("".join(inner), safe="")]
            if len(inner) == 1 and isinstance(inner[0], _Hole) and inner[0].name == "root":
                return [_Hole("root", True)]
            raise self.refusal(graph, "only the root parameter, or a constant, is percent-encoded")
        if name == "SUBSTR" and len(args) == 3 and _is_now(args[0]) and [self._integer(a) for a in args[1:]] == [1, 7]:
            return [_Hole("month")]
        raise self.refusal(graph, f"the function {name} is not one a graph name is built from")

    @staticmethod
    def _integer(expr: Any) -> int | None:
        return int(str(expr.term)) if isinstance(expr, Const) and str(expr.term).isdigit() else None

    def place(self, role: str, term: Any) -> Place:
        graph = f"?{term.name}" if isinstance(term, Var) else f"${term.name}" if isinstance(term, ParamRef) else str(getattr(term, "term", term))
        text = ""
        holes = False
        for part in self.parts(term, graph):
            if isinstance(part, str):
                if "{" in part or "}" in part:
                    raise self.refusal(graph, f"the constant text {part!r} holds a brace, which a template reserves for its placeholders")
                text += part
                continue
            if part.name == "root" and not part.encoded:
                raise self.refusal(graph, "the root parameter names the graph without being percent-encoded")
            if part.name == "newRev" and part.encoded:
                raise self.refusal(graph, "the new revision parameter is percent-encoded, which `{newRev}` is not")
            holes = True
            text += "{" + part.name + "}"
        if not text:
            raise self.refusal(graph, "the graph's name is empty")
        return Place(role, named=text) if holes else Place(role, graph=text)


def is_template_of_closed_set(template: str) -> bool:
    """Whether every placeholder of ``template`` is one of :data:`PLACEHOLDERS`."""
    return all(name in PLACEHOLDERS for name in _TEMPLATE_HOLE.findall(template))


def _is_now(expr: Any) -> bool:
    while isinstance(expr, Func) and expr.name == "STR" and len(expr.args) == 1:
        expr = expr.args[0]
    return isinstance(expr, Func) and expr.name == "NOW" and not expr.args


def write_places(operation: Operation, term_text) -> dict[tuple[str, str], Place]:
    """The place of every graph ``operation`` inserts into or deletes from, by the role and the text of the graph term, which is how
    an access names its graph (``term_text`` renders a term as `persistence.ir_render` does). A graph it only reads has none."""
    reader = _Reader(operation)
    out: dict[tuple[str, str], Place] = {}
    for block in (b for b in _walk((operation.insert, operation.delete)) if isinstance(b, GraphBlock)):
        role, term = block.graph.role, block.graph.term
        out.setdefault((role.value, term_text(term)), reader.place(role.value, term))
    return out


__all__ = ["PLACEHOLDERS", "PATCH_DIRECTIONS", "LandingError", "Place", "is_template_of_closed_set", "write_places"]
