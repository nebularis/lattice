<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Phase 7 invalidation and regeneration runbook

## Scope

This runbook covers the current Surface and Surface-to-MORK pipeline at stack
depth 1. It uses canonical read-set digests and dependency edges to identify
the smallest regeneration scope.

## Normal source change

1. Recompute current canonical digests for the changed declaration, scheme,
   instance, or surface source.
2. Extract recorded entries with
   `tools.surface.invalidation.read_set_from_manifest`.
3. Compare recorded and current digests with
   `tools.surface.invalidation.compare_read_set`.
4. Pass changed source IRIs to `plan_regeneration`.
5. Regenerate only the returned surfaces.
6. Lower affected Projection contracts again.
7. Recompile mappings and generated artefacts whose mapping appears in the
   returned mapping or artefact scope.
8. Replace the affected package atomically and rerun parity checks.

## Mapping or template change

1. Identify the changed MORK mapping IRI or template dependency.
2. Pass it through `changed_mappings` to `plan_regeneration`.
3. Follow `mork:dependsOnMapping` in dependency order.
4. Regenerate every artefact linked by `mork:generatedBy` or by the executable
   plan's `exe:compiledFromMapping` and `exe:producesArtefact` chain.

## Profile change

A profile change is intentionally broad. Pass the changed profile through
`changed_profiles`. The planner returns every known Surface, mapping, and
generated artefact because profile identity affects naming, canonicalisation,
entailment, symbol mode, and stack policy.

## Canonicalisation change

1. Set `canonicalisation_changed=True`.
2. Treat every recorded `srf:readHash`, `srf:semanticContentHash`, and
   `srf:artefactHash` as stale.
3. Regenerate the entire known package estate in dependency order.
4. Run deterministic regeneration checks and record the new canonicalisation
   version in every profile and manifest.
5. Do not mix old and new canonicalisation packages in one production estate.

## Release gates

Before publishing regenerated output:

- Surface unit tests pass
- MORK compiler tests pass
- read-set freshness is clean for every retained package
- generated MORK artefacts pass governance validation
- generated SHACL and SPARQL checks pass their conformance fixtures
- parity checks pass for the affected questions
- provenance and input hashes are present

## Deferred deeper stacking

Depth greater than 1 remains deferred. Before lifting that ceiling, extend the
planner with transitive artefact-hash freshness, stale-input rejection, cycle
detection over the surface DAG, and measured impact cost.