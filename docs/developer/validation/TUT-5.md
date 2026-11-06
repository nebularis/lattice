<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: TUT-5, the tutorial refreshed onto `main`

**Unit:** [`lattice-tutorial`](../status/lattice-tutorial.md)
**Plan:** [lattice-tutorial.md](../plans/lattice-tutorial.md)

## Invariant

The tutorial on `tutorial/guide` builds and checks against `main` as it stands: every excerpt and repository link matches the checkout, the page is a declared site section, it cites no working document, and it follows the writing rules `main` now enforces.

## Step 1: `main` merged into the branch, 2026-11-05

`main` at `73b31c2c` merged at the maintainer's request. Conflicts resolved:

| File | Resolution |
|---|---|
| `docs/developer/INDEX.md` | `main`'s, the generated work board, rebuilt with `mise run build:work` |
| `mise.toml` | `main`'s check list with `check:tutorial-snippets` added. The branch's Windows-safe `bootstrap:jekyll` kept |
| `docs/Gemfile.lock` | `main`'s, with the Windows platform added by `bundle lock --add-platform x64-mingw-ucrt`. No version changes |

Made to satisfy `main`'s checks in the same commit:

- `tools/tutorial_snippets.py` finds the root with the catalogue reader and its chapters as the source of the site's `tutorial` section, rather than building either path itself (ADR-A121 decision 5). Its tests pass their own chapter folder and add one test that reads the section from the catalogue. `mise exec -- python -m pytest tools/test_tutorial_snippets.py -q` gave `11 passed`.
- `repository-catalogue.md` declares the `tutorial` site section at order 2, which the catalogue reserved for it, and `mise run build:site-sections` wrote its defaults into `docs/_config.yml`.
- The status record moved onto the work board's grammar, with slices TUT-0 to TUT-5.

### Hook bypass

The merge commit was made with `LATTICE_HOOKS_SKIP=import-guard,writing`. The other eleven checks of the `pre-commit` hook passed, catalogue and site sections among them. A merge makes the hook check every file the merge changes, so it ran over `main`'s own files. The two skipped checks fail on content this branch does not change.

| Check | Failure | Why it is not this branch's |
|---|---|---|
| `import-guard` | `UnicodeDecodeError` reading a standalone module's Turtle with the platform's default encoding (cp1252 on Windows) | it reads only files under `ontology/`, and the branch changes none of them |
| `writing` | 33 semicolons in prose | every one is in a file `main` wrote. None is in a file the branch changes |

Hard-wrapped lines are reported as warnings, including in the branch's own chapters. TUT-5's later steps unwrap the tutorial's files.

## Step 2: the tutorial refreshed, 2026-11-05

- Eight excerpts re-copied from their current sources by a script, never retyped: the classification header (release 0.6.0, imports at 0.21.0), `fnd:Versioned` in the keys example (ADR-A141), the money space with its unit contract's identity, two Eligibility conditions without `elg:compatibilityOperation`, the renamed cure-expiry trigger, and the storm surge and hurricane, now from `peril/vocab/peril-vocab.ttl` since the example no longer declares them.
- Prose updated where it named what changed: `fnd:Versioned` in chapters 2 and 4, chapter 3's versions on the one release (ADR-A129), chapter 12's intensity measure and module states.
- Chapter 10 rewritten on Ledger's revolving facility, with the account definition as released and postings marked as designed and not yet released, and Capacity's moved files.
- Ledger added to chapter 3's layer map and to chapter 13's table.
- The page's comment no longer names the plan, a working document (ADR-A127).
- Every chapter unwrapped, a paragraph or list entry to a line. `tools/writing_rules.py` skips `docs/_includes/`, so this was checked with a script of our own.

## Results

Run 2026-11-05 on Windows 11.

| Check | Result |
|---|---|
| `mise exec -- python tools/tutorial_snippets.py` | `OK 49 excerpts and 35 repository links match the checkout` |
| `mise exec -- python -m pytest tools/test_tutorial_snippets.py -q` | `11 passed` |
| `mise run check:catalogue` | passed |
| `mise run check:site-sections` | passed, after `build:site-sections` |
| `mise run check:published-decisions` | `sources: 0 failure(s)` |
| `bundle exec jekyll build` | built, 14 chapters, 49 Turtle blocks highlighted, no placeholder |
| served, in the browser | three Mermaid diagrams, 13, 5 and 6 nodes, no syntax error. No horizontal scroll at 375 px |

Not run: `mise run check` as a whole, and the hook checks `import-guard` and `writing`, which fail on `main`'s own files (step 1).
