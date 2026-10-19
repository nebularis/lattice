<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Surface Revision Lifecycle — State Machine and Version Transitions

**Purpose:** Operational procedures for Surface package versioning, state transitions, and lifecycle events  
**Status:** Phase 7 implementation; depth-1 scope  
**Last updated:** 2026-09-22

---

## Overview

Every Surface execution package has a lifecycle state and a version record. This document defines:

1. **State machine** — Valid transitions between package states
2. **Version semantics** — How versions are assigned and incremented
3. **Reconciliation** — How to handle state misalignment (e.g., stale package in production)
4. **Canonicalisation cutover** — How to migrate between canonicalisation contracts

---

## State Machine

### States

```
       Draft
         ↓
    Validation-Ready (with lock for governance review)
         ↓
     Approved (signed off for production use)
         ↓
    Archived (superseded by newer version)
```

### State Definitions

| State | Meaning | Governance | Use | Promotion path |
|-------|---------|-----------|-----|---|
| **Draft** | Being authored or regenerated; not yet validated | None required | Internal development only | Promotion by: manual validation step |
| **Validation-Ready** | Regeneration complete; awaiting governance review | Review requested | CI/staging environments | Promotion by: maintainer sign-off |
| **Approved** | Governance approved; ready for production | Board signed-off or equivalent | Production consumption | Promotion by: release pipeline |
| **Archived** | Superseded by a newer version | Automatic on new promotion | Historical reference only | Demotion only (no promotion) |

### State Transitions

```
Draft → Validation-Ready
  - Regeneration complete
  - All release gates pass
  - No manual action required (automatic on gate success)

Validation-Ready → Approved
  - Maintainer reviews governance state
  - No outstanding exceptions
  - Maintainer signs off

Approved → Archived
  - Newer version promoted to Approved
  - Automatic (old version archived on new release)

Archived → (terminal state)
  - Remain queryable for provenance tracing
  - May not be promoted back to active use
```

### Invalid Transitions

These transitions are **forbidden**:

- `Draft → Approved` (must validate first)
- `Validation-Ready → Archived` (must be Approved first)
- `Archived → Approved` (no revival; create new version instead)
- Direct demotion without reason audit

---

## Version Scheme

### Format: MAJOR.MINOR.PATCH-METADATA

Example: `0.2.1-sha256.a7c9d2e.srf-canon/2`

### Components

| Part | Meaning | When incremented | Example |
|------|---------|---|---|
| **MAJOR** | Incompatible interface change; requires client rewrite | Rarely; architecture decision required | `1.0.0` (from `0.x.x`) |
| **MINOR** | New features; backward compatible | When adding new index forms, promotion types, or policy fields | `0.2.0` (added Projection subsystem) |
| **PATCH** | Bug fixes; no new features | When fixing compiler bugs or defects without spec change | `0.2.1` |
| **METADATA** | Content identifier + canonicalisation version | Every regeneration | `sha256.a7c9d2e.srf-canon/2` |

### Version Increment Rules

**MAJOR (rare):**
- Layer dependency order changes (ADR-A01 change)
- Derivation contract reshaped (Foundation migration complete)
- Compiler output format changes fundamentally

**MINOR (common during active development):**
- New law added to Surface layer
- New index form supported
- Profile policy fields expanded
- Promotion fidelity rules changed

**PATCH (common):**
- Compiler bug fix
- Defect fixture closure
- Output normalization improvement (internal only)

**METADATA (every regeneration):**
- Content hash of the contract and current output
- Canonicalisation version (`srf-canon/1`, `srf-canon/2`, etc.)
- Example: `sha256.a7c9d2e.srf-canon/2`

### Version Independence

Each Surface package tracks its own version independently. The ecosystem has **no global version number**.

However, all packages **must** use the same canonicalisation version in production to ensure hash portability.

---

## Lifecycle Events

### Event 1: Regeneration (State: Draft → Validation-Ready)

**Trigger:** Source, mapping, or profile change detected

**Procedure:**
1. Receive change notification (manual or automatic)
2. Recompute read-set digests (see [surface-invalidation-runbook.md](surface-invalidation-runbook.md))
3. Regenerate Surface packages
4. Increment PATCH version (or MINOR if spec change)
5. Update METADATA: `sha256.<new-hash>.srf-canon/<current-version>`
6. Run all release gates
7. On success: Automatically mark as `Validation-Ready`
8. Create governance review request with:
   - Changelog (what changed and why)
   - Test results
   - Parity metrics
   - Outstanding items (if any)

**Automatic on success; manual on failure:**
```bash
# Success path
python -m surface lower --contracts ontology/surface/examples/my-contract.ttl
# Regeneration + gate verification → Auto-promotion to Validation-Ready

# Failure path
# Review logs, fix issues, retry manually
python -m surface lower --contracts ontology/surface/examples/my-contract.ttl --force-draft
# Stays in Draft; requires manual repair
```

**State recorded:**
```turtle
ex:SurfacePackage_MyConcern_v0.2.1_a7c9d2e
  rdf:type srf:GeneratedSurface ;
  srf:packageState <ValidationReady> ;
  srf:packageVersion "0.2.1-sha256.a7c9d2e.srf-canon/2" ;
  srf:lastRegeneratedAt "2026-09-22T15:30:00Z"^^xsd:dateTime ;
  srf:regeneratedReason "Coverage-type scheme rebound to 2026Q4 edition" ;
  srf:reviewRequestedAt "2026-09-22T15:31:00Z"^^xsd:dateTime .
```

---

### Event 2: Governance Review (State: Validation-Ready → Approved)

**Trigger:** Maintainer reviews and approves the package

**Procedure:**
1. Review release gate report (tests, parity, provenance)
2. Review changelog
3. Consult with domain owner if changes are significant
4. Sign off in governance system (example: form in MORK UI)
5. Mark state as `Approved`
6. Record approval timestamp and approver identity

**Gate review checklist:**
- [ ] All 9 release gates passed (see surface-invalidation-runbook.md)
- [ ] Parity ratio ≥ 99%
- [ ] No regressions in determinism checks
- [ ] Read-set entries are fresh
- [ ] Changelog is clear and complete
- [ ] No outstanding "BLOCKED" items (deferred items are OK)
- [ ] Integration with downstream consumers verified

**State recorded:**
```turtle
ex:SurfacePackage_MyConcern_v0.2.1_a7c9d2e
  rdf:type srf:GeneratedSurface ;
  srf:packageState <Approved> ;
  srf:packageVersion "0.2.1-sha256.a7c9d2e.srf-canon/2" ;
  srf:reviewRequestedAt "2026-09-22T15:31:00Z"^^xsd:dateTime ;
  srf:reviewApprovedAt "2026-09-22T16:15:00Z"^^xsd:dateTime ;
  srf:reviewApprovedBy <person/maintainer-1> ;
  srf:reviewNotes "Approved for production; no outstanding issues" .
```

---

### Event 3: Promotion to Production (State: Approved → Active)

**Trigger:** Release pipeline deploys the package

**Procedure:**
1. Verify package state is `Approved`
2. Check canonicalisation version matches all other active packages (no mixing)
3. Perform atomic replacement:
   ```bash
   # Blue-green or staged rollout
   cp -r ontology/surface/execution/my-contract/v0.2.1-a7c9d2e \
         ontology/surface/execution/my-contract/current
   git add ontology/surface/execution/my-contract/current
   git commit -m "Release: my-contract v0.2.1-a7c9d2e to production"
   ```
4. Record deployment timestamp

**State recorded:**
```turtle
ex:SurfacePackage_MyConcern_v0.2.1_a7c9d2e
  rdf:type srf:GeneratedSurface ;
  srf:packageState <Active> ;
  srf:packageVersion "0.2.1-sha256.a7c9d2e.srf-canon/2" ;
  srf:deployedToProductionAt "2026-09-22T17:00:00Z"^^xsd:dateTime ;
  srf:canonicalisationVersion "srf-canon/2" ;
  srf:productionSupersedes <v0.2.0-sha256.c4e1f3a.srf-canon/2> .
```

---

### Event 4: Supersession (State: Active → Archived)

**Trigger:** A newer version is promoted to Active

**Procedure:**
1. Automatically triggered when new version enters Active state
2. Old version state changes to `Archived`
3. Maintain linkage via `srf:productionSupersedes` for provenance tracing

**Do NOT delete archived packages.** Keep them queryable for:
- Auditing: "which package was in production on date X?"
- Provenance: "this result came from package Y, what was its read-set?"
- Rollback: "if we need to revert, what was the previous version?"

**State recorded:**
```turtle
ex:SurfacePackage_MyConcern_v0.2.0_c4e1f3a
  rdf:type srf:GeneratedSurface ;
  srf:packageState <Archived> ;
  srf:packageVersion "0.2.0-sha256.c4e1f3a.srf-canon/2" ;
  srf:deployedToProductionAt "2026-09-10T08:00:00Z"^^xsd:dateTime ;
  srf:archivedAt "2026-09-22T17:00:00Z"^^xsd:dateTime ;
  srf:supersededBy <v0.2.1-sha256.a7c9d2e.srf-canon/2> .

ex:SurfacePackage_MyConcern_v0.2.1_a7c9d2e
  rdf:type srf:GeneratedSurface ;
  srf:packageState <Active> ;
  srf:productionSupersedes <v0.2.0-sha256.c4e1f3a.srf-canon/2> .
```

---

## Canonicalisation Cutover Lifecycle

### Background

A canonicalisation cutover (e.g., `srf-canon/1` → `srf-canon/2`) is a rare, high-impact event that invalidates all recorded hashes across the entire package estate.

See [surface-invalidation-runbook.md § Scenario 4](surface-invalidation-runbook.md#scenario-4-canonicalisation-change) for the technical procedure.

### Lifecycle during cutover

```
Old estate (srf-canon/1):
  all packages @ Active or Archived states
  all hashes based on srf-canon/1 algorithm

  ↓↓↓ Cutover decision & authorization ↓↓↓

Transition period:
  new packages regenerated with srf-canon/2
  both versions running (carefully isolated)
  comparison tests running to verify equivalence

  ↓↓↓ Verification complete ↓↓↓

Staged rollout:
  domain-1: v0.2.0-sha256.c4e1f3a.srf-canon/1 → Archived
            v0.2.1-sha256.a7c9d2e.srf-canon/2 → Active
  
  [wait 24 hours, monitoring]
  
  domain-2: (same)
  domain-3: (same)

  ↓↓↓ All domains transitioned ↓↓↓

New estate (srf-canon/2):
  all packages @ Active or Archived
  all hashes based on srf-canon/2 algorithm
  backward-compatibility monitoring complete
```

### Version scheme during cutover

**Before cutover:**
```
v0.2.0-sha256.c4e1f3a.srf-canon/1
```

**After cutover (same MAJOR.MINOR.PATCH, new canonicalisation):**
```
v0.2.0-sha256.a1b2c3d.srf-canon/2
```

Note: The PATCH version **does not** change because the functionality is unchanged; only the canonicalisation algorithm did. This ensures version consistency across the cutover.

### Communication during cutover

1. **Pre-cutover (2 weeks before):** Announce to all Surface consumers
2. **Cutover day:** Issue change notice with dates and domain order
3. **Per-domain transition:** Confirm to consumers before and after
4. **Post-cutover (1 week after):** Confirm cutover complete; resume normal operations

### Rollback procedure

If cutover verification fails:

```
New (srf-canon/2) packages fail comparison tests
→ Rollback: Revert to old (srf-canon/1) packages
→ Investigate failure (compiler bug? canonicalisation mismatch?)
→ Delay cutover by N weeks
→ Fix root cause and retry
```

Record the incident in the operational log with:
- Date and duration of rollback
- Root cause
- Fix deployed
- Next cutover date

---

## Reconciliation: Handling State Misalignment

### Scenario: Stale package in production (corruption or deployment error)

**Symptoms:**
- Package marked `Active` but contains old hashes
- Read-set freshness check fails
- Parity checks report mismatches

**Diagnosis:**
```bash
python tools/surface/invalidation.py --check-production-state \
  ontology/surface/execution/my-contract/current

# Output:
# ❌ MISMATCH: Package metadata says v0.2.1-a7c9d2e
#    but filesystem contains v0.2.0-c4e1f3a
# ❌ Hashes are stale (created 2026-09-10, now 2026-09-22)
```

**Recovery:**
1. Take package offline (do not use for queries)
2. Regenerate from source contract
3. Re-run release gates
4. Promote as normal (Draft → Validation-Ready → Approved → Active)

```bash
python -m surface lower --contracts ontology/surface/examples/my-contract.ttl --regenerate-all
```

### Scenario: Canonicalisation version mismatch (mixing old and new)

**Symptoms:**
- Some packages use `srf-canon/1`, others use `srf-canon/2`
- Query results inconsistent across domains
- Hash comparisons fail

**Prevention (preferred):**
- **Never mix canonicalisation versions in production**
- Staged cutover ensures clean transition
- Atomic replacement prevents mid-transition reads

**Recovery (if mixing occurred):**
1. Identify which packages use which version
2. Revert to previous cutover point (all `srf-canon/1` or all `srf-canon/2`)
3. Regenerate missing packages to match estate
4. Re-run full conformance suite
5. Re-attempt cutover with stricter controls

---

## Operational Dashboard (Example)

A real deployment would track this state in a dashboard:

```
Surface Package Lifecycle Status
═══════════════════════════════════════════════════════════════

Package                 Version              State          Updated
─────────────────────────────────────────────────────────────────
coverage-index          0.2.1-a7c9d2e        Active         2 hours ago
peril-dimension         0.1.5-c4e1f3a        Active         1 week ago
scope-closure           0.3.0-b2d8e9f        Validation-Rdy 30 mins ago
sic-category            0.2.0-d9e1a3b        Archived       1 month ago

Canonicalisation Version: srf-canon/2
Last estate-wide cutover: 2026-08-15
Next planned review: 2026-10-15

Release Gates Summary:
  ✅ All Surface tests: 61/61
  ✅ All MORK tests: 15/15
  ✅ All parity checks: 99.5%
  ⚠️  SWRL verification: Pending (Phase 8 item 7)
```

---

## See Also

- [Surface Invalidation Runbook](surface-invalidation-runbook.md) — Technical procedures
- [Phase 7 Status](../status/surface-mork-unified-projection.md#phase-7--provenance-and-invalidation-hardening) — Implementation details
- [Outstanding Items](../status/surface-outstanding-items.md#32-adr-a01-convention-conflict--closed) — Known limitations
- `tools/surface/invalidation.py` — API reference

---

**Last updated:** 2026-09-22  
**Related ADR:** [ADR-A12 (Identity and Derivation Model)](../../architecture/decisions/ADR-A12-identity-and-derivation-model.md), [ADR-A27 (Invalidation and Minimal-Scope Regeneration Policy)](../../architecture/decisions/ADR-A27-invalidation-and-minimal-scope-regeneration-policy.md)
