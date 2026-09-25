<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A87: Eligibility concept inclusion and exclusion

**Status:** Proposed
**Date:** 2026-09-25
**Related:** ADR-A03 (condition taxonomy), ADR-A06 (wildcard semantics),
ADR-A85 (scoped and temporal binding resolution), ADR-A86 (ontology semantic
versioning)
**Unit:** [`applied-ontology-readiness`](../../developer/plans/applied-ontology-readiness.md)

## Context

ADR-A03 gives every condition a match strategy, but until commit `9a12da4`
Eligibility had no property naming the concepts an `ExactMatch`,
`SetMembership` or `HierarchicalMatch` condition matches against, and no way
to state an exception. Applied ontologies need both. A clinical-trial
protocol admits "any solid tumour except those of the central nervous
system". An employment policy grants a benefit to "every job family except
contractor grades". Neither can be written as a union of ranges, which is how
`IntervalContainment` already expresses gaps.

Commit `9a12da4` added `elg:requiredConcept`, `elg:excludedConcept`, the
`elg:StaticConstraint` law register, laws L10 to L13, two warning shapes and a
decision table in `ontology/eligibility/README.md` §4. It landed without an
ADR. This ADR records the decision so it can be ratified or amended, and
corrects one defect found since.

## Decision

1. A condition matching by `ExactMatch`, `SetMembership` or
   `HierarchicalMatch` states its concepts with `elg:requiredConcept` and
   `elg:excludedConcept`. Several required concepts are alternatives. Each
   excluded concept excludes independently. Match is equality for the first
   two strategies and "at or below, in the bound scheme's ordering" for
   `HierarchicalMatch`, with the scheme resolved under ADR-A85.
2. Decisions follow the README §4 table: exclusion takes precedence (L10), a
   candidate strictly above an excluded concept is `Undetermined` (L11), and a
   condition with exclusions only admits every other member of its bound
   scheme (L12).
3. An exclusion that falls inside no inclusion excludes nothing and is
   reported as a warning (L13, `elg:ReachableExclusionShape`).
4. A concept-matching condition that declares no concept is reported as a
   warning (`elg:ConceptConditionDeclarationShape`). This warning applies to
   conditions that match candidates directly. It does not apply to an
   `elg:AdmissionProfile`, which ADR-A03 makes a condition but whose concepts
   belong to the conditions it composes. The shape as committed in `9a12da4`
   also fires on profiles. Excluding a focus node that has `elg:hasCondition`
   corrects it.
5. Both shapes are `sh:Warning`. A graph that conformed before `9a12da4`
   still conforms.

## Consequences

- The `9a12da4` change is MINOR under ADR-A86, as recorded in that commit.
  The profile correction in item 4 is a PATCH to `eligibility/spec` (a shape
  brought into line with documented intent), with the import cascade the
  policy requires.
- Eligibility's own examples must declare concepts on their concept-matching
  conditions, or they demonstrate a warning. The examples are patched in the
  unit's slice AOR-2, each with a comment naming the warning that removing the
  concept would raise.
- No backend compiles these semantics yet. ADR-A89 proposes the compiled form.
- Questions have no concept-valued candidate property. `elg:candidateValue`
  ranges over `qnt:Value`. ADR-A89 addresses this.
