<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-P1, the exploded view

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-P1, built on 2026-11-17 in autonomous mode.

## Invariant

Where a target's data lands is read by the worker from the compiled profile and the compiler's own code, and written as `landing-places.json` in a persistence compile job. The browser never guesses it from the configuration or from an IRI pattern. The canvas draws only what the latest finished persistence compilation says, and tells the author when the persistence part or the baseline has changed since, or that it cannot tell.

## What changed

- `workers/src/lattice_workers/config_studio_landing.py` reads the artefact. The target, the profiles that won each dimension, the edges of the boundary with their ownership and reference mode, and each operation with its template come from the compiled profile. The scopes a target matches come from `persistence.scopes`, and the graph each operation writes with the rule that names it comes from the typed operation `persistence.instantiate.build_operation` builds. Nothing in `tools/persistence` changed.
- `config_studio_jobs.py` writes the artefact in the group `profile`. `contracts/config-studio/landing-places.schema.json` defines it, and the contract's Jobs section and file table name it.
- `src/persistence/landing.ts` is the browser's pure part, `src/ui/PersistenceCanvas.tsx` the view, and `ConfigView.tsx` offers it as the Canvas option of the Persistence view beside Details.

## Tests

| ID | Given / When / Then | Level | The break tried | The failure it gave |
|---|---|---|---|---|
| P1-T1 | the facility sample compiled / the landing places are read / each target has the places its operations write, with the graph exactly as the operations' bindings give it | L1 | | |
| P1-T2 | a place with a fixed graph / the operations' SPARQL is read / the graph is in the text of each operation that writes it | L1 | | |
| P1-T3 | each place and operation / compared with the job's artefacts / each place names the operations that write it and not those that only read, and each operation's path is an artefact of the job | L1 | | |
| P1-T4 | the profiles and scope nodes of both targets / read / the profiles are the winners the profile records and the scopes are the ones they apply to | L1 | | |
| P1-T5 | a boundary that nests / read / owned edges nest as the shape nests, referenced edges sit beside, a family with no shape has a root and no edges | L1 | | |
| P1-T6 | a target under a patch log and one without / read / the first has patch log add and del places and the second neither | L1 | Leave the patch log places out of the worker | five tests failed, among them P1-T1, P1-T3, P1-T6 and the fixture test |
| P1-T7 | a uniqueness constraint / read, and with it removed / a key claim for each constraint, and none without it | L1 | | |
| P1-T8 | a lender edge marked `Pinned` and the others not / read / each edge has the mode configured | L1 | | |
| P1-T9 | every persistence example / compiled / each document is valid against the schema, every kind of place is found among them, a class deployed twice has a target for each, and a refusal gives none | L1 | | |
| P1-T10 | the same configuration in three shuffled orders of triples and a repeat / compiled / the same bytes | L1 | | |
| P1-T11 | the checked-in browser fixture / compared with what the worker gives / equal | L1 | | |
| P1-T12 | each lens over the fixture / drawn / the picker lists targets, profiles or scope nodes the job holds, the aggregate has root, owned, referenced and places, a place two targets share is drawn once, a referenced edge is dashed with its mode | L1 | | |
| P1-T13 | the fixture in any key order and a repeat / drawn / the same drawing | L1 | | |
| P1-T14 | what was sent and what is held now / compared / current, out of date after an edit or a new baseline, unknown for a compilation this browser did not send | L1 | Make the comparison always say current | P1-T14 failed in the unit suite and the out of date journey failed on the missing alert |
| P1-T15 | the facility sample's Persistence view / Canvas is chosen with no compilation / it says so and offers Compile, and after Compile draws the facility's root, owned Drawdown, three dashed references and seven places | L2 | | |
| P1-T16 | a compiled sample / Profile and Scope node are chosen, a place is clicked / each lists its choices, a borrower has no patch log place, and the place shows its graph and the operations with their paths | L2 | | |
| P1-T17 | a compiled canvas / the persistence part is edited, then compiled again / out of date after the edit and current after | L2 | See P1-T14 | |
| P1-T18 | a compilation started in the Build view / the canvas is opened / it is drawn and says it cannot tell whether it is out of date | L2 | | |
| P1-T19 | a node dragged / read back / its place is kept under the workspace and lens | L2 | | |

The break of P1-T6 was made in `config_studio_landing.py` and the break of P1-T14 in `landing.ts`. Each was run, seen to fail and restored.

## The command

```bash
mise exec -- python -m pytest workers/tests/test_config_studio_landing.py -q
mise exec -- yarn workspace @lattice/config-studio exec vitest run
mise exec -- yarn workspace @lattice/config-studio exec playwright test
mise run check:config-studio
```

## How the fixture is generated

`apps/config-studio/e2e/fixtures/landing-places-facility.json` is the document the worker gives for the facility sample. The fake service answers a compilation of that sample with it. It is written by the worker's own test and checked equal on every run.

```bash
LATTICE_WRITE_LANDING_FIXTURE=1 mise exec -- python -m pytest workers/tests/test_config_studio_landing.py -q -k fixture
```

## Artefacts to inspect

- the fixture above, and `contracts/config-studio/landing-places.schema.json`,
- the Aggregate and Profile screenshots of the facility sample, which a temporary step took and removed.

## Deliberate non-coverage

- Edits on the canvas are SVA-P2.
- The simulator is SVA-P3 and SVA-P4.
- The promoted rows a surface contract keeps are drawn by the surface canvas, SVA-S1.
- The Build view cannot be opened at an artefact, so a place names each operation's artefact path and does not link to it.
- The real service and worker together are not run here, only the fake service with the worker's own output.

## Decisions the brief did not settle

- The place entries carry `operations`, the names of the operations that write them, beside `from`. A template such as `key-claim-write` is used once for each constraint, so the template alone cannot tell which operation, and so which SPARQL file, is meant.
- A target has `scopes`, the scope nodes the winning profiles and the applied constraints apply to, and `matchedScopes`, every scope node `persistence.scopes` says matches it. The compiled profile records the winning profile and not the scope, so `scopes` reads `dal:appliesTo` from the configuration the compiler was given. The Scope node lens uses `matchedScopes`.
- Whether the picture is out of date is known only for a compilation this browser started, by what it sent, the persistence part as the editor held it and the baseline's saved revision. A compilation from the Build view is drawn and marked unknown. Reading what a job was sent would need the service to expose it.
- The Compile button repeats the Build view's submission of the merged parts, since `BuildView.tsx` was not in the files to edit. One shared function would remove the copy.
- The place kinds are one per graph role with `patch-log-add` and `patch-log-del` told apart by the compiler's variable name, `version` for the data graph of an append-versions family and `merge-record` for the keys graph's other resource.

## Results

What the builder ran on 2026-11-17, in autonomous mode:

- `pytest workers/tests/test_config_studio_landing.py` printed 14 passed, and `pytest workers/tests -k config_studio` printed 168 passed.
- `vitest run` printed 30 files and 488 tests passed, 468 before and 20 new.
- `tsc --noEmit` printed nothing and exited 0.
- The browser suite on the fake service, with the headless Chromium already on the machine, printed `67 passed (3.3m)` twice, 62 before and 5 new.
- The two breaks of the table failed as stated and were restored.
- Two screenshots at a device scale factor of 2, of the facility sample's canvas with the navigation collapsed, were taken by a temporary test that is removed. They read plainly after the column gap and the node sizes were widened, since the first picture was fitted at half size and cut an edge label.
