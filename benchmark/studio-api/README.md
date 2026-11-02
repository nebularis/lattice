<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Studio API

A benchmark under [ADR-A124](../../docs/architecture/decisions/ADR-A124-benchmark-root.md) and [ADR-A150](../../docs/architecture/decisions/ADR-A150-performance-integration-and-load-testing.md). It starts the `single` topology (one writer, one worker, TDB2) through the [studio harness](../../tools/testing/studio_harness/README.md) on the `processes` runner, and times the studio's HTTP API by the time of each reply.

## What it measures

| Measure | Repeats | Means |
|---|---|---|
| `save part, N triples` | 10 | a `PUT` of a concept scheme of N triples (100, 1,000, 3,000) to the part `vocabulary`, each at the revision just read. Every save differs from the last in one triple |
| `read part, N triples` | 10 | the `GET` of the part after each save |
| `list workspaces` | 20 | the `GET` of the workspace listing |
| `publish job (submit to done)` | 5 | submitting a publish job and waiting for it, with a changed label each time |
| `publish` | 5 | the `POST` that publishes the job's result |
| `list registry` | 5 | the registry listing after each publication |

Two warm-up repeats of each measure run first and are discarded. The sizes are generated deterministically: SKOS concepts with a label and one blank node each. It uses only routes that exist before and after phase D of the publication unit, and waits for no projection.

## Pass criterion

Every reply's status is asserted, a save returns the next revision, a read-back has exactly the triples saved, the workspace is listed and the published scheme is in the registry. **A wrong result fails the run. Time never does.**

## Run it

```bash
mise run benchmark:studio-api                                  # about 30 seconds
mise run benchmark:studio-api -- --checkout ../other-worktree  # another checkout of the repository
mise run benchmark:compare -- studio-api                       # the latest report against the one before
```

It never builds a jar. It reads `platform/*/target` of the checkout it measures, so build them first, and stage that checkout's assets (`mise run build:config-studio-assets`, or `python tools/config_studio_stage.py` run from it). It is never a dependency of `check`.

The report is `benchmark/reports/studio-api/{UTC date and time}-{short commit}.json` ([schema](../reports/report.schema.json)), kept in git. It names the kind of machine, its power mode and its load when the run started, never its host name or its user. A report made with uncommitted changes says so in its notes.

## Another checkout

`--checkout PATH` sets the three variables the harness reads (`LATTICE_STUDIO_HARNESS_JARS` to `PATH/platform`, `LATTICE_STUDIO_HARNESS_ASSETS` to `PATH/.build/config-studio` and `LATTICE_STUDIO_HARNESS_WORKER_ROOT` to `PATH`), so the jars, the staged assets and the worker's Python source are the checkout's own while the interpreter and its dependencies stay this checkout's. Compare runs only on the same machine, one after the other, and check the power mode and the load before reading a change as real (STD-040).

| File | Role |
|---|---|
| `run.py` | the scenario, the pass criterion and the report |
| `test_run.py` | the scenario's own tests. They start no studio |
