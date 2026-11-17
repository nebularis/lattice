<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Multi-store architecture: status

**Unit ID:** `multi-store-architecture`
**Status:** built 2026-11-17.
**Plan:** [multi-store-architecture.md](../plans/multi-store-architecture.md)
**Mode:** autonomous, at the maintainer's request on 2026-11-17, committing on `spi/sql-backend` only and never pushing, with up to two sub-agents.

## Position

| Slice | Deliverable | State | Blocked on |
|---|---|---|---|
| MSA-I1 | `spikes/multi-store-shape-census`. 505 node shapes, none closed and bounded, so 0% of sample subjects against the proposed 80%. 134 fail only on closure and reach 43.4% of subjects. [Validation Pack](../validation/MSA-I1.md) | built 2026-11-17 |  |
| MSA-I2 | the read-set census | planned | the ledger branch |
| MSA-I3 | [the classification](../notes/multi-store/MSA-I3-dimensions-by-dialect.md). 27 of 30 dimensions stable as they stand, 3 split by value, and resolution's reasoning filter makes semantic selection read a capability. [Validation Pack](../validation/MSA-I3.md) | built 2026-11-17 |  |
| MSA-I4 | [four operations lowered](../notes/multi-store/MSA-I4-four-operations-lowered.md). No construct belongs to one dialect, every resource has a relational counterpart, three implicit choices and the event's logical key found. [Validation Pack](../validation/MSA-I4.md) | built 2026-11-17 |  |
| MSA-I5 | the prover spike | planned | MSA-I4, the ledger branch, the shared types |
| MSA-I6 | the protocol models | planned | MSA-I2, MSA-I9, the protocol toolchain |
| MSA-I7 | the ledger benchmark with a PostgreSQL arm | planned | the ledger's LG-2 |
| MSA-I8 | one ledger family in PostgreSQL behind the port | planned | MSA-I5, MSA-I6, MSA-I7, MSA-I10 |
| MSA-I9 | `spikes/multi-store-stream-probes`. A single active consumer is no fence (a cut consumer applied 6 writes after takeover), no deduplication without named producers, and the client's `storeOffset()` stores unapplied offsets of other partitions, which skipped confirmed writes. [Validation Pack](../validation/MSA-I9.md) | built 2026-11-17 |  |
| MSA-I10 | two families in one mapping vocabulary | planned | MSA-I1, the ledger's LG-2 |
| MSA-I11 | [the logical port](../notes/multi-store/MSA-I11-logical-port.md). Every generated studio write moves onto it as a unit, and the port needs five things the guide's lacks. Jobs and same-request promotion maintenance remain outside it. [Validation Pack](../validation/MSA-I11.md) | built 2026-11-17 |  |
| MSA-I12 | `spikes/multi-store-emitted-topology`. One declaration emits both JSON copies byte for byte and states a binding the copies disagree on. Quanta differ from compose's. [Validation Pack](../validation/MSA-I12.md) | built 2026-11-17 |  |

**Next action, for the maintainer:** synchronise the ledger branch for MSA-I2 and MSA-I5. Confirm the unit's name (MSA-Q14), MSA-I1's threshold, and choose MSA-I6's protocol toolchain, each proposed in the [plan](../plans/multi-store-architecture.md). Decide MSA-I4's three choices (MSAI4-03, MSAI4-05, MSAI4-06) before MSA-I5. Triage the findings about running code, MSAI9-06 (the studio writer's offset storing can skip confirmed writes), MSAI12-01 (the Python worker binds the transforms queue to the dead-letter exchange), MSAI4-04 (the event's logical key), and MSAI11-01, MSAI11-02 and MSAI11-05 (partial application of a multi-aggregate command, a resend with another body answered 200, a batch retried forever).

## History

- 2026-11-17: planned from the sketch of 2026-11-12. MSA-I1, MSA-I3, MSA-I9 and MSA-I12 marked building.
- 2026-11-17: MSA-I1, MSA-I9 and MSA-I12 built. MSA-I1's falsifier fires on the strict reading, MSA-I12's does not, and MSA-I9 confirms the sketch's §4.2 caveat and finds a defect in the studio's offset storing.
- 2026-11-17: MSA-I3 built, the falsifier does not fire.
- 2026-11-17: MSA-I4 marked building.
- 2026-11-17: MSA-I4 built, the falsifier does not fire.
- 2026-11-17: MSA-I11 marked building.
- 2026-11-17: MSA-I11 built, the falsifier does not fire for the port written and fires against the guide's. Every slice left is blocked on the ledger branch, a toolchain choice or LG-2.
