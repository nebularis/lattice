<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Derivation and Validation Reference

This document is the Gate 4 companion for [decisions/ADR-A12-identity-and-derivation-model.md](decisions/ADR-A12-identity-and-derivation-model.md), [decisions/ADR-A13-dataset-graph-role-model.md](decisions/ADR-A13-dataset-graph-role-model.md), and [decisions/ADR-A15-realisation-strategy-neutrality.md](decisions/ADR-A15-realisation-strategy-neutrality.md).

## Reference realisations

| Rule family | SHACL reference | SPARQL reference | Deliberate-defect fixture |
|---|---|---|---|
| Eligibility interval declarations require a range set | [ontology/eligibility/shapes/constraints.ttl](../../ontology/eligibility/shapes/constraints.ttl) `elg:IntervalContainmentRequiresRangeSet` | [test/gate4/queries/eligibility-interval-missing-rangeset.rq](../../test/gate4/queries/eligibility-interval-missing-rangeset.rq) | [test/gate4/eligibility-interval-missing-rangeset.ttl](../../test/gate4/eligibility-interval-missing-rangeset.ttl) |
| Behaviour priority-ordered transitions require a priority | [ontology/behaviour/shapes/constraints.ttl](../../ontology/behaviour/shapes/constraints.ttl) `bhv:PriorityOrderedNeedsPriority` | [test/gate4/queries/behaviour-priority-without-priority.rq](../../test/gate4/queries/behaviour-priority-without-priority.rq) | [test/gate4/behaviour-priority-without-priority.ttl](../../test/gate4/behaviour-priority-without-priority.ttl) |
| Behaviour proportional absorption is declared-but-rejected at Gate 3 | [ontology/behaviour/shapes/constraints.ttl](../../ontology/behaviour/shapes/constraints.ttl) `bhv:SequentialOnlyAtGate3` | [test/gate4/queries/behaviour-proportional-deferred.rq](../../test/gate4/queries/behaviour-proportional-deferred.rq) | [test/gate4/behaviour-proportional-deferred.ttl](../../test/gate4/behaviour-proportional-deferred.ttl) |
| Instrument supersession requires same identity | [ontology/instrument/shapes/constraints.ttl](../../ontology/instrument/shapes/constraints.ttl) `ins:SupersessionSameIdentityShape` | [test/gate4/queries/instrument-supersession-identity-mismatch.rq](../../test/gate4/queries/instrument-supersession-identity-mismatch.rq) | [test/gate4/instrument-supersession-identity-mismatch.ttl](../../test/gate4/instrument-supersession-identity-mismatch.ttl) |

## Scope of Gate 4

Gate 4 does not add compilation. It makes three things explicit:

- how derived products are expected to be described
- how declaration-level constraints are checked in more than one realisation strategy
- how invalidation can be demonstrated without a repo-wide rebuild

## Targeted invalidation demonstration

A minimal invalidation walk can be expressed with the current fixtures:

1. Start from [ontology/eligibility/test/E2-interval-containment.ttl](../../ontology/eligibility/test/E2-interval-containment.ttl).
2. Change the required range bounds or the referenced `qnt:RangeSet`.
3. Re-run only the Eligibility interval checks and any Behaviour guard evaluations depending on the affected `elg:AdmissionProfile`.
4. Leave [ontology/behaviour/test/B-P2-sequential-allowance.ttl](../../ontology/behaviour/test/B-P2-sequential-allowance.ttl) untouched, because its allowance state does not depend on that profile.

This demonstrates dependency-local invalidation even though no execution engine is yet implemented.
