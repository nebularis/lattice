<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# The studio worker stays alive through a long job: status

**Unit ID:** `studio-worker-liveness`
**Plan:** [studio-worker-liveness.md](../plans/studio-worker-liveness.md)
**Mode:** default. Write, then hand off.
**Status:** built 2026-11-05. WL-Q1 to WL-Q6 wait on the maintainer.

## Position

| Slice | Deliverable | State | Blocked on |
|---|---|---|---|
| WL-0 | the plan, this record, the board | built 2026-11-05 |  |
| WL-1 | reproductions that fail today, the view's fate on remount, a worker's idle memory | planned | WL-Q1 to WL-Q6 |
| WL-2 | the job on its own thread, the publisher and acknowledgement across threads | planned | WL-Q1 |
| WL-3 | the check on delivery, a job that cannot run marked `Failed`, each job logged | planned | WL-Q2 |
| WL-4 | the held result, reconnecting with a backoff | planned | WL-Q4 |
| WL-5 | short jobs past long ones | planned | WL-Q3 |
| WL-6 | a view that attaches to its running job, no stacked validations | planned | WL-Q5 |
| WL-7 | the status warning, `studio:status`, the operations guide, the ADR addendum | planned | WL-Q6 |

## Next action

The maintainer answers WL-Q1 to WL-Q6.

## History

- 2026-11-05: planned from two investigations. An independent run reproduced a crash on an upgrade from a message of the retired `cst:Refresh` kind. The logs of the run that prompted TD-141 show that error nowhere, and show instead three disconnections for missed heartbeats, each while the same job ran, the first 2 min 40 s into it. The plan's root causes cover both. Which kind that job was is inferred from the graphs it read and the maintainer's recollection of a proposal in progress, and the store was not started to confirm it.
- 2026-11-05: learned, for a register once one owns it. Pika's `BlockingConnection` services heartbeats only while its own thread is inside the library, so a callback that holds the thread past the broker's timeout loses the connection, and the failure appears only at the next AMQP call, as a broken pipe.
