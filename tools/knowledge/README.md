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
| `ask.py` | the query surface. `find`, `read`, `node`, `reaches`, `exists` and `sparql`, with the miss log of questions answered weakly or not at all |

## Tasks

```bash
mise run check:identifiers            # fail on an identifier mentioned but defined nowhere
mise run check:knowledge              # fail on a T-Box term or a derived node that breaks ADR-A134
mise run build:knowledge              # derive the index into .build/knowledge, about two seconds once the model is fetched
mise run graph:ask -- find tracking a balance drawn down and restored --kind mechanism  # ask it a question
mise run graph:ask -- read MEC-56     # read the section an entry points at
```

Three reports, none of which fails:

```bash
mise exec -- python tools/knowledge/identifiers.py --report      # the inventory, by family
mise exec -- python tools/knowledge/identifiers.py --variants    # identifiers written non-canonically
mise exec -- python tools/knowledge/identifiers.py --rehomed     # register entries no longer in their register
```

## Ranking by meaning

`find` filters exactly on kind, phase and audience, ranks what remains by how close an entry's name, claim and problem shape are in meaning to the question, and raises an entry by 0.02 for each of activity, quality and technology that matches the question's. A facet value matches up and down its broader chain, so a mismatch hides nothing and a tag written before the scheme grew still counts. The model is `BAAI/bge-small-en-v1.5` (MIT licence), run from its ONNX export by onnxruntime, at the revision and SHA-256 pinned in `embed.py` ([ADR-A134](../../docs/architecture/decisions/ADR-A134-knowledge-index-and-design-shape-vocabulary.md), decisions 20 to 23). The first build downloads 130 MB from Hugging Face. Where that is blocked, the build notes why and `find` says it cannot rank, and the other questions still work.

A weak answer is advice to look further. The agent then reads the documents as it would without the index, and an answer found there that no register entry holds is a register gap, reported to the maintainer.

## Registers

A register is a Markdown table whose column headers map to properties of [`knowledge.ttl`](knowledge.ttl). The mapping is the `COLUMNS` dict in `extract.py`, and a column's meaning is that property's `rdfs:comment`, written nowhere else. A row's claim is its bolded lead sentence of at most 200 characters. A header that is neither mapped nor on the unmapped list, and a value outside a controlled column's set, are reported rather than stored or dropped.

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

**Enumeration is from `git ls-files`, never a filesystem walk.** A checkout may hold ignored directories whose contents must not be read, so no tool here walks the tree.

**A family is checked only once its definition rule is written.** A family with no rule is counted and never failed, so no identifier is reported broken on the strength of a rule nobody has written.

**A register entry is meant to disappear.** Both registers remove an entry once a plan takes it on, so an unresolved mention of one is a rehoming and is reported rather than failed. A decision file is never removed, so an unresolved decision is rot or a decision planned and never drafted, and that fails.

**One identifier may have several spellings.** Mentions resolve on a normalised key of letters and digits, and the spelling a definition uses is the canonical one. A mention that resolves under another spelling is reported by `--variants`, never failed.

**A generated copy is skipped by its marker, not its directory.** Most files under `docs/_includes` are originals that live there, and only a file carrying the marker its generator writes is a copy.

**A facet value outside its scheme is reported, never stored.** A forked vocabulary makes every filter unreliable and nothing would say so. An entry is tagged with the most specific value that fits, and a filter on a broader value reaches every value under it. A value that two taggers might confuse with its neighbour carries a `skos:scopeNote` saying when to use it rather than that one, and the pairs most often confused are related, so a question naming either raises entries tagged with the other.

**A term enters the T-Box only when a query or a check needs it, and its `rdfs:comment` says which.** `check:knowledge` fails on a term without one, so the rule is enforced rather than merely intended. The vocabulary describes this repository, so it sits here and not under `ontology/`, and it is outside the substrate release.

**The T-Box is parsed by Oxigraph in its own test, not only by rdflib.** rdflib accepts IRIs a strict parser refuses ([TSD-37](../../docs/architecture/triple-store-discovery.md)), so a document checked only on the lenient parser fails at its first strict consumer instead.
