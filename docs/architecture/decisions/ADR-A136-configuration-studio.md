<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A136: Configuration Studio, a proof of concept for authoring persistence and surface configuration

**Status:** Proposed
**Date:** 2026-10-27
**Related:** [ADR-A118](ADR-A118-word-authoring-proof-of-concept.md) (the runtime split this follows), [ADR-A38](ADR-A38-surface-output-publication-and-studio-authoring-boundary.md) (the Surface Contract Studio), [ADR-A78](ADR-A78-persistence-profile-substrate-and-aggregate-boundaries.md) and [ADR-A79](ADR-A79-persistence-compiler-toolchain.md) (the persistence substrate and its compiler), [ADR-A30](ADR-A30-shared-semantic-platform-cross-runtime-boundary.md) and [ADR-A35](ADR-A35-trusted-surface-worker-execution-boundary.md) (graph references across runtimes), [ADR-A135](ADR-A135-contract-first-wire-types.md) (wire types)
**Unit:** [`config-studio`](../../developer/plans/config-studio.md)

## Context

An adopter configures how its applied ontology is stored, with `dal:` profiles that `tools/persistence` compiles into SPARQL, and how it is surfaced, with `srf:` contracts that `tools/surface` compiles. Both are written by hand in Turtle today. The author learns which properties a profile takes, which values each allows and which baseline terms a read path may traverse from the specifications, and learns of a mistake only when a compiler or a SHACL run refuses it. The Surface Contract Studio (ADR-A38) shows typed Surface editing but is fixture-backed: it reads no baseline and never validates or compiles.

The `dal:` and `srf:` specifications already hold what a form needs: each property's `rdfs:domain`, `rdfs:range` and `rdfs:comment`, and each closed set of values as a class whose individuals are typed with it.

## Decision

1. **Status.** The studio is a proof of concept, as ADR-A118's add-in is. Its code, its HTTP API, its job messages and its `cst:` vocabulary are not platform contracts. Nothing outside it may depend on them, and they may change or be removed without deprecation.
2. **Placement**, inside existing roots:

   | Path | Holds |
   |---|---|
   | `apps/config-studio` | the browser application, React and TypeScript, with its unit and browser tests |
   | `platform/config-studio-service` | the Java service, a Maven module of `platform/pom.xml` |
   | `workers/src/lattice_workers/config_studio_*.py` | the Python job that validates and compiles |
   | `contracts/config-studio` | the `cst:` vocabulary, the AMQP topology and the samples |
   | `deployment/compose/config-studio` | an optional compose file for Fuseki and RabbitMQ |
   | `tools/config_studio_stage.py` | staging of the vocabulary and samples the service serves |

3. **Runtimes.** Java serves HTTP and the store, through the JDK's HTTP server and Apache Jena. Python validates and compiles, as a RabbitMQ job, with pySHACL and the repository's own compilers, so the studio answers as `mise run check` would. A validation of persistence configuration also compiles it, because the `dal:` shapes target the dimension classes and do not see a `dal:DataAccessProfile` that declares several dimensions at once.
4. **RDF on the wire.** Every HTTP body is Turtle. Job descriptions, results, findings and generated artefacts are graphs in the `cst:` vocabulary, and findings of either compiler are `sh:ValidationResult`s, so the browser reads one shape of finding. The AMQP message is a job's IRI and nothing else, and the worker reads the job's inputs by graph reference. Inputs are immutable by construction: a job's input graph is written once under its IRI, and each baseline revision is a new graph. Since no JSON message crosses a process boundary, ADR-A135 has no type to govern here, and its decision 3 leaves a proof of concept outside it in any case.
5. **The store is the only state.** The service holds no registry. A workspace's revisions are triples in its own graph, and a job's status is read from the job's graph, which the worker writes. A save replaces a configuration graph and moves its revision in one SPARQL Update request, guarded by `If-Match` on the revision.
6. **Forms are derived from the vocabularies.** The browser derives every field and option from the `dal:`, `srf:`, `fnd:` and `voc:` documents the service serves. It declares only how an editor groups classes into sections and which properties pick a baseline term.
7. **Store.** Fuseki through Jena's `RDFConnection`, or an in-memory dataset for tests, with the same code. It does not use or extend the semantic dataset SPI (ADR-A71, ADR-A75), and its graph names do not follow ADR-A54.

**Rejected.** A JSON view contract per screen, which would restate what the vocabularies define. SHACL validation in the service with Jena, which differs from pySHACL on SHACL-SPARQL corners the repository's checks rely on. Javalin, whose Jetty line has carried advisories, where the JDK's server suffices. A free-text Turtle editor for configuration, which [ux-design.md §2.5](../ux-design.md) lists as an anti-pattern.

## Consequences

- An author configures a baseline without knowing the `dal:` and `srf:` vocabularies by heart, and sees a violation on the field that caused it while editing.
- When `ontology/persistence` or `ontology/surface` adds a property or a value, the studio offers it without a change.
- The studio depends on Fuseki and RabbitMQ to validate. Without them it opens nothing.
- Validation runs as a job, so feedback takes a broker round trip and a compile, about a second on a laptop.
- No authentication: the service binds to `127.0.0.1` and refuses cross-origin writes by requiring `text/turtle` without answering a preflight. A shared deployment needs authentication first.

## Provenance

**Unit:** [`config-studio`](../../developer/plans/config-studio.md) (plan), [sketch](../../developer/sketches/config-studio.md), slices CS0 to CS4.

Drafted on 2026-10-27 by the unit, built autonomously at the maintainer's request. The decisions taken alone are CS-D1 to CS-D9 in the [status record](../../developer/status/config-studio.md). The maintainer has not accepted it.
