<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Typing InsurML content in LATTICE

**Unit:** [insurml-alignment](../plans/insurml-alignment.md), decision IMA-D4. **Status:** sketch,
2026-10-05, for the human's decision. Nothing here is ratified.
**Reads with:** [the bridge sketch](insurml-bridge.md) §4 (which this replaces in depth),
[the integration analysis](../notes/insurml-integration.md) §6.3 (options T1 to T3), the
[Wording README](../../../ontology/wording/README.md) §5.5 and §6, ADR-A85 (scoped binding),
ADR-A100 (hierarchical match), and the InsurML specification §4.2, §4.9 and §9.1.

---

## Contents

1. [The question](#1-the-question)
2. [How each standard types](#2-how-each-standard-types)
3. [What InsurML's types say](#3-what-insurmls-types-say)
4. [Requirements](#4-requirements)
5. [Options](#5-options)
6. [Problems every option meets](#6-problems-every-option-meets)
7. [Words that collide](#7-words-that-collide)
8. [Recommendation](#8-recommendation)
9. [Worked example](#9-worked-example)
10. [Decisions and questions](#10-decisions-and-questions)

---

## 1. The question

A lifted InsurML node carries InsurML's type, `iml:hasType`, and must also satisfy LATTICE's typing
properties, `wrd:elementType` and `wrd:classification`. The question is which concepts go where, so
that InsurML's shapes and LATTICE's shapes both pass on the same node, conditions and queries over
types work across InsurML's and publishers' schemes, and no type is read as meaning.

## 2. How each standard types

| | InsurML | LATTICE |
|---|---|---|
| Classes | four classes and one subclass: contract, component group, component, data element, variable. A class exists only where a type has its own structure | content kinds that differ in properties are classes (Text, Table, Variable, Reference, Metadata, Field, Entry, VariationSlot), disjoint. Embedded and governing variables are disjoint classes |
| Typing property | `iml:hasType`, one concept per object, at any depth of the class's type scheme | `wrd:elementType`, functional, under `wrd-voc:ElementTypeContract`. `wrd:classification`, any number, under `wrd-voc:ClassificationContract` |
| Schemes | contract type, component group type, component type, data element type, plus markup schemes. Each class names its scheme (`iml:typeScheme`) and, where one matches, its concept (`iml:typeConcept`) | a scheme contract per property. A binding chooses the scheme per scope and period (ADR-A85). Element types fall back to a baseline scheme (Section, Clause, Definition, Schedule, Annex, Endorsement). Classifications have no baseline |
| Scheme per concept | exactly one (`imlsh:ConceptShape`) | not required |
| Extension | a publisher's concept in the publisher's own scheme, `skos:broader` an InsurML concept. Rules on the broad concept apply to the narrow one | a deployment binds its own scheme, which may extend the baseline |
| Hierarchy in conditions | not used: conditions test variables, not types | hierarchical match closes over the members of the one resolved scheme (ADR-A100) |
| Rules on types | allow and deny lists of sub-component types, group placement, applicability, all on concepts | Wording laws read classes, not types. Profile shapes may read types |
| Types and meaning | legal intent is a component type (Coverage, Exclusion, Condition) | meaning is in Instrument. A type is evidence for review (IP7) |
| Retired types | `owl:deprecated`, rejected as a type (Clause) | governance states on concepts and schemes (`fnd:GovernanceState`) |

Two differences decide most of what follows. InsurML puts several kinds of distinction into one
type per object, and LATTICE separates "what kind of part" from "how it is classified". InsurML
allows a concept in one scheme only, and LATTICE resolves each contract to one scheme in a context.

## 3. What InsurML's types say

InsurML's component type scheme is one list, but its concepts answer different questions. Reading
each concept for the question it answers gives six facets.

| Facet | Answers | InsurML concepts |
|---|---|---|
| F1 structural | what kind of part this is in the document's tree | group types Module, Section, Sub-section, Schedule, Clause Group, Complex Component. Data element types Paragraph, Numbered Clause, Nested Clause, Title, Ordered List, Static Table, Dynamic Table and the reference and variable types |
| F2 document part | which separately issued or presented document this part is | Contract Jacket, Schedule Document, Certificate of Insurance, IPID, Synopsis, List of Benefits, Introduction, Table, Assessment |
| F3 legal function | what the clause does in the contract | Insuring Clause, Coverage, Exclusion, Condition, Limit, Defined Term, General Provision |
| F4 subject | what the clause is about | Premium, Sanctions, Notice, Communication, Survivorship, Termination and Automatic Suspension, Effect of Non-Renewal |
| F5 content status | whether it is part of the contract | System Guidance, Technical Guidance (always informational) |
| F6 instrument kind | what kind of contract the whole is | contract types Policy, Insurance, Reinsurance, Agreement, Binding Authority, Consortium, DCAA, Line Slip |

The facets are a reading for LATTICE's purposes, not a change to InsurML's scheme. A publisher's
narrower concept inherits its facet from its InsurML parent. InsurML's object attributes add two
more axes, area of coverage (a literal today) and applicability to contract types
(`iml:applicableTo`).

Each facet has a different home in LATTICE:

| Facet | Home in LATTICE | Why |
|---|---|---|
| F1 | `wrd:elementType`, and for data elements the content class | it is the "what kind of part" question Wording asks |
| F2 | `wrd:elementType` of the part, and `wrd:documentKind` where it is a linked document | a jacket or certificate is a kind of part, or a separate document |
| F3 | `wrd:classification`, and a routing hint for review. The meaning is an Instrument relation | a type does not decide meaning (IP7, §7) |
| F4 | `wrd:classification`, and the choice of template (a notice clause suggests a notice regime, CCS C8a) | a subject is a classification |
| F5 | content status in the profile (bridge §12) | informational content has no stated meaning |
| F6 | a classification of the wording root, and in AIR's contract module a classification of the instrument | the kind of contract is a fact about the instrument as much as about its words |

## 4. Requirements

| # | Requirement | Source |
|---|---|---|
| RT1 | InsurML's shapes pass unchanged on the co-typed graph, including one scheme per concept and class-concept agreement | AV1 |
| RT2 | Wording's shapes pass: `wrd:elementType` has one value under the resolved element type scheme, classifications under theirs | Wording §7 |
| RT3 | a condition or query on an InsurML type reaches publishers' narrower types | ADR-A100 |
| RT4 | no type is read as meaning | IP7 |
| RT5 | LATTICE-native wordings in the same deployment keep the baseline element types | AV7 |
| RT6 | no InsurML concept is minted again under another IRI | IP4 |
| RT7 | InsurML's rules held as data apply to the lifted graph | bridge §2.2 |
| RT8 | each fact is stated once | DP10, InsurML D116 |

## 5. Options

T1 to T3 are the integration analysis's options. T4 and T5 are new.

| Option | `wrd:elementType` | `wrd:classification` | `iml:hasType` |
|---|---|---|---|
| T1 profile structural scheme | a profile scheme of structural types (contract, module, section, component, paragraph, list) | InsurML's component type | kept |
| T2 InsurML types as element types | InsurML's type, whatever its facet | other classifications | kept |
| T3 baseline only | the baseline (Clause, Section, Definition, Schedule) | none | kept |
| T4 InsurML's structural concepts as element types | InsurML's own F1 and F2 concepts, plus a small profile scheme for what InsurML has no concept for (component, contract, placement, list item) | InsurML's component type | kept |
| T5 none in LATTICE | no `wrd:elementType` on InsurML nodes. LATTICE reads `iml:hasType` through the profile | none | kept |

Against the requirements:

| | RT1 | RT2 | RT3 | RT4 | RT5 | RT6 | RT7 | RT8 |
|---|---|---|---|---|---|---|---|---|
| T1 | yes | yes | needs §6.1 | yes | yes, by scope | no: a profile "section" beside InsurML's | yes | no: the structural type stated twice |
| T2 | yes | yes | needs §6.1 | no: legal intent becomes the kind of part | yes, by scope | yes | yes | yes |
| T3 | yes | yes | no | yes | yes | yes | yes | lossy |
| T4 | yes | needs §6.1, since three schemes feed one contract | needs §6.1 | yes | yes, by scope | yes | yes | yes |
| T5 | yes | yes, as the property is optional | needs §6.1 | yes | yes | yes | yes | yes, but LATTICE queries must know InsurML |

Notes on the table:

- **T1** is simple to build today and keeps the Wording contract resolving to one scheme. It mints a
  profile concept for each InsurML structural concept and links them with `skos:exactMatch`, which
  is SKOS-correct but states each structural type twice, once in each vocabulary.
- **T2** gives LATTICE one type per node with no new concepts, at the cost of treating
  "Exclusion" as a kind of part. Every query and shape that reads `wrd:elementType` then reads
  legal intent, which is what DP3 and IP7 exist to prevent.
- **T3** discards InsurML's types for LATTICE's purposes. A query for every exclusion must read
  InsurML's property directly.
- **T4** uses InsurML's own structural concepts, so nothing is minted twice. The element type
  contract would resolve to InsurML's group type scheme, its data element type scheme and a small
  profile scheme at once, which Vocabulary cannot do today (§6.1).
- **T5** leaves InsurML nodes untyped in Wording's terms. It works where LATTICE never reads
  element types, and LATTICE's own consumers (Instrument sections in C7c, the renderer, the review
  router) then need an InsurML branch.

## 6. Problems every option meets

### 6.1 One scheme per contract in a context

ADR-A85 resolves a scheme contract to one scheme in a context, by scope and period. InsurML's types
come from several schemes, and a publisher's narrower types sit in the publisher's own scheme, so
one property can need concepts from three or four schemes in one context.

The integration analysis proposed a union scheme per publisher, holding InsurML's concepts and the
publisher's (integration §6.3). That breaks RT1. A union scheme built by stating `skos:inScheme`
on InsurML's concepts puts each of them in two schemes, which `imlsh:ConceptShape` rejects.

| Way out | How | Cost |
|---|---|---|
| Scopes per class | bind InsurML's group type scheme in one scope and the data element type scheme in another, with the scope chosen by the node's class | scopes are opaque in Vocabulary (ADR-A85), and a resolver that picks a scope from a node's class is a new kind of context |
| Parallel profile concepts | T1: the profile mints its own concepts and maps them | breaks RT6 and RT8 |
| Scheme composition | a Vocabulary construct that makes a contract resolve to a set of schemes in one context, with membership the union of theirs and the hierarchy the union of their `skos:broader` links, without stating `skos:inScheme` again | a Vocabulary ADR, and Eligibility's hierarchical match reading the composition (an ADR-A100 addendum) |

Scheme composition is the general answer, and the same problem has already appeared in CCS. HQ-4
records that Quantification's context role contract must collect roles from Instrument, other
layers and each wording's own dates, and that Vocabulary resolves it to one scheme. One Vocabulary
ADR could serve both, and HQ-4 is due with CCS C8.

### 6.2 Hierarchy across schemes

A publisher's "Cyber exclusion" is `skos:broader` InsurML's "Exclusion", in another scheme. Under
ADR-A100, a hierarchical match on "Exclusion" closes over the members of the resolved scheme only.
If the resolved scheme is the publisher's, InsurML's "Exclusion" is outside it. If it is
InsurML's, the publisher's concept is outside it. Only a composition, or a reviewed crosswalk under
ADR-A100's decision 4, lets the match reach both. The crosswalk works today but treats a
publisher's own declared hierarchy as an external mapping that waits for review, which misreads
it.

### 6.3 Classes and concepts

InsurML types data elements with concepts where LATTICE uses classes. The top of InsurML's data
element hierarchy maps to LATTICE classes, and the narrower concepts to element types:

| InsurML data element type | LATTICE class | Element type |
|---|---|---|
| Text, and Paragraph, Numbered Clause, Nested Clause, Title, Ordered List | `wrd:Text` | the narrower concept |
| Table, and Static Table, Dynamic Table | `wrd:Table` | the narrower concept |
| Reference, and its four narrower types | `wrd:Reference` | the narrower concept |
| Variable, Embedded Variable, Governing Variable | `wrd:EmbeddedVariable`, `wrd:GoverningVariable` | none needed |
| Metadata, Descriptive, System | `wrd:Metadata` | the narrower concept |

The alignment can state the class from the concept with `owl:hasValue` axioms, which give useful
design-time entailment and meet the repository's rule on sparing domains and ranges:

```turtle
[ a owl:Restriction ; owl:onProperty iml:hasType ;
  owl:hasValue <https://insurml.example/vocab/data-element-type/embedded-variable> ]
    rdfs:subClassOf wrd:EmbeddedVariable .
```

The axiom covers the named concept only. A publisher's narrower concept is reached by the lift,
which reads `skos:broader` and states the class, since OWL cannot follow a concept hierarchy from a
value. The lift and the axiom must agree, and a test checks it.

### 6.4 Rules held as data

InsurML's allow and deny lists and placement rules read `iml:hasType`. The profile's shapes,
generated from the same data (bridge §2.2), read `iml:hasType` too. So InsurML's rules hold under
every option, and the choice of option decides only what LATTICE's own rules and queries read.

### 6.5 Governance of InsurML's schemes

LATTICE's contracts check a scheme's governance state (`voc:requiresGovernanceState`). InsurML's
schemes have no edition IRIs. A concept grows without a schema change and is retired with
`owl:deprecated`. The profile declares each InsurML scheme a `voc:ConceptScheme` with an identity
and a state, which states the deployment's adoption of the scheme, not InsurML's own status. It
maps `owl:deprecated` on an InsurML concept to a retired governance state, so a binding refuses
the concept as InsurML does.

## 7. Words that collide

Several InsurML concepts share a label with a LATTICE concept or term of another meaning. The
mapping relation is chosen by definition, never by label (IP6).

| InsurML concept | LATTICE term | Relation | Why |
|---|---|---|---|
| group type Section | `wrd-voc:Section`, a part with a determined meaning of its own (parties, authority, classes or capacity) | `skos:relatedMatch` | an insurance section often has its own limits and so meets LATTICE's definition, but not always. Whether it does is a finding of review, which C7c's sections can record |
| group type Schedule | `wrd-voc:Schedule`, a part holding an instance's particulars | `skos:closeMatch` | the same idea, with InsurML's Schedule Document a separate document part |
| component type Defined Term | `wrd-voc:Definition`, and `ins:Definition` (C7c) | `skos:exactMatch` to the element type | the same idea in the wording. The meaning is C7c's |
| Complex Component, altLabel Endorsement | `wrd-voc:Endorsement`, a document issued after the contract is made | none | InsurML's label names a structure. LATTICE's names a document |
| component type Clause, deprecated | `wrd-voc:Clause` | none | InsurML retired it. A lifted component is never typed Clause |
| component type Condition | `ins:OnCondition` (a legal trigger), term classification "condition" (breach lets the other side terminate, C7c), `elg:Condition` | none | four meanings across the two standards. The component type is F3 evidence only |
| component type Exclusion | `ins:Exclusion`, a Hohfeldian privilege or immunity within a scope | none | an exclusion clause may except an obligation, narrow its scope, or state a condition |

Each row becomes a fixture in the alignment's collision test (bridge §3).

## 8. Recommendation

**T4, with scheme composition, and T1 as the interim.**

| Step | When | What |
|---|---|---|
| Interim | phase 1 | T1. A small profile structural scheme for `wrd:elementType`, each concept `skos:exactMatch` its InsurML concept, recorded as a known duplication. `wrd:classification` bound to InsurML's component type scheme. Publishers' narrower concepts reached through reviewed crosswalks. The facets of §3 as profile annotations on InsurML's concepts, for routing and queries |
| Vocabulary ADR | with CCS C8 and HQ-4 | scheme composition: a contract resolving to a set of schemes in one context, with Eligibility's hierarchical match reading the union |
| Target | after the ADR | T4. `wrd:elementType` from InsurML's group type and data element type schemes, composed with a profile scheme for what InsurML lacks. `wrd:classification` from InsurML's component type scheme composed with each publisher's. The profile's parallel concepts are deprecated, and their `exactMatch` links remain for data typed in the interim |

The interim keeps every requirement except RT6 and RT8 and needs no substrate change. The target
meets all eight, and it settles a Vocabulary gap CCS already has.

## 9. Worked example

A publisher's cyber exclusion in a section, under the target. Identities and keys are omitted.

```turtle
@prefix iml:  <https://insurml.example/ns/core#> .
@prefix wrd:  <https://www.nebularis.org/neuro-semantic/lattice/wording#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .

<https://insurer.example/vocab/component-type/cyber-exclusion> a skos:Concept ;
    skos:inScheme <https://insurer.example/vocab/component-type> ;
    skos:broader <https://insurml.example/vocab/component-type/exclusion> .

<https://insurer.example/id/group/property-section/2026-01-01>
    a iml:ComponentGroup , wrd:Element ;
    iml:hasType     <https://insurml.example/vocab/component-group-type/section> ;
    wrd:elementType <https://insurml.example/vocab/component-group-type/section> .

<https://insurer.example/id/component/cyber-exclusion/2026-01-01>
    a iml:Component , wrd:Element ;
    iml:hasType        <https://insurer.example/vocab/component-type/cyber-exclusion> ;
    wrd:elementType    <https://deployment.example/vocab/insurml-structure/component> ;
    wrd:classification <https://insurer.example/vocab/component-type/cyber-exclusion> .

<https://insurer.example/id/component/cyber-exclusion/2026-01-01#p1>
    a wrd:Text ;
    wrd:elementType <https://insurml.example/vocab/data-element-type/numbered-clause> .
```

A hierarchical match on InsurML's "Exclusion", over the composed classification schemes, admits
the component. InsurML's shapes see one scheme per concept, and its rules on "Exclusion" apply to
the publisher's concept. Nothing here says what the clause means. That is the meaning template's
job.

## 10. Decisions and questions

| # | Decision or question | Leaning |
|---|---|---|
| IMA-D4 | typing option | T1 as the interim, T4 as the target |
| IMA-D4a | draft a Vocabulary ADR for scheme composition, shared with CCS HQ-4 | yes, briefed with C8 |
| TY-Q1 | Does InsurML intend its component type scheme to stay one list, or would its owner accept facets as sub-schemes or collections? | ask (Q-17). Facets as annotations work either way |
| TY-Q2 | Should F6 instrument kinds type the wording root, the instrument, or both? | both, the wording's from InsurML and the instrument's in AIR's contract module, linked by `ins:expressedIn` |
| TY-Q3 | Do C7c's sections read `wrd:elementType`? | no. Sections in law are named by `ins:appliesWithin`, so the `relatedMatch` of §7 cannot leak into meaning |
