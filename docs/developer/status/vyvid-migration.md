<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# LATTICE adopts Вивід: status

**Unit ID:** `vyvid-migration`
**Plan:** [vyvid-migration.md](../plans/vyvid-migration.md)
**Sketch:** [vyvid-migration.md](../sketches/vyvid-migration.md)
**Mode:** default. Write, then hand off, unless the maintainer says otherwise.
**Status:** building 2026-11-05. VM-0 and VM-1 built and verified, ADR-A152 accepted, the binding trusted. VM-2 building, with every other branch paused until the unit merges.

## Position

| Slice | Deliverable | State | Blocked on |
|---|---|---|---|
| VM-0 | the sketch rewritten, the plan, this record, the INDEX.md region | built 2026-11-05 |  |
| VM-1 | the binding, `bootstrap:vyvid`, the comparison | built 2026-11-05, building 2026-11-05, briefed 2026-11-05 |  |
| VM-2 | the index tasks and hooks over `vyd`, AGENTS.md's index section, the addenda | building 2026-11-05 |  |
| VM-3 | the quanta and owners extractor, the tests against Вивід, the deletions | planned | VM-2 |
| VM-4 | the board tasks and the `work` check over `vyd`, the old tools removed | planned | VM-3 |
| VM-5 | the fifteen composed skills, the coverage proven, the citations and pointers | planned | VM-4 |
| VM-6 | the moves, the page at the old path, TD-2 cleared | planned | VM-5 |

## Next action

VM-2 is building. The next trust point is 2, VM-3's extractor entry, and no edit to `vyvid.toml` is made before it.

## Trust points

`vyd trust` is the maintainer's to run in a terminal, and any edit to `vyvid.toml` lapses it (plan, decision 13), so the edits are batched and trust is asked at these points only.

| Point | After | What waits on it |
|---|---|---|
| 1 | VM-1's handoff, `vyvid.toml` as the patch gave it plus the question family marked `removable` | `vyd context`, `test_vm1_08`, and `vyd install --project` in VM-5. Everything else in VM-1's comparison ran untrusted, since an untrusted project gives knowledge alone |
| 2 | VM-3's `[[project.extractors]]` entry for quanta and owners | VM-3's tests against the store |

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
