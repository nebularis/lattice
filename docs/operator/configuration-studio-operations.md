<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Configuration Studio: Operations Guide

**Purpose:** How to configure, run, stop and check each part of the Configuration Studio, and what it does and does not protect
**Status:** Supported. A single-author tool for one machine, not a service to expose on a network
**Companion:** [Configuration Studio runbook](configuration-studio-runbook.md)

---

## Overview

The Configuration Studio is a browser application for authoring and checking configuration against an applied ontology. It is six processes on one machine. Every command below runs through `mise`, which puts the pinned Java, Maven, Node, Python and Erlang on the path ([ADR-A29](../architecture/decisions/ADR-A29-repository-toolchain-and-environment-boundary.md)). A bare `python`, `java` or `mvn` may be a different version.

| Part | What it is | What it does | Listens on |
|---|---|---|---|
| Browser application | React, built with Vite ([README](../../apps/config-studio/README.md)) | The authoring views. Served by the service once built, or by a hot-reload dev server | `127.0.0.1:4175` for the dev server only |
| Service | Java on Helidon SE with Apache Jena ([README](../../platform/config-studio-service/README.md)) | The HTTP API under `/api`, workspaces and jobs as named graphs, the built browser application, and publishing each job to RabbitMQ | `127.0.0.1:8090` |
| Worker | Python, `lattice_workers.config_studio_main` ([README](../../workers/README.md#configuration-studio-jobs-adr-a136)) | Consumes jobs, validates or compiles the configuration with each layer's own engine, and writes the result back | nothing |
| Transforms worker | Java, with Saxon-HE and JOLT ([README](../../platform/config-studio-transforms/README.md)) | Runs the mapping part's compiled XSLT stylesheets and JOLT chains over an XML or JSON sample source, answering each request on its sender's reply queue. It reads the store and never writes it | nothing |
| Fuseki | Apache Jena Fuseki ([version pinned below](#download-pins)) | The graph store. One dataset, `studio`, in TDB2 on disk | `127.0.0.1:3130` |
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

Read by `StudioConfig.fromEnv`. A blank value counts as unset. `LATTICE_FUSEKI_PASSWORD` and `LATTICE_AMQP_URI` may instead be read from a file (see [Secrets in files](#secrets-in-files)).

| Variable | Default | Meaning |
|---|---|---|
| `LATTICE_STUDIO_PORT` | `8090` | Listening port. A value that is not a number, or outside 0 to 65535, stops the service at start |
| `LATTICE_STUDIO_BIND` | `127.0.0.1` | Bind address. Leave it |
| `LATTICE_STUDIO_AUTH` | `local` | How a request is authenticated (ADR-A149). `local` offers named developer principals with no provider and refuses to start on an address other than loopback. `oidc` validates an OpenID Connect provider's bearer tokens |
| `LATTICE_STUDIO_LOCAL_PRINCIPALS`, `LATTICE_STUDIO_LOCAL_ADMINS` | `developer,reviewer` and `developer` | With `local`, the names a request may give in `X-Lattice-Principal`, the first being a request that gives none, and those who administer |
| `LATTICE_STUDIO_OIDC_ISSUER`, `LATTICE_STUDIO_OIDC_AUDIENCE` | none, required with `oidc` | The provider's issuer, whose discovery document names its keys and endpoints, and the audience a token must name |
| `LATTICE_STUDIO_OIDC_AUDIENCE_CLAIM` | `aud` | The claim that holds the audience. AWS Cognito's access tokens carry it as `client_id` |
| `LATTICE_STUDIO_OIDC_CLIENT_ID`, `LATTICE_STUDIO_OIDC_SCOPE` | the audience, and `openid profile email` | The public client the browser signs in as, by the authorization code flow with PKCE, and the scopes it asks for. Register the studio's address as the client's redirect URI |
| `LATTICE_STUDIO_OIDC_JWKS_URL` | the discovery document's | The provider's published keys |
| `LATTICE_STUDIO_OIDC_NAME_CLAIM` | `sub` | The claim that names the principal |
| `LATTICE_STUDIO_OIDC_ADMIN_CLAIM`, `LATTICE_STUDIO_OIDC_ADMIN_VALUE` | `groups`, and none | A principal administers when the claim holds the value. With no value nobody administers |
| `LATTICE_STUDIO_ASSETS` | `.build/config-studio` | The directory `mise run build:config-studio-assets` fills with `vocabulary.ttl`, `samples.ttl`, `samples/` and `persistence/`, the operations the persistence compiler generated for the studio's store, which the service and the writer both load. A relative path is relative to the directory the service starts in, the repository root |
| `LATTICE_STUDIO_EPOCH` | `1` | The epoch the store's version rows are written at, a whole number from 1. Raise it when the store is restored from a backup, so a row written before the restore cannot be taken for a later one. The service and the writer must have the same value |
| `LATTICE_STUDIO_STATIC` | none | The built browser application, served for any path outside `/api`. The stack sets it to `apps/config-studio/dist`. Without it the service answers `404` outside `/api` |
| `LATTICE_FUSEKI_URL` | none | Fuseki's base URL. Unset means an in-memory dataset inside the service, lost on exit, with a warning in the log |
| `LATTICE_FUSEKI_DATASET` | `studio` | The Fuseki service the service reads through, which cannot update |
| `LATTICE_FUSEKI_USER`, `LATTICE_FUSEKI_PASSWORD` | none | Basic authentication to Fuseki. The stack's Fuseki has none |
| `LATTICE_AMQP_URI` | none | RabbitMQ's URI. Unset means jobs are recorded but never delivered, and stay `cst:Queued`, with a warning in the log, and the service writes the store through a writer of its own, which is for tests and a demonstration only |

### Store writer

Read by `WriterConfig.fromEnv`. The variables are in the [writer's README](../../platform/config-studio-writer/README.md). It also reads `LATTICE_STUDIO_ASSETS` and `LATTICE_STUDIO_EPOCH` as the service does, from the same defaults, and both must agree with the service's.

| Variable | Default | Meaning |
|---|---|---|
| `LATTICE_STUDIO_ASSETS` | `.build/config-studio` | The directory whose `persistence/` folder holds the generated operations the writer runs. A relative path is relative to the directory the writer starts in |
| `LATTICE_STUDIO_EPOCH` | `1` | The epoch the version rows it writes carry, as the service's |

 `LATTICE_FUSEKI_PASSWORD`, `LATTICE_AMQP_URI` and `LATTICE_STREAM_URI` may instead be read from a file (see [Secrets in files](#secrets-in-files)). `studio:up` gives it `LATTICE_FUSEKI_WRITE_DATASET=studio-write`, the stack's AMQP URI, and `LATTICE_STREAM_URI=rabbitmq-stream://guest:guest@127.0.0.1:5553/%2f`. It is the only process given the update service.

### Worker

Read by `config_studio_main.read_config`, and the proposer settings by each proposal job. `LATTICE_AMQP_URI`, `LATTICE_FUSEKI_PASSWORD` and `LATTICE_PROPOSER_KEY` may instead be read from a file (see [Secrets in files](#secrets-in-files)).

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `LATTICE_AMQP_URI` | yes | none | RabbitMQ's URI. Unset, with `LATTICE_AMQP_URI_FILE`, stops the worker at start with `LATTICE_AMQP_URI is required` |
| `LATTICE_FUSEKI_URL` | yes | none | Fuseki's base URL. Unset stops the worker at start |
| `LATTICE_FUSEKI_DATASET` | no | `studio` | The dataset name, which must be the service's |
| `LATTICE_FUSEKI_USER`, `LATTICE_FUSEKI_PASSWORD` | no | none | Basic authentication to Fuseki |
| `LATTICE_ROOT` | no | found from the working directory | The repository root, where the worker reads the ontology files it validates against |
| `LATTICE_PROPOSER_PROVIDER` | no | `chat-completions` | Which language model provider the `language-model` and `mapping-language-model` proposers use. `chat-completions` speaks the Chat Completions wire format to `LATTICE_PROPOSER_URL`. `anthropic` uses Anthropic's Messages API through its SDK, with prompt caching on the conversation, so each turn of a mapping proposal reads the turns before it from the cache. Anything else fails the job. The `sentence-forms` and `rml` proposers need none of these settings |
| `LATTICE_PROPOSER_URL` | for `chat-completions` | none | The endpoint's base URL, to which `/chat/completions` is added. For `anthropic`, it overrides the API's base URL, for example to reach a gateway. Without it, or without the model, a `chat-completions` job fails, saying no language model is configured |
| `LATTICE_PROPOSER_MODEL` | yes, for either proposer | none | The model asked, for example `claude-opus-5-5` |
| `LATTICE_PROPOSER_EFFORT` | no | the model's own | For `anthropic` only, the model's effort: `low`, `medium`, `high`, `xhigh` or `max`. A mapping proposal is a long tool loop, which `high` suits |
| `LATTICE_PROPOSER_PACK` | no | none | For the `language-model` proposer only, the folder of the pack the prompt is rendered from, a `manifest.json` with its templates, as the [contract](../../contracts/config-studio/README.md#proposers) describes. The repository holds no clause-reading pack, so a deployment supplies its own |
| `LATTICE_PROPOSER_KEY` | no | none | The provider's key. Without it, `anthropic` falls back to the SDK's own sources, such as `ANTHROPIC_API_KEY`. Keep it in a secret store and give it to the worker through `LATTICE_PROPOSER_KEY_FILE` (see [Secrets in files](#secrets-in-files)), never in a file the repository tracks. It is never logged |
| `LATTICE_MAPPING_PROPOSER_ROUNDS` | no | `40` | The most turns a mapping proposal gives the model before the job fails |

### Transforms worker

Read by `TransformsMain`. `LATTICE_FUSEKI_URL` and `LATTICE_AMQP_URI` are required, `LATTICE_FUSEKI_DATASET` defaults to `studio`, and `LATTICE_FUSEKI_USER` and `LATTICE_FUSEKI_PASSWORD` are as the worker's. `LATTICE_AMQP_URI` and `LATTICE_FUSEKI_PASSWORD` may instead be read from a file (see [Secrets in files](#secrets-in-files)). `studio:up` gives it the service's values.

### Values the stack sets

`studio:up`, `studio:service` and `studio:worker` all use the same values. The service and the worker must agree on the Fuseki URL and dataset and on the AMQP URI, or jobs are written where the worker does not look.

| Variable | Value |
|---|---|
| `LATTICE_FUSEKI_URL` | `http://127.0.0.1:3130` |
| `LATTICE_FUSEKI_DATASET` | `studio` |
| `LATTICE_AMQP_URI` | `amqp://guest:guest@127.0.0.1:5673/%2F` |
| `LATTICE_STUDIO_STATIC` | `apps/config-studio/dist` (the service only) |

`studio:up` also reads `LATTICE_STUDIO_DATA`, the folder for the store (see [Where things live](#where-things-live)).

The AMQP URI holds RabbitMQ's `guest` password. That is acceptable only because the broker is local and `guest` is its default. Do not put a real credential in it. Give a real one through `LATTICE_AMQP_URI_FILE`.

### Secrets in files

Each secret below may be given as a file instead of a value. Set `NAME_FILE` to the file's path, and the process reads the value from it. Setting both `NAME` and `NAME_FILE` stops the process at start, or fails the job, since one of them would otherwise be ignored. An error names the variable and the path, never the value.

| Secret | Read by | Read |
|---|---|---|
| `LATTICE_PROPOSER_KEY` | the worker | at each proposal job, so a rotated key is used from the next job without a restart |
| `LATTICE_FUSEKI_PASSWORD` | the service, the writer, the worker | at start |
| `LATTICE_AMQP_URI` | the service, the writer, the worker | at start |
| `LATTICE_STREAM_URI` | the writer | at start |

A secret read at start takes a restart of that process to change.

**The file's format.** UTF-8 text holding the value alone, with no name, no `=`, no quotes and no `export`. One trailing line ending, `\n` or `\r\n`, is dropped, so `echo` and most editors are fine, and nothing else is changed, so a leading or trailing space is part of the value. An empty file is refused. A URI is written whole, for example `amqp://studio:<password>@broker.example:5672/%2F`, with any reserved character in the password percent-encoded.

**The file's permissions.** Only the user the process runs as should read it, and nobody should write it but whatever puts the secret there. On Linux or macOS:

```bash
(umask 077 && read -rs key && printf '%s' "$key" > /path/to/proposer.key)
```

```bash
chmod 0400 /path/to/proposer.key
```

The first prompts for the value without echoing it or keeping it in the shell's history, and writes it with `0600` from the start, so no other user can read it even for a moment. The second takes away the owner's own write, leaving `0400`, which lets the owner read it and no one else do anything. Keep `0600` instead if a person edits it by hand. The file must be owned by the user the process runs as (`chown` it if another user wrote it), and its folder should be `0700`, so others can neither list nor replace it. A secret store's own command can write the file in place of the first line. On Windows, remove inherited access and grant only the process's user read, for example `icacls proposer.key /inheritance:r /grant:r "%USERNAME%:R"`. The studio does not check the file's permissions, since a container platform sets them itself, so they are the operator's to set.

**From a secret store.** Every secret store can write a file, so none needs code in the studio. Examples follow.

| Source | How the file is made | Notes |
|---|---|---|
| Docker Compose | a top-level `secrets:` entry with `file:` or `environment:`, listed under the service, appears at `/run/secrets/<name>`. Set `LATTICE_PROPOSER_KEY_FILE=/run/secrets/proposer_key` | A `file:` secret is mounted with the host file's own permissions, so `chmod 0400` it on the host. In Swarm, set `mode: 0400` and `uid` on the service's secret |
| Kubernetes | a `Secret` mounted as a volume, one file per key, for example at `/var/run/secrets/lattice/proposer-key` | The default mode is `0644`. Set `defaultMode: 0400` on the volume, with `securityContext.runAsUser` and `fsGroup` matching the process's user, or the user cannot read it. Prefer a volume to `env.valueFrom.secretKeyRef`, which puts the value back into the environment |
| HashiCorp Vault, Agent | a `template` stanza that renders `{{ with secret "secret/data/lattice/studio" }}{{ .Data.data.proposer_key }}{{ end }}` to a `destination` file, with `perms = "0400"` | The Agent renews its token and renders the file again when the secret changes. The worker reads the proposer key afresh at the next job. Restart the others after a change |
| HashiCorp Vault, CSI | the Secrets Store CSI driver with the Vault provider, a `SecretProviderClass` naming each object's `secretPath` and `secretKey`, mounted as a volume | Set each object's `filePermission` to `0400`. Turning on the driver's rotation updates the file in place |
| A cloud secret manager | its CSI provider, or its agent, writes a file the same way | as for Vault |

Whichever is used, the value should never also be set in `NAME`, a compose file, a manifest or a shell profile. A secret store that can only set an environment variable works too, through `NAME`, at the cost of the value being visible in the process's environment.

---

## Where things live

The workspaces are kept in the data folder, outside the checkout, so they survive `mise run clean`, a new checkout and a removed worktree. Everything else the stack writes is under `.build/config-studio`, which git ignores. Deleting that directory resets the stack but keeps the workspaces (see the runbook).

| Platform | Data folder, unless `LATTICE_STUDIO_DATA` names another |
|---|---|
| macOS | `~/Library/Application Support/LATTICE/studio` |
| Windows | `%LOCALAPPDATA%\LATTICE\studio` |
| Linux | `$XDG_DATA_HOME/lattice/studio`, or `~/.local/share/lattice/studio` |

The store is `tdb2/` in that folder. With `up --docker` it is the volume `studio-data` instead.

| Path | Holds |
|---|---|
| `.build/config-studio/run/{name}.pid` | The process id of `fuseki`, `rabbitmq`, `service`, `worker` or `web`, written when `up` starts it and removed by `down` |
| `.build/config-studio/run/{name}.log` | That process's standard output and error, appended on each start and never rotated |
| `.build/config-studio/run/docker` | Present only after `up --docker`. Holds the compose file's path so `down` knows to stop the containers |
| `.build/config-studio/infra/` | The downloads and what they unpack to |
| `.build/config-studio/infra/jena-fuseki-server-{version}.jar` | The Fuseki release |
| `.build/config-studio/infra/fuseki-base/` | Fuseki's `FUSEKI_BASE` (its working files and logging configuration). The dataset is not stored here |
| `.build/config-studio/infra/rabbitmq/enabled_plugins`, `rabbitmq.conf` | The plugins RabbitMQ enables, the stream plugin, and its configuration: the stream protocol on `127.0.0.1:5553`, advertised there. Both written on each start |
| `.build/config-studio/infra/fuseki-base/studio.ttl` | Fuseki's configuration, written on each start: one TDB2 database in the data folder behind the services `studio`, which reads, and `studio-write`, which updates |
| `.build/config-studio/infra/rabbitmq-server-*` and `rabbitmq_server-{version}/` | The RabbitMQ archive and its unpacked release |
| `.build/config-studio/infra/rabbitmq/mnesia/` | RabbitMQ's data directory (`RABBITMQ_MNESIA_BASE`), holding the node's metadata and any persistent messages |
| `.build/config-studio/infra/rabbitmq/log/` | RabbitMQ's own logs (`RABBITMQ_LOG_BASE`), apart from `run/rabbitmq.log` |
| `.build/config-studio/vocabulary.ttl`, `samples.ttl`, `samples/` | The assets the service reads, staged by `mise run build:config-studio-assets` |
| `apps/config-studio/dist/` | The built browser application |
| `platform/config-studio-service/target/config-studio-service.jar` | The built service |

The service and the worker log to standard output, so their only log is `run/service.log` and `run/worker.log`. A run started in a terminal logs to that terminal. With `up --docker`, the logs of Fuseki and RabbitMQ are the containers' (`docker compose -f deployment/compose/config-studio/docker-compose.yml logs`).

---

## Fuseki

Started as `java -jar jena-fuseki-server-{version}.jar --localhost --port 3130 --config fuseki-base/studio.ttl`.

| Setting | Effect |
|---|---|
| `studio.ttl` | One TDB2 database in the data folder. Each update is committed before Fuseki answers it, so stopping Fuseki loses no saved work, and the next start recovers any update cut off |
| service `studio` | Query and graph store reads only, so an update or a graph store write answers `405`. The service and the worker use it |
| service `studio-write` | Query, update and graph store writes. The store writer alone uses it |
| `--localhost` | Fuseki listens on the loopback address only |
| `FUSEKI_BASE` | `.build/config-studio/infra/fuseki-base` |

The Docker setup builds the same server from `deployment/compose/config-studio/fuseki.Dockerfile` on `eclipse-temurin:25-jre-alpine`, pinned by the same checksum, listening on `3030` in the container, published at `127.0.0.1:3130`, with the database in `/data`, the volume `studio-data`. `docker compose down` keeps the volume, and `docker compose down -v` deletes every workspace.

TDB2 serves reads while a write runs, and applies one write at a time per dataset. A deleted workspace or job frees no disk space until the database is compacted, which the studio does not do yet. To back up, export each workspace from the browser, or copy the data folder while Fuseki is stopped. To start afresh, stop the stack and delete the data folder.

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
| `RABBITMQ_ENABLED_PLUGINS_FILE` | `.build/config-studio/infra/rabbitmq/enabled_plugins` | Enables `rabbitmq_stream`, which the writes super stream needs |
| `RABBITMQ_CONFIG_FILE` | `.build/config-studio/infra/rabbitmq/rabbitmq.conf` | The stream protocol on `127.0.0.1:5553`, advertised as `127.0.0.1:5553`, so the writer reaches each partition's leader there |
| `ERLANG_HOME` | the parent of the directory holding `erl` | RabbitMQ's scripts find Erlang from it. The stack derives it from `erl` on the path, and stops with "RabbitMQ needs Erlang" if there is none |

RabbitMQ runs on the Erlang mise installs, so start it through `mise`. The user is the default `guest` with password `guest`, in virtual host `/` (written `%2F` in the URI). The Docker setup mounts `rabbitmq-stream.conf`, which listens for streams on `5552` in the container, published at `127.0.0.1:5553` and advertised as `localhost:5553`, and `fuseki-studio.ttl`, the same two services over `/data`. It runs `rabbitmq:4.4-management-alpine` with `guest`/`guest` set explicitly, and publishes the AMQP port at `127.0.0.1:5673` and the management interface at `127.0.0.1:15673`. It mounts `deployment/compose/config-studio/enabled_plugins`, which keeps the image's own plugins and adds the stream plugin.

### Topology

Declared identically, and idempotently, by the service when it connects and by the worker when it starts, from [`amqp-topology.json`](../../contracts/config-studio/amqp-topology.json).

| Kind | Name | Notes |
|---|---|---|
| Exchange | `lattice.studio` | topic, durable |
| Exchange | `lattice.studio.dlx` | topic, durable. The dead-letter exchange |
| Queue | `lattice.studio.jobs` | durable. Bound to `lattice.studio` with key `lattice.studio.jobs`. Dead-letters to `lattice.studio.dlx` |
| Queue | `lattice.studio.transforms` | durable, with no dead-lettering. Bound to `lattice.studio` with key `lattice.studio.transforms`. Each request expires when the service stops waiting for it, after 30 seconds |
| Queue | `lattice.studio.dead` | durable. Bound to `lattice.studio.dlx` with key `#` |
| Super stream | `lattice.studio.writes` | a direct exchange with `x-super-stream`. A write's routing key is its workspace's partition, `0` to `7` |
| Streams | `lattice.studio.writes-0` to `-7` | one per partition, bound with `x-stream-partition-order`, keeping a week or 1 GiB. Consumed by the group `lattice.studio.writers` with a single active consumer per partition |

A message is the job's IRI (`urn:lattice:studio:job:` and a lower-case UUID) in UTF-8, persistent, published with a broker confirm and a five-second timeout. The worker consumes with manual acknowledgement and one message in flight at a time (`prefetch_count=1`), and acknowledges only after the broker has confirmed the final job graph's `job-update`. The writer that applies it is the service's.

| Worker outcome | Broker action |
|---|---|
| Job run, whatever its result | Acknowledged |
| Message that is not a job IRI, or names a job graph that does not exist | Rejected without requeue, so it moves to `lattice.studio.dead` |
| Any other error, such as Fuseki being unreachable | Rejected with requeue, and the worker stops with the error |

A store writer holds the partitions RabbitMQ gives it. It applies what waits for it in one request, replies to each write the service sent, then stores each partition's offset. It logs a write it refuses and passes over it, since a stream has no dead letters. If the store cannot take a batch, the writer retries it each second, holding its partitions in order. The service waits 10 seconds for a reply and then reads the write's receipt, answering `503` only when it finds none. To see which writer holds which partition: `mise exec -- $RMQ/rabbitmq-streams -n studio@localhost list_stream_group_consumers --stream lattice.studio.writes-0 --reference lattice.studio.writers`.

A job that fails because its configuration did not validate or compile is not an error. It is a `cst:Succeeded` job whose report says so. A `cst:Failed` job is one that could not run, such as a missing input graph.

---

## Starting

### Everything, in the background

```bash
mise run studio:up
```

This stages the assets, then for each of Fuseki and RabbitMQ downloads the release if it is not already in `.build/config-studio/infra` (checking its SHA-256), starts it, and waits up to 180 seconds for its port. If the port is already listening it prints "already listening" and starts nothing. It then builds the browser application with Yarn, builds the service with Maven, starts the service and waits for `8090`, and starts the worker and the transforms worker. It prints the address, `http://127.0.0.1:8090`.

The first run downloads about 80 MB (Fuseki's jar and RabbitMQ's archive) and builds the browser application and the service, so it is slow. Later runs reuse the downloads.

| Command | Effect |
|---|---|
| `mise run studio:up` | The downloaded Fuseki and RabbitMQ, the built browser application served by the service on `8090` |
| `mise run studio:up -- --docker` | Fuseki and RabbitMQ from `docker compose` instead of downloads. Needs Docker. Waits for both containers to be healthy |
| `mise run studio:up -- --dev` | Also the browser code with hot reload on `4175`, proxying `/api` to the service. The browser application is not built. Browse `http://127.0.0.1:4175` |
| `mise run studio:status` | Per part, the process id if its pid file names a live process, and whether its port is listening |
| `mise run studio:down` | Stops what `up` started, in the order the web server, transforms worker, worker, service, RabbitMQ and Fuseki |

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
mise run studio:transforms
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

On Windows a detached console process can receive no termination request, so after `rabbitmqctl shutdown` has stopped RabbitMQ the script ends the process tree at once with `taskkill /T /F`. That loses nothing. TDB2 commits each update before Fuseki answers it, and recovers on the next start. The service keeps no state outside the store, and a write a writer had not acknowledged is redelivered. A job the worker had not acknowledged is redelivered, and running a job twice gives the same graph but for its times.

`down` removes a pid file whose process has gone and says nothing for it. A part that was never started here is skipped.

---

## Migrating a store written before phase D

A store written before the store writer ran on generated persistence operations holds its workspaces and the registry in the old layout. Migrate it once, with the writer and the service stopped and Fuseki running.

```bash
mise run studio:migrate -- --dry-run
mise run studio:migrate
```

The dry run writes nothing and prints what each workspace, the registry and the imports would move. The real run first writes every graph of the dataset as TriG to `migration-backup-{UTC time}.trig` in `LATTICE_STUDIO_ASSETS`, prints its path, and stops if it cannot write it. It then moves each workspace in one request, so a workspace moves whole or not at all, then the registry, then the imports no workspace held, and drops the old graphs, the workspaces' jobs and their graphs. A workspace's receipts stay.

To restore, stop Fuseki, empty the dataset (or create a new one) and load the backup into it, for example with `tdb2.tdbloader --loc <dataset directory> <backup>.trig`. The command is idempotent. It moves only the old graphs it finds, so a second run finds none, changes nothing and writes no backup.

---

## The MCP server

The service is also an MCP server, at `http://127.0.0.1:8090/mcp` over the Streamable HTTP transport, as the [contract](../../contracts/config-studio/README.md#mcp) describes. An MCP host reads a workspace's clauses and proposes their stated meaning with its own model, and each proposal waits in the Meaning view for a person to decide. It needs nothing configured, since the host brings the model. To connect Claude Code, for example:

```bash
claude mcp add --transport http lattice-studio http://127.0.0.1:8090/mcp
```

A host that speaks MCP over stdio only reaches it through a bridge from stdio to Streamable HTTP. The server accepts requests from `localhost` origins only and, like the rest of the service, authenticates no one, so it is for a studio on the author's own machine.

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
| Topology and workers | `mise exec -- .build/config-studio/infra/rabbitmq_server-4.4.0/sbin/rabbitmqctl -n studio@localhost list_queues name messages consumers` | `lattice.studio.jobs` and `lattice.studio.transforms` each with `consumers` 1, and `messages` 0 when idle. `consumers` 0 means no worker, or no transforms worker, is connected, and a transform then answers `504` |

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

The Configuration Studio authenticates every request but `/api/health` and `/api/session`, which describes how to sign in. By default it is a tool for one machine, whose developers pick a name. **Exposing it on a network needs `oidc`, TLS in front of it, and a broker and store that listen on loopback or are otherwise protected.**

| Aspect | State |
|---|---|
| Authentication | `local` by default, which trusts the name a request gives and is allowed on loopback only, or `oidc`, which accepts a bearer token whose signature the provider's published keys verify with an asymmetric algorithm, naming the configured issuer and audience, unexpired. Every write carries its principal to the writer, which records it on the receipt. Fuseki and RabbitMQ still accept any client that reaches them |
| Authorisation | A workspace's creator owns it and sets its mode: `locked`, read and written by its owner and administrators only, `read-only`, read by everyone signed in and written by its owner and administrators, or `shared`, read and written by everyone signed in. A workspace from before modes has no owner and is shared until an administrator gives it one with `POST /api/workspaces/{ws}/access?mode=…&owner=…`. The service hides what a principal may not read, and the writer refuses a write the mode does not allow, whatever the service checked |
| Network exposure | Every listener is bound to `127.0.0.1`. Fuseki has `--localhost`, RabbitMQ has `RABBITMQ_NODE_IP_ADDRESS=127.0.0.1`, and Docker publishes each port at `127.0.0.1`. Changing `LATTICE_STUDIO_BIND` opens the service, and nothing else protects it |
| RabbitMQ user | The default `guest`/`guest`, which RabbitMQ accepts from the loopback address only, and the node listens on loopback alone. In Docker the container's own network is not loopback to the broker, so the compose file sets `loopback_users []` and relies on the loopback-only port publication instead |
| Transport | Plain HTTP and plain AMQP. No TLS |
| Cross-origin | No response carries `Access-Control-Allow-Origin`, so a page on another origin cannot read the API from a browser. This is not authentication, because the browser's same-origin rule does not stop a request from the local machine or a forged request |
| Request validation | The service validates every request: content type (Turtle or RDF/XML, else `415`), body size (5 MiB, else `413`), syntax (else `400`), every identifier in a path, the revision a save expects (`If-Match`, else `428` or `412`), and that a saved graph holds only its own part's subjects (`422`). RDF/XML that declares a DTD is refused, which prevents external entities |
| Response headers | `X-Content-Type-Options: nosniff` on every response. `Cache-Control: no-store` on every `/api` response except the vocabulary, which is revalidated by its `ETag`. `Referrer-Policy: no-referrer` on every response. On an HTML response, `Content-Security-Policy: default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'`, which allows no scripts from elsewhere and no framing |
| Static files | The service resolves a requested file to its real path and serves it only if it is a regular file under `LATTICE_STUDIO_STATIC`, so a `..` or a link out is refused |
| Errors | An unexpected error returns `500` with the text `internal error` and logs the detail to the service log, not to the client |
| Secrets | The AMQP and stream URIs, the Fuseki password and the proposer key are read from the environment or from a file it names ([Secrets in files](#secrets-in-files)). A value in the environment is visible to anyone who can read the process's environment, and a file only to whom its permissions allow. The local stack's compose file has the broker's default `guest` password in the clear |

Reaching it from another machine needs `oidc`, TLS and a protected broker and store. The studio terminates no TLS itself.
