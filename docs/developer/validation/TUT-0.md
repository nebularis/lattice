<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: TUT-0, the tutorial skeleton and its excerpt check

**Unit:** [`lattice-tutorial`](../status/lattice-tutorial.md)
**Plan:** [lattice-tutorial.md](../plans/lattice-tutorial.md) §5, decisions TUT-D4, TUT-D5, TUT-Q1 to TUT-Q3

## Invariant

The tutorial is one page of the GitHub Pages site, built from `docs/` with the pinned
`github-pages` gem, and every Turtle excerpt and repository link in it agrees with the checkout.
An excerpt that no longer matches its source, a Turtle block that names no source, and a link to a
path that does not exist each fail `check:tutorial-snippets`, which runs in `mise run check`.

## Test cases

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| TUT0-01 | an excerpt whose lines are in its source / checked / no finding | L1 | + |
| TUT0-02 | an excerpt with one changed line / checked / one finding, "no longer matches" | L1 | - |
| TUT0-03 | an excerpt naming a missing file / checked / one finding, "does not exist" | L1 | - |
| TUT0-04 | an excerpt naming `../x.ttl` / checked / one finding, "outside the repository" | L1 | - |
| TUT0-05 | a `turtle` block with no source comment / checked / one finding | L1 | - |
| TUT0-06 | a `bash` block with no source comment / checked / no finding | L1 | + |
| TUT0-07 | an excerpt elided with `# …`, parts in source order / checked / no finding | L1 | + |
| TUT0-08 | elided parts in reverse order / checked / one finding naming part 2 | L1 | - |
| TUT0-09 | a `blob/main` and a `tree/main` link to present paths / checked / no finding, two links counted | L1 | + |
| TUT0-10 | a link to a missing path / checked / one finding | L1 | - |
| TUT0-11 | the real chapters, all placeholders / checked / `OK 0 excerpts and 0 repository links` | L0 | + |
| TUT0-12 | the site / built and served / `tutorial.html` shows the hero, a 14-entry contents grid and 14 placeholder chapters, each contents entry jumps to its chapter, the home page shows a Tutorial link in the top bar and a tutorial card under Docs | L6, by hand | + |

TUT0-01 to TUT0-10 are `tools/test_tutorial_snippets.py`. TUT0-11 is the script run on the
checkout. TUT0-12 is by hand, since no test builds the site.

## One command

```bash
mise run check:tutorial-snippets
```

Pass: the script prints `OK 0 excerpts and 0 repository links match the checkout`, then pytest
reports `10 passed`.

For TUT0-12, from the repository root, once Ruby is installed for the site:

```bash
mise run bootstrap:jekyll
```

```bash
mise run serve:jekyll
```

Then open `http://127.0.0.1:4000/tutorial.html` and the home page.

## Artefacts to inspect

- `docs/tutorial.md`, the page, and `docs/_includes/tutorial/`, its 14 chapter files
- `docs/_layouts/tutorial.html`, derived from `docs/_layouts/theory.html`. The differences are the
  brand, the contents link in the top bar, the chapter list, and the Rouge token styles
- `docs/index.html`, the two links
- `tools/tutorial_snippets.py` and `tools/test_tutorial_snippets.py`
- `mise.toml`, the `check:tutorial-snippets` task and its place in `check`
- `docs/developer/developer-guide.md` §5, the new row

## Deliberate non-coverage

- Whether Turtle is highlighted cannot be seen until a chapter holds an excerpt. TUT-1 checks it in
  the preview. That Rouge 3.30.0 has a `turtle` lexer was confirmed from its source at tag `v3.30.0`.
- Mermaid rendering is the theory layout's, unchanged. The first diagram arrives in TUT-1
  (chapter 3).

## Results

Run 2026-10-14 on Windows 11, at the maintainer's request.

| Check | Result |
|---|---|
| `mise run bootstrap:jekyll` | passed after the fix below. `Bundle complete! 2 Gemfile dependencies, 98 gems now installed` |
| `mise run check:tutorial-snippets` | passed. `OK 0 excerpts and 0 repository links match the checkout`, `10 passed` (TUT0-01 to TUT0-11) |
| `bundle exec jekyll build` | passed. Liquid warnings only in existing Validation Packs that quote mustache templates, none in the tutorial |
| TUT0-12, served and inspected | passed. Hero, 14-entry contents grid, 14 chapters with ids `why` to `next`, a contents link lands on its chapter, the home page has the top-bar link and the Docs card. No horizontal scroll at 375 px |
| Turtle highlighting | Rouge 3.30.0, from the bundle, lexes `turtle` into the classes `kd`, `nn`, `nl`, `k`, `n`, `s`, `c1`, `p`. The layout styles all but `n`, which keeps the code colour |
| `mise run check:agent-guidance` | the guidance check passed, 0 problems. One test, `test_link_replaces_its_own_links_and_refuses_others`, failed with WinError 1314, since creating a symlink on Windows needs Developer Mode. It fails on `main` the same way, and is unrelated to this slice |

Found and fixed during verification:

- `bootstrap:jekyll` ran only its first line, `cd docs`, under `cmd.exe`, and reported success.
  Rewritten as a `run` array with `dir`, the same on every platform.
- A contents link put its chapter heading under the sticky top bar. The layout now sets
  `scroll-margin-top` on every element with an id. The theory layout has the same defect, left as it is.
- `bundle install` on Windows added the `x64-mingw-ucrt` platform to `docs/Gemfile.lock`, beside the
  macOS and Linux platforms already there. Kept, so Windows resolves the same gem versions.

Not run on macOS or Linux.

## Adversarial probe

Not yet run.
