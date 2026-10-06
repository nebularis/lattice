<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Formal Methods, Track E: Status

**Unit ID:** `formal-methods-track-e` (phase, within the `formal-methods` epic)
**Status:** E1.0 and E1.1 done, 2026-10-06, native route only (human instruction). E1.2
attempted and found blocked on a missing normative source, not merely unstarted (see Log). E1.3
not started
**Last updated:** 2026-10-06
**Plan:** [formal-methods-track-e.md](../plans/formal-methods-track-e.md)
**Sketch:** [formal-methods-track-e.md](../sketches/formal-methods-track-e.md)
**Epic status:** [formal-methods.md](formal-methods.md)
**Decided by:** [ADR-A-FM1](../../architecture/decisions/ADR-A-FM1-formal-methods-prover-choice.md),
[ADR-A-FM2](../../architecture/decisions/ADR-A-FM2-formal-methods-theory-home.md)

## Current position

Track D closed with FM-D1 decided (Isabelle/HOL). FM-D2 is decided and acted on: track E's
theories live under `tools/proofs/`, one subdirectory per layer. `tools/proofs/eligibility/` now
exists: `Kernel.thy` generated from `ontology/eligibility/README.md`'s new `isabelle-spec` block
(§10), `KernelLaws.thy`/`Eligibility.thy`/`Adequacy.thy` hand-written (ported from track D's
spike, byte-identical statement digests), `gate.py`/`claim-schema.json` carried over, a
`check.py` driver and a `check:proofs` `mise` task. `isabelle build` and `gate.py` both pass,
native route (`spikes/formal-prover/env/driver.py --route native`); no Isabelle image exists, by
design (deferred).

**Next action, for the human:** E1.2 was attempted and found blocked on something more
fundamental than sourcing a citation (see below): `split`/`proRata`/the rounding-residual rule
have no normative ontology declaration anywhere, in Quantification or elsewhere. Decide where
they are specified and under which ADR before this resumes, or redirect to track C's C2 (to
unblock E1.3) or to E2 preparatory reading instead.

## Slices

| Slice | State | Blocked on |
|---|---|---|
| E1.0 (home, generation tooling) | **done** | nothing |
| E1.1 (the kernel, for real) | **done**, folded into E1.0's pass | nothing |
| E1.2 (rounding and residual theorem) | **blocked, not merely unstarted** (see Log) | no normative source exists for `split`/`proRata`/the rounding-residual rule anywhere under `ontology/`. Needs a design-time decision (and likely an ADR) before any proof is attempted |
| E1.3 (binding resolution) | not started | track C's C2 (design-time model), which has not started either |
| E2 to E5 | not started, outline only | E1 |

## Open questions

| # | Question | Owner |
|---|---|---|
| where `split`/`proRata`/the combinator algebra are specified normatively | a new Quantification section, a new layer, or folded into Behaviour's evaluation context; `sketches/formal-methods.md` §8.1 places the rounding/residual theorem with the kernel, §9.2 places it with the combinator algebra (epic track E3), which do not obviously agree on which track owns E1.2's theorem | human |
| the Isabelle image | does not exist; needed before epic E9's "image route only" rule applies to track E's recorded claims, not before E1 itself | human, timing deferred 2026-10-06 to conserve tokens, confirmed again when E1 started (native/local explicitly requested) |

## Log

- 2026-10-06: sketch and plan written, following track D's close and ADR-A-FM1. E1 split into
  E1.0 (home and generation tooling, a prerequisite the epic's numbering does not name), E1.1 (the
  kernel), E1.2 (rounding and residual, Quantification), and E1.3 (binding resolution, blocked on
  track C's C2). No code written yet.
- 2026-10-06: FM-D2 decided (ADR-A-FM2): `tools/proofs/`, one subdirectory per layer, not beside
  each layer under `ontology/` and not named `tools/formal/`. The attached
  `improved-ontology-documentation.md` sketch (README narrative into generated `.ttl` annotations)
  was reviewed for compatibility: confirmed orthogonal to track E's own generation (a separate
  extraction target from the same README, fenced-code-block generated, not HTML-comment
  generated), not adopted, no plan or slice opened for it. E1.0 unblocked; still needs the
  human's go-ahead to actually start, and its own generation-direction question decided when it
  does.
- 2026-10-06: E1.0 and E1.1 done, native route only (human instruction, explicit for this slice).
  `tools/literate_extract.py` gained an `isabelle-spec` fence tag and `--proofs-root`, purely
  additively (Surface/Wording/Behaviour's existing `--check` invocations re-run unchanged and
  pass, confirming no regression). `ontology/eligibility/README.md` §10 (new) states the closed
  `decision` datatype; `tools/proofs/eligibility/Kernel.thy` is generated from it.
  `KernelLaws.thy`/`Eligibility.thy`/`Adequacy.thy` are hand-written, ported from
  `spikes/formal-prover/isabelle/` with identical statement digests (TA1, TA2, TL1-some,
  TL1-every, TL2, TL3a, TL3b, AQ). `tools/proofs/gate.py` (PF1's fix carried over) passes.
  Eligibility's pre-existing `spec`/`vocab`/`shapes` drift (TD-16) was left untouched on purpose:
  only the new generated output was written. `check:proofs` wired into `mise.toml`, outside the
  default aggregate `check` task (same "large, explicit" convention as the formal-prover D0
  tasks), since Isabelle is a heavy native toolchain not every host has installed.
- 2026-10-06: E1.2 attempted. Searched `ontology/quantification/README.md` and ADR-A93 to
  ADR-A95 directly (not guessed at): neither names `split`, `proRata`, or any rounding/residual-
  allocation rule. Quantification's only rounding-related content is `qnt:roundingPolicy`, a
  property whose own README already lists it as having no declared vocabulary yet. Searched all
  of `ontology/` for `proRata`: zero matches, in any layer, under any name. The theorem exists
  only in two epic sketches, which do not agree on which track owns it
  (`sketches/formal-methods.md` §8.1 places it with the kernel, §9.2 places it with the
  combinator algebra the epic plan assigns to E3). Not drafted: formalising an operation with no
  design-time decision behind it risks fixing its design inside a proof, the same risk already
  held E1.3 back for binding resolution. Plan and this record both updated; the human's decision
  is needed on where it is specified and under which ADR before this resumes.
