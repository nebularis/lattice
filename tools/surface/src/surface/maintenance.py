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

The operations are typed IR values of the persistence compiler (ADR-A123), so they are rendered, guarded and statically checked as every
generated write is, and the touched nodes are a rows slot the caller fills. A caller whose delta touches nothing sends neither, since
there is nothing to maintain."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from rdflib import URIRef
from rdflib.namespace import RDF

from persistence.ir import (
    Bind, Binding, Const, Graph, GraphBlock, GraphRole, Group, Kind, Operation, Param, ParamRef, Path, RowValues, RowsSlot, Triple,
    Union_, Var,
)
from persistence.paths import Alt, Seq, Step
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


__all__ = ["Maintenance", "MaintenanceRefused", "PLACEMENTS", "check", "maintenance"]
