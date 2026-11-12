<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Handover: `studio-visual-authoring`, paused 2026-11-12

**Unit:** `studio-visual-authoring` (SVA). **Status record:** [studio-visual-authoring.md](../status/studio-visual-authoring.md), the one authoritative live state. This note is a snapshot for whoever resumes the work, and the status record wins where the two disagree.

The work was paused by the maintainer on 2026-11-12, part way through its second wave of slices. Everything written is committed on the unit's branch, which `mise run work:board` names.

## Read in this order

1. [The sketch](../sketches/studio-visual-authoring.md). Section 4 is the run protocol and section 12 holds every question with its answer.
2. [ADR-A154](../../architecture/decisions/ADR-A154-runs-in-the-configuration-studio.md), Proposed, which states the run protocol as decisions.
3. [The plan](../plans/studio-visual-authoring.md), 31 slices in six phases with what each waits on.
4. [The status record](../status/studio-visual-authoring.md), its board, its probes and its log.

## Where each slice stands

| Slice | State | What exists | What is left |
|---|---|---|---|
| SVA-B1 | built, verified | `rdf/catalog.ts`, `rdf/imports.ts`, 33 tests, [pack](../validation/SVA-B1.md) | nothing |
| SVA-M1 | built, verified | the scheme list in `MappingView.tsx`, `schemeSummary`, [pack](../validation/SVA-M1.md) | nothing |
| SVA-O3 | built, verified | `rdf/axioms.ts`, `ui/AxiomForms.tsx`, 47 tests, [pack](../validation/SVA-O3.md) | nothing |
| SVA-O1 | built, verified | `src/canvas/`, the mapping canvas moved onto it, [pack](../validation/SVA-O1.md) | nothing |
| SVA-R1 | building | ADR-A154 and its catalogue row | the contract's Runs section, the `cst:` terms of a run and a frame, the two run queues in the topology, the fake service's runs. All wait on SVA-R0's limits |
| SVA-R0 | building | the probe scripts `web_mqtt_frames.mjs` and `publish_frames.py` and their notes, in the studio harness's package folder | the probes have not been run to completion and no result is recorded. Run them against a stack with events on, write `docs/developer/validation/SVA-R0.md`, and confirm or change the limits of the sketch's rule 9 |
| SVA-B2a | building | the contract, vocabulary, summaries query, `Workspace`, `Command`, `Writer`, `StudioApi`, the worker's `fence`, and tests for each | review, a Validation Pack, an adversarial probe, and the checks below |
| SVA-O2 | building | nothing. The slice was stopped before it wrote a file | the whole slice |
| every other slice | planned | | |

**SVA-B2a in detail.** The code was written by a delegated developer that was stopped before it reported, so its own account of its decisions does not exist. Run after the pause on 2026-11-12, with no change to the code: the three Java modules compile, `config-studio-core` passes 24 tests, `config-studio-service` 198 and `config-studio-writer` 10, among them the new `ImportsClosureTest` with 14, and `workers/tests/test_config_studio_publish.py` passes 16. That shows the code is consistent. It does not show it is right. To finish the slice:

- read the diff of `Writer.java` and `Command.java` against ADR-A149 decision 13, that the import graphs are written before the description and that a guard failing part way names no import
- confirm the ontology IRI and version IRI on a held import are taken from the fence job's graph in the store and never from the request (PRI-75)
- read the change to `contracts/config-studio/workspace-summaries.rq`. The summaries are evaluated as they are read and are not a stored promotion, so no rebuild should follow, which is to be confirmed and not assumed
- check that a single `job` still takes the path it took before, and that the contract's HTTP row says what the code does
- record whether a workspace's export and its TriG import carry held imports, which the slice was asked to find out and not to change
- write `docs/developer/validation/SVA-B2a.md`, break the ordering of the command to see a test fail, and run `mise run check:config-studio`

## Decisions, and what is open

- SVA-Q1, SVA-Q2 and SVA-Q4 to SVA-Q16 are answered, each on its question in the sketch.
- **SVA-Q3 is open.** The maintainer asked how many triples a request body holds, how large a step is and whether the limit comes from the MQTT frames. The sketch's section 8.2 answers. Only SVA-P3 waits on the maintainer confirming (a).
- **ADR-A154 is Proposed.** Only the maintainer accepts it. Its decision 11 rests on SVA-Q3.
- SVA-M2a will draft an addition to MORK for template libraries (SVA-Q14 (a)), which is a modelling change to design with the maintainer's review, examples first.
- Backlog rows BL-20 to BL-24 were added for what the answers left for later.

## What to do next, in order

1. **Finish SVA-B2a**, as above. It is the nearest to done and SVA-B3 and SVA-B2b wait on it.
2. **Run SVA-R0's probes** and write its record. Phase R, the critical path for the sample pane and both simulators, waits on it.
3. **Finish SVA-R1**: the contract's Runs section with the limits the probes support, then SVA-R2, SVA-R3 and SVA-R4, which touch the service, the run worker and the browser and can proceed side by side.
4. **Build SVA-O2** on the canvas kit. Its brief is the plan's row and the sketch's section 7. Its acceptance is that the shapes toggle adds exactly the edges the facility sample's shapes state, each naming its shape.
5. **SVA-M2a**, the MORK design, can start at any time since nothing else waits on phase R.

## How the built slices were made

Each slice was briefed in writing to a second developer with the files it may touch named, built there, then verified by the developer overseeing the design, who ran the unit tests, the type check and the browser suite again, broke one rule to see a test fail, and only then committed. Lessons worth keeping:

- Two slices of the application can be built side by side only where they share no file. `styles.css` and `e2e/studio.spec.ts` are shared by nearly every slice of the application, which is why SVA-M1 and SVA-O3 are one commit.
- A brief that asks for a browser test of existing behaviour to be written and passed before the change, then again after, is what held the mapping canvas's picture through SVA-O1.
- A brief is often wrong about the code in small ways. Each report listed where, and the status record's log carries what changed as a result, for example that selecting a scheme now clears the selected source concept.

## Not run

`mise run check`, `mise run check:config-studio` as a whole, `mise run test:config-studio-browser` on the real stack and `mise run studio:liveness` have not been run on this branch. The browser suite on the fake service passed with 25 tests after SVA-O1. ROADMAP's generated sections were not regenerated on this branch and need `mise run build:roadmap -- --fetch` on a full clone.
