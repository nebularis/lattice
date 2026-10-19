# Review: RDF & SPARQL Patterns Guide, IRI and Identity Patterns, and IRI Policy

**Review state:** Closed 2026-09-23. Every finding is dispositioned in [iri-patterns-post-3866b21-remediation.md](../status/iri-patterns-post-3866b21-remediation.md), which also lists the follow-on work and where it is tracked.

## Summary

The set is unusually strong. It explains why each pattern exists, marks most portability hazards, and correctly treats the TCK as the source of truth rather than vendor documentation. The remediation passes in D.1 and D.2 fixed many real bugs.

However, several defects remain that would cause silent data loss, a wedged system, or unenforceable guarantees if the examples were copied into production. Some are new; some were left behind when earlier text was corrected and not every copy was updated. The most serious are:

1. **Epoch bump wedges every aggregate.** The procedure for what happens to version rows after an epoch bump is undefined, and with the dual epoch guards, every write fails permanently.
2. **Two "dense" sequencers are not dense.** S8 recommends PostgreSQL `BIGSERIAL` and Redis `INCR`, which have the pre-allocation hole (G2) that the guide itself identifies.
3. **The global HLC read reintroduces G2.** HLCs are assigned before commit, and the example read has no upper bound.
4. **TTL-pruning txn claims is not safe for appends.** A late retry duplicates events.
5. **Appendix B contradicts the body.** It ships a fork shape the guide proves can never fire, and a `sh:class` constraint the guide says must never be added.
6. **Idempotency keys don't bind request content.** A reused txn id with different content is reported as applied.

Details follow, grouped by severity, with a suggested fix for each.

---

## A. Critical: correctness or data-loss defects

### A1. Epoch bump leaves version rows unwritable (§19.1, §10.1, §24.1, §24.4)

Every write guards on the same epoch value twice:
- the dataset node: `<urn:ds:prod> pat:epoch "3"`
- the row itself: `<urn:g:orders/1> pat:epoch "3"`

The §24.4 runbook bumps only the dataset epoch. After the bump to 4:
- A client using epoch 4 fails the row guard, because every row still says 3.
- A client using epoch 3 fails the dataset guard.

No write can ever succeed again. The runbook never says whether version rows are rewritten to epoch 4, whether `pat:seq` restarts at 1 or continues, or what `pat:prevRev` points at across the boundary.

Each choice has consequences the guide doesn't address:
- **If `seq` continues,** the S3 gap scan (pinned to one epoch) reports every stream as starting at 43 with no earlier receipts.
- **If `seq` restarts,** the rows must be reset in bulk.

**Fix:** specify the row-migration step (lazy per-row rebase on first write, or bulk rewrite), the `seq` policy, and the cross-epoch `prevRev` rule. Add a TCK test that performs a write after the bump, not just a rejection of a stale write (T-5 only covers the rejection).

### A2. S8 external sequencers are not dense and have the G2 hole (§S8, §25.4 `ExternalSequencerStrategy`)

`ExternalSequencerStrategy` claims `TOTAL_DENSE` / `PER_STREAM_DENSE` and lists Kafka offsets, `BIGSERIAL`, `nextval` and Redis `INCR`. This is wrong for most of them:

- **`BIGSERIAL`/`nextval` and `INCR`** allocate before the RDF write commits. Failed writes leave gaps, and concurrent writers can commit out of order. This is exactly G2, and the guide itself cites "the PostgreSQL sequence-versus-LSN gap."
- **Kafka offsets** are per partition, not per stream. With `hash(stream) mod N`, a partition carries many streams, so offsets are not per-stream dense. Transaction markers and compaction also create offset gaps.

Density holds only if one serialised writer per stream allocates and writes, and reuses the same number on retry.

**Fix:** downgrade these to `TOTAL_SPARSE` unless paired with a single writer per stream that retries with the same number. Remove the density claim for sequences and `INCR`.

### A3. The global HLC read has the allocate-then-commit hole (§21.3, §19.4)

`pat:hlc` is taken by `clock.send()` in the client before the update is issued. A slow transaction with an earlier HLC can commit after a consumer has already read past it with `FILTER(?hlc > …)`.

- The example query has no watermark or lag bound, so it is exactly the G2 failure.
- The per-target contiguity check only detects the skipped revision when a later revision for the same target arrives. If the skipped revision is a stream's last write, the loss is silent indefinitely.
- `LagWindowRead` is only safe if the lag exceeds the maximum transaction duration plus clock skew. Neither bound is stated.

**Fix:** show the watermark or lag upper bound in the example query. State the lag-sizing rule. Mark the unbounded form as unsafe.

### A4. TTL-pruning txn claims is unsafe for the append form (§15.2, §24.2)

§15.2 says a claim pruned too early "turns a late retry into a spurious `412`, which is safe." That holds only for the CAS form, where the expected-version guard also fails.

The append form (§10.1, `Expectation.Any`) has no version guard. Its only idempotency protection is the txn claim. A retry after the 72-hour TTL (for example, an outbox relay draining a backlog after an outage) appends the events again and burns a new sequence number.

Pruning also deletes the evidence that the F5 fork-detection query depends on.

**Fix:**
- For append families, require TTL ≥ the maximum outbox or redelivery horizon, or make event IRIs (already txn-derived) the idempotency witness via `FILTER NOT EXISTS` on the event subject.
- Add a receipt-side fork audit: any `pat:Revision` with more than one `pat:txn`. This survives txn-claim pruning.

### A5. Idempotency keys don't bind request content (§30.2 rule 3, §19.2, Appendix A `pat:rev`)

§30.2 says `requestDigest` "is what the claim records." But the txn claim stores only `pat:rev`.

If a client reuses a txn id with a different payload, `FILTER NOT EXISTS` makes the update a no-op, the `ASK` returns true, and the caller is told `Applied` even though its content was never written. The PostgreSQL rule this is supposed to translate explicitly rejects this case.

**Fix:** add `pat:requestDigest` to the txn claim. On an `ASK`-true result, compare digests and return a distinct `IdempotencyKeyReuse` error on mismatch.

### A6. Appendix B contradicts the body of the guide

**`pat:NoForkShape` can never fire.** It detects forks as "two revisions sharing a `prevRev`." F5, §15.3 and the Appendix A comment all explain that deterministic revision IRIs make this impossible: colliding writers produce one subject, not two. Yet Appendix B still recommends the shape and discusses its cost, and T-11 relies on it. The effective constraint is `sh:maxCount 1` on `pat:txn`.
- **Fix:** delete the shape, or replace it with a `sh:sparql` check on txn-claim cardinality.

**`pat:RevisionShape` includes `sh:class pat:Revision` on `pat:prevRev`.** §24.2 says this constraint "would break under pruning and must not be added," and the §19.7 copy of the shape omits it. With monthly buckets, it also fails on validators that validate named graphs individually, because the predecessor sits in last month's bucket.
- **Fix:** remove it, and align the §19.7 and Appendix B copies of the shape.

**`pat:EventOrderShape` requires `pat:opSeq` on every event.** S5 says commit-grain families (`dal:CommitGrain`) legitimately lack it, so the shape rejects valid data.

**`pat:VersionRowShape` targets `sh:targetSubjectsOf pat:seq`.** This also matches every receipt, since receipts carry `pat:seq` too. It is harmless today but fragile.
- **Fix:** target by an explicit class or graph.

### A7. §24.2 falsely claims the live head is always in the newest bucket

The text says "the live `pat:head` is always in the newest bucket," and uses this to justify prefix-only retention. In fact, a stream last written 14 months ago has its head in an old bucket; S4 itself notes this case. With `log: 400d`, prefix pruning deletes the receipt that a live head points at.

**Fix:** pin buckets that contain any live head, or copy the head receipt forward on rotation. Add a test for this case.

---

## B. Major: misleading or unsafe guidance

**B1. The ETag form is still inconsistent.** §15.4 and §19.4 correctly require strong ETags. But weak `W/` forms remain in:
- F3 (`ETag: W/"42"`)
- F4 (`ETag: W/"3-42"`)
- the Glossary (`W/"{epoch}-{seq}"`)
- §30.2 rule 1

Readers copying the Glossary or §30.2 will produce ETags that fail every `If-Match`.

A related point: a strong ETag asserts byte-identical representations. Turtle serialisation order can vary between two reads of the same version, so the serialiser must be deterministic, or the "strong" claim is technically false.

**B2. The `firstWrite` / `OPTIONAL pat:head` logic contradicts itself.**
- The inline comment in §19.1 is correct: under `PreCreatedRow`, the row has no head on its first CAS.
- §14.2 and §19.3 say the opposite: that `PreCreatedRow` never needs the `OPTIONAL`, and that `AbsentRow` is why it exists. But the §19.3 create path does write `pat:head`.
- Separately, the §24.1 delete makes `pat:head` mandatory, so a pre-created, never-written row cannot be deleted.

**B3. The create path lacks the dataset-level epoch guard (§19.3, §14.2).** The CAS, append and delete forms all have the B1 guard; the create path does not. A stale client can create with `e3` IRIs after a bump to 4. Add the guard and a test for it (T-9 plus a restore).

**B4. The deadlock guidance contradicts itself.** §10.1 and §19.6 correctly say that sorted order in query text does nothing. §25.7 lists "counters and version rows acquired in **sorted order**" as a non-negotiable. Reconcile §25.7 with `dal:deadlockPolicy`.

**B5. Target IRIs are inconsistent in the queries.** §10.1 insists that one target IRI is used everywhere (`<urn:g:orders/1>`, "B3"). S2 and the S4 head lookup query `<urn:stream:orders/1>`, which returns nothing against data written by the documented write paths.

**B6. The Chapter 21 and Chapter 26 store tables contradict each other.**
- §21.2 puts Virtuoso and RDF4J under "HLC only. Do not add a global counter."
- §26.1 gives Virtuoso `NativeSequence` as its dataset tier ("strongest dense option") and gives RDF4J an `InTxCounter` dataset tier.

**B7. S3's low-water-mark check has undefined semantics.**
- Appendix A defines `pat:retentionLowWaterMark` as "the lowest `pat:seq` the retention job has pruned up to."
- S3 treats it as "the lowest seq still present."

Under the Appendix A definition, `FILTER(?lo > ?expectedLo)` fires for every pruned stream. There are further gaps:
- Streams never pruned have no row, so a lost prefix goes undetected. Bootstrap every stream's mark to 0 or 1.
- Streams with no surviving receipts are not checked at all.
- `urn:g:retention` is missing from the §2.3 graph inventory.

**B8. Outcome classification is too narrow (§19.4).**
- Only `TimeoutError` routes to `UNKNOWN`. Connection resets, 5xx responses, proxy 502/504 and client crashes after sending are equally ambiguous and must also go to `UNKNOWN`.
- The confirming `ASK` must go to the writer or primary. A negative `ASK` on a lagging replica gets classified as a definitive `CONFLICT`, and the caller then re-decides on top of a write that actually applied.
- `CONFLICT` also conflates guard failure with a tombstoned target or a changed epoch. These should map to 404/410 and resync respectively, not 412 plus retry. The §25.7 append loop retries tombstoned streams pointlessly.
- For the append form, the client cannot know the revision IRI, so `resolve` must `ASK { <txn> pat:rev ?any }`, not the specific-rev form shown.

**B9. The HLC is never merged across nodes (§S7, §19.4).** `receive()` is defined but never called. Without it, each node's HLC is just its own physical clock plus a counter, so the "causally consistent" claim does not hold across writers. Call `receive(head.hlc)` on the head receipt read before a CAS, or before an append that follows a read.

**B10. The normalization pipeline is specified four different ways.**

| Where | Pipeline |
|---|---|
| Guide code, `PERSON_EMAIL_V1` | strip(hand-picked 5 characters) → NFKC → trim → casefold |
| Guide §25.3 declaration | `[nfkc, trim, casefold]` (missing the strip step) |
| iri-identity §7.3 | NFKC(strip(NFKC(x)).casefold()), using the full `Default_Ignorable_Code_Point` property, not a hand-maintained subset |
| iri-policy | none; the pipeline is left unspecified |

The problems:
- **Idempotence:** the guide's order does not re-normalize after `casefold`, so it is not guaranteed idempotent. Unicode's defined `NFKC_Casefold` / `toNFKC_Casefold` should be referenced instead of ad-hoc compositions.
- **Domain semantics:** casefolding or NFKC-normalizing an entire email address changes its semantics (the local part is technically case-sensitive, and `ß` becomes `ss`). This is fine as a declared business rule, but the guide presents it as the correct generic answer.
- **Missing coverage:**
  - Neither document addresses confusables or homoglyphs (UTS #39), which is the realistic way K2/K4 uniqueness gets bypassed.
  - IDN handling is deferred to v2 while v1 claims are issued, so `bücher.example` / `xn--…` duplicates ship in v1 by design.

**B11. Claim and IRI derivations use delimiter concatenation.** `claim_iri` and `deterministic_iri` hash `f"{version}|{constraint}|{scope}|{key}"`. iri-identity §7.2 calls delimiter concatenation "unsafe" and requires self-delimiting tuple encoding. The `|` character is legal in an email local part, and scope tokens are not guaranteed to exclude it. Use the length-prefixed encoding from §7.2.

**B12. The example outputs are placeholders, not the verified values D.1 claims.**
- `MFRGGZDFMZTWQ2LK` is base32 of the ASCII string `"abcdefghij"`.
- `GEZDGNBVGY3TQOJQ` is base32 of `"1234567890"`.

Both are 16 characters, which corresponds to 10 bytes. With the documented `nbytes=16`, the output would be 26 characters. So D.1's statement that example outputs are "computed and verified" is false for the claim IRIs.

The `deterministic_iri` output has the right length for 20 bytes but cannot be checked from the text. The comment "keyed hash of `person-email|acme|…`" also doesn't match the actual hash input (`v1|person-email-unique|…`).

Recompute these values, or label them as placeholders.

**B13. Fence datatypes drift (§7.4).** §7.4 inserts `pat:fence 7184` and bootstraps `pat:fence 0` as plain `xsd:integer`. §16.2 and Appendix A use `xsd:long`. The two are different RDF terms, so a mix leaves two fence values on one node and the guard matches twice. This is exactly the F7 failure the guide warns about elsewhere. Type all fence values as `xsd:long`.

**B14. S8 and S7 aside, other examples break the guide's own rules.**
- S5 uses an unbound `GRAPH ?log`, which F6 forbids.
- Epochs are unpadded (`e3`) everywhere. iri-identity §10.2 explains that `e10` sorts before `e3`, and requires either padding or a declared "no cross-epoch lexical scans" rule. The guide does neither.
- The 16-digit versus 19-digit width split is exactly what iri-identity §10.2 calls invalid for identity-bearing strings. D.2 acknowledges this but it remains unfixed.

---

## C. Safety, security and operations gaps

**C1. The SPI allows arbitrary graph writes.** `CasCommand.inserts` is a `List<Quad>` with no restriction on which graphs it targets. The same applies to TriG accepted by a GSP proxy. A caller could forge version rows, txn claims, key claims or receipts.

**Fix:** the port must reject any insert or delete outside the aggregate's payload graph, and infrastructure quads must be generated only by the adapter.

**C2. Running the TCK at registration is dangerous.** It includes destructive and disruptive tests:
- backup/restore (O-4, T-5)
- stepping the wall clock back (O-6)
- a 10M-triple bulk load
- creating 10⁶ graphs

Running these "at registration" against a production backend is unsafe. Specify a non-production instance with the identical image, configuration and topology.

**C3. The TCK is over-claimed and missing coverage.**
- Passing six torture tests cannot *prove* `LINEARIZABLE` behaviour. Tests can only falsify it. Call the result "no violation observed under the tested conditions."
- There are no failover, leader-change, partition or replication-lag tests (Jepsen style). This is where clustered stores such as Neptune typically violate assumptions.
- O-8 is a query-modelling test, not a store property, so it is an odd gate for a CAS capability.
- D.2 refers to "T-4 through T-13," but only T-1 to T-11 exist.

**C4. The epoch guard under snapshot isolation needs quiesced writers.** A CAS only *reads* the dataset node. A concurrent epoch bump therefore does not conflict with it, and under snapshot isolation the CAS can commit under the old epoch. This is safe only if writers are stopped during the bump (`WriterStartRefusal` or a runbook step). State this explicitly.

**C5. Erasure and the running example conflict.**
- The §24.1 deletion example is a GDPR erasure of an order in a family declared `patch_log` (§29.3). This is precisely the combination that `dal:PersonalDataReceiptCompatibilityShape` forbids, because the payload survives in the delta graphs.
- People live in one shared `urn:g:people` graph. That is incompatible with `PerSubjectGraphDrop`, and it is not an aggregate with a version row.
- Retired key claims (`pat:retiredBy <person>`) are kept forever. With the HMAC secret, that confirms "this email was once a customer." iri-identity §6.4 and §11.5 say claims may need physical deletion; the guide's P1/P2 text only ever tombstones.
- The §24.4 restore runbook omits the erasure-register replay required by iri-identity §11.6, so a restore silently reinstates erased data.
- §24.0's "no deletes until the Phase 0 exit gate passes" cannot override a legal erasure obligation. iri-identity §11.5 says as much; the guide should too.

**C6. The recreate path is undocumented.** "A later recreate is a CAS from 43 to 44 that removes `pat:deleted`" fails with every documented shape:
- The §19.1 CAS guard excludes tombstoned rows.
- The §19.3 create path requires that no row exists.

Provide the shape.

**C7. The keys graph's access-control assumption is weak.** Many SPARQL endpoints have no graph-level ACLs, and union-default-graph stores expose every graph to any query. The PII argument for P1 depends on an ACL capability that is neither in `StoreCapabilities` nor tested by the TCK.

**C8. Unregistered URN namespaces.** `urn:g:`, `urn:rev:`, `urn:key:`, `urn:txn:` and `urn:order:` use unregistered NIDs (see RFC 8141). They will be copied from the examples verbatim, and they collide on any dataset merge. iri-identity §17 lists this as open; the guide should flag its examples as illustrative only.

**C9. The YAML declaration and the `dal:` vocabulary are two configuration surfaces that have diverged.** The §29.3 YAML omits many choices the prose makes mandatory through `dal:` properties:
- epoch authority and guard scope
- `firstWrite`
- `deadlockPolicy`
- ETag form
- retention mode and as-of floor source
- global read strategy
- txn/log/key sharding
- privacy profile

Specify which surface is authoritative and how one maps onto the other.

---

## D. Cross-document inconsistencies (iri-identity-patterns and iri-policy)

1. **Store-local epoch.** iri-identity §10.3 says store-local epoch is "**prohibited**" for position-derived occurrence identity. iri-identity §14.1 and §15 and guide §24.4 say it is "warned, not refused." Pick one.

2. **Key rotation (§6.4 versus §15).** iri-identity §6.4 describes rotation as "write a new claim, backfill, retain a mapping." §15 explicitly says that description is insufficient without a dual-write phase. Update §6.4 to include the phase.

3. **Revision class alignment.** iri-identity §10.1 says `pat:Revision rdfs:subClassOf prov:Activity`. Guide §23.3 and Appendix E consider `fnd:Evidence`. Appendix A declares neither. This is exactly the "alternating classes" problem §10.1 warns against.

4. **Status contradiction.** iri-identity §1 says the `ontology/persistence` extension is "future… until then." §14 says an initial slice is already specified.

5. **Missing cross-reference.** iri-identity "Related" omits ADR-A82, which the other two documents cite as the superseding decision.

6. **Rendering defect.** In iri-identity §17, `\u00a714.1` renders as literal escape text instead of "§14.1."

7. **iri-policy.md contradicts its own status.** The header says "Historical… Not normative," but the body still says:
   - "Rules (normative…)"
   - "Recommended default"
   - "single source of truth" (for the validator)

   Its content also conflicts with the current guidance:
   - §3.4 canonicalizes literals only for hashing, which iri-identity §8.2 explicitly forbids.
   - §5 claims skolem IRIs are deterministic while prescribing random UUIDv4 surrogates.
   - Rule 7 ("all-lowercase") conflicts with its own `POL-000123` example.
   - The "UUIDv4" example `01j9z8q3-k4m5-n6p7-…` is not a valid UUID; it contains non-hex characters.

   Strip or clearly fence the body, so it cannot be mistaken for guidance.

---

## E. Minor and editorial

- **§24.2 table:** a prose paragraph splits the retention table, so the "Delta graphs" and "Snapshot graphs" rows render as orphaned text.
- **Appendix A `pat:opSeq`:** refers to "§10.1's P3 pattern," but §10.1 is S1.
- **F5 cross-reference:** says "the F2/F3 fix below," but F2 and F3 are above it.
- **§2.3 inventory:** says "five kinds of infrastructure graph." Event, delta and retention graphs used later are missing from it.
- **`pat:stableWatermark`:** uses an unpadded string (`"3:91438"`), so it sorts wrong lexicographically.
- **§6.2 idempotency:** "re-running is a no-op" is true only if the payload is byte-identical; it re-inserts payload.
- **§1.3 atomicity:** SPARQL 1.1 Update says each request **SHOULD** be treated atomically. "Does not require" is accurate, but citing the SHOULD is more precise.
- **S6 as-of and blank nodes:** triple-level as-of matching silently fails for blank nodes across delta graphs. This is covered by the skolemization rule, but worth stating at S6.
- **SHACL validation scope:** SHACL validates a data graph, not a dataset. Whether cross-graph shapes see the union of graphs is engine-specific. This affects every shape in Appendix B and belongs in `StoreCapabilities` and the TCK.
- **§24.3 step 4:** "advance the version rows… in one transaction" is infeasible at the stated 20M-aggregate scale. Specify a batched, gated cut-over instead.

---

## Recommended priority

1. **Fix A1–A7.** These can corrupt or wedge production.
2. **Make the copyable artefacts consistent.** This covers the shapes,

