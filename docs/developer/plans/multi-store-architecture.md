<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: multi-store architecture

**Unit ID:** `multi-store-architecture`
**Prefix:** MSA
**Status:** planned 2026-11-17, from the [sketch](../sketches/multi-store-architecture.md) of 2026-11-12. The maintainer confirmed the unit's name and prefix on 2026-11-17 (MSA-Q14)
**Status record:** [multi-store-architecture.md](../status/multi-store-architecture.md)
**Decisions it builds on:** the sketch's D1 to D6, ADR-A48, ADR-A74, ADR-A75, ADR-A123, ADR-A124, ADR-A125, PRI-51, PRI-52
**Placement:** open. Platform, tooling and substrate configuration, nothing domain-specific

## Why

The sketch's §2 shows the fault the epic starts from: the logical contract of a generated operation is derived from its SPARQL, so a second realisation has nothing to be lowered from. The sketch states leanings about placement, crossings, the neutral IR, the mapping and the port, each ratified by the maintainer as a leaning and none decided. This plan runs the twelve investigations of its §6, which try to disprove those leanings cheaply before anything is built.

## Outcome

Each investigation reports whether the leaning it tests survives, with the evidence, against the falsifier the sketch's §6 states for it. The questions MSA-Q1 to MSA-Q18 are then put to the maintainer with that evidence. Building the port, the IR or a relational realisation is the next plan's, written on the answers.

## Out of scope

Everything the sketch's §9 leaves out. Any change to `tools/persistence`, the port or the store SPI beyond what an investigation needs to measure, and none of that merges into code that runs. Amending the texts in the sketch's §8, which waits for the answers.

## Order and dependencies

The sketch's §4.14 order holds. The persistence model rests on no ledger law, so MSA-I1, MSA-I3, MSA-I4, MSA-I9, MSA-I11 and MSA-I12 start now. MSA-I2 reads the ledger's examples and MSA-I5 uses the proof gate, and both take the ledger branch first. MSA-I7, MSA-I8 and MSA-I10 name the ledger's records and wait for its runtime document, LG-2. MSA-I6 waits on the choice of a protocol toolchain. The dependency graph is the sketch's §6.

## Slices

Each slice is the sketch's investigation of the same identifier, with the falsifier and estimate its §6 gives. One Validation Pack each, `docs/developer/validation/MSA-I<n>.md`.

| Slice | Kind | Where its work lives | Waits on |
|---|---|---|---|
| MSA-I1 | script | `spikes/multi-store-shape-census/` | the threshold, proposed below |
| MSA-I2 | paper | `docs/developer/notes/multi-store/` | the ledger branch |
| MSA-I3 | paper | `docs/developer/notes/multi-store/` | none |
| MSA-I4 | paper | `docs/developer/notes/multi-store/` | MSA-I3 |
| MSA-I5a | proofs | `tools/proofs/shared/` | none, ADR-A-FM2's addendum of 2026-11-18 is accepted |
| MSA-I5 | proofs | `spikes/multi-store-model/` | MSA-I4, the ledger branch's proof gate, and MSA-I5a, the shared session that holds a position and an amount (sketch §4.14) |
| MSA-I6 | models | `tools/models/<topic>/` | MSA-I2, MSA-I9, and the choice of TLA+ or Quint (Track H records it as not chosen) |
| MSA-I7 | benchmark | `benchmark/` | the ledger's runtime document, LG-2 |
| MSA-I8 | proof of concept | `spikes/` | MSA-I5, MSA-I6, MSA-I7, MSA-I10, MSA-I14 and the ledger's design |
| MSA-I9 | probes | `spikes/multi-store-stream-probes/` | none |
| MSA-I10 | paper | `docs/developer/notes/multi-store/` | MSA-I1, LG-2 |
| MSA-I11 | paper | `docs/developer/notes/multi-store/` | MSA-I4 |
| MSA-I12 | proof of concept | `spikes/multi-store-emitted-topology/` | none |
| MSA-I13 | test support | `tools/testing/postgres/` | none |
| MSA-I14 | paper, with a model | `docs/developer/notes/multi-store/`, `tools/models/multi-store-protocols/` | none. MSA-I8 waits on it |

## Decided by the maintainer, 2026-11-17

- **MSA-Q14.** The unit is `multi-store-architecture`, prefix MSA, and its slices are its investigations and the fixes below.
- **MSA-I1's threshold.** A mapping is worth building where at least 80% of the subjects of a family's sample graphs fall under shapes that are bounded, counted only for the families chosen for a relational realisation. Closure is declared by the mapping, since a row is closed by construction and the shapes are open by convention. The census of MSA-I1 found 0% on the strict reading and 43.4% bounded across the estate, so a mapping derived from the shapes alone is not built, and a mapping written for a family and checked against its shapes is what MSA-I10 tests.
- **MSA-I6's toolchain.** TLA+ with TLC. The models are small protocols, and the property that a confirmed write is eventually applied is one of liveness, which TLC checks. The choice is Track H's FMH-5 toolchain spike, which adopts it.

## Decided by the maintainer, 2026-11-18

The answers to the status record's next action of 2026-11-18, and the maintainer's brief of the same day, written on `docs/placement-vehicles-structure`.

- **MSAF6-01.** A deletion wins over a save that moves the row's revision first. The tombstone is planned again at the revision the row then has, while the row is live, so the first send removes the row, and a resend is never needed. MSA-F7.
- **MSA-F2's second half.** A failure of the writer's own code stays unretried, and is answered as the writer's fault, a 500, not as a refusal of the request. MSA-F8.
- **MSA-F3's departure.** Confirmed: the receipt holds the command's own digest, `cst:requestDigest`.
- **MSAF6-02.** The reply to a new document's save that lost the description's guard reads the document's own row. MSA-F9.
- **The ledger's unit.** The owner's ledger, every account of one owner, is the unit that is consistent, serialised and placed in one store, and an account still owns its postings (the ledger plan's LG-Q44, ADR-A131's addendum proposed 2026-11-18). A ledger is a node holding the revision, and each pass records the revision it moved the ledger to (LG-Q37, built by the ledger's LG-27). The rule MSA-I2 proposed, placing an identity's Behaviour state with its ledger, was not taken, since a read by revision is pinned. MSA-I2 is reworked on it.
- **The shared types.** A proof session of their own, `tools/proofs/shared/`, built as MSA-I5a once ADR-A-FM2's addendum proposed 2026-11-18 is accepted, generic over an ordered ring. What a position is stays proposed.
- **MSAI4-03, the order of the guards.** A resend is answered before a conflict, so a command already applied is always answered as applied.
- **MSAI4-05, who advances a sequence.** The store computes the successor in both the append and the delta replace, and the caller's expected current value stays the guard.
- **MSAI4-06, what the patch log holds.** The delta as requested, stated as such. An audit that needs effects derives them by replaying the log.

## Decided by the maintainer, 2026-11-18

- **MSA-Q1, for the ledger's families.** The unit of placement is the owner's ledger, every account of one owner, which is also the unit that is consistent and that one writer serialises (LG-Q44 of the [ledger plan](ledger.md), ADR-A131's addendum of 2026-11-18). An account still owns its postings and a period's unit is still the partition. The census of MSA-I2 counts a read of another account of the same ledger as inside the unit.
- **A guard outside the ledger reads a balance as of a revision.** The read is of a fact that does not change, so it is no read of changeable state in another store. The proposal that an identity's Behaviour state be placed with its ledger is not taken. The revision a pass records is a term of the ledger's LG-27 and is not built yet.
- **MSA-Q19, where the shared types live.** In a new small proof session, `tools/proofs/shared/`, `LatticeShared`, hand-written and gated (ADR-A-FM2's addendum of 2026-11-18). Never in the prelude and never in the ledger's session. It is MSA-I5a, built before MSA-I5.
- **MSA-Q21, the number type.** It stays generic over an ordered ring. A model that only stores an amount treats it as a value of any type.

- **MSA-Q20, what a position is.** Confirmed by the maintainer on 2026-11-18, in the same addendum to ADR-A-FM2. A natural number on a named axis, compared only within its axis. On a sequence the writer assigns the next number, with no gap, inside the write the axis serialises, and 0 means nothing is written yet. On an effective axis the arrangement assigns it, and it may skip or be shared. The [brief of 2026-11-18](../notes/machine-s-brief-2026-11-18.md) says what a relational store has to respect for it to hold.

## Decided by the maintainer, 2026-11-19

- **C1 to C3 of MSA-I2.** A pass is evaluated from one revision of a ledger and written as one request, which moves the revision once and is refused when the ledger has moved (LG-Q45 and LG-Q46 of the [ledger plan](ledger.md), ADR-A131's second addendum of 2026-11-19). Behaviour states its half when it imports Ledger, and the plan that builds the logical port states the port's half (PDD-22).
- **The port's half, a finding of MSA-I11 for that plan.** A write on the port names the revision it expects. It returns the revision it produced or, where it is turned away, the revision it found. MSA-I8 builds to this.
- **A pass over two ledgers is not decided.** Each ledger takes a request of its own. MSA-I6 models it with the saga row.
- **MSA-I13, a PostgreSQL test fixture,** is added and built first, since the isolation probes of MSA-I6, MSA-I7 and MSA-I8 stand on it. It runs on Windows, macOS and a cloud session.
- **MSA-I5 is built in Isabelle on machine S.** The Rocq formalisation of the sketch's §4.14 stays in the plan and is built off machine S on Rocq 9.3.0, the version the earlier spike's claim records name, once `exec` and its laws exist.
- **Branches.** `spi/multi-store-architecture` is a merging point. Machine S works on `spi/worktree-s`, by the [brief of 2026-11-19](../notes/machine-s-brief-2026-11-19-multi-store.md) and its [ledger half](../notes/machine-s-brief-2026-11-19.md).

## Fixes to running code

The investigations found five defects in code that runs and one design point to test, and later answers and a review added six more slices. Each is a slice of its own, built in this order, with a test that fails before the fix and passes after it. The order puts first the one that can lose a confirmed write.

| Slice | Fix | Finding |
|---|---|---|
| MSA-F1 | the studio's stream writer stores only offsets it has applied, by stream and offset through the environment, so a stop skips no confirmed write | MSAI9-06 |
| MSA-F2 | a batch the store refuses for a reason that a retry cannot change is answered and the stream goes on, and only a store that cannot be reached is retried | MSAI11-05 |
| MSA-F3 | a command id resent with a different body is refused, its digest compared with the one its claim holds | MSAI11-02 |
| MSA-F4 | the queue topology states each queue's dead-letter binding once, and the Python worker and the Java service declare the same broker objects from it | MSAI12-01 |
| MSA-F5 | the event's logical key names one event, not one append, in the persistence contract | MSAI4-04 |
| MSA-F6 | a test that a command writing several aggregates, whose later guard fails, leaves nothing a reader acts on and is completed by a resend | MSAI11-01 |
| MSA-F7 | a deletion whose tombstone loses a race to a save of the same part or document still removes it, the tombstone planned again at the revision the save left | MSAF6-01 |
| MSA-F8 | a failure of the stream writer's own code is answered as the writer's fault, a 500, and the service answers it 500 | MSA-F2 |
| MSA-F9 | a new document's save that loses the description's guard is answered as a change to send again, read from the document's own row, not as a deleted id | MSAF6-02 |
| MSA-F10 | the stream writer's thread survives a reply or an offset that cannot be sent or stored, and a writer that cannot go on leaves its group, so no partition is held by a member that applies nothing | MSAF2-01 |
| MSA-F11 | a deletion answered from its receipt still removes a row its tombstone lost, so a batch that fails after its update commits is completed by its retry | MSAF7-01 |
| MSA-F12 | a reply built from an exception carries a fixed message, and the exception's text goes to the log with the command's id | MSAF8-01 |
| MSA-F13 | the Java topology refuses a queue whose `bindsTo` names no declared exchange, as the Python worker does | the review of MSA-F4 |
| MSA-F14 | a command's digest separates two bodies that differ in how their blank nodes connect, each blank node labelled by a hash of its own quads. Built only where a studio command's body can hold a blank node | TD-165 |
| MSA-F15 | a creation under a document id that has a version row, live or tombstoned, is refused, so a document whose removal is not finished cannot be listed again with what it held. It also tests a deletion delivered twice after a lost tombstone | TD-168, TD-171 |

MSAI11-01 is by design under [ADR-A149](../../architecture/decisions/ADR-A149-publication-from-the-studio.md) decision 13, which orders a command's operations so that a guard failing part way leaves nothing a reader acts on. MSA-F6 tests that claim for every command that writes several aggregates. A unit on the port is all or nothing, so moving a studio command onto the port gives its operations one guard, which is the next plan's.

MSA-F7 to MSA-F9 come from the maintainer's answers of 2026-11-18, and are built in that order, each with a test that fails before it.

MSA-F10 to MSA-F14 come from the review of MSA-F1 to MSA-F9 on 2026-11-19, made by reading, with no test or model run, and the maintainer's answers to it of the same day. They are built in that order, each with a test that fails before it. The review's findings are these.

- **MSAF2-01, the writer's thread can end and keep its partitions.** `StreamWriter.run` catches only an interruption. A reply sent on a closed channel throws a runtime exception, which `reply` does not catch, and storing an offset can throw too. Either ends the thread while the consumer stays a member of its group, so its partitions are held and nothing applies them, and nothing watches the thread. The defect is older than the fixes. It defeats what MSA-F2 and MSA-F8 give, a write that never holds its partition, and the fairness model X1 assumes of a live writer. MSA-F10.
- **MSAF7-01, the second tombstone is not replayed.** `Writer.finish` runs only for a command planned in the batch in hand. Where the batch's update commits and a later step fails on a store that cannot be reached, the retry answers the deletion from its receipt and `finish` does not run again, so the row MSAF6-01 described stays live. MSA-F11.
- **MSAF8-01, an exception's text reaches a client.** The replies for a refused write and for the writer's own failure carry the exception's message, and `StudioApi` returns a reply's message as the response body. A store's refusal or a failure in our code can name an endpoint, a query or a class. MSA-F12.
- **MSAI6-01, model X1 does not hold the studio's guard.** X1's stores refuse a command unless the partition's version row is one below the command's position. The studio keeps a receipt for each command id and a revision for each aggregate, and no row for a partition. The one configuration without the guard also drops the receipts. A configuration with receipts and no partition row is missing, and it is the one a store without such a row gets. It joins MSA-I6's remaining rows.

The maintainer answered the review's smaller points on 2026-11-19.

- **A message that cannot be decoded is answered 400,** in MSA-F12.
- **The digest.** The limit is recorded as TD-165, and MSA-F14 narrows it where bodies hold blank nodes. Full canonicalisation is not taken.
- **A broker's stale binding** goes to a unit of its own for administering running components, [component-administration](component-administration.md), planned and built later.
- **The Java topology's `bindsTo` check** is MSA-F13.
- **The models' README on X2's audit** is settled by a run. MSA-I6 adds an invariant that a flagged decision's evidence is stale, which we expect TLC to violate, and both sentences are rewritten from what it prints.
- **Wider instances** are run in MSA-I6, sized to the machine that runs them. The models have to run on macOS and in a Linux cloud session with far less memory than machine S, so the runner reads the memory it has and skips with a reason what does not fit, as the [brief of 2026-11-19](../notes/machine-s-brief-2026-11-19-multi-store.md)'s section 4.4 states.

## A design that admits no inconsistent state, MSA-I14 and MSA-F15

Added 2026-11-20, at the maintainer's word, as urgent. The maintainer asked whether the addendum to ADR-A149's decision 13 can leave the store inconsistent. It can. TD-166 to TD-171 record three states, their two causes and one unchecked point, read from the writer's code with nothing run.

**The requirement.** After any request commits, and after any crash, redelivery or handover, the store is in a state that some sequence of whole commands gives. No command is answered as applied while part of it is not, and none leaves a row its answer does not account for. The addendum bounds the states it admits and does not meet this.

**MSA-F15, the fix that cannot wait.** A creation under a document id that has a version row, live or tombstoned, is refused (the addendum's point 5, TD-168). Its test leaves a document's row live and unlisted, saves under its id expecting revision 0, and finds the save refused and the description unchanged. It fails before the fix. A second test delivers a deletion twice more after a lost tombstone and finds the row gone (TD-171). Machine S builds it next.

**MSA-I14, the design.** A note with options, their costs in requests and in contention, and a recommendation, for the maintainer to decide. It is written by the session that reviews this unit, and machine S adds the model. It answers these.

- **Which guard makes a command whole.** One guard over every row the command writes, so the request applies all of its steps or none, with the command planned again from fresh revisions where it is refused. A unit on the logical port is all or nothing (MSA-I11), and the ledger's pass is refused whole and evaluated again by the same rule (LG-Q45). The hypothesis to test is that the studio's commands take that rule today, without waiting for the port.
- **Whether a fence is needed as well.** MSA-I9 found a single active consumer is no fence. A whole-command guard catches a second writer only on rows the command writes. A fence the store checks, for example the partition's epoch guarded in every request, would refuse the second writer outright. The note says whether the first makes the second unnecessary, with the case that shows it.
- **What a deletion's receipt then means.** With one guard a deletion has no later request, so points 2 to 4 of the addendum fall away and it is answered as applied only when everything it deletes is gone. The note drafts the addendum's replacement.
- **What it costs.** A command refused whole is planned again, so the note counts the extra requests under contention, and says what a sender is told when a command loses three times.
- **The model.** A configuration of X1 with two writers on one partition, the studio's receipts and per-aggregate revisions (MSAI6-01's configuration), and a command over two aggregates. It checks the requirement above for the design as built, where we expect TLC to find TD-166 and TD-169's states, and for each option.
- **What a command's answer is read from.** A creation and a deletion of one workspace in one batch answers the creation as refused although it was applied, since the deletion clears the receipt the answer is read from (TD-172). The note says where an answer comes from so that it cannot disagree with what was applied.
- **What stays outside one guard.** Jobs and the promotion maintenance done in the same request are not generated writes (MSA-I11). The note says whether they can leave a state of this kind.

**Its falsifier.** An option is rejected where the model finds a reachable state no sequence of whole commands gives. The slice is done when the maintainer has decided, the decision is drafted as a Proposed addendum, and the slices that build it are planned.

**What waits on it.** MSA-I8, and any slice that builds a write path on the port. The fixes already built stand until the decision replaces them.
