# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
MORK-to-SPARQL compiler for Eligibility interval conditions (ADR-A23, ADR-A24).

Generates one parameterised SPARQL ``SELECT`` per condition plan, answering
the three-valued question ADR-A24 requires — ``Permitted``, ``Denied``, or
``Undetermined`` — never a silent ``Denied`` for missing evidence. The query
is written as a ``mork:QueryTemplate``, which MorkEnhancements.md recommends
as the first target and which ``ontology/mork/spec/Mork.ttl`` already models
(``queryText``, ``queryLanguage``, ``paramBinding``). It is not attached to a
``mork:DataMapping``: ``QueryTemplate`` is ``rdfs:subClassOf skos:Concept``
in the ontology today, with no property linking a mapping to one, so
provenance instead runs ``exe:IntervalContainmentPlan -> exe:producesArtefact
-> mork:QueryTemplate``.

Undetermined handling: a candidate missing either bound is Undetermined, not
Denied, matching ADR-A24's stated requirement that unsupported or absent
evidence must never silently read as a denial.

Every row carries ``?diagnostic``, an ``exe:Diagnostic`` individual, exactly
when its decision is Undetermined (ADR-A89 item 6).

Concept plans (ADR-A89) follow the ADR-A87 decision table: a question with no
``elg:candidateConcept``, or more than one, is Undetermined. An excluded
candidate is Denied (L10), a required one Permitted, and any other Denied.
Where the plan resolved a scheme, a candidate outside it is Undetermined, and
hierarchical match walks ``skos:broader`` at query time (the "QueryTime" form
of ADR-A89 item 3). The walk does not check that intermediate concepts belong
to the scheme. The plan's own expansion does, and the two agree on any scheme
whose members are broader only than other members.
"""

from __future__ import annotations

from typing import Sequence, Union

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF

from .common import mint
from .eligibility_ir import ConceptPlan, EvidencePath, IntervalPlan, ProfilePlan, RequiredInterval
from .namespaces import ELG, EXE, MORK, QNT

PREFIXES = (
    "PREFIX elg: <https://www.nebularis.org/neuro-semantic/lattice/eligibility#>\n"
    "PREFIX qnt: <https://www.nebularis.org/neuro-semantic/lattice/quantification#>\n"
    "PREFIX skos: <http://www.w3.org/2004/02/skos/core#>\n"
    "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
)


def _interval_clause(interval: RequiredInterval) -> str:
    clauses = []
    if interval.lower is not None:
        op = ">=" if interval.lower_closed else ">"
        clauses.append(f"?candLower {op} {interval.lower!r}")
    if interval.upper is not None:
        op = "<=" if interval.upper_closed else "<"
        clauses.append(f"?candUpper {op} {interval.upper!r}")
    if interval.unit is not None:
        clauses.append(f"BOUND(?candUnit) && ?candUnit = <{interval.unit}>")
    return "(" + " && ".join(clauses) + ")" if clauses else "true"


def containment_expression(plan: IntervalPlan) -> str:
    """A SPARQL boolean expression: the candidate is contained by *some* required interval."""
    return " || ".join(_interval_clause(interval) for interval in plan.required)


def applicable(plan: IntervalPlan) -> str:
    """A SPARQL boolean expression: some required interval is stated in the
    candidate's unit (ADR-A95). Always true when an interval states no unit."""
    units = sorted({i.unit for i in plan.required}, key=lambda u: str(u or ""))
    if None in units:
        return "true"
    return f"(BOUND(?candUnit) && ?candUnit IN ({_in_list(units)}))"


def render_query(plan: IntervalPlan) -> str:
    """The SPARQL query text for one condition plan."""
    return PREFIXES + interval_select(plan)


def evidence_path(evidence: EvidencePath) -> str:
    """The binding's steps as a SPARQL property path."""
    return "/".join(f"^<{prop}>" if inverse else f"<{prop}>" for prop, inverse in evidence.steps)


def _subjects(evidence: EvidencePath, key: str) -> str:
    """Instances of the subject class, including subclass instances, matching
    how a SHACL ``sh:targetClass`` selects them."""
    return f"{key} a/rdfs:subClassOf* <{evidence.subject_class}> ."


def interval_select(plan: IntervalPlan, carry: str = "", key: str = "?question") -> str:
    """The SELECT block, without prefixes, projecting ``key`` ?decision ?diagnostic.
    ``key`` is the question, or the subject when the condition is bound.
    ``carry`` is prepended to every projection (see ``profile_select``)."""
    if plan.evidence is not None:
        return _bound_interval_select(plan, carry, key)
    return (
        f"SELECT {carry}{key} ?decision ?diagnostic WHERE {{\n"
        f"  {key} elg:forCondition <{plan.condition}> .\n"
        "  OPTIONAL {\n"
        f"    {key} elg:candidateRangeSet ?candidateRangeSet .\n"
        "    ?candidateRangeSet qnt:hasRange ?candidateRange .\n"
        "    ?candidateRange qnt:lowerBound/qnt:boundValue/qnt:numericValue ?candLower .\n"
        "    ?candidateRange qnt:upperBound/qnt:boundValue/qnt:numericValue ?candUpper .\n"
        "    OPTIONAL { ?candidateRange qnt:lowerBound/qnt:boundValue/qnt:inUnit ?candUnit }\n"
        "  }\n"
        "  BIND(\n"
        "    IF(!BOUND(?candLower) || !BOUND(?candUpper), \"Undetermined\",\n"
        f"       IF(!{applicable(plan)}, \"Undetermined\", IF({containment_expression(plan)}, \"Permitted\", \"Denied\"))\n"
        "    ) AS ?decision\n"
        "  )\n"
        f"  BIND(IF(!BOUND(?candLower) || !BOUND(?candUpper), <{EXE.MissingCandidate}>, "
        f"IF(!{applicable(plan)}, <{EXE.NoBoundInUnit}>, ?none)) AS ?diagnostic)\n"
        "}\n"
    )


def literal_readable(plan: IntervalPlan) -> bool:
    """Whether a literal at the end of the path is read on the condition's space."""
    return plan.evidence is not None and plan.evidence.space == plan.value_space


def _bound_interval_select(plan: IntervalPlan, carry: str, key: str) -> str:
    """A bound interval condition reads one value per subject: a qnt:Quantity on
    the condition's space, or a literal where the binding reads on that space.
    Any other value leaves the subject Undetermined (exe:ValueSpaceMismatch)."""
    literal = "isLiteral(?reading)" if literal_readable(plan) else "false"
    return (
        f"SELECT {carry}{key} ?decision ?diagnostic WHERE {{\n"
        "  {\n"
        f"    SELECT {carry}{key} (COUNT(DISTINCT ?value) AS ?candidates) (SAMPLE(?value) AS ?reading)"
        " (SAMPLE(?number) AS ?quantity) (SAMPLE(?unitOfValue) AS ?candUnit) WHERE {\n"
        f"      {_subjects(plan.evidence, key)}\n"
        f"      OPTIONAL {{ {key} {evidence_path(plan.evidence)} ?value .\n"
        f"        OPTIONAL {{ ?value qnt:numericValue ?number ; qnt:onSpace <{plan.value_space}> }}\n"
        "        OPTIONAL { ?value qnt:inUnit ?unitOfValue } }\n"
        "    }\n"
        f"    GROUP BY {carry}{key}\n"
        "  }\n"
        f"  BIND(IF({literal}, ?reading, ?quantity) AS ?candLower)\n"
        "  BIND(?candLower AS ?candUpper)\n"
        f'  BIND(IF(?candidates != 1 || !BOUND(?candLower), "Undetermined", '
        f'IF(!{applicable(plan)}, "Undetermined", IF({containment_expression(plan)}, "Permitted", "Denied"))) AS ?decision)\n'
        f"  BIND(IF(?candidates = 0, <{EXE.MissingCandidate}>, IF(?candidates > 1, <{EXE.SeveralCandidates}>, "
        f"IF(!BOUND(?candLower), <{EXE.ValueSpaceMismatch}>, IF(!{applicable(plan)}, <{EXE.NoBoundInUnit}>, ?none)))) AS ?diagnostic)\n"
        "}\n"
    )


def _in_list(concepts: Sequence[URIRef]) -> str:
    return ", ".join(f"<{concept}>" for concept in concepts)


def _flat_decision(plan: ConceptPlan) -> str:
    admitted = f"?candidate IN ({_in_list(plan.required)})" if plan.required else "true"
    decision = f'IF({admitted}, "Permitted", "Denied")'
    if plan.excluded:
        decision = f'IF(?candidate IN ({_in_list(plan.excluded)}), "Denied", {decision})'
    return decision


def _hierarchical_decision(plan: ConceptPlan) -> str:
    def below(concepts: Sequence[URIRef]) -> str:
        return f"EXISTS {{ ?candidate skos:broader* ?target . FILTER (?target IN ({_in_list(concepts)})) }}"

    admitted = below(plan.required) if plan.required else "true"
    if not plan.excluded:
        return f'IF({admitted}, "Permitted", "Denied")'
    above = f"EXISTS {{ ?target skos:broader+ ?candidate . FILTER (?target IN ({_in_list(plan.excluded)})) }}"
    return (
        f'IF({below(plan.excluded)}, "Denied", '
        f'IF({admitted}, IF({above}, "Undetermined", "Permitted"), "Denied"))'
    )


def render_concept_query(plan: ConceptPlan) -> str:
    """The SPARQL query text for one concept plan."""
    return PREFIXES + concept_select(plan)


def concept_select(plan: ConceptPlan, carry: str = "", key: str = "?question") -> str:
    """The SELECT block, without prefixes, projecting ``key`` ?decision ?diagnostic.
    ``key`` is the question, or the subject when the condition is bound.
    ``carry`` is prepended to every projection and grouping (see ``profile_select``)."""
    decision = _hierarchical_decision(plan) if plan.hierarchical else _flat_decision(plan)
    determined = f'IF(?decision = "Undetermined", <{EXE.AboveExclusion}>, ?none)'
    if plan.scheme is not None:
        membership = f"EXISTS {{ ?candidate skos:inScheme <{plan.scheme.scheme}> }}"
        decision = f'IF({membership}, {decision}, "Undetermined")'
        determined = f"IF({membership}, {determined}, <{EXE.OutsideScheme}>)"
    diagnostic = (
        f"IF(?candidates = 0, <{EXE.MissingCandidate}>, "
        f"IF(?candidates > 1, <{EXE.SeveralCandidates}>, {determined}))"
    )
    if plan.evidence is None:
        source = (
            f"      {key} elg:forCondition <{plan.condition}> .\n"
            f"      OPTIONAL {{ {key} elg:candidateConcept ?offered }}\n"
        )
    else:
        source = (
            f"      {_subjects(plan.evidence, key)}\n"
            f"      OPTIONAL {{ {key} {evidence_path(plan.evidence)} ?offered }}\n"
        )
    return (
        f"SELECT {carry}{key} ?decision ?diagnostic WHERE {{\n"
        "  {\n"
        f"    SELECT {carry}{key} (COUNT(DISTINCT ?offered) AS ?candidates) (SAMPLE(?offered) AS ?candidate) WHERE {{\n"
        f"{source}"
        "    }\n"
        f"    GROUP BY {carry}{key}\n"
        "  }\n"
        f'  BIND(IF(?candidates != 1, "Undetermined", {decision}) AS ?decision)\n'
        f"  BIND({diagnostic} AS ?diagnostic)\n"
        "}\n"
    )


def condition_select(plan: Union[IntervalPlan, ConceptPlan], carry: str = "", key: str = "?question") -> str:
    select = concept_select if isinstance(plan, ConceptPlan) else interval_select
    return select(plan, carry, key)


def _aggregate(plan: ProfilePlan) -> str:
    if plan.aggregation == ELG.AllRequired:
        return 'IF(?denied > 0, "Denied", IF(?undetermined > 0 || ?missing > 0, "Undetermined", "Permitted"))'
    return 'IF(?permitted > 0, "Permitted", IF(?undetermined > 0 || ?missing > 0, "Undetermined", "Denied"))'


def profile_select(plan: ProfilePlan, record: str = "?record") -> str:
    """The SELECT block, without prefixes, projecting the record, ?decision and
    ?diagnostic (ADR-A89 item 5). A record is an ``elg:EligibilityDecision`` of
    the profile, or each bound subject when the profile's conditions are bound
    (ADR-A91). A condition with no answer for the record counts as Undetermined.

    ``record`` names the record variable. A SHACL-SPARQL constraint passes
    ``$this``, which SHACL then requires every nested SELECT to project, so it
    is carried through each condition block as well."""
    if plan.subject_class is not None:
        key, carry = record, ""
        records = f"{record} a/rdfs:subClassOf* <{plan.subject_class}> ."
        link = guard = ""
    else:
        key, carry = "?question", ("$this " if record == "$this" else "")
        records = f"{record} elg:forProfile <{plan.profile}> ."
        link = f"        {record} elg:hasQuestion ?question .\n"
        # rdflib evaluates a grouped subquery under the outer binding of ?question,
        # which yields an empty row from other conditions' branches.
        guard = "        ?question elg:forCondition ?condition .\n"
    branches = "\n        UNION\n".join(
        "        {\n        {\n" + condition_select(condition, carry, key)
        + f"        }}\n        BIND(<{condition.condition}> AS ?condition)\n        }}"
        for condition in plan.conditions
    )

    def count(outcome: str) -> str:
        return f'(SUM(IF(COALESCE(?outcome, "") = "{outcome}", 1, 0)) AS ?{outcome.lower()})'

    return (
        f"SELECT {record} ?decision ?diagnostic WHERE {{\n"
        "  {\n"
        f"    SELECT {record} {count('Permitted')} {count('Denied')} {count('Undetermined')}\n"
        "      (COUNT(DISTINCT ?condition) AS ?answered) (MAX(COALESCE(STR(?reason), '')) AS ?conditionDiagnostic) WHERE {\n"
        f"      {records}\n"
        "      OPTIONAL {\n"
        f"{link}"
        f"{branches}\n"
        f"{guard}"
        "        FILTER (BOUND(?decision))\n"
        "        BIND(?decision AS ?outcome)\n"
        "        BIND(?diagnostic AS ?reason)\n"
        "      }\n"
        "    }\n"
        f"    GROUP BY {record}\n"
        "  }\n"
        f"  BIND({len(plan.conditions)} - ?answered AS ?missing)\n"
        f"  BIND({_aggregate(plan)} AS ?decision)\n"
        f'  BIND(IF(?decision != "Undetermined", ?none, IF(?missing > 0, <{EXE.MissingCandidate}>, IRI(?conditionDiagnostic))) AS ?diagnostic)\n'
        "}\n"
    )


def render_profile_query(plan: ProfilePlan) -> str:
    """The SPARQL query text for one profile plan."""
    return PREFIXES + profile_select(plan)


def _compile_profile_template(plan: ProfilePlan) -> Graph:
    graph = Graph()
    for prefix, namespace in (("mork", MORK), ("exe", EXE), ("elg", ELG)):
        graph.bind(prefix, namespace)
    plan_node = mint(plan.profile, "execplan")
    template = mint(plan.profile, "sparql")
    graph.add((plan_node, RDF.type, EXE.ProfilePlan))
    graph.add((plan_node, EXE.implementsProfile, plan.profile))
    graph.add((plan_node, EXE.usesCompatibilityOperation, plan.aggregation))
    graph.add((plan_node, EXE.derivedFromEligibilityNode, plan.profile))
    graph.add((plan_node, EXE.producesArtefact, template))
    for condition in plan.conditions:
        graph.add((plan_node, EXE.hasConditionPlan, mint(condition.condition, "execplan")))
    graph.add((template, RDF.type, MORK.QueryTemplate))
    graph.add((template, RDF.type, EXE.SparqlArtefact))
    graph.add((template, MORK.queryLanguage, Literal("SPARQL")))
    graph.add((template, MORK.queryText, Literal(render_profile_query(plan))))
    return graph


def compile_query_template(plan: Union[IntervalPlan, ConceptPlan, ProfilePlan]) -> Graph:
    """Emit the ``mork:QueryTemplate`` and its executable-plan provenance."""
    if isinstance(plan, ProfilePlan):
        return _compile_profile_template(plan)
    graph = Graph()
    for prefix, namespace in (("mork", MORK), ("exe", EXE), ("elg", ELG), ("qnt", QNT)):
        graph.bind(prefix, namespace)

    plan_node = mint(plan.condition, "execplan")
    template = mint(plan.condition, "sparql")

    graph.add((plan_node, EXE.implementsCondition, plan.condition))
    graph.add((plan_node, EXE.producesArtefact, template))
    graph.add((plan_node, EXE.derivedFromEligibilityNode, plan.condition))
    if isinstance(plan, ConceptPlan):
        graph.add((plan_node, RDF.type, EXE.ConceptMatchPlan))
        provenance, text = EXE.derivedFromVocabularyNode, render_concept_query(plan)
    else:
        graph.add((plan_node, RDF.type, EXE.IntervalContainmentPlan))
        provenance, text = EXE.derivedFromQuantificationNode, render_query(plan)
    for node in plan.source_nodes:
        if node != plan.condition:
            graph.add((plan_node, provenance, node))

    graph.add((template, RDF.type, MORK.QueryTemplate))
    graph.add((template, RDF.type, EXE.SparqlArtefact))
    graph.add((template, MORK.queryLanguage, Literal("SPARQL")))
    graph.add((template, MORK.queryText, Literal(text)))
    return graph
