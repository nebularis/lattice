<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Multi-store architecture: status

**Unit ID:** `multi-store-architecture`
**Status:** built 2026-11-18.
**Plan:** [multi-store-architecture.md](../plans/multi-store-architecture.md)
**Mode:** autonomous, at the maintainer's request on 2026-11-17, committing on `spi/sql-backend` only and never pushing, with up to two sub-agents.

## Position

| Slice | Deliverable | State | Blocked on |
|---|---|---|---|
| MSA-I1 | `spikes/multi-store-shape-census`. 505 node shapes, none closed and bounded, so 0% of sample subjects against the proposed 80%. 134 fail only on closure and reach 43.4% of subjects. [Validation Pack](../validation/MSA-I1.md) | built 2026-11-17 |  |
| MSA-I2 | the read-set census | planned |  |
| MSA-I3 | [the classification](../notes/multi-store/MSA-I3-dimensions-by-dialect.md). 27 of 30 dimensions stable as they stand, 3 split by value, and resolution's reasoning filter makes semantic selection read a capability. [Validation Pack](../validation/MSA-I3.md) | built 2026-11-17 |  |
| MSA-I4 | [four operations lowered](../notes/multi-store/MSA-I4-four-operations-lowered.md). No construct belongs to one dialect, every resource has a relational counterpart, three implicit choices and the event's logical key found. [Validation Pack](../validation/MSA-I4.md) | built 2026-11-17 |  |
| MSA-I5 | the prover spike | planned | the shared types |
| MSA-I6 | the protocol models | planned | MSA-I2 |
| MSA-I7 | the ledger benchmark with a PostgreSQL arm | planned | the ledger's LG-2 |
| MSA-I8 | one ledger family in PostgreSQL behind the port | planned | MSA-I5, MSA-I6, MSA-I7, MSA-I10 |
| MSA-I9 | `spikes/multi-store-stream-probes`. A single active consumer is no fence (a cut consumer applied 6 writes after takeover), no deduplication without named producers, and the client's `storeOffset()` stores unapplied offsets of other partitions, which skipped confirmed writes. [Validation Pack](../validation/MSA-I9.md) | built 2026-11-17 |  |
| MSA-I10 | two families in one mapping vocabulary | planned | MSA-I1, the ledger's LG-2 |
| MSA-I11 | [the logical port](../notes/multi-store/MSA-I11-logical-port.md). Every generated studio write moves onto it as a unit, and the port needs five things the guide's lacks. Jobs and same-request promotion maintenance remain outside it. [Validation Pack](../validation/MSA-I11.md) | built 2026-11-17 |  |
| MSA-I12 | `spikes/multi-store-emitted-topology`. One declaration emits both JSON copies byte for byte and states a binding the copies disagree on. Quanta differ from compose's. [Validation Pack](../validation/MSA-I12.md) | built 2026-11-17 |  |
| MSA-F1 | the studio's stream writer stores only offsets it has applied, by stream and offset through the environment, so a stop skips no confirmed write (MSAI9-06). P3a rerun through the writer's code skipped 0 against 36 on the old path. [Validation Pack](../validation/MSA-F1.md) | built 2026-11-18 |  |
| MSA-F2 | a batch the store refuses for a reason that a retry cannot change is answered and the stream goes on, and only a store that cannot be reached is retried (MSAI11-05). A refused batch is tried command by command, so only the command at fault is answered 400. [Validation Pack](../validation/MSA-F2.md) | built 2026-11-18 |  |
| MSA-F3 | a command id resent with a different body is refused, its digest compared with the one its claim holds (MSAI11-02) | planned |  |
| MSA-F4 | the queue topology states each queue's dead-letter binding once, and the Python worker and the Java service declare the same broker objects from it (MSAI12-01) | planned |  |
| MSA-F5 | the event's logical key names one event, not one append, in the persistence contract (MSAI4-04) | planned |  |
| MSA-F6 | a test that a command writing several aggregates, whose later guard fails, leaves nothing a reader acts on and is completed by a resend (MSAI11-01) | planned |  |

**Next action:** MSA-F1 to MSA-F6 in order, on machine S, then MSA-I2 and MSA-I6, per the [brief of 2026-11-17](../notes/machine-s-brief-2026-11-17.md). The ledger's work is on `main`, so MSA-I2 and MSA-I5 no longer wait on its branch.

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
