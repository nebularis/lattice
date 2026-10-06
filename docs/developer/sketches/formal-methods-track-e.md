<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Track E: the prover programme (sketch)

**Unit:** [formal-methods](../plans/formal-methods.md) (epic), track E
**Status:** sketch, 2026-10-06. FM-D2 decided (ADR-A-FM2); the generation-direction question
remains, for the plan
**Follows:** track D's spike, closed by [ADR-A-FM1](../../architecture/decisions/ADR-A-FM1-formal-methods-prover-choice.md)
(Isabelle/HOL), evidenced by [formal-prover-experiment.md](../notes/formal-prover-experiment.md).
Theory home decided by [ADR-A-FM2](../../architecture/decisions/ADR-A-FM2-formal-methods-theory-home.md)
(`tools/proofs/`)
**Prover:** Isabelle2025-2/HOL (FM-D1)
**Reads with:** [formal-methods.md](formal-methods.md) §4 "Track E" and §7 (FM-D2, FM-D4), the
[adequacy and architecture sketch](formal-adequacy-and-architecture.md)

## 1. What changes from the spike

Track D's theories (`spikes/formal-prover/isabelle/Kernel.thy`, `Eligibility.thy`) hand-restate
the kernel and Eligibility's set readings directly in Isabelle syntax, built to compare two
provers, not to be the normative theory. Track E mechanises the real thing, under two rules the
epic already states and the spike did not need to follow:

- **E1 (epic principle):** "the theory's closed datatypes are generated from [the literate
  README]. Laws in the theory are hand-written, with their statements extracted back into it."
  The spike's `datatype decision = Permitted | Denied | Undetermined` was hand-written both ways.
  Track E needs the generation direction working before its proofs can be called the real thing
  rather than a second hand copy of the README's prose, same as the spike's.
- **FM-D2 (decided, ADR-A-FM2):** where track E's theories and build project live. Not `spikes/`,
  which this epic's plan (§7.1) and the repository topology rules (`copilot-instructions.md`)
  only allow for an unmerged spike branch. Decided: a new `tools/proofs/`, one subdirectory per
  layer, mirroring `ontology/<layer>/`'s own names.

The generation direction (which tool, not yet decided, see §4) remains the open question this
sketch exists to narrow, closed by the plan that follows this sketch, not here.

## 2. Scope, restated from the epic plan (§4)

| Slice | Target | Depends on |
|---|---|---|
| E1 | the kernel (TA1, TA2, as the spike proved them, now README-sourced), the rounding and residual theorem (Quantification), and binding resolution | the generation direction (§1), and binding resolution's design-time model (track C, C2), which does not exist yet |
| E2 | the Eligibility denotation and one SPARQL compiler core, "not a value" mapping to Undetermined as its first theorem, a fragment gate, a cross-store conformance suite | E1, track B's reference (B1, B2) for differential evidence |
| E3 | the combinator algebra | E1, E2 |
| E4 | the evaluation context, mechanising track B4's reference | B4 |
| E5 | the template library in rely and guarantee form | E1 to E4, track G's property language (FM-D7) |

E1 is the first slice to plan in detail (this sketch's §4). E2 to E5 stay at the epic's existing
outline level until E1 is underway.

## 3. What "the rounding and residual theorem" and "binding resolution" need, that the spike did not

Both are named in the epic plan's E1 outline without restating their content here, deliberately:

- **The rounding and residual theorem** is Quantification's. Its precise statement needs sourcing
  from `ontology/quantification/README.md` and ADR-A93 to ADR-A95 (derived rate spaces, calendar
  binding, alternative bounds) before it can be formalised, not guessed at in a sketch.
- **Binding resolution** is the subject of CCS's HQ-4 and IMA-D4a, and the epic's own track C (C2)
  models it at design time, ahead of CCS C8, before track E mechanises it. Track C has not started.
  E1's binding-resolution theorem should not be drafted ahead of C2's model: a proof assistant
  mechanising a semantics that is still being decided at design time risks proving the wrong
  thing precisely, which is a worse outcome than not proving it yet.

**Consequence for sequencing:** E1 splits into parts with different readiness, not one slice
started all at once (the plan, §4, below).

## 4. Open questions, for the plan

| # | Question | Candidates |
|---|---|---|
| generation direction | extend `tools/literate_extract.py` with an Isabelle-datatype fenced-block kind (parallel to its `turtle-spec`/`turtle-vocab`/`turtle-shapes` blocks), or a separate generator | `literate_extract.py`'s existing block/file-count contract (one block per generated file, in document order) is proven infrastructure; reusing its shape is the lower-risk default unless Isabelle's datatype syntax does not fit it |
| image route | Isabelle has no container image in this spike (deferred, human instruction, 2026-10-06, to conserve tokens) | build one before E1's claims are recorded, per epic E9's "only an image route's verdict is recorded", or accept native-only evidence for E1 specifically and revisit before gate E |
| binding resolution's timing | start E1's kernel and rounding/residual parts now, defer binding resolution until track C's C2 model exists | do the two independent parts first (§3), track C's timing decides the third |

## 5. Compatibility with the improved-ontology-documentation sketch

A separate, unplanned sketch (`docs/developer/sketches/improved-ontology-documentation.md`,
2026-10-02) proposes injecting README narrative into generated `.ttl` files' own annotation
properties, via a new pair of HTML-comment markers, and floats removing generated `.ttl` from git
entirely, generating it at bootstrap instead. Track E is not adopting it (out of scope, not this
epic's decision to make), but ADR-A-FM2 confirms the two are compatible, not competing:

- The comment-marker mechanism is **orthogonal** to the fenced-code-block mechanism
  `literate_extract.py` already uses and that track E's own generation direction (§4, above) will
  extend or parallel: one demarcates narrative prose for an annotation property, the other
  demarcates a block of normative syntax (Turtle today, Isabelle once E1.0 decides how). Adopting
  one does not require touching the other, and nothing E1.0 does should assume README prose
  **outside** fenced blocks is free of such markers later: an Isabelle-block generator should skip
  HTML comments the same way a Turtle-block generator would need to, not choke on them.
- If the "remove generated `.ttl` from git" idea is ever taken up, it is a repository-wide
  reproducibility change far larger than track E and deserves its own ADR regardless; track E's
  own generated `tools/proofs/<layer>/*.thy` should be designed to tolerate that outcome without
  rework (generated from the README on demand, not hand-maintained), which E1.0's generation
  direction already requires for its own reasons (epic principle E1).
- The sketch's own nested-marker example has a real ambiguity worth fixing before anyone
  implements it (an inner `exclude` block reuses its enclosing block's `id` rather than a distinct
  one, relying on the end marker's proximity to resolve which block closes): not a reason to avoid
  the idea, a reason its own eventual implementation should settle on stack-based nesting (no id
  matching needed to close the innermost open marker) rather than id-matched pairs once ids can
  repeat.

## 6. Non-goals, unchanged from the epic

`DesignEnv`/`RunEnv` and Behaviour's macrostep (track B4, not yet built). Instrument assurance
(track G). Any native-tooling decision (track F). Binding resolution's own design-time model
(track C's job, not track E's, though E1 consumes its output).
