<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A17: Surface unified projection authoring model

**Status:** Accepted
**Date:** 2026-09-18
**Supersedes:** none
**Related:** ADR-A16 (Surface projection mechanism), ADR-A18 (Surface-to-MORK lowering boundary), ADR-A01 (layer conventions)
**Source plan:** [surface-mork-unified-projection-delivery-plan.md](../../../ontology/surface/docs/surface-mork-unified-projection-delivery-plan.md), [adr-bundle-outline-surface-mork-unified-projection.md](../../../ontology/surface/docs/adr-bundle-outline-surface-mork-unified-projection.md)

## Context

ADR-A16 gave Surface two operations, Promotion and Index. Both restate an existing value: onto a direct property, or into a retrieval symbol. Neither covers a mapping that must construct new graph structure, derive a value, join across carriers, or expand a relation into several — the class of intent the delivery plan calls Projection.

Two ways to add this capability were open:

1. A third, independent authoring language for projection intent, separate from Surface.
2. A third Surface subsystem, alongside Promotion and Index, sharing Surface's declaration, generation, and derived-record tiers and its derivation-authority model.

The first duplicates mapping semantics MORK already owns and gives authors a second vocabulary to learn for a need that is, in kind, the same as Promotion and Index: state an intent against a carrier, generate an artefact, record what was generated and from what.

## Decision

**Surface is the single top-level authoring layer for Promotion, Index, and Projection.** A `srf:ProjectionContract` is declared the same way a promotion or index contract is: naming a carrier, an intent, and a generation profile. It does not emit an executable artefact directly — it lowers into MORK (ADR-A18), which is where Promotion and Index already have the option to land when a deployment wants MORK-mediated compilation instead of direct emission.

Projection gets its own law set (ADR-A20), distinct from Promotion and Index's X1–X6, because its failure modes — an unresolvable join, an underspecified role binding — are not restatement failures.

## Consequences

- Surface's vocabulary and shapes gain one subsystem. Existing Promotion and Index contracts, and everything ADR-A16 already decided about them, are unchanged.
- The `srf:` namespace grows; it is not reorganised or renamed.
- Every Projection contract is subject to the same conservativity and signature-scope discipline (ADR-A21) that already governs Promotion, because Projection can construct assertions over an authored property exactly as a source-signature promotion can.
- Authoring documentation for Surface must now teach three subsystems instead of two, sharing one mental model: declare intent, generate, record.
