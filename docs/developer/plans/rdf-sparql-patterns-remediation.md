<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# RDF & SPARQL Patterns Guide — Remediation Plan

**Unit ID:** `rdf-sparql-patterns-remediation`
**Unit type:** Plan (documentation remediation, no code)
**Status record:** [rdf-sparql-patterns-remediation.md](../status/rdf-sparql-patterns-remediation.md)
**Sketch:** None. The defects are fully specified by the governing review; no design exploration is needed to locate them, only to resolve the handful of items flagged below as design decisions.
**Governing review:** [ADR-A68-A82-iri-patterns-review.md](../review/ADR-A68-A82-iri-patterns-review.md) (2026-09-23). Treated as current and authoritative for this plan. Where that review's own text is incomplete (§C3), this plan says so rather than inventing content.
**Primary target document:** [rdf-sparql-patterns-guide.md](../../architecture/rdf-sparql-patterns-guide.md)
**Secondary target document:** [ADR-A51-iri-and-identity-policy.md](../../architecture/decisions/ADR-A51-iri-and-identity-policy.md) (one header-wording fix, C1)
**Reference-only document:** [iri-identity-patterns.md](../../architecture/iri-identity-patterns.md) — cited throughout as the authority the guide's identity-adjacent passages must repoint to. No changes proposed to this document.

## 0. Purpose, scope and constraints

This plan enumerates every defect in the governing review, maps each to its exact location(s) in the source, and specifies the change required, including all named options and their consequences where the review or the surrounding text presents more than one valid fix.

**This plan makes no changes.** Per the Agentic Development Contract's Design First and Planning Mode rules, and per the explicit instruction under which it was written, no edit has been applied to `rdf-sparql-patterns-guide.md` or any other file as part of producing this document. Implementation is one or more future slices, gated on the human confirming the items marked **Decision required: YES** below, per the Pause For Architectural Guidance clause: several fixes are design decisions with real operational trade-offs, not mechanical corrections, and this plan does not pre-empt them.

**On the review's own completeness.** The governing review's §2 (Cross-document inconsistencies) ends mid-sentence at finding C3: *"Catalogue §7.4 and §10.2 both reject variable widths. The guide has"* — the source file itself is truncated at that point, not merely the excerpt seen in chat. §B.14 below records what can be independently established about C3 from the guide and the catalogue, and flags the rest as pending confirmation from the review's author rather than presenting a guess as the review's own conclusion.

## 1. Severity and decision legend

| Marker | Meaning |
|---|---|
| **Blocking** | From review §1. Production-unsafe as written. |
| **Cross-doc** | From review §2. Consistency and citation defects. |
| **Decision required: YES** | The fix has more than one architecturally valid option with different operational consequences. Do not implement until a human picks one (or an explicit combination). |
| **Decision required: NO** | The fix is a single correct correction (a spec-conformance bug, a missing cross-reference, an internal inconsistency with only one valid resolution). Safe to implement without further design discussion. |
| **Decision required: VERIFY** | The fix depends on a short factual check outside this plan's scope (for example, whether an ontology term exists) before the mechanical edit is made. |

## 2. Findings ledger

| ID | Severity | One-line defect | Primary guide location(s) | Decision |
|---|---|---|---|---|
| B1 | Blocking | Epoch guard never reads the dataset epoch; restore-safety (F3) is not actually enforced | §19.1, §19.4, §24.4 | YES |
| B2 | Blocking | Deterministic revision IRIs make the fork query and T-1 pass while the system is corrupt | §15.3, Ch.18 F5, §19.2, Ch.27 T-1 | NO (single valid fix; alternative is foreclosed) |
| B3 | Blocking | Two version-row keying schemes mint into one revision namespace | §2.3, §10.1, §10.2, Ch.11 S6, §19.4 | YES |
| B4 | Blocking | `?n + 1` silently drifts from `xsd:long` to `xsd:integer` | §7.1, §10.1 | NO |
| B5 | Blocking | Mandatory `pat:head` guard contradicts the pre-created, headless version row it is paired with | §19.1, §19.3, §14.2 | NO |
| B6 | Blocking | Append form (S1) never maintains `pat:head`/`pat:prevRev` | §10.1 | NO |
| B7 | Blocking | Weak ETags never satisfy `If-Match` under RFC 9110 | §15.4, §19.2, §19.4, §19.5, §24.4 | NO |
| B8 | Blocking | Timeout resolution maps "not yet visible" to `CONFLICT`, contradicting the `UNKNOWN` contract | §19.4, §25.1, §25.5 | YES |
| B9 | Blocking | Retention pruning can strand a live `pat:head` behind a `sh:class pat:Revision` shape | §24.2, Appendix B | YES |
| B10 | Blocking | Fencing tokens are checked but never advanced | §7.4, §16.2 | NO |
| B11 | Blocking | Global HLC pagination reopens the G2 reorder hole | §21.3, §25.7 | YES |
| B12 | Blocking | Sharding covers the meta graph only; txn/log/key graphs remain single hot statements | §17, §7.1, §10.1/§19.1 | NO |
| B13 | Blocking | "Sorted `WHERE` order" cannot control SPARQL lock/evaluation order | §10.1, §19.6 | NO |
| C1 | Cross-doc | Guide still cites superseded ADR-A51 as live authority in six places | L14, L474, L757, L834, L1761-1767, Appendix D.1; ADR-A51 header | NO |
| C2 | Cross-doc | `fnd:replacedBy` prescribed but not confirmed to exist in Foundation | §7.5, §23.3 | VERIFY |
| C3 | Cross-doc | Identifier widths not fixed (review text incomplete) | §13, §19.4 (`REV_WIDTH`), worked examples throughout | YES, pending review completion |

---

## Part A — Blocking defects (production-unsafe)

### B1. The epoch guard does not protect against restore

**Locations**

- §19.1 "The write" — the `WHERE` clause's dataset-restore protection is the version row's own `pat:epoch "3"^^xsd:long` triple (line 1702), never a dataset-level value.
- §19.4 "The client side" — `compare_and_set`: `nxt = Version(expected.epoch, expected.seq + 1)` (line 1799) and `params = {..., "epoch": expected.epoch, ...}` (line 1803). The epoch used in every write is whatever the caller's stale `Version` object says, never read from the store.
- §24.4 "Restore and migration runbook" — step 1, *"Bump `pat:epoch` on `<urn:ds:prod>`"* (line 2136), and step 2's claim *"Every open ETag is now stale by construction"* (line 2137). Nothing in §19.1/§19.4 ever compares against `<urn:ds:prod> pat:epoch`, so step 2's claim is false as the code stands.
- Cross-reference only, no separate fix: §2.3 (line 233) and §10.2 (line 989) both show `<urn:ds:prod> pat:epoch "3"^^xsd:long` as an inert record that nothing in the guide's own queries reads back.

**Problem.** After a restore, every version row still carries its pre-restore epoch value (because the version row is what was restored). A stale client holding an old ETag matches that unchanged row, succeeds against a different history, and mints a revision IRI that may already exist in exports, CDC sinks and `pat:prevRev` references taken before the restore — exactly the aliasing the epoch mechanism exists to prevent. A second hazard: if the epoch value itself is only ever bumped inside the dataset being restored, restoring twice from the same backup reuses the same "new" epoch both times.

**Change required**

Two independent parts. Part (a) is mechanical; part (b) is a design decision.

**(a) Add a dataset-level epoch guard to every write template — mechanical, Decision required: NO.**
Add a second guard clause to §19.1, §19.3, §10.1 and §24.1's `WHERE` blocks, comparing against the dataset node, alongside the existing version-row `pat:epoch` triple (which remains, as the per-target record of which epoch that row was last written under):

```sparql
GRAPH <urn:g:dataset> { <urn:ds:prod> pat:epoch "4"^^xsd:long }   # must equal the client's expected epoch
```

Correct §24.4 to state plainly that the write path reads and compares this triple on every write, closing the gap between the runbook's assumption and what the code actually does.

**(b) Decide how a new epoch value is allocated so that it survives a double restore — Decision required: YES.** This is the residual unsafety the review names even once (a) is fixed. Options, matching `iri-identity-patterns.md` §10.3's own classification of the same problem:

| Option | Mechanism | Consequences |
|---|---|---|
| **1. External high-water mark** | An external system outside the RDF store (a PostgreSQL row, an etcd key, the restore tooling's own state) tracks the highest epoch ever issued. Restore reads "current max + 1" from that system before writers are unblocked. | Fail-safe even under repeated restores from the same backup, because the counter is not part of what gets restored. Adds a small coordination dependency that must itself survive whatever caused the restore. This is the option the review names first. |
| **2. Restore-controlled epoch** | The restore runbook/tooling is the sole allocator: it reads the last known epoch from its own operational log (never from the dataset being restored) and writes the new epoch into the freshly restored dataset before any writer connects. | No new coordination service. Depends entirely on the runbook always running, and running first; a manual restore that skips the step reproduces the defect exactly. |
| **3. Writer-start refusal** | Every writer, on connecting, refuses to issue any write until it has confirmed the dataset's epoch exceeds a durable external watermark it can read. | Fail-safe like Option 1. Adds availability risk during recovery (writers block until the check passes) and duplicates part of Option 1's machinery. |
| **4. Store-local epoch only (current design)** | No external source; the epoch lives only inside `<urn:g:dataset>`. | Rejected. Unsafe under a double restore from the same backup, per the review and per the catalogue's own explicit classification of this pattern as unsafe. Recorded only so it is not silently re-proposed later. |

Options 1 and 3 are not mutually exclusive; Option 3 can be layered on Option 1 for defence in depth at the cost of availability during recovery. No recommendation is asserted as final here — this table exists so the human can pick one (or the 1+3 combination) with the consequences visible, per the review's own framing.

**Also update:** §24.4's runbook text (state the actual guard mechanism, not only "bump the epoch"); Appendix E if the epoch-source decision is deferred past this remediation pass (state it as an explicitly open item, not silently dropped).

---

### B2. Lost updates are invisible under the corrected design; the fork query cannot fire

**Locations**

- §15.3 "Making the store enforce the invariant: the SHACL trick" (lines 1361-1366) — narrative describing fork detection via `pat:NoForkShape`.
- Chapter 18, F5 (lines 1583-1596) — the standing fork-detection query `GROUP BY ?prev HAVING (COUNT(*) > 1)` and its "must always return zero rows" framing, plus the worked fork example.
- §19.2 "Then, always, the confirmation" (lines 1715-1725) — the confirming `ASK` shape.
- Chapter 27 §27.3, test **T-1** — assertion text "exactly one receipt; all others `412`; `pat:seq` advanced by exactly 1; **fork query returns zero rows**".
- Appendix A, `pat:prevRev`'s comment ("Two revisions sharing a prevRev is a fork") and Appendix B, `pat:RevisionShape`'s `pat:txn` property (line 2922, already `sh:minCount 1 ; sh:maxCount 1`) and `pat:NoForkShape` (lines ~2938-2947).

**Problem.** Revision IRIs are deterministic from `(aggregate, epoch, seq)`, which is required for restore-safety (F2/F3). Two writers who both win a broken-isolation CAS from the same prior version therefore mint the **same** revision subject, not two siblings sharing one `pat:prevRev`. Set semantics then collapse the evidence into one receipt carrying two `pat:txn` values and two txn claims pointing at it. `GROUP BY ?prev HAVING (COUNT(*) > 1)` never fires because there is only one `?r` for that `?prev`, so F5, `pat:NoForkShape` and T-1 all report a clean system while it is corrupt, and both racing clients' confirming `ASK` returns true.

**Change required — single valid option.**

- Rewrite the standing detection query (F5, and the query §15.3 refers to) from a `pat:prevRev`-grouping query to a `pat:txn`-multiplicity query:
  ```sparql
  SELECT ?rev (COUNT(DISTINCT ?t) AS ?n)
  WHERE { GRAPH <urn:g:txn> { ?t pat:rev ?rev } }
  GROUP BY ?rev HAVING (COUNT(DISTINCT ?t) > 1)
  ```
- Note explicitly, at the location of the rewritten query, that this is not a new SHACL obligation: `pat:RevisionShape`'s existing `pat:txn` property (Appendix B, line 2922: `sh:minCount 1 ; sh:maxCount 1`) already enforces this at commit time on validating stores. No shape addition is needed, only the narrative and the standing audit query.
- Strengthen the confirming `ASK` in §19.2 (and the `resolve()` function in §19.4) so a racing winner learns about corruption immediately, not only at the next audit cycle:
  ```sparql
  ASK { GRAPH <urn:g:txlog/…> { <rev> pat:txn "mine"
        FILTER NOT EXISTS { <rev> pat:txn ?o FILTER(?o != "mine") } } }
  ```
- Update T-1's assertion text in Chapter 27 to name the corrected query and to state the residual behaviour precisely: on stores without commit-time SHACL, the check is after-the-fact (satisfied only once the audit or the strengthened `ASK` observes the second `pat:txn`), not a preventive guarantee.
- Retain `pat:NoForkShape` (or clearly relabel it) as applicable only to a future non-deterministic revision-IRI scheme, since under the current deterministic scheme its own `pat:prevRev`-grouping query has the identical blind spot as the narrative fix above and should not be presented as still-effective without the same correction.

**Why this is not a two-option decision.** An alternative — minting revision IRIs with a non-deterministic disambiguator, so two colliding writers always produce distinct subjects and the original `pat:prevRev`-grouping query keeps working unmodified — was considered and rejected: it reintroduces exactly the restore-reuse risk (F2/F3, B1) that this guide's whole deterministic revision-IRI design exists to prevent. It is recorded here only so a future reader does not re-propose it without knowing why it fails. **Decision required: NO** — this is a correction of the existing design's own stated goals, not an open architectural choice.

**Also update:** Appendix A's `pat:prevRev` comment (add a note that a *same-subject* multiplicity of `pat:txn`, not a *shared-prevRev* multiplicity, is the operative fork signal under deterministic revision IRIs).

---

### B3. Revision IRIs collide between the stream form and the aggregate form

**Locations**

- §2.3 (line 257) — worked example, `pat:target <urn:g:orders/1>`.
- §10.1 (line 953: `BIND(<urn:stream:orders/1> AS ?stream)`) and §10.2's own worked receipt (around lines 989-1002, `pat:target <urn:stream:orders/1>`).
- Chapter 11, S6 (around line 1128) — also keys on `<urn:stream:orders/1>`.
- §19.1/§19.4 — CAS form keys the version row and payload graph on `<urn:g:orders/1>` (lines 1665-1666, 1678-1680); `rev_iri(aggregate, epoch, seq)` (line ~1791) is called with a bare string `"orders/1"`, so it derives `urn:rev:orders/1/e{epoch}/{seq}` regardless of whether the true target IRI was `urn:g:orders/1` or `urn:stream:orders/1`.

**Problem.** Two different version-row keying schemes (`urn:stream:orders/1` in the append-form chapters, `urn:g:orders/1` in the CAS-form chapters) both mint into the identical revision namespace `urn:rev:orders/1/e{epoch}/{seq}`, because `rev_iri()` derives its namespace from an ad hoc string a caller supplies out of band, not from the actual target IRI. This is F2 (revision IRI collision) reintroduced one layer up, and it means the guide's own two running examples of "the same domain object" (an order) are not, in fact, the same target IRI.

**Change required — two options, both requiring the same underlying fix.**

Regardless of which option is chosen, `rev_iri()` (§19.4) must derive its revision namespace from the actual target IRI (a URL-safe encoding or short hash of the full graph IRI), not from a bare string passed independently of it — this closes the derivation gap even after picking one canonical form, because two future differently-named targets that happen to share a trailing path segment would otherwise still collide.

| Option | Mechanism | Consequences |
|---|---|---|
| **1. Unify on one target IRI form (recommended)** | Rewrite §10.1's `BIND(<urn:stream:orders/1> AS ?stream)` to `BIND(<urn:g:orders/1> AS ?stream)`, and correct §10.2 and Chapter 11 §S6's examples to match. The aggregate/stream's own graph IRI becomes the single form used everywhere a version row, a receipt's `pat:target`, or an as-of query needs to name "the thing this write is about". | Removes the inconsistency with the least prose churn, since Chapter 19's CAS examples already use this form. Chapter 22's point that append and CAS are two contracts over the *same* mechanism, usable on the *same* target, becomes literally demonstrated by one shared worked example instead of two differently-named ones that were never actually the same target. |
| **2. Keep the two examples genuinely distinct** | Rename the illustrative append-only stream so it is not literally `orders/1` (for example `urn:g:orders/1/decisions`, a decision-event stream attached to, but distinct from, the `orders/1` aggregate). | Preserves Chapter 22's two separate worked examples as pedagogically distinct targets, matching a domain where an aggregate and one of its attached event streams really are different things. Requires more prose rework than Option 1, and Chapter 22's specific claim ("a stream can be appended to *and* compare-and-set... without two mechanisms") would then need a **new**, additional worked example to demonstrate the same target being written both ways, since the existing two would no longer be that target. |

**Decision required: YES** — this determines which of the guide's two running examples the rest of Part III and Part V's prose refers to, and Option 2 requires writing new material Option 1 does not.

---

### B4. `?n + 1` silently changes datatype from `xsd:long` to `xsd:integer`

**Locations**

- §7.1 "P3: materialise the write conflict" (line 606): `BIND(?n + 1 AS ?n1)`.
- §10.1 "The workhorse operation" (line 957): `BIND(?n + 1 AS ?n1)`.

**Problem.** Under SPARQL 1.1 §17.3 and XPath F&O `op:numeric-add`, addition on an `xsd:long`-typed operand returns `xsd:integer`, not `xsd:long`. Both counters end up typed `xsd:integer` despite the guide's own claim ("pinning `xsd:long` everywhere... keeps `?n + 1` from drifting"). On a SHACL-validating store this fails `VersionRowShape`'s `sh:datatype xsd:long` outright; on a non-validating store the next guard on `"n"^^xsd:long` stops term-matching and the stream silently wedges.

**Change required — single correct fix, no options. Decision required: NO.**

Cast explicitly at both locations:
```sparql
BIND(xsd:long(?n + 1) AS ?n1)
```

**Also update:** add a one-line pointer from Chapter 13's existing gotcha-table row (which already names this hazard in the abstract) to these two now-corrected locations, so a reader is not left to independently notice the guide's own queries used to be an instance of the exact hazard it warns against. Add a new TCK row (Chapter 27 §27.1) asserting the counter's term datatype is `xsd:long` after N increments (a "datatype round-trip" test).

---

### B5. The recommended pre-created version row makes the first CAS impossible

**Locations**

- §19.1 "The write", `WHERE` clause (line 1704): `pat:head ?prevRev .` — a mandatory, non-`OPTIONAL` triple.
- §19.3 "The create path" (line 1747): recommends pre-creating the version row with `pat:seq "0"`, **no head**, "so that the CAS shape above is the only shape ever used".
- §14.2 "Variants" (create-if-absent guidance): recommends pre-creating the meta row with `pat:seq "0"` at aggregate-id allocation time.

**Problem.** With no head present on a freshly pre-created row, §19.1's mandatory `pat:head ?prevRev` triple matches nothing, so every first write against a pre-created row returns `412` — directly contradicting §19.3's claim that this makes "the CAS shape above the only shape ever used".

**Change required — single correct fix, no options. Decision required: NO.**

Wrap the `pat:head` triple in `OPTIONAL` in §19.1's `WHERE` clause:
```sparql
OPTIONAL { GRAPH <urn:g:meta/17> { <urn:g:orders/1> pat:head ?prevRev } }
```
An unbound `?prevRev` then drops harmlessly from both the `DELETE` clause's `pat:head ?prevRev` removal and the receipt's `pat:prevRev ?prevRev` insertion (SPARQL templates silently omit triples with an unbound term; no special-casing is required). Confirm this does not reopen F7's "unconstrained guard" hazard: `pat:seq` and `pat:epoch` remain mandatory, non-`OPTIONAL` triples in the same `WHERE` group, so guard cardinality stays functional; only `pat:head` becomes optional.

---

### B6. The append form does not maintain the head or the chain

**Location:** §10.1 "The workhorse operation" (lines 917-983), the `DELETE`/`INSERT`/`WHERE` block.

**Problem.** S1 increments `pat:seq` but never reads, deletes, or re-inserts `pat:head`, and never writes `pat:prevRev` on the receipt — yet §10.2's own worked example of this chapter's output shows a receipt with `pat:prevRev` populated. On a stream written by both the append form and the CAS form, the CAS form ends up reading a stale head, the receipt chain has holes, and T-4 ("single unbroken path") fails.

**Change required — single correct fix, no options. Decision required: NO.**

- Add `OPTIONAL { GRAPH <urn:g:meta/17> { ?stream pat:head ?prev } }` to the `WHERE` clause.
- Add `?stream pat:head ?rev` to the `DELETE` clause (paired with the existing `?stream pat:seq ?n`) and to the `INSERT` clause (paired with the existing `?stream pat:seq ?n1`), mirroring how §19.1's CAS form already handles `pat:head`.
- Add `pat:prevRev ?prev` to the receipt's `INSERT` block, matching the shape already shown (but not produced) by §10.2's worked example.

---

### B7. Weak ETags never satisfy `If-Match`

**Locations**

- §15.4 "HTTP-level CAS" (lines 1372, 1374, 1379, 1384, 1389): `ETag: W/"3-41"`, `If-Match: W/"3-41"`, `ETag: W/"3-42"`.
- §19.2 (line 1722), §19.4 (`Version.etag` property: `return f'W/"{self.epoch}-{self.seq}"'`), §19.5's HTTP mapping table (lines 1834-1835).
- §24.4 (line 2137): "every open ETag is now stale by construction (`W/"3-42"` cannot match epoch 4)".

**Problem.** RFC 9110 §13.1.1 requires `If-Match` to use strong comparison, and a weak validator (`W/"..."`) never matches under strong comparison. With every ETag in the guide marked weak, a compliant server or intermediary returns `412` on **every** conditional `PUT`, regardless of whether the precondition actually holds. The entire HTTP-level CAS mapping in §15.4/§19.5 is non-functional as written.

**Change required — single correct fix, no options. Decision required: NO.**

Drop the weak indicator throughout: use `"3-41"`, `"3-42"`, and so on as strong validators everywhere the guide currently prints `W/"..."`. Add one clarifying sentence at §15.4's first occurrence noting that RFC 9110 §13.1.1 mandates strong comparison for `If-Match`, and that this guide's HTTP mapping only ever uses `If-Match` (never `If-None-Match` on `GET`), so a weak validator has no legitimate use in this mapping at all. Keeping a future, unrelated weak-validator use case for `GET`-side caching is out of scope for this remediation and is not requested by the review; do not add it.

---

### B8. Outcome resolution after a timeout is wrong

**Locations**

- §19.4 (lines ~1806-1820): `compare_and_set`'s `except TimeoutError:` block (line 1814) calls `resolve(store, txn_id, ...)`, and `resolve()` itself (line 1818-1820) unconditionally maps `ASK == false` to `Outcome.CONFLICT`.
- §25.1 "The port": states `resolve(txnId)` is mandatory and "Nothing may return `Unknown` without a working `resolve`."
- §25.5 "Composition: decorators and retry rules", rule 3: "`Unknown` ⇒ `resolve()` first. Never retry an `Unknown` directly."

**Problem.** A `false` answer from `resolve()` immediately after a timeout can simply mean the original request is still executing, not that it failed. Mapping this unconditionally to `CONFLICT` causes duplicate events on retry (append form) or tells a caller "re-decide" while the original write may still land (CAS form). `Outcome.UNKNOWN` is defined in the enum but never returned by `resolve()`, contradicting both the Java port's contract (§25.1) and the retry rule (§25.5) that assume it can be.

**Change required — two options, both requiring the same base correction first.**

**Base correction (applies to both options, Decision required: NO):** `resolve()`'s `False` branch must be distinguished by *why* it was called. The ordinary, non-timeout path through `compare_and_set` (where the request definitely completed and the store returned a normal response) can safely continue to map a normal guard failure to `CONFLICT`, because that boolean is definitive. Only the *timeout-path* call to `resolve()` is ambiguous, and only that path needs the fix below.

| Option | Mechanism | Consequences |
|---|---|---|
| **1. Re-submit the identical request** | On timeout, retry the *same* `store.update(CAS_TEMPLATE, params)` call under the *same* `txn_id`. The update's own `FILTER NOT EXISTS` idempotency guard (already present) makes this safe: if the original applied, the resend is a no-op guard failure and falls through to `resolve()` for the true answer; if it did not apply, the resend has a normal chance to apply. | Return type stays `(Outcome, str \| None)` with only `APPLIED`/`CONFLICT` ever surfaced to callers who do not want to handle `UNKNOWN`. Only correct if retries are bounded; under a sustained partition this can retry indefinitely unless given its own timeout budget. |
| **2. Return `Outcome.UNKNOWN`** | On timeout, call `resolve()` once; if it returns `false`, that means only "not observed yet". Return `Outcome.UNKNOWN` (never `CONFLICT`) and require the caller to invoke `resolve()` again later, per the existing §25.1/§25.5 contract. | Matches the Java port's contract exactly (`CasResult.Unknown`, mandatory `resolve(txnId)`) with no change needed elsewhere in the guide. Pushes the "when do we finally decide it's a conflict" decision to the caller/adapter layer, which must poll `resolve()` on its own schedule. |

**Decision required: YES.** Option 2 requires no other changes to the guide (it is already the documented contract in §25.1/§25.5/§25.7) and is offered as the lower-friction default; Option 1 is presented because the review names it as an equally valid alternative with a different operational shape (bounded retry budget vs. caller-driven polling).

---

### B9. Retention pruning breaks every quiet aggregate on SHACL-validating stores

**Locations**

- §24.2 "Retention and pruning" table (lines 2107-2119). The Receipts row already protects the *middle* of a chain ("never delete individual receipts, which would break the `pat:prevRev` chain in the middle") but nothing protects a stream's **head** receipt when its containing monthly bucket ages out and the aggregate has not been written since.
- Appendix B, `pat:RevisionShape` (line 2921): `sh:property [ sh:path pat:prevRev ; sh:maxCount 1 ; sh:nodeKind sh:IRI ; sh:class pat:Revision ]`.

**Problem.** An aggregate untouched for longer than the receipt retention window has a `pat:head` pointing into a bucket retention has already dropped. The next write's new receipt has a `pat:prevRev` targeting an IRI with no retained `pat:Revision` typing triple, which fails `sh:class pat:Revision` outright on any commit-time-validating store — every write to an old, quiet aggregate is rejected.

**Change required — two options.**

| Option | Mechanism | Consequences |
|---|---|---|
| **1. Retention never prunes a live head (recommended)** | Before dropping a monthly bucket, retention scans `pat:head` values across meta shards and refuses to drop a bucket that still contains a receipt referenced as a head. That bucket is retained until the aggregate is next written (moving its head to a newer bucket) or explicitly archived through a separate cold-storage path. | Bounded cost: one receipt per quiet aggregate stays alive indefinitely, not the whole bucket. Requires a small index ("heads still in bucket X") that retention jobs do not currently maintain. Preserves the existing SHACL guarantee (an unpruned `pat:prevRev` always resolves to a real, typed `pat:Revision`) unchanged. |
| **2. Weaken the shape, add an explicit low-water-mark check** | Drop `sh:class pat:Revision` from `pat:prevRev`'s property shape (Appendix B, line 2921). Document that a `pat:prevRev` may point at an IRI with no retained triples, and that a reader must treat "no type, but `(epoch, seq)` recoverable from the IRI is below the recorded retention low-water mark" as expected pruning rather than corruption. | No change to retention's existing whole-bucket-drop mechanism. Weakens the SHACL contract's own guarantee: a genuinely dangling/corrupt `pat:prevRev` and an expected, pruned one become indistinguishable to the shape alone, and distinguishing them requires the same kind of low-water-mark check the guide already uses for the S3 gap-scan's own blind spot, applied one level lower (per-receipt, not per-bucket). |

**Decision required: YES.** Option 1 preserves the current shape's guarantee at the cost of a new bookkeeping index; Option 2 keeps retention unchanged at the cost of weakening what the shape can promise.

---

### B10. Fencing tokens are checked but never advanced

**Locations**

- §7.4 "P6: external allocator or lock" (line 726): `FILTER(?current < 7183)` — a `WHERE`-clause fragment with no accompanying `DELETE`/`INSERT` of the fence value shown at all.
- §16.2 "External lock with fencing tokens" (lines 1423-1431): `GRAPH <urn:g:meta/17> { <urn:g:orders/1> pat:seq "41"^^xsd:long ; pat:fence "7183"^^xsd:long . }` and the guard `FILTER(?f < 7184)` (line 1431) — again, no update of the stored fence value is shown.

**Problem.** Both locations check a fencing token against a stale threshold but never advance it. This has two effects: a stale holder whose token is anything above the *stored* value still passes (no fencing actually occurs), and the legitimate current holder's *second* write with the *same* token fails, because the comparison is strict (`<`, not `<=`).

**Change required — single correct fix, no options. Decision required: NO.**

At both locations, guard with `?f <= mytoken` (not strict `<`), and in the same update, `DELETE` the old `pat:fence` value and `INSERT` the new one, exactly as every other version-row field in this guide is maintained (read-old, delete, insert-new, in one operation).

---

### B11. Global HLC pagination reintroduces the G2 reorder hole

**Locations**

- §21.3 "The pragmatic default" (lines 1953-1966): the global consumer query, `FILTER(?hlc > "1758445702450:0001:n7") ... ORDER BY ?hlc LIMIT 500`, with no upper bound.
- §25.7 "The write path and the reader path": defines `watermarks.stable()` and `PRE_COMMIT` semantics, which §21.3 does not apply.

**Problem.** The client stamps the HLC before commit, so `FILTER(?hlc > last) ORDER BY ?hlc` can permanently skip a receipt with a lower HLC that commits *after* a higher one has already been read and paged past. Per-target contiguity (S3) only detects the loss after the fact, once the consumer has already advanced past it.

**Change required — two options, combinable.**

| Option | Mechanism | Consequences |
|---|---|---|
| **1. Cap reads at the stable watermark** | Add an upper bound derived from `watermarks.stable()` (already defined in §25.7 for `PRE_COMMIT` backends) to §21.3's query, so a consumer never reads past the point below which no earlier-stamped commit can still land. | Closes the gap safely. Adds latency for the freshest events, proportional to however the watermark itself lags. Only available on backends with a watermark source; §21.3 must state what a consumer does on backends without one (falls back to Option 2). |
| **2. Mandatory S3 reconciliation** | Treat the global HLC feed as best-effort; require every consumer to also run the existing per-target `pat:seq` contiguity check (S3) on a schedule, and rewind its cursor to re-fetch any target found to have a gap. | Works on any backend, no watermark source required. Only safe if S3 monitoring is mandatory for every consumer and the rewind-and-refetch remediation is actually implemented — a heavier operational requirement than a single upper-bound filter. |

**Decision required: YES.** The two are not mutually exclusive (Option 1 wherever a watermark source exists, Option 2 as a universal backstop), but §21.3 currently states neither, and presenting the unguarded query as "the pragmatic default" needs correcting regardless of which combination is chosen.

---

### B12. Contention is sharded for the meta graph only

**Locations**

- §17 "What separating metadata from payload buys" (lines 1502-1512), the F12 sharding note.
- §7.1 "P3: materialise the write conflict" (lines 590-618): a single, unsharded `urn:g:keys` graph holds every P3 sentinel counter.
- §10.1/§19.1: every write also inserts into the single graphs `urn:g:txn` and `urn:g:txlog/2026-09`, regardless of aggregate.

**Problem.** F12 and T-3 shard the version-row (meta) graph, but every write also touches the single txn-claim graph and the single monthly log-bucket graph. On an engine with graph- or page-granular conflict detection, every write in the dataset conflicts on these two graphs regardless of meta-shard tuning, so A6 (no contention between unrelated aggregates) is lost anyway.

**Change required — single correct fix, no options. Decision required: NO.**

Extend the sharding declaration to cover the txn-claim graph, the log-bucket graph(s), and the P3 key-shard graph, the same way it already covers the meta graph. Extend T-3 (Chapter 27) to measure cross-aggregate false-conflict contention on all four graph kinds, not only the meta shard. The shard-count value itself remains an operational tuning parameter, exactly as the meta-shard count already is (Appendix E already notes "64 meta shards and 1024 key shards are starting points... decide the real numbers" per-engine) — this is not a new kind of decision, only an extension of an already-adopted one to graphs it was silently assumed not to apply to.

---

### B13. Lock ordering cannot be controlled through the order of `WHERE` patterns

**Locations**

- §10.1 (line 982): "Acquire multiple counters in sorted order if one commit touches several streams..."
- §19.6 "Multi-aggregate writes" (line 1844): "Acquire (that is, list in the `WHERE` clause and rewrite) the version rows in sorted IRI order, always."

**Problem.** SPARQL gives no control over pattern evaluation order or lock acquisition order; a query optimiser is free to reorder `WHERE` patterns freely. Listing patterns in a particular textual order does not achieve the deadlock avoidance both passages claim it does.

**Change required — single correct fix (documenting two existing, valid mitigations, not a new choice). Decision required: NO.**

Rewrite both passages to state plainly that deadlock avoidance in a true multi-statement-lock engine depends on one of:
- (a) the engine's own deadlock detection plus the bounded, jittered retry policy already documented elsewhere in the guide for ordinary conflicts, or
- (b) an external ordering mechanism — a lock service the client explicitly acquires in sorted order before issuing the SPARQL request, or a partitioned single-writer-per-key design (S8) that removes the possibility of two commits racing on the same pair of aggregates at all.

Add a new TCK test (Chapter 27 §27.3) exercising two commits touching the same two streams in opposite orders, asserting the system either serialises them without deadlock or surfaces a bounded, retryable conflict, never a hang.

---

## Part B — Cross-document inconsistencies

### C1. The guide still treats superseded ADR-A51 as authoritative

**Locations and required repoints**

| Line(s) | Current text (abridged) | Repoint to |
|---|---|---|
| 14 | Status line cites `ADR-A51-review-disposition.md` for identity corrections | `docs/architecture/iri-identity-patterns.md` and ADR-A82 as the current identity guidance; keep the historical corrections summary but do not present A51 as live |
| 474 | "matches ADR-A51's minimum content-hash width" | "matches `iri-identity-patterns.md` §7.4's minimum digest width" |
| 757 | "a plain, revocable pointer (ADR-A51)" | "a plain, revocable pointer (`iri-identity-patterns.md` §11.4)" |
| 834 | "This is what ADR-A51 names `surrogate-claimed`..." | "This is what `iri-identity-patterns.md` §6.4 names `surrogate-claimed`..." |
| 1761, 1765, 1767 | "Note on ULID here versus ADR-A51..." comment block | Cite `iri-identity-patterns.md` §6.3 (random surrogate pattern) and §10.6 (runtime occurrence identifiers) instead, preserving the same substantive point (ULID is acceptable for ephemeral txn ids, not for entity surrogates) |
| 3043-3057 | Appendix D.1 heading and table cite the ADR-A51 review as the operative authority | Keep as a historical record of the specific 2026-09-23 corrections (do not delete history); add one line at the top of D.1 noting ADR-A51 was later superseded by ADR-A82 and that current guidance lives in `iri-identity-patterns.md` |

**Also required (secondary target document):** `ADR-A51-iri-and-identity-policy.md`'s header currently reads "Superseded by ADR-A82" while ADR-A82 itself is still `Proposed`. Reword to "to be superseded on ratification of ADR-A82" (or record both as `Proposed` consistently), so the header does not assert a supersession that has not formally happened yet.

**Decision required: NO** — mechanical repointing to an already-published, current document.

### C2. `fnd:replacedBy` is used but not defined

**Locations**

- §7.5 "P7: detect and reconcile" (line 757): prescribes `fnd:replacedBy` as the merge relation.
- §23.3 "Aligning `pat:` with Foundation": the guide's own alignment table does not list `fnd:replacedBy` among the Foundation terms it cross-references.

**Change required — Decision required: VERIFY, then mechanical.**

This depends on a short factual check outside this plan's scope: whether `fnd:replacedBy` is actually declared in `ontology/foundation/`. Two possible outcomes:

- **If it exists:** add it to §23.3's alignment table, closing the gap the guide's own cross-reference discipline should have caught.
- **If it does not exist:** rewrite §7.5's prescription to "a merge relation declared per profile (never `owl:sameAs`; see `iri-identity-patterns.md` §11.3-§11.4)" rather than asserting a specific Foundation term as if it were already guaranteed to exist.

This check is recorded as an open item in Part F below rather than resolved here, since it requires reading `ontology/foundation/` rather than the reviewed documents.

### C3. Identifier widths are not fixed — review text incomplete

The governing review's own text ends mid-sentence: *"Catalogue §7.4 and §10.2 both reject variable widths. The guide has"* — no continuation, no named location, no stated fix. This plan does not complete that sentence on the review's behalf. What follows is an independent cross-check, offered as the most likely subject of the unfinished finding, not as a substitute for it.

**Independently verifiable inconsistency matching the catalogue's rule.**

- `iri-identity-patterns.md` §10.2 ("Fixed-width positions") states: for signed 64-bit sequences, 19 decimal digits is sufficient, and "a documentation-only distinction such as '16 for examples, 19 in production' is not valid for identity-bearing strings."
- The guide's own Chapter 13 gotcha table states, in its own words: *"zero-pad to a fixed width wide enough for the datatype (19 digits for int64; this guide uses 16 in examples for legibility)"* — precisely the pattern the catalogue rejects.
- §19.4 defines `REV_WIDTH = 16   # zero-padding width for revision IRIs (19 for full int64 in production)` (line 1768), and every worked revision-IRI example throughout the guide (Chapters 2, 10, 14, 18, 19, 20, 24) is zero-padded to 16 digits under this constant.

**Change required, pending confirmation — two options.**

| Option | Mechanism | Consequences |
|---|---|---|
| **1. Adopt 19 digits everywhere** | Set `REV_WIDTH = 19` and regenerate every worked example's zero-padded digit count throughout the guide. Remove the "(19 in production)" caveat from Chapter 13's table and from §19.4. | Matches full `xsd:long` range without ambiguity. Every worked example in the guide needs its digit count corrected, a large mechanical edit across many chapters. |
| **2. Fix 16 digits as the platform's committed width** | Keep 16 digits, but state it as the single, permanent, enforced width (not "for legibility"), with an explicit, justified range bound (16 decimal digits covers sequences up to 10^16 − 1, which must be shown to be sufficient for every declared use, including the dataset-wide sparse tiers) recorded alongside the constant. Remove the "(19 in production)" caveat entirely. | Smaller mechanical edit (no example regeneration needed). Requires a justification that 16 digits is provably sufficient for every profile this guide permits, which has not been demonstrated anywhere in the current text. |

**Decision required: YES**, and this decision should not be finalized until the review's own C3 finding is completed by its author, since the review may have identified a specific instance, consequence, or constraint this independent cross-check has not. This item is recorded in Part F as requiring both a human decision and a completed source review before implementation.

---

## Part C — Consolidated per-chapter location index

For an implementer working chapter by chapter rather than finding by finding. Every chapter or appendix touched by at least one finding above, in document order.

| Location | Findings that touch it |
|---|---|
| Header status line (L14) | C1 |
| Chapter 2 §2.3 (worked example, L217-263) | B3 (cross-reference only) |
| Chapter 6 §6.1 (`claim_iri` docstring, L459-480) | C1 (L474) |
| Chapter 7 §7.1 P3 (L584-618) | B4 (L606), B12 (unsharded `urn:g:keys`) |
| Chapter 7 §7.4 P6 (L694-733) | B10 (L726), C1 (fencing note is unrelated to A51, no change here) |
| Chapter 7 §7.5 P7 (L734-758) | C1 (L757), C2 (L757) |
| Chapter 8 §8.4 (L823-845) | C1 (L834) |
| Chapter 10 §10.1 (L917-983) | B3 (L953), B4 (L957), B6 (whole block), B12, B13 (L982) |
| Chapter 10 §10.2 (L985-1023) | B3, B6 (worked example inconsistency) |
| Chapter 11 §S6 (L~1128) | B3 |
| Chapter 13 (gotcha table, L1228-1257) | B4 (cross-reference), C3 (width row) |
| Chapter 14 §14.2 (L1291-1316) | B5 |
| Chapter 15 §15.3 (L1361-1366) | B2 |
| Chapter 15 §15.4 (L1367-1409) | B7 |
| Chapter 16 §16.2 (L1418-1437) | B10 |
| Chapter 17 (L1475-1512) | B12 |
| Chapter 18, F2 (L1554-1567), F5 (L1583-1596) | B2 |
| Chapter 19 §19.1 (L1654-1714) | B1 (L1702), B5 (L1704), B7 |
| Chapter 19 §19.2 (L1715-1725) | B2, B7 |
| Chapter 19 §19.3 (L1727-1748) | B5 |
| Chapter 19 §19.4 (L1749-1829) | B1 (L1799, L1803), B3 (`rev_iri`), B7, B8 (L1806-1820), C1 (L1761-1767), C3 (`REV_WIDTH`, L1768) |
| Chapter 19 §19.5 (L1830-1841) | B7 |
| Chapter 19 §19.6 (L1842-1845) | B13 |
| Chapter 21 §21.3 (L1953-1966) | B11 |
| Chapter 24 §24.2 (L2107-2119) | B9 |
| Chapter 24 §24.4 (L2132-2148) | B1, B7 |
| Chapter 25 §25.1 | B8 |
| Chapter 25 §25.5 | B8 |
| Chapter 25 §25.7 | B11 |
| Chapter 27 §27.3, T-1 | B2 |
| Chapter 27 (new rows) | B4, B13 |
| Appendix A | B2 (`pat:prevRev` comment) |
| Appendix B, `pat:RevisionShape` (L2921-2922) | B2 (no change needed, cross-reference only), B9 |
| Appendix B, `pat:NoForkShape` | B2 |
| Appendix D.1 (L3043-3057) | C1 |
| ADR-A51 header (secondary document) | C1 |

---

## Part D — Sequencing and dependencies between fixes

These fixes are not independent edits; several touch the same SPARQL block for different reasons and should land together in one pass, in this order, to avoid re-editing the same lines twice:

1. **§19.1 pass (single edit, addresses B1, B5, B7 together):** add the dataset-epoch guard (B1a), make `pat:head` `OPTIONAL` (B5), and drop the weak-ETag marker from every example in the surrounding prose (B7). All three touch the same `WHERE` clause and its immediately surrounding narrative.
2. **§10.1 pass (single edit, addresses B3, B4, B6, B12, B13 together):** decide B3's target-IRI option first (it determines whether this whole example is rewritten to `urn:g:orders/1` or renamed), then apply B4's datatype cast, B6's head/prevRev maintenance, and B12's graph-sharding note in the same revision of the block, since B6's fix touches the same DELETE/INSERT/WHERE structure B3 and B4 also touch.
3. **§19.4 pass (single edit, addresses B1, B3, B7, B8, C1, C3 together):** this one function block (`compare_and_set`/`resolve`/`rev_iri`/`Version`) is the single most-touched location in the guide. B1's epoch-source decision, B3's `rev_iri` derivation fix, B7's ETag string format, B8's timeout-handling option, C1's comment repoint, and C3's `REV_WIDTH` decision all land in this one code sample. Resolve the three YES-decisions (B1b, B3, B8) before touching this block, so it is edited once with the final answers, not iteratively.
4. **Chapter 18/27 pass (addresses B2):** rewrite F5's query and narrative, then T-1's assertion text, in the same pass, since T-1 quotes F5's mechanism by name.
5. **Chapter 21/25 pass (addresses B11):** requires B1's epoch-source decision to be settled first only if the chosen watermark mechanism is coupled to epoch state; otherwise independent.
6. **Appendix B pass (addresses B9):** requires B9's option choice (shape-preserving vs. shape-weakening) before editing, since the two options produce different shape text.
7. **C1's six repoints** can be done at any time, independently of the above, since they are citation fixes only.
8. **C2** requires the `ontology/foundation/` verification (Part F) before its one-line edit.
9. **C3** is blocked on the review's own completion (Part F) before any width change is made, per the instruction not to guess the review's intended fix.

---

## Part E — Downstream artefacts affected once implementation starts

Recorded here so the eventual implementation slice(s) do not discover these late. Not performed by this plan.

- **Appendix A (pattern vocabulary):** `pat:prevRev`'s comment needs the B2 fork-signal correction (§B2 above).
- **Appendix B (SHACL shapes):** possible edit to `pat:RevisionShape`'s `pat:prevRev` property (B9, Option 2 only) or a new low-water-mark-aware validation note (B9, Option 1).
- **Appendix D (traceability):** a new D.2 entry (or an addition to D.1) recording this remediation pass's own corrections, following the same table format D.1 already uses, once implemented.
- **Appendix E (what remains open):** B1's epoch-source decision and B9's retention-option decision, if not resolved before implementation, must be added here as explicitly open rather than silently absent.
- **Chapter 27 (TCK):** new rows for B4 (datatype round-trip), B13 (opposite-order two-stream deadlock/serialisation probe), and a rewrite of T-1's assertion text (B2).
- **Per copilot-instructions' mandatory slice shape**, once this plan is executed: the resulting slice(s) need a Validation Pack at `docs/developer/validation/<slice-id>.md` (test cases against the corrected SPARQL, including at least one adversarial/mutation case per Blocking finding, per the human validation gate's "adversarial probe" step), a traceability update in `docs/developer/INDEX.md`, and the doc delta is this remediation itself (the guide is the normative document; there is no separate "doc update" step because the fix *is* the document).

---

## Part F — Open items requiring human confirmation before implementation

Every item below must be resolved (or explicitly deferred with a recorded reason) before an implementation slice starts, because each has more than one architecturally valid answer or depends on information outside this plan:

1. **B1(b)** — which epoch-allocation source (external high-water mark, restore-controlled, writer-refusal, or a combination) is acceptable given the deployment's tolerance for a new coordination dependency versus availability risk during recovery.
2. **B3** — unify the two running examples onto one target IRI (Option 1) or keep them deliberately distinct with a new supporting example for Chapter 22's claim (Option 2).
3. **B8** — bounded-retry resubmission versus `UNKNOWN`-and-poll for the timeout-path outcome.
4. **B9** — preserve `pat:RevisionShape`'s `sh:class pat:Revision` guarantee at the cost of a new retention index (Option 1), or weaken the shape and rely on a low-water-mark convention (Option 2).
5. **B11** — adopt the stable-watermark cap, the mandatory-S3-reconciliation backstop, or both, for global HLC pagination.
6. **C2** — confirm whether `fnd:replacedBy` exists in `ontology/foundation/`; the answer determines whether this is a cross-reference addition or a rewording away from a specific Foundation term.
7. **C3** — obtain the completed text of the governing review's finding C3 from its author before finalizing a width decision; in the meantime, the independent cross-check in this plan (§C3 above) identifies the most likely subject (`REV_WIDTH` and the "16 for legibility / 19 in production" split) without asserting it is the whole of what the review intended to say.

No implementation slice should proceed past the point of touching §19.1, §19.4, §21.3, §24.2, or Appendix B until the corresponding item(s) above are resolved, per the sequencing notes in Part D.
