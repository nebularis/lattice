## mise is the one entry point

ADR-A29 makes `mise` the one entry point. A `check:*` task that reads an artefact a build writes, such as the studio's staged assets under `.build/config-studio/` or the rendered Teaching Pack, names that build in its `depends` (STD-299). The developer guide's "What `check` needs first" lists them. The task families also include `topology:*`.

## Which checks a change needs

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
| a root, a tool package, a documentation area or a generated path | `repository-catalogue.md`, giving a new root or documentation area a `name` code asks for it by (see [Finding paths](#finding-paths)), then `build:agent-guidance` and `check:catalogue` |
| anything to be committed | the commit hook runs what the change touches (below). `mise run hooks:run` runs it by hand over what is staged |

## Is the code under test this checkout's?

Working in several checkouts at once, and integrating a bundle from a machine that cannot push, are in the developer guide, §9.

## A running process and the build

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

- A new Python package for a layer goes under `tools/<layer>/`, shaped like `tools/persistence/`:
  `pyproject.toml` with a `src/` layout and a `test` extra, a README, `tests/conftest.py` with fixtures,
  and `bootstrap:<pkg>` and `check:<pkg>` tasks wired into the aggregates.
- A new build output outside `build/` or `.build/<name>/`, or a Maven module outside
  `platform/pom.xml`, needs adding to `clean` and `clean-win`, which list exact paths.
