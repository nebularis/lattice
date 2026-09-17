<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR A-07: Eligibility authoring direction and extraction contract

## Status

Accepted

## Context

Eligibility is currently green-field in this repository. To avoid domain leakage and keep extraction reproducible, authoring order and extraction boundaries must be explicit.

## Decision

Eligibility authoring follows this sequence:

1. Non-domain examples in `eligibility/examples/`.
2. Mechanism prose and fenced content in `eligibility/README.md`.
3. Extracted artefacts in `eligibility/spec/eligibility.ttl`, `eligibility/vocab/eligibility-vocab.ttl`, and `eligibility/shapes/*.ttl`.
4. Projection contracts in `eligibility/projection/*.ttl`.
5. Conformance fixtures in `eligibility/test/`.

Extraction contract:

- `turtle-spec` blocks generate `spec/eligibility.ttl`.
- `turtle-vocab` blocks generate `vocab/eligibility-vocab.ttl`.
- `turtle-shapes` blocks generate `shapes/*.ttl`.
- `turtle-example` is illustrative only and never extracted.

## Consequences

- The layer can be regenerated consistently.
- Domain-neutral substrate content remains clearly separated from worked examples and optional applied material.
- Gate-based verification has concrete artefacts to check.
