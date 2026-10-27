<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Developer Guide

What every tool and script in this repository is for, when to reach for it, and how the pieces
fit together. For first-time setup, read [Getting Started](getting-started.md) first. For how
formal methods specifically hooks into the development lifecycle, read
[Formal Methods in the Development Lifecycle](formal-methods-lifecycle.md). For pictures of all
of this, see [`docs/diagrams/`](../diagrams/README.md).

## 1. How this repository is organised

| Root | Owns |
|---|---|
| `ontology/` | Semantic assets only: normative sources, shapes, vocabularies, projections, examples, semantic documentation. One directory per layer (`foundation`, `vocabulary`, `quantification`, `party`, `eligibility`, `behaviour`, `wording`, `instrument`, `surface`, `mork`, `persistence`, `governance`, `spc`) plus `applied/` domain ontologies and `examples/` |
| `tools/` | Executable reference implementations and developer-facing toolchains: compilers, resolvers, validators, formal-methods artefacts. `tools/testing/` holds test-support packages, used only by tests, checks and benchmarks (ADR-A125) |
| `benchmark/` | Checks that measure, run on demand and never part of `check`. They fail on a wrong result, never on time (ADR-A124) |
| `platform/` | Runtime platform services (Java/Maven): authoring, Surface workflow, release integration, the semantic dataset SPI and Fuseki backend, policy, the test-only reasoning harness |
| `apps/` | User-facing web applications (TypeScript/React, Yarn workspace): the MORK Review Workbench, Surface Contract Studio, the Word authoring add-in |
| `packages/` | Standalone libraries with no LATTICE dependency (identity minting, Python and Java) |
| `contracts/` | Inter-component data contracts (JSON Schema): events, identity, MORK, release, Surface |
| `deployment/` | Local reference environment (Docker Compose) |
| `workers/` | The asynchronous worker runtime |
| `test/` | End-to-end conformance suites |
| `spikes/` | Experimental feasibility work, not production (today: the formal-prover toolchain spike, track D, and `persistence-oxigraph`, which runs the persistence compiler's updates on a second SPARQL engine and defines no SPI (its adapter now lives in `tools/testing/oxigraph`), and `persistence-aggregate-ownership`, experiments for the aggregate ownership note) |
| `docs/` | Architecture, ADRs, developer process (sketches/plans/status/validation), and the diagrams this guide links to |

A layer under `ontology/` follows one shape: `README.md` (the one normative, literate source),
`spec/<layer>.ttl`, `vocab/<layer>-vocab.ttl`, `shapes/structural.ttl` and `shapes/constraints.ttl`,
`projection/` where it applies, `examples/`. §3 explains how the generated files relate to the
README.

## 2. `mise`: the one task entry point

Every build, test and validation step runs through `mise` (ADR-A29). Do not invoke `pip`,
`pytest`, `mvn` or `yarn` directly except when iterating inside one package — `mise.toml` is the
record of what actually needs to run and in what order, and CI runs the exact same tasks (§6).

```bash
mise install            # pin the toolchain versions mise.toml declares (Java, Python, Node, Erlang, Elixir)
mise run bootstrap       # install every package's dependencies, and the git hooks
mise run check           # run every validation task
mise tasks               # list every task mise.toml declares, with its description
```

### Git hooks

`mise run bootstrap` installs two git hooks, `pre-commit` and `pre-merge-commit` ([ADR-A133](../architecture/decisions/ADR-A133-git-hooks.md)). They live in the repository's shared hooks directory, so one install covers the main checkout and every worktree. `mise run hooks:install` installs them alone. It never replaces a hook it did not write: it stops and says how to add the dispatcher to yours, and under bootstrap it warns and carries on.

**At a commit**, the hook runs only the checks the staged files touch, and each judges only those files, so debt elsewhere in the tree never blocks you:

| You stage | The hook checks |
|---|---|
| anything | your personal deny-list (`check:deny-terms`) |
| a layer's README or a file it generates | that they agree, as the literate check does (§3) |
| `AGENTS.md`, a skill, the plugin listing or the catalogue | the agent guidance and its Copilot copy (§8) |
| an ontology file, a module or a tool package | the repository catalogue and the import guard |
| Markdown | its links, and the writing rules on the lines you added: no semicolon in prose, no "this document" in a literate README. A hard-wrapped line and a citation of an unpublished decision only warn |
| a theory, a reference or the site's sources | formal freshness (§4) and the site's section copies |

A commit that touches none of these runs the deny-list alone, in well under a second. A typical commit takes a few seconds. If a check's tool cannot run, for example after a dependency change, it warns and asks for `mise run bootstrap`.

**At a merge into `main`** (a clean merge, or a commit on `main` while a merge or a squash is in progress) the same checks run over every file the merge brings, all blocking, together with the published-decisions check over the whole tree and ontology versioning, since the merge is where the release moves. CI is manual (§6), so before merging on GitHub run `mise run hooks:merge`, which runs this gate for the current branch by hand.

**No hook runs at a push**, so a branch, and a cloud agent's work, always reaches the maintainer.

**Running and skipping.** `mise run hooks:run` runs the commit checks over what is staged without committing. `LATTICE_HOOKS_SKIP=links,writing git commit …` skips named checks, and `git commit --no-verify` skips every check. Record a skip, and why, in the slice's Validation Pack. The hooks are a floor: `mise run check` remains the full gate. `mise run check:hooks` tests the dispatcher (`tools/hooks.py`) and the writing rules (`tools/writing_rules.py`).

### Task families

| Family | Does | Run |
|---|---|---|
| `bootstrap:*` | Installs one package's dependencies (`pip install -e`, `yarn install`, …). `bootstrap:python` installs every Python package in one pip resolve | Once per clone, again after a dependency changes |
| `check:*` | Validates one package or gate (tests, shape conformance, catalog/version checks) | Before every commit touching that package; `mise run check` runs all of them |
| `build:*` | Regenerates a derived artefact (the ontology catalog, release rows, the MORK Teaching Pack, Persistence's compiled examples, minting vectors) | When the source it derives from changes |
| `clean:*` | Removes build output and caches | When something looks stale |
| `topology:*` | Checks the repository's own structure against ADR-A77 | Rarely, mostly for the topology migration itself |

### What `check` does **not** include, and why

A handful of `check:*` tasks are deliberately **not** part of the default `check` aggregate,
because their toolchain is large, native, or otherwise too heavy to run on every commit:

| Task | Needs | Why manual |
|---|---|---|
| `check:formal-network` | network access | probes whether track D's prover sources are reachable at all, not a correctness check |
| `check:formal-smoke` | Docker, or a native Rocq/Isabelle install | confirms a prover toolchain runs end to end, minutes to build |
| `check:proofs` | a native Isabelle install | builds every `tools/proofs/<layer>/` Isabelle session and runs the proof gate (ADR-A-FM2) |
| `check:minting-tables` | network access (Unicode Character Database) | regenerates pinned tables and diffs them; only needed when Unicode itself updates |

Everything else, including the formal-methods reference semantics (`check:reference-eligibility`)
and the formal-artefact freshness check (`check:formal-freshness`, §4), **is** in `check`, because
those are ordinary Python and do not need a heavy toolchain.

## 3. The literate-source discipline

A layer's `README.md` is the one normative source (epic principle E1). Its own fenced code
blocks — ```` ```turtle-spec ````, ```` ```turtle-vocab ````, ```` ```turtle-shapes ````,
```` ```turtle-example ```` (illustrative only, never extracted), and ```` ```isabelle-spec ````
for a formalised layer's closed datatype — are mechanically extracted by
[`tools/literate_extract.py`](../../tools/literate_extract.py) into `spec/`, `vocab/`, `shapes/`
and (for formalised layers) `tools/proofs/<layer>/Kernel.thy`. Never hand-edit a generated file:
edit the README's own fenced block and re-run the extractor.

A layer with a second spec document, such as Behaviour's runtime document, writes it from the same
README ([ADR-A120](../architecture/decisions/ADR-A120-literate-specs-with-several-documents.md)). A
`turtle-spec` block whose first line is `# @output-file "spec/<file>.ttl"` goes to that file, which
gains `spec/<layer>.ttl`'s `@prefix` lines. The directive counts only on the first line. Each such
block states its own ontology header. All of a layer's spec documents carry one version and are
bumped together. The extractor refuses them otherwise. The same directive works on a
`turtle-vocab` block, for a module with several vocabulary documents (a module's own version for
its vocabulary, independent of its spec version). `--layer` may itself be a nested module path
below `ontology/`, such as `applied/insurance/peril`, whose last segment names the default
documents (ADR-A120 addendum, AIR-2.0).

```bash
# Check a layer's generated files still match its README (writes nothing, exits non-zero on drift)
mise exec -- python tools/literate_extract.py ontology/surface/README.md --layer surface --root . --check

# Regenerate them (same command, without --check)
mise exec -- python tools/literate_extract.py ontology/surface/README.md --layer surface --root .

# Extract a formalised layer's Isabelle datatype too
mise exec -- python tools/literate_extract.py ontology/eligibility/README.md --layer eligibility --root . \
  --proofs-root tools/proofs --reference-root tools/reference --check

# A nested applied-insurance module, with several vocabulary documents
mise exec -- python tools/literate_extract.py ontology/applied/insurance/peril/README.md \
  --layer applied/insurance/peril --root . --check
```

Each module's extraction contract is also stated in its README's entry in the
[repository catalogue](../../repository-catalogue.md)
([ADR-A121](../architecture/decisions/ADR-A121-repository-catalogue.md)), read by
`tools/lattice_repo_catalogue.py`, the one module that finds the repository root and says where a
module's artefacts are. `mise run check:catalogue`, part of `check`, fails when the catalogue and the
tree disagree. The root file also declares the roots, the tool packages under `tools/`, the
documentation areas and the generated outputs. A new root, tool package or documentation area is added
there, and `mise run build:agent-guidance` then rewrites the "Where things are" table in `AGENTS.md`
between its markers, never by hand. Each root and documentation area has a `name`, and code asks the
reader for its directory by that name, `Catalogue.area("developer")` or `area developer` on the command
line, rather than writing the path (STD-273). The same check reports Python under `tools/` that builds a path to a
root itself, against the known cases in `tools/lattice_repo_catalogue_exceptions.txt`, a list that only
shrinks. It does not scan tests (TD-54), or find a root counted from `__file__` (TD-88).

```bash
# The files a module's README generates for one role, in extraction order
mise exec -- python tools/lattice_repo_catalogue.py paths instrument shapes

# A role's directory, and the whole catalogue as JSON for other runtimes
mise exec -- python tools/lattice_repo_catalogue.py path party projection
mise exec -- python tools/lattice_repo_catalogue.py area developer
mise exec -- python tools/lattice_repo_catalogue.py dump --json
```

**Not every layer passes `--check` today.** Vocabulary, Party and Eligibility's own `spec`/`vocab`/
`shapes` predate the extractor and currently
drift from their README's blocks. Surface, Wording, Behaviour, Quantification and Instrument are
clean. Before hand-editing a layer's generated file, run `--check` first and read the diff — on a
layer that already drifts, a `--check`-clean regeneration could silently discard unrelated
hand-maintained content.

## 4. Formal-methods artefacts stay in sync too

Three further kinds of artefact extend a layer's literate README, each checked its own way (full
account in [Formal Methods in the Development Lifecycle](formal-methods-lifecycle.md)):

| Kind | Home | Relationship to the README | Checked by |
|---|---|---|---|
| Mechanised theory | `tools/proofs/<layer>/` | `Kernel.thy`'s datatype is **generated** from `isabelle-spec` blocks; the laws proved on top are hand-written | `check:proofs` (native Isabelle, manual) for the proofs themselves; `check:formal-freshness` (always on, §2) for whether `Kernel.thy` still matches the README |
| Design-time model | `tools/models/<name>/` | Hand-written, evidence for an ADR not yet accepted — no literate relationship at all | Re-run manually with Alloy/SMT when the ADR it informs is revisited |
| Reference semantics | `tools/reference/<layer>/` | Hand-written, restates an **already-accepted** law independently of any compiler, so a shared compiler mistake has something else to disagree with | `check:reference-eligibility` (differential tests against the real compilers) plus `check:formal-freshness`'s law-coverage check: every law the README declares `elg:lawRegister elg:SemanticLaw` must be named somewhere in the reference, covered or explicitly out of scope |

`mise run check:formal-freshness` (`tools/check_formal_freshness.py`) is the one command that
checks both relationships across every layer that has them, the same "never let the generated
artefact silently drift from its source" discipline `literate_extract.py --check` already gives
ordinary Turtle.

## 5. Tool-by-tool reference

### Ontology compilers and resolvers (Python, `tools/`)

| Package | What it does | Key command |
|---|---|---|
| [`tools/mork_compilers/`](../../tools/mork_compilers/README.md) | Compiles Eligibility conditions into SPARQL, SHACL, SWRL and an OWL design-time-checking backend, through one shared IR (ADR-A23, ADR-A24, ADR-A89) | `mise run check:mork-compilers` |
| [`tools/vocabulary/`](../../tools/vocabulary/README.md) | The scoped and temporal concept-scheme binding resolver (ADR-A85) | `mise run check:vocabulary` |
| [`tools/surface/`](../../tools/surface/README.md) | Compiles Surface promotion/projection contracts into generated module packages, with minimal-scope regeneration planning (ADR-A27) | `mise run check:python-root` (its tests run under `surface.test_surface`) |
| [`tools/persistence/`](../../tools/persistence/README.md) | Compiles Persistence profiles into SPARQL plans (ADR-A78/A79) | `mise run check:persistence` |
| [`tools/mork/`](../../tools/mork/README.md) | The MORK package and the MORK Teaching Pack generator | `mise run check:mtp`, `mise run build:mtp` |
| [`tools/testing/oxigraph/`](../../tools/testing/oxigraph/README.md) | An in-memory Oxigraph engine for the persistence tests and benchmark (ADR-A125). Not a store SPI | `mise run check:persistence` (default engine), `mise run check:persistence-conformance` (every engine, on demand and before a merge) |
| [`benchmark/persistence-composite-cost/`](../../benchmark/persistence-composite-cost/README.md) | The cost of a composite replace on rdflib and Oxigraph (ADR-A124, TD-42) | `mise run check:persistence-composite-cost` |

### Formal-methods toolchains (`tools/`)

| Package | What it does | Key command |
|---|---|---|
| [`tools/proofs/`](../../tools/proofs/README.md) | Mechanised Isabelle/HOL theories, one subdirectory per formalised layer (track E, ADR-A-FM1/A-FM2) | `mise run check:proofs` (native, manual) |
| [`tools/models/`](../../tools/models/README.md) | Alloy/SMT design-time models, evidence for an ADR before it is accepted (track C) | run directly with the Alloy Analyzer JAR, see that README |
| [`tools/reference/`](../../tools/reference/README.md) | Hand-written reference semantics, differentially tested against the real compilers (track B, ADR-A-FM3) | `mise run check:reference-eligibility` |

### Repository-wide gates (`tools/*.py`)

| Script | Checks | Command |
|---|---|---|
| `literate_extract.py` | README ⇄ generated-artefact drift (§3) | see §3 |
| `full_sweep.py` | Runs every check an ontology change needs, one line each, failures in red, logs in `.build/full-sweep`. Uses this checkout's tool packages, and compares versions with `main` | `mise run check:full-sweep`, or `-- --base-ref REF` |
| `check_formal_freshness.py` | Formal artefact ⇄ README drift (§4) | `mise run check:formal-freshness` |
| `ontology_catalog.py` | The import catalog (`ontology/catalog-v001.xml`) is complete and consistent (ADR-A88) | `mise run check:ontology-catalog` / `mise run build:ontology-catalog` |
| `ontology_version_check.py` | Every changed ontology document bumped its version, with a release row (ADR-A86) | `mise run check:ontology-versioning` |
| `ontology_releases.py` | Release rows exist for every version, tags are named correctly | `mise run build:ontology-releases` / `check` |
| `import_guard.py` | No substrate layer imports upward (ADR-A01 addendum, law B7) | `mise run check:import-guard` |
| `reasoning_isolation_check.py` | A reasoner is declared only in `platform/reasoning-testkit` (ADR-A83) | `mise run check:reasoning-isolation` |
| `repository_topology_check.py` | The repository's own structure matches ADR-A77 | `mise run topology:preflight` / `topology:ready` / `topology:links` |
| `phase8_conformance.py` | A shared conformance corpus runs clean across Surface and Eligibility's compiled backends | part of `mise run check:python-root` |
| `conftest.py` | Shared, session-scoped caching for the `tools/test_*.py` suite (`graph_cache`, `validated`, `repo_files`; `python-test-melting`). A module that benefits declares one module-scoped autouse fixture fetching its own graphs from `graph_cache` and assigning `module.validate = validated`; see the module's own docstring. `mise run dev:time-ontology-tests` times `check:ontology-catalog`'s test files separately, slowest first. `-- --workers N --dist MODE` reruns it with other xdist settings and reports when each worker finished, which files it ran, and peak memory (macOS and Linux), for comparing worker counts and scheduling modes on one machine | `mise run check:ontology-catalog` runs the whole suite with `pytest-xdist` (`-n auto --dist worksteal`, so the largest file does not set a floor on the run). `PYTEST_XDIST_AUTO_NUM_WORKERS` sets what `auto` means, e.g. on a laptop with efficiency cores that add nothing. `tools/test_peril_vocabulary.py` is part of the run again (it was excluded as the second TD-45 while it set a floor under file-level distribution) and `mise run check:peril-vocabulary` runs it alone |
| `validation_replay.py` | Records every SHACL validation the ontology suite makes (shapes' source files, data graph, full report) and replays them against the shapes in the working tree, blank nodes masked, to show that a rewrite of a constraint query, or an upgrade of the validator, changed no report (docs/architecture/efficient-queries-and-shapes.md, R7). Tested by `tools/test_validation_replay.py` | `mise run dev:record-validations -- --out DIR` at the commit before a change, then `mise run dev:replay-validations -- DIR --write-baseline FILE` there and `mise run dev:replay-validations -- DIR --baseline FILE` after it. Exit status 1 when a validation outside the baseline differs |

### Platform services (Java/Maven, `platform/`)

Authoring service (design-time control plane), Surface workflow (revision lifecycle and worker
coordination), release integration, the semantic dataset SPI and its Fuseki backend, the semantic
policy module, and the test-only reasoning harness (`reasoning-testkit`, never a runtime
dependency, ADR-A83). `mise run check:java` runs the whole Maven reactor.

### Frontend applications (`apps/`)

The MORK Review Workbench and Surface Contract Studio (React, Vite, Playwright). `mise run
check:frontend` (lint/typecheck), `mise exec -- yarn build`, `mise exec -- yarn test` (Playwright
end-to-end, after `yarn playwright install`).

### Identity minting (`packages/minting/`)

Framework-neutral identity-pattern libraries, Python and Java, with no LATTICE dependency
(ADR-A84). `mise run check:minting` (anchors, Python, Java together).

## 6. Continuous integration

`.github/workflows/platform.yml`, `phase8-conformance.yml` and `formal-methods.yml` run the same
`mise run check:*` tasks described above — nothing is reimplemented in YAML. All three are
**manual-dispatch only** (`workflow_dispatch`), a deliberate cost-control choice, not a readiness
gap: every job is written and ready, so switching to automatic triggering on push/PR is a one-line
change (see the commented-out trigger block at the top of `platform.yml`), made when the maintainer
chooses to activate it.

`formal-methods.yml` is split out deliberately: its two jobs (`proofs`, native Isabelle; `models`,
Alloy) each install a full native toolchain from scratch, making them slower and more toolchain-
fragile than everything else — kept out of the main `platform.yml` run so a toolchain hiccup there
never blocks the rest of CI.

While CI stays manual, the merge gate is local: the `pre-merge-commit` hook, or `mise run hooks:merge` before a merge on GitHub (§2, Git hooks).

## 7. Validation packs and the Epic Decomposition Model

Any unit of work beyond a small fix follows the model in the [lattice-lifecycle skill](../../.claude/skills/lattice-lifecycle/SKILL.md) and
the developer index: a sketch, a plan, a status record updated live, and (for a
slice) a Validation Pack naming its test cases, the one command
that runs them, and what a maintainer should inspect before merging, which is the sign-off. Read that model before starting a new unit — this guide
covers the tools; that model and skill cover the
process those tools are run under.

## 8. Agent guidance

AI agents work here under [AGENTS.md](../../AGENTS.md), always loaded, and six skills in
[`.claude/skills/`](../../.claude/skills), loaded by task (ADR-A117). `.github/copilot-instructions.md`
is generated from `AGENTS.md`, never edited by hand.

| Task | Does |
|---|---|
| `build:agent-guidance` | writes `AGENTS.md`'s "Where things are" table from the repository catalogue, then Copilot's file from `AGENTS.md` |
| `check:agent-guidance` | checks that table is current, that file, every skill's name and description, `AGENTS.md`'s skill table, the plugin marketplace and every link (in `check`) |
| `skills:link` | links the skills into `~/.copilot/skills/` for Copilot in other projects, copying on Windows |
| `check:deny-terms` | checks staged changes against your personal, never published, list of terms (skill `lattice-publication-hygiene`) |
| `hooks:install` | installs the git hooks into the shared hooks directory, covering every worktree. `bootstrap` runs it (ADR-A133) |
| `hooks:run` | runs the commit checks over what is staged, as the commit hook does |
| `hooks:merge` | runs the merge checks for the current branch against `main`, for example before merging on GitHub |
| `check:hooks` | tests the hooks dispatcher and the writing rules |

Claude Code users elsewhere install the skills with `/plugin marketplace add nebularis/lattice` and
`/plugin install lattice@nebularis`. Do not install the plugin inside this repository, where the
skills already load, or each appears twice.

**Cloud sessions.** A Claude Code cloud environment prepares itself with
[`tools/claude-cloud-setup.sh`](../../tools/claude-cloud-setup.sh). Paste the two lines from its header
into the environment's **Setup script** field, and set its network access to **Custom**, with the
default list of package managers included, plus `mise.jdx.dev` and `www.cl.cam.ac.uk`. It installs
mise, Java 25 from Ubuntu's archive, Python 3.14 from the deadsnakes PPA and Isabelle2025-2, with its
prebuilt HOL heap, from the Cambridge mirror. It links those and the image's Node and Maven into mise,
and runs `mise run bootstrap`. GitHub serves a cloud session only its own repositories, so nothing is
fetched from GitHub. The script always exits 0, as a cloud setup script must, and its last lines
report how long setup took, which must stay under about five minutes for the environment to be
cached.


## 9. Several checkouts side by side

We often run several workstreams at once: a slice on one branch, a review of another, a bundle from
a machine that cannot push. Each needs its own working files and its own installed tool packages,
without containers. Two things give that: a virtual environment per checkout, and git worktrees.

### A virtual environment per checkout

`mise.toml` declares `_.python.venv = { path = ".venv", create = true }`. Every checkout, worktrees
included, gets its own `.venv` (ignored by git), which mise activates in an activated shell inside the
checkout and for every `mise run` and `mise exec`. Editable installs (`pip install -e`, which the
`bootstrap:*` tasks use) then point at that checkout's own `tools/` and never at another's.

- Run `mise run bootstrap` once in each new checkout. With pip's shared cache it takes a minute or two.
- `mise run bootstrap` installs every Python package in one pip resolve (`bootstrap:python`), so
  packages that need incompatible versions of a shared dependency fail at once and visibly. Keep
  `pytest` and `pytest-xdist` specifiers identical in every `pyproject.toml`
  (`tools/test_python_requirements.py` checks it).
- `mise` creates the `.venv` with `uv` where `uv` is installed, and `uv` leaves out pip. Every Python
  `bootstrap:*` task depends on `bootstrap:pip`, which runs `ensurepip`.
- Run individual `bootstrap:<package>` tasks one at a time (`mise run --jobs 1 bootstrap:a bootstrap:b`).
  Parallel pip runs into one `.venv` interleave files of different versions of the same package and
  leave it unimportable. If that has happened, run `rm -rf .venv && mise run bootstrap`.
- In a shell where mise is not activated, a bare `python` is mise's global interpreter, not the
  checkout's. Use `mise run <task>` or `mise exec -- python ...`, or activate mise in the shell.
- Check which code a test imports: `mise exec -- python -c "import persistence; print(persistence.__file__)"`
  must print a path inside the checkout.

### Git worktrees

A git repository can have several working trees. Each has its own files, index and checked-out
`HEAD`, and all share one object store, one set of branches and tags, and one set of remotes. So a
`git fetch` in any of them is seen by all, and a commit made in one is visible from the others at
once. Git refuses to check out the same branch in two worktrees, which protects a branch from two
workstreams editing it at the same time.

We keep the primary checkout at `~/work/lattice` and put its worktrees in `~/work/lattice-wt/`:

```bash
cd ~/work/lattice
git fetch origin-ssh
git worktree add ../lattice-wt/fm-review fm/some-branch                          # a local branch that exists: the worktree is on it
git worktree add --track -b fm/some-branch ../lattice-wt/fm-review origin-ssh/fm/some-branch   # no local branch yet: create one tracking origin-ssh
git worktree add -b ccs/c9b3-sets ../lattice-wt/c9b3 main                       # a new branch, started from main
git worktree add --detach ../lattice-wt/look origin-ssh/fm/some-branch          # a read-only look at a commit, on no branch
git worktree list                                                                # every worktree and what it has checked out
git worktree remove ../lattice-wt/fm-review                                      # when done: refuses if there are uncommitted changes
git worktree prune                                                               # forget worktrees deleted by hand
```

Name a **branch**, not a remote-tracking ref such as `origin-ssh/fm/some-branch`. Given a
remote-tracking ref, `git worktree add` checks out its commit with no branch (a detached `HEAD`),
where a commit belongs to no branch and a `git pull` has nothing to update. With no local branch of
that name, git creates one tracking the remote only when exactly one remote has it. We have two,
`origin` and `origin-ssh`, so create it explicitly with `--track -b` as above. A worktree already
detached joins its branch with `git switch fm/some-branch`, and `git branch
--set-upstream-to=origin-ssh/fm/some-branch` changes which remote it tracks.

Then, in each new worktree:

```bash
cd ~/work/lattice-wt/c9b3
mise trust          # once per worktree, since its mise.toml is a new file to mise
mise run bootstrap  # its own .venv, node_modules and builds
```

To avoid `mise trust` per worktree, add `~/work` to `trusted_config_paths` in
`~/.config/mise/config.toml`.

**What stays separate:** the working files, `.venv`, `node_modules`, `target/` (so the reasoner jar),
`.build/` (sweep logs, pytest cache) and the checked-out branch. **What is shared:** commits,
branches, tags, remotes and stashes (so set work aside with a commit, not a bare `git stash`), and
outside git, Maven's `~/.m2` and pip's cache, which are safe to share. Two worktrees running the
authoring stack's dev servers at once collide on ports, so run one at a time.

An agent session works in one worktree and stays there. Several sessions can run at once, one per
worktree, as long as no two share a branch.

### Integrating work from a machine that cannot push

A machine with no route to the remote sends its commits as a git bundle: one file holding commits
and the branches that name them, which another clone can fetch from as if it were a remote.

**On the machine that cannot push (machine S):**

```bash
git bundle create ../fm-2026-10-10.bundle main..fm/some-branch   # only the commits main lacks
git bundle verify ../fm-2026-10-10.bundle                        # checks it is complete
```

`main..fm/some-branch` sends only the commits that are not on `main`, so the bundle is small, and the
receiving clone must already have `main` up to that point, which `verify` on the receiving side
confirms. For a first bundle, or when unsure what the receiver has, bundle the whole branch:
`git bundle create ../fm.bundle fm/some-branch`. For later bundles, send everything since the last
one by tagging what was sent:

```bash
git bundle create ../fm-2026-10-11.bundle bundle/last-sent..fm/some-branch
git tag -f bundle/last-sent fm/some-branch
```

Copy the file to the receiving machine by any means.

**On the machine that can push (machine R):**

```bash
cd ~/work/lattice
git bundle verify ~/Downloads/fm-2026-10-10.bundle                              # lists its heads, and says if a prerequisite commit is missing
git fetch ~/Downloads/fm-2026-10-10.bundle 'refs/heads/*:refs/remotes/machine-s/*'
git log --oneline main..machine-s/fm/some-branch                                 # what arrived
git worktree add --detach ../lattice-wt/machine-s machine-s/fm/some-branch       # review it in its own worktree, on no branch
```

The fetch puts the bundle's branches under `machine-s/`, beside `origin-ssh/`, and every worktree
sees them. Review and run the checks in the `machine-s` worktree. To accept the work, push it from
any worktree with `git push origin-ssh machine-s/fm/some-branch:fm/some-branch` and merge it as any
branch, or merge `machine-s/fm/some-branch` into `main` directly.

**Sending updates back to machine S** works the same way in reverse: on R,
`git bundle create ../r-main.bundle main`, and on S, `git fetch ../r-main.bundle main:refs/remotes/r/main`
followed by a merge or rebase of `r/main` into its branch.
