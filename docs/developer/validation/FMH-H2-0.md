<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-H2.0, ADR-A123 drafted

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice H2.0 of the
[typed IR sketch §7](../../developer/sketches/formal-methods-track-h-typed-ir.md#7-slices).
**Decisions needing confirmation:** none. **A123 accepted by the maintainer on 2026-10-10**, with decision 5 corrected
by the H2.1 review before acceptance (the guard is its own group, [FMH-H2-1](FMH-H2-1.md) F1). The ADR-A79 addendum is
applied and dated.

## Invariant

Every decision of the typed IR brief (§1, §3, §3.1, §4, §4.3) that later slices build on is recorded in one
ADR, with what it supersedes in ADR-A79, so a slice never rests on a decision that only exists in a sketch.

## What changed

- [ADR-A123](../../architecture/decisions/ADR-A123-typed-operation-ir.md), **Proposed**. Ten decisions: the typed
  `Operation`, its type rules, derived read and write sets, declarations in the compiled profile over logical
  resources, the two-sided parameter guard, the PL-B payload with its `INFO` diagnostic, the kept form of the
  composite replace (TD-42), the retirement of Mustache behind the equivalence harness, the audit surface, and
  the list of what ADR-A79 loses.
- The catalogue row in `docs/architecture/decisions/README.md`.
- The ADR-A79 addendum is drafted at the foot of A123 and **not** applied to ADR-A79. It is added and dated
  when the maintainer accepts A123.
- A123 was free: no remote branch holds an `ADR-A123` file, and the catalogue ends at A122 (checked 2026-10-10).

## Test cases

A docs slice, so the cases are reading checks.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| H2.0-T1 | the sketch §6 list of superseded points / compared with A123 decision 10 / the same four points | L0 | + |
| H2.0-T2 | each of H2-Q1 to H2-Q6 / looked up in A123 / each answer appears in a decision | L0 | + |
| H2.0-T3 | the hazard table of sketch §3 / compared with decision 2 / every row present | L0 | + |
| H2.0-T4 | the file / `check:deny-terms` and `check:agent-guidance` / pass | L0 | + |

## One command

Run from the repository root. A pass is both tasks exiting 0.

```bash
mise run check:deny-terms && mise run check:agent-guidance
```

## Deliberate non-coverage

- Acceptance. The status of A123 stays Proposed until the maintainer accepts it.
- The ADR-A79 addendum text is a draft, and is applied on acceptance.
