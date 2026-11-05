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
