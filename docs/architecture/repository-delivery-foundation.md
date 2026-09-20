<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Repository Delivery Foundation

Phase 0 establishes repeatable entry points without replacing language-native build systems. The configuration is deliberately thin. It selects compatible tools and exposes repository tasks, while each project retains authority over its dependencies and lockfiles.

## Components

- `mise.toml` selects Java 21, Maven 3.9, Node 22, Python 3.11, Erlang 27, and Elixir 1.17. Its tasks invoke native package managers and checks.
- Root `package.json`, `.yarnrc.yml`, and `yarn.lock` reserve the Yarn workspace for `apps/*` and `packages/*`.
- Root `pyproject.toml` and `requirements-lock.txt` retain ontology validation dependencies. `workers/pyproject.toml` is a separate deployable Python package.
- `platform/pom.xml` is the Java reactor. Its modules do not change the existing ontology or Python compiler layout.
- `.devcontainer/` and `deployment/compose/docker-compose.yml` define the reproducible service-backed environment. PostgreSQL, RabbitMQ, and Fuseki are reference services. The OCI registry profile is optional reference tooling.
- `.github/workflows/platform.yml` runs native checks in CI. It is the evidence-producing validation path, not architecture documentation.

## Bootstrap and Validation Flow

```text
mise install
  -> selects toolchains
mise run bootstrap
  -> invokes native dependency installation
mise run check
  -> invokes Python, worker, Maven, Yarn, and Mix checks
```

`mise` does not own dependency resolution. For example, Corepack selects the pinned Yarn binary, Maven resolves its own reactor dependencies, and Python installs from the project manifests and lock constraints.

## Environment Boundaries

Use WSL2 plus Docker Desktop for container-backed work on Windows. Store the repository in the Linux filesystem. The Compose configuration is development reference infrastructure. It does not represent production credential policy, image retention, backup, or deployment topology.

## Extension Rules

New modules add a native manifest and lockfile where their ecosystem supports one, then add a scoped `mise` task and CI check. New services add an explicit Compose profile, ports, health checks, fixture needs, and teardown instructions. Any durable toolchain, CI, or environment decision requires an ADR under the plan's documentation discipline.
