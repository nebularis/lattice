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
| `describe_term` | one term of a LATTICE layer in depth: its comment and utility in full, its place, the properties of it and to it, its individuals, and the message of every shape that names it, which carries the laws a mapping must keep. An agent reads it for each target term a card leaves unclear |
| `target_cards` | one line per term of each named LATTICE layer: its CURIE, kind, label, its `rdfs:comment` or its `fnd:utility`, whichever is longer, in full, and its superclass, domain or range. The deontic layers, Instrument, Eligibility, Party and Behaviour, are about 17,800 tokens together, where their READMEs are about 120,000 |
| `source_cards` | the same for a source vocabulary in an RDF file, for example ODRL's 206 terms in about 7,000 tokens |
| `candidate_terms` | the target terms likeliest to match one source term, ranked by BM25 over labels, names and definitions among terms of a compatible kind, so the agent chooses among a few |
| `check_mapping` | a proposal in MCN decoded by the reference decoder, validated against MORK's shapes and compiled by `tools/mork_rdf`, and run over a sample source when one is given, with every failure a finding the agent can act on |

Cards are generated from the specifications each time, in milliseconds, and never stored, so they cannot drift from what they describe.
