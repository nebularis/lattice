<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Formal Methods, Track B: the reference semantics and the oracle

**Unit ID:** `formal-methods-track-b`
**Unit type:** Phase (Epic Decomposition Model, `copilot-instructions.md`)
**Epic:** [formal-methods](formal-methods.md)
**Sketch:** [formal-methods-track-b.md](../sketches/formal-methods-track-b.md)
**Status record:** none yet — created at kickoff, once this plan is reviewed
**Status:** Proposed, awaiting human review before any slice starts

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
| an ADR for track B's home and scope (epic plan §3's own dependency row) | not drafted. Proposed content in the sketch §5 | B1's first commit — drafted as B1's own first action, Proposed, for human review, the same shape as track A's A1 |
| the Isabelle kernel (`tools/proofs/eligibility/`) | done (track E, E1.0/E1.1) | nothing — B1 ports its statements, doesn't wait on anything further from it |
| `tools/mork_compilers`' SPARQL and SHACL backends | exist, stable | nothing — B2 tests against what exists today |
| `tools/surface/src/surface/invalidation.py` (`RegenerationPlan`) | exists | nothing — B3's item wraps it in a property test |
| an RDF-to-MCN encoder | **does not exist anywhere in the repository** (`mcnio.NullTool.encode` returns `None`) | MCN's round-trip item — out of scope for this plan, recorded as a gap, not built here |
| MORK's join-semilattice claim | **deferred by the human's own call** (2026-10-07): the claim has always been questionable and is left for a later slice to state and confirm properly | out of scope for this plan, not pursued here |
| CCS's C12 | "waiting," several tranche-D slices away (confirmed on `main`, 2026-10-07) | B4 only, out of scope for this plan |

## 3. Slices

### B1: the kernel and Eligibility's denotation, in Python

- Draft `ADR-A-FM3` (home `tools/reference/`, scope B1-B3, restating E1/E3), Proposed, as this
  slice's first action — reviewed and accepted before the rest of the slice's code is treated as
  final, the same order track A's A1 uses for its own ADR.
- `tools/reference/eligibility/kernel.py`: `or3`/`and3`/`neg3`/`decision_leq` ported from
  `tools/proofs/eligibility/KernelLaws.thy`, same names, same statements, docstring wording kept
  close enough to `ontology/eligibility/README.md` to align by inspection.
- `tools/reference/eligibility/denotation.py`: the single-candidate decision function (L9-L12,
  L14), `some_value`/`every_value` (L15, ported from `Eligibility.thy`), negation (L16, `neg3`
  applied to the combined outcome).
- **Validation**: every one of the Isabelle kernel's own `Adequacy.thy` fixture lemmas (the 15
  `MIXES`-derived cases) reproduced as Python unit tests against B1's functions, with identical
  inputs and expected outcomes — the two representations of the same law are compared directly,
  and any divergence is a finding, not a merge conflict to paper over.

### B2: differential tests against the existing compilers

- A test harness that takes one Eligibility condition or profile declaration, evaluates it under
  B1, compiles and evaluates it under `tools/mork_compilers`' SPARQL backend (and SHACL, and SWRL
  or OWL only where the input is one each backend does not already refuse by its own documented
  restriction), and asserts agreement.
- Fixtures: the existing `MIXES` family (`test_set_readings.py` and siblings) reused directly, not
  copied; shape-derived generators (property-based, from `ontology/eligibility/shapes/constraints.ttl`)
  for conditions and profiles within the shapes' own constraints.
- The named negative fixture (epic plan's own B2 row): hierarchical match with exclusions under
  L11, generated at every position relative to an excluded concept in the hierarchy, asserting the
  exclusion's effect never promotes a Permitted candidate.
- "Not a value" first (sketch §3): unbound variables, absent solutions and `FILTER` errors tested
  for their mapping to Undetermined before any other law-by-law comparison runs.
- **Validation**: the harness runs over every existing Eligibility example fixture
  (`ontology/eligibility/examples/`) plus the generated cases, with a report of agreement and
  disagreement per law, not a single pass/fail count — a disagreement is a finding for
  `tools/mork_compilers`' own maintainers, not silently fixed by this slice (sketch §7).

### B3: a property test for Surface (MORK and MCN deferred)

- Surface: a property test (Hypothesis or equivalent) generating a read-set change and asserting
  `plan_regeneration`'s output against the old output's image equals a direct regeneration from
  the new state — ADR-A27's own naturality claim, checked, not only exercised by example.
- MORK's join-semilattice claim: **not pursued this slice**, by the human's own call — it has
  always been the least certain of the three B3 items named in the epic plan, and is left for a
  later slice to state and confirm properly against `mork_schemas.py`'s `IntentNodeSpec.refines`
  and `mork_validation.py`'s co-occurrence checks, rather than being carried here on an assumption.
- MCN: **not built this slice**. Recorded in the status record as found-blocked (no RDF-to-MCN
  encoder exists), with a line for whoever eventually builds one.
- **Validation**: the Surface property test runs, with its generator's coverage (how many
  distinct cases, what the shrinker finds on a seeded failure) recorded, not just a pass count —
  the same "prove it can fail" discipline every other track in this epic uses. A seeded, known-bad
  mutation of `plan_regeneration` (e.g. dropping one read-set entry from the rebuild scope) must
  make the property test fail, checked once before the slice is called done.

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
