<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-4.3, dependencies, peril metrics and exposure units

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** R, taking over from S. **Branch:** `air/applied-reference`, commits `[AIR-4.3] …`
**Plan and test cases:** [Phase 4 plan](../plans/applied-insurance-reference-phase-4.md) (AIR-4.3 in detail)
**Decisions:** ADR-A90, ADR-A98, epic E3, R8, R9. Milestone M3, first half

## Invariant

Dependencies between locations, assets and third parties are evidenced relations, peril metrics are derived artefacts with comparable scopes, and exposure units are computed on demand for the perils a check asks about, never asserted by hand and never required to be stored.

## Test cases

The table in the plan section above, AIR43-01 to 09. Under the amendment of 2026-10-14 they are
built later, in the AIR-deferred-testing slice (Phase 4 plan), with the probes recorded in the
Handoff below as ready-made negative cases.

## One command

Run from the repository root. S runs it before the handoff commit. R runs it again at verification,
after `mise run build:ontology-catalog` and `mise run build:ontology-releases`, which S cannot do.

```bash
mise exec -- python -m pytest tools/test_exposure_ontology.py -q && mise run check:ontology-catalog && mise run check:ontology-versioning
```

## Artefacts to inspect

- The `dependencies-metrics-units` sections of the exposure README.
- `exposure_units` in `tools/exposure_derivations.py`.
- `examples/units.ttl` and the M3 decisions, and that the source graph holds no units afterwards.
- The Open Results Data citations.

## Deliberate non-coverage

No maximum foreseeable interruption derivation. No catastrophe model results (epic §7).

## Handoff

Written by R in the `[AIR-4.3] Handoff` commit. Testing for the applied insurance modules is
deferred (amendment of 2026-10-14), so the heavy suites did not run. Cheap ad hoc scripts did.

- **Built:** the `dependencies-metrics-units` region of the exposure README, with the spec
  (`aeo:Dependency`, `aeo:PerilMetric`, `aeo:MetricComparison`, `aeo:ExposureUnit`,
  `aeo:scheduleGroup` and their properties), the vocabulary (six schemes with their contracts, two
  contracts with no reference scheme, and four value spaces), and nine shapes. Regenerated spec,
  vocab and both shape files. `tools/exposure_derivations.py` (`exposure_units`).
  `examples/dependencies.ttl` and `examples/units.ttl`. No version bump, the module being new on
  the branch.
- **Run, with the result:**
  - The literate extraction, and every generated file parses.
  - `dependencies.ttl` with `core.ttl`, and `units.ttl`, each against every exposure shape with
    pySHACL (`advanced=True`, `inference="none"`): conform, no warning.
  - Ten single-change probes of the new shapes, one per shape (an exceedance metric without a
    return period and with both, a score on the wrong space and with no space, a scenario loss with
    no scenario, a metric with no peril scope, a dependency with no provider, a dependency cycle, a
    comparison of an insured with a ground-up loss, and an incomplete unit with no derivation run):
    each reported the expected shape (the metric with no scope also breaks the comparison that cites it, correctly).
  - `exposure_units` over `units.ttl` for flood and wind: eight units, values 1, 2, 3 and 4
    million pounds, an empty report, and no triple added to the source graph.
  - The M3 profile over those units with this branch's SPARQL backend: seven units decide as the
    example states. Site D's flood unit reads Undetermined (`exe:MissingCandidate`), because this
    branch's compilers ignore a closure. It reads Denied once CCS HQ-6a.2 merges.
- **Not run, and why:** `tools/test_exposure_ontology.py`, the catalog and release checks, and
  `check:full-sweep`. Deferred.
- **Versions used, if they differ from the plan's snapshot:** none. No import of `insurance/peril`'s
  spec was added, since no spec term uses it (the vocabulary already imports `peril-vocab`).
- **Check first:** §4.3's prose and the metric shape table, then the Open Results Data citations in
  the metric kind, perspective and calculation method notes.
- **Deviations from the plan:**
  - `aeo:perilScope` lost its `aeo:PoolParticipation` domain (AIR-4.2 had set it), because peril
    metrics reuse it and a reasoner would otherwise read each metric as a pool participation.
  - Two terms beyond the brief: `aeo:MetricComparison` with `aeo:comparedMetric`, which gives the
    comparability shape something to read, and `aeo-voc:ScenarioContract`, because
    `aeo:scenario` is concept-valued.
  - Only two calculation methods (`FullUncertainty`, `PerSampleMean`), as the brief allowed. Their
    names and the EPType mapping of the metric kinds follow the Oasis Open Results Data
    specification as remembered and are not checked against it, so R's check is open.
  - `aeo-voc:ProbabilityOfEvents` is described as the probability or expected number of events,
    because the brief's wording ("names a count") could be read either way.
  - The maximum foreseeable interruption is deferred, as the brief said.
- **Open question for the maintainer:** the metric shape asks for exactly one perspective, which a
  hazard score or a probability of events does not have, so `dependencies.ttl` states ground-up for
  its score. The options are to require a perspective only for the loss kinds or to leave it as
  decided. No change was made.

## Results

Written on machine R at verification.
