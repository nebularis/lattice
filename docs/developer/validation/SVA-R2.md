<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-R2, the service's side of runs

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-R2, with the checks run on 2026-11-16 in autonomous mode.

## Invariant

A run is accepted at once and is recorded in the accepting instance's registry before its request is published, since a worker can answer before the publish call returns, and it is forgotten again if the broker did not take the request. Its frames reach the submitting tab, or the request that waits for them, once and in order through the instance that accepted it, and every other instance ignores them. Each frame is validated against the frame schema before anything else, since the service cannot know it was not forged or altered on the way (PRI-75), and the reader's access to the workspace is checked as the frame is delivered, from the graph as it is then, so a change of access needs no change in the broker. A frame the check refuses is withheld and the run stays pending. A deadline ends a run that did not end itself, with one failed last frame one past the highest `seq` forwarded, and a run of more than 128 frames ends with a failed frame saying the result is too large. A tab holds at most four runs pending. The deadline is computed from a `Clock` the service is given and fired by timers it is given, never from the wall clock directly (PRI-56), and nothing of a run, neither its entry, its timer nor its collected frames, outlives it in the service. This is ADR-A154 decisions 2 to 6, 9 and 10.

## What changed

- **`Topology`.** The two run queues, `lattice.studio.runs.interactive` and `lattice.studio.runs`, with their routing keys, declared as the transforms queue is and not dead-lettered, as `amqp-topology.json` lists them.
- **`RunRegistry`.** A class with no broker and no HTTP, taking a `Clock`, `Timers` and a `mayRead` function. `accept`, `frame`, `cancel`, and the sinks `TabSink` and `Collector`. One lock guards its maps and is held only for a map operation, and each run's entry has a lock of its own, held while one of its frames is checked, sent and counted, so the frames of a run never interleave and frames of different runs do not wait for one another.
- **`POST /api/workspaces/{ws}/runs`.** The route of the contract's Runs section, with the checks on the workspace and the compile job shared with the transform route in `checkCompile`.
- **`JobBus.publishRun`, `RunMessage`, `RabbitJobBus`, `RecordingJobBus`.** The request to the run worker, published on the confirmed channel, not persistent, with `expiration` the time to the deadline.
- **`Relay`.** Split in two. `startRuns` needs a broker alone and hands each event of type `org.nebularis.lattice.studio.run.frame` to the registry. `start` serves tabs as before, returns where a tab's events are published, and leaves run frames to `startRuns`. `StudioMain.plan` decides which start.
- **Where no events are served.** A run with `wait=true` works, and one without answers `400`, since there is no tab to forward to.
- **`/api/status`.** A warning for each run queue no worker consumes, by the same count of consumers.
- **`Cst`.** `cst:Run`, `cst:SampleRun`, `cst:SimulationStep` and `cst:deadline`, which the contract's vocabulary already declares.
- **Nothing else.** No contract, worker or browser change.

## Tests

Levels are L1 for one class, L2 for the API with a recording bus and an in-memory store.

| ID | Test | Given / When / Then | Level | Pass |
|---|---|---|---|---|
| R2-T1 | `RunRegistryTest.framesGoToTheTabAndToACollectorOnceAndInTheOrderGiven` | one run for a tab sink and one for a collector, frames given alternately | L1 | each sink has its frames once and in order, the collector's array is in sequence order, the registry is empty after the last frames |
| R2-T2 | `aFrameOfARunThisInstanceDoesNotHoldIsIgnored` | a frame of another run and text that is not JSON | L1, negative | nothing sent and no access check made |
| R2-T3 | `anInvalidFrameIsDroppedAndNothingIsSentAndTheRunStaysPending` | 22 frames that break the schema, one at a time, including a text of 49,154 bytes in 24,577 characters | L1, negative | nothing sent, the run still pending, and then a text of exactly 49,152 bytes, a whole part and a failed last frame go out |
| R2-T4 | `theFrameAfterThe128thEndsTheRunWithAFailedFrameSayingTheResultIsTooLarge` | 128 frames and one more | L1 | one failed last frame, `seq` 128, whose message says the result is too large, and the run is forgotten |
| R2-T5 | `accessIsCheckedAtDeliveryAndARefusedFrameIsWithheldWhileALaterPermittedOneGoesOut` | access refused for two frames and then granted | L1 | the two frames are withheld, the run stays pending, the later frames go out, and the check names the principal and the workspace the run holds |
| R2-T6 | `aRunsLastFrameIsWithheldToo` | a last frame while access is refused | L1, negative | nothing sent and the run is forgotten |
| R2-T7 | `theDeadlineSendsOneFailedLastFrameOnePastTheHighestForwardedAndForgetsTheRun` | 0, 1 and 4 frames forwarded, then the deadline | L1 | one failed last frame with `seq` 0, 1 and 4, not before the deadline, a late frame ignored |
| R2-T8 | `theDeadlineFramesSeqCountsOnlyWhatWasForwardedAndItIsCheckedForAccessToo` | a withheld frame, and a deadline while access is refused | L1 | `seq` one past the highest forwarded, and nothing sent but the run forgotten when access is refused |
| R2-T9 | `noDeadlineFrameFollowsARunThatEnded` | a run that ended, then time moves | L1 | its timer is gone and no frame follows |
| R2-T10 | `aTabHoldsFourPendingRunsAndTheFifthIsRefusedWithTheSecondsToTheEarliestDeadline` | four runs, a fifth, then one ends or expires | L1 | the fifth is refused with the seconds to the earliest deadline, rounded up, and accepted once one ends |
| R2-T11 | `twoTabsOfOnePrincipalAndTheSameTabOfTwoPrincipalsAreCountedApart` | four runs on a tab | L1 | another tab of the principal and the same tab id of another principal are accepted |
| R2-T12 | `nothingOfARunOutlivesItInTheRegistryOrTheTimers` | runs that end by a last frame, `cancel` and the deadline | L1 | the registry's size and the timers' count return to zero |
| R2-T13 | `aFrameThatBeatsTheAcceptingThreadsReturnStillEndsTheRunWithItsTimerCancelled` | a frame from another thread the moment a run is accepted, 200 times | L1, concurrent | the run ends each time and no timer is left |
| R2-T14 | `framesOfSeveralRunsGivenByManyThreadsArriveInOrderAtEachSink` | 16 runs, 8 threads giving frames of 2 runs each, and a thread that accepts and cancels other runs | L1, concurrent | each run's 100 frames arrive in order, no two threads were inside a sink at once, and the registry is empty |
| R2-T15 | `framesOfOneRunGivenByTwoThreadsNeverInterleaveInsideItsSink` | two threads giving frames of one run | L1, concurrent | the sink was never entered by two threads at once |
| R2-T16 | `theTabSinkPublishesAStructuredCloudEventWhoseDataIsTheFrameAsReceived` | a frame and a deadline | L1 | the event has the contract's eight attributes with the values it states, `data` equal to the frame, the deadline's frame has the service as source and the clock's time |
| R2-T17 | `aCollectorAnswersTheFramesInSequenceOrderTheFirstOfEachNumberAndNotTheDeadlineFrame` | frames out of order and a repeated number, then the deadline | L1 | sequence order, the first of each number kept, and `timedOut` rather than the service's frame |
| R2-T18 | `RunsRouteTest.aSampleRunIsAcceptedAtOnceAndDescribedAsACstRunAndPublishedToItsQueue` | a sample run | L2 | `202`, a `cst:Run` in Turtle with no `Location`, and the message the bus was given, routing key, headers, expiration, content type and body |
| R2-T19 | `aSimulatorStepGoesToTheInteractiveQueueWithADeadlineOf15SecondsAndTakesTrig` | a step for persistence and for surface | L2 | the interactive routing key, 15 seconds, `application/trig` |
| R2-T20 | `aGivenDeadlineSetsTheExpirationAndIsRefusedInThePastOrBeyondTheKindsMaximum` | deadlines inside and outside the range, with an offset and without a zone | L2 | accepted inside the range, `400` outside it, and the expiration is the time to the deadline |
| R2-T21 | `theDeadlineDefaultsFromTheClockSoItMovesWithIt` | the clock moved before a request | L2 | the default deadline is the clock's now plus the kind's default |
| R2-T22 | `aRequestThatIsNotAWellFormedPairTabOrDeadlineIs400AndNothingIsPublished` | 12 bad queries | L2, negative | `400`, nothing published, nothing held |
| R2-T23 | `aWorkspaceOrJobTheWorkspaceDoesNotHoldIs404` | an unknown workspace, an unknown job, a job that is not an id, no job | L2, negative | `404` |
| R2-T24 | `aPrincipalWhoMayNotReadTheWorkspaceGets404AndNothingIsPublishedOrHeld` | a locked workspace and another principal | L2, negative | `404`, nothing published, and the owner is still accepted |
| R2-T25 | `aJobThatIsNotAFinishedCompilationOfTheTargetsPartIs409` | an unfinished job, a job of another part, a validation | L2, negative | `409` |
| R2-T26 | `aMediaTypeTheKindDoesNotTakeIs415AndABodyOver5MiBIs413` | each kind with a media type it does not take, and bodies at and over 5 MiB | L2, negative | `415`, `413`, and the five sample media types accepted |
| R2-T27 | `aFifthPendingRunOfATabIs429WithRetryAfterAndNothingIsPublishedForIt` | four runs and a fifth | L2 | `429` with the seconds to the earliest deadline, nothing published for the fifth, another tab accepted |
| R2-T28 | `aBusThatCannotPublishMakesTheRoute503AndLeavesNothingPending` | a bus that throws, six times | L2, negative | `503` each time, nothing pending, no timer, and the tab's limit not used up |
| R2-T29 | `aServiceWithNoBrokerAnswersRunsWith503` | a service given no registry | L2, negative | the job's checks come first, then `503` |
| R2-T30 | `aGetOrAnotherMethodOnTheRouteIs405` | a `GET` | L2, negative | `405` with `Allow: POST` |
| R2-T31 | `theRunIsRecordedBeforeItIsPublishedSoAFrameFromInsideThePublishCallIsDelivered` | a bus that gives two frames from inside its publish call | L2 | both frames reach the tab and the run ends before the answer |
| R2-T32 | `framesReachTheSubmittingTabAsCloudEventsOnceTheRunIsAccepted` | frames given after the `202` | L2 | the tab's events name the run as subject and carry the frame |
| R2-T33 | `waitTrueAnswersTheFramesInSequenceOrderAs200Json` | frames given out of order from inside the publish call | L2 | `200`, `application/json`, an array in sequence order, nothing sent to a tab |
| R2-T34 | `waitTrueAnswersAFailedLastFrameAs200Too` | a worker's one failed frame | L2 | `200` with that frame |
| R2-T35 | `waitTrueAnswers504WhenTheDeadlinePassesWithNoLastFrameAndForgetsTheRun` | a waiting request, one frame, then the test's clock passes the deadline | L2, concurrent | `504`, and the registry and the timers are empty |
| R2-T36 | `theStatusWarnsOfARunQueueNoWorkerConsumesLikeItDoesOfAJobQueue` | a bus that counts no consumer of the interactive queue | L2 | a warning for that queue alone |
| R2-T37 | `TopologyTest.theConstantsEqualTheContractFile` and `theRunQueuesAreDeclaredLikeTheTransformsQueueAndNeitherIsDeadLettered` | the constants, the contract's file and a recording channel | L1 | the names, routing keys and settings are the contract's and the transforms queue's, and neither run queue is dead-lettered |
| R2-T38 | `LanesTest.theStatusNamesEachQueueNoWorkerConsumesAndToldWhichToStart`, changed | the status of a bus that counts consumers | L2 | one count for each of four queues, and the warnings for the job queues as before |
| R2-T39 | `RunsRouteTest.whereNoEventsAreServedARunWithoutWaitIs400AndNothingIsRecordedOrPublished` | a registry and no events served, a run without `wait` | L2, negative | `400` saying to send `wait=true`, nothing published and no timer |
| R2-T40 | `whereNoEventsAreServedARunWithWaitTrueAnswers200WithItsFrames` | the same service, `wait=true`, a frame from inside publish | L2 | `200` with the frame |
| R2-T41 | `whereNoEventsAreServedARunWithWaitTrueAnswers504AtItsDeadline` | the same, the clock passes the deadline | L2, concurrent | `504` and an empty registry |
| R2-T42 | `StudioMainPlanTest.runsAreReadWheneverThereIsABrokerAndTabsAreServedOnlyWithEventsAndTheirSecret` | each combination of broker, events address and secret | L1 | runs are read with a broker alone, tabs only with all three |

## Tests whose bodies changed, and why

- `LanesTest.theStatusNamesEachQueueNoWorkerConsumesAndToldWhichToStart` expected two counts of consumers, one for each job queue. The status now counts the two run queues too, so it expects four. Its other assertions are as they were.
- `RunsRouteTest.setUp` now states that events are served, since a run without `wait` needs them.
- `Fixture` has a constructor that takes the clock, and its wrapper bus delegates `publishRun`. Nothing a test asserts changed.

## Breaks

Each was made, the tests run, and the file restored.

- **Access at delivery skipped.** `RunRegistry.deliver` was made to treat every principal as allowed. `RunRegistryTest` failed 3 of its 17 tests, `accessIsCheckedAtDeliveryAndARefusedFrameIsWithheldWhileALaterPermittedOneGoesOut`, `aRunsLastFrameIsWithheldToo` and `theDeadlineFramesSeqCountsOnlyWhatWasForwardedAndItIsCheckedForAccessToo`.
- **Publish before record.** In `StudioApi.run` the request was published before `accept` was called. `RunsRouteTest` failed 4 of its 19 tests, `theRunIsRecordedBeforeItIsPublishedSoAFrameFromInsideThePublishCallIsDelivered`, `aFifthPendingRunOfATabIs429WithRetryAfterAndNothingIsPublishedForIt`, and the two `wait=true` tests that take frames from inside the publish call, `waitTrueAnswersTheFramesInSequenceOrderAs200Json` and `waitTrueAnswersAFailedLastFrameAs200Too`, each of which then waited out its 121 seconds.

## The one command

From `platform/`, `mise exec -- mvn -q -o -pl config-studio-core,config-studio-service,config-studio-writer -am test`. The wider check is `mise run check:config-studio` from the repository root.

## Artefacts to inspect

- `platform/config-studio-service/src/main/java/org/nebularis/lattice/studio/runs/RunRegistry.java`, the class comment on its two kinds of lock, `accept`, `frame`, `expire` and `problem`.
- `platform/config-studio-service/src/main/java/org/nebularis/lattice/studio/api/StudioApi.java`, `run` and `checkCompile`.
- `platform/config-studio-service/src/main/java/org/nebularis/lattice/studio/events/Relay.java`, where a run's frame is told from a job's event.
- `contracts/config-studio/README.md`, the Runs section, and `run-frame.schema.json`.

## Deliberate non-coverage

- **Two service instances and a real broker.** That one instance forwards a run's frames and the other ignores them, over a real exchange and a real MQTT connection, is exercised by SVA-R5 on the real stack. Here the registry is given frames directly, and what the relay does with a broker message is not run.
- **The message's persistence.** `RabbitJobBus.publishRun` sets delivery mode 1 and the expiration, which `RecordingJobBus` cannot show. SVA-R5 reads them from the broker.
- **The run worker.** It is SVA-R3.
- **A client that closes a waiting request early.** The service does not notice it. The run ends at its deadline and is forgotten, and the request's thread ends with it.
- **A schema validator.** The registry checks the frame by code that restates `run-frame.schema.json`, since the service has no JSON Schema library and takes none. R2-T3 holds the cases, and a change to the schema needs a change to `RunRegistry.problem`.

## Results

Run on 2026-11-16 in autonomous mode.

- From `platform/`, the one command passed. The surefire reports total core 24, service 244 and writer 10 tests, with no failure and no error. Before the slice they were 24, 207 and 10, so the 37 new tests are the difference, 17 in `RunRegistryTest`, 19 in `RunsRouteTest` and 1 in `TopologyTest`.
- The first break, access at delivery skipped, failed 3 of the 17 tests of `RunRegistryTest`, and `RunsRouteTest` passed since its principal is always allowed there. The second break, publish before record, failed 4 of the 19 tests of `RunsRouteTest`, as listed above, and the run took 245 seconds since two tests then waited out a deadline. Both files were restored and the one command passed again afterwards.
- `mise run check:config-studio` exited 0. The pytest run passed 286, the Maven `verify` exited 0 and printed no test summary under `-q`, and the browser unit run passed 433 in 25 files. The Maven output holds the logged errors of R2-T28, which the test provokes on purpose, and the logged warnings of R2-T3. The output is in the session's scratchpad. The check rewrote `ontology/mork/mtp/data/pins.lock.json`, which this slice does not touch.
- After a fault found in review, the registry is wired whenever there is a broker and not only where events are served, with 4 more tests, R2-T39 to R2-T42. The totals and the check are repeated below.
- Both mermaid diagrams of `docs/architecture/configuration-studio.md` still render.
