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
| `tools/` | Executable reference implementations and developer-facing toolchains: compilers, resolvers, validators, formal-methods artefacts |
| `platform/` | Runtime platform services (Java/Maven): authoring, Surface workflow, release integration, the semantic dataset SPI and Fuseki backend, policy, the test-only reasoning harness |
| `apps/` | User-facing web applications (TypeScript/React, Yarn workspace): the MORK Review Workbench, Surface Contract Studio, the Word authoring add-in |
| `packages/` | Standalone libraries with no LATTICE dependency (identity minting, Python and Java) |
| `contracts/` | Inter-component data contracts (JSON Schema): events, identity, MORK, release, Surface |
| `deployment/` | Local reference environment (Docker Compose) |
| `workers/` | The asynchronous worker runtime |
| `test/` | End-to-end conformance suites |
| `spikes/` | Experimental feasibility work, not production (today: the formal-prover toolchain spike, track D) |
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
mise run bootstrap       # install every package's dependencies
mise run check           # run every validation task
mise tasks               # list every task mise.toml declares, with its description
```

### Task families

| Family | Does | Run |
|---|---|---|
| `bootstrap:*` | Installs one package's dependencies (`pip install -e`, `yarn install`, …) | Once per clone, again after a dependency changes |
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
bumped together. The extractor refuses them otherwise.

```bash
# Check a layer's generated files still match its README (writes nothing, exits non-zero on drift)
python tools/literate_extract.py ontology/surface/README.md --layer surface --root . \
  --shapes shapes/structural.ttl shapes/constraints.ttl --check

# Regenerate them (same command, without --check)
python tools/literate_extract.py ontology/surface/README.md --layer surface --root . \
  --shapes shapes/structural.ttl shapes/constraints.ttl

# Extract a formalised layer's Isabelle datatype too
python tools/literate_extract.py ontology/eligibility/README.md --layer eligibility --root . \
  --proofs-root tools/proofs --shapes shapes/structural.ttl shapes/constraints.ttl --check
```

**Not every layer passes `--check` today.** Vocabulary, Party and Eligibility's own `spec`/`vocab`/
`shapes` predate the extractor (TD-16, `docs/developer/plans/technical-debt.md`) and currently
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
| `conftest.py` | Shared, session-scoped caching for the `tools/test_*.py` suite (`graph_cache`, `validated`, `repo_files`; `python-test-melting`). A module that benefits declares one module-scoped autouse fixture fetching its own graphs from `graph_cache` and assigning `module.validate = validated`; see the module's own docstring. `mise run dev:time-ontology-tests` times `check:ontology-catalog`'s test files separately, slowest first | `mise run check:ontology-catalog` runs the whole suite with `pytest-xdist` (`-n auto --dist loadfile`) |

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
change (see the commented-out trigger block at the top of `platform.yml`), made when the human
chooses to activate it.

`formal-methods.yml` is split out deliberately: its two jobs (`proofs`, native Isabelle; `models`,
Alloy) each install a full native toolchain from scratch, making them slower and more toolchain-
fragile than everything else — kept out of the main `platform.yml` run so a toolchain hiccup there
never blocks the rest of CI.

## 7. Validation packs and the Epic Decomposition Model

Any unit of work beyond a small fix follows the model in the [lattice-lifecycle skill](../../.claude/skills/lattice-lifecycle/SKILL.md) and
[`docs/developer/INDEX.md`](INDEX.md): a sketch, a plan, a status record updated live, and (for a
slice) a Validation Pack under `docs/developer/validation/` naming its test cases, the one command
that runs them, and what a human should inspect before signing off in
`docs/developer/validation/LOG.md`. Read that model before starting a new unit — this guide
covers the tools; INDEX.md and that skill cover the
process those tools are run under.

## 8. Agent guidance

AI agents work here under [AGENTS.md](../../AGENTS.md), always loaded, and six skills in
[`.claude/skills/`](../../.claude/skills), loaded by task (ADR-A117). `.github/copilot-instructions.md`
is generated from `AGENTS.md`, never edited by hand.

| Task | Does |
|---|---|
| `build:agent-guidance` | writes Copilot's file from `AGENTS.md` |
| `check:agent-guidance` | checks that file, every skill's name and description, `AGENTS.md`'s skill table, the plugin marketplace and every link (in `check`) |
| `skills:link` | links the skills into `~/.copilot/skills/` for Copilot in other projects, copying on Windows |
| `check:deny-terms` | checks staged changes against your personal, never published, list of terms (skill `lattice-publication-hygiene`) |
| `hooks:install` | adds an opt-in pre-commit hook running `check:deny-terms` |

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

