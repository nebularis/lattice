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

- **Built:** `ontology/wording` (README as literate source, `spec/wording.ttl` and
  `vocab/wording-vocab.ttl` extracted from it, two examples), the major-version-zero rule in the
  versioning policy, `tools/test_wording.py` in `check:ontology-catalog`, catalogs, two release
  rows, and the layer order and Wording rows in the root README and `ontology-architecture.md`.
- **Not run:** nothing skipped. The reasoner rows ran against the built harness jar.
- **Check first:** the vocab's baseline scheme (Section, Clause, Definition, Schedule, Annex), and
  the governing variable in the trial example, which is a count of study arms, since a
  concept-valued one needs variable values (C4) to say anything.
- **Deviations from the plan:** none of substance. The root README and `ontology-architecture.md`
  show the accepted order with a note that Behaviour's move lands in C10.
- **Tags for the human:** `wording-v0.1.0`, `wording-vocab-v0.1.0`.

## Results

Verified on machine R, 2026-10-01, with the reasoning harness built.

| ID | Result |
|---|---|
| C3-01 | pass |
| C3-02 | pass, spec and vocab |
| C3-03 | pass |
| C3-04 | pass: every text in both examples, and clause 4.1's five parts |
| C3-05 | pass, both examples |
| C3-06 | pass: a self-comprising element and a two-element cycle are inconsistent |
| C3-07 | pass: Wording and Element, Text and Table, and embedded and governing variable are each inconsistent |
| C3-08 | pass, and the vocab closure conforms to Vocabulary's shapes |
| C3-09 | pass (`literate_extract --check`) |
| C3-10 | pass. `check:ontology-versioning` exits 0 and lists the two tags |
| C3-11 | pass: `6a0509c` commits the examples alone, before the README and spec |
| C3-12 | pass: `check:ontology-catalog`, 102 tests |
| C3-13 | pass: the five element types the examples use are all in the baseline scheme |

`mise run topology:links`: 427 broken links, the baseline, none in a changed file.
