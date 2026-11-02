<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Writing only what changed, as a persistence mode - Status

**Unit ID:** `persistence-delta-replace`
**Status:** building 2026-11-01. DR-1, DR-2 and DR-4 built, awaiting the maintainer's review. DR-3 lacks its capability spec
**Last updated:** 2026-11-02
**Plan:** [persistence-delta-replace.md](../plans/persistence-delta-replace.md)
**Sketch:** [persistence-delta-replace.md](../sketches/persistence-delta-replace.md)

## Current position

The maintainer raised the unit on 2026-10-31 from the studio's quality work and answered DR-Q1 to DR-Q7 that day. The studio line built a delta replace from those answers on 2026-11-01, and this unit's own line built one on H2.12 on 2026-11-02, after the maintainer decided DR-Q4 to DR-Q8 and confirmed DR-Q1 to DR-Q3. On 2026-11-02 the maintainer chose to merge both with this line's design as the base, item by item: the kind `dal:DeltaReplace`, H2.12, the README's §5.6.12 and the caller checks from this line, and `replace-whole`, `load-whole`, the opt-in state digest and the studio's writer from the studio line, as DR-4 ([plan §9](../plans/persistence-delta-replace.md#9-the-studio-lines-slices)). The studio line's DR-Q5 to DR-Q7 are now DR-Q9 to DR-Q11, and the two lines' standards are numbered STD-309 to STD-316.

**Next action:** for the maintainer, review the Validation Packs, re-approve the regenerated expected profiles, accept or change the ADR-A123 addenda of 2026-11-02, and ratify STD-309 to STD-316. Then DR-3's remaining step, the studio deployment's capability spec ([plan §9](../plans/persistence-delta-replace.md#9-the-studio-lines-slices)).

## Slices

| Slice | Deliverable | State | Blocked on |
|---|---|---|---|
| DR-1 | the vocabulary, the delta builders, the kind and the selection | built 2026-11-02, [Validation Pack](../validation/persistence-delta-replace.md). Fourteen expected profiles for re-approval, the ADR-A123 addendum of 2026-11-02 for acceptance | the review |
| DR-2 | both caller libraries' checks and vectors, the caller obligations as standards | built 2026-11-02. Seven standards for ratification | the review |
| DR-3 | the studio's writer on the generated delta replace | building 2026-11-01. All but its capability spec, which gives the whole-state families the rows form |  |
| DR-4 | `replace-whole`, `load-whole` and the state digest, carried over from the studio line | built 2026-11-02, [Validation Pack](../validation/DR-4.md) | the review |

## Log

- The studio line:
  - 2026-10-31: sketched, every question answered, planned.
  - 2026-11-01: the maintainer asked for every planned slice on `claude/config-authoring-studio`, built autonomously, with the linear replace branch kept apart until later.
  - 2026-11-01: DR-1 built. The vocabulary, the derived default, two refusals, twelve delta builders, a slot in a DELETE template, the contract with no payload part, whole-state fixtures for every test of the whole replace, and the studio pinned to the whole replace until DR-4. `check:persistence` 4,312 passed, `check:persistence-conformance` 5,104 passed, `check:persistence-library` passed. Two Sonnet subagents wrote the vocabulary and the whole-state fixtures.
  - 2026-11-01: DR-3 built before DR-2, since DR-1 left the libraries' tests reading the delta replace. A delta replace's digest has no payload part, `digest-replace-delta` is a vector, and both libraries read and digest the delta replace. TDB2 and Fuseki are covered through the studio in DR-4.
  - 2026-11-01: DR-2 built. `replace-whole` beside the delta replace, the bulk load composed by the caller under one transaction id an aggregate, the opt-in state digest with its record and its audit, `compose` and `state_digest` in both libraries, and TSD-68 (Oxigraph refuses a prologue after `;`). Conformance 5,213 passed.
  - 2026-11-01: DR-4 built with PM-2. The writer replaces parts and documents through the generated delta replace (TD-136 closed), the service takes a patch, and the browser sends one where it can. The real-stack browser suite found a patch with one empty side refused, since Jena keeps no empty graph (TSD-69), now fixed. Both browser suites run at a merge into `main` (ADR-A133 decision 11). `check:config-studio` and `test:config-studio-browser` passed. The benchmark ran twice under load from other work, a publish at 117 ms both times, so it is not read yet.
- This unit's line:
  - 2026-11-02: planned. DR-Q1 to DR-Q3 decided at the leanings, with the maintainer's questions on cost, novelty and the digest answered in the sketch. DR-1 started.
  - 2026-11-02: DR-1 built autonomously. Ten delta builders, the kind `dal:DeltaReplace`, the dimension `replaceEncoding` with its two refusals and one warning, the README's §5.6.12 with four diagrams and the running case on the delta, the example `replace-encoding`, fourteen expected profiles, the benchmark's delta form, the studio's profiles pinned to `dal:WholeState` until DR-3. `check:persistence` 4,721 passed, conformance 5,577 passed and 16 skipped on three engines ([Validation Pack](../validation/persistence-delta-replace.md)). The mechanical half was written by a Sonnet subagent and reviewed.
  - 2026-11-02: DR-2 built autonomously. Both caller libraries check a delta, `DeltaOverlap`, `EmptyDelta` and, given the next state, `AssertOutsideNextState`, `RetractInNextState` and the bound over the next state, the digest vector `digest-delta-replace`, the seven caller obligations as STD-310 to STD-316 closing TD-139. Libraries 127 and 118, vectors 94, conformance 5,577 passed and 16 skipped ([Validation Pack](../validation/persistence-delta-replace.md)). DR-3 briefed in plan §8. The mechanical half was written by the same Sonnet subagent and reviewed.
- 2026-11-02: both lines merged into `realign/config-authoring-studio`, with this line's design as the base and the studio line's `replace-whole`, `load-whole`, state digest and writer carried over as DR-4. The studio's writer moved onto the kind `dal:DeltaReplace`, runs the caller check over the next state, and answers a save that changes nothing with the revision it has, writing nothing (STD-309). TD-136 closed.
- 2026-11-02: `main` merged in, with the work board. The plan declares the prefix DR, the slices are DR-1 to DR-4 and their packs renamed to match, and the board is in the standard shape. Two register rows collided with the work board's, settled by first in wins, which `check:identifiers` found a tie at the day, so the work board's kept their numbers. This line's standards STD-300 to STD-308 became STD-308 to STD-316, and its closed TD-137 became TD-139, each citation with them.
