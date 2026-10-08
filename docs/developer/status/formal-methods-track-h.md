<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Formal Methods, Track H: Status

**Unit ID:** `formal-methods-track-h` (phase, within the `formal-methods` epic)
**Status:** Proposed. Not started
**Last updated:** 2026-10-08
**Plan:** [formal-methods-track-h.md](../plans/formal-methods-track-h.md)
**Sketches:** [formal-methods-track-h.md](../sketches/formal-methods-track-h.md) (main),
[formal-methods-track-h-protocols.md](../sketches/formal-methods-track-h-protocols.md),
[formal-methods-track-h-specification.md](../sketches/formal-methods-track-h-specification.md)
**Epic status:** [formal-methods.md](formal-methods.md)
**Decided by:** [ADR-A-FM4](../../architecture/decisions/ADR-A-FM4-persistence-formal-methods-home-and-scope.md)
(**Proposed**, not yet accepted)

## Current position

This track is new, drafted 2026-10-08 directly from an independent, exhaustive review
(`docs/developer/notes/rdf-engine/persistence-fml.md`) applying this epic's own techniques to the
Persistence layer. Nothing has been built yet. The review itself was read in full, cross-checked
section by section against the epic's own existing track structure (B, C, E) before this track's
plan and sketches were written, so that it connects to, rather than duplicates, what those tracks
already established (the claim/gate discipline, the Isabelle and Alloy homes, the epic's own
rolling-wave discipline for scoping a first slice).

**Why Persistence, briefly** (full argument in the main sketch §1): it is a structurally different
pilot from Eligibility (tracks B/C/E's only target so far), specifically because its own recorded
defect history (three remediation passes, documented in the review's own calibration table) is
dominated by concurrency and protocol defects — a class none of this epic's existing techniques
(reference semantics, Alloy, Isabelle) reach at all. This track's H5 slice is the epic's first use
of rung T4 (TLA+/Quint model checking), named in the epic sketch since its first draft but never
yet attempted.

**Explicitly out of scope, for this entire track:** any relational or SQL-compilation work (a
separate, independent review, `sql-feedback.md`, names its own different formal-methods
programme). See the main sketch §2 and ADR-A-FM4 decision 1.

**Next action, for the human:** review and accept (or revise) `ADR-A-FM4`
(`docs/architecture/decisions/ADR-A-FM4-persistence-formal-methods-home-and-scope.md`), which
decides this track's home (mechanised theories under `tools/proofs/persistence/`, design-time
models — Alloy **and** the new TLA+/Quint protocol models — under `tools/models/`) and its scope
(RDF/SPARQL only, no relational work). H1 (static hygiene) needs no toolchain and no ADR
acceptance to start, and could begin immediately if the human wants work to proceed before
reviewing the ADR; H2 onward should wait for ADR-A-FM4's acceptance.

## Slices

| Slice | State | Blocked on |
|---|---|---|
| H1 (static hygiene: prefix antichain, witness coverage, S-3/S-4, declaration gap, stable labels) | not started, fully detailed in the plan | nothing — can start immediately |
| H2 (typed IR) | not started, outlined in the plan | H1 (informative, not a hard blocker) |
| H3 (specification registry) | not started, outlined in the plan | H2 preferred first (smaller, more self-contained), not a hard blocker |
| H4 (exhaustive cross-axis validation, BDD/SMT) | not started, outline only | H3 |
| H5 (capability-record extension, TLA+/Quint toolchain spike, protocol models A-D) | not started, outline only | H2 (read/write sets from the IR); ADR-A-FM4's acceptance recommended first |
| H6 (Isabelle theories: Resolution, Positions, Encoding, Outcomes) | not started, outline only | H1; H5 for `Outcomes.thy` |
| H7 (protocol models E-J) | not started, outline only | H5, H6 |
| H8 (protocol models K-N, grounding) | not started, outline only | H7 |
| H9 (detection-coverage closure, generated audits) | not started, outline only | H3, H4 |
| H10 (runtime monitors) | not started, outline only | H9 |

## Open questions

| # | Question | Owner |
|---|---|---|
| H-D1 | accept, revise or reject ADR-A-FM4 | human |
| H-D2 | TLA+ or Quint | deferred to H5's own toolchain spike |
| H-D3 | ADR-A79 addendum vs a fresh ADR for H2/H3's design | recommend an addendum; deferred to H2/H3 |
| H-D4 | fix the composite-boundary soundness gap now (a refusal) or wait for H2's typed IR | recommend: refuse now, fix properly later |
| H-D5 | feed track A's ledger once it exists, or keep an independent record permanently | recommend: feed track A once it starts |

## Log

- 2026-10-08: sketch (main, protocols, specification), plan and status record written, following a
  full read of `persistence-fml.md` and a cross-check against the epic's own existing track
  structure (B, C, E) and conventions (ADR-A-FM2, ADR-A-FM3, track C's `tools/models/` home). ADR
  `ADR-A-FM4` drafted, Proposed, deciding this track's own home and scope, including the explicit
  exclusion of all relational/SQL-compilation work (the separate `sql-feedback.md` review). No
  code written yet; H1 is ready to start as the next action.
