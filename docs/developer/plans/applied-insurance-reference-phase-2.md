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
| AIR-2.0 | literate `insurance/common` and `insurance/peril`, the extractor extended to nested modules and several vocabulary documents (ADR-A120 addendum), the documentation rule and its shape | — | added 2026-10-13, first slice of the trip |
| AIR-2.1 | `prl:` spec: kind and part sub-properties of `skos:broader` aligned to `iso-thes:`, `prl:canTrigger` (⊑ `skos:semanticRelation`), `prl:overlaps`, characteristic properties, Quantification and exposure links. Shapes of §10. `vocab/peril-vocab.ttl` created with its regions (lanes §4) | §6, §10 | unblocks Phase 4 |
| AIR-2.2 | characteristic schemes (mechanism, agency, onset, definition basis, accumulation class) and companion schemes (consequence, harm subject), bound to their `insurance/common/` contracts | §3, §6.3 | precedes the cause families, whose concepts must carry the mandatory characteristics |
| AIR-2.3 | cause scheme, families N, T and E | §5.1 to §5.3 | reference codes, one primary parent per concept |
| AIR-2.4 | cause scheme, families H, P, C, F and L, and every link between the two family groups | §5.4 to §5.8 | parallel with 2.3, merges after it |
| AIR-2.5 | collections: bundles, standard sets, model groupings. The open-perils condition example | §7 | milestone M1 |
| AIR-2.6 | intensity measure scheme, value spaces, defining thresholds, customary event windows, all in `peril-intensity.ttl` | §6.4 | Quantification only, no substrate change. Built before AIR-2.3 (lanes §4) |
| AIR-2.7 | pools scheme and the example market edition bound by a scoped `voc:SchemeBinding` | §9.1, §9.4 | precedence tests: scoped binding wins, reference is the fallback |

Branches, machines and rounds: [machines, branches and merges](applied-insurance-reference-lanes.md).
S slices share one branch, `air/applied-reference`, as commit ranges (lanes §2).

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

Schemes and concepts are in `prl-voc:`, following ADR-A98 decision 6 (confirmed,
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
   | `prl:ReferenceCode` | `rdfs:Datatype`, `owl:equivalentClass` a restriction of `xsd:string` with an `xsd:pattern` of the family class `[NTEHPCFL]` followed by `(\\.[A-Z]{2,4}){0,4}`, written as one Turtle string. It matches all 287 codes of sketch §5 |
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

## AIR-2.0 in detail

**Machine:** S. **Branch:** `air/applied-reference`, commits `[AIR-2.0] …`, the last being
`[AIR-2.0] Handoff`. The first slice of the trip. **Validation Pack:**
[applied-insurance-reference-2.0](../validation/applied-insurance-reference-2.0.md).
**Decisions:** ADR-A120 (literate specs with several documents), with the addendum below.

**Why (decided 2026-10-13).** Every AIR module the trip creates or changes is literate: its
`README.md` is the source, and its Turtle is extracted from it, as Wording, Behaviour, Surface,
Quantification and Instrument already are. The vocabularies are documented to the standard a
reference vocabulary needs: every concept says which published standards, scales or sources it
follows (the documentation rule below).

**Invariant:** `insurance/common` and `insurance/peril` are literate. Extracting either README
reproduces its committed Turtle, up to formatting, and a test fails when they diverge.

### The extractor (`tools/literate_extract.py`)

ADR-A120 serves top-level layers with one vocabulary document. AIR needs nested modules and
several vocabulary documents (`peril-vocab.ttl`, `peril-intensity.ttl`, `peril-collections.ttl`).

1. `--layer` accepts a path under `ontology/`, for example `applied/insurance/peril`. Default
   targets use its last segment: `spec/peril.ttl`, `vocab/peril-vocab.ttl`. Paths without a `/`
   behave exactly as today.
2. The `# @output-file "…"` directive is read on the first line of a `turtle-vocab` block as well,
   and must name a `.ttl` under the module's `vocab/`. A redirected vocabulary document gains the
   `@prefix` lines of the default vocabulary document's blocks, as a redirected spec document does.
3. A module's vocabulary documents carry one version, as its spec documents do (ADR-A120 decision
   3). Extraction fails if their `owl:versionIRI` versions differ. A module's spec and vocabulary
   versions remain independent of each other.

Tests in `tools/test_literate_extract.py`, added to the existing ones, which stay unchanged:

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AIR20-01 | a README for a nested module with one spec and one vocab block / extract / `spec/<last>.ttl` and `vocab/<last>-vocab.ttl` under the nested directory | L1 | + |
| AIR20-02 | a `turtle-vocab` block with `@output-file "vocab/x-extra.ttl"` / extract / that file, with the default vocabulary document's prefixes | L1 | + |
| AIR20-03 | two vocabulary documents at different versions / extract / fails, naming both | L1 | − |
| AIR20-04 | a vocabulary directive naming `spec/x.ttl` or a path outside the module / extract / fails | L1 | − |
| AIR20-05 | every literate layer of `main` / `--check` / unchanged result | L1 | + |

**ADR-A120 addendum.** Append to the ADR, dated 2026-10-13, Proposed until the trip merges:
"Decision 4 widens. The directive is read on `turtle-vocab` blocks too, a module's vocabulary
documents move in unison as its spec documents do, and `--layer` accepts a nested module path whose
last segment names its default documents. Motivated by the applied insurance modules, which have
several vocabulary documents and sit below `ontology/applied/`." Update `tools/README.md`, the
developer guide's literate-spec section and skill `lattice-ontology-authoring` to match.

### Converting `insurance/common` and `insurance/peril`

For each module, as TD-16 describes the conversion of a substrate layer:

1. Every Turtle construct of its spec, vocabulary and shape files goes into a fenced block of the
   right tag in its README, beside the prose that explains it. Keep every piece of the README's
   current content.
2. An "Extraction contract" section names every output file and the shape targets in order.
3. Regenerate the files from the README and compare them with `HEAD` for isomorphism (rdflib
   `isomorphic`). Only formatting may differ. Record the comparison in the Handoff.
4. No version changes. The content is unchanged.
5. A test per module runs `literate_extract --check`, as `tools/test_instrument.py` does for its
   layer. Add the commands to the module READMEs.

**Regions become README sections.** The comment regions of `peril-vocab.ttl` and of the exposure
documents were there to keep parallel branches from conflicting. The trip is sequential, so each
region becomes a README section of the same name, and a later slice adds its blocks under its
section. Read "region X" in the briefs below as "README section X".

### The documentation rule, for every slice of the trip

Every concept in a scheme the trip publishes (`prl-voc:`, `aeo-voc:`, `icm-voc:`, units) carries:

| Property | Content |
|---|---|
| `skos:prefLabel`, `skos:definition` (`@en`) | as AIR-2.1 requires |
| `skos:note` (`@en`, at least one) | which published standards, scales or sources the concept follows, how it follows them, and where it departs from them. For example: "Follows the IRDR Peril Classification's tropical cyclone. The basin names follow the WMO regional specialised meteorological centres. Unlike the IRDR entry, storm surge and rainfall flooding are parts of this concept, not separate hazards (PV2)." A concept no standard covers says so and names the usage it follows |
| `rdfs:seeAlso` | the IRI of a standard's own entry, where one is stable and public. Never a link to a paywalled or unofficial copy |
| `skos:scopeNote` | where the concept's boundary needs saying |
| `skos:exactMatch`, `skos:closeMatch` | to an external concept only where AIR-3.4's crosswalk rules allow, so not in this rule |

`skos:note` was chosen over `skos:editorialNote` because the alignment is for every reader of the
vocabulary, while an editorial note is for its maintainers. Each module README gains a "Sources
consulted" section listing every standard the notes cite, with its edition or date.

A new shape, "documentation", in `peril/shapes/constraints.ttl` (bumping the shapes `.version` to
`0.2.0`, once on the branch): every concept in a `prl-voc:` scheme has at least one `skos:note` in
`@en`. Violation. The exposure module's shapes carry the same rule from AIR-4.1. This slice adds the
shape, and the notes on the concepts `insurance/common` and AIR-2.1 already publish.

## AIR-2.2 in detail

**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[AIR-2.2] …`, the
last being `[AIR-2.2] Handoff`. **Validation Pack:**
[applied-insurance-reference-2.2](../validation/applied-insurance-reference-2.2.md), whose Handoff
section S fills in. **Decisions:** ADR-A98 (decision 5), ADR-A99. **Sketch:** peril vocabulary §3,
§6.3.

**Invariant:** every characteristic and companion scheme holds its reference concepts, the four
schemes `insurance/common/` has contracts for are bound to them, and the characteristic
properties specialise `common/`'s properties so those contracts govern their values.

### Versions (refreshed 2026-10-13)

CCS cascades moved every layer this slice pins since the brief was first written. The table is a
snapshot of `main` at `69cb7675`. At the start of the slice, read the live `owl:versionIRI` of each
document below and use those. If one differs from the table, use the live one and say so in the
Handoff.

| Document | Brief first pinned | Snapshot | Use |
|---|---|---|---|
| Foundation | 0.3.0 | 0.4.0 | already imported by `peril.ttl` and `peril-vocab.ttl`, no change |
| Vocabulary | 0.3.0 | 0.4.0 | already imported by `peril-vocab.ttl`, no change |
| Quantification | 0.5.0 | 0.8.0 | already imported by `peril.ttl`, no change |
| `insurance/common` | 0.1.0 | 0.5.0 | new import of `peril.ttl` |
| `insurance/common-vocab` | 0.1.0 | 0.5.0 | new import of `peril-vocab.ttl` |
| `insurance/peril` | 0.1.0 | 0.4.0 | bumped here to 0.5.0 |
| `insurance/peril-vocab` | 0.1.0 | 0.4.0 | bumped here to 0.5.0 |
| `insurance/peril` shapes | 0.1.0 | 0.1.0 | unchanged |

`peril.ttl` and `peril-vocab.ttl` were re-pinned by the CCS cascades without a slice of this epic
touching them, so they sit at 0.4.0 although AIR-2.1 released 0.1.0. The designs below are
unchanged. Only the numbers moved.

### Spec changes (`spec/peril.ttl`, 0.4.0 → 0.5.0, MINOR)

1. Import `…/insurance/common/0.5.0` as well. ADR-A98 decision 5 has `peril/` import `common/`,
   and AIR-2.1 was built before `common/` existed (flagged at AIR-1.2).
2. Four sub-property axioms, so a check on a `common/` property also reads the peril vocabulary:
   `prl:typicalAgency ⊑ icm:agency`, `prl:typicalMechanism ⊑ icm:mechanism`,
   `prl:typicalConsequence ⊑ icm:consequence`, `prl:harmSubject ⊑ icm:harmSubject`.
   `prl:onset`, `prl:definitionBasis` and `prl:accumulationClass` stay as they are: `common/` has
   no property for them, because only the peril vocabulary uses those axes.

### Vocabulary changes (`vocab/peril-vocab.ttl`, 0.4.0 → 0.5.0, MINOR)

1. Re-pin the spec import to `…/insurance/peril/0.5.0`, and add `…/insurance/common-vocab/0.5.0`
   (the contracts the bindings name).
2. Fill the seven characteristic and companion regions, and no other region. Every concept is
   `skos:Concept`, `skos:inScheme` its scheme, `skos:topConceptOf` its scheme (each scheme is flat),
   with one `skos:prefLabel` and one `skos:definition` in `@en`. Local names in UpperCamelCase:

   | Region | Scheme | Concepts |
   |---|---|---|
   | `agency` | `prl-voc:AgencyScheme` | `Natural`, `Accidental`, `Negligent`, `Intentional`, `MaliciousCriminal`, `MaliciousPolitical`, `Sovereign`, `Belligerent`, `Economic`, `UndeterminedAgency` |
   | `mechanism` | `prl-voc:MechanismScheme` | `Shaking`, `GroundFailure`, `Inundation`, `WaterDamage`, `WindLoad`, `Load`, `Fire`, `Smoke`, `Heat`, `Freezing`, `Explosion`, `Impact`, `Collapse`, `Breakdown`, `Corrosion`, `Erosion`, `Contamination`, `BiologicalAgent`, `Radiation`, `ElectricalOverstress`, `DataEncryption`, `Deprivation` |
   | `onset` | `prl-voc:OnsetScheme` | `Sudden`, `Gradual`, `Latent`, `Recurrent` |
   | `definition-basis` | `prl-voc:DefinitionBasisScheme` | `Physical`, `Designation`, `Threshold`, `WordingDefined`, `Statutory`, `Index` |
   | `accumulation-class` | `prl-voc:AccumulationClassScheme` | `Catastrophe`, `Systemic`, `Attritional` |
   | `consequence` | `prl-voc:ConsequenceScheme` | `DirectPhysicalDamage`, `BusinessInterruption`, `ExtraExpense`, `Spoilage`, `DenialOfAccess`, `Recall`, `CleanUp`, `DataRestoration`, `ExtortionPayment`, `LiabilityToOthers`, `DefenceCosts`, `Delay`, `ShortageOrNonDelivery`, `GeneralAverageContribution`, `ReputationalHarm`, `RegulatoryPenalty`, `NotificationCosts`, `ForensicCosts`, `CancellationCosts` |
   | `harm-subject` | `prl-voc:HarmSubjectScheme` | `Property`, `Persons`, `FinancialInterest`, `DataAndSystems`, `Environment`, `Reputation` |

   `Explosion` is added to the sketch's mechanism list because peril vocabulary §6.8's cyber
   write-back names it. `UndeterminedAgency` avoids a clash with Eligibility's `Undetermined`.

   **Amended again 2026-10-13, after the review of earlier designs.** Eight consequences added,
   the heads of loss that marine, construction, event and cyber covers name. `Delay` covers delay
   in start-up and transit delay (the notes cite the advance loss of profits and delay in start-up
   covers of the construction and marine markets). `ShortageOrNonDelivery` is cargo that does not
   arrive. `GeneralAverageContribution` is a cargo or hull owner's share of a general average
   sacrifice (notes cite the York-Antwerp Rules 2016). `ReputationalHarm` is the cost of
   responding to harm to reputation. `RegulatoryPenalty`, `NotificationCosts` and `ForensicCosts`
   are the first-party cyber and privacy heads of loss (notes cite the GDPR's Articles 33, 34 and
   83). `CancellationCosts` is the irrecoverable cost of a cancelled or abandoned event or
   journey. Whether a penalty is insurable is a matter of law, so its note says the consequence
   names a loss and not that cover for it is lawful.

   **Amended 2026-10-13, before S started.** The cause scheme's notes name mechanisms and
   consequences the first lists lacked (ground failure, burial and load, blast, deprivation,
   spoilage, extortion payment, data restoration, denial of access), and two kinds of agency had no
   value. Decided 2026-10-13: two agency values, `Intentional` (a deliberate act that is not a
   crime, such as a lawful strike or most employment wrongful acts) and `Economic` (the failure of
   a commercial counterparty, or market forces), thirteen mechanisms and four consequences. The
   lists are a first edition, to be refined after the trip.

   Definitions follow the style rules and sources of AIR-2.3 ("Definitions"). Each mechanism is
   how harm is done, not the event that does it (for example `Load` is "the weight of material
   bearing on a structure or object beyond what it was built to carry", and `WaterDamage` is "harm
   from water escaping from, or entering, a structure other than by flood"). `Breakdown` is the
   internal failure of machinery or electrical equipment. `Collapse` is the loss of a structure's
   ability to stand.
3. Four bindings, after the scheme declarations: `icm-voc:AgencyContract voc:boundScheme
   prl-voc:AgencyScheme`, and likewise Mechanism, Consequence and HarmSubject. They are the
   reference fallback (ADR-A99 decision 1). A deployment binds its own editions by scope.

### Fixture and tests

1. `examples/well-formed.ttl` stops declaring `Natural`, `Sudden`, `Physical` and `Threshold`: the
   vocabulary now does. The test already loads the vocabulary with the fixture.
2. `tools/test_peril_vocabulary.py` gains AIR22-01 to AIR22-08 below. The existing tests stay
   unchanged.

**On R at verification:** catalogs, release rows and tags for `insurance-peril-v0.5.0` and
`insurance-peril-vocab-v0.5.0`. The shapes directory does not change.

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

## Shared rules for AIR-2.3 and AIR-2.4

Both slices fill the cause scheme from sketch §5, one region per family, with nothing invented
beyond the rules below. Decided 2026-10-13 (characteristics Q1 to Q6 in the status record's
history).

### What each table row of sketch §5 becomes

| Sketch column or note | Turtle |
|---|---|
| Code | the local name, with dots kept (`prl-voc:N.MET.TC`), and `skos:notation "N.MET.TC"^^prl:ReferenceCode` |
| Concept | `skos:prefLabel` in `@en` |
| Link K or P | `prl:broaderGeneric` or `prl:broaderPartitive` to the primary parent, and the same as `skos:broader`. A top concept has `skos:topConceptOf prl-voc:CauseScheme` instead |
| model code in the last column (three capital letters, for example `QEQ`, `WTC`) | a second `skos:notation` typed `prl:CatModelCode`. These are Oasis Open Exposure Data peril codes |
| "alt label X" | `skos:altLabel "X"@en` |
| "`prl:overlaps` X" | `prl:overlaps prl-voc:X`, stated once, on the concept with the lower code in sort order. The property is symmetric |
| "`prl:canTrigger` from X" | `prl-voc:X prl:canTrigger` the row's concept, written on X |
| "`prl:canTrigger` X" | the row's concept `prl:canTrigger prl-voc:X` |
| "related X" | `skos:related prl-voc:X`, stated once, as for overlaps |
| "Mechanism: …", "agency …", "onset …", "definition basis …", "accumulation class …", "`prl:typicalConsequence` …" | superseded by the characteristic tables below, which already include them |
| every other note | a `skos:scopeNote` in `@en`, reworded as a statement about the concept, not about the sketch |

Every concept is `a skos:Concept` with `skos:inScheme prl-voc:CauseScheme`.

### Characteristics: inheritance and overrides

A concept takes each characteristic from the nearest concept on its primary-parent chain (itself
first) that the tables assign it, starting from the family default. S writes the resulting values
onto every concept: the shapes check each concept, and no reasoner fills them in. "None" in an
override means the concept, and those below it, carry no value for that optional characteristic.
Mechanism, consequence and harm subject inherit the same way, and a list replaces the inherited
list, it does not add to it.

### Definitions

The [peril vocabulary sketch](../sketches/peril-vocabulary.md) fixes the concepts. Their definitions are guided by published
standards, consulted and paraphrased, never copied:

- the IRDR Peril Classification and Hazard Glossary (2014), whose natural-hazard families (geophysical,
  hydrological, meteorological, climatological, biological, extraterrestrial) are the N groups
- the UNDRR and ISC Hazard Information Profiles
- WMO definitions for tropical cyclone classes and the regional naming authorities
- the EM-DAT disaster classification
- the Oasis Open Exposure Data peril codes, for the model-code notations
- for T, E, H, P, C, F and L, which those sources do not cover, common legal and market usage,
  stated neutrally

Rules for every `skos:definition`:

1. One sentence, genus then difference ("A tropical cyclone whose …").
2. What the event or condition is. Never what a policy does with it: no "covered", "excluded",
   "insured", "loss" in the coverage sense, or market meaning (PV8).
3. A threshold is named, not numbered ("hurricane strength"). The numbers live in
   `peril-intensity.ttl` (AIR-2.6).
4. A part (link P) is defined as a part of its parent event ("the damaging wind field of a
   tropical cyclone").
5. No text longer than a short phrase from any source. If a source's wording is the only
   natural one, reword it.

The module README gains a "Sources consulted" section listing the standards above.

**Sample, the N.MET group (drafted 2026-10-13, for the maintainer's review).** S drafts every other definition in this style, and changes the sample only as the review directs.

| Code | Definition |
|---|---|
| N.MET | A hazard arising from atmospheric processes lasting minutes to days. |
| N.MET.TC | A warm-core, non-frontal low-pressure system of organised convection and closed surface wind circulation that forms over tropical or subtropical waters. |
| N.MET.TC.WND | The damaging wind field of a tropical cyclone, including its gusts. |
| N.MET.TC.SRG | An abnormal rise of the sea above the predicted astronomical tide, driven by a tropical cyclone's wind and low pressure, together with the coastal inundation it causes. |
| N.MET.TC.RFL | Flooding caused by the rainfall of a tropical cyclone, apart from its storm surge. |
| N.MET.TC.TOR | A tornado formed within the circulation of a tropical cyclone, usually in its outer rainbands. |
| N.MET.TC.HUR | A tropical cyclone whose maximum sustained wind reaches hurricane strength in the North Atlantic or the central or eastern North Pacific basin. |
| N.MET.TC.TYP | A tropical cyclone whose maximum sustained wind reaches hurricane strength in the western North Pacific basin. |
| N.MET.TC.SEV | A tropical cyclone whose maximum sustained wind reaches hurricane strength in the South Pacific or Indian Ocean basins. |
| N.MET.TC.TST | A tropical cyclone whose maximum sustained wind is above tropical depression strength and below hurricane strength. |
| N.MET.TC.TDP | A tropical cyclone whose maximum sustained wind is below tropical storm strength. |
| N.MET.NS | A storm given a name by a recognised meteorological authority, whatever its type. |
| N.MET.ETC | A low-pressure system of the middle or high latitudes that draws its energy from horizontal temperature contrasts, typically along fronts. |
| N.MET.ETC.WND | The damaging wind field of an extratropical cyclone. |
| N.MET.ETC.SRG | A rise of the sea above the predicted tide driven by an extratropical cyclone's wind and low pressure, together with the coastal inundation it causes. |
| N.MET.SCS | A thunderstorm or system of thunderstorms intense enough to produce tornadoes, large hail, damaging straight-line wind or intense rainfall. |
| N.MET.SCS.TOR | A violently rotating column of air extending from a thunderstorm to the ground. |
| N.MET.SCS.HAI | Ice precipitation from a convective storm, in stones large enough to cause damage. |
| N.MET.SCS.SLW | Damaging non-rotating wind from a thunderstorm, such as a downburst or gust front. |
| N.MET.SCS.SLW.DER | A widespread, long-lived straight-line windstorm produced by a fast-moving band of thunderstorms, meeting stated criteria of path length and gust speed. |
| N.MET.SCS.LTG | An electrical discharge between a cloud and the ground, or within the atmosphere, together with its direct effects. |
| N.MET.SCS.HVR | Intense rainfall of short duration from convective storms. |
| N.MET.WIN | A cold-season storm or period of cold bringing snow, ice, freezing rain or low temperature. |
| N.MET.WIN.SNL | The weight of accumulated snow bearing on structures and objects. |
| N.MET.WIN.ICE | Rain or drizzle that freezes on contact with surfaces, building a coating of ice. |
| N.MET.WIN.BLZ | A winter storm combining strong wind with falling or blowing snow that reduces visibility for a sustained period. |
| N.MET.WIN.FRZ | Air temperature below the freezing point of water for long enough to freeze water in pipes, tanks or the ground. |
| N.MET.WIN.FRS | Ice formation on surfaces, or air temperature below freezing near the ground, harming crops and plants. |
| N.MET.LWS | A strong wind produced neither by a tropical or extratropical cyclone nor by a thunderstorm, such as a downslope or gap wind. |
| N.MET.DST | Strong wind lifting large amounts of sand or dust, reducing visibility and depositing particles. |

### Notes

Every concept also follows AIR-2.0's documentation rule: at least one `skos:note` naming the
standards it follows and where it departs, `rdfs:seeAlso` to a standard's stable entry where one
exists. For a cause concept the note names the IRDR or HIP entry it follows (N), or the usage it
follows (T to L), and states any difference in placement, such as a part kept under its event
family (PV2) where a standard lists it as a separate hazard. The N.MET sample's notes are written by
S with the rest.

### Links between slices

A `prl:canTrigger`, `prl:overlaps` or `skos:related` link whose two ends are both in N, T or E is
written by AIR-2.3, on the concept the mapping table names. A link with one end in N, T or E and
the other in H, P, C, F or L is written by AIR-2.4 in the `cross-group-links` region. A link
within H to L is written by AIR-2.4 in its family's region. `prl:definingThreshold` and
`prl:intensityMeasure` are not written here: AIR-2.6, which now precedes both slices, writes them in
`peril-intensity.ttl`.

## AIR-2.3 in detail

**Machine:** S. **Branch:** `air/applied-reference`, commits `[AIR-2.3] …`, the last being
`[AIR-2.3] Handoff`. **Validation Pack:**
[applied-insurance-reference-2.3](../validation/applied-insurance-reference-2.3.md).
**Decisions:** ADR-A99, the shared rules above. **Sketch:** peril vocabulary §5.1 to §5.3.

**Invariant:** every concept of sketch §5.1 to §5.3 exists once, with its code, its links to its
parent, and the characteristics the rules give it, and the vocabulary passes every peril shape.

**Versions.** No bump. AIR-2.2 bumped `peril-vocab.ttl` on this branch (lanes §1).

### Family defaults

| Family | Agency | Onset | Basis | Accumulation | Mechanism | Harm subject |
|---|---|---|---|---|---|---|
| N | Natural | Sudden | Physical | none | none | Property |
| T | Accidental | Sudden | Physical | Attritional | none | Property |
| E | Negligent, Accidental | Latent | Physical | Attritional | none | Property |

### Overrides

| Concept (and those below it) | Characteristic | Value |
|---|---|---|
| N.GEO.EQ, N.GEO.TSU, N.GEO.VOL, N.MET.TC, N.MET.NS, N.MET.ETC, N.MET.SCS, N.MET.WIN, N.HYD.FLD, N.CLI.WF, N.CLI.DRT | accumulation | Catastrophe |
| N.BIO.OUT.PAN, N.EXT.GMS | accumulation | Systemic |
| N.GEO.MM.SUB, N.GEO.MM.HVE, N.HYD.ERS, N.CLI.DRT, N.BIO.OUT, N.BIO.INF, N.BIO.CRD, N.BIO.ANI, N.BIO.MLD, N.BIO.ALG | onset | Gradual |
| N.CLI.WF | agency | UndeterminedAgency |
| N.MET.TC.HUR, N.MET.TC.TYP, N.MET.TC.SEV, N.MET.TC.TST, N.MET.TC.TDP, N.MET.SCS.SLW.DER, N.MET.WIN.BLZ | basis | Threshold |
| N.CLI.DRT, N.CLI.HTW, N.CLI.CLD | basis | Index |
| N.MET.NS, N.BIO.OUT.PAN | basis | Designation |
| N.BIO.OUT, N.CLI.HTW | harm subject | Persons |
| T.REL.ASB | onset | Latent |
| T.NUC | accumulation | Catastrophe |
| T.UTL | accumulation | Systemic |
| T.UTL | consequence | BusinessInterruption |
| T.EQB.TCF | consequence | Spoilage |
| E.DET | agency, onset | Natural, Gradual |
| E.HUM, E.TST | onset | Sudden |
| E.PRO | basis, harm subject | WordingDefined, FinancialInterest |
| E.PRD | harm subject | Property, Persons |

### Mechanisms

| Concept (and those below it) | Mechanism |
|---|---|
| N.GEO.EQ, N.GEO.EQ.SHK, N.GEO.EQ.AFT | Shaking |
| N.GEO.EQ.FFE | Fire |
| N.GEO.EQ.LIQ, N.GEO.EQ.LSD, N.GEO.MM | GroundFailure |
| N.GEO.EQ.SPL | WaterDamage |
| N.GEO.TSU | Inundation, Impact |
| N.GEO.VOL.ASH | Load, Contamination |
| N.GEO.VOL.LAV | Fire, Heat |
| N.GEO.VOL.PYR | Heat, Impact |
| N.GEO.VOL.LAH, N.GEO.MM.LS | Impact, GroundFailure |
| N.GEO.VOL.GAS | Contamination |
| N.GEO.MM.AVL | Impact, Load |
| N.MET.TC | WindLoad, Inundation |
| N.MET.TC.WND, N.MET.TC.TOR, N.MET.NS, N.MET.ETC, N.MET.SCS, N.MET.LWS | WindLoad |
| N.MET.TC.SRG, N.MET.TC.RFL, N.MET.ETC.SRG, N.MET.SCS.HVR, N.HYD.FLD | Inundation |
| N.MET.SCS.HAI | Impact |
| N.MET.SCS.LTG | ElectricalOverstress, Fire |
| N.MET.WIN, N.MET.WIN.BLZ | Load, WindLoad, Freezing |
| N.MET.WIN.SNL, N.MET.WIN.ICE | Load |
| N.MET.WIN.FRZ, N.MET.WIN.FRS, N.CLI.CLD | Freezing |
| N.MET.DST | Impact, Contamination |
| N.HYD.ERS | Erosion |
| N.HYD.WAV | Impact |
| N.CLI.HTW | Heat |
| N.CLI.WF | Fire, Smoke |
| N.BIO | BiologicalAgent |
| N.EXT.GMS | ElectricalOverstress |
| N.EXT.SRS | Radiation |
| N.EXT.MET | Impact |
| T.FIR | Fire, Smoke |
| T.EXP | Explosion |
| T.EQB | Breakdown |
| T.EQB.ELC | Breakdown, ElectricalOverstress |
| T.STR | Collapse |
| T.EOW | WaterDamage |
| T.REL | Contamination |
| T.REL.RAD, T.NUC | Radiation, Contamination |
| T.TRN, T.IMP, T.HND | Impact |
| T.TRN.MAR.SNK | Inundation |
| E.DET.COR | Corrosion |

### Files

`vocab/peril-vocab.ttl`, regions `cause-N`, `cause-T` and `cause-E` only. `README.md`: the
"Sources consulted" section and a concept count per family. No spec, shape or fixture change.

### Tests (`tools/test_peril_vocabulary.py`)

The data graph is the spec, the vocabulary and `peril-intensity.ttl` (AIR-2.6).

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AIR23-01 | the vocabulary / read / N has 90 concepts, T 71 and E 15 (sketch §5.1 to §5.3), and every code is present once | L1 | + |
| AIR23-02 | the vocabulary with `peril-intensity.ttl` / the peril shapes / no result | L1 | + |
| AIR23-03 | every N, T and E concept / read / has exactly one onset and one basis and at least one agency, each the value the rules give. Check five: N.CLI.WF.FOR UndeterminedAgency, N.MET.TC.HUR Threshold, E.DET.COR Natural and Gradual, T.REL.ASB Latent, N.BIO.OUT.PAN Designation and Systemic | L1 | + |
| AIR23-04 | N.GEO.EQ.FFE and N.MET.TC.SRG / read / partitive links and mechanisms Fire and Inundation | L1 | + |
| AIR23-05 | the vocabulary / read / every model code of §5.1 is a `prl:CatModelCode` notation on its concept | L1 | + |
| AIR23-06 | N.GEO.EQ / read / `prl:canTrigger` N.GEO.TSU.EQT, and N.MET.TC.SRG `prl:overlaps` N.HYD.FLD.CST | L1 | + |
| AIR23-07 | the vocabulary with N.MET.TC.HUR's onset removed / the peril shapes / characteristics violation | L1 | − |
| AIR23-08 | every definition / read / none contains "cover", "covered", "exclude", "insured" or "policy" | L1 | − |

The counts were taken from the sketch on 2026-10-13. If the sketch has changed since, use its counts and record the difference in the Handoff.

## AIR-2.4 in detail

**Machine:** S. **Branch:** `air/applied-reference`, commits `[AIR-2.4] …`.
**Validation Pack:** [applied-insurance-reference-2.4](../validation/applied-insurance-reference-2.4.md).
**Decisions:** ADR-A99, the shared rules above. **Sketch:** peril vocabulary §5.4 to §5.8, §8.1.

**Invariant:** as AIR-2.3, for H, P, C, F and L, and every link between the two family groups
exists once in `cross-group-links`.

**Versions.** No bump.

### Family defaults

| Family | Agency | Onset | Basis | Accumulation | Mechanism | Harm subject |
|---|---|---|---|---|---|---|
| H | MaliciousCriminal | Sudden | Physical | Attritional | none | Property |
| P | Belligerent, MaliciousPolitical, Sovereign | Sudden | WordingDefined | Catastrophe | none | Property |
| C | UndeterminedAgency | Sudden | WordingDefined | none | none | DataAndSystems |
| F | Economic | Sudden | WordingDefined | none | none | FinancialInterest |
| L | Natural | Gradual | Physical | none | none | Persons |

P is wording-defined throughout: the market decides these events by the war, terrorism, strike
riot and civil commotion, and political risk definitions in the wording. A statutory definition,
such as one a terrorism pool certifies, comes in through a market edition (decided 2026-10-13).

### Overrides

| Concept (and those below it) | Characteristic | Value |
|---|---|---|
| H.FRD, H.EXT | harm subject | FinancialInterest |
| H.FRD.EMD | onset | Gradual |
| H.EXT.KID, H.VIO | harm subject | Persons |
| H.VIO.ABS | onset | Latent |
| H.WRA | agency, onset, basis, harm subject | Negligent and Intentional, Latent, WordingDefined, FinancialInterest |
| H.WRA.EMP | agency | Intentional |
| H.WRA.DEF | harm subject | Reputation |
| P.WAR | agency | Belligerent |
| P.WAR.CYW | agency, harm subject | Sovereign and Belligerent, DataAndSystems |
| P.TER | agency | MaliciousPolitical |
| P.TER.CYT | harm subject | DataAndSystems |
| P.PV | agency | MaliciousPolitical |
| P.PV.STK | agency | Intentional |
| P.GOV | agency, accumulation, harm subject | Sovereign, none, FinancialInterest |
| P.GOV.DEP | onset | Gradual |
| P.GOV.ACA | harm subject, consequence | Property, DenialOfAccess |
| C.MAL | agency | MaliciousCriminal, MaliciousPolitical, Sovereign |
| C.NML | agency | Accidental, Negligent |
| C.MAL.SUP, C.NML.SVC | accumulation | Systemic |
| C.MAL.RAN | consequence | ExtortionPayment, DataRestoration |
| C.MAL.OTA, C.NML.OTF | harm subject | Property, DataAndSystems |
| F.DEF.SOV | agency, accumulation | Sovereign, Systemic |
| F.DEF.NPY | onset | Gradual |
| F.INS | basis | Statutory |
| F.MKT | onset, basis, accumulation | Gradual, Index, Systemic |
| L.MOR | agency, onset | Natural and Accidental, Sudden |
| L.ACC | agency, onset | Accidental, Sudden |
| L.MED | agency, onset | Negligent, Sudden |
| L.OCD | agency, onset, basis | Negligent, Latent, Statutory |
| L.LNG | basis, accumulation | Index, Systemic |
| L.MRB.CRI, L.MRB.DIS, L.MRB.LTC | basis | WordingDefined |

### Mechanisms

| Concept (and those below it) | Mechanism |
|---|---|
| H.THF, H.FRD, H.EXT | Deprivation |
| H.MAL.VAN, H.VIO | Impact |
| H.MAL.ARS | Fire |
| H.MAL.TMP | Contamination |
| P.WAR | Explosion, Fire, Impact |
| P.WAR.SZR | Deprivation |
| P.WAR.CYW, P.TER.CYT | none |
| P.TER.CNV | Explosion, Fire |
| P.TER.CBR.CHM | Contamination |
| P.TER.CBR.BIO | BiologicalAgent |
| P.TER.CBR.RAD | Radiation, Contamination |
| P.TER.CBR.NUC | Radiation, Explosion |
| P.PV | Fire, Impact |
| P.PV.STK | none |
| P.GOV.EXP, P.GOV.CNF, P.GOV.NAT, P.GOV.DEP | Deprivation |
| C.MAL.RAN | DataEncryption |

### Files

`vocab/peril-vocab.ttl`, regions `cause-H` to `cause-L` and `cross-group-links`. `README.md`:
the concept counts.

### Tests

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AIR24-01 | the vocabulary / read / H has 37 concepts, P 36, C 17, F 10 and L 11 (sketch §5.4 to §5.8), 287 in the whole scheme, and every code is present once | L1 | + |
| AIR24-02 | the whole cause scheme with `peril-intensity.ttl` / the peril shapes / no result | L1 | + |
| AIR24-03 | the rules / read / H.WRA.EMP.DIS Intentional, P.PV.STK Intentional, F.INS Economic and Statutory, L.OCD Negligent, Latent and Statutory, C.NML.SWF Accidental and Negligent | L1 | + |
| AIR24-04 | the scheme / read / eight top concepts, N to L | L1 | + |
| AIR24-05 | `cross-group-links` / read / holds T.EQB.CTL overlaps C.NML.OTF, T.UTL.TEL overlaps C.NML.SVC, T.REL.RAD related P.TER.CBR.RAD, C.NML.CFG related E.HUM, L.MED related E.PRO, and C.MAL.OTA canTrigger T.FIR, T.EXP and T.EQB, and no link with both ends in one group | L1 | + |
| AIR24-06 | the scheme / a hierarchical condition requiring N to L and excluding N.HYD.FLD, evaluated as `tools/test_eligibility_examples.py` evaluates its examples / N.HYD.FLD.FLU Denied, P.TER.CNV Permitted | L2 | + |
| AIR24-07 | P.TER.CNV given `skos:related` to P.TER / the peril shapes / associative integrity violation | L1 | − |

## AIR-2.6 in detail

**Machine:** S. **Branch:** `air/applied-reference`, commits `[AIR-2.6] …`. Built after AIR-2.2
and before AIR-2.3 (lanes §4). **Validation Pack:**
[applied-insurance-reference-2.6](../validation/applied-insurance-reference-2.6.md).
**Decisions:** ADR-A99, Q7 to Q10 of 2026-10-13. **Sketch:** peril vocabulary §6.4, §11.

**Invariant:** each intensity measure has its own value space with a unit contract, the
threshold-defined cause concepts point at range sets on the spaces of their measures, and units are
declared once, aligned to QUDT.

### Units, in `insurance/common` (Q10)

Quantification ships no unit inventory. The units go in `common/`'s vocabulary, the lowest level
that covers peril and exposure (ADR-A98, D5), and move to a cross-domain module when a second
domain needs them. `common-vocab.ttl` is bumped once on the branch (MINOR).

| Unit family | Units (canonical first), each `skos:exactMatch` its QUDT unit |
|---|---|
| acceleration | standard gravity `unit:G`, `unit:M-PER-SEC2` |
| speed | `unit:M-PER-SEC`, `unit:KN`, `unit:MI-PER-HR`, `unit:KiloM-PER-HR` |
| pressure | `unit:KiloPA`, `unit:HectoPA` |
| length | `unit:M`, `unit:MilliM`, `unit:KiloM`, `unit:FT`, `unit:MI` |
| area | `unit:M2`, `unit:FT2` |
| mass per area | `unit:KiloGM-PER-M2` |
| power per length | `unit:KiloW-PER-M` |
| temperature | `unit:DEG_C` |
| duration | `unit:HR`, `unit:DAY`, `unit:MO`, `unit:YR` |
| currency | every currency in ISO 4217 List One, each `skos:exactMatch` its QUDT currency unit (`http://qudt.org/vocab/currency/`) |

QUDT is `http://qudt.org/vocab/unit/`. Check each IRI against QUDT's published unit vocabulary at
the start of the slice, and record any that does not resolve. Each conversion is a `qnt:Conversion`
with its exact factor (1 kn = 1852/3600 m/s, 1 mph = 0.44704 m/s, 1 g = 9.80665 m/s², 1 hPa =
0.1 kPa). Every unit carries a `skos:note` naming the SI definition or the convention it follows.

**Currencies (decided 2026-10-13, Q14).** Exposure, loss and requirement amounts need money units,
so `common/` declares every active currency of ISO 4217 List One as a `qnt:Unit` on one money
space, `icm-voc:Money`. Each has its alphabetic code as local name (`icm-voc:USD`), its numeric code
as `skos:notation`, its English name as `skos:prefLabel`, and a note citing ISO 4217 and giving its
minor unit (2 for USD, 0 for JPY, 3 for KWD). Funds codes and precious metals (`XAU`, `XDR` and the
like) are left out, and the note on the space says so. No conversion is declared between currencies:
a rate depends on a date and a source, so it is a `qnt:Conversion` under a `qnt:ConversionContext`
(Quantification's pattern), authored by whoever converts. S drafts the list from the standard. R
checks it against the maintenance agency's published List One at verification and records the
edition date in the README's "Sources consulted". The month and year are `qnt:CalendarUnit`s (ADR-A94),
for horizons and indemnity periods: their length in days depends on the calendar and the date
counted from, so any conversion to days is contextual and none is declared.

### Measures and their spaces (`vocab/peril-intensity.ttl`)

A new document, the intensity measure scheme `prl-voc:IntensityMeasureScheme` (flat) and one
`qnt:ValueSpace` per measure, linked by `prl:measuredOn`. A measure's averaging period or scale is
part of the measure, never of its unit (sketch §6.4).

| Measure | Space, canonical unit | Standard named in its note |
|---|---|---|
| `PeakGroundAcceleration` | g | USGS ShakeMap |
| `SpectralAcceleration` | g. The period is stated in the observation | USGS ShakeMap |
| `ModifiedMercalliIntensity` | ordinal, I to XII | the Modified Mercalli scale |
| `MomentMagnitude` | dimensionless | the moment magnitude scale |
| `SustainedWind1Min` | m/s | NHC, WMO averaging conventions |
| `MeanWind10Min` | m/s | WMO standard averaging |
| `WindGust3s` | m/s | WMO gust definition |
| `CentralPressure` | hPa | |
| `SaffirSimpsonCategory` | ordinal, 1 to 5 | Saffir–Simpson Hurricane Wind Scale |
| `EnhancedFujitaRating` | ordinal, EF0 to EF5 | NWS Enhanced Fujita scale |
| `FloodDepth` | m | |
| `FlowVelocity` | m/s | |
| `SurgeHeight` | m, above the predicted astronomical tide | |
| `RainfallDepth` | mm. The duration is stated in the observation | |
| `HailDiameter` | mm | |
| `IceAccretion` | mm, radial | the ASCE 7 ice-load convention |
| `SnowLoad` | kPa | |
| `AshLoad` | kg/m² | |
| `FirelineIntensity` | kW/m | Byram's fireline intensity |
| `StandardisedPrecipitationIndex` | dimensionless | the WMO-recommended drought index |
| `WarmSpellDurationIndex`, `ColdSpellDurationIndex` | days | the ETCCDI climate indices (Q8) |
| `Visibility` | m | |
| `PathLength` | km | |
| `EventDuration` | h | |

An ordinal measure's space is a `qnt:ValueSpace` with ordered ordinal concepts in a small scheme of
its own in the same document, each with a definition and a note.

### Threshold-defined concepts (Q7)

A concept with several defining thresholds meets all of them. AIR-2.6 adds that sentence to
`prl:definingThreshold`'s `rdfs:comment` in the spec (already bumped by AIR-2.2). Each threshold is
a `qnt:RangeSet` on the space of one of the concept's intensity measures.

| Concept | Intensity measures | Defining thresholds | Notes cite |
|---|---|---|---|
| N.MET.TC.HUR | `SustainedWind1Min` | ≥ 64 kn | NHC, Saffir–Simpson |
| N.MET.TC.TST | `SustainedWind1Min` | ≥ 34 kn and < 64 kn | NHC |
| N.MET.TC.TDP | `SustainedWind1Min` | < 34 kn | NHC, WMO tropical cyclone classification. The note says a depression is numbered but not named in the North Atlantic, so it is not a named storm (N.MET.NS) |
| N.MET.TC.TYP | `MeanWind10Min` | ≥ 64 kn | RSMC Tokyo (JMA). The note says JTWC's 1-minute figures belong in a market edition |
| N.MET.TC.SEV | `MeanWind10Min` | ≥ 64 kn | Australian Bureau of Meteorology (category 3 and above), RSMC La Réunion. The note says IMD's 3-minute convention belongs in a market edition |
| N.MET.SCS.SLW.DER | `WindGust3s`, `PathLength` | gusts ≥ 26 m/s, path ≥ 400 km | NOAA Storm Prediction Center |
| N.MET.WIN.BLZ | `SustainedWind1Min`, `Visibility`, `EventDuration` | wind ≥ 15.6 m/s, visibility < 400 m, ≥ 3 h | US National Weather Service. The note says other national definitions belong in market editions |

N.CLI.HTW and N.CLI.CLD are index-based (Q8), with `WarmSpellDurationIndex` and
`ColdSpellDurationIndex`, and N.CLI.DRT with `StandardisedPrecipitationIndex`. None has a defining
threshold. AIR-2.3's overrides table is amended to match.

### Other intensity links

| Concept | Intensity measures |
|---|---|
| N.GEO.EQ | `MomentMagnitude` |
| N.GEO.EQ.SHK | `PeakGroundAcceleration`, `SpectralAcceleration`, `ModifiedMercalliIntensity` |
| N.MET.TC.WND | `SustainedWind1Min`, `MeanWind10Min`, `WindGust3s`, `CentralPressure`, `SaffirSimpsonCategory` |
| N.MET.TC.SRG, N.MET.ETC.SRG, N.HYD.FLD.CST | `SurgeHeight`, `FloodDepth` |
| N.MET.TC.RFL, N.HYD.FLD | `FloodDepth`, `FlowVelocity` |
| N.HYD.FLD.PLU, N.MET.SCS.HVR | `RainfallDepth`, `FloodDepth` |
| N.MET.ETC.WND, N.MET.LWS, N.MET.SCS.SLW | `WindGust3s`, `MeanWind10Min` |
| N.MET.SCS.TOR, N.MET.TC.TOR | `EnhancedFujitaRating`, `WindGust3s` |
| N.MET.SCS.HAI | `HailDiameter` |
| N.MET.WIN.SNL | `SnowLoad` |
| N.MET.WIN.ICE | `IceAccretion` |
| N.GEO.VOL.ASH | `AshLoad` |
| N.CLI.WF | `FirelineIntensity` |

### Customary event windows (Q9, informative, PV8)

`prl:customaryEventWindow`, a `qnt:Quantity` on the duration space, on these concepts only. Each
carries a note saying the figure is the one hours clauses commonly use, and that the window that
applies is a contract term.

| Window | Concepts |
|---|---|
| 72 h | N.MET.TC, N.MET.NS, N.MET.ETC, N.MET.SCS, N.MET.LWS, P.PV.RIO, P.PV.CCM |
| 168 h | N.GEO.EQ, N.GEO.TSU, N.GEO.VOL, N.HYD.FLD |

### Files

`vocab/peril-intensity.ttl` (new, carrying the version of `peril-vocab.ttl`, AIR-2.0), its README
sections, and the units section of `common/`'s README. Links from cause concepts name them by IRI:
AIR-2.3 and AIR-2.4 declare them later in the trip.

### Tests

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AIR26-01 | the intensity document and `common/`'s vocabulary / loaded with their imports / parse, every import resolves | L1 | + |
| AIR26-02 | every measure / read / one `prl:measuredOn` space with a unit contract, or an ordinal scheme | L1 | + |
| AIR26-03 | every unit / read / one `skos:exactMatch` into QUDT, and each conversion's factor as listed | L1 | + |
| AIR26-04 | N.MET.TC.TYP / read / its threshold is on `MeanWind10Min`'s space, and HUR's on `SustainedWind1Min`'s | L1 | + |
| AIR26-05 | 30 m/s on the 10-minute space, and 34 m/s / compared with TYP's range / outside, inside | L2 | + |
| AIR26-06 | a value in knots / converted to m/s through the declared conversion / 64 kn is 32.92 m/s to two places | L2 | + |
| AIR26-07 | a threshold of HUR placed on `WindGust3s`'s space / the threshold shape / violation, the space is not one of HUR's measures | L1 | − |
| AIR26-08 | every measure, unit and ordinal concept / the documentation shape / each has a note | L1 | + |
| AIR26-09 | the currency units / read / every one is on `icm-voc:Money`, with a three-digit notation and a QUDT match, `USD`, `EUR`, `GBP` and `JPY` are present, and no conversion links two currencies | L1 | + |

## Documentation deltas

`ontology/applied/README.md` (module row), the module's own README (generated tables of §5),
`docs/architecture/ontology-architecture.md` §3 status row.

## Exit gate

M1 demonstrated. PV-O1 and PV-O2 closed in the module README.
