<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A41: Surface Projection to MORK staging boundary

**Status:** Accepted
**Date:** 2026-09-20
**Related:** Phase 4, ADR-A18, ADR-A19, ADR-A25, ADR-A35

## Context

Projection contracts express mapping intent but do not directly generate executable artifacts. Lowering must preserve deterministic role and backend-policy evidence while preventing Surface authors from activating mappings into a MORK estate.

## Decision

Lower Projection contracts only through a graph-reference job into an immutable MORK staging namespace. Requests cannot supply active mapping targets, RDF payloads, credentials, or commands. Joins require mapping review. Derivations and expansions require engineering review. Every backend policy is deterministic-only and prohibits LLM completion.

## Consequences

- The Technical Inspector shows staging identity, MCN state, dependencies, capabilities, and review requirement only.
- MORK governance owns activation. Phase 4 introduces no active-mapping write capability.
- The ARR projection fixture is the reference lower-job corpus. RabbitMQ and graph-store validation remain offsite.
