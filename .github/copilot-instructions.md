<!-- Generated from AGENTS.md by `mise run build:agent-guidance`. Edit AGENTS.md, not this file. -->

# LATTICE: instructions for AI agents

These rules apply to every task in this repository and in projects built on LATTICE. Procedures and
reference material live in skills, loaded when a task needs them (see the last section). This file
is the source of `.github/copilot-instructions.md`. Edit it here, then run
`mise run build:agent-guidance` ([ADR-A117](../docs/architecture/decisions/ADR-A117-agent-guidance-and-skill-library.md)).

## The contract

We work iteratively. The agent suggests what to build next, and the human verifies the approach
along the way.

- **Default mode, unless told otherwise.** Write, then hand off. Do not run build, test, compile or
  integration commands to validate a change. End the turn with the exact commands to run, where to
  run them from, and what a pass looks like. Cheap static checks, such as a single-file syntax
  check, are fine.
- **Autonomous mode, only when the human says so.** Run the checks yourself and report their real
  results. It does not change anything else in this contract.
- **Never claim a check passed** unless it ran and passed. Say "authored, not yet run" and give the
  command.
- **Pause for design decisions.** Do not make an architecture or modelling decision alone. Present
  the options and their consequences (skill `lattice-design`) and wait for the answer.
- **Never commit, merge, tag or push** without the human's go-ahead. Release tags are always the
  human's to create. Do not mark an ADR Accepted yourself.
- **End a "what next" report** with 🔴 PLAN FIRST when something must be decided first, or
  🟢 READY TO BRANCH when a new branch is due.

## Where things are

| Root | Owns |
|---|---|
| `ontology/` | semantic assets only: sources, shapes, vocabularies, projections, examples, their documentation |
| `tools/` | executable reference implementations and developer toolchains |
| `platform/`, `apps/`, `packages/`, `contracts/`, `deployment/`, `workers/`, `test/`, `spikes/` | services, applications, libraries, data contracts, the local environment, the worker runtime, end-to-end suites, experiments |
| `docs/architecture/` | architecture documents and the ADRs, in `decisions/` |
| `docs/developer/` | sketches, plans, status records, review requests, Validation Packs, and durable guidance |
| `.claude/skills/` | the skills below |

Do not add a directory at the root, or a new kind of directory anywhere, without an accepted ADR.
`mise` is the only task entry point (ADR-A29). The [developer guide](../docs/developer/developer-guide.md)
describes every tool.

## Writing

Every piece of text, in documents, code comments, commit messages and replies:

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
- do not coin technical terms from insurance market vocabulary. Producing bound meaning is
  **instantiation**, done by an **instantiator**, never a "binder" (skill `lattice-ontology-authoring`)
- call a class that is a member of `fnd:Version` "versioned". Call a node "a version" only when it is
  one specific version

## Modelling

- Ask how the law and contract drafting answer a question before modelling it, and model that.
- Model reality first, then simplify. Never reduce reality's complexity by waving it away, and record
  any drift forced by usability.
- Judgements, such as whether a rule was met or an act took effect, are evaluated from facts, never
  authored. Layers state, code executes.

Skill `lattice-ontology-authoring` has the detail.

## A public repository

This repository is public, and so is everything it publishes.

- Nothing that identifies a person or a client, outside what the project itself names.
- No credentials, private hostnames, internal URLs or private repository paths, in files, commit
  messages or agent notes.
- Notes true of one machine or one person's setup belong in that person's own configuration or agent
  memory, never in the repository.
- Substrate and layer documentation stays domain-neutral.
- AI-assisted contributions are disclosed as [GENAI_CONTRIBUTION.md](../GENAI_CONTRIBUTION.md) requires.

Skill `lattice-publication-hygiene` has the detail and the pre-commit check.

## Skills

Load the skill whose description matches the task. Each lives in `.claude/skills/<name>/SKILL.md`.

| Skill | When |
|---|---|
| `lattice-lifecycle` | starting, continuing, handing off or closing a unit of work or slice: status, plans, Validation Packs, commits, merges, release tags |
| `lattice-design` | writing a sketch, a plan brief, an ADR or design questions for the human |
| `lattice-architecture` | a design that crosses layers or modules, or needs the principles behind LATTICE's structure |
| `lattice-ontology-authoring` | changing anything under `ontology/` |
| `lattice-toolchain` | building, testing, running checks, or setting up or repairing an environment |
| `lattice-testing` | a slow test suite, writing or extending a Python test under `tools/` that parses an ontology graph or calls pySHACL, sharing state across test modules with pytest fixtures, or a repository-wide text scan that must work on every platform |
| `lattice-publication-hygiene` | before a commit or pull request, and whenever writing text that will be published |
