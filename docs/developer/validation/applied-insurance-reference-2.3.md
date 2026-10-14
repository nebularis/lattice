<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-2.3, peril causes N, T and E

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[AIR-2.3] …`
**Plan and test cases:** [Phase 2 plan](../plans/applied-insurance-reference-phase-2.md) (AIR-2.3 in detail, and the shared rules for AIR-2.3 and AIR-2.4)
**Decisions:** ADR-A98 (namespaces, addendum), ADR-A99

## Invariant

Every concept of peril vocabulary §5.1 to §5.3 exists once, with its code, its parent link and the characteristics the shared rules give it, and the vocabulary passes every peril shape.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root. S runs it before the handoff commit. R runs it again at verification,
after `mise run build:ontology-catalog` and `mise run build:ontology-releases`, which S cannot do.

```bash
mise run check:ontology-catalog && mise run check:ontology-versioning
```

## Artefacts to inspect

- `vocab/peril-vocab.ttl`: regions `cause-N`, `cause-T`, `cause-E`.
- `README.md`: Sources consulted, concept counts.
- Ten definitions picked at random, read against the style rules.

## Deliberate non-coverage

No links to H to L (AIR-2.4). No intensity links or thresholds (AIR-2.6). No collections (AIR-2.5).

## Handoff

Written by S in the `[AIR-2.3] Handoff` commit. S runs the checks itself, so say which ran.

- **Built:**
- **Run, with the result:**
- **Not run, and why:**
- **Versions used, if they differ from the plan's snapshot:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
