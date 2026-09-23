<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A82: Framework-Neutral Identity Pattern Selection

**Status:** Proposed
**Date:** 2026-09-23
**Supersedes:** [ADR-A51](ADR-A51-iri-and-identity-policy.md)
**Related:** [IRI and Identity Patterns](../iri-identity-patterns.md), [RDF & SPARQL Patterns Guide](../rdf-sparql-patterns-guide.md), ADR-A54, ADR-A63, ADR-A68, ADR-A78
**Drafted by:** Agent following human architectural direction. Pending human ratification, see [phase-0-status.md](../../developer/status/phase-0-status.md).

## Context

ADR-A51 attempted to select one IRI grammar and one identity policy for all LATTICE users. The subsequent reviews showed both specification gaps and a broader architectural error: LATTICE is a framework, while adopters already have domain identifiers, tenancy models, project structures, deployment environments, and graph-store topologies. A universal LATTICE grammar would either re-mint identifiers outside the framework's authority or encode one application topology as a framework rule.

The persistence substrate already models independently selectable aggregate, concurrency, ordering, receipt, topology, and uniqueness patterns. Identity must follow the same configuration-first approach.

## Decision

1. LATTICE supplies a framework-neutral catalogue of IRI and identity patterns, not one mandatory identifier grammar. The catalogue is [IRI and Identity Patterns](../iri-identity-patterns.md).
2. An adopter selects compatible patterns by resource role and deployment scope. Resource roles include external entities, runtime entities, aggregate roots, component nodes, authored lineages, content revisions, graph locators, key claims, and event occurrences.
3. Tenant, project or authoring context, environment, dataset, source system, and naming authority are independent dimensions. A selected profile decides which dimensions participate in an identifier. The framework does not equate or require any of them.
4. Existing adopted identifiers retain their naming authority. LATTICE records mappings and provenance where needed, but does not rewrite them to fit a framework scheme.
5. A future, separately reviewed extension to `ontology/persistence` will express identity profiles and compile them to minting, validation, conformance fixtures, and runtime requirements. No generic runtime component may infer identifier semantics from a prefix, class name, graph name, or current store location.
6. Framework reference deployments may publish a concrete identity profile. A reference profile is opt-in, versioned, and does not become a universal adopter policy.

## Consequences

- ADR-A51 is superseded. Its proposed `urn:lattice` forms remain historical examples, not a normative framework requirement.
- `iri-policy.md` is retained as a historical proposed profile and redirects readers to the patterns catalogue.
- P0.3.7's validator becomes profile-aware. It validates the configured grammar and test vectors, rather than one hard-coded platform grammar.
- ADR-A54's named-graph layout and ADR-A63's reference types must be amended before ratification to consume selected topology and identity profiles rather than assume a universal environment, tenant, or graph-name structure.
- Any identity-profile vocabulary addition must be a separately scoped slice with a validation pack, compiler changes, and cross-runtime conformance tests. This ADR does not add terms to `ontology/persistence`.
- The guide makes the safety requirements explicit for hash bytes, canonicalization, blank nodes, key claims, key rotation, erasure, alias resolution, event positions, epoch durability, and retention. A deployment selecting one of these patterns inherits its stated requirements.
