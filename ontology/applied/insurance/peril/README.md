<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Reference Peril Vocabulary (`prl:`)

Literate specification for the reference peril vocabulary, LATTICE's applied insurance domain's
default peril scheme ([ADR-A99](../../../../docs/architecture/decisions/ADR-A99-reference-vocabularies-and-peril-structure.md)),
built by the [`applied-insurance-reference`](../../../../docs/developer/plans/applied-insurance-reference.md)
epic, Phase 2. See ADR-A99 and the [peril vocabulary sketch](../../../../docs/developer/sketches/peril-vocabulary.md)
for the design this module implements.

## 1. Purpose and scope

A peril is what initiates a loss: an earthquake, a fire, a cyber attack, a trial of a drug. A
contract's drafter or its market is always free to define what a peril means for that contract
([ADR-A99](../../../../docs/architecture/decisions/ADR-A99-reference-vocabularies-and-peril-structure.md)
decision 1, mork-bridge sketch §2), so this module is a *reference*: the unscoped fallback a check
reaches when nothing more specific binds. It gives:

- a **cause scheme** (`prl-voc:CauseScheme`), a hierarchy of 287 reference perils in eight
  families (N natural, T technological/accidental, E error and omission, H human/criminal,
  P political, C cyber, F financial, L liability-adjacent), built region by region across
  AIR-2.2 to AIR-2.7
- seven **characteristic and companion schemes** (agency, mechanism, onset, definition basis,
  accumulation class, consequence, harm subject), one value per axis per cause concept
  (AIR-2.2)
- **kind and part** links aligned to [ISO 25964](http://purl.org/iso25964/skos-thes#)'s
  thesaurus relations, so the hierarchy distinguishes "is a kind of" from "is part of an
  occurrence of"
- **directed triggering** (`prl:canTrigger`) and **non-subsuming overlap** (`prl:overlaps`),
  for perils that cause each other or can describe the same physical event without either
  subsuming the other
- **intensity measures and thresholds** (AIR-2.6), linking a cause to the
  [Quantification](../../../quantification/README.md) value space its severity is measured on
- **collections** (AIR-2.5) and a small **example market edition** (AIR-2.7) for the precedence
  tests

```mermaid
flowchart TB
    subgraph families["CauseScheme: eight families (287 concepts)"]
        direction LR
        N["N natural\n(AIR-2.3)"] --- T["T technological\n(AIR-2.3)"] --- E["E error/omission\n(AIR-2.3)"]
        H["H human/criminal\n(AIR-2.4)"] --- P["P political\n(AIR-2.4)"] --- C["C cyber\n(AIR-2.4)"]
        F["F financial\n(AIR-2.4)"] --- L["L liability-adjacent\n(AIR-2.4)"]
    end
    families -- "prl:canTrigger, prl:overlaps,\nskos:related (cross-group-links)" --> families
    families -- "prl:typicalAgency, prl:onset,\nprl:definitionBasis, prl:accumulationClass" --> characteristics["characteristic schemes\n(AIR-2.2)"]
    families -- "prl:typicalMechanism, prl:typicalConsequence,\nprl:harmSubject" --> companions["companion schemes\n(AIR-2.2)"]
    families -- "prl:intensityMeasure" --> intensity["intensity measures\n(AIR-2.6)"]
    intensity -- "prl:measuredOn" --> valueSpace["qnt:ValueSpace\n(Quantification)"]
    families -- "prl:definingThreshold" --> rangeSet["qnt:RangeSet\n(Quantification)"]
```

## 2. Files and namespaces (ADR-A98 decision 6)

| File | Content | Namespace | Prefix | Version IRI |
|---|---|---|---|---|
| `spec/peril.ttl` | the `prl:` properties and datatypes only. No scheme, no concept | `https://www.nebularis.org/neuro-semantic/insurance/peril#` | `prl:` | `…/insurance/peril/0.4.0` |
| `vocab/peril-vocab.ttl` | the eight reference schemes, and the cause scheme's members | `https://www.nebularis.org/neuro-semantic/insurance/peril/vocab#` | `prl-voc:` | `…/insurance/peril-vocab/0.4.0` |
| `vocab/peril-intensity.ttl` | the intensity measure scheme and its `qnt:ValueSpace`s | as above | `prl-voc:` | AIR-2.6 |
| `vocab/peril-collections.ttl` | reference collections | as above | `prl-voc:` | AIR-2.5 |
| `crosswalk/*.ttl` | reviewed crosswalks from external code systems | — | — | AIR-3.4 |
| `shapes/` | well-formedness (§6), versioned by its own `.version` | — | — | `0.2.0` |

Sketches and this README write concept and scheme IRIs as `prl:` for brevity (for example
`prl:N.MET.TC`): read those as `prl-voc:`. Only properties and datatypes are `prl:`.

## 3. Namespace and prefixes

```turtle-spec
@prefix prl:     <https://www.nebularis.org/neuro-semantic/insurance/peril#> .
@prefix iso-thes: <http://purl.org/iso25964/skos-thes#> .
@prefix fnd:     <https://www.nebularis.org/neuro-semantic/lattice/foundation#> .
@prefix qnt:     <https://www.nebularis.org/neuro-semantic/lattice/quantification#> .
@prefix skos:    <http://www.w3.org/2004/02/skos/core#> .
@prefix owl:     <http://www.w3.org/2002/07/owl#> .
@prefix rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:    <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .
```

## 4. Extraction contract

- `turtle-spec` blocks generate `spec/peril.ttl`.
- `turtle-vocab` blocks generate `vocab/peril-vocab.ttl`, in document order: the ontology header
  and the eight scheme declarations, then one block per region of §5.2 and §5.3, in the order
  listed there. A region's block is empty until the slice that owns it fills it in place.
- `turtle-shapes` blocks generate, in order, `shapes/structural.ttl` (per-concept shapes) and
  `shapes/constraints.ttl` (cross-concept and hierarchy shapes, §6).
- `turtle-example` blocks are illustrative only. The real fixture lives in
  [`examples/well-formed.ttl`](examples/well-formed.ttl).

```bash
python3 tools/literate_extract.py ontology/applied/insurance/peril/README.md \
    --layer applied/insurance/peril --root . \
    --shapes shapes/structural.ttl shapes/constraints.ttl --check
```

## 5. The `prl:` properties

### 5.1 Kind and part, triggering, overlap, characteristics (ADR-A99 decision 4)

Two concepts in the cause scheme relate in one of four ways, each its own property so a reader
(and a shape) never has to guess which the plain `skos:broader`/`skos:related` hierarchy means:

```mermaid
classDiagram
    class SkosConcept["skos:Concept"]
    SkosConcept : broaderGeneric "is a kind of" --|> skos_broader
    SkosConcept : broaderPartitive "is part of an occurrence of" --|> skos_broader
    SkosConcept : canTrigger "can cause (directed, irreflexive)" --|> skos_semanticRelation
    SkosConcept : overlaps "describes the same event (symmetric)" --|> skos_related
    note for SkosConcept "A hurricane prl:broaderGeneric a tropical cyclone (kind).\nA storm surge prl:broaderPartitive a tropical cyclone (part).\nAn earthquake prl:canTrigger a tsunami (directed cause).\nStorm surge prl:overlaps coastal flood (same event, neither subsumes)."
```

`prl:broaderGeneric` and `prl:broaderPartitive` are each a `skos:broader` sub-property, aligned to
[ISO 25964](http://purl.org/iso25964/skos-thes#)'s SKOS-THES vocabulary (`iso-thes:broaderGeneric`,
`iso-thes:broaderPartitive`), declared locally since ISO 25964's own vocabulary is never
`owl:imports`'d (PV3). Every value asserted through either one must also be asserted as plain
`skos:broader`, so a consumer reading only SKOS still sees the hierarchy (`MaterialisedBroaderShape`,
§6). `prl:canTrigger` is directed and irreflexive: the secondary effect stays classified under its
own initiating family, and the causal link never becomes a second `skos:broader` (PV2). `prl:overlaps`
is symmetric and irreflexive, for two concepts that are not in a kind or part relation but can both
describe one real event (whitepaper §3.5).

Six more properties link a cause concept to its typical characteristics, each a concept in its own
scheme (§7, §8):

```turtle-spec
<https://www.nebularis.org/neuro-semantic/insurance/peril>
    rdf:type owl:Ontology ;
    owl:versionIRI <https://www.nebularis.org/neuro-semantic/insurance/peril/0.4.0> ;
    rdfs:label "LATTICE reference peril vocabulary properties"@en ;
    rdfs:comment "The prl: properties and datatypes the reference peril vocabulary uses to say more than plain SKOS: kind and part links, directed triggering, non-subsuming overlap, characteristic links (mechanism, agency, onset, definition basis, accumulation class), and links to Quantification for intensity thresholds and event windows. Schemes and concepts are declared in vocab/peril-vocab.ttl, in the prl-voc: namespace (ADR-A98 decision 6). This document declares no scheme and no concept. See ADR-A99 and docs/developer/sketches/peril-vocabulary.md." ;
    owl:imports <http://www.w3.org/2004/02/skos/core> ,
                <https://www.nebularis.org/neuro-semantic/lattice/foundation/0.4.0> ,
                <https://www.nebularis.org/neuro-semantic/lattice/quantification/0.8.0> .

#################################################################
#    Kind and part (ADR-A99 decision 4, PV3). iso-thes: terms are
#    declared locally, per ISO 25964's own SKOS-THES vocabulary, and
#    never owl:imports'd.
#################################################################

iso-thes:broaderGeneric a owl:ObjectProperty ;
    rdfs:isDefinedBy <http://purl.org/iso25964/skos-thes> ;
    rdfs:label "has broader generic"@en ;
    rdfs:comment "ISO 25964 generic (kind-of) relation." .

iso-thes:broaderPartitive a owl:ObjectProperty ;
    rdfs:isDefinedBy <http://purl.org/iso25964/skos-thes> ;
    rdfs:label "has broader partitive"@en ;
    rdfs:comment "ISO 25964 partitive (part-of) relation." .

prl:broaderGeneric a owl:ObjectProperty ;
    rdfs:subPropertyOf skos:broader ;
    owl:equivalentProperty iso-thes:broaderGeneric ;
    rdfs:label "has broader generic"@en ;
    rdfs:comment "This concept is a kind of its broader concept (a hurricane is a kind of tropical cyclone)." ;
    fnd:utility "Use for a kind link in the cause scheme (marked K in the sketch). Every value asserted here must also be asserted as skos:broader (the materialised-broader shape checks this), so a plain SKOS consumer still sees the hierarchy." .

prl:broaderPartitive a owl:ObjectProperty ;
    rdfs:subPropertyOf skos:broader ;
    owl:equivalentProperty iso-thes:broaderPartitive ;
    rdfs:label "has broader partitive"@en ;
    rdfs:comment "This concept is part of an occurrence of its broader concept (a storm surge is part of a tropical cyclone event)." ;
    fnd:utility "Use for a part link in the cause scheme (marked P in the sketch). Every value asserted here must also be asserted as skos:broader, for the same reason as prl:broaderGeneric." .

#################################################################
#    Triggering and overlap (ADR-A99 decision 4)
#################################################################

prl:canTrigger a owl:ObjectProperty , owl:IrreflexiveProperty ;
    rdfs:subPropertyOf skos:semanticRelation ;
    rdfs:label "can trigger"@en ;
    rdfs:comment "One peril's occurrence can cause another's (an earthquake can trigger a tsunami). Directed: not symmetric, not transitive. skos:related is symmetric and cannot carry this." ;
    fnd:utility "Use for cross-family causal links (PV2): the secondary effect stays classified under its own initiating family, and the causal link is this property, never a second skos:broader. Both ends must be checked by the associative-integrity shape for accidental hierarchy crossing." .

prl:overlaps a owl:ObjectProperty , owl:SymmetricProperty , owl:IrreflexiveProperty ;
    rdfs:subPropertyOf skos:related ;
    rdfs:label "overlaps"@en ;
    rdfs:comment "Two perils can describe the same physical occurrence without one subsuming the other (tropical cyclone storm surge and coastal flood). Symmetric and irreflexive." ;
    fnd:utility "Use where two concepts are not in a kind or part relation to each other, but a real event can satisfy both (whitepaper §3.5). Never use this to avoid deciding a real broader link." .

#################################################################
#    Characteristics (ADR-A99 decision 4, PV1): one scheme per axis,
#    linked from cause concepts for typical values. Four of these
#    specialise insurance/common's own classification properties
#    (AIR-2.2), so a check on a common/ property also reads the peril
#    vocabulary: prl:onset and prl:definitionBasis have no common/
#    counterpart, since only the peril vocabulary uses those axes.
#################################################################

prl:typicalAgency a owl:ObjectProperty ;
    rdfs:domain skos:Concept ; rdfs:range skos:Concept ;
    rdfs:label "typical agency"@en ;
    rdfs:comment "A cause concept's typical agency (natural, accidental, negligent, malicious criminal, malicious political, sovereign, belligerent, undetermined), a concept in the agency scheme." ;
    fnd:utility "Link a cause concept to one or more agency values it is typically associated with. Several values are permitted (a peril is not always one agency); the characteristics shape requires at least one." .

prl:onset a owl:ObjectProperty ;
    rdfs:domain skos:Concept ; rdfs:range skos:Concept ;
    rdfs:label "onset"@en ;
    rdfs:comment "A cause concept's typical onset (sudden, gradual, latent, recurrent), a concept in the onset scheme." ;
    fnd:utility "Link a cause concept to exactly one onset value, the characteristics shape's own requirement." .

prl:definitionBasis a owl:ObjectProperty ;
    rdfs:domain skos:Concept ; rdfs:range skos:Concept ;
    rdfs:label "definition basis"@en ;
    rdfs:comment "What makes a cause concept exist as a distinct thing: physical, designation, threshold, wording-defined, statutory, or index (PV6), a concept in the definition-basis scheme." ;
    fnd:utility "Link a cause concept to exactly one definition-basis value. A value of prl-voc:Threshold requires prl:definingThreshold on the same concept (the threshold-definitions shape)." .

prl:typicalMechanism a owl:ObjectProperty ;
    rdfs:domain skos:Concept ; rdfs:range skos:Concept ;
    rdfs:label "typical mechanism"@en ;
    rdfs:comment "A cause concept's typical mechanism of harm (shaking, inundation, wind load, fire, impact, contamination, electrical overstress, data encryption, and others), a concept in the mechanism scheme." ;
    fnd:utility "Link a cause concept to one or more mechanism values. Not required by the characteristics shape in this slice; the mechanism scheme itself is built in AIR-2.2." .

prl:accumulationClass a owl:ObjectProperty ;
    rdfs:domain skos:Concept ; rdfs:range skos:Concept ;
    rdfs:label "accumulation class"@en ;
    rdfs:comment "A cause concept's typical accumulation character (catastrophe, systemic, attritional), a concept in the accumulation-class scheme." ;
    fnd:utility "Link a cause concept to at most one accumulation-class value. Optional: many perils have no single typical accumulation character." .

prl:typicalConsequence a owl:ObjectProperty ;
    rdfs:domain skos:Concept ; rdfs:range skos:Concept ;
    rdfs:label "typical consequence"@en ;
    rdfs:comment "A cause concept's typical head of loss (direct physical damage, business interruption, and others), a concept in the consequence scheme." ;
    fnd:utility "Informative only (PV8): records what is customary, never what a contract covers. The consequence scheme itself is built in AIR-2.2." .

prl:harmSubject a owl:ObjectProperty ;
    rdfs:domain skos:Concept ; rdfs:range skos:Concept ;
    rdfs:label "harm subject"@en ;
    rdfs:comment "What is typically harmed by a cause concept (property, persons, financial interest, data and systems, environment, reputation), a concept in the harm-subject scheme." ;
    fnd:utility "Informative only (PV8). Liability direction is derived from party roles, never from this property (term-parameters sketch §7)." .

#################################################################
#    Intensity and collections links (§6.4, §7 of the sketch). The
#    intensity measure scheme itself, its qnt:ValueSpaces, and
#    collection classes are built in AIR-2.6 and AIR-2.5.
#################################################################

prl:intensityMeasure a owl:ObjectProperty ;
    rdfs:domain skos:Concept ; rdfs:range skos:Concept ;
    rdfs:label "intensity measure"@en ;
    rdfs:comment "A cause concept's typical intensity measure (PGA, sustained wind, flood depth, and others), a concept in the intensity-measure scheme (AIR-2.6)." ;
    fnd:utility "Link a cause concept to the measure that quantifies its severity, where one is customary." .

prl:relevantAttribute a owl:ObjectProperty ;
    rdfs:domain skos:Concept ; rdfs:range skos:Concept ;
    rdfs:label "relevant attribute"@en ;
    rdfs:comment "An exposure attribute typically relevant when assessing this cause's hazard at a location (asset exposure ontology)." ;
    fnd:utility "Used by the exposure ontology's attribute assessments (Phase 4), not by this module's own shapes." .

prl:minimumGeoPrecision a owl:ObjectProperty ;
    rdfs:domain skos:Concept ; rdfs:range skos:Concept ;
    rdfs:label "minimum geographic precision"@en ;
    rdfs:comment "The coarsest location precision at which this cause's hazard can be meaningfully assessed." ;
    fnd:utility "Used by the exposure ontology (Phase 4), not by this module's own shapes." .

prl:measuredOn a owl:ObjectProperty ;
    rdfs:domain skos:Concept ; rdfs:range qnt:ValueSpace ;
    rdfs:label "measured on"@en ;
    rdfs:comment "The Quantification value space an intensity measure concept's values are expressed in." ;
    fnd:utility "Link an intensity measure concept (AIR-2.6) to its qnt:ValueSpace." .

prl:definingThreshold a owl:ObjectProperty ;
    rdfs:domain skos:Concept ; rdfs:range qnt:RangeSet ;
    rdfs:label "defining threshold"@en ;
    rdfs:comment "The Quantification range set a threshold-defined cause concept must fall within to be that cause (PV6)." ;
    fnd:utility "Required whenever prl:definitionBasis is prl-voc:Threshold (the threshold-definitions shape). Point at a qnt:RangeSet over the relevant intensity measure's value space." .

prl:customaryEventWindow a owl:ObjectProperty ;
    rdfs:domain skos:Concept ; rdfs:range qnt:Quantity ;
    rdfs:label "customary event window"@en ;
    rdfs:comment "The typical time span over which occurrences of this cause are customarily grouped into one event (PV8, informative only)." ;
    fnd:utility "Records custom, never decides occurrence grouping for a contract, which is a statement matter (§8 of the sketch)." .

#################################################################
#    Datatypes (§5's reference codes and open cat-model codes)
#################################################################

prl:ReferenceCode a rdfs:Datatype ;
    owl:equivalentClass [
        a rdfs:Datatype ;
        owl:onDatatype xsd:string ;
        owl:withRestrictions ( [ xsd:pattern "[NTEHPCFL](\\.[A-Z]{2,4}){0,4}" ] )
    ] ;
    rdfs:label "Reference code"@en ;
    rdfs:comment "A dotted reference code for a cause concept: a family letter (N, T, E, H, P, C, F or L) optionally followed by up to four dot-separated segments (§5)." ;
    fnd:utility "Type every cause concept's skos:notation with this datatype. The reference-code shape checks the stronger, parent-relative rule (a segment appended to the concept's own primary parent's code), which this pattern alone cannot express." .

prl:CatModelCode a rdfs:Datatype ;
    owl:equivalentClass [
        a rdfs:Datatype ;
        owl:onDatatype xsd:string ;
        owl:withRestrictions ( [ xsd:pattern "[A-Z0-9]{2,5}" ] )
    ] ;
    rdfs:label "Open cat-model code"@en ;
    rdfs:comment "An open catastrophe-model peril code (for example QEQ, WTC), recorded informatively where the sketch's §5 tables give one. No shape in this slice requires it." ;
    fnd:utility "Attach with a domain-appropriate property once the cause scheme carries model-code annotations (AIR-2.3, AIR-2.4)." .
```

## 5.2 The eight reference schemes

Each is a `voc:ConceptScheme`, an unscoped-fallback reference edition (ADR-A99 decision 1), marked
by `skos:editorialNote "Reference edition published by LATTICE. Not a market standard."`.

| Scheme | Axis |
|---|---|
| `prl-voc:CauseScheme` | the peril backbone (§5 of the sketch) |
| `prl-voc:AgencyScheme` | natural, accidental, negligent, intentional, malicious, sovereign, belligerent, economic, undetermined |
| `prl-voc:MechanismScheme` | how harm is inflicted |
| `prl-voc:OnsetScheme` | sudden, gradual, latent, recurrent |
| `prl-voc:DefinitionBasisScheme` | physical, designation, threshold, wording-defined, statutory, index |
| `prl-voc:AccumulationClassScheme` | catastrophe, systemic, attritional |
| `prl-voc:ConsequenceScheme` | heads of loss |
| `prl-voc:HarmSubjectScheme` | what is typically harmed |

```turtle-vocab
@prefix prl:     <https://www.nebularis.org/neuro-semantic/insurance/peril#> .
@prefix prl-voc: <https://www.nebularis.org/neuro-semantic/insurance/peril/vocab#> .
@prefix voc:     <https://www.nebularis.org/neuro-semantic/lattice/vocabulary#> .
@prefix fnd:     <https://www.nebularis.org/neuro-semantic/lattice/foundation#> .
@prefix skos:    <http://www.w3.org/2004/02/skos/core#> .
@prefix owl:     <http://www.w3.org/2002/07/owl#> .
@prefix rdf:     <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@base <https://www.nebularis.org/neuro-semantic/insurance/peril/vocab> .

<https://www.nebularis.org/neuro-semantic/insurance/peril/vocab>
    rdf:type owl:Ontology ;
    owl:versionIRI <https://www.nebularis.org/neuro-semantic/insurance/peril-vocab/0.4.0> ;
    owl:imports <https://www.nebularis.org/neuro-semantic/insurance/peril/0.4.0> ,
                <https://www.nebularis.org/neuro-semantic/lattice/vocabulary/0.4.0> ,
                <https://www.nebularis.org/neuro-semantic/lattice/foundation/0.4.0> .

#################################################################
#    The eight reference schemes (ADR-A99 §5, §6). Each is an
#    unscoped-fallback reference edition (ADR-A99 decision 1): never
#    a market standard, always the default when nothing more specific
#    is bound. No concepts in this slice: the cause scheme's own
#    members are added region by region, AIR-2.2 to AIR-2.4, each in
#    its own README section below (§5.2, §5.3).
#################################################################

prl-voc:CauseScheme a voc:ConceptScheme ;
    fnd:hasIdentity prl-voc:CauseScheme-identity ;
    fnd:hasGovernanceState fnd:Active ;
    skos:prefLabel "Reference cause of loss scheme"@en ;
    skos:editorialNote "Reference edition published by LATTICE. Not a market standard."@en .

prl-voc:AgencyScheme a voc:ConceptScheme ;
    fnd:hasIdentity prl-voc:AgencyScheme-identity ;
    fnd:hasGovernanceState fnd:Active ;
    skos:prefLabel "Reference agency scheme"@en ;
    skos:editorialNote "Reference edition published by LATTICE. Not a market standard."@en .

prl-voc:MechanismScheme a voc:ConceptScheme ;
    fnd:hasIdentity prl-voc:MechanismScheme-identity ;
    fnd:hasGovernanceState fnd:Active ;
    skos:prefLabel "Reference mechanism scheme"@en ;
    skos:editorialNote "Reference edition published by LATTICE. Not a market standard."@en .

prl-voc:OnsetScheme a voc:ConceptScheme ;
    fnd:hasIdentity prl-voc:OnsetScheme-identity ;
    fnd:hasGovernanceState fnd:Active ;
    skos:prefLabel "Reference onset scheme"@en ;
    skos:editorialNote "Reference edition published by LATTICE. Not a market standard."@en .

prl-voc:DefinitionBasisScheme a voc:ConceptScheme ;
    fnd:hasIdentity prl-voc:DefinitionBasisScheme-identity ;
    fnd:hasGovernanceState fnd:Active ;
    skos:prefLabel "Reference definition-basis scheme"@en ;
    skos:editorialNote "Reference edition published by LATTICE. Not a market standard."@en .

prl-voc:AccumulationClassScheme a voc:ConceptScheme ;
    fnd:hasIdentity prl-voc:AccumulationClassScheme-identity ;
    fnd:hasGovernanceState fnd:Active ;
    skos:prefLabel "Reference accumulation-class scheme"@en ;
    skos:editorialNote "Reference edition published by LATTICE. Not a market standard."@en .

prl-voc:ConsequenceScheme a voc:ConceptScheme ;
    fnd:hasIdentity prl-voc:ConsequenceScheme-identity ;
    fnd:hasGovernanceState fnd:Active ;
    skos:prefLabel "Reference consequence scheme"@en ;
    skos:editorialNote "Reference edition published by LATTICE. Not a market standard."@en .

prl-voc:HarmSubjectScheme a voc:ConceptScheme ;
    fnd:hasIdentity prl-voc:HarmSubjectScheme-identity ;
    fnd:hasGovernanceState fnd:Active ;
    skos:prefLabel "Reference harm-subject scheme"@en ;
    skos:editorialNote "Reference edition published by LATTICE. Not a market standard."@en .
```

## 5.3 Characteristic and companion schemes (AIR-2.2)

Each heading below is one README section, and the extraction contract (§4) concatenates its
`turtle-vocab` block into `vocab/peril-vocab.ttl` in the order the headings appear, after the
scheme declarations of §5.2. A block stays empty until the slice named fills it in place, in the
same position, so a later slice's diff is additive.

### Agency

```turtle-vocab
# Filled by AIR-2.2: Natural, Accidental, Negligent, Intentional, MaliciousCriminal,
# MaliciousPolitical, Sovereign, Belligerent, Economic, UndeterminedAgency.
```

### Mechanism

```turtle-vocab
# Filled by AIR-2.2: Shaking, GroundFailure, Inundation, WaterDamage, WindLoad, Load, Fire,
# Smoke, Heat, Freezing, Explosion, Impact, Collapse, Breakdown, Corrosion, Erosion,
# Contamination, BiologicalAgent, Radiation, ElectricalOverstress, DataEncryption, Deprivation.
```

### Onset

```turtle-vocab
# Filled by AIR-2.2: Sudden, Gradual, Latent, Recurrent.
```

### Definition basis

```turtle-vocab
# Filled by AIR-2.2: Physical, Designation, Threshold, WordingDefined, Statutory, Index.
```

### Accumulation class

```turtle-vocab
# Filled by AIR-2.2: Catastrophe, Systemic, Attritional.
```

### Consequence

```turtle-vocab
# Filled by AIR-2.2: DirectPhysicalDamage, BusinessInterruption, ExtraExpense, Spoilage,
# DenialOfAccess, Recall, CleanUp, DataRestoration, ExtortionPayment, LiabilityToOthers,
# DefenceCosts, Delay, ShortageOrNonDelivery, GeneralAverageContribution, ReputationalHarm,
# RegulatoryPenalty, NotificationCosts, ForensicCosts, CancellationCosts.
```

### Harm subject

```turtle-vocab
# Filled by AIR-2.2: Property, Persons, FinancialInterest, DataAndSystems, Environment,
# Reputation.
```

## 5.4 The cause scheme (AIR-2.3, AIR-2.4)

287 reference peril concepts in eight families, each region its own README section. See the
[peril vocabulary sketch](../../../../docs/developer/sketches/peril-vocabulary.md) §5 for the
full tables these regions implement, and the phase 2 plan's AIR-2.3/AIR-2.4 briefs for the
inheritance, mechanism and definition rules.

### Cause: N (natural hazards)

```turtle-vocab
# Filled by AIR-2.3: 90 concepts (geophysical, hydrological, meteorological, climatological,
# biological, extraterrestrial), sketch §5.1.
```

### Cause: T (technological and accidental events)

```turtle-vocab
# Filled by AIR-2.3: 71 concepts, sketch §5.2.
```

### Cause: E (error and omission)

```turtle-vocab
# Filled by AIR-2.3: 15 concepts, sketch §5.3.
```

### Cause: H (human and criminal acts)

```turtle-vocab
# Filled by AIR-2.4: 37 concepts, sketch §5.4.
```

### Cause: P (political)

```turtle-vocab
# Filled by AIR-2.4: 36 concepts, sketch §5.5.
```

### Cause: C (cyber)

```turtle-vocab
# Filled by AIR-2.4: 17 concepts, sketch §5.6.
```

### Cause: F (financial)

```turtle-vocab
# Filled by AIR-2.4: 10 concepts, sketch §5.7.
```

### Cause: L (liability-adjacent)

```turtle-vocab
# Filled by AIR-2.4: 11 concepts, sketch §5.8.
```

### Cross-group links

```turtle-vocab
# Filled by AIR-2.4: every prl:canTrigger, prl:overlaps or skos:related link with one end in
# N, T or E and the other in H, P, C, F or L, and every link within H to L (sketch §8.1).
```

## 6. Shapes (ADR-A99 §10)

"Cause concept" means a concept with `skos:inScheme prl-voc:CauseScheme`. All shapes are
`sh:Violation` severity (no discouraged-but-valid case here). Structural shapes (per concept) are
in `shapes/structural.ttl`; cross-concept and hierarchy shapes are in `shapes/constraints.ttl`.

```mermaid
flowchart LR
    concept["a skos:Concept\nin a prl-voc: scheme"] --> LAD["LabelAndDefinitionShape\nexactly one prefLabel, definition"]
    concept --> DOC["DocumentationShape\nat least one skos:note (AIR-2.0)"]
    causeConcept["a cause concept"] --> RC["ReferenceCodeShape\nunique, parent-relative code"]
    causeConcept --> PP["PrimaryParentShape\nexactly one broaderGeneric/Partitive"]
    causeConcept --> MB["MaterialisedBroaderShape\nalso asserted as skos:broader"]
    causeConcept --> CH["CharacteristicsShape\nagency, onset, basis, accumulation"]
    causeConcept --> AI["AssociativeIntegrityShape\nno related/overlaps/canTrigger\nacross a broader+ chain"]
    causeConcept --> AC["AcyclicShape\nno concept is broader+ of itself"]
    causeConcept --> TD["ThresholdDefinitionShape\nThreshold basis needs definingThreshold"]
```

| Shape | Rule |
|---|---|
| `prl:LabelAndDefinitionShape` | every concept in a `prl-voc:` scheme has exactly one `skos:prefLabel` and one `skos:definition`, each `@en` |
| `prl:DocumentationShape` | every concept in a `prl-voc:` scheme has at least one `skos:note` in `@en` (§7, AIR-2.0) |
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

```turtle-shapes
# Structural (per-concept) shapes for the reference peril vocabulary (ADR-A99
# §10, applied-insurance-reference AIR-2.1). Cross-concept and hierarchy
# shapes are in constraints.ttl. "Cause concept" means a concept with
# skos:inScheme prl-voc:CauseScheme. Every sh:sparql query is SHACL-SPARQL,
# validated with pySHACL advanced=True (tools/test_peril_vocabulary.py).

@prefix sh:      <http://www.w3.org/ns/shacl#> .
@prefix skos:    <http://www.w3.org/2004/02/skos/core#> .
@prefix prl:     <https://www.nebularis.org/neuro-semantic/insurance/peril#> .
@prefix prl-voc: <https://www.nebularis.org/neuro-semantic/insurance/peril/vocab#> .

prl:LabelAndDefinitionShape
    a sh:NodeShape ;
    sh:targetClass skos:Concept ;
    sh:sparql [
        sh:message "A concept in a reference peril scheme needs exactly one skos:prefLabel and exactly one skos:definition, each tagged @en (ADR-A99 §10)." ;
        sh:select """
            PREFIX prl: <https://www.nebularis.org/neuro-semantic/insurance/peril#>
            PREFIX prl-voc: <https://www.nebularis.org/neuro-semantic/insurance/peril/vocab#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT $this WHERE {
              $this skos:inScheme ?scheme .
              FILTER (?scheme IN (prl-voc:CauseScheme, prl-voc:AgencyScheme, prl-voc:MechanismScheme,
                                  prl-voc:OnsetScheme, prl-voc:DefinitionBasisScheme,
                                  prl-voc:AccumulationClassScheme, prl-voc:ConsequenceScheme,
                                  prl-voc:HarmSubjectScheme))
              OPTIONAL { $this skos:prefLabel ?l . FILTER (LANG(?l) = "en") }
              OPTIONAL { $this skos:definition ?d . FILTER (LANG(?d) = "en") }
            }
            GROUP BY $this
            HAVING (COUNT(DISTINCT ?l) != 1 || COUNT(DISTINCT ?d) != 1)
        """ ] .

prl:CharacteristicsShape
    a sh:NodeShape ;
    sh:targetClass skos:Concept ;
    sh:sparql [
        sh:message "A cause concept needs at least one prl:typicalAgency (in the agency scheme), exactly one prl:onset (in the onset scheme), exactly one prl:definitionBasis (in the definition-basis scheme), and at most one prl:accumulationClass (in the accumulation-class scheme) (ADR-A99 §10)." ;
        sh:select """
            PREFIX prl: <https://www.nebularis.org/neuro-semantic/insurance/peril#>
            PREFIX prl-voc: <https://www.nebularis.org/neuro-semantic/insurance/peril/vocab#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT $this WHERE {
              $this skos:inScheme prl-voc:CauseScheme .
              OPTIONAL { $this prl:typicalAgency ?ag . ?ag skos:inScheme prl-voc:AgencyScheme }
              OPTIONAL { $this prl:onset ?on . ?on skos:inScheme prl-voc:OnsetScheme }
              OPTIONAL { $this prl:definitionBasis ?db . ?db skos:inScheme prl-voc:DefinitionBasisScheme }
              OPTIONAL { $this prl:accumulationClass ?ac . ?ac skos:inScheme prl-voc:AccumulationClassScheme }
            }
            GROUP BY $this
            HAVING (COUNT(DISTINCT ?ag) < 1 || COUNT(DISTINCT ?on) != 1 || COUNT(DISTINCT ?db) != 1 || COUNT(DISTINCT ?ac) > 1)
        """ ] .
```

```turtle-shapes
# Cross-concept and hierarchy shapes for the reference peril vocabulary
# (ADR-A99 §10, applied-insurance-reference AIR-2.1). Per-concept shapes are
# in structural.ttl. "Cause concept" means a concept with skos:inScheme
# prl-voc:CauseScheme. Every sh:sparql query is SHACL-SPARQL, validated with
# pySHACL advanced=True (tools/test_peril_vocabulary.py).

@prefix sh:      <http://www.w3.org/ns/shacl#> .
@prefix skos:    <http://www.w3.org/2004/02/skos/core#> .
@prefix prl:     <https://www.nebularis.org/neuro-semantic/insurance/peril#> .
@prefix prl-voc: <https://www.nebularis.org/neuro-semantic/insurance/peril/vocab#> .

prl:DocumentationShape
    a sh:NodeShape ;
    sh:targetClass skos:Concept ;
    sh:sparql [
        sh:message "A concept in a reference peril scheme needs at least one skos:note in @en, naming the published standards, scales or sources it follows, and where it departs from them (AIR-2.0 documentation rule, §7)." ;
        sh:select """
            PREFIX prl-voc: <https://www.nebularis.org/neuro-semantic/insurance/peril/vocab#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT $this WHERE {
              $this skos:inScheme ?scheme .
              FILTER (?scheme IN (prl-voc:CauseScheme, prl-voc:AgencyScheme, prl-voc:MechanismScheme,
                                  prl-voc:OnsetScheme, prl-voc:DefinitionBasisScheme,
                                  prl-voc:AccumulationClassScheme, prl-voc:ConsequenceScheme,
                                  prl-voc:HarmSubjectScheme))
              OPTIONAL { $this skos:note ?n . FILTER (LANG(?n) = "en") }
            }
            GROUP BY $this
            HAVING (COUNT(DISTINCT ?n) < 1)
        """ ] .

prl:ReferenceCodeShape
    a sh:NodeShape ;
    sh:targetClass skos:Concept ;
    sh:sparql [
        sh:message "A cause concept needs exactly one skos:notation typed prl:ReferenceCode, unique among cause concepts, equal to its primary parent's code plus one '.'-separated segment, or to its family letter if it is a top concept (ADR-A99 §10, sketch §5)." ;
        sh:select """
            PREFIX prl: <https://www.nebularis.org/neuro-semantic/insurance/peril#>
            PREFIX prl-voc: <https://www.nebularis.org/neuro-semantic/insurance/peril/vocab#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT $this WHERE {
              $this skos:inScheme prl-voc:CauseScheme .
              OPTIONAL { $this skos:notation ?n . FILTER (DATATYPE(?n) = prl:ReferenceCode) }
            }
            GROUP BY $this
            HAVING (COUNT(DISTINCT ?n) != 1)
        """ ] ;
    sh:sparql [
        sh:message "A cause concept's reference code must be unique among cause concepts (ADR-A99 §10)." ;
        sh:select """
            PREFIX prl: <https://www.nebularis.org/neuro-semantic/insurance/peril#>
            PREFIX prl-voc: <https://www.nebularis.org/neuro-semantic/insurance/peril/vocab#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT $this WHERE {
              $this skos:inScheme prl-voc:CauseScheme ; skos:notation ?code .
              FILTER (DATATYPE(?code) = prl:ReferenceCode)
              ?other skos:inScheme prl-voc:CauseScheme ; skos:notation ?code .
              FILTER (DATATYPE(?code) = prl:ReferenceCode && ?other != $this)
            }
        """ ] ;
    sh:sparql [
        sh:message "A non-top cause concept's reference code must equal its primary parent's code plus exactly one '.'-separated segment (ADR-A99 §10, sketch §5)." ;
        sh:select """
            PREFIX prl: <https://www.nebularis.org/neuro-semantic/insurance/peril#>
            PREFIX prl-voc: <https://www.nebularis.org/neuro-semantic/insurance/peril/vocab#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT $this WHERE {
              $this skos:inScheme prl-voc:CauseScheme ; skos:notation ?code .
              FILTER (DATATYPE(?code) = prl:ReferenceCode)
              { $this prl:broaderGeneric ?parent } UNION { $this prl:broaderPartitive ?parent }
              ?parent skos:notation ?parentCode .
              FILTER (DATATYPE(?parentCode) = prl:ReferenceCode)
              FILTER (!STRSTARTS(STR(?code), CONCAT(STR(?parentCode), "."))
                      || CONTAINS(STRAFTER(STR(?code), CONCAT(STR(?parentCode), ".")), "."))
            }
        """ ] ;
    sh:sparql [
        sh:message "A top concept of the cause scheme's reference code must be exactly its family letter (N, T, E, H, P, C, F or L) (ADR-A99 §10, sketch §5)." ;
        sh:select """
            PREFIX prl: <https://www.nebularis.org/neuro-semantic/insurance/peril#>
            PREFIX prl-voc: <https://www.nebularis.org/neuro-semantic/insurance/peril/vocab#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT $this WHERE {
              $this skos:inScheme prl-voc:CauseScheme ; skos:notation ?code .
              FILTER (DATATYPE(?code) = prl:ReferenceCode)
              FILTER NOT EXISTS { $this prl:broaderGeneric ?p1 }
              FILTER NOT EXISTS { $this prl:broaderPartitive ?p2 }
              FILTER (!REGEX(STR(?code), "^[NTEHPCFL]$"))
            }
        """ ] .

prl:PrimaryParentShape
    a sh:NodeShape ;
    sh:targetClass skos:Concept ;
    sh:sparql [
        sh:message "A cause concept that is not a top concept of prl-voc:CauseScheme needs exactly one value across prl:broaderGeneric and prl:broaderPartitive together (ADR-A99 §10)." ;
        sh:select """
            PREFIX prl: <https://www.nebularis.org/neuro-semantic/insurance/peril#>
            PREFIX prl-voc: <https://www.nebularis.org/neuro-semantic/insurance/peril/vocab#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT $this WHERE {
              $this skos:inScheme prl-voc:CauseScheme .
              FILTER NOT EXISTS { prl-voc:CauseScheme skos:hasTopConcept $this }
              OPTIONAL { { $this prl:broaderGeneric ?p } UNION { $this prl:broaderPartitive ?p } }
            }
            GROUP BY $this
            HAVING (COUNT(DISTINCT ?p) != 1)
        """ ] ;
    sh:sparql [
        sh:message "A cause concept with more skos:broader values than its primary (broaderGeneric/broaderPartitive) values needs a skos:editorialNote explaining the extra one (ADR-A99 §10)." ;
        sh:select """
            PREFIX prl: <https://www.nebularis.org/neuro-semantic/insurance/peril#>
            PREFIX prl-voc: <https://www.nebularis.org/neuro-semantic/insurance/peril/vocab#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT $this WHERE {
              # Two independent counts, one sub-query each. Each anchors $this and makes
              # the counted pattern OPTIONAL, so a concept with none still gets a row (0).
              $this skos:inScheme prl-voc:CauseScheme .
              {
                SELECT $this (COUNT(DISTINCT ?b) AS ?nb) WHERE {
                  $this skos:inScheme prl-voc:CauseScheme .
                  OPTIONAL { $this skos:broader ?b }
                } GROUP BY $this
              }
              {
                SELECT $this (COUNT(DISTINCT ?p) AS ?np) WHERE {
                  $this skos:inScheme prl-voc:CauseScheme .
                  OPTIONAL { { $this prl:broaderGeneric ?p } UNION { $this prl:broaderPartitive ?p } }
                } GROUP BY $this
              }
              FILTER (?nb > ?np)
              FILTER NOT EXISTS { $this skos:editorialNote ?note }
            }
        """ ] .

prl:MaterialisedBroaderShape
    a sh:NodeShape ;
    sh:targetClass skos:Concept ;
    sh:sparql [
        sh:message "Every prl:broaderGeneric or prl:broaderPartitive link must also appear as skos:broader, so a plain SKOS consumer sees it (ADR-A99 §10)." ;
        sh:select """
            PREFIX prl: <https://www.nebularis.org/neuro-semantic/insurance/peril#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT $this WHERE {
              { $this prl:broaderGeneric ?p } UNION { $this prl:broaderPartitive ?p }
              FILTER NOT EXISTS { $this skos:broader ?p }
            }
        """ ] .

prl:AssociativeIntegrityShape
    a sh:NodeShape ;
    sh:targetClass skos:Concept ;
    sh:sparql [
        sh:message "skos:related, prl:overlaps and prl:canTrigger must never link two concepts where one is skos:broader+ of the other, in either direction (ADR-A99 §10)." ;
        sh:select """
            PREFIX prl: <https://www.nebularis.org/neuro-semantic/insurance/peril#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT $this WHERE {
              {
                { $this skos:related ?other } UNION { ?other skos:related $this }
                UNION { $this prl:overlaps ?other } UNION { ?other prl:overlaps $this }
                UNION { $this prl:canTrigger ?other } UNION { ?other prl:canTrigger $this }
              }
              { $this skos:broader+ ?other } UNION { ?other skos:broader+ $this }
            }
        """ ] .

prl:AcyclicShape
    a sh:NodeShape ;
    sh:targetClass skos:Concept ;
    sh:sparql [
        sh:message "No concept may be skos:broader+ of itself (ADR-A99 §10)." ;
        sh:select """
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT $this WHERE {
              $this skos:broader+ $this .
            }
        """ ] .

prl:ThresholdDefinitionShape
    a sh:NodeShape ;
    sh:targetClass skos:Concept ;
    sh:sparql [
        sh:message "A concept whose prl:definitionBasis is prl-voc:Threshold needs a prl:definingThreshold (ADR-A99 §10, PV6)." ;
        sh:select """
            PREFIX prl: <https://www.nebularis.org/neuro-semantic/insurance/peril#>
            PREFIX prl-voc: <https://www.nebularis.org/neuro-semantic/insurance/peril/vocab#>
            SELECT $this WHERE {
              $this prl:definitionBasis prl-voc:Threshold .
              FILTER NOT EXISTS { $this prl:definingThreshold ?t }
            }
        """ ] .
```

## 7. Documentation rule (AIR-2.0)

Every concept in a scheme this module publishes carries, beside its `skos:prefLabel` and
`skos:definition`:

| Property | Content |
|---|---|
| `skos:note` (`@en`, at least one, `prl:DocumentationShape` checks this) | which published standards, scales or sources the concept follows, how it follows them, and where it departs from them. For example: "Follows the IRDR Peril Classification's tropical cyclone. The basin names follow the WMO regional specialised meteorological centres. Unlike the IRDR entry, storm surge and rainfall flooding are parts of this concept, not separate hazards (PV2)." A concept no standard covers says so and names the usage it follows |
| `rdfs:seeAlso` | the IRI of a standard's own entry, where one is stable and public. Never a link to a paywalled or unofficial copy |
| `skos:scopeNote` | where the concept's boundary needs saying |
| `skos:exactMatch`, `skos:closeMatch` | to an external concept only where AIR-3.4's crosswalk rules allow, so not used by this module directly |

`skos:note` was chosen over `skos:editorialNote` because the alignment is for every reader of the
vocabulary, while an editorial note is for its maintainers.

## 8. Sources consulted

Filled as each region's concepts are drafted (AIR-2.2 to AIR-2.4), and cited by the `skos:note` on
each concept, never copied verbatim:

- the IRDR Peril Classification and Hazard Glossary (2014), whose natural-hazard families
  (geophysical, hydrological, meteorological, climatological, biological, extraterrestrial) are
  the N groups
- the UNDRR and ISC Hazard Information Profiles
- WMO definitions for tropical cyclone classes and the regional naming authorities
- the EM-DAT disaster classification
- the Oasis Open Exposure Data peril codes, for the model-code notations (`prl:CatModelCode`)
- the York-Antwerp Rules 2016, for general average
- the GDPR Articles 33, 34 and 83, for the first-party cyber and privacy heads of loss
- for T, E, H, P, C, F and L, which the sources above do not cover, common legal and market
  usage, stated neutrally

## 9. Fixture and tests

[`examples/well-formed.ttl`](examples/well-formed.ttl) is a small, real fragment of the cause
scheme (two family tops and a four-generation branch under `N.MET.TC`) that conforms to every
shape above. [`tools/test_peril_vocabulary.py`](../../../../tools/test_peril_vocabulary.py)
validates it, plus one negative case per shape by mutating a copy of the fixture, with pySHACL
(`advanced=True`, `inference="none"`), and checks the eight schemes conform to Vocabulary's own
shapes. Runs under `mise run check:ontology-catalog`, which runs every `tools/test_*.py`.

```turtle-example
prl-voc:N.MET.TC.HUR a skos:Concept ;
    skos:inScheme prl-voc:CauseScheme ;
    skos:prefLabel "Hurricane"@en ;
    skos:definition "A tropical cyclone at or above hurricane strength in the North Atlantic and eastern North Pacific basins."@en ;
    skos:notation "N.MET.TC.HUR"^^prl:ReferenceCode ;
    prl:broaderGeneric prl-voc:N.MET.TC ;
    skos:broader prl-voc:N.MET.TC ;
    prl:definitionBasis prl-voc:Threshold ;
    prl:definingThreshold ex:hurricane-wind-threshold .
```

## 10. PV-O3, PV-O4

Concept lifecycle across editions (PV-O3) and matching over generic links only (PV-O4) need
upstream changes (substrate track S1, S2). Neither blocks this module's first release.

## 11. Release notes

| Version | Change |
|---|---|
| `0.1.0` | AIR-2.1: the `prl:` properties, kind/part/trigger/overlap/characteristic links, the eight reference schemes, the well-formedness shapes |
| `0.4.0` | re-pinned by the computable-contract-substrate unit's Foundation and Quantification cascades (no content change). AIR-2.0 (this slice) converts the module to a literate README and adds `prl:DocumentationShape` to `shapes/constraints.ttl`, bumping the shapes `.version` to `0.2.0` only |
| `0.5.0` | AIR-2.2: imports `insurance/common`, specialises four characteristic properties as its sub-properties, fills the characteristic and companion scheme regions |
