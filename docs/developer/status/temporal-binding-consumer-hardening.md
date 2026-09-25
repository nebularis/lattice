<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Vocabulary Temporal-Binding Consumer Hardening - Status

**Unit ID:** `temporal-binding-consumer-hardening`
**Status:** Planned. No implementation started.
**Last updated:** 2026-09-25
**Trigger:** Closure cross-reference of `vocabulary-temporal-binding` against
[docs/architecture/rdf-sparql-patterns-guide.md](../../architecture/rdf-sparql-patterns-guide.md)
**Plan:** [temporal-binding-consumer-hardening.md](../plans/temporal-binding-consumer-hardening.md)
**Predecessor:** [vocabulary-temporal-binding](vocabulary-temporal-binding.md) (closed)

## Current position

This unit exists to carry forward four items found during the closure review
of `vocabulary-temporal-binding`, none of which blocked that unit's closure.
Only planning has happened so far — this status record and the plan it
accompanies. No code or documentation change against any of the four findings
has been made yet.

## Findings tracked

| # | Finding | Deliverable type | Slice |
|---|---|---|---|
| 1 | `produced_at` doubles as an undeclared semantic input to Surface's artefact/semantic hash for scoped-binding contracts | Resolution plan (options recorded, decision pending) | 3 |
| 2 | Surface's manifest records the resolved scheme but not the resolution context/trace that produced it | Resolution plan (options recorded, decision pending) | 4 |
| 3 | `vvp:resolvedAt`'s name reads as transaction time under the guide's convention, though it is used as a valid-time axis | Documentation improvement (scoped, not yet applied) | 1 |
| 4 | `tools/vocabulary` has no architecture/no-wall-clock test, unlike `tools/persistence` | Test implementation (scoped, not yet applied) | 2 |
| 5 | "Scope" is overloaded across the guide, Surface, and Vocabulary | Accepted, no action | — |

## Blockers

- Slices 3 and 4 (findings 1 and 2) cannot start until the human chooses
  between the design options recorded in the plan for Finding 1, since
  Finding 2's resolution depends on what "resolution instant" means once
  Finding 1 is settled.
- Slices 1 and 2 (findings 3 and 4) have no blockers and can start
  independently once this unit is scheduled.

## Next steps

1. Human decision on Finding 1's Option A/B/C (plan's "Finding 1" section).
2. Implement Slice 1 (Finding 3 documentation) and Slice 2 (Finding 4 test)
   independently of that decision.
3. Implement Slices 3 and 4 once the Finding 1 decision is made, in that
   order (4 depends on 3).
