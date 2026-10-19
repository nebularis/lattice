<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Phase 2 — Ingestion and Query Planes (Sketch)

**Unit type:** Phase (of Epic `lattice-platform-development`)
**Unit ID:** `phase-2`
**Promotes to:** [phase-2-plan.md](../plans/phase-2-plan.md)
**Status record:** [phase-2-status.md](../status/phase-2-status.md)
**Depends on:** [phase-1](phase-1-sketch.md) exit gate

## Why this chunk is deliberately light

The epic states its own methodology plainly (Part 0.5, rolling-wave detail): "Phases 2–4 are specified at slice granularity but with lighter test enumeration; each is expanded to full VP-level detail **in the last two slices of the preceding phase**... Phase 2's ingestion design will be better informed by what Phase 1 learns about the store SPI." That is a considered decision, not a gap this decomposition should paper over by inventing detail the epic explicitly says would be premature. Phase 2's chunk is therefore a real, standalone `docs/developer/plans/phase-2.md` + status file — satisfying the Epic Decomposition Model's requirement that every phase gets one — but its slice-level content stays a pointer to [epic Part 6](../plans/lattice-platform-agentic-development-v0.2.md#part-6--phase-2-ingestion-and-query-planes) until P1.11.3 (Phase 1's own close-out slice) expands it.

One piece of Phase 2 is **not** light: the persistence-compiler integration (P2.1.4a, P2.3.1, P2.3.6, P2.4.1) was already fully designed and written into the epic in a prior decomposition pass, because `ontology/persistence`/`tools/persistence` (Slice 2 of `rdf-sparql-patterns-phase`) already exists and there was nothing premature about specifying how Phase 2 uses it. That work is not repeated here — see [epic Part 6's preamble](../plans/lattice-platform-agentic-development-v0.2.md#part-6--phase-2-ingestion-and-query-planes) and [docs/developer/INDEX.md](../INDEX.md) Part II §6.

## What this chunk still needs to add now, ahead of full expansion

Even a rolling-wave placeholder needs the obligations the user asked every chunk to carry: `docs/architecture` deliverables, subproject READMEs, and an SDS delta plan for what is already concretely scoped (the persistence-compiler integration, C-05/C-04/C-12's module boundaries). [phase-2-plan.md](../plans/phase-2-plan.md) covers exactly that slice, without inventing VP-level test tables the epic has not yet earned the right to specify.

## Risks specific to this phase, worth stating now rather than at P1.11.3

- C-05 (mapping plan compiler) is the largest single piece of missing implementation in the entire epic (Part 14's critical path calls it out by name) and gates Phases 2 and 3 entirely. Resourcing it first and heaviest is already stated in the epic; this decomposition adds nothing except to note it should not be quietly deprioritised because Phase 2's chunk looks lighter on paper than Phase 0/1's.
- P2.9 (content pipeline) explicitly says "Build C-14 first" — the agent orchestrator supervisor — before any LLM call exists in C-06. That ordering constraint belongs in whatever expands this chunk at P1.11.3; flagging it here so it is not lost between documents.
