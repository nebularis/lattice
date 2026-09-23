<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Persistence Compiler / IRI-Patterns Sync — Status

**Unit ID:** `persistence-compiler-iri-sync`
**Status:** ✅ Slices 1–3 complete, 570/570 tests passing. Slices 4–6 not started, nothing blocked
**Last updated:** 2026-09-23 (Slice 3)
**Plan:** [persistence-compiler-iri-sync.md](../plans/persistence-compiler-iri-sync.md)
**Sketch (gap analysis):** [persistence-compiler-iri-sync.md](../sketches/persistence-compiler-iri-sync.md)

---

## Is this unit complete?

**No.** Three of six slices are done. Of the eight gaps in the [gap analysis](../sketches/persistence-compiler-iri-sync.md), four are closed, one is partly closed, two are open, and one (documentation) is kept current slice by slice with a final pass in Slice 6. The one live correctness gap (G1) is closed, and nothing is blocked. What remains is missing coverage in Slices 4 and 5, then the close-out.

| Gap | Summary | Disposition | Where |
|---|---|---|---|
| G1 | Epoch guard generated the discouraged row-level shape unconditionally | ✅ Closed | Slice 1, then revised by [`iri-patterns-post-3866b21-remediation`](iri-patterns-post-3866b21-remediation.md) (row epoch rebased, not guarded) |
| G2 | Identity minting profile unresolved | ✅ Closed | Slice 3: role-qualified resolution, emitted to the compiled profile, six checks. Minting stays with the caller (decision 2) |
| G3 | Epoch/restore configuration surface | ◐ Partly closed | Slice 1 resolves `dal:epochGuardScope` and reads `dal:epochAuthority` with its `StoreLocalEpoch` warning. Open for Slice 4: `dal:epochCoordinatorBinding`, `dal:erasureRegisterBinding`, `dal:erasureReplayOnRestore`, and making `dal:epochAuthority` its own dimension (it is still an extra, so it has the drop-off-the-winning-node problem Slice 2 fixed for the others) |
| G4 | Privacy/erasure profile and cross-profile checks | ⏳ Open | Slice 4 |
| G5 | Extension properties on existing profile classes | ✅ Closed | Slice 2 |
| G6 | Meta-topology sharding extension | ✅ Closed as resolution and warning | Slice 2. The counts are recorded, not applied to the generated SPARQL (plan Slice 2 decision 3) |
| G7 | Uniqueness `onViolation`, `mergeRelation`, `ClaimScheme` rotation | ⏳ Open | Slice 5 |
| G8 | `tools/persistence/README.md` stale | ◐ Kept current | Updated in Slices 1 and 2 and by the post-3866b21 remediation. Final pass in Slice 6 |

## Current state

Scoped on 2026-09-23 in response to commit `c276afb`, which added three new profile dimensions, extended six existing ones, and added eight new SHACL shapes to `ontology/persistence`, none of it consumed by `tools/persistence`. This was anticipated, not a surprise: [rdf-sparql-patterns-remediation.md](rdf-sparql-patterns-remediation.md)'s own "Deferred item 1" named this exact gap the day it was created.

Slice 1 was implemented the same day, in Default Mode: code and tests were written and the underlying logic was verified by direct script execution, but the committed pytest suite was handed off unrun (per Default Mode). The human ran `mise run check:persistence` and reported one failure: `TestEpochGuardScopeTemplateSelection::test_dataset_level_guard_selects_dataset_guard_templates` — `epoch-dataset-level-guard.ttl` declared only a `dal:EpochProfile`, no concurrency/boundary profile, so the target's `concurrencyProfile` fell back to the platform baseline (`ProvidedConcurrency`) and never entered the CAS branch at all; `select_operations()` generated `unconditional-write`, not `cas-replace`. Not a logic bug in the epoch-guard code — a fixture bug: the file wasn't a complete, self-contained positive example the way every other fixture in this directory is. Fixed by giving the fixture its own full `dal:DataAccessProfile` (matching `baseline-single-class.ttl`'s shape) alongside the `EpochProfile`, both scoped to the same target. Human then granted autonomous mode for this fix; re-ran the suite directly: **290/290 passing.**

**2026-09-23, later:** the post-3866b21 review remediation ([status](iri-patterns-post-3866b21-remediation.md)) changed the Slice 1 dataset-guard templates to rebase the row epoch instead of guarding it, added dataset-guard variants for `create-if-absent`, `append` and a new `bootstrap-version-row`, and replaced the audits. Slice 1's own tests still pass unchanged. Slice 2 then closed the `firstWrite` item.

## Blockers

| Blocker | Detail | Resolution owner |
|---|---|---|
| ~~Slice 3 resolution-model decision~~ | Resolved 2026-09-23: role-qualified dimensions, see [plan](../plans/persistence-compiler-iri-sync.md#slice-3--identity-minting-profile-resolution-g2) | — |

Nothing blocks starting Slices 4 or 5.

## Slice status

| Slice | Scope | Status |
|---|---|---|
| 1 | Dataset-level epoch guard (G1 — correctness) | ✅ Complete, 290/290 passing — see [VP](../validation/persistence-compiler-iri-sync-slice-1.md) |
| 2 | Ordering/receipt/concurrency/aggregate-boundary extension properties + meta-topology sharding (G5, G6) | ✅ Complete, 526/526 passing — see [VP](../validation/persistence-compiler-iri-sync-slice-2.md) |
| 3 | Identity minting profile resolution (G2) | ✅ Complete, 570/570 passing — see [VP](../validation/persistence-compiler-iri-sync-slice-3.md) |
| 4 | Privacy/erasure profile + cross-profile compatibility (G3 partial, G4) | Not started |
| 5 | Uniqueness `onViolation` branching, `mergeRelation`, `ClaimScheme` rotation (G7) | Not started |
| 6 | Documentation close-out | Not started, waits on 3–5. Items already done early are listed in the [plan](../plans/persistence-compiler-iri-sync.md#slice-6--documentation-close-out) |

## Slice 1 delivery detail

**Code**: `model.py` (new `epochGuardScope` dimension, `RowLevelGuardOnly` baseline default), `resolver.py` (`_DIMENSION_SPEC` entry, `epochAuthority` carried as an extra), `validator.py` (two new WARNING-severity diagnostics mirroring `RowLevelGuardOnlyWarningShape`/`StoreLocalEpochWarningShape`, firing on the baseline default as well as explicit configuration), `operations.py` (`datasetGraph`/`datasetNode` fixed-constant bindings, template selection branches on the resolved value for the three named write shapes).

**New templates**: `cas-replace-named-graph-dataset-guard.mustache`, `tombstone-delete-named-graph-dataset-guard.mustache`, `cas-replace-composite-property-dataset-guard.mustache` — each verified to render and parse as valid SPARQL Update via direct script execution before being committed.

**New example fixtures**: `epoch-dataset-level-guard.ttl` (positive), `warning-epoch-unsafe-restore.ttl` (both discouraged values together). `ontology/persistence/README.md`'s fixture listing was brought up to date in Slice 2 (19 fixtures after Slice 2).

**Design point resolved, documented, not hidden in code alone**: the dataset-level guard's graph and subject IRI (`urn:g:dataset`) are a fixed constant, matching how `urn:g:txn`/`urn:g:txlog/` already work in this compiler, because `dal:EpochProfile` does not declare a property naming them. Recorded in `tools/persistence/README.md`'s "Known limitations," not silently invented as new ontology vocabulary — extending the ratified vocabulary was judged out of scope for a compiler-only slice.

**Deliberately not touched**: `unconditional-write`, `cas-replace-value-guard`, `append-event` (no dataset-guard variant — see VP's "Deliberate non-coverage"); `dal:epochCoordinatorBinding`/`erasureRegisterBinding`/`erasureReplayOnRestore` (deferred to Slice 4, per the plan).

## Slice 2 delivery detail

Run in autonomous mode, 2026-09-23, after the plan was revised with three agreed decisions (per-property resolution, baseline defaults, warn on unhonoured shard counts).

**Code**: `model.py` (13 new dimensions, `LITERAL_DIMENSIONS`, six baseline defaults), `resolver.py` (one `_DIMENSION_SPEC` entry per property), `compiler.py` (`dal:resolvedLiteral` emission), `validator.py` (`_check_slice_2`: two refusals, six warning kinds), `operations.py` (`dal:firstWrite dal:PreCreatedRow` emits `bootstrap-version-row` instead of `create-if-absent`; `registryGraph` bound on every audit), `render.py` (`REQUEST_TIME_SLOTS`: `payloadTriples` and `logGraphs` pass through instantiate as Mustache tags).

**Vocabulary**: `dal:resolvedLiteral`, `dal:LagWindowRequiredShape`, the Slice 2 shapes widened to `dal:DataAccessProfile` targets, `dal:PreCreatedRow` comment.

**Templates**: `#PAYLOAD#` and `#LOG_GRAPHS#` replaced by `{{{payloadTriples}}}` and `{{{logGraphs}}}`. `bootstrap-version-row` generalised from streams to any version row (`$target`).

**Docs**: `tools/persistence/README.md` gains "Using the generated SPARQL directly" (value kinds, request-time slots, SPARQL variables per operation, the obligations a caller outside LATTICE's query layer carries, first among them running `bootstrap-version-row` at id allocation). `ontology/persistence/README.md` §3 records per-property resolution.

**Found on the way**: the resolver's extras model would have dropped any property declared off the winning node (now the reason for decision 1); a new negative fixture initially failed on an unrelated `orderingGrain` tie, caught and pinned by a dedicated test; `test_determinism.py` depended on the working directory.

## Slice 3 delivery detail

Decisions taken with the human on 2026-09-23: role-qualified dimensions, resolve/check/emit only, four cross-checks, autonomous mode.

**Code**: `resolver.py` (precedence step factored into `_select`, reused by `resolve_identity`, which resolves one `identity:<Role>` dimension per declared role, winning node as a unit), `validator.py` (`check_identity`: five refusals, one warning), `compiler.py` (identity resolved and checked per target, emitted as resolved dimensions).

**Vocabulary**: `dal:DigestSchemeWellFormedShape`, `dal:OccurrenceNamespaceDerivationRequiredShape`.

**Fixtures**: `identity-epoch-privacy-profile.ttl` (Worked example 4, handed over from `rdf-sparql-patterns-remediation`), `invalid-claimed-identity-without-key.ttl`, `invalid-position-event-without-derivation.ttl`.

**Docs**: `tools/persistence/README.md` "Identity is resolved per resource role"; `ontology/persistence/README.md` §3 and §9 (the worked example gained the uniqueness constraint its claimed identity needs, and a second role); `iri-identity-patterns.md` §14.2 records which compilation responsibilities are implemented, and now says "warn", consistent with §10.3, for a position-derived event without a durable epoch.

**Found on the way**: Worked example 4 as written would have been refused by the new claimed-key check; `iri-identity-patterns.md` §14.2 asked the compiler to refuse where §10.3 says warn, and to generate minting functions, which decision 2 defers.

## Severity note

Slice 1 addresses a live correctness gap, not a coverage gap: the compiler's existing CAS/tombstone templates generate the epoch-guard shape the vocabulary now explicitly documents as unsafe (`dal:RowLevelGuardOnly`), unconditionally, for every deployment, with no way to configure the safe alternative (`dal:DatasetLevelGuard`). Recommend prioritising Slice 1 ahead of the others regardless of overall sequencing.

## Test count tracker

| Point in time | `tools/persistence` test count |
|---|---|
| Before this unit (Slice 2 of `rdf-sparql-patterns-phase`) | 239 |
| After Slice 1 | **290 passing, 0 failing** (confirmed by an actual run, 2026-09-23) |
| After `iri-patterns-post-3866b21-remediation` template alignment | **471 passing** (2026-09-23, see [that unit's status](iri-patterns-post-3866b21-remediation.md)) |
| After Slice 2 | **526 passing, 0 failing** (autonomous run, 2026-09-23) |
| After Slice 3 | **570 passing, 0 failing** (autonomous run, 2026-09-23) |
| After Slice 4 | TBD |
| After Slice 5 | TBD |

## Commands to run (already run and passing, kept for reproducibility)

```bash
mise run check:persistence
```

Result as of 2026-09-23 (after Slice 3): `570 passed`.

## Next steps

1. Proceed to Slice 4 or 5 (independent of each other). Slice 4 also takes the G3 remainder listed above and exercises Worked example 4's privacy profile.
3. Update this file after every slice lands, per the Documentation Lifecycle rule that this status record is the sole authoritative live state for this unit.
