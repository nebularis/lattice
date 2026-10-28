<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Ledger — Status

**Unit ID:** `ledger`
**Status:** 🚧 LG-0 and LG-1 built, verified and committed. LG-5 part built ahead of its dependency. LG-2 unblocked, briefed and not started.
**Last updated:** 2026-10-28
**Plan:** [ledger.md](../plans/ledger.md)
**Validation Packs:** [LG-0](../validation/ledger-lg-0.md), [LG-1](../validation/ledger-lg-1.md)

---

## Is this unit complete?

**No.** LG-0 (examples first) and LG-1 (the configuration document) are built, verified and committed. LG-5 (benchmark) is part built, ahead of the LG-2 it depends on. LG-2 (runtime document) is briefed in the plan, unblocked, and not started. LG-3 (Behaviour's migration) and LG-4 (allocation) are not briefed.

## Current state

**2026-10-27.** Everything the 2026-10-22 entry below listed as blocking is done. The release tags exist, ADR-A131 was published 2026-10-26, `check:published-decisions` passes, and the `bootstrap` failure that stopped LG0-01 being machine-run is gone. That entry is kept as the record of how LG-0 and LG-1 were built, and is no longer the current state.

Since then the work has been design rather than build, and it has answered the whole runtime question set.

**The runtime model, decided 2026-10-27 by the maintainer** (history sketch §7). A posting carries a running balance along the recorded ordering, with checkpoints at closings (LF-Q17 b). Two orderings, recorded and effective (LF-Q11). Post at the drawn account only and derive ancestors, with declared exceptions for purpose-counting accounts (LF-Q18 c). An account instance gains a minted IRI, **reversing ADR-A131 decision 4** (LF-Q19 a). Closing recurrence sits on the account definition (LF-Q20 a). A speculative pass goes in a droppable named graph (LF-Q21 a). A maximum magnitude per value space, in Quantification (LF-Q22 a).

**The storage shape, decided and measured.** A graph per account partition per closing period, where the partitioned unit is the account's book for one period and is itself an aggregate root, so the graph IRI template keeps one slot and whole-graph replace keeps its meaning ([ADR-A13](../../architecture/decisions/ADR-A13-dataset-graph-role-model.md) addendum, STD-276, MS-Q2). A role is declared once per graph family rather than per graph. The checkpoint IRI derives from the account and the close position (MS-Q8 d, TSD-36). A checkpoint is written only where the balance moved, with a carry-forward (MS-Q6 a). A sealed book is registrable and its content hash is the archive digest ([ADR-A34](../../architecture/decisions/ADR-A34-surface-graph-family-registry-and-immutable-identity.md) addendum), which closed the digest question the multi-store sketch §5.3 left open. §5.2 of the history sketch now carries all of this.

**Measured** in [ledger-posting-cost](../../../benchmark/ledger-posting-cost/README.md) and [ledger-store-comparison](../../../benchmark/ledger-store-comparison/README.md), with CAP-84 and CAP-85 ratified and reviewed in [the benchmark review](../review/ledger-benchmarks-cap-84-cap-85-review.md). The partition removes the scan floor and the read goes flat, 0.40 to 0.54 ms over a hundredfold history where one graph grows to 217.53 ms (MS-Q1 a). The shape replicates on Jena TDB2, so it is a property of naming the graphs rather than of one engine. The partition can be fine: 13,082 graphs with no read ceiling, so **storage bounds the partition, not the engine** (MS-Q9 a).

**One measured result runs against the design and is unexplained.** On TDB2 the partition makes writing cost 1.32 s against 0.63 s at 20,000 events, where on Oxigraph the two were within noise. Checkpoints are most of the extra quads. Anything write-heavy leaning on the partition should measure this first.

## What is open

| | What | Owner |
|---|---|---|
| PDD-15 | **decided (a), 2026-10-28.** A periodic amount becomes one account per period, keyed by the recurrence bin the effective position falls in, with no reset credit. Three rules came with it: the period key is derived at write and never supplied by a draw, one period recurrence holds along a path with a keyed child part of its parent's instance under the same bin key, and a draw whose effective position cannot be binned is Undetermined. `ldg:resetRecurrence` is renamed, since nothing resets | LG-2 and LG-3 to build |
| TD-97, TD-98 | `licence-seats.ttl` models the reset the decision removes, and `ldg:keyDimension`'s OWL range is narrower than its prose and its shape. Both wait on the slice that implements PDD-15 rather than preceding it | LG-2 and LG-3 |
| the restatement read's partition | PDD-15's claim that an old period's later books hold only stragglers holds where the partition root is the keyed instance, which the benchmark does not yet partition by. The next measurement, not a blocker | benchmark |
| MS-Q4 | **answered (a)**, with no persistence addendum owed. A scratch dataset is a dataset, so the restore is an ordinary whole-dataset one of a small dataset and `dal:EpochProfile` needs no change | closed |
| MS-Q11 and LF-Q21 | **both answered**, and they never competed. Evaluation before commitment is a lifecycle boundary LATTICE does not implement, and a droppable graph governs evaluation against committed record | closed |
| PDD-12 | **closed**, on a position-derived name for a period's unit, measured flat across a change of recurrence | closed |
| PDD-14 | **closed**, on STD-278. The correctness-path read is the flat one, since an effective position selects the account and that account's balance now decides the amount | closed |
| PDD-08 | **split**, not owned. Combinators to a Quantification slice before C7b, the log's grain into LG-2, a Datalog backend to PDD-13 | split |
| MS-Q3, MS-Q5, MS-Q7, MS-Q10 | **all answered (a)**, 2026-10-27. MS-Q3 gained the rule that a retention declaration states a horizon for a registration too, never shorter than its book's | persistence |

**Next action:** LG-2, briefed against PDD-15's derived period key rather than the reset it replaces, with LG-3 following for Behaviour's migration. The README's narrative and exemplar expansion is requested and not started, and now waits on LG-2 rather than on an open question.

## 2026-10-22, LG-1 built and verified

**Historical.** Kept as the record of how LG-1 was built. Its two 🔴 items are both discharged: the release tags exist and `check:published-decisions` passes, since ADR-A131 was published 2026-10-26. Read it for what was done, not for what is outstanding.

Built on `docs/placement-vehicles-structure`, same session convention as LG-0 (one branch, one
bundle). Full detail in the [LG-1 Validation Pack](../validation/ledger-lg-1.md)'s Handoff and
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
