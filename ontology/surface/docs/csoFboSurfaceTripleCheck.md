# Triple-check: can `surface` carry the complexity of CSO → FBO?

## Short answer

**Partly, yes. Entirely, no.**

After checking the live Surface design, the current compiler, the FBO design, the FBO core ontology, and the older CSO→FBO projection mapping, my conclusion is:

- **`surface` is strong enough to handle the path-based, deterministic, query-facing part of CSO → FBO projection**
- **`surface` is not a replacement for the full `π₃₄` CSO → FBO compiler**

That distinction matters.

If the question is:

- can Surface flatten long property chains,
- cross mapping relations,
- materialise exact convenience properties onto FBO-authored predicates,
- and build efficient retrieval structures over the resulting FBO graph,

then the answer is **yes**.

If the question is:

- can Surface itself create `fbo:LimitTank`, `fbo:AggregateTank`, `fbo:RetentionTank`, `fbo:FlowAction`, `fbo:ScopeQualifier`, derive multiple output nodes from one facet, perform value-resolution joins, perform non-trivial semantic rewrites, and stand in for the CSO→FBO compiler,

then the answer is **no**.

---

## My confidence after the triple-check

I am confident of the following:

1. **X6 does not block the FBO projection path you care about**, provided the promoted FBO property is exact or exact-by-crosswalk and the restatement is materialised.
2. **Surface is a good downstream projection and acceleration mechanism around FBO**.
3. **Surface is not the right mechanism for the whole CSO→FBO semantic compilation problem**.
4. **Keeping X6 is still the right choice**, because it constrains only the dangerous cases, not the exact FBO convenience projections you want to preserve.

---

## Why I am saying “partly yes, partly no”

The live Surface layer has two operations only:

- `PromotionContract` — restate a reachable value as a direct assertion on the carrier
- `IndexContract` — restate a reachable value as a retrievable symbol

That is explicit in [ontology/surface/README.md](ontology/surface/README.md#L11-L18), and the implementation mirrors it in [tools/surface/model.py](tools/surface/model.py#L81-L110) and [tools/surface/compile.py](tools/surface/compile.py#L374-L514).

The pre-Surface CSO→FBO mapping file is doing much more than that. It is not just flattening paths. It is a **semantic compiler** that:

- creates new behavioural entities
- changes representation level
- derives dimensions from multiple structural inputs
- resolves value crosswalks and type breaks
- initialises state-related structures
- preserves rule identities and coverage completeness

That is visible in [WINGMAN/Nebularis/Ontologies/specification/MERIDIAN%20CSO-FBO%20Projection%20Mapping%20V1.0.ttl](WINGMAN/Nebularis/Ontologies/specification/MERIDIAN%20CSO-FBO%20Projection%20Mapping%20V1.0.ttl), especially rules `R001`–`R019` and the dimension sourcing block.

So the key architectural point is:

## Surface can express deterministic restatement of already-available graph facts

but

## Surface cannot, by itself, express the full structural-to-behavioural compilation that creates the FBO graph in the first place.

---

## What `surface` can handle well

## 1. Multi-hop property traversal

This is a core strength.

The Surface README explicitly supports:

- single-hop property lookup
- multi-hop traversal
- traversal through a mapping or crosswalk relation

See [ontology/surface/README.md](ontology/surface/README.md#L30-L38) and [ontology/surface/README.md](ontology/surface/README.md#L147-L156).

The current implementation supports this directly with ordered `PathStep` sequences in [tools/surface/model.py](tools/surface/model.py#L62-L74) and path evaluation in [tools/surface/model.py](tools/surface/model.py#L138-L145).

### Relevance to CSO → FBO

This means Surface is well suited to cases like:

- reading `ctr:hasLineOfBusinessScope` from a `ctr:TermApplication`
- following a multi-hop structural chain to a value that a consumer wants as one direct FBO-facing predicate
- traversing a final match relation into a governed vocabulary

That part of your complexity is a fit.

---

## 2. Exact restatement onto authored FBO properties

This is the point you care about most.

Surface allows source-signature promotion onto an authored property when the promotion is:

- `ExactSource`, or
- `CrosswalkExact`

and when the output is:

- `Materialised`, not `DefinitionOnly`

This is not just design prose. It is enforced in [tools/surface/compile.py](tools/surface/compile.py#L480-L514).

### Relevance to FBO

For dimensions that are structurally direct or exact after an exact crosswalk, Surface can safely restate them onto FBO-owned properties.

A strong candidate is **dimension 6**:

- CSO source: `ctr:hasLineOfBusinessScope`
- FBO target: `fbo:hasLineOfBusiness`
- mapping status in the older mapping file: `direct`

See [WINGMAN/Nebularis/Ontologies/specification/MERIDIAN%20CSO-FBO%20Projection%20Mapping%20V1.0.ttl](WINGMAN/Nebularis/Ontologies/specification/MERIDIAN%20CSO-FBO%20Projection%20Mapping%20V1.0.ttl#L249-L252).

This is exactly the class of case X6 preserves.

---

## 3. Crosswalk-aware projection, with exact vs inexact explicitly separated

Surface already models crosswalk traversal through `srf:viaMatchRelation`, with fidelity declared on the contract. See [ontology/surface/README.md](ontology/surface/README.md#L82-L84) and [ontology/surface/README.md](ontology/surface/README.md#L191-L192).

There is a working example in [ontology/surface/examples/clinical-trial-crosswalk.ttl](ontology/surface/examples/clinical-trial-crosswalk.ttl), and a test covering it in [tools/surface/test_surface.py](tools/surface/test_surface.py#L263-L268).

### Relevance to CSO → FBO

This means Surface can cope with:

- exact crosswalks into FBO vocabularies
- inexact crosswalks into generated properties for advisory use

This is especially important because the CSO→FBO mapping file already admits that some mappings are **not lossless**, for example trigger-mode projection. See `R007` in [WINGMAN/Nebularis/Ontologies/specification/MERIDIAN%20CSO-FBO%20Projection%20Mapping%20V1.0.ttl](WINGMAN/Nebularis/Ontologies/specification/MERIDIAN%20CSO-FBO%20Projection%20Mapping%20V1.0.ttl#L129-L135).

So Surface is a good fit where you need exactness discipline on crosswalk-driven promotions.

---

## 4. Efficient retrieval over hierarchical dimensions

Surface is also a good fit for the **read efficiently afterwards** part of your problem.

It supports:

- `NominalClass`
- `MembershipAssertion`
- `ClosureRelation`
- explicit `closureBasis`
- governed populations through `ContractBoundPopulation`

See [ontology/surface/README.md](ontology/surface/README.md#L94-L117), [ontology/surface/README.md](ontology/surface/README.md#L127-L145), and [tools/surface/compile.py](tools/surface/compile.py#L374-L457).

### Relevance to FBO

This is a strong fit for FBO’s hierarchical dimensions such as:

- `fbo:hasPeril`
- `fbo:hasTerritory`
- `fbo:hasLineOfBusiness`
- `fbo:hasAssetClass`

The FBO design explicitly marks those as hierarchical in the twenty-dimensional model, see [WINGMAN/Nebularis/Ontologies/specification/MERIDIAN%20Financial%20Behaviour%20Ontology%20(FBO)%20Detailed%20Design%20V2.md](WINGMAN/Nebularis/Ontologies/specification/MERIDIAN%20Financial%20Behaviour%20Ontology%20(FBO)%20Detailed%20Design%20V2.md#L214-L221).

That means a very plausible architecture is:

1. use a real CSO→FBO compiler to generate valid FBO qualifiers and tanks
2. use Surface to create query-facing retrieval layers over hierarchical FBO dimensions

This is where Surface adds a lot of value.

---

## 5. Governance, invalidation, and regeneration

If you are going to project exact facts into FBO-authored properties, you need a clean story for:

- what was read
- what was generated
- when it went stale
- what must be regenerated

Surface gives you that directly through its read set and generated-surface manifests, see [ontology/surface/README.md](ontology/surface/README.md#L179-L187) and [tools/surface/compile.py](tools/surface/compile.py#L313-L360).

This is one of the main reasons it is a better home than MORK for this specific problem.

---

## What `surface` cannot handle as the whole CSO → FBO mechanism

## 1. It does not create arbitrary target nodes

Surface promotes or indexes **existing reachable values** from carrier instances.
It does not implement a general graph-construction mapping calculus.

The implementation creates only:

- generated properties
- generated classes
- closure relations
- manifest records

See [tools/surface/compile.py](tools/surface/compile.py#L401-L514).

It does **not** create domain nodes like:

- `fbo:LimitTank`
- `fbo:AggregateTank`
- `fbo:RetentionTank`
- `fbo:FlowAction`
- `fbo:ScopeQualifier`

That matters because the old mapping file is full of rules whose whole purpose is target-node creation, including `R001`–`R006`. See [WINGMAN/Nebularis/Ontologies/specification/MERIDIAN%20CSO-FBO%20Projection%20Mapping%20V1.0.ttl](WINGMAN/Nebularis/Ontologies/specification/MERIDIAN%20CSO-FBO%20Projection%20Mapping%20V1.0.ttl#L89-L127).

### Practical consequence

If your question is “can Surface replace the compiler that projects facets and directives into FBO behavioural entities?”, the answer is no.

---

## 2. It does not perform multi-source semantic derivation

Many CSO→FBO mappings are not simple path reads. They derive one FBO field from multiple structural inputs.

Examples from the older mapping file:

- `D09_TimeWindow` derives from aggregation windows, hours-clause parameters, waiting periods, and indemnity periods
- `D11_CostClass` derives from defense-cost treatment structure
- `D13_PartyRole` derives role-side semantics from claimant and payee role sources
- `D14_TemporalQualifier` derives from retroactive and continuity dates

See [WINGMAN/Nebularis/Ontologies/specification/MERIDIAN%20CSO-FBO%20Projection%20Mapping%20V1.0.ttl](WINGMAN/Nebularis/Ontologies/specification/MERIDIAN%20CSO-FBO%20Projection%20Mapping%20V1.0.ttl#L253-L304).

Surface does not contain a transformation language for “take these several inputs and synthesise one target concept by rule”. It follows a declared path and restates what it reaches.

### Practical consequence

Surface is suitable after the derivation is already made available in the source graph, not as the place where the derivation logic itself lives.

---

## 3. It does not handle datatype-to-concept resolution joins

This is a very important boundary.

The older CSO→FBO mapping has cases where a source literal must be resolved to a target SKOS concept, for example currency code resolution by `skos:notation`. See `R015` in [WINGMAN/Nebularis/Ontologies/specification/MERIDIAN%20CSO-FBO%20Projection%20Mapping%20V1.0.ttl](WINGMAN/Nebularis/Ontologies/specification/MERIDIAN%20CSO-FBO%20Projection%20Mapping%20V1.0.ttl#L174-L182).

The Surface compiler’s path evaluation is graph-object traversal via `graph.objects(start, contract.read_path())` in [tools/surface/compile.py](tools/surface/compile.py#L135-L138).

That is not a general join engine. It does not express:

- “read a string literal”
- “find the concept whose `skos:notation` matches it”
- “fail if none exists”

### Practical consequence

Some of the hardest CSO→FBO mapping work is beyond Surface by design.

---

## 4. It does not express one-to-many target expansion rules

The old mapping contains cases like `R009`, where one defense-cost facet yields two qualifiers that differ on cost-class behavior. See [WINGMAN/Nebularis/Ontologies/specification/MERIDIAN%20CSO-FBO%20Projection%20Mapping%20V1.0.ttl](WINGMAN/Nebularis/Ontologies/specification/MERIDIAN%20CSO-FBO%20Projection%20Mapping%20V1.0.ttl#L141-L145) and rule commentary later in the file.

Surface is not a duplication engine of that kind.
It does not say “from one source node, manufacture two target behavioural nodes with coordinated differences”.

### Practical consequence

That logic belongs in the behavioural compiler, not in Surface.

---

## 5. Some Surface forms have deliberate limits

These limits do not make Surface unsuitable. They just show where composition is needed.

### Closure over multi-hop paths is refused

The current compiler refuses `ClosureRelation` over a multi-hop read path and tells you to promote first, then index. See [tools/surface/compile.py](tools/surface/compile.py#L421-L427).

That means if you want efficient ancestor retrieval after a long CSO chain, the right pattern is:

1. materialise the long path as a promoted direct property
2. index that property with closure as a second surface

That is still workable. It just becomes a two-stage design.

### Definition-only promotion is restricted

Definition-only promotions:

- must be forward-only
- may not target authored properties

See [ontology/surface/README.md](ontology/surface/README.md#L155-L162) and [tools/surface/compile.py](tools/surface/compile.py#L503-L514).

For your FBO use case this is acceptable, because the recommended path is already materialised source-signature promotion for exact restatements.

### Range partition is not ready

`RangePartitionPopulation` is still declared but intentionally unavailable. See [ontology/surface/README.md](ontology/surface/README.md#L145-L145) and [tools/surface/model.py](tools/surface/model.py#L220-L224).

This matters later for some quantitative bucketed retrieval patterns, but not for the current X6 decision.

### Stack depth is capped at one

Surface-over-surface is supported, but only one level deep in the current release. See [ontology/surface/README.md](ontology/surface/README.md#L168-L168) and [tools/surface/compile.py](tools/surface/compile.py#L570-L584).

That still allows the useful pattern:

- Stage 1: promote a long path
- Stage 2: index the promoted property

which is exactly one layer of stacking.

---

## How the attached CSO → FBO mapping breaks down against Surface

## Category A — not Surface, must stay in a real compiler

These mappings are structural compilation, not surface restatement:

- `R001` `ctr:LimitFacet -> fbo:LimitTank`
- `R002` `ctr:AggregationFacet -> fbo:AggregateTank`
- `R003` `ctr:RetentionFacet -> fbo:RetentionTank`
- `R004` `ctr:FlowDirective -> fbo:FlowAction`
- `R005` `ctr:TermApplication -> fbo:ScopeQualifier`
- `R006` `ctr:Claim -> fbo:Claim`

These create or align behavioural entities. Surface does not do that.

## Category B — can be supported by Surface once the target entity exists

These are good Surface candidates after the compiler has produced the relevant FBO node:

- exact promotion of scope values onto FBO-authored properties
- exact promotion of behavioural convenience fields for queryability
- indexing over hierarchical FBO dimensions for fast retrieval
- source-signature materialised promotion into FBO where exactness holds

Examples:

- `D06 LineOfBusiness`
- `D07 AssetClass`
- `D01 Peril`
- `D02 Territory`

provided their source path is exact and already represented in graph form.

## Category C — partially compatible, but only in constrained cases

These depend on exactness or on a preprocessing compiler:

- `D10 TriggerMode` because the mapping file itself says the crosswalk is partial and not injective
- `D12 CurrencyFX` because notation-based concept resolution is not plain graph traversal
- `D13 PartyRole` where role-side derivation may need preprocessing before restatement
- `D14 TemporalQualifier` when derived from multiple structural conditions rather than a directly reachable asserted value

---

## What this means for your decision on X6

This triple-check made me more confident, not less, in keeping X6.

Why:

1. **The exact FBO projection path you care about is still available.**
   - For direct or exact-crosswalk cases, Surface can materialise onto FBO properties.

2. **The hard CSO→FBO logic is not a reason to weaken X6.**
   - That complexity mostly lives in the compiler problem, not in the source-signature-promotion policy problem.

3. **Weakening X6 would not solve the real hard cases.**
   - Allowing lossy or definition-only authored-signature projection would not suddenly make Surface capable of node synthesis, datatype-concept joins, or multi-input semantic derivation.
   - It would only make approximate or inferential outputs look more authoritative than they are.

So the complexity of `π₃₄` is **not** an argument against X6.
It is an argument for a clean split of responsibilities.

---

## Recommended architecture

## Recommended split

### 1. Keep a dedicated CSO → FBO compiler

This compiler remains responsible for:

- generating FBO behavioural nodes
- creating tanks, actions, qualifiers, claims and spans
- performing semantic derivations
- performing value resolution and crosswalk validation
- enforcing projection completeness

That is what the older mapping file was trying to do.

### 2. Use Surface for exact, deterministic restatement around that compiler

Use Surface in three ways:

#### A. Exact convenience projection into FBO-authored properties
For exact cases only.
Example shape:
- project an already-determined line of business onto `fbo:hasLineOfBusiness`
- materialised
- source-signature
- exact or exact-crosswalk only

#### B. Local-signature advisory projections for lossy or heuristic results
For approximate normalisation, unresolved crosswalks, or convenience summaries.
Example shape:
- emit `generated:projectedTriggerMode` or similar
- keep it visibly generated
- advisory authority

#### C. Efficient retrieval over produced FBO structures
After the FBO graph exists:
- index hierarchical dimensions
- materialise closure relations
- make retrieval cheap without changing FBO semantics

This is where Surface is strongest.

---

## Concrete use-cases

## Use case 1 — exact line-of-business projection into FBO

### Input situation
A `ctr:TermApplication` has an exact `ctr:hasLineOfBusinessScope` value.
The compiler creates the relevant `fbo:ScopeQualifier`.
A consumer wants to query one direct FBO property.

### Surface fit
Good.
This can be a source-signature materialised promotion onto `fbo:hasLineOfBusiness`.

### X6 status
Allowed.

---

## Use case 2 — trigger-mode projection with partial crosswalk

### Input situation
`ctr:ClaimsBasisFacet` maps through a crosswalk that the mapping file explicitly says is partial and not injective.

### Surface fit
Not safe as an authored-property promotion unless the exact case is proven.

### X6 status
- exact case: allowed
- inexact case: must land on a generated property, not `fbo:hasTriggerMode`

This is a feature, not a bug.

---

## Use case 3 — long structural chain, then hierarchical retrieval

### Input situation
A value is several hops away in CSO or in produced FBO, and users later want ancestor retrieval.

### Surface fit
Good as a two-stage pattern:

1. promotion of the long path to a direct property
2. index over that direct property with `ClosureRelation`

Current implementation supports that pattern within the current stack-depth limit.

---

## Use case 4 — CoverSpan-facing retrieval later

Ignoring sweep-line logic itself, Surface is still a good fit for making span attributes query-friendly before export into another persistence model.

That does not affect the X6 decision directly, but it supports the idea that Surface belongs **around** FBO as an acceleration layer.

---

## Final decision advice

## My recommendation after the triple-check

**Keep X6.**

And adopt this interpretation:

- Surface is **not** the CSO→FBO compiler
- Surface **is** the right mechanism for deterministic, governed, query-facing restatement before and after that compiler
- exact source-signature promotion into FBO should remain allowed
- lossy and inferential authored-signature projection should remain disallowed

That gives you all of the following at once:

- the ability to project into FBO
- support for complex traversal where the output is still just restatement
- efficient read models over produced FBO graphs
- no semantic blur between authored truth and generated approximations

---

## Bottom line

The enormous complexity of CSO → FBO does **not** show that X6 is too restrictive.
It shows that **Surface must not be mistaken for the whole projection compiler**.

The right conclusion is:

- **use a real compiler for CSO → FBO semantics**
- **use Surface wherever the job is deterministic restatement, flattening, indexing, closure, and governed query acceleration**
- **keep X6 so exact FBO projections stay possible while approximate ones do not masquerade as authored facts**
