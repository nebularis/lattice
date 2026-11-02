<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A151: The work board. A slice's state is written once, on its home unit's board, and read across every branch

**Status:** Proposed, 2026-11-02
**Date:** 2026-11-02
**Supersedes:** none
**Related:** [ADR-A133](ADR-A133-git-hooks.md) (the hooks and their moments), [ADR-A134](ADR-A134-knowledge-index-and-design-shape-vocabulary.md) (what the index reads), [ADR-A121](ADR-A121-repository-catalogue.md) (a generated region in a hand-written file)
**Unit:** [`work-board`](../../developer/plans/work-board.md)

## Context

Agents build in parallel, each in its own worktree on its own branch, and the question "where is slice X being built, and what is on branch Y" was answered by reading. Measured on 2026-11-02, 18 refs held commits `main` lacked, two of them marked nothing, the hand-written coordination index was 1,102 lines and a month stale, thirteen status records named a branch that had since moved, and the slice boards took five column shapes with state cells in prose, so no script could compare them and the knowledge index could not be asked. Branches are squash-merged, so ancestry says nothing about whether a branch is merged. The sketch [work-board.md](../../developer/sketches/work-board.md) measured this and drew the options.

## Decision

1. **A slice's state is written in one place, its row on the slice board of its home unit's status record**, the unit whose plan defines it, whichever branch builds it. The adopting unit's record says so in its history and never carries a second row.
2. **The board has one shape**, `Slice`, `Deliverable`, `State`, `Blocked on`, found by its column names, with other columns kept and ignored. A state cell opens with a word of the closed, ordered set `planned`, `briefed`, `building`, `built`, `verified`, `merged`, `tagged`, with `blocked` and `dropped` aside, and the day it was reached from `building` on, newest first, so the cell is its own trail. The day is written and the commit is derived from git, since the commit that carries a mark does not exist when the mark is written, and a commit stops resolving once its branch is squash-merged and deleted.
3. **A slice id is `PREFIX-segment(.segment)*`**, a segment being optional capitals, digits and one lowercase letter, with the prefix declared on the unit's plan's `**Prefix:**` line. The `slice` identifier family is built from the declared prefixes and defined by INDEX.md's Work table, so a slice mentioned and defined nowhere fails `check:identifiers`. The historic ids were crossed over mechanically by `mise run work:rename`, with the crosswalk kept under `docs/developer/notes/`.
4. **One tool reads the boards at the tip of every local and remote branch** through one `git cat-file --batch`, folds remotes that share a URL, reports each branch's drift from its upstream, joins the rows per slice by the one furthest along the ladder and then the later day, prints two branches both building one slice as a double claim and never chooses, flags a branch's row behind `main`'s as stale, and measures a branch by content. `mise run work:board` is the answer to "where is X" and costs a few hundred tokens.
5. **INDEX.md is the generated register**, a preamble and a region written by `mise run build:work` from the working tree, the Units and Work tables, which the knowledge index reads as the class Slice. ROADMAP.md's "programme at a glance" and "branches" sections are generated regions written by `mise run build:roadmap` from every branch, the first with a gantt of the dated slices.
6. **An agent marks before its first edit**, setting the row to `building <day>`, regenerating the register and committing the mark alone, so the board sees the claim from the first push. Handing off sets `built`, verification `verified`, and the merge into `main` sets `merged` in the merge commit.
7. **No plan and no status record names a branch.** The board derives it.
8. **The `work` hook check blocks a commit and a merge** whose touched status record's Status line or board row opens with no state word, whose row from `building` on has no day, whose slice id is outside the grammar, or whose INDEX.md region is stale, naming the task that fixes it. The post-merge hook regenerates INDEX.md's region after the knowledge index and ROADMAP.md's regions on `main`, and never fails. The check landed in the same merge as the sweep that normalised every record, never before it.
9. **Presence in a shared worktree is a git-ignored file per session** under the worktree's `.local/agents/`, written by `mise run work:here` from the session id the client exposes and the role, model and slices stated by hand, live while touched in the last twelve hours, since liveness is a question only a clock answers. The rule that a session asks the maintainer before writing where another is building is in AGENTS.md.

## Consequences

A pick-up is one commit that the board shows on the next fetch, and a branch that marks nothing is a row in the Branches table rather than a thing nobody knows. A unit's record is the one authoritative live state, as the lifecycle already said, and the register and the roadmap are derived from it, never edited. A live branch that merges `main` runs `work:normalise`, `work:rename` and `build:work` once, which the branching skill lists beside the index rebuild. Slices a plan names with no board row resolve only through the identifier exceptions baseline until their rows are written (TD-137). The gantt draws dated slices of the last thirty days and open work, never a plan nobody made. The Claude Code hook that would write presence automatically is a later slice, once the task has run for a few weeks.

## Provenance

The sketch [work-board.md](../../developer/sketches/work-board.md) holds the measurements, the five options for where the mark lives and their costs, the branch survey, and the questions WB-Q1 to WB-Q9 with the maintainer's answers of 2026-11-02. The plan [work-board.md](../../developer/plans/work-board.md) holds the decisions and slices WB-0 to WB-7.
