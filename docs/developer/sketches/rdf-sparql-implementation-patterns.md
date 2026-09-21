# RDF/SPARQL Implementation Patterns — Sketch

**Status:** Design sketch. This document surveys the problem space for RDF/SPARQL data management and query discipline at LATTICE, proposes a solution approach grounded in portable SPARQL patterns, and identifies the decisions and design patterns needed to make A74 (graph-primary) and A75 (store SPI) concrete and implementable.

**Prerequisite for:** Epic decomposition; Phase 0 and 1 planning; store SPI specification (C-02)

---

## Part 0 — Problem statement

### The gap

`solution-design-specification.md`, `data-architecture.md`, and `ontology-architecture.md` together describe a system where:

- RDF is the system of record (A74)
- Multiple stores can be plugged in via an SPI (A75: Jena/Fuseki reference implementation)
- Data flows through four planes: design-time, deployment, ingestion, operation, and feedback
- MORK decisions, provenance, lineage, and lifecycle are captured as RDF

**What is missing:** A coherent set of **data patterns and query discipline** that make these goals achievable in practice. Specifically:

1. **Uniqueness at scale** — how to enforce natural and surrogate keys in RDF without silent lost updates or inefficient scans
2. **Ordering and causality** — how to order events both causally (per-stream) and temporally (across the system), with ordering that survives backup/restore
3. **Concurrency control** — how to implement compare-and-set (CAS) atomicity across multiple data writers without relying on store-specific features
4. **Bi-temporal modeling** — whether and how to record valid-time, transaction-time, and logical-time separately, and which is configurable vs. mandated
5. **SPARQL query safety** — how to prevent injection, ensure determinism, and handle edge cases in a portable way
6. **Storage lifecycle** — deletion policy, versioning strategy, and archive/retention — which parts are platform policy vs. application choice

### Why this matters

These patterns are **blocking concerns for Phase 0 and 1:**

- **Phase 0.2 (Walking skeleton)** needs a working store with CAS semantics and ordered writes, or state mutations silently collide
- **Phase 0.4 (Canonicalization & identity)** depends on a uniqueness mechanism that survives concurrent writers
- **Phase 0.5 (Component integration)** needs end-to-end testing of SPARQL guards and ordering guarantees
- **Phase 1 (Ingestion)** needs ordered delivery of mapped data to maintain per-aggregate causal consistency
- **Phase 2+ (Runtime operations)** needs bi-temporal queries that don't timeout and decision records that don't lose fidelity

---

## Part 1 — Solution overview: portable SPARQL patterns

The approach is **not** to mandate a single store or distribution model. Instead, it is to define **reusable, vendor-independent SPARQL patterns** that work on any store claiming SPARQL 1.1 compliance, and to identify where store-specific behaviour must be tested and documented.

### 1.1 Core patterns

#### **Pattern K: Uniqueness** (Uniqueness in RDF.md, P1–P7)

**Problem:** How to enforce that a key (surrogate or natural) is claimed by exactly one entity, without race conditions or lost updates.

**Solution:** Two-tier approach per key scope:

1. **Deterministic IRIs (P0)** — for immutable, non-PII keys, hash the key into the IRI itself. Concurrent inserts converge (idempotent).
2. **Key-claim registry (P1)** — for mutable or PII keys, create a `<urn:key:…>` node per key value and enforce `sh:maxCount 1` on the claim. Index for O(1) lookup.
3. **Guarded update in one request (P2)** — `INSERT … WHERE NOT EXISTS …` is a conditional write. Execute claim insert and payload insert atomically.
4. **Materialize the write conflict (P3)** — on MVCC stores, force conflicting writers to hit the same statement (sharded counter) to bypass snapshot isolation.
5. **SHACL validation (P5)** — lean on `sh:maxCount 1` for incremental validation; use `sh:sparql` for cross-node checks with the caveat that it may trigger full-graph re-validation.
6. **External allocator (P6)** — for truly hot keys (high-contention ID minting), use a Postgres row, Redis `SET NX`, or Kafka topic as the lock; write to RDF idempotently.
7. **Detect-and-reconcile (P7)** — nightly/streaming scan for collided keys → quarantine + human decision or merge policy.

**Applies to:** Entity de-duplication on ingest; natural key enforcement (email, orderNumber per tenant); surrogate key (UUIDs) paired with natural key claims.

**Trade-off:** False conflicts in sharded counters under high load. Tune shard count (e.g., 1024 shards) based on write rate.

#### **Pattern O: Ordering and causality** (Ordering in RDF.md, O1–O5)

**Problem:** Five distinct "ordering" requirements get conflated; single solution doesn't fit all. Events must be ordered causally (per entity), temporally (globally), and queryably (for replay/sync) — but these are different clocks.

**Solution:** Three separate mechanisms, kept physically distinct:

1. **Valid time** (`ex:occurredAt`) — when it happened in the world. Late/backfilled data is normal. Never assume commit order is valid order.
2. **Transaction time** (`ex:recordedAt` + per-stream `seq`, optionally `epoch`, optionally `opSeq`) — when the system learned it. Monotonic, append-only, used for audit and replay.
3. **Logical/causal time** (per-stream counters, version pointers, `fnd:supersedes`) — happened-before, independent of wall clocks.

**Key decision:** Per-stream vs. per-dataset ordering.

- **Per-stream dense sequence (required)** — stream = entity, aggregate, tenant, or topic. Cheap, shardable, gap-free. Concurrent writers to different streams never contend on the counter.
- **Dataset-wide total order (optional)** — do **not** mint it in the write transaction. Derive from the store's change feed, or accept sparse HLC order.

**Critical implementation detail:** Put the counter read-and-increment **in the same transaction as the payload write**, on a single shared statement. This ensures allocation order == commit order and is dense with no abandoned values.

```sparql
DELETE { GRAPH <urn:meta> { ?ctr ex:next ?n } }
INSERT { GRAPH <urn:meta> { ?ctr ex:next ?n1 }
         GRAPH ?cg { … payload … }
         GRAPH <urn:log> { ?cg ex:epoch 3 ; ex:commitSeq ?n } }
WHERE  { GRAPH <urn:meta> { ?ctr ex:next ?n }
         BIND(?n + 1 AS ?n1) }
```

**Applies to:** Event sourcing; audit logs; MORK decision records; ingestion pipelines; state mutations.

**Anti-pattern:** Pre-allocating sequence numbers before the transaction; using `NOW()` as an ordering mechanism; global dataset-wide dense counters (contention point).

#### **Pattern C: Concurrency control** (Optimistic concurrency in RDF stores.md, 1.1–1.5)

**Problem:** SPARQL 1.1 Protocol has no `If-Match`, no `RETURNING`, no affected-row count. An update endpoint replies `200`/`204` whether it changed anything or nothing. Two concurrent writers can both see "success" when only one actually won.

**Solution:** Guarded `DELETE/INSERT … WHERE` as the CAS primitive, plus outcome verification:

1. **Guarded update (1.1)** — Put the version guard (e.g., `FILTER(?etag = "E1")`) in the `WHERE` clause. No solutions in `WHERE` ⇒ no-op and silent success (the problem). One request = one transaction (works on most stores).

2. **Append-only receipt log (1.2)** — Every successful write produces an immutable receipt `<urn:rev:orders/1/…>` with metadata. Check receipt with `ASK { GRAPH <urn:g:txlog> { <urn:rev:…> ?p ?o } }` to learn outcome. Idempotent and race-free across retries and crashes.

3. **Derive the ETag (1.2)** — Don't store `"E42"` separately; derive it from `{epoch}-{seq}`. One source of truth, HTTP and SPARQL agree by construction.

4. **Immutable receipt chain (1.2)** — `<urn:rev:orders/1/…> :prevRev <urn:rev:orders/1/…previous>` as IRIs, not strings. Verifiable chain catches forks (proof of lost update) via `GROUP BY ?prev HAVING (COUNT(*) > 1)`.

5. **HTTP-level CAS (1.4)** — If each aggregate is one graph, push concurrency control to HTTP: GSP `PUT + If-Match`, LDP `ETag` + conditional, or Solid N3 Patch with built-in precondition semantics.

6. **Escape hatches for high contention (1.5)** — Single-writer queue per aggregate (Kafka partitioning); external lock (Postgres row, etcd, Redis with fencing tokens); event sourcing with patch logs (RDF Delta, TerminusDB).

**Applies to:** Any state mutation; aggregate state machines; MORK review outcomes; claims processing.

**Portability gotchas:** Dataset scoping (`WITH`/`USING`); blank nodes (not addressable across requests); guard cardinality (must be functional); never rely on `INSERT DATA` failing for existing triple.

#### **Pattern T: Combined concurrency and ordering** (Combine Concurrency And Ordering Plan.md, A1–A7, F1–F6)

**Problem:** The above patterns interact. A74 (graph-primary) separates metadata in a separate graph, which buys several properties but introduces new failure modes.

**Solution:** Use version metadata in a dedicated graph per aggregate, combined with dense per-stream sequencing:

**What this buys (A1–A7):**

- **A1:** Counter read-modify-write and CAS guard are the same operation on the same triple. One materialized write conflict serves both.
- **A2:** O(1) guard regardless of aggregate size (metadata separate from payload).
- **A3:** Whole-graph replace safe (payload can be deleted and re-created; version counter survives).
- **A4:** Head pointer via single-triple lookup (no `MAX()`/`GROUP BY`).
- **A5:** Different retention policies for payload (mutable), meta (mutable point), receipts (append-only).
- **A6:** Per-subject sharding (different aggregates touch different subjects, no contention).
- **A7:** Localizes where to be careful (exactly one statement per aggregate contended).

**Critical findings (F1–F6) and fixes:**

| Finding | Severity | Fix |
|---------|----------|-----|
| F1: CAS outcome unobservable | CRITICAL | Use receipt node + `ASK` for idempotent outcome check |
| F2: Revision IRI collides across aggregates | CRITICAL | Derive from full position: `urn:rev:orders/1/0000000000000042` (zero-padded) |
| F3: No epoch; restore resets seq and breaks consumers | CRITICAL | Add `:epoch` to guard, meta row, every receipt, ETag; bump on restore |
| F4: `:etag` and `:seq` two sources of truth | MAJOR | Derive ETag: `{epoch}-{seq}`; store only `:epoch` + `:seq` + `:head` |
| F5: `:prev` is a string, chain not traversable | MAJOR | `:prevRev <urn:rev:…>` as IRI for verifiable chain + fork detection |
| F6: Idempotency key written but never checked | MAJOR | Include `:txn` id as claim node, check in outcome ASK |

**Applies to:** LATTICE's A74 (graph-primary) implementation; Phase 0.2 walking skeleton; any system that combines concurrent writers with dense ordering.

### 1.2 SPARQL query discipline

**Problem:** SPARQL enables unsafe patterns that lead to injection, non-determinism, and unexpected costs at scale.

**Solution:** Enforce five rules:

1. **No string concatenation into SPARQL.** `PreparedQuery` + `Params` only. Prevents injection.
2. **No `now()` inside guards, effects, or canonicalization.** Time is an input. Prevents non-determinism and state-dependent results.
3. **Every result-returning method returns a `Cursor`, never materialized collection.** Bounds memory; enables streaming.
4. **Determinism is tested (L2).** Any function claiming determinism has a permutation + repeat test in the validation pack.
5. **Store isolation must be empirically verified.** Guarded updates don't guarantee write-skew isolation on all stores/configs. Test against the actual target store.

**Policy enforcement:** Lint rules (Python imports, string checking); ArchUnit rules (Java read/write encapsulation); CI gates (determinism test, injection probes in L8 suite).

### 1.3 Bi-temporal modeling: configurable, not mandated

**Design question:** Should LATTICE mandate that all data be immutable (never update in place, only supersede), versioned (every triple gets a version), and bi-temporally queryable (as-of-valid-time AND as-of-transaction-time)?

**Answer:** No. Mandate transaction-time capture and order-preservation; leave valid-time and in-place update to application choice.

**Rationale (from Architecture Review counter-argument):**

- `fnd:TemporallyScoped` already provides a mixin for time-bound domain facts (eligibility rules, time-limited claims).
- Mandating immutability everywhere creates data explosion (versions of every triple).
- End-user business domains vary wildly in their temporal requirements.
- Eligibility rule evaluation can noop on `validTo`, but that's application logic, not platform mandate.
- Some users may prefer in-place updates for cost/operability; this is a valid choice.

**What LATTICE provides:**
- **Required:** `ex:recordedAt` + dense ordering for transaction time.
- **Optional:** `ex:occurredAt` for valid time, if the application needs it.
- **Configurable:** Whether to immutably version writes, whether to allow deletes, whether to materialize projections or query on-demand.
- **Per-graph setting:** Can vary by subgraph or tenant configuration.

**Policy:** Decision records (MORK outcomes, admissions, behaviour state changes) are always append-only and immutable (audit requirement). Projection-source data can have deletion/update policies configured per application.

### 1.4 Storage lifecycle and deletion

**Design question:** Should LATTICE forbid deletes and mandate immutable, versioned, append-only writes?

**Answer:** No. Deletes are a valid and sometimes necessary policy, not a forbidden anti-pattern.

**What LATTICE requires:**
- **Audit trail:** Before any delete, record why (decision record with cause, principal, provenance).
- **Partition strategy:** Hot/cold data separated by retention window (monthly partition by transaction time).
- **Configuration:** Policy specified per graph or tenant, not globally.
- **Irreversibility gates:** No deletes until Phase 0 exit gate passes (identity/provenance/temporal conventions ratified).

**What LATTICE does NOT require:**
- Immutability of application data (MORK source data can be updated per mapping decision).
- Versioning of every triple (write versioning at the decision/commit level, not triple level).
- Prohibition on corrective writes or backfills.

---

## Part 2 — Architecture decision implications

### A74 impact: Graph-primary system of record

**Proposed ADR-A74 (graph-primary)** states: RDF is the authoritative store for all semantic state. PostgreSQL and RabbitMQ are coordination stores only (transient, derived, reconstructible).

**Patterns required by A74:**

- **K (Uniqueness):** Natural keys must be enforced in RDF via key claims or deterministic IRIs. No authoritative `UNIQUE` constraints in PostgreSQL.
- **O (Ordering):** Per-stream dense sequencing in `<urn:meta>` graphs per aggregate. Kafka offsets and database timestamps are derived, not canonical.
- **C (Concurrency):** Guarded `DELETE/INSERT … WHERE` against RDF. PostgreSQL row locks are belt-and-braces only.
- **T (Combined):** Separate metadata graphs with version counters. Whole-graph payload replaces safe because version survives.

### A75 impact: Three-tier store SPI (C-02)

**Proposed ADR-A75 (store SPI)** defines three contract tiers:

1. **Core SPI (mandatory):** SPARQL 1.1 query + update endpoints; named-graph support; isolation level (document which); `CONSTRUCT`/`ASK`/`SELECT` support; atomic one-request semantics.
2. **Query SPI (optional):** SHACL validation; full-text search; geospatial indexing; temporal indices.
3. **Distribution SPI (optional):** Replication/HA; sharding (key-based partition); multi-region.

**Reference implementation:** Jena TDB2 + Fuseki HTTP layer (Core SPI fully compliant, Query SPI partial, Distribution SPI none — single instance).

**Patterns that must be portable across all Core SPI implementations:**

- K (Uniqueness) ✅ P0–P7 work on any SPARQL 1.1 store
- O (Ordering) ✅ Dense sequences work anywhere; dataset-wide sparse order requires change feed (store-specific)
- C (Concurrency) ⚠️ Guarded update is portable; write-skew isolation varies by store/config (must test)
- T (Combined) ✅ Metadata graphs are portable; version counters and receipts work anywhere

---

## Part 3 — Decision and design pattern inventory

### Decisions to formalize (proposed ADRs)

| ID | Title | Rationale | Impact |
|-----|-------|-----------|--------|
| **A74** | Graph-primary system of record | RDF is authoritative; PostgreSQL/RabbitMQ are coordination stores only | Shapes data model, deployment, queries; requires K/O/C patterns |
| **A75** | Three-tier store SPI | Multiple stores pluggable; reference impl Jena/Fuseki | Defines Core/Query/Distribution tiers; portability constraints |
| **A-Unique** | Uniqueness enforcement in RDF | Use key-claim registry (P1) + guarded update (P2) + SHACL (P5); P3 for high-contention keys | All natural and surrogate key enforcement; scales to millions |
| **A-Order** | Dense per-stream ordering + transaction time | Per-stream dense seq in metadata graph; transaction time immutable; valid time optional; dataset-wide order derived | Audit, replay, causal consistency; event sourcing |
| **A-CAS** | Compare-and-set via guarded SPARQL update | `DELETE/INSERT … WHERE` with receipt log (P2/C); verify via `ASK` not re-read | Atomic state mutations; works on any SPARQL 1.1 store |
| **A-Temporal** | Bi-temporal configurable, not mandated | `recordedAt` + order required; valid time optional; in-place update configurable per graph | Per-application temporal semantics; no data explosion mandate |
| **A-Delete** | Deletion is policy, not forbidden | Audit trail required; partition by retention; config per graph/tenant | Cost control; legal compliance; flexibility |
| **A-Query** | SPARQL query safety and determinism | No string concat (injection); no `now()` in guards (determinism); Cursor not collection (memory); L2 tests; store isolation verified | Prevents silent bugs; scales to large queries |

### Design patterns to catalog and implement

1. **Pattern K: Uniqueness** (7 sub-patterns P0–P7)
   - Sub-pattern K1: Deterministic IRIs for immutable keys
   - Sub-pattern K2: Key-claim registry for mutable keys
   - Sub-pattern K3: Guarded insert (CAS for uniqueness)
   - Sub-pattern K4: Upsert for functional properties
   - Sub-pattern K5: SHACL validation (cardinality + cross-node)
   - Sub-pattern K6: External allocator (high-contention keys)
   - Sub-pattern K7: Detect-and-reconcile nightly scan

2. **Pattern O: Ordering** (with sub-patterns O1–O5 for use cases)
   - Sub-pattern O1: Per-stream dense sequencing
   - Sub-pattern O2: Valid-time capture (optional)
   - Sub-pattern O3: Logical causality (version pointers)
   - Sub-pattern O4: Dataset-wide order (derived, sparse)
   - Sub-pattern O5: Bitemporal query (point-in-time reads)

3. **Pattern C: Concurrency control** (with escape hatches C1–C6)
   - Sub-pattern C1: Guarded `DELETE/INSERT … WHERE` CAS
   - Sub-pattern C2: Receipt-log outcome verification
   - Sub-pattern C3: Derived ETags + immutable chain
   - Sub-pattern C4: HTTP-level CAS (GSP/LDP)
   - Sub-pattern C5: Single-writer queue (Kafka partitioning)
   - Sub-pattern C6: External lock (Postgres/Redis)

4. **Pattern T: Temporal + Concurrency combined**
   - Sub-pattern T1: Metadata graphs per aggregate
   - Sub-pattern T2: Version counters in separate graph
   - Sub-pattern T3: Whole-graph payload replace
   - Sub-pattern T4: Epoch + seq for backup safety
   - Sub-pattern T5: Immutable receipts with chain

5. **Query patterns**
   - QP1: Prepared query + params (injection safety)
   - QP2: Time-agnostic guards (determinism)
   - QP3: Cursor for results (memory bounds)
   - QP4: Permutation determinism test (L2)
   - QP5: Store isolation verification (L8)

---

## Part 4 — Path to formalization

### 4.1 This sketch phase

**Outcomes:**

- ✅ Problem statement framed (uniqueness, ordering, concurrency, bi-temporal, query safety)
- ✅ Solution approach outlined (7 portable SPARQL patterns + 3 clocks model)
- ✅ 8 proposed ADRs identified
- ✅ 15 design sub-patterns cataloged
- ✅ Architecture Review counter-arguments incorporated (configurable, not mandated)

### 4.2 Plan phase: Documentation and pattern library

**Deliverable:** `docs/developer/plans/rdf-sparql-patterns-phase-plan.md` (0.5–2 agent-days)

**Scope:**

- **Part A:** Formalize each pattern as a design document with concrete examples
  - For each pattern (K, O, C, T, QP): write a 2–4 page design spec + runnable SPARQL examples
  - For each sub-pattern: code snippet + test case template
  
- **Part B:** Map patterns to LATTICE components
  - Which patterns are used by Uniqueness service (K1–K7)?
  - Which patterns are used by MORK decision records (O1, O3, T)?
  - Which patterns are used by store SPI (C, T)?
  - Which patterns are used by ingestion (O1, C)?

- **Part C:** Store-specific adapter guide
  - For each Core SPI store (Jena TDB2, GraphDB, Neptune, Rya, RDFox): document which patterns are native, which need workarounds
  - Jena TDB2: write-conflict detection (T1–T5); no dataset-global dense counter; no SHACL incremental validation
  - Neptune: MVCC (needs P3 sharded counter); no SHACL; has Streams (alternative to log); supports RDFMS (time-series)

- **Part D:** Policy enforcement
  - Lint rules: Python import ban on `datetime.now()`, `uuid.uuid4()` in certain modules
  - ArchUnit: Java `@ScopedDataset` boundary; ban on direct store access
  - CI gates: Determinism L2 tests; injection corpus for L8

- **Part E:** Validation pack structure
  - Skeleton test suite per pattern: K1 (immutable key collision), K2 (claim registry race), C1 (guarded update under concurrent writers), T1 (version counter + payload), etc.
  - 1–3 test cases per pattern (positive + adversarial)

### 4.3 Implementation phase: Slices and milestones

**Post-plan:** Decompose into Phase 0 slices:

- **Phase 0.2 (Walking skeleton):** Implement T (concurrent write + ordering) + C (guarded update) on Jena TDB2
- **Phase 0.3 (Schema & contracts):** Implement K (uniqueness) for identity minting
- **Phase 0.4 (Canonicalization):** Implement O (dense ordering) for audit/replay
- **Phase 0.5 (Component integration):** Implement query discipline (QP), SHACL (K5), full test suite

---

## Part 5 — Open questions

1. **Store SPI target breadth** — Do we commit to GraphDB compatibility (≥ 2 stores), or is Jena/Fuseki reference enough initially?
2. **Epoch/restart safety** — How do we regenerate valid ETags after restore without conflicting with existing consumer watermarks?
3. **Distributed ordering** — If stores are sharded per tenant, how do we handle global dataset position (for compliance audits)?
4. **SHACL incremental validation** — Which stores support re-validating only the changed subgraph? If none, does P5 stay optional?
5. **Temporal analytics path** — For as-of queries over millions of triples per graph, do we materialize "current" projections + separate analytic queries, or query the log directly?
6. **LLM decision node usage** — Architecture Review notes: having MORK decision nodes in the graph (not Postgres) enables LLM to learn from rejection history. Does this change the store SPI for MORK decision records?

---

## Appendix: References

- `docs/architecture/Architecture Review.md` — Gap analysis and component spec (G-01 through G-34)
- `docs/architecture/solution-design-specification.md` — Product surface (design-time plane)
- `docs/architecture/data-architecture.md` — Current three-realm model (to be revisited under A74)
- `docs/developer/notes/Uniqueness in RDF.md` — Portable patterns P0–P7
- `docs/developer/notes/Ordering in RDF.md` — Requirements O1–O5 and clock model
- `docs/developer/notes/Optimistic concurrency in RDF stores.md` — Portable CAS patterns 1.1–1.5
- `docs/developer/notes/Combine Concurrency And Ordering Plan.md` — A1–A7 and F1–F6 findings
