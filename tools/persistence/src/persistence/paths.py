# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Compiling an ownership tree to one SPARQL property path (ADR-A122 decision 3, sketch §6).

SPARQL property paths are regular expressions over predicates. The owned edges of a boundary
shape form a finite automaton whose states are the owned shapes, so the set of members is a regular
language over steps, and state elimination turns it into a single path expression. One pattern with
that path sweeps the aggregate in time linear in its size. Recursion becomes ``*``, an edge from child
to parent becomes ``^``, and SPARQL's path semantics terminate on cyclic data.

The expression is a small tree (:class:`Eps`, :class:`Step`, :class:`Seq`, :class:`Alt`, :class:`Star`,
:class:`Opt`) built by smart constructors that keep it small and give one canonical form, so the
rendered text does not depend on the order the owned edges were visited. The text reaches a template
only through :class:`persistence.terms.PropertyPath`, which renders every predicate through
``Iri.encode``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Hashable, Iterable, Optional

from rdflib import URIRef

from .terms import Iri


class PathExpr:
    """A property path expression. Abstract."""

    __slots__ = ()


@dataclass(frozen=True)
class Eps(PathExpr):
    """The empty path. It matches the root itself."""


@dataclass(frozen=True)
class Step(PathExpr):
    """One hop, forward (``<p>``) or inverse (``^<p>``)."""

    predicate: URIRef
    inverse: bool = False


@dataclass(frozen=True)
class Seq(PathExpr):
    parts: tuple[PathExpr, ...]


@dataclass(frozen=True)
class Alt(PathExpr):
    options: tuple[PathExpr, ...]


@dataclass(frozen=True)
class Star(PathExpr):
    inner: PathExpr


@dataclass(frozen=True)
class Opt(PathExpr):
    inner: PathExpr


def _grouped(expr: PathExpr) -> str:
    """``expr`` in parentheses, unless an alternative already is."""
    text = render(expr)
    return text if isinstance(expr, Alt) else "(" + text + ")"


def render(expr: PathExpr) -> str:
    """The SPARQL text of ``expr``. Every predicate goes through :meth:`Iri.encode`."""
    if isinstance(expr, Step):
        return ("^" if expr.inverse else "") + Iri.encode(str(expr.predicate))
    if isinstance(expr, Seq):
        return "/".join(render(part) for part in expr.parts)
    if isinstance(expr, Alt):
        return "(" + "|".join(render(option) for option in expr.options) + ")"
    if isinstance(expr, Star):
        return _grouped(expr.inner) + "*"
    if isinstance(expr, Opt):
        return _grouped(expr.inner) + "?"
    raise ValueError("the empty path has no rendering of its own")


# ---- smart constructors


def seq(a: Optional[PathExpr], b: Optional[PathExpr]) -> Optional[PathExpr]:
    """``a`` then ``b``. ``None`` (no path) absorbs, ``Eps`` is the identity, nested sequences flatten."""
    if a is None or b is None:
        return None
    if isinstance(a, Eps):
        return b
    if isinstance(b, Eps):
        return a
    parts = (*(a.parts if isinstance(a, Seq) else (a,)), *(b.parts if isinstance(b, Seq) else (b,)))
    return Seq(parts)


def alt(a: Optional[PathExpr], b: Optional[PathExpr]) -> Optional[PathExpr]:
    """``a`` or ``b``. ``None`` is the identity. Options are flattened, de-duplicated and sorted by their
    rendering. An empty option makes the whole optional, and an optional option is unwrapped into one."""
    if a is None:
        return b
    if b is None:
        return a
    options: dict[str, PathExpr] = {}
    optional = False

    def add(expr: PathExpr) -> None:
        nonlocal optional
        if isinstance(expr, Alt):
            for option in expr.options:
                add(option)
        elif isinstance(expr, Eps):
            optional = True
        elif isinstance(expr, Opt):
            optional = True
            add(expr.inner)
        else:
            options[render(expr)] = expr

    add(a)
    add(b)
    if not options:
        return Eps()
    ordered = tuple(options[key] for key in sorted(options))
    core: PathExpr = ordered[0] if len(ordered) == 1 else Alt(ordered)
    if not optional or isinstance(core, Star):
        return core
    return Opt(core)


def star(x: PathExpr) -> PathExpr:
    """Zero or more of ``x``."""
    if isinstance(x, Eps):
        return x
    if isinstance(x, Star):
        return x
    if isinstance(x, Opt):
        return Star(x.inner)
    return Star(x)


# ---- state elimination

_START = "\x00start"
_FINAL = "\x00final"
LEAF = URIRef("urn:x-persistence:leaf")
"""The state of an owned edge that names no ``sh:node``. A node reached that way is a member with no
owned edges of its own."""


def eliminate(
    states: Iterable[Hashable],
    transitions: Iterable[tuple[Hashable, Hashable, PathExpr]],
    root: Hashable,
) -> Optional[PathExpr]:
    """The path expression for every walk from ``root`` through ``transitions``, ending in any state.

    ``states`` must hold ``root`` and every transition's endpoints. Each state is eliminated in sorted
    order (by its string), so the result is a function of the automaton and not of the order its
    transitions were listed in. The result contains the empty path, since ``root`` itself is matched."""
    table: dict[tuple[Hashable, Hashable], PathExpr] = {}

    def put(source: Hashable, target: Hashable, expr: Optional[PathExpr]) -> None:
        table[(source, target)] = alt(table.get((source, target)), expr)  # type: ignore[assignment]

    for source, target, expr in transitions:
        put(source, target, expr)
    table[(_START, root)] = Eps()
    ordered = sorted(set(states), key=lambda s: (s == LEAF, str(s)))
    for state in ordered:
        table[(state, _FINAL)] = Eps()
    for state in ordered:
        loop = table.pop((state, state), None)
        middle: PathExpr = star(loop) if loop is not None else Eps()
        incoming = [(source, expr) for (source, target), expr in table.items() if target == state]
        outgoing = [(target, expr) for (source, target), expr in table.items() if source == state]
        for source, before in incoming:
            for target, after in outgoing:
                put(source, target, seq(seq(before, middle), after))
        for key in [k for k in table if state in k]:
            del table[key]
    return table.get((_START, _FINAL))


__all__ = ["PathExpr", "Eps", "Step", "Seq", "Alt", "Star", "Opt", "LEAF", "render", "seq", "alt", "star", "eliminate"]
