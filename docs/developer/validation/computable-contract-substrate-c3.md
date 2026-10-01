<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C3, the Wording layer's spec and vocab

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R (Claude Code). **Branch:** `ccs/c3-wording-spec`
**Plan and test cases:** [CCS plan](../plans/computable-contract-substrate.md) (C3 in detail)
**Decisions:** ADR-A112, ADR-A113, ADR-A-C2 and its addendum, CC-D6, CC-D11. C3-Q1, C3-Q2 decided 2026-10-01

## Invariant

`ontology/wording` imports exactly Foundation, Vocabulary, Quantification and Eligibility, names
no higher layer's term, and holds structure, text parts and variables. Nothing imports it, so no
other version moves.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R, with the reasoning harness built
(`mise run bootstrap:reasoning-testkit`), so the L2 rows do not skip.

```bash
mise run build:ontology-catalog && mise run check:ontology-versioning && mise run check:ontology-catalog
```

## Artefacts to inspect

- `ontology/wording/spec/wording.ttl`: the part-whole properties' characteristics, and the text
  part properties.
- `ontology/wording/examples/facility-agreement.ttl`: clause 4.1's five parts.
- `ontology/wording/README.md`: the examples come before the model prose.
- `docs/architecture/ontology-versioning-policy.md`: the major-version-zero rule.

## Deliberate non-coverage

Tables' rows and columns, assembly and variable values (C4). Amendments, shapes for W1 to W7 and
the how-to (C5). The LMA WIM profile (applied insurance).

## Handoff

Written by the building machine when the work is committed.

- **Built:**
- **Not run:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
