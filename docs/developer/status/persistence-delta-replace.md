<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Writing only what changed, as a persistence mode - Status

**Unit ID:** `persistence-delta-replace`
**Status:** 🟡 DR1 to DR4 built and merged into the studio's branch 2026-11-02, awaiting the maintainer's review
**Last updated:** 2026-11-02
**Plan:** [persistence-delta-replace.md](../plans/persistence-delta-replace.md)
**Sketch:** [persistence-delta-replace.md](../sketches/persistence-delta-replace.md)
**Branch:** `realign/config-authoring-studio`, which merged `claude/persistence-linear-replace` and `claude/persistence-delta-replace` on 2026-11-02

## Current position

The maintainer raised the unit on 2026-10-31 from the studio's quality work and answered DR-Q1 to DR-Q7 that day. The studio line built a delta replace from those answers on 2026-11-01, and this unit's own line built one on H2.12 on 2026-11-02, after the maintainer decided DR-Q4 to DR-Q8 and confirmed DR-Q1 to DR-Q3. On 2026-11-02 the maintainer chose to merge both with this line's design as the base, item by item: the kind `dal:DeltaReplace`, H2.12, the README's §5.6.12 and the caller checks from this line, and `replace-whole`, `load-whole`, the opt-in state digest and the studio's writer from the studio line, as DR4 ([plan §9](../plans/persistence-delta-replace.md#9-the-studio-lines-slices)). The studio line's DR-Q5 to DR-Q7 are now DR-Q9 to DR-Q11, and the two lines' standards are numbered STD-301 to STD-308.

**Next action:** for the maintainer, review the Validation Packs, re-approve the regenerated expected profiles, accept or change the ADR-A123 addenda of 2026-11-02, and ratify STD-301 to STD-308. Then DR3's remaining step, the studio deployment's capability spec ([plan §9](../plans/persistence-delta-replace.md#9-the-studio-lines-slices)).

## Slices

| Slice | State | Blocked on |
|---|---|---|
| DR1 | **built 2026-11-02, awaiting the maintainer's review.** Fourteen expected profiles for re-approval, the ADR-A123 addendum of 2026-11-02 for acceptance | the review |
| DR2 | **built 2026-11-02, awaiting the maintainer's review.** Seven standards for ratification | the review |
| DR3 | **built on the studio line as its DR4 on 2026-11-01, finished at the merge 2026-11-02** | the review |
| DR4 | **carried over from the studio line at the merge 2026-11-02** | the review |

## Log

- The studio line:
  - 2026-10-31: sketched, every question answered, planned.
  - 2026-11-01: the maintainer asked for every planned slice on `claude/config-authoring-studio`, built autonomously, with the linear replace branch kept apart until later.
  - 2026-11-01: DR1 built. The vocabulary, the derived default, two refusals, twelve delta builders, a slot in a DELETE template, the contract with no payload part, whole-state fixtures for every test of the whole replace, and the studio pinned to the whole replace until DR4. `check:persistence` 4,312 passed, `check:persistence-conformance` 5,104 passed, `check:persistence-library` passed. Two Sonnet subagents wrote the vocabulary and the whole-state fixtures.
  - 2026-11-01: DR3 built before DR2, since DR1 left the libraries' tests reading the delta replace. A delta replace's digest has no payload part, `digest-replace-delta` is a vector, and both libraries read and digest the delta replace. TDB2 and Fuseki are covered through the studio in DR4.
  - 2026-11-01: DR2 built. `replace-whole` beside the delta replace, the bulk load composed by the caller under one transaction id an aggregate, the opt-in state digest with its record and its audit, `compose` and `state_digest` in both libraries, and TSD-68 (Oxigraph refuses a prologue after `;`). Conformance 5,213 passed.
  - 2026-11-01: DR4 built with PM2. The writer replaces parts and documents through the generated delta replace (TD-136 closed), the service takes a patch, and the browser sends one where it can. The real-stack browser suite found a patch with one empty side refused, since Jena keeps no empty graph (TSD-69), now fixed. Both browser suites run at a merge into `main` (ADR-A133 decision 11). `check:config-studio` and `test:config-studio-browser` passed. The benchmark ran twice under load from other work, a publish at 117 ms both times, so it is not read yet.
- This unit's line:
  - 2026-11-02: planned. DR-Q1 to DR-Q3 decided at the leanings, with the maintainer's questions on cost, novelty and the digest answered in the sketch. DR1 started.
  - 2026-11-02: DR1 built autonomously. Ten delta builders, the kind `dal:DeltaReplace`, the dimension `replaceEncoding` with its two refusals and one warning, the README's §5.6.12 with four diagrams and the running case on the delta, the example `replace-encoding`, fourteen expected profiles, the benchmark's delta form, the studio's profiles pinned to `dal:WholeState` until DR3. `check:persistence` 4,721 passed, conformance 5,577 passed and 16 skipped on three engines ([Validation Pack](../validation/persistence-delta-replace.md)). The mechanical half was written by a Sonnet subagent and reviewed.
  - 2026-11-02: DR2 built autonomously. Both caller libraries check a delta, `DeltaOverlap`, `EmptyDelta` and, given the next state, `AssertOutsideNextState`, `RetractInNextState` and the bound over the next state, the digest vector `digest-delta-replace`, the seven caller obligations as STD-302 to STD-308 closing TD-137. Libraries 127 and 118, vectors 94, conformance 5,577 passed and 16 skipped ([Validation Pack](../validation/persistence-delta-replace.md)). DR3 briefed in plan §8. The mechanical half was written by the same Sonnet subagent and reviewed.
- 2026-11-02: both lines merged into `realign/config-authoring-studio`, with this line's design as the base and the studio line's `replace-whole`, `load-whole`, state digest and writer carried over as DR4. The studio's writer moved onto the kind `dal:DeltaReplace`, runs the caller check over the next state, and answers a save that changes nothing with the revision it has, writing nothing (STD-301). TD-136 closed.
