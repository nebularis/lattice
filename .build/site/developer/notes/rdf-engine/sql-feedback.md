# Review: *Compiling LATTICE to a relational model* (paper 5), and how formal methods apply to it

## 0. Summary

**What I reviewed.** I read the paper against two references: its own stated laws, and the formal-methods brief from earlier in this conversation. I have not seen papers 1 to 4, the `dal:` vocabulary, the Eligibility README or the compilers.

- Findings that rest on PostgreSQL or W3C semantics are stated as fact. Where I am less than certain, I say so.
- Findings that depend on LATTICE internals I can't see are framed as questions.

**Overall verdict.** The direction is sound, and I think the headline judgement survives. Compiling the shape-closed part of a deployment to PostgreSQL is likely a better trade than a custom engine. Using SHACL rather than OWL as the structural input is the right central choice. Treating `persistence` as transaction scope is a genuinely clarifying reframe.

The paper's weakness is the one the formal-methods brief warned about. It states universally quantified laws (round trip, query, inference), says "none needs a proof assistant", and then verifies them only by examples. Several of those laws, as stated, are **false for the paper's own rules**. Examples are cheap here, and several of these failures are exactly the kind cheap techniques find in hours.

**The most consequential findings:**

1. **The round-trip law fails on the paper's own worked example.** The R2RML template mints IRIs from the surrogate `id`, not the stored `iri` column (§10 vs M2). Appendix A also adds a `NOT NULL current_state_id` that the closed `LayerShape` cannot supply.
2. **"SHACL closes the world" is only partly true.** `sh:closed` restricts the properties of *focus nodes*. Triples about nodes no shape targets still validate. So $\mathrm{Valid}(\mathcal{S})$ is not the set of graphs the encoding covers.
3. **Literal mapping breaks round trip and uniqueness.**
   - `timestamptz` discards the offset, and silently reinterprets a zone-less `xsd:dateTime` in the session time zone.
   - `UNIQUE` on `numeric` rejects valid RDF that holds both `"1.0"` and `"1.00"`.
   - `interval` equality makes `P1M = P30D`, which XSD treats as incomparable.
   - Discrete ranges canonicalise `[]` to `[)`.
4. **The eligibility mapping covers only the Kleene kernel, not the concept-matching laws.** "`HierarchicalMatch`: a join to the closure table" ignores L9 (out of scheme → Undetermined), L11 and L14, which the Track B reference had to encode carefully. The concept table also gives each concept a single `scheme_id`, contrary to SKOS and to the composition problem that Alloy and ADR-A116 just worked through.
5. **The proposed oracles repeat the circularity the formal-methods brief identified.** RS-X3 checks the new SQL eligibility backend against the SPARQL backend, which shares the same IR and `_expand`. The independent oracle already exists: `tools/reference/eligibility`.
6. **Concurrency is the largest unexamined risk, and §12 has no test for it.** Three examples:
   - Aggregate invariants enforced by deferred triggers are unsound under READ COMMITTED unless every child write serialises on the root.
   - The guard in `fire_bind` can read evidence from other aggregates without protection against write skew.
   - Ordering by sequence (M45) skips rows when commit order differs from allocation order.
   This is the protocol-level gap (rung T4) the formal-methods brief already named as open.
7. **Several rules are wrong or incomplete as written:**
   - M12: class-table inheritance does *not* enforce disjointness.
   - M14 and M17: no rule for `sh:minCount ≥ 1` or bounded `sh:maxCount > 1`.
   - M21 excludes reflexive pairs.
   - M27 needs foreign keys to views, which PostgreSQL cannot do.
   - M30 contradicts `sh:closed`.

**Formal-methods answer, in one paragraph.** Don't verify the Python compiler. Verify each compiled output with small independent checkers, plus a few targeted models and proofs:

- **Translation validation:** emit an Alloy model from the relational IR. Check, at bounded scope, that it admits exactly the instances the shapes admit.
- **Differential testing (T0):** add the SQL eligibility backend as a fifth backend under the existing reference harness. Check the constraint law (SQL accepts iff a SHACL engine conforms) on mutated graphs.
- **A small extension to the existing Isabelle theory (T5)** proving the SQL three-valued encoding, aggregates included, equal to `every_value`/`some_value`.
- **TLA+/Quint (T4)** for generated operations under PostgreSQL isolation, the outbox and the projection feed.
- **SMT and automata (T3)** for regex translation, IRI-template injectivity and range-bound canonicalisation.
- **Runtime monitors (T7)** in S2/S3, built from the same invariants.

This fits G5: roughly 15% on top of the paper's estimate (§10.8), much of it replacing test effort already budgeted.

---

## 1. What the paper gets right

- **SHACL as the primary structural input (RS-D2).** This is the right call, with the caveat in §2.2.
- **Grading.** The Fact / Judgement / *(verify)* grading, and the explicit statement that nothing here is a decision, are good practice.
- **Rule IDs carried into `COMMENT ON` (M35).** This makes rule coverage *measurable*, which the formal-methods work can exploit directly (§10.6).
- **M28's scope classification** (row → `CHECK`, aggregate → deferred trigger, cross-aggregate → detective view). It is honest that cross-aggregate checks are detective only.
- **"Untranslatable patterns are refused, never approximated" (M26)** is the right default throughout.
- **Effects split into in-transaction assignments vs outbox rows**, with "no effect is ever executed outside the transaction that records it". Correct.
- **Staging through O2.** Building the SQL as a rebuildable projection first is the correct de-risking order.
- **Calling out `bool_and` and `WHERE`.** These are real hazards, and naming them shows the right instinct, though the list is incomplete (§2.4).
- **The token arithmetic checks out** (§8.4).

---

## 2. Foundations: the three laws, the closed world and three-valued logic

### 2.1 [Major] The round-trip law is necessary but nowhere near sufficient

$\mathrm{dec}(\mathrm{enc}(G)) \cong G$ is satisfied by a degenerate compiler that puts every triple into one generic `(s, p, o)` table and emits a trivial R2RML mapping. Round trip shows that information is preserved. It says nothing about whether the schema *enforces* the shapes.

The missing law is **constraint preservation**:

$$\forall G.\ \ \mathrm{load}_{SQL}(G)\ \text{succeeds} \iff \mathrm{conforms}(\mathcal{S}, G)$$

It must hold for *all* $G$, not just conforming ones. §12's "Rejection" row gestures at this, using an adversarial corpus, but only in one direction. The interesting failures are in the other direction: valid graphs the SQL rejects, as with `numeric UNIQUE` (§3), or invalid graphs it accepts, as with M12 under M8 or `minCount` on child tables.

Relevant prior art the paper omits: Sequeda, Arenas and Miranker, *On directly mapping relational databases to RDF and OWL* (WWW 2012). It formalises *information preservation* and *query preservation* for direct mappings, which are close to the paper's round-trip and query laws. It is the natural theoretical anchor for §3.2 *(verify exact formulation)*.

### 2.2 [Major] SHACL closes the world only for focus nodes

`sh:closed true` restricts which predicates a **focus node** may carry. A triple whose subject no shape targets is untouched by validation, so it validates. Such triples are in $\mathrm{Valid}(\mathcal{S})$ but no M-rule encodes them, and the round-trip law fails on them.

The compilability contract therefore needs a **coverage condition**: every subject in $G$ is a focus node of some closed compiled shape, or a vocabulary concept, or the graph is rejected. Further gaps in the same family:

- **Complex paths.** The rules assume `sh:path` is a simple predicate. Inverse, sequence and alternative paths need a rule or a refusal.
- **Logical constraints.** `sh:or`, `sh:xone`, `sh:not`, `sh:qualifiedValueShape` and `sh:node` have no rules. The compilability check must name and refuse them.
- **Severity.** `sh:conforms` is false whenever *any* result exists, whatever its severity. A graph with only `sh:Warning` results is therefore non-conforming and would be rejected at load. In O2, where RDF is authoritative and may legitimately hold draft or warning-level data, the projection cannot be built for that data. A policy is needed.
- **Targets other than `sh:targetClass`** (`sh:targetSubjectsOf`, `sh:targetNode`) are not discussed.

**Unverified assumption at the heart of the verdict.** The whole design presumes that LATTICE's shapes are, in practice, closed with bounded `maxCount`. The paper never measures this. A census is cheap — a script over the shapes graphs counting `sh:closed`, path kinds, logical constraints and unbounded counts — and it determines how much of a deployment is compilable at all. It should precede RS-D1 (proposed as RS-X0, §11).

### 2.3 [Major] The paper changes OWL semantics without saying so

Compiling OWL axioms into constraints is a closed-world, unique-name reading. That is fine, but it is a *semantic change* and belongs in §4.4:

| Axiom | OWL meaning | Compiled meaning |
|---|---|---|
| `owl:FunctionalProperty`, two distinct values | infer the two values are `owl:sameAs` | reject (`UNIQUE` / single column) |
| `owl:hasKey` | infer the two individuals are the same (named individuals only) | reject (`UNIQUE`) |
| `rdfs:domain` / `rdfs:range` | *infer* the type of subject/object | §3.4 treats them as compile-time constraints |
| `owl:someValuesFrom` | the existence of a value, possibly unnamed | dropped (§7.6), fine, but stated |

The inference law (§3.2) has a related problem. If $P^\infty(G)$ derives triples on closed focus nodes that the shapes do not allow, then $\mathrm{enc}(P^\infty(G))$ is undefined. The law needs the precondition $P^\infty(G) \in \mathrm{Valid}(\mathcal{S})$, or must restrict $P$ to rules whose heads are compiled relations. OWL 2 RL's equality rules (`eq-*`) cannot be views at all; they need merging.

### 2.4 [Major] The NULL-as-Undetermined encoding has more than two hazards, and conflates two meanings

That SQL's `AND`/`OR`/`NOT` follow strong Kleene logic is correct (fact). But NULL behaves non-Kleene almost everywhere else. Each of these silently turns Undetermined into something else:

| Construct | Behaviour on NULL | Effect |
|---|---|---|
| `WHERE`, `JOIN … ON` | NULL treated as false | Undetermined → Denied (paper lists this) |
| `bool_and`/`bool_or` | NULL ignored; **empty input returns NULL** | paper lists the first half only |
| `CASE WHEN c THEN …` | NULL condition falls to the next branch or `ELSE` | the paper's own quantifier `CASE` is correct only because of this (see below) |
| `CHECK (c)` | NULL **passes** | an eligibility predicate in a `CHECK` accepts Undetermined |
| PL/pgSQL `IF c THEN` | NULL treated as false | generated function bodies |
| `NOT IN (…)` with a NULL element | always NULL | "not in excluded set" becomes Undetermined |
| `COALESCE`, `IS DISTINCT FROM`, `GROUP BY`, `DISTINCT` | NULLs treated as equal / replaced | grouping decisions merges Undetermined with itself (fine) but `COALESCE(x, false)` in hand-written reports is the classic error |
| `STRICT` functions | NULL in → NULL out without running | a strict guard function never runs on missing evidence |
| BI tools, ORMs | NULL ≈ "no data" | the §13 audience will misread Undetermined |

**The quantifier `CASE` is right for a fragile reason.** For the empty set, `bool_or(...)` returns NULL, both `WHEN` branches are skipped, and `ELSE` yields TRUE (EveryValue) or FALSE (SomeValue). Those are the correct empty-set answers, assuming Eligibility defines them that way. RS-X3 is right to check.

**The hazard that bites in practice is `LEFT JOIN` padding.** §7.5 recommends `LEFT JOIN` so that zero matches yield a row. Quantifying over a `LEFT JOIN`ed evidence set turns *empty evidence* into *one NULL row*. EveryValue then returns NULL (Undetermined) instead of TRUE. The two pieces of advice in the paper contradict each other.

**Conflation of meanings.** NULL also means "column has no value", which under M13 (`minCount 0`) is a *closed-world known absence*. `ExactMatch` on such a column yields Undetermined. Whether "known to have no value" should be Undetermined or Denied is an Eligibility-law question the paper silently answers. It is exactly the open-/closed-world tension of §3.1, resurfacing.

**Recommendation.** Separate the *computation* encoding (boolean/NULL inside generated expressions, always consumed with `IS TRUE`/`IS FALSE`/`IS NULL`) from the *storage and exposure* encoding (a non-null `decision` column referencing the three Eligibility concepts). Stored and exposed decisions must never be NULL. This also fixes the R2RML problem in §5.3.

### 2.5 [Moderate] §3.3's normalisation theory is decorative

The paper cites Bernstein's synthesis, but no M-rule uses it. The rules are standard ER/ORM mapping. Two options:

- drop the claim to "fifty years of theory" as justification;
- or actually use the FD set: check that each generated table is in 3NF/BCNF with respect to the shape-derived FDs.

The second is a cheap, mechanical check (§10.5).

Note also that `sh:maxCount 1` gives an FD *per target class*. A property shared across classes with different counts yields different FDs per table. That is fine, but it means `owl:FunctionalProperty` ("globally") and SHACL can disagree, and the compilability check should flag the disagreement.

---

## 3. Rule-level defects

| Rule | Problem | Severity | Fix |
|---|---|---|---|
| **M5** `xsd:dateTime → timestamptz` | the offset is lost. A zone-less `xsd:dateTime` (allowed by XSD) is *interpreted in the session time zone*, which changes its meaning, not just its lexical form | Major | require a timezone via the shape, or use `timestamp` plus an offset column. State round trip at value-space level |
| **M5** `xsd:duration → interval` | PostgreSQL compares `'1 mon' = '30 days'` as TRUE. XSD durations are only partially ordered, and `P1M`/`P30D` are incomparable. This affects `UNIQUE`, joins and equality matches | Moderate | store `(months, seconds)` separately, or refuse duration equality |
| **M5/M14** numeric literals | RDF 1.1 literal equality is lexical, so `"1.0"^^xsd:decimal` and `"1.00"^^xsd:decimal` are distinct triples. `UNIQUE (owner_id, value)` on `numeric` treats them as equal and **rejects a valid graph**. `"01"^^xsd:integer` round-trips as `"1"` | Major | state the round-trip law modulo canonical lexical forms (value-space equality), and decide whether non-canonical literals are rejected at load |
| **M10** superclass = `UNION ALL` view | conflicts with M7/M8, where a parent table already exists. Under M9 (non-disjoint), `UNION ALL` yields duplicate rows, breaking set semantics. A concrete superclass with its own instances has no table | Moderate | apply M10 only to M9/abstract cases, using `UNION` or the type table |
| **M12** "nothing needed under M8 when the hierarchy is a tree" | **wrong.** Child primary key = parent foreign key does not stop one parent id appearing in two sibling child tables. Disjointness needs a parent discriminator plus a composite foreign key `(id, kind)` from each child, or a trigger | Major | as stated; also a good first Alloy check (§10.3) |
| **M13–M17** | `sh:minCount ≥ 1` on a child or association table (M14/M17), and bounded `sh:maxCount n > 1`, have no rule. Neither is expressible as `NOT NULL`/`UNIQUE`. Both need M28b deferred count triggers. Appendix A's `ex:peril` (`minCount 1`) is exactly this case and is not enforced | Major | add explicit rules; test at zero and at n+1 |
| **M21** `CHECK (a_id < b_id)` | excludes reflexive symmetric pairs (`x p x`) | Minor | `<=` |
| **M22** recursive views | cyclic data (`skos:broader` cycles are easy, per the earlier Alloy counterexample) needs `UNION` (not `UNION ALL`) or the `CYCLE` clause. Maintaining a closure table under *deletes* is the hard case (cf. DRed), not insert | Moderate | specify the cycle policy; restrict trigger-maintained closures to insert-only or full recompute |
| **M24** `sh:in` / scheme value → FK to concept table | `sh:in` lists of *literals* need `CHECK … IN`. An FK to `voc.concept` does not restrict *which scheme*. ADR-A85 resolution is per contract per context, so the admissible set varies by row and cannot be a static FK | Major | composite FK `(concept_id, scheme_id)` for static schemes; for resolved schemes, a deferred trigger or guard calling the resolution function |
| **M26** regex translation | right policy. Also note `sh:flags`, XPath-only classes (`\i`, `\c`, Unicode blocks) and that both `sh:pattern` and POSIX `~` are unanchored | Moderate | validate translation equivalence mechanically (§10.4) |
| **M27** `sh:class` → FK to "the superclass view's base table" | PostgreSQL cannot place a foreign key on a view. Under M7/M8 the target table exists; under M9/M10 polymorphic references need a supertype key table | Major | a per-hierarchy key table, or refuse |
| **M28** SHACL-SPARQL to SQL | requires a SPARQL→SQL translator and a static scope analysis of arbitrary SPARQL. Neither is in §16's estimate. PostgreSQL `CHECK` cannot contain subqueries, so M28a covers only queries that reduce to a row predicate | Major (cost) | budget it, or reuse Ontop's SPARQL→SQL machinery; refuse whatever the analysis cannot classify |
| **M28b** deferred constraint triggers | do not fire when `session_replication_role = replica`, which is the logical replication apply default. Bypassed by `COPY`/bulk paths if triggers are disabled. Unsound under concurrency unless writes serialise (§4.3) | Major | §4.3; document replica behaviour |
| **M30** `extras jsonb` | **contradicts `sh:closed`**: a closed shape rejects unknown properties, so extras cannot exist in $\mathrm{Valid}(\mathcal{S})$. Enabling M30 means the shape is not closed, which removes the §3.2 basis. "Best-effort" round trip also contradicts the round-trip law | Moderate | define M30 classes as explicitly outside the round-trip law, with shapes using `sh:ignoredProperties` or non-closed shapes |
| **M34** truncation with hash | fine. Note §6.3 determinism and §11.2 name stability make outputs depend on the *previous* IR, so "same inputs" must include it | Minor | state it |
| **M48** `UNIQUE` with scope columns | PostgreSQL treats NULLs as distinct by default. Nullable scope columns silently stop enforcing uniqueness | Major | `NULLS NOT DISTINCT` (PG 15+) or `NOT NULL` scope columns |

---

## 4. LATTICE layer mappings

### 4.1 Eligibility (§8.5)

- **[Major] Concept matching is not a boolean expression.** The Track B reference (`decide_concept_match`) shows what the SQL must encode:
  - L9: out of the resolved scheme → Undetermined, *before* exclusion;
  - L10: exclusion → Denied;
  - L14: a flat scheme under hierarchical matching;
  - L11: a candidate that is a proper ancestor of an excluded concept → Undetermined;
  - SingleValue: exactly one candidate, otherwise Undetermined.

  "A join to the concept closure table" captures none of these. The SQL backend must lower the *full* `ConceptPlan` semantics. It must be tested against `tools/reference/eligibility`, not against the SPARQL backend.
- **[Major] Wrong oracle.** RS-X3 and §12's "Kleene" row compare against the SPARQL backend. Both backends share `_expand`, so a bug shared through it is invisible. Use the reference semantics; the harness and fixtures already exist.
- **[Moderate] `ExactMatch` on multi-valued evidence** needs a quantifier, which the table does not say. `= ANY ($set)` with a NULL element returns NULL for a non-match, as the paper notes. Under `NOT`, it stays NULL.
- **Empty-set semantics.** The paper defers to RS-X3. The Isabelle theory already *defines* `some_value`/`every_value`, including the empty list, so this can be settled by reading `Eligibility.thy`, and then proved (§10.2).

### 4.2 Vocabulary (§8.2)

- **[Major] One scheme per concept.** The concept table `(id, scheme_id, …)` assigns each concept to exactly one scheme. `skos:inScheme` is many-valued, and scheme versions overlap almost entirely.
- **[Major] A global closure table is wrong.** The Alloy model in the formal-methods brief represents `broader` per scheme. A global closure table conflates hierarchies that differ by scheme, and that is exactly the disagreement Alloy found.
- **[Moderate] It predates the composition decision.** "ADR-A85 resolution precedence as a generated SQL function" predates ADR-A116 (multi-source composition, no overlapping membership). The relational design should follow ADR-A116's rule, or wait for it.

**Fix.** Use a membership table `(scheme_id, concept_id)`, `broader` keyed by scheme, and a closure per scheme.

### 4.3 Behaviour (§8.4) and the example function

| Issue | Severity |
|---|---|
| **Outcome conflation.** One `RAISE EXCEPTION` covers version conflict, state not admitting the transition, guard Denied, and guard Undetermined. §12's operation oracle compares outcomes (applied / conflict / refused), which this function cannot distinguish. It also discards the Denied/Undetermined distinction Eligibility exists to provide. Re-read with `FOR UPDATE` after a zero-row update, and raise distinct SQLSTATEs | Major |
| **Guard isolation.** `elg.decide_bind_guard` is evaluated inside the `UPDATE`'s `WHERE`. If it reads evidence outside the aggregate, then under READ COMMITTED the evidence can change and commit concurrently (write skew). PL/pgSQL functions are `VOLATILE` by default, and in READ COMMITTED each statement inside them takes its own snapshot. The guard may therefore not even see the same state as the enclosing `UPDATE`. The precise behaviour (EvalPlanQual re-checking only the target row) is subtle, which is why it should be modelled (§10.1), not reasoned about informally | Major |
| **Declarations as rows vs generated code.** §8.4 says transition definitions are rows, not DDL. The function hard-codes `'Bound'`, `'FirmQuoted'` and the guard name. Either generate per-transition functions (so declarations are compile-time, and a row change requires recompilation and a drift check) or write one generic interpreter over the rows. Pick one. Also, `bhv.state_id('Bound')` by label is ambiguous across state spaces | Moderate |
| **Missing records.** No `bhv.StateOccupancy` history, no effect rows, untyped `jsonb` stimulus. No `SET search_path` on the function (a hygiene issue, and a security issue if it ever becomes `SECURITY DEFINER`) | Minor |
| **Outbox delivery is at-least-once.** Consumer idempotency is needed and unaddressed; this is the T4 gap the formal-methods brief named | Moderate |

### 4.4 Persistence (§9)

- **[Major] Global order by sequence (M45) is a known bug.** Sequence values are assigned at insert time, not commit time. A reader polling `id > last_seen` permanently skips a row whose transaction commits after a later-numbered one.
  - The commit LSN *is* ordered.
  - Workable alternatives: logical decoding, a snapshot `xmin` horizon, or a single-writer stream.
  - This is the textbook model-checking target (§10.1).
- **[Major] Aggregate invariants under concurrency.** M28b triggers check at commit within one transaction's snapshot. Two concurrent transactions changing *different* child rows of one aggregate (for example, two participation shares) can each pass the sum check and jointly break it. This is safe only if every child write also performs the root version compare-and-set (forcing a write-write conflict) or runs under SERIALIZABLE. Generated operations probably do this; ad hoc writes and other paths do not. The rule must be stated and enforced, for example by revoking direct DML on child tables.
- **[Moderate] Combinations that must be refused.** `AppendOnly` (revoked `DELETE`) combined with `PerSubjectGraphDrop` erasure is one. `privacyClass` on append-only data should force `CryptoShred`. The persistence compiler already refuses invalid combinations (§9's table notes that it "refuses invalid combinations"), so the relational compiler should inherit that refusal list and add the combinations that only become invalid in SQL. Candidates:
  - `AppendOnly` with any erasure strategy other than `CryptoShred`;
  - `PatchLog` or `SnapshotPerRevision` receipts on a class with `privacyClass` set, unless the history tables are also covered by the erasure strategy (see the next bullet);
  - `Optimistic` concurrency on a class whose aggregate invariants are M28b triggers, unless every child write performs the root version compare-and-set (§4.3 above);
  - `minConcurrencyLevel` below SERIALIZABLE on any operation whose guard reads outside its aggregate.

  These are cheap, declarative, compile-time checks, and they belong in the compilability step (pipeline step 2).

- **[Major] Erasure in SQL reaches further than the table rows.** M50 deletes rows or keys. Personal data also persists in:
  - **History.** PatchLog `delta jsonb`, history tables and receipt tables.
  - **The outbox.** `fire_bind` copies the whole `p_stimulus` into `outbox.event.payload`.
  - **Change capture.** Logical decoding slots and every downstream CDC consumer (Debezium topics are retained independently).
  - **Recovery and replication.** WAL archives and PITR base backups, which by design contain deleted rows until they expire. Also streaming replicas and any O2 RDF source the projection was built from.
  - **Encryption keys.** With `pgcrypto`, encryption happens *in the server*. Plaintext therefore crosses the connection and appears in statement logs if `log_statement` or `auto_explain` capture parameters. Keys stored in the same database share its backups, so shredding the live key does not shred the backed-up copy.

  `CryptoShred` survives backups only if keys are held outside the database's backup domain, and only if encryption happens in the application or with keys fetched per operation. The paper should state an erasure *boundary*: which stores erasure covers, and with what latency (for example "after backup retention expires"). This is a legal property as much as a technical one, and it is the strongest argument in the paper for an explicit model (§10.1, model F).

- **[Moderate] Epoch fencing (M47)** is described in one line. Fencing works only if *every* write path compares the epoch. That includes triggers, Surface promotions and the outbox relay, not just generated operations. This is another protocol property to check by model, not by inspection.

- **[Moderate] Content-addressed identity (M49, R5)** is computed in the application, so the database cannot verify it. A row with a wrong hash is accepted. Either verify at load in the loader, on the same code path as the round-trip test, or record that this identity class is *trusted input*. The round-trip test catches drift only on generated data, not on production writes.

### 4.5 Party and Quantification (§8.3)

- **[Major] Range canonicalisation loses information (the item flagged in the summary).**
  - **Discrete ranges.** PostgreSQL canonicalises discrete range types (`int4range`, `int8range`, `daterange`) to `[)`. `int8range(1, 5, '[]')` is stored and returned as `[1,6)` (fact). The `qnt:Bound` closure flags and bound values therefore do not round-trip as authored, only up to value-space equivalence.
  - **Empty ranges.** Every empty range normalises to `empty` and loses its bounds (fact). A `qnt:Range` such as `(5,5)` that is semantically empty but carries authored bounds cannot be reconstructed.
  - **Continuous ranges.** `numrange` and `tstzrange` keep the flags, so the problem is limited to discrete types and empty ranges.

  The round-trip law must say which equivalence it uses. Either the ontology already treats `[1,5]` and `[1,6)` over integers as the same `qnt:Range`, or it does not, and then discrete value spaces need explicit bound columns. The question is for the Quantification README. It is a good SMT target (§10.4).

- **[Moderate] Unbounded and infinite bounds.** PostgreSQL distinguishes an omitted bound from `infinity` for timestamp and numeric types, and they behave differently. The mapping from `qnt:` unboundedness needs stating.

- **[Moderate] Party share sums (M28b).** This has the concurrency problem of §4.3. It also needs a precision rule: is "sum to the declared total" exact `numeric` equality or within a tolerance? The ontology should say which, rather than leaving it to the trigger author.

- **[Minor] The `EXCLUDE` constraint in the §8.1 example.**
  - It is keyed on `(role_id, actor_id)`. It prevents the *same actor* holding the same role twice concurrently, and permits a role to have several concurrent occupants.
  - With `actor_id` nullable, vacant (contingent) occupancies never conflict, because `NULL = NULL` is not true. That may be intended.
  - The text above the example describes a different invariant ("validity periods for one identity cannot overlap").

  Which invariant does Party actually state? A single-occupant role would need `EXCLUDE (role_id WITH =, valid_period WITH &&)`.

- **[Minor] Temporal model.** `fnd:Version` (a version table plus a `current_*` view) and `fnd:TemporalScope` (valid time) together imply a bitemporal model: transaction time from versions or history, valid time from ranges. The paper never says whether queries are bitemporal, or what "current" means when a newer version has a future validity period.

### 4.6 Instrument, Wording, Surface and MORK (§8.6–§8.8)

- **[Moderate] `ltree` path columns** (§8.2, §8.6) need relabelling of the whole subtree whenever a node moves. Maintaining them by trigger is the same delete/move problem as M22. `ltree` labels are also restricted (alphanumerics and underscore; recent versions add hyphens *(verify)*), so encode them from ids, not names.
- **[Moderate] Surface promotions maintained by trigger** inherit the concurrency issue. Two transactions updating sources of the same promoted value can leave it stale unless they serialise on the aggregate root.
  - `REFRESH MATERIALIZED VIEW CONCURRENTLY` needs a unique index on the view.
  - It is a full recomputation, not an incremental one.
  - The freshness rules of paper 4 §19.5 must therefore assume refresh cost proportional to the view, not to the change.
- **[Minor] Generated derived columns** such as `span` in Appendix A are not ontology properties. The R2RML emitter must exclude them, or they appear as extra triples and break the round trip.
- **[Minor] MORK.** Deferral is reasonable. Note that `COPY` and bulk ingestion paths are where triggers are most often disabled for speed. Any relational ingestion emitter must keep M28b triggers enabled, or must re-validate afterwards.

---

## 5. Keeping an RDF view (§10)

### 5.1 [Major] The worked example's round trip fails

- **Subject IRIs.** M2 stores `iri text UNIQUE NOT NULL`. The §10 R2RML maps subjects with `rr:template "https://example.org/contract/{id}"`, which mints a *new* IRI from the surrogate key. Every subject IRI in the RDF view therefore differs from the source graph, and $\mathrm{dec}(\mathrm{enc}(G)) \not\cong G$. Under M2 the subject map must be `rr:column "iri"` with `rr:termType rr:IRI`. Under M3 the template must be the identity profile's own template, and that template must be injective (§10.4).
- **`current_state_id`.** Appendix A adds `current_state_id bigint NOT NULL`. A conforming `ex:Layer` under the *closed* `LayerShape` cannot carry a state property, so the loader has nothing to put there.
  - If the R2RML emits it, the view contains triples the source never had.
  - If the R2RML omits it, Behaviour state is invisible in RDF.
  - Either the shape must declare the state property (open the shape, or add the path), or the column must be documented as outside the round-trip law.

  The same applies to `version`, `provenance_id` and the `bhv:` tables.

This is the cheapest high-value finding in the review. Running the paper's own round-trip law on its own appendix would show the failure in minutes. It argues for running the laws mechanically from S0, not at RS-X1.

### 5.2 [Moderate] Limits of R2RML

- **Ordered values (M15).** An `ordinal` child table cannot be rendered as an `rdf:List` by R2RML. R2RML has no list constructor; RML extensions and some engines add one *(verify)*. If the source data uses `rdf:List`, the round trip needs RML, a post-processing step, or a refusal.
- **Language tags (M6).** R2RML supports a constant `rr:language` only. A per-row language tag needs an RML `rml:languageMap` or one triples map per language *(verify)*. Since the paper's own option is RML-capable tools (Morph-KGC, RMLMapper), say **RML** rather than R2RML wherever this matters.
- **Literal forms.** R2RML's "natural RDF literal" for `numeric` produces the *canonical* `xsd:decimal` form. This is where the §3 lexical-form issue becomes visible: `"1.00"` comes back as `"1.0"`. It reinforces stating the round trip at value-space level.
- **Blank nodes (M4).** These need `rr:termType rr:BlankNode` with a template over the child key. That is fine up to isomorphism, which the law allows.
- **Virtualisation of procedures.** Ontop virtualises reads only. Views produced by M10, M18 and M22 can be mapped too, but Ontop's rewriting over recursive views and `UNION ALL` views performs differently. RS-X5 should include a transitive query.

### 5.3 [Major] Undetermined vanishes from the RDF view

R2RML generates no triple when a column value is NULL (fact). If eligibility outcomes are ever stored or exposed as NULL, the RDF view drops the `elg:Undetermined` decision entirely. An RDF consumer then cannot tell "Undetermined" from "never evaluated", and under the open world it is free to treat the decision as unknown. That happens to look correct here, but it is wrong as a record.

This is the second reason for §2.4's recommendation: store and expose decisions as non-null references to the three Eligibility concepts, and use boolean/NULL only *inside* expressions.

### 5.4 [Moderate] Security of views and virtual graphs

- **Row-level security and views.** PostgreSQL views execute with the *view owner's* privileges by default. Since owners typically bypass RLS, the views generated by M10, M18 and Surface would **bypass row-level security** unless created `WITH (security_invoker = true)` (PG 15+, fact).
- **Other bypasses.** Table owners bypass RLS unless `FORCE ROW LEVEL SECURITY` is set. `SECURITY DEFINER` functions bypass it too.
- **Ontop.** It connects as a single database user. Tenant isolation in the RDF view therefore depends on Ontop's connection configuration, not on RLS.

The §15 claim that row-level security removes ADR-A54's objection to shared graphs holds only if these bypasses are closed and checked. That check is a catalog-level verification (§10.7).

---

## 6. Schema evolution (§11)

- **[Major] Live migration is missing.** The four change classes say whether information survives. They say nothing about *availability*.
  - In PostgreSQL, adding a `NOT NULL` column with a volatile default, changing a column type, adding a `CHECK` or foreign key without `NOT VALID`, or building an index without `CONCURRENTLY` all take strong locks. Some rewrite the whole table.
  - Restructuring from M7/M8 to M9, or folding a child table into a column, are multi-step expand/backfill/contract operations. Generated operations, triggers and the R2RML view must handle *both* shapes during the window.
  - The migration emitter needs a **phased** output, not a single file. "Use Flyway" solves running migrations, not designing them.
- **[Moderate] O2 does not need migrations.** At S1 the SQL is a rebuildable projection, so the cheapest and safest migration is "drop and rebuild". Generated migrations are needed only from S2. Deferring the migration emitter (4k lines, about 8.4M base tokens) to S2 shortens S0/S1 and lets RS-X4 run on real ontology releases.
- **[Moderate] Some cells of the change table are ambiguous.**
  - "Local name changed, IRI unchanged" cannot happen in RDF: the local name *is* part of the IRI. The row presumably means "label changed".
  - "IRI changed" is a breaking ontology change under ADR-A86 in any realisation, so an R2RML alias is a compatibility shim, not a fix.
  - "`sh:maxCount` lowered to 1 fails on existing multi-valued data": this is an ontology release declaring previously valid data invalid. ADR-A86 should classify that as breaking, and the migration should refuse rather than fail midway.
- **[Moderate] Rollback.** A lossy migration cannot be reversed by a down-migration. The policy should be "restore or roll forward", stated for S2/S3.
- **The migration law is well formed and worth keeping.** Migrating data from the old schema gives the same RDF view as loading it directly into the new one. It is a commuting square:

$$\mathrm{dec}_{\mathcal{S}'}\big(\mathrm{mig}(\mathrm{enc}_{\mathcal{S}}(G))\big) \cong \mathrm{dec}_{\mathcal{S}'}\big(\mathrm{enc}_{\mathcal{S}'}(\mathrm{up}(G))\big)$$

  Here $\mathrm{up}$ is the RDF-level data migration implied by the ontology change. The paper omits $\mathrm{up}$: for non-additive changes, "loading that data into the new schema directly" is undefined unless the old data first conforms to $\mathcal{S}'$. The law needs it stated, and it is a natural property-test target (§10.5).

---

## 7. Verification plan (§12)

| Gap | Severity | Fix |
|---|---|---|
| **No concurrency or isolation testing at all.** Every risk in §4.3–4.4 is concurrent, and the operation oracle runs histories sequentially | Major | §10.1 models plus history checking on real PostgreSQL (Elle/Jepsen style, Hermitage-style isolation probes) |
| **Constraint-preservation law absent** (§2.1) | Major | SHACL engine as oracle on generated *and mutated* graphs (§10.5) |
| **Kleene oracle is the SPARQL backend** (shared `_expand`) | Major | `tools/reference/eligibility` as oracle; SPARQL as a secondary comparison |
| **The operation oracle compares two realisations generated from the same `dal:` profile.** A misreading of a dimension is shared, which is the same circularity one level up | Moderate | state each dimension's meaning as a small TLA+/Quint model (§10.1), and use the model's traces as a third oracle for both realisations |
| **Inference law needs a reference engine independent of the compiled views.** "A reference Datalog or SPARQL engine" is right; it should not be the view generator's own rule IR evaluated another way | Moderate | a naive bottom-up evaluator over the rule text, in the spirit of Track B |
| **No security tests.** RLS bypasses (§5.4), privilege revocation for `AppendOnly`, direct DML bypassing generated operations | Major | catalog checks (§10.7) and negative tests as an unprivileged application role |
| **No check that the deployed database matches the relational IR** (dropped trigger, disabled constraint, `NOT VALID` never validated) | Moderate | catalog-versus-IR drift check (§10.7), extending R1's DDL drift check to the live catalog |
| **The levels L1–L4 are undefined in this paper** | Minor | cite their definition |
| **Mutation check is good, but three mutations is a spot check**, as the formal-methods review noted for that epic | Moderate | a mutation operator set over the relational IR, run per rule (§10.5) |

Most important: the "None needs a proof assistant" remark is true but answers the wrong question. The laws do not need a proof assistant. They do need **universally quantified checking**, bounded or proved, rather than a fixed corpus. That is what §10 provides.

---

## 8. Costs, risks, staging and the estimate

### 8.1 [Major] Missing risks

| Risk | Why it matters |
|---|---|
| **Direct SQL access bypasses the semantics.** The §13 audience will write their own `SELECT … WHERE eligible`, their own `UPDATE`s and BI joins | Generated functions protect nothing if the application role can write tables directly. Revoke DML on base tables, expose only functions and `security_invoker` views, and generate reporting views that pre-render decisions as concept labels |
| **Concurrency anomalies** (§4.3–4.4) | absent from R1–R7 |
| **Erasure boundary** (§4.4) | regulatory exposure |
| **Two systems of record at S2.** One aggregate type is SQL-authoritative while RDF still holds vocabularies, the TBox, provenance and references *to* that aggregate | No distributed transaction spans them. Referential integrity across stores becomes eventual. Vocabulary concepts must be *replicated into* SQL for M24's foreign keys, so the SQL copy can lag a vocabulary release. The paper never says that O3 implies a vocabulary synchronisation protocol |
| **The O2 feed is unspecified.** How does the SQL projection stay current: full rebuild, CDC from the RDF store, or dual writes? | Freshness, staleness indicators and the "disposable" claim all depend on this |
| **Write-path claims may not hold** | A "guarded write" in Appendix A's profile is the `UPDATE` plus a PatchLog row plus a receipt plus an outbox row plus deferred-trigger checks plus GiST `EXCLUDE` maintenance. That is far fewer operations than 20 + 3n quads, but not "one `UPDATE`". RS-X2 should measure write latency with all compiled constraints enabled |
| **PostgreSQL version floor** | the design uses PG 14 (multirange, `range_agg`), 15 (`NULLS NOT DISTINCT`, `security_invoker`) and possibly 18 (`WITHOUT OVERLAPS`; I believe temporal primary keys and `PERIOD` foreign keys shipped in 18, *verify*). Managed services lag. State the floor explicitly |

### 8.2 [Moderate] The gap query (§8.7)

The query is essentially right:
- `range_agg` ignores NULL inputs from unmatched `LEFT JOIN` rows;
- `coalesce` covers the empty case;
- multirange difference is native.

Two caveats:
- **`r.required` must be a multirange.** `numrange - numrange` raises an error when the result would be non-contiguous (fact). Declare `required` as `nummultirange`, or cast it.
- **The scenario filter is in the `ON` clause.** Keeping `c.in_scenario` there (not in `WHERE`) is correct and deliberate. Note it, since moving it to `WHERE` would silently turn the `LEFT JOIN` into an inner join and drop layers with no cover, exactly the rows a gap analysis exists to find. That makes it a good mutation-test target.

### 8.3 [Moderate] Appendix A, further points

- **`ex:validity sh:class fnd:TemporalScope`** is an *object* property. Inlining it as a `valid_period` column flattens a node into a value. That is reasonable for a value object, but it needs a rule ("owned value object with `maxCount 1` → inline columns, decoded as a blank node"), and no such rule appears in M1–M36.
- **`ex:peril sh:minCount 1`** is not enforced (§3, M14).
- **No scheme restriction on `ex:peril`.** `sh:class skos:Concept` names no scheme, so any concept is accepted. If the real shape names a scheme, M24's static-scheme foreign key applies.
- **`layer_change` blocks deletion.** It references `tower.layer` without `ON DELETE CASCADE`, so deleting a layer fails. Whether history should survive deletion is an erasure-policy question (§4.4).
- **`"limit"` is quoted.** M33 needs a reserved-word rule.
- **`tower.quote` lacks columns.** It has no `version`, no `provenance_id` and no state. It sits inside Layer's aggregate (`CompositePropertyBoundary`), so it is versioned through the root. Then every quote write must bump the layer's version, which is the §4.4 rule in action. Show that in the example.

### 8.4 The token estimate

The arithmetic checks:
- 38k R × 2.10 = 79.8M;
- 4k D × 1.02 ≈ 4.1M;
- 32 × 0.64 + 3 × 1.53 + 3.06 = 28.1M;
- total 112.0M; ×1.5 = 168M; ×2.5 = 280M;
- 168/380 ≈ 44%, matching "roughly 45%".

Three issues:
- **The "G" columns are not defined in this paper.** The Base G / Base E ratio also differs by row (3.17, 3.0, 3.10). Either define G or drop it.
- **Underestimated scope.** M28's SPARQL-to-SQL translation and scope analysis, a phased-migration emitter, the concurrency and security test suites, and the S2 vocabulary-synchronisation protocol are all missing or under-sized. My rough judgement is that these add 15–25% to code and tests.
- **The excluded recurring migration cost** is the paper's own "principal ongoing cost" (§11.1). It should be estimated per ontology release, even roughly, or the 45% comparison with paper 3 is not like-for-like.

---

## 9. Decisions for the maintainer (§17): proposed changes

| # | Change |
|---|---|
| RS-D1 | Make it conditional on RS-X0 (shape census) showing that the compilable fraction of a real deployment is large enough |
| RS-D2 | Keep (a). Add: compilability requires the focus-node coverage condition of §2.2 |
| **RS-D10 (new)** | Decision encoding: boolean/NULL inside expressions only; stored and exposed decisions are non-null concept references (§2.4, §5.3) |
| **RS-D11 (new)** | Default isolation and write discipline: every write to an aggregate goes through the root's version compare-and-set; DML on base tables revoked from the application role; SERIALIZABLE for cross-aggregate guards |
| **RS-D12 (new)** | Literal policy: round trip at value-space level, with non-canonical lexical forms either accepted and canonicalised, or rejected at load |
| **RS-D13 (new)** | Vocabulary placement in O3: RDF authoritative, compiled into SQL reference tables by release, with a stated staleness bound; or SQL authoritative for vocabularies too |
| **RS-D14 (new)** | Erasure boundary: which stores, which latency, where keys live |
| RS-D9 | Keep. G0 should also run the §10.1 history checks, not just performance |

---

## 10. Applying formal methods to this work

### 10.0 Principles

1. **Verify each output, not the compiler.** A verified compiler in the CompCert sense is out of proportion to G5. **Translation validation** (Pnueli et al. 1998; Necula 2000) gives most of the assurance at a fraction of the cost. For each compiled module, an independent checker confirms that *this* output satisfies the laws for *these* inputs. The Python compiler stays unverified. Its outputs do not.
2. **Each law gets the cheapest technique that can establish it universally**, in bounded or proved form, as in the earlier epic's rung ladder.
3. **Reuse what already exists:**
   - the Eligibility reference semantics (Track B);
   - the Isabelle Kleene theory (Track E);
   - the Alloy scheme-composition model (Track C);
   - the claim/gate discipline and the freshness checker.
4. **Protocols are where the unexamined risk lies.** This paper is the natural trigger for rung T4, which the formal-methods brief listed as never attempted.
5. **Avoid the earlier epic's own weaknesses.** The independence of each oracle must be stated, the digests must cover definitions, and a fault must be seeded in the *implementation*, not only in the reference.

| Law or property | Technique | Rung | Independence of the oracle |
|---|---|---|---|
| Kleene encoding, quantifiers, empty sets | Isabelle extension | T5 | proof against `Eligibility.thy` definitions |
| Eligibility SQL backend (full concept matching) | differential, bounded-exhaustive | T0 | `tools/reference/eligibility`, which does not import the IR |
| Schema admits exactly the shapes' instances | Alloy translation validation | T2 | Alloy model generated from the *shapes*, separately from one generated from the *relational IR* |
| Regex, IRI templates, range bounds, numeric facets | SMT / automata | T3 | solver |
| Constraint preservation, round trip, query, inference, migration | property-based and metamorphic | T1 | pySHACL, an independent SPARQL engine, a naive Datalog evaluator |
| Isolation, ordering, outbox, erasure, fencing, cutover | TLA+/Quint | T4 | model, then history checking on real PostgreSQL |
| Deployed catalog equals relational IR; live invariants | runtime and catalog checks | T7 | PostgreSQL system catalogs |

### 10.1 T4: protocol models (TLA+ or Quint)

The isolation level must be part of the model. Model PostgreSQL's READ COMMITTED (per-statement snapshots, row re-check on update) and SERIALIZABLE (SSI) abstractly at the level of read and write sets, not SQL. Published TLA+ specifications of snapshot isolation and SSI exist and can be adapted *(verify current sources)*. Seven small models, each a few hundred lines:

| Model | System | Properties (safety S, liveness L) | Expected finding |
|---|---|---|---|
| **A. Guarded transition** | `fire_bind`: version CAS, state check, guard over evidence possibly outside the aggregate, outbox insert | S: a committed transition's guard was Permitted in a state consistent with the commit (no write skew). S: every committed transition has exactly one outbox row. S: failure outcomes are distinguishable | write skew under READ COMMITTED when the guard reads external evidence; confirms RS-D11 |
| **B. Aggregate invariant** | concurrent writes to child rows of one aggregate with an M28b deferred check (shares summing to a total) | S: the invariant holds in every committed state | violation unless every child write also performs the root CAS, or under SERIALIZABLE |
| **C. Ordered stream (M45)** | sequence allocation, commit order, a polling reader | S: the reader never permanently skips a committed row. L: every committed row is eventually read | skip with plain sequences; passes with an LSN or `xmin`-horizon reader |
| **D. Outbox** | in-transaction outbox insert, relay, at-least-once delivery, consumer with an idempotency key | S: effects are applied at most once per event. L: every committed event is eventually applied | double application without consumer idempotency |
| **E. O2 projection** | RDF source, change feed or rebuild, SQL projection, readers | S: readers never see a state mixing two source versions within one aggregate. L: freshness bound under fair scheduling | depends on the unspecified feed; forces the paper to specify it |
| **F. Erasure** | live rows, history, outbox, CDC consumers, replicas, backups, key store | S: after erasure completes plus the retention bound, no store yields the subject's plaintext | finds every store §4.4 lists; tests whether `CryptoShred` survives backups given key placement |
| **G. S2 cutover** | moving one aggregate type's write path from RDF to SQL while both are live | S: no write lost or applied twice across the switch. S: no reader sees regressions | the dual-write window is the classic failure; produces the cutover runbook |

**Grounding the models.** A model of PostgreSQL is only as good as its fidelity, so check the model against reality:
- Run the generated operations on real PostgreSQL under randomised concurrent histories and check the recorded histories for isolation anomalies with an Elle-style checker (Kingsbury and Alvaro, VLDB 2020).
- Run Hermitage-style probes (Kleppmann's isolation test suite) for the specific anomalies each model predicts.

A predicted anomaly that appears in the history confirms the model; one the model rules out but the history shows means the model is wrong. This is the T4 analogue of the earlier epic's seeded mutations.

**Cost and payoff.** These models are the highest expected value in this section: concurrency defects are where the paper is weakest, and they are the defects tests find least. Models A–D should gate S2. E gates S1. F gates any deployment holding personal data. G gates each S2 cutover.

### 10.2 T5: extend the Isabelle Eligibility theory

This is cheap because the theory and its gate discipline already exist. Add a theory `SqlEncoding.thy`:

```isabelle
type_synonym sql3 = "bool option"          (* None = SQL NULL / UNKNOWN *)

fun enc :: "decision ⇒ sql3" where
  "enc Permitted = Some True" | "enc Denied = Some False" | "enc Undetermined = None"

(* SQL standard AND / OR / NOT on bool option, written from the standard's truth tables *)
fun sql_and :: "sql3 ⇒ sql3 ⇒ sql3" where ...
fun sql_not :: "sql3 ⇒ sql3" where ...

(* bool_or: NULL-ignoring, NULL on empty or all-NULL input *)
definition sql_bool_or :: "sql3 list ⇒ sql3" where ...

(* the paper's CASE encoding of EveryValue, with CASE skipping NULL conditions *)
definition every_case :: "sql3 list ⇒ sql3" where ...
```

Gated claims:
- **Homomorphism.** `enc (and3 a b) = sql_and (enc a) (enc b)`, and the same for `or3` and `neg3`. This states, as a theorem, the paper's "maps onto it exactly".
- **Quantifier correctness.** `every_case (map enc xs) = enc (every_value xs)`, and the same for `some_value`, *including* `xs = []`. This settles RS-X3's open empty-set question by proof rather than by test.
- **Negative lemmas, mirroring the De Morgan witness.**
  - `∃xs. sql_bool_and (map enc xs) ≠ enc (every_value xs)`, with witness `[Permitted, Undetermined]`.
  - The `LEFT JOIN` padding lemma: `every_case [None] ≠ enc (every_value [])`.

  These make each hazard the paper names, plus the one it misses (§2.4), a proved fact, so a reverted fix fails the build.
- **Consumption.** `IS TRUE` / `IS FALSE` / `IS NULL` partition `sql3`. A `CHECK` predicate admits `None`, so a lemma that `CHECK` acceptance ≠ Permitted documents why decisions must not be enforced through `CHECK`.

**Two lessons from the earlier review apply directly:**
- The truth tables for `sql_and` and the others must be **gated**, and preferably generated from a README table, because the definitions carry the semantics (formal-methods review §2.1–2.2).
- Use kernel-checked methods (`simp`, `cases`, `induction`), not `eval`.

**Limits.** This proves the *encoding*, not the generated SQL text. The link to the text is §10.5's differential testing, which uses the same lemmas as properties. The proved lemmas thus become the test oracle for the implementation, which is the missing proof-to-implementation link the earlier review identified.

**Out of scope for proof here:** concept matching in SQL. Its oracle is the Python reference. Mechanising `decide_concept_match` in Isabelle is Track E's own next step, and it would then serve both backends.

### 10.3 T2: Alloy translation validation

Two uses, rule-level and deployment-level.

**(a) Rule-level models, once, by hand.** For each mapping rule, model the RDF side (focus nodes, properties, cardinalities, class membership) and the relational side (tables, keys, foreign keys, `CHECK`s, triggers as invariants), with $\mathrm{enc}$ as a relation between them. Then check:

```alloy
assert ConstraintPreservation {
  all g: Graph | (some d: DB | enc[g, d] and d.satisfiesSchema) iff g.conformsTo[Shapes]
}
assert RoundTrip { all g: Graph, d: DB | enc[g, d] implies dec[d] = g }
```

Bounded at scope 4–5, this finds at once several defects this review found by hand:

| Rule | Counterexample Alloy would produce |
|---|---|
| M12 under M8 | one parent id in two sibling child tables |
| M14/M17 with `minCount ≥ 1` | an owner with zero child rows accepted |
| M21 | a reflexive symmetric pair rejected |
| M10 under M9 | duplicate rows in the superclass view |
| M24 with ADR-A85 resolution | a concept from a non-resolved scheme accepted |
| M27 under M9 | a dangling polymorphic reference |
| §8.2 concept table | a concept in two schemes cannot be represented; a global closure merges two schemes' hierarchies |

The last item extends `SchemeComposition.als` directly. Add the relational encoding to the existing model and check that per-scheme `broader` survives encoding.

**(b) Deployment-level, generated per compile.** Emit two Alloy modules per compiled module: one generated from the **shapes**, one from the **relational IR**. Both modules must be generated by code paths that share nothing beyond the parsed RDF; otherwise the check is circular. Then check the equivalence assertion at bounded scope.

This is translation validation proper. A wrong decision procedure (M7 vs M8 vs M9) or a missed constraint shows up as a counterexample for that deployment's shapes. Datatypes are abstracted to uninterpreted atoms; their facets go to §10.4. Run it in CI on every compile, with the receipt recorded as a claim (§10.6).

**Limits.** Alloy is bounded and abstracts datatypes. It complements, and does not replace, the property tests over real data in §10.5.

### 10.4 T3: SMT and automata for the value-level rules

| Target | Check | Tool |
|---|---|---|
| **M26 regex translation** | XPath pattern and translated POSIX pattern accept the same language. Both are regular for the supported subset, so equivalence is decidable by automata, and exact. Anchoring and `sh:flags` are included | an automata library; Z3's string/regex theory as a second opinion |
| **M3 IRI templates** | the template is injective over the key domain, and the R2RML/RML inverse parses every generated IRI back to the same key (no separator ambiguity, correct percent-encoding) | Z3 strings |
| **M5 integer bounds** | shape bounds on `xsd:integer` fit `bigint`; otherwise `numeric` | LIA |
| **M25 numeric facets** | generated `CHECK` admits exactly the shape's interval, including exclusive bounds | LRA |
| **§8.3 range canonicalisation** | for discrete value spaces, ∀x. x ∈ qnt-range ⇔ x ∈ PG-range after canonicalisation, with empty ranges a separate case | LIA |
| **M34 names** | no collision after truncation and hashing within one schema (direct enumeration is enough; listed for completeness) | none needed |
| **M28a classification** | a SHACL-SPARQL constraint classified as row scope references only the focus row's columns | static analysis; SMT only if the predicate needs simplifying |

Each is a small, local, fully automatic check run per compile. Together they cover the rules where "untranslatable is refused, never approximated" is the stated policy and needs enforcing.

### 10.5 T0/T1: differential, property-based and metamorphic testing

| Law | Generator | Oracle | Notes |
|---|---|---|---|
| **Constraint preservation** (§2.1) | shape-conforming graphs (paper 4 §11), then *mutated* by one edit each: drop a required value, add a second value, wrong datatype, unknown property, cross-type reference, cycle | pySHACL `conforms` | the main test the paper lacks; each mutation is labelled with the rule it targets |
| **Round trip** | same generators | RDFC-1.0 canonicalisation after value-space normalisation of literals | the law stated at value level (§3, RS-D12) |
| **Query law** | the compiled workload's queries over generated data | an independent SPARQL engine (Oxigraph and Jena, not the one the persistence compiler targets) | for the more complex translations, formal SQL semantics work (Guagliardo and Libkin, VLDB 2017) and SQL equivalence checkers can be used selectively *(verify maturity)* |
| **Inference law** | generated ABoxes | naive bottom-up evaluator over the rule text | includes cycles, for M22 |
| **Eligibility SQL backend** | bounded-exhaustive: every scheme with up to 3–4 concepts, every required and excluded subset, both match modes, inside and outside the scheme, zero, one and two candidates | `tools/reference/eligibility` | add the SQL backend as a fifth backend in the existing harness |
| **Kleene lemmas as properties** | random decision lists | the §10.2 lemmas evaluated against generated SQL on PostgreSQL | the proof-to-implementation link |
| **Migration square** | data under $\mathcal{S}$, a sampled ontology change | both paths of the square in §6 | needs $\mathrm{up}$ to be defined |
| **Metamorphic** | any of the above | the relation itself | e.g. reordering input triples leaves outputs unchanged; adding an unrelated aggregate leaves another's decisions unchanged; compiling twice gives byte-identical output (§6.3 determinism); renaming via M36 preserves the RDF view |

**Mutation operators over the relational IR**, run per rule, each of which must fail a named test:
- drop a `CHECK`, `NOT NULL`, `UNIQUE` or foreign key;
- omit `NULLS NOT DISTINCT`;
- remove the version predicate;
- replace the quantifier `CASE` with `bool_and`;
- consume a predicate bare in `WHERE`;
- move `in_scenario` from `ON` to `WHERE`;
- make a view `security_invoker = false`;
- disable a constraint trigger.

**Seed faults in the compiler and IR, not only in the outputs.** This is the earlier review's §3.1 finding applied here. At least once per rule group, introduce a bug in the Python rule implementation and confirm the Alloy validation (§10.3) or a property test catches it.

**Make the Kleene hazard impossible by construction.** Give the relational IR a distinct `decision3` type, separate from `bool`. The emitter refuses to place a `decision3` expression in a `WHERE`, `ON`, `CHECK`, `IF` or aggregate except through `IS TRUE` / `IS FALSE` / `IS NULL` or the generated quantifier templates. A typed IR is a formal method costing a few hundred lines, and it removes a whole class of defect rather than testing for it.

**Mechanical normal-form check (§2.5).** From the shape- and OWL-derived functional dependencies, check that each generated table is in 3NF (or BCNF). It is a small algorithm and turns §3.3's appeal to theory into a check.

### 10.6 Claims, gates and coverage

Extend the earlier epic's discipline to the M-rules:
- **One claim record per rule**, `claims/M12.json` and so on. Each names the statement it guarantees, the checks establishing it (Alloy assertion, SMT check, property test, mutation operator) and the latest outcome.
- **Digests cover definitions.** The digest covers the rule's specification *and* the generator code that implements it. A behavioural change to M12's implementation is then a reviewable event. This is the definition-coverage fix from the earlier review's §2.1.
- **Rule coverage from `COMMENT ON` (M35).** Every emitted object cites its producing rule. A coverage report lists, per deployment, which rules produced artefacts and which of those have green claims. A rule that produced output but has no passing check fails the gate.
- **Freshness checker.** Extend `check_formal_freshness.py` so that every M-rule ID in the paper's catalogue appears in at least one check, or is explicitly disclaimed. Also bind each rule to a check that fails under that rule's mutation operator, not just to a name, which addresses the textual-heuristic weakness raised in the earlier review's answer to its Q4.

### 10.7 T7: runtime and catalog verification

From S2 onwards, the same invariants become monitors:
- **Catalog equals relational IR.** Query `pg_constraint`, `pg_trigger`, `pg_index`, `pg_class` and `pg_policy` and compare them with the compiled IR. The check fails on:
  - a disabled trigger (`tgenabled`);
  - a `NOT VALID` constraint never validated;
  - a missing index or policy;
  - a view without `security_invoker`;
  - a table without `FORCE ROW LEVEL SECURITY`;
  - application roles with DML on base tables or `BYPASSRLS`;
  - `session_replication_role` misuse.

  This extends R1's drift check from DDL text to the live database, and it is cheap.
- **Detective invariants.** M28c validation views already exist. Run them on a schedule and route violations to the `onViolation` handling.
- **O2/O3 reconciliation.** Periodically compute the RDF view of a sample of aggregates through R2RML and compare it with the RDF source (O2) or the RDF store's references (O3). This is the round-trip law applied to production data.
- **History checking in staging.** Run Elle-style checks continuously against the staging workload, not only during development.
- **Erasure audit.** After each erasure, probe every store in model F's list for the subject's identifiers.

### 10.8 Placement in the epic and cost

| Item | Track (from the formal-methods epic) | Rough size | Base tokens (paper's model, class R) |
|---|---|---|---|
| Isabelle `SqlEncoding.thy` (§10.2) | E | ~0.5k lines | ~1.1M |
| Alloy rule-level models (§10.3a) | C | ~1k lines | ~2.1M |
| Alloy per-compile generator and checker (§10.3b) | C/B | ~2.5k lines | ~5.3M |
| SMT and automata checks (§10.4) | C (C3 already scopes SMT) | ~1.5k lines | ~3.2M |
| TLA+/Quint models A–G plus history harness (§10.1) | G (protocols) | ~2.5k lines | ~5.3M |
| Typed IR, normal-form check, catalog drift check (§10.5, §10.7) | A/F | ~1k lines | ~2.1M |
| **Total** | | **~9k lines** | **~19M base, ~28M expected** |

That is about 17% of the paper's base estimate. Part of it replaces planned test effort rather than adding to it: the constraint-preservation and Kleene harnesses partly overlap §16's 6k lines of test harnesses. The net addition is about 12–15%, consistent with the summary's figure, and within G5's "cost proportional" mandate.

**Sequencing against the paper's stages:**

| Gate | Required formal evidence |
|---|---|
| **S0** | §10.2 proved; §10.3a rule models green for every rule S0's module uses; §10.4 checks for those rules; constraint-preservation and round-trip property tests green; typed IR in place |
| **S1 (O2)** | model E green; §10.3b per-compile validation in CI; reconciliation monitor running |
| **S2 (O3, one aggregate)** | models A–D and G green and confirmed by history checking on real PostgreSQL; catalog drift check enforced; model F green if the aggregate holds personal data |
| **S3** | the above per aggregate type, with rule coverage (§10.6) complete for every rule its compile uses |

### 10.9 What not to do

- **Don't mechanise the Python compiler.** Translation validation gives per-output assurance at far lower cost.
- **Don't model PostgreSQL's implementation.** Model the isolation *contract* abstractly, and test the contract against the real system with history checking.
- **Don't formalise full SPARQL or full SQL semantics.** Use them selectively for the query law where the translation is non-trivial (M28, M22). Otherwise use differential testing against independent engines.
- **Don't let Alloy's bounded "pass" stand as a universal claim.** Record its scope in the claim, as for the earlier model.

---

## 11. Additional experiments

| # | Experiment | Decides | Pass criterion |
|---|---|---|---|
| **RS-X0** | Shape census over the real shapes graphs: closed shapes, path kinds, logical constraints, unbounded counts, targets, focus-node coverage of a sample ABox | RS-D1, compilable fraction | a stated fraction of instance data falls in the compilable fragment, agreed in advance |
| **RS-X1′** | Run the round-trip law on Appendix A before anything else | §5.1 | passes after the R2RML and state-column fixes |
| **RS-X3′** | Replace RS-X3's oracle with `tools/reference/eligibility`, bounded-exhaustive; prove empty-set behaviour in Isabelle (§10.2) | §8.5 | identical outputs; gated lemmas green |
| **RS-X7** | TLA+/Quint models A–D, then history checking on PostgreSQL | RS-D11 | no anomalies under the chosen discipline; predicted anomalies reproduced under the weaker one |
| **RS-X8** | Constraint preservation on mutated graphs, one mutation class per rule | §2.1 | zero disagreements with pySHACL |
| **RS-X9** | Erasure model F plus a probe of every store in a staging deployment | RS-D14 | no plaintext reachable after the stated bound |
| **RS-X10** | RLS bypass audit: views, owners, `SECURITY DEFINER`, Ontop's connection | §5.4, the ADR-A54 claim in §15 | no cross-tenant read as any application role |
| **RS-X2′** | RS-X2 with every compiled constraint, trigger, receipt and outbox write enabled | the write-path claim | measured write latency, not a single `UPDATE` |

---

## 12. Prioritised recommendations

| Priority | Action | Cost | Addresses |
|---|---|---|---|
| 1 | Fix and then run the round-trip law on Appendix A (subject map from `iri`; state and version columns inside or outside the law) | Hours | §5.1 |
| 2 | Run the RS-X0 shape census before RS-D1 | Hours–days | §2.2 |
| 3 | Add the constraint-preservation law and its mutated-graph test | Small | §2.1, §7 |
| 4 | Introduce the typed `decision3` IR; store and expose decisions as concepts, never NULL | Small | §2.4, §5.3 |
| 5 | Prove the SQL encoding and quantifiers in Isabelle, including negative lemmas | Small | §10.2 |
| 6 | Test the SQL eligibility backend against the reference semantics, with the full concept-matching laws | Small–Medium | §4.1 |
| 7 | Fix the defective rules: M12, M14/M17 counts, M21, M24, M27, M30, M48, the concept table | Small each | §3, §4.2 |
| 8 | Literal and range policy (value-space round trip), with SMT checks for ranges, templates and regexes | Small–Medium | §3, §4.5, §10.4 |
| 9 | TLA+/Quint models A–D and history checking; decide RS-D11 | Medium | §4.3, §4.4, §10.1 |
| 10 | Alloy rule-level models, then per-compile translation validation | Medium | §10.3 |
| 11 | Define the erasure boundary (RS-D14); model F | Medium | §4.4 |
| 12 | RLS hardening and catalog drift check | Small | §5.4, §10.7 |
| 13 | Specify the O2 feed and the O3 vocabulary synchronisation; models E and G | Medium | §8.1 |
| 14 | Phased migrations from S2; drop-and-rebuild at S1 | Medium | §6 |
| 15 | Rule claims, digests covering definitions, coverage from `COMMENT ON` | Small | §10.6 |
| 16 | Re-estimate: M28 translation, concurrency and security tests, recurring migration cost, formal methods; define or drop the G columns | Small | §8.4 |

**Bottom line.** The paper's architecture is right, and its strategic judgement that PostgreSQL delivers natively what paper 2 needed a custom engine for is persuasive. But it states universal laws and plans to check them with fixed examples, and several of those laws are already false for its own rules and its own appendix. The remedy is not heavyweight. It needs:
- a typed IR;
- one more law (constraint preservation);
- translation validation per compile in Alloy;
- a short Isabelle extension;
- a handful of SMT checks;
- a set of small protocol models confirmed against real PostgreSQL.

All of it fits within the formal-methods epic's existing tracks for about 15% extra. The concurrency models give the largest return, and this paper is the right occasion to finally start rung T4.