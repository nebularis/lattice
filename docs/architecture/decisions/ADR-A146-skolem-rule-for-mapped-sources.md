<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A146: How a MORK run names a source's blank nodes

**Status:** Proposed 2026-10-29
**Date:** 2026-10-29
**Related:** [ADR-A82](ADR-A82-framework-neutral-identity-pattern-selection.md) (the identity pattern catalogue, whose §9.2 and §9.4 this applies), [ADR-A143](ADR-A143-one-canonicalisation.md) (digests of RDF content, which this does not change)
**Described in:** [`tools/mork_rdf`](../../../tools/mork_rdf/README.md) §12.2

## Context

A MORK mapping over an RDF source reads a focus node's identity with `STR()` and mints target IRIs from it, so every blank node of the source needs an IRI before the queries run, and that IRI decides which target nodes are the same across runs. ODRL policies and most JSON-LD hold their rules, constraints and nested records as blank nodes, so most identities in such a source are blank.

The runner first named them by RDFC-1.0 canonical labels over the whole source. That has two faults. Canonical labels are numbered across the whole source, so adding one unrelated blank node renumbers others: an author alone is `c14n0`, and the same author beside one more record is `c14n1`, and every target IRI minted from it changes. The catalogue already says so of its revision-local canonical-label pattern (§9.4), which suits addresses inside one sealed revision and not durable identities. And canonicalising the whole source was the run's largest memory cost, 1,699 MB at 100,000 records against 558 MB for a plain load.

## Decision

1. **Tree nodes take the source-local deterministic pattern** (catalogue §9.2). A blank node in a tree of blank nodes hanging from one named node is named from the IRI of the node that reaches it, the predicate that reaches it, and a hash of its own description, its triples with each blank object replaced by that object's description hash. Siblings identical in all three are numbered, since nothing tells them apart and any numbering gives the same graph.
2. **Other blank nodes take the revision-local pattern, scoped to their component** (catalogue §9.4). A node in a cycle, shared by several triples, or reached from no named node is named by its component's RDFC-1.0 digest and its canonical label within the component, and the run reports each such component, since its IRIs change whenever the component does.
3. **The rule is versioned in every IRI**, `urn:mork-rdf:skolem:v1:`, so a later rule can never be mistaken for this one. Its text is normative in the runner's README §12.2, conformance vectors pin it, and a test re-derives a name by hand from the text. A change to any IRI the vectors hold is a new version.

## Consequences

- A blank node's IRI does not depend on the order of the triples or on unrelated content, so a re-run over a source with records added gives the existing records the same target IRIs.
- A blank node's IRI changes when its own description, its predicate or its parent's IRI changes, so an edit inside a nested record gives that record new IRIs up to its root blank node. This is RDF's own view of a blank node, and a mapping that needs identity to survive such edits reads a natural key into its identity template, or the source names the node.
- Identical siblings, such as two authors both named Anon, are two nodes with numbered IRIs, which are interchangeable.
- Target IRIs minted under the earlier canonical labels differ from those minted under this rule. Nothing has been released or deployed that holds them.
- Skolemising 100,000 records with one blank node each fell from 1,699 MB to 857 MB, and a streamed run from 1,514 MB in 23.2 s to 1,041 MB in 13.4 s.
- An implementation outside this repository reproduces the names from the rule's text and its vectors alone.

## Provenance

Found by the MORK run planner's benchmark on 2026-10-29, which showed canonicalisation setting the run's peak, and by a probe of the labels that showed renumbering under an unrelated addition. The maintainer accepted a new naming rule on condition that its consequences are documented and it is enforced, which the vectors, the hand derivation and the property tests do.
