<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSA-F10, the stream writer's thread survives a lost reply or offset, and a writer that stops leaves its group

**Unit:** [`multi-store-architecture`](../status/multi-store-architecture.md)
**Plan:** [multi-store-architecture](../plans/multi-store-architecture.md), MSA-F10, from finding MSAF2-01 of the review of 2026-11-19, as section 4.7 of the [machine S brief of 2026-11-19](../notes/machine-s-brief-2026-11-19-multi-store.md) states it
**Machine:** machine S, Windows, Java 25 through mise, Maven 3.9.16, stream-client 1.12.0. **Placement:** T0, public. The studio's stream writer, nothing domain-specific.
**Status:** built 2026-11-19, not verified. The three cases are the review's leaning, on which the maintainer has not ruled. Two cases that do not fit are below.

## Invariant

A writer that is a member of the group `lattice.studio.writers` has a thread that applies its partitions. Before this slice, `StreamWriter.run` caught only an interruption. A reply sent on a closed channel throws a runtime exception, and storing an offset can throw too. Either ended the thread while the consumer stayed in the group, so its partitions were held and nothing applied them (MSAF2-01).

| What fails | What the writer does now | Who applies the partition's next write |
|---|---|---|
| a reply, with any runtime exception | logs a warning naming the stream and offset, and goes on with the batch | this writer. The sender reads the write's receipt after its wait |
| storing a partition's offset, with any runtime exception | logs a warning naming the offset and stream, and goes on with the other partitions and the batch | this writer. The next batch stores a later offset. A write delivered again is answered from its receipt |
| anything else that escapes the loop, a runtime exception or an `Error` | logs an error that the writer stops and leaves its group, closes the consumer and ends the thread | another member, to which the group gives the partition |

An interruption, which only `close()` makes, still ends the thread quietly. `close()` closes the consumer as before.

The writer's state is readable from the object, for the unit [component-administration](../plans/component-administration.md)'s ADM-1. No endpoint reads it.

- `threadAlive()`, whether the thread that applies the writer's batches is running.
- `storedOffsets()`, for each partition, the offset this writer last stored for it since it started, as a copy. An offset whose store failed is not in it.

## Change

- `platform/config-studio-writer/.../StreamWriter.java`.
  - `apply` catches a runtime exception from each reply and from each partition's offset store, and logs it.
  - `run` catches a runtime exception or an `Error` that escapes a batch, logs the writer stopping, and closes the consumer. A failure to close is logged.
  - A package-private constructor takes the waiting queue, the consumer, the writer function, the reply consumer, the `Offsets` and the retry interval, so a test drives the thread with fakes. The public constructor builds the consumer and passes the production functions to it, as before.
  - The `Offsets` the thread uses records each offset stored in a map, after the store returns. `threadAlive()` and `storedOffsets()` read the thread and the map. They are public, since ADM-1 may read them from another module.
  - The class comment names the three cases.
- `StreamWriterTest.java`, three tests and a fake consumer that records whether it was closed.

## Tests

| ID | Given / When / Then | Level | Invariant | Pass criterion | Kind |
|---|---|---|---|---|---|
| F10-T1 | Given a running writer whose reply to offset 1 throws the AMQP client's `AlreadyClosedException`, when offset 1 is applied and then offset 2 arrives on the same partition, then offset 2 is applied and stored by the same writer, its thread is alive, `storedOffsets()` is `{writes-0=2}` and the consumer is open | L1 | the first row | `aReplyThatCannotBeSentIsLoggedAndThePartitionsNextWriteIsApplied` passes | negative |
| F10-T2 | Given a running writer whose store of offset 1 throws a `StreamException`, when offset 1 is applied and then offset 2 arrives on the same partition, then offset 2 is applied and stored by the same writer, its thread is alive, `storedOffsets()` is `{writes-0=2}` and the consumer is open | L1 | the second row | `anOffsetThatCannotBeStoredIsLoggedAndThePartitionsNextWriteIsApplied` passes | negative |
| F10-T3 | Given a running writer whose writer function answers fewer replies than it was given, when a write arrives, then the thread ends, the consumer is closed, so a group would give the partition to another member, and `threadAlive()` is false | L1 | the third row | `aFailureThatEscapesTheLoopClosesTheConsumerSoTheGroupMovesThePartition` passes | negative |
| existing | MSA-F1's, MSA-F2's and MSA-F8's tests of `apply` and the reply-to decoding, unchanged | L1 | theirs | pass | |

Each test waits for its condition for at most 5 s and fails with the message its row names.

## Commands and results

Run on 2026-11-19.

| Command | Result |
|---|---|
| `mise exec -- mvn -q -f platform/pom.xml -pl config-studio-writer -am test -Dtest=StreamWriterTest -Dsurefire.failIfNoSpecifiedTests=false`, on the unchanged code | 6 tests, 0 failures |
| `mise exec -- mvn -f platform/pom.xml -pl config-studio-writer -am test -Dtest=StreamWriterTest -Dsurefire.failIfNoSpecifiedTests=false`, with the constructor and the accessors and without the three catches | 9 tests, 3 failures. F10-T1: "the partition's next write was not applied after a reply could not be sent". F10-T2: "the partition's next write was not applied after an offset could not be stored". F10-T3: "the consumer was not closed, so the writer keeps its partitions with no thread applying ==> expected: <true> but was: <false>" |
| the same, after the fix | 9 tests, 0 failures, BUILD SUCCESS |
| `mise run check:config-studio`, first run | exit 1. `check:authoring-domain` failed: "Couldn't find the node_modules state file", since this worktree had no `node_modules` |
| `mise run bootstrap:frontend` | exit 0, Yarn 4.6.0, "Done in 35s 350ms" |
| `mise run check:config-studio` | exit 0. pytest "158 passed". JUnit 247 tests across the studio's modules with 0 failures and 0 errors (authoring 9, core 24, service 194, transforms 2, writer 18), 256 with mork-transforms and platform-outbox, which the run also builds. The browser checks "Tests 121 passed (121)" |

The one command for the slice is `mise run check:config-studio`.

**Why the tests could not fail on the unchanged code.** They need the constructor that takes a consumer and functions, and the accessors, which the unchanged code lacks, so they would not compile. The constructor and the accessors were written first, with the loop and `apply` unchanged, and the failures above are from that state.

## Where a case does not fit

- **A store of offsets that fails for good.** The writer goes on applying and replying, and logs a warning on every batch, but the stored offset does not move. Nothing is lost. A member that takes the partition over reads again every write since the last offset stored, each answered from its receipt. That cost grows for as long as the store fails, and only the log says so. `storedOffsets()` shows the offset frozen, which ADM-1 can read. Stopping the writer instead would move the partition to a member whose store may fail the same way. Built as stated, for the maintainer to rule on.
- **A reply channel that is closed for good.** The reply connection has the AMQP client's automatic recovery on, which reopens a channel after the connection is lost. A channel the broker closed on its own, with the connection still open, is not reopened, and after it closes every reply is lost. Each service request then waits for its timeout and reads the receipt. The writer goes on applying, which is the case as stated, but every caller pays the wait. Reopening such a channel is not built here.
- **An `Error` from a reply or a store** is not caught by the first two cases, which catch runtime exceptions. It reaches the third, so the writer stops and leaves its group. The brief's "whatever was thrown" for a reply could mean an `Error` too. Catching one there would keep a writer running after, for example, an out-of-memory error, so this slice does not.

## Deliberate non-coverage

- A broker. No test shows a real group giving a closed consumer's partitions to another member. The fake consumer records the close. The probe of [MSA-F1](MSA-F1.md) on the three-node cluster could show it, and was not run.
- A write delivered again answered from its receipt. That is the store writer's existing behaviour, tested in `ReceiptsTest.aRedeliveredCommandIsAnsweredFromItsReceiptAndAppliedOnce`. The fakes here have no receipts.
- A writer stopped and then closed calls the client's `Consumer.close()` twice. The fake accepts it. No test runs the stream client's own close twice.
- Group membership and the partitions a writer holds, which ADM-1 also names, are not exposed. The brief asks for the thread and the offsets only.

## Decisions taken

- **The state is the offsets this writer stored, not the broker's.** `storedOffsets()` records an offset after its store returns, so it says what this writer last stored, which may lag the broker's where another member has since stored a later one. It holds only partitions this writer has stored for since it started.
- **The accessors are public** and named after ADM-1's row, "offset last stored for each, thread alive".
