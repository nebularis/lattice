<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSA-F7, a deletion that loses a race to a save still removes what it deletes

**Unit:** [`multi-store-architecture`](../status/multi-store-architecture.md)
**Plan:** [multi-store-architecture](../plans/multi-store-architecture.md), MSA-F7, from finding MSAF6-01 of [MSA-F6](MSA-F6.md), as the maintainer decided it on 2026-11-18
**Machine:** machine S, Windows, Java 25 through mise, Maven 3.9.16, Jena 6.2.0 in memory. **Placement:** T0, public. The studio's writer, nothing domain-specific.
**Status:** built 2026-11-18, not verified. The decision record needs an addendum, drafted below for the maintainer.

## Invariant

A deletion wins over a save of the part or document it deletes. `deleteDocument` and `deleteWorkspace` remove the description's mention first, as [ADR-A149](../../architecture/decisions/ADR-A149-publication-from-the-studio.md) decision 13 has it, then tombstone each row. A tombstone is guarded on the row's revision, so a save that moved the revision just before made it write nothing, and the row and its graph stayed live with nothing reaching them, for good (MSAF6-01). Now the first send removes them, and no resend is needed.

## How

The generated `tombstone-delete` operation is unchanged, and each tombstone is still guarded on the revision it expects, so the writer still calls only generated operations (decision 12).

- **The receipt follows the description's step.** For `deleteWorkspace` it already did. For `deleteDocument` it followed the tombstone, so a lost tombstone answered "send it again" and the resend found no document. Once the description no longer lists the document no reader finds it, so the command is answered as applied from that step.
- **A lost tombstone is planned again.** The writer records each tombstone a deletion plans. After the commit, for each deletion applied, a row that is still live lost its tombstone, and the writer plans it again at the revision the row has then, with the patch log up to the new tombstone's revision, in a request of its own. Up to three rounds. A row that is gone is done, and one still live after the third round is logged and left.
- **Who wins.** The save that beat the tombstone committed and was answered 200. The deletion then removes what it saved. This is the order the two were applied in, a save then a deletion.

## Draft for the maintainer: an addendum to ADR-A149

The brief of 2026-11-17 keeps decision records off this branch, so the text is here, for the maintainer to write where the decision records are kept.

> **Narrows decision 13.** A deletion wins over a write of the part or document it deletes. Its tombstones stay guarded on the revision they expect. Where a write moved a row's revision first, so its tombstone wrote nothing, the writer plans the tombstone again at the revision the row then has, in a request after the command's own, until the row is gone or three attempts have failed. A deletion's receipt is guarded on the step that removes the description's mention, since after it no reader finds what is deleted. A row still live after the last attempt is logged and left, as is one whose writer stopped between the two requests. A sweep of the rows no description reaches would remove both, and is not built.

## Tests

`platform/config-studio-service/src/test/java/org/nebularis/lattice/studio/MultiAggregateCommandsTest.java`. Two of MSA-F6's tests, which recorded the orphan, now require the deletion. Each still asserts that the interfering save committed first, with a 200 at revision 2.

| ID | Given / When / Then | Level | Invariant | Pass criterion | Kind |
|---|---|---|---|---|---|
| F7-T1 | Given a document at revision 1, when a save moves it to 2 just before a `deleteDocument` is applied, then the deletion is answered 200 with a receipt, the description no longer lists the document, its row is tombstoned, its graph is empty, its patch log for revisions 1 to 3 is gone, and a resend is answered 200 from the receipt | L4 | the invariant | `deletingADocumentWhoseTombstoneLosesARaceToASaveStillDeletesTheDocument` passes | negative |
| F7-T2 | Given a workspace whose surface part is at revision 1, when a save moves it to 2 just before a `deleteWorkspace` is applied, then the deletion is answered 200, no workspace is found, the surface part's row is tombstoned, its graph is empty and its patch log for revisions 1 to 3 is gone, and a resend is answered 200 | L4 | the invariant | `deletingAWorkspaceWhosePartTombstoneLosesARaceToASaveStillRemovesThePart` passes | negative |
| existing | MSA-F6's other four tests, `ReceiptsTest`, `DocumentsTest` and `WorkspaceCommandsTest` | L4 | unchanged | pass | |

## Commands and results

Run on 2026-11-18.

| Command | Result |
|---|---|
| `mise exec -- mvn -q -f platform/pom.xml -pl config-studio-service -am test -Dtest=MultiAggregateCommandsTest -Dsurefire.failIfNoSpecifiedTests=false`, before the change | 6 tests, 2 failures. F7-T1: expected 200 but was 400, "the workspace changed while the command was applied, so send it again". F7-T2: the surface part's row expected gone but was at revision 2 |
| the same with `-Dtest=MultiAggregateCommandsTest,ReceiptsTest`, after the change | 15 tests, 0 failures |
| `mise run check:config-studio` | exit 0. JUnit 241 tests across the studio's modules with 0 failures (the service's 192), the browser checks 121 passed, pytest passed |

The one command for the slice is `mise run check:config-studio`.

## Deliberate non-coverage

- A writer that stops between the command's request and the next. The receipt is then written and the row stays live, as before this slice, and a resend is answered from the receipt. A sweep would remove it.
- A save that beats all three further rounds. Each round needs another writer to save the same row in the moment between the read and the update, which the single writer of each partition makes very unlikely.
- The interference is made by a second writer on the same store, not by a second process, as in MSA-F6.

## Doc delta

MSA-F6's Validation Pack names this slice beside MSAF6-01 and gives its two tests their new names.
