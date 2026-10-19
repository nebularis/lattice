<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C0, ADRs A-112 and A-113 and the A-01 and A-C2 addenda

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R. **Branch:** `ccs/c0-adrs`
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

- **Built:** ADR-A112, ADR-A113, the addenda to ADR-A01 and ADR-A-C2, the index rows and the
  numbering sentence.
- **Not run:** nothing beyond the link and prose checks, as planned.
- **Check first:** A-113 decision 2, which creates a "Release notes" section in a layer's README
  on its first breaking change, since no layer README has one today.
- **Deviations from the plan:** C0-10's scope is wider, because C1 and C2 were done on the same
  branch at our instruction. The plan also gained the C1 and C2 briefs and the C10 row's
  wording.

## Results

Verified on machine R, 2026-10-01.

| ID | Result |
|---|---|
| C0-01 | pass |
| C0-02 | pass: premise, facility agreement, trial protocol, then the problem |
| C0-03 | pass: Wording, Behaviour and Instrument import lists match the sketch §1 diagram. No upward import |
| C0-04 | pass: the split is cited as A-106's |
| C0-05 | pass |
| C0-06 | pass: CC-D7's two conditions, measured under C0-Q2, authoring order and brand ban unchanged |
| C0-07 | pass, with A-104 and A-106 rows added by C1 and C2 |
| C0-08 | pass: no broken link names a changed file. Repository total 427, the baseline |
| C0-09 | pass: no semicolons or superlatives in new prose. The index paragraph's two semicolons predate C0 |
| C0-10 | deviation, as above: the tranche's files only, no ontology or tool change |
| C0-11 | pass |
