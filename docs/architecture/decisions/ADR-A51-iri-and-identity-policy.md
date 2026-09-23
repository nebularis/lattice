<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A51: IRI and Identity Policy

**Status:** Proposed
**Date:** 2026-09-23
**Related:** Architecture Review Appendix A, G-05, ADR-A74, ADR-A54, ADR-A68, `docs/architecture/iri-policy.md`
**Drafted by:** Agent, autonomous session (P0.1.3). Pending human ratification — see [phase-0-status.md](../../developer/status/phase-0-status.md).

## Context

`data-architecture.md` §5.2 currently rejects a graph-family registration when `(tenantId, projectId, graphIri)` collides on a different hash, family, or owner — a runtime conflict-rejection code path that exists only because identity is not structural. G-05 names the underlying gap: there is no normative IRI minting policy distinguishing a stable lineage identity from an immutable content-addressed revision, and no rule preventing personal data or timestamps leaking into IRIs.

## Decision

### Lineage, revision, and alias IRIs

| Kind | Form | Maps to | Mutability |
|---|---|---|---|
| Lineage IRI | `urn:lattice:{tenant}:{scope}:{family}:{localName}` | `fnd:PersistentIdentity` | Stable forever |
| Revision IRI | `{lineageIri}/rev/{profileVersion}-{semanticHash[0:16]}` | `fnd:Version` | Immutable, content-addressed |
| Alias graph | `{lineageIri}/current` | — | Repointed atomically at promotion |

The registry key becomes the revision IRI. Uniqueness is therefore structural: two different contents cannot collide on one IRI by construction, which deletes the `SurfaceGraphFamilyRegistry` conflict-rejection path entirely. `revisionHash` on a `GraphReference` becomes a verification field, not an identity field.

### Entity IRI minting strategies

| Strategy | Form | Use when | Risk if misused |
|---|---|---|---|
| `natural-key` | `{base}/{class}/{urlsafe(keyTuple)}` | Source has a stable business key | Key collision across source systems — mitigate with a source-system discriminator |
| `derived-hash` | `{base}/{class}/h/{sha256(canonical(keyTuple))[0:24]}` | Composite or sensitive keys, avoids PII in IRIs | Opacity; requires an index from key to IRI |
| `surrogate` | `{base}/{class}/s/{ULID}` | Genuinely identity-less nodes (reified span, extraction candidate) | Never idempotent — forbidden for any node re-ingestion must converge onto |

### Rules

1. IRIs never contain personal data (ADR-A68).
2. IRIs never contain a version number or timestamp — versioning lives exclusively in `fnd:Version` nodes.
3. IRIs are environment-scoped by their base segment; environment cloning rewrites that segment only.
4. `surrogate` minting in an ingestion plan requires an explicit declaration and justification (G9 — no silent surrogate use).

## Consequences

- `docs/architecture/iri-policy.md` is the normative reference for this ADR (created alongside it).
- ADR-A54's named-graph grammar and ADR-A63's `AuthoredGraphReference`/`RuntimeGraphReference` types both depend on the lineage/revision distinction defined here.
- A graph-name validator library with grammar tests is required (P0.3.7) before any dataset is created.
- `surrogate` minting is checked by the TCK (P0.5) and audited at ingestion-plan review time, not just at write time.
