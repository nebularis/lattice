<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: formal methods C4, a design model of ADR-A130 (Ensemble)

**Unit:** [`formal-methods-track-c`](../status/formal-methods-track-c.md)
**Machine:** R. **Branch:** `fm/c4-ensemble-model`. Commits are the maintainer's.
**Plan and test cases:** [track C plan](../plans/formal-methods-track-c.md) (C4 in detail)
**Decisions:** ADR-A130 decisions 3, 4, 5 and 10, ADR-A131 decisions 5 and 6

## Invariant

ADR-A130's design admits every motivating case (a guarantee on default, ranking, mutual
cross-default, an excess on exhaustion, a shared aggregate, two insurers each writing a primary and an
excess in one contract), refuses a cycle that remains over parts and positions, gives one outcome
whatever valid order a host chooses, and signs shares that sum to the order, checked over generated
instances up to stated scopes. Where it leaves a case undefined, a finding probe shows it before the
ADR is accepted.

## Test cases

The table in the plan section above. Each row's result is recorded under Results.

## One command

From the repository root on machine R, with `ALLOY_JAR` set to Alloy Analyzer 6.2.0.

```bash
mise exec -- java -jar "$ALLOY_JAR" exec tools/models/ensemble-composition/Ensemble.als
```

## Artefacts to inspect

- `tools/models/ensemble-composition/Ensemble.als`
- `tools/models/ensemble-composition/README.md`: every result, each instance drawn and explained,
  the Alloy version and the JAR's SHA-256
- `tools/models/ensemble-composition/Ensemble/receipt.json`, archived
- the findings C4-F1 to F4, each with the question it raises

## Deliberate non-coverage

Ledger's arithmetic and rounding (C5). Admitted cycles (C4c, with ES-8). The locality lemma and the
composition law's proof (E4b). Evaluating real terms (B4b, CCS C12).

## Handoff

Written by the building machine when the work is ready for the maintainer to commit.

## Results

Written at verification.
