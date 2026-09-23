<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# IRI and Identity Policy

**Normative for:** [ADR-A51](decisions/ADR-A51-iri-and-identity-policy.md)
**Status:** Proposed, pending human ratification alongside ADR-A51
**Amended:** 2026-09-23, following [docs/developer/review/ADR-A51-review.md](../developer/review/ADR-A51-review.md). See [ADR-A51-review-disposition.md](../developer/review/ADR-A51-review-disposition.md) for the finding-by-finding resolution.

This document is the operational reference for minting and interpreting IRIs across the LATTICE platform. ADR-A51 records the decision; this document records the grammar, encoding rules and worked examples so implementers and the graph-name validator (P0.3.7) share one source. Nothing here departs from ADR-A51; where the two could be read as disagreeing, ADR-A51 controls.

## 1. Scope and non-goals

This grammar applies to LATTICE-minted `urn:lattice:` and `urn:` entity IRIs. It does **not** apply to:

- TBox, shapes or vocabulary IRIs (Foundation and every ontology layer), which use their own `https://www.nebularis.org/...` namespaces and are never tenant- or environment-scoped.
- External IRIs referenced by, but not minted by, LATTICE.
- Public, dereferenceable identifiers. This grammar is internal-only (`urn:` scheme); whether anything gets an `https://` public identity is a separate, not-yet-taken decision (ADR-A51 rule 9).

## 2. Graph-lineage identity

| Kind | Grammar | Example |
|---|---|---|
| Lineage IRI | `urn:lattice:{tenantId}:{scope}:{family}:{localName}` | `urn:lattice:t7f3a2:project-42:surface:policy-eligibility` |
| Content revision IRI | `{lineageIri}/rev/{schemeVersion}-{contentHash}` | `urn:lattice:t7f3a2:project-42:surface:policy-eligibility/rev/2-9f3a1c2b7e4d5601a8b6c4d2e0f1a9b7` |
| Event/promotion IRI | `{lineageIri}/evt/e{epoch}/{seq}` | `urn:lattice:t7f3a2:project-42:surface:policy-eligibility/evt/e3/0000000000000042` |
| Current pointer | `pat:current` triple on the lineage's version row; optional materialised projection at `{lineageIri}/current` | — |

- `{tenantId}` is an immutable, opaque, allocated identifier (ADR-A51 rule 4), never a human-readable tenant name. `{scope}` is a project or environment id per ADR-A63, itself immutable and opaque; it is part of identity here because it names *which authoring or runtime context this lineage belongs to*, not because it is rewritten on clone — cloning creates a **new** environment with its own scope segment and, where content must be copied, new lineages under it, never a rewrite of an existing lineage's segment (see ADR-A51 rule 3; this corrects the original draft's "rewrite on clone" rule, finding F-1).
- **Content revision IRI** identifies a state of the content. Re-registering identical content (including after a revert) yields the *same* content revision IRI — this is correct: content identity and event identity are separate (ADR-A51, finding F-9).
  - `{schemeVersion}` is the canonicalisation/minting scheme version (an integer), never a data version.
  - `{contentHash}` is at least 128 bits (32 lowercase hex characters). See §3 for its exact specification.
  - On registering an already-known content revision IRI, the registry **compares the full verification hash** (not the possibly-truncated IRI form) and rejects on mismatch (ADR-A51, finding F-2). This is the one runtime check the design keeps; it costs one lookup, not a scan.
- **Event/promotion IRI** identifies an occurrence — "this lineage was promoted to point at this content revision, at this position." It is immutable, append-only, and chained by `pat:prevRev` to the previous event for the same lineage, exactly as `rdf-sparql-patterns-guide.md` Part V specifies for aggregate streams.
  - `{epoch}` is the dataset generation (`rdf-sparql-patterns-guide.md` §9, G4): an integer bumped on any restore, rebuild, re-key or migration. Carrying it in the IRI, not only as a co-resident property, is what stops a post-restore event from reusing a pre-restore IRI (ADR-A51, finding F-9 cross-referencing the guide's F3).
  - `{seq}` is the dense per-lineage sequence, zero-padded to 19 digits (fixed width for a 64-bit signed sequence; see the patterns guide §13 for why zero-padding matters for lexicographic sort and range scans).
- **Current pointer.** `pat:current` is a normal object-property triple on the lineage's version row (the same version row the patterns guide's Part V describes), updated by the same guarded CAS write as every other version-row field. It is not a second named graph, and no store-level "aliasing" mechanism is assumed (ADR-A51, finding F-11). A materialised `{lineageIri}/current` graph, if a consumer needs one, is rebuilt from the pointer on every promotion — it is a cache, never the source of truth.

## 3. Content hash specification

`{contentHash}` (and any other place this document calls for a "semantic hash" or "content hash") is defined as follows, closing the gaps the review identified (finding F-14):

1. **Canonicalisation algorithm:** RDF Dataset Canonicalization (RDFC-1.0), per `ontology-architecture.md` §10, under the dataset's recorded `canonicalisationProfileVersion`. Hashes computed under different profile versions are never compared; `{schemeVersion}` in the content revision IRI **is** the canonicalisation profile version.
2. **Complexity bound:** canonicalisation is run under a bounded work budget (blank-node graph complexity limit). A graph that exceeds the budget is rejected before hashing, not hashed on a best-effort basis — an unbounded adversarial "poison graph" is a denial-of-service vector on registration otherwise.
3. **Self-reference:** if the canonicalised content contains its own content revision IRI or lineage IRI (for example an `owl:versionIRI` in an ontology header, or a provenance triple naming the graph being hashed), that occurrence is replaced with a fixed placeholder IRI before hashing. Otherwise the hash input depends on its own output.
4. **Literal canonicalisation:** lexical forms are canonicalised per datatype before hashing (`"1"^^xsd:integer` and `"01"^^xsd:integer` hash identically; two OWL-equivalent but syntactically different axiomatisations do **not** — this hashes syntax after normalisation, not semantic equivalence). Call this **`contentHash`**, not "semantic hash": it is not a claim about meaning-level equivalence.
5. **Environment exclusion:** because no LATTICE-minted IRI carries an environment component (ADR-A51 rule 3), this is not a special case the hash needs to handle — content hashes identically regardless of which dataset it is loaded into.
6. **Encoding:** lowercase hexadecimal, minimum 128 bits (32 characters). A shorter, explicitly-labelled digest (for example a 64-bit prefix used only for a human-readable log line) is never used as the identity-bearing form.

## 4. Entity identity

| Strategy | Grammar | Example | Notes |
|---|---|---|---|
| `natural-key` | `{base}/{ns}/{urlsafe(keyTuple)}` | `urn:lattice:t7f3a2:prod/party/Policy/POL-000123` | Immutable, non-PII key only |
| `derived-hash` | `{base}/{ns}/h/{hex(sha256(v{schemeVersion}\|{ns}\|enc(keyTuple)))[0:32]}` | `urn:lattice:t7f3a2:prod/party/Claimant/h/3fa1e9c0b6d8425719ac0e77c2b4f108` | Non-sensitive keys only — unkeyed hashes of personal keys are reversible and remain personal data |
| `surrogate-claimed` | `{base}/{ns}/s/{uuid4}` + an HMAC-keyed `pat:KeyClaim` on the natural key | `urn:lattice:t7f3a2:prod/eligibility/Claimant/s/2b6f9e34-9a41-4d7a-8b2e-3f6c1a9d7e40` | **Recommended default** for mutable or sensitive keys |
| `surrogate` (unclaimed) | `{base}/{ns}/s/{uuid4}` | `urn:lattice:t7f3a2:prod/eligibility/ExtractionCandidate/s/01j9z8q3-k4m5-n6p7-q8r9-s0t1u2v3w4x5` (rendered as a UUIDv4, not a ULID — see §6) | Identity-less nodes only; declared and justified per plan |

`{ns}` is a registered minting namespace, never an `rdf:type` (ADR-A51 rule 5). Two different classifications of "the same" entity under OWL reasoning or a later ontology refactor never change `{ns}`, because identity must survive reclassification (finding F-10).

## 5. Skolemization

Blank nodes arriving from ingestion (RDF 1.1 §3.5) are skolemized before they cross a request boundary:

- Where a natural key exists, skolemize deterministically using the `natural-key` or `derived-hash` form above, computed from that key.
- Where no natural key exists, skolemize with `surrogate-claimed` (preferred, if the node has any claimable identifying attribute) or `surrogate` (an unclaimed, identity-less node — for example a reified span or an extraction candidate), never a raw ULID (see §6).
- Skolem IRIs are deterministic within one content revision: the same blank-node graph canonicalised twice produces the same skolem IRIs, because they are derived from the canonical blank-node label, not randomly assigned per run.

## 6. Rules (normative — mirrors ADR-A51 §Rules; see that ADR for rationale)

1. No IRI contains personal data. Use `derived-hash` only for non-sensitive keys; use `surrogate-claimed` (an opaque IRI plus an access-controlled, HMAC-keyed claim) for sensitive or mutable keys, never an unkeyed hash of a personal key (ADR-A68).
2. No IRI contains a data version, generation number, or timestamp, except a content revision IRI's `schemeVersion`, an event IRI's `epoch`/`seq`, or an ADR-A54 infrastructure graph bucket. `surrogate` and `surrogate-claimed` use UUIDv4, never ULID or UUIDv7 — both embed a millisecond timestamp in their first 48 bits, which is trivially decodable and can itself be personal data (for example, the creation time of a specific patient record).
3. No IRI carries an environment component. Environments are isolated by dataset and access control (ADR-A54), never by identity rewriting.
4. The tenant segment is an immutable, opaque, allocated identifier, never a name. A reserved tenant exists for cross-tenant shared reference data.
5. `{ns}` and `{family}` are registered tokens, never renamed, never used to infer `rdf:type` or graph classification.
6. `surrogate` (unclaimed) minting requires an explicit declaration and justification in the ingestion plan that uses it. `surrogate-claimed` does not, because it is claim-backed and convergent by construction.
7. No `@base` or relative IRI resolution against a `urn:` base — only the fully-written canonical form is stored or compared. The canonical lexical form is all-lowercase.
8. Registry uniqueness at the content-revision level is enforced by full-hash comparison on write, not merely assumed from IRI non-collision (§2).
9. Public, dereferenceable identity is undecided; do not assume one.

## 7. Validator

A graph-name validator library (P0.3.7) implements this grammar and is the single source of truth for parsing and formatting these forms — `ontology/persistence`'s `dal:graphIriTemplate` and `dal:graphPrefix` values must be well-formed instances of this same grammar, not a competing one. The validator rejects: mixed-case scheme or NID segments, percent-encoding of unreserved characters, non-NFC Unicode in any component, and any `contentHash` shorter than 32 hex characters.

