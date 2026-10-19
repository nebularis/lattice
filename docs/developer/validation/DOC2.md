<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: DOC2, site sections

**Unit:** [`improved-ontology-documentation`](../status/improved-ontology-documentation.md), slice DOC2
([plan](../plans/improved-ontology-documentation.md#doc2-site-sections)).
**Implements:** OD-D29 to OD-D31, with OD-D37 and TD-50, TD-53.
**Built autonomously**, at the maintainer's request of 2026-10-19, in a sub-agent's worktree cut from
`docs/literate-v2` at `ef9c62cf`. The decisions taken alone are listed below.

## Invariant

The site publishes its declared sections only. A section page shows every source its catalogue entry lists, a copy
of a source outside `docs/` is never stale, and no working document, unpublished decision or unused directory
is in the built site.

## What changed

- `repository-catalogue.md`, a "Site" section and nine `[[site]]` entries: Home, Field Guide, Theory,
  Layer specifications, Architecture, Decisions, Operations, Glossary and Contributing.
  **Tutorial is left out**, since it lives on another branch. It takes order 2 when it arrives (DOC3).
- `tools/lattice_repo_catalogue.py`. A `site` key with its own validation (`_site`, `_site_problems`), added to
  `check` and the dump. Nothing else in the schema changed.
- `tools/site_sections.py`. `build` copies sources outside `docs/` into `docs/_includes/<section>/` (mirroring
  the path, wrapped in `raw`) and writes a generated `defaults` region into `docs/_config.yml`. `check` finds a
  stale or missing copy, a copy of nothing, stale defaults, and a page that does not show a source.
- `mise.toml`. `build:site-sections` and `check:site-sections`, the latter part of `check`.
- `docs/_config.yml`. Exclusions for `developer`, `diagrams`, `operator`, `security`, `traceability`, the decisions
  README, the stray notes below, and the generated `defaults`. DOC1's ADR exclusion and include region are intact.
- New pages `layer-specifications.md`, `operations.md`, `contribute.md` and `architecture/index.md`. Layer
  specifications shows Eligibility's README, the one migrated layer.
- `tools/sources_check.py` reads each section's page (a working document fails) and its sources in `docs/` (reported).
- `index.html` and `book.html` link the published decisions page. `book.html` links the four unpublished ADRs it
  cites at `main` on GitHub. `getting-started.md` loses its developer-index bullet and links two guides absolutely.
- `.build/site` was committed by DOC1 by mistake. It is untracked and ignored.
- TD-60 and TD-61.

## Decisions taken alone, for the maintainer

1. **Defaults need no front matter.** Built here, `defaults` applies to a `.md` page without front matter
   (the optional front matter plugin renders it), so the section pages carry none. It does not apply to `.html`
   pages, so Home and Field Guide have layout `none` and keep their own HTML.
2. **The contributing page is `contribute.md`.** The plugin skips a file named `contributing.md`.
3. **Exclude whole directories, show their files in a page.** `developer`, `operator` and
   `operational-guidance.md` are excluded, and Operations and Contributing show their files with
   `include_relative`, which reads excluded files. The inverse default of TD-53 for `developer/`.
4. **The decisions README is excluded.** The Decisions section's page is the generated list, which needs no
   edit, and `defaults` gives it its layout. The two links to the directory now point at it.
5. **Contributing holds three guides**, getting started, WSL and the Protege walkthrough. The developer guide and
   the formal methods lifecycle guide name working documents (TD-60), so they stay off the site until cleaned.
6. **Layer specifications holds migrated READMEs only**, since the rest cite working documents (591 reports).
7. **Architecture lists 35 documents**, all of `docs/architecture/` but the notes below.
8. **No tutorial spine authoring note exists** in `docs/` on this branch, so none was repointed.
9. **Stray working notes**, excluded and left in place. Recommendation for each:
   `docs/proposed-readme-updates.md` (investigative draft, retire),
   `docs/architecture/updated-plan-ammendment.md` and `updated-plan-remediation.md` (an old plan, move to
   `docs/developer/notes/`), `docs/architecture/Architecture Review.md` (a review, move to
   `docs/developer/review/`). `repository-topology-migration.md` is a record under ADR-A77 and stays published,
   with its JSON excluded. `GOVERNANCE.md` and `validation-and-test-plan.md` are in no section and still
   published. Add them to a section or exclude them.

## Test cases

In `tools/test_site_sections.py`.

| ID | Given / When / Then | Level | +/- |
|---|---|---|---|
| DOC2-T1 | the repository catalogue / load / ordered sections, every page and source exists | L1 | + |
| DOC2-T2 | an unknown key, a missing title, a repeated name, a page outside docs/, a text order, a bad name, an upward source / load / each refused | L1 | − |
| DOC2-T3 | a section whose page, layout and source are missing / problems / each reported | L1 | − |
| DOC2-T4 | a missing, a changed and an orphan copy / check, copy task, check / fails, then passes | L3 | +/− |
| DOC2-T5 | stale defaults, and a page not showing a source / check / each fails, and defaults keep the rest of the config | L3 | +/− |
| DOC2-T6 | the repository / check / copies and defaults current | L4 | + |

## Commands

```bash
mise run check:site-sections
mise run check:catalogue
mise run check:published-decisions
mise run check:agent-guidance
mise run check:deny-terms
mise run bootstrap:jekyll
cd docs && mise exec -- bundle exec jekyll build -q -d ../.build/site
```

## Results

2026-10-19, run while building:

- `check:site-sections`, `check:catalogue`, `check:published-decisions` (0 failures, 591 reports),
  `check:agent-guidance` and `check:deny-terms` pass. 6 new tests, and the catalogue, published decisions and
  full sweep tests (121) pass.
- **The site:** 836 files before, 96 after. `.build/site/architecture/decisions/` holds 12 files, the published
  ADRs. No `developer/`, `diagrams/`, `operator/`, `security/`, `traceability/`, no stray note and no
  decisions README. `theory`, `layer-specifications`, `operations`, `contribute`, `glossary`,
  `architecture/index` and `architecture/published-architecture-decisions` are built with their layout (the
  topbar is present) and title. Home and Field Guide keep their own HTML.
- The `.md` twins of rendered pages are still copied, as before.

## Deliberate non-coverage

- Relative links inside shown sources (TD-61), and the working-document references in 11 architecture pages (TD-60).
- The Tutorial section, and the Field Guide review (DOC3).
- The full `mise run check`, which needs Java and Node. Only the checks above ran.
- A Pages workflow replacing the copies (TD-50).
