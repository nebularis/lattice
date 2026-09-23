<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A82: Framework-Neutral Identity Pattern Selection

**Status:** Proposed
**Date:** 2026-09-23
**Supersedes:** [ADR-A51](ADR-A51-iri-and-identity-policy.md)
**Related:** [IRI and Identity Patterns](../iri-identity-patterns.md), [RDF & SPARQL Patterns Guide](../rdf-sparql-patterns-guide.md), ADR-A54, ADR-A63, ADR-A68, ADR-A78
**Drafted by:** Agent following human architectural direction. Pending human ratification, see [phase-0-status.md](../../developer/status/phase-0-status.md).
**Amended:** 2026-09-23, point 5, before ratification (see "Amendment", below).

## Context

ADR-A51 attempted to select one IRI grammar and one identity policy for all LATTICE users. The subsequent reviews showed both specification gaps and a broader architectural error: LATTICE is a framework, while adopters already have domain identifiers, tenancy models, project structures, deployment environments, and graph-store topologies. A universal LATTICE grammar would either re-mint identifiers outside the framework's authority or encode one application topology as a framework rule.

The persistence substrate already models independently selectable aggregate, concurrency, ordering, receipt, topology, and uniqueness patterns. Identity must follow the same configuration-first approach.

## Decision

1. LATTICE supplies a framework-neutral catalogue of IRI and identity patterns, not one mandatory identifier grammar. The catalogue is [IRI and Identity Patterns](../iri-identity-patterns.md).
2. An adopter selects compatible patterns by resource role and deployment scope. Resource roles include external entities, runtime entities, aggregate roots, component nodes, authored lineages, content revisions, graph locators, key claims, and event occurrences.
3. Tenant, project or authoring context, environment, dataset, source system, and naming authority are independent dimensions. A selected profile decides which dimensions participate in an identifier. The framework does not equate or require any of them.
4. Existing adopted identifiers retain their naming authority. LATTICE records mappings and provenance where needed, but does not rewrite them to fit a framework scheme.
5. An extension to `ontology/persistence` expresses identity profiles and compiles them to minting recipes, conformance vectors, validation and runtime requirements. Executing a recipe is a runtime concern, served by the standalone minting libraries ([ADR-A84](ADR-A84-standalone-minting-libraries.md)) and by the normative [identity minting specification](../identity-minting-specification.md) for implementors who use neither. No generic runtime component may infer identifier semantics from a prefix, class name, graph name, or current store location.
6. Framework reference deployments may publish a concrete identity profile. A reference profile is opt-in, versioned, and does not become a universal adopter policy.

## Consequences

- ADR-A51 is superseded. Its proposed `urn:lattice` forms remain historical examples, not a normative framework requirement.
- `iri-policy.md` is reduced to a historical record (its body was removed on 2026-09-23) and redirects readers to the patterns catalogue.
- P0.3.7's validator becomes profile-aware. It validates the configured grammar and test vectors, rather than one hard-coded platform grammar.
- ADR-A54's named-graph layout and ADR-A63's reference types must be amended before ratification to consume selected topology and identity profiles rather than assume a universal environment, tenant, or graph-name structure.
- `ontology/persistence` (`spec/persistence.ttl` §12-§18, `shapes/constraints.ttl`) now specifies the identity-profile vocabulary named in `iri-identity-patterns.md` §14: identity strategy per resource role, epoch authority and guard scope, privacy class and erasure strategy, global-read strategy, retention mode, HTTP conditional form, first-write policy, deadlock policy, merge relation, and claim-scheme rotation. Skolemization strategy and alias-resolution strategy remain candidate, pending a follow-on slice. Compiler wiring is tracked in `docs/developer/status/persistence-compiler-iri-sync.md` (identity profiles resolved per resource role since its Slice 3). Minting recipes, conformance vectors and the minting libraries are tracked in `docs/developer/status/identity-minting.md`. TCK integration remains a follow-on.
- The guide makes the safety requirements explicit for hash bytes, canonicalization, blank nodes, key claims, key rotation, erasure, alias resolution, event positions, epoch durability, and retention. A deployment selecting one of these patterns inherits its stated requirements.

## Amendment (2026-09-23, before ratification)

Point 5 originally read "compiles them to minting, validation, conformance fixtures, and runtime requirements", which left open whether the compiler itself mints. It cannot at design time: minting needs a request's values, the claim secret and randomness, none of which exist when the compiler runs, and none of which SPARQL can provide. The amended wording splits minting three ways, as agreed with the human while scoping the `identity-minting` unit: the compiler produces **recipes** and **conformance vectors**, and **execution** happens at runtime, through the standalone libraries or an adopter's own implementation checked against the vectors.

