# SPDX-License-Identifier: MPL-2.0
"""The contract builder's dry run (ADR-A138 decision 7, CB-Q2): a stated term's eligibility conditions decided over
sample facts, by each condition's compiled SPARQL as an eligibility validation decides a question, never by the
reference evaluator and never by instantiating the term. contracts/config-studio/README.md describes the request."""

from __future__ import annotations

from datetime import datetime

from rdflib import BNode, Graph, URIRef
from rdflib.namespace import RDF, RDFS, SH

from .config_studio_jobs import CST, _Result

INS = "https://www.nebularis.org/neuro-semantic/lattice/instrument#"
ELG = "https://www.nebularis.org/neuro-semantic/lattice/eligibility#"
QNT = "https://www.nebularis.org/neuro-semantic/lattice/quantification#"


def _conditions(world: Graph) -> set:
    classes = {URIRef(ELG + "Condition")} | set(world.transitive_subjects(RDFS.subClassOf, URIRef(ELG + "Condition")))
    return {s for c in classes for s in world.subjects(RDF.type, c) if isinstance(s, URIRef)}


def conditions_read(world: Graph, term: URIRef) -> list[URIRef]:
    """The conditions a stated term reads: those its relations and their qualifiers reach, following every link but
    a link back to the term or to a clause, and stopping at a condition."""
    conditions = _conditions(world)
    found, seen = set(), {term}
    pending = [r for r in world.subjects(URIRef(INS + "arisesUnder"), term)]
    while pending:
        node = pending.pop()
        if node in seen:
            continue
        seen.add(node)
        if node in conditions:
            found.add(node)
            continue
        for p, o in world.predicate_objects(node):
            if p in (URIRef(INS + "arisesUnder"), URIRef(INS + "expressedIn"), RDF.type):
                continue
            if isinstance(o, (URIRef, BNode)):
                pending.append(o)
    return sorted(found, key=str)


def _question(data: Graph, question: URIRef, condition: URIRef, facts: list, request: Graph) -> None:
    """Poses one condition with its facts as the candidate: concepts as candidate concepts, a number as a range set of
    one point on the condition's own space."""
    data.add((question, RDF.type, URIRef(ELG + "Question")))
    data.add((question, URIRef(ELG + "forCondition"), condition))
    concepts = [c for f in facts for c in request.objects(f, CST.concept)]
    numbers = [n for f in facts for n in request.objects(f, CST.number)]
    for concept in concepts:
        data.add((question, URIRef(ELG + "candidateConcept"), concept))
    if len(numbers) == 1:
        space = data.value(data.value(condition, URIRef(ELG + "requiredRangeSet")), URIRef(QNT + "onSpace"))
        bound, quantity, range_, range_set = (URIRef(f"{question}#{n}") for n in ("bound", "quantity", "range", "range-set"))
        data.add((quantity, URIRef(QNT + "numericValue"), numbers[0]))
        data.add((bound, URIRef(QNT + "boundValue"), quantity))
        data.add((range_, URIRef(QNT + "lowerBound"), bound))
        data.add((range_, URIRef(QNT + "upperBound"), bound))
        data.add((range_set, URIRef(QNT + "hasRange"), range_))
        if space is not None:
            for node in (quantity, range_, range_set):
                data.add((node, URIRef(QNT + "onSpace"), space))
        data.add((question, URIRef(ELG + "candidateRangeSet"), range_set))


def dry_run(job: URIRef, config: Graph, spec: Graph, submitted_at: str) -> Graph:
    from .config_studio_layers import _decide_questions

    result = _Result(job)
    runs = [r for r in config.subjects(RDF.type, CST.DryRun)]
    if len(runs) != 1 or not isinstance(config.value(runs[0], CST["term"]), URIRef):
        raise ValueError("a dry run's input holds one cst:DryRun naming a stated term with cst:term")
    request, term = runs[0], config.value(runs[0], CST["term"])
    world = spec + config
    read = conditions_read(world, term)
    facts_by_condition: dict = {}
    for fact in config.objects(request, CST.fact):
        condition = config.value(fact, CST.forCondition)
        if condition not in read:
            result.finding(SH.Info, f"A fact is for {condition}, which the term does not read.", "dry-run", condition)
            continue
        facts_by_condition.setdefault(condition, []).append(fact)
    data = Graph() + world
    for n, condition in enumerate(read, start=1):
        facts = facts_by_condition.get(condition, [])
        if not facts:
            result.finding(SH.Info, f"No sample fact for {condition}, which reads Undetermined.", "dry-run", condition)
        _question(data, URIRef(f"{job}#dry-run-{n}"), condition, facts, config)
    if not read:
        result.finding(SH.Info, "The term reads no eligibility condition.", "dry-run", term)
    now = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
    # Only the dry run's own questions are decided, not the eligibility part's tests beside them.
    for question in list(data.subjects(RDF.type, URIRef(ELG + "Question"))):
        if not str(question).startswith(f"{job}#dry-run-"):
            data.remove((question, RDF.type, URIRef(ELG + "Question")))
    _decide_questions(result, data, now)
    result.conforms(True)
    return result.graph
