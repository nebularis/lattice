<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Capacity: finite resources that are drawn down, bounded and reset

A cross-domain applied module ([ADR-A98](../../../docs/architecture/decisions/ADR-A98-applied-layout-and-insurance-modules.md)
decision 2). It holds no domain vocabulary.

---

## 1. Purpose and scope

Models finite capacity that can be drawn upon. Example uses include a loan facility, an insurance limit, a service quota, a credit line, an inventory allocation, a grant budget, or an emissions allowance. Each are a resource that is declared with a quantity, has a balance that changes over time, is consumed by demands, may reset or be replenished, may be gated by eligibility, and may bound, deplete, or gate other resources.

Capacity models networks of such resources, atop [`behaviour`](../../behaviour/) allowances and [`quantification`](../../quantification/)'s handling of value spaces.

**Static and dynamic.** An instrument states a limit, a static parameter. The running total drawn against it is dynamic, and lives here: a projection that Capacity defines, through Surface, creates the dynamic resource from the instrument's static limit ([computable contract substrate](../../../docs/developer/sketches/computable-contract-substrate.md)
§7.8). A threshold regime's state is then derived from the resource's value.

The design, its principles, and laws, are located in [`docs/architecture-overview.md`](docs/architecture-overview.md), with runtime performance constraints documented in [`docs/perf.md`](docs/perf.md).

## 2. What is authored

| Part | Namespace | File | State |
|---|---|---|---|
| source ontology: arrangements, resources, demands, draws, dependencies, rules | `cap:` | `spec/capacity.ttl` | **designed, not authored** (architecture overview §"Proposed applied ontology") |
| runtime execution profile | `capx:` | [`spec/applied_capacity_execution_spec_capx_Version2.ttl`](spec/applied_capacity_execution_spec_capx_Version2.ttl) | authored, `0.10.0` |

The execution profile's `capx:projectsFrom…` properties range over `cap:` classes that no document
declares yet. They resolve when the source ontology is authored.

## 3. The execution profile (`capx:`)

A compact, normalised view of a capacity arrangement for transaction-time evaluation
([ADR-A-CAP1](../../../docs/architecture/decisions/ADR-A-CAP1-capacity-runtime-projection-profile_Version2.md),
Proposed). The source graph stays the source of truth. The profile is materialised from it by a
deterministic projection, so an evaluator reads scalar values with bounded-hop lookups instead of
traversing the generic graph.

**Imports:** Foundation, Quantification, Eligibility and Behaviour's runtime document (which imports
Behaviour's configuration). It does not import Instrument.

| Kind | Terms |
|---|---|
| runtime classes | `ExecutableArrangement`, `ExecutableResource`, `ExecutableBalance`, `ExecutableDemand`, `ExecutableDraw`, `ExecutableDependency`, `ExecutableGuardState` |
| dependency kinds | `DepletesTarget`, `BoundsTarget`, `GatesTarget` |
| dependency phases | `PreDrawPhase`, `ActivationPhase`, `PostDrawPhase` |
| draw statuses | `Allocated`, `PartiallyAllocated`, `Denied`, `Unavailable`, `Undetermined` |
| links to Behaviour and Eligibility | `usesTransitionExecution` (a `bhv:TransitionExecution`), `usesEffectApplication` (a `bhv:EffectApplication`), `requiresEligibilityDecision` (an `elg:EligibilityDecision`) |

**Shapes**, in the same file:

| Shape | Checks |
|---|---|
| `ExecutableResourceShape`, `ExecutableBalanceShape`, `ExecutableDemandShape`, `ExecutableGuardStateShape` | required keys, amounts and flags |
| `ExecutableDependencyShape` | a dependency's source and target differ |
| `ExecutableDrawShape` | the allocated amount never exceeds the requested amount, and requested equals allocated plus unmet (conservation) |
| `DependencyPrecedenceUniquePerTargetPhase` | no two dependencies share a precedence for one target and phase |
| `DemandSpaceMatchesResourceSpace` | a draw's demand and resource are in the same execution space |

## 4. Where it sits

```
behaviour configuration
    └── behaviour runtime
            └── applied/capacity execution profile (capx)
```

Capacity sits above Behaviour and below any domain that uses it. A construct moves from Capacity into
Behaviour only when the promotion criteria of
[ADR-A-CAP2](../../../docs/architecture/decisions/ADR-A-CAP2-capacity-to-behaviour-promotion-criteria_Version2.md)
(Proposed) are met (principle CP-9).

The architecture overview predates ADR-A106 in two respects. Its proposed import list names
Instrument, which an applied module may still import, since Instrument is a layer below it. Its
list of substrate layers puts Instrument below Behaviour, the order before ADR-A106.

## 5. Release notes

Breaking versions at major version zero ([ADR-A113](../../../docs/architecture/decisions/ADR-A113-breaking-changes-at-major-version-zero.md)):

- 0.8.0 (breaking): the execution profile imports `behaviour-runtime` 0.8.0 in place of `behaviour`
  0.7.0. Its import closure no longer includes Instrument, so a consumer that reached Instrument's
  terms through it must import Instrument directly. ADR-A106.
