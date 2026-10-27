<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A133: Git hooks check what a change touches, never block a push, and gate the merge into `main`

**Status:** Proposed, 2026-10-23
**Date:** 2026-10-23
**Supersedes:** none
**Related:** [ADR-A29](ADR-A29-repository-toolchain-and-environment-boundary.md) (`mise` is the only task entry point), [ADR-A117](ADR-A117-agent-guidance-and-skill-library.md) (agent guidance and the deny-list), [ADR-A121](ADR-A121-repository-catalogue.md) (the repository catalogue), [ADR-A126](ADR-A126-literate-specification-layout-and-grammar.md) (literate READMEs), [ADR-A127](ADR-A127-published-architecture-decisions.md) (published decisions), [ADR-A129](ADR-A129-one-release-for-the-substrate.md) (one release, bumped at merge)
**Unit:** [`git-hooks`](../../developer/plans/git-hooks.md)

## Context

The repository's checks run in two places today. `mise run check` and the full sweep take minutes and are run by hand. CI is manual only. The one git hook, installed by `mise run hooks:install` when someone remembers to, runs the personal deny-list check.

So the slips the checks exist to catch are found late, often by the maintainer at review. A README edited without its Turtle re-extracted, `AGENTS.md` edited without its Copilot copy rebuilt, a broken link, a semicolon in prose, a user-facing document citing a decision not yet published: each is cheap to catch at the commit that introduces it, and costly once several commits have built on it.

Three facts shape what a hook may do.

- **Whole-tree checks carry debt that a change did not cause.** On 2026-10-23, `main` had 198 broken-link reports, almost all in generated site copies. A hook that ran the whole-tree link check would block every commit for something no committer touched.
- **A working branch defers versioning to its merge** (ADR-A129, and the lifecycle skill). `check:ontology-versioning` reports a pending bump on such a branch by design, so it cannot run at commit.
- **A push must always succeed.** A cloud agent pushes its branch so that the maintainer can receive the work and verify it before merging. A hook that blocked the push would strand that work.

## Decision

1. **Installed by bootstrap.** `mise run bootstrap` runs `mise run hooks:install`, which installs the hooks into the repository's shared hooks directory, so one install covers the main checkout and every linked worktree. It never overwrites a hook it did not write. Under bootstrap it then warns and carries on, and run on its own it fails and says what to do.
2. **One dispatcher.** `tools/hooks.py` decides which checks a change needs, runs them, and reports. Each installed hook is a short script that starts the dispatcher through `mise exec`, falling back to `python3` where `mise` is not on the path. In a checkout that predates the dispatcher, the script runs the deny-list check alone, as the old hook did.
3. **A check judges only what the change touches.** Each check declares the paths it governs. It runs only when the change touches one of them, and it judges only the touched files, or the modules they belong to. A check that a set of files agree, such as a README and the files it generates, `AGENTS.md` and its Copilot copy, or the catalogue and the tree, judges the whole set once any member is touched, since the member left untouched is often the one at fault. A hook never fails on a file outside what it judges. A check whose tool cannot run, for want of a package, warns and says to run `mise run bootstrap`.
4. **Three moments.**

   | Moment | Git hook | What runs |
   |---|---|---|
   | a commit | `pre-commit` | the commit checks over the staged files |
   | a merge into `main` | `pre-merge-commit`, and `pre-commit` while a merge or a squash into `main` is in progress | the commit checks over every file the merge changes, all blocking, plus the merge gates |
   | a push | none | nothing, ever |

5. **The commit checks.**

   | Check | Runs when the change touches | On failure |
   |---|---|---|
   | the personal deny-list | anything | blocks |
   | literate freshness: a README and the files it generates agree | a literate module's README or a file it generates | blocks |
   | agent guidance: `AGENTS.md`, its Copilot copy, the skills and the plugin listing agree | any of them | blocks |
   | the repository catalogue and the import guard | the catalogue, a module's README or an ontology file | blocks |
   | links in the touched Markdown | a Markdown file | blocks |
   | formal freshness | a theory, a reference, or the README they follow | blocks |
   | the site's section copies | a section's source | blocks |
   | the writing rules: no semicolon in prose, and no "this document" in a literate README | the added lines of a Markdown file | blocks |
   | the writing rules: no hard-wrapped paragraph | the added lines of a Markdown file | warns |
   | published decisions: a user-facing document cites only published decisions and no working document | a user-facing document or a decision | warns |

   A commit that touches nothing a check governs runs nothing but the deny-list check. A typical commit takes under five seconds.
6. **The merge gates.** At a merge into `main`, the published-decisions check runs over the whole tree and blocks, since a published page must never cite an unpublished decision. Ontology versioning runs too, since the merge is where the bump happens. The writing rules warn only, since every commit on the branch has already met them.
7. **Escapes.** `LATTICE_HOOKS_SKIP` names checks to skip, separated by commas, and `git commit --no-verify` skips every check. The committer records a skip, and why, in the slice's Validation Pack. The hooks add to `mise run check` and CI and replace neither.
8. **What a check reads.** A check reads the working tree for the staged files. A file with further unstaged edits is judged as it stands on disk.

## Consequences

- `tools/deny_terms.py install-hook` installs the dispatcher, so existing instructions keep working.
- The link checker gains a mode over named files, and a new tool checks the writing rules on added lines. Each has tests, and the dispatcher's path rules have their own.
- The developer guide, the toolchain, publication-hygiene and lifecycle skills, and `AGENTS.md` describe the hooks and the rule that an agent never bypasses one without recording why.
- A failure the hooks miss, because it lies in a file the change did not touch, is still found by `mise run check`, as today.
- A merge made on GitHub runs no local hook. Until CI runs on pull requests, the maintainer merges locally, or runs `mise run hooks:merge` before merging on GitHub.

## Provenance

Proposed on 2026-10-23, after the maintainer asked which checks should become hooks. The maintainer decided that the published-decisions check warns at commit and blocks only at a merge, never at a push, and that one dispatcher installs every hook. Planned in the [git hooks plan](../../developer/plans/git-hooks.md).
