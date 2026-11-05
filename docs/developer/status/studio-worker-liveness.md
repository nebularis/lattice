<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# The studio worker stays alive through a long job: status

**Unit ID:** `studio-worker-liveness`
**Plan:** [studio-worker-liveness.md](../plans/studio-worker-liveness.md)
**Mode:** default. Write, then hand off.
**Status:** building 2026-11-05. WL-Q1 to WL-Q6 are answered.

## Position

| Slice | Deliverable | State | Blocked on |
|---|---|---|---|
| WL-0 | the plan, this record, the board | built 2026-11-05 |  |
| WL-1 | reproductions that fail today, the view's fate on remount, a worker's idle memory | built 2026-11-05 |  |
| WL-2 | the job on its own thread, the publisher and acknowledgement across threads | building 2026-11-05 |  |
| WL-3 | the check on delivery, a job that cannot run marked `Failed`, each job logged | planned |  |
| WL-4 | the held result, reconnecting with a backoff | planned |  |
| WL-5 | short jobs past long ones | planned |  |
| WL-6 | a view that attaches to its running job, no stacked validations | planned |  |
| WL-7 | the status warning, `studio:status`, the operations guide, the ADR addendum | planned |  |

## Next action

Build WL-2 to WL-7 in order, each marked `building` before its first edit. The Validation Pack is [studio-worker-liveness](../validation/studio-worker-liveness.md).

## History

- 2026-11-05: planned from two investigations. An independent run reproduced a crash on an upgrade from a message of the retired `cst:Refresh` kind. The logs of the run that prompted TD-141 show that error nowhere, and show instead three disconnections for missed heartbeats, each while the same job ran, the first 2 min 40 s into it. The plan's root causes cover both. Which kind that job was is inferred from the graphs it read and the maintainer's recollection of a proposal in progress, and the store was not started to confirm it.
- 2026-11-05: learned, for a register once one owns it. Pika's `BlockingConnection` services heartbeats only while its own thread is inside the library, so a callback that holds the thread past the broker's timeout loses the connection, and the failure appears only at the next AMQP call, as a broken pipe.
- 2026-11-05: the maintainer answered the questions. WL-Q1 (a) a thread per job with every AMQP call on the connection's thread, WL-Q2 (a) a job found `Running` is marked `Failed` and a finished one is ignored, WL-Q3 (b) a separate queue and worker for long jobs, with the topology to be revisited later, WL-Q4 (b) hold the result, reconnect and publish it, WL-Q5 (a) unfinished jobs are re-read from the store when a view opens, WL-Q6 (a) the service checks the queue's consumer count and warns, and the worker logs each job. The plan is accepted and TD-131 and TD-141 leave the debt register.
- 2026-11-05: WL-1 picked up, building. The reproductions run the real worker entry point against a real broker started by the studio harness, since the unit tests fake the connection and cannot see a heartbeat.
- 2026-11-05: WL-1 built. Three tests of `test/studio-integration/test_worker_liveness.py` fail on `main` for the reasons the plan gave: a 10 s job on a 2 s heartbeat is never finished (RC1), a job the first worker had started is run again by the second (RC3), and a `cst:Refresh` message stops the worker and the validation behind it waits without end (RC7). The view test (RC5) shows 2 validations submitted at the first mount of a workspace and 4 after the author leaves and returns, with the held jobs still polled. A worker is 62 MB idle and up to 130 MB after a mapping compile. Learned: `ProcessStudio` takes `workers = 0` and starts a patched worker with `start_worker`, which is how a test changes what a job does without changing the worker.
- 2026-11-05: WL-2 picked up, building. The consumer is designed once for WL-2 to WL-4, as a connection thread that owns every AMQP call and a thread per job, so WL-3 (the check on delivery) and WL-4 (the held result) are changes to the same two modules and each is marked and committed in turn.
