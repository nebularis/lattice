# src/spc/encoder/subtyping.py
"""
Gay-Hole subtyping algorithm and A-Box encoding.

Implements the coinductive subtyping check for SPC local types
and encodes the results as subtypeOf assertions in the A-Box.

For ProcessLE-generated protocols, the subtyping checks that arise
are finite structural comparisons (label set containment and tree
equality). Coinductive comparison is available but rarely needed.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from rdflib import Graph, URIRef, RDF
from spc.processle import ast_nodes as ast
from spc.util.namespaces import SPC, PROTO


@dataclass(frozen=True)
class LocalType:
    """Minimal local type representation for subtyping."""
    pass


@dataclass(frozen=True)
class LTEnd(LocalType):
    pass


@dataclass(frozen=True)
class LTOutput(LocalType):
    target: str
    options: frozenset[tuple[str, str, 'LocalType']]  # (label, sort, cont)


@dataclass(frozen=True)
class LTInput(LocalType):
    source: str
    options: frozenset[tuple[str, str, 'LocalType']]


@dataclass(frozen=True)
class LTRec(LocalType):
    var: str
    body: LocalType


@dataclass(frozen=True)
class LTVar(LocalType):
    var: str


def check_subtype(t1: LocalType, t2: LocalType,
                   visited: Optional[set] = None) -> bool:
    """
    Check if t1 <: t2 using the Gay-Hole coinductive algorithm.
    Returns True if the subtyping holds.
    """
    if visited is None:
        visited = set()

    pair = (id(t1), id(t2))
    if pair in visited:
        # Coinductive hypothesis: assume true for visited pairs
        return True
    visited.add(pair)

    # [Sub-End]
    if isinstance(t1, LTEnd) and isinstance(t2, LTEnd):
        return True
    if isinstance(t1, LTEnd) or isinstance(t2, LTEnd):
        return isinstance(t1, LTEnd) and isinstance(t2, LTEnd)

    # [Sub-Rec]: unfold and recurse
    if isinstance(t1, LTRec):
        unfolded = unfold(t1)
        return check_subtype(unfolded, t2, visited)
    if isinstance(t2, LTRec):
        unfolded = unfold(t2)
        return check_subtype(t1, unfolded, visited)

    # [Sub-Out]: I ⊆ J, covariant payloads and continuations
    if isinstance(t1, LTOutput) and isinstance(t2, LTOutput):
        if t1.target != t2.target:
            return False
        labels_1 = {label for label, _, _ in t1.options}
        labels_2 = {label for label, _, _ in t2.options}
        if not labels_1.issubset(labels_2):
            return False
        opts_2 = {label: (sort, cont) for label, sort, cont in t2.options}
        for label, sort1, cont1 in t1.options:
            sort2, cont2 = opts_2[label]
            # Covariant payload sort (simplified: structural equality)
            if sort1 != sort2:
                return False
            if not check_subtype(cont1, cont2, visited):
                return False
        return True

    # [Sub-In]: I ⊇ J, contravariant payloads, covariant continuations
    if isinstance(t1, LTInput) and isinstance(t2, LTInput):
        if t1.source != t2.source:
            return False
        labels_1 = {label for label, _, _ in t1.options}
        labels_2 = {label for label, _, _ in t2.options}
        if not labels_2.issubset(labels_1):
            return False
        opts_1 = {label: (sort, cont) for label, sort, cont in t1.options}
        for label, sort2, cont2 in t2.options:
            sort1, cont1 = opts_1[label]
            # Contravariant payload sort (simplified)
            if sort1 != sort2:
                return False
            if not check_subtype(cont1, cont2, visited):
                return False
        return True

    return False


def unfold(lt: LTRec) -> LocalType:
    """Unfold a recursive type once: μt.T → T[μt.T/t]"""
    return _substitute(lt.body, lt.var, lt)


def _substitute(lt: LocalType, var: str, replacement: LocalType) -> LocalType:
    if isinstance(lt, LTVar) and lt.var == var:
        return replacement
    elif isinstance(lt, LTOutput):
        return LTOutput(
            target=lt.target,
            options=frozenset(
                (label, sort, _substitute(cont, var, replacement))
                for label, sort, cont in lt.options
            ),
        )
    elif isinstance(lt, LTInput):
        return LTInput(
            source=lt.source,
            options=frozenset(
                (label, sort, _substitute(cont, var, replacement))
                for label, sort, cont in lt.options
            ),
        )
    elif isinstance(lt, LTRec):
        if lt.var == var:
            return lt  # Shadowed
        return LTRec(var=lt.var, body=_substitute(lt.body, var, replacement))
    else:
        return lt


def compute_and_encode_subtyping(graph: Graph, protocol: ast.Protocol) -> None:
    """
    Find places where subtyping is needed (internal choice typing)
    and encode the results.

    For ProcessLE protocols, this arises when a communication has
    multiple branches — each branch's singleton output type must be
    a subtype of the combined output type.
    """
    _find_and_encode_choice_subtypes(graph, protocol.name, protocol.global_type)


def _find_and_encode_choice_subtypes(
    graph: Graph, protocol_name: str, gt: ast.GlobalType
) -> None:
    """Walk the AST and encode subtyping for multi-branch communications."""
    if isinstance(gt, ast.Communication) and len(gt.options) > 1:
        # Each singleton {lᵢ} is a subtype of the full {l₁, ..., lₙ}
        # This is trivially true by label set containment.
        # We encode it for completeness.
        full_iri = PROTO[f"{protocol_name}/subtype/full_{gt.sender}_{gt.receiver}"]
        for opt in gt.options:
            single_iri = PROTO[
                f"{protocol_name}/subtype/single_{opt.label}"
            ]
            graph.add((single_iri, SPC.subtypeOf, full_iri))

        for opt in gt.options:
            if opt.continuation:
                _find_and_encode_choice_subtypes(
                    graph, protocol_name, opt.continuation)

    elif isinstance(gt, ast.ParallelComp):
        _find_and_encode_choice_subtypes(graph, protocol_name, gt.left)
        _find_and_encode_choice_subtypes(graph, protocol_name, gt.right)

    elif isinstance(gt, ast.Recursion):
        _find_and_encode_choice_subtypes(graph, protocol_name, gt.body)

    elif isinstance(gt, ast.SubprotocolCall) and gt.continuation:
        _find_and_encode_choice_subtypes(
            graph, protocol_name, gt.continuation)