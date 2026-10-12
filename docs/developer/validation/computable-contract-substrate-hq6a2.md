<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: CCS HQ-6a.2, closures in the compilers

**Unit:** [`computable-contract-substrate`](../status/computable-contract-substrate.md)
**Machine:** R. **Branch:** `ccs/hq6a2-closures-compilers`, examples first (ADR-A-C2, commit `0869d43b`)
**Plan:** [CCS plan](../plans/computable-contract-substrate.md), "What HQ-6a.2 builds"
**Decisions:** HQ6a2-Q1 (1), Q2 (i) and Q3, answered 2026-10-12.
[ADR-A105](../../architecture/decisions/ADR-A105-closure-declarations.md) and its 2026-10-12 addendum

## Invariant

The compilers decide as the reference semantics does (HQ-6a.1). A set reading decides on
completeness, `elg:SomeValue` Denied and `elg:EveryValue` Permitted, the empty case included, only
when its binding names a closure in force at the resolution instant. Without one, such an outcome
is Undetermined with `exe:NoClosureLicence`, or the diagnostic of an undetermined value, or
`exe:MissingCandidate` for no value. A binding naming something that is not a closure, or a closure
with no source, is refused at compile time. A SPARQL row names the closure exactly when
completeness decided it, before negation, and a profile row names the union of its conditions'
closures. The compilers mint no decision records. SWRL and OWL output is unchanged.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| HQ6a2-01 | `SomeValue` over the readings fixture, open and closed / SPARQL / open decides only a Permitted value, closed Denies every value Denied, the empty case included | L2 | + − |
| HQ6a2-02 | `EveryValue`, open and closed / SPARQL / open decides only a Denied value, closed Permits every value Permitted, the empty case included | L2 | + − |
| HQ6a2-03 | a subject with no value / SPARQL, under a closure / Denied under some value, Permitted under every value, no diagnostic | L2 | + |
| HQ6a2-04 | the admissions, trial, usage, facility and reinsurance examples, with and without their closures / SPARQL, and the compiled reinsurance claims in `test_legal_acts.py` / each example's two tables, as the reference gives them (HQ6a1-04 to 09) | L2 | + − |
| HQ6a2-05 | the same examples / SHACL / agrees with SPARQL on every subject, with and without the closure | L2 | + − |
| HQ6a2-06 | the admissions conditions / SPARQL's `?closure` / named only where completeness decided, before negation | L2 | + − |
| HQ6a2-07 | a binding naming a node that is not a closure, and a closure with no source / compile / refused, `exe:NoClosureLicence` | L1 | − |
| HQ6a2-08 | the admissions profile / SPARQL's `?closures` / ada, ben and cai name the registry's closure, dee none (HQ6a2-Q2 (i)) | L2 | + − |
| HQ6a2-09 | the reference semantics / `decide_condition_with_reliance` / the admissions reliance table, and no reliance without a closure (HQ6a2-Q3) | L2 | + − |
| HQ6a2-10 | SWRL and OWL / set readings and negation / still refused | L1 | − |
| HQ6a2-11 | Executable 0.7.0 / versioning, catalog, release register, `build:mtp` and `check:mtp`, `check:full-sweep` / pass | L0 | + |

## One command

```bash
mise run check:full-sweep
```

The sweep runs `check:mork-compilers` (rows 01 to 08 and 10, in `test_set_readings.py` and
`test_closure_readings.py`), `check:reference-eligibility` (row 09), `check:ontology-catalog` with
`test_legal_acts.py` (row 04's compiled claims), and `build:mtp`, `check:mtp` and the versioning
checks (row 11). The 15 example tests red before the model phase are the first to look at:

```bash
mise exec -- python -m pytest tools/mork_compilers/src/mork_compilers/test_closure_readings.py tools/mork_compilers/src/mork_compilers/test_set_readings.py tools/reference/eligibility/tests/test_denotation.py tools/test_legal_acts.py -q
```

## Artefacts to inspect

- `ontology/mork/spec/Executable.ttl`: `exe:NoClosureLicence`, version 0.7.0
- `tools/mork_compilers/src/mork_compilers/eligibility_ir.py`: `EvidencePath.closure` and `_closure`
- `tools/mork_compilers/src/mork_compilers/sparql_backend.py`: the module docstring's `?closure`
  contract, `_read_set`, `_negate` and `profile_select`
- `tools/reference/eligibility/src/reference_eligibility/denotation.py`: `decide_condition_with_reliance`
- `tools/mork_compilers/src/mork_compilers/test_closure_readings.py`: `sparql_profile`
- `ontology/catalog-v001.xml` and `docs/architecture/ontology-releases.md`

## Deliberate non-coverage

- **Minting the decision record**, its cut and identity, and copying `?closure` into
  `elg:closureReliedOn`: C12.
- **SHACL reliance.** SHACL reports violations only, so it agrees on decisions and names no closure
  (HQ6a2-Q1).
- **The differential harness** does not yet check the `?closure` column. It reads single-value
  readings only, and takes reliance up when it covers bound conditions (track B).
- **Closures over a period**, anchors, supersession by a late fact and a closure's binding to the
  store: HQ-6b. Set comparisons over closures: C9b3.

## Handoff

**Built** (commit `349ccfa2`, after the examples commit `0869d43b`, then fixed at verification as below):

- Executable 0.7.0 with `exe:NoClosureLicence`. Only the catalog imports Executable, so there is
  no cascade. The catalog and release register regenerated, adding only Executable's rows.
- The IR: an evidence path carries its binding's closure. A binding naming a non-closure, or a
  closure with no `elg:licensedBy`, is refused. A closure on a single-value reading is ignored. A
  closure whose source states `fnd:validFrom` is in force only from it, and compiling then needs
  an explicit resolution instant. `namespaces.py` gains `FND`.
- SPARQL: every condition query projects `?closure`. `_read_set` decides on completeness only under
  a closure, counts a subject's `exe:MissingCandidate` row as no value, and reports
  `exe:NoClosureLicence` when an open binding cannot decide. Negation carries the column. Profile
  rows project `?closures`, the space-separated union.
- SHACL: unchanged in code. Its decided shapes wrap the SPARQL backend's condition select, so they
  take up closures with it.
- The reference: `decide_condition_with_reliance`, with `decide_condition` now delegating to it,
  its behaviour unchanged. The package README names it.
- `test_closure_readings.py`: HQ6a2-08 reads `?closures` through a new `sparql_profile` helper,
  comparing sets. Its expected closures are unchanged.

**Deviations from the plan:**

- **`build:mtp` moves no pins.** The MTP pins hash MORK's own terms (`Mork.ttl`), and Executable
  is not among them. The build reported the pinned graph hash unchanged, and `pins.lock.json` did
  not change.
- **No SHACL backend change**, for the reason above.
- **Three fixes found at verification**, after the maintainer accepted `349ccfa2`:
  - `profile_select` had an unterminated string, so `sparql_backend.py` did not import. The quote
    is corrected.
  - AIR32-08 (`test_set_readings.py`, an interval read `EveryValue`) still expected an open binding
    with every value Permitted to be Permitted, which L15 as restated (ADR-A105, HQ6a1-07) makes
    Undetermined. Its binding now names a closure, as the examples phase did for the other
    AIR-3.2 tests, so its expected outcomes stand, and a second assertion checks the open reading:
    Undetermined, with a Denied value still Denied. This strengthens the test. It is listed here
    under the non-weakening rule for the maintainer to countersign.
  - `test_concept_backends.py` pins the set of declared diagnostics. `exe:NoClosureLicence` joins it.

**What to check first:** `_read_set`'s decision and diagnostic expressions in `sparql_backend.py`,
then `_closure` in `eligibility_ir.py`, then the module docstring's statement of the `?closure`
contract against ADR-A105's addendum.

**Checked while writing the pack.** `_read_set` treats every per-value Undetermined row with
`exe:MissingCandidate` as "no value". That is sound for both plan kinds. Grouped per value, a
present value always counts one candidate, so the diagnostic arises only for a subject with no
value. A present interval value that cannot be read reports `exe:ValueSpaceMismatch` and stays
undetermined under a closure.

## Results

| ID | Result |
|---|---|
| HQ6a2-01 to 08, 10 | `check:mork-compilers`: 126 passed, including `test_closure_readings.py` and `test_set_readings.py` (16) |
| HQ6a2-04 | also `test_legal_acts.py`, in `check:ontology-catalog`: pass |
| HQ6a2-09 | `check:reference-eligibility`: 60 passed |
| HQ6a2-11 | `check:full-sweep` against `main`: all 14 checks passed, `check:ontology-catalog` 750 passed, `build:mtp` and `check:mtp` pass |

The 15 tests red after the examples phase pass. The first sweep found two failures, the stale
AIR32-08 expectation and the pinned diagnostic set, fixed as above, and a versions check that
could not run because the clone had no local `main`. The second sweep passed.

## Adversarial probes

Our pick, as the maintainer asked us to complete the slice autonomously (2026-10-12). Each broke
one file, ran the tests that guard it, and restored the file from a copy, after which the same
tests passed again (50 passed).

| Artefact | Defect introduced | Caught by |
|---|---|---|
| SPARQL `_read_set` | every binding read as closed | 5 fail: HQ6a2-04's open tables, HQ6a2-01, 02 and 03's open cases, AIR32-08's open case |
| IR `_closure` | a closure with no source accepted | 1 fails: HQ6a2-07's no-source case |
| SPARQL `profile_select` | a profile row drops its conditions' closures | 1 fails: HQ6a2-08 |
| reference `decide_condition_with_reliance` | reliance decided after negation | 1 fails: `TestReliance`'s admissions table |

A first probe of the reference, reliance reported without a closure, survived. It is an equivalent
mutant: an open `SomeValue` reading is never Denied and an open `EveryValue` never Permitted, so
the `closed` guard on reliance is redundant, and removing it changes no outcome. We kept the guard,
since it states the rule, and replaced the probe with the one above.

## Acceptance

Accepted by the maintainer on 2026-10-12 (commit `349ccfa2`), with the three verification fixes and
the probes above recorded after. The maintainer's merge into `main` is the sign-off.
