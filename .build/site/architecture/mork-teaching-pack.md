<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# MORK Teaching Pack

MTP is a deterministic generator for a versioned, hash-pinned MCN curriculum. It is not an LLM runtime, evaluation harness, or alternative MORK source of truth. It consumes the normative MORK ontology, MCN decoder, MCN codebook, examples, and constraints.

## Ownership

`tools/mork/src/mtp/` is pure generator code. `ontology/mork/mtp/data/` contains curated doctrine, partition, lenses, cassettes, routing, and pins. `ontology/mork/mtp/out/` contains generated and committed output. The build owns every file under `out/`. MTP does not move or rewrite `Mork.ttl`, `mcn_decoder.py`, `mcn_codebook.py`, examples, or constraints.

## Structural Pipeline

The build extracts logical facts and fingerprints from `Mork.ttl`, verifies codebook coverage through the existing codebook, reads curated doctrine and term-to-lens partitioning, measures the example corpus, validates and minimises MCN cassettes, runs structural mutations, renders lenses and routing, then writes a digest manifest. The silent mutation set is a governance signal: it either drives a lens smell or a separately filed constraints gap.

`mtp/mcnio.py` uses the existing `mcn` package for decoding, linting, and graph isomorphism. This is required correctness infrastructure and is not model evaluation. The absent MCN encoder remains a narrow `NullTool` limitation only.

## Toolchain and Validation

The root `mise.toml` provides `bootstrap:mork`, `check:mtp`, and `build:mtp`. `tools/mork/pyproject.toml` owns MTP Python dependencies. The manual `mtp-structural` CI job installs the MORK package, runs structural tests, builds output, checks pins and coverage, and rejects generated-file drift.

The authoring host has not run these Python commands. A network-enabled environment must install dependencies, regenerate and review `ontology/mork/mtp/out/` and `pins.lock.json`, then record the build and check results. LLM output scoring, backend selection, held-out eval sets, and eval metrics remain deferred to MTP Phase 7.

## Documentation Boundary

The detailed roadmap is [MTP implementation plan](../../ontology/mork/docs/mtp-implementation-plan.md). The phase handoff is [MTP handoff](../developer/mtp-handoff.md). Decisions affecting curation, pins, packages, code-generation, or backend interfaces require ADRs. Normative MCN and MORK semantics remain in their MORK documents.
