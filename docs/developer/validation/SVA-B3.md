<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-B3, the list of ontologies and the import dialog

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-B3 of the [plan](../plans/studio-visual-authoring.md), from section 5 of the [sketch](../sketches/studio-visual-authoring.md), built on 2026-11-13 in autonomous mode.

## Invariant

The author sees how every import resolves, and what is missing, before anything is written. A closure is held by one request or not at all. Nothing is fetched from the web (SVA-Q5). An imported document is held as a fenced import and never merged into the baseline (SVA-Q6, ADR-A149 decision 6). What is missing is shown in the Baseline view at all times and never blocks, neither the import of the rest nor a save (SVA-Q7). The view shows an import as held only after the service has answered. The list of ontologies is derived from the baseline, the held imports and their loaded graphs, so it follows a replaced baseline with no further step.

## What changed

- **`src/rdf/held.ts`.** Pure. `heldByIri` gives the input `resolveImports` takes as `held`, `missingImports` the `owl:imports` objects of the baseline and of each loaded held import that no held import declares, and `ontologyList` what the left list shows. Sorted, so input order does not matter.
- **`src/ui/ImportDialog.tsx`.** Choose, Plan and Hold as three states of one component. Fence jobs run at most four at a time, a failure stops the rest and holds nothing, and one `holdImports` request names every job.
- **`src/ui/BaselineView.tsx`.** The Ontologies section above the class tree, the Import ontologies button, and a line when imports are not held.
- **`src/api.ts`.** A held import gains `ontology` and `version`. `submitFence` and `holdImports` are new, and `fenceImport` calls them.
- **`e2e/fake-service.ts`.** Fence jobs with a digest and declarations, `POST imports` with repeated `job` and `label` and all or nothing, `GET` and `DELETE` of a held import.
- **`src/styles.css`, `README.md`.** Appended rules and the Baseline row.

## Tests

| ID | Given / When / Then | Level | Pass |
|---|---|---|---|
| B3-T1 | a held import declaring an ontology IRI and a version IRI / `heldByIri` / both IRIs give its digest, and `resolveImports` reports the imports as held | L1, positive | Expected map and statuses |
| B3-T2 | a held import that declares nothing / `heldByIri` / no IRI | L1, negative | Empty map |
| B3-T3 | a baseline importing a held and an unheld ontology / `missingImports` / the unheld one, importer the baseline | L1, positive | Expected list |
| B3-T4 | a loaded held import that imports an unheld ontology / `missingImports` / it is missing, importer the held ontology, and with two importers both are named, sorted | L1, positive | Expected lists |
| B3-T5 | a held import whose graph is not loaded, a held import with no ontology IRI, a baseline with no `owl:Ontology`, a self import / `missingImports` / nothing missing | L1, negative | Empty lists |
| B3-T6 | a baseline, held imports and missing imports / `ontologyList` / own, held by label, missing by IRI, and a line for a baseline declaring none | L1, positive | Expected entries |
| B3-T7 | the same inputs in other orders / `heldView` / identical output | L1, positive | Equal JSON |
| B3-T8 | long IRIs and labels / `shortIri`, `shortLabel` / cut in the middle, labels to 200 characters | L1, positive | Expected lengths |
| B3-T9 | a baseline importing two ontologies, a dropped file for one, a catalog mapping the other to a file not dropped / the dialog, Plan then Hold / the list shows both missing, the plan shows "from a dropped file" and "missing" with the catalog problem, nothing is held before confirming, one request names one job, the baseline is not saved, then the list shows one held with its IRI and one missing | L3, positive | The test passes |
| B3-T10 | a catalog mapping an import to a file with an unrelated name / the plan / "from the catalog" and the path, and it is held | L3, positive | The test passes |
| B3-T11 | one valid file and one file that is not Turtle, both resolved / Hold / the file is shown failed, no request holds anything, the dialog stays open, both imports stay missing | L3, negative | The test passes |
| B3-T12 | the 26 earlier browser tests / the whole suite on the fake service / none changes | L3, positive | 29 tests pass |

**The one command:** `mise exec -- yarn workspace @lattice/config-studio exec vitest run src/rdf/held.test.ts`, from the repository root. `mise exec -- yarn workspace @lattice/config-studio exec tsc --noEmit` checks the types, and `mise run test:config-studio` runs the browser suite.

## Artefacts to inspect

- `apps/config-studio/src/rdf/held.ts` and its test, `src/ui/ImportDialog.tsx`, and the new section of `src/ui/BaselineView.tsx`.
- The three browser tests at the end of `apps/config-studio/e2e/studio.spec.ts`.
- `STAGED_DOCUMENTS` in the dialog, an empty constant that SVA-B2b fills.

## Deliberate non-coverage

- **LATTICE's staged documents and the validation warning** on an `owl:imports` with no held document are SVA-B2b.
- **The import graph drawing** is SVA-B4.
- **The real service.** The browser tests run on the fake service. `test:config-studio-browser` exercises the real one and this slice did not run it.
- **Dropping a folder on the page.** A folder is chosen with the Folder input. Dragging files onto the dialog is not built.
- **A baseline that declares no ontology.** The plan says so and resolves nothing, since the walk starts at the baseline's ontology.
- **RDF/XML held imports** are read for their header only in the browser, and the fake returns a header for their graph.

## Results

What the builder ran on 2026-11-13, in autonomous mode:

- `vitest run`, 18 files and 293 tests passed, 277 before and the 16 new ones.
- `tsc --noEmit` for `@lattice/config-studio` printed nothing.
- The browser suite, with a temporary Playwright config that points at the Chromium already on this machine, deleted afterwards, printed `29 passed`. One new test failed once on an ambiguous locator, since a held import's name and its IRI both showed the IRI, and passed after the row showed it once.
- Two screenshots at device scale 2 from a temporary spec, deleted afterwards, were read by the builder. The plan table, the catalog problem and the summary line are readable. The Baseline list shows the workspace, one held and one missing import in warning colour, and the line "1 import is not held."
- Not run: `mise run check:config-studio`, `mise run test:config-studio` as written, and any run against the live stack.
