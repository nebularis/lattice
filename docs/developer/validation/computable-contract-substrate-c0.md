<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C0, ADRs A-112 and A-113 and the A-01 and A-C2 addenda

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R (Claude Code). **Branch:** `ccs/c0-adrs`
**Plan and test cases:** [CCS plan](../plans/computable-contract-substrate.md) (C0 in detail)
**Decisions:** CC-D1, CC-D2, CC-D4, CC-D7, CC-D8 (layer order). Brief questions C0-Q1 to C0-Q3

## Invariant

Paper only. A-112 and A-113 and the two addenda are `Proposed`, decide only what CC-D1, CC-D2,
CC-D4, CC-D7 and CC-D8's layer order decided, and cite the sketch rather than restating it. No
ontology, tool, README or architecture document changes.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R. The check fails on the existing baseline of 427 broken
links, so a pass is the same count with no line naming a changed file.

```bash
mise run topology:links 2>&1 | grep -E "ADR-A(01|112|113|C2)|decisions/README|computable-contract-substrate-c0"
```

A pass prints nothing.

## Artefacts to inspect

- `docs/architecture/decisions/ADR-A112-wording-layer.md`: the Context's order (premise, then
  examples), and Decision 2's import lists.
- `ADR-A01-layer-dependency-order.md`: the addendum's order against the sketch §1 diagram.
- `ADR-A113-breaking-changes-at-major-version-zero.md`: the scope and the marking rule.
- `ADR-AC2-clean-room-authoring-procedure.md`: the addendum's two conditions.

## Deliberate non-coverage

The documentation the ADRs call for (`ontology-versioning-policy.md`, `ontology-architecture.md`,
the root README) changes after acceptance, not in C0. A-104 and A-106 are C1 and C2.

## Handoff

Written by the building machine when the work is committed.

- **Built:**
- **Not run:**
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
