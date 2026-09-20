<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Addendum: Capacity Model Runtime Performance for Financial Transactions

**Scope:** T-Box suitability and runtime-view design constraints for high-throughput financial transaction evaluation  
**Context:** Complements `capacity-domain-analysis-and-design.md`

---

## 1. Purpose

This addendum evaluates whether the current generic layering (`behaviour` + `quantification` + proposed `capacity`) is suitable for high-throughput financial transaction runtime.

It does not replace the generic ontology design.  
It defines the runtime constraints and an optimised semantic shape the projection layer should materialise for execution.

The core principle is:

> Keep generic source semantics rich and composable.  
> Execute on a compact, normalised runtime projection with bounded-hop lookups.

---

## 2. Design assumption

The canonical source graph remains generic, expressive, and provenance-complete.

A deterministic projection compiles source assertions into a runtime execution graph optimised for:

- low-latency admission checks,
- low-latency amount arithmetic,
- deterministic ordering,
- bounded traversal depth,
- stable key-based joins,
- efficient incremental invalidation.

This addendum focuses on **what that runtime T-Box should look like** for transaction processing.

---

## 3. Why this is needed

The generic model is semantically correct but can be expensive at runtime if used directly.

Typical expensive source-path patterns:

1. Demand → Draw → Resource → AllowanceDefinition → ValueSpace → Quantity conversion → account balance.
2. Resource → GuardDefinition → Eligibility profile → condition set → question set → decision.
3. Resource → Dependency node → source resource → source account → balance → target draw cap.
4. Draw decision requiring repeated compatibility checks across `qnt:Quantity`, `qnt:Value`, `qnt:ValueSpace`, optional conversions, and recurrence/reset state.
5. State-dependent activation requiring transition graph inspection in addition to balance checks.

If executed as-is over a general RDF store at transaction time, this introduces many joins and unpredictable latency under load.

Financial transaction systems require stable and tight latency envelopes. The runtime graph must therefore collapse multi-hop semantics into compact execution-ready structures.

---

## 4. Runtime hot paths to optimise

## 4.1 Admission hot path

For each incoming demand and candidate capacity resource:

1. Read effective admission status.
2. Read effective activation status.
3. Read effective bounded cap.
4. Decide eligible/not eligible in deterministic order.

### Runtime requirement

Admission decision should be executable in O(1) node fetch plus small bounded joins for dependency checks.

## 4.2 Allocation hot path

For each admitted resource:

1. Read current available balance.
2. Read request remainder.
3. Compute allocable amount = min(remainder, balance, bound cap).
4. Write draw record and new balance.

### Runtime requirement

No dynamic ValueSpace discovery at this stage.  
All quantities in the hot path must already be canonicalised to one execution unit per arrangement.

## 4.3 Governing-capacity hot path

For bounded/depleting relations:

1. Read governing resource execution balance.
2. Apply cap before draw.
3. Apply depletion after draw.

### Runtime requirement

Dependency semantics must be pre-typed and phase-separated, with numeric precedence available directly on the dependency edge node.

## 4.4 Reset and recurrence hot path

At processing boundary:

1. Determine whether reset applies.
2. If yes, restore balance according to policy.
3. Continue processing with deterministic ordering relative to pending draws.

### Runtime requirement

Runtime node must carry precomputed reset profile key and next-effective boundary metadata.  
No recurrence model traversal in the transaction loop.

## 4.5 Ordering hot path

Where multiple resources can serve a demand:

1. Resolve sequence deterministically.
2. Apply draw and dependency effects in that order.

### Runtime requirement

Single numeric sort key per executable relation and per executable resource path.  
No fallback to graph insertion order or lexical URI order.

---

## 5. Performance-oriented runtime T-Box profile

This section proposes a compact execution profile ontology for projection outputs.  
It is intentionally narrower than the source model.

Prefix used for illustration:

```turtle
@prefix capx: <https://www.nebularis.org/neuro-semantic/lattice/applied/capacity/execution#> .
```

## 5.1 Core runtime classes

### `capx:ExecutableArrangement`

Execution root containing only transaction-time required members.

### `capx:ExecutableResource`

Flattened runtime representation of a capacity resource, with prebound execution-space quantities and direct links to executable balances and dependency sets.

### `capx:ExecutableDemand`

Runtime demand record with canonical requested amount in execution space.

### `capx:ExecutableDraw`

Runtime draw event record with pre-normalised fields and deterministic status coding.

### `capx:ExecutableDependency`

Typed and phase-specific dependency between executable resources.

### `capx:ExecutableBalance`

Current mutable or append-only tracked balance object for one executable resource.

### `capx:ExecutableGuardState`

Pre-evaluated admission/activation state snapshot used in the transaction loop.

## 5.2 Required runtime properties (minimal hot-path surface)

### On `capx:ExecutableResource`

- `capx:resourceKey` (stable string key, unique within arrangement)
- `capx:maxCapacityAmount` (decimal)
- `capx:balanceRef` (`capx:ExecutableBalance`)
- `capx:executionSpaceKey` (string)
- `capx:admissionStateRef` (`capx:ExecutableGuardState`)
- `capx:priority` (integer)
- `capx:phaseBucket` (integer or enum)
- `capx:resetProfileKey` (string)
- `capx:activeFlag` (boolean snapshot, if policy allows snapshot-based activation)

### On `capx:ExecutableBalance`

- `capx:availableAmount` (decimal)
- `capx:lastUpdatedAt` (dateTime)
- `capx:balanceVersion` (integer or hash)
- `capx:nonNegativeInvariant` (implicit via shape, not necessarily stored)

### On `capx:ExecutableDependency`

- `capx:dependencyKind` (enum: `DepletesTarget`, `BoundsTarget`, `GatesTarget`)
- `capx:sourceResourceKey` (string)
- `capx:targetResourceKey` (string)
- `capx:precedence` (integer)
- `capx:phase` (enum: pre-draw, post-draw, activation)
- `capx:enabledFlag` (boolean snapshot)
- `capx:conditionKey` (optional, if conditional dependency supported)

### On `capx:ExecutableDemand`

- `capx:demandKey` (stable string)
- `capx:requestedAmount` (decimal)
- `capx:remainingAmount` (decimal)
- `capx:executionSpaceKey` (string)
- `capx:sequence` (integer)
- `capx:receivedAt` (dateTime)

### On `capx:ExecutableDraw`

- `capx:drawKey` (stable string)
- `capx:demandKey`
- `capx:resourceKey`
- `capx:requestedAmount` (decimal)
- `capx:allocatedAmount` (decimal)
- `capx:unmetAmount` (decimal)
- `capx:statusCode` (compact enum)
- `capx:executedAt` (dateTime)
- `capx:executionOrder` (integer)

### On `capx:ExecutableGuardState`

- `capx:admittedFlag` (boolean)
- `capx:activationFlag` (boolean)
- `capx:guardStateVersion` (hash or integer)
- `capx:evaluatedAt` (dateTime)

---

## 6. Normalisation strategy for runtime efficiency

## 6.1 Quantity flattening

For transaction-time evaluation:

- materialise canonical decimal amounts directly on runtime nodes,
- keep source `qnt:Quantity` objects for provenance and audit in the source graph,
- maintain explicit links from runtime decimals back to source quantity IRIs where needed for trace.

This avoids repeated `Quantity -> Value -> ValueSpace` expansion in hot loops.

## 6.2 Value-space canonicalisation

Per executable arrangement:

- define one execution space key for each compatible amount family,
- precompute all conversion paths at projection time,
- reject unresolved or ambiguous conversion at projection time, not runtime.

Hot path must perform no semantic conversion discovery.

## 6.3 Guard-state pre-evaluation

Eligibility and activation logic remain generic in source semantics.  
Projection materialises a runtime guard-state snapshot.

Transaction loop consumes booleans and versions, not full Eligibility graphs.

Where policy requires fully live guard recalculation per demand, recalc should be confined to targeted changed resources, not global re-evaluation.

## 6.4 Dependency phase separation

Materialise phase-specific dependency sets:

- pre-draw constraints (bounds),
- activation transitions (gates),
- post-draw depletion.

Do not infer phase from dependency type at runtime.

## 6.5 Key-based joins

All hot-path joins should be by compact stable keys (`resourceKey`, `demandKey`) rather than by long IRIs and repeated RDF term comparisons.

IRI links remain for semantic traceability but are not the primary runtime join surface.

## 6.6 Deterministic order fields

Store explicit numeric order for:

- resource traversal,
- dependency traversal,
- draw write ordering.

Never rely on graph store iteration order.

---

## 7. Runtime graph invariants

The runtime projection should enforce the following invariants by shape constraints and compile-time checks.

1. **Non-negativity**
   - max capacity, available balance, requested, allocated, unmet all >= 0.

2. **Bounded allocation**
   - allocated <= requested
   - allocated <= available pre-draw
   - allocated <= effective cap after pre-draw bounds.

3. **Conservation**
   - requested = allocated + unmet per draw.
   - per-demand conservation across multi-resource sequence.

4. **Space consistency**
   - demand and resource execution-space keys must match.
   - dependencies cannot cross incompatible execution-space keys.

5. **Deterministic ordering**
   - precedence unique per target per phase.
   - execution order total for all applicable dependencies.

6. **Acyclic phase graphs**
   - depleting graph acyclic in its phase.
   - gating graph acyclic in its phase.
   - union may contain structural opposites when phase-safe.

7. **Snapshot coherence**
   - guard-state version must match arrangement execution epoch used by transaction evaluator.

8. **Idempotency support**
   - draw keys unique.
   - repeat processing of same demand key under same epoch does not create duplicate effective allocation.

---

## 8. Financial-transaction suitability assessment

## 8.1 Fit

The current generic model is suitable as source semantics for financial transaction processing **if** runtime execution uses a compact projection profile like the one above.

Without projection, transaction throughput and latency predictability will degrade due to repeated multi-hop traversal and semantic joins.

## 8.2 Strengths already present

- Strong generic allowance/account core in Behaviour.
- Explicit recurrence hooks.
- Determinism-oriented policy constructs.
- Eligibility composition model.
- Quantification model that supports canonicalisation and conversion.
- Provenance and versioning foundations for auditable transaction traces.

## 8.3 Gaps for direct runtime use

- No compact execution-key surface.
- No first-class demand/draw runtime profile.
- No phase-tagged dependency execution contract.
- No direct max-capacity scalar on allowance definition.
- No runtime snapshot construct for guard state.
- No explicit hot-path oriented shape pack.

These are projection-profile gaps, not semantic-theory failures.

---

## 9. Recommended implementation path

## 9.1 Keep source semantics generic

Do not simplify `behaviour` or `quantification` to chase runtime speed.  
They are source-of-truth semantics and should remain expressive.

## 9.2 Add a Capacity Execution profile

Under `ontology/applied/capacity/execution/`, define:

- execution T-Box (`capacity-execution.ttl`),
- structural/constraint shapes,
- deterministic ordering constraints,
- quantity canonicalisation rules,
- invalidation policy and regeneration profile.

## 9.3 Compile from source to execution view

Projection compiler responsibilities:

1. Resolve and canonicalise quantities.
2. Materialise executable resources, balances, demands, dependencies.
3. Pre-evaluate or cache guard-state booleans with version keys.
4. Emit deterministic order indices.
5. Emit provenance pointers to source IRIs.
6. Reject ambiguous conversions and unresolved guards.

## 9.4 Keep bidirectional traceability

Every executable node should carry source references so transaction outcomes are auditable against source semantics.

Runtime compactness must not break explainability.

## 9.5 Test with transaction benchmark packs

Create benchmark fixtures for:

- high-frequency small draws,
- mixed accepted and denied demands,
- shared governing resource under heavy contention,
- reset boundary transitions,
- idempotent replay behavior.

Measure:

- hop count and join count per draw,
- p50/p95/p99 latency,
- deterministic replay equivalence,
- invalidation and regeneration scope.

---

## 10. Promotion criteria to Behaviour

A runtime construct in Capacity Execution should move into Behaviour only if:

1. it is generic across at least two non-financial and non-insurance domains,
2. it has a domain-neutral law and validation profile,
3. it reduces duplication in multiple applied layers,
4. it does not encode execution-engine-specific storage choices.

Likely long-term promotion candidates:

- generic executable balance snapshot pattern,
- generic phase-tagged dependency execution relation,
- generic demand-allocation execution record.

Not candidates:

- financial status codes,
- lending-specific drawdown semantics,
- insurance-specific admission dimensions,
- market-specific ordering policies.

---

## 11. Concrete addendum decisions

1. **Adopt projection-first runtime strategy** for Capacity transaction processing.
2. **Define `capx:` runtime profile** as a compact execution T-Box under `ontology/applied/capacity/execution`.
3. **Treat quantity canonicalisation as compile-time mandatory** for runtime-critical flows.
4. **Require deterministic ordering and phase separation** as runtime invariants.
5. **Retain source richness in Behaviour and Quantification** and avoid substrate simplification.
6. **Benchmark before broadening semantics** so performance decisions are evidence-led.

---

## 12. Summary

`behaviour` and `quantification` are suitable foundations for financial transaction handling, but not as direct transaction-time data shapes under load.

The right architecture is:

- rich generic source semantics,
- deterministic projection,
- compact normalised executable view,
- strict runtime invariants,
- full provenance back to source.

That gives both:

- semantic elegance and domain neutrality,
- transaction-grade performance and operational predictability.