<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-2.2, peril characteristics

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[AIR-2.2] …`
**Plan and test cases:** [Phase 2 plan](../plans/applied-insurance-reference-phase-2.md) (AIR-2.2 in detail)
**Decisions:** ADR-A98 (namespaces, addendum), ADR-A99

## Invariant

The seven characteristic schemes hold their reference concepts, the four shared characteristic properties specialise their `icm:` parents, and the `icm-voc:` contracts bind to the peril schemes.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root. S runs it before the handoff commit. R runs it again at verification,
after `mise run build:ontology-catalog` and `mise run build:ontology-releases`, which S cannot do.

```bash
mise run check:ontology-catalog && mise run check:ontology-versioning
```

## Artefacts to inspect

- `ontology/applied/insurance/peril/spec/peril.ttl`: the `common/` import and the four sub-property axioms.
- `vocab/peril-vocab.ttl`: the seven characteristic regions and the four `voc:boundScheme` bindings.
- `examples/well-formed.ttl` and `tools/test_peril_vocabulary.py`.

## Deliberate non-coverage

No cause concepts (AIR-2.3, AIR-2.4). No typical-characteristic links on cause concepts, which arrive with the causes. No shape changes.

## Handoff

Written by S in the `[AIR-2.2] Handoff` commit. S runs the checks itself, so say which ran.

- **Built:** `spec/peril.ttl` (via the README, §5.1): the `insurance/common/0.5.0` import, and
  `prl:typicalAgency`, `prl:typicalMechanism`, `prl:typicalConsequence` and `prl:harmSubject` each
  gain `rdfs:subPropertyOf` the matching `icm:` property. `prl:onset` and `prl:definitionBasis`
  specialise nothing, as the plan requires. `vocab/peril-vocab.ttl` (§5.2, §5.3): re-pinned to
  `insurance/peril/0.5.0` and `insurance/common-vocab/0.5.0`, the seven characteristic and
  companion schemes filled (70 concepts: 10 agency, 22 mechanism, 4 onset, 6 definition-basis, 3
  accumulation-class, 19 consequence, 6 harm-subject), each with `skos:prefLabel`,
  `skos:definition` and the AIR-2.0 documentation rule's `skos:note`, and four `voc:boundScheme`
  bindings (`AgencyContract`, `MechanismContract`, `ConsequenceContract`, `HarmSubjectContract`).
  `examples/well-formed.ttl` no longer declares local `Natural`/`Sudden`/`Physical`/`Threshold`
  placeholders, referencing the real vocabulary concepts instead. `tools/test_peril_vocabulary.py`
  gains AIR22-01 to AIR22-08.
- **Run, with the result:**
  - `python -m pytest tools/test_peril_vocabulary.py tools/test_applied_shared_contracts.py
    tools/test_literate_extract.py -q`: 49 passed.
  - `python tools/literate_extract.py ontology/applied/insurance/peril/README.md --layer
    applied/insurance/peril --root . --shapes shapes/structural.ttl shapes/constraints.ttl
    --check`: 4 extracted artefacts consistent, no drift.
  - `mise run check:ontology-versioning`: `tools/ontology_version_check.py` reports "40 in-scope
    ontology document(s) checked against HEAD: no unbumped changes" (clean). `tools/ontology_releases.py
    check` reports `UNRELEASED` for `insurance-peril-v0.5.0`, `insurance-peril-vocab-v0.5.0` and
    `applied-insurance-peril-shapes-v0.2.0` (the shapes bump carried over from AIR-2.0): expected,
    since catalog and release-row regeneration stay on R (lanes §1, §6 step 2).
- **Not run, and why:** the full `mise run check:ontology-catalog` (run once for AIR-2.0 and
  confirmed clean apart from the seven pre-existing, unrelated failures already recorded there;
  not re-run for every subsequent slice of the trip to avoid its ~2.5 minute cost each time. The
  scoped test files above exercise everything this slice changes).
- **Versions used, if they differ from the plan's snapshot:** none differ from the brief's own
  refreshed table (peril 0.4.0 → 0.5.0, peril-vocab 0.4.0 → 0.5.0, common 0.5.0, common-vocab
  0.5.0, Foundation 0.4.0, Vocabulary 0.4.0, Quantification 0.8.0, unchanged).
- **Check first:** nothing beyond the `UNRELEASED` catalog/release rows R regenerates at merge.
- **Deviations from the plan:**
  1. **Agency, mechanism and consequence lists amended beyond the brief's first table**, per the
     brief's own "Amended again 2026-10-13" and "Amended 2026-10-13, before S started" notes:
     `Intentional` and `Economic` agency, thirteen more mechanisms (`GroundFailure`, `WaterDamage`,
     `Load`, `Smoke`, `Heat`, `Freezing`, `Collapse`, `Breakdown`, `Corrosion`, `Erosion`,
     `BiologicalAgent`, `Radiation`, `Deprivation`), and the consequence scheme widened to its
     final list of nineteen (`Spoilage`, `DenialOfAccess`, `DataRestoration`, `ExtortionPayment`,
     `Delay`, `ShortageOrNonDelivery`, `GeneralAverageContribution`, `ReputationalHarm`,
     `RegulatoryPenalty`, `NotificationCosts`, `ForensicCosts`, `CancellationCosts` added to the
     brief's first six). Built as the amended brief directs, not the original table.
  2. `prl-voc:AgencyScheme` through `prl-voc:HarmSubjectScheme` also gain `skos:hasTopConcept`
     listing every member, beyond what the brief's table states, mirroring the existing fixture's
     own pattern for the cause scheme's top concepts (both directions materialised, since pySHACL
     validates with `inference="none"`). Not required by any shape, but consistent with house
     style and AIR22-03's own "each a top concept of it" test.

## Results

Written on machine R at verification.
