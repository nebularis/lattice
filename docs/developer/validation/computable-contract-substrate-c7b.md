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

- **Built:**
- **Not run:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
