<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A12: Identity and Derivation-Authority Model

**Status:** Accepted
**Date:** 2026-09-17

## Context

Eligibility and Behaviour will both produce artefacts derived from an authored declaration — a compiled property surface, a materialised closure, a validation report, an execution record. Several different questions get asked of a derived artefact, and conflating them produces real bugs: "has the meaning of the declaration changed", "was this produced by an interchangeable implementation", "is this exact file byte-identical to what would be produced now", and "can this replay be trusted" are four different questions with four different answers.

A single "hash" property cannot answer all four without collapsing distinctions that matter. Quantification already establishes a `LawDischarge`/`OperationalProfile` pattern (`qnt:dischargedForImplementationProfile`, `qnt:staticAnalysisMethod`) that this ADR generalises across the substrate rather than reinvents per layer.

## Decision

Four distinct identities are recognised, and are never conflated in any layer's specification:

| Identity | Covers | Used for |
|---|---|---|
| **Semantic content hash** | Canonical, meaning-bearing declaration content | Detecting semantic change. A witnessed-only variant is permitted, where only dimensions/states actually used contribute to the hash. |
| **Generation/profile identity** | Implementation profile version, generation/entailment/validation configuration, bound evaluator versions, property-IRI bindings | Determining whether two derived products are interchangeable. |
| **Build artefact hash** | A specific generated serialisation, materialised graph, or projection snapshot | Regeneration/re-materialisation equality checks. |
| **Runtime state hash** | A state snapshot or replay position, where required | Replay verification, only where the semantic log alone is insufficient. |

**Cache/derived-product validity = semantic content hash AND generation/profile identity.** A witnessed-only semantic hash may preserve caches when unused dimensions or states are added — this is the property that makes extending a declaration affordable — but must never, on its own, be used to claim interchangeability across registry, entailment-regime, or realisation-profile versions.

**Derivation-product taxonomy.** Every derived product is one of: inferred, validated, materialised, projected, indexed, generated, compiled, or a decision/execution record. Each records: source dataset/graph snapshot, source declaration(s), derivation/projection profile, implementation version, entailment regime (where applicable), validation profile (where applicable), creation time, the relevant hash identity/identities above, and its invalidation dependencies.

**Authority declaration.** Every derived product states its own authority as one of:

- `advisory` — informative, never authoritative on its own
- `cached-reproducible` — authoritative only because it is provably reproducible from its source
- `operationally authoritative` — the system of record for the fact it carries
- `externally authoritative-and-synchronised` — authority lives outside the graph, with an explicit synchronisation contract

A materialised or projected statement never automatically outranks its source declaration. Where an external store also accepts writes, a bidirectional synchronisation contract must be declared explicitly — it must never arise by accident because both the graph and an external store happen to both be writable.

**One canonicalisation contract** serves every layer and every derived-product type: blank nodes, ordered collections, equivalent serialisations, imported graph versions, concept/scheme identity, optional values, wildcard elision, and legacy IRI overrides are all canonicalised the same way regardless of which layer or which derivation kind is doing the canonicalising.

## Consequences

- Eligibility's dimension-set hash, Behaviour's declaration hash, and any future compiled surface all use this same four-identity model rather than each inventing its own hash property.
- A change to the canonicalisation contract changes every structural hash in the estate. This is a known, accepted cost, planned for at cutover rather than discovered later.
- Ordered-collection support is required in Foundation for this to be implementable consistently (effect precedence, absorption order, stimulus sequences, and canonicalisation all need it) — tracked as an open Foundation requirement, not designed here.
