<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Behaviour Ontology — State, Transition, Trigger, Guard, Effect, and Allowance

Literate specification for the Behaviour layer.

---

## 1. Purpose and Scope

Behaviour models declared state spaces, transitions, triggers, guards, effects, executions, and durable state records.

Behaviour imports Foundation, Vocabulary, Quantification, Party, Eligibility, and Instrument.

## 2. Namespace and Prefixes

```turtle-spec
@prefix bhv:  <https://www.nebularis.org/neuro-semantic/lattice/behaviour#> .
@prefix fnd:  <https://www.nebularis.org/neuro-semantic/lattice/foundation#> .
@prefix voc:  <https://www.nebularis.org/neuro-semantic/lattice/vocabulary#> .
@prefix qnt:  <https://www.nebularis.org/neuro-semantic/lattice/quantification#> .
@prefix pty:  <https://www.nebularis.org/neuro-semantic/lattice/party#> .
@prefix elg:  <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .
@prefix ins:  <https://www.nebularis.org/neuro-semantic/lattice/instrument#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
```

## 3. Extraction Contract

- `turtle-spec` blocks generate `spec/behaviour.ttl`.
- `turtle-vocab` blocks generate `vocab/behaviour-vocab.ttl`.
- `turtle-shapes` blocks generate `shapes/*.ttl`.
- `turtle-example` blocks are illustrative only.

## 4. Four-tier model

Behaviour distinguishes four tiers:

- declaration: `StateSpace`, `State`, `TransitionDefinition`, `TriggerDefinition`, `GuardDefinition`, `EffectDefinition`, `AllowanceDefinition`, policy classes
- occurrence: `Stimulus`
- execution: `TransitionExecution`, `EffectApplication`
- state record: `StateOccupancy`, `AllowanceAccount`

## 5. Core Model

```turtle-spec
@base <https://www.nebularis.org/neuro-semantic/behaviour> .

<https://www.nebularis.org/neuro-semantic/behaviour>
	rdf:type owl:Ontology ;
	owl:versionIRI <https://www.nebularis.org/neuro-semantic/lattice/behaviour/0.2.0> ;
	owl:imports <https://www.nebularis.org/neuro-semantic/lattice/foundation/0.2.0> ,
				<https://www.nebularis.org/neuro-semantic/lattice/vocabulary/0.2.0> ,
				<https://www.nebularis.org/neuro-semantic/lattice/quantification/0.2.0> ,
				<https://www.nebularis.org/neuro-semantic/lattice/party/0.2.0> ,
				<https://www.nebularis.org/neuro-semantic/lattice/eligibility/0.2.0> ,
				<https://www.nebularis.org/neuro-semantic/lattice/instrument/0.2.0> .

bhv:StateSpace a owl:Class ;
	rdfs:subClassOf fnd:Version ;
	rdfs:comment "A declared state space." .

bhv:State a owl:Class ;
	rdfs:comment "A declared state belonging to one state space." ;
	rdfs:subClassOf [ a owl:Restriction ; owl:onProperty bhv:inStateSpace ; owl:cardinality "1"^^xsd:nonNegativeInteger ] .

bhv:TransitionDefinition a owl:Class ;
	rdfs:subClassOf fnd:Version,
		[ a owl:Restriction ; owl:onProperty bhv:fromState ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty bhv:toState ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty bhv:hasTrigger ; owl:minCardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty bhv:hasEffect ; owl:minCardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty bhv:selectionPolicy ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty bhv:activationPolicy ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "A declared transition between states." .

bhv:TriggerDefinition a owl:Class ; rdfs:comment "A declared trigger condition for a transition." .
bhv:GuardDefinition a owl:Class ; rdfs:comment "A declared eligibility or policy guard." .
bhv:EffectDefinition a owl:Class ; rdfs:comment "A declared cross-layer effect." .
bhv:Stimulus a owl:Class ; rdfs:subClassOf fnd:Evidenced ; rdfs:comment "An observed stimulus or event." .
bhv:TransitionExecution a owl:Class ; rdfs:subClassOf fnd:Evidenced ; rdfs:comment "A recorded transition execution." .
bhv:EffectApplication a owl:Class ; rdfs:subClassOf fnd:Evidenced ; rdfs:comment "A recorded effect application." .
bhv:StateOccupancy a owl:Class ; rdfs:subClassOf fnd:Evidenced, fnd:TemporallyScoped ; rdfs:comment "A current or hypothetical occupancy of a state." .

bhv:AllowanceDefinition a owl:Class ;
	rdfs:subClassOf fnd:Version,
		[ a owl:Restriction ; owl:onProperty bhv:allowanceSpace ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty bhv:absorptionPolicy ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "A declared allowance or quota model." .

bhv:AllowanceAccount a owl:Class ;
	rdfs:subClassOf fnd:Evidenced,
		[ a owl:Restriction ; owl:onProperty bhv:tracksAllowance ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty bhv:availableBalance ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "A durable state record tracking allowance balance." .

bhv:SelectionPolicy a owl:Class .
bhv:ActivationPolicy a owl:Class .
bhv:TriggerKind a owl:Class .
bhv:TargetKind a owl:Class .
bhv:AbsorptionPolicy a owl:Class .
bhv:OperationalProfile a owl:Class ; rdfs:subClassOf fnd:Version .

bhv:inStateSpace a owl:ObjectProperty, owl:FunctionalProperty ; rdfs:domain bhv:State ; rdfs:range bhv:StateSpace .
bhv:fromState a owl:ObjectProperty, owl:FunctionalProperty ; rdfs:domain bhv:TransitionDefinition ; rdfs:range bhv:State .
bhv:toState a owl:ObjectProperty, owl:FunctionalProperty ; rdfs:domain bhv:TransitionDefinition ; rdfs:range bhv:State .
bhv:hasTrigger a owl:ObjectProperty ; rdfs:domain bhv:TransitionDefinition ; rdfs:range bhv:TriggerDefinition .
bhv:hasGuard a owl:ObjectProperty ; rdfs:domain bhv:TransitionDefinition ; rdfs:range bhv:GuardDefinition .
bhv:hasEffect a owl:ObjectProperty ; rdfs:domain bhv:TransitionDefinition ; rdfs:range bhv:EffectDefinition .
bhv:triggerKind a owl:ObjectProperty, owl:FunctionalProperty ; rdfs:domain bhv:TriggerDefinition ; rdfs:range bhv:TriggerKind .
bhv:selectionPolicy a owl:ObjectProperty, owl:FunctionalProperty ; rdfs:domain bhv:TransitionDefinition ; rdfs:range bhv:SelectionPolicy .
bhv:activationPolicy a owl:ObjectProperty, owl:FunctionalProperty ; rdfs:domain bhv:TransitionDefinition ; rdfs:range bhv:ActivationPolicy .
bhv:priority a owl:DatatypeProperty, owl:FunctionalProperty ; rdfs:domain bhv:TransitionDefinition ; rdfs:range xsd:integer .
bhv:requiresEligibility a owl:ObjectProperty, owl:FunctionalProperty ; rdfs:domain bhv:GuardDefinition ; rdfs:range elg:AdmissionProfile .
bhv:targetKind a owl:ObjectProperty, owl:FunctionalProperty ; rdfs:domain bhv:EffectDefinition ; rdfs:range bhv:TargetKind .
bhv:targetsElement a owl:ObjectProperty ; rdfs:domain bhv:EffectDefinition ; rdfs:range ins:Element .
bhv:targetsOccupancy a owl:ObjectProperty ; rdfs:domain bhv:EffectDefinition ; rdfs:range pty:RoleOccupancy .
bhv:usesAllowance a owl:ObjectProperty, owl:FunctionalProperty ; rdfs:domain bhv:EffectDefinition ; rdfs:range bhv:AllowanceDefinition .
bhv:consumesAmount a owl:ObjectProperty, owl:FunctionalProperty ; rdfs:domain bhv:EffectDefinition ; rdfs:range qnt:Quantity .
bhv:allowanceSpace a owl:ObjectProperty, owl:FunctionalProperty ; rdfs:domain bhv:AllowanceDefinition ; rdfs:range qnt:ValueSpace .
bhv:resetRecurrence a owl:ObjectProperty, owl:FunctionalProperty ; rdfs:domain bhv:AllowanceDefinition ; rdfs:range qnt:Recurrence .
bhv:absorptionPolicy a owl:ObjectProperty, owl:FunctionalProperty ; rdfs:domain bhv:AllowanceDefinition ; rdfs:range bhv:AbsorptionPolicy .
bhv:tracksAllowance a owl:ObjectProperty, owl:FunctionalProperty ; rdfs:domain bhv:AllowanceAccount ; rdfs:range bhv:AllowanceDefinition .
bhv:availableBalance a owl:ObjectProperty, owl:FunctionalProperty ; rdfs:domain bhv:AllowanceAccount ; rdfs:range qnt:Quantity .
bhv:occupiesState a owl:ObjectProperty, owl:FunctionalProperty ; rdfs:domain bhv:StateOccupancy ; rdfs:range bhv:State .
bhv:forSubject a owl:ObjectProperty ; rdfs:domain bhv:StateOccupancy ; rdfs:range pty:RoleOccupancy .
bhv:executedTransition a owl:ObjectProperty, owl:FunctionalProperty ; rdfs:domain bhv:TransitionExecution ; rdfs:range bhv:TransitionDefinition .
bhv:appliesEffect a owl:ObjectProperty, owl:FunctionalProperty ; rdfs:domain bhv:EffectApplication ; rdfs:range bhv:EffectDefinition .
bhv:causedByStimulus a owl:ObjectProperty ; rdfs:domain bhv:TransitionExecution ; rdfs:range bhv:Stimulus .
bhv:usesProfile a owl:ObjectProperty, owl:FunctionalProperty ; rdfs:domain bhv:TransitionExecution ; rdfs:range bhv:OperationalProfile .
bhv:isHypothetical a owl:DatatypeProperty, owl:FunctionalProperty ; rdfs:domain bhv:StateOccupancy ; rdfs:range xsd:boolean .
bhv:isCurrent a owl:DatatypeProperty, owl:FunctionalProperty ; rdfs:domain bhv:StateOccupancy ; rdfs:range xsd:boolean .

[] a owl:AllDisjointClasses ;
	owl:members ( bhv:StateSpace bhv:State bhv:TransitionDefinition bhv:TriggerDefinition bhv:GuardDefinition bhv:EffectDefinition bhv:Stimulus bhv:TransitionExecution bhv:EffectApplication bhv:StateOccupancy bhv:AllowanceDefinition bhv:AllowanceAccount bhv:SelectionPolicy bhv:ActivationPolicy bhv:TriggerKind bhv:TargetKind bhv:AbsorptionPolicy bhv:OperationalProfile ) .
```

## 6. Mechanism vocabulary

```turtle-vocab
@prefix bhv:  <https://www.nebularis.org/neuro-semantic/lattice/behaviour#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

bhv:ExternalStimulus a bhv:TriggerKind .
bhv:ScheduledTrigger a bhv:TriggerKind .
bhv:DerivedTrigger a bhv:TriggerKind .

bhv:SingleMatch a bhv:SelectionPolicy .
bhv:AllMatches a bhv:SelectionPolicy .
bhv:PriorityOrdered a bhv:SelectionPolicy .

bhv:ImmediateActivation a bhv:ActivationPolicy .
bhv:DeferredActivation a bhv:ActivationPolicy .
bhv:ManualActivation a bhv:ActivationPolicy .

bhv:InstrumentTarget a bhv:TargetKind .
bhv:PartyTarget a bhv:TargetKind .
bhv:AllowanceTarget a bhv:TargetKind .

bhv:Sequential a bhv:AbsorptionPolicy .
bhv:Proportional a bhv:AbsorptionPolicy .

bhv:B-P1 a bhv:OperationalProfile ; rdfs:comment "Direct transition-evaluation profile" .
bhv:B-P2 a bhv:OperationalProfile ; rdfs:comment "Sequential allowance-evaluation profile" .
```

## 7. Extent profile

Gate 3 includes the allowance extent profile directly against Quantification.

- `bhv:AllowanceDefinition` binds to one `qnt:ValueSpace`.
- `bhv:AllowanceAccount` carries one current `qnt:Quantity` balance.
- `bhv:Sequential` absorption is supported now.
- `bhv:Proportional` is declared but not permitted by Gate 3 constraints.

Gate 6 does not widen that surface. `bhv:Proportional` remains declared-and-unusable until the repository carries two non-domain motivating examples, an explicit proportional conservation law, and cross-profile conformance coverage. Reset edge cases remain deferred for the same reason: they need explicit law statements and fixtures, not inferred behaviour.

State occupancy records distinguish hypothetical from current execution state through `bhv:isHypothetical` and `bhv:isCurrent`. A non-hypothetical subject may have at most one current occupancy in a given state space.

## 8. Shapes

```turtle-shapes
@prefix sh:   <http://www.w3.org/ns/shacl#> .
@prefix bhv:  <https://www.nebularis.org/neuro-semantic/lattice/behaviour#> .

bhv:TransitionDefinitionShape a sh:NodeShape ;
	sh:targetClass bhv:TransitionDefinition ;
	sh:property [ sh:path bhv:fromState ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path bhv:toState ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path bhv:hasTrigger ; sh:minCount 1 ] ;
	sh:property [ sh:path bhv:hasEffect ; sh:minCount 1 ] ;
	sh:property [ sh:path bhv:selectionPolicy ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path bhv:activationPolicy ; sh:minCount 1 ; sh:maxCount 1 ] .

bhv:AllowanceDefinitionShape a sh:NodeShape ;
	sh:targetClass bhv:AllowanceDefinition ;
	sh:property [ sh:path bhv:allowanceSpace ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path bhv:absorptionPolicy ; sh:minCount 1 ; sh:maxCount 1 ] .
```

## 9. Worked examples

Examples are authored in:

- `ontology/behaviour/examples/state-transition.ttl`
- `ontology/behaviour/examples/sequential-allowance.ttl`

```turtle-example
@prefix bhv: <https://www.nebularis.org/neuro-semantic/lattice/behaviour#> .
@prefix ex:  <https://example.org/lattice/behaviour/> .

ex:exec-1 a bhv:TransitionExecution .
```
