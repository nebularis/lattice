<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: DOC2b, working documents out of published pages

**Unit:** [`improved-ontology-documentation`](../status/improved-ontology-documentation.md), slice DOC2b.
**Closes:** TD-60. **Built autonomously** on 2026-10-20 by a Sonnet sub-agent in this checkout, and reviewed here.

## Invariant

No page the site publishes refers to a working document by path or link. The developer guide and the formal
methods lifecycle guide join the Contributing section.

## What changed

- **Twelve architecture documents**, from `identity-minting-specification.md` to `ux-design.md`. 27 references to
  plans, sketches, notes and status records became plain text or were dropped, with no Provenance section added.
  `insurml-alignment-vision.md` lost its Plan, Sketches and Analysis header lines.
- **`developer-guide.md` and `formal-methods-lifecycle.md`**, 4 references each, and both guides are added to the
  Contributing section through the catalogue's site sources and `docs/contribute.md`.
- **The stray notes, as the maintainer decided:**
  - `docs/proposed-readme-updates.md` is retired.
  - `updated-plan-ammendment.md` moves to `docs/developer/sketches/`, marked TBD.
  - `updated-plan-remediation.md` moves to `docs/developer/notes/`.
  - `Architecture Review.md` moves to `docs/developer/review/`.
  - Every path naming them is updated, and their site exclusions are dropped.
- **ADR-A129 published**, and the 0.18.0 release notes cite it.
- TD-60 removed. TD-62 records the citations left by name only.

## Decisions taken alone, for the maintainer

1. **References removed rather than moved to Provenance**, since only a published ADR has a Provenance section
   under ADR-A127.
2. **Mentions by name only stay**, for example `insurml-alignment-vision.md`'s "comparison §n" and "integration
   §n" citations. They carry design content, and the sources check reads paths and links. TD-62 records them.

## Results

2026-10-20: the sources check shows 0 failures and no working-document report outside `ontology/`.
`check:site-sections`, `check:published-decisions`, `check:agent-guidance` and `check:deny-terms` pass. The site
builds with both guides on the Contributing page. `mise run check:full-sweep` passes all 17 checks.
