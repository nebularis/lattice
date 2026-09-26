<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Applied Insurance Reference — Phase 4, Exposure Ontology

**Unit ID:** `applied-insurance-reference-phase-4`
**Epic:** [applied-insurance-reference](applied-insurance-reference.md)
**Status:** Rolling-wave outline. Detailed at the Phase 1 gate, since it needs only Phase 1 and AIR-2.1.
**Sketch:** [asset-exposure-ontology.md](../sketches/asset-exposure-ontology.md)

## Scope

`ontology/applied/insurance/exposure/` (`aeo:`, `aeo-voc:`) as the sketch's §3 lays out. Facts
about the world, not about cover. No class the substrate already provides.

## Slices

| Slice | Content | Sketch |
|---|---|---|
| AIR-4.1 | exposure set, location, legal entity, control relations, asset, interest, valuation. Spec and shapes created with one region per slice (lanes §4) | §5.1 to §5.6 |
| AIR-4.2 | zones and pool participation, hazard attributes, assessments and profile shapes | §5.4, §5.7, §5.8 |
| AIR-4.3 | dependencies, peril metrics, exposure units derived on demand (no materialisation required) | §5.9 to §5.11 |
| AIR-4.4 | loss history with one `aeo:LossCause` node per link of the cause chain (peril, position, mechanism, agency), effective characteristic values defaulted from the cause's typical values as derived artefacts (epic D12), the loss event class in `insurance/common/` (D7), coverage requirements, existing cover, financial metrics | §5.12 to §5.14 |
| AIR-4.5 | liability exposure: counterparty populations, relationship depth, exposure bases | §5.15 |
| AIR-4.6 | London and US profiles as scheme bindings and shapes, and the worked examples | §10, §12 |

After 4.1, two lanes run in parallel: 4.2, 4.3 and 4.6 in one, 4.4 and 4.5 in the other. 4.2
needs AIR-2.1, 4.3 needs AIR-2.3, 4.4 needs AIR-2.2, and 4.6 needs AIR-2.7. Order and lanes:
[lanes and merge order](applied-insurance-reference-lanes.md).

Milestone M3 closes in 4.3 and 4.6. Personal data of individual insureds is declared through a
`dal:PrivacyProfile` in 4.1.

## Documentation deltas

Module README, `ontology/applied/README.md`, `docs/architecture/data-architecture.md` (exposure
aggregates and privacy boundaries), `docs/architecture/ontology-architecture.md` §3.

## Exit gate

M3 demonstrated. Recommendations AI-1 to AI-4 closed or carried.
