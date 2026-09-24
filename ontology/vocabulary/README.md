<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Vocabulary Ontology — Description Logic Elements

*Literate specification, following the same convention established in `ontology/foundation/spec/foundation.md` — see [§3](#3-how-to-read-this-document) if this is the first layer document you're reading.*

---

## 1. Purpose and Scope

Vocabulary provides a governed mechanism by which external, domain-specific concept schemes get bound into every other layer's concept-valued properties without those layers' own specifications ever naming a domain concept directly. 

`vocab/` folders elsewhere in this repository hold small, mechanism-intrinsic enumerations (trigger kind, role type); actual business vocabularies — product codes, jurisdiction lists, currency schemes, etc — are supplied entirely by whoever builds on LATTICE, and never appear in this repository at all.

Vocabulary builds on W3C SKOS rather than reinventing concept-scheme modelling, adding governed versioning of a scheme as a whole, a structural contract mechanism for binding a property to a scheme without either side knowing about the other in advance, and scoped, time-bounded bindings for where the scheme in use differs between contexts or changes over time.

What Vocabulary does *not* do is resolve a fuzzy label to a concept - it defines what a *valid* binding looks like structurally, but has nothing to say about how one was arrived at.

## 2. Namespace and Prefixes

Same base and per-layer convention established in Foundation:

```
https://www.nebularis.org/neuro-semantic/lattice/
```

This document uses:

```turtle-spec
@prefix voc:  <https://www.nebularis.org/neuro-semantic/lattice/vocabulary#> .
@prefix fnd:  <https://www.nebularis.org/neuro-semantic/lattice/foundation#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
```

## 3. How to Read This Document

Same template and same two-tag extraction convention as Foundation's document: genuine specification content is fenced ` ```turtle-spec `; illustration (the worked example in §9) is fenced ` ```turtle-example ` and is never part of the extraction. Concatenate the prefix block above with every ` ```turtle-spec ` block from §5 onward, in document order, to produce `spec/vocabulary.ttl`.

One small refinement versus Foundation's document, worth naming since consistency across layer documents matters: **§8 (Alignments) is the only place a relationship to an external vocabulary — here, SKOS — is asserted.** Foundation's document states `fnd:Evidence rdfs:subClassOf prov:Entity` both inline in the class's own block (§6) and again in its Alignments section (§8) — harmless, since duplicate triples collapse in RDF's set semantics, but untidy. This document doesn't repeat that pattern: `voc:ConceptScheme`'s block in §6 declares only its LATTICE-internal parentage (`fnd:Version`, `fnd:Governable`); its SKOS parentage is stated once, in §8. Worth tidying Foundation's document to match at some point — noted in [§11](#11-open-items).

## 4. Design Decisions

**Scheme-level versioning through Foundation. Concept-level versioning explicitly out of scope.** A `ConceptScheme` is a `fnd:Version` — it has identity, and one version of a scheme can supersede another. An individual `skos:Concept` does not get its own independent version thread here. Tracking how a specific concept's meaning drifts or splits across scheme versions is a cross-version alignment problem that we do not address in this ontology.

**`SchemeContract` is structural only — it never encodes what a scheme is *about*.** This is the decision most worth reading carefully. `SchemeContract` therefore constrains only in structural, governance terms — which property, which scheme, what governance state that scheme must hold. What the scheme is *about* is communicated in prose, by whichever domain ontologies extend the framework.

**Concept-level constraints are out of scope for this pass.** Excluding deprecated concepts, requiring leaf concepts with no narrower terms, and similar refinements are plausible future extensions to `SchemeContract`. Left out here deliberately, the same way Foundation left OWL-Time alignment out — real complexity for a requirement not yet demonstrated.

**Scoped, time-bounded binding is a separate construct; `boundScheme` remains the unscoped default.** `boundScheme` gives a contract one binding, everywhere, indefinitely. That is enough for a single deployment, and it stays unchanged. Three requirements need more. First, one deployment can serve contexts in which the same property must draw on different schemes, so a binding needs a scope. Second, replacing a binding in place silently changes what previously recorded concept values meant, so a binding needs a validity period, and a versioned record needs a way to state which binding it was resolved under. Third, `boundScheme` is functional, so asserting a second value is read by a reasoner as the two schemes being the same individual rather than as a conflict — more than one binding therefore has to be expressed as more than one node, not more than one value. `SchemeBinding` meets all three by reifying the binding. Its scopes are opaque to this layer, in the same way `SchemeContract` never encodes what a scheme is about: Vocabulary states *that* a binding applies within a named scope, never what the scope means or how membership of it is decided. A binding naming several scopes applies only where all of them hold; alternatives are expressed as separate bindings. A contract's `requiresGovernanceState` applies to a scheme however it is bound. `resolvedUnder` states no domain because the records that need it live in the layers above this one, and Vocabulary does not reach upward to name them.

**Resolution precedence is stated here, and not axiomatised.** For a value resolved in a given context at a given time, a `SchemeBinding` is applicable when every scope it names holds in that context and the time falls within its temporal scope. Among applicable bindings for one contract, a binding whose scopes are a strict superset of another's takes precedence. If more than one binding remains, the bindings conflict, which is a governance error rather than a choice to be made silently. If no binding applies, `boundScheme` is used where present. A `SchemeBinding` naming no scope is the time-bounded counterpart of `boundScheme`, and where both exist for one contract they must name the same scheme. Checking these conditions needs whole-graph comparison, so it belongs in SHACL-SPARQL rather than in OWL.

## 5. Annotation Properties

None.

## 6. Classes

#### `voc:ConceptScheme`

**Definition.** A published, identified, governed collection of concepts.

**Utility.** A published, versioned, governed collection of concepts. Use `fnd:hasIdentity` and `fnd:supersededBy` to track successive editions of the same scheme over time, and `fnd:hasGovernanceState` to record whether a given edition is in draft, under review, active, or superseded.

```turtle-spec
voc:ConceptScheme a owl:Class ;
    rdfs:subClassOf fnd:Version, fnd:Governable ;
    rdfs:comment "A published, identified, governed collection of concepts." ;
    fnd:utility "A published, versioned, governed collection of concepts. Use fnd:hasIdentity and fnd:supersededBy to track successive editions of the same scheme over time, and fnd:hasGovernanceState to record its review status." .
```

#### `voc:SchemeContract`

**Definition.** A declared requirement binding a property, defined in some other layer, to concepts drawn from a conformant scheme.

**Utility.** Author one of these when a property should take concept values, but you don't yet know, or don't want to fix, which scheme those concepts will come from. Set `constrainsProperty` to name the property, `requiresGovernanceState` if the eventual scheme must be in a specific status, and leave `boundScheme` empty until an implementation supplies one.

```turtle-spec
voc:SchemeContract a owl:Class ;
    rdfs:subClassOf fnd:Version, fnd:Governable ;
    rdfs:comment "A declared requirement binding a property, defined in some other layer, to concepts drawn from a conformant scheme." ;
    fnd:utility "Author one of these when a property should take concept values but you don't yet know which scheme those concepts will come from. Set constrainsProperty to name the property, requiresGovernanceState if needed, and leave boundScheme empty until an implementation supplies one." ;
    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty voc:constrainsProperty ;
        owl:minCardinality "1"^^xsd:nonNegativeInteger
    ] .
```

#### `voc:SchemeBinding`

**Definition.** A statement that a scheme contract is satisfied by a specific concept scheme, within zero or more named scopes, for a stated period.

**Utility.** Author one of these when a contract's scheme differs between contexts, or when the scheme in force must change over time without altering what earlier values meant. Set `forContract` to the contract, `bindsScheme` to the specific scheme edition, `bindingScope` to each scope within which the binding applies (leave it unset for a binding that applies everywhere), and a temporal scope stating when the binding is in force. To change the scheme a context uses, end the old binding's validity and add a new binding, rather than editing the old one.

```turtle-spec
voc:SchemeBinding a owl:Class ;
    rdfs:subClassOf fnd:TemporallyScoped ;
    rdfs:comment "A statement that a scheme contract is satisfied by a specific concept scheme, within zero or more named scopes, for a stated period." ;
    fnd:utility "Author one of these when a contract's scheme differs between contexts or must change over time. Set forContract, bindsScheme (a specific scheme edition), bindingScope for each scope it applies within (none means everywhere), and a temporal scope. To change the scheme in use, end this binding's validity and add a new one rather than editing it." ;
    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty voc:forContract ;
        owl:cardinality "1"^^xsd:nonNegativeInteger
    ] , [
        a owl:Restriction ;
        owl:onProperty voc:bindsScheme ;
        owl:cardinality "1"^^xsd:nonNegativeInteger
    ] .
```

#### `voc:BindingScope`

**Definition.** A declared context within which a scheme binding applies.

**Utility.** Declare one for each context in which bindings may differ — a deployment, a tenant, a jurisdiction, a product, or any other division an implementation draws. Vocabulary ships no scope individuals and says nothing about how an implementation decides which scopes hold for a given value; an implementation may also type its scopes as concepts in a scheme of its own.

```turtle-spec
voc:BindingScope a owl:Class ;
    rdfs:comment "A declared context within which a scheme binding applies." ;
    fnd:utility "Declare one for each context in which bindings may differ, such as a deployment, tenant, jurisdiction or product. Vocabulary ships no scope individuals and does not decide which scopes hold for a given value." .
```

### Disjointness

```turtle-spec
[] a owl:AllDisjointClasses ;
    owl:members ( voc:ConceptScheme voc:SchemeContract voc:SchemeBinding voc:BindingScope ) .
```

**Utility.** A collection of concepts, a declared requirement about a property, a statement satisfying that requirement, and a context are categorically different kinds of thing; nothing should ever be classified as more than one of them.

## 7. Object Properties

#### `voc:constrainsProperty`

**Definition.** The property, declared in another layer, that this contract governs.

**Utility.** Names the property a SchemeContract governs. Point this at whichever property, in whatever layer, needs its values to come from a conformant concept scheme.

```turtle-spec
voc:constrainsProperty a owl:ObjectProperty ;
    rdfs:domain voc:SchemeContract ;
    rdfs:range rdf:Property ;
    rdfs:comment "The property, declared in another layer, that this contract governs." ;
    fnd:utility "Names the property a SchemeContract governs. Point this at whichever property needs its values to come from a conformant concept scheme." .
```

#### `voc:requiresGovernanceState`

**Definition.** A governance state the bound scheme must currently hold for this contract to be considered satisfied.

**Utility.** States which governance state or states the bound scheme must currently hold. If you give more than one value, any single one is sufficient. Leave this unset if the contract does not care about governance status.

```turtle-spec
voc:requiresGovernanceState a owl:ObjectProperty ;
    rdfs:domain voc:SchemeContract ;
    rdfs:range fnd:GovernanceState ;
    rdfs:comment "A governance state the bound scheme must currently hold for this contract to be considered satisfied." ;
    fnd:utility "States which governance state(s) the bound scheme must currently hold — any one value given is sufficient if more than one is stated. Leave unset if the contract doesn't care about governance status at all." .
```

#### `voc:boundScheme`

**Definition.** The concrete scheme a downstream implementation has bound to satisfy this contract, if one has been bound yet.

**Utility.** Points a SchemeContract at the concrete scheme that satisfies it, once one has been chosen. Leave this unset until an implementation actually supplies a scheme.

```turtle-spec
voc:boundScheme a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain voc:SchemeContract ;
    rdfs:range voc:ConceptScheme ;
    rdfs:comment "The concrete scheme a downstream implementation has bound to satisfy this contract, if one has been bound yet." ;
    fnd:utility "Points a SchemeContract at the concrete scheme that satisfies it, once one has been chosen. Leave this unset until an implementation supplies a scheme." .
```

#### `voc:forContract`

**Definition.** The scheme contract a scheme binding satisfies.

**Utility.** Names the contract a SchemeBinding satisfies. Every binding names exactly one contract; a contract may have any number of bindings.

```turtle-spec
voc:forContract a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain voc:SchemeBinding ;
    rdfs:range voc:SchemeContract ;
    rdfs:comment "The scheme contract a scheme binding satisfies." ;
    fnd:utility "Names the contract a SchemeBinding satisfies. Every binding names exactly one contract; a contract may have any number of bindings." .
```

#### `voc:bindsScheme`

**Definition.** The concept scheme a scheme binding supplies.

**Utility.** Points a SchemeBinding at the specific scheme edition it supplies. Point at the edition itself — the `ConceptScheme` version — so that what the binding means does not change when a later edition of the same scheme is published.

```turtle-spec
voc:bindsScheme a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain voc:SchemeBinding ;
    rdfs:range voc:ConceptScheme ;
    rdfs:comment "The concept scheme a scheme binding supplies." ;
    fnd:utility "Points a SchemeBinding at the specific scheme edition it supplies. Point at the edition itself, the ConceptScheme version, so the binding keeps its meaning when a later edition of the same scheme is published." .
```

#### `voc:bindingScope`

**Definition.** A scope within which a scheme binding applies.

**Utility.** Names a scope within which a SchemeBinding applies. Give several values where the binding applies only where all of them hold; express alternatives as separate bindings. Leave it unset for a binding that applies in every scope.

```turtle-spec
voc:bindingScope a owl:ObjectProperty ;
    rdfs:domain voc:SchemeBinding ;
    rdfs:range voc:BindingScope ;
    rdfs:comment "A scope within which a scheme binding applies." ;
    fnd:utility "Names a scope within which a SchemeBinding applies. Several values mean the binding applies only where all of them hold; express alternatives as separate bindings. Leave unset for a binding that applies in every scope." .
```

#### `voc:resolvedUnder`

**Definition.** A scheme binding in force when a record's concept values were resolved.

**Utility.** Records, on any versioned record in any layer, which binding its concept values were drawn under, so their meaning can be recovered after bindings or scheme editions change. Give one value per contract the record draws on.

```turtle-spec
voc:resolvedUnder a owl:ObjectProperty ;
    rdfs:range voc:SchemeBinding ;
    rdfs:comment "A scheme binding in force when a record's concept values were resolved." ;
    fnd:utility "Records, on any versioned record in any layer, which SchemeBinding its concept values were drawn under, so their meaning survives later changes to bindings or scheme editions. Give one value per contract the record draws on." .
```

## 8. Alignments

```turtle-spec
voc:ConceptScheme rdfs:subClassOf skos:ConceptScheme .
voc:ConceptScheme owl:disjointWith skos:Concept .
```

**Utility.** A `voc:ConceptScheme` is a specialised, governed `skos:ConceptScheme`, not a separate or competing kind of thing. Nothing should be classified as both a scheme and a concept at once.

## 9. Worked Micro-Example

Illustration only. `ins:hasPerilType` isn't defined here — it belongs to Instrument, and appears only to show how a contract would attach to it. `fnd:Active` is a forward reference to a named individual Foundation's own document leaves as an open item (`vocab/foundation-vocab.ttl`), not yet declared anywhere in this repository.

```turtle-example
# Illustrative only — ins: and ex: are not part of Vocabulary's own namespace.

# Authored once, as part of ins:hasPerilType's own definition in Instrument's layer.
# No scheme exists yet, and none is required to exist for this to be valid.
ex:peril-contract
    a voc:SchemeContract ;
    voc:constrainsProperty ins:hasPerilType ;
    voc:requiresGovernanceState fnd:Active .

# Bound later, separately, by a specific downstream implementation —
# this triple could be added months after the one above, by a different party.
ex:acme-peril-codes-v2
    a voc:ConceptScheme ;
    fnd:hasIdentity ex:acme-peril-codes-identity ;
    fnd:hasGovernanceState fnd:Active .

ex:peril-contract voc:boundScheme ex:acme-peril-codes-v2 .
```

`ins:hasPerilType` itself is never mentioned anywhere in this document's own specification content — only in this illustration. The contract mechanism constrains the property without Vocabulary needing to know, or ever encode, what the property is about.

A second illustration shows scoped, time-bounded binding. An organisation classifies roles into job families. Its two regional deployments use different job-family schemes, and one region adopts a new edition part-way through the year. `ex:hasJobFamily` is again not part of Vocabulary.

```turtle-example
# Illustrative only — ex: is not part of Vocabulary's own namespace.

ex:job-family-contract
    a voc:SchemeContract ;
    voc:constrainsProperty ex:hasJobFamily ;
    voc:requiresGovernanceState fnd:Active .

ex:region-north a voc:BindingScope .
ex:region-south a voc:BindingScope .

# North used edition 1 until the end of June, then edition 2.
ex:north-binding-2026a
    a voc:SchemeBinding ;
    voc:forContract ex:job-family-contract ;
    voc:bindsScheme ex:north-job-families-v1 ;
    voc:bindingScope ex:region-north ;
    fnd:hasTemporalScope [
        a fnd:TemporalScope ;
        fnd:validFrom "2026-01-01T00:00:00Z"^^xsd:dateTime ;
        fnd:validTo   "2026-07-01T00:00:00Z"^^xsd:dateTime
    ] .

ex:north-binding-2026b
    a voc:SchemeBinding ;
    voc:forContract ex:job-family-contract ;
    voc:bindsScheme ex:north-job-families-v2 ;
    voc:bindingScope ex:region-north ;
    fnd:hasTemporalScope [
        a fnd:TemporalScope ;
        fnd:validFrom "2026-07-01T00:00:00Z"^^xsd:dateTime
    ] .

ex:south-binding
    a voc:SchemeBinding ;
    voc:forContract ex:job-family-contract ;
    voc:bindsScheme ex:south-job-families-v1 ;
    voc:bindingScope ex:region-south ;
    fnd:hasTemporalScope [
        a fnd:TemporalScope ;
        fnd:validFrom "2026-01-01T00:00:00Z"^^xsd:dateTime
    ] .

# An offer letter issued in the north in March keeps edition 1's meaning,
# even though the north now binds edition 2.
ex:offer-letter-117-v1 voc:resolvedUnder ex:north-binding-2026a .
```

No binding here names a scope the other lacks, so precedence never arises. Had a deployment added a binding scoped to both `ex:region-north` and a further scope, that binding would take precedence within the narrower context, per §4.

## 10. Axiom Index

| Term | Kind | Key characteristics |
|---|---|---|
| `voc:ConceptScheme` | Class | subClassOf `fnd:Version`, `fnd:Governable`, `skos:ConceptScheme`; disjoint with `voc:SchemeContract`, `voc:SchemeBinding`, `voc:BindingScope`, `skos:Concept` |
| `voc:SchemeContract` | Class | subClassOf `fnd:Version`, `fnd:Governable`; `constrainsProperty` min 1 |
| `voc:SchemeBinding` | Class | subClassOf `fnd:TemporallyScoped`; `forContract` exactly 1; `bindsScheme` exactly 1 |
| `voc:BindingScope` | Class | no restrictions; no individuals shipped |
| `voc:constrainsProperty` | Object property | domain `SchemeContract`, range `rdf:Property` (punning) |
| `voc:requiresGovernanceState` | Object property | domain `SchemeContract`, range `fnd:GovernanceState`; optional; disjunctive if multi-valued |
| `voc:boundScheme` | Object property | Functional; optional (unbound is the normal starting state); the unscoped default binding |
| `voc:forContract` | Object property | Functional; domain `SchemeBinding`, range `SchemeContract` |
| `voc:bindsScheme` | Object property | Functional; domain `SchemeBinding`, range `ConceptScheme` |
| `voc:bindingScope` | Object property | domain `SchemeBinding`, range `BindingScope`; optional; conjunctive if multi-valued |
| `voc:resolvedUnder` | Object property | no domain; range `SchemeBinding` |

No new annotation properties; `fnd:utility` reused throughout.

## 11. Open Items

- **Tidy Foundation's document to match §8's convention** — move `fnd:Evidence rdfs:subClassOf prov:Entity` out of its inline position in Foundation §6 so it appears only once, in Foundation §8, matching the stricter convention adopted here. Cosmetic (duplicate triples already collapse harmlessly), but worth doing for consistency now that a second layer document has established the tidier pattern.
- **Concept-level constraints** (excluding deprecated concepts, requiring leaf concepts) are a plausible extension to `SchemeContract` — deliberately deferred, per §4.
- **Binding resolution shapes.** The precedence and conflict conditions in §4 are stated but not yet checked: overlapping applicable bindings with no strict-superset winner, a scopeless `SchemeBinding` naming a different scheme from `boundScheme` on the same contract, and a record resolved under a binding whose temporal scope excludes the record's own time. Each needs a SHACL-SPARQL constraint in `shapes/constraints.ttl`.
- **Consumers of `boundScheme`.** Surface (`srf:BoundSchemeGovernanceShape`, the parity shapes) and Eligibility (`HierarchicalMatch` rule) read `boundScheme` only. They are correct for unscoped deployments and unchanged by this addition; honouring scoped bindings there means resolving the applicable binding per §4 first.
- **Version.** The additions are backward compatible; the `owl:versionIRI` has not been advanced, since Quantification and Instrument import `vocabulary/0.0.2` by exact IRI.
- **The named `SchemeContract` and `ConceptScheme` individuals themselves** — the actual authored contracts each layer will declare, and the actual schemes downstream implementers bind — belong in each consuming layer's own files (e.g. Instrument would declare its peril-type contract in `ontology/instrument/projection/` or a dedicated location not yet settled) and in `ontology/governance/scheme-contracts/` at the root, per the repository structure. Nothing here populates either.
- **This Turtle has been checked by manual syntax review and by testing the extraction procedure against this exact document** (confirmed to produce the intended fragment set correctly — see the two-tag convention in §3) but not by an actual OWL/Turtle parser, for the same environment reason noted in Foundation's document. Needed before this becomes `spec/vocabulary.ttl`.
