<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-2.7, pools, fallback bindings and the example editions

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[AIR-2.7] …`
**Plan and test cases:** [Phase 2 plan](../plans/applied-insurance-reference-phase-2.md) (AIR-2.7 in detail)
**Decisions:** ADR-A99, ADR-A100

## Invariant

The reference cause scheme is the unscoped fallback of the peril contract, a pool scheme exists with an empty reference edition, and an example market edition, house list and pool edition resolve by LATTICE's precedence rule with no insurance logic.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root. S runs it before the handoff commit. R runs it again at verification,
after `mise run build:ontology-catalog` and `mise run build:ontology-releases`, which S cannot do.

```bash
mise exec -- python -m pytest tools/test_peril_vocabulary.py -q && mise run check:ontology-catalog && mise run check:ontology-versioning
```

## Artefacts to inspect

- The two fallback bindings in `peril-vocab.ttl`.
- `examples/bindings.ttl` and the resolution results.
- The pool citations in `examples/pools.ttl`, against their statutes.

## Deliberate non-coverage

No maintained market edition (epic §7). The US edition's bundles come in AIR-2.5.

## Handoff

Written by S in the `[AIR-2.7] Handoff` commit. S runs the checks itself, so say which ran.

- **Built:**
- **Run, with the result:**
- **Not run, and why:**
- **Versions used, if they differ from the plan's snapshot:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
