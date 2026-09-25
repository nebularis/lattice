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
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
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

Conditions matching by `ExactMatch`, `SetMembership`, or `HierarchicalMatch` state what they match against with `elg:requiredConcept` and `elg:excludedConcept`. A candidate *matches* a concept by equality under `ExactMatch` and `SetMembership`, and by standing at or below it in the bound scheme's ordering under `HierarchicalMatch`. Several required concepts are alternatives to one another, and each excluded concept excludes independently. Neither reading changes how the condition's compatibility operation is interpreted. An admission profile declares no concepts of its own, since its conditions do. A question offers its candidate with `elg:candidateConcept`. `IntervalContainment` needs no exclusion construct: a `qnt:RangeSet` is a union of ranges and already expresses gaps.

| Candidate | Decision | Law |
|---|---|---|
| absent, unresolved, more than one per question, or outside the bound scheme where the decision needs that scheme | `Undetermined` | |
| matches an excluded concept | `Denied`, whether or not it also matches a required concept | L10 |
| under `HierarchicalMatch`, stands strictly above an excluded concept and is otherwise admitted | `Undetermined`, since its true value may fall under the exclusion | L11 |
| matches a required concept, or the condition declares exclusions only and the candidate is a member of the bound scheme | `Permitted` | L12 for the second case |
| otherwise | `Denied` | |

**Evidence bindings.** A condition reads its candidate from an `elg:Question` unless an `elg:EvidenceBinding` binds it. A binding names the class of subjects the condition evaluates (`elg:subjectClass`) and an ordered path of `elg:EvidenceStep`s from each subject to its candidate, over the applied ontology's own properties (ADR-A91). The path ends at a `skos:Concept` for a concept condition. For an interval condition it ends at a `qnt:Quantity` on the condition's value space, or at a literal where the binding reads on that space (`elg:readOnSpace`). A subject with no value at the end of the path, or several, is `Undetermined`, as is one whose value is on another space. A profile evaluates either questions or one class of bound subjects. A binding may claim that each step of its path yields at most one value (`elg:singleValued`). The design-time OWL backend compiles only claimed paths (ADR-A90).

## 5. Core Model

```turtle-spec
@base <https://www.nebularis.org/neuro-semantic/eligibility> .

<https://www.nebularis.org/neuro-semantic/eligibility>
	rdf:type owl:Ontology ;
	owl:versionIRI <https://www.nebularis.org/neuro-semantic/lattice/eligibility/0.6.0> ;
	owl:imports <https://www.nebularis.org/neuro-semantic/lattice/foundation/0.3.0> ,
				<https://www.nebularis.org/neuro-semantic/lattice/vocabulary/0.3.0> ,
				<https://www.nebularis.org/neuro-semantic/lattice/quantification/0.5.0> ,
				<https://www.nebularis.org/neuro-semantic/lattice/party/0.5.0> .

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

elg:requiredConcept a owl:ObjectProperty ;
	rdfs:domain elg:Condition ; rdfs:range skos:Concept ;
	rdfs:comment "A concept a candidate must match, under the condition's match strategy. Several required concepts are alternatives to one another." .

elg:excludedConcept a owl:ObjectProperty ;
	rdfs:domain elg:Condition ; rdfs:range skos:Concept ;
	rdfs:comment "A concept a candidate must not match, under the condition's match strategy. Each excluded concept excludes independently of the others." .

elg:candidateRangeSet a owl:ObjectProperty ;
	rdfs:domain elg:Question ; rdfs:range qnt:RangeSet .

elg:candidateValue a owl:ObjectProperty ;
	rdfs:domain elg:Question ; rdfs:range qnt:Value .

elg:candidateConcept a owl:ObjectProperty ;
	rdfs:domain elg:Question ; rdfs:range skos:Concept ;
	rdfs:comment "The concept a question offers to a condition matching by ExactMatch, SetMembership or HierarchicalMatch." .

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

elg:EvidenceBinding a owl:Class ;
	rdfs:comment "Binds a condition to the class of subjects it evaluates and to the path that reaches each subject's candidate on the applied ontology's own properties (ADR-A91)." .

elg:EvidenceStep a owl:Class ;
	rdfs:comment "One positioned traversal within an evidence binding's path, in a stated direction. Shaped like srf:PathStep." .

elg:StepDirection a owl:Class .

rdf:Property a owl:Class .

elg:bindsCondition a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain elg:EvidenceBinding ; rdfs:range elg:Condition .

elg:subjectClass a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain elg:EvidenceBinding ;
	rdfs:comment "The class whose instances the bound condition evaluates." .

elg:evidenceStep a owl:ObjectProperty ;
	rdfs:domain elg:EvidenceBinding ; rdfs:range elg:EvidenceStep .

elg:stepIndex a owl:DatatypeProperty, owl:FunctionalProperty ;
	rdfs:domain elg:EvidenceStep ; rdfs:range xsd:nonNegativeInteger ;
	rdfs:comment "Zero-based position of the step in traversal order." .

elg:stepProperty a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain elg:EvidenceStep ; rdfs:range rdf:Property .

elg:stepDirection a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain elg:EvidenceStep ; rdfs:range elg:StepDirection .

elg:readOnSpace a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain elg:EvidenceBinding ; rdfs:range qnt:ValueSpace ;
	rdfs:comment "The value space a literal at the end of an interval condition's path is read on. A qnt:Quantity at the end of the path states its own space." .

elg:singleValued a owl:DatatypeProperty, owl:FunctionalProperty ;
	rdfs:domain elg:EvidenceBinding ; rdfs:range xsd:boolean ;
	rdfs:comment "The author's claim that each step of the binding's path yields at most one value. The design-time OWL backend compiles only claimed paths, and checks the claim on data with a generated shape (ADR-A90 addendum, option B)." .

[] a owl:AllDisjointClasses ;
	owl:members ( elg:Condition elg:Question elg:EligibilityDecision elg:MatchStrategy elg:CompatibilityOperation elg:WildcardSemantics elg:Decision elg:OperationalProfile elg:Law elg:EvidenceBinding elg:EvidenceStep elg:StepDirection ) .
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

elg:Forward a elg:StepDirection ; rdfs:comment "Traversed from subject to object." .
elg:Inverse a elg:StepDirection ; rdfs:comment "Traversed from object to subject." .

elg:E1 a elg:OperationalProfile ; rdfs:comment "Exact-match profile" .
elg:E2 a elg:OperationalProfile ; rdfs:comment "Interval-containment profile" .
elg:E3 a elg:OperationalProfile ; rdfs:comment "Wildcard profile" .
elg:E4 a elg:OperationalProfile ; rdfs:comment "Compatibility-any profile" .
elg:E5 a elg:OperationalProfile ; rdfs:comment "Compatibility-all profile" .
elg:E6 a elg:OperationalProfile ; rdfs:comment "Dimension-consistency profile" .

elg:SemanticLaw a elg:LawRegister ; rdfs:comment "Discharged by formal argument." .
elg:StaticConstraint a elg:LawRegister ; rdfs:comment "Discharged by SHACL, SPARQL, or other static analysis of declarations." .

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
elg:L10 a elg:Law ;
	elg:lawRegister elg:SemanticLaw ;
	rdfs:comment "Exclusion precedence. A candidate that matches an excluded concept of a condition, under the condition's match strategy, does not satisfy the condition, whether or not it also matches a required concept." .
elg:L11 a elg:Law ;
	elg:lawRegister elg:SemanticLaw ;
	rdfs:comment "Exclusion granularity. Under hierarchical match, a candidate that stands strictly above an excluded concept in the bound scheme's ordering, and is otherwise admitted, leaves the condition undetermined for that candidate. Its true value may or may not fall under the exclusion." .
elg:L12 a elg:Law ;
	elg:lawRegister elg:SemanticLaw ;
	rdfs:comment "Default inclusion. A condition that declares excluded concepts and no required concept requires every member of its bound scheme, so it admits any member not excluded." .
elg:L13 a elg:Law ;
	elg:lawRegister elg:StaticConstraint ;
	rdfs:comment "Reachable exclusions. Where a condition declares required concepts, each of its excluded concepts matches at least one of them under the condition's match strategy. An exclusion outside every inclusion excludes nothing." .
```

## 7. Shapes

```turtle-shapes
@prefix sh:   <http://www.w3.org/ns/shacl#> .
@prefix elg:  <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

elg:ConditionShape a sh:NodeShape ;
	sh:targetClass elg:Condition ;
	sh:property [ sh:path elg:matchStrategy ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path elg:compatibilityOperation ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path elg:wildcardSemantics ; sh:minCount 1 ; sh:maxCount 1 ] .

elg:IntervalConditionShape a sh:NodeShape ;
	sh:targetClass elg:IntervalCondition ;
	sh:property [ sh:path elg:requiredRangeSet ; sh:minCount 1 ] .

elg:ConceptConditionDeclarationShape a sh:NodeShape ;
	sh:targetClass elg:Condition ;
	sh:severity sh:Warning ;
	sh:sparql [
		sh:message "A condition matching by ExactMatch, SetMembership or HierarchicalMatch declares neither a required nor an excluded concept, so it states nothing to match against." ;
		sh:select """
			PREFIX elg: <https://www.nebularis.org/neuro-semantic/lattice/eligibility#>
			SELECT $this WHERE {
				$this elg:matchStrategy ?strategy .
				FILTER (?strategy IN (elg:ExactMatch, elg:SetMembership, elg:HierarchicalMatch))
				FILTER NOT EXISTS { $this elg:requiredConcept ?required }
				FILTER NOT EXISTS { $this elg:excludedConcept ?excluded }
				FILTER NOT EXISTS { $this elg:hasCondition ?member }
			}
		"""
	] ;
	sh:sparql [
		sh:message "A required or excluded concept is declared on a condition whose match strategy does not match concepts. IntervalContainment expresses gaps through its range set instead." ;
		sh:select """
			PREFIX elg: <https://www.nebularis.org/neuro-semantic/lattice/eligibility#>
			SELECT $this WHERE {
				$this elg:matchStrategy ?strategy .
				FILTER (?strategy IN (elg:IntervalContainment, elg:Wildcard))
				{ $this elg:requiredConcept ?concept } UNION { $this elg:excludedConcept ?concept }
			}
		"""
	] .

elg:ReachableExclusionShape a sh:NodeShape ;
	sh:targetClass elg:Condition ;
	sh:severity sh:Warning ;
	sh:sparql [
		sh:message "An excluded concept matches none of the condition's required concepts, so it excludes nothing. Discharges elg:L13." ;
		sh:select """
			PREFIX elg: <https://www.nebularis.org/neuro-semantic/lattice/eligibility#>
			PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
			SELECT $this ?value WHERE {
				$this elg:excludedConcept ?value ;
					  elg:requiredConcept ?anyRequired .
				FILTER NOT EXISTS {
					$this elg:requiredConcept ?required .
					FILTER (?value = ?required || EXISTS {
						$this elg:matchStrategy elg:HierarchicalMatch .
						?value skos:broader+ ?required .
					})
				}
			}
		"""
	] .

elg:EvidenceBindingShape a sh:NodeShape ;
	sh:targetClass elg:EvidenceBinding ;
	sh:property [ sh:path elg:bindsCondition ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path elg:subjectClass ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path elg:evidenceStep ; sh:minCount 1 ] ;
	sh:property [ sh:path elg:singleValued ; sh:maxCount 1 ; sh:datatype xsd:boolean ] .

elg:EvidenceStepShape a sh:NodeShape ;
	sh:targetClass elg:EvidenceStep ;
	sh:property [ sh:path elg:stepIndex ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path elg:stepProperty ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path elg:stepDirection ; sh:minCount 1 ; sh:maxCount 1 ; sh:in ( elg:Forward elg:Inverse ) ] .
```

## 8. Worked Examples

Illustrative non-domain examples are authored in:

- `ontology/eligibility/examples/condition-taxonomy.ttl`
- `ontology/eligibility/examples/interval-containment.ttl`
- `ontology/eligibility/examples/hierarchical-match.ttl`
- `ontology/eligibility/examples/evidence-binding.ttl`

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
