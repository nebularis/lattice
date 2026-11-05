<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: VM-5, the skills

**Unit:** [vyvid-migration](../plans/vyvid-migration.md)
**Status record:** [vyvid-migration](../status/vyvid-migration.md)

## Invariant

The skills an agent loads are composed by `vyd install --project` from the domains and LATTICE's own sources under `.vyvid/`, committed, each opening on the index-first block Вивід writes, and held to their sources by `vyd check skills`, as a hook check too. A skill of yesterday is removed only once that check, given the old file and its coverage map, proves every line of it has a home, and every citation and register pointer into the old skills reaches the composed text ([ADR-A152](../../architecture/decisions/ADR-A152-vyvid-adoption.md) decision 5, plan decisions 11 and 16).

## Tests

| ID | Given / When / Then | Level | Invariant | Pass | Kind |
|---|---|---|---|---|---|
| `vyd check skills` | the fifteen committed skills / the check / each equals what its sources compose to | L4 | held to their sources | `skills check passed: 15 composed, 0 problem(s)` | positive |
| `vyd check skills --from <old> --map <map>`, eleven runs | each old skill file at commit b08ece69 and its map in `docs/developer/notes/vm-5-coverage-maps/` / the check / every line of the old file is in a composed skill or in a row of the map | L4 | no line lost | exit 0 for each | positive |
| test_vm5_01 | no `vyd` on the path / the `skills` hook check / a note naming `mise run bootstrap`, nothing failed | L1 | never blocks | the check returns no failure | negative |
| test_vm5_02 | this checkout, trusted / the `skills` hook check / nothing | L4 | the check runs from a hook | no message | positive |
| `mise run check:agent-guidance` | AGENTS.md's skills table, the fifteen directories, the marketplace / the check / they agree and every link resolves | L4 | the guidance is whole | `0 problem(s)`, 9 passed | positive |
| `test_the_build_reports_nothing_but_the_known_notes` | the registers re-pointed / `vyd build` / no note on a pointer or an anchor | L4 | every pointer resolves | among the 38 of `check:knowledge` | positive |

## What ran, and what it showed

Run on 2026-11-05 and read in full. The ten old skill directories were removed and `vyd install --project` wrote fifteen, eight under the old names and seven new, `lattice-mise`, `lattice-windows` and `lattice-environment-lessons` from `lattice-toolchain`, `lattice-probing`, `lattice-query-writing` and `lattice-shacl-testing` from `lattice-triple-stores`, and `lattice-ontology-modelling`. `vyd check skills` passed with no problem. The eleven coverage runs, one per old file with its map, passed. The maps are the migration patch's, keyed on the old files' line numbers, and two rows were set by hand: the old branching skill's bullet on `knowledge.ttl` conflicts is mapped as removed, since VM-3 removed the file and the bullet with it, and the lifecycle line the patch marked for review, that no second status record is created for a unit, is placed at the composed lifecycle skill's line that says so. Every other row the first runs reported was a hard-wrapped fragment of a line that sits whole in a composed skill, added to the maps as joined onto one line after an exact substring match, and no line was mapped by guess. The old files are read back with `git show b08ece69:.claude/skills/<name>/SKILL.md`.

The 117 citations of the two old skills in 39 files became 35 replacements in prose, each chosen from what its sentence is about, `lattice-mise` for tasks and the environment, `lattice-windows` for Windows, `lattice-environment-lessons` and `lattice-constrained-environments` for the environment's lessons and blocks, `lattice-probing`, `lattice-query-writing` and `lattice-shacl-testing` for a store's behaviour, a query's cost and a SHACL test. ADR-A117 is Accepted, so a dated addendum names the fifteen rather than an edit to its text. This unit's own records keep the old names as history. The 201 register pointers, all in `standards.md` and `principles.md`, were re-pointed from the composed text (decision 11): a script matched each old section's lines, as fragments since the old files were wrapped and the sources joined, against every composed section and re-pointed 156 where one section held at least half of them, and the 45 it left, a tie between the two ontology skills and sections reworded past the threshold, were placed by hand from the headings, the old architecture skill's structure standards in `lattice-design`, the old testing skill's SHACL rows in `lattice-shacl-testing` and its bound-variable rule in `lattice-query-writing`, the conftest cache in `lattice-shacl-testing`, and the rest under the same heading's new slug. `mise run build:knowledge` then printed no note on a pointer or an anchor, `mise run check:knowledge` passed with 38, `mise run check:identifiers` with 2107 identifiers mentioned and 0 unresolved, `mise run check:hooks` with 48, and `mise run check:agent-guidance` with 0 problems and 9 passed. `mise run check` ran after the slice, unfiltered to a file, exit 0 from `mise` in 324 s, and its 3,447 lines were compared line by line with the VM-4 log, which had been compared the same way with the VM-3 log the agent read whole, differing only in `check:hooks` at 48 passed, `check:identifiers` at 2111 identifiers in 860 files, and timings.

## One command

```bash
mise run check:hooks
```

Run from the checkout's root, with `vyd check skills` and `mise run check:agent-guidance` beside it. A pass is every test passing, the two skills tests skipped where `vyd` is not installed or the binding is not trusted, `15 composed, 0 problem(s)`, and `0 problem(s)` from the guidance check.

## Artefacts

The fifteen skills under `.claude/skills/`, the six sources under `.vyvid/` with their citations renamed, the eleven maps under `docs/developer/notes/vm-5-coverage-maps/`, the `skills` check in `tools/hooks.py` with `test_vm5_01` and `test_vm5_02`, the task `check:skills` in `check` since 2026-11-05, AGENTS.md's skills table and `.github/copilot-instructions.md`, `.claude-plugin/marketplace.json`, the addendum of 2026-11-05 on ADR-A117, the 35 renamed citations, and the 201 re-pointed cells of `standards.md` and `principles.md`.

## Not covered here

The composed skills' wording is the domains', and a rule LATTICE's old skill stated that the domain words differently is held by the coverage map, not by a text match, so a reader of a register row reaches the section and not always the sentence. The `shown = "asked"` headers and the reminder hook are Вивід's, tested in its suite. Windows, proven after the switch (plan, decision 3). The copies and the page at the old path, VM-6.
