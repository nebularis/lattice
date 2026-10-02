# Word authoring POC stack (ADR-A114)

A standalone Docker Compose stack for the word authoring proof of concept (plan WA10). It is
separate from the root [`deployment/compose/docker-compose.yml`](../docker-compose.yml) dev stack
and uses different host ports, so the two can run side by side.

## Services

| Service | Image | Purpose | Host port (127.0.0.1 only) |
|---|---|---|---|
| `fuseki` | `stain/jena-fuseki:5.1.0` | Wording, proposal and analysis graphs | 3130 → 3030 |
| `rabbitmq` | `rabbitmq:3.13-management-alpine` | `wording-analysis-request`/`-result` events | 5673 → 5672, 15673 → 15672 (management UI) |
| `authoring-service` | built from [`service.Dockerfile`](service.Dockerfile) | The Java authoring API ([`platform/authoring-service`](../../../platform/authoring-service)) | 8088 → 8080 |
| `authoring-worker` | built from [`worker.Dockerfile`](worker.Dockerfile) | The Python wording analysis worker ([`workers`](../../../workers)) | none (internal only) |
| `authoring-proxy` | `caddy:2.10-alpine` | TLS termination (local CA) and static add-in hosting | 3443 → 3443 |

`authoring-service` seeds the three samples on startup (`LATTICE_AUTHORING_SEED_SAMPLES=true`),
each analysed automatically by the worker within a few seconds of the stack becoming healthy.

## Volumes

| Volume | Holds |
|---|---|
| `authoring-fuseki` | The Fuseki dataset, across restarts and `authoring:down` |
| `authoring-caddy-data` | Caddy's local CA and its issued certificate |

`mise run authoring:reset` (`docker compose down -v`) deletes both, including the local CA — a
browser that trusted the old CA will need to trust the new one after a reset.

## Commands

All commands run from the repository root, via `mise`:

| Command | Does |
|---|---|
| `mise run build:authoring` | Builds the service jar, builds the add-in, stages `.build/authoring/{service,worker,addin}` |
| `mise run authoring:up` | `build:authoring`, then `docker compose up -d --build --wait` |
| `mise run authoring:down` | `docker compose down` (keeps volumes) |
| `mise run authoring:reset` | `docker compose down -v` (deletes volumes, including the local CA) |
| `mise run authoring:ca` | Copies the proxy's local root certificate to `.build/authoring/lattice-authoring-root.crt` |
| `mise run check:authoring-stack` | `authoring:up`, then runs the Playwright suite in [`apps/word-authoring-addin/e2e-stack`](../../../apps/word-authoring-addin/e2e-stack) against the real stack |

## Browsing the demo

Browse to `https://localhost:3443`. It redirects to `/addin/harness.html`, a browser-only stand-in
for the real Word task pane — no `Word` object model, its left-hand "Document" panel holds the
in-memory model instead of a Word document — that talks to the real `authoring-service` over the
same proxy. This is not the real Word add-in. Loading the add-in inside real Word requires
sideloading `apps/word-authoring-addin/manifest/manifest.xml`, which is a separate step (plan
WA11), not provided by this stack.

The proxy's TLS certificate is issued by Caddy's own local CA, untrusted by your browser by
default. Either accept the browser's certificate warning, or run `mise run authoring:ca` and trust
`.build/authoring/lattice-authoring-root.crt` in your OS or browser certificate store first.

## Content-Security-Policy note

The proxy's `script-src` directive includes `'unsafe-eval'`, needed because the add-in's bundled
AJV JSON Schema validator compiles validators via `new Function` at runtime. Every other directive
stays restrictive (`default-src 'self'`, no `unsafe-inline` for scripts, `connect-src 'self'`).
