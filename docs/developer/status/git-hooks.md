<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Git hooks: status

**Unit ID:** `git-hooks`
**Plan:** [git-hooks.md](../plans/git-hooks.md)
**ADR:** [ADR-A133](../../architecture/decisions/ADR-A133-git-hooks.md), Proposed
**Branch:** `hooks-impl`, from `main` at `04f6f9ae`
**Mode:** autonomous, at the maintainer's request on 2026-10-23. Each slice is committed locally, and the branch is handed back for review before the merge into `main`.

**Validation Pack:** [git-hooks](../validation/git-hooks.md)

## Position

| Slice | State |
|---|---|
| GH-0 | built |
| GH-1 | built: `tools/hooks.py`, its tests (12), the tasks, bootstrap |
| GH-2 | built: the commit checks and merge gates wired, 19 tests |
| GH-3 | built: `tools/writing_rules.py`, wired as the writing and wrapping checks, 30 tests in all |
| GH-4 | built: `AGENTS.md` and its Copilot copy, the toolchain, publication-hygiene and lifecycle skills, the developer guide (task table and a Git hooks section), the ADR index |

## History

- 2026-10-23: GH-0, ADR-A133 (Proposed), the plan and this record.
- 2026-10-23: GH-1, the dispatcher with the deny-list check, installation into the shared hooks directory with its fallback, the tasks `hooks:install`, `hooks:run`, `hooks:merge`, `check:hooks` and `bootstrap:hooks`. Twelve tests pass. Adversarial probe: merge detection made to ignore a squash, and GH1-07 failed until restored.
- 2026-10-23: GH-2, the commit checks (literate per module, agent guidance, catalogue, import guard, links in the touched Markdown, formal freshness, site sections, published decisions as a warning) and the merge gates (published decisions over the whole tree, ontology versioning). The link checker gains `check_links_in`. ADR-A133 decision 3 now says that a check of agreement across a set of files judges the whole set. Probes on this checkout: a hand edit to `party.ttl` refused by the literate check in 1.4 s, a broken link refused by the link check, a change to `apps/` running only the deny-list check. The catalogue's bypass scan found that the first version built paths under `tools/` itself, fixed without adding exceptions. Adversarial probe: the link check made to judge the site's generated copies, and GH2-02 failed until restored.
- 2026-10-23: GH-3, the writing rules on added Markdown lines: a semicolon in prose and "this document" in a literate README block at a commit and warn at a merge, and a hard-wrapped line warns, reported once a file. Calibrated over the 660 tracked Markdown files: 2,933 lines with a semicolon in prose in 216 files, 25 uses of "this document" in literate READMEs and about 28,000 hard-wrapped lines, all existing debt that only an edited line meets. The calibration found header blocks of bold fields (**Status:**, **Date:**) misread as wraps, now fields. Adversarial probe: URLs no longer excluded, and GH3-02 failed until restored.
- 2026-10-23: GH-4, the guidance. `AGENTS.md` gains the rule that the hooks are a floor and a bypass is recorded, the toolchain skill a section on the hooks, the lifecycle skill the merge gate, the publication-hygiene skill the deny-list as one of the commit checks. The developer guide lists the new tasks, and the ADR index lists A-133 with a note on numbering against the placement branch.
- 2026-10-23: handoff. Every slice built and committed, `mise run check:hooks` 30 passed, `mise run hooks:merge` passes for the branch. Ready for the maintainer's review and the merge into `main`. ADR-A133 is Proposed, for the maintainer to accept.
- 2026-10-23: at the maintainer's request, a Git hooks section in the developer guide, a merge of `claude/fix-topology-links` (the whole-tree link check now passes, and its rule for generated copies lives in `check_links_in`), and TD-75 to TD-77 for the writing rules' existing debt. `check:hooks` 30 passed again. Ready for the merge into `main`.
