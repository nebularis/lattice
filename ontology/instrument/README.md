<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Instrument Ontology — Minimal Governing Document Shape

Literate specification for the Instrument layer.

---

## 1. Purpose and Scope

Instrument provides the minimal document-structure model required by Behaviour and Party integration: `Element`, `Provision`, `Obligation`, and `Qualifier`.

It imports Foundation, Vocabulary, Quantification, Party, and Eligibility.

## 2. Namespace and Prefixes

```turtle-spec
@prefix ins:  <https://www.nebularis.org/neuro-semantic/lattice/instrument#> .
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

- `turtle-spec` blocks generate `spec/instrument.ttl`.
- `turtle-vocab` blocks generate `vocab/instrument-vocab.ttl`.
- `turtle-shapes` blocks generate `shapes/*.ttl`.
- `turtle-example` blocks are illustrative only.

## 4. Core Model

```turtle-spec
@base <https://www.nebularis.org/neuro-semantic/instrument> .

<https://www.nebularis.org/neuro-semantic/instrument>
	rdf:type owl:Ontology ;
	owl:versionIRI <https://www.nebularis.org/neuro-semantic/lattice/instrument/0.3.0> ;
	owl:imports <https://www.nebularis.org/neuro-semantic/lattice/foundation/0.2.0> ,
				<https://www.nebularis.org/neuro-semantic/lattice/vocabulary/0.2.0> ,
				<https://www.nebularis.org/neuro-semantic/lattice/quantification/0.3.0> ,
				<https://www.nebularis.org/neuro-semantic/lattice/party/0.3.0> ,
				<https://www.nebularis.org/neuro-semantic/lattice/eligibility/0.3.0> .

ins:Element a owl:Class ;
	rdfs:subClassOf fnd:Version ;
	rdfs:comment "A versioned instrument element." .

ins:Provision a owl:Class ;
	rdfs:subClassOf ins:Element ;
	rdfs:comment "A structural provision grouping obligations." .

ins:Obligation a owl:Class ;
	rdfs:subClassOf ins:Element ;
	rdfs:comment "A versioned obligation element." .

ins:Qualifier a owl:Class ;
	rdfs:subClassOf ins:Element ;
	rdfs:comment "A qualifier constraining or refining another element." .

[] a owl:AllDisjointClasses ;
	owl:members ( ins:Provision ins:Obligation ins:Qualifier ) .

ins:hasProvision a owl:ObjectProperty ;
	rdfs:domain ins:Element ;
	rdfs:range ins:Provision .

ins:partOfInstrument a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain ins:Provision ;
	rdfs:range ins:Element ;
	owl:inverseOf ins:hasProvision .

ins:hasObligation a owl:ObjectProperty ;
	rdfs:domain ins:Provision ;
	rdfs:range ins:Obligation .

ins:inProvision a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain ins:Obligation ;
	rdfs:range ins:Provision ;
	owl:inverseOf ins:hasObligation .

ins:hasQualifier a owl:ObjectProperty ;
	rdfs:domain ins:Element ;
	rdfs:range ins:Qualifier .

ins:qualifies a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain ins:Qualifier ;
	rdfs:range ins:Element ;
	owl:inverseOf ins:hasQualifier .

ins:hasCondition a owl:ObjectProperty ;
	rdfs:domain ins:Element ;
	rdfs:range elg:Condition .

ins:fulfilledBy a owl:ObjectProperty ;
	rdfs:domain ins:Obligation ;
	rdfs:range pty:ParticipationGroup .

ins:obligor a owl:ObjectProperty ;
	rdfs:domain ins:Obligation ;
	rdfs:range pty:RoleOccupancy .

ins:obligee a owl:ObjectProperty ;
	rdfs:domain ins:Obligation ;
	rdfs:range pty:RoleOccupancy .
```

## 5. Versioning and Supersession Contract

Instrument uses Foundation versioning without in-place mutation.

- Every `ins:Element` instance is a `fnd:Version` and therefore has one `fnd:hasIdentity`.
- Any material change creates a new version and links the old version via `fnd:supersededBy`.
- Supersession is valid only for versions sharing the same `fnd:hasIdentity`.

## 6. Mechanism Vocabulary

```turtle-vocab
@prefix ins:  <https://www.nebularis.org/neuro-semantic/lattice/instrument#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@base <https://www.nebularis.org/neuro-semantic/instrument-vocab> .

<https://www.nebularis.org/neuro-semantic/instrument-vocab>
	a owl:Ontology ;
	owl:versionIRI <https://www.nebularis.org/neuro-semantic/lattice/instrument-vocab/0.3.0> ;
	owl:imports <https://www.nebularis.org/neuro-semantic/lattice/instrument/0.3.0> .
```

## 7. Shapes

```turtle-shapes
@prefix sh:   <http://www.w3.org/ns/shacl#> .
@prefix ins:  <https://www.nebularis.org/neuro-semantic/lattice/instrument#> .
@prefix fnd:  <https://www.nebularis.org/neuro-semantic/lattice/foundation#> .

ins:ElementShape a sh:NodeShape ;
	sh:targetClass ins:Element ;
	sh:property [ sh:path fnd:hasIdentity ; sh:minCount 1 ; sh:maxCount 1 ] .

ins:ProvisionShape a sh:NodeShape ;
	sh:targetClass ins:Provision ;
	sh:property [ sh:path ins:hasObligation ; sh:minCount 1 ] .

ins:ObligationShape a sh:NodeShape ;
	sh:targetClass ins:Obligation ;
	sh:property [ sh:path ins:obligor ; sh:minCount 1 ] ;
	sh:property [ sh:path ins:obligee ; sh:minCount 1 ] .
```
