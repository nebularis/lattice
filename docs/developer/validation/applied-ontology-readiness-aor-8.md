<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AOR-8, profile aggregation

**Unit:** [`applied-ontology-readiness`](../status/applied-ontology-readiness.md)
**Plan section:** [Phase B](../plans/applied-ontology-readiness.md#phase-b-executable-coverage)
**Decisions:** [ADR-A89](../../architecture/decisions/ADR-A89-eligibility-ir-concept-conditions-and-profile-aggregation.md) items 5 and 7, [ADR-A28](../../architecture/decisions/ADR-A28-parity-and-conformance-release-gate.md)

## Invariant

Every `elg:EligibilityDecision` record of a profile is decided by strong
Kleene logic over its conditions' outcomes, identically by SPARQL and SHACL.
SWRL derives a sound subset. An unanswered condition counts as
`Undetermined`. `DimensionConsistent` is refused.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AOR8-01 | eight records over a diagnosis and a consent condition, `AllRequired` and `AnySufficient` / SPARQL / the hand-derived Kleene table | L2 | + and - |
| AOR8-02 | `AllRequired` records / SPARQL / nothing answered and consent unanswered → `MissingCandidate`, diagnosis above exclusion → `AboveExclusion`, a diagnostic exactly when `Undetermined` | L1 | - |
| AOR8-03 | both profiles / SHACL / the same table | L2 | + |
| AOR8-04 | both profiles / condition and profile SWRL rules applied / every derived outcome agrees with SPARQL, and exactly the derivable subset is derived | L2 | + |
| AOR8-05 | `DimensionConsistent` / compiled / refused | L1 | - |
| AOR8-06 | profile plan / inspected / `exe:ProfilePlan` linking both condition plans and its operation | L1 | + |
| AOR8-07 | interval example's profile / SPARQL / `Permitted`, no diagnostic | L1 | + |
| AOR8-08 | one profile / all three backends compiled twice / isomorphic | L2 | + |
| AOR8-09 | corpus cases E1 to E4 / Phase 8 gate / SPARQL and SHACL each match every expected record | L3 | + and - |

The SWRL subset in AOR8-04 is smaller than the decided set because the consent
condition has no scheme and no exclusion, so no positive fact denies `refused`
(ADR-A24).

## One command

```bash
mise run check:python-root
```

Pass: the unittest run, then `Phase 8 conformance passed: 3 Surface parity
cases, 4 Eligibility cases (SPARQL and SHACL)`. `mise run check:mork-compilers`
reports `61 passed`.

## Artefacts to inspect

- `sparql_backend.py`: `profile_select`, `_aggregate`. Condition queries are
  now SELECT blocks that nest in the profile query.
- `shacl_backend.py`: `render_profile_selects`. SHACL requires every nested
  SELECT in a constraint to project `$this`, so the blocks carry it.
- `swrl_backend.py`: `_profile_rule`, `_compile_profile_rules`.
- `ontology/mork/spec/Executable.ttl`: `exe:impliesProfileDecision`, and the
  `exe:ProfilePlan` comment that replaced its "no backend emits this" note.
- `tools/phase8_conformance.py`: `run_eligibility_cases`.
- `test/conformance/`: E3 (hierarchical exclusion, `elg:E5`), E4
  (any-sufficient, `elg:E4`), and E1's condition now declares a required
  concept, with the declaration-warning comment.

## Adversarial probe (run by the agent)

| Mutation | Tests failed |
|---|---|
| `AnySufficient` evaluated as `AllRequired` | AOR8-01, AOR8-03 |
| unanswered conditions ignored | AOR8-01, AOR8-02, AOR8-03 |
| SWRL `AllRequired` Permitted rule checks one condition | AOR8-04 |
| E4 expected record altered | AOR8-09, through both backends |

## Found while implementing

- SHACL-SPARQL constraints may not contain `VALUES`. The hierarchical query
  now uses `FILTER (?target IN (…))`.
- rdflib's `MIN` aggregate fails when it compares two unbound values. The
  profile query uses `MAX(COALESCE(…, ''))`.

## Deliberate non-coverage

- Several questions for one condition in one record. Each is counted, and the
  result is not defined by ADR-A89.
- SWRL in the corpus gate, which needs a reasoner for interval rules (ADR-A83).
