<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# The LATTICE tutorial - Status

**Unit ID:** `lattice-tutorial`
**Status:** building 2026-11-06.
**Last updated:** 2026-11-06
**Plan:** [lattice-tutorial.md](../plans/lattice-tutorial.md)

## Position

| Slice | Deliverable | State | Blocked on |
|---|---|---|---|
| TUT-0 | the page, its layout, the home page links and `check:tutorial-snippets` | verified 2026-10-14 |  |
| TUT-1 | chapters 0 to 3 | built 2026-10-15 |  |
| TUT-2 | chapters 4 to 6 | built 2026-10-15 |  |
| TUT-3 | chapters 7 to 9 | built 2026-10-16 |  |
| TUT-4 | chapters 10 to 13 | built 2026-10-16 | the maintainer's end-to-end reading (TUT4-05) |
| TUT-5 | the tutorial refreshed onto `main`: excerpts, the site's rules, Ledger in chapter 10. [Validation Pack](../validation/TUT-5.md) | built 2026-11-05, building 2026-11-05 |  |
| TUT-6 | the Configuration Studio guide's groundwork: the studio run, the routes in and out tested, the page, layout and site section, the worked sample and its test, the screenshot task (plan §9) | building 2026-11-06 |  |
| TUT-7 | the guide's modules 1 to 4 | briefed 2026-11-06 | TUT-6 |
| TUT-8 | the guide's modules 5, 6 and 11 | briefed 2026-11-06 | TUT-6 |
| TUT-9 | the guide's modules 7 to 10 | briefed 2026-11-06 | TUT-6 |
| TUT-10 | the guide's modules 12, 13 and the quick reference | briefed 2026-11-06 | TUT-6 |

## Current position

Every question is answered (TUT-D1 to TUT-D5, TUT-Q1 to TUT-Q4, plan §2 and §8). TUT-0 to TUT-4 are committed on `tutorial/guide` and pushed, without the AI disclosure trailer, which the squash merge into `main` carries. On 2026-11-05 `main` was merged into the branch at the maintainer's request, the first step of TUT-5.

**Next action, for the maintainer:** review TUT-5 ([Validation Pack](../validation/TUT-5.md)), commit it, and read the tutorial end to end (TUT4-05), the unit's acceptance. Then the squash merge into `main`, with the AI disclosure trailer, and the Configuration Studio guide on its own branch (plan §9, TUT-D6 to TUT-D11).

## History

- 2026-10-14: at our request, the branch `tutorial/guide` was created from `main` (level with
  `origin/main`). The maintainer chose the audience (a data architect new to ontologies), a
  read-only tutorial with a hands-on version deferred, sources from each substrate's own
  `examples/` folder and from `ontology/applied/`, one page with chapters as includes, and copied
  excerpts verified by a check task. Plan written.
- 2026-10-14: the maintainer accepted every leaning, TUT-Q1 to TUT-Q4. TUT-Q3 turned out moot,
  since Rouge 3.30.0 has a Turtle lexer. TUT-0 authored, not yet run.
- 2026-10-14: previewing TUT-0 on Windows found `bootstrap:jekyll` ran only `cd docs` under
  `cmd.exe` and reported success. Rewritten as a `run` array with `dir`, which behaves the same on
  Windows, macOS and Linux. Run after the fix, it reaches `bundle install`, which on Windows needs
  MSYS2 for native gems. The per-platform C toolchain is now in getting-started.md §1, and both
  lessons in the toolchain skill's environment lessons.
- 2026-10-14: TUT-0 verified on Windows at the maintainer's request, after MSYS2 was installed.
  Every check passed (Validation Pack, Results). Fixed during verification: the sticky top bar
  covering a chapter heading after a contents link. `docs/Gemfile.lock` gained the Windows
  platform. One existing `check:agent-guidance` test fails on Windows without Developer Mode,
  unrelated to this unit and flagged as separate work.
- 2026-10-14: the maintainer committed TUT-0 as `2c99ead`, not yet pushed. The commit has no
  `Generated-by` and `AI-Content` trailer yet.
- 2026-10-14: TUT-1 written, chapters 0 to 3. `check:tutorial-snippets` caught one excerpt that did
  not match its source, now corrected. The Mermaid diagram, the Turtle highlighting and the 375 px
  layout checked in a served preview. Awaiting the maintainer's reading.
- 2026-10-15: the maintainer committed TUT-1 as `834d9e4`, without the disclosure trailer. TUT-2
  written, chapters 4 to 6. Every excerpt matched on the first run. The diagrams, highlighting and
  375 px layout checked in a served preview.
- 2026-10-16: the maintainer committed TUT-2 as `fe608d7`, without the disclosure trailer. TUT-3
  written, chapters 7 to 9. Every excerpt matched on the first run. The state diagram failed to
  render because `default` is reserved in Mermaid, fixed by renaming the state.
- 2026-10-16: the maintainer committed TUT-3 as `1f9a171`, without the disclosure trailer. TUT-4
  written, chapters 10 to 13. Every excerpt matched on the first run. Chapter 3's Governance row
  corrected, since `ontology/governance/` holds only an empty README.
- 2026-11-02 to 2026-11-05: `main` gained the Configuration Studio, MORK's new compilers, the Ledger layer and new rules for the site (user-facing documents cite no working document, Markdown is not hard-wrapped, a page is a declared site section). Against `main` the tutorial has 11 excerpt and link findings. The maintainer chose the recommended plan: refresh the tutorial onto `main` (TUT-5), then a separate do-along Studio guide.
- 2026-11-05: `main` (`73b31c2c`) merged into `tutorial/guide` at the maintainer's request. Conflicts resolved: `docs/developer/INDEX.md` taken from `main` and regenerated, `mise.toml` takes `main`'s check list with `check:tutorial-snippets` added, `docs/Gemfile.lock` takes `main`'s with the Windows platform added by `bundle lock --add-platform x64-mingw-ucrt`. This record moved onto the board grammar. The tutorial check now reads its root and chapters from the catalogue, and the tutorial is declared as site section 2. The merge commit skipped `import-guard` and `writing`, whose failures are in `main`'s own files (TUT-5 Validation Pack).
- 2026-11-05: the maintainer accepted every recommendation for the Configuration Studio guide (plan §9, TUT-D6 to TUT-D11) and passed on the lead developer's answers. TUT-5 built: eight excerpts re-copied, chapter 10 rewritten on Ledger, Ledger in the layer map, the page's reference to the plan removed, every chapter unwrapped. Every check in its Validation Pack passed.
- 2026-11-06: `tutorial/studio-guide` created from `tutorial/guide` at the maintainer's request, so the guide can go ahead while the tutorial waits for its reading. TUT-6 marked building.
- 2026-11-06: TUT-6 in part. The studio run on this laptop with `mise run studio:up` (Yarn's first install needed `COREPACK_ENABLE_DOWNLOAD_PROMPT=0`, and a RabbitMQ download reset by the remote was replaced by the archive with the pinned SHA-256 from another checkout). A persistence compile of the Lending sample succeeded, the Policies sample compiled to JOLT and XSLT and ran its JSON example, and a scratch mapping took Foundation's keys out to schema.org through `tools/mork_rdf`, which also showed a naive outbound mapping can write a sensitive key's value into an IRI. Raised for the lead developer: PDD-20 (where site images live), PDD-21 (the worked sample as a studio sample) and TD-149 (RML for an XML scheme written with JSONPath). Built: `docs/studio-guide.md`, its layout `docs/_layouts/studio-guide.html` with styles for keys and numbered steps, fourteen placeholder modules in `docs/_includes/studio-guide/`, the `studio-guide` site section at order 11, and the home page links. The plan reference in the tutorial layout's CSS comment removed, since the layout is published. `check:site-sections`, `check:catalogue` and `check:published-decisions` passed, and the page served with its 14 modules and no horizontal scroll at 375 px.
- 2026-11-06: `main` (`1f6784f6`), with the Вивід migration, merged into `tutorial/studio-guide` at the maintainer's request. Conflicts resolved: `mise.toml` takes `main`'s check list with `check:tutorial-snippets` added, `technical-debt.md` keeps both sides' rows, `ROADMAP.md` takes `main`'s generated regions and section 10 with the tutorial's item added, and `environment-lessons.md`, which `main` moved into the Вивід tools domain, is deleted. Its two Windows lessons (multi-line `run` strings on `cmd.exe`, MSYS2 for Ruby gems) are not yet in the domain. Board rows added for TUT-7 to TUT-10, which the plan names and the new identifier check reports.
