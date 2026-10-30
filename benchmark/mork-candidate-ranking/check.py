# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""How often each way of ranking candidate target terms puts the confirmed target in its first five and first ten
(ADR-A124): BM25 over the target cards, BM25 with MTP's translation table, MORK's recognition engine
(`mork_communities.recognition`) with the target terms loaded as its concepts, and the two fused by reciprocal rank.

The confirmed pairs are the source term and each target term of every mapping of the hand-made ODRL pack, and of every
mapping the LegalRuleML history accepted, leaving out the terms a pattern supplies and no source term names, such as
ins:Template and pty:Role.

**Pass criterion.** Each source of pairs gives at least one pair, and each method ranks every pair's source. A missing
source or a method that ranks nothing fails the check. **A hit rate never does.** The figures go to `report.md` and
`report.json` here, which are generated and git-ignored. Run `mise run check:mork-candidate-ranking`."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, SKOS

HERE = Path(__file__).resolve().parent
LATTICE = "https://www.nebularis.org/neuro-semantic/lattice/"
LAYERS = ("instrument", "eligibility", "party", "behaviour", "quantification")
STRUCTURAL = {"ins:Template", "ins:Term", "pty:Role", "ins:arisesUnder", "elg:hasCondition", "elg:conditionKey", "qnt:onSpace"}
METHODS = ("BM25", "BM25 + translations", "recognition", "fused")
AT = datetime(2026, 10, 30, tzinfo=timezone.utc)


def _studio() -> Path:
    import lattice_repo_catalogue as reader

    catalogue = reader.load()
    return catalogue.root / catalogue.area("contracts") / "config-studio"


def _pairs(mapping_graph: Graph, scheme, keep, targets: dict) -> list:
    from mork_propose.history import signatures

    return [(s.source, t) for s in signatures(mapping_graph, scheme, AT) if keep(s.mapping) and s.source is not None
            for t in s.targets if str(t).startswith(LATTICE) and t in targets and targets[t].curie not in STRUCTURAL]


def cases(targets: dict) -> list:
    """(name, source cards, confirmed pairs) for the ODRL pack and the LegalRuleML history's accepted mappings."""
    from mork_propose.cards import source_card
    from mork_propose.history import MORK, History

    studio = _studio()
    odrl = source_card(Graph().parse(studio / "odrl" / "odrl22.ttl"), ["http://www.w3.org/ns/odrl/2/"])
    lrml = source_card(Graph().parse(studio / "legalruleml" / "trial" / "legalruleml-metamodel.ttl"),
                       ["http://docs.oasis-open.org/legalruleml/ns/v1.0/metamodel#"])
    pack = Graph().parse(studio / "odrl" / "odrl-instrument.mork.ttl")
    scheme = URIRef("https://www.nebularis.org/neuro-semantic/lattice/config-studio/odrl-mapping#Scheme")
    history = History(studio / "legalruleml" / "trial" / "history.ttl")
    accepted = {m for m, (d, _, _) in history.decisions().items() if d == MORK.Accepted}
    lrml_pairs = [p for s in history.graph.subjects(RDF.type, MORK.MappingScheme) for p in _pairs(history.graph, s, lambda m: m in accepted, targets)]
    return [("ODRL pack", odrl, _pairs(pack, scheme, lambda m: True, targets)), ("LegalRuleML accepted", lrml, lrml_pairs)]


def rankings(source, target_cards: list, engine) -> dict:
    """Each method's order of target IRIs for one source card."""
    from mork_propose.rank import candidates
    from mork_propose.translations import aliases

    everything = len(target_cards)
    bm = [c.iri for c, _ in candidates(source, target_cards, k=everything)]
    bm_tr = [c.iri for c, _ in candidates(source, target_cards, k=everything, aliases=aliases())]
    rec = [r.concept_iri for r in engine.recognise(source.label or source.curie.split(":")[-1])]
    fused = sorted(set(bm_tr[:50]) | set(rec[:50]), key=lambda x: (-sum(1 / (60 + o.index(x)) for o in (bm_tr, rec) if x in o), str(x)))
    return dict(zip(METHODS, (bm, bm_tr, rec, fused)))


def measure() -> dict:
    from mork_communities.namespaces import CONCEPT_NAME, DATA_CONCEPT
    from mork_communities.recognition import RecognitionEngine
    from mork_propose.cards import layer_card

    target_cards = [c for m in LAYERS for c in layer_card(m)]
    targets = {c.iri: c for c in target_cards}
    g = Graph()
    for c in target_cards:
        g.add((c.iri, RDF.type, DATA_CONCEPT))
        g.add((c.iri, SKOS.prefLabel, Literal(c.label)))
        g.add((c.iri, CONCEPT_NAME, Literal(c.curie.split(":")[-1])))
    engine = RecognitionEngine(g, max_candidates=len(target_cards), min_score=0.0)
    out = {"cases": []}
    for name, source_cards, pairs in cases(targets):
        sources = {c.iri: c for c in source_cards}
        pairs = sorted({p for p in pairs if p[0] in sources})
        hits = {m: [0, 0] for m in METHODS}
        ranked = defaultdict(int)
        for s, t in pairs:
            for method, order in rankings(sources[s], target_cards, engine).items():
                ranked[method] += bool(order)
                r = order.index(t) + 1 if t in order else None
                hits[method][0] += r is not None and r <= 5
                hits[method][1] += r is not None and r <= 10
        out["cases"].append({"name": name, "pairs": len(pairs), "ranked": dict(ranked),
                             "top5": {m: h[0] for m, h in hits.items()}, "top10": {m: h[1] for m, h in hits.items()}})
    return out


def verify(m: dict) -> list[str]:
    problems = []
    for case in m["cases"]:
        if case["pairs"] == 0:
            problems.append(f"{case['name']}: no confirmed pair")
        problems += [f"{case['name']}: {method} ranked nothing for some pair" for method in METHODS
                     if method != "recognition" and case["ranked"].get(method, 0) < case["pairs"]]
    return problems


def report(m: dict) -> str:
    lines = ["# Candidate ranking", "", f"Run {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}.", ""]
    for case in m["cases"]:
        lines += [f"## {case['name']}, {case['pairs']} confirmed pairs", "", "| Method | First 5 | First 10 |", "|---|---|---|"]
        lines += [f"| {method} | {case['top5'][method]} ({case['top5'][method] / case['pairs']:.0%}) | {case['top10'][method]} ({case['top10'][method] / case['pairs']:.0%}) |"
                  for method in METHODS if case["pairs"]]
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    m = measure()
    (HERE / "report.json").write_text(json.dumps(m, indent=1) + "\n", encoding="utf-8")
    (HERE / "report.md").write_text(report(m), encoding="utf-8")
    print(report(m))
    problems = verify(m)
    print("\n".join(problems) if problems else "pass")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
