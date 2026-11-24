<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Surface Ontology — Promotion, Indexing, and Generated Lookup Surfaces

Literate specification for the Surface layer.

The workflow control boundary for immutable contract revisions and graph-reference jobs is documented in [the revision lifecycle guide](../../docs/operator/surface-revision-lifecycle.md). It wraps the existing compiler and does not alter this normative specification.

---

## 1. Purpose and Scope

A declaration graph states what is true. Answering a question against it may require traversing relations that are expensive, remote, or governed elsewhere. Surface declares how part of that graph may be restated locally — as additional symbols and assertions that make a specific class of question answerable by direct lookup, and that add nothing to what the source already meant.

Three operations are declared:

- **Promotion** — a value reachable from a subject by a declared read path is restated as a direct assertion on that subject.
- **Indexing** — a value asserted of subjects is restated as a symbol those subjects can be retrieved by.
- **Projection** (ADR-A17) — mapping intent that needs graph construction, derivation, a join, or an expansion is lowered into a MORK mapping graph rather than restated directly.

Promotion and indexing emit their generated artefact directly. Projection does not: its intent is broader than a single read path can express, so a `ProjectionContract` lowers into MORK (ADR-A18), which a staged compiler (ADR-A19) then compiles to SPARQL, SHACL, SWRL, RML, or a native execution plan.

This subsystem turns declared facts into query-friendly local surfaces without altering their meaning. A `Surface` is a generated, graph-local, query-facing restatement of a sub-graph originating in a domain or substrate ontology. The sub-graph usually refers to the target domain or substrate ontology's A-Box, though this is not a constraint.

### Using Surface (A practical Guide)

A carrier is a class or entity type that a surface contract refers to. It is the “host” object whose values are being made easier to query by classification or restating in a generated local surface. This is usually a runtime record-like concept such as:

- a subscription
- a role assignment
- an enrolment
- an eligibility condition
- a policy component

For example, a _Surface Contract_ may say: “For instances of `Subscription`, restate the value reached by hasPlan -> hasPricing -> inCurrency as a direct property.” Here, `Subscription` is the carrier. The chain of relations used to reach a value from the carrier (`hasPlan -> hasPricing -> inCurrency`) may be written as a simple property or a sequence of `PathStep` entries, is referred to in this subsystem as a _read path_, and can take the form of:

- single-hop property lookup
- multi-hop traversal
- path through a mapping/crosswalk relation 

The _Surface Contract_ is a declarative specification that says:

- what carrier the surface applies to
- what path it reads through
- what form the surface takes
- what namespace it emits under
- which generation profile applies

There are three main kinds of _Surface Contract_:
- `PromotionContract`
- `IndexContract`
- `ProjectionContract`

#### Promotion, in practice

We will consider a SaaS billing domain ontology. A `Subscription` has a plan, which has pricing, which in turn has a currency code assocaited with it. A consumer for "what currency is this subscription billed in" which does not want to know about `Plan` or `Pricing` (i.e., they want one property hanging off `Subscription`), will make use of `PromotionContract`:

```turtle-example
@prefix srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#> .
@prefix ex:  <https://example.org/lattice/surface/> .
@prefix saas: <https://example.org/saas/> .

ex:subscription-currency a srf:PromotionContract ;
	srf:contractKey "subscription-currency" ;
	srf:carrier saas:Subscription ;
	srf:hasPathStep ex:step-0, ex:step-1, ex:step-2 ;
	srf:promotesTo saas:subscriptionCurrency ;
	srf:sourceFidelity srf:ExactSource ;
	srf:realisationMode srf:Materialised ;
	srf:targetNamespace <https://example.org/saas/generated/> ;
	srf:surfaceProfile ex:default-profile .

ex:step-0 srf:stepIndex 0 ; srf:stepProperty saas:hasPlan     ; srf:stepDirection srf:Forward .
ex:step-1 srf:stepIndex 1 ; srf:stepProperty saas:hasPricing  ; srf:stepDirection srf:Forward .
ex:step-2 srf:stepIndex 2 ; srf:stepProperty saas:inCurrency  ; srf:stepDirection srf:Forward .
```

A few things of note:

- **Three `PathStep` individuals instead of one property** Because the value is three hops away and `srf:readProperty` only covers the single-hop case, the moment a value needs more than one hop, the contract switches to `srf:hasPathStep` and never mixes the two forms (see `srf:S1`).

- **The generator emits a `DirectProperty` restatement:** `saas:subscriptionCurrency` asserted directly on each `Subscription` instance, holding the currency value read at the end of the path. Promotion always emits `DirectProperty`, which is the index form designed for unbounded, non-enumerable value spaces (e.g., currency values).

- **Why `srf:ExactSource`?** Because the path is pure traversal — no computation, no mapping relation, nothing lossy. `ExactSource` and `CrosswalkExact` preserve meaning, whilst `DerivedSource` and `CrosswalkInexact` do not, so any surface built from one of those two is capped at `Advisory` authority regardless of what else the contract declares (see `srf:X5`).

- **Where does the promoted property live?** `saas:subscriptionCurrency` is declared by the consuming layer, not minted by Surface — `srf:promotesTo` points at a term the domain already owns precisely so consumers can query something they already know about. This is also the one case where a surface's assertions land on the authored signature rather than staying inside its own generated namespace (its `srf:signatureScope` is `SourceSignature`, not `LocalSignature`) — see "Authority, conservativity, and signature scope" below before treating this kind of surface as freely discardable.

A promotion sometimes has to cross into a different ontology to reach its value — for instance, mapping a locally-recorded diagnosis code to a value from an external clinical coding scheme. That is what `srf:viaMatchRelation` is for: it names the mapping relation to be traversed and the fidelity must be one of the crosswalk values (`CrosswalkExact` if the mapping asserts exact correspondence, `CrosswalkInexact` if it does not). This is the shape of `ontology/surface/examples/clinical-trial-crosswalk.ttl`, which has the same mechanism as the subscription example, but the last step traverses a match relation instead of a same-ontology property, and the resulting surface is advisory because the mapping is inexact.

#### Indexing

The collapse of traversal into a type check or a single triple pattern is the primary value proposition of an index If we ask the question "give me every carrier that has value X", we are looking for retrieval rather than lookup, which is what `IndexContract` supports. Consider role assignments classified by job family, where job families form a hierarchy (`SiteReliability` is narrower than `Engineering`, which is narrower than `Technical`):

```turtle-example
@prefix srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#> .
@prefix ex:  <https://example.org/lattice/surface/> .
@prefix hr:  <https://example.org/hr/> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .

ex:role-job-family a srf:IndexContract ;
	srf:contractKey "job-family" ;
	srf:carrier hr:RoleAssignment ;
	srf:readProperty hr:hasJobFamily ;
	srf:valuePopulation ex:job-family-population ;
	srf:indexForm srf:NominalClass, srf:MembershipAssertion, srf:ClosureRelation ;
	srf:closureBasis skos:broader ;
	srf:namingPolicy srf:LocalNameFromValue ;
	srf:targetNamespace <https://example.org/hr/generated/> ;
	srf:surfaceProfile ex:default-profile .

ex:job-family-population a srf:ContractBoundPopulation ;
	srf:fromSchemeContract hr:job-family-scheme-contract .
```

Let's break down what the generator does:

- **The value population** — `srf:valuePopulation` — is not the job-family scheme itself, but a `ContractBoundPopulation` that names the *scheme contract* governing it (`hr:job-family-scheme-contract`). This is deliberate: the population is whatever scheme is currently bound to that contract, so rebinding the scheme (a new taxonomy version, a governance sign-off) changes what the index covers without anyone editing this surface contract. Naming the scheme directly (an `EnumeratedPopulation` or hand-picked list) is only appropriate for a fixture or a deliberately partial index that isn't meant to track its source.

- **Three index forms, one contract.** `NominalClass` mints a class per value (`Carrier ⊓ ∃R.{v}`, retrieval by `?x a σ(v)`), `MembershipAssertion` asserts each instance's type into that class outright rather than leaving it to entailment, whilst `ClosureRelation` adds a relation from every `RoleAssignment` to every *ancestor* of its job family. Pairing `NominalClass` with `MembershipAssertion` is the usual combination when a deployment wants both a definitional surface and one that answers without a reasoner in the query path.

- **The closure needs a basis.** `srf:closureBasis` names `skos:broader` explicitly — the relation is never assumed. This is required exactly when `ClosureRelation` is declared, and forbidden otherwise (see `srf:S3`). If declared, the generator computes for each carrier instance, every ancestor of its asserted value under that relation's reflexive-transitive closure. If the basis relation reaches values the population doesn't include, `srf:closureScope` narrows the closure to a population boundary instead of following it outside.

- **What retrieval looks like afterwards.** With `MembershipAssertion` materialised, "everyone in Engineering or a descendant of it" becomes `?x a hr_generated_RoleAssignment_job-family_Engineering` for the direct case, or `?x hr_generated_matches_job-family hr:Engineering` via the closure relation for the "any assignment whose family rolls up to Engineering" case — no traversal of `hasJobFamily` and no walking `skos:broader` at query time.

- **Well-foundedness is checked, not assumed.** SPARQL cannot verify acyclicity of a closure over an arbitrary declared relation as a static shape, so the generator itself traverses the basis over the declared scope at generation time and records the result as an `srf:LawDischarge` for `srf:R5`. A closure-form surface with no such discharge on record is non-conformant.

For an example of this kind of shape, see `ontology/surface/examples/employment-job-family.ttl`.

#### Projection

Promotion restates one value, and indexing restates a value as a retrieval symbol. Neither covers intent that needs new graph structure, a computed value, evidence combined across more than one carrier, or one relation expanding into several — the case `ProjectionContract` exists for (ADR-A17). Consider annualising a subscription's recurring revenue: the value is not reachable by any single read path, because it is computed from two of the carrier's own properties rather than read off the end of a chain.

```turtle-example
@prefix srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#> .
@prefix ex:  <https://example.org/lattice/surface/> .
@prefix saas: <https://example.org/saas/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

ex:subscription-arr a srf:ProjectionContract ;
	srf:contractKey "subscription-arr" ;
	srf:carrier saas:Subscription ;
	srf:projectionKind srf:DerivationProjection ;
	srf:hasRoleBinding ex:arr-subject, ex:arr-price, ex:arr-frequency, ex:arr-target ;
	srf:realisationMode srf:Materialised ;
	srf:targetNamespace <https://example.org/saas/generated/> ;
	srf:surfaceProfile ex:default-profile ;
	srf:backendPolicy ex:arr-backend-policy .

ex:arr-subject a srf:ProjectionRoleBinding ; srf:roleKind srf:EvaluationSubjectRole .
ex:arr-price a srf:ProjectionRoleBinding ; srf:roleKind srf:RequiredEvidenceRole ;
	srf:bindsProperty saas:hasMonthlyPrice ; srf:bindsDatatype xsd:decimal .
ex:arr-frequency a srf:ProjectionRoleBinding ; srf:roleKind srf:RequiredEvidenceRole ;
	srf:bindsProperty saas:hasBillingPeriodsPerYear ; srf:bindsDatatype xsd:integer .
ex:arr-target a srf:ProjectionRoleBinding ; srf:roleKind srf:ResultTargetRole ;
	srf:bindsProperty saas:annualRecurringRevenue ; srf:bindsDatatype xsd:decimal ;
	srf:derivedAs ex:arr-expression .

ex:arr-expression a srf:ProductExpression ; srf:resultDatatype xsd:decimal ;
	srf:leftOperand ex:arr-price ; srf:rightOperand ex:arr-frequency .

ex:arr-backend-policy a srf:ProjectionBackendPolicy ;
	srf:allowedBackend srf:SparqlBackend, srf:NativeIrBackend ;
	srf:deterministicOnly true ;
	srf:llmCompletionPolicy srf:NoLLMCompletion .
```

A few things of note:

- **No read path.** A projection reads its evidence through role bindings, not `srf:hasPathStep` — `srf:RequiredEvidenceRole` names the property directly, because the value isn't reached by traversal, it's read from two properties of the carrier itself and combined.
- **Two required-evidence bindings, one contract.** Unlike `EvaluationSubjectRole`, `ResultTargetRole`, and `ClosureBasisRole`, which a contract declares at most once, `RequiredEvidenceRole` and `CandidateEvidenceRole` may repeat — a derivation commonly needs more than one input (`srf:P3`).
- **The operation is stated in the contract.** A derivation states what it computes with `srf:derivedAs` on its result-target binding, in a closed vocabulary of typed expressions (section 6.15). Here the product of the two evidence bindings, a decimal times an integer, is a decimal, and the result-target binding states the same datatype. A shape refuses an operand that states no datatype, an operand that is not an evidence binding of the same contract, and a choice that lacks a branch (`srf:P6` to `srf:P9`).
- **This contract never emits SPARQL, SHACL, or anything else directly.** It lowers into a MORK mapping scheme (ADR-A18). The scheme iterates the carrier class, takes each source node as its own identity so nothing is minted, reads each evidence binding through a typed reference, and asserts the result property with the expression carried across. The backend policy states which compiled targets that scheme may become, and forbids LLM participation in the lowering outright (`srf:deterministicOnly true`).

For a worked instance graph, see `ontology/surface/examples/saas-subscription-arr-projection.ttl`.

#### Graph construction

A derivation computes a value onto the instance. A graph construction writes new structure that no single read path reaches: a node of another class, linked from the instance and carrying values read from it. Consider an order that names its supplier by a code and, where it has one, a name. No read path reaches a supplier as a node of its own, so the contract states the node.

```turtle-example
@prefix srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#> .
@prefix ex:  <https://example.org/lattice/surface/order-supplier#> .

ex:os-code a srf:ProjectionRoleBinding ; srf:roleKind srf:RequiredEvidenceRole ;
	srf:bindsProperty ex:supplierCode .
ex:os-name a srf:ProjectionRoleBinding ; srf:roleKind srf:CandidateEvidenceRole ;
	srf:bindsProperty ex:supplierName .
ex:os-link a srf:ProjectionRoleBinding ; srf:roleKind srf:ResultTargetRole ;
	srf:bindsProperty ex:suppliedBy ; srf:constructedAs ex:os-node .

ex:os-node a srf:ConstructedNode ;
	srf:constructedClass ex:Supplier ;
	srf:nodeIdentity srf:ByKey ; srf:keyBinding ex:os-code ;
	srf:writes [ srf:writesProperty ex:code ; srf:fromBinding ex:os-code ] ,
	           [ srf:writesProperty ex:name ; srf:fromBinding ex:os-name ] .
```

- **The construction is stated on the result-target binding.** The binding binds the link from the instance, here `ex:suppliedBy`, and `srf:constructedAs` names the node the link reaches. A role keeps its one meaning, so `srf:P2` and `srf:P3` stand. The link is mandatory, and under a key it records which instances support a node. Only a graph construction states one (`srf:P10`).
- **The node states what it is.** A class, an identity and at least one value it writes, each value naming an evidence binding of the same contract (`srf:P11`, `srf:P12`). It writes each property once.
- **The identity is the contract's choice, never implicit.** `srf:PerInstance` gives a node for each instance, and `srf:ByKey` one node for each value of a key of required-evidence bindings (`srf:P13`), so two instances with one key share one node. How the identifier is spelled is naming, which the compiler keeps. It is readable from the key, or a hash of the instance's identifier for a node for each instance, and it carries the contract's key, so two contracts never reach one node.
- **An instance contributes whole or not at all.** A node is written only for an instance that holds every required-evidence binding's value. One that has the key and lacks a required value writes no link, even where another instance has made the node, and a check reports it. A candidate-evidence binding writes what it finds, so an order with no name still gives its supplier and its link.
- **A key is spelled into an identifier.** The key's value is part of the node's identifier, which outlives the data it came from, so a key that may be personal, such as an email address or a name, would place a personal value in an identifier, and a key that may change leaves the node under its old identifier. Surface cannot check either, so a key that may be personal or may change is no key. Use a code the thing is known by. Where there is none, construct a node for each instance.
- **A key merges, and a merge is shared.** Instances that give one node different values for one property disagree, and a run-time check names the node and the values. Withdrawing one instance removes its link and leaves the node while another instance supports it, which takes a read of the node's other links, where a node for each instance goes with its instance and reads nothing. A keyed construction takes a mapping review (ADR-A41), since the merge is where a reviewer's judgement is needed, and a construction for each instance takes none.

For a worked instance graph, see `ontology/surface/examples/order-supplier-construction-projection.ttl`. It lowers into a MORK mapping scheme (ADR-A18) whose root takes each order as its own identity, with beneath it the supplier, minted and typed, glued to the order by the link and guarded by the required code, and an assertion for each value.

#### Choosing an index form

The permitted forms trade off differently, supporting choices about population size and retrieval patterns.

- **`DirectProperty`** is preferred whenever the value space is large, open-ended, or not usefully enumerable — it is the only form that doesn't require an enumerable population, and is what promotion always emits.

- **`NominalClass`** (optionally paired with `MembershipAssertion`) is preferred when the population is small and stable enough to mint one class per value, usually where consumers want to ask "is this a member of value *v*" as a type check.

- Add **`ClosureRelation`** on top of a `NominalClass`/`MembershipAssertion` pair only when retrieval by *ancestor* (as opposed to just by the asserted value itself) is a real query pattern. This should only be used alongside a declared `closureBasis`.

- Treat a per-value form (`NominalClass`, `MembershipAssertion`) as suspect past a few hundred values: the profile or contract declares a `srf:populationBudget` (falling back to `srf:defaultPopulationBudget`, then 5000), and exceeding this is a hard failure. A warning fires past 500 even within budget. Past that point, you should aim to restructure as a promotion (`DirectProperty`) instead of raising the budget (which exists precicely to make people think twice about this scenario).

#### Value populations

Every per-value index form needs an enumerable `srf:ValuePopulation` (per `srf:S4`), except `DirectProperty`, which needs none since it never enumerates. Four population kinds are modelled:

- **`ContractBoundPopulation`** — the default choice. This points at a `voc:SchemeContract` rather than a scheme, so the population tracks whatever scheme is currently bound and in the governance state that contract requires.

- **`ClassExtentPopulation`** — for indexing against terms an upper ontology already names rather than a governed scheme, with `srf:extentKind` choosing between the class's named individuals, its direct subclasses, or transitive subclasses.

- **`EnumeratedPopulation`** — an explicit, hand-listed set. Intended for use when no scheme contract or class extent describes the value set (e.g., a fixture, or a deliberately partial index). This does not track a source and will therefore never invalidate!

- **`RangePartitionPopulation`** — declared for partitioning an ordered value space. This is currently a placeholder (SHACL shape flags any usage), because partition laws have yet to be stated. Use a `DirectProperty` form for a quantified dimension for the time being instead.

#### Read paths

Read paths tell the generator how to traverse from a carrier instance to the value being promoted or indexed. They come in two mutually exclusive shapes (viz `srf:S1`):

- **`srf:readProperty`** — a single property, for the common single-hop case (the job-family example above: `hr:hasJobFamily` directly).

- **A sequence of `srf:PathStep` individuals**, one per hop, each with a zero-based `srf:stepIndex` giving traversal order and an explicit `srf:stepDirection` (the subscription-currency example above: three forward hops).

`srf:Forward` traverses a step from subject to object as the property is declared, whilst `srf:Inverse` traverses it from object to subject. A `DefinitionOnly` promotion emits an OWL property-chain axiom rather than materialised triples, and a property chain has no way to express "traverse this backwards," so a definition-only promotion's path steps must all be `srf:Forward`!

#### Generation profiles

Every contract names one `srf:SurfaceProfile`, and every generated artefact names the profile it was produced under. The profile is what lets two runs be compared at all:

- **`generatorVersion`** and **`canonicalisationVersion`** pin the code and the canonical-form rules a profile's hashes depend on. Every hash in this layer is computed under one rule, the substrate's canonicalisation (the substrate's digest rule, Persistence section 5.6): RDFC-1.0 canonical N-Quads, SHA-256, lowercase hex, of the named content. An artefact hash is over emitted bytes instead, reproducible only under the same generator version.
- **`entailmentRegime`** matters specifically for `DefinitionOnly` output — a definitional surface answers nothing until something evaluates it under the named regime (`NoEntailment`, `RDFSEntailment`, `OWL2ELEntailment`, or `OWL2DLEntailment`). Declare `NoEntailment` only where every form the profile's contracts use is `Materialised`.
- **`symbolMode`** chooses between `PunnedSymbols` (the default — a symbol's provenance record shares its IRI with the minted term) and `WrappedSymbols` (a separate provenance individual linked by `srf:denotes`, for toolchains that reject an individual and a class sharing an IRI).
- **`namingNormalisation`**, together with a contract's `srf:namingPolicy` (`LocalNameFromValue`, `QualifiedLocalName`, or `DigestLocalName`), decides how identifier fragments get minted (§8 has the exact concatenation rules). `LocalNameFromValue` is injective only while local names stay unique across the population — the moment two schemes bind one dimension, or two namespaces share a local name, that stops holding, and a collision is a hard failure rather than a warning. `DigestLocalName` is the escape hatch: injective for any population, at the cost of a human-unreadable identifier.
- **`permittedStackDepth`** bounds how many surfaces deep a generation run's read set may reach — this release caps it at one, so a surface may be built over another surface, but not over a surface built over a surface.
- **`defaultPopulationBudget`** is the fallback a contract's own `srf:populationBudget` overrides.

The practical consequence of all this living on the profile rather than being an implicit compiler default: **a profile change is an estate-wide regeneration.** Bump `namingNormalisation` or `symbolMode` and every minted IRI under that profile changes, so the profile carries its own version (it subclasses `fnd:Versioned`) and a change to any of these fields is a new profile version, deliberately, not a silent upgrade.

#### Authority, conservativity, and signature scope

This is the part that decides how much a consumer is allowed to trust a generated surface, and it is worth internalising before wiring anything downstream to one:

- **Conservativity is why an index is free to regenerate or discard.** An index mints only its own terms, so adding one entails nothing new about source terms and removing one loses no authored fact (`srf:X1`). That property, not the performance win, is what licenses treating a generated index as disposable cache.
- **Promotion is the one case that isn't automatically conservative.** `srf:signatureScope` records which situation a given surface is in: `LocalSignature` when a promotion restates onto a property minted in the contract's own target namespace, and `SourceSignature` when it restates onto a property a consuming layer already declares (as in the subscription-currency example above). A `SourceSignature` promotion's assertions are indistinguishable from authored facts once emitted — which is exactly why two laws constrain it rather than leaving it implicit. A promotion reaching the authored signature must declare `ExactSource` or `CrosswalkExact` fidelity and must be `Materialised`, never `DefinitionOnly` (`srf:X6`). Separately, any promotion that is lossy — `DerivedSource` or `CrosswalkInexact` — may not target an authored property at all, only a property in its own generated namespace (`srf:X5`, `srf:X6` again from the other direction).
- **A projection reads its scope from what it writes.** A derivation writes a value on the carrier, and a graph construction writes a node of the class it states. Where that class, or the property it links or writes, is minted in the contract's own target namespace, the projection is local-signature and conservative as an index is (`srf:P1`). Where it is a class an authored vocabulary declares, as `ex:Supplier` is, the constructed nodes and what is written on them reach the authored signature and are indistinguishable from authored facts once emitted, so the projection is source-signature and composes under the same rule as `srf:X1` and `srf:X6`.
- **Authority is capped below authoritative, always.** A surface declares `Advisory` or `CachedReproducible` and nothing higher (`srf:S9`) — an index that outranked the declaration it was built from would invert the derivation order. A lossy promotion is capped specifically at `Advisory` (`srf:X5`). If an external store is genuinely the system of record and accepts writes back, that relationship is a synchronisation contract, not a surface — Surface only ever restates, never originates.

#### Derived records and staying fresh

Nothing in the derived-record tier is asserted by hand — a `srf:GeneratedSurface`, `srf:GeneratedSymbol`, or `srf:ReadSetEntry` without a proper record is unaccounted for and fails governance. In practice, this is the mechanism that answers "is this surface still good, and how much do I need to redo if not":

- Every generation run records what it **read**, not just what it produced: one `srf:ReadSetEntry` per input, each carrying the hash of that input's canonical content at read time. A surface is stale exactly when any entry's current hash no longer matches the recorded one. That single comparison decides staleness, and nothing needs to be classified first.
- Once staleness is known, *how much* to recompute is a smaller question, and the answer depends on what moved. A change to bound scheme membership recomputes that contract's symbol inventory (plus closure, if declared). A change to the carrier instance graph recomputes materialised memberships for the changed instances only, and nothing at all under `DefinitionOnly`. A change to the scheme contract's binding or required governance state, or to the profile identity, forces regeneration of the whole contract or the whole profile's estate respectively. Keeping definitions and materialised assertions in separate emitted modules is precisely what lets an instance-graph change skip the definitional module entirely.
- `srf:semanticContentHash` (the canonical, meaning-bearing inputs) and `srf:artefactHash` (the emitted bytes) serve different jobs. Matching semantic content hash plus matching profile identity is what licenses reusing an existing surface instead of regenerating it, and an artefact hash that changes while both of those hold steady is a generator defect, not a source change.
- Laws don't all get discharged the same way, and knowing which register a law sits in (`srf:lawRegister`) tells you what evidence to expect. A `SemanticLaw` (conservativity, index faithfulness, closure soundness, promotion fidelity, promotion signature discipline) is argued formally and tested as a property, never discharged by inspecting one run. A `StaticConstraint` is checked by the SHACL shapes in §10 over the contract or record graph. A `RuntimeConformance` law (determinism, ontology/surface/source parity, invalidation minimality, materialisation idempotence, closure well-foundedness) is discharged only by an actually executed run, recorded as a `srf:LawDischarge` — never by argument alone.

#### A practical checklist for authoring a contract

1. **Name the carrier and the value.** What class is this about, and what question about it needs to be answerable by lookup instead of traversal?
2. **Decide promotion or index.** Want the value on the subject itself → `PromotionContract`. Want to retrieve subjects by value → `IndexContract`.
3. **Write the read path.** One hop → `srf:readProperty`. More than one, or a hop that runs backwards → `srf:hasPathStep`, indexed and directed.
4. **For a promotion:** pick `srf:promotesTo` (an existing property, ideally), state `srf:sourceFidelity` honestly, and name `srf:viaMatchRelation` if and only if the path crosses a mapping relation.
5. **For an index:** pick a `srf:ValuePopulation` (prefer `ContractBoundPopulation`), pick one or more `srf:indexForm` values against the guidance above, and declare `srf:closureBasis` if and only if `ClosureRelation` is one of them.
6. **Pick a `srf:namingPolicy`** and check it stays injective over the actual population — `DigestLocalName` if it might not.
7. **Point at a `srf:surfaceProfile`.** Don't invent a new one per contract. Reuse the deployment's profile unless there's a real reason to fork it. A fork is a new version and an estate-wide regeneration, so it's not a casual choice.
8. **Let the SHACL shapes in §10 do the rest.** They catch the mechanical mistakes below before generation ever runs.

#### Common pitfalls

- **Declaring both `srf:readProperty` and `srf:hasPathStep`, or neither.** Caught by `srf:ReadPathFormExclusiveShape`, so pick exactly one form.
- **A `ClosureRelation` with no `closureBasis`, or a `closureBasis` with no `ClosureRelation`.** The two are required together (`srf:S3`), never one without the other.
- **Choosing `NominalClass`/`MembershipAssertion` for a population that's actually open-ended.** This is what the population budget is for — if the count is unbounded or grows without a ceiling, it belongs in a `DirectProperty` promotion, not a per-value index.
- **Promoting a lossy value onto an authored property.** A `DerivedSource` or `CrosswalkInexact` promotion may only mint its own property in its own namespace, and pointing `srf:promotesTo` at a property the domain already declares requires exact or crosswalk-exact fidelity.
- **Promoting onto a property no layer declares.** Outside its target namespace a promotion restates onto a property an authored layer declares, so the compiler refuses one whose property the source graph does not declare as a property. Compile against the layer that declares it, or promote into the target namespace.
- **Assuming `LocalNameFromValue` is safe by default.** It's injective only until two schemes or namespaces collide on a local name — which happens exactly when a deployment grows to use more than one scheme for the same dimension. `QualifiedLocalName` or `DigestLocalName` avoid the failure mode outright.
- **Treating a generated surface as evidence for a decision.** A surface accelerates a lookup, and it is never itself the evidence for an admissibility decision or an execution record, and reaching an answer through a surface is a realisation-profile fact recorded on the decision, not a change in what the decision rests on (§12).

## 2. Namespace and Prefixes

```turtle-spec
@prefix srf:  <https://www.nebularis.org/neuro-semantic/lattice/surface#> .
@prefix fnd:  <https://www.nebularis.org/neuro-semantic/lattice/foundation#> .
@prefix voc:  <https://www.nebularis.org/neuro-semantic/lattice/vocabulary#> .
@prefix qnt:  <https://www.nebularis.org/neuro-semantic/lattice/quantification#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .
```

## 3. Extraction Contract

- `turtle-spec` blocks generate `spec/surface.ttl`, concatenated in document order.
- `turtle-vocab` blocks generate `vocab/surface-vocab.ttl`, concatenated in document order.
- `turtle-shapes` blocks generate, in document order: `shapes/structural.ttl`, then `shapes/constraints.ttl`.
- `turtle-example` blocks are illustrative only and are never extracted.
- `projection/*.ttl` files are authored directly, following existing practice in Eligibility, Instrument, and Behaviour.

Extraction and drift checking are performed by `tools/lattice/literate_extract.py`.

The module's entry in the [repository catalogue](../../repository-catalogue.md)
([ADR-A121](../../docs/architecture/decisions/ADR-A121-repository-catalogue.md)) follows.

```toml repository-catalogue
[module]
kind = "standalone"
roles = ["examples", "execution", "shapes", "spec", "test", "vocab"]
imports = ["foundation", "vocabulary", "quantification"]

[module.extract]
spec = ["spec/surface.ttl"]
vocab = ["vocab/surface-vocab.ttl"]
shapes = ["shapes/structural.ttl", "shapes/constraints.ttl"]
```

## 4. Design Decisions

**Read path plus surface form, not a shadow-class mechanism.** A generated class per vocabulary member is one point in a larger space. Declaring a read path from a carrier to a value, and separately declaring the form in which that relationship is restated, covers promotion across ontologies, multi-hop flattening, hierarchical closure, and per-value class generation with one mechanism. Building only the per-value class case would require a second mechanism for any value space that isn't enumerable.

**A population names a contract, never a scheme and never a concept.** `srf:ContractBoundPopulation` points at a `voc:SchemeContract`. The population is whatever scheme is currently bound to that contract, in the governance state that contract requires. This keeps the mechanism domain-neutral while tracking live vocabulary and makes rebinding a scheme simpler.

**Conservativity is the governing property.** A surface extends the signature, not the source-signature consequence set. Adding a surface entails nothing new about source terms and removing one loses no authored fact. 

**Promotion onto an authored property is the one case that leaves the local signature, and it is modelled rather than hidden.** An index always mints its own terms and it therefore conservative by construction. A promotion restates a value on a property that may be either minted in the contract's own target namespace or already declared by a consuming layer. The second case produces statements over the source signature: they are indistinguishable from authored facts, so scope is recorded on the generated surface and a promotion onto an authored property may not be definition-only, whilst a lossy promotion may not target an authored property at all — a value reached across a weaker-than-exact match lands on a generated property, where its derived nature is visible in the identifier.

**Authority is capped below authoritative.** A surface may declare `Advisory` or `CachedReproducible` and nothing higher. An index that outranked the declaration it was built from would invert the derivation order. Where an external store is genuinely the system of record and accepts writes, that is a synchronisation contract and is not a surface.

**Read paths are step lists, not blank-node path expressions.** SHACL property-path syntax nests blank nodes, whose labels do not survive canonicalisation without a blank-node normalisation pass. Indexed `srf:PathStep` individuals give the same sequence-and-inverse expressivity with a canonical form that hashes directly, following the positional pattern `qnt:OrderingComponent` already uses.

**Both punning and wrapper symbol modes are supported.** Punning is cheaper and is the default. Some toolchains do not accept an individual and a class sharing an IRI, so `srf:WrappedSymbols` mints a separate provenance individual linked by `srf:denotes`, following the `mrk:OwlAxiom` convention. The mode is a property of the generation profile, so a deployment chooses once and every artefact under that profile agrees. This mirror's mork's `shadow.py` module's behaviour.

**The nominal form is deliberately EL-safe.** `σ(c) ≡ Carrier ⊓ ∃R.{c}` uses `owl:hasValue`, which is inside OWL 2 EL, so classification over a large generated surface stays tractable. A form requiring a more expressive profile would need its own index form and this is not currently supported.

**Naming is part of the profile, not the compiler.** Normalisation, prefixing, and digest fallback are declared, because a change to any of them changes every minted IRI in the estate and therefore *requires* a profile version bump.

**Well-foundedness of a closure basis is a runtime claim, not a static one.** SPARQL cannot express a property path over a variable predicate, so no fixed SHACL shape can check acyclicity for an arbitrary declared basis. The generator checks it over the declared scope and discharges the law, and a surface that has not discharged it is non-conformant.

**Projection lowers into MORK rather than emitting an artefact itself.** Promotion and indexing cover restatement of one already-reachable value. Graph construction, derivation, joins, and expansion are mapping-graph concerns MORK already owns, so a `ProjectionContract` declares intent and role bindings and hands the rest to MORK's mapping graph and staged compiler family (ADR-A17–ADR-A19), rather than Surface growing a second compiler for the same problem.

## 5. Architecture

There are three tiers, with one class of artefact in each.

```
DECLARATION      srf:SurfaceContract  (srf:PromotionContract | srf:IndexContract | srf:ProjectionContract)
                 srf:ValuePopulation · srf:PathStep · srf:SurfaceProfile · srf:ProjectionRoleBinding · srf:ProjectionBackendPolicy
                 versioned, governable
                 "What may be restated locally, from what, in what form?"

GENERATION       the compiler: contract + read set + profile -> symbols
                 not modelled here; a realisation strategy

DERIVED RECORD   srf:GeneratedSurface · srf:GeneratedSymbol · srf:ReadSetEntry
                 srf:LawDischarge
                 "What was generated, from what exact inputs, under which profile,
                  with what authority, and which runtime laws were discharged?"
```

The declaration tier is authored. The derived-record tier is generated alongside the symbols it describes and lives with them. Generated symbols and their records occupy projection and execution graph roles only, and they never appear in `spec/`, `vocab/`, `shapes/`, or `projection/`.

## 6. Core Model

### 6.1 Ontology header and punned targets

A contract must be able to name any class or property in the estate without importing the layer that declares it. Vocabulary's `voc:constrainsProperty` already establishes this device, and Surface reuses it, which is why the layer sits low in the dependency order rather than above the layers whose terms it names.

```turtle-spec
@base <https://www.nebularis.org/neuro-semantic/surface> .

<https://www.nebularis.org/neuro-semantic/surface>
	rdf:type owl:Ontology ;
	owl:versionIRI <https://www.nebularis.org/neuro-semantic/lattice/surface/0.21.1> ;
	owl:imports <https://www.nebularis.org/neuro-semantic/lattice/foundation/0.21.1> ,
				<https://www.nebularis.org/neuro-semantic/lattice/vocabulary/0.21.1> ,
				<https://www.nebularis.org/neuro-semantic/lattice/quantification/0.21.1> .

rdf:Property rdf:type owl:Class .
rdfs:Class rdf:type owl:Class .
```

### 6.2 Surface contracts

#### `srf:SurfaceContract`

**Definition.** A governed declaration that a relationship reachable from a carrier may be restated locally in a declared form.

**Utility.** Author one whenever a question about a carrier must be answerable without traversing the path that establishes the answer. Give it a carrier, a read path, a realisation mode, a stable key, a target namespace for minted symbols, and the profile it is generated under. Use `srf:PromotionContract` to restate a value as a direct assertion, and `srf:IndexContract` to restate it as a symbol subjects can be retrieved by.

```turtle-spec
srf:SurfaceContract a owl:Class ;
	rdfs:comment "A governed declaration that a relationship reachable from a carrier may be restated locally in a declared form." ;
	fnd:utility "Author one whenever a question about a carrier must be answerable without traversing the path that establishes the answer. Give it a carrier, a read path, a realisation mode, a stable contract key, a target namespace for minted symbols, and a surface profile. Use PromotionContract to restate a value as a direct assertion and IndexContract to restate it as a retrievable symbol." ;
	rdfs:subClassOf
		fnd:Versioned ,
		fnd:Governable ,
		[ a owl:Restriction ; owl:onProperty srf:carrier ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:contractKey ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:targetNamespace ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:realisationMode ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:surfaceProfile ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:readProperty ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:populationBudget ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ] .
```

#### `srf:PromotionContract`

**Definition.** A surface contract restating a value reachable by a read path as a direct assertion on the carrier.

**Utility.** Use where a value is only reachable through a chain of relations, or through a mapping relation into another ontology, and consumers need it on the subject itself. Set `srf:promotesTo` to the local property that will carry the value, and `srf:sourceFidelity` to state whether the restatement preserves meaning. A promotion traversing a mapping relation names that relation in `srf:viaMatchRelation`.

```turtle-spec
srf:PromotionContract a owl:Class ;
	rdfs:subClassOf srf:SurfaceContract ,
		[ a owl:Restriction ; owl:onProperty srf:promotesTo ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:sourceFidelity ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:viaMatchRelation ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "A surface contract restating a value reachable by a read path as a direct assertion on the carrier." ;
	fnd:utility "Use where a value is reachable only through a chain of relations or through a mapping relation into another ontology, and consumers need it on the subject itself. Set promotesTo to the local property carrying the value and sourceFidelity to state whether the restatement preserves meaning. Name any traversed mapping relation in viaMatchRelation." .
```

#### `srf:IndexContract`

**Definition.** A surface contract restating a carrier's values as symbols by which carriers can be retrieved.

**Utility.** Use where retrieval by value is the hot operation. Declare the value population, one or more index forms, and a naming policy. Declare a closure basis where retrieval must also succeed for ancestors of the asserted value. `srf:closureScope` narrows the value set the closure is computed over, and unset means the contract's own population.

```turtle-spec
srf:IndexContract a owl:Class ;
	rdfs:subClassOf srf:SurfaceContract ,
		[ a owl:Restriction ; owl:onProperty srf:valuePopulation ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:indexForm ; owl:minCardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:namingPolicy ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:closureBasis ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:closureScope ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "A surface contract restating a carrier's values as symbols by which carriers can be retrieved." ;
	fnd:utility "Use where retrieval by value is the hot operation. Declare the value population, one or more index forms, and a naming policy. Declare a closure basis where retrieval must also succeed for ancestors of the asserted value; closureScope narrows the value set the closure is computed over." .
```

#### `srf:ProjectionContract`

**Definition.** A surface contract restating mapping intent that requires graph construction, derivation, a join, or an expansion, lowered into MORK rather than emitted directly.

**Utility.** Use where neither promotion's direct-property restatement nor indexing's population membership covers the intent — a computed value, a join across carriers, or one relation expanding into several. Declare a `srf:projectionKind`, at least one role binding naming what the projection reads and where it writes, and a backend policy. A projection contract never emits SPARQL, SHACL, or SWRL itself. It lowers into a MORK mapping graph (ADR-A18), which a separate compiler stage compiles (ADR-A19).

```turtle-spec
srf:ProjectionContract a owl:Class ;
	rdfs:subClassOf srf:SurfaceContract ,
		[ a owl:Restriction ; owl:onProperty srf:projectionKind ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:hasRoleBinding ; owl:minCardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:backendPolicy ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "A surface contract restating mapping intent that requires graph construction, derivation, a join, or an expansion, lowered into MORK rather than emitted directly." ;
	fnd:utility "Use where neither promotion's direct-property restatement nor indexing's population membership covers the intent — a computed value, a join across carriers, or one relation expanding into several. Declare a projectionKind, at least one role binding naming what the projection reads and where it writes, and a backend policy. A ProjectionContract never emits SPARQL, SHACL, or SWRL itself; it lowers into a MORK mapping graph, which a separate compiler stage compiles." .
```

### 6.3 Read paths

#### `srf:PathStep`

**Definition.** One positioned traversal within a read path, in a stated direction.

**Utility.** Use where the value is not reachable by a single property. Add one step per hop with a zero-based `srf:stepIndex` in traversal order and an explicit `srf:stepDirection`. For a single-hop path use `srf:readProperty` instead, since a contract declares one form or the other, never both.

```turtle-spec
srf:PathStep a owl:Class ;
	rdfs:comment "One positioned traversal within a read path, in a stated direction." ;
	fnd:utility "Use where the value is not reachable by a single property. Add one step per hop with a zero-based stepIndex in traversal order and an explicit stepDirection. For a single-hop path use readProperty instead; a contract declares one form or the other, never both." ;
	rdfs:subClassOf
		[ a owl:Restriction ; owl:onProperty srf:stepIndex ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:stepProperty ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:stepDirection ; owl:cardinality "1"^^xsd:nonNegativeInteger ] .
```

### 6.4 Value populations

#### `srf:ValuePopulation`

**Definition.** The declared set of values a contract's symbols are generated for.

**Utility.** Required by any index form that mints one symbol per value. Prefer `srf:ContractBoundPopulation`, which follows a scheme contract rather than naming a scheme, so rebinding the scheme changes the population without editing the surface contract.

```turtle-spec
srf:ValuePopulation a owl:Class ;
	rdfs:comment "The declared set of values a contract's symbols are generated for." ;
	fnd:utility "Required by any index form that mints one symbol per value. Prefer ContractBoundPopulation, which follows a scheme contract rather than naming a scheme, so rebinding the scheme changes the population without editing the surface contract." .

srf:ContractBoundPopulation a owl:Class ;
	rdfs:subClassOf srf:ValuePopulation ,
		[ a owl:Restriction ; owl:onProperty srf:fromSchemeContract ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "A population comprising the members of whichever concept scheme resolves for a named scheme contract, given the population's declared active binding scopes and the compiler's resolution time." ;
	fnd:utility "Point fromSchemeContract at the voc:SchemeContract governing the read path's value property, and declare activeBindingScope for each voc:BindingScope this population is generated within, if any. The population is the membership of whichever scheme the Vocabulary resolver selects for that contract — the most specific applicable voc:SchemeBinding, or the contract's boundScheme fallback — in whatever governance state the contract requires (ADR-A85)." .

srf:ClassExtentPopulation a owl:Class ;
	rdfs:subClassOf srf:ValuePopulation ,
		[ a owl:Restriction ; owl:onProperty srf:fromClass ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:extentKind ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "A population comprising the declared extent of a class in a source ontology." ;
	fnd:utility "Use to index against terms an upper ontology already names, rather than against concepts in a bound scheme. Set extentKind to state whether the extent is the class's named individuals, its direct subclasses, or its transitive subclasses." .

srf:EnumeratedPopulation a owl:Class ;
	rdfs:subClassOf srf:ValuePopulation ,
		[ a owl:Restriction ; owl:onProperty srf:hasPopulationMember ; owl:minCardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "A population listed explicitly, member by member." ;
	fnd:utility "Use only where no scheme contract or class extent describes the value set — a fixture, or a deliberately partial index. An enumerated population does not track its source and will not invalidate when that source changes." .

srf:RangePartitionPopulation a owl:Class ;
	rdfs:subClassOf srf:ValuePopulation ,
		[ a owl:Restriction ; owl:onProperty srf:fromRangeSet ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "A population comprising the partition induced by a declared range set over an ordered value space." ;
	fnd:utility "Declared and not yet permitted. Until a partition law is stated, use a DirectProperty index form for quantified dimensions." .
```

### 6.5 Generation profile

#### `srf:SurfaceProfile`

**Definition.** The declared generation configuration under which a surface is produced.

**Utility.** Every generated artefact names one. Two artefacts are interchangeable only if they share both a profile identity and the same source content, so any change to the generator, the naming normalisation, the symbol mode, the entailment regime, or the canonicalisation contract is a new profile version and a full regeneration.

```turtle-spec
srf:SurfaceProfile a owl:Class ;
	rdfs:subClassOf fnd:Versioned ,
		[ a owl:Restriction ; owl:onProperty srf:generatorVersion ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:canonicalisationVersion ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:entailmentRegime ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:namingNormalisation ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:symbolMode ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:permittedStackDepth ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:defaultPopulationBudget ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "The declared generation configuration under which a surface is produced." ;
	fnd:utility "Every generated artefact names one. Two artefacts are interchangeable only if they share a profile identity and the same source content, so a change to the generator, naming normalisation, symbol mode, entailment regime, or canonicalisation contract is a new profile version and a full regeneration." .
```

### 6.6 Generated terms

Generated classes and properties are marked by parentage rather than by type assertion, so that a surface loaded in wrapper mode introduces no class-as-individual statements of its own.

```turtle-spec
srf:GeneratedClass a owl:Class ;
	rdfs:comment "The common parent of every class minted by a surface generator." ;
	fnd:utility "Every generated class reaches this by rdfs:subClassOf, directly or through its contract's family class. Query for its subclasses to enumerate a surface's class inventory without relying on punning." .

srf:generatedRelation a owl:ObjectProperty ;
	rdfs:comment "The common parent of every object property minted by a surface generator." ;
	fnd:utility "Every generated object relation, including closure relations and promoted object-valued properties, is a subproperty of this." .

srf:generatedAttribute a owl:DatatypeProperty ;
	rdfs:comment "The common parent of every datatype property minted by a surface generator." ;
	fnd:utility "Every generated literal-valued property, including promoted datatype-valued properties, is a subproperty of this." .
```

### 6.7 Derived records

#### `srf:DerivedArtefact`

**Definition.** A recorded product of a generation run, traceable to its inputs, its profile, and its authority.

**Utility.** Never assert one by hand. A derived artefact states what produced it and how far it may be trusted, and a generated symbol without such a record is unaccounted for and fails governance.

```turtle-spec
srf:DerivedArtefact a owl:Class ;
	rdfs:subClassOf fnd:Evidenced , fnd:DerivedArtefact ,
		[ a owl:Restriction ; owl:onProperty srf:generatedByProfile ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:derivationAuthority ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:producedAt ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "A recorded product of a generation run, traceable to its inputs, its profile, and its authority." ;
	fnd:utility "Never assert one by hand. A derived artefact states what produced it and how far it may be trusted; a generated symbol without such a record is unaccounted for and fails governance." .

srf:GeneratedSurface a owl:Class ;
	rdfs:subClassOf srf:DerivedArtefact ,
		[ a owl:Restriction ; owl:onProperty srf:coversContract ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:hasReadSetEntry ; owl:minCardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:stackDepth ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:signatureScope ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:populationSize ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:semanticContentHash ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:artefactHash ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "The recorded output of one generation run for one surface contract." ;
	fnd:utility "One per contract per run. Carries the read set the run depended on, the symbol inventory counts, and the hashes that decide whether the surface is still current." .

srf:GeneratedSymbol a owl:Class ;
	rdfs:subClassOf srf:DerivedArtefact ,
		[ a owl:Restriction ; owl:onProperty srf:inSurface ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:symbolForm ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:denotes ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:fromValue ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "The record of one term minted by a generation run." ;
	fnd:utility "Points at the minted term through denotes, and at the source value through fromValue where the form mints one symbol per value. In punned symbol mode the record and the term share an IRI; in wrapper mode they do not." .

srf:ReadSetEntry a owl:Class ;
	rdfs:subClassOf
		[ a owl:Restriction ; owl:onProperty srf:readsSource ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:readSourceKind ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:readHash ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:readVersion ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:resolvedAt ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:resolvedBinding ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:resolvedViaFallback ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "One input a generation run depended on, with the version and hash it was read at." ;
	fnd:utility "The unit of invalidation. A surface is stale when any entry's current hash differs from the recorded one; nothing else needs to be classified to know that. resolvedAt/resolvedBindingScope/resolvedBinding/resolvedViaFallback are populated on a BoundSchemeSource entry to record why its scheme was the one resolved (Finding 2), never to redecide invalidation." .

srf:SymbolCount a owl:Class ;
	rdfs:subClassOf
		[ a owl:Restriction ; owl:onProperty srf:countForm ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:countValue ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "The number of symbols a generation run minted in one index form." ;
	fnd:utility "Use for inventory parity between runs without materialising a diff of every symbol." .

srf:LawDischarge a owl:Class ;
	rdfs:subClassOf fnd:Evidenced ,
		[ a owl:Restriction ; owl:onProperty srf:dischargesLaw ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:dischargedForSurface ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:dischargedAt ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "Recorded evidence that one runtime-conformance law held for one generated surface." ;
	fnd:utility "Required for every law in the runtime-conformance register that the contract's declared forms bring into play. A formal argument never discharges one of these; only an executed run does." .
```

### 6.8 Mechanism kind classes

```turtle-spec
srf:IndexForm a owl:Class .
srf:RealisationMode a owl:Class .
srf:NamingPolicy a owl:Class .
srf:NamingNormalisation a owl:Class .
srf:SourceFidelity a owl:Class .
srf:ExtentKind a owl:Class .
srf:StepDirection a owl:Class .
srf:EntailmentRegime a owl:Class .
srf:SymbolMode a owl:Class .
srf:ReadSourceKind a owl:Class .
srf:SignatureScope a owl:Class .
srf:DerivationAuthority a owl:Class .
srf:Law a owl:Class ;
	rdfs:subClassOf [ a owl:Restriction ; owl:onProperty srf:lawRegister ; owl:cardinality "1"^^xsd:nonNegativeInteger ] .
srf:LawRegister a owl:Class .
```

### 6.9 Properties

```turtle-spec
srf:carrier a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:SurfaceContract ; rdfs:range rdfs:Class ;
	rdfs:comment "The class whose instances a surface contract restates a relationship for." ;
	fnd:utility "Names a class declared in any layer, by punning. Surface never imports the layer the carrier belongs to." .

srf:readProperty a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:SurfaceContract ; rdfs:range rdf:Property ;
	rdfs:comment "The single property reaching a carrier's value, where the read path is one hop." ;
	fnd:utility "Use for the common single-hop case. A contract declares either this or a sequence of PathStep individuals, never both." .

srf:hasPathStep a owl:ObjectProperty ;
	rdfs:domain srf:SurfaceContract ; rdfs:range srf:PathStep ;
	rdfs:comment "A positioned traversal belonging to a multi-hop read path." ;
	fnd:utility "Add one per hop; the steps' indices give the traversal order." .

srf:stepProperty a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:PathStep ; rdfs:range rdf:Property ;
	rdfs:comment "The property traversed by a path step." .

srf:stepDirection a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:PathStep ; rdfs:range srf:StepDirection ;
	rdfs:comment "Whether a path step is traversed from subject to object or from object to subject." .

srf:stepIndex a owl:DatatypeProperty, owl:FunctionalProperty ;
	rdfs:domain srf:PathStep ; rdfs:range xsd:nonNegativeInteger ;
	rdfs:comment "The zero-based position of a path step within its read path." .

srf:surfaceProfile a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:SurfaceContract ; rdfs:range srf:SurfaceProfile ;
	rdfs:comment "The generation profile a surface contract is generated under." .

srf:realisationMode a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:SurfaceContract ; rdfs:range srf:RealisationMode ;
	rdfs:comment "Whether a contract emits definitions, materialised assertions, or both." ;
	fnd:utility "DefinitionOnly leaves the work to a declared entailment regime; Materialised emits assertions and needs none. Mode decides which generated module a change lands in, so it also decides invalidation scope." .

srf:promotesTo a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:PromotionContract ; rdfs:range rdf:Property ;
	rdfs:comment "The local property a promotion contract restates its value on." ;
	fnd:utility "Declared, not minted. Point it at a property the consuming layer already declares, so consumers query a term they know." .

srf:sourceFidelity a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:PromotionContract ; rdfs:range srf:SourceFidelity ;
	rdfs:comment "Whether a promotion preserves the meaning of the value it restates." ;
	fnd:utility "ExactSource and CrosswalkExact preserve meaning. DerivedSource and CrosswalkInexact do not, and cap the resulting surface at advisory authority." .

srf:viaMatchRelation a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:PromotionContract ; rdfs:range rdf:Property ;
	rdfs:comment "The mapping relation a promotion traverses, where it crosses between schemes." ;
	fnd:utility "Required for either crosswalk fidelity and absent otherwise. Name the exact relation traversed rather than a family of them, since match strength is what the fidelity declaration rests on." .

srf:valuePopulation a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:IndexContract ; rdfs:range srf:ValuePopulation ;
	rdfs:comment "The value set an index contract mints symbols for." .

srf:indexForm a owl:ObjectProperty ;
	rdfs:domain srf:IndexContract ; rdfs:range srf:IndexForm ;
	rdfs:comment "A form in which an index contract restates its values." ;
	fnd:utility "Declare more than one where a deployment wants both a definitional surface and an inert one — NominalClass with MembershipAssertion is the usual pair." .

srf:namingPolicy a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:IndexContract ; rdfs:range srf:NamingPolicy ;
	rdfs:comment "How an index contract derives a minted symbol's identifier from a value." .

srf:closureBasis a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:IndexContract ; rdfs:range rdf:Property ;
	rdfs:comment "The property whose reflexive-transitive closure an ancestor-compatible index is computed over." ;
	fnd:utility "Declared rather than assumed. Set it to whichever relation orders the value set — a scheme's broader relation, a subclass relation, or a deployment's own ordering property." .

srf:closureScope a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:IndexContract ; rdfs:range srf:ValuePopulation ;
	rdfs:comment "The value set a closure is computed within, where it differs from the contract's own population." ;
	fnd:utility "Set this where the basis relation reaches values outside the indexed population and the closure must stop at the population boundary." .

srf:fromSchemeContract a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:ContractBoundPopulation ; rdfs:range voc:SchemeContract ;
	rdfs:comment "The scheme contract whose resolved scheme supplies a population's members." .

srf:activeBindingScope a owl:ObjectProperty ;
	rdfs:domain srf:ContractBoundPopulation ; rdfs:range voc:BindingScope ;
	rdfs:comment "A scope this population's caller is active within, for resolving which voc:SchemeBinding applies." ;
	fnd:utility "Declare one value per scope this population is generated within. None declared means the unscoped context, where only a scopeless SchemeBinding or the contract's boundScheme fallback can apply (ADR-A85)." .

srf:fromClass a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:ClassExtentPopulation ; rdfs:range rdfs:Class ;
	rdfs:comment "The class whose declared extent supplies a population's members." .

srf:extentKind a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:ClassExtentPopulation ; rdfs:range srf:ExtentKind ;
	rdfs:comment "Which extent of a class a population takes." .

srf:hasPopulationMember a owl:ObjectProperty ;
	rdfs:domain srf:EnumeratedPopulation ;
	rdfs:comment "A value listed explicitly in an enumerated population." .

srf:fromRangeSet a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:RangePartitionPopulation ; rdfs:range qnt:RangeSet ;
	rdfs:comment "The range set whose induced partition supplies a population's members." .

srf:entailmentRegime a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:SurfaceProfile ; rdfs:range srf:EntailmentRegime ;
	rdfs:comment "The entailment regime under which a profile's definitional output is expected to be evaluated." ;
	fnd:utility "A DefinitionOnly surface answers nothing without the regime named here. State NoEntailment only where every declared form is materialised." .

srf:namingNormalisation a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:SurfaceProfile ; rdfs:range srf:NamingNormalisation ;
	rdfs:comment "The transformation applied to identifier fragments before a symbol is minted." .

srf:symbolMode a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:SurfaceProfile ; rdfs:range srf:SymbolMode ;
	rdfs:comment "Whether a profile records symbol provenance on the minted term itself or on a separate individual." .

srf:generatedByProfile a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:DerivedArtefact ; rdfs:range srf:SurfaceProfile ;
	rdfs:comment "The profile a derived artefact was produced under." .

srf:derivationAuthority a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:DerivedArtefact ; rdfs:range srf:DerivationAuthority ;
	rdfs:comment "How far a derived artefact may be trusted on its own." ;
	fnd:utility "A surface never declares an authority above CachedReproducible. Where an external store is the system of record, that is a synchronisation contract and not a surface." .

srf:coversContract a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:GeneratedSurface ; rdfs:range srf:SurfaceContract ;
	rdfs:comment "The surface contract a generation run was performed for." .

srf:hasReadSetEntry a owl:ObjectProperty ;
	rdfs:domain srf:GeneratedSurface ; rdfs:range srf:ReadSetEntry ;
	rdfs:comment "An input a generation run depended on." .

srf:readsSource a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:ReadSetEntry ;
	rdfs:comment "The graph, declaration, scheme, or surface a read-set entry was taken from." .

srf:readSourceKind a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:ReadSetEntry ; rdfs:range srf:ReadSourceKind ;
	rdfs:comment "What kind of input a read-set entry names." ;
	fnd:utility "SurfaceSource entries are what make a surface stacked; the depth they imply is checked against the profile's permitted stack depth." .

srf:resolvedBindingScope a owl:ObjectProperty ;
	rdfs:domain srf:ReadSetEntry ; rdfs:range voc:BindingScope ;
	rdfs:comment "A scope that was active when a BoundSchemeSource read-set entry's scheme was resolved." ;
	fnd:utility "Recorded on every BoundSchemeSource entry for a contract-bound population, whether or not any value is present — an empty set here means the unscoped context, exactly as for srf:activeBindingScope, so the two are always directly comparable." .

srf:resolvedBinding a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:ReadSetEntry ; rdfs:range voc:SchemeBinding ;
	rdfs:comment "The voc:SchemeBinding a BoundSchemeSource read-set entry's scheme was resolved from, absent when the contract's boundScheme fallback was used instead." .

srf:signatureScope a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:GeneratedSurface ; rdfs:range srf:SignatureScope ;
	rdfs:comment "Whether a generated surface's output stays within its own minted terms or reaches the authored signature." ;
	fnd:utility "An index is always local. A promotion is local when it restates onto a property minted in the contract's target namespace, and reaches the source signature when it restates onto a property a consuming layer already declares. Read this before treating a surface as discardable." .

srf:inSurface a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:GeneratedSymbol ; rdfs:range srf:GeneratedSurface ;
	rdfs:comment "The generated surface a symbol record belongs to." .

srf:symbolForm a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:GeneratedSymbol ; rdfs:range srf:IndexForm ;
	rdfs:comment "The index form a symbol was minted in." .

srf:fromValue a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:GeneratedSymbol ;
	rdfs:comment "The source value a symbol was minted for, where the form mints one symbol per value." .

srf:denotes a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:GeneratedSymbol ;
	rdfs:comment "The minted term a symbol record accounts for." .

srf:hasSymbolCount a owl:ObjectProperty ;
	rdfs:domain srf:GeneratedSurface ; rdfs:range srf:SymbolCount ;
	rdfs:comment "A per-form tally of the symbols a generation run minted." .

srf:countForm a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:SymbolCount ; rdfs:range srf:IndexForm ;
	rdfs:comment "The index form a symbol count is taken over." .

srf:dischargesLaw a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:LawDischarge ; rdfs:range srf:Law ;
	rdfs:comment "The law a discharge record evidences." .

srf:dischargedForSurface a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:LawDischarge ; rdfs:range srf:GeneratedSurface ;
	rdfs:comment "The generated surface a law was discharged for." .

srf:lawRegister a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:Law ; rdfs:range srf:LawRegister ;
	rdfs:comment "Which evidence register a law belongs to." ;
	fnd:utility "Check this before asking how a law is discharged: a semantic law needs a formal argument, a static constraint needs static analysis, a runtime-conformance claim needs an executed run." .

srf:contractKey a owl:DatatypeProperty, owl:FunctionalProperty ;
	rdfs:domain srf:SurfaceContract ; rdfs:range xsd:string ;
	rdfs:comment "A stable key identifying a surface contract within its deployment." ;
	fnd:utility "Participates in every identifier the contract mints, so changing it renames the whole surface. Choose it once, at authoring time." .

srf:targetNamespace a owl:DatatypeProperty, owl:FunctionalProperty ;
	rdfs:domain srf:SurfaceContract ; rdfs:range xsd:anyURI ;
	rdfs:comment "The namespace a surface contract's minted identifiers are placed in." ;
	fnd:utility "Keep generated terms out of the namespace of any authored layer, so that a generated term is recognisable as generated from its IRI alone." .

srf:populationBudget a owl:DatatypeProperty, owl:FunctionalProperty ;
	rdfs:domain srf:SurfaceContract ; rdfs:range xsd:nonNegativeInteger ;
	rdfs:comment "The largest population a contract may mint one symbol per value for." ;
	fnd:utility "Overrides the profile default. Raising it is a deliberate act: a per-value form over a large population is the case a DirectProperty form exists to avoid." .

srf:defaultPopulationBudget a owl:DatatypeProperty, owl:FunctionalProperty ;
	rdfs:domain srf:SurfaceProfile ; rdfs:range xsd:nonNegativeInteger ;
	rdfs:comment "The population budget applied to any contract under a profile that declares none of its own." .

srf:generatorVersion a owl:DatatypeProperty, owl:FunctionalProperty ;
	rdfs:domain srf:SurfaceProfile ; rdfs:range xsd:string ;
	rdfs:comment "The version of the generator a profile binds." .

srf:canonicalisationVersion a owl:DatatypeProperty, owl:FunctionalProperty ;
	rdfs:domain srf:SurfaceProfile ; rdfs:range xsd:string ;
	rdfs:comment "The version of the canonicalisation contract a profile's hashes are computed under. The contract is the substrate's, RDFC-1.0 canonical N-Quads, SHA-256, lowercase hex (the substrate's digest rule, Persistence section 5.6), and the version names the rule that selects the content triples." .

srf:namingPrefix a owl:DatatypeProperty, owl:FunctionalProperty ;
	rdfs:domain srf:IndexContract ; rdfs:range xsd:string ;
	rdfs:comment "The disambiguating token inserted into minted identifiers under a qualified naming policy." .

srf:permittedStackDepth a owl:DatatypeProperty, owl:FunctionalProperty ;
	rdfs:domain srf:SurfaceProfile ; rdfs:range xsd:nonNegativeInteger ;
	rdfs:comment "The deepest chain of surface-over-surface generation a profile allows." .

srf:stackDepth a owl:DatatypeProperty, owl:FunctionalProperty ;
	rdfs:domain srf:GeneratedSurface ; rdfs:range xsd:nonNegativeInteger ;
	rdfs:comment "How many surfaces deep a generation run's read set reaches." ;
	fnd:utility "Zero where every input is a source graph. One where an input is itself a generated surface, and so on." .

srf:populationSize a owl:DatatypeProperty, owl:FunctionalProperty ;
	rdfs:domain srf:GeneratedSurface ; rdfs:range xsd:nonNegativeInteger ;
	rdfs:comment "The number of values a generation run enumerated." .

srf:producedAt a owl:DatatypeProperty, owl:FunctionalProperty ;
	rdfs:domain srf:DerivedArtefact ; rdfs:range xsd:dateTime ;
	rdfs:comment "When a derived artefact was produced." .

srf:artefactHash a owl:DatatypeProperty, owl:FunctionalProperty ;
	rdfs:domain srf:GeneratedSurface ; rdfs:range xsd:string ;
	rdfs:comment "The SHA-256, lowercase hex, of a generation run's emitted bytes as the generator version the profile binds serialised them." ;
	fnd:utility "Compare across runs to establish that regeneration was deterministic. A change here with no change in the read set or profile is a generator defect." .

srf:semanticContentHash a owl:DatatypeProperty, owl:FunctionalProperty ;
	rdfs:domain srf:GeneratedSurface ; rdfs:range xsd:string ;
	rdfs:comment "The digest of the canonical, meaning-bearing inputs a generation run consumed: the RDFC-1.0 canonical N-Quads, SHA-256, lowercase hex, of the dataset whose graphs are the read set's inputs, each in a graph named by its entry (the substrate's digest rule, Persistence section 5.6)." ;
	fnd:utility "Together with the profile identity, decides whether an existing surface may be reused rather than regenerated." .

srf:readVersion a owl:DatatypeProperty, owl:FunctionalProperty ;
	rdfs:domain srf:ReadSetEntry ; rdfs:range xsd:string ;
	rdfs:comment "The version identifier an input carried when it was read." .

srf:readHash a owl:DatatypeProperty, owl:FunctionalProperty ;
	rdfs:domain srf:ReadSetEntry ; rdfs:range xsd:string ;
	rdfs:comment "The digest of an input's canonical content at the time it was read: the RDFC-1.0 canonical N-Quads, SHA-256, lowercase hex, of the input's graph (the substrate's digest rule, Persistence section 5.6)." .

srf:resolvedAt a owl:DatatypeProperty, owl:FunctionalProperty ;
	rdfs:domain srf:ReadSetEntry ; rdfs:range xsd:dateTime ;
	rdfs:comment "The resolution instant used to resolve a BoundSchemeSource read-set entry's scheme." ;
	fnd:utility "Recorded on every BoundSchemeSource entry, so an auditor can recover why a given compile resolved the scheme it did without re-running the compiler (Finding 2). Distinct from srf:producedAt: the same production run's resolution instant, named explicitly here as the semantic input it is, per srf:R1's updated text." .

srf:resolvedViaFallback a owl:DatatypeProperty, owl:FunctionalProperty ;
	rdfs:domain srf:ReadSetEntry ; rdfs:range xsd:boolean ;
	rdfs:comment "Whether a BoundSchemeSource read-set entry's scheme came from the contract's boundScheme fallback rather than a resolved voc:SchemeBinding." .

srf:countValue a owl:DatatypeProperty, owl:FunctionalProperty ;
	rdfs:domain srf:SymbolCount ; rdfs:range xsd:nonNegativeInteger ;
	rdfs:comment "The number of symbols tallied in one index form." .

srf:dischargedAt a owl:DatatypeProperty, owl:FunctionalProperty ;
	rdfs:domain srf:LawDischarge ; rdfs:range xsd:dateTime ;
	rdfs:comment "When a law discharge was recorded." .

srf:executedRun a owl:DatatypeProperty, owl:FunctionalProperty ;
	rdfs:domain srf:LawDischarge ; rdfs:range xsd:string ;
	rdfs:comment "The identifier of the executed run evidencing a law discharge." .
```

### 6.10 Disjointness

```turtle-spec
[] a owl:AllDisjointClasses ;
	owl:members ( srf:SurfaceContract srf:PathStep srf:ValuePopulation srf:SurfaceProfile
				  srf:DerivedArtefact srf:ReadSetEntry srf:SymbolCount srf:LawDischarge
				  srf:IndexForm srf:RealisationMode srf:NamingPolicy srf:NamingNormalisation
				  srf:SourceFidelity srf:ExtentKind srf:StepDirection srf:EntailmentRegime
				  srf:SymbolMode srf:ReadSourceKind srf:SignatureScope srf:DerivationAuthority
				  srf:Law srf:LawRegister srf:ProjectionRoleBinding srf:ProjectionBackendPolicy
				  srf:ProjectionKind srf:ProjectionRole srf:CompilerBackend srf:LLMCompletionPolicy ) .

srf:PromotionContract owl:disjointWith srf:IndexContract .
srf:ProjectionContract owl:disjointWith srf:PromotionContract, srf:IndexContract .
srf:GeneratedSurface owl:disjointWith srf:GeneratedSymbol .
srf:ContractBoundPopulation owl:disjointWith srf:ClassExtentPopulation, srf:EnumeratedPopulation, srf:RangePartitionPopulation .
srf:ClassExtentPopulation owl:disjointWith srf:EnumeratedPopulation, srf:RangePartitionPopulation .
srf:EnumeratedPopulation owl:disjointWith srf:RangePartitionPopulation .
```

### 6.11 Projection role bindings

#### `srf:ProjectionRoleBinding`

**Definition.** One named role a projection contract binds to a property and, where the role's evidence comes from a different class than the contract's own carrier, to that class.

**Utility.** Name the role a property or carrier plays explicitly, rather than leaving a compiler to infer it from position — the same discipline `srf:PathStep` applies to a read path, extended to intents with more than one moving part. Every projection names at least an evaluation-subject and a result-target role, and a join or derivation names candidate-evidence or required-evidence roles as well.

```turtle-spec
srf:ProjectionRoleBinding a owl:Class ;
	rdfs:subClassOf
		[ a owl:Restriction ; owl:onProperty srf:roleKind ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:bindsProperty ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:bindsCarrier ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:bindsDatatype ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:derivedAs ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:constructedAs ; owl:maxCardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "One named role a projection contract binds to a property and, where the role's evidence comes from a different class than the contract's own carrier, to that class." ;
	fnd:utility "Name the role a property or carrier plays explicitly, rather than leaving a compiler to infer it from position — the same discipline srf:PathStep applies to a read path, extended to intents with more than one moving part. Every projection names at least an evaluation-subject and a result-target role; a join or derivation names candidate-evidence or required-evidence roles as well." .
```

### 6.12 Projection backend policy

#### `srf:ProjectionBackendPolicy`

**Definition.** The declared backend eligibility and LLM-participation policy a projection contract lowers under.

**Utility.** Name every backend a lowered mapping may target in `srf:allowedBackend`, or every backend it may not in `srf:deniedBackend`, never both for one backend. Set `srf:deterministicOnly` true to forbid LLM completion outright during lowering, and set `srf:llmCompletionPolicy` to state what happens when it is false.

```turtle-spec
srf:ProjectionBackendPolicy a owl:Class ;
	rdfs:subClassOf
		[ a owl:Restriction ; owl:onProperty srf:llmCompletionPolicy ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:deterministicOnly ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "The declared backend eligibility and LLM-participation policy a projection contract lowers under." ;
	fnd:utility "Name every backend a lowered mapping may target in allowedBackend, or every backend it may not in deniedBackend, never both for one backend. Set deterministicOnly true to forbid LLM completion outright during lowering; set llmCompletionPolicy to state what happens when it is false." .
```

### 6.13 Projection mechanism kind classes

```turtle-spec
srf:ProjectionKind a owl:Class .
srf:ProjectionRole a owl:Class .
srf:CompilerBackend a owl:Class .
srf:LLMCompletionPolicy a owl:Class .
```

### 6.14 Projection properties

```turtle-spec
srf:projectionKind a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:ProjectionContract ; rdfs:range srf:ProjectionKind ;
	rdfs:comment "The mapping-intent kind a projection contract declares." .

srf:hasRoleBinding a owl:ObjectProperty ;
	rdfs:domain srf:ProjectionContract ; rdfs:range srf:ProjectionRoleBinding ;
	rdfs:comment "A named role a projection contract binds to a property or carrier." .

srf:roleKind a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:ProjectionRoleBinding ; rdfs:range srf:ProjectionRole ;
	rdfs:comment "Which role a projection role binding fills." .

srf:bindsProperty a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:ProjectionRoleBinding ; rdfs:range rdf:Property ;
	rdfs:comment "The property a projection role binding names for its role." .

srf:bindsCarrier a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:ProjectionRoleBinding ; rdfs:range rdfs:Class ;
	rdfs:comment "The class a role's evidence is drawn from, where it differs from the contract's own carrier." ;
	fnd:utility "Set this for a join or a required-evidence role that reaches a second carrier; leave it unset where the role reads the contract's own carrier." .

srf:backendPolicy a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:ProjectionContract ; rdfs:range srf:ProjectionBackendPolicy ;
	rdfs:comment "The backend-eligibility and LLM-participation policy a projection contract lowers under." .

srf:allowedBackend a owl:ObjectProperty ;
	rdfs:domain srf:ProjectionBackendPolicy ; rdfs:range srf:CompilerBackend ;
	rdfs:comment "A compiler backend a lowered mapping may target." .

srf:deniedBackend a owl:ObjectProperty ;
	rdfs:domain srf:ProjectionBackendPolicy ; rdfs:range srf:CompilerBackend ;
	rdfs:comment "A compiler backend a lowered mapping may not target." .

srf:llmCompletionPolicy a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:ProjectionBackendPolicy ; rdfs:range srf:LLMCompletionPolicy ;
	rdfs:comment "What an LLM may propose during lowering, where deterministicOnly is false." .

srf:deterministicOnly a owl:DatatypeProperty, owl:FunctionalProperty ;
	rdfs:domain srf:ProjectionBackendPolicy ; rdfs:range xsd:boolean ;
	rdfs:comment "Whether lowering under this policy may invoke an LLM at all." ;
	fnd:utility "True forbids LLM participation outright, the recommended default for production. False defers to llmCompletionPolicy." .

srf:approvedTemplate a owl:DatatypeProperty ;
	rdfs:domain srf:ProjectionBackendPolicy ; rdfs:range xsd:string ;
	rdfs:comment "The identifier of a mapping template a bounded LLM completion may draw from." .

srf:producesMapping a owl:ObjectProperty ;
	rdfs:domain [ a owl:Class ; owl:unionOf ( srf:GeneratedSurface srf:ProjectionContract ) ] ;
	rdfs:comment "A MORK mapping node a projection's lowering produced, which is how a lowered scheme or mapping names its contract." ;
	fnd:utility "Written by the lowering from a ProjectionContract to the node that stands for it, the root of a scheme or a bare mapping. A generated surface covering a ProjectionContract may name its mapping the same way. Names a mork:DataMapping, mork:ShapeMapping, mork:RuleMapping, mork:QueryTemplate, or mork:ProjectionMapping by punning, without Surface importing MORK." .
```

### 6.15 Projection expressions

A derivation projection states the operation it performs as an expression, in a closed vocabulary, so the contract carries the meaning of the derivation and no backend has to supply it. The expression is stated on the result-target role binding with `srf:derivedAs`, and its operands are the contract's evidence role bindings and expressions of their own. The vocabulary is the four arithmetic operations, a literal of a stated datatype, rounding to a stated scale, and a choice between two values on a comparison of two operands. Each node and each evidence role binding an expression reads states its datatype, so a shape refuses an untyped operand, a non-numeric operand of arithmetic or an ordering comparison, and branches of a choice that disagree. A node is named by an IRI, never a blank node, so the expression has a canonical form.

#### `srf:ProjectionExpression`

**Definition.** A node of the expression a derivation projection states over its evidence role bindings. It is one of a closed set of operations, and states the datatype of the value it computes.

**Utility.** State the operation a derivation performs here, never in a backend's text. Give every node a `srf:resultDatatype` and every evidence role binding an operand reads a `srf:bindsDatatype`, since a shape checks each node against its direct operands only.

```turtle-spec
srf:ProjectionExpression a owl:Class ;
	rdfs:subClassOf
		[ a owl:Restriction ; owl:onProperty srf:resultDatatype ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "A node of the expression a derivation projection states over its evidence role bindings. It is one of a closed set of operations, and states the datatype of the value it computes." ;
	fnd:utility "State the operation a derivation performs here, never in a backend's text. Give every node a resultDatatype and every evidence role binding an operand reads a bindsDatatype, since a shape checks each node against its direct operands only." .

srf:ArithmeticExpression a owl:Class ;
	rdfs:subClassOf srf:ProjectionExpression ,
		[ a owl:Restriction ; owl:onProperty srf:leftOperand ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:rightOperand ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "An operation on two numeric operands, taken in order." .

srf:SumExpression a owl:Class ;
	rdfs:subClassOf srf:ArithmeticExpression ;
	rdfs:comment "The sum of its left and right operands." .

srf:DifferenceExpression a owl:Class ;
	rdfs:subClassOf srf:ArithmeticExpression ;
	rdfs:comment "The left operand less the right operand." .

srf:ProductExpression a owl:Class ;
	rdfs:subClassOf srf:ArithmeticExpression ;
	rdfs:comment "The product of its left and right operands." .

srf:QuotientExpression a owl:Class ;
	rdfs:subClassOf srf:ArithmeticExpression ;
	rdfs:comment "The left operand divided by the right operand. A quotient is at least decimal, whatever its operands, and is undefined where the right operand is zero." .

srf:TypedLiteralExpression a owl:Class ;
	rdfs:subClassOf srf:ProjectionExpression ,
		[ a owl:Restriction ; owl:onProperty srf:typedValue ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "A constant, written as a literal of the datatype the expression states." .

srf:RoundingExpression a owl:Class ;
	rdfs:subClassOf srf:ProjectionExpression ,
		[ a owl:Restriction ; owl:onProperty srf:roundedOperand ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:roundingScale ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "Its operand rounded to the nearest multiple of ten to the power of minus the scale, a tie going toward positive infinity, as SPARQL's ROUND does. This is the one rounding mode, so -2.5 rounds to -2 and 2.5 to 3. Other modes, such as half-even, are added when a contract needs one. A scale of 2 rounds to hundredths and a scale of -2 to hundreds." .

srf:ChoiceExpression a owl:Class ;
	rdfs:subClassOf srf:ProjectionExpression ,
		[ a owl:Restriction ; owl:onProperty srf:comparisonOperator ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:comparedLeft ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:comparedRight ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:whenTrue ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:whenFalse ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "The value of its true branch where its left compared operand stands in its comparison to its right compared operand, and the value of its false branch otherwise." .

srf:ComparisonOperator a owl:Class ;
	rdfs:comment "How a choice compares its two operands. Its individuals are in the vocabulary." .

[ a owl:AllDisjointClasses ; owl:members (
	srf:SumExpression srf:DifferenceExpression srf:ProductExpression srf:QuotientExpression
	srf:TypedLiteralExpression srf:RoundingExpression srf:ChoiceExpression ) ] .
```

Each operand is another expression, or a role binding of the same contract that reads evidence (`srf:RequiredEvidenceRole` or `srf:CandidateEvidenceRole`) and binds a property. A binding as an operand stands for the value of its property on the carrier instance.

```turtle-spec
srf:derivedAs a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:ProjectionRoleBinding ; rdfs:range srf:ProjectionExpression ;
	rdfs:comment "The expression a derivation projection states over its evidence role bindings." ;
	fnd:utility "Set it on the result-target role binding of a derivation projection, once, and nowhere else (srf:P6). The value written on the carrier is the value of the expression." .

srf:bindsDatatype a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:ProjectionRoleBinding ; rdfs:range rdfs:Datatype ;
	rdfs:comment "The datatype of the value the bound property carries, as an expression reads it." ;
	fnd:utility "State it on each evidence role binding an expression reads and on the result-target role binding, where it is the datatype of the expression's value. It restates the range of the property the contract binds, which the contract graph may not hold, so that a shape can check the contract alone (srf:P8)." .

srf:resultDatatype a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:ProjectionExpression ; rdfs:range rdfs:Datatype ;
	rdfs:comment "The datatype of the value an expression computes." ;
	fnd:utility "Numeric promotion gives it for arithmetic (srf:P8). Write xsd:integer, xsd:decimal, xsd:float or xsd:double for a numeric value." .

srf:leftOperand a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:ArithmeticExpression ;
	rdfs:comment "The first operand of an arithmetic expression, an expression or an evidence role binding of the same contract." .

srf:rightOperand a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:ArithmeticExpression ;
	rdfs:comment "The second operand of an arithmetic expression, an expression or an evidence role binding of the same contract." .

srf:typedValue a owl:DatatypeProperty, owl:FunctionalProperty ;
	rdfs:domain srf:TypedLiteralExpression ; rdfs:range rdfs:Literal ;
	rdfs:comment "The constant of a typed literal expression. Its datatype is the expression's result datatype." .

srf:roundedOperand a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:RoundingExpression ;
	rdfs:comment "The operand a rounding expression rounds, an expression or an evidence role binding of the same contract." .

srf:roundingScale a owl:DatatypeProperty, owl:FunctionalProperty ;
	rdfs:domain srf:RoundingExpression ; rdfs:range xsd:integer ;
	rdfs:comment "The number of places a rounding expression keeps after the decimal point. It may be negative." .

srf:comparisonOperator a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:ChoiceExpression ; rdfs:range srf:ComparisonOperator ;
	rdfs:comment "How a choice compares its compared operands." .

srf:comparedLeft a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:ChoiceExpression ;
	rdfs:comment "The left operand of the comparison a choice makes, an expression or an evidence role binding of the same contract." .

srf:comparedRight a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:ChoiceExpression ;
	rdfs:comment "The right operand of the comparison a choice makes, an expression or an evidence role binding of the same contract." .

srf:whenTrue a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:ChoiceExpression ;
	rdfs:comment "The value a choice takes where its comparison holds, an expression or an evidence role binding of the same contract." .

srf:whenFalse a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:ChoiceExpression ;
	rdfs:comment "The value a choice takes where its comparison does not hold, an expression or an evidence role binding of the same contract." .
```

### 6.16 Projection constructions

A graph construction projection states the node it writes, in the way a derivation states its expression. The statement is on the result-target role binding with `srf:constructedAs`, so the binding keeps its one meaning, the place the projection's result is written, and the result of a graph construction is a node where a derivation's is a value. The binding binds the link from each instance to the node. The constructed node states its class, its identity, and each value it writes from an evidence binding of the same contract. The identity is a closed choice, a node for each instance or a node for each value of a key, so two instances are never merged by an author's silence.

#### `srf:ConstructedNode`

**Definition.** The node a graph construction projection writes for an instance of its carrier, with the class it is typed with, its identity and the values it carries.

**Utility.** State it once, on the result-target role binding of a graph construction with `srf:constructedAs`, and name it by an IRI. Give it one `srf:constructedClass`, one `srf:nodeIdentity`, a `srf:keyBinding` for each part of its key where its identity is `srf:ByKey`, and a `srf:writes` for each value it carries, at least one. The class a constructed node is typed with decides the projection's signature scope (`srf:P1`).

```turtle-spec
srf:ConstructedNode a owl:Class ;
	rdfs:subClassOf
		[ a owl:Restriction ; owl:onProperty srf:constructedClass ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:nodeIdentity ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:writes ; owl:minCardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "The node a graph construction projection writes for an instance of its carrier, with the class it is typed with, its identity and the values it carries." ;
	fnd:utility "State it once, on the result-target role binding of a graph construction with constructedAs, and name it by an IRI. Give it one constructedClass, one nodeIdentity, a keyBinding for each part of its key where its identity is ByKey, and a writes for each value it carries, at least one. The class it is typed with decides the projection's signature scope (srf:P1)." .

srf:WrittenValue a owl:Class ;
	rdfs:subClassOf
		[ a owl:Restriction ; owl:onProperty srf:writesProperty ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ,
		[ a owl:Restriction ; owl:onProperty srf:fromBinding ; owl:cardinality "1"^^xsd:nonNegativeInteger ] ;
	rdfs:comment "One value a constructed node carries, the property it is written as and the evidence role binding it is read from." ;
	fnd:utility "Name each written value by a blank node or an IRI, as srf:writes takes it. A node writes each property once." .

srf:IdentityChoice a owl:Class ;
	rdfs:comment "What makes two constructed nodes the same node. Its individuals are in the vocabulary." .
```

```turtle-spec
srf:constructedAs a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:ProjectionRoleBinding ; rdfs:range srf:ConstructedNode ;
	rdfs:comment "The node a graph construction projection writes, stated on its result-target role binding, which binds the link from each instance to it." ;
	fnd:utility "Set it on the result-target role binding of a graph construction, once, and nowhere else (srf:P10). The property that binding binds is the link from the instance to the node." .

srf:constructedClass a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:ConstructedNode ; rdfs:range rdfs:Class ;
	rdfs:comment "The class a constructed node is typed with." ;
	fnd:utility "A class an authored vocabulary declares puts the projection in the authored signature, and a class minted in the contract's target namespace in its own (srf:P1)." .

srf:nodeIdentity a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:ConstructedNode ; rdfs:range srf:IdentityChoice ;
	rdfs:comment "Whether a constructed node is made for each instance of the carrier or for each value of a key." ;
	fnd:utility "State it, never leave it implicit. PerInstance gives each instance its own node, which merges nothing. ByKey merges the instances that share the values of the key bindings, which takes a mapping review (ADR-A41) and brings a run-time check for a node whose instances disagree on a value." .

srf:keyBinding a owl:ObjectProperty ;
	rdfs:domain srf:ConstructedNode ; rdfs:range srf:ProjectionRoleBinding ;
	rdfs:comment "A required-evidence role binding whose value is part of the key a keyed constructed node is made for." ;
	fnd:utility "Name one for each part of the key, and none for a node for each instance (srf:P11). A key binding is required evidence (srf:P13), so an instance without a value for it contributes nothing. The key is spelled into the node's identifier, so a key that may be personal or may change is no key." .

srf:writes a owl:ObjectProperty ;
	rdfs:domain srf:ConstructedNode ; rdfs:range srf:WrittenValue ;
	rdfs:comment "A value a constructed node carries." .

srf:writesProperty a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:WrittenValue ; rdfs:range rdf:Property ;
	rdfs:comment "The property a written value is written as on the constructed node." .

srf:fromBinding a owl:ObjectProperty, owl:FunctionalProperty ;
	rdfs:domain srf:WrittenValue ; rdfs:range srf:ProjectionRoleBinding ;
	rdfs:comment "The candidate-evidence or required-evidence role binding of the same contract a written value is read from." ;
	fnd:utility "A required-evidence binding gates the node, since an instance without it contributes nothing. A candidate-evidence binding writes what it finds (srf:P12)." .
```

## 7. Index forms

| Form | Emits | Needs an enumerable population | Retrieval | Entailment required |
|---|---|---|---|---|
| `srf:NominalClass` | `σ(v) ≡ Carrier ⊓ ∃R.{v}` | yes | `?x a σ(v)` | yes, unless paired with `MembershipAssertion` |
| `srf:MembershipAssertion` | `x rdf:type σ(v)` | yes | `?x a σ(v)` | no |
| `srf:ClosureRelation` | `x match ancestor` for every ancestor of the asserted value | no | `?x match ?a` | no |
| `srf:DirectProperty` | `x p v` for the read path's value | **no** | `?x p ?v` | no |
| `srf:ExternalIndex` | store-native | n/a | n/a | n/a |

`srf:DirectProperty` is the form that carries unbounded value spaces and long read paths, and it is what a promotion contract emits. `srf:ExternalIndex` is declared and rejected by this release's constraints, so that its absence is visible rather than silent.

Wildcard or "any" members of a population are minted on the same terms as every other member. Admitting everything is a matching-semantics question, decided where the match is evaluated, and building it into the index would make the surface non-conservative.

## 8. Naming and determinism

A contract with key `k`, target namespace `N`, and carrier local name `C`, under normalisation `f`, mints:

| Term | Identifier |
|---|---|
| family class | `N` + `f(C)` + `_` + `f(k)` |
| nominal class for value `v` | family class + `_` + `local(v)` under `LocalNameFromValue`, family class + `_` + prefix + `_` + `local(v)` under `QualifiedLocalName`, family class + `_` + digest(`v`) under `DigestLocalName` |
| closure relation | `N` + `matches_` + `f(k)` |
| surface record | `N` + `surface_` + `f(k)` |
| symbol record (wrapper mode only) | minted term + `_symbol` |

`local(v)` is the fragment after `#`, or after the final `/` where there is no fragment. A promoted property is declared by the contract and is never minted.

Injectivity is not assumed. `LocalNameFromValue` is injective only while value local names are unique across the population, which stops being true as soon as two schemes bind one dimension or two namespaces share a local name. A collision is a hard failure, not a warning, and `DigestLocalName` is the escape hatch.

## 9. Mechanism Vocabulary

```turtle-vocab
@prefix srf:  <https://www.nebularis.org/neuro-semantic/lattice/surface#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@base <https://www.nebularis.org/neuro-semantic/surface-vocab> .

<https://www.nebularis.org/neuro-semantic/surface-vocab>
	a owl:Ontology ;
	owl:versionIRI <https://www.nebularis.org/neuro-semantic/lattice/surface-vocab/0.21.1> ;
	owl:imports <https://www.nebularis.org/neuro-semantic/lattice/surface/0.21.1> .

srf:NominalClass a srf:IndexForm ; rdfs:comment "One generated class per value, defined as the carrier restricted to that value." .
srf:MembershipAssertion a srf:IndexForm ; rdfs:comment "Asserted typing of each carrier instance into the generated class for its value." .
srf:ClosureRelation a srf:IndexForm ; rdfs:comment "One generated relation carrying each carrier instance to every ancestor of its value under the declared basis." .
srf:DirectProperty a srf:IndexForm ; rdfs:comment "One generated property carrying each carrier instance to the value at the end of its read path." .
srf:ExternalIndex a srf:IndexForm ; rdfs:comment "A store-native index outside the RDF surface. Declared and not yet permitted." .

srf:DefinitionOnly a srf:RealisationMode ; rdfs:comment "Emit definitions and axioms only; evaluation depends on the profile's declared entailment regime." .
srf:Materialised a srf:RealisationMode ; rdfs:comment "Emit asserted triples only; evaluation requires no entailment." .
srf:DefinitionAndMaterialised a srf:RealisationMode ; rdfs:comment "Emit both definitions and the assertions they would entail." .

srf:LocalNameFromValue a srf:NamingPolicy ; rdfs:comment "Mint from the value's own local name." .
srf:QualifiedLocalName a srf:NamingPolicy ; rdfs:comment "Mint from the value's local name preceded by the contract's declared naming prefix." .
srf:DigestLocalName a srf:NamingPolicy ; rdfs:comment "Mint from a digest of the value's identifier. Injective for any population." .

srf:VerbatimLocalName a srf:NamingNormalisation ; rdfs:comment "Use identifier fragments unchanged." .
srf:SanitisedLocalName a srf:NamingNormalisation ; rdfs:comment "Replace each character outside the unreserved identifier set with a single underscore." .

srf:ExactSource a srf:SourceFidelity ; rdfs:comment "The promoted value is the source value, reached by traversal alone." .
srf:DerivedSource a srf:SourceFidelity ; rdfs:comment "The promoted value is computed from source values and is not one of them." .
srf:CrosswalkExact a srf:SourceFidelity ; rdfs:comment "The promoted value is reached through a mapping relation asserting exact correspondence." .
srf:CrosswalkInexact a srf:SourceFidelity ; rdfs:comment "The promoted value is reached through a mapping relation weaker than exact correspondence." .

srf:NamedIndividuals a srf:ExtentKind ; rdfs:comment "The named individuals asserted to be instances of the class." .
srf:DirectSubClasses a srf:ExtentKind ; rdfs:comment "The immediate subclasses of the class." .
srf:TransitiveSubClasses a srf:ExtentKind ; rdfs:comment "The transitive subclasses of the class." .

srf:Forward a srf:StepDirection ; rdfs:comment "Traversed from subject to object." .
srf:Inverse a srf:StepDirection ; rdfs:comment "Traversed from object to subject." .

srf:NoEntailment a srf:EntailmentRegime ; rdfs:comment "Asserted triples only." .
srf:RDFSEntailment a srf:EntailmentRegime ; rdfs:comment "RDFS entailment." .
srf:OWL2ELEntailment a srf:EntailmentRegime ; rdfs:comment "OWL 2 EL entailment." .
srf:OWL2DLEntailment a srf:EntailmentRegime ; rdfs:comment "OWL 2 DL entailment." .

srf:PunnedSymbols a srf:SymbolMode ; rdfs:comment "The symbol record and the minted term share one identifier." .
srf:WrappedSymbols a srf:SymbolMode ; rdfs:comment "The symbol record is a separate individual pointing at the minted term." .

srf:DeclarationSource a srf:ReadSourceKind ; rdfs:comment "An authored declaration graph." .
srf:BoundSchemeSource a srf:ReadSourceKind ; rdfs:comment "A concept scheme bound to a scheme contract." .
srf:InstanceGraphSource a srf:ReadSourceKind ; rdfs:comment "A graph of carrier instances." .
srf:SurfaceSource a srf:ReadSourceKind ; rdfs:comment "Another generated surface." .

srf:LocalSignature a srf:SignatureScope ; rdfs:comment "Every term the surface asserts about is one it minted itself." .
srf:SourceSignature a srf:SignatureScope ; rdfs:comment "The surface asserts over a property an authored layer declares." .

srf:Advisory a srf:DerivationAuthority ; rdfs:comment "Informative; never authoritative on its own." .
srf:CachedReproducible a srf:DerivationAuthority ; rdfs:comment "Authoritative only because it is provably reproducible from its source." .

srf:GraphConstructionProjection a srf:ProjectionKind ; rdfs:comment "Mapping intent that constructs new graph structure not present as a single reachable value." .
srf:DerivationProjection a srf:ProjectionKind ; rdfs:comment "Mapping intent that computes a value from one or more source values." .
srf:JoinProjection a srf:ProjectionKind ; rdfs:comment "Mapping intent that combines evidence from more than one carrier." .
srf:ExpansionProjection a srf:ProjectionKind ; rdfs:comment "Mapping intent that restates one relation as several." .

srf:EvaluationSubjectRole a srf:ProjectionRole ; rdfs:comment "The carrier instance a projection is evaluated for." .
srf:CandidateEvidenceRole a srf:ProjectionRole ; rdfs:comment "A value offered as evidence toward the projection's result." .
srf:RequiredEvidenceRole a srf:ProjectionRole ; rdfs:comment "A value a projection's result cannot be computed without." .
srf:ResultTargetRole a srf:ProjectionRole ; rdfs:comment "Where a projection's computed result is written." .
srf:ClosureBasisRole a srf:ProjectionRole ; rdfs:comment "The relation a projection's closure, where it has one, is computed over." .
srf:TransformDependencyRole a srf:ProjectionRole ; rdfs:comment "A dependency a derivation reads without itself being required or candidate evidence." .

srf:LessThan a srf:ComparisonOperator ; rdfs:comment "The left compared operand is less than the right." .
srf:LessThanOrEqual a srf:ComparisonOperator ; rdfs:comment "The left compared operand is less than or equal to the right." .
srf:EqualTo a srf:ComparisonOperator ; rdfs:comment "The two compared operands are equal." .
srf:NotEqualTo a srf:ComparisonOperator ; rdfs:comment "The two compared operands are not equal." .
srf:GreaterThanOrEqual a srf:ComparisonOperator ; rdfs:comment "The left compared operand is greater than or equal to the right." .
srf:GreaterThan a srf:ComparisonOperator ; rdfs:comment "The left compared operand is greater than the right." .

srf:PerInstance a srf:IdentityChoice ; rdfs:comment "A constructed node for each instance of the carrier. Nothing is merged, and the node's identifier is a hash of the instance's identifier." .
srf:ByKey a srf:IdentityChoice ; rdfs:comment "One constructed node for each value of a key of required-evidence bindings. Instances that share the key share the node, and its identifier is read from the key." .

srf:RmlBackend a srf:CompilerBackend ; rdfs:comment "RML/R2RML triples-map compilation." .
srf:SparqlBackend a srf:CompilerBackend ; rdfs:comment "SPARQL query compilation." .
srf:ShaclBackend a srf:CompilerBackend ; rdfs:comment "SHACL shape compilation." .
srf:SwrlBackend a srf:CompilerBackend ; rdfs:comment "SWRL rule compilation." .
srf:NativeIrBackend a srf:CompilerBackend ; rdfs:comment "Native execution intermediate representation compilation." .

srf:NoLLMCompletion a srf:LLMCompletionPolicy ; rdfs:comment "No LLM participation in lowering." .
srf:BoundedLLMCompletion a srf:LLMCompletionPolicy ; rdfs:comment "An LLM may complete only declared gaps using an approved template, and every completion requires governance state before production use." .

srf:SemanticLaw a srf:LawRegister ; rdfs:comment "Discharged by formal argument and property tests." .
srf:StaticConstraint a srf:LawRegister ; rdfs:comment "Discharged by SPARQL, SHACL, reasoner, or compiled static analysis." .
srf:RuntimeConformance a srf:LawRegister ; rdfs:comment "Discharged only by an executed run." .

srf:X1 a srf:Law ; srf:lawRegister srf:SemanticLaw ; rdfs:comment "Conservativity. For a source graph G and a local-signature surface S generated from it, G union S entails a statement over the source signature exactly when G does. Composition: a stacked surface's signature scope is source-signature if any surface in its read set is source-signature, and conservativity composes accordingly." .
srf:X2 a srf:Law ; srf:lawRegister srf:SemanticLaw ; rdfs:comment "Index faithfulness. A carrier instance belongs to the generated class for a value exactly when the read path relates it to that value under the profile's declared entailment regime." .
srf:X3 a srf:Law ; srf:lawRegister srf:SemanticLaw ; rdfs:comment "Closure soundness and completeness. A generated closure relation holds between a carrier instance and a value exactly when the read path relates that instance to some value standing in the reflexive-transitive closure of the declared basis, restricted to the declared scope." .
srf:X4 a srf:Law ; srf:lawRegister srf:SemanticLaw ; rdfs:comment "Wildcard non-collapse. A wildcard member of a population mints a symbol on the same terms as any other member and carries no admits-everything semantics." .
srf:X5 a srf:Law ; srf:lawRegister srf:SemanticLaw ; rdfs:comment "Promotion fidelity. A promotion declaring exact or crosswalk-exact fidelity preserves the meaning of the value it restates; a promotion declaring derived or crosswalk-inexact fidelity does not, and caps its surface at advisory authority." .

srf:X6 a srf:Law ; srf:lawRegister srf:SemanticLaw ; rdfs:comment "Promotion signature discipline. A promotion onto a property outside the contract's target namespace reaches the authored signature: it declares exact or crosswalk-exact fidelity, and it is materialised rather than definitional." .

srf:S1 a srf:Law ; srf:lawRegister srf:StaticConstraint ; rdfs:comment "Every surface contract declares a carrier, a contract key, a target namespace, a realisation mode, a profile, and exactly one read-path form." .
srf:S2 a srf:Law ; srf:lawRegister srf:StaticConstraint ; rdfs:comment "A contract-bound population names a scheme contract with a bound scheme holding a required governance state." .
srf:S3 a srf:Law ; srf:lawRegister srf:StaticConstraint ; rdfs:comment "A closure basis is declared exactly when a closure-relation index form is declared." .
srf:S4 a srf:Law ; srf:lawRegister srf:StaticConstraint ; rdfs:comment "An index form minting one symbol per value declares an enumerable population." .
srf:S5 a srf:Law ; srf:lawRegister srf:StaticConstraint ; rdfs:comment "Every population member has exactly one symbol per declared index form." .
srf:S6 a srf:Law ; srf:lawRegister srf:StaticConstraint ; rdfs:comment "No two population members mint the same identifier." .
srf:S7 a srf:Law ; srf:lawRegister srf:StaticConstraint ; rdfs:comment "Every minted term has a symbol record naming its value, contract, and profile." .
srf:S8 a srf:Law ; srf:lawRegister srf:StaticConstraint ; rdfs:comment "Generated content occupies projection and execution graph roles only." .
srf:S9 a srf:Law ; srf:lawRegister srf:StaticConstraint ; rdfs:comment "No generated surface declares an authority above cached-reproducible." .
srf:S10 a srf:Law ; srf:lawRegister srf:StaticConstraint ; rdfs:comment "A generated surface's stack depth does not exceed its profile's permitted stack depth." .

srf:R1 a srf:Law ; srf:lawRegister srf:RuntimeConformance ; rdfs:comment "Regeneration determinism. The same read set under the same profile yields an identical symbol inventory and an identical artefact hash. Composition: every surface in a stack shares one profile identity, checked statically; a mixed-profile stack is not a conformant regeneration. For a contract-bound population that could resolve a caller-scoped voc:SchemeBinding (ADR-A85), the resolution instant is part of that read set as a required, explicit input, not an incidental reuse of the production timestamp: the law holds relative to a fixed resolution instant, and the compiler refuses to supply one implicitly for such a population." .
srf:R2 a srf:Law ; srf:lawRegister srf:RuntimeConformance ; rdfs:comment "Surface and source parity. Every question in the shared conformance corpus is answered identically against the surface and against the source under a direct evaluation profile." .
srf:R3 a srf:Law ; srf:lawRegister srf:RuntimeConformance ; rdfs:comment "Invalidation minimality. A scoped change regenerates only the computed impact set and leaves every other surface byte-identical." .
srf:R4 a srf:Law ; srf:lawRegister srf:RuntimeConformance ; rdfs:comment "Materialisation idempotence. Re-running a materialisation over an unchanged read set adds no triples." .
srf:R5 a srf:Law ; srf:lawRegister srf:RuntimeConformance ; rdfs:comment "Closure well-foundedness. The declared closure basis is acyclic over the declared scope, established by traversing it." .

srf:P1 a srf:Law ; srf:lawRegister srf:SemanticLaw ; rdfs:comment "Projection conservativity. A local-signature projection is conservative on the same terms as an index; a source-signature projection composes under the same rule as X1 and X6. A graph construction reads its scope from the class of its constructed node: a class minted in the contract's own target namespace is local-signature, and a class an authored vocabulary declares reaches the authored signature, so the nodes it writes and the values on them are indistinguishable from authored facts once emitted and the projection is source-signature." .
srf:P2 a srf:Law ; srf:lawRegister srf:StaticConstraint ; rdfs:comment "Every projection contract declares exactly one projection kind and at least an evaluation-subject and a result-target role binding; a join or derivation kind additionally declares at least one candidate-evidence or required-evidence role binding." .
srf:P3 a srf:Law ; srf:lawRegister srf:StaticConstraint ; rdfs:comment "A projection contract declares at most one evaluation-subject, result-target, and closure-basis role binding; candidate-evidence, required-evidence, and transform-dependency role bindings may repeat." .
srf:P4 a srf:Law ; srf:lawRegister srf:StaticConstraint ; rdfs:comment "A backend policy names no compiler backend in both allowedBackend and deniedBackend." .
srf:P5 a srf:Law ; srf:lawRegister srf:StaticConstraint ; rdfs:comment "A backend policy declaring deterministicOnly true declares no llmCompletionPolicy other than NoLLMCompletion." .

srf:P6 a srf:Law ; srf:lawRegister srf:StaticConstraint ; rdfs:comment "A derivation projection states exactly one expression, with derivedAs on its result-target role binding, and that binding binds the property the value is written on. No other projection kind states an expression. Every expression node is reached from such a statement through its operands." .
srf:P7 a srf:Law ; srf:lawRegister srf:StaticConstraint ; rdfs:comment "Each operand of a projection expression is a projection expression, or a candidate-evidence or required-evidence role binding of the same contract that binds a property." .
srf:P8 a srf:Law ; srf:lawRegister srf:StaticConstraint ; rdfs:comment "Each projection expression states a result datatype, and each evidence role binding an expression reads and the result-target role binding state a binding datatype. The operands of an arithmetic expression, a rounding expression and an ordering comparison are numeric. A node's result datatype is the wider of its operands' under numeric promotion (a quotient is at least decimal), the datatype of its operand under rounding, and the datatype of both branches of a choice. The result-target role binding's datatype is the expression's." .
srf:P9 a srf:Law ; srf:lawRegister srf:StaticConstraint ; rdfs:comment "A projection expression is acyclic. No expression is an operand of itself, directly or through other expressions." .

srf:P10 a srf:Law ; srf:lawRegister srf:StaticConstraint ; rdfs:comment "A graph construction projection states exactly one constructed node, with constructedAs on its result-target role binding, and that binding binds the property that links each instance to the node. No other projection kind states a construction. Every constructed node is reached from such a statement." .
srf:P11 a srf:Law ; srf:lawRegister srf:StaticConstraint ; rdfs:comment "A constructed node states exactly one class and exactly one identity, a node for each instance or a node for each value of a key. It writes at least one value and writes each property at most once. It names key bindings exactly when its identity is by key." .
srf:P12 a srf:Law ; srf:lawRegister srf:StaticConstraint ; rdfs:comment "Each value a constructed node writes states exactly one property and names exactly one candidate-evidence or required-evidence role binding of the same contract that binds a property." .
srf:P13 a srf:Law ; srf:lawRegister srf:StaticConstraint ; rdfs:comment "A key binding of a constructed node is a required-evidence role binding of the same contract that binds a property, so an instance without a value for any part of the key contributes nothing." .
```

## 10. Shapes

Contract-local and record-local checks are shipped here. Checks that need a source declaration and its generated surface in view at once belong to `ontology/governance/parity/`, which runs over the union graph.

```turtle-shapes
@prefix sh:   <http://www.w3.org/ns/shacl#> .
@prefix srf:  <https://www.nebularis.org/neuro-semantic/lattice/surface#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

srf:SurfaceContractShape a sh:NodeShape ;
	sh:targetClass srf:SurfaceContract ;
	sh:property [ sh:path srf:carrier ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:contractKey ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:targetNamespace ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:realisationMode ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:surfaceProfile ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:readProperty ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:populationBudget ; sh:maxCount 1 ] .

srf:PromotionContractShape a sh:NodeShape ;
	sh:targetClass srf:PromotionContract ;
	sh:property [ sh:path srf:promotesTo ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:sourceFidelity ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:viaMatchRelation ; sh:maxCount 1 ] .

srf:IndexContractShape a sh:NodeShape ;
	sh:targetClass srf:IndexContract ;
	sh:property [ sh:path srf:valuePopulation ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:indexForm ; sh:minCount 1 ] ;
	sh:property [ sh:path srf:namingPolicy ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:closureBasis ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:closureScope ; sh:maxCount 1 ] .

srf:PathStepShape a sh:NodeShape ;
	sh:targetClass srf:PathStep ;
	sh:property [ sh:path srf:stepIndex ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:stepProperty ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:stepDirection ; sh:minCount 1 ; sh:maxCount 1 ] .

srf:SurfaceProfileShape a sh:NodeShape ;
	sh:targetClass srf:SurfaceProfile ;
	sh:property [ sh:path srf:generatorVersion ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:canonicalisationVersion ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:entailmentRegime ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:namingNormalisation ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:symbolMode ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:permittedStackDepth ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:defaultPopulationBudget ; sh:maxCount 1 ] .

srf:GeneratedSurfaceShape a sh:NodeShape ;
	sh:targetClass srf:GeneratedSurface ;
	sh:property [ sh:path srf:coversContract ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:generatedByProfile ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:derivationAuthority ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:producedAt ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:hasReadSetEntry ; sh:minCount 1 ] ;
	sh:property [ sh:path srf:stackDepth ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:signatureScope ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:artefactHash ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:semanticContentHash ; sh:maxCount 1 ] .

srf:GeneratedSymbolShape a sh:NodeShape ;
	sh:targetClass srf:GeneratedSymbol ;
	sh:property [ sh:path srf:inSurface ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:symbolForm ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:denotes ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:fromValue ; sh:maxCount 1 ] .

srf:ReadSetEntryShape a sh:NodeShape ;
	sh:targetClass srf:ReadSetEntry ;
	sh:property [ sh:path srf:readsSource ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:readSourceKind ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:readHash ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:readVersion ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:resolvedAt ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:resolvedBinding ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:resolvedViaFallback ; sh:maxCount 1 ] .

srf:SymbolCountShape a sh:NodeShape ;
	sh:targetClass srf:SymbolCount ;
	sh:property [ sh:path srf:countForm ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:countValue ; sh:minCount 1 ; sh:maxCount 1 ] .

srf:LawDischargeShape a sh:NodeShape ;
	sh:targetClass srf:LawDischarge ;
	sh:property [ sh:path srf:dischargesLaw ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:dischargedForSurface ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:dischargedAt ; sh:minCount 1 ; sh:maxCount 1 ] .

srf:ProjectionContractShape a sh:NodeShape ;
	sh:targetClass srf:ProjectionContract ;
	sh:property [ sh:path srf:projectionKind ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:hasRoleBinding ; sh:minCount 1 ] ;
	sh:property [ sh:path srf:backendPolicy ; sh:maxCount 1 ] .

srf:ProjectionRoleBindingShape a sh:NodeShape ;
	sh:targetClass srf:ProjectionRoleBinding ;
	sh:property [ sh:path srf:roleKind ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:bindsProperty ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:bindsCarrier ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:bindsDatatype ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:derivedAs ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:constructedAs ; sh:maxCount 1 ] .

srf:ProjectionBackendPolicyShape a sh:NodeShape ;
	sh:targetClass srf:ProjectionBackendPolicy ;
	sh:property [ sh:path srf:llmCompletionPolicy ; sh:minCount 1 ; sh:maxCount 1 ] ;
	sh:property [ sh:path srf:deterministicOnly ; sh:minCount 1 ; sh:maxCount 1 ] .

srf:ProjectionExpressionShape a sh:NodeShape ;
	sh:targetClass srf:SumExpression , srf:DifferenceExpression , srf:ProductExpression , srf:QuotientExpression ,
		srf:TypedLiteralExpression , srf:RoundingExpression , srf:ChoiceExpression ;
	sh:property [ sh:path srf:resultDatatype ; sh:minCount 1 ; sh:maxCount 1 ; sh:nodeKind sh:IRI ;
		sh:message "A projection expression states exactly one result datatype. Discharges srf:P8." ] .

srf:ArithmeticExpressionShape a sh:NodeShape ;
	sh:targetClass srf:SumExpression , srf:DifferenceExpression , srf:ProductExpression , srf:QuotientExpression ;
	sh:property [ sh:path srf:leftOperand ; sh:minCount 1 ; sh:maxCount 1 ;
		sh:message "An arithmetic expression has exactly one left operand. Discharges srf:P7." ] ;
	sh:property [ sh:path srf:rightOperand ; sh:minCount 1 ; sh:maxCount 1 ;
		sh:message "An arithmetic expression has exactly one right operand. Discharges srf:P7." ] .

srf:TypedLiteralExpressionShape a sh:NodeShape ;
	sh:targetClass srf:TypedLiteralExpression ;
	sh:property [ sh:path srf:typedValue ; sh:minCount 1 ; sh:maxCount 1 ; sh:nodeKind sh:Literal ;
		sh:message "A typed literal expression has exactly one literal value. Discharges srf:P8." ] .

srf:RoundingExpressionShape a sh:NodeShape ;
	sh:targetClass srf:RoundingExpression ;
	sh:property [ sh:path srf:roundedOperand ; sh:minCount 1 ; sh:maxCount 1 ;
		sh:message "A rounding expression has exactly one operand. Discharges srf:P7." ] ;
	sh:property [ sh:path srf:roundingScale ; sh:minCount 1 ; sh:maxCount 1 ; sh:datatype xsd:integer ;
		sh:message "A rounding expression has exactly one scale, an integer. Discharges srf:P8." ] .

srf:ChoiceExpressionShape a sh:NodeShape ;
	sh:targetClass srf:ChoiceExpression ;
	sh:property [ sh:path srf:comparisonOperator ; sh:minCount 1 ; sh:maxCount 1 ;
		sh:in ( srf:LessThan srf:LessThanOrEqual srf:EqualTo srf:NotEqualTo srf:GreaterThanOrEqual srf:GreaterThan ) ;
		sh:message "A choice states exactly one comparison operator, one of the six the vocabulary names. Discharges srf:P8." ] ;
	sh:property [ sh:path srf:comparedLeft ; sh:minCount 1 ; sh:maxCount 1 ;
		sh:message "A choice has exactly one left compared operand. Discharges srf:P7." ] ;
	sh:property [ sh:path srf:comparedRight ; sh:minCount 1 ; sh:maxCount 1 ;
		sh:message "A choice has exactly one right compared operand. Discharges srf:P7." ] ;
	sh:property [ sh:path srf:whenTrue ; sh:minCount 1 ; sh:maxCount 1 ;
		sh:message "A choice has exactly one branch for a true comparison. Discharges srf:P7." ] ;
	sh:property [ sh:path srf:whenFalse ; sh:minCount 1 ; sh:maxCount 1 ;
		sh:message "A choice has exactly one branch for a false comparison. Discharges srf:P7." ] .

srf:ConstructedNodeShape a sh:NodeShape ;
	sh:targetClass srf:ConstructedNode ;
	sh:property [ sh:path srf:constructedClass ; sh:minCount 1 ; sh:maxCount 1 ; sh:nodeKind sh:IRI ;
		sh:message "A constructed node states exactly one class. Discharges srf:P11." ] ;
	sh:property [ sh:path srf:nodeIdentity ; sh:minCount 1 ; sh:maxCount 1 ; sh:in ( srf:PerInstance srf:ByKey ) ;
		sh:message "A constructed node states exactly one identity, srf:PerInstance or srf:ByKey. Discharges srf:P11." ] ;
	sh:property [ sh:path srf:writes ; sh:minCount 1 ;
		sh:message "A constructed node writes at least one value. Discharges srf:P11." ] .

srf:WrittenValueShape a sh:NodeShape ;
	sh:targetObjectsOf srf:writes ;
	sh:property [ sh:path srf:writesProperty ; sh:minCount 1 ; sh:maxCount 1 ; sh:nodeKind sh:IRI ;
		sh:message "A written value states exactly one property it is written as. Discharges srf:P12." ] ;
	sh:property [ sh:path srf:fromBinding ; sh:minCount 1 ; sh:maxCount 1 ; sh:nodeKind sh:IRI ;
		sh:message "A written value names exactly one evidence role binding it is read from. Discharges srf:P12." ] .
```

```turtle-shapes
@prefix sh:   <http://www.w3.org/ns/shacl#> .
@prefix srf:  <https://www.nebularis.org/neuro-semantic/lattice/surface#> .

srf:ReadPathFormExclusiveShape a sh:NodeShape ;
	sh:targetClass srf:SurfaceContract ;
	sh:sparql [
		sh:message "A surface contract declares exactly one read-path form: either srf:readProperty or one or more srf:hasPathStep, never both and never neither. Discharges srf:S1." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				{ $this srf:readProperty ?p . $this srf:hasPathStep ?s }
				UNION
				{
					FILTER NOT EXISTS { $this srf:readProperty ?anyProperty }
					FILTER NOT EXISTS { $this srf:hasPathStep ?anyStep }
				}
			}
		"""
	] .

srf:PathStepIndexUniqueShape a sh:NodeShape ;
	sh:targetClass srf:SurfaceContract ;
	sh:sparql [
		sh:message "Two path steps of one read path share a step index. Discharges srf:S1." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				$this srf:hasPathStep ?first, ?second .
				?first srf:stepIndex ?index .
				?second srf:stepIndex ?index .
				FILTER (?first != ?second)
			}
		"""
	] .

srf:BoundSchemePresentShape a sh:NodeShape ;
	sh:targetClass srf:IndexContract ;
	sh:sparql [
		sh:message "A contract-bound population names a scheme contract with no bound scheme and no scheme binding, so it can never resolve. Discharges srf:S2." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			PREFIX voc: <https://www.nebularis.org/neuro-semantic/lattice/vocabulary#>
			SELECT $this WHERE {
				$this srf:valuePopulation ?population .
				?population a srf:ContractBoundPopulation ;
							srf:fromSchemeContract ?schemeContract .
				FILTER NOT EXISTS { ?schemeContract voc:boundScheme ?scheme }
				FILTER NOT EXISTS { ?binding voc:forContract ?schemeContract }
			}
		"""
	] .

srf:BoundSchemeGovernanceShape a sh:NodeShape ;
	sh:targetClass srf:IndexContract ;
	sh:sparql [
		sh:message "A scheme this contract-bound population could resolve to, via boundScheme or a voc:SchemeBinding, holds none of the governance states the contract requires. Discharges srf:S2." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			PREFIX voc: <https://www.nebularis.org/neuro-semantic/lattice/vocabulary#>
			PREFIX fnd: <https://www.nebularis.org/neuro-semantic/lattice/foundation#>
			SELECT $this WHERE {
				$this srf:valuePopulation ?population .
				?population srf:fromSchemeContract ?schemeContract .
				?schemeContract voc:requiresGovernanceState ?required .
				{
					?schemeContract voc:boundScheme ?scheme .
				} UNION {
					?binding voc:forContract ?schemeContract ;
							 voc:bindsScheme ?scheme .
				}
				FILTER NOT EXISTS {
					?schemeContract voc:requiresGovernanceState ?permitted .
					?scheme fnd:hasGovernanceState ?permitted .
				}
			}
		"""
	] .

srf:BoundSchemeSourceResolutionRecordedShape a sh:NodeShape ;
	sh:targetClass srf:ReadSetEntry ;
	sh:sparql [
		sh:message "A BoundSchemeSource read-set entry must record the resolution instant that selected its scheme, so an auditor can recover why without re-running the compiler." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				$this srf:readSourceKind srf:BoundSchemeSource .
				FILTER NOT EXISTS { $this srf:resolvedAt ?at }
			}
		"""
	] .

srf:ClosureBasisAgreementShape a sh:NodeShape ;
	sh:targetClass srf:IndexContract ;
	sh:sparql [
		sh:message "A closure basis is declared exactly when a closure-relation index form is declared. Discharges srf:S3." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				{
					$this srf:indexForm srf:ClosureRelation .
					FILTER NOT EXISTS { $this srf:closureBasis ?basis }
				}
				UNION
				{
					$this srf:closureBasis ?declaredBasis .
					FILTER NOT EXISTS { $this srf:indexForm srf:ClosureRelation }
				}
			}
		"""
	] .

srf:EnumerablePopulationShape a sh:NodeShape ;
	sh:targetClass srf:IndexContract ;
	sh:sparql [
		sh:message "An index form minting one symbol per value requires a population that can be enumerated; a range-partition population cannot be in this release. Discharges srf:S4." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				$this srf:indexForm ?perValueForm ;
					  srf:valuePopulation ?population .
				?population a srf:RangePartitionPopulation .
				FILTER (?perValueForm IN (srf:NominalClass, srf:MembershipAssertion))
			}
		"""
	] .

srf:RangePartitionDeferredShape a sh:NodeShape ;
	sh:targetClass srf:IndexContract ;
	sh:sparql [
		sh:message "Range-partition populations are declared and not yet permitted. Use a DirectProperty index form for quantified dimensions." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				$this srf:valuePopulation ?population .
				?population a srf:RangePartitionPopulation .
			}
		"""
	] .

srf:ExternalIndexDeferredShape a sh:NodeShape ;
	sh:targetClass srf:IndexContract ;
	sh:sparql [
		sh:message "The ExternalIndex form is declared and not yet permitted." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				$this srf:indexForm srf:ExternalIndex .
			}
		"""
	] .

srf:CrosswalkRelationRequiredShape a sh:NodeShape ;
	sh:targetClass srf:PromotionContract ;
	sh:sparql [
		sh:message "A crosswalk promotion names the mapping relation it traverses, and a non-crosswalk promotion names none. Checks the structural condition of srf:X5. The semantic law is discharged in its register, not by this shape." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				{
					$this srf:sourceFidelity ?crosswalk .
					FILTER (?crosswalk IN (srf:CrosswalkExact, srf:CrosswalkInexact))
					FILTER NOT EXISTS { $this srf:viaMatchRelation ?relation }
				}
				UNION
				{
					$this srf:sourceFidelity ?direct .
					$this srf:viaMatchRelation ?declaredRelation .
					FILTER (?direct IN (srf:ExactSource, srf:DerivedSource))
				}
			}
		"""
	] .

srf:DefinitionOnlyPromotionShape a sh:NodeShape ;
	sh:targetClass srf:PromotionContract ;
	sh:sparql [
		sh:message "A definition-only promotion emits a property chain and therefore traverses forward steps only." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				$this srf:realisationMode srf:DefinitionOnly ;
					  srf:hasPathStep ?step .
				?step srf:stepDirection srf:Inverse .
			}
		"""
	] .

srf:PromotionSignatureDisciplineShape a sh:NodeShape ;
	sh:targetClass srf:PromotionContract ;
	sh:sparql [
		sh:message "A promotion onto a property outside the contract's target namespace reaches the authored signature: it must declare exact or crosswalk-exact fidelity and must be materialised rather than definitional. Checks the structural condition of srf:X6. The semantic law is discharged in its register, not by this shape." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				$this srf:promotesTo ?promoted ;
					  srf:targetNamespace ?namespace .
				FILTER (!STRSTARTS(STR(?promoted), STR(?namespace)))
				{
					$this srf:sourceFidelity ?lossy .
					FILTER (?lossy IN (srf:DerivedSource, srf:CrosswalkInexact))
				}
				UNION
				{ $this srf:realisationMode srf:DefinitionOnly }
			}
		"""
	] .

srf:AuthorityCeilingShape a sh:NodeShape ;
	sh:targetClass srf:DerivedArtefact ;
	sh:sparql [
		sh:message "A derived surface artefact declares an authority above cached-reproducible. Discharges srf:S9." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				$this srf:derivationAuthority ?authority .
				FILTER (?authority NOT IN (srf:Advisory, srf:CachedReproducible))
			}
		"""
	] .

srf:InexactPromotionAuthorityShape a sh:NodeShape ;
	sh:targetClass srf:GeneratedSurface ;
	sh:sparql [
		sh:message "A surface generated from a derived or crosswalk-inexact promotion is advisory only. Discharges srf:X5." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				$this srf:coversContract ?contract ;
					  srf:derivationAuthority ?authority .
				?contract srf:sourceFidelity ?lossy .
				FILTER (?lossy IN (srf:DerivedSource, srf:CrosswalkInexact))
				FILTER (?authority != srf:Advisory)
			}
		"""
	] .

srf:StackDepthShape a sh:NodeShape ;
	sh:targetClass srf:GeneratedSurface ;
	sh:sparql [
		sh:message "A generated surface's stack depth exceeds the permitted depth of its profile. Discharges srf:S10." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				$this srf:stackDepth ?depth ;
					  srf:generatedByProfile ?profile .
				?profile srf:permittedStackDepth ?permitted .
				FILTER (?depth > ?permitted)
			}
		"""
	] .

srf:StackDepthReleaseCeilingShape a sh:NodeShape ;
	sh:targetClass srf:SurfaceProfile ;
	sh:sparql [
		sh:message "This release permits a stack depth of at most one surface over another." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				$this srf:permittedStackDepth ?permitted .
				FILTER (?permitted > 1)
			}
		"""
	] .

srf:PopulationBudgetExceededShape a sh:NodeShape ;
	sh:targetClass srf:GeneratedSurface ;
	sh:sparql [
		sh:message "A generation run enumerated more values than its contract's population budget permits. Discharges srf:S4." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				$this srf:populationSize ?size ;
					  srf:coversContract ?contract .
				OPTIONAL { ?contract srf:populationBudget ?contractBudget }
				OPTIONAL {
					?contract srf:surfaceProfile ?profile .
					?profile srf:defaultPopulationBudget ?profileBudget
				}
				BIND (COALESCE(?contractBudget, ?profileBudget, 5000) AS ?budget)
				FILTER (?size > ?budget)
			}
		"""
	] .

srf:PopulationBudgetWarningShape a sh:NodeShape ;
	sh:targetClass srf:GeneratedSurface ;
	sh:severity sh:Warning ;
	sh:sparql [
		sh:message "A generation run enumerated more than five hundred values for a per-value index form. Consider a DirectProperty form." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				$this srf:populationSize ?size .
				FILTER (?size > 500)
			}
		"""
	] .

srf:SymbolNamingInjectiveShape a sh:NodeShape ;
	sh:targetClass srf:GeneratedSurface ;
	sh:sparql [
		sh:message "Two population members minted the same identifier. Discharges srf:S6." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				?first srf:inSurface $this ; srf:denotes ?term ; srf:fromValue ?firstValue .
				?second srf:inSurface $this ; srf:denotes ?term ; srf:fromValue ?secondValue .
				FILTER (?firstValue != ?secondValue)
			}
		"""
	] .

srf:ClosureWellFoundednessDischargedShape a sh:NodeShape ;
	sh:targetClass srf:GeneratedSurface ;
	sh:sparql [
		sh:message "A surface generated for a closure-relation form has no recorded discharge of srf:R5." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				$this srf:coversContract ?contract .
				?contract srf:indexForm srf:ClosureRelation .
				FILTER NOT EXISTS {
					?discharge srf:dischargedForSurface $this ;
							   srf:dischargesLaw srf:R5 .
				}
			}
		"""
	] .

srf:ProjectionEvaluationSubjectRequiredShape a sh:NodeShape ;
	sh:targetClass srf:ProjectionContract ;
	sh:sparql [
		sh:message "A projection contract has no evaluation-subject role binding. Discharges srf:P2." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				$this a srf:ProjectionContract .
				FILTER NOT EXISTS {
					$this srf:hasRoleBinding ?binding .
					?binding srf:roleKind srf:EvaluationSubjectRole .
				}
			}
		"""
	] .

srf:ProjectionResultTargetRequiredShape a sh:NodeShape ;
	sh:targetClass srf:ProjectionContract ;
	sh:sparql [
		sh:message "A projection contract has no result-target role binding. Discharges srf:P2." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				$this a srf:ProjectionContract .
				FILTER NOT EXISTS {
					$this srf:hasRoleBinding ?binding .
					?binding srf:roleKind srf:ResultTargetRole .
				}
			}
		"""
	] .

srf:ProjectionEvidenceRequiredForJoinOrDerivationShape a sh:NodeShape ;
	sh:targetClass srf:ProjectionContract ;
	sh:sparql [
		sh:message "A join or derivation projection has no candidate-evidence or required-evidence role binding. Discharges srf:P2." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				$this srf:projectionKind ?evidenceKind .
				FILTER (?evidenceKind IN (srf:JoinProjection, srf:DerivationProjection))
				FILTER NOT EXISTS {
					$this srf:hasRoleBinding ?binding .
					?binding srf:roleKind ?evidenceRole .
					FILTER (?evidenceRole IN (srf:CandidateEvidenceRole, srf:RequiredEvidenceRole))
				}
			}
		"""
	] .

srf:ProjectionRoleKindSingletonShape a sh:NodeShape ;
	sh:targetClass srf:ProjectionContract ;
	sh:sparql [
		sh:message "A projection contract declares more than one evaluation-subject, result-target, or closure-basis role binding. Discharges srf:P3." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				$this srf:hasRoleBinding ?first, ?second .
				?first srf:roleKind ?singletonRole .
				?second srf:roleKind ?singletonRole .
				FILTER (?first != ?second)
				FILTER (?singletonRole IN (srf:EvaluationSubjectRole, srf:ResultTargetRole, srf:ClosureBasisRole))
			}
		"""
	] .

srf:ProjectionBackendAllowDenyDisjointShape a sh:NodeShape ;
	sh:targetClass srf:ProjectionBackendPolicy ;
	sh:sparql [
		sh:message "A backend policy names one compiler backend in both allowedBackend and deniedBackend. Discharges srf:P4." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				$this srf:allowedBackend ?backend ;
					  srf:deniedBackend ?backend .
			}
		"""
	] .

srf:ProjectionDeterministicOnlyLLMPolicyShape a sh:NodeShape ;
	sh:targetClass srf:ProjectionBackendPolicy ;
	sh:sparql [
		sh:message "A backend policy declares deterministicOnly true and an llmCompletionPolicy other than NoLLMCompletion. Discharges srf:P5." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				$this srf:deterministicOnly true ;
					  srf:llmCompletionPolicy ?policy .
				FILTER (?policy != srf:NoLLMCompletion)
			}
		"""
	] .

srf:DerivationExpressionRequiredShape a sh:NodeShape ;
	sh:targetClass srf:ProjectionContract ;
	sh:sparql [
		sh:message "A derivation projection states no expression on its result-target role binding. Discharges srf:P6." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				$this srf:projectionKind srf:DerivationProjection .
				FILTER NOT EXISTS {
					$this srf:hasRoleBinding ?binding .
					?binding srf:roleKind srf:ResultTargetRole ;
						srf:derivedAs ?expression .
				}
			}
		"""
	] .

srf:DerivationResultPropertyRequiredShape a sh:NodeShape ;
	sh:targetClass srf:ProjectionContract ;
	sh:sparql [
		sh:message "The result-target role binding of a derivation projection binds no property, so there is nothing to write the value on. Discharges srf:P6." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				$this srf:projectionKind srf:DerivationProjection ;
					srf:hasRoleBinding ?binding .
				?binding srf:roleKind srf:ResultTargetRole .
				FILTER NOT EXISTS { ?binding srf:bindsProperty ?property }
			}
		"""
	] .

srf:ProjectionExpressionPlacementShape a sh:NodeShape ;
	sh:targetClass srf:ProjectionRoleBinding ;
	sh:sparql [
		sh:message "A role binding states an expression and is not the result-target role binding of a derivation projection. Discharges srf:P6." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				$this srf:derivedAs ?expression .
				FILTER NOT EXISTS {
					$this srf:roleKind srf:ResultTargetRole .
					?contract srf:hasRoleBinding $this ;
						srf:projectionKind srf:DerivationProjection .
				}
			}
		"""
	] .

srf:ProjectionExpressionReachedShape a sh:NodeShape ;
	sh:targetClass srf:SumExpression , srf:DifferenceExpression , srf:ProductExpression , srf:QuotientExpression ,
		srf:TypedLiteralExpression , srf:RoundingExpression , srf:ChoiceExpression ;
	sh:sparql [
		sh:message "A projection expression is not reached from the result-target role binding of any derivation, so no contract states it. Discharges srf:P6." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				$this a ?kind .
				FILTER NOT EXISTS {
					$this (^srf:leftOperand|^srf:rightOperand|^srf:roundedOperand|^srf:comparedLeft|^srf:comparedRight|^srf:whenTrue|^srf:whenFalse)* ?root .
					?binding srf:derivedAs ?root .
				}
			}
		"""
	] .

srf:ProjectionOperandEvidenceShape a sh:NodeShape ;
	sh:targetClass srf:ProjectionContract ;
	sh:sparql [
		sh:message "An operand of the contract's expression is neither an expression nor a candidate-evidence or required-evidence role binding of this contract that binds a property. Discharges srf:P7." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this ?value WHERE {
				$this srf:hasRoleBinding/srf:derivedAs ?root .
				?root (srf:leftOperand|srf:rightOperand|srf:roundedOperand|srf:comparedLeft|srf:comparedRight|srf:whenTrue|srf:whenFalse)* ?node .
				?node (srf:leftOperand|srf:rightOperand|srf:roundedOperand|srf:comparedLeft|srf:comparedRight|srf:whenTrue|srf:whenFalse) ?value .
				FILTER NOT EXISTS {
					?value a ?kind .
					FILTER (?kind IN (srf:SumExpression, srf:DifferenceExpression, srf:ProductExpression, srf:QuotientExpression,
						srf:TypedLiteralExpression, srf:RoundingExpression, srf:ChoiceExpression))
				}
				FILTER NOT EXISTS {
					$this srf:hasRoleBinding ?value .
					?value srf:roleKind ?role ;
						srf:bindsProperty ?property .
					FILTER (?role IN (srf:RequiredEvidenceRole, srf:CandidateEvidenceRole))
				}
			}
		"""
	] .

srf:ProjectionOperandTypedShape a sh:NodeShape ;
	sh:targetClass srf:SumExpression , srf:DifferenceExpression , srf:ProductExpression , srf:QuotientExpression ,
		srf:TypedLiteralExpression , srf:RoundingExpression , srf:ChoiceExpression ;
	sh:sparql [
		sh:message "An operand states no datatype, neither a result datatype as an expression nor a binding datatype as a role binding. Discharges srf:P8." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this ?value WHERE {
				$this (srf:leftOperand|srf:rightOperand|srf:roundedOperand|srf:comparedLeft|srf:comparedRight|srf:whenTrue|srf:whenFalse) ?value .
				FILTER NOT EXISTS { ?value (srf:resultDatatype|srf:bindsDatatype) ?datatype }
			}
		"""
	] .

srf:ProjectionOperandNumericShape a sh:NodeShape ;
	sh:targetClass srf:SumExpression , srf:DifferenceExpression , srf:ProductExpression , srf:QuotientExpression ,
		srf:TypedLiteralExpression , srf:RoundingExpression , srf:ChoiceExpression ;
	sh:sparql [
		sh:message "An operand of arithmetic or rounding is not numeric. Its datatype is none of xsd:integer, xsd:decimal, xsd:float and xsd:double. Discharges srf:P8." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
			SELECT $this ?value WHERE {
				$this (srf:leftOperand|srf:rightOperand|srf:roundedOperand) ?value .
				?value (srf:resultDatatype|srf:bindsDatatype) ?datatype .
				FILTER (?datatype NOT IN (xsd:integer, xsd:decimal, xsd:float, xsd:double))
			}
		"""
	] .

srf:ProjectionOrderingOperandsShape a sh:NodeShape ;
	sh:targetClass srf:ChoiceExpression ;
	sh:sparql [
		sh:message "A choice compares by order and one of its compared operands is not numeric. Discharges srf:P8." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
			SELECT $this ?value WHERE {
				$this srf:comparisonOperator ?operator ;
					(srf:comparedLeft|srf:comparedRight) ?value .
				?value (srf:resultDatatype|srf:bindsDatatype) ?datatype .
				FILTER (?operator IN (srf:LessThan, srf:LessThanOrEqual, srf:GreaterThanOrEqual, srf:GreaterThan))
				FILTER (?datatype NOT IN (xsd:integer, xsd:decimal, xsd:float, xsd:double))
			}
		"""
	] .

srf:ProjectionComparedOperandsShape a sh:NodeShape ;
	sh:targetClass srf:ChoiceExpression ;
	sh:sparql [
		sh:message "A choice compares two operands of different datatypes that are not both numeric. Discharges srf:P8." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
			SELECT $this ?value WHERE {
				$this srf:comparedLeft ?left ;
					srf:comparedRight ?value .
				?left (srf:resultDatatype|srf:bindsDatatype) ?leftType .
				?value (srf:resultDatatype|srf:bindsDatatype) ?rightType .
				FILTER (?leftType != ?rightType)
				FILTER (!(?leftType IN (xsd:integer, xsd:decimal, xsd:float, xsd:double) && ?rightType IN (xsd:integer, xsd:decimal, xsd:float, xsd:double)))
			}
		"""
	] .

srf:ProjectionBranchDatatypeShape a sh:NodeShape ;
	sh:targetClass srf:ChoiceExpression ;
	sh:sparql [
		sh:message "A branch of a choice has a datatype other than the choice's own result datatype. Discharges srf:P8." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this ?value WHERE {
				$this srf:resultDatatype ?actual ;
					(srf:whenTrue|srf:whenFalse) ?value .
				?value (srf:resultDatatype|srf:bindsDatatype) ?branchType .
				FILTER (?branchType != ?actual)
			}
		"""
	] .

srf:ProjectionArithmeticDatatypeShape a sh:NodeShape ;
	sh:targetClass srf:SumExpression , srf:DifferenceExpression , srf:ProductExpression ;
	sh:sparql [
		sh:message "The result datatype of a sum, difference or product is not the wider of its operands' datatypes under numeric promotion. Discharges srf:P8." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
			SELECT $this ?value WHERE {
				$this srf:leftOperand ?left ;
					srf:rightOperand ?right ;
					srf:resultDatatype ?actual .
				?left (srf:resultDatatype|srf:bindsDatatype) ?leftType .
				?right (srf:resultDatatype|srf:bindsDatatype) ?rightType .
				BIND(IF(?leftType = xsd:integer, 1, IF(?leftType = xsd:decimal, 2, IF(?leftType = xsd:float, 3, IF(?leftType = xsd:double, 4, 0)))) AS ?leftRank)
				BIND(IF(?rightType = xsd:integer, 1, IF(?rightType = xsd:decimal, 2, IF(?rightType = xsd:float, 3, IF(?rightType = xsd:double, 4, 0)))) AS ?rightRank)
				BIND(IF(?leftRank > ?rightRank, ?leftRank, ?rightRank) AS ?widest)
				BIND(IF(?widest > 1, ?widest, 1) AS ?rank)
				BIND(IF(?rank = 1, xsd:integer, IF(?rank = 2, xsd:decimal, IF(?rank = 3, xsd:float, xsd:double))) AS ?expected)
				BIND(?actual AS ?value)
				FILTER (?leftRank > 0 && ?rightRank > 0 && ?actual != ?expected)
			}
		"""
	] .

srf:ProjectionQuotientDatatypeShape a sh:NodeShape ;
	sh:targetClass srf:QuotientExpression ;
	sh:sparql [
		sh:message "The result datatype of a quotient is not the wider of its operands' datatypes under numeric promotion, and at least xsd:decimal. Discharges srf:P8." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
			SELECT $this ?value WHERE {
				$this srf:leftOperand ?left ;
					srf:rightOperand ?right ;
					srf:resultDatatype ?actual .
				?left (srf:resultDatatype|srf:bindsDatatype) ?leftType .
				?right (srf:resultDatatype|srf:bindsDatatype) ?rightType .
				BIND(IF(?leftType = xsd:integer, 1, IF(?leftType = xsd:decimal, 2, IF(?leftType = xsd:float, 3, IF(?leftType = xsd:double, 4, 0)))) AS ?leftRank)
				BIND(IF(?rightType = xsd:integer, 1, IF(?rightType = xsd:decimal, 2, IF(?rightType = xsd:float, 3, IF(?rightType = xsd:double, 4, 0)))) AS ?rightRank)
				BIND(IF(?leftRank > ?rightRank, ?leftRank, ?rightRank) AS ?widest)
				BIND(IF(?widest > 2, ?widest, 2) AS ?rank)
				BIND(IF(?rank = 1, xsd:integer, IF(?rank = 2, xsd:decimal, IF(?rank = 3, xsd:float, xsd:double))) AS ?expected)
				BIND(?actual AS ?value)
				FILTER (?leftRank > 0 && ?rightRank > 0 && ?actual != ?expected)
			}
		"""
	] .

srf:ProjectionRoundingDatatypeShape a sh:NodeShape ;
	sh:targetClass srf:RoundingExpression ;
	sh:sparql [
		sh:message "The result datatype of a rounding expression is not the datatype of its operand. Discharges srf:P8." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this ?value WHERE {
				$this srf:roundedOperand ?operand ;
					srf:resultDatatype ?actual .
				?operand (srf:resultDatatype|srf:bindsDatatype) ?operandType .
				BIND(?actual AS ?value)
				FILTER (?operandType != ?actual)
			}
		"""
	] .

srf:ProjectionLiteralDatatypeShape a sh:NodeShape ;
	sh:targetClass srf:TypedLiteralExpression ;
	sh:sparql [
		sh:message "The literal of a typed literal expression does not have the expression's result datatype. Discharges srf:P8." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this ?value WHERE {
				$this srf:typedValue ?value ;
					srf:resultDatatype ?actual .
				FILTER (datatype(?value) != ?actual)
			}
		"""
	] .

srf:ProjectionResultTargetDatatypeShape a sh:NodeShape ;
	sh:targetClass srf:ProjectionRoleBinding ;
	sh:sparql [
		sh:message "The datatype a result-target role binding states is missing or is not the result datatype of the expression it states. Discharges srf:P8." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				$this srf:derivedAs ?expression .
				?expression srf:resultDatatype ?datatype .
				FILTER NOT EXISTS { $this srf:bindsDatatype ?datatype }
			}
		"""
	] .

srf:ProjectionExpressionAcyclicShape a sh:NodeShape ;
	sh:targetClass srf:SumExpression , srf:DifferenceExpression , srf:ProductExpression , srf:QuotientExpression ,
		srf:TypedLiteralExpression , srf:RoundingExpression , srf:ChoiceExpression ;
	sh:sparql [
		sh:message "A projection expression is an operand of itself, directly or through other expressions. Discharges srf:P9." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				$this (srf:leftOperand|srf:rightOperand|srf:roundedOperand|srf:comparedLeft|srf:comparedRight|srf:whenTrue|srf:whenFalse)+ $this .
			}
		"""
	] .

srf:ConstructionRequiredShape a sh:NodeShape ;
	sh:targetClass srf:ProjectionContract ;
	sh:sparql [
		sh:message "A graph construction projection states no constructed node on its result-target role binding. Discharges srf:P10." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				$this srf:projectionKind srf:GraphConstructionProjection .
				FILTER NOT EXISTS {
					$this srf:hasRoleBinding ?binding .
					?binding srf:roleKind srf:ResultTargetRole ;
						srf:constructedAs ?node .
				}
			}
		"""
	] .

srf:ConstructionLinkPropertyRequiredShape a sh:NodeShape ;
	sh:targetClass srf:ProjectionContract ;
	sh:sparql [
		sh:message "The result-target role binding of a graph construction binds no property, so there is no link from an instance to the node. Discharges srf:P10." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				$this srf:projectionKind srf:GraphConstructionProjection ;
					srf:hasRoleBinding ?binding .
				?binding srf:roleKind srf:ResultTargetRole .
				FILTER NOT EXISTS { ?binding srf:bindsProperty ?property }
			}
		"""
	] .

srf:ConstructionPlacementShape a sh:NodeShape ;
	sh:targetClass srf:ProjectionRoleBinding ;
	sh:sparql [
		sh:message "A role binding states a constructed node and is not the result-target role binding of a graph construction. Discharges srf:P10." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				$this srf:constructedAs ?node .
				FILTER NOT EXISTS {
					$this srf:roleKind srf:ResultTargetRole .
					?contract srf:hasRoleBinding $this ;
						srf:projectionKind srf:GraphConstructionProjection .
				}
			}
		"""
	] .

srf:ConstructionNodeTypedShape a sh:NodeShape ;
	sh:targetClass srf:ProjectionRoleBinding ;
	sh:sparql [
		sh:message "A role binding states as its constructed node a term that is not a srf:ConstructedNode named by an IRI. Discharges srf:P10." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this ?value WHERE {
				$this srf:constructedAs ?value .
				FILTER (!isIRI(?value) || NOT EXISTS { ?value a srf:ConstructedNode })
			}
		"""
	] .

srf:ConstructedNodeReachedShape a sh:NodeShape ;
	sh:targetClass srf:ConstructedNode ;
	sh:sparql [
		sh:message "A constructed node is not stated by the result-target role binding of any graph construction, so no contract constructs it. Discharges srf:P10." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				$this a srf:ConstructedNode .
				FILTER NOT EXISTS { ?binding srf:constructedAs $this }
			}
		"""
	] .

srf:ConstructedKeyShape a sh:NodeShape ;
	sh:targetClass srf:ConstructedNode ;
	sh:sparql [
		sh:message "A constructed node by key names no key binding, or a constructed node for each instance names one. Discharges srf:P11." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this WHERE {
				{
					$this srf:nodeIdentity srf:ByKey .
					FILTER NOT EXISTS { $this srf:keyBinding ?key }
				} UNION {
					$this srf:nodeIdentity srf:PerInstance ;
						srf:keyBinding ?key .
				}
			}
		"""
	] .

srf:ConstructedPropertyOnceShape a sh:NodeShape ;
	sh:targetClass srf:ConstructedNode ;
	sh:sparql [
		sh:message "A constructed node writes one property more than once. Discharges srf:P11." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this ?value WHERE {
				$this srf:writes ?first , ?second .
				?first srf:writesProperty ?value .
				?second srf:writesProperty ?value .
				FILTER (?first != ?second)
			}
		"""
	] .

srf:WrittenValueEvidenceShape a sh:NodeShape ;
	sh:targetClass srf:ConstructedNode ;
	sh:sparql [
		sh:message "A value a constructed node writes is read from a term that is not a candidate-evidence or required-evidence role binding of the stating contract that binds a property. Discharges srf:P12." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this ?value WHERE {
				?link srf:constructedAs $this .
				?contract srf:hasRoleBinding ?link .
				$this srf:writes/srf:fromBinding ?value .
				FILTER NOT EXISTS {
					?contract srf:hasRoleBinding ?value .
					?value srf:roleKind ?role ;
						srf:bindsProperty ?property .
					FILTER (?role IN (srf:RequiredEvidenceRole, srf:CandidateEvidenceRole))
				}
			}
		"""
	] .

srf:ConstructedKeyEvidenceShape a sh:NodeShape ;
	sh:targetClass srf:ConstructedNode ;
	sh:sparql [
		sh:message "A key binding of a constructed node is not a required-evidence role binding of the stating contract that binds a property. Discharges srf:P13." ;
		sh:select """
			PREFIX srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#>
			SELECT $this ?value WHERE {
				?link srf:constructedAs $this .
				?contract srf:hasRoleBinding ?link .
				$this srf:keyBinding ?value .
				FILTER NOT EXISTS {
					?contract srf:hasRoleBinding ?value .
					?value srf:roleKind srf:RequiredEvidenceRole ;
						srf:bindsProperty ?property .
				}
			}
		"""
	] .
```

## 11. Canonicalisation, identity, and invalidation

A generation run records what it read, not merely what it produced. Each `srf:ReadSetEntry` names one input and the hash of that input's canonical content at the time it was read. A surface is stale exactly when any entry's current hash differs from the recorded one. That is the whole rule, and no change needs to be classified for staleness to be decided.

Change classification survives as the impact-scoping question — how much to recompute once staleness is known:

| What moved | Recompute |
|---|---|
| Bound scheme membership | symbol inventory for that contract, and closure where a closure form is declared |
| Closure basis subgraph | closure symbols and the assertions depending on them |
| Carrier instance graph | materialised memberships and matches for the changed instances only, and nothing at all under `DefinitionOnly` |
| Scheme contract binding or required governance state | the whole contract |
| Profile identity | every surface on that profile, with a version bump |
| Canonicalisation version | the whole estate, rehashed |

Separating definitions from materialised assertions into different emitted modules is what lets the third row avoid touching a definitional module at all.

`srf:semanticContentHash` covers the canonical, meaning-bearing inputs, and `srf:artefactHash` covers the emitted bytes. Reuse of an existing surface requires both a matching semantic content hash and a matching profile identity, and an artefact hash that changes while both of those hold is a generator defect, not a source change.

## 12. Conformance

A generated surface is **projection-conformant (L7)** when every static constraint in §9's register passes, every read-set entry is current, the runtime-conformance laws its declared forms bring into play are discharged, and the parity law `srf:R2` holds over the shared conformance corpus for the questions the surface claims to answer.

Two consequences hold regardless:

- A conformant surface does not raise the conformance level of the graph it indexes. A surface over an analysis-ready graph does not make that graph operationally evaluable. Surfaces accelerate, and they do not admit.
- A surface is never the evidence for an admissibility decision or an execution record. Those cite declarations. That an implementation reached the answer through a surface is a realisation-profile fact recorded on the decision, not a change in what the decision rests on.

## 13. Worked Examples

Non-domain examples are authored in:

- `ontology/surface/examples/employment-job-family.ttl` — hierarchical closure and per-value classes over a scheme-bound population
- `ontology/surface/examples/saas-subscription-currency.ttl` — promotion across a three-step read path onto a direct property
- `ontology/surface/examples/clinical-trial-crosswalk.ttl` — promotion across an inexact mapping relation
- `ontology/surface/examples/saas-subscription-arr-projection.ttl` — a derivation projection stating the product of two required-evidence bindings as its expression, lowered under a deterministic-only backend policy
- `ontology/surface/examples/order-supplier-construction-projection.ttl` — a graph construction projection stating a supplier for each supplier code, with its class, its key, and the code and name it writes, lowered under a deterministic-only backend policy

Deliberate-defect fixtures are authored in `ontology/surface/test/`.

```turtle-example
@prefix srf: <https://www.nebularis.org/neuro-semantic/lattice/surface#> .
@prefix ex:  <https://example.org/lattice/surface/> .

ex:index-1 a srf:IndexContract ;
	srf:contractKey "example" ;
	srf:indexForm srf:NominalClass .
```

## 14. Release notes

- **Unreleased**.
  - no effect. A graph construction projection states the node it writes. New: `srf:ConstructedNode`, `srf:WrittenValue` and `srf:IdentityChoice` with its two individuals `srf:PerInstance` and `srf:ByKey`, and the properties `srf:constructedAs`, `srf:constructedClass`, `srf:nodeIdentity`, `srf:keyBinding`, `srf:writes`, `srf:writesProperty` and `srf:fromBinding`. New laws `srf:P10` to `srf:P13`, with a shape for each part of them, and `srf:P1` says how a constructed node's class decides its signature scope.
  - may invalidate. A graph construction projection that states no constructed node on its result-target role binding fails the new shape, and the compiler refuses to read it. A projection of another kind that states one fails too. The example is a graph construction, an order giving a supplier keyed by a supplier code.
  - no effect. A derivation projection states its operation. New: `srf:ProjectionExpression` with `srf:SumExpression`, `srf:DifferenceExpression`, `srf:ProductExpression` and `srf:QuotientExpression` under `srf:ArithmeticExpression`, `srf:TypedLiteralExpression`, `srf:RoundingExpression` and `srf:ChoiceExpression`, `srf:ComparisonOperator` with its six individuals, and the properties `srf:derivedAs`, `srf:bindsDatatype`, `srf:resultDatatype`, `srf:leftOperand`, `srf:rightOperand`, `srf:typedValue`, `srf:roundedOperand`, `srf:roundingScale`, `srf:comparisonOperator`, `srf:comparedLeft`, `srf:comparedRight`, `srf:whenTrue` and `srf:whenFalse`. New laws `srf:P6` to `srf:P9`, with a shape for each part of them.
  - may invalidate. A derivation projection that states no expression on its result-target role binding fails the new shape, and the compiler refuses to read it. A projection of another kind that states one fails too. The example derivation states its operation, the product of its monthly price and its billing periods a year, and the datatype of each evidence binding.
  - no effect. Six SPARQL constraints of the shapes no longer use a `VALUES` clause, which SHACL forbids in a constraint and a validator such as pySHACL refuses, so the shapes load in one. Each is written with `FILTER` and `IN` and reports what it reported.
- **0.21.0**.
  - no effect. Imports re-pinned to release 0.21.0, with no other change.
- **0.20.0**.
  - changes meaning ([ADR-A141](../../docs/architecture/decisions/ADR-A141-versioned-mixin-rename.md)). Imports re-pinned to release 0.20.0, whose Foundation renames fnd:Version to fnd:Versioned, so a graph that typed a thing fnd:Version re-keys.
  - no effect ([ADR-A143](../../docs/architecture/decisions/ADR-A143-one-canonicalisation.md)). Every hash names its content triples and the substrate's digest rule, RDFC-1.0 canonical N-Quads, SHA-256, lowercase hex, and the two promotion shapes say they check the structural condition of X5 and X6 rather than discharging them.

Earlier versions are listed in the [ontology release register](../../docs/architecture/ontology-releases.md).
