# Optimistic concurrency (compare-and-set).

The Tl;Dr here is that there are some elegant techniques, but they are mostly predicated on named graphs, which implies aggregate roots, which implies some way for a domain ontology author to define membership.

## Standard Approach (minus named graphs)

This is indeed usually handled via a versioning field, i.e.,:

```SPARQL
PREFIX ex: <http://example.org/>

DELETE {
  ?entity ex:version ?currentVersion .
  ?entity ex:status ?oldStatus .
}
INSERT {
  # 3. SET: Define the new state and increment the version
  ?entity ex:version 2 .
  ?entity ex:status "Active" .
}
WHERE {
  BIND(<http://example.org/resource/123> AS ?entity)
  
  # 1. READ: Bind the exact current state
  ?entity ex:version ?currentVersion .
  OPTIONAL { ?entity ex:status ?oldStatus . }
  
  # 2. COMPARE: Ensure the state hasn't mutated since the application's last read
  FILTER (?currentVersion = 1)
}
```

If another transaction updated the version to 2 before this query executes, the FILTER condition fails. The application layer will need to inspect the database's response payload (which typically includes an update count or mutation summary), and this isn't guaranteed to provide an update count. Indeed, there are many gaps with this approach...

## HTTP-level CAS: SPARQL 1.1 Graph Store HTTP Protocol, LDP, Solid

Since our architecture updates data at the Named Graph level rather than the triple level, a backend that supports W3C SPARQL 1.1 Graph Store HTTP Protocol will natively support optimistic concurrency using standard HTTP headers.

When you retrieve a graph, the server provides an `ETag`: 
```
    HTTP GET /rdf-graph-store?graph=http://example.org/myGraph
```
(Server responds with ETag: "version-1")

To perform a compare-and-set update, the application sends a PUT or POST request with the If-Match header. If another client has altered the graph, the ETag will have changed, and the triplestore will reject the update.

```
PUT /rdf-graph-store?graph=http://example.org/myGraph
If-Match: "version-1"
Content-Type: text/turtle

<http://example.org/resource/123> <http://example.org/status> "Active" .
```

If each aggregate is one graph, you can push concurrency control up to HTTP:

- **GSP `PUT` + `If-Match: "etag"` then `412 Precondition Failed`.** Not required by the GSP spec; supported by some servers and easy to add in a proxy.
- **LDP** mandates `ETag` and strongly encourages `If-Match` on `PUT`/`PATCH` — a fully standard CAS.
- **Solid N3 Patch** (`text/n3` with `solid:where`, `solid:inserts`, `solid:deletes`) has *built-in* precondition semantics: the server must fail (409) when the `where` clause has no solution or a `deletes` triple is absent. Combined with `If-Match`, it is the cleanest standardized conditional patch in the RDF world.

### Escape hatches that don't depend on store isolation

- **Single-writer queue / partitioned writers.** Route all writes for an aggregate through one process or one partition (Kafka/Rabbit key = aggregate IRI, or an actor). Guards become belt-and-braces and the store only needs durability.
- **Event sourcing / patch logs.** Never mutate in place: append immutable revisions and hash-chain them. **RDF Delta** (Apache Jena) is exactly this — a patch log where each patch names its predecessor, so the log server rejects a patch whose `prev` isn't the head. Same idea in **TerminusDB** (commit graph, Git-like conflict on stale head).
- **CRDT-style merge** (add/remove sets with causal tags, tombstones) when you genuinely have multi-master or offline writers and want convergence instead of rejection.

### Portability Notes

- **Dataset scoping.** `WITH` / `USING` / `USING NAMED` redefine what the `WHERE` clause sees: some stores default to a union-of-all-graphs default graph. Always name graphs explicitly in guards.
- **Blank nodes.** Skolemize everything you intend to update later, since bnodes are not addressable across requests and behave badly in DELETE templates.
- **Guard cardinality.** A guard that matches N solutions instantiates templates N times. Keep guards functional.
- **Never** rely on `INSERT DATA` failing for an existing triple (it's a no-op, not an error).
- **Never** read the version from an eventually-consistent read replica and CAS against the writer.
- Avoid `NOW()`-based versions, due to clock skew and same-millisecond collisions.

## Vendor Extensions

### Stardog 

Stardog uses Multi-Version Concurrency Control (MVCC) with Snapshot Isolation. A stardog adpter can wrap standard SPARQL queries in explicit transactions via its HTTP API or Java SNARL API. If two transactions read the same data and attempt concurrent writes, Stardog natively throws an optimistic locking failure at the commit phase.

### GraphDB & RDF4J

The underlying RDF4J framework (which powers GraphDB) supports an optimistic locking scheme for both its memory and native stores. You can utilize the RDF4J Transaction API (POST /repositories/{id}/transactions) to bundle multiple SPARQL queries. The engine tracks the read/write sets and will throw a TransactionException if a concurrent commit invalidates your transaction's read state.   

## Recommended Technique

Model an aggregate as a named graph, keep version metadata in a separate metadata graph, and keep an **append-only receipt log**:

```sparql
PREFIX : <https://example.org/ns#>
DELETE {
  GRAPH <urn:g:orders/1> { ?s ?p ?o }                       # old payload
  GRAPH <urn:g:meta>     { <urn:g:orders/1> :etag "E1" ; :seq ?n }
}
INSERT {
  GRAPH <urn:g:orders/1> { <urn:order:1> a :Order ; :status "paid" }
  GRAPH <urn:g:meta>     { <urn:g:orders/1> :etag "E2" ; :seq ?n2 }
  GRAPH <urn:g:txlog>    { <urn:rev:E2> :target <urn:g:orders/1> ;
                                        :prev  "E1" ;
                                        :seq   ?n2 ;
                                        :txn   "01HX…client-uuid" ;
                                        :at    ?now }
}
WHERE {
  GRAPH <urn:g:meta> { <urn:g:orders/1> :etag "E1" ; :seq ?n }   # the guard
  BIND(?n + 1 AS ?n2) BIND(NOW() AS ?now)
  OPTIONAL { GRAPH <urn:g:orders/1> { ?s ?p ?o } }               # whole-graph replace
}
```

This fits well with the layered model that `LATTICE` provides and is an elegant, enterprise-grade pattern that treats the RDF database more like a Document Store or Event-Sourced system.

Instead of attaching version numbers to individual triples (which can get messy), we group related data into a Bounded Context or Aggregate (represented by a Named Graph). This cleanly separates business data from infrastructure data, HOWEVER, this requires us to build another substrate layer for the user to be able to define the bounded context. We can leverage `quantification` combined with `surface` to do this, but it is an additional modelling (and therefore congnitive) load. I think it's worth exploring...

### The Architecture

#### **Aggregate (Named Graph)**

By isolating <urn:order:1> and all its sub-components into a specific named graph (<urn:g:orders/1>), you can manage the entire entity as a single unit. When the order changes, you don't patch it; you overwrite the entire graph. This prevents "dangling triples" (e.g., if a previous version had three line items and the new one has two).

#### **The Metadata Graph**

By keeping ETags and sequence numbers in <urn:g:meta>, your actual business data remains pure. If you query the order graph, you only see order data, not database versioning mechanics.

#### Append-Only Log

The <urn:g:txlog> graph acts as an immutable audit trail. Because every write links to the previous ETag (:prev "E1"), it creates a cryptographic-like chain of state changes. This is invaluable for debugging, event-driven architectures, and system recovery.

### Query Plan

The query is a relatively easy pattern to template.

- Guard: The query looks into the metadata graph to verify the aggregate currently has the exact ETag ("E1") the application expects. If another user already modified this order, the ETag will be different. This line will fail to match, yielding zero results, and the entire transaction safely aborts. This works as per the original example.
- Setup: We then calculate the next sequence number ?n2 and grab the current database timestamp. (NB: The new ETag "E2" and the transaction ID "01HX..." are injected into the query string by application code before sending it to the database).
- Sweep: The OPTIONAL block binds every single existing triple ?s ?p ?o inside the order's named graph. It is optional just in case this is a brand-new aggregate with no existing triples.

Using the bindings captured in the WHERE clause, the database completely wipes the current state of the order. It also deletes the old version metadata so it can be replaced.

Finally, the query writes three things atomically:

- The Payload: The fresh, complete state of the order is written into the order graph.
- The Metadata: The new ETag ("E2") and incremented sequence number (?n2) are saved to the meta graph to lock out older transactions.
- The Receipt: A permanent record of who made the change, when it happened, and what the previous state was, is appended to the transaction log graph.

### Variants:

- **Create-if-absent**: `INSERT { … } WHERE { BIND(1 AS ?_) FILTER NOT EXISTS { GRAPH <urn:g:meta> { <urn:g:orders/1> :etag ?e } } }`. (The dummy `BIND` helps engines that dislike a group containing only a filter.)
- **Delete-if-version**: symmetric, guard plus `DROP`-equivalent `DELETE { GRAPH <g> {?s ?p ?o} }`.
- **Value-based CAS / state machines**: skip the version triple entirely and guard on the old value — `DELETE { <o1> :status ?old } INSERT { <o1> :status "shipped" } WHERE { <o1> :status ?old FILTER(?old = "paid") }`. Cheap and natural for status transitions, but you lose the ability to detect "someone else changed a different field". Not applicable for _user data_, but potentially useable for internal nodes.
- **Field-level versions** to reduce false conflicts on hot aggregates (`:etag_shipping`, `:etag_billing`).
- **Content-hash ETags** using RDF Dataset Canonicalization (RDFC-1.0/URDNA2015) instead of counters: gives natural no-op detection and works nicely for offline/mobile sync — at a real CPU cost on large graphs.

## Checking if an update applied (the missing return value)

Since the protocol tells you nothing, use the **append-only receipt**:

```sparql
ASK { GRAPH <urn:g:txlog> { ?rev :txn "01HX…client-uuid" } }
```

This is *definitive and idempotent*, unlike re-reading `:etag` (another writer may have advanced it in the meantime, making a success look like a failure). It also resolves the **outcome-unknown** case after a socket timeout — which is exactly what you need for safe retries.

Prune the log with a TTL/keep-last-N job, and optionally verify chain integrity (`:prev` pointers must form a line, not a fork — a fork is proof of a lost update).

## Making the store *enforce* the invariant (SHACL)

If the store validates SHACL/ICV at commit against committed state, add `sh:maxCount 1` on `:etag`. Then a lost update — both writers deleting `E1` and inserting different new etags — leaves two `:etag` triples and the second committer's transaction is rejected.

This converts a silent lost update into a loud error on stores whose isolation is too weak. Caveat: under pure snapshot isolation where each transaction validates only against *its own* snapshot, both can pass and the merge goes unvalidated. Verify empirically.

## Appendix

### Vendor Notes

These are a snapshot and should be checked against versions and release notes.

| Store | Options |
|---|---|
| **Jena Fuseki / TDB2** | One SPARQL request = one transaction; TDB2 serializes writers (MRSW), so a guarded update is safe. Embedded: `begin(READ)` then `Transactional.promote()` — promotion *fails* if another writer committed since your read. That is a true optimistic CAS at the API level. Pair with **RDF Delta** for a hash-chained patch log. HTTP gives no counts → use receipts. |
| **RDF4J-based (GraphDB, RDF4J Native/Memory, Halyard…)** | The RDF4J **transaction REST API**: `POST /repositories/{id}/transactions?isolation-level=SERIALIZABLE` → tx URL, then `PUT …?action=UPDATE`, `action=SIZE`, `action=COMMIT`. Serializable isolation gives real conflict aborts on commit; `SIZE` gives you a delta signal. `ShaclSail` validates at commit for the §1.3 trick. |
| **Amazon Neptune** | Documented transaction semantics; mutation queries take locks over the matched patterns, and conflicts surface as `ConcurrentModificationException` which the client must retry. Guarded `DELETE/INSERT WHERE` is the documented conditional-write idiom. Use Neptune Streams for CDC. Don't CAS against a reader endpoint. |
| **Stardog** | HTTP transaction API (`/{db}/transaction/begin` → `/{db}/{tx}/update` → `commit`); snapshot isolation by default with a serializable option; ICV can reject commits that violate constraints; versioning add-on gives a commit log. |
| **Blazegraph** | Single-writer + MVCC readers; the update REST response carries a **mutation count** (`<data modified="N" …/>`), which directly answers "did my CAS apply?" Also supports read-from-commit-point time travel. |
| **Virtuoso** | SPARQL updates map onto SQL with row-level locking; update responses include per-graph "N triples — done" messages you can parse; treat SQL `40001` deadlock/serialization errors as conflicts and retry. Watch the union-default-graph behaviour in guards. |
| **RDFox** | Explicit transactions via shell and REST (`/datastores/{n}/transactions`) with read-only/read-write levels; do read + guarded write inside one read-write transaction. |
| **MarkLogic** | Full multi-statement ACID (`POST /transactions`) plus document-level optimistic locking with ETag/`If-Match`; the easiest environment of the lot if triples live inside documents. |
| **AllegroGraph** | Explicit begin/commit/rollback per session; verify the isolation level you're getting before trusting guards alone. |
| **Oracle RDF, Jena/RDF4J on JDBC, Rya/Accumulo, Halyard/HBase** | Borrow the substrate's primitive: SQL `SELECT … FOR UPDATE`/`ORA_ROWSCN`, Accumulo `ConditionalWriter`, HBase `checkAndPut`. |
| **Oxigraph, Qlever, in-process stores** | Usually a single-writer transaction API; wrap it, and lean on the single-writer queue pattern. |

## Testing

Because the guarantee we need (write–write conflict detection under set semantics) is exactly the one vendors describe least precisely, make a **CAS torture test** part of adapter registration and CI:

1. N concurrent workers × K rounds, each: read `:seq`, CAS to `:seq+1` with a unique txn id.
2. Assert: final `:seq` == number of client-reported successes == number of receipts in the txlog, and the `:prev` chain is a line with no forks.
3. Concurrent create-if-absent: exactly one winner, everyone else gets `conflict`.
4. Kill the client mid-flight; assert the receipt query resolves the unknown outcome correctly.
5. Repeat with large payloads, with connection-pool exhaustion, and (if applicable) with reads from replicas.

A backend that passes gets the `LinearizableCas` capability. One that doesn't gets documented or wrapped in a serial API.

## 4. An adapter design for pluggable backends

### 4.1 Domain model

- **Aggregate = named graph.** It's the only unit that every backend can version, replace and ETag cheaply.
- **Version = opaque token** (`string`). Hides integer counters, UUID etags, content hashes, store commit ids and HTTP ETags behind one type. Never let callers do arithmetic on it.
- **Metadata graph** separate from payload graphs, so payloads stay exportable/pure; requires the backend to write two graphs atomically (a capability, see below). Alternative: metadata inside the payload graph — simpler, single-graph CAS, but pollutes the data.

### 4.2 Port interface

```ts
type AggregateId = string;              // graph IRI
type Version     = string;              // opaque

type Expectation =
  | { kind: 'absent' }
  | { kind: 'version'; version: Version }
  | { kind: 'any' };                    // unconditional (explicitly requested)

interface CasCommand {
  id: AggregateId;
  expect: Expectation;
  deletes: Quad[] | 'ALL';
  inserts: Quad[];
  guards?: GuardPattern[];              // extra business preconditions, e.g. status = "paid"
  txnId: string;                        // client-generated idempotency key
}

type CasResult =
  | { status: 'applied';  version: Version }
  | { status: 'conflict'; actual?: Version }
  | { status: 'unknown';  txnId: string };   // caller must call resolve()

interface Snapshot { id: AggregateId; version: Version; quads: Quad[]; }

interface ConditionalRdfStore {
  capabilities(): Capabilities;

  read(id: AggregateId): Promise<Snapshot | null>;
  compareAndSet(cmd: CasCommand): Promise<CasResult>;
  resolve(txnId: string): Promise<CasResult>;          // decides 'unknown'

  // optional, capability-gated
  runUnitOfWork?<T>(f: (tx: TxContext) => Promise<T>): Promise<T>;
  readAt?(id: AggregateId, v: Version): Promise<Snapshot>;
  changesSince?(v: Version): AsyncIterable<Change>;
}

interface Capabilities {
  cas: 'linearizable' | 'best-effort';      // set by the torture test, not by hand
  multiAggregateAtomicity: boolean;
  reportsMutationCounts: boolean;
  httpPreconditions: boolean;               // If-Match / 412
  explicitTransactions: boolean;
  timeTravel: boolean;
  changeFeed: boolean;
  quadsInUpdateTemplates: boolean;          // GRAPH in DELETE/INSERT templates
  maxRequestBytes: number;
  requiresSkolemization: boolean;
  validatesShaclOnCommit: boolean;
}
```

Key design choices:

- `resolve(txnId)` is what makes the port safe over an unreliable network. Every strategy must implement it, even if via the receipt log.
- `Expectation.absent` is first-class, because create-if-absent needs a different SPARQL shape than replace.
- `guards` lets the domain layer express business preconditions (`status = "paid"`) that get compiled into the same atomic guard as the version check, instead of being checked in application code (which reintroduces a race).
- Capabilities are **discovered, not declared**: `cas` is populated by running §3 against the configured backend at startup or in CI.

### 4.3 Strategies behind the port

1. **GuardedSparqlUpdate** — the portable default. Compiles `CasCommand` into a single guarded operation plus a receipt; `resolve` = `ASK` on the txlog. Requires `cas: linearizable` from the test.
2. **ExplicitTransaction** — RDF4J/Stardog/RDFox/MarkLogic style: begin at serializable, read, write, commit; map commit-conflict exceptions to `conflict`. Best fidelity and enables `runUnitOfWork`.
3. **HttpPrecondition** — GSP/LDP/Solid: `PUT`/`PATCH` with `If-Match`; `412`/`409` → `conflict`. Version = HTTP ETag. Trivially correct where available.
4. **NativePromote** — embedded TDB2: `begin(READ)` → compute → `promote()` → `commit()`; `promote()==false` → `conflict`.
5. **PatchLog** — RDF Delta / TerminusDB: submit a patch naming the expected head; stale-head rejection *is* the conflict.
6. **SerializingProxy** — for `best-effort` backends: an external lock or single-writer queue keyed by aggregate IRI, with a fencing token embedded in the version so a paused writer can't apply a stale write.
7. **SubstratePrimitive** — HBase `checkAndPut` / Accumulo conditional writer / SQL `FOR UPDATE` where the store is layered.

### 4.4 Composition

Wrap strategies with decorators rather than baking policy into each one:

```
RetryDecorator            // conflict -> re-read -> re-run domain function -> retry
  ( MetricsDecorator      // conflict rate, retry histogram, unknown-outcome count
  ( ValidationDecorator    // SHACL preflight, skolemization, size/budget checks
  ( OutboxDecorator        // write domain events into the same atomic unit for CDC
  ( strategy ) ) ) )
```

Retry rules that matter in practice:

- **Never blindly replay** the same insert/delete set. On `conflict`, re-read, re-run the domain function against the fresh snapshot, and only then re-issue. The business decision may now be different (or unnecessary).
- Bounded retries with exponential backoff **and jitter**; surface a `ConflictExhausted` error with the observed version history so callers can fall back to a merge UI.
- Treat `unknown` as "call `resolve` before doing anything else"; never retry an unknown outcome directly.
- Track conflict rate per aggregate; a hot aggregate is a modelling smell (split it, or add field-level versions).

### 4.5 Cross-aggregate writes

Expose `runUnitOfWork` only when `multiAggregateAtomicity` is true; otherwise throw `UnsupportedPreconditionError` at the port boundary and force the caller into a saga/outbox. Silently degrading multi-aggregate atomicity is the single worst thing a pluggable adapter can do — it produces corruption that only appears under load, on one backend.

---

## 5. Quick decision guide

- **One aggregate per graph, HTTP in front (LDP/Solid/GSP with ETags)** → use HTTP preconditions. Cleanest, most standard.
- **Store with a real transaction API (RDF4J-family, Stardog, MarkLogic, RDFox)** → explicit serializable transactions; use guards as defence in depth.
- **Store with only a SPARQL Update endpoint (most SaaS endpoints, Fuseki over HTTP, Neptune)** → guarded single-operation `DELETE/INSERT WHERE` + append-only receipt log + retry-on-conflict, gated on the torture test.
- **Weak or unknown isolation** → single-writer queue or external lock with fencing tokens; don't argue with the store.
- **Audit, offline clients, multi-master** → patch log / event sourcing (RDF Delta, TerminusDB) or CRDT merge; CAS then becomes "append against the head you read".


