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

## Remaining TUT-5 steps

- the 11 excerpt and link findings `mise run check:tutorial-snippets` reports against `main`
- the tutorial's files unwrapped, and its references to working documents removed
- chapter 10 rewritten on Ledger's revolving facility, chapter 3's versioning on the shared release
- `fnd:Version` written as `fnd:Versioned` where the text names it

## Results

Step 1 only, above. The rest to be filled at verification.
