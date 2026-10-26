<!-- Generated from AGENTS.md by `mise run build:agent-guidance`. Edit AGENTS.md, not this file. -->

# LATTICE: instructions for AI agents

These rules apply to every task in this repository and in projects built on LATTICE. Procedures and
reference material live in skills, loaded when a task needs them (see the last section). This file
is the source of `.github/copilot-instructions.md`. Edit it here, then run
`mise run build:agent-guidance` ([ADR-A117](../docs/architecture/decisions/ADR-A117-agent-guidance-and-skill-library.md)).

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
- **Pause for design decisions.** Do not make an architecture or modelling decision alone. Present
  the options and their consequences (skill `lattice-design`) and wait for the answer.
- **When two standards conflict for a change, stop and ask the maintainer** before proceeding, and record the conflict in `docs/developer/pending-design-decisions.md`, so conflicts that recur show which standards to rework. Standards have no precedence order.
- **The git hooks are a floor, never a ceiling.** `mise run bootstrap` installs them ([ADR-A133](../docs/architecture/decisions/ADR-A133-git-hooks.md)). They run the checks a commit, or a merge into `main`, touches, and never block a push. Never bypass one (`--no-verify`, `LATTICE_HOOKS_SKIP`) without recording which and why in the slice's Validation Pack, and never report a passing hook as a passing `mise run check`.
- **Never commit, merge, tag or push** without the maintainer's go-ahead. Release tags are always the
  maintainer's to create. Do not mark an ADR Accepted yourself.
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

How each triple store behaves, and how we found out, is recorded in
[docs/architecture/triple-store-discovery.md](../docs/architecture/triple-store-discovery.md). Read it before relying on what a
store does with SPARQL, and add to it when you find something new (skill `lattice-triple-stores`).

How to write a SPARQL constraint, a generated query or a test fixture that runs in reasonable time is recorded in
[docs/architecture/efficient-queries-and-shapes.md](../docs/architecture/efficient-queries-and-shapes.md)
([ADR-A128](../docs/architecture/decisions/ADR-A128-efficient-queries-and-shapes.md)). Read it before writing or changing one. It says
which of its rules hold for any engine and which only for rdflib, pySHACL or our harness.

Do not add a directory at the root, or a new kind of directory anywhere, without an accepted ADR.
`mise` is the only task entry point (ADR-A29). Every command you run or give the maintainer goes
through it, as `mise run <task>` or `mise exec -- <command>`, never a bare `python`, `pytest` or `pip`.
Only mise picks up this checkout's `.venv` and its dependencies, and a bare interpreter is the global
one (skill `lattice-toolchain`). The [developer guide](../docs/developer/developer-guide.md)
describes every tool.

## Asking the knowledge index

The knowledge index ranks the project's decisions, mechanisms, capabilities, patterns, principles, standards and store findings against a question, so an agent reads the one section that answers it instead of whole documents ([ADR-A134](../docs/architecture/decisions/ADR-A134-knowledge-index-and-design-shape-vocabulary.md)).

- **Ask it first,** before a design, modelling, code or efficiency decision, and before adding a mechanism, a dependency or a component. Describe the problem in your own words, name the activity, quality and technology of the work at hand, then read the entries that answer it. `--kind`, `--phase` and `--audience` filter exactly. `--activity`, `--quality` and `--tech` raise matching entries and hide none.
  ```bash
  mise run graph:ask -- find <the problem in your own words> --activity physical-data-modelling --quality concurrency --phase runtime
  mise run graph:ask -- read <ID>
  ```
  `mise run graph:ask -- find --help` lists every option, and `tools/knowledge/facets.ttl` defines every facet value. `exists <word>` finds a declared ontology term by name.
- **Ask more than once.** Reword the question, or narrow, widen or drop a filter, until the answers fit the question or two attempts have found nothing better.
- **An empty or weak answer never proves that nothing exists.** When `find` reports one, fall back to reading the documents and the code as you would without the index.
- **A register gap is technical debt.** If the fallback finds an answer in the repository that no register entry holds, tell the maintainer in the handoff, and add the entry in the same change or a row to `docs/developer/technical-debt.md` (STD-272).

## Writing

Every piece of text, in documents, code comments, commit messages and replies:

- do not put newlines in markdown text for formatting. Modern editors can word-wrap long lines. Newlines should be used to create space between paragraphs: don't assume a line length and enforce it with newlines.
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
- call a class that is a member of `fnd:Version` "versioned". Call a node "a version" only when it is
  one specific version
- write as the team. Decisions, approvals and actions are ours: "we decided", "accepted
  2026-10-10", "the maintainer accepts", never "the human decided" or "the agent built". An agent is
  a developer on the team, and its decisions are still ratified by the maintainer (the contract
  above). The only place AI involvement is marked is the commit trailer and pull request section that
  [GENAI_CONTRIBUTION.md](../GENAI_CONTRIBUTION.md) requires, which EU legislation needs

## Modelling

- Ask how the law and contract drafting answer a question before modelling it, and model that.
- Model reality first, then simplify. Never reduce reality's complexity by waving it away, and record
  any drift forced by usability.
- Judgements, such as whether a rule was met or an act took effect, are evaluated from facts, never
  authored. Layers state, code executes.
- **Weigh the runtime with the meaning.** A term written at runtime carries four costs at once: whether its history is defensible to a regulator, what it costs to store, what a read of it costs, and whether concurrent work contends for it. Keep stored data to the minimum correctness and robustness need, and reach for a mechanism the domain already has before inventing one for performance.

Skill `lattice-ontology-authoring` has the detail.

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
  such as the getting-started guide ([ADR-A127](../docs/architecture/decisions/ADR-A127-published-architecture-decisions.md)).
  Until decisions are published, they cite Accepted ADRs
- AI-assisted contributions are disclosed as [GENAI_CONTRIBUTION.md](../GENAI_CONTRIBUTION.md) requires.

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
| `lattice-lifecycle` | starting, continuing, handing off or closing a unit of work or slice: status, plans, Validation Packs, commits, merges, release tags |
| `lattice-design` | writing a sketch, a plan brief, an ADR or design questions for the maintainer |
| `lattice-architecture` | a design that crosses layers or modules, or needs the principles behind LATTICE's structure |
| `lattice-ontology-authoring` | changing anything under `ontology/` |
| `lattice-toolchain` | building, testing, running checks, or setting up or repairing an environment |
| `lattice-testing` | a slow test suite, writing or extending a Python test under `tools/` that parses an ontology graph or calls pySHACL, sharing state across test modules with pytest fixtures, or a repository-wide text scan that must work on every platform |
| `lattice-publication-hygiene` | before a commit or pull request, and whenever writing text that will be published |
| `lattice-triple-stores` | relying on, probing or recording how a triple store behaves: running generated SPARQL on rdflib, Oxigraph or another engine, writing an engine test, or meeting unexpected store behaviour |
