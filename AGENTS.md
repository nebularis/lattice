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
- **The git hooks are a floor, never a ceiling.** `mise run bootstrap` installs them ([ADR-A133](docs/architecture/decisions/ADR-A133-git-hooks.md)). They run the checks a commit, or a merge into `main`, touches, and never block a push. Never bypass one (`--no-verify`, `LATTICE_HOOKS_SKIP`) without recording which and why in the slice's Validation Pack, and never report a passing hook as a passing `mise run check`.
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

How each triple store behaves, and how we found out, is recorded in [docs/architecture/triple-store-discovery.md](docs/architecture/triple-store-discovery.md). Before relying on what a store does with SPARQL, find the findings that touch it with `mise run graph:ask -- find <the behaviour> --kind discovery` and read each with `read TSD-nn`, reading the whole record only when the query answers weakly. Add to it when you find something new (skill `lattice-triple-stores`).

How to write a SPARQL constraint, a generated query or a test fixture that runs in reasonable time is recorded in [docs/architecture/efficient-queries-and-shapes.md](docs/architecture/efficient-queries-and-shapes.md) ([ADR-A128](docs/architecture/decisions/ADR-A128-efficient-queries-and-shapes.md)), and its rules are standards in the register. Before writing or changing one, find the rules that apply with `mise run graph:ask -- find <what the query does> --kind standard --activity query-writing` and read each, reading the whole record only when the query answers weakly. It says which of its rules hold for any engine and which only for rdflib, pySHACL or our harness.

Do not add a directory at the root, or a new kind of directory anywhere, without an accepted ADR.
`mise` is the only task entry point (ADR-A29). Every command you run or give the maintainer goes
through it, as `mise run <task>` or `mise exec -- <command>`, never a bare `python`, `pytest` or `pip`.
Only mise picks up this checkout's `.venv` and its dependencies, and a bare interpreter is the global
one (skill `lattice-toolchain`). The [developer guide](docs/developer/developer-guide.md)
describes every tool.

Code finds the repository root and every directory the [repository catalogue](repository-catalogue.md) names through its reader, `tools/lattice_repo_catalogue.py`, by a module's role or a root's or documentation area's name, such as `area("developer")` for the registers, never from `__file__` or a path written in code (STD-273, skill `lattice-toolchain`'s Finding paths).

## Asking the knowledge index

The knowledge index ranks the project's decisions, mechanisms, capabilities, patterns, principles, standards, store findings and the questions plans and sketches raise against a question, and, only when asked with `--kind term`, the declared ontology terms, so an agent reads the one section that answers it instead of whole documents ([ADR-A134](docs/architecture/decisions/ADR-A134-knowledge-index-and-design-shape-vocabulary.md)).

- **Ask it first,** before a design, modelling, code or efficiency decision, and before adding a mechanism, a dependency or a component. Describe the problem in your own words, name every activity, quality and technology of the work at hand, several at once where several apply, then read the entries that answer it. `--activity`, `--quality` and `--tech` raise matching entries and hide none. `--kind`, `--phase` and `--audience` filter exactly, so use them only where an entry outside them could not answer.
  ```bash
  mise run graph:ask -- find <the problem in your own words> --activity physical-data-modelling --quality concurrency --phase runtime
  mise run graph:ask -- read <ID>
  ```
  `mise run graph:ask -- find --help` lists every option, and the [facet register](docs/developer/facets.md) defines every facet value. `exists <word>` finds a declared ontology term by name.
- **Ask for terms only when the question is about a term.** `find` searches the declared ontology classes and properties only when `--kind` names `term`, and never otherwise.
  - Use `--kind term` when you need to know what a class, property, scheme concept or declared individual means, whether one already exists for a concept or a value before you declare one, or what restricts it, such as functional, its domain and range, or at most one value. For example `find which property derives one account per key value --kind term`. A term's row names its module and its line under the row gives its definition and restrictions.
  - Leave it off for every other question: how to design, model, build or test something, which rule, decision or pattern applies, and what mechanism or capability the project already has. Ranked together, terms push the entries that answer such a question out of the top five, measured as hit@5 0.79 against 0.93 without them.
  - When you are modelling, ask both ways, once for the rules with no kind and once for the terms with `--kind term`, rather than mixing them. `exists <word>` still finds a term by its name.
- **Asking first means before searching the files.** `grep`, `sed` and reading a whole document are the fallback after `find` has answered weakly, never the opening move. Searching first is the common failure, and it costs twice: it finds the text and misses the entry that governs it, and it leaves nothing in the misses log, so a gap the index could have been told about stays invisible.
- **Ask more than once.** Reword the question, or narrow, widen or drop a filter, until the answers fit the question or two attempts have found nothing better.
- **Look for what is related, not only for the entry.** When reviewing, re-sourcing or changing an entry, ask for the decisions that ground it and the standards, patterns and mechanisms that bear on it, in your own words and with `--kind decision` among them, since the entry itself is rarely the whole answer.
- **Read the flags and the line under each row.** `!` says the entry states a case it does not cover, `~` that the text returned was superseded or reversed, `TD` that an open debt bears on the entry, and `?` that it is Proposed. The line under a row holds the whole claim and names each of these, and `read <ID>` prints the entry's fields and every entry linked to it before its text. The boundary is usually in the part of a claim the table cuts.
- **Ask for the reason, not only the rule.** A constraint's rationale lives in the decision that grounds it, and a decision holding several numbered decisions is indexed under one claim, so its later decisions may not come back from a question about their own subject. Ask for the rule, read the decision the answer names, and treat a rule you could find only by searching the files as a register gap (STD-272).
- **The index holds a plan's questions, never the rest of the plan or the status records.** A question raised by a bold lead or a table row in a plan or a sketch is an entry, open or answered, found with `--kind question` or among the rest. When questions crowd out the entries that would answer, ask again with `--exclude question`, which keeps every other kind. What a unit is doing now and what it does next is in `docs/developer/status/<unit>.md`, and its scope and slices are in `docs/developer/plans/<unit>.md`, so no wording or facet will find them here. An identifier written in a question, such as `find PDD-08`, names its entry outright and ranks first, and `read <ID>` gives its text.
- **An empty or weak answer never proves that nothing exists.** When `find` reports one, fall back to reading the documents and the code as you would without the index.
- **A register gap is technical debt.** If the fallback finds an answer in the repository that no register entry holds, tell the maintainer in the handoff, and add the entry in the same change or a row to `docs/developer/technical-debt.md` (STD-272).
- **Record a gap when you find it.** When reading finds something the index did not say, such as a case an entry does not cover, run `mise run graph:ask -- gap "<what you found>" <ID> <path:line>` at once. When a change writes the signpost that answers it, run `mise run graph:ask -- close <ID>` in the same change, which removes the gap and the log lines of the question behind it.
- **Report misses and improvements as they come up.** At each handoff, list what the index answered weakly or not at all, the near answers and the gaps recorded, from `mise run graph:ask -- misses --near`, and say which column or edge would have carried each, so the maintainer can decide what to add.

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
| `lattice-lifecycle` | starting, continuing, handing off or closing a unit of work or slice: status, plans, Validation Packs, commits, merges, release tags |
| `lattice-design` | writing a sketch, a plan brief, an ADR or design questions for the maintainer |
| `lattice-architecture` | a design that crosses layers or modules, or needs the principles behind LATTICE's structure |
| `lattice-ontology-authoring` | changing anything under `ontology/` |
| `lattice-toolchain` | building, testing, running checks, or setting up or repairing an environment |
| `lattice-testing` | a slow test suite, writing or extending a Python test under `tools/` that parses an ontology graph or calls pySHACL, sharing state across test modules with pytest fixtures, or a repository-wide text scan that must work on every platform |
| `lattice-publication-hygiene` | before a commit or pull request, and whenever writing text that will be published |
| `lattice-triple-stores` | relying on, probing or recording how a triple store behaves: running generated SPARQL on rdflib, Oxigraph or another engine, writing an engine test, or meeting unexpected store behaviour |
| `lattice-constrained-environments` | a bootstrap, install or download refused by a registry, mirror or proxy, and deciding whether a blocked package can be worked around safely |
| `lattice-branching` | merging or measuring a branch, a register or index conflict and its renumbering, a git worktree, the git hooks at each moment, and a task that writes to more than one repository |
