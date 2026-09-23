<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# ADR-A51: IRI and Identity Policy

**Status:** Proposed
**Date:** 2026-09-23 (amended 2026-09-23 following review)
**Related:** Architecture Review Appendix A, G-05, ADR-A74, ADR-A54, ADR-A68, ADR-A75, `docs/architecture/iri-policy.md`, `docs/architecture/rdf-sparql-patterns-guide.md`
**Drafted by:** Agent, autonomous session (P0.1.3). Pending human ratification — see [phase-0-status.md](../../developer/status/phase-0-status.md).
**Amendment note:** The initial draft was reviewed in [docs/developer/review/ADR-A51-review.md](../../developer/review/ADR-A51-review.md), which found one critical conflict with RDF identity semantics (environment-scoped IRIs), one critical overclaim (uniqueness "by construction" with a truncated hash), and a set of internal contradictions and gaps against the `rdf-sparql-patterns-guide.md` entity-identity default. This revision resolves all of them; the disposition of each finding is recorded in [docs/developer/review/ADR-A51-review-disposition.md](../../developer/review/ADR-A51-review-disposition.md). Superseded content is struck from this document rather than kept alongside the correction, per the "say it once" convention.

## Context

`data-architecture.md` §5.2 currently rejects a graph-family registration when `(tenantId, projectId, graphIri)` collides on a different hash, family, or owner — a runtime conflict-rejection code path that exists only because identity is not structural. G-05 names the underlying gap: there is no normative IRI minting policy distinguishing a stable lineage identity from an immutable content-addressed revision, and no rule preventing personal data or timestamps leaking into IRIs.

The review additionally established that this policy must be consistent with `rdf-sparql-patterns-guide.md`, which independently derives an entity-identity default (opaque IRI plus a key-claim registry) and a revision/receipt model (content-addressed graphs plus position-addressed event receipts) from RDF and SPARQL's own constraints. Where the two disagreed, this revision adopts the guide's position, because it is derived from the same store-portability and GDPR constraints this ADR is trying to satisfy, and because ratifying two identity models under one platform would be a standing source of bugs.

## Decision

### Scope

This policy applies to LATTICE-minted IRIs. External vocabulary IRIs are never rewritten by LATTICE. TBox, shapes and vocabulary IRIs (Foundation and every ontology layer) are **never** tenant- or environment-scoped, and are unaffected by anything in this ADR.

### Graph-lineage identity: content and event are two identities, not one

A prior draft used one revision IRI for both "this content state" and "this write happened." That conflates a content-addressed identity with an event-addressed identity, and produces a cycle if content is ever reverted to a prior state (finding F-9). This ADR separates them:

| Kind | Form | Maps to | Mutability |
|---|---|---|---|
| Lineage IRI | `urn:lattice:{tenantId}:{scope}:{family}:{localName}` | `fnd:PersistentIdentity` | Stable forever |
| Content revision IRI | `{lineageIri}/rev/{schemeVersion}-{contentHash}` | `fnd:Version` (a content state) | Immutable, content-addressed |
| Event/promotion IRI | `{lineageIri}/evt/e{epoch}/{seq}` | a `prov:Activity` (a thing that happened) | Immutable, append-only, chained by `prevRev` |
| Current pointer | `pat:current` triple on the lineage's version row (normative); an optional materialised `{lineageIri}/current` graph is a projection, not the identity mechanism | — | Repointed by a single guarded write at promotion |

- **The content revision IRI identifies a state.** A revert from state B back to state A re-registers the *same* content revision IRI for A — this is correct and expected, not a collision.
- **The event/promotion IRI identifies an occurrence** — "lineage L was promoted to point at content revision R at position (epoch, seq)." A revert is a *new* event pointing at an *old* content revision. Event history (`prevRev` chaining) therefore never cycles, because it chains events, not content states.
- `epoch` is the dataset generation from `rdf-sparql-patterns-guide.md` §9 (G4) and §24.4: bumped on any restore, rebuild, re-key or migration, carried on every event IRI so a position from before a restore can never collide with a position minted after it. `seq` is the dense per-lineage event sequence from the same guide, zero-padded per `docs/architecture/iri-policy.md` §2.
- **The current pointer is a triple, not an aliasing graph.** RDF datasets have no aliasing mechanism (finding F-11); `{lineageIri}/current` named as if it were an addressable graph is meaningless without a stated mechanism. The normative mechanism is a `pat:current` object property on the lineage's version row, protected by the same guarded-write (CAS) primitive as everything else in the patterns guide. Tooling that needs a literal queryable graph may materialise `{lineageIri}/current` as a **projection** of that pointer, rebuilt on every promotion, never itself the source of truth.

### Registry uniqueness is verified, not merely structural

The original draft claimed identity was "structural by construction" and deleted the registry's conflict-rejection check entirely. With a hash truncated to 64 bits (`semanticHash[0:16]` as hex), an adversarial collision costs on the order of 2³² hash operations against attacker-influenced content (Surface contracts, mappings, uploaded ontologies) — not negligible (finding F-2). This ADR corrects both the width and the claim:

- **Content hash width is at least 128 bits** (32 lowercase hex characters), computed as specified in `docs/architecture/iri-policy.md` §3.
- **Registration compares the full verification hash, not just the IRI.** On registering an already-known content revision IRI, the registry compares the complete content hash (not the truncated form in the IRI) and rejects on mismatch. This is an O(1) assertion, not the O(n) conflict scan the prior rule performed, so the simplification the original draft claimed is real — it is just not "no check at all."
- **What the revision IRI construction actually removes** is the old rule's family and owner dimensions being conflated with content hash collision. Lineage `{family}:{localName}` allocation is a `pat:KeyClaim`-shaped registration (patterns guide P1) with an explicit owner, resolved once at lineage creation, not on every content write (finding F-3).

### Entity identity

| Strategy | Form | Use when | Risk if misused |
|---|---|---|---|
| `natural-key` | `{base}/{ns}/{urlsafe(keyTuple)}` | Source has an **immutable** (not merely "stable"), non-PII business key | Key collision across source systems — mitigate with a source-system discriminator; discriminated keys from different sources are a distinct identity until an explicit merge (see below) |
| `derived-hash` | `{base}/{ns}/h/{hex(sha256(schemeVersion\|ns\|enc(keyTuple)))[0:32]}` | **Non-sensitive**, immutable composite keys only | An unkeyed hash of a low-entropy personal key (email, national ID, phone, MRN) is reversible by dictionary and remains personal data under GDPR (Recital 26) — never use this strategy for sensitive keys |
| `surrogate-claimed` | `{base}/{ns}/s/{uuid4}` plus an HMAC-keyed `pat:KeyClaim` (patterns guide P1) on the natural key | **Recommended default** for entities with mutable or sensitive keys | The claim key must be per-tenant and never rotated for existing entities (rotation mints a new scheme version plus an old-to-new alias index, not a re-keyed IRI) |
| `surrogate` | `{base}/{ns}/s/{uuid4}` (unclaimed) | Genuinely identity-less nodes (a reified span, an extraction candidate) | Never idempotent — forbidden for any node re-ingestion must converge onto; declaration and justification required (Rule 6) |

`{ns}` is a registered **minting namespace** (for example `person`, `order`), not an `rdf:type` assertion. It is chosen once and never renamed — an entity's classification may change under OWL (multiple types, inferred types, refactored hierarchies), and identity must not depend on it (finding F-10). Readers and tools must never infer `rdf:type` from IRI structure.

`derived-hash` was previously described as "avoiding PII in IRIs" for composite or sensitive keys; that was wrong for exactly the sensitive case it named (finding F-6). `surrogate-claimed` is the strategy for that case, matching `rdf-sparql-patterns-guide.md`'s recommended default (opaque UUID entity IRI plus a P1 key-claim registry) — this ADR previously stated the opposite as the default and restricted surrogates to identity-less nodes only (finding F-7); both documents now agree.

### Key mutability and merges

Key-derived strategies (`natural-key`, `derived-hash`) require the key to be **immutable**, not merely "stable" — business keys are renamed, reissued and merged in practice, and "stable" invited exactly that ambiguity (finding F-8). When two IRIs are later found to denote one entity:

- One IRI becomes canonical.
- The other is retained as a deprecated alias carrying `fnd:replacedBy` pointing at the canonical IRI (not `owl:sameAs`, which under reasoning produces sameAs-clique explosion and cannot be retracted cleanly).
- References are migrated to the canonical IRI as a tracked operation, not silently.

A source-system discriminator (used to avoid cross-source key collision) creates provenance-local identity, not resolved cross-source identity. Cross-source entity resolution is a merge, following the rule above, layered on top of minting.

### Rules

1. IRIs never contain personal data (ADR-A68), including an unkeyed hash of a personal key and any timestamp that could be attributed to a data subject.
2. IRIs never contain a data version, generation number, or timestamp, **except** in a content revision IRI's `schemeVersion` segment, an event IRI's `epoch`/`seq` segments, or an ADR-A54 infrastructure graph bucket — all of which are identity-level positions, not data-version claims about the resource itself. Lineage and entity IRIs carry none of these.
3. No IRI carries an environment component. Environments are isolated by dataset and access control (ADR-A54), never by rewriting identity — an IRI denotes the same resource in every dataset it appears in, per RDF's own semantics (finding F-1). A tenant clone that needs synthetic, distinguishable data uses a distinct **tenant** (for example a `test-fixtures` tenant), not a rewritten base.
4. The tenant segment is an immutable, opaque allocated identifier, never a human-readable name — tenants rename, merge and split, and for single-person tenants a name would itself be personal data (finding F-15). A reserved tenant is allocated for shared reference data used across tenants.
5. `{ns}` (entity minting namespace) and `{family}` (graph lineage family) are registered tokens, never renamed, and never used by readers to infer `rdf:type` or graph classification (finding F-10).
6. `surrogate` (unclaimed) minting in an ingestion plan requires an explicit declaration and justification (G9 — no silent surrogate use). `surrogate-claimed` does not require this declaration, because it is claim-backed and therefore convergent on re-ingestion.
7. No `@base` or relative IRI resolution against a `urn:` base. RFC 3986 relative resolution against a rootless URN path produces silently wrong results (a reference like `<rev/abc>` resolving against `urn:lattice:...:x` does not mean what it looks like it means). Only the fully-written canonical form is ever stored or compared. The canonical lexical form is lowercase (`urn:lattice:...`, never `URN:LATTICE:...` — URN lexical equivalence is not RDF term equivalence).
8. Blank nodes arriving from ingestion are skolemized, deterministically where a natural key exists (`natural-key`/`derived-hash` rules apply) and with `surrogate-claimed`/`surrogate` otherwise, per the skolem-IRI form in `docs/architecture/iri-policy.md` §5. Blank nodes are never retained across a request boundary.
9. Public dereferenceable identity (an `https://` mapping for anything published outside the platform, e.g. via LDP/Solid) is **not** decided by this ADR and must not be assumed. `urn:` identity is internal-only until a separate decision states otherwise.

## Consequences

- `docs/architecture/iri-policy.md` is the normative grammar reference for this ADR: full component grammar, escaping and normalization rules, the content-hash specification, worked examples, and the skolemization convention (finding F-12, F-14, F-16).
- ADR-A54's named-graph grammar and ADR-A63's `AuthoredGraphReference`/`RuntimeGraphReference` types depend on the lineage/content-revision/event distinction defined here, not on the single revision IRI the original draft assumed.
- `rdf-sparql-patterns-guide.md`'s receipt IRIs must carry the dataset epoch (they did not; tracked and fixed as part of this same review pass, see the guide's own Appendix D).
- A graph-name validator library with grammar tests (P0.3.7) implements this ADR's grammar and `ontology/persistence`'s `dal:graphIriTemplate`/`dal:graphPrefix` values must validate against it.
- `surrogate` minting is checked by the TCK (P0.5) and audited at ingestion-plan review time; `surrogate-claimed` minting is checked by the patterns guide's K-series TCK suite (uniqueness torture tests) instead, since its correctness is a claim-registry property, not an ingestion-plan property.
- The merge/alias mechanism (`fnd:replacedBy`) requires a lookup path from any deprecated alias to its canonical IRI; this is a P1.2 dependency, not a Phase 0 implementation requirement, but the field and its semantics are fixed now so no IRI minted in Phase 0 needs to change shape later.

