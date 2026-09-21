# RDF Design

Does the separation of meta-data in our CAS pattern help with monotonic ordering issues? 

# Verdict

Yes — and more than you may realize. Putting the version row in a separate, fixed-size, per-aggregate statement is the single change that makes CAS *and* per-stream dense ordering work on the same mechanism, and your query **already gets the hard part right**: because the guard reads `:seq ?n` and the update rewrites that same statement, allocation order == commit order per aggregate, densely, with no abandoned numbers. That's the G2 reorder hole from the last round, closed structurally. Good.

Three things are missing or wrong in ways that will hurt:

* **You cannot tell whether the CAS succeeded.** SPARQL Update returns no affected-row count. A failed guard is a silent 200 OK.
* **`<urn:rev:E2>` is not namespaced by target** — two aggregates at revision "E2" collide into one receipt subject.
* **No epoch**, and `:etag`/`:seq` are two sources of truth for one fact.

Details, then a corrected version.

---

# Part 1 — What the separation actually buys for ordering

| | Why it helps |
|---|---|
| **A1. The version row is a single hot statement** | The counter read-modify-write and the CAS guard are the *same* operation on the *same* triple. One materialized write conflict serves both. You don't need a separate sequence mechanism at all for the per-stream tier. |
| **A2. O(1) guard regardless of aggregate size** | If `:seq` lived inside `urn:g:orders/1`, the guard read would compete with a whole-graph scan, and counter hold-time would scale with payload size. Separation decouples contention from data volume. |
| **A3. Whole-graph replace can't erase the order** | This is the decisive one. `DELETE { GRAPH <urn:g:orders/1> { ?s ?p ?o } }` deletes *everything* in that graph. If version metadata lived there, every write would destroy its own ordering evidence and re-create it — turning a compare-and-set into a delete-and-hope. Separation is what makes "replace the payload" safe. |
| **A4. Head pointer for free** | `<urn:g:orders/1> :seq ?n ; :head ?rev` is a single-triple lookup. No `MAX()`/`GROUP BY` over the log (S4 last round), no aggregation in the hot path. |
| **A5. Immutable log vs mutable state** | Payload is mutable, meta is a mutable point, receipts are append-only. Three different retention policies, backup cadences, index strategies, and access-control rules — impossible if they're interleaved. |
| **A6. Per-subject sharding is automatic** | Different aggregates touch different subjects in the meta graph, so concurrent writes to different streams don't contend *provided the backend's conflict detection is per-statement*. See the caveat in A7. |
| **A7. It localizes where you must be careful** | Exactly one statement per aggregate is contended, and it's tiny. That's a small enough surface to reason about and to test. |

And what it does **not** buy:

| Not solved | Why |
|---|---|
| **Dataset-wide total order** | `:seq` is per-aggregate. Receipts from different aggregates are mutually unordered. Needs a second tier (below). |
| **Intra-commit order** | One `:seq` per revision; if a revision emits 3 domain events they're unordered. Needs `:opSeq`. |
| **Epoch safety** | The meta graph is destroyed/restored with everything else. Restore resets `:seq`; stale ETags silently match a *different* revision. |
| **Valid time** | `:at`/`NOW()` is transaction time. Backfilled history still needs `:occurredAt`. |
| **Replay / as-of** | Your receipts record *that* a revision happened, not *what changed*. Whole-graph replace discards the diff. See F9. |
| **Cross-aggregate atomic invariants** | Two aggregates in one commit = two counters = lock-ordering discipline required. |

One trap to name explicitly: **do not put a dataset-wide counter in `urn:g:meta`.** The moment you add `<urn:ds:prod> :globalSeq ?n` next to the per-aggregate rows, every write in the dataset contends on one statement and you've thrown away A6.

---

# Part 2 — Findings in the query

Ordered by severity.

### F1 — CRITICAL: the outcome is unobservable

If the guard doesn't match, the update is a legal no-op and the protocol returns success. The client cannot distinguish *"I won"* from *"someone else won"* from *"the aggregate doesn't exist."* Worse, on an ambiguous timeout (response lost, write applied) a retry fails the guard — and looks identical to a genuine conflict.

**Fix:** make the client-supplied `:txn` id a **claim node in a dedicated small graph** so the outcome is a single-triple `ASK`, and check it in the same operation for idempotency. This is literally the key-claim registry (P1) from the uniqueness round, reused:

```sparql
ASK { GRAPH <urn:g:txn> { <urn:txn:01HX…> :rev ?rev } }
```

True ⇒ my write landed (now or on an earlier attempt) ⇒ 200/204 idempotent replay. False ⇒ genuine 412. Unambiguous, O(1), and safe across retries and crashes. **This is the highest-value change in the whole design**, and it's why the receipt log is worth more than the version row.

### F2 — CRITICAL: `<urn:rev:E2>` collides across aggregates

The revision IRI is derived from an etag that is only unique *within* an aggregate. `orders/1` and `orders/2` both reaching "E2" produce one subject carrying two `:target`s, two `:prev`s, two `:seq`s. Your log is silently corrupt and every traversal is wrong.

**Fix:** derive it from the full position, zero-padded:
`urn:rev:orders/1/0000000000000042`. Padding matters — unpadded numeric strings in IRIs sort `"9" > "10"` and break range scans.

### F3 — CRITICAL: no epoch

Restore from backup → `:seq` rewinds → a client holding `ETag: "E5"`/`seq 5` compare-and-sets against a *different* revision 5 and overwrites it. Receipt IRIs are reused. Consumer cursors resume into a changed past.

**Fix:** `:epoch` in the guard, in the meta row, in every receipt, and in the ETag. Bump on any restore/rebuild/re-key/migration.

### F4 — MAJOR: `:etag` and `:seq` are two sources of truth

Nothing keeps them consistent. A partial failure or a buggy client leaves `:etag "E2" ; :seq 41` and both guards now mean different things.

**Fix:** **derive** the ETag; don't store it. `ETag: W/"3-42"` = `{epoch}-{seq}`. `If-Match` maps mechanically onto the guard, HTTP and graph agree by construction, and you delete a whole class of bug. Store only `:epoch` + `:seq` + `:head`.

### F5 — MAJOR: `:prev "E1"` is a string, so the chain isn't traversable

**Fix:** `:prevRev <urn:rev:orders/1/0000000000000041>` as an IRI. This upgrades the receipt log from a flat table into a **verifiable chain**, which gives you the strongest integrity check available:

```sparql
# fork detection: must always return zero rows
SELECT ?prev (COUNT(*) AS ?n) (GROUP_CONCAT(STR(?r);separator=" ") AS ?forks)
WHERE { GRAPH ?log { ?r :prevRev ?prev } }
GROUP BY ?prev HAVING (COUNT(*) > 1)
```

Two receipts with the same `:prevRev` means two writers both won a CAS against the same version — i.e. your isolation guarantee is broken, or the backend lied about its capabilities. This catches lost updates *after the fact*, independent of the counter, and it's the test that would have caught F2 and F3 in production. Add it to the auditor.

If you need tamper-evidence rather than just consistency, add `:hash = H(prevHash ‖ canonicalized-change)` and you have a ledger.

### F6 — MAJOR: idempotency key recorded but never checked

`:txn` is written and never read. As written it's decoration.

**Fix:** as in F1 — guard on it *and* make it queryable. Put it in `urn:g:txn` with the txn id as **subject** so the lookup is a single triple; don't scan `?any :txn "…"` across a growing log (and never `GRAPH ?log { ?any :txn … }` with an unbound graph, which scans every graph in the dataset).

### F7 — MODERATE: unconstrained `:seq ?n` in the guard

`<urn:g:orders/1> :etag "E1" ; :seq ?n` matches *any* seq. If a prior half-applied write left two `:seq` values, the guard matches twice, `?n2` takes two values, and you insert two receipts and two meta rows. Also: numeric datatype drift (`xsd:integer` vs `xsd:long`) changes term equality even where `ORDER BY` still works.

**Fix:** ground the expected values (the client knows them — see F8), pin one datatype, and enforce `sh:maxCount 1` on `:seq`, `:epoch`, `:head` for `:VersionRow`. On RDF4J/GraphDB/Stardog that's a commit-time constraint, so the invariant is enforced rather than merely intended.

### F8 — MODERATE: server-side arithmetic is unnecessary

Because you're doing CAS, **the client already knows the expected version, therefore it knows the next one.** Move `?n+1`, the revision IRI, and the padding to the client and make the whole template ground except `?s ?p ?o` and `?prevRev`. Simpler plan, no numeric-promotion hazard, no `SUBSTR`/`CONCAT` padding gymnastics in SPARQL, and the store's job reduces to *verify and apply*.

### F9 — DESIGN FORK: receipts ≠ a replayable log

Whole-graph replace discards the diff. You can order revisions but you cannot reconstruct state at revision 37, or feed a consumer the change. Decide, explicitly:

* **Receipt log** (what you have): audit trail + CAS outcomes + ordering. Cheap. No replay, no as-of.
* **Patch log**: add `:asserts <urn:g:…/delta/42/add>` and `:retracts <urn:g:…/delta/42/del>`, computed client-side (you already have old and new state). Enables replay, as-of, and CDC. Costs ~2× write volume.
* **Snapshot-per-revision**: never mutate `urn:g:orders/1`; write `urn:g:orders/1/0000…042` and point `:head` at it. Trivially as-of and immutable, but graph count grows without bound → bucket and prune.

Don't leave this implicit; consumers will assume replay exists.

### F10 — MODERATE: `:seq` deletion resets the counter

Delete an aggregate → the meta row goes → a recreate starts at 1 → seq and receipt IRI reuse, which is F3 at the aggregate level.

**Fix:** tombstone. Keep `:epoch`/`:seq`/`:head`, add `:deleted true`, and guard `FILTER NOT EXISTS { … :deleted true }` on normal writes. Counters are monotonic *forever* per stream key.

### F11 — MINOR: the `OPTIONAL` cross-product

The guard yields 1 row, the `OPTIONAL` yields N (one per payload triple), so both templates are instantiated N times. Harmless — quad insertion is set-semantics idempotent — but it's O(N) template instantiation, and it *stops* being harmless the moment you add any non-ground element that varies per row (a `UUID()`, a computed `:opSeq`). Keep the guard's projection separate in your head, and never add per-row derived values to this shape.

Also: you can't substitute `CLEAR GRAPH` here, because `CLEAR` can't be made conditional on the guard. The `OPTIONAL` pattern is correct; just know it reads the whole graph.

### F12 — MINOR: single meta graph, coarse conflict detection

A6 assumes per-statement conflict detection. Some engines conflict at graph or page granularity, which produces **false conflicts between unrelated aggregates** and turns your nice sharded counters back into a hotspot. Shard preemptively: `urn:g:meta/{hash(target) % 64}`. Verify with the TCK, don't assume.

### F13 — MINOR: `:at NOW()` is the only time, and it's the wrong one

Fine as transaction time. Add `:occurredAt` for valid time, and keep `(epoch, seq, opSeq)` as the deterministic tiebreak. Never `ORDER BY ?at`.

---

# Part 3 — Corrected pattern

All positions client-computed; everything ground except the payload sweep and the previous head.

```sparql
PREFIX :    <https://example.org/ns#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

DELETE {
  GRAPH <urn:g:orders/1> { ?s ?p ?o }                     # whole-graph replace
  GRAPH <urn:g:meta/17>  { <urn:g:orders/1> :seq  "41"^^xsd:long ;
                                            :head ?prevRev }
}
INSERT {
  GRAPH <urn:g:orders/1> { <urn:order:1> a :Order ; :status "paid" }

  GRAPH <urn:g:meta/17>  { <urn:g:orders/1> :epoch "3"^^xsd:long ;
                                            :seq   "42"^^xsd:long ;
                                            :head  <urn:rev:orders/1/0000000000000042> }

  GRAPH <urn:g:txn>      { <urn:txn:01HX…client-uuid>
                              :rev <urn:rev:orders/1/0000000000000042> }

  GRAPH <urn:g:txlog/2024-06> {
      <urn:rev:orders/1/0000000000000042>
          a           :Revision ;
          :target     <urn:g:orders/1> ;
          :epoch      "3"^^xsd:long ;
          :seq        "42"^^xsd:long ;
          :opSeq      "1"^^xsd:long ;
          :prevRev    ?prevRev ;
          :txn        "01HX…client-uuid" ;
          :hlc        "0001719412345678:0003:n7" ;
          :recordedAt ?now ;
          :occurredAt "2024-06-26T13:58:02Z"^^xsd:dateTime
  }
}
WHERE {
  GRAPH <urn:g:meta/17> {
    <urn:g:orders/1> :epoch "3"^^xsd:long ;                 # epoch guard  (F3)
                     :seq   "41"^^xsd:long ;                # CAS guard    (F4/F7/F8)
                     :head  ?prevRev .
    FILTER NOT EXISTS { <urn:g:orders/1> :deleted true }     # tombstone    (F10)
  }
  FILTER NOT EXISTS {                                        # idempotency  (F6)
    GRAPH <urn:g:txn> { <urn:txn:01HX…client-uuid> :rev ?any }
  }
  BIND(NOW() AS ?now)
  OPTIONAL { GRAPH <urn:g:orders/1> { ?s ?p ?o } }           # (F11)
}
```

Then, always:

```sparql
ASK { GRAPH <urn:g:txn> { <urn:txn:01HX…client-uuid>
                            :rev <urn:rev:orders/1/0000000000000042> } }
```

→ `true` = applied (this attempt or a previous one) → `204` + `ETag: W/"3-42"`
→ `false` = guard failed → `412 Precondition Failed`, return current `ETag`

**First write / create** is the same shape with the guard inverted:

```sparql
WHERE {
  FILTER NOT EXISTS { GRAPH <urn:g:meta/17> { <urn:g:orders/1> :seq ?any } }
  FILTER NOT EXISTS { GRAPH <urn:g:txn>     { <urn:txn:…> :rev ?any } }
  BIND(NOW() AS ?now)
}
```
with `:seq "1"`, no `:prevRev`, and `If-None-Match: *` on the HTTP side. Note the create path is a **uniqueness** problem, not a CAS problem — it's P2 from round one, and it needs the same isolation caveat: `FILTER NOT EXISTS` on a non-existent row is write-skew-prone unless the backend serializes writers or detects it. On MVCC backends, pre-create the meta row (`:seq "0"`) at aggregate-ID allocation time so *every* write, including the first, is a rewrite of an existing statement.

---

# Part 4 — Wiring the two tiers on top of this

You now have the per-stream tier for free. The dataset tier:

| Backend has | Dataset-order source | Level |
|---|---|---|
| Dense change feed (Neptune Streams, Jena `rdf-delta`) | feed position; receipts carry it as a cache | `TOTAL_DENSE` |
| Native commit position (MarkLogic ts, Oracle SCN) | native, + `TimeTravel` for as-of | `TOTAL_SPARSE` |
| Single writer (TDB2, GraphDB, Oxigraph) | a global counter statement is *affordable here* — writes are already serialized | `TOTAL_DENSE` |
| MVCC, no feed (Stardog, RDF4J, Virtuoso) | **`:hlc` only.** Don't add a global counter | `PARTIAL_CAUSAL` |
| Federated / non-ACID (Rya, Halyard) | external sequencer; CAS itself is unsafe here | `PARTIAL_CAUSAL` |

The pragmatic default that needs no extra machinery: **global reads ordered by `:hlc`, completeness verified per target by `:seq` contiguity.** Sparse across streams, dense within them — so a consumer can both make progress globally and *prove* it missed nothing on any given aggregate. That combination is only possible because the per-aggregate counter is dense, which is only cheap because the version row is separated out. The three decisions reinforce each other.

Adapter delta from the last round: `CasStrategy` slots in where `InTxCounterStrategy` was, since the guard *is* the counter increment. `OrderCapabilities` gains two flags worth testing rather than assuming — `statementLevelConflictDetection` (F12) and `reportsAffectedRows` (F1, vendor-specific; if present you can skip the confirming `ASK`).

---

# Part 5 — TCK additions

Additions to the suite from the previous rounds:

1. **Lost-update probe.** N writers CAS from the same version concurrently → exactly one receipt, all others `412`, `:seq` advanced by exactly 1, **fork query (F5) returns zero rows**.
2. **Ambiguous-timeout replay.** Kill the client after the update but before the confirming `ASK`, then retry the identical request → exactly one receipt, `ASK` returns true, caller sees success not `412`.
3. **Cross-aggregate false conflict.** Concurrent writes to 64 different aggregates in the same meta graph → measure conflict rate. Non-zero ⇒ coarse conflict detection ⇒ shard the meta graph (F12).
4. **Chain integrity under fuzz.** Random interleaved writes/deletes/recreates → `:prevRev` chain is a single unbroken path per target, `:seq` contiguous from 1, no reused revision IRIs.
5. **Restore safety.** Snapshot → write more → restore → replay a *stale but structurally valid* ETag → must be rejected on the epoch guard, not silently applied (F3).
6. **Delete/recreate.** Delete then recreate an aggregate → `:seq` continues, does not restart; old receipt IRIs are never reused (F10).
7. **Empty-graph replace.** CAS against an aggregate whose payload graph is empty → `OPTIONAL` binds nothing, meta and receipt still update correctly (F11).
8. **Large-payload hold time.** CAS on a 1M-triple aggregate under concurrent load → confirm counter hold time and conflict rate don't blow up (validates A2 on this engine).

Tests 1 and 2 are gating.

---

# Recommendation

Keep the architecture — meta/payload/receipt separation is right, and it's what makes CAS and dense per-stream ordering the same mechanism. Change six things:

1. **Make the outcome readable.** Idempotency key as a claim node in a small dedicated graph; confirm with one `ASK`. This is the fix that turns the pattern from "probably works" into "provably works."
2. **Derive the ETag from `(epoch, seq)`.** Delete the stored `:etag`. One source of truth.
3. **Add the epoch** to the guard, the meta row, every receipt, and the ETag.
4. **Namespace and zero-pad revision IRIs** by target and position.
5. **`:prevRev` as an IRI**, and run the fork-detection query as a standing alert — it's your independent check that the backend's isolation claims are true.
6. **Decide receipts vs patches vs snapshots** (F9) now, and write it down, because consumers will assume replay works.

Then leave the per-aggregate counter exactly as you have it, and put dataset-wide order in a separate, weaker, derived tier — sourced from the store's change feed where one exists, HLC where it doesn't.
