<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Writing only what changed, as a persistence mode - Status

**Unit ID:** `persistence-delta-replace`
**Status:** 🟡 DR1 to DR4 built 2026-11-01, the benchmark to be read on a quiet machine
**Last updated:** 2026-11-01
**Plan:** [persistence-delta-replace.md](../plans/persistence-delta-replace.md)
**Sketch:** [persistence-delta-replace.md](../sketches/persistence-delta-replace.md)

## Current position

Sketched and planned on 2026-10-31 at the maintainer's request, after SQ-Q1 asked that a write write only what changed unless its profile chose a whole replace. DR-Q1 to DR-Q7 were answered the same day. The studio already writes its parts' and documents' deltas by hand (TD-136), which DR4 moves onto the generated replace. The linear replace investigation, on its own branch and unanswered, does not block the unit: what still writes a whole state is generated as R0 until LR-Q1 to LR-Q3 are answered.

**Next action:** read `mise run benchmark:studio-api` on a quiet machine against `2e8a02cc`, which closes DR4's done criterion. For the maintainer, ADR-A123's addendum of 2026-11-01 and the decisions in the Validation Packs of [DR1](../validation/DR1.md), [DR2](../validation/DR2.md) and [DR4](../validation/DR4.md).

## Log

- 2026-10-31: sketched, every question answered, planned.
- 2026-11-01: the maintainer asked for every planned slice on `claude/config-authoring-studio`, built autonomously, with the linear replace branch kept apart until later.
- 2026-11-01: DR1 built. The vocabulary, the derived default, two refusals, twelve delta builders, a slot in a DELETE template, the contract with no payload part, whole-state fixtures for every test of the whole replace, and the studio pinned to the whole replace until DR4. `check:persistence` 4,312 passed, `check:persistence-conformance` 5,104 passed, `check:persistence-library` passed. Two Sonnet subagents wrote the vocabulary and the whole-state fixtures.
- 2026-11-01: DR3 built before DR2, since DR1 left the libraries' tests reading the delta replace. A delta replace's digest has no payload part, `digest-replace-delta` is a vector, and both libraries read and digest the delta replace. TDB2 and Fuseki are covered through the studio in DR4.
- 2026-11-01: DR2 built. `replace-whole` beside the delta replace, the bulk load composed by the caller under one transaction id an aggregate, the opt-in state digest with its record and its audit, `compose` and `state_digest` in both libraries, and TSD-68 (Oxigraph refuses a prologue after `;`). Conformance 5,213 passed.
- 2026-11-01: DR4 built with PM2. The writer replaces parts and documents through the generated delta replace (TD-136 closed), the service takes a patch, and the browser sends one where it can. The real-stack browser suite found a patch with one empty side refused, since Jena keeps no empty graph (TSD-69), now fixed. Both browser suites run at a merge into `main` (ADR-A133 decision 11). `check:config-studio` and `test:config-studio-browser` passed. The benchmark ran twice under load from other work, a publish at 117 ms both times, so it is not read yet.
