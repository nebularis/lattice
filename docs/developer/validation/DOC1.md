<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: DOC1, published decisions

**Unit:** [`improved-ontology-documentation`](../status/improved-ontology-documentation.md), slice DOC1
([plan](../plans/improved-ontology-documentation.md#doc1-published-decisions)).
**Implements:** [ADR-A127](../../architecture/decisions/ADR-A127-published-architecture-decisions.md) decisions 1
to 4, and decision 5's hiding of unpublished ADRs, with OD-D37 to OD-D39 and OD-D47 to OD-D50.
**Built autonomously**, at the maintainer's request of 2026-10-19. The publication pass over twelve ADRs was done
by a second developer working in the same checkout, and reviewed here. The decisions taken alone are listed
below.

## Invariant

Every user-facing document cites only published decisions and refers to no working document. A migrated
README and the files it generates fail the check on either. A README not yet migrated is reported. A
published ADR may cite an accepted one, by an absolute link, and never a proposed one. Every published ADR has
a Provenance section, a Described in line and `published: true` front matter, and is on the generated list.
The site shows published ADRs only.

## What changed

- `tools/published_decisions.py`. Reads every ADR's status, Described in line and front matter, writes
  `docs/architecture/published-architecture-decisions.md`, and checks the list is current and every published
  ADR meets ADR-A127 decision 2.
- `tools/sources_check.py`. Reads every line of every user-facing document: the module READMEs the catalogue
  lists, the files each generates, published ADRs outside Provenance, and the list.
- `mise.toml`. `build:published-decisions`, and `check:published-decisions`, which runs both checks and the
  tests and is part of `mise run check` and the full sweep.
- `docs/_config.yml`. Every ADR is excluded from the site, and a region `build:published-decisions` writes
  includes each published one by file name (decision 7).
- **The publication pass (OD-D38, OD-D50).** The twelve ADRs Eligibility's README cites, now that ELC's release
  note cites ADR-A03 and ADR-A05 too: ADR-A03, A05, A06, A85, A87, A90, A91, A100, A103, A105, A121 and A126. Each gained front matter, the published status line, a Described
  in line and a Provenance section holding its references to working documents. Links to unpublished ADRs are
  absolute. The decisions index marks them Published.
- ADR-A127 gains an addendum for OD-D47 and OD-D49.

## Decisions taken alone, for the maintainer

1. **An absolute link to an unpublished ADR points at `main`**, not at a release tag. OD-D47 said "the release
   tag", but an ADR belongs to no ontology document's release, and a tag would point at the decision as it
   stood before it was published.
2. **A working document is recognised by its path**, `developer/sketches/`, `plans/`, `status/`, `reviews/`,
   `validation/`, `notes/` or `developer/INDEX.md`. Question and slice IDs, such as "HQ6a-Q1", are not detected.
   The publication pass removed them by reading each ADR.
3. **A published-then-superseded ADR** reads `Superseded by ADR-An. Published YYYY-MM-DD.` and stays on the
   list, marked. No ADR is in that state yet.
4. **A README not yet migrated is reported, never failed**, for working documents as well as citations, since
   385 such reports exist today. They become failures as each layer migrates.
5. **A citation of an ADR with no file is reported**, never failed. Three exist today in ADRs that are not
   published (A101, A108 and A109).
6. **The list's Described in links** are rewritten relative to the list's own directory.
7. **Exclude and include, not a `published: false` default** (OD-D37 as built). The local site build showed the
   default hides nothing. An ADR without front matter is copied as a static `.md` file and also rendered by the
   optional front matter plugin, and neither reads `defaults`. So `_config.yml` excludes `architecture/
   decisions/ADR-*` and includes each published ADR by file name, the form Jekyll 3.10's entry filter matches
   inside an excluded glob, and restates Jekyll's own exclusions, which setting `exclude` replaces. Published
   ADRs keep `published: true` front matter, so each is rendered as a page.
8. **Accepted dates.** A03, A05 and A06 have no recorded acceptance date, so they take the date of the commit
   that added them, 2026-09-17, followed across a later move.

## Test cases

In `tools/test_published_decisions.py`.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| DOC1-T1 | a published, an accepted and a proposed ADR / build, check, edit the list, check / one row, passes, then stale | L3 | +/− |
| DOC1-T2 | a published ADR with no Described in, no Provenance and false front matter, an accepted one with true front matter, a malformed published status / problems / each reported | L1 | − |
| DOC1-T3 | a working-document link in a migrated README, in a published ADR's Provenance, in its body / check / the README and the body fail, Provenance passes | L3 | +/− |
| DOC1-T4 | an unpublished citation in a migrated and in an unmigrated README / check / a failure, then a report | L3 | +/− |
| DOC1-T5 | a published ADR citing an accepted ADR by name, by absolute link, by relative link, and a proposed one / check / the first two pass, the last two fail | L3 | +/− |
| DOC1-T6 | the repository / check / no failure, no problem, and the site's defaults hide unpublished ADRs | L4 | + |

## Commands

Run from the repository root. A pass is each exiting 0.

```bash
mise run check:published-decisions
```

```bash
mise run bootstrap:jekyll
```

```bash
cd docs && mise exec -- bundle exec jekyll build -d ../.build/site
```

## Results

2026-10-19, run while building, from this worktree:

- **`check:published-decisions`:** 0 failures, 355 reports for READMEs not yet migrated (385 before the twelve were published), 6 tests passed.
- **The site build:** `mise run bootstrap:jekyll`, then the build above, 2026-10-19. `.build/site/architecture/decisions/` holds
  the twelve published ADRs and the directory index only, where before the change it held 218 files. The list
  page `published-architecture-decisions.html` is built.

## Deliberate non-coverage

- Site sections, layouts and excluding working documents from the site (DOC2, TD-53).
- Publishing ADRs no migrated README cites. They are published as each layer migrates.
- Question and slice IDs in published ADRs, which the check does not detect (decision 2).
- The decisions index page on the site links every ADR, so its links to unpublished ones are broken there.
  DOC2 gives the site its sections and layouts.
