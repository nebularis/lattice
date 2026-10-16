<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-2.3, peril causes N, T and E

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[AIR-2.3] …`
**Plan and test cases:** [Phase 2 plan](../plans/applied-insurance-reference-phase-2.md) (AIR-2.3 in detail, and the shared rules for AIR-2.3 and AIR-2.4)
**Decisions:** ADR-A98 (namespaces, addendum), ADR-A99

## Invariant

Every concept of peril vocabulary §5.1 to §5.3 exists once, with its code, its parent link and the characteristics the shared rules give it, and the vocabulary passes every peril shape.

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

- `vocab/peril-vocab.ttl`: regions `cause-N`, `cause-T`, `cause-E`.
- `README.md`: Sources consulted, concept counts.
- Ten definitions picked at random, read against the style rules.

## Deliberate non-coverage

No links to H to L (AIR-2.4). No intensity links or thresholds (AIR-2.6). No collections (AIR-2.5).

## Handoff

Written by S in the `[AIR-2.3] Handoff` commit. S runs the checks itself, so say which ran.

- **Built:** `vocab/peril-vocab.ttl`'s `cause-N`, `cause-T` and `cause-E` regions filled in place
  in the peril README: 90 N concepts (geophysical, hydrological, meteorological, climatological,
  biological, extraterrestrial), 71 T concepts, 15 E concepts, 176 in total. Every concept carries
  its `skos:notation` (`prl:ReferenceCode`), `skos:prefLabel`, `skos:definition`, `skos:note`
  (citing a standard where one applies, saying so plainly where none does), materialised
  `prl:broaderGeneric`/`prl:broaderPartitive` plus `skos:broader`, and the characteristics the
  family-default and override tables give it (`prl:typicalAgency`, `prl:onset`,
  `prl:definitionBasis`, `prl:accumulationClass` where the table sets one,
  `prl:typicalMechanism` where the mechanisms table names one, `prl:harmSubject`). Sixteen Oasis
  Open Exposure Data model codes added as a second, `prl:CatModelCode`-typed `skos:notation`.
  Nine in-family `prl:canTrigger`/`prl:overlaps`/`skos:related` links named in the sketch (every
  link with both ends inside N, T or E). `prl-voc:CauseScheme skos:hasTopConcept` gained its
  first three members (N, T, E); AIR-2.4 adds the remaining five. README's Sources consulted
  section and fixture/tests section updated.
- **Run, with the result:**
  - `python -m pytest tools/test_peril_vocabulary.py tools/test_peril_intensity.py
    tools/test_applied_shared_contracts.py tools/test_exposure_ontology.py
    tools/test_literate_extract.py -v`: 93 passed (AIR23-01 to AIR23-08, 03 and 08 split into two
    test functions each, 9 tests in total, added to `tools/test_peril_vocabulary.py`).
  - A standalone `pyshacl.validate()` script over `spec/peril.ttl` + `vocab/peril-vocab.ttl` +
    `vocab/peril-intensity.ttl` + `examples/well-formed.ttl` against `structural.ttl` +
    `constraints.ttl`: `conforms: True`.
  - `python tools/literate_extract.py ontology/applied/insurance/peril/README.md --layer
    applied/insurance/peril --root . --shapes shapes/structural.ttl shapes/constraints.ttl
    --check`: 5 extracted artefacts consistent.
  - `python tools/ontology_version_check.py --base-ref main`: one `UNBUMPED` line,
    `common/spec/common.ttl`, the same pre-existing AIR-2.0 artefact recorded in that slice's own
    Validation Pack (a pure reformatting, not a semantic change). Nothing new from this slice:
    `peril/spec/peril.ttl` and `peril/vocab/peril-vocab.ttl` change content again without a
    further bump, correctly, since AIR-2.2 already bumped them this trip (lanes §3).
- **Not run, and why:** `mise run check:ontology-catalog` (the full sweep). The targeted run above
  covers every test file this slice's content could affect; the full sweep's 7 pre-existing,
  unrelated failures (the hanging `reasoning-testkit` jar) are already recorded in earlier
  slices' Validation Packs, not reconfirmed here.
- **Versions used, if they differ from the plan's snapshot:** none differ. No version bump, per
  the plan's own note ("AIR-2.2 bumped `peril-vocab.ttl` on this branch").
- **Check first:** `check:ontology-versioning`'s one `UNBUMPED` line, the same pre-existing
  artefact as every earlier slice touching `insurance/common`.
- **Deviations from the plan:**
  1. `examples/well-formed.ttl` (AIR-2.1's small, self-contained 6-concept fixture) re-declared
     N, T, N.MET, N.MET.TC, N.MET.TC.SRG and N.MET.TC.HUR with its own `skos:prefLabel`/
     `skos:definition` text. Now that AIR-2.3 declares these for real in `peril-vocab.ttl`, the
     fixture's own re-declarations became a second, distinct value for the same property,
     breaking `LabelAndDefinitionShape`'s "exactly one" rule. Fixed by removing the fixture's
     re-declarations entirely (it now has no triples of its own beyond a header comment): the
     real vocabulary already supplies the hierarchy fragment the fixture existed to exercise.
     The fixture's placeholder threshold for `N.MET.TC.HUR` is also gone, since
     `tools/test_peril_vocabulary.py`'s and `tools/test_peril_intensity.py`'s `_fixture()`
     helpers now both load `vocab/peril-intensity.ttl` (AIR-2.6), which carries the real
     `prl:definingThreshold` for every threshold-defined concept. This matches the lanes rule's
     own reasoning for building AIR-2.6 before AIR-2.3 ("the thresholds must exist when AIR-2.3
     assigns that basis").
  2. For the same reason, `test_air22_04_vocabulary_alone_has_no_results` (AIR-2.2) started
     failing: `vocab/peril-vocab.ttl` alone now contains seven threshold-basis cause concepts
     whose `prl:definingThreshold` lives in the separate `peril-intensity.ttl` document by
     design (ADR-A120 addendum). Fixed by loading both documents together for this one test;
     "vocabulary alone" now means both vocabulary documents, not `peril-vocab.ttl` in isolation.
  3. AIR23-08's "no definition contains cover/covered/exclude/insured/policy" needs a word-
     boundary match, not substring containment: four existing, correct definitions
     (`Inundation`'s "water covering land", `CancellationCosts`'s "irrecoverable cost",
     and this slice's own `N.HYD.FLD` "water covering land" and `E.LAT` "not discoverable")
     false-positived on a plain substring check. Fixed with a `\bword\b` regular expression.
  4. Performance, not a defect: `tools/test_peril_vocabulary.py`'s SHACL-heavy tests slowed
     noticeably once the cause scheme held 176 real concepts (the file's full run moved from a
     few seconds to roughly 15 minutes). Logged in repo memory as an expected, worsening cost for
     AIR-2.4 (287 concepts), not something this slice's scope includes fixing.

## Results

Written on machine R at verification.
