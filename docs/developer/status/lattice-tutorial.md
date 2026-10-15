<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# The LATTICE tutorial - Status

**Unit ID:** `lattice-tutorial`
**Status:** 🔨 In progress. TUT-0 committed (`2c99ead`). TUT-1 written and checked, awaiting the maintainer's reading
**Last updated:** 2026-10-14
**Plan:** [lattice-tutorial.md](../plans/lattice-tutorial.md)
**Branch:** `tutorial/guide`, local, created from `main` 2026-10-14. The maintainer pushes it

## Current position

Every question is answered (TUT-D1 to TUT-D5, TUT-Q1 to TUT-Q4, plan §2 and §8). TUT-0, the
skeleton, is committed on `tutorial/guide` (`2c99ead`), verified on Windows (its Validation Pack, Results). It holds the page, its layout, 14 placeholder
chapters, the home page links, and `check:tutorial-snippets` with its tests, wired into `check`.
Its [Validation Pack](../validation/TUT-0.md) lists the one command and the preview steps.

TUT-1, chapters 0 to 3, is written, and its [Validation Pack](../validation/TUT-1.md) results are in.

**Next action, for the maintainer:** read chapters 0 to 3 as the intended reader (TUT1-05), since
they set the voice and depth for TUT-2 to TUT-4, then commit TUT-1. Before pushing, add the AI
disclosure trailer GENAI_CONTRIBUTION.md requires to `2c99ead` and to the TUT-1 commit.

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
