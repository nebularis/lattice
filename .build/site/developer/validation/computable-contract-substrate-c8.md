<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C8, parameter bindings

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R. **Branch:** `ccs/c8-parameter-bindings`. Commits are the maintainer's, and
the change is merged into `main` before its release tags are created
**Plan and test cases:** [CCS plan](../plans/computable-contract-substrate.md) (C8 in detail)
**Decisions:** ADR-A104 decision 13 and its 2026-10-06 addendum, ADR-A92, ADR-A51, ADR-A85,
ADR-A115. Laws I13 and I17. C8-Q1 to C8-Q6, with HQ-4 decided after the formal-methods epic's
track C2. An ADR-A104 addendum, to be drafted with the examples

## Invariant

An instrument stores only what differs from its form, and its values are among that. Stated meaning names roles, words and variables. Bound meaning names occupancies, meanings and values, and is generated from the form and the instance. An instrument version binds exactly the stated meaning of the elements its wording includes (I17). Nothing here evaluates.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R, with the reasoning harness built where a row is L2.

```bash
mise run build:ontology-catalog && mise run check:ontology-versioning && mise run check:ontology-catalog && mise run check:import-guard
```

## Artefacts to inspect

- `ontology/instrument/examples/`: the new and reworked examples, written before the model.
- `ontology/instrument/README.md`: values in stated meaning, schedules, value words, encoding
  status, generation, law I17.
- `ontology/instrument/shapes/`: variables and words in bound meaning, encoding status, I17, and the
  form's overlap and word resolution checks.
- `tools/instrument_binder.py`: the reference binder.
- The ADR-A104 addendum.

## Deliberate non-coverage

Evaluation (C12, C13). Computed amounts, bases, aggregation and `ins:computedBy` (contract amounts). Sharing bound meaning across instruments, its cache and subgraph (C16b). Amendments, consent rules and incorporation (C9).

## Handoff

Written by the building machine when the work is ready for the maintainer to commit.

Phase 1, examples first (ADR-A-C2), 2026-10-06:

- **Built:**
  - `facility-parameters.ttl` (new): a facility form whose due length, leverage ceiling and
    Commitment are placeholders taking their values from variables, the Commitment as an amount
    word, and a ceiling taking its value from that word. The facility's values, and its generated
    bound meaning with the path from each slot to its placeholder generated anew
  - `framework-lots.ttl` (reworked): Schedule 1's rows declare variables, each row's definition means
    a placeholder role taking its value from its variable, and the framework records Ash Ltd, the Lot
    3 group and Dogwood Ltd as values (C8-Q2). The generated part is unchanged
  - `services-schedule.ttl` (new): a multi-valued territory variable, the concept word "Territory"
    meaning its values and standing as a required concept in the duty's scope, a note for
    information marked `ins-voc:NoMeaning`, and a data clause with neither meaning nor mark, not yet
    assessed
  - the ADR-A104 addendum "values in stated meaning" (Proposed), restating decision 13
  - the brief's resolution table corrected to law W5 (below)
- **Run:** the three examples against the C7c model and every layer's structural and
  constraint shapes, without inference. All conform. The framework's only result is its intended
  overlap warning at Lot 2 (I16). `tools/test_constitutive_terms.py` and `tools/test_instrument.py`
  pass (120). `check:ontology-versioning` passes.
- **Not run:** the other tool tests, and the reasoner.
- **Decided 2026-10-06:** a placeholder may take its value from a value word, with
  thorough cycle checking, clear reports, and the rule stated wherever it may come up. A concept word
  may stand in an Eligibility concept slot, with shapes governing it. Recorded in the plan's C8
  section, with rows C8-18 to C8-21.
- **Deviations from the plan:**
  - **Variables are never included** (law W5). The brief's table said a placeholder resolves to the
    included version of its variable. It resolves to the value whose variable version has that
    identity. Corrected in the plan
  - **A placeholder may take its value from an amount word**, not only from a variable: 7.2's ceiling
    is "the Commitment". Without it, an amount word could be defined but not used inside a condition,
    since Quantification's slots take quantities, never words
  - **A concept word stands in an Eligibility condition's concept slot.** "Territory" is a
    `skos:Concept`, so `elg:requiredConcept ex:Territory` breaks no range, and binding replaces the
    word by its meaning, the customer's territories. D12 named only Instrument's condition slots.
    This extends it to concept slots anywhere, with no change below Instrument
  - **A party placeholder is a role,** the stated kind of a party slot (law I13), so stated meaning
    still names no occupancy
  - **No margin.** An interest rate is a qualifier's amount, which waits for contract amounts
  - **The lease's date words are not written**, waiting for HQ-4 and track C2
  - **Generation copies a path.** A placeholder inside a condition makes the binder generate the
    condition, its range set, range, bound and quantity anew for the instance: five nodes per
    ceiling. The rest stays the form's (D5)

Phase 2, the model, 2026-10-06:

- **Built:**
  - Instrument 0.13.0 (additive): `ins:valueFrom` and `ins:encodingStatus`, a new README section
    §18 Values and Generation (placeholders, resolution tier by tier, schedules, value words and
    cycles, which text is expected to mean something, generation, law I17), terminology §4.2.21,
    the properties table and group, §15.1 on amount words and concept words in Eligibility's
    concept slots, worked examples §22.18 and §22.19, and release notes. The former §18 to §22 are
    now §19 to §23. `instrument-vocab` 0.13.0 adds `ins-voc:EncodingStatuses` with `ins-voc:NoMeaning`
  - shapes 0.6.0 (breaking): `ins:ValueFromShape`, `ins:EncodingStatusShape`, `ins:WordCycleShape`,
    `ins:VariableCycleShape`, `ins:WordInConceptSlotShape`, `ins:WordMeaningSuitsSlotShape`,
    `ins:BoundNamesValuesShape`, law I17 (`ins:BoundFromIncludedShape`, `ins:StatedMeaningBoundShape`,
    `ins:CoverageShape` as a warning), and C7c's open checks on the form
    (`ins:FormDefinitionOverlapShape` as a warning, `ins:FormWordResolvedShape`)
  - the reference binder, `tools/instrument_binder.py`, which regenerates the generated part of all
    seven C7c and C8 examples, isomorphic up to the names of generated nodes, and reports unresolved
    words, variables with no value, overlaps and cycles with every hop
  - the cycle rule documented in the Instrument README (§15.1, §18.4, §18.6, §22.18), Wording's
    README beside `wrd:populatedFrom`, Quantification's beside `qnt:Quantity`, Eligibility's beside
    its concept slots, `tools/README.md` and the ADR-A104 addendum
  - `tools/test_parameter_bindings.py` (42 tests), added to `check:ontology-catalog`. Version pins and
    C7c's warning filters moved in four earlier modules
- **Run:** every row below.
- **Check first:** the deviations.
- **Deviations from the plan:**
  - **Five older examples gained bound terms.** Law I17 found that the C7a and C7b examples left
    terms holding only a regime unbound: `facility-cure-period.ttl` (22.1, 22.2), `lease-expiry.ttl`
    (2.1), `service-dispute.ttl` (20.1), `service-renewal.ttl` (2.1) and `supply-suspension.ttl`
    (14.1). Every stated term is now bound, a regime being read as stated. This is why shapes 0.6.0
    are breaking
  - **Three truthful coverage warnings remain.** The call-offs' order form (incorporation, C9), the
    software licence's notices clause, whose meaning is only notice addresses, and the services
    data clause, which is the example's point. None is marked `NoMeaning`, since each does mean
    something not yet modelled
  - **The form's cycle check is conservative.** It reports a loop among definitions even where they
    apply in different sections, since the form alone cannot rule out a section where they meet.
    The binder checks each section exactly, and binds the sections a loop does not reach
  - **The form's overlap and word checks read sections one level deep.** A definition applying within
    a parent section is found for its nested sections, but two definitions in a parent and a child
    are not reported as overlapping on the form. The binder, which resolves each section, reports
    them
  - **Lower layers name no Instrument term.** The notes in Wording's, Quantification's and
    Eligibility's READMEs describe the rule as a layer above's, without `ins:` terms, which
    Wording's own test forbids and the layering requires
  - **A placeholder's default** is honoured by the binder but shown in no example

## Results

Run on machine R, 2026-10-06, with every tool package importing from this checkout.

| Row | Result |
|---|---|
| C8-01 | pass: 0.13.0, imports unchanged, both new properties state subject and value, the encoding statuses hold `NoMeaning` alone |
| C8-02 | pass: the three examples, and all 19 Instrument examples, have no violation under every layer's shapes. Warnings: the framework's overlap (generated and form) and three coverage warnings |
| C8-03 | pass: the three examples are consistent (reasoning harness) |
| C8-04 to C8-09 | pass: each change reported at its node, with its message. A prevailing definition removes the form's warning, and a marked leaf the coverage warning |
| C8-10 | pass: the binder's output is isomorphic to the expected part of all seven C7c and C8 examples, and the C8 examples with the binder's output conform |
| C8-11 to C8-13 | pass: a missing value reported, Schedule 1's values reaching each lot with Lots 1 and 2 sharing 3.1, the same IRIs on every run |
| C8-14 | pass: the README generates its five files, release notes for 0.13.0 and shapes 0.6.0, three release rows |
| C8-15 | pass: 84 diagrams in the Instrument README render under mermaid 11, with the ELK layout, in a page |
| C8-16 | pass: 566 tests in `check:ontology-catalog` |
| C8-17 | pass: `check:ontology-versioning`, `check:import-guard` (0 violations), `check:python-root`, `check:mork-compilers` (114), `check:vocabulary` (16), `check:persistence` (778), `build:mtp` (lock unchanged) and `check:mtp`. The literate checks of Wording, Quantification and Instrument pass |
| C8-18 | pass: a word taking its value from itself, a loop through two words, and a loop through two variables are each a violation on the form, and the binder reports every hop in order with its clause |
| C8-19 | pass: a loop closing in Lot 2 only is reported for Lot 2, and Lot 1 binds |
| C8-20 | pass: a word also in its condition's scheme, and a word meaning a condition in a concept slot, each reported |
| C8-21 | pass: the cycle rule stated in all six documents |

Three release rows added. The tags are listed in the status record.
