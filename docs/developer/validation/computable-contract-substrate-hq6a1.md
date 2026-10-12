<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS HQ-6a.1, closures in Eligibility

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R. **Branch:** `ccs/hq6a1-closures-model`, in the worktree
`~/work/lattice-wt/ccs-hq6a1-closures-model`, examples first (ADR-A-C2, commit `5a6bbee1`)
**Plan:** [CCS plan](../plans/computable-contract-substrate.md), HQ-6a in detail
**Decisions:** HQ6a-Q1 (b), Q2 (a), Q3 (a), Q4 (2) and Q5 (b), answered 2026-10-10 to 2026-10-12.
[ADR-A105](../../architecture/decisions/ADR-A105-closure-declarations.md) and
[ADR-A103's 2026-10-12 addendum](../../architecture/decisions/ADR-A103-eligibility-set-readings.md),
both Proposed. NRS D7 (refuse)

## Invariant

Absence decides an outcome only under a declared closure, named by the binding that relies on it,
which states on whose authority. Without one, a set reading decides only what a record proves:
`elg:SomeValue` Permitted, `elg:EveryValue` Denied. Under a closure in force, some value is Denied
when every value is Denied and every value Permitted when every value is Permitted, the empty case
included (L15 as restated). A closure is in force from its source's effective time and licenses the
records as they stood at the deciding record's recording time (L17). A closure never changes a
single-value reading. Nothing here touches Persistence or a period of time.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| HQ6a1-01 | a closure with one source, none, two / Eligibility's shapes / conforms, reported, reported | L1 | + − |
| HQ6a1-02 | a binding naming a closure, read some value, every value, single value, with no reading / shapes / conform, conform, reported, reported | L1 | + − |
| HQ6a1-03 | a binding naming a node that is not a closure / shapes / reported | L1 | − |
| HQ6a1-04 to 06 | the admissions example, with its registry's closure and with it removed / the reference evaluator / the example's two tables: ada and ben Undetermined without it, cai Denied and Permitted with it | L2 | + − |
| HQ6a1-07 | the trial example, every value, with and without the protocol's closure / the reference evaluator / Permitted only with it, a recorded excluded diagnosis Denied either way | L2 | + − |
| HQ6a1-08 | a closure whose source takes effect after the decision / the reference evaluator, before and after / Undetermined, then Permitted (L17) | L2 | − + |
| HQ6a1-09 | the facility's objections register, the licence's usage reports and the reinsurance claims file, with and without their closures / the reference evaluator / each example's table | L2 | + − |
| HQ6a1-10 | the five examples / Eligibility's shapes, and every layer's shapes through the example and Instrument suites / conform | L3 | + |
| HQ6a1-11 | a decision relying on its binding's closure, and on another / shapes / conforms, reported | L1 | + − |
| HQ6a1-12 | the reference semantics / `check:reference-eligibility` / L15 as restated and L17 hold over every list up to length 3, closed and open, and the 30 adequacy rows | L2 | + |
| HQ6a1-13 | the Isabelle session / `check:proofs -- eligibility` / every claim proved, the assumption audit clean, every digest current | L2 | + |
| HQ6a1-14 | Eligibility's README / literate `--check` (in `test_eligibility_examples.py`), `check:formal-freshness` / consistent | L0 | + |
| HQ6a1-15 | the versions and cascade / `check:full-sweep` against `main` / pass | L0 | + |

## One command

```bash
mise run check:full-sweep && mise run check:proofs -- eligibility
```

The sweep runs `tools/test_closures.py` (rows 01 to 11) in `check:ontology-catalog`, the reference
semantics (row 12), the formal-freshness gate and the literate check (row 14), and the versioning and
release register checks (row 15). `check:proofs` is native and manual, so it is the second command.

## Artefacts to inspect

- [ADR-A105](../../architecture/decisions/ADR-A105-closure-declarations.md) and ADR-A103's addendum
- `ontology/eligibility/README.md` §5.6 (closures), §6.1 (readings), §6.4 (L15, L17), §7 (shapes),
  §10 (Formalisation), §11 (release notes)
- `tools/proofs/eligibility/Eligibility.thy`, `Adequacy.thy` and `claims/`
- `tools/reference/eligibility/src/reference_eligibility/kernel.py` and `denotation.py`
- the five examples: `set-reading-admissions.ttl`, `set-reading-trial.ttl`, `closure-usage-reports.ttl`,
  `facility-requests.ttl`, `reinsurance-claims-cooperation.ttl`
- `tools/test_closures.py`

## Deliberate non-coverage

- **The compilers** keep ADR-A103's original reading of set readings until HQ-6a.2, which applies
  closures, the refusal (`exe:NoClosureLicence`) and the decision's relied-on closures. So
  `test_legal_acts.py` still expects the compiled claim 2 to be Undetermined, with a comment.
- **Closures over a period**, their anchors, the deemed-failure example, the trial placeholder in
  `trial-definitions.ttl`, supersession by a late fact, deemings' precedence and purpose, business
  days, and a closure's binding to the store: HQ-6b.
- **Set comparisons** over closures: C9b3.

## Handoff

**Built** (on the branch, uncommitted, after the examples commit `5a6bbee1`):

- ADR-A105, Proposed, and ADR-A103's addendum, Proposed. The ADR catalogue lists both.
- Eligibility's README: §5.6 Closures with `elg:Closure`, `elg:licensedBy`, `elg:closedUnder` and
  `elg:closureReliedOn`, the readings and L15 restated, L17, three shapes and two properties on
  existing shapes, and the release notes. Its seven files regenerated, the kernel files unchanged.
- Isabelle: `some_value` and `every_value` take whether the binding is closed. TL1-some, TL1-every,
  TL2, TL3a, TL3b, TL4a and TL4b restated and proved, `Adequacy.thy`'s rows doubled, closed and open.
- The reference semantics: `some_value` and `every_value` take `closed`, `decide_condition` passes
  it, the kernel and denotation tests restated, and new tests of both admissions tables.
- `tools/test_closures.py`, registered in `check:ontology-catalog`. `closure-usage-reports` joins
  `test_eligibility_examples.py`'s examples.
- Versions: Eligibility 0.12.0, `eligibility-vocab` 0.13.0 and Eligibility's shapes 0.3.0, each
  breaking. The cascade, computed from the import graph: Behaviour, `behaviour-runtime` and
  `behaviour-vocab` 0.15.0, Instrument, `instrument-acts` and `instrument-vocab` 0.17.0, Wording and
  `wording-vocab` 0.9.0, and the capacity execution profile 0.15.0, each with a release note. The
  catalog and release register regenerated.

**Deviations from the plan:**

- **All 13 proof claims re-digested, not three.** A claim's digest covers every definition in the
  session (E1.4), so changing `some_value` and `every_value` changes every claim's digest. Each was
  re-proved before its digest was refreshed. TL2, TL3a and TL3b are restated too, since the readings
  take the closure. AQ's description now reads 30 lemmas.
- **The reference test count fell from 66 to 58.** The 15 adequacy tests became two table-driven
  tests over the 30 rows, and three closure tests and two TL4 tests were added.
- **No coupling with the differential tests.** They read candidates directly with a single-value
  reading, so the reference's new set readings could not disagree with the compilers there.

**What to check first:** §5.6 and L15's new wording in the README, then `Eligibility.thy`'s two
definitions and TL1 statements, then the five examples' tables against `test_closures.py`.

## Results

| ID | Result |
|---|---|
| HQ6a1-01 to 11 | 20 tests in `tools/test_closures.py`, all pass |
| HQ6a1-10 | also `test_eligibility_examples.py`, with `closure-usage-reports` added: pass |
| HQ6a1-12 | `check:reference-eligibility`: 58 passed |
| HQ6a1-13 | `check:proofs -- eligibility`: Eligibility session built, 13 claims passed, audit clean, gate pass |
| HQ6a1-14 | literate check consistent (7 artefacts), `check:formal-freshness` consistent |
| HQ6a1-15 | `check:full-sweep` against `main`: all 14 checks passed, `check:ontology-catalog` 750 passed |
