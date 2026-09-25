# SPDX-License-Identifier: MPL-2.0

"""A limit stated in several units (ADR-A95): each candidate is compared with
the statement in its own unit, never converted, and is Undetermined when no
statement is in its unit. SPARQL is the reference, SHACL must agree, SWRL
must derive a sound subset."""

from __future__ import annotations

import unittest

from pyshacl import validate
from rdflib import Graph, Namespace
from rdflib.namespace import RDF

from .common import mint
from .eligibility_ir import IRCompileError, compile_any_condition, compile_condition
from .namespaces import ELG, EXE, MORK, QNT, SH
from .shacl_backend import compile_shapes
from .sparql_backend import compile_query_template
from .swrl_backend import compile_rules
from .test_concept_backends import apply_rules

EX = Namespace("https://example.org/lattice/lending/")

LIMIT = """
@prefix elg: <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .
@prefix qnt: <https://www.nebularis.org/neuro-semantic/lattice/quantification#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <https://example.org/lattice/lending/> .

ex:money a qnt:ValueSpace .
ex:usd-limit a qnt:Quantity ; qnt:onSpace ex:money ; qnt:numericValue 10000000 ; qnt:inUnit ex:USD .
ex:eur-limit a qnt:Quantity ; qnt:onSpace ex:money ; qnt:numericValue 9000000 ; qnt:inUnit ex:EUR .
ex:ceiling a qnt:Bound ; qnt:onSpace ex:money ; qnt:boundValue ex:usd-limit ;
    qnt:boundSense qnt:Upper ; qnt:boundClosure qnt:Closed ; qnt:alternativeBound ex:ceiling-eur .
ex:ceiling-eur a qnt:Bound ; qnt:onSpace ex:money ; qnt:boundValue ex:eur-limit ;
    qnt:boundSense qnt:Upper ; qnt:boundClosure qnt:Closed .
ex:up-to-limit a qnt:Range ; qnt:onSpace ex:money ; qnt:upperBound ex:ceiling ; qnt:hasBound ex:ceiling .
ex:allowed a qnt:RangeSet ; qnt:onSpace ex:money ; qnt:hasRange ex:up-to-limit .

ex:facility-limit a elg:IntervalCondition ;
    elg:matchStrategy elg:IntervalContainment ;
    elg:compatibilityOperation elg:AllRequired ;
    elg:wildcardSemantics elg:NoWildcard ;
    elg:requiredRangeSet ex:allowed .
"""

# name -> (amount, unit or None)
CANDIDATES = {
    "usd-within": (8000000, "USD"), "usd-over": (12000000, "USD"),
    "eur-within": (8000000, "EUR"), "eur-over": (9500000, "EUR"),
    "gbp": (5000000, "GBP"), "unitless": (5000000, None),
}
EXPECTED = {
    "usd-within": "Permitted", "usd-over": "Denied", "eur-within": "Permitted",
    "eur-over": "Denied", "gbp": "Undetermined", "unitless": "Undetermined",
}


def questions() -> Graph:
    """One question per candidate, each offering a one-point range."""
    lines = []
    for name, (amount, unit) in CANDIDATES.items():
        in_unit = f" ; qnt:inUnit ex:{unit}" if unit else ""
        lines.append(
            f"ex:v-{name} a qnt:Quantity ; qnt:onSpace ex:money ; qnt:numericValue {amount}{in_unit} .\n"
            f"ex:b-{name} qnt:boundValue ex:v-{name} .\n"
            f"ex:r-{name} qnt:lowerBound ex:b-{name} ; qnt:upperBound ex:b-{name} .\n"
            f"ex:s-{name} qnt:hasRange ex:r-{name} .\n"
            f"ex:q-{name} a elg:Question ; elg:forCondition ex:facility-limit ; elg:candidateRangeSet ex:s-{name} .\n"
        )
    return Graph().parse(data=LIMIT + "".join(lines), format="turtle")


def sparql(plan, data: Graph) -> dict:
    artefact = compile_query_template(plan)
    query = str(artefact.value(next(artefact.subjects(RDF.type, MORK.QueryTemplate)), MORK.queryText))
    return {str(row.question).rsplit("/q-", 1)[-1]: (str(row.decision), row.diagnostic) for row in data.query(query)}


class AlternativeBoundTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = questions()
        self.plan = compile_condition(self.data, EX["facility-limit"])

    def test_plan_holds_one_interval_per_unit(self) -> None:
        self.assertEqual({(i.upper, str(i.unit).rsplit("/", 1)[1]) for i in self.plan.required},
                         {(10000000.0, "USD"), (9000000.0, "EUR")})

    def test_each_candidate_is_compared_in_its_own_unit(self) -> None:
        rows = sparql(self.plan, self.data)
        self.assertEqual({k: d for k, (d, _) in rows.items()}, EXPECTED)
        self.assertEqual((rows["gbp"][1], rows["unitless"][1]), (EXE.NoBoundInUnit, EXE.NoBoundInUnit))

    def test_shacl_agrees(self) -> None:
        _, report, _ = validate(self.data, shacl_graph=compile_shapes(self.plan), advanced=True, inference="none")
        found = {}
        for result in report.subjects(RDF.type, SH.ValidationResult):
            found.setdefault(report.value(result, SH.focusNode), set()).add(report.value(result, SH.sourceShape))
        readiness = mint(self.plan.condition, "readiness-shape")
        containment = mint(self.plan.condition, "containment-shape")
        decisions = {}
        for name in CANDIDATES:
            shapes = found.get(EX[f"q-{name}"], set())
            decisions[name] = "Undetermined" if readiness in shapes else "Denied" if containment in shapes else "Permitted"
        self.assertEqual(decisions, EXPECTED)

    def test_swrl_derives_only_matching_units(self) -> None:
        derived = apply_rules(self.data, compile_rules(self.plan))
        permitted = {str(q).rsplit("/q-", 1)[-1] for q, _, _ in derived.triples((None, EXE.impliesDecision, ELG.Permitted))}
        self.assertEqual(permitted, {"usd-within", "eur-within"})

    def test_two_statements_in_one_unit_are_refused(self) -> None:
        self.data.set((EX["eur-limit"], QNT.inUnit, EX.USD))
        with self.assertRaises(IRCompileError):
            compile_condition(self.data, EX["facility-limit"])


class BoundSubjectTests(unittest.TestCase):
    def test_bound_subjects_are_compared_in_their_own_unit(self) -> None:
        data = Graph().parse(data=LIMIT + """
            @prefix owl: <http://www.w3.org/2002/07/owl#> .
            ex:Facility a owl:Class .
            ex:binding a elg:EvidenceBinding ; elg:bindsCondition ex:facility-limit ; elg:subjectClass ex:Facility ;
                elg:evidenceStep [ elg:stepIndex 0 ; elg:stepProperty ex:drawn ; elg:stepDirection elg:Forward ] .
            ex:a a ex:Facility ; ex:drawn [ a qnt:Quantity ; qnt:onSpace ex:money ; qnt:numericValue 8500000 ; qnt:inUnit ex:EUR ] .
            ex:b a ex:Facility ; ex:drawn [ a qnt:Quantity ; qnt:onSpace ex:money ; qnt:numericValue 9500000 ; qnt:inUnit ex:EUR ] .
            ex:c a ex:Facility ; ex:drawn [ a qnt:Quantity ; qnt:onSpace ex:money ; qnt:numericValue 1 ; qnt:inUnit ex:GBP ] .
        """, format="turtle")
        plan = compile_any_condition(data, EX["facility-limit"])
        rows = {k.rsplit("/", 1)[-1]: v for k, v in sparql(plan, data).items()}
        self.assertEqual({k: d for k, (d, _) in rows.items()}, {"a": "Permitted", "b": "Denied", "c": "Undetermined"})
        self.assertEqual(rows["c"][1], EXE.NoBoundInUnit)


if __name__ == "__main__":
    unittest.main()
