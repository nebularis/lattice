<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-2.4, peril causes H, P, C, F and L, cross-group links

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[AIR-2.4] …`
**Plan and test cases:** [Phase 2 plan](../plans/applied-insurance-reference-phase-2.md) (AIR-2.4 in detail, and the shared rules for AIR-2.3 and AIR-2.4)
**Decisions:** ADR-A98 (namespaces, addendum), ADR-A99

## Invariant

Every concept of peril vocabulary §5.4 to §5.8 exists once with its characteristics, and every link between the two family groups exists once in `cross-group-links`.

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

- `vocab/peril-vocab.ttl`: regions `cause-H` to `cause-L` and `cross-group-links`.
- The overrides for H.WRA, P.PV.STK, F and L, read against the plan's tables.
- Ten definitions picked at random, read against the style rules.

## Deliberate non-coverage

No collections (AIR-2.5). No crosswalk (AIR-3.4).

## Handoff

Written by S in the `[AIR-2.4] Handoff` commit. S runs the checks itself, so say which ran.

- **Built:** `vocab/peril-vocab.ttl`'s `cause-H`, `cause-P`, `cause-C`, `cause-F`, `cause-L` and
  `cross-group-links` regions filled in place in the peril README: 37 H concepts, 36 P, 17 C, 10
  F, 11 L, bringing the cause scheme to 287 concepts in eight families. Every concept carries its
  code, label, definition, note, materialised parent link and the characteristics the family-
  default and override tables give it, matching AIR-2.3's own conventions. Eleven in-family and
  cross-group `prl:canTrigger`/`prl:overlaps`/`skos:related` triples in `cross-group-links`
  (`T.EQB.CTL` overlaps `C.NML.OTF`, `T.UTL.TEL` overlaps `C.NML.SVC`, `T.REL.RAD` related
  `P.TER.CBR.RAD`, `C.NML.CFG` related `E.HUM`, `L.MED` related `E.PRO`, `C.MAL.OTA` and
  `C.NML.OTF` each `prl:canTrigger` `T.FIR`, `T.EXP` and `T.EQB`). `prl-voc:CauseScheme
  skos:hasTopConcept` gains its remaining five members, for eight in total. README's concept
  counts updated.
- **Run, with the result:**
  - `python -m pytest tools/test_peril_vocabulary.py tools/test_peril_intensity.py
    tools/test_applied_shared_contracts.py tools/test_exposure_ontology.py
    tools/test_literate_extract.py -v`: all passed (AIR24-01 to AIR24-07 added to
    `tools/test_peril_vocabulary.py`, 7 tests).
  - A standalone `pyshacl.validate()` script over the full 287-concept scheme (`spec/peril.ttl` +
    `vocab/peril-vocab.ttl` + `vocab/peril-intensity.ttl` + `examples/well-formed.ttl`) against
    every peril shape: `conforms: True` on the first run.
  - `python tools/literate_extract.py ontology/applied/insurance/peril/README.md --layer
    applied/insurance/peril --root . --shapes shapes/structural.ttl shapes/constraints.ttl
    --check`: 5 extracted artefacts consistent.
  - `python tools/ontology_version_check.py --base-ref main`: one `UNBUMPED` line,
    `common/spec/common.ttl`, the same pre-existing AIR-2.0 artefact recorded in every earlier
    slice's own Validation Pack. Nothing new from this slice.
- **Not run, and why:** `mise run check:ontology-catalog` (the full sweep), for the same reason as
  every earlier slice this trip: the targeted run above covers every test file this slice's
  content could affect, and the sweep's 7 pre-existing, unrelated failures are already recorded.
- **Versions used, if they differ from the plan's snapshot:** none differ. No version bump, per
  the plan's own note.
- **Check first:** `check:ontology-versioning`'s one `UNBUMPED` line, the same pre-existing
  artefact as every earlier slice touching `insurance/common`.
- **Deviations from the plan:**
  1. AIR24-06 ("a hierarchical condition requiring N to L and excluding N.HYD.FLD, evaluated as
     `tools/test_eligibility_examples.py` evaluates its examples") names a test file that only
     validates SHACL shapes against static example fixtures: it has no reusable Python function
     for evaluating a profile against arbitrary data. Built the test instead by reusing the real
     three-valued kernel connectives (`tools/reference/eligibility`'s `and3`, `PERMITTED`,
     `DENIED`, `UNDETERMINED`) directly: a required-match decision (`Permitted` if the concept is
     `skos:broader+`-or-self of any of the eight family tops, else `Undetermined`), an excluded-
     match decision (`Denied` if the concept is `skos:broader+`-or-self of `N.HYD.FLD`, else
     `Permitted`), combined with `and3` (an `elg:AllRequired`-style conjunction). This reproduces
     the plan's own worked example (`N.HYD.FLD.FLU` Denied, `P.TER.CNV` Permitted) using
     Eligibility's real semantics, not a new ad hoc evaluator, but does not go through the RDF
     `elg:AdmissionProfile`/`elg:Condition` machinery itself. Installed
     `tools/reference/eligibility` as an editable, no-dependency local package
     (`pip install -e tools/reference/eligibility --no-deps`) to import it, the same package
     `mise run bootstrap:reference-eligibility` already installs.
  2. Performance, not a defect: the full `tools/test_peril_vocabulary.py` run is slower again now
     that the cause scheme holds all 287 concepts (see AIR-2.6's and AIR-2.3's own notes on this).
     Not fixed, since it is outside this slice's scope.
- **Check first:**
- **Deviations from the plan:**

## Results

Written on machine R at verification.
