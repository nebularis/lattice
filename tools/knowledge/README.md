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
| `facets.ttl` | the facets entries are tagged with, Activity, Quality and Technology, each a SKOS concept scheme with a definition per value. A value may sit under several broader values, so Java is both a language and a platform, and two values may be related across facets, as UX design is to interaction capability. Generated from Markdown once TD-81 is paid |
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

## Rules this tooling keeps

**Enumeration is from `git ls-files`, never a filesystem walk.** A checkout may hold ignored directories whose contents must not be read, so no tool here walks the tree.

**A family is checked only once its definition rule is written.** A family with no rule is counted and never failed, so no identifier is reported broken on the strength of a rule nobody has written.

**A register entry is meant to disappear.** Both registers remove an entry once a plan takes it on, so an unresolved mention of one is a rehoming and is reported rather than failed. A decision file is never removed, so an unresolved decision is rot or a decision planned and never drafted, and that fails.

**One identifier may have several spellings.** Mentions resolve on a normalised key of letters and digits, and the spelling a definition uses is the canonical one. A mention that resolves under another spelling is reported by `--variants`, never failed.

**A generated copy is skipped by its marker, not its directory.** Most files under `docs/_includes` are originals that live there, and only a file carrying the marker its generator writes is a copy.

**A facet value outside its scheme is reported, never stored.** A forked vocabulary makes every filter unreliable and nothing would say so. An entry is tagged with the most specific value that fits, and a filter on a broader value reaches every value under it. A value that two taggers might confuse with its neighbour carries a `skos:scopeNote` saying when to use it rather than that one, and the pairs most often confused are related, so a question naming either raises entries tagged with the other.

**A term enters the T-Box only when a query or a check needs it, and its `rdfs:comment` says which.** `check:knowledge` fails on a term without one, so the rule is enforced rather than merely intended. The vocabulary describes this repository, so it sits here and not under `ontology/`, and it is outside the substrate release.

**The T-Box is parsed by Oxigraph in its own test, not only by rdflib.** rdflib accepts IRIs a strict parser refuses ([TSD-37](../../docs/architecture/triple-store-discovery.md)), so a document checked only on the lenient parser fails at its first strict consumer instead.
