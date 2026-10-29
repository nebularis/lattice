---
name: lattice-branching
description: Working across branches, worktrees and repositories in LATTICE and projects built on it. Use when merging or measuring a branch, resolving a conflict in a register or in the knowledge index, renumbering a register row, working in a git worktree, running or bypassing a git hook, or doing a task that writes to more than one repository.
---

# Branches, worktrees and repositories

The lifecycle skill says how a unit of work runs and when a branch is due. This skill is about the git mechanics around it: what the hooks do at each moment, how a branch is merged and measured, what a worktree changes, and what a task that spans repositories must decide first.

## The hooks

`mise run bootstrap` installs the hooks into the shared hooks directory, which covers the main checkout and every worktree ([ADR-A133](../../../docs/architecture/decisions/ADR-A133-git-hooks.md)). Four moments.

| Moment | Hook | Runs |
|---|---|---|
| a commit | `pre-commit` | the commit checks over the staged files, each check only where the change touches what it governs |
| a merge into `main`, automatic | `pre-merge-commit` | the commit checks over every file the merge changes, plus the merge gates |
| a merge into `main` completed by `git commit`, after conflicts or a squash | `pre-commit`, which detects the merge | the same |
| after any merge | `post-merge` | `build:knowledge`, so the index is never stale. Never fails |

A push is never refused, so a branch always reaches the maintainer. A merge made on GitHub runs no local hook, so run `mise run hooks:merge` first. Never bypass a hook (`--no-verify`, `LATTICE_HOOKS_SKIP`) without recording which and why in the slice's Validation Pack, and never report a passing hook as a passing `mise run check`.

## Measuring a branch

Branches here are usually squash-merged, so ancestry says nothing about whether a branch is merged. `git log main..branch` lists commits whose content may be on `main` already, and `git cherry` sees none of them, since a squash changes every patch id. Measure by content. For each file the branch changed since its merge-base, compare the branch's blob with `main`'s, and count how many of the branch's added lines are present in `main` today. A branch at or above the whole is merged. Before analysing a set of branches, ask the maintainer which are live.

A trial merge, `git merge-tree --write-tree main branch`, reports textual conflicts without touching the tree. It does not see a branch that changes a term another branch renames in a file the rename does not touch, so the sweep tasks on the merged tree are still the check.

## Merging

- **Merge `main` into a paused branch, never rebase it.** A branch is pushed, and a cloud agent may hold it. A rebase rewrites what they have.
- **Register rows collide.** Every branch numbers its rows from the highest it can see, so two branches assign one identifier to two rows, and `check:identifiers` fails the merged tree with both sites and the date each line was committed. First in wins: the row committed earlier keeps the number, and the later row and every citation of it are renumbered, which the same check then verifies. No provisional identifiers and no reserved ranges, since a long-lived branch must keep its own index fresh.
- **`tools/knowledge/knowledge.ttl` conflicts.** Take `main`'s file and add the branch's own relation rows back.
- **Rebuild the index after the merge** (`mise run build:knowledge`), which the `post-merge` hook does for a merge made with `git merge`. A squash completed by `git commit` runs no post-merge hook, so run it by hand.
- **Versions move once, at the merge into `main`** (lifecycle skill), by `mise run release:prepare`, and tags are the maintainer's.
- **Record the merge.** The status record of each unit the merge touched says what moved, and a renumbering says which identifiers changed.

## Worktrees

A worktree shares the repository, its remotes, its hooks directory and its ignore rules with the main checkout. It has its own `.local/`, git-ignored, so a draft left in one worktree is not in another. `mise` tasks run against the worktree they are run in, and `mise run bootstrap` is needed once per worktree for its `.venv`. A commit in a worktree runs the same hooks. Delete a worktree with `git worktree remove`, never by deleting its directory, so the repository forgets it.

## A task that spans repositories

Before writing, decide for each repository the task writes to which guidance governs it: that repository's `AGENTS.md`, and the maintainer's private guidance where the repository's `AGENTS.md` says one exists. State the result once, in chat, when the task first writes to the repository. Never copy between a public and a private repository. Link to a tag instead. A change blocked in one repository is explained there by that repository's own rules.
