<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Phase 0 and 1 Validation Handoff

## Source and ownership

This handoff covers `mise.toml`, the Dev Container and Compose configuration, `platform/`, `workers/`, `contracts/events/`, developer documentation, and CI workflows. Existing ontology layers, Surface tooling, MORK tooling, and SPC sources remain owned by their existing modules and were not moved.

## Validation commands

Run from a clean network-enabled clone:

```text
mise install
mise run bootstrap
mise run check
docker compose -f deployment/compose/docker-compose.yml up -d
mvn -f platform/pom.xml verify
python -m pytest workers/tests
docker compose -f deployment/compose/docker-compose.yml down -v
```

Expected outcomes are successful root extraction and conformance checks, worker contract tests, Maven unit tests, and a running reference PostgreSQL, RabbitMQ, and Fuseki stack. The Phase 1 Java modules do not yet have Testcontainers integration tests or PostgreSQL-backed outbox persistence. Those remain bounded deployment gaps, not evidence of runtime integration.

## Environment

Reference services use PostgreSQL `5432` inside the Compose network, RabbitMQ `5672` and management UI `15672`, and Fuseki `3030`. Development-only credentials are `lattice` for the PostgreSQL user, database, and password, and Fuseki's `ADMIN_PASSWORD`. Do not use these values outside the local reference environment.

The request schema requires graph references with tenant ID, project ID, graph IRI, and revision hash. It also requires a profile ID, opaque job ID, and correlation ID. Browser tokens, credentials, and RDF payloads are prohibited.

## Dependency and compatibility status

The Java reactor resolves Jena 5.1.0 and JUnit 5.11.0 from Maven. The worker package resolves pytest only for its test extra. The root Yarn lockfile contains no external workspace dependencies. Docker image tags are present for the reference environment but immutable image digests must be resolved and committed by the network-enabled validation environment. No existing lockfiles were regenerated in this restricted environment.

No ontology schema migration occurs. The new event schemas are version `1.0.0`, additive, and do not change existing graph formats. The Compose stack creates disposable state only. Roll back by stopping it with `docker compose -f deployment/compose/docker-compose.yml down -v` and reverting the platform directories together.

## Restricted-environment statement

Validation was not executed in the restricted authoring environment. The local Windows host has neither Python nor the Python launcher on `PATH`, and has Java 8 but no Maven. Dependency resolution, containers, builds, tests, and CI execution therefore remain unverified.
