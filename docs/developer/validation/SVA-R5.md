<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: SVA-R5, the run protocol's failure cases on a real stack

**Unit:** [`studio-visual-authoring`](../status/studio-visual-authoring.md), slice SVA-R5, with the checks run on 2026-11-17 in autonomous mode.

## Invariant

On a real broker with two service instances, a run's frames reach the submitting tab once and in order through the instance that accepted it, whichever instance that is ([ADR-A154](../../architecture/decisions/ADR-A154-runs-in-the-configuration-studio.md) decisions 2, 4 and 5). A worker that stops does not run a run twice, since the broker's redelivery makes a new worker say it was lost (decision 7). An instance that stops takes its runs with it, and the frames the worker then publishes reach no tab (decisions 4 and 6). A workspace locked during a run hears nothing more, not even the failed frame at the deadline, since access is checked at delivery (decision 3). A tab that was away misses what was sent meanwhile and still learns the run failed, from the service's failed frame at the deadline (decisions 5 and 6). A run no worker takes expires in the broker and ends at its deadline for the tab (decision 6). The message to the worker is not persistent and expires at the deadline, a tab holds at most four runs, and a run answers on the request with the same frames when it is sent with `wait=true` (decisions 6, 9 and 10).

## What changed

- `test/studio-integration/test_runs.py` and `topologies/runs.toml`, the suite and its topology, with the marker `studio_runs` declared in the suite's `conftest.py` and the task `studio:runs` in `mise.toml`.
- The harness, `tools/testing/studio_harness`, gained what the suite needs. A topology declares `run_workers` (the transforms jar, started by the `processes` runner only) and `instances` (service instances on ports of their own, sharing the broker, the store and the broker secret). A `ProcessStudio` gives `client(principal, instance)`, `signal(name, "STOP" | "CONT" | "KILL")`, `start_run_worker`, `start_service`, `wait_service` and `queue_counts`, and continues every process before it stops one, since a stopped process cannot shut itself down. `Client` gained `submit_run` and `run_iri`.
- `tab.Tab` and `tab_events.mjs`, a tab's subscriber, and `settle`, the contract's rule for what a client shows. The helper connects over Web MQTT as the studio's browser does and prints each message. It reads the events key from the session of the service inside its own process and never prints it. Its tests are SH-T11 to SH-T14 in the harness's own tests.
- No production code changed.

## Tests

The suite starts one writer, the Python workers, one run worker and two service instances, with events served. A tab connects with the events key of the first instance, which is the one the broker asks about a browser, and a run may be sent to either. A run is held or ended by stopping, continuing or killing the run worker's process and an instance's, so no hook is added to the worker or the service. The sample is "Policies from XML and JSON", compiled to XSLT and JOLT, and the input is its XML source. `FrameSpy` reads every run frame published to the events exchange through a queue of its own, so a test can say what the worker published whether or not an instance forwarded it.

| ID | Test | Given / When / Then | Level | Pass |
|---|---|---|---|---|
| R5-T1 | `test_r5_t1_a_whole_run_reaches_the_tab_once_and_in_order_through_either_instance` | a warm worker and a subscribed tab, a run sent to the first instance and then one sent to the second | L3 | each time the tab holds every frame once, `seq` 0 to the last in order, ending `succeeded` with `last` on that frame only, and the frames equal those the worker published, so the instance that did not accept the run forwarded no copy |
| R5-T2 | `test_r5_t2_wait_answers_the_frames_a_tab_would_receive` | a run with the tab, and the same input with `wait=true` on the other instance | L3 | `200`, `application/json`, the frames in order ending `succeeded`, equal to what the tab received once the run's IRI, which the report's text names, is replaced |
| R5-T3 | `test_r5_t3_a_worker_that_stops_mid_run_does_not_run_it_twice` | the worker is stopped and holds the run unacknowledged, then it is killed and a new worker started | L3, case 1 | the tab receives one frame, `seq` 0, `last`, `failed`, saying a worker stopped. The events exchange saw that one frame for the run and no other, so nothing ran twice, and the queue is empty |
| R5-T4 | `test_r5_t4_an_instance_that_stops_takes_its_runs_with_it` | the worker is stopped, the run is sent to the first instance, the instance is killed and the worker continued | L3, case 2 | the worker publishes a succeeded run, and over the deadline and the 2 second grace the tab receives nothing, for the run or at all |
| R5-T5 | `test_r5_t5_a_workspace_locked_during_a_run_hears_nothing_more` | a run of the principal `reviewer` is held, the owner locks the workspace, the worker is continued | L3, case 5 | the principal could read before and cannot after, the worker publishes a succeeded run, and over the deadline and the grace the tab receives nothing, so the frames and the failed frame at the deadline were both withheld |
| R5-T6 | `test_r5_t6_a_tab_that_was_away_misses_frames_and_still_learns_the_run_failed` | frame 0 reaches the tab, the tab disconnects, frames 1 and 2 are published, the tab reconnects on a clean session, no last frame comes | L3, case 4 | the tab receives only the failed frame, `seq` 3, at the deadline, saying the run did not finish by it, and `settle` of the frames it holds is `failed` with that message and `seq` 1 and 2 missing |
| R5-T7 | `test_r5_t7_a_run_no_worker_takes_expires` | no run worker, a run with a deadline 5 seconds ahead | L3 | the tab receives the service's failed frame, `seq` 0, at the deadline and nothing else, and the queue is empty, since the broker expired the message |
| R5-T8 | `test_r5_t8_the_message_is_not_persistent_and_expires_at_the_deadline` | no run worker, a run with a deadline 30 seconds ahead, the message read with a `basic_get` and rejected without requeue | L3 | `delivery_mode` is not 2, `expiration` is within 3 seconds of the time to the deadline, the media type is the input's, the headers are exactly `run`, `job`, `kind`, `target` and `deadline` with the values the contract gives, and the body is the input |
| R5-T9 | `test_r5_t9_a_tab_holds_at_most_four_runs` | the worker is stopped, four runs of one tab, the first with a deadline 6 seconds ahead | L3 | the fifth answers `429` with a `Retry-After` of 1 to 7 seconds, and a sixth sent after the first one's deadline is `202` |
| SH-T11 to SH-T14 | the harness's own tests | the topology keys, `queue_counts`, `submit_run` and `run_iri`, and `settle` | L1 | pass, and start nothing |

R5-T6 publishes frames 0 to 2 itself, over AMQP in the worker's shape, since the real worker publishes a run's frames in one burst and the suite cannot stop it between two. It does not stand in for the worker anywhere else.

## Breaks

Each was made in a copy of the sources outside the repository, built there with Maven, run against the stack through `LATTICE_STUDIO_HARNESS_JARS`, and discarded. The repository's sources and its `target` folders were not touched. A build of a changed module took about 7 seconds.

- **The worker ignores the redelivered flag.** In `RunWorker.apply` the test `message.redelivered()` was made `false && message.redelivered()`. R5-T3 failed, since the tab received 8 frames, the whole run, where one failed frame was expected, so the run ran again on the new worker.
- **An instance forwards the frames of runs it does not hold.** In `RunRegistry.handle`, a frame whose run has no entry was sent to a fixed tab through a `TabSink` set in `StudioApi.runs`, and R5-T4 uses that tab's identifier. R5-T4 failed, since the tab received the 8 frames of a run whose accepting instance had stopped, where none were expected.
- **The access check at delivery is skipped.** In `RunRegistry.deliver`, `mayRead.test(...)` was replaced by `true`. R5-T5 failed, since the tab received the 8 frames of a run in a workspace locked against it, where none were expected.

## The one command

`mise exec -- bash -c 'export PATH=$HOME/.local/share/mise/installs/erlang/27.3.4.19/bin:$PATH; python -m pytest test/studio-integration/test_runs.py -q -s -m studio_runs --durations=0'` from the repository root, which is what `mise run studio:runs` runs. It needs the jars built under `platform/*/target` and the staged assets. In an environment where mise has Erlang disabled the path above is how RabbitMQ and the harness's certificate find it. `mise run studio:runs` itself does not find it there, since mise rebuilds its `PATH` and leaves the install out. The harness's own tests are `mise exec -- python -m pytest tools/testing/studio_harness/tests -q`.

## Artefacts to inspect

- `test/studio-integration/test_runs.py`, the docstring of each test.
- `tools/testing/studio_harness/src/lattice_testing_studio_harness/tab_events.mjs` and `tab.py`, a tab's subscriber and `settle`.
- `tools/testing/studio_harness/src/lattice_testing_studio_harness/processes.py`, `start_service`, `start_run_worker`, `signal` and `stop_worker`.
- `platform/config-studio-service/src/main/java/org/nebularis/lattice/studio/runs/RunRegistry.java`, `handle`, `deliver` and `expire`, which the breaks changed.
- `platform/config-studio-transforms/src/main/java/org/nebularis/lattice/studio/transforms/RunWorker.java`, `apply`.

## Deliberate non-coverage

- **A proxy, TLS and a browser as the client.** The tab is a Node subscriber that connects as the browser does and does not verify the harness's own certificate. A browser's origin and certificate checks, a proxy in front of the service and Web MQTT, and the browser's own timers are not run. The client rule is applied by `settle` to the frames a tab received, and the browser's code has its own tests.
- **A real network.** Every process is on loopback. Loss between the relay and the tab is made by a tab that is away, and a slow tab, a dropped packet and the broker's limits are SVA-R0's probes.
- **A limit across instances.** The registry of an instance holds its own runs, so R5-T9 sends all five runs to one instance. A tab that spreads its runs over two instances is not limited to four by either.
- **The events key of a second instance.** The broker asks the first instance about a browser, so a tab reads its key from that instance. Each instance with local sign-in makes a key of its own, and a key read from the second is refused by the broker. This is true of a development stack only, since a deployment with OIDC has no such key.
- **The two interactive and RDF cases.** A `simulate` run and an RDF sample are answered with one failed frame until SVA-P3 and SVA-M3a, so no test sends them.
- **Case 3, the author edits during a run.** It is the browser's, and the browser's tests hold it.

## Faults found

None. Three observations, none of them a fault of the contract. A deadline 5 seconds ahead is accepted. The run IRI appears in the text of the report part, so two runs of one input are equal only once it is replaced, which R5-T2 does. Instances keep separate coordination state and, with local sign-in, separate events keys, as noted above.

## Results

Run on 2026-11-17 in autonomous mode.

- The harness's tests, `mise exec -- python -m pytest tools/testing/studio_harness/tests -q`, passed 43, which includes SH-T11 to SH-T14.
- The one command ran twice and each run ended `9 passed in 135 s`. Both outputs are in the session's scratchpad. The two runs agree to within a second for each test, R5-T1 5.9 s, R5-T2 2.4 s to 2.5 s, R5-T3 5.7 s to 5.9 s, R5-T4 25.3 s to 25.8 s, R5-T5 25.6 s to 26.2 s, R5-T6 12.8 s, R5-T7 8.0 s to 8.1 s, R5-T8 0.5 s and R5-T9 9.6 s to 9.9 s. Four earlier runs of the suite, while it was written, ended with the failures the tests then had and one run of 9 passed, so no test was flaky once it was right.
- The three breaks each failed their test as above.
- The `single`, `pair` and `runs` topologies each passed the smoke scenario of `test_smoke.py`. The `runs` topology first failed it, since it had no worker for the long queue, which publishing needs, so `runs.toml` declares one.
- `mise run studio:runs` ran its `depends` and then failed at the harness's certificate, which needs `erl`, for the reason under the one command. The `depends` task `build:config-studio-assets` rewrote `ontology/mork/mtp/data/pins.lock.json`, which this slice does not touch.
- Every process the runs started was stopped, and `ps` showed none of `rabbitmq`, `beam`, `java` or a worker afterwards.
