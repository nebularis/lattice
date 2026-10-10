<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C9b1, the legal acts tier

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R (Claude Code, a sub-agent). **Branch:** `ccs/c9b1-legal-acts`, in its own worktree,
merged into `ccs/c9b-groundwork` after C9b0 and C9b2 by the coordinating agent. Examples first
(ADR-A-C2). The version bumps and re-pins are their own commit, so the merge can retake each version
at the strongest level any of the three slices needs
**Plan:** [CCS plan](../plans/computable-contract-substrate.md), C9b1 in detail
**Decisions:** the [consent sketch](../sketches/consent-and-group-powers.md) §2.1, §2.6, §3, §4.3 and
§6, ADR-A104, ADR-A106, ADR-A113, ADR-A120. C9b1-Q1 (a) and C9b1-Q2 (a), answered 2026-10-09, and
the items the plan lists as decided by precedent

## Invariant

What the parties did, such as a proposal, a declaration, an exercise or a notice with legal effect, is
an Instrument fact in its own document, `instrument-acts`, written by any application and evaluated,
never stated, for its effect. What the evaluator concluded about an act is a Behaviour finding. A
consumer that only states meaning never imports an act, and the acts document never imports
Behaviour's runtime (ADR-A104 and ADR-A106, their 2026-10-09 addenda, ADR-A120, TD-32).

## Test cases

The table has 15 rows in two parts, the acts tier (C9b1-01 to C9b1-11) and Behaviour's change
(C9b1-12 to C9b1-14), committed separately. Row 15 covers both.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| C9b1-01 | the acts document / parsed / Instrument's version, `ins:LegalAct ⊑ prov:Activity, fnd:TemporallyScoped, fnd:Evidenced`, every act class and property with its utility, each property stating its subject and value, `ins:Assent` moved from the main document without "consent to a power" | L1 | + |
| C9b1-02 | the acts document / its imports and terms / imports only Instrument's main document at the same version, names no `behaviour-runtime` IRI and no runtime term, and the main document never names it (the per-document check for TD-32) | L3 | + |
| C9b1-03 | the reinsurance and facility examples, and C9a's three examples with the acts document loaded / every layer's shapes / no violation | L1 | + |
| C9b1-04 | each act / its shapes, at zero and at too many: a proposal's matter and proposer, a consent's or objection's proposal, a withdrawal's declaration, an act's party, an exercise's bound power (also a stated one), a second case, an act's time, its evidence / reported | L1 | − |
| C9b1-05 | a node that is not an act carrying `ins:proposes`, `ins:directedAt`, `ins:withdraws`, `ins:exercises`, `ins:forCase` or `ins:pursuantTo` / shapes / reported | L1 | − |
| C9b1-06 | the facility's two requests / read / the first proposes C9a's amendment, made in February while the amendment takes effect in January, and `ins:Amendment` is no subclass of `ins:Proposal` (C9b1-Q1). The second has three lenders' consents and objection and two withdrawals | L1 | + |
| C9b1-07 | the settlement under the policy made pursuant to the approval under the reinsurance / shapes / conforms across instruments. With the approval moved after the settlement, reported, and at the same moment, conforms | L1 | + − |
| C9b1-08 | the approval made by the reinsured instead of the reinsurer / shapes / reported. Made by a later version of the reinsurer's occupancy / conforms | L1 | − + |
| C9b1-09 | the indemnity's scope, an evidence path from the claim through `ins:forCase`, `ins:pursuantTo`, `ins:exercises` and `ins:activity` / compiled by MORK's SPARQL backend and run / claim 1, settled pursuant to an approval, Permitted. Claim 2, settled with none, Undetermined (deliberate non-coverage, HQ-6). Claim 1 without its reliance, Undetermined | L4 | + − |
| C9b1-10 | `ins:OnExercise` / its restriction, every example's exercise triggers, and a trigger given `bhv:ExternalStimulus` / `bhv:DerivedTrigger` throughout, and the external kind reported | L1 | + − |
| C9b1-11 | `ins:impliedBy` and the reinsurance's implied term / read / the utility names a judgment, the term and its relation name the judgment, the relation is a prohibition on refusing (`ins-voc:Refuse`) whose obligor is the power's holder and whose scope is a refusal found arbitrary, with no implied obligation to approve (C9b1-Q4), and README §1.1 no longer calls a runtime document upstream | L1 | + |
| C9b1-12 | Behaviour's runtime document / parsed / `bhv:exercised` has no range and names the exercise act, the exercise record is a finding, `bhv:actor` is deprecated on it, and no Instrument term is named (law B7) | L1 | + |
| C9b1-13 | an acceptance record / Behaviour's shapes / `owl:deprecated`, and one warning, no violation, naming C16c (C9b1-Q2) | L1 | − |
| C9b1-14 | `licence-suspension.ttl` and the three notice examples / read and validated / no acceptance record, no actor on an exercise record, conforms. Each notice act record carries the annotation | L1 | + |
| C9b1-15 | the earlier slices' tests, C9a's among them, the version and catalog checks, the import guard, `build:mtp`, `check:mtp`, the literate checks / pass. Release notes and register rows for Instrument 0.16.0 and Behaviour 0.14.0 | L1 | + |

## One command

Run from the repository root on machine R.

```bash
mise run build:ontology-catalog && mise run check:ontology-versioning && mise run check:ontology-catalog && mise run check:import-guard
```

`check:ontology-catalog` runs `tools/test_legal_acts.py` (rows 01 to 15) with every earlier slice's
module.

## Artefacts to inspect

- `ontology/instrument/examples/reinsurance-claims-cooperation.ttl` and `facility-requests.ttl`,
  written before the model
- `ontology/instrument/README.md` §6.4 (the acts tier), §10 (an exercise trigger is derived), §21's
  C9b1 paragraph, §22.23 and §22.24, and `spec/instrument-acts.ttl`, generated from §6.4
- `ontology/behaviour/README.md` §5.2 (facts and findings) and §8, and `examples/licence-suspension.ttl`
- the ADR-A104 and ADR-A106 addenda of 2026-10-09, accepted by the human 2026-10-10

## Deliberate non-coverage

- A settlement with no approval is Undetermined, not Denied: a condition precedent needs a closure
  over the absence of an approval (HQ-6, ADR-A105)
- Precedence on an evidence path. The path reads that an approval exists. That it was by the holder
  and came first is the acts' shapes', not the path's (C9b3)
- Who may act for a power held by a group, and whether consents qualify (C9b4). The holder check runs
  only where the holder is a role occupancy
- Whether a withdrawal counts, and whether a withdrawal must come after what it withdraws and from the
  same party: the instrument's rule or a deployment's profile, with no substrate default
- Cross-instrument constraints on `ins:pursuantTo` and on arising, unshaped until a case needs one
  (C9c may revisit)
- An exercise's effect (law I10) and the derived stimulus for `ins:OnExercise` (C12)
- The import guard's blind spot for Behaviour's runtime (TD-32), covered here by C9b1-02 only for the
  acts document
- Five Behaviour examples (garden-leave, run-off, standstill, occasion-refinement, force-majeure)
  still name a power and an actor on their fourteen exercise records. They read as before, and move
  to exercise acts in C16c, with the removal of deprecated terms (C9b1-Q5)
- Whether a refusal was arbitrary. The implied prohibition's scope requires a concept that only a
  determination supplies, and no evidence path reads it here

## Handoff

Written by the building machine.

- **Built:** in five commits. Examples first, then the acts tier (Instrument), then Behaviour's
  records as findings, then the version bumps, re-pins, catalog and release register, then this
  pack.
- **Run by the agent:** every check under Results, and a mutation probe (Results, last paragraph).
- **Check first:** the deviations, then §6.4 of the Instrument README.
- **Deviations from the plan:**
  - **Two properties the brief does not name.** Consents, objections, withdrawals and exercises need a
    party, and consents and objections a proposal. `ins:actBy` names the party of any act, with
    `ins:assentBy` and `ins:proposedBy` as sub-properties, and `ins:directedAt` the proposal a
    consent or an objection answers. Both were the least committal reading of the sketch's "directed
    at" and of "the act names its party", and are open to renaming
  - **`ins:forCase` is at most one, not required.** The plan says every act names its case, but an
    assent or a proposal to amend concerns a version and has none. Requiring it would also have
    broken C9a's examples once the acts document is loaded
  - **The act shapes name each act class, not `ins:LegalAct`**, so they select the graph the engine
    reads without the acts document's subclass axioms (README §12.3), and the earlier slices'
    conformance tests, which load only the main document, still apply them
  - **C9a's term test reads both documents.** `test_c9a_01_spec_terms` checked that `ins:Assent`,
    `ins:assentBy` and `ins:assentTo` were in the main document, which the decided move contradicts.
    It now reads the main and acts documents together and still asserts every term, so it is not
    weakened. Its version pin moved with the bump, as the skill's re-pin step requires. Every other
    C9a test is unchanged
  - **C7a's trigger-kind tests moved** with the decided change of `ins:OnExercise` to a derived
    trigger: `FIXED_KIND`, one C7a-05 case and C7a-18 now expect `bhv:DerivedTrigger`. Not weakened:
    each still checks the one fixed kind
  - **`bhv:actor` on an exercise record is deprecated in its utility, with no warning shape.** The
    brief gives a warning shape to `bhv:AcceptanceRecord` only, and a warning on `bhv:actor` would
    fire on fourteen records in five earlier examples
  - **New activities** `ins-voc:Settle`, `ins-voc:Approve` and `ins-voc:Refuse` in
    `instrument-vocab`, for the reinsurance example
  - **Assent's disjointness with `fnd:Version`** is now entailed through `ins:LegalAct`, not stated on
    `ins:Assent`
  - **Pack name.** The plan names it `ccs-c9b1.md`. This file follows the brief and C9a's name
- **Answers after the first handoff (the human, 2026-10-09):**
  - **C9b1-Q3:** `ins:actBy` and `ins:directedAt` keep their names. `ins:actBy` stays
    non-functional, since an act by agreement or a joint notice has several parties, and
    `ins:assentBy` stays functional, as built
  - **C9b1-Q4:** the reinsurance's implied term is a prohibition on refusing approval, whose scope is
    a refusal found to be arbitrary, `ins:impliedBy` the judgment. The reinsurer may refuse for proper
    reasons (*Gan v Tai Ping (No 2)*). The earlier obligation to approve is removed, and
    `ins-voc:Refuse` added
  - **C9b1-Q5:** the five earlier Behaviour examples move to exercise acts in C16c
- **Pre-existing failure, not this slice's:** `test_c6_10_no_retired_term_outside_history` fails on
  retired `ins:` terms in `ontology/examples/insure-o/` (commit 89248158), which the branch point
  already tracks (`git grep` at `080a8af8` finds them). It is reported, not fixed

## Results

Run by the agent on 2026-10-09, with `tools/persistence/src`, `packages/minting/python/src` and
`tools/surface/src` first on `PYTHONPATH`, since the editable installs point at another clone.

| Row | Result | Evidence |
|---|---|---|
| C9b1-01 | pass | `test_c9b1_01_the_acts_document` |
| C9b1-02 | pass | `test_c9b1_02_the_acts_document_imports_no_behaviour_runtime` |
| C9b1-03 | pass | `test_c9b1_03_examples_conform` (two), `test_c9b1_03_c9a_examples_conform_with_the_acts_document` (three), and the earlier slices' conformance tests over every Instrument example |
| C9b1-04 | pass | `test_c9b1_04_act_shapes_report` (17 cases) |
| C9b1-05 | pass | `test_c9b1_05_subject_shapes_report` (6 cases) |
| C9b1-06 | pass | `test_c9b1_06_a_proposal_is_made_when_its_amendment_is_not` |
| C9b1-07 | pass | `test_c9b1_07_pursuant_to_across_instruments`, `test_c9b1_07_an_approval_after_the_settlement_is_reported` |
| C9b1-08 | pass | `test_c9b1_08_an_approval_by_another_party_is_reported` |
| C9b1-09 | pass | `test_c9b1_09_settled_with_approval_is_permitted`, `test_c9b1_09_without_the_settlements_reliance_the_claim_is_undetermined` |
| C9b1-10 | pass | `test_c9b1_10_on_exercise_is_a_derived_trigger`, and C7a's moved cases |
| C9b1-11 | pass | `test_c9b1_11_a_term_implied_by_a_judgment` |
| C9b1-12 | pass | `test_c9b1_12_an_exercise_record_is_a_finding_about_an_exercise` |
| C9b1-13 | pass | `test_c9b1_13_an_acceptance_record_is_deprecated_with_a_warning` |
| C9b1-14 | pass | `test_c9b1_14_licence_suspension_keeps_no_acceptance`, and `test_behaviour_records.py`'s example conformance |
| C9b1-15 | pass, with one pre-existing failure | `test_c9b1_15_release_notes_and_versions`. `check:ontology-catalog`: 595 passed, 69 skipped, 1 failed, `test_c6_10_no_retired_term_outside_history`, pre-existing (Handoff). `python tools/ontology_catalog.py check` consistent. `check:ontology-versioning`, `check:import-guard`, `build:mtp` (no change to `pins.lock.json`), `check:mtp`, `check:python-root`, `check:vocabulary` (16), `check:mork-compilers` (107 passed, 7 skipped), `check:persistence` (778 on a second run. The first failed `test_export_recipes_writes_each_recipe_and_refuses_a_tampered_one`, which fails about two runs in five on its own, since it tampers the first of an unordered set of recipes), the Instrument and Behaviour literate checks, `check:deny-terms` |

`tools/test_legal_acts.py` has 42 tests. The reasoner rows of earlier slices skip, since the ADR-A83
harness jar is not built here.

**Mutation probe.** With `?relied fnd:hasTemporalScope/fnd:validFrom ?later` broken to `validTo` in
`ins:PursuantPrecedesShape`, and `?power ins:holder ?holder` broken to `ins:obligor` in
`ins:ExerciseByHolderShape`, C9b1-07 and C9b1-08 fail. Restored, they pass.

The README's new diagrams, in §6.4 and §22.23, were not rendered in a browser.
