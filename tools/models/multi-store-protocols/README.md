<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# `tools/models/multi-store-protocols/`

TLA+ models of the protocols behind rows of the multi-store catalogue (sketch section 4.2). They are design-time evidence for the formal-methods track H plan's FMH-5, protocol models A to D, for MSA-I6, models X1 to X4, X1 with receipts only, Protocol A in one ledger, a pass over two ledgers, X2's audit and the trace validation that holds models A to D to the Isabelle model of [`spikes/multi-store-model/`](../../../spikes/multi-store-model/README.md), and for MSA-I14, model X5 of the studio's writers. They are not shipped code and not a proof. TLC checks every state of a small finite instance, so a result holds for the stated constants only.

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

### The stores of models B, C and D

Models B, C and D share one reading of a store, wider than model A's. Each writer sends one request, whose guards are evaluated in the order the multi-store model's IR gives them, so the first that fails decides the outcome. The constant `Isolation` selects what the store makes of the request.

| Value | Meaning |
|---|---|
| `Atomic` | The guards and the writes are one atomic step, as a store that serialises its writers gives. |
| `SnapshotInsertWW` | The guards are evaluated against a snapshot in one step, and the writes, computed from the snapshot, commit in a later step. The store aborts the commit where a transaction that committed since the snapshot wrote a statement this one writes, and inserting a statement identical to another's counts as writing it. |
| `SnapshotDeleteWW` | As `SnapshotInsertWW`, except that only a statement both transactions delete is a conflict. Inserting an identical statement is not. |
| `SnapshotNoWW` | As `SnapshotInsertWW`, with no conflict detected, so every commit writes what its snapshot computed. |

Each model records, for each committed transaction, the statements it deleted and inserted, each a pair of a kind and a value, so the store can compare them. A request whose guards failed writes nothing and is never aborted. An aborted commit writes nothing, and its writer sends the same request again, up to `Retries` times, as a caller does with a failure it cannot classify, and is then answered `Aborted`. With `Resend`, a writer whose request was applied may send the identical request once more, as after a lost reply.

What the three abstract away, beyond what each says below.

- A statement is a kind and a value. The graph and the subject are left out, since each model has one row, one stream or one claim.
- A store with snapshots evaluates its guards and computes its writes in one step and commits them in one step. What a store does between the two is not modelled.
- An abort is the only failure. A store that loses a commit it acknowledged, and a writer that crashes, are not modelled.
- A writer sends one request. Two requests of one writer at once are not modelled.

### `ModelB_AppendForm.tla`

The append form, an event appended to a stream under the dataset guard, as the persistence compiler generates `append-event-dataset-guard`. Each writer reads the dataset epoch, then sends one request meaning "if the dataset epoch is the one I read, and my transaction has no claim, set the stream's row to its sequence plus one under my epoch, and write my claim, the receipt at that position and my event". It is answered `Refused EpochMismatch` where the epoch differs, then `Duplicate` where the claim exists. The request names no expected sequence, and the store computes the next one. An append deletes the row's epoch, sequence and head statements and inserts their successors, its claim, its receipt and its event. With `Bump`, the dataset epoch is bumped once while writers are live, a transaction of its own that deletes the old epoch statement and inserts the new.

| Constant | Meaning |
|---|---|
| `Writers` | The writers, each with a transaction id of its own. |
| `Isolation` | As above. |
| `Bump` | Whether the dataset epoch is bumped once. |
| `Resend`, `Retries` | As above. |

| Name | Kind | Statement | Expected |
|---|---|---|---|
| `OnePerPosition` | invariant | No two applied appends take one position, so the stream has one receipt for each position. | fails with `SnapshotNoWW` |
| `NoLostAppend` | invariant | The row's sequence counts the applied appends. | fails with `SnapshotNoWW` |
| `FencedAppends` | invariant | Every applied append carries the dataset epoch in force when it applied, so no write sent before a bump lands after it. | fails on every snapshot store with a bump |
| `TypeOK` | invariant | Each variable stays in its range. | holds |

What the model abstracts away.

- The stream's row exists from the start and is never tombstoned, so the IR's two guards on it always hold. The row is created by `bootstrap-version-row`, which is not modelled.
- Each append carries one event. The event's rows and their order within an append are not modelled.
- The bump is atomic and happens once. Restoring a dataset, and a writer that reads the epoch again after a refusal, are not modelled.

### `ModelC_CreateRace.tla`

The first write of an aggregate, raced by writers that each write it under a transaction id and a revision of their own. The constant `FirstWrite` selects the operation, as `dal:firstWrite` does.

| `FirstWrite` | Meaning |
|---|---|
| `AbsentRow` | `create-if-absent`. "If my transaction has no claim and the root has no version row, write the row at seq 1 with my revision as its head, my claim, the receipt and the payload." Answered `Duplicate`, then `Conflict Exists`. It deletes nothing, and inserts the row's type, epoch and seq statements, which every writer's create inserts alike, beside a head of its own. |
| `PreCreatedRow` | The row was created at seq 0 when the id was allocated, and the first write is a guarded replace expecting seq 0. Answered `Duplicate`, then `Conflict Missing`, then `Conflict Stale`. It deletes the row's seq 0 statement. |

The row holds a set of heads, since an RDF row can hold two.

| Name | Kind | Statement | Expected |
|---|---|---|---|
| `OneFirstWrite` | invariant | At most one first write is applied, so the aggregate has one receipt at seq 1 and one creator. | fails with `AbsentRow` and `SnapshotDeleteWW`, and with either form and `SnapshotNoWW` |
| `OneHead` | invariant | The row has at most one head. | fails where `OneFirstWrite` does |
| `TypeOK` | invariant | Each variable stays in its range. | holds |

What the model abstracts away.

- One root. The payload is the writer's identity, and the aggregate's triples are not compared.
- A first write is the only write. A replace after it, and a tombstone, are not modelled.
- The dataset guard is not modelled. Model B has it.

### `ModelD_KeyClaim.tla`

The key claim, owners racing for one claim node, as the persistence compiler generates `key-claim-write`. Each owner sends one request meaning "if the claim is held by no owner but me, insert the claim's type, its constraint and me as its owner". It is answered `Conflict HeldByOther` where another owner holds it. The request has no transaction claim, so an owner that sends it again is applied again and changes nothing. The claim's type and constraint are the same statements whoever inserts them, and the owner differs. With `Sentinel`, each claim also rewrites one pre-created counter statement, deleting its value and inserting the next, so racing claims delete a statement in common. That is the patterns guide's P3, which the generated `key-claim-write` does not do.

| Constant | Meaning |
|---|---|
| `Owners` | The owners racing for the claim, one request each. |
| `Isolation` | As above. |
| `Sentinel` | Whether a claim also rewrites the counter statement. |
| `Resend`, `Retries` | As above. |

| Name | Kind | Statement | Expected |
|---|---|---|---|
| `OneOwner` | invariant | The claim names at most one owner, so the key is unique. | fails with `SnapshotDeleteWW` without the sentinel, and with `SnapshotNoWW` |
| `TypeOK` | invariant | Each variable stays in its range. | holds |

What the model abstracts away.

- One claim and one constraint. The claim's write is its own request. The pattern that writes the claim and the payload in one request is not modelled.
- The counter is one statement. Sharding counters by the key's hash, and the false conflicts between keys that share a shard, are not modelled.
- A claim's retirement, its quarantine and the audit that finds a claim with two owners are not modelled.

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
- The audit is conservative, and flags a decision whose evidence is correct. Where S changes the value and changes it back between the position read at and `p`, the decision carries the value S held at `p` and is flagged all the same, as TLC printed for `X2A_FlaggedIsStale` under `X2_AuditFlags.tla`.
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

### `PA_PassRevision.tla`

Protocol A in one ledger, a second model of what the plain Python model of [`tools/models/ledger-pass-revision/`](../ledger-pass-revision/README.md) checks. It was written from ADR-A131's second addendum of 2026-11-19, its addendum of 2026-11-20 and Behaviour's example `ordered-draws.ttl`, and run, before that model was read. A pass is every record one evaluation writes. It is written as one request that names the revision of the ledger it was evaluated from, and the writer writes it only while the ledger is at that revision. Where the ledger has moved, the writer writes nothing and answers with the revision it found, and the evaluation is made again from that revision. The request moves the revision once.

One owner's ledger holds a seat bundle and an alert quota. An activation's pass makes, in this order, a draw of one seat while the bundle has one, a draw of one alert when the bundle as that draw left it is below 2, and a move of the licence to overage when the bundle as the draws left it is empty. The move is a record of the pass. From overage an activation makes nothing and writes no pass. A credit's pass restores seats, and is cut at the bundle's stated amount. Actor A is an activation and actor O a credit or a second activation. An actor may stop while it holds a plan and lose it. It then looks for its own pass by its name, and evaluates again from the latest revision where it finds none.

| Constant | Meaning |
|---|---|
| `Protocols` | `OnRead` is Protocol A. `OnLatest` writes the request on whatever revision is latest, each draw applied by the ledger's own arithmetic, so a draw that no longer fits is refused as a record, and nothing evaluates the pass again. `PerPosting` makes each posting a request of its own, guarded on the revision the previous one returned and the first on the revision read. A refused posting returns the revision found, and the transitions not yet written are evaluated again from it. After a stop, the transitions whose records are found are left out and the rest evaluated again from the latest revision. |
| `Rules` | `Stimulus` gives a pass its stimulus's position. `LaterOf` gives it the later of that and the position of the ledger's latest pass at the revision it was evaluated from. |
| `Others` | What actor O is, `Credit` or `Activation`. |
| `Modes` | `Concurrent` lets the actors interleave freely. `OneAfterAnother` lets an actor evaluate only while the other is not in the middle of a pass. |
| `MaxStops`, `StopActors` | The most stops in a behaviour, and the actors that may stop. |
| `Bundles`, `Quotas`, `Orders` | The starting balances, and the order of the two stimuli's positions, `AFirst` (A at 1, O at 2), `OFirst` or `Same` (both at 1). |
| `Stated`, `CreditSeats` | The bundle's stated amount, at which a credit is cut, and the seats a credit restores. |
| `Licences` | `One`, both activations of one licence, or `PerActor`, O's activation of a licence of its own on the same accounts. |
| `AlertNeedsQuota` | Whether the alert's guard also asks for a unit in the quota. Where it does not, an alert drawn from an empty quota is refused and the refusal is a record of the pass. |

Each of `Protocols`, `Rules`, `Others` and `Modes` is a set chosen from in the initial state, so one run covers several variants, as the census configurations do. Each step is a function of the state, so the outcomes reachable with no stop are computed inside the model, which O2 needs. The properties are numbered as the Python model numbers its checks.

| Name | Kind | Statement | Expected |
|---|---|---|---|
| `SerialOutcomes` (O1) | invariant | Once both actors are done, the bundle, the quota, the licences' states and each actor's records are those that the two evaluations give made whole one after the other, in one order or the other. | holds with `OnRead` |
| `StopSafe` (O2) | invariant | Once both actors are done in a behaviour with a stop, the outcome is one that some behaviour with no stop reaches from the same starting state. | holds |
| `PassOrder` (O3) | invariant | The ledger's passes, in the order of the revisions they moved it to, are in the order of their positions. | holds with `OnRead` and `LaterOf` |
| `NotBeforeStimulus` (O4) | invariant | No pass takes a position before its stimulus's. | holds |
| `Census` | invariant | Always holds, and prints one line for each state where both actors are done, naming the variant, the starting cell, the stops taken, whether O1 to O4 hold there, and the outcome. The cells a variant breaks are counted from those lines. | holds |

What the model abstracts away.

- Two actors, one evaluation each, and at most one stop. The writer takes a request in one step.
- The records of a pass are a set, so their order within the pass is not compared.
- Behaviour's records are not modelled apart from the ledger's. The move to overage is a record of the pass, written in its one request, so no step falls between a pass and the state change.
- A pass is found by its name, which the model takes to be its actor. How a key is formed is not modelled.
- Under `OnLatest` the writer applies a stale plan by the ledger's arithmetic. A writer that refuses such a request whole where it would overdraw, and has it evaluated again, is another reading of writing on the latest revision, and is the one the Python model takes.
- The census only prints. TLC checks nothing in it, and the counts are read from its output.

The model terminates, so TLC is run with `-deadlock`.

### `X6_PassTwoLedgers.tla`

A pass over two ledgers, the ledger's case of the named saga row, starting from X1's torn read and torn crash with two ledgers in place of two stores. A claim on a contract erodes the programme's aggregate. The contract's account is in the contract's ledger C and the aggregate in the programme's ledger P, which belong to different owners, so the claim's evaluation writes a pass to each and each ledger takes a request of its own, guarded as in `PA_PassRevision.tla` on the revision that ledger was read at. A claim is paid one unit where the contract's account and the aggregate each have one. It reads C, then P in a later step, decides, and writes C first and P second. A claim that is not paid writes nothing. A claim whose C pass is written and that is then not paid writes a compensating pass on C, which restores what it drew. Two claims, E1 and E2, on the same contract. A pass takes the later of its claim's stimulus's position and the position of its ledger's latest pass at the revision it names.

| Constant | Meaning |
|---|---|
| `RefusalReturnsRevision` | The first gap. `TRUE` closes it. A refused request returns the revision the ledger was at, and the decision is made again with that ledger read as of it and the other ledger as of the revision the decision held. `FALSE` leaves it open. A refusal returns nothing, the decision is made again from the revisions held, so the request names the same revision again, and after `Retries` such refusals the claim gives up. |
| `RecordStart` | The second gap. `TRUE` closes it. The C pass records the revisions of both ledgers its decision was evaluated from, and a replay after a stop decides again from them. `FALSE` leaves it open. A replay finds the passes it wrote by their names, and evaluates from the latest revision of each ledger. |
| `Retries` | How many refusals with no revision a claim takes again before it gives up. |
| `MaxStops` | The most stops in a behaviour. A claim may stop once it has read C, and loses what it held in memory. |
| `WithReader` | Whether one reader reads C and later P, as X1's reader reads A and then B. |
| `Contracts`, `Aggregates`, `Orders` | The starting balances, and the order of the claims' stimulus positions, `E1First`, `E2First` or `Same`. |

| Name | Kind | Statement | Expected |
|---|---|---|---|
| `SerialClaims` | invariant | Once both claims are done, the contract's account, the aggregate and the claims paid are those that the two claims give evaluated whole one after the other, in one order or the other. | holds with both gaps closed |
| `NoHalfClaim` | invariant | Once both claims are done, each is drawn in both ledgers or in neither, a compensation counted. | fails with the first gap open |
| `NoStrandedHalf` | invariant | A claim that has stopped and not started again is drawn in both ledgers or in neither. X1's torn crash. | fails |
| `NoTornRead` | invariant | The reader saw each claim in both ledgers or in neither. X1's torn read. | fails |
| `PassOrderEach` | invariant | Each ledger's passes are in the order of their positions. | holds |
| `NotBeforeStimulus` | invariant | No pass takes a position before its claim's stimulus's. | holds |
| `OnePosition` | invariant | A claim's draw takes one position in both ledgers. | fails |
| `TypeOK` | invariant | Each variable stays in its range, and a claim's net draw on each ledger is 0 or 1. | holds |

What the model abstracts away.

- Two claims of one unit on one contract under one programme. A claim on another contract and a third writer are not modelled. With two claims on one contract a compensation follows a refusal on P, which only the other claim's P pass causes, so no claim decides from a draw that is later compensated.
- The order of the two passes is fixed, C then P.
- The compensation is a pass that restores the draw, and its request names the latest revision of C the claim knows. No text decides whether a compensation is a pass of the same evaluation or of another, or what it records.
- The start is recorded when the C pass is written. A claim that stops before that has written nothing, and evaluates from the latest revisions.
- A decision reads the two balances only. Positions do not enter it.
- Liveness is not checked. Every behaviour ends, since writes and refusals are bounded.

The model terminates, so TLC is run with `-deadlock`.

### `X2_AuditFlags.tla`

X2's audit, settled by a run. The module extends `X2_EvidenceAcrossStores.tla` and changes nothing in it. It adds one invariant. `AuditFindsStale` says the audit flags every stale decision, and this one says every decision it flags is stale, so the two together would make the audit exact.

| Name | Kind | Statement | Expected |
|---|---|---|---|
| `FlaggedIsStale` | invariant | Once S has reached `p`, a decision the audit flags carries a value that differs from what S held at `p`. | fails where a value can change and change back between the read and `p` |

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
| `PA_OnRead.cfg` | Protocol A | `OnRead`, `LaterOf`, a credit of one seat or a second activation of the same licence, `Concurrent`, one stop of either actor, the bundle at 0 to 3 and stated at 3, the quota at 0 to 2, every order of the stimuli | `TypeOK`, O1, O2, O3, O4 | no error |
| `PA_OnReadAligned.cfg` | Protocol A | `OnRead`, `LaterOf`, the Python model's instance: the bundle at 0, 1 or 2, the quota at 1 or 3, a credit of 3 seats that no ceiling cuts, a second activation of a licence of its own, the quota in the alert's guard, one stop of A | `TypeOK`, O1, O2, O3, O4 | no error |
| `PA_OnLatestO1.cfg` | Protocol A | `OnLatest`, otherwise as `PA_OnRead.cfg` | O1 | violated |
| `PA_OnLatestO3.cfg` | Protocol A | as `PA_OnLatestO1.cfg` | O3 | violated |
| `PA_PerPostingO1.cfg` | Protocol A | `PerPosting`, otherwise as `PA_OnRead.cfg` | O1 | violated |
| `PA_StimulusO3.cfg` | Protocol A | `OnRead`, `Stimulus`, `OneAfterAnother`, no stop, the cells of `PA_OnRead.cfg` | O3 | violated |
| `PA_Census.cfg` | Protocol A | every protocol, rule, second actor and mode, otherwise as `PA_OnRead.cfg` | `TypeOK`, `Census` | no error, and the census printed |
| `PA_CensusAligned.cfg` | Protocol A | every protocol, rule, second actor and mode on the instance of `PA_OnReadAligned.cfg` | `TypeOK`, `Census` | no error, and the census printed |
| `X6_Closed.cfg` | X6 | both gaps closed, two claims on one contract, one stop, the contract's account and the aggregate each at 0, 1 or 2, every order of the stimuli | `TypeOK`, `SerialClaims`, `NoHalfClaim`, `PassOrderEach`, `NotBeforeStimulus` | no error |
| `X6_ClosedTorn.cfg` | X6 | as `X6_Closed.cfg` with the reader | `NoTornRead` | violated |
| `X6_ClosedTornCrash.cfg` | X6 | as `X6_Closed.cfg` | `NoStrandedHalf` | violated |
| `X6_ClosedPositions.cfg` | X6 | as `X6_Closed.cfg` | `OnePosition` | violated |
| `X6_RefusalOpen.cfg` | X6 | the first gap open, `Retries=1`, otherwise as `X6_Closed.cfg` | `SerialClaims` | violated |
| `X6_RefusalOpenHalf.cfg` | X6 | as `X6_RefusalOpen.cfg` | `NoHalfClaim` | violated |
| `X6_StartOpen.cfg` | X6 | the second gap open, otherwise as `X6_Closed.cfg` | `SerialClaims` | violated |
| `X6_StartOpenHalf.cfg` | X6 | as `X6_StartOpen.cfg` | `TypeOK`, `NoHalfClaim`, `PassOrderEach`, `NotBeforeStimulus` | no error |
| `X2A_FlaggedIsStale.cfg` | X2 with `FlaggedIsStale` | the constants of `X2_BestKnownAudit.cfg`, `MaxPos=3` and two values, so a value can change and change back | `FlaggedIsStale` | violated |
| `X2A_FlaggedIsStaleOneStep.cfg` | X2 with `FlaggedIsStale` | `BestKnown`, `MaxPos=1`, a decision at 1 only, so no value can change back | `TypeOK`, `FlaggedIsStale`, `AuditFindsStale` | no error |
| `ModelB_Atomic.cfg` | B | `Atomic`, three writers, a bump, a resend | `TypeOK`, `OnePerPosition`, `NoLostAppend`, `FencedAppends` | no error |
| `ModelB_SnapshotDeleteWW.cfg` | B | `SnapshotDeleteWW`, three writers, no bump, a resend, `Retries=2` | the same | no error |
| `ModelB_SnapshotDeleteWWBump.cfg` | B | `SnapshotDeleteWW`, two writers, a bump, no resend, `Retries=1` | `TypeOK`, `FencedAppends` | `FencedAppends` violated |
| `ModelB_SnapshotInsertWWBump.cfg` | B | `SnapshotInsertWW`, otherwise as `ModelB_SnapshotDeleteWWBump.cfg` | `TypeOK`, `FencedAppends` | `FencedAppends` violated |
| `ModelB_SnapshotNoWW.cfg` | B | `SnapshotNoWW`, two writers, no bump, no resend | `TypeOK`, `OnePerPosition` | `OnePerPosition` violated |
| `ModelB_SnapshotNoWWLost.cfg` | B | as `ModelB_SnapshotNoWW.cfg` | `TypeOK`, `NoLostAppend` | `NoLostAppend` violated |
| `ModelC_Atomic.cfg` | C | `AbsentRow`, `Atomic`, three writers, a resend | `TypeOK`, `OneFirstWrite`, `OneHead` | no error |
| `ModelC_SnapshotInsertWW.cfg` | C | `AbsentRow`, `SnapshotInsertWW`, three writers, a resend, `Retries=2` | the same | no error |
| `ModelC_SnapshotDeleteWW.cfg` | C | `AbsentRow`, `SnapshotDeleteWW`, two writers, no resend, `Retries=1` | `TypeOK`, `OneFirstWrite` | `OneFirstWrite` violated |
| `ModelC_SnapshotDeleteWWHead.cfg` | C | as `ModelC_SnapshotDeleteWW.cfg` | `TypeOK`, `OneHead` | `OneHead` violated |
| `ModelC_PreCreatedAtomic.cfg` | C | `PreCreatedRow`, `Atomic`, three writers, a resend | `TypeOK`, `OneFirstWrite`, `OneHead` | no error |
| `ModelC_PreCreatedDeleteWW.cfg` | C | `PreCreatedRow`, `SnapshotDeleteWW`, three writers, a resend, `Retries=2` | the same | no error |
| `ModelC_PreCreatedNoWW.cfg` | C | `PreCreatedRow`, `SnapshotNoWW`, two writers, no resend | `TypeOK`, `OneFirstWrite` | `OneFirstWrite` violated |
| `ModelD_Atomic.cfg` | D | `Atomic`, three owners, no sentinel, a resend | `TypeOK`, `OneOwner` | no error |
| `ModelD_SnapshotInsertWW.cfg` | D | `SnapshotInsertWW`, three owners, no sentinel, a resend, `Retries=2` | the same | no error |
| `ModelD_SnapshotDeleteWW.cfg` | D | `SnapshotDeleteWW`, two owners, no sentinel, no resend, `Retries=1` | the same | `OneOwner` violated |
| `ModelD_SentinelDeleteWW.cfg` | D | `SnapshotDeleteWW`, three owners, the sentinel, a resend, `Retries=2` | the same | no error |
| `ModelD_SentinelNoWW.cfg` | D | `SnapshotNoWW`, two owners, the sentinel, no resend | the same | `OneOwner` violated |

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

A pass of the base tier prints the runner's tests, `24 passed`, then a line with the heap budget, then for each of the 86 configurations a `RUN` line and a `PASS` line. Forty `PASS` lines read "no error" and forty-six name the property violated, each as the manifest expects. It ends with the line below and exits 0.

```text
models: 86 as expected, 0 failed, 0 skipped, 0 stopped
```

On a machine of 8 GB the budget is at most 2 GB, which every base configuration fits, the largest heap given being 320 MB. The wide tier on such a machine skips each configuration whose heap exceeds the budget, with both figures, and exits 0 unless a verdict differs.

The peak heap is read from the GC log. The young generation is fixed at 16 MB, so a collection runs at least every 16 MB allocated, and the peak is the largest heap in use before a collection that the log printed. The true peak is at most 16 MB above it.

The module for a `ModelA_*.cfg` is `ModelA_GuardedCas.tla`, for a `ModelB_*.cfg` is `ModelB_AppendForm.tla`, for a `ModelC_*.cfg` is `ModelC_CreateRace.tla`, for a `ModelD_*.cfg` is `ModelD_KeyClaim.tla`, for an `X1_*.cfg` is `X1_SerialisedApply.tla`, for an `X1R_*.cfg` is `X1_ReceiptsOnly.tla`, for an `X2_*.cfg` is `X2_EvidenceAcrossStores.tla`, for an `X3_*.cfg` is `X3_ReceiptRelay.tla`, for an `X4_*.cfg` is `X4_AuthorityCutover.tla`, for an `X5_*.cfg` is `X5_WholeCommand.tla`, for a `PA_*.cfg` is `PA_PassRevision.tla`, for an `X6_*.cfg` is `X6_PassTwoLedgers.tla` and for an `X2A_*.cfg` is `X2_AuditFlags.tla`. TLC run by hand in this directory writes `states/` and any trace file here, and `.gitignore` excludes them.

## Trace validation

Models A to D and the multi-store model of [`spikes/multi-store-model/`](../../../spikes/multi-store-model/README.md) describe the same four operations. The multi-store model states each as a command of its IR, run by `exec` in one atomic step, and models A to D state each as a store's steps under an isolation level. The transitions are written apart, in TLA+ and in Isabelle. Trace validation holds them together. Every behaviour TLC finds for a configuration is run, step by step, through the interpreter Isabelle exports to Scala, and each step's outcome and the state after it must be the same in both.

| Model | The IR's command | Parameters the model gives |
|---|---|---|
| A | `delta_replace` with an empty delta | the target, epoch 1, the writer's expected sequence, and a revision, transaction id and digest of the writer's own |
| B | `append_event` | the stream, the epoch the writer read, a revision base, the writer's transaction id and digest, and one event row |
| C with `AbsentRow` | `create_if_absent` | the root, epoch 1, the writer's revision, transaction id and digest, and one payload fact |
| C with `PreCreatedRow` | `delta_replace` expecting seq 0 | as for `AbsentRow`, the payload fact asserted |
| D | `key_claim_write`, its constraint `k1` | the claim and the owner |

`mise run check:models-multi-store-traces`, which is [`tools/models/trace_validation.py`](../trace_validation.py), does the following.

1. The task first runs the check's own tests, `mise run check:models-multi-store-traces-runner`, which need neither Java, TLC nor Isabelle. The check finds TLC in the jar `TLA2TOOLS_JAR` names, Java as the runner does, and Isabelle as the formal-methods driver does. Where one is missing it says what it skipped and exits 0.
2. For each configuration the manifest marks with `trace`, it runs TLC with every invariant but `TypeOK` taken out, so that the whole state graph is explored, and has TLC dump the graph with each step's action, `-dump dot,actionlabels`, under `.build/formal/tlc-traces/<configuration>/`.
3. It reads each step of the graph. A step that is one request to the store is the IR's command, with the parameters above and the outcome the model gives it. A step with no IR command must leave the store as it was. These are a client's read, a store's evaluation against a snapshot, a store's aborted commit and a writer's resend. The bump of the dataset epoch changes the store and has no IR command, so the driver writes the new epoch into the IR's state as the entry the append's guard reads.
4. It walks the product of the state graph and a tree of the IR commands met so far, breadth first from each initial state, so a step reached by many behaviours with the same IR state before it is checked once. Every step of every behaviour is a step of this product, so checking every step of the product checks every step of every behaviour. The behaviours themselves are counted from the graph, not enumerated.
5. It builds and gates the session `MultiStoreModel`, exports its Scala, compiles it as generated with the spike's driver `replay/Replay.scala` and with [`TraceReplay.scala`](../TraceReplay.scala), and runs the tree through the interpreter in one call, under `.build/formal/multi-store-traces/`.
6. It compares, after every step, the outcome the model gives with the IR's, and the state the model holds with the IR's, each read into the lines both hold: the row's sequence, and its epoch and head where the model has them, the receipts with their position and transaction, the transaction claims, the events, the dataset epoch and the claim's owners. It prints the shortest behaviour that reaches the first disagreement of each kind.

A configuration marked `agree` fails where any step disagrees, and one marked `differ`, a store weaker than the IR's atomic step, fails where none does. A pass prints the runner's tests, `8 passed`, then the session's gate, then for each configuration a `PASS` line and ends with the line below.

```text
traces: 18 as expected, 0 failed, 2,672 interpreter steps
```

What the IR's state and the models' states hold differs, and only what both hold is compared.

| Model | The IR holds and the model does not | The model holds and the IR does not |
|---|---|---|
| A | the head, the transaction claim, the receipt's revision and previous head, the patch log and the aggregate's facts | each writer's program counter, the value it read and whether its snapshot's guard held |
| B | the row's head, the receipt's revision and previous head, the claim's revision and digest | the dataset epoch in force when an append applied, the statements each transaction wrote, and each writer's state |
| C | the row's epoch and tombstone flag, the receipt's revision and previous head, the claim's revision and digest, the patch log and the aggregate's facts | a second head on the row and a second receipt at seq 1, which an RDF store can hold and the IR's keyed entries cannot, the statements each transaction wrote, and each writer's state |
| D | nothing beyond the claim's constraint and owner | a second owner on the claim, which an RDF store can hold and the IR's one owner field cannot, the sentinel's counter, the statements each transaction wrote, and each owner's state |

The IR has no outcome for an aborted commit, which a model answers `Aborted` once its writer gives up, and no command for the bump of the dataset epoch.

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

The `PA_*`, `X6_*` and `X2A_*` configurations were run through `mise run check:models-multi-store` on 2026-11-24, with TLC 2.19 and TLA+ tools 1.7.4 on Java 25.0.2, one at a time under a heap of 2,048 MB given by `--heap-mb`, on 8 workers where no error was expected and one where a counterexample was. Another session ran its own JVMs on the machine at the time, so the times are those of a shared machine. Every one fits the base tier's budget, the largest peak 59 MB.

| Configuration | Result | States generated | Distinct states | Depth | TLC time | Wall time | Peak heap | Counterexample |
|---|---|---|---|---|---|---|---|---|
| `PA_OnRead` | no error | 2,664 | 1,764 | 7 | 01s | 3.1 s | 29 MB | none |
| `PA_OnReadAligned` | no error | 1,224 | 900 | 7 | 01s | 2.3 s | 28 MB | none |
| `PA_OnLatestO1` | `SerialOutcomes` violated | 1,662 | 1,234 | 5 | 03s | 4.9 s | 23 MB | The bundle at 0 and the quota at 0, two activations of one licence. Both read revision 0 and plan a refused alert and a move to overage. A's pass is written. O's is written on revision 1 as it was evaluated, and records a second move of a licence already on overage. Made one after the other, the second activation finds the licence on overage and writes nothing. |
| `PA_OnLatestO3` | `PassOrder` violated | 1,232 | 941 | 5 | 01s | 2.7 s | 15 MB | The bundle at 0 and the quota at 0, A's stimulus at 1 and a credit's at 2. Both read revision 0, where no pass is, and the credit is written at position 2. A's pass is written after it at position 1, the later of its stimulus's and the latest position it read. |
| `PA_PerPostingO1` | `SerialOutcomes` violated | 5,394 | 3,480 | 7 | 01s | 2.7 s | 28 MB | The bundle at 0 and the quota at 0, two activations of one licence. O reads and posts its refused alert. A reads revision 1 and posts its refused alert, then its move. O's move names revision 1, is refused, and is evaluated again from revision 3, where the licence is on overage, so O writes nothing more. O has a refused alert and no move, which no order of the two gives. |
| `PA_StimulusO3` | `PassOrder` violated | 505 | 505 | 5 | 00s | 1.6 s | 15 MB | The bundle at 0 and the quota at 0, A's stimulus at 1 and a credit's at 2, one after the other. The credit's pass is written at position 2, then A's at position 1. |
| `PA_Census` | no error, the census printed | 45,414 | 31,098 | 13 | 01s | 2.6 s | 59 MB | none |
| `PA_CensusAligned` | no error, the census printed | 21,012 | 15,976 | 14 | 01s | 2.9 s | 47 MB | none |
| `X6_Closed` | no error | 8,745 | 4,950 | 15 | 01s | 1.6 s | 28 MB | none |
| `X6_ClosedTorn` | `NoTornRead` violated | 2,788 | 1,406 | 6 | 00s | 1.4 s | 23 MB | The contract's account and the aggregate at 1. E1 reads both and writes its C pass. The reader reads C, which holds E1's draw, and then P, which does not. |
| `X6_ClosedTornCrash` | `NoStrandedHalf` violated | 687 | 435 | 5 | 00s | 1.3 s | 15 MB | E1 reads both ledgers, writes its C pass and stops before its P pass. |
| `X6_ClosedPositions` | `OnePosition` violated | 2,878 | 1,655 | 8 | 00s | 1.3 s | 27 MB | The contract's account at 2 and the aggregate at 1, E1's stimulus at 1 and E2's at 2. E2's C pass is written at position 2, then E1's at position 2, the later of its stimulus's and C's latest pass's. E1's P pass is written at position 1, since P has no pass. E1's draw is at 2 in C and at 1 in P. |
| `X6_RefusalOpen` | `SerialClaims` violated | 5,805 | 3,367 | 10 | 00s | 1.4 s | 28 MB | The contract's account and the aggregate at 2. E1 reads both ledgers and decides to pay. E2 reads C at revision 0. E1 writes both passes. E2 reads P at revision 1 and decides to pay. Its C pass names revision 0 and is refused. With no revision returned it names 0 again, is refused again and gives up. One claim is paid where one after the other both are. No stop is involved. |
| `X6_RefusalOpenHalf` | `NoHalfClaim` violated | 6,935 | 4,055 | 11 | 01s | 1.6 s | 28 MB | The contract's account at 2 and the aggregate at 1. E1 reads both at revision 0. E1 writes its C pass. E2 reads C at revision 1 and P at revision 0, and decides to pay. E1 writes its P pass, which empties the aggregate. E2 writes its C pass. Its P pass names revision 0 and is refused twice, and E2 gives up. E2 is drawn on the contract and not on the aggregate, and nothing compensates it. |
| `X6_StartOpen` | `SerialClaims` violated | 8,957 | 5,195 | 13 | 00s | 1.4 s | 28 MB | The contract's account and the aggregate at 1. E1 reads both, decides to pay, writes its C pass and stops. With no start recorded it reads C at its latest revision, where its own draw leaves the contract's account at 0, decides not to pay, and compensates its draw. E2 reads C before the compensation, finds 0, and decides not to pay. No claim is paid where one after the other one is. |
| `X6_StartOpenHalf` | no error | 13,911 | 8,256 | 20 | 01s | 1.7 s | 31 MB | none |
| `X2A_FlaggedIsStale` | `FlaggedIsStale` violated | 453 | 361 | 5 | 00s | 1.6 s | 15 MB | The core for position 2 reads "a" at position 0. S commits "b" at position 1 and "a" at position 2. The core commits the decision with "a" read at 0. S held "a" at 2, so the evidence is correct, and the audit flags it, since S changed at position 1. |
| `X2A_FlaggedIsStaleOneStep` | no error | 15 | 13 | 4 | 00s | 1.7 s | 15 MB | none |

The census lines were counted by starting cell. A revision cell is a starting balance with what O is, and a position cell is one with the order of the stimuli as well. "A stop allowed" counts every behaviour of the run, those with no stop among them, as the Python model's "with one crash" does.

| Instance | Protocol | O1 fails, no stop | O1 fails, a stop allowed | O2 fails | Outcomes no order gives, no stop |
|---|---|---|---|---|---|
| `PA_Census`, 24 revision cells | `OnRead` | 0 | 0 | 0 | 0 |
| | `OnLatest` | 12 | 12 | 0 | 17 |
| | `PerPosting` | 9 | 9 | 0 | 38 |
| `PA_CensusAligned`, 12 revision cells | `OnRead` | 0 | 0 | 0 | 0 |
| | `OnLatest` | 5 | 5 | 0 | 9 |
| | `PerPosting` | 7 | 7 | 0 | 9 |

| Instance | Protocol | Rule | O3 fails, one after another | O3 fails, no stop | O3 fails, a stop allowed | O4 fails |
|---|---|---|---|---|---|---|
| `PA_Census`, 72 position cells | `OnRead` | `Stimulus` | 36 | 36 | 36 | 0 |
| | `OnRead` | `LaterOf` | 0 | 0 | 0 | 0 |
| | `OnLatest` | `Stimulus` | 36 | 48 | 48 | 0 |
| | `OnLatest` | `LaterOf` | 0 | 48 | 48 | 0 |
| | `PerPosting` | `Stimulus` | 36 | 48 | 48 | 0 |
| | `PerPosting` | `LaterOf` | 0 | 0 | 0 | 0 |
| `PA_CensusAligned`, 36 position cells | `OnRead` | `Stimulus` | 24 | 24 | 24 | 0 |
| | `OnRead` | `LaterOf` | 0 | 0 | 0 | 0 |
| | `OnLatest` | `Stimulus` | 24 | 24 | 24 | 0 |
| | `OnLatest` | `LaterOf` | 0 | 24 | 24 | 0 |
| | `PerPosting` | `Stimulus` | 24 | 24 | 24 | 0 |
| | `PerPosting` | `LaterOf` | 0 | 0 | 0 | 0 |

The configurations of models B, C and D were run through `mise run check:models-multi-store` on 2026-11-24, with TLC 2.19 and TLA+ tools 1.7.4 on Java 25.0.2, under a heap of 2,048 MB given by `--heap-mb`, on 8 workers where no error was expected and one where a counterexample was. Another session ran its own JVMs on the machine at the time. Every one fits the base tier's budget, the largest peak 29 MB. Each counterexample is the trace TLC printed with one worker.

| Configuration | Result | States generated | Distinct states | Depth | TLC time | Wall time | Peak heap | Counterexample |
|---|---|---|---|---|---|---|---|---|
| `ModelB_Atomic` | no error | 5,301 | 2,652 | 14 | 00s | 1.3 s | 28 MB | none |
| `ModelB_SnapshotDeleteWW` | no error | 17,686 | 7,179 | 25 | 00s | 1.4 s | 29 MB | none |
| `ModelB_SnapshotDeleteWWBump` | `FencedAppends` violated | 40 | 33 | 5 | 00s | 1.2 s | 18 MB | A writer reads the dataset epoch 1 and its append is evaluated against a snapshot. The epoch is bumped to 2. The append commits, since it wrote no statement the bump wrote, and lands with epoch 1 after the bump. |
| `ModelB_SnapshotInsertWWBump` | `FencedAppends` violated | 40 | 33 | 5 | 00s | 1.2 s | 18 MB | The same trace as `ModelB_SnapshotDeleteWWBump`. |
| `ModelB_SnapshotNoWW` | `OnePerPosition` violated | 25 | 19 | 7 | 00s | 1.2 s | 18 MB | Both writers read the epoch, and both appends are evaluated against a snapshot where the row is at 0. Both commit, and both take position 1. |
| `ModelB_SnapshotNoWWLost` | `NoLostAppend` violated | 25 | 19 | 7 | 00s | 1.5 s | 18 MB | The same trace. The row is at 1 after two appends. |
| `ModelC_Atomic` | no error | 64 | 37 | 6 | 00s | 1.3 s | 18 MB | none |
| `ModelC_SnapshotInsertWW` | no error | 1,306 | 596 | 14 | 00s | 1.4 s | 18 MB | none |
| `ModelC_SnapshotDeleteWW` | `OneFirstWrite` violated | 13 | 12 | 5 | 00s | 1.2 s | 15 MB | Both creates are evaluated against a snapshot with no row. Both commit, since neither deletes a statement. The row has two first writes. |
| `ModelC_SnapshotDeleteWWHead` | `OneHead` violated | 13 | 12 | 5 | 00s | 1.2 s | 15 MB | The same trace. The row has two heads. |
| `ModelC_PreCreatedAtomic` | no error | 64 | 37 | 6 | 00s | 1.2 s | 18 MB | none |
| `ModelC_PreCreatedDeleteWW` | no error | 1,306 | 596 | 14 | 00s | 1.3 s | 18 MB | none |
| `ModelC_PreCreatedNoWW` | `OneFirstWrite` violated | 13 | 12 | 5 | 00s | 1.2 s | 15 MB | Both first writes are evaluated against a snapshot with the row at 0. Both delete seq 0 and commit, and no conflict is detected. |
| `ModelD_Atomic` | no error | 64 | 37 | 6 | 00s | 1.3 s | 18 MB | none |
| `ModelD_SnapshotInsertWW` | no error | 1,474 | 692 | 14 | 00s | 1.2 s | 18 MB | none |
| `ModelD_SnapshotDeleteWW` | `OneOwner` violated | 13 | 12 | 5 | 00s | 1.1 s | 15 MB | Both claims are evaluated against a snapshot with no owner. Both commit, since neither deletes a statement. The claim names two owners. |
| `ModelD_SentinelDeleteWW` | no error | 1,474 | 692 | 14 | 00s | 1.2 s | 17 MB | none |
| `ModelD_SentinelNoWW` | `OneOwner` violated | 13 | 12 | 5 | 00s | 1.2 s | 15 MB | Both claims are evaluated against a snapshot with no owner and the counter at 0. Both delete it and commit, and no conflict is detected. |

The trace validation was run with `mise run check:models-multi-store-traces` on 2026-11-24, the interpreter compiled and run by Isabelle's `isabelle scalac` and `isabelle scala`, with TLC 2.19 dumping each graph on one worker. A behaviour runs from an initial state to a state with no successor, and its count and its steps are counted from the graph. The checks are the steps of the product of the graph and the IR's states, each checked once, and the pairs are its states. The tree the interpreter ran had 2,672 nodes over the 18 configurations.

| Configuration | Expected | Result | Behaviours | Their steps | Of them store steps | Checks | Pairs | The IR's outcomes over the checks |
|---|---|---|---|---|---|---|---|---|
| `ModelA_Atomic` | agree | every step agrees | 90 | 540 | 270 | 79 | 107 | `Applied` 42, `Conflict Stale` 36 |
| `ModelA_SnapshotNoWWDetect` | differ | 60 outcomes and 12 states differ | 1,680 | 15,120 | 5,040 | 202 | 327 | `Applied` 81, `Conflict Stale` 120 |
| `ModelB_Atomic` | agree | every step agrees | 278,418 | 3,571,950 | 1,925,184 | 4,737 | 5,567 | `Applied` 681, `Duplicate` 1,689, `Refused EpochMismatch` 1,704 |
| `ModelB_SnapshotDeleteWW` | agree | every step agrees | 363,363,336 | 8,275,348,368 | 2,180,180,016 | 9,880 | 11,235 | `Applied` 1,215, `Duplicate` 8,664 |
| `ModelB_SnapshotDeleteWWBump` | differ | 18 outcomes and 10 states differ | 164 | 1,300 | 492 | 108 | 177 | `Applied` 34, `Refused EpochMismatch` 48 |
| `ModelB_SnapshotInsertWWBump` | differ | 18 outcomes and 10 states differ | 164 | 1,300 | 492 | 108 | 177 | `Applied` 34, `Refused EpochMismatch` 48 |
| `ModelB_SnapshotNoWW` | differ | 2 states differ | 20 | 120 | 40 | 11 | 21 | `Applied` 10 |
| `ModelC_Atomic` | agree | every step agrees | 36 | 180 | 144 | 61 | 64 | `Applied` 3, `Conflict Exists` 42, `Duplicate` 15 |
| `ModelC_SnapshotInsertWW` | agree | every step agrees | 37,590 | 472,710 | 150,360 | 532 | 752 | `Applied` 12, `Conflict Exists` 360, `Duplicate` 159 |
| `ModelC_SnapshotDeleteWW` | differ | 2 outcomes differ | 6 | 24 | 12 | 9 | 14 | `Applied` 4, `Conflict Exists` 4 |
| `ModelC_PreCreatedAtomic` | agree | every step agrees | 36 | 180 | 144 | 61 | 64 | `Applied` 3, `Conflict Stale` 42, `Duplicate` 15 |
| `ModelC_PreCreatedDeleteWW` | agree | every step agrees | 37,590 | 472,710 | 150,360 | 532 | 752 | `Applied` 12, `Conflict Stale` 360, `Duplicate` 159 |
| `ModelC_PreCreatedNoWW` | differ | 2 outcomes differ | 6 | 24 | 12 | 9 | 14 | `Applied` 4, `Conflict Stale` 4 |
| `ModelD_Atomic` | agree | every step agrees | 36 | 180 | 144 | 61 | 64 | `Applied` 18, `Conflict HeldByOther` 42 |
| `ModelD_SnapshotInsertWW` | agree | every step agrees | 37,590 | 472,710 | 150,360 | 688 | 872 | `Applied` 171, `Conflict HeldByOther` 516 |
| `ModelD_SnapshotDeleteWW` | differ | 2 outcomes differ | 6 | 24 | 12 | 9 | 14 | `Applied` 4, `Conflict HeldByOther` 4 |
| `ModelD_SentinelDeleteWW` | agree | every step agrees | 37,590 | 472,710 | 150,360 | 688 | 872 | `Applied` 171, `Conflict HeldByOther` 516 |
| `ModelD_SentinelNoWW` | differ | 2 outcomes differ | 6 | 24 | 12 | 9 | 14 | `Applied` 4, `Conflict HeldByOther` 4 |

The first disagreement of each kind, as the check printed it.

| Configuration | The shortest behaviour | What differs |
|---|---|---|
| `ModelA_SnapshotNoWWDetect` | w1 reads and is evaluated, w2 reads and is evaluated, w1 commits, w2 commits | the model applies w2's write, the IR answers `Conflict Stale`, and the model holds a second receipt at 1 |
| `ModelB_SnapshotDeleteWWBump` | w1 reads the epoch and is evaluated, the bump, w1 commits | the model applies the append, the IR answers `Refused EpochMismatch`, and the model's row, receipt, claim and event are ones the IR does not write |
| `ModelB_SnapshotNoWW` | w1 reads and is evaluated, w2 reads and is evaluated, w1 commits, w2 commits | both answer `Applied`, and the model puts w2's append at position 1 where the IR puts it at 2, so the row is at 1 in the model and at 2 in the IR |
| `ModelC_SnapshotDeleteWW` | w1 and w2 are evaluated, w1 commits, w2 commits | the model applies w2's create, the IR answers `Conflict Exists`, and the model holds w2's head, receipt and claim |
| `ModelC_PreCreatedNoWW` | as above | the model applies w2's first write, the IR answers `Conflict Stale` |
| `ModelD_SnapshotDeleteWW`, `ModelD_SentinelNoWW` | o1 and o2 are evaluated, o1 commits, o2 commits | the model applies o2's claim, the IR answers `Conflict HeldByOther`, and the model's claim names o2 as well |

## What the results say

- The guard in each store, and the offset stored as applied, give a row that is ordered, applies each command at most once in effect, and applies every confirmed command eventually, for up to three incarnations including a zombie that keeps acting. The zombie's late applies are answered `Duplicate`.
- The row does not give atomic visibility. A reader of two stores sees them at different versions in every configuration, with no crash needed, because the two applies are separate steps. A crash between them leaves A ahead until a successor replays, which is why the catalogue row reads ordered and eventually applied and a read that must be correct reads one store or waits on a watermark.
- Storing the highest received offset loses commands. A command received but not applied is skipped after a crash and the commands after it are rejected by the guard, so the stores stop short of the stream. The safety properties still hold in that run, so the guard turns the defect into a missing command and never into a wrong one.
- Taking the guard out of the stores breaks at-most-once in effect as soon as a second writer acts on the same command, which is the reason a store with no guard cannot take the row.
- A decision that reads the watermark first and then the value as of `p` carries evidence that equals what the source held at `p`, and the evaluation waits. If the source stalls, the evaluation never completes, which is the cost of the row. The best known read never waits and completes in every configuration run, but its evidence can differ from what the source held at `p`. In the configurations run the audit found every such decision, because the read set records the position read at. TLC also printed a decision that the audit flags and whose evidence is correct. The core for position 2 read "a" at position 0, S committed "b" at 1 and "a" at 2, and the decision carries "a", which S held at 2. So the audit is a trigger for review and not a verdict. With S one position past the start and a decision at that position only, where no value can change back, TLC found no flagged decision whose evidence was correct.
- A relay that publishes by one global commit position skips a receipt that commits after a later position has been published, and a restart does not repair it. The skip breaks order within a stream, since a later receipt of the stream can be published first. A relay that tracks the next seq of each stream publishes every receipt in order in the configurations run, and a restart makes it publish some receipts twice, so the consumer has to be idempotent.
- Copying and then flipping the authority loses a write that the old authority acknowledges between the copy and the flip. Fencing the old authority before the copy loses none in the configurations run. A writer that times out and resends can have the same write acknowledged by both stores without a fence. With the fence it is acknowledged once in the configurations run, and every write is acknowledged in the end.
- Stores that keep a receipt for each command and no row for the partition keep every property of X1 with offsets stored as applied, for one writer at a time and for up to three incarnations including a zombie. TLC printed the same counts as for X1 with the guard, so in those configurations the partition's row refused nothing that the receipts did not answer.
- With received offsets the same stores keep at-most-once, order within each store and `AThenB`, and lose eventual application as X1 does. They also let store B apply command 3 after it missed command 2, which X1's guard refused, so a gap in the second store is reachable and nothing in the store stops it. S1 as X1 states it and `VersionStepsByOne` fail by the same trace, since the last command applied no longer counts the commands applied.
- The studio's writer as built reaches states that no sequence of whole commands gives when two writers do not share one order. A deletion is answered from a receipt while the document it deletes is live and unlisted, until a later request removes it. A deletion whose description step lost tombstones the document while the description still lists it, with no receipt. Where each writer takes the stream in order from the stored offset, TLC found no such state, for two writers in either order of the stream and for three writers with two crashes. We read this as the transaction ids doing the work, since a step that another delivery applied writes nothing, and a writer reaches a command only after it has finished every earlier one. That is a reading of the runs and not a proof.
- The answers as built disagree even in stream order. A writer that read no receipt plans after another writer applied the command, and answers a save stale although it was applied.
- One guard over every row a command writes reaches only states that whole commands give, in both deliveries in the configurations run, and its answers disagree by the same trace as the design as built.
- One guard with the epoch in every request also reaches only such states in the configurations run, and its answers still disagree. The writer that lost the partition answers a command its own check refuses without sending a request, so the epoch never reaches that answer. Answering such a command from one read of its rows, the epoch and its receipt removes the disagreement in the configurations run, for two writers in either delivery and for three writers in stream order.
- In the wide tier TLC printed "Model checking completed. No error has been found." for every configuration it finished. So the serialised writer kept S1, S2, `AThenB` and L1 with four commands and a window of three, with and without a zombie, over 279,119 distinct states. The watermark read kept its evidence and completed, and the audit of the best known read flagged every stale decision, with S reaching position 4 and a decision at each of positions 1 to 4. The relay by each stream's next seq kept order and published every receipt with four receipts in a stream, or three streams, and with a restart and three receipts in a stream. The fenced cutover kept every acknowledged write, acknowledged none twice and acknowledged every write, with four writes for each writer or three writers, with and without timeouts, and the naive cutover without timeouts acknowledged no write twice. Each holds for the constants run and no others. With a restart and four receipts in a stream, or a restart and three streams of two receipts, TLC was stopped at 30 minutes with its heap of 8 GB full and no error printed by then, after more than 15 million distinct states. Nothing is concluded for those two instances, since TLC had not reached every state.
- A pass written as one request on the revision it was evaluated from kept every outcome one that the two evaluations give made one after the other, with a stop and without, and every outcome with a stop one that a behaviour without a stop reaches. With the later of the stimulus's position and the latest pass's, read with the revision, the passes stayed in the order of their positions and none fell before its stimulus. TLC printed "No error has been found" for `PA_OnRead` on this model's own instance and for `PA_OnReadAligned` on the Python model's, and the census found no cell in which `OnRead` with `LaterOf` broke O1 to O4. These are the Python model's conclusions for its protocol A, reached by a second model written without reading it.
- Written on whatever revision is latest, a pass broke O1 with a second activation and never with a credit, in 12 of 12 starting balances on this model's instance and 5 of 6 on the Python model's. The stale pass is written as it was evaluated, so it can record what the state no longer allows, for example a move of a licence already on overage. Its position, read before another pass landed, fell behind that pass's in every cell where the stimuli's positions differ, 48 of 72 and 24 of 36.
- Each posting a request of its own broke O1 in 9 cells on this model's instance and 7 on the Python model's, the same 7 cells in which the Python model's three variants of a posting written alone break it. A refused posting evaluated again from the revision found leaves the pass's earlier postings written, so a pass ends with part of what it evaluated, for example a refused alert and no move.
- A pass at its stimulus's position broke the order of positions with the actors one after another, in 36 of 72 cells and 24 of 36, which by our count are the cells where both write a pass and the stimuli's positions differ.
- In the census no variant broke O2 or O4. A stop in this model falls only while an actor holds a plan, and a pass's records, the move to overage among them, are written in its one request, so a stop never falls between a pass and what it records.
- Over two ledgers, with the refusal returning the revision it found and the C pass recording the revisions its decision started from, every outcome was one that the two claims give evaluated whole one after the other, each claim ended in both ledgers or in neither, and each ledger's passes kept the order of their positions, with one stop. TLC printed "No error has been found" for `X6_Closed`. What it does not give is what X1's row does not give. A reader of C and then P sees a claim in one ledger and not the other, and a claim stopped between its passes leaves C ahead until it starts again. A claim's two passes also take different positions, since each takes the later of its stimulus's and its own ledger's latest pass's.
- Returning the revision found is what lets a refused claim go on. With the refusal returning nothing, the claim names the revision it already held, is refused again, and gives up, with no stop needed. TLC printed a claim not paid where one after the other both are, and a claim drawn on the contract and not on the aggregate, which nothing compensates.
- Recording the start is what keeps a replay's decision the one it wrote under. With no start recorded, a claim that stopped after its C pass read its own draw as the contract's account being empty, decided not to pay and compensated a claim that one after the other is paid. Each claim still ended in both ledgers or in neither, since the replay compensated what it had drawn. TLC printed "No error has been found" for `X6_StartOpenHalf`, so in these constants the second gap costs a wrong decision and never a half claim.
- An append whose store computes the next position keeps one receipt for each position and a row that counts its appends on a store that serialises its writers, and on a snapshot store that detects a statement both transactions delete, since two appends from one snapshot delete the same sequence statement and one of them is aborted and sent again. TLC printed "No error has been found" for `ModelB_Atomic` with three writers, a bump and a resend, and for `ModelB_SnapshotDeleteWW` with three writers and a resend. A snapshot store that detects no conflict gives two appends one position and loses one from the row's count.
- The dataset guard does not fence a write already evaluated on a snapshot store. An append evaluated against the epoch before a bump commits after it, with the old epoch, on a store that detects a statement both delete and on one where inserting an identical statement also conflicts, since the append writes no statement the bump writes. A store that serialises its writers refused every such append in `ModelB_Atomic`. This is the case the persistence README's sixth obligation, to quiesce writers at a bump, is there for.
- A create that inserts its row races on a snapshot store that detects only a statement both delete, since a create deletes nothing. Two creates of one root both commit, and the row holds two first writes and two heads. Where inserting an identical statement is a conflict, the row's shared type, epoch and seq statements collide, one create is aborted, and on its next send it is answered `Conflict Exists`, so TLC printed "No error has been found" for `ModelC_SnapshotInsertWW`. A row created beforehand at seq 0 makes the first write delete the seq 0 statement, so a store that detects only a statement both delete aborts one of two first writes, and `ModelC_PreCreatedDeleteWW` printed no error. On a store that detects no conflict, the row created beforehand does not help.
- A key claim deletes nothing either, and its owner differs from writer to writer, so on a snapshot store that detects only a statement both delete two owners claim one key. Where inserting an identical statement is a conflict, the claim's shared type and constraint statements collide and one owner is aborted and then refused. The sentinel counter of the patterns guide gives racing claims a statement both delete, and with it `ModelD_SentinelDeleteWW` printed no error. On a store that detects no conflict, the sentinel does not help.
- In every configuration marked to agree, each step of each behaviour TLC found gave the same outcome and the same state in the model and in the interpreter exported from the Isabelle model, for the four operations under a store that serialises its writers, for the append under a snapshot store that detects a statement both delete, for the create and the claim where inserting an identical statement is a conflict, and for the first write of a row created beforehand and the claim with a sentinel where only a statement both delete is. So in those configurations the store's steps are steps of the IR's `exec`, every outcome compared among them, `Applied`, `Duplicate`, `Conflict Exists`, `Conflict Stale`, `Conflict HeldByOther` and `Refused EpochMismatch`.
- In every configuration marked to differ, the first disagreement is the step where the model's store commits what its snapshot computed and the IR, run on the state at that step, refuses it or computes it again. For the append on a store with no conflict detection the outcomes agree and the states differ, since the IR computes the next position from the state at the commit and the model from the snapshot. Each store whose traces are not traces of `exec` is one under which TLC found a property violated in the configurations above.
- The models need, and the IR's state lacks, a way to hold two heads, two receipts at one position and two owners of a claim, which is what an RDF store that misses a conflict writes. The IR keys a receipt by its target, epoch and sequence and holds one head and one owner, so such a state shows in the comparison as a line the model holds and the IR does not. The IR has no command for the bump of the dataset epoch, which the driver writes into the IR's state, and no outcome for an aborted commit. Each holds for the constants run and no others.
