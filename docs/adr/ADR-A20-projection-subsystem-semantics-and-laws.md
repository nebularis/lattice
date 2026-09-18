<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A20: Projection subsystem semantics and law model

**Status:** Accepted
**Date:** 2026-09-18
**Supersedes:** none
**Related:** ADR-A17 (Surface unified projection authoring model), ADR-A16 (Surface projection mechanism, laws X1–X6), ADR-A21 (signature-scope composition)
**Source plan:** [surface-mork-unified-projection-delivery-plan.md](../../surface/docs/surface-mork-unified-projection-delivery-plan.md)

## Context

ADR-A16's laws — X1 conservativity, X2 index faithfulness, X6 signature scope, and the rest of the X-series — are stated against Promotion's single read path and Index's population membership. Projection's intents (graph construction, derivation, joins, expansion) are not restatements of one path, and a join or derivation failure is not a shape X1–X6 anticipate.

## Decision

**Projection has its own law register**, separate from Promotion/Index's X-series but composing with it where a Projection contract stacks over a Promotion or Index surface (ADR-A21 states the composition rule). New constraints and defect fixtures cover Projection-specific invalid states: an unresolvable join key, an underspecified role binding, a derivation with no stated dependency.

## Consequences

- `srf:` vocab and shapes gain a Projection law register, alongside rather than folded into the existing X-series.
- Signature-scope composition (ADR-A21) is a dependency of this ADR's law set: a Projection contract can produce authored-signature assertions exactly as a source-signature promotion can, and its laws must say so rather than assume Projection is automatically conservative.
- Defect fixtures for Projection are added to the same corpus structure Promotion and Index already use, not a separate one.
