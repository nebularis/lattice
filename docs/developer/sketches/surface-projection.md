<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Surface Projection Mechanism — Design Sketch

**Generic promotion and shadow-indexing for LATTICE**

**Status:** Sketch (design archived; implementation moved to plan and status documents)  
**Related plan:** [surface-mork-unified-projection-plan.md](../plans/surface-mork-unified-projection-plan.md)  
**Related status:** [surface-mork-unified-projection.md](../status/surface-mork-unified-projection.md)  
**Source:** Distilled from `ontology/surface/docs/surface-projection-design-sketch.md` (2026-09-18)

---

## Overview

The Surface layer provides a generic mechanism for promotion (restating values as direct properties) and indexing (generating lookup symbols for values). Both operations unify under a single abstraction:

> A **surface contract** declares a **read path** from a **carrier** to a **value**, and a **surface form** in which that relationship is restated locally.

This sketch designs the mechanism; implementation details are in [surface-mork-unified-projection-plan.md](../plans/surface-mork-unified-projection-plan.md) (Phases 0–8 complete) and [surface-mork-unified-projection.md](../status/surface-mork-unified-projection.md).

---

## Core Abstraction — Read Path + Surface Form

### Read Path

A property or sequence of properties traversed from a carrier class to a value. Uses SHACL property-path syntax (`sh:path`), supporting:
- **Sequence paths:** `prop1 / prop2 / prop3`
- **Inverse paths:** `^prop`
- **Object and datatype properties**

First slice excludes:
- Alternation (`prop1 | prop2`)
- Zero-or-more (`prop*`)

### Surface Forms

| Form | Mechanism | Example |
|------|-----------|---------|
| **Promotion** | Restate read-path value as direct property on carrier | `CSO:CoverageType` → `FBO:hasLocallySourcingCoverageType` |
| **Nominal Indexing** | Emit one named class per value under a family class | `ScopeCoverageType_Cyber`, subclass of `ScopeCoverageTypeFamily` |
| **Membership Assertion** | Materialize assertions directly without definitions | `x rdf:type ScopeCoverageType_Cyber` |
| **Closure Relation** | Emit relation with ancestor-closed values | `matchesLineOfBusiness(x, a)` for all `a ≥ concept` |
| **Direct Property** | Generate derived property accessible at query time | Like Promotion but without requiring enumeration |

---

## Contract Model

### SurfaceContract

Base abstraction for all surface declarations:

```
srf:SurfaceContract
  - carrier: rdfs:Class (the subject type)
  - readPath: SHACL property-path (traversal to value)
  - surfaceProfile: SurfaceProfile (generation policy)
  - populationBudget: xsd:nonNegativeInteger (optional bound)
  - (inherits from fnd:Version, fnd:Governable)
```

### PromotionContract

Restates a read-path value as direct property:

```
srf:PromotionContract ⊑ srf:SurfaceContract
  - promotesTo: rdf:Property (local dimension property)
  - sourceFidelity: {ExactSource, DerivedSource, CrosswalkExact, CrosswalkInexact}
  - viaMatchRelation: rdf:Property (optional, for scheme-based promotion)
```

**Example:** CSO→FBO sourcing (row 1 of V2 §11.2):
- Carrier: `FBO:ProvisionalPolicy`
- Read path: `CSO:coverageId / CSO:hazardClass`
- Promotes to: `FBO:hasHazardClassDirect`
- Source fidelity: `ExactSource` (hazard classes are authored, not transformed)

### IndexContract

Generates lookup symbols from value populations:

```
srf:IndexContract ⊑ srf:SurfaceContract
  - discriminator: rdf:Property (the distinguished value property)
  - valuePopulation: ValuePopulation (what to index)
  - indexForm: IndexForm (symbol type(s))
  - realisationMode: {DefinitionOnly, Materialised, DefinitionAndMaterialised}
  - namingPolicy: {LocalNameFromValue, QualifiedLocalName, DigestLocalName}
  - closureBasis: rdf:Property (optional; for ClosureRelation form)
  - closureScope: ValuePopulation (optional; bounds the closure)
```

**Example:** Coverage type shadow index (FBO execution):
- Carrier: `FBO:PolicyScope`
- Read path: `FBO:hasCoverageType`
- Discriminator: `FBO:hasCoverageType` (same property)
- Value population: `fbo:CoverageScheme` (bound scheme)
- Index forms: `NominalClass`, `ClosureRelation`
- Realisation: `Materialised`
- Naming: `LocalNameFromValue` with ASCII normalisation
- Closure basis: `skos:broader`
- Closure scope: the same coverage scheme

### ValuePopulation

Abstract type with four implementations:

| Kind | Source | Scope | Example |
|------|--------|-------|---------|
| `ContractBoundPopulation` | `voc:SchemeContract` | Whatever is currently bound | Coverage types (live with scheme rebinding) |
| `ClassExtentPopulation` | `rdfs:Class` | Named individuals, direct subclasses, or transitive | CSO concepts matching a criterion |
| `EnumeratedPopulation` | Explicit members | Finite list | Predefined status values |
| `RangePartitionPopulation` | `qnt:RangeSet` | Continuous range | Monetary brackets (⏳ deferred) |

---

## Derived Tier (Artefacts)

### GeneratedSurface

The output of compilation; one per contract:

```
srf:GeneratedSurface ⊑ fnd:DerivedArtefact
  - coversContract: SurfaceContract
  - readSetEntry: {ReadSetEntry}+ (what was read)
  - symbolCount: {NominalClasses: N, Assertions: M, …}
  - (inherits hash, authority, generation profile)
```

### GeneratedSymbol

Provenance for each emitted symbol:

```
srf:GeneratedSymbol ⊑ fnd:DerivedArtefact
  - inSurface: GeneratedSurface
  - symbolForm: IndexForm
  - fromValue: (omitted for DirectProperty form)
  - denotes: Class or Property (wrapper, avoiding punning)
```

### Read Set

Tracks what was read during generation:

```
srf:ReadSetEntry
  - readSource: (DeclarationSource | PopulationMemberSource | HierarchyBasisSource | …)
  - readVersion: xsd:string
  - readHash: xsd:string
```

---

## Key Design Decisions

### 1. Stack Position

Surface sits low in the substrate, importing Quantification:

```
Foundation
  → Vocabulary
    → Quantification
      ├→ Party, Eligibility, Instrument, Behaviour
      └→ Surface (generic, domain-neutral)
```

**Why low:** Domain-neutral mechanism avoids conceptual overlap with higher layers; ability to name any property via vocabulary punning.

### 2. Conservativity Invariant

**Non-negotiable property:** A surface adds nothing to what the source already means.

- Adding a surface entails no new consequences about source terms
- Removing a surface loses no authored facts
- Surfaces are `Advisory` or `CachedReproducible` authority, never `OperationallyAuthoritative`
- Enables safe regeneration, safe discarding, and correct governance classification

### 3. Authority Ceiling

Generated surfaces may declare only:
- `Advisory` — optional, use at discretion
- `CachedReproducible` — derived and verifiable

**Excluded:** `OperationallyAuthoritative` (would mean index outranks its declaration, violating ADR-A12)

### 4. No Stacking (First Slice)

A surface may not read from another surface. Restriction enforced in shapes.

**Rationale:** Stacked surfaces multiply invalidation scope, make hash provenance a graph rather than a tree, require composition laws for conservativity. Opened only with an explicit ADR-grade decision.

### 5. Determinism via Minting Policy

IRI generation must be deterministic and verifiable:

| Policy | Rule | Injective | Readable |
|--------|------|-----------|----------|
| `LocalNameFromValue` | `<ns><Carrier>_<Prop>_<ValueLocal>` | Conditional (depends on value uniqueness) | Yes |
| `QualifiedLocalName` | Add scheme-specific prefix token | Yes | Mostly |
| `DigestLocalName` | `<ns><Carrier>_<Prop>_<digest(ValueIRI)>` | Yes (always) | No |

**Default:** `LocalNameFromValue` with explicit declared normalisation (case, separator, character class, truncation).

**Collision handling:** Hard static failure (law `X-S6`), not warning. Escape hatch: `DigestLocalName`.

### 6. Hierarchy Closure is Scoped and Declared

Closure basis and scope are explicit contract fields:

- **Basis:** Declared (e.g., `skos:broader`), not assumed
- **Reflexivity:** Closure includes the value itself (`c ≤ c`)
- **Scope:** Bounded to declared population (not applied universe-wide)

Replaces ad-hoc hierarchy rules with a provenance-bearing mechanism.

---

## Signature Scope and Fidelity (Law X6)

### Signature Scope

Two cases:

1. **LocalSignature:** Target namespace wholly under the contract's control; conservativity guaranteed
2. **SourceSignature:** Target namespace already authored; emitted triples join authored facts

**Law X1 (revised):** Conservativity applies to `LocalSignature` surfaces only.

**Law X6:** A promotion onto a property outside the contract's target namespace declares its fidelity level:
- `ExactSource` — value is restated unmodified
- `DerivedSource` — value is transformed
- `CrosswalkExact` — value maps to authored property via deterministic scheme
- `CrosswalkInexact` — value maps with potential ambiguity

Source-signature promotions are materialized, not definitional, and require governance review.

**Example:** `DimensionSourcing` in MERIDIAN restates FBO authored properties; it declares `SourceSignature` and `ExactSource`, so the emission is materially an assertion, not a derived triple.

---

## Entailment Regimes

Surface contracts declare their entailment requirement:

- **`NoEntailment`:** Read only asserted triples (current default)
- **`RDFS`:** Include RDFS entailments
- **`OWL2EL`:** Include OWL 2 EL entailments
- **`OWL2DL`:** Full OWL 2 DL (limited automation, manual review required)

Compiler refuses to proceed for regimes other than `NoEntailment` in the first slice.

---

## Naming Determinism

Three policy levels:

### LocalNameFromValue
```
SurfaceNamespace + Carrier.localName + Property.localName + Value.localName
  → srf:ScopeCoverageType_Coverage_Cyber
```

Requires:
- Value local names unique across population
- Declared normalisation function (ASCII, case, separator rules)
- Static collision detection

### QualifiedLocalName
```
LocalNameFromValue + PerSchemePrefix
  → srf:ScopeCoverageType_ANSI_Coverage_Cyber
```

Better disambiguation for multi-source populations; slightly less readable.

### DigestLocalName
```
SurfaceNamespace + Carrier.localName + Property.localName + Digest(Value.IRI)
  → srf:ScopeCoverageType_Coverage_a7c9d2e
```

Always injective. Use when `LocalNameFromValue` collision occurs.

**Minting is part of `SurfaceProfile`:** Normalisation function, collision policy, and digest algorithm are versioned together.

---

## Deferred Items

### Explicitly Out of Scope (First Slice)

1. **`srf:RangePartitionPopulation`** — Bucketing law X7 blocked on Quantification partition semantics
2. **Stacking beyond depth 1** — Composition laws drafted (ADR-A21); full support deferred
3. **`srf:ExternalIndex`** — Declared and rejected; no admission criteria yet
4. **Entailment regimes beyond NoEntailment** — Reasoner integration deferred
5. **`DefinitionOnly` parity** — Same dependency as entailment regimes

### Open Decisions

1. **Foundation migration:** Does `fnd:DerivedArtefact` expand to Surface or stay Surface-specific? (§3.1 of current plan)
2. **Profile identity assertion:** Should `srf:profileIdentityHash` be asserted or computed-only? (Blocked on Foundation migration)
3. **MORK toolchain join:** Confirm namespace assumptions and term names before production (§5 of outstanding items)

---

## Example: CSO→FBO Sourcing

**Carrier:** `FBO:ProvisionalPolicy`  
**Read path:** `CSO:CoverageId / CSO:HazardClass`  
**Promotion contract:**
- Promotes to: `FBO:hasLocallySourcedHazardClass`
- Source fidelity: `ExactSource`
- Signature scope: `SourceSignature`

**Outcome:** One assertion per policy instance:
```
fbo:policy_P001 fbo:hasLocallySourcedHazardClass cso:HazardClass_Wind .
```

No new symbol; no index; pure promotion, materialized into the authored property.

---

## Example: Coverage Type Index

**Carrier:** `FBO:PolicyScope`  
**Read path:** `FBO:hasCoverageType`  
**Index contract:**
- Discriminator: `FBO:hasCoverageType`
- Value population: `ContractBoundPopulation(fbo:CoverageTypeSchemeContract)`
- Index forms: `NominalClass`, `ClosureRelation`
- Realisation: `Materialised`
- Naming: `LocalNameFromValue`
- Closure basis: `skos:broader` (only `Auto`, `Commercial` hierarchy)
- Closure scope: Same as value population

**Outcomes:**

1. **Nominal classes:**
```
srf:ScopeCoverageType_Cyber ≡ FBO:PolicyScope ⊓ ∃FBO:hasCoverageType.{cso:Coverage_Cyber}
srf:ScopeCoverageType_Auto ≡ FBO:PolicyScope ⊓ ∃FBO:hasCoverageType.{cso:Coverage_Auto}
…
```

2. **Materialized membership:**
```
fbo:scope_S001 rdf:type srf:ScopeCoverageType_Cyber .
fbo:scope_S002 rdf:type srf:ScopeCoverageType_Auto .
```

3. **Closure relation (Auto family only):**
```
fbo:scope_S002 srf:matchesCoverageTypeAncestor cso:Coverage_Auto .
fbo:scope_S002 srf:matchesCoverageTypeAncestor cso:Coverage_Commercial .
```

Queries against this surface:
- `?s rdf:type srf:ScopeCoverageType_Cyber` → direct lookup
- `?s srf:matchesCoverageTypeAncestor cso:Coverage_Commercial` → ancestry closure, materialized

---

## Relationship to Promotion and Index Subsystems

| Aspect | Promotion | Index | Unified |
|--------|-----------|-------|---------|
| **Read path** | Any length ≥ 1 | Length 1 (to discriminator) | Generalized |
| **Output form** | Direct property | Symbol (class, relation, etc.) | `indexForm` choice |
| **Population** | Implicit (read-path targets) | Explicit (enumerated) | Explicit `ValuePopulation` |
| **Governance** | Source-fidelity dependent | All are `Advisory` or `CachedReproducible` | Authority ceiling enforced |
| **Namespace** | Local (target-defined) or source (existing property) | Local (generated symbols) | `signatureScope` choice |

Both operations are instances of the same abstraction.

---

## Downstream: Surface to MORK

Once a surface contract is authored and validated in this model, the Surface-to-MORK lowering engine (Phases 3+) transforms it into:

- **`mork:DataMapping`** for semantic linkage
- **`mork:ShapeMapping`** for validation artefacts (Promotion shapes, Index constraints)
- **`mork:RuleMapping`** for inference artefacts (Closure rules)
- **`mork:ProjectionMapping`** for class generation (Index nominal forms)
- **`mork:QueryTemplate`** for SPARQL evaluation (Index queries)

The MORK output is deterministic, version-tracked, and governance-reviewable. Compiler backends (SPARQL, SHACL, SWRL) then lower MORK mappings to executable artefacts.

---

## Testing and Validation

Surface validation requires:

1. **Structural shapes** (ontology/surface/shapes/structural.ttl)
   - Contract well-formedness
   - Cardinality and type constraints
   - Profile identity consistency

2. **Constraint shapes** (ontology/surface/shapes/constraints.ttl)
   - Collision detection for nominal names
   - Population enumeration validity
   - Read-path reachability

3. **Defect fixtures** (six edge cases in test suite)
   - Missing evaluation subject role
   - Duplicate singleton role
   - Cyclic closure basis
   - Lossy promotion onto authored property
   - Population over budget
   - Naming collision

4. **Conformance corpus** (ontology/surface/examples/)
   - Three worked examples (CSO→FBO, dimension index, closure surface)
   - Eligibility interval-containment projection

---

## Documentation and References

- **Plan (Phases 0–8 complete):** [surface-mork-unified-projection-plan.md](../plans/surface-mork-unified-projection-plan.md)
- **Status (tracking):** [surface-mork-unified-projection.md](../status/surface-mork-unified-projection.md)
- **Outstanding items:** [surface-outstanding-items.md](../status/surface-outstanding-items.md)
- **ADRs:** A16 (mechanism), A17 (authoring model), A18 (lowering), A19 (compiler), A20 (semantics), A21 (composition), A22–A28 (MORK/governance/conformance)
- **Code:** [tools/surface/](../../tools/surface/) (61/61 tests passing), [ontology/surface/](../../ontology/surface/) (vocab, shapes, examples)

---

## Status

This sketch documents the design principles. Implementation is tracked in the plan and status documents above. See status document for test results and verification checklist.

**Last updated:** 2026-09-22
