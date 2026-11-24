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

## Addendum (2026-11-24): a keyed graph construction takes the mapping review

**Status of this addendum:** Proposed.

A graph construction that gives one node for each value of a key merges the instances that share the key, as a join relates them, and a reviewer's judgement is needed where that merge is made. A keyed construction therefore requires mapping review, recorded as a finding in the way a join's is. A construction that gives a node for each instance merges nothing and requires none. The decision above is otherwise unchanged.
