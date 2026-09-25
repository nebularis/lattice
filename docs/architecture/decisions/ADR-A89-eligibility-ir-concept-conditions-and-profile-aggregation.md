<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A89: Eligibility IR for concept conditions and profile aggregation

**Status:** Proposed
**Date:** 2026-09-25
**Extends:** ADR-A24 (Eligibility executable semantics and backend strategy)
**Related:** ADR-A23 (compiler family completion), ADR-A27 (invalidation),
ADR-A28 (parity gate), ADR-A05 (compatibility operations), ADR-A85 (binding
resolution), ADR-A87 (concept inclusion and exclusion)
**Unit:** [`applied-ontology-readiness`](../../developer/plans/applied-ontology-readiness.md)

## Context

`tools/mork_compilers` compiles `elg:IntervalCondition` only. It refuses
`ExactMatch`, `SetMembership` and `HierarchicalMatch` conditions, and it
produces no profile-level artefact. An applied ontology whose admission rules
are mostly categorical (job family, diagnosis, product tier, jurisdiction)
therefore gets no executable form for most of its conditions. ADR-A87 adds
inclusion and exclusion semantics that no backend implements.

Two model gaps block compilation. A question has no concept-valued candidate
(`elg:candidateValue` ranges over `qnt:Value`). Hierarchical match depends on
which scheme edition a contract resolves to, which under ADR-A85 depends on a
resolution context and instant that the compiler does not receive.

## Decision

1. **Concept candidate.** Eligibility adds `elg:candidateConcept`
   (`elg:Question` → `skos:Concept`). `elg:candidateValue` keeps its range.
2. **One IR plan per concept condition.** The shared IR gains a concept plan
   holding the match strategy, required and excluded concepts, the scheme
   contract, the resolved scheme edition, the winning binding or fallback
   marker, and the resolution instant and scope. Resolution calls the
   Vocabulary reference resolver. The instant and scope are explicit compile
   inputs. A contract with any `voc:SchemeBinding` does not compile without
   them.
3. **Two closure modes, chosen by the caller.** `QueryTime` evaluates the
   ordering at run time, restricted to members of the resolved scheme.
   `Expanded` enumerates, at compile time, the admitted, excluded and
   undetermined member sets from the resolved edition under the ADR-A87
   decision table. The plan records the scheme edition it read, so ADR-A27
   invalidation regenerates it when the edition changes.
4. **Backends.**

   | Backend | Concept conditions | Closure mode |
   |---|---|---|
   | SPARQL (reference) | all three outcomes | `QueryTime` or `Expanded` |
   | SHACL | readiness plus `Permitted`/`Denied` over enumerated sets | `Expanded` |
   | SWRL | `Permitted` and `Denied` for scheme members, rendered as membership facts plus fixed rules | `Expanded` |

   Every outcome SWRL derives is then a positive fact about a finite,
   enumerated set, which keeps it within ADR-A24's monotonic limit.
   `Undetermined` is never derived by SWRL.
5. **Profile aggregation** uses strong Kleene logic over the three values.
   `AllRequired`: any `Denied` gives `Denied`, else any `Undetermined` gives
   `Undetermined`, else `Permitted`. `AnySufficient`: any `Permitted` gives
   `Permitted`, else any `Undetermined` gives `Undetermined`, else `Denied`.
   The existing `exe:ProfilePlan` carries the result. `DimensionConsistent`
   has no evaluable definition in ADR-A05 and is refused with a diagnostic
   until one is decided.
6. **Diagnostics.** Executable adds a closed diagnostic vocabulary for the
   cases this ADR introduces: missing candidate, unresolved scheme, candidate
   above an exclusion (L11), refused operation. Every `Undetermined` a backend
   emits carries one.
7. **Parity.** Concept-condition and profile cases join the shared
   conformance corpus. SPARQL is the reference for ADR-A28 parity.

## Consequences

- Eligibility and Executable each take a MINOR bump, with the ADR-A86 import
  cascade.
- `tools/mork_compilers` gains a dependency on `tools/vocabulary`, as
  `tools/surface` already has.
- `Expanded` artefacts grow with scheme size and must be regenerated when an
  edition changes. `QueryTime` avoids both costs and supports only SPARQL.
  The choice stays with the caller.
- Resolution-instant handling must agree with the option chosen for the
  `temporal-binding-consumer-hardening` unit's Finding 1, so Surface and this
  compiler treat the instant the same way.
- The source of candidate evidence (the question, or a domain property) is
  decided separately, in ADR-A91.
- The Executable vocabulary's header had left diagnostic codes out as unused.
  Item 6 gives them a consumer and declares them.
- SWRL cannot tell one candidate from several. Its rules assume one candidate
  per question, and a question with several can derive both `Permitted` and
  `Denied`. SPARQL and SHACL give `Undetermined` for several.
