<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR A-10: Behaviour activation policy

## Status

Accepted

## Context

A selected transition still needs a declared rule for when it becomes effective. Immediate, deferred, and manually released transitions are semantically different and must not be inferred from operational timing.

## Decision

Every transition definition declares one `bhv:activationPolicy`. Baseline policies are:

- `bhv:ImmediateActivation`
- `bhv:DeferredActivation`
- `bhv:ManualActivation`

A deferred transition may additionally declare one scheduling or reset recurrence through Quantification, but the policy itself remains a Behaviour concern.

## Consequences

- Execution timing is part of the semantic model.
- Deferred and manual flows are representable without inventing engine-specific state.
- Quantified schedules integrate through projection rather than by duplicating time logic in Behaviour.
