<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C7c, what terms are, and who they bind

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R (Claude Code). **Branch:** `ccs/c7c-terms-and-parties`. Commits are the human's, and
the change is merged into `main` before its release tags are created
**Plan and test cases:** [CCS plan](../plans/computable-contract-substrate.md) (C7c in detail)
**Decisions:** ADR-A104 decisions 4, 9, 11 and 12, ADR-A102, ADR-A87, ADR-A113. Laws I11, I15 and
I16. C7c-Q1 to C7c-Q9 answered 2026-10-06. Held design questions HQ-5 (group behaviours after C9) and HQ-6 (deemings with ADR-A105) carry the follow-ups. An ADR-A104 addendum, to be drafted with the examples

## Invariant

An instrument says what its words mean and whom they bind. A definition gives a word its meaning, within the parts of the instrument it applies to. A deeming says what is taken to hold, and on what footing. A term may apply only within some sections, and a case's section is fixed by the power it was bound under (I15). Definitions of one word that overlap combine by union unless one prevails, and every overlap is reported (I16). A party that depends on the case is resolved when an occasion arises, and stays fixed (I11). A term's classification is read, never evaluated. Nothing here evaluates.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R, with the reasoning harness built where a row is L2.

```bash
mise run build:ontology-catalog && mise run check:ontology-versioning && mise run check:ontology-catalog && mise run check:import-guard
```

## Artefacts to inspect

- `ontology/instrument/examples/`: the four examples, written before the model.
- `ontology/instrument/README.md`: constitutive terms, sections and who terms bind, with diagrams
  and the worked examples.
- `ontology/instrument/shapes/`: definitions, deemings, sections, I15, I16, party resolution and
  classification.
- The ADR-A104 addendum.

## Deliberate non-coverage

Evaluation of definitions, deemings, sections and party resolution (C12, C13). Date and amount words, which need parameter bindings (C8, C7c-Q7), and HQ-4. Consent rules, and so a group's power, and the full set of group behaviours (C9, HQ-5). The closure declaration a deeming licenses, rebuttal and supersession of deemings (ADR-A105, NRS N5, HQ-6). Precedence between terms (NRS N10). Deemed receipt counted in business days (HQ-3). Amendments, incorporation and `ins:takesEffectWhen` (C9).

## Handoff

Written by the building machine when the work is ready for the human to commit.

## Results

Recorded at verification.
