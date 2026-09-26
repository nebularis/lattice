<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Applied Insurance Reference — Lanes and Merge Order

**Epic:** [applied-insurance-reference](applied-insurance-reference.md)
**Purpose:** who builds which slice, on which branch, what each waits for, and the order in which
branches merge to `main`. Slice content stays in the phase plans. This file holds only the
coordination.

## 1. Lanes

A lane is a role, not a person. One participant may hold several lanes, or pick up another lane
when theirs is done (lane L finishes early, for example).

| Lane | Owns | Slices |
|---|---|---|
| G | governance and merging. Held by the human or an integrator agent | AIR-0.1, every merge, every gate |
| L | layout and shared contracts | AIR-1.1, AIR-1.2 |
| P1 | peril vocabulary: spec, characteristics, natural and technical causes | AIR-2.1, AIR-2.2, AIR-2.3, AIR-2.6 |
| P2 | peril vocabulary: human, political, cyber, financial and life causes, editions, collections | AIR-2.4, AIR-2.7, AIR-2.5 |
| B | scheme profiles and MORK bridge | AIR-3.1 to AIR-3.5 |
| E1 | exposure core, units and profiles, then submission | AIR-4.1, AIR-4.2, AIR-4.3, AIR-4.6, AIR-6.1 |
| E2 | exposure history and liability | AIR-4.4, AIR-4.5 |
| U | substrate track, one branch per item | S1 to S7 |

Phase 5 and AIR-6.2 onwards are deferred (epic D2) and have no lane.

## 2. Merge order

A branch is created from `main` once everything in "Branch after" has merged and the named ADR
is Accepted. It is then developed alongside every other open branch. It merges, after rebasing
onto `main`, when every slice with a lower sequence number has merged. G may swap two adjacent
entries only when neither appears in the other's "Branch after" column and they share no region
of §4.

| Seq | Slice | Lane | Branch after | Milestone |
|---|---|---|---|---|
| 1 | AIR-0.1 ADRs A-98, A-99, A-100, A-102 | G | — | |
| 2 | AIR-1.1 drop legacy module, layout | L | 1, A-98 | |
| 3 | AIR-1.2 `classification/`, `insurance/common/` | L | 2, A-102 | |
| 4 | AIR-2.1 `prl:` spec, shapes, file regions | P1 | 1, A-99 | |
| 5 | AIR-3.1 scheme profile vocabulary | B | 1, A-100 | |
| 6 | AIR-2.2 characteristic and companion schemes | P1 | 3, 4 | |
| 7 | AIR-4.1 exposure core, file regions | E1 | 3 | |
| 8 | AIR-3.2 profile derivation | B | 5 | |
| 9 | AIR-2.3 causes N, T, E | P1 | 6 | |
| 10 | AIR-2.4 causes H, P, C, F, L, cross-group links | P2 | 6 | |
| 11 | AIR-4.2 zones, pools, attributes, assessments | E1 | 4, 7 | |
| 12 | AIR-4.4 loss history, loss event, requirements, cover, metrics | E2 | 6, 7 | |
| 13 | AIR-3.3 tier-gated evaluation | B | 8 | |
| 14 | AIR-2.6 intensity measures and thresholds | P1 | 9 | |
| 15 | AIR-2.7 pools scheme, example edition, precedence | P2 | 9, 10 | |
| 16 | AIR-4.3 dependencies, peril metrics, exposure units | E1 | 9, 11 | |
| 17 | AIR-4.5 liability exposure | E2 | 12 | |
| 18 | AIR-2.5 collections, open-perils example | P2 | 10 | M1 |
| 19 | AIR-3.4 lift from a flat list | B | 10, 13 | |
| 20 | AIR-4.6 London and US profiles, examples | E1 | 15, 16, 17 | M3 |
| 21 | AIR-3.5 lower, list to list | B | 19 | M2 |
| 22 | AIR-6.1 submission | E1 | 20 | |
| 23+ | S6, S1, S7, S2, S3, S5, S4, in this order | U | 1, the item's own ADR | |

Substrate items merge last because each bump of a substrate layer triggers the import-pinning
cascade over every applied module already merged. S6 is guidance only and may merge at any point.
S3 rebases onto S2, since both change Eligibility.

## 3. Critical path

1 → 2 → 3 → 6 → 10 → 18 → 19 → 21. The exposure lanes (7 → 11 → 16 → 20 → 22) run alongside and
are the next longest. Starting B at sequence 5, instead of after Phase 2, removes the whole of
Phase 2 from Phase 3's first three slices.

## 4. Rules for shared files

| File | Rule |
|---|---|
| `ontology/catalog-v001.xml` and the stub catalogs | never merged by hand. Regenerate with `mise run build:ontology-catalog` after each rebase |
| `owl:versionIRI` literals and `.version` files | `check:ontology-versioning` compares with the base ref, so two branches bumping one document collide. The later branch takes `main`'s version after rebasing, bumps again under ADR-A86, and runs the import-pinning cascade for merged importers |
| `insurance/peril/vocab/peril-vocab.ttl` | AIR-2.1 creates it with one delimited region per characteristic scheme, one per cause family and a final cross-group links region. AIR-2.2 writes the characteristic regions, AIR-2.3 the N, T and E regions, AIR-2.4 the H, P, C, F and L regions and every link between the two groups. Intensity links (AIR-2.6) go in `peril-intensity.ttl`, not in the family regions |
| `insurance/exposure/spec/exposure.ttl` and its shapes | AIR-4.1 creates one region per slice of Phase 4. Each slice writes only its region |
| `ontology/applied/README.md`, `ontology-architecture.md` §3 | one row per module, added by the slice that creates the module. Conflicts keep both rows |
| `docs/developer/INDEX.md` | each slice edits only its own row |
| phase status records | one per phase (units rule). Lanes sharing a phase (P1 and P2, E1 and E2) each update only their own slice rows. B creates the Phase 3 record at sequence 5 |
| `docs/developer/validation/LOG.md` | the human's only |

## 5. Branches

`air/<slice>-<slug>`, for example `air/2.3-causes-n-t-e`. One branch per slice, deleted after
merge. Each branch's Validation Pack runs its single command on the rebased branch before G
merges it.
