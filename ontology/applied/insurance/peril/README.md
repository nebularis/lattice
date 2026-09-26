<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Reference Peril Vocabulary (`prl:`)

The reference peril vocabulary, LATTICE's applied insurance domain's default peril scheme
(ADR-A99), built by the [`applied-insurance-reference`](../../../../docs/developer/plans/applied-insurance-reference.md)
epic, Phase 2. See [ADR-A99](../../../../docs/architecture/decisions/ADR-A99-reference-vocabularies-and-peril-structure.md)
and the [peril vocabulary sketch](../../../../docs/developer/sketches/peril-vocabulary.md) for the
design this module implements.

## Files and namespaces (ADR-A98 decision 6)

| File | Content | Namespace | Prefix | Version IRI |
|---|---|---|---|---|
| `spec/peril.ttl` | the `prl:` properties and datatypes only. No scheme, no concept | `https://www.nebularis.org/neuro-semantic/insurance/peril#` | `prl:` | `…/insurance/peril/0.1.0` |
| `vocab/peril-vocab.ttl` | the eight reference schemes, and the cause scheme's members | `https://www.nebularis.org/neuro-semantic/insurance/peril/vocab#` | `prl-voc:` | `…/insurance/peril-vocab/0.1.0` |
| `vocab/peril-intensity.ttl` | the intensity measure scheme and its `qnt:ValueSpace`s | as above | `prl-voc:` | AIR-2.6 |
| `vocab/peril-collections.ttl` | reference collections | as above | `prl-voc:` | AIR-2.5 |
| `crosswalk/*.ttl` | reviewed crosswalks from external code systems | — | — | AIR-3.4 |
| `shapes/` | well-formedness (below), versioned by its own `.version` | — | — | `0.1.0` |

Sketches and this README write concept and scheme IRIs as `prl:` for brevity (for example
`prl:N.MET.TC`): read those as `prl-voc:`. Only properties and datatypes are `prl:`.

## The eight reference schemes

Each is a `voc:ConceptScheme`, an unscoped-fallback reference edition (ADR-A99 decision 1), marked
by `skos:editorialNote "Reference edition published by LATTICE. Not a market standard."`.

| Scheme | Axis |
|---|---|
| `prl-voc:CauseScheme` | the peril backbone (§5 of the sketch) |
| `prl-voc:AgencyScheme` | natural, accidental, negligent, malicious, sovereign, belligerent, undetermined |
| `prl-voc:MechanismScheme` | how harm is inflicted |
| `prl-voc:OnsetScheme` | sudden, gradual, latent, recurrent |
| `prl-voc:DefinitionBasisScheme` | physical, designation, threshold, wording-defined, statutory, index |
| `prl-voc:AccumulationClassScheme` | catastrophe, systemic, attritional |
| `prl-voc:ConsequenceScheme` | heads of loss |
| `prl-voc:HarmSubjectScheme` | what is typically harmed |

## Regions in `vocab/peril-vocab.ttl`, and which slice owns each

The cause scheme's own members are added region by region, so parallel slices' insertions merge
cleanly. Each region is delimited by a `# ==== BEGIN REGION <name> ==== ` / `# ==== END REGION
<name> ====` comment pair.

| Region | Slice |
|---|---|
| `agency`, `mechanism`, `onset`, `definition-basis`, `accumulation-class`, `consequence`, `harm-subject` | AIR-2.2 |
| `cause-N`, `cause-T`, `cause-E` | AIR-2.3 |
| `cause-H`, `cause-P`, `cause-C`, `cause-F`, `cause-L`, `cross-group-links` | AIR-2.4 |

## Shapes (ADR-A99 §10)

"Cause concept" means a concept with `skos:inScheme prl-voc:CauseScheme`. All eight shapes are
`sh:Violation` severity (no discouraged-but-valid case here). Structural shapes (per concept) are
in `shapes/structural.ttl`; cross-concept and hierarchy shapes are in `shapes/constraints.ttl`.

| Shape | Rule |
|---|---|
| `prl:LabelAndDefinitionShape` | every concept in a `prl-voc:` scheme has exactly one `skos:prefLabel` and one `skos:definition`, each `@en` |
| `prl:ReferenceCodeShape` | every cause concept has exactly one `skos:notation` typed `prl:ReferenceCode`, unique among cause concepts, equal to its primary parent's code plus one `.`-separated segment, or its family letter if it is a top concept |
| `prl:PrimaryParentShape` | every cause concept that is not a top concept has exactly one value across `prl:broaderGeneric` and `prl:broaderPartitive`. A second `skos:broader` needs a `skos:editorialNote` |
| `prl:MaterialisedBroaderShape` | every `prl:broaderGeneric` or `prl:broaderPartitive` link also appears as `skos:broader` |
| `prl:CharacteristicsShape` | every cause concept has at least one `prl:typicalAgency`, exactly one `prl:onset`, exactly one `prl:definitionBasis`, and at most one `prl:accumulationClass`, each in its own scheme |
| `prl:AssociativeIntegrityShape` | no `skos:related`, `prl:overlaps` or `prl:canTrigger`, in either direction, between two concepts one of which is `skos:broader+` of the other |
| `prl:AcyclicShape` | no concept is `skos:broader+` of itself |
| `prl:ThresholdDefinitionShape` | a concept whose `prl:definitionBasis` is `prl-voc:Threshold` has a `prl:definingThreshold` |

**Deferred, not built in this slice:** the collections shape (AIR-2.5) and the crosswalk shape
(AIR-3.4). The sketch's "overlap coverage on data" shape reads a consumer's wording statements,
so it is not LATTICE's and is not built.

## Fixture and tests

[`examples/well-formed.ttl`](examples/well-formed.ttl) is a small, real fragment of the cause
scheme (two family tops and a four-generation branch under `N.MET.TC`) that conforms to every
shape above. [`tools/test_peril_vocabulary.py`](../../../../tools/test_peril_vocabulary.py)
validates it, plus one negative case per shape by mutating a copy of the fixture, with pySHACL
(`advanced=True`, `inference="none"`), and checks the eight schemes conform to Vocabulary's own
shapes. Runs under `mise run check:ontology-catalog`, which runs every `tools/test_*.py`.

## PV-O3, PV-O4

Concept lifecycle across editions (PV-O3) and matching over generic links only (PV-O4) need
upstream changes (substrate track S1, S2). Neither blocks this module's first release.
