# Instructions for Copilot

## Agentic Development Contract

This governs how implemented code is validated. It exists to conserve tokens and keep the human in control of what runs.

The general approach is that we work iteratively together, with the agent suggesting what we should build next, and the human verifying the approach along the way.

### Design First

Before we even sketch a plan for implementing/coding, we must consult the architecture and design records and produce a proposed Architecture Decision Record, which should also include either a design sketch OR be linked to a detailed design entry in the `docs/architecture/solution-design-specification.md' file. 

At all times, the following files MUST be kept up to date with changes:

- the root directory `README.md` (any new structure/folders/projects must be documented here)
- the project-level `README.md` files (significant changes must be documented appropriately)
- the ADR catalogue in `docs/architecture/decisions`
- the ontology architecture `docs/architecture/ontology-architecture.md'
- the platform specification `docs/architecture/solution-design-specification.md'
- the data architecture `docs/architecture/data-architecture.md'
- the ux design `docs/architecture/ux-design.md'

### Planning Mode

When writing a plan for coding, the plan must be VERY detailed. This allows us to ensure alignment between the architecture, the design specification, and the plan.

Lattice is a framework. It should not impose design decisions on its users unless they are materially vital for correctness. Instead, Lattice should provide the user with options and, where possible, configuration and capabilities that operate on the user's chosen configuration set.

If you are changing an ontology, you need to consider the semantic versioning impact of your change (see ADR-A86).

Whenever any ontology document changes, follow every step of `docs/architecture/ontology-versioning-policy.md` in the same change, including the import cascade, regenerating the import catalog (`mise run build:ontology-catalog`) and adding release rows (`mise run build:ontology-releases`). A change to a file in a layer's `shapes/` or `projection/` directory bumps that directory's `.version` (semver), never the spec or vocab version IRI. Run `mise run check:ontology-versioning` and `mise run check:ontology-catalog` before handing off. A skipped step breaks consumers silently, and has done so before.

**Release tags are the user's to create, never the agent's.** Whenever `build:ontology-releases` adds a row, or `check:ontology-versioning` lists pending tags, end your handoff with a prominent notice headed `🔴 RELEASE TAGS REQUIRED`, listing each tag as a, b, c and the commands to create and push them once the change is merged into `main`. Repeat the notice in every handoff until the tags exist.

**Merge to `main` before tagging, and branch from `main`.**

- A release tag names a commit on `main`. Stable changes are merged into `main` first, and the ontology release tags are created on the merged commit, never on a feature branch. A tag on an unmerged branch can name a commit that never reaches `main`, or one a rebase later replaces. When handing off a change that adds releases, order the steps as commit, merge into `main`, then tag.
- Create each new feature branch from the current `main`, so that it starts from every merged release. Branch from somewhere else only where branching from `main` would cause problems for parallel work.
- The human says when parallel work is under way, before any merge into `main`. Without that notice, assume no parallel work, branch from `main`, and expect to merge into it. Never merge into `main` or push without the human's go-ahead.

### Two Agentic Execution Modes: Default and Autonomous

In both modes, the Agentic Development Contract still applies. The agent should not run off and build multiple sub-systems, but should follow the `Agentic Development Approach` instead.

The two modes are explained next.

#### Default Mode - use this unless other instructed

- **Default** mode is write, then hand off. After implementing a change, do not run build, test, compile, or integration commands yourself to validate it. Cheap static diagnostics (language-server error checks, lint-on-save) are fine, they produce no large log output.
- End every implementation turn with an explicit "Commands to run" block: exact commands, the directory to run them from, and what a pass looks like.
- Wait for the human to run those commands and report the result before assuming success or making further changes on that assumption.
- If the human reports a failure, diagnose from the pasted output. Do not re-run the command yourself to reproduce it, ask for more output if what was pasted is insufficient. The human in the loop is key to this mode.
- This applies to every ecosystem in this repository: Maven/Java, Python/pytest, Yarn/Playwright, Docker Compose, database migrations, and any future build or test tooling.
- Only run a command yourself when the human explicitly asks you to, or when a single-file syntax check is faster than an explanation and stays within the current tool call's scope.
- Never state a change "passed," "works," or "is validated" unless the human reported that the commands succeeded, or you ran them because the human explicitly asked you to.

#### Autonomous Mode - use this only when explicitly instructed

- **Autonomous** mode allows the agent to run build, test, compile, or integration commands itself to validate changes. Use this mode only when explicitly allowed by the human.
- The human trusts your judgment and expects accurate self-validation, testing, and verification in this mode.
- NB: **THIS MODE DOES NOT OVERRIDE THE Agentic Development Contract**: you must still check in with the human when making design decisions.

### Pause For Architectural Guidance

In BOTH **Default** and **Autonomous** modes, do not make design decisions unilaterally without consulting the human for architectural guidance. In this way, we will work together on alignment and ensure that ADR logs are available to you and other agents, that help shape our understanding as we work together.

## Repository Topology and Documentation Governance

If your user requests a named "unit of work", read:

1. Any relevant accepted architecture decision in `docs/architecture/decisions/`
2. The unit plan in `docs/developer/plans/<unit>.md`
3. The unit status record in `docs/developer/status/<unit>.md`
4. Any active human review request in `docs/developer/review/<unit>-review.md`

Do not treat a plan as a status log. Do not begin a physical path move before the applicable ADR and path manifest are approved.

When trying to estimate scope, the measure should not be `agent days`, but rather, aim to estimate the cost in `tokens` or `ai-credits`. We can validate this after implementation and the record of estimated and actual might help with future planning.

### Repository Topology

- `ontology/` owns semantic assets only: normative ontology sources, shapes, vocabularies, projections, semantic examples, semantic fixtures, and semantic documentation.
- `tools/` owns executable reference implementations and developer-facing toolchains.
- MORK and SPC semantic assets live under `ontology/mork` and `ontology/spc`. Their executable projects live under `tools/mork` and `tools/spc`.
- `workers/` is a deployable asynchronous runtime package and remains a top-level root.
- `platform/`, `apps/`, `packages/`, `contracts/`, `deployment/`, and `test/` remain top-level roots unless an accepted ADR says otherwise.
- DO NOT introduce new directory structure, especially at the repo root, without an accepted architecture decision.

### Documentation Lifecycle

Most ideas start out life as `sketches`. Some may be captured as a plan rather than a sketch. Each active unit has one stable identifier, such as `iri-policy-p013`.

- `docs/developer/sketches/<unit>.md` defines the broad shape of an idea. Sketches can become plans. A sketch can be updated freely. Once a sketch becomes a plan, it will typically be deleted. Some legacy sketches may still exist and should be left alone until the user has reviewed them with you.
- `docs/developer/plans/<unit>.md` defines scope, dependencies, steps, decisions, and planned validation. Change it only when the plan changes. 
- `docs/developer/status/<unit>.md` is the sole authoritative live state. Update it after every material implementation action, validation result, blocker, or handoff.
- `docs/developer/review/<unit>-review.md` is the human review request. It contains scope, artifacts, exact `mise` commands, pass criteria, open questions, and a link to the matching status record. Create or refresh it before handoff. Archive or close it after disposition.
- `docs/developer/plans/technical-debt.md` is a special plan: the register of technical debt spotted with no planned home, a shortcut, a gap between what a component claims and what it does, or a check that does not run. It is not a unit and has no status record. Add an entry when you spot such debt and no plan owns it, and remove it, naming the plan, when a plan takes it on. Never record outstanding work there (features, follow-ups, deferred slices): those belong in their unit's plan.
- Never create a second active status record for a unit.
- Every active review record must name an existing matching status record.
- `docs/developer/` root holds durable guidance only. Do not create a new `current/` directory.

### Epic Decomposition Model

An **epic** is a large work package spanning multiple phases, teams, or quarters with complex interdependencies. Epics are broken down into smaller, manageable units.

**Hierarchy:** Epic ⇒ Phase ⇒ Slice ⇒ Milestone

| Unit | Meaning | Ends with | Documentation |
|---|---|---|---|
| **Epic** | A large cross-phase work package with a stable owner (e.g. "LATTICE platform delivery", "Store SPI", "Ingestion pipeline") | Never; only the implementation phases end. Epic itself has no completion gate, only status tracking | `docs/developer/plans/<epic>.md` (marked `Unit type: Epic`) + individual phase plans + epic status file |
| **Phase** | A cohort of slices that together produce a demonstrable capability (e.g. "Phase 0: Decisions and foundations") | Phase gate: integration milestone + docs updated + ADRs ratified. **Status file created.** | `docs/developer/plans/<phase>.md` + `docs/developer/status/<phase>.md` |
| **Slice** | One agent work package (0.5–4 agent-days). A single coherent change, independently reviewable and testable | **Human validation gate.** Status file updated. | `docs/developer/validation/<slice-id>.md` (Validation Pack) |
| **Milestone (Mn)** | Cross-component demonstrable outcome, exercised end-to-end in the local stack (e.g. "M0: Walking skeleton") | Human demo + E2E suite green. Recorded in phase status. | Phase plan and phase status |

**Epic-specific governance:**

- The epic plan document (e.g. `lattice-platform-agentic-development-v0.2.md`) outlines phases, tracks, dependencies, and milestones at a high level.
- The epic plan is marked explicitly as `Unit type: Epic` and states that it will be decomposed into individual phase plans.
- **No epic-level review is created until all phase plans are authored and all acceptance test suites pass.** The epic remains in status-tracking mode, referencing phase-level status and review documents.
- Each phase gets its own plan (`phase-0-plan.md`, `phase-1-plan.md`, etc.) with scope, hard orderings, slice boundaries, and test taxonomy.
- Each phase gets its own status file (`phase-0-status.md`, etc.) updated at the phase gate.
- Each phase may get a review file only once that phase's acceptance tests are ready.

**Slice sizing rule:** If a slice's Validation Pack contains more than ~15 test cases or touches more than two modules, split it. If it contains fewer than 3, merge it. Skeleton slices are exempt (they contain 1 test: the build smokes).

**The mandatory shape of every slice:**

Every slice, without exception, delivers:

1. **Code** in one or two modules only.
2. **Validation Pack (VP)** — a single markdown file at `docs/developer/validation/<slice-id>.md` containing:
   - *What invariant does this slice protect?* (1 paragraph, in architecture language, citing G-nn/A-nn)
   - *Test case table*: ID, Given/When/Then in plain language, test level (L0–L8), the invariant it protects, pass criterion, and whether it is a positive or negative case.
   - *One command to run everything*: e.g. `mise module:check` or `mvn clean:verify`. If it is not one command, the slice is rejected on process grounds.
   - *Expected artifacts* the human should inspect (golden files, capability report, canonicalisation trace, screenshots).
   - *Deliberate non-coverage*: what this slice does **not** test and which later slice covers it.
3. **Traceability update** — Update `docs/developer/INDEX.md` to record the slice's completion status and link to its validation pack. Optionally maintain `docs/traceability/matrix.csv` rows linking slice ⇒ G-nn/C-nn/A-nn ⇒ test IDs if this slice addresses a gap. See `docs/developer/INDEX.md` for current traceability model.
4. **Doc delta** — if the slice contradicts or extends a normative document, the document is edited *in the same slice*. No "docs later".

**Human validation gate protocol:**

- **Step 1 — Review the VP before running anything.** The human judges whether the test cases are the *right* tests: do they actually pin the invariant? Are the negative cases the ones that matter? Is anything important listed under "deliberate non-coverage" that should not be?
- **Step 2 — Run the single command.** If it is not one command, the slice is rejected on process grounds.
- **Step 3 — Inspect named artifacts.** Golden files, traces, reports, screenshots.
- **Step 4 — Adversarial probe.** The human picks one test case and asks the agent to demonstrate it *fails* when the implementation is deliberately broken (mutation check). This catches vacuous tests, which is the dominant failure mode of agent-authored suites.
- **Step 5 — Sign off** in `docs/developer/validation/LOG.md` with slice ID, date, name, and any accepted deviations.

**Test taxonomy (L0–L8):**

The level of testing discipline for a slice should be verified during planning.

| Level | Name | Runs where |
|---|---|---|
| **L0** | Build smoke (compiles, runs, no-op test passes) | Local + CI |
| **L1** | Unit / pure-function | Local + CI |
| **L2** | Property & determinism (same input → same digest; permutation invariance; law checks) | Local + CI |
| **L3** | Contract (JSON Schema validation both directions; cross-runtime fixtures; OpenAPI conformance) | CI |
| **L4** | Component integration with real infrastructure (Testcontainers: databases, brokers, stores) | CI |
| **L5** | System E2E over the local compose stack via HTTP/AMQP only | CI nightly + on demand |
| **L6** | UI E2E (Playwright) against the compose stack | CI nightly |
| **L7** | Non-functional: SLO benchmark, capability/benchmark report, load profile | CI weekly + gated releases |
| **L8** | Hostile / security suites: cross-tenant probe, injection corpus, scoping escape | CI nightly |

**Non-weakening rule:** No slice may delete, skip, `@Disabled`, or loosen a test from a previous slice without an ADR-grade justification recorded in the VP and countersigned at the gate.

### Changing an ontology document

Follow this procedure for any change to a document under `ontology/**/spec/` or `ontology/**/vocab/`, or to a `shapes/` or `projection/` directory. It was written from CCS F1 (2026-10-03), which changed Foundation and re-pinned 24 importers. Read [the versioning policy](../docs/architecture/ontology-versioning-policy.md) (ADR-A86, ADR-A113) first.

**1. Find the source of truth.** Some layers' READMEs are literate specifications: their fenced ` ```turtle-spec `, ` ```turtle-vocab ` and ` ```turtle-shapes ` blocks generate the `.ttl` files, and ` ```turtle-example ` blocks are illustration only. Foundation, Wording, Behaviour and Surface are literate, checked by tests or CI. For those, edit the README, never the generated `.ttl`, then regenerate:

```bash
python tools/literate_extract.py ontology/<layer>/README.md --layer <layer> --root . --shapes <shape files>
```

- `--shapes` lists the shape files, relative to the layer, in the order of the README's ` ```turtle-shapes ` blocks: one block per file, and the count must match. Foundation: `shapes/constraints.ttl`. Wording and Surface: `shapes/structural.ttl shapes/constraints.ttl`. Behaviour: `shapes/structural.ttl`.
- All ` ```turtle-spec ` blocks are concatenated, in document order, into `spec/<layer>.ttl`, and all ` ```turtle-vocab ` blocks into `vocab/<layer>-vocab.ttl`. The ontology header (`owl:Ontology`, `owl:versionIRI`, `owl:imports`) is itself a block, so a version bump is an edit to the README.
- Add `--check` to compare without writing. It exits non-zero and names each drifted file.
- Before relying on a README as the source, run `--check` on it unchanged. If it already drifts, the README is not the source yet: compare the extracted and committed graphs (`rdflib.compare.graph_diff` over `to_isomorphic` graphs) before regenerating, and either restore it (as F1 did for Foundation) or record the drift in [technical-debt.md](../docs/developer/plans/technical-debt.md).
- Persistence and the applied modules are not literate: edit their `.ttl` directly.

**2. Bump the version.** At major version zero an additive change is a MINOR, and a breaking one is a MINOR marked breaking (ADR-A113). Change the document's `owl:versionIRI`. A `shapes/` or `projection/` directory is versioned by its `.version` file: bump it when any file in it changes or is added.

**3. Compute the cascade, never trust a count.** A document whose only change is a re-pinned import takes the imported change's bump level (ADR-A86). Build the import graph from every in-scope document, using `find_in_scope_ttl_files` and `extract_version_iris` from `tools/ontology_version_check.py`, and close it transitively from the changed version IRI. MORK's version IRIs are `http://`, not `https://`. A document with no version of its own (a MORK example) still re-pins, with no release.

**4. Re-pin, in one pass.** Version IRIs appear in spec and vocab files, literate README blocks, `tools/surface/src/surface/namespaces.py` (`SURFACE_ONTOLOGY`), examples and tests. Replace exact IRIs with one regex alternation over the whole old-to-new mapping, so no replaced IRI is replaced again. Leave alone:
- `docs/architecture/ontology-releases.md`: generated, and its rows are never edited.
- `tools/test_ontology_releases.py`: unit tests of release names.
- `tools/fixtures/import_guard/`: self-contained fixtures.

Tests also build IRIs from fragments, such as `LATTICE + "behaviour/0.10.0"`, which a search for full IRIs misses. Move a test that locates the current document, or asserts its current version and imports, to the new version. Keep a test that asserts history, a release row or a release note, unchanged.

**5. Regenerate the derived files.**

```bash
mise run build:ontology-catalog
```

```bash
mise run build:ontology-releases
```

The second adds a row per new version and prints the tags to create. Tags are the human's: never create or push them. They are created after the change is merged into `main`, on the merged commit.

**6. Record the release.** Add an entry to the "Release notes" section of each README that has one (Foundation, Wording, Behaviour, `applied/capacity` at the time of writing), including re-pin-only entries.

**7. Check.** Run the suites that read ontology versions:

```bash
mise run check:ontology-catalog
```

```bash
mise run check:ontology-versioning
```

```bash
mise run check:import-guard
```

```bash
mise run build:mtp
```

```bash
mise run check:mtp
```

Also run `mise run check:persistence`, `mise run check:python-root`, `mise run check:vocabulary` and `mise run check:mork-compilers`, and the literate `--check` for every literate layer. `build:mtp` rewrites `ontology/mork/mtp/data/pins.lock.json` whenever MORK's version changes, a re-pin included, since its ontology hash covers the header: commit the regenerated lock. If Persistence's spec, examples or templates changed, regenerate their SPARQL with `mise run build:persistence-execution` (generated, not committed).

**8. Make sure the code under test is this checkout's.** Editable installs can point at another clone. Check before running anything that imports `persistence`, `lattice_minting` or `surface`:

```bash
python -c "import persistence, lattice_minting, surface; print(persistence.__file__, lattice_minting.__file__, surface.__file__)"
```

If a path is outside this checkout, ask the human to re-run the matching `mise run bootstrap:*` task, or put `tools/persistence/src`, `packages/minting/python/src` and `tools/surface/src` first on `PYTHONPATH`.

### Decisions and Links

- Architecture decisions live only in `docs/architecture/decisions/`.
- New or updated links must use canonical paths. Do not introduce `docs/adr/` references.
- When moving files, prefer using `git mv` if possible, and update all source, configuration, CI, documentation, and website references in the same migration unit.
- Historical records may describe old paths only when needed for context. Add a relocation note and link to the canonical path.

### Toolchain

- `mise` is the only task-orchestration entry point unless ADR-A29 is superseded.
- Maven, Yarn 4, Python project tooling, and Mix remain their own dependency authorities.

#### Shell activation

Installing `mise` is not enough on its own — a freshly opened shell will not have `mise`-managed
tools (`mvn`, `python`, `node`, etc.) on `PATH` until the shell profile activates it.

- If a package manager installed `mise` somewhere it did not add to `PATH` itself, locate the
  installed binary first and add its directory to `PATH` before activating.
- POSIX shells (`bash`/`zsh`): add `eval "$(mise activate bash)"` (or `zsh`) to the shell's rc file.
- PowerShell: add `mise activate pwsh | Out-String | Invoke-Expression` to `$PROFILE`. On Windows
  PowerShell 5.1 (not PowerShell 7+), also set `$env:MISE_PWSH_CHPWD_WARNING = "0"` first to
  silence an unsupported-feature warning that otherwise prints on every new session.
- Verify with a brand-new shell (not the current one), not by patching `$env:PATH`/`PATH` in the
  already-open session, which does not prove the profile change actually works.

#### Restricted or mirrored package registries

Some networks block direct access to public package registries (PyPI, npm's registry, etc.) and
require going through an internal mirror instead. If package installs fail in a way that looks
like a network policy block:

- A plain connection failure or an HTTP redirect to an unrelated page is an obvious block.
- A **hash mismatch reported by `pip` even though no hash-pinned requirements file was given** is
  a less obvious symptom of the same thing — some network intermediaries substitute a different
  response body (e.g. a block notice) for the blocked file while leaving the package index
  metadata (and therefore the expected hash) untouched. Confirm by fetching the exact failing
  URL directly and inspecting the body before concluding it is a corrupted download.
- If TLS interception is in play, a downstream tool (e.g. Node/Corepack) may fail with something
  like `UNABLE_TO_GET_ISSUER_CERT_LOCALLY` even though the OS trusts the intercepting certificate.
  That tool needs to be told about the relevant CA bundle separately (e.g. Node's
  `NODE_EXTRA_CA_CERTS`).
- Fix this by pointing the package manager's **user-level** config at an approved internal mirror
  or index, never by editing files in this repository and never by trying to route around the
  network policy. For `pip` specifically, this is a `pip.ini`/`pip.conf` file outside the repo
  (`pip config file -f user` prints the exact path for the current OS).
- Any index URL, mirror hostname, or credential needed to reach such a mirror is
  environment-specific. Keep it in user-level configuration or a secret store, never in a file
  tracked by this repository, and never in an agent's persisted notes that might get published.
- `mise.toml` task `run` strings are interpreted by `cmd.exe` on Windows and by a POSIX shell
  elsewhere. Use double quotes, not single quotes, around any argument containing shell-special
  characters such as `[`, `]`, or `,` (e.g. pip extras like `"./pkg[test]"`) — `cmd.exe` does not
  strip single quotes, so they end up passed through literally to the underlying command.

## General Guidelines

- Do not use semi-colons in English text. Use periods or commas instead.
- Use colons sparingly in English text. Do not use one to join two clauses or to lead into an explanation ("A regime is stated once: its clause states it"). Write two sentences, or one with a conjunction. A colon may introduce a list, a table or a quotation.
- Be concise, do not repeat yourself. Avoid unnecessary verbosity.
- Avoid over-explaining. Say things once and cross-reference if really needed.
- Avoid superlatives.

### Documenting DL/OWL/TTL Ontologies

Try not to explain your design decisions in multiple places. Avoid explaining why you did not use a certain pattern or construct, especially if you've just explained why you did use a different one. If you feel the need to explain your design decisions, do so in a single place and cross-reference it from other places.

**Use `rdfs:domain` and `rdfs:range` sparingly.** They are not constraints on how a property may be used. They tell a reasoner something about everything the property is used with: any individual that has the property *is* an instance of the domain, and any value *is* an instance of the range. A domain of `ins:LegalRelation` on `ins:activity` would make every trigger that names an act a legal relation. Declare a domain or range only where it:

- gives useful entailment at design time, or
- restates something a SHACL shape already validates, so the two say the same thing.

Otherwise leave it out, say the subject and value in the property's comment, and let a shape check use. Before adding one, ask whether *every* individual that could carry the property really is an instance of the class.

**A "Formalisation" section introducing a generated theory (ADR-A-FM2) names no tool.** Title it "Formalisation", not "Formalisation (Isabelle/HOL)" or similar: the tool is a decision (ADR-A-FM1, ADR-A-FM2), not a fact about the layer, and naming it in a heading is one more place to update if it ever changes. Say only what the type itself means (its ordering, its reading, what two readings disagree on) — not the ADR's number, the generation mechanism, the epic principle that explains why only the datatype is generated, or a past evaluation's findings. Those are said once, where they were decided, and cross-referenced, not repeated beside every generated block. Add more narrative only if the type itself is complex enough to need it (a union type whose cases are not obvious, say) — a closed enumeration of a few named values usually is not.

### When running the Ponytail skill

The Ponytail skill pushes for the smallest model and the shortest diff. In an ontology, that must never cost logical correctness. Before proposing or applying a simplification, check each of these:

- **RDF has no override.** A merged view of two nodes is the union of their triples. Do not let one node "inherit" another's properties and replace some of them, such as a bound relation stating only what differs from its template: the result has both values, and breaks every "exactly one" constraint. Restate in full, and let a generator do the repetition.
- **Derivable in the examples is not derivable in general.** Before deleting a property because the examples could compute it, search the sketches' scenario catalogues and the decisions for a case where it differs. `ins:party` matched the relations' parties in every C6 example, but third-party beneficiaries (CC-Q4) and separate execution (S90) make it independent data.
- **Open world.** Removing an assertion is not asserting its negation. A reasoner infers from what remains, so check what it now infers, and what it can no longer distinguish.
- **Who reads it without a reasoner.** SHACL and the compilers read asserted triples only. A fact moved from asserted data into an axiom disappears for them.
- **Cross-check before applying.** Search every sketch and plan that names the term, LATTICE's and the epics that build on it (CCS, AIR, NRS), for a scenario the simplification breaks. If one exists, stop and discuss it with the human.
- **Keep what the decisions require.** A simplification that contradicts an accepted ADR is a new decision, not a cleanup.

### Authoring SHACL-SPARQL shapes

These rules come from defects found at verification. Follow them in every `sh:sparql` constraint.

- **Declare prefixes inside the query**, with `PREFIX` lines at the top of `sh:select`, as `ontology/eligibility/shapes/constraints.ttl` does. Do not use `sh:prefixes` pointing at a namespace IRI: it needs `sh:declare` triples, and pySHACL silently falls back to the file's `@prefix` lines where other SHACL engines fail.
- **Make sure a subject with zero matches still produces a row.** A pattern that must match before it is counted returns no row for a subject with none, so a check on the count never runs and "exactly one" passes when there are none. Put the counted pattern in `OPTIONAL`, so the count is 0.
- **Choose the counting form by the number of counts.**
  - One count: a flat query, `OPTIONAL { … ?x … }` then `GROUP BY $this HAVING (COUNT(DISTINCT ?x) != 1)`.
  - Two or more independent counts, or high cardinality: one grouped sub-query per count, so the counts do not multiply each other and the store can plan them separately. Each sub-query anchors the subject and makes its counted pattern optional, for example `{ SELECT $this (COUNT(DISTINCT ?x) AS ?n) WHERE { $this a ex:C . OPTIONAL { $this ex:p ?x } } GROUP BY $this }`. A sub-query without the anchor drops zero-count subjects from the join.
  - Several flat `OPTIONAL`s in one group multiply rows. `COUNT(DISTINCT …)` still counts correctly over them, but plain `COUNT` and `SUM` do not.
- **Disable a SPARQL constraint by breaking a triple pattern, never with `FILTER (false)`**, when probing that a test catches a broken shape. Under pySHACL a constraint whose filter is constant false reports every focus node, so the probe passes for the wrong reason.
- **Test every cardinality rule at zero, not only at too many.** A negative case with two values does not catch a query that drops subjects with none.

### Thinking / Reasoning for Coding

Your user may present design collateral, architectural guidance, and coding standards. These must be adhered to at all times. Readability and clarity of intent is as important as working code that passes tests.

Always consider the architectural quanta of the code you are writing and carefully consider whether your code might implicitly or explicitly change the dependencies within the codebase. If in chat mode (as opposed to agentic / co-work), prefer to clarify impacts with your user before making them.

### Thinking / Reasoning for Writing

Your primary mode of operation should be critical thinking - looking for logical consistency and challenging logical errors, gaps, or misunderstandings.

You should consider whether to present your own arguments as hypotheses or determined facts, generally adopting a stance of curiosity rather than dogmatism. This must be balanced against the need to maintain a clear and concise writing style (see below).

### Writing Style / Voice 

Regardless of the style your user has requested (formal, informal, etc), try to be concise and avoid unnecessary verbosity. Where your user has requested that you provide output that is "comprehensive" and "detailed", this refers to the depth of subject matter understanding and analysis required, not the number of words used.

Think about whether giving examples will be helpful, and if you do, give them in a clear way. When giving examples, do NOT just hop into them via a colon: like this, or like that, you see? Instead, you should explain that you are giving an example. For example, the following is very confusing:

```markdown
From the moment the instrument takes effect it is in each regime's initial state (`bhv:initialState`): in force, performing, unaffected.
```

That reads as those `initialState` has a set of three value, which is neither correct nor helpful. In that text, why are the "example" states being given at all? They add nothing to the text. 

Here is a good example of what you SHOULD do instead:

```markdown
A *party* is an entity (e.g. person or organisation) bound by or benefiting from an instrument.
```

You can use "for example" instead of e.g. anywhere as well. 

### What To Avoid

The following MUST be avoided if at all possible, breaking these rules only under exceptional circumstances.

- Do not use semi-colons in English text. Use periods or commas instead.
- Use colons sparingly in English text. Do not use one to join two clauses or to lead into an explanation ("A regime is stated once: its clause states it"). Write two sentences, or one with a conjunction. A colon may introduce a list, a table or a quotation.
- Be concise, do not repeat yourself. Avoid unnecessary verbosity.
- Avoid over-explaining. Say things once and cross-reference if really needed.
- Avoid superlative adjectives. These must be reserved for factual extremes (e.g., "the tallest building") and are banned from use for emphasis (e.g., "the best solution," "the ultimate guide"). 
- Try to avoid "It's not X, it's Y" binary reframes, replace them with direct statements. 
- Avoid formulaic transitions such as "Furthermore," "Moreover," "Additionally," and "In conclusion" at the start of sentences. 
- Avoid vague meta-commentary like "It is important to note that," "In today's digital age," and "This serves as a testament to." Keep it short and succinct.
- Do not coin technical terms from insurance market vocabulary. A word with a market meaning reads as that meaning to an insurance reader, and the meaning differs between markets. "Binder" is the example: in insurance it names a binding authority or a temporary cover note. Use it only in its market sense. Producing bound meaning from stated meaning, a wording's variable values and an instance's parties is **instantiation**, and what performs it an **instantiator**, as Persistence's `instantiate` fills its templates with parameters. Check any new technical term against `docs/glossary.md` and the insurance modules in `ontology/applied/insurance/` before using it.
  - **Exception: "bound".** It has a settled technical meaning, as in a bound variable, so "bound meaning", `ins:boundIn` and `ins:boundFrom` stay (CC-D12). It is still a market word ("the risk is bound"), so say "bound meaning" or "bound term", never "bound" alone where an insurance reader could read it as cover.
  - **Leave SPC alone.** SPC's "binder" is the process-calculus term (`rec X.B` binds a recursion variable) in a published specification. Do not rename it.
- Keep substrate and layer READMEs domain-neutral. Insurance is LATTICE's primary target, but the substrate is a framework for any domain. Do not appeal to "the market" or a market's practice to explain a term: explain it from law, contract drafting or computing. Do not cite Open CBAA or other downstream projects as examples in a layer README: they depend on LATTICE, not the reverse, and a reader will not know them. Sketches and plans may name them. Prefer examples from several domains (lending, licences, trials, warranties) over insurance ones.

### What To Reduce

The following styles should be kept to a minimum.

- Rhetorical questions that are followed immediately by an answer. In general, do not pose rhetorical questions and, if you choose to, do not give their answer (as doing so ruins the rhetoric)
- Emphasis via short sentences, e.g., "Short sentences. For Emphasis. Often in threes."
- Excessive use of metaphores, e.g., "A symphony of the unnecessary tapestry of metaphores".
