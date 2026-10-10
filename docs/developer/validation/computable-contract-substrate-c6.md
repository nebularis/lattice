<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C6, instrument, terms and legal relations

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R. **Branch:** `ccs/c6-instrument-relations`. Commits are the maintainer's
**Plan and test cases:** [CCS plan](../plans/computable-contract-substrate.md) (C6 in detail)
**Decisions:** ADR-A104 decisions 1 to 5 and 10, CC-D10, CC-D12, ADR-A96, ADR-A102, ADR-A113.
C6-Q1 to C6-Q4 answered (2026-10-02 and 2026-10-03). C6-Q5 open

## Invariant

Instrument states what an agreement binds its parties to: an instrument expressed in one assembled wording, terms, and the five legal relations with their parties and content. Only `ins:Instrument` is a version. Every relation arises under exactly one term and belongs to it.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R, with the reasoning harness built where a row is L2.

```bash
mise run build:ontology-catalog && mise run check:ontology-versioning && mise run check:ontology-catalog && mise run check:import-guard
```

## Artefacts to inspect

- `ontology/instrument/examples/`: the four instruments, written before the model.
- `ontology/instrument/README.md`: the model, its diagrams and the worked examples.
- `ontology/instrument/shapes/`: the Core shapes, I2 and I8.

## Deliberate non-coverage

Arising, due, ending, survival and constitutive terms (C7b). Legal triggers, regimes and gating (C7a). Parameter bindings, encoding status and law I17 (C8). Amendments, consent rules and incorporation (C9). Instrument keys, built in slice F1 and used by `facility-agreement.ttl`. Evaluation, including the exception burden of law I7 (C13).

## Open questions

- **C6-Q5. A party that depends on the case.** Deferred to C7b (decided 2026-10-03): resolving a
  case-dependent party, through a definition (S58) or through the case (S20), is decided there,
  either by a path-only `elg:EvidenceBinding` or by ruling such resolution out as a way to model.
  C6 keeps the contingent occupancy and has no `ins:resolvedBy`.

## Handoff

Written by the building machine when the work is ready for the maintainer to commit.

- **Built (examples, phase 1):** the four examples of the brief in `ontology/instrument/examples/`,
  each a small wording of its own, its stated meaning owned by the wording's clauses, and the
  bound meaning of one instrument, simplified after review (the brief, "Simplified after review").
  Each conforms to Foundation's, Vocabulary's, Quantification's, Wording's and Eligibility's
  shapes, loaded with Foundation's keys example (the facility's keys use its schemes). Every bound
  relation restates its template, differing only in its parties and in the bound nodes it names.
  The activities, which the vocab's baseline scheme must hold: `ins-voc:CreateSecurity`,
  `DeclareDue`, `EndParticipation`, `Enrol`, `Repair`, `Repay`, `ReportAdverseEvent`, `Terminate`.
  `ins-voc:LocationContract` is used by `software-licence.ttl`.
- **Built (model, phase 2):**
  - `instrument` 0.9.0 (breaking): the instrument, terms in two tiers (`ins:Template`,
    `ins:expressedIn`, `ins:alsoExpressedIn`, `ins:boundIn` on terms only, `ins:boundFrom`,
    `ins:impliedBy`), the five relations under `ins:LegalRelation`, the party union
    `ins:RelationParty`, party details, content and qualifiers. The ADR-A07b terms are retired.
  - `instrument-vocab` 0.9.0: the activity contract and its baseline of eight activities, the
    location contract, `ins:InstrumentTarget`.
  - `instrument-shapes` 0.2.0 (breaking): Core shapes for I1, I2, I13 and each class's content,
    SHACL-SPARQL for supersession and I8, the optional `single-expression.ttl`. `rules.ttl`,
    `single-provision.ttl` and the projection to Party are removed.
  - The README rewritten as the literate source of all five files, with the model, the two tiers,
    a worked section per example and release notes. Technical debt TD-16 is closed for Instrument.
  - Elsewhere: the gate-4 supersession fixture and query target `ins:Instrument`, the ADR-A96 test
    moves to `ins:alsoExpressedIn`, Party's README and the architecture doc stop naming
    `ins:fulfilledBy`, and the architecture doc's Instrument rows are rewritten.
  - `tools/test_instrument.py`, C6-01 to C6-14, 41 tests, in `check:ontology-catalog`.
- **Not run:** the Java and frontend checks of `mise run check`, which C6 does not touch, and
  `check:mtp`, since MORK is unchanged.
- **Check first:** the three tags `mise run check:ontology-versioning` lists: `instrument-v0.9.0`,
  `instrument-vocab-v0.9.0`, `instrument-shapes-v0.2.0`.
- **Deviations from the plan:** examples. The licence grants no modelled right to use: a permission
  excepts a prohibition (ADR-A104), and a bare licence to use has none to except, as the example's
  header says. Clause 15.1 (notices) has no stated meaning, its effect being the occupancies' party
  details. The facility agreement records its keys (C6-Q2), and a notice locates it by its market
  reference. Instrument's README, which drifts from `instrument.ttl` today (technical debt TD-16),
  becomes the literate source when it is rewritten (step 6), closing TD-16 for Instrument.
- **Deviations from the plan (model):**
  - Law I13 ships in C6, as part of the two-tier shape (`ins:RelationTierShape`): stated relations
    name roles, bound ones occupancies and groups. The brief listed I2 only, and I13 reads only
    terms C6 builds.
  - `ins:holder` and `ins:counterparty` take `ins:LegalRelation` as their domain, and
    `ins:expressedIn` and `ins:excepts` carry no domain, rather than naming further unions: the
    class shapes check which relation carries which. Only the two unions the brief names exist.
  - C6-15 is the existing suites passing, recorded under Results, rather than a test row.

## Results

Run on machine R, 2026-10-03, against this checkout's packages.

| Check | Result |
|---|---|
| `tools/test_instrument.py` (C6-01 to C6-14, reasoner rows included) | 41 passed |
| `mise run check:ontology-catalog` (all ontology tool tests, catalog) | 347 passed, catalog consistent |
| `mise run check:ontology-versioning` | passed, 3 tags pending |
| `mise run check:import-guard` | 0 violations |
| `mise run check:python-root`, `check:mork-compilers`, `check:vocabulary`, `check:persistence` | passed (84, 114, 16, 778) |
| literate check, Instrument | 5 artefacts consistent |
| adversarial probes: I8's holder query disabled, I13's bound-party check removed | the matching C6-06 and C6-07 tests fail, as they should |
