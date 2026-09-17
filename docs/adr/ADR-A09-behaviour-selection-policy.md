<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR A-09: Behaviour selection policy

## Status

Accepted

## Context

A trigger may make several transitions eligible at once. Behaviour needs a declared selection rule so execution is deterministic and auditable.

## Decision

Behaviour declares selection policy explicitly on a transition definition via `bhv:selectionPolicy`, using mechanism vocabulary rather than implementation-local logic. Baseline policies are:

- `bhv:SingleMatch`
- `bhv:AllMatches`
- `bhv:PriorityOrdered`

When `PriorityOrdered` is used, transition definitions must also declare one integer `bhv:priority`.

## Consequences

- Ambiguity is visible in authored data rather than hidden in an engine.
- Deterministic selection can be validated structurally.
- Multi-profile conformance can compare outcomes across evaluators.
