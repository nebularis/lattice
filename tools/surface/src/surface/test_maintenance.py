# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI
"""PM1: a promotion's rows kept by the write that changes their source (projection maintenance, slice PM1).
Validation Pack: docs/developer/validation/PM1.md. Test IDs are PM1-Tn.

After any sequence of writes, the rows the clear and fill operations leave are the rows a rebuild from the source leaves, for each
placement, on rdflib and Oxigraph."""

from __future__ import annotations

import random
import unittest
import warnings

import pyoxigraph
from rdflib import Dataset, Graph, Literal, URIRef
from rdflib.namespace import RDF

from lattice_persistence import compose
from persistence.ir_render import render
from surface.maintenance import MaintenanceRefused, maintenance
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


if __name__ == "__main__":
    unittest.main()
