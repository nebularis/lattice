<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# `tools/models/multi-store-protocols/`

TLA+ models of the protocols behind rows of the multi-store catalogue (sketch section 4.2). They are design-time evidence for the formal-methods track H plan's FMH-5, protocol model A, and for MSA-I6, models X1 to X4. They are not shipped code and not a proof. TLC checks every state of a small finite instance, so a result holds for the stated constants only.

## Models

### `ModelA_GuardedCas.tla`

A guarded compare-and-set on one version row. Each writer reads the row, then issues one request meaning "if the row equals the value read, set it to that value plus one, apply the payload and write the receipt keyed by the target and the new value". The constant `Isolation` selects what the store makes of the request.

| Value | Meaning |
|---|---|
| `Atomic` | The guard and the write are one atomic step, as a SPARQL request on a serialisable store or an SQL row lock gives. |
| `SnapshotNoWWDetect` | The guard is evaluated against a snapshot in one step and the write commits in a later step, and the store detects no write-write conflict, so the commit is unconditional. |

`NoLostUpdate` is an invariant. No two applied writes share an expected value, and no two receipts share a key.

What the model abstracts away.

- Each writer makes one attempt and is done. A writer whose guard fails does not retry.
- There is one target, so the receipt key is the new version alone.
- The payload is the writer's identity. Its content and the aggregate's triples are not modelled.
- Failures of the store and of the writer are not modelled. Model A is about isolation only.

### `X1_SerialisedApply.tla`

One serialised writer per key applying a stream partition to two stores, A then B. The stream holds `K` commands, published and confirmed one at a time. A writer incarnation receives commands in order, up to `W` ahead of the last one it finished. For each command it applies to A, then to B, then stores an offset.

The store side follows the guarded command of the four-operations note. A store applies command `c` only when its version row is `c - 1` and computes the successor itself. A command with a receipt is answered `Duplicate` before the guard is tried, and a command whose guard fails with no receipt is answered `Conflict` and changes nothing. A `Conflict` from A skips B for that command. The writer goes on after either outcome, so a rejected command is not retried.

A writer may crash at any step and loses what it held in memory. The next incarnation resumes from the stored offset, where the last writer wins and the offset can move backwards. With `Zombie` true, a successor may also start while its predecessor is alive and still acting, which is the broker behaviour found in the probes (a cut consumer applies after its replacement has begun, and a rebalance re-applies). No fence is modelled, so the guard in each store is the only safety device.

| Constant | Meaning |
|---|---|
| `K` | Number of commands in the partition. |
| `W` | Window an incarnation may receive ahead of the last command it finished. |
| `MaxCrashes` | Largest number of crashes in a behaviour. The model has `MaxCrashes + 1` incarnations, so one always survives. |
| `Zombie` | Whether a successor may start while its predecessor is alive. |
| `OffsetMode` | `Applied` stores the seq of the command just applied to both stores. `Received` stores the highest seq the incarnation has received, which can exceed the last applied by up to `W - 1`. This is the defect found in the broker probes, where the context call stored received offsets. |
| `WithReader` | Whether the one reader of A then B is enabled. The reader reads the version of A and later, in a separate step, the version of B. |

Properties.

| Name | Kind | Statement | Expected |
|---|---|---|---|
| `EachAppliedOnceInEffect` (S1) | invariant | No command's effect is applied to a store more than once, and a store's version row equals the number of commands applied. | holds when guarded |
| `VersionStepsByOne` (S1) | action property | A version row only stays or rises by exactly 1. | holds when guarded |
| `OrderPerKey` (S2) | invariant | Each store applies commands in seq order. | holds when guarded |
| `AThenB` | invariant | B is never ahead of A. An addition, since every writer applies A first. | holds |
| `EventuallyApplied` (L1) | temporal | Every confirmed command is eventually received by both stores, under weak fairness on publication, on each live incarnation's steps and on the start of a successor after a crash. A crash and a start while the predecessor is alive are never forced. | holds with `Applied`, violated with `Received` |
| `NoTornRead` (T1) | invariant | A reader of A then B never sees them at different versions. | fails in every configuration |
| `NoStrandedHalfApply` | invariant | After a crash with no incarnation alive, A and B are at the same version. An addition that isolates the crash window of the sketch's sequence diagram. | fails |

What the model abstracts away.

- Publication is not modelled beyond a counter. There is no duplicate publish and no loss of a confirmed command. The broker is outside the model apart from the offset.
- Commands carry no payload, so the effect of a command in a store is a count of applications.
- A store never fails and never rejects for a reason other than the guard. A store restart and receipt pruning are not modelled.
- The reader makes one pass. It is not a snapshot read, since the claim is about two separate reads.
- Incarnations are numbered and started in order. A started incarnation never stops except by a crash, so a finished zombie stays alive.
- Time and heartbeats are not modelled, so a takeover is any interleaving the constants allow.

The model terminates, so TLC is run with `-deadlock`, which turns the check for a state with no successor off. For the temporal property TLC treats such a state as repeating forever, which is how the counterexample for `Received` ends.

`UnguardedOutcome` replaces the store's guard in one configuration to show what the guard is worth.

### `X2_EvidenceAcrossStores.tla`

A core that reads evidence in a source store S and commits a decision with its read set to a records store R. S commits at positions 1, 2, 3 and so on. Each position holds the value of the evidence after that commit, and a commit may leave the value as it was. S keeps every version, so the value at position `p` is always available. The watermark is the highest committed position. Each position in `DecPositions` has one core. The core reads in one step and commits a decision carrying the value read and the position read at in a later step, and S moves between the two.

The constant `Row` selects the last two rows of the catalogue in section 4.2.

| Constant | Meaning |
|---|---|
| `Row` | `Watermark` makes the core wait until the watermark has reached `p` and read the value S held at `p`, recording `p` as the position. `BestKnown` makes the core read S's current value at once and record the watermark as the position. |
| `MaxPos` | The highest position S reaches. |
| `Values` | The values the evidence can take. |
| `Holder0` | The value at position 0. |
| `DecPositions` | The decision positions, one core each. |

The audit is computed from the read set and S's versions only. A decision is superseded if S committed a change at a position between the position read at and `p`, in either order. A decision whose `p` is above the watermark cannot be audited yet.

Two specifications are defined. `Spec` makes S advance under weak fairness, so its watermark is live. `SpecStalled` removes that fairness, so S may stop at any point, which stands for a partition. The cores are weakly fair in both.

Properties.

| Name | Kind | Statement | Expected |
|---|---|---|---|
| `CommitOnlyPastWatermark` | invariant | A committed decision has `p` at or below the watermark. | holds with `Watermark` |
| `EvidenceAsOfP` (W) | invariant | Once S has reached `p`, a committed decision's value equals what S held at `p`. | holds with `Watermark`, fails with `BestKnown` |
| `AuditFindsStale` (A) | invariant | Once S has reached `p`, a decision whose value differs from what S held at `p` is flagged by the audit. | holds |
| `NoneSuperseded` | invariant | No auditable decision is flagged. A check that the audit is not vacuous. | fails with `BestKnown` |
| `ReadSetTrue` | invariant | The recorded position holds the recorded value. | holds |
| `AllDecided` (L) | temporal | Every evaluation eventually commits. | holds with `Watermark` under `Spec`, fails with `Watermark` under `SpecStalled`, holds with `BestKnown` under either |

What the model abstracts away.

- S commits at consecutive positions one at a time, and the order of positions is the order of commits. A late-arriving commit is the subject of `X3_ReceiptRelay.tla` and is not modelled here.
- The evidence is one value. A real read set has several triples and several stores.
- R is a set. A decision is never rejected or retried.
- The audit is conservative. Whether it flags a decision whose evidence is correct, for instance when the value changes and changes back, was not checked.
- Each position has one core, so two cores never race for the same decision.

### `X3_ReceiptRelay.tla`

A relay that publishes receipts which writers have committed to one store, the outbox of section 4.9. Each stream has `N` receipts numbered from 1. The writer of a stream is serialised, so it begins receipt `q + 1` only after receipt `q` has committed. Beginning a receipt takes the next position from a global counter and committing is a later step. Receipts of different streams therefore commit in an order that differs from their positions, which is the late arrival of a transaction that took its position before it committed.

The relay checkpoints its progress in a separate step. A restart returns it to the last checkpoint, so receipts after the checkpoint are published again.

| Constant | Meaning |
|---|---|
| `Relay` | `ByCommitPosition` keeps one high-water mark and publishes the committed receipt with the lowest position above it, then moves the mark to that position. `PerStreamContiguous` keeps the next seq expected for each stream and publishes a stream's receipt only when it is that one. |
| `Streams` | The streams. |
| `N` | The number of receipts in each stream. |
| `MaxRestarts` | The largest number of relay restarts in a behaviour. |

Properties.

| Name | Kind | Statement | Expected |
|---|---|---|---|
| `AllPublished` (R1) | temporal | Every committed receipt is eventually published, under weak fairness on the writers and the relay. A checkpoint and a restart are never forced. | fails with `ByCommitPosition`, holds with `PerStreamContiguous` |
| `PerStreamOrder` (R2) | invariant | A receipt is published only after every lower seq of its stream has been. A second publication is allowed. | fails with `ByCommitPosition`, holds with `PerStreamContiguous` |
| `NoUncommittedPublished` (R3) | invariant | Every published receipt has committed. True by construction, since both relays read committed receipts only, so it is a check of the model and not a finding. | holds |
| `NoDuplicate` | invariant | No receipt is published twice. A check that the restart does republish. | fails when `MaxRestarts` is above 0 |

What the model abstracts away.

- The writer of each stream is serialised. The late arrival is across streams only, so order within a stream is the order of positions.
- A position is taken at `Begin` and the receipt commits at `Commit`. The store's own transaction machinery, the lock or snapshot that makes a position visible late, is not modelled.
- Receipts carry no payload and the downstream consumer is not modelled. Publication appends to a sequence.
- The relay has no crash other than the restart to a checkpoint, and a checkpoint is atomic.
- A receipt is never rolled back. Every begun receipt commits in the end.

The model terminates, so TLC is run with `-deadlock`.

### `X4_AuthorityCutover.tla`

Moving a family's authority from store A to store B while writers are live, the cutover of section 4.5. A router holds the current authority. Each writer keeps a cached view of it and refreshes the view in a separate step. A writer has `PerWriter` writes to make, one after another. For the current write it sends a request to the store its view names, waits, and moves on when a store acknowledges. A store handles a request in one step. A store that is not fenced applies the write and acknowledges, and a fenced store refuses it, which sends a waiting writer back to sending. A request may stay in flight while the writer does other things.

A migrator moves the authority. The copy is one step that takes a snapshot of A, so a write that A applies after the copy is not in B.

| Constant | Meaning |
|---|---|
| `Protocol` | `Naive` copies A to B and then flips the router, and writers keep writing to A until they see the flip. `Fenced` fences A first, then copies, then flips, and a fenced store refuses writes. |
| `Timeouts` | Whether a waiting writer may give up on its request without the request being withdrawn, and send again to wherever its view then points. This is a constant beyond the two protocols, added so that a lost write and a double acknowledgement can be shown separately. |
| `Writers` | The writers. |
| `PerWriter` | The number of writes each writer makes. |

Properties.

| Name | Kind | Statement | Expected |
|---|---|---|---|
| `NoLostWrite` (C1) | invariant | Every acknowledged write is in the state of the current authority. | fails with `Naive`, holds with `Fenced` |
| `SingleAuthority` (C2) | invariant | No write is acknowledged by both stores. | holds with `Naive` when `Timeouts` is false, fails with `Naive` when it is true, holds with `Fenced` |
| `AllAcknowledged` (C3) | temporal | Every write is eventually acknowledged, under weak fairness on everything except a timeout. | holds with `Fenced` |

What the model abstracts away.

- The copy is atomic. A copy that streams while writes arrive, and the catch-up it would need, is not modelled.
- The migrator and the stores never crash, and a fence is never lost.
- A store applies and acknowledges in one step, and the writer learns of the acknowledgement in the same step if it is still waiting on that write.
- A store is a set of write identifiers, so an application is idempotent and a duplicate application is invisible in the state. Acknowledgement is what shows a double application.
- There is no deduplication by the writer or the store, so a write sent twice can be applied twice. `SingleAuthority` checks that no write is acknowledged by both stores.
- The router is read in one step and a view is never invalidated, so a view stays stale until the writer refreshes it.
- `C3` was checked for `Fenced` only. It was not checked for `Naive`.

## Configurations

| File | Model | Parameters | Checks | Expected |
|---|---|---|---|---|
| `ModelA_Atomic.cfg` | A | three writers, `Atomic` | `NoLostUpdate` | no error |
| `ModelA_SnapshotNoWWDetect.cfg` | A | three writers, `SnapshotNoWWDetect` | `NoLostUpdate` | violated |
| `X1_Applied.cfg` | X1 | `K=3`, `W=2`, `MaxCrashes=2`, no zombie, `Applied` | S1, S2, `AThenB`, L1 | no error |
| `X1_AppliedZombie.cfg` | X1 | `K=3`, `W=2`, `MaxCrashes=1`, zombie, `Applied` | S1, S2, `AThenB`, L1 | no error |
| `X1_AppliedZombie2.cfg` | X1 | `K=3`, `W=2`, `MaxCrashes=2`, zombie, `Applied` | S1, S2, `AThenB`, L1 | no error |
| `X1_Received.cfg` | X1 | `K=3`, `W=2`, `MaxCrashes=1`, no zombie, `Received` | S1, S2, `AThenB`, L1 | L1 violated |
| `X1_Unguarded.cfg` | X1 | `K=3`, `W=2`, `MaxCrashes=1`, zombie, `Applied`, no guard | S1, S2 | S1 violated |
| `X1_Torn.cfg` | X1 | `K=3`, `W=2`, `MaxCrashes=1`, no zombie, `Applied`, reader | T1 | violated |
| `X1_TornZombie.cfg` | X1 | as `X1_Torn.cfg` with a zombie | T1 | violated |
| `X1_TornReceived.cfg` | X1 | as `X1_Torn.cfg` with `Received` | T1 | violated |
| `X1_TornCrash.cfg` | X1 | `K=3`, `W=2`, `MaxCrashes=1`, no zombie, `Applied` | `NoStrandedHalfApply` | violated |
| `X2_Watermark.cfg` | X2 | `Watermark`, `Spec`, `MaxPos=3`, two values, decisions at 1, 2 and 3 | `CommitOnlyPastWatermark`, W, A, `ReadSetTrue`, L | no error |
| `X2_WatermarkStalled.cfg` | X2 | as `X2_Watermark.cfg` with `SpecStalled` | the same | L violated |
| `X2_BestKnown.cfg` | X2 | `BestKnown`, `Spec`, constants as above | W | violated |
| `X2_BestKnownAudit.cfg` | X2 | as `X2_BestKnown.cfg` | A, `ReadSetTrue`, L | no error |
| `X2_BestKnownStalled.cfg` | X2 | as `X2_BestKnown.cfg` with `SpecStalled` | A, `ReadSetTrue`, L | no error |
| `X2_BestKnownSuperseded.cfg` | X2 | as `X2_BestKnown.cfg` | `NoneSuperseded` | violated |
| `X3_ByPositionLive.cfg` | X3 | `ByCommitPosition`, two streams of two receipts, no restart | R1, R3 | R1 violated |
| `X3_ByPositionOrder.cfg` | X3 | as `X3_ByPositionLive.cfg` | R2 | violated |
| `X3_ByPositionRestart.cfg` | X3 | as `X3_ByPositionLive.cfg` with `MaxRestarts=1` | R1, R3 | R1 violated |
| `X3_PerStream.cfg` | X3 | `PerStreamContiguous`, two streams of two receipts, no restart | R1, R2, R3 | no error |
| `X3_PerStreamRestart.cfg` | X3 | as `X3_PerStream.cfg` with `MaxRestarts=1` | R1, R2, R3 | no error |
| `X3_PerStreamDuplicate.cfg` | X3 | as `X3_PerStreamRestart.cfg` | `NoDuplicate` | violated |
| `X4_Naive.cfg` | X4 | `Naive`, no timeouts, two writers of two writes | C1 | violated |
| `X4_NaiveSingle.cfg` | X4 | as `X4_Naive.cfg` | C2 | no error |
| `X4_NaiveTimeouts.cfg` | X4 | `Naive`, timeouts, two writers of two writes | C2 | violated |
| `X4_Fenced.cfg` | X4 | `Fenced`, no timeouts, two writers of two writes | C1, C2, C3 | no error |
| `X4_FencedTimeouts.cfg` | X4 | `Fenced`, timeouts, two writers of two writes | C1, C2, C3 | no error |

## Running

TLC comes from the TLA+ tools jar, which is installed locally and never committed. Set `TLA2TOOLS_JAR` to its path for the session and run TLC from this directory.

```powershell
$env:TLA2TOOLS_JAR = '<path to tla2tools.jar>'
$java = "$(mise where java)\bin\java.exe"
& $java -XX:+UseParallelGC -cp $env:TLA2TOOLS_JAR tlc2.TLC -workers auto -deadlock -config X1_Applied.cfg X1_SerialisedApply.tla
```

The module for a `ModelA_*.cfg` is `ModelA_GuardedCas.tla`, for an `X1_*.cfg` is `X1_SerialisedApply.tla`, for an `X2_*.cfg` is `X2_EvidenceAcrossStores.tla`, for an `X3_*.cfg` is `X3_ReceiptRelay.tla` and for an `X4_*.cfg` is `X4_AuthorityCutover.tla`. TLC writes `states/` and any trace file into the directory, and `.gitignore` excludes them.

## Results

TLC 2.19 with TLA+ tools 1.7.4 on Java 25, 2026-11-18. The runs expected to find no error used `-workers auto`. The runs that end in a counterexample used `-workers 1`, since with several workers the counts at the moment of the error and the trace vary between runs. The counts for complete runs do not vary. The depth for a counterexample run is the depth of the search when it stopped. For a violated temporal property the counts are those of the complete state graph, the depth is the one the last progress line reports, and the counterexample ends in a stuttering state. The `X2_WatermarkStalled` run did not print a depth.

| Configuration | Result | States generated | Distinct states | Depth | Counterexample |
|---|---|---|---|---|---|
| `ModelA_Atomic` | no error | 121 | 98 | 7 | none |
| `ModelA_SnapshotNoWWDetect` | `NoLostUpdate` violated | 111 | 79 | 7 | Two writers read version 0 and both evaluate their guard against a snapshot where it holds. Both commit. Two writes are applied with expected version 0 and two receipts share the key (target, 1). |
| `X1_Applied` | no error | 2,411 | 1,479 | 25 | none |
| `X1_AppliedZombie` | no error | 4,504 | 1,603 | 27 | none |
| `X1_AppliedZombie2` | no error | 216,611 | 50,513 | 41 | none |
| `X1_Received` | `EventuallyApplied` violated, S1, S2 and `AThenB` hold | 630 | 395 | 21 | Incarnation 1 receives commands 1 and 2, finishes 1, stores offset 2 (received), applies 2 to A and crashes before B. Incarnation 2 resumes at 3. B never receives 2, and 3 is rejected there as a Conflict since B's row is 1. A ends at version 3 and B at 1. |
| `X1_Unguarded` | `EachAppliedOnceInEffect` violated | 240 | 118 | 8 | A successor starts while incarnation 1 is alive. Both apply command 1 to A, so its effect is applied twice. |
| `X1_Torn` | `NoTornRead` violated | 156 | 84 | 7 | One writer applies command 1 to A. The reader reads A at 1 and then B at 0. No crash is involved. |
| `X1_TornZombie` | `NoTornRead` violated | 297 | 133 | 7 | The same trace as `X1_Torn`. |
| `X1_TornReceived` | `NoTornRead` violated | 156 | 84 | 7 | The same trace as `X1_Torn`. |
| `X1_TornCrash` | `NoStrandedHalfApply` violated | 35 | 25 | 6 | A writer applies command 1 to A and crashes before B. With no incarnation alive, A is at 1 and B at 0. This is the sequence of the sketch's diagram. |
| `X2_Watermark` | no error | 571 | 259 | 10 | none |
| `X2_WatermarkStalled` | `AllDecided` violated, the invariants hold | 571 | 259 | not printed | S stays at watermark 0 and the behaviour stutters. The core for each position waits for the watermark to reach `p` and never reads. |
| `X2_BestKnown` | `EvidenceAsOfP` violated | 89 | 80 | 4 | The core for position 1 reads "a" at position 0. S commits "b" at position 1. The core commits the decision with value "a" read at 0, and S held "b" at 1. |
| `X2_BestKnownAudit` | no error | 15,875 | 7,481 | 10 | none |
| `X2_BestKnownStalled` | no error | 15,875 | 7,481 | 10 | none |
| `X2_BestKnownSuperseded` | `NoneSuperseded` violated | 89 | 80 | 4 | The same trace as `X2_BestKnown`. The audit flags the decision because S changed at position 1, between the position read at and `p`. |
| `X3_ByPositionLive` | `AllPublished` violated | 1,293 | 645 | 14 | The receipt s2.1 takes position 1 and s1.1 takes position 2. The receipt s2.1 commits and is published, so the mark is 1. The receipt s2.2 takes position 3, commits and is published, so the mark is 3. Then s1.1 commits at position 2, below the mark. The relay publishes s1.2 and never s1.1. |
| `X3_ByPositionOrder` | `PerStreamOrder` violated | 372 | 217 | 9 | The receipt s1.1 takes position 1 and s2.1 takes position 2. The receipt s2.1 commits and is published, then s1.1 commits, then s1.2 takes position 3 and commits. The relay publishes s1.2 as the mark moves to 3, and s1.1 is skipped for good. |
| `X3_ByPositionRestart` | `AllPublished` violated | 7,555 | 4,031 | 19 | The same skip as `X3_ByPositionLive`, with a restart in the trace. The restart does not repair it. |
| `X3_PerStream` | no error | 2,399 | 1,143 | 14 | none |
| `X3_PerStreamRestart` | no error | 31,897 | 17,863 | 19 | none |
| `X3_PerStreamDuplicate` | `NoDuplicate` violated | 68 | 50 | 6 | The receipt s1.1 commits and is published. The relay restarts to its checkpoint before it has checkpointed, and publishes s1.1 again. |
| `X4_Naive` | `NoLostWrite` violated | 50 | 36 | 5 | Writer 1 sends write 1.1 to A. The migrator copies A, which is empty. A applies and acknowledges 1.1. The router flips to B, which does not hold 1.1. |
| `X4_NaiveSingle` | no error | 1,607 | 782 | 13 | none |
| `X4_NaiveTimeouts` | `SingleAuthority` violated | 1,013 | 442 | 9 | Writer 1 sends 1.1 to A and times out. The migrator copies and flips, and the writer refreshes and sends 1.1 to B. A then handles the first request and acknowledges. B handles the second request and acknowledges, so 1.1 is acknowledged by both stores. |
| `X4_Fenced` | no error | 740 | 331 | 14 | none |
| `X4_FencedTimeouts` | no error | 4,536 | 1,171 | 18 | none |

## What the results say

- The guard in each store, and the offset stored as applied, give a row that is ordered, applies each command at most once in effect, and applies every confirmed command eventually, for up to three incarnations including a zombie that keeps acting. The zombie's late applies are answered `Duplicate`.
- The row does not give atomic visibility. A reader of two stores sees them at different versions in every configuration, with no crash needed, because the two applies are separate steps. A crash between them leaves A ahead until a successor replays, which is why the catalogue row reads ordered and eventually applied and a read that must be correct reads one store or waits on a watermark.
- Storing the highest received offset loses commands. A command received but not applied is skipped after a crash and the commands after it are rejected by the guard, so the stores stop short of the stream. The safety properties still hold in that run, so the guard turns the defect into a missing command and never into a wrong one.
- Taking the guard out of the stores breaks at-most-once in effect as soon as a second writer acts on the same command, which is the reason a store with no guard cannot take the row.
- A decision that reads the watermark first and then the value as of `p` carries evidence that equals what the source held at `p`, and the evaluation waits. If the source stalls, the evaluation never completes, which is the cost of the row. The best known read never waits and completes in every configuration run, but its evidence can differ from what the source held at `p`. In the configurations run the audit found every such decision, because the read set records the position read at. The audit also flags a decision whose evidence is stale and one whose evidence is not, so it is a trigger for review and not a verdict.
- A relay that publishes by one global commit position skips a receipt that commits after a later position has been published, and a restart does not repair it. The skip breaks order within a stream, since a later receipt of the stream can be published first. A relay that tracks the next seq of each stream publishes every receipt in order in the configurations run, and a restart makes it publish some receipts twice, so the consumer has to be idempotent.
- Copying and then flipping the authority loses a write that the old authority acknowledges between the copy and the flip. Fencing the old authority before the copy loses none in the configurations run. A writer that times out and resends can have the same write acknowledged by both stores without a fence. With the fence it is acknowledged once in the configurations run, and every write is acknowledged in the end.
