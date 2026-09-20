<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR A-03: Eligibility condition taxonomy

## Status

Accepted

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
