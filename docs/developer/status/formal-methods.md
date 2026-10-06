<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Formal Methods: Status

**Unit ID:** `formal-methods` (epic)
**Status:** � Track D in progress. D0-D2 complete on `fm/phase-0-prover-spike`, D3 (Isabelle) and D4
(report) remain
**Last updated:** 2026-10-06
**Plan:** [formal-methods.md](../plans/formal-methods.md), [the prover spike](../plans/formal-methods-phase-0.md)
**Review response:** [formal-methods-review-response.md](../notes/formal-methods-review-response.md)
**Sketches:** [formal-methods.md](../sketches/formal-methods.md),
[adequacy and architecture](../sketches/formal-adequacy-and-architecture.md),
[assurance records](../sketches/assurance-records.md),
[instrument assurance](../sketches/instrument-assurance.md),
[reference evaluator](../sketches/reference-evaluator.md),
[toolchain workers](../sketches/formal-toolchain-workers.md)

## Current position

Nothing is built. The prover spike (track D) is the first step. The tracks are staggered: C1, C2, B1
and B2 alongside the spike, A1 to A4 after gate D, B4 with C11a and C12, C3 with C13a. CCS remains the active unit, with C7c branched.

**Next action, for the human:** decide FM-D16 (how tools run on each host), decide when and where the
spike branch, `fm/phase-0-prover-spike`, is created, and approve the image builds and any native
installs.

## Track board

| Track | State | Blocked on |
|---|---|---|
| D Prover spike | not started | the branching decision, toolchain installs |
| A Ledger and harness | not started | gate D, then its ADR (A1). A5 runs with track C |
| B Reference semantics and oracle | not started | its ADR. B1 and B2 alongside the spike, B4 with C11a and C12 |
| C Design-time models | not started | none. C1 and C2 first, before CCS C8 |
| E Prover programme | not started | gate D |
| F Native tooling | not started | its ADR, then a Python baseline per family |
| G Instrument assurance | not started | B4, C3 |

## Track D

| Slice | State |
|---|---|
| D0 environments | done (commit `efa2469`): image and native routes, driver, network probe, smoke suite |
| D1 brief | done (commit `bb86f17`): written semantics, seeded defects S1-S5, MINOR change spec, measures |
| D2 Rocq track | done (commits `f4a6db4`, `17f05d9`, `57fea56`, `ca6fbc0`): Kernel.v (TA1, TA2), Eligibility.v (TL1-TL3), Adequacy.v (13 fixture-matching theorems, all via `reflexivity`), defects S1-S5 (each a compiled, positive detection, not a narrative), Reading.v (the MINOR change, M3 measured at +21/-7 lines for adding `MostValueR`), Interface.v (M6's `MonotoneReading` record, rejects non-monotone candidates at construction), Extraction.v (M4, extracted OCaml kernel checked against all 15 reference fixtures outside Rocq), 12 claim records, `gate.py rocq` passes clean |
| D3 Isabelle track | not started |
| D4 report | not started |

## Decisions

| # | State |
|---|---|
| FM-D1 | open, settled by track D, or the prover abandoned |
| FM-D5, FM-D7, FM-D9 | revised 2026-10-06 after review |
| FM-D11, FM-D12, FM-D13 | decided 2026-10-06, as recommended |
| FM-D15 | decided 2026-10-06: stale on a tool change, suspect on a known soundness fix, invalid on a semantic change. Needs an ADR-A27 addendum |
| FM-D14 | open |
| FM-D16 | open: the image route everywhere for recorded work, native installs for authoring only |
| the rest | open |

## Log

- 2026-10-06: epic, sketches and the prover experiment drafted.
- 2026-10-06: reviewed. Five headline findings accepted. The epic re-sequenced into tracks A to G with
  metrics and abandonment conditions. The spike narrowed to the kernel and L15 and L16 carried end to
  end. Six points rebutted or refined in the review response, four of them for the human's decision.
- 2026-10-06: FM-D11 (stratified Datalog), FM-D12 (generation from the README) and FM-D13 (L15 and L16 in the spike) decided as recommended. FM-D15's addendum belongs to ADR-A27, the invalidation rule, with the read-set kinds in ADR-A92's terms
- 2026-10-06: FM-D15 decided: a semantic input change invalidates, a tool identity change marks claims stale and schedules re-verification, and a known soundness fix marks them suspect, failing the gate until re-verified
- 2026-10-06: tracks staggered: C1, C2, B1 and B2 alongside the spike, A1 to A4 after gate D (A5 with C), B4 with C11a and C12, C3 with C13a
- 2026-10-06: a toolchain spike on a Windows host without administrator rights, behind a TLS-re-signing proxy, ran both stacks natively and in Linux containers: proofs, code generation, compilation, AST reading and cross-compilation all passed. The plans now run on macOS, Windows and Linux: an image route for every recorded check and job, slim, multi-arch, pinned and capped, native installs for authoring only (epic E9, §4 Environments, FM-D16), and slice D0 for environments in track D

## Estimates and actuals

| Track | Estimate (tokens) | Actual |
|---|---|---|
| D | 0.3M to 0.6M | |
| sketches, plans and the review response (2026-10-06) | not estimated | not recorded |
