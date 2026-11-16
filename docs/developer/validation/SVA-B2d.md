<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-B2d, a fence reads its imports from their fence jobs

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-B2d, closing finding B of the [SVA-B2a pack](SVA-B2a.md), with the checks run on 2026-11-16 in autonomous mode.

## Invariant

An import's content is what its fence job digested, and the writer reads it from that job in the store. A `fence` command carries no content, no named graph and no part, only, for each import, its root, its label and its fence job. The writer checks that each job belongs to the command's workspace, is a finished fence job and has the digest in the import's name, then stores the job's one `import.nt` artefact, so no command can store a graph under a digest by naming it alone (PRI-75, ADR-A149 decisions 6 and 13). The older form, a digest as the part and a graph in the default graph, is refused, and its factory is gone. The order of decision 13 is kept, each import created and then the description replaced once.

## What changed

- **`Command`.** One `fence` factory, `fence(ws, List<Fenced>)`. `Fenced` is a digest, a label and a job id. The dataset holds the default graph's label and job statements and nothing else. The older factory is removed.
- **`Writer.fence`.** `fenced` refuses a command with a part or a named graph, and any statement beyond each import's label and job. `content` reads the job's one `import.nt` artefact, which must be present, unique, parse as N-Triples and hold a triple. All of it is read before any operation is planned, so a refusal writes nothing.
- **`StudioApi.fence`.** It still reads each job to answer `404`, `409` and `422` as the contract says, and sends only digests, labels and job ids.
- **Contract.** The `fence` row of the command table and the paragraph on what the writer checks.
- **Nothing else.** No worker, browser or HTTP change. The browser suite is not needed, since nothing the browser or the fake service uses changes.

## Tests

Levels are L1 for one function, L2 for the service, the writer and an in-memory store together.

| ID | Test | Given / When / Then | Level | Pass |
|---|---|---|---|---|
| B2d-T1 | `ImportsClosureTest.theContentStoredIsTheJobsArtefactAndNothingACommandCarriesCanReplaceIt` | a finished fence job, and commands built by hand that add a named graph of the import's own name, another named graph, or a part / sent to the writer / `400` and nothing written for each, then the plain command applies and the stored graph is the job's | L2, negative and positive | No step, receipt, or import graph after each refusal, and the stored graph isomorphic to the job's artefact |
| B2d-T2 | `theOlderFormOfAFenceNamingNoJobIsRefusedWithAMessageSayingWhatAFenceNames` | the older form, a digest as the part and a graph | `400` with the message that a fence names its imports by their fence jobs, nothing written | L2, negative | The message and a clean store |
| B2d-T3 | `aJobWhoseArtefactIsAbsentDuplicatedEmptyOrUnparseableRefusesTheCommandAndWritesNothing` | a good job beside a job with no `import.nt`, an empty one, one that is not N-Triples, and two of them / sent to the writer / `400` | L2, negative | Nothing written, the good job's import included |
| B2d-T4 | `ImportsClosureTest` tests B2a-T1 to B2a-T14 as listed in the SVA-B2a pack | unchanged | L2 | Passing, with the bodies listed below |
| B2d-T5 | `ReceiptsTest.aCommandsReceiptIsAbsentWhenItsLastOperationsGuardFailedAndARetryAppliesIt` and `aFenceOfSeveralImportsWhoseDescriptionGuardFailedLeavesNoImportNamedAndARetryHoldsAllOfThem` | an interfered store, a job in it | L2 | Passing |
| B2d-T6 | `WorkspaceCommandsTest.aFencedImportTwoWorkspacesHoldIsOneGraphAndAReleaseLeavesIt` | one digest held by two workspaces, each through its own job | L2 | Passing |

## Tests whose bodies changed, and why

The assertions of each are as they were. Only the set-up changed, since a command no longer carries a graph.

- `ImportsClosureTest.theIrisComeFromTheJobsGraphAndNothingInTheRequestCanSayOtherwise` and `theWriterChecksEachJobItselfWhateverTheServiceChecked`, `aFenceCommandSurvivesTheWireAsTheWriterReadsIt`, `aWorkspaceThatIsReadOnlyForAPrincipalRefusesTheWholeCommand`. `Command.Fenced` has no content argument. In the second, the case of an empty graph now holds a job whose artefact is empty, set up with `Fixture.fenceJob`, and is still `400`.
- `ReceiptsTest.aFenceOfSeveralImportsWhoseDescriptionGuardFailedLeavesNoImportNamedAndARetryHoldsAllOfThem`. Each job gets an `import.nt`, and the test compares the stored graph with the graph it wrote into the job.
- `ReceiptsTest.aCommandsReceiptIsAbsentWhenItsLastOperationsGuardFailedAndARetryAppliesIt` and `WorkspaceCommandsTest.aFencedImportTwoWorkspacesHoldIsOneGraphAndAReleaseLeavesIt`. They used the older form to hold an import. Each now writes a finished fence job first, with `Fixture.fenceJob`, and sends the new form. In the first, the job is written before the interference is armed, since the interfering store acts on the first write after it.

## The one command

From `platform/`, `mise exec -- mvn -q -o -pl config-studio-core,config-studio-service,config-studio-writer -am test`. The wider check is `mise run check:config-studio` from the repository root.

## Artefacts to inspect

- `platform/config-studio-core/src/main/java/org/nebularis/lattice/studio/writes/Writer.java`, `fence`, `fenced` and `content`.
- `platform/config-studio-core/src/main/java/org/nebularis/lattice/studio/writes/Command.java`, `Fenced` and `fence`.
- `contracts/config-studio/README.md`, the `fence` row of the command table and the paragraph after it.

## Deliberate non-coverage

- **The digest is not recomputed.** The writer now stores what the job holds under the digest, and the job is the worker's, which may set `cst:digest` and the artefact through `job-update` (`WORKER_PREDICATES`). Nothing in the studio's Java modules computes an RDFC-1.0 canonicalisation. Jena 6.2.0 has none, and the dependency tree has no other. Adding one is a new dependency, which this slice does not take. What stays open is that a worker, or a client of the broker that can write a `job-update`, could still hold an artefact under a digest it does not have. What would close it is an RDFC-1.0 implementation in the writer's classpath, with a test that its digest of a real fence job's artefact equals the Python worker's `mork_rdf.digest`, or a check by the worker side that signs its jobs.
- The compose stack, and a broker client's other commands, such as a `job-update` with its own content, are outside this slice.
- The browser suite, since nothing it uses changes.

## Results

Run on 2026-11-16 in autonomous mode.

- From `platform/`, the one command passed. The surefire reports total core 24, service 207 and writer 10 tests, with no failure and no error. Before the slice they were 24, 204 and 10, so the three new tests are the difference.
- The break. The writer's refusal of a command that carries a part or a named graph was disabled, and `ImportsClosureTest` was run alone, 17 tests with 2 failures. `theContentStoredIsTheJobsArtefactAndNothingACommandCarriesCanReplaceIt` expected `400` and got `200`, and `theOlderFormOfAFenceNamingNoJobIsRefusedWithAMessageSayingWhatAFenceNames` failed on the message. The writer was restored and the suite run again as above.
- `mise run check:config-studio` exited 0. The pytest run passed 284, the Maven `verify` exited 0 and printed no test summary under `-q`, and the browser unit run passed 365 in 22 files. The output is in the session's scratchpad. The check rewrote `ontology/mork/mtp/data/pins.lock.json`, which this slice does not own, and it is left for the maintainer to restore.
