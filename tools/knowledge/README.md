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
| `design-shapes.ttl` | the SKOS scheme: 10 facets and 58 shapes, each phrased as a problem and carrying the synonyms a question arrives under |
| `extract.py` | derives the index from the tracked documents into an Oxigraph store under `.build/`, never committed |
| `ask.py` | the query surface. `exists`, `node`, `reaches` and `sparql`, with the miss log that decides whether the vocabulary needs a new concept |

## Tasks

```bash
mise run check:identifiers            # fail on an identifier mentioned but defined nowhere
mise run check:knowledge              # fail on a T-Box term or a derived node that breaks ADR-A134
mise run build:knowledge              # derive the index into .build/knowledge, about two seconds
mise run graph:ask -- exists version  # ask it a question
```

Three reports, none of which fails:

```bash
mise exec -- python tools/knowledge/identifiers.py --report      # the inventory, by family
mise exec -- python tools/knowledge/identifiers.py --variants    # identifiers written non-canonically
mise exec -- python tools/knowledge/identifiers.py --rehomed     # register entries no longer in their register
```

## Rules this tooling keeps

**Enumeration is from `git ls-files`, never a filesystem walk.** A checkout may hold ignored directories whose contents must not be read, so no tool here walks the tree.

**A family is checked only once its definition rule is written.** A family with no rule is counted and never failed, so no identifier is reported broken on the strength of a rule nobody has written.

**A register entry is meant to disappear.** Both registers remove an entry once a plan takes it on, so an unresolved mention of one is a rehoming and is reported rather than failed. A decision file is never removed, so an unresolved decision is rot or a decision planned and never drafted, and that fails.

**One identifier may have several spellings.** Mentions resolve on a normalised key of letters and digits, and the spelling a definition uses is the canonical one. A mention that resolves under another spelling is reported by `--variants`, never failed.

**A generated copy is skipped by its marker, not its directory.** Most files under `docs/_includes` are originals that live there, and only a file carrying the marker its generator writes is a copy.

**Every design shape carries `skos:altLabel` forms, including the gerund.** Measured: a question for "versioning" matches neither `fnd:Version`, a noun, nor the author's own phrasing of the problem, so without a declared synonym the right row is unreachable. `check:knowledge` fails on a shape with no synonym, and a tag outside the scheme is refused rather than stored.

**A term enters the T-Box only when a query or a check needs it, and its `rdfs:comment` says which.** `check:knowledge` fails on a term without one, so the rule is enforced rather than merely intended. The vocabulary describes this repository, so it sits here and not under `ontology/`, and it is outside the substrate release.

**The T-Box is parsed by Oxigraph in its own test, not only by rdflib.** rdflib accepts IRIs a strict parser refuses ([TSD-37](../../docs/architecture/triple-store-discovery.md)), so a document checked only on the lenient parser fails at its first strict consumer instead.
