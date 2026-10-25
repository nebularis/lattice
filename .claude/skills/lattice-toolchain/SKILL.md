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
| a Python package under `tools/` | its `check:*` task, and `check:python-root`. A new package is declared in `repository-catalogue.md`, which `check:catalogue` checks |
| Java under `platform/` | `check:java` |
| an app under `apps/` | `check:frontend`, then `test:frontend` |
| a formal-methods artefact | `check:formal-freshness`, and `check:proofs` where Isabelle is installed |
| generated SPARQL, or a test that runs it on an engine | `check:persistence` on Oxigraph, and `check:persistence-conformance` on every engine before a merge (skill `lattice-triple-stores`) |
| a benchmark under `benchmark/` | its own `check:<area>-<topic>`, run on demand, never part of `check` (ADR-A124) |
| `AGENTS.md` or a skill | `build:agent-guidance`, then `check:agent-guidance`. The "Where things are" table in `AGENTS.md` is generated from `repository-catalogue.md`, so edit a root, tool package or documentation area there |
| a root, a tool package, a documentation area or a generated path | `repository-catalogue.md`, then `build:agent-guidance` and `check:catalogue` |
| anything to be committed | the commit hook runs what the change touches (below). `mise run hooks:run` runs it by hand over what is staged |

## Git hooks

`mise run bootstrap` installs the git hooks ([ADR-A133](../../../docs/architecture/decisions/ADR-A133-git-hooks.md)), as `mise run hooks:install` does alone. They go into the repository's shared hooks directory, so one install covers every worktree. Install never replaces a hook it did not write: on its own it fails and says what to do, and under bootstrap it warns.

| Moment | What runs |
|---|---|
| a commit | the checks the staged files touch: the deny-list, literate freshness per module, agent guidance, the catalogue, the import guard, links in the touched Markdown, formal freshness, the site's copies and the writing rules. Published decisions and hard wraps warn |
| a merge into `main` (a clean merge, or a commit on `main` while a merge or a squash is in progress) | the same checks over every file the merge changes, all blocking but the writing rules, plus published decisions over the whole tree and ontology versioning. `mise run hooks:merge` runs this by hand, for example before merging on GitHub |
| a push | nothing, so a cloud agent's push always reaches the maintainer |

A check judges only what the change touches, so a failure elsewhere in the tree never blocks a commit, and `mise run check` still finds it. A check whose tool cannot run warns and asks for `mise run bootstrap`. `LATTICE_HOOKS_SKIP=links,writing` skips named checks, and `--no-verify` skips all. Record either, and why, in the slice's Validation Pack. `mise run check:hooks` tests the dispatcher (`tools/hooks.py`) and the writing rules (`tools/writing_rules.py`).

## Is the code under test this checkout's?

Each checkout, git worktrees included, has its own `.venv`, which `mise.toml` creates and which `mise
run`, `mise exec` and an activated shell use. A bare `python` in a shell without mise activated is
the global interpreter, whose editable installs can point at another clone. So run Python through
`mise run` or `mise exec -- python`, and before running anything that imports `persistence`,
`lattice_minting` or `surface`:

```bash
mise exec -- python -c "import persistence, lattice_minting, surface; print(persistence.__file__, lattice_minting.__file__, surface.__file__)"
```

Every path must be inside this checkout. If not, or if the import fails, run `mise run bootstrap` in
this checkout. Working in several checkouts at once, and integrating a bundle from a machine that
cannot push, are in the developer guide, §9.

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
- A tool writes text with an explicit encoding and newline, for example `path.write_text(text, encoding="utf-8", newline="\n")`, never the platform's. Without it Windows writes `\r\n` for a `\n` inside a generated multi-line string, and the file is corrupt.
- After changing a list other code counts or iterates over, such as a task's test modules, a version pin, or a set whose size a test asserts, run every task and test that reads that list, not only the one you edited. A merge resolution once left a task skipping two test modules without failing, and a contract added beyond a pinned count was caught only by the full sweep.
