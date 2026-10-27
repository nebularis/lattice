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
§4, "Track C"). This plan details C1 (skeletons), C2 (binding
resolution with scheme composition, ahead of CCS C8's HQ-4 and insurml-alignment's IMA-D4a), and C4 and C5 (the models of ADR-A130 and ADR-A131). C4c, with the Ensemble plan's ES-8, is added only if its addendum admits cyclic components. C3
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
  stay acyclic) with no choice made among them here — that choice is the maintainer's, informed by
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

### C4: model ADR-A130 (Ensemble) — briefed 2026-10-22

**Gate.** ADR-A130 is accepted after C4 (the Ensemble plan, 2026-10-21). C4 is evidence for that
decision. A check that fails where the brief expects it to hold, or a finding probe that shows a gap,
comes back as an amendment to ADR-A130 or a question in the Ensemble or Ledger plan before the
maintainer accepts.

#### C4 in detail

**Machine:** R. **Branch:** `fm/c4-ensemble-model`, from this branch or `main` after it merges.
**Commits are the maintainer's.** **Validation Pack:** [formal-methods-c4](../validation/formal-methods-c4.md).
**Decisions modelled:** ADR-A130 decisions 3 (kinds, closed semantics), 4 (endpoints, narrowing), 5
(units, positions, least fixpoint, order, cycles, independence of order) and 10 (signed shares), with
ADR-A131 decisions 5 (an account shared by several instruments belongs to their ensemble) and 6 (two
phases at one position).
**Home:** `tools/models/ensemble-composition/`, with `Ensemble.als`, a `README.md` in the form of
`vocabulary-scheme-composition/README.md`, and the archived `receipt.json` and any counterexample
files `exec` writes. `tools/models/README.md` gains a line for it.
**Toolchain:** Alloy Analyzer 6.2.0, the same JAR as C1, from
`https://github.com/AlloyTools/org.alloytools.alloy/releases/download/v6.2.0/org.alloytools.alloy.dist.jar`.
It is not installed on machine R. The maintainer downloads it, or approves the download, to a path
outside the repository, and its SHA-256 is recorded in the model's README. Run with the mise JDK.

**The question.** Does ADR-A130's design admit every motivating case, refuse what it says it refuses,
and give one outcome whatever valid order a host chooses? And where does it leave a case undefined?

**What is modelled, and what is not.**

| Modelled | As |
|---|---|
| instruments and their parts | `Instrument`, `Part`. A unit is a part. An endpoint naming a whole instrument names all its parts (decision 4) |
| positions | `Position`, totally ordered (`util/ordering`) |
| ensembles and nesting | `Ensemble` with `members` and an acyclic `nested` |
| relations | `Relation` with a kind, one ensemble, an antecedent and a dependant endpoint, and whether the dependant reads the antecedent at the previous position. Only K2 and K3 create reading edges. K1, K4, K5 and K8 are structural here |
| shared accounts | `Account` with an owner ensemble, drawn by parts |
| evaluation | steps over parts and positions: `Propose(u, p)`, `Merge(a, p)`, `Settle(u, p)`, with edges for reads, proposals, grants and a unit's own propose-before-settle |
| outcomes | an abstract value per step from a small set including Undetermined, and two runs compared |
| signed shares | integers for written lines, lines to stand, the order and signed lines |

| Not modelled | Why |
|---|---|
| Instrument's own evaluation inside a unit | assumed deterministic in the facts the unit reads. That a part's evaluation agrees with its whole instrument restricted to it is E4b's locality lemma |
| merge rules' arithmetic and rounding | Ledger's, model C5. C4 models only that a merge reads the set of proposals, never their arrival |
| K7 and admitted cycles | ES-8's addendum, with C4c |
| time beyond the previous position | a read further back is acyclic for the same reason, so one step back suffices |

**A starting point for the model.** The builder may restructure it, but every check below must keep
its meaning.

```alloy
-- SPDX-License-Identifier: MPL-2.0
open util/ordering[Position] as Pos

sig Position {}
sig Instrument { parts: some Part }
sig Part { of: one Instrument }
fact PartsOfTheirInstrument { parts = ~of }

sig Ensemble { members: set Instrument, nested: set Ensemble }
fact NestingAcyclic { no e: Ensemble | e in e.^nested }

abstract sig Kind {}
one sig K1, K2, K3, K4, K5, K6, K8 extends Kind {}
one sig Earlier {}

sig Relation {
  kind: one Kind,
  inEnsemble: one Ensemble,
  antecedent: some Part,
  dependant: some Part,
  readsEarlier: lone Earlier
}

fact Endpoints {
  all r: Relation {
    one r.antecedent.of
    one r.dependant.of
    r.antecedent = r.antecedent.of.parts or one r.antecedent
    r.dependant = r.dependant.of.parts or one r.dependant
    (r.antecedent + r.dependant).of in r.inEnsemble.*nested.members
  }
}

sig Account { owner: one Ensemble, drawnBy: set Part }

abstract sig Step { at: one Position }
sig Propose extends Step { unit: one Part }
sig Settle extends Step { unit: one Part }
sig Merge extends Step { account: one Account }
fact OneStepEach {
  all u: Part, p: Position | one s: Propose | s.unit = u and s.at = p
  all u: Part, p: Position | one s: Settle | s.unit = u and s.at = p
  all a: Account, p: Position | one m: Merge | m.account = a and m.at = p
}

-- precedes: Step -> Step, defined as the union of (not `before`, an Alloy 6 temporal keyword)
--   a unit's propose before its settle, at one position
--   a drawer's propose before the account's merge, and the merge before the drawer's settle
--   for a K2 or K3 relation, the antecedent's settle before the dependant's propose, at the same
--   position, or at the previous position where the relation reads earlier
fun precedes: Step -> Step { ... }

pred admitted { no (^precedes & iden) }

-- the same graph over parts only, ignoring positions, with edges only from relations that read at
-- the same position
fun samePosition: Part -> Part { ... }
```

**Checks.** Each is a `check` (expected: no counterexample) or a `run` (expected: an instance), at
the scope shown. Integers use `8 Int` and every amount is bounded to 0 to 10 by a fact, so no
product overflows.

| ID | Command | Claim | ADR | Expected | Scope |
|---|---|---|---|---|---|
| C4-A1 | `check RefusalCriterion` | the step graph is acyclic exactly when the same-position graph over parts is: refining by position and part is the whole of the refusal rule | A130 d5 | no counterexample | 5, 3 Position |
| C4-A2 | `check UniqueOutcomeWhenAdmitted` | two runs that are each deterministic in what a step reads give the same outcome at every step, when admitted. This is the composition law at small scope, and order independence follows, since a schedule only sequences determined steps | A130 d5 | no counterexample | 5, 3 Position, 2 Run |
| C4-A3 | `run CycleAdmitsTwoOutcomes` | without admission, two deterministic runs can differ. The reason cycles are refused | A130 d5 | an instance | 4 |
| C4-A4 | `check SharedDrawsAddNoCycle` | parts drawing one account at one position never make the step graph cyclic by themselves, given the two phases | A131 d6 | no counterexample | 5, 3 Position |
| C4-A5 | `run SingleStepDrawsCycle` | if each drawer instead read the balance the others left, at one position, the graph is cyclic. The reason for two phases | A131 d6 | an instance | 4 |
| C4-A6 | `check SharedAccountOwnedByCommonEnsemble` | every account drawn by parts of two or more instruments is owned by an ensemble whose nested members include each drawer | A131 d5 | no counterexample, as a fact the model states. A counterexample means the fact is missing | 5 |
| C4-A7 | `check SignedSharesSumToOrder` | where written lines reach the order and lines to stand do not exceed it, and every scaled line is exact, signed lines sum to the order | A130 d10 | no counterexample | 4 Line, 8 Int |
| C4-A8 | `check SignedNeverAboveWritten` | no signed line exceeds its written line, and a line to stand is signed as written | A130 d10 | no counterexample | 4 Line, 8 Int |
| C4-A9 | `check UnderwrittenSignedInFull` | where written lines fall short of the order at inception, every line is signed as written | A130 d10 | no counterexample | 4 Line, 8 Int |

**Motivating cases.** Each a `run` with a predicate that pins the instance, expected to find one,
confirming the design admits it. The README draws each instance.

| ID | Case | Shape |
|---|---|---|
| C4-R1 | a guarantee called on default | K2 from the facility to the guarantee |
| C4-R2 | ranking under an intercreditor agreement | K3 from the senior to the junior facility |
| C4-R3 | mutual cross-default | two K2 relations in opposite directions, each reading the previous position |
| C4-R4 | an excess on exhaustion | K2 from the primary to the excess, same position |
| C4-R5 | two contracts sharing an aggregate | two instruments drawing one account owned by their ensemble, at one position |
| C4-R6 | two insurers each writing the primary and the excess in one contract | two instruments of two parts each, each excess part reading both primary parts, same position |
| C4-R7 | refused: two policies whose other insurance clauses each make it excess of the other | two K2 relations in opposite directions at the same position. Expected: an instance in which `admitted` is false |

**Finding probes.** Each a `run` that looks for a case ADR-A130 or ADR-A131 leaves undefined.
Expected: an instance, which is a finding. Each finding names the question it raises, for the
maintainer before acceptance.

| ID | Probe | What an instance means | Raised as |
|---|---|---|---|
| C4-F1 | lines to stand that together exceed the order | decision 10 does not say how to sign them | a new Ensemble question for ES-5 |
| C4-F2 | two draws of equal rank under `ldg:InPriorityOrder` at one account and position | the merge rule does not say how to break the tie | the Ledger plan's LG-Q3, refined before LG-2 |
| C4-F3 | an account drawn by instruments of two nested ensembles, where both contain every drawer | "their ensemble" names two | a clarification of ADR-A131 decision 5: the owner is stated by the account's definition, never inferred |
| C4-F4 | a scaled line that no integer states exactly | rounding is needed for signing | confirms LG-Q6 and ADR-A131 decision 6's rounding and residual, already decided |

**Reading the results.** Every result is recorded in the model's README with its command, scope,
outcome and duration, and every instance is read and explained, not only counted. A `check` with no
counterexample is evidence up to its scope, stated as such, never as a proof. A check that finds a
counterexample where none was expected is a defect in the model or in ADR-A130. The builder first
rules out the model (a missing fact, a wrong definition), records which it was, and if the ADR, stops
and reports it as a proposed amendment. The receipt is archived beside the README, and the Alloy
version and JAR digest stated.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| C4-01 | the model / `exec` / it loads and every command runs | model | + |
| C4-02 | C4-A1, A2, A4, A6 to A9 / `exec` / no counterexample at the stated scope | model | + |
| C4-03 | C4-A3 and C4-A5 / `exec` / an instance each, read in the README | model | + |
| C4-04 | C4-R1 to R6 / `exec` / an instance each, admitted | model | + |
| C4-05 | C4-R7 / `exec` / an instance, not admitted | model | - |
| C4-06 | C4-F1 to F4 / `exec` / each outcome recorded, with the question it raises | model | + |
| C4-07 | a seeded defect: remove the merge step, so drawers read each other / `exec` / C4-A4 finds a counterexample, then restored | model | - |
| C4-08 | a seeded defect: let a relation's endpoint lie outside its ensemble / `exec` / the `Endpoints` fact refuses it, shown by a `run` that finds no instance | model | - |
| C4-09 | the README / read / every result, the Alloy version, the JAR digest, the receipt | paper | + |
| C4-10 | the changed files / prose check / no semicolons in English text | L1 | + |

**One command,** from the repository root on machine R, with `ALLOY_JAR` set to the downloaded JAR:

```bash
mise exec -- java -jar "$ALLOY_JAR" exec tools/models/ensemble-composition/Ensemble.als
```

**Estimate:** 150k to 250k tokens, most of it in reading and explaining the instances.

**Not covered:** C5 (Ledger's arithmetic), C4c (admitted cycles, with ES-8), the locality lemma and the
composition law's proof (E4b), and evaluating real terms (B4b, CCS C12).

### C5: model ADR-A131 (Ledger) — not started

**Recommended before or alongside ADR-A131's acceptance.** Model account trees, draws, credits and
merge rules. Check that a draw on a path succeeds or fails whole, that availability is the least
remaining balance along the path, that a credit never raises a balance above its stated amount, that
the tree has no cycle, that each merge rule's postings sum to the amount shared after rounding and its residual
rule, and that draws proposed at one position give the same postings in every order. `run` the Ledger
plan's examples to confirm they are admitted. See the [Ledger plan](ledger.md).

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
Vocabulary ADR (the maintainer's decision, this track's job is the evidence for it). Any change under
`ontology/` (this track produces a model and a recommendation, not a merged ontology edit).
Eligibility's hierarchical-match addendum (`insurml-typing.md` §6.1's dependent follow-on),
until the Vocabulary ADR itself is accepted.
