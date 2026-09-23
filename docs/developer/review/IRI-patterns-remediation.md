# Remediation Plan — RDF Operational Patterns & Identity Documentation Set

**Applies to:** `rdf-sparql-patterns-guide.md`, `iri-identity-patterns.md`, `ADR-A82`, `ADR-A68`
**Inputs:** `ADR-A68-A82-iri-patterns-review.md` (findings B1–B13, C1–C3; document truncated mid-C3)
**Status of this plan:** proposed remediation specification. It does not rewrite the guides; it specifies the changes, their exact location, and the evidence required to close each gap.

---

## 0. Summary

### 0.1 Disposition of the review

| Review finding | Disposition | Note |
|---|---|---|
| B1 epoch guard does not protect restore | **Accepted, fix amended** | Reviewer's "rewrite every version row" is O(aggregates) and non-atomic on most stores. Root cause is a single overloaded property name. See WP‑1. |
| B2 lost updates invisible; fork query cannot fire | **Accepted, fix amended** | Keep deterministic revision IRIs; move detection onto txn cardinality and receipt property cardinality. See WP‑2. |
| B3 revision IRI namespace collision | **Accepted** | Requires an injective, width-fixed derivation, not prefix stripping. WP‑2. |
| B4 `?n + 1` datatype promotion | **Accepted, fix rejected as non-portable** | `xsd:long(...)` is not in SPARQL 1.1's constructor-function table. Use `STRDT`. WP‑3. |
| B5 pre-created row makes first CAS impossible | **Accepted, scope widened** | Also exposes an undefined `Expectation.Absent` semantics and an undefined recreate path. WP‑4. |
| B6 append form does not maintain head/chain | **Accepted** | WP‑4. |
| B7 weak ETags never satisfy `If-Match` | **Accepted, extended** | Strong tags require a representation dimension. WP‑5. |
| B8 outcome resolution after timeout | **Accepted, extended** | The defect is the conflation of *definite response* with *timeout*. WP‑6. |
| B9 retention pruning breaks quiet aggregates | **Accepted, extended** | §24.2 is also self-contradictory about `pat:head`. WP‑7. |
| B10 fencing tokens never advanced | **Accepted** | WP‑8. |
| B11 global HLC pagination reintroduces G2 | **Accepted, extended** | Requires a concrete watermark mechanism, not just a rule. WP‑9. |
| B12 contention sharded for meta only | **Accepted, extended** | Sharding the keys graph has an access-control consequence. WP‑10. |
| B13 lock ordering via `WHERE` order | **Accepted, partially retained** | The sorted-acquisition rule remains valid for the multi-request transaction strategies. WP‑11. |
| C1 A51 treated as live | **Accepted** | WP‑14. |
| C2 `fnd:replacedBy` undefined | **Accepted** | WP‑14. |
| C3 identifier widths not fixed | **Accepted; completed here** | The review is truncated. Completed as A‑1/A‑2 below. WP‑0, WP‑14. |

### 0.2 Additional gaps found in this review of the review

Fifteen further defects, four of them blocking. The review's focus on the write path missed an entire class: **privacy and erasure interact with every history model in the guide, and neither document set closes that loop.**

| ID | Gap | Severity |
|---|---|---|
| A‑1 | Padding widths still unfixed (`REV_WIDTH = 16 … 19 in production`; claim `nbytes=16` vs 80-bit examples), violating catalogue §10.2 verbatim. Completes review C3. | Blocking |
| A‑2 | The epoch component of a revision IRI is **unpadded** (`e3`), so any cross-epoch lexical scan misorders (`e10 < e3`). Catalogue §10.2 requires one exact width per identity-bearing position. | Blocking |
| A‑3 | **Restore resurrects erased personal data.** A graph drop under ADR‑A68 is not recorded anywhere outside the dataset, so the §24.4 restore runbook reinstates erased payload. The epoch bump does not help. | Blocking |
| A‑4 | **Patch-log and snapshot-per-revision receipt models make ADR‑A68 erasure impossible** for any family containing personal data: the delta/snapshot graphs are a second, immutable copy. No document notices the interaction. | Blocking |
| A‑5 | Claim-scheme (HMAC secret) rotation is described as "a new version salt and a backfill", but **uniqueness is not enforced across scheme versions during the migration window**. Two owners can hold `v1` and `v2` claims for the same key. | Major |
| A‑6 | §6.2's "ownership monotonicity" is asserted unconditionally; catalogue §6.4 states erasure breaks it. The post-`ASK` correctness argument therefore has an undeclared exception. | Major |
| A‑7 | The guide's own S3 gap scan, S4 head query and F5 fork query use `GRAPH ?log` with a `STRSTARTS` prefix filter — forbidden by F6 (its own rule) and by catalogue §12.3. S4 additionally hard-codes one month bucket, so it returns the wrong head for any stream last written in an earlier bucket. | Major |
| A‑8 | The P7 reconciler and the `ex:PersonEmailUnique` SHACL query group on the **raw** literal, so they cannot detect the normalization-variant duplicate that §4's own K4 example shows. Data that bypassed the claim path is undetectable. | Major |
| A‑9 | S5's valid-time query orders on a possibly-unbound `?op` — the exact failure §13 forbids and S2 guards with `COALESCE`. | Moderate |
| A‑10 | Recreate-after-tombstone is not an executable operation: the CAS shape's `FILTER NOT EXISTS { pat:deleted true }` blocks it and the create path's `FILTER NOT EXISTS { pat:seq ?any }` cannot match. | Moderate |
| A‑11 | HLC `send()` has no bound on the logical counter; past 9999 it breaks both the `pat:hlc` shape pattern and lexical order. `receive()` is likewise unclamped. | Moderate |
| A‑12 | `pat:opSeq` appears on a `pat:Revision` in §19.1, but Appendix A defines it as an ordinal *of an event within a revision*, and `pat:EventOrderShape` targets event subjects. Undefined semantics on the receipt. | Moderate |
| A‑13 | Three names are used for valid time (`ex:occurredAt`, `pat:occurredAt`, declaration key `valid_time.property`). | Moderate |
| A‑14 | Vocabulary incompleteness: `pat:retentionLowWaterMark` is used in S3 and absent from Appendix A; `pat:etag` is constrained by `VersionRowShape` and absent from Appendix A; `pat:stableWatermark`'s `{epoch}:{seq}` string is delimited concatenation with no declared widths or parse rule (catalogue §7.2, §10.2). | Moderate |
| A‑15 | Port/client contradiction: §25.1 declares `Version` opaque with "never do arithmetic on it", while §19.4's Python client is built entirely on arithmetic over `(epoch, seq)`. | Moderate |

### 0.3 Overall judgement

The review's verdict stands and is strengthened: **the patterns guide must not be implemented, and no production data may be written, until Gate 1 and Gate 2 below are passed.** The identity catalogue and ADR‑A82 are structurally sound; they need six targeted additions (WP‑15), most of which exist because the catalogue's rules were correct and the guide silently broke them — the catalogue's own refusal table did not require the compiler to *detect* those breaks.

---

## 1. Root-cause remedy applied first: separate the profile from the narrative

Eleven of the twenty-eight findings (C3, A‑1, A‑2, A‑12, A‑13, A‑14, B3, B7's representation dimension, and the illustrative-value drift in Chapters 2, 5, 6, 7) share one cause: **the patterns guide carries identity-bearing grammar inside narrative prose and hand-typed examples.** Catalogue §7 and §14.3 already forbid this; Appendix E item 9 already flags it as open. Patching each occurrence leaves the mechanism that produced them.

**WP‑0 — Extract a normative reference profile.**

Create two new artefacts:

1. `docs/architecture/profiles/reference-urn-profile-v1.md` — a concrete, versioned, opt-in identity profile in the sense of ADR‑A82 §6, containing **only** normative grammar:
   - every base (`urn:g:`, `urn:rev:`, `urn:key:`, `urn:txn:`, `urn:ev:`, `urn:stream:`, `urn:ds:`) with its owner and stability class;
   - exact widths: sequence **19** decimal digits, epoch **10** decimal digits, `opSeq` **5** decimal digits, claim digest **128 bits / 26 unpadded base32 characters**, P0 digest **160 bits / 32 characters**;
   - the digest schemes in catalogue §7.4 form (function, input literal, tuple encoder, encoding, exact width, verification-digest policy);
   - the tuple encoder (catalogue §7.2 length-prefixed UTF‑8) and each frozen normalization pipeline with its version;
   - the target-token derivation for revision namespaces (WP‑2);
   - the graph-locator templates including all shard dimensions (WP‑10).
2. `fixtures/identity/reference-urn-profile-v1/` — golden test vectors for every derived identifier, satisfying catalogue §14.3.

**Then, in the patterns guide:** replace every inline grammar statement and every hand-typed identifier with (a) a reference to the profile section, and (b) an example drawn from the fixture file by the documentation build. Add a build check that fails if any IRI literal in the guide is not present in the fixtures.

*Where:* new files; guide Chapter 2 (§2.1–2.3), Chapter 5, Chapter 6 (§6.1), §7.1–7.2, §10.1–10.2, §19.1, §19.4 (`REV_WIDTH`), §20.2–20.3, Chapter 13's padding row, Appendix A preamble, Appendix E item 9.

*Rationale to record in the guide:* `REV_WIDTH = 16` with a comment saying 19 in production is the exact anti-pattern catalogue §10.2 names. `MFRGGZDFMZTWQ2LK` and `GEZDGNBVGY3TQOJQ` are base32 of `abcdefghij` and `1234567890`; they are 80 bits where `claim_iri` defaults to 128, and they are presented as HMAC outputs. Appendix D.1 claims this class of drift was fixed; it was not.

---

## 2. Work packages

Each package states the change, the exact location, and the evidence that closes it.

### WP‑1 — Epoch integrity and restore safety (B1, A‑2, A‑3)

**Root cause of B1:** `pat:epoch` names two different things — the dataset generation and the epoch a version row's `pat:seq` was allocated under — so a guard on the second looks like a guard on the first.

**Changes.**

1. **Split the property.** In Appendix A:
   - `pat:epoch` — domain restricted to the dataset node. "The dataset generation. Allocated by an external authority (§24.4). The only epoch a write may guard on."
   - **new** `pat:seqEpoch` — version row. "The dataset epoch in which this row's current `pat:seq` was allocated. Informational and diagnostic. **Never a guard target.**" Add `sh:minCount 1; sh:maxCount 1; sh:datatype xsd:long` to `pat:VersionRowShape` and remove `pat:epoch` from that shape.
   - Receipts keep `pat:epoch` (the epoch the write was made under); add to `pat:RevisionShape` a note that its value must equal the dataset epoch at commit.

2. **Add a dataset-epoch guard to every write** — CAS (§19.1), append (§10.1), create (§19.3), delete (§24.1), key claim (§6.2, §7.1, §7.2), P3 (§7.1), pre-creation of version rows:

```sparql
WHERE {
  GRAPH <urn:g:dataset> { <urn:ds:prod> pat:epoch "4"^^xsd:long }   # client's expected epoch; O(1) read
  GRAPH <urn:g:meta/17> {
    <urn:g:orders/1> pat:seq "41"^^xsd:long ; pat:seqEpoch ?rowEpoch .
    OPTIONAL { <urn:g:orders/1> pat:head ?prevRev }                  # B5
    FILTER NOT EXISTS { <urn:g:orders/1> pat:deleted true }
  }
  ...
}
```

   State the invariants explicitly in a new §19.1.1 *Epoch invariants*:
   - `pat:seq` is monotonic **forever per stream key, across epochs** (this is F10 generalised);
   - a new epoch does not reset or rewrite any `pat:seq`;
   - the revision IRI uses the **dataset** epoch, so a post-restore write with a rewound `seq` cannot collide with a pre-restore IRI;
   - the ETag is `{datasetEpoch}-{seq}`, so every ETag issued before the bump fails the dataset guard. This is the intended fail-safe.

   This replaces the reviewer's "rewrite every version row" step: it is O(1) per write, needs no bulk maintenance transaction, and cannot be partially applied.

3. **External epoch allocation.** Rewrite §24.4 to name catalogue §10.3 strategies explicitly and adopt two of them:
   - **External high-water mark** — the new epoch is allocated from a coordination store outside the restored dataset, strictly greater than any epoch ever issued for that dataset. Restoring the same backup twice therefore cannot reuse an epoch (the second hazard in B1).
   - **Writer-start refusal** — a writer refuses to start, and fails in-flight writes, unless its cached dataset epoch equals the coordinator's current epoch. Cached epochs are revalidated on conflict, on a declared TTL, and on `EpochChanged`.
   - Add an explicit prohibition: **"Store-local epoch only" must not be selected** (catalogue §10.3 already classifies it unsafe; the current runbook implements exactly it).
   - Add a new capability/requirement `epoch_source: external_high_water_mark` to the family declaration and a planner refusal when no coordinator is bound (WP‑17).

4. **Fixed-width epoch (A‑2).** In the reference profile: epoch is 10 decimal digits, zero-padded, so `e0000000003 < e0000000010`. Update every example IRI. Alternatively, if unpadded epochs are retained, the guide must state that cross-epoch lexical range scans are unsupported and every prefix scan is epoch-pinned — but the padded form is cheaper than the caveat.

5. **Restore must replay erasures (A‑3).** Add step 0 to §24.4 and a new subsection §24.6 *Erasure register*:
   - every ADR‑A68 erasure appends an entry to an **erasure register held outside the dataset** (the same coordination store as the epoch high-water mark), recording the pseudonymous subject reference, the dropped graph locators, the legal basis reference, and the epoch at erasure;
   - restore tooling **must replay the register — dropping the listed graphs and re-asserting tombstones — before writers or readers are admitted**;
   - the register itself must contain no personal data (ADR‑A68 rule 3);
   - backups taken before an erasure remain a copy; the runbook must state the backup expiry window that bounds it, and that window must be part of the erasure response the DPO review assesses.

**Evidence:** TCK T‑5 rewritten to bump the dataset epoch only, then replay a structurally valid stale ETag (must be rejected); new T‑14 "restore the same backup twice, assert no epoch reuse"; new T‑15 "erase, restore, assert the erased graph is absent and the tombstone present".

*Where:* guide §2.3, §10.1, §10.2, §14.1, §19.1 (+ new §19.1.1), §19.3, §19.5, §24.1, §24.4 (+ new §24.6), §25.7, Appendix A, Appendix B, Appendix C ("Epoch"), Chapter 27; catalogue §10.3 (WP‑15); ADR‑A68 consequences (WP‑13).

---

### WP‑2 — Occurrence identity and corruption detection (B2, B3, A‑12)

**Decision on B2:** keep deterministic revision IRIs. They are required for the client-side ground template (F8), for lexical range scans, and for the O(1) `pat:head` lookup. The defect is not the determinism; it is that **every detection mechanism in the guide was built on the assumption that a fork produces two subjects.** Under a deterministic scheme the collision merges into one subject, and set semantics destroy the evidence exactly as in §1.1. Record that reasoning in a new §15.5 *Why fork detection moved*.

**Changes.**

1. **Replace the primary corruption signal.** Detection now rests on three things, in this order:
   - **Commit-time (SHACL Core):** `pat:RevisionShape`'s `pat:txn sh:maxCount 1` is the effective constraint — a merged receipt carries two `pat:txn` literals. Add the same reasoning for `pat:hlc`, `pat:recordedAt`, `pat:actor`. Promote this from an incidental property constraint to a documented invariant with an `sh:message` naming it as a lost-update signal.
   - **Standing audit (portable):**
     ```sparql
     SELECT ?rev (COUNT(DISTINCT ?t) AS ?n)
     WHERE { GRAPH ?txn { ?t pat:rev ?rev } }      # ?txn from the shard registry, not a prefix scan
     GROUP BY ?rev HAVING (COUNT(DISTINCT ?t) > 1)
     ```
     Must return zero rows. Ship as a metric and alert.
   - **Strengthened confirmation (§19.2, §15.2, F1):**
     ```sparql
     ASK { GRAPH <urn:g:txlog/…> {
             <urn:rev:…> pat:txn "01J8Q5B2…"
             FILTER NOT EXISTS { <urn:rev:…> pat:txn ?o FILTER(?o != "01J8Q5B2…") } } }
     ```
     A racing winner now learns the write is corrupt instead of being told `APPLIED`.
2. **Retain `pat:NoForkShape` and the F5 query only for non-deterministic revision schemes**, and say so. Delete the `…0042-b` example fork from F5: `rev_iri()` can never produce it, and leaving it implies a detection path that does not exist.
3. **Rewrite TCK T‑1's assertions.** "Exactly one receipt" and "fork query returns zero rows" currently pass while the system is corrupt. Replace with: exactly one txn claim for the winning revision; exactly one `pat:txn` on that revision; exactly one payload state; the losing client received `CONFLICT`, not `APPLIED`.
4. **One target IRI per stream (B3).** Add a new §10.4 *Target identity*:
   - each stream/aggregate has exactly one **target IRI**, which is the version-row subject, the `pat:target` value, the stream key for delta graph names, and the input to the revision namespace;
   - if that IRI is also the payload graph locator, this is a **declared punning** under catalogue §2 and must appear in the topology profile; it is not automatic;
   - the revision namespace token is derived **injectively and at fixed width** from the target IRI — either a registry-allocated token (catalogue §12.4) or `base32(sha256(targetIri))` truncated to the profile width — **never** by stripping a `urn:g:` prefix;
   - reconcile every example: §2.3, §10.1–10.2, §19.1, §20.2–20.3 and S6 currently mix `urn:stream:orders/1` and `urn:g:orders/1` as `pat:target`.
5. **Chapter 22** must state that the append and CAS forms share a mechanism **only because they share one version row and one target IRI**; otherwise they are two counters in one namespace (F2 reintroduced).
6. **A‑12:** remove `pat:opSeq` from the §19.1 receipt, or define `pat:opSeq 0` on a revision as "no event grain" and add it to `pat:RevisionShape` with that meaning. Align `Position`'s `opSeq` default with the choice and with S2's `COALESCE(?op, 0)`.

*Where:* guide §2.3, §10.1–10.2, new §10.4, §15.2, §15.3, new §15.5, §19.1–19.2, §19.4, §20.2–20.3, F2, F5, Chapter 22, Chapter 27 (T‑1, new T‑16 "deterministic-IRI collision under forced weak isolation is detected"), Appendix A (`pat:opSeq`), Appendix B; reference profile (target token).

---

### WP‑3 — Datatype and arithmetic portability (B4)

**The reviewer's finding is correct and the reviewer's fix is not portable.** SPARQL 1.1 §17.5's constructor-function table covers `xsd:integer`, `xsd:decimal`, `xsd:float`, `xsd:double`, `xsd:string`, `xsd:boolean`, `xsd:dateTime`. `xsd:long(...)` is a vendor extension. Using it would make the guide's own portability claim false on a conforming engine.

**Changes.**

1. **Prefer eliminating server-side arithmetic.** State the rule in F8 and §10.1: server arithmetic is used **only** in the append form, where the client genuinely does not know `?n`.
2. **Where it is unavoidable**, use the portable re-typing:
   ```sparql
   BIND(STRDT(STR(?n + 1), xsd:long) AS ?n1)
   ```
   Apply in §10.1 (`?n1`), §7.1 (P3 `?n1`), and anywhere else a counter is incremented. Add a note that the input must be in `xsd:long` range, enforced by `pat:VersionRowShape`'s bounds, and that `xsd:long(...)` is non-portable.
3. **Add the hazard to Chapter 13.** The existing "Mixed `xsd:integer`/`xsd:long`/`xsd:decimal`" row describes the failure without noting that the guide's own queries cause it. Add: "`?n + 1` on an `xsd:long` returns `xsd:integer` per XPath F&O numeric promotion; pinning the operand does not pin the result."
4. **Pin `pat:counter`** (P3 sentinel) to `xsd:long` in a new shape, and apply the same `STRDT` treatment.

**Evidence:** new TCK test O‑13 *datatype round-trip*: increment a counter, read it back, assert the term matches `"n"^^xsd:long`, and assert `VersionRowShape` validates. Add a QP4 determinism case.

*Where:* guide §7.1, §10.1, Chapter 13, F8, Appendix A (`pat:counter`), Appendix B (new `pat:KeyShardShape`), Chapter 27.

---

### WP‑4 — Write-path completeness (B5, B6, A‑10)

**Changes.**

1. **Optional head (B5).** In §19.1, move `pat:head ?prevRev` into an `OPTIONAL` inside the meta `GRAPH` block (see the WP‑1 snippet). Unbound `?prevRev` drops from both templates per SPARQL 1.1 Update template instantiation. Add a sentence: this is safe only because `pat:head sh:maxCount 1` is enforced or audited (F7); a two-valued head would match twice and double-instantiate.
2. **Define the first-write policy (B5, widened).** Add to §14.2 and §19.3, and to the family declaration:
   `first_write: pre_created_row | absent_row`.
   - `pre_created_row` — a row with `pat:seq "0"`, `pat:seqEpoch`, no head is created when the aggregate id is allocated (itself an idempotent, epoch-guarded write). The CAS shape is then the only shape ever used; `Expectation.Absent` is **not available** and `§19.3`'s create path is dead code for that family.
   - `absent_row` — `Expectation.Absent` and the §19.3 shape apply, with P2's write-skew caveat.
   Amend §25.1's `Expectation` doc comment accordingly. Today the two recommendations coexist and contradict each other.
3. **Append form maintains head and chain (B6).** In §10.1: read `OPTIONAL { ?stream pat:head ?prev }`, delete it, insert the new head, and emit `pat:prevRev ?prev` on the receipt. State that a stream written by both forms must share one version row (WP‑2) or T‑4 cannot pass.
4. **Define recreate/undelete (A‑10).** Add §24.1.1 *Recreate*: a distinct operation whose guard requires `pat:deleted true` and whose templates remove the tombstone, advance `pat:seq`, set a new head, and write a receipt typed `pat:Revision` (not `pat:Deletion`). The ordinary CAS guard (`FILTER NOT EXISTS { pat:deleted true }`) intentionally excludes it, and the create path cannot match an existing row.
5. **Forbid `pat:deleted false`.** Add `sh:hasValue true` alongside `sh:maxCount 1` on `pat:deleted` in `pat:VersionRowShape`; presence-and-true is the intended encoding, and a `false` triple would pass every `FILTER NOT EXISTS` guard in the guide.
6. **Bulk path completeness (A‑24 in §0.2 terms).** §24.3 assigns positions offline but writes no txn claims, no heads and no `prevRev`. Add: the offline assignment emits a chain-consistent receipt set and the final head per stream; step 3's gate adds the T‑4 chain-integrity check and a head-correctness check.

*Where:* guide §10.1, §14.2, §19.1, new §19.1.1, §19.3, §24.1 (+ new §24.1.1), §24.3, §25.1, Appendix B, Chapter 27 (new T‑17 "first CAS on a pre-created row", T‑4 extended to mixed append/CAS streams).

---

### WP‑5 — HTTP conditional semantics (B7)

**Changes.**

1. Replace every weak tag with a **strong** tag: `ETag: "3-41"`, `If-Match: "3-41"`. RFC 9110 §13.1.1 requires strong comparison for `If-Match`; a weak validator never matches, so the current mapping returns `412` unconditionally on a conforming server or intermediary.
2. Add a representation dimension, because a strong validator is per-representation: either serve exactly one serialisation for conditional requests, or include a representation token in the tag (`"3-41.ttl"`) and emit `Vary: Accept`. State the choice in the family declaration (`http.etag_form`).
3. Fix the Python `Version.etag` / `Version.parse_etag` in §19.4 and the §19.5 mapping table. Keep `If-None-Match: *` for create (correct as written) and `428` for unconditional writes (RFC 6585, correct).
4. Note that `W/` remains acceptable for `If-None-Match` caching, and that only the CAS path requires strong tags. This is the one place the distinction matters.

**Evidence:** new TCK test T‑18 *conditional round-trip through a conforming intermediary*: `GET` → `PUT` with the returned tag → must be `204`, not `412`.

*Where:* guide §15.4, §19.2, §19.4, §19.5, §29.3/WP‑17 declaration, Appendix C ("ETag").

---

### WP‑6 — Outcome resolution (B8, A‑15)

**Changes.**

1. **Separate the two paths** in §19.4 and §25.5. The defect is that `resolve()` is called identically after a definite response and after a timeout, and `ASK == false` is mapped to `CONFLICT` in both.
   - **Definite response** (HTTP status received, request completed): `ASK` false ⇒ `CONFLICT`. Sound, because the update finished.
   - **Timeout / lost connection**: `ASK` false ⇒ **`UNKNOWN`**. The request may still be executing. Never `CONFLICT`.
2. **Define the `UNKNOWN` protocol.**
   - Re-submit the **identical** request with the **same** txn id — this is safe precisely because the in-update `FILTER NOT EXISTS` on the txn claim makes it idempotent — with bounded retries and jitter; or
   - poll `resolve()` until it returns a definite answer or a declared deadline expires, then surface `UNKNOWN` to the caller.

Delete the `except TimeoutError: return resolve(...)` branch in §19.4 as written — it is the code that produces the defect.

3. **Make `UNKNOWN` reachable.** `Outcome.UNKNOWN` is defined and never returned, which contradicts `CasResult.Unknown` in §25.1 and retry rule 3 in §25.5. Add the return path and state the caller's obligation: an `UNKNOWN` may not be converted to a retry, a `412`, or a `500` without first calling `resolve()`.
4. **Append-form specific warning.** Add to §10.1 and Chapter 22: a timeout on the append form must **never** be retried under a new txn id. The txn claim is the only thing preventing duplicate events, and a new id defeats it. This is the failure mode the current client code produces.
5. **Resolve `Version` opacity (A‑15).** §25.1 declares `Version` opaque with "never do arithmetic on it"; §19.4's client is arithmetic over `(epoch, seq)`. Fix by layering explicitly:
   - the **port** exposes opaque `Version` tokens and `Expectation`;
   - the **strong-profile strategy** owns the `(datasetEpoch, seq)` structure, the ETag form, the revision-IRI formatter and the increment;
   - application code never parses a `Version`.
   Move the §19.4 client code into a documented "strategy-internal" subsection and say so, or make `Version` a sealed hierarchy with a `VersionedPosition` variant the strategy may destructure. Either is acceptable; the current silent contradiction is not.

**Evidence:** TCK T‑2 extended — inject a timeout *while the update is still executing* (not after it commits) and assert the client reports `UNKNOWN`, not `CONFLICT`; then assert that resubmission under the same txn id yields exactly one receipt and one event set. New T‑20: append form under injected timeout, assert no duplicate events.

*Where:* guide §10.1, §15.2, §19.2, §19.4, §22, §25.1, §25.5, §25.7, Chapter 27 (T‑2, new T‑20).

---

### WP‑7 — Retention, pruning and chain integrity (B9, plus one further defect)

**Changes.**

1. **Pin stream heads (B9).** Retention must never prune a receipt that is the current `pat:head` of any live stream, nor any receipt reachable from a still-valid reader grace window (catalogue §10.4 already requires exactly this for pointers; §24.2 ignores it). Implement as: the retention job resolves every `pat:head` before selecting buckets, and copies or retains pinned receipts rather than dropping a bucket wholesale.
2. **Then relax the shape.** Even with pinning, a mid-chain predecessor may legitimately be gone. Change `pat:RevisionShape`'s `pat:prevRev` from `sh:class pat:Revision` to `sh:nodeKind sh:IRI`, and add `pat:prevRevPruned` (boolean) or require the chain-integrity audit to consult `pat:retentionLowWaterMark` before reporting a break. Keep `sh:class` only where a family declares `retention.log: forever`.
3. **Resolve §24.2's internal contradiction.** The table says receipts are dropped by bucket and simultaneously that `pat:head` never points at a pruned graph. These cannot both hold without step 1. Rewrite the row and cross-reference §24.1.
4. **Maintain `pat:retentionLowWaterMark` where S3 expects it.** S3's corrected gap scan reads it from `urn:g:retention`; nothing in the guide writes it. Add the write to the retention job, define the property in Appendix A (see WP‑14), and add a shape.

**A‑16 (further defect, surfaced while specifying this package — extends §0.2; severity: blocking for patch-log families).**
Pruning a patch-log bucket does not make as-of reads *unavailable*; it makes them **silently wrong**. S6 reconstructs state by taking assertions at or before a position and excluding those a later revision retracted. If the bucket holding the *retraction* is pruned while the bucket holding the *assertion* survives, S6 returns a triple that was deleted. The result is a plausible state that never existed, with no error.

**Fix:**
- Every family declares an **as-of floor**: the earliest position for which as-of reconstruction is supported. The floor is advanced by the retention job **before** any delta graph is dropped, and every as-of query is rejected below it (`AsOfFloorExceeded`), not answered approximately.
- Retention over a patch log must prune **only a contiguous prefix** and must advance the floor past it atomically with the drop. Random or per-bucket pruning of a patch log is prohibited.
- Alternatively, compact: materialise a snapshot at the new floor, then prune below it. Document compaction as the supported way to shorten a patch log.
- Add `temporal.as_of_floor_source` to the family declaration and a planner refusal when `as_of_strategy: log_replay` is combined with non-prefix retention.

**Evidence:** new TCK O‑14 *prune-then-as-of*: assert/retract, prune the retraction's bucket, assert the as-of read is **refused**, not answered. New O‑15: retention run with a quiet aggregate older than the window; assert the next write to it succeeds under commit-time SHACL.

*Where:* guide §20.2, §20.4, §24.2, §24.3, S3, S6, §29.3 declaration, §29.4 table, Appendix A, Appendix B, Chapter 27; catalogue §5.8 and §10.4 (WP‑15).

---

### WP‑8 — Leases and fencing tokens (B10)

**Changes.**

1. **Advance the token.** In §7.4 and §16.2, every fenced write must both compare and rewrite the token in the same operation:
   ```sparql
   DELETE { GRAPH <urn:g:meta/17> { <urn:g:orders/1> pat:fence ?f } }
   INSERT { GRAPH <urn:g:meta/17> { <urn:g:orders/1> pat:fence "7184"^^xsd:long } }
   WHERE  { GRAPH <urn:g:meta/17> { <urn:g:orders/1> pat:fence ?f }
            FILTER(?f <= 7184) ... }
   ```
   `<=` admits the legitimate holder's second write (the current strict `<` rejects it); the rewrite is what actually fences a lapsed holder. The present form does neither.
2. **Bootstrap the token eagerly** with `pat:fence "0"`, for the same reason P3 counters and version rows are pre-created: a lazy `OPTIONAL` reintroduces the race on first use.
3. **Bind the token to the lease authority.** State that tokens must be monotonic across lease-service restarts (the same durability problem as the epoch, WP‑1), and name the mechanism. A token allocated from volatile state is not a fence.
4. **Fix §16.3's editorial lease.** It has no fencing token at all; §23.5 permits the expiry comparison *only if* a token is present. Add `pat:fence` to the lease example, and make the client-injected comparison value explicit rather than `NOW()`.
5. **`pat:fence` typing.** Pin to `xsd:long` (already in `VersionRowShape`), and apply WP‑3's `STRDT` rule if the token is ever incremented in SPARQL.

**Evidence:** new TCK T‑21 *stale lease*: acquire, pause past expiry, let a second writer acquire and write, then let the first writer attempt its write; assert it fails the guard.

*Where:* guide §7.4, §16.2, §16.3, §23.5, §25.4 (`ExternalLockStrategy`, `SerializingProxy`), Appendix A (`pat:fence`), Chapter 27.

---

### WP‑9 — Global order, watermarks and the HLC (B11, A‑11)

**Changes.**

1. **Forbid the naive global HLC page.** §21.3's `FILTER(?hlc > last) ORDER BY ?hlc LIMIT 500` is a pre-commit position read, which is precisely the G2 hole Part III closed for the dense tier. Because the HLC is stamped client-side before commit, a receipt with a lower HLC can commit after a higher one has been read, and the consumer's watermark has already advanced past it. Per-target contiguity (S3) detects this only *after* the loss.
2. **Require one of three safe global-read patterns**, declared per family:
   - **Watermarked sparse read** — read only below a stable watermark, computed as `min(active writers' in-flight HLC) − safety margin` and published as structured triples (see A‑14 fix in WP‑14). This requires writer registration and heartbeats; state that dependency honestly rather than implying the watermark is free.
   - **Lag-window read** — read only below `observed_max_hlc − lagWindow`, where `lagWindow ≥ max clock skew + max commit duration + max client stamp-to-commit delay`, all declared and monitored, with a **late-arrival alarm**: any receipt whose HLC is below the consumer's last committed watermark is a declared incident, not a silent skip.
   - **Dense feed** — use `NativeFeed` where `changeFeedDense` is true (Neptune Streams, rdf-delta) and treat the feed position as the dataset tier. Preferred where available.
3. **Make the per-target contiguity check blocking, not advisory.** §21.3 currently says the consumer "then asserts" contiguity. Specify the action: on a contiguity failure, the consumer must rescan from the affected stream's last known-good position before advancing the global watermark. A failed contiguity check that only raises a metric is a data-loss path.
4. **Clamp the HLC (A‑11).** `Hlc.send()` increments `c` without bound; past 9999 the `{logical:04}` format overflows, breaking both `pat:hlc`'s `sh:pattern` and lexical ordering. `receive()` is likewise unclamped. Fix: on `c > 9999`, advance `l` by 1 and reset `c` to 0 (borrowing from the physical component), or widen the field in the profile and the shape. Add the same clamp to `receive()`. Add a unit test that drives 10⁵ same-millisecond stamps and asserts monotone lexical order and shape validity.
5. **Node-id grammar.** `pat:hlc`'s pattern admits `[A-Za-z0-9-]+` of any length, so two node ids of different lengths sort by prefix and can interleave incorrectly at equal `(l, c)`. Fix the node-id width in the reference profile, or state that equal-`(l,c)` ordering across nodes is arbitrary-but-stable and never load-bearing.

**Evidence:** new TCK O‑16 *HLC reorder probe* — the ordering analogue of O‑2, run against the global reader: inject delay between HLC stamp and commit and assert the consumer never permanently skips a receipt. O‑17 *counter overflow*.

*Where:* guide S7, §21.2, §21.3, §25.7, §29.3, §29.4, Appendix A (`pat:hlc`, `pat:stableWatermark`), Appendix B (`RevisionShape`), Chapter 27.

---

### WP‑10 — Contention topology beyond the meta graph (B12)

**Changes.**

1. **Shard or bucket every hot graph, not just meta.** F12 and T‑3 shard the version rows; every write in the dataset still inserts into single `urn:g:txn` and `urn:g:txlog/{month}` graphs, and every P3 claim into `urn:g:keys`. On an engine whose conflict detection is graph- or page-granular, A6 is lost regardless of meta sharding. Add to §17.3 and §25.2:
   - `urn:g:txn/{hash(txnId) mod N}`
   - `urn:g:txlog/{month}/{hash(target) mod N}` — shard *within* the time bucket so that both bucket rotation (retention) and shard isolation (contention) are preserved
   - `urn:g:keys/{hash(claimIri) mod N}`
   - the P3 sentinel nodes distributed across key shards
2. **Make the shard dimensions part of the topology profile** (catalogue §5.8, §12.1), not hard-coded strings. Every query that enumerates them must resolve them from the bucket/shard registry introduced in WP‑12, not from a prefix scan.
3. **Extend T‑3** to measure conflict rate on the txn, log and keys graphs independently, and record each in the capability report. `statementLevelConflictDetection` is currently populated from the meta graph only, which under-reports.
4. **Two consequences to state explicitly:**
   - **Access control (catalogue §5.9, §13.3).** The keys graph is restricted. Sharding multiplies the number of graphs that must carry the restricted ACL, and a missed shard is a silent PII disclosure. Require that the ACL be expressed over the shard *template*, that the profile declare the shard count, and that a conformance check assert every shard graph is covered.
   - **Graph-name visibility.** Graph names are frequently listable even where contents are not; catalogue §13.3 already warns that a graph name is not a security boundary. Shard membership therefore leaks bucket-level count metadata. This is low severity because shard membership derives from the keyed claim IRI, but it must be an accepted, recorded consequence rather than an unexamined one.
5. **Graph-count budget.** Sharding the txn, log and keys graphs multiplies graph count against the G6 proliferation limit and TCK O‑12. Add the combined graph-count budget to §29.3 and require O‑12 to run against the *full* topology, not the payload graphs alone.

*Where:* guide §2.3, §6.1, §7.1, §17.3, §19.1, §24.2, §25.2, §29.3, §29.4, Chapter 27 (T‑3, O‑12), Appendix A (`pat:counter`); catalogue §5.8, §5.9, §12.1 (WP‑15).

---

### WP‑11 — Multi-target writes and lock ordering (B13)

**Changes.**

1. **Withdraw the claim as stated.** §10.1 and §19.6 instruct the writer to "acquire version rows in sorted IRI order" by listing them in that order in `WHERE`. SPARQL specifies no evaluation order and no lock order; the optimiser may reorder freely. Replace with a scoped statement:
   - **Single-request updates:** deadlock avoidance is the engine's responsibility. The adapter must treat deadlock/abort as `Conflict`, retry with jitter, and expose a deadlock-rate metric. Sorted ordering in the query text is a readability convention with no guarantee, and must be labelled as such.
   - **Multi-request transaction strategies** (`ExplicitTransaction`, `NativePromote`, vendor APIs) and **external lock strategies**: sorted acquisition *is* effective, because the client controls statement order. Retain the rule there and say so.
   - **Partitioned writers:** the partition key must cover all targets of a multi-target write, or the write must be a saga. Cross-partition multi-target writes are not orderable by convention.
2. **Bound the exposure.** `beginUnitOfWork()` remains gated on `multiAggregateAtomicity` (§25.6, correct as written). Add that a family declaring `multi_aggregate: unit_of_work` must also declare a deadlock policy, and that the planner refuses `unit_of_work` when the capability report shows deadlock aborts but the family declares no retry budget.
3. **Cross-target epoch consistency.** A multi-target write must read the dataset epoch once and guard all targets against that one value (WP‑1), so that an epoch bump mid-write cannot half-apply.

**Evidence:** new TCK T‑19 *opposite-order two-stream write*: two clients write targets A,B and B,A concurrently; assert forward progress and that aborts are reported as `Conflict`, not `Unknown` or success.

*Where:* guide §10.1, §19.6, §25.4 (`ExplicitTransaction`, `SerializingProxy`), §25.6, §29.3, Chapter 27.

---

### WP‑12 — Query hygiene and detection correctness (A‑7, A‑8, A‑9)

The guide's *detection* queries — the ones it relies on to prove the whole design safe — break the guide's own rules. Every one is in the "standing alert" set.

**Changes.**

1. **Introduce a bucket/shard registry and stop prefix-scanning (A‑7).** Add a small `urn:g:catalog` graph listing every log bucket, txn shard, keys shard and delta bucket with its role, target-shard range and `(epoch, seq)` coverage. Then rewrite to enumerate from the registry via `VALUES`:
   - **S3 gap scan** — currently `GRAPH ?log { … } FILTER(STRSTARTS(STR(?log), "urn:g:txlog/"))`. This is forbidden by F6 (unbound `GRAPH ?log` scans every graph in the dataset) and by catalogue §12.3 (prefix scans are diagnostics, not integrity mechanisms). It is also unsound: it scans *nothing* if a bucket is renamed and *everything* if another graph shares the prefix.
   - **F5 fork query** — same defect.
   - **The txn-cardinality query** introduced in WP‑2 — must be registry-driven from the outset.
   - **S6 as-of** — `GRAPH ?log` / `GRAPH ?log2` unbound; must be bounded to registry buckets within the as-of range.
2. **Fix S4 (A‑7, second half).** S4 hard-codes `urn:g:txlog/2026-09`, so it returns the wrong "latest revision" for any stream last written in an earlier bucket — silently, with a plausible answer. Changes:
   - the normative head lookup is `pat:head` on the version row (single triple, already benefit A4);
   - the `MAX(?seq)` form is demoted to a **repair/audit** query, registry-driven, with the `pat:epoch` pinned and all buckets enumerated;
   - add a head-consistency audit: `pat:head` must equal the max-`seq` receipt per target per epoch.
3. **Fix the duplicate scans (A‑8).** §7.5's P7 reconciler and §7.3's `ex:PersonEmailUnique` group on the **raw** literal, so neither can detect the normalization-variant duplicate that §4's own K4 example uses (`ada@example.org` vs `Ada@Example.org`). §8.1 already states SPARQL cannot normalize; the two sections contradict each other.
   - Replace the primary reconciler with an **application-side** job that reads the payload, applies the frozen pipeline, recomputes the claim IRI, and groups on that. This is the only form that matches the write path.
   - Keep the SPARQL exact-match query as a cheap first pass, labelled as such — it catches byte-identical duplicates only.
   - Replace `ex:PersonEmailUnique` (`sh:sparql`, full-scan, raw-literal) with the claim-based `sh:maxCount 1` check the guide already argues for in §6.1, plus an audit rule that every `ex:Person` with an `ex:email` has a corresponding owned claim. Cross-node `sh:sparql` uniqueness on a raw literal is the worst of both worlds: expensive *and* incorrect.
   - Add the same treatment to the `order-number-per-tenant` example in §29.3.
4. **Fix S5 (A‑9).** S5 orders on `?op` from an `OPTIONAL`-adjacent pattern without `COALESCE`, which is the exact failure Chapter 13 forbids and S2 already guards. Change to `ORDER BY ?occurred ?epoch ?seq ?opk` with `BIND(COALESCE(?op, 0) AS ?opk)`. Reconcile with the A‑12 decision on receipt-level `pat:opSeq`.
5. **Add a review-checklist item and a lint rule.** Chapter 28's checklist already requires named graphs; add: "no `STRSTARTS` over graph names in any integrity, ordering or as-of query; enumerate from the registry." Enforce in the lint suite (WP‑18).
6. **Re-verify every remaining query in the guide** against the Chapter 28 checklist as a closing task, and record the audit in a table. The four defects above were found by applying the guide's own rules to the guide; the remaining queries have not been audited that way.

*Where:* guide §6.1, §7.3, §7.5, S3, S4, S5, S6, F5, F6, §21.3, §24.2, §29.3, Chapter 28 (checklist), Appendix B (`ex:PersonEmailUnique` replacement), new §2.3 registry row; catalogue §12.3, §12.4 (WP‑15).

---

### WP‑13 — Privacy, erasure and the history models (A‑3, A‑4, A‑5, A‑6)

This is the largest unclosed area and the one the review did not reach. ADR‑A68 decides *how* erasure works; the patterns guide decides *what history is kept*; **no document reconciles them**, and the combinations the guide recommends most strongly are the ones that make erasure impossible.

**Changes.**

1. **Erasure register and restore replay (A‑3).** Specified in WP‑1 step 5. Add the corresponding consequence to ADR‑A68: "Erasure is durable only if it survives restore. A deployment must maintain an erasure register outside the dataset and replay it before admitting readers or writers after any restore, rebuild, or environment clone."
2. **Receipt-model / privacy-class compatibility (A‑4).** State the matrix and make it a planner refusal:

   | Receipt model | Family contains personal data | Verdict |
   |---|---|---|
   | `receipt_only` | yes | **Permitted.** Receipts carry pseudonymous references only (ADR‑A68 rule 3). Erasure = drop the per-subject payload graph + tombstone. |
   | `patch_log` | yes | **Refused** unless (a) delta graphs are per-subject and enumerable from the erasure register, **or** (b) delta payloads are crypto-shredded per subject. Otherwise the delta graphs are a second immutable copy of the personal data and the graph-drop mechanism cannot reach them. |
   | `snapshot_per_revision` | yes | **Refused** unless snapshots are per-subject and enumerable, or crypto-shredded. Same reasoning. |
   | any | no | Permitted. |

   Note the sharp edge this creates: §20.4 and §30.1 currently require decision records to be `patch_log` or `snapshot_per_revision` ("never receipt-only"), and MORK decision records plausibly reference data subjects. The resolution is that a decision record may reference a subject **only pseudonymously**; any personal payload must live in the per-subject graph the decision *points at*, never inside the decision or its deltas. Add this as an explicit rule in §20.4 and §30.1, and as a shape in `ontology/governance/shapes/` per ADR‑A68's existing consequence.

3. **Crypto-shredding, if selected, must be specified (catalogue §11.5 names it; nothing defines it).** Add a new §24.5 *Crypto-shredding* covering: per-subject key derivation and custody, what is encrypted (payload triples? object literals? whole graph serialisation?), how encrypted content interacts with RDFC‑1.0 canonicalisation and content-addressed revision IRIs (a re-encryption changes bytes and therefore changes content identity — this must be designed, not discovered), key-destruction durability across backups, and the resulting as-of behaviour (a shredded revision is *unreadable*, so as-of reads must fail cleanly, not return partial state). If the deployment cannot specify these, it must select per-subject graph drop instead.
4. **Claim-scheme rotation must preserve uniqueness (A‑5).** §6.1's docstring and catalogue §6.4 both describe rotation as "a new version salt and a backfill", which leaves a window where writer W1 (on `v1`) and writer W2 (on `v2`) each successfully claim the same normalized key. Specify a three-phase protocol:
   - **Phase A (dual-write):** every claim acquisition guards and inserts **both** the `v1` and `v2` claim IRIs in one operation; reads resolve either. Uniqueness holds because any two writers collide on at least one claim node.
   - **Phase B (backfill):** existing `v1`-only claims gain their `v2` counterpart, idempotently, under the same dual-write guard.
   - **Phase C (retire):** once no writer accepts `v1` (enforced by a scheme registry state machine, not by deployment order), `v1` claims are tombstoned or — under an erasure policy — deleted.
   Add `pat:claimScheme` to claim nodes, a scheme registry with states `accepting | dual | retiring | retired`, and a refusal if a writer's scheme state does not match the registry.
   **Evidence:** new TCK K‑9 *rotation under contention*: two writers on different scheme versions race for the same normalized key; assert exactly one owner.
5. **Declare the ownership-monotonicity exception (A‑6).** §6.2's post-`ASK` correctness argument rests on "a claim is only ever released by an explicit retire operation issued by its own owner". Catalogue §6.4 states erasure may physically delete a claim, which breaks that premise. Add to §6.2, §8.4 and Appendix C:
   - monotonicity holds **except** where an erasure policy permits physical claim deletion;
   - in such families, the post-`ASK` is valid only in the absence of a concurrent erasure of that claim, and erasure must be serialised against claim allocation for the same key (via the shard sentinel, the external allocator, or a declared lock);
   - the family declares `erasure_precedence` (catalogue §11.5 already demands it) naming which of erasure and monotonicity wins and how reconciliation behaves.
6. **Audit records must not reintroduce personal data.** §24.1's deletion receipt carries `pat:cause <urn:decision:gdpr-erasure/2026-09-21/7>`. Add a rule: a decision IRI, a receipt, a tombstone, a ledger entry and a graph *name* must contain no personal data or reversible derivative of a personal key (ADR‑A68 rules 3 and 5, catalogue §5.9). Add this to the PII data-model shape ADR‑A68 already requires at P0.3.8, and add an L1 fixture that fails a ledger containing personal data (already promised by ADR‑A68; not yet specified).
7. **Environment clones.** Catalogue §4.4 requires synthetic data to use a distinct tenant or namespace rather than an environment substitution. Add to §24.4: cloning production into a lower environment is a restore for erasure purposes and must replay the erasure register; a clone that has not replayed it is a personal-data breach surface, not a test fixture.

*Where:* guide §6.1, §6.2, §8.4, §20.4, §24.0, §24.1, §24.2, §24.4, new §24.5, §29.3, §30.1, Appendix C, Chapter 27 (K‑9, T‑15, new T‑22 "clone replays erasure register"), Appendix E items 5 and 7; ADR‑A68 (Decision and Consequences, see WP‑15); catalogue §6.4, §11.5, §13.7 (WP‑15).

---

### WP‑14 — Vocabulary, terminology and cross-document consistency (C1, C2, C3, A‑12, A‑13, A‑14)

**Changes.**

1. **Repoint every ADR‑A51 citation (C1).** Exact sites and targets:

   | Site | Current | Repoint to |
   |---|---|---|
   | Status line | "identity-related corrections applied… ADR‑A51 review disposition" | Retain the historical reference; add "ADR‑A51 is superseded by ADR‑A82; identity grammar is now governed by the reference profile (WP‑0)." |
   | `claim_iri` docstring | "matches ADR‑A51's minimum content-hash width" | reference profile §digest schemes; catalogue §7.4 |
   | §7.5 | "`fnd:replacedBy` … (ADR‑A51)" | catalogue §11.3–11.4 plus the C2 resolution |
   | §8.4 item 1 | "what ADR‑A51 names `surrogate-claimed`" | catalogue §6.4 |
   | §19.4 ULID note | "ADR‑A51 rule 2" | catalogue §6.3 (Prohibition) and §6.4 |
   | Appendix D.1 | table of A51-review corrections | retain as history; add a row-by-row status column recording which corrections this plan finds **incomplete** (revision IRI epoch → B1/A‑2; claim width → A‑1; illustrative-value drift → WP‑0; S6 → A‑16; S3 → A‑7) |
   | Appendix E item 9 | "a later split remains open" | now closed by WP‑0; update |

   Also amend ADR‑A51's header: "Superseded by ADR‑A82" asserts a completed action while A82 is `Proposed`. Change to "To be superseded on ratification of ADR‑A82", or record both as proposals. Mirror in ADR‑A82's Consequences.

2. **Resolve `fnd:replacedBy` (C2).** It is prescribed by P7 and §30.2, absent from the guide's own Foundation-term list (§23.3), and catalogue §11.4 forbids writing a relation the selected ontology does not define. Do one of:
   - confirm the term exists in Foundation and add it to §23.3 with its domain, range, transitivity and revocability; or
   - replace it with a profile-declared `merge_relation` in the family declaration, defaulting to unset, with the planner refusing `on_violation: merge` when no relation is declared.
   In either case, keep the existing prohibition on `owl:sameAs` as the default merge mechanism (catalogue §11.3), and state that the relation must be revocable — a merge later found wrong must be retractable without reasoner side effects.

3. **Fix the valid-time naming (A‑13).** Three names for one role: `ex:occurredAt` (events), `pat:occurredAt` (receipts, §19.1 and Appendix A), `valid_time.property` (declaration). Decide and apply uniformly:
   - domain valid time is a **domain** property, declared per family (`valid_time.property`), illustrated as `ex:occurredAt`;
   - `pat:occurredAt` on a receipt is permitted **only** where the write itself has a valid time distinct from its events, and must be declared; otherwise remove it from §19.1;
   - `fnd:TemporalScope` remains the mechanism for interval-scoped domain facts (§23.3), not for point events.
   Update §3.2, §10.2, §19.1, §23.2, §23.3, §29.3, Appendix A, Appendix C.

4. **Complete the vocabulary (A‑14).** Appendix A must define every term any query or shape in the guide uses. Missing or wrong today:

   | Term | Action |
   |---|---|
   | `pat:retentionLowWaterMark` | Add (used in S3, written by the retention job per WP‑7). Range `xsd:long`, per target, per epoch. |
   | `pat:etag` | Add as **prohibited/deprecated** with the F4 rationale, since `VersionRowShape` constrains it with `sh:maxCount 0`. A shape may not reference an undefined term. |
   | `pat:stableWatermark` | Replace the `{epoch}:{seq}` delimited string with `pat:watermarkEpoch` + `pat:watermarkSeq` (both `xsd:long`). A delimited concatenation with no declared widths or parse rule violates catalogue §7.2 and §10.2 and cannot be compared numerically. |
   | `pat:seqEpoch` | Add (WP‑1). |
   | `pat:claimScheme` | Add (WP‑13). |
   | `pat:prevRevPruned` or equivalent | Add if selected in WP‑7. |
   | `pat:opSeq` | Resolve the A‑12 contradiction: it is defined as an ordinal of an event within a revision, `pat:EventOrderShape` targets event subjects, and §19.1 writes it on a receipt. Either scope it to events and remove it from §19.1, or define `pat:opSeq 0` on a revision as "no event grain" and add it to `RevisionShape`. Align `Position.opSeq` and S2's `COALESCE(?op, 0)`. |
   | `pat:counter` | Pin datatype and add a shape (WP‑3). |
   | Registry terms | Add the bucket/shard registry vocabulary from WP‑12. |

5. **Add the `sh:declare` requirement wherever `sh:prefixes` is used.** Appendix B states it for `pat:`; `ex:PersonEmailUnique` in §7.3 uses `sh:prefixes ex:` without it. Fix or remove with the WP‑12 replacement.

6. **Terminology.** Appendix C must gain `Target IRI`, `As-of floor`, `Erasure register`, `Claim scheme`, `Dataset epoch` vs `Row epoch`, and must correct `Epoch` and `ETag` per WP‑1 and WP‑5.

*Where:* as tabulated; plus ADR‑A51 header, ADR‑A82 Consequences, catalogue §11.4 cross-reference.

---

### WP‑15 — Amendments to the catalogue, ADR‑A82 and ADR‑A68

The catalogue was mostly right; its gap is that it stated rules without requiring anyone to *detect* violations. Six additions.

**`iri-identity-patterns.md`:**

| § | Addition |
|---|---|
| §10.3 (Epoch durability) | Add the requirement that **every write guards on the current dataset epoch**, and that a version-row or receipt epoch is not a substitute. Restate "store-local epoch only" as **prohibited**, not merely "unsafe by itself", for any position-derived occurrence identity. Add the double-restore reuse hazard. |
| §10.2 (Fixed-width positions) | Extend to **every** identity-bearing component of an occurrence IRI, naming the epoch explicitly. Add: a variable-width epoch makes cross-epoch lexical scans wrong even when the sequence is padded. |
| §5.10 / §10.6 (Event occurrences) | Add: where an occurrence IRI is derived deterministically from `(target, epoch, position)`, a broken isolation guarantee produces one *merged* subject rather than two, so **fork-style detection by subject count cannot fire**. A deterministic occurrence profile must declare a per-occurrence uniqueness witness (a transaction claim or equivalent) and a cardinality constraint on it. Also require the target→namespace derivation to be **injective and fixed-width**. |
| New §11.6 (Erasure and history models) | The compatibility matrix from WP‑13 item 2, plus the rule that an erasure mechanism must reach every derived copy — deltas, snapshots, projections, caches, exports, backups — and that an erasure register replayed on restore is the mechanism. |
| §15 (Refusal conditions) | New rows: deterministic occurrence IRI without a uniqueness witness; `patch_log`/`snapshot_per_revision` with personal data and no per-subject scoping or crypto-shred; claim scheme without a dual-write rotation protocol; position-derived event without an external epoch authority; conditional HTTP without a strong ETag and representation policy; patch-log retention that is not prefix-only when as-of is supported. |
| §14.1 / §14.3 | Candidate concepts: `dal:EpochAuthority`, `dal:OccurrenceNamespaceDerivation`, `dal:ClaimSchemeVersion`, `dal:PrivacyClass`, `dal:ErasureRegister`, `dal:AsOfFloorPolicy`. Validation requirements: cross-epoch lexical ordering test; numeric datatype round-trip test; erasure-replay-after-restore test; claim-rotation concurrency test. |

**`ADR-A82`:** add to Consequences — (a) the patterns guide and any other implementation document is a **consumer** of a selected profile and must not restate identifier grammar inline (closing the root cause in WP‑0); (b) the new reference URN profile is published under §6 as opt-in and versioned; (c) the refusal conditions added to catalogue §15 are compiler obligations, not prose.

**`ADR-A68`:** add to Decision/Consequences —
- (6) **Erasure register.** Erasure is recorded outside the dataset and replayed before any restored, rebuilt or cloned dataset admits traffic.
- (7) **History-model restriction.** A family containing personal data may not select a history model that duplicates personal payload into immutable derived graphs unless those graphs are per-subject and enumerable, or crypto-shredded.
- (8) **Claim rotation and erasure precedence.** Claim-scheme rotation follows the dual-write protocol; the family declares erasure precedence against ownership monotonicity.
- (9) **Backup window.** The residual exposure window is the backup retention period; it must be stated and accepted as part of the DPO review, which ADR‑A68 already requires before the Phase 0 exit gate.
- Note that ADR‑A68's existing exception to ADR‑A65/A67 (graph drop is not a superseding version) now also needs an exception for **derived** graphs, which contradicts ADR‑A68 rule 4's "write-back never writes to a derived graph" only in the erasure direction. State that erasure may *delete* from derived layers even though normal writes may not *write* there.

---

### WP‑16 — TCK and capability evidence

Consolidate every test named above into Chapter 27, and correct the "what a pass means" set in §27.4.

| Test | Status | Asserts |
|---|---|---|
| K‑1, K‑3 | unchanged | gating |
| **K‑9** | new | claim-scheme rotation under contention yields one owner |
| O‑2, O‑8 | unchanged | gating |
| **O‑13** | new | counter datatype round-trip is `xsd:long`; shape validates |
| **O‑14** | new | prune-then-as-of is **refused**, not answered |
| **O‑15** | new | write to an aggregate older than the log retention window succeeds under commit-time SHACL |
| **O‑16** | new, **gating** | global HLC reader never permanently skips a receipt (the sparse-tier analogue of O‑2) |
| **O‑17** | new | HLC logical-counter overflow preserves order and shape |
| T‑1 | rewritten | one txn claim per revision; one `pat:txn` per revision; loser sees `CONFLICT` |
| T‑2 | extended, gating | timeout *during* execution yields `UNKNOWN`, then exactly-once on resubmission |
| T‑3 | extended | conflict rate measured on meta **and** txn, log, keys graphs |
| T‑4 | extended | chain integrity across mixed append/CAS streams |
| T‑5 | rewritten, gating | stale ETag rejected on the **dataset** epoch guard |
| **T‑14** | new, gating | restoring the same backup twice does not reuse an epoch |
| **T‑15** | new, gating | erase → restore → erased graph absent, tombstone present |
| **T‑16** | new | deterministic-IRI collision under forced weak isolation is detected |
| **T‑17** | new | first CAS against a pre-created row succeeds |
| **T‑18** | new | conditional `PUT` round-trip through a conforming intermediary returns `204` |
| **T‑19** | new | opposite-order two-target writes make progress; aborts reported as `Conflict` |
| **T‑20** | new | append form under timeout produces no duplicate events |
| **T‑21** | new | lapsed lease holder's write fails the fence |
| **T‑22** | new | environment clone replays the erasure register |
| O‑12 | extended | graph-count budget measured over the full sharded topology |

**§27.4 correction.** The current pass set (K‑1, K‑3, O‑2, O‑8, T‑1, T‑2) cannot be trusted because T‑1 passes while the system is corrupt (B2) and T‑5 cannot fail (B1). New gating set: **K‑1, K‑3, O‑2, O‑8, O‑16, T‑1 (rewritten), T‑2 (extended), T‑5 (rewritten), T‑14, T‑15.** Add: capability flags are populated from a TCK report bound to an exact image, configuration and **isolation setting**; a report older than the current configuration hash is not evidence.

**Chapter 30.4 correction.** The existing sequencing note is still right in shape but incomplete: add that the TCK must run against at least one MVCC engine *and* one engine with coarse (graph- or page-granular) conflict detection before `statementLevelConflictDetection` means anything, and that the epoch coordinator must exist before T‑5, T‑14 or T‑15 can run at all.

---

### WP‑17 — Family declaration and planner refusals

Extend §29.3's declaration and §25.3's planner. Every remediation above that depends on a deployment choice must be declarable and refusable; a rule that lives only in prose is the failure mode this whole set already demonstrated.

**New or changed declaration keys:**

```yaml
identity:
  profile: reference-urn-profile-v1          # WP-0; required
  target_iri: "urn:g:{family}/{id}"          # WP-2; the version-row subject
  occurrence_namespace: hashed_target        # registry_token | hashed_target
epoch:
  authority: external_high_water_mark        # WP-1; store_local is refused
  coordinator: <binding>
  guard: dataset                             # WP-1; row is refused
privacy:
  class: personal_data | internal | public   # WP-13
  erasure: per_subject_graph_drop | crypto_shred | none
  erasure_precedence: erasure_wins | monotonicity_wins    # catalogue §11.5
  erasure_register: <binding>
first_write: pre_created_row | absent_row    # WP-4
http:
  etag_form: strong                          # WP-5
  etag_representation: single | tagged
receipts:
  model: receipt_only | patch_log | snapshot_per_revision
  retention_mode: prefix_only | bucket_any   # WP-7 (A-16)
temporal:
  as_of_floor_source: retention_job          # WP-7
order:
  global_read: watermark | lag_window | dense_feed | none   # WP-9
  lag_window: <duration>
topology:
  meta_shards: 64                            # WP-10
  txn_shards: 16
  log_shards: 16
  keys_shards: 1024
  registry_graph: urn:g:catalog              # WP-12
merge:
  relation: <declared or unset>              # WP-14 / C2
claims:
  scheme_version: v2
  scheme_state: dual                         # accepting | dual | retiring | retired
concurrency:
  deadlock_policy: engine_detect_and_retry | sorted_acquisition | partitioned
```

**New planner refusals (fail at startup, never silently downgrade):**

| Refuse when | Because |
|---|---|
| `epoch.authority: store_local` with position-derived occurrence identity | B1, catalogue §10.3 |
| No epoch coordinator bound | WP‑1 |
| `privacy.class: personal_data` with `receipts.model` ∈ {`patch_log`, `snapshot_per_revision`} and no per-subject scoping or crypto-shred | A‑4 |
| `privacy.erasure: crypto_shred` without key custody, as-of failure semantics and backup-destruction policy | WP‑13 §24.5 |
| `as_of_strategy: log_replay` with `retention_mode: bucket_any` | A‑16 |
| `claims.scheme_state` mismatch between writer and registry | A‑5 |
| `order.global_read: none` while the family advertises a dataset tier | B11 |
| `http.etag_form: weak` with conditional writes | B7 |
| `on_violation: merge` with `merge.relation` unset | C2 |
| Any `min_level` unsupported by a current, configuration-bound TCK report | existing rule, now with the corrected gating set |
| Identity profile absent, or a grammar restated in the family declaration | WP‑0, ADR‑A82 §5 |

---

### WP‑18 — Enforcement

Rules in prose decayed into the twenty-eight defects above. Each remediation gets a mechanical check.

| Check | Enforces |
|---|---|
| Documentation build fails if any IRI-shaped literal in the guide is absent from the fixture set | WP‑0, A‑1, A‑2, illustrative drift |
| Lint: no `STRSTARTS` on a graph name in any integrity/ordering/as-of query | A‑7 |
| Lint: no unbound `GRAPH ?g` in any guide example or shipped query | F6, A‑7 |
| Lint: any `?x + 1` written to a typed property must be wrapped in `STRDT(..., xsd:long)` | B4 |
| Lint: `W/"` may not appear in an `If-Match` code path | B7 |
| Lint: every write template must contain a dataset-epoch guard | B1 |
| Lint: every shape term must exist in Appendix A | A‑14 |
| Lint: `sh:prefixes X` requires a `sh:declare` on `X` | Appendix B, §7.3 |
| ArchUnit: no caller outside the strong-profile strategy destructures `Version` | A‑15 |
| ArchUnit: no `Collection<Row>` return from the SPI or callers | existing QP3 |
| CI gate: adapter not deployable without a TCK report bound to image + config + isolation hash | QP5, §27.4 |
| CI gate: planner refusal matrix has a test per row | WP‑17 |
| Fixture gate: golden vectors exist for every derived identifier in the profile | catalogue §14.3 |

---

## 3. Gates

No work downstream of a gate may proceed until the gate's evidence exists.

**Gate 0 — Immediate (documentation state).**
Mark `rdf-sparql-patterns-guide.md` **"Not implementable — under remediation"** at the head, listing B1–B13 and A‑1 to A‑16 with links to this plan. Today it is labelled "Authoritative architectural guide", and it is being read as such. Freeze any code generated from it. No production data is written under any circumstance before Gate 3.

**Gate 1 — Identity frozen.** *Required before any component mints an identifier.*
WP‑0, WP‑1 (items 1–4), WP‑2, WP‑3, WP‑5, WP‑14, WP‑15 (catalogue §10.2/§10.3/§5.10 items), WP‑18 (fixture and lint checks).
Evidence: published reference profile; golden vectors; every guide example drawn from fixtures; cross-epoch and cross-target ordering tests; datatype round-trip test; O‑13, T‑18.

**Gate 2 — Write path safe.** *Required before any multi-writer or non-development deployment.*
WP‑4, WP‑6, WP‑7, WP‑8, WP‑9, WP‑10, WP‑11, WP‑12, WP‑16, WP‑17.
Evidence: full gating TCK set green on (a) one single-writer engine, (b) one MVCC engine, (c) one engine with coarse conflict detection; epoch coordinator operating; registry-driven integrity queries running as alerts with zero rows; planner refusal matrix tested.

**Gate 3 — Production data admitted.** *ADR‑A68's own precondition, now specified.*
WP‑1 item 5, WP‑13, WP‑15 (ADR‑A68 amendments), T‑15, T‑22.
Evidence: erasure register operating and replayed in a rehearsed restore; PII data-model shape and L1 failing fixture in `ontology/governance/shapes/`; receipt-model/privacy-class refusal enforced; claim-rotation protocol tested (K‑9); erasure precedence declared; **DPO/legal review completed against this mechanism, including the backup exposure window** — ADR‑A68 already requires this review and explicitly does not substitute for it.

---

## 4. Sequencing

| Order | Packages | Depends on | Note |
|---|---|---|---|
| 1 | WP‑0 | — | Unblocks everything; every later fix writes into the profile rather than the prose |
| 2 | WP‑1, WP‑2, WP‑3 | WP‑0 | Identity and epoch are the irreversible decisions |
| 3 | WP‑14, WP‑15 | WP‑1, WP‑2 | Consistency and upstream rules, once the decisions exist |
| 4 | WP‑5, WP‑4, WP‑6 | WP‑1 | Write-path correctness |
| 5 | WP‑12, WP‑7 | WP‑2 (registry), WP‑1 | Detection must be correct before it is trusted; A‑16 depends on the registry |
| 6 | WP‑8, WP‑9, WP‑10, WP‑11 | WP‑1, WP‑12 | Contention, ordering and leases |
| 7 | WP‑13 | WP‑1 item 5, WP‑7, WP‑15 | Erasure depends on the history-model and retention decisions |
| 8 | WP‑16, WP‑17, WP‑18 | all | Evidence and enforcement close each package rather than following it — write the test with the fix, not after |

Chapter 30.4's existing Phase‑0 correction remains valid and is amended: the epoch coordinator (WP‑1) is now a Phase 0.2 prerequisite, because T‑5, T‑14 and T‑15 cannot run without it.

---

## 5. Traceability

| Finding | Package | Primary location | Gate |
|---|---|---|---|
| B1 | WP‑1 | §19.1, §24.4, Appendix A/B | 1 |
| B2 | WP‑2 | §15.2–15.3, F5, T‑1 | 1 |
| B3 | WP‑2 | new §10.4, §2.3, §19.1, §20.2 | 1 |
| B4 | WP‑3 | §10.1, §7.1, Chapter 13 | 1 |
| B5 | WP‑4 | §19.1, §19.3, §14.2, §25.1 | 2 |
| B6 | WP‑4 | §10.1 | 2 |
| B7 | WP‑5 | §15.4, §19.4–19.5 | 1 |
| B8 | WP‑6 | §19.4, §25.5 | 2 |
| B9 | WP‑7 | §24.2, Appendix B | 2 |
| B10 | WP‑8 | §7.4, §16.2–16.3 | 2 |
| B11 | WP‑9 | §21.3, §25.7 | 2 |
| B12 | WP‑10 | §17.3, §25.2, T‑3 | 2 |
| B13 | WP‑11 | §10.1, §19.6 | 2 |
| C1 | WP‑14 | Status line, §7.5, §8.4, §19.4, Appendix D.1 | 1 |
| C2 | WP‑14 | §7.5, §23.3, §29.3 | 1 |
| C3 / A‑1 / A‑2 | WP‑0, WP‑1, WP‑14 | reference profile; §19.4; all examples | 1 |
| A‑3 | WP‑1, WP‑13 | §24.4, new §24.6, ADR‑A68 | 3 |
| A‑4 | WP‑13 | §20.4, §30.1, catalogue §11.6 | 3 |
| A‑5 | WP‑13 | §6.1, catalogue §6.4 | 3 |
| A‑6 | WP‑13 | §6.2, §8.4, Appendix C | 3 |
| A‑7 | WP‑12 | S3, S4, S6, F5 | 2 |
| A‑8 | WP‑12 | §7.3, §7.5, §29.3 | 2 |
| A‑9 | WP‑12 | S5 | 2 |
| A‑10 | WP‑4 | new §24.1.1 | 2 |
| A‑11 | WP‑9 | S7, Appendix B | 2 |
| A‑12 | WP‑2, WP‑14 | §19.1, Appendix A/B | 1 |
| A‑13 | WP‑14 | §3.2, §10.2, §19.1, §23.2 | 1 |
| A‑14 | WP‑14 | Appendix A | 1 |
| A‑15 | WP‑6 | §19.4, §25.1 | 2 |
| A‑16 | WP‑7 | §20.2, §24.2, S6 | 2 |

---

## 6. Decisions required from humans

This plan specifies mechanisms; seven choices are not the agent's to make.

1. **Epoch coordinator.** Which external store holds the epoch high-water mark and the erasure register, and who operates it. Everything in Gate 1 and Gate 3 depends on this existing.
2. **Occurrence IRI determinism.** This plan recommends keeping deterministic revision IRIs and moving detection to txn cardinality (WP‑2). The alternative — random occurrence surrogates with position properties (catalogue §10.6) — restores subject-count fork detection but forfeits lexical range scans and the ground client template. A one-way decision.
3. **`fnd:replacedBy`.** Does Foundation define it? If not, the merge relation becomes profile-declared (C2).
4. **Erasure mechanism per family.** Per-subject graph drop or crypto-shredding. Crypto-shredding requires the §24.5 specification and interacts with content-addressed identity; graph drop requires per-subject modelling discipline from every domain author.
5. **Strong-ETag representation policy.** One serialisation for conditional requests, or tagged representations plus `Vary` (WP‑5).
6. **`recordedAt` source.** Server `NOW()` (audit-only, lint-warned) or client-injected. Must be uniform; still open in Appendix E item 4.
7. **Shard counts.** 64/16/16/1024 above are placeholders pending T‑3, K‑2 and O‑12 on the actual engines (Appendix E item 6).

---

## 7. Residual risk after remediation

| Risk | Residual state |
|---|---|
| Backup copies of erased personal data | Bounded by backup retention, not eliminated. Must be stated and accepted in the DPO review (Gate 3). |
| Coarse-conflict-detection engines | Detected and labelled, not fixed. Such deployments fall back to `SerializingProxy` or external sequencers; A6 does not hold for them. |
| Cross-epoch as-of reads | Explicitly unsupported or reported non-reproducible (catalogue §10.3). Not solved; declared. |
| Deadlock on multi-target single-request writes | Mitigated by retry and metrics; not eliminated (WP‑11). |
| Sparse global tier completeness | Detectable per stream, never provable globally. This is inherent to HLC (§3.3) and now declared rather than implied. |
| Guide length and coupling | WP‑0 extracts the grammar; the narrative/normative split for the *remaining* content (Appendix E item 9) stays open. The fixture-binding build check is what prevents recurrence in the interim. |

---

## 8. What this plan deliberately does not change

- **The core insights stand and must be preserved verbatim:** the three clocks; dense-per-stream/sparse-across-streams; the in-transaction counter closing G2; the txn claim as the outcome mechanism; A1–A7's case for separating the version row; P0–P7 as a stack; capability discovery over declaration; `min_level` fail-fast; deletion as policy with audit; bi-temporality as configurable.
- **The catalogue's framework-neutral stance (ADR‑A82)** is not weakened. The reference profile added in WP‑0 is opt-in under ADR‑A82 §6 and does not become adopter policy.
- **ADR‑A68's mechanism** — per-subject graphs, graph drop plus tombstone, pseudonymous ledger references — is not replaced. WP‑13 closes the paths by which the rest of the architecture would have defeated it.