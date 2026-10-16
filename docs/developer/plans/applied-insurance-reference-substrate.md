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
| S2 | Eligibility | `HierarchicalMatch` with a chosen traversal: all broader links, or one named sub-property of `skos:broader` | L-P2, PV-O4 | Author with CCS slice C9b3, which edits the same hierarchical-match code paths (NRS NQ-4, 2026-10-10. Previously with NRS N5, now CCS HQ-6). kind-only matching (Phase 2 and 3 checks) |
| S3 | Eligibility | moved into Phase 3 as AIR-3.2 and AIR-3.3 (ADR-A103, epic D12) | L-P3, AL-2 | checks across cause and characteristics (M2) |
| S4 | Capacity first, then Quantification per promotion criteria | grouping occurrences into episodes by a window anchored on the first occurrence | L-P5 | hours clauses, event aggregates (5.7, 6.3) |
| S5 | Surface | generated classes from collections and characteristic conjunctions, optional per E3 | L-P4 | design-time checks over bundles and write-back scopes |
| S6 | guidance only | spatial pattern: GeoSPARQL alignment, zones as concepts, spatial joins as derived artefacts | L-P6, AL-1 | Phase 4 zones |
| S7 | Foundation | resolution policy for conflicting evidenced assertions of one attribute | AL-3 | Author with [NRS](normative-rule-substrate.md) N10 (epic §3b). several assessments of one building (Phase 4) |
| S8 | Persistence | a disclosure class beside the privacy class, read by every export (legal privilege) | claims sketch S-CL2 | claims plan AIR-6.10 |
| S9 | Persistence | retention per class after an anchoring event, and legal hold overriding retention and erasure | claims sketch S-CL3 | claims plan AIR-6.10 |
| S10 | Persistence | erasure deferred by a duty to retain, a new `dal:ErasurePrecedence` member | claims sketch S-CL4 | claims plan AIR-6.10 |

## S6 in detail

**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[S6] …`, the last
being `[S6] Handoff`. **Validation Pack:**
[applied-insurance-reference-s6](../validation/applied-insurance-reference-s6.md). **Sketch:**
peril structure whitepaper §7.2 (L-P6), asset exposure ontology §13 (AL-1).

**Invariant:** a guidance document states how LATTICE content records places, zones and spatial
computations with the constructs it already has, in domain-neutral terms, and changes no layer.

No ADR. S6 is guidance only and changes no layer, so the clean-room procedure applies to its text
(ADR-A-C2): the premise and both worked examples are domain-neutral, and no insurance term appears.

### The document (`docs/architecture/spatial-data-patterns.md`)

| Section | Content |
|---|---|
| Premise | places matter to many domains, and LATTICE has no spatial layer and needs none: geometry is an optional alignment, zones are classifications, and spatial computations are derivations |
| Geometry | align with OGC GeoSPARQL 1.1 (`geo:hasGeometry`, `geo:asWKT`), state the coordinate reference system in the WKT literal and default to WGS 84 longitude and latitude order (CRS84), keep elevation's vertical datum with the value's evidence. A module does not import GeoSPARQL to use a location, so the core stays independent of it |
| Zones | a zone is a concept in a scheme bound per territory by a scheme contract (Vocabulary), not a class and not a geometry. A designation of a place in a zone is an evidenced, temporally scoped node, whose temporal scope is the map edition's validity, so a new map never rewrites history |
| Spatial joins | a zone membership or distance computed from coordinates is a `fnd:DerivedArtefact`, whose derivation run names the dataset edition and the method, and whose `prov:used` names the inputs. GeoSPARQL's topological functions may compute it at query time, and nothing computed is asserted as an authored fact |
| Precision | how precisely a place is known is a concept from an ordered scheme, so a consumer can require a minimum |
| Distances and areas | Quantification quantities on declared spaces, in QUDT-aligned units |
| Example 1 | a city's planning zones and the parcels designated in them, with a revised zoning map |
| Example 2 | a conservation charity's monitoring sites, their distance to the nearest watercourse computed from a published river network edition |
| Where it is used | one closing line pointing at the applied exposure module, the only insurance mention, as a consumer and not as the premise |

Linked from `docs/architecture/ontology-architecture.md` (the guidance list) and from the
developer guide's list of architecture documents. The substrate track's S6 row is marked done at
the merge.

### Checks

Text only. The Validation Pack's command is `mise run topology:links`, which checks the new
document's local links, and R reads the document against the clean-room rule.

## Documentation deltas

Each item: its ADR, the layer README, `docs/architecture/ontology-architecture.md` (layer section
and §11 open items).
