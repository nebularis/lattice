---
published: true
---
<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A146: A published term is versioned by its release

**Status:** Published, 2026-10-29. Accepted 2026-10-29.
**Date:** 2026-10-29
**Related:** [ADR-A86](https://github.com/nebularis/lattice/blob/main/docs/architecture/decisions/ADR-A86-ontology-semantic-versioning.md) (one `owl:versionIRI` per ontology document), the [identity guide](../iri-identity-patterns.md) (persistent identity across immutable versions, and a public vocabulary term scoped by nothing), [ADR-A141](ADR-A141-versioned-mixin-rename.md) (the mixin `fnd:Versioned`), [ADR-A142](ADR-A142-meaning-bearing-edges.md) (a meaning-bearing edge from a versioned thing is owned or pinned)
**Described in:** [Foundation](../../../ontology/foundation/README.md), §4, §6 and §8.7

## Context

Foundation's mixin `fnd:Versioned` gives a class instances that are versions of a persistent identity, each with exactly one `fnd:hasIdentity` and chained by `fnd:supersededBy`. Behaviour, Eligibility, Vocabulary, Wording, Instrument and Quantification made their authored definitions members of it, state spaces, transition definitions, admission and operational profiles, scheme contracts and concept schemes, because an adopter writes those at runtime, edits them, and a judgement made under one version must be reproducible from that version. The ontology remediation of 2026-10-28 filled Foundation's empty structural shape with the restriction the OWL already stated, so `fnd:VersionedShape` began to check it.

The layers also declare individuals of those classes in their own documents. Eligibility publishes the reference profiles E1 to E5, Behaviour two operational profiles and two state spaces, Wording, Instrument and Quantification their scheme contracts and concept schemes, twenty-two in all at 0.19.0. The first run of the shape over them, in the computable contract substrate's tests, failed every one that carried no identity, and the identities the rest did carry pointed at untyped nodes. Minting an identity for each would have given every published term two version histories, the chain's and the release's, that agree only by discipline.

The identity guide already draws the line. A public vocabulary term is scoped by nothing (§4.6), and its revision is the ontology's `owl:versionIRI` (§9). Its identity is its IRI.

## Decision

1. **The rule.** An individual that an ontology document declares is a published term. Its identity is its IRI and its versions are the releases of the ontology that declares it, so it carries no `fnd:hasIdentity` chain of its own, whatever class it is an instance of.
2. **The mark.** A published term says which ontology declares it with `rdfs:isDefinedBy`, the RDF Schema property with that meaning, pointing at the `owl:Ontology` of the document that declares it. The layer that declares the term sets the mark.
3. **Two shapes read the mark.** `fnd:VersionedShape` requires exactly one `fnd:hasIdentity`, a `fnd:PersistentIdentity`, of a versioned thing that is not so marked. `fnd:MeaningBearingEdgeShape` treats a meaning-bearing edge to a published term as safe, beside an edge to a versioned or an owned node, since a release changes every published term at once and nothing edits one in a store.
4. **An example is not a published term.** The examples under a layer show the data an adopter copies into a store and then edits, so they carry identities and the rules hold on them without exemption.
5. **Copying a published term.** An adopter who copies a published term into a store to edit it drops the mark and mints an identity. The copy is authored data from then on.
6. **The OWL restriction stands.** `fnd:Versioned` keeps its cardinality of one on `fnd:hasIdentity`. Under the open world a reasoner infers that a published term's identity exists without naming it, which is what its IRI is.

## Consequences

- The twenty-two published terms are marked, and a layer that publishes a new term of a versioned class marks it in the same declaration.
- A published term that already carries an identity may keep it. The exemption makes the chain optional for a published term, never forbidden.
- The Persistence compiler's refusal of a meaning-bearing edge by identity from a versioned class (ADR-A142 decision 3) does not yet read the mark, so an authored definition that names a published part is still refused as a reference by identity until the compiler can see that the target is a published term (TD-127).
- An adopter's configuration vocabulary follows the same rule for the terms it publishes.

## Provenance

The maintainer ruled on 2026-10-29, when the computable contract substrate's merge of main surfaced the fifty-three failures, that published terms are exempt and that examples, being samples of authored data, are not. The question was not raised in the ontology design review of 2026-10-28, which took the versioned classes as given and remedied only their mutable parts, so the remediation made the restriction checkable without deciding its reach over published terms.
