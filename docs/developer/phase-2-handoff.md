<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Phase 2 Validation Handoff

## Scope

This in-progress Phase 2 slice adds the Surface revision lifecycle, immutable release candidates, Surface worker job schemas, and graph-reference dispatch. It preserves `tools/surface`, the literate Surface specification, extraction rules, and existing fixtures.

It also adds the `SurfaceRevisionRepository` ledger port, an in-memory concurrency test adapter, a PostgreSQL JDBC adapter and migration, typed transition commands, a framework-neutral OpenAPI contract, and an in-memory immutable graph-family registry. No HTTP endpoint, migration runner, durable graph-family registry, or physical graph-store adapter is included yet.

## Commands

Run from a clean network-enabled clone:

```text
mise install
mise run bootstrap
mvn -f platform/pom.xml -pl surface-workflow test
python -m pytest workers/tests/test_surface_jobs.py
python -m pytest workers/tests/test_surface_executor.py workers/tests/test_surface_consumer.py workers/tests/test_rabbitmq_surface_worker.py
python -m unittest tools.surface.test_surface -v
python -m tools.phase8_conformance
yarn install
yarn check
yarn build
yarn test
```

Expected results are valid Surface schemas, lifecycle tests proving approval precedes generation, stale-write tests rejecting optimistic-concurrency conflicts, graph-family tests rejecting graph-IRI reuse with a different revision hash, worker tests rejecting RDF and command payloads, and existing compiler conformance results unchanged.

The command service must report a stale-version conflict before evaluating an action against a newer revision. It must report an invalid lifecycle transition only when the expected version matches the current revision.

Surface consumer tests must prove that an exact job retry republishes its cached result without re-running the executor, a job ID reused with different request content is rejected, and a failed publish does not mark a job as processed. The integration environment must then test the same behavior using a durable store and RabbitMQ acknowledgement semantics.

## Inputs and Preconditions

The worker integration must resolve graph references to isolated copies of the SaaS subscription currency, clinical trial crosswalk, and employment job-family fixture graphs. It must submit generation, parity, and invalidation work with distinct opaque job IDs and a propagated correlation ID. Invalidation supplies its generated manifest through `manifestGraph`, never by source-graph order.

RabbitMQ, PostgreSQL, and Fuseki are needed for end-to-end worker-path testing. Apply `platform/surface-workflow/src/main/resources/db/migration/V1__surface_revision_ledger.sql` through the selected migration runner before exercising revision updates. Seed the reference tenant and project consistently across contract, profile, manifest, and source graphs. The job handler must invoke compiler operations through a trusted graph resolver and execution adapter, never from request fields. Materialize each graph in the canonical byte form used to calculate its revision hash, verify the SHA-256 value, and reject paths outside the worker directory before compiler invocation.

Apply `workers/sql/V1__processed_surface_jobs.sql` before starting a durable worker. Exercise a successful acknowledgement, malformed-message dead lettering without requeue, transient publish failure with requeue, exact duplicate delivery, and job-ID reuse with a different request digest. Verify that result publishing and the receiving control-plane result handler are idempotent by opaque job ID.

## Outstanding Phase 2 Work

Phase 2 is authoring complete. The Surface Contract Studio, OpenAPI contract, lifecycle and graph-family persistence ports, trusted compiler executor, durable worker store, RabbitMQ adapter, worker tests, E2E browser definitions, existing Surface fixtures, CI tasks, ADRs, and architecture documentation are present.

Validation remains outstanding. The validation environment must run the ledger and graph-family migrations against PostgreSQL, regenerate and review `yarn.lock`, install Playwright browsers, execute Studio E2E tests, exercise real Fuseki materialization and output publication, and verify RabbitMQ retry, dead-letter, duplicate-delivery, and result-recording behavior. The current authoring environment did not run these commands.

## Restricted-environment Statement

This authoring environment has no usable Python interpreter, Maven, or Java 21 toolchain on `PATH`. The commands above were not run locally. JSON parsing and editor diagnostics were the available static checks.
