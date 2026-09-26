<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Applied Insurance Reference — Substrate Track

**Unit ID:** `applied-insurance-reference-substrate`
**Epic:** [applied-insurance-reference](applied-insurance-reference.md)
**Status:** Rolling-wave outline. Each item starts with its own clean-room ADR.
**Sketch:** [peril-structure-whitepaper.md](../sketches/peril-structure-whitepaper.md) §7.2,
[asset-exposure-ontology.md](../sketches/asset-exposure-ontology.md) §13

## Scope

Substrate changes the applied work motivates. None blocks a first release of Phases 1 to 5.
Each follows ADR-A-C2: a domain-neutral premise and two non-insurance examples before any
mechanism prose, and no insurance vocabulary in substrate text (ADR-A-C1).

| Item | Layer | Change | Sketch ref | Enables |
|---|---|---|---|---|
| S1 | Vocabulary | concept-level lifecycle: deprecation, replacement and split across editions (already a Vocabulary open item) | L-P1, PV-O3 | edition upgrades of Phase 2 without breaking recorded values |
| S2 | Eligibility | `HierarchicalMatch` with a chosen traversal: all broader links, or one named sub-property of `skos:broader` | L-P2, PV-O4 | kind-only matching (Phase 2 and 3 checks) |
| S3 | Eligibility | every-value and some-value readings for evidence bindings, and exclusion when any value is excluded | L-P3, AL-2 | multi-valued perils on a case, anti-concurrent causation (Phase 6) |
| S4 | Capacity first, then Quantification per promotion criteria | grouping occurrences into episodes by a window anchored on the first occurrence | L-P5 | hours clauses, event aggregates (5.7, 6.3) |
| S5 | Surface | generated classes from collections and characteristic conjunctions, optional per E3 | L-P4 | design-time checks over bundles and write-back scopes |
| S6 | guidance only | spatial pattern: GeoSPARQL alignment, zones as concepts, spatial joins as derived artefacts | L-P6, AL-1 | Phase 4 zones |
| S7 | Foundation | resolution policy for conflicting evidenced assertions of one attribute | AL-3 | several assessments of one building (Phase 4) |

## Documentation deltas

Each item: its ADR, the layer README, `docs/architecture/ontology-architecture.md` (layer section
and §11 open items).
