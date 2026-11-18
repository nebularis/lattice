<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: git hooks, GH-0 to GH-4

**Unit:** [`git-hooks`](../status/git-hooks.md)
**Branch:** `hooks-impl`, built autonomously on 2026-10-23 and committed slice by slice at the maintainer's request
**Plan:** [git-hooks.md](../plans/git-hooks.md)
**Decisions:** ADR-A133 (Proposed), the maintainer's answers of 2026-10-23 recorded in the plan

## Invariant

A commit is refused when it breaks a rule a governed check holds over the files it touches, and never for a file it did not touch. A push is never refused. A merge into `main` runs the merge gates. `mise run bootstrap` leaves the hooks installed in the shared hooks directory, covering every worktree, and never replaces a hook it did not write (ADR-A133).

## Test cases

| ID | Given / When / Then | Level | +/- | Result |
|---|---|---|---|---|
| GH1-01 to GH1-04 | a registry of checks / a change / a check runs only on what it governs, blocks or warns by moment, is skipped by name or "all", and a merge-only check waits for a merge | L1 | + | pass |
| GH1-05 | a staged change / read / its files and added lines | L1 | + | pass |
| GH1-06, GH1-07 | a branch, then `main` with a merge or a squash in progress / detect / a merge into `main`, never on the branch | L4 | + | pass |
| GH1-08 | a branch / `hooks:merge` / reads the branch's files and lines against `main` | L4 | + | pass |
| GH1-09, GH1-10, GH1-11 | a repository / install / both hooks written and executable, the old deny-list hook replaced, a foreign hook refused or, under bootstrap, left with a warning, and no failure outside git | L4 | +/- | pass |
| GH1-12 | the installed hook, without `mise` on the path / `git commit` with a denied term / refused, then allowed with `LATTICE_HOOKS_SKIP=deny-terms` | L5 | - | pass |
| GH2-01 | paths / which checks run / each change triggers its checks, and versioning only at a merge | L1 | + | pass |
| GH2-02 | a broken link in a touched file and in a generated site copy / links / only the touched file is reported | L4 | - | pass |
| GH2-03 | published-decisions findings / at a commit and at a merge / the touched ones warn, all block | L1 | + | pass |
| GH2-04, GH2-05, GH2-06 | touched literate modules / literate / each module checked with its options, a disagreement reported, and this checkout passes | L4 | +/- | pass |
| GH2-07 | a tool that cannot run / any check / a warning that asks for bootstrap | L1 | + | pass |
| GH3-01 to GH3-11 | Markdown / the writing rules / a semicolon in prose and "this document" in a literate README fail, code, URLs, entities, comments, front matter, tables, headings, fields and line breaks are not judged, a wrapped paragraph or list entry warns, only added lines are judged | L1 | +/- | pass |
| GH3-10 | a staged README / writing and wrapping / writing blocks at a commit and warns at a merge, wrapping warns once a file | L4 | + | pass |

## One command

```bash
mise run check:hooks
```

30 passed, 2026-10-23.

## Probes on this checkout

| Probe | Result |
|---|---|
| a hand edit to `ontology/party/spec/party.ttl`, staged | refused by `literate` in 1.4 s, naming the README and the drifting file |
| a new note with a broken link, staged | refused by `links`, naming the file and the target |
| a file under `apps/`, staged | only `deny-terms` ran |
| `mise run hooks:merge` for this branch | eight checks run, none fail, one wrapping warning |
| every commit of this branch | made through the hooks, from GH-1 on |

## Adversarial probes

| Probe | Result |
|---|---|
| merge detection made to ignore a squash | GH1-07 failed, then restored |
| the link check made to judge the site's generated copies | GH2-02 failed, then restored |
| the writing rules made to judge URLs | GH3-02 failed, then restored |

## Other checks run

`check:catalogue`, `check:agent-guidance`, `check:published-decisions`, `check:site-sections`, `check:import-guard`, `check:formal-freshness`, `check:ontology-versioning` and `check:deny-terms` pass. The whole-tree link check reported 197 broken links, as on `main`, until the merge of `claude/fix-topology-links`, after which it passes. That merge's one rewritten line with a semicolon was refused by the writing check and fixed.

## Deliberate non-coverage

- A merge made on GitHub runs no local hook, until CI runs on pull requests (ADR-A133's consequences). `mise run hooks:merge` covers it by hand.
- The full `mise run check`, including Java and the frontend, was not run. Nothing on this branch touches them.
- A check reads the working tree for staged files, so a file with further unstaged edits is judged as it stands on disk (ADR-A133 decision 8).

## Handoff

- **Built:** `tools/hooks.py`, `tools/writing_rules.py` and their tests, `check_links_in` in the link checker, `deny_terms.py install-hook` delegating, the tasks `hooks:install`, `hooks:run`, `hooks:merge`, `check:hooks` (in `check`) and `bootstrap:hooks` (in `bootstrap`), ADR-A133 (Proposed), the guidance in `AGENTS.md`, three skills and the developer guide (its task table and a Git hooks section). Merged in: `claude/fix-topology-links`, with its generated-copy rule moved into `check_links_in`. TD-75 to TD-77 record the writing rules' existing debt.
- **Installed:** the hooks are in this machine's shared hooks directory, so they already run in every worktree. A worktree without `tools/hooks.py` runs the deny-list check alone, as before.
- **Check first:** ADR-A133 decision 3's rule for checks of agreement across a set of files, and decision 5's split of blocking and warning checks.
- **Deviation from the design discussed in chat:** no `pre-push` hook at all, at the maintainer's answer, and the merge gate is a local merge (`pre-merge-commit`, or a commit on `main` while a merge or squash is in progress) since CI is manual.

## GH-6, 2026-11-18: the knowledge index leaves the post-merge hook

**Invariant.** The `post-merge` hook answers in seconds and never rebuilds the knowledge index, and the index is rebuilt at the first question after a merge, a merge that only deletes included.

**Measured before the change.** A squash of `docs/placement-vehicles-structure` (302 files) onto `main` at `bf1bf349`, in a scratch linked worktree, took 72.8 s, of which the hook took 72.0 s: `vyd build` 71.2 s, `vyd work build` 0.3 s, and `vyd work roadmap` 1.5 s when run on its own. An unchanged `vyd build` took 3.8 s and embedded nothing.

| Test | Shows |
|---|---|
| OR1-02 | the hook never fails and prints nothing about the knowledge index |
| VM2-02 | where `vyd` is absent, the hook names what it did not regenerate and never fails |
| WB4-08 | the regions are regenerated, ROADMAP.md's on `main` only |

**Adversarial probe.** The rebuild put back into `post_merge`, and OR1-02 failed until restored.

**Run.** `mise run check:hooks` 56 passed. In Вивід, `mise run check` passed with 1,564 tests, among them one that a deleted file an entry points into makes the index stale and the link check that now counts what a rebuild refused.

