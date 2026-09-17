<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A13: Dataset, Graph-Role, and Provenance Model

**Status:** Accepted
**Date:** 2026-09-17

## Context

RDF/OWL lets a graph hold information before it is fully mapped, validated, classified, or operationalised. Eligibility and Behaviour's designs, taken naively, could be read as assuming a graph only becomes "real" once it is declaration-conformant and, optionally, compiled. That reading is wrong and needs to be corrected as a standing architectural premise, not left implicit in each layer's own document.

Compilation is one optional, deliberately chosen delivery strategy, appropriate when latency, volume, or deployment constraints justify generated code or generated properties. SPARQL, SHACL, OWL/RDFS reasoning, graph-native materialisation, and external projection are peer strategies, not fallback options on the way to compilation. Validation reports conformance to a stated profile; it does not gate ingestion. A graph can fail an operational Eligibility or Behaviour profile while remaining perfectly valid input for mapping, remediation, audit, or exploratory query. Open-world reasoning and closed-world operational decisions coexist: closure is a property of a specific declaration, profile, or operation, never a property of the dataset as a whole.

## Decision

**Graph roles** (named graphs or equivalent provenance partitioning — recommended, not mandatory as physical graphs):

| Graph role | Purpose |
|---|---|
| Source | Faithful representation of ingested source data |
| Mapping | Confirmed mappings and mapping hypotheses |
| Declaration | Eligibility dimensions, Behaviour state spaces/transitions/policies |
| Assertion | Interpreted domain facts and occurrences |
| Entailment | Statements inferred under a declared entailment regime |
| Materialisation | Persisted derived views (current state, closures, candidate compatibility) |
| Validation | SHACL reports and governance findings |
| Execution | Decisions, transition executions, occupancy records |
| Projection-metadata | Description of external projections, indexes, generated artefacts |

**Statement provenance** properties cover: source artefact, extraction/mapping activity, asserting agent, observation/assertion time, valid time, confidence, mapping status, derivation method, entailment regime, validation profile, generation/projection profile, and supersession/retraction.

**Preservation rules**, adopted as governance defaults:

- Mapping never destroys the source assertion.
- Inference never silently becomes an authored assertion.
- Materialisation records its own derivation.
- Validation failure never deletes data.
- Retraction preserves history rather than erasing it.
- Every operational consumer declares which graph roles and profiles it trusts.

**Progressive semantic commitment**, non-destructive and coexisting with provenance:

```
captured → identified → partially mapped → semantically classified
    → validated for a stated use → operationally admitted
```

A statement useful for discovery, remediation, or audit while still short of "operationally admitted" is a normal, expected state, not a defect to be compiled away.

## Open sub-question

Whether this model requires new `fnd:` properties (a graph-role annotation property, a commitment-state property) is left open rather than decided here. Foundation is a complete T-Box already depended on by Vocabulary, Party, and Quantification; any edit to it is a deliberate, separately reviewed change, not something to fold silently into this ADR's adoption. This question is revisited when Eligibility or Behaviour's authoring (Gates 2–3) first needs a concrete provenance property Foundation does not yet provide.

## Consequences

- No layer's specification may assume a graph is "not real" until compiled or fully validated.
- Eligibility and Behaviour's own operational profiles (defined in their respective ADRs and READMEs) each state which graph roles and commitment level they require.
- The minimum a conforming deployment must physically implement is: distinguish source/mapping content from declaration/assertion content, and distinguish both from execution content. Finer-grained named-graph separation is a deployment choice, not a substrate requirement.
