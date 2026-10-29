<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A19: Staged compiler architecture and backend fan-out

**Status:** Accepted
**Date:** 2026-09-18
**Supersedes:** none
**Related:** ADR-A18 (Surface-to-MORK lowering boundary), ADR-A23 (MORK compiler family completion policy)
**Unit:** [`surface-mork-unified-projection`](../../developer/plans/surface-mork-unified-projection-plan.md) (epic)
**Source plan:** the Surface-MORK Unified Projection Program plan

## Context

The MORK enhancements analysis shows the compiler side has lagged the vocabulary side: MORK already models `ShapeMapping`, `RuleMapping`, and `QueryTemplate` generatively, but `tools/mork/src/mork2rml.py` identifies `ShapeMapping` and `RuleMapping` only to skip them, because it targets RML alone. Adding SPARQL, SHACL, SWRL, and native-IR compilers without a shared pipeline risks four separate readings of the same mapping graph, each free to diverge in normalisation, parameter resolution, or determinism guarantees.

## Decision

**Every backend compiler runs the same staged pipeline: validate, normalise, lower, compile, emit, record provenance.** Stage boundaries are explicit interfaces. A backend (RML, SPARQL, SHACL, SWRL, native IR) is an adapter attached after the shared validate/normalise/lower stages, not a parallel reimplementation of them.

## Consequences

- Determinism — identical input graph and profile identity produce identical output — is a property of the shared stages, checked once, rather than re-verified per backend.
- Adding a backend (ADR-A23) means writing a compile/emit adapter against a stable intermediate model, not re-deriving parameter resolution or dependency ordering.
- `tools/mork/src/mork2rml.py`'s existing behaviour for RML is retained as the reference adapter. New adapters are added beside it rather than by modifying its `ShapeMapping`/`RuleMapping` skip logic in place.
- The staged model is a prerequisite for ADR-A21's composition rules and ADR-A27's invalidation planning, both of which depend on stage boundaries being explicit enough to reason about.
