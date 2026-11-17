<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: MSA-I9, the super stream under failover and partition

**Unit:** [`multi-store-architecture`](../status/multi-store-architecture.md)
**Plan:** [multi-store-architecture](../plans/multi-store-architecture.md), MSA-I9
**Machine:** a Windows laptop, Docker Desktop 29.8.0, a three-node cluster of `rabbitmq:4-management-alpine` (RabbitMQ 4.4.0), stream-client 1.12.0 and amqp-client 5.37.0 on `eclipse-temurin:25-jre`. **Placement:** T0, public. Transport behaviour, nothing domain-specific.
**Status:** authored and run, not accepted. The maintainer's review is the sign-off.

## Scope

- `spikes/multi-store-stream-probes/`, a Maven project of probe programs and PowerShell scripts that start the cluster, run each probe, cut or kill a consumer or a broker node, read the streams back and analyse the logs. The consumer is built as the studio's `StreamWriter` is, with the same group name, offset specification, tracking strategy, flow strategy, batch limit and offset storing.
- Three probes. P1, two consumers in one group while one is killed or cut from the network, run once killed and five times cut. P2, publisher deduplication with and without a named producer. P3, offsets across a consumer stop and across the loss of a broker node that leads partitions.
- Out of scope. Any change to the studio, and any network fault other than `docker network disconnect`.

## Result in one paragraph

The transport gives what the sketch's serialised-writer row assumes of it once the row's own caveat holds, and the studio's client code gives less. The sketch's §4.2 already says a single active consumer is a liveness device and never a safety one, and P1 confirms it. A consumer cut from the network applied 6 messages up to 5.95 s after its replacement began receiving, and after a heal both consumers had applies in flight on one partition for up to 42 s summed over batches. Takeover took 0.3 s when the broker saw the connection drop, 21 to 23 s with a 10 s heartbeat and 151 s at the default. The studio publishes with no named producer, so the broker deduplicates nothing and a replay duplicates every message, which leaves idempotence to the store's guards as the row requires. The finding that matters most is in P3. `MessageHandler.Context.storeOffset()` on a super stream consumer stores, for every other partition the consumer holds, the offset last *received*, and the studio's handler only enqueues. A stop before a batch is applied therefore skips confirmed writes on the other partitions, 36 in one run, and storing through `Environment.storeOffset` with the applied offset skipped none. With the store's guards and offsets stored as applied, the row stands as ordered and eventually applied, each write at most once in effect.

## Findings

| ID | Finding | Evidence |
|---|---|---|
| MSAI9-01 | A single active consumer is not a fence. A cut consumer applies what it holds after its replacement has begun receiving | P1 run 3, 6 applies up to 5.95 s after takeover |
| MSAI9-02 | After a heal the group rebalances and two consumers have applies in flight on one partition, and older sequence numbers are applied after newer ones | P1 runs 1, 2, 4 and 5, up to 16 overlapping batches and 20 older-after-newer applies |
| MSAI9-03 | Takeover time is set by how the broker learns of the loss: 0.3 s for a dropped connection, the heartbeat for a silent one | P1, 315 ms killed, 21 to 23 s at 10 s, 151 s at the default |
| MSAI9-04 | The studio uses no named producer, so the broker deduplicates nothing. An unnamed replay left 892 extra copies of 2000 and the studio's double publish stored every message twice | P2 cases b and d |
| MSAI9-05 | A named producer deduplicates across a kill and replay. A same-name producer restarting from a lower publishing id is dropped silently though confirmed, two live producers sharing a name interfere, and `getLastPublishingId` of a super stream producer reports one partition's id | P2 cases a, a2, c1b and c2 |
| MSAI9-06 | `Context.storeOffset()` on a super stream consumer stores the last received offset of every other partition the consumer holds, so the studio's `StreamWriter`, which enqueues in the handler and stores after the batch applies, can skip confirmed writes after a stop | P3a `p3-before-apply`, 36 skipped, P1 kill run 18 skipped, and `SuperStreamConsumer.ManualOffsetTrackingMessageHandler` in the stream-client 1.12.0 sources, which calls `state.consumer.store(state.offset)` for each other partition |
| MSAI9-07 | Storing through `Environment.storeOffset(reference, stream, offset)` with the applied offset skips nothing | P3a `p3-before-apply-env`, 0 skipped |
| MSAI9-08 | No confirmed message was lost when a broker node leading partitions was killed. The publisher saw one batch time out, the consumers resubscribed and replayed from the stored offset | P3b, 0 of 15,008 and 0 of 15,346 missing |

## Commands and results

Run from `spikes/multi-store-stream-probes` on 2026-11-17, the jar built with Maven 3.9.16.

| Command | Result |
|---|---|
| `.\scripts\cluster-up.ps1` | three nodes clustered, streams replicated on all three |
| `.\scripts\p1.ps1 -Mode kill -Run p1-kill-1` | takeover 315 to 322 ms, 18 skipped |
| `.\scripts\p1.ps1 -Mode partition` five times, as in the README | the P1 table, takeover 21 to 151 s, overlaps in four of five runs |
| `.\scripts\p2-dedup.ps1` | the P2 table |
| `.\scripts\p3-offsets.ps1` at `before-apply`, `before-store` and a pause, and at `before-apply` with `-StoreVia env` | 36 skipped through the context, 0 through the environment |
| `.\scripts\p3-leader-kill.ps1 -KillNode 2` and `-KillNode 1` | leaders moved in about 7 s and 16 s, 0 confirmed messages missing |
| `.\scripts\cluster-down.ps1` | no container, network or volume named `msa-i9-` remains |

## Adversarial probes

1. The zombie case needs a consumer that holds a batch across the cut. With batches of 300 ms no apply after takeover was seen, and with 15 s one was. The probe reports both, so a short batch does not stand for a fence.
2. P3a was run with a debug trace (`results/p3-dbg/c1.debug.txt`) to find which call stored the unapplied offsets, and the cause was then read in the client's own source.
3. The leader-kill probe was run against two different nodes, so the result does not rest on one node's leaders.

## Decisions taken

- **The probes reproduce the studio's consumer rather than running the studio.** The studio's writer needs the store and the service. The probe keeps every setting of the consumer and replaces the store write with a sleep.
- **A partition is `docker network disconnect`.** It closes the connection rather than dropping packets silently, so an `iptables` drop may take longer to notice. The heartbeat results bound that case.

## Open matters

- MSAI9-06 is a defect in running code that can leave confirmed writes unapplied after a writer stops, with the caller left at its timeout. It is for the maintainer to triage, and this slice changes no code. MSAI9-07 is the mitigation the probes support.
- Most cases ran once, and only the partition probe was repeated. The figures are observations, not distributions.
- Only RabbitMQ 4.4.0 and stream-client 1.12.0 were tested, with two consumers.
- The Docker VM clock is about 155 ms off the host, so overlaps shorter than that are not resolved.
- What MSA-I6's model X1 must keep follows from MSAI9-01, MSAI9-02 and MSAI9-06: redelivery, reordering after a rebalance and a writer that outlives its turn.
