<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Behaviour Ontology — State, Transition, Trigger, Guard, Effect, and Allowance

Literate specification for the Behaviour layer.

---

## 1. Purpose and Scope

Behaviour models declared state spaces, transitions, triggers, guards, effects, executions, and durable state records.

Behaviour imports Foundation, Vocabulary, Quantification, Party and Eligibility. It sits below
Instrument, which builds on it, and names no term of any layer above it
([ADR-A106](../../docs/architecture/decisions/ADR-A106-behaviour-configuration-runtime-occasions-and-records.md),
[ADR-A01](../../docs/architecture/decisions/ADR-A01-layer-dependency-order.md) addendum).

Behaviour is two documents in one namespace:

| Document | File | Holds | Imported by |
|---|---|---|---|
| configuration | `spec/behaviour.ttl` | the declaration tier: state spaces, states, transitions, triggers, guards, effects, allowance definitions, policies | Instrument, applied layers, `behaviour-vocab`, the runtime document |
| runtime | `spec/behaviour-runtime.ttl` | the occurrence, execution and state record tiers: stimuli, executions, effect applications, state occupancies, allowance accounts | the runtime evaluator, applied runtime modules (`applied/capacity`'s execution profile) |

A model that only declares behaviour imports configuration and never meets a runtime record.

## 2. Namespace and Prefixes

```turtle-spec
@prefix bhv:  <https://www.nebularis.org/neuro-semantic/lattice/behaviour#> .
@prefix fnd:  <https://www.nebularis.org/neuro-semantic/lattice/foundation#> .
@prefix voc:  <https://www.nebularis.org/neuro-semantic/lattice/vocabulary#> .
@prefix qnt:  <https://www.nebularis.org/neuro-semantic/lattice/quantification#> .
@prefix pty:  <https://www.nebularis.org/neuro-semantic/lattice/party#> .
@prefix elg:  <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
```

## 3. Extraction Contract

- `turtle-spec` blocks generate `spec/behaviour.ttl`, the configuration document.
- `turtle-vocab` blocks generate `vocab/behaviour-vocab.ttl`.
- The `turtle-shapes` block generates `shapes/structural.ttl`. `shapes/constraints.ttl` and
  `shapes/rules.ttl` are authored as files.
- `spec/behaviour-runtime.ttl` is authored as a file (§5.2): the extractor writes one spec
  document per layer.
- `turtle-example` blocks are illustrative only.

```bash
python3 tools/literate_extract.py ontology/behaviour/README.md --layer behaviour --root . \
    --shapes shapes/structural.ttl --check
```

## 4. Four-tier model

Behaviour distinguishes four tiers:

- declaration: `StateSpace`, `State`, `TransitionDefinition`, `TriggerDefinition`, `GuardDefinition`, `EffectDefinition`, `AllowanceDefinition`, policy classes. The configuration document
- occurrence: `Stimulus`. The runtime document
- execution: `TransitionExecution`, `EffectApplication`. The runtime document
- state record: `StateOccupancy`, `AllowanceAccount`. The runtime document

## 5. Core Model

### 5.1 Configuration

```turtle-spec
@base <https://www.nebularis.org/neuro-semantic/behaviour> .

<https://www.nebularis.org/neuro-semantic/behaviour>
	rdf:type owl:Ontology ;
	owl:versionIRI <https://www.nebularis.org/neuro-semantic/lattice/behaviour/0.8.0> ;
	owl:imports <https://www.nebularis.org/neuro-semantic/lattice/foundation/0.3.0> ,
				<https://www.nebularis.org/neuro-semantic/lattice/vocabulary/0.3.0> ,
				<https://www.nebularis.org/neuro-semantic/lattice/quantification/0.5.0> ,
				<https://www.nebularis.org/neuro-semantic/lattice/party/0.5.0> ,
				<https://www.nebularis.org/neuro-semantic/lattice/eligibility/0.7.0> .

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
		[ a owl:Restriction ; owl:onProperty bhv:selectionPolicy ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty bhv:activationPolicy ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "A declared transition between states. It may have no effect: entering the state is often the whole effect (ADR-A106 decision 4)." .

bhv:TriggerDefinition a owl:Class ; rdfs:comment "A declared trigger condition for a transition." .
bhv:GuardDefinition a owl:Class ; rdfs:comment "A declared eligibility or policy guard." .
bhv:EffectDefinition a owl:Class ; rdfs:comment "A declared effect on a target, of one target kind." .

bhv:AllowanceDefinition a owl:Class ;
	rdfs:subClassOf fnd:Version,
		[ a owl:Restriction ; owl:onProperty bhv:allowanceSpace ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty bhv:absorptionPolicy ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "A declared allowance or quota model." .

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

bhv:targets a owl:ObjectProperty ;
	rdfs:domain bhv:EffectDefinition ;
	rdfs:comment "What an effect acts on. Subject: an effect definition. Value: any resource." ;
	fnd:utility "Deliberately has no range: an effect may target a relation, an occasion, an instrument or anything else, and a range would classify every target as one kind. The layer that declares a target kind checks proper targets with its own shapes (ADR-A106 decision 2). Use bhv:targetsOccupancy or bhv:targetsAllowance where they fit." .

bhv:targetsOccupancy a owl:ObjectProperty ;
	rdfs:subPropertyOf bhv:targets ;
	rdfs:domain bhv:EffectDefinition ; rdfs:range pty:RoleOccupancy ;
	rdfs:comment "An effect's target that is a role occupancy. Subject: an effect definition. Value: a role occupancy." .

bhv:targetsAllowance a owl:ObjectProperty ;
	rdfs:subPropertyOf bhv:targets ;
	rdfs:domain bhv:EffectDefinition ; rdfs:range bhv:AllowanceDefinition ;
	rdfs:comment "An effect's target that is an allowance. Subject: an effect definition. Value: an allowance definition." .

bhv:usesAllowance a owl:ObjectProperty, owl:FunctionalProperty ; rdfs:domain bhv:EffectDefinition ; rdfs:range bhv:AllowanceDefinition .
bhv:consumesAmount a owl:ObjectProperty, owl:FunctionalProperty ; rdfs:domain bhv:EffectDefinition ; rdfs:range qnt:Quantity .
bhv:allowanceSpace a owl:ObjectProperty, owl:FunctionalProperty ; rdfs:domain bhv:AllowanceDefinition ; rdfs:range qnt:ValueSpace .
bhv:resetRecurrence a owl:ObjectProperty, owl:FunctionalProperty ; rdfs:domain bhv:AllowanceDefinition ; rdfs:range qnt:Recurrence .
bhv:absorptionPolicy a owl:ObjectProperty, owl:FunctionalProperty ; rdfs:domain bhv:AllowanceDefinition ; rdfs:range bhv:AbsorptionPolicy .

[] a owl:AllDisjointClasses ;
	owl:members ( bhv:StateSpace bhv:State bhv:TransitionDefinition bhv:TriggerDefinition bhv:GuardDefinition bhv:EffectDefinition bhv:AllowanceDefinition bhv:SelectionPolicy bhv:ActivationPolicy bhv:TriggerKind bhv:TargetKind bhv:AbsorptionPolicy bhv:OperationalProfile ) .
```

### 5.2 Runtime

`spec/behaviour-runtime.ttl` (version IRI `…/lattice/behaviour-runtime/0.8.0`) imports the
configuration document and declares the other three tiers:

| Tier | Classes | Properties |
|---|---|---|
| occurrence | `Stimulus` | |
| execution | `TransitionExecution`, `EffectApplication` | `executedTransition`, `appliesEffect`, `causedByStimulus`, `usesProfile` |
| state record | `StateOccupancy`, `AllowanceAccount` | `occupiesState`, `forSubject`, `isHypothetical`, `isCurrent`, `tracksAllowance`, `availableBalance` |

`bhv:forSubject` has no range: a state occupancy may be for a role occupancy, an instrument's
persistent identity, a section, a term or an occasion. Where the subject is versioned, the occupancy
is for its persistent identity, so its state outlives a new version (ADR-A106 decision 5). Every
runtime class is disjoint from every other Behaviour class.

## 6. Mechanism vocabulary

```turtle-vocab
@prefix bhv:  <https://www.nebularis.org/neuro-semantic/lattice/behaviour#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@base <https://www.nebularis.org/neuro-semantic/behaviour-vocab> .

<https://www.nebularis.org/neuro-semantic/behaviour-vocab>
	a owl:Ontology ;
	owl:versionIRI <https://www.nebularis.org/neuro-semantic/lattice/behaviour-vocab/0.8.0> ;
	owl:imports <https://www.nebularis.org/neuro-semantic/lattice/behaviour/0.8.0> .

bhv:ExternalStimulus a bhv:TriggerKind .
bhv:ScheduledTrigger a bhv:TriggerKind .
bhv:DerivedTrigger a bhv:TriggerKind .

bhv:SingleMatch a bhv:SelectionPolicy .
bhv:AllMatches a bhv:SelectionPolicy .
bhv:PriorityOrdered a bhv:SelectionPolicy .

bhv:ImmediateActivation a bhv:ActivationPolicy .
bhv:DeferredActivation a bhv:ActivationPolicy .
bhv:ManualActivation a bhv:ActivationPolicy .

bhv:InstrumentTarget a bhv:TargetKind ;
	owl:deprecated true ;
	rdfs:comment "Deprecated in behaviour-vocab 0.8.0. A target kind is declared by the layer that owns the target, so Instrument declares its own (ADR-A104, ADR-A106)." .
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

The target rule is checked without inference: the alternative path names `bhv:targets` and its
sub-properties, so an effect targeting an allowance conforms without a reasoner deriving
`bhv:targets`. Selection and activation policies stay required on every transition (ADR-A09,
ADR-A10, ADR-A106 decision 6).

```turtle-shapes
@prefix sh:   <http://www.w3.org/ns/shacl#> .
@prefix bhv:  <https://www.nebularis.org/neuro-semantic/lattice/behaviour#> .

bhv:TransitionDefinitionShape a sh:NodeShape ;
	sh:targetClass bhv:TransitionDefinition ;
	sh:property [ sh:path bhv:fromState ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path bhv:toState ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path bhv:hasTrigger ; sh:minCount 1 ] ;
	sh:property [ sh:path bhv:selectionPolicy ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path bhv:activationPolicy ; sh:minCount 1 ; sh:maxCount 1 ] .

bhv:EffectDefinitionShape a sh:NodeShape ;
	sh:targetClass bhv:EffectDefinition ;
	sh:property [ sh:path bhv:targetKind ; sh:minCount 1 ; sh:maxCount 1 ;
		sh:message "An effect declares exactly one target kind." ] ;
	sh:property [ sh:path [ sh:alternativePath ( bhv:targets bhv:targetsOccupancy bhv:targetsAllowance ) ] ; sh:minCount 1 ;
		sh:message "An effect names at least one target, through bhv:targets or one of its sub-properties." ] .

bhv:AllowanceDefinitionShape a sh:NodeShape ;
	sh:targetClass bhv:AllowanceDefinition ;
	sh:property [ sh:path bhv:allowanceSpace ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path bhv:absorptionPolicy ; sh:minCount 1 ; sh:maxCount 1 ] .

bhv:AllowanceAccountShape a sh:NodeShape ;
	sh:targetClass bhv:AllowanceAccount ;
	sh:property [ sh:path bhv:tracksAllowance ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path bhv:availableBalance ; sh:minCount 1 ; sh:maxCount 1 ] .
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

## 10. Release notes

Breaking versions at major version zero ([ADR-A113](../../docs/architecture/decisions/ADR-A113-breaking-changes-at-major-version-zero.md)):

- 0.8.0 (breaking): Behaviour no longer imports Instrument, and moves below it. `bhv:targetsElement`
  is replaced by `bhv:targets`, with no range. `bhv:forSubject` loses its range. A transition needs
  no effect. The occurrence, execution and state record tiers move to `behaviour-runtime` 0.8.0.
  `bhv:InstrumentTarget` is deprecated. ADR-A106.
