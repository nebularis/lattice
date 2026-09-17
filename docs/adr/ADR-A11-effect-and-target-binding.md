<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR A-11: Effect payload and target binding contract

## Status

Accepted

## Context

Behaviour effects write across layers. Without an explicit target and payload contract, a transition may be declared but remain operationally uninterpretable.

## Decision

Each `bhv:EffectDefinition` declares:

- one `bhv:targetKind`
- at least one explicit target binding to Instrument or Party
- an optional payload space or quantity binding where the effect carries quantified state

Gate 3 defines allowance effects only for `bhv:Sequential` absorption. `bhv:Proportional` is declared in vocabulary but rejected by Gate 3 constraints, making the deferred status visible.

## Consequences

- Effects can be validated before runtime.
- Cross-layer writes remain projection-driven and auditable.
- The extent profile is usable now for sequential consumption and explicitly not yet usable for proportional consumption.
