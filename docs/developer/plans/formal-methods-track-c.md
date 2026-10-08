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

### C1: the Alloy skeleton (prerequisite, not in the epic's own numbering) — done

- Alloy Analyzer 6.2.0 (a single MIT-licensed JAR) installed at `C:\fmx\alloy\alloy.jar`, the
  same short-root, not-tracked-in-the-repository convention track D and E's toolchains use.
  Needs a JDK new enough for Alloy's own dispatcher; the mise-managed Java 25 already on this
  host works (the bare `java` on `PATH` in a fresh terminal is a stale 1.8.0_491 — invoke the
  mise JDK's `bin\java.exe` explicitly, or put it first on `PATH`, same gotcha repository memory
  already records for Maven).
- A trivial smoke-test model (`tools/models/vocabulary-scheme-composition/smoke.als`: a
  satisfiable `run Possible` and an unsatisfiable `run Impossible`) run headlessly via the
  Analyzer's own `exec` sub-command (`java -jar alloy.jar exec smoke.als`), which writes a
  `receipt.json` with each command's structured result.
- **Validated:** `Possible` reported `SAT` with an instance in its `receipt.json`; `Impossible`
  reported `UNSAT` with no `solution` key at all — the same "prove it can fail, not just that it
  can pass" discipline track D's seeded defects used. The smoke output itself was not kept (a
  one-off toolchain check, recorded here instead); the model file (`smoke.als`) is.

### C2: binding resolution with scheme composition — done

- The model built at `tools/models/vocabulary-scheme-composition/SchemeComposition.als`, close
  to the sketch's proposed shape (§4) with one simplification found necessary once Alloy's own
  type-checking was run against it: `Scheme` is given explicit `Concept` members and a
  `broader: Concept -> Concept` hierarchy restricted to its own members (needed to state the
  overlap question concretely), and `single: Source -> Context -> lone Scheme` stands in for the
  whole of ADR-A85's resolver collapsed to "at most one scheme, per source, per context" — not a
  model of candidate bindings, specificity or conflict, which `tools/vocabulary/` already
  implements and whose own properties are assumed to hold before composition is asked to do
  anything with the result.
- Two checks run, not assumed, at scope 4: `EverySourceResolves` (HQ-4's own property, "every
  role a layer needs resolves," made checkable) and `NoOverlapDisagreement` (does the sketch's
  proposed union of members and union of hierarchies, by itself, already rule out two composed
  schemes disagreeing about a shared concept's `broader` parent).
- **Validated, results recorded in full in [the model's own README](../../../tools/models/vocabulary-scheme-composition/README.md):**
  `EverySourceResolves` found **no counterexample** (a self-consistency check on `composed`'s own
  definition, not a deep claim, and recorded as such). `NoOverlapDisagreement` **found a
  counterexample** — two schemes sharing two member concepts, disagreeing about one concept's
  `broader` parent — confirming the sketch's open question (§2, §5) is reachable, not merely
  hypothetical. The counterexample instance itself is read and explained in the model's README,
  not only reported as a pass/fail count. **Finding:** the overlap rule cannot be left unstated;
  three candidates are named (forbid overlap by a new Vocabulary shape, order sources by an
  explicit precedence rule, or allow free union and require `broader`'s transitive closure to
  stay acyclic) with no choice made among them here — that choice is the human's, informed by
  this evidence, for whichever ADR accepts scheme composition.

### C2.1: well-formedness facts, and a re-run — done

Queued, then done the same session, 2026-10-08, after an implementation-level review (full
disposition in [the review response](../notes/formal-methods-more-feedback-response.md) §2, §4):
the original `NoOverlapDisagreement` counterexample relied on a concept recorded as its own
`broader` parent, a self-loop `Scheme`'s signature never excluded. Two facts were added
(`broader` irreflexive, `^broader` acyclic) and the check re-run at the same scope. The
counterexample survives, now non-degenerate (two distinct schemes genuinely disagreeing about a
shared concept's parent, neither relation touching the shared concept itself) — recorded in full,
with the new witness, in [the model's own README](../../../tools/models/vocabulary-scheme-composition/README.md).

### C2.2: model the composed scheme and check a decision-level property — not started

The model as built (C2) shows that two source schemes' relations *can* differ over a shared
concept. It never constructs the composed scheme itself, and never checks a property at the level
that actually matters to an adopter: whether a decision made under the composed scheme (an
Eligibility hierarchical-match outcome, L9-L11) can disagree with the decision any one source
scheme alone would have given. Extend the model to build the union scheme explicitly and check
this directly, rather than only the weaker "the inputs to a union can disagree" property C2
checked.

### C2.3: model `ADR-A116`'s accepted rule itself, against its own motivating cases — not started

**Recommended before or alongside `ADR-A116`'s acceptance, not after.** Neither C2 nor its
well-formedness fix (C2.1) ever modelled the rule `ADR-A116` actually decided (forbid overlapping
membership, checked by a new static Vocabulary shape). Add it as a fact, then `run` the real HQ-4
and IMA-D4a configurations (an Instrument baseline's dates composed with a wording's own dates;
InsurML's type scheme composed with a profile-local scheme) to confirm they are *admitted*, not
rejected by a rule chosen for simplicity. The live risk, raised directly by the review (its
answer to its own open question 2) and not yet checked: a wording that refines or redefines a
baseline date, or a profile concept that legitimately belongs to two schemes (ordinary SKOS
practice: `skos:inScheme` is many-valued), may be exactly the overlap the simplest rule forbids. A
`run` that fails to admit either motivating case is evidence the ADR should be revised before it
is accepted, not after.

## 4. Home for the model

Confirmed, not merely proposed: `tools/models/vocabulary-scheme-composition/`, with a parent
`tools/models/README.md` explaining the convention for any later law family's model. Parallel in
spirit to `tools/proofs/`'s layer-named subdirectories but under a different top-level name, since
a checked design-time model is not a mechanised proof and ADR-A-FM2's reasoning (a proof is an
executable reference implementation's assurance) does not transfer unchanged to a model whose job
is finding counterexamples before anything is implemented.

## 5. Test taxonomy and evidence

A design-time model's result is its own category, parallel to proof's in the Isabelle track
(`formal-methods-track-e.md` §4): a `run` or `check`'s outcome (instance found / none found, at a
stated scope) is the unit of evidence, not a position on the `copilot-instructions.md` L0-L8
taxonomy. Alloy's scope is always finite, so a `check` that finds no counterexample is evidence
up to that scope, stated as such, never reported as an unconditional proof.

**Process additions, queued 2026-10-08** (review §4.5): archive each model's `receipt.json`
alongside its `README.md` rather than only summarising it in prose; pin and state the Alloy
Analyzer version a result was produced with; re-run every check whenever the ADR or law family it
evidences changes, not only once at authoring time; add at least one non-vacuous `run` (not only
`check`s) per model, exhibiting a realistic instance, so a reader can see the model is not
accidentally unsatisfiable everywhere.

## 6. Out of scope

C3 (slot exclusivity and exhaustiveness, SMT, CCS C13a — a later slice). Writing the shared
Vocabulary ADR (a human decision; this track's job is the evidence for it). Any change under
`ontology/` (this track produces a model and a recommendation, not a merged ontology edit).
Eligibility's hierarchical-match addendum (`insurml-typing.md` §6.1's dependent follow-on),
until the Vocabulary ADR itself is accepted.
