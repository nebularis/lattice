<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: git hooks

**Unit ID:** `git-hooks`
**ADR:** [ADR-A133](../../architecture/decisions/ADR-A133-git-hooks.md), Proposed
**Status record:** [git-hooks.md](../status/git-hooks.md)
**Status:** built 2026-10-23 on `hooks-impl`, slice by slice, autonomously at the maintainer's request. Handed back for review before the merge into `main`. [Validation Pack](../validation/git-hooks.md).

## Scope

A dispatcher that runs the repository's cheap checks at the moments ADR-A133 names, installed by bootstrap, with the checks scoped to what a change touches, a writing-rules check for added lines, and the guidance that makes every agent follow it.

Out of scope: CI on pull requests (the workflows stay manual), and any check that takes minutes, which stays in `mise run check`.

## Decisions taken

| # | Decision | Date |
|---|---|---|
| 1 | the published-decisions check warns at commit and blocks only at a merge into `main`, never at a push, since a cloud agent pushes for the maintainer to receive its work | 2026-10-23 |
| 2 | one dispatcher, `tools/hooks.py`, installs every hook | 2026-10-23 |
| 3 | `mise run bootstrap` installs the hooks | 2026-10-23 |
| 4 | the principles are an ADR (A133), and the guidance and skills state them so every agent follows them | 2026-10-23 |

## Slices

| Slice | Delivers | Validation |
|---|---|---|
| **GH-0** | ADR-A133, this plan, the status record | links resolve, the writing rules hold |
| **GH-1** | `tools/hooks.py`: the change set for each moment, the merge detection (a merge or squash into `main`), the registry of checks with the paths each governs, the runner with blocking and warning outcomes, `LATTICE_HOOKS_SKIP`, and installation of `pre-commit` and `pre-merge-commit` through a short script with its fallback. The deny-list check moves in as the first check, and `deny_terms.py install-hook` installs the dispatcher. Tasks `hooks:install`, `hooks:run` (the commit checks over what is staged) and `hooks:merge` (the merge checks against `main`). Bootstrap runs `hooks:install` and warns where a foreign hook is present | `tools/test_hooks.py`: path rules, merge detection, skips, installation into a temporary repository, refusal of a foreign hook, the old hook replaced |
| **GH-2** | the commit checks wired, each over the touched files: literate freshness per module, agent guidance, catalogue and import guard, links in named Markdown files (a new mode of the link checker), formal freshness, site sections, published decisions as a warning filtered to the touched documents. The merge gates: published decisions over the whole tree, and ontology versioning | tests for each rule's trigger, a link check over named files, and a staged change in a temporary repository that fails each blocking check |
| **GH-3** | `tools/writing_rules.py`: on the added lines of Markdown, outside code blocks, code spans, front matter and HTML comments, a semicolon blocks, "this document" in a literate README blocks, and a hard-wrapped paragraph warns. Wired into the dispatcher | `tools/test_writing_rules.py`: each rule, each exclusion, and a wrapped list item |
| **GH-4** | the guidance: `AGENTS.md` (rebuilt into the Copilot copy), the toolchain, publication-hygiene and lifecycle skills, the developer guide's task table, the ADR index | `check:agent-guidance`, the hooks themselves on the commit |

## Done when

A commit that breaks a governed rule is refused with the file and the reason, a commit that touches nothing a check governs runs only the deny-list check, a push is never refused, a merge into `main` runs the gates, and `mise run bootstrap` leaves the hooks installed. `mise run check:hooks`, the tests of GH-1 to GH-3, passes.
