---
published: true
---
<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A122: Aggregate ownership, a classified boundary shape for every boundary strategy

**Status:** Published, 2026-10-20. Accepted 2026-10-10.
**Described in:** [Persistence](../../../ontology/persistence/README.md)
**Date:** 2026-10-10
**Supersedes:** none
**Amends:** [ADR-A78](ADR-A78-persistence-profile-substrate-and-aggregate-boundaries.md) decision 4
**Related:** [ADR-A79](ADR-A79-persistence-compiler-toolchain.md),
[ADR-A-FM4](https://github.com/nebularis/lattice/blob/main/docs/architecture/decisions/ADR-A-FM4-persistence-formal-methods-home-and-scope.md),
[the spike](../../../spikes/persistence-aggregate-ownership/README.md)

## Context

ADR-A78 decision 4 gives an aggregate two runtime boundary mechanisms. `dal:NamedGraphBoundary`
puts the aggregate in one graph per root. `dal:CompositePropertyBoundary` walks a SHACL shape's
`sh:property`/`sh:node` tree and sweeps the members it reaches. An aggregate of realistic size, with
several owned relations, nested and recursive structure, references to independent entities, and
links to reference data, showed that the composite mechanism does not model ownership.

- **It reads `sh:node` as ownership.** In SHACL, `sh:node` says a value must conform to a shape,
  and validation shapes put it on references too. A shape whose only `sh:node` is a reference has
  that reference's triples swept by every replace.
- **It follows one property.** A shape with several owned relations is refused since formal-methods
  slice H1.4a, so such an aggregate cannot be declared.
- **It cannot express an edge from child to parent** (`sh:inversePath`), which is how several of
  LATTICE's own layers link a part to its whole.
- **Its replace writes the new payload to the receipt log graph**, not to the graph it deleted from
  , and **does work proportional to the product** of the root's and the members' triples.
- **It has no create or tombstone delete.**
- **Ownership depends on context.** One property can be owned from one class and a reference from
  another, so a flat list of owned properties cannot describe an aggregate.

The named-graph mechanism needs the same classification. A writer still decides which subjects
belong in the graph. Its graph IRI is also derived from the root's local name, so two
roots with one local name share a graph.

No adopter uses `ontology/persistence` or `tools/persistence` outside the formal-methods stream
(agreed 2026-10-10), so no compatibility is kept.

## Decision

1. **A boundary shape is a classified tree.** Every property shape in it that leads to a node
   carries `dal:ownership`, one of `dal:Owned`, `dal:Reference` or `dal:Vocabulary`. A property
   shape with `sh:datatype`, or `sh:nodeKind sh:Literal`, is a value property and carries none.
   `sh:node` alone no longer means ownership. The shape is the authority on which edges exist, not
   `rdfs:domain`. An edge the shape does not declare is not followed.

2. **Members and the delete set.** The members of an aggregate are the nodes reached from its root by
   a non-empty path of owned edges, each in its declared direction (`sh:path` or `[ sh:inversePath ]`).
   Recursion is allowed. The delete set is every triple whose subject is the root or a member. So
   reference and vocabulary edges are deleted with the aggregate, and the nodes at their far ends
   are not. Member types are not checked at run time. Skolem IRIs are ordinary nodes, owned only
   through owned edges, since payloads are skolemised.

3. **One compiled path, three composite operations.** The compiler turns the owned edges into one
   SPARQL property path by state elimination, and every composite operation sweeps with that one
   path in one pattern. The composite strategy gains create-if-absent and tombstone delete beside
   replace. A composite family's aggregates live in one named graph, the profile's mandatory
   `dal:dataGraph`, and every composite operation reads and writes that graph only, never the
   default graph, whose contents differ between stores (static check S-1 of the patterns guide
   §14.3). `dal:maxTraversalDepth` is removed, and the walk visits each shape once.

4. **Reference data is never owned**, unless the aggregate manages it. `skos:Concept`,
   `skos:ConceptScheme`, classes declared through `dal:ReferenceData` with `dal:coversClass`, and
   their asserted subclasses are reference data. An owned edge to reference data is refused unless the
   profile declares `dal:ownsReferenceData true`, as a concept scheme's own aggregate would.

5. **One owner, and references to roots.** A class may be owned by at most one composite boundary,
   and a class owned by one boundary may not be another's root. Both are compile-time refusals.
   References from outside an aggregate should target its root, and the compiler warns when a shape
   points at a non-root owned class.

6. **Named graphs share the classified tree.** A `dal:NamedGraphBoundary` profile may name a
   `dal:boundaryShape`, checked by the same rules, which defines the subjects a payload may contain.
   The typed IR of Track H slice H2 states that payload check for the runtime caller to enforce.
   Documentation recommends named graphs for new deployments. The compiler's default strategy does
   not change.

7. **Version rows stay one per root.** Every write to an aggregate meets every other on the root's
   version row, which is correct and conflicts more than strictly necessary. Units (owned nodes with
   their own version rows) and level operations (edits below the root) are deferred. The rules they
   would need are that an edit bumps its nearest unit, that creating or removing a
   child unit bumps its parent, that removing a unit bumps and tombstones every unit below it, and that a
   cross-level invariant has its own row. They return if contention on a root's version row is
   measured, or a domain invariant needs per-level edits.

8. **A named graph's IRI is injective in its root.** It is `dal:graphIriTemplate` with `{id}`
   replaced by the root IRI encoded with `ENCODE_FOR_URI`, and text after `{id}` kept. A template
   must contain `{id}` exactly once. Across families, the text before `{id}` forms an antichain,
   and a non-empty suffix starts with a character the encoding never emits, so equal graph IRIs
   imply the same family and the same root. No standard limits IRI length, minted ASCII roots grow by about a
   fifth when encoded, and a store that refused an over-long IRI would fail the write with an error,
   where a shared graph would overwrite another aggregate silently.

## Consequences

- `ontology/persistence` goes to 0.3.0 with `dal:ownership`, `dal:OwnershipKind` and its three
  values, `dal:ReferenceData`, `dal:ownsReferenceData` and `dal:dataGraph`, three shapes, and without
  `dal:maxTraversalDepth`. The composite example and every composite fixture gain `dal:ownership`.
- `tools/persistence` gains an ownership tree, a path compiler (`persistence.paths`), a
  `PropertyPath` term on the injection boundary of ADR-A79, four composite templates, seven refusals
  (`MissingDataGraph`, `ComplexBoundaryPath`, `UnclassifiedBoundaryEdge`, `OwnershipOnValueProperty`,
  `CompositeBoundaryWithoutOwnedEdges`, `OwnedReferenceData`, `OverlappingOwnership`), one warning
  (`ReferenceToOwnedClass`) and two refusals for graph naming (`GraphIriTemplateInvalid`,
  `GraphIriTemplateOverlap`). It loses
  `CompositeBoundaryMultipleProperties` (H1.4a) and `BoundaryCycleError`, and the tests that
  asserted them, which this decision supersedes.
- Every named-graph graph IRI changes. Nothing persisted depends on the old ones.
- Track H: H1.4b reports the gaps that remain while the slices run. H2's typed IR carries the tree,
  the path, the payload check and the required-parameter guard. Protocol model O, for units,
  is deferred with them.
- An adopter declares more than before, since every node property must be classified. The refusal
  names the shape and the predicate, and "these edges are references" stays a short statement.
- This decision does not cover erasure of personal data, which follows its own procedure, or a
  membership index, which was considered and not needed at expected aggregate sizes.

## Provenance

The decision was taken on 2026-10-10 from the design sketch ([persistence-aggregate-ownership](../../developer/sketches/persistence-aggregate-ownership.md), normative detail, with the rules for units in its section 11), the exploration note ([persistence-aggregate-ownership](../../developer/notes/persistence-aggregate-ownership.md), section 4.1 for context-dependent ownership) and the review of both ([persistence-aggregate-ownership-review](../../developer/notes/persistence-aggregate-ownership-review.md)). The review's findings S1 to S6 and F1 to F9 and its decisions AO-Q1 to AO-Q13 are the questions this ADR answers. The plan is [Track H plan section 3.5](../../developer/plans/formal-methods-track-h.md#35-ho-aggregate-ownership).

The defects in the Context come from the review and the debt register ([technical-debt](../../developer/technical-debt.md)). Finding F1 is TD-35, F2 is TD-36, F4 is TD-37 and F6 concerns the named-graph writer. TD-03 is the single-property limit, TD-04 the missing create and tombstone, TD-38 the shared graph for equal local names and TD-39 the replace payload written to the log graph. Rows TD-03, TD-04, TD-35 to TD-39 close as their slices land. TD-34, the silently unbound request variable, is addressed by the required-parameter guard of ADR-A123.
