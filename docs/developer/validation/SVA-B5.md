<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-B5, a sample whose import graph shows every kind of edge, a drop area, the state's own graphs, and the baseline's validation shown as a part's

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-B5, built on 2026-11-16 in autonomous mode.

## Invariant

A sample exists whose import graph, once its imports are held from LATTICE's documents, draws a stated import, a binds edge and a derived edge, each told apart. A folder dropped onto the import dialog gives each file the path from the dropped root, the form a folder chosen through the input gives, so a catalog's relative entries resolve the same way. The import graph reads the graphs of the workspace's dependencies and held imports from the workspace's state and issues no request for a graph the state already loaded. The baseline's validation is shown wherever a part's is, in the state pill as validating and as unavailable, and in the Overview's count of violations.

## What changed

- **`contracts/config-studio/samples/library-baseline.ttl`, `library-vocabulary.ttl`, `samples.ttl`.** The sample `library-imports`. The baseline is its own ontology under `https://example.org/library` and imports LATTICE's vocabulary layer by its ontology IRI, `https://www.nebularis.org/neuro-semantic/vocabulary`. That layer imports the foundation layer, which the baseline does not. The baseline uses `fnd:Governable`, which only the foundation layer declares, as the superclass of a catalogue entry, so `importGraph` derives an edge from the workspace's ontology to the foundation layer, and no stated edge joins the pair. The vocabulary configuration holds a scheme contract that constrains `lib:subject`, a binding and a scheme of subject headings, so a binds edge is drawn from the workspace's ontology to the scheme.
- **The import by ontology IRI.** `tools/bump_version.py` does not rewrite anything under `contracts/config-studio/samples` (it reads each module's `spec` documents), so a version IRI written there would go stale at the next release. The ontology IRI keeps the sample correct when a layer's version moves, and the staged index answers it as it answers a version IRI.
- **`src/dropEntries.ts` and `ImportDialog.tsx`.** A drop area, a group named "Drop area" that says in words what it takes. The helper walks entry-like objects, reading a directory until a read returns an empty batch, and gives each file its path from the dropped root. The dialog takes the entries before it awaits anything, falls back to the dropped files where a browser gives no entries, and cancels `dragover` and `drop`.
- **`src/state.ts`, `BaselineView.tsx`.** The state keeps each dependency's graph by the IRI the workspace names, and each held import's graph by its digest, filled by the load that already happens, and `BaselineView` reads them and no longer fetches either.
- **`state.ts`, `Workspace.tsx`, `Overview.tsx`.** `validationSummary` gives what the pill reports, over the parts and the baseline alike, and the Overview's count reads the baseline's issues with the parts'.
- **`styles.css`.** The drop area, and a name and an IRI of an import node that wrap, since the two LATTICE layers share a namespace and their labels were cut at the same place.
- **`e2e/fake-service.ts`.** Stand-ins for the two layers under their real IRIs, a registry that serves a published version, a `dependsOn` a workspace can hold, `fail` for jobs that finish as failed, and `baselineViolation`.
- **`tools/test_config_studio_stage.py`.** The expected list of samples gains `library-imports`, and one test checks the new sample. This edits one list in an existing test, which the new sample made necessary.
- **`README.md` of the app and of the contract.** One sentence each, and one row for the samples.

## Tests

| ID | Given / When / Then | Level | The break tried | The failure it gave |
|---|---|---|---|---|
| B5-T1 | a workspace made from the library sample, its imports held with no file given / the Baseline diagram's import graph is opened / four nodes are drawn, two solid import edges and none from the baseline to the foundation layer, one labelled binds edge to the subject scheme, and one derived edge from the workspace's ontology to the foundation layer | L3, positive | `importGraph.ts`, derived edges dropped | the derived edge's title was not drawn, expected 1, received 0 |
| B5-T2 | the import dialog / a file is dropped on the drop area / `dragover` and `drop` are both cancelled, the file is listed as chosen, and the plan holds it | L3, positive | not tried | |
| B5-T3 | a workspace that pins a published version declaring a concept scheme and holds an import / the diagram's import graph is opened / the scheme is drawn, and the page made no request for a held import's graph, a version or a lineage after the diagram opened, with some made before | L3, positive | `BaselineView.tsx`, a fetch of each held import's graph restored when the diagram opens | the count of requests was 4, expected 3 |
| B5-T4 | the baseline's validation never finishes / the workspace opens / the pill reads "Validating" and not "Conforms" | L3, positive | not tried | |
| B5-T5 | the baseline's validation finishes as failed / the workspace opens / the pill reads "Validation unavailable" with the failure as its title | L3, positive | not tried | |
| B5-T6 | the baseline's validation reports a violation / the Overview opens / the count of violations is 1 and the pill reads "1 violation" | L3, positive | not tried | |
| B5-U1 to B5-U7 | `dropEntries.test.ts` / a file alone, nested folders, a directory read in four batches, an empty folder, files beside a folder, the file the entry gave, and a failed read / each has the path from the dropped root, nothing for an empty folder, and a rejection for a failed read | L1 | | |
| B5-U8, B5-U9 | `state.test.ts` / `validationSummary` over parts and the baseline / nothing running or failed when all are done or idle, and running and failed taken from the baseline as from a part, the part's failure first | L1 | | |
| B5-P1 | `test_config_studio_stage.py` / the staged samples and the library sample's file / the sample is listed without its parts, its baseline imports the vocabulary layer alone, both layers are staged and the first imports the second, the baseline uses a foundation term, and the binding names a scheme of the sample | L2, positive | | |

B5-T3 reads what the state loaded by the requests it made, so it asserts that some were made before the diagram opened. It does not tell which request an extra fetch would repeat, only that the total moved. B5-T2 drops a file built in the page, since a browser test cannot make a directory entry, so the walk of a folder is covered by B5-U1 to B5-U7 on entry-like fakes.

**Decisions the brief did not settle.**

- The existing list of samples in `test_config_studio_stage.py` had to change for the new sample to stage. No other existing test was edited.
- The pill's failed state takes the first failed validation in the order of the parts and then the baseline, so a part's message shows when both failed.
- A dependency's graph is kept as the state merges it, with a followed lineage's version IRI renamed to the lineage's IRI. The view used the unrenamed graph before. The import graph reads schemes from it, and a scheme's IRI is not the version's.
- The Overview's count is of violations, as its label says. The baseline's warnings, which are what a missing import gives, do not move it, so B5-T6 gives the baseline a violation through the fake.
- Held imports' graphs are no longer fetched when the Baseline view mounts. The state loads them after the dependencies, so a view that opens first shows a held import without its graph until the state's load ends.
- On the real stack the two layers also import `skos` core and `prov-o`, which are not staged, so the import graph there draws them as two missing imports. The stand-ins in the fake leave them out.

**The one command:** from the repository root, `mise run check:config-studio`, and for the browser suite a temporary Playwright config that points at an installed Chromium, `mise exec -- yarn workspace @lattice/config-studio exec playwright test -c <that config> --trace off`.

## Artefacts to inspect

- The import graph of the library sample, `/tmp/claude-0/-home-user-lattice/bb8e50d1-c3ca-5af7-87f8-246becfac271/scratchpad/sva-b5-imports.png`, taken at a device scale factor of 2.
- `droppedFiles` in `apps/config-studio/src/dropEntries.ts` and `validationSummary` in `apps/config-studio/src/state.ts`.
- `contracts/config-studio/samples/library-baseline.ttl` and `library-vocabulary.ttl`.

## Deliberate non-coverage

- **The sample on the real service.** That the real service stages both layers, serves each by its ontology IRI and holds them is exercised by the real-stack suite. Here the stage is checked by `test_config_studio_stage.py` and `mise run check:config-studio`, and the browser tests run on stand-ins.
- **A dropped folder in a browser.** A test cannot build a directory entry, so the walk is tested on fakes and the browser test drops a file.
- **Timing.** The tests wait on conditions and assert no duration.

## Results

What the builder ran on 2026-11-16, in autonomous mode:

- `mise exec -- python -m pytest tools/test_config_studio_stage.py -q` printed `13 passed`.
- `vitest run` printed 23 files and 374 tests passed, 365 before and 9 new.
- `tsc --noEmit` for `@lattice/config-studio` printed nothing.
- The browser suite, with a temporary Playwright config that points at the Chromium already on this machine, deleted afterwards. Two full runs printed `47 passed (2.0m)` and `47 passed (2.0m)`, 41 before and the 6 new.
- The two breaks of B5-T1 and B5-T3 were made one at a time, each test was seen to fail as the table says, and each break was restored.
- `mise run check:config-studio` exited 0, with 285 Python tests passed, the Maven verify finished and 374 tests passed in 23 files. Its stage printed `staged 48 ontology documents, skipped 0`. It rewrote `ontology/mork/mtp/data/pins.lock.json`, which this slice did not touch.
- The screenshot showed the workspace's ontology with a solid arrow to the vocabulary layer, which has a solid arrow to the foundation layer, a labelled arrow `lib:SubjectContract` to the scheme node, and a dashed arrow from the workspace's ontology to the foundation layer. Before the wrapping rule the two layer nodes both read `www.nebularis.org/neuro-semanti…`, and after it each reads in full.
- Not run: any run against the live stack.
