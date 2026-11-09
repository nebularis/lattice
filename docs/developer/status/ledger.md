<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Ledger — Status

**Unit ID:** `ledger`
**Status:** built 2026-11-09. LG-0 and LG-1 built, verified and committed. LG-5 part built ahead of its dependency. LG-7, LG-2 and LG-8 built.
**Last updated:** 2026-11-08
**Plan:** [ledger.md](../plans/ledger.md)
**Validation Packs:** [LG-0](../validation/LG-0.md), [LG-1](../validation/LG-1.md), [LG-7](../validation/LG-7.md), [LG-2](../validation/LG-2.md)

---

## Is this unit complete?

**No.** LG-0 (examples first) and LG-1 (the configuration document) are built, verified and committed. LG-8 (the proofs widened on HOL-Library) is built on machine S and committed locally on `fm/prelude-and-ledger-proofs`, waiting for the maintainer's verification, without LM1, which waits on LG-Q11. LG-7 (the laws mechanised) and LG-2 (the runtime document) are built on machine S and committed locally, waiting for the maintainer's verification. LG-5 (benchmark) is part built, ahead of the LG-4 it depends on. LG-3 (Behaviour's migration) and LG-4 (allocation) are not briefed.

## Current state

**2026-10-27.** Everything the 2026-10-22 entry below listed as blocking is done. The release tags exist, ADR-A131 was published 2026-10-26, `check:published-decisions` passes, and the `bootstrap` failure that stopped LG0-01 being machine-run is gone. That entry is kept as the record of how LG-0 and LG-1 were built, and is no longer the current state.

Since then the work has been design rather than build, and it has answered the whole runtime question set.

**The runtime model, decided 2026-10-27 by the maintainer** (history sketch §7). A posting carries a running balance along the recorded ordering, with checkpoints at closings (LF-Q17 b). Two orderings, recorded and effective (LF-Q11). Post at the drawn account only and derive ancestors, with declared exceptions for purpose-counting accounts (LF-Q18 c). An account instance gains a minted IRI, **reversing ADR-A131 decision 4** (LF-Q19 a). Closing recurrence sits on the account definition (LF-Q20 a). A speculative pass goes in a droppable named graph (LF-Q21 a). A maximum magnitude per value space, in Quantification (LF-Q22 a).

**The storage shape, decided and measured.** A graph per account partition per closing period, where the partitioned unit is the account's book for one period and is itself an aggregate root, so the graph IRI template keeps one slot and whole-graph replace keeps its meaning ([ADR-A13](../../architecture/decisions/ADR-A13-dataset-graph-role-model.md) addendum, STD-276, MS-Q2). A role is declared once per graph family rather than per graph. The checkpoint IRI derives from the account and the close position (MS-Q8 d, TSD-36). A checkpoint is written only where the balance moved, with a carry-forward (MS-Q6 a). A sealed book is registrable and its content hash is the archive digest ([ADR-A34](../../architecture/decisions/ADR-A34-surface-graph-family-registry-and-immutable-identity.md) addendum), which closed the digest question the multi-store sketch §5.3 left open. §5.2 of the history sketch now carries all of this.

**Measured** in [ledger-posting-cost](../../../benchmark/ledger-posting-cost/README.md) and [ledger-store-comparison](../../../benchmark/ledger-store-comparison/README.md), with CAP-84 and CAP-85 ratified and reviewed in [the benchmark review](../review/ledger-benchmarks-cap-84-cap-85-review.md). The partition removes the scan floor and the read goes flat, 0.40 to 0.54 ms over a hundredfold history where one graph grows to 217.53 ms (MS-Q1 a). The shape replicates on Jena TDB2, so it is a property of naming the graphs rather than of one engine. The partition can be fine: 13,082 graphs with no read ceiling, so **storage bounds the partition, not the engine** (MS-Q9 a).

**One measured result runs against the design and is unexplained.** On TDB2 the partition makes writing cost 1.32 s against 0.63 s at 20,000 events, where on Oxigraph the two were within noise. Checkpoints are most of the extra quads. Anything write-heavy leaning on the partition should measure this first.

**Merged main at `0fb8170b`, release 0.20.0, on 2026-10-29.** Two of the ledger's rows moved first, since main's rows of the same number are earlier (ADR-A133 addendum). STD-279 became STD-294 and TD-94 became TD-126. Four of main's rows moved the other way, since the ledger's are the earlier ones, STD-276 to STD-278 of 2026-10-27 10:53 against the computable contract substrate's of 16:34, and TD-93 of 11:23 against 16:34. Main's "name the deferral", "facts, meaning and findings apart" and "a place for implied terms" became STD-295 to STD-297, with their citations in ADR-A145, the substrate's plan and status, TD-100 and `test_extract.py`, and main's "the technical debt register carries no facets" became TD-129. The knowledge index code was taken from main whole, which carries the section mechanism this branch built as decision 29 of ADR-A134, so the branch's ADR-A134 addendum of 2026-10-27 was dropped and its measurement is recorded here instead, 430 numbered items and 68 addenda gave 498 sections, and ADR-A122 came back at 0.82 pointing at its decision 8 where before it was not returned. TD-92 was paid on main by ADR-A145, so its row and this branch's citation of it in the discovery record are gone. The three guidance bullets this branch added to `AGENTS.md`, on reading output in full, asking the index before searching, and asking for the reason, were re-applied over main's text. `tools/knowledge/identifier-exceptions.txt` no longer lists STD-280.

## What is open

| | What | Owner |
|---|---|---|
| PDD-15 | **decided (a), 2026-10-28.** A periodic amount becomes one account per period, keyed by the recurrence bin the effective position falls in, with no reset credit. Three rules came with it: the period key is derived at write and never supplied by a draw, one period recurrence holds along a path with a keyed child part of its parent's instance under the same bin key, and a draw whose effective position cannot be binned is Undetermined. LG-2 built the first two, with `ldg:periodRecurrence` beside a deprecated `ldg:resetRecurrence` rather than a rename | LG-3, and the evaluator for the third |
| the to-first-in-order rule | raised by LG-8. `ldg:ToFirstInOrder` can give a residual unit to a key of weight zero, past its bound, so it is lawful over whole units only on positive weights. Whether a shape refuses a zero-weight key under it, or largest remainder is the only residual rule for a proportional merge, is open | the maintainer, then LG-4 |
| LG-Q9, LG-Q10 | raised by LG-2 in the plan. Which balance a posting's running balance states under post-once (LF-Q17 is answered (b) and not yet built), and how a pool that caps an aggregate's reinstatements is built now that a credit rolls up | the maintainer |
| the restatement read's partition | PDD-15's claim that an old period's later books hold only stragglers holds where the partition root is the keyed instance, which the benchmark does not yet partition by. The next measurement, not a blocker | benchmark |
| MS-Q4 | **answered (a)**, with no persistence addendum owed. A scratch dataset is a dataset, so the restore is an ordinary whole-dataset one of a small dataset and `dal:EpochProfile` needs no change | closed |
| MS-Q11 and LF-Q21 | **both answered**, and they never competed. Evaluation before commitment is a lifecycle boundary LATTICE does not implement, and a droppable graph governs evaluation against committed record | closed |
| PDD-12 | **closed**, on a position-derived name for a period's unit, measured flat across a change of recurrence | closed |
| PDD-14 | **closed**, on STD-278. The correctness-path read is the flat one, since an effective position selects the account and that account's balance now decides the amount | closed |
| PDD-08 | **split**, not owned. Combinators to a Quantification slice before C7b, the log's grain into LG-2, a Datalog backend to PDD-13 | split |
| MS-Q3, MS-Q5, MS-Q7, MS-Q10 | **all answered (a)**, 2026-10-27. MS-Q3 gained the rule that a retention declaration states a horizon for a registration too, never shorter than its book's | persistence |
| TD-95 | **the form is settled, the debt stays.** Conservation states recoveries plus residual equal the amount drawn, with the residual explicit, which an external Isabelle development proves claim by claim for every well-formed contract list and every allocator satisfying the axioms ([sketch](../sketches/waterfall-proofs-and-the-generality-gap.md) §5.1). Open until LG-4 writes the shape | LG-4 |
| the allocation axioms | **four, not five.** Exactness, boundedness by each part's own amount, non-negativity, and allocating the whole returns the whole. Zero at zero follows. **Monotonicity is dropped**, since no law in that development needed it, and LG-4 adds it back only by naming the law that needs it | LG-4 |
| WPG-Q2 | **open, leaning (a).** Where the declared ceiling lives: on `ldg:AccountDefinition` as a per-account availability bound, on the draw term, or in Quantification beside LF-Q22(a)'s maximum magnitude per value space. The bound is a property of the account, and LF-Q22's is about a value space, so the two are different things that happen to be upper bounds | the maintainer, then LG-4 |
| the `owl:rational` probe | **done by LG-2**, TSD-70. rdflib, Oxigraph and Jena keep the literal and none compares it by value, so a proportion is two integers. ES-5 can rely on the finding | closed |

**Next action:** the maintainer's verification of LG-7 and LG-2 from their packs, and LG-Q9 and LG-Q10. Then LG-3, Behaviour's migration. The README's narrative and exemplar expansion is requested and not started, and no longer waits on LG-2.

## 2026-11-09, LG-8 built

On machine S, branch `fm/prelude-and-ledger-proofs`, committed locally, [its pack](../validation/LG-8.md). The session parents on track E's prelude, LO1 holds over multisets, LC3 bounds every step, and LR3 to LR5 prove `ldg:LargestRemainder`, both integer rules lawful over whole units, and the rounded split of an amount across accounts against the exact one, each a gated claim. LM1 is not built, since LG-Q11 is open. Three findings for the maintainer. `ldg:ToFirstInOrder` is lawful only on positive weights, since it can give a residual unit to a key of weight zero, so LR4 states it under that hypothesis and largest remainder carries the integer spread. Rounding moves amounts between keys and never between accounts, so the rounded balances equal the exact ones rather than lying within a unit per posting. Per key, the two splits are compared at one part only.

## 2026-11-09, LG-8 marked building

On machine S, branch `fm/prelude-and-ledger-proofs`, per the [machine S brief](../notes/machine-s-brief-2026-11-08.md), after track E's FME-0 built the prelude the session parents on. LG-Q14 is decided (d) and LG-Q11 is open, so LM1 is left out.

## 2026-10-22, LG-1 built and verified

**Historical.** Kept as the record of how LG-1 was built. Its two 🔴 items are both discharged: the release tags exist and `check:published-decisions` passes, since ADR-A131 was published 2026-10-26. Read it for what was done, not for what is outstanding.

Built on `docs/placement-vehicles-structure`, same session convention as LG-0 (one branch, one
bundle). Full detail in the [LG-1 Validation Pack](../validation/LG-1.md)'s Handoff and
Results sections. In short:

- `ontology/ledger/README.md` written in ADR-A126's layout and extracted: `spec/ledger.ttl`,
  `vocab/ledger-vocab.ttl`, `shapes/structural.ttl`, `shapes/constraints.ttl` (six SHACL-SPARQL
  constraints). Registered in the root catalogue after `quantification`, in the ontology
  architecture document and the root README. `tools/test_ledger.py` added to
  `check:ontology-catalog`'s list (13 tests, all passing).
- **The substrate release moved to 0.19.0.** Ledger joining the release changes every member's
  version IRI under ADR-A129's one-release model, which cascaded into five applied modules that pin
  the substrate (each bumped one MINOR of their own, per ADR-A86's re-pinned-import rule, with their
  test files' hardcoded version strings updated to match): `applied/capacity` 0.17.0,
  `applied/classification` 0.4.0, `insurance/common` 0.8.0, `insurance/exposure` 0.3.0,
  `insurance/peril` 0.7.0. Release-notes lines added to every affected README that has one.
- **🔴 RELEASE TAGS REQUIRED**, once this is merged (`mise run build:ontology-releases` already lists
  them; repeated here per the lifecycle skill):
  ```
  git tag applied-capacity-execution-v0.16.0 applied-capacity-execution-v0.17.0 applied-classification-v0.3.0 applied-classification-v0.4.0 applied-classification-vocab-v0.3.0 applied-classification-vocab-v0.4.0 insurance-common-v0.7.0 insurance-common-v0.8.0 insurance-common-vocab-v0.7.0 insurance-common-vocab-v0.8.0 insurance-exposure-v0.2.0 insurance-exposure-v0.3.0 insurance-exposure-vocab-v0.2.0 insurance-exposure-vocab-v0.3.0 insurance-peril-v0.6.0 insurance-peril-v0.7.0 insurance-peril-intensity-v0.6.0 insurance-peril-intensity-v0.7.0 insurance-peril-vocab-v0.6.0 insurance-peril-vocab-v0.7.0 ontologies-v0.18.0 ontologies-v0.19.0
  ```
  (most of these pre-date this slice and were already pending; `ontologies-v0.19.0` and the
  `v0.17.0`/`v0.4.0`/`v0.8.0`/`v0.3.0`/`v0.7.0` members are new here.)
- **🔴 `check:published-decisions` cannot go green without the maintainer.** Ledger's README and
  `shapes/constraints.ttl` cite ADR-A131 throughout, since the whole document describes that
  decision, which is Accepted but not Published. Publishing is the maintainer's act (ADR-A127
  decision 1), the same as accepting. ADR-A01's 2026-10-19 addendum (also cited, also Accepted) has
  the same gate.
- Two small, low-risk fixes made to pass this environment's checks honestly rather than skip them:
  `tools/import_guard.py`'s violation renderer now prints `Path.as_posix()` (was bare `Path`,
  backslash-separated on Windows, failing five of its own test's fixtures), and
  `tools/test_import_guard.py`'s diagram-order check now reads `ontology-architecture.md` with
  `encoding="utf-8"` explicitly (was defaulting to the Windows locale codec).
- Three LG-0 refusal fixtures gained a missing `qnt:Difference` capability so each isolates exactly
  the one shape it is meant to test (see LG-1 Validation Pack for which).
- A real scaling limit found, not a defect: rdflib's SPARQL property-path evaluator recurses past
  Python's call stack on a 10,000-deep `ldg:partOf+` chain. No real account tree is anywhere near
  that deep; LG1-09's test now uses a shallow, wide tree instead, which is also the shape real trees
  have.
- `check:full-sweep`'s other failures (`build:mtp`/`check:mtp`, `check:persistence`,
  `check:agent-guidance`, and one flaky `reasoning_server` timing test) are pre-existing and
  unrelated, each confirmed in isolation. `check:site-sections` failed once (my edit to
  `eligibility/README.md` left its site copy stale) and is fixed (`build:site-sections` run).

## Board

| Slice | Deliverable | State | Blocked on |
|---|---|---|---|
| LG-0 | examples, as data the model must accept or refuse, from licensing, lending and grants | merged 2026-10-27, built 2026-10-27 |  |
| LG-1 | the configuration document, the README in ADR-A126's layout with account definitions, the tree, owner kinds and the merge rule scheme | merged 2026-10-27, built 2026-10-27 |  |
| LG-2 | the runtime document, postings, balance records, their keys and PROV, the two phases at one position | built 2026-11-08, building 2026-11-08, built 2026-11-08, building 2026-11-08, briefed 2026-10-27 |  |
| LG-3 | Behaviour's migration, the import, effects onto accounts, threshold regimes over a balance | planned | LG-2 |
| LG-4 | allocation with conservation, one amount split into postings by a merge rule, the conservation law as a shape | planned | LG-3 |
| LG-5 | a benchmark, a generated corpus of account trees and draws at the performance section's volumes, part built ahead of LG-4 | blocked | LG-4 |
| LG-6 | the fold investigation of the ledger-folds-and-stores sketch, probes P1 to P6, arms A, B, B0 and C, sharing LG-5's corpus | planned | LG-5 |
| LG-7 | the ledger laws mechanised in `tools/proofs/ledger/`, ahead of LG-2 | built 2026-11-08, building 2026-11-08 |  |
| LG-8 | the proofs widened on HOL-Library, LO1 over multisets, LR3 to LR5, LC3 for every step, LM1 | merged 2026-11-09, built 2026-11-09, building 2026-11-09 |  |
| LG-9 | the proofs' second widening, LR2 over multisets, an executable path, the running balance, a merge over whole units, and the parts that wait on LG-Q11, LG-Q12, LG-Q13, LG-Q15 and LG-Q16 | planned |  |
- 2026-11-09: LG-9 added and planned, the proofs' second widening, for machine S on one branch with a brief. The Results sections of LG-7, LG-2 and LG-8 record the maintainer's proofs run of the day and what is left to read. LG-Q15 and LG-Q16 raised from LG-8's first finding, in a sketch on the residual to the first in order. The prelude's double build on a first run is fixed in `tools/proofs/check.py`, and LG-8's row reads merged.
- 2026-11-08: LG-2 handed back at built, the scale tests under benchmark, the LG-1 constraints class-targeted and the ledger_corpus package, squash-merged into `main` with the substrate at 0.21.1. Its verification and LG-Q9's rework are still to come.
- 2026-11-08: LG-Q14 decided (d) by the maintainer, a prelude session every layer session parents on, track E's FME-0, after the HOL sessions survey. LG-8 parents on it.
- 2026-11-08: LG-8 added and planned, the proofs widened on HOL-Library, after the library built on machine R under a memory limit. LG-Q14 raised in the plan, how the session reaches the library, leaning a `sessions` clause that loads the theories from source so no other machine needs the heap. Plan only, nothing under `tools/proofs/` changed.
- 2026-11-08: LG-2 picked up again on `docs/placement-vehicles-structure`, on the maintainer's approval of how the suite's findings are handled: the two 10,000-definition scale tests move under `benchmark/ledger-posting-cost/` with small correctness versions left in `tools/test_ledger.py` (STD-155, PRI-65), the six LG-1 constraints are retargeted at the class as the runtime shapes are (TSD-23), the cycle test's narrowing stands, and TD-158 is folded into the rework LG-Q9 decides.
- 2026-11-08: built, with no slice of its own, the speed of `tools/test_ledger.py` and the release of the on-disk Oxigraph store before its temporary folder is removed in `benchmark/ledger-posting-cost/`, where on Windows the deletion error replaced the expected one. The suite went from 57 s to 41 s without parallelism (the median of three runs each on one machine), by running LG1-09 on the cycle shape alone and thirteen of the sixteen runtime shapes of LG2-10 on Oxigraph. The other three stay with pySHACL, two because they find nothing on Oxigraph (TD-158) and one because it costs 38.7 s there (TD-159). Every store is now let go before its folder goes, and a probe in the benchmark tests makes an open store fail the removal on any platform.
- 2026-11-08: LG-2 built on machine S, with its [Validation Pack](../validation/LG-2.md)'s handoff. The runtime document `spec/ledger-runtime.ttl`, sixteen runtime laws in `shapes/runtime.ttl`, the examples carrying their records, `licence-seats.ttl` under PDD-15, and TSD-70 from the `owl:rational` probe, so an exact share is two integers. `tools/test_ledger.py` passes 35 tests, and LG2-10's pass of 5,000 postings and 10,000 balance records validates in 56.6 s. TD-97 and TD-98 paid. LG-Q9 (the running balance under post-once) and LG-Q10 (a reinstatement under a capacity pool) raised in the plan. Versions not bumped, as `check:ontology-versioning` reports.
- 2026-11-08: LG-2 picked up on machine S, after LG-7, under the same go-ahead. This mark was committed after the README's first runtime edits rather than before them, a lapse the pack's handoff records.
- 2026-11-08: LG-7 built on machine S, with its [Validation Pack](../validation/LG-7.md)'s handoff. Section 10 of the ledger README states the definitions, `tools/proofs/ledger/` proves sixteen claims under the gate, LA1 to LA4, LC1 to LC4, LD1 to LD4, LO1, LR1, LR2 and LN1, and `check:proofs -- ledger`, `check:formal-freshness` and `check:ontology-versioning -- --base-ref main` pass. Two adversarial probes failed as they should, a credit with no ceiling at LD3 and a weakened LN1 at the gate's digest. WPG-Q1 answered 2026-11-08, (a) holds, in a scratch session that was not kept. `ldg:LargestRemainder` is not proved, and RE-Q4 leans to it.
- 2026-11-08: LG-7 picked up on machine S, on the maintainer's go-ahead to build LG-7 and then the next ledger slice autonomously, committing locally and never pushing.
- 2026-11-07: WPG-Q4 answered by the maintainer, (b) for the general core and (a) for the reinsurance instance, recorded in the [waterfall proofs sketch](../sketches/waterfall-proofs-and-the-generality-gap.md) and promoted to ADR-A-FM2's addendum of the same day. LG-7 is the first slice under it. No slice changed state.
- 2026-11-07: LG-7 added and briefed, the ledger laws mechanised in `tools/proofs/ledger/` ahead of LG-2, with its [Validation Pack](../validation/LG-7.md). The maintainer decided the same day that it runs before LG-2 on a machine they assign, that it builds on the domain-neutral core of the external development the waterfall proofs sketch reads, renamed and re-proved under the terms the plan states, and that the composition law stays with E4b. The plan's E4a row now says it started as LG-7. The row is planned, since this session is not the one that builds it.
- 2026-11-07: LG-4 briefed further and LG-Q6's probe widened, on `docs/placement-vehicles-structure`, from the [waterfall proofs sketch](../sketches/waterfall-proofs-and-the-generality-gap.md) §5.1. No slice changed state, since this was design on the plan rather than a slice picked up. Five things landed in LG-4. (1) Conservation with an explicit residual term as the form to take, which settles the open half of TD-95 in an instance. (2) The allocation axioms corrected from five to four, with monotonicity dropped because no law needed it, against a removed review note that listed five. (3) The merge rule as declared data with an identity and never a default, since two rules satisfying every axiom move different money on one arrangement, which makes LG-Q3's "refuse as the default" load-bearing. (4) Attribution across parties as a second conservation law with its own shape, shared with ES-5's K4. (5) The rule that nothing above the ledger may assume a balance is monotone in its input, since a franchise makes the residual fall as the input rises. LG-Q6's probe now covers Jena as well as rdflib and Oxigraph. WPG-Q2 raised, on where the declared ceiling lives.
- 2026-11-04: the board corrected on `docs/placement-vehicles-structure` (plan work-board, WB-7). LG-0 and LG-1 read merged, since `ontology/ledger/` reached `main` on 2026-10-27. LG-2 reads briefed, as this record said and against the row the adopt step took from its pack. LG-5 reads blocked on LG-4, with its part built ahead noted. LG-6, the fold investigation the ledger-folds-and-stores sketch adds after LG-5, has a row and leaves the identifier exceptions. The deliverables are the plan's.
