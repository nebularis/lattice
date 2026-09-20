<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Governance

This document records the authoritative document hierarchy for the substrate, the naming/containment rule that applies to all new content, and pointers to the frameworks that operationalise both.

## Document hierarchy

When two documents appear to disagree, this is the order of authority:

1. **ADRs** ([architecture decisions](architecture/decisions/)) — the record of *why* the substrate is shaped the way it is. Supersede any conflicting statement in a layer README or in this document.
2. **Layer READMEs** (`<layer>/README.md`) — the authoritative literate specification for that layer's mechanism. `spec/*.ttl`, `vocab/*-vocab.ttl`, and `shapes/*.ttl` are mechanically extracted from a README's fenced blocks and never diverge from it independently.
3. **This document and `docs/architecture/*`** — cross-layer reference material, kept in sync with the ADRs and layer READMEs, but not itself a source of new decisions.
4. **Design notes, worked-example commentary, historical sketches** — informative only. Never cited as the reason for a substrate decision; if a design note motivates a change, the change is recorded as an ADR.

Substrate specifications never cite or quote applied-layer, deployment-specific, or historical design documents. A substrate document may state a generic premise and a generic law; it does not reference where that premise happened to first come up.

## Naming and containment rule

One rule, stated once here rather than repeated per layer or per gate:

**Substrate directories (`ontology/foundation/`, `ontology/vocabulary/`, `ontology/quantification/`, `ontology/party/`, `ontology/eligibility/`, `ontology/instrument/`, `ontology/behaviour/`, and their `spec/`, `vocab/`, `shapes/`, `projection/`, `ontology/examples/`) stay domain-neutral.** No class, property, named individual, `fnd:utility` string, or shipped example names a specific industry, product, brand, or closed-estate identifier.

Applied-layer or deployment-specific content — a concrete dimension set, a worked deployment example, a projection binding for a specific applied ontology — may be authored anywhere in this repository the user directs (for example, under `WINGMAN/`, which is not tracked by version control). Generating such content is not restricted; whether it is ever committed to a public branch is the user's decision, made per instance, not gated by a standing review process. This replaces an earlier, heavier containment posture (physical repository separation, an adversarial two-role clean-room review) that this project does not require.

The authoring *order* for substrate content — generic premise, then non-domain examples, then mechanism prose — is fixed procedurally in [ADR-A-C2](architecture/decisions/ADR-AC2-clean-room-authoring-procedure.md), not repeated here.

## Frameworks referenced elsewhere

- **Conformance levels** — [architecture/conformance-levels.md](architecture/conformance-levels.md) and [ADR-A14](architecture/decisions/ADR-A14-conformance-levels.md): what "conformant" means at a given stage of a graph's life, replacing a single valid/invalid gate.
- **Identity and derivation** — [ADR-A12](architecture/decisions/ADR-A12-identity-and-derivation-model.md): what a derived artefact's hash and authority claims mean.
- **Graph roles and provenance** — [ADR-A13](architecture/decisions/ADR-A13-dataset-graph-role-model.md): how source, mapping, declaration, and execution content coexist in one dataset.
- **Realisation-strategy neutrality** — [ADR-A15](architecture/decisions/ADR-A15-realisation-strategy-neutrality.md): no mechanism requires compilation to be usable.
- **MORK Compact Notation** — [architecture/mork-compact-notation.md](architecture/mork-compact-notation.md): the token-minimal wire format in which mapping agents emit MORK graphs, with the deterministic decoding to OWL that ADR-A25's proposal-grade gate operates on.
