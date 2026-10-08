# Applying formal methods to the Persistence layer, its generated SPARQL, and pluggable RDF backends

## 0. Scope, sources, and how to read this

I have read the Persistence README (the `dal:` vocabulary, its dimensions, resolution, validation and compiler outputs) and the RDF/SPARQL patterns guide (the patterns being configured, the corrected SPARQL, the store SPI, the TCK). I have **not** seen `spec/persistence.ttl`, `shapes/constraints.ttl`, `tools/persistence`, the template library, `docs/precedence-and-resolution.md`, the minting libraries, or your existing Isabelle/Alloy/SMT assets beyond what the SQL review describes.

Conventions:

- **Fact** marks something that follows from the W3C specifications or from the attached documents.
- **Judgement** marks my assessment.
- ***(verify)*** marks something I believe but cannot confirm from the material given.
- Findings about compiler internals are posed as questions, not assertions.

The analysis is deliberately long because the question is "exhaustive". §1 is the summary, §12 is the defect list, §13 answers the compiler-generation question, §18 is the prioritised plan. Everything between is the reasoning.

---

## 1. Summary

### 1.1 Headline judgement

This layer is a far better formal-methods target than the SQL compilation work, for three reasons.

1. **The specification is already mostly written down and mostly declarative.** Dimensions with enumerated values, a baseline per dimension, a precedence algorithm, a refusal/warning table, an operation-selection table, a template library, an outcome table, and a set of standing audits. Almost all of this is finite, tabular, and therefore mechanisable at low cost. The expensive part of formalisation (recovering intent from code) has largely been done by the guide.

2. **The historical defect profile is exactly what cheap formal methods catch.** Appendix D records three remediation passes. Nearly every defect in D.1–D.3 is a bounded-model-checkable or decision-table property: a guard that can never match, a shape that can never fire, an audit query that cannot detect the loss it claims to detect, a fencing token that is checked but never advanced, an unbounded read that skips a committed write, a digest that is not computed, a retention rule that prunes a live head. These were found by three successive human reviews over months. A model checker finds that class in hours. §1.3 makes the argument concretely.

3. **Pluggable backends force the verification to be parametric, which is a virtue.** The honest statement of correctness here is not "the generated SPARQL is correct" but "*for this capability profile*, this strategy delivers this guarantee level". That is a matrix, each cell of which is a proof, a bounded check, or a counterexample. Once that matrix exists, the planner's `min_level` fail-fast becomes a lookup into checked evidence instead of a human claim, and the TCK's job narrows to establishing which column of the matrix a given store occupies. This is the single most valuable structural idea in this document (§4).

**The principal risk the current design carries is not in the compiler.** It is in three places formal methods reach well and testing reaches poorly:

- **the gap between the resolved declaration and the generated operations** (shard counts recorded but not honoured, infrastructure graph IRIs fixed, retention and epoch bumps delegated to housekeeping, composite boundaries binding only the first property): the compiled profile claims things the SPARQL does not implement, and nothing enumerates the gap;
- **the assume-guarantee split** between generated SPARQL, the caller, housekeeping and the store: every safety property in the guide depends on obligations discharged by at least two of those four parties, and none of the four has a machine-readable contract;
- **concurrency and procedure**, where the guide's own corrections cluster.

### 1.2 Top findings (detail in §12)

| # | Finding | Severity |
|---|---|---|
| 1 | **Scope matching is defined on instances; resolution is per class-and-deployment.** `dal:NamespaceScope` matches "resources whose own IRI starts with..." and `dal:ShapeScope` matches "resources conforming to a shape", but a target is a class. Either every instance of the class matches the same scopes (an unstated, undecidable-from-the-ontology side condition) or the compiled profile is unsound for some instances. `dal:ShapeScope` "resolved once at compile time" makes resolution data-dependent and therefore unstable under later data. | Major |
| 2 | **Overlapping `dal:graphPrefix` makes the instance-to-target map a relation, not a function.** Two `dal:GraphPatternScope`s covering one class with nested prefixes both claim an instance, and "the unscoped fallback for instances outside any of them" is only well defined if the prefixes form an antichain. No antichain or longest-prefix rule is stated. | Major |
| 3 | **The cross-axis rules are specified twice** (SHACL shapes, and "the compiler, which mirrors the cross-axis checks"), with no agreement proof and a known asymmetry. Two implementations of one rule set is the classic drift source. | Major |
| 4 | **The capability record in `dal:` is weaker than the one the safety argument needs.** `dal:CapabilitySpec` carries CAS level, reasoning and commit validation. The guide's `StoreCapabilities` additionally needs `detectsWriteWriteConflict`, `statementLevelConflictDetection`, `atomicUpdateRequest`, `graphLevelAccessControl` and `shaclDataGraphScope`, and the dimensions that depend on them (`dal:firstWrite`, meta topology, uniqueness enforcement, key-claim placement) cannot be checked without them. The spec is also unverified and unlinked to any TCK report. | Major |
| 5 | **Known-unsafe baselines.** `dal:RowLevelGuardOnly` is the epoch-guard baseline and is warned whether declared or defaulted; `dal:AbsentRow` is the first-write baseline and carries the create-path write skew on MVCC backends; `dal:ProvidedConcurrency` emits an unconditional write. A warning is not a gate, and nothing records which safety property each warning forfeits. | Major |
| 6 | **Infrastructure graphs that are mutable but unguarded.** The dataset node, the registry graph and the retention graph are rewritten by "the epoch authority", "bucket rotation" and "the retention job" respectively. None has a version row, a guard or a receipt. Every single-writer assumption there is unenforced, and a reader racing a registry rotation silently misses a bucket. | Major |
| 7 | **The request digest and the recipe canonicalisation are under-specified.** "Sorted canonical N-Triples" is not a canonicalisation: N-Triples admits choices in escaping, in `"x"` versus `"x"^^xsd:string`, and in literal lexical forms. "Canonical JSON" names no profile (RFC 8785/JCS?). Two conforming client implementations can therefore compute different digests for the same request and report spurious `IdempotencyKeyReuse`. | Major |
| 8 | **Detective controls have no proved coverage.** The always-on audits (S3, F5, the §24.2 receipt-side pair, the four generated audits) are the last line of defence against bulk loads, administrative `LOAD`s, restores and non-conforming writers. Three of them have already been corrected for *not detecting what they claimed*. No artefact states which violation classes are covered by which audit, nor which are uncovered. | Major |
| 9 | **The declaration-to-operation gap is not enumerated.** Declared shard counts are not honoured, infrastructure IRIs are constants, retention and epoch bumps are housekeeping, a composite boundary binds only the first property its shape reaches. The last of these is a soundness bug in the closure sweep, not just a limitation: an unswept closure member leaves exactly the dangling triple that "replace whole" exists to prevent. | Major |
| 10 | **The ETag parser does not handle the form the vocabulary offers.** `Version.parse_etag` splits on `-` and integer-parses both halves; `dal:TaggedRepresentation` folds the representation into the tag (`"3-41.ttl"`), which that parser cannot read. Epoch and sequence in the tag are also unpadded, against the fixed-width discipline applied everywhere else. | Minor, but a type-level smell |

### 1.3 The business case is already in the repository

Appendix D.1–D.3 is a labelled defect corpus. Treat it as the calibration set for any formal-methods investment: a technique that cannot find these is not worth buying, and a technique that finds all of them in a day pays for itself immediately.

| Recorded defect | Class | Technique that finds it | Rung | Time to find once tooling exists |
|---|---|---|---|---|
| A1: guard on dataset **and** row epoch wedges every row after a bump | liveness of a protocol | TLA+/Quint (no write can ever apply) or Alloy (no satisfying post-bump state) | T4/T2 | minutes |
| A2: `nextval`/offsets classed as dense | definitional, allocate-then-commit | TLA+ model with pre-allocation (reader skips) | T4 | minutes |
| A3: unbounded HLC read skips a committed write forever | liveness/safety under pre-commit stamping | TLA+ | T4 | minutes |
| A4: pruned txn claim lets an append apply twice | safety under retention | TLA+ with a TTL action | T4 | minutes |
| A5: no request digest, reused id reported as applied | decision-table soundness | Isabelle totality/soundness of the outcome function against a trace model | T5/T4 | hours once modelled |
| A6: `pat:NoForkShape` could never fire; row shape also targeted receipts | **vacuity** | witness obligation per constraint (exhibit a violating graph) | T0 | seconds per shape |
| A7: retention drops a bucket holding a dormant live head | safety under pruning | TLA+/Alloy | T4/T2 | minutes |
| B7: gap scan missed prefix, suffix and total loss | **completeness of detection** | Alloy or Isabelle: `audit_nonempty ⟷ ¬invariant` at bounded scope | T2/T5 | minutes |
| B11: separator joins collide (`"a|b","c"` vs `"a","b|c"`) | injectivity of an encoding | Isabelle (prefix-free code) or SMT strings | T5/T3 | minutes |
| B12/B13/B14: hand-typed example IRIs, 16 versus 19 digits, untyped literals | determinism and width | generated test vectors; LIA width check; emitter lint on the IR | T0/T3 | immediate |
| S6 as-of query compared retractions against the wrong graph | query semantics | bounded evaluation of the query against a modelled store | T2 | minutes |
| §16.2 fence checked but never advanced | protocol | TLA+ with a stalled lease holder | T4 | minutes |

Eleven of twelve are in reach of three techniques: a bounded relational model, a protocol model checker, and a decision-table/witness discipline. **Judgement:** the marginal cost of the tooling is less than the cost of a fourth remediation pass, and there will be a fourth remediation pass without it.

---

## 2. The verification problem

### 2.1 The artefact chain and the laws between stages

```
applied ontology + dal: config + capability spec
   │  (1) resolve      → one value per dimension per target
   │  (2) validate     → refusals and warnings
   │  (3) select        → named templates + operation set
   │  (4) emit          → dal:CompiledProfile, ParameterBindings, MintingRecipes, CapabilityRequirement
   │  (5) instantiate   → .rq text;   export-recipes → JSON
   ▼
generated operations  +  caller obligations  +  housekeeping obligations
   │  (6) execute on a store with capability profile C
   ▼
store state (payload, meta, keys, txn, log, deltas, snapshots, pinned, retention, registry, dataset)
   │  (7) read / resume / audit / erase / restore
   ▼
clients and consumers
```

Each arrow carries a law. These are the laws worth naming, because they are what the techniques below establish:

| # | Law | Statement (informal) |
|---|---|---|
| L1 | **Resolution is a function** | Resolution depends only on (config graph, applied ontology, target, capability spec), not on triple order, blank-node labels, file order, or machine. |
| L2 | **Resolution is local** | Adding a profile that matches no target leaves every target's resolution unchanged; adding one that matches target *t* changes only *t*. |
| L3 | **Target coverage is a partition** | Every instance of every configured class belongs to exactly one target. |
| L4 | **Validation is sound and complete w.r.t. the rule table** | The compiler refuses exactly the combinations the table declares unworkable, and the SHACL shapes refuse a subset of those, with every difference explained. |
| L5 | **Selection is total and disjoint** | For every resolved profile the operation set is defined, and no two selection rules assign different operation sets to one profile. |
| L6 | **The compiled profile is implemented** | For each resolved dimension, either the generated SPARQL implements it, or it is an explicit caller obligation, housekeeping obligation, or recorded-only value. Nothing is silently unimplemented. |
| L7 | **Instantiation is substitution** | `parse(render(template, σ)) = subst(parse(template), σ)`, and `render` escapes and types every parameter, so no parameter value can change the query's structure. |
| L8 | **Operation correctness (sequential)** | Each generated operation, executed alone on a state satisfying the invariants, produces a state satisfying the invariants and the operation's postcondition. |
| L9 | **Operation correctness (concurrent, parametric)** | For capability profile *C*, every interleaving of the generated operations preserves the declared invariants and the family's declared guarantee level, or else *C* is below the family's `min_level` and the compiler refuses. |
| L10 | **Outcome soundness** | The confirmation procedure's verdict is justified by the history: `Applied` implies exactly one application of this request; `PreconditionFailed` implies no application and a moved row; and so on, totally and disjointly. |
| L11 | **Detection completeness** | For each invariant and each violation class reachable by an out-of-band writer, some always-on audit returns a non-empty result, within a stated latency. |
| L12 | **Identity laws** | Claim IRIs, revision IRIs, event IRIs and key IRIs are deterministic, injective on their declared domains, and their derivations are agreed by every independent implementation. |
| L13 | **Erasure boundary** | After erasure plus the stated retention bound, no store in the family's enumerated set yields the subject's plaintext or pseudonym. |
| L14 | **Epoch safety** | No position, ETag, revision IRI or consumer cursor minted under one epoch can be mistaken for one minted under another, and no backup restored twice can reuse an epoch. |
| L15 | **Migration/rotation squares** | Changing shard counts, rotating a claim scheme, or bumping an epoch commutes with reading: the pre-change and post-change views agree where they must and are disjoint where they must. |

**Judgement:** L1, L2, L4, L5, L7, L8, L10, L12 are cheap and should be settled by proof or exhaustive check. L3, L6, L11 are the ones currently missing from the design, not merely from its verification. L9, L13, L14, L15 need protocol models and will produce the findings.

## 2.2 Why "verify the compiler" is the wrong target *(continued)*

The compiler is a resolver, a validator, a lookup table and a printer. Its code is not where the risk is. The risk is in the *rules* it applies, the *templates* it selects, the *protocol* those templates participate in, and the *backend* that executes them. Follow the same principle the SQL review states: **verify the outputs and the rules, not the program.** Concretely:

- **The rules become machine-checked definitions and are generated into both the compiler and the shapes** (§13). Today the cross-axis rules exist twice — in `shapes/constraints.ttl` and in the compiler — and the README already records an asymmetry ("the compiler also catches combinations declared on different profile nodes, which node-local shapes cannot see"). Two hand-written implementations of one rule set drift. One generated source of truth does not, and the same source feeds the Isabelle definitions, the SAT/BDD exhaustive check, the model-checker configuration and the README tables.

- **Each compiled profile is validated against its inputs by an independent checker.** Translation validation, not compiler verification: for *this* configuration graph, an independently written resolver recomputes the dimension values and the operation set, and a checker confirms the emitted `dal:CompiledProfile` agrees. The Python compiler stays unverified; its outputs do not. This is cheap because resolution is a small pure function over a finite lattice.

- **Each generated operation is checked against a model of the protocol it participates in, parametrised by backend capability.** The operation text is not verified in isolation — "is this SPARQL correct?" is not a well-posed question. The well-posed question is "does the set of operations this profile generates, under capability profile *C*, preserve the invariants and deliver the declared guarantee level?" That is a model-checking question (§10), and its answer is a matrix cell (§4).

- **Each always-on audit is checked for the property it claims to detect.** Three of them have already been corrected for failing exactly this (D.1 S3/prefix loss, D.3 A6 fork shape, D.3 B7 suffix and total loss). The obligation is `audit returns a row ⟺ the invariant is violated`, bounded (§7.4, §11).

- **Everything the generated SPARQL cannot enforce becomes an explicit, machine-readable obligation** on the caller, on housekeeping, or on the store, and each obligation is discharged by a named test, monitor or runbook check (§5, §16). An assume-guarantee argument with unwritten assumptions is not an argument.

The one place where "verify the compiler" partially *is* the right target is the **emitter**, because L7 (instantiation is substitution) is a genuine program property with a genuine injection consequence. That one component is small enough to specify precisely and test exhaustively, and §13.4 argues it should be *generated from a typed IR* rather than verified as hand-written string handling.

---

## 3. What there is to formalise: the specification surface

### 3.1 The four kinds of content, and the technique each wants

| Content | Character | Size | Technique | Rung |
|---|---|---|---|---|
| **Dimensions, values, baselines** | finite enumerations with a default per dimension | ~20 dimensions, 2–5 values each | typed registry; totality and exhaustiveness checks | T0 |
| **Scopes, matching, precedence** | a small pure function over a finite lattice, plus one reasoning-dependent case | one algorithm | Isabelle (determinism, locality, monotonicity); bounded-exhaustive differential | T5/T0 |
| **Cross-axis validation** | a propositional predicate over a finite product space | ~1.3 × 10⁸ combinations (§7.2) | **SAT/BDD/SMT — exhaustive, not sampled** | T3 |
| **Operation selection** | a lookup table, dimension → operation set | ~8 rules | totality/disjointness check; covering-array execution | T0 |
| **Templates and their guards** | SPARQL text with parameters | ~15 operations, 4 audits | typed IR + emitter; Alloy for state effects; TLA+ for interleavings; automata for well-designedness | T2/T3/T4 |
| **Identity and digests** | string functions over Unicode and bytes | ~8 derivations | Isabelle (injectivity, order), SMT strings (template injectivity), test vectors | T5/T3/T0 |
| **Protocols** | concurrent, crash-prone, backend-parametric | 10–14 models | **TLA+/Quint** | T4 |
| **Detection (audits, shapes)** | queries claiming to detect violations | ~10 artefacts | Alloy equivalence + witness obligations | T2/T0 |
| **Housekeeping and runbooks** | procedures outside the compiler | 5 procedures | TLA+ for the procedure, monitors for the evidence | T4/T7 |

**Judgement.** The second and third rows are where the best value-for-money sits and where nothing currently exists. The seventh row is where the defects are. The eighth row is where false assurance is.

### 3.2 The state space to be modelled, once, and shared

Every technique below needs the same abstract state. Define it once, in one place, and generate the Alloy signatures, the TLA+ variables and the Isabelle records from it (§13.3). From the README's graph table plus the guide's Appendix A:

```
Dataset       : epoch, orderModel, stableWatermark?
VersionRow    : target ↦ (epoch, seq, head?, deleted?, fence?, lockedBy?, lockExpires?, current?)
Receipt       : revIri ↦ (target, epoch, seq, opSeq?, prevRev?, txn, hlc?, recordedAt,
                          occurredAt?, actor?, cause?, asserts?, retracts?)
TxnClaim      : txnId ↦ (rev, requestDigest)
KeyClaim      : claimIri ↦ (constraint, claimedBy?, retiredBy?, retiredAt?)
KeyShard      : shardIri ↦ counter                         -- P3 only
Retention     : target ↦ lowWaterMark
Registry      : family ↦ set of (log | event | delta | txn | key) graph IRIs
Payload       : graphIri ↦ set of triples
Delta         : revIri ↦ (addGraph, delGraph)              -- PatchLog only
Snapshot      : revIri ↦ sealedGraph                       -- SnapshotPerRevision only
Pinned        : set of receipts carried out of dropped buckets
ErasureReg    : append-only, outside the dataset
External      : allocator rows, lock leases + fence counter, watermark, epoch high-water mark
```

Plus the **environment**: a capability record (§4.1), a clock model, a crash model, and a set of out-of-band writers (bulk load, administrative `LOAD`, restore, a rogue ETL).

**Finding (Major).** Four of these — `Dataset`, `Registry`, `Retention`, and the external stores — are **mutable and unguarded**. The README says the dataset node is "rewritten only by the epoch authority", the registry "rewritten on bucket rotation", the retention graph "rewritten by the retention job". There is no version row, no guard, no receipt and no epoch check on any of them. Every safety argument that reads them (the epoch guard on every write, the registry-listed bucket enumeration in every audit and every resume query, the low-water mark in the gap scan) assumes a single writer and atomic replacement, and nothing enforces or detects a violation. A reader enumerating buckets concurrently with a rotation can miss a bucket, which makes the gap scan report loss that did not happen — or, worse, *not* report loss that did (if the rotation adds a bucket after the reader has computed its `VALUES` list). This is the first thing I would model (§10, model J).

---

## 4. The organising idea: a strategy × capability guarantee matrix

### 4.1 The capability record is the formal environment assumption

Everything in this layer is conditional on the backend. The guide already knows this and the planner already acts on it (`min_level` fail-fast). What is missing is that **the conditions are not written as assumptions of a proof, and the conclusions are not written as guarantees of a proof.** The fix is small and structural.

Let *C* be the capability record. The guide's `StoreCapabilities` is the right shape; the `dal:CapabilitySpec` in the ontology is a strict subset of it.

| Capability flag | In `dal:CapabilitySpec`? | Which dimension's safety depends on it |
|---|---|---|
| `atomicUpdateRequest` | **no** | everything: the whole single-request guarded-write design |
| `maxIsolation` | partially (`dal:providesCas`) | P2/P3 selection, write-skew exposure |
| `singleWriter` | **no** | `dal:GlobalDenseCounter` affordability, `dal:AbsentRow` safety |
| `detectsWriteWriteConflict` | **no** | P3 viability, `InTxCounter`, `dal:Optimistic` |
| `statementLevelConflictDetection` | **no** | `dal:metaTopology`, shard counts, A6 |
| `multiAggregateAtomicity` | **no** | multi-target writes, `dal:deadlockPolicy` |
| `commitValidation`, `shaclDataGraphScope` | partially (`dal:providesCommitValidation`) | `dal:minEnforcementLevel`, the SHACL trick, fork detection |
| `graphLevelAccessControl` | **no** | key-claim placement for personal data (TCK S-1 is gating) |
| `reportsAffectedRows` | **no** | whether confirmation can be skipped |
| `nativeChangeFeed`, `changeFeedDense`, `feedRetention` | **no** | `dal:DerivedFeed`, `dal:DenseFeedRead`, `CursorExpired` |
| `nativeSequence`, `nativeCommitPosition`, `nativeTimeTravel` | **no** | `dal:datasetTierModel`, as-of strategy |
| `quadsInUpdateTemplates`, `unionDefaultGraph`, `requiresSkolemization`, `maxRequestBytes` | **no** | whether the generated text runs at all |
| `providesReasoning` | yes | `dal:EquivalentClassScope`, `dal:ShapeScope` |

**Finding (Major, #4).** The capability vocabulary is too narrow to express the preconditions the generated SPARQL actually has, so the `dal:CapabilityRequirement` the compiler computes cannot be a complete precondition. Two consequences: a profile can be accepted against a spec that says nothing about the flags its safety depends on; and the compiler cannot refuse `quadsInUpdateTemplates`-dependent output for a store that lacks it, which is a *runtime failure*, not a weaker guarantee.

**Recommendation (PV-D1).** Extend `dal:CapabilitySpec` to the full `StoreCapabilities` record, make every flag three-valued (`provides` / `does-not-provide` / `unknown`), and make `unknown` behave as `does-not-provide` for refusals and as `does-not-provide` for warnings — i.e. never optimistic. Bind each spec to a **TCK report digest**, so a spec is evidence rather than a claim (§14).

### 4.2 The matrix

For each (strategy, capability profile) pair, the guarantee delivered. The guide has this implicitly in Chapter 25's strategy tables and Chapter 26's store table, written by hand, and Appendix D records that the hand-written version was wrong in at least five cells (A2 density, the Neptune/TDB2 rows, the P3 purpose, A6's conflict granularity).

```
         Guarantee(strategy, C) = the strongest level the model preserves under C
         Refuse(family, C)      ⟺ Guarantee(selected(family), C) < declared min_level(family)
```

The matrix cells are produced **mechanically** by model-checking one parametric model per pattern family across the capability configuration space (§10.2). That is the single highest-value structural move in this analysis, because:

- it replaces a hand-maintained table with generated evidence;
- it makes Chapter 26's per-store rows derived data (store → *C* via TCK, *C* → guarantees via the matrix), so a store row can no longer contradict a TCK run;
- it gives the planner's refusal a *reason* ("`PER_STREAM_DENSE` requires `detectsWriteWriteConflict ∨ singleWriter`; your TCK report says neither"), which is both a better error message and a reviewable claim;
- it turns "which TCK tests gate which family" from judgement into derivation: the gating tests for a family are exactly the TCK tests that discharge the assumptions the family's matrix cell used.

**Counterexamples are the deliverable, not just passes.** A cell whose check fails should record the counterexample trace, and that trace should become a TCK test and a Hermitage-style probe (§14.3). "The model says this store will lose a write in this interleaving; here is the probe that reproduces it" is the artefact that makes the matrix trustworthy.

### 4.3 Monotonicity properties of the matrix worth checking

| Property | Statement | My expectation |
|---|---|---|
| **Capability monotonicity (guarantees)** | `C ≤ C′ ⟹ Guarantee(s, C) ≤ Guarantee(s, C′)` | holds; cheap to check; a violation means the model misuses a flag |
| **Capability monotonicity (resolution)** | a stronger capability spec never yields a weaker *resolved profile* | **fails by construction** (§6.4): enabling reasoning can let a reasoning-dependent scope win and declare `dal:ProvidedConcurrency` over a non-reasoning `dal:Optimistic` |
| **Strategy dominance** | the planner's "strongest strategy the backend can deliver" is a genuine maximum, not a maximal element of an incomparable set | needs checking; if the order is partial, "strongest" is ill-defined and `strongest(...)` silently picks by list order |
| **Declaration monotonicity** | strengthening a declared `min_level` never makes a previously refused deployment accepted | should hold trivially; cheap |

The second row is a real finding and a design question for the human (PV-Q1): should the compiler warn when a capability *increase* weakens a resolved guarantee? I think yes, and it is a two-line check once resolution is a function you can evaluate twice.

---

## 5. The assume-guarantee decomposition

Every safety property in the guide is discharged jointly by four parties. The generated SPARQL is one of them. Writing the split down is a prerequisite for any proof, and it does not currently exist in machine-readable form.

| Party | What it must do | Enforced today by | Verification approach |
|---|---|---|---|
| **Generated SPARQL** | guards (epoch, seq/value, tombstone, txn, claim-not-held), single-statement counter rewrite, head/chain maintenance, receipt and claim insertion, closure sweep | the templates | Alloy (state effect), TLA+ (interleavings), emitter typing (§13.4) |
| **Caller / adapter** | compute positions and digests; supply `opSeq`; confirm on the primary; resend identically on `Unknown`; re-decide on `PreconditionFailed`; never write infrastructure graphs; never read the version from a replica; retry with jitter; `clock.receive` before a read-dependent write; bounded retries | prose + library code | generate the obligation set from the spec; enforce at the port boundary; property-test the client state machine; model the client as a TLA+ process |
| **Housekeeping** | txn-claim TTL ≥ redelivery horizon; prefix-only pruning with low-water-mark-first and pinned heads; bucket rotation with registry update; epoch allocation from the declared authority; quiesce; erasure register replay; reconcilers; gap/fork audits | runbooks (ADR-A80) | TLA+ models of each procedure; monitors that prove the procedure ran (§15) |
| **Store** | the capability flags | TCK | TCK as assumption discharger; history checking |

**Finding (Major).** The *caller obligations* are the largest unverified surface in the whole design, and they are where the guide's own corrections concentrated (B8 outcome classification, B9 `clock.receive`, A5 digest, the resend-identically rule, the primary-only confirmation). They are also the part an adopter writes themselves if they use "only the generated SPARQL and walk away" — which the README explicitly supports. An adopter following §9's promise ("run both once and walk away") gets the SPARQL and none of the obligations.

**Recommendation (PV-D2).** Emit the obligations as **data**, per generated operation, in the compiled profile: for each operation, the preconditions the caller must establish, the postconditions it may assume, the outcome classification procedure, and the parameters it must compute (with their derivations). The compiler already emits reified `dal:ParameterBinding`s; this extends the same idea to obligations. Then:

- the obligation set is one artefact, verified once, consumed by the Python and Java adapters and by the TLA+ client process — removing the two-implementation drift;
- an adopter who takes only the `.rq` files gets a machine-readable list of what they must do, and can be told, mechanically, which guarantees they forfeit by skipping each one;
- `instantiate` can emit the obligations as comments in the `.rq` header, so the forfeited guarantee is visible at the point of use.

---

## 6. Resolution and precedence

### 6.1 What to prove (Isabelle, small)

Model the resolution function abstractly:

```isabelle
type_synonym dim   = string
datatype scope_kind = GraphPattern | Namespace | Class | Shape | EquivalentClass
record cand = scope :: scope_kind  priority :: int  reasoning :: bool  value :: val

fun resolve :: "cand list ⇒ bool ⇒ val option res"   (* bool = reasoning supported *)
```

Gated claims:

| Claim | Statement | Why it matters |
|---|---|---|
| **Determinism** | `resolve` is a function of the candidate *set*, not the list order | L1; a resolution that depends on Turtle parse order is unreproducible across machines, and the README promises "the same way every time, on any machine" |
| **Order independence** | `resolve (xs @ ys) = resolve (ys @ xs)` | the collection step must be a set operation |
| **Locality** | adding a candidate that does not match the target leaves the result unchanged | L2; makes configurations composable |
| **Winner dominance** | the winner's priority is maximal among surviving candidates, and if tied, non-reasoning | matches the stated algorithm |
| **Totality** | the result is always exactly one of `Baseline`, `Winner v`, `Ambiguity` | no fourth outcome, no exception path |
| **Ambiguity is exactly a tie** | `Ambiguity ⟷ ∃ two surviving candidates with equal priority, both reasoning or both not, with different values` | note the *different values* side condition: two candidates with the same value at the same priority should **not** be an ambiguity. Does the compiler treat it as one? (question) If it does, a configuration that says the same thing twice is refused, which is a usability bug; if it does not, the check must compare values, and value equality for literal-valued dimensions needs a definition (`xsd:long 64` vs `xsd:integer 64`) |
| **Negative lemma: capability monotonicity fails** | `∃ cands. resolve cands False` is *stronger* than `resolve cands True` under any sensible strength order on values | §4.3; proved with a witness, so the behaviour is a recorded decision rather than a surprise |
| **Baseline is reachable** | for every dimension there is a candidate set yielding `Baseline`, and the baseline value is in the dimension's value set | catches a baseline typo'd outside its enumeration |

All of this is a few hundred lines of Isabelle and it settles the resolution layer permanently. The negative lemma is the valuable one, exactly as the De Morgan witness is in the SQL review.

### 6.2 Target identification is the real problem

**Finding (Major, #1 and #2).** The README defines scope *matching* on resources and resolution on *targets*, and a target is "a class, plus a deployment". These are reconciled only if every instance of a class matches the same set of scopes — which is false for three of the five scope kinds:

- `dal:NamespaceScope` matches "resources whose own IRI starts with `dal:iriPrefix`". Two instances of one class with different IRI prefixes match different scopes. One target, two profiles.
- `dal:ShapeScope` matches "resources conforming to a named `sh:NodeShape`". Conformance is per-resource and data-dependent.
- `dal:GraphPatternScope` matches by graph prefix *and* class; the README handles this by making each graph-pattern scope its own target, plus "an unscoped fallback for instances outside any of them". That works **only if the declared graph prefixes form an antichain.** With `urn:g:lending/` and `urn:g:lending/behaviour/`, an instance in the inner graph matches both, giving two targets with different profiles for one instance, and no longest-prefix rule is stated.

Consequences:

1. **The instance → target map is a relation, not a function** (L3 fails). At runtime, "which generated operation applies to this instance?" has no unique answer, so a writer picks, and two writers can pick differently — which means two *different* version-row conventions and guard shapes for one aggregate. That is a lost-update hole created by configuration, invisible to every current check.
2. **Non-monotone scope membership.** SHACL conformance is non-monotone in the data (`sh:maxCount`, `sh:not`, `sh:closed`). A resource conforming at compile time can stop conforming after more data arrives. A profile "resolved once at compile time" is then stale, and the staleness is silent.
3. **The fallback target is not well-defined** without the antichain property.

**Recommendations.**

- **PV-D3.** Make target identification a declared, checkable function. Either (a) restrict profile-bearing scopes to those that are class-determined (`ClassScope`, `EquivalentClassScope`) plus `GraphPatternScope` with an enforced antichain and a longest-prefix rule; or (b) keep instance-level scopes but *refuse* any configuration in which two scopes with different resolved values can match one instance, which is a decidable check for prefix scopes (automata; §8.3) and for class scopes, and an undecidable-in-general check for shape scopes.
- **PV-D4.** Restrict `dal:ShapeScope` to a **monotone SHACL fragment** — no `sh:not`, `sh:closed`, `sh:maxCount`, `sh:qualifiedMaxCount`, `sh:lessThan`-family, `sh:sparql` — so that conformance, once established, cannot be lost by adding data. This is a cheap syntactic check over the shapes graph and it makes compile-time resolution sound. Otherwise refuse `dal:ShapeScope` for any dimension whose value affects the write path.
- **PV-X1.** An **antichain and overlap check** over all declared `dal:graphPrefix` and `dal:iriPrefix` values, with a counterexample IRI when it fails. Minutes of work; catches a class of configuration error that no current check sees.

### 6.3 `dal:EquivalentClassScope` is a syntactic approximation called reasoning

**Finding (Moderate).** The README describes this scope as matching "resources reachable through `owl:equivalentClass` and `owl:intersectionOf`", and marks it as the one scope kind that "needs reasoning". Those are different things. Syntactic reachability over two OWL constructs is neither sound nor complete for OWL entailment: it misses `owl:unionOf`, `rdfs:subClassOf` chains through restrictions, property-restriction equivalences and `owl:sameAs`; and it can over-reach, since `owl:intersectionOf` membership is a *subclass* relation in one direction only (a member of an intersection is a member of each conjunct; a member of each conjunct is a member of the intersection — the latter direction does hold for intersection, but reachability does not distinguish direction).

Either:

- define it syntactically, document it as a *syntactic* rule, and stop gating it on `dal:providesReasoning` (the rule needs no reasoner); or
- define the entailment regime (RDFS? OWL 2 RL? OWL 2 DL?), pin it, and check two independent reasoners agree on a corpus (T1 differential).

Formally, option 1 is strictly better for this layer: a syntactic rule is a decidable, implementable, provable function; an entailment regime drags in the reasoner as a trusted input and makes resolution depend on a reasoner's version. The README elsewhere avoids exactly this dependency deliberately (ADR-A78 point 4, refusing `rdfs:subPropertyOf dal:isCompositeOf` to avoid leaking entailments).

### 6.4 Per-dimension independence is the main source of incoherent profiles

Resolution is per dimension, and `dal:DataAccessProfile` is sugar that decomposes. That is a clean design, and it has one consequence worth stating formally: **the resolved profile is a product of independent choices, so the only thing standing between the adopter and an incoherent combination is the cross-axis table.** The completeness of that table is therefore a correctness property of the layer, not a convenience. §7 treats it.

A concrete instance the current table seems to miss (question, not assertion): `dal:lagWindowMillis` resolved from one profile node while `dal:globalReadStrategy` resolves to `dal:NoGlobalRead` from another. The table refuses the converse (lag-window read with no lag) but a dead parameter is a silent misconfiguration and the adopter believes they have a lag window. The general shape — **parameter resolved, owning strategy not selected** — applies to `dal:metaShards`/`txnShards`/`logShards`/`keyShards`, `dal:maxTraversalDepth` with a non-composite boundary, `dal:valueGuardProperty` with a named-graph boundary, `dal:opSeqRequired` with commit grain (this one *is* refused), `dal:priorMetaShards` without a change, `dal:asOfFloorSource` with `dal:PrefixOnlyRetention` and no as-of consumer, `dal:perSubjectScoped` with `dal:ReceiptOnly`, `dal:mergeRelation` without `dal:Merge`, `dal:claimsConstraint` on a non-claimed strategy, `dal:epochCoordinatorBinding` with `dal:StoreLocalEpoch`, `dal:erasureRegisterBinding` with `dal:NoErasure`. Each is a one-line rule; the point is that **the list should be derived from the dimension registry, not hand-written** (§13.2): for every parameter, declare which strategy values it belongs to, and generate both the refusal and the dead-parameter warning.

---

## 7. Validation: make it exhaustive, because it can be

### 7.1 The key observation

The cross-axis validation predicate is **propositional over finite domains**. Every dimension has a small enumerated value set; the refusals and warnings are conjunctions and disjunctions of equalities over those sets, plus a handful of integer comparisons (shard counts, depth, lag) and one list-membership condition (key property inside the boundary closure). That means it can be encoded as a BDD or an SMT formula over finite sorts and **checked universally**, not sampled.

This is the same point the SQL review makes about universally quantified laws, but here the quantification domain is genuinely finite and small enough that there is no excuse for example-based checking.

### 7.2 The size of the space, and why BDDs are the right tool

Rough product over the dimensions in the README's table (including "none" where absence is meaningful):

```
boundary 3 × firstWrite 2 × concurrency 4 × deadlock 3 × etagForm 2 × etagRep 2
× grain 2 × datasetTier 4 × globalRead 5 × contiguity 2 × receipt 3 × retention 2
× metaTopology 2 × epochAuthority 5 × epochGuard 2 × privacyClass 4
× erasureStrategy 4 × erasurePrecedence 3
≈ 1.3 × 10⁸
```

times the multiplicities for uniqueness constraints (0..n) and identity roles (8 roles × 7 strategies). Too large to enumerate, trivial for a BDD (≈60 boolean variables after one-hot or binary encoding, with the one-hot consistency constraints added).

### 7.3 The properties to check exhaustively (T3)

| # | Property | What a counterexample means |
|---|---|---|
| V1 | **Classification totality**: every combination is exactly one of refused, warned, or accepted-clean | an unclassified combination is a silent acceptance of something nobody considered |
| V2 | **No combination is both refused and accepted** by the two implementations (shapes vs compiler) | the drift in finding #3, found universally instead of by example |
| V3 | **Shape-checkable refusals ⊆ compiler refusals**, with the difference explained and enumerated | the README asserts this containment; prove it, and *list* the difference automatically so the asymmetry is reviewable |
| V4 | **Every accepted combination has a guarantee assignment** `Guarantee(s, C)` defined for every *C* | an accepted profile with no guarantee statement is a profile whose safety nobody has considered |
| V5 | **Refusal monotonicity**: weakening any single dimension to its baseline never turns a refusal into an acceptance *unless* the baseline is itself the safe value | catches rules written against the wrong polarity |
| V6 | **Operation-set totality and disjointness** (L5): every accepted combination maps to exactly one operation set | the selection table in §9 of the README is a lookup; prove it is a function and that its domain is all accepted combinations. The `dal:AppendOnly` row ("or event grain with any concurrency other than `dal:Optimistic`") overlaps the `dal:ProvidedConcurrency` row ("with commit grain") only if grain is read correctly — exactly the kind of overlap to check mechanically |
| V7 | **Every value of every dimension is reachable** in some accepted combination | an unreachable value is dead vocabulary, or a rule is too strong |
| V8 | **Every refusal rule is necessary**: removing it admits a combination no other rule refuses | a redundant rule is harmless; a rule that is *entirely* subsumed may indicate a mis-stated condition |
| V9 | **Every refusal rule is non-vacuous**: some combination triggers it | the vacuity class (D.3 A6). A refusal that can never fire is a false sense of coverage |
| V10 | **Warning coverage**: every combination that forfeits a guarantee is at least warned | the known-unsafe baselines (finding #5) make this the most important one |

**V10 deserves its own treatment.** Three baselines are known-unsafe-by-default: `dal:RowLevelGuardOnly` (epoch guard), `dal:AbsentRow` (create race on MVCC), `dal:ProvidedConcurrency` (unconditional write). The guide is explicit about each. But a warning is not a gate, and nothing associates a warning with the specific safety property it forfeits. Make that association data:

```
warning  dal:RowLevelGuardOnlyWarningShape
  forfeits  L14 (epoch safety)
  witness   trace: stale client matches an unrebased row after a bump
  gated-by  dal:epochGuardAcknowledged true     (proposed)
```

**Recommendation (PV-D5).** Every warning names the law it forfeits and the counterexample trace that demonstrates it, and acknowledging a warning is an explicit property in the configuration (as `dal:epochBumpAcknowledged` and `dal:acknowledgedSharedClassOverride` already are for two cases). Then the compiled profile records, per target, exactly which laws hold — and that list, not prose, is what a consumer reads.

### 7.4 Non-vacuity and witness obligations, generally

The single cheapest technique in this whole document, and the one that would have caught D.3 A6 and D.1's `sh:prefixes` defect in seconds:

> **For every constraint, refusal, warning, shape and audit query, produce a witness: a minimal input that triggers it, generated and checked in CI.**

Applied to:

- each SHACL shape in `shapes/constraints.ttl` and `shapes/persistent-foundation.ttl` → a violating fixture that it reports, plus a conforming fixture it accepts;
- each refusal and warning in the compiler → a configuration fixture (the README already has many of these in `examples/`; the obligation is that **every** rule has one, checked by coverage, not by author diligence);
- each shape in the guide's Appendix B → a store-state fixture that violates it;
- each audit query (S3 gap scan, F5 fork, the two §24.2 receipt-side audits, the four generated audits, the key-claim duplicate/merge/quarantine reconcilers) → a store state in which it returns a row;
- each `sh:sparql` constraint → a check that its `sh:prefixes` target carries `sh:declare` (D.1's finding, as a static lint).

This is T0, it is a few hundred lines of harness, and it converts "we have a constraint for that" into "we have a constraint that we have seen fire".

**Note the vacuity hazard specific to this layer.** The README says "every target also gets the four audits". For a `dal:NoBoundary` target there is no version row, so the gap-scan and fork audits are vacuously green. A vacuously green audit is worse than an absent one, because the operator reads it as evidence. Either refuse the combination, or label the audit's applicability in the compiled profile so the monitor can report "not applicable" rather than "clean".

---

## 8. Templates and the generated SPARQL

### 8.1 The static checks that are worth having, and why

These are cheap, local, fully automatic, and each corresponds to a defect class in Appendix D or to a stated SPARQL fact. Run per compile.

| # | Check | Grounding | Consequence of failure |
|---|---|---|---|
| S-1 | **Every graph is explicitly named** in every guard and every template quad; no reliance on the default graph; no `WITH`/`USING` | union-default-graph stores (fact) | a guard that reads every graph in the dataset |
| S-2 | **No unbound `GRAPH ?g`** in any audit, resume or confirmation query; bucket sets come from the registry as `VALUES` | F6, D.1 | full-dataset scan; prefix-matching unrelated graphs |
| S-3 | **Every variable in an INSERT template is bound in every solution**, or is on an explicit allow-list of deliberately-optional positions (`pat:prevRev` only) | SPARQL Update skips a template triple whose variables are unbound in that solution (fact) | a silently missing triple. If `?digest` were ever unbound, the claim lands with no digest and the confirmation reports `Applied` for a different request — i.e. defect A5 reintroduced *silently* |
| S-4 | **No blank nodes in any INSERT template** | blank nodes in an INSERT template are fresh per solution per execution (fact); blank nodes are illegal in DELETE templates (fact) | a retry is **not** a no-op: it inserts a second set of fresh blank nodes. This interacts directly with the idempotency design and with the README's own note that compiled profiles have unstable blank-node labels |
| S-5 | **Guard functionality**: the guard sub-pattern yields at most one solution for ground subject and predicate, given the `sh:maxCount 1` invariants; any non-ground template value must not vary per solution | F7, F11 | duplicated receipts, multi-valued version rows |
| S-6 | **`NOW()` only on audit-only lines**, never in a `FILTER`, `ORDER BY`, IRI construction or digest input | §23.4 policy | non-determinism; a guard that depends on server clock |
| S-7 | **Datatype pinning**: every `seq`, `epoch`, `fence`, `opSeq`, counter literal is `xsd:long`, in both templates and guards; arithmetic re-typed portably (`STRDT(STR(?n+1), xsd:long)`) | numeric promotion returns `xsd:integer`; BGP matching is term-based (fact) | a guard that cannot match; a shape that rejects a value a `FILTER` accepted (§8.2) |
| S-8 | **Well-designed pattern check**: no variable bound only inside an `OPTIONAL` is used outside that `OPTIONAL` within the same group graph pattern | well-designedness (Pérez/Arenas/Gutierrez; Angles & Gutierrez) ***(verify exact formulation)*** | non-monotone `OPTIONAL` semantics, evaluation-order dependence across engines |
| S-9 | **`FILTER NOT EXISTS` vs `MINUS` discipline**: use `NOT EXISTS` where the inner pattern shares variables; never substitute `MINUS` | the two differ when the patterns share no variables, and `MINUS` on disjoint variables removes nothing (fact) | a guard that removes nothing |
| S-10 | **Delete/insert overlap**: no triple appears in both templates under the same bindings unless deliberate (SPARQL deletes before inserting, so an overlapping triple survives) | fact | a "rewrite" that is a no-op; a tombstone that is immediately re-asserted |
| S-11 | **Property paths appear only in `WHERE`**, never in a template | fact; the README states it for the composite boundary | parse failure |
| S-12 | **Zero-padding and width**: any position embedded in an IRI is padded to the declared width, consistently, in templates and client code | B13, §10.2 | lexicographic order ≠ numeric order; two widths = two schemes |
| S-13 | **Request-size and operation-count budget** against `maxRequestBytes` for the biggest realistic payload and closure | capability flag | runtime failure under load only |
| S-14 | **Multi-operation requests**: if any generated `.rq` contains `;`-separated operations, record that intermediate states are visible to later operations and that atomicity is per *request* (SHOULD, not MUST) | SPARQL 1.1 Update (fact) | a "single guarded write" that is two writes on a store that does not honour the SHOULD |

**Judgement.** S-3 and S-4 are the two I would implement first. Both are unconditionally checkable from the template text plus the parameter binding list, both have severe and silent consequences, and S-4 in particular is the kind of thing that works in every test (where a retry is rare) and fails in production (where it is not).

### 8.2 A term-equality versus value-equality divergence worth naming

**Finding (Moderate).** The guide's fencing-token guard is

```sparql
GRAPH <urn:g:meta/17> { <urn:g:orders/1> pat:fence ?f }
FILTER(?f <= "7184"^^xsd:long)
```

The BGP binds `?f` to whatever term is stored; the `FILTER` compares by **value**, so an `xsd:integer` fence satisfies the comparison. But `pat:VersionRowShape` pins `sh:datatype xsd:long`, so the same store state is a shape violation. And the `DELETE { ... pat:fence ?f }` removes the exact term, so the rewrite is correct. Net effect: a datatype-drifted fence is *accepted by the guard*, *rejected by the shape*, and *silently normalised by the write*. The same divergence applies anywhere a guard uses `FILTER` on a numeric (the fence, the keyset-pagination predicates, the gap scan's arithmetic) rather than a ground BGP term (the `seq` guard).

This is exactly the kind of property the SQL review's "typed IR" recommendation addresses, transposed: **give the IR distinct types for *term-matched* and *value-compared* positions**, and refuse to emit a value comparison on a position whose invariant is term-based, or vice versa. A few hundred lines; removes the class rather than testing for it.

### 8.3 Template parameter substitution (L7)

The emitter is the one program component where verification is proportionate, because the consequence of a bug is injection (QP1) or a structurally different query.

Properties:

| # | Property | Technique |
|---|---|---|
| E1 | `parse(render(t, σ)) = subst(parse(t), σ)` for every template and every well-typed σ | property-based over generated σ including adversarial strings; differential against a second renderer |
| E2 | No σ can change the parse tree's shape: for all adversarial σ, `render` either produces a query whose algebra differs from `subst` only in leaf terms, or refuses | fuzzing with an injection corpus (the guide's L8 suite) plus a parse-tree-shape comparison, which is a much stronger oracle than "no exception" |
| E3 | Typed rendering: `IRI` → absolute-IRI-escaped or refusal; `Long(n)` → `"n"^^xsd:long`; strings escaped per Turtle/SPARQL rules; language tags well-formed | SMT strings / automata on the escaping function; exhaustive over escape classes |
| E4 | Determinism and idempotence: `render(t, σ)` is byte-identical across runs and machines | permutation/repeat test (QP4) |
| E5 | Parameter completeness: every variable in `t` is either in σ's domain or on the deliberately-optional list (S-3) | static, per compile |
| E6 | Round trip on the compiled profile: `instantiate(emit(resolve(cfg)))` is a function of `cfg` alone | metamorphic |

**Finding (Moderate, #10 and related).** `Version.parse_etag` splits on `-` and integer-parses both halves. `dal:TaggedRepresentation` offers `"3-41.ttl"`. Also an unpadded `"10-3"` versus `"3-41"` sorts wrongly if an ETag is ever used as a sort key or a cache key, against the fixed-width discipline used everywhere else. The ETag grammar should be a declared regular language with a generated parser and a generated printer, and a proof (automata) that printer ⊆ grammar and parser ∘ printer = identity, for both representation modes. Ten lines of specification; removes a whole class of adapter bug.

### 8.4 The composite boundary: two findings

**Finding (Major, #9, part).** "A composite boundary currently binds only the first property its shape reaches." If the closure is swept and rewritten but only one property is bound, then members reached by the other properties are **not deleted**, which leaves precisely the dangling triple that whole-replace exists to prevent (the guide's own motivating example: three line items down to two). This is not a limitation, it is unsoundness of the aggregate-replace contract for every composite-boundary family. It should be a refusal until implemented, not a known limitation.

**Finding (Major, new).** There are two closures and they can differ:

- the **compile-time** closure, computed by walking `sh:property`/`sh:node` offline, with a cycle check and `dal:maxTraversalDepth`;
- the **runtime** closure, bound in the generated `WHERE` by a SPARQL property path.

SPARQL 1.1 has `*`, `+`, `?` but **no bounded repetition `{n,m}`** (fact — it was removed from the specification before Recommendation). So a depth-bounded closure cannot be expressed as a property path. Therefore either the generated path is unbounded (and the runtime sweep can reach deeper than `dal:maxTraversalDepth`, including around cycles the compile-time walk refused), or the path is an explicit fixed-length alternation enumerated to depth *n* (and the query grows with depth, and the declared depth becomes part of the query text, so changing it is a recompile). Which it is, is a question for the compiler; either way the *equality of the two closures* is a property to state and check, by automata over the property alternation and by Alloy over small instance graphs.

**Finding (Major, new).** **Composite closures are not guaranteed disjoint across roots.** Nothing in the shape-based definition prevents a node from being reachable from two roots. Two aggregates then overlap; each root's replace sweeps the shared node; their version rows are different, so the two writers do **not** collide; and the last writer wins on the shared triples while both receipts claim success. For `dal:NamedGraphBoundary` disjointness is structural (one graph per aggregate). For `dal:CompositePropertyBoundary` it is an unstated precondition.

This is the single best Alloy target in the layer:

```alloy
pred overlap { some r1, r2: Root, n: Node |
  r1 != r2 and n in closure[r1] and n in closure[r2] }
assert ClosuresDisjoint { not overlap }
check ClosuresDisjoint for 5
```

Expect a counterexample in seconds for any shape with a shared-reference property. The remedy is a compile-time check: for each pair of root classes reachable from the shape set, prove that no node class is reachable from both, or require an inverse-functional/ownership annotation on every closure edge, or refuse.

### 8.5 Guard composition

The port accepts `guards: List<GuardPattern>` — business preconditions compiled into the same atomic guard. That is the right design and it is also an open hole: arbitrary caller-supplied patterns can

- bind variables that collide with template variables (`?s ?p ?o`, `?n`, `?prevRev`, `?rev`) and silently change the templates' cardinality or bindings;
- introduce unbound-variable `OPTIONAL`s, breaking S-8;
- make the guard non-functional, breaking S-5 and duplicating receipts;
- read graphs outside the aggregate, which is the write-skew exposure the SQL review raises for SQL guards, in exactly the same form;
- contain `NOW()`, `UUID()`, `RAND()`, or a property path with surprising cost.

**Recommendation (PV-D6).** Give `GuardPattern` a typed, restricted grammar: a conjunction of ground-subject BGP triples within the aggregate's own graph (or a declared read set), plus `FILTER`s over bound variables with a whitelisted function set, with variables drawn from a reserved namespace that cannot collide with template variables. Then S-5 and S-8 are preserved by construction, and the read set becomes a declared input to the concurrency model (§10, model A), which is what makes the write-skew question answerable at all.

---

## 9. The query side: resume, audit, as-of, confirmation

These are read queries, and their correctness is *detection* and *completeness* rather than state change. They have already produced four recorded defects (S6's as-of, S3's gap scan twice, F5's fork query, S2's `COALESCE`), which is the strongest signal in the corpus that this is where to point a checker.

### 9.1 What to prove (Isabelle, small and high value)

| Claim | Statement | Replaces |
|---|---|---|
| **Keyset predicate = lexicographic order** | `(seq > s) ∨ (seq = s ∧ opk > o)` ⟺ `(seq, opk) >lex (s, o)`, with `opk = COALESCE(op, 0)` and the side condition `op ≥ 1` where present | S2 correctness; the `COALESCE` trap; off-by-one on resume |
| **Page completeness** | with an ordered, bounded stream and a monotone cursor, iterating pages delivers every element exactly once | "exactly-once per position" (TCK O-7) proved rather than tested |
| **Gap-scan soundness and completeness** | given `L ≤ S+1`, all receipts for a target have `seq ≤ S`, and `pat:seq` is single-valued per receipt: `|{seq ∈ [L,S]}| = S − L + 1` ⟺ the retained prefix is contiguous and complete | D.1 and D.3 B7, settled permanently, **with the side conditions made explicit** — the valuable part, because the side conditions are the invariants the rest of the design must maintain |
| **Gap-scan detects prefix, suffix and total loss** | three negative lemmas with witnesses | the exact three cases the README now claims; each becomes a regression-proof |
| **Fork detection** | with deterministic revision IRIs, `two txn claims on one revision` ⟺ `two writers committed a CAS from one prior version`, under the stated isolation failure | D.3 A6; proves the audit is the *right* audit, not merely a non-vacuous one |
| **As-of correctness** | the triple-level as-of `CONSTRUCT` equals the fold of asserts/retracts up to the position, given no blank nodes in deltas and per-target scoping | D.1's S6 correction; the proof's side conditions are exactly "skolemise deltas" and "constrain `?r2` to the same target", which is how you know the fix is complete |
| **Contiguity blind spot** | the per-target contiguity check cannot detect a skipped *last* write; the row-driven S3 check can | the README states this; prove it, so the compensating control is justified rather than asserted |
| **Position order is total** | `(epoch, seq, opSeq)` lexicographic is a total order, and the zero-padded decimal string order agrees with it at the declared width | B13 |

### 9.2 What to check with Alloy (bounded, structural)

Model the store state (§3.2) and encode each audit query as a relational expression. Then, for each invariant *I* and its audit *A*:

```alloy
assert DetectionComplete_I { all s: State | violates[s, I] implies some rows[A, s] }
assert DetectionSound_I    { all s: State | some rows[A, s] implies violates[s, I] }
check DetectionComplete_I for 6
```

The invariants to cover (L11):

| Invariant | Audit claiming to detect it | Expected result |
|---|---|---|
| per-target receipt contiguity above the low-water mark | S3 gap scan | should hold after D.3; worth proving |
| no fork (one revision, two txns) | F5 query / `pat:TxnCardinalityShape` / receipt-side audit (1) | holds only with deterministic revision IRIs — make the dependency explicit |
| no duplicate application (one txn, two revisions) | receipt-side audit (2) | holds; depends on receipts outliving claims |
| at most one owner per key claim | `pat:KeyClaimShape` + reconciler | holds |
| `pat:head` resolves to a retained receipt | **no audit** | **gap**: the pinned-head mechanism maintains it, but nothing checks it. A dangling `pat:head` breaks S4, the chain, and the next CAS's `pat:prevRev`. Add an audit |
| version row single-valued (`seq`, `epoch`, `head`, `deleted`) | `pat:VersionRowShape` (only where commit validation exists) | **gap** on non-validating stores: add a standing audit, since F7's failure mode is exactly multi-valued `seq` |
| chain integrity (`prevRev` forms one path per target) | TCK T-4 only | **gap**: no standing audit. The chain is the audit trail; it should be checked in production, not only under fuzz |
| every receipt's target has a version row | **no audit** | **gap**: catches bulk loads that wrote receipts without rows |
| every graph in the dataset is registry-listed or declared infrastructure | **no audit** | **gap**: catches stray graphs from administrative `LOAD`, half-finished bulk cutovers, orphaned deltas/snapshots |
| no payload graph outside its family's declared pattern | **no audit** | **gap** |
| tombstoned rows have empty payload | **no audit** | **gap** |
| delta/snapshot graphs referenced by a retained receipt exist, and vice versa | **no audit** | **gap**: orphaned deltas are storage leaks; missing deltas break as-of silently |
| key claims reference existing owners | reconciler (partially) | partial |
| retention low-water mark ≥ all pruned seqs and ≤ S+1 | **no audit** | **gap**: a wrong mark makes S3 lie in either direction |

**Judgement.** Nine gaps in detection coverage, in a design whose own stated philosophy is "the reconciler is never the only strategy, and it is never absent" and whose threat model explicitly includes bulk loads, administrative `LOAD`s and restores that bypass every guard. The audits are the only control for that threat, and their coverage has never been enumerated. **This is the most under-defended part of the layer, and it is also the cheapest to fix**: each gap is a SPARQL query over infrastructure graphs, each is a metric, and the Alloy obligation above tells you when you have enough of them.

### 9.3 Differential query checking (T1)

For the read queries, run them against two or three independent engines (Jena, RDF4J, Oxigraph) on generated store states, and compare. This catches engine-dependent semantics (`OPTIONAL` ordering, `NOT EXISTS` scoping, numeric promotion in `FILTER`, `ORDER BY` on mixed types, aggregation with unbound) that no single-engine test will see, and it is the empirical arm of S-8. Generated store states should include: empty payload, empty log, pruned prefix, pinned heads, epoch-crossing streams, tombstoned rows, recreated rows, multi-valued rows (damaged state, to check the audits fire), cycles in composite closures, and mixed datatypes.

---

## 10. Protocol models: the centrepiece

This is where the defects are, where tests are weakest, and where the guide's own corrections cluster. It is also what the SQL review identifies as rung T4, never attempted.

### 10.1 Modelling discipline

- **Model the isolation *contract*, not the engine.** Read and write sets, snapshots, commit points, conflict detection granularity. Three levels (READ COMMITTED with per-statement snapshots, SNAPSHOT with and without write–write detection, SERIALIZABLE), plus flags for statement-versus-graph conflict granularity and for atomic-request semantics. Published TLA+ specifications of snapshot isolation and SSI exist and can be adapted ***(verify current sources)***.
### 10.1 Modelling discipline *(continued)*

- **Parametrise by the capability record**, so one model yields the §4.2 matrix row for its pattern rather than a single yes/no. One `.cfg` per capability profile, one run per cell, one recorded verdict (plus counterexample) per cell. This is what makes the models pay for themselves: a single model of the guarded write, checked across eight capability profiles, replaces eight hand-written claims in Chapter 26 and keeps them honest when a store's TCK result changes.
- **Model the caller as a process, not an oracle.** Every recorded defect in the B-series (B8 outcomes, B9 `clock.receive`, A5 digest, resend-identically, primary-only confirmation) lives in the caller. A model whose client always does the right thing proves nothing about the system as deployed. The client process should be able to misbehave in declared ways, so that each misbehaviour's consequence is a recorded counterexample rather than a surprise.
- **Model crashes and transport failures explicitly**, at every point the guide identifies: after send and before commit, after commit and before response, after response and before confirmation, during confirmation, between the two steps of the retention job, between quiesce and epoch allocation.
- **Model the out-of-band writers.** Bulk load, administrative `LOAD`, restore, a rogue ETL. These are in the stated threat model and they are what the audits exist for. A model without them cannot evaluate L11.
- **Keep each model small.** A few hundred lines, one concern, named safety and liveness properties, and a recorded scope. Twelve small models beat one large one: the large one will not finish, and when it does you will not know which assumption carried the proof.
- **State the scope in the claim.** Bounded model checking at 2–3 writers, 2 aggregates, 2 epochs, 3 sequence values is enough for every defect in Appendix D. Record the bound; do not let a bounded pass be read as universal (the SQL review makes the same point about Alloy).

### 10.2 The models

Fourteen models. Each lists the system, the properties (S = safety, L = liveness), and what I expect it to find. The "expected finding" column is a prediction and therefore falsifiable — which is the point: a model that finds nothing it was expected to find is evidence that either the design is sound or the model is wrong, and the grounding step (§14.3) distinguishes those.

| # | Model | System modelled | Properties | Expected finding |
|---|---|---|---|---|
| **A** | **Guarded CAS (the core)** | §19.1 write: dataset epoch guard, row epoch read-and-rebase, `seq` CAS, tombstone guard, txn-claim `NOT EXISTS`, `OPTIONAL` head, payload sweep, receipt insert; client computes positions and digest; confirmation on primary; retry rules | S: at most one receipt per `(target, epoch, seq)`. S: a committed write's guard held at its commit point. S: `pat:head` always names a receipt that exists. S: `prevRev` forms one unbroken path per target. S: `seq` dense from 1 per target. L: a client that keeps retrying eventually applies or learns a definite outcome | With `detectsWriteWriteConflict = false` and `maxIsolation = SNAPSHOT`: two writers both commit, producing the *same* revision subject with two `pat:txn` values — reproducing D.3 A6's corrected analysis as a trace, which is exactly the evidence that `pat:TxnCardinalityShape` is the right audit. With caller misbehaviour "re-issue the same delete/insert set on `PreconditionFailed`": a lost domain decision |
| **B** | **Append form** | §10.1: server-side `?n+1` on the shared statement, `VALUES`-supplied `opSeq`, dataset guard, row rebase, txn guard, head/chain maintenance | S: allocation order = commit order. S: no `seq` consumed by an aborted transaction. S: `opSeq` distinct within a revision. S: no duplicate application while the claim is retained. L: no stall | With pre-allocation (modelling `nativeSequence` instead of the in-transaction counter): the G2/A2 reader-skip trace. With claim TTL < retry horizon: the A4 double-append. **Both are regression proofs for corrections already made** |
| **C** | **First write and the create race** | `dal:AbsentRow` create-if-absent vs `dal:PreCreatedRow` bootstrap; concurrent creators; both under each isolation level | S: exactly one creator wins. S: no payload lands without a row. S: no row at `seq 0` is mistaken for a written aggregate | `dal:AbsentRow` + SNAPSHOT without write–write detection: two creators both commit (P2 write skew), two payloads merged into one graph, two receipts at `seq 1` with the **same** revision IRI. Since `dal:AbsentRow` is the **baseline**, this is a default-unsafe configuration (finding #5) and the model turns it into a trace |
| **D** | **Key claim (P1/P2/P3)** | claim guard, `claimedBy` cardinality, retire, rotation (`dal:Dual` two-version write), P3 sentinel counter with sharding, external allocator (P6) | S: at most one owner per claim, per scheme version. S: rotation opens no window where a key is claimed under neither version. S: a retire is only by the owner. S: ownership monotonicity (the premise of the race-free post-`ASK`) | Write skew without P3/serialisable. **Rotation under concurrent retire**: during `dal:Dual`, if a retire removes only one version's claim, the key is half-claimed — I would check this specifically, because the rotation state machine is four states and the write is "guards and inserts both versions in one update", but the *retire* path's dual behaviour is not described. Also: erasure under `dal:ErasureWins` physically deletes a claim, which **breaks ownership monotonicity**, so the post-`ASK` can now produce a false negative for a concurrent legitimate owner. The guide acknowledges the monotonicity break; the model shows its consequence for the confirmation procedure |
| **E** | **Outcome classification** | the §15.2 decision procedure: claim present/absent × digest equal/differs × epoch same/changed × tombstoned/not, plus replica reads, plus a request still in flight | S: totality (every history yields a verdict). S: disjointness. S: soundness — `Applied` ⟹ exactly one application of *this* request; `PreconditionFailed` ⟹ no application; `IdempotencyKeyReuse` ⟹ a different request used the id. L: `Unknown` is resolvable by the stated procedure | Confirmation on a replica returning `absent` for an applied write (B-series, already corrected — keep as a regression proof). A confirmation taken while the original is still executing: the guide says it is not definitive; the model should show the resend-then-confirm procedure *is* definitive, and that is a liveness property depending on the server's maximum request duration being enforced. **If the digest is unspecified (§12 finding #7), `IdempotencyKeyReuse` can fire spuriously; the model exposes that as a violation of soundness of the `Applied` verdict's complement** |
| **F** | **Epoch bump and restore** | quiesce, allocation from each of the four authorities, dataset-node write, row rebase on next write, stale-ETag rejection, consumer resync, double restore of one backup, `dal:RowLevelGuardOnly` vs `dal:DatasetLevelGuard` | S: no position minted under epoch *e* is accepted as epoch *e′*. S: no revision IRI reused. S: a double restore never reuses an epoch. S: no row is permanently wedged (the A1 liveness property). L: every row eventually rebases | `dal:StoreLocalEpoch` + double restore: epoch reuse (warned today). `dal:RowLevelGuardOnly`: stale client matches an unrebased row — the warned baseline, as a trace. Insufficient quiesce (< max transaction duration): a pre-bump CAS commits post-bump. **A1 as a regression proof**: guard on both epochs ⟹ no write can ever apply |
| **G** | **Retention and pruning** | bucket rotation, registry update, low-water-mark advance, pinned-head copy, drop, reader enumerating buckets, as-of floor, claim TTL prune | S: a dropped bucket contains no live head. S: the low-water mark is never below a surviving receipt (the crash-safe ordering). S: a reader never enumerates a bucket set that misses a retained bucket. S: as-of never reads across a hole. L: retention makes progress despite dormant streams | A7 (dormant head) as a regression proof. **New: the registry is unguarded** (§3.2 finding), so a reader computing `VALUES ?log { ... }` concurrently with rotation can miss a bucket, making the gap scan report false loss — or add a bucket mid-query, making it report false completeness. **New: the pinned-head graph is itself unbounded** unless entries are removed when heads move; the README says the job removes them, so the model should check that removal cannot race a CAS that moves the head |
| **H** | **Global read (dataset tier)** | HLC stamped pre-commit, each of the four `dal:globalReadStrategy` options, lag budget derived from enforced transaction duration, late-arrival audit, per-target contiguity | S: no committed receipt is permanently skipped. S: contiguity check detects any skip it can detect. L: freshness bound | A3 (unbounded read) as a regression proof. A lag budget that omits replica lag or clock skew. `dal:NoGlobalRead` declared alongside a dataset tier (warned today) producing no reader at all, so the late-arrival audit never runs. **The blind spot the README names — a skipped *last* write — should be confirmed as genuinely uncoverable by the contiguity check and covered by the row-driven scan** |
| **I** | **Fencing and external locks** | lease acquire, GC pause, lease expiry, second acquirer, fence check-and-advance in one operation, `dal:LockingConcurrency` with no generated guard | S: a writer whose lease lapsed cannot apply. S: the fence is monotone. L: the lock is eventually acquirable | The §16.2 check-without-advance defect as a regression proof. **`dal:LockingConcurrency` generates no guard at all**, so the model has nothing to check inside the store: the entire safety argument is external, and the model's job is to state the external obligation precisely (mutual exclusion per aggregate, fence advance, bounded clock skew) so it can be discharged by something. This is the one dimension where the compiler's output carries *no* safety and the obligation must therefore be explicit |
| **J** | **Infrastructure-graph writers** | the epoch authority, the bucket-rotation job, the retention job, the shard-count migration, concurrent readers and writers | S: single-writer assumptions hold or violations are detected. S: readers see a consistent registry/retention view | **I expect this to be the richest model**, because none of these writers is guarded (finding in §3.2). Expected: lost updates between the retention job and the rotation job; a reader seeing a half-rotated registry; a shard-count migration racing an ordinary write; the dataset node rewritten by two restore attempts |
| **K** | **Erasure** | per-subject aggregate drop or crypto-shred, version-row tombstone, key-claim handling under both precedence values, decision record first, register append, restore replay, patch-log/snapshot per-subject condition, backups | S: after erasure plus the retention bound, no modelled store yields the subject's plaintext or pseudonym. S: no other subject's data is affected. S: a restore cannot resurrect an erased subject | Every store the guide lists, enumerated: deltas, snapshots, pinned heads, backups, replicas, the key graph, the external allocator (P6's `key_claim` table and its `norm_key` column — **personal data in PostgreSQL, outside the RDF erasure path entirely**), the outbox, CDC consumers. The allocator table is the one I would expect to be missed, because P6 is described as an availability/contention choice and its privacy consequence is not stated |
| **L** | **Multi-aggregate writes** | two version rows in one request, each `dal:deadlockPolicy`, saga via outbox, `multiAggregateAtomicity` absent | S: no partial application visible as success. S: no deadlock or livelock under the declared policy. L: progress | `dal:SortedAcquisition` with a single guarded update (warned today): SPARQL specifies no evaluation order, so the policy is unenforceable — the model shows the warning is really a refusal in disguise. `dal:EngineDetectAndRetry` on an engine that neither detects nor aborts: livelock |
| **M** | **Bulk load and cutover** | offline position assignment, staging graphs, the gate (P7 + S3 + F5 + shapes), batched cutover under the epoch guard with writers quiesced per affected stream, flip, re-admit | S: no acknowledged write lost across the cutover. S: version rows advance to high-water marks consistently. S: no stream is live under two position schemes | The guide already says a single transaction over every row is not portable and that batches must quiesce the affected streams. The model should establish *which* streams must be quiesced and for how long, and whether a stream touched by two batches can interleave with an ordinary write between them |
| **N** | **Shard-count migration** | `dal:metaShards` change with `dal:priorMetaShards` and `dal:epochBumpAcknowledged`, version rows moving between shard graphs, readers using the old modulus | S: every row is reachable under exactly one modulus at any time. S: no row is lost or duplicated. S: the epoch bump makes stale readers resync | The README refuses the change without an acknowledged bump, which is the right gate. The model's value is in the *procedure*: moving rows is itself a set of writes, and those writes are not guarded by anything (they rewrite version rows in a new graph while the old ones still exist). Expect a window where both copies are live |

### 10.3 Properties that cut across all models

| Property | Why it belongs at the top level |
|---|---|
| **No position is ever reused** across epoch bumps, tombstone/recreate, shard migration, bulk cutover, restore | this is L14, and it is violated by composition even when each procedure is individually correct. Four of the fourteen models touch it; only a combined invariant catches the composition |
| **Every acknowledged write has exactly one receipt, and every receipt has at most one acknowledged write** | the audit pair in §24.2 checks both directions; the model should prove they are the right pair |
| **Receipts outlive claims** | the premise of the receipt-side audits. A retention policy that prunes receipts faster than claims breaks the audits silently |
| **Every invariant has a detector** (L11) | the obligation from §9.2, checked against the model's reachable violating states: for each reachable bad state, some audit fires |
| **Infrastructure writes are either guarded or single-writer-by-construction** | model J's conclusion, lifted to a design rule |

### 10.4 Grounding the models against reality

A model of a store is only as good as its fidelity, so the models must be checked against the store, not merely against each other. Three mechanisms, in increasing cost:

1. **Hermitage-style isolation probes** per backend, one per anomaly the models predict (dirty write, lost update, read skew, write skew, phantom). These populate the capability record's isolation fields with evidence and are cheap.
2. **History checking.** Run the generated operations under randomised concurrent workloads and check the recorded histories for the anomalies the models predict, Elle-style (Kingsbury & Alvaro, VLDB 2020) ***(verify applicability to this data model — Elle's inference relies on list-append or register semantics, and the version-row-plus-receipt structure is a natural register-with-history, which should fit, but the encoding needs design)***. The guide's TCK already describes most of the fault injection; history checking adds the *inference* that turns "no exception observed" into "no cycle in the dependency graph".
3. **Predicted-anomaly reproduction.** For each counterexample trace the models produce, write a TCK test that attempts to reproduce it on a real store. Two outcomes, both informative: reproduced ⟹ the model is faithful and the store is as classified; not reproduced ⟹ either the store is stronger than classified (update the capability record) or the test is too weak (strengthen it). This is the T4 analogue of seeded mutations, and it is what makes the matrix trustworthy.

**Judgement.** The TCK is already a strong artefact — stronger than most projects have. Its weakness is that its test list is hand-derived from prose, so its coverage is unmeasured, and the gating set (K-1, K-3, O-2, T-1, T-2, T-12 to T-14, the R-suite, S-1, S-2) is a judgement call. Deriving the TCK's obligations from the models makes coverage measurable: **every assumption a matrix cell uses must be discharged by a named TCK test**, and every model counterexample must have a reproduction attempt. That is a mechanical completeness criterion for a suite that currently has none.

---

## 11. Isabelle: what is worth proving, concretely

The SQL review's advice applies unchanged: the theory and the gate discipline already exist, so extensions are cheap. Four theories, roughly 1.5–2k lines total.

### 11.1 `Resolution.thy`

Contents as §6.1. The negative lemma (capability monotonicity fails) is the one that pays, because it converts a surprising behaviour into a recorded decision.

### 11.2 `Positions.thy`

```isabelle
type_synonym pos = "int × int × int"        (* epoch, seq, opSeq *)

definition pos_le :: "pos ⇒ pos ⇒ bool" where ...          (* lexicographic *)
definition pad :: "nat ⇒ int ⇒ string" where ...           (* fixed-width zero-pad *)
definition rev_iri :: "string ⇒ int ⇒ int ⇒ string" where ...
```

Gated claims:

- `pos_le` is a total order.
- **Order agreement**: for all `e, s < 10^w`, `pad w e @ pad w s` is lexicographically ordered iff `(e,s)` is numerically ordered. This is the B13 defect as a theorem, and the side condition `< 10^w` is exactly the width obligation the guide states and the compiler should check against the declared `xsd:long` range (SMT, §12).
- **Injectivity of `rev_iri`** on `(target, epoch, seq)` given a prefix-free or fixed-width encoding, hence the F2 collision cannot recur, and hence (as a corollary) the fork signal is `pat:txn` cardinality rather than shared `prevRev` — which is D.3 A6's analysis, proved.
- **Width uniformity**: two widths produce two schemes, stated as a negative lemma with a witness (`e10` sorts before `e3`).
- **Keyset predicate = `pos_le`**, as §9.1.

### 11.3 `Encoding.thy`

```isabelle
definition enc :: "string list ⇒ byte list" where     (* length-prefixed: len ":" bytes *)
```

Gated claims:

- **`enc` is injective** on lists of strings. The proof is the prefix-free-code argument, and it is the B11 defect as a theorem (`["a|b","c"]` vs `["a","b|c"]` collide under separator joining; they cannot under `enc`).
- **Negative lemma**: separator joining is not injective, with the witness. This makes the defect a proved fact, so a reverted fix fails the build.
- **Digest determinism** modulo the canonicalisation obligation: `digest(kind, target, expected, canon(payload))` is a function, *given* that `canon` is a function. Which is exactly where finding #7 bites: `canon` is currently "sorted canonical N-Triples", which is not a function unless the lexical normalisation, the `xsd:string` question and the escaping are pinned. **The proof should be stated with `canon` as a parameter and an explicit assumption, so the unproved part is visible.** That is the honest way to carry an under-specified dependency: not by assuming it away, but by naming it as a hypothesis that something else must discharge.
- **Pipeline idempotence**: `nfkc_casefold ∘ trim` is idempotent. Mechanising Unicode is out of proportion; axiomatise the ICU mapping's properties (idempotent, order-independent with trim under stated conditions) and discharge them by property test against ICU (T1). State the axioms explicitly so the trust boundary is visible.

### 11.4 `Outcomes.thy`

The §15.2 decision procedure as a total function from observations to outcomes, with the history as an abstract parameter.

```isabelle
datatype obs = Obs (claim: "(rev × digest) option") (dsEpoch: int) (deleted: bool) (reqEpoch: int) (reqDigest: digest)
datatype outcome = Applied | PreconditionFailed | Gone | EpochChanged | IdempotencyKeyReuse | Unknown

fun classify :: "obs ⇒ outcome" where ...
```

Gated claims: totality, disjointness, and **soundness relative to an abstract history predicate** — `classify o = Applied ⟹ applied_once h req`, and so on. The soundness proofs need the history model, which means this theory is the bridge between Isabelle and the TLA+ models (model E). The practical form: prove the classification correct under stated assumptions (confirmation on the primary; monotone claim ownership; claim retained; digest is a function), and let model E check that the protocol establishes those assumptions. **Each assumption is then an explicit obligation with a named discharger** — which is the assume-guarantee discipline of §5 applied at the level of a proof.

This theory also yields a lemma worth having explicitly: **`classify` never returns `Applied` on the basis of claim presence alone**, which is the A5 defect as a type-level fact.

### 11.5 What not to prove

- Not the Python compiler. Not SPARQL's semantics in full. Not Unicode. Not the store.
- Not the `dal:` resolution of *literal-valued* dimensions beyond type-correctness; their content is checked by the validation BDD, which is the better tool.
- Not the templates' text. Their link to the proofs is the typed IR and the differential tests (§13.4, §16).

---

## 12. Static and value-level checks (SMT, automata)

Small, local, fully automatic, run per compile. Each corresponds to a stated policy or a recorded defect.

| # | Target | Check | Tool |
|---|---|---|---|
| C1 | **IRI templates** (`dal:graphIriTemplate`, `dal:mintedIriTemplate`, `dal:claimIriTemplate`, revision and event templates) | injective over the declared key/position domain; no separator ambiguity; the inverse parser recovers the parameters; percent-encoding correct; the template's own prefix cannot collide with another role's | Z3 strings / automata |
| C2 | **Graph-prefix and IRI-prefix sets** | antichain (or declared longest-prefix rule); no two scopes with different resolved values can match one IRI; the fallback's complement is non-empty when claimed | automata (prefix languages are trivially regular) |
| C3 | **Width adequacy** | `epochWidth`/`sequenceWidth` ≥ digits needed for the declared datatype's maximum (`xsd:long` ⟹ 19); all identity-bearing strings in one profile use one width per field | LIA + a registry check |
| C4 | **Shard arithmetic** | `hash mod n` is the same function in the compiler, the templates and every minting library; `n` consistent with `priorMetaShards` during migration; `n ≥ 1`; declared `n` versus honoured `n` (the gap in finding #9) | LIA + test vectors |
| C5 | **Lag budget** | `lagWindowMillis ≥ T_tx + skew + replicaLag + margin`, with each term a declared input rather than a guess | LIA; refuse if any term is undeclared |
| C6 | **HLC field widths** | 13-digit millis and 4-digit logical cannot overflow without the borrow; the borrow preserves monotonicity and the `sh:pattern`; the formatted string's lexicographic order agrees with `(l, c, node)` | LIA + automata on the pattern |
| C7 | **`sh:pattern` regexes** in the shapes (`pat:hlc`, the digest hex pattern, claim IRI templates) | the pattern accepts exactly the generated language; anchoring is explicit (XPath patterns are anchored, POSIX are not — a mismatch here is a silently permissive constraint) | automata; Z3 regex as a second opinion |
| C8 | **Base32/hex alphabets and digest widths** | declared width = emitted width; alphabet single-case (so no two key nodes fold together, which the README's §14.1 argument depends on); no padding where unpadded is declared | enumeration |
| C9 | **ETag grammar** | a declared regular language per representation mode; printer ⊆ grammar; parser ∘ printer = id; strong-validator requirement (never `W/`) | automata |
| C10 | **Property-path closure** | the generated path's language = the compile-time closure walk, to the declared depth, including the cycle policy | automata over the shape graph |
| C11 | **Template variable discipline** | every INSERT-template variable bound in every solution (S-3); no blank nodes in templates (S-4); no path in a template (S-11); guard variables disjoint from caller guard variables (§8.5) | static analysis on the IR |
| C12 | **Datatype pinning** | every position literal `xsd:long`; arithmetic re-typed; no `FILTER`-value comparison on a term-matched position (§8.2) | typed IR |
| C13 | **Reserved-word and syntax hygiene** | generated IRIs and local names are valid; no SPARQL keyword collisions in variable names; no `PREFIX` shadowing | static |
| C14 | **Request-size bound** | worst-case rendered size for the largest declared payload and closure ≤ `maxRequestBytes` | LIA with declared bounds |

**Judgement.** C1, C2, C3 and C11 are the four I would do first: C2 and C11 catch live findings (§6.2, §8.1), C1 is the foundation of every identity law, and C3 is a one-line check that prevents the two-widths defect recurring.

---

## 13. Generating the compiler from a specification

The question was whether this has value. My answer: **generate the rules, the registry, the IR and the emitter; do not generate the resolver.** The reasoning follows, then the concrete proposal.

### 13.1 Where generation pays, and where it does not

| Component | Size | Generate? | Why |
|---|---|---|---|
| **Dimension registry** (dimensions, values, baselines, owning class, parameter ownership, strength order) | small, tabular | **yes, emphatically** | it is already a table in the README, duplicated in the ontology, in the compiler, in the shapes, and in the guide's YAML. Five copies of one table is four drift sources. One generated source eliminates them and makes §7's exhaustive checks possible at all |
| **Cross-axis rules** (refusals, warnings, acknowledgements, dead-parameter rules) | ~40 rules | **yes** | finding #3 is exactly this duplication. Generate the SHACL shapes, the compiler predicate, the Isabelle definitions, the BDD input and the README tables from one source. The asymmetry the README notes ("node-local shapes cannot see cross-node combinations") then becomes a *derived, enumerated* fact: the generator can label each rule as shape-checkable or compiler-only and emit the list |
| **Operation-selection table** | ~8 rules | **yes** | tiny, and V6's totality/disjointness check is trivial on generated data |
| **Template library** | ~15 templates | **as an IR, yes** | §13.4 |
| **Emitter / renderer** | small | **yes, from the IR** | L7's properties are structural; a generated renderer over a typed IR satisfies most of them by construction |
| **Resolver** | small, pure | **no** | it is a hundred lines of a pure function over a finite lattice. Proving it (§11.1) is cheaper than generating it, and a hand-written resolver plus an independently generated checker gives translation validation (two implementations is a *feature* here, provided one is derived from the spec and they are diffed) |
| **Capability requirement computation** | small | **partly** | the mapping from resolved dimensions to required flags is a table; generate it. The comparison against the spec is three lines |
| **Minting recipes** | small | **yes** | they are already declared as "canonical JSON with a digest, holding everything a minter needs, missing members refused by name" — i.e. already a generated artefact from a schema. Make the schema the source and generate the recipe builder, the validator, the test vectors and the libraries' parsers |
| **Audits** | ~10 queries | **yes, from invariants** | §13.5 |

### 13.2 The specification artefact

A single machine-readable specification, from which everything downstream is generated. Shape, not syntax (TOML/YAML/Turtle all work; Turtle has the advantage of being the same technology as the rest, and of being validatable by SHACL):

```
dimension concurrency
  declared-on   dal:ConcurrencyProfile
  property      dal:concurrencyProfile
  values        ProvidedConcurrency, Optimistic, AppendOnly, LockingConcurrency
  baseline      ProvidedConcurrency
  strength      ProvidedConcurrency < LockingConcurrency < Optimistic ; AppendOnly incomparable
  guarantees    Optimistic → L9(CAS) requires {atomicUpdateRequest, (singleWriter | detectsWriteWriteConflict)}
                AppendOnly → L9(append) requires {atomicUpdateRequest, (singleWriter | detectsWriteWriteConflict)}
                ProvidedConcurrency → forfeits L8-outcome, L9
                LockingConcurrency → forfeits nothing in-store; obligation EXT-MUTEX, EXT-FENCE

parameter metaShards
  declared-on   dal:MetaTopologyProfile
  belongs-to    metaTopology ∈ {SharedSharded}
  type          xsd:long, ≥ 1
  honoured      false                              ← the declaration/implementation gap, as data
  warning       ShardingNotHonoured

rule compositeboundary-receiptonly
  refuse when   boundary = CompositePropertyBoundary ∧ receiptModel = ReceiptOnly
  because       "a receipt could not say what changed inside the closure"
  shape-checkable  false        ← cross-node
  witness       examples/invalid-compositeboundary-receiptonly.ttl

rule rowlevelguard
  warn when     epochGuardScope = RowLevelGuardOnly
  forfeits      L14
  witness-trace models/F.tla#StaleClientMatchesUnrebasedRow
  acknowledge   dal:epochGuardAcknowledged          ← proposed (PV-D5)

operation-set
  when          concurrency = Optimistic ∧ boundary = NamedGraphBoundary ∧ firstWrite = AbsentRow
  emit          create-if-absent, cas-replace, tombstone-delete
```

Generated from this, in one build step:

1. `spec/persistence.ttl` skeleton (classes, properties, individuals, `rdfs:comment` from `because`) — or at minimum, a check that the hand-written ontology agrees with the registry;
2. `shapes/constraints.ttl` for every shape-checkable rule;
3. the compiler's validation predicate and selection table;
4. the Isabelle definitions for §11.1 and the strength orders;
5. the BDD/SMT input for §7.3's exhaustive checks;
6. the TLA+ constants and `.cfg` files per capability profile (§10.1);
7. the README tables (§5, §7, §9, §12) — so documentation drift becomes impossible;
8. the guide's §29.3 YAML ↔ `dal:` mapping table, which currently exists by hand and already carries a list of unmapped keys;
9. the capability-requirement table and the `min_level` comparison;
10. the obligation set per operation (PV-D2);
11. the witness-coverage report (§7.4): every rule with no fixture fails the build;
12. the laws-held list per compiled target (PV-D5).

**Value, stated plainly.** The generation is worth it not because it saves code — the compiler is small — but because **it makes the specification the artefact that is reviewed, verified and cited**, and because several of the checks in this document are impossible without a machine-readable rule set. §7's exhaustive validation needs the rules as data. §4's matrix needs the guarantees as data. §5's obligations need them as data. §7.4's witness coverage needs them as data. The generation is the enabling move for everything else.

**Cost.** My estimate: the registry and generator are ~1.5–2k lines, and they *replace* roughly comparable hand-written content across the ontology, the shapes, the compiler's validation module and the README. Net addition is small; the leverage is large.

**What I would not claim.** Generating the compiler does not make it correct, and a generator is itself unverified code. The mitigation is that the generator's output is *checked* — the shapes against the predicate (V2/V3), the predicate against the BDD (V1), the tables against the README (string diff), the fixtures against the rules (witness coverage). A generator whose outputs are cross-checked against each other is far safer than four hand-written copies that are not.

### 13.3 One state/term model, many back ends

The same generation argument applies to the state space (§3.2) and the vocabulary (Appendix A). Generate from one declaration:

- the Alloy signatures and fields;
- the TLA+ variables and type invariant;
- the Isabelle record types;
- the SHACL shapes of Appendix B;
- the `pat:` (or Foundation-aligned) vocabulary itself, with cardinalities;
- the fixture generators for §9.3's differential tests;
- the audit queries' schema assumptions.

This matters because every model in §10 and every check in §9 reads the same state, and three hand-written encodings of one state space will disagree — which would silently invalidate the cross-model properties of §10.3.

### 13.4 The typed IR and the emitter

This is the SQL review's "typed `decision3` IR" recommendation, transposed, and it is the highest-leverage code change in this document.

Give the compiler an intermediate representation of a generated operation:

```
Operation
  name, template-id, target-kind
  reads      : set of (graph-role, pattern)        -- the declared read set (feeds §10's models)
  writes     : set of (graph-role, pattern)
  guards     : list of Guard                        -- each tagged Term | Value
  params     : list of (name, Type)                 -- Type ∈ {IRI, Long, String, LangString, Payload, Position, Digest, ...}
  templates  : Insert/Delete quad patterns, each variable tagged Bound | OptionalAllowed
  obligations: caller | housekeeping | store
  laws       : the laws this operation participates in establishing
```

Then the emitter is a renderer from IR to SPARQL text, and the following become **impossible by construction** rather than tested:

| Hazard | How the IR removes it |
|---|---|
| injection (QP1) | parameters are typed terms; there is no path from a string to query structure |
| untyped position literals (S-7, B14) | `Long` renders as `"n"^^xsd:long`, always |
| a variable in an INSERT template that may be unbound (S-3) | `Bound` vs `OptionalAllowed` is a type; the renderer refuses an untagged variable |
| blank nodes in templates (S-4) | no blank-node constructor in the IR |
| property path in a template (S-11) | paths are a `reads`-only construct |
| unnamed graphs (S-1) | every pattern carries a graph role; there is no default-graph constructor |
| unbound `GRAPH ?g` (S-2) | bucket sets are a `RegistryList` parameter type, not a variable |
| term/value comparison confusion (§8.2) | `Guard` is tagged; the renderer refuses a `Value` guard on a term-invariant position |
| caller guard variable collision (§8.5) | guard variables come from a reserved namespace by type |
| `NOW()` in a guard (S-6) | no clock constructor except in an `AuditOnly` position |
| unpadded positions in IRIs (S-12, B13) | `Position` renders through the declared width |
| a missing parameter (E5) | the IR's `params` is the renderer's domain; completeness is a type check |

Plus: the IR is the natural input to the Alloy and TLA+ generators (the `reads`/`writes` sets *are* the model's read and write sets), to the obligation emitter (PV-D2), to the request-size bound (C14), and to the mutation operators (§16.2). **A typed IR is a formal method costing a few hundred lines, and it removes whole classes of defect rather than testing for them** — the SQL review's phrasing, and it is equally true here.

### 13.5 Generate the audits from the invariants

Invert the current direction. Today the invariants are prose and the audits are hand-written queries, and three of them have been wrong. Instead:

```
invariant head-retained
  states      ∀ r ∈ VersionRow. r.head ≠ ⊥ ⟹ ∃ receipt with that IRI in a registry-listed bucket or pinned
  detector    generated SELECT over meta ⋈ registry-listed logs ⋈ pinned
  obligation  retention job (pinned-head copy)
  alloy       assert HeadRetained
  gating      S2 onwards
```

Then: the audit query is generated from the invariant; the Alloy assertion is generated from the same invariant; the detection-completeness obligation (§9.2) is checked between them; and the §9.2 coverage gaps become *visible as invariants with no detector* rather than invisible as audits nobody wrote. This closes finding #8 structurally.

---

## 14. The capability record, the TCK, and evidence

### 14.1 Capabilities as discharged assumptions

Restructure the relationship so the words match the logic:

```
TCK run (image, config, topology) ──► report (digest, per-test verdicts)
                                        │
                                        ▼
                              capability record C      ← derived, not declared
                                        │
          matrix(strategy, C) ◄─────────┘        ← generated by model checking (§4.2, §10.2)
                                        │
                                        ▼
       planner: Guarantee(selected(family), C) ≥ min_level(family) ?  → accept / refuse with reason
```

Two properties worth checking of this pipeline:

- **Every flag in *C* is set by at least one TCK test**, and every gating TCK test discharges at least one assumption used by some matrix cell. Unused tests and undischarged assumptions are both reportable.
- **A capability record is only as fresh as its report.** Bind the spec to the report digest and the image/config/topology identity; refuse or warn on a stale or absent binding. This is the freshness-checker discipline the SQL review describes, applied to capability claims.

### 14.2 The honest reading of a TCK pass

The guide already says it well: "Tests can falsify a guarantee, never prove one." Keep that, and add the symmetric statement for models: **a bounded model check can falsify a design, and can establish a guarantee only up to its scope and its assumptions.** Record both scopes — the TCK's workload/fault scope, and the model's bound and capability assumptions — in the claim. A claim that says "no violation observed under workload W on image I" plus "no violation exists at scope ≤ 3 writers under assumption set A" is a much stronger and much more honest artefact than either alone, and the two have genuinely complementary blind spots: the model misses fidelity errors, the test misses rare interleavings.

### 14.3 Closing the loop

| Direction | Mechanism | What it establishes |
|---|---|---|
| model → TCK | every counterexample becomes a reproduction test | model fidelity; store classification |
| TCK → model | any anomaly the model rules out but the store exhibits means the model's assumptions are wrong | model correction, and a corrected capability flag |
| TCK → matrix | the report populates *C*, which selects the matrix column | the planner's refusal becomes evidence-based |
| matrix → TCK | the assumptions used become the gating set | measurable coverage for a suite that currently has none |
| invariants → audits → production | §13.5 generation plus monitors | L11 in production, not only in CI |

---

## 15. Housekeeping, runtime monitoring and the operational surface

The compiler deliberately does not generate retention, epoch bumps or erasure (ADR-A80). That is a sound boundary, and it means those procedures have *no* machine-checked artefact today. Two consequences and two remedies.

**Consequence 1.** The safety of the generated SPARQL depends on housekeeping obligations (claim TTL, prefix-only pruning with mark-first and pinned heads, registry rotation, epoch allocation and quiesce, erasure register replay). If housekeeping is a runbook, the obligation is discharged by a human, every time, under time pressure, during an incident.

**Consequence 2.** Nothing proves housekeeping *ran*. A pinned-head copy that was skipped is invisible until a dormant stream's next CAS fails with a dangling `prevRev`, long after the bucket is gone.

**Remedy 1 — model the procedures** (models F, G, J, K, M, N). These are short models and they produce runbooks as a by-product: a model-checked procedure *is* a runbook with its preconditions and step ordering justified. The retention job's "advance the mark, in its own transaction, and only then drop" ordering is exactly the kind of step whose justification is a crash-safety argument, and the argument is two lines in TLA+ and a paragraph of prose that has already been wrong once.

**Remedy 2 — runtime monitors derived from the same invariants** (T7, §13.5):

| Monitor | Checks | Cadence |
|---|---|---|
| **Invariant suite** | every invariant from §9.2, including the nine gaps | continuous; alert on non-zero |
| **Housekeeping evidence** | the retention job advanced marks before dropping; pinned heads were copied; the registry lists exactly the extant buckets; claim TTL ≥ the current redelivery horizon (which is a *live* quantity: it changes when a dead-letter policy changes) | per run, and continuously |
| **Capability drift** | the store's version/config/topology still matches the TCK report the deployment was accepted against | on deploy and on a schedule |
| **Declaration drift** | the generated `.rq` in production matches the compiled profile, which matches the configuration graph (the README's determinism guarantee makes this a byte comparison) | on deploy |
| **Erasure audit** | after each erasure, probe every store in model K's enumerated list for the subject's identifiers and pseudonyms, including the external allocator table and the outbox | per erasure, and after the retention bound |
| **Position-reuse audit** | no `(target, epoch, seq)` has two distinct receipt bodies; no revision IRI has two creation events | continuous |
| **Fork/duplicate/gap** | the four existing audits plus the nine gap-filling ones | continuous |
| **Late-arrival audit** | rescan a trailing window and compare with delivered (the guide's own control for the lag budget) | scheduled |
| **Vacuity watch** | each audit reports *applicable / clean / violated*, never conflating "not applicable" with "clean" (§7.4) | continuous |

**Judgement.** The monitors are cheap because they are generated from the same invariants as the proofs and the models, and they are the only control that survives the threat the design explicitly names: writers that bypass every guard. I would weight this above several of the proofs.

---

## 16. Testing that complements the formal work

Formal methods do not replace the TCK or live testing; they aim it. Four additions.

### 16.1 Differential and metamorphic testing of the compiler (T0/T1)

| Law | Generator | Oracle | Note |
|---|---|---|---|
| L1 determinism | a configuration graph, permuted triple order, permuted file order, relabelled blank nodes, two machines | byte-identical compiled profile and `.rq` (modulo the README's known blank-node caveat — which should be fixed, since an unstable artefact cannot be diffed) | the README already promises this; test it |
| L1/L2 locality | add an unrelated class, profile, target | unchanged outputs for other targets | metamorphic |
| L4 validation | **exhaustive** over the dimension product (BDD-guided enumeration of boundary cases) | the generated predicate, the SHACL shapes, and the compiler, three ways | §7 |
| L5 selection | same | generated table | §7 V6 |
| L7 instantiation | adversarial parameter corpus (the injection suite) | parse-tree-shape comparison, not exception-freedom | §8.3 E2 |
| L12 identity | the anchor vectors and coverage fixtures already in `examples/` | the minting libraries *and* an independent reimplementation from the specification | the README already does conformance by test vectors, which is the right design; add an independent implementation so the vectors test the *specification*, not the reference |
| Rotation/migration squares (L15) | a claim-scheme rotation, a shard-count change | both paths of the commuting square | needs the data-migration leg to be defined, which it currently is not for shard changes |

### 16.2 Mutation testing, over the IR and the rules

Every mutation must fail a named check. This is the measure of whether the suite is worth anything.

Over the **IR**: drop the epoch guard; drop the seq guard; drop the tombstone guard; drop the txn `NOT EXISTS`; drop the digest from the claim; drop `pat:head`; drop `prevRev`; make a `Bound` variable `OptionalAllowed`; change a `Long` to a plain literal; unpad a position; swap `NOT EXISTS` for `MINUS`; move a filter from the guard to the template; replace the in-transaction counter with a pre-read; make the fence check not advance; widen a graph role to the default graph; reorder the mark-advance and the bucket drop; omit the pinned-head copy; remove the upper bound from the global read; shorten the claim TTL below the retry horizon.

Over the **rules**: delete each refusal; weaken each warning; change a baseline; remove an acknowledgement requirement.

Over the **compiler**: seed a bug in the resolver's precedence, in the tie-break, in the reasoning-drop, in the parameter binding. **Seed in the implementation, not only in the reference** — the SQL review's §3.1 finding, and it applies here identically.

Each mutation is labelled with the check that must catch it, and the labelling is generated from the specification (§13.2), so an uncaught mutation is a reportable coverage gap rather than a lucky escape.

### 16.3 Property-based testing of the client state machine

The caller obligations (§5) are a state machine: read → decide → write → classify → retry/resend/abandon. Property-test it against a model store under injected failures, with properties: never replays blindly on `PreconditionFailed`; always resends identically on `Unknown`; never reports success on `IdempotencyKeyReuse`; always confirms on the primary; calls `clock.receive` before a read-dependent write; respects the retry bound; surfaces `ConflictExhausted` with history. Each property corresponds to a recorded defect or a stated rule.

### 16.4 Fixture coverage as a gate

The `examples/` directory is already strong — one negative fixture per refused combination, warning fixtures, identity anchor vectors, generated SPARQL per example with `diff -r` reviewability. Three additions:

- **witness coverage** (§7.4): every rule, shape, warning and audit has a fixture that triggers it, enforced by the build;
- **store-state fixtures**, not only configuration fixtures: the generated `.rq` is currently reviewed as text, never executed against a state. Add a small in-memory store (or Oxigraph), a library of store states, and assertions on the post-state of every generated operation. This turns the elegant `execution/` + `diff -r` discipline from a *syntactic* review into a *semantic* one, at low cost;
- **stable compiled profiles**: fix the blank-node labelling so compiled profiles can be committed and diffed like the SPARQL.

---

## 17. Cost, sequencing, and what not to do

### 17.1 Cost

Rough sizes, in the SQL review's units (lines; token figures omitted since I do not have the model's parameters).

| Item | Track | Size | Replaces |
|---|---|---|---|
| Specification registry + generator (§13.2) | A/F | ~2k | hand-written shapes, validation module, README tables, YAML mapping |
| Typed IR + emitter (§13.4) | A | ~1k | hand-written template rendering |
| State/term model generator (§13.3) | A | ~0.5k | three hand encodings |
| Exhaustive validation checks, BDD/SMT (§7.3) | C | ~0.8k | sampled tests |
| Static/value checks, SMT + automata (§12) | C | ~1.2k | — |
| Isabelle: Resolution, Positions, Encoding, Outcomes (§11) | E | ~1.8k | — |
| Alloy: state model, closure disjointness, audit detection (§8.4, §9.2) | C | ~1.2k | — |
| TLA+/Quint: models A–N (§10.2) | G | ~3.5k | — |
| History-checking + Hermitage harness (§14.3) | G | ~1k | some TCK scaffolding |
| Generated audits + monitors (§13.5, §15) | F | ~1k | hand-written audits |
| Witness coverage, mutation operators, client property tests (§16) | B | ~1.2k | some existing tests |
| **Total** | | **~15k** | |

Of which the specification registry, the typed IR, the generated audits and parts of the test harness *replace* existing or planned hand-written content. My judgement on net addition: 8–10k lines, with the highest-value third (registry + IR + exhaustive validation + models A–F + witness coverage) at roughly 5k.

### 17.2 Sequencing

| Stage | Gate: required evidence |
|---|---|
| **0. Immediate (days)** | prefix antichain/overlap check (PV-X1); witness coverage for every existing rule, shape and audit, with the gaps listed; non-vacuity for every SHACL shape; the `sh:declare` lint; S-3 and S-4 static checks on the current templates; stable compiled-profile labels |
| **1. Specification (weeks)** | the registry and generator; shapes and validation predicate generated from it; V1–V10 exhaustive; dead-parameter rules derived; the laws-held and obligation lists emitted per target |
| **2. Typed IR (weeks)** | IR in place; C11/C12 by construction; read/write sets declared per operation; obligations emitted; closure disjointness check; composite boundary either fixed or refused |
| **3. Proofs (weeks, parallel)** | Resolution, Positions, Encoding, Outcomes gated; keyset/gap-scan/as-of/fork lemmas; negative lemmas with witnesses |
| **4. Models A–F (weeks)** | guarded CAS, append, first write, key claim, outcomes, epoch — each checked across the capability profiles that matter to the supported backends; counterexamples reproduced as TCK tests; the matrix's first rows generated |
| **5. Models G–N + grounding** | retention, global read, fencing, infrastructure writers, erasure, multi-aggregate, bulk, shard migration; history checking on at least one MVCC engine (the guide's own §30.4 point 3 — TDB2 alone cannot exercise the hazards) |
| **6. Production** | generated audits deployed as monitors; invariant coverage complete or the gaps declared; housekeeping evidence monitored; capability and declaration drift checks enforced |

Model-checking at least one MVCC engine before trusting the capability model is the guide's own stated condition, and it applies to the models too: a model whose only grounding is a single-writer store has not been grounded.

### 17.3 What not to do

- **Do not mechanise SPARQL's semantics in full.** Use it selectively: the as-of query, the gap scan, the keyset predicate, the composite closure. Elsewhere use differential testing against independent engines.
- **Do not model an engine's implementation.** Model the isolation contract; test the contract.
- **Do not verify the resolver.** Prove its properties; generate an independent checker.
- **Do not let a bounded pass stand as universal.** Record scope and assumptions in every claim.
- **Do not formalise the Unicode pipelines.** Axiomatise, then property-test against ICU, and declare the pinned version as part of the pipeline's identity (the README already does this).
- **Do not build a second TCK.** Extend the one that exists; derive its obligations from the models.
- **Do not generate the whole compiler.** Generate the parts that are tables, and the part whose bugs are injections.

---

## 18. Prioritised recommendations

| # | Action | Addresses | Cost |
|---|---|---|---|
| 1 | **Prefix antichain/overlap check and a declared target-identification function**; refuse configurations where two scopes with different values can match one instance | §6.2, findings #1, #2 | hours–days |
| 2 | **Witness obligation for every rule, shape, warning and audit**, with coverage as a build gate; `sh:declare` lint; non-vacuity checks | §7.4, D.3 A6 class | days |
| 3 | **S-3 and S-4 static checks** (unbound template variables, blank nodes in templates) on the existing templates, now | §8.1 | days |
| 4 | **Enumerate the declaration/implementation gap** as data (shards not honoured, fixed infrastructure IRIs, housekeeping-only dimensions, first-property-only closure) and emit it per target; refuse the composite-boundary case | finding #9, L6 | days |
| 5 | **Specification registry + generator**; generate shapes, validation predicate, selection table, README tables, obligations, laws-held | finding #3, §13 | weeks |
| 6 | **Exhaustive cross-axis validation (BDD/SMT)**, V1–V10, including warning coverage and refusal non-vacuity | §7 | small, once (5) exists |
| 7 | **Typed IR + generated emitter**; read/write sets per operation; guard grammar restriction | §8, §13.4 | weeks |
| 8 | **Extend the capability record to the full `StoreCapabilities`**, three-valued, bound to a TCK report digest; make `unknown` pessimistic | finding #4, §4.1 | small |
| 9 | **TLA+/Quint models A–F**, parametrised by capability; generate the first matrix rows; reproduce counterexamples as TCK tests | §10, L9, L14 | weeks; highest defect yield |
| 10 | **Isabelle: Positions, Encoding, Outcomes, Resolution**, with the negative lemmas | §11 | weeks, parallel |
| 11 | **Detection-coverage completion**: the nine missing invariants, generated audits, Alloy detection obligations, applicability labelling | finding #8, §9.2, §13.5 | small–medium, high value |
| 12 | **Pin the digest and recipe canonicalisations** (an exact profile: literal forms, `xsd:string`, escaping, JSON profile), with an independent reimplementation checked against the vectors | finding #7, L12 | small |
| 13 | **Composite closure: disjointness check, two-closure equality, depth/path reconciliation** | §8.4 | small–medium |
| 14 | **Models G–N**, especially J (unguarded infrastructure writers) and K (erasure boundary, including the P6 allocator table) | §10.2, §3.2, L13 | weeks |
| 15 | **Monitors generated from invariants**, plus housekeeping evidence, capability drift and declaration drift | §15, L11 | small–medium |
| 16 | **ETag grammar, widths, and the two-representation parser**, generated and checked | finding #10, C9 | hours |
| 17 | **Store-state fixtures and semantic review of generated SPARQL** (execute, don't only diff); stable compiled-profile labels | §16.4 | small |
| 18 | **Mutation operators over IR, rules and compiler**, each labelled with the check that must catch it | §16.2 | small–medium |

### Decisions for the human

| # | Decision |
|---|---|
| PV-D1 | Full `StoreCapabilities` in `dal:`, three-valued, pessimistic on `unknown`, bound to a TCK report |
| PV-D2 | Caller and housekeeping obligations emitted as data per operation, and in the `.rq` header |
| PV-D3 | Target identification declared as a function: restricted scope kinds, or a refusal for ambiguous instances |
| PV-D4 | `dal:ShapeScope` restricted to a monotone SHACL fragment, or excluded from write-path dimensions |
| PV-D5 | Every warning names the law it forfeits and its witness trace; forfeiting a law requires an explicit acknowledgement property |
| PV-D6 | `GuardPattern` restricted to a typed grammar with a declared read set |
| PV-D7 | Known-unsafe baselines: keep (`dal:RowLevelGuardOnly`, `dal:AbsentRow`, `dal:ProvidedConcurrency`) for compatibility, or flip to safe-by-default with a declared opt-out |
| PV-D8 | The specification registry is the single source of truth for dimensions, rules, selection, guarantees and obligations; the ontology, shapes, compiler and README are generated or checked against it |
| PV-Q1 | Should a capability *increase* that weakens a resolved guarantee be a warning? (I think yes) |
| PV-Q2 | Is `Ambiguity` raised for two tied candidates with the *same* value? (If so, it should not be; if not, literal value equality needs a definition) |

---

## 19. Bottom line

The Persistence layer is unusually well suited to formal methods because its specification is already largely explicit, tabular and finite, and because its recorded defect history is dominated by exactly the classes that bounded model checking, decision-table exhaustion and witness obligations catch cheaply. Three remediation passes found eleven of twelve calibration defects by human review; a model checker finds that class in an afternoon.

The highest-value work, in order:

1. **Make the rules data** (§13.2). It is the enabling move: exhaustive validation, the guarantee matrix, the obligation set, witness coverage and documentation consistency all depend on it, and it eliminates the two-implementation drift that finding #3 names.
2. **Make the operations typed** (§13.4). A typed IR removes, by construction, at least eleven defect classes that are currently guarded by prose and review.
3. **Model the protocols, parametrised by capability** (§10, §4.2). This is where the defects are, where tests are weakest, and where the hand-written store table has already been wrong. The output is a generated matrix that makes the planner's refusals evidence-based and the TCK's coverage measurable.
4. **Close the detection gap** (§9.2, §13.5). The audits are the only control against the threat the design explicitly names — writers that bypass every guard — and their coverage has never been enumerated. Nine invariants currently have no detector.
5. **Prove the small, sharp things** (§11): injectivity of the tuple encoding, order agreement of padded positions, totality and soundness of the outcome classification, determinism and locality of resolution, and the negative lemmas that keep each fix from being reverted.

On generating the compiler: generate the registry, the rules, the IR, the emitter, the audits and the documentation; prove the resolver rather than generating it, and keep an independently generated checker so that every compiled profile is validated against its own inputs. The value is not saved code — the compiler is small — but a specification that is the reviewed artefact, and a verification story in which nothing is claimed twice in two places.

Finally, the parametric framing is the thing I would hold onto above any individual technique. The honest claim this layer can make is not "the generated SPARQL is correct" but **"for this capability profile, these operations deliver these guarantees, under these assumptions, discharged by these tests, with these obligations on the caller and these on housekeeping."** Every element of that sentence can be made machine-checked data. Once it is, pluggable backends stop being a verification obstacle and become the parameter the verification is indexed by.
