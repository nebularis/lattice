<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: the work board

**Unit ID:** `work-board`
**Unit type:** multi-slice unit, one tool, generated registers, hooks and guidance
**Prefix:** WB
**Sketch:** [work-board.md](../sketches/work-board.md), the options, the measurements and the questions
**Status record:** [work-board.md](../status/work-board.md)
**ADR:** drafted in WB-5 as Proposed, at the next free number
**Status:** built 2026-11-02, WB-0 to WB-6. WB-7 waits on the merge of this branch into `main`. Every question answered in the sketch.

## Scope

One place where an agent marks the slice, unit or plan it picks up, before its first edit, and one tool that reads every local and remote branch and says where everything is, in a few hundred tokens. The mark is the slice's row in the slice board of its home unit's status record, with a state from a closed ordered set and the day it was reached. The tool derives the branch, joins the rows across refs, measures a branch by content, regenerates INDEX.md's register and ROADMAP.md's summary, and checks a touched board at every commit. Slice ids take one grammar, with a mechanical crosswalk from the historic ones. A presence file tells sessions sharing a worktree about each other. The rules go into AGENTS.md and the skills so the index can answer them.

Out of scope: a merge driver for registers, an agent column on the board, a web view, the Claude Code presence hook (a later slice, once WB-6 has run for a few weeks), and any change to what the knowledge index extracts beyond giving the `slice` family its definition.

## Dependencies

[ADR-A133](../../architecture/decisions/ADR-A133-git-hooks.md) for the hooks and their moments, [ADR-A134](../../architecture/decisions/ADR-A134-knowledge-index-and-design-shape-vocabulary.md) for what the index reads and how a family is checked, [ADR-A121](../../architecture/decisions/ADR-A121-repository-catalogue.md) for a generated region in a hand-written file, and the lifecycle, branching and design skills, which WB-5 changes.

## Decisions taken

| # | Decision | Date |
|---|---|---|
| 1 | the mark lives in the home unit's status record, its slice board (WB-Q1, option A) | 2026-11-02 |
| 2 | INDEX.md is replaced by a preamble and a generated region, its prose archived under `notes/` (WB-Q2) | 2026-11-02 |
| 3 | the state set is `planned`, `briefed`, `building`, `built`, `verified`, `merged`, `tagged`, with `blocked` and `dropped` aside, joined across refs by furthest along then latest day, and two refs at one state on one day are a double claim, printed and never chosen (WB-Q3) | 2026-11-02 |
| 4 | a state cell carries the day, not a commit. The commit is derived by `work:board --commits` from git (WB-Q6, sketch §5) | 2026-11-02 |
| 5 | slice ids take the grammar `PREFIX-segment(.segment)*`, a segment being optional capitals, digits and one lowercase letter, with the prefix declared on the plan's `**Prefix:**` line, crossed over mechanically from the historic ids (WB-Q4, WB-Q7) | 2026-11-02 |
| 6 | the post-merge hook regenerates ROADMAP.md on `main` and the maintainer commits it. `build:roadmap` serves on demand (WB-Q5) | 2026-11-02 |
| 7 | the `work` check blocks a commit on a malformed touched board, a stale INDEX.md region or an undefined slice id, and lands in the same merge as the sweep that normalises every board, never before it (WB-Q6) | 2026-11-02 |
| 8 | presence in a shared worktree is a git-ignored file per session under `.local/agents/`, written by `mise run work:here`, live while touched in the last twelve hours, with the rule in AGENTS.md (WB-Q8, option a) | 2026-11-02 |
| 9 | no plan or status record names a branch. The board derives it | 2026-11-02 |
| 10 | an agent marks before its first edit, in a commit of its own, and pushes only its own branch and never merges unless the maintainer says otherwise | 2026-11-02 |

## Slices

Each slice is briefed on this branch, built in default mode unless the maintainer says otherwise, and handed off with its Validation Pack. Estimates are in tokens.

| Slice | Delivers | Validation | Estimate |
|---|---|---|---|
| **WB-0** | the sketch, this plan, the status record, the INDEX.md entry | links resolve, the writing rules hold, the hooks pass | done |
| **WB-1** | `tools/work_board.py`, stdlib and git only: the board parser (the first table of a status record with `Slice` and `State` columns, by name), the state cell parser with its trail, the join, the reader over every local and remote-tracking ref through one `git cat-file --batch` with remotes folded by URL and each branch's ahead and behind against its upstream, `--all`, `--fetch`, `--measure` (the branching skill's content share) and `--commits`. Tasks `work:board` and `build:work`, the latter writing INDEX.md's generated region (Units and Work tables) between markers | `tools/test_work_board.py`: the parser on each board shape in the repository, the join on the sketch's stale-branch case and on a double claim, the fold of two remotes with one URL, a branch ahead of and behind its upstream, `--measure` on a squash-merged fixture, and determinism (a permutation of refs and a repeat give one board) | 70k |
| **WB-2** | the grammar and the prefixes on every plan that has slices, `work:rename` (the crosswalk built to `docs/developer/notes/slice-crosswalk-2026-11.md`, then applied longest-first to working documents, the exceptions baseline and the Validation Pack names with `git mv`, two-unit overlaps listed), `work:normalise` (a board rewritten into the standard columns and state words where its words map, the rest listed), both idempotent, run on this branch over every record, every `**Branch:**` line removed, and the `slice` family in `tools/knowledge/identifiers.py` built from the declared prefixes with the Work table as its definition | tests for the grammar, the crosswalk on each historic shape, idempotence (a second run changes nothing), the overlap report, and `check:identifiers` passing over the renamed tree | 60k |
| **WB-3** | INDEX.md as a preamble and the generated region, its old parts moved whole to `docs/developer/notes/coordination-index-2026-10.md`, and ROADMAP.md's §1 and §7 as generated regions (units table, gantt from the trails with undated slices listed below it, branches table), written by `build:roadmap` with the date and ref count in the heading | the regions regenerate to the same bytes twice, the gantt parses, `check:knowledge` reads the Units and Work tables, and `graph:ask -- find` ranks a Work row for a question about its deliverable | 30k |
| **WB-4** | the `work` check in `tools/hooks.py`, at a commit over the staged records and INDEX.md, at a merge over every record the merge changes, with messages naming the cell, the set and the task. The post-merge hook runs `build:work`, then `build:roadmap` on `main`, after the index rebuild, never failing | `tools/test_hooks.py` gains a staged malformed board refused, a stale region refused, a well-formed one accepted, and the post-merge regeneration leaving the files changed | 25k |
| **WB-5** | AGENTS.md's three contract bullets (mark before you touch, know who is here, ask the board), rebuilt into the Copilot copy. The lifecycle skill's "Picking up and finishing" with each rule a standard row, the branching skill's three tasks after merging `main` and the presence file under worktrees, the design skill's plan header with `**Prefix:**` and without `**Branch:**`, and the ADR as Proposed, recording the grammar, the state set, the regions and the check | `check:agent-guidance`, `check:knowledge`, `check:identifiers`, and `graph:ask -- find how do I take over a slice from another plan` ranking the standard | 35k |
| **WB-6** | `work:here`: writes `.local/agents/<session>.toml` from `CLAUDE_CODE_SESSION_ID` and `AI_AGENT` where set, with `--role` from `build`, `review`, `read`, `--model`, `--on`, touches it on a later run, lists sessions touched in the last twelve hours, `--leave`, and `--now` as the clock's input | tests with a temporary `.local/`, two sessions, one aged out, `--leave`, and no variable set | 15k |
| **WB-7** | the branches. For each branch the maintainer names live in WB-Q9, `main` merged, `work:normalise`, `work:rename` and `build:work` run, every slice it builds set to `building` with the day the work started, the mark committed alone and pushed. Every other branch and its worktree deleted by the maintainer | `mise run work:board --fetch` shows no `no mark` row and no branch the maintainer did not name | 25k |

WB-2, WB-3 and WB-4 merge into `main` together, since the check must never precede the sweep (decision 7). WB-7 follows that merge.

## Open

Nothing. WB-Q9 was answered on 2026-11-02, and the sketch's §12 holds each branch's disposition beside its measurement. WB-7 runs once this branch is on `main`, since a live branch marks its slices after merging `main` with the `work` check on it. The live set is `realign/config-authoring-studio`, `ccs-trunk`, `docs/placement-vehicles-structure`, `fml/isabelle-layers` while H3.1 completes, and `spikes/pol-map` as a spike.

## Done when

An agent's pick-up is one commit that the board shows on the next fetch. `mise run work:board` answers where every unit and slice is, across every local and remote branch, in a few hundred tokens, with no `no mark` row. A malformed board, a stale INDEX.md region or an undefined slice id is refused at the commit with the fix named. ROADMAP.md's regions are regenerated by the post-merge hook on `main`. `graph:ask -- find` answers how to take over a slice and where a slice is, from the standards and the Work table. The tests of WB-1, WB-2, WB-4 and WB-6 pass under `mise run check:work-board`.
