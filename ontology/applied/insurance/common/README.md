<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Insurance Common (`icm:`)

Insurance scheme contracts shared by two or more of the domain's modules (ADR-A98 decision 1,
epic D7), and the liability role types of [ADR-A102](../../../../docs/architecture/decisions/ADR-A102-liability-direction-from-party-roles.md).
Built by the [`applied-insurance-reference`](../../../../docs/developer/plans/applied-insurance-reference.md)
epic, AIR-1.2.

## Files and namespaces (ADR-A98 decision 6)

| File | Content | Namespace | Prefix | Version IRI |
|---|---|---|---|---|
| `spec/common.ttl` | six classification properties | `https://www.nebularis.org/neuro-semantic/insurance/common#` | `icm:` | `…/insurance/common/0.1.0` |
| `vocab/common-vocab.ttl` | one `voc:SchemeContract` per property, and the four liability role types | `https://www.nebularis.org/neuro-semantic/insurance/common/vocab#` | `icm-voc:` | `…/insurance/common-vocab/0.1.0` |

## The six contracts

| Contract | Constrains | Typically bound to (from Phase 2 onwards) |
|---|---|---|
| `icm-voc:PerilContract` | `icm:peril` | `prl-voc:CauseScheme` |
| `icm-voc:MechanismContract` | `icm:mechanism` | `prl-voc:MechanismScheme` |
| `icm-voc:AgencyContract` | `icm:agency` | `prl-voc:AgencyScheme` |
| `icm-voc:ConsequenceContract` | `icm:consequence` | `prl-voc:ConsequenceScheme` |
| `icm-voc:HarmSubjectContract` | `icm:harmSubject` | `prl-voc:HarmSubjectScheme` |
| `icm-voc:PoolContract` | `icm:pool` | the pools scheme (AIR-2.7) |

None binds a scheme here: reference editions bind themselves once they exist (peril's AIR-2.2
onwards), and a deployment binds its own. `icm:mechanism`/`icm:agency`/`icm:consequence`/`icm:harmSubject`
mirror the peril vocabulary's characteristic and companion axes (ADR-A99 §3) at the domain-shared
level, so a module that only needs to classify by one of these axes, without the full peril
vocabulary, can depend on `common/` alone.

## The four liability role types (ADR-A102)

| Role | Meaning |
|---|---|
| `icm-voc:HarmedParty` | suffered the harm |
| `icm-voc:LiableParty` | alleged or found liable |
| `icm-voc:Claimant` | makes the claim |
| `icm-voc:Payee` | receives payment |

Each is a `pty:Role` `owl:NamedIndividual`, declared the same way Party declares its own roles
(`pty:Obligor`, `pty:Obligee`). Contracts name role types and populations, never people: at claim
time, `pty:RoleOccupancy` instances of these roles are created and filled, possibly unfilled at
first if a notice names the role before an actor is known (ADR-A102 decision 2). Liability
direction (first party, third party, insured against insured, derivative, fourth party) is
derived from filled occupancies and the relationship graph, never asserted — and never from the
peril vocabulary's agency characteristic (ADR-A102 decisions 3 and 4). The derivation rules
themselves are specified with the contract module (Phase 5).

## What arrives later

The loss event (AIR-4.4, shared by exposure and claims) and the liability direction scheme
(Phase 5, ADR-A102) are not declared here.

## Dependencies

Imports Foundation, Vocabulary, Party and `classification/`, all by exact version IRI.
`peril/` does not yet import this module (ADR-A98 decision 5 says it should): `peril/`'s spec was
built in AIR-2.1, before `common/` existed. Wiring that import, and specialising `icm:peril` and
the rest with `prl:`-prefixed sub-properties where the peril module needs its own, is for AIR-2.2
or a later slice to do — this slice does not edit `peril/`.
