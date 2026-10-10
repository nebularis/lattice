<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C7b, terms in time

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R. **Branch:** `ccs/c7b-terms-in-time`. Commits are the maintainer's, and the
change is merged into `main` before its release tags are created
**Plan and test cases:** [CCS plan](../plans/computable-contract-substrate.md) (C7b in detail)
**Decisions:** ADR-A104 decisions 6, 13 and 14 and its 2026-10-04 addendum, ADR-A94, ADR-A113. Laws
I3, I5 and I9. C7b-Q1, Q2, Q6 and Q7 answered 2026-10-04. C7b-Q3 to Q5 designed in the
[terms in time sketch](../sketches/terms-in-time.md), whose TQ1 to TQ7 were answered 2026-10-05.
ADR-A115 (Quantification context values), to be drafted with the examples

## Invariant

An instrument says when its relations must be performed and how long they last. An obligation may fall due within a range anchored at a named time, never at evaluation time (law I9). A recurring obligation has one occasion per period. An instrument or a term ends when a regime enters an ending state, and a surviving term goes on giving rise to occasions after that. Nothing here evaluates.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R, with the reasoning harness built where a row is L2.

```bash
mise run build:ontology-catalog && mise run check:ontology-versioning && mise run check:ontology-catalog && mise run check:import-guard
```

## Artefacts to inspect

- `ontology/instrument/examples/`: the three examples, written before the model.
- `ontology/instrument/README.md`: terms in time, with diagrams and the worked examples.
- `ontology/instrument/shapes/`: the due, recurrence, window, ending and survival shapes.
- `ontology/quantification/`: its README restored as the literate source, context values and
  unit-bearing offsets, release 0.7.0, and the re-pin cascade to its importers.
- ADR-A115 and the ADR-A104 addendum.

## Deliberate non-coverage

Evaluation of due ranges, recurrences, ending and survival (C12, C13). What is reasonable where no time is fixed, which only a finding establishes (C13). Due dates set by variables (C8). Reasonable time where no time is fixed, which this layer does not model unless the words define it (C7b-Q2). Definitions, deemings, sections, classification, party resolution and group modes (C7c). `ins:computedBy` (contract amounts, C7b-Q7). Rescission ab initio, frustration and combinations of times (sketch §5.6, §10). Business day conventions and times of day (held design question HQ-3).

## Handoff

Written by the building machine when the work is ready for the maintainer to commit.

Phase 1, examples first (ADR-A-C2), 2026-10-05:

- **Built:**
  - Quantification's README restored as its literate source: an ontology header block in §2 and an
    extraction contract in §3 naming `shapes/constraints.ttl`, which holds every Quantification
    shape (`structural.ttl` and `rules.ttl` are empty). Regenerated from the README, the spec, vocab
    and shapes are isomorphic to `HEAD`'s. The regenerated files are not committed here, because
    their text differs (licence header, a trailing space) and the versioning check rejects a changed
    file without a bump. The model phase regenerates them with 0.7.0
  - one Quantification example, `ontology/quantification/examples/context-anchor.ttl`: a
    subscription's allowance year anchored at a context value, and a grace period whose offsets
    carry units
  - four Instrument examples in `ontology/instrument/examples/`: `trial-reporting.ttl` (a due range
    from the arising, a monthly recurrence with a due range in business days from each period's
    end, quarterly test dates, an obligation with no due range), `lease-expiry.ttl` (expiry at the
    Expiry Date, a break in a window, rent due on each Quarter Day, a deposit repaid within 30 days
    of either ending), `licence-survival.ttl` (ending on the notice regime's terminated state,
    return of materials arising on termination, survival for five years and without limit), and
    `service-renewal.ttl` (an evergreen agreement renewing by an external self-transition, a
    notice window as a region of each period, and the expiry chosen by guards reading an election
    regime)
  - ADR-A115 (Quantification context values, Proposed) and the ADR-A104 addendum "terms in time"
    (Proposed), with the ADR index row
- **Run:** each example against the C7a model and the structural and constraint shapes
  of Foundation, Vocabulary, Quantification, Party, Eligibility, Wording, Behaviour and Instrument,
  without inference. `context-anchor.ttl`, `trial-reporting.ttl` and `service-renewal.ttl` conform.
  `lease-expiry.ttl` and `licence-survival.ttl` fail only where the model is to change: C7a's expiry
  shape requires `ins:after` (`ins:at` is TQ6), and C7a's arising shape does not yet admit
  `ins:OnEntry` (TQ4). `check:ontology-versioning` passes.
- **Not run:** the tool tests. `tools/test_instrument.py` and `tools/test_regimes.py` iterate over
  every example, and fail on these until the model phase: the two shapes above, and C6-11's check
  that every activity is in the baseline (six new activities, below).
- **Check first:** `service-renewal.ttl`'s design (deviations), and the ADR texts.
- **Deviations from the plan:**
  - **The evergreen notice window is a region, not `ins:window`.** "Six months before the end of the
    current period" has no anchor outside the regime: the period's end is known only from when the
    period was entered. The window is the open part of each period, a region restarted on each
    renewal, and the power is gated by it. The renewal and the expiry share the year's expiry, and
    guards reading an election regime (renewing or not) choose between them. `ins:window` is shown
    by the lease's break, which anchors at a date the wording defines.
  - **Survival is stated on the stated term only**, and read for each instrument through the bound
    term's `ins:boundFrom`, as a regime is read as stated. A bound term carries no content of its
    own in C6, and survival does not change that.
  - **Due ranges and recurrences are shared nodes**, named by both the stated and the bound
    relation, as scope conditions are. They name no party or role.
  - **Dates the wording defines are example roles** (`ex:ExpiryDate`, `ex:BreakDate`,
    `ex:FirstQuarterDay`) in a scheme bound to `qnt:ContextRoleContract`, until C8 binds wording
    variables. Instrument's baseline roles are `Arising`, `Inception`, `Ending`, `PeriodStart` and
    `PeriodEnd`.
  - **Six new activities** in the baseline: `Pay`, `Report`, `ReturnMaterials`, `Disclose`,
    `Indemnify` and `DeclineRenewal`. One new state kind, `Expired`.

Phase 2, the model, 2026-10-05:

- **Built:**
  - **Quantification 0.7.0** (additive, ADR-A115), from its README: `qnt:ContextValue` with
    `qnt:contextRole` and disjoint from the other three kinds of value, `qnt:ContextRoleContract`,
    and the unit-bearing offsets `qnt:lowerOffsetBy` and `qnt:upperOffsetBy`. Shapes 0.2.0: a
    context value's one role and space, and an anchor binding's offsets in one form. The README
    gains an eleventh design decision, a class section with two diagrams, a table of anchored
    windows, an open question for HQ-3, and release notes. At our request (2026-10-05), a
    guided tour (§5.1, thirteen steps, from value spaces to the law registers) and diagrams for
    range containment, law prerequisites and the layer's consumers: 20 diagrams, all rendered, with
    no change to the generated files
  - **the cascade**: 18 documents that import Quantification, directly or not, re-pinned in one
    pass with their versions bumped (Party, Eligibility, Wording, Behaviour configuration and
    runtime and vocab, Surface, Instrument, `applied/capacity`, and the insurance `common` and
    `peril` modules, each with its vocab). Tests that locate a current document moved to the new
    versions. Tests of release history are unchanged. Release notes added where a README has them
    (Wording, Behaviour, capacity). 21 release rows added
  - **Instrument 0.11.0**, vocab 0.11.0, shapes 0.4.0, from the README. The README gains §4.2.16
    (`ins:Survival`), a property group and glance rows for time and ending, §4.7 (the legal terms
    of time and ending), `ins:OnEntry` in §4.2.15 and §10, §13 Anchored Time and §14 Ending, the
    worked examples §18.9 to §18.12, laws I3, I5 and I9, and release notes. Sections 13 to 17 are
    renumbered 15 to 19. 85 diagrams across both READMEs and the sketch render under mermaid 11
  - `tools/test_terms_in_time.py`, rows C7b-01 to C7b-19 (30 tests). `tools/test_instrument.py` and
    `tools/test_regimes.py` assert the current versions. The ontology architecture's Quantification,
    Wording and Instrument rows are updated
- **Check first:**
  - **Context roles from several sources (held design question HQ-4).** Quantification's role
    contract resolves to one scheme in a context, and two unscoped bindings conflict (Vocabulary's
    invariant 4). Instrument binds its baseline roles, so the lease example's own date roles are
    left unbound, and the Quantification example validates only beside Quantification's model,
    not Instrument's. A deployment that uses Instrument with another layer's roles, or a wording's
    own dates, cannot bind them all to one contract yet. Recorded as HQ-4, to take up with C8
  - `ins:ofState` has a domain, `ins:OnEntry`, under the rule that gave `ins:ofPower` theirs: it has
    one subject class, and the domain lets a reasoner infer the trigger
  - `ins:dueTolledIn` is on the obligation, not the range, because ranges are shared nodes
- **Deviations from the plan:**
  - `ins:OnExpiry`'s shape now requires exactly one of `ins:after` and `ins:at`. An expiry with
    neither was already rejected, so this rejects nothing that conformed
  - the evergreen diagram draws the year's end as a choice. The data has no pseudo-state: two
    transitions on one expiry, each with a guard
  - row C7b-20 (diagrams render) is run in a browser, not in pytest

## Results

Run on machine R, 2026-10-05, with every tool package importing from this checkout.

| Row | Result |
|---|---|
| C7b-01 | pass: 0.11.0, Quantification 0.7.0 imported, every new property states subject and value, `ins:OnEntry`'s kind is a `hasValue`, `ins:ofState` alone of the new properties has a domain |
| C7b-02 | pass: the four new examples conform to every layer's structural and constraint shapes, and under pySHACL's RDFS and OWL RL inference. The Quantification example conforms beside its own model (HQ-4) |
| C7b-03 | pass: the four new examples are consistent (reasoning harness) |
| C7b-04 to C7b-09, C7b-16, C7b-18 | pass: each change reported at its node, with its message |
| C7b-10, C7b-19 | pass: bound relations name their templates' ranges and recurrences, and a termination consequence conforms with no survival |
| C7b-11 | pass: `ins:ofState` alone yields `ins:OnEntry`, `bhv:TriggerDefinition` and `bhv:DerivedTrigger` after an OWL 2 RL closure |
| C7b-12 | pass: the context roles bound to Quantification's contract, every baseline role the examples use in it, `Expired` and `ins-voc:TheInstrument` declared |
| C7b-13, C7b-15 | pass: both READMEs generate their files, release notes recorded, shapes at 0.4.0 and 0.2.0 |
| C7b-14 | pass: 383 tests across the Instrument, regime, terms in time, Wording, Behaviour, applied contract, peril and keys modules, after one C7a test's expected message moved with the expiry shape. `check:python-root`, `check:mork-compilers` (114), `check:persistence` (778), `check:vocabulary` (16), `check:ontology-catalog`, `check:ontology-versioning`, `check:import-guard`, `build:mtp` (lock unchanged) and `check:mtp` pass. The literate checks of Foundation, Wording, Behaviour, Surface, Quantification and Instrument pass |
| C7b-17 | pass: no file outside the catalog still names Quantification 0.6.0 |
| C7b-20 | pass: 85 diagrams across both READMEs and the sketch render under mermaid 11, in a page |

21 release rows added. The tags are listed in the status record.
