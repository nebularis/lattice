<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A66: Principal Model Extension

**Status:** Proposed
**Date:** 2026-09-23
**Related:** Architecture Review §5.1, ADR-A63, ADR-A69
**Drafted by:** Agent, autonomous session (P0.1.12). Pending human ratification — see [phase-0-status.md](../../developer/status/phase-0-status.md).

## Context

Identity, authorization, and graph visibility need one extended principal shape shared by human users, ingestion services, and LLM-mediated agents, with graph visibility derived server-side rather than accepted from a client.

## Decision

```
Principal {
  subject, kind: human|service|agent,
  organisationId, tenantId,
  scope: { projects: [..], environments: [..] },     // explicit, never wildcard
  roles: [ scoped role claims ],
  graphVisibility: GraphSelector,                    // derived, never client-supplied
  entitlements: [..],
  delegation: { onBehalfOf?, chain: [..] }?,
  deadline, correlationId
}
```

**Rules:**

1. `graphVisibility` is derived server-side from roles, activation binding, and dataset binding, once per request. It is the only input to graph scoping. No component re-derives it or accepts it from elsewhere.
2. Service principals for ingestion are first-class, with their own credential lifecycle (rotation, expiry, per-route scoping), not OIDC end-user tokens. Service-principal roles are drawn from a role set disjoint from human roles (for example `ingest:route:*`, `query:projection:*`).
3. Agent principals are distinct from service principals. MORK's design constrains agents by named-graph perimeter; an LLM-mediated agent runs under a principal whose visibility is exactly its perimeter, and no component can widen it.
4. Delegation is recorded, never implied. When an effect is applied on behalf of a policy, provenance records the chain via `pty:Delegation`.
5. Break-glass is a procedure, not an absence of controls: a time-boxed elevated principal, requiring a second approver, emitting a governance ledger entry on issue and on every use, with all resulting writes tagged `cause.kind = admin` in the change feed (ADR-A57).

## Consequences

- A `Principal` constructed from a client-supplied `graphVisibility` is rejected (L1 test, P0.7.1).
- Role sets for service vs. human principals are disjoint by type, not just by convention — an ingestion credential cannot read the review queue (L8 test, P1.7.5).
- ADR-A63's environment scoping is the unit `Principal.scope.environments` binds to; project scope is authoring-only and does not grant runtime graph visibility.
