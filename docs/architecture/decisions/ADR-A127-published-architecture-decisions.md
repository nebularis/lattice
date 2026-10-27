<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A127: Published architecture decisions

**Status:** Accepted, 2026-10-17
**Date:** 2026-10-16
**Supersedes:** none
**Related:** [ADR-A77](ADR-A77-repository-topology-and-documentation-governance.md) (documentation governance),
[ADR-A117](ADR-A117-agent-guidance-and-skill-library.md) (agent guidance),
[ADR-A121](ADR-A121-repository-catalogue.md) (the repository catalogue and its site sections),
[ADR-A126](ADR-A126-literate-specification-layout-and-grammar.md) (README layout)
**Unit:** [`improved-ontology-documentation`](../../developer/plans/improved-ontology-documentation.md)

## Context

LATTICE's user-facing documents are its layer READMEs, the ontology documents generated from them, and
the pages of its GitHub Pages site. They cite ADRs to explain why a layer is shaped as it is. An ADR in turn
often cites the sketch, plan or status record it came from. Measured on 2026-10-16, 59 of the 110 ADR files
link to such working documents, 129 times in all, so a reader who follows a citation from a README lands in
the team's working papers.

The site has the same problem in another form. GitHub Pages builds the whole of `docs/` with no workflow,
so about 330 working documents, and every ADR including those only proposed, are published as unstyled
pages with no title, beside about twenty pages written for readers.

## Decision

1. **A further status, Published.** An ADR is Proposed, then Accepted, then Published, and may later be
   Superseded. The maintainer publishes an ADR, as the maintainer accepts one, and its Status line records
   the date.
2. **What publication requires.**
   - The ADR's references to working documents sit only in a closing section headed "Provenance". Its
     context, decision and consequences read completely without them.
   - The architecture documents the decision affects describe it, so a reader of the architecture does not
     need the ADR to know what was decided.
   - It is listed in `docs/architecture/published-architecture-decisions.md`.
3. **The list is generated.** `published-architecture-decisions.md` is generated from the ADRs' Status
   lines, with each decision's number, title, publication date and the architecture documents that describe
   it, and a check keeps it current. It is the Decisions section of the site. A superseded decision stays on
   it, marked, with a link to its successor.
4. **User-facing documents cite only published decisions, and never a working document.** Working documents
   are sketches, plans, status records, review requests, Validation Packs, notes and the developer index.
   User-facing documents are layer READMEs, generated ontology documents, the pages of the site's sections,
   and published ADRs outside their Provenance section. The rule covers text, links and HTML comments,
   including hidden blocks, since a reader of a file on GitHub sees all of them. Durable guidance kept under
   `docs/developer/`, such as the getting-started guide, may be linked. A check reads every line of every
   user-facing document.
5. **The site publishes declared sections only.** The site's sections are declared in the repository
   catalogue (ADR-A121), each with a title, a page, a layout, an order and its sources. Working documents are
   excluded in `_config.yml`, and an ADR that is not published carries Jekyll's `published: false`. Durable
   developer guidance forms a Contributing section. Each page in a section takes its layout through Jekyll's
   `defaults`, so no section page is bare. A source outside `docs/`, such as a layer README, is copied into
   the site's includes by a `mise` task, tracked and checked, since Jekyll cannot include files above its
   source directory.

## Consequences

- `AGENTS.md` states the rule of decision 4 for agents, and the decision catalogue's convention lists the
  new status.
- Working documents stay public in the repository. Only the site stops serving them, so links to them from
  outside the repository break, and the check keeps the site's own pages from linking to them.
- Accepted ADRs leave the site until they are published. Publishing them is a pass over each, moving its
  references to working documents into a Provenance section and checking that the architecture documents
  describe it. Until a module's README is migrated to the layout of ADR-A126, and until that pass has
  published the decisions it cites, the check reports a citation of an Accepted ADR rather than failing on it.
- Release notes and the Overview and Detailed Design sections of a README cite decisions under the same rule.
- Copying sources into `docs/` duplicates them in git. A Pages workflow that assembles the site from the
  catalogue at deploy time would remove the copies, and needs the repository's Pages source changed by the
  maintainer. It is recorded as technical debt.

## Addendum, 2026-10-19: what a published decision may cite

Agreed by the maintainer. Decision 4 holds for layer READMEs, generated ontology documents and the site's
pages, which cite only published decisions. A published decision may also cite an accepted one, since a
decision record often builds on decisions not yet published. Such a citation links the accepted ADR on
GitHub, `https://github.com/nebularis/lattice/blob/main/docs/architecture/decisions/...`, because the site
hides it. A published decision never cites a proposed one. Without this, publishing the ten decisions
Eligibility's README cites would have meant publishing the 74 they cite in turn. `mise run
check:published-decisions` checks the rule and keeps the list current.

The status line of a published decision reads `**Status:** Published, YYYY-MM-DD. Accepted YYYY-MM-DD.`, and
one published and then superseded reads `**Status:** Superseded by ADR-An. Published YYYY-MM-DD.` A layer
README counts as a document that describes a decision.

## Provenance

Raised by the maintainer on 2026-10-16 during the
[`improved-ontology-documentation` plan](../../developer/plans/improved-ontology-documentation.md)'s design
discussion (decisions OD-D21, OD-D22, OD-D25 and OD-D28 to OD-D31, slices DOC1 to DOC3, technical debt
TD-50).
