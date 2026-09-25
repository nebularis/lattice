<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AOR-7, SHACL, SWRL and diagnostics for concept plans

**Unit:** [`applied-ontology-readiness`](../status/applied-ontology-readiness.md)
**Plan section:** [Phase B](../plans/applied-ontology-readiness.md#phase-b-executable-coverage)
**Decisions:** [ADR-A89](../../architecture/decisions/ADR-A89-eligibility-ir-concept-conditions-and-profile-aggregation.md) items 3, 4 and 6, [ADR-A24](../../architecture/decisions/ADR-A24-eligibility-executable-semantics-backend-strategy.md), [ADR-A28](../../architecture/decisions/ADR-A28-parity-and-conformance-release-gate.md)

## Invariant

SHACL agrees with the SPARQL reference on every concept-plan case. SWRL
derives only what SPARQL decides as `Permitted` or `Denied`, each from a
positive fact, and never `Undetermined`. Every `Undetermined` row carries a
declared diagnostic, and no other row carries one.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AOR7-01 | flat entitlement / SPARQL / no candidate → `MissingCandidate`, two → `SeveralCandidates`, decided rows none | L1 | - |
| AOR7-02 | diagnosis arm / SPARQL / above exclusion → `AboveExclusion`, unlisted → `OutsideScheme` | L1 | - |
| AOR7-03 | interval example plus an empty question / SPARQL / `MissingCandidate`, the example's question `Permitted` with none | L1 | - |
| AOR7-04 | three conditions, every member plus absent, several, outside / SPARQL / diagnostic present exactly when `Undetermined`, each one of the five declared `exe:Diagnostic` individuals | L2 | + |
| AOR7-05 | same cases / SHACL via pySHACL, read in shape order / equals SPARQL | L2 | + |
| AOR7-06 | flat entitlement, no scheme / SHACL / equals SPARQL | L2 | + |
| AOR7-07 | same cases, one candidate each / SWRL applied / equals SPARQL's `Permitted` and `Denied`, nothing for `Undetermined` | L2 | + |
| AOR7-08 | flat entitlement, no scheme / SWRL applied / `Permitted` for a required tier, `Denied` for the excluded one, nothing for a tier outside the required set | L1 | - |
| AOR7-09 | every generated concept rule / heads inspected / objects only `Permitted` or `Denied` | L1 | - |
| AOR7-10 | one plan / shapes and rules compiled twice / isomorphic | L2 | + |
| AOR7-11 | CLI on a bound contract / without then with `--at` / exit 2, then a `ConceptMatchPlan` with an `exe:admittedBy` fact | L1 | +/- |

SWRL rules are applied by `apply_rules`, which evaluates each rule body as a
conjunctive query. That is exact for rules with class and individual-property
atoms only, and it refuses any other atom.

## One command

```bash
mise run check:mork-compilers
```

Pass: `53 passed`.

## Artefacts to inspect

- `ontology/mork/spec/Executable.ttl`: `exe:Diagnostic` and its five
  individuals, `exe:admittedBy`, `exe:deniedBy`, the revised header, and the
  revised `exe:impliesDecision` scope note.
- `shacl_backend.py`: `concept_sets`, `render_concept_selects`.
- `swrl_backend.py`: `concept_facts`, `_concept_rule`.
- `sparql_backend.py`: the `?diagnostic` column, which interval queries now
  carry too.
- CLI: `compile-condition` accepts concept conditions, `--at` and `--scope`.
- `tools/mork_compilers/pyproject.toml`: a `test` extra (`pyshacl`, `pytest`),
  installed by `bootstrap:mork-compilers`.

## Adversarial probe (run by the agent)

| Mutation | Tests failed |
|---|---|
| determinacy shape not emitted | AOR7-05 |
| SWRL denies every member not permitted | AOR7-07 |
| `OutsideScheme` replaced by `AboveExclusion` | AOR7-02 |

## Known limit

SWRL cannot tell one candidate from several. A question with two candidates
derives an outcome per candidate. AOR7-07 and AOR7-08 use one candidate per
question. ADR-A89's consequences record this.

## Deliberate non-coverage

- Loading the rules into an OWL reasoner (ADR-A83 harness).
- Profile-level artefacts (AOR-8).
