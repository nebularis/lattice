# SPDX-License-Identifier: MPL-2.0
"""The skolem rule, version 1 (README §12.2): each blank node of a source becomes an IRI, so that a mapping can read its
identity with STR() and the target nodes minted from it are the same whenever the same node is in the source.

Most blank nodes are tree-shaped: each is the object of exactly one triple, from a named node or from another such
blank node. One of those is named by the source-local deterministic skolem pattern (IRI and Identity Patterns §9.2),
from the identity of the node that reaches it, the predicate that reaches it, and a hash of its own description, the
triples it is the subject of with each blank object replaced by that object's description hash. So its IRI does not
depend on the order of the triples or on anything else in the source, and changes when, and only when, its
description, its predicate or its parent's identity changes, which is RDF's own view that a blank node is nothing but
its description. Siblings with the same description, such as two authors both named Anon, are indistinguishable, so
they are numbered, and any numbering gives the same graph.

Any other blank node, one in a cycle, reached by several triples, or reached by none, is named by the revision-local
canonical-label pattern (§9.4), scoped to its component, the blank nodes connected to it through other blank nodes.
The component's triples are canonicalised with RDFC-1.0, and each node is named by the component's digest and its
canonical label, so its IRI holds while the component is unchanged. Such IRIs are reported, since they are not durable
across edits to the component.

The version is in every IRI, so a later rule can never be mistaken for this one."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable, Iterator

import pyoxigraph as ox

VERSION = "v1"
PREFIX = f"urn:mork-rdf:skolem:{VERSION}:"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class Skolemised:
    """The rewritten triples, and the blank-node components named by their canonical labels, each by its digest and
    the number of its nodes."""

    triples: list = field(default_factory=list)
    components: list = field(default_factory=list)


def skolemise(triples: Iterable[ox.Triple]) -> Iterator[ox.Triple]:
    """The triples with every blank node named by rule version 1. A generator, so the ground triples pass through as
    they arrive and only the triples that touch a blank node are held."""
    result = Skolemised()
    yield from _rule(triples, result)


def skolemise_with_report(triples: Iterable[ox.Triple]) -> Skolemised:
    result = Skolemised()
    result.triples = list(_rule(triples, result))
    return result


def _rule(triples: Iterable[ox.Triple], result: Skolemised) -> Iterator[ox.Triple]:
    held: list[ox.Triple] = []
    out_edges: dict = defaultdict(list)   # blank node -> [(predicate, object)]
    in_edges: dict = defaultdict(list)    # blank node -> [(subject, predicate)]
    for t in triples:
        s_blank, o_blank = isinstance(t.subject, ox.BlankNode), isinstance(t.object, ox.BlankNode)
        if not (s_blank or o_blank):
            yield t
            continue
        held.append(t)
        if s_blank:
            out_edges[t.subject].append((t.predicate, t.object))
        if o_blank:
            in_edges[t.object].append((t.subject, t.predicate))
    if not held:
        return
    names, canonical = _name(out_edges, in_edges, held, result)

    def term(x):
        return names[x]

    for t in held:
        if (t.subject in names or not isinstance(t.subject, ox.BlankNode)) and (t.object in names or not isinstance(t.object, ox.BlankNode)):
            yield ox.Triple(term(t.subject) if isinstance(t.subject, ox.BlankNode) else t.subject, t.predicate,
                            term(t.object) if isinstance(t.object, ox.BlankNode) else t.object)
    yield from canonical


def _components(blanks: set, out_edges: dict) -> dict:
    """Each blank node's component, the blank nodes connected to it through triples between blank nodes."""
    parent = {b: b for b in blanks}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for s, edges in out_edges.items():
        for _, o in edges:
            if isinstance(o, ox.BlankNode):
                a, b = find(s), find(o)
                if a != b:
                    parent[a] = b
    groups: dict = defaultdict(set)
    for b in blanks:
        groups[find(b)].add(b)
    return groups


def _name(out_edges: dict, in_edges: dict, held: list, result: Skolemised) -> tuple[dict, list]:
    """The tree-shaped nodes' names, and the other components' triples, already named."""
    blanks = set(out_edges) | set(in_edges)
    names: dict = {}
    canonical: list = []
    tree_roots = []
    for members in _components(blanks, out_edges).values():
        roots = [b for b in members if len(in_edges[b]) == 1 and not isinstance(in_edges[b][0][0], ox.BlankNode)]
        # A component whose every node has one incoming triple and exactly one root is a tree, since it is connected
        # and has one fewer edge between its nodes than it has nodes.
        if len(roots) == 1 and all(len(in_edges[b]) == 1 for b in members):
            tree_roots.append(roots[0])
        else:
            canonical += _name_canonically(members, held, names, result)
    _name_trees(tree_roots, out_edges, in_edges, names)
    return names, canonical


def _name_trees(roots: list, out_edges: dict, in_edges: dict, names: dict) -> None:
    """Every tree at once, so siblings in different trees, such as two authors of one work, are numbered together."""
    # Description hashes, children first.
    description: dict = {}
    order, stack = [], list(roots)
    while stack:
        b = stack.pop()
        order.append(b)
        stack.extend(o for _, o in out_edges[b] if isinstance(o, ox.BlankNode))
    for b in reversed(order):
        lines = sorted(f"{p} {('_:' + description[o]) if isinstance(o, ox.BlankNode) else o}" for p, o in out_edges[b])
        description[b] = _sha("\n".join(lines))
    # Names, parents first, numbering the siblings that share a parent, a predicate and a description.
    pending = list(roots)
    while pending:
        level, pending = pending, []
        groups: dict = defaultdict(list)
        for b in level:
            (parent, predicate), = in_edges[b]
            reached_from = str(names[parent]) if isinstance(parent, ox.BlankNode) else str(parent)
            groups[_sha(f"{VERSION}\n{reached_from}\n{predicate}\n{description[b]}")].append(b)
        for key, twins in groups.items():
            for i, b in enumerate(twins, start=1):
                names[b] = ox.NamedNode(PREFIX + key + (f"-{i}" if len(twins) > 1 else ""))
                pending.extend(o for _, o in out_edges[b] if isinstance(o, ox.BlankNode))


def _name_canonically(members: set, held: list, names: dict, result: Skolemised) -> list[ox.Triple]:
    """The component's triples, canonicalised, with each canonical label named under the component's digest. Every
    triple that touches a member is in the component, so these are its triples in the output."""
    dataset = ox.Dataset(ox.Quad(t.subject, t.predicate, t.object) for t in held if t.subject in members or t.object in members)
    dataset.canonicalize(ox.CanonicalizationAlgorithm.RDFC_1_0)
    canonical = list(dataset)
    digest = _sha("".join(sorted(f"{q} .\n" for q in canonical)))
    result.components.append((digest, len(members)))

    def term(x):
        return ox.NamedNode(f"{PREFIX}c:{digest}:{x.value}") if isinstance(x, ox.BlankNode) else x

    return [ox.Triple(term(q.subject), q.predicate, term(q.object)) for q in canonical]
