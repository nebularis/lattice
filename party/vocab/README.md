<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Party Vocabulary

---

## 1. Purpose and Scope

Provides mechanism-intrinsic vocabulary (rather than domain vocabulary) via Vocabulary's scheme-contract mechanism.

## 2. Namespace and Prefixes

Same `pty:` and `fnd:` namespaces as `./spec/party.md`. No new prefixes needed.

```turtle-spec
@prefix pty:  <https://www.nebularis.org/neuro-semantic/lattice/party#> .
@prefix fnd:  <https://www.nebularis.org/neuro-semantic/lattice/foundation#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
```

## 3. How to Read This Document

Same two-tag convention as the layer documents: `turtle-spec` is extracted to produce `party-vocab.ttl`; `turtle-example` (unused in this document — there's nothing here that needs illustrating beyond what §5–6 already show directly) would not be. Concatenate the prefix block above with every `turtle-spec` block from §5 onward, in order.

## 4. Design Decisions

**This is a baseline, not a closed set.** Previous versions had `CompositionRule` "closed in `shapes/constraints.ttl`. The `sh:in` constraint that `shapes/constraints.ttl` will eventually declare constrains against *this* baseline by default — a downstream implementation needing an additional composition rule (such as a proportional cap, layered-cost structure, etc) extends this vocabulary with its own named individuals and correspondingly extends or overrides that specific SHACL shape. "Closed" describes what ships by default, not a ceiling nothing may ever cross.

**`Role` gets the same treatment, for consistency, even though the original document only said this explicitly about composition rules.** There's no principled reason role types would be less extensible than composition rules — both are mechanism-intrinsic baselines a downstream domain may reasonably need to extend (e.g., a "Witness" or "Indemnifier" role, say) without that extension being domain vocabulary in the sense Vocabulary's scheme-contract mechanism exists to gate.

**`Guarantor` is included, and it's the least mechanically complete of the vocabulary here.** Unlike Obligor/Obligee (which `Instrument`'s projection will hang directly off Obligation's direction) and Accountable/Performing (which `Delegation` already formalises), nothing gives Guarantor a mechanism of its own. A guarantee's real content — contingent liability that activates on another occupancy's default — looks like it needs Instrument's Obligation and a Behaviour trigger together, not Party alone. 

## 5. Role Individuals

#### `pty:Obligor`

**Definition.** The role of owing an obligation.

```turtle-spec
pty:Obligor a owl:NamedIndividual, pty:Role ;
    rdfs:label "Obligor"@en ;
    rdfs:comment "The role of owing an obligation." ;
    fnd:utility "The direction-of-obligation counterpart to Obligee. Instrument's Obligation class references a Role Occupancy in this role as its obligor, in Instrument's projection." .
```

#### `pty:Obligee`

**Definition.** The role of being owed an obligation.

```turtle-spec
pty:Obligee a owl:NamedIndividual, pty:Role ;
    rdfs:label "Obligee"@en ;
    rdfs:comment "The role of being owed an obligation." ;
    fnd:utility "The direction-of-obligation counterpart to Obligor. Also the role a contingent occupancy — a third party with no relationship to an instrument until some event binds them in — is typed as, once occupiedBy is eventually set." .
```

#### `pty:Guarantor`

**Definition.** The role of backing another occupancy's obligation, becoming answerable if that occupancy fails to perform.

```turtle-spec
pty:Guarantor a owl:NamedIndividual, pty:Role ;
    rdfs:label "Guarantor"@en ;
    rdfs:comment "The role of backing another occupancy's obligation, becoming answerable if that occupancy fails to perform." ;
    fnd:utility "Named in the original design alongside Obligor, Obligee, Accountable, and Performing, but the least mechanically complete of the five — see §4. Included as a role type; its contingent-activation mechanism is not yet built." .
```

#### `pty:Accountable`

**Definition.** The role that remains answerable for an obligation's performance even when a different occupancy actually carries it out.

```turtle-spec
pty:Accountable a owl:NamedIndividual, pty:Role ;
    rdfs:label "Accountable"@en ;
    rdfs:comment "The role that remains answerable for an obligation's performance even when a different occupancy actually carries it out." ;
    fnd:utility "One side of the delegation split formalised by pty:Delegation. Accountability does not transfer to a Performing occupancy even when performance does." .
```

#### `pty:Performing`

**Definition.** The role that actually carries out an obligation's performance, discharging an Accountable occupancy's obligation without taking on its accountability.

```turtle-spec
pty:Performing a owl:NamedIndividual, pty:Role ;
    rdfs:label "Performing"@en ;
    rdfs:comment "The role that actually carries out an obligation's performance, discharging an Accountable occupancy's obligation without taking on its accountability." ;
    fnd:utility "The other side of the delegation split. A pty:Delegation's delegatesTo always points at an occupancy in this role, whilst delegatesFrom always at one in the Accountable role." .
```

## 6. Composition Rule Individuals

#### `pty:SeveralOnly`

**Definition.** A composition rule under which each member's share of an obligation is independently capped. No member answers for another's shortfall.

```turtle-spec
pty:SeveralOnly a owl:NamedIndividual, pty:CompositionRule ;
    rdfs:label "Several-only"@en ;
    rdfs:comment "A composition rule under which each member's share of an obligation is independently capped; no member answers for another's shortfall." ;
    fnd:utility "If one member defaults, the residual is simply unmet — it does not redistribute onto the remaining members. The baseline case for a Participation Group whose members each bear a bounded, non-aggregating portion of one obligation." .
```

#### `pty:JointAndSeveral`

**Definition.** A composition rule under which any member may be called for the full obligation, subject to a right of recourse against the other members afterward.

```turtle-spec
pty:JointAndSeveral a owl:NamedIndividual, pty:CompositionRule ;
    rdfs:label "Joint and several"@en ;
    rdfs:comment "A composition rule under which any member may be called for the full obligation, subject to a right of recourse against the other members afterward." ;
    fnd:utility "The dual of SeveralOnly: exposure is not capped at a member's own share, but the group's internal contribution rights — who ultimately bears what — are a distinct concern this rule does not itself resolve." .
```

## 7. Axiom Index

| Individual | Type | Notes |
|---|---|---|
| `pty:Obligor` | `pty:Role` | direction, paired with `Obligee` |
| `pty:Obligee` | `pty:Role` | direction, paired with `Obligor`,; also the contingent-occupancy role |
| `pty:Guarantor` | `pty:Role` | activation mechanism TBD |
| `pty:Accountable` | `pty:Role` | `Delegation`'s `delegatesFrom` side |
| `pty:Performing` | `pty:Role` | `Delegation`'s `delegatesTo` side |
| `pty:SeveralOnly` | `pty:CompositionRule` | independently capped shares |
| `pty:JointAndSeveral` | `pty:CompositionRule` | full exposure, right of recourse |

Seven individuals total — the baseline this vocabulary ships with, extensible per §4.

## 8. Open Items

- **`party/spec/party.md` §4 should be tightened** to describe `CompositionRule` (and, for consistency, `Role`) as closed-by-default-and-extensible, matching §4 of this document, rather than the stronger "closed" language it currently uses.
- **Guarantor's activation mechanism** — contingent liability triggered by another occupancy's default — needs Instrument's Obligation and a Behaviour trigger together. Not attempted here, and not really attemptable until both those documents exist.
- **The `sh:in` constraint itself**, and the pattern for how a downstream implementation extends or overrides it, belongs in `shapes/constraints.ttl` and hasn't been built for any layer yet — this document only supplies what that constraint would enumerate by default.
- **Checked by manual syntax review and extraction testing**, not an actual parser, per the same environment caveat as every prior document.
