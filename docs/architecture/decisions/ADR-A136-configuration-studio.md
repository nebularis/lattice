<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A136: Configuration Studio, for authoring configuration against an applied ontology

**Status:** Accepted 2026-10-28, with its addendum and amendment. How a job's status reaches the service, in decisions 4 and 5, is reopened (see Provenance)
**Date:** 2026-10-27
**Related:** [ADR-A118](ADR-A118-word-authoring-proof-of-concept.md) (the runtime split this follows), [ADR-A38](ADR-A38-surface-output-publication-and-studio-authoring-boundary.md) (the Surface Contract Studio), [ADR-A78](ADR-A78-persistence-profile-substrate-and-aggregate-boundaries.md) and [ADR-A79](ADR-A79-persistence-compiler-toolchain.md) (the persistence substrate and its compiler), [ADR-A30](ADR-A30-shared-semantic-platform-cross-runtime-boundary.md) and [ADR-A35](ADR-A35-trusted-surface-worker-execution-boundary.md) (graph references across runtimes), [ADR-A135](ADR-A135-contract-first-wire-types.md) (wire types)
**Unit:** [`config-studio`](../../developer/plans/config-studio.md)

## Context

An adopter configures how its applied ontology is stored, with `dal:` profiles that `tools/persistence` compiles into SPARQL, and how it is surfaced, with `srf:` contracts that `tools/surface` compiles. Both are written by hand in Turtle today. The author learns which properties a profile takes, which values each allows and which baseline terms a read path may traverse from the specifications, and learns of a mistake only when a compiler or a SHACL run refuses it. The Surface Contract Studio (ADR-A38) shows typed Surface editing but is fixture-backed: it reads no baseline and never validates or compiles.

The `dal:` and `srf:` specifications already hold what a form needs: each property's `rdfs:domain`, `rdfs:range` and `rdfs:comment`, and each closed set of values as a class whose individuals are typed with it.

## Decision

1. **Status.** The studio is a supported part of LATTICE. We develop and maintain it with the ontologies, and it becomes part of a release once the release policy defines how software is released. Its HTTP API, its job messages and its `cst:` vocabulary (`https://www.nebularis.org/neuro-semantic/lattice/config-studio#`) are its contracts, in `contracts/config-studio`. A change that would break a client is announced there and deprecated before it is removed. ADR-A135 governs any JSON type they gain.
2. **Placement**, inside existing roots:

   | Path | Holds |
   |---|---|
   | `apps/config-studio` | the browser application, React and TypeScript, with its unit and browser tests |
   | `platform/config-studio-service` | the Java service, a Maven module of `platform/pom.xml` |
   | `workers/src/lattice_workers/config_studio_*.py` | the Python job that validates and compiles |
   | `contracts/config-studio` | the `cst:` vocabulary, the AMQP topology and the samples |
   | `deployment/compose/config-studio` | an optional compose file for Fuseki and RabbitMQ |
   | `tools/config_studio_stage.py` | staging of the vocabulary and samples the service serves |

3. **Runtimes.** Java serves HTTP and the store, through Helidon SE's WebServer and Apache Jena. Python validates and compiles, as a RabbitMQ job, with pySHACL and the repository's own compilers, so the studio answers as `mise run check` would. A validation of persistence configuration also compiles it, because the `dal:` shapes target the dimension classes and do not see a `dal:DataAccessProfile` that declares several dimensions at once.
4. **RDF on the wire.** Every HTTP body is RDF, Turtle by default or RDF/XML by content negotiation, so an XSLT can read what a configuration means. A request body names its syntax by `Content-Type`, and an RDF/XML body may not declare a DTD. Job descriptions, results, findings and generated artefacts are graphs in the `cst:` vocabulary, and findings of either compiler are `sh:ValidationResult`s, so the browser reads one shape of finding. The AMQP message is a job's IRI and nothing else, and the worker reads the job's inputs by graph reference. Inputs are immutable by construction: a job's input graph is written once under its IRI, and each baseline revision is a new graph. Since no JSON message crosses a process boundary, ADR-A135 has no type to govern here, and its decision 3 leaves a proof of concept outside it in any case.
5. **The store is the only state.** The service holds no registry. A workspace's revisions are triples in its own graph, and a job's status is read from the job's graph, which the worker writes. A save replaces a configuration graph and moves its revision in one SPARQL Update request, guarded by `If-Match` on the revision.
6. **Forms are derived from the vocabularies.** The browser derives every field and option from the `dal:`, `srf:`, `fnd:` and `voc:` documents the service serves. It declares only how an editor groups classes into sections and which properties pick a baseline term.
7. **Store.** Fuseki through Jena's `RDFConnection`, or an in-memory dataset for tests, with the same code. It does not use or extend the semantic dataset SPI (ADR-A71, ADR-A75), and its graph names do not follow ADR-A54.

**Rejected.** A JSON view contract per screen, which would restate what the vocabularies define. SHACL validation in the service with Jena, which differs from pySHACL on SHACL-SPARQL corners the repository's checks rely on. Javalin, whose Jetty line has carried advisories. The JDK's `com.sun.net.httpserver`, which our first version used, since it is a JDK module outside Java SE that another JVM need not ship. Netty, Undertow, Vert.x and embedded Tomcat, for the advisories each has carried. A free-text Turtle editor for configuration, which [ux-design.md §2.5](../ux-design.md) lists as an anti-pattern.

## Consequences

- An author configures a baseline without knowing the `dal:` and `srf:` vocabularies by heart, and sees a violation on the field that caused it while editing.
- When `ontology/persistence` or `ontology/surface` adds a property or a value, the studio offers it without a change.
- The studio depends on Fuseki and RabbitMQ to validate. Without them it opens nothing.
- Validation runs as a job, so feedback takes a broker round trip and a compile, about a second on a laptop.
- Every component validates what it receives, whatever its client has checked (PRI-75, STD-279): the service checks a body's size, type, syntax and part membership and every identifier, and the worker reads only the graphs its own job may name.
- No authentication: the service binds to `127.0.0.1` and refuses cross-origin writes by requiring `text/turtle` without answering a preflight. A shared deployment needs authentication first.

## Provenance

**Unit:** [`config-studio`](../../developer/plans/config-studio.md) (plan), [sketch](../../developer/sketches/config-studio.md), slices CS0 to CS4.

Drafted on 2026-10-27 by the unit, built autonomously at the maintainer's request. The decisions taken alone are CS-D1 to CS-D9 in the [status record](../../developer/status/config-studio.md). The maintainer accepted it, with the addendum and the amendment, on 2026-10-28, and ratified CS-D1 to CS-D3, CS-D8, CS-D9, CS-D11, CS-D13 and CS-D14, with CS-D6 and CS-D7 superseded by the amendment. CS-D4, a job's status written by the worker into the job graph and read from the store, is reopened as PDD-13 in the [pending design decisions](../../developer/pending-design-decisions.md), since every poll and every worker write meets in the store, and we have no model of concurrent writes there, nor yet the usage patterns to build one from. The studio keeps it as built until PDD-13 is decided. CS-D5, CS-D10 and CS-D12 wait on the maintainer's questions.

## Addendum, 2026-10-27: vocabulary, quantification and eligibility (Accepted 2026-10-28)

The studio keeps three more configurations, `vocabulary`, `quantification` and `eligibility`, as graphs revisioned and saved like persistence and surface, and validated by their layers' own shapes as the author edits. A vocabulary validation also resolves every scheme contract with `tools/vocabulary` for every time segment and set of scopes its bindings draw. An eligibility validation also compiles every condition with `tools/mork_compilers`, expands each concept condition over its resolved scheme, and decides each `elg:Question` with the condition's compiled SPARQL against the decision the author expects of it, given as `cst:expectedDecision`. A question is the eligibility layer's own input, so a test is the query a deployment would run on it. The reference evaluator is not used: it is a test-time oracle (ADR-A-FM3). A job's body is every configuration as edited, and its target names the one checked. Features that wait on other work are shown and marked as under construction. Decision 4 and the rest stand.

## Amendment, 2026-10-28: a supported component (Accepted 2026-10-28)

The maintainer decided that the studio is to be supported, meaning developed and maintained with the ontologies and released with them once a release policy exists, and that this is an amendment to this record rather than a new one, since it is still Proposed. Decision 1 now says so, and the title no longer calls the studio a proof of concept. With it the `cst:` namespace drops `poc/` from its IRI, while no workspace is kept outside an in-memory store, so nothing needs migrating. Decision 3's HTTP server is Helidon SE's WebServer, since the JDK's `com.sun.net.httpserver` is a JDK module outside Java SE that another JVM need not ship. Decision 4 adds RDF/XML. Which software a release carries, and how it is versioned, is the release policy's own decision, beside ADR-A129. The other decisions stand.

