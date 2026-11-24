<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# `tools/models/multi-store-protocols/`

TLA+ models of the protocols behind rows of the multi-store catalogue (sketch section 4.2). They are design-time evidence for the formal-methods track H plan's FMH-5, protocol model A, for MSA-I6, models X1 to X4 and X1 with receipts only, and for MSA-I14, model X5 of the studio's writers. They are not shipped code and not a proof. TLC checks every state of a small finite instance, so a result holds for the stated constants only.

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

### `X1_ReceiptsOnly.tla`

X1 with the stores the studio has, which keep a receipt for each command id and no version row for the partition. The module extends `X1_SerialisedApply.tla` and changes nothing in it. Each of its configurations replaces X1's `Outcome` by `ReceiptOutcome`, so a store answers a command that has a receipt `Duplicate` and applies any other, and nothing in the store guards the partition's order. `X1_Unguarded.cfg` takes out the guard and the receipts together, and these configurations take out the guard alone.

X1's `ver` then holds the seq of the last command a store applied, which is what X1's version row would hold. S1 states that it equals the count of commands applied, so here S1 reads as "no command was skipped". Three invariants are added.

| Name | Kind | Statement | Expected |
|---|---|---|---|
| `AtMostOnce` | invariant | The first half of S1. No command's effect is applied to a store twice. | holds |
| `NoGap` | invariant | A store holds no command after one it lacks. | fails with `Received` |
| `NoGapBehindA` | invariant | Store B holds no command after one that A holds and B lacks, the gap of the second store alone. | fails with `Received` |

What the model abstracts away, beyond X1's list.

- Each command writes an aggregate of its own, so an aggregate's revision never refuses it. Commands on one aggregate are the subject of `X5_WholeCommand.tla`.

### `X5_WholeCommand.tla`

Writers of the studio on one partition, and whether every state they reach is one that some sequence of whole commands gives. One workspace has two aggregates, its description and one document, each with a version row, and the description lists the document. The stream holds a deletion of the document, which writes both aggregates, beside a save of the document, a save of the description alone, or both. The model is written from the studio's `Writer` and its generated operations as built, and from ADR-A149's decision 13 and its addendum of 2026-11-19.

A writer handles one command at a time. It reads the command's receipt, and a command with one is answered from it. Otherwise it reads the rows and plans the command, or answers it without a request where the command's own check fails. A save of the document expects revision 1, the one its sender read, and is answered stale otherwise. A deletion of a document the description does not list is answered not found. A planned command is sent as one request, which the store applies in one step, and the writer reads the receipt back to answer. Then it stores the offset.

Every step of a request is guarded on its row's revision and on its transaction having no claim, and writes the claim where it applies, as the generated operations do. A transaction is named by the command's id and the step's number, the same on every delivery, so a step another delivery applied writes nothing.

| `Guard` | Meaning |
|---|---|
| `PerStep` | The design as built. Each step applies where its own guard holds. A deletion is a description step and then a tombstone of the document, and its receipt is guarded on the description step's claim. A save has one step, and its receipt is guarded on it. A deletion whose receipt is present after its request, or that is answered from its receipt, tombstones a document row still live in a later request, then answers. |
| `Whole` | One guard over every row the command writes, so the request applies every step and the receipt, or nothing. A refused command is planned again from its receipt on, up to `Retries` times, and is then answered as not applied. |
| `Fenced` | `Whole`, and every request carries the writer's epoch. A writer sets the partition's epoch when it starts, and the store refuses a request whose epoch is not the partition's, after which the writer stops without answering. |
| `FencedAnswer` | `Fenced`, and a command refused by its own check, which sends no request, is answered from the same read as its rows, which also reads the epoch and the receipt. A writer that reads another epoch stops without answering, and one that reads the receipt answers from it. A variant beyond the two designs asked for, added after `Fenced`'s run. |

| Constant | Meaning |
|---|---|
| `Guard` | As above. |
| `Delivery` | `Stream` is X1's delivery. Each writer takes the stream in order from the offset stored when it started, and stores the offset of each command it finishes, as applied, the last writer winning. `Any` makes each writer take every command once, in any order, which stands for two writers that do not share one order. |
| `Saves` | The saves on the stream, `SaveDoc`, `SaveDesc` or both, in that order. |
| `DelFirst` | Whether the deletion is first on the stream. Otherwise it is last. |
| `NWriters` | How many writers start, one after another. Each may start while the one before is alive. |
| `MaxCrashes` | The most crashes in a behaviour. |
| `Retries` | How many times a refused command is planned again under `Whole`, `Fenced` and `FencedAnswer`. |

Properties.

| Name | Kind | Statement | Expected |
|---|---|---|---|
| `WholeCommands` | invariant | The description's revision and listing, the document's revision and liveness and the set of receipts equal what some sequence of distinct commands gives, each applied whole from the start as one writer alone applies it. So no command has a receipt while part of it is not applied, and no row has moved that no receipt accounts for. | fails with `PerStep` under `Any`, holds otherwise |
| `AnswersAgree` | invariant | No command answered as not applied has a receipt, then or later. | fails under `Stream` unless `FencedAnswer`. Checked under `Any` with `FencedAnswer` only |
| `TypeOK` | invariant | Each variable stays in its range. | holds |

What the model abstracts away. Where the code leaves a choice, the model makes the one stated here.

- One workspace, one document and two or three commands. The save of the document is of a document already listed whose title and template do not change, so it writes the document alone. The save of the description stands for a change of access, of dependencies or of an import's holding, each of which rewrites the description as read under its revision's guard. Creations, deletions of a workspace, parts, publications and jobs are not modelled.
- A batch holds one command. A batch of several commands of one workspace, planned together, is not modelled.
- The read of the receipt before planning and the reads of the plan are two steps, since another writer may commit between them. The plan's reads are one step, although the writer makes several. The request and the read of the receipt after it are one step, as the store applies one request in one transaction.
- A document's revision is read through the description, so it reads 0 where the document is not listed or its row is tombstoned, as the writer reads only the live rows of listed documents.
- The tombstone a deletion makes again after its request is one step, a read and a request together, so its first round lands. Nothing else moves the document after a deletion's request in these instances. The transaction ids of those rounds are not modelled, since a round that loses writes no claim.
- Content is not modelled. A row is its revision and, for the document, whether it is live. A receipt is the command's id, and a second delivery that writes it again leaves the same receipt.
- A writer answers once for each delivery. Which answer the sender keeps when two writers answer one command is not modelled, so `AnswersAgree` counts any answer that disagrees.
- Under `Fenced` and `FencedAnswer` a writer sets the epoch in the step it starts.
- The patch log, the promotions kept in the same request, jobs, events and the broker are not modelled. Liveness is not checked.

The model terminates, so TLC is run with `-deadlock`.

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
| `X1R_Applied.cfg` | X1, receipts only | `K=3`, `W=2`, `MaxCrashes=2`, no zombie, `Applied` | S1, S2, `AThenB`, `NoGap`, L1 | no error |
| `X1R_AppliedZombie2.cfg` | X1, receipts only | `K=3`, `W=2`, `MaxCrashes=2`, zombie, `Applied` | S1, S2, `AThenB`, `NoGap`, L1 | no error |
| `X1R_Received.cfg` | X1, receipts only | `K=3`, `W=2`, `MaxCrashes=1`, no zombie, `Received` | `AtMostOnce`, S2, `AThenB`, L1 | L1 violated |
| `X1R_ReceivedGap.cfg` | X1, receipts only | as `X1R_Received.cfg` | `NoGap` | violated |
| `X1R_ReceivedGapB.cfg` | X1, receipts only | as `X1R_Received.cfg` | `NoGapBehindA` | violated |
| `X1R_ReceivedRow.cfg` | X1, receipts only | as `X1R_Received.cfg` | `EachAppliedOnceInEffect` | violated |
| `X1R_ReceivedStep.cfg` | X1, receipts only | as `X1R_Received.cfg` | `VersionStepsByOne` | violated |
| `X5_BuiltAnyDoc.cfg` | X5 | `PerStep`, `Any`, the save of the document, two writers, one crash | `WholeCommands` | violated |
| `X5_BuiltAnyDesc.cfg` | X5 | `PerStep`, `Any`, the save of the description, two writers, one crash | `WholeCommands` | violated |
| `X5_BuiltStream.cfg` | X5 | `PerStep`, `Stream`, both saves then the deletion, two writers, one crash | `TypeOK`, `WholeCommands` | no error |
| `X5_BuiltStreamDelFirst.cfg` | X5 | as `X5_BuiltStream.cfg` with the deletion first | `TypeOK`, `WholeCommands` | no error |
| `X5_BuiltStream3.cfg` | X5 | as `X5_BuiltStream.cfg` with three writers and two crashes | `TypeOK`, `WholeCommands` | no error |
| `X5_BuiltStreamAnswers.cfg` | X5 | as `X5_BuiltStream.cfg` | `AnswersAgree` | violated |
| `X5_WholeAny.cfg` | X5 | `Whole`, `Any`, both saves and the deletion, two writers, one crash, `Retries=3` | `TypeOK`, `WholeCommands` | no error |
| `X5_WholeStream.cfg` | X5 | `Whole`, `Stream`, otherwise as `X5_WholeAny.cfg` | `TypeOK`, `WholeCommands` | no error |
| `X5_WholeStreamAnswers.cfg` | X5 | as `X5_WholeStream.cfg` | `AnswersAgree` | violated |
| `X5_FencedAny.cfg` | X5 | `Fenced`, otherwise as `X5_WholeAny.cfg` | `TypeOK`, `WholeCommands` | no error |
| `X5_FencedStream.cfg` | X5 | `Fenced`, otherwise as `X5_WholeStream.cfg` | `TypeOK`, `WholeCommands` | no error |
| `X5_FencedStreamAnswers.cfg` | X5 | as `X5_FencedStream.cfg` | `AnswersAgree` | violated |
| `X5_FencedAnswerAny.cfg` | X5 | `FencedAnswer`, otherwise as `X5_WholeAny.cfg` | `TypeOK`, `WholeCommands`, `AnswersAgree` | no error |
| `X5_FencedAnswerStream.cfg` | X5 | `FencedAnswer`, otherwise as `X5_WholeStream.cfg` | `TypeOK`, `WholeCommands`, `AnswersAgree` | no error |
| `X5_FencedAnswerStream3.cfg` | X5 | as `X5_FencedAnswerStream.cfg` with three writers and two crashes | `TypeOK`, `WholeCommands`, `AnswersAgree` | no error |

The configurations above are the base tier. The wide tier takes each configuration of X1 to X4 that is expected to find no error and steps its instance up one constant at a time, to at most four commands and, in X1, a window of three. A command is a command of the stream in X1, a position of the source and a decision in X2, a receipt of a stream in X3 and a write of a writer in X4. X3 and X4 have no window, so their second step adds a third stream or a third writer. Each checks what its base configuration checks.

| File | Model | Parameters | Expected |
|---|---|---|---|
| `X1_Applied_K4W2.cfg` | X1 | as `X1_Applied.cfg` with `K=4` | no error |
| `X1_Applied_K4W3.cfg` | X1 | as `X1_Applied.cfg` with `K=4`, `W=3` | no error |
| `X1_AppliedZombie2_K4W2.cfg` | X1 | as `X1_AppliedZombie2.cfg` with `K=4` | no error |
| `X1_AppliedZombie2_K4W3.cfg` | X1 | as `X1_AppliedZombie2.cfg` with `K=4`, `W=3` | no error |
| `X2_Watermark_P4.cfg` | X2 | as `X2_Watermark.cfg` with `MaxPos=4` | no error |
| `X2_Watermark_P4D4.cfg` | X2 | as `X2_Watermark.cfg` with `MaxPos=4` and decisions at 1 to 4 | no error |
| `X2_BestKnownAudit_P4.cfg` | X2 | as `X2_BestKnownAudit.cfg` with `MaxPos=4` | no error |
| `X2_BestKnownAudit_P4D4.cfg` | X2 | as `X2_BestKnownAudit.cfg` with `MaxPos=4` and decisions at 1 to 4 | no error |
| `X2_BestKnownStalled_P4.cfg` | X2 | as `X2_BestKnownStalled.cfg` with `MaxPos=4` | no error |
| `X2_BestKnownStalled_P4D4.cfg` | X2 | as `X2_BestKnownStalled.cfg` with `MaxPos=4` and decisions at 1 to 4 | no error |
| `X3_PerStream_N3.cfg` | X3 | as `X3_PerStream.cfg` with `N=3` | no error |
| `X3_PerStream_N4.cfg` | X3 | as `X3_PerStream.cfg` with `N=4` | no error |
| `X3_PerStream_S3.cfg` | X3 | as `X3_PerStream.cfg` with three streams | no error |
| `X3_PerStreamRestart_N3.cfg` | X3 | as `X3_PerStreamRestart.cfg` with `N=3` | no error |
| `X3_PerStreamRestart_N4.cfg` | X3 | as `X3_PerStreamRestart.cfg` with `N=4` | no error |
| `X3_PerStreamRestart_S3.cfg` | X3 | as `X3_PerStreamRestart.cfg` with three streams | no error |
| `X4_NaiveSingle_P3.cfg` | X4 | as `X4_NaiveSingle.cfg` with `PerWriter=3` | no error |
| `X4_NaiveSingle_P4.cfg` | X4 | as `X4_NaiveSingle.cfg` with `PerWriter=4` | no error |
| `X4_NaiveSingle_W3.cfg` | X4 | as `X4_NaiveSingle.cfg` with three writers | no error |
| `X4_Fenced_P3.cfg` | X4 | as `X4_Fenced.cfg` with `PerWriter=3` | no error |
| `X4_Fenced_P4.cfg` | X4 | as `X4_Fenced.cfg` with `PerWriter=4` | no error |
| `X4_Fenced_W3.cfg` | X4 | as `X4_Fenced.cfg` with three writers | no error |
| `X4_FencedTimeouts_P3.cfg` | X4 | as `X4_FencedTimeouts.cfg` with `PerWriter=3` | no error |
| `X4_FencedTimeouts_P4.cfg` | X4 | as `X4_FencedTimeouts.cfg` with `PerWriter=4` | no error |
| `X4_FencedTimeouts_W3.cfg` | X4 | as `X4_FencedTimeouts.cfg` with three writers | no error |

## Running

TLC comes from the TLA+ tools jar, which is installed locally and never committed. `TLA2TOOLS_JAR` names it. One command runs the models on Windows, macOS and Linux, from the repository's root. On macOS and Linux:

```bash
export TLA2TOOLS_JAR=/path/to/tla2tools.jar
mise run check:models-multi-store                                    # the base tier
mise run check:models-multi-store -- X1_Applied                      # one configuration
mise run check:models-multi-store -- "X5_*"                          # a pattern
mise run check:models-multi-store -- wide                            # what of the wide tier fits the machine
LATTICE_MODELS_MAX_HEAP_MB=2048 mise run check:models-multi-store    # the base tier within 2 GB
```

On Windows, in PowerShell, the variable is set with `$env:TLA2TOOLS_JAR = '<path to tla2tools.jar>'` and the separator is quoted, as in `mise run check:models-multi-store '--' wide`, since `mise` is a PowerShell function there.

[`manifest.toml`](manifest.toml) lists every configuration, with its module, its `.cfg`, its tier, the verdict expected of TLC, and the distinct states, depth, peak heap and time measured on machine S (Windows, 16 logical cores, 64 GB installed). The `base` tier runs within a heap budget of 2 GB. The `wide` tier is the larger instances of X1 to X4 below, some of which need more heap or more time. The runner, [`tools/models/check_tlc.py`](../check_tlc.py), does the following.

- It runs its own tests first, `mise run check:models-multi-store-runner`, which need neither Java nor TLC.
- It finds Java on the path `mise` gives a task, and TLC in the jar. Where the jar or `mem_check` is missing, it says what it skipped and exits 0.
- It reads physical memory from the operating system and the memory available from `mem_check`, within a Linux cgroup's limit where one is set. The heap budget is a quarter of physical memory, never above what is available. `LATTICE_MODELS_MAX_HEAP_MB` lowers it further, and never raises it.
- It gives each run a heap of twice the configuration's peak and 64 MB more, and at least 256 MB, since the peak read under a large heap understates what a small heap needs. `X1_AppliedZombie2`, whose peak read 111 MB under 2 GB, ran out of a heap of 208 MB in TLC's liveness checking, ran out of 224 MB in one run of four and completed in the other three, and completed in 240 and 256 MB. A configuration whose heap exceeds the budget is skipped with both figures and never started. So is one whose peak the manifest does not state, and one that machine S stopped at its limit. `--heap-mb` gives every selected run one heap instead, to measure it, within the budget all the same.
- It runs a configuration expected to find no error with as many TLC workers as the machine has cores, shared between the `--jobs`, and one expected to violate a property with one worker, so that its counts and its trace do not vary. Configurations run together never hold more heap than the budget. `--max-minutes` stops a run and reports it.
- It runs TLC with `-deadlock`, since every model terminates, in a copy of this directory under `.build/formal/tlc/multi-store-protocols/<configuration>/`, where TLC writes its states, any trace, its temporary files and its GC log.
- It prints, for each configuration, the verdict, the distinct and generated states, the depth, TLC's time, the wall time and the peak heap, then one line of totals. Where the distinct states differ from the manifest's, the line says so. A configuration fails only where TLC's verdict differs from the manifest's. A skip, a stop and a run that runs out of heap are reported and do not fail.

A pass of the base tier prints the runner's tests, `24 passed`, then a line with the heap budget, then for each of the 50 configurations a `RUN` line and a `PASS` line. Twenty-four `PASS` lines read "no error" and twenty-six name the property violated, each as the manifest expects. It ends with the line below and exits 0.

```text
models: 50 as expected, 0 failed, 0 skipped, 0 stopped
```

On a machine of 8 GB the budget is at most 2 GB, which every base configuration fits, the largest heap given being 320 MB. The wide tier on such a machine skips each configuration whose heap exceeds the budget, with both figures, and exits 0 unless a verdict differs.

The peak heap is read from the GC log. The young generation is fixed at 16 MB, so a collection runs at least every 16 MB allocated, and the peak is the largest heap in use before a collection that the log printed. The true peak is at most 16 MB above it.

The module for a `ModelA_*.cfg` is `ModelA_GuardedCas.tla`, for an `X1_*.cfg` is `X1_SerialisedApply.tla`, for an `X1R_*.cfg` is `X1_ReceiptsOnly.tla`, for an `X2_*.cfg` is `X2_EvidenceAcrossStores.tla`, for an `X3_*.cfg` is `X3_ReceiptRelay.tla`, for an `X4_*.cfg` is `X4_AuthorityCutover.tla` and for an `X5_*.cfg` is `X5_WholeCommand.tla`. TLC run by hand in this directory writes `states/` and any trace file here, and `.gitignore` excludes them.

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

The `X1R_*` and `X5_*` configurations were run with TLC 2.19 and TLA+ tools 1.7.4 on Java 25.0.2, on 2026-11-24 by TLC's clock, each run by hand under `-Xmx2g -Xmn16m -XX:+UseParallelGC -Xlog:gc`, with `-workers auto` where no error was expected and `-workers 1` where a counterexample was. TLC's time is the "Finished in" figure, in whole seconds. The wall time includes the JVM's start. The peak heap is as the Running section defines it. Every one fits a heap of 2 GB, the largest at 114 MB.

| Configuration | Result | States generated | Distinct states | Depth | TLC time | Wall time | Peak heap | Counterexample |
|---|---|---|---|---|---|---|---|---|
| `X1R_Applied` | no error | 2,411 | 1,479 | 25 | 00s | 2.5 s | 28 MB | none |
| `X1R_AppliedZombie2` | no error | 216,611 | 50,513 | 41 | 05s | 7.0 s | 114 MB | none |
| `X1R_Received` | `EventuallyApplied` violated, `AtMostOnce`, S2 and `AThenB` hold | 632 | 397 | not printed | 00s | 2.2 s | 27 MB | Incarnation 1 receives commands 1 and 2, applies 1 to both stores, stores offset 2 (received), receives 3, applies 2 to A and crashes before B. Incarnation 2 resumes at 3 and applies it to A and then to B, where it has no receipt and nothing guards the order. A ends with 1, 2 and 3, and B with 1 and 3. B never receives 2. |
| `X1R_ReceivedGap` | `NoGap` violated | 385 | 235 | 14 | 00s | 2.1 s | 15 MB | Incarnation 1 receives 1 and 2, applies 1 to both stores, stores offset 2 and crashes. Incarnation 2 resumes at 3 and applies it to A, which holds 1 and 3. Command 2 is in neither store. |
| `X1R_ReceivedGapB` | `NoGapBehindA` violated | 505 | 312 | 16 | 00s | 2.1 s | 15 MB | Incarnation 1 receives 1 and 2, applies 1 to both stores, stores offset 2, applies 2 to A and crashes before B. Incarnation 2 resumes at 3 and applies it to A and then to B. A holds 1, 2 and 3, and B holds 1 and 3. |
| `X1R_ReceivedRow` | `EachAppliedOnceInEffect` violated | 385 | 235 | 14 | 00s | 2.2 s | 15 MB | The same trace as `X1R_ReceivedGap`. A's last command applied is 3, and it has applied two. |
| `X1R_ReceivedStep` | `VersionStepsByOne` violated | 385 | 235 | 14 | 00s | 2.3 s | 15 MB | The same trace. A's last command applied moves from 1 to 3. |
| `X5_BuiltAnyDoc` | `WholeCommands` violated | 536 | 243 | 11 | 00s | 2.1 s | 16 MB | Writer 1 plans the save of the document at revision 1. Writer 2 starts and plans the deletion, reading the description at 1 and the document at 1. Writer 1's request moves the document to 2 and writes the save's receipt. Writer 2's request applies the description step, so the document is no longer listed, and its tombstone at revision 1 writes nothing, and the receipt is written on the description step's claim. The deletion has a receipt and the document's row is live at 2, unlisted, until writer 2's later request removes it. |
| `X5_BuiltAnyDesc` | `WholeCommands` violated | 536 | 242 | 11 | 00s | 2.1 s | 16 MB | Writer 1 plans the save of the description at revision 1. Writer 2 plans the deletion at description 1 and document 1. Writer 1's request moves the description to 2. Writer 2's request writes nothing for the description step and tombstones the document, and writes no receipt, since the description step has no claim. The description lists a tombstoned document and no receipt accounts for the tombstone. Writer 2 answers the deletion as not applied. |
| `X5_BuiltStream` | no error | 3,535 | 1,344 | 31 | 00s | 2.3 s | 24 MB | none |
| `X5_BuiltStreamDelFirst` | no error | 2,786 | 1,080 | 31 | 00s | 2.2 s | 24 MB | none |
| `X5_BuiltStream3` | no error | 249,875 | 56,474 | 39 | 01s | 3.0 s | 63 MB | none |
| `X5_BuiltStreamAnswers` | `AnswersAgree` violated | 157 | 81 | 10 | 00s | 2.1 s | 16 MB | Writer 1 plans the save of the document. Writer 2 starts at offset 0, takes the same save and reads no receipt. Writer 1's request applies the save and writes its receipt. Writer 2 then plans, reads the document at revision 2 and answers the save stale, which it was not. |
| `X5_WholeAny` | no error | 41,580 | 14,308 | 31 | 00s | 2.5 s | 30 MB | none |
| `X5_WholeStream` | no error | 3,020 | 1,181 | 30 | 00s | 2.2 s | 24 MB | none |
| `X5_WholeStreamAnswers` | `AnswersAgree` violated | 157 | 81 | 10 | 00s | 2.1 s | 16 MB | The same trace as `X5_BuiltStreamAnswers`. Writer 1's request carries no epoch, so nothing refuses it after writer 2 starts. |
| `X5_FencedAny` | no error | 24,745 | 9,335 | 31 | 00s | 2.5 s | 30 MB | none |
| `X5_FencedStream` | no error | 1,955 | 827 | 30 | 00s | 2.2 s | 24 MB | none |
| `X5_FencedStreamAnswers` | `AnswersAgree` violated | 165 | 84 | 10 | 00s | 2.1 s | 16 MB | Writer 1 takes the save of the document and reads no receipt. Writer 2 starts, which sets the epoch to 2, takes the same save, plans it and applies it. Writer 1, which has lost the partition, then plans, reads the document at revision 2 and answers the save stale. It sends no request, so the epoch never refuses it. |
| `X5_FencedAnswerAny` | no error | 18,789 | 7,083 | 29 | 00s | 2.4 s | 30 MB | none |
| `X5_FencedAnswerStream` | no error | 1,299 | 540 | 24 | 00s | 2.2 s | 18 MB | none |
| `X5_FencedAnswerStream3` | no error | 55,386 | 14,597 | 35 | 01s | 2.7 s | 33 MB | none |

The wide tier was run through `mise run check:models-multi-store` on 2026-11-24, with TLC 2.19 and TLA+ tools 1.7.4 on Java 25.0.2, one configuration at a time with nothing else heavy running, on 16 workers, under a heap of 4,096 MB given by `--heap-mb` and stopped at 30 minutes. The two configurations that reached the limit ran under a heap of 8,192 MB, machine S's other limit. The depth is TLC's depth of the complete state graph search, and with 16 workers it can differ by one or two between runs while the counts do not. The peak heap is the one read under the heap given, and [`manifest.toml`](manifest.toml) holds these figures and the base tier's.

| Configuration | Result | States generated | Distinct states | Depth | TLC time | Wall time | Peak heap |
|---|---|---|---|---|---|---|---|
| `X1_Applied_K4W2` | no error | 5,941 | 3,381 | 30 | 00s | 1.5 s | 40 MB |
| `X1_Applied_K4W3` | no error | 9,052 | 5,092 | 32 | 01s | 1.7 s | 47 MB |
| `X1_AppliedZombie2_K4W2` | no error | 791,227 | 174,940 | 50 | 23s | 24.4 s | 724 MB |
| `X1_AppliedZombie2_K4W3` | no error | 1,329,535 | 279,119 | 51 | 40s | 41.2 s | 1,116 MB |
| `X2_Watermark_P4` | no error | 1,867 | 691 | 11 | 00s | 1.6 s | 35 MB |
| `X2_Watermark_P4D4` | no error | 4,459 | 1,555 | 13 | 00s | 1.7 s | 36 MB |
| `X2_BestKnownAudit_P4` | no error | 62,387 | 28,777 | 11 | 01s | 2.1 s | 63 MB |
| `X2_BestKnownAudit_P4D4` | no error | 779,759 | 297,679 | 13 | 13s | 14.0 s | 572 MB |
| `X2_BestKnownStalled_P4` | no error | 62,387 | 28,777 | 11 | 01s | 1.9 s | 63 MB |
| `X2_BestKnownStalled_P4D4` | no error | 779,759 | 297,679 | 13 | 13s | 14.0 s | 567 MB |
| `X3_PerStream_N3` | no error | 56,051 | 23,151 | 20 | 02s | 2.9 s | 88 MB |
| `X3_PerStream_N4` | no error | 1,098,505 | 424,131 | 26 | 51s | 51.6 s | 1,674 MB |
| `X3_PerStream_S3` | no error | 971,581 | 392,848 | 20 | 38s | 39.2 s | 1,324 MB |
| `X3_PerStreamRestart_N3` | no error | 2,971,163 | 1,454,319 | 27 | 02min 07s | 128.4 s | 3,084 MB |
| `X3_PerStreamRestart_N4` | stopped at 30 minutes under a heap of 8,192 MB, no error printed by then | 33,918,649 | 15,204,162 found, 5,178,623 on the queue | 27 reached | not printed | 1,800.8 s | 8,128 MB |
| `X3_PerStreamRestart_S3` | stopped at 30 minutes under a heap of 8,192 MB, no error printed by then | 47,624,388 | 24,348,504 found, 8,286,182 on the queue | 24 reached | not printed | 1,801.1 s | 8,190 MB |
| `X4_NaiveSingle_P3` | no error | 6,390 | 3,009 | 17 | 00s | 1.1 s | 35 MB |
| `X4_NaiveSingle_P4` | no error | 18,951 | 8,806 | 21 | 00s | 1.2 s | 37 MB |
| `X4_NaiveSingle_W3` | no error | 55,341 | 18,430 | 18 | 00s | 1.2 s | 40 MB |
| `X4_Fenced_P3` | no error | 1,856 | 823 | 18 | 00s | 1.3 s | 36 MB |
| `X4_Fenced_P4` | no error | 3,792 | 1,687 | 22 | 00s | 1.4 s | 44 MB |
| `X4_Fenced_W3` | no error | 14,332 | 4,471 | 19 | 01s | 1.8 s | 51 MB |
| `X4_FencedTimeouts_P3` | no error | 13,745 | 3,436 | 22 | 01s | 1.7 s | 49 MB |
| `X4_FencedTimeouts_P4` | no error | 32,168 | 7,903 | 27 | 01s | 2.2 s | 72 MB |
| `X4_FencedTimeouts_W3` | no error | 195,904 | 33,797 | 25 | 06s | 6.7 s | 209 MB |

## What the results say

- The guard in each store, and the offset stored as applied, give a row that is ordered, applies each command at most once in effect, and applies every confirmed command eventually, for up to three incarnations including a zombie that keeps acting. The zombie's late applies are answered `Duplicate`.
- The row does not give atomic visibility. A reader of two stores sees them at different versions in every configuration, with no crash needed, because the two applies are separate steps. A crash between them leaves A ahead until a successor replays, which is why the catalogue row reads ordered and eventually applied and a read that must be correct reads one store or waits on a watermark.
- Storing the highest received offset loses commands. A command received but not applied is skipped after a crash and the commands after it are rejected by the guard, so the stores stop short of the stream. The safety properties still hold in that run, so the guard turns the defect into a missing command and never into a wrong one.
- Taking the guard out of the stores breaks at-most-once in effect as soon as a second writer acts on the same command, which is the reason a store with no guard cannot take the row.
- A decision that reads the watermark first and then the value as of `p` carries evidence that equals what the source held at `p`, and the evaluation waits. If the source stalls, the evaluation never completes, which is the cost of the row. The best known read never waits and completes in every configuration run, but its evidence can differ from what the source held at `p`. In the configurations run the audit found every such decision, because the read set records the position read at. The audit also flags a decision whose evidence is stale and one whose evidence is not, so it is a trigger for review and not a verdict.
- A relay that publishes by one global commit position skips a receipt that commits after a later position has been published, and a restart does not repair it. The skip breaks order within a stream, since a later receipt of the stream can be published first. A relay that tracks the next seq of each stream publishes every receipt in order in the configurations run, and a restart makes it publish some receipts twice, so the consumer has to be idempotent.
- Copying and then flipping the authority loses a write that the old authority acknowledges between the copy and the flip. Fencing the old authority before the copy loses none in the configurations run. A writer that times out and resends can have the same write acknowledged by both stores without a fence. With the fence it is acknowledged once in the configurations run, and every write is acknowledged in the end.
- Stores that keep a receipt for each command and no row for the partition keep every property of X1 with offsets stored as applied, for one writer at a time and for up to three incarnations including a zombie. TLC printed the same counts as for X1 with the guard, so in those configurations the partition's row refused nothing that the receipts did not answer.
- With received offsets the same stores keep at-most-once, order within each store and `AThenB`, and lose eventual application as X1 does. They also let store B apply command 3 after it missed command 2, which X1's guard refused, so a gap in the second store is reachable and nothing in the store stops it. S1 as X1 states it and `VersionStepsByOne` fail by the same trace, since the last command applied no longer counts the commands applied.
- The studio's writer as built reaches states that no sequence of whole commands gives when two writers do not share one order. A deletion is answered from a receipt while the document it deletes is live and unlisted, until a later request removes it. A deletion whose description step lost tombstones the document while the description still lists it, with no receipt. Where each writer takes the stream in order from the stored offset, TLC found no such state, for two writers in either order of the stream and for three writers with two crashes. We read this as the transaction ids doing the work, since a step that another delivery applied writes nothing, and a writer reaches a command only after it has finished every earlier one. That is a reading of the runs and not a proof.
- The answers as built disagree even in stream order. A writer that read no receipt plans after another writer applied the command, and answers a save stale although it was applied.
- One guard over every row a command writes reaches only states that whole commands give, in both deliveries in the configurations run, and its answers disagree by the same trace as the design as built.
- One guard with the epoch in every request also reaches only such states in the configurations run, and its answers still disagree. The writer that lost the partition answers a command its own check refuses without sending a request, so the epoch never reaches that answer. Answering such a command from one read of its rows, the epoch and its receipt removes the disagreement in the configurations run, for two writers in either delivery and for three writers in stream order.
- In the wide tier TLC printed "Model checking completed. No error has been found." for every configuration it finished. So the serialised writer kept S1, S2, `AThenB` and L1 with four commands and a window of three, with and without a zombie, over 279,119 distinct states. The watermark read kept its evidence and completed, and the audit of the best known read flagged every stale decision, with S reaching position 4 and a decision at each of positions 1 to 4. The relay by each stream's next seq kept order and published every receipt with four receipts in a stream, or three streams, and with a restart and three receipts in a stream. The fenced cutover kept every acknowledged write, acknowledged none twice and acknowledged every write, with four writes for each writer or three writers, with and without timeouts, and the naive cutover without timeouts acknowledged no write twice. Each holds for the constants run and no others. With a restart and four receipts in a stream, or a restart and three streams of two receipts, TLC was stopped at 30 minutes with its heap of 8 GB full and no error printed by then, after more than 15 million distinct states. Nothing is concluded for those two instances, since TLC had not reached every state.
