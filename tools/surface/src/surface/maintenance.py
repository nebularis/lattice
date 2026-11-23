# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI
"""The operations that keep a promotion contract's materialised rows current from a write's delta (projection maintenance, PM1,
PM-Q1 (a'), PM-Q2 (a), PM-Q9).

A write sends, in the same request after its own update, two operations a contract: ``clear`` deletes the rows of every carrier the
delta can have changed, and ``fill`` inserts them again from the source as the write left it. The carriers the delta can have changed
are its touched nodes, the subjects and the IRI objects of its asserted and retracted triples, and every node that reaches one of them
by a proper prefix of the contract's read path. A carrier whose link to a touched node the write removed is itself touched, as that
link's subject or object, so it is found too. The work is the rows of those carriers, never the whole source.

Rows are keyed to the carrier they derive from (PM-Q1 (a')). The derived partition is named by the caller as ``$derived``: the source's
own graph for placement (ii), beside the source, or the graph of the source's derived family for placement (iii). The source is
``$source``, a named graph. A source in a shared data graph, and an index contract, whose symbols are minted under its naming policy,
are not maintained in the write yet and are refused by name (TD-138).

That pair reads the one graph ``$source`` names. The studio's writer and the surface simulator keep a source's rows another way, a partition
clear and :func:`fill_all` over the whole source, and a promotion that reads across graphs adds :func:`reach`, which names the other sources a
write changes. :func:`fill_all` reads what the read path reads, each hop in the graph that holds it and a carrier typed by a subclass, as the
compiler's rebuild over the merged world does.

The operations are typed IR values of the persistence compiler (ADR-A123), so they are rendered, guarded and statically checked as every
generated write is, and the touched nodes are a rows slot the caller fills. A caller whose delta touches nothing sends neither, since
there is nothing to maintain."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from rdflib import URIRef
from rdflib.namespace import RDF, RDFS

from persistence.ir import (
    Bind, Binding, Const, Filter, Graph, GraphBlock, GraphRole, Group, Kind, Operation, Param, ParamRef, Path, RowValues, RowsSlot, Select,
    SubSelect, TermGuard, Triple, Union_, Var,
)
from persistence.paths import Alt, Seq, Star, Step
from persistence.terms import Iri, PropertyPath

from .model import Contract, PathStep


class MaintenanceRefused(ValueError):
    """A contract whose rows are not maintained in the write, with the reason."""

    def __init__(self, contract: URIRef, reason: str) -> None:
        super().__init__(f"{contract}: {reason}")
        self.contract, self.reason = contract, reason


PLACEMENTS = ("beside", "derived")
"""PM-Q9 (ii), the source's own graph, and (iii), a graph of the source's derived family. (i) stores nothing and (iv) is tier 2."""


@dataclass(frozen=True)
class Maintenance:
    """The two operations of one contract, in the order a write sends them."""

    contract: URIRef
    key: str
    clear: Operation
    fill: Operation


def _step(step: PathStep) -> Step:
    return Step(URIRef(str(step.prop)), inverse=step.inverse)


def _seq(steps: Sequence[PathStep]):
    parts = tuple(_step(s) for s in steps)
    return parts[0] if len(parts) == 1 else Seq(parts)


def _path(expr) -> Path:
    return Path(PropertyPath.encode(expr))


def _iri(value) -> Const:
    return Const(Iri.encode(str(value)))


def _carriers(steps: Sequence[PathStep], source: Graph) -> tuple:
    """`?c` for each touched node `?t`: the node itself, and every node that reaches it by a proper prefix of the read path."""
    touched, carrier = Var("t", kind=Kind.IRI), Var("c")
    itself = Group((Bind(touched, carrier),))
    if len(steps) == 1:
        return (itself,)
    prefixes = tuple(_seq(steps[:n]) for n in range(1, len(steps)))
    prefix = prefixes[0] if len(prefixes) == 1 else Alt(prefixes)
    return (Union_((itself, Group((GraphBlock(source, (Triple(carrier, _path(prefix), touched),)),)))),)


def check(contract: Contract) -> None:
    """Refuses what this backend does not maintain."""
    if contract.is_index:
        raise MaintenanceRefused(contract.iri, "an index contract mints its symbols under its naming policy, which the write does not do yet (TD-138)")
    if contract.promotes_to is None:
        raise MaintenanceRefused(contract.iri, "a promotion names the property it promotes to (srf:promotesTo)")
    if not contract.path:
        raise MaintenanceRefused(contract.iri, "a promotion names a read property or path")


def maintenance(contract: Contract, *, guards: bool = True) -> Maintenance:
    """The clear and fill operations of ``contract``, a promotion, for a named-graph source."""
    check(contract)
    source, derived = Graph(GraphRole.DATA, ParamRef("source")), Graph(GraphRole.DERIVED, ParamRef("derived"))
    rows = RowValues((Var("t", kind=Kind.IRI),), RowsSlot("touched"))
    carrier, value = Var("c"), Var("v")
    promoted = _iri(contract.promotes_to)
    params = (Param("source", Kind.IRI), Param("derived", Kind.IRI), Param("touched", Kind.ROWS))
    carriers = _carriers(contract.path, source)
    bound = lambda v: Var(v.name, binding=Binding.BOUND)
    # a one-step path finds its carriers among the touched nodes alone, so its clear reads no source
    clear_params = params if len(contract.path) > 1 else params[1:]
    clear = Operation.build(
        f"maintain-{contract.key}-clear", clear_params,
        Group((rows, *carriers, GraphBlock(derived, (Triple(carrier, promoted, value),)))),
        guards=guards,
        delete=(GraphBlock(derived, (Triple(bound(carrier), promoted, bound(value)),)),),
    )
    fill = Operation.build(
        f"maintain-{contract.key}-fill", params,
        Group((rows, *carriers, GraphBlock(source, (
            Triple(carrier, _iri(RDF.type), _iri(contract.carrier)),
            Triple(carrier, _path(_seq(contract.path)), value),
        )))),
        guards=guards,
        insert=(GraphBlock(derived, (Triple(bound(carrier), promoted, bound(value)),)),),
    )
    return Maintenance(contract.iri, contract.key, clear, fill)


SCOPES = ("source", "world")
"""What a fill reads. ``source`` reads the one graph it fills for, as the studio's own promotions do, since each reads one family of aggregates
that hold the nodes it follows. ``world`` reads what a promotion's read path reads, which is the compiler's rule, the one a promotion means."""

SUBCLASS_SEGMENTS = 3
"""A subclass edge of the carrier's hierarchy may lie in any graph of the world. The fill follows a chain of such edges that changes graph at
most ``SUBCLASS_SEGMENTS - 1`` times, each segment of any length within one graph. A SPARQL path cannot leave a graph, so a longer chain of
graph changes is a limit of this form, where the compiler's rebuild over the merged world has none."""

_SUBCLASS = Step(RDFS.subClassOf)
_SUBCLASS_ONE_OR_MORE = Path(PropertyPath.encode(Seq((_SUBCLASS, Star(_SUBCLASS)))))
_TYPE = Const(Iri.encode(str(RDF.type)))


def _world(name: str) -> Graph:
    return Graph(GraphRole.WORLD, Var(name))


def _below(top, out: Var, tag: str, *, itself: bool) -> tuple:
    """The branches that give ``out`` a class at or below ``top`` (a constant or a bound variable), one for each number of graphs the chain of
    ``rdfs:subClassOf`` edges passes through, up to ``SUBCLASS_SEGMENTS``. A branch is a group of patterns, joined in the group they are put in.
    ``itself`` adds the branch where ``out`` is ``top``."""
    branches = []
    if itself:
        branches.append((Bind(top, out),))
    for n in range(1, SUBCLASS_SEGMENTS + 1):
        names = [Var(f"{tag}{i}") for i in range(1, n)]
        chain = (top, *reversed(names), out)
        # from the end that is bound, each segment in a graph of its own: the nearest the top first
        steps = []
        upper = top
        for i in range(n):
            lower = out if i == n - 1 else names[n - 2 - i]
            steps.append(GraphBlock(_world(f"{tag}g{i + 1}"), (Triple(lower, _SUBCLASS_ONE_OR_MORE, upper),)))
            upper = lower
        branches.append(tuple(steps))
    return tuple(branches)


def _carrier_classes(contract: Contract, out: Var) -> SubSelect:
    """``out``: the carrier and every class below it, in any graph of the world. It is evaluated once, on its own."""
    top = _iri(contract.carrier)
    groups = tuple(Group(branch) for branch in _below(top, out, "m", itself=True))
    return SubSelect(Select((out,)), Group((Union_(groups),)))


def _hop(step: PathStep, graph: str, near: Var, far: Var) -> GraphBlock:
    """``near`` to ``far`` along ``step`` in a graph of the world, whichever graph holds the triple."""
    subject, obj = (far, near) if step.inverse else (near, far)
    return GraphBlock(_world(graph), (Triple(subject, _iri(step.prop), obj),))


def fill_all(contract: Contract, *, guards: bool = True, scope: str = "world") -> Operation:
    """Every row of ``contract`` for the carriers typed in its source, for a write that replaces the source whole and sends the partition
    clear first. It reads the source as the request leaves it, so the rows are right whether the guarded write applied or found its row stale.

    With scope ``world`` a carrier is typed in the source by the carrier's class or by a class below it in any graph, and each hop of the
    read path is read in whichever graph holds it, which is what the compiler's rebuild reads over the merged world. A write to another graph
    that holds a hop or the subclass edge changes these rows, and :func:`reach` names the sources it does. With scope ``source`` every
    pattern reads the source alone, which the studio's own promotions keep, each reading one family of aggregates."""
    check(contract)
    if scope not in SCOPES:
        raise MaintenanceRefused(contract.iri, f"a fill reads one of {SCOPES}, not {scope!r}")
    source, derived = Graph(GraphRole.DATA, ParamRef("source")), Graph(GraphRole.DERIVED, ParamRef("derived"))
    carrier, value = Var("c"), Var("v")
    bound = lambda v: Var(v.name, binding=Binding.BOUND)
    promoted = _iri(contract.promotes_to)
    params = (Param("source", Kind.IRI), Param("derived", Kind.IRI))
    insert = (GraphBlock(derived, (Triple(bound(carrier), promoted, bound(value)),)),)
    if scope == "source":
        where = Group((GraphBlock(source, (
            Triple(carrier, _iri(RDF.type), _iri(contract.carrier)),
            Triple(carrier, _path(_seq(contract.path)), value),
        )),))
    else:
        classes = Var("k")
        nodes = [Var(f"x{i}") for i in range(1, len(contract.path))]
        ends = [carrier, *nodes, value]
        hops = tuple(_hop(step, f"g{i + 1}", ends[i], ends[i + 1]) for i, step in enumerate(contract.path))
        where = Group((_carrier_classes(contract, classes), GraphBlock(source, (Triple(carrier, _TYPE, classes),)), *hops))
    return Operation.build(f"maintain-{contract.key}-fill-all", params, where, guards=guards, insert=insert)


def reach(contract: Contract, *, guards: bool = True) -> Operation:
    """The sources whose rows a write changes through ``contract``, found from the triples it added and removed (``{{{delta}}}``, rows of
    ``?s ?p ?o``) and the world it leaves, a query that names each source ``?src`` once.

    A triple changes the rows of a carrier when it is the hop of the read path that starts at a node the carrier reaches, so for the hop
    ``i`` whose property the triple has, the carriers are those that reach the triple's start by the hops before it, in whichever graphs hold
    them. A triple of ``rdfs:subClassOf`` changes the carriers that are an instance of its subject or of a class below it. The source is
    each graph that types such a carrier by the carrier's class or one below it. The reverse reading is exact on the world before the write,
    for the first hop the write changes has all its predecessors in place on both sides of it, so the query may run before the write is sent."""
    check(contract)
    delta = RowValues((Var("s"), Var("p"), Var("o")), RowsSlot("delta"))
    src, carrier, classes = Var("src"), Var("c"), Var("k")
    steps = contract.path
    typed = (_carrier_classes(contract, classes), GraphBlock(Graph(GraphRole.WORLD, src), (Triple(carrier, _TYPE, classes),)))
    groups = []
    for i, step in enumerate(steps):
        start = Var("o") if step.inverse else Var("s")
        elements = [delta, Filter(TermGuard(Var("p"), _iri(step.prop)))]
        if step.inverse:
            elements.append(Filter(_is_iri(Var("o"))))
        # the carriers reach `start` by the hops before this one, read backwards from the end that is bound
        later = start
        for j in range(i - 1, -1, -1):
            nearer = carrier if j == 0 else Var(f"r{j}")
            elements.append(_hop(steps[j], f"h{j + 1}", nearer, later))
            later = nearer
        if i == 0:
            elements.append(Bind(start, carrier))
        # the carriers' classes first, so a store reads them once and not for each triple of the delta
        groups.append(Group((typed[0], *elements, typed[1])))
    s_var = Var("s")
    for n, branch in enumerate(_below(s_var, classes, "u", itself=True)):
        groups.append(Group((delta, Filter(TermGuard(Var("p"), _TYPE_SUBCLASS)), Filter(_is_iri(s_var)), *branch,
                             GraphBlock(Graph(GraphRole.WORLD, src), (Triple(carrier, _TYPE, classes),)))))
    return Operation.build(
        f"reach-{contract.key}", (Param("delta", Kind.ROWS),), Group((Union_(tuple(groups)),)), guards=guards,
        select=Select((src,), distinct=True),
    )


_TYPE_SUBCLASS = Const(Iri.encode(str(RDFS.subClassOf)))


def _is_iri(var: Var):
    from persistence.ir import Func

    return Func("ISIRI", (var,))


def partition_clear(*, guards: bool = True) -> Operation:
    """Every row of one source's derived partition, deleted. A write that replaces its source whole sends it before the fills, whose
    touched nodes are then every node of the new state, so a carrier the write removed loses its rows too."""
    s, p, o = Var("s"), Var("p"), Var("o")
    derived = Graph(GraphRole.DERIVED, ParamRef("derived"))
    bound = lambda v: Var(v.name, binding=Binding.BOUND)
    return Operation.build(
        "partition-clear", (Param("derived", Kind.IRI),),
        Group((GraphBlock(derived, (Triple(s, p, o),)),)),
        guards=guards,
        delete=(GraphBlock(derived, (Triple(bound(s), bound(p), bound(o)),)),),
    )


__all__ = ["Maintenance", "MaintenanceRefused", "PLACEMENTS", "SCOPES", "SUBCLASS_SEGMENTS", "check", "fill_all", "maintenance", "partition_clear", "reach"]
