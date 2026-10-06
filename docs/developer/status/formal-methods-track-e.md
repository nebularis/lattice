<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Formal Methods, Track E: Status

**Unit ID:** `formal-methods-track-e` (phase, within the `formal-methods` epic)
**Status:** Not started. Plan and sketch written 2026-10-06; FM-D2 decided the same day
(ADR-A-FM2, `tools/proofs/`). E1.0 may now begin
**Last updated:** 2026-10-06
**Plan:** [formal-methods-track-e.md](../plans/formal-methods-track-e.md)
**Sketch:** [formal-methods-track-e.md](../sketches/formal-methods-track-e.md)
**Epic status:** [formal-methods.md](formal-methods.md)
**Decided by:** [ADR-A-FM1](../../architecture/decisions/ADR-A-FM1-formal-methods-prover-choice.md),
[ADR-A-FM2](../../architecture/decisions/ADR-A-FM2-formal-methods-theory-home.md)

## Current position

Track D closed with FM-D1 decided (Isabelle/HOL). FM-D2 is now decided too: track E's theories
live under `tools/proofs/`, one subdirectory per layer. Track E has not started coding. Its plan
splits E1 (the epic's first slice: kernel, rounding/residual theorem, binding resolution) into
three parts of different readiness, plus a prerequisite part (E1.0, home and generation tooling)
the epic's own numbering does not name separately.

**Next action, for the human:** confirm E1.0 should start (scaffolding `tools/proofs/`, and
deciding the generation-direction question: extend `tools/literate_extract.py`, or a separate
generator), since that is new tooling work on a script other layers depend on.

## Slices

| Slice | State | Blocked on |
|---|---|---|
| E1.0 (home, generation tooling) | not started, unblocked | nothing; awaiting the human's go-ahead to start |
| E1.1 (the kernel, for real) | not started | E1.0 |
| E1.2 (rounding and residual theorem) | not started | E1.0. Its exact statement is not yet sourced from `ontology/quantification/README.md` and ADR-A93 to ADR-A95 |
| E1.3 (binding resolution) | not started | E1.0, and track C's C2 (design-time model), which has not started either |
| E2 to E5 | not started, outline only | E1 |

## Open questions

| # | Question | Owner |
|---|---|---|
| generation direction | extend `tools/literate_extract.py`, or a separate generator, for Isabelle datatypes | E1.0, when it starts |
| the Isabelle image | does not exist in this spike; needed before epic E9's "image route only" rule applies to track E's recorded claims, not necessarily before E1 starts on native evidence | human, timing deferred 2026-10-06 to conserve tokens |

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
