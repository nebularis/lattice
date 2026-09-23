<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# RDF & SPARQL Patterns Guide — Remediation Status

**Unit ID:** `rdf-sparql-patterns-remediation`
**State:** Plan authored, not started. No edits have been made to `rdf-sparql-patterns-guide.md` or any other file.
**Plan:** [rdf-sparql-patterns-remediation.md](../plans/rdf-sparql-patterns-remediation.md)
**Sketch:** None (remediation of fully specified, reviewed defects; no design exploration slice was needed to produce the plan)
**Governing review:** [ADR-A68-A82-iri-patterns-review.md](../review/ADR-A68-A82-iri-patterns-review.md) (2026-09-23)
**Primary target document:** [rdf-sparql-patterns-guide.md](../../architecture/rdf-sparql-patterns-guide.md)

## Current state

The governing review identified 13 blocking (production-unsafe) defects and 3 cross-document inconsistencies in `rdf-sparql-patterns-guide.md`, all now mapped to exact locations, quoted anchors, and concrete fixes (or fix options with consequences, where more than one valid fix exists) in the plan above. No fix has been applied. This status record exists to track the plan's disposition and, once implementation starts, its slice-by-slice progress.

The review's own §2 (cross-document inconsistencies) is truncated mid-sentence at finding C3. The plan records what can be independently established about C3 and does not guess the rest on the review's behalf — see the plan's Part B (C3) and Part F item 7.

## Findings disposition

| ID | Severity | Disposition |
|---|---|---|
| B1 | Blocking | Planned. Part (a) mechanical, part (b) is an open decision (Part F item 1) |
| B2 | Blocking | Planned. Single valid fix identified; no open decision |
| B3 | Blocking | Planned. Open decision (Part F item 2) |
| B4 | Blocking | Planned. Single valid fix identified; no open decision |
| B5 | Blocking | Planned. Single valid fix identified; no open decision |
| B6 | Blocking | Planned. Single valid fix identified; no open decision |
| B7 | Blocking | Planned. Single valid fix identified; no open decision |
| B8 | Blocking | Planned. Open decision (Part F item 3) |
| B9 | Blocking | Planned. Open decision (Part F item 4) |
| B10 | Blocking | Planned. Single valid fix identified; no open decision |
| B11 | Blocking | Planned. Open decision (Part F item 5) |
| B12 | Blocking | Planned. Single valid fix identified; no open decision |
| B13 | Blocking | Planned. Single valid fix identified; no open decision |
| C1 | Cross-doc | Planned. Mechanical repointing; no open decision |
| C2 | Cross-doc | Planned. Blocked on a factual check (Part F item 6) |
| C3 | Cross-doc | Planned as far as the source review permits. Blocked on the review's own completion (Part F item 7) |

## Pre-execution blockers

| Blocker | Detail | Resolution owner |
|---|---|---|
| Five design decisions open | B1(b) epoch-allocation source, B3 target-IRI unification, B8 timeout-outcome policy, B9 retention/shape trade-off, B11 HLC-pagination safeguard | Human — see plan Part F items 1-3, 4, 5 |
| One factual verification open | C2: whether `fnd:replacedBy` exists in `ontology/foundation/` | Whoever implements the slice, before touching §7.5/§23.3 |
| One incomplete source document | C3: the governing review's own text ends mid-sentence at this finding | Review's author — plan Part F item 7 |

Nothing else blocks starting the mechanical (Decision required: NO) fixes listed in the plan's ledger, but Part D's sequencing notes mean several mechanical and decision-gated fixes share the same source blocks (notably §19.1, §10.1, and §19.4) and should not be edited twice — implementation should wait for all decisions touching a given block before editing it once.

## Next steps

1. Human resolves the five open design decisions in Part F items 1-5.
2. Implementer confirms the `fnd:replacedBy` question in `ontology/foundation/` (Part F item 6).
3. Review's author completes finding C3, or the human explicitly accepts this plan's independent cross-check as sufficient to proceed on a stated width choice without it.
4. Once resolved, decompose the plan into one or more implementation slices per copilot-instructions' mandatory slice shape (code/doc change, Validation Pack, traceability update, doc delta), following the sequencing order in the plan's Part D.
5. Each slice's Validation Pack must include at least one adversarial case per Blocking finding it closes, per the human validation gate's mutation-check step, given several of these defects (B2, B8 in particular) are exactly the kind of "test passes while the system is corrupt" bug that discipline exists to catch.
