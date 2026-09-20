I’d use **`mise` as the top-level developer tool/runtime manager**, plus **VS Code Dev Containers as the canonical fallback/reproducible environment**. Keep Yarn, Maven, pip, Paket, and Mix as the package managers for their own sub-projects; don’t try to replace them with one universal dependency manager.

In short:

> **Top-level orchestration:** `mise`  
> **Per-language package managers:** Yarn / Maven / pip / Paket / Mix  
> **Canonical cross-platform environment:** `.devcontainer` + Docker Compose  
> **Windows recommendation:** work inside WSL2 for the repo, not directly from `C:\...`

`mise` is a good fit because it manages tool versions, environment variables, and tasks from a committed `mise.toml`; it works across macOS, Linux, and Windows, and it can run tasks with the project’s configured environment. It also supports shells including PowerShell and can install tools from multiple backends. ([mise.en.dev](https://mise.en.dev/?utm_source=openai))

## Recommended model

### 1. Put this at the repo root

```toml name=mise.toml
[tools]
java = "21"
maven = "3.9.x"
node = "22.x"
python = "3.11.x"
dotnet = "8.x"
erlang = "27.x"
elixir = "1.17.x"

# Optional if you use these directly
# "pipx:poetry" = "latest"
# "pipx:pre-commit" = "latest"

[env]
MAVEN_OPTS = "-Dstyle.color=always"
PYTHONUNBUFFERED = "1"

[tasks.bootstrap]
description = "Install all toolchains and package-manager dependencies"
run = [
  "mise install",
  "corepack enable",
  "yarn install --immutable",
  "mvn -q -N wrapper:wrapper || true",
  "python -m pip install --upgrade pip",
  "python -m pip install -r requirements.txt",
  "dotnet tool restore || true",
  "mix local.hex --force",
  "mix local.rebar --force"
]

[tasks.check]
description = "Run repo-level validation"
depends = [
  "check:python",
  "check:java",
  "check:frontend",
  "check:dotnet",
  "check:elixir"
]

[tasks."check:python"]
run = "python -m pytest"

[tasks."check:java"]
run = "mvn verify"

[tasks."check:frontend"]
run = "yarn workspaces foreach -A run test"

[tasks."check:dotnet"]
run = "dotnet test"

[tasks."check:elixir"]
run = "mix test"
```

Adjust the exact versions and task paths to match `nebularis/lattice`.

### 2. Let `mise` install tools, not own project dependencies

Use `mise` for:

- Java version
- Maven version, if not relying solely on Maven Wrapper
- Node version
- Python version
- .NET SDK version
- Erlang / Elixir versions
- repo-level tasks
- environment variables

Keep these as the actual dependency authorities:

| Area | Keep using |
|---|---|
| React / TypeScript | Yarn workspaces + `yarn.lock` |
| Java | Maven + Maven Wrapper + `pom.xml` |
| Python | pip / venv / requirements or pyproject lock strategy |
| F# / .NET | Paket + `paket.lock` |
| Elixir / Erlang | Mix + `mix.lock` |
| Services | Docker Compose |
| Repo orchestration | `mise run ...` |

For Yarn specifically, I’d use **Corepack** rather than globally installing Yarn. Corepack is intended to provide Yarn/pnpm/npm binaries based on the project configuration, and Yarn’s own docs recommend Corepack instead of `npm install -g yarn`. ([github.com](https://github.com/nodejs/corepack/blob/main/README.md?utm_source=openai))

Add this to the root `package.json`:

```json name=package.json
{
  "private": true,
  "packageManager": "yarn@4.6.0",
  "workspaces": [
    "apps/*",
    "packages/*"
  ]
}
```

Use whatever Yarn version you standardize on.

## Windows/macOS/Linux strategy

I would support **two developer modes**.

### Mode A: Native mode

Best for macOS and Linux, and acceptable for Windows when the task is mostly frontend, Java, or .NET.

```bash
mise install
mise run bootstrap
mise run check
```

On Windows, `mise` is available, but backend/tool support can vary by platform; the docs note that some asdf-shell plugins are Unix-only and that backend support differs on Windows. ([mise.jdx.dev](https://mise.jdx.dev/faq.html?utm_source=openai))

So I would not make native Windows the only blessed path for the whole monorepo.

### Mode B: Canonical dev-container mode

Best for CI parity, RabbitMQ/PostgreSQL/Fuseki work, Python worker work, and anything involving Unix-leaning tooling.

Use:

```text
.devcontainer/
deployment/docker-compose.yml
mise.toml
```

VS Code Dev Containers work with Docker Desktop on Windows/macOS/Linux, and the VS Code docs specifically support the Windows pattern of WSL2 + Docker Desktop WSL backend + source stored inside WSL. ([code.visualstudio.com](https://code.visualstudio.com/docs/devcontainers/containers?utm_source=openai))

For Windows, make this the documented happy path:

```text
\\wsl$\Ubuntu\home\<user>\src\lattice
```

not:

```text
C:\Users\<user>\src\lattice
```

That avoids a lot of file-watching, path, symlink, and performance pain.

## Why I would not start with Nix as the default

Nix, Devbox, or devenv can give stronger reproducibility than `mise`. Nix-style shells are designed for portable development environments across Linux, macOS, and WSL. ([wiki.nixos.org](https://wiki.nixos.org/wiki/Nix_Installation_Guide?utm_source=openai))

But for your repo, I would treat that as **Phase 2 infrastructure**, not the first answer, because:

- you already have multiple existing package ecosystems;
- your agents are supervised in VS Code;
- Windows is already WSL/Docker-backed;
- you need contributors to onboard without learning Nix first;
- you need to preserve independent Python, Maven, Yarn, Paket, and Mix workflows.

So:

> Start with `mise` + lockfiles + dev containers.  
> Consider Devbox/Nix later if you need stronger hermetic builds.

## Suggested repository additions

```text name=repo-layout.txt
nebularis/lattice/
  mise.toml
  .devcontainer/
    devcontainer.json
    Dockerfile
  deployment/
    docker-compose.yml
  package.json
  yarn.lock
  .yarnrc.yml
  platform/
    pom.xml
    .mvn/
  workers/
    pyproject.toml
    requirements.lock
  mork/
    mix.exs
    mix.lock
  legacy-dotnet/
    paket.dependencies
    paket.lock
    dotnet-tools.json
  docs/
    developer/
      getting-started.md
      toolchain.md
      windows-wsl.md
```

## Practical bootstrapping flow

Document one root command:

```bash name=bootstrap.sh
mise run bootstrap
```

And one root validation command:

```bash name=check.sh
mise run check
```

For Windows docs, I’d explicitly say:

```powershell name=windows-bootstrap.ps1
wsl
cd ~/src/lattice
mise install
mise run bootstrap
```

Avoid making Windows users run half the tools in native PowerShell and half inside WSL. That split is where mono-repos become painful.

## My final recommendation

Use this stack:

1. **`mise`** for top-level toolchain installation, version pinning, environment variables, and repo-level task orchestration.
2. **Yarn via Corepack** for React workspaces.
3. **Maven Wrapper** for Java builds, with Java 21 pinned by `mise`.
4. **pip/venv or your existing Python lock workflow** for Python, with Python pinned by `mise`.
5. **Paket via .NET local tools** for F#.
6. **Mix** for Elixir/Erlang.
7. **Docker Compose** for PostgreSQL, RabbitMQ, Fuseki, Keycloak, and other services.
8. **VS Code Dev Containers** as the canonical environment for Windows/WSL and CI-like development.

That gives you a pragmatic “meta package manager” without fighting the package managers each ecosystem already expects.