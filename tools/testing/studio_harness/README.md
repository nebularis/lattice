<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# lattice-testing-studio-harness

Starts a Configuration Studio from a declared topology, on ports, data and names of its own, and gives a client over the studio's HTTP API ([ADR-A125](../../../docs/architecture/decisions/ADR-A125-test-support-tooling.md), [ADR-A150](../../../docs/architecture/decisions/ADR-A150-performance-integration-and-load-testing.md)). Only tests, checks and benchmarks import it. It is not a deployment tool.

```python
from lattice_testing_studio_harness import Topology, smoke

with Topology.load("test/studio-integration/topologies/pair.toml").start() as studio:
    steps = smoke(studio.client())
```

## A topology

A TOML file with these keys, all but `name` optional.

| Key | Values | Default | Means |
|---|---|---|---|
| `name` | letters, digits, `-`, `_` | | names the topology |
| `writers` | 1 or more | 1 | store writer processes. They join one consumer group and RabbitMQ spreads the writes super stream's partitions across them |
| `workers` | 0 or more | 1 | Python workers consuming the jobs queue |
| `store` | `tdb2`, `memory` | `tdb2` | Fuseki over TDB2 in the run's folder (or a Docker volume), or over a dataset in memory |
| `auth` | `local` | `local` | the service's authentication. `oidc` is not supported yet |
| `runner` | `processes`, `compose` | `processes` | how the components run. `start(runner=...)` overrides it |

The number of partitions is fixed at 8 by `contracts/config-studio/amqp-topology.json`, so `writers` is a number of writer processes and not of partitions. The transforms worker is not started, since no scenario here uses it.

## The two runners

Both start Fuseki with two services over one dataset (`studio` reads and `studio-write` updates), RabbitMQ with the stream plugin, the writers, the service and the workers, wait until the service answers and every worker consumes the jobs queue, and remove everything on `stop()`.

| | `processes` | `compose` |
|---|---|---|
| Components | local processes started by `tools/config_studio_stack.py`'s own functions | one container each, on a network `studio` of the run's own, from a generated `compose.yaml` |
| Ports | five free loopback ports found at start (Fuseki, AMQP, Erlang distribution, stream, service) | one free loopback port, the service's. The rest are reached by service name |
| Data | `{run folder}/data/tdb2`, or memory | the volume `data` of the project, removed by `down -v`, or memory |
| Broker | a RabbitMQ node named `{run id}@localhost` with its own base folder and ports | a container of the project |
| Names | the run id names the folder and the node. The streams and queues keep the names the contract declares, which cannot clash because each run has its own broker | the run id is the compose project and the tag of every image built |
| Stop | each process through its own shutdown, in reverse order, then the folder | `docker compose down -v --remove-orphans`, `docker rmi` of the run's tags, then the folder |

In `compose` the service listens on loopback inside its container, as the `local` authentication requires, and a Caddy container sharing its network namespace forwards the published port to it. Images are built from `deployment/compose/config-studio` (`fuseki.Dockerfile`, `java.Dockerfile` for the service and the writer, `worker.Dockerfile`).

## What a run reads from the checkout

- the staged assets in `.build/config-studio` (`mise run build:config-studio-assets`), copied into the run without the developer stack's `run` and `infra` folders and backups
- the service's and the writer's jars from `platform/config-studio-{service,writer}/target`, copied by content hash to `.build/studio-harness/_cache/jars`. The harness only reads `target`, so a stack running from those jars is not disturbed. It runs Maven, which writes `target`, only when a jar is missing. `LATTICE_STUDIO_HARNESS_JARS` names a folder to use instead, holding the two jars or being another checkout's `platform` folder
- the Fuseki jar and the RabbitMQ release, seeded from the developer stack's `infra` folder when present and otherwise downloaded and checked against the checksums the stack script pins, into the same cache

To run an older checkout, as the `studio-api` benchmark's `--checkout` does, set `LATTICE_STUDIO_HARNESS_JARS` (its `platform` folder), `LATTICE_STUDIO_HARNESS_ASSETS` (its staged `.build/config-studio`) and `LATTICE_STUDIO_HARNESS_WORKER_ROOT` (the checkout). The `processes` runner then starts the worker from this checkout's interpreter with that checkout's `workers/src`, `tools` and package sources first on `PYTHONPATH`, and its root as `LATTICE_ROOT`. The `compose` runner ignores the worker root.

A run of the `processes` runner has a detached reaper, which stops its processes and removes its folder when the process that started it ends without finishing `stop()`, by SIGKILL for example. A killed run of the `compose` runner still leaves its containers, for `docker compose -p {run id} down -v`.

A run folder is `.build/studio-harness/{run id}` (git-ignored). Setting `STUDIO_HARNESS_KEEP=1` keeps it after `stop()`, with the logs in `run/`.

## The client

`Client(url, principal="developer")` sends `X-Lattice-Principal`. Each method returns a `Reply` (`status`, `body`, `text`, `headers`, `location`, `revision`, `nanos`) and never raises on a status. `nanos` is the time of the request, from sending to the last byte read, on `time.perf_counter_ns`. Methods are `create_workspace`, `list_workspaces`, `get_workspace`, `delete_workspace`, `export_workspace`, `read_part`, `save_part`, `set_access`, `set_dependencies`, `submit_job`, `get_job`, `wait_job`, `publish`, `delete_job`, `registry_terms`, `registry_holders`, `registry_bundle` and `health`. Each request opens its own connection, so a client may be shared by threads.

`smoke(client)` runs create, list, two saves, a stale save refused with `412`, a read of revision 1, a publish job and publish, the registry, lock and delete, and returns the steps with their times.

## Reports, the timer and the comparison

`reports` writes a benchmark's report, one JSON file per run in `benchmark/reports/{benchmark}/{UTC date and time}-{short commit}.json`, described by [report.schema.json](../../../benchmark/reports/report.schema.json). `reports.machine()` records the kind of machine, never its name or its user. `reports.measure()` gives a measure's median, interquartile range, minimum and maximum, and `reports.time_ms()` times a Python action on `time.perf_counter_ns` with warm-up repeats discarded. `compare` (`mise run benchmark:compare -- {benchmark} [--base REPORT] [--head REPORT]`) tables two reports, marks a change whose medians lie outside both runs' interquartile ranges, warns when the machines differ, and exits 1 only on a malformed or missing report (STD-290). They live here because the harness is the one consumer so far and is already installed where the checks run. Move them to their own package when a benchmark that does not use the harness needs them.

## Tests

`tests/` holds the package's own tests (SH-T1 to SH-T8, and SR-T1 to SR-T12 for the reports). They start nothing and run in `mise run check:config-studio`. The suite that starts studios is [`test/studio-integration`](../../../test/studio-integration/README.md).
