## Running tasks

- **`mise` is the one entry point** (ADR-A29). Every build, test and check runs through it, and CI runs the same tasks. {{other_authorities}} remain their own dependency authorities.
- `mise install` and `mise run bootstrap` are all `mise run check` needs. The builds a check reads include the studio's staged assets under `.build/config-studio/` and the rendered Teaching Pack (STD-299), and the developer guide's "What `check` needs first" lists them.
- The task families are `bootstrap:*`, `check:*`, `build:*`, `clean:*` and `topology:*`. Some heavy checks are deliberately outside `check`, as the developer guide lists.
- Run the checks a change needs, not only the aggregate, and run the aggregate with `--continue-on-error` for a true picture.

## Which checks a change needs

## Which checks a change needs

| Change | Run |
|---|---|
| an ontology document | the list in skill `lattice-ontology-authoring`, step 7 |
| a Python package under `tools/` | its `check:*` task, and `check:python-root`. A new package is declared in `repository-catalogue.md`, which `check:catalogue` checks |
| Java under `platform/` | `check:java` |
| an app under `apps/` | `check:frontend`, then `test:frontend` |
| a formal-methods artefact | `check:formal-freshness`, and `check:proofs` where Isabelle is installed |
| generated SPARQL, or a test that runs it on an engine | `check:persistence` on Oxigraph, and `check:persistence-conformance` on every engine before a merge (skill `lattice-probing`) |
| a benchmark under `benchmark/` | its own `check:<area>-<topic>`, run on demand, never part of `check` (ADR-A124) |
| `AGENTS.md` or a skill | `build:agent-guidance`, then `check:agent-guidance`. The "Where things are" table in `AGENTS.md` is generated from `repository-catalogue.md`, so edit a root, tool package or documentation area there |
| a root, a tool package, a documentation area or a generated path | `repository-catalogue.md`, giving a new root or documentation area a `name` code asks for it by (see [Finding paths](#finding-paths)), then `build:agent-guidance` and `check:catalogue` |
| anything to be committed | the commit hook runs what the change touches (below). `mise run hooks:run` runs it by hand over what is staged |

## Is the code under test this checkout's?

Each checkout, git worktrees included, has its own `.venv`, which `mise.toml` creates, so `mise run bootstrap` in a checkout installs its packages again. Working in several checkouts at once, and integrating a bundle from a machine that cannot push, are in the developer guide, §9.

## A running process and the build

## A running process and the build

A build never writes a file that a running process has open. A JVM reads classes from its jar for as long as it runs, so a build that rewrites the jar under it leaves it failing with `NoClassDefFoundError` on the first class it had not loaded yet. A process started from the repository runs from a copy of what the build wrote, made just before it starts. A process that has to run from the build output itself is stopped before the build, and the task that starts it says so.

`mise run check` rewrites the studio's shaded jars. `mise run studio:up` runs from a copy under `.build/config-studio/run/pinned` and the studio harness does under its cache (STD-308).

## Git hooks

## Git hooks

`mise run bootstrap` installs the git hooks ([ADR-A133](../../../docs/architecture/decisions/ADR-A133-git-hooks.md)), as `mise run hooks:install` does alone. They go into the repository's shared hooks directory, so one install covers every worktree. Install never replaces a hook it did not write: on its own it fails and says what to do, and under bootstrap it warns.

| Moment | What runs |
|---|---|
| a commit | the checks the staged files touch: the deny-list, literate freshness per module, agent guidance, the catalogue, the import guard, links in the touched Markdown, formal freshness, the site's copies and the writing rules. Published decisions and hard wraps warn |
| a merge into `main` (a clean merge, or a commit on `main` while a merge or a squash is in progress) | the same checks over every file the merge changes, all blocking but the writing rules, plus published decisions over the whole tree and ontology versioning. `mise run hooks:merge` runs this by hand, for example before merging on GitHub |
| a push | nothing, so a cloud agent's push always reaches the maintainer |

A check judges only what the change touches, so a failure elsewhere in the tree never blocks a commit, and `mise run check` still finds it. A check whose tool cannot run warns and asks for `mise run bootstrap`. `LATTICE_HOOKS_SKIP=links,writing` skips named checks, and `--no-verify` skips all. Record either, and why, in the slice's Validation Pack. `mise run check:hooks` tests the dispatcher (`tools/hooks.py`) and the writing rules (`tools/writing_rules.py`).

## Finding paths

## Finding paths

**Find the repository root and every catalogued directory through the catalogue reader, never from `__file__` or a path written in code** ([ADR-A121](../../../docs/architecture/decisions/ADR-A121-repository-catalogue.md) decisions 4 and 5). A written path breaks when a directory moves, and a root counted from `__file__` is wrong in a copy or a worktree run with another checkout's interpreter.

| To find | Ask the reader, in Python | From a task or a shell |
|---|---|---|
| the repository root | `lattice_repo_catalogue.find_root()`, or `catalogue.root` after `load()` | the working directory, or `LATTICE_ROOT` |
| a module's role directory, such as its examples | `catalogue.module("instrument").directory("examples")` | `python tools/lattice_repo_catalogue.py path instrument examples` |
| a module's generated files, in order | `catalogue.module("wording").files("shapes")` | `python tools/lattice_repo_catalogue.py paths wording shapes` |
| a root or documentation area, such as the registers' | `catalogue.area("developer")` | `python tools/lattice_repo_catalogue.py area developer` |
| every file of a name a check should scan, such as each `pyproject.toml` or `pom.xml` | `catalogue.files("pom.xml")`, the root's own and those under the catalogued roots, never a nested worktree or build output |  |

`load()` comes from `tools/lattice_repo_catalogue.py`, which a tool under `tools/` imports after putting `tools/` on `sys.path`. Each lookup returns a directory relative to the root, and a file's name is joined to it, as in `catalogue.root / catalogue.area("developer") / "facets.md"`. A name or role the catalogue lacks fails with an error naming where to declare it, so declare it there rather than writing the path. `check:catalogue` fails a tool under `tools/` that builds a path to a catalogued root itself. Its scan does not yet read tests (TD-54) or find a root counted from `__file__` (TD-87, TD-88), so there the rule holds only while it is followed.

## Rules for tasks and tools

- **A task that needs a shell feature, or that reads or writes text whose encoding or line endings matter, runs a Python script under `tools/`, the same on Windows, Linux and macOS** (STD-322). A shell feature is a variable, a glob, a redirect, a pipe, a loop, `cd` or a multi-line script. Text means files, streams and a process's output. Plain commands are a `run` array, one per entry, with `dir` instead of `cd`. The script opens text with `encoding="utf-8"`, writes it with `newline="\n"`, gives every `subprocess` call that uses text an encoding, and compares text with its line endings normalised. LATTICE keeps no `run_windows` variant but the formal-methods installers, which install a platform's own toolchain. `mise run check:portability` (CAP-108) fails a task that needs a shell, a Windows variant not listed in `tools/portability.py` with its reason, a text call that names no encoding beyond `tools/portability-baseline.txt` (TD-154), and a test that skips on the platform.
- Ask {{maintainer}} to start Docker Desktop if its engine is not running. Do not start it yourself.

- A new Python package for a layer goes under `tools/<layer>/`, shaped like `tools/persistence/`: `pyproject.toml` with a `src/` layout and a `test` extra, a README, `tests/conftest.py` with fixtures, and `bootstrap:<pkg>` and `check:<pkg>` tasks wired into the aggregates.
- A new build output outside `build/` or `.build/<name>/` needs adding to its area in `tools/clean.py`, and a Maven module outside `platform/pom.xml` to `clean:java`, which list exact paths. `tools/test_clean.py` checks what each area removes and keeps.
