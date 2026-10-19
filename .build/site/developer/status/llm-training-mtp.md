<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# LLM Training and MORK Teaching Pack (MTP) Implementation Status

**Unit:** `llm-training-mtp`
**State:** Accepted - fully implemented and validated
**Sketch:** [llm-training.md](../sketches/llm-training.md)
**Governing ADRs:** [ADR-A25](../../architecture/decisions/ADR-A25-llm-participation-and-deterministic-production-gate.md), [ADR-A44](../../architecture/decisions/ADR-A44-mork-teaching-pack-generated-content-boundary.md)

## What was built

The MORK Teaching Pack (MTP) is a versioned, hash-pinned, machine-generated curriculum that teaches language models to emit valid MCN (MORK Compact Notation) without requiring them to memorize `Mork.ttl` in full. The implementation consists of:

### L0 Kernel Generator (`tools/mork/src/mtp/facts.py`, `doctrine.py`, `render.py`)
- Automatically extracts 258 terms and 895 axioms from `Mork.ttl`
- Derives box families, uncertainty codes, inverse pairs, and generative mandatory parts
- Anchors curated doctrine to ontology IRIs with logical fingerprinting
- Enforces axiom ownership: every GCI, disjointness, and completeness axiom must be claimed
- Generates `l0.txt` kernel with 7 invariants, decision ladder, 14 hot codes, and uncertainty escape

### L2/L3 Lenses and Cassettes Pipeline
- **S1–S13 pipeline** implements the full feed from ontology through cassette fidelity, minimisation, mutation, cassette selection, and routing
- Mutation-derived ground truth: applies mutation operators to verified examples, records what lint catches, identifies silent mistakes
- **9 lenses** (L-EGR, L-GEN, L-IND, L-INT, L-REP, L-TAX, L-TBX, L-UNC, L-?) with 300–800 tokens each
- **30+ cassettes** (C-LOAN, C-UNCERTAIN, etc.) with 150–400 tokens and isomorphic MCN verification
- Diagnostics and repair-loop table derived from mutation matrix
- Budget enforcement: hard gates on token counts, partition coverage, cassette fidelity

### Data and Contracts
- Curated inputs: `doctrine.yaml` (anchored doctrine), `partition.yaml` (term→lens assignment), `lenses/L-*.yaml`, `cassettes/C-*.yaml`, `routing.yaml`
- Generated artifacts: `pins.lock.json` (logical fingerprints), L0/L2/L3 rendered text and JSON, coverage report, mutation matrix
- MCN codebook (`mcn_codebook.py`) with stable reverse lookups

### Verification and CI
- MCN decoder with 337 round-trip tests including `loan_mapping.ttl` and `UncertainMappings.ttl` isomorphism proofs
- Structural tests: `test_mtp.py` with 9 passing tests
- CI gate: `build:mtp` generates output, `check:mtp` validates pins, cassette fidelity, mutation verdicts, and stale output
- Deterministic hashing: same inputs always produce byte-identical pins and manifest

## Evidence

- **Build:** `mise run build:mtp` produces 20 output files under `ontology/mork/mtp/out/` from curated inputs
- **Check:** `mise run check:mtp` validates logical consistency, pin drift detection, cassette isomorphism, and mutation fidelity
- **Tests:** `python -m pytest tools/mork/src -q` yields 346 passed, 8 skipped in 2.29s
- **Facts report:** `python -m mtp.cli facts-report` confirms 258 terms and 895 axioms extracted
- **Repository integration:** Follows [ADR-A77](../../architecture/decisions/ADR-A77-repository-topology-and-documentation-governance.md) topology; uses `mise` for orchestration, Python project under `tools/mork/` with conventional locks

## Design sketches implemented

1. [llm-training.md](../sketches/llm-training.md) — the conceptual thesis and L0-L5 tier model
2. [MTP-L0 Generator Sketch](../sketches/MTP-L0%20Generator%20Sketch) — facts.py, doctrine pinning, axiom ownership gates
3. [MTP L2 Generator Sketch.md](../sketches/MTP%20L2%20Generator%20Sketch.md) — S1-S13 pipeline, mutation-derived ground truth, cassette fidelity

## Acceptance

All three design sketches have been fully implemented and validated. The MTP generator is production-ready for the LLM training backend integration work (Phase 7), which remains deferred pending backend interface specification.

## Deferred (out of scope)

- Model-quality evaluation (`evalset.py`, `eval-report` CI, eval leakage/thin gates) — requires LLM backend invocation interface
- Backend selection and sampling policy — owned by separate backend-interface effort
- MCN encoder (`mcnio.encode()`) — only needed for future lint repair automation

## Next steps

- Phase 7: LLM backend integration, model-quality metrics, eval harness
- Maintain pin determinism across future Mork.ttl edits
- Expand cassette library and lens coverage as production deployments report new patterns
