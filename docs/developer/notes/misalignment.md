**Verdict: no. The document is a good headline summary but not a faithful or complete implementation of the sources.** It captures the core ideas correctly: the three clocks, the in-transaction counter, guarded `DELETE/INSERT` as the CAS primitive, meta/payload/receipt separation, and the F1–F6 table. But it also mis-states several source positions, mislabels or renumbers references, overclaims portability, and drops most of the adapter, TCK, and correctness content that makes the patterns safe to build.

Line numbers below refer to the implementation doc (L) or the named source.

---

## 1. Mis-stated (the sources say something different)

| # | Implementation doc | Sources |
|---|---|---|
| 1 | **L103:** the receipt outcome check is `ASK { <urn:rev:…> ?p ?o }`, by revision IRI. | The check is by the client's **txn id**: `ASK { GRAPH <urn:g:txn> { <urn:txn:…> :rev ?rev } }`. Checking the revision IRI only shows that *some* writer landed revision 42, not that *yours* did. That is the exact ambiguity F1 exists to remove. The txn-id claim node in its own small graph (reusing P1) is the fix, and the doc drops it. F6 also requires guarding on it in the same update (`FILTER NOT EXISTS`), not just checking it afterwards. |
| 2 | **L72:** transaction time is `recordedAt` + seq, "optionally `epoch`, optionally `opSeq`". | Epoch is **mandatory** ("Non-optional", G4/F3). `opSeq` is required whenever grain is event, and G1 recommends `(epoch, streamSeq, opSeq)` as the default. It also contradicts the doc's own F3 row. |
| 3 | **L226–229, L243:** P0–P7 "work on any SPARQL 1.1 store", dense sequences "work anywhere", and receipts and counters "work anywhere". | Rya/Halyard/federated stores: "Do not attempt guarded updates" (Uniqueness L231); "Do not attempt S1" (Ordering L291); "CAS itself is unsafe here" (Combine L229). Guarded update is only valid when a torture test passes, and P2/P3 depend on isolation. The doc also lists Rya as a Core SPI store (L319) while its own Core SPI requires atomic one-request semantics. |
| 4 | **L321:** "Neptune: MVCC (needs P3 sharded counter) … supports RDFMS (time-series)". | Sources describe Neptune as **lock-based on index ranges**. The guard must touch the same index range as the write, which P1 makes trivially true. Neptune Streams is the `NativeFeed`, and "don't mint your own dataset counter." **"RDFMS" appears in none of the six files.** |
| 5 | **L320:** TDB2 has "write-conflict detection" and "no dataset-global dense counter". | The opposite. TDB2 is the one store where a global counter is *affordable* (Ordering L92; Combine L227), giving `TOTAL_DENSE`. Writers are serialized, so there are no write-write conflicts to detect. It also pairs with rdf-delta as `NativeFeed`. |
| 6 | **L241:** A-Unique says "P3 for high-contention keys". | P3 is an **isolation fix** for write-skew under MVCC and *adds* false conflicts. High contention is **P6** (external allocator), which the row omits. |
| 7 | **L130:** A6 says per-subject sharding means "no contention". | The source adds "*provided the backend's conflict detection is per-statement*", and F12 says to shard the meta graph (`urn:g:meta/{hash % 64}`) and test it. Both are dropped. |
| 8 | **L121, L210, L275:** "dedicated graph per aggregate", "`<urn:meta>` graphs per aggregate", "Metadata graphs per aggregate". | The design is **one** meta graph (sharded) with one row per aggregate. A meta graph per aggregate doubles graph count, which is the proliferation problem in G6. The doc also attributes the meta separation to A74. In the sources it is a CAS design choice with a documented alternative and a capability prerequisite (atomic multi-graph write). |
| 9 | **L263, L227:** dataset-wide order is "derived, sparse" and "requires change feed". | Change feeds are **dense** (`TOTAL_DENSE`). HLC is `PARTIAL_CAUSAL` and needs no feed. Native commit position is `TOTAL_SPARSE`. The doc also calls global dense counters a flat anti-pattern (L93), but the source says that is fine on single-writer stores and to "measure" elsewhere. |
| 10 | **L82–89:** the counter SPARQL. | It is the pre-amendment G2 snippet. `?ctr` is **never bound** (the source has `BIND(<urn:ctr:stream:orders> AS ?ctr)`), so as written it would increment every counter in the graph. It uses per-commit `commitSeq` (which G1 says doesn't solve the problem), server-side `?n+1` (which F8 moves to the client), and omits `recordedAt` and the idempotency guard. The Combine "corrected pattern", the most implementable artifact in the set, is nowhere in the doc. |
| 11 | **L153:** "No `now()` inside guards, effects…". | The corrected pattern binds `NOW()` for `:recordedAt`, and F13 calls it "fine as transaction time". The rule is not in the sources and conflicts with them. It needs an explicit decision, for example inject time as a parameter, which makes `recordedAt` the client's clock. The rule also appears in two different forms (L153 vs L246). |
| 12 | **L47, L117:** reference labels. | The doc cites P1–P7 (source is **P0–P7**), concurrency 1.1–1.5 (source has 1.1–1.6 plus §2–5), and F1–F6 (source has **F1–F13**). "Derive the ETag (1.2)" and "Immutable receipt chain (1.2)" are Combine F4/F5, not concurrency §1.2. "`WHERE NOT EXISTS`" (L59) should be `FILTER NOT EXISTS`. |
| 13 | **Part 3 catalog.** | K1–K7 renumbers P0–P7, **drops P3**, and collides with the source's own K1–K4, which are a taxonomy of uniqueness *kinds*. O1–O5 is redefined: the source has O2 = causal, O3 = valid time, O4 = point-in-time, O5 = ordered collections. The doc swaps O2/O3, shifts point-in-time to O5, and **drops ordered collections** entirely. "15 sub-patterns" is actually 28, and "7 patterns" is 8. |

## 2. Mispositioned or misunderstood

- **A74 vs P6/S8.** L209 and L210 say "no authoritative UNIQUE in PostgreSQL" and that Kafka offsets are "derived, not canonical". But P6 makes the external unique index authoritative with RDF as projection. S8 says an external sequencer is "frequently the correct answer and shouldn't be treated as a fallback", and it is mandatory for Rya/Halyard. The doc's own Part 1 (L58, L111) endorses Postgres/Kafka. This needs an explicit ADR carve-out.
- **L211 reverses the roles.** In the sources, guards become belt-and-braces when a queue or lock is primary. Guarded update is primary only when the torture test grants `cas: linearizable`, and a lock needs a fencing token written into the version.
- **A75's SPI is the biggest structural gap.** The doc defines three feature tiers and says "isolation level (document which)". The sources say capability flags are *claims verified by a TCK*. A planner then picks the strongest strategy and **fails at startup** if `min_level` isn't met. The SPI is missing:
  - `singleWriter`, `detectsWriteWriteConflict`, `multiRequestTx`, `maxIsolation`, `atomicUpdateRequest`
  - `statementLevelConflictDetection`, `reportsAffectedRows`, `quadsInUpdateTemplates`
  - `commitValidation`, dense change feed, time travel, and `bulkLoadBypasses…`
  - the `CasResult` states `applied | conflict | unknown`, and `resolve(txnId)`
  - the strategies ExplicitTransaction, NativePromote, HttpPrecondition and PatchLog, so guarded update looks like the only CAS route
- **L160–199 (bi-temporal, in-place, deletes) versus G5, F9 and F10.**
  - Letting in-place update be "configurable" forfeits replay, as-of and CDC unless that is declared per graph (G5: "half-measures make O4 unanswerable").
  - F9 forces an explicit choice among receipt log, patch log and snapshot-per-revision, and the doc omits it.
  - "Decision records are append-only" conflicts with T3 whole-graph replace, which discards the diff.
  - The deletion policy never mentions F10: without a tombstone, `:seq` resets and receipt IRIs get reused.
- **Phase sequencing is internally inconsistent.**
  - Part 0 says Phase 0.4 (identity) depends on uniqueness, but L337–338 put K in 0.3 and O in 0.4.
  - T in 0.2 already contains the dense per-aggregate counter, which the source says is the *same mechanism* as CAS.
  - T's create path is "a uniqueness problem, not a CAS problem" (Combine L215), so it depends on K.
  - A TDB2-only walking skeleton can't exercise the MVCC hazards (P3, F12, write-skew).
- **Open questions 2–5 are largely answered by the sources:**
  - Q2 is the epoch bump, with the epoch part of the cursor and ETag and stale cursors triggering `EpochChanged` and a resync.
  - Q3 is per-stream dense with tenant as the stream key, global position via HLC or feed, and per-stream gap scan for completeness.
  - Q4 is that RDF4J ShaclSail and GraphDB validate incrementally and Stardog ICV rejects at commit. TDB2 and Neptune have none, which is why P1 exists, and P7 is the backstop regardless.
  - Q5 is S6's preference order: native time travel, then `validFrom`/`validTo`, then log replay for audit only.

## 3. Omitted

**Correctness-critical**
- **F7–F13.** Pin one datatype and `sh:maxCount 1` on `:seq`, `:epoch` and `:head`; client-computed arithmetic; the F9 fork; tombstones; OPTIONAL cross-product; sharded meta graph; `occurredAt`.
- **G2's reason.** The reorder hole is why pre-allocation loses events for `seq > watermark` readers. Also missing are the reader-side rules and the gating reorder-probe test.
- **`opSeq` must come from the client.** `NOW()` is constant within an update, so the store can't mint distinct ordinals.
- **Atomic ≠ serializable.** `FILTER NOT EXISTS` is write-skew-prone; ownership monotonicity is what makes the post-`ASK` race-free; the protocol has no multi-request transactions.
- **Bootstrap before first write.** Eager counter init and pre-created meta rows, because lazy `OPTIONAL` init races.
- **Sorted acquisition** of claims and counters to avoid deadlock; cross-aggregate atomicity gating; and the source's warning that silently degrading it is "the single worst thing a pluggable adapter can do".
- **Retry rules.** Never blindly replay; `unknown` means call `resolve`; jitter; `ConflictExhausted`.
- **Normalization pipeline.** Frozen, versioned, and shared by the write path, SHACL and backfill. This is the source's "where uniqueness actually breaks", and it maps directly onto Phase 0.4 canonicalization. Stream-key normalization and versioning are missing for the same reason.
- **OWL `InverseFunctionalProperty` is not a constraint.** It merges via `owl:sameAs`, which matters for the ontology architecture.

**Structural**
- All four **TCKs**, with their gating tests: single-key torture, reorder probe, valid-vs-transaction-time, lost-update, and ambiguous-timeout replay.
- **Always-on reconciler and order auditor**: P7 isn't flagged as mandatory, and the gap scan (S3) and standing fork-detection alert are missing.
- **Bulk/backfill pipeline.** Bulk load bypasses constraints and counters, which matters directly for Phase 1 ingestion.
- S2 keyset pagination, S3–S8, the SPARQL gotchas table, order levels, the dataset-tier table with its HLC + seq-contiguity default, G5 and G6, and the concurrency variants.
- Field-level versions, content-hash ETags, HTTP mapping (`W/"epoch-seq"`, 412/204, `If-None-Match: *`), lease locks, and CRDT merge.

**LATTICE-specific content in `optimistic-concurrency-in-rdf.md`** (not cited anywhere; the appendix cites only the underscore version): named graphs imply aggregate roots, which imply a way for ontology authors to define membership. That needs a new substrate layer (`quantification` + `surface`) and adds modelling load. It also notes value-based CAS as "not applicable for user data, potentially usable for internal nodes", and covers the triple-level fallback when no aggregate boundary exists. **The doc assumes aggregate = graph but proposes no ADR for how aggregate and stream boundaries are defined**, which is probably the largest missing decision.

## 4. Could not verify from these files

- Part 1.2 rules 1, 3, 4, 5 (PreparedQuery, Cursor, L2, L8) and the Architecture Review rationale in 1.3–1.4.
- `fnd:supersedes`; the sources use `ex:supersedes`.
- Two collisions to check:
  - Your "Cursor" (a memory-bounded result iterator) is a different thing from the source's Cursor, a resume position `(epoch, seq, opSeq)`.
  - The `uuid4()` lint ban (L324) must not hit identity minting, since Uniqueness recommends opaque UUID entity IRIs.

## 5. Tensions in the sources themselves

- **Append vs CAS.** Ordering's S1 is server-assigned next-seq (append, no expected version). Combine's F8 is client-computed expected-version CAS. Ingestion and decision records want append (`Expectation.any`) and aggregate replace wants CAS. The doc merges them as "one mechanism" without saying which use case gets which. This is my inference from reading the two together, not an explicit source statement.
- **P0 vs P1 and PII.** P0 says hashing an email into an IRI leaks PII. P1's claim-node IRI is a hash of the email. The doc's "for mutable or PII keys" inherits the ambiguity.

## What is faithful

The following are accurately carried over:
- the three clocks and the dense-per-stream / sparse-across-streams decision
- the in-transaction counter insight
- the protocol's missing return value
- the F1–F6 severities and fixes
- A1–A5 and A7
- HTTP-level CAS
- the portability gotchas
- P0–P3 and P5–P7 as concepts

## Suggested fixes, in order

1. Correct items 1–13 in §1.
2. Add a source-to-doc traceability appendix, so omissions are visible.
3. Replace the L82 snippet with the Combine corrected pattern.
4. Rewrite A75 as capabilities + strategies + `min_level` + TCK.
5. Add ADRs for aggregate and stream boundaries, normalization, F9 (receipt vs patch vs snapshot), and the A74/P6 carve-out.
6. Retire open questions 2–5, or restate what is still open.

I can draft the traceability matrix or a redline of the specific passages as a file if that would help.