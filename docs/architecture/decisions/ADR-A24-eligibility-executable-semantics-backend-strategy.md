<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A24: Eligibility executable semantics and backend strategy

**Status:** Accepted
**Date:** 2026-09-18
**Supersedes:** none
**Related:** ADR-A23 (MORK compiler family completion policy), ADR-A07 (Eligibility authoring direction), ADR-A03 (condition taxonomy), ADR-A04 (interval overlap law split)
**Source plan:** [surface-mork-unified-projection-delivery-plan.md](../../../ontology/surface/docs/surface-mork-unified-projection-delivery-plan.md)

## Context

Eligibility conditions — interval containment, compatibility operations — are declarative and have no executable form today. `ontology/surface/docs/MorkEnhancements.md`'s worked credit-score example shows a `mork:RuleMapping` sketch generating a SWRL rule, but also states plainly that OWL reasoning alone cannot compute interval containment, and that SPARQL, SHACL, and SWRL backends need to agree on the same semantics rather than each encoding it separately.

## Decision

**A shared executable IR captures Eligibility's semantic core**: interval containment, three-valued outcomes (permitted, denied, undetermined), diagnostics with source trace, and profile aggregation (all-required, any-sufficient). Backend delivery order is native evaluator and SPARQL first, SHACL for readiness and diagnostics second, SWRL for positive monotonic classifications third — SWRL only where its Horn-clause, monotonic character can express the outcome, which excludes `undetermined` and excludes any outcome that depends on absence of evidence.

## Consequences

- Eligibility gains an IR layer between its declarative conditions and MORK's mapping graph, consumed by the SPARQL, SHACL, and SWRL compilers from ADR-A23 rather than each backend reading Eligibility's vocabulary independently.
- SWRL support is intentionally partial. This ADR records that limit as a design decision, not a gap to be discovered later: unsupported semantics on any backend return `undetermined` with a diagnostic code, never a silent denial.
- Parity between the native/SPARQL backend and any other backend claiming to support the same condition is a release gate (ADR-A28), not a best-effort check.

## Addendum (2026-09-18): implemented, narrowed to interval containment

The shared IR is `tools/mork_compilers/eligibility_ir.py`; SPARQL, SHACL, and SWRL backends consume it in `tools/mork_compilers/{sparql,shacl,swrl}_backend.py`. Two narrowings from this ADR's original decision, both deliberate:

- **No native evaluator.** "Native evaluator and SPARQL first" is reduced to SPARQL alone — see ADR-A23's addendum for why. SPARQL is the reference backend for three-valued output instead.
- **Diagnostic codes are not implemented.** This ADR's consequence that "unsupported semantics... return undetermined with a diagnostic code" holds for the *outcome* (the SPARQL and SHACL backends both distinguish missing evidence from a failed containment check) but no `exe:Diagnostic`/diagnostic-code vocabulary exists yet — `ontology/mork/spec/Executable.ttl` deliberately omits it as unused vocabulary rather than declaring it ahead of any consumer. `Undetermined` is a bare decision value, not yet paired with a machine-readable reason code.

See `ontology/mork/docs/eligibility-executable-compiler.md` for the full scope record and verification plan. Not executed.
