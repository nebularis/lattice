# RDF/SPARQL Implementation Patterns — Phase Plan

**Unit type:** Plan  
**Identifier:** `rdf-sparql-patterns-phase`  
**Status:** Ready for execution  
**Blocks:** Epic decomposition; Phase 0.2 implementation; A74/A75 ratification  
**Estimated scope:** 1–2 agent-days across 3 slices  

**Purpose:** Formalize RDF/SPARQL data patterns and query discipline from sketch into a documented, validated set of design patterns, proposed ADRs, and policy rules. Provide concrete examples, store-specific adapters, and lint/test infrastructure so Phase 0 implementation can proceed with clear patterns and enforcement.

**Entry criteria:**
- Sketch approved: [rdf-sparql-implementation-patterns.md](../sketches/rdf-sparql-implementation-patterns.md)
- Notes reviewed: uniqueness, ordering, concurrency, combined patterns in `docs/developer/notes/`
- Architecture Review counter-arguments incorporated (configurable, not mandated)

**Success criteria:**
- 8 proposed ADRs documented with rationale and impact
- 15 design sub-patterns with concrete SPARQL examples
- Store-specific adapter guide for Jena TDB2 (+ roadmap for GraphDB)
- Lint rules and CI gates specified (code + enforcement spec)
- Test suite templates per pattern (ready for Phase 0 implementation)
- Status recorded in `docs/developer/status/rdf-sparql-patterns-status.md`

---

## Part 0 — Dependencies and ordering

### Hard ordering

No external blockers. This plan is independent and prerequisite to all Phase 0 slices.

### Information dependency

Requires review and sign-off on:
1. Counter-arguments in Architecture Review.md (bi-temporal, deletion, configurability) ✅ (captured in sketch)
2. Notes correctness (are the patterns actually portable?) — will be validated in Slice 1

---

## Part 1 — Slice breakdown

### Slice 1: Core patterns and design specs (0.5 days)

**Objective:** Document each of the 5 core patterns (K, O, C, T, Q) as a 2–4 page design spec with concrete SPARQL examples, runnable on Jena TDB2.

**Deliverables:**

1. **Pattern K (Uniqueness)** → `docs/architecture/design-patterns/uniqueness-in-rdf.md`
   - P0: Deterministic IRIs — when to use, canonicalization input, version safety
   - P1: Key-claim registry — registry structure, claim lifecycle, retirement
   - P2: Guarded insert — `INSERT … WHERE NOT EXISTS …` with full example
   - P3: Materialize write conflict — sharded counter bootstrap, contention tuning
   - P5: SHACL validation — `sh:maxCount 1`, when incremental works, fallback to P7
   - P6: External allocator — Postgres adapter pattern, fallback to in-graph
   - P7: Detect-and-reconcile — nightly job structure, quarantine pattern
   - Runnable examples: 3 test cases (P1 create, P1 race, P3 under contention)

2. **Pattern O (Ordering)** → `docs/architecture/design-patterns/ordering-in-rdf.md`
   - O1: Per-stream dense sequencing — counter structure, epoch safety, zero-padding
   - O2: Valid-time capture (optional) — when to use, how to backfill
   - O3: Logical causality — version pointers, `supersededBy` chains
   - O4: Dataset-wide order (derived, sparse) — change feed alternatives, HLC
   - O5: Bitemporal query patterns — as-of-valid-time, as-of-transaction-time examples
   - Runnable examples: 2 test cases (dense seq under writers, as-of query)

3. **Pattern C (Concurrency)** → `docs/architecture/design-patterns/concurrency-in-rdf.md`
   - C1: Guarded update — isolation semantics, why one-request atomicity matters
   - C2: Receipt-log outcome — why re-read fails, `ASK` for idempotent check
   - C3: Derived ETags — ETag generation, HTTP If-Match mapping, consistency proof
   - C4: Immutable receipt chain — fork detection query, corruption detection
   - Escape hatches C5–C6: Kafka queue, external lock
   - Runnable examples: 2 test cases (successful CAS, failed CAS with outcome verification)

4. **Pattern T (Temporal + Concurrency)** → `docs/architecture/design-patterns/temporal-concurrency-combined.md`
   - Metadata graphs per aggregate — structure, what lives where
   - Version counters + dense seq — the critical pairing
   - Whole-graph replace safety — why T1–T5 combined is safe
   - Epoch + backup safety — generating new epochs, consumer watermark invalidation
   - Runnable examples: 1 full end-to-end test (write, verify receipt, replace, verify ordering survives)

5. **Query patterns** → `docs/architecture/design-patterns/sparql-query-discipline.md`
   - QP1: Prepared query + params — injection examples, why string concat fails
   - QP2: Time-agnostic guards — why `now()` breaks determinism, input-based alternatives
   - QP3: Cursor for results — memory bounds, streaming semantics
   - QP4: Permutation determinism test — L2 test structure per pattern
   - QP5: Store isolation verification — test suite for write-skew detection
   - Runnable examples: 2 test cases (injection probe, determinism check)

**Validation pack:**
- Test level: L1 (unit) + L3 (contract validation) 
- Command: `mise patterns:validate-sparql` (compiles examples, runs tests against Jena TDB2)
- Expected artifacts: SPARQL query log, test results JSON
- Deliberate non-coverage: Store-specific optimizations (next slice); LLM integration (Phase 2); full benchmark (Phase 0.5/L7)

**Traceability:**
- Links to proposed ADRs: A-Unique, A-Order, A-CAS, A-Temporal, A-Query
- Links to components: Store SPI (C-02), Uniqueness service (TBD), MORK records, ingestion

---

### Slice 2: Store-specific adapters and policy (0.4 days)

**Objective:** Document how each pattern adapts to Jena TDB2 (reference), with roadmap for GraphDB and Neptune. Specify lint rules and CI gates.

**Deliverables:**

1. **Store adapter guide** → `docs/architecture/design-patterns/store-adapters.md`
   - **Jena TDB2** (reference implementation):
     - K patterns: P0–P2 native; P3 works (MVCC with per-statement conflict detection); P5 works (no incremental SHACL); P6 via outbox to Postgres; P7 works
     - O patterns: O1–O3 native; O4 via change feed (delta or polling); O5 requires separate query path
     - C patterns: C1–C4 work (atomic request, verifiable chain); write-skew possible under snapshot isolation (test!)
     - T patterns: T1–T5 fully supported
   - **GraphDB** (stretch target):
     - Write-skew isolation at serializable? Needs validation.
     - SHACL incremental? Yes (reuses cached results). But at what cost?
     - Repository replication? Yes, but how does it affect sequence allocation?
   - **Neptune** (future):
     - Streams alternative to log? How to integrate with O1 dense seq?
     - Multi-region? Global counter becomes impossible; per-region seq only.

2. **Policy enforcement** → `docs/architecture/design-patterns/policy-enforcement.md`
   - **Python lint rules:**
     - Ban `import datetime; datetime.datetime.now()` in `tools/mork/src/mtp/`, `tools/mork_compilers/`
     - Ban `uuid.uuid4()` in guard/determinism-critical modules
     - Ban string formatting into SPARQL (`f"SELECT … WHERE { <{iri}> ?p ?o }"`)
     - Enforcement: `mise lint:python-patterns` pre-commit hook + CI gate
   - **Java ArchUnit rules:**
     - No component reads/writes RDF except via `ScopedDataset` interface
     - `ScopedDataset` methods must accept `CommitMetadata` parameter
     - Ban `this.now()` in guard/canonicalization modules
     - Enforcement: `mise lint:archunit-spi` in CI
   - **CI gates:**
     - Determinism L2 tests: every function claiming determinism must pass permutation + repeat
     - Injection corpus: L8 suite includes SPARQL injection probes (see QP1 examples)
     - Store isolation: before shipping a new adapter, verify write-skew handling with pattern C test suite

3. **Test infrastructure** → `tools/patterns/rdf-sparql-tests/`
   - Template structure: `test_{pattern}_{sub_pattern}.py` (Python) + `Test{Pattern}.java` (Java)
   - Example: `test_uniqueness_keyregistryrace.py` — concurrent inserts of same key, verify only one lands
   - Fixture data: small Turtle files per pattern (10 triples each, ready to load)
   - Comparison matrix: expected results for TDB2, placeholder rows for GraphDB/Neptune

**Validation pack:**
- Test level: L1 (lint) + L3 (contract) + L8 (store isolation)
- Command: `mise patterns:validate-enforced` (runs lint, archunit, store isolation tests against TDB2)
- Expected artifacts: Lint report, ArchUnit violations report, store isolation test results (JSON matrix)
- Deliberate non-coverage: Performance tuning (L7, Phase 0.5); multi-region deployment (Phase 4); LLM usage of patterns (Phase 2)

---

### Slice 3: Proposed ADRs and decision record (1 day)

**Objective:** Formalize the 8 proposed ADRs with full rationale, alternatives considered, and implementation implications. Record status and next steps.

**Deliverables:**

1. **ADR-A74 (Graph-primary)** → `docs/architecture/decisions/ADR-A74-graph-primary-system-of-record.md`
   - **Decision:** RDF is authoritative for all semantic state; PostgreSQL and RabbitMQ are coordination stores only
   - **Rationale:** 
     - Enables audit via immutable graph history
     - Single source of truth for identity, provenance, governance
     - Patterns K/O/C/T are designed around this model
   - **Implications:**
     - Phase 0.2 must implement T (metadata graphs + version counters) first
     - Phase 0.3 must implement K (uniqueness in RDF, not Postgres UNIQUE)
     - Phase 0.4 must implement O (dense ordering in RDF)
     - All writes must go through a `CommitMetadata` wrapper (A-CAS pattern C2)
     - Postgres becomes read-only for most queries (except operational indices)
   - **Alternatives considered:**
     - Dual-write (RDF + Postgres authoritative) — rejected, creates sync loss risk
     - RDF advisory, Postgres primary — rejected, contradicts "graph-primary"
   - **Risks:**
     - Performance if dense seq contends (mitigated: per-stream sharding)
     - Backup/restore requires epoch regeneration (mitigated: epoch versioning in ETag)
   - **Validation:** Slice 1 patterns + Slice 2 store adapters prove feasibility

2. **ADR-A75 (Store SPI)** → `docs/architecture/decisions/ADR-A75-three-tier-store-spi.md`
   - **Decision:** Define three tiers of store contracts (Core, Query, Distribution)
   - **Rationale:**
     - Multiple stores must be pluggable (cost, ops, compliance reasons)
     - Not all stores have SHACL, FTS, temporal indices, replication — don't mandate
   - **Core SPI (mandatory):**
     - SPARQL 1.1 query + update; named graphs; atomic one-request; isolation level documented
   - **Query SPI (optional):**
     - SHACL validation; FTS; geospatial; temporal; graph compression
   - **Distribution SPI (optional):**
     - Replication/HA; sharding; multi-region; write rebalancing
   - **Reference implementation:** Jena TDB2 (Core ✅, Query ⚠️, Distribution ❌)
   - **Validation:** Slice 2 store adapter guide proves portability across Jena/GraphDB

3. **ADR-A-Unique (Uniqueness enforcement)** → `docs/architecture/decisions/ADR-A-unique-enforcement-in-rdf.md`
   - **Decision:** Use key-claim registry (P1) + guarded update (P2) for natural/surrogate keys
   - **Rationale:** Portable, scales to millions, works on all stores, audit-friendly
   - **Sub-decisions:**
     - P0 (deterministic IRIs) for immutable keys only; bans PII in IRIs
     - P3 (sharded counter) for write-contention; shard count per workload (default 1024)
     - P6 (external allocator) for ID minting microservice only (not for domain keys)
     - P7 (detect-and-reconcile) nightly job as safety net
   - **Validation:** Slice 1 pattern K test cases

4. **ADR-A-Order** → `docs/architecture/decisions/ADR-A-order-dense-per-stream.md`
   - **Decision:** Dense per-stream seq in metadata graph; transaction time immutable; valid/logical time optional
   - **Rationale:** Cheap, shardable, gap-free; application decides temporal semantics
   - **Implications:**
     - Every write requires `ex:epoch` + `ex:seq` in metadata graph (T1–T2)
     - Every aggregate is one stream (aggregate IRI = stream key)
     - Dataset-wide order is derived (not dense, not canonical)
     - Epoch must be bumped on restore (safety against ETag collisions)
   - **Validation:** Slice 1 pattern O + Slice 2 policy enforcement

5. **ADR-A-CAS** → `docs/architecture/decisions/ADR-A-cas-guarded-sparql-update.md`
   - **Decision:** CAS primitive is `DELETE/INSERT … WHERE` with receipt log outcome verification
   - **Rationale:** Portable (works on all SPARQL 1.1 stores), safe (guarded + receipt), idempotent (receipt check)
   - **Implications:**
     - No `INSERT … WHERE NOT EXISTS` without full guard specification
     - Every state mutation must produce an immutable receipt (C2, C4)
     - ETag derived, not stored (C3)
     - Store isolation must be empirically verified (C5 escape hatches when CAS fails under write-skew)
   - **Validation:** Slice 1 pattern C + Slice 2 store isolation tests

6. **ADR-A-Temporal** → `docs/architecture/decisions/ADR-A-temporal-bi-temporal-configurable.md`
   - **Decision:** Transaction time (`recordedAt` + seq) required; valid time + in-place update configurable per graph/tenant
   - **Rationale:** 
     - Mandate transaction time for audit, not valid time (business logic depends on domain)
     - Immutability mandate causes data explosion (versions of every triple)
     - Application chooses whether to supersede vs. update in place
   - **Implications:**
     - MORK decision records always immutable + versioned (audit requirement)
     - Projection-source data can have deletion/update policy (config option)
     - `fnd:TemporallyScoped` is a mixin for domain use, not platform mandate
     - As-of queries are application responsibility (optional analytic path, separate from hot path)
   - **Validation:** Slice 1 pattern O (O5 example)

7. **ADR-A-Delete** → `docs/architecture/decisions/ADR-A-delete-audit-and-policy.md`
   - **Decision:** Deletes are allowed; audit trail required; partition by retention window; policy per graph
   - **Rationale:**
     - No deletes mandate is operationally untenable (GDPR, cost)
     - Audit trail (decision record with cause) provides accountability
     - Irreversibility gates (no deletes until Phase 0 exit) protect design convergence
   - **Implications:**
     - Every delete must be preceded by a decision record
     - Graphs partitioned by transaction-time window (monthly)
     - Retention policy configured per application (TTL, archive, comply-until)
     - Reconciliation query: `SELECT ?s (COUNT(*) AS ?n) WHERE { ?s ?p ?o } GROUP BY ?s HAVING COUNT(*) > 1` detects collided IRIs post-delete
   - **Validation:** Slice 1 pattern O (partition example)

8. **ADR-A-Query** → `docs/architecture/decisions/ADR-A-query-discipline-and-safety.md`
   - **Decision:** No string concat (injection); no `now()` in guards (determinism); Cursor not collection (memory); L2 + L8 tests
   - **Rationale:** Prevents injection, ensures reproducibility, scales to large queries, catches edge cases in adversarial test
   - **Implications:**
     - All SPARQL must use `PreparedQuery` + `Params` (language-level)
     - Time must be an input parameter, never derived from wall clock
     - Result-returning methods return `Cursor<T>` not `List<T>`
     - Every determinism claim has a permutation + repeat test (L2)
     - Store isolation verified empirically (no assumptions)
   - **Validation:** Slice 1 pattern Q + Slice 2 lint/archunit enforcement

2. **Status record** → `docs/developer/status/rdf-sparql-patterns-status.md`
   - Slice completion status + evidence links
   - Open questions (Part 5 of sketch)
   - Proposed review checklist for human decision

**Validation pack:**
- Test level: L4 (design validation)
- Command: `mise decisions:review` (renders ADR markdown + traceability)
- Expected artifacts: Decision record status, links to pattern docs, reviewer checklist
- Deliberate non-coverage: Implementation code (Phase 0); store certification (Phase 1); performance tuning (Phase 0.5)

---

## Part 2 — Execution plan and dependencies

### Timeline

| Slice | Identifier | Duration | Start | End | Blockers |
|-------|-----------|----------|-------|-----|----------|
| **Sketch** | `rdf-sparql-patterns-sketch` | — | ✅ Done | ✅ | — |
| **1. Core patterns** | `rdf-sparql-core-patterns` | 0.5 days | Ready | Sketch + Notes | None |
| **2. Store adapters + policy** | `rdf-sparql-store-adapters` | 0.4 days | After Slice 1 | Slice 1 output | None |
| **3. ADRs + status** | `rdf-sparql-adrs-and-status` | 1 day | After Slice 2 | Slice 2 output | None |

**Total:** 1.9 days (2 agent-days, parallel where possible)

### Entry and exit criteria

**Entry (whole plan):**
- ✅ Sketch approved: [rdf-sparql-implementation-patterns.md](../sketches/rdf-sparql-implementation-patterns.md)
- ✅ Notes reviewed and accuracy confirmed
- ✅ Architecture Review counter-arguments incorporated

**Exit (whole plan):**
- ✅ All 5 design pattern docs complete with runnable examples
- ✅ Store adapter guide for Jena TDB2 + roadmap for GraphDB
- ✅ 8 ADRs drafted with full rationale and implications
- ✅ Lint and CI gate specs ready for Phase 0 implementation
- ✅ Test infrastructure templates in place
- ✅ Status record complete and reviewed
- ✅ Traceability matrix updated (`docs/traceability/matrix.csv`)

**Exit criteria metrics:**
- `mise patterns:validate-sparql` passes 100% (all pattern test cases pass against TDB2)
- `mise patterns:validate-enforced` produces no new violations (lint + archunit)
- ADR checklist reviewed and signed off
- No open questions remain unanswered (or documented as deferred to Phase 0)

---

## Part 3 — Success criteria and validation

### Validation pack location

`docs/developer/validation/rdf-sparql-patterns-phase.md`

### Acceptance criteria (5-step gate)

**Step 1: Review VPs before running**
- Is the test taxonomy correct? (L1 + L3 for Slices 1–2; L4 for Slice 3)
- Are the examples actually portable or TDB2-specific?
- Do the ADRs capture the counter-arguments from Architecture Review?

**Step 2: Run single command**
```bash
mise patterns:validate-sparql && mise patterns:validate-enforced && mise decisions:review
```

**Step 3: Inspect artifacts**
- Pattern docs: 5 files, each with 2–4 pages + runnable examples
- Store adapters: Jena TDB2 fully documented, GraphDB roadmap clear
- ADRs: 8 decisions, each with rationale + implications + risks
- Test infrastructure: templates ready for Phase 0

**Step 4: Adversarial probe**
- Pick one pattern (e.g., K1: deterministic IRI uniqueness)
- Ask: "Show me this pattern *fails* if we use non-deterministic IRI generation"
- Verify test catches the bug
- Repeat for one pattern per Slice

**Step 5: Sign-off**
- Recorded in `docs/developer/validation/LOG.md`
- ADR review checklist signed (human decision on A74/A75)
- Phase 0.2 implementation can begin

---

## Part 4 — Integration with Phase 0

### Immediate next steps (after plan approval)

1. **Phase 0.2 (Walking skeleton)** implementation depends on:
   - Pattern T (concurrent write + ordering) ✅ (from Slice 1)
   - Pattern C (guarded update) ✅ (from Slice 1)
   - Jena TDB2 store adapter ✅ (from Slice 2)
   - Lint/archunit rules ✅ (from Slice 2)

2. **Phase 0.3 (Schema & contracts)** depends on:
   - Pattern K (uniqueness) ✅ (from Slice 1)
   - External allocator escape hatch ✅ (from Slice 1)
   - Policy enforcement ✅ (from Slice 2)

3. **Phase 0.4 (Canonicalization)** depends on:
   - Pattern O (dense ordering) ✅ (from Slice 1)
   - Epoch/restart safety rules ✅ (from Slice 1)
   - Query discipline (QP) ✅ (from Slice 1)

### Deferred to Phase 1+

- GraphDB store adapter (Slice 2 roadmap only)
- Neptune store adapter (Slice 2 roadmap only)
- Performance tuning (L7 SLO benchmark, Phase 0.5)
- LLM integration with decision node history (Phase 2)
- Multi-region deployment (Phase 4, Distribution SPI)

---

## Appendix: Reference documents

- **Sketch:** [rdf-sparql-implementation-patterns.md](../sketches/rdf-sparql-implementation-patterns.md)
- **Notes:** `docs/developer/notes/` (4 files: Uniqueness, Ordering, Concurrency, Combined)
- **Architecture Review:** `docs/architecture/Architecture Review.md` (§5.6, §5.11–5.12 counter-arguments)
- **Epic plan:** [lattice-platform-agentic-development-v0.2.md](lattice-platform-agentic-development-v0.2.md)
