<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Persistence Compiler / IRI-Patterns Sync — Status

**Unit ID:** `persistence-compiler-iri-sync`
**Status:** ✅ Slices 1–3 complete, 570/570 tests passing (confirmed by an actual run). ⚠️ Slice 4 implemented (code, fixtures and tests written) but **not yet executed**: this sandbox has no working Python/mise and no PyPI access (see Blockers). Slices 5–6 not started.
**Last updated:** 2026-09-23 (Slice 4)
**Plan:** [persistence-compiler-iri-sync.md](../plans/persistence-compiler-iri-sync.md)
**Sketch (gap analysis):** [persistence-compiler-iri-sync.md](../sketches/persistence-compiler-iri-sync.md)

---

## Is this unit complete?

**No.** Three of six slices are done and verified by an actual test run; a fourth is implemented but unverified in this environment. Of the eight gaps in the [gap analysis](../sketches/persistence-compiler-iri-sync.md), four are closed and verified, two more are implemented pending a test run, and one (documentation) is kept current slice by slice with a final pass in Slice 6. The one live correctness gap (G1) is closed and verified. What remains before this unit can move past Slice 4 is a human running the test suite, per the Blockers section below, then Slice 5.

| Gap | Summary | Disposition | Where |
|---|---|---|---|
| G1 | Epoch guard generated the discouraged row-level shape unconditionally | ✅ Closed | Slice 1, then revised by [`iri-patterns-post-3866b21-remediation`](iri-patterns-post-3866b21-remediation.md) (row epoch rebased, not guarded) |
| G2 | Identity minting profile unresolved | ✅ Closed | Slice 3: role-qualified resolution, emitted to the compiled profile, six checks. Minting stays with the caller (decision 2) |
| G3 | Epoch/restore configuration surface | ⚠️ Implemented, unverified | Slice 4: `dal:epochAuthority` promoted to its own resolved dimension; `dal:epochCoordinatorBinding`, `dal:erasureRegisterBinding`, `dal:erasureReplayOnRestore` wired as its extras. Code/tests written, not yet run (see Blockers) |
| G4 | Privacy/erasure profile and cross-profile checks | ⚠️ Implemented, unverified | Slice 4: `dal:privacyClass`/`dal:erasureStrategy`/`dal:erasurePrecedence`/`dal:perSubjectScoped` each resolved as their own dimension; two checks (`PersonalDataRequiresErasure`, `PersonalDataReceiptConflict`) mirroring the two named SHACL shapes. Code/tests written, not yet run (see Blockers) |
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
| **Slice 4's test run** | This sandbox has no system Python, no `mise` on `PATH`, and no PyPI/`files.pythonhosted.org` access (the corporate proxy 307-redirects every package download to an MMC block-notice page — a deliberate network policy, not a transient fault, and not something to route around). `uv python install --system-certs` can fetch a Python interpreter from GitHub releases, but installing `rdflib`/`pytest`/`pyshacl`/`chevron` from PyPI to actually run the suite fails the same way regardless of installer (`uv pip`, plain `pip`) or cache state. Slice 4's code, fixtures and tests were authored and checked for syntax/import errors only (editor-level `get_errors`, no errors found); the actual `mise run check:persistence` run is unconfirmed. | Human — run `mise run check:persistence` in an environment with working PyPI access and report the result |

Nothing blocks starting Slice 5's implementation work, but its own test run will hit the identical environment blocker.

## Slice status

| Slice | Scope | Status |
|---|---|---|
| 1 | Dataset-level epoch guard (G1 — correctness) | ✅ Complete, 290/290 passing — see [VP](../validation/persistence-compiler-iri-sync-slice-1.md) |
| 2 | Ordering/receipt/concurrency/aggregate-boundary extension properties + meta-topology sharding (G5, G6) | ✅ Complete, 526/526 passing — see [VP](../validation/persistence-compiler-iri-sync-slice-2.md) |
| 3 | Identity minting profile resolution (G2) | ✅ Complete, 570/570 passing — see [VP](../validation/persistence-compiler-iri-sync-slice-3.md) |
| 4 | Privacy/erasure profile + cross-profile compatibility (G3 partial, G4) | ⚠️ Implemented. Suite green on 2026-09-24 (669 passed, run from the `identity-minting` M3 session), awaiting human review of the slice |
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

## Slice 4 delivery detail

Implemented 2026-09-23, autonomous mode (granted for this slice explicitly). No design decision was needed: every dimension this slice wires already exists, ratified, in `ontology/persistence/spec/persistence.ttl`, matching the plan's own framing ("compiler catch-up, not a new design").

**Code**: `model.py` (five new dimensions — `epochAuthority`, `privacyClass`, `erasureStrategy`, `erasurePrecedence`, `perSubjectScoped` — appended to `DIMENSIONS`; `perSubjectScoped` added to `LITERAL_DIMENSIONS`; no baseline defaults, matching Slice 2 decision 2's precedent that an undeclared privacy stance is meaningfully absent, not `PublicData` by default), `resolver.py` (`_DIMENSION_SPEC`: `epochAuthority` promoted out of `epochGuardScope`'s extras into its own entry, carrying the three remaining restore-surface properties — `epochCoordinatorBinding`, `erasureRegisterBinding`, `erasureReplayOnRestore` — as its own extras; four new one-property-per-dimension entries for the privacy/receipt properties), `validator.py` (`_check_slice_4`: two checks, both raised as `CrossAxisViolation` because neither mirrored shape declares `sh:severity sh:Warning`; the `StoreLocalEpoch` warning in `check_cross_axis` and the `PositionEventUnsafeEpoch` join in `check_identity` both repointed from `epoch_guard.extra.get("epochAuthority")` to the new top-level `epochAuthority` dimension). `compiler.py` and `operations.py` needed no changes: the former emits every `DIMENSIONS` entry generically, and Slice 4 generates no SPARQL, matching Slice 3's "resolve, check, emit" precedent for a profile class that is adopter-facing configuration, not a template input.

**Fixtures**: `invalid-personaldata-no-erasure.ttl` (mirrors `PersonalDataRequiresErasureShape`), `invalid-personaldata-receipt-conflict.ttl` (mirrors `PersonalDataReceiptCompatibilityShape`, `dal:PrivacyProfile` and `dal:ReceiptProfile` declared on separate individuals sharing one scope), `privacy-receipt-compatible.ttl` (positive: `dal:PatchLog` with `dal:perSubjectScoped true`). All three registered in `test_compiler_integration.py`'s `POSITIVE_FIXTURES`/`NEGATIVE_FIXTURES`/`SHACL_NEGATIVE_FIXTURES` lists as appropriate.

**Tests**: `test_slice_4_privacy.py` (24 test cases counting parametrisation: per-property resolution including the lower-priority-node case, no-default absence, both checks positive and negative including the cross-node join, the two new negative fixtures asserting the exact `CrossAxisViolation.kind`, the positive fixture, literal emission, and Worked example 4's privacy profile resolving and being emitted cleanly). `test_resolver.py`'s two existing `TestEpochGuardScope` tests that asserted `rd.extra["epochAuthority"]` were rewritten, not weakened, to assert the new dimension instead — the documented contract change this slice makes deliberately (epochAuthority is no longer an extra of any dimension).

**Docs**: `tools/persistence/README.md` gains "Privacy and erasure are resolved and checked" (mirroring the identity section's structure) and a "Known limitations" bullet for the three still-unchecked restore-surface extras; its test list and "A `Target` is a class..." section ordering updated accordingly. `ontology/persistence/README.md` §9's worked-example narrative updated from "resolved by the compiler from Slice 4" (future tense) to what Slice 4 actually resolves and checks, and its fixture-list paragraph extended with the three new files.

**Not executed**: per the Blockers section above, this sandbox cannot install `rdflib`/`pytest`/`pyshacl`/`chevron` from PyPI (network policy block, not a code problem), so `mise run check:persistence` has not been run against these changes. Every new and modified Python file was checked for syntax/import errors via the editor's static diagnostics only, with none found. A human must run the suite and report the result before this slice's status can move from "implemented" to "complete".

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
| After Slice 4 | **Not run.** Code adds 24 new dedicated test cases (`test_slice_4_privacy.py`) plus additional parametrised cases from three new fixture files across `test_compiler_integration.py`'s existing suites (end-to-end, negative-compile, SHACL conformance and non-conformance, turtle-parse). Expected total is therefore comfortably above 594, but this is arithmetic, not a confirmed run — see Blockers |
| After Slice 4 and `identity-minting` M3 | **669 passing, 0 failing** (run 2026-09-24 on Python 3.14.7, in the `identity-minting` session). Includes the 24 cases of `test_slice_4_privacy.py` and 4 parametrised cases for `identity-minting-coverage.ttl` |
| After Slice 5 | TBD |

## Commands to run

```bash
mise run check:persistence
```

Result as of 2026-09-23 (after Slice 3, the last point this was actually run): `570 passed`. **Slice 4's changes have not been run against this command in this environment** (see Blockers). Expected: all previously-passing tests still pass, plus the new Slice 4 cases, all green.

## Next steps

1. Minting recipes, conformance vectors and `dal:claimsConstraint` moved to the separate unit [`identity-minting`](../sketches/identity-minting.md) (sketch, 2026-09-23); Slice 3's interim "at least one uniqueness constraint" check is replaced there. Slice 4 also takes the G3 remainder listed above and exercises Worked example 4's privacy profile.
2. **Human runs `mise run check:persistence`** and reports the result, so Slice 4 can move from "implemented" to "complete" (or so any failure can be diagnosed from the pasted output, per this repository's Default Mode).
3. Proceed to Slice 5 once Slice 4 is confirmed (or in parallel, since the plan marks them independent — but its own test run will hit the identical sandbox blocker until run somewhere with PyPI access).
4. **Registry-token events need an unused digest scheme** (found in `identity-minting` M3). The Slice 3 check requires `dal:digestScheme` on every `dal:DerivedHashIdentity` profile, including a position-derived event profile whose namespace is a `dal:RegistryTokenDerivation` token, where the digest is never used. `identity-minting-coverage.ttl` carries one with a comment. Relax the check for that case in Slice 5 or 6.
5. Update this file after every slice lands, per the Documentation Lifecycle rule that this status record is the sole authoritative live state for this unit.
