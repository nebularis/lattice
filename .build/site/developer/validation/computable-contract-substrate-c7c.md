<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C7c, what terms are, and who they bind

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R. **Branch:** `ccs/c7c-terms-and-parties`. Commits are the maintainer's, and
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

Written by the building machine when the work is ready for the maintainer to commit.

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
- **Run:** the five examples and `facility-agreement.ttl` against the C7b model and the
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

Phase 2, the model, 2026-10-06:

- **Built:**
  - Instrument 0.12.0 (breaking): definitions, deemings, classification, sectionings, scopes,
    `ins:boundWithin`, `ins:boundUnder`, party resolution, with README sections §15 Constitutive
    Terms, §16 Sections and §17 Who Terms Bind (the former §15 to §19 are now §18 to §22),
    terminology entries §4.2.17 to §4.2.20, a property group in §4.3, laws I11, I12, I15 and I16
    registered and I13 restated, worked examples §21.13 to §21.17, and release notes.
    `instrument-vocab` 0.12.0 adds `ins-voc:TermClassificationContract` and `ins-voc:Award`. Shapes
    0.5.0
  - Party 0.8.0 and `party-vocab` 0.8.0 (breaking, D19): `pty:outwardShare` and `pty:inwardShare`
    replace `pty:share`, `pty:EachForOwnShare` and `pty:EachForWhole` replace `pty:SeveralOnly` and
    `pty:JointAndSeveral`, with the README, the vocabulary README and the ontology architecture
    updated
  - the cascade: Eligibility 0.10.0, `eligibility-vocab` 0.11.0, Behaviour, `behaviour-vocab` and
    `behaviour-runtime` 0.13.0, Wording and `wording-vocab` 0.6.0, Insurance Common and its vocab
    0.4.0, the capacity execution profile 0.13.0. The catalog, 15 release rows, and release notes
    where the README keeps them
  - `tools/test_constitutive_terms.py` (49 tests), added to `check:ontology-catalog`. Version pins
    in eight existing test modules moved to the new versions
- **Run:** every row below, with every tool package importing from this checkout.
- **Check first:** the deviations, in particular the removed ranges and the optional composition
  rule, which make 0.12.0 and Party 0.8.0 breaking.
- **Deviations from the plan:**
  - **Instrument 0.12.0 is breaking, not additive.** `ins:scope`, `ins:maintains` and
    `ins:condition` lose `rdfs:range elg:Condition`, since a word stands there on stated meaning
    (D12) and a reasoner would otherwise type every word a condition. `ins:qualifies` is no longer
    functional (D10). The Party cascade is breaking in any case
  - **Party's composition rule is optional** (`owl:maxCardinality 1`, was exactly 1), and a
    membership's shares are optional, so that a silent instrument (CC-D10) is representable
  - **Sections are checked as element identities.** A scope, a section, a bound term's section and an
    ending name a value that is the `fnd:hasIdentity` of a wording element (`ins:ElementIdentityShape`).
    The examples do not type identity nodes `fnd:PersistentIdentity`, and the rule is about being an
    element's identity in any case
  - **A scope cutting through a section is a warning**, reported for the drafter, not a violation.
    Only a declared or named section may be ended (`ins:EndsSectionShape`)
  - **I16 is checked on generated bound meaning.** Overlaps are found where sections are explicit,
    in `ins:boundWithin`. Checking them on the form alone, and checking that every word a term uses
    resolves in every section it applies within, needs the binder (C8, C16b). C7c checks only that a
    word in a condition slot is defined somewhere
  - **C7c-21 checks structure, not outcomes.** Which towers' credits arise on the incident is
    evaluation (C12, C13). The row checks that each tower's generated trigger reads its own
    condition and that the incident carries no placement
  - **C7c-22 is restated as "stated meaning is context-free"**: no stated node names an element
    version except through `ins:expressedIn`, nor any instrument. That is the property hash reuse
    relies on. Sharing stated nodes between instruments already follows from their owning element
    version
  - **Eligibility and Insurance Common keep no release notes**, as in earlier cascades. Their
    versions are in the release register

## Results

Run on machine R, 2026-10-06, with every tool package importing from this checkout.

| Row | Result |
|---|---|
| C7c-01 | pass: 0.12.0, Party 0.8.0, Eligibility 0.10.0, Wording 0.6.0 and Behaviour 0.13.0 imported, every new property states subject and value, the three condition slots have no range, `ins:qualifies` is not functional. Party has its new terms and no old ones, and nothing in `ontology/` or `tools/` names the old ones |
| C7c-02 | pass: the five examples conform to every layer's structural and constraint shapes. The only warning is I16's at Lot 2, naming rows S1.1 and S1.2. All 17 Instrument examples conform |
| C7c-03 | pass: the five examples are consistent (reasoning harness) |
| C7c-04 to C7c-14 | pass: each change reported at its node, with its message. A silent group conforms (C7c-11), a prevailing definition removes the warning (C7c-09) |
| C7c-15 | pass: the README generates its five files, release notes for 0.12.0 and shapes 0.5.0, the 15 release rows present |
| C7c-16 | pass: 82 diagrams in the Instrument README render under mermaid 11, with the ELK layout, in a page |
| C7c-17 | pass: 518 tests in `check:ontology-catalog`, after the version pins in eight modules moved |
| C7c-18 | pass: `check:ontology-catalog`, `check:ontology-versioning`, `check:import-guard` (0 violations), `check:python-root`, `check:mork-compilers` (114), `check:persistence` (778), `check:vocabulary` (16), `build:mtp` (lock unchanged) and `check:mtp`. The literate checks of Behaviour, Wording and Instrument pass |
| C7c-19 to C7c-22 | pass: 3.1 bound once for Lots 1 and 2 and once for Lot 3, each resolving "the Supplier" alike within itself, and a second binding of one section reported. The cap bound once over the three credits. Each tower's trigger reads its own condition. No stated node names an element version or an instrument |

15 release rows added. The tags are listed in the status record.
