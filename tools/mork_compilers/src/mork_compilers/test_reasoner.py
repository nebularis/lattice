# SPDX-License-Identifier: MPL-2.0

"""
Generated SWRL loaded into HermiT through the ADR-A83 harness (L4). Checks
that the reasoner derives exactly what ``apply_rules`` derives for the
builtin-free rules: concept, profile and bound-subject rules. Interval rules
use ``swrlb`` builtins, which HermiT does not evaluate. Skipped when the
harness jar is not built (``mise run bootstrap:reasoning-testkit``).
"""

from __future__ import annotations

import unittest
from pathlib import Path

from rdflib import Graph, URIRef

from . import reasoning
from .eligibility_ir import compile_any_condition, compile_concept_condition, compile_profile
from .namespaces import EXE
from .swrl_backend import compile_rules
from .test_concept_backends import apply_rules, everyone, with_questions
from .test_evidence_bindings import EX as EMPLOYMENT
from .test_evidence_bindings import fixture as employment
from .test_hierarchical_conditions import DIAGNOSES, EX
from .test_profiles import records

ROOT = Path(__file__).resolve().parents[4]
SPECS = [Graph().parse(ROOT / path) for path in (
    "ontology/eligibility/spec/eligibility.ttl", "ontology/mork/spec/Executable.ttl")]


def pairs(graph: Graph, prop: URIRef) -> set:
    return {(s, o) for s, _, o in graph.triples((None, prop, None))}


@unittest.skipUnless(reasoning.available(), "reasoning-testkit jar not built")
class HermitSwrlTests(unittest.TestCase):
    def agree(self, data: Graph, plans, prop: URIRef, entailed: frozenset = frozenset()) -> None:
        """HermiT derives what apply_rules derives, plus ``entailed``: pairs
        that need OWL entailment, which apply_rules does not perform."""
        rules = Graph()
        for plan in plans:
            rules += compile_rules(plan)
        expected = pairs(apply_rules(data, rules), prop) | entailed
        derived = {(URIRef(s), URIRef(o)) for s, o in reasoning.run("values", str(prop), graphs=SPECS + [data, rules])}
        self.assertTrue(expected, "the fixture should derive something")
        self.assertEqual(derived, expected)

    def test_concept_rules(self) -> None:
        data = Graph().parse(data=DIAGNOSES, format="turtle")
        plan = compile_concept_condition(data, EX["solid-tumour-arm"])
        asked = with_questions(data, plan.condition, {k: v for k, v in everyone(plan).items() if len(v) == 1})
        self.agree(asked, [plan], EXE.impliesDecision)

    def test_profile_rules(self) -> None:
        data = records("all-arm")
        plan = compile_profile(data, EX["all-arm"])
        self.agree(data, list(plan.conditions) + [plan], EXE.impliesProfileDecision)

    def test_bound_subject_rules(self) -> None:
        # DL-safe rules bind only named individuals, so the fixture's blank-node
        # roles are skolemised: through a blank node HermiT derives nothing.
        data = employment()
        data.remove((EMPLOYMENT.gina, None, None))
        data = data.skolemize(authority="https://example.org", basepath="/lattice/role/")
        plan = compile_any_condition(data, EMPLOYMENT["engineering-family"])
        # hal is a Manager, a subclass of Employee, so only a reasoner reaches him
        self.agree(data, [plan], EXE.permittedUnder, frozenset({(EMPLOYMENT.hal, plan.condition)}))


if __name__ == "__main__":
    unittest.main()
