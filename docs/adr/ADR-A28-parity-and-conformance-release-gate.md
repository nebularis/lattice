<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A28: Parity and conformance gate for generated behaviours

**Status:** Accepted
**Date:** 2026-09-18
**Supersedes:** none
**Related:** ADR-A24 (Eligibility executable strategy), ADR-A25 (LLM participation and deterministic gate), ADR-A26 (provenance chain completeness)
**Source plan:** [surface-mork-unified-projection-delivery-plan.md](../../surface/docs/surface-mork-unified-projection-delivery-plan.md)

## Context

`surface/docs/OUTSTANDING-ITEMS.md` §3.4 recorded Surface's own parity law (R2) as unimplemented. `OUTSTANDING-ITEMS 2.md` records the follow-on state: `tools/surface/parity.py` now implements the comparison, but generates its own questions from the contract rather than drawing on the shared conformance corpus the other layers use, so its results are not comparable across layers. Extending parity to Projection and to each new MORK compiler backend (ADR-A23) without a shared corpus repeats that same gap once per mechanism.

## Decision

**Parity and conformance are CI release gates**, using one shared conformance corpus across Surface, MORK, and Eligibility rather than a per-mechanism harness generating its own questions. SHACL execution against the corpus and extraction-drift checks (`tools/literate_extract.py --check`) are mandatory CI checks, not optional ones.

## Consequences

- `tools/surface/parity.py` is extended to draw questions from the shared corpus, retiring its self-generated question set once the shared corpus covers the same cases.
- A parity regression or an extraction-drift failure blocks release, for any layer the shared corpus covers.
- New compiler backends (ADR-A23) and the Eligibility IR (ADR-A24) are conformance-corpus consumers from the outset, rather than being added to the corpus after their first release.
