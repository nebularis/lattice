<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A117: Agent guidance and the skill library

**Status:** Proposed
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
4. **Machine-specific and private notes leak.** Some guidance is true of one machine or one network
   only, and the repository is public.

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
5. **What stays personal.** Guidance true of one machine, one network or one person's accounts
   (remotes, proxies, editable installs pointing elsewhere) stays in that person's own agent memory
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
