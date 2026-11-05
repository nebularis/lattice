<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Studio integration tests

Runs each topology declared in `topologies/` on the [studio harness](../../tools/testing/studio_harness/README.md) ([ADR-A150](../../docs/architecture/decisions/ADR-A150-performance-integration-and-load-testing.md)). A run starts a studio on ports, data and names of its own, so it never touches a developer's store or a running `studio:up` stack, and it stops everything it started.

```bash
mise run studio:integration
mise run studio:integration -- --runner compose
```

The first runs every component as a local process, the second in Docker Compose. It needs the jars already built under `platform/*/target` (`mise run studio:up` builds them) and the staged assets, which the task builds. It takes about a minute with processes and a few minutes with Compose the first time, while images build.

The task is on demand and never a dependency of `check` (SQ-D7). The tests carry the marker `studio_integration`, and the root pytest configuration collects only `tools`, so nothing here runs unless asked.

| File | Holds |
|---|---|
| `topologies/single.toml` | one writer, one worker |
| `topologies/pair.toml` | two writers, two workers |
| `test_smoke.py` | for each topology, starts it, runs the smoke scenario, stops it, and asserts that no process or container it started remains, its run folder is gone and its port is closed |

A topology is added by adding a file to `topologies/`. Output is printed with the time of each step, so run with `-s` (the task does).
