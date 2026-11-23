# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI
"""PM1: a promotion's rows kept by the write that changes their source (projection maintenance, slice PM1).
Validation Pack: docs/developer/validation/PM-1.md. Test IDs are PM1-Tn.

After any sequence of writes, the rows the clear and fill operations leave are the rows a rebuild from the source leaves, for each
placement, on rdflib and Oxigraph."""

from __future__ import annotations

import random
import unittest
import warnings

import pyoxigraph
from rdflib import Dataset, Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS

from lattice_persistence import compose
from persistence.ir_render import render
from surface.compile import compile_contract
from surface.maintenance import MaintenanceRefused, fill_all, maintenance, reach
from surface.model import PathStep, read_contracts

EX = "urn:ex:"
CARRIER, OTHER = URIRef(EX + "Order"), URIRef(EX + "Note")
A, B, C = URIRef(EX + "a"), URIRef(EX + "b"), URIRef(EX + "c")
PROMOTED = URIRef("urn:promoted#value")
SOURCE = URIRef("urn:g:source")
DERIVED = {"beside": SOURCE, "derived": URIRef("urn:g:derived")}

CONTRACT = f"""
@prefix srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#> .
@prefix fnd: <https://www.nebularis.org/neuro-semantic/lattice/foundation#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
<urn:p> a srf:SurfaceProfile ; fnd:hasIdentity <urn:p-id> ; srf:generatorVersion "g" ; srf:canonicalisationVersion "c" ;
    srf:entailmentRegime srf:NoEntailment ; srf:namingNormalisation srf:SanitisedLocalName ; srf:symbolMode srf:PunnedSymbols ;
    srf:permittedStackDepth 0 .
<urn:k> a srf:PromotionContract ; fnd:hasIdentity <urn:k-id> ; fnd:hasGovernanceState fnd:Active ; srf:contractKey "k" ;
    srf:carrier <{CARRIER}> ; srf:readProperty <{A}> ;
    srf:targetNamespace "urn:promoted#"^^xsd:anyURI ; srf:realisationMode srf:Materialised ; srf:surfaceProfile <urn:p> ;
    srf:promotesTo <{PROMOTED}> ; srf:sourceFidelity srf:ExactSource .
"""


def _contract(path=None):
    import dataclasses

    contract = read_contracts(Graph().parse(data=CONTRACT, format="turtle"))[0]
    return dataclasses.replace(contract, path=tuple(PathStep(i, p, inv) for i, (p, inv) in enumerate(path))) if path else contract


PATHS = {"one step": None, "two steps": [(B, False), (A, False)], "an inverse step": [(B, True), (A, False)]}


class Store:
    """One engine behind the two calls the tests make."""

    def __init__(self, engine: str) -> None:
        self.engine = engine
        if engine == "rdflib":
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                self.ds = Dataset()
        else:
            self.ox = pyoxigraph.Store()

    def update(self, text: str) -> None:
        if self.engine == "rdflib":
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                self.ds.update(text)
        else:
            self.ox.update(text)

    def load(self, world: dict) -> None:
        """Every graph of ``world`` (name to triples) as a named graph."""
        for name, triples in world.items():
            for s, p, o in triples:
                if self.engine == "rdflib":
                    self.ds.graph(URIRef(name)).add((s, p, o))
                else:
                    obj = pyoxigraph.NamedNode(str(o)) if isinstance(o, URIRef) else pyoxigraph.Literal(str(o))
                    self.ox.add(pyoxigraph.Quad(pyoxigraph.NamedNode(str(s)), pyoxigraph.NamedNode(str(p)), obj, pyoxigraph.NamedNode(name)))

    def sources(self, text: str) -> set:
        """The values of ``?src`` a query gives."""
        if self.engine == "rdflib":
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                return {str(row[0]) for row in self.ds.query(text)}
        return {solution["src"].value for solution in self.ox.query(text)}

    def triples(self, graph: URIRef) -> set:
        if self.engine == "rdflib":
            return {(s, p, o) for s, p, o in self.ds.graph(graph)}
        out = set()
        for q in self.ox.quads_for_pattern(None, None, None, pyoxigraph.NamedNode(str(graph))):
            o = q.object
            obj = URIRef(o.value) if isinstance(o, pyoxigraph.NamedNode) else Literal(o.value)
            out.add((URIRef(q.subject.value), URIRef(q.predicate.value), obj))
        return out


def _nt(triples) -> str:
    return " ".join(f"{s.n3()} {p.n3()} {o.n3()} ." for s, p, o in sorted(triples))


def _apply(store: Store, contract, placement: str, asserted: set, retracted: set) -> None:
    """The write's own delta, then the contract's clear and fill, in one request."""
    m = maintenance(contract)
    touched = {s for s, _, _ in asserted | retracted} | {o for _, _, o in asserted | retracted if isinstance(o, URIRef)}
    rows = " ".join(f"({t.n3()})" for t in sorted(touched))
    values = {"$source": SOURCE.n3(), "$derived": DERIVED[placement].n3()}

    def fill(op) -> str:
        text = render(op).replace("{{{touched}}}", rows)
        for name, value in values.items():
            text = text.replace(name, value)
        return text

    write = f"DELETE DATA {{ GRAPH {SOURCE.n3()} {{ {_nt(retracted)} }} }} ; INSERT DATA {{ GRAPH {SOURCE.n3()} {{ {_nt(asserted)} }} }}"
    # a delta that touches nothing has nothing to maintain, and rdflib 7.6 fails on a VALUES block with no rows
    store.update(compose(write, fill(m.clear), fill(m.fill)) if touched else write)


def _rebuilt(store: Store, contract, placement: str) -> set:
    """The rows a rebuild from the whole source gives, by walking the read path over the source's triples."""
    source = {t for t in store.triples(SOURCE) if t[1] != PROMOTED}
    out = set()
    for c in {s for s, p, o in source if p == RDF.type and o == contract.carrier}:
        frontier = {c}
        for step in contract.path:
            frontier = {o for s, p, o in source if p == step.prop and s in frontier} if not step.inverse else \
                       {s for s, p, o in source if p == step.prop and o in frontier}
        out |= {(c, PROMOTED, v) for v in frontier}
    return out


def _rows(store: Store, placement: str) -> set:
    return {t for t in store.triples(DERIVED[placement]) if t[1] == PROMOTED}


NODES = [URIRef(EX + f"n{i}") for i in range(5)]


def _random_delta(rng: random.Random, state: set, steps: list) -> tuple[set, set]:
    props = [A, B, RDF.type]
    candidate = set()
    for _ in range(rng.randint(1, 4)):
        p = rng.choice(props)
        o = rng.choice([CARRIER, OTHER]) if p == RDF.type else rng.choice(NODES + [Literal(f"v{rng.randint(0, 2)}")] if p == A else NODES)
        candidate.add((rng.choice(NODES), p, o))
    asserted = {t for t in candidate if t not in state and rng.random() < 0.6}
    retracted = set(rng.sample(sorted(state, key=str), min(len(state), rng.randint(0, 2))))
    return asserted, retracted - asserted


class MaintenanceTest(unittest.TestCase):
    def test_pm1_t1_after_any_sequence_of_writes_the_rows_are_those_a_rebuild_gives(self):
        for engine in ("rdflib", "oxigraph"):
            for name, path in PATHS.items():
                for placement in ("beside", "derived"):
                    with self.subTest(engine=engine, path=name, placement=placement):
                        contract, store, state = _contract(path), Store(engine), set()
                        rng = random.Random(f"{engine}{name}{placement}")
                        for _ in range(40):
                            asserted, retracted = _random_delta(rng, state, [])
                            _apply(store, contract, placement, asserted, retracted)
                            state = (state - retracted) | asserted
                            self.assertEqual(_rows(store, placement), _rebuilt(store, contract, placement))

    def test_pm1_t2_a_carrier_whose_type_goes_loses_its_rows_and_one_whose_type_comes_gains_them(self):
        for placement in ("beside", "derived"):
            store, contract = Store("rdflib"), _contract()
            _apply(store, contract, placement, {(NODES[0], RDF.type, CARRIER), (NODES[0], A, Literal("x"))}, set())
            self.assertEqual(_rows(store, placement), {(NODES[0], PROMOTED, Literal("x"))})
            _apply(store, contract, placement, set(), {(NODES[0], RDF.type, CARRIER)})
            self.assertEqual(_rows(store, placement), set())
            _apply(store, contract, placement, {(NODES[0], RDF.type, CARRIER)}, set())
            self.assertEqual(_rows(store, placement), {(NODES[0], PROMOTED, Literal("x"))})

    def test_pm1_t3_an_index_contract_is_refused_by_name(self):
        import dataclasses

        with self.assertRaises(MaintenanceRefused) as refused:
            maintenance(dataclasses.replace(_contract(), is_index=True))
        self.assertIn("TD-138", str(refused.exception))

    def test_pm1_t4_the_studio_contracts_each_render_a_clear_and_a_fill(self):
        from pathlib import Path

        root = Path(__file__).resolve().parents[4]
        contracts = read_contracts(Graph().parse(root / "contracts" / "config-studio" / "promotions.ttl"))
        self.assertTrue(contracts)
        for contract in contracts:
            m = maintenance(contract)
            self.assertIn("DELETE", render(m.clear))
            self.assertIn("INSERT", render(m.fill))


# --- a promotion kept by the compiler's rule: the world a read path crosses, and a carrier typed by a subclass (SVA-S2a) ----------

WORLD_GRAPHS = ["urn:g:one", "urn:g:two", "urn:g:mids", "urn:g:vocab1", "urn:g:vocab2"]
VOCABULARIES = WORLD_GRAPHS[3:]
CLASSES = [URIRef(EX + "Sub"), URIRef(EX + "Mid")]
AT = "2026-01-01T00:00:00Z"
ONE_STEP, TWO_STEPS, INVERSE = None, [(B, False), (A, False)], [(B, True), (A, False)]


def _rows_by_source(contract, world: dict) -> dict:
    """The rows the compiler's rebuild gives over the merged world, each in the source that types its carrier by the carrier's class or by a class below it."""
    merged = Graph()
    for triples in world.values():
        for t in triples:
            merged.add(t)
    assertions = compile_contract(contract, Graph().parse(data=CONTRACT, format="turtle") + merged, AT).modules["assertions"]
    rows = set(assertions.triples((None, contract.promotes_to, None)))
    below = {contract.carrier} | {c for c in set(merged.subjects(RDFS.subClassOf, None)) if contract.carrier in set(merged.transitive_objects(c, RDFS.subClassOf))}
    return {name: {row for row in rows if any((row[0], RDF.type, k) in triples for k in below)} for name, triples in world.items()}


def _held(store: Store, contract, world: dict, source: str) -> set:
    """What ``fill_all`` leaves in the partition of ``source`` when it runs over ``world``."""
    derived = URIRef("urn:g:promoted/" + source)
    text = render(fill_all(contract)).replace("$source", URIRef(source).n3()).replace("$derived", derived.n3())
    store.update(text)
    return {t for t in store.triples(derived) if t[1] == contract.promotes_to}


def _random_world(rng: random.Random) -> dict:
    nodes = [URIRef(EX + f"n{i}") for i in range(3)]
    hierarchy = [(CLASSES[0], CLASSES[1]), (CLASSES[0], CARRIER), (CLASSES[1], CARRIER)]
    world = {name: set() for name in WORLD_GRAPHS}
    for _ in range(rng.randint(10, 24)):
        name = rng.choice(WORLD_GRAPHS)
        if name in VOCABULARIES:
            child, parent = rng.choice(hierarchy)
            world[name].add((child, RDFS.subClassOf, parent))
        elif rng.random() < 0.35:
            world[name].add((rng.choice(nodes), RDF.type, rng.choice([CARRIER, *CLASSES, OTHER])))
        else:
            p = rng.choice([A, B])
            world[name].add((rng.choice(nodes), p, rng.choice(nodes) if p == B else rng.choice([Literal("x"), Literal("y"), rng.choice(nodes)])))
    return world


class PromotionRuleTest(unittest.TestCase):
    def test_s2a_t1_the_fill_over_the_world_gives_the_rows_of_the_compilers_rebuild(self):
        for engine in ("rdflib", "oxigraph"):
            for name, path in {"one step": ONE_STEP, "two steps": TWO_STEPS, "an inverse step": INVERSE}.items():
                with self.subTest(engine=engine, path=name):
                    contract, rng, hits = _contract(path), random.Random(f"s2a{engine}{name}"), 0
                    for _ in range(25):
                        world = _random_world(rng)
                        store = Store(engine)
                        store.load(world)
                        expected = _rows_by_source(contract, world)
                        for source in ("urn:g:one", "urn:g:two", "urn:g:mids"):
                            self.assertEqual(_held(store, contract, world, source), expected[source], f"{source} of {world}")
                        hits += any(expected[source] for source in expected)
                    self.assertGreater(hits, 8, "the worlds the test makes hold rows, or it tests nothing")

    def test_s2a_t2_the_sources_a_write_reaches_hold_every_source_whose_rows_it_changes(self):
        """For a random edit of a random world, each source whose rows the compiler's rebuild changes is a source the reverse lookup names over the world before the edit."""
        for engine in ("rdflib", "oxigraph"):
            for name, path in {"one step": ONE_STEP, "two steps": TWO_STEPS, "an inverse step": INVERSE}.items():
                with self.subTest(engine=engine, path=name):
                    contract, rng, changed_total = _contract(path), random.Random(f"reach{engine}{name}"), 0
                    for _ in range(70):
                        world = _random_world(rng)
                        after = {graph: set(triples) for graph, triples in world.items()}
                        added, removed, written = set(), set(), set()
                        for _ in range(rng.randint(1, 3)):
                            graph = rng.choice(WORLD_GRAPHS)
                            if after[graph] and rng.random() < 0.5:
                                triple = rng.choice(sorted(after[graph], key=str))
                                after[graph].discard(triple)
                                removed.add(triple)
                                written.add(graph)
                            else:
                                triple = _random_world(rng)[graph]
                                if triple:
                                    triple = rng.choice(sorted(triple, key=str))
                                    if triple not in after[graph]:
                                        after[graph].add(triple)
                                        added.add(triple)
                                        written.add(graph)
                        delta = added | removed
                        if not delta:
                            continue
                        rows_before, rows_after = _rows_by_source(contract, world), _rows_by_source(contract, after)
                        changed = {source for source in world if rows_before[source] != rows_after[source]}
                        store = Store(engine)
                        store.load(world)
                        text = render(reach(contract)).replace("{{{delta}}}", " ".join(f"({s.n3()} {p.n3()} {o.n3()})" for s, p, o in sorted(delta, key=str)))
                        named = store.sources(text)
                        # the graphs the edit writes are kept by the write itself, so the lookup names the others
                        changed -= written
                        self.assertLessEqual(changed, named, f"the edit {sorted(delta, key=str)} of {world}")
                        changed_total += len(changed)
                    self.assertGreater(changed_total, 4, "the edits change rows, or the test tests nothing")

    def test_s2a_t3_the_lookup_names_the_sources_a_write_reaches_and_no_others(self):
        order, other = URIRef(EX + "o"), URIRef(EX + "other")
        world = {
            "urn:g:one": {(order, RDF.type, URIRef(EX + "Sub")), (order, B, URIRef(EX + "m1"))},
            "urn:g:two": {(other, RDF.type, CARRIER), (other, B, URIRef(EX + "m2"))},
            "urn:g:mids": {(URIRef(EX + "m1"), A, Literal("x")), (URIRef(EX + "m2"), A, Literal("y"))},
            "urn:g:vocab1": {(URIRef(EX + "Sub"), RDFS.subClassOf, URIRef(EX + "Mid"))},
            "urn:g:vocab2": {(URIRef(EX + "Mid"), RDFS.subClassOf, CARRIER)},
        }
        contract = _contract(TWO_STEPS)

        def reached(*delta) -> set:
            store = Store("rdflib")
            store.load(world)
            return store.sources(render(reach(contract)).replace("{{{delta}}}", " ".join(f"({s.n3()} {p.n3()} {o.n3()})" for s, p, o in delta)))

        self.assertEqual(reached((URIRef(EX + "m1"), A, Literal("z"))), {"urn:g:one"}, "the value the second hop reads, in a graph that is no carrier's")
        self.assertEqual(reached((order, B, URIRef(EX + "m2"))), {"urn:g:one"}, "the first hop, whose start is the carrier")
        self.assertEqual(reached((URIRef(EX + "m1"), B, URIRef(EX + "m3"))), set(), "a property the path reads only from the carrier")
        self.assertEqual(reached((URIRef(EX + "unrelated"), A, Literal("z"))), set(), "a node no carrier reaches")
        self.assertEqual(reached((URIRef(EX + "Mid"), RDFS.subClassOf, URIRef(EX + "Higher"))), {"urn:g:one"}, "the instances of a class whose superclass changes, here the instance of its subclass")
        self.assertEqual(reached((URIRef(EX + "Other"), RDFS.subClassOf, URIRef(EX + "Higher"))), set(), "a class with no instance")


if __name__ == "__main__":
    unittest.main()
