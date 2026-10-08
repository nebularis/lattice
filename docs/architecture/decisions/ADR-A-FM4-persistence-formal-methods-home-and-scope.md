<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A-FM4: Home and scope of the Persistence formal-methods track

**Status:** Proposed
**Date:** 2026-10-08
**Related:** the formal-methods epic plan, [formal-methods-track-h.md](../../developer/plans/formal-methods-track-h.md),
[its sketch](../../developer/sketches/formal-methods-track-h.md),
[ADR-A-FM2](ADR-A-FM2-formal-methods-theory-home.md) (home of mechanised theories),
[ADR-A-FM3](ADR-A-FM3-reference-evaluator-home-and-scope.md) (home of the reference evaluator),
[the Persistence engine notes](../../developer/notes/rdf-engine/persistence-fml.md) (the review
this track implements),
[ADR-A78](ADR-A78-persistence-profile-substrate-and-aggregate-boundaries.md),
[ADR-A79](ADR-A79-persistence-compiler-toolchain.md),
[ADR-A80](ADR-A80-housekeeping-component-boundary.md)
**Unit:** [`formal-methods`](../../developer/plans/formal-methods.md) (epic), track H

## Context

`docs/developer/notes/rdf-engine/persistence-fml.md` is an independent, exhaustive review applying
the formal-methods programme's own techniques to the Persistence layer: the `dal:` configuration
vocabulary, its compiler (`tools/persistence`), its generated SPARQL, and the pluggable RDF
backends it targets. Unlike Eligibility (tracks B, C and E's first and so far only target), the
review's calibration evidence (its own Appendix D references, three recorded remediation passes)
is dominated by **concurrency and protocol defects** — a class none of tracks B, C or E's
techniques reach, since T0 (reference semantics), T2 (Alloy) and T5 (Isabelle) are each, by
design, sequential. The epic's own cost ladder (`formal-methods.md` sketch §5) names T4 (model
checking, TLA+ or Quint) as a rung and states plainly that it has "never been attempted." Track H
is that attempt, and needs its own decisions about where its artefacts live, for the same reason
tracks B, C and E each needed one before their first slice (ADR-A-FM2, ADR-A-FM3, and track C's
own "home for the model" sections).

This ADR is deliberately narrow, matching ADR-A-FM2 and ADR-A-FM3's own scope: it decides *where
things live and what the track covers*, not the specification registry's exact shape, the typed
IR's exact types, or any individual protocol model's content. Those are each a later slice's own
design question, detailed when that slice starts, per this epic's rolling-wave discipline.

## Decision

1. **Scope is the RDF and SPARQL side of Persistence only.** Track H covers the `dal:`
   configuration vocabulary, its resolution and validation, the generated SPARQL templates and
   operations, the pluggable RDF-store backends (Core/Extended/Native tiers, ADR-A75), and their
   protocols. **It explicitly excludes any relational or SQL-compilation work** (the separate
   review at `docs/developer/notes/rdf-engine/sql-feedback.md`, "paper 5"): no PostgreSQL schema
   generation, no R2RML/RML mapping, no relational typed IR, no SQL isolation-level models. If a
   relational-compilation formal-methods effort is undertaken later, it is a sibling track with
   its own ADR, not an extension of this one — the two reviews' findings do not transfer
   unchanged (persistence-fml.md §0 states it has not read the SQL review's own material in
   depth, and this track preserves that separation).
2. **Mechanised theories live under `tools/proofs/persistence/`**, extending ADR-A-FM2's existing,
   already-decided convention (one subdirectory per layer, mirroring `ontology/<layer>/`'s own
   name) rather than creating a new convention. No change to ADR-A-FM2 itself.
3. **Design-time models — both Alloy and the new TLA+/Quint protocol models — live under
   `tools/models/`**, in topic-named subdirectories (for example
   `tools/models/persistence-scope-matching/`, `tools/models/persistence-guarded-write/`),
   extending track C's existing, already-established convention (`tools/models/
   vocabulary-scheme-composition/`) to a second tool family under the same top-level name. Track
   C's own reasoning for a name distinct from `tools/proofs/` — "a checked design-time model is
   not a mechanised proof" — applies identically to a TLA+ or Quint protocol model: both are
   bounded-scope evidence for a design or an ADR, not a proof, and neither should be read as one.
   **This is the one point in this ADR that marginally widens an existing convention** (track C's
   "home for the model" section was written describing Alloy specifically); it is named here
   explicitly rather than assumed, for the human to confirm or redirect.
4. **The specification registry and the typed intermediate representation are not a new home at
   all.** Both are changes to the existing `tools/persistence` compiler's own internals — how it
   authors its rules and emits its templates — governed by that package's own existing ADRs
   (ADR-A78, ADR-A79, ADR-A80), not by this one. When track H's H2/H3 slices land, their design is
   recorded as an **addendum to ADR-A79** (persistence compiler toolchain), dated, per this
   repository's own practice for a decision found while building, not as a new formal-methods ADR.
   This ADR does not pre-decide that design.
5. **Generated audits and runtime monitors (rung T7) are deployed where Persistence's own
   generated operations already are** — no new home, no new toolchain. They extend
   `tools/persistence`'s existing generation pipeline and `tools/persistence`'s own housekeeping
   boundary (ADR-A80), not a formal-methods-specific runtime.
6. **The TLA+ versus Quint choice is not made by this ADR.** Both remain named candidates for
   rung T4 (epic sketch §5), exactly as before. Track H's first protocol-model slice runs a short
   toolchain spike (mirroring track C's C1 and track D's D0) before committing either tool to any
   recorded claim, and that spike's own evidence, not this ADR, decides it.
7. **Claims, gates and the assurance ledger.** Track H's claims use the same claim schema and
   gate discipline `tools/proofs/eligibility/gate.py` established (extended per the second
   review's hardening items, track E's E1.4), reused, not reinvented, for
   `tools/proofs/persistence/`. Where track A (the ledger and the harness) exists by the time
   track H needs it, track H's claims feed it; until then, each slice's own Validation Pack is
   the record, the same interim arrangement tracks B and C already use.

## Consequences

- Track H's plan, sketch(es) and status record are filed as their own documents
  (`formal-methods-track-h.md` under `plans/`, `sketches/` and `status/`, plus
  `formal-methods-track-h-protocols.md` and `formal-methods-track-h-specification.md` as
  supporting sketches), per the Epic Decomposition Model's phase-level documentation rule.
- `docs/developer/plans/formal-methods.md` and `docs/developer/status/formal-methods.md` record
  track H alongside tracks A to G, cross-referencing this ADR.
- No ontology content changes as a consequence of this ADR by itself: it governs where track H's
  tooling and evidence live, not any layer's semantics. The `dal:` vocabulary itself is unaffected
  until a specific slice proposes a change, each its own ADR.
- This ADR is numbered in the epic's own non-colliding `A-FM` block (`A-FM4`, the next free number
  in that series, confirmed against this branch's and `main`'s ADR catalogues on 2026-10-08),
  since it is an epic-scoped tooling-home decision, not a shared cross-epic decision — unlike
  `ADR-A116`, which was filed in the main sequential pool for exactly that reason.
