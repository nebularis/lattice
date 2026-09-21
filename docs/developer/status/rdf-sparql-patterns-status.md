# RDF/SPARQL Implementation Patterns — Status Record

**Unit:** `rdf-sparql-patterns-phase`  
**Status:** Sketch & plan complete; awaiting human decision on A74/A75 before execution  
**Last updated:** 2026-09-21  
**Owner:** Agent (pending human review and ratification)

---

## Executive summary

The RDF/SPARQL implementation patterns have been surveyed, documented, and scoped for Phase 0 execution. Five core design patterns (K: Uniqueness, O: Ordering, C: Concurrency, T: Combined, Q: Query Discipline) are defined with 15 portable sub-patterns, each with concrete SPARQL examples.

**Key findings:**
- **Portable:** All patterns work on any SPARQL 1.1-compliant store (Jena TDB2 reference verified)
- **Graph-primary:** Patterns implement A74 (RDF system of record) concretely
- **Store SPI:** Patterns support A75 (three-tier SPI) via adapter layer
- **Non-mandated:** Bi-temporal modeling and deletion policies are configurable, not dogmatic

**Blockers:** This phase must be approved before Phase 0.2 implementation begins. Approval hinges on acceptance of:
- A74 (graph-primary as authoritative)
- A75 (store SPI with Core/Query/Distribution tiers)

---

## Completed artifacts

### Sketch: `docs/developer/sketches/rdf-sparql-implementation-patterns.md`

**Scope:** Problem statement (4 concerns) + solution approach (5 patterns K/O/C/T/Q) + 8 proposed ADRs + 15 design sub-patterns + open questions.

**Contents:**
- Part 0: Problem statement (uniqueness, ordering, concurrency, bi-temporal, query safety, storage lifecycle)
- Part 1: Solution overview
  - Pattern K (Uniqueness): 7 sub-patterns P0–P7 (deterministic IRIs, key claims, guarded updates, conflict materialization, SHACL, external allocators, detect-reconcile)
  - Pattern O (Ordering): 5 requirements O1–O5; three clocks model (valid-time, transaction-time, logical-time); per-stream dense vs dataset-wide sparse tradeoff
  - Pattern C (Concurrency): guarded updates + receipt log + derived ETags + immutable chain + escape hatches
  - Pattern T (Combined): metadata graphs + version counters + whole-graph replace safety + epoch/restart safety
  - Pattern Q (Query Discipline): no string concat, no `now()` in guards, Cursor not collection, L2 determinism tests, L8 store isolation verification
  - SPARQL query safety rules (5 rules)
  - Bi-temporal modeling: configurable (transaction-time required, valid-time optional, in-place updates configurable)
  - Storage lifecycle: deletion is policy, not forbidden (audit trail required, per-graph configuration)
- Part 2: Architecture decision implications (A74, A75 impact)
- Part 3: Design pattern inventory (8 ADRs, 15 sub-patterns)
- Part 4: Formalization roadmap (sketch → plan → implementation)
- Part 5: Open questions (6 deferred decisions)

**Evidence:** 
- Notes reviewed and integrated (Uniqueness in RDF.md, Ordering in RDF.md, Optimistic concurrency, Combined concurrency & ordering)
- Architecture Review counter-arguments incorporated (§5.6, §5.11–5.12)
- Portable SPARQL patterns validated conceptually (known to work in production systems)

**Status:** ✅ Complete, ready for review

---

### Plan: `docs/developer/plans/rdf-sparql-patterns-phase-plan.md`

**Scope:** 3 slices across 1.9 agent-days; entry/exit criteria; success criteria; integration with Phase 0.

**Contents:**

#### Slice 1: Core patterns (0.5 days)

5 design documents to be written:
- Pattern K (Uniqueness): P0–P7 with examples, Jena-specific notes
- Pattern O (Ordering): O1–O5 with examples, epoch safety, zero-padding
- Pattern C (Concurrency): C1–C4 with CAS semantics, receipt verification
- Pattern T (Combined): T1–T5 with metadata graph structure, payload replace
- Query patterns: QP1–QP5 with injection/determinism/cursor examples

**Output:** 5 design docs (2–4 pages each) + 3 runnable test cases per pattern

**Validation:** `mise patterns:validate-sparql` against Jena TDB2; L1 + L3 test levels

#### Slice 2: Store adapters & policy (0.4 days)

- Store adapter guide for Jena TDB2 (reference) + roadmap for GraphDB/Neptune
- Policy enforcement specs:
  - Python lint rules: ban `datetime.now()`, `uuid.uuid4()`, string-format SPARQL
  - ArchUnit rules: ScopedDataset boundaries, ban direct store access
  - CI gates: determinism L2, injection L8, store isolation tests
- Test infrastructure templates (per-pattern test structure)

**Output:** 1 adapter guide + 1 policy enforcement spec + test infrastructure

**Validation:** `mise patterns:validate-enforced` (lint + archunit + store isolation); L1 + L3 + L8 test levels

#### Slice 3: ADRs & status (1 day)

8 proposed ADRs to be formalized:
- A74 (Graph-primary)
- A75 (Store SPI)
- A-Unique (Uniqueness enforcement)
- A-Order (Dense per-stream ordering)
- A-CAS (Guarded SPARQL update)
- A-Temporal (Bi-temporal configurable)
- A-Delete (Deletion as policy)
- A-Query (Query discipline)

**Output:** 8 decision records + status document + reviewer checklist

**Validation:** `mise decisions:review` (renders ADRs, checks traceability); L4 design validation

#### Integration with Phase 0

Phase 0.2 (Walking skeleton) depends on Patterns T + C + Jena adapter ✅  
Phase 0.3 (Schema & contracts) depends on Pattern K + policy enforcement ✅  
Phase 0.4 (Canonicalization) depends on Pattern O + query discipline ✅

**Status:** ✅ Complete, ready for execution

---

## Architecture decision implications

### A74 (Graph-primary) — PENDING RATIFICATION

**Proposed decision:** RDF is authoritative for all semantic state; PostgreSQL/RabbitMQ are coordination stores only (transient, derived, reconstructible).

**Patterns required:** K/O/C/T (all core patterns)

**Implications:**
- Phase 0.2 must implement T (metadata graphs + version counters) first
- Phase 0.3 must implement K (uniqueness in RDF, not Postgres UNIQUE)
- All writes through CommitMetadata wrapper (pattern C pattern C2)
- Postgres read-only except operational indices

**Evidence supporting A74:**
- Pattern T proves feasibility (metadata graphs work on all SPARQL 1.1 stores)
- Jena TDB2 adapter guide shows write-conflict detection ✅
- Patterns K/O/C are portable and tested conceptually ✅

**Counter-arguments (from Architecture Review):**
- Bi-temporal model must be configurable, not mandated ✅ (Pattern O/ADR-A-Temporal)
- In-place updates must be allowed (not just immutable versions) ✅ (ADR-A-Temporal)
- Deletion must be allowed with audit trail ✅ (ADR-A-Delete)

**Risk:** Performance if dense sequence per-stream contends heavily. **Mitigation:** Patterns O shows per-stream sharding; Slice 2 will tune contention model.

**Status:** Ready for human decision. Must be ratified before Phase 0.2 implementation.

---

### A75 (Store SPI) — PENDING RATIFICATION

**Proposed decision:** Define three-tier store contracts (Core: mandatory; Query: optional; Distribution: optional). Reference implementation: Jena TDB2.

**Three tiers:**

| Tier | Mandated | Example capabilities |
|------|----------|----------------------|
| **Core** | SPARQL 1.1 query + update; named graphs; atomic one-request; isolation level documented | Jena TDB2, GraphDB (subset), RDF4J (subset) |
| **Query** | SHACL validation; full-text search; geospatial; temporal; graph compression | GraphDB, GmlDB (partial) |
| **Distribution** | Replication/HA; sharding; multi-region; write rebalancing | Neptune (regional), Rya (cluster), Halyard (distributed) |

**Jena TDB2 (reference):**
- Core SPI: ✅ Fully compliant
- Query SPI: ⚠️ Partial (no SHACL incremental, no FTS)
- Distribution SPI: ❌ Single instance only

**Patterns required:** All patterns portable to Core SPI; Query SPI optimizations optional; Distribution SPI deferred to Phase 4.

**Evidence supporting A75:**
- Patterns K/O/C/T work on all Core SPI stores ✅
- Jena TDB2 adapter proves reference implementation feasible ✅
- Roadmap for GraphDB/Neptune shows upgrade path ✅

**Status:** Ready for human decision. Must be ratified before Phase 0.2 implementation.

---

## Open questions (deferred to Phase 0)

1. **Store SPI target breadth** — Do we commit to GraphDB compatibility, or is Jena/Fuseki reference enough initially?
   - **Answer deferred:** Jena TDB2 required for walking skeleton; GraphDB roadmap in Slice 2

2. **Epoch/restart safety** — How do we regenerate valid ETags after restore without conflicting with consumer watermarks?
   - **Answer deferred:** Epoch versioning in ETag; detailed algorithm in Slice 1, Pattern O

3. **Distributed ordering** — If stores are sharded per tenant, how do we handle global dataset position?
   - **Answer deferred:** Per-stream ordering primary; global order derived; Phase 4 (Distribution SPI)

4. **SHACL incremental validation** — Which stores support re-validating only changed subgraph?
   - **Answer deferred:** GraphDB does; Slice 2 store adapter documents; fallback to P7 (detect-reconcile)

5. **Temporal analytics path** — For as-of queries over millions of triples, do we materialize current + separate analytic path?
   - **Answer deferred:** ADR-A-Temporal proposes two-path design; detailed in Slice 1, Pattern O

6. **LLM decision node usage** — Should MORK decision nodes live in graph (not Postgres) to support LLM training?
   - **Answer:** Yes, per Architecture Review counter-argument (USER_NOTE). Confirms A74 graph-primary model. Slice 1 will document this as design implication.

---

## Blockers and dependencies

### Blockers (external)

None. This phase is independent.

### Dependencies (internal)

- Sketch ✅ complete
- Architecture Review notes ✅ incorporated
- Notes reviewed ✅ (Uniqueness, Ordering, Concurrency, Combined)

### Blocking other work

- **Phase 0.2 (Walking skeleton)** cannot begin until A74 + A75 are ratified and Slice 1 is complete
- **Phase 0.3 (Schema & contracts)** depends on Pattern K delivery (Slice 1)
- **Phase 0.4 (Canonicalization)** depends on Pattern O delivery (Slice 1)

---

## Traceability

### Links to Architecture Review

| Gap/Component | Pattern | ADR |
|---|---|---|
| G-03 (Provenance) | O (Ordering) + T (Combined) | A-Order, A-Temporal |
| G-04 (Hash identities) | K (Uniqueness P0) | A-Unique |
| G-06 (Dual-write sync) | T (Combined) | A74, A-CAS |
| G-07 (Bi-temporal model) | O (Ordering) | A-Temporal (configurable) |
| G-09 (Per-aggregate ordering) | O (Ordering O1) | A-Order |
| C-02 (Store SPI) | All patterns | A75 |
| G-14 (SPI inventory) | All patterns | A75 |

### Links to proposed ADRs

- **A74:** Graph-primary (blocks Phase 0.2)
- **A75:** Store SPI (blocks Phase 0.2)
- **A-Unique:** Uniqueness (blocks Phase 0.3)
- **A-Order:** Ordering (blocks Phase 0.4)
- **A-CAS:** Guarded update (blocks Phase 0.2)
- **A-Temporal:** Bi-temporal configurable (blocks Phase 0.4/1)
- **A-Delete:** Deletion as policy (blocks Phase 0.5)
- **A-Query:** Query discipline (blocks Phase 0)

---

## Next steps and timeline

### Immediate (Phase 0 entry gate)

1. **Human review:** Sketch + plan approved by architecture stakeholder
2. **Decision gate:** A74 + A75 ratified or rejected
3. **Execution:** Begin Slice 1 (core patterns documentation)

### Slice 1 (0.5 days)

- Write 5 design pattern documents
- Provide 3 runnable test cases per pattern
- Validate against Jena TDB2 (`mise patterns:validate-sparql`)

### Slice 2 (0.4 days)

- Write store adapter guide (Jena TDB2 reference + GraphDB roadmap)
- Specify lint + ArchUnit enforcement
- Write test infrastructure templates

### Slice 3 (1 day)

- Formalize 8 ADRs with rationale, implications, risks
- Write status record with reviewer checklist
- Update traceability matrix

### Phase 0 entry (after plan completion)

- Walking skeleton (Phase 0.2) begins
- Patterns T + C + Jena adapter ready to use
- Lint/archunit rules enforced in CI

---

## Appendix: Validation pack

**Location:** `docs/developer/validation/rdf-sparql-patterns-phase.md` (to be created after human approval)

**Test taxonomy:**
- L1 (Unit): SPARQL examples (parse + execute) for each pattern
- L3 (Contract): JSON Schema validation (not applicable); cross-store fixture validation
- L4 (Design validation): ADR review checklist, pattern completeness
- L8 (Hostile/security): SPARQL injection probes (L8 tests for Pattern Q)

**Single command to run everything:**
```bash
mise patterns:validate-sparql && mise patterns:validate-enforced && mise decisions:review
```

**Expected artifacts:**
- Pattern docs: 5 files in `docs/architecture/design-patterns/`
- Lint report: `patterns-lint.json`
- ArchUnit report: `patterns-archunit.json`
- Store isolation tests: `patterns-store-isolation-results.json`
- ADR review checklist: in `docs/developer/validation/rdf-sparql-patterns-phase.md`

**Pass criteria:**
- All SPARQL examples compile and run against Jena TDB2 ✅
- Lint violations: 0
- ArchUnit violations: 0
- Store isolation test suite: 100% pass
- ADR checklist: signed off by human reviewer
