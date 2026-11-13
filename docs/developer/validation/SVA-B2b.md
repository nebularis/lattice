<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-B2b, LATTICE's documents staged and served by IRI, and the warning for an import no held document declares

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-B2b of the [plan](../plans/studio-visual-authoring.md), from section 5.1 of the [sketch](../sketches/studio-visual-authoring.md), built on 2026-11-13 in autonomous mode.

## Invariant

The service serves a LATTICE ontology document only by an ontology IRI or version IRI that an index written at staging holds, never by a path or file name taken from a request, and never from the web. A request names an IRI, the index names the staged copy, and the copy's name is never given out (PRI-75, each component validates what it receives). A staged folder with no index answers `404` and the service still starts. The browser's import walk goes on through a staged document's own imports, so a baseline importing a substrate layer resolves it and what it imports with no file dropped (ADR-A88, SVA-Q5 (a)). An `owl:imports` that no held document declares is a warning on the importing ontology and never blocks a save, an import or a validation's conforming (SVA-Q7). The results of the validation are sorted, so a repeat gives the same graph.

## What changed

- **`tools/config_studio_stage.py`.** `stage_ontologies` reads `ontology/catalog-v001.xml` with `ontology_catalog.Catalog`, copies each Turtle file the catalog maps under `ontology/` once under the SHA-256 of its content, and writes `ontologies/index.ttl`. A document that is not Turtle or declares no single named `owl:Ontology` is skipped and counted, and the stage prints the count.
- **`contracts/config-studio/studio-vocabulary.ttl`.** `cst:stagedAs`, the staged copy's name, and `cst:Baseline`, a target.
- **`StagedOntologies` and `StudioApi`.** The index is read once at start. `GET /api/ontologies` answers the index without `cst:stagedAs`, with an `ETag` and `304`. `GET /api/ontologies?iri=` answers a document, `404` for an IRI the index does not hold and `400` for a value that is not one absolute IRI. An index entry whose file name is not a content digest with `.ttl`, or whose file is absent, is not listed and not served. `validate` accepts `baseline` as a target and `compile` does not.
- **`workers/src/lattice_workers/config_studio_imports.py`, `config_studio_worker.py`, `config_studio_jobs.py`.** `validate_baseline` gives one `ImportNotHeld` warning for each import no held document declares. The worker tells the held imports from the configuration parts by their graph names, as `_context` does. `_Result.finding` takes an optional result path and value.
- **`apps/config-studio`.** `ResolveInput.staged` may be a map from IRI to a header, so the walk goes through a staged document. `api.stagedOntologies` and `api.stagedOntology` read the two routes, and the Import dialog shows a staged import as "from LATTICE's documents", counts it among those to hold, and fetches its text when it holds it.
- **`e2e/fake-service.ts`, `README.md` files, `mise.toml`.** The fake answers the two routes from two staged ontologies and accepts a baseline validation. The contract, the architecture document and the studio README say what is new. `check:config-studio` runs the new worker test file.

## Tests

| ID | Given / When / Then | Level | Pass |
|---|---|---|---|
| B2b-T1 | the repository's catalog / the stage / the index holds foundation with its one version IRI, its `owl:imports`, and a `cst:stagedAs` that names an existing digest-named copy, and every copy has an entry | L1, positive | `test_the_ontologies_are_staged_with_an_index_of_ontology_iri_version_iri_imports_and_file` |
| B2b-T2 | a catalog mapping two IRIs, MORK's ontology IRI and version IRI, to one file / the stage / one index node and one copy | L1, positive | `test_two_iris_of_one_file_share_one_staged_copy` |
| B2b-T3 | the same tree staged twice / the two `ontologies/` folders / byte-identical | L1, positive | `test_staging_the_ontologies_twice_gives_byte_identical_output` |
| B2b-T4 | a catalog naming a document with two named ontologies, a web location and a missing file / the stage / one document staged, the two-ontology one skipped and counted, the other two not counted | L1, negative | `test_a_document_that_declares_no_single_named_ontology_is_skipped_and_counted` |
| B2b-T5 | a staged folder with an index, one entry naming `../secret.ttl` / `GET /api/ontologies` / `200` listing the ontology IRI, version IRI and imports, with no file name, no `stagedAs` and not the bad entry, an `ETag`, `304` for a matching `If-None-Match`, `200` for another, `405` for `POST` | L2, positive | `StudioApiTest.theStagedOntologiesAreListedWithoutTheirFilesAndCarryAnEtag` |
| B2b-T6 | the same folder / `GET /api/ontologies?iri=` with the ontology IRI, then the version IRI / `200`, the document as Turtle, and `304` for its `ETag` | L2, positive | `StudioApiTest.aStagedDocumentIsServedByItsOntologyIriOrItsVersionIri` |
| B2b-T7 | an IRI the index does not hold, an empty value, a relative value, a value with a space, two values, an undecodable query / the route / `404` for the first and `400` for the others | L2, negative | `StudioApiTest.anIriTheIndexDoesNotHoldIs404AndOneThatIsNotAbsoluteIs400` |
| B2b-T8 | an `iri` of `../vocabulary.ttl`, its encoded form, `/etc/passwd`, `../secret.ttl`, a staged file's name, `ontologies/index.ttl`, a `file:` IRI and an entry the index refused, and the paths `/api/ontologies/{file}` / the routes / always `400` or `404` and never a file's content | L2, negative | `StudioApiTest.aRequestCannotNameAFile` |
| B2b-T9 | a staged folder with no `ontologies/index.ttl` / both reads / `404`, and the service starts and serves the vocabulary | L2, negative | `StudioApiTest.aStagedFolderWithoutAnOntologyIndexAnswers404AndStillStarts` |
| B2b-T10 | a workspace / `validate` with target `baseline`, and `compile` and `propose` with it / `202` with `cst:Baseline` as target, the other parts of the workspace as context and the body as input, and `400` for the others | L2, positive | `StudioApiTest.aValidationOfTheBaselineIsSubmittedLikeAnyOtherAndNamesEveryPartAsContext` and `anInvalidKindOrTargetIs400` |
| B2b-T11 | a held import declaring the imported ontology IRI / the baseline's validation / no finding and `cst:conforms` true | L1, positive | `test_an_import_held_by_its_ontology_iri_is_not_reported` |
| B2b-T12 | a held import declaring the imported version IRI / the validation / no finding | L1, positive | `test_an_import_held_by_its_version_iri_is_not_reported` |
| B2b-T13 | an import nothing holds / the validation / one `sh:Warning` with `ImportNotHeld`, focus the baseline's ontology, `sh:resultPath owl:imports`, `sh:value` the import, a message naming both, no violation, `cst:conforms` true and the job Succeeded | L1, positive | `test_a_missing_import_is_a_warning_on_its_statement_that_does_not_stop_the_baseline_conforming` |
| B2b-T14 | a held import that imports an IRI nothing holds / the validation / a warning with the held ontology as the focus node | L1, positive | `test_an_import_a_held_import_states_and_nothing_holds_is_reported_on_the_held_ontology` |
| B2b-T15 | a held import that imports the baseline's own ontology IRI and version IRI / the validation / no finding | L1, negative | `test_a_held_import_that_imports_the_baseline_itself_is_not_reported` |
| B2b-T16 | a baseline with no named `owl:Ontology`, and one with a blank-node ontology importing an IRI / the validation / no finding and `cst:conforms` true | L1, negative | `test_a_baseline_with_no_named_ontology_has_no_finding` |
| B2b-T17 | a configuration part among the job's context graphs that states an import / the validation / the part is not read as a held import and its import is not reported | L1, negative | `test_a_part_of_the_workspace_is_never_read_as_a_held_import` |
| B2b-T18 | a held document that declares two named ontologies / the validation / it holds no name, so the import it was meant to hold is reported | L1, negative | `test_a_document_declaring_no_single_named_ontology_holds_nothing` |
| B2b-T19 | imports given in another order, run twice / the validation / findings sorted by importing ontology and then IRI, minted nodes in that order, and identical N-Triples | L1, positive | `test_the_findings_are_sorted_and_the_graph_is_the_same_on_a_repeat`, `test_missing_imports_lists_each_pair_once` |
| B2b-T20 | a staged map whose document imports a second one / `resolveImports` / both are staged, the nodes carry the ontology and version IRIs, and the edges follow | L1, positive | `walks through a staged document to its own imports when staged is a map of headers` |
| B2b-T21 | a staged document importing an IRI nothing holds / `resolveImports` / the IRI is missing and names the staged document as importer | L1, positive | `reports an import a staged document states and nothing resolves as missing` |
| B2b-T22 | staged documents that import each other and the root / `resolveImports` / the walk ends and every edge is kept | L1, positive | `ends a cycle through staged documents` |
| B2b-T23 | a baseline importing the fake's first staged ontology, no file given / the dialog, Plan then Hold / the list shows it missing, the plan says "from LATTICE's documents" for it and for the one it imports, "2 to hold now", nothing is held before confirming, then one request holds both under their ontology IRIs and the list shows both held and none missing | L3, positive | `an import only LATTICE's documents give is resolved with no file given, and confirming holds it and the one it imports` |
| B2b-T24 | every earlier test / the whole suites / none is edited but the one that listed `baseline` among the invalid targets | L3, positive | 296 unit tests and 30 browser tests pass, and `check:config-studio` exits 0 |

**The one command:** `mise run check:config-studio`, from the repository root. It stages the assets, runs the stage and worker tests, `mvn verify` for the service, writer and transforms, and the browser's unit tests. The browser suite is `mise run test:config-studio`.

## Artefacts to inspect

- `.build/config-studio/ontologies/index.ttl` after `mise run build:config-studio-assets`, and the digest-named copies beside it.
- `platform/config-studio-service/src/main/java/org/nebularis/lattice/studio/api/StagedOntologies.java` and the `ontologies` method of `StudioApi.java`.
- `workers/src/lattice_workers/config_studio_imports.py` and its test.
- The `staged` handling in `apps/config-studio/src/rdf/imports.ts` and the last browser test of `e2e/studio.spec.ts`.
- The two HTTP rows, the baseline paragraph of Jobs and the paragraph on `ontologies/` in `contracts/config-studio/README.md`.

## Deliberate non-coverage

- **A catalog directory a deployment configures** is BL-22. The service serves the documents staged from this repository only.
- **The import graph drawing** is SVA-B4.
- **The baseline's validation in the problems drawer.** Live validation runs once for each configuration part, and the baseline is no part, so the warning is not yet shown there. The Baseline view's own list of missing imports, which the browser derives from what it holds, already shows the same imports. Driving a baseline validation from `state.ts` needs a baseline slot beside `configs`, a generalised `useValidation` that submits the baseline as its body and runs again when a held import changes, `api.submit` taking `baseline` as a target, and a baseline entry in the issues the drawer lists.
- **The real stack.** The browser test runs on the fake service, and `test:config-studio-browser` exercises the real one and was not run here.
- **RDF/XML in the staged folder.** Only Turtle is staged. Another syntax would be skipped and counted.
- **A document with several named ontologies.** It is skipped and counted, so an import that only it could give stays missing.

## Results

What the builder ran on 2026-11-13, in autonomous mode:

- `python -m pytest tools/test_config_studio_stage.py -q`, 12 passed, 8 before and the 4 new ones.
- `mvn -q -o -pl config-studio-core,config-studio-service,config-studio-writer -am test` ended with no failure. The surefire reports total 24 tests in core, 204 in the service, 6 more than before, and 10 in the writer.
- `python -m pytest workers/tests -q -k config_studio`, `152 passed, 75 deselected`, which includes the 10 new tests of `test_config_studio_imports.py`.
- `vitest run`, 18 files and 296 tests passed, 3 more than before. `tsc --noEmit` printed nothing.
- The browser suite, with a temporary Playwright config that points at the Chromium already on this machine and was deleted afterwards, printed `30 passed`. The new test failed once on an ambiguous locator, since the row of the second document also names the first as its importer, and passed after the locators were anchored.
- `mise run check:config-studio`, exit 0, with `161 passed` for the stage and worker tests, 296 browser unit tests, and a silent `mvn verify`. Its whole output is kept in the builder's scratchpad.
- `mise run build:config-studio-assets` printed `staged 48 ontology documents, skipped 0`.
- The check rewrote `ontology/mork/mtp/data/pins.lock.json` as a side effect of building the teaching pack. It was left as it is.
- Not run: `mise run test:config-studio-browser` and any run against the live stack.
