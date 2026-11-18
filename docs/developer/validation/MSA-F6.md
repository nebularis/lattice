<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSA-F6, a multi-aggregate command whose later guard fails

**Unit:** [`multi-store-architecture`](../status/multi-store-architecture.md)
**Plan:** [multi-store-architecture](../plans/multi-store-architecture.md), MSA-F6, from finding MSAI11-01 of [MSA-I11](MSA-I11.md)
**Machine:** machine S, Windows, Java 25 through mise, Maven 3.9.16, Jena 6.2.0 in memory. **Placement:** T0, public. The studio's writer, nothing domain-specific.
**Status:** built 2026-11-18, not verified. Tests only, no change to running code. Two findings are for the maintainer.

## Invariant under test

[ADR-A149](../../architecture/decisions/ADR-A149-publication-from-the-studio.md) decision 13 says a command that writes several aggregates orders its operations so that a guard failing part way leaves nothing a reader acts on, a version before its lineage, the parts before the description on creation, the description first on deletion. The brief adds that a resend completes the command. Each test makes the later operation's guard fail and not the earlier one's, by a write another writer makes just before the request, asserts that the earlier operation applied, and reads what a reader acts on and what a resend of the identical command does.

## Results

| Command | Interference | Reply | Nothing a reader acts on remains | A resend completes it |
|---|---|---|---|---|
| `publish` onto an existing lineage | another publication on the lineage | 400, publish again | holds. The lineage names the other version current and the command's nowhere, and the version's graph is reached by nothing | holds, 200 at revision 3, one event, and a third send answered from the receipt |
| `saveDocument` of a new document | `setAccess`, which replaces the description | 400 | holds. The description lists no document, and the document's graph and row are reached by nothing | holds, 200 at revision 1 with its title |
| `fence`, in `ReceiptsTest` already | `setAccess` | 400 | holds | holds |
| `create` | the description created directly by its generated operation, which no command does alone | 400, the workspace exists | holds for every state a command can reach. The interference writes a description without its baseline, which no command writes. Reached that way, the command's baseline is read as the other workspace's | does not, 400 again. Reachable only from the same unreachable state |
| `importing` | as `create` | 400 | as `create` | as `create` |
| `deleteDocument` | a save of the same document, moving its revision | 400, send it again | holds. The description no longer lists the document | **does not.** A resend is answered 404, since the description no longer lists the document. The document's row stays live at revision 2 and its graph stays, reached by no reader |
| `deleteWorkspace` | a save of a part, moving its revision | 200, since the receipt is guarded on the description's tombstone | holds. No workspace is found | **does not.** A resend is answered 200 from the receipt. The part's row stays live and its graph stays, reached by no reader |

## Findings for the maintainer

| ID | Finding | Why no code changed |
|---|---|---|
| MSAF6-01 | A deletion whose later tombstone fails, because a concurrent save moved the aggregate's revision, leaves that aggregate's graph and live row with nothing that reaches it, and no resend removes it. This holds for `deleteDocument` and `deleteWorkspace` | decision 13 holds, since no reader acts on what is left. Completing the deletion needs a choice the decision record owns: a tombstone whose guard does not read the revision, a sweep of rows no description reaches, or the port's unit with one guard. Recorded for the maintainer, as the brief asks where a fix is not obvious |
| MSAF6-02 | The new document's save answers "the document was deleted, so its id cannot be used again" when its description replace lost a race, because the reply compares the description's revision of the document, 0, with the expected 0 | the message misleads and the resend succeeds, so it costs a confused user and nothing stored. A fix needs the reply to read the document's own row, and is left with the finding |

## Tests

`platform/config-studio-service/src/test/java/org/nebularis/lattice/studio/MultiAggregateCommandsTest.java`, six tests, each named for what it shows.

| ID | Test | Level | Kind |
|---|---|---|---|
| F6-T1 | `createWhoseDescriptionGuardFailsLeavesItsBaselineUnderTheOtherDescriptionAndIsRefusedOnResend` | L4 | negative |
| F6-T2 | `importingWhoseDescriptionGuardFailsLeavesItsPartsAndDocumentsUnderTheOtherDescriptionAndIsRefusedOnResend` | L4 | negative |
| F6-T3 | `savingANewDocumentWhoseDescriptionGuardFailsLeavesAnOrphanDocumentGraphAndAResendCompletesIt` | L4 | negative |
| F6-T4 | `deletingADocumentWhoseTombstoneGuardFailsReadsAsDeletedAndLeavesTheGraphAndAResendIsNotFound` | L4 | negative |
| F6-T5 | `publishingWhoseLineageGuardFailsLeavesAnUnnamedVersionGraphAndAResendCompletesIt` | L4 | negative |
| F6-T6 | `deletingAWorkspaceWhosePartTombstoneGuardFailsReadsAsGoneAndLeavesThePartAndAResendDoesNotRemoveIt` | L4 | negative |

Each asserts the later guard failed and the earlier operation applied, so none passes by an interference that missed.

## Commands and results

Run on 2026-11-18.

| Command | Result |
|---|---|
| `mise exec -- mvn -q -f platform/pom.xml -pl config-studio-service -am test -Dtest=MultiAggregateCommandsTest -Dsurefire.failIfNoSpecifiedTests=false` | 6 tests, 0 failures |
| `mise run check:config-studio` | exit 0. pytest 158 passed, JUnit 241 tests across the studio's modules with 0 failures (the service's 192), the browser checks 121 passed |

The one command for the slice is `mise run check:config-studio`.

## Deliberate non-coverage

- The patch-log drops a deletion makes are not guarded, and what they drop when the tombstone fails is not asserted.
- Commands that write one aggregate, and jobs, which are written outside the profiles.

## Doc delta

The port note, [MSA-I11-logical-port.md](../notes/multi-store/MSA-I11-logical-port.md), now cites decision 13 for MSAI11-01, says that a unit on the port is all or nothing so a studio command moved onto it gives its operations one guard, and points here.
