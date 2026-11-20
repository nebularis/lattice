<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSA-F9, a new document's save reads the document's own row

**Unit:** [`multi-store-architecture`](../status/multi-store-architecture.md)
**Plan:** [multi-store-architecture](../plans/multi-store-architecture.md), MSA-F9, from finding MSAF6-02 of [MSA-F6](MSA-F6.md), as the maintainer agreed on 2026-11-18
**Machine:** machine S, Windows, Java 25 through mise, Maven 3.9.16, Jena 6.2.0 in memory. **Placement:** T0, public. The studio's writer, nothing domain-specific.
**Status:** built 2026-11-18, not verified. It also fixes a defect its test found, MSAF9-01.

## Invariant

A deleted document's row stays tombstoned, so its id is never created again, as the writer's comment already said. A new document's save gets one of two answers, and its reply says which.

- **The id was deleted.** Refused with "the document was deleted, so its id cannot be used again", and nothing is written.
- **Another command moved the description first.** The document's graph and row are written and the description's replace wrote nothing, as MSA-F6's F6-T3 shows. Answered "the workspace changed while the command was applied, so send it again", and the resend completes it. It was answered as a deleted id before (MSAF6-02).

The reply reads the document's own row, through a new `StudioOperations.tombstoned`, where it read the description's revision of the document, which is 0 in both cases.

## MSAF9-01, found by this slice's test

A save of a new document under a deleted document's id was answered 200. The create of the document wrote nothing, since a create writes nothing over an existing version row and a tombstoned row is one. The description's replace then listed the document. The save's receipt is guarded on the description's step, so the command counted as applied. A reader then found a listed document at revision 0 with an empty graph. The user was told the save had applied, and nothing they saved was kept. Probed on the code before the change: reply 200 at revision 1, the document listed, revision 0, graph empty.

The writer now refuses such a save before planning anything, where the document is not listed, the save expects revision 0, and the row is tombstoned in the store or by a deletion earlier in the same batch. The unapplied reply above covers a deletion that lands between the read and the update. The check costs a new document's save one more read.

`DocumentsTest.aDocumentIsDeletedWithItsGraphAndWithItsWorkspace` saved a document again under the id it had just deleted, and was answered 204 for a save that kept nothing. It now asserts the 400, and the API answers it 400, and saves another document under a new id before deleting the workspace.

## Tests

| ID | Given / When / Then | Level | Invariant | Pass criterion | Kind |
|---|---|---|---|---|---|
| F9-T1 | MSA-F6's F6-T3: given a new document's save whose description replace loses to a `setAccess`, then the reply says to send it again, and the resend completes it at revision 1 | L4 | the lost race | `savingANewDocumentWhoseDescriptionGuardFailsLeavesAnOrphanDocumentGraphAndAResendCompletesIt` passes | negative |
| F9-T2 | Given a document saved and deleted, when a new document is saved under its id, then the reply is the deleted id's refusal, the description does not list it and its graph is empty | L4 | MSAF9-01 | `savingANewDocumentUnderADeletedDocumentsIdIsRefusedAsADeletedId` passes | negative |
| F9-T3 | the same through the API, a 400, then another document saved under a new id and removed with its workspace | L3 | MSAF9-01 | `DocumentsTest.aDocumentIsDeletedWithItsGraphAndWithItsWorkspace` passes | negative |

## Commands and results

Run on 2026-11-18.

| Command | Result |
|---|---|
| `mise exec -- mvn -f platform/pom.xml -pl config-studio-service -am test -Dtest=MultiAggregateCommandsTest -Dsurefire.failIfNoSpecifiedTests=false`, before the change | 7 tests, 2 failures. F9-T1: expected "send it again" but was the deleted id's refusal. F9-T2: expected the deleted id's refusal but was 200 at revision 1 |
| the same with `-Dtest=MultiAggregateCommandsTest,DocumentsTest,ReceiptsTest`, after the change | 7, 9 and 9 tests, 0 failures, once F9-T3 asserts the 400 |
| `mise run check:config-studio` | exit 0. JUnit 244 tests across the studio's modules with 0 failures, the browser checks 121 passed, pytest passed |

The one command for the slice is `mise run check:config-studio`.

## Deliberate non-coverage

- A part's save. A part is never tombstoned while its workspace lives, so the same case cannot arise.
- The browser's message for the refusal, which it shows as it shows any failed save.
