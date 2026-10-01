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
	owl:versionIRI <https://www.nebularis.org/neuro-semantic/lattice/behaviour/0.9.0> ;
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

bhv:initialState a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain bhv:StateSpace ; rdfs:range bhv:State ;
	rdfs:comment "The state a subject is in when it takes effect, before any transition. Subject: a state space. Value: one of its own states, at most one." ;
	fnd:utility "An occupancy of the initial state needs no transition execution: it carries evidence of the subject taking effect (law B6). Nested states reuse this property for a composite state's initial sub-state." .
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

`spec/behaviour-runtime.ttl` (version IRI `…/lattice/behaviour-runtime/0.9.0`) imports the
configuration document and declares the other three tiers:

| Tier | Classes | Properties |
|---|---|---|
| occurrence | `Stimulus`, `Occasion`, and the records below | `occasionOf`, `forCase`, `occasionParty`, `fromStimulus`, `actor` |
| execution | `TransitionExecution`, `EffectApplication` | `executedTransition`, `appliesEffect`, `causedByStimulus`, `usesProfile` |
| state record | `StateOccupancy`, `AllowanceAccount` | `occupiesState`, `forSubject`, `enteredBy`, `isHypothetical`, `isCurrent`, `tracksAllowance`, `availableBalance` |

`bhv:forSubject` has no range: a state occupancy may be for a role occupancy, an instrument's
persistent identity, a section, a term or an occasion. Where the subject is versioned, the occupancy
is for its persistent identity, so its state outlives a new version (ADR-A106 decision 5). Every
runtime class is disjoint from every other Behaviour class.

**Occasions.** An occasion is one declaration (a legal relation, in practice) applied to one case.
`bhv:occasionOf` and `bhv:forCase` have no range, so Behaviour names nothing of the layer that
declares the relation. Its parties are role occupancy versions, fixed when it arises: a later version
of a party's occupancy does not change them (law I11). Its states are `bhv:OccasionStates` (§6).

**Records.** Each record is a `bhv:Record`, evidenced and temporally scoped: it carries a
`fnd:Evidence` (when it was recorded, and by whom when it is asserted) and a `fnd:TemporalScope` (its
valid time). It points at what it is about through properties with no range.

| Record | Records | Carries |
|---|---|---|
| `bhv:ActRecord` | an act of an activity by an actor for a case | `activity`, `actor`, `forCase` |
| `bhv:BreachRecord` | a breach of an occasion, derived or asserted by an adjudicator | `ofOccasion`, `closureReliedOn` |
| `bhv:ExerciseRecord` | an exercise of a power, whether or not it took effect | `exercised`, `actor`, `tookEffect`, `reasonNotTaken` |
| `bhv:DeterminationRecord` | a determination by the party a contract names | `matter`, `determiner`, `determinedValue` |
| `bhv:DeemedFactRecord` | a fact taken to hold by a deeming | `deeming`, `conditionSatisfied` |
| `bhv:AcceptanceRecord` | a party's acceptance of a version | `accepted`, `actor` |

**Every state entry is recorded** (law B6). An occupancy names the execution that entered it
(`bhv:enteredBy`), which names its stimulus, or carries evidence: of the subject taking effect when
it occupies its space's initial state, of an external log entry otherwise. An occupancy of an
occasion state is a derived artefact (law B1), `prov:wasDerivedFrom` the records it rests on.

## 6. Mechanism vocabulary

```turtle-vocab
@prefix bhv:  <https://www.nebularis.org/neuro-semantic/lattice/behaviour#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix fnd:  <https://www.nebularis.org/neuro-semantic/lattice/foundation#> .
@base <https://www.nebularis.org/neuro-semantic/behaviour-vocab> .

<https://www.nebularis.org/neuro-semantic/behaviour-vocab>
	a owl:Ontology ;
	owl:versionIRI <https://www.nebularis.org/neuro-semantic/lattice/behaviour-vocab/0.9.0> ;
	owl:imports <https://www.nebularis.org/neuro-semantic/lattice/behaviour/0.9.0> .

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

# ---- The occasion state space: a fixed core, refined by sub-states ----------
# Its transitions are the runtime evaluator's, derived from the legal
# algorithms and protected by law I7, so they are not declared here. A
# deployment refines a core state with sub-states of its own and adds parallel
# regimes, never a new state of this space (CCS C11-Q1).

bhv:OccasionStates a bhv:StateSpace ;
	fnd:hasIdentity bhv:OccasionStates-identity ;
	bhv:initialState bhv:Pending ;
	rdfs:label "Occasion states"@en ;
	rdfs:comment "The states of an occasion: one legal relation applied to one case." .

bhv:Pending a bhv:State ; bhv:inStateSpace bhv:OccasionStates ;
	rdfs:label "Pending"@en ;
	rdfs:comment "The relation applies to the case, and has not yet arisen. The initial state. The evaluator's." .
bhv:Arisen a bhv:State ; bhv:inStateSpace bhv:OccasionStates ;
	rdfs:label "Arisen"@en ;
	rdfs:comment "The relation has arisen for the case and is live. The evaluator's." .
bhv:Performed a bhv:State ; bhv:inStateSpace bhv:OccasionStates ;
	rdfs:label "Performed"@en ;
	rdfs:comment "The relation has been fulfilled for the case. The evaluator's." .
bhv:Breached a bhv:State ; bhv:inStateSpace bhv:OccasionStates ;
	rdfs:label "Breached"@en ;
	rdfs:comment "The relation has been breached for the case, as derived or as asserted by an adjudicator. The evaluator's." .
bhv:Ended a bhv:State ; bhv:inStateSpace bhv:OccasionStates ;
	rdfs:label "Ended"@en ;
	rdfs:comment "The relation ended for the case without being performed or breached. The evaluator's." .
bhv:Suspended a bhv:State ; bhv:inStateSpace bhv:OccasionStates ;
	rdfs:label "Suspended"@en ;
	rdfs:comment "The relation is suspended for the case, from Pending or Arisen, and resumes its prior state on reinstatement (law B5). The evaluator's." .
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

`shapes/constraints.ttl` adds the checks that need SPARQL: an initial state belongs to its own
space, and an occupancy of an occasion state is derived from a record (law B1). The target rule is checked without inference: the alternative path names `bhv:targets` and its
sub-properties, so an effect targeting an allowance conforms without a reasoner deriving
`bhv:targets`. Selection and activation policies stay required on every transition (ADR-A09,
ADR-A10, ADR-A106 decision 6).

```turtle-shapes
@prefix sh:   <http://www.w3.org/ns/shacl#> .
@prefix bhv:  <https://www.nebularis.org/neuro-semantic/lattice/behaviour#> .
@prefix pty:  <https://www.nebularis.org/neuro-semantic/lattice/party#> .
@prefix fnd:  <https://www.nebularis.org/neuro-semantic/lattice/foundation#> .
@prefix elg:  <https://www.nebularis.org/neuro-semantic/lattice/eligibility#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

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

bhv:InitialStateShape a sh:NodeShape ;
	sh:targetClass bhv:StateSpace ;
	sh:property [ sh:path bhv:initialState ; sh:maxCount 1 ; sh:class bhv:State ;
		sh:message "A state space has at most one initial state." ] .

# ---- B6: every state entry is recorded ---------------------------------------

bhv:StateEntryRecordedShape a sh:NodeShape ;
	sh:targetClass bhv:StateOccupancy ;
	sh:or (
		[ sh:path bhv:enteredBy ; sh:minCount 1 ]
		[ sh:path fnd:hasEvidence ; sh:minCount 1 ]
	) ;
	sh:message "A state occupancy names the execution that entered it, or carries evidence (law B6)." ;
	sh:property [ sh:path bhv:enteredBy ; sh:maxCount 1 ; sh:class bhv:TransitionExecution ;
		sh:node [ sh:property [ sh:path bhv:causedByStimulus ; sh:minCount 1 ;
			sh:message "An execution that entered a state names the stimulus that caused it (law B6)." ] ] ] .

bhv:EnteredBySubjectShape a sh:NodeShape ;
	sh:targetSubjectsOf bhv:enteredBy ;
	sh:class bhv:StateOccupancy ;
	sh:message "Only a state occupancy is entered by an execution." .

# ---- Occasions, with parties fixed at arising (I11) -------------------------------

bhv:OccasionSubjectShape a sh:NodeShape ;
	sh:targetSubjectsOf bhv:occasionOf , bhv:occasionParty ;
	sh:class bhv:Occasion ;
	sh:message "Only an occasion applies a declaration or has occasion parties." .

bhv:ForCaseSubjectShape a sh:NodeShape ;
	sh:targetSubjectsOf bhv:forCase ;
	sh:or ( [ sh:class bhv:Occasion ] [ sh:class bhv:ActRecord ] ) ;
	sh:message "Only an occasion or an act record is for a case." .

bhv:OccasionShape a sh:NodeShape ;
	sh:targetClass bhv:Occasion ;
	sh:property [ sh:path bhv:occasionOf ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path bhv:forCase ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path bhv:occasionParty ; sh:class pty:RoleOccupancy ;
		sh:not [ sh:class fnd:PersistentIdentity ] ;
		sh:message "An occasion's parties are role occupancy versions, fixed at arising, never persistent identities (law I11)." ] .

# ---- Records ----------------------------------------------------------------------

bhv:RecordSubjectShape a sh:NodeShape ;
	sh:targetSubjectsOf bhv:fromStimulus , bhv:actor ;
	sh:class bhv:Record ;
	sh:message "Only a record comes from a stimulus or names an actor." .

bhv:RecordShape a sh:NodeShape ;
	sh:targetClass bhv:Record ;
	sh:property [ sh:path bhv:fromStimulus ; sh:maxCount 1 ; sh:class bhv:Stimulus ] ;
	sh:property [ sh:path bhv:actor ; sh:class pty:RoleOccupancy ] .

bhv:ActRecordSubjectShape a sh:NodeShape ;
	sh:targetSubjectsOf bhv:activity ; sh:class bhv:ActRecord ;
	sh:message "Only an act record names an activity." .
bhv:ActRecordShape a sh:NodeShape ;
	sh:targetClass bhv:ActRecord ;
	sh:property [ sh:path bhv:activity ; sh:minCount 1 ; sh:maxCount 1 ; sh:nodeKind sh:IRI ] ;
	sh:property [ sh:path bhv:forCase ; sh:minCount 1 ; sh:maxCount 1 ] .

bhv:BreachRecordSubjectShape a sh:NodeShape ;
	sh:targetSubjectsOf bhv:ofOccasion , bhv:closureReliedOn ; sh:class bhv:BreachRecord ;
	sh:message "Only a breach record names an occasion or a closure relied on." .
bhv:BreachRecordShape a sh:NodeShape ;
	sh:targetClass bhv:BreachRecord ;
	sh:property [ sh:path bhv:ofOccasion ; sh:minCount 1 ; sh:maxCount 1 ; sh:class bhv:Occasion ] .

bhv:ExerciseRecordSubjectShape a sh:NodeShape ;
	sh:targetSubjectsOf bhv:exercised , bhv:tookEffect , bhv:reasonNotTaken ; sh:class bhv:ExerciseRecord ;
	sh:message "Only an exercise record names what was exercised and whether it took effect." .
bhv:ExerciseRecordShape a sh:NodeShape ;
	sh:targetClass bhv:ExerciseRecord ;
	sh:property [ sh:path bhv:exercised ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path bhv:tookEffect ; sh:minCount 1 ; sh:maxCount 1 ; sh:datatype xsd:boolean ] ;
	sh:property [ sh:path bhv:reasonNotTaken ; sh:maxCount 1 ; sh:datatype xsd:string ] .

bhv:DeterminationRecordSubjectShape a sh:NodeShape ;
	sh:targetSubjectsOf bhv:matter , bhv:determiner , bhv:determinedValue ; sh:class bhv:DeterminationRecord ;
	sh:message "Only a determination record names a matter, a determiner or a determined value." .
bhv:DeterminationRecordShape a sh:NodeShape ;
	sh:targetClass bhv:DeterminationRecord ;
	sh:property [ sh:path bhv:matter ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path bhv:determiner ; sh:minCount 1 ; sh:maxCount 1 ; sh:class pty:RoleOccupancy ] ;
	sh:property [ sh:path bhv:determinedValue ; sh:minCount 1 ] .

bhv:DeemedFactRecordSubjectShape a sh:NodeShape ;
	sh:targetSubjectsOf bhv:deeming , bhv:conditionSatisfied ; sh:class bhv:DeemedFactRecord ;
	sh:message "Only a deemed-fact record names a deeming or the condition satisfied." .
bhv:DeemedFactRecordShape a sh:NodeShape ;
	sh:targetClass bhv:DeemedFactRecord ;
	sh:property [ sh:path bhv:deeming ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path bhv:conditionSatisfied ; sh:maxCount 1 ; sh:class elg:Condition ] .

bhv:AcceptanceRecordSubjectShape a sh:NodeShape ;
	sh:targetSubjectsOf bhv:accepted ; sh:class bhv:AcceptanceRecord ;
	sh:message "Only an acceptance record names a version accepted." .
bhv:AcceptanceRecordShape a sh:NodeShape ;
	sh:targetClass bhv:AcceptanceRecord ;
	sh:property [ sh:path bhv:accepted ; sh:minCount 1 ; sh:maxCount 1 ; sh:class fnd:Version ] ;
	sh:property [ sh:path bhv:actor ; sh:minCount 1 ] .
```

## 9. Worked examples

Examples are authored in:

- `ontology/behaviour/examples/state-transition.ttl`
- `ontology/behaviour/examples/sequential-allowance.ttl`
- `ontology/behaviour/examples/adverse-event-occasion.ttl`: an occasion of a reporting duty that
  arises on an event and is breached when its window closes, each state derived from its record
- `ontology/behaviour/examples/licence-suspension.ttl`: a state space with an initial state, exercise
  records that took effect and one that did not, and acceptance, determination and deemed-fact
  records

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
- 0.9.0: occasions, records and `bhv:initialState` added (`behaviour` and `behaviour-runtime` 0.9.0,
  additive). Shapes 0.3.0 (breaking): every state occupancy must name the execution that entered it
  or carry evidence (law B6), and an occasion's parties must be role occupancy versions (law I11).
  ADR-A106.
