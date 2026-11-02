<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# The work board: status

**Unit ID:** `work-board`
**Plan:** [work-board.md](../plans/work-board.md)
**Sketch:** [work-board.md](../sketches/work-board.md)
**Mode:** default. Write, then hand off.
**Status:** building 2026-11-02. WB-0 to WB-2 built, WB-3 next, WB-Q9 open. Autonomous mode from WB-1 at the maintainer's request, commits to `docs/work-board` only.

## Position

| Slice | Deliverable | State | Blocked on |
|---|---|---|---|
| WB-0 | the sketch, the plan, this record, the INDEX.md entry | built 2026-11-02 |  |
| WB-1 | `tools/work_board.py`, `work:board`, `build:work` | built 2026-11-02, building 2026-11-02 |  |
| WB-2 | the slice grammar, `work:rename`, `work:normalise`, the sweep, the `slice` family | built 2026-11-02, building 2026-11-02 |  |
| WB-3 | INDEX.md replaced, ROADMAP.md's generated regions, `build:roadmap` | building 2026-11-02 |  |
| WB-4 | the `work` check and the post-merge regeneration | planned | WB-3 |
| WB-5 | AGENTS.md, the skills, the standards, the ADR | planned | WB-4 |
| WB-6 | `work:here` | planned | WB-1 |
| WB-7 | the branches marked or deleted | planned | WB-4, WB-Q9 |

## History

- 2026-11-02: the sketch, with the branch survey, the options and WB-Q1 to WB-Q6, committed on `docs/work-board` from `main` at `df0ddd1a`. The maintainer answered WB-Q1 to WB-Q6, and the sketch was revised with the slice grammar, the blocking conditions, the presence design and the measured branch table. WB-Q7 and WB-Q8 answered per the leanings, and the state cell keeps a day rather than a commit.
- 2026-11-02: WB-0, the plan and this record. WB-Q9 open.
- 2026-11-02: WB-1 built. `tools/work_board.py` reads every status record's board at the tip of every local and remote branch through one `git cat-file --batch`, folds remotes by URL, joins rows per slice, measures a branch by content and writes INDEX.md's generated region. On this checkout the board reads 28 branches in 1.9 s. 13 tests pass under `mise run check:work-board`. The region appended to INDEX.md shows 21 units with boards and every unparsed cell, which WB-2 normalises.
- 2026-11-02: WB-2 built. `tools/work_migrate.py` with `work:normalise` and `work:rename`, both idempotent. The sweep on this branch: 63 records normalised, every board row and every Status line now opens with a state word, 21 records had boards, 174 ids crossed over 11 units, 193 files rewritten, 137 Validation Packs renamed, 26 left as they were, 3 ids claimed by two units (C1, C2, C3 of CCS and track C) left outside their own documents. The `slice` identifier family is built from the plans' Prefix lines and defined by INDEX.md's Work table. 169 slices a plan names with no board row are baselined in the exceptions file as TD-137. Status lines of the 42 records without a board were set by reading each record, in a Sonnet session, and the ones it was unsure of are listed in this slice's handoff. The state cell's day where the record gave none is the day git last changed that cell's text. Dead links in the renamed Validation Packs, to the authoring service that has since moved, became plain text, and their semicolons commas, since a renamed file is judged whole by the hooks. 25 tests pass under `mise run check:work-board`.
