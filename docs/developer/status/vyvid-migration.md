<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# LATTICE adopts Вивід: status

**Unit ID:** `vyvid-migration`
**Plan:** [vyvid-migration.md](../plans/vyvid-migration.md)
**Sketch:** [vyvid-migration.md](../sketches/vyvid-migration.md)
**Mode:** default. Write, then hand off, unless the maintainer says otherwise.
**Status:** building 2026-11-05. VM-0 built. VM-1 building from 2026-11-05 on the maintainer's go-ahead, with every other branch paused until the unit merges.

## Position

| Slice | Deliverable | State | Blocked on |
|---|---|---|---|
| VM-0 | the sketch rewritten, the plan, this record, the INDEX.md region | built 2026-11-05 |  |
| VM-1 | the binding, `bootstrap:vyvid`, the comparison | building 2026-11-05, briefed 2026-11-05 |  |
| VM-2 | the index tasks and hooks over `vyd`, AGENTS.md's index section, the ADR | planned | VM-1 |
| VM-3 | the quanta and owners extractor, the tests against Вивід, the deletions | planned | VM-2 |
| VM-4 | the board tasks and the `work` check over `vyd`, the old tools removed | planned | VM-3 |
| VM-5 | the fifteen composed skills, the coverage proven, the citations and pointers | planned | VM-4 |
| VM-6 | the moves, the page at the old path, TD-2 cleared | planned | VM-5 |

## Next action

The maintainer's go-ahead for VM-1, then VM-1 on this branch.

## History

- 2026-11-04: the sketch, with Вивід's facts at 0.1.0, the table of what moves, five slices and VM-Q1 to VM-Q6, committed on `vyvid-migration` from `main`.
- 2026-11-05: `main` merged into the branch. VM-Q1 to VM-Q6 answered by the maintainer through Вивід's side, with the changes since the first draft, skills composed and committed rather than cut, a reminder hook, generated regions honoured, the board in Вивід, Windows proven after the switch. A handoff patch of 35 files with eleven coverage maps received and found to apply cleanly. The sketch rewritten against Вивід 0.2.1, the plan written with twelve decisions and six slices, and this record opened. VM-0 built.
