<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-66, exposure versions never edited, content names identities (TD-66)

**Unit:** [formal methods, track H](../plans/formal-methods-track-h.md), §4.14
**Branch:** `claude/nice-bohr-pmj43u`, done here at the maintainer's request, to be moved to the AIR branches later
**Decisions:** sketch EP-8 and EP-9, VH-Q2 (a)

## Invariant

A version is written once and never edited. That a version is current or superseded is read from the
succession (`fnd:supersededBy`), not from a `fnd:validTo` or a governance state added to the earlier
version. Content names a persistent identity (`aeo:LocationIdentity`, `aeo:AssetIdentity`), and the
exposure set version's membership fixes which version of that identity holds for the set. One
location changing therefore writes one location version, and the assets and valuations that name its
identity are unchanged and shared by both set versions.

## What changed

| Area | Change |
|---|---|
| `examples/versions.ttl` | version 1 keeps its scope (`fnd:validFrom` only) and its `fnd:Active` state. The warehouse changes address, one location version is written, and a stock asset and its valuation (named by identity) are listed unchanged by both set versions |
| `aeo:locatedAt` | range `aeo:LocationIdentity` (was `aeo:Location`) |
| `aeo:valueOf` | range the union of `aeo:AssetIdentity` and `aeo:LocationIdentity` (had none) |
| `aeo:AssetShape`, `aeo:ValuationShape` | the two properties name an identity, not a version |
| `aeo:ExposureSetShape` | every `aeo:locatedAt` of a listed asset resolves to exactly one listed location, and every `aeo:valueOf` of a listed valuation to exactly one listed asset or location, through `fnd:hasIdentity` |
| `aeo:PerilCompletenessShape` | reaches an asset's location through the identity |
| examples `core.ttl`, `units.ttl` | every `aeo:locatedAt` and `aeo:valueOf` names an identity |
| `tools/exposure_derivations.py` | resolves `aeo:locatedAt` through the set's locations and looks valuations up by the asset's identity |
| README | §4 text, the diagram, the class table, the shapes table and a release-notes row. Spec and shapes regenerated from it |

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AIR66-01 | the spec / read the ranges / `aeo:locatedAt` over `aeo:LocationIdentity`, `aeo:valueOf` over the union of the two identity classes | L1 | + |
| AIR66-02 | `versions.ttl` with spec and vocab / every shape / no result | L3 | + |
| AIR66-03 | `versions.ttl` / read version 1 / `fnd:supersededBy` version 2, state `fnd:Active`, no `fnd:validTo` anywhere | L1 | + |
| AIR66-04 | `versions.ttl` / compare the two set versions / assets and valuations equal, locations differ by the two warehouse versions only, two assets and two valuations in all | L1 | + |
| AIR66-05 | an asset naming a location version / `aeo:AssetShape` / violation | L3 | − |
| AIR66-06 | a valuation naming an asset version / `aeo:ValuationShape` / violation | L3 | − |
| AIR66-07 | a set that lists an asset but not its location identity's version / `aeo:ExposureSetShape` / violation, on that set only | L3 | − |
| AIR66-08 | a set that lists two versions of one location identity / `aeo:ExposureSetShape` / violation | L3 | − |
| AIR66-09 | a set that lists a valuation but not its asset / `aeo:ExposureSetShape` / violation | L3 | − |

The existing AIR42-12 test, which builds a location and its completeness warning, runs over the
changed `aeo:PerilCompletenessShape` and passes.

## One command

```bash
mise exec -- python -m pytest tools/test_exposure_ontology.py -q -n auto
```

A pass is 41 passed. Then `mise run check:ontology-catalog`, and the literate check:

```bash
mise exec -- python tools/literate_extract.py ontology/applied/insurance/exposure/README.md --layer applied/insurance/exposure --root . --check
```

## Artefacts to inspect

- The exposure README, the paragraph after the §4 membership text, the shapes table and the release notes.
- `examples/versions.ttl`.
- The three new `sh:sparql` constraints on `aeo:ExposureSetShape` in the README.
- `tools/test_exposure_ontology.py`, the AIR66 block at the end.

## Results

Run on 2026-10-20 in this worktree.

| Check | Result |
|---|---|
| `tools/test_exposure_ontology.py` | 41 passed |
| literate `--check` | 6 extracted artefacts consistent with the README |
| `python tools/ontology_catalog.py check` | consistent, 2 known defects in MORK examples |
| `mise run check:ontology-catalog` | 1129 passed, 7 failed, 7 skipped. None is in exposure. Four in `tools/test_wording.py` (the untracked `ontology/wording/examples/shared-values.ttl` and TD-65 work in progress) and three in `tools/test_lattice_repo_catalogue.py` (`ontology/persistence/execution` is not yet one of persistence's roles). Both areas belong to other developers |

## Deliberate non-coverage

- `aeo:presenceLocation` still names a location version. It was not in the brief, and a presence is a
  period at a place, so it is a candidate for the same change.
- `aeo:assesses`, `aeo:interestIn`, `aeo:partOf` and the zone and loss links still name versions.
- `aeo:PerilCompletenessShape` reads any asset that names the location's identity, in any set, as it
  read any asset before. It does not scope the join to one set version.
- A reader's "location at a date" query is not written. Resolution is by the set version, as the
  README says.
- The module's version is not bumped (TD-64), and no release row or tag is produced.

## Decisions taken alone

- `aeo:valueOf`'s range is a union of the two identity classes, an `owl:unionOf`, where the property
  had no range.
- Three set-level `sh:sparql` constraints on `aeo:ExposureSetShape` enforce that membership fixes the
  identity. They are violations, not warnings, and also reject a set listing two versions of one
  location identity. The AIR-4.2a pack named that as deliberately not covered, and with identities in
  content it is no longer a free choice.
- Type checks (identity, not version) are SPARQL checks on `aeo:AssetShape` and `aeo:ValuationShape`,
  following the file's house style, not `sh:class`.
- `versions.ttl` gains a warehouse stock asset and valuation, to show an asset and a valuation
  surviving a location change, and the earlier restated warehouse valuation is gone. Version 1 keeps
  `fnd:Active`.
- `tools/exposure_derivations.py` was changed, outside the listed paths, since its reads of
  `aeo:locatedAt` and `aeo:valueOf` break otherwise. No test exercises it, and it was not run.
- Presence locations were left as they are (above).
- The release-notes row sits before AIR-4.4's, not at the end.

## Handoff

- **Built:** as above. **Not committed.**
- **Check first:** the README paragraph on identities, then the three set shapes.
- **Next:** TD-66 can come off the register when this moves to the AIR branches, which is the maintainer's call.
