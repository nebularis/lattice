<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A-FM3: Home and scope of the reference evaluator and its oracle

**Status:** Accepted
**Date:** 2026-10-07
**Related:** [ADR-A-FM1](ADR-A-FM1-formal-methods-prover-choice.md) (prover choice, Isabelle/HOL),
[ADR-A-FM2](ADR-A-FM2-formal-methods-theory-home.md) (home of track E's theories, `tools/proofs/`),
the formal-methods epic plan, [the Track B sketch](../../developer/sketches/formal-methods-track-b.md)
and [plan](../../developer/plans/formal-methods-track-b.md),
[ADR-A77](ADR-A77-repository-topology-and-documentation-governance.md) (repository topology)
**Unit:** [`formal-methods`](../../developer/plans/formal-methods.md) (epic), track B

## Context

The epic plan's own dependency table (§3) names "its ADR" as track B's prerequisite, the same
shape as track A's A1 — unlike track C, whose dependency is "none" and whose design-time models'
home (`tools/models/`) was decided directly in that track's own plan, with no ADR of its own.
Track B needs one because its artefact is a new kind this epic has not produced before: a
hand-written Python oracle, checked by differential and property test, never generated and never
proved. The epic now has three kinds of artefact under three different relationships to a layer's
literate README, and track B's ADR is where the third is named and told apart from the other two:

1. **Generated** (`tools/proofs/`, ADR-A-FM2): a theory's closed datatypes are mechanically
   extracted from a README's fenced `isabelle-spec` blocks (epic principle E1). The laws built on
   top are hand-written, but the kernel datatype itself is never hand-edited.
2. **Hand-written, not tied to any README's generation mechanism at all** (`tools/models/`, track
   C): a design-time model (Alloy, SMT) stating a proposed law precisely enough to check it before
   an ADR commits to it. Nothing in it is generated, and nothing in it is proved — it is evidence
   for a decision not yet made.
3. **Hand-written, faithful to an already-accepted law, verified by test** (this ADR's subject):
   a Python function restating a law `ontology/<layer>/README.md` already states as accepted
   prose (Eligibility's L9-L16 today), checked by differential and property test against both the
   law's own worked examples and whatever compiles or implements the same law independently
   (`tools/mork_compilers` today). Unlike (1), nothing here is mechanically generated: B1's
   `kernel.py` is a port of an existing Isabelle theory's statements (`tools/proofs/eligibility/
   KernelLaws.thy`), read and restated by hand, not derived from it by any tool. Unlike (2), it
   does not propose a law — Eligibility's L9-L16 are already accepted — it restates one
   independently enough that a shared mistake in every compiler backend has something else to
   disagree with (reference-evaluator.md §1).

No candidate location was seriously contested for this one, unlike ADR-A-FM2's two live options:
the repository topology rules' own division (`tools/` for "executable reference implementations
and developer-facing toolchains", `ontology/` for semantic assets only) places a test-verified
Python oracle under `tools/` without argument, the only open question being what to name it and
how far its first ADR's scope should reach.

## Decision

**The reference evaluator and its oracle live under a new top-level toolchain directory:
`tools/reference/`.** Not `tools/oracle/` (the reference-evaluator sketch's own vocabulary
throughout is "reference", with "oracle" as the role it plays for differential testing, not its
name) and not folded into `tools/mork_compilers` (which compiles Eligibility conditions into
backends; this package is independent of every backend, by design, and folding it in would make
that independence a matter of directory layout instead of a stated fact).

1. `tools/reference/<layer>/` mirrors `ontology/<layer>/`'s own layer names, the same convention
   `tools/proofs/<layer>/` and `tools/models/<name>/` already use. `tools/reference/eligibility/`
   is the first and only subdirectory this ADR authorises; a second layer's reference gets its own
   subdirectory when a later slice needs one, additive, never a parallel tree every layer must
   populate.
2. **Scope for this ADR: B1, B2 and B3 only** (Eligibility's kernel and denotation, differential
   tests against `tools/mork_compilers`, and Surface's regeneration-as-naturality property test —
   the formal-methods-track-b.md plan's own slices). **B4** (the evaluation-context reference,
   `DesignEnv`/`RunEnv`, the rounding and residual rule, CCS C12's conformance kit) is explicitly
   out of scope: CCS's C12 is not yet briefable (confirmed by reading `main` directly, track B's
   sketch §6), and deciding B4's shape now would mean guessing at a CCS slice this epic does not
   own. B4 gets its own ADR extension, or its own ADR, when that dependency clears.
3. **Restates E3** (no generated OCaml or Haskell runs against the live graph): the reference
   evaluator is not generated, but the same principle holds of it unmodified — it is a test-time
   oracle, imported only by this package's own tests and by differential/property test suites,
   never by a runtime path. A later slice adding a production import of `tools/reference/` is a
   new architectural decision, not a consequence of this one.
4. **Restates E1** (the literate README stays the one normative source): a `tools/reference/<layer>/`
   module's docstring states the law it implements close enough in wording to
   `ontology/<layer>/README.md`'s own that a reviewer can align the two by inspection, the
   discipline `tools/proofs/eligibility/`'s own `.thy` files already use. Nothing under
   `tools/reference/` amends or restates a law with different content than its README already
   carries — a finding that the README and the reference disagree is a defect in whichever is
   wrong, not a silent amendment by this package.
5. **Numbering**: continues the non-colliding `A-FM` block (`ADR-A-FM3`), for the reason
   ADR-A-FM1 and ADR-A-FM2 already give: this epic's branch and the concurrently active
   CCS/insurml-alignment work on `main` both draft ADRs in real time, and a plain next free number
   would collide on merge.

## Consequences

- Track B's plan is unblocked for B1: its ADR dependency (epic plan §3) is satisfied once this is
  accepted, and B1's own first action (drafting this ADR) is complete.
- Root `README.md` gains an entry for `tools/reference/` once B1 creates it (repository topology
  governance: "any new structure/folders/projects must be documented" there), not by this ADR
  itself, which creates no files under `tools/`.
- `tools/mork_compilers`, `tools/surface` and `tools/mork` are unaffected: `tools/reference/`
  depends on reading their public interfaces for differential testing (B2) and wraps their own
  code in a property test (B3), but changes nothing in them. A disagreement B2 or B3 finds is a
  finding for those packages' own maintainers, handled in their own slice (track B sketch §7).
- B4's ADR extension, when CCS's C12 clears, inherits this ADR's home and E1/E3 restatements
  without needing to re-argue them; it adds only what B4's own scope needs (`DesignEnv`/`RunEnv`,
  the conformance kit's shape).
