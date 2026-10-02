<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: WA10, Compose stack

**Unit:** `word-authoring-poc` (WAP), ADR-A114
**Plan:** [word-authoring-poc.md](../plans/word-authoring-poc.md) section "WA10: Compose stack"
**Status record:** [word-authoring-poc.md](../status/word-authoring-poc.md)

## Invariant

The word authoring POC (service, worker, Fuseki, RabbitMQ, and the add-in) can be brought up as one
standalone, browsable demo with one `mise` command, independent of the root dev stack and bound
only to `127.0.0.1`. Every piece that plan WA4-WA9a built in isolation — snapshot submission,
worker analysis, conformance checking, graph export, the harness UI — must work when wired together
through a real network, a real reverse proxy, and real containers, not through test mocks. A
restart of any one service must not corrupt or duplicate the data the others depend on.

## Test case table

| ID | Given / When / Then | Level | Invariant protected | Pass criterion | +/- |
|---|---|---|---|---|---|
| S10-01 | `authoring_stage.py` over a fake tree; the jar or `taskpane.html` missing | L1 | the staging script never builds a stack from stale or absent inputs | `test_authoring_stage.py` (4 tests) passes | +/- |
| S10-02 | `docker compose config -q` over `docker-compose.yml` | L4 | the compose file is structurally valid before any service starts | the command exits 0 | + |
| S10-03 | `GET /api/health` through the proxy | L5 | the service is reachable, and both the service and the proxy set their own security headers | `status: "ok"`, `nosniff` and the CSP both present | + |
| S10-04 | `GET /api/templates`, `/api/samples`, and `/api/documents/{id}` for each sample | L5 | seeding on startup actually happens and is visible through the proxy | 3 templates, 3 samples, each seeded document at `latestRevision >= 1` | + |
| S10-05 | the seeded facility and licence, analysis polled for up to 60s | L5 | the full event pipeline (service to worker to service) completes for real, including conformance checking | facility has an `Obligation`/`form` element; licence's conformance has `term-kind-not-allowed` in `grant` | + |
| S10-06 | a new snapshot submitted via `PUT`, job polled for up to 20s | L5 | a document submitted after startup, not just a seeded one, completes the same pipeline | the job completes; the proposal graph Turtle contains `instrument#` and `Obligation` | + |
| S10-07 | `GET` on the add-in's static paths and the manifest's icon/help URLs, through the proxy | L5 | the proxy serves the add-in's build output at the paths the manifest references | every path responds 200 | + |
| S10-08 | the harness, through the proxy, with no mocking: insert the facility sample, analyse, open Logical English | L6 | the whole stack renders a real, usable demo in a real browser | coloured spans appear for the facility reading | + |
| S10-09 | `docker compose restart authoring-service`, health polled, then re-read the facility analysis and document view | L5 | a service restart does not lose or duplicate seeded data, which lives in Fuseki, not the service's memory | same analysis as before the restart; `latestRevision` still 1 | +/- |

9 test cases: 4 in `tools/test_authoring_stage.py`, 1 compose-config check folded into the slice's
own verification (not a persisted automated test — compose's own `config -q` is the check), and 7
in `apps/word-authoring-addin/e2e-stack/stack.spec.ts`, run for real against the live stack.

## One command

```
mise run check:authoring-stack
```

Runs `authoring:up` (which itself runs `build:authoring`: package the service jar, build the
add-in, stage `.build/authoring/`) then the Playwright suite in `e2e-stack/`.

```
mise run check:authoring-tools
```

Runs just the staging-script unit tests (`tools/test_authoring_stage.py`), without Docker.

## Expected artefacts

- `deployment/compose/authoring/docker-compose.yml`, `service.Dockerfile`, `worker.Dockerfile`, `Caddyfile`
- `tools/authoring_stage.py`, `tools/test_authoring_stage.py`
- `apps/word-authoring-addin/playwright.stack.config.ts`, `e2e-stack/stack.spec.ts`
- `docker compose -f deployment/compose/authoring/docker-compose.yml ps` showing all five services healthy/running
- Browsing `https://localhost:3443` (redirects to `/addin/harness.html`)

## Deliberate non-coverage

- No test asserts on RabbitMQ or Fuseki internals directly — they are exercised only through the
  service and worker's own behaviour, consistent with how WA4-WA7 already tested them.
- No test covers sideloading the manifest into real Word; that is WA11's job, not this stack's.
- No test covers restarting `fuseki` or `rabbitmq` themselves (only `authoring-service`, per
  S10-09) — a later slice could add this if the POC's scope grows to cover it.
- The compose stack has no automatic TLS trust: a fresh browser must accept the warning or run
  `mise run authoring:ca` once. Automating certificate trust is out of scope for a local POC stack.

## Self-probe

Plan: "stop `authoring-worker` and confirm S10-06 fails (the job never completes); restart it and
confirm S10-06 passes again."

Ran `docker compose stop authoring-worker`, then `playwright test -g S10-06`: failed exactly as
predicted (`job ... did not complete within 20000ms`, since nothing ever consumes the
`wording-analysis-request` event with the worker down). Restarted the worker
(`docker compose start authoring-worker`), waited for it to finish starting, reran the same test:
passed. The fifth slice running (after WA7, WA8, WA9, WA9a) whose prescribed self-probe bites
exactly as written, with no replacement test needed.

## Real bugs found and fixed while building this slice

Running the stack for real (not just authoring Dockerfiles and compose YAML) surfaced two
pre-existing bugs that every earlier, mocked Playwright test had masked, because
`page.route("**/api/health", ...)` and similar globs match any URL *containing* that suffix,
including a doubled one:

1. **`HttpApiClient` was constructed with `"/api"` as its base URL** in both `main.tsx` and
   `harness.tsx`, but every one of its methods already includes `/api/...` in the path it requests
   (`getJson("/api/health")`, etc). Every real request therefore went to `/api/api/health` and
   the like, which Javalin's exact-path routing correctly 404s, and which the mocked tests'
   wildcard globs incorrectly matched anyway. Fixed by constructing both clients with `""`.
2. **The add-in's bundled Ajv compiles validators via `new Function` at runtime** (the standard,
   documented way Ajv achieves its validation speed), which a strict `script-src` without
   `'unsafe-eval'` silently blocks in a real browser, throwing a `pageerror` that stopped the
   entire React app from rendering past catalogue load. No earlier test caught this because none
   of them ran the add-in behind a real CSP-enforcing proxy. Fixed by adding `'unsafe-eval'` to
   the proxy's `script-src` directive — every other directive stays as restrictive as planned.

Neither bug is specific to this stack: both would affect the add-in running for real inside Word
too, once sideloaded (WA11). Finding them here, rather than there, is the reason this slice's test
level reaches L5/L6 against a real stack instead of stopping at mocked L1 tests.
