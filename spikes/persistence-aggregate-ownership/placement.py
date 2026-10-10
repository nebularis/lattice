# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The placement example from the aggregate-ownership note, as data, with four ways of
deciding which nodes a deletion of the root takes with it. Read-only experiments on rdflib.
No product code is imported."""

from __future__ import annotations

from dataclasses import dataclass, field

from rdflib import RDF, SKOS, XSD, Graph, Literal, Namespace, URIRef

EX = Namespace("https://example.org/placing#")

ROOT = EX.P


def placement_graph(*, shared_policy: bool = False, inbound_quote: bool = False, shared_document: bool = False) -> Graph:
    """Our placement sketch. A policy is a reference (review AO-Q1), so it is outside the
    aggregate. ``shared_policy`` adds a second placement whose binding connects the same policy
    as the first, and ``inbound_quote`` adds a quote that refers to that policy. Neither makes
    a second owner, since the policy is not owned. ``shared_document`` adds a second placement
    whose layer attaches the first placement's owned document, which is a node with two owners."""
    g = Graph()
    add = g.add

    def typed(node, cls, **props):
        add((node, RDF.type, cls))
        for key, value in props.items():
            add((node, EX[key], value))

    # the placement, its client (outside) and its contacted markets (inside)
    typed(EX.P, EX.Placement, forClient=EX.C, marketsContacted=EX.Mc1, definedProgramme=EX.T)
    add((EX.P, EX.marketsContacted, EX.Mc2))
    typed(EX.C, EX.Client, name=Literal("A client"))
    for mc, market, date in ((EX.Mc1, EX.Axa, "2023-10-10"), (EX.Mc2, EX.Chubb, "2023-10-11")):
        typed(mc, EX.MarketContacted, contactedDate=Literal(date, datatype=XSD.date), marketType=EX.TypeCarrier, contactedMarket=market)
        typed(market, EX.Market, name=Literal(str(market).rsplit("#", 1)[1]))
    # a vocabulary concept that two owned nodes point at
    add((EX.TypeCarrier, RDF.type, SKOS.Concept))
    add((EX.TypeCarrier, SKOS.inScheme, EX.MarketTypes))
    add((EX.TypeCarrier, SKOS.prefLabel, Literal("Carrier")))
    # the tower: owned as a whole
    typed(EX.T, EX.Tower, authorisationStatus=Literal("authorised"), hasLayer=EX.L1)
    add((EX.T, EX.hasLayer, EX.L2))
    add((EX.T, EX.hasLayer, EX.L3))
    for layer in (EX.L1, EX.L2, EX.L3):
        add((layer, RDF.type, EX.Layer))
    for binding in (EX.LCB1, EX.LCB2, EX.LCB3):
        add((EX.L1, EX.hasPolicyBinding, binding))
        add((binding, RDF.type, EX.LayerContractBinding))
    add((EX.LCB1, EX.hasShare, EX.S1))
    typed(EX.S1, EX.Quant, value=Literal("1/3"))
    add((EX.LCB1, EX.connectsPolicy, EX.Pol1))
    typed(EX.Pol1, EX.Policy, status=EX.PolBound)
    add((EX.PolBound, RDF.type, SKOS.Concept))
    add((EX.PolBound, SKOS.inScheme, EX.PolicyStatuses))
    # the same property, owned in one context and a reference in another
    add((EX.L1, EX.attachment, EX.DocOwned))
    typed(EX.DocOwned, EX.Document, title=Literal("Layer slip"))
    add((EX.LCB2, EX.attachment, EX.DocShared))
    typed(EX.DocShared, EX.Document, title=Literal("Library wording"))
    if shared_policy or shared_document:
        typed(EX.P2, EX.Placement, definedProgramme=EX.T2)
        typed(EX.T2, EX.Tower, hasLayer=EX.L9)
        add((EX.L9, RDF.type, EX.Layer))
    if shared_policy:
        add((EX.L9, EX.hasPolicyBinding, EX.LCB9))
        add((EX.LCB9, RDF.type, EX.LayerContractBinding))
        add((EX.LCB9, EX.connectsPolicy, EX.Pol1))
    if shared_document:
        add((EX.L9, EX.attachment, EX.DocOwned))
    if inbound_quote:
        typed(EX.Q1, EX.Quote, basedOnPolicy=EX.Pol1)
    return g


# ---------------------------------------------------------------- ownership declarations

# Allow-list by property, flat: the object properties whose objects are owned, wherever they occur.
FLAT_OWNED = [EX.marketsContacted, EX.definedProgramme, EX.hasLayer, EX.hasPolicyBinding, EX.hasShare, EX.attachment]

# Allow-list by context: a tree from class to the properties owned from it. ``attachment`` is owned
# from a Layer and a reference from a binding, so it appears under Layer only.
OWNED_TREE: dict[URIRef, dict[URIRef, URIRef]] = {
    EX.Placement: {EX.marketsContacted: EX.MarketContacted, EX.definedProgramme: EX.Tower},
    EX.Tower: {EX.hasLayer: EX.Layer},
    EX.Layer: {EX.hasPolicyBinding: EX.LayerContractBinding, EX.attachment: EX.Document},
    EX.LayerContractBinding: {EX.hasShare: EX.Quant},
}

# Deny-list: every object property is followed except these references.
REFERENCES = {EX.forClient, EX.contactedMarket, EX.marketType, EX.status, EX.attachment, EX.connectsPolicy}
REFERENCES_FORGETTING_ONE = REFERENCES - {EX.contactedMarket}


def outgoing(g: Graph, node) -> set:
    return {(node, p, o) for p, o in g.predicate_objects(node)}


def class_of(g: Graph, node):
    return next(iter(g.objects(node, RDF.type)), None)


def is_vocabulary(g: Graph, node) -> bool:
    """The detection the user asked about: a node typed ``skos:Concept``, or in a scheme."""
    return (node, RDF.type, SKOS.Concept) in g or (node, SKOS.inScheme, None) in g


@dataclass
class Result:
    name: str
    members: set = field(default_factory=set)

    def short(self) -> list[str]:
        return sorted(str(m).rsplit("#", 1)[-1] for m in self.members)


def first_property_path(g: Graph, root=ROOT) -> Result:
    """What the compiler did before H1.4a: the first node property, in path order, followed with
    ``+``. The compiler refused this shape from H1.4a to HO5 (CompositeBoundaryMultipleProperties), and since
    HO5 it sweeps every owned edge, so this simulates a build that no longer exists. Review S1."""
    first = sorted(OWNED_TREE[EX.Placement], key=str)[0]
    rows = g.query(f"SELECT DISTINCT ?m WHERE {{ ?r <{first}>+ ?m }}", initBindings={"r": root})
    return Result("today: first property only", {row["m"] for row in rows})


def flat_alternation(g: Graph, root=ROOT) -> Result:
    alternation = "|".join(f"<{p}>" for p in FLAT_OWNED)
    rows = g.query(f"SELECT DISTINCT ?m WHERE {{ ?r ({alternation})+ ?m }}", initBindings={"r": root})
    return Result("allow-list, flat alternation", {row["m"] for row in rows})


def unrolled_paths(g: Graph, root=ROOT) -> Result:
    """Typed walk over OWNED_TREE: the property is followed only from the class that owns it."""
    members: set = set()
    stack = [root]
    while stack:
        node = stack.pop()
        for prop, child_class in OWNED_TREE.get(class_of(g, node), {}).items():
            for child in g.objects(node, prop):
                if child not in members and class_of(g, child) == child_class:
                    members.add(child)
                    stack.append(child)
    return Result("allow-list, per-class tree", members)


def unrolled_sparql(g: Graph, root=ROOT) -> Result:
    """The same closure as a UNION of explicit sequence paths, the form SPARQL can carry."""
    paths: list[str] = []

    def walk(cls, prefix):
        for prop, child in OWNED_TREE.get(cls, {}).items():
            path = f"{prefix}/<{prop}>" if prefix else f"<{prop}>"
            paths.append(path)
            walk(child, path)

    walk(EX.Placement, "")
    union = " UNION ".join(f"{{ ?r {p} ?m }}" for p in paths)
    rows = g.query(f"SELECT DISTINCT ?m WHERE {{ {union} }}", initBindings={"r": root})
    return Result("allow-list, per-class tree as SPARQL", {row["m"] for row in rows})


def deny_list(g: Graph, root=ROOT, references=REFERENCES, guard_vocabulary=False, label="complete") -> Result:
    """Follow every object property except ``references``. Optionally skip vocabulary nodes."""
    members: set = set()
    stack = [root]
    while stack:
        node = stack.pop()
        for p, o in g.predicate_objects(node):
            if isinstance(o, Literal) or p == RDF.type or p in references or o in members or o == root:
                continue
            if guard_vocabulary and is_vocabulary(g, o):
                continue
            members.add(o)
            stack.append(o)
    return Result(f"deny-list, {label}", members)


# ---------------------------------------------------------------- what a delete does

def delete_set(g: Graph, result: Result, root=ROOT) -> set:
    """Every triple whose subject is the root or a member. Datatype and object properties alike."""
    triples = set(outgoing(g, root))
    for member in result.members:
        triples |= outgoing(g, member)
    return triples


def vocabulary_hit(g: Graph, result: Result) -> set:
    """Members that are vocabulary concepts. The runtime guard: a non-empty answer refuses the delete."""
    return {m for m in result.members if is_vocabulary(g, m)}


def inbound_from_outside(g: Graph, result: Result, root=ROOT) -> set:
    inside = result.members | {root}
    return {(s, p, o) for o in inside for s, p in g.subject_predicates(o) if s not in inside}


def owners(g: Graph, roots: list, strategy=unrolled_paths) -> dict:
    """Member -> the roots whose closure holds it. More than one is a node with two owners."""
    held: dict = {}
    for root in roots:
        for member in strategy(g, root).members:
            held.setdefault(member, set()).add(root)
    return {m: r for m, r in held.items() if len(r) > 1}
