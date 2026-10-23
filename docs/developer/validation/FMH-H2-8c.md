<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: FMH-H2.8c, the follow-ups of the H2.6 and H2.8 reviews

**Unit:** [`formal-methods-track-h`](../status/formal-methods-track-h.md), slice H2.8c,
[plan §4.18](../plans/formal-methods-track-h.md#418-h28c-the-follow-ups-of-the-h26-and-h28-reviews-planned-2026-10-20). Authored and run in
autonomous mode, committed locally and not pushed. Versioning is ignored on this branch (TD-64), so no version IRI moved.

**Signed off 2026-10-20.** The maintainer approved the seven decisions taken alone (decision 3 with TD-67 narrowed and not closed), the four
expected profiles and the four changed tests. No test was removed, skipped or weakened.

## Invariant

Each edge of a family's boundary shape is stated once, by the compiled profile, with an IRI, and the payload contract of every operation points
at the edges of its own profile (H2.6e (2), the middle ground). The `members` read gives the members of every version of a delta family exactly
as the reference model does, on rdflib under every hash seed and on Oxigraph, and finds its nearest checkpoint before it joins the chain
(TD-68, TSD-34). A profile can name record classes (`dal:recordClass`), which the evidence warning and a new warning on `dal:NoReceipt` read
(D-15 (b), D-9), and which the compiled profile states for the caller library. The add and del parts of a digest are documented once in each
of the three READMEs, for both meanings (H2.6f (8)).

## What changed

1. **Each edge stated once.** `compile` mints the profile's `dal:ReferenceEdge` nodes as `<target>/compiled/profile#edge-NN`
   (`contract_emit.mint_edge`), in the order of `edge_contracts`, where they were blank nodes. `emit_contract` writes a payload contract's
   `dal:referenceEdge` as pointers to those nodes and copies no edge facts. `contract_of` and `contract_for` lose their `edges` argument, so a
   contract derived from an operation has no edges. The library's reader is unchanged in code, since following `dal:referenceEdge` from a payload
   contract reaches the profile's edge, which holds the facts. A SPARQL constraint on `dal:PayloadContractShape` holds every pointer to an edge
   its own profile states.
2. **The faster `members` form.** The nearest checkpoint is found in a sub-select, `{ SELECT ?cp WHERE { ... FILTER NOT EXISTS { GRAPH ... } } }`,
   inside the data graph's block, and both `NOT EXISTS` bodies name their graph. The builder moves to version 3, its template follows, and the
   builder goldens are re-recorded.
3. **Record classes.** `dal:recordClass` (spec, no `rdfs:domain`). `validator.record_classes` reads every object of it in the configuration and
   their asserted subclasses. `EvidenceEdgeByIdentity` reads it beside `fnd:Evidence` and `fnd:DerivedArtefact`. A new warning,
   `NoReceiptForRecord`, fires for `dal:NoReceipt` on a family whose target class is versioned or a record class, with a witness. The compiled
   profile states the record classes the family touches as `dal:recordClass`, and the library reads them into `PayloadContract.record_classes`.
4. **The member parts.** The Persistence README (§7.10.1), the library README and the contracts README each say once what the add and del parts
   hold under `dal:DeltaMembership` and under a patch log, with an example of each. The comments of `dal:AddPart` and `dal:DelPart` say the same.
5. **Documents.** The Persistence README §7.1 (the edges stated once, record classes) and §7.4 (the new warning, and the stale "nothing checks
   that yet" for a no-receipt family's meta shard, which `NoReceiptSharesMetaShard` has checked since H2.8b), the compiler README, the comment of
   `dal:referenceEdge`, TD-67 narrowed, TD-68 (below).

## Decisions taken alone, approved by the maintainer 2026-10-20

All seven approved. Decision 3 is ratified with TD-67 narrowed. Decision 7 concerns test code only (`tests/tsd34_support.py`).

1. **The profile's edge IRIs** are minted under the reserved segment `profile`, `<target>/compiled/profile#edge-NN`, beside the operations'
   `<target>/compiled/<operation>#...`. No generated operation is named `profile`. The index follows the sorted edge order, as before, so an
   added edge can renumber the others, as it renumbered the per-operation copies.
2. **Record classes are named for the whole configuration.** Every `dal:recordClass` on any profile counts, with the subclasses the configuration
   asserts, as `dal:ReferenceData` does. It is not resolved per target through `dal:appliesTo`, since being a record is a fact about a domain class
   and not about one family. The alternative, a dimension resolved per scope, would let two families disagree on whether one class is a record.
3. **The caller check refuses nothing on a record class.** The library reads the record classes from the compiled profile, and `refusals` is
   unchanged. The compile only warns on an identity edge from a record, so that a deliberate choice compiles, and a refusal at the call would
   overrule it. The plan said TD-67 closes. It is narrowed instead, since a source of what is a version is still the caller's (`version_of`).
   To ratify, or to ask for a refusal (or an option that turns one on).
4. **The compiled profile states only the record classes the family touches**, its target class and the subject classes of its edges, and none
   where the family touches none, so the ten profiles that name no record class are unchanged.
5. **`NoReceiptForRecord` is a warning, and fires for a versioned target too,** as the plan's step 3 says. A versioned target written in place
   already has `VersionedClassWrittenInPlace`. Both fire for one written in place with no receipt.
6. **The part note sits on the role individuals** `dal:AddPart` and `dal:DelPart` in the spec, and not on each emitted `dal:DigestPart`, so the
   expected profiles do not grow by a comment per operation.
7. **The random-history sweep runs its 16 child processes side by side**, which takes about 80 s on four cores, where one after another took about
   five minutes.

## Changes to existing tests

| Test | Change |
|---|---|
| `test_reference_modes::test_h2_6e_t3` | the profile's edges are IRIs, not blank nodes |
| `test_reference_modes::test_h2_6e_t12` | reads the payload contract through the library, which follows the pointers, since `contract_of` no longer takes the edges. Its assertions are the same |
| `test_reference_modes::test_h2_6e_t13` | was "a contract given no edges has none". Now "each edge is stated once by the profile and every payload contract points at those edges", which keeps the old assertion that a derived contract has no edges and adds the pointers |
| `test_membership::test_h2_6f_t20` | `members` is at version 3 |

## Expected profiles (for re-approval)

Four changed. `composite-project-ownership`, `write-discipline-composite-append-versions` and `write-discipline-delta-membership` state each edge once,
on the profile with an IRI, and their payload contracts point at those edges, where each operation had its own copy (the composite profile lost
about 250 lines). `write-discipline-delta-membership` also has `members` at version 3. The other eight are unchanged. The library fixtures
`composite-project-ownership` and `write-discipline-delta-membership` are regenerated to match.

## Tests

| ID | Given / When / Then | Level | Pass criterion | +/- |
|---|---|---|---|---|
| H2.6e-T13 (changed) | a composite family is compiled. The profile's edges are IRIs, typed `dal:ReferenceEdge`, and every payload contract points at exactly those | L2 | sets equal | + |
| contract-shapes `an edge its own profile does not state` | a payload contract points at an edge no profile states. `dal:PayloadContractShape` reports it | L2 | the violation is reported | - |
| H2.8c-T5 | the `members` operation is built. Its block opens with a sub-select projecting `?cp`, and both `NOT EXISTS` bodies name their graph | L1 | structure as stated | + |
| H2.8c-T6 | 24 random histories (checkpoints every 2, 3 and 4, stray adds) on rdflib, each of 16 hash seeds in a child process. Every version reads its members as the reference model gives | L4 | `{"[]"}` | + |
| H2.8c-T7 | the same histories on each engine in process | L4 | `[]` on rdflib and Oxigraph | + |
| H2.6f-T5 to T10, H2.6g-T4, T4o | the existing reference-model tests of `members`, on both engines and with and without guards | L4 | unchanged, all pass | + |
| H2.8c-T8 | a profile names `ex:Order` a record class, or a superclass of it. An identity edge to a versioned class warns `EvidenceEdgeByIdentity`. With no record class, or a pinned edge, it does not | L2 | as stated | + / - |
| H2.8c-T9 | `dal:NoReceipt` on a family whose target is a record class, or versioned, warns `NoReceiptForRecord`. On a plain target it does not | L2 | as stated | + / - |
| H2.8c-T10 | the compiled profile states the record classes the family touches and not an unrelated one, the library reads them on each payload contract, and a profile with none states none | L2 | as stated | + |
| H2.8c-T11 | the spec declares `dal:recordClass` as an object property with no domain | L0 | as stated | + |
| witness | `warning-NoReceiptForRecord.ttl` raises the new warning | L2 | 128 rules witnessed, no known gap | + |

## Results (run 2026-10-20)

| Command | Result |
|---|---|
| `mise run check:persistence` | 4004 passed, 3 failed, 1 xfailed. The expected profiles check passed. The three failures are the Oxigraph cases below (TD-73) |
| `mise run check:persistence-oxigraph` | 365 passed, 3 failed, the same three |
| `mise run check:persistence-library` | vectors 91 checks passed, 0 failed. Library 75 passed |
| `mise run check:persistence-membership` | every member set and stored count right on both engines, to 100 versions (below) |
| `mise run check:ontology-catalog` | 1143 passed, "ontology catalog consistent, 2 known defect(s) reported" |
| `mise run check:catalogue` | 19 modules and 8 tool packages agree with the tree |
| `mise run check:published-decisions` | 6 passed |
| `python -m persistence witness` (through `check:persistence`) | 128 of 128 rules witnessed |

**The three failures predate H2.8c.** `test_store_probes::test_h2_4b_t1_p1[oxigraph-insert row first]`, `test_h2_4b_t2_p1[oxigraph]` and
`test_key_claims_and_audits::test_h2_5_t44[oxigraph]` fail on pyoxigraph 0.5.12, which the bootstrap now installs, on this branch with H2.8c's
changes stashed too. All three pass on 0.5.11. Recorded as TD-73, then resolved the same day at the maintainer's choice. TSD-01 and TSD-17
record 0.5.12, and the tests follow the installed version (the status record's log, 2026-10-20).

## Probes

| Probe | Result |
|---|---|
| A payload contract points at an edge its profile does not state | `dal:PayloadContractShape` reports it (the contract-shapes case) |
| `emit_contract` copies each edge onto the payload contract again, as before H2.8c | 7 tests fail (H2.6e-T13, the expected profiles, the new shape case), and the code was restored |
| The evidence warning ignores record classes | H2.8c-T8 fails, and the code was restored |
| `NoReceiptForRecord` disabled | H2.8c-T9 fails, and the witness check reports `UNWITNESSED warning:NoReceiptForRecord`, and the code was restored |
| The `members` form without the sub-select, on the same histories (4 seeds, a scratch run) | right on every seed, as FMH-H2-6g found, so the sweep guards correctness and T5 guards the form |

## Benchmark

`mise run check:persistence-membership`, 500 members, one replaced per version, checkpoint every 16, rdflib 7.6.0, pyoxigraph 0.5.12. Every member
set and stored count was right. The read of the current members of a delta family:

| Engine | Versions | Before (FMH-H2-6f) | After |
|---|---|---|---|
| rdflib | 100 | 98.6 s | 1.28 s |
| rdflib | 10 | | 0.21 s |
| Oxigraph | 100 | 1.7 s | 0.005 s |

Time never fails the check (ADR-A124). TD-68 is closed and removed from the register.

## What remains

- A source of what is a version that the library can read (TD-67).
- Three Oxigraph tests failed on pyoxigraph 0.5.12, before and after H2.8c (TD-73). Resolved after the slice, outside it.
- H2.9 retires the templates, including the `members` template this slice keeps equal to its builder.

## One command

```
mise run check:persistence
mise run check:persistence-oxigraph
mise run check:persistence-library
mise run check:persistence-membership
```
