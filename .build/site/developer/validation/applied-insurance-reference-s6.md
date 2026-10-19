<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: S6, spatial data patterns

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[S6] …`
**Plan and test cases:** [The substrate track plan](../plans/applied-insurance-reference-substrate.md) (S6 in detail)
**Decisions:** none: guidance only, under ADR-A-C2

## Invariant

A guidance document states how LATTICE content records places, zones and spatial computations with the constructs it already has, in domain-neutral terms, and changes no layer.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root. S runs it before the handoff commit. R runs it again at verification.

```bash
mise run topology:links
```

## Artefacts to inspect

- `docs/architecture/spatial-data-patterns.md`, read against the clean-room rule: no insurance term outside its closing line.
- The links added to `ontology-architecture.md` and the developer guide.

## Deliberate non-coverage

No layer change and no ADR.

## Handoff

Written by S in the `[S6] Handoff` commit. S runs the checks itself, so say which ran.

- **Built:**
- **Run, with the result:**
- **Not run, and why:**
- **Versions used, if they differ from the plan's snapshot:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
