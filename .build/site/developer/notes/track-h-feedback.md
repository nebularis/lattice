<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Design review: H2.5 (key claims, audits, guard D) and H2.6 (expected compiled profile, paper check)

## 0. Verdict and the issues that matter most

Both slices are well aimed. H2.5 finishes the ports and fixes a real cross-store defect. H2.6 puts the contract up for review as data before any vocabulary is fixed, which is the right order. Neither is ready to branch as written. The blocking issues, in priority order:

| # | Slice | Issue | Why it blocks |
|---|---|---|---|
| B1 | H2.5 | The IR needs a **top-level `SELECT` query form** (aggregates, `GROUP BY`, `HAVING`, `COUNT(DISTINCT)`, `GROUP_CONCAT`, `COALESCE`, arithmetic) for the five audits. Q1 only asks about the sub-select. | It is the larger part of the new IR surface and has no decision behind it. The H2.1 property test ("parses as exactly one update") does not cover queries. |
| B2 | H2.5 | The rule "a projected aggregate counts as bound in every solution, since each group is non-empty" is **wrong in general**. | It repeats the F1/F4 pattern of a hand-written SPARQL rule that a test would later contradict. |
| B3 | H2.5 / §4.5 | "`GRAPH_ROLES` needs no new role" covers only the registry. The audits and reconcilers touch the **pinned, retention and quarantine graphs**, and gap-scan's `?log` ranges over **two roles**. | SI-4 (T20, T21, T32) and H2.6's resource mapping both depend on the roles. The §4.5 rule "neither slice adds a role" is probably already broken. |
| B4 | H2.6 | The contract omits things H2-Q6 (a) and H2-Q5 promised: the **logical operation kind**, the **request-digest construction**, **access modes** (in particular absence reads), and **result columns** for the audits. | Without them the profile is not a contract a caller in another language, a relational realisation or H5 can use. |
| B5 | H2.6 | Logical resources are keyed by "the parameter that names its subject". That is a **SPARQL artefact**: version-row subjects are computed (`?g`), receipts are minted, transaction claims come from `STR($txnId)`. | This brings the realisation back into a contract meant to be realisation-neutral, which is the point of H2-Q6. |
| B6 | H2.6 | No decision on **blank nodes or isomorphism** in the expected profiles. The persistence README still says compiled-profile labels "differ on every run". | Without one, H2.7 cannot compare its output with the reviewed examples deterministically. |
| B7 | H2.6 | The agreement test must allow for points where **H2.7 deliberately differs from the builders**, for example `$assertGraph` and `$retractGraph` required under `dal:PatchLog` (H2.3-Q3). | As written, the test would fail on the reviewed design, or the design would be bent to match today's builders. |

The rest of this review gives the full analysis, then proposed answers to the questions (§4) and a list of plan edits (§5).

---

## 1. H2.5

### 1.1 Guard D, the self-calibrating datatype test

**What it does.** `DATATYPE($p) = DATATYPE("0"^^xsd:long)` compares a parameter's datatype with whatever datatype the store assigns to a long constant. On rdflib that is `xsd:long`. On Oxigraph (TSD-07) it is the store's normalised integer datatype.

**The design is sound, with one precondition.** The guard's real contract is not "the parameter is an `xsd:long`". It is:

> the parameter's datatype equals the datatype this store gives an `xsd:long` literal on every path by which a value can arrive.

P5's extension is the right test. Its scope needs widening and its consequences need recording.

| Point | Analysis | Recommendation |
|---|---|---|
| The guard's acceptance set differs between stores | On rdflib, `"1"^^xsd:integer` is refused. On Oxigraph, `xsd:int`, `xsd:short` and `xsd:nonNegativeInteger` may all pass if they normalise to the same type. One query text therefore has store-dependent semantics. | Record it as a store property (`numericDatatypeNormalisation`, three-valued) for H5's capability record, not only as a TSD finding. Make the Python caller check (H2-Q4 (c)) the strict, store-independent contract: exactly `xsd:long`. The SPARQL guard is then the store-calibrated backstop. Say this in ADR-A123's fourth addendum. |
| P5's arrival paths | Planned: a constant, a substituted parameter, an initial binding, a stored value. Missing: a value arriving through `VALUES`, a value bound over the SPARQL Protocol (HTTP, which is how a real remote caller binds), and a value read from storage and rebound in the same query. | Add them. Make P5 a probe in the H2.4b probe table (P1 to P4 are there, P5 is referenced but not defined in the plan). |
| No stop condition | If any engine gives a constant and a parameter different datatype treatment, guard D refuses every write on it, which is the defect it was built to fix. | Add: "if P5 shows a constant and a parameter diverging on any engine, stop and ask." |
| Scope of the change | Only `Long` and `Position` change. `Digest` keeps `DATATYPE = xsd:string`. | Either apply the calibrated form to every `DATATYPE` test (`DATATYPE("x")` for `Digest` and `String`), so one rule covers all, or state why `xsd:string` cannot drift. Uniformity is cheaper to reason about. |
| It is a change, not a port | It rewrites the guard of every operation ported in H2.2 to H2.4. The equivalence harness compares with guards off, so it is unaffected. Harness step 4 ("one type test per required parameter, computed from the parameter list") is affected. | Treat it as a change under §7.1: list the golden `.rq` diff for every affected operation in the Validation Pack, and update step 4's expected conjunct form. "Regenerate the pinned renderings" alone hides the diff. |
| The defect it reveals | Fact 4 implies that on Oxigraph every guarded write of H2.2 to H2.4, guards on, has been refused silently. That is a shipped defect. | Record it in the triple-store-discovery document and as a TD row, closed by guard D, with a regression test on Oxigraph that runs a guarded write with guards on and expects it to apply. |
| Dropping `engines.guards()` | Guards off remains a supported mode (`--no-parameter-guards`, H2.7). | Keep guards on and off as a test axis on both engines rather than deleting the off cases. |
| Ill-typed literals | `"99999999999999999999"^^xsd:long` keeps its datatype on rdflib and passes the guard. | Leave it to the Python caller check, and add it to the Validation Pack's non-coverage list. |

Separately, H2-Q4 (a) writes the guard as `FILTER(BOUND($p))`. Under text substitution `BOUND(<iri>)` is a syntax error, because `BOUND` takes only a variable. If any kind's guard, for example `IriOrLiteral`'s, still uses `BOUND`, confirm it is never emitted for a parameter a caller may substitute as text.

### 1.2 Q1, the sub-select, and the missing `Select` form (B1, B2)

**Option (a) is right**, since (b) blocks H2.9. The design needs four corrections.

**1. One `Select` value for both uses.** The audits are top-level `SELECT`s that need the same projection, aggregate, `GROUP BY` and `HAVING` machinery. Define one `Select` IR value used as:
- a query operation kind beside the update kinds, and
- a `SubSelect` pattern element wrapping it.

Extend the H2.1 property test so a rendered query parses as exactly one query.

**2. Boundness rules for aggregates (B2).** Replace the planned rule with these:

| Projected item | Bound in every solution when |
|---|---|
| `COUNT(...)`, `COUNT(DISTINCT ...)` | always, including over an empty group (it returns 0) |
| a `GROUP BY ?k` key | `?k` is `Bound` in the inner pattern. An unbound key forms a group with an unbound key |
| `MIN`, `MAX`, `SAMPLE`, `SUM`, `AVG`, `GROUP_CONCAT` | there is an explicit `GROUP BY` **and** the argument is `Bound` in the inner pattern **and** the argument cannot raise a type error (for `SUM` and `AVG`, numeric) |
| any aggregate, with no `GROUP BY` | never, except `COUNT`. An implicit group over zero rows is one empty group, so `MIN` is unbound |
| `(expr AS ?v)` | the same rule as `BIND`. It can fail |

**3. Close the fragment.** Accept only projection of variables and aggregates, `GROUP BY` over variables, and `HAVING`. Refuse by type:
- `ORDER BY`, `LIMIT`, `OFFSET` and `DISTINCT` inside a sub-select, and nested sub-selects
- an aggregate outside a projection or `HAVING`
- a projected variable that is neither grouped nor aggregated
- a `HAVING` term that is neither a group key nor an aggregate
- an inner variable used outside the sub-select without being projected

Each refusal gets a test and does one of three jobs. Some reject queries that SPARQL 1.1 makes illegal or that fail silently. Some keep the boundness rules of §1.2 sound. The rest keep the fragment no larger than the ten templates need. They differ in strength, and two of them are choices rather than necessities.

#### Why refuse in the IR, not leave it to the parser

H2.1's design is that a builder cannot construct a forbidden operation, and the refusal names the rule (ADR-A123). Relying on the parser fails in three ways:

- **Engines differ in what they accept.** Some accept an ungrouped projected variable and return an arbitrary value from the group. Others raise an error. A query that parses on rdflib can fail on Oxigraph, or the reverse.
- **Some forbidden forms are legal syntax with silent semantics.** No parser catches them (the `HAVING` and leaked-variable cases below).
- **A parse failure arrives late.** It surfaces when the query is rendered, or in the H2.1 property test, not when the builder runs.

"By type" means the IR's constructors make the form unbuildable where possible, for example an `Aggregate` expression accepted only by `Projection` and `Having`. Where a type cannot express the rule, the checker refuses it with a named refusal.

#### An aggregate outside a projection or `HAVING`

**What SPARQL says.** The grammar allows aggregates only in `SELECT` expressions, `HAVING` and `ORDER BY`. `BIND(COUNT(?x) AS ?n)` or `FILTER(COUNT(?x) > 1)` in a `WHERE` is a syntax error.

**Why refuse it in the IR.** The operation would render to text that no store accepts. Making `Aggregate` a separate expression type, accepted only where the grammar allows it, turns this into a type error when the builder runs. This is the cheapest and least contestable refusal.

#### A projected variable that is neither grouped nor aggregated

**What SPARQL says.** In a grouped query, every projected variable must be a group key or appear inside an aggregate (SPARQL 1.1 §11.4, §18.2.4.1). `SELECT ?claim ?owner (COUNT(?owner) AS ?n) … GROUP BY ?claim` is illegal, because `?owner` has many values per group.

**Why it matters.**
- **Engines are inconsistent.** A strict engine raises an error. A lenient one picks an arbitrary value, like `SAMPLE`, which is non-deterministic. In an update, such as quarantine or merge-rewrite, an arbitrary value means a retry can write different triples, which breaks retry idempotence.
- **Boundness has no answer.** The rules of §1.2 say when a group key or an aggregate is bound. An ungrouped variable has no defined value, so the checker could not classify it as `Bound` or `OptionalAllowed`.

If a builder needs one value from the group, it must write `SAMPLE(?owner)` or `MIN(?owner)`. The choice is then explicit and goes through the aggregate boundness rules.

#### A `HAVING` term that is neither a group key nor an aggregate

**What SPARQL says.** `HAVING` filters groups. Only the group keys and aggregates are in scope there. A reference to any other variable is legal syntax on most engines, but evaluates to unbound.

**Why it matters.** This is the silent case. An unbound variable makes the expression an error. An error in a filter counts as false, so **every group is dropped, with no error**. In `HAVING (COUNT(?owner) > 1 && ?constraint = "x")`, where `?constraint` is not grouped, the quarantine would find nothing and report a clean store. That is the same failure as TD-34: an operation that does nothing and looks as if it succeeded. A parser does not catch it. Only a refusal does.

#### An inner variable used outside the sub-select without being projected

**What SPARQL says.** A sub-select is evaluated on its own, and only its projected variables leave it. An outer variable with the same name as an unprojected inner one is a different variable.

**Why it matters.** It looks like a correlation the author intended, but SPARQL does not make one. Suppose merge-rewrite projects `?claim` and `?canonical`, and the outer pattern uses `?owner` expecting the owners the inner query grouped. The outer `?owner` is then unrelated to the inner one, and the update links the wrong owners. Two things make this worse:

- **No error is raised.** The query is legal.
- **The opposite rule applies nearby.** `[NOT] EXISTS` does pass outer bindings in (§1.3). An author moving between the two constructs can apply the wrong rule.

This is the scope rule H2.5-Q1 already names ("only projected variables are visible after it"). The refusal enforces it. It is also what keeps the H2.1 lesson from recurring: F4 was a scope rule held only in memory.

#### `ORDER BY`, `LIMIT`, `OFFSET` and `DISTINCT` inside a sub-select, and nested sub-selects

These are different in kind. **They are legal SPARQL, and refusing them is a design choice**, not a correction. The reasons:

| Form | Hazard |
|---|---|
| `ORDER BY` without `LIMIT` | Has no effect. A join does not preserve the sub-select's order, and the specification guarantees none. Allowing it suggests a guarantee that does not exist. |
| `LIMIT` or `OFFSET` without `ORDER BY` | Non-deterministic. Which solutions survive is the engine's choice. In an update, a retry could write different triples. |
| `LIMIT` with `ORDER BY` | Deterministic only up to the engine's ordering of terms. That ordering differs for IRIs, mixed numeric datatypes (TSD-07) and ties. It is the same question that §1.5 raises about `MIN` over IRIs, and it would need its own engine tests and findings. |
| `DISTINCT` | Changes multiplicities, so an aggregate in the outer query, or a solution count, gives a different answer. It is mostly redundant after `GROUP BY`. This is the weakest refusal of the five. |
| nested sub-selects | Each level is another isolated scope. The boundness, role and `access_sets` walks of §1.2 would have to recurse, and each level would need engine tests (plan §5.1). No template needs one. |

The principle behind these choices: **the fragment holds what the ten templates use, and nothing else.** Every construct the checker accepts needs a boundness rule, a role walk, a harness normalisation and an engine test. Admitting a construct later costs one slice. Removing a construct after builders depend on it is a change to every one of them.

#### How strong each refusal is

| Refusal | Basis | Could it be relaxed? |
|---|---|---|
| aggregate outside a projection or `HAVING` | illegal SPARQL | no |
| ungrouped projected variable | illegal SPARQL, and engines handle it inconsistently | no. Use `SAMPLE` or `MIN` explicitly |
| non-group term in `HAVING` | silent failure: every group is dropped | no |
| unprojected inner variable used outside | silent failure: a false correlation | no |
| `ORDER BY`, `LIMIT`, `OFFSET` | non-determinism and ordering that differs by store | yes, with an engine test, if an operation ever needs "the first N" |
| `DISTINCT` | changes counts. Weakest | yes, cheaply, if a builder needs it |
| nested sub-selects | cost to the checker, and no use today | yes, when a template needs one |

I should have made this split in the review. The first four refusals are needed for correctness. The last three keep the fragment small and can be revisited. The plan should record them the same way: the first four as type rules of ADR-A123, and the last three as fragment limits of H2.5, each with the condition under which it would be lifted.

**4. Every IR walk must enter sub-selects:**
- the `GRAPH_ROLES` and role checks (T20, T21, T32), so SI-4 holds inside them
- `access_sets` derivation, which H2.6 consumes for quarantine and merge-rewrite
- the harness normaliser's BGP sorting. rdflib renames aggregates internally (`__agg_n__`, noted in §13.4), so a builder must emit aggregates in the template's order, or the normaliser must be shown to be insensitive to it
- the guard placement rule (the guard group stays first in the outer `WHERE`, never inside a sub-select)

Also check the active graph. If a sub-select sits inside a `GRAPH` block, it is evaluated against that graph. Engines have differed here, so give it an engine test, as the plan already does for scope.

### 1.3 Three scoping disciplines, stated once

With H2.5 the checker must model four scoping rules. Each needs its own engine test (plan §5.1):

| Construct | Scope it sees |
|---|---|
| `BIND` in a group | bottom-up, the group so far (F4) |
| `OPTIONAL`, join, `UNION` branch with a correlated `GRAPH ?g` | joined afterwards, so an outer binding restricts (H2.3-Q2) |
| `FILTER` inside `[NOT] EXISTS` | **substitution**: outer bindings, including parameters, flow in |
| `SubSelect` | empty, isolated, and only projections leave |

`key-claim-write` relies on the third: `FILTER(?other != $owner)` inside `NOT EXISTS`. Merge-rewrite relies on it with `?canonical`, a variable projected by a sub-select. `EXISTS` substitution is the best-known ambiguity in SPARQL 1.1. H2.3 tested "`NOT EXISTS` sees `$root`" in a pattern, not inside a `FILTER`. Add an engine test of a parameter and a sub-select projection inside a `FILTER` inside `NOT EXISTS`, bound by text substitution and by initial binding, on both engines.

### 1.4 Q2, the kind of `$now`

Neither option is tied to the data contract. H2.3 set `$cause` and `$actor` from the patterns guide's shapes (fact 3). Do the same here: look up the range and shape of the property `$now` is written to.

| Option | Assessment |
|---|---|
| (a) `IriOrLiteral` | Too loose. It accepts an IRI as a retirement time, which the property almost certainly forbids. |
| (b) `DateTime` | Store-sensitive. It refuses legitimate datatypes. |
| **(c) new: `Literal`** (`isLiteral($now) && LANG($now) = ""`) | Catches a missing value and an IRI, accepts any timestamp datatype, and is not datatype-sensitive per store. |

Recommend (c), unless the guide's shape says otherwise.

Two further notes:
- **Asymmetry.** Retire takes a caller timestamp while quarantine uses `NOW()`. The port keeps it. Record the reason, or a TD row if there is none.
- **Name.** `$now` and `?now` are the same SPARQL variable (§13.1 fact 4). The parameter does not collide today, since the two are in different templates. It does sit close to the `ClockInGuard` rule. A rename would be a later change. For now, a refusal test that `Now()` never binds a declared parameter's name costs little.

### 1.5 The key-claim ports

| Point | Analysis | Recommendation |
|---|---|---|
| `?other != $owner` declared `Kind.IRI` | For two IRIs, `!=` equals `!sameTerm`, so there is no term/value divergence. `$owner` is an IRI only while its guard is on. `?other` is an IRI only if stored data honours `sh:nodeKind sh:IRI` on `pat:claimedBy`. The IR cannot check that. | Record the data invariant as a declared assumption on the comparison, not as a type fact. Add a test with a literal owner stored in the data, guards on and off. |
| No missing-parameter tests | H2.3 and H2.4 each had "a missing `$root` writes nothing" and "without the guard, record what rdflib does". Step 5 has neither. | Add both for write, dual and retire. Retire is the dangerous case: a missing `$now` with guards off may release the claim with no record. |
| Retire semantics | "A retire moves the claim" is ambiguous. | State the expected triples from the template. Add the negative case that a retire by a non-owner writes nothing ("only a claim's owner releases it", README §7.6). |
| Dual | Two claims guarded together. | Add the half-held case: the next claim is held by another owner and the current one is free, so nothing is written. This is what makes rotation safe. |
| Quarantine idempotence | Step 5 asserts it is idempotent, while the template writes `BIND(NOW() AS ?now)` into the record. Unless the template guards against re-quarantine, a second run adds a second timestamp. | Check the template. If it is not idempotent, the port must keep that behaviour and the test records it ("record what rdflib does"), with a TD row. The test must not assert a property the template lacks. |
| `COUNT(?owner) > 1` in quarantine | This counts solutions, not distinct owners. It is correct only while one owner yields one solution, which holds while the pattern spans one keys graph. | Note it as a review item for when `dal:keyShards` is honoured (TD-06, TD-41). The port is unchanged. |
| `MIN` over IRIs for the canonical owner | The ordering is engine-defined. Two stores, or one store after a migration, could choose different canonical owners and leave conflicting merge relations. | Keep the engine test. If the stores differ, record a finding and a follow-up change to `IRI(MIN(STR(?owner)))`, a codepoint comparison. Separately, the canonical owner changes when a lower IRI joins later, so earlier merge relations then point at a non-canonical owner. Record this as a known property, outside the port. |
| `mergeRelation` read by `b.const` | It must be an IRI in predicate position, not a path or a literal. | Give it a predicate kind. The README forbids `owl:sameAs` as a merge relation. If no validator rule refuses it today, that belongs to H3's inventory. |
| Where the merge relation is written | Not stated. If it is written on the owners themselves, in their aggregates' graphs, merge-rewrite writes to aggregates outside any version-row guard. | Identify the graph now. It decides H2.6's write set for merge-rewrite (§2.2). |

### 1.6 The audits

| Point | Analysis | Recommendation |
|---|---|---|
| `GRAPH ?log` inside `OPTIONAL`, `?log` bound by `VALUES` | Accepted under the H2.3-Q2 rule (a). | Cite the rule in the port, and attach the P3 cost note: the gap scan is the clearest case of a sweep across many buckets. |
| `?log` covers the pinned graph and log buckets (B3) | One variable, two logical resources (`LOG` and `PinnedHeadResource`). `GRAPH_ROLES` maps `?log` to `LOG`. | Choose one: (i) a graph variable may carry a set of roles derived from its `VALUES` rows, or (ii) the pinned graph is part of `LOG`. (i) is more precise and is what H2.6's table assumes. Decide before H2.6's examples are committed. |
| Retention graph | Gap-scan reads it. It is probably used by no earlier port. | Confirm the role exists, or add it under the §4.5 rule. |
| Empty `logGraphs` | Valid input. The audit then checks only the pinned graph and reports clean. This is the TD-34 hazard in another form, since a slot left unfilled fails closed but an empty list does not. | Name it in non-coverage as a caller obligation for H2.8's caller check, and as an input to H9's applicability labelling. |
| Mixed numeric datatypes | `COUNT(DISTINCT ?seq)` over `"1"^^xsd:long` and `"1"^^xsd:integer` on rdflib counts two values and gives a false alarm. | Find where mixed types can come from, not only whether they count apart. In particular, check whether `append-event`'s `?n1` arithmetic writes `xsd:integer` while CAS writes `xsd:long`. If so, a stream that is appended to and then CAS-replaced would also fail the term guard on `seq`. Make one fixture an append followed by a CAS on the same stream. |
| Value compare on `?seq`, `?S`, `?L` | Correct for audits. Guards elsewhere compare positions as terms. | Write the rule down: positions are compared as terms in guards and as values in audits. That way an audit and a guard cannot disagree without a test noticing. |
| Non-vacuous negatives | "Nothing on a fixture that does not have it" is vacuous if the fixture lacks the relevant data. | Each clean fixture holds the data the audit inspects, minus the defect. Reuse the H1.2 witnesses rather than writing new ones. |
| `GROUP_CONCAT` | Compare as sets, as planned. | Declare the output column's encoding (space-separated `STR` of IRIs) as part of the result contract (§2.1). |
| Guard for parameter-free operations | Audits and the two reconcilers have no request-time parameters. | Confirm `ParameterGuard.derive` emits nothing, rather than an empty group or `FILTER(true)`, and that harness step 4 accepts "no group" for an empty parameter list. |

### 1.7 Closing TD-34 (step 7)

H2.3 step 7 said TD-34 "is removed only when H2.5 ports the last". The value guard (TD-43) is not ported, and guards can be turned off. Removing the row loses the trail. Instead:
- close TD-34 for every operation built with its guard on
- move the residual to TD-43, naming the value guard's unguarded parameters
- point to H2.8's `INFO` diagnostic for the guards-off case

### 1.8 Q3, slice size and order of work

One slice is defensible, since the harness compares with guards off and so guard D cannot hide a port difference. The slice nonetheless holds three kinds of work: a change across earlier ports, a new IR capability, and ports. Keep one Validation Pack, but fix the order of commits and give each part its own gate:

1. **Guard D and P5**, with the stop condition and the golden diff. Independent, and it unblocks Oxigraph guards-on for everything after it.
2. **`Select` and `SubSelect`**, with the refusals, the boundness rules of §1.2 and the scope engine tests of §1.3.
3. **Roles**: any new roles and the multi-role `?log` decision, coordinated with H2.6 (§3).
4. The **five key-claim ports**.
5. The **five audit ports**.
6. **Engine findings**, the triple-store record, and TD-34 moved to TD-43.

If the P5 stop fires, steps 2 to 6 can continue on rdflib.

### 1.9 Validation additions

- Adversarial probes: add an aggregate projected without `GROUP BY` counted as bound (a refusal must fire), `NOT EXISTS` correlation broken by an engine (the engine test must fail), and an empty `logGraphs` that still reports clean (it must be named as non-coverage).
- The harness's non-vacuity count must include the query stems. Today it counts only updates.

---

## 2. H2.6

### 2.1 What the expected profile must contain (B4)

The list in §4.4 is incomplete against H2-Q5 and H2-Q6:

| Missing | Why it is needed | Proposal |
|---|---|---|
| **Logical operation kind** | H2-Q6 (a) names "the operation kind" first. `dal:templateId` is the builder's identity, a SPARQL artefact. A relational realisation and lattice-sql's operation oracle compare by kind. | `dal:operationKind`, with individuals such as Create, Bootstrap, Replace, Tombstone, Append, UnconditionalWrite, KeyClaimWrite, KeyClaimRetire, Reconcile (Merge or Quarantine), Audit (by name) |
| **Request-digest contract** | `$requestDigest` has kind `Digest`, but its construction (canonical N-Triples, sorted, with the kind, target and expected `seq`, and a hash) is a cross-language obligation, as minting recipes are. A caller in another language cannot compute it from the profile. | A `dal:DigestContract` on each operation that takes `$requestDigest`, or a digest recipe beside the minting recipes |
| **Access modes** | H5 needs more than read and write. Write skew, README §2's own example, is a property of **absence reads** (`NOT EXISTS`) in create-if-absent and key-claim-write. | A mode per access: `PointRead`, `AbsenceRead`, `ScanRead`, `ClosureRead` (or `WholeAggregateRead`), `Insert`, `Delete`. Optionally say which reads guard which writes |
| **Result contract for queries** | The audits are operations a caller runs and parses. The projected columns and their encodings are a contract, like the parameters. | `dal:resultVariable` declarations: name, kind, and encoding (for example the `GROUP_CONCAT` separator) |
| **Source of `logGraphs`** | The caller fills it from the registry. The operation does not read the registry (fact 2), but the obligation needs stating. | On the `RegistryList` parameter, `dal:sourcedFrom` the family's `dal:registryGraph`, as a declared caller obligation |
| **`templateVersion` after Mustache** | It is kept as the builder's identity, but nothing says what versions a builder. | Decide now: a version bumped by any change that alters the golden `.rq`, which the golden check enforces |

### 2.2 The logical-resource table

| Point | Issue | Recommendation |
|---|---|---|
| Keys (B5) | "The parameter that names its subject" does not fit computed subjects (`?g` from `$root`), minted subjects (receipt IRIs from epoch and seq), derived ones (`?txnKey` from `STR($txnId)`), or scans (audits and reconcilers have no subject parameter). | Key each resource by its **logical key**: aggregate and version row by root (or stream), transaction claim by txn id, receipt by (target, epoch, seq), key claim by claim (or by constraint and normalised key), event by (stream, seq). Mark scans as unkeyed. The SPARQL subject is the builders' mapping, which is what H2-Q6 (a) means. |
| Closure versus whole graph | "Whether the read is a closure through the owned path" exposes the path, a SPARQL property-path text, and SI-5's open gap. | The contract says "reads and deletes the whole aggregate of `$root`". The path stays in the `ownedPath` binding as realisation. A relational realisation reads the same access as a cascade (M37). |
| Transaction claim, "every guarded write" | Key-claim writes are guarded (`NOT EXISTS`) but take no `$txnId`. | "Every operation that takes `$txnId`." |
| Merge relation | Merge-rewrite is listed as writing `KeyClaimResource`, but it writes merge-relation triples (§1.5). | Name a `MergeRecord` resource, or `AggregateResource` if the triples land on owners. The latter is a guard bypass that the paper check and H5 must see. |
| `NoBoundary` value guard | Its target is one property value, not an aggregate, and its realisation is the default graph (TD-43). No resource in the table fits it. | Add `PropertyValueResource`, keyed by root and property. A relational realisation is a column with an old-value compare. |
| Pinned heads read through `?log` | See §1.6. | The mapping must take the pinned read from the `VALUES` constant, not from `?log`'s role. |
| Graph IRI templates | A named-graph family's per-root graph. | Fine as the aggregate's realisation. Bucket months (log, events) are realisation, so `ReceiptResource` must not carry a bucket. |
| The name "Resource" | Clashes with `rdfs:Resource` in reading. | Use individuals of a kind enumeration, for example `dal:VersionRow a dal:LogicalResourceKind`, not subclasses. That keeps the vocabulary OWL-light and the kinds closed. |

### 2.3 Q1, where the expected profiles live

**Option (a), `ontology/persistence/test/`, is right in intent.** In H2.7 these files become positive fixtures for the layer's shapes. Before choosing it, verify three things:

1. No check that runs over the layer flags use of undeclared `dal:` terms. The files will use terms that do not exist until H2.7.
2. The ontology catalogue and release tooling do not ship `test/`, and the addition does not trigger `check:ontology-versioning` for a 0.3.x change.
3. Nothing globs `ontology/*/test/` as SHACL test suites to run.

Use a subdirectory, `test/expected-profiles/`, so H2.7's shape tests can treat these files as a class of their own.

### 2.4 Q2, which configurations

The eight examples are a good choice, and (a) is right. Gaps:

- **The run choices are not shown.** Every example shows guards on and graph names chosen by the query. Add one variant, for example `baseline-single-class.caller-named.expected.ttl`, with guards off and `graph_names=caller`. Reviewers then see how the `$g` `equals` rule is encoded. That rule must be structural (prefix, `ENCODE_FOR_URI` of the root, suffix, by reference to `dal:graphIriTemplate`), not SPARQL expression text, or it breaks H2-Q5 (a) and SI-5.
- **Payload contract with no shape.** `baseline-single-class` shows a named-graph payload with no boundary shape, H2-Q2's `INFO` case. Make sure the contract shows the absence explicitly rather than leaving the field out. Decide also whether H2.8's `payload-check` query is a listed `dal:GeneratedOperation`. Examples first is where that is settled.
- **Patch-log requiredness.** `baseline-single-class` uses `dal:PatchLog`, so its expected profile must show `$assertGraph` and `$retractGraph` required (H2.7's design), while today's builder declares them optional (B7).
- **Composite dataset-guard variants.** Their absence is acceptable, since the agreement test covers their derived parts, but the claim "differ by the dataset read alone" should be an assertion in that test.

### 2.5 Q3, the value guard

**(a), hand declarations, is right.** Add:
- **Provenance.** Mark the operation's declarations `dal:declarationSource dal:HandDeclared`, so readers and H5 know they are not derived.
- **Guard status per operation.** It has no generated guard. A run-level `dal:parameterGuards true` would then be untrue for this operation. Record guard status per operation, or let the run-level term carry an exception list.
- The agreement test with the template's `$` variables reuses the H-D11 lexical convention. That is acceptable as temporary, and it is removed with TD-43.

### 2.6 Q4, the terms

Settling names at review is right, but the **model** should be proposed now, so the review is about names and not structure:

```
op  dal:operationKind     dal:Replace ;
    dal:templateId        "cas-replace-named-graph" ; dal:templateVersion "…" ;
    dal:parameterGuards   true ; dal:graphNames dal:QueryNamed ;
    dal:parameter         op:param-root , … ;
    dal:access            op:acc-1 , … ;
    dal:payloadContract   op:payload ;
    dal:digestContract    op:digest .
op:param-root a dal:ParameterDeclaration ;
    dal:parameterName "root" ; dal:parameterKind dal:IriKind ; dal:required true .
op:acc-1 a dal:ResourceAccess ;
    dal:resourceKind dal:VersionRow ; dal:accessMode dal:PointRead ; dal:keyedBy op:param-root .
```

Two rules keep the model compatible with a stored IR later (typed IR sketch §9.4) and make the review about names only:

1. **No blank nodes, and no node ids that depend on order.** Every declaration node gets an IRI derived from its position in the contract: the target, the operation's `templateId`, and the parameter name or access index. One example is `<…/compiled/LoanApplication/cas-replace#param-root>`. This also resolves B6 (§2.7).
2. **No SPARQL text in any value.** Kinds, modes and resources are closed enumerations of individuals. The caller-named graph's `equals` rule refers structurally to `dal:graphIriTemplate`, and the owned path stays in the `ownedPath` binding, not in the contract (SI-5). A value holding SPARQL text is refused at review, and later by an H2.7 shape.

The Validation Pack should present the model as a class diagram with the proposed names. The review then settles the names, while the structure is already fixed by the questions above.

### 2.7 Determinism and comparison (B6)

The persistence README §11.5 says "compiled profiles are not written: their blank-node labels differ on every run". H1.5 exists to fix that, and the plan says it "waits for nothing". The plan does not say whether H1.5 has landed. The expected profiles fix the structure H2.7 must emit, so how they are compared has to be decided now.

| Option | Consequence |
|---|---|
| (a) **Minted IRIs for every new declaration node** (rule 1 above), plus comparison by graph isomorphism (`rdflib.compare.isomorphic`) for the existing parts, which still use blank nodes | Deterministic now for the new parts, and independent of H1.5. Diffs are readable at review. |
| (b) Byte identity, which waits for H1.5 | A Turtle diff is easy to review, but H2.6 becomes blocked on H1.5. |
| (c) Isomorphism alone | Works, but a failure is reported as "not isomorphic" with no location, so reviewing a difference is expensive. |

**Recommend (a).** State H1.5's status in the plan. If it has landed, the existing blank nodes go too, and comparison becomes byte identity.

### 2.8 The agreement test (B7)

As written, the test checks that "declarations and sets equal what the builder gives through the same mapping". Three problems:

**1. Intended differences.** Some differences are deliberate, because the expected profiles describe H2.7's design and not today's code. Known cases are `$assertGraph` and `$retractGraph` required under `dal:PatchLog` (H2.3-Q3), the logical key of each access (§2.2), access modes beyond read and write, and per-operation guard status (§2.5). The test should therefore sort each comparison into one of three outcomes:

| Outcome | Meaning | Reported as |
|---|---|---|
| equal | derived from the builder, and the two agree | pass |
| intended difference | listed in a reviewed table with the reason and the slice that closes it, for example "H2.7: required per receipt model" | pass, named |
| skipped | no builder yet (H2.5's ten, if H2.5 has not merged) | pass, named |

A difference not in the table fails. The table of intended differences is part of H2.7's brief, and H2.7 empties it.

**2. Where the mapping from roles to resources lives.** H2-Q6 (a) says "the builders map each logical resource to its graph role". If H2.6 writes the mapping only inside its test, H2.7 will write a second one, and the two can drift. Put the mapping in production code now, as a small data table beside `GRAPH_ROLES`, so the test and H2.7 read the same table. That touches builder-side code, which affects the parallel plan (§3).

**3. The mapping is not a function of the graph role.** If one role holds two resources, the role alone cannot tell them apart. Possible cases:
- `LOG` holds receipts and, through `?log`, pinned heads (§1.6).
- `KEYS` may hold key claims and merge records (§1.5).
- `META` holds version rows, and possibly the stream counter of `append-event`.

Where this happens, the mapping needs the predicate or the subject's type as well as the role. Check each role against the templates before writing the table. Any role found to hold two resources is a finding for the review.

**A fourth check to add: the base profile.** An expected profile is described as "the compiled profile as `compile` emits it today, plus…". Add a test that the expected profile, minus the new terms, is isomorphic to today's `compile` output minus `dal:templatePath`. Without it, the examples drift silently whenever H2.5, an HO follow-up or anything else changes compile output. The cost is that a change to compile output must regenerate the expected files in the same commit. That is the H1.5 golden-file rule already applied to HO slices, so it is not a new discipline. H2.7 later replaces the test with full equality.

**A fifth, cheap check: declared parameters against the golden `.rq`.** For every operation, the declared parameter names should equal the `$` names in its golden `.rq`, and for the value guard, in its template. This catches errors in the hand-written H2.5 entries, and it previews H2.9's replacement of the H-D11 convention.

### 2.9 The paper check (step 3, sketch §7.2)

Comparing against the tables early is right. The criteria as written check too little:

| Gap in the criteria | Add |
|---|---|
| Checks only that a counterpart exists | Check that the **logical key** matches a relational key: the version row's key is the aggregate's primary key, the receipt's key is (target, epoch, seq), and the key claim's key is a unique index. A resource with a counterpart but a different key is a mismatch. |
| Ignores access modes | An absence read (create-if-absent, key-claim-write) maps to a unique index or a `SELECT … FOR UPDATE`, and a whole-aggregate delete maps to a cascade (M37). A mode with no relational reading is a mismatch. |
| Ignores atomicity scope | The contract assumes one request. Relationally that is one transaction. Record this per operation kind, since R1 of §4.3 shows the property is load-bearing. |
| One direction only for operations | Check both directions. Every §9 operation should touch only named resources, and every operation kind in the contract should have a §9 counterpart or be marked as having none. |
| Pass or fail per row | Use three outcomes per row: *logical* (both realisations have it), *realisation only* (an artefact of one realisation, so it should not be a logical resource), and *gap* (to the maintainer). |

The *realisation only* outcome matters, because two rows of the proposed table probably belong there:
- **`PinnedHeadResource`.** Pinned heads exist because receipts sit in monthly buckets that are dropped whole (README §7.4). The logical fact is "a version row's head receipt survives retention". In a relational realisation, a foreign key from the version row to its head keeps the receipt, and no separate structure exists. The likely conclusion is that the pinned graph is the SPARQL realisation of retention of `ReceiptResource`, and is not a logical resource of its own. This also simplifies the multi-role `?log` question (§1.6): pinned heads and buckets are both realisations of receipts.
- **Registry and buckets.** These are already excluded from the table, which is consistent with this reading.

**`TransactionClaimResource` is logical.** A relational realisation needs an idempotency-key table, and §9's silence on it is a gap in §9, not in the contract. Say so in the Validation Pack, so the gap is not read as a fault of the contract.

**`RetentionMarkResource` and `DatasetEpochResource` are logical.** Both are per-stream or per-dataset rows in either realisation.

Record each conclusion as a hypothesis for the maintainer, as §3.1 says, and not as a decision.

### 2.10 Steps, validation, non-coverage, estimate

- **Order of steps.** Add a step 0: before writing the files, decide the open items that change the structure of the files. These are the multi-role `?log` (§1.6), pinned heads as a realisation (§2.9), the digest contract (§2.1), minted node IRIs (§2.7), and the result contract (§2.1). Writing eight files and then restructuring them is the expensive order.
- **Hand-written entries for H2.5's ten.** Mark each file section written from a template, so that whichever slice merges second knows what to reconcile.
- **Validation.** Keep `mise run check:persistence` as the one command. Name the five tests: parse, agreement (three outcomes), base-profile isomorphism, `$` names against the golden `.rq`, and node IRIs deterministic (two compiles produce the same IRIs). Also define adversarial probes for the gate: drop a parameter from one expected file (agreement fails), add an undeclared `$` to a golden file (the name check fails), and change an example's configuration without regenerating its expected profile (the isomorphism test fails).
- **Non-coverage.** Add the composite dataset-guard variants, the relational realisation itself (paper only), the digest algorithm beyond its declaration (H2.8), and isolation semantics (H5).
- **Estimate.** With the base-profile test, the mapping in production code and the extra variant, about 250k to 300k tokens rather than 200k.

---

## 3. Running H2.5 and H2.6 in parallel (§4.5)

The plan's claim that the slices "share no code" fails in three places:

| Point | Problem | Rule to add |
|---|---|---|
| Roles and resources | H2.5 probably needs the pinned, retention and quarantine roles, and a decision on multi-role `?log` (B3). H2.6's mapping needs the same decisions. The rule "neither slice adds a role without updating both sections" assumes this is rare. It is the main point of contact. | Take the role decisions out of both slices into one **precursor commit** on `main`: the roles, `?log`'s treatment, and the role-to-resource table (§2.8). Both branches start from it. |
| `access_sets` | If H2.6 needs access modes and logical keys from the builders, it must extend `access_sets` in `builders.py`, which H2.5 also edits. | Either H2.6 writes modes and keys by hand and the agreement test checks only the fields `access_sets` provides today, with the rest listed as intended differences, or the precursor commit extends `access_sets`. Prefer the precursor. It also gives H2.5's new operations modes from the start. |
| Who fixes disagreements | "Whichever merges second … fixes any disagreement in its own branch" conflicts with "each slice edits only its own plan section and Validation Pack". If H2.5 merges second, it must edit H2.6's expected files. | State the exception: the slice that merges second may edit the other's expected files, and lists each edit in its Validation Pack for countersignature. |
| Guard status | "The guard's form is not recorded in a profile" is true. Per-operation guard status (§2.5) is recorded, and the audits' guard is empty. | No conflict, but say so, so H2.5's parameter-free operations are written in H2.6 with no guard and not with "guards on". |
| Result contract | H2.6 declares the audits' result columns before H2.5 ports them. | H2.5's audit ports must keep the column names, which the harness already enforces (variable names match exactly). Note this, so a renamed projection is treated as a contract change. |

With the precursor commit, the remaining parallel plan holds. H2.6 merging first, after the maintainer commits its examples, is the better order: H2.5 then runs the agreement test against reviewed examples.

---

## 4. Proposed answers to the questions

| # | Proposed answer |
|---|---|
| H2.5-Q1 | **(a), extended.** One `Select` value, used both as a query operation and as a `SubSelect` pattern element. Aggregate boundness by the table of §1.2, not by "each group is non-empty". A closed fragment with a refusal per excluded form. Every IR walk enters sub-selects. Engine tests for sub-select scope and for the active graph inside `GRAPH`. |
| H2.5-Q2 | **A new option (c), `Literal`** (`isLiteral && LANG = ""`), unless the patterns guide's shape for the retired-at property says otherwise. Check the shape first, as H2.3 did for `$cause` and `$actor`. |
| H2.5-Q3 | **(a), one slice**, with the six ordered gates of §1.8 and a stop condition on P5. |
| H2.6-Q1 | **(a)**, at `ontology/persistence/test/expected-profiles/`, after the three checks of §2.3. |
| H2.6-Q2 | **(a)**, plus one variant with guards off and caller-named graphs. The patch-log requiredness is shown as designed, and the absence of a boundary shape is shown explicitly. |
| H2.6-Q3 | **(a)**, with `dal:declarationSource dal:HandDeclared` and guard status recorded per operation. |
| H2.6-Q4 | **Propose the model now** (§2.6) and settle the names at review. |

New questions for the maintainer, to be answered before either branch:

| # | Question | Leaning |
|---|---|---|
| NQ1 | Does a graph variable carry a set of roles taken from its `VALUES` rows, or is the pinned graph part of `LOG`? | Part of `LOG`, if NQ2 is answered "realisation" |
| NQ2 | Is the pinned head a logical resource, or a SPARQL realisation of receipt retention? | Realisation (§2.9) |
| NQ3 | Does the compiled profile declare the request-digest construction? | Yes, as a digest contract, since a caller in another language cannot compute the digest without it |
| NQ4 | Are declaration nodes given minted IRIs, independently of H1.5? | Yes (§2.7) |
| NQ5 | Is the canonical owner of a merge computed by `MIN` over IRIs, or by codepoint order? | Record the engine findings first, then decide as a change after the port |
| NQ6 | Is the Python caller's datatype check strict (`xsd:long` only), with the SPARQL guard calibrated per store? | Yes, recorded in ADR-A123's fourth addendum |
| NQ7 | Where are merge relations written, and is merge-rewrite a write outside any version-row guard? | Find out from the template. It decides H2.6's write set and H5's model |

---

## 5. Plan edits

**§4.3 (H2.5)**
- Facts: add fact 6, "the IR has no query form", and fact 7, the three scoping disciplines of §1.3. Correct fact 2: the registry needs no role, but the pinned, retention and quarantine graphs may.
- Q1: rewrite the boundness sentence per §1.2. Name the `Select` form.
- Q2: add option (c).
- Step 1: add the extra P5 arrival paths, the P5 stop condition, the golden diff, harness step 4's new conjunct form, a TD row for the Oxigraph guards-on defect with its regression test, and guards on and off kept as a test axis.
- Step 3: declare the IRI assumption on `?other` as a data invariant, give `mergeRelation` a predicate kind, and name the graph the merge relation is written to.
- Step 5: add missing-parameter tests for write, dual and retire, the non-owner retire, the half-held dual, quarantine idempotence checked against the template, non-vacuous clean fixtures, and an append followed by a CAS on the same stream.
- Step 6: add the `NOT EXISTS` correlation engine test and the active graph of a sub-select.
- Step 7: TD-34 closed for guarded operations, with the residual moved to TD-43.
- Validation: add the new probes, and count query stems in the harness's non-vacuity check.
- Non-coverage: add empty `logGraphs`, ill-typed long literals, and `COUNT(?owner)` under key sharding.

**§4.4 (H2.6)**
- "What H2.7 will add": add the operation kind, the digest contract, access modes, logical keys in place of subject parameters, the result contract, `logGraphs`' source, and the versioning rule for `templateVersion`.
- Resource table: change the transaction claim to "every operation that takes `$txnId`". Add a merge record and a property-value resource. Mark the pinned head as a hypothesis for "realisation only". Use kind individuals, not classes.
- Q2: add the caller-named variant.
- Q3: add provenance and per-operation guard status.
- Q4: add the model sketch and the two rules.
- Steps: add step 0 (§2.10). Make the agreement test three-way, with its table of intended differences. Add the base-profile isomorphism test and the `$` name check. Put the role-to-resource mapping in production code.
- Step 3: extend the paper check per §2.9.
- Estimate: 250k to 300k tokens.

**§4.5 (parallel running)**
- Add the precursor commit (roles, `?log`, the mapping, `access_sets`), the rule allowing the second slice to edit the other's expected files, and the notes on guard status and the result contract.

**Typed IR sketch**
- §7: add the `Select` form to H2.5's row.
- §9.4: SI-5 gains "no SPARQL text in the compiled-profile contract" as an enforced rule from H2.6 on.

**ADR-A123**
- The fourth addendum states the guard's per-store contract and the strict check in the caller (NQ6).
