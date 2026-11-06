<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# The studio worker stays alive through a long job: status

**Unit ID:** `studio-worker-liveness`
**Plan:** [studio-worker-liveness.md](../plans/studio-worker-liveness.md)
**Mode:** default. Write, then hand off.
**Status:** built 2026-11-06. WL-Q1 to WL-Q6 are answered.

## Position

| Slice | Deliverable | State | Blocked on |
|---|---|---|---|
| WL-0 | the plan, this record, the board | built 2026-11-05 |  |
| WL-1 | reproductions that fail today, the view's fate on remount, a worker's idle memory | built 2026-11-05 |  |
| WL-2 | the job on its own thread, the publisher and acknowledgement across threads | built 2026-11-05 |  |
| WL-3 | the check on delivery, a job that cannot run marked `Failed`, each job logged | built 2026-11-05 |  |
| WL-4 | the held result, reconnecting with a backoff | built 2026-11-05 |  |
| WL-5 | short jobs past long ones | built 2026-11-05 |  |
| WL-6 | a view that attaches to its running job, no stacked validations | built 2026-11-05 |  |
| WL-7 | the status warning, `studio:status`, the operations guide, the ADR addendum | built 2026-11-05 |  |
| WL-8 | a run that leaves no process behind when its test process is killed | built 2026-11-06 |  |

## Next action

The maintainer verifies the unit and merges it. The Validation Pack is [studio-worker-liveness](../validation/studio-worker-liveness.md).

## History

- 2026-11-05: planned from two investigations. An independent run reproduced a crash on an upgrade from a message of the retired `cst:Refresh` kind. The logs of the run that prompted TD-141 show that error nowhere, and show instead three disconnections for missed heartbeats, each while the same job ran, the first 2 min 40 s into it. The plan's root causes cover both. Which kind that job was is inferred from the graphs it read and the maintainer's recollection of a proposal in progress, and the store was not started to confirm it.
- 2026-11-05: learned, for a register once one owns it. Pika's `BlockingConnection` services heartbeats only while its own thread is inside the library, so a callback that holds the thread past the broker's timeout loses the connection, and the failure appears only at the next AMQP call, as a broken pipe.
- 2026-11-05: the maintainer answered the questions. WL-Q1 (a) a thread per job with every AMQP call on the connection's thread, WL-Q2 (a) a job found `Running` is marked `Failed` and a finished one is ignored, WL-Q3 (b) a separate queue and worker for long jobs, with the topology to be revisited later, WL-Q4 (b) hold the result, reconnect and publish it, WL-Q5 (a) unfinished jobs are re-read from the store when a view opens, WL-Q6 (a) the service checks the queue's consumer count and warns, and the worker logs each job. The plan is accepted and TD-131 and TD-141 leave the debt register.
- 2026-11-05: WL-1 picked up, building. The reproductions run the real worker entry point against a real broker started by the studio harness, since the unit tests fake the connection and cannot see a heartbeat.
- 2026-11-05: WL-1 built. Three tests of `test/studio-integration/test_worker_liveness.py` fail on `main` for the reasons the plan gave: a 10 s job on a 2 s heartbeat is never finished (RC1), a job the first worker had started is run again by the second (RC3), and a `cst:Refresh` message stops the worker and the validation behind it waits without end (RC7). The view test (RC5) shows 2 validations submitted at the first mount of a workspace and 4 after the author leaves and returns, with the held jobs still polled. A worker is 62 MB idle and up to 130 MB after a mapping compile. Learned: `ProcessStudio` takes `workers = 0` and starts a patched worker with `start_worker`, which is how a test changes what a job does without changing the worker.
- 2026-11-05: WL-2 picked up, building. The consumer is designed once for WL-2 to WL-4, as a connection thread that owns every AMQP call and a thread per job, so WL-3 (the check on delivery) and WL-4 (the held result) are changes to the same two modules and each is marked and committed in turn.
- 2026-11-05: WL-2 built. `config_studio_consumer.py` holds the connection thread and the job threads, and `config_studio_main.py` is the pika session over it. WL1-01 and WL1-03 pass against the real broker, and WL1-02 waits for WL-3. The held result and the adoption of a redelivered job (WL-4) are in the same consumer and have their unit tests, which WL-4 will cite. `RabbitMqConfigStudioWorker` and its two tests are retired, see the pack. Two per-worker settings are new: `LATTICE_WORKER_QUEUE` names the queue, for WL-5.
- 2026-11-05: WL-3 picked up, building.
- 2026-11-05: WL-3 built. `handle` leaves a finished job alone, writes `Failed` on a job found running, refuses a job that names no workspace unless it is a rebuild, and logs the start of each job. `fail` is what the consumer calls for a job it could not run. `studio:liveness` passes all three cases. Recorded in the pack: a race between two workers on one queue that can leave a succeeded job reading `Failed`.
- 2026-11-05: WL-4 picked up, building. Its code is in the consumer WL-2 committed. What remains is the connection's name, so the broker's own tools can find the worker's connection, a real-broker test that closes it mid-job, and the pack.
- 2026-11-05: WL-4 built. A real broker closes the worker's connection three seconds into an eight second job. The worker reconnects, takes the redelivered message for the job in hand and finishes it once. The worker's connection is named, and the harness closes connections by name. Learned for a register: `rabbitmqctl list_connections` prints a pid in JSON as `Pid(#PID<...>)`, which `close_connection` refuses, and in its default table as `<node.creation.id.serial>`, which it takes.
- 2026-11-05: WL-5 picked up, building. The service routes by kind to a second queue, `lattice.studio.jobs.long`, for a proposal by a model and for a publication. The worker takes its queue from `LATTICE_WORKER_QUEUE`, `studio:up` starts a worker for each queue, and the harness topology gains `long_workers`.
- 2026-11-05: WL-5 built. `contracts/config-studio/amqp-topology.json` gains `lattice.studio.jobs.long`, the service routes by `Lanes`, the worker takes its queue from `LATTICE_WORKER_QUEUE`, `studio:up` starts `worker-long`, `studio:worker-long` runs one by hand, and the harness topology gains `long_workers`, default 1. With a worker for each queue a validation ends in a few seconds while a 25 s proposal runs. Learned: the harness's `spawn` appends to a process's log, so two tests that name a worker alike read each other's lines.
- 2026-11-05: WL-6 picked up, building.
- 2026-11-05: WL-6 built. `GET /api/workspaces/{ws}/jobs?unfinished=true` is the new read. `awaitJob` ends on an abort signal, a validation's hook aborts when the workspace view goes and deletes its job, and the proposal views and the publication view attach to the unfinished job of their kind when they open. Two adversarial probes failed the new tests as they should. The worker acknowledges a job the store no longer holds. Not driven by a browser: the publication view's attach and the mapping proposal's.
- 2026-11-05: WL-7 picked up, building.
- 2026-11-05: WL-7 built. `/api/status` warns of a queue no worker consumes, the studio reads its warnings every half minute, the Build view counts a queued job's wait, and `studio:status` names a part that has ended with the last line of its log. The operations guide, the runbook, the worker's README, the contract, MEC-95 and an amendment to ADR-A136 (Proposed) describe the worker. The whole unit is built. TD-131 and TD-141 left the register with the plan.
- 2026-11-05: merged `main` in, which carries the adoption of Вивід. Two text conflicts, `ROADMAP.md` and the debt register. Both sides had written a TD-146, and `check:identifiers` kept the number for this unit's row, committed first, so the row on the writing rules is now TD-149 with its citations. TD-141 stays removed by this unit, TD-143 and TD-144 by the migration. The worker, service, contract and test files are as the fixes left them.
- 2026-11-06: WL-8 picked up, building. An interrupted `studio:liveness` left its Fuseki, broker, writer and service running for hours.
- 2026-11-06: WL-8 built. Each process of a run is detached, so a test process killed before `stop()` finished left them running. The last leak stopped at the fourth liveness test, 08:25:37, with `worker-dies` told to stop and no later worker started, so the run was interrupted, and what ended its teardown is inferred, not observed. A run of the `processes` runner now has a detached reaper that waits on a pipe from its starter. Against a real stack, SIGKILL mid-test, SIGINT then SIGKILL in teardown, and SIGTERM each left no process and no run folder. A run of the `compose` runner has no reaper (TD-150). Noted by the maintainer: `close_connection` is an orderly close, and a netsplit, where the peer goes silent with no close, is not tested. See the pack.
- 2026-11-06: the harness's workers no longer take `LATTICE_PROPOSER_*` from the shell. The liveness suite submits a proposal by a language model, and `stack.spawn` passes on the whole environment, so a developer's key could have reached it and spent on a real model. `_worker_env` blanks that family and a test sets its own through `env`. The `compose` runner names its workers' environment already.
