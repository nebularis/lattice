<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Persistence Compiler / IRI-Patterns Gap Analysis

**Unit ID:** `persistence-compiler-iri-sync`
**Promotes to:** [persistence-compiler-iri-sync.md](../plans/persistence-compiler-iri-sync.md)
**Status record:** [persistence-compiler-iri-sync.md](../status/persistence-compiler-iri-sync.md)
**Triggering commit:** `c276afb` "[iri-patterns] remediate docs and update persistence ontology vocabulary" (2026-09-23)
**Related:** [rdf-sparql-patterns-remediation.md status](../status/rdf-sparql-patterns-remediation.md) (Deferred item 1 names this exact gap), ADR-A82, [iri-identity-patterns.md](../../architecture/iri-identity-patterns.md)

## Method

Every finding below was verified against actual source, not inferred from commit messages or prose:

- `git show c276afb` for the exact ontology/spec diff.
- `grep`/direct reads of `tools/persistence/src/persistence/*.py` and every `*.mustache` template, to confirm each new vocabulary term's presence or absence in the compiler.
- Direct reads of `docs/architecture/rdf-sparql-patterns-guide.md` §19.1 and §24.4 to check whether a given gap is "spec exists, compiler hasn't caught up" versus "spec itself is still abstract."

## Executive summary

Commit `c276afb` added **three new profile dimensions** (`dal:IdentityProfile`, `dal:EpochProfile`, `dal:PrivacyProfile`), **extended six existing profile classes** with new properties, and added **eight new SHACL compatibility/warning shapes** to `ontology/persistence`. None of this is consumed by `tools/persistence`. This was not an oversight: the remediation status file that shipped in the same session names it explicitly as "Deferred item 1: Compiler wiring... not yet consumed by the `tools/persistence` compiler. They are documentation- and SHACL-validation-only until a compiler-wiring slice lands." This document is that slice's scoping.

One finding is more serious than "missing feature": the compiler's existing CAS/tombstone templates generate an epoch guard shape that the new vocabulary now explicitly documents as unsafe and discouraged, with no way to configure the safe alternative. See G1.

## What is confirmed *not* a gap (checked, to keep this analysis honest)

- `operations.py`'s SHA-256 usage (`_shard_for()`) computes a shard-routing number, not an identity-bearing digest. The new `dal:DigestScheme`'s width/encoding/full-verification requirements govern identity-minting digests only. Collisions in shard routing are correct and expected; this is not the same concern and needed no change.
- The guide's dataset-level epoch guard (§19.1) is **fully specified**, down to the exact SPARQL shape (`GRAPH <urn:g:dataset> { <urn:ds:prod> pat:epoch "3"^^xsd:long }` as an added `WHERE`-clause condition). This is a compiler-catch-up gap (G1), not a specification gap.

## Gap catalogue

### G1 — Epoch guard: compiler generates the discouraged pattern unconditionally (severity: correctness)

Every CAS-style template that guards on epoch (`cas-replace-named-graph.mustache`, `tombstone-delete-named-graph.mustache`, `cas-replace-composite-property.mustache`) guards **only** the per-aggregate meta-graph row:

```sparql
GRAPH {{{metaGraphPrefix}}} {
    $root pat:epoch $epoch ; pat:seq $expectedSeq ; pat:head ?prevRev
}
```

This is exactly `dal:RowLevelGuardOnly` — the value the new `RowLevelGuardOnlyWarningShape` flags: "A stale client can still match an unrestored row after a dataset-level bump that never reaches the row." There is no template variant implementing `dal:DatasetLevelGuard` (an added `GRAPH <urn:g:dataset> { ... }` condition, per guide §19.1), and no compiler-level concept of `dal:EpochProfile` at all, so there is currently no way to configure the safe option even if an adopter wanted it. This is the compiler silently defaulting to the pattern the spec now warns against, for every deployment, unconditionally.

### G2 — Identity minting profile (§12) entirely unresolved (severity: missing dimension, open architecture question)

`dal:IdentityProfile`, `dal:ResourceRole` (8 values), `dal:IdentityStrategy` (7 values), `dal:DigestScheme`, `dal:OccurrenceNamespaceDerivation`, `dal:EventIdentityStrategy`, `dal:uniquenessWitnessRequired` — zero references anywhere in `tools/persistence/src`.

This is not a simple "add a row to `_DIMENSION_SPEC`" fix like G5/G6 below. `dal:resourceRole` has `sh:minCount 1 ; sh:maxCount 1` on `IdentityProfileShape`, meaning **one target class needs different identity strategies for different resource roles simultaneously** — an aggregate root's own identity (`dal:AggregateRootRole`) is minted differently from its event occurrences' identity (`dal:EventOccurrenceRole`), for the same class. The resolver's current model resolves one value per `(Target, dimension)` pair; `Target` is `(class, deployment)` with no resource-role axis. Whether `resourceRole` becomes a third resolution key, a new `ScopeInfo` kind, or something else is a genuine design decision, not an implementation detail — flagged for the plan's Slice 3, not resolved here.

### G3 — Epoch/restore-safety configuration surface unresolved, distinct from G1 (severity: missing dimension)

Separate from G1's template-shape problem: there is no way to declare `dal:epochAuthority` (which of four allocation strategies a deployment uses), `dal:epochCoordinatorBinding`, `dal:erasureRegisterBinding`, or `dal:erasureReplayOnRestore` at all. Even once G1's template gains a `DatasetLevelGuard` variant, nothing resolves *which* `EpochProfile` applies to a given target, or surfaces `StoreLocalEpochWarningShape`/`RowLevelGuardOnlyWarningShape` at the Python level (only SHACL catches these today, and only if someone runs `pyshacl` directly against a hand-authored configuration, since the compiler never emits or checks one).

### G4 — Privacy/erasure profile (§14) entirely unresolved, including cross-profile compatibility (severity: missing dimension)

`dal:PrivacyProfile`, `dal:PrivacyClass`, `dal:ErasureStrategy`, `dal:ErasurePrecedence`, `dal:perSubjectScoped` — zero references. Two new SHACL shapes join a `PrivacyProfile` to a `ReceiptProfile` sharing the same `dal:appliesTo` scope (`PersonalDataReceiptCompatibilityShape`) or check a `PrivacyProfile` in isolation (`PersonalDataRequiresErasureShape`). Neither has a Python-level equivalent. This breaks the defense-in-depth pattern the persistence compiler established for itself in its first build (every cross-axis SHACL rule paired with a named Python exception type, per `validator.py`'s existing `check_cross_axis`) — right now these two invariants exist in exactly one place, not two.

### G5 — Extension properties on existing profile classes not threaded through (severity: missing coverage, low architectural risk)

These attach to profile classes the resolver already knows how to resolve (`_DIMENSION_SPEC` already has an entry for each), so this is additive, not a new resolution kind:

- `dal:OrderingProfile`: `dal:globalReadStrategy` (4 values), `dal:lagWindowMillis`, `dal:contiguityCheckMode` (2 values, one discouraged).
- `dal:ReceiptProfile`: `dal:retentionMode` (2 values, one incompatible with as-of replay), `dal:asOfFloorSource`.
- `dal:ConcurrencyProfile`: `dal:etagForm` (2 values, one invalid for CAS), `dal:etagRepresentation` (2 values), `dal:deadlockPolicy` (3 values).
- `dal:AggregateBoundaryProfile`: `dal:firstWrite` (2 values). This one has a real behavioural consequence already described in the guide (§19.1's comment on `dal:PreCreatedRow`): `select_operations()` currently has no concept of `dal:firstWrite` at all, so it cannot know that a `dal:PreCreatedRow` target must never be offered `create-if-absent-named-graph.mustache` (no row is ever "absent" for such a target; only the CAS shape is legitimate).

Five new SHACL shapes correspond to these: `WeakEtagCasWarningShape`, `NoGlobalReadWarningShape`, `AdvisoryContiguityWarningShape`, `AsOfFloorRetentionCompatibilityShape`. None has a Python-level equivalent (same defense-in-depth gap as G4, smaller blast radius).

### G6 — Meta-topology sharding extension not threaded through (severity: missing coverage, low risk)

`dal:txnShards`, `dal:logShards`, `dal:keyShards`, `dal:registryGraph` extend `dal:MetaTopologyProfile`, which the resolver already resolves (`metaTopology` dimension exists, currently carries `metaShards`/`priorMetaShards`/`epochBumpAcknowledged` as extras per `_DIMENSION_SPEC`). Adding these four is a pure extras-tuple addition — no new resolution kind, no new template behaviour required until a slice actually needs to shard the txn-claim, log-bucket, or key-shard graphs differently from the meta graph.

### G7 — Uniqueness `onViolation`/`mergeRelation`/`ClaimScheme` gap, compounding a pre-existing issue (severity: correctness + missing coverage)

Two distinct problems, one old and one new:

1. **Pre-existing, not introduced by this commit**: `resolve_uniqueness()` reads `onViolation` but `operations.py`'s `select_operations()` never branches on its value — every uniqueness constraint gets exactly one `key-claim-write`/`key-claim-retire` pair regardless of whether it declares `dal:Reject`, `dal:Merge`, or `dal:Quarantine`. Only `Reject`-shaped behaviour is actually generated today.
2. **New, sharpens problem 1**: `dal:mergeRelation` is now required whenever `dal:onViolation` is `dal:Merge` (`MergeRelationRequiredShape`), but `resolve_uniqueness()` never reads it, and no template exists that would use it even if it were read. There is now a required, validated configuration value with no consumer.
3. **New, unimplemented from scratch**: `dal:ClaimScheme`/`dal:schemeVersion`/`dal:SchemeState` (Accepting/Dual/Retiring/Retired) model HMAC-secret rotation for keyed claims. `dal:Dual` state requires "every claim acquisition guards and inserts both this and the next scheme version's claim IRI in one operation" — `key-claim-write.mustache` has no scheme-version parameter at all and no dual-guard structure.

### G8 — `tools/persistence/README.md` is now stale (severity: documentation)

The "Known limitations" section predates this commit entirely and describes none of G1–G7. An adopter reading the README today would not learn that identity minting, epoch/restore safety, or privacy/erasure are unresolved by this compiler at all.

## Non-goals of the eventual fix (explicitly out of scope for the plan this analysis produces)

- Re-litigating ADR-A82 or `iri-identity-patterns.md`'s design. This analysis takes both as settled input.
- Building the Request Query Mapping library or Query Execution component (both remain deferred pending A75, unaffected by this gap).
- Regenerating the guide's worked examples to a single digit width (explicitly deferred in the remediation status file's own "Deliberate scope reduction" section, a separate follow-up).
