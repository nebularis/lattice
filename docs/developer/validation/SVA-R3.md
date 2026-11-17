<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-R3, the run worker

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-R3, with the checks run on 2026-11-17 in autonomous mode.

## Invariant

One execution core serves the deprecated transform route and a run. It reads the compile job, checks it, runs each scheme's transform and attributes what it wrote to mappings, and gives a plain result, which the transform route tells as its Turtle reply, byte for byte as before, and a run tells as frames. A run's result reaches the events exchange as frames that each satisfy `run-frame.schema.json`, a report part first and then one artefact part for each mapping in order of group and path, each part cut into frames of at most 49,152 bytes as UTF-8 and only between characters, and never more than 128 frames, since a result that needs more is one failed frame. The frames are published in order on one confirmed channel and the message is acknowledged only after that. A request is checked before anything is done (PRI-75), and one that fails is rejected without requeue. A run the broker redelivers is failed and never run again, a run whose deadline has passed is acknowledged and dropped without a frame, and an execution still running at its deadline is interrupted and nothing more is published for it. Each queue has a channel, a prefetch and a pool of threads of its own, so a sample run held open never delays a simulator step. The deadline and the frames' times come from a `Clock` the worker is given and the frames are a function of the compile job and the sample alone, so a repeat or a permutation of the job's artefacts gives the same frames (PRI-56, PRI-58). This is ADR-A154 decisions 1, 3, 6, 7, 9 and 12.

## What changed

- **`TransformRun`.** `execute` is the core and gives a `Result`, the findings and the outputs in the order they were found and a failure when the run could not finish. `run` tells it as the Turtle reply as before. The outputs are available in canonical order, by group and then by path. The report of a run is written as Turtle statement by statement in a fixed order, since a Turtle writer orders subjects by how nodes hash, which gave another order for another run IRI.
- **`RunFrames`.** The result as frames, the cut between characters, the limit of 128 frames and the one failed frame.
- **`RunWorker`.** The check of a run message, the redelivered, expired, RDF sample and `simulate` cases, and the execution on a thread of its own with a timeout taken from the deadline and the `Clock`.
- **`QueueWorker`.** One queue's pool of threads. A message is acknowledged or rejected after its handler returned, holding the channel's monitor.
- **`AmqpFrameSink`.** Publishes each frame as a CloudEvent in the AMQP binding's binary mode with `RabbitMqEventPublisher`, the publisher the store writer uses, on a channel in confirm mode, and waits for the confirms of a run's frames before the message is acknowledged. Every publish and confirm holds one lock.
- **`LegacyTransforms`.** The transform route's request and reply, moved out of `TransformsMain` and answered through the same core.
- **`TransformsMain`.** Three queues, each with a channel, a prefetch and a pool of its own, and the settings `LATTICE_RUNS_INTERACTIVE_CONCURRENCY` and `LATTICE_RUNS_CONCURRENCY`, each 2 unless set.
- **`bindTo`.** Each queue of `amqp-topology.json` and its copy in `workers` names the exchange it is bound to, and `declare_topology` follows it. Before, it bound every queue that is not dead-lettered to the dead-letter exchange, which is right only for `lattice.studio.dead` and put the transforms queue and the two run queues there too. The Java `Topology` already bound them to `lattice.studio` alone.
- **Documents.** The operations guide, the worker's README and the contract's description of the topology file.

## Tests

Levels are L1 for one class and L2 for the consumer with a publisher and a channel faked in memory and a clock the test sets, at 2026-11-17T10:00:00Z.

| ID | Test | Given / When / Then | Level | Pass |
|---|---|---|---|---|
| R3-T1 | `RunFramesTest.aSampleRunIsTheReportThenOneArtefactForEachMappingInCanonicalOrderAndEachTextIsWhatTheTransformRouteReplies` | the `policies` example's compile job and its XML sample | L1 | the report first as Turtle that parses, then one artefact part for each mapping in order of group, each with the legacy reply's path and content for the same input, `step` 0, `seq` and `index` contiguous, and a last frame that succeeded and conforms |
| R3-T2 | `aPartLongerThanAFrameIsCutBetweenCharactersAndTheFramesJoinToTheExactText` | texts of 3- and 4-byte characters with the frame boundary at each offset of a character, and a part of 40,000 and 20,000 such characters | L1 | no piece is over 49,152 bytes, the pieces join to the exact text with no replacement character, `more` is true on every frame of a part but its last and `part` is on its first frame only |
| R3-T3 | `aResultOfMoreThan128FramesIsOneFailedFrameAndOneOf128IsSent` | results of 126, 127 and 200 outputs | L1 | 126 outputs are 128 frames and succeed, 127 and 200 are one failed frame with `seq` 0 whose message says the result is too large and to narrow what is run |
| R3-T4 | `theSameRunTwiceAndTheSameJobInAnotherOrderGiveTheSameFrames` | the same request twice, and the job's artefacts added in reverse order, for an XML and a JSON sample | L1 | the frames are equal |
| R3-T5 | `aFailedResultIsOneFailedFrame` | a result that failed | L1 | one frame, `seq` 0, `last` true, `failed`, with the message |
| R3-T6 | `theSchemaCheckRefusesWhatTheSchemaRefusesAndAcceptsTheContractsExample` | the contract's complete example, and eight frames each broken in one way, an extra property, a role, a status on a frame that is not last, `seq` 129, a run IRI, a failed frame with `conforms`, `more` on a last frame and a text of 49,155 bytes in 16,385 characters | L1, negative | the example passes, each broken frame is refused and a gap in `seq` is refused |
| R3-T7 | `RunWorkerTest.aSampleRunPublishesItsFramesAndIsAcknowledgedAfterThem` | a sample run with a publisher that takes 100 milliseconds | L2 | the log is the publish and then the acknowledgement, and the last frame succeeded |
| R3-T8 | `aRedeliveredRunIsNotRunButFailedAndAcknowledged` | a redelivered sample run | L2 | one failed frame saying a worker stopped and to run it again, acknowledged after it, and the compile job never read |
| R3-T9 | `anExpiredRunIsAcknowledgedAndDroppedWithoutAFrame` | a deadline one second ago and a deadline that is now | L2 | acknowledged, no frame and no compile job read |
| R3-T10 | `aMessageThatFailsItsChecksIsRejectedWithoutRequeueAndNothingIsRun` | each of the five headers missing, a run IRI, a job IRI, three pairs of kind and target that are not allowed or not carried by the queue, and two deadlines without a zone | L2, negative | each is rejected without requeue, and nothing is published, acknowledged or read |
| R3-T11 | `aRunPastItsDeadlineIsStoppedNothingMoreIsPublishedAndItIsAcknowledged` | an execution held open until interrupted and a deadline 300 milliseconds off | L2 | acknowledged with no frame, and the execution saw the interrupt |
| R3-T12 | `anRdfSampleAndASimulationEachGiveTheirOneFailedFrame` | a Turtle sample, an N-Triples sample with a parameter and a `simulate` run | L2 | one failed frame each that names SVA-M3a or SVA-P3, acknowledged, nothing run |
| R3-T13 | `aRunThatCannotStartIsOneFailedFrameForEachReason` | a compile job the store cannot read, one that is not a finished compilation of the mapping part, an unparseable sample, a media type no sample has and a sample over 5 MiB | L2 | one failed frame each, with the reason in plain words |
| R3-T14 | `aFailedPublishIsNotAcknowledgedButRequeuedSoTheNextWorkerSaysItWasLost` | a publisher that throws | L2, negative | the message is requeued, not acknowledged |
| R3-T15 | `twoInteractiveRunsAndTwoSampleRunsAtOnceKeepEachRunsFramesInOrderAndASampleRunHeldOpenNeverDelaysAStep` | two sample runs held open in the store read, then two `simulate` runs | L2 | the two steps are published and acknowledged while the sample runs are held, then each sample run's frames are in order, equal to the other's once the run IRI is the same, and each acknowledgement follows its run's publish |
| R3-T16 | `theTransformsRouteAnswersAsItDidThroughTheSharedExecution` | a transform request with a reply queue, and one without | L2 | the reply is the Turtle of `TransformRun.run` on the reply queue with the correlation id, and a request without a reply queue is dropped |
| R3-T17 | `theConcurrencyOfARunQueueIsASettingFromOneUpAndDefaultsToTwo` | no setting, ` 3 `, and `0`, `-1`, `two` and `1.5` | L1 | 2, 3, and the others refused |
| R3-T18 | `aFrameIsPublishedToTheEventsExchangeAsABinaryModeCloudEventAndConfirmed` | two frames given to `AmqpFrameSink` on a recording channel | L2 | the exchange is declared, the channel put in confirm mode, two publishes follow and then the wait for confirms, the routing key and the `cloudEvents:type` are the frame type, the subject is the run, the source is this worker, the ids differ, the time is the clock's and the body is the frame |
| R3-T19 | `TransformRunTest` | unchanged | L1 | passes as it was, so the legacy reply is as before |
| R3-T20 | `test_each_queue_is_bound_to_the_exchange_its_field_names_and_to_no_other` in `workers/tests/test_config_studio_worker.py` | the packaged topology declared on a recording channel | L1 | each queue has one binding, to the exchange its `bindTo` names, and only `lattice.studio.dead` is bound to the dead-letter exchange |
| R3-T21 | `test_only_a_dead_lettered_queue_names_the_dead_letter_exchange_as_an_argument` | the same | L1 | only the two job queues carry `x-dead-letter-exchange` |

Every frame the consumer tests publish is checked against the schema after each test, so any test that publishes is also a check of its frames.

## Tests whose bodies changed, and why

- `tools/test_config_studio_contract.py`, `test_the_two_run_queues_sit_in_the_topology_with_the_transforms_queues_settings`, compared each run queue's whole entry with an entry of three fields. The entry has a fourth, `bindTo`, so the expected entry names it, taken from the transforms queue.
- `TopologyTest` is unchanged. It finds each field of the contract file by its text and a queue's `deadLetter` inside the text between two queue names, so a field added after `deadLetter` does not disturb it. It passes.

## Breaks

Each was made, the tests run, and the file restored.

- **A part cut at a fixed byte count.** In `RunFrames.cut` the loop that moves a cut back to the start of a character was removed. `RunFramesTest` failed 1 of its 6 tests, `aPartLongerThanAFrameIsCutBetweenCharactersAndTheFramesJoinToTheExactText`, at `pad 0`, where the boundary falls inside a 4-byte character.
- **Acknowledge before publishing.** In `QueueWorker.deliver` the acknowledgement was made before the handler ran. `RunWorkerTest` failed 6 of its 12 tests, among them `aSampleRunPublishesItsFramesAndIsAcknowledgedAfterThem`, whose log was the acknowledgement alone where the publish and then the acknowledgement were expected, `aRedeliveredRunIsNotRunButFailedAndAcknowledged`, `aFailedPublishIsNotAcknowledgedButRequeuedSoTheNextWorkerSaysItWasLost`, which saw an acknowledgement where it expected a requeue, and the concurrency test.

## The one command

From `platform/`, `mise exec -- mvn -q -o -pl config-studio-transforms,config-studio-core,config-studio-service,config-studio-writer -am test`. The Python tests are `mise exec -- python -m pytest workers/tests -q -k config_studio`. The wider check is `mise run check:config-studio` from the repository root.

## Artefacts to inspect

- `platform/config-studio-transforms/src/main/java/org/nebularis/lattice/studio/transforms/RunWorker.java`, the class comment on what an interrupt does, and `apply`.
- `platform/config-studio-transforms/src/main/java/org/nebularis/lattice/studio/transforms/RunFrames.java`, `cut` and `of`.
- `platform/config-studio-transforms/src/main/java/org/nebularis/lattice/studio/transforms/AmqpFrameSink.java` and `QueueWorker.java`, the two comments on how a channel is kept safe.
- `platform/config-studio-transforms/src/test/java/org/nebularis/lattice/studio/transforms/SchemaCheck.java`, the interpreter of the schema file.
- `contracts/config-studio/amqp-topology.json` and `contracts/config-studio/run-frame.schema.json`.

## Deliberate non-coverage

- **A real broker and two service instances.** That the frames reach the exchange, that publisher confirms hold on a real channel and that a tab receives them through the instance that accepted the run is SVA-R5 on the real stack. Here the channel is a recording proxy and the publisher a fake.
- **RDF samples.** They are answered with one failed frame. Running them is SVA-M3a.
- **Simulations.** A `simulate` run is answered with one failed frame. Running them is SVA-P3.
- **An engine that honours an interrupt.** Neither Saxon-HE's XSLT processing nor JOLT is known to poll the interrupt flag, and this slice did not measure it. R3-T11 holds an execution that does honour it. One that does not is abandoned on its daemon thread, so the message is acknowledged and nothing more is published at the deadline, and the thread runs until the engine returns.
- **A JSON Schema library.** None is on the module's test classpath, so `SchemaCheck` reads the schema file and interprets the keywords it uses and refuses any it does not know. The service's `RunRegistry.problem` is in another module, so the frames were not run through it, and R3-T6 holds the cases of the schema.
- **Live `Clock` use.** The consumer takes the clock it is given. The real worker is given the system clock in `TransformsMain`, which the tests do not run.

## Results

Run on 2026-11-17 in autonomous mode.

- From `platform/`, the one command exited 0. The surefire reports total core 24, service 248, writer 10 and transforms 20 tests, with no failure and no error. Before the slice the first three were 24, 248 and 10 and the transforms module had 2, so the 18 new tests are the difference, 6 in `RunFramesTest` and 12 in `RunWorkerTest`.
- `mise exec -- python -m pytest workers/tests -q -k config_studio` ended `154 passed, 75 deselected`, which includes R3-T20 and R3-T21.
- The two breaks failed as above and both files were restored and compared with the originals. The first attempt at the second break did not compile, and its silence was not read as a pass. It was made again so that it compiled.
- `mise run check:config-studio` exited 0. The pytest run passed 288, which is the 286 of before and R3-T20 and R3-T21. The Maven `verify` exited 0 and printed no test summary under `-q`. Its output holds logged errors and warnings that tests provoke on purpose, among them the `RunsRouteTest` errors on the run worker handing, the `RunRegistryTest` warnings of dropped frames and the two exceptions R3-T13 and R3-T14 provoke. The browser unit run passed 433 in 25 files. The authoring domain's run passed 21. The output is in the session's scratchpad. The check rewrote `ontology/mork/mtp/data/pins.lock.json`, which this slice does not touch.
- A test was found flaky on first writing, R3-T15 asserting that an acknowledgement directly follows a publish in a log that two pools write to at once. It now asserts that each run's publish comes before its acknowledgement, and ran 5 times clean.
