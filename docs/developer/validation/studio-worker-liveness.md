<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: studio-worker-liveness WL-1 to WL-7

**Plan:** [studio-worker-liveness](../plans/studio-worker-liveness.md)
**Status record:** [studio-worker-liveness](../status/studio-worker-liveness.md)

One pack for the unit, each slice a section.

## Invariant

A job the worker has accepted ends in the store as `Succeeded` or `Failed`, however long it runs and whatever happens to the worker's connection, and a job that cannot finish never stops the jobs behind it (MEC-95, STD-298, plan root causes RC1 to RC7).

## Commands

```bash
mise run check:config-studio
mise run studio:liveness
mise run test:config-studio-browser
```

The first runs the unit tests of the worker, the harness and the service. The second starts a studio on a broker whose heartbeat is two seconds and drives the worker through a long job, a lost job and a message it cannot read, in about three and a half minutes. The third runs the studio's browser suites. A pass is exit status 0. `studio:liveness` needs the jars under `platform/*/target`, which `mise run studio:up` builds, and Erlang on the path.

## WL-1: reproductions that fail today

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| WL1-01 | a worker on a broker with a 2 s heartbeat, patched so each job first sleeps 10 s / a validation is submitted / the job reaches `Succeeded`, the broker logs no missed heartbeat and the worker still runs | L5 | + | fails on `main` as built, 2026-11-05: the job is never finished and the worker has exited |
| WL1-02 | a worker that dies two seconds after it marked a job running / a second worker starts / the job ends `Failed` with a message saying the worker stopped, and is not run | L5 | − | fails on `main` as built: the second worker runs it again and writes `Succeeded` |
| WL1-03 | a `cst:Refresh` job naming no workspace at the head of the queue / a worker starts and a validation is submitted / the validation finishes and the worker still runs | L5 | − | fails on `main` as built: the worker exits at the first message, and the validation waits without end |
| WL1-04 | a workspace whose validations never finish / the author leaves the workspace and returns / no validation is submitted again | L6 | − | expected failure on `main` as built (`test.fail()`): 2 validations at the first mount, 4 after the return |

`test/studio-integration/test_worker_liveness.py` (WL1-01 to WL1-03, marker `studio_liveness`) and `apps/config-studio/e2e/studio.spec.ts` (WL1-04). The harness gained `start_worker`, `stop_worker`, `purge`, `log`, `broker_log` and `amqp_uri` so a test can start a worker of its own, patched by a program the test supplies, and the worker's code is untouched.

**A worker's idle memory**, measured on a Linux machine with 4 cores, Python 3.14, one worker started by the harness: 62 MB idle, 66 MB after a vocabulary validation, 104 MB after a validation of the ODRL mapping sample and 130 MB after its compilation. A second worker for long jobs (WL-Q3) costs about that much again, 60 MB at rest and up to 130 MB after a mapping compile.

**Not covered.** The conclusion that the first incident's job was a proposal: the store was not available, so WL-1 does not confirm the job's kind. Each later slice turns one of these tests green, and a test turned green is not weakened.

## WL-2: the job on its own thread

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| WL2-01 | a job that waits / delivered / it runs on a thread named `job`, the connection thread's `process` goes on being called, and nothing is acknowledged until the job ends | L1 | + | pass |
| WL2-02 | a job that publishes its result / run / the publish is made on the connection thread and the acknowledgement follows it | L1 | + | pass |
| WL2-03 | a message that is not a job, or a job the worker refuses / delivered / rejected without requeue, the next served, and a refused job is not marked failed | L1 | − | pass, 3 cases |
| WL2-04 | a job that raises / run / marked failed, rejected without requeue, the next served and the consumer alive | L1 | − | pass |
| WL2-05 | stop requested with a job in hand / the job ends / no other message taken and the process ends after the job's acknowledgement | L1 | + | pass |
| WL2-06 | a broker that refuses connections / tried / backoff of 1, 2 and 5 s, then served | L1 | − | pass |
| WL1-01 | the real-broker test of WL-1 | L5 | + | pass, 2026-11-05 (was failing) |
| WL1-03 | the real-broker test of the unknown kind | L5 | − | pass, 2026-11-05 (was failing). The worker refuses the message, which is dead-lettered |

`workers/tests/test_config_studio_consumer.py` (11 cases, with the two of WL-4) and `test/studio-integration/test_worker_liveness.py`.

**Retired.** `test_acks_after_final_write_and_requeues_on_store_error` asserted that a store error requeues the job and ends the worker, which is RC2. The consumer replaces it: a job that cannot be run is marked failed where it can be and rejected without requeue (WL2-04). `test_malformed_message_is_nacked_without_requeue` is now `test_a_malformed_message_is_not_a_job` for the parsing and WL2-03 for the rejection. Neither is weakened. Each asserts what the adapter it tested promised, and that adapter, `RabbitMqConfigStudioWorker`, is gone.

**Not covered.** A heartbeat interval longer than the poll interval of 0.25 s is assumed. The poll is the longest the connection thread is away from the broker, and a job thread's call waits for it.

## WL-3: the check on delivery

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| WL3-01 | a job the store holds as `Succeeded` or `Failed` / delivered / left as it is, with no write | L1 | − | pass, 2 cases |
| WL3-02 | a job the store holds as `Running` / delivered / one write, `Failed` with a message saying the worker stopped, what the service wrote kept, no report, and the job not run | L1 | − | pass |
| WL3-03 | a queued job / delivered / run to `Succeeded` | L1 | + | pass |
| WL3-04 | a job naming no workspace that is not a rebuild, of the retired kind or a current one / delivered / refused as `InvalidMessage`, nothing written | L1 | − | pass, 2 cases |
| WL3-05 | a rebuild job naming no workspace / delivered / run | L1 | + | pass |
| WL3-06 | an unfinished job / `fail` / `Failed` and the message. A finished one is not written again | L1 | ± | pass |
| WL3-07 | a job / run / its start is logged with its kind, target and IRI, and the consumer logs its end with the duration and what became of it | L1 | + | pass, 2 cases |
| WL1-02 | the real-broker test of WL-1 | L5 | − | pass, 2026-11-05 (was failing). A second worker finds the job running and writes `Failed` |

`workers/tests/test_config_studio_worker.py` and `test_config_studio_consumer.py`, and `test/studio-integration/test_worker_liveness.py`, which now passes all three of its cases in 43 s.

**Changed, not weakened.** `test_same_job_twice_gives_same_graph` ran `handle` twice on one job, and a job the store holds as finished is not run again, so the second run would have compared the first with itself. It now sets the job back to the graph the service wrote before the second run, which keeps what it protects, that one job gives one graph.

**Not covered.** Two workers on one queue where a lost connection redelivers a job to the idle one while the first still runs it. The idle worker marks the job `Failed`, and the first worker's result, published later, replaces that with `Succeeded`. If the first worker's result is applied before the other's `Failed`, the job reads `Failed` though it succeeded. The window is the time between the idle worker's read and its write, and a rerun is the author's to ask. WL-5 gives each lane one worker by default, and a second worker on a lane is the operator's choice.

## WL-4: the held result and the reconnection

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| WL4-01 | a job in hand / the connection is lost and the broker delivers the message again / the job is not started a second time, and its acknowledgement goes on the new tag | L1 | + | pass |
| WL4-02 | a job that finishes while the broker is unreachable / the connection is lost / no tag from the lost connection is used, and when the broker delivers the message again the worker finds the job finished and acknowledges it | L1 | + | pass |
| WL4-03 | a result published while the connection is down / the next connection opens / it is published once, on the connection thread, and the job is then acknowledged | L1 | + | pass |
| WL4-04 | a worker started when the broker is not reachable / it is tried again / after 1, 2 and 5 s, then served (opened as WL2-06) | L1 | − | pass |
| WL4-05 | a worker on a real broker, and a job of eight seconds / the broker closes the worker's connection at three / the worker reconnects, the message is delivered again and taken for the job in hand, the job ends `Succeeded`, and its start is logged once | L5 | + | pass, 2026-11-05, in 30 s |

`workers/tests/test_config_studio_consumer.py` and `test/studio-integration/test_worker_liveness.py` (4 cases, about 55 s). The worker's connection is named `config-studio-worker {queue}`, as the Java components name theirs, so the broker's tools can find it, and the harness's `close_connections` closes it through `rabbitmqctl`.

**Not covered.** A result that could not be published because the broker refused or could not route it, which is a fault of the topology and not of the connection. The job is then marked failed where it can be and rejected, as for any job that cannot be written (WL2-04). A worker killed with its result in hand has no result to keep, and the job is found running at the next delivery and failed (WL1-02).

## WL-5: short jobs past long ones

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| WL5-01 | a proposal by a language model, by a mapping proposal, and a publication / `Lanes.isLong` / long | L1 | + | pass |
| WL5-02 | a validation, a compilation, a sentence-form proposal, an ODRL import, a rebuild and an assembly / `Lanes.isLong` / short | L1 | − | pass |
| WL5-03 | the service / a validation, a proposal by a language model and a sentence-form proposal are submitted / the proposal alone is published to the long queue | L3 | ± | pass |
| WL5-04 | the contract `amqp-topology.json` / compared with the Java constants and the worker's packaged copy / equal, and the long queue dead-letters like the short one | L3 | + | pass |
| WL5-05 | a studio with a worker for each queue, the long one patched to take 25 s per job / a proposal is submitted, then a validation / the validation ends `Succeeded` in under 15 s while the proposal is still unfinished, and the proposal ends later | L5 | + | pass, 2026-11-05 |
| WL5-06 | the harness's two shipped topologies, now with a worker for the long queue / each starts, runs the smoke scenario (which publishes) and stops / nothing left behind | L5 | + | pass, 2 in 50 s |

`platform/config-studio-service` `LanesTest` (4) and `TopologyTest`, `workers/tests/test_config_studio_worker.py::test_topology_copy_equals_contract`, `test/studio-integration/test_worker_liveness.py` (now 5 cases, 95 s) and `test_smoke.py`.

**What is long.** A proposal by a language model (`language-model`, `mapping-language-model`) and a publication. The list is `Lanes` in the service and nowhere else, since a worker runs whatever its queue gives it. A job of another kind that turns out to be long moves by one edit there.

**The topology may be split further later**, as the maintainer said. Nothing here assumes two queues: a queue is a name in the contract, a routing key in `Lanes` and a worker started with `LATTICE_WORKER_QUEUE`.

**Existing brokers.** The service and the worker declare the long queue when they start, as they do the others, so a broker that has none gets it. A `lattice.studio.jobs` that holds jobs from before keeps them, and the short worker runs them whatever their kind. A broker that has no worker on the long queue holds the long jobs, which WL-7 makes visible.

**Not covered.** Docker Compose: the generated compose file has a service for the long worker (`tools/testing/studio_harness` unit test) but the run in containers was not made. `docker` has no daemon here.

## WL-6: a view that attaches to its job

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| WL6-01 | a workspace with queued, running and finished jobs of several kinds / the unfinished listing is read / the queued and running ones with kind, target and start, and no finished one and no input | L3 | ± | pass |
| WL6-02 | a wait on a job / its signal aborts / the wait ends with an AbortError within 300 ms and the job is read no more. A signal already aborted ends at once. A job that finishes is returned | L1 | ± | pass, 3 cases |
| WL6-03 | a workspace whose validations never finish / the author leaves it / its jobs leave the store, and on return as many are open as before | L6 | + | pass |
| WL6-04 | a proposal by a language model running when the author leaves the workspace / they return / the view shows it running, submits nothing, and applies its proposals when it ends | L6 | + | pass |
| WL6-05 | adversarial: the attach disabled in the meaning view, and the abort disabled in the validation hook / the same two tests / each fails (the propose button is enabled again, and 2 validations are left open instead of 0) | L6 | − | probed 2026-11-05, restored |
| WL6-06 | a job whose graph the store no longer holds / delivered to the worker / acknowledged with nothing written, and not sent to the dead-letter queue | L1 | − | pass |

`platform/config-studio-service` `LanesTest`, `apps/config-studio/src/jobs.test.ts`, `apps/config-studio/e2e/studio.spec.ts` (22 cases with the two new) and `workers/tests/test_config_studio_worker.py`. The unit tests of the app are 118, and the browser suite on the fake service 22.

**What attaches.** The views that start a job of minutes: the meaning view's proposals, the mapping view's proposal by a model, and the publication view. Each reads the workspace's unfinished jobs when it opens and waits for the one of its kind as for one it had just submitted. Validations are not attached to. A validation still queued when its view goes is deleted, and one that is running is deleted as well, since nobody reads its result. The worker then finds a queued one gone, which is no longer a dead letter but an acknowledgement (WL6-06). The writer refuses the result of a running one and logs a refusal.

**The dead-letter noise the plan asked about.** Before this slice a deleted queued validation reached `lattice.studio.dead` as `job graph not found`, one message per validation the author's view dropped. It is now acknowledged and logged at info.

**Not covered.** The compile view already reads the job it selected and the workspace's compile jobs from the store, and is unchanged. The publication view's attach is not driven by a browser test, since the fake service does not hold publish jobs. The mapping proposal's attach is the meaning view's, repeated, and has no test of its own.
