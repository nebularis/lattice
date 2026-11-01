---
published: true
---
<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A142: A meaning-bearing edge from a versioned thing is owned or pinned

**Status:** Published, 2026-10-29. Accepted 2026-10-29.
**Date:** 2026-10-28
**Related:** [ADR-A122](ADR-A122-aggregate-ownership.md) (a classified boundary shape, and references by identity or pinned), [ADR-A131](ADR-A131-ledger-layer.md) (an account definition folded into every balance), [ADR-A85](ADR-A85-vocabulary-scoped-temporal-binding-resolution.md) (scheme bindings)
**Described in:** [Foundation](../../../ontology/foundation/README.md) §4 and §5, [Persistence](../../../ontology/persistence/README.md) §5.6.1

## Context

Four layers point from a versioned thing at parts that are edited in place. An admission profile is versioned over plain, shared condition nodes. A transition definition is versioned over plain trigger, guard and effect definitions. An account definition is a plain class whose stated amount, ceiling and merge rule every historical balance folds against. A scheme binding takes its end date on the existing node. Foundation itself invites in-place writes of the governance state, and Party adds an occupant later to an existing occupancy. In each case a judgement reproduced from a past version depends on the current state of a node that was not part of that version, against the rule that judgements are evaluated from facts.

Persistence already has the vocabulary for the fix. An aggregate is a root and the nodes its boundary shape owns, written as one unit, and an edge that leaves it is by identity or pinned to one version of its target, which the compiler refuses when the target is not versioned (ADR-A122). What was missing was the mark that says which edges bear meaning: only evidence and record classes got the by-identity warning.

## Decision

1. **The rule.** A node that a versioned thing's meaning depends on is itself versioned, content-addressed, or copied into the owner's version. In Persistence's terms, a meaning-bearing edge from a versioned node is owned or pinned, never a reference by identity.
2. **The mark.** Foundation declares the annotation property `fnd:meaningBearing`, set to `true` on an object property whose object is part of its subject's meaning. The layer that owns the property sets it.
3. **Checked twice.** A SHACL-SPARQL shape in Foundation warns on data where a versioned subject's meaning-bearing edge leads to a node that is neither versioned nor minted under the subject. The Persistence compiler refuses a profile whose boundary shape classifies such an edge as a reference by identity from a versioned class (`MeaningBearingEdgeByIdentity`), so the edge is owned or pinned. The shape is a warning because data cannot tell a content-addressed object from a mutable one. The compiler's refusal is exact.
4. **Nested aggregates are not needed.** A boundary shape is already a nested, recursive tree, and a root inside another root stays refused. A part that other aggregates cite, such as an account definition inside a configuration aggregate, is pinned by the configuration aggregate's version with the part's IRI minted under it. The warning on a pin to an owned component becomes a check that the component's root is versioned, in the slice that needs it.
5. **The four instances** are taken by their layers: Eligibility's conditions, Behaviour's components, Vocabulary's bindings and, in the ledger unit, the account definition. Foundation's governance state and Party's occupancy follow the same rule.
6. **A scheme binding stays unversioned.** Its ending is a fact of its own, a closure record the resolver reads as the end of validity, since a binding is a governance act and its ending another. Versioning it would add a transaction-time axis to ADR-A85's resolution.

## Consequences

- A layer marks its meaning-bearing properties once, and every adopter's persistence configuration is checked against the mark at compile time.
- A deployment that compiles a family in place without receipt delta graphs can still lose a past state. That is the family's write discipline (`dal:AppendVersions` keeps it) and not this rule.
- Existing data that references a mutable part by identity validates with a warning until the part is versioned or minted under its owner.

## Provenance

The maintainer asked on 2026-10-28 whether the defect evaporates under an aggregate, whether nested composition is needed, how the rule is enforced, and what versioning a scheme binding entails. The answers are decisions 3, 4, 2 and 6. Built as slice OR-7 of the [ontology remediation plan](../../developer/plans/ontology-remediation.md).
