---
name: lattice-toolchain
description: Building, testing and running LATTICE's checks, and setting up or repairing a development environment. Use when running or choosing mise tasks, when a build, test, package install, shell, proxy, certificate, Docker or Windows problem appears, when adding a new tool package or mise task, or before running anything that imports LATTICE's Python packages.
---

# The LATTICE toolchain

The [developer guide](https://github.com/nebularis/lattice/blob/main/docs/developer/developer-guide.md)
describes every tool and task, and
[getting started](https://github.com/nebularis/lattice/blob/main/docs/developer/getting-started.md)
the first setup. Read them rather than guessing a command. Lessons from past environment problems
are in [environment-lessons.md](environment-lessons.md), beside this file.

## mise is the one entry point

- Every build, test and check runs through `mise` (ADR-A29). CI runs the same tasks. Maven, Yarn 4,
  Python tooling and Mix remain their own dependency authorities.
- `mise install`, `mise run bootstrap`, `mise run check`, and `mise tasks` to list them.
- Task families are `bootstrap:*`, `check:*`, `build:*`, `clean:*` and `topology:*`. Some heavy
  checks are deliberately outside `check`, as the developer guide lists.
- Run the checks a change needs, not only the aggregate. `mise run check` stops every sibling task as
  soon as one fails, so a known-broken task hides the rest. Run the remaining `check:*` tasks one by
  one for a true picture.

## Which checks a change needs

| Change | Run |
|---|---|
| an ontology document | the list in skill `lattice-ontology-authoring`, step 7 |
| a Python package under `tools/` | its `check:*` task, and `check:python-root` |
| Java under `platform/` | `check:java` |
| an app under `apps/` | `check:frontend`, then `test:frontend` |
| a formal-methods artefact | `check:formal-freshness`, and `check:proofs` where Isabelle is installed |
| `AGENTS.md` or a skill | `build:agent-guidance`, then `check:agent-guidance` |
| anything to be committed | `check:deny-terms` (skill `lattice-publication-hygiene`) |

## Is the code under test this checkout's?

Editable installs can point at another clone. Before running anything that imports `persistence`,
`lattice_minting` or `surface`:

```bash
python -c "import persistence, lattice_minting, surface; print(persistence.__file__, lattice_minting.__file__, surface.__file__)"
```

If a path is outside this checkout, ask the maintainer to re-run the matching `mise run bootstrap:*`
task, or put `tools/persistence/src`, `packages/minting/python/src` and `tools/surface/src` first on
`PYTHONPATH`.

## Shell activation

Installing `mise` is not enough. A new shell has no `mise`-managed tools on `PATH` until its profile
activates it.

- POSIX shells: `eval "$(mise activate zsh)"` (or `bash`) in the rc file.
- PowerShell: `mise activate pwsh | Out-String | Invoke-Expression` in `$PROFILE`. On Windows
  PowerShell 5.1, set `$env:MISE_PWSH_CHPWD_WARNING = "0"` first.
- If a package manager put `mise` somewhere not on `PATH`, find the binary and add its directory
  first. Verify in a brand-new shell, never by patching the current one.

## Restricted or mirrored package registries

Some networks reach public registries only through a mirror, or not at all.

- A connection failure, or a redirect to an unrelated page, is a block.
- A **`pip` hash mismatch with no hash-pinned requirements file** is the same block in disguise, an
  intermediary substituting a notice page for the file. Fetch the failing URL and read the body
  before calling it a corrupted download. Retrying gives the same wrong hash.
- If a proxy intercepts TLS, a tool may fail with `UNABLE_TO_GET_ISSUER_CERT_LOCALLY` though the OS
  trusts the certificate. Tell the tool about the extra root CA separately, for example Node's
  `NODE_EXTRA_CA_CERTS`. Containers need it copied in, as the formal-methods images do with
  `extra-ca.crt`.
- Fix it in **user-level** configuration (`pip config file -f user` prints pip's), pointing at an
  approved mirror. Never edit repository files for it, never route around the block, and never
  record a mirror's hostname, an index URL or a credential in the repository or in published notes.
- A package missing from a mirror, or a registry that cannot be reached, is handed to the maintainer with
  the exact command. Do not retry it.

## Rules for tasks and tools

- `mise.toml` `run` strings run under `cmd.exe` on Windows and a POSIX shell elsewhere. Use double
  quotes around arguments with shell-special characters (`"./pkg[test]"`), and never rely on a shell
  glob. Enumerate files explicitly.
- A Windows-only variant of a task uses `run_windows` with `shell = "powershell -c"`. Start its script
  with `$ErrorActionPreference = "SilentlyContinue"` and end it with `exit 0`, because PowerShell
  exits 1 after any suppressed non-terminating error.
- A tool that prints a repository-relative path for comparison prints `Path.as_posix()`.
- A new Python package for a layer goes under `tools/<layer>/`, shaped like `tools/persistence/`:
  `pyproject.toml` with a `src/` layout and a `test` extra, a README, `tests/conftest.py` with fixtures,
  and `bootstrap:<pkg>` and `check:<pkg>` tasks wired into the aggregates.
- A new build output outside `build/` or `.build/<name>/`, or a Maven module outside
  `platform/pom.xml`, needs adding to `clean` and `clean-win`, which list exact paths.
- Ask the maintainer to start Docker Desktop if its engine is not running. Do not start it yourself.
