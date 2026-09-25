# SPDX-License-Identifier: MPL-2.0

"""
SHACL and SWRL backends for concept plans, and diagnostics on every
Undetermined outcome (ADR-A24, ADR-A28, ADR-A89 items 4 and 6).

SPARQL is the reference (ADR-A28). SHACL is run with pySHACL and read through
the shapes' documented order. The SWRL rules are applied by ``apply_rules``, a
forward-chaining evaluator for rules whose atoms are class, individual- and
data-valued property atoms, and ``swrlb`` numeric comparisons: each body is a
conjunctive query with filters, so evaluating it as SPARQL is exact for these
rules. Loading the rules into an OWL reasoner is the
ADR-A83 harness's job and is not attempted here.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from typing import Dict, Optional, Tuple

from pyshacl import validate
from rdflib import Graph, URIRef
from rdflib.collection import Collection
from rdflib.namespace import RDF
from rdflib.compare import isomorphic

from .common import mint
from .eligibility_ir import ConceptPlan, compile_concept_condition, compile_condition
from .namespaces import ELG, EXE, MORK, SH, SWRL, SWRLB
from .shacl_backend import compile_shapes
from .sparql_backend import compile_query_template
from .swrl_backend import compile_rules
from .test_concept_conditions import ENTITLEMENT
from .test_hierarchical_conditions import DIAGNOSES, EX

ROOT = Path(__file__).resolve().parents[4]
DIAGNOSTICS = {
    EXE.MissingCandidate, EXE.SeveralCandidates, EXE.OutsideScheme, EXE.AboveExclusion,
    EXE.ValueSpaceMismatch, EXE.RefusedOperation,
}
DECISIONS = {ELG.Permitted: "Permitted", ELG.Denied: "Denied"}


def graph(text: str) -> Graph:
    return Graph().parse(data=text, format="turtle")


def with_questions(data: Graph, condition: URIRef, candidates: Dict[str, Tuple[URIRef, ...]]) -> Graph:
    asked = Graph()
    asked += data
    for name, concepts in candidates.items():
        question = EX[f"q-{name}"]
        asked.add((question, RDF.type, ELG.Question))
        asked.add((question, ELG.forCondition, condition))
        for concept in concepts:
            asked.add((question, ELG.candidateConcept, concept))
    return asked


def sparql(plan, data: Graph) -> Dict[URIRef, Tuple[str, Optional[URIRef]]]:
    artefact = compile_query_template(plan)
    template = next(artefact.subjects(RDF.type, MORK.QueryTemplate))
    rows = data.query(str(artefact.value(template, MORK.queryText)))
    return {row.question: (str(row.decision), row.diagnostic) for row in rows}


def shacl(plan: ConceptPlan, data: Graph) -> Dict[URIRef, str]:
    """Read the report in the shapes' documented order."""
    _, report, _ = validate(data, shacl_graph=compile_shapes(plan), advanced=True, inference="none")
    reported: Dict[URIRef, set] = {}
    for result in report.subjects(RDF.type, SH.ValidationResult):
        reported.setdefault(report.value(result, SH.focusNode), set()).add(report.value(result, SH.sourceShape))
    shape = {role: mint(plan.condition, f"{role}-shape") for role in ("readiness", "determinacy", "admission")}
    decisions = {}
    for question in data.subjects(ELG.forCondition, plan.condition):
        found = reported.get(question, set())
        if found & {shape["readiness"], shape["determinacy"]}:
            decisions[question] = "Undetermined"
        elif shape["admission"] in found:
            decisions[question] = "Denied"
        else:
            decisions[question] = "Permitted"
    return decisions


def _term(node, variables: Dict[URIRef, str]) -> str:
    return variables[node] if node in variables else f"<{node}>"


def apply_rules(data: Graph, rules: Graph) -> Graph:
    """Forward-chain every ``swrl:Imp`` in ``rules`` over ``data`` plus the
    rules graph's own facts, to a fixpoint. Returns the derived triples."""
    facts = Graph()
    facts += data
    facts += rules
    variables = {v: f"?v{i}" for i, v in enumerate(sorted(rules.subjects(RDF.type, SWRL.Variable)))}

    def atoms(node):
        return list(Collection(rules, node))

    comparisons = {
        SWRLB.greaterThanOrEqual: ">=", SWRLB.greaterThan: ">",
        SWRLB.lessThanOrEqual: "<=", SWRLB.lessThan: "<",
    }

    def pattern(atom) -> Tuple[str, str, str]:
        kind = rules.value(atom, RDF.type)
        if kind == SWRL.ClassAtom:
            return (_term(rules.value(atom, SWRL.argument1), variables), "a", f"<{rules.value(atom, SWRL.classPredicate)}>")
        if kind in (SWRL.IndividualPropertyAtom, SWRL.DatavaluedPropertyAtom):
            return (
                _term(rules.value(atom, SWRL.argument1), variables),
                f"<{rules.value(atom, SWRL.propertyPredicate)}>",
                _term(rules.value(atom, SWRL.argument2), variables),
            )
        if kind == SWRL.BuiltinAtom and rules.value(atom, SWRL.builtin) in comparisons:
            left, right = list(Collection(rules, rules.value(atom, SWRL.arguments)))
            return ("FILTER", comparisons[rules.value(atom, SWRL.builtin)], (left, right))
        raise AssertionError(f"apply_rules does not evaluate {kind}")

    def clause(p) -> str:
        if p[0] == "FILTER":
            left, right = p[2]
            as_term = lambda n: variables[n] if n in variables else n.n3()  # noqa: E731
            return f"FILTER ({as_term(left)} {p[1]} {as_term(right)})"
        return " ".join(p) + " ."

    derived = Graph()
    changed = True
    while changed:
        changed = False
        for imp in rules.subjects(RDF.type, SWRL.Imp):
            body = [pattern(atom) for atom in atoms(rules.value(imp, SWRL.body))]
            head = [pattern(atom) for atom in atoms(rules.value(imp, SWRL.head))]
            query = "SELECT * WHERE { " + " ".join(clause(p) for p in body) + " }"
            for row in facts.query(query):
                bound = {f"?{name}": value for name, value in row.asdict().items()}
                for s, p, o in head:
                    triple = (bound.get(s) or URIRef(s[1:-1]), URIRef(p[1:-1]), bound.get(o) or URIRef(o[1:-1]))
                    if triple not in facts:
                        facts.add(triple)
                        derived.add(triple)
                        changed = True
    return derived


def swrl(plan: ConceptPlan, data: Graph) -> Dict[URIRef, str]:
    derived = apply_rules(data, compile_rules(plan))
    return {question: DECISIONS[decision] for question, _, decision in derived.triples((None, EXE.impliesDecision, None))}


def everyone(plan: ConceptPlan) -> Dict[str, Tuple[URIRef, ...]]:
    """One question per scheme member, plus absent, several and outside cases."""
    candidates = {str(concept): (concept,) for concept, _ in plan.expansion}
    candidates.update({"absent": (), "several": (EX["lung-tumour"], EX.glioma), "outside": (EX.unlisted,)})
    return candidates


class DiagnosticTests(unittest.TestCase):
    def test_flat_undetermined_rows_name_their_reason(self) -> None:
        data = graph(ENTITLEMENT)
        rows = sparql(compile_concept_condition(data, EX.entitlement), data)
        self.assertEqual(rows[EX["q-absent"]], ("Undetermined", EXE.MissingCandidate))
        self.assertEqual(rows[EX["q-two"]], ("Undetermined", EXE.SeveralCandidates))
        self.assertEqual((rows[EX["q-premium"]][1], rows[EX["q-free"]][1]), (None, None))

    def test_hierarchical_undetermined_rows_name_their_reason(self) -> None:
        data = graph(DIAGNOSES)
        plan = compile_concept_condition(data, EX["solid-tumour-arm"])
        rows = sparql(plan, with_questions(data, plan.condition, {"solid": (EX["solid-tumour"],), "outside": (EX.unlisted,)}))
        self.assertEqual(rows[EX["q-solid"]], ("Undetermined", EXE.AboveExclusion))
        self.assertEqual(rows[EX["q-outside"]], ("Undetermined", EXE.OutsideScheme))

    def test_interval_undetermined_row_names_its_reason(self) -> None:
        data = Graph().parse(ROOT / "ontology/eligibility/examples/interval-containment.ttl")
        plan = compile_condition(data, EX["minimum-credit-condition"])
        data.add((EX["q-empty"], ELG.forCondition, plan.condition))
        rows = sparql(plan, data)
        self.assertEqual(rows[EX["q-empty"]], ("Undetermined", EXE.MissingCandidate))
        self.assertEqual(rows[EX["question-1"]], ("Permitted", None))

    def test_every_undetermined_row_has_a_declared_diagnostic_and_no_other_row_has_one(self) -> None:
        declared = set(Graph().parse(ROOT / "ontology/mork/spec/Executable.ttl").subjects(RDF.type, EXE.Diagnostic))
        self.assertEqual(declared, DIAGNOSTICS)
        data = graph(DIAGNOSES)
        for condition in (EX["solid-tumour-arm"], EX["non-haematological"], EX["not-haematological-flat"]):
            plan = compile_concept_condition(data, condition)
            for decision, diagnostic in sparql(plan, with_questions(data, condition, everyone(plan))).values():
                self.assertEqual(decision == "Undetermined", diagnostic is not None)
                self.assertTrue(diagnostic is None or diagnostic in declared)


class ShaclParityTests(unittest.TestCase):
    def test_shacl_agrees_with_sparql(self) -> None:
        data = graph(DIAGNOSES)
        for condition in (EX["solid-tumour-arm"], EX["non-haematological"], EX["not-haematological-flat"]):
            plan = compile_concept_condition(data, condition)
            asked = with_questions(data, condition, everyone(plan))
            reference = {q: decision for q, (decision, _) in sparql(plan, asked).items()}
            self.assertEqual(shacl(plan, asked), reference, str(condition))

    def test_shacl_agrees_with_sparql_without_a_scheme(self) -> None:
        data = graph(ENTITLEMENT)
        plan = compile_concept_condition(data, EX.entitlement)
        reference = {q: decision for q, (decision, _) in sparql(plan, data).items()}
        self.assertEqual(shacl(plan, data), reference)


class SwrlTests(unittest.TestCase):
    def test_swrl_derives_what_sparql_decides_and_nothing_for_undetermined(self) -> None:
        data = graph(DIAGNOSES)
        for condition in (EX["solid-tumour-arm"], EX["non-haematological"], EX["not-haematological-flat"]):
            plan = compile_concept_condition(data, condition)
            candidates = {k: v for k, v in everyone(plan).items() if len(v) == 1}  # SWRL assumes one candidate
            asked = with_questions(data, condition, candidates)
            reference = {q: d for q, (d, _) in sparql(plan, asked).items() if d != "Undetermined"}
            self.assertEqual(swrl(plan, asked), reference, str(condition))

    def test_without_a_scheme_swrl_denies_only_what_is_excluded(self) -> None:
        data = graph(ENTITLEMENT)
        data.remove((EX["q-two"], None, None))  # SWRL assumes one candidate per question
        plan = compile_concept_condition(data, EX.entitlement)
        derived = swrl(plan, data)
        self.assertEqual(derived, {EX["q-premium"]: "Permitted", EX["q-legacy"]: "Denied"})
        self.assertNotIn(EX["q-free"], derived)  # never Denied from absence

    def test_no_rule_derives_undetermined(self) -> None:
        data = graph(DIAGNOSES)
        for condition in (EX["solid-tumour-arm"], EX["non-haematological"], EX["not-haematological-flat"]):
            rules = compile_rules(compile_concept_condition(data, condition))
            heads = set()
            for imp in rules.subjects(RDF.type, SWRL.Imp):
                for atom in Collection(rules, rules.value(imp, SWRL.head)):
                    heads.add(rules.value(atom, SWRL.argument2))
            self.assertLessEqual(heads, {ELG.Permitted, ELG.Denied})


class DeterminismTests(unittest.TestCase):
    def test_shapes_and_rules_are_deterministic(self) -> None:
        plan = compile_concept_condition(graph(DIAGNOSES), EX["solid-tumour-arm"])
        self.assertTrue(isomorphic(compile_shapes(plan), compile_shapes(plan)))
        self.assertTrue(isomorphic(compile_rules(plan), compile_rules(plan)))



class CliTests(unittest.TestCase):
    def test_concept_condition_compiles_from_the_command_line(self) -> None:
        import tempfile

        from .cli import main
        from .test_hierarchical_conditions import EDITIONS

        with tempfile.TemporaryDirectory() as directory:
            declarations = Path(directory) / "editions.ttl"
            declarations.write_text(EDITIONS)
            out = Path(directory) / "out.ttl"
            base = ["compile-condition", "--declarations", str(declarations), "--condition", str(EX["engineering-benefit"])]
            self.assertEqual(main(base + ["--out", str(out)]), 2)  # bindings, no instant
            self.assertEqual(main(base + ["--at", "2026-06-01T00:00:00+00:00", "--out", str(out)]), 0)
            artefact = Graph().parse(out)
        self.assertIn((None, RDF.type, EXE.ConceptMatchPlan), artefact)
        self.assertIn((EX.data, EXE.admittedBy, EX["engineering-benefit"]), artefact)


if __name__ == "__main__":
    unittest.main()
