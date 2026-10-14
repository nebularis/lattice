<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Plan: The LATTICE tutorial

**Unit ID:** `lattice-tutorial` (TUT)
**Unit type:** multi-slice unit, validation gate per slice
**Status:** Planned 2026-10-14. Every question answered (TUT-D1 to TUT-D5, TUT-Q1 to TUT-Q4). TUT-0 in progress
**Status record:** [lattice-tutorial.md](../status/lattice-tutorial.md)
**Branch:** `tutorial/guide`, created from `main` 2026-10-14 at the maintainer's request
**ADRs:** none needed (TUT-D4 adds no new kind of directory)
**Depends on:** nothing unmerged. Every source the tutorial cites is on `main`

## 1. Goal and acceptance

A read-only tutorial, published with the project's GitHub Pages site from `docs/`, that takes a
reader who knows data architecture but has little exposure to ontologies to the point where they can
read LATTICE's layers and examples, and judge how to build on LATTICE in a project of their own.

The unit is accepted when:

1. `docs/tutorial.md` builds with the site's own Jekyll (`mise run serve:jekyll`) and renders every
   chapter, every Mermaid diagram and every Turtle excerpt
2. every Turtle excerpt matches its source file, checked by `mise run check:tutorial-snippets`
3. every link to a repository file resolves on GitHub
4. the site's home page links to the tutorial
5. a reader of the intended audience (the maintainer) has read it end to end and found no chapter
   that assumes knowledge an earlier chapter did not give

## 2. Recorded decisions

Recorded 2026-10-14, from the maintainer's answers.

| ID | Decision |
|---|---|
| TUT-D1 | **Audience.** A data architect with little exposure to ontologies, who wants to use LATTICE in another project. The tutorial explains each ontology idea through its nearest data-architecture counterpart, and says where the counterpart misleads |
| TUT-D2 | **Read-only.** The reader reads and does not run anything. A hands-on version is deferred to its own later unit (§7) |
| TUT-D3 | **Sources.** Excerpts come from each substrate's own `examples/` folder (for example `ontology/instrument/examples/`) and from the modules under `ontology/applied/`. The files directly in `ontology/examples/` are not used |
| TUT-D4 | **One page, chapters as includes.** The pattern `docs/theory.md` already uses. A page `docs/tutorial.md` includes one file per chapter from `docs/_includes/tutorial/`, under a layout `docs/_layouts/tutorial.html` |
| TUT-D5 | **Excerpts are copied and checked.** Each Turtle excerpt is copied into its chapter, and a check task confirms every excerpt still appears in its source file (option (b) of the options put to the maintainer) |

## 3. The running example

Most substrate example folders already model one loan facility agreement, with a borrower, a
syndicate of lenders and a leverage covenant. The tutorial follows it through every layer, so
each chapter adds one idea to a model the reader already knows.

| Layer | Source | What it shows |
|---|---|---|
| Foundation | `foundation/examples/keys.ttl` | the facility's real-world keys, one identity across two versions |
| Wording | `wording/examples/facility-agreement.ttl` | the agreement's text as structure, with values supplied per facility |
| Instrument | `instrument/examples/facility-agreement.ttl`, `facility-definitions.ttl`, `facility-parameters.ttl` | the legal relations of the form, and of one signed facility |
| Quantification | `quantification/examples/additivity.ttl` (case 1) | a multicurrency facility limit, and which amounts may be added |
| Vocabulary, applied classification | `vocabulary/examples/temporal-handover.ttl`, `applied/classification/` | reference data bound to a contract, and changed at a stated instant |
| Eligibility | `eligibility/examples/flat-scheme-lending.ttl` | a credit policy's sector rule, with a three-valued outcome |
| Behaviour | `behaviour/examples/covenant-default.ttl`, `instrument/examples/facility-cure-period.ttl` | default and cure as nested states |
| Instrument, change | `instrument/examples/facility-amendment.ttl`, `wording/examples/facility-amendment.ttl` | an amendment, and the versions it produces |
| Capacity (applied) | `applied/capacity/` | drawdowns against the facility limit |
| Persistence | `persistence/examples/lending-credit-shared-class.ttl` | how a lending deployment chooses its storage patterns |
| Surface | `surface/examples/saas-subscription-currency.ttl` | promoting a value along a read path, the ontology's counterpart to denormalisation |
| Applied insurance | `applied/insurance/common/`, `applied/insurance/peril/` | how a domain is built on the substrate |

Party has no examples folder. Its ideas (actors, role occupancy, several and joint obligation) are
taught from the Instrument facility examples, which use them.

Each chapter re-reads its sources when it is written. This table was drawn from the files' header
comments only, and a chapter whose source turns out not to show its idea picks another file from the
same folder and records the change in the status record.

## 4. Chapters

| # | Chapter | For the data architect |
|---|---|---|
| 0 | Why LATTICE | contracts as versioned, queryable data, and judgements evaluated from facts rather than stored |
| 1 | From tables to graphs | a concept map: class and entity, property and attribute or relationship, IRI and global key, named graph and partition, SHACL and constraints, SKOS scheme and reference data, version IRI and schema version. The open-world assumption, where the analogy breaks |
| 2 | Reading Turtle | enough syntax to read every later excerpt, taught on `keys.ttl` |
| 3 | The layer map | substrates, applied modules and the one-way dependency order, as a Mermaid diagram |
| 4 | Identity and keys | Foundation |
| 5 | Text and meaning | Wording, and instantiation of a form for one facility |
| 6 | Who owes what | Instrument and Party |
| 7 | Amounts and reference data | Quantification and Vocabulary, with the applied classification module |
| 8 | Rules for admission | Eligibility |
| 9 | Change over time | Behaviour, and amendment |
| 10 | Drawing down | the applied Capacity module |
| 11 | Storing and serving it | Persistence and Surface |
| 12 | Building a domain | the applied insurance modules as a worked case, and the steps for a domain of the reader's own |
| 13 | Where next | the Field Guide, the theory page, the architecture diagrams and the ADRs |

## 5. Slices

| Slice | Delivers | Estimate |
|---|---|---|
| TUT-0 | the skeleton: `docs/tutorial.md`, `docs/_layouts/tutorial.html` (from the theory layout, with chapter navigation and Turtle highlighting styles), empty chapter files, the home page link, and the excerpt check (`tools/tutorial_snippets.py`, its test, `check:tutorial-snippets`) | 120k tokens |
| TUT-1 | chapters 0 to 3, the orientation | 150k tokens |
| TUT-2 | chapters 4 to 6, identity, wording, instrument | 200k tokens |
| TUT-3 | chapters 7 to 9, amounts, eligibility, behaviour | 200k tokens |
| TUT-4 | chapters 10 to 13, capacity, storage, domains, next steps | 180k tokens |

Each slice is read and approved by the maintainer before the next starts, since TUT-1 sets the
voice and depth the rest follow.

### The excerpt check (TUT-0)

An excerpt in a chapter is a fenced Turtle block preceded by an HTML comment naming its source, for
example `<!-- source: ontology/instrument/examples/software-licence.ttl -->`. The check reads every
chapter file, and for each excerpt confirms that its lines appear, in order and contiguous, in the
named file, ignoring trailing whitespace. An excerpt may elide lines with a line holding only
`# …`, which splits it into parts checked separately. The same check confirms that every link of the
form `https://github.com/nebularis/lattice/blob/main/<path>` or `…/tree/main/<path>` names a path
that exists in the checkout (TUT-Q1). The script uses the standard library only, and prints
repository-relative paths with `Path.as_posix()`.

Tests, at level L1, cover a matching excerpt, a changed line, a missing source file, an excerpt
without a source comment, an elision, a link to a present path and a link to a missing one.

## 6. Publishing constraints

- Only `docs/` is published. Links to repository files are absolute GitHub URLs to `main` (TUT-Q1).
- The site uses no Jekyll theme. The layout carries all styling, including code highlighting.
- The pinned `github-pages` gem brings Rouge 3.30.0, which has a Turtle lexer (tag `turtle`, file
  `lib/rouge/lexers/turtle.rb` at tag `v3.30.0`). Excerpts are fenced as `turtle` and the layout
  styles Rouge's token classes (TUT-Q3).
- Every new file carries the `CC-BY-SA-4.0` SPDX header, as the existing docs do.
- Mermaid is loaded once by the layout, as in the theory layout. Every diagram is checked to render
  before handoff.

## 7. Deferred: the hands-on tutorial

A later unit turns the tutorial into exercises the reader runs: install the toolchain, validate an
example, break a shape and read the report, compile a condition to SPARQL. It depends on a stable
task for each step and on a working local environment, and is not planned here. It is recorded in
`docs/developer/INDEX.md` so it is not lost.

## 8. Questions, answered

The maintainer accepted every leaning on 2026-10-14.

| ID | Question | Options and consequences | Answer |
|---|---|---|---|
| TUT-Q1 | Where do repository links point? | (a) `main`, always current, but a link can break when a file moves. (b) a release tag, stable, but the reader sees an old file. The excerpt check already keeps excerpts current | (a), with the check in TUT-0 extended to confirm each linked path exists |
| TUT-Q2 | Does `check:tutorial-snippets` join the `check` aggregate? | If yes, a stale excerpt fails the build for whoever changed the example, who may not know the tutorial exists. If no, the tutorial drifts until someone runs the check | yes. The check is stdlib-only and fast |
| TUT-Q3 | If Rouge 3.30.0 has no Turtle lexer, how are excerpts shown? | (a) plain, unhighlighted blocks. (b) a client-side highlighter loaded by the layout, a script from a CDN | (a) accepted, then moot. Rouge 3.30.0 has a Turtle lexer, so excerpts are highlighted at build time with no script |
| TUT-Q4 | The insurance modules are being built by the `applied-insurance-reference` epic now. How does chapter 12 treat them? | (a) teach what is merged, with a note that the modules are under construction. (b) wait for the epic's phase 2 | (a). Chapter 12 is written last, so it sees the latest state |
