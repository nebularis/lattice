<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Foundation Ontology — Description Logic Elements

*Literate specification. This document and `spec/foundation.ttl` are meant to be regenerated from one another — see [§3, How to Read This Document](#3-how-to-read-this-document) for the exact mechanics.*

---

## 1. Purpose and Scope

Foundation provides four independent, composable capabilities: persistent identity and versioning, evidential support, temporal scoping, and governance status.

Foundation's own governance-status concept is therefore a bare value, not a lifecycle — a downstream layer wanting transitions, triggers, and guards around that value composes Behaviour on top of it. This constraint shapes several of the decisions below and is worth keeping in mind.

## 2. Namespace and Prefixes

Base namespace for all LATTICE ontologies:

```
https://www.nebularis.org/neuro-semantic/lattice/
```

Each layer gets its own hash namespace under that base, following the convention:

| Layer | Namespace | Prefix |
|---|---|---|
| Foundation | `.../lattice/foundation#` | `fnd:` |
| Vocabulary | `.../lattice/vocabulary#` | `voc:` |
| Party | `.../lattice/party#` | `pty:` |
| Instrument | `.../lattice/instrument#` | `ins:` |
| Eligibility | `.../lattice/eligibility#` | `elg:` |
| Behaviour | `.../lattice/behaviour#` | `bhv:` |
| Mapping (MORK) | `.../lattice/mork#` | `mrk:` |

Hash namespaces are preferred to slash namespaces so that every term in a layer resolves with a single retrieval of that layer's ontology document, rather than requiring per-term de-referencing.

This document uses only the prefixes Foundation's own axioms actually need:

```turtle-spec
@prefix fnd:  <https://www.nebularis.org/neuro-semantic/lattice/foundation#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
```

## 3. How to Read This Document

Every class, property, and axiom group below follows the same fixed template:

> #### `fnd:TermName`
>
> **Definition.** One line — becomes the term's `rdfs:comment`.
>
> **Utility.** A paragraph explaining why the term exists and what it's for — becomes the term's `fnd:utility` value (defined in §5 below).
>
> ```turtle-example
> fnd:TermName a owl:Class ;
>     rdfs:comment "..." ;
>     fnd:utility "..." .
> ```

**NOTE FOR LLMs Regenerating `spec/foundation.ttl` from this document:** concatenate the prefix block in §2, then every fenced ` ```turtle ` block from **§5, §6 (including its Disjointness subsection), §7, and §8 — those four sections only.** The template illustration in this section (§3) and the worked example in §9 also use ` ```turtle ` fences but are not specification content — the template shows the pattern with a placeholder name rather than a real term, and the worked example deliberately uses `ins:` and `ex:` prefixes that aren't part of Foundation's own namespace and aren't declared in §2. A naive "every turtle block in the document" extraction will pull both in by mistake; an extraction tool should filter by section number, not merely by fence language. (This rule was tightened after testing the extraction against this exact document turned up precisely that mistake — worth keeping the explicit section list here rather than reverting to the vaguer phrasing.)

The blocks are fragments, not independently complete files — prefixes are declared once, not repeated per block, both to keep this document readable and to keep its own token footprint down if it's ever fed back to a model for extension. Nothing else in the document (the Definition/Utility prose, the tables) is authoritative; it's a rendering of what the Turtle blocks already say via `rdfs:comment` and `fnd:utility`.

**Regenerating this document from `spec/foundation.ttl`:** walk the ontology's classes and properties, and for each, render its `rdfs:comment` as Definition, its `fnd:utility` as Utility, and its full axiom set as the Turtle block, in the section order given by §5–8 below (Annotation Properties, Classes, Object and Data Properties, Alignments). Because the prose is sourced from annotation values rather than written independently, the two artefacts can't drift apart from ordinary editing of either one — drift can only happen if someone edits the rendered Markdown prose directly instead of the annotation value it came from, which the convention above is designed to make unnecessary.

## 4. Design Decisions

**Alignment with PROV-O.** Evidence is modelled as a subclass of `prov:Entity`, and `fnd:assertedBy` as a sub-property of `prov:wasAttributedTo`. Temporal scoping is *not* aligned with OWL-Time's `time:Instant`/`time:Interval` apparatus, since that would require modelling `validFrom`/`validTo` as individuals rather than plain `xsd:dateTime` literals. This is a considered asymmetry, not an oversight, and it's reversible later if temporal reasoning requirements grow.

**Four focused mixins.** An earlier pass considered a single `fnd:Governed` class carrying all four capabilities at once. This was rejected as it would force every class adopting any one capability to adopt all four, which overclaims, whereas independent, non-disjoint mixins let a downstream class pick exactly what it needs.

**`GovernanceState` is open at the OWL level, closed in SHACL.** OWL's open-world assumption sees us push closed-world constraints into `shapes/constraints.ttl` via `sh:in` restrictions over named individuals. The class exists here so the property `fnd:hasGovernanceState` has somewhere to range over; the enumeration itself is a different layer's concern, per the established `spec/` vs `vocab/` vs `shapes/` architectural boundary.

## 5. Annotation Properties

#### `fnd:utility`

**Definition.** The design rationale for a term — why it exists and what it means.

**Utility.** Ordinary `rdfs:comment` provides a narrative, whilst `fnd:utility` speaks to why a thing exists and is shaped the way it is. Every term in every LATTICE layer uses this property, making the reasoning behind the ontology itself as inspectable as the data the ontology describes.

```turtle-spec
fnd:utility a owl:AnnotationProperty ;
    rdfs:comment "The design rationale for a term — why it exists, not merely what it means." .
```

## 6. Classes

#### `fnd:Version`

**Definition.** An individual representing a specific, identified state of some persistent thing.

**Utility.** This is the mixin a domain class subclasses when it needs identity that survives change. Unlike the other three mixins below, `Version` doesn't point *out* to a separate value object — the domain individual itself plays the role, e.g., an Obligation instance as it stands between two dates, which doesn't have a version so much as it *is* one!

This is a deliberate asymmetry with Evidence, TemporalScope, and GovernanceState, which are naturally separate small objects (a proof, a date range, a status, etc).

```turtle-spec
fnd:Version a owl:Class ;
    rdfs:comment "An individual representing a specific, identified state of some persistent thing." ;
    fnd:utility "The mixin for identity that survives change. The domain individual itself plays the role of being a version, rather than pointing out to a separate version object — unlike Evidence, TemporalScope, and GovernanceState, there is no meaningful object distinct from the thing itself for versioning to reference." ;
    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty fnd:hasIdentity ;
        owl:cardinality "1"^^xsd:nonNegativeInteger
    ] .
```

#### `fnd:PersistentIdentity`

**Definition.** The stable identifier for a thing across all of its versions.

**Utility.** Separating identity from version is what makes "this is the same Obligation, edited" distinguishable from "this is a different Obligation that happens to look similar." Without this split, versioning collapses into a flat sequence of unrelated snapshots with no way to assert they're states of one continuant.

```turtle-spec
fnd:PersistentIdentity a owl:Class ;
    rdfs:comment "The stable identifier for a thing across all of its versions." ;
    fnd:utility "Separates 'the same thing, edited' from 'a different thing that looks similar' — without this, a version history is just a set of unrelated snapshots with no continuant they're all states of." ;
    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty fnd:hasVersion ;
        owl:minCardinality "1"^^xsd:nonNegativeInteger
    ] .
```

#### `fnd:Evidenced`

**Definition.** A mixin for anything that can carry supporting evidence.

**Utility.** Kept independent of `Version` deliberately — a Role Occupancy's contingent binding (a D&O third party becoming bound to a role) needs evidential support ("this transition fired because X was asserted") without that being a question of versioning at all. Coupling the two would force anything needing evidence to also take on full version-tracking, which is a stronger commitment than most callers need.

```turtle-spec
fnd:Evidenced a owl:Class ;
    rdfs:comment "A mixin for anything that can carry supporting evidence." ;
    fnd:utility "Independent of Version deliberately — needing evidential support for an assertion (why did this transition fire) is a different concern from needing identity that survives change, and coupling them would force every evidenced thing into full version-tracking whether it needs it or not." .
```

#### `fnd:Evidence`

**Definition.** An item of evidence supporting some assertion or entity.

**Utility.** Aligned with `prov:Entity` (§8) rather than defined from scratch, since PROV-O already provides exactly this concept with established semantics and tooling support. Evidence is required to support at least one thing — evidence that supports nothing isn't evidence of anything, and that's worth the T-box catching rather than leaving implicit.

```turtle-spec
fnd:Evidence a owl:Class ;
    rdfs:subClassOf prov:Entity ;
    rdfs:comment "An item of evidence supporting some assertion or entity." ;
    fnd:utility "Aligned with prov:Entity rather than defined from scratch, for interoperability with existing provenance tooling. Required to support at least one thing, since evidence supporting nothing isn't evidence of anything." ;
    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty fnd:supports ;
        owl:minCardinality "1"^^xsd:nonNegativeInteger
    ] , [
        a owl:Restriction ;
        owl:onProperty fnd:recordedAt ;
        owl:cardinality "1"^^xsd:nonNegativeInteger
    ] .
```

#### `fnd:TemporallyScoped`

**Definition.** A mixin for anything with a validity period distinct from when it was recorded.

**Utility.** Named separately from `Evidence.recordedAt` on purpose: *when a fact was true* and *when we learned or asserted it* are genuinely different questions, and conflating them is a common, easy-to-make modelling error (the bitemporal distinction — valid time versus transaction time). A thing can be `TemporallyScoped` without being `Evidenced`, and vice versa.

```turtle-spec
fnd:TemporallyScoped a owl:Class ;
    rdfs:comment "A mixin for anything with a validity period distinct from when it was recorded." ;
    fnd:utility "Keeps 'when this was true' (TemporalScope) separate from 'when we recorded it' (Evidence.recordedAt) — the bitemporal distinction between valid time and transaction time, which is easy to accidentally collapse into one timestamp." ;
    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty fnd:hasTemporalScope ;
        owl:cardinality "1"^^xsd:nonNegativeInteger
    ] .
```

#### `fnd:TemporalScope`

**Definition.** A validity period: a start, and an optional end.

**Utility.** A re-entering state (suspended, then reinstated) is modelled as a new `Version` with its own `TemporalScope`, rather than one individual carrying multiple disjoint validity windows — keeping this class to exactly one `validFrom`/`validTo` pair keeps that discipline enforceable at the T-box level instead of relying on convention.

```turtle-spec
fnd:TemporalScope a owl:Class ;
    rdfs:comment "A validity period: a start, and an optional end." ;
    fnd:utility "Deliberately holds exactly one validFrom/validTo pair. A thing that becomes valid, lapses, then becomes valid again is modelled as a new Version with a new TemporalScope, not as one TemporalScope with multiple windows — this keeps that discipline enforceable rather than conventional." ;
    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty fnd:validFrom ;
        owl:cardinality "1"^^xsd:nonNegativeInteger
    ] .
```

#### `fnd:Governable`

**Definition.** A mixin for anything that carries a governance-lifecycle status.

**Utility.** Expected to apply mainly to specification-level artefacts — a Wording Template, a SHACL shape, an ontology term — moving through draft/review/active/superseded, rather than to ordinary A-box facts. Kept as its own mixin rather than folded into `Version` or `Evidenced` so that a downstream class only takes on governance semantics when it genuinely has a review lifecycle, not by default.

```turtle-spec
fnd:Governable a owl:Class ;
    rdfs:comment "A mixin for anything that carries a governance-lifecycle status." ;
    fnd:utility "Expected to apply mainly to specification-level artefacts moving through a review lifecycle, not to ordinary facts. Kept separate from Version and Evidenced so governance semantics are opted into deliberately, not inherited by default." ;
    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty fnd:hasGovernanceState ;
        owl:cardinality "1"^^xsd:nonNegativeInteger
    ] .
```

#### `fnd:GovernanceState`

**Definition.** The status of a governed artefact within its review lifecycle.

**Utility.** Deliberately left open here — see [§4](#4-design-decisions). The class exists so `hasGovernanceState` has a range to point at; the closed set of actual values (`Draft`, `Reviewed`, `Active`, `Superseded`) is declared as named individuals in `vocab/foundation-vocab.ttl` and enforced as a closed set in `shapes/constraints.ttl`, not here. Also deliberately *not* a state machine — Foundation sits below Behaviour in the dependency order and cannot depend on Behaviour's Trigger/Guard/Effect apparatus without creating a cycle; a downstream ontology wanting transition semantics around governance status composes Behaviour on top of this bare value.

```turtle-spec
fnd:GovernanceState a owl:Class ;
    rdfs:comment "The status of a governed artefact within its review lifecycle." ;
    fnd:utility "Left open at the T-box level; the closed enumeration lives in vocab/ and shapes/, not spec/. Deliberately not a state machine — Foundation sits below Behaviour in the dependency order and cannot depend on it, so this is a bare value a downstream ontology can layer Behaviour's transition semantics on top of, not a lifecycle Foundation provides itself." .
```

### Disjointness

```turtle-spec
[] a owl:AllDisjointClasses ;
    owl:members ( fnd:Version fnd:PersistentIdentity fnd:Evidence fnd:TemporalScope fnd:GovernanceState ) .

fnd:Evidenced owl:disjointWith fnd:Evidence .
fnd:TemporallyScoped owl:disjointWith fnd:TemporalScope .
fnd:Governable owl:disjointWith fnd:GovernanceState .
```

**Utility.** The first group prevents category errors among the five things-that-aren't-mixins — an Evidence individual should never also be classified as a TemporalScope, and so on. The second set of three prevents the narrower error of confusing a mixin with the value object it points at (an `Evidenced` thing is not itself `Evidence`) — these three are *not* folded into the `AllDisjointClasses` group above because, unlike the five value classes, `Evidenced`/`TemporallyScoped`/`Governable` are meant to co-occur freely with each other and with `Version`.

## 7. Object and Data Properties

#### `fnd:hasIdentity` / `fnd:hasVersion`

**Definition.** `hasIdentity`: a Version's persistent identity. `hasVersion`: a PersistentIdentity's versions (inverse).

**Utility.** `hasIdentity` is marked `Functional` — a version belongs to exactly one identity, never several — which, combined with the `owl:inverseOf` relationship, entails the corresponding inverse-functional behaviour on `hasVersion` automatically. No separate axiom is needed to state that a version can't belong to two different identities; it follows from `Functional` plus the inverse declaration, and asserting it again would be redundant.

```turtle-spec
fnd:hasIdentity a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain fnd:Version ;
    rdfs:range fnd:PersistentIdentity ;
    owl:inverseOf fnd:hasVersion ;
    rdfs:comment "A Version's persistent identity." ;
    fnd:utility "Functional: a version belongs to exactly one identity. Combined with owl:inverseOf, this alone entails that hasVersion is inverse-functional — asserting that separately would be redundant." .

fnd:hasVersion a owl:ObjectProperty ;
    rdfs:domain fnd:PersistentIdentity ;
    rdfs:range fnd:Version ;
    rdfs:comment "A PersistentIdentity's versions." ;
    fnd:utility "The inverse of hasIdentity. Not independently marked with a cardinality characteristic — its inverse-functional behaviour is already entailed by hasIdentity's Functional characteristic." .
```

#### `fnd:supersededBy`

**Definition.** Direct succession between two versions of the same identity.

**Utility.** Marked `Irreflexive` (a version cannot supersede itself) and `Asymmetric` (if A supersedes B, B cannot also supersede A) — both cheap, correct, reasoner-checkable constraints that catch nonsensical version histories. Deliberately *not* marked `Transitive`: this property expresses immediate succession only, not "is eventually superseded by." Materialising the full transitive closure of a long version chain would multiply inferred triples for little benefit; "is this the latest version" is better answered as a zero-or-more-hop query at query time than as a standing set of materialised facts. Whether two versions related by this property actually share the same `hasIdentity` value is a whole-graph integrity check, not expressible as a pure class restriction without property chains that would overreach what this axiom is for — that check belongs in `shapes/constraints.ttl`.

```turtle-spec
fnd:supersededBy a owl:ObjectProperty, owl:AsymmetricProperty, owl:IrreflexiveProperty ;
    rdfs:domain fnd:Version ;
    rdfs:range fnd:Version ;
    rdfs:comment "Direct succession between two versions of the same identity." ;
    fnd:utility "Irreflexive and Asymmetric catch nonsensical version histories cheaply. Deliberately not Transitive — this is immediate succession only; materialising full transitive closure isn't worth the inferred-triple cost, and 'latest version' is a query-time question. Same-identity integrity is a shapes/constraints.ttl concern, not a T-box restriction here." .
```

#### `fnd:hasEvidence` / `fnd:supports`

**Definition.** `hasEvidence`: the evidence supporting an Evidenced thing. `supports`: the inverse.

**Utility.** Not `Functional` in either direction — an individual can accumulate multiple pieces of evidence over time, and one piece of evidence could in principle support more than one thing. No minimum cardinality on `hasEvidence`: an Evidenced thing may have no evidence yet, which is the normal starting state, not an error.

```turtle-spec
fnd:hasEvidence a owl:ObjectProperty ;
    rdfs:domain fnd:Evidenced ;
    rdfs:range fnd:Evidence ;
    owl:inverseOf fnd:supports ;
    rdfs:comment "The evidence supporting an Evidenced thing." ;
    fnd:utility "Not Functional — an individual can accumulate multiple pieces of evidence over time. No minimum: having no evidence yet is a normal starting state, not an error." .

fnd:supports a owl:ObjectProperty ;
    rdfs:domain fnd:Evidence ;
    rdfs:range fnd:Evidenced ;
    rdfs:comment "The inverse of hasEvidence." ;
    fnd:utility "The inverse direction of hasEvidence; Evidence's own minimum-one restriction (§6) is what actually requires every piece of evidence to support something." .
```

#### `fnd:assertedBy`

**Definition.** The agent that asserted a piece of evidence.

**Utility.** A sub-property of `prov:wasAttributedTo` rather than a freestanding LATTICE property, and its range is `prov:Agent` directly rather than a LATTICE-specific Agent class — Foundation doesn't need its own agent concept when PROV-O already provides one with the right generality (human, organisation, or software agent all fit).

```turtle-spec
fnd:assertedBy a owl:ObjectProperty ;
    rdfs:domain fnd:Evidence ;
    rdfs:range prov:Agent ;
    rdfs:subPropertyOf prov:wasAttributedTo ;
    rdfs:comment "The agent that asserted a piece of evidence." ;
    fnd:utility "Sub-property of prov:wasAttributedTo, ranging over prov:Agent directly — no LATTICE-specific Agent class is defined, since PROV-O already has the right generality across human, organisational, and software agents." .
```

#### `fnd:recordedAt`

**Definition.** When a piece of evidence was recorded.

**Utility.** The transaction-time half of the bitemporal split introduced under `TemporallyScoped` (§6) — deliberately attached to `Evidence`, not to `TemporalScope`, since "when we learned this" is a property of the evidence itself, not of the validity period the evidence might be evidence for.

```turtle-spec
fnd:recordedAt a owl:DatatypeProperty, owl:FunctionalProperty ;
    rdfs:domain fnd:Evidence ;
    rdfs:range xsd:dateTime ;
    rdfs:comment "When a piece of evidence was recorded." ;
    fnd:utility "The transaction-time half of the bitemporal split. Attached to Evidence rather than TemporalScope, since 'when we learned this' describes the evidence, not the validity period it may be evidence for." .
```

#### `fnd:hasTemporalScope`

**Definition.** The validity period of a TemporallyScoped thing.

```turtle-spec
fnd:hasTemporalScope a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain fnd:TemporallyScoped ;
    rdfs:range fnd:TemporalScope ;
    rdfs:comment "The validity period of a TemporallyScoped thing." ;
    fnd:utility "Functional, consistent with TemporalScope's own single validFrom/validTo pair (§6) — one scope per version, with re-entry modelled as a new version rather than a scope with gaps." .
```

#### `fnd:validFrom` / `fnd:validTo`

**Definition.** The start (required) and end (optional) of a validity period.

**Utility.** `validFrom` is required — an unbounded-past validity period isn't a case LATTICE needs to express. `validTo` is optional, capped at one, so a currently-open-ended scope simply omits it rather than needing a sentinel value.

```turtle-spec
fnd:validFrom a owl:DatatypeProperty, owl:FunctionalProperty ;
    rdfs:domain fnd:TemporalScope ;
    rdfs:range xsd:dateTime ;
    rdfs:comment "The start of a validity period." ;
    fnd:utility "Required — an unbounded-past validity period isn't a case LATTICE needs to express." .

fnd:validTo a owl:DatatypeProperty, owl:FunctionalProperty ;
    rdfs:domain fnd:TemporalScope ;
    rdfs:range xsd:dateTime ;
    rdfs:comment "The end of a validity period, if it has one." ;
    fnd:utility "Optional and capped at one — an open-ended scope simply omits this rather than needing a sentinel value." .
```

#### `fnd:hasGovernanceState`

**Definition.** The current governance status of a Governable thing.

```turtle-spec
fnd:hasGovernanceState a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain fnd:Governable ;
    rdfs:range fnd:GovernanceState ;
    rdfs:comment "The current governance status of a Governable thing." ;
    fnd:utility "Functional — one current status. A status change is a new fact about this property's value, not a state-machine transition Foundation itself models; see GovernanceState (§6)." .
```

## 8. Alignments

Collected here for visibility, and to make them easy to extract into a separate optional module later if that split (discussed in §4) is taken up. Nothing in this section introduces new LATTICE classes or properties — it only relates existing ones to PROV-O.

```turtle-spec
fnd:Evidence rdfs:subClassOf prov:Entity .
fnd:assertedBy rdfs:subPropertyOf prov:wasAttributedTo .
```

## 9. Worked Micro-Example

Illustration only — `ins:Obligation` isn't defined here; it belongs to Instrument. This shows how a domain class from another layer would compose Foundation's mixins.

```turtle-example
# Illustrative only — ins: is not part of Foundation's own namespace.
ins:Obligation rdfs:subClassOf fnd:Version, fnd:Evidenced, fnd:TemporallyScoped .

ex:ob1
    a ins:Obligation ;
    fnd:hasIdentity ex:ob-identity-471 ;
    fnd:hasTemporalScope [
        fnd:validFrom "2026-03-03T00:00:00Z"^^xsd:dateTime
    ] ;
    fnd:hasEvidence [
        a fnd:Evidence ;
        fnd:supports ex:ob1 ;
        fnd:recordedAt "2026-03-03T09:14:00Z"^^xsd:dateTime ;
        fnd:assertedBy ex:underwriting-system
    ] .
```

`ex:ob1` doesn't take on `fnd:Governable` — an ordinary contract fact, as distinct from a specification artefact, has no review lifecycle to track, and the mixins were designed precisely so it doesn't have to.

## 10. Axiom Index

| Term | Kind | Key characteristics |
|---|---|---|
| `fnd:utility` | Annotation property | — |
| `fnd:Version` | Class (mixin) | `hasIdentity` cardinality 1 |
| `fnd:PersistentIdentity` | Class | `hasVersion` min 1 |
| `fnd:Evidenced` | Class (mixin) | — |
| `fnd:Evidence` | Class | subClassOf `prov:Entity`; `supports` min 1; `recordedAt` cardinality 1 |
| `fnd:TemporallyScoped` | Class (mixin) | `hasTemporalScope` cardinality 1 |
| `fnd:TemporalScope` | Class | `validFrom` cardinality 1 |
| `fnd:Governable` | Class (mixin) | `hasGovernanceState` cardinality 1 |
| `fnd:GovernanceState` | Class | open at T-box; closed via SHACL |
| `fnd:hasIdentity` | Object property | Functional; inverse of `hasVersion` |
| `fnd:hasVersion` | Object property | inverse-functional (entailed) |
| `fnd:supersededBy` | Object property | Asymmetric, Irreflexive; not Transitive |
| `fnd:hasEvidence` | Object property | inverse of `supports` |
| `fnd:supports` | Object property | domain `Evidence`, range `Evidenced` |
| `fnd:assertedBy` | Object property | subPropertyOf `prov:wasAttributedTo` |
| `fnd:recordedAt` | Data property | Functional, `xsd:dateTime` |
| `fnd:hasTemporalScope` | Object property | Functional |
| `fnd:validFrom` | Data property | Functional, required |
| `fnd:validTo` | Data property | Functional, optional |
| `fnd:hasGovernanceState` | Object property | Functional |

Five classes mutually disjoint (`Version`, `PersistentIdentity`, `Evidence`, `TemporalScope`, `GovernanceState`); each of the three "points-to" mixins disjoint from its own value class.

## 11. Open Items

- **Alignment module split.** §8's PROV-O alignment axioms are candidates for a separate, optional file a consumer could choose not to import, keeping `spec/foundation.ttl` itself free of external dependencies. Not built yet — a decision for whoever builds `tools/`.
- **`fnd:GovernanceState`'s named individuals** (`Draft`, `Reviewed`, `Active`, `Superseded`) belong in `vocab/foundation-vocab.ttl`, not written here — this document only establishes the class and property they'll populate.
- **The `same-identity` integrity check** on `fnd:supersededBy` (§7) belongs in `shapes/constraints.ttl` as a SHACL-SPARQL rule, not attempted here as an OWL property chain.
- **This Turtle has been checked by manual syntax review, not by an actual OWL/Turtle parser** — no parser was available in the environment this document was drafted in. Running it through `riot` (Apache Jena) or `rdflib` before merging into `spec/foundation.ttl` is a needed step, not an optional one.
- ~~Extraction tooling should assert its section filter explicitly~~ — **Resolved.** Spec content is now fenced ` ```turtle-spec `; illustration is fenced ` ```turtle-example `. Extraction filters on the fence tag alone; no section-number knowledge is required.
