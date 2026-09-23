# Review: ADR-A54 (Dataset Topology) and ADR-A67 (Bi-Temporal Model)

This review uses the same lenses as the A51 review: internal soundness, fit with RDF, OWL and triple-store expectations, and consistency with the patterns guide and ADR-A51.

## 1. Verdict

**ADR-A54 chooses sensibly, but its grammar doesn't compose with anything else.** Dataset-per-tenant is a defensible default. Content-addressed TBox graphs and generation-based projections are good ideas. As written, though, it has four problems:

- **Its graph-name grammar collides with A51's.** It cannot be the "shared grammar" the ADR claims.
- **It omits every infrastructure graph the patterns guide needs**, including the meta shards, keys, txn claims, log buckets and dataset/epoch graph.
- **Its `rtstate:{aggregateType}:{gen}` layout is incompatible with the guide's aggregate-per-graph CAS model.**
- **It makes an undefined mechanism (alias graphs) the *sole* promotion path.** It then forbids consumers from naming generations, which A67's as-of queries and every reproducibility guarantee require.

It also re-introduces the environment into identity. This time the environment appears *inside* a tenant dataset, which weakens the isolation argument the ADR uses to reject graph-per-tenant.

**ADR-A67 states the right intent, but the mechanism is not correct as specified.** Two time axes, time as an input to guards, decision records carrying both times, and an explicit hot/analytic split are all right. The problems are these:

- **Transaction time is a wall-clock instant claimed to be "monotone per dataset".** That is not achievable in general. It also has the allocate-then-commit reorder hole (G2) from the guide, so as-of-transaction-time answers can change retroactively. This breaks rule 5's reproducibility promise.
- **The unit of supersession is undefined** (graph? entity? fact?), and there is no retraction model (G5).
- **Valid time is attached to subject nodes, but valid time belongs to facts.**
- **"No in-place correction" is mandated globally.** This contradicts the guide's "configurable, not mandated" position (Chapter 23) and its deletion policy (Chapter 24). It also collides with erasure obligations.
- **There is no epoch**, so restores silently change "what the system believed."

Neither ADR conflicts with RDF or OWL at the level of first principles. Both need explicit rules to stay within what triple stores, SPARQL and OWL reasoners actually do:

- no graph aliasing
- no temporal semantics in OWL
- SHACL and OWL evaluate over a single data graph

---

# Part A — ADR-A54: Dataset Topology and Named-Graph Layout

## A.1 What it gets right

| Decision | Why it is good |
|---|---|
| **Dataset-per-tenant as default** | Isolation is enforced by *which endpoint or dataset a query runs against*, which is store-level structure rather than a filter every query must remember. <br>It also gives you: <ul><li>per-tenant backup and restore</li><li>per-tenant erasure (drop the dataset)</li><li>per-tenant epochs (restoring one tenant need not disturb others)</li><li>per-tenant write parallelism</li></ul> Per-tenant write parallelism is a real win on single-writer stores. TDB2's writer lock is per dataset, so tenants stop serialising behind each other. |
| **Store-per-tenant tier with an unchanged grammar** | The right escape hatch for regulated tenants. Keeping the grammar tier-independent avoids a migration when a tenant moves tiers. |
| **Content-addressed TBox and shapes graphs (`:{revHash}`)** | Pinning ontology and shapes revisions per tenant makes validation and inference reproducible, and allows staggered upgrades across tenants. |
| **Generations for projections** | This is the guide's snapshot-per-revision model (§20.3) applied to derived data. Rollback becomes a pointer move. |
| **A separate staging category** | Correctly separates unadmitted data from belief-bearing data, which matters for A67. |
| **Tenant in graph names even inside a tenant dataset** | Deliberate redundancy that keeps graph names globally unique. That matters for exports, federation, the PostgreSQL `GraphReference`, and merging dumps during migration. |
| **One validator shared with `dal:graphIriTemplate`** | Correct. Graph names generated from ontology templates must satisfy the same grammar. |

## A.2 Findings

### A54-1 — CRITICAL: the A51 and A54 grammars collide

| ADR | Form |
|---|---|
| A51 lineage | `urn:lattice:{tenant}:{scope}:{family}:{localName}` |
| A54 graph | `urn:lattice:{tenant}:{env}:{category}:{…}` |

The second segment is `{scope}` in one and `{env}` in the other. `urn:lattice:acme:prod:tbox:core:ab12…` is ambiguous:

- Is `prod` an environment or a scope?
- Is `tbox` a family or a category?

A validator can only tell them apart with reserved words, and neither ADR defines any.

The revision encodings also differ:

- A51 uses `{lineage}/rev/{profileVersion}-{hash}`, with slash, `rev` and the profile version.
- A54 uses `…:tbox:{layer}:{revHash}`, with colon, no marker and no profile version.

A TBox revision would therefore have two candidate names. The consequence "sharing its grammar with ADR-A51" is currently false.

**Recommendation:** Write one ABNF grammar covering both ADRs, e.g. `urn:lattice:{tenant}:{kind}:{…}`, with a closed, reserved set of `kind` tokens:

- `tbox`, `shapes`, `abox`, `stage`, `proj`, `prov`, `rtstate`, `writeback`
- `meta`, `keys`, `txn`, `log`, `ds`
- `lin` for A51 lineages

For every variable segment, define:

- the alphabet (no `:`, `/`, `?`, `#`)
- the maximum length
- whether it is opaque

Pick one revision encoding.

### A54-2 — CRITICAL: the grammar omits the guide's infrastructure graphs

The patterns guide's strong profile requires these graphs (§2.3):

- meta shards (`urn:g:meta/{n}`)
- the key-claim graph
- the txn-claim graph
- monthly log buckets
- delta graphs
- event buckets
- the dataset/epoch graph

None of these appear in A54. A validator built to this ADR (P0.3.7, "before any dataset is created") will reject them. Alternatively, they get invented ad hoc, which is the outcome A54 exists to prevent.

**Recommendation:** Add categories with their mutability, retention and access class:

| Category | Mutability | Access |
|---|---|---|
| `ds` | epoch, order model | — |
| `meta:{shard}` | mutable point | — |
| `keys` | append + tombstone | restricted, since it indexes PII-derived keys |
| `txn` | TTL | — |
| `log:{yyyy-MM}` | append-only | — |
| `delta:{target}:{pos}:{add\|del}` | append-only | — |
| `events:{streamFamily}:{yyyy-MM}` | append-only | — |
| `inf:{…}` | materialised inferences (see A54-9) | — |

### A54-3 — MAJOR: `rtstate:{aggregateType}:{gen}` is incompatible with aggregate-level CAS

The guide's whole concurrency design rests on **aggregate = named graph** (§14.1, §30.3):

- whole-graph replace
- a version row keyed by the graph IRI
- receipts targeting the graph

A54 puts *all aggregates of a type* into one graph per generation. Two consequences follow:

- **Whole-graph replace no longer works.** Replacing one order's state would replace every order's state. You are left with triple-level value CAS (§14.2), which the guide says "cannot detect someone else changed a different field."
- **Generations of a whole type are copy-on-write at type granularity.** Behaviour runtime state is the highest-churn data in the platform. A new generation per state change is untenable. A generation per batch of changes means runtime state is only as fresh as the last promotion.

**Recommendation:** Make runtime state `rtstate:{aggregateType}:{aggregateId}`, governed by the guide's version row and CAS. Use generations only for *projections derived from* runtime state. If this depends on the open A-Aggregate decision (guide §30.3), say so, and mark `rtstate` as blocked on it.

### A54-4 — MAJOR: alias graphs are undefined, yet made the *sole* promotion mechanism

This repeats the A51 finding F-11, with higher stakes. SPARQL 1.1 and RDF 1.1 datasets have no graph aliasing, and "repoints the alias atomically" has no portable meaning. Each option has a cost here:

- **Materialised copy.** Promoting a large `abox:{appOntology}:current` means copying the entire ABox inside one write transaction. On TDB2 this blocks all other writers in the tenant for the duration.
- **Pointer triple** (the guide's `pat:current`). `:current` stops being a graph that clients can name in `GRAPH <…>` or `FROM <…>`. The query component (C-12) must resolve the pointer and rewrite the query. That is fine, but it must be stated, because it makes C-12 mandatory for every reader.
- **Store-native aliasing.** Some stores offer named-graph aliases (Stardog does in recent versions). Most in the SPI list (TDB2, RDF4J, Neptune, Virtuoso) do not. This needs to be a capability flag, not an assumption.

There is also a consistency issue. A query touching `tbox:…`, `shapes:…` and `abox:…:current` needs all three resolved **from one consistent pointer state**. Otherwise a promotion mid-query mixes generations. The resolution must be read in the same transaction or snapshot as the data.

**Recommendation:** Make the pointer normative:

- Protect it with the guide's version row and CAS.
- Resolve all aliases once per query, in one snapshot.
- Allow an optional materialised projection for tools that must name a graph literally.
- Add a `graphAliases` capability to the A75 SPI.

### A54-5 — MAJOR: "No consumer names a generation directly" conflicts with reproducibility and with A67

Several mechanisms need concrete generation or revision names:

- **Provenance and decision records.** Decisions must cite exactly what they read: the guide's value-based CAS on `snapshotHash` (data-architecture §5.4), and A67 rule 5. A decision that records "`…:current`" cannot be re-derived.
- **A67's analytic as-of path.** It must read prior generations, but it is forbidden to name them.
- **Rollback.** Repointing to generation *n−1* requires naming it.
- **Promotion history is lost.** Repointing overwrites the only record of which generation was current when. A67's "what did the system believe at *T*" depends on the TBox, shapes and projection generations that were current at *T*, not just the ABox data.

**Recommendation:** Reword as follows:

- *Hot-path consumers read through aliases.* Every alias resolution is recorded, and every decision or provenance record stores the **resolved** generation or revision IRIs.
- *Every repoint is an event.* Record it as a receipt with `(epoch, seq)`, the previous target, the new target and the transaction time. This is the guide's version row, receipt chain and `pat:head` applied to aliases.
- *The analytic path resolves "current at T" through that promotion log.*

This is also the event-identity versus content-identity split recommended for A51 (F-9).

### A54-6 — MAJOR: the environment inside a tenant dataset weakens the isolation argument

Every graph name carries `{env}` *inside the tenant dataset*. That implies one of two things:

- **Several environments share one dataset.** Then dev/test/prod isolation is "app layer only", which is exactly why the ADR rejects graph-per-tenant. Prod data would also be one mistaken `GRAPH ?g` away from test fixtures.
- **Datasets are per (tenant, env).** Then the segment is redundant and only costs you. Every graph name changes on environment clone, so every stored reference to a graph name changes too:
  - `pat:target`
  - provenance
  - receipts
  - `GraphReference`
  - any content hash that covers those references (the same failure as A51 F-1)

**Recommendation:** Make the dataset boundary `(tenant, env)` and drop `{env}` from graph names. Record the environment as dataset metadata in the `ds` graph. If the segment is kept for operational legibility, exclude it from all content hashes and state that clones do not rewrite it.

### A54-7 — MAJOR: the isolation claim needs conditions, and the graph-per-tenant rejection is mis-argued

**Isolation.** "Strong at query scope" holds only if all of the following are true:

- **Principal-to-dataset binding happens server-side.** It must be at the gateway or C-12, never chosen by the client.
- **`SERVICE` is disabled or allow-listed for tenant queries.** In a shared Fuseki process, `SERVICE <http://localhost:3030/{otherTenant}/sparql>` is a cross-tenant federation you didn't intend. Jena has context settings controlling `SERVICE`; verify the behaviour for the version you deploy.
- **Admin, upload and GSP endpoints are not exposed per tenant.**
- **Resource isolation exists.** There must be query timeouts, result limits and per-dataset memory bounds. In one JVM, a pathological tenant query can exhaust shared heap and take every tenant down. That is an availability failure, even though confidentiality holds.

**Graph-per-tenant.** It is not inherently "client-side security." GraphDB, Stardog, Virtuoso and MarkLogic all have server-side graph- or document-level access control. Rejecting it for the reference stack (Fuseki, which lacks that) is reasonable, but the stated reason is wrong and will mislead the store-by-store analysis.

### A54-8 — MAJOR: dataset-per-tenant is not portable across the SPI

The concept of a "dataset" varies widely across stores:

| Store | What "dataset per tenant" means |
|---|---|
| Fuseki/TDB2 | Directory per dataset, one JVM hosts many. A per-dataset overhead (node-table caches, file handles) limits tenants per process. |
| RDF4J Server, GraphDB | A repository per tenant, each with its own memory footprint. Fine at tens to hundreds of tenants; needs pooling beyond that. |
| Stardog | A database per tenant. |
| MarkLogic | A database per tenant, or collections with permissions. |
| **Neptune** | **One graph store per cluster.** Dataset-per-tenant *is* store-per-tenant, which is the tier the ADR calls expensive. |
| **Virtuoso** | One quad store per instance. Separation is by graph-level security, i.e. graph-per-tenant. |

**Recommendation:** Add an `isolationUnit` capability to the SPI (`DATASET | GRAPH_ACL | STORE`). The planner then refuses a deployment that cannot meet the tenant-isolation requirement, following the guide's fail-fast `min_level` principle. Also define *tenant sharding across store processes* (N tenants per process, placement recorded), because thousands of tenants cannot share one JVM.

### A54-9 — MAJOR: the ADR doesn't say what OWL reasoning and SHACL validation run over

OWL has no notion of named graphs, and SHACL validates *a* data graph against *a* shapes graph. Once state is split across `tbox`, `shapes`, `abox:*:current`, `abox:ingest:*`, `stage:*` and `proj:*`, the ADR must define the **evaluation closure**: which graphs are unioned for inference and validation.

- **Union-default-graph settings leak data.** Settings like TDB2 `unionDefaultGraph` are common. Without an explicit closure, `stage:*` graphs (meant to be "never queried") and superseded A67 versions flow into inference. You get spurious cardinality violations, `owl:sameAs` merges via inverse-functional properties (guide §1.4), or outright inconsistency.
- **Materialised inferences have no home.** GraphDB puts them in an implicit graph, and Jena and RDF4J do it differently. You need an `inf:{…}` category, keyed to the TBox revision and ABox generation they derive from, invalidated when either changes.
- **`owl:imports` resolves ontology IRIs, not graph names.** A mapping is needed from ontology or version IRI (`https://www.nebularis.org/…foundation`) to `tbox:{layer}:{revHash}`: a catalog graph or the registry. Otherwise imports can't be resolved inside the store.

**Recommendation:** Add a "closure" section:

- **Default graph policy:** empty, with union mode disabled on every store.
- **The inference closure:** `tbox` pinned revisions plus `abox:current`.
- **The validation closure.**
- **"Never queried" is enforced**, by C-12 rejecting unbound `GRAPH ?g` and union-default-graph queries against tenant datasets, or by placing staging in a separate dataset.

### A54-10 — MINOR: other gaps

- **ABox generations are missing from the grammar.** There is `abox:{appOntology}:current` but no `abox:{appOntology}:{gen}`.
  - Is `current` a pointer to a merged generation, or a union of `ingest:{batchId}` graphs?
  - These are very different models for promotion cost and for A67 supersession.
- **Graph proliferation (guide G6) and retention are unaddressed.** `ingest:{batchId}`, `proj:*:{gen}` and `prov:{scope}` all grow without bound. Define:
  - bucketing for `prov`
  - rollback depth (how many generations are retained)
  - pruning rules that never prune a generation still cited by a decision record
- **Cross-dataset operations are never atomic.** Examples are platform-wide TBox upgrades, cross-tenant reference data, the reconciler (P7) and metrics. State that these are sagas.
- **Shared reference data** (Foundation TBox, code lists) is duplicated into every tenant dataset. That is acceptable and even desirable for pinning, but upgrade fan-out needs a runbook. The ADR should also say explicitly that **vocabulary IRIs inside those graphs are never tenant-scoped**, even though the graph names are.
- **`GraphReference` must now locate a dataset.** A graph IRI alone doesn't locate data under dataset- or store-per-tenant. A tenant→endpoint resolver is required, and tenant tier moves are migrations that bump the epoch (guide §24.4).
- **`abox:ingest:{batchId}` as "provenance carrier" is ambiguous.** It needs a rule on whether the batch graph is sealed after admission (see A67-3).

---

# Part B — ADR-A67: Bi-Temporal Model

## B.1 What it gets right

| Decision | Why it is good |
|---|---|
| **Two independent axes** | Correct and standard (Snodgrass-style bitemporal). It matches the guide's valid versus transaction time split (§3.2). |
| **Time as an input to guards (rule 4)** | Exactly right. `decisionTime` is a stimulus field, and the guard never reads a clock. This is what makes behaviour replay deterministic, and it matches QP2 and §23.4 of the guide. |
| **Decision records store both times (rule 5)** | Correct direction. It enables re-derivation without freezing the graph (but see B67-6: times alone are not enough). |
| **Corrections as new versions with `fnd:Evidence` naming the cause** | Matches the guide's `pat:cause` on deletions, and its rule that decision records are never receipt-only (§20.4). |
| **Explicit two-path design** | A materialised current path plus a separate analytic as-of path with relaxed SLOs is honest, and it matches the guide's S6 preference order. Stating it up front is good practice. |
| **One field for A65 provenance and transaction time** | Avoids two write paths disagreeing. |

## B.2 Findings

### A67-1 — CRITICAL: a wall-clock "commit instant" cannot be monotone, and as-of answers can change retroactively

`lattice:transactionTime` is "the commit instant, monotone per dataset." This fails in three ways.

**1. The value cannot be the commit instant.** A triple written *inside* a transaction must be computed before that transaction commits:

- `NOW()` gives execution start time.
- A client or engine value gives the time the value was chosen.

Either way, this is the guide's **G2 allocate-then-commit reorder hole** applied to time:

```
t=100  Tx A stamps transactionTime=100
t=101  Tx B stamps transactionTime=101, commits
t=102  Query "as of transaction time 101" -> sees B, not A
t=103  Tx A commits with transactionTime=100
t=104  Same query "as of transaction time 101" -> now sees A as well
```

The past changed. An as-of-transaction-time answer isn't stable, which is exactly what rule 5 ("re-derive this decision exactly") depends on.

**2. Monotonicity needs a serialisation point.** Wall clocks step back (NTP, VM migration), and two writers can stamp the same millisecond (guide Ch. 13, TCK O-6). Achieving "monotone per dataset" requires either:

- a single writer, as in TDB2, where you can compute `max(prev + 1, now)` inside the serialised write, or
- a dataset-wide hot statement, which the guide warns against on MVCC stores (G3, §17.2).

**3. It contradicts the guide's `NOW()` policy.** The guide allows `NOW()` only for audit-only `recordedAt` and forbids it as an ordering key (§23.4, QP2). A67 uses transaction time as the as-of axis, which *is* an ordering key.

**Recommendation:** Define transaction time as a **position**:

- `(epoch, seq)` from the guide's per-dataset or per-stream ordering, with the instant carried as a human-facing label.
- As-of-transaction-time queries resolve an instant to a position through the log.
- They are only answered up to a **stable watermark**: the highest position below which no commit can still land (guide `pat:stableWatermark`).
- A query for "as of T" where T is above the watermark is either refused or answered as of the watermark, and the response says which.

On a single-writer store, an in-transaction counter gives this for free.

### A67-2 — CRITICAL: no epoch, so restores rewrite belief history silently

Restoring a tenant dataset from backup discards every transaction between backup and restore. Wall-clock transaction times don't rewind, so nothing reveals that "what the system believed at *T*" for *T* in the lost window has changed. Consider a decision record from that window that says "re-derive against transaction time *T*":

- It will re-derive against different data.
- It will produce a different answer.
- There will be no error.

**Recommendation:** Adopt the guide's epoch (G4, F3, §24.4). A restore bumps the epoch, and as-of queries and decision re-derivation compare epochs. A decision recorded under an earlier epoch whose position exceeds the restore point is reported as **not reproducible**, not silently re-derived.

### A67-3 — MAJOR: the unit of versioning and supersession is undefined, and there is no retraction

Rule 1 stamps *graphs*. Rule 2 supersedes *versions*. The ADR never says what a version is.

- **If the unit is a graph** (e.g., A54's `abox:ingest:{batchId}`):
  - Correcting one fact in a million-triple batch means a new version of the whole batch, or a partial supersession the model cannot express.
  - "Carries `lattice:transactionTime`" in the singular also implies assertion graphs are **write-once**. Any graph written by more than one commit (`prov:{scope}`, `rtstate`) would have several commit times.
- **If the unit is an entity or a fact**, graph-level stamping is not enough. You need per-version nodes, which is the guide's patch-log or snapshot model.
- **There is no retraction.** A correction that *removes* a fact ("this claim never existed") has no successor to supersede with. This is the guide's G5: additions are ordered, retractions are not.

**Recommendation:**

- Declare the versioning unit per family (entity or aggregate recommended), using the guide's receipt models (§20).
- State that transaction-time-stamped assertion graphs are **sealed** once committed.
- Add an explicit retraction: a tombstone version or `pat:retracts`, carrying evidence.
- Define transaction-time end as derived: the successor's transaction position, never stored and mutated.

### A67-4 — MAJOR: valid time on subject nodes misrepresents facts

"Subject nodes also carry `fnd:TemporalScope`" attaches valid time to *entities*. Valid time is a property of *facts*, not of subjects. Take a person with two addresses over time:

```turtle
ex:p ex:address ex:addrA , ex:addrB ;
     fnd:hasTemporalScope [ fnd:validFrom "2020-01-01"^^xsd:date ] .
```

Nothing says which address held when. With a single scope per subject, you cannot represent an entity whose facts have different validity. The model has to be one of these:

- **N-ary relation nodes.** For example, `ex:Residence` with `ex:of`, `ex:address` and a `fnd:TemporalScope`. This is the standard OWL-compatible pattern, and it is what `fnd:TemporallyScoped` as a mixin for "time-bound domain facts" implies.
- **RDF 1.2 triple terms or annotations** on the asserted triple, if the target stores support them.
- **Named graph per validity context.** This conflicts with A54's layout and proliferates graphs.

**Recommendation:** Mandate the n-ary pattern for temporally scoped facts. List RDF 1.2 annotation as a future option gated on store capability. Say explicitly that a temporal scope on an entity node means "the entity existed," not "its properties held."

### A67-5 — MAJOR: OWL and SHACL over history produce false inconsistencies

OWL and SHACL have no temporal semantics. If superseded and current versions sit in the same evaluation closure ("the prior version remains queryable"), the following things break:

- Functional properties see two values, which produces an inconsistency, or `owl:sameAs` inference between the two objects.
- `sh:maxCount 1` fails on every corrected entity.
- Inverse-functional properties merge past and present individuals (guide §1.4).
- Disjointness axioms fire across versions (a thing that *was* a `Prospect` and *is* a `Customer`).

**Recommendation:** Add the rule that **reasoning and validation are only ever performed over a snapshot**:

- the materialised current, or
- an as-of materialisation.

They are never performed over the union of history. This is the A67 half of A54-9, and it should be stated in both ADRs.

### A67-6 — MAJOR: decision records need read positions, not just times

Rule 5 stores valid time and transaction time. Re-derivation also needs to know **exactly what was read**:

- which TBox and shapes revision, and
- which projection generation.

The hot path reads materialised projections, which lag the authoritative layer. The guard may have read generation *g* even though transaction time *T* implies *g+1*. Re-deriving "as of *T*" against the authoritative layer then produces a different input than the one actually used.

**Recommendation:** Decision records store:

- `decisionTime`
- the transaction position `(epoch, seq)`
- the **resolved** revision and generation IRIs of every graph read (see A54-5)
- optionally a snapshot hash

This is the guide's value-based CAS on `snapshotHash` (data-architecture §5.4). It makes re-derivation exact without depending on the analytic path.

It also resolves a hidden problem in rule 4: "replay supplies both [times]". If replay must query as of the pinned transaction time, deterministic replay depends on the slow analytic path. Replaying from recorded read positions avoids that.

### A67-7 — MAJOR: the global "no in-place correction" conflicts with the guide and with erasure

- **The guide conflicts.** Chapter 23 argues that bi-temporality should be *configurable, not mandated*, citing data explosion and domain variety. Its Appendix D records "in-place update is configurable only with a per-family declaration." A67 mandates immutability for all "runtime A-Box assertion graphs" without addressing that argument. One of the two documents has to change.
- **Scope is undefined.** Does "runtime A-Box" include `rtstate` (high-churn behaviour state), `proj` (derived) and `writeback`? Applied to `rtstate`, it means snapshot-per-revision for the most frequently written data in the platform.
- **Correction versus update is undefined.** A change *in the world* (the address changed) is a valid-time event. A *correction* (the address was always wrong) is a transaction-time event. The ADR forbids in-place correction but is silent on in-place update. The storage layer cannot distinguish the two unless the write API does.
- **Erasure conflicts.** "The prior version remains queryable" is incompatible with GDPR Article 17 and with the guide's §24.0 ("deletes are a valid and sometimes necessary policy"). You need an erasure exception such as:
  - redaction with a tombstone and evidence, or
  - crypto-shredding of payload with retained structural provenance.

  Otherwise the ADR mandates a compliance violation.

**Recommendation:**

- Make "no in-place correction" mandatory for **belief-bearing families**: admitted A-Box facts, decision records, provenance.
- Leave other families (`rtstate`, operational state) to the guide's per-family declaration.
- Define update and correction as distinct write operations.
- Add an erasure clause that overrides retention and immutability, leaving evidence behind.

### A67-8 — MINOR: other gaps

- **Interval semantics.** Specify half-open `[validFrom, validTo)`, open-ended `validTo`, and how untimed facts behave (always valid). "Omitting both means current beliefs about now" means results depend on query execution time. The response must echo the resolved `asOf` values so results can be reproduced.
- **Datatypes.**
  - Use `xsd:dateTimeStamp` (timezone mandatory) for transaction time.
  - Fix the valid-time datatype per property. SPARQL 1.1 defines comparison only for `xsd:dateTime`. Comparing `xsd:date` to `xsd:dateTime` is a type error in standard SPARQL, so the filter silently evaluates false. Several engines extend this differently.
  - Mixed date and dateTime valid times will silently drop rows from as-of queries.
- **Vocabulary proliferation.** There are now three properties for one concept:
  - `lattice:transactionTime` (A67)
  - `pat:recordedAt` (guide)
  - `fnd:recordedAt` (Foundation, domain `fnd:Evidence`)

  Pick one. Guide Appendix E item 3 is where this decision belongs.
- **`fnd:supersededBy` with content-addressed revisions has the revert-cycle problem** from A51 F-9 (A → B → A). Supersession must chain version *events*, not content revisions.
- **Identifier collision.** A67's "G6 (no `now()` …)" is a different G6 from the guide's G6 (graph proliferation). A51 has a G9 as well. These are three identifier namespaces with overlapping labels, the same class of problem as the guide's *cursor* versus *Position* collision. Prefix them (e.g., `AR-G6` for Architecture Review gaps).
- **Freshness of the materialised current.** Is the current projection updated in the same transaction as the authoritative write, or asynchronously?
  - If asynchronously, it violates read-your-writes and needs a staleness SLO.
  - CAS guards (guide Ch. 19) must read the authoritative layer, never the projection. Say so.

---

# Part C — Conformance with RDF, OWL and store expectations

| Expectation | A54 | A67 | Notes |
|---|---|---|---|
| Graph names are IRIs; their denotation is open (RDF 1.1) | ✅ | — | URN graph names are fine. Document that graph IRIs denote graphs, not ontologies. |
| No graph aliasing in SPARQL or RDF datasets | ⚠ Conflict | ⚠ via as-of | A54-4 |
| Default graph and union-default-graph behaviour varies by store | ⚠ Gap | ⚠ Gap | A54-9. Must be pinned per store. |
| `owl:imports` resolves ontology IRIs | ⚠ Gap | — | Needs a catalog to graph names. |
| OWL has no named graphs and no time | ⚠ Gap | ⚠ Conflict | Reason and validate over snapshots only (A54-9, A67-5). |
| SHACL validates one data graph | ⚠ Gap | ⚠ Conflict | Define the validation closure. |
| Valid time is a property of statements | — | ⚠ Conflict | A67-4. Use the n-ary pattern or RDF 1.2 annotations. |
| SPARQL temporal comparison defined for `xsd:dateTime` only | — | ⚠ Gap | A67-8 |
| Multi-dataset support is store-dependent | ⚠ Conflict | — | Neptune, Virtuoso (A54-8) |
| Transactions are per dataset | ✅ with caveat | — | Cross-tenant operations are sagas. |
| `SERVICE` federation within one process | ⚠ Risk | — | Disable or allow-list for tenant queries. |
| GDPR erasure | ✅ (drop dataset) | ⚠ Conflict | A67-7 |

---

# Part D — Cross-document consistency

| Topic | A51 | A54 | A67 | Patterns guide | Resolution |
|---|---|---|---|---|---|
| Second URN segment | `{scope}` | `{env}` | — | `urn:g:` examples | One ABNF grammar with a reserved `kind` token (A54-1) |
| Environment in identity | Entity base rewritten on clone | In every graph name | — | Absent | Dataset per `(tenant, env)`; no env in any identifier (A51 F-1, A54-6) |
| Revision encoding | `/rev/{pv}-{hash}` | `:{revHash}` | "new version" | `urn:rev:{agg}/{seq}` (no epoch) | Content revision versus event receipt, both named in the grammar, epoch in receipts |
| Alias / current | "repointed atomically" | "sole mechanism, never name generations" | as-of must read prior versions | `pat:current` pointer plus CAS | Normative pointer; every repoint a receipt; records store resolved IRIs (A54-4, A54-5) |
| Aggregate granularity | — | `rtstate:{type}:{gen}` | versioning unit undefined | aggregate = named graph | Per-aggregate graphs (A54-3, A67-3); resolve A-Aggregate first |
| Transaction time | — | — | wall-clock instant, monotone | `(epoch, seq)` position; `recordedAt` audit-only | Position is the axis, instant is the label (A67-1) |
| Epoch | — | absent (no `ds` graph) | absent | mandatory in strong profile | Add to grammar and to A67 (A67-2) |
| In-place update | — | — | forbidden globally | configurable per family | Mandatory for belief-bearing families only (A67-7) |
| Deletion / erasure | Rule 1 (no PII in IRIs) | drop dataset | "prior versions remain queryable" | policy with audit and tombstones | Erasure clause in A67 |
| `NOW()` | — | — | "engine pins at commit" | audit-only | Consistent once A67-1 is fixed |
| Infrastructure graphs | — | missing | — | seven kinds | Add to grammar (A54-2) |
| Time vocabulary | `fnd:Version` | — | `lattice:transactionTime` | `pat:recordedAt` / `fnd:recordedAt` | One property |

**Positive interaction:** dataset-per-tenant plus the guide's dataset-level epoch gives per-tenant epochs. Restoring one tenant invalidates only that tenant's ETags and consumer positions. That is a real operational advantage and worth stating in A54.

---

# Part E — Suggested amendments (sketch)

### ADR-A54

1. **Dataset boundary:** `(tenant, env)`. `isolationUnit` becomes an SPI capability, and the planner fails fast when isolation can't be met. `SERVICE`, admin and upload endpoints are disabled for tenant principals. Per-dataset query timeouts and memory limits are required.
2. **One grammar with A51:** `urn:lattice:{tenantId}:{kind}:{…}`, with a reserved `kind` set:
   - `lin`, `tbox`, `shapes`, `abox`, `stage`, `proj`, `inf`, `prov`
   - `rtstate`, `writeback`
   - `ds`, `meta`, `keys`, `txn`, `log`, `delta`, `events`

   Segment alphabet `[a-z0-9-]`. No environment segment.
3. **Aliases:**
   - The `pat:current` pointer, protected by CAS, is normative.
   - Every repoint is a receipt.
   - Resolution happens once per query, in one snapshot.
   - Records cite resolved IRIs.
   - An optional materialised projection is allowed where a literal graph is required.
4. **Runtime state:** `rtstate:{aggregateType}:{aggregateId}` under the version row and CAS. Generations only for projections.
5. **Closures:**
   - The default graph is empty, with union mode off.
   - Inference and validation closures are named explicitly and are always snapshots.
   - Staging lives in a separate dataset, or C-12 enforces "never queried."
6. **Retention:** rollback depth, pruning that respects citations, and `prov` bucketing.

### ADR-A67

1. **Transaction time** is the position `(epoch, seq)`, with an `xsd:dateTimeStamp` label. As-of queries are answered only up to the stable watermark, and the response echoes what was resolved.
2. **Epoch is mandatory.** Decisions recorded past a restore point are reported as non-reproducible.
3. **The versioning unit is declared per family** (entity or aggregate). Assertion graphs are sealed. Retraction is explicit. Transaction-time end is derived.
4. **Valid time uses the n-ary fact pattern** with half-open intervals and one datatype per property.
5. **Reasoning and validation run over snapshots only.**
6. **Decision records store** `decisionTime`, the read position, resolved revision and generation IRIs, and optionally a snapshot hash. Replay uses these, not the analytic path.
7. **Immutability** is mandatory for belief-bearing families and per-family for everything else, with distinct update and correction operations and an erasure clause.
8. **One transaction-time property**, shared with A65 and aligned with `fnd:recordedAt`.

With these changes, A51, A54 and A67 would describe a single identity, topology and time model that the patterns guide can implement directly. As it stands, each ADR is individually plausible, but the three do not yet fit together.