<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: LATTICE adopts Вивід

**Unit ID:** `vyvid-migration`
**Unit type:** multi-slice unit, a binding, tasks and hooks over an installed tool, deletions, composed skills and two moves
**Prefix:** VM
**Sketch:** [vyvid-migration.md](../sketches/vyvid-migration.md), the facts, the table of what moves and the answered questions
**Status record:** [vyvid-migration.md](../status/vyvid-migration.md)
**ADR:** drafted in VM-2 as Proposed, at the next free number
**Status:** planned 2026-11-05. VM-0 built. VM-1 briefed, waiting on the maintainer's go-ahead, with every other branch paused from then until the unit merges.

## Scope

LATTICE's knowledge index and work board tooling become a configuration of [Вивід](https://github.com/nebularis/vyvid), installed on the machine as `vyd` and pinned, plus a thin layer for what is LATTICE's own, its architectural quanta and the catalogue's owners. The `mise` task names agents use stay and run `vyd` underneath. The skills are composed from Вивід's domains plus LATTICE's additions and committed. The triple-store record and the thirty query-writing standards move to the `vyvid-triple-stores` domain, with a LATTICE page at the record's old path. Nothing LATTICE has is removed before its replacement is proven on this checkout.

The starting point is the patch Вивід's side handed over on 2026-11-05, 35 files, with eleven coverage maps beside it. VM-1 takes its binding files and VM-5 its skills.

Out of scope: a claims store, moving any register that is LATTICE's own, a code path for a checkout without `vyd`, proving Windows (Вивід's VYD-14, after this unit), and the private rules as a domain (VM-Q6).

## Dependencies

Вивід at `v0.2.1`, whose VYD-16 to VYD-20 and VYD-22 this unit relies on. [ADR-A134](../../architecture/decisions/ADR-A134-knowledge-index-and-design-shape-vocabulary.md) for what the index reads, [ADR-A133](../../architecture/decisions/ADR-A133-git-hooks.md) for the hooks' moments, [ADR-A151](../../architecture/decisions/ADR-A151-the-work-board.md) for the board, [ADR-A117](../../architecture/decisions/ADR-A117-agent-guidance-and-skill-library.md) for AGENTS.md and the skills, [ADR-A29](../../architecture/decisions/ADR-A29-repository-toolchain-and-environment-boundary.md) for `mise` as the one entry point, and WB-7 done, which it is on `main`.

## Decisions taken

| # | Decision | Date |
|---|---|---|
| 1 | the binding is both a `vyvid.toml` in the repository, public, and an entry in the maintainer's user configuration for the paths one machine knows (VM-Q1) | 2026-11-05 |
| 2 | the whole unit runs now, slice after slice on this branch, with every other branch paused until it merges (VM-Q2) | 2026-11-05 |
| 3 | Вивід is a `uv` tool pinned to `v0.2.1` in `mise.toml` and installed by `bootstrap`. Every hook and task that calls `vyd` skips with a message where `vyd` is missing or fails, and never blocks a commit. `vyd check skills` saying it did not run is not a failure (VM-Q3) | 2026-11-05 |
| 4 | `check:knowledge` proves the whole knowledge base consistent, and every one of LATTICE's knowledge tests passes against the store `vyd build` writes before any test or module is deleted (VM-Q4) | 2026-11-05 |
| 5 | the board moves to Вивід with no loss of function. INDEX.md stays the generated register. The old tools go once `vyd board`, `vyd work` and `vyd here` agree with them on this checkout and across every branch (VM-Q5) | 2026-11-05 |
| 6 | the private rules become a domain later, after this unit (VM-Q6) | 2026-11-05 |
| 7 | the skills are composed from the domains plus LATTICE's additions by `vyd install --project` and committed, each opening on the index-first header, and an old skill is removed only once `vyd check skills --from` it with its coverage map passes | 2026-11-05 |
| 8 | `mise` stays the one entry point (ADR-A29). Every `vyd` call an agent is told to make is a `mise` task under the name it has today, and `mise run vyd -- <args>` passes the rest through | 2026-11-05 |
| 9 | the switch is recorded as an ADR drafted Proposed in VM-2, with dated addenda on ADR-A134 and ADR-A151 pointing at it rather than rewriting their text | 2026-11-05 |
| 10 | the moves come last, after `vyd move check --ref` on every branch, and the page at the record's old path is written before the copy goes | 2026-11-05 |
| 11 | the 201 register rows whose Pointer is a skill section are re-pointed by the coverage maps, mechanically, in VM-5 | 2026-11-05 |
| 12 | the identifier exceptions baseline stays one file, read by both checks while both run | 2026-11-05 |

## Slices

Each slice is built on this branch in default mode unless the maintainer says otherwise, and handed off with its Validation Pack. A slice's pass is measured on this checkout and, where it reads branches, on every branch. Estimates are in tokens.

| Slice | Delivers | Validation | Estimate |
|---|---|---|---|
| **VM-0** | the sketch rewritten against Вивід 0.2.1, this plan, the status record, the INDEX.md region | links resolve, the writing rules hold, the hooks pass | done |
| **VM-1** | **bind.** From the patch, `vyvid.toml`, `.claude/settings.json` and `.github/hooks/vyvid.json` for the reminder hook, and the additions under `.vyvid/`. The user-configuration entry (decision 1). `uv` in `mise.toml`'s tools and a `bootstrap:vyvid` task installing Вивід at `v0.2.1`, wired into `bootstrap`. `vyd trust`, `vyd build`. The comparison, every difference written in the status record: `vyd find` against `graph:ask` on the bake-off rerun on the merged `main` with `mise run bench:lattice` in Вивід's checkout, `vyd check identifiers` against `check:identifiers`, including the 105 unresolved mentions of the question family on a clone and the `ABC-Q` examples in the domain text that the family reads as mentions, `vyd board` against `work:board`, and `vyd work build --check` against `build:work --check`. The ten skills stay as they are | `tools/test_vyvid_binding.py`: `vyvid.toml` parses and names every family `identifiers.py` defines today, `vyd context` prints LATTICE's contract in this checkout, and `bootstrap:vyvid` is a no-op where `vyd` is at the pinned version. The comparison's differences in the status record, each with its disposition | 60k |
| **VM-2** | **switch.** `graph:ask`, `build:knowledge` and `check:identifiers` as tasks over `vyd find`, `read`, `node`, `reaches`, `exists`, `sparql`, `misses`, `gap`, `close`, `vyd build` and `vyd check identifiers`, the identifiers hook check over `vyd check identifiers`, the post-merge hook running `vyd build`, each skipping with a message where `vyd` is missing or fails (decision 3). `mise run vyd -- <args>` for the rest. AGENTS.md's "Asking the knowledge index" cut to what is LATTICE's, opening on the install and `vyd context`, and `build:agent-guidance`. The ADR, Proposed, and the addenda (decision 9) | `tools/test_hooks.py`: the post-merge hook and the identifiers check skip with a message, exit zero and name `mise run bootstrap` where `vyd` is absent, and the identifiers check fails a staged mention nothing defines where `vyd` is present. `mise run graph:ask -- find` on three bake-off questions returns the same top five as before the switch | 90k |
| **VM-3** | **the thin layer.** `tools/knowledge/quanta.py` wrapped as a `[[project.extractors]]` command, reading the JSON request, writing `quads.nq` and `result.json`, declaring the catalogue's units so an `Owner` cell becomes an edge. Every knowledge test re-pointed at the store `vyd build` writes and passing, and `check:knowledge` running them (decision 4). Then the removal of `extract.py`, `ask.py`, `identifiers.py`, `facets.py`, `anchors.py` and `embed.py` with the tests Вивід's suite already holds, `knowledge.ttl` reduced to LATTICE's additions, and `facets.md` kept for the values the general scope lacks, named from VM-1's comparison | `check:knowledge` passes against Вивід's store before and after the deletions, and the quanta and owner tests among the ones kept. `mise run graph:ask -- find <a quantum's purpose>` returns the quantum. `mise run check` passes | 80k |
| **VM-4** | **the board.** `work:board`, `build:work`, `build:roadmap`, `work:here`, `work:rename`, `work:normalise` and `work:adopt` as tasks over `vyd board`, `vyd work build`, `vyd work roadmap`, `vyd here` and the three migrations, the `work` hook check over `vyd work check --staged`, the post-merge regeneration over `vyd work build` and `vyd work roadmap`, each skipping with a message where `vyd` is missing or fails. `tools/work_board.py`, `tools/work_migrate.py` and their 58 tests removed once each pair agrees (decision 5) | the old and new `board --all --commits` outputs equal on this checkout across every local and remote branch, `build:work --check` and `vyd work build --check` agree on a staged stale region, `tools/test_hooks.py`'s eight `work` cases pass over the new check, and INDEX.md and ROADMAP.md regenerate byte for byte | 40k |
| **VM-5** | **the skills.** The patch's fifteen composed skills regenerated by `vyd install --project` against the domains of the day. For each of the ten old skills, `vyd check skills --from <old> --map <map>` passing before it is removed, the one line the lifecycle map marks for review placed by hand. AGENTS.md's skills table, the 94 citations of `lattice-toolchain` and `lattice-triple-stores` in 30 files renamed, an accepted ADR among them taking a dated addendum, the 201 register pointers into skill files re-pointed by the maps (decision 11), `build:agent-guidance`, and `vyd check skills` as a hook check that skips where `vyd` is missing | `vyd check skills` passes with no `--from`, and with `--from` and the map for each old skill. `check:agent-guidance` passes. `build:knowledge` reads every re-pointed register cell, its notes read in full. `check:identifiers` passes | 60k |
| **VM-6** | **the moves.** `vyd move check --ref` on every branch, with every difference read. LATTICE's copy of `docs/architecture/triple-store-discovery.md` replaced by a page at the same path saying what each finding means for LATTICE, keyed to the domain's identifiers and pinned to a tag of the domain, the thirty query-writing standards removed from `standards.md`, every mention resolving by the declared moves, the writing rules and the general facet values moved to the general scope and removed here, the bake-off rerun, and TD-2 cleared in Вивід's register (decision 10) | `check:identifiers` passes with every `TSD-nn` and `STD-026` to `STD-054` and `STD-279` resolving to the domain, the eleven published pages that link the record reach the page at the old path, `check:links` passes, and the bake-off scores hit@5 and MRR within 0.01 of VM-1's | 80k |

## Open

- Вивід's `vyd check skills` exits non-zero when it did not run. Its side says 2. Run unbound in this checkout on 2026-11-05 it said no project claims the folder and exited 1. VM-1 records which exit means "did not run" and the hook check in VM-5 treats that one as a skip.
- The 105 unresolved question mentions `vyd check identifiers` reports on a clone, against LATTICE's own check. VM-1 lists them, and each is an exception, a `defined_only` pattern or a change to the domain's examples.
- TD-2 is Вивід's debt, not LATTICE's, and is cleared there in VM-6.

## Done when

`mise run check` passes with `tools/knowledge/` holding only the extractor, its wrapper and the tests that stay, and no `tools/work_board.py` or `tools/work_migrate.py`. `check:knowledge` proves the knowledge base consistent against Вивід's store. `vyd check skills` passes with and without `--from`. `vyd check identifiers`, `vyd board` and `vyd work build --check` stand where the old tools stood, through the same `mise` task names, and skip cleanly where `vyd` is absent. No copy of the moved content remains, and the page at the record's old path resolves. The bake-off on the merged `main` matches VM-1's. AGENTS.md's index section is LATTICE's alone. The ADR is drafted and the roadmap's sections refreshed.
