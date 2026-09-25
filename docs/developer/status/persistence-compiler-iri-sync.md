<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Persistence Compiler / IRI-Patterns Sync — Status

**Unit ID:** `persistence-compiler-iri-sync`
**Status:** ✅ Complete. All six slices done, 774/774 tests passing (human-validated 2026-09-25).
**Last updated:** 2026-09-25 (Slice 6 documentation close-out, unit complete)
**Plan:** [persistence-compiler-iri-sync.md](../plans/persistence-compiler-iri-sync.md)
**Sketch (gap analysis):** [persistence-compiler-iri-sync.md](../sketches/persistence-compiler-iri-sync.md)

---

## Is this unit complete?

**Yes.** All six slices are done. Every gap in the [gap analysis](../sketches/persistence-compiler-iri-sync.md) (G1–G8) is closed and verified, the last (G7, Slice 5) by an actual, human-confirmed test run (774/774 passing). Nothing further is owed by this unit.

### Slice 5 decisions (human, 2026-09-25)

1. **Decision 1 (onViolation semantics), Option A chosen.** The synchronous guarded write (`key-claim-write`) stays unchanged for every `dal:onViolation` policy — a race is always prevented at write time. `dal:onViolation` instead selects which **reconciler** operation Slice 5 generates, matching guide §7.5 (P7) rather than §6 (P1/P2, which only ever describes the Reject shape): `dal:Reject` (the baseline default when undeclared) generates an alert-only duplicate-scan audit; `dal:Merge` generates an operation that records `dal:mergeRelation` from every non-canonical owner to a deterministic canonical one (lexicographically lowest IRI, documented, not hidden); `dal:Quarantine` generates an operation that copies every duplicate into a dedicated `urn:g:key-quarantine` graph for human review. None of the three deletes anything or resolves the duplicate automatically — "the reconciler is never the only strategy, and it is never absent" (guide §7.5).
2. **Decision 2 (registry-token digest relaxation), accepted as correctly framed.** `dal:DigestSchemeRequiredShape` and the mirrored Python check in `check_identity` are narrowed to exempt exactly the combination `dal:eventIdentityStrategy dal:PositionDerivedEvent` + `dal:occurrenceNamespaceDerivation dal:RegistryTokenDerivation`: the namespace is a registry-allocated token, not digest-derived, so the digest is provably unused (`recipes.py` already never reads a digest for this role). `dal:HashedTargetDerivation` is deliberately **not** exempted: its own ontology comment ("an injective, fixed-width digest of the target's own IRI") documents a real, if not yet wired, use of the digest scheme. `ontology/persistence` bumped PATCH (0.2.0 → 0.2.1): a shape narrowed to match already-documented intent, the same class of change as `eligibility/spec`'s 0.3.0 → 0.3.1 precedent (`applied-ontology-readiness` AOR-2).
3. **Decision 3 (execution mode).** Fully autonomous, granted for this slice. Per explicit instruction, no install or test-run was attempted in this session (the sandbox's PyPI block, recorded in the Blockers table below, is unchanged) — verification is left for the end of the slice, for the human to run.

| Gap | Summary | Disposition | Where |
|---|---|---|---|
| G1 | Epoch guard generated the discouraged row-level shape unconditionally | ✅ Closed | Slice 1, then revised by [`iri-patterns-post-3866b21-remediation`](iri-patterns-post-3866b21-remediation.md) (row epoch rebased, not guarded) |
| G2 | Identity minting profile unresolved | ✅ Closed | Slice 3: role-qualified resolution, emitted to the compiled profile, six checks. Minting stays with the caller (decision 2) |
| G3 | Epoch/restore configuration surface | ✅ Closed | Slice 4: `dal:epochAuthority` promoted to its own resolved dimension; `dal:epochCoordinatorBinding`, `dal:erasureRegisterBinding`, `dal:erasureReplayOnRestore` wired as its extras. Human-validated 2026-09-25 |
| G4 | Privacy/erasure profile and cross-profile checks | ✅ Closed | Slice 4: `dal:privacyClass`/`dal:erasureStrategy`/`dal:erasurePrecedence`/`dal:perSubjectScoped` each resolved as their own dimension; two checks (`PersonalDataRequiresErasure`, `PersonalDataReceiptConflict`) mirroring the two named SHACL shapes. Human-validated 2026-09-25 |
| G5 | Extension properties on existing profile classes | ✅ Closed | Slice 2 |
| G6 | Meta-topology sharding extension | ✅ Closed as resolution and warning | Slice 2. The counts are recorded, not applied to the generated SPARQL (plan Slice 2 decision 3) |
| G7 | Uniqueness `onViolation`, `mergeRelation`, `ClaimScheme` rotation | ✅ Closed | Slice 5 (2026-09-25): reconciler operations per policy (decision 1, Option A), `dal:mergeRelation` read and checked, `key-claim-write-dual.mustache` selected when a constraint's active `dal:ClaimScheme`s are both `dal:Dual`. Human-validated 2026-09-25, 774 passed |
| G8 | `tools/persistence/README.md` stale | ✅ Closed | Updated in Slices 1, 2 and 4, by the post-3866b21 remediation, and finalised in Slice 6 (2026-09-25): "Known limitations" reflects exactly what Slices 1–5 shipped, `rdf-sparql-patterns-remediation.md`'s Deferred item 1 marked closed, `rdf-sparql-patterns-status.md` records the final 774-test count, and `docs/developer/INDEX.md` had its final traceability pass |

## Current state

Scoped on 2026-09-23 in response to commit `c276afb`, which added three new profile dimensions, extended six existing ones, and added eight new SHACL shapes to `ontology/persistence`, none of it consumed by `tools/persistence`. This was anticipated, not a surprise: [rdf-sparql-patterns-remediation.md](rdf-sparql-patterns-remediation.md)'s own "Deferred item 1" named this exact gap the day it was created.

Slice 1 was implemented the same day, in Default Mode: code and tests were written and the underlying logic was verified by direct script execution, but the committed pytest suite was handed off unrun (per Default Mode). The human ran `mise run check:persistence` and reported one failure: `TestEpochGuardScopeTemplateSelection::test_dataset_level_guard_selects_dataset_guard_templates` — `epoch-dataset-level-guard.ttl` declared only a `dal:EpochProfile`, no concurrency/boundary profile, so the target's `concurrencyProfile` fell back to the platform baseline (`ProvidedConcurrency`) and never entered the CAS branch at all; `select_operations()` generated `unconditional-write`, not `cas-replace`. Not a logic bug in the epoch-guard code — a fixture bug: the file wasn't a complete, self-contained positive example the way every other fixture in this directory is. Fixed by giving the fixture its own full `dal:DataAccessProfile` (matching `baseline-single-class.ttl`'s shape) alongside the `EpochProfile`, both scoped to the same target. Human then granted autonomous mode for this fix; re-ran the suite directly: **290/290 passing.**

**2026-09-23, later:** the post-3866b21 review remediation ([status](iri-patterns-post-3866b21-remediation.md)) changed the Slice 1 dataset-guard templates to rebase the row epoch instead of guarding it, added dataset-guard variants for `create-if-absent`, `append` and a new `bootstrap-version-row`, and replaced the audits. Slice 1's own tests still pass unchanged. Slice 2 then closed the `firstWrite` item.

## Blockers

| Blocker | Detail | Resolution owner |
|---|---|---|
| ~~Slice 3 resolution-model decision~~ | Resolved 2026-09-23: role-qualified dimensions, see [plan](../plans/persistence-compiler-iri-sync.md#slice-3--identity-minting-profile-resolution-g2) | — |
| ~~Slice 4's test run~~ | Resolved 2026-09-25: human ran `mise run check:persistence`, confirmed all tests pass, and checked the adversarial probes. | — |
| ~~Slice 5's test run~~ | Resolved 2026-09-25: human ran `mise run check:persistence`, confirmed **774 passed** after fixing a mustache-comment parsing issue in `key-claim-merge-rewrite.mustache` (found by the run itself, see Slice 5 VP's "Found on the way"). | — |

No open blockers remain.

## Slice status

| Slice | Scope | Status |
|---|---|---|
| 1 | Dataset-level epoch guard (G1 — correctness) | ✅ Complete, 290/290 passing — see [VP](../validation/persistence-compiler-iri-sync-slice-1.md) |
| 2 | Ordering/receipt/concurrency/aggregate-boundary extension properties + meta-topology sharding (G5, G6) | ✅ Complete, 526/526 passing — see [VP](../validation/persistence-compiler-iri-sync-slice-2.md) |
| 3 | Identity minting profile resolution (G2) | ✅ Complete, 570/570 passing — see [VP](../validation/persistence-compiler-iri-sync-slice-3.md) |
| 4 | Privacy/erasure profile + cross-profile compatibility (G3 partial, G4) | ✅ Complete, human-validated 2026-09-25 (669 passed, adversarial probes checked) — see [VP](../validation/persistence-compiler-iri-sync-slice-4.md) |
| 5 | Uniqueness `onViolation` reconciler operations, `mergeRelation`, `ClaimScheme` `dal:Dual` rotation, registry-token digest relaxation (G7) | ✅ Complete, human-validated 2026-09-25 (774 passed) — see [VP](../validation/persistence-compiler-iri-sync-slice-5.md) |
| 6 | Documentation close-out | ✅ Complete, 2026-09-25 | no VP (L0, documentation only — same precedent as `applied-ontology-readiness` AOR-1) |

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

**Confirmed**: the human ran `mise run check:persistence` on 2026-09-25, reported all tests passing, and checked the adversarial probes in the Slice 4 VP. This slice is complete.

## Slice 5 delivery detail

Implemented 2026-09-25, fully autonomous mode (granted for this slice explicitly). Three human decisions preceded implementation, recorded above under "Slice 5 decisions": Option A for `onViolation` semantics, the registry-token digest relaxation, and autonomous mode with no install/test-run attempted this tranche.

**Code**: `resolver.py` (`resolve_uniqueness()` now also reads `dal:mergeRelation`, and computes `dualClaimScheme` — true exactly when a constraint's `dal:claimScheme`s in state `Accepting`/`Dual` number two, mirroring `recipes.py`'s own `claims()` filter rather than a second, divergent rule), `validator.py` (`check_identity`'s digest-scheme check gains the `RegistryTokenDerivation` exemption, checking a declared-anyway scheme for well-formedness rather than skipping validation outright; a new `_check_slice_5` raises `MergeRelationRequired`, mirroring `dal:MergeRelationRequiredShape`, called from `check_cross_axis`), `operations.py` (a new fixed `keyQuarantineGraph` binding (`urn:g:key-quarantine`), `key-claim-write` now selects the `-dual` template variant when `dualClaimScheme`, and `onViolation` — defaulting to `Reject` when undeclared, the same explicit-baseline-default convention as every other dimension — selects one reconciler operation per constraint: `key-claim-duplicate-audit` (Reject), `key-claim-merge-rewrite` (Merge, carrying `mergeRelation` as an `Iri` binding), or `key-claim-quarantine` (Quarantine)).

**New templates**: `key-claim-write-dual.mustache` (guards and inserts both scheme versions' claim IRIs in one operation, guide §6.1), `key-claim-duplicate-audit.mustache` (the guide §7.5 claim-registry duplicate scan, scoped to one constraint), `key-claim-merge-rewrite.mustache` (records `dal:mergeRelation` from every non-canonical owner to the lexicographically lowest — arbitrary but deterministic, documented — owner IRI; idempotent; records the merge edge only, since retiring a claim is an owner's own act per guide §6.2 and a background reconciler has no such authority), `key-claim-quarantine.mustache` (copies every duplicate owner into `urn:g:key-quarantine` with a timestamp, idempotent per owner, deletes nothing).

**Ontology**: `dal:DigestSchemeRequiredShape` and `dal:DigestScheme`'s comment narrowed to exempt `dal:PositionDerivedEvent` + `dal:RegistryTokenDerivation`. `identity-minting-coverage.ttl`'s `ex:ShipmentEvents` fixture had its now-unnecessary `dal:digestScheme`/`ex:ShipmentDigest` removed, with a comment recording why — verified this changes nothing in the already-generated `packages/minting/testdata/Shipment-*` recipe/vectors (no `digest` key was ever emitted for a `PositionDerivedEvent` role; `recipes.py`'s `build()` skips the digest branch entirely once `eventIdentityStrategy` overrides the effective strategy). `ontology/persistence` bumped PATCH, 0.2.0 → 0.2.1; no importers to cascade (leaf ontology, ADR-A78).

**New fixtures**: `uniqueness-merge-policy.ttl`, `uniqueness-quarantine-policy.ttl`, `invalid-merge-policy-no-relation.ttl` (also a SHACL-negative fixture, mirrors `MergeRelationRequiredShape`), `claim-scheme-dual-rotation.ttl` (two `dal:ClaimScheme`s, both `dal:Dual`). Registered in `test_compiler_integration.py`'s fixture lists.

**Tests**: new `test_slice_5_uniqueness.py` (onViolation defaulting, all three reconciler templates selected and rendered, `MergeRelationRequired` positive/negative, `dualClaimScheme` computation and template selection, the registry-token digest exemption's positive case and its `HashedTargetDerivation` boundary negative case). `test_template_alignment.py` extended: `_full_context()` gains `mergeRelation`/`keyQuarantineGraph`, and the `key-claim-*` template list in `test_key_claims_live_in_the_keys_graph` extended to the four new templates.

**Not executed**: per instruction for this tranche, no install or test-run was attempted. Every new and modified file was checked for syntax/import errors via the editor's static diagnostics (`get_errors`), none found. A human must run the suite and report the result, per the Blockers table above.

**Confirmed**: the human ran `mise run check:persistence` on 2026-09-25 and reported **774 passed**, after fixing one issue the run itself surfaced: `key-claim-merge-rewrite.mustache`'s header comment quoted the literal Mustache tag `{{{mergeRelation}}}` as prose inside a `{{! ... }}` comment, which this compiler's renderer (`chevron`) does not treat as inert — the braces inside the comment were parsed as a second, spurious tag. Fixed by rephrasing the comment in words instead of quoting the tag syntax. Recorded as a general gotcha for this compiler's templates in the Slice 5 VP and `docs/developer/INDEX.md`'s Key Findings. This slice is complete.

## Slice 6 delivery detail

Completed 2026-09-25, the same session as Slice 5's validation. Documentation-only (L0), no VP file, matching the `applied-ontology-readiness` AOR-1 precedent for a governance/documentation-only slice.

- **`tools/persistence/README.md` "Known limitations"**: already current as of Slice 5 (each slice updated it as it landed, per the plan's own note that Slice 6 "remains the final pass" only if something drifted). Reviewed line by line against what Slices 1–5 actually shipped; no correction needed.
- **[`rdf-sparql-patterns-remediation.md`](rdf-sparql-patterns-remediation.md)**'s Deferred item 1 ("Compiler wiring") marked closed, citing this unit's Slices 1–5 completion and the 774/774 result.
- **[`rdf-sparql-patterns-status.md`](rdf-sparql-patterns-status.md)** updated: header status line, and a new "2026-09-25, re-sync complete" paragraph recording that the compiler is fully re-synced against the post-`c276afb` vocabulary, with the final 774-test count.
- **`docs/developer/INDEX.md`** final traceability pass: the "change package at a glance" summary, unit 1a's full slice table, the Validation Packs list, the Complete/In Progress lists, the Key Findings (added the Slice 5 mustache-comment gotcha), the Persistence compiler test-coverage row, and the document's own "Last updated" footer.

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
| After Slice 4 and `identity-minting` M3 | **669 passing, 0 failing** (run 2026-09-24 on Python 3.14.7, in the `identity-minting` session). Includes the 24 cases of `test_slice_4_privacy.py` and 4 parametrised cases for `identity-minting-coverage.ttl`. Human-confirmed 2026-09-25 as Slice 4's own result |
| After Slice 5 | **774 passing, 0 failing** (human-confirmed run, 2026-09-25). Adds `test_slice_5_uniqueness.py` plus parametrised cases from four new fixtures across `test_compiler_integration.py`'s existing suites |

## Commands to run

```bash
mise run check:persistence
```

Result as of 2026-09-25 (after Slice 5, the last point this was actually run): `774 passed`.

## Next steps

None. This unit is complete. `identity-minting-shared-core` (deferred sketch) can now revisit its own next steps, which named this unit's Slice 6 as the thing it was waiting on.
