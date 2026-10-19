<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Improved Ontology Documentation: Status

**Unit ID:** `improved-ontology-documentation` (absorbs `repository-catalogue`)
**Status:** In progress. OD0 accepted. OD1, RC1, RC2, OD2 and OD3 done. OD4 and OD5 built autonomously and committed locally, not pushed.
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

1. The maintainer answers REL-Q2a and lets MC1, OD7, VER1, DOC2 and OD-REL run autonomously (OD-D62). MC1, OD7
   and DOC2 need no further answer. VER1 needs REL-Q2a.
2. The [release bundles sketch](../sketches/release-bundles.md), BUN-Q1 to BUN-Q7, decides what ships with a
   release beyond the RDF and where it goes.

**Known inconsistency on this branch (OD-D43).** Migrated layers' documents change without new version IRIs,
so `check:ontology-versioning` reports unbumped changes, and importers stay pinned to the old versions. This is
deliberate. The release slice OD-REL resolves it once, before the merge into `main`.

## Slices

| Slice | State | Blocked on |
|---|---|---|
| OD0 ADRs, the AGENTS.md rule, the conventions document | accepted 2026-10-17, committed, [Validation Pack](../validation/OD0.md) | |
| RC1 catalogue and reader | committed 2026-10-17, tests pass, choices agreed 2026-10-18, [Validation Pack](../validation/RC1.md) | |
| RC2 consumers use the reader | passed and committed 2026-10-18, [Validation Pack](../validation/RC2.md) | |
| RC3 roots, AGENTS.md table, bypass scan | approved 2026-10-19 after the `reaches` audit, committed locally, [Validation Pack](../validation/RC3.md) | |
| OD1 scanner and markers | passed 2026-10-17, choices agreed, [Validation Pack](../validation/OD1.md) | the maintainer's merge |
| OD2 sections 1 to 3 | built autonomously 2026-10-18, committed locally (`8947e696`), [Validation Pack](../validation/OD2.md) | |
| OD3 section 6 to OWL | built autonomously 2026-10-18, committed locally, [Validation Pack](../validation/OD3.md) | |
| OD4 section 6 to SHACL | built autonomously 2026-10-18, committed locally, [Validation Pack](../validation/OD4.md) | the maintainer's review of six decisions taken alone |
| OD5 generated regions | built autonomously 2026-10-18, committed locally, [Validation Pack](../validation/OD5.md) | the maintainer's review of six decisions taken alone |
| OD6 Eligibility pilot | built autonomously 2026-10-18, committed locally, [Validation Pack](../validation/OD6.md) | the maintainer's review of seven decisions, 32 definitions and two changed tests |
| OD7 Vocabulary | planned | OD6 |
| OD8 onward, one per layer | planned | OD7, and for Foundation and Party their part of TD-16 |
| DOC1 published decisions | approved 2026-10-19, committed locally, [Validation Pack](../validation/DOC1.md) | |
| DOC2 site sections | planned | DOC1, RC1 |
| DOC3 tutorial and Field Guide review | planned | DOC2, `lattice-tutorial` merged |
| RC4 downstream extension | planned | RC3 |
| RC5 package promotion | planned | RC4 |
| RC6 XML catalogue folded in | planned | RC5, a new ADR on ADR-A88 |
| ELC composition operation | approved 2026-10-19, committed locally, [Validation Pack](../validation/ELC.md) | |
| MC1 migration check labels | briefed 2026-10-19 | |
| VER1 one release for the substrate | briefed 2026-10-19 | REL-Q2a |
| OD-REL first release, 0.18.0 | planned | every migration on the branch |

## Open questions

- **REL-Q2a. Do the standalone modules join the substrate's release?** MORK's `Mork.ttl`, Surface's `surface.ttl`
  and Persistence's `persistent-foundation.ttl` import Foundation (Surface also Quantification and Vocabulary),
  and MORK's `Executable.ttl` names Eligibility terms without importing Eligibility. SPC depends on nothing.
- **BUN-Q1 to BUN-Q7**, in the [release bundles sketch](../sketches/release-bundles.md).

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
- 2026-10-17: the maintainer committed RC1 (`be612df5`). Its results and choices are not yet recorded.
- 2026-10-17: RC2 authored, not yet run. The extractor reads shape targets from the catalogue and `--shapes`
  is removed. The import guard, the versioning check and the freshness check read their constants from it.
  Every extractor command for people or CI drops `--shapes` and goes through `mise exec`, CI's two Surface
  steps included. RC1-T4 now compares the catalogue with ADR-A01's order written out in the test.
- 2026-10-18: the maintainer merged `main` into the branch (`74989f04`, with `mise.toml` taking main's
  `check:ontology-catalog` plus our two test modules) and ran RC2's checks: the import guard, versioning,
  freshness and catalogue checks pass, and `check:ontology-catalog` passes with 974 tests and 7 skips (the
  reasoning tests without their jar). RC1's tests pass in the same run.
- 2026-10-18: RC1-C1 to RC1-C8 and RC2-C2 agreed as implemented, RC2-C1 changed to option (c): the extractor
  finds the catalogue above its README, from any working directory. Implemented with RC2-T7. On RC1-C5, a
  migrated README holds its entry in section 3, which OD2's layout check will enforce. RC2-C2's move to
  option (b), every extraction checked against its entry, is planned in RC4.
- 2026-10-18: the maintainer committed and pushed RC2, and asked for OD2 and OD3 to be built without stopping
  for decisions, with local commits only. OD2 built: `tools/literate_grammar.py` compiles sections 1 and 2 of
  a README in the layout into each document's opening, and the layout check requires the catalogue entry in
  section 3. Eight decisions taken alone are listed in its Validation Pack. Its tests, the catalogue tests,
  the per-layer extraction tests and the freshness check were run and pass.
- 2026-10-18: OD3 built: the Manchester parser and the section 6 compiler in `tools/literate_grammar.py`. Ten
  decisions taken alone are listed in its Validation Pack. The grammar states two of SPC's axioms exactly as
  SPC's file does (OD3-T7). Its tests, the extractor and catalogue tests, the per-layer extraction tests, and
  the freshness and catalogue checks were run and pass. Committed locally, not pushed.
- 2026-10-18: the maintainer answered OD2's and OD3's decisions. All agreed but OD2's decision 5, changed to
  order a document's blocks by their text and refuse prefixes in a migrated README's blocks (OD2-Q5, option
  b), with a later move to a version check on graph content (TD-51). Multilingual support recorded as PDD-10,
  and OD3's unsupported forms in the plan's unplanned backlog. The maintainer ran every test suite and
  all pass. The change and its tests (OD2-T10, OD2-T11) pass and are committed locally.
- 2026-10-18: the maintainer agreed OD4's four leanings and asked for OD4 and OD5 to be built autonomously,
  with local commits. OD4 built: restriction rows checked in SHACL become `shapes/structural.ttl`, generated
  whole, and rows for one property and message share a property shape. The grammar states Eligibility's
  `EligibilityDecisionShape` exactly as its file does (OD4-T7). Six decisions taken alone are listed in its
  Validation Pack. Its tests and the neighbouring suites pass.
- 2026-10-18: OD5 built: the Axiom Index and the Overview's class diagram are generated from the compiled
  section 6 into required regions of the README, rewritten by extraction and reported as drift by `--check`.
  The generated diagram renders under mermaid 10.9.1. Six decisions taken alone are listed in its Validation
  Pack. Its tests and the neighbouring suites pass. Committed locally, not pushed.
- 2026-10-18: OD4's decisions 2 to 6 and OD5's decisions 1 and 3 to 6 agreed. OD4's decision 1 (merging rows
  into one property shape) and OD5's decision 2 (the README as an output) agreed after explanation. Every OD4
  and OD5 decision is settled.
- 2026-10-18: the planning round answered (OD-D32 to OD-D40): merge before the pilot and continue on this branch,
  a reusable migration check, enumeration in the grammar for OWL enumerated classes and SHACL `sh:in`, individuals
  with extra statements whole in 6.6 blocks, the maintainer named as creator with permission for the display name,
  unpublished ADRs hidden by a Jekyll default, the first publication pass limited to what Eligibility cites, a
  Described in field, and AGENTS.md's table generated with its columns unchanged. TD-52 (ADR metadata as a table)
  and TD-53 (most of `docs/` unpublished by default, for a website sketch) added. Briefs for OD6, DOC1 and RC3
  written into the plan.
- 2026-10-18: RC3-Q2 answered (b), recorded as OD-D41: the bypass scan's exceptions in a file beside the reader,
  with one technical debt row giving their count. Every planning question is answered.
- 2026-10-18: OD6 started. Enumeration in the grammar and the migration check written, with their tests, which
  pass. Two findings stopped the migration for a decision: 32 of Eligibility's 52 terms have no definition, and
  any migration changes a layer's graphs (Dublin Core in the header), so each needs a version that cascades
  through 11 documents in 5 modules. Answered: definitions are drafted and reviewed (OD-D42), and versions are
  left inconsistent on this branch until one release slice, OD-REL, bumps and re-pins everything before the merge
  (OD-D43). The maintainer asked for a sketch on changing how imports pin, and authorised OD6 to continue
  autonomously with local commits.
- 2026-10-18: OD6 finished. Eligibility's README is in the layout, and the migration check against `dab1c790`
  passes with 40 reconciled differences, the 32 drafted definitions and each document's Dublin Core. No axiom
  or shape changed. `check_formal_freshness.py` now reads only the Isabelle blocks, and OD1-T1 and RC1-T3 were
  adjusted for a migrated README. Two gaps found and left as the README's open issues: L1 to L8 name no
  register, and 14 individuals have no definition.

- 2026-10-18: OD6 reviewed. The definitions agreed with three changes, applied and reconciled. L1 to L8's
  register goes to OD-REL. OD6-Q7 opened on renaming `elg:CompatibilityOperation`.
- 2026-10-19: OD6-Q7 answered. `elg:CompatibilityOperation` becomes `elg:CompositionOperation`, declared on
  admission profiles only (OD-D44), and `elg:DimensionConsistent` is retired with `elg:E6` (OD-D45). Slice ELC
  briefed, to land before OD-REL.
- 2026-10-19: ELC-Q1 and Q2, DOC1-Q4 to Q7 and RC3-Q3 to Q5 answered (OD-D46 to OD-D53). The maintainer
  authorised ELC, DOC1 and RC3 to be built autonomously, committed locally and not pushed.
- 2026-10-19: ELC built. `elg:CompositionOperation` on profiles only, `elg:DimensionConsistent` and `elg:E6`
  removed, 42 graphs rewritten and checked graph to graph, and Instrument's warranty carve-back typed as the
  profile it is. The migration check now escapes line breaks, and TD-55 records its whole-file blank node
  labels. RC3 runs in a separate worktree.
- 2026-10-19: DOC1 built. The published decisions list and the sources check run in `mise run check`, the
  twelve ADRs Eligibility cites are published under the maintainer's advance approval (OD-D50), and the site
  shows only those. The local site build showed Jekyll's `published: false` default hides nothing, so the site
  excludes ADRs and includes each published one by name.
- 2026-10-19: RC3 built in a separate worktree and cherry-picked onto this branch, without the main checkout's own
  commit it was cut from. Its bypass scan found DOC1's new list tool building `docs/` paths, which now asks the
  reader for the architecture area instead. ADR-A121's addendum keeps its slice reference in Provenance.

- 2026-10-19: ELC, DOC1 and RC3 approved. RC3's `reaches` audited and now checked by RC3-T17. Two entries
  corrected, and TD-56 records SPC's pipeline script writing into a missing directory.
- 2026-10-19: next slices proposed (MC1, OD7, DOC2, OD-REL). NX-Q1 answered (a), the branch is cut after OD-REL.
  The import pinning checks were run, and the maintainer asked to rethink versioning first. The
  [release model sketch](../sketches/ontology-release-model.md) proposes one release for every ontology,
  REL-Q1 to REL-Q6 open.
- 2026-10-19: REL-Q1 to REL-Q6 and NX-Q3 to NX-Q5 answered (OD-D54 to OD-D62). One release for the substrate,
  starting at 0.18.0, with the data class of every change in its notes. Briefs written for MC1, OD7, VER1, DOC2
  and OD-REL. The check REL-Q2 asked for found three standalone modules depending on the substrate (REL-Q2a). The
  release bundles sketch opened BUN-Q1 to BUN-Q7.
