<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A30: Shared semantic platform and cross-runtime boundary

**Status:** Accepted
**Date:** 2026-09-19
**Supersedes:** none
**Related:** Phase 1, ADR-A13, [semantic platform architecture](../semantic-platform.md)

## Context

Surface and MORK require common graph access, authorization, job correlation, and operational reliability. Their established semantic algorithms are implemented in Python, while the planned control plane is Java. Passing RDF documents or credentials between browser, control plane, broker, and worker would duplicate sensitive data and obscure immutable graph provenance.

## Decision

Use scoped immutable graph references as the cross-runtime contract. A reference contains tenant ID, project ID, absolute graph IRI, and revision hash. Java owns the portable dataset SPI, graph-scope policy, and outbox boundary. Python workers validate graph-reference-only job envelopes and invoke trusted graph-resolving adapters. RabbitMQ is the cross-runtime transport boundary. PostgreSQL is operational state, and RDF remains semantic source of truth.

## Consequences

- Event schemas must exclude RDF payloads, credentials, browser tokens, and executable commands.
- Each adapter declares capabilities and fails unsupported capabilities explicitly.
- Tenant and project scope is checked before graph resolution. Worker messages are not an authority for user identity.
- The in-memory outbox and adapter tests establish behavior only. PostgreSQL persistence, Testcontainers, and end-to-end AMQP retry validation remain required before deployment.
