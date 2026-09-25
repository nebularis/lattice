<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AOR-5, flat concept conditions

**Unit:** [`applied-ontology-readiness`](../status/applied-ontology-readiness.md)
**Plan section:** [Phase B](../plans/applied-ontology-readiness.md#phase-b-executable-coverage)
**Decisions:** [ADR-A89](../../architecture/decisions/ADR-A89-eligibility-ir-concept-conditions-and-profile-aggregation.md) items 1, 2 and 4 (SPARQL), [ADR-A87](../../architecture/decisions/ADR-A87-eligibility-concept-inclusion-and-exclusion.md), both Proposed

## Invariant

A condition matching by `ExactMatch` or `SetMembership` compiles through the
shared IR, and its SPARQL artefact decides every question as the ADR-A87
table says. It never denies for absent evidence (ADR-A24).

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AOR5-01 | a set condition with three required concepts, one also excluded / compiled / plan holds both sets, sorted | L1 | + |
| AOR5-02 | the condition stripped of concepts / compiled / refused | L1 | - |
| AOR5-03 | a non-default wildcard policy / compiled / refused | L1 | - |
| AOR5-04 | an interval strategy / compiled as a concept plan / refused | L1 | - |
| AOR5-05 | candidate in the required set / SPARQL executed / `Permitted` | L1 | + |
| AOR5-06 | candidate outside every required concept / executed / `Denied` | L1 | - |
| AOR5-07 | candidate both required and excluded / executed / `Denied` (L10) | L1 | - |
| AOR5-08 | question with no candidate / executed / `Undetermined` | L1 | - |
| AOR5-09 | question with two candidates / executed / `Undetermined` | L1 | - |
| AOR5-10 | artefact / inspected / plan typed `exe:ConceptMatchPlan`, `exe:derivedFromVocabularyNode` names every concept | L1 | + |
| AOR5-11 | one plan compiled twice / compared / isomorphic | L2 | + |
| AOR5-12 | `condition-taxonomy.ttl`'s exact condition plus two questions / executed / `Permitted` and `Denied` | L1 | + |

Every decision case runs the generated query with rdflib's SPARQL engine.

## One command

```bash
mise run check:mork-compilers
```

Pass: `27 passed` (the 15 existing compiler tests and the 12 above). Also
run `mise run check:ontology-catalog`, which includes the Eligibility example
tests.

## Artefacts to inspect

- `elg:candidateConcept` in `ontology/eligibility/README.md` §5 and the spec,
  and the README §4 sentence and table row on candidates. A question with
  more than one candidate is `Undetermined`. That reading is new and flagged
  in the status record.
- `elg:UndeterminedWhenNoCandidateInput` in `shapes/rules.ttl` now recognises
  `elg:candidateConcept`. Without this, the migrated `hierarchical-match.ttl`
  received a second decision value and broke L6. AOR2-01 caught it.
- `exe:ConceptMatchPlan` and `exe:derivedFromVocabularyNode` in
  `ontology/mork/spec/Executable.ttl`.
- Versions: Eligibility is MINOR, so the Eligibility cascade moves to 0.4.0
  against the committed 0.3.0, superseding AOR-2's interim 0.3.1. Executable
  moves 0.2.0 → 0.3.0. Nothing imports Executable.

## Adversarial probe (run by the agent)

Dropping the exclusion clause failed AOR5-07. Letting two candidates through
(`< 1` for `!= 1`) failed AOR5-09.

## Deviations from the plan

- `exe:ConceptMatchPlan` lands here, not in AOR-7, because the SPARQL
  artefact's provenance needs it. `exe:derivedFromVocabularyNode` is new, since
  concepts are neither Eligibility nor Quantification nodes.
- Exclusion-only flat conditions (L12) need the bound scheme's members, so
  they are refused here and handled with scheme resolution in AOR-6.
- Conformance-corpus cases compare profile-level decisions. They land with
  profile aggregation in AOR-8.

## Deliberate non-coverage

- Hierarchical match and scheme resolution (AOR-6).
- SHACL and SWRL for concept plans (AOR-7).
- Diagnostic codes for `Undetermined` (AOR-7).
