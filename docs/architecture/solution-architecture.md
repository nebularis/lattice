<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# LATTICE Solution Architecture — Consolidated Reference

*A single-document synthesis of the whole repository: purpose, architecture, layer designs, and embedded DL encodings. Written for consumption by another AI agent doing design review or extension work, and secondarily by humans. Compressed on purpose — see [§0](#0-how-to-read-this-document) for the DL notation used.*

Generated from the repository state as of this writing. Where a layer's content does not exist yet, this document says so explicitly rather than inventing it — see [§3](#3-implementation-status) for the authoritative state.

---

## 0. How to Read This Document

Each populated layer gets: purpose/scope, key design decisions (the *why*, not repeated across layers), a compressed DL encoding of every class/property, and an axiom index table. The DL encoding uses standard description-logic shorthand, not Turtle:

| Symbol | Meaning |
|---|---|
| `⊑` | `rdfs:subClassOf` / `rdfs:subPropertyOf` |
| `⊓` | conjunction (a class combines these parents/restrictions) |
| `∃r.C` | `owl:someValuesFrom` restriction on property `r` to class `C` |
| `=n r.C`, `≥n r.C`, `≤n r.C` | exact/min/max cardinality on `r` (range `C` where relevant) |
| `r⁻` | `owl:inverseOf` |
| `Func`, `Asym`, `Irref`, `Trans` | property characteristics (Functional, Asymmetric, Irreflexive, Transitive) |
| `A ⊥ B` | `owl:disjointWith` / `AllDisjointClasses` |
| `dom/range` | `rdfs:domain` / `rdfs:range` |

A class with no restrictions listed is a bare class (no cardinality constraints of its own). "Mixin" means the class exists to be a `subClassOf` parent for domain classes defined in higher layers; it is rarely instantiated on its own. Every class and property below also carries an `rdfs:comment` (one-line definition) and an `fnd:utility` annotation (usage guidance) in the source; these are folded into the prose rather than repeated verbatim, to keep this document's token footprint down. Consult the layer's own `README.md` or `spec/*.ttl` for the exact annotation strings if needed.

---

## 1. What LATTICE Is

LATTICE is a domain-neutral semantic framework (OWL + SHACL + SKOS) for representing governing instruments — contracts, protocols, agreements, policies, entitlement schemes, any document or system that defines obligations, eligibility conditions, and lifecycle behaviour — as structured, queryable, versioned RDF graphs.

It is the middle of a three-part picture:

- **MORK** (Mapping Ontological & Representational Knowledge) — a general-purpose, SKOS-based mapping vocabulary and pipeline for aligning heterogeneous source data (schemas, records, free text) onto a target ontology's T-Box/A-Box/R-Box, using AI-proposed hypotheses validated by deterministic machinery (OWL reasoning, SHACL, Formal Concept Analysis over co-occurrence). MORK ships inside this repository (`mork/`) and is domain-agnostic; `mork/targets/` (currently empty) is where it would be configured to target LATTICE specifically, but MORK itself does not depend on LATTICE.
- **LATTICE proper** — the six-layer ontology substrate this document mostly covers, designed to be extended per-industry.
- **SPC** (Subject-oriented Process Calculus) — a *planned* formal mechanism for session-typed orchestration between agents (human, AI, computational) whose data MORK has mapped and whose roles/obligations/eligibility LATTICE models. SPC gives the live exchange between agents a contract grounded in the same ontology. **SPC has no implementation in this repository at all** — it exists only as a named concept in the root README's overview. Anyone extending this project toward orchestration is starting from zero here, not from a partially-built spec.

### The six LATTICE layers

| Layer | Kind | Models | Namespace prefix | Depends on |
|---|---|---|---|---|
| Foundation | Substrate | Identity/versioning, evidence, temporal scoping, governance status | `fnd:` | — |
| Vocabulary | Substrate | Governed binding of external concept schemes into other layers' properties | `voc:` | Foundation |
| Party | Substrate | Actors, roles, role occupancy, participation groups, delegation | `pty:` | Foundation, Vocabulary |
| Eligibility | Substrate | Admissibility: conditions, unresolved questions, decisions | `elg:` | Foundation, Vocabulary, Party |
| Behaviour | Substrate | State, transition, trigger, guard, effect | `bhv:` | Foundation, Vocabulary, Party, Eligibility, Instrument |
| Instrument | Applied domain ontology | Generic governing-document shape: Provision → Obligation → Qualifier | `ins:` | Foundation, Vocabulary, Party |

Dependency order, as stated in the root README:

```
foundation
    └── vocabulary
            └── party
                    ├── instrument
                    ├── eligibility
                    └── behaviour   (imports instrument, eligibility, party)
```

Instrument is a first applied ontology on the substrates, not the only possible one — a different applied domain (device lifecycle, access-control entitlement, asset maintenance) could sit atop Instrument or replace it, composing with Party/Eligibility/Behaviour through its own `projection/` contracts without touching the core layers.

Layer-crossing composition rules (stated once here, they recur throughout the layer sections below):

- **Guard calls Eligibility.** A Behaviour transition's guard is, in the general case, an Eligibility decision (conditions, unresolved questions, results).
- **Effects write into Instrument or Party.** A transition firing can create/modify an Obligation, or populate a Role Occupancy that was contingent until that moment.
- **Role Occupancy is itself stateful**, governed by the same State/Trigger/Effect apparatus as an Obligation — this is the mechanism that lets a party unconnected to an instrument be bound in later, by the instrument's own design (see Party §4, `pty:RoleOccupancy`).

---

## 2. Repository Conventions

**Per-layer template.** Every layer directory follows the same structure, populated as needed:

```
<layer>/
├── README.md          # literate spec: prose + fenced turtle-spec blocks == the T-box/R-box source of truth
├── spec/<layer>.ttl    # compiled OWL, mechanically extractable from README.md's turtle-spec fences
├── shapes/
│   ├── structural.ttl   # SHACL property shapes (local, per-instance)
│   ├── constraints.ttl  # SHACL-SPARQL, whole-graph conditions (e.g. sh:in closed-world enums)
│   └── rules.ttl        # SHACL-SPARQL rules materialising derived facts
├── vocab/<layer>-vocab.ttl   # mechanism-intrinsic named individuals only, never business vocabulary
├── projection/<other-layer>.ttl   # this layer's declared contracts to/from another layer
├── execution/          # generated runtime artefacts + regeneration docs (invalidation-policy.md etc)
├── examples/           # single-layer worked instances
└── test/               # this layer's own shape/rule tests
```

**Literate-spec ⇄ compiled-ttl duality.** A layer's `README.md` is authoritative. Each class/property is documented once, with a *Definition* (→ `rdfs:comment`), a *Utility* paragraph (→ `fnd:utility`), and a fenced code block. Two fence tags matter: ` ```turtle-spec ` is genuine specification content, extracted in document order and concatenated with the layer's prefix block to produce `spec/<layer>.ttl`; ` ```turtle-example ` is illustration only and is never extracted. This convention was tightened after an early extraction pass over Foundation's document pulled in its own template illustration by mistake — worth knowing if you're asked to regenerate a `spec/*.ttl` from its README, or vice versa (walk classes/properties, render `rdfs:comment` as Definition and `fnd:utility` as Utility). The two artefacts are designed not to drift apart under this discipline: drift can only happen if someone edits the rendered Markdown prose directly instead of the annotation value it came from.

**`vocab/` vs domain vocabulary — a hard boundary.** `vocab/` folders hold only small, mechanism-intrinsic enumerations (trigger kind, role type, composition-rule type) — closed-by-default sets that are part of *how the mechanism works*, not what a domain calls things. Actual business vocabularies (product codes, jurisdictions, currencies) never appear in this repository; `vocabulary/`'s `SchemeContract` mechanism is precisely how a downstream implementation supplies its own without touching core specs. If a proposed `vocab/` addition is hard to justify as mechanism rather than domain, that difficulty is the signal.

**Governance is separate from every layer it checks.** `governance/` (currently an empty scaffold — `parity/`, `scheme-contracts/`, `shapes/`, all `.gitkeep` only) is meant to run over the union graph, enforcing scheme-contract compliance, deprecation posture, and cross-layer parity in CI, rather than living inside any one module.

**Two licences, split by content type.** `.ttl` files and `tools/` (the reference implementation, also currently empty) are MPL 2.0 — copyleft only on the modified file itself, no obligation on what you build atop it. `.md` files (docs, specs, layer READMEs) are CC BY-SA 4.0. Every file requires a one-line SPDX header as its first non-blank line (`# SPDX-License-Identifier: MPL-2.0` or `<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->`), checked by `reuse lint` in CI. `spec/`, `shapes/`, `vocab/`, `projection/` never contain executable code — that boundary is CI-enforced too.

**AI-assisted contributions** are welcome but carry disclosure obligations (`GENAI_CONTRIBUTION.md`): a `Generated-by:` commit trailer, a PR-description provenance section, and — specific to this project, not derived from any licensing concern — a check that AI-drafted ontology content holds the same domain-neutral line as hand-drafted content. The stated risk: generative models drift toward heavily-represented training-data domains (insurance, lending) when asked for an unprompted example, which is exactly the kind of drift `vocab/`'s mechanism-vs-domain boundary and the cross-domain worked examples (`examples/employment.ttl` etc, currently empty placeholders) are designed to catch.

**Namespace convention.** Base `https://www.nebularis.org/neuro-semantic/lattice/`, one hash namespace per layer under that base (hash rather than slash namespaces, so every term in a layer resolves with one retrieval of that layer's document). See the prefix table in §1.

---

## 3. Implementation Status

This is the section to read before recommending any change — most of the six-layer picture described in the root README **does not exist as content yet**. What follows is the actual, verified-by-file-size state of the tree, not the aspirational structure.

| Layer / area | README (spec prose) | `spec/*.ttl` | `shapes/*.ttl` | `vocab/*.ttl` | `projection/*.ttl` | Status |
|---|---|---|---|---|---|---|
| Foundation | 434 lines, complete | 230 lines, complete | empty | empty (no individuals yet — `Draft/Reviewed/Active/Superseded` not declared) | n/a | **Fully specified T-box** |
| Vocabulary | complete | 81 lines, complete | empty | n/a | n/a (contracts belong in consuming layers) | **Fully specified T-box** |
| Party | 359 lines, complete | 202 lines, complete | empty | 75 lines, 7 named individuals, complete | `behaviour.ttl` empty | **Fully specified T-box + vocab** |
| Eligibility | **empty (0 bytes)** | **empty** | empty | empty | `party.ttl` empty | **Not authored** |
| Behaviour | **empty (0 bytes)** | **empty** | empty | empty | `eligibility.ttl`, `instrument.ttl`, `party.ttl` all empty | **Not authored** — only `execution/{benchmark-pack,invalidation-policy,split-plan}.md` exist as filenames, also empty |
| Instrument | **empty (0 bytes)** | **empty** | empty | empty | `party.ttl` empty | **Not authored** |
| Governance | empty | n/a | empty | n/a | n/a | **Not authored** — scaffold only |
| MORK | 657 lines, narrative "for dummies" guide (not literate-spec format) | `Mork.ttl` 1888 lines + `Mork.owl`, complete and large | empty | n/a | n/a | **Fully specified, pre-existing/independent vocabulary** — richer and older in style (OWL-API generated, SKOS-annotation-heavy) than the newer literate-spec layers |
| SPC | mentioned in root README only | — | — | — | — | **No content anywhere** |
| Root `examples/*.ttl` (employment, lending-covenant, saas-subscription, clinical-trial) | — | all four files 0 bytes | — | — | — | **Not authored** |
| `docs/adr/`, `docs/operational-guidance.md`, `docs/validation-and-test-plan.md`, `docs/architecture/technology-options.md` | — | — | — | — | — | Present as filenames; `docs/adr/` and this file (prior to this write-up) were empty. `operational-guidance.md` and `validation-and-test-plan.md` were not inspected for this document — check directly before relying on them. |
| `tools/`, `scripts/` | — | — | — | — | — | **Empty** (`.gitkeep` only) — no reference implementation, no compiler, no extraction tooling, no `scaffold-lattice.sh` despite `CONTRIBUTING.md` referencing it |

**Practical implication for anyone extending this repository:** Foundation, Vocabulary, and Party form a complete, internally consistent, three-layer T-box that MORK-style tooling or a hand-written populated graph could already build on for actor/role/versioning/evidence/governance-state modelling. Eligibility, Behaviour, Instrument, Governance, SPC, the reference tooling, and every worked example are green-field. The only concrete guidance for their eventual shape is: (a) the purpose/scope sentence each empty layer's directory presence and the root README imply, (b) forward references already made from Party's own document (`ins:Obligation`, `ins:fulfilledBy`, a Behaviour-driven Effect setting `pty:occupiedBy`), and (c) the general composition rules in §1. These are collected in [§7](#7-unbuilt-layers-scope-implied-by-cross-reference).

---

## 4. Foundation Layer (`fnd:`)

### 4.1 Purpose

Four independent, composable mixin capabilities: persistent identity/versioning, evidential support, temporal scoping, governance status. Foundation's own governance-status concept is a bare value, not a lifecycle with transitions — a downstream layer wanting triggers and guards around that value composes Behaviour on top of it.

### 4.2 Design decisions

- **PROV-O alignment for evidence only.** `fnd:Evidence ⊑ prov:Entity`, `fnd:assertedBy ⊑ prov:wasAttributedTo`. Temporal scoping deliberately does *not* align with OWL-Time's Instant/Interval apparatus (which would force `validFrom`/`validTo` to be individuals rather than plain `xsd:dateTime` literals) — a considered, reversible asymmetry, not an oversight.
- **Four focused mixins, not one `Governed` god-class.** A single class carrying all four capabilities would force every adopter to take all four; independent, non-disjoint mixins let a class pick exactly what it needs.
- **`GovernanceState` open at T-box, closed via SHACL.** OWL's open-world assumption means the closed enumeration (`Draft`/`Reviewed`/`Active`/`Superseded`, not yet declared anywhere) belongs in `shapes/constraints.ttl` as `sh:in` over named individuals, not in the class definition itself.

### 4.3 DL Encoding

```
Annotation property: fnd:utility  (concise usage explanation; carried by every term below)

Classes:
  fnd:Version          ⊑ =1 hasIdentity.PersistentIdentity
  fnd:PersistentIdentity ⊑ ≥1 hasVersion.Version                    [hasVersion ≡ hasIdentity⁻]
  fnd:Evidenced         (mixin, no own restriction — target of hasEvidence)
  fnd:Evidence          ⊑ prov:Entity ⊓ ≥1 supports.Evidenced ⊓ =1 recordedAt.xsd:dateTime
  fnd:TemporallyScoped  ⊑ =1 hasTemporalScope.TemporalScope
  fnd:TemporalScope     ⊑ =1 validFrom.xsd:dateTime               [validTo optional, ≤1]
  fnd:Governable        ⊑ =1 hasGovernanceState.GovernanceState
  fnd:GovernanceState   (bare; enumeration deferred to vocab/ + SHACL sh:in)

Disjointness:
  AllDisjoint( Version, PersistentIdentity, Evidence, TemporalScope, GovernanceState )
  Evidenced ⊥ Evidence
  TemporallyScoped ⊥ TemporalScope
  Governable ⊥ GovernanceState

Object properties:
  hasIdentity     : Version → PersistentIdentity, Func, inv(hasVersion)
  hasVersion      : PersistentIdentity → Version                          (inverse-functional, entailed)
  supersededBy    : Version → Version, Asym, Irref                        (NOT Transitive — walk the chain to reach latest)
  hasEvidence     : Evidenced → Evidence, inv(supports)                    (not Func — accumulates over time; no min — absent is normal)
  supports        : Evidence → Evidenced
  assertedBy      : Evidence → prov:Agent, ⊑ prov:wasAttributedTo
  hasTemporalScope: TemporallyScoped → TemporalScope, Func
  hasGovernanceState: Governable → GovernanceState, Func

Data properties:
  recordedAt : Evidence → xsd:dateTime, Func
  validFrom  : TemporalScope → xsd:dateTime, Func, required
  validTo    : TemporalScope → xsd:dateTime, Func, optional
```

### 4.4 Axiom Index (summary table)

| Term | Kind | Key characteristics |
|---|---|---|
| `fnd:Version` | Class/mixin | `hasIdentity` = 1 |
| `fnd:PersistentIdentity` | Class | `hasVersion` ≥ 1 |
| `fnd:Evidenced` | Class/mixin | — |
| `fnd:Evidence` | Class | `⊑ prov:Entity`; `supports` ≥ 1; `recordedAt` = 1 |
| `fnd:TemporallyScoped` | Class/mixin | `hasTemporalScope` = 1 |
| `fnd:TemporalScope` | Class | `validFrom` = 1 |
| `fnd:Governable` | Class/mixin | `hasGovernanceState` = 1 |
| `fnd:GovernanceState` | Class | open T-box; closed via SHACL |
| `hasIdentity`/`hasVersion` | Obj. prop. | Functional / inverse pair |
| `supersededBy` | Obj. prop. | Asymmetric, Irreflexive, not Transitive |
| `hasEvidence`/`supports` | Obj. prop. | inverse pair, not Functional |
| `assertedBy` | Obj. prop. | subPropertyOf `prov:wasAttributedTo` |
| `hasTemporalScope` | Obj. prop. | Functional |
| `hasGovernanceState` | Obj. prop. | Functional |
| `recordedAt`, `validFrom`, `validTo` | Data prop. | all Functional, `xsd:dateTime` |

### 4.5 Worked pattern (illustrative, not part of the spec)

A domain class from a higher layer (e.g. `ins:Obligation`, not defined in Foundation) composes mixins directly:

```
ins:Obligation ⊑ fnd:Version ⊓ fnd:Evidenced ⊓ fnd:TemporallyScoped
```

An ordinary populated instance does *not* take `fnd:Governable` — that mixin is for specification artefacts (a wording template, a SHACL shape) under review, not for ordinary contract facts.

### 4.6 Open items

- PROV-O alignment axioms (§4.3's `⊑ prov:Entity`, `⊑ prov:wasAttributedTo`) are candidates for splitting into a separate optional import module — not built.
- `GovernanceState`'s four named individuals belong in `vocab/foundation-vocab.ttl` and are **not yet declared anywhere in the repository** — this is a real gap: nothing currently instantiates `Draft`/`Reviewed`/`Active`/`Superseded`, so any downstream layer or example that references `fnd:Active` (Vocabulary's own worked example does exactly this) is using a forward reference to a term that does not exist yet.
- A same-identity integrity check on `supersededBy` (two versions being superseded must share one `PersistentIdentity`) belongs in `shapes/constraints.ttl` as SHACL-SPARQL, not attempted as an OWL property chain — not built.
- Turtle checked by manual review and extraction-procedure testing only, not run through an actual OWL/Turtle parser (no parser available in the drafting environment) — running `riot` or `rdflib` over `spec/foundation.ttl` (and the other compiled `.ttl` files) is a real outstanding validation step, not merely optional polish.

---

## 5. Vocabulary Layer (`voc:`)

### 5.1 Purpose

Governs how external, domain-specific concept schemes bind into other layers' concept-valued properties, without those layers naming a domain concept directly. Builds on W3C SKOS, adding governed scheme-level versioning and a structural contract mechanism binding a property to a scheme neither side knows about in advance. Vocabulary does **not** resolve a fuzzy label to a concept (that is MORK's job) — it only defines what a valid binding looks like structurally.

### 5.2 Design decisions

- **Scheme-level versioning through Foundation; concept-level versioning explicitly out of scope.** A `ConceptScheme` is a `fnd:Version`; an individual `skos:Concept` gets no independent version thread — tracking meaning drift of one concept across scheme versions is left unaddressed.
- **`SchemeContract` is structural only — never encodes what a scheme is *about*.** It constrains which property, which scheme, and what governance state that scheme must hold; the aboutness is prose, supplied by whichever domain ontology extends the framework.
- **Concept-level constraints (excluding deprecated concepts, requiring leaf concepts) deliberately deferred** as a plausible future `SchemeContract` extension.
- SKOS alignment is stated once, in the Alignments section, not duplicated inline (a stricter convention than Foundation's own document follows for its PROV-O alignment — noted as a tidy-up item against Foundation).

### 5.3 DL Encoding

```
Classes:
  voc:ConceptScheme   ⊑ skos:ConceptScheme ⊓ fnd:Version ⊓ fnd:Governable
  voc:SchemeContract  ⊑ fnd:Version ⊓ fnd:Governable ⊓ ≥1 constrainsProperty

Disjointness:
  ConceptScheme ⊥ SchemeContract
  ConceptScheme ⊥ skos:Concept

Object properties:
  constrainsProperty     : SchemeContract → rdf:Property                (punning — points at a property defined elsewhere)
  requiresGovernanceState: SchemeContract → fnd:GovernanceState          (disjunctive if multi-valued: any one value suffices; optional)
  boundScheme            : SchemeContract → ConceptScheme, Func          (optional — unbound is the normal starting state)
```

### 5.4 Axiom Index

| Term | Kind | Key characteristics |
|---|---|---|
| `voc:ConceptScheme` | Class | `⊑ fnd:Version, fnd:Governable, skos:ConceptScheme`; `⊥ voc:SchemeContract, skos:Concept` |
| `voc:SchemeContract` | Class | `⊑ fnd:Version, fnd:Governable`; `constrainsProperty` ≥ 1 |
| `voc:constrainsProperty` | Obj. prop. | dom `SchemeContract`, range `rdf:Property` |
| `voc:requiresGovernanceState` | Obj. prop. | dom `SchemeContract`, range `fnd:GovernanceState`; optional, disjunctive |
| `voc:boundScheme` | Obj. prop. | Functional; optional |

### 5.5 Worked pattern (illustrative)

```
# Authored once, alongside ins:hasPerilType's own definition (Instrument, not yet written):
ex:peril-contract a voc:SchemeContract ;
    voc:constrainsProperty ins:hasPerilType ;
    voc:requiresGovernanceState fnd:Active .        # forward reference — fnd:Active not yet declared, see §4.6

# Bound later, independently, by a downstream implementation:
ex:acme-peril-codes-v2 a voc:ConceptScheme ;
    fnd:hasIdentity ex:acme-peril-codes-identity ;
    fnd:hasGovernanceState fnd:Active .
ex:peril-contract voc:boundScheme ex:acme-peril-codes-v2 .
```

`ins:hasPerilType` itself is never named in Vocabulary's own spec — only in this illustration, demonstrating the contract mechanism constrains a property without ever knowing what it is about.

### 5.6 Open items

- Named `SchemeContract`/`ConceptScheme` individuals (the actual authored contracts, e.g. Instrument's peril-type contract) belong in each consuming layer's own files and in `governance/scheme-contracts/` — none exist yet (both Instrument and `governance/scheme-contracts/` are empty).
- Same "not run through a parser" caveat as Foundation.

---

## 6. Party Layer (`pty:`)

### 6.1 Purpose

Actor, Role, and the reified qualified-relation individual (Role Occupancy) connecting them, scoped and time-bound; Participation Groups with shares/composition rules; Delegation between an accountable role and a performing one — all built on that reification. Imports Foundation + Vocabulary; imported by Instrument, Eligibility, Behaviour. Upward references (an Obligation's obligor/obligee, an Effect populating a contingent occupancy, a Guard testing a delegation's scope) are deliberately left to the higher layer's own `projection/` files — Party never depends upward.

### 6.2 Design decisions

- **`RoleOccupancy` has no property pointing back at what it's scoped to** (no `withinInstrument` ranging over `ins:Instrument`) — that would create an upward dependency Party cannot have. Scoping is established entirely from the referencing (higher-layer) side.
- **`occupiedBy` optional, `inRole` required** — the formal mechanism for contingent role occupancy: a role designed into an instrument from the outset, unoccupied until some triggering event binds an actor.
- **Group membership is its own reified class (`GroupMembership`), not a property on `RoleOccupancy`.** Share is a property of *participating in a specific group*; putting it directly on the occupancy would be ambiguous if one occupancy ever belonged to more than one group. `GroupMembership` reifies participation the same way `RoleOccupancy` itself reifies Actor-in-Role.
- **`Role` and `CompositionRule` are open at T-box, closed-by-default in `vocab/party-vocab.ttl`.** "Closed" = closed-by-default, extensible by a downstream implementation supplying its own named individuals plus a correspondingly extended/overridden SHACL shape — not a permanent ceiling.
- **`Delegation` carries no formal scope property** — formalising one would either duplicate Eligibility's mechanism or create an upward dependency. `Delegation` states only that a performing occupancy discharges an accountable one; whether performance is *within scope* is composed on top by Eligibility.
- **`Actor` and `Role` are bare classes** — no Foundation mixins, no internal structure; a domain adds whatever identification fields it needs via subclassing.

### 6.3 DL Encoding

```
Classes:
  pty:Actor              (bare)
  pty:Role               (bare; open T-box, closed-by-default in vocab/party-vocab.ttl)
  pty:RoleOccupancy      ⊑ fnd:Version ⊓ fnd:Evidenced ⊓ fnd:TemporallyScoped ⊓ =1 inRole.Role
  pty:ParticipationGroup ⊑ fnd:Version ⊓ fnd:Evidenced ⊓ =1 hasCompositionRule.CompositionRule ⊓ ≥1 hasParticipant.GroupMembership
  pty:CompositionRule    (bare; open T-box, closed-by-default in vocab/party-vocab.ttl)
  pty:GroupMembership    ⊑ =1 memberOccupancy.RoleOccupancy ⊓ =1 memberOf.ParticipationGroup ⊓ =1 share.xsd:decimal
  pty:Delegation         ⊑ fnd:Evidenced ⊓ fnd:TemporallyScoped ⊓ =1 delegatesFrom.RoleOccupancy ⊓ =1 delegatesTo.RoleOccupancy

Disjointness:
  AllDisjoint( Actor, Role, RoleOccupancy, ParticipationGroup, GroupMembership, Delegation )

Object properties:
  occupiedBy       : RoleOccupancy → Actor, Func                          (optional — unset = designed-in-but-unfilled, the contingent-occupancy state)
  inRole           : RoleOccupancy → Role, Func, required
  memberOccupancy  : GroupMembership → RoleOccupancy, Func, required
  memberOf         : GroupMembership → ParticipationGroup, Func, required, inv(hasParticipant)
  hasParticipant   : ParticipationGroup → GroupMembership                  (entailed inverse; typically populated by query, not asserted directly)
  hasCompositionRule: ParticipationGroup → CompositionRule, Func, required
  delegatesFrom    : Delegation → RoleOccupancy, cardinality 1 per Delegation individual, NOT globally functional (an accountable occupancy may have several Delegations over time/in parallel)
  delegatesTo      : Delegation → RoleOccupancy, cardinality 1 per Delegation individual, NOT globally functional (one performer may discharge several accountable occupancies)

Data properties:
  share : GroupMembership → xsd:decimal, Func   (proportion, e.g. 0.40 for 40% — not an absolute amount; add a separate property for fixed amounts)

Named individuals (vocab/party-vocab.ttl — baseline, extensible):
  Roles:            pty:Obligor, pty:Obligee, pty:Guarantor, pty:Accountable, pty:Performing
  CompositionRules: pty:SeveralOnly, pty:JointAndSeveral
```

Role individuals and their intent: `Obligor`/`Obligee` are the direction-of-obligation pair (`Obligee` doubles as the role a contingent occupancy is typed with once eventually filled). `Accountable`/`Performing` are the two sides of `Delegation` (`delegatesFrom` always points at an `Accountable` occupancy, `delegatesTo` always at a `Performing` one). `Guarantor` backs another occupancy's obligation, becoming answerable on that occupancy's default — but **has no mechanism of its own yet**: it needs Instrument's `Obligation` and a Behaviour trigger together (contingent liability activating on default), and is flagged as the least mechanically complete individual in the baseline.

Composition-rule individuals: `SeveralOnly` — each member's exposure independently capped, a defaulting member's shortfall is simply unmet, does not redistribute. `JointAndSeveral` — any member may be called for the full obligation, with a right of recourse against the others afterward (the group's internal contribution accounting is a separate concern this rule does not resolve).

### 6.4 Axiom Index

| Term | Kind | Key characteristics |
|---|---|---|
| `pty:Actor` | Class | bare |
| `pty:Role` | Class | bare, open-T-box/closed-by-default |
| `pty:RoleOccupancy` | Class | `Version, Evidenced, TemporallyScoped`; `inRole` = 1 |
| `pty:ParticipationGroup` | Class | `Version, Evidenced`; `hasCompositionRule` = 1; `hasParticipant` ≥ 1 |
| `pty:CompositionRule` | Class | bare, open-T-box/closed-by-default |
| `pty:GroupMembership` | Class | bare; `memberOccupancy`, `memberOf`, `share` each = 1 |
| `pty:Delegation` | Class | `Evidenced, TemporallyScoped`; `delegatesFrom`, `delegatesTo` each = 1 |
| `occupiedBy` | Obj. prop. | Functional; optional |
| `inRole` | Obj. prop. | Functional; required |
| `memberOccupancy` | Obj. prop. | Functional; required |
| `memberOf` / `hasParticipant` | Obj. prop. | inverse pair; `memberOf` Functional+required |
| `share` | Data prop. | Functional; `xsd:decimal`; proportion |
| `hasCompositionRule` | Obj. prop. | Functional; required |
| `delegatesFrom` / `delegatesTo` | Obj. prop. | not globally Functional; = 1 per Delegation |

Six classes mutually disjoint. No `owl:Alignments` section — Party introduces no external-vocabulary dependency (unlike Vocabulary/SKOS or Foundation/PROV-O); everything here is LATTICE-internal or reuse of Foundation's mixins.

### 6.5 Worked patterns (illustrative)

**Several liability** — three occupancies sharing one obligation, none liable beyond its own share:

```
ex:group-1 a pty:ParticipationGroup ; pty:hasCompositionRule pty:SeveralOnly .
ex:occ-a a pty:RoleOccupancy ; pty:inRole pty:Obligor ; pty:occupiedBy ex:syndicate-a .
ex:mem-a a pty:GroupMembership ; pty:memberOccupancy ex:occ-a ; pty:memberOf ex:group-1 ; pty:share "0.40" .
# occ-b/mem-b (0.35), occ-c/mem-c (0.25) follow the same pattern.
```
Note what is *absent*: nothing here says which obligation the group fulfils — that reference (`ins:fulfilledBy` or similar) is declared from Instrument's side, in Instrument's own projection file, pointing *at* the group.

**Contingent occupancy + delegation split:**

```
ex:third-party-occ a pty:RoleOccupancy ; pty:inRole pty:Obligee .     # inRole set, occupiedBy unset
# Later, a Behaviour Effect (not Party's own mechanism) adds:
#   ex:third-party-occ pty:occupiedBy ex:claimant-x .

ex:sponsor-occ a pty:RoleOccupancy ; pty:inRole pty:Accountable .
ex:cro-occ a pty:RoleOccupancy ; pty:inRole pty:Performing .
ex:delegation-1 a pty:Delegation ;
    pty:delegatesFrom ex:sponsor-occ ; pty:delegatesTo ex:cro-occ .
```

### 6.6 Open items

- `party/spec/party.md` §4 should be tightened to describe `CompositionRule` and `Role` as closed-by-default-and-extensible consistently (currently one is stated more strongly "closed" than the vocab document's own §4 implies).
- `Guarantor`'s activation mechanism is unbuilt — depends on Instrument's `Obligation` and a Behaviour trigger, neither of which exists yet.
- The `sh:in` constraint enumerating the baseline `Role`/`CompositionRule` individuals (and the pattern for a downstream implementation extending or overriding it) belongs in `shapes/constraints.ttl` — not built for any layer.

---

## 7. Unbuilt Layers: Scope Implied by Cross-Reference

Eligibility, Behaviour, and Instrument have no specification content (§3). Their eventual shape is not invented here, but the following is directly evidenced by forward references already present in Party's and the root README's text, and should anchor any future authoring rather than being re-derived from scratch:

**Instrument (`ins:`)** — "the generic shape of a governing document: Provision → Obligation → Qualifier." Forward-referenced terms: `ins:Obligation` (a domain class expected to compose `fnd:Version ⊓ fnd:Evidenced ⊓ fnd:TemporallyScoped`, per Foundation's own worked example), `ins:hasPerilType` (an example of a property meant to be bound via a `voc:SchemeContract`, per Vocabulary's worked example), `ins:fulfilledBy` or similar (the property, declared from Instrument's side, pointing at a `pty:ParticipationGroup` that fulfils an Obligation — Party explicitly does not declare the reverse direction). Instrument's own `projection/party.ttl` is where an Obligation's `obligor`/`obligee` pointing at `pty:RoleOccupancy` would be declared.

**Eligibility (`elg:`)** — "admissibility criteria: conditions, unresolved questions, and decisions." Composes with Party (`eligibility/projection/party.ttl`, currently empty) presumably to test whether a specific `RoleOccupancy` or `Delegation` satisfies an admissibility condition — this is the mechanism Party's own document names as testing "a delegation's scope" (§6.2 above) without formalising it itself.

**Behaviour (`bhv:`)** — "State, transition, trigger, guard, and effect." Imports Instrument, Eligibility, and Party (the only layer with three upstream imports, per the dependency diagram). Composition rule already fixed by §1/root README: a transition's **guard is, in the general case, an Eligibility decision**; a transition's **effect can create/modify an `ins:Obligation`, or populate a contingent `pty:RoleOccupancy`'s `occupiedBy`** (exactly the mechanism Party's §6.5 worked example defers to "a separate Effect, not Party's own"). `behaviour/projection/instrument.ttl` is explicitly called out in the root README as carrying a design note on Behaviour's non-presupposition of a target domain — worth reading first if that file is ever populated, since it is referenced as already having something to say despite being empty in this checkout.

**Governance** — runs over the union graph (not a layer instances live in), enforcing scheme-contract compliance, deprecation posture, cross-layer parity, in CI. `governance/scheme-contracts/` is explicitly where authored `voc:SchemeContract` individuals for cross-cutting concerns would live; `governance/parity/` presumably checks that sibling layers (e.g., all six) maintain structural parity in how they apply the shared per-layer template.

**SPC** — no forward references exist beyond the root README's paragraph (§1 above). Any implementation work here is genuinely green-field; do not assume any hidden design intent beyond "session-typed exchange between agents, grounded in the same ontology Behaviour and Party populate."

Recommendation for an agent asked to author one of these layers: follow the literate-spec convention exactly (§2) — write the `README.md` first with Definition/Utility pairs and `turtle-spec`/`turtle-example` fencing, then extract `spec/<layer>.ttl` mechanically — rather than writing the compiled Turtle directly, to stay consistent with how Foundation/Vocabulary/Party were built and keep the two artefacts from the outset in the non-drifting relationship §2 describes.

---

## 8. MORK (`mrk:` / Mork.ttl `:`)

MORK predates the newer literate-spec layers stylistically — it is a large (1888-line), OWL-API-generated, SKOS-annotation-heavy vocabulary (`skos:definition`, `skos:scopeNote`, `skos:example` used as de facto documentation, rather than the `fnd:utility` convention). It is functionally independent of LATTICE's own layers; LATTICE is one possible mapping *target* for it, not a dependency.

### 8.1 Purpose and architecture

MORK addresses the *n × m* data-integration problem (n sources × m consumers, every change touching all of them) by giving every source-to-ontology alignment a first-class, typed graph representation instead of ad hoc ETL code. Three separated layers, each changing at a different rate:

1. **Intent** — AI-extracted structured meaning from natural language or schema field names, expressed only in general vocabularies (SKOS concepts, standard datatypes) so it stays portable across target ontologies. Never references the target ontology directly.
2. **Mapping** — `mrk:DataMapping` individuals connecting intent to specific target classes/properties/individuals, stratified by which OWL box they touch: T-Box (`exactTBoxMatch`/`broadTBoxCategoryMatch`/`narrowTBoxCategoryMatch` — "this creates/references a class"), A-Box (`exactABoxMatch` and broad/narrow variants — "this creates/references an individual"), R-Box (`exactRBoxMatch`/`inverseRBoxMatch` and broad/narrow variants — "this creates/references a property/relation"). Ordering is derived automatically from this stratification: T-Box before A-Box before R-Box.
3. **Artefact** — deterministic compilation to SHACL shapes, SPARQL queries, SWRL rules, RML transformation mappings. Same validated mapping graph always produces the same artefacts.

**Compilation boundary — the core architectural commitment:** the LLM is never invoked at runtime for anything but *proposing* intent/mapping nodes. Everything downstream of a validation gate (structural SHACL checks, GCI/disjointness consistency checks, type-safety checks against the target ontology) is deterministic — compilation, artefact generation, execution. This buys reproducibility (same validated graph → same artefacts regardless of LLM variance), auditability (every artefact traces back through mapping → intent → original source text), and composability (independently generated mapping fragments compose because they share this algebraic structure).

### 8.2 Class taxonomy (compressed)

```
skos:Concept
  ⊑ mrk:DataConcept        ⊓ ∃conceptScheme.TaxonomyScheme      # abstract concept to be mapped
  ⊑ mrk:DataMapping         ⊓ ∃mappingScheme.MappingScheme        # captures a mapping; usually skos:note-annotated with rationale
       ⊑ mrk:Datum                                                 # explicit individuation of a DataConcept in a target OntologicalScheme
       ⊑ mrk:DeferredContext                                       # placeholder axiom another DataMapping must reference via an object property
       ⊑ mrk:Hypothesis    ≡ ∃(hypothesisMapping⁻).DataMapping     # a mapping supplying supporting evidence for another
       ⊑ mrk:IndexedMapping
       ⊑ mrk:Lookup         ⊓ ∃dataRef.xsd:string                  # base data → named individual; dataRef = source path
       ⊑ mrk:UncertainMapping
  ⊑ mrk:Digraph  (deprecated — use compositeBroaderMapping/compositeNarrowerMapping instead)

mrk:Representation
  ⊑ mrk:IdentifiableElement ⊓ ∃identifier.xsd:string
       ⊑ mrk:Entity          # an entity in a source representation scheme, marked with its native identifier
  ⊑ mrk:Membership           # by convention, only subclassed, never instantiated directly

mrk:Interpolation ≡ ∃interpolationComponent.DataMapping ⊓ ∃interpolationTemplate.xsd:string
  ⊑ skos:OrderedCollection   # positional template ("$1, $2, ...") over an ordered set of component mappings

mrk:MappingScheme     ⊑ skos:ConceptScheme     # captures mappings from a RepresentationScheme to an OntologicalScheme
mrk:RepresentationScheme, mrk:OntologicalScheme, mrk:TaxonomyScheme  — the three source/target scheme kinds
mrk:OwlAxiom
  ⊑ mrk:DeferredConceptIRI, DeferredClassDefinition, DeferredObjectPropertyDefinition,
     DeferredDataPropertyDefinition, DeferredIndividualDefinition, DeferredABoxReference
     # placeholders for axioms a mapping proposes creating, referenced before they formally exist —
     # needed because instances of owl:ObjectProperty in an RDF triple's object position are disallowed
     # by some processing environments (e.g. owlapi); resolved via owl:sameAs once materialised.
mrk:OwlClass, mrk:OwlObjectProperty, mrk:OwlDataProperty     # T-box/R-box element wrappers
mrk:Array, mrk:Collection ⊑ (mrk:OrderedCollection | mrk:UnorderedCollection), mrk:CollectionElement, mrk:AnonymousElement
mrk:Attribute, mrk:Association, mrk:Chaining, mrk:Composition, mrk:Objectification    # structural pattern vocabulary for source schema shapes
mrk:SerializationFormat ⊒ mrk:JSON, mrk:XML, mrk:YAML
mrk:WeightedMatch                                                                     # base for confidence-carrying match assertions
```

### 8.3 Property groups (compressed — ~90 total, grouped by role)

```
Box-stratified match properties (each with broad/narrow/exact variants):
  {exact,broad,narrow}TBoxCategoryMatch, {exact,broad,narrow}ABoxCategoryMatch,
  {exact,broad,narrow}RBoxCategoryMatch, inverseRBoxMatch
  exactTBoxMatch / exactABoxMatch / exactRBoxMatch — direct create-or-reference
  broadCategoryMatch / narrowCategoryMatch — generic (stratum-agnostic) hierarchical match
  broadConceptRole / narrowConceptRole, broadNavigableConceptRole / narrowNavigableConceptRole

Composition / DAG-building operators:
  compositeNarrowerMapping, compositeBroaderMapping, compositeNarrowerTemplate, compositeBroaderTemplate
  broaderApplicative   — apply sub-mappings within a parent mapping's output context
  deferredMapping      — this mapping cannot finish until another completes
  templateMapping / identityTemplateMapping / templateClassMapping  — reusable pattern, instantiated per source
  hypothesisMapping    — supporting-evidence relation between mappings
  dependentMapping, siblingMapping, relatedMapping, placeholderMapping, indicativeMapping, possibleMatch, partialMatch,
  missingOrUnrelatedMatch, incompleteMapping

Confidence / weighting:
  weightedBroader, weightedNarrower, weighting   — carries the 0–100 confidence score; effective confidence
    down a dependency chain = local_confidence × min(child_confidences) (see §8.4)

Structural/lexical/semantic evidence:
  lexicalMatch, semanticMatch, structuralMatch, pathMatch, digraphMatch (deprecated path), digraphOf

Data access / value shaping:
  dataRef, dataInline, data, path, reference, template, identifier, name,
  conceptId, conceptName, conceptIRI, conceptFQNameTemplate, conceptNameTemplate, conceptShortNameTemplate,
  individualIRI, individualName, externalPropertyValue, collectionElementScalarValue, orderedItems, uniqueItems, itemsConstrained

Scheme / membership plumbing:
  conceptScheme, mappingScheme, ontologicalScheme, representationScheme, hasConcept, hasMapping, memberOf, memberProperty,
  mappingFor, mappingIndex, mappingRecommendation, representationOf, representedAs, relatedProperty

Assertion-generation (drive the compiler's SHACL/SWRL/RML output):
  assertsPropertyDomains, assertsPropertyRanges, propertyMappingAssertions, referenceDataMapping, referenceDataPath

Governance annotations:
  mappingNote, userDeclined
```

### 8.4 Formal guarantees and the convergence claim

Category-theoretic framing (profunctors, Galois connections; the README is explicit that using MORK never requires understanding this maths, only trusting what it proves):

- **Tri-stratum inference**, cheapest-first: Recognition (lexical/type similarity, available cold) → Community (co-occurrence clusters detected via Formal Concept Analysis / Leiden — "recognising one community member is evidence for all members," the *acceleration factor*) → Projection (lookup against confirmed prior mappings). By steady state the three strata together are claimed to resolve 90–98% of fields without AI.
- **Convergence theorem** (aspirational/theoretical, not empirically demonstrated in this repository): `ε(t) ≈ K·exp(−(1+d′)·t / (K·ln K))` — fraction of fields still needing help decays with mapping-run count `t`, community acceleration factor `d′`, vocabulary size `K`.
- **Claimed formal properties:** termination, idempotence, determinism (any valid execution order → same output), precedence completeness (ordering derived automatically from the T-Box→A-Box→R-Box stratification, never manually specified), provenance compositionality (every generated axiom traces to mapping → intent → original source).
- **Non-LLM degradation path is explicit and specific:** lexical scoring via a small local sentence transformer (85–92%), type checking via an OWL reasoner (100%, fully symbolic), community detection via FCA (100%, deterministic), constraint validation via SHACL+OWL reasoner (100%), compilation via a rule-based compiler (100%). Roughly 60–85% of pipeline intelligence is claimed deliverable with zero LLM involvement; the LLM is stated to be an accelerator, not a load-bearing dependency.

### 8.5 Relationship to Semantica (external, complementary, not part of this repo)

Semantica (referenced, not present here) is positioned as handling data *acquisition* — ingestion, normalisation, entity extraction, dedup — which MORK deliberately does not address; MORK owns schema modelling, ontological alignment, artefact generation, and AI-output governance. The stated integration point is an adapter layer between Semantica's entity-extraction output and MORK's mapping pipeline — not built, not this repository's concern.

### 8.6 Assessment for a reviewing agent

MORK's vocabulary is real and complete (`Mork.ttl`), but its narrative document (`README.md`) is aspirational in tone throughout ("Our convergence theorem," "should be proven theorems," "we hope to see") — treat the mathematical claims in §8.4 as *design intent the vocabulary was built to support*, not as verified, benchmarked properties of a running system. There is no `tools/` implementation of the compiler, validator, or agents described in Part 6 of the README anywhere in this checkout. If asked to assess MORK's maturity: the T-box is production-ready as a vocabulary; the pipeline, agents, and convergence guarantees are unimplemented specification.

---

## 9. Cross-Layer Composition Patterns (Consolidated)

These recur across the layer sections above and are the load-bearing joints of the whole design — worth having in one place for quick recall:

1. **Mixin composition, not inheritance depth.** Foundation's four mixins (`Version`, `Evidenced`, `TemporallyScoped`, `Governable`) are designed to be combined à la carte on a domain class defined elsewhere (`ins:Obligation ⊑ Version ⊓ Evidenced ⊓ TemporallyScoped`, deliberately *not* `⊓ Governable` — see §4.5).
2. **Reification over direct properties whenever the relation itself needs identity, evidence, or a time scope.** `RoleOccupancy` reifies Actor-in-Role; `GroupMembership` reifies occupancy-in-group; `Delegation` reifies accountable-discharged-by-performing. Each of these could in principle have been a direct property; each was reified instead because the *relation itself* needed to survive change, carry evidence, or scope a share value unambiguously.
3. **Strict downward-only dependency; upward references live in the higher layer's own `projection/` file.** No lower layer (Foundation, Vocabulary, Party) ever names a class or property from a higher layer (Instrument, Eligibility, Behaviour). A lower layer's document may *illustrate* with a higher-layer term (always under an `ins:`/`ex:` prefix explicitly marked as "not part of this layer's own namespace"), but never specifies against it.
4. **Contingent occupancy as the general mechanism for "not yet bound in."** A `RoleOccupancy` can exist with `inRole` set and `occupiedBy` unset — the shared representation for "designed into the instrument from the outset, filled later by an event." What fills it is a Behaviour Effect (unbuilt), never a Party-layer mechanism itself.
5. **Guard = Eligibility decision; Effect = write into Instrument/Party.** The entire Behaviour layer's purpose (as scoped, not yet built) is to be the state machine whose guards delegate truth-evaluation to Eligibility and whose effects are the only sanctioned way anything mutates an Obligation's state or a RoleOccupancy's `occupiedBy`.
6. **`vocab/` baselines are closed-by-default, not closed-permanently.** Both `pty:Role`/`pty:CompositionRule` and (by the same reasoning, though only stated explicitly for the latter) any future layer's mechanism-intrinsic vocab are meant to be extended by a downstream implementation supplying additional named individuals plus a correspondingly extended/overridden SHACL shape — never by a PR against this repository.
7. **`SchemeContract` decouples "this property needs governed values" from "here is the scheme."** The two can be authored months apart by different parties; nothing in the mechanism requires the scheme to exist when the contract is declared.

---

## 10. Open Items and Recommendations (Aggregated)

Ranked by what would most unblock further work, not by section order:

1. **Author Instrument first**, not Eligibility or Behaviour. Both Vocabulary's and Party's worked examples already lean on `ins:` terms (`ins:hasPerilType`, an Obligation shape) that don't exist; Behaviour's own dependency graph needs Instrument imported before it can be usefully specified at all (§1, §7).
2. **Declare `fnd:GovernanceState`'s four named individuals** (`Draft`, `Reviewed`, `Active`, `Superseded`) in `vocab/foundation-vocab.ttl`. Currently a real gap, not a stylistic one — Vocabulary's own worked example already forward-references `fnd:Active`, and any populated graph using governance status today has nothing to actually point at.
3. **Run every existing compiled `.ttl` through an actual OWL/RDF parser** (`riot`/Apache Jena or `rdflib`). Every layer's own "Open Items" section flags this as unverified, checked only by manual review — a cheap, high-value validation pass before any of it is treated as load-bearing.
4. **Build `shapes/constraints.ttl` for Foundation and Party** before extending either layer further — both documents defer specific, named closed-world constraints (the `GovernanceState` enumeration, the `Role`/`CompositionRule` `sh:in` baseline, the `supersededBy` same-identity check) to a SHACL layer that does not exist in any layer yet.
5. **Reconcile Party §4's "closed" language for `CompositionRule`/`Role`** with `party-vocab.ttl`'s own, more precise "closed-by-default, extensible" framing (§6.6) — a small textual fix, not a design change.
6. **Treat MORK's convergence/formal-guarantee claims (§8.4) as design targets, not verified properties**, when recommending its use — there is no benchmarked implementation in this repository to point at.
7. **SPC has zero design surface to build from.** Any request to implement orchestration/session-typing should be scoped as new design work, not treated as filling in an existing gap.
