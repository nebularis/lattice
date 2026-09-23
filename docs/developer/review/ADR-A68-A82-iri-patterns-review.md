# Review: RDF operational-patterns documentation set

## Scope and limits

I reviewed all five documents against each other, against the standards they cite (SPARQL 1.1, SHACL, RFC 9110, RFC 4648, XPath F&O numeric semantics, GDPR Recital 26), and against the rules the documents set for themselves.

Several referenced documents were not provided, so I could not check agreement with them:
- `data-architecture.md`, `iri-policy.md`, the ADR-A51 review and disposition documents
- ADR-A54, ADR-A63, ADR-A67, ADR-A74, ADR-A75, ADR-A78

I also could not execute the Python examples.

**Verdict:** the set is not safe to apply to production as written.
- The identity catalogue (`iri-identity-patterns.md`) and ADR-A82 are broadly sound. They are the stricter documents.
- Most problems are in `rdf-sparql-patterns-guide.md`. It still treats the superseded ADR-A51 as live and breaks several of the catalogue's rules.
- More seriously, the "corrected" CAS pattern has defects that defeat the guarantees the guide claims for it: epoch safety, fork detection and outcome resolution.

The findings below are ordered by severity. Section numbers refer to the patterns guide unless stated otherwise.

---

## 1. Blocking defects (production-unsafe)

### B1. The epoch guard does not protect against restore (F3 is not actually fixed)

The write path never reads the dataset epoch.
- §19.1 guards on the version row's own `pat:epoch "3"`.
- The Python client takes the epoch from the caller's ETag (`expected.epoch`).
- The §24.4 runbook bumps only `<urn:ds:prod> pat:epoch`, which the write path never reads.

After a restore, every version row still says epoch 3. A stale client holding `W/"3-42"` therefore matches the restored row. It succeeds against a different history and mints `urn:rev:orders/1/e3/0000000000000043`. That IRI may already exist in exports, CDC sinks and `prevRev` references taken before the restore. This is exactly the aliasing F3 and Appendix D.1 claim to have fixed. TCK T-5 would fail.

There is a second hazard. §24.4 says "bump `pat:epoch`", but the value being bumped is itself restored data. Suppose you restore twice from the same backup. Epoch 3 is bumped to 4 both times, and epoch 4 is reused. The catalogue (§10.3) already classifies a store-local epoch as unsafe. The guide ignores this.

**Fix:**
1. Allocate each new epoch from an external high-water mark (the highest epoch ever issued, plus one).
2. In the same maintenance transaction, before writers start, rewrite every version row's `pat:epoch` to the new value.
3. Add a dataset-epoch guard to every write (CAS, append, create, delete):
   ```sparql
   GRAPH <urn:g:dataset> { <urn:ds:prod> pat:epoch "4"^^xsd:long }   # client's expected epoch == current
   ```
4. Adopt one of catalogue §10.3's fail-safe strategies by name in §24.4.

### B2. Lost updates are invisible under the corrected design; the fork query cannot fire

Revision IRIs are deterministic from `(aggregate, epoch, seq)`. So when two writers both win a CAS from 41 under broken isolation, they both mint the *same* subject, `…/e3/0000000000000042`, with the same `pat:prevRev`.

Set semantics then collapse the evidence:
- There is one receipt carrying two `pat:txn` values.
- There are two txn claims, both pointing at it.

As a result:
- The F5 fork query (`GROUP BY ?prev HAVING COUNT(*) > 1`) and `pat:NoForkShape` return nothing.
- T-1's "exactly one receipt" and "fork query returns zero rows" both **pass while the system is corrupt**.
- Both clients' `ASK` returns true, so both are told `APPLIED`.

This is the §1.1 counter problem again, one level up. The example fork (`…0042-b`) can never be produced by `rev_iri()`.

**Fix:**
- Rewrite §15.3, F5 and T-1 so detection rests on "more than one txn per revision":
  ```sparql
  SELECT ?rev (COUNT(DISTINCT ?t) AS ?n)
  WHERE { GRAPH <urn:g:txn> { ?t pat:rev ?rev } }
  GROUP BY ?rev HAVING (COUNT(DISTINCT ?t) > 1)
  ```
- At commit time, the effective shape is `RevisionShape`'s `pat:txn sh:maxCount 1`, which is SHACL Core. An inverse-path `[sh:inversePath pat:rev] sh:maxCount 1` also works where the validator's data graph spans both graphs. Keep `NoForkShape` only for non-deterministic revision schemes.
- Strengthen the confirming `ASK` so a racing winner learns about corruption:
  ```sparql
  ASK { GRAPH <urn:g:txlog/…> { <rev> pat:txn "mine"
        FILTER NOT EXISTS { <rev> pat:txn ?o FILTER(?o != "mine") } } }
  ```

### B3. Revision IRIs collide between the stream form and the aggregate form

Two different version rows mint revisions into the same namespace:
- The append form (§10.1) keys its row on `<urn:stream:orders/1>` and mints `urn:rev:orders/1/e3/…`.
- The CAS form (§19) keys its row on `<urn:g:orders/1>` and mints `urn:rev:orders/1/e3/…` via `rev_iri("orders/1", …)`.

These are two independent counters sharing one IRI namespace, which is F2 reintroduced. The §2.3 and §10.2 examples already show `urn:rev:orders/1/e3/…` receipts with two different `pat:target` values. S6 (`urn:stream:`) and §20.2 (`urn:g:`) disagree in the same way.

Chapter 22's claim that "a stream can be appended to … and compare-and-set … without two mechanisms" requires a single version row.

**Fix:**
- Make one target IRI the version-row subject for each stream.
- Derive the revision namespace injectively from that exact IRI (for example, an encoded or hashed target), rather than by stripping a `urn:g:` prefix.

### B4. `?n + 1` silently changes datatype from `xsd:long` to `xsd:integer`

Under SPARQL 1.1 §17.3 and XPath F&O, `op:numeric-add` on integer-derived types returns `xsd:integer`. Pinning the input to `xsd:long` does not prevent this, contrary to the claim in §10.1.

S1 and P3 therefore write counters typed `xsd:integer`, with three consequences:
- `VersionRowShape` (`sh:datatype xsd:long`) rejects the commit on SHACL-validating stores.
- On non-validating stores, the next guard on `"n"^^xsd:long` stops term-matching, and the stream wedges.
- The Chapter 13 gotcha row describes this exact hazard without noticing that the guide's own queries trigger it.

**Fix:** `BIND(xsd:long(?n + 1) AS ?n1)` in S1 and P3. Add a datatype round-trip test to the TCK.

### B5. The recommended pre-created version row makes the first CAS impossible

§14.2 and §19.3 recommend pre-creating `pat:seq "0"` with no head, so that "the CAS shape above is the only shape ever used". But §19.1's `WHERE` requires `pat:head ?prevRev` as a mandatory triple. With no head, nothing matches, and every first write returns `412`.

**Fix:** make the head optional:
```sparql
OPTIONAL { GRAPH <urn:g:meta/17> { <urn:g:orders/1> pat:head ?prevRev } }
```
Unbound `?prevRev` then drops harmlessly from both templates.

### B6. The append form does not maintain the head or the chain

S1 increments `pat:seq` but never updates `pat:head` and never writes `pat:prevRev`, yet the §10.2 receipt shows one. On a stream written by both forms:
- The CAS form reads a stale head.
- The receipt chain has holes.
- T-4 ("single unbroken path") fails.

**Fix:** in the append update:
- Read `pat:head ?prev` (optionally).
- Delete it and insert the new head.
- Emit `pat:prevRev ?prev`.

### B7. Weak ETags never satisfy `If-Match`

RFC 9110 §13.1.1 requires `If-Match` to use strong comparison, and a weak tag never matches under strong comparison. With `W/"3-41"`, a compliant server or proxy returns `412` on every conditional `PUT`. §15.4 and §19.5 (and the Python `Version.etag`) are therefore non-functional over standard HTTP.

**Fix:**
- Use a strong tag, `"3-41"`.
- If multiple serialisations are served for one version, include the format in the tag or document `Vary` handling.

### B8. Outcome resolution after a timeout is wrong

§19.4 `compare_and_set` calls `resolve()` after a `TimeoutError` and maps `ASK == false` to `CONFLICT`. But a false answer during a timeout can simply mean the original request is still executing.
- **Append form:** the caller retries under a new txn id, and duplicate events land when the original commits.
- **CAS form:** the caller is told "412, re-decide" while its original write may still apply.

`Outcome.UNKNOWN` is defined but never returned, which contradicts the Java port (§25.1) and retry rule 3 (§25.5).

**Fix:** after a timeout, either:
- re-submit the *identical* request with the *same* txn id until a definitive answer arrives (this is safe because it is idempotent), or
- return `UNKNOWN`.

Never map "not yet visible" to `CONFLICT`.

### B9. Retention pruning breaks every quiet aggregate on SHACL-validating stores

§24.2 drops whole month buckets after 400 days, but `pat:head` on an aggregate untouched for longer than that points at a pruned receipt. On the next write:
- The new receipt's `pat:prevRev` targets an untyped IRI.
- `RevisionShape`'s `sh:class pat:Revision` fails.
- With commit-time SHACL (the recommended upgrade path), **every write to an old aggregate is rejected**.

**Fix, either:**
- retention always preserves each stream's head receipt, or
- drop `sh:class` from `pat:prevRev` and treat pruned predecessors explicitly, recording the retention low-water mark.

### B10. Fencing tokens are checked but never advanced

§7.4 and §16.2 guard with `FILTER(?f < mytoken)` and never write the new token. This has two effects:
- A stale holder with any token above the *stored* value still passes, so there is no fencing.
- The legitimate holder's second write with the same token fails, because the comparison is strict.

**Fix:** guard with `?f <= mytoken`, and in the same update `DELETE ?f` / `INSERT mytoken`.

### B11. Global HLC pagination reintroduces the G2 reorder hole

The client stamps the HLC before commit. §21.3's `FILTER(?hlc > last) ORDER BY ?hlc` can therefore permanently skip a receipt with a lower HLC that commits after a higher one.

Per-target contiguity (S3) detects the loss only *after* the consumer has advanced. This is the pre-commit case that §25.7's stable watermark exists for, but §21.3 does not apply it.

**Fix:** a global HLC reader must do one of the following:
- read only below a stable watermark or lag window, or
- rescan from the stream position whenever the contiguity check fails.

### B12. Contention is sharded for the meta graph only

F12 and T-3 shard the version rows, but every write also inserts into the single graphs `urn:g:txn` and `urn:g:txlog/2026-09`. P3 claims all live in `urn:g:keys`. On an engine with graph- or page-granular conflict detection, every write in the dataset conflicts on these graphs, so A6 is lost anyway.

**Fix:**
- Extend T-3 to measure contention on the txn, log and keys graphs.
- Make their sharding part of the topology declaration.

### B13. Lock ordering cannot be controlled through the order of `WHERE` patterns

§10.1 and §19.6 say to "acquire version rows in sorted IRI order" by listing them that way in `WHERE`. SPARQL gives no control over evaluation or lock order; the optimiser reorders patterns freely.

**Fix:**
- State that deadlock avoidance depends on engine deadlock detection plus retry, or on an external ordering mechanism (a lock service or partitioned writer).
- Add a two-stream opposite-order TCK test.

---

## 2. Cross-document inconsistencies

### C1. The guide still treats superseded ADR-A51 as authoritative
The guide cites A51 as the live authority in:
- the Status line
- the `claim_iri` docstring ("ADR-A51's minimum content-hash width")
- §7.5 (`fnd:replacedBy` "(ADR-A51)")
- §8.4 ("what ADR-A51 names `surrogate-claimed` and adopts…")
- the §19.4 ULID note ("ADR-A51 rule 2")
- Appendix D.1

**Fix:** repoint each to the relevant section of the catalogue (§6.4, §7.4, §11) or to ADR-A82.

ADR-A51's header also says "Superseded by ADR-A82" while ADR-A82 is still Proposed. Word it as "to be superseded on ratification of A82", or record both as proposals.

### C2. `fnd:replacedBy` is used but not defined
P7 prescribes `fnd:replacedBy`, but the guide's own list of Foundation terms (§23.3) does not include it. Catalogue §11.4 forbids writing a relation that the selected ontology does not define.
- **Fix:** either confirm the term exists in Foundation, or make the merge relation a profile-declared property.

### C3. Identifier widths are not fixed, which the catalogue forbids
Catalogue §7.4 and §10.2 both reject variable widths. The guide has