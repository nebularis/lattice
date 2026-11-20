<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSA-F1, the stream writer stores only offsets it has applied

**Unit:** [`multi-store-architecture`](../status/multi-store-architecture.md)
**Plan:** [multi-store-architecture](../plans/multi-store-architecture.md), MSA-F1, from finding MSAI9-06 of [MSA-I9](MSA-I9.md)
**Machine:** machine S, Windows, Java 25 through mise, Maven 3.9.16, Docker Desktop with `rabbitmq:4-management-alpine` (RabbitMQ 4.4.0), stream-client 1.12.0. **Placement:** T0, public. The studio's store writer, nothing domain-specific.
**Status:** built 2026-11-18, not verified.

## Invariant

A confirmed write is applied before any offset at or past it is stored, so a writer that stops at any point leaves its partitions to a successor that resumes no later than the first unapplied message. The stream client's super-stream `MessageHandler.Context.storeOffset()` breaks this, because it also stores, for every other partition the consumer holds, the offset that partition last received, and the studio's handler only queues what it receives (MSAI9-06, read in the client's `SuperStreamConsumer` 1.12.0). The writer now stores, for each partition a batch touched, the offset of the last message it applied, through `Environment.storeOffset(reference, stream, offset)` under the group's reference, which [MSA-I9](MSA-I9.md)'s MSAI9-07 found skips nothing.

## Change

- `platform/config-studio-writer/.../StreamWriter.java`. The batch's application is a package-private static `apply(batch, writer, replies, offsets)`, so it is tested without a broker. It replies to each message, then stores the highest applied offset of each partition through `Offsets`, then marks the batch processed. `offsets(environment)` gives the production store, `environment.storeOffset(GROUP, stream, offset)`. The retry of a failed batch is unchanged, and is MSA-F2's.
- `StreamWriterTest.java`, a new test with a fake context that behaves as the client's super-stream context does.
- `spikes/multi-store-stream-probes`. A writer mode, `--store-via writer`, in which `StudioWriterBridge`, in the writer's package, runs the probe's batch through the studio's own `StreamWriter.apply` and its `offsets`. The probe's pom depends on the installed writer and compiles for Java 25.

## Tests

| ID | Given / When / Then | Level | Invariant | Pass criterion | Kind |
|---|---|---|---|---|---|
| F1-T1 | Given a batch of offsets 10 and 11 on partition 0 and 5 on partition 1, with 12 on partition 0 and 40 on partition 2 received and waiting, when the batch is applied, then the stored offsets are 11 and 5 and nothing else, each message is replied to in order, and three are processed | L1 | the invariant | `StreamWriterTest.aBatchStoresTheOffsetItAppliedOnEachPartitionAndNothingItHasOnlyReceived` passes | negative |
| F1-T2 | the existing reply-to decoding | L1 | none new | `aReplyToKeptAsAnAmqp10AddressNamesItsQueue` passes | positive |
| F1-T3 | Given a three-node cluster and the probe consumer stopped before its third batch applies, when a second consumer takes over, then no confirmed message is skipped | L4 | the invariant, on a broker | `p3-before-apply-writer/analysis.txt` reports 0 confirmed but skipped | negative |

## Commands and results

Run on 2026-11-18.

| Command | Result |
|---|---|
| `mise exec -- mvn -q -f platform/pom.xml -pl config-studio-writer -am test -Dtest=StreamWriterTest -Dsurefire.failIfNoSpecifiedTests=false`, with the writer still calling `item.context().storeOffset()` | 1 failure, F1-T1: expected `{writes-0=11, writes-1=5}` but was `{writes-2=40, writes-1=5, writes-0=11}`, the unapplied offset of partition 2 stored |
| the same, after the fix | 2 tests, 0 failures |
| `mise run check:config-studio` | exit 0. pytest 157 passed, the Maven verify of the authoring, service, writer and transforms modules with core (229 JUnit tests, 0 failures, the writer's 11 among them), the browser checks 121 passed |
| `spikes/multi-store-stream-probes/scripts/p3-offsets.ps1 -Run p3-before-apply-writer -Point before-apply -StoreVia writer` | 0 confirmed but skipped, 0 extra applies, c2 resumed on each partition at the offset after the one c1 stored |
| the same with `-Run p3-before-apply-context-2026-11-18 -StoreVia context`, the control | 36 confirmed but skipped, as on 2026-11-17 |

The one command for the slice is `mise run check:config-studio`. The probe needs the cluster and is run as the spike's README says.

## Artefacts

- `spikes/multi-store-stream-probes/results/p3-before-apply-writer/` and `p3-before-apply-context-2026-11-18/`, each with `analysis.txt` and the stored offsets after the crash and after the restart.

## Deliberate non-coverage

- A writer that has lost its partition and still stores an offset. `Environment.storeOffset` stores whether or not the consumer is still active, so a writer that outlives its turn (MSAI9-01) can store an offset lower than its successor's, which makes the successor's successor read again what was applied. That is redelivery, answered from receipts, never a skip. It is a property for MSA-I6's model X1, not a test here.
- The retry of a batch the store refuses, MSA-F2.

## Decisions taken

- **The highest applied offset per partition, not the last one seen.** A batch holds a partition's messages in order, so the two agree, and the maximum says what is meant.
- **The probe runs the writer's code.** A copy of the algorithm in the probe would test the copy. The bridge class lives in the writer's package in the spike, so the writer exposes nothing new.
