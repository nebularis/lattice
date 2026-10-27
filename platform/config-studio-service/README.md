<!-- SPDX-License-Identifier: MPL-2.0 -->

# Configuration Studio service

The HTTP service of the Configuration Studio, a proof of concept ([ADR-A136](../../docs/architecture/decisions/ADR-A136-configuration-studio.md)). It keeps workspaces and jobs as named graphs in a Jena dataset, serves them as Turtle, and publishes each job's IRI to RabbitMQ for the [worker](../../workers/README.md#configuration-studio-jobs-adr-a136). It never interprets `dal:` or `srf:`. Nothing outside the studio may depend on it. The routes, graphs and messages are in [contracts/config-studio/README.md](../../contracts/config-studio/README.md).

The HTTP server is the JDK's `com.sun.net.httpserver` on virtual threads. The only dependencies are Jena (`jena-arq`, `jena-rdfconnection`) and the RabbitMQ client.

## Packages

All under `org.nebularis.lattice.studio`.

| Package | Holds |
|---|---|
| `store` | `StudioStore` over Jena's `RDFConnection`, in memory or on Fuseki, the graph IRIs and the `cst:` terms |
| `jobs` | `JobBus`, `RabbitJobBus`, the recording bus for tests and `Topology`, the declared exchange and queues |
| `api` | `StudioApi`, every rule of the contract with no HTTP framework, and the Turtle reader and writer |
| `http` | `StudioHttpServer`, which adapts the JDK server to `StudioApi`, serves the built SPA and adds the security headers |
| `app` | `StudioConfig` and `StudioMain` |

## Environment

| Variable | Default | Meaning |
|---|---|---|
| `LATTICE_STUDIO_PORT` | `8090` | listening port |
| `LATTICE_STUDIO_BIND` | `127.0.0.1` | bind address |
| `LATTICE_STUDIO_ASSETS` | `.build/config-studio` | the directory `tools/config_studio_stage.py` fills with `vocabulary.ttl`, `samples.ttl` and `samples/` |
| `LATTICE_STUDIO_STATIC` | none | directory of the built SPA, served for paths outside `/api` |
| `LATTICE_FUSEKI_URL` | none | Fuseki base URL. Absent means an in-memory dataset |
| `LATTICE_FUSEKI_DATASET` | `studio` | dataset name |
| `LATTICE_FUSEKI_USER`, `LATTICE_FUSEKI_PASSWORD` | none | basic authentication |
| `LATTICE_AMQP_URI` | none | RabbitMQ URI. Absent means jobs are recorded, never delivered, and stay `cst:Queued` |

## Build and test

```bash
mise run build:config-studio-assets
mise exec -- mvn -q -f platform/pom.xml -pl config-studio-service -am verify
mise exec -- java -jar platform/config-studio-service/target/config-studio-service.jar --self-check
```

The first stages the vocabulary and samples. The second builds and runs the 29 tests, in memory with no containers. The third serves one request in memory and exits 0. `mise run check:config-studio` runs these with the rest of the studio's tests.

## Run it

`mise run studio:up` starts the whole stack in the background on every platform, and `mise run studio:down` stops it. `up` downloads Fuseki and RabbitMQ once into `.build/config-studio/infra`, refusing either unless its SHA-256 is the one `tools/config_studio_stack.py` pins, then builds and starts the service and the worker and serves the studio on <http://127.0.0.1:8090>. `mise run studio:up -- --docker` runs Fuseki and RabbitMQ with the compose file instead, and `-- --dev` adds the browser code with hot reload on <http://127.0.0.1:4175>. `mise run studio:status` shows what is running. Logs and process ids are in `.build/config-studio/run`.

`down` stops each process through its own shutdown. RabbitMQ is stopped with `rabbitmqctl shutdown`, which waits for the node to stop its applications and its metadata store. Fuseki, the service, the worker and the dev server get a termination request (SIGTERM) and up to a minute to stop: the service's shutdown hook closes its HTTP server, AMQP connection and store, and the worker finishes the job in hand and closes its connection. Windows has no termination request a detached console process can receive, so there the last four are stopped at once, which loses nothing: Fuseki holds an in-memory dataset, the service holds no state outside the store, and a job the worker had not acknowledged is redelivered.

To run each part in its own terminal instead, as below.

The studio needs Fuseki on `127.0.0.1:3130` with an updatable dataset `studio`, and RabbitMQ on `127.0.0.1:5673` with its default `guest` user, which RabbitMQ accepts from the loopback address only. The compose file lets `guest` in from the container network, since the host is not loopback there.

With Docker:

```bash
mise run studio:infra
```

Without Docker, from the Apache Jena release of Fuseki on Maven Central (`org.apache.jena:jena-fuseki-server`, checked against its `.sha1`) and RabbitMQ's generic Unix release (checked against the SHA-256 GitHub publishes), which runs on the Erlang mise installs:

```bash
mise exec -- java -jar jena-fuseki-server-6.2.0.jar --localhost --port 3130 --mem --update /studio
```

```bash
RABBITMQ_NODE_IP_ADDRESS=127.0.0.1 RABBITMQ_NODE_PORT=5673 RABBITMQ_DIST_PORT=25673 mise exec -- rabbitmq_server-4.4.0/sbin/rabbitmq-server
```

Then the service, the worker and the browser application, each in its own terminal, and browse <http://127.0.0.1:4175>:

```bash
mise run studio:service
```

```bash
mise run studio:worker
```

```bash
mise run studio:web
```

`studio:service` also serves the built application on <http://127.0.0.1:8090> once `mise exec -- yarn workspace @lattice/config-studio run build` has run.
