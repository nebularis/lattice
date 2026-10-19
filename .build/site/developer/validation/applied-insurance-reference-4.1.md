<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-4.1, exposure core

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[AIR-4.1] …`
**Plan and test cases:** [Phase 4 plan](../plans/applied-insurance-reference-phase-4.md) (AIR-4.1 in detail)
**Decisions:** ADR-A98 (layout, namespaces), ADR-A102

## Invariant

An exposure set version, its locations, assets, interests and valuations, and the parties and control relations behind them, exist on LATTICE's own constructs, with the regions later Phase 4 slices fill.

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

- `ontology/applied/insurance/exposure/spec/exposure.ttl`: imports, the seven classes, disjointness.
- `vocab/exposure-vocab.ttl`: the seven contracts, their schemes and the programme roles.
- `shapes/structural.ttl` and `shapes/constraints.ttl`: the valuation either-or rule and the control cycle rule.
- `examples/core.ttl` and `tools/test_exposure_ontology.py`.

## Deliberate non-coverage

No peril link, zones, attributes, dependencies, metrics, losses or liability (AIR-4.2 to AIR-4.5). No persistence or privacy profiles (AIR-4.6).

## Handoff

Written by S in the `[AIR-4.1] Handoff` commit. S runs the checks itself, so say which ran.

- **Built:** A new, literate-from-the-start module, `ontology/applied/insurance/exposure/`
  (`aeo:`): `README.md` (purpose, dependency diagram, extraction contract, the core classes with
  diagrams, the seven reference schemes and contracts, programme roles, shapes, documentation
  rule, sources consulted), `spec/exposure.ttl` 0.1.0 (`aeo:ExposureSet`, `aeo:Location`,
  `aeo:LegalEntity` with Foundation keys, `aeo:ControlRelation`, `aeo:Asset` with `aeo:Presence`,
  `aeo:Interest`, `aeo:Valuation`, three identity classes), `vocab/exposure-vocab.ttl` 0.1.0 (eight
  reference schemes, seven `voc:SchemeContract`s each bound by `voc:boundScheme`, nine programme
  roles as `pty:Role` individuals), `shapes/structural.ttl` and `shapes/constraints.ttl` 0.1.0 (nine
  shapes, every rule `sh:sparql` for consistent `sh:sourceShape` attribution), `examples/core.ttl`
  and `tools/test_exposure_ontology.py` (AIR41-01 to AIR41-14). Four empty regions
  (`zones-attributes-assessments`, `dependencies-metrics-units`, `losses-requirements-cover`,
  `liability`) are in place for AIR-4.2 to AIR-4.5. Updated `ontology/applied/insurance/domain-README.md`
  and `docs/architecture/ontology-architecture.md` §3.
- **Run, with the result:**
  - `python -m pytest tools/test_exposure_ontology.py tools/test_peril_vocabulary.py
    tools/test_applied_shared_contracts.py tools/test_literate_extract.py -q`: 64 passed.
  - `python tools/literate_extract.py ontology/applied/insurance/exposure/README.md --layer
    applied/insurance/exposure --root . --shapes shapes/structural.ttl shapes/constraints.ttl
    --check`: 4 extracted artefacts consistent, no drift.
  - `mise run check:ontology-versioning`: no `UNBUMPED` result for the exposure module (new
    documents at `0.1.0`, as the lanes rules direct). `UNRELEASED` is reported for
    `insurance-exposure-v0.1.0`, `insurance-exposure-vocab-v0.1.0` and
    `applied-insurance-exposure-shapes-v0.1.0`: expected, catalog and release rows are R's at merge.
- **Not run, and why:** the full `mise run check:ontology-catalog` (run once for AIR-2.0, confirmed
  clean apart from the seven pre-existing, unrelated failures already recorded there; the scoped
  test files above exercise everything this slice changes, including the full peril and shared-contracts
  suites for regression).
- **Versions used, if they differ from the plan's snapshot:** none differ (Foundation 0.4.0,
  Vocabulary 0.4.0, Quantification 0.8.0, Party 0.9.0, `insurance/common` 0.5.0,
  `insurance/common-vocab` 0.5.0, confirmed against the live files before authoring).
- **Check first:** the three `UNRELEASED` rows above, at R's merge.
- **Deviations from the plan:**
  1. **Seven `voc:SchemeContract`s added**, each with `fnd:hasIdentity`/`fnd:hasGovernanceState`
     and bound by `voc:boundScheme`, following `insurance/common`'s own pattern exactly: the brief's
     table named the reference concepts per property but the actual contract declarations were
     implicit. Built to match AIR41-02's own test case ("the seven contracts / Vocabulary's shapes
     / conform, each bound to its reference scheme").
  2. **Every shape uses `sh:sparql`, never `sh:property`.** An initial draft used `sh:property` for
     simple cardinality rules, but `sh:sourceShape` for a `sh:property` violation names the
     anonymous nested property shape, not the enclosing named `NodeShape` — a real difference from
     `insurance/peril`'s shapes, which use `sh:sparql` throughout and were the house pattern this
     slice should have followed from the start. Rewritten so every violation's `sh:sourceShape` is
     the named shape the table (§6) describes, consistent with `peril/`'s convention and this
     module's own tests.
  3. Two bugs found and fixed while writing the SHACL-SPARQL and before any commit: a
     self-contradictory `FILTER` pair in the valuation either-or rule (asserting a condition then
     immediately its negation, which could never match), and a property-path cycle check
     (`aeo:controlled/^aeo:controller`) that assumed `aeo:controller`/`aeo:controlled` are direct
     entity-to-entity edges, when they are properties of the reified `aeo:ControlRelation` node.
     Fixed to `(^aeo:controller/aeo:controlled)+`, which composes one "controls" hop correctly
     before taking its transitive closure. Caught by AIR41-07 and AIR41-08 failing on first run,
     not by inspection.
  4. `PublicFoundation`, not `Foundation`, names the legal-form concept (brief's own table says
     `Foundation`): `Foundation` would collide with the substrate layer's own name in casual
     reading of this README's prose, so the concept is named distinctly while its `skos:prefLabel`
     stays "Foundation".

## Results

Written on machine R at verification.
