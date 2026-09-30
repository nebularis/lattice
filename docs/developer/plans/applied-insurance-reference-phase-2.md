<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Applied Insurance Reference — Phase 2, Reference Peril Vocabulary

**Unit ID:** `applied-insurance-reference-phase-2`
**Epic:** [applied-insurance-reference](applied-insurance-reference.md)
**Status:** Rolling-wave outline. Detailed at the Phase 1 gate.
**Sketch:** [peril-vocabulary.md](../sketches/peril-vocabulary.md)

## Scope

`ontology/applied/insurance/peril/` (epic D9) as the sketch's §4 lays out: `prl:` properties,
the cause scheme, characteristic and companion schemes, collections, intensity measures and
pools, with the §10 well-formedness shapes. Market editions are out of scope except one small
example edition used by the binding tests.

## Slices

| Slice | Content | Sketch | Notes |
|---|---|---|---|
| AIR-2.1 | `prl:` spec: kind and part sub-properties of `skos:broader` aligned to `iso-thes:`, `prl:canTrigger` (⊑ `skos:semanticRelation`), `prl:overlaps`, characteristic properties, Quantification and exposure links. Shapes of §10. `vocab/peril-vocab.ttl` created with its regions (lanes §4) | §6, §10 | unblocks Phase 4 |
| AIR-2.2 | characteristic schemes (mechanism, agency, onset, definition basis, accumulation class) and companion schemes (consequence, harm subject), bound to their `insurance/common/` contracts | §3, §6.3 | precedes the cause families, whose concepts must carry the mandatory characteristics |
| AIR-2.3 | cause scheme, families N, T and E | §5.1 to §5.3 | reference codes, one primary parent per concept |
| AIR-2.4 | cause scheme, families H, P, C, F and L, and every link between the two family groups | §5.4 to §5.8 | parallel with 2.3, merges after it |
| AIR-2.5 | collections: bundles, standard sets, model groupings. The open-perils condition example | §7 | milestone M1 |
| AIR-2.6 | intensity measure scheme, value spaces, defining thresholds, customary event windows, all in `peril-intensity.ttl` | §6.4 | Quantification only, no substrate change |
| AIR-2.7 | pools scheme and the example market edition bound by a scoped `voc:SchemeBinding` | §9.1, §9.4 | precedence tests: scoped binding wins, reference is the fallback |

Branches, machines and rounds: [machines, branches and merges](applied-insurance-reference-lanes.md).
Each slice is its own branch, even where one machine builds several in a row.

Each slice's pack includes an SKOS integrity case (no `skos:related` and no `prl:canTrigger`
within one `broaderTransitive` chain) and a reasoner-free parse and shapes run through
`check:ontology-catalog`.

## AIR-2.1 in detail

**Machine:** S (Copilot Business). **Branch:** `air/2.1-peril-spec`. **Validation Pack:**
[applied-insurance-reference-2.1](../validation/applied-insurance-reference-2.1.md), whose Handoff
section S fills in. **Decisions:** ADR-A98, ADR-A99. **Sketch:** peril vocabulary §4, §6, §10.

**Invariant:** the `prl:` properties exist with the characteristics ADR-A99 fixes, every peril
scheme of the reference edition is declared, and the vocabulary's well-formedness shapes accept
a well-formed fixture and reject each defect they name.

### Namespaces

| Document | Ontology IRI | Version IRI | Term namespace, prefix |
|---|---|---|---|
| `spec/peril.ttl` | `https://www.nebularis.org/neuro-semantic/insurance/peril` | `…/insurance/peril/0.1.0` | `https://www.nebularis.org/neuro-semantic/insurance/peril#`, `prl:` |
| `vocab/peril-vocab.ttl` | `https://www.nebularis.org/neuro-semantic/insurance/peril/vocab` | `…/insurance/peril-vocab/0.1.0` | `https://www.nebularis.org/neuro-semantic/insurance/peril/vocab#`, `prl-voc:` |

Schemes and concepts are in `prl-voc:`, following ADR-A98 decision 6 (confirmed by the human,
2026-09-26). The sketches' examples write them as `prl:` (for example `prl:N.MET.TC`). Read those
as `prl-voc:`.

### Files

All under `ontology/applied/insurance/peril/`.

1. **`spec/peril.ttl`.** Imports, by exact version IRI: SKOS (`http://www.w3.org/2004/02/skos/core`),
   Foundation 0.3.0 and Quantification 0.5.0. Every term has `rdfs:label`, `rdfs:comment` and
   `fnd:utility`, as `ontology/vocabulary/spec/vocabulary.ttl` does. Declares:

   | Term | Declaration |
   |---|---|
   | `prl:broaderGeneric`, `prl:broaderPartitive` | `owl:ObjectProperty`, `rdfs:subPropertyOf skos:broader`, `owl:equivalentProperty` `iso-thes:broaderGeneric` and `iso-thes:broaderPartitive` respectively. The two `iso-thes:` properties (`http://purl.org/iso25964/skos-thes#`) are declared locally as `owl:ObjectProperty` with `rdfs:isDefinedBy <http://purl.org/iso25964/skos-thes>`. Do not `owl:imports` the thesaurus vocabulary |
   | `prl:canTrigger` | `owl:ObjectProperty`, `owl:IrreflexiveProperty`, `rdfs:subPropertyOf skos:semanticRelation`. Not symmetric, not transitive |
   | `prl:overlaps` | `owl:ObjectProperty`, `owl:SymmetricProperty`, `owl:IrreflexiveProperty`, `rdfs:subPropertyOf skos:related` |
   | `prl:typicalAgency`, `prl:onset`, `prl:definitionBasis`, `prl:typicalMechanism`, `prl:accumulationClass`, `prl:typicalConsequence`, `prl:harmSubject` | `owl:ObjectProperty`, domain and range `skos:Concept`. No `owl:FunctionalProperty`: cardinalities are the shapes' job |
   | `prl:intensityMeasure`, `prl:relevantAttribute`, `prl:minimumGeoPrecision` | `owl:ObjectProperty`, domain and range `skos:Concept` |
   | `prl:measuredOn` | `owl:ObjectProperty`, domain `skos:Concept`, range `qnt:ValueSpace` |
   | `prl:definingThreshold` | `owl:ObjectProperty`, domain `skos:Concept`, range `qnt:RangeSet` |
   | `prl:customaryEventWindow` | `owl:ObjectProperty`, domain `skos:Concept`, range `qnt:Quantity` |
   | `prl:ReferenceCode` | `rdfs:Datatype`, `owl:equivalentClass` a restriction of `xsd:string` with an `xsd:pattern` of the family class `[NTEHPCFL]` followed by `(\\.[A-Z]{2,4}){0,4}`, written as one Turtle string. It matches all 286 codes of sketch §5 |
   | `prl:CatModelCode` | `rdfs:Datatype`, `owl:equivalentClass` a restriction of `xsd:string` with `xsd:pattern "[A-Z0-9]{2,5}"` |

   Nothing else. Collection classes arrive with AIR-2.5.

2. **`vocab/peril-vocab.ttl`.** Imports `…/insurance/peril/0.1.0`, Vocabulary 0.3.0 and Foundation
   0.3.0. Declares eight schemes, each `a voc:ConceptScheme` with `fnd:hasIdentity` (a
   `fnd:PersistentIdentity` node), `fnd:hasGovernanceState fnd:Active`, `skos:prefLabel` and
   `skos:editorialNote "Reference edition published by LATTICE. Not a market standard."@en`, as
   `ontology/vocabulary/examples/conjunctive-scopes.ttl` declares schemes:
   `prl-voc:CauseScheme`, `prl-voc:AgencyScheme`, `prl-voc:MechanismScheme`,
   `prl-voc:OnsetScheme`, `prl-voc:DefinitionBasisScheme`, `prl-voc:AccumulationClassScheme`,
   `prl-voc:ConsequenceScheme`, `prl-voc:HarmSubjectScheme`. No concepts.

   After the schemes, empty regions, each opened and closed by a comment line, in this order:

   ```text
   # ==== BEGIN REGION agency (AIR-2.2) ====
   # ==== END REGION agency ====
   ```

   Regions: `agency`, `mechanism`, `onset`, `definition-basis`, `accumulation-class`,
   `consequence`, `harm-subject` (AIR-2.2). `cause-N`, `cause-T`, `cause-E` (AIR-2.3). `cause-H`,
   `cause-P`, `cause-C`, `cause-F`, `cause-L`, `cross-group-links` (AIR-2.4). Leave one blank line
   between an END line and the next BEGIN line, so later slices' insertions merge cleanly.

3. **`shapes/structural.ttl`, `shapes/constraints.ttl`, `shapes/.version`** (`0.1.0`). "Cause
   concept" means a concept with `skos:inScheme prl-voc:CauseScheme`. Shapes may use SHACL-SPARQL
   and SPARQL-based targets (the repository validates with pySHACL, `advanced=True`).

   | Shape | Rule | Severity |
   |---|---|---|
   | label and definition | every concept in a `prl-voc:` scheme has exactly one `skos:prefLabel` and one `skos:definition` in `@en` | Violation |
   | reference code | every cause concept has exactly one `skos:notation` typed `prl:ReferenceCode`. It is unique among cause concepts, and equals its primary parent's code plus one `.`-separated segment. A top concept's code is its family letter | Violation |
   | primary parent | every cause concept that is not a top concept of `prl-voc:CauseScheme` has exactly one value across `prl:broaderGeneric` and `prl:broaderPartitive` together. A second `skos:broader` needs a `skos:editorialNote` | Violation |
   | materialised broader | every `prl:broaderGeneric` or `prl:broaderPartitive` link also appears as `skos:broader` | Violation |
   | characteristics | every cause concept has at least one `prl:typicalAgency` in `prl-voc:AgencyScheme`, exactly one `prl:onset` in `prl-voc:OnsetScheme`, exactly one `prl:definitionBasis` in `prl-voc:DefinitionBasisScheme`, and at most one `prl:accumulationClass` in `prl-voc:AccumulationClassScheme` | Violation |
   | associative integrity | no `skos:related`, `prl:overlaps` or `prl:canTrigger`, in either direction, between two concepts one of which is `skos:broader+` of the other | Violation |
   | acyclic | no concept is `skos:broader+` of itself | Violation |
   | threshold definitions | a concept whose `prl:definitionBasis` is `prl-voc:Threshold` has a `prl:definingThreshold` | Violation |

   Not in this slice: the collections shape (AIR-2.5) and the crosswalk shape (AIR-3.4). The
   sketch's "overlap coverage on data" shape reads a consumer's wording statements, so it is not
   LATTICE's and is not built.

4. **`examples/well-formed.ttl`.** No `owl:Ontology`. A fragment that passes every shape: the
   top concepts `prl-voc:N` and `prl-voc:T`, `prl-voc:N.MET`, `prl-voc:N.MET.TC` with a part
   `prl-voc:N.MET.TC.SRG` (partitive), and `prl-voc:N.MET.TC.HUR` (generic, threshold-defined
   with a `prl:definingThreshold`). It declares the few characteristic concepts it uses
   (`prl-voc:Natural`, `prl-voc:Sudden`, `prl-voc:Physical`, `prl-voc:Threshold`) in their schemes,
   since AIR-2.2 has not landed. Reference codes follow §5 of the sketch.

5. **`tools/test_peril_vocabulary.py`.** Modelled on `tools/test_eligibility_examples.py`: data is
   the fixture plus `spec/peril.ttl` and `vocab/peril-vocab.ttl`, shapes are the two shape
   files, pySHACL with `advanced=True` and `inference="none"`. One test per row of the table
   below. Negative cases are small Turtle strings in the test, each breaking one rule of the
   fixture. It runs under `mise run check:ontology-catalog`, which runs every `tools/test_*.py`.

6. **`README.md`** for the module: purpose (link ADR-A99 and the sketch), files, namespaces, the
   regions and which slice owns each, the shapes table, and the three deferred shapes.

**Do not edit** `ontology/applied/README.md` or `docs/architecture/ontology-architecture.md`:
AIR-1.1 rewrites them in parallel. R adds the peril module's rows at verification, after AIR-1.1
has merged.

**On R at verification:** `mise run build:ontology-catalog` (stub catalogs for `spec/` and
`vocab/`), and `mise run build:ontology-releases` (release rows for the two documents and the
shapes directory).

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AIR21-01 | `spec/peril.ttl` and `vocab/peril-vocab.ttl` / loaded with their import closure / parse, every import resolves | L1 | + |
| AIR21-02 | the spec / read / `prl:canTrigger` is a sub-property of `skos:semanticRelation` and not of `skos:related`, `prl:overlaps` is declared symmetric, both irreflexive | L1 | + |
| AIR21-03 | the eight schemes / Vocabulary's shapes / conform | L1 | + |
| AIR21-04 | `examples/well-formed.ttl` / the peril shapes / no result | L1 | + |
| AIR21-05 | a concept without `skos:definition` / validated / label and definition violation | L1 | − |
| AIR21-06 | two cause concepts with one code, and a code not extending its parent's / validated / reference code violations | L1 | − |
| AIR21-07 | a non-top cause concept with both a generic and a partitive parent / validated / primary parent violation | L1 | − |
| AIR21-08 | `prl:broaderGeneric` without `skos:broader` / validated / materialised broader violation | L1 | − |
| AIR21-09 | a cause concept without `prl:onset` / validated / characteristics violation | L1 | − |
| AIR21-10 | `prl:overlaps` from a concept to its parent, and `prl:canTrigger` from an event to its part / validated / two associative integrity violations | L1 | − |
| AIR21-11 | a `skos:broader` cycle / validated / acyclic violation | L1 | − |
| AIR21-12 | a threshold-basis concept without `prl:definingThreshold` / validated / threshold violation | L1 | − |

## AIR-2.2 in detail

**Machine:** S (Copilot Business). **Branch:** `air/2.2-characteristics`. **Validation Pack:**
[applied-insurance-reference-2.2](../validation/applied-insurance-reference-2.2.md), whose Handoff
section S fills in. **Decisions:** ADR-A98 (decision 5), ADR-A99. **Sketch:** peril vocabulary §3,
§6.3.

**Invariant:** every characteristic and companion scheme holds its reference concepts, the four
schemes `insurance/common/` has contracts for are bound to them, and the characteristic
properties specialise `common/`'s properties so those contracts govern their values.

### Spec changes (`spec/peril.ttl`, 0.1.0 → 0.2.0, MINOR)

1. Import `…/insurance/common/0.1.0` as well. ADR-A98 decision 5 has `peril/` import `common/`,
   and AIR-2.1 was built before `common/` existed (flagged at AIR-1.2).
2. Four sub-property axioms, so a check on a `common/` property also reads the peril vocabulary:
   `prl:typicalAgency ⊑ icm:agency`, `prl:typicalMechanism ⊑ icm:mechanism`,
   `prl:typicalConsequence ⊑ icm:consequence`, `prl:harmSubject ⊑ icm:harmSubject`.
   `prl:onset`, `prl:definitionBasis` and `prl:accumulationClass` stay as they are: `common/` has
   no property for them, because only the peril vocabulary uses those axes.

### Vocabulary changes (`vocab/peril-vocab.ttl`, 0.1.0 → 0.2.0, MINOR)

1. Re-pin the spec import to `…/insurance/peril/0.2.0`, and add `…/insurance/common-vocab/0.1.0`
   (the contracts the bindings name).
2. Fill the seven characteristic and companion regions, and no other region. Every concept is
   `skos:Concept`, `skos:inScheme` its scheme, `skos:topConceptOf` its scheme (each scheme is flat),
   with one `skos:prefLabel` and one `skos:definition` in `@en`. Local names in UpperCamelCase:

   | Region | Scheme | Concepts |
   |---|---|---|
   | `agency` | `prl-voc:AgencyScheme` | `Natural`, `Accidental`, `Negligent`, `MaliciousCriminal`, `MaliciousPolitical`, `Sovereign`, `Belligerent`, `UndeterminedAgency` |
   | `mechanism` | `prl-voc:MechanismScheme` | `Shaking`, `Inundation`, `WindLoad`, `Fire`, `Explosion`, `Impact`, `Contamination`, `ElectricalOverstress`, `DataEncryption` |
   | `onset` | `prl-voc:OnsetScheme` | `Sudden`, `Gradual`, `Latent`, `Recurrent` |
   | `definition-basis` | `prl-voc:DefinitionBasisScheme` | `Physical`, `Designation`, `Threshold`, `WordingDefined`, `Statutory`, `Index` |
   | `accumulation-class` | `prl-voc:AccumulationClassScheme` | `Catastrophe`, `Systemic`, `Attritional` |
   | `consequence` | `prl-voc:ConsequenceScheme` | `DirectPhysicalDamage`, `BusinessInterruption`, `ExtraExpense`, `Recall`, `CleanUp`, `LiabilityToOthers`, `DefenceCosts` |
   | `harm-subject` | `prl-voc:HarmSubjectScheme` | `Property`, `Persons`, `FinancialInterest`, `DataAndSystems`, `Environment`, `Reputation` |

   `Explosion` is added to the sketch's mechanism list because peril vocabulary §6.8's cyber
   write-back names it. `UndeterminedAgency` avoids a clash with Eligibility's `Undetermined`.
3. Four bindings, after the scheme declarations: `icm-voc:AgencyContract voc:boundScheme
   prl-voc:AgencyScheme`, and likewise Mechanism, Consequence and HarmSubject. They are the
   reference fallback (ADR-A99 decision 1). A deployment binds its own editions by scope.

### Fixture and tests

1. `examples/well-formed.ttl` stops declaring `Natural`, `Sudden`, `Physical` and `Threshold`: the
   vocabulary now does. The test already loads the vocabulary with the fixture.
2. `tools/test_peril_vocabulary.py` gains AIR22-01 to AIR22-08 below. The existing tests stay
   unchanged.

**On R at verification:** catalogs, release rows and tags for `insurance-peril-v0.2.0` and
`insurance-peril-vocab-v0.2.0`. The shapes directory does not change.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AIR22-01 | the spec and vocabulary / loaded with their import closures / parse, every import resolves, the spec imports `common/` | L1 | + |
| AIR22-02 | the spec / read / the four sub-property axioms hold, and `prl:onset` specialises nothing | L1 | + |
| AIR22-03 | each of the seven schemes / read / holds exactly the concepts in the table, each a top concept of it | L1 | + |
| AIR22-04 | the vocabulary alone / the peril shapes / no result | L1 | + |
| AIR22-05 | the four contracts with the peril vocabulary / Vocabulary's shapes / conform, each bound to its scheme | L1 | + |
| AIR22-06 | the well-formed fixture, now without local characteristic concepts / the peril shapes / no result | L1 | + |
| AIR22-07 | a characteristic concept without `skos:definition` / the peril shapes / violation | L1 | − |
| AIR22-08 | a cause concept whose `prl:onset` is a mechanism concept / the peril shapes / characteristics violation | L1 | − |

## Documentation deltas

`ontology/applied/README.md` (module row), the module's own README (generated tables of §5),
`docs/architecture/ontology-architecture.md` §3 status row.

## Exit gate

M1 demonstrated. PV-O1 and PV-O2 closed in the module README.
