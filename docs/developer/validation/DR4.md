<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: DR4, the studio on the generated delta replace

**Unit:** [`persistence-delta-replace`](../status/persistence-delta-replace.md), slice DR4 of the [plan](../plans/persistence-delta-replace.md), built with PM2 on 2026-11-01 in autonomous mode.

**For countersignature (non-weakening rule):** no test of the write path was weakened. `StudioOperationsTest` compares every quad but the digest's, since the generated delta replace's digest is over the delta and the hand-written one's was over the whole state (DR-Q3 (a)), which DR3's vector `digest-replace-delta` covers.

## Invariant

The studio's writer replaces a part and a document only through the generated delta replace, so no hand-written SPARQL writes them (TD-136, PRI-60). A save sent as a patch, what is added and removed against the revision read, leaves the state the same save sent whole leaves.

## What changed

- **The writer.** Operations are keyed by name, so a family holds its delta replace and `replace-whole`. `replaceDelta()` fills the generated delta from the stored and the next state, and the hand-written sweep helpers are gone (TD-136 closed). A bulk write uses `replace-whole`.
- **The patch.** `PATCH /api/workspaces/{ws}/graphs/{name}` takes TriG with the graphs `urn:lattice:studio:patch:add` and `urn:lattice:studio:patch:del` and an `If-Match`. A blank node is refused with 400, and the browser sends that part whole. An absent side is empty, since Jena keeps no empty graph (TSD-69).
- **The browser.** `rdf/patch.ts` sends a patch when it holds the saved part and no blank node is involved.
- **The merge gate.** Both browser suites run at a merge into `main` that touches the studio, the fake service's and the real stack's (ADR-A133 decision 11).

## Tests

| ID | Given / When / Then | Level | Pass |
|---|---|---|---|
| DR4-T1 | each family with a delta replace / `aDeltaReplaceLeavesWhatTheGeneratedReplaceLeaves` / the store equals the generated whole replace's, but for the digest quad | L3 | |
| DR4-T2 | a family with no delta replace / `aDeltaReplaceIsOnlyForPartsAndDocuments` / refused | L1, negative | |
| DR4-T3 | a part saved, then patched / `aPatchLeavesThePartASaveOfTheSameChangeLeaves` / the same state, a new ETag, 412 when stale, 428 with no `If-Match`, 415 for Turtle, 422 for another graph, 400 for a blank node, 204 for a patch that only adds | L4, positive and negative | |
| DR4-T4 | a part with blank nodes / `anEarlierRevisionOfAPartIsRebuiltFromThePatchLogBlankNodesIncluded` / its earlier revision rebuilt from the patch log | L4 | |
| DR4-T5 | a saved part and an edit / `patch.test.ts` / the patch holds what was added and removed and nothing kept, declines a blank node, names both graphs | L1 | |
| DR4-T6 | the real stack / `e2e-stack/stack.spec.ts`, an author edits and saves / saved by a patch | L6 | |

**The one command:** `mise run check:config-studio`, then `mise run test:config-studio-browser` for DR4-T6.

## Results, 2026-11-01

- `mise run check:config-studio` passed after PM0: 138 Python tests, 24 Java tests in the core and 170 in the service, 112 browser unit tests.
- `mise run test:config-studio-browser` passed: 20 journeys on the fake service and 2 on the real stack.
- DR4-T6 failed first, on the real stack. A patch that only added was refused, since its empty `del` graph was gone after Jena parsed it. The writer now reads an absent side as empty, and DR4-T3 covers it.
- **The benchmark** (`mise run benchmark:studio-api`, report `20261101T212435Z-0c3fef20`) is not read yet. Both runs on 2026-11-01 met a load average of 3 and of 10 from other work on the machine, against 1.5 for `2e8a02cc`, so every measure but publish moved outside the noise. A publish took 117 ms in both runs, against 294 ms at `2e8a02cc`. The done criterion, saves no slower than `2e8a02cc`, waits for a run on a quiet machine.

## Deviations from the plan

1. **The benchmark is unread,** for the reason above.

## Decisions taken alone, for the maintainer's review

1. **A missing side of a patch is empty, and any other graph is refused,** so a reader never depends on a graph Jena drops (TSD-69).
2. **The fake service stays,** and the real stack joins it at a merge, as the maintainer chose on 2026-11-01.
