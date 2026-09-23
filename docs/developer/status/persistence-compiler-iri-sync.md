<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Persistence Compiler / IRI-Patterns Sync — Status

**Unit ID:** `persistence-compiler-iri-sync`
**Status:** ⏳ Not started — scoped, one slice blocked on a human decision
**Last updated:** 2026-09-23
**Plan:** [persistence-compiler-iri-sync.md](../plans/persistence-compiler-iri-sync.md)
**Sketch (gap analysis):** [persistence-compiler-iri-sync.md](../sketches/persistence-compiler-iri-sync.md)

---

## Current state

Scoped on 2026-09-23 in response to commit `c276afb`, which added three new profile dimensions, extended six existing ones, and added eight new SHACL shapes to `ontology/persistence`, none of it consumed by `tools/persistence`. This was anticipated, not a surprise: [rdf-sparql-patterns-remediation.md](rdf-sparql-patterns-remediation.md)'s own "Deferred item 1" named this exact gap the day it was created. No code has changed yet. `tools/persistence`'s 239 existing tests are unaffected and still pass against the pre-`c276afb` vocabulary subset they exercise.

## Blockers

| Blocker | Detail | Resolution owner |
|---|---|---|
| Slice 3 resolution-model decision | Does `dal:IdentityProfile` need a `resourceRole` axis on `Target`, or a different mechanism? See [plan](../plans/persistence-compiler-iri-sync.md#human-decision-required-before-slice-3) | Human |

Nothing blocks starting Slices 1, 2, 4, or 5.

## Slice status

| Slice | Scope | Status |
|---|---|---|
| 1 | Dataset-level epoch guard (G1 — correctness) | Not started |
| 2 | Ordering/receipt/concurrency/aggregate-boundary extras + meta-topology sharding (G5, G6) | Not started |
| 3 | Identity minting profile resolution (G2) | Blocked on human decision |
| 4 | Privacy/erasure profile + cross-profile compatibility (G3 partial, G4) | Not started |
| 5 | Uniqueness `onViolation` branching, `mergeRelation`, `ClaimScheme` rotation (G7) | Not started |
| 6 | Documentation close-out | Not started, waits on 1–5 |

## Severity note

Slice 1 addresses a live correctness gap, not a coverage gap: the compiler's existing CAS/tombstone templates generate the epoch-guard shape the vocabulary now explicitly documents as unsafe (`dal:RowLevelGuardOnly`), unconditionally, for every deployment, with no way to configure the safe alternative (`dal:DatasetLevelGuard`). Recommend prioritising Slice 1 ahead of the others regardless of overall sequencing.

## Test count tracker

| Point in time | `tools/persistence` test count |
|---|---|
| Before this unit (Slice 2 of `rdf-sparql-patterns-phase`) | 239 |
| After Slice 1 | TBD |
| After Slice 2 | TBD |
| After Slice 3 | TBD |
| After Slice 4 | TBD |
| After Slice 5 | TBD |

## Next steps

1. Human resolves the Slice 3 blocker (can happen in parallel with Slices 1/2/4/5 starting).
2. Start Slice 1 first, given its severity.
3. Update this file after every slice lands, per the Documentation Lifecycle rule that this status record is the sole authoritative live state for this unit.
