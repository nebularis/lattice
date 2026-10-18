<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A117: Agent guidance and the skill library

**Status:** Accepted 2026-10-07, with the addendum below
**Date:** 2026-10-07
**Related:** [ADR-A77](ADR-A77-repository-topology-and-documentation-governance.md) (repository
topology), [ADR-A29](ADR-A29-repository-toolchain-and-environment-boundary.md) (`mise` as the task entry point),
[GENAI_CONTRIBUTION.md](../../../GENAI_CONTRIBUTION.md), technical debt TD-21
**Unit:** [`agent-skills`](../../developer/sketches/agent-skills.md) (sketch)

## Context

LATTICE is developed with AI agents, mainly Claude Code and GitHub Copilot, and so are the projects
built on it, such as Open CBAA. The rules those agents follow live in one 425-line file,
`.github/copilot-instructions.md`. Its problems:

1. **Only an agent in this repository reads it.** Open CBAA keeps a 90-line fork that has already
   drifted, and lacks the ontology change procedure, the versioning rules and the SHACL-SPARQL
   rules that apply to every LATTICE layer it imports.
2. **A hand-made copy has drifted.** A Claude skill copied from the file outside the repository
   lacked five rules added since, and an agent loading it worked to stale rules (TD-21).
3. **Everything loads every time.** Writing style and the commit rules must hold in every reply.
   The ontology change procedure, the slice lifecycle and the toolchain notes matter only for the
   task at hand, and loading all of it always costs context and dilutes what matters.
4. **Some guidance is personal.** Some of it is true of one machine or one person's setup only,
   and the repository is public.

Both agents now read the same open skill format: a directory holding a `SKILL.md` with a name and a
description, loaded when the description matches the task. Claude Code reads project skills from
`.claude/skills/`. GitHub Copilot's cloud agent, its CLI and VS Code's agent mode read project
skills from `.github/skills/`, `.claude/skills/` or `.agents/skills/`, and personal skills from
`~/.copilot/skills/`, `~/.claude/skills/` or `~/.agents/skills/`. Claude Code installs skills in
other projects from a plugin marketplace, a repository holding `.claude-plugin/marketplace.json`.

## Decision

1. **Two tiers.**
   - **An always-on core**, `AGENTS.md` at the repository root, short enough to load every time: the
     agentic development contract's essentials, the writing rules, the privacy rules, and a map of
     the skills. It is the canonical always-on text. `CLAUDE.md` imports it (`@AGENTS.md`), and
     Copilot's `.github/copilot-instructions.md` is derived from it, as the sketch decides.
   - **Skills**, loaded when a task needs them, for procedures and reference.
2. **Six skills**, in `.claude/skills/`, each `lattice-<name>/SKILL.md`, with longer material in
   files beside it that the skill names:

   | Skill | For |
   |---|---|
   | `lattice-lifecycle` | the agentic contract and the development lifecycle: slices, Validation Packs, status, examples first, commits, merges and release tags |
   | `lattice-design` | sketches, plan briefs and ADRs: setting the scene, comparing options, KISS |
   | `lattice-architecture` | the layers, their dependencies and the principles behind them |
   | `lattice-ontology-authoring` | changing an ontology: literate sources, versions and cascades, shapes, modelling rules |
   | `lattice-toolchain` | `mise`, the checks, environments and package registries |
   | `lattice-publication-hygiene` | what may enter a public repository or generated text, and what may not |

3. **One source, read in place.** Inside this repository both agents load `.claude/skills/` and
   `AGENTS.md` with no setup. Skills point to the canonical documents (the developer guide, the
   versioning policy, the ADRs) and do not copy them. A rule that must be restated in a skill is
   checked against its source by a test.
4. **Shared with other projects as a plugin.** `.claude-plugin/marketplace.json` at the repository
   root lists one plugin, `lattice`, whose source is the repository root and whose `skills` names
   the six directories, so only those load. Claude Code users elsewhere run
   `/plugin marketplace add nebularis/lattice` and install it. Copilot users elsewhere run a `mise`
   task that links the skills into their personal skills directory. A project built on LATTICE
   keeps its own short `AGENTS.md` for what is its own, and takes the shared skills from here.
5. **What stays personal.** Guidance true of one machine or one person's accounts
   (remotes, editable installs pointing elsewhere) stays in that person's own agent memory
   or user-level configuration, never in the repository. The publication hygiene skill states
   rules and categories only: a list of real names to avoid would publish them, so any such list
   lives in user-level configuration, read by a local check.
6. **Retirements.** The hand-made copy outside the repository is retired. TD-21 is removed when the
   skills land. `.github/copilot-instructions.md` stops being a source.

## Consequences

- ADR-A77's topology gains `AGENTS.md`, `CLAUDE.md`, `.claude/` and `.claude-plugin/` at the root,
  documented in the root `README.md`.
- The plugin's root is the repository root. Claude Code would also load a root `bin/`, `hooks/`,
  `.mcp.json` or `settings.json` as plugin components, so none may be added at the root without
  revisiting this decision. The root has none today.
- Inside this repository, a contributor does not install the plugin as well, or each skill appears
  twice.
- A rule now has one home, in the core or in one skill, and a change to it is one edit, reviewed
  like any other document.
- Copilot users outside this repository re-run the link task after pulling, until Copilot installs
  skills from a repository by itself.
- The skills are public, so they describe the project's conventions only, and are reviewed under
  the publication hygiene rules before each change.

## Addendum (2026-10-07): the plugin's source is `.claude/`

Found while building. Decision 4 makes the repository root the plugin's source, with `skills`
naming the six directories. Instead, the marketplace entry's source is `./.claude`, so Claude Code
scans `.claude/skills/` by default and needs no list.

- An install copies `.claude/` only, not the whole repository.
- The root needs no restriction on `bin/`, `hooks/`, `.mcp.json` or `settings.json`, so the first
  consequence above no longer applies.
- Anything added under `.claude/agents/`, `.claude/commands/` or `.claude/hooks/` is shared with
  every project that installs the plugin, so it is reviewed as part of the library. A
  `.claude/settings.json` would apply only its `agent` and `subagentStatusLine` keys to them.
- `mise run check:agent-guidance` checks the entry's source.

## Addendum (2026-10-18): a private overlay

**Status:** Proposed

Decision 5 keeps personal guidance out of the repository. Some guidance is personal but not about
one machine. A maintainer who also works on private projects needs rules about what may enter this
repository, and those rules are themselves private. Decision 5 extends to them.

1. **One path.** An agent reads `~/.config/lattice/private/AGENTS.md` before every task, if it
   exists. On Windows the path is `%USERPROFILE%\.config\lattice\private\AGENTS.md`. The path is
   literal on every platform, because an agent's file reader and Claude Code's `@` imports expand
   `~` but not `XDG_CONFIG_HOME` or `%APPDATA%`. The folder is usually a link to a private checkout,
   a symbolic link on macOS and Linux, a directory junction on Windows.
2. **Precedence.** The overlay adds to the repository's rules and tightens them. It never relaxes
   them. Where the two disagree, the stricter rule holds, so a contributor without an overlay is
   bound by exactly the public rules.
3. **Confidentiality.** Nothing in the overlay is quoted, cited or paraphrased in anything the
   repository publishes. The publication hygiene skill names the overlay beside the deny-list.
4. **How agents find it.** `AGENTS.md` says so in a short section, so every agent that reads
   `AGENTS.md` and can read files finds it, including Copilot through the generated
   `.github/copilot-instructions.md`. Claude Code users load it directly from a user-level rule,
   `~/.claude/rules/<name>.md` (`%USERPROFILE%\.claude\rules\<name>.md` on Windows), holding an
   `@` import of the overlay. Claude Code loads imports in user-level files without an approval
   dialog. `CLAUDE.md` does not import it. A committed import of a path outside the project would
   show every contributor an approval dialog naming that path.
5. **Scope is the overlay's own.** A user-level rule loads in every project, so the overlay itself
   decides which repositories it governs, for example by their git remotes. The repository does
   not record how.

**Consequences.**

- A cloud agent working on a hosted checkout never sees an overlay, and works to the public rules.
  That is the intended fallback.
- The repository names the overlay's path, not its content or purpose beyond the sentence in
  `AGENTS.md`.
- Private skills stay in the personal skill directories this ADR already lists
  (`~/.claude/skills/`, `~/.copilot/skills/`, `~/.agents/skills/`), linked from the same private
  checkout.
