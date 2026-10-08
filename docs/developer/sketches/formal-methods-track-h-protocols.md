<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Track H: protocol models (sketch)

**Unit:** [formal-methods](../plans/formal-methods.md) (epic), track H
**Status:** sketch, 2026-10-08. Nothing here is ratified
**Reads with:** [the main track H sketch](formal-methods-track-h.md) (§4's matrix idea, which this
sketch builds), [persistence-fml.md](../notes/rdf-engine/persistence-fml.md) §10 (the full
analysis this sketch compresses), [formal-methods.md](formal-methods.md) §5 (rung T4: "model
checking... never been attempted" — this sketch is its first attempt anywhere in this epic)

## 1. Why this is the centrepiece, not an afterthought

Review §1.3's own calibration table is blunt about where the value is: eleven of twelve recorded
defects from three real remediation passes are protocol or liveness properties — a guard that
wedges every row after an epoch bump, an allocation scheme that lets a reader skip a committed
write forever, a pruned transaction claim that lets an append apply twice, a fence checked but
never advanced. **None of tracks B, C or E's techniques (reference semantics, Alloy, Isabelle)
reach this class of defect at all.** They are sequential tools applied to a concurrent, crash-prone
problem. T4 is not one more rung alongside the others for Persistence; it is the rung that answers
the question the other three cannot even ask.

## 2. Modelling discipline, stated once

Four rules, read directly from the review (§10.1) and kept as this sketch's own discipline for
every model built under it:

1. **Model the isolation *contract*, not the engine.** Read and write sets, snapshots, commit
   points, conflict-detection granularity. Not PostgreSQL's or any store's actual implementation —
   there is no such single implementation here, by design (Persistence targets pluggable
   backends). Three abstract levels suffice for most models: a level with per-statement snapshots
   and no cross-statement isolation, a level with snapshot isolation without write-write
   detection, and a level with full conflict detection, plus flags for statement-versus-graph
   conflict granularity and atomic-request semantics.
2. **Parametrise by the capability record** (main sketch §5), so one model yields a matrix *row*
   (main sketch §4) rather than a single yes/no. One configuration per capability profile, one run
   per cell, one recorded verdict plus counterexample per cell.
3. **Model the caller as a process that can misbehave in declared ways, not an oracle that always
   does the right thing.** Every recorded defect in the review's own calibration table that
   involves a caller (resend-identically on `Unknown`, confirm-on-primary, `clock.receive` before
   a read-dependent write) is caught only if the model's client process can fail to do these
   things and the model shows the consequence.
4. **Model crashes, transport failures and out-of-band writers explicitly** at every point the
   review identifies them: after send and before commit, after commit and before response, during
   confirmation, between retention's two steps, between quiesce and epoch allocation, and a bulk
   load, an administrative `LOAD`, a restore or a rogue ETL writing outside every guard.

**Scope discipline.** Bounded model checking at small scope (2-3 writers, 2 aggregates, 2 epochs,
3 sequence values) is enough to reproduce every defect in the review's own calibration table.
Record the bound in every claim; a bounded pass is never read as universal, the same discipline
Alloy's own track (C) already states for itself.

## 3. Fourteen models, by priority, not all at once

The review names fourteen candidate models (§10.2, table). This track does not build all fourteen
in one slice — rolling-wave, same as every other track in this epic. **The first four (A to D)
are this track's actual H5 slice** (the plan's own numbering); E through N are named here, at
outline level, for when their own slice starts.

| Model | System | Why it is prioritised (or deferred) |
|---|---|---|
| **A. Guarded CAS** | the core write protocol: epoch guard, row-epoch rebase, sequence CAS, tombstone guard, transaction-claim exclusion, head/chain maintenance | **H5, first.** This is the write path every other guarantee in the layer depends on; its expected finding (two writers both committing under `detectsWriteWriteConflict = false`) is a direct reproduction of the review's own worked defect, D.3 A6 |
| **B. Append form** | server-side counter allocation, `opSeq`, dataset/row/transaction guards | **H5.** Directly reproduces two already-recorded defects (A2 reader-skip, A4 double-append) as regression proofs, the cheapest possible first evidence that the modelling approach is faithful |
| **C. First write / create race** | `AbsentRow` vs `PreCreatedRow`, concurrent creators | **H5.** Tests the review's flagged *default-unsafe baseline* (`dal:AbsentRow`) directly — a finding with an immediate consequence for the compiler's own warning text |
| **D. Key claim** | the three key-placement patterns (P1/P2/P3), rotation, retire, external allocation | **H5.** Rotation-under-concurrent-retire is named by the review as a genuine open question, not a known defect — the first model in this set that might find something nobody has found by hand yet |
| E. Outcome classification | the confirmation decision procedure | H6, next: depends on A-D's guard semantics being modelled first |
| F. Epoch bump and restore | quiesce, allocation, rebase, double-restore | H6 |
| G. Retention and pruning | bucket rotation, registry update, low-water-mark advance, pinned heads | H6. Expected to be "the richest model" (review's own words) given the registry/retention graphs are unguarded today (main sketch, L3/L6 gaps) |
| H. Global read (dataset tier) | HLC stamping, lag budget, late-arrival audit | H7 |
| I. Fencing and external locks | lease/fence check-and-advance | H7. Directly reproduces a recorded defect (§16.2, checked but not advanced) |
| J. Infrastructure-graph writers | the epoch authority, rotation job, retention job, concurrent readers | H7. Expected to be the single richest source of new findings (nothing here is guarded at all today, main sketch §3) |
| K. Erasure | the full enumerated store list, including the out-of-band key-placement allocator | H8, gates any deployment holding personal data before this track calls itself done for Persistence |
| L. Multi-aggregate writes | deadlock/livelock under each `dal:deadlockPolicy` | H8 |
| M. Bulk load and cutover | offline positions, staging, gated cutover | H8 |
| N. Shard-count migration | moving rows between shard graphs under an acknowledged epoch bump | H8 |

## 4. Grounding: a model is only as good as its fidelity

Three mechanisms, increasing in cost, all named by the review (§10.4) and adopted here without
change:

1. **Isolation probes** (Kleppmann's Hermitage-style suite) per backend, one per anomaly a model
   predicts. Cheap, and populates the capability record's isolation fields with evidence rather
   than a claimed level.
2. **History checking** under randomised concurrent workloads, with an Elle-style checker
   (Kingsbury and Alvaro, VLDB 2020) inferring anomalies from the recorded history rather than
   from an exception being thrown. *(verify: Elle's inference typically assumes list-append or
   register semantics; Persistence's version-row-plus-receipt structure is a natural
   register-with-history, but the encoding needs its own design when this is reached — not
   assumed here.)*
3. **Predicted-anomaly reproduction**: for each counterexample a model produces, write a TCK test
   that attempts to reproduce it on a real backend. Reproduced ⟹ the model is faithful and the
   backend is correctly classified. Not reproduced ⟹ either the backend is stronger than
   classified (update the capability record) or the model is too strong a claim (weaken it). This
   is this track's own version of the seeded-mutation discipline every other track in this epic
   already uses (a model whose predicted counterexample never actually reproduces anywhere is as
   suspect as a test that cannot fail).

At least one MVCC-style backend must be exercised before any capability-model claim is trusted —
a single-writer-only backend cannot exercise the hazards these models exist to find.

## 5. Toolchain: not yet chosen

Neither TLA+ (with TLC or Apalache) nor Quint is chosen by this sketch or by
[ADR-A-FM4](../../architecture/decisions/ADR-A-FM4-persistence-formal-methods-home-and-scope.md).
The first protocol-model slice (H5, the plan's own numbering) runs a short toolchain spike first —
install both, write model A in each, compare authoring cost and counterexample readability — the
same shape as track D's prover spike and track C's C1 Alloy-skeleton install, at a much smaller
scale (one model, not a full kernel). Published TLA+ specifications of snapshot isolation and
serialisable snapshot isolation exist and can be adapted as a starting point for model A
*(verify current sources when H5 starts; not confirmed in this sketch)*.

## 6. Non-goals

Timed automata (the epic's own existing exclusion, `formal-methods.md` §10, applies unchanged: no
model here needs real-valued clocks, every duration is an integer position or a bounded step
count). Modelling any store's actual implementation rather than its isolation contract. Building
all fourteen models before any of them is grounded against a real backend — grounding model A
before building model E is this track's own priority order, not an afterthought.
