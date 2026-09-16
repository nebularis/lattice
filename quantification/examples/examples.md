<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Quantification Ontology — Worked Examples

*Companion to `quantification/spec/quantification.md`. Illustrative, not normative.*

All examples use the `ex:` namespace. No example contributes a unit, currency, calendar, scale, recurrence, or domain vocabulary to the Quantification substrate. Wherever an example needs to reference a construct belonging to Party, Instrument, Eligibility, or Behaviour, it uses an `ex:`-prefixed term rather than that layer's own namespace, since Quantification's own specification never references those layers — see the standing note at the head of Part XIII, which applies throughout, not only there.

---

## 1. How to read these examples

Same operational strategies as described in `quantification.md` §1 and §5: direct SPARQL, SHACL, RDFS/OWL/SKOS reasoning, RDF materialisation, external projection, or generated code, none of them a universal requirement. The graph remains the semantic source throughout.

Fence convention, matching the README exactly: everything in this document illustrating substrate usage is `turtle-example`. Nothing here is extracted into `spec/quantification.ttl`, `vocab/quantification-vocab.ttl`, or `shapes/constraints.ttl` — those come from the README alone. Where a snippet shows a *substrate* shape for reference, it uses the `qnt:` namespace exactly as `quantification.md` §11 declares it; every shape actually authored in this document, as a deployment would author one, uses `ex:` — the two are never conflated here, correcting an earlier draft that used `ex:` for both.

## 2. Shared prefixes

```turtle-example
@prefix ex:   <https://example.org/quantification/> .
@prefix qnt:  <https://www.nebularis.org/neuro-semantic/lattice/quantification#> .
@prefix fnd:  <https://www.nebularis.org/neuro-semantic/lattice/foundation#> .
@prefix voc:  <https://www.nebularis.org/neuro-semantic/lattice/vocabulary#> .
@prefix sh:   <http://www.w3.org/ns/shacl#> .
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
```

---

# Part I — Numeric quantities, bounds, and ranges

## 3. Declaring a mass space

```turtle-example
ex:mass-space
    a qnt:ValueSpace ;
    qnt:spaceKey "mass" ;
    qnt:orderKind qnt:TotalOrder ;
    qnt:densityKind qnt:Dense ;
    qnt:spaceHash "example:mass-space:v1" ;
    qnt:unitContract ex:mass-unit-contract ;
    qnt:hasOperationCapability
        ex:mass-compare , ex:mass-contains , ex:mass-difference ,
        ex:mass-sum , ex:mass-minimum , ex:mass-maximum , ex:mass-ratio .

ex:mass-unit-contract
    a qnt:UnitContract ;
    qnt:requiresUnit true ;
    qnt:unitFamily ex:mass-family ;
    qnt:canonicalUnit ex:mass-base-unit .

ex:mass-family a qnt:UnitFamily .
ex:mass-base-unit a qnt:Unit .

# Compare, Contains, and Overlaps never declare a resultSpace — they
# produce a qnt:Comparison. resultSpace applies only to value-producing
# operations (Difference, Sum, Ratio, Minimum, Maximum).
ex:mass-compare a qnt:OperationCapability ; qnt:operationKind qnt:Compare .
ex:mass-contains a qnt:OperationCapability ; qnt:operationKind qnt:Contains ;
    qnt:rangeSemanticsKind qnt:ExactRangeSemantics ;
    qnt:participatesInMeet true .

ex:mass-difference a qnt:OperationCapability ; qnt:operationKind qnt:Difference ; qnt:resultSpace ex:mass-space .
ex:mass-sum a qnt:OperationCapability ; qnt:operationKind qnt:Sum ; qnt:resultSpace ex:mass-space .
ex:mass-minimum a qnt:OperationCapability ; qnt:operationKind qnt:Minimum ; qnt:resultSpace ex:mass-space .
ex:mass-maximum a qnt:OperationCapability ; qnt:operationKind qnt:Maximum ; qnt:resultSpace ex:mass-space .
ex:mass-ratio a qnt:OperationCapability ; qnt:operationKind qnt:Ratio ; qnt:resultSpace ex:ratio-space .
```

### 3.1 Asserting values

```turtle-example
ex:shipment-mass a qnt:Quantity ; qnt:onSpace ex:mass-space ;
    qnt:numericValue "18450"^^xsd:decimal ; qnt:inUnit ex:mass-base-unit .

ex:vehicle-capacity a qnt:Quantity ; qnt:onSpace ex:mass-space ;
    qnt:numericValue "24000"^^xsd:decimal ; qnt:inUnit ex:mass-base-unit .
```

---

## 4. Half-bounded ranges, both directions

### 4.1 Upper only — a capacity

```turtle-example
ex:permitted-load a qnt:Range ; qnt:onSpace ex:mass-space ;
    qnt:upperBound ex:permitted-load-upper-bound .

ex:permitted-load-upper-bound a qnt:Bound ; qnt:onSpace ex:mass-space ;
    qnt:boundSense qnt:Upper ; qnt:boundClosure qnt:Closed ;
    qnt:boundValue ex:vehicle-capacity .
```

### 4.2 Lower only — "18 or over"

An earlier draft of this document only ever showed the upper-bounded case; the canonical half-bounded example — an open-ended eligibility floor with no ceiling — was absent.

```turtle-example
ex:adult-age-space
    a qnt:ValueSpace ;
    qnt:spaceKey "age-years" ;
    qnt:orderKind qnt:TotalOrder ;
    qnt:densityKind qnt:Discrete ;
    qnt:granularityFloor ex:one-year ;
    qnt:spaceHash "example:age-years-space:v1" ;
    qnt:hasOperationCapability ex:age-compare , ex:age-contains .

ex:age-contains a qnt:OperationCapability ; qnt:operationKind qnt:Contains ;
    qnt:rangeSemanticsKind qnt:ExactRangeSemantics ; qnt:participatesInMeet true .

ex:adult-or-over a qnt:Range ; qnt:onSpace ex:adult-age-space ;
    qnt:lowerBound ex:adult-lower-bound .

ex:adult-lower-bound a qnt:Bound ; qnt:onSpace ex:adult-age-space ;
    qnt:boundSense qnt:Lower ; qnt:boundClosure qnt:Closed ;
    qnt:boundValue ex:eighteen-years .
```

The range has no upper bound and needs none — `qnt:Range`'s `upperBound` is `maxCardinality 1`, not `minCardinality 1`, precisely so this case doesn't need a sentinel.

---

## 5. Anchored tolerance

An earlier draft dropped `AnchorBinding` and expressed a tolerance as two independently-authored bounds, losing the relationship between them entirely — nothing in that version's graph said the bounds were ±2% of a nominal value rather than a hand-authored band. Restored here.

```turtle-example
ex:nominal-mass a qnt:Quantity ; qnt:onSpace ex:mass-space ;
    qnt:numericValue "18000"^^xsd:decimal ; qnt:inUnit ex:mass-base-unit .

ex:mass-tolerance
    a qnt:AnchorBinding ;
    qnt:anchorValue ex:nominal-mass ;
    qnt:offsetKind qnt:Proportional ;
    qnt:lowerOffset "0.02"^^xsd:decimal ;
    qnt:upperOffset "0.02"^^xsd:decimal .

ex:accepted-mass-range
    a qnt:Range ;
    qnt:onSpace ex:mass-space ;
    qnt:relativeToAnchor ex:mass-tolerance .
```

Widening the tolerance to ±3% is now a change to `ex:mass-tolerance`'s two offsets, not a rewrite of two computed bounds — the relationship is reconstructable at any point, whether or not a deployment also materialises the resulting endpoints for direct querying. `Proportional` is valid here because `ex:mass-ratio` (§3) declares `Ratio` capability on `ex:mass-space`; a proportional offset on a space without it would be a declaration error.

---

# Part II — Units and conversion

## 6. Unit families and a registered conversion function

```turtle-example
ex:mass-alternate-unit a qnt:Unit ; rdfs:label "deployment alternate mass unit" .

ex:mass-linear-conversion
    a qnt:Conversion ;
    qnt:fromUnit ex:mass-alternate-unit ;
    qnt:toUnit ex:mass-base-unit ;
    qnt:conversionKind qnt:Defined ;
    qnt:conversionFactor "0.001"^^xsd:decimal .
```

A linear factor covers the common case. For anything non-linear, register a function once and reference it — this is the shared mechanism Behaviour's own `ValueFunction` registry is expected to reuse rather than duplicate:

```turtle-example
ex:temperature-offset-function
    a qnt:ConversionFunction ;
    rdfs:label "linear-offset transform, registered deterministic" ;
    fnd:hasEvidence ex:temperature-offset-conformance .

ex:temperature-offset-conformance
    a fnd:Evidence ;
    fnd:supports ex:temperature-offset-function ;
    fnd:recordedAt "2026-01-10T00:00:00Z"^^xsd:dateTime ;
    fnd:assertedBy ex:conformance-test-suite .

ex:temperature-conversion
    a qnt:Conversion ;
    qnt:fromUnit ex:celsius-unit ;
    qnt:toUnit ex:fahrenheit-unit ;
    qnt:conversionKind qnt:Defined ;
    qnt:conversionFunction ex:temperature-offset-function .
```

A `Conversion` never declares only `fromUnit`/`toUnit` and nothing about how — every `Defined` or `Contextual` conversion in this document sets either `conversionFactor` or `conversionFunction`.

## 7. Contextual conversion, and when context is actually required

A context is required for `Contextual` conversion. It is not required for `Defined` — an earlier draft's example used one anyway and then hedged in prose about whether that was correct. Stated plainly here: attach a context to a `Defined` conversion only where recording that specific conversion's provenance matters; never omit one from a `Contextual` conversion.

```turtle-example
ex:indexed-tariff-conversion
    a qnt:Conversion ;
    qnt:fromUnit ex:nominal-tariff-unit ;
    qnt:toUnit ex:indexed-tariff-unit ;
    qnt:conversionKind qnt:Contextual .

ex:march-2026-index-context
    a qnt:ConversionContext ;
    fnd:hasEvidence ex:published-index-observation ;
    fnd:hasTemporalScope [ fnd:validFrom "2026-03-01T00:00:00Z"^^xsd:dateTime ] .

ex:published-index-observation
    a fnd:Evidence ;
    fnd:supports ex:march-2026-index-context ;
    fnd:recordedAt "2026-03-02T09:00:00Z"^^xsd:dateTime ;
    fnd:assertedBy ex:published-index-series .
```

Comparing two months' indexed charges without a context is not silently approximate — it is `Undetermined` with `ConversionContextAbsent`, a load-time-visible fact rather than a misleading number.

---

# Part III — Granularity and unresolved values

## 8. A known-but-coarse value

```turtle-example
ex:approximate-delivery-date
    a qnt:Quantity ;
    qnt:onSpace ex:delivery-date-space ;
    qnt:numericValue "2026-03-01T00:00:00Z"^^xsd:dateTime ;
    qnt:knownToGranularity ex:one-month-granularity .
```

A comparison asking whether this falls before a boundary inside March returns `Undetermined` with `GranularityInsufficient` — the value is known, just not known finely enough for that particular question.

## 9. An explicitly unresolved value

```turtle-example
ex:disputed-mass
    a qnt:UnresolvedValue ;
    qnt:onSpace ex:mass-space ;
    qnt:unresolvedReason qnt:ValueMarkedUnresolved ;
    fnd:hasEvidence ex:dispute-record .

ex:dispute-record a fnd:Evidence ;
    fnd:supports ex:disputed-mass ;
    fnd:recordedAt "2026-04-02T00:00:00Z"^^xsd:dateTime ;
    fnd:assertedBy ex:receiving-depot .
```

Distinct from §8: this value is not coarse, it is absent pending resolution — different provenance, different remediation (resolve the dispute, rather than accept the coarseness and adjust the comparison).

---

# Part IV — Ordinal values

## 10. Ordered grades, kept distinct from their backing concepts

An earlier draft conflated the `OrdinalValue` individual with the `skos:Concept` it points at, asserting one IRI as both. Kept separate here, since they are two different kinds of thing under §6's disjointness.

```turtle-example
ex:grade-space
    a qnt:ValueSpace ;
    qnt:spaceKey "grade" ;
    qnt:orderKind qnt:TotalOrder ;
    qnt:densityKind qnt:Discrete ;
    qnt:spaceHash "example:grade-space:v1" ;
    qnt:hasOperationCapability ex:grade-compare , ex:grade-minimum , ex:grade-maximum , ex:grade-count .

ex:grade-compare a qnt:OperationCapability ; qnt:operationKind qnt:Compare .
ex:grade-minimum a qnt:OperationCapability ; qnt:operationKind qnt:Minimum ; qnt:resultSpace ex:grade-space .
ex:grade-maximum a qnt:OperationCapability ; qnt:operationKind qnt:Maximum ; qnt:resultSpace ex:grade-space .
ex:grade-count a qnt:OperationCapability ; qnt:operationKind qnt:Count .
# No Sum or Ratio capability is declared — deliberately: an average grade
# has no matching capability and must not be manufactured.

ex:grade-two-value a qnt:OrdinalValue ; qnt:onSpace ex:grade-space ; qnt:ordinalConcept ex:grade-two .
ex:grade-four-value a qnt:OrdinalValue ; qnt:onSpace ex:grade-space ; qnt:ordinalConcept ex:grade-four .

# The backing concepts belong to a governed scheme (Vocabulary's concern):
ex:grade-two a skos:Concept ; skos:prefLabel "Grade 2"@en .
ex:grade-four a skos:Concept ; skos:prefLabel "Grade 4"@en .

ex:grade-window
    a qnt:Range ;
    qnt:onSpace ex:grade-space ;
    qnt:lowerBound [ a qnt:Bound ; qnt:onSpace ex:grade-space ; qnt:boundSense qnt:Lower ; qnt:boundClosure qnt:Closed ; qnt:boundValue ex:grade-two-value ] ;
    qnt:upperBound [ a qnt:Bound ; qnt:onSpace ex:grade-space ; qnt:boundSense qnt:Upper ; qnt:boundClosure qnt:Closed ; qnt:boundValue ex:grade-four-value ] .
```

A request to average these grades has no matching `OperationCapability` and returns `OperationNotPermitted` — see Part XIV for the request itself, recorded rather than silently rejected.

---

# Part V — Cyclic ranges

## 11. A wrapping window, with declared endpoint closure

An earlier draft's cyclic range had no closure properties at all, despite an ordinary `Bound` requiring one. Fixed here — `startClosure` and `endClosure` are both cardinality-1 on `CyclicRange`.

```turtle-example
ex:daily-cycle
    a qnt:ValueSpace ;
    qnt:spaceKey "daily-cycle" ;
    qnt:orderKind qnt:CyclicOrder ;
    qnt:densityKind qnt:Dense ;
    qnt:cycleLength ex:twenty-four-hours ;
    qnt:spaceHash "example:daily-cycle-space:v1" .

ex:off-peak-window
    a qnt:CyclicRange ;
    qnt:onSpace ex:daily-cycle ;
    qnt:cycleStart ex:late-evening ;
    qnt:cycleExtent ex:eight-hour-extent ;
    qnt:startClosure qnt:Closed ;
    qnt:endClosure qnt:Open .
```

Membership follows §9.3 of the README precisely rather than being asserted by a table with no stated rule: measuring forward from 22:00, any position with forward distance less than 8 hours is contained, 22:00 itself is contained (`startClosure Closed`), and 06:00 is not (`endClosure Open`) — the same closed/open semantics an ordinary `Bound` would apply, just measured around a cycle instead of along a line.

A second, unrelated cyclic space — a season crossing a year boundary — is the identical mechanism on a different declared space, not a new construct.

---

# Part VI — Recurrence

## 12. A monthly recurrence, with the two alignment axes separated

An earlier draft's single `alignmentPolicy` conflated whether bins may have gaps with how a boundary is derived when an anchor doesn't land cleanly — the sketch's own motivating case, a month-end anchor in a short month, needed the second axis specifically and none of the three flattened values addressed it. Split here.

```turtle-example
ex:monthly-recurrence
    a qnt:Recurrence ;
    qnt:anchor ex:initial-position ;
    qnt:period ex:one-month-extent ;
    qnt:binContiguity qnt:Contiguous ;
    qnt:boundaryDerivation qnt:AnchorPreserving ;
    qnt:binKeyStrategy qnt:BoundaryPair ;
    qnt:validRange ex:recurrence-valid-range .
```

`qnt:AnchorPreserving` states that where the anchor's day-of-month exists in a given month, the boundary falls there; `qnt:PeriodEndAligned` (not used here) would instead always snap the boundary to the period's end regardless. `binOf` (README §9.7) returns `Undetermined` with `OutsideDeclaredSpace` for any position outside `ex:recurrence-valid-range`, rather than extrapolating the recurrence indefinitely.

A deployment may query the applicable bin directly, materialise `qnt:RecurrenceBin` resources, or maintain the same bins in an external operational store — all three must produce the same bin key for the same position, per `Q9`.

---

# Part VII — Ordering bases

## 13. Deterministic tie-breaking

An earlier draft's `OrderingBasis` had a primary space and nothing else, and its worked example invented a deployment-level tie-breaker property to compensate — exactly the private-invention failure mode the substrate exists to prevent. Fixed with `OrderingComponent`.

```turtle-example
ex:meter-reading-order
    a qnt:OrderingBasis ;
    qnt:hasOrderingComponent ex:observation-position-component , ex:assertion-position-component ;
    qnt:unresolvedOrderPolicy qnt:PlaceLast .

ex:observation-position-component
    a qnt:OrderingComponent ;
    qnt:componentIndex "0"^^xsd:nonNegativeInteger ;
    qnt:componentSpace ex:observation-time-space ;
    qnt:componentDirection qnt:Ascending .

ex:assertion-position-component
    a qnt:OrderingComponent ;
    qnt:componentIndex "1"^^xsd:nonNegativeInteger ;
    qnt:componentSpace ex:assertion-time-space ;
    qnt:componentDirection qnt:Ascending .
```

A scheduled meter read and a later correction sharing the same observation timestamp now resolve deterministically: the primary component (observation position) ties, and the second component (assertion position — when each reading was actually recorded) breaks it. Under `Q11`, this ordering is the same regardless of storage order or when it's evaluated, checked by running it over a representative input set, not by inspecting the declaration.
---

# Part VIII — Operation capabilities with operands

## 14. Position minus position, yielding an extent

An earlier draft defined `OperationOperand` but never used it, including in the one case that actually motivates it — subtracting two positions to get an extent, on a *different* result space than either operand. Worked here.

```turtle-example
ex:position-space a qnt:ValueSpace ;
    qnt:spaceKey "delivery-position" ; qnt:orderKind qnt:TotalOrder ; qnt:densityKind qnt:Dense ;
    qnt:spaceHash "example:position-space:v1" ;
    qnt:hasOperationCapability ex:position-difference .

ex:extent-space a qnt:ValueSpace ;
    qnt:spaceKey "delivery-extent" ; qnt:orderKind qnt:TotalOrder ; qnt:densityKind qnt:Dense ;
    qnt:spaceHash "example:extent-space:v1" ;
    qnt:hasOperationCapability ex:extent-sum .

ex:position-difference
    a qnt:OperationCapability ;
    qnt:operationKind qnt:Difference ;
    qnt:resultSpace ex:extent-space ;
    qnt:hasOperand
        [ a qnt:OperationOperand ; qnt:operandIndex "0"^^xsd:nonNegativeInteger ; qnt:operandSpace ex:position-space ] ,
        [ a qnt:OperationOperand ; qnt:operandIndex "1"^^xsd:nonNegativeInteger ; qnt:operandSpace ex:position-space ] .

ex:extent-sum a qnt:OperationCapability ; qnt:operationKind qnt:Sum ; qnt:resultSpace ex:extent-space .
```

Two positions in, one extent out, on a space neither operand belongs to — exactly the case §4's "position and extent are distinct spaces" decision exists to make representable, now with a declared signature rather than an implicit convention.

---

# Part IX — Direct SPARQL evaluation

## 15. Closed-bound containment, directly queried

```sparql
PREFIX qnt: <https://www.nebularis.org/neuro-semantic/lattice/quantification#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

ASK WHERE {
  ?candidate qnt:onSpace ?space ; qnt:numericValue ?candidateValue .
  ?range qnt:onSpace ?space ; qnt:upperBound ?bound .
  ?bound qnt:boundClosure qnt:Closed ; qnt:boundValue/qnt:numericValue ?boundValue .
  FILTER (?candidateValue <= ?boundValue)
}
```

This query answers the *same-unit, closed-bound* case directly. It does not attempt unit conversion or contextual resolution — a general-purpose evaluator additionally checks the relevant `UnitContract`, resolves any required `Conversion`, and returns `Undetermined` with `ConversionContextAbsent` only where a *contextual* step in that resolution genuinely lacks its context, not merely because two literals happen to differ. An earlier draft's illustrative query treated any unit inequality as `ConversionContextAbsent`, which is wrong whenever the units differ by a `Defined`, non-contextual conversion — corrected by scoping this query's stated purpose to the same-unit case rather than mis-stating the general one.

---

# Part X — SHACL readiness validation

## 16. A deployment shape, `ex:`-named

Substrate shapes (`quantification.md` §11) are `qnt:`-named. A deployment authoring its own operational readiness shape uses its own namespace — never `qnt:` for a shape the substrate itself doesn't ship.

```turtle-example
ex:MassRangeReadinessShape
    a sh:NodeShape ;
    sh:targetClass qnt:Range ;
    sh:property [
        sh:path qnt:onSpace ;
        sh:hasValue ex:mass-space ;
    ] ;
    sh:sparql [
        sh:message "A mass Range on a UnitContract requiring units must have bound values carrying a unit." ;
        sh:select """
            SELECT $this WHERE {
                $this qnt:upperBound/qnt:boundValue ?v .
                FILTER NOT EXISTS { ?v qnt:inUnit ?u }
            }
        """
    ] .
```

---

# Part XI — Materialised and external projections

## 17. A materialised range normal form, with declared authority

Every derived product now carries an authority declaration — advisory, cached-reproducible, operationally authoritative, or externally authoritative-and-synchronised. An earlier draft's examples included most of the required provenance metadata but never this specific property.

```turtle-example
ex:normalised-temperature-ranges
    a qnt:RangeSet ;
    qnt:onSpace ex:temperature-space ;
    qnt:hasRange ex:normalised-cool-range , ex:normalised-warm-range ;
    ex:isNormalised true ;
    ex:derivedFrom ex:permitted-temperature-ranges ;
    ex:derivationAuthority ex:CachedReproducible .
```

The source set remains intact; the normalised set can be discarded and regenerated if its dependencies change, exactly because its authority is declared as cached-reproducible rather than operationally authoritative in its own right.

A relational or document-store projection (SQL DDL, JSON payload) follows the same pattern as before — a derived representation identifying its source semantic hash, producing profile, and now its authority level, never an alternative ontology.

---

# Part XII — Optional compiled calculation

## 18. When compilation is justified

Unchanged in substance from the earlier draft: compilation suits stable declarations, high-frequency calculation, and strict latency needs; it is not required for storage, investigation, validation, reporting, or moderate-volume comparison. A compiled evaluator is itself a derived artefact, valid only for the declaration versions, unit contracts, operational profile, and canonicalisation rules it was built against — and now, per Part XI, carrying its own authority declaration like any other derived product.

---

# Part XIII — Behaviour and Eligibility composition

*Standing note, applying to every example in this Part, not restated per example: any Party-, Instrument-, Eligibility-, or Behaviour-prefixed term below is illustrative and uses `ex:`, because Quantification's own specification never references those layers' namespaces. The account, the condition trigger, and the guard shown here belong to Behaviour and Eligibility respectively; Quantification supplies only the comparison and range semantics they consume.*

## 19. Eligibility range containment

```turtle-example
ex:observed-grade a qnt:OrdinalValue ; qnt:onSpace ex:grade-space ; qnt:ordinalConcept ex:grade-three .

ex:permitted-grade-band
    a qnt:Range ; qnt:onSpace ex:grade-space ;
    qnt:lowerBound ex:grade-band-lower ; qnt:upperBound ex:grade-band-upper .

# An Eligibility-layer evaluation might then read:
# contains(observed-grade, permitted-grade-band) = qnt:True, via ex:mass-contains-equivalent's
# rangeSemanticsKind ExactRangeSemantics — safe for meet-based enumeration.
```

## 20. A comparison Behaviour disposes of as `True`

```turtle-example
ex:observed-quantity a qnt:Quantity ; qnt:onSpace ex:mass-space ;
    qnt:numericValue "24500"^^xsd:decimal ; qnt:inUnit ex:mass-base-unit .

ex:quantity-exceeds-bound
    a qnt:Comparison ;
    qnt:comparisonResult qnt:True ;
    qnt:comparisonProfile ex:direct-sparql-profile .

# A Behaviour condition trigger consumes this result and fires.
```

## 21. A comparison Behaviour disposes of as `Undetermined`

An earlier draft showed only the `True` path; the `Undetermined` path — where the substrate's three-valued semantics actually earn their place — was untested.

```turtle-example
ex:disputed-mass-comparison
    a qnt:Comparison ;
    qnt:comparisonResult qnt:Undetermined ;
    qnt:unresolvedReason qnt:ValueMarkedUnresolved ;
    qnt:comparisonProfile ex:direct-sparql-profile ;
    fnd:hasEvidence ex:disputed-mass-comparison-evidence .

ex:disputed-mass-comparison-evidence a fnd:Evidence ;
    fnd:supports ex:disputed-mass-comparison ;
    fnd:recordedAt "2026-04-02T00:01:00Z"^^xsd:dateTime ;
    fnd:assertedBy ex:comparison-evaluator .

# A Behaviour condition trigger reading this result does not fire an edge —
# Undetermined is neither True nor False, and Behaviour's own guard
# disposition (not shown here — Behaviour's construct, not Quantification's)
# decides what happens to an occurrence stalled on an indeterminate result.
# Quantification's contribution stops at supplying the honest Undetermined;
# Behaviour decides what to do with it.
```

## 22. A recurrence bin as reset-bin identity

```turtle-example
# The account itself belongs to Behaviour and is shown only illustratively,
# per the standing note at the head of this Part.
ex:allowance-account-example
    ex:forOccupant ex:some-occupant ;
    ex:governedBy ex:some-allowance-definition ;
    ex:resetBin ex:periodic-window-bin-2026-09 ;
    ex:keyValue ex:some-key-value .
```

Quantification establishes that `ex:periodic-window-bin-2026-09`'s key is stable and independently reproducible (`Q9`). Behaviour establishes the account's depletion, reset, authority, transition, and execution semantics.

---

# Part XIV — Law discharges and recommended test cases

## 23. One discharge of each register

```turtle-example
ex:q8-discharge
    a qnt:SemanticLawDischarge ;
    qnt:dischargesLaw ex:zero-bounded-closure-law ;
    qnt:dischargedForImplementationProfile ex:direct-sparql-profile ;
    qnt:formalArgumentReference ex:q8-proof-document ;
    fnd:hasEvidence ex:q8-proof-document .

ex:q7-discharge
    a qnt:StaticConstraintDischarge ;
    qnt:dischargesLaw ex:operation-admissibility-law ;
    qnt:dischargedForImplementationProfile ex:shacl-validation-profile ;
    qnt:staticAnalysisMethod ex:shacl-shapes-package-v1 ;
    fnd:hasEvidence ex:q7-shacl-conformance-record .

ex:q9-discharge
    a qnt:RuntimeConformanceDischarge ;
    qnt:dischargesLaw ex:recurrence-determinism-law ;
    qnt:dischargedForImplementationProfile ex:direct-sparql-profile ;
    qnt:executedTestRun ex:q9-independent-recomputation-run ;
    fnd:hasEvidence ex:q9-independent-recomputation-run .
```

`ex:q8-discharge` cites a formal argument; `ex:q7-discharge` cites which static analysis checked it; `ex:q9-discharge` cites an actually executed test run comparing two independent recomputations. None of the three discharge types would satisfy another law's register — a `SemanticLawDischarge` asserted for `Q9` would not discharge it, since a formal argument alone cannot establish what an implementation does when run.

## 24. Minimum direct-evaluation corpus

| Test | Expected result |
|---|---|
| Closed lower bound, equal candidate | true |
| Open lower bound, equal candidate | false |
| Closed upper bound, equal candidate | true |
| Open upper bound, equal candidate | false |
| Half-bounded upper range, no lower endpoint | evaluated only against the upper bound |
| Half-bounded lower range, no upper endpoint | evaluated only against the lower bound |
| Candidate and bound on distinct spaces | undetermined, `OutsideDeclaredSpace` |
| Distinct compatible units with a defined conversion | definite result |
| Contextual conversion without context | undetermined, `ConversionContextAbsent` |
| Known coarse value spanning a boundary | undetermined, `GranularityInsufficient` |
| Explicit unresolved value | undetermined, declared reason |
| Grade comparison | permitted where declared |
| Grade sum or average | rejected, `OperationNotPermitted` |
| Ordinary Range asserted on a CyclicOrder space | declaration-validation failure |
| Cyclic range crossing the cycle boundary, both endpoint closures | correct containment on both sides |
| Cyclic extent equal to cycle length | whole-cycle range, all positions contained |
| Cyclic extent exceeding cycle length | declaration-validation failure |
| Closed and open bounds on the same endpoint value, same range set | normalisation edge case |
| Identical recurrence declarations, recomputed independently | same bin key |
| Recurrence bin lookup exactly on a boundary | resolves to the declared side, not ambiguous |
| Two ordering inputs identical on every declared component | resolved by `unresolvedOrderPolicy`, no fabricated order |
| Overlap capability used for meet-based enumeration | rejected — `participatesInMeet` false |

## 25. Multi-profile conformance

| Profile | Must agree on |
|---|---|
| Direct SPARQL (mandatory) | semantic comparison result and unresolved reasons |
| SHACL validation (mandatory) | readiness and structural failures |
| Reasoner-assisted | declared classification consequences |
| Materialised RDF view | source-equivalent evaluation result |
| External projection | source-equivalent result for supported semantics |
| Compiled evaluator | source-equivalent result for supported semantics |

Direct SPARQL and SHACL are the mandatory floor (README §11); every other profile is per-deployment and must agree with that floor over the shared conformance corpus wherever it's supported. Permitted differences are non-semantic: storage identifiers, materialisation timestamps, blank-node labels, physical query plans.

---

## 26. Closing guidance

1. Declare the ValueSpace and its operations before treating values as comparable.
2. Store values, ranges, unresolved states, and evidence directly in the graph.
3. Return `Undetermined` rather than inventing precision, conversion, or order.
4. Materialise only where reuse or operational performance justifies it, and declare that materialisation's authority level when you do.
5. Treat external projections and compiled calculators as derived, versioned implementations of graph semantics, never as a second ontology.
6. Keep units, calendars, conversions, ordinal scales, and domain meanings in deployment-controlled vocabularies, never in the substrate.

> Declare the semantics of values first. Query, validate, reason, materialise, project, or compile only according to the operational need at hand.
