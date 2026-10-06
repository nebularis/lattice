<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Formal Methods, Track C: the design-time models

**Unit ID:** `formal-methods-track-c`
**Unit type:** Phase (Epic Decomposition Model, `copilot-instructions.md`)
**Epic:** [formal-methods](formal-methods.md)
**Sketch:** [formal-methods-track-c.md](../sketches/formal-methods-track-c.md)
**Status record:** [formal-methods-track-c.md](../status/formal-methods-track-c.md)
**Status:** Proposed. C1 (toolchain skeleton) and C2 (the scheme-composition model) both start
now; neither needs a prover choice or an ADR of its own first

## 1. Scope

Design-time models, permanently, for whichever law family needs one before an ADR fixes it (epic
§4, "Track C"). This plan details the first two slices only — C1 (skeletons) and C2 (binding
resolution with scheme composition, ahead of CCS C8's HQ-4 and insurml-alignment's IMA-D4a). C3
(slot exclusivity and exhaustiveness by SMT, in step with CCS C13a) stays at the epic's outline
level until C2 is done, per the rolling-wave rule.

Track C needs no proof assistant (epic plan's track table: "Prover: no") and does not depend on
track D or E's gate. It is independent of the Isabelle/`tools/proofs/` work entirely: a different
tool (Alloy, §3 below), a different question (does a design admit the properties an ADR will
claim, checked over generated instances, not proved as a theorem), a different artefact (a
checked model and a recommendation, not a mechanised law).

## 2. What this plan depends on, and what blocks it

| Dependency | State | Blocks |
|---|---|---|
| the Alloy toolchain | not installed in this repository yet. Java 25 is already available (`mise`); Alloy Analyzer is one MIT-licensed JAR, no further runtime dependency | C1 |
| ADR-A85 (the current single-scheme resolution law) | accepted, read in full for this plan (sketch §2) | C2's model must keep its three properties (determinism, reported conflicts, unscoped fallback) for the single-source case |
| HQ-4's and IMA-D4a's own statements | both read directly from `main` and from this repository's own plans, not guessed at (sketch §1) | C2's model targets exactly what they ask, not a reinvented version of it |
| the shared Vocabulary ADR itself | not written, and not this track's job to write (sketch §5) | C2 produces the checked evidence such an ADR would cite; it does not draft the ADR |

## 3. Slices

### C1: the Alloy skeleton (prerequisite, not in the epic's own numbering)

- Install Alloy Analyzer (a single JAR, `org.alloytools.alloy`, MIT licensed) under the same
  `.build/formal/`-style convention track D used for other toolchains, or a repository-local
  `tools/models/` home if that fits better once C2's own home is decided (see C2 below) — not
  `spikes/`, which is track D's alone.
- A trivial smoke-test model (`sig A {} sig B { r: A }` or similar) run headlessly
  (`java -cp alloy.jar ...` or the Analyzer's CLI) to confirm the JAR runs under this host's
  Java 25, and that `run`/`check` commands produce a result programmatically, not only in the
  GUI.
- **Validation:** the smoke model's `run` finds an instance, and a deliberately unsatisfiable
  variant reports none — the same "prove it can fail, not just that it can pass" discipline
  track D's seeded defects used.

### C2: binding resolution with scheme composition

- The model proposed in the sketch (§4), refined against what Alloy's analyzer actually accepts
  once C1 is working: `Scheme`, `Context`, `Source`, `Contract`, ADR-A85's existing per-source
  resolution rule as a fact, and the composed `resolvesTo` relation.
- Two checks, not assumed: **every source resolves** (HQ-4's own property, made checkable) and
  **composition does not silently merge overlap** (the sketch's second open question, §2) —
  run as a `check` with a scope large enough to find a counterexample if one exists, not just a
  `run` that shows one possible good instance.
- **Validation:** both checks run and their results are recorded verbatim (which found a
  counterexample, which did not, at what scope), with the counterexample itself (if any) read and
  explained, not just reported as a pass/fail count. A recommendation for the overlap rule
  (sketch §5's first open question) follows from what the check actually finds, not from a
  preference stated before running it.

## 4. Home for the model

Not fixed by the sketch (deliberately — see its §5). This plan's working assumption, to be
confirmed when C1 starts: `tools/models/vocabulary-scheme-composition/`, parallel in spirit to
`tools/proofs/`'s layer-named subdirectories but under a different top-level name, since a
checked design-time model is not a mechanised proof and ADR-A-FM2's reasoning (a proof is an
executable reference implementation's assurance) does not transfer unchanged to a model whose
job is finding counterexamples before anything is implemented. If a smaller, less committal home
turns out to fit better once C1 is under way, this plan is wrong here, not the sketch.

## 5. Test taxonomy and evidence

A design-time model's result is its own category, parallel to proof's in the Isabelle track
(`formal-methods-track-e.md` §4): a `run` or `check`'s outcome (instance found / none found, at a
stated scope) is the unit of evidence, not a position on the `copilot-instructions.md` L0-L8
taxonomy. Alloy's scope is always finite, so a `check` that finds no counterexample is evidence
up to that scope, stated as such, never reported as an unconditional proof.

## 6. Out of scope

C3 (slot exclusivity and exhaustiveness, SMT, CCS C13a — a later slice). Writing the shared
Vocabulary ADR (a human decision; this track's job is the evidence for it). Any change under
`ontology/` (this track produces a model and a recommendation, not a merged ontology edit).
Eligibility's hierarchical-match addendum (`insurml-typing.md` §6.1's dependent follow-on),
until the Vocabulary ADR itself is accepted.
