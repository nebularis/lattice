<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-H2.6f, how a root version lists its members

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice H2.6f, planned in
[plan §4.12](../plans/formal-methods-track-h.md#412-h26f-how-a-root-version-lists-its-members-with-fixtures-and-a-benchmark-planned-2026-10-20)
(H2.6f-Q1 to Q4), decided 2026-10-20 and built the same day for the maintainer's review. Authored and run in autonomous mode, not committed.
Versioning is ignored on this branch (TD-64), so no version IRI moved.

**For the maintainer:** re-approve the expected profiles that changed (below), accept or change the ADR-A123 addendum (accepted with the slice's
plan, so the decisions taken alone are the part to read), and read the decisions taken alone and the benchmark.
**For countersignature (non-weakening rule):** no existing test was weakened, skipped or removed. Three tests that count things gained the new
case: the ported-builder list (`test_h2_2_t1`), the expected-profile count (`test_h2_6_t1`, 11 to 12), and the builder goldens file.

## Invariant

A family that declares `dal:AppendVersions` may declare `dal:membershipEncoding`, `dal:FullMembership` (absent) or `dal:DeltaMembership`, and
`dal:checkpointEvery` (absent means 16). Under delta membership `append-version` writes `pat:previousVersion` and `pat:addsMember` and
`pat:dropsMember` for what changed, never the domain's membership property, except on a checkpoint version, where the caller writes the full list
and `pat:checkpoint true`. The generated `members` query returns a version's members from the chain back to the nearest checkpoint, honouring
drops, and a domain shape runs over those results in a scratch graph and never over the stored delta.

## What changed

- **Vocabulary** (`spec/persistence.ttl` §16b). `dal:MembershipEncoding`, `dal:FullMembership`, `dal:DeltaMembership`, `dal:membershipEncoding`
  and `dal:checkpointEvery`, both properties on `dal:WriteDisciplineProfile`, resolved like `dal:writeDiscipline` (two new dimensions, with the
  interval a literal dimension and a baseline of 16).
- **Checks** (`validator.py`). Three refusals, `DeltaMembershipNeedsAppendVersions`, `MembershipEncodingUnknown` and `CheckpointEveryInvalid`,
  each with a witness.
- **Selection** (`operations.py`). Under delta membership `append-version` is the `append-version-delta` template and the family gains the
  `members` operation. Otherwise nothing changes.
- **Builders and templates.** `append-version-delta` and its dataset-guard variant (two more request-time slots, `addedMembers` and
  `droppedMembers`), and `members`, each with a Mustache template that the equivalence harness holds the builder to. Builder version 1.
- **Contract** (`contract.py`). The kind `MembersRead`, and the delta write's add and del digest parts naming the two slots.
- **Caller side** (`persistence/members.py`). `is_checkpoint(next_seq, every)` and `materialise(version, property, rows)`.
- **Example, witnesses and fixtures.** `examples/write-discipline-delta-membership.ttl`, three refusal witnesses and a row-guard variant,
  and the TriG fixtures under `ontology/persistence/test/membership/`.
- **Benchmark** `benchmark/persistence-membership/`, with the task `check:persistence-membership`, and the task
  `build:persistence-membership-fixtures`.
- **Documents.** The ontology README §7.10.1, the compiler README, ADR-A123's addendum, and the benchmark's README.

## Expected profiles (for re-approval)

| File | Change |
|---|---|
| the eleven existing profiles | each gains the two resolved dimensions `membershipEncoding` (full) and `checkpointEvery` (16, a literal), nothing else |
| `kinds.expected.ttl` | declares the kind `MembersRead` |
| `write-discipline-delta-membership.expected.ttl` | new, the example's profile with the delta write and the `members` operation and their contracts |

## Decisions taken alone, for the maintainer's review

1. **The caller knows a checkpoint from the sequence alone.** The caller passes the full list and `pat:checkpoint true` when the version it
   writes has `nextSeq` equal to 1 or a multiple of `dal:checkpointEvery`, and the two member slots otherwise. The write cannot decide it, since
   SPARQL has no remainder in our fragment and the caller already holds the sequence. The alternatives, a query-computed marker or a flag
   parameter, add a dependency of the data on the seq arithmetic or a second source of truth. H2.8's caller check verifies it.
2. **The first version is always a checkpoint,** whatever the interval, since nothing precedes it to be a delta against. A version with no
   checkpoint before it has no members.
3. **`pat:checkpoint true` is stored on the version, and the query finds the nearest checkpoint by it,** not by seq arithmetic, so a family
   that changes its interval keeps reading its old history.
4. **The membership property is a parameter of `members`,** `$membershipProperty`, and not a binding, since the family declares none. A
   family with several membership properties runs the query once for each.
5. **A drop is honoured against any earlier version of the chain and a later add wins.** A member dropped by version k is out of every version
   from k on until an add at a version after k. Dropping and adding one member in one version leaves it dropped, which the caller never writes.
6. **`dal:checkpointEvery` is an `xsd:long`** on `dal:WriteDisciplineProfile`, read as a literal dimension. A non-integer or a value below 1 is
   refused at compile (`CheckpointEveryInvalid`), and an interval or an encoding declared on a family that does not use delta membership
   is accepted and does nothing, as `dal:FullMembership` is the default.
7. **`dal:DeltaMembership` is refused unless `dal:AppendVersions` is declared** (`DeltaMembershipNeedsAppendVersions`), since a delta needs the
   version before it.
8. **The digest parts reuse the add and del parts,** with the two member slots as their sources, so the contract needs no new part role.
9. **Domain shape validation is a documented procedure and a helper** (`materialise`), not a generated operation, since the shape is the
   domain's.
10. **The fixtures are generated by the operations and not typed,** under `ontology/persistence/test/membership/` beside the expected profiles
    (ontology test data, as in EX-Q2 (b)), with one task to regenerate and a test that holds them to the operations. They are E5 (500 members,
    one replaced) and E7's wording set (150 inclusions, one replaced), each under full and delta membership. In place with a patch log has no
    fixture here, since the benchmark checks its counts.
11. **The benchmark's in-place strategy is the composite replace under a patch log,** with the whole current set as payload and the one change in
    the add and del slots, so it pays TD-42's quadratic sweep, which is part of what an adopter would pay.
12. **The `members` query is read-only and `DISTINCT`,** with one column, and uses the closed fragment with path predicates only.

## Counts (E5 and E7)

Triples of version 2 other than its type and receipt link, after a first version that lists every member.

| Scenario | Full membership | Delta membership |
|---|---|---|
| E5, 500 members, one replaced | 501 (500 members and `pat:previousVersion`) | 3 |
| E7, 150 members, one replaced | 151 | 3 |

Whole data graph after two versions: E5 1,006 against 508, and E7 306 against 158 (full against delta). The sketch's 540 is the same figure with the
header, three pointers per location and the new location's own nodes.

## Test cases

`test_membership.py`, 21 cases, run on rdflib and Oxigraph with the guards on and off where they execute updates.

| ID | Checks |
|---|---|
| H2.6f-T1 | a checkpoint lists every member and a delta states only changes, never the membership property |
| H2.6f-T2 | an empty delta writes the version and its link alone |
| H2.6f-T3 | the dataset-guard variant writes only while the dataset epoch matches |
| H2.6f-T4 | a stale seq or a retried transaction writes nothing |
| H2.6f-T5, T6 | members of checkpoints and deltas equal the model, in any read order |
| H2.6f-T7 | dropped then added is a member, added then dropped is not |
| H2.6f-T8 | the chain stops at the nearest checkpoint |
| H2.6f-T9 | 41 versions at the default interval of 16 equal a random reference model on each side of each checkpoint |
| H2.6f-T10 | no checkpoint before it, no members, and a missing parameter returns nothing with the guard on |
| H2.6f-T11 | `is_checkpoint` and its refusals |
| H2.6f-T12, T13 | a domain shape over the resolved members finds what a shape over the full list finds, and over the stored delta passes vacuously |
| H2.6f-T14 | the defaults, and no `members` operation for any other example |
| H2.6f-T15, T16 | a delta family resolves and selects the delta write and `members`, and the profile records both |
| H2.6f-T17, T18, T19 | each refusal by its witness, a bad interval, and that full membership declared changes nothing |
| H2.6f-T20, T21 | the contracts of `members` and of the delta write |

`test_membership_fixtures.py`, H2.6f-F1 to F2 (the files are current, and the counts above). The benchmark's own tests, `test_check.py`, 5 cases.
The H1.2 witness coverage tests cover the three new refusals. The equivalence harness holds the three new builders to their templates.

## One command

```
mise run check:persistence
mise run check:persistence-oxigraph
mise run check:ontology-catalog
mise run check:persistence-membership
```

From the repository root. A pass is no failed test, and `check:persistence-expected-profiles` and the fixture test reporting nothing stale.
`mise run build:persistence-expected-profiles`, `build:persistence-builder-goldens` and `build:persistence-membership-fixtures` regenerate.

## Results

| Command | Result |
|---|---|
| `mise run check:persistence` | 3802 passed, 1 xfailed, no failures, expected profiles current (H2.6e recorded 3662 passed) |
| `mise run check:persistence-oxigraph` | 353 passed in the persistence tests marked for Oxigraph (H2.6e recorded 329), and the 5 support tests |
| `mise run check:ontology-catalog` | 1136 passed, 7 skipped |
| `mise run check:ontology-versioning` | not run, which fails `UNBUMPED` as expected on this branch (TD-64) |
| `mise run check:persistence-membership` | passed, numbers below (about 5 minutes, most of it rdflib) |

`build:persistence-execution` was not run, so no `execution` directory was left. `check:deny-terms` was not run (it needs a personal deny-list).

## Benchmark

Run of 2026-10-20, `mise run check:persistence-membership`, rdflib 7.6.0, pyoxigraph 0.5.11, Python 3.14.7, Darwin arm64
(a laptop, one process at a time). A set of 500 members, one replaced per version, checkpoint every 16 for delta. It passed, so every member set equalled
the reference model and every stored count was the arithmetic's, on both engines. Time did not decide the result.

| engine | strategy | versions | stored triples | last write s | all writes s | read of current members s |
|---|---|---|---|---|---|---|
| rdflib | full | 1 | 503 | 0.418 | 0.42 | 0.0050 |
| rdflib | full | 10 | 5,030 | 0.374 | 3.78 | 0.0044 |
| rdflib | full | 100 | 50,300 | 0.379 | 38.06 | 0.0045 |
| rdflib | delta | 1 | 503 | 0.384 | 0.38 | 0.0595 |
| rdflib | delta | 10 | 548 | 0.013 | 0.49 | 0.1465 |
| rdflib | delta | 100 | 3,992 | 0.013 | 4.00 | 98.6188 |
| rdflib | in-place | 1 | 500 | 0.000 | 0.00 | 0.0044 |
| rdflib | in-place | 10 | 518 | 1.459 | 13.11 | 0.0044 |
| rdflib | in-place | 100 | 698 | 1.481 | 145.43 | 0.0045 |
| oxigraph | full | 1 | 503 | 0.002 | 0.00 | 0.0015 |
| oxigraph | full | 10 | 5,030 | 0.001 | 0.01 | 0.0013 |
| oxigraph | full | 100 | 50,300 | 0.001 | 0.14 | 0.0014 |
| oxigraph | delta | 1 | 503 | 0.002 | 0.00 | 0.0025 |
| oxigraph | delta | 10 | 548 | 0.000 | 0.01 | 0.0032 |
| oxigraph | delta | 100 | 3,992 | 0.000 | 0.05 | 1.7293 |
| oxigraph | in-place | 1 | 500 | 0.000 | 0.00 | 0.0013 |
| oxigraph | in-place | 10 | 518 | 0.075 | 0.67 | 0.0016 |
| oxigraph | in-place | 100 | 698 | 0.071 | 7.14 | 0.0016 |

Stored triples are the data graph, plus the delta graphs for in-place. Writes are the guards-off updates as `instantiate` renders them.

Reading, on these figures.

- **Storage.** At 100 versions the full encoding holds 50,300 triples, delta 3,992 and in place 698 (500 and 198 in the delta graphs). Delta is 7.9 % of
  full, and its checkpoints, 7 lists of about 500, are 3,500 of its 3,992.
- **Write.** A delta write is the cheapest in time. On rdflib the last write is 0.013 s for delta,
  0.38 s for full (parsing a 500-triple payload) and 1.5 s for in place, whose replace is the quadratic sweep of TD-42. On Oxigraph the three are
  0.0004, 0.0014 and 0.071 s. A checkpoint version of delta costs what a full write does.
- **Read.** Full and in place read the current members in under 6 ms on rdflib. Delta reads in 0.06 s at 1 version and 0.15 s at 10, but 98.6 s at
  100 versions on rdflib and 1.7 s on Oxigraph, against 1.4 ms for the others. The chain is at most 16 links, so the cost is in the query's form and not in
  the data, which TD-68 records. The delta encoding's read is the price the plan names, and on today's `members` query it is a high one on rdflib.
- **Which to choose.** Delta wins storage and write cost by an order of magnitude or more at 100 versions, loses the read by the figures above, and
  gives up direct shape validation. Full is the right default, as planned. A deployment that reads members rarely, or reads them through Oxigraph,
  and writes a large set often, is the case for delta.


## Adversarial probes

Each was run on the finished tree and reverted. `builders.py` was restored from a copy, and its diff is the slice's change.

1. **A delta write that also writes the domain's membership property** (a `hasLine` triple added to the new version in the delta builder).
   H2.6f-T1 fails, as do the builder harness and the goldens.
2. **A `members` query that ignores drops** (the `NOT EXISTS` over `pat:dropsMember` removed). H2.6f-T3 and the other tests that drop a member fail,
   and the benchmark's own test of the same mutation fails with a wrong result.

## Deliberate non-coverage

- The caller check of H2.8: that a version is a checkpoint exactly when its seq says so, that a delta's adds are absent from and its drops present in
  the version before, and that a checkpoint's slots are empty.
- A generated shape over the resolved members, and a members query for a named-graph family (a named-graph family cannot append versions).
- Fuseki and the other stores.
- A faster form of the `members` query on rdflib (TD-68, added by this slice). Two forms that were faster were rejected because they changed the result.
  The query reads the chain with a step and a closure where one path would be about six times slower.
