<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Writing only what changed, as a persistence mode - Status

**Unit ID:** `persistence-delta-replace`
**Status:** 🟢 DR1 built 2026-11-02, awaiting the maintainer's review, DR2 in progress
**Last updated:** 2026-11-02
**Plan:** [persistence-delta-replace.md](../plans/persistence-delta-replace.md)
**Sketch:** [persistence-delta-replace.md](../sketches/persistence-delta-replace.md)
**Branch:** `claude/persistence-delta-replace`, off `claude/persistence-linear-replace` (H2.12)

## Current position

The maintainer raised the unit on 2026-10-31 from the studio's quality work, answered DR-Q4 to DR-Q8 on 2026-11-01 and DR-Q1 to DR-Q3 on 2026-11-02, every one at its leaning, and asked that the Persistence README carry narrative and diagrams for these choices and for H2.12's. The plan was written the same day and DR1 began, in autonomous mode.

**Next action:** build DR2, then brief DR3 for the studio agent. For the maintainer, review DR1's Validation Pack, re-approve the fourteen expected profiles, and accept or change the ADR-A123 addendum of 2026-11-02.

## Slices

| Slice | State | Blocked on |
|---|---|---|
| DR1 | **built 2026-11-02, awaiting the maintainer's review.** Fourteen expected profiles for re-approval, the ADR-A123 addendum of 2026-11-02 for acceptance | the review |
| DR2 | in progress, 2026-11-02 | |
| DR3 | planned, the studio agent's | DR2, and a brief |

## Log

- 2026-11-02: planned. DR-Q1 to DR-Q3 decided at the leanings, with the maintainer's questions on cost, novelty and the digest answered in the sketch. DR1 started.
- 2026-11-02: DR1 built autonomously. Ten delta builders, the kind `dal:DeltaReplace`, the dimension `replaceEncoding` with its two refusals and one warning, the README's §5.6.12 with four diagrams and the running case on the delta, the example `replace-encoding`, fourteen expected profiles, the benchmark's delta form, the studio's profiles pinned to `dal:WholeState` until DR3. `check:persistence` 4,721 passed, conformance 5,577 passed and 16 skipped on three engines ([Validation Pack](../validation/persistence-delta-replace.md)). The mechanical half was written by a Sonnet subagent and reviewed.
