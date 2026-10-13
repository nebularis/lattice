<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Applied Insurance Reference — Phase 4, Exposure Ontology

**Unit ID:** `applied-insurance-reference-phase-4`
**Epic:** [applied-insurance-reference](applied-insurance-reference.md)
**Status:** Rolling-wave outline. Detailed at the Phase 1 gate, since it needs only Phase 1 and AIR-2.1.
**Sketch:** [asset-exposure-ontology.md](../sketches/asset-exposure-ontology.md)

## Scope

`ontology/applied/insurance/exposure/` (`aeo:`, `aeo-voc:`) as the sketch's §3 lays out. Facts
about the world, not about cover. No class the substrate already provides.

## Slices

| Slice | Content | Sketch |
|---|---|---|
| AIR-4.1 | exposure set, location, legal entity, control relations, asset, interest, valuation. Spec, vocabulary and shapes created with one region per slice (lanes §8) | §5.1 to §5.3, §5.5, §5.6 |
| AIR-4.2 | zones and pool participation, hazard attributes, assessments and profile shapes | §5.4, §5.7, §5.8 |
| AIR-4.3 | dependencies, peril metrics, exposure units derived on demand (no materialisation required) | §5.9 to §5.11 |
| AIR-4.4 | loss history with one `aeo:LossCause` node per link of the cause chain (peril, position, mechanism, agency), effective characteristic values defaulted from the cause's typical values as derived artefacts (epic D12), the loss event class in `insurance/common/` (D7), coverage requirements, existing cover, financial metrics | §5.12 to §5.14 |
| AIR-4.5 | liability exposure: counterparty populations, relationship depth, exposure bases | §5.15 |
| AIR-4.6 | London and US profiles as scheme bindings and shapes, the worked examples, and their persistence profiles (an aggregate boundary per exposure set version, a privacy profile for natural persons) | §10, §12, §5.2 |

After 4.1, 4.2 needs AIR-2.3, 2.4 and 2.6 (it links their concepts and uses their units), 4.3
needs 4.2 (it reuses `aeo:perilScope`), 4.4 needs 4.3 (requirement scopes range over exposure
units) and AIR-2.2, 4.5 needs 4.4 (its exposure bases are financial metrics), and 4.6 needs every
other slice and AIR-2.7 (revised 2026-10-13). Order and lanes:
[machines, branches and merges](applied-insurance-reference-lanes.md). S builds these slices on
`air/applied-reference`.

Milestone M3 closes in 4.3 and 4.6. Persistence profiles are deployment choices, so they are
authored with the worked examples in 4.6, not in the core.

**Review of earlier designs (2026-10-13).** Earlier private designs for exposure, catastrophe
modelling and reference data were compared with this plan, and ten gaps (R1 to R10) were decided,
recorded in the status record's history. Those for slices whose briefs are not yet written:

- AIR-4.3: peril metric perspectives aligned with Oasis's Open Results Data (ground-up, insured and
  reinsurance loss) and a calculation method, a scenario-loss metric kind (Lloyd's Realistic
  Disaster Scenarios, a client's own scenarios), and a concept-valued grouping property on
  location and asset under a drafter's scheme (a division, a portfolio, an OED location group),
  so requirement scopes can select by group (R8, R9).
- AIR-4.6: example zone editions (a national flood map, ASCE 7 seismic design categories, CRESTA
  zones), a Solvency II class of business edition, and example key schemes for insurance industry
  event identifiers.
- AIR-6.1: the earlier designs' carrier question bridge (questions, expected answer forms,
  placeholders, information gaps, client data requests), with the completeness warnings of AIR-4.2
  as its gaps and questionnaire answers as assessments.



**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[AIR-4.1] …`, the
last being `[AIR-4.1] Handoff`. **Validation Pack:**
[applied-insurance-reference-4.1](../validation/applied-insurance-reference-4.1.md), whose Handoff
section S fills in. **Decisions:** ADR-A98 (layout, namespaces), ADR-A102 (roles). **Sketch:**
asset exposure ontology §3, §5.1 to §5.3, §5.5, §5.6, §6, §8.

**Invariant:** an exposure set version, its locations, assets, interests and valuations, and the
parties and control relations behind them, exist on LATTICE's own constructs, with the regions
later Phase 4 slices fill.

**Coordination (revised 2026-10-13).** The computable-contract-substrate unit added keys to
Foundation (ADR-A114, slice F1, merged, Foundation 0.4.0): `fnd:Key` with a `fnd:KeyScheme` and a
value, `fnd:externalKey` and `fnd:naturalKey`. An organisation's registration and tax numbers and
its LEI are natural keys on the `aeo:LegalEntity`, and `aeo:identifier` and `aeo:Identifier` are
not built. The rows below use Foundation's keys. CCS slice C16c later removes Party's
`pty:outwardShare` and `pty:inwardShare`. `aeo:controlShare` is a `qnt:Quantity` on the control
relation and does not use them, so it is unaffected. Do not reuse Party's share properties here.

**Literate from the start (AIR-2.0, decided 2026-10-13).** The module's `README.md` is its source:
every Turtle construct below goes into a fenced block (`turtle-spec`, `turtle-vocab`,
`turtle-shapes`) beside the prose that explains it, with an "Extraction contract" section, a test
running `literate_extract --check` (`--layer applied/insurance/exposure`), and a "Sources
consulted" section. The regions below are README sections. Every concept in an `aeo-voc:` scheme
follows the documentation rule of AIR-2.0 (at least one `skos:note` naming the standards it follows,
for example ISO 4217 for currencies, the LEI standard ISO 17442 for legal entity identifiers, or a
national flood map's own zone definitions), and the shapes carry the documentation rule.

### Versions (refreshed 2026-10-13)

The brief first pinned the versions in the middle column. The right column is a snapshot of `main`
at `69cb7675`. At the start of the slice, read the live `owl:versionIRI` of each document and use
those. If one differs from the snapshot, use the live one and say so in the Handoff.

| Document | Brief first pinned | Snapshot |
|---|---|---|
| Foundation | 0.3.0 | 0.4.0 |
| Vocabulary | 0.3.0 | 0.4.0 |
| Quantification | 0.5.0 | 0.8.0 |
| Party | 0.5.0 | 0.9.0 |
| `insurance/common` | 0.1.0 | 0.5.0 |
| `insurance/common-vocab` | 0.1.0 | 0.5.0 |

The designs below are unchanged. `pty:Actor`, `pty:RoleOccupancy`, `qnt:ValueSpace`, `qnt:Quantity`,
`qnt:Unit`, `cls:territory`, `cls:assetClass` and `fnd:NaturallyKeyed` all still exist at the
snapshot versions.

### Namespaces

| Document | Ontology IRI | Version IRI | Prefix |
|---|---|---|---|
| `spec/exposure.ttl` | `https://www.nebularis.org/neuro-semantic/insurance/exposure` | `…/insurance/exposure/0.1.0` | `aeo:` (`…/insurance/exposure#`) |
| `vocab/exposure-vocab.ttl` | `…/insurance/exposure/vocab` | `…/insurance/exposure-vocab/0.1.0` | `aeo-voc:` (`…/insurance/exposure/vocab#`) |

The spec imports, by exact version IRI, the live versions of Foundation (0.4.0), Vocabulary (0.4.0),
Quantification (0.8.0), Party (0.9.0) and `…/insurance/common` (0.5.0, which brings
`classification/`). It does not import `peril/`: nothing in this slice uses it, and AIR-2.2 bumps it
in the same trip. AIR-4.3 adds the import with its first use. The vocabulary imports the spec 0.1.0
and the live `…/insurance/common-vocab` (0.5.0). Both new documents start at 0.1.0.

### Regions

Each of `spec/exposure.ttl`, `vocab/exposure-vocab.ttl`, `shapes/structural.ttl` and
`shapes/constraints.ttl` has these regions, opened and closed as `peril-vocab.ttl`'s are, with a
blank line between them: `core` (AIR-4.1, filled here), `zones-attributes-assessments` (4.2),
`dependencies-metrics-units` (4.3), `losses-requirements-cover` (4.4), `liability` (4.5). Only
`core` is filled here.

### Spec, `core` region

Every term with `rdfs:label`, `rdfs:comment` and `fnd:utility`. Classes, each `rdfs:subClassOf`
the mixins and restrictions in the sketch:

| Class | From | Notes |
|---|---|---|
| `aeo:ExposureSet` | §5.2 | `fnd:Version`, `fnd:Governable`, `fnd:TemporallyScoped`, `fnd:Evidenced`. `aeo:reportingUnit` to `qnt:Unit`. Identity class `aeo:ExposureIdentity ⊑ fnd:PersistentIdentity` |
| `aeo:Location` | §5.3 | `fnd:Version`. Identity `aeo:LocationIdentity`. `aeo:address` to `aeo:Address` (a node), `aeo:geometry` (range left open, GeoSPARQL alignment is optional), `aeo:geoPrecision`, `aeo:territory ⊑ cls:territory` |
| `aeo:LegalEntity` | §5.1 | `⊑ pty:Actor`, `⊑ fnd:NaturallyKeyed`. Registration and tax numbers and the LEI are `fnd:naturalKey`s, key nodes of declared `fnd:KeyScheme`s (Foundation README §8). A tax number's scheme is sensitive. Added 2026-10-13 (review R2): `aeo:industry ⊑ cls:industry` (0..*, no primary industry is privileged by the property, so a primary industry is an attribute of the entity's assessment), `aeo:domicile ⊑ cls:territory` (functional, the jurisdiction of incorporation or registration) and `aeo:legalForm` (functional). Trading names are `skos:altLabel`s of the entity. Entity status (active, dormant, in liquidation, dissolved) is an attribute type in AIR-4.2, because it changes over time and is evidenced like any assessment |
| `aeo:ControlRelation` | §5.1 | `fnd:TemporallyScoped`, `fnd:Evidenced`. `aeo:controller`, `aeo:controlled` (each exactly one `aeo:LegalEntity`), `aeo:controlKind`, optional `aeo:controlShare` (`qnt:Quantity`) |
| `aeo:Asset` | §5.5 | `fnd:Version`. Identity `aeo:AssetIdentity`. `aeo:assetClass ⊑ cls:assetClass`, `aeo:locatedAt` (functional) to `aeo:Location`, `aeo:partOf` (asymmetric, irreflexive), `aeo:presence` to `aeo:Presence` (location, temporal scope, optional `aeo:presenceShare`) |
| `aeo:Interest` | §5.5 | `fnd:TemporallyScoped`, `fnd:Evidenced`. `aeo:interestHolder` (`pty:RoleOccupancy`), `aeo:interestIn` (`aeo:Asset`), `aeo:interestKind`, optional `aeo:extent` (`qnt:Quantity`) |
| `aeo:Valuation` | §5.6 | `fnd:Evidenced`, `fnd:TemporallyScoped`. `aeo:valueOf` (asset or location), `aeo:valueType`, `aeo:valuationBasis`, optional `aeo:valuationMethod`, `aeo:amount`, or `aeo:rate` with `aeo:horizon` (all `qnt:Quantity`) |

Membership properties from the exposure set, each `owl:InverseFunctionalProperty`:
`aeo:hasLocation`, `aeo:hasAsset`, `aeo:hasInterest`, `aeo:hasValuation`. The other membership
properties of §5.2 arrive with their classes. Disjointness (§6) among this slice's classes, and
with `pty:Actor` for all but `aeo:LegalEntity`.

### Vocabulary, `core` region

For each concept-valued property of this slice, a `voc:SchemeContract` and a flat reference scheme
bound as its `voc:boundScheme`, declared as `peril-vocab.ttl` declares schemes:

| Contract, constrains | Reference concepts |
|---|---|
| `aeo-voc:GeoPrecisionContract`, `aeo:geoPrecision` | `Rooftop`, `Parcel`, `Street`, `Postcode`, `City`, `ZoneCentroid` |
| `aeo-voc:ControlKindContract`, `aeo:controlKind` | `Subsidiary`, `Affiliate`, `JointVenture`, `Branch`, `Franchise` |
| `aeo-voc:InterestKindContract`, `aeo:interestKind` | `Owner`, `Lessee`, `Lessor`, `SecuredLender`, `Bailee`, `Beneficiary` |
| `aeo-voc:ValueTypeContract`, `aeo:valueType` | `Building`, `Contents`, `Stock`, `Machinery`, `GrossProfit`, `Revenue`, `Rental`, `ExtraExpense`, `OtherValue` |
| `aeo-voc:ValuationBasisContract`, `aeo:valuationBasis` | `ReplacementCost`, `ActualCashValue`, `AgreedValue`, `MarketValue`, `FunctionalReplacement`, `Reinstatement` |
| `aeo-voc:ValuationMethodContract`, `aeo:valuationMethod` | `Declared`, `Appraised`, `Indexed`, `Modelled`, `Audited` |
| `aeo-voc:LegalFormContract`, `aeo:legalForm` | `Corporation`, `LimitedLiabilityCompany`, `Partnership`, `LimitedPartnership`, `SoleProprietorship`, `Trust`, `Mutual`, `Cooperative`, `Foundation`, `PublicBody`, `UnincorporatedAssociation` |

`aeo:territory`, `aeo:domicile`, `aeo:assetClass` and `aeo:industry` use the `cls-voc:` contracts
through their super-properties, so no contract is declared for them here.

**Notes for this slice's concepts (review of earlier designs, 2026-10-13).** The value types cite
the Open Exposure Data (OED) location fields they correspond to (`Building` to `BuildingTIV`,
`Contents` to `ContentsTIV`, `GrossProfit`, `Revenue` and `Rental` to `BITIV`, `Machinery`,
`Stock` and `OtherValue` to `OtherTIV`), and say where OED is coarser. The legal forms are generic
kinds. Their notes cite ISO 20275 (Entity Legal Forms), whose codes are per jurisdiction and run
to thousands, so a deployment binds an ISO 20275 edition by territory, mapped to these kinds by
`skos:broadMatch`. The reference scheme is the unscoped fallback. Programme roles, declared as `icm-voc:Claimant` is:
`aeo-voc:NamedInsured`, `FirstNamedInsured`, `AdditionalInsured`, `LossPayee`, `LendersLossPayee`,
`Mortgagee`, `LessorRole` (distinct from the interest kind `Lessor`), `Bailor` and
`WaiverOfSubrogationBeneficiary`. `LendersLossPayee` is narrower than `LossPayee` (review R10). Its
note cites the ISO commercial property loss payable provisions endorsement (CP 12 18), whose lender's
loss payable clause gives the lender rights a simple loss payee lacks, and the London market's
practice of noting a lender's interest with a loss payee clause. The waiver beneficiary's note says
the waiver itself is a contract term (Phase 5) and the role only names who benefits. The additional
insured variants by ISO endorsement (CG 20 10, CG 20 37, CG 20 38) are conferred by the contract and
wait for Phase 5.

### Shapes, `core` region, `.version` 0.1.0

Structural cardinalities as `sh:property` shapes. Rules that need SPARQL follow the house rules
in `.github/copilot-instructions.md` ("Authoring SHACL-SPARQL shapes").

| Shape | Rule |
|---|---|
| exposure set | exactly one identity, one reporting unit, one temporal scope, one governance state |
| location | exactly one identity, at least one territory. A location with a geometry has a geo precision |
| asset | exactly one identity and one asset class. Not both `aeo:locatedAt` and `aeo:presence` |
| interest | exactly one holder, one asset and one kind |
| valuation | exactly one `aeo:valueOf`, one value type and one basis. Either one amount, or one rate and one horizon, never both and never neither |
| control | exactly one controller and one controlled, and no cycle through `aeo:controller` / `aeo:controlled` |
| legal entity | at most one domicile and one legal form |
| membership | a member belongs to at most one exposure set version |

### Other files

- `examples/core.ttl`, no `owl:Ontology`: one exposure set version with two locations, a building
  and its contents, an owner's interest and a lender's, three valuations (one amount, one rate
  with a 12-month horizon), and a parent controlling the insured. The insured has an industry, a domicile and a legal form.
  Amounts use a currency unit declared in the example (`ex:GBP`), because `common/`'s currencies
  arrive with AIR-2.6, later in the trip. Passes every shape.
- `tools/test_exposure_ontology.py`, modelled on `tools/test_peril_vocabulary.py`.
- `README.md` for the module: purpose, files, namespaces, regions and their slices.
- The exposure row of `insurance/domain-README.md` and the applied insurance row of
  `docs/architecture/ontology-architecture.md` §3.

**On R at verification:** catalogs, and release rows and tags for `insurance-exposure-v0.1.0`,
`insurance-exposure-vocab-v0.1.0` and the shapes directory.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AIR41-01 | the spec and vocabulary / loaded with their import closures / parse, every import resolves, `peril/` is not imported | L1 | + |
| AIR41-02 | the seven contracts / Vocabulary's shapes / conform, each bound to its reference scheme | L1 | + |
| AIR41-03 | `aeo:territory` and `aeo:assetClass` / read / sub-properties of `cls:territory` and `cls:assetClass` | L1 | + |
| AIR41-04 | the example / the exposure shapes / no result | L1 | + |
| AIR41-05 | a location without a territory / validated / violation | L1 | − |
| AIR41-06 | an asset with both `aeo:locatedAt` and a presence / validated / violation | L1 | − |
| AIR41-07 | a valuation with an amount and a rate, and one with neither / validated / two violations | L1 | − |
| AIR41-08 | two entities each controlling the other / validated / cycle violation | L1 | − |
| AIR41-09 | a location in two exposure set versions / validated / membership violation | L1 | − |
| AIR41-10 | an exposure set without a reporting unit / validated / violation (the zero case) | L1 | − |
| AIR41-11 | the four shape files and the vocabulary / read / every region of later slices is present and empty | L0 | + |
| AIR41-12 | `aeo:industry`, `aeo:domicile` / read / sub-properties of `cls:industry` and `cls:territory`, and the legal form contract is bound to its reference scheme | L1 | + |
| AIR41-13 | a legal entity with two domiciles / validated / violation | L1 | − |
| AIR41-14 | `aeo-voc:LendersLossPayee` / read / `skos:broader` `aeo-voc:LossPayee`, and every role and legal form has a note | L1 | + |

## AIR-4.2 in detail

**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[AIR-4.2] …`, the
last being `[AIR-4.2] Handoff`. **Validation Pack:**
[applied-insurance-reference-4.2](../validation/applied-insurance-reference-4.2.md). **Decisions:**
ADR-A98, ADR-A99. **Sketch:** asset exposure ontology §5.3, §5.4, §5.7, §5.8, §7, §8.
**Decided 2026-10-13:** the proposal of that day (zones per hazard kind with empty reference
editions, attribute types after OED, assessment kinds, the peril links), Q13 (two worked profiles),
R6 (attribute types for all eight families, shapes for two) and the review's geospatial and
geocoding additions.

**Invariant:** a location carries zone designations and pool participations, every hazard
attribute arrives as an attribute value in an evidenced assessment, and the peril vocabulary says
which attributes and which geocoding precision each peril needs, so the shapes can warn when an
exposure set lacks them.

### Versions and imports

No document bumps. `spec/exposure.ttl`, `vocab/exposure-vocab.ttl` and the shapes directory are
new on the branch (AIR-4.1) and stay at `0.1.0` (lanes §2). The vocabulary adds imports of the
peril vocabulary and re-pins `insurance/common-vocab`, both at the versions on the branch (read
the live `owl:versionIRI`s: AIR-2.2 and AIR-2.6 bumped them). The spec imports nothing new: the
properties it specialises (`icm:pool`, `icm:peril`) are in `insurance/common`, already imported.

Everything below goes into the `zones-attributes-assessments` region of each document and README
section, and follows the documentation rule (AIR-2.0).

### Spec

| Term | Kind | Definition |
|---|---|---|
| `aeo:ZoneDesignation` | class | `⊑ fnd:Evidenced ⊓ fnd:TemporallyScoped`, exactly one `aeo:zone`, exactly one `aeo:designationSource`. The temporal scope is the map's effective period |
| `aeo:zoneDesignation` | property | location to zone designation, inverse functional |
| `aeo:zone` | property | designation to concept. Not used directly: each hazard kind has a sub-property, so each can be constrained by its own contract |
| `aeo:floodZone`, `aeo:seismicZone`, `aeo:windZone`, `aeo:wildfireZone`, `aeo:tsunamiZone`, `aeo:accumulationZone` | properties | `⊑ aeo:zone` |
| `aeo:designationSource` | property | designation to concept |
| `aeo:PoolParticipation` | class | `⊑ fnd:Evidenced ⊓ fnd:TemporallyScoped`, exactly one `aeo:pool`, at least one `aeo:perilScope` |
| `aeo:poolParticipation` | property | location to pool participation, inverse functional |
| `aeo:pool` | property | `⊑ icm:pool` |
| `aeo:perilScope` | property | `⊑ icm:peril`, not functional. Peril metrics (AIR-4.3) and existing cover (AIR-4.4) reuse it |
| `aeo:Assessment` | class | `⊑ fnd:Evidenced ⊓ fnd:TemporallyScoped`, at least one `aeo:assesses`, exactly one `aeo:assessmentKind`, at least one `aeo:hasAttribute` |
| `aeo:hasAssessment` | property | exposure set membership, inverse functional (sketch §5.2) |
| `aeo:assesses` | property | assessment to asset, location, legal entity or exposure set |
| `aeo:assessmentKind` | property | how the account was obtained |
| `aeo:profileFamily` | property | which family of questions the assessment answers, 0..*. Its shapes are selected by it |
| `aeo:AttributeValue` | class | exactly one `aeo:attributeType` and exactly one of `aeo:conceptValue`, `aeo:quantityValue` (`qnt:Quantity`), `aeo:literalValue` |
| `aeo:hasAttribute` | property | assessment to attribute value, inverse functional |
| `aeo:valueForm` | property | attribute type concept to one of `aeo-voc:ConceptForm`, `QuantityForm`, `LiteralForm` |
| `aeo:valueSpace` | property | attribute type to the `qnt:ValueSpace` its quantities are on |
| `aeo:valueContract` | property | attribute type to the `voc:SchemeContract` its concepts are drawn under |
| `aeo:literalDatatype` | property | attribute type to the XSD datatype of its literals (`xsd:boolean`, `xsd:gYear`, `xsd:date`, `xsd:string`) |
| `aeo:attributeFamily` | property | attribute type to its family (below). COPE is the first four families |
| `aeo:multiValued` | property | attribute type to `xsd:boolean`. True when one assessment may hold several values of the type |

The assessment kind and the profile family are two properties, where sketch §5.8 has one. A
questionnaire can answer cyber questions or construction questions, and a survey can answer both,
so the source and the family vary independently, as valuation basis and method do (§5.6).

### Vocabulary: contracts and reference schemes

Each concept-valued property gets a `voc:SchemeContract` and, where marked, a flat reference scheme
bound to it, declared as AIR-4.1 declares its contracts.

| Contract, constrains | Reference concepts | Notes cite |
|---|---|---|
| `FloodZoneContract`, `SeismicZoneContract`, `WindZoneContract`, `WildfireZoneContract`, `TsunamiZoneContract`, `AccumulationZoneContract` | none. A deployment binds each jurisdiction's edition by territory scope (ADR-A99). AIR-4.6 adds example editions (national flood maps, ASCE 7 seismic design categories, CRESTA zones) | the kind of map each contract expects. If Vocabulary's shapes require a binding, stop and record it in the Handoff |
| `DesignationSourceContract` | `PublishedMap`, `SpatialJoin`, `Survey`, `Declared` | a `SpatialJoin` designation is a derived artefact (sketch §5.4) |
| `AssessmentKindContract` | `SurveyReport`, `ScheduleRow`, `Questionnaire`, `EngineeringInspection`, `EquipmentInspection`, `DesktopReview`, `ThirdPartyEnrichment`, `GeocoderRun`, `ScreeningRun` | |
| `ProfileFamilyContract` | `ConstructionAndProtection`, `CyberPosture`, `BusinessContinuity`, `Environmental`, `Fleet`, `Compliance`, `OperationsAndWorkforce`, `SupplyChain` | sketch §5.8 |
| `AttributeTypeContract` | the attribute types below | |
| `AttributeFamilyScheme` (no contract, read by shapes only) | `Construction`, `Occupancy`, `Protection`, `ExternalExposure`, `GeocodingQuality`, `Equipment`, `Corporate`, and the eight profile families | COPE for the first four |

`aeo-voc:ConceptForm`, `QuantityForm` and `LiteralForm` are concepts of a small `ValueFormScheme`.
`aeo-voc:GeoPrecisionOrder` is a `skos:OrderedCollection` of AIR-4.1's precision concepts, finest
first (`Rooftop`, `Parcel`, `Street`, `Postcode`, `City`, `ZoneCentroid`), which the precision
shape reads.

Value spaces, declared as AIR-2.6 declares its measure spaces, with the units of `insurance/common`:
`Count`, `Area`, `Length`, `Duration`, `Speed` (reuse AIR-2.6's space if one fits, and say so in
the Handoff), `AreaShare`, a `qnt:DerivedValueSpace` naming `Area` twice (ADR-A93), and
`ConfidenceScore`, from 0 to 1 with no unit. Ordinal schemes, declared as AIR-2.6 declares ordinal scales:
`SusceptibilityScale` (`VeryLow` to `VeryHigh`, notations 1 to 5) and `FrequencyScale`
(`Continuous`, `Monthly`, `Quarterly`, `SemiAnnually`, `Annually`, `LessThanAnnually`, `Never`).

### Vocabulary: attribute types

Form is C (concept, with the scheme its reference values come from), Q (quantity, with its space),
or L (literal, with its datatype). "Market" means a contract with no reference scheme, bound by
market and bound in AIR-4.6's examples. Every attribute type that has an Open Exposure Data field
cites it in a note. R checks those field names against the OED specification at verification, so S
cites only the ones it is sure of and lists the rest in the Handoff.

**Construction** (OED primary and secondary modifiers)

| Type | Form | Values or space | Notes cite |
|---|---|---|---|
| `ConstructionClass` | C | market | OED construction codes, the US ISO construction classes 1 to 6 |
| `YearBuilt`, `YearOfMajorRenovation`, `RoofYear` | L | `xsd:gYear` | OED |
| `Storeys`, `StoreysBelowGround` | Q | `Count` | OED |
| `FloorArea` | Q | `Area` | OED |
| `BuildingHeight`, `FirstFloorHeight` | Q | `Length` | OED. First-floor height is above grade, and the note says so |
| `RoofCover`, `RoofGeometry`, `RoofPitch`, `RoofDeck`, `RoofDeckAttachment`, `RoofAnchorage`, `OpeningProtection`, `WallType`, `FoundationType`, `SeismicRetrofit` | C | one flat reference scheme each, values after OED's code lists | OED secondary modifiers, FEMA P-804 (wind retrofit) for roof and opening concepts |
| `ExternalCladding` | C | `NonCombustible`, `LimitedCombustibility`, `Combustible`, `Unknown` | EN 13501-1 reaction-to-fire classes (A1 and A2 limited, B to F combustible) |
| `Basement`, `SoftStorey` | L | `xsd:boolean` | OED |

**Occupancy**

| Type | Form | Values or space | Notes cite |
|---|---|---|---|
| `OccupancyClass` | C | market | OED occupancy codes, ATC-13 |
| `VacantShare` | Q | `AreaShare` | |
| `OperatingHours` | C | `StandardHours`, `ExtendedHours`, `Continuous` | |
| `HazardousMaterialsPresent` | L | `xsd:boolean` | |
| `HazardousMaterialsDescription` | L | `xsd:string` | |

**Protection**

| Type | Form | Values or space | Notes cite |
|---|---|---|---|
| `SprinklerSystem` | C | `WetPipe`, `DryPipe`, `PreAction`, `Deluge`, `EarlySuppressionFastResponse`, `NoSprinklers` | NFPA 13, EN 12845 |
| `SprinklerCoverage` | Q | `AreaShare` | |
| `FireDetection` | C | `Smoke`, `Heat`, `Flame`, `Aspirating`, `Multisensor`, `NoDetection` | EN 54, NFPA 72 |
| `AlarmMonitoring` | C | `LocalOnly`, `CentralStation`, `Proprietary`, `NoAlarm` | NFPA 72, BS 5839-1 |
| `SpecialSuppression` | C | `CarbonDioxide`, `CleanAgent`, `InertGas`, `Foam`, `WaterMist`, `NoSpecialSuppression` | NFPA 12, 2001, 11, 750 |
| `PublicProtectionClass` | C | market | the US public protection classification 1 to 10 |
| `FireServiceResponseTime` | Q | `Duration` | |
| `DistanceToFireStation`, `DistanceToHydrant` | Q | `Length` | |
| `PhysicalSecurity` | C, several values allowed | `IntruderAlarm`, `Cctv`, `Guarding`, `AccessControl` | EN 50131, UL 681 |
| `BackupPower` | L | `xsd:boolean` | |
| `LossControlMeasure` | L | `xsd:string` | a measure taken, for example after a loss |

**External exposure**

| Type | Form | Values or space | Notes cite |
|---|---|---|---|
| `DistanceToCoast`, `DistanceToWaterBody`, `DistanceToFault`, `DefensibleSpace` | Q | `Length` | defensible space: NFPA 1144 |
| `WaterBodyType` | C | `River`, `Lake`, `Sea`, `Estuary`, `Reservoir`, `Canal`, `Wetland` | |
| `GroundElevation`, `BaseFloodElevation` | Q | `Length` | the note says a value is meaningless without its vertical datum, recorded on the assessment's evidence. Base flood elevation: the US flood insurance rate maps |
| `SiteClass` | C | `SiteClassA` to `SiteClassF` | ASCE 7 (NEHRP). The note says Eurocode 8 ground types belong in a market edition |
| `DesignWindSpeed` | Q | `Speed` | ASCE 7 |
| `WindBorneDebrisRegion` | L | `xsd:boolean` | ASCE 7 |
| `LiquefactionSusceptibility`, `LandslideSusceptibility`, `SubsidenceSusceptibility` | C | `SusceptibilityScale` | USGS susceptibility mapping, the British Geological Survey's shrink-swell ratings |
| `VegetationManagement` | L | `xsd:boolean` | |

**Geocoding quality**, on `GeocoderRun` assessments

| Type | Form | Values or space |
|---|---|---|
| `GeocodeConfidence` | Q | `ConfidenceScore` |
| `AddressMatchStatus` | C | `ExactMatch`, `Interpolated`, `Standardised`, `MultipleMatches`, `Unmatched` |

**Equipment**: `Manufacturer`, `ModelDesignation` (L string), `YearOfManufacture` (L `xsd:gYear`),
`ReplacementLeadTime` (Q `Duration`), `SpecialHazardEquipment` and `StatutoryInspectionCurrent`
(L boolean). Equipment kinds are asset classes (`cls:assetClass`), not attribute values.

**Corporate**: `EntityStatus` (C: `Active`, `Dormant`, `InLiquidation`, `Dissolved`, AIR-4.1's
R2), `OperatingTerritory` (C, the territory contract).

**Cyber posture** (notes cite the CIS Critical Security Controls v8, NIST CSF 2.0 and ISO/IEC
27001:2022, naming the control or function each answers)

| Type | Form | Values or space |
|---|---|---|
| `MfaCoverage` | C | `AllUsers`, `PrivilegedAndRemote`, `RemoteOnly`, `NoMfa` |
| `EndpointDetectionAndResponse`, `PrivilegedAccessManagement`, `NetworkSegmentation`, `EmailSecurityFiltering`, `UnsupportedSoftwarePresent`, `IncidentResponsePlan`, `AiManagementSystem` | L | `xsd:boolean`. AI management system: ISO/IEC 42001 |
| `IncidentResponsePlanLastTested` | L | `xsd:date` |
| `BackupStrategy` | C, several allowed | `Offline`, `Immutable`, `AirGapped`, `CloudReplicated`, `NoBackup` |
| `BackupRestoreTestFrequency`, `SecurityAwarenessTrainingFrequency` | C | `FrequencyScale` |
| `CriticalPatchWindow` | Q | `Duration` |
| `CertifiedFramework` | C, several allowed | `Iso27001`, `Soc2Type2`, `PciDss`, `CyberEssentialsPlus` |

Ransomware history is loss history (AIR-4.4), and records held is a population basis (AIR-4.5),
not attributes.

**Business continuity** (ISO 22301, ISO/TS 22317): `BusinessContinuityPlan`,
`DisasterRecoveryPlan`, `AlternateSite`, `ContractualDelayPenalties` (L boolean),
`ContinuityPlanLastTested` (L date), `RecoveryTimeObjective`, `RecoveryPointObjective`,
`MaximumTolerablePeriodOfDisruption` (Q `Duration`). The note on the last says it is the insured's
own statement, and the maximum foreseeable interruption derived from dependencies (sketch §5.9) is
a different figure.

**Environmental**: `ContaminationHistory`, `EnvironmentalManagementSystem` (L boolean, ISO
14001), `ContaminationDescription` (L string), `RemediationStatus` (C: `RemediationActive`,
`RemediationCompleted`, `Monitoring`, `NotRequired`), `UndergroundStorageTankCount`,
`AbovegroundStorageTankCount` (Q `Count`), `TankConstruction` (C: `SingleWalled`, `DoubleWalled`,
`CathodicallyProtected`, US EPA 40 CFR Part 280), `TankContents` (L string).

**Fleet** (one fleet asset per vehicle class, so a count belongs to one class): `VehicleCount` (Q
`Count`), `AverageVehicleAge` (Q `Duration`), `RadiusOfOperation` (C: `Local`, `Intermediate`,
`LongDistance`, notes cite the US commercial auto radius classes of 50 and 200 miles), `FleetUse`
(C: `Service`, `Retail`, `Commercial`, `Personal`), `Telematics`, `DriverTrainingProgramme` (L
boolean), `DriverRecordCheckFrequency` (C `FrequencyScale`).

**Compliance**: `PendingLitigation`, `RegulatoryInvestigation` (L boolean), with descriptions (L
string), and `SanctionsScreeningOutcome` (C: `NoMatch`, `PotentialMatch`, `ConfirmedMatch`). A
screening outcome is a judgement, so it is allowed only in an assessment of kind `ScreeningRun`
that is also a `fnd:DerivedArtefact`, whose derivation run names the lists screened (notes cite
the OFAC SDN list, the EU consolidated list, the UN Security Council consolidated list and the UK
financial sanctions list). Licences and permits are out of scope (epic §7).

**Operations and workforce**: `OperationsDescription`, `ProductsAndServices`, `ShiftPattern` (L
string), `HazardousProcess` (L boolean), `Headcount` (Q `Count`, on an assessment of a location for
a per-location count or of the legal entity for the total). The share of revenue earned abroad is
derived from turnover by territory (AIR-4.4), not stated.

**Supply chain** (summaries from questionnaires. The structure is dependencies, AIR-4.3):
`KeySupplierCount` (Q `Count`), `SingleSourceSupplier`, `SupplierDueDiligence`,
`AlternativeSourcing`, `JustInTimeDependency` (L boolean), `InventoryBuffer` (Q `Duration`),
`SupplierConcentration` (C, the territory contract).

Each attribute type carries `aeo:valueForm`, `aeo:attributeFamily`, and `aeo:valueSpace`,
`aeo:valueContract` or `aeo:literalDatatype` as its form needs. A type allowing several values says
so with `aeo:multiValued true`, and the others are single-valued per assessment.

### Vocabulary: links from perils to exposure

Written in this vocabulary as triples on peril concepts (sketch §5.7). A link on a concept also
holds for the concepts below it, and the shapes read it through `skos:broader*`, so it is stated
once on the highest concept it fits.

| Peril | `prl:relevantAttribute` | `prl:minimumGeoPrecision` |
|---|---|---|
| N.MET.TC.WND, N.MET.ETC.WND, N.MET.SCS.TOR, N.MET.SCS.SLW | `ConstructionClass`, `YearBuilt`, `Storeys`, `RoofGeometry`, `RoofCover`, `RoofDeckAttachment`, `RoofAnchorage`, `OpeningProtection`, `DesignWindSpeed`, `WindBorneDebrisRegion` | `Postcode` |
| N.MET.SCS.HAI | `RoofCover`, `RoofYear`, `ExternalCladding` | `Postcode` |
| N.GEO.EQ.SHK | `ConstructionClass`, `YearBuilt`, `Storeys`, `SoftStorey`, `SiteClass`, `SeismicRetrofit`, `FoundationType` | `Street` |
| N.GEO.EQ.LIQ | `LiquefactionSusceptibility`, `SiteClass`, `FoundationType` | `Street` |
| N.HYD.FLD, N.MET.TC.SRG | `FirstFloorHeight`, `Basement`, `GroundElevation`, `BaseFloodElevation`, `DistanceToWaterBody` | `Rooftop` |
| N.HYD.FLD.CST | as N.HYD.FLD, plus `DistanceToCoast` | `Rooftop` |
| N.CLI.WF | `DefensibleSpace`, `VegetationManagement`, `RoofCover`, `ExternalCladding` | `Rooftop` |
| N.GEO.MM.SUB | `SubsidenceSusceptibility`, `FoundationType` | `Street` |
| N.GEO.MM.LS | `LandslideSusceptibility` | `Street` |
| T.FIR | `ConstructionClass`, `OccupancyClass`, `SprinklerSystem`, `SprinklerCoverage`, `FireDetection`, `AlarmMonitoring`, `PublicProtectionClass`, `FireServiceResponseTime`, `DistanceToHydrant`, `ExternalCladding` | |
| H.THF.BUR | `PhysicalSecurity` | |
| C.MAL | `MfaCoverage`, `EndpointDetectionAndResponse`, `BackupStrategy`, `PrivilegedAccessManagement`, `NetworkSegmentation`, `CriticalPatchWindow` | |

Each link's note is on the attribute type, and says why the attribute changes loss for the peril.
The precision rows say why that level is the coarsest that works (inundation depth varies over
metres, ground motion over a street, a wind field over a postcode).

### Shapes, `zones-attributes-assessments` region and `shapes/profiles/`

| Shape | Rule | Severity |
|---|---|---|
| zone designation | exactly one zone, through one of the six sub-properties, exactly one source, a temporal scope | violation |
| zone in territory | the zone's scheme is bound to its contract for one of the location's territories | violation |
| spatial join | a designation whose source is `SpatialJoin` is a `fnd:DerivedArtefact` | violation |
| pool participation | exactly one pool, at least one peril | violation |
| assessment | at least one subject, exactly one kind, at least one attribute value, a temporal scope | violation |
| attribute value | exactly one value form, the one its type declares. A quantity is on the type's space, a concept is in a scheme bound to the type's contract, a literal has the type's datatype | violation |
| single-valued types | at most one value per type per assessment, unless the type is `aeo:multiValued` | violation |
| screening | `SanctionsScreeningOutcome` only in a `ScreeningRun` assessment that is a derived artefact | violation |
| peril completeness | for each peril named by `aeo:perilScope` on a member of the exposure set, and each attribute type relevant to it or to a broader concept, each location of the set has a value of that type in some assessment of the location or of an asset located there | warning |
| geo precision for peril | for each such peril with a minimum precision, a location's `aeo:geoPrecision` is no coarser in `GeoPrecisionOrder` | warning |
| profile: construction and protection | `shapes/profiles/construction-protection.ttl`. An assessment of this family assesses a location or asset and has `ConstructionClass`, `OccupancyClass`, `YearBuilt` and `Storeys`. Types outside the Construction, Occupancy, Protection and External exposure families are reported | violation for the four, warning for the rest |
| profile: cyber posture | `shapes/profiles/cyber-posture.ttl`. Assesses a legal entity, has `MfaCoverage`, `BackupStrategy` and `EndpointDetectionAndResponse`. Types outside the family are reported | violation for the three, warning for the rest |

The completeness shape is read per location, not per asset. Attribute types do not say which asset
classes they apply to, so a per-asset rule would warn about a roof on stock. The six other
families get kinds and attribute types now and shapes later (Q13).

### Examples and tests

`examples/attributes.ttl`, no `owl:Ontology`: AIR-4.1's example set gains a flood zone designation
with a map period, a spatial-join designation as a derived artefact, a pool participation, a
survey report of the construction and protection family on one location, a cyber posture
questionnaire on the insured, and a geocoder run. It passes every shape with no warning, because
its pool participation's peril (N.HYD.FLD) finds the flood attributes present.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AIR42-01 | the spec and vocabulary / loaded with their import closures / parse, every import resolves | L1 | + |
| AIR42-02 | the contracts of this slice / Vocabulary's shapes / conform, those with reference schemes bound to them | L1 | + |
| AIR42-03 | every attribute type / read / has a form, a family, and the space, contract or datatype its form needs | L1 | + |
| AIR42-04 | the example / every exposure shape / no result, no warning | L1 | + |
| AIR42-05 | an attribute value with a concept and a quantity / validated / violation | L1 | − |
| AIR42-06 | `FirstFloorHeight` with a quantity on `Count` / validated / violation | L1 | − |
| AIR42-07 | a zone designation of a scheme bound only for another territory / validated / violation | L1 | − |
| AIR42-08 | the example without its first-floor height / validated / one warning for N.HYD.FLD, none for other perils | L1 | − |
| AIR42-09 | the example with the flood location at `Postcode` / validated / one precision warning | L1 | − |
| AIR42-10 | a sanctions outcome in a questionnaire / validated / violation | L1 | − |
| AIR42-11 | a cyber posture assessment without `MfaCoverage` / validated / violation | L1 | − |
| AIR42-12 | a link stated on N.HYD.FLD / the completeness shape over a location exposed to N.HYD.FLD.PLU / reads it | L1 | + |
| AIR42-13 | every concept of this slice / the documentation shape / each has a note | L1 | + |

**On R at verification:** catalogs. No release rows: the module's documents stay at `0.1.0` until
the merge.

## AIR-4.3 in detail

**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[AIR-4.3] …`, the
last being `[AIR-4.3] Handoff`. **Validation Pack:**
[applied-insurance-reference-4.3](../validation/applied-insurance-reference-4.3.md). **Decisions:**
ADR-A90 (option B, single-valued paths from a case), ADR-A98, epic E3. Decided 2026-10-13: R8, R9.
**Sketch:** asset exposure ontology §5.9 to §5.11, §6, §8. **Milestone:** M3, with AIR-4.6.

**Invariant:** dependencies between locations, assets and third parties are evidenced relations,
peril metrics are derived artefacts with comparable scopes, and exposure units are computed on
demand for the perils a check asks about, never asserted by hand and never required to be stored.

### Versions and imports

No bump (the module is new on the branch). Everything goes into the `dependencies-metrics-units`
region of each document and README section.

### Spec

**Dependencies**

| Term | Definition |
|---|---|
| `aeo:Dependency` | `⊑ fnd:TemporallyScoped ⊓ fnd:Evidenced`. Exactly one `aeo:dependent` (location or asset), exactly one `aeo:provider` (location, asset or `pty:Actor`), exactly one `aeo:dependencyKind`. Optional: `aeo:shareAtRisk` (`qnt:Quantity` on `OutputShare`), `aeo:recoveryLeadTime` (`qnt:Quantity` on `Duration`), `aeo:substitutability`, `aeo:singleSource` (`xsd:boolean`) |
| `aeo:hasDependency` | exposure set membership, inverse functional |

**Peril metrics**

| Term | Definition |
|---|---|
| `aeo:PerilMetric` | `⊑ fnd:DerivedArtefact ⊓ fnd:Evidenced`. At least one `aeo:perilScope` (AIR-4.2), exactly one `aeo:metricSubject` (exposure set, location or asset), exactly one `aeo:metricKind`, exactly one `aeo:perspective`, exactly one `aeo:metricValue` (`qnt:Value`: a money quantity, or a quantity or ordinal value on a score space). Optional: `aeo:regionScope` (`⊑ cls:territory`), `aeo:returnPeriod` or `aeo:exceedanceProbability` (exactly one of them for exceedance kinds), `aeo:calculationMethod`, `aeo:modelOption` (several), `aeo:scenario` (for scenario losses), `aeo:scoreSpace` (for hazard scores) |
| `aeo:hasPerilMetric` | exposure set membership, inverse functional |

The model and its version are the `fnd:DerivationRun`'s (`prov:wasGeneratedBy`), and the model's
output file is evidence. Full curves and event tables are out of scope (epic §7).

**Exposure units**

| Term | Definition |
|---|---|
| `aeo:ExposureUnit` | `⊑ fnd:DerivedArtefact`. Exactly one `aeo:unitLocation`, one `aeo:unitAssetClass` (`⊑ cls:assetClass`), one `aeo:unitPeril` (`⊑ icm:peril`), at most one `aeo:unitValue` (money `qnt:Quantity`) |

**Groupings (R9)**

| Term | Definition |
|---|---|
| `aeo:scheduleGroup` | location or asset to a concept naming a group the insured or drafter uses (a division, a portfolio, an OED location group). Not functional |

### Vocabulary

| Contract, constrains | Reference concepts | Notes cite |
|---|---|---|
| `DependencyKindContract` | `SupplyOfGoods`, `Utility`, `ItService`, `Logistics`, `Customer` | sketch §5.9. Customer dependencies give contingent business interruption on the customer side |
| `SubstitutabilityContract` | `NotSubstitutable`, `PartlySubstitutable`, `FullySubstitutable` | |
| `MetricKindContract` | `AverageAnnualLoss`, `OccurrenceExceedanceLoss`, `AggregateExceedanceLoss`, `OccurrenceTailValueAtRisk`, `AggregateTailValueAtRisk`, `ProbabilityOfEvents`, `HazardScore`, `ScenarioLoss` | Oasis Open Results Data (AAL, OEP, AEP and their TVaR), Solvency II's 1 in 200 convention for return periods, Lloyd's Realistic Disaster Scenarios for scenario losses. The note on `ProbabilityOfEvents` says it names a count with `aeo:returnPeriod` unused |
| `PerspectiveContract` | `GroundUpLoss`, `InsuredLoss`, `ReinsuranceLoss` | Open Results Data's GUL, IL and RIL. The note says the market's "gross" is usually insured loss and its "net" loss after reinsurance, and that a metric states which it is |
| `CalculationMethodContract` | the exceedance curve calculation methods of Open Results Data (for example full uncertainty and per-sample mean), those S is sure of | R checks them against the specification |
| `ModelOptionContract` | `SecondaryUncertainty`, `DemandSurge`, `StormSurgeIncluded`, `FireFollowingIncluded`, `ClimateConditioned` | |
| `ScheduleGroupContract` | none. Bound per insured or drafter, at agreement or organisation scope | OED's location group field |

Value spaces: `OutputShare`, a `qnt:DerivedValueSpace` over a production space named twice (its note
says the share is of the dependent's output), and the score spaces a deployment declares per
provider. A hazard score from one provider is never on another's space (sketch §5.10).

### Derivation of exposure units (`tools/exposure_derivations.py`)

`exposure_units(graph, perils, run)` returns the units for every location of the exposure set,
asset class present there and peril in `perils`, as a separate graph. It never writes into the
source graph. A unit's value is the sum of the amounts of the valuations of that class's assets at
that location, when they share one currency. With several currencies and no conversion in the
graph, the value is omitted and the function reports it, since converting needs a rate and a
date (Quantification's pattern). A peril applies to a location's unit when the location has any
asset (the function does not decide physical exposure, which is a model's work).

"On demand" (sketch §5.11, route R1) means a check calls this function for the perils its
conditions name, evaluates over the result together with the source graph, and discards it. A
deployment may persist the result as a derived artefact, and nothing requires it to.

### Milestone M3, first half (`examples/units.ttl`)

AIR-4.2's example set grows to four locations, two in a special flood hazard area (example zone
concepts, until AIR-4.6 binds a real edition). An Eligibility admission profile over
`aeo:ExposureUnit`, two conditions: the unit's peril is under N.HYD.FLD (hierarchical), and the
unit's location has a flood zone in the special flood hazard set (set membership, read through
`aeo:unitLocation`, `aeo:zoneDesignation`, `aeo:floodZone`). Recorded decisions: the two zone
locations' flood units Permitted, the other two Denied, every wind unit Denied. The test computes
the units, evaluates with the SPARQL backend, and checks the source graph has no unit triples
afterwards.

### Shapes

| Shape | Rule | Severity |
|---|---|---|
| dependency | exactly one dependent, provider and kind | violation |
| dependency cycle | a cycle of dependencies is reported | warning |
| peril metric | the cardinalities above. An exceedance kind has exactly one of return period or exceedance probability | violation |
| comparability | two metrics cited by one derived artefact as compared have equal peril scope, region scope and perspective | violation |
| score | a hazard score's value is on its declared score space | violation |
| exposure unit | the cardinalities above | violation |
| unit not asserted | an exposure unit in a graph without a derivation run is reported | warning |

The maximum foreseeable interruption derived from the dependency graph (sketch §5.9) is deferred:
it needs a graph algorithm and a policy for parallel paths, and no milestone reads it. The
dependency data it would read is complete in this slice.

### Tests

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AIR43-01 | the documents / loaded with their import closures / parse | L1 | + |
| AIR43-02 | the contracts of this slice / Vocabulary's shapes / conform | L1 | + |
| AIR43-03 | the examples / every exposure shape / no result | L1 | + |
| AIR43-04 | `exposure_units` over the example for N.HYD.FLD and N.MET.TC.WND / called / one unit per location, class and peril, with summed values | L2 | + |
| AIR43-05 | a location with values in two currencies / `exposure_units` / that unit has no value and the function reports it | L2 | − |
| AIR43-06 | the M3 profile / SPARQL over the computed units / the recorded decisions, and no unit triple in the source graph | L2 | + |
| AIR43-07 | an occurrence exceedance metric with neither return period nor probability / validated / violation | L1 | − |
| AIR43-08 | a comparison of a ground-up and an insured-loss metric / validated / violation | L1 | − |
| AIR43-09 | every concept of this slice / the documentation shape / each has a note | L1 | + |

## AIR-4.4 in detail

**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[AIR-4.4] …`, the
last being `[AIR-4.4] Handoff`. **Validation Pack:**
[applied-insurance-reference-4.4](../validation/applied-insurance-reference-4.4.md). **Decisions:**
ADR-A98, ADR-A99, ADR-A103 (set readings), epic D7 and D12. **Sketch:** asset exposure ontology
§5.12 to §5.14.
**Decided 2026-10-13:** the proposal of that day, Q11 (option a, recorded and effective
characteristics), Q12 (no link to `ins:Obligation` before Phase 5), Q14 (currencies, in AIR-2.6),
and the review's R1 (class of business), R3 (loss experience), R4 (cover history), R5
(requirement strength and attachment).

**Invariant:** an insured's loss experience states its period, source and completeness, each loss
records its cause chain with recorded and effective characteristics kept apart, and requirements,
existing cover, cover history and financial metrics are evidenced facts that gap analysis can read
without any of them computing cover.

### Versions and imports

`insurance/common`'s spec changes for the first time on the branch, so this slice bumps it once,
0.5.0 to 0.6.0 (MINOR, additions only), and changes the import of every importer on the branch to
0.6.0: `peril/spec` (already bumped by AIR-2.2, so its own version does not change) and
`exposure/spec`. `common-vocab` was bumped by AIR-2.6 and changes here without another bump. The
exposure documents stay at `0.1.0`. The exposure spec adds an import of Eligibility at the version
of `main` at the branch point, for `elg:AdmissionProfile`.

### `insurance/common` additions

| Term | Kind | Definition | Notes cite |
|---|---|---|---|
| `icm:LossEvent` | class | `⊑ fnd:Evidenced ⊓ fnd:TemporallyScoped ⊓ fnd:NaturallyKeyed`. One occurrence in the world (a storm, an earthquake, a cyber campaign) that many losses can share. Its temporal scope is the event's span, its perils are `icm:peril` values, its territories `cls:territory` values (epic D7) | the event is not an insurance occurrence: grouping losses into one occurrence under a contract is the contract's rule (AIR-6.3) |
| `icm-voc:GlideNumber` | `fnd:KeyScheme` | the GLIDE number assigned by the Asian Disaster Reduction Center's GLobal IDEntifier scheme, as the open reference key | GLIDE. The note says insurance industry event identifiers (catastrophe serial numbers, industry loss index event codes) are key schemes their publishers own, declared in AIR-4.6's examples |
| `icm:classOfBusiness` | property | to a concept, the class or line of business. No domain | R1 |
| `icm-voc:ClassOfBusinessContract` | contract | constrains `icm:classOfBusiness`, no reference scheme. AIR-4.6 binds an example edition of the Solvency II lines of business | Commission Delegated Regulation (EU) 2015/35, Annex I |

### Exposure spec

**Loss experience and losses**

| Term | Definition |
|---|---|
| `aeo:LossExperience` | `⊑ fnd:Evidenced ⊓ fnd:TemporallyScoped`. One source's account of an insured's losses over a period, its temporal scope. Exactly one `aeo:experienceOf` (legal entity), exactly one `aeo:experienceSource`, at most one `aeo:statedComplete` (`xsd:boolean`), any number of `aeo:classOfBusiness` (`⊑ icm:classOfBusiness`), the lines it covers |
| `aeo:hasLossExperience` | exposure set membership, inverse functional |
| `aeo:hasLossRecord` | loss experience to loss record, inverse functional. Records belong to an experience, not directly to the exposure set as sketch §5.2 has it, so that an experience with no records, stated complete, says "no losses in the period" and an absent experience says nothing |
| `aeo:LossRecord` | `⊑ fnd:Evidenced`, `fnd:NaturallyKeyed` for the claim reference. Exactly one `aeo:lossDate` (`xsd:date`), at most one `aeo:lossAt` (location), exactly one `aeo:lossStatus`, at most one `aeo:classOfBusiness` (the line it was paid under), at most one `aeo:lossEvent` (`icm:LossEvent`), any number of `aeo:hasCause` and `aeo:consequence` (`⊑ icm:consequence`) |
| money on a loss record | each at most one `qnt:Quantity` in a currency: `aeo:grossAmount` (before deductible), `aeo:deductibleApplied`, `aeo:paid`, `aeo:reserved`, `aeo:incurred`, `aeo:recovered` (subrogation and salvage) |
| `aeo:LossCause` | `⊑ fnd:Evidenced`. Exactly one `aeo:peril` (`⊑ icm:peril`), exactly one `aeo:causePosition`, at most one `aeo:agency` (`⊑ icm:agency`), any number of `aeo:mechanism` (`⊑ icm:mechanism`). These are what the source recorded |
| `aeo:effectiveAgency`, `aeo:effectiveMechanism` | `⊑ icm:agency`, `⊑ icm:mechanism`. Written by the derivation below, never by hand. Eligibility bindings read these (Q11) |
| `aeo:DefaultedCharacteristic` | `⊑ fnd:DerivedArtefact`. One per effective value that was defaulted rather than copied: exactly one `aeo:defaultedOn` (the loss cause), exactly one `aeo:defaultedProperty` (`aeo:effectiveAgency` or `aeo:effectiveMechanism`), `prov:wasDerivedFrom` the cause concept whose typical value was used, `prov:wasGeneratedBy` the derivation run |

A loss cause may record a mechanism or agency that differs from the cause concept's typical value.
The recorded value wins and is copied. Only where nothing is recorded is the typical value used,
and then a reviewer sees a `DefaultedCharacteristic` beside it. A cause concept without typical
values (a drafter's flat code) leaves the effective value empty, and a check reading it is
Undetermined (sketch §5.12).

**Requirements**

| Term | Definition |
|---|---|
| `aeo:CoverageRequirement` | `⊑ fnd:Version ⊓ fnd:Evidenced`. Exactly one `aeo:requirementSource`, exactly one `aeo:requirementStrength`, at least one `aeo:requiredMeasure`, at most one `aeo:requirementScope` (`elg:AdmissionProfile` whose subject class is `aeo:ExposureUnit`, AIR-4.3), any number of `aeo:classOfBusiness`, at most one `aeo:owedTo` (`pty:RoleOccupancy`, the lender as mortgagee, for example) |
| `aeo:hasRequirement` | exposure set membership, inverse functional |
| `aeo:MeasureConstraint` | exactly one `aeo:measure`, exactly one `aeo:bound` (`qnt:RangeSet` on the measure's space), at most one `aeo:atReturnPeriod` (`qnt:Quantity` in years, for `NetRetainedLoss`), at most one `aeo:relativeTo` (`aeo:FinancialMetric`) |
| `aeo:measureSpace` | measure concept to the space its bounds are on |

A relative bound (net loss at 1 in 100 not above 10% of equity) is on a `qnt:DerivedValueSpace`
naming the money space twice (ADR-A93) and names the metric with `aeo:relativeTo`. If Quantification
at the live version has a construct for a bound relative to a value, use it and say so in the
Handoff. `aeo:arisesFrom` to `ins:Obligation` is not built (Q12): Instrument is being rewritten
by CCS, and Phase 5 adds the link. `aeo:owedTo` names the obligee until then.

**Existing cover and cover history**

| Term | Definition |
|---|---|
| `aeo:ExistingCover` | `⊑ fnd:Evidenced ⊓ fnd:TemporallyScoped` (the policy period). Exactly one `aeo:coverRelation`, at most one `aeo:coverReference` (`xsd:anyURI`, the contract, which the contract module owns), at most one `aeo:triggerBasis`, any number of `aeo:perilScope`, `aeo:classOfBusiness`, `aeo:insurer` (`pty:Actor`) and `aeo:summaryTerm` |
| `aeo:summaryTerm` | to an `aeo:TermSummary`: exactly one `aeo:measure`, exactly one `aeo:summaryValue` (`qnt:Quantity`). The expiring limit, retention or premium, when the contract itself is not in the graph |
| `aeo:hasExistingCover` | exposure set membership, inverse functional |
| `aeo:CoverHistoryEvent` | `⊑ fnd:Evidenced`. Exactly one `aeo:historyEventKind`, exactly one `aeo:eventDate` (`xsd:date`), at most one `aeo:byInsurer` (`pty:Actor`), any number of `aeo:classOfBusiness`, at most one `aeo:reasonGiven` (`xsd:string`) |
| `aeo:hasCoverHistoryEvent` | exposure set membership, inverse functional |

**Financial metrics**

| Term | Definition |
|---|---|
| `aeo:FinancialMetric` | `⊑ fnd:Evidenced ⊓ fnd:TemporallyScoped` (the reporting period). Exactly one `aeo:metricOf` (legal entity), exactly one `aeo:financialMetricKind`, exactly one `aeo:metricAmount` (`qnt:Quantity`), at most one `aeo:audited` (`xsd:boolean`), any number of `aeo:metricTerritory` (`⊑ cls:territory`, for turnover by territory) |
| `aeo:hasFinancialMetric` | exposure set membership, inverse functional |

Disjointness (sketch §6) extends to every class of this slice.

### Vocabulary

| Contract, constrains | Reference concepts | Notes cite |
|---|---|---|
| `LossExperienceSourceContract` | `InsuredDeclared`, `InsurerLossRun`, `ClaimsAdministratorReport`, `BrokerRecord` | |
| `LossStatusContract` | `Open`, `Closed`, `ClosedWithoutPayment`, `Reopened`, `InLitigation`, `InRecovery` | ACORD claim status practice |
| `CausePositionContract` | `Initiating`, `Intermediate`, `Proximate` | English law's proximate cause, the dominant or effective cause (*Leyland Shipping v Norwich Union* [1918] AC 350), concurrent causes (*Wayne Tank v Employers Liability* [1974] QB 57), and the US efficient proximate cause doctrine (*Sabella v Wisler*, 59 Cal.2d 21 (1963)). The note says several links can be proximate under concurrent causation, and which link a contract reads is the contract's rule |
| `RequirementSourceContract` | `RiskAppetite`, `LenderCovenant`, `Regulation`, `LeaseOrContract`, `BoardMandate` | sketch §5.13 |
| `RequirementStrengthContract` | `Mandatory`, `Preferred`, `Optional` | RFC 2119's MUST, SHOULD and MAY, as an analogy for the force of a client's requirement |
| `MeasureContract` | `Limit`, `SubLimit`, `Attachment`, `Retention`, `IndemnityPeriod`, `WaitingPeriod`, `CapacityShare`, `NetRetainedLoss`, `Premium` | each with `aeo:measureSpace`: money for amounts, duration (calendar months and hours) for periods, a share of the limit for capacity. `Premium` is for summary terms only, and a shape keeps it out of requirements |
| `CoverRelationContract` | `Underlying`, `Alongside`, `Replaced` | |
| `TriggerBasisContract` | `Indemnity`, `Parametric`, `IndustryLossIndex` | |
| `CoverHistoryEventKindContract` | `Declined`, `NonRenewed`, `Cancelled`, `SpecialTermsImposed`, `Avoided` | the UK Insurance Act 2015 duty of fair presentation (s.3) and remedies (Schedule 1), and the prior cover questions of the ACORD 125 commercial application |
| `FinancialMetricKindContract` | `Revenue`, `GrossProfit`, `Ebitda`, `NetIncome`, `Equity`, `TotalAssets`, `Payroll`, `Headcount`, `MarketCapitalisation`, `Fees`, `Turnover` | IFRS 15 for revenue, IAS 1 for the statement lines. The note on `Ebitda` says it is not defined by IFRS, so its source's definition is evidence. `Headcount` is a count, the rest money |

### The effective characteristics derivation

`tools/exposure_derivations.py`, one function `effective_characteristics(graph)` returning the
triples to add. One SPARQL `CONSTRUCT` per characteristic: copy each recorded value to the effective
property, and where none is recorded and the cause concept has `prl:typicalAgency` or
`prl:typicalMechanism`, write the typical values and one `aeo:DefaultedCharacteristic` each, with a
`fnd:DerivationRun` for the call. Code executes, the layer states: the function writes no other
triple. `examples/losses.ttl` holds its output for the example's causes, and a test checks the file
equals the function's output on the example's input.

### Shapes, `losses-requirements-cover` region

| Shape | Rule | Severity |
|---|---|---|
| loss experience | exactly one entity, one source, a temporal scope | violation |
| loss record | exactly one date, one status. Every money amount on it in one currency | violation |
| loss in period | a record's date is within its experience's temporal scope | violation |
| incurred | incurred equals paid plus reserved when all three are present | violation |
| loss cause | exactly one peril, one position, at most one agency and one effective agency | violation |
| defaulted | an effective value that differs from every recorded value has a `DefaultedCharacteristic`, and one with a recorded value has none | violation |
| requirement | one source, one strength, at least one measure. Each bound on its measure's space. No `Premium`. A relative bound is on a share space and names a metric | violation |
| requirement scope | the admission profile's subject class is `aeo:ExposureUnit` | violation |
| existing cover | one relation, a temporal scope. A cover with neither a reference nor a summary term is reported | violation, warning |
| cover history | one kind, one date | violation |
| financial metric | one entity, one kind, one amount, a temporal scope. `Headcount` is a count, the others money | violation |

### Examples and tests

`examples/losses.ttl`, no `owl:Ontology`: a five-year loss experience stated complete, with two
records (a flood loss with a two-link chain, the initiating cause a tropical cyclone and the
proximate an inundation, one link with a recorded mechanism and one defaulted, and a fire loss
grouped under a loss event with a GLIDE key), a second experience from an insurer's loss run with
no records, a lender's flood requirement (mandatory, limit at least the principal, scope over flood
exposure units in a special flood hazard area), an appetite requirement relative to equity, an
expiring programme with summary terms, a non-renewal, and revenue by territory.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AIR44-01 | `common` and the exposure documents / loaded with their import closures / parse, every import resolves, every importer of `common` on the branch names 0.6.0 | L1 | + |
| AIR44-02 | the contracts of this slice and `ClassOfBusinessContract` / Vocabulary's shapes / conform | L1 | + |
| AIR44-03 | the example / every exposure shape / no result | L1 | + |
| AIR44-04 | the example's input / `effective_characteristics` / equals `examples/losses.ttl`'s derived triples, one `DefaultedCharacteristic`, none for the recorded link | L2 | + |
| AIR44-05 | a cause concept with no typical agency / the derivation / no effective agency and no `DefaultedCharacteristic` | L2 | + |
| AIR44-06 | a loss dated outside its experience's period / validated / violation | L1 | − |
| AIR44-07 | paid 10, reserved 5, incurred 20 / validated / violation | L1 | − |
| AIR44-08 | an effective agency differing from the recorded one, with no defaulted node / validated / violation | L1 | − |
| AIR44-09 | a requirement bound on a duration space for `Limit` / validated / violation | L1 | − |
| AIR44-10 | a requirement with a `Premium` measure / validated / violation | L1 | − |
| AIR44-11 | a requirement scope over `aeo:Location` / validated / violation | L1 | − |
| AIR44-12 | an experience stated complete with no records / queried for losses in the period / the answer is "none" from a stated fact, and an insured with no experience gives no answer | L2 | + |
| AIR44-13 | every concept of this slice / the documentation shape / each has a note | L1 | + |

**On R at verification:** catalogs, and the release row for `insurance-common-v0.6.0` is written at
the merge, not now.

## AIR-4.5 in detail

**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[AIR-4.5] …`, the
last being `[AIR-4.5] Handoff`. **Validation Pack:**
[applied-insurance-reference-4.5](../validation/applied-insurance-reference-4.5.md). **Decisions:**
ADR-A102 (liability role types), epic E4. **Sketch:** asset exposure ontology §5.15, term
parameters §7.3.

**Invariant:** exposure to claims by parties unknown at binding is described by populations (who
could claim, how they relate to the insured, how many and where), never by named claimants, and
nothing here records liability direction, which is derived from roles (E4).

### Spec (`liability` region)

| Term | Definition |
|---|---|
| `aeo:CounterpartyPopulation` | `⊑ fnd:Evidenced ⊓ fnd:TemporallyScoped`. Exactly one `aeo:populationOf` (legal entity), one `aeo:populationKind`, one `aeo:relationshipDepth`, at most one `aeo:populationSize` (`qnt:Quantity` on `Count`), any number of `aeo:populationTerritory` (`⊑ cls:territory`), at most one `aeo:exposureBasis` (a `FinancialMetricKind` concept), at most one `aeo:exposureMetric` (`aeo:FinancialMetric`, the figure itself) |
| `aeo:hasPopulation` | exposure set membership, inverse functional |

### Vocabulary

| Contract, constrains | Reference concepts | Notes cite |
|---|---|---|
| `PopulationKindContract` | `Shareholders`, `SecuritiesHolders`, `Creditors`, `Employees`, `Customers`, `Patients`, `DataSubjects`, `Regulators`, `GeneralPublic`, `CustomersCustomers` | data subjects: GDPR Art. 4(1). Patients and customers, for professional liability |
| `RelationshipDepthContract` | `Direct`, `ThroughOneIntermediary`, `Further` | term parameters §7.3, the third and fourth party readings |

Attribute types for securities listings, family `Corporate`, on the legal entity's assessments
(sketch §5.15): `ListingVenue` (C, a market contract with no reference scheme, its note citing
ISO 10383 market identifier codes as the edition a deployment binds), `ListingKind` (C:
`PrimaryListing`, `SecondaryListing`, `DepositaryReceipt`, `OverTheCounter`), `ListedSince` (L
`xsd:date`). Records held are a data subjects population's size, not an attribute.

### Shapes

| Shape | Rule | Severity |
|---|---|---|
| population | the cardinalities above | violation |
| basis and figure | an exposure metric, when present, is of the exposure basis kind and belongs to the population's entity | violation |
| no claimant | a population names no `pty:Actor` other than its entity | violation |

### Examples (`examples/liability.ttl`)

A listed manufacturer: securities holders (direct, size a market capitalisation basis), employees
(direct, payroll basis, two territories), its customers' customers (further, through a customer
dependency of AIR-4.3), data subjects (direct, size two million records). Passes every shape.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AIR45-01 | the documents / loaded / parse, the two contracts conform | L1 | + |
| AIR45-02 | the example / every exposure shape / no result | L1 | + |
| AIR45-03 | a population with a payroll basis citing a revenue metric / validated / violation | L1 | − |
| AIR45-04 | a population naming a claimant actor / validated / violation | L1 | − |
| AIR45-05 | every concept of this slice / the documentation shape / each has a note | L1 | + |

## AIR-4.6 in detail

**Machine:** S (Copilot Business). **Branch:** `air/applied-reference`, commits `[AIR-4.6] …`, the
last being `[AIR-4.6] Handoff`. **Validation Pack:**
[applied-insurance-reference-4.6](../validation/applied-insurance-reference-4.6.md). **Decisions:**
ADR-A99, ADR-A98. **Sketch:** asset exposure ontology §10, §12, §5.2.
**Milestone:** M3, with AIR-4.3.

**Invariant:** a market profile is scheme bindings and shapes and never a class. The London and US
profiles bind example editions for every market-bound contract of Phase 4 and make their
market's required data mandatory, and the worked examples pass under each profile.

### What a profile is

A deployment loads a profile's bindings and its shapes when it works in that market. Nothing in an
exposure set says which market it is placed in (that is the submission's, AIR-6.1), so a profile's
shapes target every exposure set they are run over.

| File | Content |
|---|---|
| `examples/profile-us.ttl`, `examples/profile-london.ttl` | editions and bindings, scoped to `ex:us-market` with `ex:us-risk-regime`, and to `ex:london-market` (AIR-2.7's scopes) |
| `shapes/profiles/market-us.ttl`, `shapes/profiles/market-london.ttl` | the profile shapes below |
| `examples/worked-london.ttl`, `examples/worked-us.ttl` | sketch §12's two fragments, completed until they pass, with the profile's bindings |
| `examples/persistence.ttl` | the persistence profiles |

### Example editions

Each is a small scheme with notes citing its source, and each says it is an example, not a
maintained edition.

| Contract | Edition | Profile | Notes cite |
|---|---|---|---|
| `FloodZoneContract` | US national flood map zones `A`, `AE`, `AH`, `AO`, `AR`, `A99`, `V`, `VE`, `X`, `D`, with a collection of the special flood hazard area zones (the A and V zones) | US, territory `ex:US` | FEMA flood insurance rate map zone definitions |
| `FloodZoneContract` | England's flood zones `1`, `2`, `3a`, `3b` | London, territory `ex:GB` | National Planning Policy Framework flood zones (Environment Agency) |
| `SeismicZoneContract` | seismic design categories `A` to `F` | US | ASCE 7 |
| `AccumulationZoneContract` | a handful of CRESTA zones of one country, by code | London | CRESTA zone definitions. The note says the full zone set is obtained from its publisher |
| `ConstructionClass` | the US construction classes 1 to 6 (frame, joisted masonry, non-combustible, masonry non-combustible, modified fire resistive, fire resistive) | US | ISO construction classes |
| `ConstructionClass` | a short international set (timber, masonry, concrete, steel frame, mixed) | London | OED construction codes, as close matches |
| `OccupancyClass` | a short set from OED occupancy codes | both | OED |
| `PublicProtectionClass` | classes 1 to 10 | US | the public protection classification |
| `icm-voc:ClassOfBusinessContract` | the twelve Solvency II non-life direct lines of business | both | Commission Delegated Regulation (EU) 2015/35, Annex I |
| key schemes | `ex:PcsSerialNumber`, `ex:PerilsEventId`, for `icm:LossEvent` keys | US, London | the publishers' own event identifiers, named as key schemes and not reproduced |

### Profile shapes

| Profile | Rule | Severity |
|---|---|---|
| US | every location in `ex:US` has a building valuation with an amount (percentage deductibles read it), a flood zone designation, a construction class and a year built | violation |
| US | a location in a special flood hazard area with a lender's interest has a mandatory lender requirement for flood (sketch §10) | warning |
| US | a loss cause records both initiating and proximate links when it has more than one link (causation varies by state) | warning |
| London | every location has an accumulation zone designation | violation |
| London | every exposure set with business income valuations has a rate with a horizon on each | violation |
| both | every concept-valued attribute in a market-bound contract resolves under the profile's bindings | violation |

### Persistence profiles (`examples/persistence.ttl`)

An aggregate boundary profile per exposure set version (`dal:NamedGraphBoundary`, a graph IRI
template on the version's identity), as sketch §5.2 states, and a privacy profile for legal
entities that are natural persons (`dal:PersonalData`, `dal:PerSubjectGraphDrop`). These are
deployment choices, so they are examples. Persistence is being reworked on its own branch
(ADR-A122, aggregate ownership): use Persistence at the version of `main` at the branch point,
and R re-checks this file at the merge.

### Tests

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AIR46-01 | each profile's files / loaded with the module / parse, every binding resolves under its scopes | L1 | + |
| AIR46-02 | `worked-us.ttl` with the US profile / every shape / no result | L1 | + |
| AIR46-03 | `worked-london.ttl` with the London profile / every shape / no result | L1 | + |
| AIR46-04 | the US worked example without a flood zone designation / US profile / violation | L1 | − |
| AIR46-05 | `worked-london.ttl` / the US profile / violations, showing profiles are chosen by loading | L1 | − |
| AIR46-06 | M3, second half: the AIR-4.3 profile rebound to the US flood zone edition's special flood hazard collection / units computed for `worked-us.ttl` / the coastal hotel's flood unit Permitted | L2 | + |
| AIR46-07 | the persistence example / Persistence's shapes / no result | L1 | + |
| AIR46-08 | every example concept / the documentation shape / each has a note | L1 | + |

## Documentation deltas

Module README, `ontology/applied/README.md`, `docs/architecture/data-architecture.md` (exposure
aggregates and privacy boundaries), `docs/architecture/ontology-architecture.md` §3.

## Exit gate

M3 demonstrated. Recommendations AI-1 to AI-4 closed or carried.
