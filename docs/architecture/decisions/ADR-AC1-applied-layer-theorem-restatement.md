<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A-C1: Applied-Layer Theorem Restatement Policy

**Status:** Accepted
**Date:** 2026-09-17

## Context

An applied or deployment layer built on the substrate will sometimes prove a domain-specific theorem that generalises a substrate mechanism — for example, a completeness result about how many admissible-set regions a particular deployment's dimension set can produce. Such a result is genuinely useful to the deployment, but it is a fact about that deployment's specific configuration (its dimension count, its category partition, its scheme content), not a fact about the substrate mechanism itself.

## Decision

Where an applied layer proves a domain-specific theorem that generalises a substrate mechanism, the applied layer restates and proves it privately, in its own applied-layer documentation. The public substrate records only the generic mechanism and the generic laws that mechanism must satisfy (for example, Eligibility's strategy laws L1–L8). No applied-layer theorem, proof, numeric worked result, or deployment-specific finding is published in the public substrate, under any name, generic or otherwise.

This is a restatement boundary, not a secrecy rule about the mechanism itself: the substrate's own laws and their discharges are fully public. What stays out is the applied arithmetic — dimension counts, category assignments, specific numeric bounds — that would let a reader reconstruct a particular deployment's configuration from the substrate's own text.

## Consequences

- A substrate layer's README may state and prove a law (for example, "meet is commutative, associative, and idempotent for every registered strategy") without reference to any specific deployment's dimension set.
- An applied layer wanting to publish a generalisable finding follows [ADR-A-C2](ADR-AC2-clean-room-authoring-procedure.md): the generic version is authored first, from the generic premise, independent of the applied result, and only then checked against the applied result for sufficiency.
