<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# MORK Python Toolchain

Install the editable package from the repository root with:

```bash
mise exec -- python -m pip install -e ./tools/mork
```

The package provides the MORK decoder, codebook, community tooling, and MTP generator. Source code lives under `src/` using the standard Python package layout.

## Proposing mappings

`mork_propose` is what an agent needs to propose a MORK mapping from a source vocabulary to LATTICE, and `mise run mork:propose-mcp` serves it over MCP on standard input and output, for a host such as Claude Desktop. The server holds no model and saves nothing, so a person reviews what the agent keeps.

| Tool | Gives |
|---|---|
| `teaching_pack` | MTP's L0, doctrine, partition and worked cassettes, and MCN's codebook, about 4,500 tokens |
| `teaching_pack` translation card | MTP's `data/translations.yaml` as a card: the words a source vocabulary uses for legal relations and contract parts, such as right, duty, bearer, condition and rule, each with the LATTICE terms it may mean and when each reading holds. `candidate_terms` indexes each word under every term it may mean, so a source's Right finds `ins:Permission`, `ins:Power`, `ins:Exclusion` and `ins:Obligation` |
| `lessons` (CLI) | the rules a proposal history teaches, as `mork:propose -- lessons <history.ttl> [--reference <pack.ttl>]`: corrections grouped by what they changed, or by the reviewer's note where no correcting mapping is named, rejections grouped by the term written, the most frequent first, each with the mappings it covers and one note. A written term that is a subclass of the kept one is marked, and a rule that recurs is marked as a candidate minimal pair for MTP, which a person promotes. `--ledger` gives the older one line per mapping |
| `describe_term` | one term of a LATTICE layer in depth: its comment and utility in full, its place, the properties of it and to it, its individuals, and the message of every shape that names it, which carries the laws a mapping must keep. An agent reads it for each target term a card leaves unclear |
| `target_cards` | one line per term of each named LATTICE layer: its CURIE, kind, label, its `rdfs:comment` or its `fnd:utility`, whichever is longer, in full, and its superclass, domain or range. The deontic layers, Instrument, Eligibility, Party and Behaviour, are about 17,800 tokens together, where their READMEs are about 120,000 |
| `source_cards` | the same for a source vocabulary in an RDF file, for example ODRL's 206 terms in about 7,000 tokens |
| `candidate_terms` | the target terms likeliest to match one source term, ranked by BM25 over labels, names and definitions among terms of a compatible kind, so the agent chooses among a few |
| `check_mapping` | a proposal in MCN decoded by the reference decoder, validated against MORK's shapes, its target terms checked against the layers and compiled by `tools/mork_rdf`, and run over a sample source when one is given, what it writes validated against the layers' shapes with OWL RL entailment and each result reported on the mapping that wrote its node. A result about what the context supplies, a persisted identity or a stated term's clause, is information. Every failure is a finding the agent can act on |

Cards are generated from the specifications each time, in milliseconds, and never stored, so they cannot drift from what they describe.
