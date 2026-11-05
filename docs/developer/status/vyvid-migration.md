<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# LATTICE adopts Вивід: status

**Unit ID:** `vyvid-migration`
**Plan:** [vyvid-migration.md](../plans/vyvid-migration.md)
**Sketch:** [vyvid-migration.md](../sketches/vyvid-migration.md)
**Mode:** default. Write, then hand off, unless the maintainer says otherwise.
**Status:** built 2026-11-05. VM-0 to VM-4 built, VM-1 and VM-3 verified, ADR-A152 accepted, trust point 3 run. VM-4 waits at its gate, with every other branch paused until the unit merges.

## Position

| Slice | Deliverable | State | Blocked on |
|---|---|---|---|
| VM-0 | the sketch rewritten, the plan, this record, the INDEX.md region | built 2026-11-05 |  |
| VM-1 | the binding, `bootstrap:vyvid`, the comparison | built 2026-11-05, building 2026-11-05, briefed 2026-11-05 |  |
| VM-2 | the index tasks and hooks over `vyd`, AGENTS.md's index section, the addenda | built 2026-11-05, building 2026-11-05 |  |
| VM-3 | the quanta and owners extractor, the tests against Вивід, the deletions | verified 2026-11-05, built 2026-11-05, building 2026-11-05 |  |
| VM-4 | the board tasks and the `work` check over `vyd`, the old tools removed | built 2026-11-05, building 2026-11-05 |  |
| VM-5 | the fifteen composed skills, the coverage proven, the citations and pointers | planned | VM-4 |
| VM-6 | the moves, the page at the old path, TD-2 cleared | planned | VM-5 |

## Next action

The maintainer runs `mise run check:hooks` for VM-4's gate and gives the word for VM-5, the fifteen composed skills. No `vyvid.toml` edit is pending, so trust holds.

## Trust points

`vyd trust` is the maintainer's to run in a terminal, and any edit to `vyvid.toml` lapses it (plan, decision 13), so the edits are batched and trust is asked at these points only.

| Point | After | What waits on it |
|---|---|---|
| 1 | VM-1's handoff, `vyvid.toml` as the patch gave it plus the question family marked `removable` | `vyd context`, `test_vm1_08`, and `vyd install --project` in VM-5. Everything else in VM-1's comparison ran untrusted, since an untrusted project gives knowledge alone |
| 2 | VM-3's `[[project.extractors]]` entry for quanta and owners, written 2026-11-05 | the extractor's run in `vyd build`, the two quanta tests of `test_knowledge_base.py`, and `vyd install --project` in VM-5. Run by the maintainer 2026-11-05, which showed the two tests failing |
| 3 | VM-3's slice family `SL` and the identifier scan's `skip` of the slice crosswalk, written 2026-11-05 after the full check ran trusted | the extractor's run in `vyd build`, the three quanta and owner tests of `test_knowledge_base.py`, and `vyd install --project` in VM-5. Run by the maintainer 2026-11-05, after which the 38 pass |

The user-configuration entry (VM-Q1, both), for the maintainer's own `config.toml`, binds by remote and names nothing the repository's file does not. It is here so the two are written once.

```toml
[[projects]]
name = "lattice"
code = "~/work/lattice"
match = { remote = "github.com/nebularis/lattice" }
```

## History

- 2026-11-04: the sketch, with Вивід's facts at 0.1.0, the table of what moves, five slices and VM-Q1 to VM-Q6, committed on `vyvid-migration` from `main`.
- 2026-11-05: `main` merged into the branch. VM-Q1 to VM-Q6 answered by the maintainer through Вивід's side, with the changes since the first draft, skills composed and committed rather than cut, a reminder hook, generated regions honoured, the board in Вивід, Windows proven after the switch. A handoff patch of 35 files with eleven coverage maps received and found to apply cleanly. The sketch rewritten against Вивід 0.2.1, the plan written with twelve decisions and six slices, and this record opened. VM-0 built.
- 2026-11-05: VM-1 begun. Вивід's side answered three points and raised two more, folded into the plan as decisions 13 to 15 and the revised 9 to 11. The pin is `v0.2.2`, released that day with the exit code of `vyd check skills` fixed. The patch's binding files applied, `vyvid.toml`, the reminder hook's settings for Claude Code and Copilot, and LATTICE's additions under `.vyvid/`. `uv` and `VYVID_VERSION` pinned in `mise.toml`, `bootstrap:vyvid` written as `tools/bootstrap_vyvid.py` and wired into `bootstrap`, `check:vyvid-binding` with eight tests. `facets.md` copied to `notes/facets-register-2026-11-05.md`. ADR-A152 drafted Proposed, since `vyvid.toml` and `.vyvid/` sit at the root. Paused at trust point 1.

## VM-1 comparison, 2026-11-05

Every command run in this worktree with the binding untrusted, which gives knowledge alone, so each result below is what a clone has before anyone trusts the file.

| What | LATTICE's tooling | Вивід | Difference | Disposition |
|---|---|---|---|---|
| the index build | `build:knowledge`, ten notes on claim length, one on a Provided by cell | `vyd build`, 63 s with embeddings, 110,941 quads, 119 entries answered by `triple-stores` with LATTICE's copies left out of the index | the same ten notes, plus three from the domains' own registers | none |
| the board | `work:board --all --commits`, 527 lines | `vyd board --all --commits`, 527 lines | four cells, where Вивід prints `mise run work:rename -- --apply` and LATTICE printed `work:rename` | none, Вивід's is the fuller command |
| the register region | `build:work --check` current | `vyd work build --check` current | none | none |
| the roadmap regions | `build:roadmap --check` stale, since the branch gained commits | `vyd work roadmap --check` stale, the same message | none | none |
| the `work` hook check | passes | `vyd work check` exit 0 | none | none |
| identifiers | `check:identifiers` passes | 102 unresolved, every one in the question family `LGQ`, 2 variants (`ADR-AC1`, `ADR-AC2`), 50 removable entries no longer defined, 25 stale exceptions, exit 1 | LATTICE's question family is counted and never failed, so a question raised in a note, a record or a decision never fails the check. Вивід has no non-failing flag, and `removable = true` has that effect | `LGQ` marked `removable = true` in `vyvid.toml` the same day, before any trust was given, after which `vyd check identifiers` exits 0. Вивід may add a non-failing key later. The variants, the removable entries and the stale exceptions are reported on both sides and fail neither |
| the moves | none | `vyd move check --ref main`, nothing differs | none | none |
| the facet register | `facets.md`, 329 table rows | the packaged general scheme, 329 rows, identical row for row, definitions and broader and narrower links included. Only the title, the licence line and the preamble differ | none | decision 14's comparison is done, no additions file is needed, and `facets.md` stays until VM-3 decides its future |
| `find` | `graph:ask -- find`, hit@5 0.884 and MRR 0.806 on the 43 scored questions, 0.800 and 0.567 on the 5 held out | `vyd find`, the same four figures on this checkout, run through `mise run bench:lattice` in Вивід's checkout against this worktree | the top five differ in 4 of 48 questions, each time in the fourth or fifth place, and every expected entry keeps its rank | none |
| the contract | none | `vyd context` fails with `KeyError: 'lattice'` when the project is declared by `vyvid.toml` and has no entry in the user configuration | Вивід's bug, reported to its side | fixed in 0.2.3, pinned 2026-11-05, after which `vyd context` names LATTICE and `test_vm1_08` passes |
- 2026-11-05: VM-1's comparison run untrusted and recorded above. Agreement on the board, the regions, the hook check, the moves and the facets. One difference in the identifiers check, the question family failing in Вивід and never in LATTICE, with its disposition. One Вивід bug found, `vyd context` on a file-declared project. The bake-off started on this checkout.
- 2026-11-05: the bake-off on this checkout scored both sides alike, hit@5 0.884 and MRR 0.806 on the 43, 0.800 and 0.567 on the held-out 5, the top five differing in 4 of 48 below the expected entries. The question family marked `removable` in `vyvid.toml` before any trust, so `vyd check identifiers` exits 0. The Validation Pack [VM-1](../validation/VM-1.md) written, eight tests passing with the eighth skipped until trust. VM-1 built and handed off, paused at trust point 1.
- 2026-11-05: the maintainer accepted ADR-A152 and ran `vyd trust`, trust point 1. The pin moved to `v0.2.3`, which answers `vyd context` for a project only `vyvid.toml` declares, and the eight binding tests pass. `main`'s two technical-debt commits merged in. The 133 hard-wrapped lines under `.vyvid/` joined by a script that keeps every word, since those sources are hand-written and never regenerated (decision 16). VM-2 begun.
- 2026-11-05: VM-2 built. `tools/vyd.py` runs `vyd` for a task or a hook and turns an absent tool, or an exit of 2, into a note and a pass. `graph:ask`, `build:knowledge` and `check:identifiers` run over it, `mise run vyd -- <args>` passes the rest through, the identifiers hook check and the post-merge rebuild run over it, with four tests in `tools/test_hooks.py`. AGENTS.md's index section cut to what is LATTICE's and the Copilot file regenerated. PRI-79 added, Proposed. The addenda of 2026-11-05 on ADR-A134 and ADR-A151 written, Proposed. The bake-off's first three questions return the same top five as before the switch. A second `vyd build` takes 3.5 s, so the post-merge hook stays cheap. Validation Pack [VM-2](../validation/VM-2.md).
- 2026-11-05: v0.2.4 pinned, which keeps the misses log per project and prints a passing identifier check as one line. STD-319 added for the weak answer on how a register row is written. VM-3 built. `tools/knowledge/extractor.py` is the command `vyvid.toml` declares, run by `vyd build` once trusted, writing the fifteen quanta, identical to the old extractor's, and the catalogue's units. The knowledge tests re-pointed at Вивід's store as `test_knowledge_base.py`, 24 kept or restored of 69, the rest testing the old modules, and one new test holds the build's notes to the known ones. All passed before the deletions and after. Removed `extract.py`, `ask.py`, `identifiers.py`, `facets.py`, `anchors.py`, `embed.py`, `knowledge.ttl` and their six test modules, about 5,300 lines. `knowledge.ttl` held no term Вивід's vocabulary lacks. `facets.md` stays (decision 14). Two findings for Вивід's side: `vyd find WB-10 --kind slice` returns nothing, so slices are not indexed from this checkout, and the owl-terms extractor names a module by its directory, `module/lattice/ontology/ledger/vocab`, while a declared unit is `module/lattice/ledger`, so a term's owner and an Owner edge are different nodes. Validation Pack [VM-3](../validation/VM-3.md).
- 2026-11-05: VM-3 reopened. With trust at point 2 the two quanta tests ran and failed, STD-319 governing `registers`, no quantum, and CAP-98 provided by `tools/owl_profile.py`, no unit, which `main`'s build had reported before this unit, with thirteen notes on Owner cells ending in a slash. Вивід's side fixed its part as v0.2.5, pinned, and the two rows are corrected. The extractor declares `unit_paths`, each unit's folder, so a term's owner is the unit an Owner cell reaches, with a test on foundation's terms and MEC-01. The slice family `SL` added to `vyvid.toml` on INDEX.md's Work table with `defined_only`, the crosswalk skipped as the old check skipped it, and the fourteen VTB test identifiers excused, so `vyd find WB-10 --kind slice` answers and `check:identifiers` checks 466 slice mentions, trust point 3. The 132 removed tests accounted for one by one in the Validation Pack, with twelve Вивід tests its suite lacks and one lost corpus check recovered, the unpromoted question read from the build's findings. The two full checks of the first pass explained there, the first's exit code was its pipeline's. `mise run check` ran trusted at v0.2.5, exit 0 in 254 s, read as the pack records. Validation Pack [VM-3](../validation/VM-3.md) rewritten.
- 2026-11-05: VM-3 verified. v0.2.6 pinned, which notes a register row whose pointer covers the whole of a long file, and the build-notes test holds the baseline of fifteen such entries from the old suite, failing on a new one and on one fixed, linked to TD-119. `test_vm3_05` pins the decision spelling pattern, LATTICE's since `vyvid.toml` declares it, and the two odd spellings the old pattern also read, one plan line with a space and one review document with a non-breaking hyphen, are written with the hyphen. Every test the removed-test table names was checked to exist by a script. The VTB exceptions accepted, with the reason in the pack. `mise run check` run at v0.2.6 trusted and every one of its 3,447 lines read by the agent, exit 0 in 191.66 s, every task passing, as the pack records task by task. Validation Pack [VM-3](../validation/VM-3.md) corrected.
- 2026-11-05: VM-4 built. The seven board tasks run `vyd board`, `vyd work` and `vyd here` through `tools/vyd.py`, the `work` hook check is `vyd work check --staged`, and the post-merge hook regenerates the regions by `vyd work`, each skipping with a note where `vyd` is missing. The nine work-board tests rewritten over `vyd` on a probe project declared through `VYVID_CONFIG`, since an untrusted `vyvid.toml` writes nothing, every message read from `vyd` first and no scenario weakened. The old and new board outputs agree on this checkout but the four cells VM-1 recorded, INDEX.md regenerates byte for byte, ROADMAP.md with three of those cells and one generated sentence. `tools/work_board.py`, `tools/work_migrate.py` and their 58 tests removed, CAP-103 and CAP-104 re-pointed, TD-143 and TD-144 reworded as `vyd work roadmap`'s behaviours, for Вивід's side. One Вивід finding: under a git hook's `GIT_DIR`, `vyd` takes the status folder for the repository root and `vyd work check --staged` crashes, reproduced from a shell with `GIT_DIR` set, so `tools/vyd.py` runs `vyd` without `GIT_DIR` and a test holds it. `mise run check` run after the slice, exit 0 in 194.10 s, its 3,447 lines compared line by line with VM-3's log, which was read whole, and differing only in `check:hooks` at 46 passed, `check:identifiers` at 855 files, and timings. Validation Pack [VM-4](../validation/VM-4.md).
