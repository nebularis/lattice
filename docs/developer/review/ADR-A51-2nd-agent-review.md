<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Disposition: ADR-A51 Review Verification and Soundness Assessment By 2nd Autonomous Agent

**Review:** [ADR-A51-review.md](ADR-A51-review.md)
**Reviewed artefacts:** [ADR-A51](../../architecture/decisions/ADR-A51-iri-and-identity-policy.md), [iri-policy.md](../../architecture/iri-policy.md), [rdf-sparql-patterns-guide.md](../../architecture/rdf-sparql-patterns-guide.md)
**Date:** 2026-09-23
**Disposed by:** 2nd Agent, autonomous session. Pending human ratification alongside ADR-A51 itself — see [phase-0-status.md](../status/phase-0-status.md).


## 1. Verdict

The rewrite is a real improvement. The high-level structure is now right:

- content identity and event identity are separate;
- the environment is removed from identity;
- `surrogate-claimed` is the default for mutable or sensitive keys;
- `pat:current` is a pointer, not a graph alias;
- the guide's receipt IRIs now carry the epoch.

However, the review has not been applied as thoroughly as the disposition claims. Specifically:

- **One Critical finding (F-1) has partially regressed** through `{scope}` and the worked examples.
- **Several findings marked "Accepted/Resolved" are not actually implemented.** These are F-12, F-16 and parts of F-5, F-10, F-14 and §5.
- **The disposition misstates what the review asked for** in at least three places.
- **The two normative documents still disagree** on bytes that matter: hash inputs and padding width.

I would not ratify in the current state. Most fixes are editorial, but four are design decisions: `{base}`/`{scope}`, literal canonicalisation, skolem derivation, and epoch durability.

---

## 2. Finding-by-finding verification

| Finding | Disposition says | Actual status |
|---|---|---|
| F-1 environment in identity | Resolved | ⚠ **Partially regressed** (§2.1) |
| F-2 hash width, verification | Resolved | ✅ Mostly. Hash function unnamed; "at least 128" is ambiguous (§2.5) |
| F-3 lineage allocation / owner | Resolved | ◑ Partial. The owner question and the `projectId`→`{scope}` mapping are unanswered |
| F-4 Rule 2 scoping | Resolved | ◑ Partial. Claim-IRI `v1` salts and ULID `urn:txn:` IDs are not in the exception list |
| F-5 ULID timestamps | Resolved | ⚠ **Example still invalid** (§2.2) |
| F-6 `derived-hash` and PII | Resolved | ◑ Partial. Rotation guidance is misapplied (§2.6) |
| F-7 `surrogate-claimed` | Resolved | ✅ |
| F-8 key mutability / merges | Resolved | ◑ `fnd:replacedBy` may not exist; reference rewriting conflicts with content addressing (§4) |
| F-9 content vs event | Resolved | ✅ Structure is right. Padding is inconsistent and `fnd:supersededBy` is unconstrained (§2.4) |
| F-10 `{class}` → `{ns}` | Resolved | ⚠ **Examples still embed class names** (§2.3) |
| F-11 alias mechanism | Resolved | ◑ Reader semantics during promotion are not stated; `pat:` is an illustrative namespace |
| F-12 grammar / escaping | Resolved | ❌ **Not done** (§2.5) |
| F-13 URN hygiene, `@base` | Resolved / deferred | ✅ for `@base` and case. The `owl:imports` catalog is not addressed |
| F-14 content hash spec | Resolved | ◑ Literal canonicalisation creates a new integrity bug (§4.1) |
| F-15 tenant | Resolved | ✅ The reserved tenant is not named |
| F-16 skolemization | Resolved | ❌ **Self-contradictory, no IRI form** (§2.7) |
| F-17 risk wording | Accepted | Reasonable to drop, but it is "not carried forward", not "accepted" |

### 2.1 F-1 has leaked back in through `{scope}` and `{base}`

**`{scope}` can be an environment.** iri-policy §2 says `{scope}` "is a project **or environment** id per ADR-A63". A lineage IRI containing an environment id is exactly what ADR Rule 3 forbids.

**Cloning still re-mints.** The accompanying text says cloning creates "new lineages under it". Content copied into new lineages must have every internal reference to the old lineage rewritten. That changes its content hash, which is precisely the F-1 failure mode, just relocated.

**The entity examples put the environment in the base.** Every entity example in iri-policy §4 uses `urn:lattice:t7f3a2:prod/...`, with **`prod`** in the base.

**`{base}` is never defined** in either document. This is now the most important gap in the ADR, because it determines three things:

- whether entity identity is per tenant, per project or (as the examples imply) per environment;
- whether the same real-world entity referenced from two projects gets two IRIs;
- whether Rule 3 holds at all.

**Fix:**
- Define `{base}` explicitly (probably `urn:lattice:{tenantId}`, or `urn:lattice:{tenantId}:{scope}` with `{scope}` restricted to a project).
- State that `{scope}` is never an environment.
- Replace `prod` in all examples.

### 2.2 F-5: the "corrected" surrogate example is not a UUID

The disposition says the iri-policy §4 example was "corrected to a UUIDv4 form". The unclaimed `surrogate` row still reads:

`01j9z8q3-k4m5-n6p7-q8r9-s0t1u2v3w4x5`

This contains non-hex characters (`j z q k m n p r s t u v w x`) and has no version-4 nibble. It looks like a hyphenated ULID. The parenthetical beside it ("rendered as a UUIDv4, not a ULID") is false.

The `surrogate-claimed` example (`2b6f9e34-9a41-4d7a-8b2e-3f6c1a9d7e40`) is valid. Examples get copied into tests and fixtures, so this matters.

### 2.3 F-10: the examples reintroduce class-in-IRI and violate lowercase

The iri-policy §4 examples use `party/Policy/…`, `party/Claimant/…`, `eligibility/Claimant/…` and `eligibility/ExtractionCandidate/…`. These cause four problems:

- **They reintroduce class names.** These are capitalised OWL class names, the exact pattern F-10 removed. It is also ambiguous whether `{ns}` is `party` or `party/Policy`.
- **They break the lowercase rule.** Rule 7 says "the canonical lexical form is all-lowercase". `Policy` and `POL-000123` violate it.
- **The validator won't catch it.** iri-policy §7 only rejects mixed case in the *scheme/NID*, so it would pass these.
- **One example models the very misuse the ADR warns against.** `derived-hash` is demonstrated on `Claimant`, a person. Claimant keys are almost certainly personal data, so this is the case the ADR says `derived-hash` must never be used for.

**Decide whether "all-lowercase" applies to the whole IRI or only to scheme/NID and hex.** If it applies to the whole IRI, you also need a rule for case-significant natural keys: lowercasing may merge keys that the source system treats as distinct.

### 2.4 F-9 / §5: padding width is inconsistent, and the disposition dismisses it

**The review said the padding width must be fixed.** Its words were: "Identity-bearing padding must be fixed in the grammar, because changing it later re-mints every IRI."

**The disposition dismisses this.** It says the 16-vs-19 inconsistency "was not the defect" and leaves it.

**The current state is self-contradictory.** iri-policy §2 mandates **19 digits**, but its own event example (`…/evt/e3/0000000000000042`) is **16** digits. The guide uses `REV_WIDTH = 16` "(19 in production)".

Pick one width, put it in the grammar, make every example conform, and have the validator enforce it.

**Two further F-9 gaps:**

- **Nothing forbids `fnd:supersededBy` between content revisions.** That is exactly the chain that cycles on revert (A→B→A). The ADR maps content revisions to `fnd:Version`, and the guide (§23.3) says `fnd:Version` carries `fnd:supersededBy`. Add a rule: supersession and history are asserted only between event IRIs, never between content revisions.
- **The event type differs between documents.** The ADR types the event IRI as `prov:Activity`. iri-policy says events are chained by `pat:prevRev` "exactly as … Part V", which makes them `pat:Revision` (and `RevisionShape` then requires `pat:target`, `pat:txn`, etc.). State the relationship, for example `pat:Revision rdfs:subClassOf prov:Activity`.

### 2.5 F-12: grammar and escaping are claimed but absent

The disposition says tuple encoding "is specified as length-prefixed … see `derived-hash`'s grammar row in iri-policy.md §4". That row contains only `enc(keyTuple)`. It is undefined, and it is not length-prefixed. The following are all still missing:

- the component alphabet (the review proposed `[a-z0-9-]`) and how `:`, `/`, `?`, `#` inside components are handled;
- a definition of `urlsafe(keyTuple)`;
- a definition of `enc(keyTuple)` and its delimiter or escaping;
- a reference to the guide's versioned normalization pipelines for key components;
- the uppercase-hex rule for percent-encodings;
- the hash **function** for `contentHash`. RDFC-1.0 canonicalises; it does not define the dataset digest you store.

**Worse, the two normative texts produce different bytes for `derived-hash`:**

- ADR: `sha256(schemeVersion|ns|enc(keyTuple))`
- iri-policy: `sha256(v{schemeVersion}|{ns}|enc(keyTuple))`

Two teams implementing from the two documents will mint different IRIs for the same key.

**"At least 128 bits" is itself ambiguous.** If implementations may choose 128 or 256, the same content has two IRIs. Fix the width exactly per `schemeVersion`.

The ADR's Consequences section says iri-policy contains the "full component grammar, escaping and normalization rules". It does not yet.

### 2.6 F-6: key rotation guidance is misapplied

The review's "never rotate" warning was about **keyed `derived-hash` entity IRIs**, where the IRI itself depends on the key. The ADR attaches it to `surrogate-claimed` instead ("claim key must be … never rotated for existing entities").

This is wrong for two reasons:

- **Rotation doesn't touch identity here.** Under `surrogate-claimed` the entity IRI is a random UUID, so rotating the HMAC key only re-derives *claim* IRIs.
- **Never rotating is not operable.** A key that can never be rotated, even after compromise, will not pass a security review.

The guide already has the right answer: rotation is a re-key with a new version salt and a backfill (§6.1, Appendix E item 5).

**The documents also disagree on key scope.** The ADR says "per-tenant"; the guide's docstring says "the platform key".

**GDPR erasure is also unresolved.** The review's argument for `surrogate-claimed` was that "erasure remains possible (delete the claim)". But the guide retires claims by tombstone and says "the node is never deleted". The tombstone keeps `pat:retiredBy <person>` linked to an HMAC pseudonym of the email forever.

HMAC output is still pseudonymous personal data. You need an erasure path that actually deletes the claim node, and a note on how that interacts with ownership monotonicity.

### 2.7 F-16: skolemization is contradictory and has no IRI form

iri-policy §5 says two incompatible things:

- Without a natural key, skolemize with `surrogate` (random UUIDv4).
- Skolem IRIs "are deterministic … derived from the canonical blank-node label, not randomly assigned per run."

Both cannot hold. There are also three further problems:

- **No skolem IRI form is defined.** This was the core of the review's request: there is no `/.well-known/genid/` equivalent for URNs.
- **Canonical labels are only unique within one graph.** `c14n0` recurs in every graph, so the skolem IRI must incorporate the lineage and content hash or it collides across graphs.
- **Labels churn across revisions.** Canonical labels change whenever the surrounding graph changes, so a node's skolem identity changes on every edit. That defeats the reason to skolemize things you intend to update later (guide §14.3).
- **The ordering is circular and unstated.** Do you canonicalise, then skolemize, then hash again?

My recommendation: skolemize at ingestion from a source-local deterministic key where one exists (for example `source record id + path`), using the `derived-hash` form. Use UUIDv4 otherwise, and accept that those nodes are identity-less. After that, the stored graph has no blank nodes. RDFC-1.0 then degenerates to sorting N-Quads, which also solves most of the hashing performance problem (§4.4).

---

## 3. Problems in the disposition document itself

| Claim | Reality |
|---|---|
| "Accepted in full" | Several items are deferred, dismissed or not implemented (F-12, F-16, padding, crosswalk, `pat:etag`) |
| §3: the IRI-grammar crosswalk "was not raised as a defect by the review" | The review's §5 table explicitly says "the guide should include a crosswalk to A51/A54 grammar" |
| §3: padding "was not the defect" | The review states the opposite (§2.4 above) |
| "Chapter 6's `claim_iri(...)` example outputs were recomputed" | Chapter 6 shows no computed output (§5 below) |
| §1 refers to open questions in "§4 of this document" | They are in §5 |
| Guide Appendix D.1 attributes the receipt-epoch bug to "the reviewer's F9" | It was the review's §5 cross-document finding |

Also silently skipped from review §4 and §6:

- `pat:etag` should be declared deprecated in Appendix A.
- `ex:PersonEmailUnique` in guide §7.3 has the same `sh:prefixes ex:` problem; only `NoForkShape` was fixed.
- The review asked for "distinct IRIs are not asserted `owl:differentFrom`" to be stated.
- The review asked for the `owl:imports` catalog requirement.
- The review asked for explicit link triples to be used for "all revisions of lineage X" instead of `STRSTARTS` scans.
- The review asked how `owl:Ontology` headers and `owl:versionIRI` relate to the registry IRI, beyond the placeholder rule.

A disposition that overstates completion is itself a risk: the human ratifier will trust the table rather than re-check the diff.

---

## 4. Soundness and production-readiness issues in the amended ADR

These are not in the original review but affect whether the design is workable at scale.

### 4.1 Literal canonicalisation breaks content addressing (design bug)

iri-policy §3.4 hashes `"1"^^xsd:integer` and `"01"^^xsd:integer` identically. In RDF 1.1 these are **different terms**. If the store keeps the original lexical forms, two different stored graphs share one content revision IRI and pass full-hash verification.

That is the silent aliasing F-2 was meant to prevent, now caused by design rather than by collision. Choose one:

- **(a)** Canonicalise lexical forms **on write**, so the stored graph *is* the hashed graph.
- **(b)** Hash exact lexical forms and drop §3.4. This is simpler, and consistent with the §3.4 statement that the hash is "not semantic equivalence".

Either way, fully specify the rules for language-tag case, `xsd:decimal`/`xsd:double`, and `xsd:dateTime` timezones. Also state whether `schemeVersion` is inside the hash input: the review asked, and it is still unanswered.

### 4.2 Merges by reference rewriting do not scale, and conflict with immutability

F-8's "references are migrated to the canonical IRI" means rewriting every content revision that mentions the alias. Each rewrite changes that revision's hash, which means a new content revision and a new event, cascading across lineages. For a large entity-resolution merge this is a platform-wide write storm.

Recommended approach:

- **Resolve aliases at read time** via an alias index.
- **Rewrite lazily** when a lineage next revises for its own reasons.
- **Never rewrite sealed content revisions.**

Separately, **verify that `fnd:replacedBy` exists in Foundation.** The guide's Foundation alignment (§23.3) lists `fnd:supersededBy`, not `fnd:replacedBy`. If it doesn't exist, the ADR depends on an undefined term.

### 4.3 The epoch fix depends on the epoch surviving a restore

The epoch lives in `urn:g:dataset`, *inside* the dataset being restored. A restore brings back epoch 3. Collision safety then depends entirely on an operator bumping it before the first write (runbook step 1).

For a mechanism whose whole purpose is disaster recovery, make it fail-safe. For example:

- source the epoch from outside the backed-up store (PostgreSQL, etcd or the restore tooling); or
- have writers refuse to start until the epoch exceeds a durable external high-water mark.

A related gap: the S6 as-of query pins a single epoch. As-of reads spanning a restore boundary (epoch-3 prefix plus epoch-4 continuation) are not handled.

### 4.4 Content-hash cost

RDFC-1.0 on large graphs with blank nodes is expensive. The "bounded work budget" has no value and no stated behaviour for legitimate large ontologies.

If skolemization happens at ingestion (§2.7), canonicalisation becomes a sort-and-stream hash and the budget only matters for residual blank nodes. For very large or frequently revised graphs, consider chunked or Merkle hashing so a small edit doesn't rehash millions of triples.

### 4.5 `pat:current` read semantics

**State the normative read pattern.** Readers resolve the pointer and the payload in **one query**, so both come from one snapshot, for example:

```sparql
GRAPH <meta> { <lineage> pat:current ?g }
GRAPH ?g { … }
```

Two separate requests can observe a pointer to a revision that has since been pruned.

**Specify three further things:**

- where a lineage's version row lives, since the guide keys rows by aggregate graph IRI in `urn:g:meta/{shard}`;
- that retention must never prune anything reachable from `pat:current`, or within a reader grace window;
- that the "materialised `/current` projection" is a full graph copy per promotion. Recommend it only for small graphs, or not at all.

**The `pat:` namespace is not decided.** The ADR now makes `pat:current` normative, but `pat:` is explicitly an illustrative namespace (`https://example.org/lattice/patterns#`, Appendix E item 3). A normative ADR shouldn't depend on it; either decide the namespace first or state that dependency.

### 4.6 Scope and registries are undefined

**Scope.** iri-policy §1 says the grammar applies to "`urn:lattice:` **and `urn:`** entity IRIs". Taken literally, that brings `urn:key:`, `urn:rev:`, `urn:txn:` and `urn:g:` into scope. These violate the grammar: uppercase base32 claim IRIs, and ULID txn IDs versus Rule 2.

Either narrow the scope to `urn:lattice:`, or add the crosswalk the review asked for and reconcile the forms. Right now the guide's receipts (`urn:rev:{agg}/e{epoch}/{seq}`) and ADR events (`{lineage}/evt/e{epoch}/{seq}`) are two grammars for the same concept.

**Registries.** `{ns}`, `{family}`, `{scope}`, tenant IDs and the reserved shared-data tenant are all "registered", but there is no registry artefact the validator can check against. Define one, even if it is just a versioned file in the ontology repo.

### 4.7 Owner semantics for lineages

F-3's question is still open: what happens when two producers register identical content under the same lineage? Is it a no-op, or an ownership conflict?

Also, lineage allocation via `pat:KeyClaim` inherits P1's write-skew caveat. On MVCC stores it needs P3, serializable isolation or a single writer. Say so. Because the lineage key is non-sensitive, you can also note that no HMAC is needed.

### 4.8 Minor points

- The ADR says `surrogate` minting "is checked by the TCK (P0.5)". The TCK tests stores, not ingestion plans; this needs a plan linter.
- The default-ignorable strip list in the guide's §8.1 is incomplete. The Unicode `Default_Ignorable_Code_Point` set also includes U+00AD, U+034F, U+180E, U+2061–2064, bidi controls and variation selectors. Use the property, not a hand list.
- `casefold` should be followed by re-normalisation (`NFKC(casefold(NFKC(x)))`).
- The QP4 test's second loop compares a function with itself. That is not "an independent computation", despite what the disposition says.
- For registration of an unregistered NID, consider `tag:` URIs (RFC 4151). They require no registration and have the same internal-only properties.
- UUIDv4 IRIs have poor B-tree locality wherever they are indexed as text outside the triple store, for example in the PostgreSQL ledgers. Store them as native `uuid` columns there.

---

## 5. Guide-side checks

| Disposition claim | Verified? |
|---|---|
| Receipt IRIs carry epoch across chapters | ✅ Yes, throughout the examples checked |
| HMAC widened to 128 bits | ◑ The function default changed, but **every claim-IRI example is still 16 base32 chars (80 bits)**. 128 bits needs 26 chars. The examples are also literally `base32("abcdefghij")` (`MFRGGZDFMZTWQ2LK`) and `base32("1234567890")` (`GEZDGNBVGY3TQOJQ`). Fine as placeholders, but label them as such and fix the length |
| `deterministic_iri` output recomputed | ◑ Length is now consistent (20 bytes → 32 chars). The value can't be verified from the documents; generate it in a test rather than trusting prose |
| S6 corrected | ✅ The logic is now correct, including re-assertion after retraction. Still uses an unbound `GRAPH ?log` (the guide's own F6 anti-pattern) and is single-epoch |
| S3 prefix check | ◑ Introduces `urn:g:retention` and `pat:retentionLowWaterMark`, neither in §2.3 nor Appendix A. §24.2, which it cites as maintaining the value, doesn't mention it. Doesn't detect a stream with *no* surviving receipts |
| `sh:declare` note | ✅ for `NoForkShape`. ❌ `ex:PersonEmailUnique` (§7.3) not addressed |
| Normalization strip step | ✅ The QP4 inputs now converge. The list is incomplete (§4.8) |

---

## 6. Recommended actions

**Blocking before ratification:**

1. Define `{base}`, and restrict `{scope}` so it is never an environment. Fix all `prod` examples (§2.1).
2. Reconcile the `derived-hash` input bytes between the ADR and iri-policy. Name the hash function and fix the exact width (§2.5).
3. Fix one sequence padding width in the grammar and make all examples conform (§2.4).
4. Resolve literal canonicalisation: canonicalise on write, or drop it (§4.1).
5. Rewrite skolemization with a concrete IRI form and a non-contradictory derivation rule (§2.7).
6. Write the actual component grammar and escaping rules (§2.5).
7. Correct the examples: valid UUIDv4, lowercase `{ns}` tokens, no `derived-hash` on person-like entities (§2.2, §2.3).
8. Correct the disposition so it accurately reflects what was deferred.

**Should fix before production:**

9. Make the epoch durable outside the restorable dataset (§4.3).
10. Adopt read-time alias resolution for merges, and confirm that `fnd:replacedBy` exists (§4.2).
11. Specify the `pat:current` read pattern, where the version row lives, and retention interaction; decide the `pat:` namespace (§4.5).
12. Correct the HMAC rotation wording, reconcile per-tenant versus platform key, and define claim erasure (§2.6).
13. Forbid `fnd:supersededBy` between content revisions (§2.4).
14. Add the scope clarification or crosswalk between the guide's `urn:` forms and the ADR (§4.6), and create the token registries.

With items 1–8 done, the ADR would be a sound, implementable identity policy. The underlying model is now the right one; what remains is making the normative text precise enough that two independent implementations mint the same bytes.