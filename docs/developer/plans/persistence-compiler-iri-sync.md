<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Persistence Compiler / IRI-Patterns Sync — Plan

**Unit ID:** `persistence-compiler-iri-sync`
**Status:** Slices 1 and 2 complete — see [persistence-compiler-iri-sync.md](../status/persistence-compiler-iri-sync.md)
**Sketch (gap analysis):** [persistence-compiler-iri-sync.md](../sketches/persistence-compiler-iri-sync.md)
**Governing ADRs:** ADR-A78 (persistence substrate), ADR-A79 (compiler toolchain), ADR-A82 (framework-neutral identity pattern selection)
**New ADR required for this plan itself:** No. Every dimension this plan wires already exists, ratified, in `ontology/persistence/spec/persistence.ttl`. This is compiler catch-up, not a new design.

## Scope

Bring `tools/persistence` back into sync with the `dal:` vocabulary as it exists after commit `c276afb`, per the gap analysis. Six slices, sequenced by severity and dependency. Each follows copilot-instructions' mandatory slice shape: code, a Validation Pack at `docs/developer/validation/persistence-compiler-iri-sync-<slice>.md`, a traceability update to `docs/developer/INDEX.md`, and doc deltas in the same slice (not deferred).

**Non-weakening rule applies**: no slice may loosen or delete an existing test in `tools/persistence/tests` (471 passing on 2026-09-23, after Slice 1 and the `iri-patterns-post-3866b21-remediation` template alignment). Every slice adds tests. A test may be rewritten only where a documented change of contract makes its assertion obsolete, and the slice's VP names it.

## Slice 1 — Dataset-level epoch guard (G1)

**Why first**: the only finding that is a live correctness problem, not a coverage gap. The compiler generates the pattern the spec now calls unsafe, for every deployment, today.

- Add `dal:EpochProfile` to `_DIMENSION_SPEC` (or an equivalent resolution path — implementer's choice how `epochAuthority` vs `epochGuardScope` split between primary value and extras, per the sketch's G1 note) so a target's epoch configuration resolves the same way the existing six dimensions do.
- Add a `DatasetLevelGuard` template variant (or a Mustache conditional block) to `cas-replace-named-graph.mustache`, `tombstone-delete-named-graph.mustache`, and `cas-replace-composite-property.mustache`, emitting the guide §19.1 shape (`GRAPH <urn:g:dataset> { <urn:ds:prod> pat:epoch $epoch }` as an added `WHERE` condition) when `dal:epochGuardScope` is `dal:DatasetLevelGuard`.
- Preserve the existing row-level-only behaviour as the `dal:RowLevelGuardOnly` path, but only when explicitly configured — never as the unconfigured default. Absence of an `EpochProfile` for a target should be a documented baseline default (per the existing `BASELINE_DEFAULTS` convention), stated explicitly, not silently the discouraged shape by omission.
- Python-level check mirroring `RowLevelGuardOnlyWarningShape`/`StoreLocalEpochWarningShape` in `validator.py`, following the existing `check_cross_axis`/named-exception pattern.
- Tests: a positive fixture generating the dataset-level guard clause; a positive fixture generating row-level-only when explicitly configured; a determinism test (permuted triple order, identical output, per the existing `test_determinism.py` pattern); a rendered-SPARQL parse test proving the added `WHERE` clause is syntactically valid (this repository's own history shows this exact category of bug — invalid SPARQL only caught by actually parsing it — twice already in this compiler's build).

## Slice 2 — Ordering/receipt/concurrency/aggregate-boundary extension properties, and meta-topology sharding (G5, G6)

**Mode:** autonomous (granted 2026-09-23).

### Decisions (agreed 2026-09-23)

1. **Each new property is its own resolved dimension.** The resolver today reads extra properties only from the profile node that wins the dimension's primary value, so a property declared on a separate or lower-priority profile node is dropped silently, and extras never reach the compiled profile. Every Slice 2 property is therefore added as a dimension of its own, resolved by the existing precedence algorithm (priority, reasoning-aware tie break, `ProfileAmbiguityError`) and emitted as a `dal:ResolvedDimension`. Candidates are nodes typed with the property's profile class, or `dal:DataAccessProfile` nodes, that declare the property. Literal-valued dimensions are emitted with a new `dal:resolvedLiteral` datatype property, since `dal:resolvedValue` is an object property.
2. **Baseline defaults**, following Slice 1's precedent that absence of configuration is an explicit, documented value: `firstWrite` → `dal:AbsentRow` (today's behaviour), `etagForm` → `dal:StrongEtag`, `etagRepresentation` → `dal:SingleRepresentation`, `deadlockPolicy` → `dal:EngineDetectAndRetry`, `contiguityCheckMode` → `dal:BlockingContiguityCheck`, `retentionMode` → `dal:PrefixOnlyRetention`. No default for `globalReadStrategy`, `lagWindowMillis`, `asOfFloorSource`, the three shard counts or `registryGraph`.
3. **Shard counts are resolved but not yet honoured.** Every template writes to one txn, keys and log-bucket graph. A declared `dal:txnShards`, `dal:logShards` or `dal:keyShards` greater than 1 raises a `ShardingNotHonoured` warning rather than being ignored silently.

### Dimensions added

| Dimension | Profile class | Property | Kind |
|---|---|---|---|
| `firstWrite` | `dal:AggregateBoundaryProfile` | `dal:firstWrite` | object |
| `etagForm`, `etagRepresentation`, `deadlockPolicy` | `dal:ConcurrencyProfile` | same names | object |
| `globalReadStrategy`, `contiguityCheckMode` | `dal:OrderingProfile` | same names | object |
| `lagWindowMillis` | `dal:OrderingProfile` | `dal:lagWindowMillis` | literal |
| `retentionMode` | `dal:ReceiptProfile` | `dal:retentionMode` | object |
| `asOfFloorSource` | `dal:ReceiptProfile` | `dal:asOfFloorSource` | literal |
| `txnShards`, `logShards`, `keyShards`, `registryGraph` | `dal:MetaTopologyProfile` | same names | literal |

### Behaviour

- **`dal:firstWrite dal:PreCreatedRow`.** `select_operations()` never offers `create-if-absent` for the target. It emits `bootstrap-version-row` (the dataset-guard variant under `dal:DatasetLevelGuard`) instead: the row is created at `seq 0` with no head when the aggregate id is allocated, and every later write is a CAS (guide §14.2). This applies to `dal:NamedGraphBoundary` and `dal:CompositePropertyBoundary`. `tools/persistence/README.md` documents the obligation for a caller that runs the generated SPARQL without LATTICE's query layer.
- **Request-time slots use Mustache.** The `#PAYLOAD#` and `#LOG_GRAPHS#` text markers become the Mustache tags `{{{payloadTriples}}}` and `{{{logGraphs}}}`. `persistence instantiate` renders compile-time slots and passes request-time slots through verbatim, so the instantiated SPARQL carries standard Mustache tags that any language's Mustache library can fill. An instantiated operation contains no other `{{` or `}}` sequence, which a test enforces.
- **`dal:registryGraph`** is emitted as a resolved dimension and, when declared, as an `Iri` parameter binding on every audit operation, so whatever fills `{{{logGraphs}}}` knows which registry to read.

### Checks (Python mirrors, on resolved values)

| Check | Severity | Mirrors |
|---|---|---|
| `dal:etagForm dal:WeakEtag` with `dal:Optimistic` | WARNING | `dal:WeakEtagCasWarningShape` |
| `dal:globalReadStrategy dal:NoGlobalRead` | WARNING | `dal:NoGlobalReadWarningShape` |
| a `dal:datasetTierModel` declared with no `dal:globalReadStrategy` | WARNING | new, decision 2 |
| `dal:contiguityCheckMode dal:AdvisoryContiguityCheck` | WARNING | `dal:AdvisoryContiguityWarningShape` |
| `dal:retentionMode dal:BucketAnyRetention` with a `dal:asOfFloorSource` | ERROR (`CrossAxisViolation`) | `dal:AsOfFloorRetentionCompatibilityShape` |
| `dal:LagWindowRead` without a positive `dal:lagWindowMillis` | ERROR (`CrossAxisViolation`) | new `dal:LagWindowRequiredShape` |
| `dal:deadlockPolicy dal:SortedAcquisition` with `dal:Optimistic` or `dal:AppendOnly` | WARNING | new: sorted acquisition needs multi-request or external-lock strategies (guide §19.6) |
| a shard count greater than 1 | WARNING (`ShardingNotHonoured`) | new, decision 3 |

The SHACL shapes check one profile node at a time, and the Python checks check resolved values across nodes. Where they differ, for example a weak ETag and optimistic concurrency declared on two different nodes, the Python check is authoritative and the SHACL shape is the same-node subset.

### Tests

A positive and negative pair per check. Per-property resolution from a separate profile node and from a lower-priority node. Baseline defaults. Literal dimension emission. `dal:PreCreatedRow` excluding `create-if-absent` and emitting `bootstrap-version-row`. The request-time slot contract. `registryGraph` binding. Determinism over the new dimensions.

## Slice 3 — Identity minting profile resolution (G2)

**Blocked on a human decision**, per the sketch's G2 finding: does `dal:resourceRole` become a third resolution key alongside `Target`, a new `ScopeInfo`/scope-kind concept, or something else? This is an architecture question, not an implementation detail — do not start this slice until that is settled.

Once resolved:

- Wire `dal:IdentityProfile` (`resourceRole`, `identityStrategy`, `namingAuthority`) and its dependent classes (`dal:DigestScheme`, `dal:OccurrenceNamespaceDerivation`, `dal:EventIdentityStrategy`, `dal:uniquenessWitnessRequired`) into resolution, per whatever resolution-key shape the decision settles on.
- Python-level checks mirroring `DigestSchemeRequiredShape` and `UniquenessWitnessRequiredShape`.
- Tests: at minimum, one fixture per `dal:ResourceRole` value showing distinct identity strategies resolve correctly for the same target class at different roles (the scenario that motivates the resolution-key question in the first place).

## Slice 4 — Privacy/erasure profile and cross-profile compatibility (G3 partial, G4)

- Wire `dal:PrivacyProfile` (`privacyClass`, `erasureStrategy`, `erasurePrecedence`) into resolution.
- Wire the remaining `dal:EpochProfile` surface not needed for Slice 1's guard-shape decision: `epochCoordinatorBinding`, `erasureRegisterBinding`, `erasureReplayOnRestore`.
- Python-level checks mirroring `PersonalDataRequiresErasureShape` and `PersonalDataReceiptCompatibilityShape` — the latter is a genuine cross-profile-type join (a `PrivacyProfile` and a `ReceiptProfile` sharing one `dal:appliesTo` scope), which no existing Python check does today; this is new shape of validation for `validator.py`, not just a new rule.
- Tests: the cross-profile join is the interesting case — a fixture with matching scope but incompatible receipt model, and a fixture with matching scope and `dal:CryptoShred`/`dal:perSubjectScoped true` that correctly passes.

## Slice 5 — Uniqueness: `onViolation` branching, `mergeRelation`, `ClaimScheme` rotation (G7)

- Fix the pre-existing gap: `select_operations()` must branch on `onViolation` (`dal:Reject` / `dal:Merge` / `dal:Quarantine`), not generate the same `key-claim-write`/`key-claim-retire` pair unconditionally. This may require new template(s) for `Merge`/`Quarantine` behaviour if none exist — check the guide's Chapter 6 worked examples for the intended shape before authoring one from scratch.
- Read `dal:mergeRelation` in `resolve_uniqueness()`; require it when `onViolation` is `dal:Merge` (Python-level mirror of `MergeRelationRequiredShape`).
- Wire `dal:ClaimScheme`/`dal:schemeVersion`/`dal:SchemeState`; extend `key-claim-write.mustache` to guard-and-insert both the current and next scheme version's claim IRI when `dal:schemeState` is `dal:Dual`.
- Tests: one fixture per `onViolation` value showing distinct generated operations; a `Dual`-state fixture proving both scheme versions are guarded in one operation, not two.

## Slice 6 — Documentation close-out

- Rewrite `tools/persistence/README.md`'s "Known limitations" section to reflect what Slices 1–5 actually shipped (not what this plan proposed — write it after, not before).
- Update [rdf-sparql-patterns-remediation.md status](../status/rdf-sparql-patterns-remediation.md)'s Deferred item 1 to point at this unit's completion.
- Update [rdf-sparql-patterns-status.md](../status/rdf-sparql-patterns-status.md) (the Slice 2 status record, currently reads "✅ Complete" with 239 tests) to note the compiler was re-synced against the post-`c276afb` vocabulary, with the new test count.
- Final `docs/developer/INDEX.md` traceability pass across all five preceding slices.

## Dependencies and sequencing

```
Slice 1 (epoch guard, urgent) ──┐
Slice 2 (extras, low risk)     ─┼─► independent, any order, can run in parallel
Slice 6 (docs close-out)        │   waits on whichever slices actually land
                                 │
Slice 3 (identity, blocked) ────┴─► blocked on human resolution-model decision
Slice 4 (privacy)                   independent of 1/2/3, can start any time
Slice 5 (uniqueness/claim)          independent of 1/2/3/4, can start any time
```

Slice 1 should land first given its severity, but nothing structurally blocks starting Slices 2, 4, or 5 in parallel. Slice 3 is the only slice gated on a decision this plan does not make.

## Human decision required before Slice 3

**Does resolving `dal:IdentityProfile` require extending the `Target` model with a `resourceRole` axis, or is there a better-fitting mechanism?** See the sketch's G2 finding for the concrete scenario that forces the question (one aggregate class needing different identity strategies for its own entity identity versus its event occurrences' identity, simultaneously).

## Validation approach

Per copilot-instructions' human validation gate: each slice's VP names its positive and negative cases, the single `mise run check:persistence` command, and at least one adversarial probe (deliberately break the new check, show it fails, per the pattern already established in `docs/developer/validation/persistence-substrate-and-compiler.md`'s two adversarial probes). No slice is signed off without one.
