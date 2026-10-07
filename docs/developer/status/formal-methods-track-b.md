<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Formal Methods, Track B: Status

**Unit ID:** `formal-methods-track-b` (phase, within the `formal-methods` epic)
**Status:** B1 done, 2026-10-07. B2 and B3 not started
**Last updated:** 2026-10-07
**Plan:** [formal-methods-track-b.md](../plans/formal-methods-track-b.md)
**Sketch:** [formal-methods-track-b.md](../sketches/formal-methods-track-b.md)
**Epic status:** [formal-methods.md](formal-methods.md)
**Decided by:** [ADR-A-FM3](../../architecture/decisions/ADR-A-FM3-reference-evaluator-home-and-scope.md)
(**Proposed**, not yet accepted — home `tools/reference/`, scope B1-B3)

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

**Next action, for the human:** accept or revise `ADR-A-FM3` (Proposed). Then, B2 (differential
tests against `tools/mork_compilers`' SPARQL and SHACL backends) or B3 (Surface's ADR-A27
regeneration property test) — either can start next, neither depends on the other.

## Slices

| Slice | State | Blocked on |
|---|---|---|
| B1 (kernel and denotation) | **done** | nothing |
| B2 (differential tests against the compilers) | not started | nothing |
| B3 (Surface's regeneration property test; MORK and MCN deferred) | not started | nothing |
| B4 (evaluation context, CCS C12's conformance kit) | not started, outline only | CCS's C12, not yet briefable |

## Open questions

| # | Question | Owner |
|---|---|---|
| ADR-A-FM3's acceptance | Proposed, drafted as B1's first action | human |
| the overlap rule MORK's lattice-law item needs before it is pursued (deferred, not this phase) | left for a later slice | human, when that slice is scoped |

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
