<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Configuration Studio: Operations Guide

**Purpose:** How to configure, run, stop and check each part of the Configuration Studio, and what it does and does not protect
**Status:** Proof of concept. A single-author tool for one machine, not a service to expose on a network
**Companion:** [Configuration Studio runbook](configuration-studio-runbook.md)

---

## Overview

The Configuration Studio is a browser application for authoring and checking configuration against an applied ontology. It is five processes on one machine. Every command below runs through `mise`, which puts the pinned Java, Maven, Node, Python and Erlang on the path ([ADR-A29](../architecture/decisions/ADR-A29-repository-toolchain-and-environment-boundary.md)). A bare `python`, `java` or `mvn` may be a different version.

| Part | What it is | What it does | Listens on |
|---|---|---|---|
| Browser application | React, built with Vite ([README](../../apps/config-studio/README.md)) | The authoring views. Served by the service once built, or by a hot-reload dev server | `127.0.0.1:4175` for the dev server only |
| Service | Java on Helidon SE with Apache Jena ([README](../../platform/config-studio-service/README.md)) | The HTTP API under `/api`, workspaces and jobs as named graphs, the built browser application, and publishing each job to RabbitMQ | `127.0.0.1:8090` |
| Worker | Python, `lattice_workers.config_studio_main` ([README](../../workers/README.md#configuration-studio-jobs-adr-a136)) | Consumes jobs, validates or compiles the configuration with each layer's own engine, and writes the result back | nothing |
| Fuseki | Apache Jena Fuseki ([version pinned below](#download-pins)) | The graph store. One dataset, `studio`, in memory | `127.0.0.1:3130` |
| RabbitMQ | RabbitMQ on Erlang | Carries job messages from the service to the worker | `127.0.0.1:5673` (AMQP), `127.0.0.1:25673` (Erlang distribution) |

The data contracts between them are in [contracts/config-studio](../../contracts/config-studio/README.md).

```
browser ──HTTP──▶ service ──SPARQL──▶ Fuseki ◀──graph store protocol── worker
                     │                                                     ▲
                     └──────────── AMQP, job IRI ──▶ RabbitMQ ────────────┘
```

A save writes to Fuseki only. A validation or compilation writes the job to Fuseki as `cst:Queued`, publishes its IRI to RabbitMQ, and the worker reads the job from Fuseki, runs it, and writes the same graph back as `cst:Succeeded` or `cst:Failed`. The browser polls the service for the job.

---

## Ports and addresses

| Port | Bound to | Used by | Set by |
|---|---|---|---|
| `8090` | `127.0.0.1` | the service | `LATTICE_STUDIO_PORT`, `LATTICE_STUDIO_BIND` |
| `4175` | `127.0.0.1` | the dev server (`--dev` or `studio:web`), with `strictPort` so it fails rather than choosing another | `apps/config-studio/vite.config.ts` |
| `3130` | `127.0.0.1` | Fuseki. Fuseki is started with `--localhost`, and the compose file publishes `127.0.0.1:3130` to the container's `3030` | `tools/config_studio_stack.py`, the compose file |
| `5673` | `127.0.0.1` | RabbitMQ AMQP | `RABBITMQ_NODE_PORT` in the stack script, the compose file |
| `25673` | `127.0.0.1` | RabbitMQ's Erlang distribution port, the AMQP port plus 20000. `rabbitmqctl` uses it | `RABBITMQ_DIST_PORT` in the stack script |
| `15673` | `127.0.0.1` | RabbitMQ's management interface, in the Docker setup only | the compose file |

The stack script has no setting for these ports. The ports of Fuseki and RabbitMQ are constants in `tools/config_studio_stack.py` and the same numbers appear in `mise.toml` (the `studio:service` and `studio:worker` tasks) and the compose file. Change all three together or none.

The dev server proxies `/api` to `127.0.0.1` on `LATTICE_STUDIO_PORT`, or `8090` if that is unset.

---

## Environment

### Service

Read by `StudioConfig.fromEnv`. A blank value counts as unset.

| Variable | Default | Meaning |
|---|---|---|
| `LATTICE_STUDIO_PORT` | `8090` | Listening port. A value that is not a number, or outside 0 to 65535, stops the service at start |
| `LATTICE_STUDIO_BIND` | `127.0.0.1` | Bind address. Leave it |
| `LATTICE_STUDIO_ASSETS` | `.build/config-studio` | The directory `mise run build:config-studio-assets` fills with `vocabulary.ttl`, `samples.ttl` and `samples/`. A relative path is relative to the directory the service starts in, the repository root |
| `LATTICE_STUDIO_STATIC` | none | The built browser application, served for any path outside `/api`. The stack sets it to `apps/config-studio/dist`. Without it the service answers `404` outside `/api` |
| `LATTICE_FUSEKI_URL` | none | Fuseki's base URL. Unset means an in-memory dataset inside the service, with a warning in the log |
| `LATTICE_FUSEKI_DATASET` | `studio` | The dataset name |
| `LATTICE_FUSEKI_USER`, `LATTICE_FUSEKI_PASSWORD` | none | Basic authentication to Fuseki. The stack's Fuseki has none |
| `LATTICE_AMQP_URI` | none | RabbitMQ's URI. Unset means jobs are recorded but never delivered, and stay `cst:Queued`, with a warning in the log |

### Worker

Read by `config_studio_main.read_config`.

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `LATTICE_AMQP_URI` | yes | none | RabbitMQ's URI. Unset stops the worker at start with `LATTICE_AMQP_URI is required` |
| `LATTICE_FUSEKI_URL` | yes | none | Fuseki's base URL. Unset stops the worker at start |
| `LATTICE_FUSEKI_DATASET` | no | `studio` | The dataset name, which must be the service's |
| `LATTICE_FUSEKI_USER`, `LATTICE_FUSEKI_PASSWORD` | no | none | Basic authentication to Fuseki |
| `LATTICE_ROOT` | no | found from the working directory | The repository root, where the worker reads the ontology files it validates against |

### Values the stack sets

`studio:up`, `studio:service` and `studio:worker` all use the same values. The service and the worker must agree on the Fuseki URL and dataset and on the AMQP URI, or jobs are written where the worker does not look.

| Variable | Value |
|---|---|
| `LATTICE_FUSEKI_URL` | `http://127.0.0.1:3130` |
| `LATTICE_FUSEKI_DATASET` | `studio` |
| `LATTICE_AMQP_URI` | `amqp://guest:guest@127.0.0.1:5673/%2F` |
| `LATTICE_STUDIO_STATIC` | `apps/config-studio/dist` (the service only) |

The AMQP URI holds RabbitMQ's `guest` password. That is acceptable only because the broker is local and `guest` is its default. Do not put a real credential in it.

---

## Where things live

Everything the stack writes is under `.build/config-studio`, which git ignores. Deleting that directory resets the stack (see the runbook).

| Path | Holds |
|---|---|
| `.build/config-studio/run/{name}.pid` | The process id of `fuseki`, `rabbitmq`, `service`, `worker` or `web`, written when `up` starts it and removed by `down` |
| `.build/config-studio/run/{name}.log` | That process's standard output and error, appended on each start and never rotated |
| `.build/config-studio/run/docker` | Present only after `up --docker`. Holds the compose file's path so `down` knows to stop the containers |
| `.build/config-studio/infra/` | The downloads and what they unpack to |
| `.build/config-studio/infra/jena-fuseki-server-{version}.jar` | The Fuseki release |
| `.build/config-studio/infra/fuseki-base/` | Fuseki's `FUSEKI_BASE` (its working files and logging configuration). The dataset is not stored here |
| `.build/config-studio/infra/rabbitmq-server-*` and `rabbitmq_server-{version}/` | The RabbitMQ archive and its unpacked release |
| `.build/config-studio/infra/rabbitmq/mnesia/` | RabbitMQ's data directory (`RABBITMQ_MNESIA_BASE`), holding the node's metadata and any persistent messages |
| `.build/config-studio/infra/rabbitmq/log/` | RabbitMQ's own logs (`RABBITMQ_LOG_BASE`), apart from `run/rabbitmq.log` |
| `.build/config-studio/vocabulary.ttl`, `samples.ttl`, `samples/` | The assets the service reads, staged by `mise run build:config-studio-assets` |
| `apps/config-studio/dist/` | The built browser application |
| `platform/config-studio-service/target/config-studio-service.jar` | The built service |

The service and the worker log to standard output, so their only log is `run/service.log` and `run/worker.log`. A run started in a terminal logs to that terminal. With `up --docker`, the logs of Fuseki and RabbitMQ are the containers' (`docker compose -f deployment/compose/config-studio/docker-compose.yml logs`).

---

## Fuseki

Started as `java -jar jena-fuseki-server-{version}.jar --localhost --port 3130 --mem --update /studio`.

| Setting | Effect |
|---|---|
| `--mem` | The dataset is in memory. **Stopping Fuseki loses every workspace and job.** There is no persistence and no backup |
| `--update` | The dataset accepts updates. Without it the service could not save |
| `/studio` | The dataset name. It matches `LATTICE_FUSEKI_DATASET` |
| `--localhost` | Fuseki listens on the loopback address only |
| `FUSEKI_BASE` | `.build/config-studio/infra/fuseki-base` |

The Docker setup builds the same server from `deployment/compose/config-studio/fuseki.Dockerfile` on `eclipse-temurin:25-jre-alpine`, pinned by the same checksum, listening on `3030` in the container, published at `127.0.0.1:3130`, and also in memory.

Because the dataset is in memory, a restart of Fuseki alone, while the service and the worker keep running, empties the studio. The browser then shows `404` for the workspace it had open. Export anything worth keeping from the browser before stopping Fuseki.

---

## RabbitMQ

Started from the generic Unix release (the Windows release on Windows) through its `rabbitmq-server` script, with this environment.

| Variable | Value | Why |
|---|---|---|
| `RABBITMQ_NODENAME` | `studio@localhost` | A node name of its own, so it cannot clash with another RabbitMQ on the machine. Every `rabbitmqctl` call names it with `-n` |
| `RABBITMQ_NODE_IP_ADDRESS` | `127.0.0.1` | Loopback only |
| `RABBITMQ_NODE_PORT` | `5673` | Not the default `5672` |
| `RABBITMQ_DIST_PORT` | `25673` | Not the default `25672` |
| `RABBITMQ_MNESIA_BASE` | `.build/config-studio/infra/rabbitmq/mnesia` | Data stays in the checkout |
| `RABBITMQ_LOG_BASE` | `.build/config-studio/infra/rabbitmq/log` | Logs stay in the checkout |
| `RABBITMQ_SERVER_ADDITIONAL_ERL_ARGS` | `-rabbit loopback_users []` | Allows `guest` from any address the node accepts connections on. The node accepts only loopback (see [Security](#security)) |
| `ERLANG_HOME` | the parent of the directory holding `erl` | RabbitMQ's scripts find Erlang from it. The stack derives it from `erl` on the path, and stops with "RabbitMQ needs Erlang" if there is none |

RabbitMQ runs on the Erlang mise installs, so start it through `mise`. The user is the default `guest` with password `guest`, in virtual host `/` (written `%2F` in the URI). The Docker setup runs `rabbitmq:4.4-management-alpine` with `guest`/`guest` set explicitly, and publishes the AMQP port at `127.0.0.1:5673` and the management interface at `127.0.0.1:15673`.

### Topology

Declared identically, and idempotently, by the service when it connects and by the worker when it starts, from [`amqp-topology.json`](../../contracts/config-studio/amqp-topology.json).

| Kind | Name | Notes |
|---|---|---|
| Exchange | `lattice.studio` | topic, durable |
| Exchange | `lattice.studio.dlx` | topic, durable. The dead-letter exchange |
| Queue | `lattice.studio.jobs` | durable. Bound to `lattice.studio` with key `lattice.studio.jobs`. Dead-letters to `lattice.studio.dlx` |
| Queue | `lattice.studio.dead` | durable. Bound to `lattice.studio.dlx` with key `#` |

A message is the job's IRI (`urn:lattice:studio:job:` and a lower-case UUID) in UTF-8, persistent, published with a broker confirm and a five-second timeout. The worker consumes with manual acknowledgement and one message in flight at a time (`prefetch_count=1`), and acknowledges only after it has written the final job graph.

| Worker outcome | Broker action |
|---|---|
| Job run, whatever its result | Acknowledged |
| Message that is not a job IRI, or names a job graph that does not exist | Rejected without requeue, so it moves to `lattice.studio.dead` |
| Any other error, such as Fuseki being unreachable | Rejected with requeue, and the worker stops with the error |

A job that fails because its configuration did not validate or compile is not an error. It is a `cst:Succeeded` job whose report says so. A `cst:Failed` job is one that could not run, such as a missing input graph.

---

## Starting

### Everything, in the background

```bash
mise run studio:up
```

This stages the assets, then for each of Fuseki and RabbitMQ downloads the release if it is not already in `.build/config-studio/infra` (checking its SHA-256), starts it, and waits up to 180 seconds for its port. If the port is already listening it prints "already listening" and starts nothing. It then builds the browser application with Yarn, builds the service with Maven, starts the service and waits for `8090`, and starts the worker. It prints the address, `http://127.0.0.1:8090`.

The first run downloads about 80 MB (Fuseki's jar and RabbitMQ's archive) and builds the browser application and the service, so it is slow. Later runs reuse the downloads.

| Command | Effect |
|---|---|
| `mise run studio:up` | The downloaded Fuseki and RabbitMQ, the built browser application served by the service on `8090` |
| `mise run studio:up -- --docker` | Fuseki and RabbitMQ from `docker compose` instead of downloads. Needs Docker. Waits for both containers to be healthy |
| `mise run studio:up -- --dev` | Also the browser code with hot reload on `4175`, proxying `/api` to the service. The browser application is not built. Browse `http://127.0.0.1:4175` |
| `mise run studio:status` | Per part, the process id if its pid file names a live process, and whether its port is listening |
| `mise run studio:down` | Stops what `up` started, in the order the web server, worker, service, RabbitMQ and Fuseki |

`--docker` and `--dev` combine. `up` waits only for a port to listen, so a service that failed to bind because another program holds `8090` is reported as started (see the runbook), and it does not wait for the worker. Read `studio:status`, `service.log` and `worker.log` after a start.

### Each part in its own terminal

For working on one part, or to watch its output. Start Fuseki and RabbitMQ first, either with Docker

```bash
mise run studio:infra
```

or from the releases, for example in `.build/config-studio/infra` (the [service README](../../platform/config-studio-service/README.md#run-it) has the commands). Then each of these in its own terminal.

```bash
mise run studio:service
```

```bash
mise run studio:worker
```

```bash
mise run studio:web
```

`studio:service` builds the service with Maven on each run, then runs the jar with the environment above. `studio:web` is the hot-reload dev server on `4175`. `studio:service` serves the built browser application on `8090` once `mise exec -- yarn workspace @lattice/config-studio run build` has run. Start the service after RabbitMQ is up. It retries the connection 15 times, two seconds apart, and then stops. The worker retries every two seconds without limit.

Do not mix the two ways of running. `studio:down` knows only the processes `studio:up` started, and a part you started in a terminal that holds a port makes `up` skip starting its own ("already listening").

---

## Stopping

```bash
mise run studio:down
```

`down` stops the parts in reverse order, so the worker and the service go before the store and the broker. Each is stopped the way its own tool supports, because a hard kill of a message broker or a store risks the state it would have flushed on a clean stop.

| Part | How it is stopped | Why |
|---|---|---|
| RabbitMQ | `rabbitmqctl -n studio@localhost shutdown`, then the process group is stopped | `shutdown` waits for the node to stop its applications and its metadata store cleanly, so the next start does not recover from an unclean stop |
| Fuseki, service, worker, dev server | `SIGTERM` to the process group, then up to 60 seconds, then `SIGKILL` if it is still running (a message says so) | The service's shutdown hook closes its HTTP server, its AMQP connection and its store. The worker finishes the job in hand and then stops consuming, so no job is left half written. A JVM runs its shutdown hooks on `SIGTERM` |
| Docker | `docker compose down --timeout 60`, when `up --docker` was used | The containers stop through Docker's own stop, with a minute before it kills |

On Windows a detached console process can receive no termination request, so after `rabbitmqctl shutdown` has stopped RabbitMQ the script ends the process tree at once with `taskkill /T /F`. That loses nothing. Fuseki's dataset is in memory and would be lost on any stop. The service keeps no state outside the store. A job the worker had not acknowledged is redelivered, and running a job twice gives the same graph but for its times.

`down` removes a pid file whose process has gone and says nothing for it. A part that was never started here is skipped.

---

## Health checks

| Check | Command | A pass |
|---|---|---|
| Whole stack | `mise run studio:status` | each part `running as {pid}` and the four ports `listening` (`web` shows not listening unless `--dev`) |
| Service up | `curl -s http://127.0.0.1:8090/api/health` | `ok`, status `200` |
| Service build | `mise exec -- java -jar platform/config-studio-service/target/config-studio-service.jar --self-check` | exit status 0 and `self-check passed` in the log. It starts the service on an ephemeral port in memory, requests `/api/health` and exits. It needs neither Fuseki nor RabbitMQ and does not test either |
| Fuseki | `curl -s http://127.0.0.1:3130/$/ping` | status `200` and a timestamp. Quote the URL in a shell where `$` expands |
| Dataset | `curl -s -o /dev/null -w '%{http_code}\n' 'http://127.0.0.1:3130/studio/sparql?query=ASK%7B%7D'` | `200` |
| RabbitMQ, downloaded | `mise exec -- .build/config-studio/infra/rabbitmq_server-4.4.0/sbin/rabbitmq-diagnostics -n studio@localhost -q ping` | exit status 0 and no error. Use the version the stack script pins |
| RabbitMQ, Docker | `docker compose -f deployment/compose/config-studio/docker-compose.yml exec rabbitmq rabbitmq-diagnostics -q ping` | exit status 0. This is also the container's health check |
| Topology and worker | `mise exec -- .build/config-studio/infra/rabbitmq_server-4.4.0/sbin/rabbitmqctl -n studio@localhost list_queues name messages consumers` | `lattice.studio.jobs` with `consumers` 1, and `messages` 0 when idle. `consumers` 0 means no worker is connected |

The worker has no port. It is healthy when `worker.log` shows no error, the queue has one consumer, and a submitted job reaches `cst:Succeeded` or `cst:Failed`.

---

## Download pins

`tools/config_studio_stack.py` downloads each release once, and refuses it unless its SHA-256 equals the one written in the script. A download goes to a `.part` file, is checked, and is then renamed, so a refused or interrupted download never leaves a file that looks complete. A file already in `.build/config-studio/infra` is reused only if its checksum still matches.

| Part | Constant | Pinned |
|---|---|---|
| Fuseki | `FUSEKI_VERSION`, `FUSEKI_URL`, `FUSEKI_SHA256` | Maven Central, `org.apache.jena:jena-fuseki-server` |
| RabbitMQ | `RABBITMQ_VERSION`, `RABBITMQ_RELEASE`, and `RABBITMQ_ARCHIVE` per platform (`rabbitmq-server-generic-unix-{version}.tar.xz` or `rabbitmq-server-windows-{version}.zip`) | The GitHub release of `rabbitmq/rabbitmq-server` |

The versions and checksums are in the script, which is the single source. The Docker setup repeats Fuseki's version and checksum in `fuseki.Dockerfile` and pins RabbitMQ by image tag in `docker-compose.yml`. The service's README repeats both versions in its commands.

### Moving a pinned version

1. Choose the new version. For Fuseki that is a release of `jena-fuseki-server` on Maven Central. Check that the service's Jena version (`platform/pom.xml`) and the release are compatible, since the service speaks SPARQL and the graph store protocol to it. For RabbitMQ, read the release notes for a change of required Erlang against `erlang` in `mise.toml`.
2. Download the file once, from the pinned URL's pattern with the new version, into an empty directory outside the repository.
3. Obtain the checksum from the publisher. For RabbitMQ, GitHub lists a SHA-256 for each release asset. For Fuseki, Maven Central publishes `.sha1` and `.sha512` beside the jar, not `.sha256`. Verify the jar against the published digest first, then compute the SHA-256 of the verified file with `shasum -a 256 {file}` (or `certutil -hashfile {file} SHA256` on Windows). Never take the SHA-256 from the file you downloaded without checking it against the publisher first, since that pins whatever you received.
4. Change the version and checksum constants in `tools/config_studio_stack.py`. For RabbitMQ change both archives, as the two platforms have different checksums.
5. Change the same version in `deployment/compose/config-studio/fuseki.Dockerfile` (URL and `--checksum`), and the image tag in `docker-compose.yml`, and the commands in the service's README.
6. Run `mise run studio:down`, delete `.build/config-studio/infra` for the part that changed (the old release stays on disk and is ignored), then `mise run studio:up`.
7. Run the checks under [Health checks](#health-checks), then `mise run check:config-studio`.

RabbitMQ's data directory is read by the new version on its next start. If it will not start on data an older version wrote, delete `.build/config-studio/infra/rabbitmq` (the queue holds only jobs, which are written to Fuseki first and can be resubmitted).

---

## Security

The Configuration Studio is a single-author tool for one machine. **It must not be exposed on a network as it stands.**

| Aspect | State |
|---|---|
| Authentication | None. The service, the API and Fuseki accept any request. There are no users, sessions or permissions |
| Authorisation | None. Anyone who can reach `/api` can read, change and delete every workspace and job |
| Network exposure | Every listener is bound to `127.0.0.1`. Fuseki has `--localhost`, RabbitMQ has `RABBITMQ_NODE_IP_ADDRESS=127.0.0.1`, and Docker publishes each port at `127.0.0.1`. Changing `LATTICE_STUDIO_BIND` opens the service, and nothing else protects it |
| RabbitMQ user | The default `guest`/`guest`. RabbitMQ accepts `guest` from the loopback address only, but the stack sets `loopback_users []` to remove that rule, so what keeps `guest` local is the loopback bind. In Docker the container's own network is not loopback to the broker, so the compose file sets the same option and relies on the loopback-only port publication |
| Transport | Plain HTTP and plain AMQP. No TLS |
| Cross-origin | No response carries `Access-Control-Allow-Origin`, so a page on another origin cannot read the API from a browser. This is not authentication, because the browser's same-origin rule does not stop a request from the local machine or a forged request |
| Request validation | The service validates every request: content type (Turtle or RDF/XML, else `415`), body size (5 MiB, else `413`), syntax (else `400`), every identifier in a path, the revision a save expects (`If-Match`, else `428` or `412`), and that a saved graph holds only its own part's subjects (`422`). RDF/XML that declares a DTD is refused, which prevents external entities |
| Response headers | `X-Content-Type-Options: nosniff` on every response. `Cache-Control: no-store` on every `/api` response except the vocabulary, which is revalidated by its `ETag`. `Referrer-Policy: no-referrer` on every response. On an HTML response, `Content-Security-Policy: default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'`, which allows no scripts from elsewhere and no framing |
| Static files | The service resolves a requested file to its real path and serves it only if it is a regular file under `LATTICE_STUDIO_STATIC`, so a `..` or a link out is refused |
| Errors | An unexpected error returns `500` with the text `internal error` and logs the detail to the service log, not to the client |
| Secrets | The AMQP URI and the optional Fuseki credentials are environment variables. They are not written to the repository, but they are visible in the process environment and the compose file has the broker's password in the clear |

Reaching it from another machine needs authentication, TLS and a persistent store first, which are outside the proof of concept.
