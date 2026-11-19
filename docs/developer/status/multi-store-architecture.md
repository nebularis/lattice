<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Multi-store architecture: status

**Unit ID:** `multi-store-architecture`
**Status:** built 2026-11-18.
**Plan:** [multi-store-architecture.md](../plans/multi-store-architecture.md)
**Mode:** autonomous on machine S, at the maintainer's request of 2026-11-17 and the brief of the same day, committing locally only and never pushing, with up to two sub-agents. The branch defers versioning, so Persistence's spec, changed by MSA-F5, is reported unbumped until the merge.

## Position

| Slice | Deliverable | State | Blocked on |
|---|---|---|---|
| MSA-I1 | `spikes/multi-store-shape-census`. 505 node shapes, none closed and bounded, so 0% of sample subjects against the proposed 80%. 134 fail only on closure and reach 43.4% of subjects. [Validation Pack](../validation/MSA-I1.md) | built 2026-11-17 |  |
| MSA-I2 | [the read-set census](../notes/multi-store/MSA-I2-read-set-census.md). The falsifier fires on one example, a pass whose guards read a balance an earlier draw wrote, and becomes common once Behaviour imports Ledger. Every other cross-aggregate read is pinned. [Validation Pack](../validation/MSA-I2.md) | built 2026-11-18 |  |
| MSA-I3 | [the classification](../notes/multi-store/MSA-I3-dimensions-by-dialect.md). 27 of 30 dimensions stable as they stand, 3 split by value, and resolution's reasoning filter makes semantic selection read a capability. [Validation Pack](../validation/MSA-I3.md) | built 2026-11-17 |  |
| MSA-I4 | [four operations lowered](../notes/multi-store/MSA-I4-four-operations-lowered.md). No construct belongs to one dialect, every resource has a relational counterpart, three implicit choices and the event's logical key found. [Validation Pack](../validation/MSA-I4.md) | built 2026-11-17 |  |
| MSA-I5 | the prover spike | planned | MSA-I5a |
| MSA-I5a | the shared proof session, `tools/proofs/shared/`, with a position and an amount | planned | ADR-A-FM2's addendum proposed 2026-11-18, accepted |
| MSA-I6 | `tools/models/multi-store-protocols`. TLA+ models A, X1 to X4, 28 configurations. Five catalogue rows keep their guarantee with a stated requirement, and the serialised writer never gives atomic visibility. Probes and trace validation not run. [Validation Pack](../validation/MSA-I6.md) | built 2026-11-18 |  |
| MSA-I7 | the ledger benchmark with a PostgreSQL arm | planned | the ledger's LG-2 |
| MSA-I8 | one ledger family in PostgreSQL behind the port | planned | MSA-I5, MSA-I6, MSA-I7, MSA-I10 |
| MSA-I9 | `spikes/multi-store-stream-probes`. A single active consumer is no fence (a cut consumer applied 6 writes after takeover), no deduplication without named producers, and the client's `storeOffset()` stores unapplied offsets of other partitions, which skipped confirmed writes. [Validation Pack](../validation/MSA-I9.md) | built 2026-11-17 |  |
| MSA-I10 | two families in one mapping vocabulary | planned | MSA-I1, the ledger's LG-2 |
| MSA-I11 | [the logical port](../notes/multi-store/MSA-I11-logical-port.md). Every generated studio write moves onto it as a unit, and the port needs five things the guide's lacks. Jobs and same-request promotion maintenance remain outside it. [Validation Pack](../validation/MSA-I11.md) | built 2026-11-17 |  |
| MSA-I12 | `spikes/multi-store-emitted-topology`. One declaration emits both JSON copies byte for byte and states a binding the copies disagree on. Quanta differ from compose's. [Validation Pack](../validation/MSA-I12.md) | built 2026-11-17 |  |
| MSA-F1 | the studio's stream writer stores only offsets it has applied, by stream and offset through the environment, so a stop skips no confirmed write (MSAI9-06). P3a rerun through the writer's code skipped 0 against 36 on the old path. [Validation Pack](../validation/MSA-F1.md) | built 2026-11-18 |  |
| MSA-F2 | a batch the store refuses for a reason that a retry cannot change is answered and the stream goes on, and only a store that cannot be reached is retried (MSAI11-05). A refused batch is tried command by command, so only the command at fault is answered 400. [Validation Pack](../validation/MSA-F2.md) | built 2026-11-18 |  |
| MSA-F3 | a command id resent with a different body is refused, its digest compared with the one its claim holds (MSAI11-02). The receipt holds the command's own digest, `cst:requestDigest`, since an operation's cannot be recomputed for a resend. [Validation Pack](../validation/MSA-F3.md) | built 2026-11-18 |  |
| MSA-F4 | the queue topology states each queue's dead-letter binding once, and the Python worker and the Java service declare the same broker objects from it (MSAI12-01). Each queue has `bindsTo` and `deadLettersTo`, and the worker and the service declare from the contract. [Validation Pack](../validation/MSA-F4.md) | built 2026-11-18 |  |
| MSA-F5 | the event's logical key names one event, not one append, in the persistence contract (MSAI4-04). The key is `stream, seq, event` in the contract and the persistence spec. [Validation Pack](../validation/MSA-F5.md) | built 2026-11-18 |  |
| MSA-F6 | a test that a command writing several aggregates, whose later guard fails, leaves nothing a reader acts on and is completed by a resend (MSAI11-01). Six commands tested: nothing a reader acts on remains in each. A resend completes a publication and a new document's save, and does not complete a deletion whose later tombstone failed (MSAF6-01). [Validation Pack](../validation/MSA-F6.md) | built 2026-11-18 |  |
| MSA-F7 | a deletion whose tombstone loses a race to a save of the same part or document still removes it, the tombstone planned again at the revision the save left (MSAF6-01). The receipt follows the description's step, and up to three more rounds tombstone a row still live. An addendum to ADR-A149 is drafted for the maintainer. [Validation Pack](../validation/MSA-F7.md) | built 2026-11-18 |  |
| MSA-F8 | a failure of the stream writer's own code is answered as the writer's fault, a 500, and the service answers it 500 (MSA-F2). Still not retried, and a request the store refused keeps its 400. [Validation Pack](../validation/MSA-F8.md) | built 2026-11-18 |  |
| MSA-F9 | a new document's save that loses the description's guard is answered as a change to send again, read from the document's own row, not as a deleted id (MSAF6-02). Its test found that a save under a deleted id was answered 200 and kept nothing (MSAF9-01), now refused before it is planned. [Validation Pack](../validation/MSA-F9.md) | built 2026-11-18 |  |

**Next action:** MSA-F7, MSA-F8 and MSA-F9 in order, then MSA-I2 reworked on the ledger's unit as the maintainer decided it. MSA-I5a once ADR-A-FM2's addendum proposed 2026-11-18 is accepted, then MSA-I5 on it.

## History

- 2026-11-17: the work of machine S brought into `docs/placement-vehicles-structure` as one squashed commit, with a machine path removed from two files. The maintainer confirmed the unit's name, MSA-I1's threshold read per family, TLA+ for MSA-I6, and MSA-I4's three choices, recorded in the [plan](../plans/multi-store-architecture.md). The findings on running code became MSA-F1 to MSA-F6, to be fixed on machine S first, MSA-F1 before the rest.
- 2026-11-17: planned from the sketch of 2026-11-12. MSA-I1, MSA-I3, MSA-I9 and MSA-I12 marked building.
- 2026-11-17: MSA-I1, MSA-I9 and MSA-I12 built. MSA-I1's falsifier fires on the strict reading, MSA-I12's does not, and MSA-I9 confirms the sketch's §4.2 caveat and finds a defect in the studio's offset storing.
- 2026-11-17: MSA-I3 built, the falsifier does not fire.
- 2026-11-17: MSA-I4 marked building.
- 2026-11-17: MSA-I4 built, the falsifier does not fire.
- 2026-11-17: MSA-I11 marked building.
- 2026-11-17: MSA-I11 built, the falsifier does not fire for the port written and fires against the guide's. Every slice left is blocked on the ledger branch, a toolchain choice or LG-2.
- 2026-11-18: on machine S, per the brief of 2026-11-17, autonomous and committing locally only. MSA-F1 marked building.
- 2026-11-18: MSA-F1 built. The writer stores each partition's applied offset through the environment. The probe's P3a, run through the writer's own `apply`, skipped no confirmed write, and the old path skipped 36 the same day.
- 2026-11-18: MSA-F2 marked building.
- 2026-11-18: MSA-F2 built. Retried are a store that cannot be reached, a 5xx and a refusal of the writer's configuration. A request the store refuses as malformed, or a failure of the writer's own code, is answered as refused after the batch is tried command by command. The second half is a choice for the maintainer to confirm.
- 2026-11-18: MSA-F3 marked building.
- 2026-11-18: MSA-F3 built. The brief's digest, the operation's in its claim, depends on the state the writer read, so a resend of a save would never match. The receipt now holds the digest of the command, a new term `cst:requestDigest` in the studio's vocabulary, and an id resent with another digest is refused with a 400.
- 2026-11-18: MSA-F4 marked building.
- 2026-11-18: MSA-F4 built. The contract's `deadLetter` became `bindsTo` and `deadLettersTo`, the Java service declares from the contract on its classpath, and the worker and the service are tested against the operator guide's table. The spike's comparison shows no difference for the transforms binding.
- 2026-11-18: MSA-F5 marked building.
- 2026-11-18: MSA-F5 built. `dal:Event`'s logical key is `stream, seq, event`, in `contract.py` and the persistence README, whose spec was regenerated and whose release notes gain an Unreleased entry. The branch defers versioning, so `check:ontology-versioning` reports Persistence unbumped until the merge.
- 2026-11-18: MSA-F6 marked building.
- 2026-11-18: MSA-F6 built, tests only. ADR-A149 decision 13 holds for every command tested: no reader acts on what a failed later guard leaves. A deletion whose later tombstone loses a race to a save leaves a graph and a live row nothing reaches, and no resend removes them (MSAF6-01), which needs the maintainer's choice. The port note cites decision 13.
- 2026-11-18: MSA-I2 marked building.
- 2026-11-18: MSA-I6 marked building, with TLA+ and TLC as decided. Its models of the serialised writer rest on MSA-I9's probes, and MSA-I2 runs beside it, since X2's reads are its subject.
- 2026-11-18: MSA-I2 built. The falsifier fires on the text of `ordered-draws.ttl` and is not shown common, and the leaning of §4.1 survives with a rule placing an identity's Behaviour state with its ledger. ADR-A131 states two units for the ledger, a question for the maintainer.
- 2026-11-18: MSA-I6 built in part. FMH-5's model A and four new models, X1 to X4, checked with TLC. The falsifier does not fire for the five rows modelled. The saga row, FMH-5's models B to D, the isolation probes on PostgreSQL and Fuseki and the trace validation against Isabelle are not done, and FMH-5's row on Track H's board is unchanged.
- 2026-11-18: the maintainer answered the six points of the next action, recorded in the [plan](../plans/multi-store-architecture.md): MSA-F7 to MSA-F9 planned from MSAF6-01, MSA-F2's second half and MSAF6-02, MSA-F3's departure confirmed, the owner's ledger as the ledger's unit with no placement rule, and the shared types in a proof session of their own, MSA-I5a, which waits on ADR-A-FM2's addendum.
- 2026-11-18: MSA-F7 marked building.
- 2026-11-18: MSA-F7 built. A deletion's receipt follows the step that removes the description's mention, and a tombstone a save beat is planned again at the revision the save left, up to three rounds. The generated tombstone and its guard are unchanged. The addendum to ADR-A149 decision 13 it needs is drafted in its Validation Pack for the maintainer.
- 2026-11-18: MSA-F8 marked building.
- 2026-11-18: MSA-F8 built. `Reply.failed` answers a failure of the writer's own code with a 500, the stream writer tells it from a store's refusal by the status the store's exception carries, and the service passes a 500 through.
- 2026-11-18: MSA-F9 marked building.
- 2026-11-18: MSA-F9 built. The reply to a new document's save reads the document's own row. Its test found MSAF9-01: a save under a deleted document's id was answered 200, the create wrote nothing over the tombstone and the description listed an empty document. The writer now refuses it before planning, and `DocumentsTest`, which saved under a deleted id and was answered 204, asserts the 400.
