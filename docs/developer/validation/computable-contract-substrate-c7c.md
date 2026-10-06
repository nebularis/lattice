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

Phase 1, examples first (ADR-A-C2), 2026-10-06, reworked under decisions D1 to D22 of the plan's
C7c section:

- **Built:**
  - five Instrument examples in `ontology/instrument/examples/`, each in three parts: the form
    (wording and stated meaning, shared and matched on its hash), the instance (only what differs
    from the form, D1), and the generated bound meaning, headed as expected output, not stored (D4):
    - `framework-lots.ttl`: a sectioning clause declaring four lots, award powers placed by
      containment, and call-offs bound under lots 2 and 3 (I15). "The Supplier" defined per lot,
      with an overlap at lot 2 meaning the same party (I16). Lot 3's suppliers each for the whole,
      bearing it equally between themselves, from Party's new terms. Clause 3.1 scoped to every lot
      except lot 4 and bound once for lots 1 and 2, which resolve it alike (D5). Lot 4's withdrawal
      ending its terms for its call-offs
    - `service-towers.ttl` (new): three towers, one with a nested section, each defining "Service
      Failure". A general credit clause split per tower, a cap across towers bound once (D10), a
      clause bound once because its words are the same everywhere, and an incident that is a
      Service Failure in two towers, placed in neither (D9)
    - `facility-definitions.ttl`: an unsectioned facility, one section (D7). A condition word and a
      party word with its acting rule (D12), the Obligors each for the whole, an interpretation
      clause, and a conclusive deemed receipt
    - `trial-definitions.ttl` and `supply-classification.ttl`: as before, restructured into the
      three parts
  - `facility-agreement.ttl` moved to Party's new terms: `pty:EachForOwnShare` and
    `pty:outwardShare` for lenders owed severally (D19)
  - the ADR-A104 addendum "what terms are, and who they bind" (Proposed), recording D1 to D22
  - in the plan: decisions D1 to D22, the reworked examples, shapes and tests (C7c-19 to C7c-22),
    slice C16b (required before the epic closes), and HQ-7. TD-19 in the technical debt register
- **Run by the agent:** the five examples and `facility-agreement.ttl` against the C7b model and the
  structural and constraint shapes of every layer, without inference. `trial-definitions.ttl`,
  `supply-classification.ttl` and `facility-agreement.ttl` conform. Three fail only where the
  model is to change:
  - `framework-lots.ttl`: C7b's ending shape admits only `ins-voc:TheInstrument` or stated terms
    (D11)
  - `service-towers.ttl`: a qualifier qualifies exactly one node, and the cap qualifies each tower's
    bound credit (D10). A stated condition trigger names a word, which the trigger shape refuses
    (D12)
  - `facility-definitions.ttl`: the same trigger shape, on the word "Material Adverse Effect" (D12)

  `check:ontology-versioning` passes. The new terms (Instrument's and Party's) are undeclared until
  the model phase, which no shape run without inference reports.
- **Not run:** the tool tests, which iterate over every example and fail on these until the model
  phase: the two shapes above, and C6-11's check that every activity is in the baseline
  (`ins-voc:Award`). The reasoner (C7c-03).
- **Check first:** the generated bound meaning in
  `framework-lots.ttl` and `service-towers.ttl`, which is what a binder must produce.
- **Deviations from the plan:**
  - **A condition word is a plain concept, accepted where a condition is expected** (D12, agreed
    2026-10-06). Stated meaning names words, bound meaning names meanings. A condition slot on
    stated meaning may take a defined word, as a thunk binding forces into the condition the
    applicable definition means. Authors write no wrapper condition. Generated triggers read each
    section's meaning
  - **The resolution signature is what words resolve to, not which definitions said so** (D5,
    sharpened). Lots 1 and 2 have different definitions of "the Supplier" (S1.1, and S1.1 with
    S1.2) but both resolve to Ash Ltd, so clause 3.1 is bound once for both
  - **Generated nodes have deterministic identities** (D5). A call-off stores `ins:boundUnder` a
    generated power, which must keep its IRI when regenerated
  - **A bound qualifier may qualify several bound relations** (D10). `ins:qualifies` is functional
    today
  - **The actors a schedule names are wording values.** Until C8's parameter bindings, the
    examples show them only in the generated definitions, with no stored record of which
    occupancy a row names
  - **One new activity, `ins-voc:Award`.** Withdrawing a lot uses `ins-voc:Terminate`
  - **Older examples keep stored bound meaning.** The C6 to C7b examples are not split into form,
    instance and generated parts. C16b retrofits them, or the README states the convention

## Results

Recorded at verification.
