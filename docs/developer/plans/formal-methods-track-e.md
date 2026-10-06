<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Formal Methods, Track E: the prover programme

**Unit ID:** `formal-methods-track-e`
**Unit type:** Phase (Epic Decomposition Model, `copilot-instructions.md`)
**Epic:** [formal-methods](formal-methods.md)
**Sketch:** [formal-methods-track-e.md](../sketches/formal-methods-track-e.md)
**Status record:** [formal-methods-track-e.md](../status/formal-methods-track-e.md)
**Decided by:** [ADR-A-FM1](../../architecture/decisions/ADR-A-FM1-formal-methods-prover-choice.md)
(FM-D1: Isabelle/HOL; FM-D10: Haskell and Scala as code-generation targets),
[ADR-A-FM2](../../architecture/decisions/ADR-A-FM2-formal-methods-theory-home.md)
(FM-D2: `tools/proofs/`)
**Status:** E1.0 done. E1.1 (the kernel, for real) done alongside it. E1.2 (rounding/residual)
and E1.3 (binding resolution) not started; E1.3 waits on track C's C2

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
are reused as-is from `spikes/formal-prover/`; they move to `tools/proofs/` (ADR-A-FM2) rather
than being rewritten.

## 2. What this plan depends on, and what blocks it

| Dependency | State | Blocks |
|---|---|---|
| FM-D2 (home of track E's theories) | **decided and done: `tools/proofs/`, one subdirectory per layer** (ADR-A-FM2) | nothing further |
| the literate-generation direction for Isabelle datatypes | **decided and done:** `isabelle-spec` fenced blocks, extending `tools/literate_extract.py` additively (new `--proofs-root` argument; every existing Turtle invocation unaffected) | nothing further |
| track C's C2 (binding resolution, design-time model) | not started | E1.3 (binding resolution) specifically. E1.1 and E1.2 do not depend on it |
| the Quantification layer's rounding/residual statement | exists in prose (`ontology/quantification/README.md`, ADR-A93 to ADR-A95), not yet read against this plan | E1.2's exact theorem statement, drafted when E1.2 starts, not guessed at here |
| an Isabelle image | does not exist in this spike (deferred, human instruction, 2026-10-06, confirmed again for E1: native/local route only) | epic E9's "only an image route's verdict is recorded" rule, and gate D's own smoke-suite criterion. Track E proceeds on native evidence; closing this before claims are recorded for gate E, not gate D, is the human's call to make when it is needed |

## 3. Slices

### E1.0: home and generation tooling (prerequisite, not in the epic's own numbering) — done

- `tools/proofs/` scaffolded: `README.md`, `gate.py` and `claim-schema.json` carried over
  unchanged in design from `spikes/formal-prover/` (PF1's fix included), `check.py` (builds every
  layer's Isabelle session natively and runs the gate), and a `check:proofs` `mise` task. No
  Python package here (there is nothing to `pip install`): the native Isabelle install
  `bootstrap:formal-native-isabelle` already provides is reused as-is.
- Generation direction decided and implemented: `tools/literate_extract.py` gained a new
  `isabelle-spec` fenced-block kind (parallel to `turtle-spec`), a `--proofs-root` argument, and
  an Isabelle-style SPDX header, entirely additively (every existing Turtle invocation, re-run
  unchanged, confirmed byte-for-byte identical: Surface, Wording and Behaviour's own `--check`
  calls still pass). Proven on the smallest case first: `ontology/eligibility/README.md` §10
  (new) now carries the `isabelle-spec` block that generates
  `tools/proofs/eligibility/Kernel.thy`'s closed `datatype decision = Permitted | Denied |
  Undetermined`, nothing else. Eligibility's own pre-existing `spec`/`vocab`/`shapes` drift
  (TD-16) was left untouched: only the new `@proofs-root@/…` output was written, not the whole
  plan() result, so this work does not silently "fix" debt that belongs to its own unit.
- `spikes/formal-prover/isabelle/{Kernel,Eligibility,Adequacy}.thy`'s proof *content* moved into
  `tools/proofs/eligibility/`, split so the generated file is never hand-edited: `Kernel.thy`
  (generated, datatype only), `KernelLaws.thy` (hand-written: `decision_leq`, `or3`, `and3`,
  `neg3`, TA1, TA2 — everything the spike's `Kernel.thy` had besides the datatype declaration
  itself), `Eligibility.thy` (hand-written: `some_value`, `every_value`, TL1 to TL3, re-pointed at
  `KernelLaws` instead of a self-contained `Kernel`), `Adequacy.thy` (unchanged, 15 fixture
  checks). Claim records and digests carried over: byte-identical to the spike's, since the
  moved content is verbatim.
- **Validated:** the generated datatype and the spike's hand-written one are isomorphic (same
  three constructors, same names, confirmed by inspection — they are the same line of text).
  `isabelle build -d tools/proofs/eligibility Eligibility` compiles clean (native route, per the
  human's instruction to use native/local, not an image). `python tools/proofs/gate.py
  tools/proofs/eligibility` passes: AQ, TA1, TA2, TL1-some, TL1-every, TL2, TL3a, TL3b all
  `passed`, no digest mismatch, no banned marker.

### E1.1: the kernel (TA1, TA2), for real — done, folded into E1.0 above

Given E1.0's and E1.1's validation criteria turned out to need the same artefacts (the kernel's
proofs had to exist, against the generated datatype, for E1.0's own "moved proofs still compile"
criterion to mean anything), both were completed in one pass rather than two. Restated exactly as
track D proved them, including the TA2 correction (negation is monotone, not order-reversing).
Claim records match track D's own evidence, not merely a close port of it: identical statement
digests.

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
