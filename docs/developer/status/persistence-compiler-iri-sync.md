<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Persistence Compiler / IRI-Patterns Sync — Status

**Unit ID:** `persistence-compiler-iri-sync`
**Status:** 🚧 Slice 1 implemented, awaiting human test run and sign-off. Slices 2–6 not started, Slice 3 blocked on a human decision
**Last updated:** 2026-09-23
**Plan:** [persistence-compiler-iri-sync.md](../plans/persistence-compiler-iri-sync.md)
**Sketch (gap analysis):** [persistence-compiler-iri-sync.md](../sketches/persistence-compiler-iri-sync.md)

---

## Current state

Scoped on 2026-09-23 in response to commit `c276afb`, which added three new profile dimensions, extended six existing ones, and added eight new SHACL shapes to `ontology/persistence`, none of it consumed by `tools/persistence`. This was anticipated, not a surprise: [rdf-sparql-patterns-remediation.md](rdf-sparql-patterns-remediation.md)'s own "Deferred item 1" named this exact gap the day it was created.

Slice 1 was implemented the same day, in Default Mode: code and tests were written and the underlying logic was verified by direct script execution (compiling real example fixtures through the resolver/validator/operations pipeline and parsing the rendered SPARQL), but the committed pytest suite itself has not been run by the agent — per this repository's Default Mode, that is the human's step. See [Commands to run](#commands-to-run) below.

## Blockers

| Blocker | Detail | Resolution owner |
|---|---|---|
| Slice 3 resolution-model decision | Does `dal:IdentityProfile` need a `resourceRole` axis on `Target`, or a different mechanism? See [plan](../plans/persistence-compiler-iri-sync.md#human-decision-required-before-slice-3) | Human |

Nothing blocks starting Slices 1, 2, 4, or 5.

## Slice status

| Slice | Scope | Status |
|---|---|---|
| 1 | Dataset-level epoch guard (G1 — correctness) | 🚧 Implemented, awaiting human test run and sign-off — see [VP](../validation/persistence-compiler-iri-sync-slice-1.md) |
| 2 | Ordering/receipt/concurrency/aggregate-boundary extras + meta-topology sharding (G5, G6) | Not started |
| 3 | Identity minting profile resolution (G2) | Blocked on human decision |
| 4 | Privacy/erasure profile + cross-profile compatibility (G3 partial, G4) | Not started |
| 5 | Uniqueness `onViolation` branching, `mergeRelation`, `ClaimScheme` rotation (G7) | Not started |
| 6 | Documentation close-out | Not started, waits on 1–5 |

## Slice 1 delivery detail

**Code**: `model.py` (new `epochGuardScope` dimension, `RowLevelGuardOnly` baseline default), `resolver.py` (`_DIMENSION_SPEC` entry, `epochAuthority` carried as an extra), `validator.py` (two new WARNING-severity diagnostics mirroring `RowLevelGuardOnlyWarningShape`/`StoreLocalEpochWarningShape`, firing on the baseline default as well as explicit configuration), `operations.py` (`datasetGraph`/`datasetNode` fixed-constant bindings, template selection branches on the resolved value for the three named write shapes).

**New templates**: `cas-replace-named-graph-dataset-guard.mustache`, `tombstone-delete-named-graph-dataset-guard.mustache`, `cas-replace-composite-property-dataset-guard.mustache` — each verified to render and parse as valid SPARQL Update via direct script execution before being committed.

**New example fixtures**: `epoch-dataset-level-guard.ttl` (positive), `warning-epoch-unsafe-restore.ttl` (both discouraged values together). `tools/persistence`'s example count is now 16, `ontology/persistence/README.md`'s worked-example listing is not yet updated to match — flagged for Slice 6.

**Design point resolved, documented, not hidden in code alone**: the dataset-level guard's graph and subject IRI (`urn:g:dataset`) are a fixed constant, matching how `urn:g:txn`/`urn:g:txlog/` already work in this compiler, because `dal:EpochProfile` does not declare a property naming them. Recorded in `tools/persistence/README.md`'s "Known limitations," not silently invented as new ontology vocabulary — extending the ratified vocabulary was judged out of scope for a compiler-only slice.

**Deliberately not touched**: `unconditional-write`, `cas-replace-value-guard`, `append-event` (no dataset-guard variant — see VP's "Deliberate non-coverage"); `dal:epochCoordinatorBinding`/`erasureRegisterBinding`/`erasureReplayOnRestore` (deferred to Slice 4, per the plan).

## Severity note

Slice 1 addresses a live correctness gap, not a coverage gap: the compiler's existing CAS/tombstone templates generate the epoch-guard shape the vocabulary now explicitly documents as unsafe (`dal:RowLevelGuardOnly`), unconditionally, for every deployment, with no way to configure the safe alternative (`dal:DatasetLevelGuard`). Recommend prioritising Slice 1 ahead of the others regardless of overall sequencing.

## Test count tracker

| Point in time | `tools/persistence` test count |
|---|---|
| Before this unit (Slice 2 of `rdf-sparql-patterns-phase`) | 239 |
| After Slice 1 | ~254 (10 new explicit test functions + 5 additional parametrised instances from 2 new example fixtures joining existing generic suites) — **not yet confirmed by an actual run**, see Commands to run |
| After Slice 2 | TBD |
| After Slice 3 | TBD |
| After Slice 4 | TBD |
| After Slice 5 | TBD |

## Commands to run

From the repository root:

```bash
mise run check:persistence
```

Expected: all existing tests still pass (non-weakening rule — Slice 1 added tests, it did not modify or remove any), plus the new tests named in [the Slice 1 Validation Pack](../validation/persistence-compiler-iri-sync-slice-1.md). A failure most likely means either an assertion mismatch in the newly written test code (not yet run by the agent) or a namespace/property-name typo against `persistence.ttl` — the same failure mode this project's own history names repeatedly.

## Next steps

1. Human runs `mise run check:persistence` and reports the result.
2. Human resolves the Slice 3 blocker (can happen in parallel with Slices 2/4/5 starting).
3. On a clean Slice 1 run, proceed to Slice 2, 4, or 5 (independent of each other and of Slice 3).
4. Update this file after every slice lands, per the Documentation Lifecycle rule that this status record is the sole authoritative live state for this unit.
