<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Formal Methods, Track B: Status

**Unit ID:** `formal-methods-track-b` (phase, within the `formal-methods` epic)
**Status:** B1, B2 and B3 done, 2026-10-07
**Last updated:** 2026-10-07
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

`ADR-A-FM3` accepted by the human, 2026-10-07.

**Next action, for the human:** none blocking. Track B's three ready slices (B1-B3) are complete.
B4 waits on CCS's C12.

## Slices

| Slice | State | Blocked on |
|---|---|---|
| B1 (kernel and denotation) | **done** | nothing |
| B2 (differential tests against the compilers) | **done** | nothing |
| B3 (Surface's regeneration property test; MORK and MCN deferred) | **done** | nothing |
| B4 (evaluation context, CCS C12's conformance kit) | not started, outline only | CCS's C12, not yet briefable |

## Open questions

| # | Question | Owner |
|---|---|---|
| the overlap rule MORK's lattice-law item needs before it is pursued (deferred, not this phase) | left for a later slice | human, when that slice is scoped |
| an RDF-to-MCN encoder (needed before MCN's round-trip property can be stated at all) | not built, not this track's job | human, if ever prioritised |

## Log

- 2026-10-07: sketch and plan written, scoping B1-B3 (B4 confirmed still blocked on CCS's C12 by
  reading `main` directly). B3 lightened at the human's request: the MORK join-semilattice item
  removed as a questionable claim not to be carried on assumption, MCN's round-trip item already
  recorded as blocked (no RDF-to-MCN encoder exists). Both documents committed by the human.
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
- 2026-10-07: `ADR-A-FM3` accepted by the human.
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
