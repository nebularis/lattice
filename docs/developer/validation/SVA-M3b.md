<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-M3b, the sample pane

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-M3b, built on 2026-11-20 in autonomous mode, from section 10.3 of the [sketch](../sketches/studio-visual-authoring.md), SVA-Q15 and ADR-A154 with its addendum of 2026-11-20.

## Invariant

A sample runs when the author presses Run and never by itself. Pressing Run compiles the mapping part when it, or a part a compilation reads beside it, has changed since the last compilation, and then starts a `sample` run over the finished compile job through the run controller. An edit of the scheme or of another part, a new sample, a new sample format or a new choice of form starts nothing, not a compilation and not a run. The counts on the mapping canvas, the tree and the scheme list are those of the last run that completed, kept with the part, the other parts' revisions, the sample and the format they were counted from, and are marked out of date as soon as any of the four differs. A run that fails leaves the counts of the last completed run as they were. A form no runtime runs offers no Run. The studio no longer calls the deprecated transforms route.

## What changed

- **`src/sample.ts`, the pane's model.** `FORM_TABLE` is the sketch's table, SPARQL CONSTRUCT for an RDF source, XSLT 3.0 for XML and JOLT for JSON with a runtime, and RML with none. `formsOf` lists the forms a compilation wrote for a scheme from its artefacts and `sourceFormats` reads the formats a scheme reads from the part, as `mork:format` names them. `createSampleSession` keeps the sample and its format in the browser's storage, as before, the last compilation, the chosen form, and the last completed run with what it ran over. It is a store like the run controller, so its rules are tested without a page.
- **`src/ui/RunPane.tsx`, the Sample tab.** Controls on the left: the scheme, with the template libraries it instantiates from listed under it where it has any (none yet, since libraries arrive with a later slice), the forms of the last compilation each with its path, whether it runs here and a download, the sample as a text box or a file with its format, and Run. Displays on the right: the status line, the engine the run's report names, a note when the counts are out of date, and each part through the output explorer. An RML form says in words that it waits on an RML runtime. A form the author chose that cannot read the sample's format says so. Where no form of the scheme reads the sample's format, Run is on and the pane says the run covers the other schemes of the part that do, since a run covers every scheme of the part that reads the sample's format. The example buttons moved here from the list, and choosing one selects the scheme that reads its source.
- **`src/ui/MappingView.tsx`, `MappingCanvas.tsx`.** `useSampleRun`, its 800 ms timer, the dry run of a Turtle sample, the sample panel of the list and the stored-transform download are gone. The scheme is the session's, so the pane and the list agree on it. The tree, the canvas, the scheme list and the mapping card read the counts from the last run, mark them as out of date once they are, and a chip in the Mappings header says so.
- **`src/ui/Workspace.tsx`.** One session a workspace, made when it opens, given the mapping part and the other parts' revisions as they are.
- **`src/api.ts`.** `transform`, the client of the deprecated route, is removed.
- **The Java run worker.** The report of a sample run over XML or JSON names its engine as `cst:engine`, as the Python worker's already did, `Saxon-HE 12.5, XSLT 3.0` or `JOLT 0.1.8`. The JOLT version is read from the descriptor Maven keeps in the library's jar, since the shaded jar replaces the manifest. The contract's report row, the vocabulary's comment on `cst:engine` and the two READMEs say so, and that the studio no longer calls the transforms route.
- **The fixture and the fake service.** `e2e/fixtures/sample-runs.json` holds, for the two workspaces of the journeys, what the browser submits to compile the mapping part and the compilation the compiler gave for it, and for each run the sample and the frames the worker gave. The fake service's canned frames are gone. It answers a compile of a body the fixture holds with that compilation, a run of a sample the fixture holds over that compilation with those frames, and anything else with one failed frame that says so. The switches that make a run fail, be refused, expire or give another artefact text stay, for the tests of how the pane shows them.

## How the fixtures stay current

Each owner checks its own part and writes it only when asked, and no frame is written by hand.

| Part | Owner | Check | Write |
|---|---|---|---|
| the body the browser submits to compile each workspace's mapping part, the baseline and other parts beside it, and each sample | `src/sample.journey.test.ts` | builds them from the staged sample, the repository's files and the example a source carries, as the browser saves, reads and submits them | `UPDATE_SAMPLE_RUNS=1` |
| each compilation | `workers/tests/test_config_studio_sample_runs.py` | compiles the body with the worker's job logic and compares the artefacts, a Turtle artefact as a graph, since the RML file of a workspace with two formats is written in an order that changes from one process to the next | `LATTICE_WRITE_SAMPLE_RUNS=1` |
| the frames of the Turtle run | the same test | runs the sample over a compile job with `RdfRunWorker` and compares the frames, each held to the frame schema | the same |
| the frames of the XML and JSON runs | `SampleRunsTest` in the run worker | runs the sample over the fixture's compilation through `RunWorker` and compares the frames, each held to the schema | `-Dsamples.update=true` |

## Tests

| ID | Given / When / Then | Level | The break tried | The failure it gave |
|---|---|---|---|---|
| M3b-T1 | the recorded compilations / the forms of each scheme are listed / the XML scheme has XSLT, the JSON scheme JOLT and RML with no runtime, the catalogue's scheme SPARQL CONSTRUCT, and a scheme's queries are offered only for an RDF source | L1 | | |
| M3b-T2 | a session given a part, a scheme and a sample / each is edited or changed, and a form is chosen / no compilation and no run | L1 | | |
| M3b-T3 | a session / Run is pressed, the part is edited, another part is saved, a sample is run again / one compilation for the same part and parts, another for a changed one, the replaced one removed, and one the pane found is left alone | L1 | | |
| M3b-T4 | the JSON scheme's RML form chosen / Run is pressed / no run, the reason in words, and no identifier of a working document in it | L1 | | |
| M3b-T5 | a form the author chose that cannot read the sample, and a scheme no form of which reads it / Run / the first is refused with a reason, the second runs the other schemes and says so | L1 | | |
| M3b-T6 | a completed run / the part, another part, the sample or its format changes, and a new run is made / the counts are out of date after each, current again when the same content returns or a run is made, and kept when a later run fails | L1 | | |
| M3b-T7 | the recorded XML and Turtle runs / completed / the report then an artefact for each mapping reach the explorer as parts, the engine is read from the report, and the counts are by mapping and stratum | L1 | | |
| M3b-T8 | the fixture / checked against the browser, the Python worker and the Java run worker / each side fails when its part is stale | L1 | a body, a sample, a frame of each worker and a compiled artefact each changed | see below |
| M3b-T9 | a Turtle workspace of the journeys, typed with the catalogue sample / the author waits longer than the old rerun, presses Run, edits the scheme and undoes it / nothing ran before Run, one compilation and one run after it, the mork_rdf engine named, the counts marked out of date after the edit in the tree, the list and the pane, and current after the undo | L2 | | |
| M3b-T10 | the policies workspace with the XML example / Run, then an edit of the sample, then Run, then the sample put back / nothing ran before Run, Saxon named, the XSLT form with a runtime, the counts marked out of date in the tree and the canvas after the edit and kept after a failed run, current when the sample returns, and no request to the transforms route | L2 | | |
| M3b-T11 | the JSON example / Run, then the RML form chosen / the JOLT form runs and is named, the RML form says it waits on a runtime, Run is off, and choosing JOLT turns it on | L2 | | |

The breaks of M3b-T8 were each tried by changing the fixture and running the owner's check. Another sample body in the compile body failed `sample.journey.test.ts`. One more character in a Turtle frame failed the Python worker's test, naming the run. One more comment in the XSLT artefact failed its compilation check. One more character in an XML frame failed `SampleRunsTest`, naming the run. Each was then restored.

## Checks run

| Command | Result |
|---|---|
| `tsc --noEmit` in `apps/config-studio` | exit 0, nothing printed |
| `vitest run` | 36 files, 564 tests passed |
| the whole Playwright suite on the fake service, from a configuration outside the commit pointing at the container's Chromium, `--trace off` | 73 passed, none failed, so none was rerun |
| `mise exec -- python -m pytest workers/tests -k config_studio -q` | 232 passed, 75 deselected |
| `mise exec -- python -m pytest tools/test_config_studio_contract.py tools/test_config_studio_stage.py tools/testing/studio_harness/tests -q` | 94 passed |
| `mise exec -- mvn -o -f platform/pom.xml -pl config-studio-transforms -am verify` | BUILD SUCCESS, the run worker's 62 tests, 0 failures and 0 errors |
| `mise run check:identifiers`, `mise run check:catalogue` | passed |

## Left open

- The fixture's compilations are of the mapping part with an empty baseline and no other part, as the two workspaces of the journeys have it. A workspace with a baseline or other parts would give the worker more to read, and the fixture records both for each workspace so that the test passes them as the service does.
- The RML artefact of a workspace with two source formats is not byte-stable from one process to the next, so its check compares graphs. TD-151 records that one RML file serves both formats, and compiling each scheme on its own would remove the unstable order.
- A run covers every scheme of the part that reads the sample's format, whatever scheme the pane lists, since the service takes no scheme or form. The pane says so where the listed scheme has no form that reads the sample. Choosing a form only gates Run.
- A compilation the pane did not make, such as one started in Build, lists its forms before Run, and Run compiles again since the pane cannot tell whether it is current.
- The capabilities register's CAP-100 and the sketch's table row for the sample run still describe the automatic rerun.

## Placement

T0. The studio's code, worker and contract are open.
