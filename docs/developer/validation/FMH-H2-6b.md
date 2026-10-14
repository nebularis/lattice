<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-H2.6b, the event slots and the unhonoured receipt models

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice H2.6b, the event half only, planned in
[plan §4.6](../plans/formal-methods-track-h.md#46-h26b-the-event-and-patch-content-slots-planned-2026-10-14) ("Steps, the event half"), after
[H2.6](FMH-H2-6.md). The patch-log half is held (H-D33) and is not built.
**For the maintainer:** re-approve the six expected profiles that changed (below), accept or
change the ADR-A123 addendum draft, and read the probe results, one of which did not behave as the plan predicted.
**For countersignature (non-weakening rule):** one existing test was changed. `test_ho6_t14` asserted that a warning witness triggers exactly its own
rule. The composite example it extends declares `dal:PatchLog`, so its own compile now warns `ReceiptModelNotHonoured` (TD-46), and the test now
subtracts what the base example reports on its own. It still fails if the witness triggers any other rule. Three other existing tests were adapted
to the new request shape (`test_h2_2_t10`, `test_h2_2_t18`, `test_h2_5_t38`), which fill the event slots where they passed the removed parameters.
No test was removed or skipped.

## Invariant

One append request, however many events it carries, steps the stream's seq once and writes one version row, one txn claim and one receipt, and
every event it writes names that receipt. The result does not depend on the order in which a store applies the solutions. A declaration of a
receipt model the generated operations do not honour is reported, never silent (H1.4c).

## What changed

- **The IR** (`ir.py`, `ir_render.py`). A `Rows` slot kind, `RowsSlot` and `RowValues`. The checker takes the variables of a `RowValues` as
  definitely bound and refuses a wrong slot kind, an undeclared parameter and an invalid variable name.
- **Templates and builder.** `append-event` and `append-event-dataset-guard` read their events from `VALUES (?event ?eventType ?opSeq ?occurredAt)
  { {{{eventRows}}} }` and write `{{{eventTriples}}}` beside them. The parameters `$event`, `$eventType`, `$opSeq` and `$occurredAt` are gone.
  The builder and the template still agree under the equivalence harness. `append-event` is builder version 2.
- **The contract.** `DigestContract` gains `event`, the sources of an append's event part (the two slots). An append has no payload part. The part
  leaves out `pat:revision`. H2.8 computes it.
- **The warning.** `compile` warns `ReceiptModelNotHonoured`, naming the model, for `dal:PatchLog` and `dal:SnapshotPerRevision`. A witness exists
  for each (`warning-ReceiptModelNotHonoured.ttl`, `snapshot-ReceiptModelNotHonoured.ttl`), each on a scope of higher priority than the base's.
- **Documents.** ADR-A123 addendum (draft), guide §15.2 dated note, README, TSD-21 in the triple-store record, this pack, the status record, the plan and the index.

## Expected profiles that changed (for re-approval)

| File | Change |
|---|---|
| `kinds.expected.ttl` | adds `RowsKind` and `EventPart` |
| `append-stream-dataset-guard.expected.ttl` | one more `ReceiptModelNotHonoured` diagnostic, and the append's parameters lose the four event parameters, its digest part 4 is an `EventPart` with two sources, and `append-event` is version 2 |
| `baseline-single-class.expected.ttl`, `baseline-single-class.caller-named.expected.ttl`, `epoch-dataset-level-guard.expected.ttl`, `composite-project-ownership.expected.ttl` | each gains one `ReceiptModelNotHonoured` diagnostic, since each resolves to `dal:PatchLog` |

## Findings

- **TSD-21.** rdflib 7.6.0 raises `AttributeError` for an empty `VALUES` block in an update `WHERE`, before it changes anything. Oxigraph gives no
  solution. Recorded in the [triple-store record](../../architecture/triple-store-discovery.md#tsd-21-an-empty-values-block-in-an-update). Nothing is
  written on either store, and H2.8's caller check refuses an empty slot before sending.
- **Cost of the event triples (TD-42).** Each row writes the same ground `eventTriples`, so k rows cost k × |eventTriples| fills over one set. This is
  the quadratic fill of TSD-02 and is not measured here.
- **The parameter guards no longer see `opSeq` or `occurredAt`,** which are row values. This is the deliberate non-coverage of the plan, closed by H2.8.

## Test cases

`test_append_events.py`, 40 cases over both engines, with and without the parameter guards.

| ID | Checks |
|---|---|
| H2.6b-T1 | a three-row append steps the seq once and writes one receipt, one claim and three events with the same `pat:revision` |
| H2.6b-T2 | the same quads under eight `PYTHONHASHSEED` values on rdflib (TSD-01) |
| H2.6b-T3 | a retry with the same transaction id writes nothing |
| H2.6b-T4 | the event triples land in the events bucket once, and an empty `eventTriples` writes the events only |
| H2.6b-T5 | a one-row append writes the four triples the single-event form wrote |
| H2.6b-T6 | an empty `eventRows` writes nothing, and rdflib raises where Oxigraph gives no solution (TSD-21) |
| H2.6b-T7 | a second append chains to the first, and `opSeq` restarts per request |
| H2.6b-T8 | the dataset-guard variant writes only while the dataset epoch matches |
| H2.6b-T9 | with the guards on, a batch missing any parameter writes nothing |
| H2.6b-T10 (`test_ir.py`) | the `RowValues` refusals and its binding |
| H2.6b-T11 | each unhonoured receipt model warns once and names itself and TD-46 |
| H2.6b-T12 | a `dal:ReceiptOnly` profile does not warn |

The existing tests of the builder harness, the contract, the expected profiles and the witness coverage cover the rest.

## One command

```
mise run check:persistence
mise run check:persistence-oxigraph
```

From the repository root. A pass is no failed test in either, and `check:persistence-expected-profiles` reporting no stale file. `mise run
build:persistence-expected-profiles` regenerates the files if a builder changes.

## Adversarial probes

Each was run on the finished tree and then reverted.

1. **The `VALUES` block moved into a group of its own** (the plan predicted the three-row test would fail). It did not. All 57 selected tests
   passed, because a group that holds only a `VALUES` block joins with the rest of the `WHERE` exactly as the bare block does. The plan's
   prediction was wrong and we found no form of this change the tests catch.
2. **A mutation that makes the receipt depend on the event** (`?opSeq` added to the log graph name). T1 and T7 fail on all four engine and guard
   combinations, because three receipts are written. This is the probe that tests the invariant.
3. **The digest parts declared in another order** (`ExpectedSeqPart` before `TargetPart`). `check:persistence-expected-profiles` reports the five
   files stale.
4. **A patch-log profile that compiles without the warning.** T11 fails for the patch-log witness, and the witness-coverage tests
   (`test_h1_2_t15`, `t16`, `t23`, `t27`, `t28`) fail.

## Deliberate non-coverage

- Checks on the slots' content: subjects bounded to the batch's events, distinct `opSeq` values and a non-empty `eventRows` (H2.8).
- The digest computation itself (H2.8) and the parts for the held patch-log half.
- The held patch-log half, snapshot receipts, H2.10, H2.7 and H2.8. Nothing of them is built here.
- Fuseki and the other stores. Only rdflib and Oxigraph are measured (TSD-Q12).
