"""The Configuration Studio's checks of vocabulary, quantification and eligibility configuration
(ADR-A136, addendum of 2026-10-27). Each validation runs the layer's own shapes, and then what only
the layer's own engine can say:

- vocabulary: the resolution table, every contract's resolution for every time segment its bindings
  draw and every combination of the scopes they name, by `tools/vocabulary`'s resolver (ADR-A85)
- eligibility: each condition compiled by `tools/mork_compilers`' IR, each concept condition's
  expansion over its resolved scheme, and each `elg:Question` decided by the compiled SPARQL, run on
  the data, against the decision the author expects of it

Quantification has no engine beyond its shapes yet, so its validation is SHACL alone.
"""

from __future__ import annotations

import itertools
from datetime import datetime, timedelta
from typing import Any, Dict, FrozenSet, List, Optional, Sequence, Tuple

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, XSD

CST = Namespace("https://www.nebularis.org/neuro-semantic/lattice/config-studio#")
SH = Namespace("http://www.w3.org/ns/shacl#")
VOC = Namespace("https://www.nebularis.org/neuro-semantic/lattice/vocabulary#")
FND = Namespace("https://www.nebularis.org/neuro-semantic/lattice/foundation#")
ELG = Namespace("https://www.nebularis.org/neuro-semantic/lattice/eligibility#")

# A contract whose bindings name more scopes than this gets one row per binding's own scope set
# instead of one per combination, so a table stays in the hundreds of rows.
MAX_SCOPES = 6
DECISIONS = ("Permitted", "Denied", "Undetermined")


def _instant(literal: Any) -> datetime:
    return datetime.fromisoformat(str(literal).replace("Z", "+00:00"))


def _time(moment: datetime) -> Literal:
    return Literal(moment.isoformat().replace("+00:00", "Z"), datatype=XSD.dateTime)


# --- vocabulary --------------------------------------------------------------------------------


def _bindings(graph: Graph, contract: URIRef) -> List[URIRef]:
    return sorted((b for b in graph.subjects(VOC.forContract, contract) if (b, RDF.type, VOC.SchemeBinding) in graph), key=str)


def _contexts(graph: Graph, bindings: Sequence[URIRef]) -> List[FrozenSet[URIRef]]:
    """Every combination of the scopes the bindings name, or, past MAX_SCOPES, each binding's own
    scope set and the empty one."""
    sets = [frozenset(graph.objects(b, VOC.bindingScope)) for b in bindings]
    scopes = sorted(frozenset().union(*sets), key=str) if sets else []
    if len(scopes) > MAX_SCOPES:
        return sorted({frozenset(), *sets}, key=lambda s: (len(s), sorted(map(str, s))))
    return [frozenset(c) for n in range(len(scopes) + 1) for c in itertools.combinations(scopes, n)]


def _segments(graph: Graph, bindings: Sequence[URIRef]) -> List[Tuple[Optional[datetime], Optional[datetime]]]:
    """The time segments the bindings' validity bounds draw, the first open below and the last open
    above. Within one segment every binding is either valid throughout or invalid throughout."""
    instants = set()
    for b in bindings:
        for scope in graph.objects(b, FND.hasTemporalScope):
            for p in (FND.validFrom, FND.validTo):
                value = graph.value(scope, p)
                if value is not None:
                    instants.add(_instant(value))
    points = sorted(instants)
    return list(zip([None, *points], [*points, None]))


def resolution_table(result: Any, graph: Graph, now: datetime) -> None:
    """Adds one `cst:Resolution` per contract, segment and context to `result`. `now`, the job's
    submission time, stands for a contract whose bindings bound no time at all."""
    from vocabulary.model import BindingConflictError, NoApplicableBindingError
    from vocabulary.resolver import resolve

    for contract in sorted(graph.subjects(RDF.type, VOC.SchemeContract), key=str):
        bindings = _bindings(graph, contract)
        for start, end in _segments(graph, bindings):
            # A moment inside the segment: its start, or a day before the first bound.
            at = start if start is not None else (end - timedelta(days=1) if end is not None else now)
            for context in _contexts(graph, bindings):
                node = result._mint("resolution")
                add = result.graph.add
                add((result.job, CST.resolution, node))
                add((node, RDF.type, CST.Resolution))
                add((node, CST.contract, contract))
                if start is not None:
                    add((node, CST.validFrom, _time(start)))
                if end is not None:
                    add((node, CST.validTo, _time(end)))
                for scope in sorted(context, key=str):
                    add((node, CST.context, scope))
                try:
                    found = resolve(graph, contract, context, at)
                except BindingConflictError as error:
                    add((node, CST.outcome, CST.Conflict))
                    for b in sorted(error.candidates, key=lambda c: str(c.node)):
                        add((node, CST.tied, b.node))
                    continue
                except NoApplicableBindingError:
                    add((node, CST.outcome, CST.Unresolved))
                    continue
                add((node, CST.outcome, CST.Fallback if found.used_fallback else CST.Resolved))
                add((node, CST.scheme, found.scheme))
                if found.winning_binding is not None:
                    add((node, CST.binding, found.winning_binding))


# --- eligibility -------------------------------------------------------------------------------


def _conditions(graph: Graph) -> List[URIRef]:
    found = set(graph.subjects(RDF.type, ELG.Condition)) | set(graph.subjects(RDF.type, ELG.IntervalCondition))
    return sorted((c for c in found if isinstance(c, URIRef)), key=str)


def _context(graph: Graph, node: URIRef, default: datetime) -> Any:
    from mork_compilers import ResolutionContext

    at = graph.value(node, CST.resolutionTime)
    return ResolutionContext(at=_instant(at) if at is not None else default, scope=frozenset(graph.objects(node, CST.resolutionScope)))


def _local(term: Any) -> str:
    text = str(term)
    return text.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def eligibility(result: Any, graph: Graph, now: datetime) -> bool:
    """Compiles each condition, adds each concept condition's expansion and each question's decision.
    Returns False when a condition cannot be compiled or a question's decision is not the one expected. `now` is the job's submission time, the
    resolution instant of an expansion and of a question that names none."""
    from mork_compilers import IRCompileError, compile_any_condition
    from mork_compilers.eligibility_ir import ConceptPlan

    compiled = True
    plans: Dict[URIRef, Any] = {}
    for condition in _conditions(graph):
        try:
            plan = compile_any_condition(graph, condition, _context(graph, condition, now))
        except IRCompileError as error:
            result.finding(SH.Violation, str(error), "IRCompileError", condition)
            compiled = False
            continue
        plans[condition] = plan
        if isinstance(plan, ConceptPlan):
            for concept, decision in plan.expansion:
                node = result._mint("expansion")
                result.graph.add((result.job, CST.expansion, node))
                result.graph.add((node, CST.condition, condition))
                result.graph.add((node, CST.concept, concept))
                result.graph.add((node, CST.decision, CST[_local(decision)]))
        if plan.evidence is not None:
            result.finding(
                SH.Info,
                "This condition reads its candidate from bound subjects, which the studio cannot test yet. Its questions are not decided here.",
                "EvidenceBindingNotTested", condition,
            )
    return _decide_questions(result, graph, now) and compiled


def _decide_questions(result: Any, graph: Graph, now: datetime) -> bool:
    """Decides each question, and returns False when one is decided otherwise than its
    `cst:expectedDecision`, a failed test."""
    from mork_compilers import IRCompileError, compile_any_condition
    from mork_compilers.engines import run_query
    from mork_compilers.sparql_backend import condition_select, PREFIXES

    all_passed = True
    for question in sorted((q for q in graph.subjects(RDF.type, ELG.Question) if isinstance(q, URIRef)), key=str):
        condition = graph.value(question, ELG.forCondition)
        if not isinstance(condition, URIRef):
            continue
        node = result._mint("test")
        add = result.graph.add
        add((result.job, CST.testResult, node))
        add((node, CST.question, question))
        add((node, CST.condition, condition))
        try:
            plan = compile_any_condition(graph, condition, _context(graph, question, now))
            if plan.evidence is not None:
                add((node, CST.decision, CST.NotTested))
                continue
            rows = [row for row in run_query(graph, PREFIXES + condition_select(plan)) if row[0] == question]
        except IRCompileError:
            add((node, CST.decision, CST.NotTested))
            continue
        decision = _local(rows[0][1]) if len(rows) == 1 else "Undetermined"
        add((node, CST.decision, CST[decision] if decision in DECISIONS else CST.Undetermined))
        if len(rows) == 1 and len(rows[0]) > 2 and rows[0][2] is not None:
            add((node, CST.diagnostic, Literal(_local(rows[0][2]))))
        expected = graph.value(question, CST.expectedDecision)
        if expected is not None:
            passed = _local(expected) == decision
            add((node, CST.passed, Literal(passed)))
            if not passed:
                all_passed = False
                result.finding(
                    SH.Violation, f"Expected {_local(expected)}, decided {decision}.", "TestFailed", question,
                )
    return all_passed


def eligibility_artefacts(result: Any, graph: Graph, now: datetime) -> bool:
    """The SPARQL query and SHACL shapes of each condition and profile, as artefacts."""
    from mork_compilers import IRCompileError, compile_any_condition, compile_profile
    from mork_compilers.shacl_backend import compile_shapes
    from mork_compilers.sparql_backend import condition_select, profile_select, PREFIXES

    compiled = True
    named = [(c, False) for c in _conditions(graph)]
    named += [(p, True) for p in sorted((p for p in graph.subjects(RDF.type, ELG.AdmissionProfile) if isinstance(p, URIRef)), key=str)]
    for node, profile in named:
        group = _local(node)
        try:
            plan = (compile_profile if profile else compile_any_condition)(graph, node, _context(graph, node, now))
            query = PREFIXES + (profile_select(plan) if profile else condition_select(plan))
            shapes = compile_shapes(plan).serialize(format="turtle")
        except IRCompileError as error:
            result.finding(SH.Violation, str(error), "IRCompileError", node)
            compiled = False
            continue
        result.artefact(f"{group}/decision.rq", "application/sparql-query", query, group)
        result.artefact(f"{group}/shapes.ttl", "text/turtle", shapes, group)
    return compiled

