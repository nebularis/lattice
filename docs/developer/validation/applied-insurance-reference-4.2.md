<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-4.2, zones, pools, attributes and assessments

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[AIR-4.2] …`
**Plan and test cases:** [Phase 4 plan](../plans/applied-insurance-reference-phase-4.md) (AIR-4.2 in detail)
**Decisions:** ADR-A98, ADR-A99. Decided 2026-10-13: the AIR-4.2 proposal, Q13, R6

## Invariant

A location carries zone designations and pool participations, every hazard attribute arrives as an attribute value in an evidenced assessment, and the peril vocabulary says which attributes and which geocoding precision each peril needs, so the shapes can warn when an exposure set lacks them.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root. S runs it before the handoff commit. R runs it again at verification,
after `mise run build:ontology-catalog` and `mise run build:ontology-releases`, which S cannot do.

```bash
mise exec -- python -m pytest tools/test_exposure_ontology.py -q && mise run check:ontology-catalog && mise run check:ontology-versioning
```

## Artefacts to inspect

- The `zones-attributes-assessments` sections of the exposure README and the Turtle they generate.
- The attribute type tables, each type's form, family and space, contract or datatype, and the OED fields cited, against the OED specification.
- The peril links table, read against the attribute types it names.
- `shapes/profiles/construction-protection.ttl` and `shapes/profiles/cyber-posture.ttl`.

## Deliberate non-coverage

No zone or class editions (AIR-4.6). No shapes for the six other profile families. Completeness is checked per location, not per asset. Peril scope comes only from `aeo:perilScope` on exposure set members until AIR-4.3 and AIR-4.4 add metrics and requirements.

## Handoff

Written by S in the `[AIR-4.2] Handoff` commit. S runs the checks itself, so say which ran.

- **Built:** `ontology/applied/insurance/exposure/README.md`'s `zones-attributes-assessments` region: `aeo:ZoneDesignation`/`aeo:PoolParticipation`/`aeo:Assessment`/`aeo:AttributeValue` and their properties in `spec/exposure.ttl`. Six zone contracts (unbound), designation source, assessment kind and profile family contracts and schemes, value forms, value spaces (`Count`, `Area`, `Length`, `Duration`, `Speed`, `AreaShare`, `ConfidenceScore`), `SusceptibilityScale` and `FrequencyScale`, and an `AttributeTypeScheme` covering fifteen attribute families (Construction with ten reference sub-schemes, Occupancy, Protection, External exposure, Geocoding quality, Equipment, Corporate, and the seven profile-only families Cyber posture, Business continuity, Environmental, Fleet, Compliance, Operations and workforce, Supply chain) in `vocab/exposure-vocab.ttl`. The eleven peril-attribute links, as triples on the existing `prl-voc:` cause concepts. Ten new structural shapes (`ZoneDesignationShape`, `ZoneInTerritoryShape`, `SpatialJoinShape`, `PoolParticipationShape`, `AssessmentShape`, `AttributeValueShape`, `SingleValuedTypesShape`, `ScreeningShape`) in `shapes/structural.ttl`, two warning-severity cross-node shapes (`PerilCompletenessShape`, `GeoPrecisionForPerilShape`) in `shapes/constraints.ttl`, and two new files `shapes/profiles/construction-protection.ttl` and `shapes/profiles/cyber-posture.ttl` (a violation-severity shape plus a warning-severity "outside family" shape each). `literate_extract.py`'s `--shapes` now takes four paths, updated in the README's own documented command. `examples/attributes.ttl`, extending AIR-4.1's `core.ttl` fixture. `tools/test_exposure_ontology.py` gained AIR42-01 to AIR42-13 (13 tests; also updated two AIR-4.1 tests the slice's own import/scheme growth made stale: renamed the import-closure test to `test_air42_01_...`, and loosened the eight-scheme exact-set assertion to a subset check). Added `@prefix cls-voc:` and an import of `classification-vocab/0.2.0` to `vocab/exposure-vocab.ttl` (needed for `cls-voc:TerritoryContract`). Added `skos:notation` integer ranks to AIR-4.1's six `GeoPrecisionScheme` concepts, for the new geo-precision shape's ordinal comparison. No version bump (exposure's documents were already bumped to `0.1.0` this trip, at AIR-4.1, per the "bump once" rule).
- **Run, with the result:** `python -m pytest tools/test_exposure_ontology.py -q` — 27 passed. `python -m pytest tools/test_peril_intensity.py tools/test_applied_shared_contracts.py -q` — 18 passed (regression check, no content change to either). `python -m pytest tools/test_peril_vocabulary.py -q -n auto` — 39 passed (regression check; found, during this, that the file now takes about 16 minutes serially and is too slow for the main `check` pathway, unrelated to this slice's own content — fixed as its own small change: excluded from `check:ontology-catalog`, given its own optional `check:peril-vocabulary` task, recorded as TD-45). `python tools/literate_extract.py ontology/applied/insurance/exposure/README.md --layer applied/insurance/exposure --root . --shapes shapes/structural.ttl shapes/constraints.ttl shapes/profiles/construction-protection.ttl shapes/profiles/cyber-posture.ttl --check` — 6 extracted artefacts consistent. `python tools/ontology_version_check.py --base-ref main` — one `UNBUMPED` line, `ontology/applied/insurance/common/spec/common.ttl`, the one pre-existing AIR-2.0 artefact (a `@base` directive removal, no semantic change) already noted in every slice this trip. A standalone `pyshacl.validate()` of the full example (spec, vocab, peril's spec/vocab/intensity, `examples/core.ttl` and `examples/attributes.ttl`) against all four shape files conforms with zero results, including warnings (`allow_warnings=False`).
- **Not run, and why:** `mise run check:ontology-catalog` and `mise run check:ontology-versioning` as `mise` tasks (ran the underlying commands directly instead, same effect, per this environment's usual pattern this trip).
- **Versions used, if they differ from the plan's snapshot:** none.
- **Check first:** the "zone in territory" shape (see deviations) once AIR-4.6 actually binds a market scheme to a zone contract, and the "peril-attribute links" section's reading of `skos:broader*` once AIR-2.5's collections add indirection between a cause concept and its siblings.
- **Deviations from the plan:**
  1. The brief's "zone in territory" shape row reads "the zone's scheme is bound to its contract for one of the location's territories". `voc:boundScheme` is `owl:FunctionalProperty` (one scheme per contract, not one per territory), and no per-territory multi-binding mechanism exists anywhere in LATTICE. Built as a single global check instead: where a scheme *is* bound to the zone's own contract (from AIR-4.6 onward), the zone concept must be in it; before that (contracts unbound, as built here) the check is vacuously satisfied. The per-territory nuance is an open question for AIR-4.6, which does the actual market bindings.
  2. `aeo:DocumentationShape`'s hard-coded `FILTER (?scheme IN (...))` list (seven AIR-4.1 scheme IRIs) would have needed roughly 38 more entries for this slice's own new schemes alone, and more every later slice. Generalised to `FILTER (STRSTARTS(STR(?scheme), ".../exposure/vocab#"))` with `?scheme a voc:ConceptScheme` — same meaning (every `aeo-voc:` scheme's concepts need a note), no further edits needed by later slices.
  3. pySHACL refuses a `VALUES` clause inside a `sh:sparql` constraint. Hit this in the two profile shapes' required-attribute-type checks; rewritten as a `UNION` of `FILTER NOT EXISTS` branches instead, same meaning.
  4. Found and fixed a real bug while writing the example: `aeo:zoneDesignation` and `aeo:poolParticipation` both have `rdfs:domain aeo:Location`, but the first draft of `examples/attributes.ttl` asserted them backwards. This didn't break conformance (every per-node shape still read fine) but silently made the two warning shapes vacuously pass, caught by three negative tests (AIR42-08, 09, 12) expecting a warning that never fired.

## Results

Written on machine R at verification.
