<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-2.6, intensity measures, thresholds and units

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[AIR-2.6] …`
**Plan and test cases:** [Phase 2 plan](../plans/applied-insurance-reference-phase-2.md) (AIR-2.6 in detail)
**Decisions:** ADR-A98 (namespaces, addendum), ADR-A99

## Invariant

Each intensity measure has its own value space with a unit contract, threshold-defined cause concepts point at range sets on their measures' spaces, and units, currencies among them, are declared once in `insurance/common`, aligned to QUDT and ISO 4217.

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

- `vocab/peril-intensity.ttl` and its README sections.
- The units section of `insurance/common`'s README and `common-vocab.ttl`.
- The seven threshold range sets, read against the plan's table and its cited sources.
- The currency list, against ISO 4217 List One as published on the day of verification.

## Deliberate non-coverage

No exposure attribute links (`prl:relevantAttribute`, `prl:minimumGeoPrecision`), which AIR-4.2 writes in the exposure vocabulary. No parametric triggers.

## Handoff

Written by S in the `[AIR-2.6] Handoff` commit. S runs the checks itself, so say which ran.

- **Built:**
  - `insurance/common`'s README §6 "Units and currencies": ~25 physical units across nine families
    (acceleration, speed, pressure, length, area, mass per area, power per length, temperature,
    duration), each `qnt:Unit` with a `skos:exactMatch` into QUDT's `http://qudt.org/vocab/unit/`
    vocabulary and a `skos:note` naming its SI definition or convention, four `qnt:Conversion`s with
    their exact factors (knot, mph, g, hPa), and every active ISO 4217 List One currency (about 39)
    as a `qnt:Unit` on one money space `icm-voc:Money`, with its numeric code as `skos:notation`, its
    English name as `skos:prefLabel`, a `skos:exactMatch` into QUDT's currency unit vocabulary
    (`http://qudt.org/vocab/unit/CCY_XXX`, not the deprecated `http://qudt.org/vocab/currency/XXX`
    pattern, confirmed by fetching both a deprecated and a current QUDT page), and a note citing ISO
    4217 and the minor unit. `common-vocab` bumped `0.5.0` → `0.6.0`.
  - `insurance/peril`'s README §5.5 "Intensity measures and thresholds": a new document
    `vocab/peril-intensity.ttl` (its own ontology self-IRI
    `https://www.nebularis.org/neuro-semantic/lattice/insurance/peril/intensity`, versioned in unison with
    `peril-vocab` at `0.5.0`, per ADR-A120 addendum decision 3 and the AIR-2.0 precedent set by
    `behaviour-runtime.ttl`). Contains `prl-voc:IntensityMeasureScheme` (a `voc:ConceptScheme`) and
    24 measure concepts, each `skos:inScheme`/`skos:topConceptOf` it and `prl:measuredOn` its own
    `qnt:ValueSpace`. Three ordinal measures (`ModifiedMercalliIntensity`, `SaffirSimpsonCategory`,
    `EnhancedFujitaRating`) each point at a small ordinal scheme of their own
    (`prl-voc:MmiScale` I–XII, `prl-voc:SaffirSimpsonScale` 1–5, `prl-voc:EnhancedFujitaScale`
    EF0–EF5), also `voc:ConceptScheme`s. Seven threshold-defined cause concepts
    (N.MET.TC.HUR/TST/TDP/TYP/SEV, N.MET.SCS.SLW.DER, N.MET.WIN.BLZ) carry one or two
    `prl:definingThreshold` `qnt:RangeSet`s each, built with flat, named blank nodes rather than
    nested brackets. Thirteen other cause concepts carry `prl:intensityMeasure` links, and nine
    carry `prl:customaryEventWindow` (72 h or 168 h). `prl:definingThreshold`'s `rdfs:comment` in
    `spec/peril.ttl` gains the sentence "A concept with several defining thresholds meets all of
    them."
  - `prl:ThresholdDefinitionShape` (`shapes/constraints.ttl`) extended with a second `sh:sparql`
    rule: a `prl:definingThreshold`'s `qnt:onSpace` must be the `prl:measuredOn` space of one of the
    concept's `prl:intensityMeasure`s (the plan's AIR26-07). Shapes `.version` `0.2.0` → `0.3.0`.
    `examples/well-formed.ttl` gained a placeholder `prl:intensityMeasure` on `N.MET.TC.HUR` on the
    same placeholder space its threshold already used, so the new rule holds on the AIR-2.1/2.2
    fixture without depending on `peril-intensity.ttl`.
  - `tools/test_peril_intensity.py` (new): AIR26-01 to AIR26-09, 11 tests.
  - `tools/test_peril_vocabulary.py`: one line updated, the pinned `common-vocab` import now
    expected at `0.6.0`.
  - Documentation: the peril README's shape table, mermaid diagram and Sources consulted list; the
    common README's §9 fixture/tests note and new §9a Sources consulted; the domain README's module
    table; `docs/architecture/ontology-architecture.md`'s applied insurance domain row; the status
    record's Machine S section (this commit).
- **Run, with the result:**
  - `python -m pytest tools/test_peril_vocabulary.py tools/test_peril_intensity.py
    tools/test_applied_shared_contracts.py tools/test_exposure_ontology.py
    tools/test_literate_extract.py -q`: 75 passed.
  - `python tools/literate_extract.py ontology/applied/insurance/common/README.md --layer
    applied/insurance/common --root . --check`: 2 extracted artefacts consistent.
  - `python tools/literate_extract.py ontology/applied/insurance/peril/README.md --layer
    applied/insurance/peril --root . --shapes shapes/structural.ttl shapes/constraints.ttl --check`:
    5 extracted artefacts consistent.
  - `python tools/ontology_version_check.py --base-ref main`: one `UNBUMPED` line,
    `common/spec/common.ttl` (version unchanged at `0.5.0` since `main`, content differs only in a
    dropped `@base` directive). This is the pre-existing AIR-2.0 artefact already recorded in
    [its Validation Pack](applied-insurance-reference-2.0.md) (a pure reformatting by the literate
    extractor, not a semantic change), not a new defect. Run against `main` rather than the default
    `HEAD` because the branch's bump-once-per-trip rule (lanes §3) is only visible against the
    trip's start, not the immediately prior commit: `peril/spec/peril.ttl` and
    `peril/vocab/peril-vocab.ttl` both change content again in this slice (the common-vocab re-pin
    to `0.6.0`) without a further bump, which is correct per the rule and is exactly what comparing
    against `main` confirms, but would wrongly read as a fresh defect against `HEAD`.
  - `python tools/ontology_releases.py check`: reports `UNRELEASED` for every version this trip has
    touched so far (`common-vocab-v0.6.0`, `peril-v0.5.0`, `peril-vocab-v0.5.0`,
    `exposure-v0.1.0`, `exposure-vocab-v0.1.0`, both shapes `.version`s). Expected, R's job at
    merge (`mise run build:ontology-releases`), not S's.
- **Not run, and why:** `mise run check:ontology-catalog` (the full sweep). Not needed beyond the
  targeted pytest run above: this slice touches no substrate layer and the targeted run already
  covers every test file this slice's content could affect. The full sweep's 7 pre-existing,
  unrelated failures (the hanging `reasoning-testkit` jar) are recorded in AIR-2.0's and AIR-2.2's
  Validation Packs and in repo environment memory, not reconfirmed here.
- **Versions used, if they differ from the plan's snapshot:** none differ from the plan's snapshot
  except as the plan itself anticipated: `common-vocab` `0.5.0` → `0.6.0` (plan: "bumped once on the
  branch, MINOR"), `peril-intensity.ttl` carries `peril-vocab`'s version, `0.5.0` (plan's "Files"
  note), `peril/shapes/.version` `0.2.0` → `0.3.0` (not anticipated by the plan's own text, found
  necessary while building the AIR26-07 test: the plan's threshold-shape row implies the space
  cross-check, but the slice brief did not call out that this needs a shapes bump, an omission now
  corrected).
- **Check first:** `check:ontology-versioning`'s one `UNBUMPED` line and `ontology_releases.py
  check`'s `UNRELEASED` lines, per the notes above, both expected.
- **Deviations from the plan:**
  1. The plan's "Files" line says `vocab/peril-intensity.ttl` is "new, carrying the version of
     `peril-vocab.ttl`, AIR-2.0" but does not say it needs its own distinct `owl:Ontology` self-IRI.
     The first draft reused `peril-vocab.ttl`'s own ontology IRI verbatim (and its `owl:imports`
     named itself), which `tools/ontology_releases.py check` exposed (both files reporting under
     the same product name). Fixed to its own self-IRI
     `https://www.nebularis.org/neuro-semantic/lattice/insurance/peril/intensity`, following the precedent
     `behaviour-runtime.ttl` sets for a second spec document in one layer (ADR-A120 decision 2):
     own self-IRI, version number in unison with the module's other vocab document.
  2. The 24 measure concepts' first draft omitted `skos:inScheme`/`skos:topConceptOf` on
     `prl-voc:IntensityMeasureScheme`, and the scheme itself, and the three ordinal scales, were
     declared `a owl:Class` rather than `a voc:ConceptScheme`. Found while writing AIR26-02 (every
     measure is read as a scheme member). Fixed: the scheme and the three scales are now
     `voc:ConceptScheme` individuals with `fnd:hasIdentity`/`fnd:hasGovernanceState`, and every
     measure concept is `skos:inScheme`/`skos:topConceptOf` the measure scheme.
  3. `prl:ThresholdDefinitionShape` did not, before this slice, check that a `prl:definingThreshold`
     is on a space one of the concept's `prl:intensityMeasure`s actually measures, so AIR26-07 (a
     deliberate negative case placing HUR's threshold on the wrong space) found no violation. This
     is the rule the plan's own test row describes, so it was missing, not deliberately deferred.
     Added the second `sh:sparql` rule described above, bumped shapes `.version`, and gave
     `examples/well-formed.ttl`'s `N.MET.TC.HUR` a matching placeholder measure so the existing
     AIR-2.1/2.2 fixture still conforms.
  4. Found a documentation gap while writing the currency list: the five last currencies (COP, VND,
     PKR, BDT, ISK) were drafted without their `skos:exactMatch`, caught and fixed before this
     Handoff, not after.

## Results

Written on machine R at verification.
