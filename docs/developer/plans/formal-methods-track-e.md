<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Formal Methods, Track E: the prover programme

**Unit ID:** `formal-methods-track-e`
**Unit type:** Phase (Epic Decomposition Model, `copilot-instructions.md`)
**Epic:** [formal-methods](formal-methods.md)
**Sketch:** [formal-methods-track-e.md](../sketches/formal-methods-track-e.md)
**Status record:** [formal-methods-track-e.md](../status/formal-methods-track-e.md)
**Decided by:** [ADR-A-FM1](../../architecture/decisions/ADR-A-FM1-formal-methods-prover-choice.md)
(FM-D1: Isabelle/HOL; FM-D10: Haskell and Scala as code-generation targets)
**Status:** Proposed. E1's first two parts (kernel, rounding/residual) can start once FM-D2 is
decided; its third part (binding resolution) waits on track C's C2

## 1. Scope

Mechanise, in Isabelle/HOL, the formal-methods programme the epic names for track E (`formal-
methods.md` §4): the logic kernel with the rounding and residual theorem and binding resolution
(E1), the Eligibility denotation with one proved SPARQL compiler core (E2), the combinator
algebra (E3), the evaluation context mechanising track B4's reference (E4), and the template
library in rely and guarantee form (E5). This plan details E1 only; E2 to E5 stay at the epic's
outline level until E1 is underway, per the Epic Decomposition Model's rolling-wave rule.

Every artefact follows the chain track D proved out (phase-0 plan §2.1): prose, shape, formal
statement (extracted back into the README), proof with its assumption audit, an interface one
instantiation discharges, adequacy against a reference, the compiled backend, a claim record, a
report and a gate. The claim schema, `gate.py` (now fixed, PF1) and the GATE-marker convention
are reused as-is from `spikes/formal-prover/`; they move to track E's permanent home (FM-D2)
rather than being rewritten.

## 2. What this plan depends on, and what blocks it

| Dependency | State | Blocks |
|---|---|---|
| FM-D2 (home of track E's theories) | open, an ADR decision (sketch §4) | every slice: nothing is created in a permanent home until this is decided |
| the literate-generation direction for Isabelle datatypes | open, a design choice within FM-D2's ADR or a follow-up (sketch §1, §4) | E1.1's kernel datatype must be generated from the README, not hand-restated, to honour epic principle E1 |
| track C's C2 (binding resolution, design-time model) | not started | E1.3 (binding resolution) specifically. E1.1 and E1.2 do not depend on it |
| the Quantification layer's rounding/residual statement | exists in prose (`ontology/quantification/README.md`, ADR-A93 to ADR-A95), not yet read against this plan | E1.2's exact theorem statement, drafted when E1.2 starts, not guessed at here |
| an Isabelle image | does not exist in this spike (deferred, human instruction, 2026-10-06) | epic E9's "only an image route's verdict is recorded" rule, and gate D's own smoke-suite criterion. Track E may proceed on native evidence for now; closing this before claims are recorded for gate E, not gate D, is the human's call to make when it is needed |

## 3. Slices

### E1.0: home and generation tooling (prerequisite, not in the epic's own numbering)

- Write the FM-D2 ADR (`A-FM2`, continuing ADR-A-FM1's series): choose the home (sketch §4's two
  candidates) and record the reasoning the sketch could not close unilaterally.
- Extend the literate-extraction tooling (`tools/literate_extract.py` or a sibling script) with
  whatever block kind the chosen home needs to generate the kernel's datatype from its README,
  proven first on the smallest possible case (the three-valued `decision` type itself, which
  track D's spike already states in prose terms the README can carry almost unchanged).
- Move `spikes/formal-prover/isabelle/{Kernel,Eligibility}.thy`'s proof *content* (not their
  hand-written datatypes) into the new home, re-pointed at the generated datatype.
- **Validation:** the generated datatype and the hand-written one from the spike are isomorphic
  (same constructors, same names), and the moved proofs still compile against the generated
  version unchanged. This closes the loop the spike left open rather than opening a new one.

### E1.1: the kernel (TA1, TA2), for real

- Restate TA1 and TA2 exactly as track D proved them (including the TA2 correction recorded in
  the brief and this spike's commit history: negation is monotone, not order-reversing), against
  the generated datatype from E1.0.
- **Validation:** a claim record per theorem, `gate.py` passing against the new home, and the
  assumption audit clean, matching track D's own evidence exactly (this part is expected to be
  close to a straight move, not new mathematics).

### E1.2: the rounding and residual theorem (Quantification)

- Source its exact statement from `ontology/quantification/README.md` and ADR-A93 to ADR-A95
  before drafting anything: this plan does not restate it, since guessing at a theorem's content
  ahead of reading its normative source is exactly the restatement risk the no-unreviewed-
  restatement rule exists to catch.
- **Validation:** TBD when this part starts, following the same chain as E1.1.

### E1.3: binding resolution

- **Blocked on track C's C2** (design-time model of scheme composition, ahead of CCS C8). Do not
  start this part before C2 exists: mechanising a semantics still being decided at design time
  risks proving the wrong thing precisely, which the epic's own track ordering (C before E for
  this reason) already guards against.
- **Validation:** TBD, including differential evidence against C2's model once it exists.

## 4. Test taxonomy and evidence

Proof is its own evidentiary category, not a position on the `copilot-instructions.md` L0-L8
taxonomy: a theorem's claim record (`method: Proof`) and `gate.py`'s report are the unit of
evidence, as track D established. Where a slice also produces compiled, running code (E2's SPARQL
compiler core, in particular), that code's conformance suite does sit on the L0-L8 scale (L3
contract tests against the fragment gate, L4/L5 against a real store), and both kinds of evidence
are named in that slice's own Validation Pack when it is written, not merged into one count here.

## 5. Out of scope

Everything the epic already excludes (§10): running generated code against the live graph, Lean 4,
timed automata, verifying third-party engines. `DesignEnv`/`RunEnv` and Behaviour's macrostep
(track B4, E4's dependency, not yet built). Instrument assurance (track G). Scala's actual
exercise from Isabelle's `export_code` (FM-D10 adopted it; proving it out is near-term follow-up
work, not part of E1's own validation).
