<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS C1, ADR-A104 Instrument terms and legal relations

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R (Claude Code). **Branch:** `ccs/c0-adrs` (tranche A on one branch)
**Plan and test cases:** [CCS plan](../plans/computable-contract-substrate.md) (C1 in detail)
**Decisions:** CC-D5, CC-D8, CC-D10, CC-D11

## Invariant

Paper only. ADR-A104 is `Proposed`, supersedes ADR-A07b on acceptance, decides only what the
sketch §5, §6, §7.3 and §7.4 decide, and records CC-D12 and the points settled in review.

## Test cases

The table in the plan section above.

## One command

As C0's. A pass prints nothing.

```bash
mise run topology:links 2>&1 | grep -E "ADR-A104|decisions/README|computable-contract-substrate-c1"
```

## Artefacts to inspect

- `docs/architecture/decisions/ADR-A104-instrument-terms-and-legal-relations.md`: Decision items
  5 and 6 (legal triggers and regimes) against the sketch §7.3, and decision 2 (ownership, CC-D12) against the sketch §5.9.

## Deliberate non-coverage

Nested states, history and concurrent regimes (C11a). The expression construct behind
`ins:computedBy` (the contract amounts work).

## Handoff

- **Built:** ADR-A104, its index row, A-07b marked superseded on acceptance.
- **Not run:** nothing beyond the link and prose checks, as planned.
- **Check first:** decision 2 and laws I17 and I18, added after review (CC-D12).
- **Deviations from the plan:** the brief was written on the tranche branch, not on `main`, at the
  human's instruction to complete tranche A in one run. Revised after review for CC-D12 and the
  settled points, and re-verified.

## Results

Verified on machine R, 2026-10-01.

| ID | Result |
|---|---|
| C1-01 | pass |
| C1-02 | pass: premise, facility agreement, trial protocol, then the problem |
| C1-03 | pass. Decision 2 states CC-D12, decision 4 CC-D10, decisions 6 to 8 CC-D8, decision 12 CC-D11, decision 13 CC-D5 |
| C1-04 | pass |
| C1-05 | pass: `Provision` and `Element` retired (decision 1), `Obligation` and `Qualifier` carried (3, 5), the cross-reference properties replaced by `expressedIn`, `boundIn`, `boundFrom`, `arisesUnder` and `qualifies`, `fulfilledBy` replaced by `fulfilledWhen` (5), R-B7 carried for `ins:Instrument` |
| C1-06 | pass: no broken link in the changed files (repository total 427, the baseline), no semicolons in new prose |
