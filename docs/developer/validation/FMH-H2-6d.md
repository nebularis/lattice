<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-H2.6d, the patch log, no receipt and the link between versions

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice H2.6d, planned in
[plan §4.10](../plans/formal-methods-track-h.md#410-h26d-the-patch-log-for-in-place-families-the-link-between-versions-no-receipt-planned-2026-10-20-revised-the-same-day)
and in the held half of [§4.6](../plans/formal-methods-track-h.md#46-h26b-the-event-and-patch-content-slots-planned-2026-10-14). Decided 2026-10-20
(H2.6b-Q1 and Q2, R2, VH-Q5a) and built the same day for the maintainer's review. Authored and run in autonomous mode, not committed.
Versioning is ignored on this branch (TD-64), so no version IRI moved.

**For the maintainer:** re-approve the eight expected profiles that changed (below), accept or change the ADR-A123 addendum (accepted with the
slice's plan, so the decisions taken alone are the part to read), read the decisions taken alone and the findings, and countersign the changes to
existing tests.
**For countersignature (non-weakening rule):** existing tests changed in four ways, listed under "Changes to existing tests". No test was
skipped, and one assertion was removed (the IR's refusal of two payload slots, whose rule is dropped).

## Invariant

Under `dal:PatchLog`, a create, a replace and a tombstone of an in-place family write their delta graphs in the same update as the write, named
from the receipt, and the receipt names them. A replace's graphs hold exactly what the caller gave, a tombstone's del graph holds exactly what its
sweep removed, and a create's add graph holds its payload. A retry, a write that loses the race and a request that leaves a slot out write nothing,
the delta graphs included. Under `dal:NoReceipt` the same writes leave no receipt, no log bucket and no head, and still leave the transaction claim.
`dal:NoReceipt` is refused with an append discipline. `append-version` links a version to the one before it with `pat:previousVersion` and never
writes `fnd:supersededBy`.

## What changed

- **R2** (`builders.py`, the two `append-version` templates). The new version is linked to the version the row names as current by
  `$newVersion pat:previousVersion ?priorVersion`. The direction is new to prior. `append-version` is builder version 2.
- **The patch log** (`builders.py`, `operations.py`, 12 templates). `compile` selects, under `dal:PatchLog`, a patch-log variant of create, replace
  and tombstone for each family, each with its dataset-guard variant. The two delta graphs are bound in `WHERE` as
  `IRI(CONCAT(STR($newRev), "/add"))` and `"/del"`. A create inserts its payload slot into the data graph and the add graph. A replace inserts two new
  request-time slots, `{{{assertTriples}}}` and `{{{retractTriples}}}`. A tombstone inserts `?s ?p ?o`, which its sweep binds, into the del graph.
  The receipt gains `pat:asserts` or `pat:retracts` where the write puts content in the graph. `$assertGraph` and `$retractGraph` are gone from the
  receipt-only replace, which is builder version 2.
- **No receipt** (`builders.py`, `operations.py`, 12 templates, `validator.py`, `spec/persistence.ttl`). `dal:NoReceipt` selects variants with no log
  bind, no claim time binds, no head in the row and no receipt block, and keeps the claim. The tombstone has no `$cause` and no `$actor`. The gap scan
  and the two receipt-side fork audits are not generated. `NoReceiptWithAppendDiscipline` refuses it with `dal:AppendVersions`,
  `dal:AppendRecords`, an append-only concurrency and a stream.
- **The contract** (`contract.py`, `ir.py`, `render.py`). Graph role `patch`, resource `PatchContent` keyed by (target, epoch, seq, direction),
  `DigestContract.add` and `.delete`, and the two slot names in `REQUEST_TIME_SLOTS`. The profile's digest gains the parts `AddPart` and `DelPart`
  after the payload part, for a replace under a patch log only.
- **The warning** (`validator.py`). `ReceiptModelNotHonoured` is raised for `dal:SnapshotPerRevision` alone.
- **Fixtures.** Four witnesses for no receipt, `write-discipline-no-receipt-{named-graph,named-graph-dataset-guard,composite,composite-dataset-guard}`,
  one refusal witness, `refusal-NoReceiptWithAppendDiscipline`, and four that reach the receipt-only templates through `dal:SnapshotPerRevision`,
  `write-discipline-snapshot-{named-graph,named-graph-dataset-guard,composite,composite-dataset-guard}`. The witness
  `warning-ReceiptModelNotHonoured` now witnesses the snapshot, and `snapshot-ReceiptModelNotHonoured` is merged into it and removed.
- **Documents.** The ontology README (§7.4 and §7.10), the compiler README, ADR-A123's addendum of 2026-10-20, TD-46 and TD-48 narrowed, and dated
  notes at S6 and §24.2 of the patterns guide with the backward as-of rule. This pack.

## Expected profiles (for re-approval)

| File | Change |
|---|---|
| `baseline-single-class.expected.ttl` | the named-graph writes use the `-patch-log` builders. The replace has the slots `assertTriples` and `retractTriples` and no `assertGraph`, and gains `AddPart` and `DelPart`. Every write gains a `PatchContent` access |
| `baseline-single-class.caller-named.expected.ttl` | the same, with the guards off and the caller naming each graph |
| `epoch-dataset-level-guard.expected.ttl` | the same under the dataset-level guard |
| `composite-project-ownership.expected.ttl` | the same for a composite family |
| `append-stream-dataset-guard.expected.ttl` | the diagnostic `ReceiptModelNotHonoured` is gone. The family declares `dal:PatchLog` and writes by append, so this is the silent case under Finding 1 |
| `kinds.expected.ttl` | adds `dal:PatchContent`, its logical key and realisation, and the digest part roles `AddPart` and `DelPart` |
| `write-discipline-composite-append-versions.expected.ttl` | `append-version` is at template version 2 |
| `write-discipline-noboundary-append-versions.expected.ttl` | the same |

No new expected profile was added. The `dal:NoReceipt` variants are covered by the behaviour tests and the witness fixtures, since no shipped example
declares the model.

## Decisions taken alone, for the maintainer's review

The brief left these open. Each is the simplest correct option.

1. **A write's receipt names a delta graph only where it puts content in it.** A create names `pat:asserts`, a tombstone names `pat:retracts`, and a
   replace names both. A create has nothing to retract and a tombstone nothing to assert, so a graph named for them would be one that never exists. A
   replay reader reads whichever the receipt names.
2. **The IR's rule of one payload slot is dropped.** A create writes its payload slot into the data graph and into the add graph, which is the plan's
   "the query reuses the payload slot", and a replace has three slots. A rule that counted slot uses refused both. The rule's test row is removed
   and the behaviour is tested instead (H2.6d-T4, T7, T8).
3. **A create and a tombstone have no digest part of their own for what they record.** A create's add graph is its payload, already a part, and a
   tombstone's del graph is copied from the store and is not in the request. A replace has `AddPart` and `DelPart`, in that order after the payload.
4. **The twenty-four variants are builders and templates of their own,** named by the base stem, the model and the guard, for example
   `cas-replace-composite-property-patch-log-dataset-guard`. A parameter on the six builders gives the variants, and the templates were written from
   the existing ones by a script and checked by the equivalence harness. The alternative, one template with a switch, is not possible in Mustache
   without a second renderer.
5. **`dal:NoReceipt` writes no head and keeps the claim as it is.** The claim still holds `pat:rev $newRev`, so `newRev` is a parameter and the caller
   still mints it, but nothing in the log names it. A row that already has a head from an earlier model keeps it, since the variant neither removes
   nor writes one (H2.6d-T13). A tombstone has no cause and no actor, which only a receipt records.
6. **The three audits that read receipts are not generated under `dal:NoReceipt`.** The gap scan would report every one of its rows. The fork audit
   on claims stays.
7. **A composite family may declare `dal:NoReceipt`.** The refusal `CompositeBoundaryReceiptConflict` is for `dal:ReceiptOnly`, which promises an
   audit it cannot give. `dal:NoReceipt` asks for no history, so the refusal does not apply. It is a plain opt-out, and the maintainer may prefer
   it refused.
8. **One refusal, `NoReceiptWithAppendDiscipline`,** with four causes. A stream is recognised as the compiler selects it, which is
   `dal:AppendOnly`, or an event grain under a concurrency that is not `dal:Optimistic`.
9. **`cas-replace-named-graph` is at builder version 2** since it no longer takes `$assertGraph` and `$retractGraph`. The receipt-only form never had
   a use for them, since nothing filled them (TD-46), and keeping them would have named graphs that no one writes.
10. **The builder goldens are pinned for three builders.** The golden of a builder records its text for the first fixture that generates it. The
    examples that declare `dal:PatchLog` no longer generate the receipt-only named-graph writes, so the first fixture moved and the recorded text with
    it, though the builders were unchanged for create and tombstone (checked by hash). The pin in `builder_goldens.py` takes their context from
    `write-discipline-snapshot-named-graph`, which has the baseline's target.
11. **Tests that exercise the receipt-only composite writes use `dal:SnapshotPerRevision`.** `receipt_only.py` replaces `dal:PatchLog` with it in a
    loaded example, so the sweep, lifecycle and guard tests keep testing the templates they always did.
12. **No new example.** The compiled profiles of the new variants are in the existing examples' expected profiles, and `dal:NoReceipt` needs no
    shipped example to be tested.

## Findings

1. **`dal:PatchLog` is silent where no variant writes it.** The plan says `ReceiptModelNotHonoured` warns for the snapshot alone, so a family that
   declares `dal:PatchLog` and appends, writes unconditionally or is value guarded records a receipt only and nothing says so, against H1.4c. The
   shipped `append-stream-dataset-guard` is one. TD-46 records it. The remedy is a warning keyed to the selected operations and not to the model, for
   the maintainer to choose.
2. **A gap scan reads every version row of its meta graph.** A family under `dal:NoReceipt` keeps no receipts, so a scan generated for another family of
   the same meta shard reports its rows. The scan is not generated for the no-receipt family itself, and the ontology README says such a family
   belongs in a shard of its own. Nothing checks it.
3. **The receipt-only templates of a composite family are reached only through `dal:SnapshotPerRevision`,** since `dal:ReceiptOnly` is refused for
   a composite family and `dal:PatchLog` now selects other templates. They are generated and tested, and no honest configuration uses them. They
   are candidates to remove with the templates in H2.9.
4. **The replace has three slots to keep consistent.** `payloadTriples` must be the old state less `retractTriples` plus `assertTriples`. Nothing
   in the update checks it, and H2.8's caller check is where it belongs. H2.6d-T2 pins that the update writes what it is given.
5. **`check:ontology-catalog` fails while `ontology/persistence/execution/` holds generated output.** `build:persistence-execution` was run here to
   confirm that every example still compiles, and its output is git-ignored but is a directory the catalogue does not list. The three failures name
   that directory. Removing the generated subdirectories restores the check. The removal was refused to this agent by the safety check, so it was
   left.

## Changes to existing tests

| Test | Change |
|---|---|
| `test_h2_2_t1` | the list of ported builders gains the 24 variants |
| `test_h2_6b_t11` | the patch log case becomes "does not warn", the snapshot case stays. Its fixtures are `warning-ReceiptModelNotHonoured` (now the snapshot) and `_base-thing` |
| `test_h2_6_t4` and `t5` | `INTENDED` is emptied and `designed` returns the builder's contract. The one row closed was `$assertGraph` and `$retractGraph` required under `dal:PatchLog`, which the patch-log variants resolve by dropping the parameters. `_facts` and `_read_contract` read `AddPart` and `DelPart` |
| `test_ir` | the refusal row "two payload slots" is removed (decision 2) |
| `test_h2_3_t12` | the test now asserts that the receipt-only replace writes no `pat:asserts` and no `pat:retracts`, even when given the old parameters. It asserted that it wrote them |
| `test_h2_3_t25` and `t29` | no parameter is left in the substituted text, and the two golden `.rq` files lose the two parameter lines |
| `test_h2_3_t32` | the role table gains `?addGraph` and `?delGraph` as `patch` |
| `test_h2_5_t40` | the role table gains `addGraph` and `delGraph` |
| `test_ho8_t8` | the count of templates that name a graph from a root is 19, and was 7 |
| `test_compiler_integration` (two tests), `test_template_alignment` (one) | the selected template ids are the `-patch-log` variants, since the examples declare `dal:PatchLog` |
| `test_graph_naming` (t1, t2, t2b) | the create under test is the patch-log variant |
| `test_write_disciplines` t1, t2, t8, t10 | R2 (the direction and the predicate, builder version 2) |
| `test_composite_*` (four files) | load their examples through `receipt_only` (decision 11) |

## Test cases

`test_patch_log.py`, 226 cases, 104 of them on Oxigraph. The behaviour cases run on both engines, with and without the parameter guards, and for both
families. Cases with a `dg` axis run both the row-level and the dataset-guard variant.

| ID | Checks |
|---|---|
| H2.6d-T1 | a replace's add and del graphs hold exactly the caller's delta, the aggregate holds the payload, and the receipt names both |
| H2.6d-T2 | the delta is what the caller gave and not the payload, even when it is not the difference of the payload and the old state |
| H2.6d-T3 | a tombstone's del graph holds the old aggregate, the root and an owned member for a composite family and no neighbour, and the receipt names it |
| H2.6d-T4 | a create's add graph holds its payload, and the receipt names it and nothing to retract |
| H2.6d-T5 | a retry with the same transaction id writes nothing, the delta graphs included |
| H2.6d-T6 | a write that loses the race writes nothing and no delta graph |
| H2.6d-T7 | a replace that leaves any of its three slots out writes nothing, on each engine |
| H2.6d-T8 | a create that leaves its payload slot out writes nothing |
| H2.6d-T9 | an empty delta gives empty graphs and the receipt still names both |
| H2.6d-T10 | a create, a replace and a tombstone leave a log from which the state is rebuilt from the deltas |
| H2.6d-T11 | a write under no receipt writes no receipt, no log bucket and no head, keeps the claim with its digest, and moves the row |
| H2.6d-T12 | a retry and a lost race under no receipt write nothing |
| H2.6d-T13 | a row that has a head keeps it under no receipt |
| H2.6d-T14 | the replace's digest parts, its `PatchContent` access and its parameters, with no graph parameter |
| H2.6d-T15 | a create and a tombstone have no add or del digest part, and both write patch content |
| H2.6d-T16 | the no-receipt variants touch no receipt and no patch content, and the patch-log variants touch both |
| H2.6d-T17 | `compile` selects the patch-log variants for both families and both guards |
| H2.6d-T18 | `compile` selects the no-receipt variants and leaves out the receipt audits, and keeps the fork audit |
| H2.6d-T19 | the other models keep the receipt-only writes |
| H2.6d-T20 | `ReceiptModelNotHonoured` warns for the snapshot alone |
| H2.6d-T21 | no receipt is refused with append versions, append records and a stream, and allowed in place |
| H2.6d-T22 | a composite family with no receipt is not refused as one with `dal:ReceiptOnly` is |
| H2.6d-T23 | the delta graphs are named from the receipt and no parameter names them |

The witness-coverage tests cover the new refusal and the narrowed warning, and the equivalence harness (`test_h2_2_t2`, `t3`) holds each of the 24
builders and the changed `append-version` and `cas-replace-named-graph` to their templates on every fixture. The static checks (S-3, S-4) and the
builder golden check cover the rest.

## One command

```
mise run check:persistence
mise run check:persistence-oxigraph
```

From the repository root. A pass is no failed test in either, and `check:persistence-expected-profiles` (part of the first) reporting that the
profiles are current. `mise run build:persistence-expected-profiles` and `mise run build:persistence-builder-goldens` regenerate the two records
after a change to a builder.

## Results

| Command | Result |
|---|---|
| `mise run check:persistence` | 3648 passed, 1 xfailed, no failures, expected profiles current (H2.6c recorded 2869 passed, in an environment with fewer Oxigraph cases collected) |
| `mise run check:persistence-oxigraph` | 5 passed in the Oxigraph store package, 329 passed in the persistence tests marked for Oxigraph (225 in H2.6c), none skipped |
| `mise run check:import-guard`, `check:python-root`, `check:published-decisions` | pass |
| `mise run build:persistence-execution` | ran, every example compiles or keeps its refusal. See Finding 5 |
| `mise run check:ontology-catalog` | 3 failed, 1133 passed, all three for the generated `execution` directory (Finding 5) |
| `mise run check:ontology-versioning` | fails, `UNBUMPED` for the substrate release, as expected while this branch ignores versioning (TD-64) |

Not run: `check:deny-terms` (needs a personal deny-list, to be run before a commit), the formal-methods checks, which this slice does not touch, and
the cost of the new variants. The fills of a patch-log replace are M × (N + c) and of a tombstone M, as the plan's table states, and were not measured.

## Adversarial probes

Each was run on the finished tree and then reverted. The persistence source and tests were compared with a copy taken before the first probe and are
identical.

1. **A replace that writes its add graph from the payload** (the add graph block also holds `{{{payloadTriples}}}`). `test_patch_log.py` fails 32
   cases, T1, T2 and T9, on both engines. The equivalence harness fails as well, since the template does not do it.
2. **A tombstone that does not copy its sweep** (the del block removed from the insert). 20 cases fail, T3, T10, T15 and T16.
3. **`append-version` writing `fnd:supersededBy`** (the old triple in place of `pat:previousVersion`). `test_write_disciplines.py` fails 12 cases,
   T1, T2 and T8.
4. **`dal:NoReceipt` accepted with `dal:AppendVersions`** (the append disciplines taken out of the refusal's condition). `test_h2_6d_t21` fails.

## Deliberate non-coverage

- A generated as-of read, forward or backward. The guide says how to read backward, and the generation is TD-48's.
- The caller's check that a delta satisfies the patch rules, and that the payload is the old state less the del triples plus the add triples (H2.8).
- A snapshot of in-place families (`dal:SnapshotPerRevision`, H2.10), which still warns.
- A warning for a patch log that no operation writes (Finding 1), and a check that a no-receipt family has a meta shard of its own (Finding 2).
- Checkpoints, the cost of a replay, and the sizes of the delta graphs against the plan's table. None was measured.
- A named-graph append of versions, a version row in a meta graph per family, and Fuseki and the other stores. Only rdflib and Oxigraph are
  measured (TSD-Q12).
