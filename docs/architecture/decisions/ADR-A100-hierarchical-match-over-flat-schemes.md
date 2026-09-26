<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A100: Hierarchical match over schemes without a hierarchy

**Status:** Proposed
**Date:** 2026-09-26 (proposed, then twice rewritten the same day: first to place the concern in the substrate, then to reduce it to Eligibility and its compilers)
**Related:** ADR-A85 (scoped binding resolution), ADR-A87 (concept exclusion), ADR-A89 (concept IR), ADR-A92 (derived artefacts), ADR-A13 (graph roles), ADR-A103 (set readings), ADR-A-C2, ADR-A98 (addendum)
**Unit:** [`applied-insurance-reference`](../../developer/plans/applied-insurance-reference.md) (AIR-0.1, epic decision D11)

## Context

**Premise.** One condition may be evaluated against different schemes in different contexts,
because Vocabulary resolves a contract's scheme by scope (ADR-A85). A condition written for a
hierarchical scheme can therefore meet a flat code list. Hierarchical match then finds no
`skos:broader` path and refuses every candidate the condition does not name, when the list says
nothing either way.

**Examples.**

1. *Lending.* A credit policy admits borrowers in "manufacturing" under a hierarchical industry
   classification. For one lender the contract resolves to that lender's flat list of sector
   codes. "Food processing" is in the list, but the list does not say whether it is
   manufacturing.
2. *Employment.* A benefits rule applies to "healthcare practitioners" under an occupational
   classification. For one employer the contract resolves to a flat list of job titles. "Ward
   nurse" is refused, although it is a healthcare practitioner.

Eligibility already states the precondition ("`HierarchicalMatch` is valid when a dimension is
backed by a concept scheme whose membership is resolved against a well-founded `skos:broader`
hierarchy") and does not check it. The compilers already resolve the scheme at compile time and
build a decision for each of its members (ADR-A89), and already report Undetermined outcomes with
an `exe:Diagnostic`.

## Decision

1. **The law.** Under `elg:HierarchicalMatch`, a resolved scheme has a hierarchy when at least one
   of its members has a `skos:broader` link to another member. Over a scheme without one, a
   candidate equal to a required concept matches, a candidate equal to an excluded concept is
   excluded, and every other member of the scheme is Undetermined. Candidates outside the scheme
   stay as they are (`exe:OutsideScheme`).
2. **The reason.** `exe:NoHierarchy`, a new `exe:Diagnostic`, is reported with each such
   Undetermined outcome.
3. **The compilers.** The concept IR applies the law when it expands the scheme's decisions, so
   the SHACL and SWRL backends, which read that expansion, follow without change. The SPARQL
   backend, which walks `skos:broader` at query time, gains the same rule and the new diagnostic.
   The OWL backend refuses such a plan, since a design-time class cannot express Undetermined.
4. **Crosswalks.** A crosswalk between two schemes is a graph of reviewed SKOS mapping triples,
   recorded as a `fnd:DerivedArtefact` (ADR-A92) whose read set is the two scheme editions. A
   consumer may lift a value through an exact mapping and evaluate it against the target scheme.
   An inexact mapping may advise, never decide. MORK is where proposed mappings wait for review
   (ADR-A13). Consumers read only the crosswalk.
5. **Published crosswalks (MB-Q3).** An applied module may publish a reviewed crosswalk of a
   widely used external list beside its reference edition, where the list owner's terms allow.

## Alternatives considered

A Vocabulary extension (structural capabilities as shapes over a scheme, derived scheme profiles,
`voc:requiresCapability` on contracts) was drafted and set aside. Its only consumer today would be
Eligibility, which already holds the resolved scheme at compile time. Revisit it when a contract
must refuse a scheme without a hierarchy at binding time, or when a check other than Eligibility
needs to know which structure a scheme lacks.

## Consequences

- No Vocabulary or Eligibility `.ttl` change. Eligibility's README gains the law beside L11, and
  its examples gain the two cases above, authored before the law's prose (ADR-A-C2).
- Executable takes a PATCH bump for one new individual, with the import-pinning cascade.
- A deployment that bound a flat list under hierarchical match sees Undetermined outcomes where
  it saw refusals. The law enforces a precondition Eligibility already documented, so no
  conformant use changes.
- Conditions on other properties of a subject (a code's characteristics, say) need no rule of
  their own: a flat list's codes carry no such values, and missing evidence is already
  Undetermined (`exe:MissingCandidate`).
- No applied `scheme-profile/` module exists (ADR-A98 addendum).
