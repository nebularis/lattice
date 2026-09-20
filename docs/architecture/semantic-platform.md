<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Shared Semantic Platform

The Phase 1 platform separates semantic graph access, authorization, operational state, and worker execution.

`platform/semantic-dataset-spi` owns portable graph references, capability discovery, and dataset snapshots. A graph reference includes tenant, project, graph IRI, and immutable revision hash. Job payloads carry only these references. They do not carry RDF, credentials, browser tokens, or unrestricted endpoint details.

`platform/semantic-dataset-fuseki` is the initial adapter. It reads a named graph from Fuseki and reports its serialized content hash. Further adapters must pass the same SPI contract tests before they are enabled.

`platform/semantic-policy` applies tenant, project, and role checks before a graph reference reaches an adapter. OIDC integration must construct `Principal` from verified claims at the HTTP boundary. It must not trust principal data sent in AMQP messages.

`platform/platform-outbox` captures CloudEvents with an idempotency key and relays pending records through a RabbitMQ publisher. Publisher failure leaves a record pending for retry. The publisher declares a durable topic exchange and a dead-letter exchange. The initial outbox storage is in memory for unit tests. A PostgreSQL-backed implementation is required before the platform can be deployed.

The Python `workers/` package is the initial worker boundary. Its validation handler verifies the version-one request contract and calls a supplied graph-reference validator. AMQP transport, retry scheduling, dead-letter queues, and PostgreSQL persistence are deployment adapters to be added with the corresponding integration tests.

## Component Ownership

| Component | Owns | Does not own |
|---|---|---|
| `semantic-dataset-spi` | Graph references, snapshots, and capability vocabulary | Storage-provider configuration or authorization policy |
| `semantic-dataset-fuseki` | Named-graph read adapter for Fuseki | Generic SPARQL and RDF4J support |
| `semantic-policy` | Tenant, project, and role checks at the control boundary | OIDC token parsing or identity-provider configuration |
| `platform-outbox` | Idempotency key, CloudEvent representation, pending-record relay semantics | Durable SQL persistence and broker lifecycle |
| `workers` | Validation of untrusted graph-reference job envelopes | Caller identity, graph authorization, or broker connection lifecycle |

## Graph Reference Contract

A graph reference is the only portable description of semantic input across runtimes:

```text
tenant ID + project ID + absolute graph IRI + immutable revision hash
```

The control plane authorizes the tenant and project before it asks a dataset adapter to resolve the IRI. The revision hash identifies the required immutable content. A worker must verify the received reference shape and scope, then ask a trusted resolver for the content. It does not resolve an arbitrary user-provided endpoint and it does not accept an RDF document in the event payload.

## Job and Event Flow

```text
browser or API command
	-> authenticated control boundary
	-> graph policy check
	-> transactional outbox record with idempotency key and correlation ID
	-> RabbitMQ publisher
	-> Python worker job envelope
	-> trusted graph resolver and semantic implementation
	-> result event and correlated operational record
```

The source of semantic truth remains RDF. PostgreSQL is intended to retain operational facts such as jobs, outbox rows, retries, and lifecycle records. RabbitMQ carries commands and results, not graph payloads. Correlation IDs must flow from request to outbox, event, worker result, and later release receipt.

## Failure and Retry Behavior

The outbox returns the same record for repeated enqueue requests with the same idempotency key. A publisher error leaves the record pending. The RabbitMQ publisher declares durable topic and dead-letter exchanges, while queue topology and retry policy are deployment concerns. A worker result must be idempotently recorded by its consumer before a retry can be treated as complete.

The present in-memory outbox and unit tests establish the contract. A production implementation still needs PostgreSQL transactional storage, message acknowledgement policy, retry schedule, dead-letter replay procedure, and Testcontainers validation across PostgreSQL, RabbitMQ, and Fuseki.

## Trust and Extension Rules

OIDC-derived identity must be converted to `Principal` at an authenticated boundary. AMQP messages cannot construct or modify a principal. New dataset adapters must declare their capabilities and pass the same contract tests as Fuseki. An unsupported capability is an explicit failure, not an adapter-specific fallback.

See [ADR-A30](../adr/ADR-A30-shared-semantic-platform-cross-runtime-boundary.md) for the durable decision and [the implementation map](implementation-map.md) for the cross-phase dependency map.
