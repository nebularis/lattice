<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Capacity Domain Ontology on LATTICE

## Analysis, boundary decision, and implementation design

## Decision in brief

A finite capacity is not a domain-specific thing.

A loan facility, insurance limit, cloud-service quota, credit line, inventory allocation, grant budget, emissions allowance, and access entitlement can all be understood as a finite resource that:

- is declared with a quantity and a value space,
- has a balance that changes over time,
- may be consumed by a demand,
- may reset or be replenished,
- may be subject to eligibility conditions,
- may activate, constrain, or deplete other capacity resources,
- can be governed by a deterministic allocation policy.

LATTICE already models much of this generic machinery in `ontology/behaviour/`:

- `bhv:AllowanceDefinition`
- `bhv:AllowanceAccount`
- `bhv:EffectDefinition`
- `bhv:EffectApplication`
- `bhv:State`, `bhv:StateSpace`, and `bhv:StateOccupancy`
- `bhv:TransitionDefinition`, triggers, and guards
- `bhv:Sequential` absorption
- `qnt:Quantity`, `qnt:ValueSpace`, and `qnt:Recurrence`
- `elg:AdmissionProfile`
- Foundation provenance, identity, versioning, and temporal scoping.

Behaviour does not yet provide a reusable semantic model for a **network of related finite resources**. In particular, it does not define a first-class demand, a capacity draw, a declared maximum capacity, or relations by which one resource activates, bounds, or depletes another.

Those concepts are not domain-specific, but neither should they be inserted into Behaviour merely because they are generic enough to imagine elsewhere. They should first be authored and tested in a thin `capacity` applied domain. Promotion into Behaviour should happen only after the generic law, validation surface, and non-insurance examples are stable.

The resulting architecture is:

```text
LATTICE substrate
  Foundation
  Vocabulary
  Quantification
  Party
  Eligibility
  Instrument
  Behaviour

Applied domains
  Capacity
  Insurance
    imports Capacity
  Lending
    imports Capacity
  SaaS subscription
    imports Capacity
  Other future domains

Private or deployment-specific work
  specific configuration
  scope dimensions and capital structures
  private ontologies
  Execution optimisations
  Proprietary mappings, corpora, and models
```

---

### Behaviour already has a generic allowance mechanism

Behaviour distinguishes declarations, occurrences, execution records, and durable state records. Its allowance surface already contains:

| Existing construct | Present role |
|---|---|
| `bhv:AllowanceDefinition` | Declared quota or allowance rule |
| `bhv:AllowanceAccount` | Durable balance record |
| `bhv:allowanceSpace` | Value space in which the allowance is measured |
| `bhv:availableBalance` | Current available quantity |
| `bhv:resetRecurrence` | Recurrence governing reset |
| `bhv:absorptionPolicy` | Consumption policy |
| `bhv:Sequential` | Usable sequential consumption policy |
| `bhv:EffectDefinition` | Declared cross-layer effect |
| `bhv:consumesAmount` | Quantity consumed by an effect |
| `bhv:usesAllowance` | Allowance used by an effect |
| `bhv:GuardDefinition` | Eligibility or policy guard |
| `bhv:requiresEligibility` | Link from a guard to an Eligibility admission profile |

This is already enough to model a simple generic quota:

```text
declared allowance
  → account with available balance
  → effect consumes a quantity
  → recurrence may reset the balance
```

That mechanism should remain in Behaviour. It has no insurance vocabulary and already appears suitable for domains such as subscriptions, employment benefits, lending, and access entitlements.

### Existing Behaviour does not yet model a capacity network

The current allowance surface does not answer several questions that arise as soon as multiple finite resources interact:

1. Which demand or request caused a particular draw?
2. Which resource supplied the draw?
3. What amount was allocated, refused, or left unmet?
4. What is the declared maximum capacity, distinct from the current balance?
5. Which resource bounds another resource's draw?
6. Which resource must be exhausted before another becomes active?
7. Which resource's consumption depletes a shared governing resource?
8. Which deterministic order applies when several eligible resources can respond?
9. Which eligibility profile applies to a particular resource or capacity relationship?

These are not all necessarily substrate concepts. They form the smallest coherent vocabulary for a domain in which finite resources are allocated to demands.

### The existing applied-domain boundary supports this approach

LATTICE already provides `ontology/applied/` for domain ontologies. Repository governance states that applied layers may contain concrete category sets, deployment-specific projections, applied theorems, and policy choices that should not enter the public substrate.

That is the correct place to begin. It avoids two opposite errors:

- baking a premature, partially understood capacity graph into Behaviour,
- leaving insurance to recreate generic resource mechanics under domain-specific names.

### Audit note

The current sequential allowance example asserts `bhv:targetsAllowance`, while the retrieved Behaviour core declaration clearly defines `bhv:usesAllowance` and `bhv:consumesAmount`. Before Capacity work begins, the Behaviour specification should be audited to confirm whether `bhv:targetsAllowance` is intentionally declared elsewhere or whether the example uses an undeclared property.

This is a small but important correctness issue. Capacity should build on one clear allowance targeting contract.

---

## Boundary analysis

### What belongs in Behaviour now

The following belong in Behaviour because they are mechanisms, not capacity-domain concepts.

| Mechanism | Why it belongs in Behaviour |
|---|---|
| State spaces, transitions, triggers, guards, and effects | Applies to any evolving system |
| Current and hypothetical state occupancy | Applies to any stateful subject |
| Allowance definition and allowance account | Generic quota and balance mechanism |
| Quantity and value-space compatibility | Generic Quantification composition |
| Sequential allocation policy | Generic way to consume finite allowances |
| Reset recurrence | Generic temporal recurrence mechanism |
| Eligibility as a transition or allocation guard | Generic Eligibility composition |
| Provenance of transitions and applied effects | Generic Foundation composition |
| Deterministic selection and activation policies | Generic Behaviour mechanism |

The public Behaviour layer should continue to use neutral terms such as allowance, account, balance, effect, and recurrence.

It should not introduce insurance terms such as claim, limit, retention, coverage, reinstatement premium, layer, deductible, aggregate, or peril.

### What should be built first in Capacity

The following concepts are reusable but need a coherent applied model before they can be considered for substrate promotion.

| Candidate Capacity concept | Why Behaviour cannot currently express it by wiring alone |
|---|---|
| Capacity resource | Behaviour has an allowance definition but no applied concept that distinguishes a finite allocable resource from an ordinary quota |
| Declared maximum capacity | Behaviour records an account's available balance but does not declare the resource's initial or maximum capacity |
| Demand | Behaviour has a generic stimulus, but no concept for a request that seeks allocation from one or more finite resources |
| Capacity draw | Behaviour has effect application, but no execution record that identifies demand, supplying resource, requested amount, allocated amount, and unmet amount together |
| Capacity dependency | Behaviour has transitions and effects, but no graph relation between two capacity resources |
| Governing capacity | A shared cap that bounds another resource's draw requires a resource-to-resource relation and explicit evaluation timing |
| Activation dependency | A downstream resource may become available only after an upstream resource reaches a defined state or balance |
| Capacity arrangement | A domain-level root that groups resources, demands, dependencies, rules, and execution traces |

These are plausible candidates for eventual promotion into Behaviour. They should remain in `ontology/applied/capacity/` until they have passed the promotion tests in §10.

### What belongs in Insurance, not Capacity

Capacity must not become a disguised FBO.

The following remain domain-domain concepts:

| Insurance concept | Why it does not belong in Capacity |
|---|---|
| Policy, coverage, exclusion, endorsement, clause, subjectivity | Governing instrument semantics |
| Claim as a legal or insurance event | Capacity can model a generic demand. A claim has domain-specific legal and operational meaning |
| Peril, territory, coverage type, line of business, asset class | Insurance vocabulary and risk classification |
| Retention, deductible, attachment point, excess layer | Insurance interpretation of resource ordering |
| Reinstatement premium | domain-specific commercial condition |
| Defence costs and defence treatment | Insurance coverage and cost-routing semantics |
| Claims-made, occurrence, discovery, run-off, tail cover | Insurance trigger and temporal semantics |
| Cover span and structural coverage gap | Insurance analysis outputs |
| Catastrophe scenario | Insurance or risk-modelling domain |
| Reinsurance recovery and contribution | Insurance and reinsurance semantics |
| Risk Capital Vehicle | Private capital-markets and domain-finance domain |
| Continuous liquidity product | Private financial-product domain |

Capacity can support all of these through composition. It must not define them.

### 4.4 What should remain private or deployment-specific

The public Capacity ontology should not publish the proprietary configuration that creates MERIDIAN's differentiation.

Keep private:

- the MERIDIAN twenty-dimension insurance scope model,
- any proprietary category partition or dimension completeness theorem,
- specific FBO evaluation profiles,
- domain-specific mapping rules from contractual terms to capacity networks,
- capital-structure and Risk Capital Vehicle ontology,
- continuous-liquidity product semantics,
- execution compiler internals where they contain non-obvious optimisation,
- production decisioning logic,
- curated wording library data,
- reviewed extraction corpus,
- scenario-generation methods,
- client mappings and client vocabulary bindings.

The public Capacity layer can establish the generic resource graph. It does not reveal a private deployment's dimensions, commercial policies, or analytical configuration.

---

## Design principles

### CP-1: Capacity is an applied domain, not a Behaviour synonym

Capacity imports and composes Behaviour. It does not rename Behaviour's existing concepts without adding semantic value.

### CP-2: A capacity resource is an allocable finite resource

A capacity resource is not merely a number and not merely an allowance definition. It is a declared finite resource that can be allocated to demands and whose available balance is tracked by an allowance account.

### CP-3: Demand is generic

A demand means a request for a quantity from one or more capacity resources.

A demand may later be specialised as:

- an insurance loss demand,
- a lending drawdown request,
- a service consumption request,
- an inventory reservation request,
- a grant payment request,
- a carbon-emissions usage request.

The Capacity layer does not decide which one it is.

### CP-4: Allocation records are first-class

A system must be able to answer:

- what requested capacity,
- from which resource,
- in what amount,
- under which rule,
- at what time,
- with what result,
- supported by what evidence.

An updated balance alone is not an adequate record.

### CP-5: Resource relations are explicit and typed

If one resource constrains, activates, or depletes another, that relation must be represented as a distinct node with source, target, kind, precedence, and eligibility or trigger conditions.

A plain edge loses provenance, versioning, temporal scope, and rule identity.

### CP-6: Capacity has no business vocabulary

`capacity/vocab/` may contain only mechanism-intrinsic dependency kinds and allocation statuses. It must not contain insurance, lending, or capital-market categories.

Business classifications bind through `voc:SchemeContract`.

### CP-7: Behaviour remains execution-neutral

The ontology declares the semantics and validation requirements. It does not require a particular compiler, graph database, reasoner, simulator, or optimisation strategy.

### CP-8: Deterministic semantics precede optimisation

No runtime engine should claim deterministic capacity allocation until the corresponding graph constraints are expressed and tested.

### CP-9: Promotion is earned

A capacity construct moves into Behaviour only after it is demonstrated to be generic, independently motivated, formally constrained, and supported by at least two non-domain examples.

---

## Proposed applied ontology

## Package location

```text
ontology/applied/
└── capacity/
    ├── README.md
    ├── spec/
    │   └── capacity.ttl
    ├── shapes/
    │   ├── structural.ttl
    │   ├── constraints.ttl
    │   └── rules.ttl
    ├── vocab/
    │   └── capacity-vocab.ttl
    ├── projection/
    │   ├── behaviour.ttl
    │   ├── eligibility.ttl
    │   ├── quantification.ttl
    │   ├── instrument.ttl
    │   └── party.ttl
    ├── execution/
    │   └── invalidation-policy.md
    ├── ontology/examples/
    │   ├── lending-facility.ttl
    │   ├── service-quota.ttl
    │   ├── inventory-reservation.ttl
    │   └── domain-limit-minimal.ttl
    └── test/
        ├── capacity-structural-valid.ttl
        ├── capacity-negative-balance.ttl
        ├── capacity-incompatible-space.ttl
        ├── capacity-dependency-cycle.ttl
        ├── capacity-precedence-collision.ttl
        └── capacity-governing-limit.ttl
```

The package should follow LATTICE's literate-spec convention. Its `README.md` is authoritative. Compiled Turtle, shapes, vocabulary, and tests are mechanically derived or verified against it.

## Namespace

```turtle
@prefix cap: <https://www.nebularis.org/neuro-semantic/lattice/applied/capacity#> .
```

The namespace must not use `fbo:`, `ctr:`, `apex:`, `MERIDIAN:`, or any employer-owned namespace.

## Imports

Capacity should import:

```text
Foundation
Vocabulary
Quantification
Party
Eligibility
Behaviour
Instrument
```

Instrument is imported because a capacity arrangement may be established by a governing instrument and because an applied domain will commonly connect resources to provisions and obligations. Capacity itself should not require every resource to arise from a contract.

This distinction allows the same model to represent:

- a contractual lending facility,
- a policy limit,
- a SaaS plan quota,
- a physical inventory allocation,
- an operational resource pool.

## Core classes

### `cap:CapacityArrangement`

A versioned root for a coherent set of capacity resources, dependencies, demand rules, and allocation records.

Examples:

- a credit facility arrangement,
- a policy-limit arrangement,
- a subscription entitlement plan,
- an inventory allocation plan.

It should be a versioned, evidenced resource and may be temporally scoped.

```text
cap:CapacityArrangement
  ⊑ fnd:Version
  ⊓ fnd:Evidenced
  ⊓ fnd:TemporallyScoped
```

### `cap:CapacityResource`

A declared finite resource made available for allocation.

It subclasses `bhv:AllowanceDefinition`, rather than recreating allowance semantics.

```text
cap:CapacityResource
  ⊑ bhv:AllowanceDefinition
  ⊓ fnd:Evidenced
  ⊓ cap:hasMaximumCapacity exactly 1 qnt:Quantity
  ⊓ cap:partOfArrangement exactly 1 cap:CapacityArrangement
```

A CapacityResource has:

- a declared maximum capacity,
- one value space inherited through its allowance definition,
- an absorption policy inherited through Behaviour,
- zero or more linked accounts,
- zero or more admission guards,
- zero or more declared dependencies.

It does not imply money. A capacity resource may be measured in money, units, hours, emissions units, service calls, or any other declared `qnt:ValueSpace`.

### `cap:CapacityDemand`

A stimulus that requests allocation from one or more capacity resources.

```text
cap:CapacityDemand
  ⊑ bhv:Stimulus
  ⊓ cap:requestsAmount exactly 1 qnt:Quantity
```

CapacityDemand deliberately has no domain-specific properties. Domain layers add their own facts.

Examples:

- `lend:DrawdownRequest`,
- `ins:LossDemand`,
- `saas:ServiceUsageRequest`,
- `inventory:ReservationRequest`.

### `cap:CapacityDraw`

An evidenced execution record of an allocation attempt or allocation outcome.

```text
cap:CapacityDraw
  ⊑ fnd:Evidenced
  ⊓ cap:forDemand exactly 1 cap:CapacityDemand
  ⊓ cap:fromResource exactly 1 cap:CapacityResource
  ⊓ cap:requestedAmount exactly 1 qnt:Quantity
  ⊓ cap:allocatedAmount exactly 1 qnt:Quantity
  ⊓ cap:drawStatus exactly 1 cap:DrawStatus
```

A draw records an amount allocated from one resource to one demand. It is distinct from:

- the declared resource,
- the account balance,
- the transition that authorises the draw,
- the effect application that updates the balance.

A CapacityDraw may reference the relevant `bhv:TransitionExecution` and `bhv:EffectApplication`.

### `cap:CapacityDependency`

A versioned, evidenced declaration relating two CapacityResources.

```text
cap:CapacityDependency
  ⊑ fnd:Version
  ⊓ fnd:Evidenced
  ⊓ fnd:TemporallyScoped
  ⊓ cap:dependencySource exactly 1 cap:CapacityResource
  ⊓ cap:dependencyTarget exactly 1 cap:CapacityResource
  ⊓ cap:dependencyKind exactly 1 cap:DependencyKind
  ⊓ cap:dependencyPrecedence exactly 1 xsd:integer
```

The dependency is a node rather than a binary relation because it may need:

- provenance,
- temporal scope,
- versioning,
- a priority,
- a declared guard,
- a trigger,
- a source provision,
- a mapping record,
- a reason for exclusion or override.

### `cap:CapacityRule`

A declared rule governing admission, allocation, reset, or dependency evaluation.

This class is optional for the initial release. It should exist only if the first implementation needs a reusable binding between Capacity concepts and Behaviour transition definitions.

A conservative first model is:

```text
cap:CapacityRule
  ⊑ fnd:Version
  ⊓ fnd:Evidenced
```

The rule may reference:

- `bhv:TransitionDefinition`,
- `bhv:GuardDefinition`,
- `elg:AdmissionProfile`,
- `bhv:EffectDefinition`.

Capacity should not duplicate these underlying mechanisms.

---

## Core properties

| Property | Domain | Range | Purpose |
|---|---|---|---|
| `cap:hasCapacityResource` | CapacityArrangement | CapacityResource | Includes a declared resource in an arrangement |
| `cap:partOfArrangement` | CapacityResource | CapacityArrangement | Inverse of `hasCapacityResource` |
| `cap:hasMaximumCapacity` | CapacityResource | `qnt:Quantity` | Declared maximum or initial available capacity |
| `cap:hasCapacityAccount` | CapacityResource | `bhv:AllowanceAccount` | Links resource declaration to balance record |
| `cap:admittedBy` | CapacityResource | `bhv:GuardDefinition` | Declares a Behaviour guard controlling resource use |
| `cap:forDemand` | CapacityDraw | CapacityDemand | Identifies the request being considered |
| `cap:fromResource` | CapacityDraw | CapacityResource | Identifies the resource being drawn |
| `cap:requestedAmount` | CapacityDemand or CapacityDraw | `qnt:Quantity` | Demand or draw amount requested |
| `cap:allocatedAmount` | CapacityDraw | `qnt:Quantity` | Amount allocated |
| `cap:unmetAmount` | CapacityDraw | `qnt:Quantity` | Unallocated remainder, if recorded |
| `cap:drawStatus` | CapacityDraw | `cap:DrawStatus` | Outcome of the allocation attempt |
| `cap:appliesEffect` | CapacityDraw | `bhv:EffectApplication` | Links draw to the applied effect |
| `cap:executedBy` | CapacityDraw | `bhv:TransitionExecution` | Links draw to authorising execution |
| `cap:hasDependency` | CapacityArrangement | CapacityDependency | Includes a resource relation |
| `cap:dependencySource` | CapacityDependency | CapacityResource | Source resource |
| `cap:dependencyTarget` | CapacityDependency | CapacityResource | Target resource |
| `cap:dependencyKind` | CapacityDependency | `cap:DependencyKind` | Mechanism-intrinsic relation kind |
| `cap:dependencyPrecedence` | CapacityDependency | `xsd:integer` | Deterministic ordering among dependencies |
| `cap:governedBy` | CapacityResource | CapacityResource | Derived convenience relation only, never authoritative |
| `cap:hasCapacityRule` | CapacityArrangement | CapacityRule | Associates rules with an arrangement |

Every quantity attached to one CapacityDraw or CapacityResource must be in the same declared value space or connected through an explicit Quantification conversion.

---

## Mechanism vocabulary

The first Capacity vocabulary should remain deliberately small.

```turtle
cap:DependencyKind a owl:Class .
cap:DrawStatus a owl:Class .

cap:DepletesTarget a cap:DependencyKind .
cap:GatesTarget a cap:DependencyKind .
cap:BoundsTarget a cap:DependencyKind .

cap:Allocated a cap:DrawStatus .
cap:PartiallyAllocated a cap:DrawStatus .
cap:Denied a cap:DrawStatus .
cap:Unavailable a cap:DrawStatus .
cap:Undetermined a cap:DrawStatus .
```

### `cap:DepletesTarget`

A draw from the source resource reduces the available balance of the target resource.

This models a shared or governing resource that is consumed by draws from another resource.

Examples:

- a lending sublimit consumes an overall facility,
- a service feature quota consumes an account-level quota,
- an insurance occurrence limit consumes an aggregate resource.

The Capacity layer does not name any of those business interpretations.

### `cap:GatesTarget`

The source resource's state or balance is a precondition for target resource activation.

Examples:

- a secondary facility becomes available only after a primary facility is exhausted,
- a backup quota becomes active only after ordinary quota is depleted,
- an excess insurance layer becomes reachable after the preceding resource has absorbed the relevant amount.

### `cap:BoundsTarget`

The source resource's available balance caps the draw that the target resource may make.

This is materially different from depletion. A target can be capable of allocating an amount in isolation but is bounded by the remaining capacity of a governing resource.

Examples:

- a revolving credit subfacility is capped by remaining total commitment,
- a departmental budget line is capped by remaining central budget,
- an occurrence limit is capped by an annual aggregate.

The distinction between `DepletesTarget` and `BoundsTarget` is necessary. A resource that is merely depleted after a draw does not necessarily limit the draw that has already happened.

### Deferred dependency kinds

The first Capacity release should not include broad or underspecified relation types such as:

- `OverridesTarget`,
- `SharesWithTarget`,
- `OffsetsTarget`,
- `RecoversFromTarget`,
- `TransfersToTarget`,
- `ReinstatesTarget`.

These may be valid generic concepts, but they need separate laws, examples, and tests. They should not be included because they appeared in FBO.

---

## Generic Capacity execution semantics

Capacity defines the domain model. Behaviour defines transitions and effects. An execution profile may implement the following process.

For a demand `d`:

1. Select CapacityResources in the relevant CapacityArrangement.
2. Evaluate each resource's Behaviour guard, which may call an Eligibility admission profile.
3. Exclude resources whose guards deny or leave eligibility undetermined, according to the declared policy.
4. Determine a deterministic resource order.
5. For each eligible resource:
   - determine the resource's available balance,
   - apply applicable `BoundsTarget` dependencies before allocation,
   - allocate no more than the demand remainder and permitted draw cap,
   - record a CapacityDraw,
   - apply the resulting Behaviour effect to the resource account,
   - apply `DepletesTarget` dependencies,
   - evaluate `GatesTarget` dependencies at their declared point.
6. Record any remaining unmet amount.
7. Preserve all transition, effect, draw, and account evidence.

This is a reference semantic model, not a requirement that every deployment use one runtime architecture.

The Capacity layer should not state insurance arithmetic, claim settlement, payment authority, premium effects, or accounting treatment.

---

## Generic laws and validation requirements

The first Capacity release should be small but law-governed.

## Quantity compatibility

A CapacityDraw is valid only if:

- requested amount,
- allocated amount,
- unmet amount when present,
- source resource maximum capacity,
- source account available balance,

are on the same `qnt:ValueSpace`, or are connected by an explicit valid conversion.

This prevents the silent comparison of incompatible quantities such as currency and hours.

## Non-negativity

For every CapacityResource and CapacityDraw:

```text
maximum capacity ≥ 0
requested amount ≥ 0
allocated amount ≥ 0
unmet amount ≥ 0
available balance ≥ 0
```

No execution profile may create a negative available balance.

## Allocation bound

For each CapacityDraw:

```text
allocated amount ≤ requested amount
allocated amount ≤ available balance before draw
allocated amount ≤ effective draw cap
```

The effective draw cap is the minimum applicable bound after evaluating `BoundsTarget` dependencies.

## Demand conservation

For a fully evaluated demand in one value space:

```text
requested amount = Σ allocated amounts + unmet amount
```

This is a generic conservation law.

It applies whether the demand is:

- a loan drawdown,
- a cloud quota request,
- a stock reservation,
- an insurance loss demand.

The public Capacity layer should prove and test the law without using any insurance example.

## Deterministic dependency order

Dependencies with a shared target must have a total order when their application is order-sensitive.

At minimum:

- `cap:dependencyPrecedence` is required,
- two distinct applicable dependencies with the same target must not have the same precedence,
- ties must either be rejected or resolved by a declared deterministic identity ordering.

## Phase-restricted acyclicity

The FBO material correctly identified that not all capacity-resource relations should be tested in one combined graph.

Capacity should distinguish at least two derived graph views:

```text
depletion graph
  source → target for DepletesTarget

gating graph
  source → target for GatesTarget and BoundsTarget
```

Each graph must be acyclic within its own evaluation phase.

The union of the two graphs need not be acyclic. A governing capacity may be depleted by a subordinate resource while simultaneously bounding that subordinate resource. Rejecting that configuration as a simple graph cycle would make a common and generic capacity pattern inexpressible.

This is a generic Capacity law. It is not domain-specific.

## Activation state

A CapacityResource with an incoming `GatesTarget` dependency must not be assumed active merely because it is eligible.

Its activation must be determined by the relevant Behaviour state and declared gating rule.

This prevents the generic analogue of an excess layer responding before the prerequisite resource is exhausted.

## Reset scope

The initial Capacity release should use Behaviour's existing `bhv:resetRecurrence` but should not specify advanced restoration semantics.

The following remain explicitly deferred:

- restoration above declared maximum capacity,
- partial or capped restoration,
- ordering of reset and a pending allocation,
- retrospective demands,
- carry-over policy across reset boundaries,
- multiple reset rules on one resource,
- interaction between reset and gated activation.

Those are generic capacity questions. They should be developed through non-insurance examples before any substrate promotion.

---

## Use Cases

## Lending facility

### Model

A borrower has:

- a total revolving facility of 10,000,000,
- a subfacility for working capital of 4,000,000,
- a subfacility for acquisitions of 6,000,000.

The working-capital and acquisition resources both deplete and are bounded by the total facility.

### Capacity mapping

| Lending notion | Capacity concept |
|---|---|
| Revolving facility | `cap:CapacityResource` |
| Subfacility | `cap:CapacityResource` |
| Drawdown request | `cap:CapacityDemand` |
| Facility availability condition | `bhv:GuardDefinition` plus `elg:AdmissionProfile` |
| Total commitment cap | `cap:BoundsTarget` dependency |
| Total commitment reduction | `cap:DepletesTarget` dependency |
| Borrower covenant breach | Lending-specific Behaviour state and Eligibility condition |
| Cure period | Lending-specific transition and temporal guard |
| Drawdown allocation | `cap:CapacityDraw` |

### Why Capacity adds value

Behaviour alone can represent an allowance and a balance. It does not naturally represent that one drawdown:

- draws from a specific subfacility,
- is constrained by a total facility,
- reduces that total facility,
- leaves an evidenced allocation trace,
- may be denied because a covenant-related eligibility guard fails.

Capacity supplies the resource-network model. Lending supplies covenant, borrower, facility, and breach semantics.

## SaaS subscription quota

### Model

A customer plan grants:

- 10,000 API calls per day,
- 1,000 premium API calls per day,
- premium calls also consume the 10,000 total-call allowance,
- a paid overage resource becomes available only when the included allowance is exhausted.

### Capacity mapping

| SaaS notion | Capacity concept |
|---|---|
| Included calls | `cap:CapacityResource` |
| Premium call quota | `cap:CapacityResource` |
| API request | `cap:CapacityDemand` |
| Overall plan quota | `cap:CapacityResource` |
| Premium usage consuming total quota | `cap:DepletesTarget` |
| Premium draw capped by overall quota | `cap:BoundsTarget` |
| Overage activation | `cap:GatesTarget` |
| Daily reset | `bhv:resetRecurrence` |
| Entitlement checks | `bhv:GuardDefinition` and Eligibility |

No insurance vocabulary is required.

## Inventory reservation

### Model

A distributor has:

- a national inventory pool,
- warehouse-specific inventory allocations,
- a priority customer reserve,
- an ordinary fulfilment capacity that must not consume the priority reserve,
- a backorder process activated when ordinary stock is unavailable.

### Capacity mapping

| Inventory notion | Capacity concept |
|---|---|
| Inventory pool | `cap:CapacityResource` |
| Order reservation | `cap:CapacityDemand` |
| Warehouse allocation | `cap:CapacityResource` |
| National inventory cap | `cap:BoundsTarget` |
| Stock reduction | `cap:DepletesTarget` |
| Backorder availability | `cap:GatesTarget` |
| Customer priority | Eligibility and Behaviour selection policy |
| Reservation trace | `cap:CapacityDraw` |

Again, the capacity graph is generic. Inventory ownership, shipping, backorders, and product catalogues belong to a future inventory domain.

## Minimum acceptance condition

Capacity is ready for public release only when at least two non-insurance examples pass all structural and behavioural validations. Lending and SaaS should be the initial pair because they exercise:

- monetary and non-monetary spaces,
- reset recurrence,
- shared governing capacity,
- eligibility guards,
- activation dependencies,
- deterministic sequential allocation.

---

## Reimagining insurance on Capacity

## The public insurance layer should import Capacity

The public insurance applied layer should not introduce `InsuranceTank`, `LayerTank`, or equivalent constructs as primitive classes.

Instead:

```text
ontology/applied/insurance
  imports ontology/applied/capacity
  imports Instrument
  imports Party
  imports Eligibility
  imports Quantification
  imports Behaviour
```

Insurance then specialises generic Capacity concepts.

```text
ins:InsuranceCapacityResource
  ⊑ cap:CapacityResource

ins:LossDemand
  ⊑ cap:CapacityDemand

ins:InsuranceCapacityDraw
  ⊑ cap:CapacityDraw
```

This establishes the correct abstraction:

```text
insurance limit
  is a capacity resource

retention
  is a capacity resource with an insurance allocation role

aggregate
  is a capacity resource whose relationship to other resources
  is expressed through generic dependency kinds

claim or loss demand
  is an domain-specific kind of capacity demand

tower or programme
  is an domain-specific arrangement of resources,
  provisions, party structures, and eligibility conditions
```

## What insurance adds

Insurance must add concepts that Capacity intentionally does not know:

- coverage grant,
- exclusion,
- insured interest,
- peril,
- insured party,
- beneficiary,
- loss event,
- retention,
- deductible,
- premium,
- policy period,
- claims basis,
- reinstatement terms,
- reinsurance role,
- attachment interpretation,
- domain-specific aggregation,
- scenario and exposure concepts.

The public insurance layer may use generic Capacity dependencies, but its own mapping rules and analytical profiles must be distinguished from the Capacity base.

## The FBO decomposition

The original FBO can be decomposed as follows.

| FBO construct or concern | Destination |
|---|---|
| Finite resource and balance | Behaviour plus Capacity |
| Capacity tank declaration | `cap:CapacityResource` |
| Tank state | `bhv:AllowanceAccount` and Behaviour state |
| Claim as a probe | `ins:LossDemand` extending `cap:CapacityDemand` |
| Scenario | Insurance analysis layer or private MERIDIAN extension |
| Scope qualifier mechanics | Eligibility plus private or domain-specific projection |
| Twenty insurance dimensions | Private MERIDIAN or a future public insurance profile, not Capacity |
| Peril and territory hierarchies | Insurance vocabulary contracts |
| Flow graph | Capacity dependencies where genuinely generic |
| domain-specific flow meanings | Insurance layer |
| Cover span | Insurance analytical output |
| Structural gap detection | Insurance analysis service or private extension |
| Reinstatement premium and collateral semantics | Insurance or capital-market layer |
| Execution shadows and runtime compiler | Execution implementation, not ontology requirement |

This is not a claim that the existing FBO is wrong. It is a refactoring claim:

> The FBO contains a generic capacity kernel, an insurance domain model, and a proprietary execution and analysis profile. Those should not be published or maintained as one indivisible ontology.

## What should not be ported automatically

The following FBO material should not move into Capacity merely because it is already designed:

- the named twenty-dimension qualifier,
- the fixed partition into insurance applicability, flow modulation, and state gating,
- claim-specific accessors,
- insurance scope vocabulary,
- defence-cost handling,
- policy trigger modes,
- cover-span interval semantics,
- scenario-conditioned coverage findings,
- domain-specific reset rules,
- reinsurance recovery classifications,
- catastrophe vocabulary,
- capital and collateral configuration.

Each may later inform an insurance or private extension. None belongs in a public generic Capacity ontology without independent justification.

---

## Behaviour promotion protocol

Capacity is a proving ground for potentially generic mechanisms.

A construct should move from `ontology/applied/capacity/` to `ontology/behaviour/` only when all of the following are true.

### Genericity test

The construct can be defined without referring to:

- insurance,
- lending,
- SaaS,
- inventory,
- finance,
- a specific industry,
- a named product,
- a specific commercial policy.

### Multiple-domain test

The construct is exercised by at least two non-domain examples from materially different applied domains.

For example:

| Candidate | Required examples |
|---|---|
| Capacity draw | lending drawdown and SaaS quota usage |
| Governing-capacity relation | lending total commitment and inventory central stock |
| Activation dependency | SaaS overage activation and inventory backorder activation |
| Proportional allocation | at least two non-insurance allocation cases |
| Balance restoration semantics | at least two domains with distinct reset requirements |

### Formal-law test

The construct has:

- a precise definition,
- declared preconditions,
- at least one invariant or law,
- positive and negative test fixtures,
- SHACL constraints where graph validation is appropriate,
- execution-profile independence.

### Architectural test

Promotion must simplify downstream domains without creating an upward dependency from Behaviour to an applied layer.

The promoted term must depend only on existing substrate layers.

### Governance test

The term has passed an ADR documenting:

- the generic premise,
- the non-domain evidence,
- the law,
- the boundary with Capacity,
- migration consequences,
- compatibility policy.

### Likely promotion candidates

The following are likely but not guaranteed to move into Behaviour later:

| Candidate | Initial home | Promotion status |
|---|---|---|
| Maximum allowance or capacity | Capacity | Candidate after non-domain proof |
| Allocation execution record | Capacity | Candidate after non-domain proof |
| Generic resource dependency | Capacity | Candidate after law and phase model stabilise |
| Governing balance constraint | Capacity | Candidate after non-domain proof |
| Activation-by-resource-state | Capacity | Candidate after non-domain proof |
| Proportional allocation | Behaviour vocabulary already exists | Remains deferred until existing prerequisites are met |
| Advanced reset semantics | Behaviour | Remains deferred until law and examples exist |

### Explicit non-promotion candidates

The following must not move into Behaviour:

- claim,
- coverage,
- insured,
- lender,
- borrower,
- policy,
- facility,
- deductible,
- covenant,
- peril,
- aggregate,
- attachment point,
- reinstatement premium,
- capital tranche,
- collateral type.

These are applied-domain concepts even where they compose with generic capacity mechanisms.

---

## Validation design

## Structural shapes

The initial `capacity/shapes/structural.ttl` should enforce:

### CapacityResource

- exactly one `cap:hasMaximumCapacity`,
- exactly one `bhv:allowanceSpace`,
- exactly one `bhv:absorptionPolicy`,
- exactly one `cap:partOfArrangement`,
- zero or more `cap:hasCapacityAccount`,
- quantity compatibility between maximum capacity and allowance space.

### CapacityDemand

- exactly one `cap:requestsAmount`,
- requested amount in a declared value space,
- non-negative requested amount.

### CapacityDraw

- exactly one demand,
- exactly one resource,
- exactly one requested amount,
- exactly one allocated amount,
- exactly one status,
- allocated amount in the resource allowance space,
- requested amount and allocated amount in compatible spaces.

### CapacityDependency

- exactly one source,
- exactly one target,
- exactly one dependency kind,
- exactly one precedence,
- source and target must differ,
- source and target must belong to the same CapacityArrangement unless an explicit cross-arrangement profile permits otherwise.

## Graph constraints

The initial `capacity/shapes/constraints.ttl` should enforce:

1. Maximum capacity is non-negative.
2. Available balance is non-negative.
3. Allocation is non-negative.
4. Allocation does not exceed request.
5. Allocation does not exceed available balance at evaluation time where an execution state is available.
6. Resource and draw quantities use compatible spaces.
7. Dependency precedence is unique per target and evaluation phase.
8. Depletion graph is acyclic.
9. Gating graph is acyclic.
10. A `BoundsTarget` dependency is evaluated before target allocation.
11. A CapacityDraw with status `Allocated` has no unmet amount greater than zero.
12. A CapacityDraw with status `Denied` or `Unavailable` has allocated amount zero.
13. A CapacityDraw marked `Undetermined` is not silently treated as allocated or denied.

## Rules

The initial `capacity/shapes/rules.ttl` may materialise only safe derived facts:

- derived effective draw cap,
- convenience `cap:governedBy` relation from a dependency,
- derived draw status where arithmetic and eligibility results are complete,
- total unmet amount where all allocation records are present.

Rules must not:

- invent a demand,
- infer commercial authority,
- infer an insurance claim,
- choose between ambiguous resources,
- apply an undeclared conversion,
- conceal an Eligibility result of `Undetermined`.

## Deliberate-defect fixtures

At minimum, include fixtures for:

| Fixture | Failure demonstrated |
|---|---|
| Negative capacity | Resource violates non-negativity |
| Negative balance | Account violates non-negativity |
| Currency versus unit mismatch | Quantity compatibility violation |
| Over-allocation | Allocated amount exceeds request or balance |
| Missing dependency precedence | Deterministic evaluation cannot be established |
| Precedence collision | Two applicable dependencies conflict |
| Depletion cycle | Resource graph cannot be evaluated safely |
| Gating cycle | Activation graph cannot be evaluated safely |
| Early activation | Gated resource used before condition is satisfied |
| Governing capacity omission | Resource depletes a total cap but is not bounded by it |
| Undetermined eligibility coerced to approval | Three-valued decision handling violation |

---

## Implementation sequence

## Phase 0: confirm and repair the Behaviour contract

Before creating Capacity:

1. Audit `bhv:targetsAllowance` against `bhv:usesAllowance`.
2. Confirm the intended relationship between:
   - EffectDefinition,
   - EffectApplication,
   - AllowanceDefinition,
   - AllowanceAccount,
   - consumed quantity.
3. Confirm the status of `bhv:Sequential`.
4. Leave proportional absorption and advanced reset semantics deferred.
5. Add parser and SHACL checks if they do not already cover the relevant allowance examples.

**Exit criterion:** one unambiguous Behaviour contract for consuming a declared allowance and updating a tracked balance.

## Phase 1: author the minimal Capacity ontology

Create:

- `cap:CapacityArrangement`,
- `cap:CapacityResource`,
- `cap:CapacityDemand`,
- `cap:CapacityDraw`,
- `cap:CapacityDependency`,
- maximum-capacity property,
- draw properties,
- the three dependency kinds,
- structural shapes,
- quantity and non-negativity constraints,
- one simple sequential allocation rule.

Do not add insurance classes.

**Exit criterion:** a single resource can allocate capacity to one demand and record the result with provenance.

## Phase 2: prove shared-capacity semantics in non-insurance domains

Author and test:

1. Lending facility example.
2. SaaS quota example.
3. Inventory or grant-budget example.

Exercise:

- `DepletesTarget`,
- `BoundsTarget`,
- `GatesTarget`,
- reset recurrence,
- eligibility guards,
- sequential allocation,
- unmet demand,
- deterministic precedence.

**Exit criterion:** at least two materially different non-insurance examples pass all Capacity validation and execution-reference tests.

## Phase 3: harden graph laws

Implement:

- phase-restricted acyclicity,
- precedence uniqueness,
- allocation conservation,
- account balance constraints,
- execution trace completeness,
- dependency-local invalidation guidance.

**Exit criterion:** deliberate defects fail predictably and valid examples remain stable under re-execution.

## Phase 4: refactor the public insurance layer

Replace the current minimal insurance validation package's direct use of Behaviour allowances with Capacity imports.

The public insurance package should:

- subclass CapacityResource for generic insurance capacity,
- subclass CapacityDemand for loss demand,
- demonstrate policy limits and retentions as capacity resources,
- demonstrate a simple ordered resource arrangement,
- use Eligibility for a non-proprietary admission example,
- avoid MERIDIAN-specific scope dimensions, tower concepts, and proprietary terminology.

**Exit criterion:** the insurance example becomes simpler because it consumes Capacity rather than recreating resource-network semantics.

## Phase 5: private MERIDIAN refactoring study

Outside the public LATTICE repository, assess the proprietary FBO against the Capacity layer.

Classify every FBO term as:

1. retained private,
2. mapped to Behaviour,
3. mapped to Capacity,
4. mapped to public Insurance,
5. candidate for later generic promotion,
6. obsolete duplication.

Do not copy the FBO source into the public repository. Produce a private mapping and equivalence analysis.

**Exit criterion:** a documented private migration path from FBO concepts to the layered LATTICE architecture.

## Phase 6: promotion review

Only after Phase 2 and Phase 3 should the team consider promoting any Capacity concept to Behaviour.

The first likely candidate is a generic allocation-execution record. The second is a generic resource-dependency mechanism.

No promotion should be made merely to make the ontology tree look elegant.

---

## Proposed initial public examples

## Lending facility

```turtle
@prefix cap: <https://www.nebularis.org/neuro-semantic/lattice/applied/capacity#> .
@prefix bhv: <https://www.nebularis.org/neuro-semantic/lattice/behaviour#> .
@prefix qnt: <https://www.nebularis.org/neuro-semantic/lattice/quantification#> .
@prefix ex:  <https://example.org/lattice/capacity/lending/> .

ex:total-facility a cap:CapacityResource ;
    cap:hasMaximumCapacity ex:amount-10m ;
    bhv:allowanceSpace ex:usd-space ;
    bhv:absorptionPolicy bhv:Sequential .

ex:working-capital-facility a cap:CapacityResource ;
    cap:hasMaximumCapacity ex:amount-4m ;
    bhv:allowanceSpace ex:usd-space ;
    bhv:absorptionPolicy bhv:Sequential .

ex:working-capital-bounds-total a cap:CapacityDependency ;
    cap:dependencySource ex:total-facility ;
    cap:dependencyTarget ex:working-capital-facility ;
    cap:dependencyKind cap:BoundsTarget ;
    cap:dependencyPrecedence 10 .

ex:working-capital-depletes-total a cap:CapacityDependency ;
    cap:dependencySource ex:working-capital-facility ;
    cap:dependencyTarget ex:total-facility ;
    cap:dependencyKind cap:DepletesTarget ;
    cap:dependencyPrecedence 20 .

ex:drawdown-request-1 a cap:CapacityDemand ;
    cap:requestsAmount ex:amount-1m .

ex:drawdown-1 a cap:CapacityDraw ;
    cap:forDemand ex:drawdown-request-1 ;
    cap:fromResource ex:working-capital-facility ;
    cap:requestedAmount ex:amount-1m ;
    cap:allocatedAmount ex:amount-1m ;
    cap:drawStatus cap:Allocated .
```

The two dependencies are not contradictory. The first limits the subfacility's draw by the total facility. The second ensures that an allocated draw reduces the total facility's remaining availability.

## SaaS overage

```turtle
@prefix cap: <https://www.nebularis.org/neuro-semantic/lattice/applied/capacity#> .
@prefix bhv: <https://www.nebularis.org/neuro-semantic/lattice/behaviour#> .
@prefix ex:  <https://example.org/lattice/capacity/saas/> .

ex:included-calls a cap:CapacityResource ;
    cap:hasMaximumCapacity ex:calls-10000 ;
    bhv:allowanceSpace ex:api-call-space ;
    bhv:absorptionPolicy bhv:Sequential ;
    bhv:resetRecurrence ex:daily-reset .

ex:paid-overage a cap:CapacityResource ;
    cap:hasMaximumCapacity ex:calls-100000 ;
    bhv:allowanceSpace ex:api-call-space ;
    bhv:absorptionPolicy bhv:Sequential .

ex:included-before-overage a cap:CapacityDependency ;
    cap:dependencySource ex:included-calls ;
    cap:dependencyTarget ex:paid-overage ;
    cap:dependencyKind cap:GatesTarget ;
    cap:dependencyPrecedence 10 .
```

The domain-specific billing consequences of paid overage do not belong in Capacity. A SaaS domain ontology or commercial application supplies them.

---

## Open questions

1. **Maximum capacity semantics.** Is `cap:hasMaximumCapacity` an initial balance, a contractual ceiling, a replenishable limit, or a combination of these? The first release should define it as a declared upper bound on available balance. More nuanced restoration semantics remain deferred.

2. **Account cardinality.** May one CapacityResource have multiple accounts, for example per currency, region, customer, or period? The first release should permit multiple accounts but require an explicit partitioning profile before cross-account allocation is supported.

3. **Demand aggregation.** Does one CapacityDemand represent one request, one event, or a bundle of related requests? The first release should model one requested quantity. Composite demand belongs in a later extension.

4. **Authority to allocate.** Is allocation an automated effect, an authorised human act, or both? Behaviour and Party can already model this. Capacity should not impose one answer.

5. **Partial allocation policy.** Sequential allocation is available. Proportional and optimisation-based allocation remain deferred until they meet Behaviour's existing genericity and conservation requirements.

6. **Cross-arrangement dependencies.** Can one arrangement consume or bound capacity in another arrangement? This is plausible but should be excluded from the first release unless a tested use case requires it.

7. **Relationship to Surface and execution tooling.** Capacity should be designed so a deterministic execution surface can be compiled later, but should not require a specific runtime representation.
