## The hooks

`mise run bootstrap` installs the hooks ([ADR-A133](../../../docs/architecture/decisions/ADR-A133-git-hooks.md)). The commit checks and merge gates are named in the skill `lattice-toolchain`. After any merge the `post-merge` hook runs `build:knowledge`. `LATTICE_HOOKS_SKIP` skips named checks, as `LATTICE_HOOKS_SKIP=links,writing` does, and `mise run check:hooks` tests the dispatcher (`tools/hooks.py`) and the writing rules (`tools/writing_rules.py`).

| a commit | the checks the staged files touch: the deny-list, literate freshness per module, agent guidance, the catalogue, the import guard, links in the touched Markdown, formal freshness, the site's copies and the writing rules. Published decisions and hard wraps warn |
| a merge into `main` (a clean merge, or a commit on `main` while a merge or a squash is in progress) | the same checks over every file the merge changes, all blocking but the writing rules, plus published decisions over the whole tree and ontology versioning. `mise run hooks:merge` runs this by hand, for example before merging on GitHub |

## Measuring a branch

Branches here are usually squash-merged. `mise run work:board -- --measure` computes this share for every branch, and the board's Branches table says which status records each branch moves and which branch marks nothing (plan `work-board`).

## Merging

`check:identifiers` is the identifier check. - **`tools/knowledge/knowledge.ttl` conflicts.** Take `main`'s file and add the branch's own relation rows back.

`mise run build:knowledge` rebuilds the index. The three tasks are `mise run work:normalise -- --apply`, `mise run work:rename -- --apply` and `mise run build:work`, and the join rule is ADR-A151. Versions move by `mise run release:prepare`.

## Worktrees

In LATTICE the local folder is `.local/`, git-ignored, `mise run bootstrap` is needed once per worktree for its `.venv`, and presence is a file under `.local/agents/` written by `mise run work:here` (STD-306).

## A task that spans repositories

That repository's `AGENTS.md`, and the maintainer's private guidance where the repository's `AGENTS.md` says one exists.
