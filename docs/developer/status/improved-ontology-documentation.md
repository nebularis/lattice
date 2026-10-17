<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Improved Ontology Documentation: Status

**Unit ID:** `improved-ontology-documentation` (absorbs `repository-catalogue`)
**Status:** In progress. OD0 accepted. OD1 passed. RC1 authored, not yet run.
**Last updated:** 2026-10-16
**Branch:** `docs/literate-v2`
**Plan:** [improved-ontology-documentation.md](../plans/improved-ontology-documentation.md)
**Sketches:** [improved-ontology-documentation.md](../sketches/improved-ontology-documentation.md),
[repository-catalogue.md](../sketches/repository-catalogue.md)

## Current position

The plan was rewritten on 2026-10-16 after two days of design discussion. It now covers three things: one
README layout whose normative sections compile to Turtle and SHACL from a markdown grammar, the repository
catalogue with each module's entry in its README, and a sources discipline for user-facing documents built
on published ADRs. Decisions OD-D1 to OD-D24 and the answers to RC-Q1 to RC-Q8 are in the plan. No code or
ontology file has changed.

## Next action

1. The maintainer reviews the [RC1 Validation Pack](../validation/RC1.md), including its eight implementation
   choices, and runs its commands. RC1 is authored, not yet run.
2. Then RC2, which moves the tools onto the reader, and OD2 and OD3 on the extractor.

## Slices

| Slice | State | Blocked on |
|---|---|---|
| OD0 ADRs, the AGENTS.md rule, the conventions document | accepted 2026-10-17, committed, [Validation Pack](../validation/OD0.md) | |
| RC1 catalogue and reader | authored 2026-10-17, not yet run, [Validation Pack](../validation/RC1.md) | the maintainer's run and review |
| RC2 consumers use the reader | planned | RC1 |
| RC3 roots, AGENTS.md table, bypass scan | planned | RC2 |
| OD1 scanner and markers | passed 2026-10-17, choices agreed, [Validation Pack](../validation/OD1.md) | the maintainer's merge |
| OD2 sections 1 and 2 | planned | OD1 |
| OD3 section 6 to OWL | planned | OD1 |
| OD4 section 6 to SHACL | planned | OD3 |
| OD5 generated regions | planned | OD3 |
| OD6 Eligibility pilot | planned | RC2, OD2, OD4, OD5 |
| OD7 Vocabulary | planned | OD6 |
| OD8 onward, one per layer | planned | OD7, and for Foundation and Party their part of TD-16 |
| DOC1 published decisions | planned | OD0 |
| DOC2 site sections | planned | DOC1, RC1 |
| DOC3 tutorial and Field Guide review | planned | DOC2, `lattice-tutorial` merged |
| RC4 downstream extension | planned | RC3 |
| RC5 package promotion | planned | RC4 |
| RC6 XML catalogue folded in | planned | RC5, a new ADR on ADR-A88 |

## Open questions

None.

## Coordination with other units

| Unit | Relationship |
|---|---|
| `computable-contract-substrate` | C6 merged on 2026-10-04 without markers, so the Instrument README migrates here. Still planned and touching migrated READMEs: C9b3 and C9b4 (Eligibility), C8a, C9c and C9d (Instrument), C16c (Party). Whichever lands second adopts the other's format. HQ-6a.2, in flight, changes no README |
| `repository-catalogue` | Absorbed. Its sketch's questions are answered in this plan |
| TD-16 | Vocabulary reconciled in OD7. Foundation and Party wait for their part |
| TD-20 | Runs when convenient. A migrated README states each term once |
| TD-50 | Added by this unit: move the site assembly to a Pages workflow later |
| `lattice-tutorial` | On branch `tutorial/guide`. Its pages join the Tutorial section in DOC2, its `<!-- source: ... -->` marker joins the conventions document, and DOC3 reviews it against the Field Guide once it merges |
| `formal-methods-track-e` | The Formalisation section carries its `isabelle-spec` blocks. `check_formal_freshness.py` moves to the reader in RC2 |

## Log

- 2026-10-14: branch `docs/literate-v2` and its worktree created from `main`. Sketch reviewed, first plan
  and this record written. Measured: prose, annotation and Turtle sizes per layer, and README-only commits
  since 2026-09-15 (36 of 84).
- 2026-10-15: the maintainer walked through the Vocabulary and Eligibility READMEs and proposed a fixed
  layout with section 6 compiled from a markdown grammar. Decisions on tracking, layout, generated views,
  OWL and SHACL, `output-file`, examples, Dublin Core, alignments and first regeneration. Measured: about
  2,700 axiom statements in the literate layers' spec and vocab files, of which 28 fall outside simple
  tables, and per layer the OWL cardinality restrictions against SHACL counts (76 OWL only, 176 SHACL only).
- 2026-10-15: an OWL-only escape for the 76, markers reduced to exclude, hide and `output-file`, extra
  annotations as labels, contributors by IRI with no legal name without permission, and section 3 as the
  module's catalogue entry, with the catalogue built in the same tranche.
- 2026-10-16: Manchester syntax for class expressions, after finding eight expressions beyond simple
  restrictions, one of which SPC's own comment already writes in Manchester syntax. RC-Q1 option C and
  RC-Q2 TOML.
- 2026-10-16: RC-Q3 (C), RC-Q4 (A), RC-Q5 (C, per-worktree `.venv`, pinnable downstream), RC-Q6 and RC-Q7
  (yes), RC-Q8 (`repository-catalogue.md`). Plain text with tag links, sorted output, sections by title with
  a numeral warning, "None." for empty subsections, Canonicalisation and Formalisation as optional normative
  sections, Release Notes mandatory, no top-level sections of a layer's own. The sources rule for
  user-facing documents and a published decisions ADR added, with slices DOC1 and DOC2, and RC6 to fold in
  the XML catalogue. CCS C6 found already merged (2026-10-04), so Instrument migrates here. Plan rewritten.
- 2026-10-16: OD-Q14 answered (a), recorded as OD-D25. For OD-Q15 the site was surveyed: GitHub Pages
  builds all of `docs/` with no workflow, so the 111 ADR files and 334 developer documents are live as
  unstyled pages with no title, beside eight styled entry pages. The branch `tutorial/guide` (unit
  `lattice-tutorial`, TUT-0 to TUT-4) adds a tutorial page with chapters as includes and an excerpt check
  using `<!-- source: ... -->` comments.
- 2026-10-16: OD-Q16 answered: release notes checked, not extracted (OD-D26), no slice references in notes,
  and fixed section numbers with "Not applicable." for an absent optional section (OD-D27).
- 2026-10-16: OD-Q15 answered: durable developer guidance may be linked (OD-D28), site sections declared in the
  root catalogue and copied into `docs/` (OD-D29, with TD-50 for a Pages workflow later), declared sections only
  with a Contributing section (OD-D30), and the section list with a tutorial and Field Guide review after the
  tutorial merges (OD-D31, DOC3). Every design question is answered.
- 2026-10-16: OD-D28 amended at the maintainer's request: the sources check reads HTML comments and hidden
  blocks too. The one comment on any branch that cites a working document, the tutorial spine's authoring note,
  is repointed in DOC2.
- 2026-10-16: OD0 authored. ADR-A121, ADR-A126 and ADR-A127 drafted as Proposed and listed in the catalogue
  (numbers checked free on every local and remote branch), the AGENTS.md rule of OD-D21 and OD-D28 added, and
  `docs/architecture/literate-specifications.md` started. Six drafting choices are listed in the Validation
  Pack for the maintainer. Links and the boundaries search checked while drafting. `build:agent-guidance`
  not yet run.
- 2026-10-17: the maintainer agreed the six drafting choices and accepted ADR-A121, ADR-A126 and ADR-A127,
  and committed OD0. Their Status lines and the catalogue rows now say Accepted, 2026-10-17. ADR-A120 and
  ADR-A01 gained their addenda, the catalogue's convention lists the Published status, and the AGENTS.md rule
  no longer marks ADR-A127 Proposed. The Copilot copy needs `build:agent-guidance` again.
- 2026-10-17: OD1 authored, not yet run. A scan of all 22 module READMEs first showed no nested tagged
  fence, no tagged fence inside a comment and no marker-like comment, so the new scanner leaves every
  extraction unchanged (OD1-T1 tests it). `tools/test_literate_extract.py`, which no task ran, joins
  `check:ontology-catalog`. Three implementation choices are listed in the Validation Pack.
- 2026-10-17: the maintainer ran OD1's tests, which pass, and agreed its three implementation choices. No
  adversarial probe was run at the gate. RC1 started.
- 2026-10-17: RC1 authored, not yet run. `repository-catalogue.md` at the root lists 19 modules, each README
  holds its entry, and `tools/lattice_repo_catalogue.py` reads and checks them (`check:catalogue`, in
  `check`). The extraction contracts were taken from what each README generates, by the extractor's
  `plan()` in memory, and the substrate imports from `import_guard.ALLOWED`, and tests hold both. Eight
  implementation choices and two deviations are in the Validation Pack.
