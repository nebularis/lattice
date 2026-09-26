<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A102: Liability direction from party roles

**Status:** Accepted
**Date:** 2026-09-26 (proposed), 2026-09-26 (accepted)
**Related:** ADR-A92 (derived artefacts), ADR-A98, ADR-A99
**Unit:** [`applied-insurance-reference`](../../developer/plans/applied-insurance-reference.md) (AIR-0.1)
**Sketches:** [term-parameters.md](../../developer/sketches/term-parameters.md) §7, [asset-exposure-ontology.md](../../developer/sketches/asset-exposure-ontology.md) §5.15

## Context

Liability, D&O and E&O cover respond differently depending on who was harmed, who is alleged
liable, who claims and who is paid: first party, third party, insured against insured, derivative
actions, and fourth parties reached through an intermediary. Those parties are mostly unknown
when the contract is bound. The peril vocabulary's agency characteristic records who or what
acted to cause an event, which is a different question (ADR-A99).

Party already reifies an occupancy of a role so that it can exist before anyone fills it
(`pty:RoleOccupancy`, `pty:inRole` exactly one, `pty:occupiedBy` optional).

## Decision

1. **Four role individuals** of `pty:Role`, in `insurance/common/` (`icm:`): harmed party,
   liable party, claimant and payee.
2. **Contracts name role types and populations, never people.** At binding, scopes and
   requirements refer to a role and a population (exposure's counterparty populations). At claim
   time, occupancies of those roles are created and filled. An occupancy may be created unfilled
   when a notice names a role before an actor is known.
3. **Direction is derived, never asserted.** Direction values (first party, third party, insured
   against insured, derivative, fourth party) are concepts in an `icm:` scheme. A direction is
   recorded only as a `fnd:DerivedArtefact` whose read set is the filled roles and the
   relationship graph (control relations, dependencies, counterparty populations). A shape
   reports a direction value without such a derivation.
4. **Agency is not direction.** No rule derives direction from the agency characteristic, and no
   peril concept carries a direction.
5. **Scope of this decision.** It fixes the representation, so that AIR-1.2 can declare the
   roles. The derivation rules, and D&O constructs such as Sides A, B and C, are specified with
   the contract and claims modules (epic Phases 5 and 6).

## Consequences

- No Party change.
- A claim by a party unknown at binding needs no invented actor at binding and no rewrite of the
  contract.
- Fourth-party distance depends on relationship data being captured. The exposure ontology's
  counterparty populations and dependencies supply it.
- New directions are new derivation rules, not new concepts asserted on each claim.
