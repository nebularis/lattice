<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSA-F15, an id whose row exists is never created again

**Unit:** [`multi-store-architecture`](../status/multi-store-architecture.md)
**Plan:** [multi-store-architecture](../plans/multi-store-architecture.md), MSA-F15, from TD-168 and TD-171 of the [technical debt register](../technical-debt.md), as section 4.8 of the [machine S brief of 2026-11-19](../notes/machine-s-brief-2026-11-19-multi-store.md) and section 3 of the [handover of 2026-11-23](../notes/machine-s-handover-2026-11-23.md) state it
**Machine:** machine S, Windows, Java 25.0.2 through mise, Maven 3.9.16, Jena 6.2.0 in memory. **Placement:** T0, public. The studio's writer and command codec, nothing domain-specific.
**Status:** built 2026-11-23, not verified.

## Invariant

A save that creates a document, one that expects revision 0 of a document the description does not list, is refused where the document's version row exists, live or tombstoned (ADR-A149's addendum of 2026-11-19, point 5). A create over a row writes nothing, so before this slice such a save under a live, unlisted row listed the document again at revision 1, discarded its body and showed what a deletion had removed (TD-168). [MSA-F9](MSA-F9.md) refused a tombstoned row only, since `StudioOperations.workspace` reads the rows of listed documents alone. A deletion whose tombstone lost leaves exactly such a row until the deletion finishes (MSA-F11), so MSA-F11's "a deleted id is never used again" holds only with this slice.

A deletion delivered twice more after a lost tombstone, with every attempt of the first redelivery lost too, still removes the row (TD-171). This held before the slice, so the transaction ids were not changed.

## Change

- `Writer.saveDocument`, in [Writer.java](../../../platform/config-studio-core/src/main/java/org/nebularis/lattice/studio/writes/Writer.java). The refusal of MSA-F9 now asks whether the document's root has a version row, live or tombstoned, where it asked whether the row was tombstoned. The batch helper `deleted` became `hasRow`, which also counts a root a deletion earlier in the batch tombstones, as before. The refusal keeps MSA-F9's words, "the document was deleted, so its id cannot be used again".
- **One exception, which the brief does not state.** A row whose create was the command's own first step, `urn:txn:{command id}/1`, on a delivery whose description step lost, is the command's own, and the resend is planned as before and completes it. Without it, MSA-F6's F6-T3, which MSA-F9 kept as F9-T1, fails, since its resend finds its own live, unlisted row. The exception reads the claim of that transaction, only where a row exists. A question for the maintainer, below.
- `StudioStore.hasVersionRow` and `StudioOperations.hasRow`, new. One query on the row, the same one `tombstoned` asks, true for any row. A new document's save still costs one read more than another save, and the claim's read only where a row exists.
- The comment of `Writer.retiredBy` names MSA-F15 beside MSA-F9.
- `MultiAggregateCommandsTest`, two tests and a helper, `moves`, that moves a document's row by its generated replace before each of the writer's updates, as a writer that read it before would. `CodecTest`, one test.

No vocabulary, contract or other code changed. `Codec.java` holds no change after the probe below, which `git diff` on it confirmed.

## Tests

| ID | Given / When / Then | Level | Invariant | Pass criterion | Kind |
|---|---|---|---|---|---|
| F15-T1 | Given a document at revision 1, when a save moves it to 2 just before a `deleteDocument`'s update and the store cannot be reached for the step after the commit, then the row is live at 2 and unlisted. When a new document's save under its id expects revision 0, then the reply is the deleted id's refusal, the description's row and graph are unchanged, the document is not listed and its row stays at 2 | L4 | TD-168, point 5 | `MultiAggregateCommandsTest.savingANewDocumentUnderAnIdWhoseRowALostTombstoneLeftLiveIsRefused` passes | negative |
| F15-T2 | Given the same deletion with the row live at 2, when it is delivered again to another member and a write moves the row before each of the three attempts, then it is answered 200 and the row is left live at 5. When it is delivered once more, then the row is tombstoned and the graph is empty | L4 | TD-171 | `MultiAggregateCommandsTest.aDeletionDeliveredTwiceMoreAfterALostTombstoneWhoseFirstRedeliveryLosesStillRemovesTheRow` passes | negative |
| F15-T3 | Given body A `_:x ex:p _:y .` and body B `_:x ex:p _:x .`, when each is digested as a save, then the digests differ | L1 | two bodies that connect blank nodes otherwise are two requests, whatever PDD-24 decides | `CodecTest.aBlankNodeThatNamesAnotherAndOneThatNamesItselfDigestApart` passes | negative |
| F9-T1 | MSA-F6's F6-T3, unchanged: a new document's save whose description step loses is told to send again, and its resend completes it at revision 1 | L4 | the exception | passes | positive |
| existing | the rest of `MultiAggregateCommandsTest`, `DocumentsTest`, `ReceiptsTest` and `CodecTest` | L4, L3, L1 | theirs | pass, unchanged | |

**F15-T2 takes every attempt of the first redelivery.** With one attempt lost, the next round in the same call removes the row, and the second delivery is never needed. With all three lost, the second delivery runs the same three transaction ids again, `urn:txn:{command id}/resent/1-again-{round}`, so it is the case TD-171 asks about. It passed on the unchanged code: a tombstone whose guard fails leaves no claim on its transaction. To show the test can fail, a probe made every repeated attempt run under a transaction that already holds a claim, the deletion's own first step, and the test failed, below. The probe was reverted.

**F15-T3 passed on the unchanged code,** since MSA-F14's labelling already tells the two bodies apart. It holds the behaviour against the break a probe on macOS made, under which no test failed: each blank node's own quads written with itself and every other blank node as one label. Under that break, A's two nodes each read `_:self ex:p _:self`, and so does B's one node, so both bodies give one equal line. The test states behaviour only, so it holds under RDFC-1.0 or a ground body.

## The one command

`mise run check:config-studio`

## What was run, in full

Run on 2026-11-23. Each Maven run is `mise exec -- mvn -f platform/pom.xml -pl <module> -am test -Dtest=<classes> -Dsurefire.failIfNoSpecifiedTests=false`, its output read in full from a file.

| Command | Result |
|---|---|
| `mise run build:config-studio-assets`, first, since the worktree had no staged profile and every test of `MultiAggregateCommandsTest` failed with "Not found: .../.build/config-studio/persistence/profile.ttl" | exit 0, "staged .../.build/config-studio" |
| `-pl config-studio-service`, `MultiAggregateCommandsTest,CodecTest`, on the unchanged code | `CodecTest` "Tests run: 3, Failures: 0". `MultiAggregateCommandsTest` "Tests run: 11, Failures: 1". F15-T1 at line 509: "expected: <Reply[status=400, revision=0, message=the document was deleted, so its id cannot be used again]> but was: <Reply[status=200, revision=1, message=]>". F15-T2 and F15-T3 passed. BUILD FAILURE |
| the same, with the brief's rule built as written, with no exception | "Tests run: 11, Failures: 1". F9-T1 at line 268: "expected: <Reply[status=200, revision=1, message=]> but was: <Reply[status=400, revision=0, message=the document was deleted, so its id cannot be used again]>". F15-T1 passed |
| `-pl config-studio-service`, `MultiAggregateCommandsTest,CodecTest,DocumentsTest,ReceiptsTest`, after the change | `CodecTest` 3, `DocumentsTest` 9, `MultiAggregateCommandsTest` 11, `ReceiptsTest` 10, "Tests run: 30, Failures: 0, Errors: 0". BUILD SUCCESS |
| probe for TD-171: `Retired.again` gives the deletion's first step's transaction, `urn:txn:{command id}/1`, which holds a claim. `-pl config-studio-service`, `MultiAggregateCommandsTest` | "Tests run: 11, Failures: 5". F15-T2 at line 546: "the second redelivery removed the row ==> expected: <Optional.empty> but was: <Optional[5]>". The other four are the two tests of MSA-F7 and the two of MSA-F11, each of a lost tombstone. Reverted |
| probe for the digest: `Codec.digest` writes every blank node in a node's own quads as `_:self`. `-pl config-studio-core`, `CodecTest` | "Tests run: 3, Failures: 1". F15-T3 at line 35: "x names y, then x names itself ==> expected: not equal but was: <af1a383664ed1939f4c79c5389319e610c78e94af64872bcc38ebe2fd5091c15>". MSA-F14's two tests passed under the break. Reverted, and `git diff` on `Codec.java` printed nothing |
| `mise run check:config-studio` | exit 0, "Finished in 122.93s". pytest "159 passed, 24 warnings". JUnit 259 tests across the studio's modules with 0 failures, 0 errors and 0 skipped (authoring 9, core 27, service 201, transforms 2, writer 20), read from the run's surefire reports, every one written by this run. The browser checks "Tests 121 passed (121)". `check:authoring-domain`, a dependency, "Tests 21 passed (21)" |

## Deliberate non-coverage

- **A part's save.** A part is never tombstoned while its workspace lives, and a lost part tombstone needs the workspace deleted, after which a save is not found. As in MSA-F9.
- **A live, unlisted row of another command's unfinished creation.** Where a save's description step lost (F6-T3) and a save under the same document id with another command id follows, it is now refused with the deleted id's words, although nothing was deleted. Before, it was answered 200 with its body discarded. No test sends it. A question below.
- **The model.** The states TD-166, TD-169 and TD-170 record are MSA-I14's, which machine S models next in `tools/models/multi-store-protocols`. This slice changes no guard.

## Doc delta

None outside this pack. For the coordinator:

- TD-168 is paid by this slice. TD-171 is answered: a lost attempt leaves no claim, and F15-T2 holds it, so the row can close with no change to the transaction ids.
- MSA-F11's pack rests on "a deleted id is never used again", which now holds.
- ADR-A149's addendum, point 5, is Proposed. A draft of the exception, for the maintainer:

> 5. **An id whose row exists is never created again.** A save that creates a document refuses an id that has a version row, live or tombstoned, unless the row is the one the same command created on an earlier delivery whose description step lost, which its resend completes. A document whose removal is not finished has a live row the description does not list, and a creation under its id would otherwise write nothing, list the document again and show what the deletion removed. Point 4 relies on this rule, since it removes whatever row a deleted id still has.

## Index report

- `mise run graph:ask -- find a save that creates a document under an id whose version row exists live or tombstoned` answered TD-168 first, at 0.77, and ADR-A149's addendum sixth, at 0.70. Enough to act on.
- One gap recorded against ADR-A149, at `Writer.java:703`: the addendum's point 5 does not state that a resend completes its own creation, which MSA-F6 and MSA-F9 hold. The decision's own text, point 5, would carry it once amended.

## For the maintainer

- **The exception for the command's own creation.** (a) As built: a row whose create is the command's own first step is its own, and the resend completes it, so F9-T1 holds as verified. It couples the check to the document's write being the command's first step. (b) Point 5 as written: every row refuses, so a save whose description step lost is told to send again and its resend is then refused, leaving its document's row live and unlisted for good, a state of TD-167's kind. F9-T1 would change to assert the refusal. (c) MSA-I14's whole-command guard would remove the partial state, and the exception with it. We lean to (a) until MSA-I14 is decided. Which?
- **The words of the refusal for a row no deletion left.** As above, a live, unlisted row of another command's unfinished creation gets "the document was deleted, so its id cannot be used again". Keep it, since a sender cannot tell the cases apart and either way must choose a new id, or give it words of its own?
