---
published: true
---
<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A03: Eligibility condition taxonomy

**Status:** Published, 2026-10-19. Accepted 2026-09-17.
**Described in:** [Eligibility README](../../../ontology/eligibility/README.md)

## Context

Eligibility must support condition declarations that are reusable across layers and domains, while remaining explicit about which matching semantics apply. Prior drafts mixed condition intent and evaluation method, which made profile conformance harder to verify and made interval semantics ambiguous.

## Decision

Eligibility conditions are declared under a single taxonomy rooted at `elg:Condition` with four strategy-specific branches:

- `elg:ExactCondition` uses exact value equality.
- `elg:SetMembershipCondition` checks concept or value membership in a declared set.
- `elg:IntervalCondition` checks containment in declared `qnt:Range` or `qnt:RangeSet`.
- `elg:WildcardCondition` allows declared wildcard slots and requires explicit wildcard semantics.

Each condition instance must declare:

- one match strategy (`elg:matchStrategy`)
- one compatibility operation (`elg:compatibilityOperation`)
- one wildcard policy (`elg:wildcardSemantics`)

`elg:AdmissionProfile` is a subclass of `elg:Condition` and additionally composes one or more conditions via `elg:hasCondition`.

## Consequences

- Strategy selection is explicit per condition and can be validated structurally.
- A profile can be reasoned over as a condition itself, which keeps composition uniform.
- Interval conditions can bind directly to Quantification ranges without introducing new numeric mechanisms in Eligibility.

## Addendum, 2026-10-19: what a profile declares

Agreed by the maintainer. A condition that is not an admission profile declares one match strategy and one
wildcard policy. An admission profile declares neither, since it tests no candidate itself, and declares one
composition operation, which says how it combines its conditions' outcomes (ADR-A05's addendum of the same
date). Laws L1 to L3 and Eligibility's shapes say so.


## Provenance

**Unit:** [`improved-ontology-documentation`](../../developer/plans/improved-ontology-documentation.md) (plan), addendum 2026-10-19

Accepted when Eligibility was first specified, 2026-09-17. The 2026-10-19 addendum answers questions OD6-Q7, ELC-Q1 and ELC-Q2 of the [`improved-ontology-documentation`](../../developer/plans/improved-ontology-documentation.md) plan.
