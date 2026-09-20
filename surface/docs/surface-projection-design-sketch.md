<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Surface Projection — Design Note

**Generic promotion and shadow-indexing for LATTICE, with a path into MORK**

---

## 0. What this document is for

MERIDIAN FBO has a working, executed instance of a pattern that LATTICE needs generically:

- **promotion** — a data point that lives in an upper/structural ontology (CSO) is landed on a runtime carrier as a local dimension value (`DimensionSourcing`, rules R001–R019);
- **indexing** — a local dimension value is compiled into a local lookup surface so hotspot evaluation never traverses into the external vocabulary graph (`fbo-exec:ScopeCoverageType_*` shadow classes, `fbo-exec:matchesLineOfBusiness` closure assertions).

This note designs the domain-neutral mechanism behind both, sited correctly in the LATTICE stack, and specifies how it later becomes a MORK generative-mapping family. It is a design document: rationale lives here and in the resulting ADR, never in the shipped artefacts.

**Authoring-order constraint.** [ADR-A-C2](../adr/ADR-AC2-clean-room-authoring-procedure.md) applies to everything this design produces on the substrate side. The generic premise (§2) is stated first; two non-domain worked examples (§13) are authored before mechanism prose; the layer README is written from the premise and those examples, **not** paraphrased from MERIDIAN or from this note's §1. MERIDIAN material may be read for sufficiency checking only.

---

## 1. What MERIDIAN actually does (input, stated in mechanism terms)

Distilled from the four execution documents and the three TTL modules, ignoring domain content:

| Step | Mechanism |
|---|---|
| Source binding | A property (`fbo:hasCoverageType`) is governed by a scheme contract (`gov:CoverageTypeSchemeContract`); an implementation-owned `skos:ConceptScheme` satisfies it |
| Enumeration | Every member of the bound scheme is enumerated, wildcards included, no special-casing |
| Nominal projection | For each member `c`, emit `σ(c) ≡ Carrier ⊓ ∃R.{c}`, subclassed under a per-dimension family class, under a global generated-artefact marker class |
| Provenance | Two triples per symbol: `generatedFromConcept`, `generatedForContract` |
| Closure | For hierarchical dimensions, a SHACL-SPARQL rule materialises `matches_R(x, a)` for every `a` in `skos:broader*` of the asserted value |
| Packaging | Split into core / closure / manifest modules with a compatibility shim at the legacy IRI |
| Invalidation | Five change classes (membership, hierarchy, instance assertion, contract binding, generator profile) with a regeneration scope matrix |
| Benchmark | Six queries proving lookup runs off the local surface only |

What it does **not** yet carry, and what the generic mechanism must:

1. no generation-profile identity, no content or artefact hash, no read-set record — so "regeneration is deterministic" is asserted, not checkable;
2. no authority declaration — nothing in the graph says a shadow class is advisory rather than a fact;
3. no naming-injectivity guarantee — `Scope<Dim>_<LocalName>` collides silently if two bound schemes share a concept local name;
4. no statement of conservativity — the property that makes the surface safe to add and safe to delete;
5. promotion (CSO→FBO sourcing) and indexing (FBO→execution shadows) are separate machinery with separate provenance, despite being the same compilation shape;
6. closure rules are generated per carrier with a `UNION` over dimensions, which couples the invalidation scope of otherwise independent dimensions;
7. the closure rule still evaluates `skos:broader*`, at rule-execution time rather than query time — correct, but it means closure validity depends on a rule run having happened, which nothing records.

---

## 2. The generic premise

> A declaration graph states what is true. Answering a question against it may require traversing relations that are expensive, remote, or governed elsewhere. A **surface** is a generated, local, query-facing restatement of part of that graph — additional symbols and assertions that make a specific class of question answerable by direct lookup, and that add nothing to what the source already meant.

Two operations follow from that premise, and only two:

- **Promotion** — a value reachable from a subject by a declared read path is restated as a direct assertion on that subject.
- **Indexing** — a value asserted of subjects is restated as a symbol (a class, a relation) that those subjects can be retrieved by.

Everything MERIDIAN's execution profile does is one of these two. So is a generated direct-property surface over Eligibility dimensions, a materialised recurrence-bin table over Quantification, a flattened peril-tree membership index, or a store-native label projection. The mechanism is the same; the surface form differs.

The premise carries one non-negotiable property: **a surface is conservative over the source signature.** Adding it entails nothing new about source terms; removing it loses no authored fact. This is what makes a surface safe to regenerate, safe to discard, and correctly classified as `advisory` or `cached-reproducible` authority under [ADR-A12](../adr/ADR-A12-identity-and-derivation-model.md) — never as a system of record.

---

## 3. Position in the stack

### 3.1 Three tiers, three homes

| Tier | Content | Home | Why there |
|---|---|---|---|
| Derivation contract | `fnd:DerivedArtefact`, `fnd:GenerationProfile`, hash and authority properties | **Foundation** (extension) | Already required by ADR-A12; Quantification §12 and Behaviour both name it as a blocking gap. Surfaces are its first forcing consumer, not its only one — validation reports, entailment sets and materialised bins need the same contract |
| Surface mechanism | promotion contracts, index contracts, populations, forms, naming, laws | **New substrate layer** (§3.2) | Mechanism-intrinsic, domain-neutral, layer-neutral |
| Compiler | deterministic generation of symbols from contracts | **`tools/`**, then **MORK** | Realisation, not semantics (ADR-A15) |

Foundation changes are deliberate and separately reviewed per ADR-A13's closing note. The derivation-contract extension is not a new decision — A-12 already took it — so it needs an implementation tranche, not a new ADR. The surface mechanism does need one.

### 3.2 The new layer

A surface contract must be able to name *any* property or class in the estate, including Behaviour's, without importing it. Vocabulary already solves exactly this: `voc:constrainsProperty` ranges over `rdf:Property` by punning and names properties defined in layers above it. The surface layer uses the same device and therefore sits **low**, not high:

```
foundation
    └── vocabulary
            └── quantification
                    ├── party
                    │     ├── eligibility
                    │     │     └── instrument
                    │     └── behaviour
                    └── surface        (imports Foundation, Vocabulary, Quantification; imported by nothing in the substrate)
```

Surface imports Quantification so that range-partitioned populations (§6.3) have somewhere to land later without a dependency change. Nothing in the substrate imports Surface: its consumers are the compiler and the generated execution packages.

The substrate ships **zero** surface contracts, exactly as Eligibility ships zero dimension sets and Behaviour ships zero state spaces. Contracts are authored per deployment, in applied-layer or execution directories.

### 3.3 Naming

`projection/` already means *cross-layer contract files* in the per-layer template, and `execution/` already means *generated runtime artefacts*. Neither name is available for the layer without collision. Proposed: **Surface**, prefix `srf:`, namespace `https://www.nebularis.org/neuro-semantic/lattice/surface#`. Alternatives considered and their problems are in the open items (§16.1) — this is a decision for you, and it should be taken before any Turtle is cut, because a rename after authoring costs an import change in every generated package.

---

## 4. The core abstraction: read path + surface form

The single generalisation that makes one mechanism cover both operations:

> A surface contract declares a **read path** from a **carrier** to a **value**, and a **surface form** in which that relationship is restated locally.

| | Read path | Surface form | MERIDIAN instance |
|---|---|---|---|
| Promotion | length ≥ 1, possibly crossing ontologies or match relations | direct property on the carrier | `ctr:hasExtent / ctr:currency` → dimension 12 |
| Nominal indexing | length 1 (the promoted dimension) | one named class per value | `ScopeCoverageType_CyberCoverage` |
| Closure indexing | length 1 + declared hierarchy basis | one relation, ancestor-closed | `matchesLineOfBusiness` |

MERIDIAN's shadow class is the special case: path length 1, nominal form, `skos:broader` basis for the two hierarchical dimensions. Generalising to arbitrary path length is what makes the mechanism able to shadow **upper-ontology shapes** and not just vocabulary members — and it is what the CSO sourcing table (V2 §11.2) is already doing by hand for nineteen rows.

Path expressions use SHACL property-path syntax (`sh:path`), because shapes already use it, MORK's `ParameterBinding` already has `paramType` `Path`, and it gives sequence and inverse for free. First slice restricts to sequence paths of object/datatype properties and `sh:inversePath`; alternation and zero-or-more are deferred (a `*` in a read path makes the promoted value set unbounded, which breaks the enumerability precondition of the nominal form).

---

## 5. Model — declaration tier

DL-style, following the notation of `docs/architecture/ontology-architecture.md` §0.

```
srf:SurfaceContract        ⊑ fnd:Version ⊓ fnd:Governable
                             ⊓ =1 carrier.rdfs:Class          (punned)
                             ⊓ =1 readPath                     (SHACL path node)
                             ⊓ =1 surfaceProfile.SurfaceProfile
                             ⊓ ≤1 populationBudget.xsd:nonNegativeInteger

srf:PromotionContract      ⊑ srf:SurfaceContract
                             ⊓ =1 promotesTo.rdf:Property      (punned; the local dimension property)
                             ⊓ =1 sourceFidelity.SourceFidelity
                             ⊓ ≤1 viaMatchRelation.rdf:Property

srf:IndexContract          ⊑ srf:SurfaceContract
                             ⊓ =1 discriminator.rdf:Property   (punned)
                             ⊓ =1 valuePopulation.ValuePopulation
                             ⊓ ≥1 indexForm.IndexForm
                             ⊓ =1 realisationMode.RealisationMode
                             ⊓ =1 namingPolicy.NamingPolicy
                             ⊓ ≤1 closureBasis.rdf:Property    (punned; required iff ClosureRelation form)
                             ⊓ ≤1 closureScope.ValuePopulation

srf:ValuePopulation        (abstract)
  srf:ContractBoundPopulation ⊑ ValuePopulation ⊓ =1 fromSchemeContract.voc:SchemeContract
  srf:ClassExtentPopulation   ⊑ ValuePopulation ⊓ =1 fromClass.rdfs:Class ⊓ =1 extentKind.ExtentKind
  srf:EnumeratedPopulation    ⊑ ValuePopulation ⊓ ≥1 hasMember
  srf:RangePartitionPopulation ⊑ ValuePopulation ⊓ =1 fromRangeSet.qnt:RangeSet     [declared, not permitted — §16.7]

srf:SurfaceProfile         ⊑ fnd:GenerationProfile
                             ⊓ =1 generatorVersion.xsd:string
                             ⊓ =1 entailmentRegime
                             ⊓ =1 canonicalisationVersion.xsd:string
```

**`srf:ContractBoundPopulation` is the load-bearing one.** A contract names a `voc:SchemeContract`, never a scheme and never a concept. The population is *whatever scheme is currently bound to that contract, in the governance state that contract requires*. This is how the substrate mechanism stays domain-neutral while the surface tracks live vocabulary: rebinding `voc:boundScheme` is a Rule-D invalidation, automatically, because it changes the read set.

### 5.1 Mechanism vocabulary

```
srf:IndexForm        : NominalClass | MembershipAssertion | ClosureRelation | DirectProperty | ExternalIndex
srf:RealisationMode  : DefinitionOnly | Materialised | DefinitionAndMaterialised
srf:NamingPolicy     : LocalNameFromValue | QualifiedLocalName | DigestLocalName
srf:SourceFidelity   : ExactSource | DerivedSource | CrosswalkExact | CrosswalkInexact
srf:ExtentKind       : NamedIndividuals | DirectSubClasses | TransitiveSubClasses
srf:MatchStrength    : (reuse SKOS mapping relations directly rather than minting a parallel set)
```

`srf:ExternalIndex` is declared and rejected by shapes in the first slice, following the `bhv:Proportional` precedent: visibly unavailable rather than silently absent.

### 5.2 Index forms, and when each applies

| Form | Emits | Requires enumerable population | Query shape | Reasoner needed |
|---|---|---|---|---|
| `NominalClass` | `σ(c) ≡ Carrier ⊓ ∃R.{c}` | yes | `?x a σ(c)` | yes, unless paired with `MembershipAssertion` |
| `MembershipAssertion` | `x rdf:type σ(c)` | yes | `?x a σ(c)` | no |
| `ClosureRelation` | `x match_R a` for all `a ⊒ c` | no (population bounds the closure, not the emission) | `?x match_R ?a` | no |
| `DirectProperty` | `x p_local v` for the read path's value | **no** | `?x p_local ?v` | no |
| `ExternalIndex` | store-native (deferred) | n/a | n/a | n/a |

`DirectProperty` is the form MERIDIAN does not yet have and the one that matters most for generalisation: it needs no enumeration, so it works for unbounded value spaces (monetary limits, dates, identifiers) and for long read paths. It is the "generated per-dimension property surface" that ADR-A15 and the hash section of the solution architecture both already anticipate. Promotion produces exactly this form, which is why promotion and indexing unify.

`NominalClass` in the `∃R.{c}` shape stays inside OWL 2 EL (`ObjectHasValue` is EL++), so classification remains tractable at scale. That is a deliberate constraint on the emitted pattern, not an accident of MERIDIAN's choice, and it should be stated in the layer's design decisions.

---

## 6. Model — derived tier

```
fnd:DerivedArtefact       ⊑ fnd:Evidenced
                            ⊓ ≥1 derivedFrom
                            ⊓ =1 generationProfile.GenerationProfile
                            ⊓ =1 derivationAuthority.DerivationAuthority
                            ⊓ ≤1 semanticContentHash.xsd:string
                            ⊓ ≤1 artefactHash.xsd:string
                            ⊓ =1 producedAt.xsd:dateTime

fnd:DerivationAuthority   : Advisory | CachedReproducible | OperationallyAuthoritative
                          | ExternallyAuthoritativeSynchronised          (vocab/foundation-vocab.ttl)

srf:GeneratedSurface      ⊑ fnd:DerivedArtefact
                            ⊓ =1 coversContract.SurfaceContract
                            ⊓ ≥1 readSetEntry.ReadSetEntry
                            ⊓ ≥1 symbolCount                      (per form, reified)

srf:GeneratedSymbol       ⊑ fnd:DerivedArtefact
                            ⊓ =1 inSurface.GeneratedSurface
                            ⊓ =1 symbolForm.IndexForm
                            ⊓ ≤1 fromValue                        (absent for DirectProperty form)
                            ⊓ =1 denotes                          (wrapper — §6.1)

srf:ReadSetEntry          ⊓ =1 readSource ⊓ =1 readVersion.xsd:string ⊓ =1 readHash.xsd:string
```

Two invariants worth stating as design decisions:

- **Authority ceiling.** A `GeneratedSurface` may declare `Advisory` or `CachedReproducible` and nothing higher. `OperationallyAuthoritative` on a surface would mean the index outranks the declaration it was built from, which is precisely what ADR-A12 forbids. Enforce in shapes.
- **No stacking.** A surface's read set may not contain another surface in the first slice. Derived-from-derived chains multiply invalidation scope and make hash provenance a graph rather than a tree. Declared-and-rejected, reopened only with a stated composition law.

### 6.1 Punning vs wrapper

`fbo-exec:generatedFromConcept` is asserted on a generated `owl:Class` with `rdfs:domain owl:Class` — metamodelling that OWL 2 DL tolerates only under punning, and that OWL-API-based toolchains object to. MORK already ran into this and solved it: `mrk:OwlAxiom` / `mrk:OwlClass` wrapper individuals linked by `owl:sameAs`, with `rdfs:seeAlso` for environments that don't honour `sameAs`.

**Recommendation:** provenance attaches to a `srf:GeneratedSymbol` *individual* which `srf:denotes` the generated class; the generated class itself carries only `rdfs:isDefinedBy` back to the surface. The class stays clean OWL; the provenance graph stays clean A-box; both are queryable. This also lets provenance live in the manifest module while definitions live in core — which the split package wants anyway.

---

## 7. Naming and determinism

Determinism of the emitted symbol set is the whole basis of the repeatability claim, and IRI minting is where it breaks first.

| Policy | Minting rule | Injective? | Readable? |
|---|---|---|---|
| `LocalNameFromValue` | `<surfaceNS><CarrierLocal>_<PropertyLocal>_<ValueLocal>` after declared normalisation | only if value local names are unique across the population | yes |
| `QualifiedLocalName` | as above, plus a declared per-scheme prefix token | yes if scheme tokens are unique | mostly |
| `DigestLocalName` | `<surfaceNS><CarrierLocal>_<PropertyLocal>_<digest(valueIRI)>` | yes, unconditionally | no |

MERIDIAN uses `LocalNameFromValue` with an implicit carrier/dimension prefix. It is injective in its current graph and stops being injective the moment two schemes bind the same dimension, or two schemes in different namespaces share a concept local name. That is not hypothetical for a jurisdiction or peril tree assembled from several sources.

**Recommendation:** default `LocalNameFromValue`; declare the normalisation function explicitly (case, separator, permitted character class, truncation) as part of the `SurfaceProfile`, not as compiler convention; make collision a hard static failure (law `X-S6`), not a warning; provide `DigestLocalName` as the escape hatch for populations that fail the check. Normalisation changes are a profile change — full regeneration, version bump.

---

## 8. Hierarchy closure

Generalising MERIDIAN's two closure rules:

- The basis is **declared, not assumed** (`srf:closureBasis`). `skos:broader` is the common case, not the only one — an upper ontology may close over `rdfs:subClassOf`, an org structure over a reporting relation.
- The closure is **reflexive**: `c ≤ c`. MERIDIAN gets this from `skos:broader*` and depends on it — Query C's expected result includes the directly-asserted ancestor case.
- The closure is **scoped** to the declared population (`srf:closureScope`, defaulting to the contract's population). Eligibility's current `elg:HierarchicalClosureRule` targets *every* `skos:Concept` in the union graph with no scope at all; a scoped, provenance-bearing surface should replace that use (§15.2).
- Closure symbols are generated **per contract**, not per carrier with a `UNION`. MERIDIAN's `ScopeQualifierHierarchyClosureRule` fuses LineOfBusiness and AssetClass into one rule, so a hierarchy change in either invalidates both. One rule per (carrier × contract) restores invalidation minimality at negligible cost.
- **Well-foundedness is a static gate.** A cycle in the basis makes `≤` non-antisymmetric and the closure non-terminating in the naive rule. Acyclicity is graph-structural and therefore SHACL-SPARQL, not OWL — the same rationale MORK gives for `mrk:precedes` acyclicity. Eligibility law L9 already requires well-foundedness for `HierarchicalMatch`; the surface mechanism should *check* it rather than restate it.
- **Materialisation must record that it ran.** A closure surface in `Materialised` mode is only valid if the rule was executed over the current read set. The `GeneratedSurface` records the run; a surface with no recorded run is not L7-conformant.

---

## 9. Laws

Three registers, reusing Quantification's `qnt:Law` / `qnt:LawDischarge` split rather than inventing a parallel scheme — a semantic law, a static constraint and a runtime claim need different evidence, and that distinction is already modelled.

### Semantic laws — formal argument plus property tests

| ID | Law |
|---|---|
| **X1** | **Conservativity.** For any source graph `G` and surface `S` generated from it, `G ∪ S ⊨ φ` iff `G ⊨ φ`, for every `φ` over the source signature. Surfaces extend the signature; they never extend the source-signature consequence set. |
| **X2** | **Index faithfulness.** `x ∈ σ_R(c)` iff `x` is a carrier and `R(x,c)` holds under the profile's declared entailment regime. Both directions; the regime is named, not assumed. |
| **X3** | **Closure soundness and completeness.** `match_R(x,a)` iff `∃c. R(x,c) ∧ c ≤_H a`, where `≤_H` is the reflexive-transitive closure of the declared basis restricted to the declared scope. |
| **X4** | **Wildcard non-collapse.** A wildcard or "any" member projects to its own surrogate on the same terms as every other member. Admit-everything semantics is an Eligibility concern (`elg:wildcardSemantics`) and must not be baked into the index, which would make the surface non-conservative. |
| **X5** | **Promotion fidelity.** A promotion with `ExactSource` or `CrosswalkExact` fidelity preserves meaning. A promotion with `DerivedSource` or `CrosswalkInexact` does not, must declare the relation it traversed, and yields a surface capped at `Advisory` authority. |

X5 is the one MERIDIAN's sourcing table needs and does not have: dimension 10 is sourced "via crosswalk" across `skos:closeMatch`, which is lossy by definition. Promoting across a close match and then indexing the result produces a lookup surface that answers a slightly different question from the one asked. Declaring it keeps that visible.

### Static declaration constraints — SPARQL / SHACL

| ID | Constraint |
|---|---|
| **X-S1** | Every contract declares carrier, read path, profile, and its form-specific required properties |
| **X-S2** | For `ContractBoundPopulation`: the named `voc:SchemeContract` has a `voc:boundScheme` in the required governance state |
| **X-S3** | `closureBasis` present iff any declared form is `ClosureRelation`; basis is acyclic over the declared scope |
| **X-S4** | Enumerable population declared for `NominalClass` / `MembershipAssertion`; population size within `populationBudget` |
| **X-S5** | Coverage: every population member has exactly one symbol per declared form |
| **X-S6** | Naming injectivity: no two members mint the same symbol IRI |
| **X-S7** | Every generated symbol has a `GeneratedSymbol` record naming value, contract and profile; no orphan symbols |
| **X-S8** | Generated content occupies only the projection/execution graph roles (ADR-A13); no generated symbol appears in `spec/`, `vocab/`, `shapes/` or `projection/` |
| **X-S9** | Authority ceiling: no surface declares authority above `CachedReproducible` |
| **X-S10** | No read-set entry names another `GeneratedSurface` (no stacking, first slice) |

### Runtime conformance — executed runs only

| ID | Claim |
|---|---|
| **X-R1** | **Regeneration determinism.** Same read set + same profile → identical symbol inventory and identical artefact hash |
| **X-R2** | **Surface/source parity.** Every question in the shared conformance corpus returns the same answer against the surface as against the source under a direct-SPARQL profile. This *is* the L7 check |
| **X-R3** | **Invalidation minimality.** A scoped change regenerates only the computed impact set and leaves other surfaces byte-identical |
| **X-R4** | **Materialisation idempotence.** Re-running a materialisation rule over an unchanged read set adds no triples |

X-R2 deserves emphasis: it is the only thing that makes a surface trustworthy, and it is cheap, because both sides of the comparison are already required to exist under ADR-A15. If the surface and the source disagree, the surface is wrong by construction — the source is authoritative.

---

## 10. Invalidation

MERIDIAN's five change-class rules are correct and should be kept, but they are the *wrong primitive* to build on: five hand-written rules do not compose, and a sixth change class needs a sixth rule.

**Model invalidation as a read set.** Each `GeneratedSurface` records, per entry, what it read and the version/hash it read. A surface is stale iff any read-set entry's current hash differs from the recorded one. That is one rule, total, and it is decidable without classifying the change.

The five change classes survive as the **impact-scoping taxonomy** — how much to recompute once staleness is known:

| Change class | Read-set entry that moves | Recompute |
|---|---|---|
| Population membership | bound scheme content hash | symbol inventory for that contract; closure for hierarchical forms |
| Hierarchy | closure basis subgraph hash | closure symbols and dependent match assertions only |
| Carrier instance assertion | instance graph hash | materialised memberships/matches for the changed nodes only; nothing in `DefinitionOnly` mode |
| Contract binding | `voc:boundScheme` / governance state | whole contract |
| Profile | profile identity | whole estate on that profile, version bump |
| Canonicalisation contract | canonicalisation version | full estate rehash (ADR-A12's known, accepted cutover cost) |

Note the third row: separating definitions from materialised assertions into different modules (§11) is what lets an instance-level change avoid touching the T-box module at all. MERIDIAN's split is core/closure/manifest; the generic layout adds an assertions module for this reason.

The existing operational-guidance document (`docs/operational-guidance.md` §4) already states dependency-scoped invalidation for Eligibility and Behaviour. Surfaces slot into the same posture and give it a machine-readable read set instead of prose examples.

---

## 11. Package layout

Per deployment or applied layer, under the existing `execution/` convention:

```
<layer-or-applied>/execution/
  <profile-id>/
    core.ttl          # T-box: family classes, nominal classes, generated properties
    closure.ttl       # closure rules and/or materialised closure assertions
    assertions.ttl    # A-box: materialised memberships and match assertions   [Materialised modes only]
    manifest.ttl      # GeneratedSurface, GeneratedSymbol records, read set, hashes, authority
```

Module boundaries follow invalidation classes, not file size. The manifest is the entry point (imports the others), matching MERIDIAN's executed decision. A compatibility shim at a legacy IRI is a deployment choice, not a substrate concern, and should not be modelled.

One deviation from MERIDIAN worth taking: MERIDIAN's manifest carries `dct:` packaging metadata only. The generic manifest carries the provenance A-box — it is the artefact the governance checks read.

---

## 12. Governance and conformance

### 12.1 Where the checks live

`governance/` runs over the union graph, which is the only place that can see a source declaration and its generated surface at once. Surface parity checks therefore belong in `governance/parity/`, not in `surface/shapes/`:

1. **Coverage parity** — every value used by any carrier instance on an indexed dimension has a surrogate (else lookup silently under-returns);
2. **Provenance parity** — every generated symbol traces to value + contract + profile;
3. **Freshness parity** — no surface's read set is stale;
4. **Containment parity** — no generated symbol outside its declared graph role;
5. **Authority parity** — no surface claims authority above its ceiling.

Checks 1, 2 and 4 are MERIDIAN's governance hooks, generalised. Checks 3 and 5 are new and are what make the estate auditable rather than merely well-formed.

### 12.2 Conformance level

The ladder already has the right rung. **L7 — projection-conformant** is defined for surfaces as: X-S1..X-S10 pass, the read set is fresh, and X-R2 parity holds over the shared corpus for the questions the surface claims to answer.

Two consequences to state explicitly in the ADR:

- An L7 surface does **not** raise the conformance level of the graph it indexes. A surface over an L4 declaration graph does not make it L5. Surfaces accelerate; they do not admit.
- A surface must never be the evidence for an L5 or L6 decision. Eligibility decisions and Behaviour executions cite declarations; if an implementation evaluated them via a surface, that is a realisation-profile fact recorded on the decision (`elg:usesOperationalProfile`, `bhv:usesProfile`), not a change of what the decision rests on.

---

## 13. Non-domain worked examples (authored first, per ADR-A-C2)

Two are required before mechanism prose, from unrelated fields. Both fit existing empty placeholders in `examples/`:

**A. `examples/employment.ttl` — hierarchical closure + nominal index.**
A job-family scheme with a `skos:broader` tree (individual contributor → engineering → technical). An eligibility condition carries `hasJobFamily`. The surface generates one nominal class per family member plus a `matchesJobFamily` closure relation, and the benchmark proves that a condition asserting a leaf family is retrievable by an ancestor family without query-time traversal. This exercises: `ContractBoundPopulation`, `NominalClass`, `ClosureRelation`, reflexivity, wildcard uniformity.

**B. `examples/saas-subscription.ttl` — promotion over a multi-hop path + direct property.**
A subscription's currency is reachable only as `hasPlan / hasPricing / inCurrency`. A promotion contract restates it as a direct `subscriptionCurrency` on the subscription. This exercises: `PromotionContract`, sequence read path, `DirectProperty` form, `ExactSource` fidelity, and — crucially — a population that is *not* enumerated, proving the mechanism is not shadow-class-shaped.

A third, optional, is worth having before the insure-o port: **C. `examples/clinical-trial.ttl`** exercising `CrosswalkInexact` promotion across a `skos:closeMatch` between two site-classification schemes, to make X5's advisory-capping visible in a fixture rather than only in prose.

Deliberate-defect fixtures to pair with these (following the Gate 4 reference-realisation pattern):

- two population members minting the same symbol IRI (X-S6 fails);
- a cyclic closure basis (X-S3 fails);
- a generated symbol with no provenance record (X-S7 fails);
- a surface whose bound scheme has since changed (freshness parity fails);
- a surface declaring `OperationallyAuthoritative` (X-S9 fails).

---

## 14. Incorporation into MORK

MORK already has the exact shape. `mrk:GenerativeMapping` has three siblings, each defined by an equivalence on what it generates:

```
ShapeMapping      ≡ DataMapping ⊓ ∃generatesShapeDefinition.sh:Shape
RuleMapping       ≡ DataMapping ⊓ ∃generatesRuleDefinition.swrl:Imp
TransformMapping  ≡ DataMapping ⊓ ∃generatesTransformDefinition.rr:TriplesMap
```

A fourth follows the same pattern exactly:

```
ProjectionMapping ≡ DataMapping ⊓ ∃generatesClassDefinition.mrk:OwlClass
                  ⊑ GenerativeMapping
                  ⊑ ∃hasTargetingSpec.TargetingSpec          (sh:targetClass = the carrier)
                  ⊑ ≥1 hasParameterBinding                    (value, discriminator, closure basis)
                  ⊑ ∃hasProjectionProvenance.ProjectionProvenance
```

What this buys, without new machinery:

| MORK construct | Reuse for surfaces |
|---|---|
| `TargetingSpec` (`sh:targetClass` / `targetObjectsOf` / `targetSubjectsOf` / `targetNode`) | carrier binding — already the right four modes |
| `ParameterBinding` with `paramType ∈ {Concept, Path, String}` | value, read path, basis, normalisation token |
| `templateMapping` + `compositeNarrowerTemplate` + `templateBinding` | one projection template, N lightweight per-value instantiations — the 180-instantiations argument in MORK's own README, applied to a 2,000-member jurisdiction scheme |
| `precedes` derivation (T-Box → A-Box → R-Box) | class definitions before membership assertions before closure relations, ordered automatically |
| `ConstraintProvenance` / `RuleProvenance` pattern | `ProjectionProvenance` — same fields, plus read set |
| `mork2rml.py` compiler skeleton | same catamorphism, different algebra map; `_compile_tbox_creation` is already 80% of `NominalClass` emission |

Three points to hold:

1. **The compilation boundary is unchanged.** An LLM may *propose* that a dimension is runtime-critical — i.e. propose a `SurfaceContract`. It never generates symbols. Symbol generation sits entirely downstream of the validation gate and is 100% deterministic, which is the strongest case in MORK's non-LLM degradation table.
2. **LATTICE owns the contract; MORK owns the compilation.** A `srf:IndexContract` is a semantic declaration in LATTICE's substrate and must stay usable without MORK (ADR-A15: compilation is never a semantic prerequisite). MORK's `ProjectionMapping` is one compiler for it. Direct SPARQL generation from the contract is another, and should be the reference realisation.
3. **Egress symmetry.** `mrk:egressProjection` already names the reverse direction. A surface is an ingress-side flattening; the same contract shape describes the egress-side projection of an ontology chain into a flat external representation. Worth checking that the read-path model serves both before freezing it, because if it does, one mechanism covers both directions and `TransformMapping` gains a sibling rather than a competitor.

---

## 15. Findings in the current repository state

Things I hit while designing that affect this work and need decisions independently of it.

### 15.1 `elg:boundScheme` does not exist

`examples/insure-o/projection/hierarchy-example.ttl` and `examples/insure-o/execution/shadow-profile.ttl` both assert `elg:boundScheme` on an `elg:Condition`. Eligibility's spec declares no such property; `voc:boundScheme` exists, with domain `voc:SchemeContract`. As written, those two triples bind nothing, and the hierarchical-match fixtures they support are not actually wired to a scheme. This matters here because `ContractBoundPopulation` depends on that binding being real.

Options: (a) add `elg:boundScheme` to Eligibility with a projection to Vocabulary; (b) rewrite the fixtures to go through a `voc:SchemeContract`; (c) add `elg:constrainedByContract : Condition → voc:SchemeContract`. (c) is the most consistent with how Vocabulary is meant to be used, and is what the surface mechanism wants.

### 15.2 Eligibility's closure rule is unscoped

`elg:HierarchicalClosureRule` constructs `skos:broaderTransitive` for every `skos:Concept` with a `skos:broader+` path anywhere in the union graph. It has no scope, no provenance, no authority declaration, and it will fire over unrelated schemes. It is currently the only discharge of law L9. Proposal: keep it as Eligibility's *semantic* statement of what closure means, and have the surface mechanism own the scoped, recorded materialisation. That needs an amendment note on L9, not a new law.

### 15.3 `ino:hasPerilType` vs `ins:hasPerilType`

`examples/insure-o/projection/bindings.ttl` declares scheme contracts constraining `ins:hasPerilType`, `ins:hasTerritory`, `ins:hasLineOfBusiness`, `ins:hasAssetClass`, `ins:hasCurrency` — none of which exist in `instrument/spec/instrument.ttl`. `examples/insure-o/spec/insure-o.ttl` defines them in the `ino:` namespace, and `test/defect-missing-scheme.ttl` uses `ino:`. So five of the five scheme contracts in the applied package currently constrain non-existent properties. Since a surface contract's population comes from a scheme contract, and the scheme contract names a property, this has to be resolved before insure-o gets surfaces. The `ino:` forms are correct — Instrument is domain-neutral and should not carry peril or currency properties.

### 15.4 Foundation's `GovernanceState` individuals are still undeclared

`X-S2` requires a bound scheme to be in a required governance state. `voc:requiresGovernanceState` ranges over `fnd:GovernanceState`; `fnd:Draft`/`Reviewed`/`Active`/`Superseded` are declared nowhere, and `examples/insure-o/projection/bindings.ttl` forward-references `fnd:Active` by full IRI. The Foundation extension tranche should close this at the same time, since it is touching `vocab/foundation-vocab.ttl` anyway.

### 15.5 `bhv:targetsAllowance` drift

`behaviour/spec/behaviour.ttl` declares `bhv:targetsAllowance`; `behaviour/README.md` §5 does not, though `behaviour/shapes/constraints.ttl` checks it and the validation plan claims it was added in Gate 3. The README is authoritative per `docs/GOVERNANCE.md`, so spec and README have drifted in the direction the drift discipline says cannot happen. Unrelated to surfaces, but it is a live README⇄spec parity failure worth logging.

---

## 16. Open items and decisions needed

I have not baked any of these into the design above beyond the stated recommendation; each needs your call before authoring.

1. **Layer name and prefix.** Recommended: `Surface` / `srf:`. Alternatives: `Projection` / `prj:` (collides with the per-layer `projection/` contract directories), `Derivation` / `drv:` (too broad — swallows validation reports and entailment sets that belong to Foundation's generic contract), `Index` / `idx:` (too narrow — excludes promotion). Decide before any Turtle.
2. **CSO expansion and promotion source.** I have read CSO as the structural stratum (Contract Structure Ontology) sitting below FBO, and "promotes data points" as the `DimensionSourcing` R001–R019 pattern: read a value from the structural ontology by a declared path and land it on the behavioural carrier. Confirm, and confirm whether promotion sources are T-box (class/shape promotion), A-box (value promotion), or both — §4 assumes both, which costs an extra `ExtentKind` axis.
3. **New layer vs. Foundation-only.** I propose a new substrate layer plus a minimal Foundation extension. The alternative is putting everything in Foundation, which avoids an eighth layer but pushes projection-specific mechanism into the layer every other layer imports. I do not recommend it, but the layer count is your call.
4. **Does Surface import Quantification?** Only needed for `RangePartitionPopulation`, which is deferred. Importing it now costs nothing and avoids a later dependency change; not importing keeps Surface at the Vocabulary tier. Recommend importing.
5. **Punning vs wrapper for symbol provenance (§6.1).** Recommend wrapper, consistent with MORK. Costs one extra individual per symbol; a 2,000-member scheme doubles its manifest size.
6. **Authority ceiling.** I have proposed hard-capping surfaces at `CachedReproducible`. If any deployment needs an operationally authoritative projection (an external store that also accepts writes), that is ADR-A12's `ExternallyAuthoritativeSynchronised` case and it is *not* a surface — it needs its own treatment. Confirm the cap.
7. **`RangePartitionPopulation`.** Declared-and-rejected in the first slice, following `bhv:Proportional`. Reopening needs a bucketing law (how a `qnt:RangeSet` partitions into a finite symbol set, and what happens at bucket boundaries under each `qnt:Closure`). Confirm it stays deferred.
8. **Stacking (§6, "no stacking").** Confirm surfaces may not read other surfaces in v1. This forbids, for example, an index built over a promoted property — which is exactly the MERIDIAN CSO→FBO→shadow chain. If that chain must work as two artefacts rather than one contract, stacking has to be permitted with a composition law, and the read-set model becomes a DAG with hash chaining. **This is the most consequential open item here** and I have deliberately not resolved it: the two-stage chain is the real use case, but permitting it in v1 doubles the invalidation model's complexity. My suggestion is to permit it with a depth bound of 1 and a stated composition law for X1 and X-R1, rather than forbid it outright.
9. **Closure materialisation vs. rule shipping.** MERIDIAN ships SHACL rules that compute closure at rule-execution time. An alternative ships the closure assertions themselves. The first is smaller and self-describing; the second is inert and needs no SHACL engine. Recommend supporting both via `RealisationMode` and defaulting to shipping assertions, since X-R4 and freshness checking are easier against inert data.
10. **Population budget.** A default ceiling on nominal-class populations (MERIDIAN's largest family is 10; a real jurisdiction or peril tree is three orders of magnitude larger). Proposal: warn at 500, fail at 5,000 unless the contract declares an explicit override with a rationale recorded in the profile. Numbers are a guess and need your judgement.
11. **Where do surface contracts live?** Substrate ships none. For insure-o they would go in `examples/insure-o/execution/`. For a real deployment, in the applied layer's own `execution/`. Confirm, and confirm that a "substrate inventory emptiness" check for Surface joins the Gate 1 check list.
12. **Gate numbering.** This reads as Gate 7 (Gate 6 closed out documentation scope). Confirm, and confirm whether the Foundation derived-artefact extension is Gate 7 or a separate Gate 4b tranche given that Quantification and Behaviour already need it.
13. **Findings §15.1–15.5.** Five defects, four of which block or distort the insure-o surface work. Decide which are fixed in this tranche and which are logged.

---

## 17. Proposed work breakdown for the code cut

Ordered so that nothing is authored before what it depends on, and so that ADR-A-C2's direction of authorship holds.

| # | Tranche | Output | Depends on |
|---|---|---|---|
| 1 | Decisions | §16.1–§16.12 resolved | you |
| 2 | ADR | `ADR-A16-surface-projection-mechanism.md` — premise, tiers, conservativity, authority ceiling, stacking decision, realisation neutrality restated | 1 |
| 3 | Foundation extension | `fnd:DerivedArtefact`, `fnd:GenerationProfile`, authority + hash properties, and the four `GovernanceState` individuals (§15.4); README first, then `spec/`, then `vocab/` | 2 |
| 4 | Non-domain examples | `examples/employment.ttl`, `examples/saas-subscription.ttl` (+ optional clinical-trial), authored **before** the layer README | 2, 3 |
| 5 | Surface layer | `surface/README.md` literate spec → `spec/surface.ttl`, `vocab/surface-vocab.ttl`, `shapes/{structural,constraints}.ttl`, `projection/vocabulary.ttl` + `projection/quantification.ttl` | 3, 4 |
| 6 | Laws and fixtures | X1–X5, X-S1–X-S10, X-R1–X-R4 in the vocab; deliberate-defect fixtures per §13 in `surface/test/` | 5 |
| 7 | Governance parity | `governance/parity/surface-parity.ttl` — the five checks of §12.1 | 5, 6 |
| 8 | Reference generator | `tools/` deterministic compiler: contract → core/closure/assertions/manifest; SPARQL reference realisation first, no MORK dependency | 5, 6 |
| 9 | Conformance corpus | X-R2 parity harness extending the Gate 5 corpus; X-R1 determinism run | 8 |
| 10 | Applied port | insure-o surfaces over peril (hierarchical) and territory (exact), after §15.1/§15.3 are fixed | 8, 9 |
| 11 | MORK integration | `mrk:ProjectionMapping` + `generatesClassDefinition` + `ProjectionProvenance`; compiler refactored onto the `mork2rml` catamorphism | 8, 10 |

Tranches 3–7 are substrate and must hold the domain-neutrality line: no artefact in them names a peril, a jurisdiction, a currency, or an insurance construct, and no `fnd:utility` or `rdfs:comment` string in them explains *why* a term is shaped as it is. That reasoning stays in the ADR and in this note.
