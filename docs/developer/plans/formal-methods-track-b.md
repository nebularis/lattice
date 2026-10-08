<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Formal Methods, Track B: the reference semantics and the oracle

**Unit ID:** `formal-methods-track-b`
**Unit type:** Phase (Epic Decomposition Model, `copilot-instructions.md`)
**Epic:** [formal-methods](formal-methods.md)
**Sketch:** [formal-methods-track-b.md](../sketches/formal-methods-track-b.md)
**Status record:** [formal-methods-track-b.md](../status/formal-methods-track-b.md)
**Status:** B1, B2 and B3 done, 2026-10-07

## 1. Scope

The reference semantics and the oracle, for whichever slices are ready now (epic plan §3: "B1 and
B2, kept small," alongside the spike and CCS, with no CCS dependency). This plan covers **B1, B2
and B3** only. B4 (the evaluation-context reference, `DesignEnv`/`RunEnv`, CCS C12's conformance
kit) needs CCS's C12, which is not yet briefable (confirmed by reading `main` directly, sketch
§6) — it is named, not detailed, and gets its own phase document when that dependency clears, the
same rolling-wave discipline tracks C and E already use.

## 2. What this plan depends on, and what blocks it

| Dependency | State | Blocks |
|---|---|---|
| an ADR for track B's home and scope (epic plan §3's own dependency row) | **`ADR-A-FM3`, Accepted 2026-10-07** | nothing further |
| the Isabelle kernel (`tools/proofs/eligibility/`) | done (track E, E1.0/E1.1) | nothing — B1 ports its statements, doesn't wait on anything further from it |
| `tools/mork_compilers`' SPARQL and SHACL backends | exist, stable | nothing — B2 tests against what exists today |
| `tools/surface/src/surface/invalidation.py` (`RegenerationPlan`) | exists | nothing — B3's item wraps it in a property test |
| an RDF-to-MCN encoder | **does not exist anywhere in the repository** (`mcnio.NullTool.encode` returns `None`) | MCN's round-trip item — out of scope for this plan, recorded as a gap, not built here |
| MORK's join-semilattice claim | **deferred by the human's own call** (2026-10-07): the claim has always been questionable and is left for a later slice to state and confirm properly | out of scope for this plan, not pursued here |
| CCS's C12 | "waiting," several tranche-D slices away (confirmed on `main`, 2026-10-07) | B4 only, out of scope for this plan |

## 3. Slices

### B1: the kernel and Eligibility's denotation, in Python — done

- Drafted `ADR-A-FM3` (home `tools/reference/`, scope B1-B3, restating E1/E3), **Proposed**, not
  yet accepted by the human.
- `tools/reference/eligibility/kernel.py`: `or3`/`and3`/`neg3`/`decision_leq` ported from
  `tools/proofs/eligibility/KernelLaws.thy`, same names, same statements, docstring wording kept
  close enough to `ontology/eligibility/README.md` to align by inspection.
- `tools/reference/eligibility/denotation.py`: the single-candidate decision function (L9-L12,
  L14), `some_value`/`every_value` (L15, ported from `Eligibility.thy`), negation (L16, `neg3`
  applied to the combined outcome).
- **Validated**: every one of the Isabelle kernel's own `Adequacy.thy` fixture lemmas (the 15
  `MIXES`-derived cases) reproduced as Python unit tests, identical inputs and expected outcomes,
  plus exhaustive checks of TA1/TA2 over the full three-valued domain, bounded checks (lists up
  to length 3) of TL1-TL3b, and direct per-law tests of L9-L12/L14-L16 against a small
  hierarchy fixture — 47 tests, all passing. A seeded mutation (`neg3` broken to fix
  `Undetermined` to `Permitted`) was confirmed to fail six tests before being reverted, the
  "prove it can fail" check this criterion calls for.

### B2: differential tests against the existing compilers — done

- `tools/reference/eligibility/tests/test_differential.py`: evaluates `decide_concept_match`
  against `tools/mork_compilers`' compiled SPARQL (executed, not inspected as text) and SHACL
  (validated with pySHACL), reusing that package's own fixtures and test helpers (`DIAGNOSES`,
  `ENTITLEMENT`, `with_questions`, `sparql`, `shacl`) and one real Eligibility example
  (`ontology/eligibility/examples/flat-scheme-lending.ttl`), not duplicating them.
- The named negative fixture (epic plan's own B2 row): hierarchical match with exclusions under
  L11, checked directly (`solid-tumour-arm`'s required solid-tumour/excluded cns-tumour) and
  generalised across every member of the resolved scheme (`TestL11OverEveryMember`).
- "Not a value" first (sketch §3): a question with no candidate at all (`q-absent`/`absent`) and
  one with several candidates and no declared reading (`q-two`) both checked as Undetermined
  across all three implementations.
- **Validated**: 63 tests pass (47 from B1 plus 16 differential). **Found and fixed two real
  defects in B1's own `denotation.py`**, exactly what an independent oracle is for:
  (1) `decide_concept_match` never checked whether a candidate was a member of the resolved
  scheme at all (L9's "restricted to that scheme's members"), so a candidate entirely outside the
  scheme could be wrongly Denied instead of Undetermined; (2) `decide_condition`'s `SingleValue`
  reading took the first value regardless of count, instead of requiring exactly one (several
  candidates with no declared reading is ambiguous, `exe:SeveralCandidates`, Undetermined). Both
  fixes are in `denotation.py`, with regression tests in `test_denotation.py` and the differential
  harness itself. L14 (hierarchy precondition) checked against a real Eligibility example fixture
  (`flat-scheme-lending.ttl`), not a synthetic one, per this criterion's own wording.

### B3: a property test for Surface (MORK and MCN deferred) — done

- `tools/surface/src/surface/test_surface.py`'s new `RegenerationPropertyTests`: a property test
  (stdlib `random`, seeded — Hypothesis was attempted first and found blocked by this
  environment's package mirror, a 403 on that one dependency, not a network-wide block) generating
  random dependency graphs and checking `impacted_surfaces`'s **soundness** (every selected
  surface genuinely depends, directly or transitively, on a changed source) and **completeness**
  (every surface that genuinely depends on one is selected) against an independently structured
  BFS oracle, plus a monotonicity check (widening the changed set never shrinks the impacted set)
  and a direct assertion of ADR-A27's own words (a surface depending on nothing changed is never
  selected).
- MORK's join-semilattice claim: **not pursued this slice**, by the human's own call — it has
  always been the least certain of the three B3 items named in the epic plan, and is left for a
  later slice to state and confirm properly against `mork_schemas.py`'s `IntentNodeSpec.refines`
  and `mork_validation.py`'s co-occurrence checks, rather than being carried here on an assumption.
- **Validated**: 72 tests pass in `surface.test_surface` (3 new, 69 existing, no regression). A
  seeded mutation (removing the "or already impacted" chaining clause from `impacted_surfaces`)
  was confirmed to fail the soundness/completeness property test before being reverted.
- MCN: **not built this slice**. Recorded in the status record as found-blocked (no RDF-to-MCN
  encoder exists), with a line for whoever eventually builds one.

### B2.1: hardening the differential harness and its independence — not started

Queued 2026-10-08 from an implementation-level review of the programme's own evidence (full
disposition in [the review response](../notes/formal-methods-more-feedback-response.md) §2, §4).
The single highest-value item in the review is listed first:

- **Seed a fault in the compiler, not just in the reference.** B2's stated rationale is catching a
  bug shared by every backend through `tools/mork_compilers`' `_expand`. That has never been
  tested: both defects B2 actually found were in B1's own `denotation.py`, discovered because it
  disagreed with the compiler, never the reverse. Seed a deliberate fault directly into `_expand`
  and into one SPARQL or SHACL template, and confirm the differential tests fail. Until this is
  done, B2's evidentiary claim is "the harness detects disagreement," not "the harness catches
  compiler bugs."
- **An adjudication record for every disagreement.** B2 already fixed two bugs by reading the
  compiler's own template (the `SingleValue` reading, justified by "the real compiler's SPARQL
  template," not by a law citation). Correcting the reference by consulting the implementation
  erodes the independence the reference exists to provide. From now on, every reference/compiler
  disagreement gets a short record: which side was wrong, and the normative citation (a README
  law, or, if the README is silent, a README change — never "the compiler says so" alone).
- **State the per-backend projection explicitly.** B2 tests SPARQL (executed) and SHACL (validated
  with pySHACL) by design (sketch §3), which is correct and already documented — but nothing
  states what SHACL's two-valued conformance result is actually projecting of {Permitted, Denied,
  Undetermined}. Add a short statement, in the reference's own README, of which projection each
  tested backend is claimed to preserve, before SWRL or OWL are ever added to the differential
  suite.
- **Name the engine.** The differential harness executes SPARQL via `tools/mork_compilers`' own
  test helpers, which use rdflib. State this explicitly in the reference's README, since a
  different production engine's semantics (error propagation in `IF`, `COUNT` over unbound values,
  blank-node handling) is untested otherwise.
- **Extend to bounded-exhaustive generation.** The differential suite's 14 cases are fixed
  fixtures. The concept-matching input space is small enough to generate exhaustively: every
  scheme of up to 3-4 concepts, with and without a hierarchy including the degenerate ones, every
  `required`/`excluded` subset, both match modes, candidates inside and outside the scheme. A few
  milliseconds of SPARQL execution per case. This gives B2 a defensible, bounded-universal claim
  instead of an example-based one.
- **Trace the untraced branch.** `decide_concept_match`'s required-but-unmatched → `Denied` branch
  carries no law-ID comment, unlike every other branch. Add one, or an explicit disclaimer, per
  the freshness checker's own discipline (`tools/check_formal_freshness.py`).
- **Confirm L13's coverage.** Not checked this session: re-read Eligibility's law register and
  confirm whether L13 is out of scope for `decide_concept_match` by design (as L15/L16 already are,
  correctly, one layer up in `decide_condition`) or missing.

**Validation:** the seeded-fault check (first bullet) needs a before/after pair exactly like B1's
own seeded `neg3` mutation: the differential test suite passes before the fault is seeded (sanity),
fails once it is seeded, and is confirmed reverted afterwards. The rest are documentation and
fixture-generation additions, validated by the extended test suite still passing.

### B2.2: verify and, if confirmed, fix a possible scheme-less hierarchical-match defect — not started

Flagged by the same review, re-read and confirmed plausible directly against
`tools/reference/eligibility/src/reference_eligibility/denotation.py` this session, but neither
test-driven nor fixed here. With `hierarchical=True` and `scheme=None`, the inner `matches()`
closure always returns `False` (its hierarchical branch requires a scheme to compute ancestors),
so a non-empty `required` set falls through to the unmatched-required branch and returns `DENIED`.
By the same reasoning that fixed B2's own scheme-membership defect (L9: a candidate judged with no
resolved scheme at all is a *different* situation from a candidate judged against a scheme it
happens not to belong to), this looks like it should be `UNDETERMINED`, not `DENIED` — "no scheme
to check hierarchy against" is closer to "not enough evidence to decide" than to "fails the
condition". This needs a fixture and a judgement call against the README's exact wording before
being changed, not a reflexive fix: write the test first, expecting it to fail against today's
code, exactly as repository convention already requires for a defect found this way.

### B5: a measured mutation score — not started

The four mutations recorded across this track and track C (`neg3`, `impacted_surfaces`,
`check_formal_freshness.py` twice) are spot checks, not a systematic mutation-testing pass. Run an
automated mutation-testing tool (for example `mutmut`) over `tools/reference/eligibility` and
report a measured mutation score (the fraction of seeded mutants the test suite kills), rather than
relying on a small, hand-picked set confirmed to fail. A mutant that survives is either a gap in
the test suite or evidence the mutated line carries no semantic weight, and both are worth knowing.

### An explicit statement of T1

This track's B2 (differential, generator-driven testing against shape-derived inputs) and B3 (a
property test of soundness, completeness and monotonicity) are already, in substance, the epic
sketch's rung T1 (property-based and metamorphic testing, §5). Nothing in this track's own
documents has said so plainly until now: T1 is not "not started" anywhere in LATTICE, it has been
running since B2 and B3 landed, under a different name. State this explicitly in the epic's own
rung table (sketch §5) the next time that section is touched, so a future reader does not
re-discover the same gap this review found in a compressed summary of the work rather than in the
work itself.

## 4. Home for the reference

`tools/reference/`, one subdirectory per layer, decided by `ADR-A-FM3` (drafted as part of B1,
§3). Parallel to `tools/proofs/` (mechanised theories, ADR-A-FM2) and `tools/models/` (design-time
models, track C) but for hand-written, test-verified executable references — a third kind of
artefact this epic now has three homes for, each named for what it contains and what verifies it.

## 5. Test taxonomy and evidence

Differential and property tests, `copilot-instructions.md`'s L1-L2 (unit, property/determinism)
for B1's own fixture-comparison tests and B3's property tests; B2's cross-backend comparison is
closest to L3 (contract conformance) in spirit, run against existing fixtures and generators
rather than a schema. None of this track's evidence is a proof (E2: "a bounded check is never
reported as a proof") — every test report names what it checked and at what generator scope, not
an unconditional claim.

## 6. Out of scope

B4 (the evaluation-context reference, CCS C12's conformance kit) — a later phase, once CCS's C12
is briefable. Building an MCN encoder. Stating or confirming MORK's join-semilattice claim —
deferred by the human's own call, not this phase's to pursue. Mechanising any of B1 or B3's
statements in Isabelle (track E, later). Fixing any disagreement B2 or B3 finds in
`tools/mork_compilers`, `tools/surface` or `tools/mork`'s own production code — reported as a
finding, fixed by that tool's own maintainers in its own slice.
