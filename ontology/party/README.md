<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Party Ontology — Description Logic Elements

*Literate specification, following the convention established in `ontology/foundation/spec/foundation.md` and `ontology/vocabulary/spec/vocabulary.md`.*

---

## 1. Purpose and Scope

Party provides Actor, Role, and the reified qualified-relation individual (Role Occupancy) that connects them, scoped and time-bound. Participation Groups with shares and composition rules, Delegation between an accountable role and a performing one, are both built on that reification.

Party imports Foundation and Vocabulary, and is imported in turn by Instrument, Eligibility, and Behaviour, per the established dependency order. The direction matters more here than in prior ontologies, because upward references (e.g., an Obligation's obligor and obligee, an Effect populating a contingent occupancy, or a Guard testing a delegation's scope) are deliberately left to the higher layer's own projection file(s) to declare.

## 2. Namespace and Prefixes

```turtle-spec
@prefix pty:  <https://www.nebularis.org/neuro-semantic/lattice/party#> .
@prefix fnd:  <https://www.nebularis.org/neuro-semantic/lattice/foundation#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
```

## 3. How to Read This Document

Same convention as the prior two documents: genuine specification content is fenced ` ```turtle-spec `; illustration is fenced ` ```turtle-example ` and is never part of the extraction. Concatenate the prefix block above with every ` ```turtle-spec ` block from §5 onward to produce `spec/party.ttl`. 

## 4. Design Decisions

**Role Occupancy has no property pointing back at whatever it's scoped to.** Earlier versions described occupancies as "scoped to an Instrument (or a specific Obligation within it)" which, read too literally, would mean declaring a property like `pty:withinInstrument` ranging over `ins:Instrument`, which Party cannot do without depending on a layer above it in the dependency order. The actual mechanism is the reverse: Scoping is established entirely from the referencing side.

**`occupiedBy` is optional; `inRole` is required.** This is the formal mechanism behind contingent role occupancy — the case where a role exists in an instrument's design from the outset but no actor occupies it until some event triggers a state change.

**Group membership is its own reified class, not a property on `RoleOccupancy`.** Share is a property of *participating in a specific group*, not of the occupancy in isolation — if an occupancy were ever relevant to more than one grouping, putting share directly on the occupancy would be ambiguous about which group it referred to. `GroupMembership` reifies exactly that participation, the same qualified-relation move `RoleOccupancy` itself already makes for Actor-in-Role.

**`Role` and `CompositionRule` are open at the T-box level, closed-by-default in `vocab/party-vocab.ttl`.** This design pattern is common — Foundation's `GovernanceState`, Vocabulary's implicit treatment of scheme-contract structure — and `CONTRIBUTING.md` already names "role type" and "composition-rule type" specifically as mechanism-intrinsic vocabulary, distinct from the genuinely domain-specific vocabulary that goes through Vocabulary's scheme-contract mechanism instead. Obligor, Obligee, Accountable, and Performing are properties of *how a directed relationship or a delegation works*, in any domain — not properties of insurance, or lending, or clinical trials specifically, which is what makes them mechanism-intrinsic rather than something a downstream implementation should have to supply. "Closed" here means closed-by-default, not closed-permanently: we allow for composition rules a lower ontology defines beyond LATTICE's own baseline, and `vocab/party-vocab.ttl` treats both Role and CompositionRule the same way — a baseline a downstream implementation may extend, with a correspondingly extended or overridden SHACL shape.

**Delegation carries no formal scope property.** Formalising a scope property here — even a simple one — would mean either duplicating Eligibility's mechanism or depending on a layer above Party in the order. `Delegation` states only that a performing occupancy discharges an accountable one; whether a given instance of performance is *within scope* is composed on top, by Eligibility, exactly the way Behaviour composes state transitions on top of Foundation's bare `GovernanceState`.

**`Actor` and `Role` are bare classes — no Foundation mixins, no internal structure.** Nothing in the established design required an actor's own details to be versioned, or a role to carry properties of its own beyond being what an occupancy points at.

## 5. Annotation Properties

None declared. `fnd:utility` is reused unchanged.

## 6. Classes

#### `pty:Actor`

**Definition.** A real-world party — a person, an organisation, or any other agent capable of occupying a role.

**Utility.** A real-world party — a person, an organisation, or any other agent. Reference an Actor from a RoleOccupancy's `occupiedBy` property. Party itself does not prescribe internal identification fields, so add whatever properties your domain needs on this class or a subclass.

```turtle-spec
pty:Actor a owl:Class ;
    rdfs:comment "A real-world party — a person, an organisation, or any other agent capable of occupying a role." ;
    fnd:utility "A real-world party — a person, an organisation, or any other agent. Reference an Actor from a RoleOccupancy's occupiedBy property. Add whatever identifying properties your own domain needs to this class or a subclass of it." .
```

#### `pty:Role`

**Definition.** A capacity in which an actor may occupy a Role Occupancy.

**Utility.** A capacity that a RoleOccupancy is filling, independent of which actor fills it. Use role individuals such as `Obligor`, `Obligee`, `Accountable`, `Performing`, or `Guarantor` to type occupancies.

```turtle-spec
pty:Role a owl:Class ;
    rdfs:comment "A capacity in which an actor may occupy a Role Occupancy." ;
    fnd:utility "A capacity that a RoleOccupancy is filling, independent of which actor fills it. Use role individuals such as Obligor, Obligee, Accountable, Performing, or Guarantor to type occupancies appropriately." .
```

#### `pty:RoleOccupancy`

**Definition.** An actor's occupancy of a role, reified so it can carry a time scope and exist before it's filled.

**Utility.** Represents one actor's occupancy of one role, for a period of time. Set `inRole` when the occupancy is created, and set `occupiedBy` once an actor is bound, which may happen later or not at all. If the occupant changes, create a new RoleOccupancy sharing the same `fnd:hasIdentity` as the old one and link them via `fnd:supersededBy`, rather than editing `occupiedBy` on the original. Use `fnd:hasEvidence` to record why a specific actor was bound, and `fnd:hasTemporalScope` for the validity period.

```turtle-spec
pty:RoleOccupancy a owl:Class ;
    rdfs:subClassOf fnd:Version, fnd:Evidenced, fnd:TemporallyScoped ;
    rdfs:comment "An actor's occupancy of a role, reified so it can carry a time scope and exist before it's filled." ;
    fnd:utility "Represents one actor's occupancy of one role, for a period of time. Set inRole when the occupancy is created — the role slot can exist before anyone fills it — and occupiedBy once an actor is bound, which may happen later or not at all. If the occupant changes, create a new RoleOccupancy sharing the old one's fnd:hasIdentity and link them with fnd:supersededBy. Use fnd:hasEvidence to record why a particular actor was bound." ;
    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty pty:inRole ;
        owl:cardinality "1"^^xsd:nonNegativeInteger
    ] .
```

#### `pty:ParticipationGroup`

**Definition.** A set of Role Occupancies sharing responsibility for one obligation, under a declared composition rule.

**Utility.** A set of Role Occupancies sharing responsibility for one obligation. Set `hasCompositionRule` to define how member shares relate to the whole, and connect members through `GroupMembership` individuals rather than a direct property. If composition changes, create a new version and link it to the old one with `fnd:supersededBy`.

```turtle-spec
pty:ParticipationGroup a owl:Class ;
    rdfs:subClassOf fnd:Version, fnd:Evidenced ;
    rdfs:comment "A set of Role Occupancies sharing responsibility for one obligation, under a declared composition rule." ;
    fnd:utility "A set of Role Occupancies sharing responsibility for one obligation. Give it a hasCompositionRule to say how members' shares relate to the whole, and connect members through GroupMembership individuals rather than a direct property. If composition changes, create a new version and link it with fnd:supersededBy." ;
    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty pty:hasCompositionRule ;
        owl:cardinality "1"^^xsd:nonNegativeInteger
    ] , [
        a owl:Restriction ;
        owl:onProperty pty:hasParticipant ;
        owl:minCardinality "1"^^xsd:nonNegativeInteger
    ] .
```

#### `pty:CompositionRule`

**Definition.** How a Participation Group's members' shares relate to the whole obligation.

**Utility.** How a Participation Group's members' shares relate to the whole obligation, for example whether each member's exposure is capped at its own share, or any member may be called for the full amount with recourse against others. Named values such as `SeveralOnly` and `JointAndSeveral` are declared in `vocab/party-vocab.ttl`.

```turtle-spec
pty:CompositionRule a owl:Class ;
    rdfs:comment "How a Participation Group's members' shares relate to the whole obligation." ;
    fnd:utility "How a Participation Group's members' shares relate to the whole obligation — for example, whether each member's exposure is capped at its own share, or any member may be called for the full amount with a right of recourse against the others. Named values are declared in vocab/party-vocab.ttl." .
```

#### `pty:GroupMembership`

**Definition.** One Role Occupancy's participation in one Participation Group, carrying that occupancy's share.

**Utility.** Connects one RoleOccupancy to one ParticipationGroup and carries that participation's share. Create one membership per occupancy-per-group relationship, rather than storing share directly on the occupancy.

```turtle-spec
pty:GroupMembership a owl:Class ;
    rdfs:comment "One Role Occupancy's participation in one Participation Group, carrying that occupancy's share." ;
    fnd:utility "Connects one RoleOccupancy to one ParticipationGroup, carrying that participation's share. Create one for each occupancy added to a group, rather than putting a share value directly on the occupancy." ;
    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty pty:memberOccupancy ;
        owl:cardinality "1"^^xsd:nonNegativeInteger
    ] , [
        a owl:Restriction ;
        owl:onProperty pty:memberOf ;
        owl:cardinality "1"^^xsd:nonNegativeInteger
    ] , [
        a owl:Restriction ;
        owl:onProperty pty:share ;
        owl:cardinality "1"^^xsd:nonNegativeInteger
    ] .
```

#### `pty:Delegation`

**Definition.** A performing Role Occupancy's discharge of an accountable one, without transferring the accountability itself.

**Utility.** Records that a performing Role Occupancy is carrying out what an accountable one owes, without transferring accountability. Set `delegatesFrom` to the accountable occupancy and `delegatesTo` to the performing occupancy. Use `fnd:hasEvidence` for the authorisation and `fnd:hasTemporalScope` for the covered period. If scope changes materially, create a new Delegation rather than editing this one.

```turtle-spec
pty:Delegation a owl:Class ;
    rdfs:subClassOf fnd:Evidenced, fnd:TemporallyScoped ;
    rdfs:comment "A performing Role Occupancy's discharge of an accountable one, without transferring the accountability itself." ;
    fnd:utility "Records that a performing Role Occupancy is carrying out what an accountable one owes, without the accountable occupancy losing its accountability. Set delegatesFrom to the accountable occupancy and delegatesTo to the performing one. If the scope changes materially, create a new Delegation rather than editing this one." ;
    rdfs:subClassOf [
        a owl:Restriction ;
        owl:onProperty pty:delegatesFrom ;
        owl:cardinality "1"^^xsd:nonNegativeInteger
    ] , [
        a owl:Restriction ;
        owl:onProperty pty:delegatesTo ;
        owl:cardinality "1"^^xsd:nonNegativeInteger
    ] .
```

### Disjointness

```turtle-spec
[] a owl:AllDisjointClasses ;
    owl:members ( pty:Actor pty:Role pty:RoleOccupancy pty:ParticipationGroup pty:GroupMembership pty:Delegation ) .
```

**Utility.** Actor, Role, RoleOccupancy, ParticipationGroup, GroupMembership, and Delegation are distinct kinds of thing. One individual should never be classified as more than one of them.

## 7. Object and Data Properties

#### `pty:occupiedBy`

**Definition.** The actor currently occupying a Role Occupancy, if one has been bound yet.

```turtle-spec
pty:occupiedBy a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain pty:RoleOccupancy ;
    rdfs:range pty:Actor ;
    rdfs:comment "The actor currently occupying a Role Occupancy, if one has been bound yet." ;
    fnd:utility "Points a RoleOccupancy at the actor currently occupying it. Leave unset for a role that's designed in but not yet filled — the normal state for a contingent occupancy until something binds an actor to it." .
```

#### `pty:inRole`

**Definition.** The role a Role Occupancy is an occupancy of.

```turtle-spec
pty:inRole a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain pty:RoleOccupancy ;
    rdfs:range pty:Role ;
    rdfs:comment "The role a Role Occupancy is an occupancy of." ;
    fnd:utility "Required, unlike occupiedBy — the role slot is designed in from the outset even when nobody has yet filled it." .
```

#### `pty:memberOccupancy` / `pty:memberOf` / `pty:hasParticipant`

**Definition.** `memberOccupancy`: the Role Occupancy a GroupMembership represents. `memberOf`: the Participation Group it belongs to. `hasParticipant`: the inverse of `memberOf`.

**Utility.** `hasParticipant` is the inverse of `memberOf`. It points a ParticipationGroup at its GroupMembership individuals and is typically used for querying rather than direct assertion.

```turtle-spec
pty:memberOccupancy a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain pty:GroupMembership ;
    rdfs:range pty:RoleOccupancy ;
    rdfs:comment "The Role Occupancy a GroupMembership represents." ;
    fnd:utility "Functional and required (§6) — a membership always names exactly one occupancy." .

pty:memberOf a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain pty:GroupMembership ;
    rdfs:range pty:ParticipationGroup ;
    owl:inverseOf pty:hasParticipant ;
    rdfs:comment "The Participation Group a GroupMembership belongs to." ;
    fnd:utility "Functional and required (§6) — a membership always names exactly one group." .

pty:hasParticipant a owl:ObjectProperty ;
    rdfs:domain pty:ParticipationGroup ;
    rdfs:range pty:GroupMembership ;
    rdfs:comment "The inverse of memberOf." ;
    fnd:utility "The inverse of memberOf — points a ParticipationGroup at its GroupMembership individuals. Typically used for querying a group's members rather than asserted directly." .
```

#### `pty:share`

**Definition.** The proportion of the obligation a group member is responsible for.

**Utility.** The proportion of the obligation this group member is responsible for, expressed as a decimal, for example `0.4` for 40 percent. If fixed-amount shares are needed, add that as a separate property.

```turtle-spec
pty:share a owl:DatatypeProperty, owl:FunctionalProperty ;
    rdfs:domain pty:GroupMembership ;
    rdfs:range xsd:decimal ;
    rdfs:comment "The proportion of the obligation a group member is responsible for." ;
    fnd:utility "The proportion of the obligation this group member is responsible for, expressed as a decimal — 0.4 for 40%. For fixed-amount shares rather than proportions, add that as a separate property." .
```

#### `pty:hasCompositionRule`

**Definition.** The rule governing how a Participation Group's members' shares relate to the whole.

```turtle-spec
pty:hasCompositionRule a owl:ObjectProperty, owl:FunctionalProperty ;
    rdfs:domain pty:ParticipationGroup ;
    rdfs:range pty:CompositionRule ;
    rdfs:comment "The rule governing how a Participation Group's members' shares relate to the whole." ;
    fnd:utility "Functional and required (§6) — a group's composition rule is never ambiguous or absent once the group exists." .
```

#### `pty:delegatesFrom` / `pty:delegatesTo`

**Definition.** `delegatesFrom`: the accountable Role Occupancy whose performance is being delegated. `delegatesTo`: the performing Role Occupancy actually carrying it out.

**Utility.** Neither is globally functional — the same accountable occupancy may have several delegations over time or in parallel (different scopes to different performers), and the same performing occupancy may discharge obligations delegated from more than one accountable occupancy (one CRO serving several sponsors). Each individual `Delegation`, however, names exactly one of each (§6) — the multiplicity lives in there being many `Delegation` individuals, not in either property being multi-valued on a single one.

```turtle-spec
pty:delegatesFrom a owl:ObjectProperty ;
    rdfs:domain pty:Delegation ;
    rdfs:range pty:RoleOccupancy ;
    rdfs:comment "The accountable Role Occupancy whose performance is being delegated." ;
    fnd:utility "Not globally functional — an accountable occupancy may have several delegations over time or in parallel. Each Delegation individual names exactly one (§6); the multiplicity is in there being many Delegation individuals." .

pty:delegatesTo a owl:ObjectProperty ;
    rdfs:domain pty:Delegation ;
    rdfs:range pty:RoleOccupancy ;
    rdfs:comment "The performing Role Occupancy actually carrying out the delegated obligation." ;
    fnd:utility "Points a Delegation at the performing RoleOccupancy that carries out the delegated obligation. One performing occupancy may appear in multiple delegations." .
```

## 8. Alignments

None. Party introduces no external-vocabulary dependency the way Vocabulary aligns with SKOS or Foundation aligns with PROV-O — everything here is either LATTICE-internal or a reuse of Foundation's own mixins, already declared as such in §6.

## 9. Worked Micro-Examples

Illustration only. `ins:` and `ex:` prefixes are not part of Party's own namespace. `pty:Obligor`, `pty:SeveralOnly`, `pty:Accountable`, and `pty:Performing` are forward references to named individuals `vocab/party-vocab.ttl` will declare, exactly as `fnd:Active` was a forward reference in Vocabulary's worked example.

### 9.1 Several liability

Three occupancies sharing one obligation, none liable for more than its own share.

```turtle-example
ex:group-1
    a pty:ParticipationGroup ;
    pty:hasCompositionRule pty:SeveralOnly .

ex:occ-a a pty:RoleOccupancy ;
    pty:inRole pty:Obligor ;
    pty:occupiedBy ex:syndicate-a ;
    fnd:hasTemporalScope [ fnd:validFrom "2026-01-01T00:00:00Z"^^xsd:dateTime ] .

ex:mem-a a pty:GroupMembership ;
    pty:memberOccupancy ex:occ-a ;
    pty:memberOf ex:group-1 ;
    pty:share "0.40"^^xsd:decimal .

# ex:occ-b / ex:mem-b (0.35) and ex:occ-c / ex:mem-c (0.25) follow the same pattern.
```

Note what's absent: nothing here says which obligation this group fulfils. That reference — `ins:fulfilledBy`, or similar — is declared in Instrument's own projection file, pointing *at* `ex:group-1` from the Obligation side, per §4.

### 9.2 Contingent occupancy and delegation

A role designed in from the outset, unoccupied until later; and an accountable/performing split.

```turtle-example
# Designed in from the start — inRole is set, occupiedBy is not.
ex:third-party-occ a pty:RoleOccupancy ;
    pty:inRole pty:Obligee .

# Later, a separate Effect (Behaviour's, not Party's) adds:
#   ex:third-party-occ pty:occupiedBy ex:claimant-x .
# together with evidence recording why.

# Accountable/performing split — the sponsor remains accountable;
# the CRO performs, under a delegation with its own evidence and period.
ex:sponsor-occ a pty:RoleOccupancy ; pty:inRole pty:Accountable .
ex:cro-occ a pty:RoleOccupancy ; pty:inRole pty:Performing .

ex:delegation-1
    a pty:Delegation ;
    pty:delegatesFrom ex:sponsor-occ ;
    pty:delegatesTo ex:cro-occ ;
    fnd:hasTemporalScope [ fnd:validFrom "2026-02-01T00:00:00Z"^^xsd:dateTime ] .
```

## 10. Axiom Index

| Term | Kind | Key characteristics |
|---|---|---|
| `pty:Actor` | Class | bare, no mixins |
| `pty:Role` | Class | bare; open at T-box, closed via `vocab/party-vocab.ttl` |
| `pty:RoleOccupancy` | Class | `fnd:Version`, `fnd:Evidenced`, `fnd:TemporallyScoped`; `inRole` cardinality 1 |
| `pty:ParticipationGroup` | Class | `fnd:Version`, `fnd:Evidenced`; `hasCompositionRule` cardinality 1; `hasParticipant` min 1 |
| `pty:CompositionRule` | Class | open at T-box, closed via `vocab/party-vocab.ttl` |
| `pty:GroupMembership` | Class | bare; `memberOccupancy`, `memberOf`, `share` each cardinality 1 |
| `pty:Delegation` | Class | `fnd:Evidenced`, `fnd:TemporallyScoped`; `delegatesFrom`, `delegatesTo` each cardinality 1 |
| `pty:occupiedBy` | Object property | Functional; optional |
| `pty:inRole` | Object property | Functional; required |
| `pty:memberOccupancy` | Object property | Functional; required |
| `pty:memberOf` | Object property | Functional; required; inverse of `hasParticipant` |
| `pty:hasParticipant` | Object property | inverse of `memberOf`; entailed, not independently asserted |
| `pty:share` | Data property | Functional; `xsd:decimal`; proportion, not absolute amount |
| `pty:hasCompositionRule` | Object property | Functional; required |
| `pty:delegatesFrom` | Object property | not globally functional; cardinality 1 per `Delegation` |
| `pty:delegatesTo` | Object property | not globally functional; cardinality 1 per `Delegation` |

Six classes mutually disjoint (§6).
