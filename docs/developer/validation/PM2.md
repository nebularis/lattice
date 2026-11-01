<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: PM0 and PM2, promotions kept by the write that changes their source

**Unit:** [`projection-maintenance`](../status/projection-maintenance.md), slices PM0 and PM2 of the [plan](../plans/projection-maintenance.md), built with DR4 on 2026-11-01 in autonomous mode.

**For countersignature (non-weakening rule):** `RefresherTest` is removed with the `Refresher` it tested, which PM2's plan removes. What it held, that a write's derived data reaches a reader, is now held without a wait by `everyPromotedPartitionTheWritesKeepEqualsWhatTheWorkerRebuildsFromTheStore` and `aPublishIsOneCommitAndItsRegistryEntryIsReadableAtOnceWithNoJobRun`. The worker's tests were rewritten for one partition a source and keep every refusal they had.

**For the maintainer:** ADR-A149's addenda of 2026-11-01, one narrowing decisions 12 and 14 and one for PM0's names.

## Invariant

Each promoted partition, the rows of a source's promotions, equals what a rebuild from the whole store gives, after any write, with no job between the write and a read (PM-Q1 (a′), PM-Q2 (a)). A start rebuilds only when the promotions grew since the recorded digests, and warns without rebuilding when one changed or was removed (PM-Q3).

## What changed

- **PM0, the names.** `promotions.ttl` with the namespace `.../config-studio/promotion#` (`prm:`), graphs `urn:lattice:studio:promotion:{key}`, the job kind `cst:Rebuild`, the worker module `config_studio_rebuild`, and the classes `Promotions`, `PromotionsTest` and `RebuildWorker`. "Projection" is kept for `srf:ProjectionContract`'s output and for MORK's projections (PM-Q8 (a)).
- **The partitions.** A source's rows live in `urn:lattice:studio:promoted:{source}`, each contract naming its family by `cst:sourceFamily`. The writer's commit sends the staged partition clear and fill for each source it wrote, in the same request, whether or not the guarded write applied.
- **The summaries** are `workspace-summaries.rq`, evaluated as they are read.
- **The rebuild.** At start, `StudioApi.startUp` compares the record `urn:lattice:studio:promoted-record` with the staged digests. `POST /api/admin/rebuild` rebuilds for an administrator, and `GET /api/status` gives the start's warnings, which the studio shows.
- **Gone.** The `Refresher`, its batching and every wait for it.

## Tests

| ID | Given / When / Then | Level | Pass |
|---|---|---|---|
| PM2-T1 | a sequence of saves, publishes, imports and deletions / `everyPromotedPartitionTheWritesKeepEqualsWhatTheWorkerRebuildsFromTheStore` / each partition equals the Python worker's rebuild of a dump | L4 | |
| PM2-T2 | a publish / `aPublishIsOneCommitAndItsRegistryEntryIsReadableAtOnceWithNoJobRun` / one commit, the entry listed by the next read | L4 | |
| PM2-T3 | a workspace just created / `theWorkspaceListingIsOneReadOfTheSummariesQueryAndShowsAWorkspaceJustCreated` / listed at once | L4 | |
| PM2-T4 | a rebuild job / `aRebuildUpdateReplacesThePartitionsAndTheRecordItNamesWholeAndNothingElse` / replaced whole, another graph or a blank node refused | L4, negative | |
| PM2-T5 | any other update / `noOtherUpdateMayCarryAPromotedPartitionAndARebuildJobNamesNoWorkspace` / refused | L8, negative | |
| PM2-T6 | no record, then the same record, then one digest changed / `aStartRebuildsWhenThePromotionsGrewAndWarnsWithoutRebuildingWhenOneChanged` / a rebuild that records every contract, then nothing, then a warning naming the contract and no rebuild | L4, positive and negative | |
| PM2-T7 | the Java and Python digests / `theJavaDigestsOfThePromotionContractsEqualTheRecordThePythonWorkerWrites` / equal | L3 | |
| PM2-T8 | the worker / `test_config_studio_rebuild.py`, 8 tests / one partition a source, an empty one for a source gone, the record, no blank node, a failure sends nothing | L1 | |

**The one command:** `mise run check:config-studio`.

## Results, 2026-11-01

- `mise run check:config-studio` passed after PM0. `PromotionsTest` passes 9 of 9 with PM2-T6.
- Probe: with the start's check of changed contracts disabled, PM2-T6 failed, and it passed again once restored.
- A publish took 117 ms against 294 ms before PM2 and 85 ms at `4029bd0f`, measured under load. The plan's target of about 90 ms is not shown, and waits for a run on a quiet machine (DR4's pack).

## Deviations from the plan

1. **PM-Q7's check of a contract change's effect is not built.** A start warns about any changed or removed contract and rebuilds none, which is never wrong and sometimes too cautious. A change that only adds rows is still reported, so an administrator rebuilds it by hand. The migration of a change that alters rows is BL-12.
2. **PM0 was built after PM2's checkpoint,** not folded into it, so the names it changes are fewer.

## Decisions taken alone, for the maintainer's review

1. **The partition clear and fill run whether or not the guarded write applied,** since an unapplied write leaves the source as it was and the fill gives the same rows. It keeps the request free of a branch.
2. **A stack written before PM0 keeps orphaned graphs** under the old `urn:lattice:studio:projection:` names. Nothing reads them, and a rebuild leaves them. Dropping the studio's data, or a one-off drop of those graphs, removes them.
