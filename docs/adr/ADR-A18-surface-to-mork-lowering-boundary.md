<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A18: Surface-to-MORK lowering boundary

**Status:** Accepted
**Date:** 2026-09-18
**Supersedes:** none
**Related:** ADR-A17 (Surface unified projection authoring model), ADR-A16 (Surface projection mechanism), ADR-A19 (staged compiler architecture)
**Source plan:** [surface-mork-unified-projection-delivery-plan.md](../../surface/docs/surface-mork-unified-projection-delivery-plan.md)

## Context

MORK is the machine-facing, provenance-rich mapping graph. It already models `mork:DataMapping`, `mork:ShapeMapping`, `mork:RuleMapping`, `mork:QueryTemplate`, and `mork:ProjectionMapping`, with parameter bindings, targeting specs, and provenance records. `surface/docs/OUTSTANDING-ITEMS 2.md` confirms `mork:ProjectionMapping` already exists in `mork/spec/Mork.ttl` and that `tools/surface/mork.py` lowers in both directions against it.

Authoring MORK's mapping graph by hand — parameter bindings, targeting specs, dependency edges — is exactly the complexity ADR-A16's Surface layer was created to spare domain authors from for Promotion and Index. Projection needs the same relief.

## Decision

**A `srf:ProjectionContract` lowers deterministically into one or more MORK mapping nodes**, drawn from `mork:DataMapping`, `mork:ShapeMapping`, `mork:RuleMapping`, `mork:QueryTemplate`, and `mork:ProjectionMapping` as the contract's intent requires. MORK remains the canonical mapping graph: dependency edges, parameter bindings, and provenance live there, not duplicated in Surface. Surface never emits an executable artefact (SPARQL, SHACL, SWRL, RML) directly for a Projection contract — only a validated MORK graph, which downstream compilers (ADR-A19, ADR-A23) then target.

## Consequences

- A new lowering stage is required in the Surface compiler, distinct from Promotion/Index's direct-emit path.
- Lowered output must satisfy MORK's own completeness and validation checks before any backend compiles it — MORK validation is an acceptance gate for Surface's Projection output, not a downstream concern.
- The namespace and toolchain assumptions recorded as unverified in `surface/docs/OUTSTANDING-ITEMS 2.md` §5 (the `mork:` prefix binding, the exact term names `tools/surface/mork.py` assumes) must be confirmed against `mork/spec/Mork.ttl` as it stands, not re-guessed, before lowering is relied on in production.
- Promotion and Index keep their existing direct-emit path; this ADR does not require routing them through MORK.
