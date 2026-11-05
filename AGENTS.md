# LATTICE: instructions for AI agents

These rules apply to every task in this repository and in projects built on LATTICE. Procedures and
reference material live in skills, loaded when a task needs them (see the last section). This file
is the source of `.github/copilot-instructions.md`. Edit it here, then run
`mise run build:agent-guidance` ([ADR-A117](docs/architecture/decisions/ADR-A117-agent-guidance-and-skill-library.md)).

## The contract

We work iteratively. The agent suggests what to build next, and the maintainer verifies the approach
along the way.

- **Default mode, unless told otherwise.** Write, then hand off. Do not run build, test, compile or
  integration commands to validate a change. End the turn with the exact commands to run, where to
  run them from, and what a pass looks like. Cheap static checks, such as a single-file syntax
  check, are fine.
- **Autonomous mode, only when the maintainer says so.** Run the checks yourself and report their real
  results. It does not change anything else in this contract.
- **Never claim a check passed** unless it ran and passed. Say "authored, not yet run" and give the
  command.
- **Read what a command printed, all of it.** A command that exits zero still reports: `mise run build:knowledge` prints a note naming a register cell it could not read, and a benchmark prints the engine version it actually ran on. A tail of the last few lines hides both. Every figure, version and verdict in a handoff comes from output that was read in full, never from what another agent said it saw.
- **Pause for design decisions.** Do not make an architecture or modelling decision alone. Present
  the options and their consequences (skill `lattice-design`) and wait for the answer.
- **When two standards conflict for a change, stop and ask the maintainer** before proceeding, and record the conflict in `docs/developer/pending-design-decisions.md`, so conflicts that recur show which standards to rework. Standards have no precedence order.
- **The git hooks are a floor, never a ceiling.** `mise run bootstrap` installs them ([ADR-A133](docs/architecture/decisions/ADR-A133-git-hooks.md)). They run the quick checks a commit, or a merge into `main`, touches, never a test suite, and never block a push. The test suites `check` leaves out run by convention before a merge, and the handoff lists each with its result (skill `lattice-lifecycle`). Never bypass one (`--no-verify`, `LATTICE_HOOKS_SKIP`) without recording which and why in the slice's Validation Pack, and never report a passing hook as a passing `mise run check`.
- **Never commit, merge, tag or push** without the maintainer's go-ahead. Release tags are always the
  maintainer's to create. Do not mark an ADR Accepted yourself.
- **Mark before you touch.** Before the first edit of anything you pick up, a slice, a unit or a plan, and above all a slice of another plan, set its row on the slice board of its home unit's status record to `building <day>`, run `mise run build:work`, and commit that alone (skill `lattice-lifecycle`). An edit made before the mark is invisible to `mise run work:board`, and every view built from the board is then wrong.
- **Know who is here.** Before the first edit in any checkout, run `mise run work:here`. Where it lists another live session building there, or you were asked to review, say who is here and ask the maintainer before writing.
- **Attend to ROADMAP.md at every handoff.** Run `mise run build:roadmap -- --fetch` for its generated sections, read each hand-written section against the records the work changed and refresh what disagrees, at the events the lifecycle skill names for each section, in the same commit. The handoff report names the sections refreshed and the sections checked. A roadmap that no handoff touched is stale by then (STD-307).
- **Ask the board, not the branches.** `mise run work:board` says where every unit and slice is across every local and remote branch, in a few hundred tokens. Read a branch only after it.
- **End a "what next" report** with 🔴 PLAN FIRST when something must be decided first, or
  🟢 READY TO BRANCH when a new branch is due.

## Where things are

<!-- BEGIN GENERATED where-things-are. Written by `mise run build:agent-guidance` from repository-catalogue.md. Do not edit between the markers. -->

| Root | Owns |
|---|---|
| `ontology/` | semantic assets only: sources, shapes, vocabularies, projections, examples, their documentation |
| `tools/` | executable reference implementations and developer toolchains. `tools/testing/` holds test-support packages, used only by tests, checks and benchmarks (ADR-A125) |
| `benchmark/` | checks that measure, run on demand and never part of `check`. They fail on a wrong result, never on time (ADR-A124) |
| `platform/`, `apps/`, `packages/`, `contracts/`, `deployment/`, `workers/`, `test/`, `spikes/` | services, applications, libraries, data contracts, the local environment, the worker runtime, end-to-end suites, experiments |
| `docs/architecture/` | architecture documents and the ADRs, in `decisions/` |
| `docs/developer/` | sketches, plans, status records, review requests, Validation Packs, the registers, and durable guidance |
| `.claude/skills/` | the skills below |

<!-- END GENERATED where-things-are -->

How each triple store behaves, and how we found out, is recorded in [docs/architecture/triple-store-discovery.md](docs/architecture/triple-store-discovery.md). Before relying on what a store does with SPARQL, find the findings that touch it with `mise run graph:ask -- find <the behaviour> --kind discovery` and read each with `read TSD-nn`, reading the whole record only when the query answers weakly. Add to it when you find something new (skill `lattice-probing`).

How to write a SPARQL constraint, a generated query or a test fixture that runs in reasonable time is recorded in [docs/architecture/efficient-queries-and-shapes.md](docs/architecture/efficient-queries-and-shapes.md) ([ADR-A128](docs/architecture/decisions/ADR-A128-efficient-queries-and-shapes.md)), and its rules are standards in the register. Before writing or changing one, find the rules that apply with `mise run graph:ask -- find <what the query does> --kind standard --activity query-writing` and read each, reading the whole record only when the query answers weakly. It says which of its rules hold for any engine and which only for rdflib, pySHACL or our harness.

**Bump an ontology version with `mise run version:bump`, and point the maintainer at it.** Without `--layer-target` it moves the substrate release, and with `--layer-target <module>` one standalone or applied module, by `--increment major|minor|patch` or `--new-version X.Y.Z`, its shapes too with `--with-shapes` or alone with `--only-shapes`. It extracts the READMEs it changed and regenerates the catalogs and the release register (CAP-105). Its rules are in `tools/bump_version.py`, read when asked how it works, never restated from memory: the substrate is one release (ADR-A129), every other module is released on its own, a module's spec documents move in unison (STD-230), and its shapes share one `.version`. `mise run check:ontology-versioning -- --base-ref main` names each module that needs a bump and the command for it.

Do not add a directory at the root, or a new kind of directory anywhere, without an accepted ADR.
`mise` is the only task entry point (ADR-A29). Every command you run or give the maintainer goes
through it, as `mise run <task>` or `mise exec -- <command>`, never a bare `python`, `pytest` or `pip`.
Only mise picks up this checkout's `.venv` and its dependencies, and a bare interpreter is the global
one (skill `lattice-mise`). The [developer guide](docs/developer/developer-guide.md)
describes every tool.

Code finds the repository root and every directory the [repository catalogue](repository-catalogue.md) names through its reader, `tools/lattice_repo_catalogue.py`, by a module's role or a root's or documentation area's name, such as `area("developer")` for the registers, never from `__file__` or a path written in code (STD-273, skill `lattice-mise`'s Finding paths).

## Asking the knowledge index

The knowledge index and the work board are Вивід's, `vyd`, installed by `mise run bootstrap` at the version `mise.toml` pins and bound by `vyvid.toml` at the root ([ADR-A152](docs/architecture/decisions/ADR-A152-vyvid-adoption.md)). Its general rules, ask the index before a decision and before searching the files, read what answers, and report the misses, are the rule file `vyd install --client` writes for every project, and `vyd context` run in this checkout lists every layer of rules that applies here, the project's last. Every `vyd` command goes through `mise` (ADR-A29): `mise run graph:ask -- <find|read|node|reaches|exists|sparql|misses|gap|close> ...`, `mise run build:knowledge`, `mise run check:identifiers`, and `mise run vyd -- <args>` for the rest. Where `vyd` is missing or says it did not run, each says what it skipped and never blocks (PRI-79). What is LATTICE's:

- **What the index holds.** The decisions, mechanisms, capabilities, patterns, principles, standards, store findings, the backlog of ideas not yet planned (`--kind backlog`, `docs/developer/backlog.md`), the questions plans and sketches raise, and, only when asked with `--kind term`, the declared ontology terms. `vyvid.toml` declares each family and the register that defines it. The triple-store findings and the query-writing standards answer from Вивід's `triple-stores` domain under its identifiers while LATTICE's copies stay (ADR-A152 decision 7).
  ```bash
  mise run graph:ask -- find <the problem in your own words> --activity physical-data-modelling --quality concurrency --phase runtime
  mise run graph:ask -- read <ID>
  ```
  `--activity`, `--quality` and `--tech` raise matching entries and hide none. `--kind`, `--phase` and `--audience` filter exactly, so use them only where an entry outside them could not answer. The [facet register](docs/developer/facets.md) defines every value.
- **Terms only when the question is about a term.** `--kind term` searches the declared classes and properties, to learn what one means, whether one exists before declaring one, or what restricts it, as in `find which property derives one account per key value --kind term`. Leave it off for every other question, since ranked together terms push the entries that answer out of the top five, hit@5 0.79 against 0.93. When modelling, ask both ways, once with no kind and once with `--kind term`. `exists <word>` finds a term by its name.
- **Read the flags and the line under each row.** `BL` says an unbuilt backlog idea bears on the entry, `!` that it states a case it does not cover, `~` that the text was superseded or narrowed by a later addendum, `TD` that an open debt bears on it, and `?` that it is Proposed. `read <ID>` prints the entry and every entry linked to it. A decision holding several numbered decisions is indexed under one claim, so ask for the rule, read the decision the answer names, and treat a rule found only by searching the files as a register gap (STD-272).
- **Questions and slices are asked for.** A question raised by a bold lead or a table row in a plan or a sketch is an entry, `--kind question`, and `--exclude question` keeps every other kind. A slice is shown only with `--kind slice` or by name, as in `find WB-10` (ADR-A134 decision 34). Where a slice stands is `mise run work:board`'s question, and what a unit is doing now is in `docs/developer/status/<unit>.md`.
- **A register gap is technical debt.** An empty or weak answer never proves that nothing exists. Fall back to the documents and the code, and where they hold an answer no register entry does, add the entry in the same change or a row to `docs/developer/technical-debt.md`, and tell the maintainer (STD-272). Record what reading found that the index did not say as you find it, `mise run graph:ask -- gap "<what you found>" <ID> <path:line>`, and run `close <ID>` in the change that writes the signpost. At each handoff, report `mise run graph:ask -- misses --near` and say which column or edge would have carried each.

## Writing

Every piece of text, in documents, code comments, commit messages and replies:

- do not put newlines in markdown text for formatting. Modern editors can word-wrap long lines. Newlines should be used to create space between paragraphs: don't assume a line length and enforce it with newlines. When you edit a hard-wrapped paragraph or list entry, join it onto one line in the same edit, since the wrapping check reports a file's wrapped lines whichever edit touched it.
- no semicolons. Use periods or commas
- colons sparingly, never to join two clauses or to lead into an explanation. A colon may introduce
  a list, a table or a quotation
- concise. Say a thing once and cross-reference it
- no superlatives for emphasis, no "it's not X, it's Y" reframes, no formulaic transitions
  ("Furthermore", "Moreover", "In conclusion"), no meta-commentary ("It is important to note that")
- introduce an example as an example ("for example", "e.g."), never by hopping into it after a colon
- keep rhetorical questions, emphatic short sentences and metaphors to a minimum
- think critically. Look for logical gaps and errors, and present arguments as hypotheses where they
  are not settled
- show structure with metadata a tool reads, and state a meaning once where it is defined rather than restating it in prose around it
- name a thing by the term this repository already uses for it, never by a name another layer already defines for something else
- do not coin technical terms from insurance market vocabulary. Producing bound meaning is
  **instantiation**, done by an **instantiator**, never a "binder" (skill `lattice-ontology-authoring`)
- call a class that is a member of `fnd:Versioned` "versioned". Call a node "a version" only when it is
  one specific version
- write as the team. Decisions, approvals and actions are ours: "we decided", "accepted
  2026-10-10", "the maintainer accepts", never "the human decided" or "the agent built". An agent is
  a developer on the team, and its decisions are still ratified by the maintainer (the contract
  above). The only place AI involvement is marked is the commit trailer and pull request section that
  [GENAI_CONTRIBUTION.md](GENAI_CONTRIBUTION.md) requires, which EU legislation needs

## Modelling

- Ask how the law and contract drafting answer a question before modelling it, and model that.
- Model reality first, then simplify. Never reduce reality's complexity by waving it away, and record
  any drift forced by usability.
- Judgements, such as whether a rule was met or an act took effect, are evaluated from facts, never
  authored. Layers state, code executes.
- **Weigh the runtime with the meaning.** A term written at runtime carries four costs at once: whether its history is defensible to a regulator, what it costs to store, what a read of it costs, and whether concurrent work contends for it. Keep stored data to the minimum correctness and robustness need, and reach for a mechanism the domain already has before inventing one for performance.

Skill `lattice-ontology-authoring` has the detail.

## Platform guardrails

Code under `platform/`, `workers/`, `packages/` and `apps/` keeps these, and so does any code that reads or writes a graph store. Each is a principle in the register, which points at the decision behind it. Most are not yet enforced by a check (TD-85), so a reviewer holds a change to them.

- **The store SPI is the only door** to the RDF store. Its Core tier is SPARQL 1.1 and the Graph Store Protocol, so a read that names several named graphs is Core. Depend on a capability beyond Core, such as a multi-graph atomic write, only where the adapter declares it or its stated Core fallback is used (PRI-51).
- **No new authoritative store.** Anything persisted outside the graph is marked as coordination or derived, and can be rebuilt from the graph (PRI-52).
- **Contract first.** Wire types are generated from the schemas in `contracts/`, never written again by hand (PRI-53).
- **Every write carries its commit metadata**, its cause, principal, profile, transaction time and provenance (PRI-54).
- **No string concatenation into SPARQL.** Use a prepared query with typed parameters (PRI-55).
- **No `now()` in a guard, an effect, an ordering key, a canonicalisation or an identity.** Time is an input (PRI-56).
- **A result-returning store method returns a cursor**, never a materialised collection (PRI-57).
- **A function that claims determinism is tested** with a permutation and a repeat (PRI-58).
- **Store isolation is verified** against the actual store and its configuration (PRI-59).
- **A write path governed by a persistence profile is generated** by the persistence compiler, never written by hand (PRI-60).
- **Each component validates what it receives**, even where a client or another layer already has, since it cannot know the input was not forged or altered on the way (PRI-75, STD-298).

## A public repository

This repository is public, and so is everything it publishes.

- Nothing that identifies a person or a client, outside what the project itself names.
- No credentials, private hostnames, internal URLs or private repository paths, in files, commit
  messages or agent notes.
- Notes true of one machine or one person's setup belong in that person's own configuration or agent
  memory, never in the repository.
- Substrate and layer documentation stays domain-neutral.
- User-facing documents (layer READMEs, generated ontology documents, the site's pages, and published
  ADRs outside their Provenance section) never refer to working documents: sketches, plans, status
  records, review requests, Validation Packs, notes or the developer index. This covers text, links and
  HTML comments. They cite only published ADRs, and may link durable guidance under `docs/developer/`,
  such as the getting-started guide ([ADR-A127](docs/architecture/decisions/ADR-A127-published-architecture-decisions.md)).
  Until decisions are published, they cite Accepted ADRs
- AI-assisted contributions are disclosed as [GENAI_CONTRIBUTION.md](GENAI_CONTRIBUTION.md) requires.

Skill `lattice-publication-hygiene` has the detail and the pre-commit check.

## Private overlays

A maintainer may keep private, user-level guidance for work that spans public and private projects
(ADR-A117). If `~/.config/lattice/private/AGENTS.md` exists
(`%USERPROFILE%\.config\lattice\private\AGENTS.md` on Windows), read it before every task and follow
it. It adds to these rules and tightens them, and never relaxes them. Never quote, cite or
paraphrase it in anything this repository publishes, including commit messages, pull requests and
agent notes.

## Skills

Load the skill whose description matches the task. Each lives in `.claude/skills/<name>/SKILL.md`.

| Skill | When |
|---|---|
| `lattice-lifecycle` | How work is run in a project, from units of work, plans and status records to the work board. Use when picking up a slice or a unit, from your own plan or another's, before your first edit, when starting, continuing, handing off or closing a unit of work, an epic, a phase or a slice, when reading or updating a status record, plan, review request or Validation Pack, when recording what was learned, when preparing a commit, merge or release, and when reporting what comes next. |
| `lattice-design` | How to design in a project. Use when writing or revising a sketch, a plan or slice brief, a decision record, or design questions for the maintainer, when presenting options for an architecture or modelling decision, and when a design adds a component, a dependency or a derived artefact. |
| `lattice-architecture` | LATTICE's structure and the principles behind it. Use when a design or change crosses layers or modules, adds a dependency or an import, places a new concept in a layer, or needs to know what a layer may and may not depend on, in LATTICE or a project built on it. |
| `lattice-ontology-authoring` | How to change a LATTICE ontology and model well in it. Use when editing anything under ontology/ (a layer README, spec, vocab, shapes, projection or examples), moving the release number or an applied module's version IRI, writing a SHACL or SHACL-SPARQL shape, declaring a domain or range, simplifying a model, or naming a new technical term, in LATTICE or an applied ontology built on it. |
| `lattice-ontology-modelling` | How to model well in RDF and OWL. Use when declaring a class, property, domain or range, simplifying or merging a model, writing a SHACL shape, naming a term, deciding what an ontology states and what code computes, or choosing where a runtime cost belongs in the model. |
| `lattice-mise` | Using mise as the one entry point for build, test and check tasks, setting up shells and keeping the code under test the checkout's own. Use when running or choosing mise tasks, when a build, test or package install problem appears, when adding a mise task, or before running anything that imports the project's Python packages. |
| `lattice-windows` | Windows-specific problems in development tools. Use when a tool reads or writes text on Windows, when mise shims fail, when long paths, PowerShell quoting or a persistent terminal misbehave, or when a toolchain's PATH order matters. |
| `lattice-environment-lessons` | Lessons from problems met with Python scripts, uv environments, Node tooling and JVM libraries while developing. Use when a Python script or test must run where packages cannot install, when a uv environment is corrupt, when yarn or Playwright misbehave, or when a JVM library's behaviour is unclear. |
| `lattice-constrained-environments` | Working in an environment where a package registry, mirror or proxy blocks some fetches. Use when a bootstrap, install or download fails with a registry-level refusal (not a missing file, a dependency conflict or a code error), when a pip hash mismatch has no hash-pinned file, when a proxy that intercepts TLS breaks a tool, when deciding whether a blocked package can be worked around safely, or when the same block might recur on another machine or checkout. |
| `lattice-testing` | Diagnosing and speeding up a slow pytest suite and writing Python tests that stay fast. Use when a test or check task is slow, when adding or parallelising a suite with pytest-xdist, when a suite may run short of memory, when sizing workers, when profiling a run, when a repository-wide text scan must work on every platform, or when reading a slow run as a regression. |
| `lattice-probing` | How triple stores really behave, and how to record what we find. Use before relying on what a store does with SPARQL (an update's order, scope, datatypes, escapes, atomicity, cost), when running generated SPARQL on rdflib, Oxigraph, Jena or another engine, when writing a probe or an engine test, and whenever a store does something unexpected. |
| `lattice-query-writing` | Writing SPARQL queries, SHACL-SPARQL constraints and generated queries that run in reasonable time. Use before writing or changing a constraint query, when a shape or a query is slow, when generating queries, or when a speed claim must say which engine it is for. |
| `lattice-shacl-testing` | Writing and speeding up tests that validate RDF graphs against SHACL shapes with pySHACL. Use when adding a test that validates a graph against shapes, when sharing parsed graphs or validation reports across test modules with pytest fixtures, when a suite makes many pyshacl.validate calls, or when a cache of graphs may hide a mutation. |
| `lattice-publication-hygiene` | What may and may not be published from a repository. Use before committing, before opening or describing a pull request, and whenever writing anything that will be public, such as documentation, code comments, commit messages, examples, release notes, environment notes or agent memory kept in the repository. |
| `lattice-branching` | Working across branches, worktrees and repositories. Use when merging or measuring a branch, resolving a conflict in a register or in a generated index, renumbering a register row, working in a git worktree, running or bypassing a git hook, or doing a task that writes to more than one repository. |
