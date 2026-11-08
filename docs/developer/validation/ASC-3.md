<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: Asset class ASC-3, exposure adopts the edition

**Unit:** `asset-class` ([plan](../plans/asset-class.md), [status](../status/asset-class.md))
**Machine:** S. **Branch:** `air/asset-classes`. Commits are local, and pushing is the maintainer's.
**Plan and test cases:** [Asset class plan](../plans/asset-class.md) (ASC-3 in detail)
**Decisions:** ASC-Q3, ASC-Q4

## Invariant

Every exposure example names an asset class from the edition, never a value type. An asset whose class states `asc-voc:Mobile` has no `aeo:locatedAt`, and one whose class states `asc-voc:Stationary` has no `aeo:presence`.

## Test cases

The table in the plan. Each row's result is recorded under Results at verification.

## One command

Run from the repository root.

```bash
mise exec -- python -m pytest tools/test_exposure_ontology.py
```

## Artefacts to inspect

`ontology/applied/insurance/exposure/README.md` (section 6, `aeo:AssetShape`, and the release notes), its extracted shapes, its examples, `tools/test_exposure_ontology.py`.

## Deliberate non-coverage

An asset with neither a location nor a presence, which the exposure module allows today.

## Handoff

Built on machine S, 2026-11-08, on `air/asset-classes`, committed locally and not pushed.

**What was built.**

- **The vocab import.** Exposure's vocab document imports `applied/asset-class-vocab/0.1.0`, so an exposure deployment has the edition bound as its fallback, beside the classification import it keeps for the territory and industry contracts.
- **`aeo:AssetShape`** gains two SHACL-SPARQL rules, each reporting the asset with its class as the value: a mobile class with an `aeo:locatedAt`, and a stationary class with an `aeo:presence`. They read `asc:mobility` on the class concept, so a deployment's own scheme that states mobility is checked alike, and a class that states none is not checked.
- **Examples.** `core.ttl`, `versions.ttl` and `units.ttl` name `asc-voc:NonResidentialBuilding`, `asc-voc:PlantAndMachinery` and `asc-voc:Inventory` where they named the value types `Building`, `Machinery` and `Stock`. The valuations keep their value types.
- **The README.** Section 5's contract text says where the asset class binding comes from and that a value type is never a class. Section 6's shape table, section 8's sources and an **Unreleased** release note, classed may invalidate for the import and the shape and no effect for the examples.
- **Tests.** `tools/test_exposure_ontology.py` loads the edition in its fixture, expects the new import, and gains seven cases.

**What was run.**

- `pytest tools/test_exposure_ontology.py -n auto`: 48 passed.
- `literate_extract.py` on the exposure README: the vocab document and `shapes/structural.ttl` change as intended, and no other generated file changes.
- `check:import-guard`, `check:owl-profile`, `check:catalogue`, `check:published-decisions`, `check:identifiers`: exit 0. `tools/ontology_catalog.py check`: consistent.

| Row | Result |
|---|---|
| ASC3-01 | pass, `test_asc3_01` over the three examples, and `test_air41_04` finds no result with the edition loaded |
| ASC3-02 | pass, a building reclassed `asc-voc:Vessel` with its location is refused |
| ASC3-03 | pass, the building with a presence instead of its location is refused |
| ASC3-04 | pass, `asc-voc:ComputerHardware` with either, and `asc-voc:MobilePlant` with presences, are accepted |
| ASC3-05 | pass |
