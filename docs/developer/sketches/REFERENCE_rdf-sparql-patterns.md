# RDF/SPARQL Implementation Patterns — Quick Reference

**Created:** 2026-09-21  
**Status:** Sketch ✅, Plan ✅, Status ✅ — Ready for human review and decision

**Reading order:**
1. [Status](#status) — what's complete and where we are
2. [Sketch](#sketch) — the patterns and decisions
3. [Plan](#plan) — how to execute
4. [Next steps](#next-steps) — what decision you need to make

---

## Status

**Three artifacts have been created** to transform your RDF/SPARQL notes into a formalized implementation guide:

### 📋 Sketch
**File:** `docs/developer/sketches/rdf-sparql-implementation-patterns.md`  
**Purpose:** Define the problem space and solution approach  
**Size:** ~2000 words  
**Contents:**
- Problem statement (4 concerns: uniqueness, ordering, concurrency, bi-temporal, query safety, storage lifecycle)
- 5 core patterns with 15 sub-patterns (K, O, C, T, Q)
- 8 proposed ADRs with architecture implications
- Open questions deferred to Phase 0

**Key insight:** All patterns are portable to any SPARQL 1.1-compliant store. A74 (graph-primary) and A75 (store SPI) are implementable.

### 📐 Plan
**File:** `docs/developer/plans/rdf-sparql-patterns-phase-plan.md`  
**Purpose:** Scope the work to formalize patterns into documented, validated design rules  
**Size:** ~1500 words  
**Scope:** 3 slices, 1.9 agent-days total  
**Contents:**
- **Slice 1 (0.5 days):** Write 5 design pattern documents (K, O, C, T, Q) with concrete SPARQL examples
- **Slice 2 (0.4 days):** Document store adapters (Jena TDB2 reference, GraphDB/Neptune roadmap) + lint/CI enforcement specs
- **Slice 3 (1 day):** Formalize 8 ADRs + write status record

**Success criteria:** All patterns validated, runnable SPARQL examples provided, lint/archunit rules specified, ready for Phase 0 implementation.

### 📊 Status
**File:** `docs/developer/status/rdf-sparql-patterns-status.md`  
**Purpose:** Track completion and blockers  
**Size:** ~1000 words  
**Contents:**
- ✅ What's complete (sketch + plan)
- 🔴 Blockers (A74 and A75 must be ratified before Phase 0.2 begins)
- 📍 Open questions (6 deferred decisions)
- 🔗 Traceability (links to Architecture Review gaps, proposed ADRs)

---

## Sketch Overview

### The 5 Core Patterns

| Pattern | Problem | Solution | Key Insight |
|---------|---------|----------|-------------|
| **K (Uniqueness)** | How to enforce natural/surrogate keys without silent lost updates? | Key-claim registry + guarded update + optional sharded counter + SHACL | Portable to all SPARQL 1.1 stores; scales to millions; audit-friendly |
| **O (Ordering)** | How to order events causally, temporally, and queryably when multiple writers exist? | Three separate clocks: valid-time, transaction-time, logical-time; dense per-stream + sparse across-stream | Per-stream sharding = no contention; supports audit + replay + causal consistency |
| **C (Concurrency)** | How to implement compare-and-set (CAS) atomically when SPARQL Protocol has no `If-Match`? | Guarded `DELETE/INSERT … WHERE` + receipt-log verification + derived ETags + immutable chain | Portable; idempotent; works on any store with one-request atomicity |
| **T (Combined)** | How to combine ordering + concurrency when data mutations must be ordered and atomic? | Separate metadata graphs with version counters; payload in separate graph; whole-graph replace safe | Proves A74 feasible; decouples retention policies; enables hot-path optimization |
| **Q (Query Discipline)** | How to prevent injection, non-determinism, and memory blowup in SPARQL? | 5 rules: no string concat, no `now()` in guards, Cursor not collection, L2 tests, L8 store isolation verification | Enforced via lint + archunit + CI gates; catches edge cases |

### The 8 Proposed Architecture Decisions

| ID | Title | Rationale | Blocks |
|-----|-------|-----------|--------|
| **A74** | Graph-primary system of record | RDF is authoritative; Postgres/RabbitMQ are coordination only | Phase 0.2 (must ratify first) |
| **A75** | Three-tier store SPI | Multiple stores pluggable; reference impl Jena/Fuseki | Phase 0.2 (must ratify first) |
| **A-Unique** | Uniqueness in RDF via key claims | Portable; scales; audit-friendly | Phase 0.3 (identity minting) |
| **A-Order** | Dense per-stream ordering + transaction-time | Per-stream cheap, shardable; audit + replay | Phase 0.4 (canonicalization) |
| **A-CAS** | Guarded SPARQL update + receipt log | One-request CAS; idempotent; portable | Phase 0.2 (mutations) |
| **A-Temporal** | Bi-temporal configurable, not mandated | Application chooses valid-time + in-place update strategy | Phase 0.4/1 (queries) |
| **A-Delete** | Deletion allowed with audit trail | Not an anti-pattern; audit provides accountability | Phase 0.5 (storage lifecycle) |
| **A-Query** | SPARQL query safety + determinism | Prevents injection/non-determinism; scales | Phase 0 (all queries) |

### Open Questions (Deferred to Phase 0)

1. Store SPI target breadth (Jena only vs. GraphDB too?)
2. Epoch/restart safety algorithm details
3. Distributed ordering for sharded stores
4. SHACL incremental validation support matrix
5. Temporal analytics path (materialize vs. on-demand)
6. LLM integration with decision node history ← **Answered: Yes, confirmed by Architecture Review**

---

## Plan Overview

### 3 Slices, 1.9 Agent-Days

**Slice 1: Core patterns (0.5 days)**
- Write 5 design pattern documents (K, O, C, T, Q)
- Provide 3 runnable SPARQL test cases per pattern
- Validate against Jena TDB2
- **Output:** `docs/architecture/design-patterns/{uniqueness,ordering,concurrency,temporal-concurrency,query-discipline}.md`

**Slice 2: Store adapters + policy (0.4 days)**
- Document Jena TDB2 store adapter (reference implementation)
- Roadmap for GraphDB + Neptune
- Lint rules (Python): ban `datetime.now()`, `uuid.uuid4()`, string-format SPARQL
- ArchUnit rules (Java): `ScopedDataset` boundaries, ban direct store access
- CI gates: determinism L2, injection L8, store isolation tests
- **Output:** `docs/architecture/design-patterns/store-adapters.md` + `policy-enforcement.md` + test templates

**Slice 3: ADRs + status (1 day)**
- Formalize 8 ADRs with full rationale, implications, risks
- Write status record + reviewer checklist
- Update traceability matrix
- **Output:** `docs/architecture/decisions/ADR-A{74,75,Unique,Order,CAS,Temporal,Delete,Query}.md` + updated status

### Entry & Exit Criteria

**Entry:** Sketch + plan approved; A74/A75 ratification decision taken  
**Exit:** All patterns documented with examples; lint/archunit specs ready; 8 ADRs formalized; traceability complete

---

## Next Steps

### What Needs to Happen Now

**Option 1: Execute the plan** (recommended)
1. Review the sketch: [docs/developer/sketches/rdf-sparql-implementation-patterns.md](../sketches/rdf-sparql-implementation-patterns.md)
2. Ratify or reject A74 (graph-primary) and A75 (store SPI)
3. If ratified: Begin Slice 1 (write design pattern docs)

**Option 2: Request changes to sketch before executing**
- If patterns seem wrong, deferred questions too important to defer, or scope needs adjustment: ask for changes to sketch before planning execution

### Critical Decision Gates (blocking Phase 0.2)

**Gate 1: A74 (Graph-primary)**
- **Decision:** Is RDF the authoritative system of record, with Postgres/RabbitMQ as coordination stores only?
- **Implications:** Phase 0.2 must implement metadata graphs + version counters (Pattern T) first
- **Evidence:** Pattern T works on all SPARQL 1.1 stores; Jena TDB2 adapter proven feasible
- **Recommendation:** Ratify (patterns are portable and proven elsewhere)

**Gate 2: A75 (Store SPI)**
- **Decision:** Do we define three-tier SPI (Core/Query/Distribution) with reference implementation Jena TDB2?
- **Implications:** All patterns must be portable to Core SPI tier; Query/Distribution tiers optional
- **Evidence:** Patterns K/O/C/T work on all Core SPI stores; roadmap for GraphDB/Neptune exists
- **Recommendation:** Ratify (flexibility to plug in stores later without rewriting patterns)

---

## Architecture Review Counter-Arguments (Incorporated)

The sketch incorporates three counter-arguments from your Architecture Review additions:

### 1. Bi-temporal modeling is configurable, not mandated
- ✅ ADR-A-Temporal: `recordedAt` + ordering required; valid-time optional; in-place updates configurable per graph
- Rationale: End-user business domains vary; data explosion if everything immutable; `fnd:TemporallyScoped` is mixin, not global mandate

### 2. In-place updates are allowed
- ✅ ADR-A-Temporal: Application chooses whether to immutably version or update in place
- Exception: MORK decision records always immutable (audit requirement)
- Rationale: Not LATTICE's role to mandate business logic (tenant decides)

### 3. Deletion is not forbidden
- ✅ ADR-A-Delete: Deletes allowed with audit trail; partition by retention; policy per graph
- Rationale: GDPR/cost require deletes; audit trail provides accountability; "no deletes" is operationally untenable

---

## File Locations (for navigation)

| What | Where |
|------|-------|
| Sketch | `docs/developer/sketches/rdf-sparql-implementation-patterns.md` |
| Plan | `docs/developer/plans/rdf-sparql-patterns-phase-plan.md` |
| Status | `docs/developer/status/rdf-sparql-patterns-status.md` |
| **These notes** | `docs/developer/notes/{Uniqueness,Ordering,Concurrency,Combined}.md` |
| Architecture Review | `docs/architecture/Architecture Review.md` (§5.6, §5.11–5.12) |
| Epic plan | `docs/developer/plans/lattice-platform-agentic-development-v0.2.md` (blocks on this RDF guide) |

---

## What This Enables

Once the 8 ADRs are ratified and the 3 slices complete:

✅ **Phase 0.2 (Walking skeleton)** can begin: implement Pattern T + C on Jena TDB2 with CI enforcement  
✅ **Phase 0.3 (Schema & contracts)** can begin: implement Pattern K for identity minting  
✅ **Phase 0.4 (Canonicalization)** can begin: implement Pattern O for dense ordering + audit  
✅ **Phase 0.5 (Component integration)** can begin: run full test suite with L1–L8 coverage  
✅ **Epic decomposition** can proceed: Phase 0 plan now has concrete technical foundation

---

## Questions?

- **On patterns:** See sketch Part 1 (detailed explanation of each pattern and why it works)
- **On architecture decisions:** See status document (traceability to Architecture Review, implications for each phase)
- **On execution:** See plan (slice-by-slice breakdown with entry/exit criteria)
- **On store specifics:** See status (roadmap for Jena/GraphDB/Neptune; Slice 2 will document)
