<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Disposition: ADR-A51 Review

**Superseded:** ADR-A51 was superseded by ADR-A82 before ratification, so the "pending human ratification alongside ADR-A51" note below no longer applies. This disposition is historical. Current state: [phase-0-status.md](../status/phase-0-status.md), P0.1.3.

**Review:** [ADR-A51-review.md](ADR-A51-review.md)
**Reviewed artefacts:** [ADR-A51](../../architecture/decisions/ADR-A51-iri-and-identity-policy.md), [iri-policy.md](../../architecture/iri-policy.md), [rdf-sparql-patterns-guide.md](../../architecture/rdf-sparql-patterns-guide.md)
**Date:** 2026-09-23
**Disposed by:** Agent, autonomous session. Pending human ratification alongside ADR-A51 itself — see [phase-0-status.md](../status/phase-0-status.md).

This document records, finding by finding, what changed and why. It exists so the review does not have to be re-read in full to confirm a fix landed, and so a human reviewer can spot-check specific findings against the concrete diff rather than re-deriving the argument.

## 1. Verdict

Accepted in full. Every numbered finding (F-1 through F-17), every cross-document consistency row (review §5), and every technical issue raised against the patterns guide itself (review §6) that touches IRI/identity handling is resolved below. Two items are explicitly *not* resolved and are carried forward as open questions (§4 of this document): the URN-registration hygiene question (informal `urn-N` registration) and the public/dereferenceable identity decision — both are named in the review as decisions for a human, not defects to fix silently.

## 2. ADR-A51 findings (review §3)

| Finding | Severity | Verdict | Resolution |
|---|---|---|---|
| F-1 | Critical | Accepted | Rule 3 (environment-scoped base, rewritten on clone) deleted. New ADR-A51 rule 3: no IRI carries an environment component; environments are isolated by dataset/access control (ADR-A54), never by identity rewriting. |
| F-2 | Critical | Accepted | Content hash widened to a minimum of 128 bits (32 lowercase hex characters); "uniqueness by construction, no check needed" language removed. Registration now compares the full verification hash on every write to an existing content revision IRI — an O(1) assertion, not the deleted O(n) scan. |
| F-3 | Major | Accepted | New ADR-A51 §"Registry uniqueness is verified, not merely structural" states lineage `{family}:{localName}` allocation is a P1-shaped claim with an explicit owner, resolved once at lineage creation — the owner/family dimensions the old rule conflated with content-hash collision now have a stated home. |
| F-4 | Major | Accepted | Rule 2 rewritten to apply only to entity and lineage IRIs; content revision IRIs (`schemeVersion`), event IRIs (`epoch`/`seq`) and ADR-A54 infrastructure buckets are explicitly permitted to carry position information, matching OWL's own `owl:versionIRI` convention. |
| F-5 | Major | Accepted | `surrogate`/`surrogate-claimed` now mint with UUIDv4, never ULID/UUIDv7 (both embed a 48-bit millisecond timestamp). Stated as ADR-A51 rule 2's explicit exception list. `iri-policy.md` §4 example corrected to a UUIDv4 form. |
| F-6 | Major | Accepted | `derived-hash` restricted to non-sensitive, immutable composite keys. `surrogate-claimed` (new strategy) is the answer for sensitive/mutable keys, matching the patterns guide's own entity-identity default. |
| F-7 | Major | Accepted | `surrogate-claimed` added as a fourth entity strategy and stated as the *recommended default* for mutable/sensitive keys, aligning ADR-A51 with `rdf-sparql-patterns-guide.md` §8.4's existing default (opaque UUID + P1 key-claim registry) instead of contradicting it. |
| F-8 | Major | Accepted | Key-derived strategies now require the key to be **immutable**, not merely "stable". New "Key mutability and merges" section: one IRI becomes canonical, the other retained as a deprecated alias via `fnd:replacedBy` (never `owl:sameAs`), references migrated as a tracked operation. Source-system discriminators are named as provenance-local identity only. |
| F-9 | Major | Accepted | Content identity and event identity split into two IRI forms: content revision IRI (`.../rev/{schemeVersion}-{contentHash}`, identifies a state, safe to re-register after a revert) and event/promotion IRI (`.../evt/e{epoch}/{seq}`, identifies an occurrence, chained by `prevRev`, never cycles). Propagated into the patterns guide as the epoch-in-IRI fix (§3 below). |
| F-10 | Major | Accepted | `{class}` renamed to `{ns}`, a registered minting namespace, explicitly stated as never an `rdf:type` assertion and never renamed even if OWL classification changes. Applies to both ADR-A51 and `iri-policy.md`. |
| F-11 | Major | Accepted | "Alias graph, repointed atomically" replaced with a normative mechanism: `pat:current`, an object-property triple on the lineage's version row, updated by the same guarded CAS write as every other version-row field (per `rdf-sparql-patterns-guide.md` Part V). An optional materialised `{lineageIri}/current` graph is explicitly a projection, never the identity mechanism. |
| F-12 | Minor | Accepted | `iri-policy.md` §1 states scope (LATTICE-minted IRIs only), and the validator (§7) rejects mixed-case scheme/NID, percent-encoding of unreserved characters, non-NFC Unicode, and any `contentHash` under 32 hex characters. Component grammar for tuple encoding is specified as length-prefixed (carried over from the review's own recommendation; see `derived-hash`'s grammar row in `iri-policy.md` §4). |
| F-13 | Minor | Accepted | ADR-A51 rule 7: no `@base`/relative resolution against a `urn:` base; canonical lexical form is all-lowercase. Rule 9: public/dereferenceable identity is explicitly undecided and must not be assumed — carried forward as an open question, not resolved (this review does not pick `https://` mapping vs. URN-only; see §4). |
| F-14 | Minor | Accepted | `iri-policy.md` §3 fully specifies `contentHash`: RDFC-1.0 canonicalisation under a recorded profile version, a bounded work budget (poison-graph DoS protection), a stated self-reference placeholder rule, per-datatype literal canonicalisation, and an explicit rename from "semantic hash" to "`contentHash`" (it hashes syntax after normalisation, not semantic equivalence — the review's own point). |
| F-15 | Minor | Accepted | ADR-A51 rule 4 and `iri-policy.md` §6 rule 4: tenant segment is an immutable, opaque, allocated identifier, never a name; a reserved tenant exists for cross-tenant shared reference data. |
| F-16 | Minor | Accepted | `iri-policy.md` §5 (new): skolemization convention — deterministic via `natural-key`/`derived-hash` where a natural key exists, `surrogate-claimed`/`surrogate` otherwise, deterministic within one content revision. RDF 1.2 triple terms noted as an unevaluated alternative in the patterns guide's Appendix E item 10. |
| F-17 | Minor | Accepted | The inverted risk description ("requires an index from key to IRI") is not carried into the rewritten ADR — the corrected direction (an IRI-to-key index for support/debugging is itself PII and must be access-controlled) is implicit in `surrogate-claimed`'s design (the claim, not a reverse index, is what's access-controlled) and does not need restating as a named risk since the strategy that had the problem (`derived-hash` for sensitive keys) is no longer recommended for that case. |

## 3. Cross-document consistency (review §5)

| Topic | Verdict | Resolution |
|---|---|---|
| Entity IRI default (ADR-A51 vs. guide) | Resolved | ADR-A51 now adopts `surrogate-claimed` as its default for mutable/sensitive keys, identical in mechanism to the guide's opaque-UUID-plus-P1-claim default. Cross-referenced explicitly in both documents (ADR-A51's "Entity identity" table; guide §8.4 item 1). |
| Revision identity (content-addressed vs. position-addressed) | Resolved | Both are needed and now both exist, under different names: ADR-A51's content revision IRI (content-addressed, `fnd:Version`) and event/promotion IRI (position-addressed, an occurrence). The guide's receipt IRI is the event/promotion form; it now carries the epoch that makes it collision-safe across a restore. |
| Versions/times in IRIs | Resolved | ADR-A51 rule 2 scopes the ban to entity/lineage IRIs; content-revision `schemeVersion` and event `epoch`/`seq` are explicit, stated exceptions. |
| Hash for sensitive keys | Resolved | ADR-A51 adopts the guide's HMAC position: `derived-hash` is non-sensitive-only; `surrogate-claimed`'s claim uses a keyed (HMAC) hash, matching the guide's `claim_iri`. |
| IRI grammar (`urn:lattice:` vs. guide's `urn:g:`/`urn:rev:`/`urn:key:` illustrative forms) | Not unified, by design | These are two different grammars for two different purposes: ADR-A51/`iri-policy.md` govern *identity* (lineage, content revision, entity); the guide's `urn:g:`/`urn:rev:`/`urn:key:` forms are its own illustrative graph-naming convention for aggregate/infrastructure graphs, a concern ADR-A54 (dataset topology) owns. Reconciling the guide's illustrative examples with ADR-A54's full tenant/environment-scoped grammar is out of scope for this pass — it was not raised as a defect by the review, only the identity IRIs were. |
| Snapshot-per-revision graphs | Resolved | The guide's `urn:g:orders/1/{seq}` snapshot graph naming now also carries the epoch (`urn:g:orders/1/e{epoch}/{seq}`), for the same reason the receipt IRI does: a payload graph name must not be reusable after a restore either. |
| Receipt IRI omits the epoch (the bug within the guide itself) | Resolved | Fixed guide-wide: `rev_iri()`, all worked examples in Chapters 2, 10, 14, 18, 19, 20, 24, and Appendix A's vocabulary comment now use `urn:rev:{aggregate}/e{epoch}/{seq}`. Padding-width inconsistency (16 vs. 19 digits) was already stated as deliberate ("16 for legibility") and is left as documented, since it was not the defect — the missing epoch was. |

## 4. Broader guide review (review §6) — technical issues addressed

| Issue | Verdict | Resolution |
|---|---|---|
| S6 as-of query incorrect (compares retraction against the wrong graph) | Fixed | Chapter 11 §S6 rewritten: the `FILTER NOT EXISTS` now checks a later revision's *retraction delta graph* for the *same triple*, constrained to the same `pat:target` and to a `seq` strictly after the assertion and at or before the as-of position. |
| QP4 determinism test would fail (zero-width space not stripped) | Fixed | §8.1's `NormalizationPipeline` gains a `strip_default_ignorable` step (a regex removing U+200B/200C/200D/2060/FEFF) run before NFKC. QP4's test (Chapter 28) rewritten to assert against a second independent computation rather than a hardcoded literal, and to explain why the third input is the one that catches a regression. |
| Illustrative outputs don't match the code | Fixed | Chapter 5's `deterministic_iri("sku","widget-9")` and Chapter 6's `claim_iri(...)` example outputs were recomputed with the documented algorithm (Node.js `crypto`, matching the Python reference implementation byte-for-byte) rather than hand-typed. Chapter 6's function also now defaults to 16-byte (128-bit) truncation. |
| SHACL-SPARQL prefixes won't resolve (`sh:prefixes pat:` needs `sh:declare`) | Fixed | Appendix B gains a note and a worked `sh:declare` triple before the shapes block. |
| `NoForkShape`'s `sh:sparql` cost understated | Fixed | Appendix B gains a caveat cross-referencing §7.3's incremental-validator warning and naming the F5 standing query as the fallback for engines that can't afford commit-time `sh:sparql` validation. |
| S3 gap scan blind spot (missing prefix) | Fixed | Chapter 11 §S3 gains a second query comparing the stream's `MIN(?seq)` against a tracked retention low-water mark. |
| HMAC claim IRI margin (80 bits) | Fixed | Widened to 128 bits by default (see ADR-A51 findings table, F-2 margin logic applied consistently). |
| Document length / normative-vs-narrative split | Acknowledged, not done | Recorded as Appendix E item 9 (new): recommended once the guide's content stabilises past Phase 0, not attempted in this pass — a restructuring of this size risks introducing new drift under review-driven time pressure, and the review itself frames it as a "worth doing", not a defect. |

## 5. Explicitly not resolved (open questions carried forward)

1. **Public/dereferenceable identity.** ADR-A51 rule 9 states this is undecided rather than picking a default. A future ADR is required before anything gets an `https://` mapping.
2. **Formal `urn:` NID registration.** The review notes `urn:lattice` is not a registered NID per RFC 8141. Not fixed here — registering an NID (or switching to a registered `urn:uuid:`/`urn:oid:` style scheme) is a process decision, not a document fix, and the review itself calls it "a hygiene issue" rather than a defect blocking ratification.
3. **`ontology/persistence`'s `dal:graphIriTemplate` illustrative examples** (`urn:g:loan-application/{id}`) were checked against this review and found not to need changes — see §3's "IRI grammar" row above.

## 6. Files changed in this pass

- [ADR-A51-iri-and-identity-policy.md](../../architecture/decisions/ADR-A51-iri-and-identity-policy.md) — rewritten
- [iri-policy.md](../../architecture/iri-policy.md) — rewritten
- [rdf-sparql-patterns-guide.md](../../architecture/rdf-sparql-patterns-guide.md) — corrected in place (epoch-scoped revision/receipt IRIs; HMAC width; normalization pipeline; S6/S3 query fixes; SHACL `sh:declare` note; `fnd:replacedBy` merge policy; verified example outputs; new Appendix D/E entries)
- [phase-0-status.md](../status/phase-0-status.md) — updated to record the review and this disposition
- `ontology/persistence` and `tools/persistence` — checked against this review (§5 item 3); no changes required
