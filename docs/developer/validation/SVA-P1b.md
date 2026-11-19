<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-P1b, the studio reads where data lands from the compiled profile

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-P1b, built on 2026-11-19 in autonomous mode, after [SVA-P1a](SVA-P1a.md) and from the [compiled landing places sketch](../sketches/compiled-landing-places.md), SVA-Q22.

## Invariant

The persistence canvas draws only what the latest finished persistence compilation's `compiled-profile.ttl` states. Each place kind is decided from facts the profile states: the place's `dal:GraphRole`, the access's `dal:resourceKind` and `dal:patchDirection`, and the operation's `dal:operationKind`. Nothing is decided from an IRI pattern or a template's text. A place two targets share is drawn once, merged by its kind, graph and label, since its IRI is minted per target. A profile compiled before SVA-P1a, with no `dal:GraphPlace`, is shown as one that predates the landing places. No second form of these facts is kept.

## What changed

- The worker no longer writes `landing-places.json`. `config_studio_landing.py`, its tests and `contracts/config-studio/landing-places.schema.json` are deleted, and the contract's README, the app's README and the studio's architecture page say the canvas reads `compiled-profile.ttl`. The `check:config-studio` task names the new fixture test in place of the deleted one.
- `apps/config-studio/src/persistence/landing.ts` reads the Turtle with `Graph.parse` of `@lattice/authoring-domain` and builds the model the lenses draw, every list sorted. `PersistenceCanvas.tsx` changes only what it loads. `PlaceKind` loses `derived-rows`, which the surface compiler writes and a persistence profile never states.
- A data graph written by a `dal:AppendVersion` operation is a version, which replaces the worker's test of a builder's name. A key claim's label is its constraint's local name. The profiles are the winners and the scopes those they won through.
- The rule that names a job's artefacts is restated in the browser as `artefactPath` and `groupOf`, with a comment naming where the job writes them, and held by a test against the 24 paths the facility job holds (TD-170).
- The facility fixture is the compiled profile the facility job gives, `e2e/fixtures/compiled-profile-facility.ttl`, with its artefact paths beside it, both checked by `workers/tests/test_config_studio_compiled_fixture.py`.
- The templates the canvas shows are the compiled profile's, `urn:g:txlog/{month}` and `urn:g:borrower/{root}`, and one journey's expected text changed with them.

## Tests

| ID | Given / When / Then | Level | The break tried | The failure it gave |
|---|---|---|---|---|
| P1b-T1 | the facility sample compiled / the job's artefacts are read / it holds `compiled-profile.ttl` and no `landing-places.json`, and the profile states seven places for the Facility and five for the Borrower | L1 | | |
| P1b-T2 | the checked-in fixtures / compared with what the job gives now / equal | L1 | | |
| P1b-T3 | the fixture / read / each place has the kind its role, resource, direction and operation give, and an append-versions operation's data graph is a version | L1 | the `AppendVersion` test removed | the kind test failed |
| P1b-T4 | two targets landing in one graph, with two place IRIs / drawn / one place | L1 | | |
| P1b-T5 | a profile with no place / read / it predates the landing places | L1 | the check for a profile with no place removed | the predates test failed |
| P1b-T6 | the fixture's triples in three seeded orders and a repeat / read and drawn / the same drawing | L1 | | |
| P1b-T7 | each operation of the fixture / its artefact path / one of the paths the facility job holds | L1 | | |
| P1b-T8 | P1-T12 to P1-T14 of SVA-P1, the lenses and the freshness of a drawing / over the new reading / as before | L1 | | |
| P1b-T9 | P1-T15 to P1-T19 of SVA-P1, the canvas journeys / on the fake service / as before, with the compiled profile's templates | L2 | | |

## Checks run

| Command | Result |
|---|---|
| `mise exec -- python -m pytest workers/tests -k config_studio -q` | 157 passed, 75 deselected |
| `mise exec -- python -m pytest tools/test_config_studio_contract.py tools/test_config_studio_stage.py -q` | 45 passed |
| `tsc --noEmit` in `apps/config-studio` | exit 0, nothing printed |
| `vitest run` in `apps/config-studio` | 30 files, 503 tests passed |
| the Playwright journeys on the fake service, all 67 | 66 passed and 1 failed in a full run. The failure, "a handle moves with the arrow keys, Home and End, and a collapsed column takes no focus on Tab", touches nothing this slice changed and passed three times of three alone. Recorded as TD-172 |
| `mise run check:identifiers` | passed, 0 unresolved, run by the delegated developer |
| `mise run check:catalogue` | agrees with the tree, run by the delegated developer |

Each count above was read by the reviewer from its own run, except the two marked. The browser this container has is an older Chromium revision than the pinned Playwright expects, so the journeys ran from a configuration outside the commit that pointed Playwright at the installed one. `mise run test:config-studio` as it stands, and `mise run check:config-studio`, were not run here, and the maintainer runs them before the merge.

## Placement

T0. The studio's code and contract are open.
