
# Verdict up front

Your pattern is **the right shape and the wrong grain, with one correctness hole that will bite you.** Specifically:

1. **It doesn't solve your stated problem.** You said `recordedAt` can't order events written in the same instant. A *per-commit* sequence doesn't order two events written in the **same commit** either. You need either an event-level sequence or `(commitSeq, opSeq)`.
2. **"Assigned at commit" + "written onto the graph as a triple" are in tension.** If the value is a triple, it is part of the commit, so it must be chosen *before* commit completes. Under concurrent writers that means `commitSeq` can be assigned in one order and become visible in another → **readers using `commitSeq > watermark` silently skip events.** This is the Postgres-sequence/LSN gap problem, and it is the classic way changefeeds lose data.
3. **A single per-dataset counter is a global serialization point.** That's either your throughput ceiling or, on a distributed store, unobtainable.
4. **A store-log-derived value is not stable across backup/restore/migration**, which invalidates every consumer watermark you've ever handed out.

The fix is small and mostly additive: make the sequence **per-stream and allocated inside the writing transaction** (which makes it dense and order-preserving *by construction*), add an **epoch** prefix, add an **intra-commit `opSeq`**, and keep the dataset-level position as a *separate, optional, derived* concern sourced from the store's change feed. Details below.

---

# Part 0 — What "ordering" actually means

Five different requirements get bundled under "ordering," and they have different solutions. Conflating them is the root cause of most of the pain.

| | Requirement | Example | Needs |
|---|---|---|---|
| **O1** | **Total order for replay/sync** | "give me everything after where I left off" | dense, gap-detectable, order-preserving position |
| **O2** | **Causal / per-entity order** | version 3 of this contract supersedes version 2 | per-stream monotonic counter or version pointers |
| **O3** | **Domain (valid-time) order** | events sorted by when they happened | `occurredAt` + a deterministic tiebreak — **not** commit order |
| **O4** | **Point-in-time / bitemporal read** | "state as of last Tuesday" / "as of seq 91,438" | validFrom/validTo, or store-native time-travel |
| **O5** | **Ordered collections in the data** | steps 1..n of a procedure, a ranked list | index property or RDF collection; a different problem entirely |

### The three clocks

Keep these physically separate in the model and never let one impersonate another:

* **Valid time** (`ex:occurredAt`) — when it happened in the world. Late/backfilled data is *normal*; sorting by commit order here is a bug.
* **Transaction time** (`ex:recordedAt` + `commitSeq`) — when the store learned it. Monotonic, never backdated, used for audit, replay, incremental sync.
* **Logical/causal time** (per-stream `seq`, `ex:supersedes`, version vectors) — happened-before, independent of wall clocks.

Your proposal addresses transaction time and *proxies* causal order. It does not address O3, and if anyone ever writes `ORDER BY ?commitSeq` to answer a domain question, you'll get wrong answers the first time someone backfills history.

### The central tradeoff (pick deliberately)

| Property | **Dense** (in-transaction counter) | **Sparse** (HLC / store LSN / timestamps) |
|---|---|---|
| Gap-free → "did I miss anything?" detectable | ✅ | ❌ |
| Allocation order == commit order | ✅ (by construction) | ⚠️ needs watermark machinery |
| Contention | one writer at a time **per counter** | none |
| Distributed / multi-region | poor | good |
| Comparable across nodes without coordination | n/a | ✅ |

**You cannot have both gap-freedom and contention-freedom.** Dense sequences give you completeness detection; sparse clocks give you scalability. The usable middle is *dense per-stream, sparse across streams* — which is why grain is the most important decision here, not the encoding.

---

# Part 1 — Critique of the proposed pattern, with fixes

### G1. Per-commit granularity doesn't order intra-commit events

If a transaction writes three events, all three carry the same `commitSeq`. RDF's set semantics mean the triples inside that graph have no intrinsic order, so the events are unordered — exactly the failure you set out to fix.

**Fix:** `(epoch, commitSeq, opSeq)` where `opSeq` is a client-supplied ordinal within the commit, or promote the sequence to **event level** (each event gets its own position). Neptune Streams' `commitNum`/`opNum` pair is precisely this design, and it's the right one.

Note a hard SPARQL constraint here: **you cannot generate distinct ordinals inside one update.** `NOW()` returns the *same* value for every solution in a query execution (per spec), and `UUID()`/`RAND()` are per-solution but unordered. The `opSeq` must come from the client, typically via `VALUES`.

### G2. The allocate-then-commit reorder hole

```
t0  Tx A reads counter=4, takes seq=5
t1  Tx B reads counter=4… or 5, takes seq=6
t2  B commits          → reader sees seq 6, advances watermark to 6
t3  A commits (seq 5)  → reader never sees it
```

Any consumer doing `FILTER(?seq > ?lastSeen)` loses event 5 forever. This is not hypothetical; it is the default behaviour of every pre-allocation scheme under concurrency.

**Fix (and the key insight):** put the counter read-and-increment **in the same transaction as the payload write**, on a single shared statement:

```sparql
DELETE { GRAPH <urn:meta> { ?ctr ex:next ?n } }
INSERT { GRAPH <urn:meta> { ?ctr ex:next ?n1 }
         GRAPH ?cg { … payload … }
         GRAPH <urn:log> { ?cg ex:epoch 3 ; ex:commitSeq ?n ; ex:recordedAt ?ts } }
WHERE  { BIND(<urn:ctr:stream:orders> AS ?ctr)
         GRAPH <urn:meta> { ?ctr ex:next ?n }
         BIND(?n + 1 AS ?n1) … }
```

Because every successful commit had to rewrite the *same* statement, successful commits form a chain: the transaction holding seq *n+1* necessarily read a value committed by the holder of *n*. Therefore **allocation order == commit order, and the sequence is dense with no abandoned values.** Aborted transactions consume nothing. No watermark machinery, no gap-filling tombstones, no stalled consumers.

This is the same materialized-write-conflict trick from the uniqueness design, reused — and here it isn't a workaround, it's the mechanism.

Cost: writers to one counter are serialized. Which leads directly to:

### G3. Per-dataset grain is the wrong default

A single global counter means every write in the dataset contends on one statement. On a single-writer store (TDB2, GraphDB) that costs nothing extra — writes are already serialized. On a clustered or MVCC store it's a hotspot, and on a distributed store (Neptune, Rya, federations) a globally monotonic dense counter may be unimplementable at acceptable cost.

Meanwhile, **most consumers don't need a global total order.** They need per-entity or per-topic order plus the ability to resume.

**Fix:** two-tier.

* **Per-stream dense sequence** (required) — stream = entity, aggregate, tenant, or topic. Cheap, shardable, gap-free, gives O1 *within a stream* and O2 for free. Concurrent writers to different streams never contend.
* **Dataset position** (optional, for global replay) — do **not** mint it in the write transaction. **Derive** it from the store's change feed / patch log, or accept a *sparse partial* order (HLC) across streams, and let consumers reconstruct completeness per stream.

Also decide the **stream key normalization and versioning** now (same discipline as key normalization in the uniqueness design), because re-keying streams later breaks every stored watermark.

### G4. No epoch → restore/migration corrupts consumer state

Restore from backup, reload into a fresh repo, or migrate vendors, and a store-log-derived position resets or diverges. Consumers holding `lastSeen = 91438` will either skip or double-process, with no way to tell.

**Fix:** a mandatory **epoch** (generation) integer in dataset metadata, bumped on *any* rebuild, restore, re-key, or vendor migration. Order on the lexicographic pair `(epoch, seq)`. Consumers persist and compare both; an epoch change is a hard signal to resynchronize rather than resume. This is Kafka leader epochs / Raft terms, and it is the detail that separates a design that survives its first disaster recovery from one that doesn't. It is also the argument that "value from the store's txn log" cannot stand alone.

### G5. Additions are ordered; retractions are not

An append-a-graph-with-a-seq design orders *assertions*. Deletions have no natural home: if you `DELETE` triples from an older graph, that mutation carries no sequence and is invisible to replay.

**Fix:** make the log explicitly change-oriented — `?cg ex:asserts ?g1 ; ex:retracts ?g2` (an RDF-Patch-shaped model), or go append-only with tombstones plus `validFrom`/`validTo`, and never mutate a sealed assertion graph. Pick one and enforce it; half-measures make O4 unanswerable.

### G6. `commitSeq` on the graph is correct, but has a query and scale cost

Annotating the **graph** rather than each triple is the right call — one metadata triple per commit, not per statement, and it aligns with "named graph = atomic changeset." Two consequences to plan for:

* **Graph proliferation.** Millions of tiny named graphs degrade several stores (graph dictionary bloat, expensive `GRAPH ?g` enumeration, slow management ops). Mitigate by bucketing (one graph per stream per time window / per N commits) rather than per commit, and keep the log in a small number of large metadata graphs.
* **Filtering by seq requires a join** through the log graph, which many optimizers won't push down; a "changes since S" query can degrade to scanning the log then probing. Measure it. If you need *per-triple* seq filtering at speed, the options are RDF-star annotation (verbose, uneven support, per-triple cost) or denormalizing `ex:commitSeq` into the data graph. Both are expensive; prefer bucketed graphs plus keyset pagination first.

### The amended spec

```turtle
# dataset metadata
<urn:ds:prod>  ex:epoch 3 ;
               ex:orderModel "per-stream-dense+hlc-global" ;
               ex:stableWatermark "3:91438"^^xsd:string .   # only if a sparse tier exists

# one entry per commit, in a small number of log graphs
<urn:commit:0000000000091439>
    a             ex:Commit ;
    ex:epoch      3 ;
    ex:stream     <urn:stream:orders/42> ;
    ex:streamSeq  "17"^^xsd:long ;        # dense per stream, in-tx allocated
    ex:hlc        "1719412345678:0003:n7" ;  # sparse, globally comparable
    ex:recordedAt "2024-06-26T14:12:25.678Z"^^xsd:dateTime ;
    ex:asserts    <urn:g:orders/42/017> ;
    ex:retracts   <urn:g:orders/42/016> .

# events carry their own ordinal within the commit
<urn:ev:…> ex:commit <urn:commit:0000000000091439> ;
           ex:opSeq  "2"^^xsd:long ;
           ex:occurredAt "2024-06-20T09:00:00Z"^^xsd:dateTime .   # valid time, separate
```

Sort key for O1/O2: `(epoch, streamSeq, opSeq)`. Sort key for O3: `(occurredAt, epoch, streamSeq, opSeq)` — valid time first, transaction time only as a deterministic tiebreak.

---

# Part 2 — Portable SPARQL patterns

### S1. In-transaction counter (dense, order-preserving) — the workhorse

As in G2. Requirements and caveats:

* Requires the engine to either serialize writers or detect write–write conflicts. Verify with the TCK, don't trust docs.
* Bootstrap counters eagerly (`?ctr ex:next 1`); an `OPTIONAL`-based lazy init reintroduces a race on first write.
* Retry on conflict with jittered backoff; the operation is idempotent if you include an idempotency guard (`FILTER NOT EXISTS { ?anyCommit ex:idempotencyKey "…" }`).
* Acquire multiple counters in sorted order if one commit touches several streams, or you will deadlock.

### S2. Keyset (seek) pagination — never `OFFSET`

`ORDER BY ?seq LIMIT 100 OFFSET 500000` is O(offset) on most engines and unstable under concurrent writes.

```sparql
SELECT ?commit ?seq ?op WHERE {
  GRAPH <urn:log> {
    ?commit ex:epoch 3 ; ex:stream <urn:stream:orders/42> ; ex:streamSeq ?seq .
    OPTIONAL { ?commit ex:opSeq ?op }
    FILTER (?seq > 17 || (?seq = 17 && ?op > 2))
  }
} ORDER BY ?seq ?op LIMIT 100
```

Always carry the full composite cursor `(epoch, seq, opSeq)`, and make the client reject a response whose epoch differs from its cursor's.

### S3. Gap / completeness check (the payoff of density)

```sparql
SELECT (MIN(?seq) AS ?lo) (MAX(?seq) AS ?hi) (COUNT(DISTINCT ?seq) AS ?n)
WHERE { GRAPH <urn:log> { ?c ex:epoch 3 ; ex:stream ?s ; ex:streamSeq ?seq } }
GROUP BY ?s
HAVING (COUNT(DISTINCT ?seq) != MAX(?seq) - MIN(?seq) + 1)
```

Ship as a metric; alert on any row. This is the single best argument for dense over sparse: with HLC or store LSNs this query is impossible, and you can never prove you haven't lost an event.

### S4. Latest-version-per-stream

```sparql
SELECT ?stream ?commit WHERE {
  { SELECT ?stream (MAX(?seq) AS ?max) WHERE {
      GRAPH <urn:log> { ?c ex:stream ?stream ; ex:epoch 3 ; ex:streamSeq ?seq } }
    GROUP BY ?stream }
  GRAPH <urn:log> { ?commit ex:stream ?stream ; ex:epoch 3 ; ex:streamSeq ?max }
}
```

Portable and index-friendly. Prefer this to `ORDER BY … LIMIT 1` inside a correlated subquery, which several optimizers handle badly. An even cheaper option: maintain a materialized `?stream ex:head ?commit` pointer, upserted in the same transaction (functional property, `sh:maxCount 1` — reuses the uniqueness machinery).

### S5. Valid-time ordering with deterministic tiebreak

```sparql
ORDER BY ?occurredAt ?epoch ?streamSeq ?opSeq
```

Never `ORDER BY ?recordedAt` alone (ties, clock skew) and never `ORDER BY ?commitSeq` for a domain question. If `occurredAt` genuinely ties and the domain has no tiebreak, the transaction-time suffix at least gives you **stable, reproducible** results — which is what makes pagination and diffs sane.

### S6. Bitemporal / as-of reads

```sparql
# state as of a transaction position
GRAPH <urn:log> { ?c ex:epoch 3 ; ex:streamSeq ?seq ; ex:asserts ?g FILTER(?seq <= 17) }
GRAPH ?g { ?s ?p ?o }
FILTER NOT EXISTS {
  GRAPH <urn:log> { ?c2 ex:epoch 3 ; ex:streamSeq ?s2 ; ex:retracts ?g FILTER(?s2 <= 17) }
}
```

This is expensive and gets worse with history depth. Realistic options in order of preference: (a) store-native time travel (MarkLogic/Oracle/Stardog — Part 3); (b) `validFrom`/`validTo` intervals materialized on the data, which makes as-of a simple range filter at the cost of a rewrite on every update; (c) this log-replay form, reserved for audit rather than serving traffic.

### S7. HLC for the sparse tier (multi-writer / multi-region)

Compute in the application, store as a single lexicographically-sortable string: `{physicalMillis:013}:{logical:04}:{nodeId}`.

```
on send/commit:  l = max(prev.l, now_ms);  c = (l == prev.l) ? prev.c+1 : 0
on receive(m):   l = max(prev.l, m.l, now_ms);  c = …
```

Gives a globally comparable, causally consistent, contention-free order that stays close to wall-clock and **survives NTP step-backs** (unlike raw timestamps). Does not give completeness detection — which is exactly why it pairs with, rather than replaces, S1.

### S8. External sequencer / partitioned single writer

Put ordering where ordering is solved: Kafka partition offsets, a Postgres `BIGSERIAL`/`nextval`, Redis `INCR`, an actor-per-stream. Partition the writer by `hash(stream) % N` and allocation order == commit order by construction, with zero RDF-side contention. Write to RDF idempotently via an outbox, carrying `(epoch, offset)` through.

This is frequently the correct answer and shouldn't be treated as a fallback. It also composes with S1 (use the external value, skip the counter statement).

### Aside: O5, ordered collections

Different problem, worth stating so it doesn't get solved with `commitSeq`:

* `rdf:List` — recursive, needs property paths to traverse, O(n) rewrite to insert in the middle, painful in SPARQL. Avoid for anything mutable.
* **Integer index property** (`ex:position 3`) — simple, sortable, pushdown-friendly; renumbering on insert is the cost.
* **Fractional / lexicographic ranking keys** (LexoRank-style: insert between `"n"` and `"p"` as `"o"`) — O(1) insertion with no renumbering, `ORDER BY` on a plain string. Best default for user-reorderable lists; occasionally needs a rebalance pass.
* `sh:order` for shape/UI ordering, `olo:` if you want a vocabulary off the shelf.

### SPARQL gotchas that break ordering schemes

| Gotcha | Consequence |
|---|---|
| `NOW()` is constant across a query execution | Can't generate distinct ordinals in one update; supply `opSeq` via `VALUES` |
| `UUID()`/`RAND()` are per-solution but unordered | Usable as a tiebreak, useless as an order |
| Ordering of **IRIs** in `ORDER BY` is not reliably specified across engines | Sort on a numeric/string **literal**, never on the IRI |
| `xsd:dateTime` precision is often truncated to ms; timezone handling and leap smearing vary | Never use wall-clock as the monotonic source |
| Unpadded numeric **strings** sort lexicographically wrong (`"9" > "10"`) | Zero-pad to fixed width (19 digits for int64) if the value is ever a string or embedded in an IRI |
| Mixed `xsd:integer`/`xsd:long`/`xsd:decimal` | Numeric promotion works for `ORDER BY`/comparison but term equality differs; pick **one** datatype and enforce it in shapes |
| `ORDER BY` with unbound variables | Unbound sorts before everything; an `OPTIONAL ?opSeq` silently reorders — default it with `COALESCE(?op, 0)` |
| `ORDER BY` in a subquery without `LIMIT` | Not guaranteed to survive into the outer query |
| Bulk load bypasses everything | No counters advanced, no log entries; needs its own path (Part 3) |

---

# Part 3 — Vendor extensions

> Same caveat as before: these features and their guarantees move between releases. Use this as a map of where to look, and let the TCK be the source of truth.

**Apache Jena / Fuseki / TDB2** — Best-in-class fit. TDB2 is **MR+SW**: writers are serialized, so S1 is trivially correct and dense with no conflict retries. More importantly, **RDF Patch + `rdf-delta`** gives you a *versioned patch log* — each patch has a monotonic version, which is exactly O1 done properly, at the storage layer, with replay and gap detection built in. If you want a durable dataset-level position, this is the reference implementation. `DatasetChanges` hooks let you emit patches from custom code.

**Eclipse RDF4J** (and derivatives) — `IsolationLevels.SERIALIZABLE` makes S1 correct on Memory/Native; `SailConflictException` on conflict. `SailConnectionListener` / `NotifyingSail` / a `SailWrapper` lets you assign the sequence *inside* the commit in-process — the cleanest place to put it, since you can stamp the value after conflict resolution but before durability. No built-in durable log; you build it.

**Amazon Neptune** — **Neptune Streams** is the model answer: each change carries `(commitNum, opNum)`, monotonic, ordered, gap-detectable, with `eventId` for resumption. Don't mint your own dataset counter; consume the stream and let `commitNum` be your dataset position. Note the stream has a retention window, so consumers must handle falling off the end (→ full resync, treat like an epoch change). No multi-request transactions; per-request conflict detection means S1 works for per-stream counters, with `ConcurrentModificationException` retries.

**Ontotext GraphDB** — Writes are serialized per repository, so S1 is safe without conflict handling. No exposed global commit counter; use a counter statement. Plugin API / `UpdateInterpreter` can assign sequences server-side in-process; `.pie` consistency rules can *enforce* monotonicity (reject a commit whose seq isn't `prev+1`), which is a genuinely useful guardrail. Connectors give you an external index for fast range scans over the log.

**Stardog** — Multi-request transactions let you read-then-stamp within one transaction. Snapshot isolation with conflict detection → S1 with retries. **Versioning / graph history** features give transaction-time tracking and as-of style queries without hand-rolling S6; check the current feature set and its cost model. Virtual graphs let you source the sequence from a relational `nextval` (S8 without a second datastore).

**OpenLink Virtuoso** — Has **native SQL sequences** (`sequence_next`/`sequence_set`) callable from procedures, plus real isolation levels, triggers, and a transaction log. The strongest option for "give me a correct dense sequence without contention pathologies": allocate in SQL, write quads, one atomic SQL transaction. Also exposes UDFs to SPARQL.

**MarkLogic** — Every transaction has a **system timestamp** (MVCC), and point-in-time queries against it are native. This makes O1 and O4 essentially free and correct; you don't need `commitSeq` at all for transaction-time ordering. Multi-statement transactions, `xdmp:lock-for-update` for pessimistic ordering, range indexes for log scans.

**Oracle RDF / Semantic Graph** — Triples in relational tables: SQL sequences, `SCN`, and **Flashback** give you dense positions and true as-of reads with no modelling effort. Bulk load through a staging table with a sequence is a clean high-throughput path.

**AllegroGraph** — Triple ids are assigned monotonically at insert and are exposed, which gives a natural insertion order; plus audit/transaction log features and server-side Prolog/Lisp/JS for atomic allocate-and-write.

**Blazegraph** — Unisolated writes are single-writer → S1 safe; has commit-time/revision metadata but it's not a great public contract.

**Oxigraph / embedded stores** — Single-writer transactions; do allocate-and-write in-process. Simplest correct implementation of all.

**Rya / Halyard / federated or non-ACID backends** — No usable dense sequence. Use S8 (external sequencer) + S7 (HLC) and accept `PER_STREAM_DENSE` at best, with a mandatory reconciler. Do not attempt S1.

---

# Part 4 — Adapter design for pluggable backends

Same philosophy as the uniqueness adapter: abstract over **capabilities**, declare the **order model** you need, let a planner choose the strongest strategy each backend can actually deliver, and fail at startup if it can't.

## 1. Declarative order spec

```yaml
- id: orders-stream-order
  version: 1
  epoch_source: dataset_metadata        # required, bumped on any rebuild
  stream:
    key: [ ex:tenant, ex:aggregateId ]  # composite; normalized + frozen per version
    normalize: [ nfkc, trim ]
  grain: event                          # commit | event  (event => opSeq required)
  tiers:
    stream:  { model: dense, min_level: TOTAL_DENSE }       # O1 within stream, O2
    dataset: { model: derived_or_sparse, min_level: PARTIAL_CAUSAL }
  valid_time:
    property: ex:occurredAt
    tiebreak: [ epoch, streamSeq, opSeq ]
  retention:
    log: 400d
    on_cursor_expired: force_resync     # treat like epoch change
  change_model: assert_retract          # assert_retract | append_only_tombstone
```

`min_level` is the contract. If the configured backend can't reach it, deployment fails — you never silently degrade from "gap-free" to "probably fine."

## 2. Order levels

```
TOTAL_DENSE       gap-free, order-preserving, completeness detectable
TOTAL_SPARSE      total order, gaps expected (store LSN, HLC w/ single sequencer)
PER_STREAM_DENSE  dense within stream, partial across streams   ← recommended default
PARTIAL_CAUSAL    causal order only (HLC / version vectors)
BEST_EFFORT_TIME  wall-clock + tiebreak; no guarantees          ← audit-only
```

## 3. Ports

```java
interface SequenceService {
  /** Allocated inside `tx` if the backend supports it; otherwise externally. */
  Position allocate(Tx tx, StreamKey stream, int opCount);
  AllocationSemantics semantics();   // IN_TRANSACTION | PRE_COMMIT | POST_COMMIT_DERIVED
}

record Position(long epoch, long seq, int opSeq) implements Comparable<Position> {}

interface ChangeFeed {                       // Neptune Streams, rdf-delta, MarkLogic ts, listeners
  Iterator<ChangeEvent> from(Cursor c) throws CursorExpiredException;
  boolean dense();                           // can we detect gaps?
  Duration retention();
}

interface WatermarkService {                 // only needed when semantics() == PRE_COMMIT
  Position stable();                         // highest fully-committed contiguous position
  void publish(Position p);
}

interface TimeTravel {                       // MarkLogic, Oracle, Stardog versioning
  TupleResult asOf(String sparql, Position p);
}

record OrderCapabilities(
  boolean singleWriter,                 // allocation order == commit order for free
  boolean detectsWriteWriteConflict,    // enables in-transaction counter
  IsolationLevel maxIsolation,
  boolean multiRequestTx,               // read-then-stamp across requests
  boolean nativeSequence,               // Virtuoso sequence_next, SQL nextval
  boolean nativeCommitPosition,         // exposed, queryable, monotonic
  boolean nativeChangeFeed, boolean changeFeedDense, Duration feedRetention,
  boolean nativeTimeTravel,
  boolean insertOrderObservable,        // AllegroGraph triple ids etc.
  boolean bulkLoadBypassesHooks,
  int     maxGraphsAdvisory) {}
```

## 4. Strategies

| Strategy | Requires | Provides | Notes |
|---|---|---|---|
| `SingleWriterCounterStrategy` (S1) | `singleWriter` | `TOTAL_DENSE` | TDB2, GraphDB, Blazegraph, Oxigraph. Simplest correct option |
| `InTxCounterStrategy` (S1) | `detectsWriteWriteConflict` ∨ `SERIALIZABLE` | `TOTAL_DENSE` / `PER_STREAM_DENSE` | retry on conflict; shard counters by stream |
| `NativeSequenceStrategy` | `nativeSequence` | `TOTAL_DENSE` | Virtuoso, Oracle; allocate in SQL inside the same tx |
| `NativeFeedStrategy` | `nativeChangeFeed && changeFeedDense` | `TOTAL_DENSE` (dataset tier) | Neptune Streams, rdf-delta. **Log is the order**; the triple is a cache |
| `NativePositionStrategy` | `nativeCommitPosition` | `TOTAL_SPARSE` | MarkLogic system ts, Oracle SCN; pairs with `TimeTravel` |
| `ExternalSequencerStrategy` (S8) | `SequenceService` external | `TOTAL_DENSE` / `PER_STREAM_DENSE` | Kafka offsets, Postgres nextval, actor-per-stream |
| `HlcStrategy` (S7) | nothing | `PARTIAL_CAUSAL` | multi-region; no completeness detection |
| `PreAllocateWatermarkStrategy` | `WatermarkService` | `TOTAL_SPARSE` | **last resort.** Needs lease + tombstone gap-filling or the watermark stalls forever |
| `ClockTiebreakStrategy` | nothing | `BEST_EFFORT_TIME` | audit only; never the primary |
| `OrderAuditStrategy` | query only | — | **always installed**: S3 gap scan, monotonicity scan, watermark-lag metric |

Planner, as before: pick the highest-level supported strategy per tier, reject at startup if it's below `min_level`, always append the auditor.

```java
Plan plan(OrderSpec s, OrderCapabilities c) {
  var stream  = strongest(s.tiers().stream(),  c);
  var dataset = strongest(s.tiers().dataset(), c);
  requireAtLeast(stream,  s.tiers().stream().minLevel());
  requireAtLeast(dataset, s.tiers().dataset().minLevel());
  return new Plan(stream, dataset, ALWAYS.orderAudit());
}
```

## 5. Write path

```java
WriteResult append(StreamKey stream, List<Event> events) {
  var streamId = normalize(stream);                      // frozen pipeline, versioned
  for (int attempt = 0; attempt < maxRetries; attempt++) {
    try (var tx = store.begin(required(isolation))) {
      var pos = sequences.allocate(tx, streamId, events.size());   // epoch + seq + opSeq base
      var cg  = commitGraphIri(pos);                               // bucketed, zero-padded
      tx.update(APPEND, bindings(pos, cg, events, idempotencyKey)); // counter + log + payload
      tx.commit();
      return new WriteResult(pos);
    } catch (ConflictException e) { sleep(jitter(attempt)); }
  }
  throw new OrderingUnavailable(streamId);
}
```

Non-negotiables:

* **Counters acquired in sorted order** across streams in one commit, or deadlock.
* **Idempotency key** in the log, checked with `FILTER NOT EXISTS` in the same operation — retries after an ambiguous timeout must not burn a sequence number or duplicate an event.
* **Epoch read from metadata at connection open and re-validated on conflict**; a changed epoch aborts rather than continues.
* **Zero-padded, fixed-width** seq in any IRI you mint (`urn:commit:0000000000091439`) so IRI range scans and lexicographic sorts behave.
* **`opSeq` supplied by the client via `VALUES`** — the store cannot generate it (see the `NOW()` gotcha).
* **One datatype for seq everywhere** (`xsd:long`), enforced by a shape.

## 6. Reader path

```java
Batch read(Cursor cursor, int limit) {
  requireSameEpoch(cursor);                  // else throw EpochChanged -> resync
  var upper = semantics == PRE_COMMIT ? watermarks.stable() : Position.MAX;
  var batch = store.query(KEYSET_PAGE, bind(cursor, upper, limit));
  auditor.recordContiguity(batch);           // dense tiers: assert seq == prev+1
  return batch;
}
```

Consumers must: persist `(epoch, seq, opSeq)`, be idempotent (at-least-once), treat `EpochChanged` and `CursorExpired` as full-resync signals, and **never** advance past the stable watermark on a `PRE_COMMIT` backend.

## 7. Per-backend wiring

| Adapter | Stream tier | Dataset tier | Notes |
|---|---|---|---|
| Fuseki/TDB2 | `SingleWriterCounter` → `TOTAL_DENSE` | `NativeFeed` (rdf-delta patch versions) | best overall fit |
| RDF4J Native/Memory | `InTxCounter` @ SERIALIZABLE | `InTxCounter` or listener-built log | stamp inside a `SailWrapper` |
| GraphDB | `SingleWriterCounter` | counter statement; `.pie` rule to enforce `prev+1` | plugin API if hot |
| Neptune | `InTxCounter` (retry `ConcurrentModificationException`) | **`NativeFeed`** (`commitNum`/`opNum`) | don't mint a global counter; watch retention |
| Stardog | `InTxCounter` w/ multi-request tx | versioning / virtual-graph `nextval` | ICV-style rule to enforce monotonicity |
| Virtuoso | `NativeSequence` in stored proc | `NativeSequence` | strongest dense option |
| MarkLogic | `InTxCounter` (or skip) | `NativePosition` + `TimeTravel` | as-of reads are native; O4 nearly free |
| Oracle RDF | `NativeSequence` | SCN + Flashback | staging table for bulk |
| AllegroGraph | `InTxCounter` | `insertOrderObservable` as a cross-check | server-side fn for atomic stamp |
| Rya / Halyard / federation | `ExternalSequencer` | `Hlc` → `PARTIAL_CAUSAL` | `min_level` must be ≤ `PARTIAL_CAUSAL` |
| In-memory test store | `InTxCounter` w/ in-proc lock | same | — |

## 8. Conformance TCK

Capability flags are claims. Run against every adapter in CI.

1. **Density under contention** — 64 threads × 500 appends to one stream; assert the observed seqs are exactly `1..N` with no gaps, no duplicates, and every `409`/conflict consumed no number.
2. **Reorder probe (the G2 test)** — concurrent writers with injected delay between allocate and commit; a reader polling `seq > watermark` must observe a strictly increasing, contiguous sequence and **never miss** a committed event. This is the test that either validates or kills your design.
3. **Intra-commit order** — write 3 events in one transaction; assert a deterministic, documented total order across repeated reads and across engines.
4. **Epoch transition** — backup → restore → assert epoch bumped, stale cursor rejected with `EpochChanged`, consumer resyncs without duplicates or loss.
5. **Crash injection** — kill the writer between allocate and commit; assert (dense strategies) no number consumed and no stall; (pre-allocate strategies) the watermark recovers within the lease TTL.
6. **Clock hostility** — step the wall clock backwards 5 minutes mid-run; assert monotonicity holds (catches anyone sneaking `NOW()` into the order key) and HLC still advances.
7. **Keyset pagination stability** — paginate while appending; assert exactly-once delivery per cursor, no skips, no repeats.
8. **Valid-time vs transaction-time** — backfill an old `occurredAt` after newer events; assert the valid-time query orders it *early* and the replay query orders it *late*. Catches the most common modelling bug.
9. **Retraction ordering** — assert/retract interleaving; assert as-of reads at each position return the correct state.
10. **Bulk load** — load 10M triples; assert counters/log are consistent afterwards (or that the load path fails loudly), and the gap scan reports zero.
11. **Feed retention expiry** — force `CursorExpired`; assert it surfaces as a resync signal rather than a silent skip.
12. **Graph proliferation** — create 10⁶ commit graphs; assert `GRAPH ?g` enumeration, backup, and management ops stay within budget (this is what tells you whether to bucket).

Tests 2 and 8 are the ones that distinguish a design that works from one that looks correct.

## 9. Bulk / backfill path

Per-event counter contention is wrong by orders of magnitude for load. Treat as a separate pipeline:

1. Assign `(epoch, seq, opSeq)` **offline** per stream (deterministic, sorted), emitting the log entries alongside the payload.
2. Load with hooks/validation off into a staging graph set.
3. Run the gap scan + monotonicity scan + shape validation as a **gate**.
4. Advance the counters to the high-water mark **in one transaction**, then flip the staging graphs live.
5. Bump the epoch if the backfill rewrote history, so consumers resync instead of resuming into a changed past.

---

# Recommended default

1. **Grain = event**, ordered by **`(epoch, streamSeq, opSeq)`**. Don't rely on per-commit granularity; it doesn't answer your original question.
2. **Per-stream dense counter, incremented in the same transaction as the write.** This makes allocation order equal commit order by construction — no watermark service, no gap-filling, no stalled consumers — and gives you the gap scan, which is the only way to *prove* a consumer hasn't lost data.
3. **Epoch in dataset metadata**, bumped on every rebuild/restore/migration/re-key, part of every cursor. Non-optional.
4. **Dataset-level order is a second, weaker tier**: derive it from the store's change feed (Neptune Streams, rdf-delta) where one exists; otherwise HLC for a contention-free partial order. Do not force a globally dense counter unless you've measured that you can afford the serialization.
5. **Keep valid time (`occurredAt`) strictly separate** from transaction time, and use the transaction-time triple only as a deterministic tiebreak in valid-time queries.
6. **Explicit assert/retract change model**, append-only assertion graphs, bucketed rather than one graph per commit.
7. **Keyset pagination** on the composite cursor; `OFFSET` never appears in the codebase.
8. **Order auditor always on**: gap scan, monotonicity scan, watermark-lag and feed-retention-headroom metrics, alerting on non-zero.
9. **A concurrency TCK** every adapter must pass — with the reorder probe and the valid-time/transaction-time test as gating cases.

So: keep `commitSeq`, but make it `(epoch, streamSeq, opSeq)`, allocate it inside the transaction, shard it by stream, and stop asking it to also be the dataset-wide replay position. That version of your pattern is, I think, about as good as RDF allows.
