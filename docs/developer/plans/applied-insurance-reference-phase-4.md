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

After 4.1, the slices form two independent chains: 4.2, 4.3 and 4.6, and 4.4 and 4.5. 4.2
needs AIR-2.1, 4.3 needs AIR-2.3, 4.4 needs AIR-2.2, and 4.6 needs AIR-2.7. Order and lanes:
[machines, branches and merges](applied-insurance-reference-lanes.md).

Milestone M3 closes in 4.3 and 4.6. Persistence profiles are deployment choices, so they are
authored with the worked examples in 4.6, not in the core.

## AIR-4.1 in detail

**Machine:** S (Copilot Business). **Branch:** `air/4.1-exposure-core`. **Validation Pack:**
[applied-insurance-reference-4.1](../validation/applied-insurance-reference-4.1.md), whose Handoff
section S fills in. **Decisions:** ADR-A98 (layout, namespaces), ADR-A102 (roles). **Sketch:**
asset exposure ontology §3, §5.1 to §5.3, §5.5, §5.6, §6, §8.

**Invariant:** an exposure set version, its locations, assets, interests and valuations, and the
parties and control relations behind them, exist on LATTICE's own constructs, with the regions
later Phase 4 slices fill.

**Coordination (2026-09-30, revised 2026-10-03).** The computable-contract-substrate unit adds keys
to Foundation (ADR-A114, slice F1) before this slice's branch takes work: `fnd:Key` with a
`fnd:KeyScheme` and a value, `fnd:externalKey` and `fnd:naturalKey`. An organisation's registration
and tax numbers and its LEI are then natural keys on the `aeo:LegalEntity`, and `aeo:identifier`
and `aeo:Identifier` are not built. The rows below use Foundation's keys (revised 2026-10-03, with F1).

### Namespaces

| Document | Ontology IRI | Version IRI | Prefix |
|---|---|---|---|
| `spec/exposure.ttl` | `https://www.nebularis.org/neuro-semantic/insurance/exposure` | `…/insurance/exposure/0.1.0` | `aeo:` (`…/insurance/exposure#`) |
| `vocab/exposure-vocab.ttl` | `…/insurance/exposure/vocab` | `…/insurance/exposure-vocab/0.1.0` | `aeo-voc:` (`…/insurance/exposure/vocab#`) |

The spec imports, by exact version IRI: Foundation 0.3.0, Vocabulary 0.3.0, Quantification 0.5.0,
Party 0.5.0 and `…/insurance/common/0.1.0` (which brings `classification/`). It does not import
`peril/`: nothing in this slice uses it, and AIR-2.2 bumps it concurrently. AIR-4.3 adds the import
with its first use. The vocabulary imports the spec 0.1.0 and `…/insurance/common-vocab/0.1.0`.

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
| `aeo:LegalEntity` | §5.1 | `⊑ pty:Actor`, `⊑ fnd:NaturallyKeyed`. Registration and tax numbers and the LEI are `fnd:naturalKey`s, key nodes of declared `fnd:KeyScheme`s (Foundation README §8). A tax number's scheme is sensitive |
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

`aeo:territory` and `aeo:assetClass` use the `cls-voc:` contracts through their super-properties,
so no contract is declared for them here. Programme roles, declared as `icm-voc:Claimant` is:
`aeo-voc:NamedInsured`, `FirstNamedInsured`, `AdditionalInsured`, `LossPayee`, `Mortgagee`,
`LessorRole` (distinct from the interest kind `Lessor`) and `Bailor`.

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
| membership | a member belongs to at most one exposure set version |

### Other files

- `examples/core.ttl`, no `owl:Ontology`: one exposure set version with two locations, a building
  and its contents, an owner's interest and a lender's, three valuations (one amount, one rate
  with a 12-month horizon), and a parent controlling the insured. Passes every shape.
- `tools/test_exposure_ontology.py`, modelled on `tools/test_peril_vocabulary.py`.
- `README.md` for the module: purpose, files, namespaces, regions and their slices.
- The exposure row of `insurance/domain-README.md` and the applied insurance row of
  `docs/architecture/ontology-architecture.md` §3.

**On R at verification:** catalogs, and release rows and tags for `insurance-exposure-v0.1.0`,
`insurance-exposure-vocab-v0.1.0` and the shapes directory.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| AIR41-01 | the spec and vocabulary / loaded with their import closures / parse, every import resolves, `peril/` is not imported | L1 | + |
| AIR41-02 | the six contracts / Vocabulary's shapes / conform, each bound to its reference scheme | L1 | + |
| AIR41-03 | `aeo:territory` and `aeo:assetClass` / read / sub-properties of `cls:territory` and `cls:assetClass` | L1 | + |
| AIR41-04 | the example / the exposure shapes / no result | L1 | + |
| AIR41-05 | a location without a territory / validated / violation | L1 | − |
| AIR41-06 | an asset with both `aeo:locatedAt` and a presence / validated / violation | L1 | − |
| AIR41-07 | a valuation with an amount and a rate, and one with neither / validated / two violations | L1 | − |
| AIR41-08 | two entities each controlling the other / validated / cycle violation | L1 | − |
| AIR41-09 | a location in two exposure set versions / validated / membership violation | L1 | − |
| AIR41-10 | an exposure set without a reporting unit / validated / violation (the zero case) | L1 | − |
| AIR41-11 | the four shape files and the vocabulary / read / every region of later slices is present and empty | L0 | + |

## Documentation deltas

Module README, `ontology/applied/README.md`, `docs/architecture/data-architecture.md` (exposure
aggregates and privacy boundaries), `docs/architecture/ontology-architecture.md` §3.

## Exit gate

M3 demonstrated. Recommendations AI-1 to AI-4 closed or carried.
