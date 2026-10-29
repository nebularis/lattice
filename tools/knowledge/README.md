<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Knowledge tooling

The index over this repository's own working documents, so an agent can retrieve what the project already knows without reading whole plans.

Markdown stays the source of truth. Everything here derives from it and holds no content of its own, so deleting the whole index loses nothing but speed.

## What is here

| File | Holds |
|---|---|
| `identifiers.py` | the identifier families, how each is written and where each is defined, and the referential-integrity check over them |
| `identifier-exceptions.txt` | identifiers that are mentioned but defined nowhere, each with its reason. The baseline the check measures a new break against |
| `knowledge.ttl` | the T-Box: the node kinds, their relations and the closed status set ([ADR-A134](../../docs/architecture/decisions/ADR-A134-knowledge-index-and-design-shape-vocabulary.md)) |
| `facets.py` | generates the facet schemes, Activity, Quality and Technology, as SKOS Turtle in `.build/knowledge/facets.ttl` from the [facet register](../../docs/developer/facets.md) on every build, never committed (see [Facets](#facets)) |
| `extract.py` | derives the index from the tracked documents into an Oxigraph store under `.build/`, never committed |
| `embed.py` | ranks entries by meaning: the pinned model, fetched into `.build/knowledge/model/` on first build, and the vectors beside the store, re-embedding only changed text |
| `ask.py` | the query surface. `find`, `read`, `node`, `reaches`, `exists` and `sparql`, with the miss log of questions answered weakly or not at all, the ask log of every `find` and `read`, and `gap` and `misses` over both |

## Tasks

```bash
mise run check:identifiers            # fail on an identifier mentioned but defined nowhere
mise run check:knowledge              # fail on a T-Box term or a derived node that breaks ADR-A134
mise run build:knowledge              # derive the index into .build/knowledge, about two seconds once the model is fetched
mise run graph:ask -- find tracking a balance drawn down and restored --kind mechanism  # ask it a question
mise run graph:ask -- read MEC-56     # read the section an entry points at, with its fields and neighbours first
mise run graph:ask -- gap "MEC-56 does not cover a keyed child" MEC-56 ontology/ledger/README.md:120  # record what reading found
mise run graph:ask -- misses --near   # the weak answers, the near ones and the gaps recorded, less those now answered
mise run graph:ask -- close MEC-56    # close the gaps on an entry whose signpost is now written
```

Three reports, none of which fails:

```bash
mise exec -- python tools/knowledge/identifiers.py --report      # the inventory, by family
mise exec -- python tools/knowledge/identifiers.py --variants    # identifiers written non-canonically
mise exec -- python tools/knowledge/identifiers.py --rehomed     # register entries no longer in their register
```

## Ranking by meaning

`find` filters exactly on kind, phase and audience, ranks what remains by how close an entry's name, claim and problem shape are in meaning to the question, and raises an entry by 0.02 for each of activity, quality and technology that matches the question's. A facet value matches up and down its broader chain, so a mismatch hides nothing and a tag written before the scheme grew still counts. A phase matches along its broader chain too, so `--phase production` also finds rules tagged runtime, which bind in every environment, and `--phase runtime` finds those tagged testing, benchmarking or production (decision 27). The model is `BAAI/bge-small-en-v1.5` (MIT licence), run from its ONNX export by onnxruntime, at the revision and SHA-256 pinned in `embed.py` ([ADR-A134](../../docs/architecture/decisions/ADR-A134-knowledge-index-and-design-shape-vocabulary.md), decisions 20 to 23). The first build downloads 130 MB from Hugging Face. Where that is blocked, the build notes why and `find` says it cannot rank, and the other questions still work.

Besides the register entries and the decisions, `find` ranks three other kinds of node ([ADR-A134](../../docs/architecture/decisions/ADR-A134-knowledge-index-and-design-shape-vocabulary.md), decisions 29 to 31). Each numbered decision and each addendum of a decision file is embedded as a section of that decision, which is scored by the best of its sections and points at that section when it wins. Each question a plan or a sketch raises is an entry of kind `question`, and `--exclude question` leaves them out of an answer they crowd. Each declared ontology term, a class, a property, a scheme concept, or an individual declared outside the examples and the tests, has a claim the term summary derives from its label, its comment and its restrictions, and `find` ranks the terms only when `--kind` names `term`. Ask for them to learn what a class or property means, whether one exists for a concept before declaring one, or what restricts it. Never mix them into a question about a design, a rule, a decision or what the project already has, since ranked with the entries they pushed the answers out of the top five, hit@5 0.79 against 0.93.

**What a row says beside its claim.** A flags column marks `!` an entry that states a case it does not cover, `~` a decision or section that was superseded, reversed or narrowed, `TD` an entry an open debt bears on, and `?` a Proposed entry. When `find` shows eight rows or fewer, the line under each holds the whole claim and names each of these: the uncovered case, the successor or the addendum, and the debt. A superseded decision is kept, marked, and loses 0.01, so its successor ranks above it at equal meaning. `read <ID>` prints the entry's fields that `find` does not show and every entry linked to it by a declared edge, in either direction, before the text, and refuses a pointer that names the whole of a file over 200 lines.

**The logs.** Every `find` and `read` is appended to `.build/knowledge/asks.log` with its best score and what it showed, and `gap` appends what an agent found by reading, with the entry and the line. `misses` lists the weak answers and the gaps, and `misses --near` adds the questions answered from 0.69 to under 0.74, where a confident and incomplete answer lives. The logs are pruned as gaps close: `misses` first asks each logged weak or near question again and removes those now answered at 0.74 or above, and `close <ID>` removes the gaps on an entry and the lines of the question asked just before each.

A weak answer is advice to look further. The agent then reads the documents as it would without the index, and an answer found there that no register entry holds is a register gap, reported to the maintainer.

## Registers

A register is a Markdown table whose column headers map to properties of [`knowledge.ttl`](knowledge.ttl). The mapping is the `COLUMNS` dict in `extract.py`, and a column's meaning is that property's `rdfs:comment`, written nowhere else. A row's claim is its bolded lead sentence of at most 200 characters. A header that is neither mapped nor on the unmapped list, and a value outside a controlled column's set, are reported rather than stored or dropped.

**Signposts.** Three columns carry what sits at an entry's edge ([ADR-A134](../../docs/architecture/decisions/ADR-A134-knowledge-index-and-design-shape-vocabulary.md) decision 28), filled forward, as an entry is written or a reader is found to have confused it. They stand last in their tables, and a row may leave them out, so only a row that carries one changes. A claim over 200 characters is reported, since it is cut where a boundary is usually written. A claim whose rule has a neighbour it could be read against names its boundary in its first sentence, and its Distinguished from column names that neighbour (STD-281).

| Column | Registers | Holds | Checked |
|---|---|---|---|
| Does not cover | standards, principles, patterns, mechanisms | the case the entry does not decide, in at most 120 characters, embedded with the claim | its length |
| Distinguished from | standards, principles, patterns, mechanisms | the entries a reader confuses this one with, symmetric | each names an entry |
| Bears on | technical debt, pending decisions, capabilities, and a store finding's `**Bears on:**` line | the entries, and the declared terms by the CURIE their layer writes, that the row qualifies | each names an entry or a declared term |

**Questions.** A plan or a sketch raises a question by a bold lead, `**LG-Q7. <question>**` or `- **LG-Q7.** <text>`, or by a table row whose first cell is its identifier. The lead's paragraph or the row is its pointer, and it is answered when its text says Answered, with the date after the word. A plan's definition wins over a sketch's. `now <ID>` in an answer makes that entry answer the question, and an answered question whose answer says must, never or only and names no such entry is reported by the build 30 days after its answer (STD-283). A question raised anywhere else is counted by `check:identifiers` and never failed.

**Supersession.** A decision's Status line, `Superseded by ADR-Ann`, gives it its successor, and the build reports a Superseded decision that names none. An addendum that reverses or narrows numbered decisions of its file opens with a bold lead, `**Reverses decision 8.**` or `**Narrows decisions 3 and 6.**` (STD-282). The number names the Decision section's item, or else the one addendum that numbers it, and a number naming neither is reported.

## Facets

A facet is a closed set of values a register entry is tagged with, in its Activity, Quality and Technology columns ([ADR-A134](../../docs/architecture/decisions/ADR-A134-knowledge-index-and-design-shape-vocabulary.md) decisions 24 and 25). The [facet register](../../docs/developer/facets.md) is the source. `facets.py` writes it as three SKOS concept schemes into `.build/knowledge/facets.ttl` on every build, and the Turtle is never committed or edited, as STD-003 requires of anything a tool can derive. SKOS concepts rather than OWL classes, because these are values the maintainer amends, not facts a check reasons over.

| Facet | Says | Follows |
|---|---|---|
| Activity | what the person or agent is doing when the entry matters | the knowledge areas of SWEBOK v4, the DAMA-DMBOK 2 data-management areas, TOGAF's architecture domains and the DevOps loop |
| Quality | which characteristic the entry protects or trades | the characteristics of ISO/IEC 25010:2023 and the data qualities of ISO/IEC 25012, with what this repository needs beyond them, such as determinism, development efficiency and auditability |
| Technology | which technology the entry is specific to, left empty when it is not specific | what this repository uses and what an agent is likely to ask about |

Each facet follows a published division of its field, so it covers the field rather than this repository's habits and needs few additions. The definitions are our own words, and no value names private work.

Each column of a scheme's table is the SKOS property that states its meaning: Label `skos:prefLabel`, Broader `skos:broader`, Related `skos:related`, Definition `skos:definition` and Scope note `skos:scopeNote`. A value with no broader value is a top concept of its scheme. Group yes is the editorial note "group", and Ratified no the editorial note "proposed". Broader and related values are slugs separated by spaces.

**Tagging.** An entry takes one to three values of Activity and of Quality, and as many of Technology as it is specific to, always the most specific value that fits. A value may have several broader values, as SKOS allows, so Java is both a language and a platform. A group value organises the others and is never tagged. A question's value matches an entry's when one lies on the other's broader chain, so a question about physical data modelling still raises an entry tagged data modelling. A value two taggers might confuse with its neighbour has a scope note saying when to use it rather than that one, and the pairs most often confused are also related, so a question naming either raises entries tagged with the other.

The structural facets, kind, audience, phase, stratum and the quanta, are T-Box individuals in [`knowledge.ttl`](knowledge.ttl), because a check reads them. The facets live outside `ontology/` and the substrate release of ADR-A129, since they describe how we work in this repository, not the domain.

## Rules this tooling keeps

**Every path comes from the catalogue reader.** `identifiers.py` takes the root and the `developer` and `architecture` areas from it, and `facets.py`, `extract.py` and `embed.py` build on those, so a moved register is one catalogue edit and the tools run from any worktree (STD-273).

**Enumeration is from `git ls-files`, never a filesystem walk.** A checkout may hold ignored directories whose contents must not be read, so no tool here walks the tree.

**A family is checked only once its definition rule is written.** A family with no rule is counted and never failed, so no identifier is reported broken on the strength of a rule nobody has written.

**A register entry is meant to disappear.** Both registers remove an entry once a plan takes it on, so an unresolved mention of one is a rehoming and is reported rather than failed. A decision file is never removed, so an unresolved decision is rot or a decision planned and never drafted, and that fails.

**One identifier may have several spellings.** Mentions resolve on a normalised key of letters and digits, and the spelling a definition uses is the canonical one. A mention that resolves under another spelling is reported by `--variants`, never failed.

**A generated copy is skipped by its marker, not its directory.** Most files under `docs/_includes` are originals that live there, and only a file carrying the marker its generator writes is a copy.

**A facet value outside its scheme is reported, never stored.** A forked vocabulary makes every filter unreliable and nothing would say so. An entry is tagged with the most specific value that fits, and a filter on a broader value reaches every value under it. A value that two taggers might confuse with its neighbour carries a `skos:scopeNote` saying when to use it rather than that one, and the pairs most often confused are related, so a question naming either raises entries tagged with the other.

**A term enters the T-Box only when a query or a check needs it, and its `rdfs:comment` says which.** `check:knowledge` fails on a term without one, so the rule is enforced rather than merely intended. The vocabulary describes this repository, so it sits here and not under `ontology/`, and it is outside the substrate release.

**The T-Box is parsed by Oxigraph in its own test, not only by rdflib.** rdflib accepts IRIs a strict parser refuses ([TSD-37](../../docs/architecture/triple-store-discovery.md)), so a document checked only on the lenient parser fails at its first strict consumer instead.
