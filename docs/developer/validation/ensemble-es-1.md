<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: Ensemble ES-1, the layer

**Unit:** `ensemble` ([plan](../plans/ensemble.md)). Its status record is created with ES-0.
**Machine:** as the maintainer assigns. **Branch:** `ensemble/es-1-layer`. Commits are the maintainer's.
**Plan and test cases:** [Ensemble plan](../plans/ensemble.md) (ES-1 in detail)
**Decisions:** ADR-A130 decisions 1 to 4, 7 and 9, ADR-A01's 2026-10-18 addendum

## Invariant

Ensembles, memberships, relations and endpoints are data, every relation in one ensemble with endpoints on its members, and Ensemble imports only Instrument and Behaviour's runtime (ADR-A130).

## Test cases

The table in the plan section above. Each row's result is recorded under Results at verification.

## One command

Run from the repository root.

```bash
mise run check
```

## Artefacts to inspect

`ontology/ensemble/README.md`, `spec/ensemble.ttl`, `vocab/ensemble-vocab.ttl`, `shapes/`, the root catalogue, `tools/test_ensemble.py`, the release notes.

## Deliberate non-coverage

The Instrument hook and outside endpoints' meaning (ES-2). Composition and cycles (ES-3). Every kind's evaluation (ES-3 to ES-8).

## Handoff

Written by the building machine when the work is ready for the maintainer to commit.

## Results

Written at verification.
