<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C8b, references by identity

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R (Claude Code). **Branch:** `ccs/c8b-references-by-identity`. Commits are the human's,
and the change is merged into `main` before its release tags are created
**Plan and test cases:** [CCS plan](../plans/computable-contract-substrate.md) (C8b in detail)
**Decisions:** ADR-A104 and its 2026-10-06 addenda, ADR-A51, the Wording ADRs behind laws W1 to W7.
C8b-Q1 to C8b-Q4. Takes over insurml-alignment IMA-3.3

## Invariant

A clause's text names what it refers to the way its stated meaning does. A reference to another part of the wording, or to a variable, names a persistent identity, resolved within the wording that holds the clause, so a clause reused under another schedule or beside a revised definition needs no new version. Nothing here changes what a wording means.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R.

```bash
mise run build:ontology-catalog && mise run check:ontology-versioning && mise run check:ontology-catalog && mise run check:import-guard
```

## Artefacts to inspect

- `ontology/wording/examples/`: the reworked examples and `reused-clause.ttl`, written before the
  model.
- `ontology/instrument/examples/`: the three C8 examples, their text references by identity.
- `ontology/wording/README.md`: references by identity, resolution at each tier, display text, W8.
- `ontology/wording/shapes/`: W8 and the reference ranges.

## Deliberate non-coverage

A renderer (insurml-alignment IMA-4.1). Resolution records for policies that cannot be derived from the graph (assembly interface sketch H5). Transclusion and inline parts (IMA-3.1, IMA-3.2).

## Handoff

Written by the building machine when the work is ready for the human to commit.

## Results

Recorded at verification.
