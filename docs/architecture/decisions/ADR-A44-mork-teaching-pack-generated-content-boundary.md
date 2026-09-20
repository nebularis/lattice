<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A44: MORK Teaching Pack generated-content boundary

**Status:** Accepted
**Date:** 2026-09-20
**Related:** MTP implementation plan, ADR-A25, ADR-A42, ADR-A43

## Context

MTP consumes normative MORK ontology, MCN codebook, decoder, examples, and shapes to generate a versioned curriculum. It must remain reproducible and structurally verifiable without depending on an LLM backend. Curated doctrine, lens, cassette, partition, and routing material also needs a clear ownership boundary from generated output.

## Decision

Place MTP Python code under `tools/mork/src/mtp/`, curated content under `ontology/mork/mtp/data/`, and generated committed output under `ontology/mork/mtp/out/`. MTP consumes `mcn`, `mcn_codebook`, `Mork.ttl`, examples, and constraints through adapters. It does not modify those sources except through separately approved work.

Use root `mise` for scoped MTP bootstrap, check, and build tasks. Add a manual MTP structural CI job that installs the MORK package, runs structural tests, regenerates the pack, checks it, and fails on generated-output or pin drift. Backend-dependent model-quality evaluation remains deferred.

## Consequences

- Generated output is build-owned and never manually edited.
- Curated source changes, generated output changes, and pins are reviewed together.
- Structural MCN decode, lint, cassette fidelity, partition, budget, routing, and drift checks remain required before any model backend exists.
- Every MTP phase must add ADR, architecture, developer handoff, structural tests, CI wiring, and authored-versus-validated status.
