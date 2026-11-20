<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSA-F11, a deletion answered from its receipt still removes a row its tombstone lost

**Unit:** [`multi-store-architecture`](../status/multi-store-architecture.md)
**Plan:** [multi-store-architecture](../plans/multi-store-architecture.md), MSA-F11, from finding MSAF7-01 of the review of 2026-11-19, as section 4.7 of the [brief of 2026-11-19](../notes/machine-s-brief-2026-11-19-multi-store.md) states it
**Machine:** machine S, Windows, Java 25 through mise, Maven 3.9.16, Jena 6.2.0 in memory. **Placement:** T0, public. The studio's writer, nothing domain-specific.
**Status:** built 2026-11-19, not verified.

## Invariant

A deletion wins over a save of the part or document it deletes, also when the batch that applied it failed after its update committed. [MSA-F7](MSA-F7.md) plans a lost tombstone again after the commit, in `Writer.finish`, but only for a command planned in the batch in hand. Where the update commits and the next step fails on a store that cannot be reached, `apply` throws, the stream writer sends the whole batch again, and the resend is answered from the receipt. Before this slice no plan held the deletion then, so `finish` did not run and the row stayed live with nothing reaching it (MSAF7-01). Now a deletion answered from its receipt removes each row it retires that is still live, in the same rounds as a deletion applied in the batch.

## How

- **Which deletions.** A `deleteDocument` or `deleteWorkspace` answered from its receipt, with the receipt's digest matching the resend. A resend refused for another body (MSAI11-02) retires nothing.
- **Which rows: the receipt's written graphs.** The receipt records `cst:wrote` for each graph the command wrote, and a deletion writes the graph of every part and document it tombstones. One query, `StudioStore.receiptWrote`, reads them for all such deletions in the batch, by command id. A part's graph is matched against `Graphs.config` for each of `Workspace.GRAPHS`, and a document's is read back by `Graphs.documentIdOfGraph`, the inverse of `Graphs.documentGraph`, since a document id is a UUID and is not encoded. The description cannot give a deleted workspace's documents, since it is tombstoned, and the receipt names them. A read of the version rows by a prefix was the other choice, and it needs a string filter over the meta graph where the receipt's read is one lookup by id, so the receipt was taken.
- **Why a live row is a lost one.** A deleted id is never used again ([MSA-F9](MSA-F9.md)), and a part of a deleted workspace cannot be saved, since the workspace is not found. So a row among them that is still live is one its tombstone lost.
- **The same operation and guard.** Each row becomes a `Retired`, with the receipt as its cause and the command's actor, and goes through `finish` as MSA-F7 built it: the generated `tombstone-delete` at the revision the row has, guarded on it, and the patch log dropped up to the new tombstone's revision, up to three rounds. Its transactions are `urn:txn:{command id}/resent/{k}-again-{round}`, by the roots in order, so they never meet the names of the first send's.
- **The batched read.** Each round of `finish` now reads the rows of all its pending roots in one query, through `StudioOperations.seqs`, which calls the batched `StudioStore.versionRows` with each root's family meta graph. Before, it asked one query a root.

The cost falls on a resend of a deletion only: one query for the written graphs and one for the rows, then nothing where every row is gone.

## Draft for the maintainer: the addendum to ADR-A149, amended

MSA-F7's draft addendum ends "A row still live after the last attempt is logged and left, as is one whose writer stopped between the two requests." With this slice it reads as follows.

> A row still live after the last attempt is logged and left. Where the writer stopped or failed between the command's request and the next, a resend of the deletion is answered from its receipt and plans the tombstone again in the same way, so a row is left only where no resend arrives.

## Tests

`platform/config-studio-service/src/test/java/org/nebularis/lattice/studio/MultiAggregateCommandsTest.java`. A new store wrapper, `unreachableAfterCommit`, runs a save just before the writer's update, as `interfered` does, and once that update has committed fails the next query or update once with `HttpException("connect", ConnectException)`, which the stream writer retries as a store that cannot be reached. The step it fails is the read of the receipts after the commit, so `apply` throws.

| ID | Given / When / Then | Level | Invariant | Pass criterion | Kind |
|---|---|---|---|---|---|
| F11-T1 | Given a document at revision 1, when a save moves it to 2 just before a `deleteDocument`'s update, and the store cannot be reached for the step after the commit, then `apply` throws, the receipt is written, the description no longer lists the document and its row is live at 2. When the same command is sent again, then it is answered 200 from the receipt, the row is tombstoned, the graph is empty and the patch log for revisions 1 to 3 is gone | L4 | the invariant | `aDocumentDeletionAnsweredFromItsReceiptAfterAFailurePastTheCommitStillDeletesTheDocument` passes | negative |
| F11-T2 | Given a workspace with its baseline, its surface part at 1 and a document at 1, when a save moves the surface part to 2 just before a `deleteWorkspace`'s update, and the store cannot be reached for the step after the commit, then `apply` throws, the receipt is in the store's receipts, no workspace is found and the surface row is live at 2. When the same command is sent again, then it is answered 200, the surface row is tombstoned, its graph is empty, its patch log for revisions 1 to 3 is gone, the baseline and the document stay tombstoned, and the resend asked 5 queries: the receipts, their digests, the written graphs, and the rows once in each of two rounds | L4 | the invariant and the batched read | `aWorkspaceDeletionAnsweredFromItsReceiptAfterAFailurePastTheCommitStillRemovesThePart` passes | negative |
| existing | MSA-F6's and MSA-F7's tests in the same class, and `ReceiptsTest` | L4 | unchanged | pass | |

F11-T2's count of 5 holds the batched read: with one query a root, its three roots (baseline, surface, document) and the second round's one would make 7. This was reasoned from the code and not run against the old `finish`, since both tests already fail before the change on the live row.

## Commands and results

Run on 2026-11-19.

| Command | Result |
|---|---|
| `mise exec -- mvn -f platform/pom.xml -pl config-studio-service -am test -Dtest=MultiAggregateCommandsTest,ReceiptsTest -Dsurefire.failIfNoSpecifiedTests=false`, before the change | 18 tests, 2 failures. F11-T1 and F11-T2 each: "the resend removed the live row ==> expected: <Optional.empty> but was: <Optional[2]>". `ReceiptsTest` 9 tests, 0 failures |
| the same, after the change | `MultiAggregateCommandsTest` 9 tests, `ReceiptsTest` 9 tests, 18 in all, 0 failures, BUILD SUCCESS |
| `mise run check:config-studio` | exit 0. pytest 158 passed, JUnit 249 tests across the studio's modules with 0 failures and 0 errors (authoring 9, core 24, service 196, transforms 2, writer 18), the browser checks `Tests 121 passed (121)` |

The one command for the slice is `mise run check:config-studio`.

## Deliberate non-coverage

- A batch whose update fails before it commits. Nothing is written then, and the resend is planned anew, as before.
- A resend that never arrives, for example a write whose sender gave up and whose offset another member stored. The row stays live, as MSA-F7 left it, and only a sweep of the rows no description reaches would remove it.
- The failure is made by a wrapper of the in-memory store, not by a Fuseki that is stopped. The stream writer's retry of a batch on `HttpException` with a `ConnectException` cause is held by `StreamWriterTest`, and is not run here.
- A receipt written before the writer recorded `cst:wrote` would retire nothing. Every receipt the writer writes records it.

## Doc delta

None outside this pack. MSA-F7's pack, its draft addendum and its first non-coverage bullet still describe the resend as answered from the receipt alone. The amended draft above is for the coordinator to carry over.
