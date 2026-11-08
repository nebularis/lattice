<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Knowledge tooling

The index over this repository's own working documents is Вивід's, `vyd`, bound by `vyvid.toml` at the root ([ADR-A152](../../docs/architecture/decisions/ADR-A152-vyvid-adoption.md)). What stays here is what only LATTICE has: its architectural quanta, the catalogue's units an Owner cell may name, the identifier exceptions, and the tests that prove the knowledge base consistent.

Markdown stays the source of truth. Everything derived from it holds no content of its own, so deleting the whole index loses nothing but speed.

## What is here

| File | Holds |
|---|---|
| `extractor.py` | LATTICE's extractor for Вивід, the command `vyvid.toml` declares. `vyd build` runs it in the checkout with one JSON request, and it writes the catalogue's units, so an Owner cell that names a module, a tool package, a root or an area becomes an edge. The architectural quanta are Вивід's own `quanta` kind, which `vyvid.toml` declares over the catalogue |
| `identifier-exceptions.txt` | identifiers that are mentioned but defined nowhere, each with its reason. The baseline `vyd check identifiers` measures a new break against |
| `test_knowledge_base.py` | the knowledge base proven consistent against the store `vyd build` writes: closed values, stable pointers, a check or a reason for each structural standard, every question an entry, every signpost resolving |
| `test_extractor.py` | the extractor run on this checkout |

## Tasks

Every `vyd` command goes through `mise` (ADR-A29), and each task skips with a note where `vyd` is missing (PRI-79).

```bash
mise run check:identifiers            # fail on an identifier mentioned but defined nowhere
mise run check:knowledge              # fail on a derived node or a register row that breaks ADR-A134
mise run build:knowledge              # derive the index into Вивід's store for this checkout, a few seconds after the first build
mise run graph:ask -- find tracking a balance drawn down and restored --kind mechanism  # ask it a question
mise run graph:ask -- read MEC-56     # read the section an entry points at, with its fields and neighbours first
mise run graph:ask -- gap "MEC-56 does not cover a keyed child" MEC-56 ontology/ledger/README.md:120  # record what reading found
mise run graph:ask -- misses --near   # the weak answers, the near ones and the gaps recorded, less those now answered
mise run graph:ask -- close MEC-56    # close the gaps on an entry whose signpost is now written
mise run vyd -- check identifiers --all   # anything else, such as the variants and the removable rows the check lists
```

## Registers

A register is a Markdown table whose column headers map to properties of Вивід's vocabulary, and a column's meaning is that property's `rdfs:comment`, written nowhere else. A row's claim is its bolded lead sentence of at most 200 characters. A header that is neither mapped nor on the unmapped list, and a value outside a controlled column's set, are reported rather than stored or dropped. Which family each register defines is declared in `vyvid.toml`.

**Signposts.** Three columns carry what sits at an entry's edge ([ADR-A134](../../docs/architecture/decisions/ADR-A134-knowledge-index-and-design-shape-vocabulary.md) decision 28), filled forward, as an entry is written or a reader is found to have confused it. They stand last in their tables, and a row may leave them out, so only a row that carries one changes. A claim over 200 characters is reported, since it is cut where a boundary is usually written. A claim whose rule has a neighbour it could be read against names its boundary in its first sentence (STD-281).

| Column | Registers | Holds | Checked |
|---|---|---|---|
| Does not cover | standards, principles, patterns, mechanisms | the case the entry does not decide, in at most 120 characters, embedded with the claim | its length |
| Distinguished from | standards, principles, patterns, mechanisms | the entries a reader confuses this one with, symmetric | each names an entry |
| Bears on | technical debt, pending decisions, capabilities, and a store finding's `**Bears on:**` line | the entries, and the declared terms by the CURIE their layer writes, that the row qualifies | each names an entry or a declared term |

**Owners.** An Owner or Provided by cell names a unit of the catalogue, a module by name, a tool package by name or path, a root or documentation area by path, or a module kind such as `substrate` for every module of that kind. The extractor declares these units to Вивід, so the cell becomes an edge to each, and a name it does not know is reported and kept as written.

**Questions.** A plan or a sketch raises a question by a bold lead, `**LG-Q7. <question>**` or `- **LG-Q7.** <text>`, or by a table row whose first cell is its identifier. The lead's paragraph or the row is its pointer, and it is answered when its text says Answered, with the date after the word. A plan's definition wins over a sketch's. `now <ID>` in an answer makes that entry answer the question, and an answered question whose answer says must, never or only and names no such entry is reported after thirty days (STD-283).

**Supersession.** A decision's Status line, `Superseded by ADR-Ann`, gives it its successor, and the build reports a Superseded decision that names none. An addendum that reverses or narrows numbered decisions of its file opens with a bold lead, `**Reverses decision 8.**` or `**Narrows decisions 3 and 6.**` (STD-282). The number names the Decision section's item, or else the one addendum that numbers it, and a number naming neither is reported.

## Facets

A facet is a closed set of values a register entry is tagged with, in its Activity, Quality and Technology columns ([ADR-A134](../../docs/architecture/decisions/ADR-A134-knowledge-index-and-design-shape-vocabulary.md) decisions 24 and 25). The values are Вивід's general scheme. LATTICE's facet register was identical to it row for row and was removed on 2026-11-05 (ADR-A152 decision 1). A value LATTICE needs which the scheme lacks goes in a project facets file named by `facets` in `vyvid.toml`.

| Facet | Says | Follows |
|---|---|---|
| Activity | what the person or agent is doing when the entry matters | the knowledge areas of SWEBOK v4, the DAMA-DMBOK 2 data-management areas, TOGAF's architecture domains and the DevOps loop |
| Quality | which characteristic the entry protects or trades | the characteristics of ISO/IEC 25010:2023 and the data qualities of ISO/IEC 25012, with what this repository needs beyond them, such as determinism, development efficiency and auditability |
| Technology | which technology the entry is specific to, left empty when it is not specific | what this repository uses and what an agent is likely to ask about |

Each facet follows a published division of its field, so it covers the field rather than this repository's habits and needs few additions. The definitions are our own words, and no value names private work.

The scheme is SKOS, and a value's label, definition, scope note, broader and related values are its properties.

**Tagging.** An entry takes one to three values of Activity and of Quality, and as many of Technology as it is specific to, always the most specific value that fits. A value may have several broader values, as SKOS allows, so Java is both a language and a platform. A group value organises the others and is never tagged. A question's value matches an entry's when one lies on the other's broader chain, so a mismatch hides nothing. A value outside its scheme is reported, never stored, since a forked vocabulary makes every filter unreliable and nothing would say so.

The structural facets, kind, audience, phase, stratum and the quanta's views, are individuals of Вивід's vocabulary, because a check reads them. The facets live outside `ontology/` and the substrate release of ADR-A129, since they describe how we work in this repository, not the domain.

## Rules this tooling keeps

**Every path comes from the catalogue reader.** The extractor reads the modules, the tool packages and the areas from it, so a moved module is one catalogue edit and the extractor runs from any worktree (STD-273). The files it reads are the ones `vyvid.toml` names, and an edit to them or to its own code rebuilds the index of the checkout it is in.

**A quantum is derived, never declared, and separately in each view.** The data view reads the imports between the ontology documents, the software view each deployment's compose file, and the same module falls into different quanta in different views. The rules are Вивід's, in its `quanta` kind ([ADR-A134](../../docs/architecture/decisions/ADR-A134-knowledge-index-and-design-shape-vocabulary.md), addendum of 2026-10-25).

**The extractor writes into its own graphs alone, and a failure costs only its entries.** Вивід refuses the whole output of a run that writes outside the index graph, or exits non-zero, and reports it, so a broken extractor never corrupts the rest of the index.

**A register entry is meant to disappear.** The debt and backlog registers remove an entry once a plan takes it on, so an unresolved mention of one is a rehoming and is reported rather than failed, which `vyvid.toml` declares as `removable`. A decision file is never removed, so an unresolved decision is rot or a decision planned and never drafted, and that fails.
