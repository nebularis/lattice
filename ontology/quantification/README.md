<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Quantification Ontology — Values, Bounds, Ranges, Conversion, and Recurrence

*Literate specification, following the convention established in `ontology/foundation/spec/foundation.md`, `ontology/vocabulary/spec/vocabulary.md`, and `ontology/party/spec/party.md`. This document and `spec/quantification.ttl`, `vocab/quantification-vocab.ttl`, and `shapes/*.ttl` are meant to be regenerated from one another — see §3.*

Suggested repository location: `ontology/quantification/spec/quantification.md`.

**Revision note.** This is a full rework of an earlier draft, addressing the five blocking defects and the substantive defects raised in that draft's critical review. §16 lists what changed and why. The rename from `qty:` to `qnt:` — Quantity to Quantification — is adopted throughout, per that review's confirmation that it is correct and should not be relitigated.

---

## 1. Purpose and Scope

Quantification models **declared value spaces, quantities, ordered values, bounds, ranges, conversion, granularity, recurrence, and deterministic ordering**.

The layer exists because a recurring family of questions has no home elsewhere in the substrate:

- Is a value inside a stated range?
- Do two ranges overlap, and does that mean the same thing as both containing a common value?
- Can two values be compared or combined at all?
- Does a value need conversion before comparison, and is the context for that conversion present?
- Is the available information precise enough to answer a comparison?
- Which recurring interval contains an observation, and will independently run processes agree on which one?
- What deterministic order applies when two occurrences are otherwise tied?

These questions arise over numeric quantities, but identically over ordered non-numeric values — grades, tiers, priorities, statuses. A range is a region over a declared *ordered space*, not a pair of numbers; a magnitude is the degenerate case where a range's bounds coincide. Naming a layer after the degenerate case is how the general case ends up invented twice, once properly and once badly in whichever ingest pipeline needs it first. Quantification exists to be the one place this is declared.

**What Quantification is not.** It is not a units-of-measure inventory, currency-code list, calendar, statistics package, formula language, or financial calculation engine. It ships no units, currencies, calendars, ordinal scales, business-day definitions, rates, thresholds, or recurrences — those are deployment content, bound to this mechanism the same way Vocabulary's scheme-contract mechanism lets a deployment bind its own concept schemes without Vocabulary shipping any.

Quantification does not require every use to be compiled. Its declarations and assertions may be queried directly with SPARQL, checked with SHACL, classified through an entailment regime, materialised into derived RDF, projected into an external store, or used to generate specialised code — these are alternative operational strategies over the same graph-native semantics, not a required pipeline.

## 2. Position and Namespace

Third in the substrate dependency order:

```
foundation
    └── vocabulary
            └── quantification
                    └── party
                            ├── instrument
                            ├── eligibility
                            └── behaviour
```

It imports Foundation and Vocabulary. It is imported by Party, Eligibility, Instrument, and Behaviour — none of which it imports back, and none of whose classes it ever references. This is the same discipline Party's document applies to Instrument, Eligibility, and Behaviour: Quantification is reusable by everything above it specifically because it never reaches upward to say how any of them will use it.

```turtle-spec
@prefix qnt:  <https://www.nebularis.org/neuro-semantic/lattice/quantification#> .
@prefix fnd:  <https://www.nebularis.org/neuro-semantic/lattice/foundation#> .
@prefix voc:  <https://www.nebularis.org/neuro-semantic/lattice/vocabulary#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
```

## 3. How to Read This Document

Same convention as Foundation, Vocabulary, and Party: genuine specification content — classes, properties, and their axioms — is fenced ` ```turtle-spec `; mechanism-intrinsic vocabulary (named individuals of open classes) is fenced ` ```turtle-vocab `; illustrative SHACL shapes are fenced ` ```turtle-shapes `; and worked-example content that is not part of the substrate is fenced ` ```turtle-example `. Only the first three are extracted when regenerating `spec/quantification.ttl`, `vocab/quantification-vocab.ttl`, and `shapes/*.ttl` respectively; `turtle-example` blocks are never extracted, regardless of where in the document they appear.

`fnd:utility` values throughout this document explain what a term is for and how to use it — never why it was shaped this way rather than some other way. That reasoning belongs in §4 (Design Decisions) alone, per the discipline corrected across Foundation, Vocabulary, and Party's own documents; nothing in this document's `fnd:utility` text should need to reference this section, a rejected alternative, or a dependency-order constraint to make sense to someone applying the term.

## 4. Design Decisions

Ten decisions, several forced by the corrected structure below rather than freely chosen — worth reading in full before treating any single class in isolation, since a number of the later definitions only make sense in light of one of these.

**Quantification, not Quantity.** Grades, tiers, statuses, and priorities need exactly the same containment, overlap, minimum, and maximum operations that magnitudes need, without being magnitudes. A layer named after magnitudes either excludes them — forcing every deployment to invent ordinal comparison privately — or admits them under a name that misdescribes what it actually is. The layer declares how a value space is *ordered, bounded, and compared*; that is Quantification, and the rename costs one import change now against every deployment inventing this privately later.

**A position and an extent are distinct spaces, not distinct readings of one space.** Two positions have a difference; a position plus an extent yields a position; two extents sum; adding two positions is not meaningful. Keeping these as genuinely separate declared spaces makes `position + position` unrepresentable rather than merely discouraged — the same "unwritable failure mode" discipline Behaviour applies to guard-versus-effect. Temporal modelling falls directly out of this: a temporal position is a point on a totally-ordered, unit-bearing space; a temporal interval is a range over it; a recurrence is a generator of canonically identified ranges. Temporal is therefore an instance of quantification, not a peer layer, and building it as a peer would duplicate ordering, bounds, normalisation, and canonical form for no reason.

**Overlap is not containment.** A value can be contained by the meet (intersection) of two ranges only if it's contained by both — that's `Q4a`, required of any range semantics claiming to support containment. The converse — a value contained by both individually is contained by their meet — is `Q4b`, and it holds for ordinary non-cyclic containment but *not* for overlap: two ranges can each overlap a third separately while having an empty three-way intersection. A semantics satisfying only `Q4a` is declared `ScreeningRangeSemantics` and must not be used for meet-based enumeration; only `ExactRangeSemantics` may be. This is a fact about ranges over an ordered space — this layer's fact to state, not a fact for every consumer to rediscover independently. §10 gives the formal statement; `qnt:participatesInMeet` gives consumers a declared answer rather than a rule to re-derive.

**Cyclic ranges are start-plus-extent.** A lower/upper pair is not globally meaningful on a cyclic space — "22:00 to 06:00" has no consistent answer to "which is lower" without picking an arbitrary cut point, and a two-bound model either rejects the wrapping window or truncates it silently, in the direction that happens to be wrong. Representing it as a start and an extent around the cycle sidesteps the question rather than answering it badly. But a cyclic range still has two endpoints, and each needs a declared closure exactly as an ordinary `Bound` does — an earlier draft of this layer gave `CyclicRange` no closure property at all, which meant containment couldn't be discharged for cyclic spaces even though `Bound` itself already required one. §6's `CyclicRange` definition fixes this.

**Granularity is not unresolvedness.** A value known only to a month is known — it denotes a range of possible exact values, not an absence. An unresolved value's required content is pending, unknown, contested, or unavailable — a genuinely different condition, needing different remediation. Both can produce `Undetermined`, but they carry different provenance and different reasons, and conflating them into one "precision" enumeration — as an earlier pass of this layer did — loses the distinction consumers actually need.

**Operation permission is declared rather than inferred from representation.** A value space stating it holds numeric literals does not thereby permit arithmetic over them — that has to be a separate, explicit `OperationCapability`. This is the layer's single highest-value check: "can I average these grades" becomes a load-time or query-time answer instead of a plausible-looking number nobody checked.

**Three law registers.** A semantic law (order coherence, bound coherence, containment soundness) is discharged by formal argument and property tests. A static declaration constraint (every value space declares a key and an order kind) is discharged by SPARQL, SHACL, or equivalent static analysis. A runtime conformance claim (a recurrence produces the same bin identity when recomputed independently) can only be discharged by actually running the computation twice and comparing — no formal argument alone establishes it. An earlier draft of this layer put all ten laws in one register with one discharge contract, which meant two of them — recurrence determinism and unresolved non-coercion — were effectively asserted by prose. §9 restructures the register into three, each with its own evidence shape.

**Conversion needs a registered function.** Declaring that a conversion exists between two units, without declaring *how*, leaves the actual transformation as an undeclared deployment detail. Quantification sits below Behaviour, so it owns the shared registered-function mechanism; Behaviour's own function registry should reuse this rather than inventing a parallel one.

**A range defined relative to an anchor keeps that relationship, rather than only keeping the two bounds it computes to.** A ±2% tolerance around a nominal value of 18,000 and a hand-authored band from 17,640 to 18,360 are indistinguishable once only the bounds are recorded — nothing says the first pair is derived from the second. That loses exactly the information a later reparameterisation (widening the tolerance to ±3%) needs: whether to rewrite the offset or rewrite two endpoints by hand. `AnchorBinding` keeps the derivation explicit.

**A value space's density determines what "adjacent" means and must be declared rather than assumed.** Range-set canonicalisation needs to know whether `[1,5]` and `[6,10]` merge — which depends entirely on whether the space is discrete (where "immediately following" is well-defined, via a granularity floor) or dense (where only closures abutting without a gap can merge). Leaving this undeclared, as an earlier draft did, made canonical form an open question for exactly the operation whose whole purpose is to have one.

## 5. Architecture

Four semantic tiers; the fourth is genuinely optional, not merely lightly used.

```
DECLARATION
    qnt:ValueSpace · qnt:UnitContract · qnt:Conversion · qnt:ConversionFunction
    qnt:OperationCapability · qnt:Recurrence · qnt:OrderingBasis · qnt:AnchorBinding
    versioned, governable, content-hashed
    "What kind of values exist, and what may be done with them?"

ASSERTION
    qnt:Value · qnt:Quantity · qnt:OrdinalValue · qnt:UnresolvedValue
    qnt:Bound · qnt:Range · qnt:CyclicRange · qnt:RangeSet
    qnt:ConversionContext · qnt:RecurrenceBin
    "What values, bounds, ranges, and contexts are actually present?"

EVALUATION
    qnt:Comparison · qnt:OperationRequest
    compare · contains · overlaps · convert · binOf
    "What can be concluded under a stated operational profile?"

OPTIONAL DERIVED REPRESENTATIONS
    range normal forms · conversion closures · materialised recurrence bins
    external projections · generated code
```

An operational profile must identify the source graph or snapshot, the declarations and versions used, the entailment regime if any, the validation profile if any, the implementation or query-set version, and its authority level (§10). Derived representations are not authored facts merely because they're persisted — they remain traceable to their inputs and producing profile.
## 6. Classes

### `qnt:ValueSpace`

**Definition.** A governed declaration of a space in which values may be represented, ordered, bounded, compared, and used by declared operations.

**Utility.** Declare one whenever values need a stated home: whether they can be ordered, whether they require units, which operations are valid over them, and — for a discrete space — what its granularity floor is. A deployment may declare numeric, ordinal, temporal-position, temporal-extent, or other spaces without needing a new substrate subclass.

```turtle-spec
qnt:ValueSpace a owl:Class ;
    rdfs:comment "A governed declaration of a space in which values may be represented, ordered, bounded, compared, and used by declared operations." ;
    fnd:utility "Declare a ValueSpace whenever values need a stated home — how they're ordered, whether they require units, and which operations are valid. Set densityKind so range-set normalisation knows what 'adjacent' means for this space, and cycleLength if the space is cyclically ordered." ;
    rdfs:subClassOf
        fnd:Version ,
        fnd:Governable ,
        [ a owl:Restriction ; owl:onProperty qnt:spaceKey ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:orderKind ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:spaceHash ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:densityKind ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:cycleLength ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ] .
```

### `qnt:Value`

**Definition.** A point value asserted in one declared ValueSpace.

**Utility.** Use as the generic point-value carrier where comparison, bounding, ordering, or provenance is needed but arithmetic isn't necessarily. Numeric values use `Quantity`; concept-valued ordinal values use `OrdinalValue`; a deployment may add further value representations while keeping the `onSpace` relation.

```turtle-spec
qnt:Value a owl:Class ;
    rdfs:comment "A point value asserted in one declared ValueSpace." ;
    fnd:utility "Use as the generic point-value carrier for values needing comparison, bounding, ordering, or evidence. Numeric values use Quantity; add other representations as needed while keeping the onSpace relation." ;
    rdfs:subClassOf [ a owl:Restriction ; owl:onProperty qnt:onSpace ; owl:cardinality "1"^^xsd:nonNegativeInteger ] .
```

### `qnt:Quantity`

**Definition.** A point value expressed as a literal, optionally in a unit governed by its ValueSpace's unit contract.

**Utility.** Use for numerically or otherwise literal-represented values. The literal's datatype follows the ValueSpace's declared `valueDatatype` where one is stated — this is not fixed to `xsd:decimal`, so a temporal position expressed as `xsd:dateTime`, an OWL-Time-aligned node, or any other space-appropriate literal all fit the same class. Whether the value can be added, averaged, divided, or converted is never implied by this class alone; those capabilities are declared on the ValueSpace.

```turtle-spec
qnt:Quantity a owl:Class ;
    rdfs:subClassOf qnt:Value ;
    rdfs:comment "A point value expressed as a literal, optionally in a unit governed by its ValueSpace's unit contract." ;
    fnd:utility "Use for literal-represented values. The literal's datatype follows the ValueSpace's declared valueDatatype rather than being fixed — a temporal position can use xsd:dateTime here as readily as a mass can use xsd:decimal. Numeric representation alone does not imply arithmetic or conversion is permitted." ;
    rdfs:subClassOf [ a owl:Restriction ; owl:onProperty qnt:numericValue ; owl:cardinality "1"^^xsd:nonNegativeInteger ] .
```

### `qnt:OrdinalValue`

**Definition.** A point value represented by a concept in an ordered deployment-defined scheme.

**Utility.** Use for ranked values — grades, tiers, priorities — where comparison is meaningful but arithmetic isn't. The ordering itself belongs to the declared ValueSpace and its scheme binding via `voc:SchemeContract`; the substrate ships no grade, tier, priority, or status inventory.

```turtle-spec
qnt:OrdinalValue a owl:Class ;
    rdfs:subClassOf qnt:Value ;
    rdfs:comment "A point value represented by a concept in an ordered deployment-defined scheme." ;
    fnd:utility "Use for ranked values such as grades or tiers where comparison is meaningful but arithmetic isn't. Point ordinalConcept at the backing skos:Concept; the substrate ships no scheme members." ;
    rdfs:subClassOf [ a owl:Restriction ; owl:onProperty qnt:ordinalConcept ; owl:cardinality "1"^^xsd:nonNegativeInteger ] .
```

### `qnt:UnresolvedValue`

**Definition.** A value whose required content is not currently available as a definite value in its declared space.

**Utility.** Use when a required value is pending, unknown, disputed, or unavailable — always with a declared reason and supporting evidence. Do not use this merely because a known value is coarse; that's what granularity (via `knownToGranularity`) expresses instead, and the two need different remediation.

```turtle-spec
qnt:UnresolvedValue a owl:Class ;
    rdfs:subClassOf qnt:Value, fnd:Evidenced ;
    rdfs:comment "A value whose required content is not currently available as a definite value in its declared space." ;
    fnd:utility "Use when a required value is pending, unknown, disputed, or unavailable, with a declared reason and evidence. Do not use this for a known-but-coarse value — see knownToGranularity instead." ;
    rdfs:subClassOf [ a owl:Restriction ; owl:onProperty qnt:unresolvedReason ; owl:minCardinality "1"^^xsd:nonNegativeInteger ] .
```

### `qnt:Bound`

**Definition.** An open or closed lower or upper limit expressed by a Value in one ValueSpace.

**Utility.** The mechanism behind ceilings, floors, thresholds, minimums, and maximums, none of which earn a separate class. Set `boundClosure` explicitly — whether the limit itself counts as within range is a real, non-cosmetic choice. A consuming layer or deployment decides whether a given bound is read as a ceiling, a threshold, or something else.

```turtle-spec
qnt:Bound a owl:Class ;
    rdfs:comment "An open or closed lower or upper limit expressed by a Value in one ValueSpace." ;
    fnd:utility "Use for any endpoint or limit — a ceiling, floor, or threshold. Always set boundClosure: whether the endpoint itself counts as within range changes the result, not just the presentation." ;
    rdfs:subClassOf
        [ a owl:Restriction ; owl:onProperty qnt:onSpace ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:boundValue ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:boundSense ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:boundClosure ; owl:cardinality "1"^^xsd:nonNegativeInteger ] .
```

### `qnt:Range`

**Definition.** A bounded region of one non-cyclic ValueSpace.

**Utility.** Use for admissible bands, windows, tolerances, and other regions determined by one declared space's order. A Range may carry one lower bound, one upper bound, or both — absence of a bound means unbounded in that direction, never a sentinel value, so a half-bounded "18 or over" range and a two-sided band use the same class with different bound cardinality. Where a range is derived from a nominal value and an offset rather than authored as two independent endpoints, point `relativeToAnchor` at the `AnchorBinding` that derives it.

```turtle-spec
qnt:Range a owl:Class ;
    rdfs:comment "A bounded region of one non-cyclic ValueSpace." ;
    fnd:utility "Use for two-sided or half-bounded regions. Set only lowerBound, only upperBound, or both — an absent bound means unbounded in that direction. If this range is derived from a nominal value and an offset, point relativeToAnchor at the AnchorBinding rather than authoring the two bounds independently." ;
    rdfs:subClassOf
        [ a owl:Restriction ; owl:onProperty qnt:onSpace ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:hasBound ; owl:minCardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:lowerBound ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:upperBound ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:relativeToAnchor ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ] .
```

### `qnt:CyclicRange`

**Definition.** A bounded region on a cyclic ValueSpace, represented by a start value and an extent around the cycle, each end independently closed or open.

**Utility.** Use for wrapping windows — an off-peak period crossing midnight, a season crossing a year boundary. Represented by start plus extent rather than lower plus upper endpoints, since a lower/upper ordering isn't globally meaningful on a cyclic space. Set `startClosure` and `endClosure` exactly as you would for an ordinary `Bound` — a cyclic range's endpoints are no less real for being expressed differently.

```turtle-spec
qnt:CyclicRange a owl:Class ;
    rdfs:comment "A bounded region on a cyclic ValueSpace, represented by a start value and an extent around the cycle, each end independently closed or open." ;
    fnd:utility "Use for a range that may wrap a cycle boundary — represent it by cycleStart and cycleExtent, not lower/upper endpoints. Set startClosure and endClosure exactly as for an ordinary Bound; a cyclic range's endpoints need closure declared just as much." ;
    rdfs:subClassOf
        [ a owl:Restriction ; owl:onProperty qnt:onSpace ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:cycleStart ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:cycleExtent ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:startClosure ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:endClosure ; owl:cardinality "1"^^xsd:nonNegativeInteger ] .
```

**Degenerate cases**, stated explicitly rather than left for each implementation to decide separately: a `cycleExtent` of zero denotes a single point, not an empty range; a `cycleExtent` equal to the space's `cycleLength` denotes the whole cycle; a `cycleExtent` exceeding `cycleLength` is a declaration error a validation profile must reject, not a range that wraps more than once.

### `qnt:RangeSet`

**Definition.** A collection of zero or more ranges over one ValueSpace.

**Utility.** Use where several disjoint regions are permitted together. An empty RangeSet may occur as a computed intersection result; an authoring profile may separately reject an empty RangeSet where an asserted admissible set must not be empty — that's a profile-level check, not a structural one.

```turtle-spec
qnt:RangeSet a owl:Class ;
    rdfs:comment "A collection of zero or more ranges over one ValueSpace." ;
    fnd:utility "Use for a union of ranges. An empty RangeSet may be a valid computed result even where an authoring profile rejects an empty asserted set." ;
    rdfs:subClassOf [ a owl:Restriction ; owl:onProperty qnt:onSpace ; owl:cardinality "1"^^xsd:nonNegativeInteger ] .
```

### `qnt:AnchorBinding`

**Definition.** A declared anchor value and offsets from which a Range's bounds are derived.

**Utility.** Use where a range is defined relative to a nominal or reference value — a tolerance, a margin, a window around a scheduled position — rather than authored as two independent bounds. The derived bounds may be materialised for direct querying, but the anchor and offsets remain the authored form, so widening a tolerance is a change to one offset, not a rewrite of two endpoints. Use `offsetKind` `Proportional` only where the space's operation capabilities include `Ratio` — a proportional offset is meaningless without it.

```turtle-spec
qnt:AnchorBinding a owl:Class ;
    rdfs:comment "A declared anchor value and offsets from which a Range's bounds are derived." ;
    fnd:utility "Use where a range is defined relative to a nominal value rather than as two independent bounds — a tolerance or a scheduled window. The anchor and offsets are the authored form even if the derived bounds are also materialised. Proportional offsets require the space to declare Ratio capability." ;
    rdfs:subClassOf
        [ a owl:Restriction ; owl:onProperty qnt:anchorValue ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:offsetKind ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:lowerOffset ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:upperOffset ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ] .
```

### `qnt:UnitContract`

**Definition.** A declaration governing whether values in a ValueSpace require units, which unit family applies, and how conversion, precision, and rounding are governed.

**Utility.** Separates the generic mechanism of unit-bearing values from any inventory of units, currencies, or measurement systems. A deployment binds the actual units and, where precision or rounding matters for a comparison, states the policy explicitly rather than leaving it to whichever implementation happens to run the calculation.

```turtle-spec
qnt:UnitContract a owl:Class ;
    rdfs:comment "A declaration governing whether values in a ValueSpace require units, which unit family applies, and how conversion, precision, and rounding are governed." ;
    fnd:utility "Declare whether a ValueSpace requires units, which unit family is permitted, and which unit is canonical. Set precisionPolicy and roundingPolicy where a comparison's exactness depends on them — the substrate ships no unit, precision, or rounding individuals." ;
    rdfs:subClassOf
        fnd:Version ,
        [ a owl:Restriction ; owl:onProperty qnt:requiresUnit ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:unitFamily ; owl:minCardinality "1"^^xsd:nonNegativeInteger ] .
```

### `qnt:Unit`, `qnt:UnitFamily`, `qnt:Conversion`, `qnt:ConversionFunction`

**Definition.** `Unit` is a deployment-defined measure designation; `UnitFamily` groups mutually governable units; `Conversion` declares that a transformation exists between two units; `ConversionFunction` is the registered, versioned function actually performing it.

**Utility.** `Unit` and `UnitFamily` are binding points — align them to QUDT, OM, ISO codes, or an internal vocabulary as needed; Quantification ships no inventory. A `Conversion` on its own only states that a transformation exists; give it a `conversionFactor` for the common linear case, or point `conversionFunction` at a registered `ConversionFunction` for anything else — never leave a `Defined` or `Contextual` conversion's actual transformation undeclared. Register a `ConversionFunction` once and reference it from every `Conversion` that uses it, the same way Behaviour's own function registry is expected to.

```turtle-spec
qnt:Unit a owl:Class ;
    rdfs:comment "A deployment-defined designation for expressing values in a unit-bearing ValueSpace." ;
    fnd:utility "Use as a value object supplied by a deployment or aligned external vocabulary. The substrate ships no unit individuals." .

qnt:UnitFamily a owl:Class ;
    rdfs:comment "A deployment-defined family of units governed by one conversion contract." ;
    fnd:utility "Use to group units a ValueSpace permits and whose conversion rules are declared together." .

qnt:Conversion a owl:Class ;
    rdfs:subClassOf fnd:Version ;
    rdfs:comment "A declared transformation between two units in a UnitFamily." ;
    fnd:utility "State how a value in one unit becomes comparable with a value in another. Give it a conversionFactor for the linear case, or a conversionFunction for anything else — never leave the transformation itself undeclared. Contextual conversions additionally need a ConversionContext at evaluation time." ;
    rdfs:subClassOf
        [ a owl:Restriction ; owl:onProperty qnt:fromUnit ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:toUnit ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:conversionKind ; owl:cardinality "1"^^xsd:nonNegativeInteger ] .

qnt:ConversionFunction a owl:Class ;
    rdfs:subClassOf fnd:Version, fnd:Evidenced ;
    rdfs:comment "A registered, versioned, deterministic function transforming values between two units." ;
    fnd:utility "Register one of these when a conversion is not a simple factor — declare its signature and determinism claim, and attach conformance evidence via fnd:hasEvidence. Reference it from every Conversion that uses it, rather than restating the transformation per conversion." .
```

### `qnt:ConversionContext`

**Definition.** An evidenced context supplying the observation or reference required for a contextual conversion.

**Utility.** Use where conversion depends on a stated reference observation or position — an index value, an exchange rate at a point in time. Its absence doesn't make the surrounding data invalid RDF; it makes a comparison requiring that conversion indeterminate under the relevant profile. Give it a context even for a `Defined` conversion only where provenance for that specific conversion matters to record — it's required only for `Contextual`.

```turtle-spec
qnt:ConversionContext a owl:Class ;
    rdfs:subClassOf fnd:Evidenced, fnd:TemporallyScoped ;
    rdfs:comment "An evidenced context supplying the observation or reference required for a contextual conversion." ;
    fnd:utility "Use where conversion depends on an external observation or reference position. Required for a Contextual conversion; optional provenance for any other kind. Its absence makes a dependent comparison indeterminate, not the underlying data invalid." .
```

### `qnt:DerivedValueSpace`

**Definition.** A value space whose values are quotients of values in two other spaces.

**Utility.** Rates and proportions (ADR-A93): a dose per body weight, a credit as a share of a fee. `qnt:Scale` applies a rate to a base value, and `qnt:Ratio` of two values names the derived space as its result space.

```turtle-spec
qnt:DerivedValueSpace a owl:Class ;
    rdfs:subClassOf qnt:ValueSpace ;
    rdfs:comment "A value space whose values are quotients of values in two other spaces (ADR-A93)." ;
    fnd:utility "Declare one for a rate or a proportion: point numeratorSpace and denominatorSpace at the spaces it divides. A proportion names the same space twice, so 10% of a fee and 10% of an income stay different spaces." ;
    rdfs:subClassOf
        [ a owl:Restriction ; owl:onProperty qnt:numeratorSpace ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:denominatorSpace ; owl:cardinality "1"^^xsd:nonNegativeInteger ] .
```

### `qnt:CalendarUnit` and `qnt:Calendar`

**Definition.** `CalendarUnit` is a unit whose relation to elapsed time depends on a calendar. `Calendar` is a calendar edition, governed and resolved as a concept scheme edition.

**Utility.** Business-day extents (ADR-A94). Converting one to elapsed time is a `Contextual` conversion whose context names the calendar's scheme contract and the starting position. Without that context a dependent comparison is `Undetermined` (§9.6).

```turtle-spec
qnt:CalendarUnit a owl:Class ;
    rdfs:subClassOf qnt:Unit ;
    rdfs:comment "A unit whose relation to elapsed time depends on a calendar, such as a business day (ADR-A94)." ;
    fnd:utility "Use for business days or working hours. Any conversion to or from it is Contextual: its ConversionContext names the calendar with underCalendar and the position counted from with fromPosition." .

qnt:Calendar a owl:Class ;
    rdfs:subClassOf voc:ConceptScheme ;
    rdfs:comment "A deployment-supplied calendar edition, governed and resolved as a concept scheme edition (ADR-A94)." ;
    fnd:utility "Declare each calendar edition as a Calendar and bind it to a SchemeContract, so the calendar in force for a context's scope and time is resolved as any scheme is. Its working-day content stays with the deployment." .
```

### `qnt:OperationCapability`

**Definition.** A declared permission and signature for applying one operation to values in specified ValueSpaces.

**Utility.** The layer's protection against category errors — declares operand spaces and result space rather than assuming a shared representation implies valid arithmetic. Where `operationKind` is `Contains` or `Overlaps`, also set `rangeSemanticsKind` and `participatesInMeet`: overlap-based screening and containment-based enumeration are not interchangeable, and a consumer needs to know which one this capability provides without re-deriving it from the operation kind alone.

```turtle-spec
qnt:OperationCapability a owl:Class ;
    rdfs:subClassOf fnd:Version ;
    rdfs:comment "A declared permission and signature for applying one operation to values in specified ValueSpaces." ;
    fnd:utility "Declare which operations a ValueSpace permits, their operand spaces, and their result space. For Contains or Overlaps, also set rangeSemanticsKind and participatesInMeet — a consumer doing meet-based enumeration needs to know directly whether this capability is safe to use for it, not re-derive it from the operation kind." ;
    rdfs:subClassOf
        [ a owl:Restriction ; owl:onProperty qnt:operationKind ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:resultSpace ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:rangeSemanticsKind ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:participatesInMeet ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ] .
```

Note: `Compare`, `Contains`, and `Overlaps` produce a `qnt:Comparison`, not a value in a `resultSpace` — comparison is three-valued and `Comparison` already carries the result. `resultSpace` applies only to value-producing operations such as `Difference`, `Sum`, or `Ratio`.

### `qnt:OperationOperand`

**Definition.** A numbered operand position in an OperationCapability signature.

**Utility.** Use where an operation needs several typed operands — `position − position → extent` is the motivating case, needing two operand positions on the position space and a result on the extent space. Numbered slots preserve signature order without hardcoding operator-specific argument properties.

```turtle-spec
qnt:OperationOperand a owl:Class ;
    rdfs:comment "A numbered operand position in an OperationCapability signature." ;
    fnd:utility "Use where an operation needs several typed operands, such as position minus position yielding an extent. Declare the required ValueSpace at each argument position; shapes ensure no two positions share an index." ;
    rdfs:subClassOf
        [ a owl:Restriction ; owl:onProperty qnt:operandIndex ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:operandSpace ; owl:cardinality "1"^^xsd:nonNegativeInteger ] .
```

### `qnt:Recurrence` and `qnt:RecurrenceBin`

**Definition.** `Recurrence` declares a deterministic generator of identified ranges over a compatible extent space; `RecurrenceBin` is one generated or materialised range produced by it.

**Utility.** A recurrence must produce a stable bin identity so independently executed processes agree on which bin a given position falls in, without relying on a mutable ordinal position like "the third period." Declare `binContiguity` and `boundaryDerivation` as two separate axes — whether bins may have gaps between them, and how a boundary is derived when the anchor doesn't land cleanly (a month-end anchor in a short month is the motivating case) are different questions, and a single `alignmentPolicy` conflating them can't answer both. Set `validRange` where the recurrence isn't defined for all positions.

```turtle-spec
qnt:Recurrence a owl:Class ;
    rdfs:subClassOf fnd:Version, fnd:Governable ;
    rdfs:comment "A governed declaration of a deterministic generator of canonically identified ranges over a compatible extent space." ;
    fnd:utility "Use for repeated periods. Declare an anchor, a period whose space is extent-compatible with the anchor's position space, a binContiguity and boundaryDerivation policy, and a binKeyStrategy — so independently executed processes identify the same generated bin. Set validRange if the recurrence has a bounded domain." ;
    rdfs:subClassOf
        [ a owl:Restriction ; owl:onProperty qnt:anchor ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:period ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:binContiguity ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:boundaryDerivation ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:binKeyStrategy ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:validRange ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ] .

qnt:RecurrenceBin a owl:Class ;
    rdfs:subClassOf qnt:Range ;
    rdfs:comment "A canonically identified range generated by a Recurrence." ;
    fnd:utility "Use for a range produced from a recurrence declaration, whether calculated live, materialised, or projected externally. Always retain its recurrence source and canonical bin key." ;
    rdfs:subClassOf
        [ a owl:Restriction ; owl:onProperty qnt:generatedByRecurrence ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:binKey ; owl:cardinality "1"^^xsd:nonNegativeInteger ] .
```

`binOf(recurrence, position)` — the operation this whole declaration exists to support — returns the unique bin containing `position`, or `Undetermined` with a declared reason where the position is unresolved, is known only to a granularity coarser than the bin boundary, or falls outside `validRange`.

**Period-space compatibility** is a static declaration constraint (§10, obligation set out under "static"): a `Recurrence`'s `period` must be on an extent space compatible with its `anchor`'s position space. Nothing in the T-box above prevents an anchor on a grade space and a period on a mass space; catching that is a SHACL-level check, per the same T-box/SHACL boundary already established in Foundation's document for `supersededBy`'s same-identity requirement.

### `qnt:OrderingBasis` and `qnt:OrderingComponent`

**Definition.** `OrderingBasis` declares deterministic ordering using an ordered sequence of components and an unresolved-order policy; `OrderingComponent` is one positioned criterion within it.

**Utility.** Use `OrderingBasis` wherever a process must order occurrences deterministically and a single position can't establish it alone — two events sharing a timestamp, needing a declared tie-breaker rather than whatever a database's insertion order or a wall clock happens to produce. Give each criterion its own `OrderingComponent` with an explicit `componentDirection`, so the whole ordering is a declared property of the data rather than an implementation convention nobody wrote down.

```turtle-spec
qnt:OrderingBasis a owl:Class ;
    rdfs:subClassOf fnd:Version ;
    rdfs:comment "A declaration of deterministic ordering using an ordered sequence of components and an unresolved-order policy." ;
    fnd:utility "Use where a process must order occurrences deterministically and a single position can't establish it alone. Add one OrderingComponent per criterion, in priority order, and state what happens when an ordering value is unresolved." ;
    rdfs:subClassOf
        [ a owl:Restriction ; owl:onProperty qnt:hasOrderingComponent ; owl:minCardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:unresolvedOrderPolicy ; owl:cardinality "1"^^xsd:nonNegativeInteger ] .

qnt:OrderingComponent a owl:Class ;
    rdfs:comment "One positioned criterion within an OrderingBasis." ;
    fnd:utility "Use to declare each ordering criterion, its position among the others, and its direction — so a scheduled read and a correction sharing a timestamp resolve deterministically rather than by whichever the store happened to return first." ;
    rdfs:subClassOf
        [ a owl:Restriction ; owl:onProperty qnt:componentIndex ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:componentSpace ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:componentDirection ; owl:cardinality "1"^^xsd:nonNegativeInteger ] .
```

An `OrderingBasis` whose components do not totally order a given input set under the declared `unresolvedOrderPolicy` is a declaration error under runtime conformance (`Q11`, §9) — this can only be caught by actually running the ordering over a representative input set, not by inspecting the declaration alone.

### `qnt:Comparison`

**Definition.** An evidenced result of comparing values, ranges, or both under a stated value space and operational profile.

**Utility.** Use where a comparison result must be retained, explained, audited, or reused rather than silently re-evaluated or discarded. Records the truth value, any relevant unresolved reasons, and the producing operational profile — a persisted Comparison is a derived, evidenced record, not an authored fact.

```turtle-spec
qnt:Comparison a owl:Class ;
    rdfs:subClassOf fnd:Evidenced ;
    rdfs:comment "An evidenced result of comparing values, ranges, or both under a stated value space and operational profile." ;
    fnd:utility "Use where a comparison result must be retained, explained, audited, or reused. Records the truth value, any unresolved reasons, and the producing operational profile." ;
    rdfs:subClassOf
        [ a owl:Restriction ; owl:onProperty qnt:comparisonResult ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:comparisonProfile ; owl:cardinality "1"^^xsd:nonNegativeInteger ] .
```

### `qnt:OperationalProfile`, `qnt:OperationRequest`

**Definition.** `OperationalProfile` identifies the implementation strategy and version under which an operation was evaluated; `OperationRequest` is a recorded request to apply an operation, whether or not a matching capability exists to satisfy it.

**Utility.** Every persisted `Comparison` names an `OperationalProfile` — a SPARQL query set, a SHACL package, a reasoner configuration, a materialisation job, an external projection, or a compiled evaluator, together with its version, so a result's provenance says how it was produced as well as what it concluded. Use `OperationRequest` where a request must itself be recorded, audited, or rejected with a reason — it may exist in the graph even where no matching `OperationCapability` exists, in which case the resulting `Comparison` records `OperationNotPermitted`.

```turtle-spec
qnt:OperationalProfile a owl:Class ;
    rdfs:subClassOf fnd:Version ;
    rdfs:comment "A declared implementation strategy and configuration under which a Quantification operation is evaluated." ;
    fnd:utility "Identifies the realisation strategy that produced a result — a SPARQL query set, SHACL package, reasoner configuration, materialisation job, external projection, or compiled evaluator — together with its version. Every persisted Comparison names one." .

qnt:OperationRequest a owl:Class ;
    rdfs:comment "A recorded request to apply an operation to values in stated ValueSpaces." ;
    fnd:utility "Use where a request must be recorded, audited, or rejected with a reason. A request may exist even where no matching OperationCapability does; the resulting Comparison then records OperationNotPermitted." ;
    rdfs:subClassOf
        [ a owl:Restriction ; owl:onProperty qnt:requestedOperation ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:requestedOnSpace ; owl:minCardinality "1"^^xsd:nonNegativeInteger ] .
```

### `qnt:Law`, `qnt:LawDischarge`, and its three registers

**Definition.** `Law` is a stated semantic obligation over Quantification mechanism, belonging to one of three registers. `LawDischarge` is evidence discharging one law for one implementation profile; its three subclasses carry the distinct evidence each register requires.

**Utility.** Consult `lawRegister` before asking how a law can be discharged, since the three registers genuinely need different kinds of evidence. A `SemanticLawDischarge` names a formal argument. A `StaticConstraintDischarge` names the static analysis method that checked it. A `RuntimeConformanceDischarge` names an actually executed test run — no formal argument alone discharges a runtime-conformance law, because the claim is about what an implementation does when run, not about what's provable from the declaration. Adding a new deployment `ValueSpace` never requires a new discharge; adding a new order kind, conversion kind, range semantics, or operation kind does.

```turtle-spec
qnt:Law a owl:Class ;
    rdfs:comment "A stated semantic obligation over Quantification mechanism, belonging to one of three registers." ;
    fnd:utility "Check lawRegister before determining how this law is discharged — semantic laws need a formal argument, static constraints need static analysis, runtime conformance needs an executed test run. See §10 for the full register." ;
    rdfs:subClassOf [ a owl:Restriction ; owl:onProperty qnt:lawRegister ; owl:cardinality "1"^^xsd:nonNegativeInteger ] .

qnt:LawDischarge a owl:Class ;
    rdfs:subClassOf fnd:Evidenced ;
    rdfs:comment "Recorded evidence discharging one Law for one implementation profile." ;
    fnd:utility "A discharge names the law, the evidence supporting it via fnd:hasEvidence, and the implementation profile it was proved or tested against. An assertion without evidence does not discharge a law — use one of the three subclasses below rather than this class directly." ;
    rdfs:subClassOf
        [ a owl:Restriction ; owl:onProperty qnt:dischargesLaw ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
        [ a owl:Restriction ; owl:onProperty qnt:dischargedForImplementationProfile ; owl:cardinality "1"^^xsd:nonNegativeInteger ] .

qnt:SemanticLawDischarge a owl:Class ;
    rdfs:subClassOf qnt:LawDischarge ;
    rdfs:comment "A LawDischarge for a semantic law, evidenced by formal argument and property tests." ;
    fnd:utility "Use for order coherence, bound coherence, containment, overlap, conversion, or closure laws — cite the formal argument as evidence and record any property tests run against it." ;
    rdfs:subClassOf [ a owl:Restriction ; owl:onProperty qnt:formalArgumentReference ; owl:minCardinality "1"^^xsd:nonNegativeInteger ] .

qnt:StaticConstraintDischarge a owl:Class ;
    rdfs:subClassOf qnt:LawDischarge ;
    rdfs:comment "A LawDischarge for a static declaration constraint, evidenced by SPARQL, SHACL, reasoner, or compiled analysis." ;
    fnd:utility "Use for a constraint checkable from the declaration alone, without running anything — record which analysis method checked it." ;
    rdfs:subClassOf [ a owl:Restriction ; owl:onProperty qnt:staticAnalysisMethod ; owl:cardinality "1"^^xsd:nonNegativeInteger ] .

qnt:RuntimeConformanceDischarge a owl:Class ;
    rdfs:subClassOf qnt:LawDischarge ;
    rdfs:comment "A LawDischarge for a runtime conformance claim, evidenced only by an executed test run." ;
    fnd:utility "Use for a claim about implementation behaviour — recurrence determinism, unresolved non-coercion, ordering determinism. Record the executed test run; a formal argument alone never satisfies this discharge type." ;
    rdfs:subClassOf [ a owl:Restriction ; owl:onProperty qnt:executedTestRun ; owl:minCardinality "1"^^xsd:nonNegativeInteger ] .
```

### Disjointness

```turtle-spec
[] a owl:AllDisjointClasses ;
    owl:members (
        qnt:ValueSpace qnt:Value qnt:Bound qnt:Range qnt:RangeSet qnt:AnchorBinding
        qnt:UnitContract qnt:Unit qnt:UnitFamily qnt:Conversion qnt:ConversionFunction
        qnt:ConversionContext qnt:OperationCapability qnt:OperationOperand
        qnt:Recurrence qnt:OrderingBasis qnt:OrderingComponent qnt:Comparison
        qnt:OperationalProfile qnt:OperationRequest qnt:Law qnt:LawDischarge
    ) .

qnt:Quantity owl:disjointWith qnt:OrdinalValue, qnt:UnresolvedValue .
qnt:OrdinalValue owl:disjointWith qnt:UnresolvedValue .
qnt:CyclicRange owl:disjointWith qnt:Range .
qnt:SemanticLawDischarge owl:disjointWith qnt:StaticConstraintDischarge, qnt:RuntimeConformanceDischarge .
qnt:StaticConstraintDischarge owl:disjointWith qnt:RuntimeConformanceDischarge .
```

**Utility.** The first group is the substrate's distinct top-level constructs — none should ever be classified as another. `Quantity`, `OrdinalValue`, and `UnresolvedValue` are three distinct kinds of `Value` and pairwise disjoint for the same reason. `CyclicRange` is disjoint from `Range` because a value space is either cyclically ordered or not (governance obligation 3, §10) — nothing should be classified as both range forms at once. The three discharge subclasses are pairwise disjoint because a single discharge names exactly one evidence contract.
## 7. Properties

```turtle-spec
qnt:spaceKey a owl:DatatypeProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:ValueSpace ; rdfs:range xsd:string ;
    rdfs:comment "A stable key for a ValueSpace." ;
    fnd:utility "Use as a stable deployment-local identifier for canonical ordering, generated artefacts, and hash construction." .

qnt:spaceHash a owl:DatatypeProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:ValueSpace ; rdfs:range xsd:string ;
    rdfs:comment "The canonical semantic hash of a ValueSpace declaration." ;
    fnd:utility "Records the hash of the canonical, meaning-bearing content of a ValueSpace declaration — not a hash of arbitrary RDF serialisation." .

qnt:onSpace a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:range qnt:ValueSpace ;
    rdfs:comment "The ValueSpace in which a value, bound, range, or range set is expressed." ;
    fnd:utility "Set this so a value and its bounds are interpreted under one declared ordering and operation contract." .

qnt:orderKind a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:ValueSpace ; rdfs:range qnt:OrderKind ;
    rdfs:comment "The ordering form declared for a ValueSpace." ;
    fnd:utility "Declares whether a ValueSpace is totally ordered, cyclically ordered, or unordered for range purposes." .

qnt:densityKind a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:ValueSpace ; rdfs:range qnt:DensityKind ;
    rdfs:comment "Whether a ValueSpace is discrete, dense, or unspecified for the purpose of range-set adjacency." ;
    fnd:utility "Set this so range-set normalisation knows what counts as adjacent. Discrete spaces merge via granularityFloor; dense spaces merge only where closures abut without a gap; Unspecified spaces are never merged on adjacency, only on overlap." .

qnt:granularityFloor a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:ValueSpace ; rdfs:range qnt:Quantity ;
    rdfs:comment "The default minimum increment between distinguishable values in a discrete ValueSpace." ;
    fnd:utility "Set on a Discrete space so adjacency has a definite meaning, and so GranularityInsufficient has a default to compare a value's own granularity against." .

qnt:cycleLength a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:ValueSpace ; rdfs:range qnt:Quantity ;
    rdfs:comment "The extent of one full cycle of a CyclicOrder ValueSpace." ;
    fnd:utility "Required on any CyclicOrder space — without it, a CyclicRange's extent cannot be checked against the space it wraps around." .

qnt:valueDatatype a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:ValueSpace ; rdfs:range rdfs:Datatype ;
    rdfs:comment "The literal datatype expected of Quantity values in this ValueSpace." ;
    fnd:utility "Set where a space's values should use a specific literal datatype other than the default — an OWL-Time-aligned xsd:dateTime for a temporal position space, for instance. Leave unset to allow xsd:decimal." .

qnt:hasOperationCapability a owl:ObjectProperty ;
    rdfs:domain qnt:ValueSpace ; rdfs:range qnt:OperationCapability ;
    rdfs:comment "An operation capability declared for a ValueSpace." ;
    fnd:utility "Links a ValueSpace to each operation signature it permits. Never assume an operation not declared here." .

qnt:unitContract a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:ValueSpace ; rdfs:range qnt:UnitContract ;
    rdfs:comment "The optional unit contract governing values in a ValueSpace." ;
    fnd:utility "Set where a space's values require or permit governed units and conversion." .

qnt:numericValue a owl:DatatypeProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:Quantity ; rdfs:range rdfs:Literal ;
    rdfs:comment "The literal representation of a Quantity, in the datatype its ValueSpace declares." ;
    fnd:utility "Stores the literal value of a Quantity. Check the ValueSpace's valueDatatype for the expected datatype rather than assuming xsd:decimal." .

qnt:ordinalConcept a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:OrdinalValue ; rdfs:range skos:Concept ;
    rdfs:comment "The concept representing an OrdinalValue." ;
    fnd:utility "Points an ordinal value at its deployment-defined concept. Scheme governance and ordering are declared outside the substrate." .

qnt:inUnit a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:Quantity ; rdfs:range qnt:Unit ;
    rdfs:comment "The unit in which a Quantity is expressed." ;
    fnd:utility "Set where the ValueSpace's unit contract requires an explicit unit. A unit-less quantity is permitted only where that contract allows it." .

qnt:knownToGranularity a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:Value ; rdfs:range qnt:Quantity ;
    rdfs:comment "The declared extent of precision with which a Value is known." ;
    fnd:utility "Set when a value is present but stands for a region of possible exact values. A comparison needing finer distinction than this returns Undetermined with GranularityInsufficient." .

qnt:boundValue a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:Bound ; rdfs:range qnt:Value ;
    rdfs:comment "The value forming a Bound's endpoint." ;
    fnd:utility "Points a bound at its endpoint value, in the same ValueSpace as the Bound." .

qnt:boundSense a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:Bound ; rdfs:range qnt:BoundSense ;
    rdfs:comment "Whether a Bound is lower or upper." .

qnt:boundClosure a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:Bound ; rdfs:range qnt:Closure ;
    rdfs:comment "Whether a Bound includes or excludes its endpoint." .

qnt:hasBound a owl:ObjectProperty ;
    rdfs:domain qnt:Range ; rdfs:range qnt:Bound ;
    rdfs:comment "A Bound belonging to a Range." ;
    fnd:utility "Use to attach one lower and/or one upper bound to a Range." .

qnt:lowerBound a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:Range ; rdfs:range qnt:Bound ; rdfs:subPropertyOf qnt:hasBound ;
    rdfs:comment "The optional lower Bound of a Range." .

qnt:upperBound a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:Range ; rdfs:range qnt:Bound ; rdfs:subPropertyOf qnt:hasBound ;
    rdfs:comment "The optional upper Bound of a Range." .

qnt:relativeToAnchor a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:Range ; rdfs:range qnt:AnchorBinding ;
    rdfs:comment "The AnchorBinding a Range's bounds are derived from, where it has one." ;
    fnd:utility "Set where a range's bounds are computed from a nominal value and offsets, so the derivation stays explicit rather than only the computed endpoints." .

qnt:hasRange a owl:ObjectProperty ;
    rdfs:domain qnt:RangeSet ; rdfs:range qnt:Range ;
    rdfs:comment "A Range belonging to a RangeSet." ;
    fnd:utility "State each member range of a RangeSet. A normalisation process may merge adjacent or overlapping members where the ValueSpace's densityKind permits it." .

qnt:cycleStart a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:CyclicRange ; rdfs:range qnt:Value ;
    rdfs:comment "The starting point of a CyclicRange." .

qnt:cycleExtent a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:CyclicRange ; rdfs:range qnt:Quantity ;
    rdfs:comment "The extent travelled from a CyclicRange's start around its cycle." ;
    fnd:utility "Use rather than an upper endpoint for cyclic ranges. Its ValueSpace must be compatible with the cyclic space's declared cycleLength." .

qnt:startClosure a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:CyclicRange ; rdfs:range qnt:Closure ;
    rdfs:comment "Whether a CyclicRange's start point is included." .

qnt:endClosure a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:CyclicRange ; rdfs:range qnt:Closure ;
    rdfs:comment "Whether a CyclicRange's end point (start plus extent) is included." .

qnt:anchorValue a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:AnchorBinding ; rdfs:range qnt:Value ;
    rdfs:comment "The nominal or reference value an AnchorBinding's offsets are relative to." .

qnt:offsetKind a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:AnchorBinding ; rdfs:range qnt:OffsetKind ;
    rdfs:comment "Whether an AnchorBinding's offsets are absolute or proportional to the anchor value." .

qnt:lowerOffset a owl:DatatypeProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:AnchorBinding ; rdfs:range xsd:decimal ;
    rdfs:comment "The offset below the anchor value, in the units or proportion offsetKind declares." .

qnt:upperOffset a owl:DatatypeProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:AnchorBinding ; rdfs:range xsd:decimal ;
    rdfs:comment "The offset above the anchor value, in the units or proportion offsetKind declares." .

qnt:requiresUnit a owl:DatatypeProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:UnitContract ; rdfs:range xsd:boolean ;
    rdfs:comment "Whether values governed by a UnitContract require an explicit unit." .

qnt:unitFamily a owl:ObjectProperty ;
    rdfs:domain qnt:UnitContract ; rdfs:range qnt:UnitFamily ;
    rdfs:comment "A unit family permitted by a UnitContract." .

qnt:canonicalUnit a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:UnitContract ; rdfs:range qnt:Unit ;
    rdfs:comment "The unit used as the canonical representation under a UnitContract." ;
    fnd:utility "Identifies the unit a normalisation or materialisation profile uses. Does not require every asserted value to already be stored in it." .

qnt:precisionPolicy a owl:DatatypeProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:UnitContract ; rdfs:range rdfs:Literal ;
    rdfs:comment "A deployment-declared statement of the precision a comparison under this contract requires." ;
    fnd:utility "Set where comparisons under this contract need a stated precision requirement rather than relying on incidental literal precision. No fixed vocabulary is defined yet for this property's value — see the open items." .

qnt:roundingPolicy a owl:DatatypeProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:UnitContract ; rdfs:range rdfs:Literal ;
    rdfs:comment "A deployment-declared statement of how values under this contract are rounded before comparison." ;
    fnd:utility "Set where rounding behaviour affects a comparison's result and needs to be explicit rather than left to whichever implementation runs it. No fixed vocabulary is defined yet for this property's value — see the open items." .

qnt:fromUnit a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:Conversion ; rdfs:range qnt:Unit ;
    rdfs:comment "The source unit of a Conversion." .

qnt:toUnit a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:Conversion ; rdfs:range qnt:Unit ;
    rdfs:comment "The destination unit of a Conversion." .

qnt:conversionKind a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:Conversion ; rdfs:range qnt:ConversionKind ;
    rdfs:comment "The kind of transformation declared by a Conversion." ;
    fnd:utility "Distinguishes exact, defined, and contextual conversion semantics." .

qnt:conversionFactor a owl:DatatypeProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:Conversion ; rdfs:range xsd:decimal ;
    rdfs:comment "A linear multiplicative factor for a Defined Conversion." ;
    fnd:utility "Use for the common linear case — target = source × factor. For anything non-linear, use conversionFunction instead." .

qnt:conversionFunction a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:Conversion ; rdfs:range qnt:ConversionFunction ;
    rdfs:comment "The registered function performing a non-linear Conversion." ;
    fnd:utility "Use for a conversion that isn't a simple factor. Point at a registered ConversionFunction rather than an undeclared deployment detail." .

qnt:conversionContext a owl:ObjectProperty ;
    rdfs:domain qnt:Comparison ; rdfs:range qnt:ConversionContext ;
    rdfs:comment "The context used by a Comparison requiring contextual conversion." ;
    fnd:utility "Records the supplied conversion context for a comparison. Its absence is an explicit source of an indeterminate result where contextual conversion is required." .

qnt:operationKind a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:OperationCapability ; rdfs:range qnt:OperationKind ;
    rdfs:comment "The operation permitted by an OperationCapability." .

qnt:rangeSemanticsKind a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:OperationCapability ; rdfs:range qnt:RangeSemanticsKind ;
    rdfs:comment "Whether a Contains or Overlaps capability provides exact or screening-only range semantics." ;
    fnd:utility "Set on any Contains or Overlaps capability. ExactRangeSemantics satisfies both meet soundness and completeness; ScreeningRangeSemantics satisfies soundness only and must not be used for meet-based enumeration — see participatesInMeet." .

qnt:participatesInMeet a owl:DatatypeProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:OperationCapability ; rdfs:range xsd:boolean ;
    rdfs:comment "Whether this capability's results may be used in meet-based (intersection) enumeration." ;
    fnd:utility "Read this directly rather than re-deriving it from rangeSemanticsKind — true only for ExactRangeSemantics. Eligibility's meet-based strategies consume this as a declared answer, not a rule to reimplement." .

qnt:hasOperand a owl:ObjectProperty ;
    rdfs:domain qnt:OperationCapability ; rdfs:range qnt:OperationOperand ;
    rdfs:comment "An operand slot in an operation capability signature." .

qnt:operandIndex a owl:DatatypeProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:OperationOperand ; rdfs:range xsd:nonNegativeInteger ;
    rdfs:comment "The zero-based position of an operation operand." .

qnt:operandSpace a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:OperationOperand ; rdfs:range qnt:ValueSpace ;
    rdfs:comment "The ValueSpace required at one operation operand position." .

qnt:resultSpace a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:OperationCapability ; rdfs:range qnt:ValueSpace ;
    rdfs:comment "The ValueSpace in which a value-producing operation yields its result." ;
    fnd:utility "Set for Difference, Sum, Ratio, and similar value-producing operations. Not used for Compare, Contains, or Overlaps, which produce a Comparison instead." .

qnt:anchor a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:Recurrence ; rdfs:range qnt:Value ;
    rdfs:comment "The anchor from which a Recurrence generates bins." .

qnt:period a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:Recurrence ; rdfs:range qnt:Quantity ;
    rdfs:comment "The extent between recurrence bin boundaries." ;
    fnd:utility "State the repeated extent of a recurrence. Its ValueSpace must be extent-compatible with the anchor's position space — checked as a static declaration constraint, not an OWL restriction here." .

qnt:binContiguity a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:Recurrence ; rdfs:range qnt:BinContiguity ;
    rdfs:comment "Whether a Recurrence's generated bins are contiguous or may have gaps between them." .

qnt:boundaryDerivation a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:Recurrence ; rdfs:range qnt:BoundaryDerivation ;
    rdfs:comment "How a Recurrence derives a bin boundary when the anchor does not land cleanly on it." ;
    fnd:utility "Set explicitly for cases like a monthly recurrence anchored on the 31st in a 30-day month — declare whether the anchor day is preserved where possible or the boundary always aligns to period end." .

qnt:binKeyStrategy a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:Recurrence ; rdfs:range qnt:BinKeyStrategy ;
    rdfs:comment "The strategy used to derive canonical identifiers for recurrence bins." .

qnt:validRange a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:Recurrence ; rdfs:range qnt:Range ;
    rdfs:comment "The bounded domain over which a Recurrence is defined, if it is not defined everywhere." ;
    fnd:utility "Set where binOf should return Undetermined with OutsideDeclaredSpace for a position outside this range, rather than extrapolating the recurrence indefinitely." .

qnt:generatedByRecurrence a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:RecurrenceBin ; rdfs:range qnt:Recurrence ;
    rdfs:comment "The Recurrence that generated a RecurrenceBin." .

qnt:binKey a owl:DatatypeProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:RecurrenceBin ; rdfs:range xsd:string ;
    rdfs:comment "The canonical stable identifier of a RecurrenceBin." .

qnt:hasOrderingComponent a owl:ObjectProperty ;
    rdfs:domain qnt:OrderingBasis ; rdfs:range qnt:OrderingComponent ;
    rdfs:comment "An OrderingComponent belonging to an OrderingBasis." ;
    fnd:utility "Add one per ordering criterion, each with its own componentIndex giving its priority." .

qnt:componentIndex a owl:DatatypeProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:OrderingComponent ; rdfs:range xsd:nonNegativeInteger ;
    rdfs:comment "The priority position of an OrderingComponent within its OrderingBasis, lower values evaluated first." .

qnt:componentSpace a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:OrderingComponent ; rdfs:range qnt:ValueSpace ;
    rdfs:comment "The ValueSpace an OrderingComponent orders by." .

qnt:componentDirection a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:OrderingComponent ; rdfs:range qnt:ComponentDirection ;
    rdfs:comment "Whether an OrderingComponent sorts ascending or descending." .

qnt:unresolvedOrderPolicy a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:OrderingBasis ; rdfs:range qnt:UnresolvedOrderPolicy ;
    rdfs:comment "The policy applied when an occurrence's ordering value is unresolved." .

qnt:comparisonResult a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:Comparison ; rdfs:range qnt:TruthValue ;
    rdfs:comment "The truth value produced by a Comparison." .

qnt:unresolvedReason a owl:ObjectProperty ;
    rdfs:domain [ a owl:Class ; owl:unionOf ( qnt:Comparison qnt:UnresolvedValue ) ] ;
    rdfs:range qnt:UnresolvedReason ;
    rdfs:comment "A declared reason why a Comparison is indeterminate, or why an UnresolvedValue has no definite value." .

qnt:comparisonProfile a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:Comparison ; rdfs:range qnt:OperationalProfile ;
    rdfs:comment "The operational profile that produced a Comparison." .

qnt:requestedOperation a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:OperationRequest ; rdfs:range qnt:OperationKind ;
    rdfs:comment "The operation kind requested by an OperationRequest." .

qnt:requestedOnSpace a owl:ObjectProperty ;
    rdfs:domain qnt:OperationRequest ; rdfs:range qnt:ValueSpace ;
    rdfs:comment "A ValueSpace supplying an operand to a requested operation." .

qnt:lawRegister a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:Law ; rdfs:range qnt:LawRegister ;
    rdfs:comment "Which of the three evidence registers a Law belongs to." .

qnt:dischargesLaw a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:LawDischarge ; rdfs:range qnt:Law ;
    rdfs:comment "The Law a LawDischarge discharges." .

qnt:dischargedForImplementationProfile a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:LawDischarge ; rdfs:range qnt:OperationalProfile ;
    rdfs:comment "The implementation profile a LawDischarge was proved or tested against." .

qnt:formalArgumentReference a owl:ObjectProperty ;
    rdfs:domain qnt:SemanticLawDischarge ;
    rdfs:comment "A reference to the formal argument evidencing a SemanticLawDischarge." .

qnt:staticAnalysisMethod a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:StaticConstraintDischarge ;
    rdfs:comment "The static analysis method (SPARQL, SHACL, reasoner, or compiled analysis) that checked a StaticConstraintDischarge." .

qnt:executedTestRun a owl:ObjectProperty ;
    rdfs:domain qnt:RuntimeConformanceDischarge ;
    rdfs:comment "A reference to an executed test run evidencing a RuntimeConformanceDischarge." .

qnt:numeratorSpace a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:DerivedValueSpace ; rdfs:range qnt:ValueSpace ;
    rdfs:comment "The space a derived space's values are the numerator of." .

qnt:denominatorSpace a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:DerivedValueSpace ; rdfs:range qnt:ValueSpace ;
    rdfs:comment "The space a derived space's values are the denominator of." .

qnt:underCalendar a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:range voc:SchemeContract ;
    rdfs:comment "The scheme contract whose resolution, for the context's scope and time, gives the calendar a ConversionContext or Recurrence counts in (ADR-A94)." .

qnt:fromPosition a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain qnt:ConversionContext ; rdfs:range qnt:Value ;
    rdfs:comment "The position a calendar conversion counts from." .

qnt:alternativeBound a owl:ObjectProperty, owl:SymmetricProperty ;
    rdfs:domain qnt:Bound ; rdfs:range qnt:Bound ;
    rdfs:comment "Another statement of the same limit in a different unit, sharing the bound's space, sense and closure. A candidate is compared with the statement in its own unit, never through a conversion (ADR-A95)." .
```
## 8. Mechanism-Intrinsic Vocabulary

```turtle-vocab
@prefix qnt:  <https://www.nebularis.org/neuro-semantic/lattice/quantification#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

qnt:OrderKind a owl:Class ;
    rdfs:comment "A mechanism-intrinsic kind of ordering declared for a ValueSpace." .

qnt:TotalOrder a qnt:OrderKind ;
    rdfs:comment "An order in which every pair of values is comparable." .

qnt:CyclicOrder a qnt:OrderKind ;
    rdfs:comment "A repeating order with no globally meaningful lower-to-upper direction." .

qnt:NoOrder a qnt:OrderKind ;
    rdfs:comment "A declaration that a ValueSpace supports equality only and does not support ranges." .

qnt:DensityKind a owl:Class ;
    rdfs:comment "A mechanism-intrinsic declaration of what counts as adjacent in a ValueSpace." .

qnt:Discrete a qnt:DensityKind ;
    rdfs:comment "Adjacency is defined via the space's granularity floor." .

qnt:Dense a qnt:DensityKind ;
    rdfs:comment "Adjacency is defined only where closures abut without a gap." .

qnt:UnspecifiedDensity a qnt:DensityKind ;
    rdfs:comment "Adjacency is not defined; range-set merging uses overlap only." .

qnt:BoundSense a owl:Class ;
    rdfs:comment "A mechanism-intrinsic designation of a bound as lower or upper." .

qnt:Lower a qnt:BoundSense .
qnt:Upper a qnt:BoundSense .

qnt:Closure a owl:Class ;
    rdfs:comment "A mechanism-intrinsic designation of whether a range endpoint is included." .

qnt:Closed a qnt:Closure ;
    rdfs:comment "A bound whose endpoint is included." .

qnt:Open a qnt:Closure ;
    rdfs:comment "A bound whose endpoint is excluded." .

qnt:OffsetKind a owl:Class ;
    rdfs:comment "A mechanism-intrinsic kind of offset used by an AnchorBinding." .

qnt:Absolute a qnt:OffsetKind ;
    rdfs:comment "An offset expressed as an absolute quantity in the anchor's space." .

qnt:Proportional a qnt:OffsetKind ;
    rdfs:comment "An offset expressed as a proportion of the anchor value. Requires the space to declare Ratio capability." .

qnt:ConversionKind a owl:Class ;
    rdfs:comment "A mechanism-intrinsic kind of unit conversion." .

qnt:Exact a qnt:ConversionKind ;
    rdfs:comment "A definitional, lossless conversion." .

qnt:Defined a qnt:ConversionKind ;
    rdfs:comment "A conversion with a declared factor or registered function under the unit contract." .

qnt:Contextual a qnt:ConversionKind ;
    rdfs:comment "A conversion requiring an evidenced contextual observation." .

qnt:OperationKind a owl:Class ;
    rdfs:comment "A mechanism-intrinsic kind of operation over declared ValueSpaces." .

qnt:Compare a qnt:OperationKind .
qnt:Contains a qnt:OperationKind .
qnt:Overlaps a qnt:OperationKind .
qnt:Difference a qnt:OperationKind .
qnt:Sum a qnt:OperationKind .
qnt:Ratio a qnt:OperationKind .
qnt:Minimum a qnt:OperationKind .
qnt:Maximum a qnt:OperationKind .
qnt:Count a qnt:OperationKind .
qnt:Scale a qnt:OperationKind ;
    rdfs:comment "Scaling a value on a derived space's denominator space by a rate on the derived space, yielding a value on its numerator space (ADR-A93)." .
qnt:BinOf a qnt:OperationKind ;
    rdfs:comment "The operation returning the unique RecurrenceBin containing a given position, or Undetermined with a reason." .

qnt:RangeSemanticsKind a owl:Class ;
    rdfs:comment "A mechanism-intrinsic classification of a Contains or Overlaps capability's meet properties." .

qnt:ExactRangeSemantics a qnt:RangeSemanticsKind ;
    rdfs:comment "Satisfies both meet soundness (Q4a) and meet completeness (Q4b). Safe for meet-based enumeration." .

qnt:ScreeningRangeSemantics a qnt:RangeSemanticsKind ;
    rdfs:comment "Satisfies meet soundness (Q4a) only, not completeness. Must not be used for meet-based enumeration — screening and candidate generation only." .

qnt:TruthValue a owl:Class ;
    rdfs:comment "A three-valued result of a comparison." .

qnt:True a qnt:TruthValue .
qnt:False a qnt:TruthValue .
qnt:Undetermined a qnt:TruthValue .

qnt:UnresolvedReason a owl:Class ;
    rdfs:comment "A mechanism-intrinsic reason why a comparison cannot yield a definite result." .

qnt:ValueAbsent a qnt:UnresolvedReason .
qnt:ValueMarkedUnresolved a qnt:UnresolvedReason .
qnt:GranularityInsufficient a qnt:UnresolvedReason .
qnt:ConversionContextAbsent a qnt:UnresolvedReason .
qnt:OutsideDeclaredSpace a qnt:UnresolvedReason .
qnt:OperationNotPermitted a qnt:UnresolvedReason .
qnt:NoBoundInUnit a qnt:UnresolvedReason ;
    rdfs:comment "No statement of a bound, among it and its alternatives, is in the candidate's unit (ADR-A95)." .

qnt:BinContiguity a owl:Class ;
    rdfs:comment "A mechanism-intrinsic policy governing whether recurrence bins are contiguous." .

qnt:Contiguous a qnt:BinContiguity ;
    rdfs:comment "Successive bins share a boundary with no gap." .

qnt:GapPermitting a qnt:BinContiguity ;
    rdfs:comment "Successive bins may have a gap between them." .

qnt:BoundaryDerivation a owl:Class ;
    rdfs:comment "A mechanism-intrinsic policy governing how a recurrence bin boundary is derived when the anchor does not land on it cleanly." .

qnt:AnchorPreserving a qnt:BoundaryDerivation ;
    rdfs:comment "The anchor's position within the period is preserved where the boundary space permits it." .

qnt:PeriodEndAligned a qnt:BoundaryDerivation ;
    rdfs:comment "The boundary always aligns to the end of the period, regardless of the anchor's exact position." .

qnt:BinKeyStrategy a owl:Class ;
    rdfs:comment "A mechanism-intrinsic strategy for deriving stable recurrence-bin keys." .

qnt:AnchorAndOrdinal a qnt:BinKeyStrategy .
qnt:BoundaryPair a qnt:BinKeyStrategy .

qnt:ComponentDirection a owl:Class ;
    rdfs:comment "A mechanism-intrinsic sort direction for an OrderingComponent." .

qnt:Ascending a qnt:ComponentDirection .
qnt:Descending a qnt:ComponentDirection .

qnt:UnresolvedOrderPolicy a owl:Class ;
    rdfs:comment "A mechanism-intrinsic policy for ordering occurrences with unresolved order values." .

qnt:Defer a qnt:UnresolvedOrderPolicy .
qnt:PlaceLast a qnt:UnresolvedOrderPolicy .
qnt:Reject a qnt:UnresolvedOrderPolicy .

qnt:LawRegister a owl:Class ;
    rdfs:comment "A mechanism-intrinsic classification of what kind of evidence discharges a Law." .

qnt:SemanticLaw a qnt:LawRegister ;
    rdfs:comment "Discharged by formal argument and property tests." .

qnt:StaticConstraint a qnt:LawRegister ;
    rdfs:comment "Discharged by SPARQL, SHACL, reasoner, or compiled static analysis." .

qnt:RuntimeConformance a qnt:LawRegister ;
    rdfs:comment "Discharged only by an executed test run — no formal argument alone suffices." .
```

The substrate ships these mechanism values only. It ships no unit, unit family, currency, calendar, date convention, grade, priority, recurring period, or conversion observation.

**On the absent `PartialOrder` and `IncomparableValues`.** An earlier draft carried both alongside a stated intention to omit `PartialOrder` from the first release, while leaving `IncomparableValues` in the `UnresolvedReason` enumeration — meaning that reason had no order kind able to produce it: dead mechanism-intrinsic vocabulary. Both are omitted here together, to be reintroduced together only if a case arrives that Eligibility's scheme-subsumption mechanism genuinely cannot express — two poset mechanisms with no declared relationship between them is worse than a missing order kind.
## 9. Evaluation Semantics

### 9.1 Comparison outcomes

| Result | Meaning |
|---|---|
| `qnt:True` | The requested relation is established under the declared space and profile. |
| `qnt:False` | The requested relation is established not to hold. |
| `qnt:Undetermined` | Available information is insufficient to establish either result. |

`Undetermined` is not an error and not a coercion to false. It occurs where a required value is absent, explicitly unresolved, known only to insufficient granularity, dependent on an absent conversion context, outside the relevant declared space, or subject to an operation the ValueSpace doesn't permit.

### 9.2 Range containment

For a non-cyclic `Range`, a value is contained if it's in the same ValueSpace, not below the lower bound (respecting closure), not above the upper bound (respecting closure), and every required comparison is definite. Where a bound has `alternativeBound` statements, the value is compared with the statement in its own unit, with no conversion, and the comparison is `Undetermined` with `NoBoundInUnit` if none is in its unit (ADR-A95).

### 9.3 Cyclic range membership

For a `CyclicRange` with `cycleStart` *s*, `cycleExtent` *e*, on a space with `cycleLength` *L*: a position *p* is contained if, measuring forward from *s* around the cycle, the forward distance to *p* is less than *e* (or equal to *e* where `endClosure` is `Closed`), and *p* is not equal to *s* unless `startClosure` is `Closed`. Degenerate cases are stated once, in §6, rather than left for each implementation to work out: extent zero is a single point; extent equal to *L* is the whole cycle; extent exceeding *L* is a declaration error.

### 9.4 Range overlap

Two non-cyclic ranges overlap when their intersection is non-empty under the declared order and endpoint closures. Overlap is sound for screening — a reported overlap is a genuine non-empty pairwise intersection — but is not complete for meet-based enumeration: a value contained by neither of two ranges' meet may still be reported as a candidate by each range's overlap with a third, separately. A capability whose `rangeSemanticsKind` is `ScreeningRangeSemantics` must never be presented as exact co-admissibility; only `ExactRangeSemantics` may be. See §10, `Q4a`/`Q4b`/`Q5`.

### 9.5 Granularity

A value with declared granularity stands for a region around its represented point. A comparison requiring a distinction finer than that region returns `Undetermined` with `GranularityInsufficient` — a position known only to a month cannot definitely be classified as before or after a boundary inside that month.

### 9.6 Conversion

A comparison between values in distinct units is permitted only when both units are allowed by the relevant `UnitContract`; a declared `Conversion` relates them directly or through an allowed chain, with its transformation stated via `conversionFactor` or a registered `ConversionFunction` — never left undeclared; a `ConversionContext` is present where any step of that chain is `Contextual`; and the declared operational profile supports the required conversion path. An absent context produces `Undetermined`; it does not make the underlying values invalid RDF. A conversion from or to a `CalendarUnit` is always `Contextual`, and its context names the calendar's scheme contract (`underCalendar`) and the starting position (`fromPosition`) (ADR-A94).

### 9.7 Recurrence and `binOf`

A `Recurrence` maps an anchor and period onto a deterministic sequence of ranges. `binOf(recurrence, position)` returns the unique bin containing `position`, or `Undetermined` with a declared reason where the position is unresolved, coarser than the bin boundary, or outside `validRange`. Each generated bin's key is stable under recomputation for the same recurrence version, anchor, period, `binContiguity`, `boundaryDerivation`, `binKeyStrategy`, and calendar or external convention binding where one is declared — this stability is `Q9`, and it is runtime conformance, not something a formal argument alone establishes (§10).

### 9.8 Ordering

An `OrderingBasis` with a total sequence of `OrderingComponent`s produces the same order for the same input set and the same `unresolvedOrderPolicy`, independently of storage order or evaluation time — this is `Q11`, also runtime conformance, checked by actually running the ordering over a representative input set rather than by inspection.

---

## 10. Laws

Restructured into three registers, per §4's design decision — a discharge's evidence shape depends on which register its law belongs to.

### Semantic laws (`qnt:SemanticLaw`) — formal argument plus property tests

| ID | Law | Consequence if violated |
|---|---|---|
| **Q1** | Order coherence — every declared order kind has defined comparison semantics, with any indeterminate cases explicit. | Sorting, comparison, and membership disagree. |
| **Q2** | Bound coherence — open and closed endpoints behave consistently under containment and intersection, including for cyclic ranges (`startClosure`/`endClosure`). | Point and range evaluations disagree. |
| **Q4a** | Containment meet soundness — a value contained by the meet of two ranges is contained by both. | Required of every range semantics. |
| **Q4b** | Containment meet completeness — a value contained by both ranges is contained by their meet. | Satisfied by `ExactRangeSemantics`, not `ScreeningRangeSemantics`. |
| **Q5** | Overlap is screening-only — overlap satisfies Q4a and not Q4b; a semantics satisfying only Q4a is `ScreeningRangeSemantics` and must not participate in meet-based enumeration. | Candidate generation is misrepresented as truth. |
| **Q6** | Conversion coherence — exact and defined conversions preserve comparison semantics; contextual conversions preserve them only within the recorded context. Not a Gate-6 prerequisite — needed for the layer's own correctness, not to unblock an upper-layer construct. | Cross-unit comparisons become silently wrong. |
| **Q8** | Zero-bounded closure — a space declaring a zero lower bound and truncated subtraction remains non-negative under permitted depletion operations. | Capacity and balance models can become negative. |

### Static declaration constraints (`qnt:StaticConstraint`) — SPARQL, SHACL, reasoner, or compiled analysis

| ID | Constraint |
|---|---|
| **Q7** | Operation admissibility — an operation is evaluated only where a matching capability signature exists (= governance obligation 2). |
| — | Governance obligations 1, 3, 4, 5, 7, 8, 12 (§11) — checkable from the declaration alone. |
| — | Period-space compatibility — a Recurrence's period is on an extent space compatible with its anchor's position space (§6). |

### Runtime conformance (`qnt:RuntimeConformance`) — executed test runs against a named implementation profile

| ID | Claim |
|---|---|
| **Q3** | Range-set canonical form — regenerating a range set's normal form from the same input twice produces the same result. Conditional on `densityKind` (§4, §6): discrete spaces canonicalise via `granularityFloor`; dense spaces via closure-abutment; `UnspecifiedDensity` spaces never merge on adjacency. |
| **Q9** | Recurrence determinism — independent recomputation of the same declaration and inputs produces identical bin keys. |
| **Q10** | Unresolved non-coercion — every indeterminate path (insufficient granularity, unresolved value, missing conversion context, incomparability) produces the declared reason, never a definite result invented to fill the gap. |
| **Q11** | Ordering determinism — an OrderingBasis with a total component sequence produces the same order for the same input set and unresolved-order policy, independently of storage order or evaluation time. |

### Gate prerequisites

Corrected mapping — an earlier draft understated this and named the wrong subset:

| Upper-layer need | Quantification law |
|---|---|
| Eligibility interval canonicalisation | **Q3** |
| Eligibility declared-indeterminate conditions for range strategies | **Q10** |
| Eligibility overlap reinstatement as a screening strategy | **Q4a / Q4b / Q5**, via `participatesInMeet` |
| Behaviour monotone, non-negative depletion | **Q8** |
| Behaviour absorption conservation | **Q8 + Q7** |
| Behaviour reset bins, keyed account identity | **Q9** |
| Behaviour emission queue ordering, same-timestamp collisions | **Q11** |

`Q6` (conversion coherence) is not a prerequisite for any of the above — it is needed for the layer's own internal correctness wherever conversion is used, not to unblock a specific upper-layer construct.

---

## 11. Governance Obligations

Checked over the relevant union graph and stated operational profile. They do not prevent ingestion of incomplete data; they determine whether declarations and evaluations are valid for a stated use.

| ID | Obligation |
|---|---|
| 1 | Every ValueSpace declares a key, order kind, density kind, and semantic hash. |
| 2 | Every requested operation has a matching OperationCapability signature. |
| 3 | A `NoOrder` ValueSpace carries no Range; a `CyclicOrder` ValueSpace carries CyclicRanges, never ordinary lower/upper Ranges, and declares a `cycleLength`. |
| 4 | Every Bound declares one sense and one closure; every CyclicRange declares both a startClosure and an endClosure; every Range has at most one lower and one upper bound; all range endpoints are on the Range's ValueSpace. |
| 5 | A ValueSpace whose UnitContract requires units has a canonical unit and every resolved Quantity carries a permitted unit. |
| 6 | A contextual conversion used by an operational comparison has an evidenced ConversionContext. |
| 7 | Every Recurrence declares anchor, period, binContiguity, boundaryDerivation, and binKeyStrategy; its period's space is extent-compatible with its anchor's position space. |
| 8 | Every OrderingBasis declares at least one OrderingComponent and its unresolved-order policy. |
| 9 | Every persisted Comparison records its producing operational profile and any unresolved reason. |
| 10 | Every in-use mechanism construct has evidence discharging its applicable laws, of the evidence type its law register requires. |
| 11 | Every persisted derived representation traces to source declarations, graph inputs, producing profile, and a declared authority level (advisory, cached-reproducible, operationally authoritative, or externally authoritative-and-synchronised). |
| 12 | Changing order kind, density kind, operation capability, canonical unit, recurrence anchor, period, binContiguity, boundaryDerivation, or bin-key strategy requires a major declaration version. |

**Conformance floor.** Direct SPARQL and SHACL validation are the mandatory baseline profiles; every other operational profile (reasoning, materialisation, projection, compiled evaluation) is per-deployment and must agree with the baseline over the shared conformance corpus (§13) where supported.

**Conformance levels.** Quantification states have a place on the same eight-level ladder used elsewhere in the substrate:

| Level | Quantification state |
|---|---|
| L0 | Values present with source provenance; no ValueSpace assigned. |
| L1 | Mapping hypotheses relating source measures to candidate spaces. |
| L2 | Values typed as Value/Quantity/OrdinalValue; space possibly unresolved. |
| L3 | ValueSpace, UnitContract, OperationCapability, and Recurrence declarations satisfy authoring shapes. |
| L4 | Suitable for stated SPARQL, reasoning, or materialisation profiles. |
| L5 | Operation has a matching capability; required values resolved or explicitly unresolved; conversion context present where contextual. |
| L6 | *Not applicable — Quantification produces comparisons, never executions.* |
| L7 | Materialised bins, normal forms, or projections consistent with declared contract. |

```turtle-shapes
@prefix qnt: <https://www.nebularis.org/neuro-semantic/lattice/quantification#> .
@prefix sh:  <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

qnt:RangeShape
    a sh:NodeShape ;
    sh:targetClass qnt:Range ;
    sh:property [ sh:path qnt:onSpace ; sh:minCount 1 ; sh:maxCount 1 ; sh:class qnt:ValueSpace ] ;
    sh:property [ sh:path qnt:lowerBound ; sh:maxCount 1 ; sh:class qnt:Bound ] ;
    sh:property [ sh:path qnt:upperBound ; sh:maxCount 1 ; sh:class qnt:Bound ] .

qnt:CyclicRangeShape
    a sh:NodeShape ;
    sh:targetClass qnt:CyclicRange ;
    sh:property [ sh:path qnt:cycleStart ; sh:minCount 1 ; sh:maxCount 1 ] ;
    sh:property [ sh:path qnt:cycleExtent ; sh:minCount 1 ; sh:maxCount 1 ] ;
    sh:property [ sh:path qnt:startClosure ; sh:minCount 1 ; sh:maxCount 1 ] ;
    sh:property [ sh:path qnt:endClosure ; sh:minCount 1 ; sh:maxCount 1 ] .

qnt:RecurrenceShape
    a sh:NodeShape ;
    sh:targetClass qnt:Recurrence ;
    sh:property [ sh:path qnt:anchor ; sh:minCount 1 ; sh:maxCount 1 ] ;
    sh:property [ sh:path qnt:period ; sh:minCount 1 ; sh:maxCount 1 ; sh:class qnt:Quantity ] ;
    sh:property [ sh:path qnt:binContiguity ; sh:minCount 1 ; sh:maxCount 1 ] ;
    sh:property [ sh:path qnt:boundaryDerivation ; sh:minCount 1 ; sh:maxCount 1 ] ;
    sh:property [ sh:path qnt:binKeyStrategy ; sh:minCount 1 ; sh:maxCount 1 ] .

qnt:OperationCapabilityMeetShape
    a sh:NodeShape ;
    sh:targetClass qnt:OperationCapability ;
    sh:sparql [
        sh:message "A Contains or Overlaps capability must declare rangeSemanticsKind and participatesInMeet." ;
        sh:select """
            SELECT $this WHERE {
                $this qnt:operationKind ?k .
                FILTER (?k IN (qnt:Contains, qnt:Overlaps))
                FILTER NOT EXISTS { $this qnt:rangeSemanticsKind ?rsk }
            }
        """
    ] .

qnt:DerivedValueSpaceShape
    a sh:NodeShape ;
    sh:targetClass qnt:DerivedValueSpace ;
    sh:property [ sh:path qnt:numeratorSpace ; sh:minCount 1 ; sh:maxCount 1 ; sh:class qnt:ValueSpace ] ;
    sh:property [ sh:path qnt:denominatorSpace ; sh:minCount 1 ; sh:maxCount 1 ; sh:class qnt:ValueSpace ] .

qnt:CalendarConversionShape
    a sh:NodeShape ;
    sh:targetClass qnt:Conversion ;
    sh:sparql [
        sh:message "A conversion from or to a calendar unit must be Contextual (ADR-A94)." ;
        sh:select """
            PREFIX qnt: <https://www.nebularis.org/neuro-semantic/lattice/quantification#>
            SELECT $this WHERE {
                { $this qnt:fromUnit ?unit } UNION { $this qnt:toUnit ?unit }
                ?unit a qnt:CalendarUnit .
                FILTER NOT EXISTS { $this qnt:conversionKind qnt:Contextual }
            }
        """
    ] .

qnt:AlternativeBoundShape
    a sh:NodeShape ;
    sh:targetClass qnt:Bound ;
    sh:sparql [
        sh:message "Alternative bounds must share space, sense and closure, and state the limit in different units (ADR-A95)." ;
        sh:select """
            PREFIX qnt: <https://www.nebularis.org/neuro-semantic/lattice/quantification#>
            SELECT $this WHERE {
                { $this qnt:alternativeBound ?other } UNION { ?other qnt:alternativeBound $this }
                FILTER (?other != $this)
                FILTER (
                    NOT EXISTS { $this qnt:onSpace ?s . ?other qnt:onSpace ?s }
                    || NOT EXISTS { $this qnt:boundSense ?d . ?other qnt:boundSense ?d }
                    || NOT EXISTS { $this qnt:boundClosure ?c . ?other qnt:boundClosure ?c }
                    || EXISTS { $this qnt:boundValue/qnt:inUnit ?u . ?other qnt:boundValue/qnt:inUnit ?u }
                )
            }
        """
    ] .
```

Substrate shapes are `qnt:`-named, as above; deployment shapes illustrating them (§14) are `ex:`-named — the two are never conflated in this document.
## 12. Relationship to Other Layers

### Foundation

Quantification uses `fnd:Version` for declarations whose meaning changes over time, `fnd:Governable` for declarations needing review before operational use, `fnd:Evidenced` for unresolved values, conversion contexts, comparisons, conversion functions, and law discharges, and `fnd:TemporallyScoped` for conversion contexts.

**Foundation provides** `fnd:DerivedArtefact`, `fnd:DerivationRun` and `fnd:DerivationKind` since ADR-A92, which this document's derived records (`RecurrenceBin`, materialised range sets, projection records) can subclass. A content-hash contract is not part of it: Surface's read-set hashes remain the only implemented one. Foundation also needs ordered-collection support or an equivalent canonical-ordering convention, and temporal scoping capable of representing a position known only to a declared granularity.

### Vocabulary

Quantification uses `voc:SchemeContract` where a deployment binds an ordinal or other concept-based ValueSpace to a governed scheme. Vocabulary remains responsible for scheme governance; Quantification declares how a scheme-backed space is ordered and which operations it permits, never populating the scheme itself.

### Eligibility

Eligibility may consume `qnt:Range` and `qnt:RangeSet` for containment strategies, `qnt:Comparison` results including `Undetermined`, range canonicalisation for interval-strategy normal forms, and `participatesInMeet` to know directly whether a given overlap capability is safe for meet-based enumeration without re-deriving it.

### Behaviour

Behaviour may consume zero-bounded quantity spaces for non-negative depletion, `Minimum`/`Difference`/`Sum` capabilities, `RecurrenceBin`s as reset bins, `OrderingBasis` for deterministic queue and same-position ordering, comparison outcomes in condition-trigger evaluation, and `qnt:ConversionFunction` as the shared registry its own `ValueFunction` mechanism should reuse rather than duplicate.

### Instrument

Instrument may consume Quantification values and ranges for declared qualifiers — windows, tolerances, deadlines, capacities. Quantification does not prescribe the Instrument-level meaning of any such qualifier.

---

## 13. Open Questions

1. **External unit alignment.** The layer should support deployment bindings to QUDT, OM, or another vocabulary, without importing one by default.
2. ~~**Calendar binding.**~~ Resolved by [ADR-A94](../../docs/architecture/decisions/ADR-A94-quantification-calendar-binding.md): calendar units, contextual conversion, and calendars resolved as concept scheme editions.
3. **Contextual conversion observations.** The precise RDF shape for an external conversion observation should be designed alongside the first implementation profile, preserving the rule that a context is required for `Contextual` conversion.
4. ~~**Derived rate spaces.**~~ Resolved by [ADR-A93](../../docs/architecture/decisions/ADR-A93-quantification-derived-rate-spaces.md): `qnt:DerivedValueSpace` and the `Scale` operation.
5. **Precision and rounding policy vocabulary.** `precisionPolicy` and `roundingPolicy` (§7) exist as properties but have no declared vocabulary of values yet — `rdfs:Literal`-valued for the first release, with a closed vocabulary to follow once a real implementation profile needs to interpret them rather than merely record them.

**Resolved, not reopened:** partial orders (omitted, §8); the L5a/L5b-equivalent classification for containment versus overlap (§9, `Q4a`/`Q4b`/`Q5`); cyclic range endpoint closure (§6); ordering tie-breakers (§6, `OrderingComponent`); range-set adjacency (§6, `densityKind`); the Gate prerequisite mapping (§10).

---

## 14. Acceptance Criteria

Quantification is ready for use by Eligibility and Behaviour only when:

- no unit, currency, calendar, scale, grade, or recurrence inventory ships in the substrate;
- a ValueSpace can be queried and validated directly without a generated surface;
- a ValueSpace declares its order, density, and permitted operations;
- a range can express open, closed, half-bounded, anchored, and cyclic forms correctly, with cyclic endpoints as fully closed/open as any other bound;
- a known-but-coarse value is distinguishable from an unresolved value;
- insufficient precision yields an evidenced `Undetermined` result;
- contextual conversion cannot silently proceed without its context, and every conversion's actual transformation is declared, not left implicit;
- overlap-based and containment-based range semantics are distinguishable via `rangeSemanticsKind`, and only `ExactRangeSemantics` is used for meet-based enumeration;
- range normalisation and recurrence bin identity are canonical and testable, conditional on declared density kind;
- a direct SPARQL profile and a SHACL validation profile both pass the shared Quantification conformance corpus, as the mandatory floor;
- any materialised, projected, or compiled representation records its source declarations, producing profile, invalidation dependencies, and authority level;
- `Q3`, `Q8`, `Q9`, `Q10`, and `Q11` — the actual Gate prerequisites (§10) — have recorded discharges of the evidence type their register requires, before Eligibility interval strategies or Behaviour extent and ordering semantics rely on them.

---

## 15. Authoring Procedure

This layer is unauthored as Turtle. Before it becomes normative:

1. Publish the generic premise and the two-premise temporal collapse (§1, §4) as a public ADR, citing only public sources on measurement, order theory, interval semantics, SKOS, SHACL, RDF, and provenance — not any closed internal estate. The name `Quantification` must be coined from this public premise directly, not arrive via a closed renaming table, for the same reason applied elsewhere in the substrate to avoid a derivation fingerprint with no corresponding benefit.
2. Author at least two non-domain-inventory examples per newly introduced construct as loadable RDF graphs, before generalising any mechanism further — three for constructs an upper layer is actually blocked on.
3. Follow the two-role clean-room procedure established elsewhere in the substrate: a public author who reads only public sources and public design documents, and a closed reviewer restricted to sufficiency verdicts, never proposed wording, notation, structure, or example order. Quantification is unauthored, so the public author can genuinely be first here — cheap now, not available once any closed-estate wording exists.
4. Implement a direct SPARQL reference profile before any materialisation or compiled evaluator.
5. Implement declaration and operational SHACL profiles separately; invalid operational data must remain ingestible for mapping and remediation.
6. Build one shared conformance corpus — Quantification's is the easiest of the substrate's to build and should come first, since Eligibility and Behaviour both consume its results — against which direct SPARQL, SHACL, materialised, projected, and compiled profiles can all be tested.
7. Keep units, calendars, scheme populations, conversion observations, and deployment-specific arithmetic outside the substrate throughout.

> Declare how values are ordered, bounded, converted, and operated on; retain those declarations and values as directly usable graph data; derive, materialise, project, or compile only where a stated operational need justifies it.

---

## 16. Revision Summary

What changed from the earlier draft, and why — kept here rather than only in an external review, so the reasoning travels with the specification.

| Area | Change | Reason |
|---|---|---|
| Order kinds | `PartialOrder` and `IncomparableValues` removed together | Neither had a supported producer; dead vocabulary otherwise (B1) |
| Evaluation classes | `OperationalProfile`, `OperationRequest`, `Law`, `LawDischarge` defined | Previously referenced, never defined; would parse but not reason usefully (B2) |
| Laws | Split into three registers with distinct discharge subclasses | One register conflated formal proof, static checking, and runtime testing (B3) |
| Containment vs overlap | Restated as `Q4a`/`Q4b`/`Q5`; `participatesInMeet` added | The counterexample needed a formal home Eligibility could cite rather than restate (B4) |
| Cyclic ranges | `startClosure`/`endClosure` added; `cycleLength` added to ValueSpace; degenerate cases stated | Containment was undefined for the only range form a cyclic space carries (B5) |
| Conversion | `ConversionFunction` registry added | `fromUnit`/`toUnit` declared that a conversion exists, never how (S1) |
| Ranges | `AnchorBinding` restored | A tolerance's derivation from a nominal value was lost once only bounds were kept (S2) |
| Ordering | `OrderingComponent` added, with direction | Tie-breaking had no mechanism, despite being the construct's whole purpose (S3) |
| Value spaces | `densityKind` and `granularityFloor` added | Canonical form depended on an explicitly undefined notion of adjacency (S4) |
| Recurrence | `binContiguity`/`boundaryDerivation` split; `binOf` defined; `validRange` added | One `alignmentPolicy` covered two unrelated axes; the operation upper layers depend on was undefined (S5) |
| Quantity | `numericValue` widened to `rdfs:Literal`; `valueDatatype` added | Fixed to `xsd:decimal`, a temporal position could not use this class at all (S6) |
| Laws | Gate prerequisite table corrected; `Q11` (ordering determinism) added | The stated prerequisites didn't match what upper layers actually depend on, and ordering had no law at all (S7) |
| Governance | Conformance-level table, mandatory-profile statement, and derivation-authority obligation added | Required by the substrate's own conformance and provenance conventions, previously absent (P1, P3, P5) |
| Procedure | Clean-room authoring referenced explicitly | An earlier, weaker procedure restated rather than deferred to the established one (P4) |
