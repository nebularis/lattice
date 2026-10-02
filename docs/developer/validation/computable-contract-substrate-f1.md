<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS F1, external and natural keys

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R (Claude Code). **Branch:** `ccs/f1-keys`. Commits are the human's
**Plan and test cases:** [CCS plan](../plans/computable-contract-substrate.md) (F1 in detail)
**Decisions:** [ADR-A114](../../architecture/decisions/ADR-A114-external-and-natural-keys.md) (Proposed, accepted at the phase 0 gate), CC-D9, ADR-A51, ADR-A84, ADR-A86, ADR-A113

## Invariant

Any thing in a LATTICE graph can carry the names the world gives it, as key nodes with a scheme and a value, either locating it (`fnd:externalKey`) or identifying it (`fnd:naturalKey`). A natural key identifies one thing: checked by SHACL everywhere, merged by OWL only under `fnd:MergedOnNaturalKey`, enforced at write time by Persistence under `dal:PersistenceKeyed`. Identity stays ADR-A51's.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R, with the reasoning harness built where a row is L2.

```bash
mise run build:ontology-catalog && mise run check:ontology-versioning && mise run check:ontology-catalog && mise run check:import-guard && mise run check:persistence && mise run check:minting
```

## Artefacts to inspect

- `docs/developer/sketches/keys-impact.md`: the phase 0 analysis of Persistence, Surface and the cascade, reviewed at the gate.
- `ontology/foundation/examples/keys.ttl`, `ontology/persistence/examples/persistent-foundation-keys.ttl`, `ontology/surface/examples/keys.ttl`: written before the model.
- Foundation's spec, shapes and README section on keys. Persistence's `persistent-foundation` and its README section.
- The cascade: every re-pinned document, its release row and tag.

## Deliberate non-coverage

Normalisations outside the minting specification's three pipelines (a change to that specification). Keys on instruments, made in C6. Revising AIR-4.1's rows that name `aeo:Identifier`, done when F1 merges. Open CBAA's migration of `agr:umr`. NRS N9's Foundation change, which keeps its own window.

## Handoff

Written by the building machine when the work is ready for the human to commit.

- **Built:**
- **Not run:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
