<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C2, ADR-A106 Behaviour configuration, runtime, occasions and records

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R (Claude Code). **Branch:** `ccs/c0-adrs` (tranche A on one branch)
**Plan and test cases:** [CCS plan](../plans/computable-contract-substrate.md) (C2 in detail)
**Decisions:** CC-D8

## Invariant

Paper only. ADR-A106 is `Proposed`, amends ADR-A11 on acceptance, maps ADR-A08's tiers onto two
documents, and decides only what the sketch §7 decides.

## Test cases

The table in the plan section above.

## One command

As C0's. A pass prints nothing.

```bash
mise run topology:links 2>&1 | grep -E "ADR-A106|decisions/README|computable-contract-substrate-c2"
```

## Artefacts to inspect

- `docs/architecture/decisions/ADR-A106-behaviour-configuration-runtime-occasions-and-records.md`:
  decision 2 (A-11 amended), the tier table, and decision 6's engine settings.

## Deliberate non-coverage

Nested states, history and concurrent regimes, left to C11a, which amends A-106.

## Handoff

- **Built:** ADR-A106, its index row, A-11 marked amended on acceptance. The plan's C10 row no
  longer says "engine-setting defaults".
- **Not run:** nothing beyond the link and prose checks, as planned.
- **Check first:** decision 5's rule that runtime state belongs to persistent identities, added
  after CC-D12. Engine settings were settled in review: A-09 and A-10 stand.
- **Deviations from the plan:** the brief was written on the tranche branch, not on `main`.

## Results

Verified on machine R, 2026-10-01.

| ID | Result |
|---|---|
| C2-01 | pass |
| C2-02 | pass: premise, software licence, trial protocol, then the problem |
| C2-03 | pass: declaration in configuration, occurrence, execution and state record in runtime |
| C2-04 | pass. B2 and B6 are shortened, same meaning |
| C2-05 | pass: Wording, Behaviour and Instrument import lists agree across the three documents |
| C2-06 | pass: no broken link in the changed files, no semicolons in new prose |
