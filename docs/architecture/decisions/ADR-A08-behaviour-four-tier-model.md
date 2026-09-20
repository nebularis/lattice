<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR A-08: Behaviour four-tier model

## Status

Accepted

## Context

Behaviour must distinguish what is declared from what occurred, what was executed, and what current state records exist. Collapsing those layers makes causality, replay, and invalidation ambiguous.

## Decision

Behaviour uses four mutually distinct semantic tiers:

1. Declaration — state spaces, states, transitions, triggers, guards, effects, allowance definitions, policies.
2. Occurrence — stimuli or facts observed that may satisfy trigger conditions.
3. Execution — evaluated transition executions and effect applications.
4. State record — durable occupancy or allowance-account state after execution.

No class serves more than one tier.

## Consequences

- State replay and invalidation can distinguish authored mechanism from observed runtime facts.
- Shapes can check tier separation directly.
- Gate 3 fixtures can test execution without confusing authored transition design with executed history.
