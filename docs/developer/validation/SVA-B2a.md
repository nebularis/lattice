<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-B2a, holding a closure of imports in one write

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-B2a of the [plan](../plans/studio-visual-authoring.md), from section 5.1 of the [sketch](../sketches/studio-visual-authoring.md), with the checks run on 2026-11-12 in autonomous mode.

## Invariant

A closure of imports is held by one command, so the description is replaced once and no reader sees part of a closure. A guard that fails part way leaves no description naming an import that was not written. An import is stored once by its digest, however many jobs or workspaces hold it. What an import declares, its ontology IRI and its version IRI, is read by the worker from the document's content and copied by the writer from the finished fence job in the store, never taken from a request or from a command's own claim (ADR-A149 decisions 6 and 13, PRI-75). The writer checks each job itself, whatever the service checked.

## What changed

- **Contract.** `POST /api/workspaces/{ws}/imports` takes `job` once or more, at most 64, and `label` once for each in the same order. `cst:declaresOntology` and `cst:declaresVersion` are declared, are allowed on a fence job's result, and are read by the workspace summaries query. The `fence` command gains a form that carries one to 64 imports, each with its label and its fence job. `contracts/config-studio/README.md`, `studio-vocabulary.ttl`, `workspace-summaries.rq` and `docs/architecture/configuration-studio.md` say so.
- **`fence` in `config_studio_publish.py`.** The job gives `cst:declaresOntology` when the document has exactly one named `owl:Ontology`, and `cst:declaresVersion` when that ontology has exactly one `owl:versionIRI`. Otherwise it gives neither and adds one `sh:Info` result with the code `NoOntologyIri`. The job still succeeds.
- **`StudioApi.fence`.** It reads every job from the store, refuses the whole request when any is not a finished fence job of the workspace, and sends one command.
- **`Writer.fence`.** It checks each job in the store, creates each import, then replaces the description once, with the declarations copied from the jobs.
- **`Workspace`.** It holds a `declared` map beside `imports`, and reads and writes it in the description.
- **Nothing else.** No UI file and no staging change.

## Tests

Levels are L1 for one function, L2 for the service, the writer and an in-memory store together.

| ID | Test | Given / When / Then | Level | Pass |
|---|---|---|---|---|
| B2a-T1 | `ImportsClosureTest.severalJobsAreHeldByOneCommandWhichReplacesTheDescriptionOnce` | three finished fence jobs / one POST with three `job` and three `label` / 201, the description moved by one step, one receipt of four writes, three imports stored and labelled, `Location` names the first | L2, positive | Steps before plus 1, receipts plus 1, imports equal to the three labels |
| B2a-T2 | `twoJobsOfOneDigestHoldItOnceUnderTheFirstLabel` | two jobs that digested one import / POST with both / one import under the first label, created once | L2, positive | One import with label `First`, its version row at 1 |
| B2a-T3 | `aSingleJobIsHeldAsBefore` | one job with no label, then one with a label / POST each / labelled `Import` and as named | L2, positive | Imports equal to the expected maps |
| B2a-T4 | `aFailedForeignUnfinishedOrUnknownJobAmongThemRefusesTheWholeRequestAndWritesNothing` | one good job beside a failed, an unfinished, a non-fence, another workspace's, a missing and a malformed job id / POST each pair / 409, 409, 409, 404, 404, 404 and the good job is not held either | L2, negative | No description step, no receipt, no import stored |
| B2a-T5 | `thePairingOfJobsAndLabelsIsExact` | fewer, more and no labels for two jobs, an empty and an overlong label, no job / POST / 400 for each of the first five and 404 for no job, then labels pair with jobs by order among their own kind | L2, negative and positive | Nothing written by the refusals, then `Second` for the second job and `Third` for the first |
| B2a-T6 | `atMostSixtyFourJobsAreHeldInOneRequest` | 65 job ids, then 64 finished jobs / POST / 400 whether or not the jobs exist, then 201 with one step | L2, negative and positive | Nothing written for 65, 64 imports in one step |
| B2a-T7 | `whatADocumentDeclaresIsReadBackFromTheDescriptionTheWorkspaceAndTheSummaries` | jobs that declare an ontology and a version, an ontology only, and nothing / POST, then read the stored description, `GET` the workspace and `GET /api/workspaces` with the contract's own summaries query / the declarations appear on each import's root beside its label, and not for the job that gave none | L2, positive | Each of the three reads has the expected triples and none for the third |
| B2a-T8 | `aVersionIriWithoutItsOntologyIriAndAnOntologyIriThatIsNotAnIriAreNotRecorded` | a job with a version IRI and no ontology IRI, and a job with two ontology IRIs / POST / neither is recorded | L2, negative | `declared()` is empty |
| B2a-T9 | `theIrisComeFromTheJobsGraphAndNothingInTheRequestCanSayOtherwise` | a request that adds `ontology` and `version` parameters, and a command whose default graph adds a `cst:declaresOntology` triple / POST and `writes.send` / the request's parameters are ignored and the command is refused with 400 | L2, negative | Only the job's declaration is stored, the forged command leaves no import |
| B2a-T10 | `theWriterChecksEachJobItselfWhateverTheServiceChecked` | commands sent to the writer directly with a failed job, another workspace's job, a job that digested another import, a missing job, no imports, 65 imports, an overlong label and an empty graph / `writes.send` / 400 each | L2, negative | Nothing written |
| B2a-T11 | `aFenceCommandSurvivesTheWireAsTheWriterReadsIt` | a two-import command encoded and decoded by `Codec` / `writes.send` / applied, with the declaration of the first only | L2, positive | Imports and declarations equal the expected maps |
| B2a-T12 | `aWorkspaceThatIsReadOnlyForAPrincipalRefusesTheWholeCommand` | a read-only workspace and another principal / a fence command / 403 and nothing written | L2, negative | No step, no import graph, no import named |
| B2a-T13 | `aHeldImportReleasedAndHeldAgainKeepsWhatItsJobDeclares` | a held import with declarations / release, then hold again from the same job / the description keeps no declaration after release and has it again after | L2, positive | `declared()` empty, then equal to the declaration |
| B2a-T14 | `anExportCarriesTheHeldImportsAndTheirLabelsAndWhatTheyDeclareAndAnImportRestoresThemWithoutTheirContent` | a workspace holding one declared import / `GET …/export`, then `POST /api/workspaces` with the TriG / the export names the import with its label and declaration and has no graph for its content (TD-135), and the new workspace holds the import by name with its declaration | L2, positive | 201, imports and declarations equal, `containsNamedModel` false for the content |
| B2a-T15 | `ReceiptsTest.aFenceOfSeveralImportsWhoseDescriptionGuardFailedLeavesNoImportNamedAndARetryHoldsAllOfThem` | three jobs, and another writer replacing the description between this writer's read and its update / `apply` / 400 with no receipt and no import named, the import graphs applied first and unread, then the same command again holds all three | L2, negative and positive | First apply 400 with an empty description, second `ok`, three imports and three declarations, receipt present |
| B2a-T16 | `test_a_fence_job_gives_the_ontology_iri_and_the_version_iri_the_document_declares` | a document with one ontology and one version IRI / `fence` / both on the job and no information result | L1, positive | `declaresOntology` and `declaresVersion` equal, no `NoOntologyIri` |
| B2a-T17 | `test_a_fence_job_gives_no_version_iri_for_an_ontology_that_has_none_or_several` | an ontology with no version IRI, and one with two / `fence` / the ontology IRI, no version IRI | L1, negative | `declaresVersion` is `None` both times |
| B2a-T18 | `test_a_document_with_no_named_ontology_records_neither_iri_and_says_so_as_information` | a document with no ontology, and one with a blank node ontology / `fence` / neither IRI, one `sh:Info` with `NoOntologyIri`, the job still conforms and has its digest | L1, negative | Both IRIs `None`, `conforms` true |
| B2a-T19 | `test_a_document_with_two_named_ontologies_records_neither_iri_and_says_so_as_information` | two named ontologies / `fence` / neither IRI, one `NoOntologyIri` | L1, negative | Both IRIs `None`, `conforms` true |
| B2a-T20 | `test_what_a_document_declares_does_not_change_its_digest_beyond_its_content` | the same document twice / `fence` / the same digest | L1, positive | The two digests are equal |

**The one command:** from `platform/`, `mise exec -- mvn -q -o -pl config-studio-core,config-studio-service,config-studio-writer -am test`, and from the repository root, `mise exec -- python -m pytest workers/tests/test_config_studio_publish.py -q`. `mise run check:config-studio` runs the wider suites and does not include the second file.

## Artefacts to inspect

- `platform/config-studio-core/src/main/java/org/nebularis/lattice/studio/writes/Writer.java`, `fence` and `fenced` (lines 354 to 460).
- `platform/config-studio-service/src/main/java/org/nebularis/lattice/studio/api/StudioApi.java`, `fence` (line 1077).
- `workers/src/lattice_workers/config_studio_publish.py`, `declared` and `fence`.
- `ImportsClosureTest.java`, the added part of `ReceiptsTest.java` and the added tests of `test_config_studio_publish.py`.

## Deliberate non-coverage

- **The browser's use of the route.** Sending one fence job per resolved document and then the one POST is SVA-B3.
- **LATTICE's staged documents and the missing-import warning.** What the service stages and the validation warning for an `owl:imports` with no held document are SVA-B2b.
- **The worker and the writer together.** No test runs a real worker's job through the real writer. The jobs of the Java tests are written as the worker leaves them, and the Python tests stop at the job's graph.
- **A digest checked against content.** See finding B. No test asserts it, since nothing does it.
- **An import's content in an export.** See finding A and TD-135.

## Findings

**A. Export and import of a workspace.** The export names a held import and does not carry its content. `StudioApi.export` (line 627) writes the workspace's description view, each part and each document, and no graph of an import. The description names each held import by `cst:holdsImport`, with its label and, now, what it declares, so those travel. A TriG imported as a new workspace, here or in another store, is read by `ImportedWorkspace.of` and `Writer.importing` (line 731), which build the workspace with `Workspace.from` from that description and write the parts and documents only. The new workspace therefore holds imports by name, and their content graphs are present only if the same digest was fenced into that store before. This was so before the slice. `export` is identical in `1dd35000` (line 626 there), `Workspace.toModel` already wrote `cst:holdsImport` and the label, and `Writer.importing` is untouched by the diff. The behaviour is recorded as TD-135. This slice adds only the declarations to what travels, and `anExportCarriesTheHeldImportsAndTheirLabelsAndWhatTheyDeclareAndAnImportRestoresThemWithoutTheirContent` (`ImportsClosureTest.java`, lines 358 to 376) shows both, asserting the content graph is absent at line 369 and the restored imports at lines 374 and 375.

**B. Who checks that an import's content matches its digest.** Nothing does, and nothing did before. The worker computes `digest(imported)` and serialises the same graph as the artefact `import.nt` (`config_studio_publish.py`, `fence`), and writes both onto the job. `StudioApi.fence` reads the job's graph from the store (line 1098), takes the artefact `import.nt` (line 1104) and the job's `cst:digest` (line 1108) from that graph, parses the artefact (line 1117) and passes both, with the job id, in `Command.Fenced` (line 1121). So the content comes from the job's graph in the store, and the request supplies only the job ids and labels. The writer (`Writer.fenced`) reads the job again and checks that it is a finished fence job of this workspace and that its `cst:digest` equals the digest in the import's name (lines 428 to 433), which is the check the adversarial probe below removes. It then stores the command's graph with `Skolem.skolemise` (line 370) under that name and does not recompute a digest of what it stores. Neither does the service, nor `ops.create`. Before the slice the service took the digest and the content from the job the same way (`StudioApi` lines 1090 and 1094 in `1dd35000`) and the writer checked only that the name was 64 lower-case hexadecimal digits and that the graph was not empty (`Writer` line 353 there). So the writer now checks more than it did, that the job and the name agree, and the content is trusted as the worker's, since the worker's job update may set `cst:digest` and the artefact (`WORKER_PREDICATES`, `Writer.java` line 69 to 72). A second matter in the same place is that the older single-import form, a command with a digest as its part and no job (`Writer.fenced`, the branch for a non-null part, line 387), is still accepted from any sender and checks no job and no digest. `Command.fence(ws, digest, label, content)` has no caller in main code.

## Results

The results are filled at verification. What was run on 2026-11-12 in autonomous mode, in a checkout where `ontology/mork/mtp/data/pins.lock.json` is modified by `mise run check:config-studio` and was left as it was written.

- `mise exec -- mvn -q -o -pl config-studio-core,config-studio-service,config-studio-writer -am test` exited 0. Summing the `Tests run` lines of each module's `target/surefire-reports/*.txt` gives `config-studio-core` 24 tests, 0 failures, 0 errors, `config-studio-service` 198 tests, 0 failures, 0 errors, and `config-studio-writer` 10 tests, 0 failures, 0 errors.
- `mise exec -- python -m pytest workers/tests/test_config_studio_publish.py -q` ended with `16 passed, 13 warnings in 0.27s`.
- `mise run check:config-studio` exited 0 in 97.30s. It printed 21 tests passed in `@lattice/authoring-domain`, `157 passed, 38 warnings` for its pytest suites, and 234 tests passed in 15 files for `@lattice/config-studio`. Its Maven step runs with `-q` and prints no test count. It printed the Python deprecation warnings, a `UserWarning: Code: _mock_name is not defined in namespace XSD`, Jena `Bad IRI` warnings and expected parse errors from negative tests, a logged `java.io.IOException: broker down` from a test of a failing bus, one `WARN` that the promotion `holders-follows-promotion` changed since the last rebuild, and `SXXP0003` and `XTMM9000` messages from negative XSLT tests. It printed no failure.
- Adversarial probe, 2026-11-12: the writer's check that a fence job digested the import it names was removed. `theWriterChecksEachJobItselfWhateverTheServiceChecked` failed, expecting 400 and getting 200. Restored, 14 of 14 passing.
- Not run: the browser suites, `studio:up` and `studio:down`, and any stack test.
