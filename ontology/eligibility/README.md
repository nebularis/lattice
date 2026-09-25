<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Eligibility Ontology — Conditions, Questions, and Admissibility Decisions

Literate specification for the Eligibility layer.

---

## 1. Purpose and Scope

Eligibility models admissibility by declaring reusable conditions, collecting evaluation questions, and recording a three-valued decision (`Permitted`, `Denied`, `Undetermined`).

Eligibility imports Foundation, Vocabulary, Quantification, and Party. Quantification is a direct dependency because interval admissibility uses declared `qnt:Range` and `qnt:RangeSet` semantics.

## 2. Namespace and Prefixes

```turtle-spec
@prefix elg:  <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .
@prefix fnd:  <https://www.nebularis.org/neuro-semantic/lattice/foundation#> .
@prefix voc:  <https://www.nebularis.org/neuro-semantic/lattice/vocabulary#> .
@prefix qnt:  <https://www.nebularis.org/neuro-semantic/lattice/quantification#> .
@prefix pty:  <https://www.nebularis.org/neuro-semantic/lattice/party#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
```

## 3. Extraction Contract

- `turtle-spec` blocks generate `spec/eligibility.ttl`.
- `turtle-vocab` blocks generate `vocab/eligibility-vocab.ttl`.
- `turtle-shapes` blocks generate `shapes/*.ttl`.
- `turtle-example` blocks are illustrative only.

## 4. Strategy Algebra

- Included match strategies: `ExactMatch`, `SetMembership`, `IntervalContainment`, `HierarchicalMatch`, `Wildcard`.
- Excluded: `IntervalOverlap` as an admissibility strategy.
- Compatibility operations: `AllRequired`, `AnySufficient`, `DimensionConsistent`.
- Wildcard policies: `NoWildcard`, `SingleDimensionWildcard`, `MultiDimensionWildcard`.

`HierarchicalMatch` is valid when a dimension is backed by a concept scheme whose membership is resolved against a well-founded `skos:broader` hierarchy. Evaluation may compute closure at query time or use a generated surface, provided closure is interpreted over the bound scheme.

## 5. Core Model

```turtle-spec
@base <https://www.nebularis.org/neuro-semantic/eligibility> .

<https://www.nebularis.org/neuro-semantic/eligibility>
	rdf:type owl:Ontology ;
	owl:versionIRI <https://www.nebularis.org/neuro-semantic/lattice/eligibility/0.2.0> ;
	owl:imports <https://www.nebularis.org/neuro-semantic/lattice/foundation/0.2.0> ,
				<https://www.nebularis.org/neuro-semantic/lattice/vocabulary/0.2.0> ,
				<https://www.nebularis.org/neuro-semantic/lattice/quantification/0.2.0> ,
				<https://www.nebularis.org/neuro-semantic/lattice/party/0.2.0> .

elg:Condition a owl:Class ;
	rdfs:comment "A declared admissibility condition." .

elg:ExactCondition a owl:Class ; rdfs:subClassOf elg:Condition .
elg:SetMembershipCondition a owl:Class ; rdfs:subClassOf elg:Condition .
elg:IntervalCondition a owl:Class ; rdfs:subClassOf elg:Condition .
elg:WildcardCondition a owl:Class ; rdfs:subClassOf elg:Condition .

elg:AdmissionProfile a owl:Class ;
	rdfs:subClassOf elg:Condition, fnd:Version,
		[ a owl:Restriction ; owl:onProperty elg:hasCondition ; owl:minCardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "A reusable admissibility profile that composes one or more conditions." .

elg:Question a owl:Class ;
	rdfs:subClassOf fnd:Evidenced,
		[ a owl:Restriction ; owl:onProperty elg:forCondition ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "An evaluation question posed against one condition." .

elg:EligibilityDecision a owl:Class ;
	rdfs:subClassOf fnd:Evidenced,
		[ a owl:Restriction ; owl:onProperty elg:forProfile ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty elg:hasQuestion ; owl:minCardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty elg:decisionValue ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "A recorded admissibility decision for one profile and one or more questions." .

elg:MatchStrategy a owl:Class .
elg:CompatibilityOperation a owl:Class .
elg:WildcardSemantics a owl:Class .
elg:Decision a owl:Class .
elg:OperationalProfile a owl:Class ; rdfs:subClassOf fnd:Version .
elg:Law a owl:Class .
elg:LawRegister a owl:Class .

elg:hasCondition a owl:ObjectProperty ;
	rdfs:domain elg:AdmissionProfile ; rdfs:range elg:Condition .

elg:forCondition a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain elg:Question ; rdfs:range elg:Condition .

elg:requiredRangeSet a owl:ObjectProperty ;
	rdfs:domain elg:Condition ; rdfs:range qnt:RangeSet .

elg:candidateRangeSet a owl:ObjectProperty ;
	rdfs:domain elg:Question ; rdfs:range qnt:RangeSet .

elg:candidateValue a owl:ObjectProperty ;
	rdfs:domain elg:Question ; rdfs:range qnt:Value .

elg:matchStrategy a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain elg:Condition ; rdfs:range elg:MatchStrategy .

elg:constrainedByContract a owl:ObjectProperty ;
	rdfs:domain elg:Condition ; rdfs:range voc:SchemeContract .

elg:compatibilityOperation a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain elg:Condition ; rdfs:range elg:CompatibilityOperation .

elg:wildcardSemantics a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain elg:Condition ; rdfs:range elg:WildcardSemantics .

elg:forProfile a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain elg:EligibilityDecision ; rdfs:range elg:AdmissionProfile .

elg:hasQuestion a owl:ObjectProperty ;
	rdfs:domain elg:EligibilityDecision ; rdfs:range elg:Question .

elg:decisionValue a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain elg:EligibilityDecision ; rdfs:range elg:Decision .

elg:lawRegister a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain elg:Law ; rdfs:range elg:LawRegister .

elg:usesOperationalProfile a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain elg:EligibilityDecision ; rdfs:range elg:OperationalProfile .

elg:subjectRoleOccupancy a owl:ObjectProperty ;
	rdfs:domain elg:Question ; rdfs:range pty:RoleOccupancy .

elg:conditionKey a owl:DatatypeProperty, owl:FunctionalProperty ;
	rdfs:domain elg:Condition ; rdfs:range xsd:string .

[] a owl:AllDisjointClasses ;
	owl:members ( elg:Condition elg:Question elg:EligibilityDecision elg:MatchStrategy elg:CompatibilityOperation elg:WildcardSemantics elg:Decision elg:OperationalProfile elg:Law ) .
```

## 6. Mechanism Vocabulary

```turtle-vocab
@prefix elg:  <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

elg:ExactMatch a elg:MatchStrategy .
elg:SetMembership a elg:MatchStrategy .
elg:IntervalContainment a elg:MatchStrategy .
elg:HierarchicalMatch a elg:MatchStrategy .
elg:Wildcard a elg:MatchStrategy .

elg:AllRequired a elg:CompatibilityOperation .
elg:AnySufficient a elg:CompatibilityOperation .
elg:DimensionConsistent a elg:CompatibilityOperation .

elg:NoWildcard a elg:WildcardSemantics .
elg:SingleDimensionWildcard a elg:WildcardSemantics .
elg:MultiDimensionWildcard a elg:WildcardSemantics .

elg:Permitted a elg:Decision .
elg:Denied a elg:Decision .
elg:Undetermined a elg:Decision .

elg:E1 a elg:OperationalProfile ; rdfs:comment "Exact-match profile" .
elg:E2 a elg:OperationalProfile ; rdfs:comment "Interval-containment profile" .
elg:E3 a elg:OperationalProfile ; rdfs:comment "Wildcard profile" .
elg:E4 a elg:OperationalProfile ; rdfs:comment "Compatibility-any profile" .
elg:E5 a elg:OperationalProfile ; rdfs:comment "Compatibility-all profile" .
elg:E6 a elg:OperationalProfile ; rdfs:comment "Dimension-consistency profile" .

elg:SemanticLaw a elg:LawRegister ; rdfs:comment "Discharged by formal argument." .

elg:L1 a elg:Law ; rdfs:comment "Each condition declares exactly one match strategy." .
elg:L2 a elg:Law ; rdfs:comment "Each condition declares exactly one compatibility operation." .
elg:L3 a elg:Law ; rdfs:comment "Each condition declares exactly one wildcard policy." .
elg:L4 a elg:Law ; rdfs:comment "IntervalContainment requires declared requiredRangeSet." .
elg:L5 a elg:Law ; rdfs:comment "IntervalOverlap is excluded from admissibility decisions." .
elg:L6 a elg:Law ; rdfs:comment "EligibilityDecision has exactly one decision value." .
elg:L7 a elg:Law ; rdfs:comment "EligibilityDecision references at least one question." .
elg:L8 a elg:Law ; rdfs:comment "EligibilityDecision names one operational profile." .
elg:L9 a elg:Law ;
	elg:lawRegister elg:SemanticLaw ;
	rdfs:comment "Hierarchical match closure. A candidate value satisfies a condition under hierarchical match exactly when it stands in the reflexive-transitive closure of the bound scheme's ordering relation, restricted to that scheme's members, below the asserted value. The ordering relation is acyclic over the bound scheme; a scheme carrying a cycle is not evaluable under hierarchical match." .
```

## 7. Shapes

```turtle-shapes
@prefix sh:   <http://www.w3.org/ns/shacl#> .
@prefix elg:  <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .

elg:ConditionShape a sh:NodeShape ;
	sh:targetClass elg:Condition ;
	sh:property [ sh:path elg:matchStrategy ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path elg:compatibilityOperation ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path elg:wildcardSemantics ; sh:minCount 1 ; sh:maxCount 1 ] .

elg:IntervalConditionShape a sh:NodeShape ;
	sh:targetClass elg:IntervalCondition ;
	sh:property [ sh:path elg:requiredRangeSet ; sh:minCount 1 ] .
```

## 8. Worked Examples

Illustrative non-domain examples are authored in:

- `ontology/eligibility/examples/condition-taxonomy.ttl`
- `ontology/eligibility/examples/interval-containment.ttl`
- `ontology/eligibility/examples/hierarchical-match.ttl`

```turtle-example
@prefix elg: <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .
@prefix ex:  <https://example.org/lattice/eligibility/> .

ex:decision-1 a elg:EligibilityDecision ;
	elg:decisionValue elg:Permitted .
```

## 9. Canonicalisation

Eligibility canonicalisation is declaration-first and profile-stable:

- `elg:conditionKey` is the canonical identifier of a condition declaration for comparison, caching, and replay.
- Canonicalisation never changes the declared strategy (`elg:matchStrategy`), compatibility operation (`elg:compatibilityOperation`), or wildcard semantics (`elg:wildcardSemantics`).
- Interval admissibility canonicalises through Quantification ranges and range sets only, using `elg:requiredRangeSet` and `elg:candidateRangeSet` with `qnt:Range`/`qnt:RangeSet`.
