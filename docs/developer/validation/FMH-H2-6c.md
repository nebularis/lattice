<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-H2.6c, the write disciplines

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice H2.6c, planned in
[plan §4.9](../plans/formal-methods-track-h.md#49-h26c-the-write-disciplines-planned-2026-10-20). Decided at our leanings on 2026-10-20 (VH-Q1 to
VH-Q6, VH-D1, VH-D2, FS-Q1 to FS-Q7) and built the same day, for the maintainer's review. Authored and run in autonomous mode, not committed.
Versioning is ignored on this branch (TD-64), so no version IRI moved.

**For the maintainer:** re-approve the eleven expected profiles that changed or are new (below), accept or change the ADR-A123 addendum
draft, read the decisions taken alone, and countersign the two changes to existing tests.
**For countersignature (non-weakening rule):** two existing tests changed, both because a list they pin grew. `test_h2_2_t1` lists the
ported builders and gains `append-version` and `append-version-dataset-guard`. `test_h2_6_t1` counted nine expected profiles and now
asserts eleven, equal to the number of configurations, and its name no longer says "nine". No test was removed or skipped.

## Invariant

A write under `dal:AppendVersions` never deletes. After a second version, the first is still whole in the data graph and linked to the
second by `fnd:supersededBy`, the identity's version row names the latest version written and its seq has stepped once per write, a retry
with the same transaction id and a write at a stale seq write nothing, and a member the new version does not restate is still reached
from it. A versioned class written in place is reported, never silent (H1.4c).

## What changed

- **Vocabulary** (`ontology/persistence/spec/persistence.ttl`, §16a). `dal:WriteDisciplineProfile`, `dal:WriteDiscipline`,
  `dal:writeDiscipline` and the individuals `dal:InPlace`, `dal:AppendVersions` and `dal:AppendRecords`. `constraints.ttl`'s shared-class
  warning also targets the new profile class. No version IRI changed.
- **Resolution** (`model.py`, `resolver.py`). A new dimension `writeDiscipline`, baseline `InPlace`, resolved like any other. Every
  compiled profile now carries it.
- **Selection** (`operations.py`). `AppendVersions` gives `bootstrap-version-row` and `append-version` (with the dataset-guard variants
  under that epoch scope). `AppendRecords` gives the append form for any concurrency. `InPlace` is unchanged.
- **The builder and templates** (`builders.py`, `append-version.mustache`, `append-version-dataset-guard.mustache`). One update, no sweep and
  no delete. Foundation is not imported, and `fnd:supersededBy` is written as a constant IRI (`namespaces.FND`).
- **The refusal and the warning** (`validator.py`). `AppendVersionsUnsupported` (refusal), `VersionedClassWrittenInPlace` (warning).
  `CompositeBoundaryReceiptConflict`, the refusal the plan calls `CompositeBoundaryReceiptOnly`, no longer applies under either append
  discipline. The no-boundary-without-value-guard refusal (`NoBoundaryConcurrencyConflict`) does not apply under `AppendVersions`.
- **The contract** (`contract.py`, `gaps.py`, `templatecheck.py`). Operation kind `AppendVersion`, builder `append-version` at version 1,
  the gap rule for retention counts it as a writing operation, and the S-3 check lists `prevRev` and `priorVersion` as optional insert
  variables with the reason.
- **Fixtures.** Two examples, `write-discipline-composite-append-versions.ttl` and `write-discipline-noboundary-append-versions.ttl`, each
  under the dataset-level guard. Two witnesses, `refusal-AppendVersionsUnsupported.ttl` and `warning-VersionedClassWrittenInPlace.ttl`,
  and two ordinary fixtures, `write-discipline-append-records-composite.ttl` and `write-discipline-append-versions-row-guard.ttl`, which
  give the append form and the row-level variant. The new files are named so they sort after every existing fixture, because the builder
  goldens record the first fixture's context for each builder (see Findings).
- **Documents.** The ontology README §7.10 (with "what works best when"), the dimension, operation and validation tables and two example
  rows, the compiler README, ADR-A123's addendum of 2026-10-20 (draft), TD-46 narrowed, this pack.

## Expected profiles (for re-approval)

| File | Change |
|---|---|
| `append-stream-dataset-guard.expected.ttl` | gains the `writeDiscipline` dimension, resolved `dal:InPlace` |
| `baseline-single-class.expected.ttl` | the same |
| `baseline-single-class.caller-named.expected.ttl` | the same |
| `claim-scheme-dual-rotation.expected.ttl` | the same |
| `composite-project-ownership.expected.ttl` | the same |
| `epoch-dataset-level-guard.expected.ttl` | the same |
| `uniqueness-merge-policy.expected.ttl` | the same |
| `uniqueness-quarantine-policy.expected.ttl` | the same |
| `value-based-cas.expected.ttl` | the same |
| `kinds.expected.ttl` | adds the operation kind `dal:AppendVersion` |
| `write-discipline-composite-append-versions.expected.ttl` | new. A composite family, `bootstrap-version-row` and `append-version` in their dataset-guard variants, `ReceiptOnly`, no diagnostic of the new kinds |
| `write-discipline-noboundary-append-versions.expected.ttl` | new. A family with no boundary and a data graph |

No existing operation's declaration changed.

## Decisions taken alone, for the maintainer's review

The brief left these open. Each is the simplest correct option.

1. **The row's current version is a new predicate, `pat:currentVersion`.** `pat:head` stays the latest receipt, as in every other write.
   The plan's "the row's head" would otherwise have to mean two things. The prior version to supersede is read from `pat:currentVersion`.
2. **The first version is written by `append-version` at seq 0, onto a row `bootstrap-version-row` created, whatever `dal:firstWrite` says.**
   A `create-if-absent` would write the first version without setting the current version, so the second would supersede nothing. Declaring
   `dal:AbsentRow` (the baseline) is not an error, and `create-if-absent` is simply not generated. The caller's obligation to bootstrap the
   row is the one already in the README.
3. **A family that appends versions has no tombstone, no create and no replace.** A tombstone sweeps the family's data and would delete the
   history. Removing a version identity is housekeeping or erasure (ADR-A80), which is not generated. This is deliberate non-coverage.
4. **The named-graph variant (one graph per version) is not built.** A named-graph family that declares `dal:AppendVersions` is refused with
   `AppendVersionsUnsupported`, so the profile never quietly drops the declaration (H1.4c). It is deliberate non-coverage.
5. **One refusal kind with three causes.** `AppendVersionsUnsupported` covers a named-graph family, a concurrency that is not `dal:Optimistic`,
   and no boundary with no `dal:dataGraph`. The witness file covers the first and the test `h2_6c_t16` covers all three.
6. **No-boundary families append into their `dal:dataGraph`.** With no boundary there is no graph to hold versions, and the default graph is
   never written (S-1), so the profile must declare one. `NoBoundaryConcurrencyConflict` is not raised under `AppendVersions`, because the
   guard is the version row and not a value.
7. **`AppendRecords` selects the append form for every concurrency,** even `dal:Optimistic`. It needs no check of its own.
8. **The version is an `Aggregate` resource in the contract.** The data graph's role is `data`, which maps to `Aggregate`, so the version
   is the aggregate resource inserted and never deleted. A separate `Version` resource kind would need a new graph role, which the brief
   does not ask for.
9. **No new request-time slot.** The new version's own triples use `{{{payloadTriples}}}`, and `$newVersion` is a parameter.
10. **The receipt does not link back to the version.** The version names its receipt with `pat:revision`, as the plan says. A
    `pat:creates` link the other way was left out.
11. **`dal:WriteDisciplineProfile` is a new profile class,** the dedicated class of the new dimension, so a profile of any class can declare
    it. `dal:DataAccessProfile` carries it too, as it carries every dimension.
12. **The two new examples both use the dataset-level guard.** The row-level variant is covered by a witness fixture.

## Findings

- **The builder goldens depend on fixture order.** `builder_goldens.current()` records each builder's rendering for the first fixture that
  generates it, examples before witnesses. A new example that generates `bootstrap-version-row` ahead of the witness that did before changed
  the recorded text of `bootstrap-version-row` and `append-event` and made the update refuse to record it, since their versions had not moved.
  The new fixtures are named `write-discipline-*` so they sort last, and the goldens gained two entries and changed none. The fragility is
  the harness's and is not changed here.
- **A mutation that deletes the prior version is also a template mismatch.** Probe 1 below stops at the first behaviour failure, and the
  equivalence harness would fail as well, since the template does not delete.

## Test cases

`test_write_disciplines.py`, 47 cases, 18 of them on Oxigraph. The behaviour cases run on both engines with and without the parameter guards.

| ID | Checks |
|---|---|
| H2.6c-T1 | a second version leaves the first whole and links it to the second by `fnd:supersededBy`, and the second supersedes nothing |
| H2.6c-T2 | the first version supersedes nothing, the row names the latest version, head and seq, and a third version chains from the second only |
| H2.6c-T3 | each version names its receipt by `pat:revision`, and the receipts chain by `pat:prevRev` |
| H2.6c-T4 | a member the second version does not restate is still reachable from it, and was written once |
| H2.6c-T5 | a retry with the same transaction id writes nothing |
| H2.6c-T6 | a write at a stale seq, or ahead of the row, writes nothing |
| H2.6c-T7 | no row, or a row marked deleted, writes nothing |
| H2.6c-T8 | the dataset-guard variant writes only while the dataset epoch matches, and rebases a row behind it |
| H2.6c-T9 | with the guard on, a missing parameter writes nothing |
| H2.6c-T10 | the operation never deletes from the data graph, its contract kind and accesses, its digest and its parameters |
| H2.6c-T11 | the discipline resolves `InPlace` when absent for every example that declares none, which still compile with the same operations |
| H2.6c-T12 | `AppendVersions` selects a bootstrap and an `append-version` and nothing else that writes |
| H2.6c-T13 | the epoch guard scope picks the variant |
| H2.6c-T14 | `AppendRecords` selects the append form, and `InPlace` the replace family |
| H2.6c-T15 | the append binding names the data graph and no owned path |
| H2.6c-T16 | the refusal for each of its three causes, and none for the no-boundary example |
| H2.6c-T17 | a no-boundary family without a value guard is refused in place and allowed when it appends versions |
| H2.6c-T18 | a composite family with `dal:ReceiptOnly` is refused in place and allowed under `AppendVersions` and `AppendRecords` |
| H2.6c-T19 | `VersionedClassWrittenInPlace` fires in place and not under either append discipline or for an unversioned class |
| H2.6c-T20 | the warning finds a version through a chain of subclasses and names the remedy |

The witness-coverage tests cover the refusal and the warning. The equivalence harness (`test_h2_2_t2`, `t3`) holds both variants of the
builder to their templates, and the contract, expected-profile, builder-golden and static-check tests cover the rest.

## One command

```
mise run check:persistence
mise run check:persistence-oxigraph
```

From the repository root. A pass is no failed test in either, and `check:persistence-expected-profiles` (part of the first) reporting no
stale file. `mise run build:persistence-expected-profiles` and `mise run build:persistence-builder-goldens` regenerate the two records after
a change to a builder.

## Results

| Command | Result |
|---|---|
| `mise run check:persistence` | 2869 passed, 1 xfailed, no failures, expected profiles current (before H2.6c: 2756 passed, 1 xfailed) |
| `mise run check:persistence-oxigraph` | 5 passed in the Oxigraph store package, 225 passed in the persistence tests marked for Oxigraph, none skipped |
| `mise run check:ontology-catalog`, `check:import-guard`, `check:python-root`, `build:persistence-execution` | pass |
| `mise run check:ontology-versioning` | fails, `UNBUMPED` for the substrate release, as expected while this branch ignores versioning (TD-64) |

Not run: `check:deny-terms` (needs a personal deny-list, to be run before a commit), and the formal-methods checks, which this slice does not touch.

## Adversarial probes

Each was run on the finished tree and then reverted. The tree was compared with its backup after the last one.

1. **An `append-version` that deletes the prior version** (a `DELETE` of the prior version's triples in the data graph, with a matching
   `OPTIONAL`). `test_h2_6c_t1` fails on the first engine run, since the first version is no longer whole.
2. **An `append-version` that skips `fnd:supersededBy`.** `test_h2_6c_t1` and `test_h2_6c_t2` fail on all four engine and guard
   combinations, which are the chain tests.
3. **A versioned class compiled in place without the warning.** `test_h2_6c_t19` and `t20` fail, and so do the witness-coverage tests
   (`test_h1_2_t15`, `t16`, `t23`, `t27`, `t28`), since `VersionedClassWrittenInPlace` has no witness.

## Deliberate non-coverage

- The named-graph append (one graph per version, named from the version, ADR-A51's content revision IRI), refused as above.
- A tombstone or any removal for a family that appends versions, left to housekeeping and erasure.
- The patch log for in-place families (H2.6d), the snapshot (H2.10), and the vocabulary's publication and the compiler's emission (H2.7).
- A check that the new version's payload holds only its own triples, that a member it points at exists, or that it is a node of the family's
  class, which is the caller check of H2.8.
- Which version is in force or agreed, which is evaluated from assents and never stored (VH-D1). `fnd:supersededBy` is written at each
  append as the plan says, whereas the sketch's VH-D1 says it is asserted when an amendment is agreed. The plan's wording is built, and the
  difference is for the maintainer.
- Fuseki and the other stores. Only rdflib and Oxigraph are measured (TSD-Q12).
