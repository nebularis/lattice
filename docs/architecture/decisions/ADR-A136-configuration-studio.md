<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A136: Configuration Studio, for authoring configuration against an applied ontology

**Status:** Accepted 2026-10-28, with its addendum and amendment. Its second amendment of 2026-10-28, on how the store is written and where it is kept, was accepted the same day. A third, on deploying the writers apart on a super stream, is Proposed
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

Drafted on 2026-10-27 by the unit, built autonomously at the maintainer's request. The decisions taken alone are CS-D1 to CS-D9 in the [status record](../../developer/status/config-studio.md). The maintainer accepted it, with the addendum and the amendment, on 2026-10-28, and ratified CS-D1 to CS-D3, CS-D8, CS-D9, CS-D11, CS-D13 and CS-D14, with CS-D6 and CS-D7 superseded by the amendment. CS-D4, a job's status written by the worker into the job graph and read from the store, is reopened as PDD-13 in the [pending design decisions](../../developer/pending-design-decisions.md), since every poll and every worker write meets in the store, and we have no model of concurrent writes there, nor yet the usage patterns to build one from. The maintainer decided it the same day as the second amendment records. CS-D5 (as forms that read SHACL shapes first, then `rdfs:domain` and `rdfs:range`), CS-D10 and CS-D12 were ratified the same day.

## Addendum, 2026-10-27: vocabulary, quantification and eligibility (Accepted 2026-10-28)

The studio keeps three more configurations, `vocabulary`, `quantification` and `eligibility`, as graphs revisioned and saved like persistence and surface, and validated by their layers' own shapes as the author edits. A vocabulary validation also resolves every scheme contract with `tools/vocabulary` for every time segment and set of scopes its bindings draw. An eligibility validation also compiles every condition with `tools/mork_compilers`, expands each concept condition over its resolved scheme, and decides each `elg:Question` with the condition's compiled SPARQL against the decision the author expects of it, given as `cst:expectedDecision`. A question is the eligibility layer's own input, so a test is the query a deployment would run on it. The reference evaluator is not used: it is a test-time oracle (ADR-A-FM3). A job's body is every configuration as edited, and its target names the one checked. Features that wait on other work are shown and marked as under construction. Decision 4 and the rest stand.

## Amendment, 2026-10-28: a supported component (Accepted 2026-10-28)

The maintainer decided that the studio is to be supported, meaning developed and maintained with the ontologies and released with them once a release policy exists, and that this is an amendment to this record rather than a new one, since it is still Proposed. Decision 1 now says so, and the title no longer calls the studio a proof of concept. With it the `cst:` namespace drops `poc/` from its IRI, while no workspace is kept outside an in-memory store, so nothing needs migrating. Decision 3's HTTP server is Helidon SE's WebServer, since the JDK's `com.sun.net.httpserver` is a JDK module outside Java SE that another JVM need not ship. Decision 4 adds RDF/XML. Which software a release carries, and how it is versioned, is the release policy's own decision, beside ADR-A129. The other decisions stand.

## Amendment, 2026-10-28: partitioned writers and an on-disk store (Accepted 2026-10-28)

The maintainer decided the design on 2026-10-28, after reopening how a job's status reaches the service (CS-D4). It changes decisions 4, 5 and 7, and the others stand.

1. **One writer per workspace at a time.** The service and the worker never write the store. Each write is a command, keyed by its workspace's id, published to a consistent-hash exchange that routes it to one of a fixed number of partition queues. Each queue has a single active consumer, so the writes of one workspace, its jobs included, are applied in order by one writer, which needs no lock to guard a revision. A deployment sets how many writers it runs, from one to the number of partitions. A second instance's writers stand by and take over a partition whose writer goes away.
2. **A save still answers at once.** The service waits for the writer's reply on RabbitMQ's direct reply-to, so the browser sees `204`, `412` or `422` as before. A write no writer applied in time expires rather than being applied after the caller was told it failed, and the caller gets `503`.
3. **The worker sends its result, never writes it.** A job's status, report and artefacts go to the job's workspace's writer as a `job-update`. The writer refuses an update that changes anything on the job but its status and results, compared by value, and drops an update for a job deleted meanwhile.
4. **The writer checks what it receives,** whatever its sender checked (PRI-75, STD-279): the ids, the graphs a command may carry, part membership, and a job's references.
5. **On disk.** Fuseki keeps the studio's dataset in TDB2, in the user's data folder or a folder a deployment names, so workspaces outlive the application. Jobs are kept there too, and finished jobs are deleted after a retention a deployment sets, 30 days by default.
6. **Samples are copied.** A workspace made from a sample is a copy that records which sample it came from, so nothing is loaded at start and a later change to a sample does not reach it.
7. **Export and import.** A workspace exports as one TriG file of every graph but its jobs, and imports under a new id with its revisions, so it can be kept, shared and moved independently of the store's format.

**Rejected.** Writers handed messages in turn, which would let two writers hold one workspace's graphs at once. A writer per workspace, whose number grows with use. Jobs in memory beside an on-disk store, which the maintainer declined so past results can be read again. Samples loaded at start as read-only workspaces.

**Consequences.** A save costs a broker round trip more than it did. TDB2 applies one update at a time per dataset (TSD-42), so more writers do not write faster on one dataset, and more throughput needs a dataset per group of partitions. A delete leaves space TDB2 reclaims only by compaction. Any client of the broker can send a command, so the broker is as trusted as the store.


## Amendment, 2026-10-28: the store writers deployed apart, on a super stream (Proposed)

The maintainer decided the design on 2026-10-28, reopening where the writers of the second amendment run. It changes that amendment's decisions 1 and 2, and the others stand.

1. **Three deployables.** `config-studio-service` serves HTTP, reads the store and publishes jobs and writes. `config-studio-writer` is the only component that writes the store. The Python worker validates and compiles. What the service and the writer share, the store's graphs and terms, the workspace model, the commands and the writer's rules, is the module `config-studio-core`.
2. **Writes travel on a RabbitMQ super stream.** A write is published to the partition its workspace's id selects, so a workspace's writes stay in order in one partition. The writers form one single-active-consumer group on the super stream, so RabbitMQ gives each partition to one live writer instance, spreads the partitions across the instances that run, and moves a partition when an instance joins or leaves. A writer stores each partition's offset after a batch, and the receipts of the second amendment make a write delivered again after a move a no-op. A deployment scales writers by running more instances.
3. **The service and the worker only read the store.** Fuseki serves one database as two services, one that reads and one that updates, and only the writer is given the second.
4. **A write the service did not hear back about may still apply.** A stream keeps a write until a writer reaches it. The service waits for the writer's reply, and past that asks the store for the write's receipt, answering `503` only when it finds none.
5. **One process only for tests.** Without a broker the service writes through a writer of its own, for unit tests, its self-check and a demonstration with no broker. `studio:up` runs the writer as its own process.

**Rejected.** The writers inside the service, which shared its failure domain, its broker connection and its write access, and could not be scaled or deployed apart. Classic queues with a single active consumer each, which fail over but give every partition to the first instance to start, so spreading them would need each instance configured by hand.

**Consequences.** RabbitMQ needs its stream plugin and a port for the stream protocol, advertised at an address the writers reach. Each partition keeps a week of writes or 1 GiB. TDB2 applies one update at a time per dataset (TSD-42), so more writer instances add availability and parallel checking, not commits, while one database serves them.
