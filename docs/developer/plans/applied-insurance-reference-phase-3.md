<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: Applied Insurance Reference — Phase 3, Scheme Profiles and MORK Bridge

**Unit ID:** `applied-insurance-reference-phase-3`
**Epic:** [applied-insurance-reference](applied-insurance-reference.md)
**Status:** Rolling-wave outline. AIR-3.1 to AIR-3.3 need only A-100 and Phase 1, and are detailed
at the Phase 0 gate. AIR-3.4 and AIR-3.5 need the cause scheme and are detailed at AIR-2.4.
**Sketch:** [mork-bridge.md](../sketches/mork-bridge.md)

## Scope

Let a consumer bind a flat or simply taxonomic peril list and get correct, tier-gated answers,
and let reviewed MORK crosswalks lift such a list towards the reference. The profile
vocabulary lives in the cross-domain module `applied/scheme-profile/` (epic D10).

## Slices

| Slice | Content | Sketch | Modules |
|---|---|---|---|
| AIR-3.1 | scheme profile vocabulary: tier (F, H, R, N), capabilities, coverage shares, `InsufficientSchemeStructure`, crosswalk artefact. No insurance terms, as the module is cross-domain | §3.3, §8 | `applied/scheme-profile/` |
| AIR-3.2 | profile derivation as a `fnd:DerivedArtefact` from a bound scheme and its crosswalks | §3.1, §3.3 | `tools/`, location fixed in A-100 |
| AIR-3.3 | tier-gated evaluation: each check declares its required capability, and returns Undetermined with the reason when the profile lacks it | §3.2 | Eligibility tooling, applied |
| AIR-3.4 | lift: MORK mapping graphs from a flat list code to cause concept plus characteristic values, with review and provenance, promoted to a crosswalk | §4.1, §7 | `ontology/mork` examples, crosswalk artefact |
| AIR-3.5 | lower and list-to-list via the reference | §4.2, §4.3 | as 3.4 |

AIR-3.1 to AIR-3.3 use non-insurance test schemes, since the module is cross-domain. Order and
lanes: [lanes and merge order](applied-insurance-reference-lanes.md).

Tests at L1 and L2: the same condition over a tier F, H, R and N scheme (milestone M2),
crosswalk invalidation when either edition changes, and a negative case where an inexact mapping
must not be treated as exact.

## Documentation deltas

`docs/architecture/ontology-architecture.md` (MORK section: crosswalk promotion from the Mapping
role), the profile module's README, and `solution-design-specification.md` if 3.3 changes the
evaluation contract.

## Exit gate

M2 demonstrated. MB-Q2 answered.
