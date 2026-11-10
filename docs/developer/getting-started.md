<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Getting Started

From a clean clone to a passing `mise run check`. For what each tool actually does, see the [Developer Guide](https://github.com/nebularis/lattice/blob/main/docs/developer/developer-guide.md). For how formal methods fits in, see [Formal Methods in the Development Lifecycle](https://github.com/nebularis/lattice/blob/main/docs/developer/formal-methods-lifecycle.md).

## 1. Prerequisites

- **`mise`** — the one task-orchestration entry point (ADR-A29). Install it from [mise.jdx.dev](https://mise.jdx.dev), then activate it for your shell.

  **PowerShell (Windows):** add `mise activate pwsh | Out-String | Invoke-Expression` to
  `$PROFILE`. On Windows PowerShell 5.1 (not PowerShell 7+), also set `$env:MISE_PWSH_CHPWD_WARNING = "0"` first in your profile, to silence an unsupported-feature warning that otherwise prints on every new session.

  **bash/zsh:** add `eval "$(mise activate bash)"` (or `zsh`) to your shell's rc file.

  Verify with a **brand-new shell**, not the one you installed `mise` in — that proves the profile change actually works, rather than relying on a PATH edit that only applies to the current session.

- **A C toolchain** (optional), only if you preview the documentation site with `mise run bootstrap:jekyll` and `mise run serve:jekyll`. Several of the site's gems build native extensions. On macOS that is the Xcode Command Line Tools (`xcode-select --install`), on Debian or Ubuntu the `build-essential` package, and on Windows MSYS2 with its MINGW toolchain, installed by running `ridk install` through mise (`mise exec ruby@3.4 -- ridk install`) and choosing options 1 and 3.
- **Docker** (optional), only if you plan to run `deployment/compose` or build the formal-methods toolchain spike's portable images (`mise run bootstrap:formal-images`).
- **An extra root CA**, if your network intercepts TLS: several tools need it set explicitly rather than relying on the OS trust store (Node via `NODE_EXTRA_CA_CERTS`, `pip` via its own `pip.ini`/`pip.conf` pointed at an approved internal mirror). This is environment- specific — ask whoever administers your network's egress policy, never hard-code a mirror URL into a file this repository tracks.

Everything else — Java 25, Maven 3.9, Node 22, Python 3.14, Erlang 27, Elixir 1.17 — is pinned in `mise.toml`'s `[tools]` section and installed by `mise install`, not by you.

## 2. Clone and install the pinned toolchain

```bash
git clone https://github.com/nebularis/lattice.git
cd lattice
mise install
```

`mise install` reads `mise.toml`'s `[tools]` section and installs exactly those versions, independent of whatever else is on your machine. If a shim reports "program not found" immediately after installing `mise` itself, the real `mise` binary likely isn't on `PATH` yet in your current shell — open a new one (see §1).

## 3. Bootstrap every package's dependencies

```bash
mise run bootstrap
```

This runs every `bootstrap:*` task: the root ontology-validation dependencies, every `tools/*` Python package (editable installs, so an edit takes effect immediately with no reinstall), the worker package, and the Yarn workspace via Corepack. It does **not** install the formal-methods toolchains (Isabelle, Rocq, Alloy) or Jekyll — those are optional, heavy, and bootstrapped separately (§5).

**If a `pip install` fails with a hash mismatch you didn't ask for** (no `-c` hash-pinned requirements file given, yet pip reports "THESE PACKAGES DO NOT MATCH THE HASHES"), this is very likely a network policy block substituting a notice page for the real wheel, not a corrupted download — confirm by fetching the failing wheel URL directly and inspecting the response body. Fix it at the package-manager configuration level (an approved internal mirror), never by editing a file this repository tracks.

## 4. Validate the install

```bash
mise run check
```

Runs every validation task that does not need a heavy, optional toolchain (§5): every `tools/*` package's own tests, the Maven reactor, the frontend workspace, the Erlang/Elixir SPC suite, every repository-wide ontology gate (catalog, versioning, import guard, reasoning isolation), and the formal-methods freshness check. A clean run here is the first-time-install's acceptance test.

Run one piece instead of everything with `mise run check:<name>` — `mise tasks` lists every task with its own description. `mise run check:python-root` alone, for instance, runs Surface and MORK's own compiler test suites plus the shared Phase 8 conformance corpus.

## 5. Optional: the formal-methods toolchains

Not part of `bootstrap`/`check` by default — large, native, and only needed if you are working on formal-methods track C, D or E (see the [lifecycle guide](https://github.com/nebularis/lattice/blob/main/docs/developer/formal-methods-lifecycle.md)):

```bash
# Track E: Isabelle/HOL, native install on macOS, Linux or Windows (about 1.2 GB, prebuilt HOL
# heap included). Installs under LATTICE_FORMAL_ROOT, default ~/.local/share/lattice-formal
# (C:/fmx on Windows, where a short path avoids path-length limits)
mise run bootstrap:formal-native-isabelle
mise run check:proofs

# Track C: Alloy Analyzer, a single MIT-licensed JAR, any OS with a JDK
# (download org.alloytools.alloy.dist.jar from the AlloyTools GitHub releases; see
# tools/models/README.md for the exact command)

# Track D: the prover spike's portable route (Docker required)
mise run check:formal-network    # confirm the toolchain's own sources are reachable first
mise run bootstrap:formal-images
mise run check:formal-smoke
```

## 6. Set up the knowledge index and the work board

`mise run bootstrap` installs Вивід, `vyd`, as a `uv` tool at the version `mise.toml` pins ([ADR-A152](../architecture/decisions/ADR-A152-vyvid-adoption.md)). It writes no configuration of yours, and the index, the work board and the composed skills need one. A first local setup is five steps, from the repository's root.

1. **Write a first configuration.** `vyd setup` reads the domains `vyvid.toml` names, sets the knowledge base's folder in your own configuration, adds each published domain you lack with trust `knowledge`, and clones them. Look first with `--dry-run`.

   ```bash
   mise run vyd -- setup --dry-run
   mise run vyd -- setup
   ```

2. **Trust `vyvid.toml`.** The file declares a command that builds the index's owners and glue, which run with your privileges, so you read what it lists and type `yes`. The command asks a question, so run it yourself and not through a task. A task that captures output would hide the question, and `vyd` refuses at once and says so.

   ```bash
   mise exec -- vyd trust
   ```

3. **Review each domain you will rely on.** A domain added with trust `knowledge` gives an index and a board and gives agents no skills, so `mise run check:skills` does not run, and says which domains it is waiting for, until you review each of them: `lifecycle`, `tools`, `python`, `triple-stores` and `rdf-modelling`. `vyd setup` printed each one's folder and its review line at the commit it cloned. Read a domain's rules and skills in its clone, then run its line.

   ```bash
   mise exec -- vyd domain trust lifecycle reviewed --commit <the commit your setup printed>
   ```

   A new commit of a domain needs a new review, which is `vyd domain trust` again.

4. **Build the index.** The first build fetches an embedding model, and later ones take seconds.

   ```bash
   mise run build:knowledge
   ```

5. **Ask the index and the board.**

   ```bash
   mise run graph:ask -- find how do we name a new ontology term
   mise run work:board
   ```

`mise run check:skills` now runs and passes, and the composed skills under `.claude/skills` match their sources. Until every domain is reviewed `vyd install --project` writes what it can and deletes no skill, so a mistake there cannot remove the committed ones. A later `mise run bootstrap` leaves the configuration as it is, and `vyd setup` run again changes nothing once the domains are configured.

## 7. Where to go next

- [Developer Guide](https://github.com/nebularis/lattice/blob/main/docs/developer/developer-guide.md) — every tool, what it is for, how the pieces fit together.
- [AGENTS.md](../../AGENTS.md) — the rules AI agents follow here, and the skills they load (Developer Guide §8).
- [Formal Methods in the Development Lifecycle](https://github.com/nebularis/lattice/blob/main/docs/developer/formal-methods-lifecycle.md) — how sketch, plan and implementation each use formal methods, for an ontology change, a tools change, or a platform service change alike.
- [`docs/diagrams/`](../diagrams/README.md) — the whole architecture, pictured, across five views.
- [`docs/architecture/solution-design-specification.md`](../architecture/solution-design-specification.md) — the platform's own architecture, the primary entry point for understanding the codebase beyond the ontology layers.
