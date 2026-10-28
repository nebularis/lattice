# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Assembly under the baseline model (ADR-A139). Load, decide, assemble, record. Reads the plan, the
settings and the choices only (law WA4), and gives either a record or findings and no record (law WA6)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Set, Tuple

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import PROV, RDF, XSD

from . import findings as fx
from .check import run_shapes
from .layer import Layer, load_layer
from .model import (BASELINE_MODEL, ELG, FND, QNT, WRD, WRD_VOC, children, digest_of, digest_text, instances, is_a,
                    is_variant, local, mode_of, variants_of)
from .plan import Plan

Mint = Callable[[str], URIRef]
_DECISION = "urn:x-wording-assembler:decision:"


@dataclass(frozen=True)
class Result:
    ok: bool
    findings: Graph
    record_iri: Optional[URIRef] = None
    record: Optional[Graph] = None                # None whenever the assembly was refused (law WA6)
    digests: Optional[Mapping[str, str]] = None   # of the plan, the settings, the choices and the model


# ---- load -----------------------------------------------------------------------------------

def _value_records(settings: Graph) -> List:
    nodes = set(settings.subjects(RDF.type, WRD.VariableValue)) | set(settings.subjects(WRD.forVariable, None))
    return sorted(nodes, key=lambda n: (isinstance(n, BNode), str(n)))


def _variable(plan: Plan, term) -> Optional[URIRef]:
    """The variable of the form a settings record names, by version or by identity."""
    g = plan.graph
    variables = instances(g, WRD.Variable)
    if term in variables:
        return term
    return next((v for v in variables if g.value(v, FND.hasIdentity) == term), None)


def _load(plan: Plan, settings: Graph, choices: Set[URIRef], out: Graph) -> None:
    g = plan.graph
    for record in _value_records(settings):
        variable = settings.value(record, WRD.forVariable)
        if variable is None or _variable(plan, variable) is None:
            fx.add(out, "load", f"The settings give a value for {variable}, which the form does not declare.",
                   record if isinstance(record, URIRef) else None, variable)
    for choice in sorted(choices, key=str):
        known = (choice, RDF.type, None) in g
        unconditioned = is_variant(g, choice) and g.value(choice, WRD.includedWhen) is None
        if not known or not (mode_of(g, choice) == WRD_VOC.Optional or unconditioned):
            fx.add(out, "load", f"{choice} is not a choice: only an optional element, or a variant with no inclusion "
                                f"condition, is chosen.", choice)


# ---- decide ---------------------------------------------------------------------------------

def _values(plan: Plan, settings: Graph, variable: URIRef) -> List:
    return [r for r in _value_records(settings) if _variable(plan, settings.value(r, WRD.forVariable)) == variable]


def _candidate(data: Graph, question: URIRef, kind: str, records: List, settings: Graph) -> None:
    """Gives a question the governing variable's value the settings supply, as the candidate the compiled
    condition reads. A condition that finds no single usable value reads Undetermined."""
    resources = [v for r in records for v in settings.objects(r, WRD.value)]
    literals = [v for r in records for v in settings.objects(r, WRD.literalValue)]
    if kind == "concept":
        for concept in resources:
            data.add((question, ELG.candidateConcept, concept))
        return
    if len(resources) + len(literals) != 1:
        return
    unit = None
    if literals:
        number = literals[0]
    else:
        number = settings.value(resources[0], QNT.numericValue)
        unit = settings.value(resources[0], QNT.inUnit)
    if number is None:
        return
    bound, quantity, range_, range_set = (URIRef(f"{question}#{n}") for n in ("bound", "quantity", "range", "range-set"))
    data.add((quantity, QNT.numericValue, number))
    if unit is not None:
        data.add((quantity, QNT.inUnit, unit))
    data.add((bound, QNT.boundValue, quantity))
    data.add((range_, QNT.lowerBound, bound))
    data.add((range_, QNT.upperBound, bound))
    data.add((range_set, QNT.hasRange, range_))
    data.add((question, ELG.candidateRangeSet, range_set))


def _decide(plan: Plan, settings: Graph) -> Dict[URIRef, Tuple[str, List[URIRef]]]:
    """Each conditional element's decision, "Permitted", "Denied" or "Undetermined", with the governing
    variables the settings do not supply when it is Undetermined. The compiled SPARQL runs against the
    settings, as the studio's eligibility jobs run it."""
    from mork_compilers.engines import run_query

    data = Graph()
    data += plan.graph
    data += settings
    records: Dict[URIRef, URIRef] = {}
    for n, element in enumerate(sorted(plan.inclusions, key=str)):
        inclusion = plan.inclusions[element]
        record = URIRef(f"{_DECISION}{n}")
        records[record] = element
        data.add((record, RDF.type, ELG.EligibilityDecision))
        data.add((record, ELG.forProfile, inclusion.profile))
        for m, (condition, variable, kind) in enumerate(inclusion.conditions):
            question = URIRef(f"{record}#question-{m}")
            data.add((question, RDF.type, ELG.Question))
            data.add((question, ELG.forCondition, condition))
            data.add((record, ELG.hasQuestion, question))
            _candidate(data, question, kind, _values(plan, settings, variable), settings)
    decided: Dict[URIRef, str] = {}
    by_profile: Dict[URIRef, str] = {i.profile: i.query for i in plan.inclusions.values()}
    for profile in sorted(by_profile, key=str):   # one compiled query per profile, over every record of it
        for row in run_query(data, by_profile[profile]):
            element = records.get(row[0])
            if element is not None and plan.inclusions[element].profile == profile:
                decided[element] = local(row[1])
    out: Dict[URIRef, Tuple[str, List[URIRef]]] = {}
    for element, inclusion in plan.inclusions.items():
        decision = decided.get(element)
        if decision in ("Permitted", "Denied"):
            out[element] = (decision, [])
            continue
        read = sorted({v for _, v, _ in inclusion.conditions}, key=str)
        out[element] = ("Undetermined", [v for v in read if len(_values(plan, settings, v)) != 1] or read)
    return out


def _walk(plan: Plan, decisions, choices: Set[URIRef], out: Graph) -> List[URIRef]:
    """The included elements, or findings. Mandatory children of included elements are included, an
    optional element and a variant with no condition when chosen, a conditional element or a variant when
    its condition is Admitted. Undetermined refuses, and so does a slot that admits none or several."""
    g = plan.graph
    included: List[URIRef] = []

    def admitted(element: URIRef) -> Optional[bool]:
        """True or False, or None after a finding for an Undetermined or missing condition."""
        if element in plan.inclusions:
            decision, lacking = decisions[element]
            if decision == "Undetermined":
                fx.add(out, "decide", f"The inclusion condition of {element} is Undetermined: the settings give no single "
                                      f"value for the governing variable {', '.join(map(str, lacking))}.", element, lacking[0])
                return None
            return decision == "Permitted"
        if mode_of(g, element) == WRD_VOC.Conditional:
            fx.add(out, "decide", f"{element} is conditional and has no inclusion condition.", element)
            return None
        if mode_of(g, element) == WRD_VOC.Optional or is_variant(g, element):
            return element in choices
        return True

    def visit(parent: URIRef) -> None:
        for child in children(g, parent):
            if is_a(g, child, WRD.Variable) or admitted(child) is not True:
                continue                       # a variable is a declaration, shown by its values (law W5)
            included.append(child)
            if not is_a(g, child, WRD.VariationSlot):
                visit(child)
                continue
            results = [(v, admitted(v)) for v in variants_of(g, child)]
            if any(a is None for _, a in results):
                continue
            chosen = [v for v, a in results if a]
            if len(chosen) != 1:
                kind = "none" if not chosen else "several: " + ", ".join(map(str, chosen))
                fx.add(out, "decide", f"The variation slot {child} admits {kind}, and must admit exactly one variant.", child)
                continue
            included.append(chosen[0])
            visit(chosen[0])

    visit(plan.form_iri)
    return included


# ---- assemble and record --------------------------------------------------------------------

def _signature(graph: Graph, record) -> Tuple:
    def term(t):
        if isinstance(t, BNode):   # ponytail: one level of anonymous value, deeper needs a description walk
            return str(sorted((str(p), str(o)) for p, o in graph.predicate_objects(t)))
        return f"{type(t).__name__} {t} {getattr(t, 'datatype', None) or ''}"
    return (str(graph.value(record, WRD.forVariable)), str(graph.value(record, WRD.forEntry)),
            tuple(sorted(term(o) for p in (WRD.value, WRD.literalValue) for o in graph.objects(record, p))))


def _copy_values(settings: Graph, record, node, into: Graph) -> None:
    into.add((node, RDF.type, WRD.VariableValue))
    for p, o in settings.predicate_objects(record):
        if p == RDF.type:
            continue
        into.add((node, p, o))
        if isinstance(o, BNode):
            for p2, o2 in settings.predicate_objects(o):
                into.add((o, p2, o2))


def _build(plan: Plan, settings: Graph, included: List[URIRef], at: datetime, mint: Mint,
           prior: Optional[Graph], prior_iri: Optional[URIRef]) -> Tuple[URIRef, Graph]:
    """The record, with the value records it writes, its model and its provenance. Mints in a fixed order
    from sorted inputs, so the same inputs mint the same identifiers in the same places (law WA5)."""
    record = mint("record")
    identity = prior.value(prior_iri, FND.hasIdentity) if prior is not None else None
    graph = Graph()
    graph.add((record, RDF.type, WRD.AssembledWording))
    graph.add((record, FND.hasIdentity, identity or mint("identity")))
    graph.add((record, FND.hasGovernanceState, FND.Active))
    graph.add((record, WRD.assembledFrom, plan.form_iri))
    for element in sorted(included, key=str):
        graph.add((record, WRD.includes, element))
    shared: Dict[Tuple, URIRef] = {}
    taken: Set = set()
    if prior is not None:
        for old in prior.objects(prior_iri, WRD.hasValue):
            shared.setdefault(_signature(prior, old), old)
            taken.add(old)
    for source in sorted(_value_records(settings), key=lambda r: (_signature(settings, r), isinstance(r, BNode), str(r))):
        signature = _signature(settings, source)
        if signature not in shared:            # a changed value is a new record, an unchanged one is shared (§5.12)
            node = source if isinstance(source, URIRef) and source not in taken else mint("value")
            _copy_values(settings, source, node, graph)
            shared[signature] = node
        graph.add((record, WRD.hasValue, shared[signature]))
    graph.add((record, WRD.assembledUnder, BASELINE_MODEL))
    activity, used = mint("assembly"), mint("settings")
    graph.add((activity, RDF.type, FND.DerivationRun))
    graph.add((used, RDF.type, PROV.Entity))
    for entity in (plan.form_iri, used, BASELINE_MODEL):
        graph.add((activity, PROV.used, entity))
    stamp = Literal(at.isoformat(), datatype=XSD.dateTime)
    graph.add((activity, PROV.startedAtTime, stamp))
    graph.add((activity, PROV.endedAtTime, stamp))
    graph.add((record, PROV.wasGeneratedBy, activity))
    if prior_iri is not None:
        graph.add((prior_iri, FND.supersededBy, record))
    return record, graph


def _run(plan: Plan, settings: Graph, choices: Iterable[URIRef], at: datetime, mint: Mint, layer: Optional[Layer],
         prior: Optional[Graph] = None, prior_iri: Optional[URIRef] = None) -> Result:
    layer = layer or load_layer()
    out = fx.report()
    choices = set(choices)
    digests = {"plan": plan.digest, "settings": digest_of(settings),
               "choices": digest_text(str(c) for c in choices), "model": digest_text([str(BASELINE_MODEL)])}
    if not plan.ok:
        out += plan.findings
        return Result(False, fx.seal(out), digests=digests)
    _load(plan, settings, choices, out)
    included = _walk(plan, _decide(plan, settings), choices, out) if fx.conforms(out) else []
    if not fx.conforms(out):
        return Result(False, fx.seal(out), digests=digests)
    record, graph = _build(plan, settings, included, at, mint, prior, prior_iri)
    # WA2: whatever the model, the record satisfies W3 to W6 and W8, checked with what it shares.
    focus = {record} | set(graph.objects(record, WRD.hasValue))
    run_shapes(graph + (prior if prior is not None else Graph()) + plan.graph + settings, layer, "assemble", out, focus)
    if not fx.conforms(out):
        return Result(False, fx.seal(out), digests=digests)
    return Result(True, fx.seal(out), record, graph, digests)


def assemble(plan: Plan, settings: Graph, choices: Iterable[URIRef], *, at: datetime, mint: Mint,
             layer: Optional[Layer] = None) -> Result:
    """Assembles `plan`'s form under the baseline model. `settings` holds `wrd:VariableValue` records,
    `choices` names the optional elements, and the variants with no condition, that the drafter chose, `at`
    is the assembly time and `mint(kind)` gives each new IRI, for the kinds record, identity, value,
    assembly and settings. A refused assembly returns findings and no record."""
    return _run(plan, settings, choices, at, mint, layer)


def reassemble(record_graph: Graph, record_iri: URIRef, plan: Plan, settings: Graph, choices: Iterable[URIRef], *,
               at: datetime, mint: Mint, layer: Optional[Layer] = None) -> Result:
    """A new version of the assembled wording `record_iri`, with its `fnd:hasIdentity`, sharing every value
    record the new settings leave unchanged. The result holds only what is new, and the link that the
    last version is superseded by it (§5.12)."""
    return _run(plan, settings, choices, at, mint, layer, record_graph, record_iri)
