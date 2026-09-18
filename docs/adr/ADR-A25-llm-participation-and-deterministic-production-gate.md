<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A25: LLM participation and deterministic production gate

**Status:** Accepted
**Date:** 2026-09-18
**Supersedes:** none
**Related:** ADR-A22 (MORK governance and versioning), ADR-A28 (parity and conformance gate)
**Source plan:** [surface-mork-unified-projection-delivery-plan.md](../../surface/docs/surface-mork-unified-projection-delivery-plan.md)

## Context

Surface-to-MORK lowering (ADR-A18) can, in principle, use an LLM to complete gaps a contract leaves declarative — a missing parameter binding, an ambiguous role. Unconstrained, this conflicts with the determinism ADR-A19's staged pipeline exists to guarantee, and with the governance gate ADR-A22 places on production mappings.

## Decision

**LLM output is proposal-grade by default.** Every LLM-originated completion is materialised as explicit, distinguishable graph nodes and requires governance state (ADR-A22) before it can compile in production mode. A deterministic-only mode — no LLM invocation anywhere in lowering — exists and is the recommended default for production deployments.

## Consequences

- Projection policy fields (ADR-A17, ADR-A20) declare an LLM-completion toggle and a template allow-list, alongside backend allow/deny lists.
- The production gate (ADR-A28) rejects any mapping with an LLM-originated node lacking governance sign-off, regardless of how the mapping otherwise validates.
- Bounded-completion mode, where an LLM may fill only declared gaps using approved templates, remains available for draft and review workflows without weakening the production gate.
