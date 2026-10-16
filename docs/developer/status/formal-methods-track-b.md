<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Formal Methods, Track B: Status

**Unit ID:** `formal-methods-track-b` (phase, within the `formal-methods` epic)
**Status:** B1, B2 and B3 done, 2026-10-07. **B2.1 and B2.2 done, 2026-10-09**, on branch
`fm/eligibility-pass` (machine S), part of the formal-methods epic's Eligibility pass (FM-EP)
CCS's C9b3 waits on. B5 attempted the same session, blocked (see below), deferred
**Last updated:** 2026-10-09
**Plan:** [formal-methods-track-b.md](../plans/formal-methods-track-b.md)
**Sketch:** [formal-methods-track-b.md](../sketches/formal-methods-track-b.md)
**Epic status:** [formal-methods.md](formal-methods.md)
**Decided by:** [ADR-A-FM3](../../architecture/decisions/ADR-A-FM3-reference-evaluator-home-and-scope.md)
(**Accepted** 2026-10-07 — home `tools/reference/`, scope B1-B3)

## Current position

B1 built `tools/reference/eligibility/`: `kernel.py` (a direct port of
`tools/proofs/eligibility/KernelLaws.thy`'s `or3`/`and3`/`neg3`/`decision_leq` and
`Eligibility.thy`'s `some_value`/`every_value`) and `denotation.py` (the single-candidate decision
for laws L9-L12 and L14, written from `ontology/eligibility/README.md` §6's own prose, cross-
checked against — not copied from — `tools/mork_compilers`' `eligibility_ir.py`'s `_expand`, and
the L15/L16 set-reading and negation composition on top of it).

47 tests pass (`mise run check:reference-eligibility`): exhaustive checks of TA1 (`or3`/`and3`
monotone in both arguments) and TA2 (`neg3` involutive, monotone, fixes `Undetermined`) over the
full three-valued domain; the 15 adequacy fixtures reproduced verbatim from
`tools/proofs/eligibility/Adequacy.thy`; bounded checks (lists up to length 3) of TL1-TL3b; and
direct tests of `decide_concept_match`/`decide_condition` against each of L9, L10, L11, L12, L14,
L15 and L16 individually, using a small citrus/fruit hierarchy fixture. A seeded mutation (`neg3`
deliberately made to fix `Undetermined` to `Permitted`) was confirmed to fail six tests across
both files before being reverted — the "prove it can fail" check the plan's own validation
criterion calls for.

B2 (`tools/reference/eligibility/tests/test_differential.py`) differentially tested the reference
against `tools/mork_compilers`' compiled SPARQL and SHACL, reusing that package's own fixtures
(`DIAGNOSES`, `ENTITLEMENT`) and one real Eligibility example (`flat-scheme-lending.ttl`). It found
and fixed two real defects in B1's `denotation.py`: a missing scheme-membership precondition (L9's
"restricted to that scheme's members" — a candidate outside the scheme could be wrongly Denied
rather than Undetermined) and a `SingleValue` reading that took the first value regardless of
count instead of requiring exactly one. 63 tests pass.

B3 added `RegenerationPropertyTests` to `tools/surface/src/surface/test_surface.py`: a property
test (stdlib `random`, seeded — Hypothesis was attempted first and found blocked by this
environment's package mirror specifically, not a network-wide block) checking `impacted_surfaces`'
soundness and completeness against an independently structured BFS oracle, plus monotonicity and a
direct ADR-A27 assertion. MORK's join-semilattice item and MCN's round trip remain deferred, as
scoped. 72 tests pass in `surface.test_surface` (3 new, no regression).

`ADR-A-FM3` accepted, 2026-10-07.

**2026-10-09, branch `fm/eligibility-pass` (machine S), B2.2 done.** The suspected defect was
real: `decide_concept_match(hierarchical=True, scheme=None, required={...})` fell through to the
unmatched-required branch and returned `Denied`. Fixed test-first (a failing test added and
confirmed failing against the old code, per convention): a new early guard returns `Undetermined`
when a hierarchical condition has no resolved scheme at all — "no closure to test a candidate
against", not "this candidate fails the closure", the same reasoning L14 already uses. `L9`'s own
wording in `ontology/eligibility/README.md` amended to state this case explicitly (the CCS plan's
own anticipation that this slice "may change the README's wording" confirmed).

**2026-10-09, B2.1 done.** All six items: (1) a deliberate fault seeded directly into
`eligibility_ir._expand` (via `monkeypatch`, not a permanent edit), confirmed the SHACL backend's
real output (which reads `plan.expansion` directly) now disagrees with the unchanged reference —
the harness's core rationale, tested for the first time; (2) an adjudication log added to this
package's own README, with entries for all three disagreements found so far (B2's two, B2.2's
one), naming which side was wrong and the normative citation, including one entry flagged as
weaker than the others (B2's `SingleValue` fix, settled by reading the compiler's template, not a
README law); (3) the per-backend projection of `{Permitted, Denied, Undetermined}` stated
explicitly for both tested backends (SPARQL: no projection, exact; SHACL: conformance-plus-lists,
reconstructed by the test helper); (4) the differential engine named (rdflib, not a production
store); (5) the previously untraced required-but-unmatched branch given a citing comment; (6) L13
confirmed out of scope by design (`elg:StaticConstraint`, not `elg:SemanticLaw` — a declaration-time
rule discharged by SHACL, never part of this decision function), documented in the module
docstring. Bounded-exhaustive generation added: `TestBoundedExhaustiveConceptMatching` generates
every combination of flat/chained three-concept scheme, both match modes, every required subset of
`{c0, c1}` and every excluded subset of `{c2}` (28 compiled plans, 4 candidates each, 112
comparisons), checked against both SPARQL and SHACL, not sampled.

**B5 attempted, blocked.** `pip install mutmut` fails: its dependency `textual` pulls
`platformdirs`, which 403s from the configured mirror (same per-package-mirror-gap pattern as
`hypothesis` before it, repository memory). Not retried further; deferred, not this session's to
force. A hand-seeded mutation (as this session already used three times elsewhere) remains the
fallback if a measured score is wanted before the mirror gap closes.

**Validated:** `python -m pytest tools/reference/eligibility/tests -q` — 66 passed (was 63: +1
B2.2, +2 B2.1's two new test classes, one of which itself checks 28 generated cases × 4
candidates internally).

**Next action, for the maintainer:** review and accept this branch's work (B2.1, B2.2, plus track E's
FM-D17/E1.4 on the same branch) so CCS's C9b3 can start. B4 still waits on CCS's C12. B5 remains
open whenever the mirror gap clears or a hand-seeded alternative is wanted.

## Slices

| Slice | State | Blocked on |
|---|---|---|
| B1 (kernel and denotation) | **done** | nothing |
| B2 (differential tests against the compilers) | **done** | nothing |
| B2.1 (harden the differential harness, seed a compiler-side fault) | **done**, 2026-10-09 | nothing |
| B2.2 (verify/fix the scheme-less hierarchical-match branch) | **done**, 2026-10-09, defect confirmed and fixed | nothing |
| B3 (Surface's regeneration property test; MORK and MCN deferred) | **done** | nothing |
| B4 (evaluation context, CCS C12's conformance kit) | not started, outline only | CCS's C12, not yet briefable |
| B5 (measured mutation score) | attempted 2026-10-09, blocked (`mutmut`'s dependency chain 403s on the mirror), deferred | the mirror gap, or a hand-seeded fallback |

## Open questions

| # | Question | Owner |
|---|---|---|
| the overlap rule MORK's lattice-law item needs before it is pursued (deferred, not this phase) | left for a later slice | maintainer, when that slice is scoped |
| an RDF-to-MCN encoder (needed before MCN's round-trip property can be stated at all) | not built, not this track's job | maintainer, if ever prioritised |

## Log

- 2026-10-07: sketch and plan written, scoping B1-B3 (B4 confirmed still blocked on CCS's C12 by
  reading `main` directly). B3 lightened at our request: the MORK join-semilattice item
  removed as a questionable claim not to be carried on assumption, MCN's round-trip item already
  recorded as blocked (no RDF-to-MCN encoder exists). Both documents committed.
- 2026-10-07: B1 built and validated. `ADR-A-FM3` drafted (Proposed): home `tools/reference/`,
  scope B1-B3, restating epic principles E1 and E3. `tools/reference/eligibility/` created
  (`pyproject.toml`, `README.md`, `src/reference_eligibility/{kernel,denotation}.py`,
  `tests/{test_kernel,test_denotation}.py`). Wired into `mise.toml`
  (`bootstrap:reference-eligibility`, `check:reference-eligibility`, both in the default
  aggregates — no dependency beyond `pytest`). Root `README.md` and `tools/README.md` updated.
  47 tests pass; a seeded mutation confirmed the suite catches a real regression before being
  reverted.
- 2026-10-07: E1.2's blocker (track E's own status) resolved as a consequence of this phase's
  sketch: the rounding/residual theorem belongs to B4/E3-E4, not Quantification. Track E's plan
  and status records corrected to retire E1.2 and point at this track's B4, and E1.3's blocked-on
  text refreshed now that track C's C2 is done (the overlap-rule ADR is the remaining blocker,
  not C2 itself).
- 2026-10-07: `ADR-A-FM3` accepted.
- 2026-10-07: B2 built. `tools/reference/eligibility/tests/test_differential.py` differentially
  tests `decide_concept_match` against `tools/mork_compilers`' compiled SPARQL (executed) and
  SHACL (pySHACL), reusing that package's own fixtures (`DIAGNOSES`, `ENTITLEMENT`) and helpers
  (`with_questions`, `sparql`, `shacl`), plus one real Eligibility example
  (`flat-scheme-lending.ttl`) for L14. Found and fixed two real defects in B1's own
  `denotation.py`: (1) no scheme-membership precondition (L9's "restricted to that scheme's
  members"), so a candidate entirely outside the resolved scheme could be wrongly Denied instead
  of Undetermined; (2) `decide_condition`'s `SingleValue` reading took the first value regardless
  of count rather than requiring exactly one. Both fixed, with regression tests added to
  `test_denotation.py`. `mork-compilers` and `pyshacl` added to the package's test extras
  (`bootstrap:reference-eligibility` now depends on `bootstrap:mork-compilers`). 63 tests pass.
- 2026-10-07: B3 built. `tools/surface/src/surface/test_surface.py` gains
  `RegenerationPropertyTests`: Hypothesis was attempted first for property generation and found
  blocked by this environment's package mirror (a 403 on that one dependency specifically,
  confirmed not a network-wide block — other packages installed normally this session); fell back
  to stdlib `random` with a fixed seed. Checks `impacted_surfaces`' soundness and completeness
  against an independently structured BFS oracle (a explicit queue, not the SUT's own
  repeated-pass fixed point) over 200 random dependency graphs, plus a monotonicity property and a
  direct assertion of ADR-A27's own wording. A seeded mutation (removing the "already impacted"
  chaining clause) was confirmed to fail the property test before being reverted. MORK's
  join-semilattice item and MCN's round trip remain deferred/blocked, as scoped. 72 tests pass in
  `surface.test_surface` (3 new, no regression). No new mise task: Surface's tests already run
  under the existing `check:python-root` task, which picks up the new test class automatically.
