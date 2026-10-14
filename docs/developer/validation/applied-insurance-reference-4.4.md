<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-4.4, loss experience, cause chains, requirements and cover

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** R, taking over from S. **Branch:** `air/applied-reference`, commits `[AIR-4.4] …`
**Plan and test cases:** [Phase 4 plan](../plans/applied-insurance-reference-phase-4.md) (AIR-4.4 in detail)
**Decisions:** ADR-A98, ADR-A99, ADR-A103, epic D7 and D12. Decided 2026-10-13: Q11, Q12, Q14, R1, R3, R4, R5

## Invariant

An insured's loss experience states its period, source and completeness, each loss records its cause chain with recorded and effective characteristics kept apart, and requirements, existing cover, cover history and financial metrics are evidenced facts that gap analysis can read without any of them computing cover.

## Test cases

The table in the plan section above, AIR44-01 to 13. Under the amendment of 2026-10-14 they are
built later, in the AIR-deferred-testing slice (Phase 4 plan), with the probes recorded in the
Handoff below as ready-made negative cases.

## One command

Run from the repository root. S runs it before the handoff commit. R runs it again at verification,
after `mise run build:ontology-catalog` and `mise run build:ontology-releases`, which S cannot do.

```bash
mise exec -- python -m pytest tools/test_exposure_ontology.py -q && mise run check:ontology-catalog && mise run check:ontology-versioning
```

## Artefacts to inspect

- `insurance/common`'s new loss event, GLIDE key scheme and class of business contract, and its 0.6.0 version IRI and every importer on the branch.
- The `losses-requirements-cover` sections of the exposure README.
- `tools/exposure_derivations.py` and `examples/losses.ttl`, which must be its output.
- The cause position notes and their case citations.

## Deliberate non-coverage

No link from a requirement to `ins:Obligation` (Phase 5). No class of business edition (AIR-4.6). No occurrence grouping under a contract (AIR-6.3). Liability populations come in AIR-4.5.

## Handoff

Written by R in the `[AIR-4.4] Handoff` commit. Testing for the applied insurance modules is
deferred (amendment of 2026-10-14), so the heavy suites did not run. Cheap ad hoc scripts did.

- **Built:**
  - `insurance/common` 0.5.0 to 0.6.0 (spec): `icm:LossEvent` and `icm:classOfBusiness`. Its
    vocabulary (already at 0.6.0 from AIR-2.6) gains `icm-voc:ClassOfBusinessContract` and
    `icm-voc:GlideNumber`, and re-pins to the spec's 0.6.0. The importers re-pinned: `peril` spec,
    the `exposure` spec. The expectations in three tests moved to 0.6.0.
  - The `losses-requirements-cover` region of the exposure README: spec (loss experience, loss
    record, loss cause, defaulted characteristic, coverage requirement and identity, measure
    constraint, existing cover, term summary, cover history event, financial metric), vocabulary
    (ten schemes and contracts, the money share space), and nineteen shapes. Eligibility 0.12.0 is
    imported for `elg:AdmissionProfile`. The generated spec, vocab and shape files are regenerated.
  - `effective_characteristics(graph, run)` in `tools/exposure_derivations.py`.
  - `examples/losses.ttl`, whose last section is the function's output for its causes.
- **Run, with the result:**
  - The literate extraction, and every generated file parses.
  - Every example set against every exposure shape with pySHACL (`advanced=True`,
    `inference="none"`): `core` with `dependencies`, `units`, `versions`, `core` with `attributes`
    and the peril documents, and `core` with `losses` all conform with no warning.
  - Seventeen single-change probes of the new shapes, one per AIR44-06 to 11 case and the rest: each
    reported the expected shape (a loss outside its experience's period, incurred not equal to paid
    plus reserved, a second currency, a missing date, an effective agency with no defaulted node, a
    defaulted node beside a recorded value, a cause with no position, a limit bound on a duration
    space, a premium requirement, a scope over locations, a relative bound on a money space, a
    requirement with no strength, a summary term on the wrong space, a cover with no reference or
    summary, a cover history event with no kind, equity stated as a count, an experience with no
    source).
  - `effective_characteristics` over `losses.ttl` with the peril vocabulary: one defaulted
    characteristic (the flood loss's proximate link, its mechanism), none for the recorded links, and
    the output equals the file's last section.
- **Not run, and why:** `tools/test_exposure_ontology.py`, the catalog, release register and
  versioning checks, `build:ontology-catalog` and `build:ontology-releases`, and
  `check:full-sweep`. Deferred. The catalogs and the release rows regenerate at verification, and
  the release rows at the merge, as the brief said.
- **Versions used, if they differ from the plan's snapshot:** none. `insurance/common` spec 0.6.0,
  Eligibility 0.12.0 (the version on `main` at the branch point).
- **Check first:** the cause position notes and their case citations, then the measure-space shape
  (`aeo:MeasureSpaceShape`) against the relative bound in `losses.ttl`, then `insurance/common`'s
  README release notes.
- **Deviations from the plan:**
  - No membership property of this slice is inverse functional (`aeo:hasLossExperience`,
    `hasLossRecord`, `hasRequirement`, `hasExistingCover`, `hasCoverHistoryEvent`,
    `hasFinancialMetric`), against the brief's wording, because AIR-4.2a (TD-49) removed
    inverse functionality from the module.
  - The financial metric kinds for revenue, gross profit and headcount are
    `aeo-voc:RevenueMetric`, `GrossProfitMetric` and `HeadcountMetric`, because `Revenue`,
    `GrossProfit` and `Headcount` already name a value type and an attribute type in the same
    namespace.
  - One `aeo:DefaultedCharacteristic` per cause and property rather than per value, so a cause
    with several typical mechanisms has one. The effective agency is single valued, so a cause concept
    with several typical agencies leaves it empty and a check reads Undetermined.
  - `aeo:CoverageRequirement` has an `aeo:RequirementIdentity`, because it is a `fnd:Version`.
  - The loss-in-period shape compares dates as ISO strings, since an `xsd:date` cast was not
    reliable across engines.
  - Quantification has no construct for a bound relative to a value (an anchor binding derives a
    range from a nominal value and offsets), so a relative bound is on `aeo-voc:MoneyShare` and names the metric
    with `aeo:relativeTo`, as the brief allowed.
  - The money amounts use `icm-voc:Money` with a currency unit, and the loss record currency shape
    checks `qnt:inUnit`. The earlier exposure examples still use a placeholder space for money.
  - `aeo:requirementScope` carries `rdfs:range elg:AdmissionProfile`, which gives the new import a
    use.
- **Open questions for the maintainer:** none beyond AIR-4.3's perspective question.

## Results

Written on machine R at verification.
