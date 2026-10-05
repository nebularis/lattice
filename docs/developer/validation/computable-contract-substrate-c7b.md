<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C7b, terms in time

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R (Claude Code). **Branch:** `ccs/c7b-terms-in-time`. Commits are the human's, and the
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

Written by the building machine when the work is ready for the human to commit.

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
- **Run by the agent:** each example against the C7a model and the structural and constraint shapes
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

## Results

Written on machine R at verification.
