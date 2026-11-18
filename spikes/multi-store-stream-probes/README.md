<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Spike: the super stream under failover and partition (MSA-I9)

**Status:** a spike, not production. It defines no interface and changes no tool. Nothing in `tools/`, `benchmark/` or `platform/` imports it.

## Question

The studio writes through a RabbitMQ super stream consumed by a single active consumer (SAC) group. This spike asks whether the transport alone gives a serialised writer per partition (one consumer applies a partition's messages at a time, in order, each once) when a consumer dies, is cut off, or a broker node leading some partitions dies. The falsifier: if two consumers can apply messages of one partition at overlapping times, or one can apply after another has begun receiving, SAC is not a fence and the stores must supply the guarantee.

## What is modelled

The consumer follows the studio's: `superStream`, `singleActiveConsumer()`, `name("lattice.studio.writers")`, `offset(first())`, `manualTrackingStrategy()`, `creditWhenHalfMessagesProcessed`. A handler enqueues. One `store-writer` thread takes batches of up to 64 messages, applies them (a sleep standing in for the store write, `--message-ms` per message, `--batch-ms` per batch), calls `storeOffset()` with the last offset per stream, then `processed()`. The publisher is AMQP 0.9.1 with confirms, no named producer, no deduplication (the idempotence is meant to come from store guards), 8 partitions.

Versions: stream-client 1.12.0, amqp-client 5.37.0, slf4j 2.0.20, shade jar built for release 21, `rabbitmq:4-management-alpine` (RabbitMQ 4.4.0, Erlang 29.1.2), clients in `eclipse-temurin:25-jre`, Docker Desktop 29.8.0 on Windows. Three broker nodes `msa-i9-rmq1..3` in the network `msa-i9-net`. Every stream is replicated on all three. The Docker VM clock is about 155 ms off the host clock. Timestamps within one probe run come from one side and are compared against fault times taken before the Docker command.

## Layout and how to run

```powershell
Set-Location spikes\multi-store-stream-probes
.\scripts\cluster-up.ps1                                  # builds target\probes.jar if missing, starts the cluster and msa-i9-ctl
.\scripts\p1.ps1 -Mode kill -Run p1-kill-1
.\scripts\p1.ps1 -Mode partition -Run p1-partition-2 -HeartbeatS 10 -BatchMs 300
.\scripts\p2-dedup.ps1
.\scripts\p3-offsets.ps1 -Run p3-before-apply-env -Point before-apply -StoreVia env
.\scripts\p3-leader-kill.ps1 -Run p3-leader-kill-2 -KillNode 2
.\scripts\cluster-down.ps1
```

Every Docker object is prefixed `msa-i9-`. Each run writes `results\<run>\` with an `analysis.txt` (the numbers below), the harness log, and the client logs (large ones gzipped). The harness and client logs are not committed, and the analyses, broker views, stored offsets and the debug trace of `p3-dbg` are. `analysis.txt` columns are described at the head of each table it prints. Do not pipe a probe script into `Select-Object -First N`. It ends the pipe before the final analysis. Use `-Last N`.

The Java probes (`src/main/java/org/nebularis/lattice/probes/msa/`) are `Sac` (consumer), `Pub` and `Dedup` (publishers), `Offsets` and `Analyze` (read-back and analysis), `Topo` (declare, delete, `--spread`), `Log` (JSON lines).

## P1: stop and partition of one of two consumers

Two consumers c1 and c2 in one group over 8 partitions. They split 4 and 4 (c1 receives 0, 2, 4, 6 and c2 1, 3, 5, 7). The studio's publisher writes at 150 msg/s. Kill is `docker kill` of c1. Partition is `docker network disconnect` of c1 from the broker network for the cut time, then reconnect.

| run | settings | takeover | c1 applies after c2 began receiving | extra applies | overlapping batches (total overlap) | skipped | confirmed |
|---|---|---|---|---|---|---|---|
| kill-1 | batch 5000 ms | 315 to 322 ms | 0 | 0 | 0 | 18 | 11428 |
| partition-1 | default heartbeat, batch 300 ms | 151.0 to 151.1 s | 0 | 23 | 6 (1247 ms) | 6 | 32469 |
| partition-2 | heartbeat 10 s, batch 300 ms | 21.05 to 21.09 s | 0 | 30 | 14 (5056 ms) | 18 | 12932 |
| partition-3 | heartbeat 10 s, batch 15000 ms, cut 30 s | 23.31 s | 6 (last 5950 ms after takeover, on partition 0) | 6 | 0 | 0 | 24807 |
| partition-4 | heartbeat 10 s, batch 5000 ms, cut 20 s | 22.22 to 22.25 s | 0 | 12 | 12 (17,784 ms, partition 1) | 0 | 18932 |
| partition-5 | as 4 | 22.50 to 22.51 s | 0 | 24 | 16 (42,258 ms) | 0 | 18935 |

"Extra applies" are applies of a sequence number already applied. Older-after-newer was 5 (run 3), 10 (run 4), 20 (run 5). "Skipped" counts confirmed messages never applied by anyone (see the stored-offset finding below).

- Takeover is fast when the broker sees the TCP connection die (about 0.3 s) and slow when it does not: about 21 to 23 s with the client heartbeat set to 10 s, about 151 s at the default.
- Run 3 is the zombie: with a 15 s batch c1 was still applying a batch it held when c2 began receiving, and applied 6 messages up to 5.95 s after takeover.
- In runs 1, 2, 4 and 5 the overlaps are after the heal. When c1 reconnected it rejoined, the group rebalanced, and for a while both consumers had applies in flight on a partition (partition 3 had 12 overlapping batches over 32.1 s and partition 7 had 4 over 10.1 s in run 5).
- The Javadoc says partitions are spread over consumers. Observed 4 and 4 for two consumers.

## P2: deduplication and named producers

2000 messages per case over 4 partitions (id mod 4), kill of the first producer after 800 confirmations, 5 ms between sends. Read back with `count`.

| case | what | stream entries | distinct | extra copies | missing |
|---|---|---|---|---|---|
| a | named producer, killed, restarted with the same name, full replay from 0 | 2000 | 2000 | 0 | 0 |
| a2 | named, restart resumes from `getLastPublishingId`+1 | 2000 | 2000 | 0 | 0 |
| b | unnamed producer, killed, full replay | 2892 | 2000 | 892 | 0 |
| c1 | two live producers with one name, odd and even ids (disjoint partitions) | 2000 | 2000 | 0 | 0 |
| c1b | two live producers with one name, both on partition 0 (500 expected, 250 confirmations logged by each) | 251 | 251 | 0 | 249 of the 500 (the range count of 1749 includes ids never sent) |
| c2 | sequential, same name: ids 1000..1199 first, then ids 0..199 | 200 | 200 (ids 1000..1199) | 0 | ids 0..199 of the second producer |
| d | AMQP publisher, every message published twice (the studio's double publish) | 200 | 100 | 100 | 0 |

- The studio uses no named producers, so broker-side deduplication does not apply to it: a replay duplicates (case b, 892 copies, and case d, every message twice). Idempotence has to come from the store guards.
- A named producer deduplicates within a partition across a kill and replay (a, a2).
- A same-name producer with a lower id is silently dropped though confirmed (c2: the second producer, ids 0..199, logged 200 confirmations, and the stream holds only ids 1000..1199). Two live producers sharing a name on one partition interfere (c1b: each logged 250 confirmations, 500 in all, but only 251 reached the stream). Case c1 showed no interference only because its partitions were disjoint.
- `getLastPublishingId` of a super stream producer reports one partition's id: 860 against a highest confirmed 863 (a) and 872 against 875 (a2). Resuming at `last-publishing-id`+1 is not generally safe across partitions.

## P3a: offsets across a consumer stop

c1 halts at batch 3 at a chosen point (`before-apply`, `before-store`, `after-store`) and c2 starts. The harness reads where c2 begins against where c1 had stored.

- Finding: `ManualOffsetTrackingMessageHandler.storeOffset()`, called from the studio's handler, also stores the received (not applied) offset of every other partition the consumer holds (`state.consumer.store(state.offset)` for partitions where the offset is non-zero, set once the user handler returns). The broker keeps the last value stored, so what survives depends on map order.
- `p3-before-apply`: 36 confirmed messages skipped (6 on each of partitions 2 to 7), and c2 began at offset 16 against 9 stored by c1 on those.
- `p3-before-store` and `p3-pause`: c2 began at 16 on 6 of 8 partitions against 9 stored by c1, so a stop before the store gives no redelivery for those partitions (those messages were applied, so nothing skipped).
- The P1 kill run skipped 18 for the same reason (6 each on partitions 2, 4, 6).
- Mitigation: `--store-via env`, `Environment.storeOffset(reference, stream, offset)` with the applied offset. `p3-before-apply-env`: 0 skipped, c2 began at 10 on all 8 partitions.
- `p3-dbg` is a debug-logging run kept for the client trace that located the cause.

## P3b: loss of a broker node that leads partitions

Leaders spread with `--spread` (partition i declared over a connection to node (i mod 3)+1, and a plain declare puts all 8 leaders on the node of the declaring connection, which was checked). Two consumers (offsets stored with `--store-via env`), publisher at 150 msg/s over AMQP with confirms, `docker kill` of a broker node, restart after 50 to 60 s. Read back all confirmed sequence numbers.

| run | killed node (leaders before) | leaders off the dead node after | publisher failures | confirmed | confirmed but not in the stream | stream entries / distinct | extra applies | older after newer | overlapping batches |
|---|---|---|---|---|---|---|---|---|---|
| p3-leader-kill-2 | rmq2 (partitions 1, 4, 7) | about 7 s (polling at 1 s) | 1 batch, `TimeoutException`, at +5.4 s | 15008 | 0 | 15075 / 15075 | 6 (partition 1) | 5 | 0 |
| p3-leader-kill-1 | rmq1 (partitions 0, 3, 6) | about 16 s | 1 batch, `TimeoutException`, at +5.3 s | 15346 | 0 | 15373 / 15373 | 12 (partition 0) | 10 | 0 |

- No confirmed message was lost. The one unconfirmed batch is the single missing id in each range (it did not reach the stream, so the publisher's retry is needed for it).
- No consumer lost group membership (no takeover): the consumers resubscribed their streams (c1 logged 14 subscribes against 8 at start in run 1) and resumed from the stored offset, which gives a replay of a few messages on the partition whose leader moved (extra applies 6 and 12) and older-after-newer applies in that replay.
- With the killed node holding the connection, the consumer's `storeOffset` timed out in `OffsetTrackingUtils` (warnings in `c1.container.txt` of run 1): the stored offset can lag the applied one at the moment of the fault.
- The restarted node rejoined as a follower for all its replicas (`cluster-after-restart.txt`). The leaders stayed where the election put them.

## Verdict on the falsifier

SAC is a liveness and assignment mechanism, not a fence.

- Takeover latency is about 0.3 s when the broker sees the connection die, about 21 to 23 s on a silent partition with heartbeat 10 s, and about 151 s at the default heartbeat. During that time nothing is applied to the partition.
- A zombie consumer applied 6 messages after the new consumer began receiving (P1 partition-3, last one 5.95 s after takeover).
- Overlapping batches of different consumers on a partition occurred in four of five partition runs, after a rejoin and rebalance, up to 42 s of overlap summed over batches.
- Re-delivery after a stop, a rejoin or a leader change produces extra applies and older-after-newer applies (up to 30 and 20 in these runs).
- The client's own offset storing can skip confirmed messages (36 and 18 in the runs above) unless the offset is stored through the environment with the applied offset.

So the transport gives less than a serialised writer row assumes. The stores need a fencing token or epoch, or guarded and idempotent writes (a per-source sequence guard that rejects stale or repeated sequence numbers), plus the offset storing through the environment.

## Doubts

- `docker network disconnect` is not a silent drop of packets. An iptables DROP variant might behave differently (the broker may see the reset of the connection earlier or later).
- The broker group view (`Get-GroupView`) samples only some partitions, and in P3b run 1 `broker-view-after.txt` is empty because it queries the node that was dead.
- The clock offset of the Docker VM is about 155 ms. Overlaps shorter than that are not resolved.
- A log line can be lost at SIGKILL, so apply counts at a kill can be short by the last second.
- Publisher confirmed ranges are flushed about once per second. Confirmations in the last second before the publisher was removed are not counted as confirmed.
- The overlap metric uses a batch's begin time to its log time. One writer thread per consumer serialises across that consumer's partitions, so an overlap can include time the batch spent behind another partition's batch.
- The apply speed (message-ms and batch-ms) is below the publish rate in several runs, so "not yet applied at the end" is a backlog (for example 10452 and 11714 in P3b), not a loss.
- Single runs for most cases. Only the partition probe was repeated (runs 4 and 5 differ in overlap, 17.8 s against 42.3 s), so the figures are not distributions.
- RabbitMQ 4.4.0 and stream-client 1.12.0 only. The Javadoc claim about spreading was checked on two consumers only.
