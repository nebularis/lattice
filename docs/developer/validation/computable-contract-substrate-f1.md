<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS F1, external and natural keys

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R (Claude Code). **Branch:** `ccs/f1-keys`. Commits are the human's
**Plan and test cases:** [CCS plan](../plans/computable-contract-substrate.md) (F1 in detail)
**Decisions:** [ADR-A114](../../architecture/decisions/ADR-A114-external-and-natural-keys.md) (Accepted 2026-10-03, at the phase 0 gate), CC-D9, ADR-A51, ADR-A84, ADR-A86, ADR-A113

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

Normalisations outside the minting specification's three pipelines (a change to that specification), including the exact pipeline of follow-up FU-F1a. The compiler deriving the natural-key constraint from `dal:PersistenceKeyed` (FU-F1b). Both are in the plan's F1 follow-ups table. Keys on instruments, made in C6. Revising AIR-4.1's rows that name `aeo:Identifier`, done when F1 merges. Open CBAA's migration of `agr:umr`. NRS N9's Foundation change, which keeps its own window.

## Open questions

- **F1-Q1. Foundation's uniqueness shape and `fnd:MergedOnNaturalKey`.** The shape reports two
  different `fnd:NaturallyKeyed` things sharing a natural key. For two members of
  `fnd:MergedOnNaturalKey` that is exactly what `owl:hasKey` merges, but SHACL does not reason, so
  it sees two IRIs and reports them. Options: (a) report them as a violation, like any other pair,
  (b) report them at `sh:Warning`, since for an ontology-only adopter the duplicate is the merge
  announced, or (c) exempt them. Recommended: (b). It keeps the merge visible and does not block
  data the adopter chose to merge. The examples show no `fnd:MergedOnNaturalKey` member, since under
  (a) a conforming example of a merge cannot exist. F1-04 constructs its pair in the test.

## Handoff

Written by the building machine when the work is ready for the human to commit.

- **Built:**
- **Not run:**
- **Check first:**
- **Deviations from the plan:** examples (phase 1). The Foundation example locates the agreement
  from drawdown requests and a transfer certificate in place of declarations and a claim, keeping to
  a neutral domain (ADR-A-C2). The Surface example has the promotion contract only, since the
  analysis found an index adds nothing (S1). Its path ends in `fnd:naturalKey`, since under
  `srf:NoEntailment` a step on `fnd:externalKey` would not reach keys asserted as natural keys.

## Results

Written on machine R at verification.
