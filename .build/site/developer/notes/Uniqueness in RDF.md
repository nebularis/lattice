# Uniqueness in RDF: the problem statement

RDF has *set* semantics for triples, so the only thing you get for free is "no duplicate triples." Everything people actually mean by "unique" has to be built:

| Kind | Example | Difficulty |
|---|---|---|
| **K1. Cardinality / functional property** | a `Person` has at most one `ex:ssn` | Easy (`sh:maxCount 1`, upsert) |
| **K2. Global key (inverse-functional)** | no two `Person`s share an `ex:email` | Hard — cross-node, needs a scan or an index |
| **K3. Composite / scoped key** | `(tenant, orderNumber)` unique per tenant | Hard + normalization issues |
| **K4. Entity identity / de-dup on ingest** | don't mint two IRIs for the same real-world thing | Hard — this is the one that actually bites in production |

Two constraints shape every solution:

1. **SPARQL 1.1 Protocol has no multi-request transactions.** So either your whole check-then-write must fit in **one HTTP request**, or you must use a vendor transaction API. (SPARQL 1.1 Update does not mandate that a request be atomic either — most engines do treat one request as one transaction, but you must verify per engine.)
2. **Atomic ≠ serializable.** `INSERT … WHERE NOT EXISTS` is a textbook **write-skew**: under snapshot isolation two concurrent writers can both see "no such email" and both insert. Atomicity does not save you; you need serializable isolation, a materialized write conflict, single-writer semantics, or an external lock.

Also: **OWL `InverseFunctionalProperty` is not a constraint.** With reasoning on, two people with the same email get silently *merged* (`owl:sameAs`), which is usually worse than a duplicate. It only raises an inconsistency if you have `owl:differentFrom`/UNA asserted. Use it deliberately for record linkage, never as an integrity check.

---

# Part 1 — Portable SPARQL patterns

## P0. Deterministic (hash-derived) IRIs — make uniqueness structural

If the key *is* the identity, the store's triple-set semantics enforces uniqueness for you and concurrent writers converge instead of conflicting.

```
IRI = urn:ex:person:{base32(sha256("person|email|" + normalize(email)))}
```

* Concurrent inserts of the same entity are idempotent, not conflicting. No locks, works on Rya/Halyard/anything.
* **Only use for immutable, natural, non-PII keys.** Hashing an email into an IRI leaks PII into every dataset dump and makes "user changes email" a migration.
* Keep a version/salt in the hash input (`"v1|person|..."`) so you can re-key later.
* Blank nodes are the anti-pattern here: canonicalize/skolemize on ingest.

For mutable keys use P0 for a **key node** and a separate opaque IRI (UUIDv4) for the entity — that's P1.

## P1. Key-claim registry — reduce K2/K3 to K1 (the single most useful trick)

Global uniqueness is expensive and poorly supported. **Per-node cardinality is cheap and universally supported.** So mint a deterministic node for the *key value* and require it to have at most one owner:

```turtle
GRAPH <urn:keys> {
  <urn:key:person-email:JBSWY3DP…>
      a              ex:KeyClaim ;
      ex:constraint  "person-email-unique" ;
      ex:claimedBy   <urn:ex:person/8f2c…> .   # must be maxCount 1
}
```

Benefits:

* The constraint becomes `sh:maxCount 1` on `ex:claimedBy` for `ex:KeyClaim` → expressible in **SHACL Core**, validated **incrementally** by engines that only re-validate the changed subgraph (RDF4J `ShaclSail`, GraphDB). A cross-node `sh:sparql` uniqueness constraint often forces a full scan; this doesn't.
* It's an **index**: "find the person with this email" is a single-triple lookup, no `?o` scan.
* All concurrent writers for the same key touch the **same subject**, which is what makes conflict detection (P3), locking (P6) and sharding work.
* Audit/undelete: retire claims with a tombstone instead of deleting.

Encode scope into the hash input: `"{constraintId}|{tenant}|{graph}|{normalizedKey}"`.

## P2. Conditional write in one request (guarded update)

```sparql
PREFIX ex: <http://example.org/>
INSERT {
  GRAPH <urn:keys> {
    ?claim a ex:KeyClaim ;
           ex:constraint "person-email-unique" ;
           ex:claimedBy  ex:person-42 .
  }
  GRAPH <urn:app> {
    ex:person-42 a ex:Person ; ex:email "ada@example.org" .
  }
}
WHERE {
  BIND(IRI("urn:key:person-email:JBSWY3DP") AS ?claim)
  FILTER NOT EXISTS {
    GRAPH <urn:keys> { ?claim ex:claimedBy ?other . FILTER(?other != ex:person-42) }
  }
}
```

Properties:

* One operation → all-or-nothing: if the key is taken, **neither** the claim nor the payload lands.
* Idempotent on retry (re-running with the same `?other` is a no-op).
* **Ownership monotonicity makes the post-check race-free.** Because a claim is only ever released by an explicit retire operation issued by its *own* owner, a follow-up request

  ```sparql
  ASK { GRAPH <urn:keys> { <urn:key:person-email:JBSWY3DP> ex:claimedBy ex:person-42 } }
  ```
  cannot produce a false positive. This is how you get a correct check-then-act **without** a transaction API — the only gap left is the write-skew of two *different* claimants (fixed by P3/P6).

## P3. Materialize the write conflict (beat snapshot isolation portably)

Under MVCC, two inserts of *different* triples don't conflict. Force them to collide on a row both must rewrite — a pre-created sentinel counter, sharded by key hash:

```sparql
# bootstrap once: for i in 0..1023 -> <urn:keyshard:i> ex:counter 0
DELETE { GRAPH <urn:keys> { ?shard ex:counter ?n } }
INSERT { GRAPH <urn:keys> { ?shard ex:counter ?n1 } ... }   # plus P2's inserts
WHERE  {
  BIND(<urn:keyshard:817> AS ?shard)                        # sha256(key) % 1024
  GRAPH <urn:keys> { ?shard ex:counter ?n }
  BIND(?n + 1 AS ?n1)
  FILTER NOT EXISTS { … as in P2 … }
}
```

Both transactions delete+insert the same statement → one gets a write-conflict abort → retry with jitter. Cost: false conflicts between unrelated keys in the same shard (tune shard count to your write rate). Use only when the engine detects write-write conflicts but not write skew.

## P4. Upsert for K1 (functional properties)

```sparql
DELETE { GRAPH <urn:app> { ex:person-42 ex:email ?old } }
INSERT { GRAPH <urn:app> { ex:person-42 ex:email "ada@example.org" } }
WHERE  { OPTIONAL { GRAPH <urn:app> { ex:person-42 ex:email ?old } } }
```

Don't forget: retire the old key claim and insert the new one in the **same** operation, or you leak claims.

## P5. SHACL as the safety net

Core constraints that are genuinely about uniqueness:

* `sh:maxCount 1` — functional properties **and** the P1 claim node.
* `sh:uniqueLang true` — at most one `rdfs:label` per language tag.

Cross-node uniqueness needs SHACL-SPARQL:

```turtle
ex:PersonEmailUnique a sh:NodeShape ;
  sh:targetClass ex:Person ;
  sh:sparql [
    sh:message "Duplicate email {?email}" ;
    sh:prefixes ex: ;
    sh:select """
      SELECT $this ?email WHERE {
        $this ex:email ?email .
        ?other ex:email ?email .
        FILTER (?other != $this)
      }""" ] .
```

Use it two ways: (a) **commit-time validation** where the engine supports it (below) — then it's a real constraint; (b) **offline auditing**, run on a schedule, results feed a quarantine queue. Check your engine's SHACL feature matrix: several incremental validators support only a subset, and `sh:sparql` may force full-graph revalidation. This is exactly why P1 is worth the indirection.

## P6. External allocator / lock (the boring industrial answer)

For high-contention K4 identity minting, put the uniqueness in something that has a real unique index and treat RDF as the projection:

* `INSERT ... ON CONFLICT DO NOTHING RETURNING id` in Postgres, or DynamoDB `ConditionExpression: attribute_not_exists(pk)`, or Redis `SET key val NX PX ttl` for a lease.
* Then write to RDF **idempotently** (P0/P2), with an outbox/CDC so the projection is retryable and at-least-once safe.
* Partitioning the writer by `hash(key) % N` (Kafka key, actor per key) removes contention entirely and is often simpler than distributed locking.

## P7. Detect-and-reconcile (always have this, regardless)

Nightly/streaming duplicate scan → quarantine graph → merge or reject. Every pattern above has holes (bulk loads, admin `LOAD`, restores from backup, a rogue ETL job that bypasses your service).

```sparql
SELECT ?email (COUNT(DISTINCT ?p) AS ?n) (GROUP_CONCAT(STR(?p);separator=" ") AS ?dups)
WHERE { GRAPH <urn:app> { ?p a ex:Person ; ex:email ?email } }
GROUP BY ?email HAVING (COUNT(DISTINCT ?p) > 1)
```

Ship it as a metric and alert on `> 0`. Decide policy per constraint: `reject | merge (sameAs + rewrite) | quarantine`.

## Normalization: where uniqueness actually breaks

Uniqueness is only as good as your key canonicalization. `"A@B.com"` vs `"a@b.com"`, `"x"` vs `"x"^^xsd:string` vs `"x"@en`, `1.0` vs `1.00`, NFC vs NFD, trailing whitespace, `http://` vs `https://`, IRI percent-encoding, trailing slash. Decide and **freeze** a normalization pipeline per constraint, version it (`v1|...` in the hash), and apply it identically in: the write path, the SHACL/audit query, and the backfill job. SPARQL's string functions can't do Unicode normalization or IDN handling — normalize in the application, not in the query.

## Portability caveats summary

| Assumption | Reality |
|---|---|
| One SPARQL Update request is atomic | Usually yes, not guaranteed by spec — test it |
| Multiple requests can share a transaction | Never in plain SPARQL Protocol; vendor API only |
| `FILTER NOT EXISTS` guard is safe | Only under serializable isolation, single-writer, or P3/P6 |
| `sh:maxCount` is enforced | Only if the engine validates at commit; otherwise it's a report |
| Bulk load respects constraints | Almost never — validate after, or pre-dedup |

---

# Part 2 — Vendor extensions

> Feature sets and isolation levels change between releases; treat this as a map of *where to look*, and verify with the concurrency TCK in Part 3 rather than trusting docs (or me).

**Stardog**
* **ICV (Integrity Constraint Validation)** — add constraints (OWL axioms or SHACL) to the DB; with validation enabled on the transaction, a violating commit is **rejected**. The closest thing in the RDF world to real DDL constraints.
* Snapshot isolation with conflict detection; retry on conflict. P3 (materialized conflict) is the fallback if write-skew is possible.
* Multi-statement transactions over HTTP (`/transaction/begin`, `/{tx}/…`, `/commit`) → you *can* do check-then-write across requests.
* Virtual graphs let you push a key into a relational source that has a real unique index (P6 without a second datastore).

**Ontotext GraphDB**
* **SHACL validation at commit** (ShaclSail-based); plus `sh:shapesGraph` management APIs.
* **Custom rulesets (`.pie`) with consistency checks** — a rule whose match aborts the transaction. Fast, materialization-time, good for K1-style axioms.
* **Plugin API / `UpdateInterpreter`** — intercept statements or specific update patterns in-process and implement a genuine unique index (e.g. back it with Lucene or your own map). This is the highest-performance option if you're willing to write Java.
* Writes serialized per repository, which makes P2 safe in practice.
* Connectors (Lucene/Elasticsearch/Solr) give you a secondary index for fast duplicate lookup.

**Eclipse RDF4J** (and everything built on it)
* `IsolationLevels.SERIALIZABLE` on Memory/Native store → P2 becomes correct, with `SailConflictException` on conflict.
* **`ShaclSail`** — validates the *changed* subgraph at commit and throws `ShaclSailValidationException`, aborting. Best-in-class for the P1 claim pattern (`sh:maxCount 1` is cheap and incremental).
* `NotifyingSail` / `SailConnectionListener` / a custom `SailWrapper` → roll your own commit-time uniqueness index.
* Transaction REST endpoint (`POST /repositories/x/transactions`) for cross-request tx.

**Apache Jena / Fuseki / TDB2**
* TDB2 is **MR+SW** (multi-reader, single-writer) — writers are serialized, so P2 is effectively serializable. Big, underrated win.
* `jena-shacl` + Fuseki SHACL endpoint for validation; no built-in commit-time reject, but you can wrap `DatasetGraph` or add a Fuseki service/filter that validates inside the write transaction and aborts.
* `jena-text` for a Lucene-backed lookup index.

**Amazon Neptune**
* No constraints, no SHACL, no multi-request SPARQL transactions. Each request is one transaction.
* Its conflict model takes locks on index ranges, so `INSERT { … } WHERE { FILTER NOT EXISTS { … } }` can be made safe — *provided the guard pattern touches the same index range as the write*. Consult the current "transaction semantics" doc; Neptune throws `ConcurrentModificationException` and you retry. Design the guard so it reads exactly the claim triple (P1 makes this trivially true).
* **Neptune Streams** for the P7 reconciler; Lambda consumer detects duplicates after the fact.

**OpenLink Virtuoso**
* RDF lives in a SQL engine you can program: stored procedures, triggers, and **user-defined functions callable from SPARQL** (`bif:`/custom). The pragmatic pattern: a SQL table with a real `UNIQUE` index for key allocation, called from a procedure that also writes the quads — one atomic SQL transaction. Full isolation levels available.
* Also supports RDF Views over relational data, so the RDBMS constraint *is* the RDF constraint.

**AllegroGraph**
* **Duplicate suppression** (`spo` or `spog`) — engine-level dedup, and quad-level semantics control.
* Transactions, plus server-side Prolog/Lisp/JS functions for atomic check-then-write.

**MarkLogic** (triples inside a document store)
* Documents are unique by URI → derive the URI from the key (P0) and the database enforces it. Multi-statement transactions, `xdmp:lock-for-update` for pessimistic locking, element range indexes for fast duplicate detection.

**Oracle RDF / Semantic Graph**
* Triples in relational tables; you can put SQL constraints/triggers and unique indexes on staging/application tables, and use `SEM_APIS` validation. Bulk load via staging table with a unique index is a clean P6.

**Blazegraph** — unisolated writes are single-writer → P2 safe; query hints for isolation.
**Oxigraph / embedded stores** — single-writer transactions; do the check-then-write in-process.
**Rya / Halyard / Trino-style federations (no ACID)** — you *must* use P0 + P6 + P7. Do not attempt guarded updates.

---

# Part 3 — Adapter design for pluggable backends

## Core idea

Don't abstract over "constraints" (backends disagree too much). Abstract over **capabilities**, declare constraints **declaratively**, and let a planner pick the strongest enforcement strategy each backend can actually support — with a portable fallback and a mandatory asynchronous backstop.

```
Declarative constraint spec ─┐
                             ├─> Planner ──> Strategy chain ──> Backend adapter (capabilities)
Normalization pipeline ──────┘                    │
                                                  └──> Reconciler (always on)
```

## 1. Constraint spec (backend-agnostic, versioned, in source control)

```yaml
- id: person-email-unique
  version: 1
  kind: unique_key            # unique_key | max_cardinality | unique_lang
  target: { class: ex:Person, graph: urn:app }
  key:    [ ex:email ]        # composite = list
  scope:  { type: tenant, path: ex:tenant }   # global | graph | tenant | parent
  normalize: [ nfkc, trim, lowercase ]        # ordered, frozen per version
  missing_key: skip           # skip | treat_as_null | reject
  on_violation: reject        # reject | merge | quarantine
  enforcement:
    min_level: transactional  # advisory | transactional | strong
```

`min_level` is the contract: deployment fails fast if the configured backend can't meet it, instead of silently degrading.

## 2. Ports

```java
interface GraphStore {                       // thin SPARQL port
  TupleResult query(String sparql, Map<String,Value> bindings);
  void update(String sparql, Map<String,Value> bindings);   // one request = one op-set
  Optional<Tx> begin(IsolationLevel requested);             // empty if unsupported
  Capabilities capabilities();
}

interface Tx extends AutoCloseable {         // vendor tx, when available
  TupleResult query(String sparql, Map<String,Value> b);
  void update(String sparql, Map<String,Value> b);
  void commit() throws ConflictException, ValidationException;
  void rollback();
}

record Capabilities(
  boolean atomicUpdateRequest,      // one request == one transaction (TCK-verified)
  boolean multiRequestTx,           // vendor transaction API
  IsolationLevel maxIsolation,      // READ_COMMITTED | SNAPSHOT | SERIALIZABLE
  boolean detectsWriteWriteConflict,// enables the materialized-conflict strategy
  boolean singleWriter,             // writers serialized (TDB2, GraphDB, Blazegraph)
  CommitValidation commitValidation,// NONE | SHACL_CORE | SHACL_SPARQL | CUSTOM_RULES
  boolean bulkLoadBypassesValidation,
  int     maxSparqlRequestBytes) {}

interface LockService {              // optional; Redis/ZK/Dynamo/Postgres/in-proc
  Lease acquire(String key, Duration ttl);
}

interface KeyAllocator {             // optional; the P6 "real unique index"
  AllocationResult claim(String constraintId, String normKey, String ownerIri);
}
```

Adapters may additionally implement *optional* interfaces the planner will exploit:

```java
interface ShaclProvisioner  { void installShapes(Model shapes); }          // RDF4J, GraphDB, Stardog
interface ConstraintProvisioner { void installNativeConstraints(Spec s); } // Stardog ICV, GraphDB .pie
interface ChangeFeed        { void subscribe(Consumer<ChangeEvent> c); }   // Neptune Streams, RDF4J listener
```

## 3. Strategy chain

Every strategy implements the same interface; the planner composes them.

```java
interface UniquenessStrategy {
  boolean supports(ConstraintSpec s, Capabilities c);
  EnforcementLevel level();     // ADVISORY | TRANSACTIONAL | STRONG
  WriteResult apply(WritePlan plan, GraphStore store) throws UniquenessViolation;
}
```

| Strategy | Requires | Level | Notes |
|---|---|---|---|
| `DeterministicIriStrategy` (P0) | nothing | STRONG | only for immutable natural keys |
| `NativeConstraintStrategy` | `ConstraintProvisioner` | STRONG | Stardog ICV, GraphDB consistency rules |
| `CommitShaclStrategy` (P1+P5) | `commitValidation ≥ SHACL_CORE` | STRONG | claim node ⇒ `sh:maxCount 1`, incremental |
| `TxGuardStrategy` (P1+P2) | `multiRequestTx` + `SERIALIZABLE` | STRONG | read-check-write inside vendor tx |
| `SerializedGuardStrategy` (P2) | `atomicUpdateRequest` + (`singleWriter` ∨ `SERIALIZABLE`) | STRONG | one guarded update + post-`ASK` |
| `MaterializedConflictStrategy` (P2+P3) | `atomicUpdateRequest` + `detectsWriteWriteConflict` | TRANSACTIONAL | retry on conflict; shard tuning |
| `ExternalLockStrategy` (P6) | `LockService` | TRANSACTIONAL | lease + guarded update; fencing token in claim |
| `AllocatorStrategy` (P6) | `KeyAllocator` | STRONG | uniqueness lives outside RDF |
| `GuardOnlyStrategy` (P2) | `atomicUpdateRequest` | ADVISORY | closes the window, not the race |
| `ReconcilerStrategy` (P7) | query only | ADVISORY | **always installed**, never the only one |

Planner:

```java
Strategy plan(ConstraintSpec s, Capabilities c) {
  var candidate = REGISTRY.stream()
      .filter(st -> st.supports(s, c))
      .max(comparing(UniquenessStrategy::level))
      .orElseThrow();
  if (candidate.level().below(s.enforcement().minLevel()))
      throw new UnsupportedDeployment(s.id(), c);   // fail at startup, not at 3am
  return candidate;
}
```

## 4. Write path

```java
WriteResult write(Entity e) {
  var keys = constraintsFor(e).stream()
        .map(c -> new KeyClaim(c, normalize(c, e), claimIri(c, e), e.iri()))
        .toList();                                  // sort by claimIri => no deadlocks
  var plan = new WritePlan(e.payloadQuads(), keys, retiredClaims(e));

  for (int attempt = 0; attempt < maxRetries; attempt++) {
    try { return strategy.apply(plan, store); }
    catch (ConflictException ex) { sleep(jitteredBackoff(attempt)); }
  }
  throw new UniquenessViolation(plan);              // 409 to the caller
}
```

Non-negotiables in the implementation:

* **Claim IRIs sorted** before acquisition — multi-key entities otherwise deadlock.
* **Key rotation is one operation**: retire old claim + insert new claim + update payload, together.
* **Idempotency key** on the request so retries after an ambiguous timeout are safe (`ex:claimedBy` equality check makes P2 naturally idempotent).
* **Fencing token** when using leases: write the lease token into the claim and reject stale writes — a lock service alone is not safe under GC pauses.

## 5. Per-backend adapter wiring

| Adapter | Selected strategy | Extra wiring |
|---|---|---|
| Stardog | `NativeConstraintStrategy` (ICV) or `TxGuardStrategy` | provision constraints at migration; ICV on tx |
| GraphDB | `CommitShaclStrategy` (+ `.pie` for K1) | shapes graph in migration; plugin if hot |
| RDF4J Native/Memory | `CommitShaclStrategy` with `ShaclSail`, `SERIALIZABLE` | wrap sail in config |
| Fuseki/TDB2 | `SerializedGuardStrategy` (single-writer) | SHACL audit job for P7 |
| Neptune | `SerializedGuardStrategy` / `MaterializedConflictStrategy` | Streams → reconciler; retry `ConcurrentModificationException` |
| Virtuoso | `AllocatorStrategy` via SQL unique index + procedure | deploy stored proc |
| MarkLogic | `DeterministicIriStrategy` (doc URI) + multi-statement tx | — |
| Rya / Halyard / federation | `AllocatorStrategy` + `DeterministicIriStrategy` + reconciler | `min_level` must be ≤ TRANSACTIONAL |
| In-memory test store | `ExternalLockStrategy` with in-proc locks | — |

## 6. The part people skip: a conformance TCK

Capability flags are claims; verify them. Run the same suite against every adapter in CI:

1. **Single-key torture**: 64 threads × 500 attempts, same normalized key, distinct entity IRIs → assert **exactly one** claim, all others got `409`, and no orphan payload triples.
2. **Write-skew probe**: two clients, deliberately interleaved, distinct keys hashing to the same shard → assert conflict detection matches `detectsWriteWriteConflict`.
3. **Atomicity probe**: guarded update that must not fire; assert *no* payload triples landed → validates `atomicUpdateRequest`.
4. **Key rotation under contention**: A rotates `k1→k2` while B claims `k2`; assert no lost claim, no double ownership.
5. **Crash injection**: kill the client between update and post-`ASK`; assert monotonic-ownership recovery leaves a consistent state.
6. **Normalization corpus**: Unicode NFC/NFD, `"x"` vs `"x"^^xsd:string` vs `"x"@en`, casing, IDN, numeric forms — identical claim IRIs across write path, SHACL query, and backfill job.
7. **Bulk-load path**: load a file with duplicates, assert the post-load verification query fails the load (constraints are bypassed by design — the *pipeline* must catch it).
8. **Invariant scan**: reconciler over a fuzzed dataset always reports 0 duplicates after a workload.

Test 1 is what separates a design that works from one that merely looks correct.

## 7. Bulk / backfill path

Per-triple guarded writes are 2–4 orders of magnitude too slow for load. Treat it as a separate pipeline:

1. Normalize + dedup **offline** (Spark/DuckDB/`sort -u` on the key column) and emit a conflict report for humans.
2. Generate claim quads alongside payload quads.
3. Load with validation disabled (fast path).
4. Run the P7 verification queries as a **gate** before flipping the graph/version live (load into a staging named graph or a fresh repo, verify, then swap).

---

## Recommended default

For a new system with a pluggable backend requirement:

1. **Opaque UUID entity IRIs** + **P1 key-claim registry** for every unique key.
2. **Guarded single-request update** (P2) as the write primitive, with post-`ASK` confirmation, relying on ownership monotonicity.
3. **Per-backend upgrade** to commit-time SHACL (`sh:maxCount 1` on the claim) or native ICV where available; materialized conflict or external lease where not.
4. **Reconciler + duplicate-count metric always on**, with a quarantine graph and an explicit merge policy.
5. **Normalization pipeline versioned and shared** by the write path, the shapes, and the backfill job.
6. **A concurrency TCK** that every adapter must pass before it's allowed in production.
