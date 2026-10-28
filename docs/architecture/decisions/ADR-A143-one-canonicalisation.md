<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A143: One canonicalisation for the substrate

**Status:** Proposed 2026-10-28
**Date:** 2026-10-28
**Related:** [ADR-A82](ADR-A82-framework-neutral-identity-pattern-selection.md) (identity patterns, and the identity guide's RDFC-1.0 rule), [ADR-A132](ADR-A132-persistence-caller-library.md) (the conformance vectors that recompute digests)
**Described in:** [Surface](../../../ontology/surface/README.md) §6, [Quantification](../../../ontology/quantification/README.md) `qnt:spaceHash`, [Persistence](../../../ontology/persistence/README.md) §5, [MCN](../mork-compact-notation.md) §12.4

## Context

Canonical bytes were defined four ways. Surface's hashes were untyped strings with no algorithm, computed in practice by rdflib's canonical graph. MCN defines a sorted N-Triples decoding with its own blank-node labelling. Persistence uses RDFC-1.0 and RFC 8785 with SHA-256 and declares its digest schemes as data. The identity guide fixes RDFC-1.0 for content revisions. Quantification made `qnt:spaceHash` mandatory with no algorithm and said that no content-hash contract existed. Two implementations could disagree on whether two declarations were the same declaration, and a cache keyed on these hashes was unreliable outside one tool.

## Decision

1. **One rule.** A digest of RDF content anywhere in the substrate is computed over the RDFC-1.0 canonical N-Quads of the content, with SHA-256, written as lowercase hexadecimal. Persistence's digest-scheme vocabulary (`dal:digestFunction "SHA-256"`, `dal:digestWidthBits 256`, `dal:digestEncoding "lowercase-hex"`) names it where a scheme is declared as data.
2. **Each layer names its content.** A layer that stores a digest says which triples form the content. Surface's read-set hash is the input's graph, its semantic content hash is the dataset of the read set's inputs each in a graph named by its entry, and its artefact hash is over emitted bytes under the bound generator version. Quantification's `qnt:spaceHash` is the space node and every triple reachable from it through `qnt:` properties, excluding the hash itself and the version and governance properties. Persistence's digests are as its specification already states.
3. **MCN's canonical decoding stays** as the digest of an MCN document, which any conforming decoder reproduces. It is not a graph digest. For a graph with no blank nodes the two coincide.
4. **Conformance.** Each layer that stores a digest publishes at least one vector, a small graph with its digest, that an implementation sharing no code with the project recomputes. The vectors are owed, and TD-103 stays open until they exist.

## Consequences

- Surface's determinism law and interchangeable surfaces are reproducible outside rdflib, at the cost of an RDFC-1.0 implementation, which rdflib and the Persistence caller library already have.
- A `qnt:spaceHash` in an example is computable, and two declarations are the same declaration exactly when their digests agree.
- Existing hashes written under rdflib's canonical graph are not comparable with the new ones. No deployment holds any.

## Provenance

The design review of 2026-10-28 (§2.4) found the four definitions, and the maintainer chose one rule adopting Persistence's vocabulary. Built as slice OR-9 of the [ontology remediation plan](../../developer/plans/ontology-remediation.md).
