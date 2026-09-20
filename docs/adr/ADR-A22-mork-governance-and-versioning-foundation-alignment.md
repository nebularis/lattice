<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A22: MORK governance and versioning with Foundation alignment

**Status:** Accepted
**Date:** 2026-09-18
**Supersedes:** none
**Related:** ADR-A12 (identity and derivation-authority model), ADR-A18 (Surface-to-MORK lowering boundary)
**Source plan:** [surface-mork-unified-projection-delivery-plan.md](../../surface/docs/surface-mork-unified-projection-delivery-plan.md)

## Context

`mork/spec/Mork.ttl` has no governance-state or version-identity terms today. Foundation already owns the persistent-identity/version pattern (a version linked to a persistent identity, direct non-transitive supersession) and is gaining `fnd:GovernanceState` individuals (`surface/docs/OUTSTANDING-ITEMS 2.md` finding 15.4). MORK mappings, once Surface lowers Projection contracts into them at volume (ADR-A18), need the same governance gate before production compilation trusts them — otherwise an unreviewed mapping compiles into a production artefact indistinguishably from a reviewed one.

## Decision

**MORK imports Foundation and adopts its governance-state and version/supersession model for mapping sets**, rather than defining a parallel one. Production-mode compilation (ADR-A25, ADR-A28) requires governance state and version identity to be present on a mapping before it compiles.

## Consequences

- MORK's ontology gains a Foundation import — MORK's first dependency of this kind.
- Existing MORK mappings without governance state remain valid for draft and review-mode compilation, and fail production-mode compilation until backfilled. This is a deliberate migration cost, not an oversight.
- Effective-time windows for mapping applicability follow the same Foundation-aligned pattern, rather than a MORK-specific one.
- This resolves, for governance and versioning specifically, the question `OUTSTANDING-ITEMS 2.md` §3.1 raised about Foundation alignment. It does not move `srf:DerivedArtefact` itself to Foundation — that remains a separate, still-open question, unaffected by this decision.

## Addendum (2026-09-18): implemented, with one deliberate deviation

Implemented in `mork/spec/Mork.ttl` (Foundation import; `mork:GenerativeMapping rdfs:subClassOf fnd:Governable, fnd:Version`, cascading to `ShapeMapping`/`RuleMapping`/`TransformMapping`/`ProjectionMapping`; a new `mork:CompilationMode` with `mork:DraftMode`/`ReviewMode`/`ProductionMode` individuals and `mork:compilationMode` on `mork:MappingScheme`) and `mork/shapes/constraints.ttl` (previously empty; three shapes: a closed `fnd:hasGovernanceState` range, a mode-conditional production gate, and an effective-time check on Foundation-aligned supersession). Full account in `mork/docs/governance-and-versioning-migration.md`.

**Deviation from "effective-time windows follow the same Foundation-aligned pattern":** MORK already had working, unwrapped `mork:effectiveFrom`/`effectiveUntil` datatype properties (with an existing GCI requiring them on `mork:supersedes` chains) before this ADR. Wrapping them in a `fnd:TemporalScope` object, as Foundation's own pattern does, would have meant every mapping's effective dates move behind a new intermediate node for no behavioural gain — MORK's flat form already answers the same question. The ADR-A22 decision to align with Foundation stands for governance state and version/supersession, where MORK had no working mechanism to lose; it does not extend to effective time, where MORK already had one. `GenerativeMappingSupersessionEffectiveFromShape` extends the existing GCI to `fnd:supersededBy` rather than introducing `fnd:TemporalScope`.

**Also found and fixed as a prerequisite:** `fnd:GovernanceState`'s four named individuals did not actually exist anywhere in the repository — `docs/architecture/ontology-architecture.md` already recorded this as a known gap, and every reference to `fnd:Active` elsewhere (Surface's examples, Vocabulary's and Party's worked examples) was a forward reference. Declared now in `foundation/vocab/foundation-vocab.ttl`, since none of the above is meaningful without them.

Not executed: no SHACL engine or Python interpreter was available when this was written. See the migration doc's verification plan.
