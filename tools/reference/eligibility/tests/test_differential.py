# SPDX-License-Identifier: MPL-2.0
"""Differential tests (track B2): ``reference_eligibility.denotation`` against
``tools/mork_compilers``' SPARQL and SHACL backends, over concept-matching
conditions (``elg:ExactMatch``, ``elg:SetMembership``, ``elg:HierarchicalMatch``;
laws L9-L12, L14-L16).

Reuses ``tools/mork_compilers``' own fixtures and test helpers
(``DIAGNOSES``, ``ENTITLEMENT``, ``with_questions``, ``sparql``, ``shacl``)
rather than duplicating them: these are the same hierarchical and flat
scheme graphs, and the same backend-execution helpers, that package's own
tests already exercise, so a disagreement found here is between this
reference and the compiler, not between two different readings of two
different graphs or two different ways of running a query.

**Not covered here** (a later slice's job, not this one's): ``elg:IntervalContainment``
(outside B1's scope), evidence-path-bound conditions (every candidate here
is read directly from ``elg:candidateConcept``, the ``plan.evidence is None``
case), profile-level aggregation (L6-L8), SWRL and OWL backends (both refuse
more than this harness exercises, by their own documented restrictions --
track B's sketch §3).
"""

from __future__ import annotations

from itertools import chain, combinations
from typing import Dict, Optional, Sequence

import mork_compilers.eligibility_ir as eligibility_ir
from mork_compilers.eligibility_ir import ConceptPlan, compile_concept_condition
from mork_compilers.namespaces import ELG
from mork_compilers.test_concept_backends import shacl, sparql, with_questions
from mork_compilers.test_concept_conditions import ENTITLEMENT
from mork_compilers.test_concept_conditions import EX as FLAT_EX
from mork_compilers.test_concept_conditions import graph as flat_graph
from mork_compilers.test_flat_schemes import LENDER_B
from mork_compilers.test_flat_schemes import example as lending_example
from mork_compilers.test_hierarchical_conditions import DIAGNOSES
from mork_compilers.test_hierarchical_conditions import EX as HIER_EX
from mork_compilers.test_hierarchical_conditions import HEADER as HIER_HEADER
from mork_compilers.test_hierarchical_conditions import graph as hier_graph
from rdflib import RDF, Graph, URIRef

from reference_eligibility.denotation import Scheme, decide_concept_match
from reference_eligibility.kernel import DENIED, PERMITTED, UNDETERMINED

DECISION_NAME = {PERMITTED: "Permitted", DENIED: "Denied", UNDETERMINED: "Undetermined"}


def _scheme_from_plan(plan: ConceptPlan) -> Optional[Scheme]:
    """The reference's ``Scheme`` built from the IR's own resolved
    membership and ordering (``plan.hierarchy``) -- the same data the
    compilers read, not a second resolution of it."""
    if plan.scheme is None:
        return None
    members = frozenset(member for member, _ in plan.hierarchy)
    broader = {member: frozenset(bs) for member, bs in plan.hierarchy}
    return Scheme(members=members, broader=broader)


def reference_decision(plan: ConceptPlan, candidate: URIRef) -> str:
    decision = decide_concept_match(
        candidate,
        hierarchical=plan.hierarchical,
        required=set(plan.required),
        excluded=set(plan.excluded),
        scheme=_scheme_from_plan(plan),
    )
    return DECISION_NAME[decision]


def agree(data: Graph, plan: ConceptPlan, candidates: Dict[str, Optional[URIRef]]) -> Dict[str, Dict[str, str]]:
    """For each named candidate (``None`` meaning a question with no
    candidate at all, the "not a value" case): the reference's decision,
    the compiled SPARQL's decision (executed, not inspected as text), and
    the compiled SHACL's decision (validated with pySHACL) -- one row per
    name, so a disagreement names which backend and which candidate."""
    present = {name: (concept,) for name, concept in candidates.items() if concept is not None}
    asked = with_questions(data, plan.condition, present)
    for name, concept in candidates.items():
        if concept is None:
            asked.add((HIER_EX[f"q-{name}"], RDF.type, ELG.Question))
            asked.add((HIER_EX[f"q-{name}"], ELG.forCondition, plan.condition))
    sparql_rows = sparql(plan, asked)
    shacl_rows = shacl(plan, asked)
    results = {}
    for name, concept in candidates.items():
        question = HIER_EX[f"q-{name}"]
        results[name] = {
            "reference": reference_decision(plan, concept) if concept is not None else "Undetermined",
            "sparql": sparql_rows[question][0],
            "shacl": shacl_rows[question],
        }
    return results


class TestHierarchicalMatchWithExclusion:
    """DIAGNOSES: a trial admits solid tumours except those of the central
    nervous system (required solid-tumour, excluded cns-tumour)."""

    def setup_method(self) -> None:
        self.data = hier_graph(DIAGNOSES)
        self.plan = compile_concept_condition(self.data, HIER_EX["solid-tumour-arm"])
        self.candidates: Dict[str, Optional[URIRef]] = {
            "lung": HIER_EX["lung-tumour"],
            "glioma": HIER_EX.glioma,
            "cns": HIER_EX["cns-tumour"],
            "solid": HIER_EX["solid-tumour"],
            "neoplasm": HIER_EX.neoplasm,
            "haematological": HIER_EX.haematological,
            "unlisted": HIER_EX.unlisted,
            "absent": None,
        }
        self.results = agree(self.data, self.plan, self.candidates)

    def test_every_candidate_agrees_across_reference_sparql_and_shacl(self) -> None:
        for name, row in self.results.items():
            assert row["reference"] == row["sparql"] == row["shacl"], (name, row)

    def test_narrower_than_required_is_permitted(self) -> None:
        assert self.results["lung"]["reference"] == "Permitted"

    def test_at_or_below_the_exclusion_is_denied(self) -> None:
        assert self.results["cns"]["reference"] == "Denied"
        assert self.results["glioma"]["reference"] == "Denied"

    def test_above_the_exclusion_is_undetermined_l11(self) -> None:
        """The named negative fixture (L11): solid-tumour is required and
        stands above the excluded cns-tumour -- evidence that an exclusion
        applies may move the outcome only from Undetermined, never from
        Permitted."""
        assert self.results["solid"]["reference"] == "Undetermined"

    def test_outside_every_inclusion_is_denied(self) -> None:
        assert self.results["neoplasm"]["reference"] == "Denied"
        assert self.results["haematological"]["reference"] == "Denied"

    def test_outside_the_scheme_and_not_a_value_are_undetermined(self) -> None:
        """"Not a value" first (sketch §3): a candidate outside the resolved
        scheme, and a question with no candidate at all, both Undetermined,
        across all three implementations."""
        assert self.results["unlisted"]["reference"] == "Undetermined"
        for row in (self.results["unlisted"], self.results["absent"]):
            assert row["reference"] == row["sparql"] == row["shacl"] == "Undetermined"


class TestL11OverEveryMember:
    """L11, generalised: for every member of the resolved scheme, an
    exclusion's effect never promotes a candidate to Permitted -- generated
    across the whole scheme, not only the one named case above."""

    def setup_method(self) -> None:
        self.data = hier_graph(DIAGNOSES)
        self.plan = compile_concept_condition(self.data, HIER_EX["solid-tumour-arm"])

    def test_no_member_above_or_at_an_exclusion_is_ever_permitted(self) -> None:
        excluded = set(self.plan.excluded)
        scheme = _scheme_from_plan(self.plan)
        assert scheme is not None
        for member in scheme.members:
            stands_above_or_at_an_exclusion = any(
                excl in scheme.ancestors(member) for excl in excluded if excl in scheme.members
            )
            if stands_above_or_at_an_exclusion:
                decision = reference_decision(self.plan, member)
                assert decision != "Permitted", member


class TestFlatSetMembershipWithExclusion:
    """ENTITLEMENT: premium and enterprise tiers qualify, except the legacy
    enterprise tier -- a flat scheme (elg:SetMembership, no hierarchy), with
    the fixture's own pre-built Questions reused directly, including
    q-absent (no candidate) and q-two (two candidates, ambiguous)."""

    def setup_method(self) -> None:
        self.data = flat_graph(ENTITLEMENT)
        self.plan = compile_concept_condition(self.data, FLAT_EX.entitlement)
        self.sparql_rows = sparql(self.plan, self.data)
        self.shacl_rows = shacl(self.plan, self.data)

    def _reference_for(self, concept: Optional[URIRef]) -> str:
        if concept is None:
            return "Undetermined"
        return reference_decision(self.plan, concept)

    def test_required_and_not_excluded_is_permitted(self) -> None:
        assert self._reference_for(FLAT_EX["tier-premium"]) == "Permitted"
        assert self.sparql_rows[FLAT_EX["q-premium"]][0] == "Permitted"
        assert self.shacl_rows[FLAT_EX["q-premium"]] == "Permitted"

    def test_required_but_also_excluded_is_denied_l10(self) -> None:
        assert self._reference_for(FLAT_EX["tier-enterprise-legacy"]) == "Denied"
        assert self.sparql_rows[FLAT_EX["q-legacy"]][0] == "Denied"
        assert self.shacl_rows[FLAT_EX["q-legacy"]] == "Denied"

    def test_not_required_is_denied(self) -> None:
        assert self._reference_for(FLAT_EX["tier-free"]) == "Denied"
        assert self.sparql_rows[FLAT_EX["q-free"]][0] == "Denied"
        assert self.shacl_rows[FLAT_EX["q-free"]] == "Denied"

    def test_no_candidate_is_undetermined(self) -> None:
        """"Not a value" first: q-absent has no elg:candidateConcept at all."""
        assert self.sparql_rows[FLAT_EX["q-absent"]][0] == "Undetermined"
        assert self.shacl_rows[FLAT_EX["q-absent"]] == "Undetermined"

    def test_several_candidates_with_no_reading_is_undetermined(self) -> None:
        """q-two has two candidates and no declared value reading to combine
        them -- ambiguous (exe:SeveralCandidates), the same rule
        reference_eligibility.denotation.decide_condition's SingleValue
        branch enforces (found via this harness, fixed in B1 -- see
        test_denotation.py's test_single_value_with_several_values_is_undetermined)."""
        assert self.sparql_rows[FLAT_EX["q-two"]][0] == "Undetermined"
        assert self.shacl_rows[FLAT_EX["q-two"]] == "Undetermined"


class TestHierarchyPreconditionL14:
    """``ontology/eligibility/examples/flat-scheme-lending.ttl``'s
    ``eligible-sector`` condition, under a lender's scope binding that
    resolves to a flat list (no member has a broader member within it):
    L14 leaves an unnamed sector Undetermined, not Denied, before L12's
    default inclusion would otherwise apply. Runs over a real Eligibility
    example fixture, not a synthetic one, per the plan's own validation
    criterion."""

    def setup_method(self) -> None:
        self.data = lending_example("flat-scheme-lending")
        self.plan = compile_concept_condition(self.data, HIER_EX["eligible-sector"], LENDER_B)
        assert self.plan.no_hierarchy
        self.sparql_rows = sparql(self.plan, self.data)
        self.shacl_rows = shacl(self.plan, self.data)

    def _reference_for(self, name: str) -> str:
        return reference_decision(self.plan, HIER_EX[name])

    def test_named_sector_is_permitted(self) -> None:
        assert self._reference_for("retail") == "Permitted"
        assert self.sparql_rows[HIER_EX["q-retail"]][0] == "Permitted"
        assert self.shacl_rows[HIER_EX["q-retail"]] == "Permitted"

    def test_unnamed_sector_is_undetermined_not_denied(self) -> None:
        for name in ("food-processing", "wholesale"):
            assert self._reference_for(name) == "Undetermined", name
            assert self.sparql_rows[HIER_EX[f"q-{name}"]][0] == "Undetermined", name
            assert self.shacl_rows[HIER_EX[f"q-{name}"]] == "Undetermined", name


class TestHarnessCatchesACompilerFault:
    """B2.1 (the formal-methods epic's second review \u00a73.1): this harness's stated
    rationale is catching a bug shared by every backend through
    ``eligibility_ir._expand``, not merely a disagreement the reference itself caused --
    never tested until now. Both of B2's own recorded findings were bugs in the
    reference, found because it disagreed with the compilers, never the reverse. Seed a
    deliberate fault directly into ``_expand`` (not the reference) and confirm the
    comparison against the unchanged reference catches it, the same "prove it can fail"
    discipline every other seeded defect in this epic already uses. ``_expand`` feeds
    ``ConceptPlan.expansion``, which the SHACL backend reads directly
    (``shacl_backend.py``'s admitted/undetermined lists), so a fault here reaches a real
    backend's real output, not only a second copy of the reference's own logic."""

    def test_a_wrong_expand_result_is_caught_as_a_disagreement(self, monkeypatch) -> None:
        data = hier_graph(DIAGNOSES)
        plan = compile_concept_condition(data, HIER_EX["solid-tumour-arm"])
        candidate = HIER_EX["lung-tumour"]
        reference = reference_decision(plan, candidate)
        assert reference == "Permitted"  # sanity, before the fault is seeded

        real_expand = eligibility_ir._expand

        def faulty_expand(ordering, hierarchical, required, excluded):
            decided = real_expand(ordering, hierarchical, required, excluded)
            return tuple(
                (concept, eligibility_ir.DENIED) if concept == candidate else (concept, decision)
                for concept, decision in decided
            )

        monkeypatch.setattr(eligibility_ir, "_expand", faulty_expand)
        faulty_plan = compile_concept_condition(data, HIER_EX["solid-tumour-arm"])
        asked = with_questions(data, faulty_plan.condition, {"lung": (candidate,)})
        faulty_shacl_rows = shacl(faulty_plan, asked)

        assert faulty_shacl_rows[HIER_EX["q-lung"]] != reference
        assert faulty_shacl_rows[HIER_EX["q-lung"]] == "Denied"


# Bounded-exhaustive generation (B2.1): three concepts in one generated scheme, every
# scheme shape, every required/excluded subset drawn from a small alphabet, and both
# match modes -- a defensible, bounded-universal claim over this input space, rather
# than only the fixed, hand-picked fixtures above.
_GEN_CONCEPTS = ("c0", "c1", "c2")


def _powerset(items: Sequence[str]) -> list:
    return [frozenset(c) for n in range(len(items) + 1) for c in combinations(items, n)]


def _generated_turtle(*, chained: bool, hierarchical: bool, required: frozenset, excluded: frozenset) -> str:
    """A small, generated Eligibility fixture (B2.1): ``c0``, ``c1``, ``c2`` in one
    scheme, either flat or a ``c0 < c1 < c2`` chain (``skos:broader``), one condition
    with the given required/excluded sets under the given match strategy, plus one
    concept (``outsider``) deliberately outside the scheme entirely."""
    lines = [
        "ex:gen-scheme a voc:ConceptScheme .",
        "ex:outsider a skos:Concept .",
    ]
    for concept in _GEN_CONCEPTS:
        lines.append(f"ex:{concept} a skos:Concept ; skos:inScheme ex:gen-scheme .")
    if chained:
        lines.append("ex:c1 skos:broader ex:c0 .")
        lines.append("ex:c2 skos:broader ex:c1 .")
    lines.append("ex:gen-contract a voc:SchemeContract ; voc:boundScheme ex:gen-scheme .")
    strategy = "elg:HierarchicalMatch" if hierarchical else "elg:SetMembership"
    condition = [
        "ex:gen-condition a elg:Condition ;",
        f"    elg:matchStrategy {strategy} ;",
        "    elg:compatibilityOperation elg:AllRequired ;",
        "    elg:wildcardSemantics elg:NoWildcard ;",
        "    elg:constrainedByContract ex:gen-contract",
    ]
    for concept in sorted(required):
        condition.append(f"    ; elg:requiredConcept ex:{concept}")
    for concept in sorted(excluded):
        condition.append(f"    ; elg:excludedConcept ex:{concept}")
    condition.append("    .")
    lines.extend(condition)
    return HIER_HEADER + "\n".join(lines)


class TestBoundedExhaustiveConceptMatching:
    """Every combination of: both match modes, a flat or a chained three-concept
    scheme, every required subset of {c0, c1} and every excluded subset of {c2} (the
    all-empty combination is refused by the compiler itself and skipped), checked for
    every candidate inside and outside the scheme -- the concept-matching input space
    is small enough to generate exhaustively rather than sample (B2.1)."""

    CASES = [
        (chained, hierarchical, required, excluded)
        for chained in (False, True)
        for hierarchical in (False, True)
        for required in _powerset(("c0", "c1"))
        for excluded in _powerset(("c2",))
        if required or excluded
    ]

    def test_reference_agrees_with_sparql_and_shacl_for_every_case(self) -> None:
        assert len(self.CASES) == 2 * 2 * 7  # a fixed count, so a change here is deliberate
        for chained, hierarchical, required, excluded in self.CASES:
            text = _generated_turtle(
                chained=chained, hierarchical=hierarchical, required=required, excluded=excluded
            )
            data = graph_from(text)
            plan = compile_concept_condition(data, HIER_EX["gen-condition"])
            candidates = {name: HIER_EX[name] for name in (*_GEN_CONCEPTS, "outsider")}
            asked = with_questions(data, plan.condition, {n: (c,) for n, c in candidates.items()})
            sparql_rows = sparql(plan, asked)
            shacl_rows = shacl(plan, asked)
            for name, concept in candidates.items():
                question = HIER_EX[f"q-{name}"]
                expected = reference_decision(plan, concept)
                case = (chained, hierarchical, sorted(required), sorted(excluded), name)
                assert sparql_rows[question][0] == expected, case
                assert shacl_rows[question] == expected, case


def graph_from(text: str) -> Graph:
    """A trivial wrapper so this module's generated fixtures do not depend on
    ``test_hierarchical_conditions``'s own ``graph`` beyond its HEADER constant,
    kept separate since that module's ``graph`` is not re-exported for reuse."""
    g = Graph()
    g.parse(data=text, format="turtle")
    return g
