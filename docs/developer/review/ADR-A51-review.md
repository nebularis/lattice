# Review: ADR-A51 (IRI and Identity Policy) and the RDF & SPARQL Patterns Guide

## 1. Verdict

**The core of ADR-A51 is sound.** It separates a stable lineage identity from an immutable, content-addressed revision. It keeps versions out of entity identifiers. It offers a small set of minting strategies with named risks, bans PII, and gates surrogate use. All of this matches good RDF and OWL practice and closely mirrors established models:

- OWL 2 ontology IRI versus `owl:versionIRI`
- Memento URI-R versus URI-M
- PROV `specializationOf`
- DCAT and Dublin Core `isVersionOf`

**It is not fundamentally in conflict with RDF or OWL.** Two rules as written do conflict with normal expectations, though, and several claims are overstated. I would not ratify it unchanged. The problems fall into five groups:

1. **One rule conflicts with RDF identity expectations.** Rule 3, environment-scoped IRIs rewritten on clone, breaks "an IRI denotes the same thing everywhere." It also breaks content addressing and vocabulary stability.
2. **Internal contradictions.** Rule 2 ("no version numbers in IRIs") is violated by the ADR's own revision IRI. Surrogate ULIDs violate the "no timestamps" rule.
3. **Overclaims.**
   - "Uniqueness is structural by construction" and "deletes the conflict-rejection path entirely" are not true with a 64-bit truncated hash.
   - The problem moves to lineage-name allocation rather than disappearing.
   - `derived-hash` does not "avoid PII" for low-entropy keys.
4. **Under-specification that will cause real interoperability bugs.** There is no component grammar, escaping, normalization or hash encoding. The alias-graph mechanism is undefined. Relative-IRI resolution against URNs misbehaves.
5. **Divergence from the patterns guide it is supposed to underpin.**
   - The guide's recommended entity identity is the strategy the ADR restricts: opaque UUIDs plus key claims.
   - The guide's revision IRIs are sequence-addressed and omit the epoch, so they can be reused after a restore.
   - The guide mints IRIs containing versions and timestamps, which the ADR forbids.

The rest of this review details each point, then gives a suggested amended policy.

---

## 2. What the proposal gets right

| Decision | Why it is good |
|---|---|
| **Lineage versus revision split** | This is the right primitive. It matches OWL 2's ontology IRI / version IRI split, which is widely understood by tools (Protégé, OWL API, ROBOT, OBO release practice). It gives you a stable handle for references and an immutable handle for evidence and provenance. |
| **Content-addressed revisions** | Registration becomes idempotent: the same content yields the same IRI, and replays are no-ops. It is cache-friendly and verifiable. It is exactly the P0 pattern ("make uniqueness structural") from Chapter 5 of the guide, applied to graphs. |
| **Alias for "current"** | Separating "which revision is live" from revision identity is correct. It keeps the only mutable state in one pointer, which the guide can then protect with CAS (§30.1). |
| **Minting strategy taxonomy with a risk column** | Explicit and teachable. The "surrogate is never idempotent" warning is exactly the K4 failure mode the guide calls "the one that bites in production." |
| **No PII in IRIs** | Correct and important. IRIs are copied into logs, dumps, URLs, caches and third-party systems, and cannot practically be erased. |
| **No versions in entity IRIs** | Correct for entities and lineages ("Cool URIs don't change"). Versioning belongs in `fnd:Version` nodes. |
| **Surrogate use requires declaration (G9)** | Good governance. It forces the "will re-ingestion converge?" question at plan-review time. |
| **Validator and grammar tests before any dataset (P0.3.7)** | Correct sequencing. Identity mistakes are the most expensive kind to fix later. |

---

## 3. Findings on soundness

Severity scale: **Critical** means ratifying as-is will cause data-integrity or identity bugs. **Major** means a significant design flaw or contradiction. **Minor** means a gap that needs clarifying.

### F-1 — CRITICAL: Rule 3 (environment-scoped base, rewritten on clone) conflicts with RDF identity

In RDF, an IRI is a global name. The same IRI should denote the same resource in every dataset in which it appears. Making the environment part of identity and rewriting it on clone causes six problems.

- **It breaks content addressing.** If the semantic hash covers graph contents, and those contents contain environment-scoped IRIs, a cloned graph hashes differently. Every revision IRI therefore changes on clone.
  - Either the clone is no longer "the same revision" (defeating the purpose of cloning), or you must re-mint every revision IRI and every reference to it.
  - The ADR doesn't say which.
- **"Rewrites that segment only" is not a safe string operation.** IRIs appear in places a triple-level rewrite won't reach:
  - inside literals, such as `sh:sparql` query strings, `sh:prefixes`/`sh:declare` namespace literals, JSON or YAML payloads in literals, `rdfs:seeAlso` strings, and documentation;
  - inside hash inputs;
  - in external systems (PostgreSQL ledgers, RabbitMQ messages, logs).
- **It breaks vocabulary and TBox stability.** If classes, properties and shapes minted under `{base}` are environment-scoped, then dev and prod have *different ontologies*. Shapes, queries, mappings and tests become environment-specific. OWL axioms linking the two are meaningless.
  - The Foundation namespace (`https://www.nebularis.org/...`) is clearly not environment-scoped. The policy must say that TBox and vocabulary IRIs never are.
- **It is inconsistent with the lineage grammar.** `urn:lattice:{tenant}:{scope}:{family}:{localName}` has no environment segment. So either lineage IRIs are identical across environments (contradicting Rule 3) or the environment is hidden inside `{tenant}` (undocumented).
- **It hides a data-governance problem.** Cloning prod to dev copies real data. Rewriting IRIs makes the copy *look* synthetic but doesn't remove PII.

**Recommendation:** Keep the environment out of identity. Environments should be separate datasets or stores with separate access control, and the same IRIs should be used everywhere. If synthetic test fixtures need distinguishing, give them a distinct *tenant* (e.g., `test-fixtures`), not a rewritten base. If environment scoping is genuinely required, define it once in the lineage grammar, exclude it from content hashes via a base-relative canonical form, and exempt all TBox IRIs.

### F-2 — CRITICAL: "Uniqueness is structural by construction" is false with a truncated hash, and the conflict path should not be deleted

`semanticHash[0:16]` is, if hex (the encoding is unspecified), **64 bits**.

- **Accidental collisions are negligible *per lineage*.** The birthday bound is about 2³² revisions per lineage.
- **Adversarial collisions are not negligible.** A 64-bit collision takes about 2³² hash work, which is trivial. Content registered by tenants or users (Surface contracts, mappings, uploaded ontologies) is attacker-influenced.
  - If the registry trusts the IRI as the key and the rejection path is deleted, a crafted collision silently aliases two different graphs under one revision IRI.
  - That is exactly the corruption the old `§5.2` check prevented.
- **"By construction" also fails without a completely specified canonicalization.** Blank-node canonicalization, literal lexical forms and the profile version all need to be defined. Otherwise the same content can yield different hashes, and "different content cannot collide" becomes "the same content may not converge."

**Recommendation:**

- Keep the check, but demote it from a code path to an assertion. On registration of an existing revision IRI, compare the *full* hash (the `revisionHash` verification field the ADR already keeps) and reject on mismatch. This is O(1) and costs nothing.
- Use at least 128 bits (32 hex chars) if the IRI is a trust boundary.
- Specify the encoding: lowercase hex or unpadded lowercase base32.

### F-3 — MAJOR: The conflict-rejection problem is moved, not removed

The old rule rejects registration when `(tenantId, projectId, graphIri)` collides on hash, **family or owner**.

- **Hash:** handled by the revision IRI (modulo F-2).
- **Family:** handled, because `{family}` is in the lineage.
- **Owner:** *not* in the IRI. Two producers can register the same content under the same lineage. Is that a no-op, or an ownership conflict?
- **Lineage allocation:** `{localName}` is chosen by someone. Two producers choosing the same lineage localName for *different logical artefacts* is a K2/K3 uniqueness problem. It needs the guide's P1/P2 claim registry, or deterministic derivation of `localName`.
- **Project:** `projectId` from the old key doesn't obviously map to `{scope}`. Is scope the project? A domain? Say so.

**Recommendation:** State that lineage IRIs are allocated through a key claim (P1 + P2) keyed on `(tenant, scope, family, localName)` with an owner. That is where the owner and family checks now live. Rewrite the consequence as "replaces the runtime content-conflict check with structural identity plus a lineage-allocation claim." This is still a genuine simplification.

### F-4 — MAJOR: Rule 2 contradicts the ADR's own revision IRI, and common OWL practice

The revision IRI is `{lineageIri}/rev/{profileVersion}-{hash}`. It contains a version number, which Rule 2 forbids.

More broadly, version-bearing IRIs are *standard* in OWL. Consider `owl:versionIRI` values like `http://purl.obolibrary.org/obo/go/releases/2024-01-17/go.owl`, which contain a date. The rule as written would forbid OWL-conformant version IRIs.

The patterns guide also mints version and time-bearing IRIs:

- the `v1` salt in `urn:key:person-email:v1:…`
- the month in `urn:g:txlog/2026-09`
- sequences in `urn:rev:orders/1/0000000000000042`, `urn:g:delta/orders/1/…/add` and snapshot graphs `urn:g:orders/1/…42`

**Recommendation:** Scope Rule 2 to **entity IRIs and lineage IRIs**. Explicitly permit version, profile or position components in:

- revision IRIs
- scheme-version salts (which are *identity-scheme* versions, not data versions)
- infrastructure graph names governed by ADR-A54's grammar

### F-5 — MAJOR: Surrogate ULIDs embed a timestamp

A ULID's first 48 bits are a millisecond Unix timestamp. So do UUIDv7s. `{base}/{class}/s/{ULID}` therefore contains a timestamp, violating Rule 2.

This is not only pedantry. It can leak personal data (Rule 1). The creation time of a patient record, a complaint, or an extraction candidate from a specific document can be sensitive, and it is trivially decodable from the IRI.

**Recommendation:** Use UUIDv4, or 128 random bits base32-encoded, for surrogates. Alternatively, keep ULIDs for their index locality and add an explicit, justified carve-out in Rules 1 and 2. The same applies to `urn:txn:{ULID}` in the guide, though infrastructure identifiers are less of a concern.

### F-6 — MAJOR: `derived-hash` does not "avoid PII in IRIs"

`sha256(canonical(keyTuple))` is unkeyed. For low-entropy keys (emails, national IDs, phone numbers, MRNs, names plus date of birth) it is reversible by dictionary or enumeration.

The patterns guide says this itself (Chapter 5, and the `claim_iri` docstring in §6.1), and uses HMAC for exactly that reason. Under GDPR, an unkeyed hash of an identifier is **pseudonymous data, which is still personal data** (Recital 26; EDPB guidance). So the strategy's "use when" column is wrong for the very case it advertises.

A keyed hash (HMAC) fixes reversibility but creates a new tension: **the key can never be rotated without re-minting every entity IRI**, which contradicts "stable forever."

**Recommendation:**

- `derived-hash` is for non-sensitive composite keys only, unless keyed.
- If keyed, the key is per tenant, never rotated for minting purposes, and rotation means "new scheme version for new entities, plus an old-to-new alias index." State this explicitly.
- For sensitive keys, prefer the guide's default: an opaque random entity IRI, plus a keyed-hash key claim in an access-controlled graph (P1). Identity stays stable, the claim stays private, and erasure remains possible (delete the claim).

### F-7 — MAJOR: The ADR and the guide disagree on the default entity-identity strategy

- **The guide** (§2.2, Chapter 5, §8.4 item 1) recommends **opaque UUID entity IRIs plus a P1 key-claim registry**. This makes surrogate-minted entities *converge* on re-ingestion: look up the claim, reuse the owner IRI.
- **The ADR** says surrogates are "never idempotent — forbidden for any node re-ingestion must converge onto." It restricts them to identity-less nodes, behind a justification gate.

Both can't be the default. The ADR's statement is true only of *unindexed* surrogates. A surrogate plus a claim registry is idempotent at the claim level, and it is the only option that satisfies all four of:

- no PII
- key mutability
- stable-forever identity
- erasure

**Recommendation:** Add a fourth strategy, e.g. `surrogate-claimed` (random IRI plus a P1 claim on the natural key), as the recommended default for entities with mutable or sensitive keys. Then reserve Rule 4's justification gate for *unclaimed* surrogates.

### F-8 — MAJOR: Key mutability and entity resolution are not addressed

Both `natural-key` and `derived-hash` bind the IRI to the key. The ADR says "use when source has a *stable* business key," but "stable" needs to mean **immutable forever**. Business keys change: SKUs get renamed, emails change, companies merge, account numbers get reissued. When they do, "stable forever" breaks, and every reference must migrate.

Relatedly, the mitigation "add a source-system discriminator" prevents cross-source collision but also **prevents convergence**. The same person from CRM and billing gets two IRIs by design. That is the K4 problem, and the ADR is silent on how it is resolved.

**Recommendation:**

- Require immutability, not stability, for key-derived strategies.
- Define the merge policy. When two IRIs are found to denote one entity, one becomes canonical. The other is retained as a deprecated alias (`fnd:replacedBy`, or `owl:deprecated` plus a pointer) and references are rewritten.
- Avoid `owl:sameAs` as the operational mechanism. Under reasoning it causes sameAs-clique explosion, and it can't be retracted cleanly (see §1.4 of the guide).
- Say that source discriminators are for *provenance-local* identity. Cross-source identity is an entity-resolution concern layered on top.

### F-9 — MAJOR: Content-addressed revisions and history cycles

A content-addressed revision identifies **a content state, not an event**. If a graph goes A → B → A (a revert), the third registration yields the *existing* revision IRI for A.

If `fnd:Version` nodes are chained with `fnd:supersededBy`, you get A supersededBy B, and B supersededBy A: a cycle. Any "latest version" or "history" traversal loops or gives nonsense. The alias `/current` repointing back to A is fine; the version graph is not.

The guide's receipts (`urn:rev:{aggregate}/{seq}`) are **event**-identified, which is the other half of the model.

**Recommendation:** Make the distinction explicit.

- **Revision IRI** is *content* identity (`fnd:Version`, a snapshot).
- **Promotion or receipt IRI** is *event* identity (e.g., `pat:Revision`, or a `prov:Activity`).
- History (`supersededBy`, `prevRev`) chains *events*, and each event points at a content revision.

A revert is then a new event pointing at an old content revision. Also decide whether `profileVersion` is inside the hash input; if not, identical content under two profiles is two IRIs with one hash.

### F-10 — MAJOR: Embedding `{class}` (and `{family}`) in "stable forever" IRIs is brittle under OWL

OWL individuals routinely:

- have multiple types;
- acquire types by inference;
- change type when the ontology is refactored (a `Customer` becomes a `Party` plus a role).

An IRI of the form `{base}/{class}/…` bakes one classification into permanent identity. When the class hierarchy changes, you either keep IRIs that lie about the type or re-mint them. The same applies to `{family}` in lineage IRIs, if a graph can ever be re-homed.

**Recommendation:** Replace `{class}` with a **minting-namespace token** from a registry (e.g., `person`, `order`). Make it explicitly *not* an `rdf:type` claim, and never rename it once used. Readers and tools must never infer types from IRI structure.

### F-11 — MAJOR: The alias graph is undefined as an RDF mechanism

"`{lineageIri}/current` — repointed atomically at promotion" assumes graph aliasing. RDF 1.1 datasets and SPARQL 1.1 have no aliases. A named graph is a `(name, graph)` pair. You must pick a mechanism:

| Mechanism | Pros | Cons |
|---|---|---|
| **(a) Materialized copy** into `…/current` | Plain `FROM`/`GRAPH` queries work | Copy cost; "atomic" only within one transaction; double storage |
| **(b) Pointer triple** (`pat:current`, as in §20.3 of the guide) | No copying | `…/current` is then not a graph but a resource; queries need a rewrite or resolution layer |
| **(c) Store-specific feature** | — | Not portable across the SPI |

**Recommendation:** Choose (b) as normative, protected by the guide's CAS on the version row, with an optional (a) projection for tools that need a literal graph. State what `FROM <…/current>` means for readers during a promotion.

### F-12 — MINOR: No component grammar, escaping or normalization rules

RDF compares IRIs by exact character string. `%2F` and `%2f` are different IRIs, as are `Acme` and `acme`, and NFC and NFD forms. The ADR needs rules for each of the following.

- **Component alphabet and escaping.** If `{localName}` or `{tenant}` can contain `:`, `/`, `?` or `#`, the grammar is ambiguous. `urn:lattice:a:b:c:d:e` doesn't parse uniquely.
- **Tuple encoding for `urlsafe(keyTuple)` and `canonical(keyTuple)`.**
  - Without length-prefixing or escaping, `("a|b","c")` and `("a","b|c")` collide.
  - "urlsafe" is undefined (percent-encoding? base64url?).
  - Normalization must use the guide's frozen, versioned pipelines (§8.1).
- **Case and Unicode.** Lowercase scheme and NID. Uppercase hex in percent-encodings. No percent-encoding of unreserved characters. NFC for any non-ASCII. (Better: restrict minted IRIs to ASCII.)
- **Hash encoding.** Hex versus base32, and case. The guide uses base32 in some places; the ADR implies hex slices.
- **Scheme versioning.** The guide rightly salts hash inputs with `v1|`. The ADR's `derived-hash` has no salt, so a change of canonicalization silently splits identity.

This is exactly what the P0.3.7 validator should enforce, but the ADR must define the rules it validates.

### F-13 — MINOR: `urn:lattice` is an unregistered URN namespace, and relative resolution misbehaves

- **Registration.** RFC 8141 requires a registered NID (formal or informal `urn-N`), and `lattice` is not registered. Practically, every triple store and OWL tool accepts it, so this is a hygiene issue.
  - There is a small risk of clashing with a future registration.
  - URN lexical equivalence is also not RDF equivalence. `URN:LATTICE:x` and `urn:lattice:x` are the same URN but different RDF terms. So mandate the lowercase form.
- **Relative resolution (the practical trap).** `{lineage}/rev/…` *looks* hierarchical, which tempts authors to use `@base` and relative IRIs in Turtle or JSON-LD. RFC 3986 resolution against a rootless URN path gives surprising results.
  - With `@base <urn:lattice:acme:p:F:x>`, the reference `<rev/abc>` resolves to `urn:rev/abc`. That is silently wrong.
  - **Forbid `@base` and relative references for URN-based IRIs.**
- **Dereferenceability.** URNs are fine for internal identity, and OWL does not require dereferenceability. But `owl:imports` of URN ontology IRIs needs a catalog (OWL API/Protégé XML catalogs). Anything published as Linked Data, LDP or Solid (which the guide discusses in §15.4) expects `http(s)` IRIs.
  - Decide now whether public identifiers will ever be needed. Mapping URNs to `https://id.<domain>/…` later is possible but is a second identity.
  - Alternatively, choose `https` under a controlled domain from the start (w3id.org or your own), with URNs reserved for purely internal infrastructure.

### F-14 — MINOR: Semantic hash specification gaps

"semanticHash" is undefined. It needs:

- **A canonicalization algorithm** (RDFC-1.0) with its **complexity limits**. Adversarial blank-node structures ("poison graphs") can make canonicalization expensive, which is a DoS vector on registration, so set a work bound and reject beyond it.
- **A self-reference rule.** If the graph contains its own revision IRI (an `owl:versionIRI` in an ontology header, or provenance triples), the hash is circular. Hash with the self IRI replaced by a placeholder, or exclude the header.
- **A name that isn't misleading.** RDFC hashes *syntax after bnode canonicalization*. `"1"^^xsd:integer` and `"01"^^xsd:integer`, or two OWL-equivalent axiomatizations, hash differently. Call it `contentHash`, or define literal canonicalization if you genuinely want value-level equivalence.
- **An environment rule** (see F-1). If IRIs in the content are environment-scoped, the hash is too.

### F-15 — MINOR: Tenant in IRIs

The tenant segment must be an **immutable opaque ID, never a name**. Tenants rename, merge and split. For single-person tenants, a name would be PII.

The ADR should also define a reserved tenant for **shared reference data** (country codes, common vocabularies), or cross-tenant references will mint duplicates.

### F-16 — MINOR: Blank nodes, skolemization and reification are unaddressed

The guide requires skolemization (§5, §14.3). The ADR should specify:

- The skolem IRI form. RDF 1.1 §3.5 suggests `/.well-known/genid/` for `http` bases; there is no equivalent convention for URNs, so define one.
- Whether skolem IRIs are deterministic (derived from the canonical bnode label within a revision) or surrogate.

The "reified span / extraction candidate" surrogate case may also be better modeled with RDF 1.2 triple terms or annotations, if the target stores support them.

### F-17 — MINOR: Imprecise risk description for `derived-hash`

"Requires an index from key to IRI" is backwards. Key → IRI is recomputable. What `derived-hash` needs is an index from **IRI to key**, for debugging and support, and that index is itself PII and must be access-controlled.

---

## 4. Conformance against RDF, OWL and store expectations

| Expectation | Status | Notes |
|---|---|---|
| IRIs are opaque global names; one IRI denotes one thing everywhere | ⚠ Conflict | Rule 3 (F-1). Fix by keeping the environment out of identity. |
| IRI equality is exact string equality (RDF 1.1 Concepts §3.2) | ⚠ Gap | Needs canonical-form rules (F-12, F-13). |
| No Unique Name Assumption in OWL | ✅ Compatible | "Structural uniqueness" is about IRI strings, not denotation. Say explicitly that distinct IRIs are not asserted `owl:differentFrom`, and define the merge policy (F-8). |
| OWL 2 ontology IRI / version IRI | ✅ Strong alignment | Lineage maps to ontology IRI and revision to version IRI. Rule 2 must allow version-bearing version IRIs (F-4). Define how in-graph `owl:Ontology` headers relate to the registry's revision IRI (F-14 self-reference). |
| `owl:imports` resolution | ⚠ Needs a catalog | URNs don't resolve; ship XML catalogs or a resolver (F-13). |
| Types are asserted or inferred, can be many, and can change | ⚠ Conflict | `{class}` in IRIs (F-10). |
| Punning and graph-name semantics | ✅ Compatible | Using a revision IRI as both a graph name and a `fnd:Version` individual is fine. RDF 1.1 leaves graph-name denotation open, and OWL 2 DL tolerates it. Document the convention. |
| Named graphs have no aliasing | ⚠ Gap | Alias mechanism undefined (F-11). |
| Linked Data / Cool URIs / dereferenceability | ◑ Partial | "Never change" and "no versions in entity IRIs" are aligned. URNs and environment rewriting are not. Acceptable for internal-only identity; decide on public identity (F-13). |
| Skolemization (RDF 1.1 §3.5) | ⚠ Gap | Not specified (F-16). |
| Triple stores (TDB2, RDF4J, GraphDB, Neptune, Stardog, Virtuoso) | ✅ No blockers | All accept URNs of this length. Random-hash IRIs have poor B-tree locality in stores that index raw strings, but dictionary-encoded stores (most of them) don't care. Prefix-based `STRSTARTS` queries over `{lineage}/rev/` work but are scans. Use explicit link triples for "all revisions of lineage X." |
| JSON-LD / Turtle tooling | ◑ Minor | Turtle prefixed names need `\/` escapes for `/` in local names. Avoid `@base` with URNs. Beware JSON-LD contexts that define a term named `urn`. |
| GDPR (pseudonymous data is personal data) | ⚠ Conflict | Unkeyed `derived-hash` (F-6); ULID timestamps (F-5). |

---

## 5. Cross-document consistency between ADR-A51 and the patterns guide

The guide is labeled "authoritative," and ADR-A54 and ADR-A63 depend on A51. Right now the two documents describe different identity models.

| Topic | ADR-A51 | Patterns guide | Resolution |
|---|---|---|---|
| Entity IRI default | natural-key or derived-hash; surrogate gated | opaque UUIDs plus P1 key claims (§8.4) | Add `surrogate-claimed` (F-7) |
| Revision identity | content-addressed `{lineage}/rev/{pv}-{hash}` | position-addressed `urn:rev:{agg}/{seq}` | Both are needed: content versus event (F-9). Name them differently. |
| Versions and times in IRIs | forbidden | `v1` salts, `txlog/2026-09`, seq-bearing receipt, delta and snapshot graph IRIs | Scope Rule 2 (F-4) |
| Hash for sensitive keys | plain SHA-256 | HMAC (and it explains why plain is unsafe) | Adopt the guide's position (F-6) |
| IRI grammar | `urn:lattice:{tenant}:…` | `urn:g:`, `urn:rev:`, `urn:key:`, `urn:txn:`, `urn:person:` | Guide examples are illustrative, but the guide should include a crosswalk to A51/A54 grammar |
| Snapshot-per-revision graphs (§20.3) | revision IRIs under the lineage | `urn:g:orders/1/0000000000000042` | Align on one form |

**A bug in the guide's identity model:** the corrected receipt IRI `urn:rev:orders/1/0000000000000042` **omits the epoch**. The guide's own F3 lists "receipt IRIs are reused" as a consequence of restore, and fixes it by adding the epoch to the guard, row, receipt and ETag, but *not to the IRI*.

After a restore that rewinds `seq`, a new revision 42 under epoch 4 mints the same IRI as the old revision 42 under epoch 3. The old one can still exist in:

- exported logs
- consumer caches
- CDC sinks
- `pat:prevRev` references held elsewhere
- the PostgreSQL ledger

That is precisely the identity reuse the ADR's philosophy forbids. **Fix:** `urn:rev:{aggregate}/e{epoch}/{seq:019}`. Also, the guide's zero-padding width is inconsistent: 16 in examples, 19 "in production" (`REV_WIDTH`). Identity-bearing padding must be fixed in the grammar, because changing it later re-mints every IRI.

---

## 6. Broader review of the patterns guide

You asked for pros and cons of the material generally, so here is a condensed assessment beyond identity.

### Strengths

- The central insight is correct: a counter rewritten inside the writing transaction makes allocation order equal commit order, and closes the G2 reorder hole.
- It is honest about SPARQL's lack of return values. The **txn-claim `ASK`** plus the mandatory `resolve(txnId)` and an explicit `Unknown` outcome is the most valuable design element.
- **Capabilities are discovered by a TCK**, not declared. `min_level` fails fast at startup. It forbids silent downgrades of multi-aggregate atomicity. This is mature SPI design.
- The dense per-stream, sparse cross-stream (HLC) default is the correct trade-off. The epoch runbook is the right answer to restore safety.
- The per-store notes are largely accurate and appropriately hedged:
  - TDB2 is multiple-reader, single-writer (MR+SW), with `promote()`.
  - RDF4J has `ShaclSail` and `SERIALIZABLE`.
  - Neptune has `ConcurrentModificationException` and Streams' `(commitNum, opNum)`.
  - Blazegraph reports a mutation count.
- Normalization discipline, the OWL inverse-functional-property warning, and the query discipline rules (QP1–QP5) are all sound.

### Technical issues I found

1. **The S6 as-of query is incorrect.**
   - `pat:retracts ?g` is compared against the *asserted* graph `?g`. In the patch-log model of §20.2, asserts and retracts point at *different* delta graphs (`…/add` versus `…/del`), so the `FILTER NOT EXISTS` never matches. Retracted triples are therefore returned.
   - The `?r2` pattern also doesn't constrain `pat:target` or require `?s2 > ?seq`.
   - A correct as-of is triple-level: "asserted at s₁ ≤ S and not retracted at any s₂ with s₁ < s₂ ≤ S, for the same target."
2. **The QP4 determinism test would fail.** The third input appears to contain a trailing zero-width space. NFKC doesn't remove U+200B, and `str.strip()` doesn't strip it (`'\u200b'.isspace()` is `False`). Either the pipeline needs a "remove default-ignorable code points" step, or the test documents a false guarantee. Either way, this is a good illustration of why normalization pipelines need their own corpus (K-6).
3. **The illustrative outputs don't match the code.** `deterministic_iri` takes 20 bytes, which is 32 base32 characters, but the example output shows 24. It's minor, but in an "authoritative" guide these get copied into tests.
4. **Some SHACL-SPARQL prefixes won't resolve.**
   - `sh:prefixes ex:` / `sh:prefixes pat:` requires those IRIs to carry `sh:declare` blocks, which are not shown, so validators will fail to resolve prefixes.
   - `pat:VersionRowShape` references `pat:etag`, which isn't in the Appendix A vocabulary. That's harmless, but should be declared deprecated.
5. **The `NoForkShape` caveat is understated.** `sh:sparql` cross-node constraints are exactly what the guide says incremental validators handle poorly (§7.3), so commit-time fork detection may force a full revalidation on every commit. That is worth stating alongside the §15.3 "SHACL trick."
6. **The S3 gap scan has a blind spot.** `MAX − MIN + 1` doesn't detect a missing *prefix*: a stream whose first retained receipt is 5 when retention hasn't expired. Compare `MIN` against the expected retention low-water mark.
7. **The HMAC claim IRI truncates to 80 bits.** That is fine against accidental collision per constraint. Given that claim IRIs drive ownership decisions, note the margin, or use 128 bits for consistency with the entity-IRI recommendation.
8. **The document is very long for "authoritative" status.** Normative content (the grammar, the SPI, the shapes, the declaration schema) is interleaved with narrative. Split out the normative parts, as `iri-policy.md` does for A51, so they can be versioned and tested.

---

## 7. Suggested amended policy (sketch)

**Scope.** This policy applies to LATTICE-minted IRIs only. External vocabulary IRIs are never rewritten. TBox and vocabulary IRIs are never tenant- or environment-scoped.

**Grammar** (ASCII-only, lowercase, components drawn from `[a-z0-9-]`, validated by P0.3.7):

| Kind | Form | Denotes |
|---|---|---|
| Lineage | `urn:lattice:{tenantId}:{scope}:{family}:{localName}` | `fnd:PersistentIdentity` (allocated via a P1 claim, with owner) |
| Content revision | `{lineage}/rev/{schemeVer}-{hash128}` | `fnd:Version` (content state; hash covers canonical content with the self-IRI placeholdered, plus `profileVersion`; full hash verified on re-registration) |
| Promotion or receipt | `{lineage}/evt/e{epoch}/{seq:019}` | event; chained by `prevRev`; points at a content revision |
| Current | `pat:current` pointer on the version row (normative); optional materialized `…/current` projection | — |

**Entity strategies:**

| Strategy | Form | Notes |
|---|---|---|
| `natural-key` | `{base}/{ns}/{enc(tuple)}` | Immutable, non-PII keys only; length-prefixed tuple encoding |
| `derived-hash` | `{base}/{ns}/h/{hex(sha256(v1‖ns‖enc(tuple)))[0:32]}` | Non-sensitive keys only |
| `surrogate-claimed` | `{base}/{ns}/s/{uuid4}` plus a keyed-hash P1 claim | **Recommended default** for mutable or sensitive keys |
| `surrogate` | `{base}/{ns}/s/{uuid4}` | Identity-less nodes; declared and justified |

**Rules:**

1. No personal data in IRIs, including unkeyed hashes of personal keys and embedded timestamps.
2. No data-version or time components in **entity or lineage** IRIs. Scheme versions, revision and event positions, and ADR-A54 infrastructure buckets are permitted.
3. No environment component. Environments are isolated by dataset and access control, not by identity.
4. `{ns}` is a registered minting namespace, not an `rdf:type`. It is never renamed.
5. No `@base` or relative references with URN bases. Only the canonical form is stored.
6. Merges retain the non-canonical IRI as a deprecated alias with `fnd:replacedBy`, rather than using `owl:sameAs`.
7. The skolem form is defined, and deterministic within a content revision.
8. The public identity strategy (URN only, or an `https` mapping) is decided and recorded before any external publication.

With these amendments, the policy would be sound, consistent with the patterns guide, and well aligned with RDF and OWL practice.