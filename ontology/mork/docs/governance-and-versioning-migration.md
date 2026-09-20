<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# MORK governance and versioning: migration guide

Date: 2026-09-18
Status: Accompanies [ADR-A22](../../docs/architecture/decisions/ADR-A22-mork-governance-and-versioning-foundation-alignment.md)

## What changed

`ontology/mork/spec/Mork.ttl`:

1. The ontology now imports Foundation (`https://www.nebularis.org/neuro-semantic/foundation/0.0.7`).
2. `mork:GenerativeMapping` is now `rdfs:subClassOf fnd:Governable, fnd:Version`, in addition to its existing `mork:DataMapping` superclass. This cascades to `ShapeMapping`, `RuleMapping`, `TransformMapping`, and `ProjectionMapping` by ordinary subsumption — nothing about their existing `owl:equivalentClass` definitions changes.
3. A new `mork:CompilationMode` class (individuals `mork:DraftMode`, `mork:ReviewMode`, `mork:ProductionMode`) and a new `mork:compilationMode` property (domain `mork:MappingScheme`) name which of the three a scheme's member mappings compile under. Unset is equivalent to `DraftMode`.

`ontology/mork/shapes/constraints.ttl` (previously empty):

1. `mork:GenerativeMappingGovernanceStateClosedShape` — closes `fnd:hasGovernanceState`'s range to Foundation's four named individuals, for `mork:GenerativeMapping`.
2. `mork:GenerativeMappingProductionGovernanceShape` — a `mork:GenerativeMapping` belonging (via `mork:mappingScheme`) to a scheme in `mork:ProductionMode` must have a governance state beyond `fnd:Draft` (`fnd:Reviewed`, `fnd:Active`, or `fnd:Superseded`) and declare `fnd:hasIdentity`. A superseded, historical mapping is not rejected merely for being superseded — only a mapping left at `Draft` or with no governance state at all fails this. **Conditional**: a mapping in a scheme with no declared mode, or in `DraftMode`/`ReviewMode`, is entirely unaffected.
3. `mork:GenerativeMappingSupersessionEffectiveFromShape` — a mapping that supersedes an earlier one via `fnd:supersededBy` must record `mork:effectiveFrom`, extending the pre-existing GCI Axiom 5.10a (which covers `mork:supersedes`) to the Foundation-aligned direction.

`ontology/foundation/vocab/foundation-vocab.ttl` gained the four `fnd:GovernanceState` individuals (`Draft`, `Reviewed`, `Active`, `Superseded`) that were referenced throughout the repository (Surface's own examples, Vocabulary's and Party's worked examples) but never actually declared — see `docs/architecture/ontology-architecture.md`'s own note on this gap. This was a prerequisite for any of the above to be meaningful, not itself part of ADR-A22's scope, and is called out separately here for that reason.

## Why

MORK already had three ad-hoc mechanisms doing adjacent jobs: `mork:reviewStatus` (a free string, "DRAFT"/"APPROVED"/"DEPRECATED", on the four `*Provenance` classes only), `mork:supersedes` + `mork:mappingVersion` (mapping-to-mapping succession plus a free string version on `MappingScheme`), and `mork:deprecationReason` (a free string on `DataMapping`). None of them are Foundation-aligned, none of them compose with the versioning/governance pattern every other layer in the substrate uses (`fnd:Governable`, `fnd:Version`, `fnd:PersistentIdentity`, `fnd:supersededBy`), and `reviewStatus`'s three string values are not a closed, checkable vocabulary the way `fnd:GovernanceState`'s four named individuals are.

ADR-A22 decided this gets **resolved by addition, not by replacement**: MORK adopts Foundation's structured pattern for `GenerativeMapping` specifically (the class whose instances actually compile into something and therefore need a real trust gate), while every pre-existing mechanism keeps working exactly as it did.

## Backward compatibility

**Nothing already true about a MORK graph becomes false.** Concretely:

- `mork:reviewStatus`, `mork:supersedes`, `mork:mappingVersion`, `mork:deprecationReason` are untouched — same domain, same range, same meaning. `tools/surface/mork.py`'s `lift()` still asserts `mork:reviewStatus` exactly as before.
- `mork:GenerativeMapping` gaining `fnd:Governable`/`fnd:Version` as superclasses is an OWL open-world addition. A `ShapeMapping` instance with no `fnd:hasGovernanceState` triple is not inconsistent — it is silently incomplete under those two mixins, precisely as every other `fnd:Governable` individual in the substrate is before someone asserts its state (Foundation's own README states this explicitly: "GovernanceState is open at the OWL level, closed in SHACL").
- The new SHACL shapes only produce a validation *failure* under a real SHACL engine, and `GenerativeMappingProductionGovernanceShape` only fires for a mapping whose scheme explicitly declares `mork:compilationMode mork:ProductionMode`. No existing MappingScheme declares this property today (it is new), so no existing mapping graph fails this shape merely by existing.
- `tools/surface/lowering.py`'s `lower_projection`/`lower_contract` (ADR-A18) emit a bare `mork:DataMapping`, not yet a `mork:GenerativeMapping` — none of this phase's shapes target them, and nothing here changes what that module emits.

**What a deployment must do to opt into production governance:**

1. Declare `mork:compilationMode mork:ProductionMode` on the `MappingScheme` whose mappings should be gated.
2. Backfill `fnd:hasGovernanceState` (`fnd:Reviewed`, `fnd:Active`, or `fnd:Superseded` — anything but `fnd:Draft`) and `fnd:hasIdentity` (an `fnd:PersistentIdentity` individual) on every `GenerativeMapping` in that scheme.
3. Anything left at `fnd:Draft` or with no governance state at all fails `GenerativeMappingProductionGovernanceShape` once a SHACL engine runs it — which is the intended production gate, not an accident.

Existing `reviewStatus` values do not automatically map onto `fnd:GovernanceState` individuals (a string `"APPROVED"` does not become `fnd:Active` by itself); this is a deliberate choice, not an oversight, because the two fields answer different questions — `reviewStatus` is per-provenance-record review history, `fnd:hasGovernanceState` is the mapping's own current, structured status. A migration script for a specific deployment may choose to derive one from the other; this repository does not assume that mapping is always correct and does not perform it automatically.

## Foundation migration boundary (delivery-plan Phase 4 item 6)

A related, narrower question — separate from the ontology/governance/versioning alignment above and still open — is whether Surface's own `srf:DerivedArtefact` family (`GeneratedSurface`, `GeneratedSymbol`, `ReadSetEntry`, `LawDischarge`) should migrate to Foundation, becoming subclasses of a Foundation-level `fnd:DerivedArtefact`, or remain layer-local (see `ontology/surface/docs/OUTSTANDING-ITEMS.md` §3.1 and [ADR-A12](../../docs/architecture/decisions/ADR-A12-identity-and-derivation-model.md)).

This guide does not resolve that question. It records the boundary criteria the eventual decision should apply, so the decision itself can be made once rather than re-litigated per layer:

- **Foundation-owned** if the concept is meaningful with no reference to how it was generated — identity, version, governance state, temporal scope, evidence. These are already there.
- **Layer-local** if the concept only makes sense relative to one layer's own generation mechanism — Surface's read sets and symbol records name Surface-specific things (a read path, a naming policy) that have no Foundation-level analogue and would need one invented, not merely reused, to migrate.
- **MORK's governance adoption in this document is a data point for that decision, not a precedent that settles it**: MORK reused Foundation's *existing* `Governable`/`Version` mixins directly, unchanged, because a `GenerativeMapping` needs nothing structurally new from them. Whether `srf:DerivedArtefact` could do the same, or needs Foundation to grow new structure first (as ADR-A12's own consequences section flags for ordered-collection support), is exactly the open question — this document only notes that "reuse without needing new Foundation structure" is the easy case, and `srf:DerivedArtefact` has not yet been shown to be that case.

## Verification plan (not yet run)

No SHACL engine and no Python interpreter were available in the environment this change was authored in. Before relying on any of the above:

1. Validate `ontology/mork/spec/Mork.ttl` still parses as consistent OWL (a reasoner run, not just a syntax check) — the new `rdfs:subClassOf` axioms on `GenerativeMapping` are additive and should not introduce inconsistency, but this has not been checked mechanically.
2. Run `ontology/mork/shapes/constraints.ttl` against a MappingScheme fixture in each of the three compilation modes, confirming: `DraftMode`/unset never triggers `GenerativeMappingProductionGovernanceShape`; `ProductionMode` triggers it exactly for mappings missing governance state or identity; `GenerativeMappingGovernanceStateClosedShape` rejects a `fnd:hasGovernanceState` value outside the four named individuals.
3. Re-run `tools/surface` (`tools/surface/test_surface.py`) to confirm nothing about MORK's own change affects Surface's existing lift/lower/lowering behaviour — none of it should, since Surface only ever asserts `mork:DataMapping`, `mork:ProjectionMapping`, `mork:hasTargetingSpec`, and `mork:hasParameterBinding`, none of which this phase touched.
