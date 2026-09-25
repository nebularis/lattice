<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AOR-2, Eligibility examples and the declaration warning

**Unit:** [`applied-ontology-readiness`](../status/applied-ontology-readiness.md)
**Plan section:** [AOR-2](../plans/applied-ontology-readiness.md#aor-2-eligibility-examples-and-the-declaration-warning)
**Decision:** [ADR-A87](../../architecture/decisions/ADR-A87-eligibility-concept-inclusion-and-exclusion.md), Proposed

## Invariant

Every Eligibility example validates against the layer's shapes with no
violation and no warning. `elg:ConceptConditionDeclarationShape` warns on a
concept-matching condition that declares no concept, and does not warn on an
admission profile, whose concepts belong to its conditions (ADR-A87 item 4).

## Test cases

| ID | Given / When / Then | Level | Invariant | +/- |
|---|---|---|---|---|
| AOR2-01 | `hierarchical-match.ttl` / validated / no results | L1 | examples conform | + |
| AOR2-02 | `condition-taxonomy.ttl` / validated / no results | L1 | examples conform | + |
| AOR2-03 | `interval-containment.ttl` / validated / no results | L1 | examples conform, profile exempt | + |
| AOR2-04 | `hierarchical-match.ttl` without the condition's required concept / validated / one declaration warning on `ex:hierarchical-condition` | L1 | warning fires | - |
| AOR2-05 | as AOR2-04 for `ex:exact-condition` | L1 | warning fires | - |
| AOR2-06 | as AOR2-04 for `ex:set-condition` | L1 | warning fires | - |
| AOR2-07 | profile with a member condition and a concept strategy, no concepts / validated / no declaration warning | L1 | profile exempt | + |
| AOR2-08 | condition with `SetMembership`, no concepts, no members / validated / one declaration warning | L1 | exemption is narrow | - |
| AOR2-09 | one exclusion inside the inclusion, one outside every inclusion / validated / one `elg:ReachableExclusionShape` warning on the condition | L1 | L13 | - |
| AOR2-10 | both concept shapes in `constraints.ttl` and the README `turtle-shapes` block / compared / isomorphic (two cases) | L3 | README mirror | + |

## One command

```bash
mise run check:ontology-catalog
```

Pass: every tool test passes, `tools/test_eligibility_examples.py` among them
(the examples task was folded into `check:ontology-catalog` on 2026-09-25). Also run `mise run check:ontology-versioning` (no unbumped
changes) and `mise run check:python-root` (unchanged 77 tests and the Phase 8
gate, which reads `interval-containment.ttl`).

## Artefacts to inspect

- The three example diffs. Each concept-matching condition carries a comment
  naming the warning that removing its concept raises.
- `hierarchical-match.ttl` is now bound to a scheme contract (sketch open
  question 2) and conforms to the Vocabulary shapes as well.
- The one-line `FILTER NOT EXISTS { $this elg:hasCondition ?member }` in both
  shape copies.
- The PATCH cascade: seven documents 0.3.0 → 0.3.1 (Eligibility spec and
  vocab, Instrument spec and vocab, Behaviour spec and vocab, the applied
  capacity execution spec), with READMEs mirrored.
  Committed at 0.3.1 in `6e36586`. AOR-5 then takes the cascade to 0.4.0
  (MINOR).

## Adversarial probe (run by the agent)

Deleting the new `FILTER` line from `constraints.ttl` failed five tests:
AOR2-01, AOR2-03, AOR2-04 (hierarchical case), AOR2-07 and AOR2-10. Restoring
it returned 11 passes.

## Deliberate non-coverage

- Examples of other layers. A repository-wide example check is a candidate
  follow-up.
- Compiled evaluation of these examples (AOR-5, AOR-6).
- `elg:candidateValue` still carries a concept in `hierarchical-match.ttl`,
  until AOR-5 introduces `elg:candidateConcept`.
