<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: AIR-2.1, peril spec, scheme declarations and shapes

**Unit:** [`applied-insurance-reference`](../status/applied-insurance-reference.md)
**Machine:** S (Copilot Business). **Branch:** `air/2.1-peril-spec`
**Plan and test cases:** [Phase 2 plan](../plans/applied-insurance-reference-phase-2.md) (AIR-2.1 in detail)
**Decisions:** ADR-A98 (namespaces), ADR-A99

## Invariant

The `prl:` properties exist with the characteristics ADR-A99 fixes, every peril scheme of the reference edition is declared, and the well-formedness shapes accept a well-formed fixture and reject each defect they name.

## Test cases

The table in the plan section above. Each row's result is recorded under Results at
verification.

## One command

Run from the repository root on machine R, after `mise run build:ontology-catalog` and `mise run build:ontology-releases`.

```bash
mise run check:ontology-catalog && mise run check:ontology-versioning
```

## Artefacts to inspect

- `ontology/applied/insurance/peril/spec/peril.ttl`: `prl:canTrigger` and `prl:overlaps`.
- `vocab/peril-vocab.ttl`: the eight schemes and the region markers.
- `examples/well-formed.ttl` and `tools/test_peril_vocabulary.py`.

## Deliberate non-coverage

No concepts beyond the fixture (AIR-2.2 to AIR-2.4). The collections and crosswalk shapes are AIR-2.5 and AIR-3.4. The applied README and ontology architecture rows are added by R at verification.

## Handoff

Written by the building machine when the work is committed. S could not run the tests, so R runs them first.

- **Built:** `spec/peril.ttl` (all `prl:` properties and datatypes of the plan's table — `broaderGeneric`/`broaderPartitive` aligned to locally-declared `iso-thes:` terms, `canTrigger`, `overlaps`, the six characteristic-link properties, the three Quantification-link properties, `ReferenceCode` and `CatModelCode` datatypes, every term with `rdfs:label`, `rdfs:comment` and `fnd:utility`). `vocab/peril-vocab.ttl` (the eight reference schemes, each with `fnd:hasIdentity`/`fnd:hasGovernanceState fnd:Active`/`skos:prefLabel`/`skos:editorialNote`, plus every empty region marker in the exact order and naming the plan specifies). `shapes/structural.ttl` (label-and-definition, characteristics) and `shapes/constraints.ttl` (reference code — as three `sh:sparql` constraints on one shape, covering cardinality, uniqueness and the parent-prefix/top-concept-letter rule — primary parent, materialised broader, associative integrity, acyclic, threshold definitions), `shapes/.version` (`0.1.0`). `examples/well-formed.ttl` (the six cause concepts and four characteristic placeholders the plan names, plus a minimal fixture-local `qnt:ValueSpace`/`qnt:RangeSet` pair for `N.MET.TC.HUR`'s threshold, kept out of the `prl-voc:` namespace since it isn't a real Quantification link — that's AIR-2.6). `tools/test_peril_vocabulary.py` (one test per plan row, AIR21-01 to AIR21-12, negative cases as fixture mutations rather than separate files, plus AIR21-03 validating the eight schemes against `ontology/vocabulary/shapes/`). `README.md` for the module.
- **Not run:** `mise run check:ontology-catalog` (which runs `tools/test_peril_vocabulary.py`) and `mise run check:ontology-versioning` — no runtime on this machine. Every SHACL-SPARQL query in the two shape files was checked by hand against the fixture and against each negative mutation, but none of it has actually been executed by pySHACL.
- **Check first:** the reference-code shape's parent-prefix rule (`STRSTARTS`/`STRAFTER`/`CONCAT` over the `xsd:string` form of two `prl:ReferenceCode` literals) is the most intricate query in this pack — worth a close read before trusting it. The associative-integrity and acyclic shapes both use the `skos:broader+` property path, which needs `advanced=True` in pySHACL the same as the SPARQL targets do (already set in the test). `mise run build:ontology-catalog` and `mise run build:ontology-releases` need to run before the catalog/versioning checks, per the plan's own note (stub catalogs for `spec/` and `vocab/`, release rows for both documents and the shapes directory). `ontology/applied/README.md` and `ontology-architecture.md` were deliberately **not** touched here (AIR-1.1 owns them in parallel) — R adds this module's rows once AIR-1.1 has merged.
- **Deviations from the plan:** none identified. One judgement call, documented rather than hidden: the reference-code shape is written as three separate `sh:sparql` entries on one `sh:NodeShape` (cardinality, uniqueness, format) instead of one combined query, since a single query mixing a `GROUP BY`/`HAVING` cardinality check with a per-parent format check produced a materially harder query to review by hand, for no behavioural difference — SHACL runs every `sh:sparql` entry on a shape independently.

## Results

Written on machine R at verification.
