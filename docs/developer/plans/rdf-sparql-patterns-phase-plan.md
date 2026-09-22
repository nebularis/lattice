<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# RDF/SPARQL Implementation Patterns — Phase Plan

**Unit type:** Plan
**Identifier:** `rdf-sparql-patterns-phase`
**Status:** Slice 1 complete. Slices 2 and 3 ready for execution, pending ADR ratification.
**Blocks:** `ontology/persistence` authoring, `tools/persistence` compiler, `platform/housekeeping` first cut, and (once the store SPI exists) the Request Query Mapping and Query Execution work items this plan explicitly excludes.
**Estimated scope:** see [Part 2](#part-2--execution-plan-and-dependencies) for a per-slice token estimate. These are planning estimates, not commitments, and are to be checked against actual consumption once each slice completes.

**This is a rewrite.** It replaces the previous version of this plan in place, at the same path and under the same unit identifier. The previous Slice 2 ("Store-specific adapters and policy") is removed entirely: store adapter documentation is deferred to a future SPI-focused phase, not part of this plan. Its replacement Slice 2 is the ontology substrate and the compiler toolchain described below, per the commissioning conversation that produced [persistence-profile-substrate.md](../sketches/persistence-profile-substrate.md). The previous Slice 3 ("Proposed ADRs and decision record") is superseded because its ADRs are delivered alongside this rewrite, per the Design First rule in `.github/copilot-instructions.md`, rather than scheduled as a future slice. Slice 3 is repurposed for the housekeeping first cut.

**Purpose:** Turn [rdf-sparql-patterns-guide.md](../../architecture/rdf-sparql-patterns-guide.md)'s portable patterns into something an adopter of LATTICE can actually select and generate SPARQL from, at whatever granularity their own applied ontology needs, without requiring them to hand-write the guide's SPARQL or adopt a store SPI that does not yet exist.

**Entry criteria:**
- Guide complete: [rdf-sparql-patterns-guide.md](../../architecture/rdf-sparql-patterns-guide.md) (fulfils Slice 1, see [§1.1](#11-slice-1--core-patterns-and-design-specs-complete))
- Sketch complete: [persistence-profile-substrate.md](../sketches/persistence-profile-substrate.md)
- ADR-A78, ADR-A79, ADR-A80 ratified (currently Proposed, see [Part 0.1](#01-proposed-adrs-delivered-with-this-rewrite))

**Success criteria:**
- `ontology/persistence` authored, validated against its own SHACL shapes, documented
- `tools/persistence` compiler implemented, passing its injection corpus and its own test suite
- `platform/housekeeping` module scaffolded with the contracts, configuration model, and generated queries described in [ADR-A80](../../architecture/decisions/ADR-A80-housekeeping-component-boundary.md)
- `ontology-architecture.md` and the root `README.md` updated per the Design First contract's "kept up to date" list
- Status recorded in `docs/developer/status/rdf-sparql-patterns-status.md`
- No SPI code, no Request Query Mapping library, no Query Execution component delivered by this plan (see [Part 5](#part-5--explicitly-out-of-scope))

---

## Part 0 — Dependencies, ordering, and governance

### 0.1 Proposed ADRs delivered with this rewrite

Per the Design First rule, a plan of this scope is preceded by a proposed ADR. Three are delivered with this rewrite, all Status: Proposed, awaiting human ratification before Slices 2 and 3 begin execution:

| ADR | Decision |
|---|---|
| [ADR-A78](../../architecture/decisions/ADR-A78-persistence-profile-substrate-and-aggregate-boundaries.md) | `ontology/persistence` substrate: six independently scopable dimensions, five scope kinds, a fixed precedence algorithm, two boundary mechanisms behind two authoring surfaces |
| [ADR-A79](../../architecture/decisions/ADR-A79-persistence-compiler-toolchain.md) | `tools/persistence` compiler: design-time only, template-based, injection-safe by construction, explicit exclusion of Request Query Mapping and Query Execution |
| [ADR-A80](../../architecture/decisions/ADR-A80-housekeeping-component-boundary.md) | `platform/housekeeping`: contracts and configuration model now, execution engine deferred alongside the SPI |

### 0.2 Hard ordering

No external blockers beyond ADR ratification. Slice 2 must complete before Slice 3 begins, because the housekeeping module's generated queries are produced by the Slice 2 compiler.

### 0.3 What this plan does not schedule

Three items depend on the store SPI (proposed A75), which this plan does not build:

1. The store SPI itself.
2. A runtime "Request Query Mapping" library binding compiled templates and live requests to an SPI.
3. A "Query Execution" component rewriting a compiled template's dialect for a specific backend at request time.

All three are recorded as open design questions in [lattice-platform-agentic-development-v0.2.md](lattice-platform-agentic-development-v0.2.md), Part 13, rows 11 and 12, and Part 6 of that plan carries a note that its ingestion and query-plane slices need revision once this plan's Slice 2 lands, because several of those slices currently assume ad hoc query construction this plan's compiler is meant to replace.

---

## Part 1 — Slice breakdown

### 1.1 Slice 1 — Core patterns and design specs (complete)

**Original objective:** document each of the five core patterns (K, O, C, T, Q) as a design spec with runnable SPARQL examples.

**Status: fulfilled**, not by the five fragmented documents originally planned under `docs/architecture/design-patterns/`, but by the single consolidated [rdf-sparql-patterns-guide.md](../../architecture/rdf-sparql-patterns-guide.md), which covers every sub-pattern (P0–P7, O1–O5, §1.1–1.6, A1–A7, F1–F13, QP1–QP5) with more worked Turtle and SPARQL than the original slice scoped, in one navigable document rather than five. No further work is scheduled against this slice. Its validation, a documentation review rather than a runnable test suite, is recorded in this plan's [status record](../../developer/status/rdf-sparql-patterns-status.md).

### 1.2 Slice 2 — Persistence profile substrate and compiler toolchain

**Slice identifier:** `persistence-substrate-and-compiler`

**Objective:** author `ontology/persistence`, implement `tools/persistence`, and deliver the policy enforcement (lint, ArchUnit, injection corpus) that keeps both honest, per [ADR-A78](../../architecture/decisions/ADR-A78-persistence-profile-substrate-and-aggregate-boundaries.md) and [ADR-A79](../../architecture/decisions/ADR-A79-persistence-compiler-toolchain.md).

**Deliverables:**

1. **`ontology/persistence`** (Turtle, literate spec, matching the `ontology/mork` and `ontology/surface` layout convention):
   - `ontology/persistence/README.md` — purpose, scope, the `dal:` prefix, worked examples (at least the three from [the sketch](../sketches/persistence-profile-substrate.md): the minimal single-class profile, the lending/credit shared-class conflict, and the `CompositePropertyBoundary` aggregate declared via a SHACL shape)
   - `ontology/persistence/spec/persistence.ttl` — the vocabulary in [sketch Appendix A](../sketches/persistence-profile-substrate.md#appendix-a--ontologypersistence-vocabulary-indicative), reviewed and finalised, not copied verbatim
   - `ontology/persistence/shapes/constraints.ttl` — the self-validating SHACL shapes from [sketch §3.9](../sketches/persistence-profile-substrate.md#39-shacl-shapes-for-ontologypersistence-itself), including the `SharedClassProfileWarning` check
   - `ontology/persistence/examples/` — at least: a single-class baseline profile, a namespace-wide profile, the lending/credit graph-pattern-scoped pair, a `CompositePropertyBoundary` example (SHACL shape is the only authoring surface, per [sketch §4.1](../sketches/persistence-profile-substrate.md#41-two-authoring-surfaces-two-runtime-mechanisms)), a sample `dal:CapabilitySpec` and its resulting `dal:CapabilityCheck`, and one deliberately invalid configuration per row of [sketch §3.5](../sketches/persistence-profile-substrate.md#35-cross-axis-consistency-checks)'s table, used as negative fixtures
   - `ontology/persistence/docs/` — the precedence algorithm and the boundary-strategy design, written for a reader who has not read the sketch, cross-referencing it and the guide rather than repeating them

2. **`tools/persistence`** (Python package, `mise bootstrap:persistence` / `mise check:persistence`, following `tools/surface`'s `pyproject.toml` and package layout), two subcommands per [sketch §5.2](../sketches/persistence-profile-substrate.md#52-the-compiler-pipeline):
   - `compile`: loader (parses `ontology/persistence` graphs, an adopter's applied ontology, and an *optional* `dal:CapabilitySpec` — never a live backend connection), resolver (implements [sketch §3.4](../sketches/persistence-profile-substrate.md#34-precedence-and-resolution-algorithm)'s algorithm per dimension, per target, producing `ProfileAmbiguityError` on unresolved ties), validator (every row of [sketch §3.5](../sketches/persistence-profile-substrate.md#35-cross-axis-consistency-checks) and the two boundary-strategy checks in [sketch §4.6](../sketches/persistence-profile-substrate.md#46-boundary-strategy-conflicts), each a named exception type), capability self-check (implements [sketch §3.6](../sketches/persistence-profile-substrate.md#36-reasoning-dependency-and-capability-self-checks)'s unconditional `dal:CapabilityRequirement` computation and the optional `dal:CapabilityCheck` against a supplied spec), and a report writer emitting the `dal:CompiledProfile` graph (Turtle) with its `dal:GeneratedOperation`s and `dal:ParameterBinding`s, per [sketch §6.2](../sketches/persistence-profile-substrate.md#62-compile-output-the-compiled-profile-ttl-canonical)
   - `instantiate`: template renderer, `chevron`-based, the `SparqlTerm`/`Iri`/`Literal`/`Var` encoder hierarchy and the type-enforced `render()` function from [sketch §5.3](../sketches/persistence-profile-substrate.md#53-templating-and-injection-safety-in-the-instantiate-stage), never a bare string reaching a template context, reading a `dal:CompiledProfile` plus the checked-in template library and producing `.rq`/`.ru` files, per [sketch §6.4](../sketches/persistence-profile-substrate.md#64-instantiate-output-generic-sparql-text-optional-derived)
   - templates: one `.mustache` file per generated operation, checked in under `tools/persistence/templates/`, each with a stable `dal:Template` identifier, covering at minimum create-if-absent, CAS-replace (`NamedGraphBoundary` and `CompositePropertyBoundary` variants), tombstone-delete, key-claim write and retire, append (event grain), and the two housekeeping-facing audit queries Slice 3 needs (gap-completeness scan, fork detection), reusing the guide's own worked SPARQL from Chapters 6, 7, 10, 19, and 24 as the reference shape for each template
   - CLI: `python -m persistence compile <config-dir> [--capability-spec <spec.ttl>] --out <compiled-profile.ttl>` and `python -m persistence instantiate <compiled-profile.ttl> --template-dir <dir> --out <dir>`

3. **Injection corpus and property tests**, scoped to `instantiate` only, since `compile` never produces SPARQL text (`tools/persistence/src/persistence/test_injection.py` or equivalent):
   - the adversarial corpus from [sketch §5.3](../sketches/persistence-profile-substrate.md#53-templating-and-injection-safety-in-the-instantiate-stage): unbalanced braces, embedded SPARQL keywords, quote and backslash sequences, bidirectional-override and zero-width Unicode
   - a parse-count assertion using `rdflib.plugins.sparql.parser` against every rendered template for every corpus entry
   - a positive fixture set proving the encoder accepts every valid IRI and literal form the guide's own examples use, so the corpus cannot be satisfied by simply rejecting everything

4. **Policy enforcement**, expanding the original plan's Slice 2 policy section rather than discarding it:
   - **Python lint**, applied to `tools/persistence` specifically: ban any `str` literal containing `SELECT`/`ASK`/`CONSTRUCT`/`INSERT`/`DELETE`/`PREFIX` from being passed to `chevron.render` except through the package's own `render()` wrapper (an AST-level check, not a regex on file contents, so a refactor cannot silently bypass it). Ban `datetime.now()`/`time.time()` in the resolver and encoder modules, mirroring the guide's [QP2](../../architecture/rdf-sparql-patterns-guide.md#chapter-28--five-rules-and-how-they-are-enforced) rule
   - **ArchUnit-equivalent for Python** (since this slice is Python, not Java): a `pytest` collection-time check that no module under `persistence.resolver` or `persistence.encoder` imports `chevron` directly, only `persistence.render`, so the trust boundary in [ADR-A79](../../architecture/decisions/ADR-A79-persistence-compiler-toolchain.md) is enforced by import graph, not by convention
   - **CI gates:** the injection corpus (item 3) as a release gate, not merely a test that can go red without blocking, plus a determinism check (L2) that compiling the same configuration twice, with the individuals' triples permuted, produces byte-identical output, extending the guide's own [QP4](../../architecture/rdf-sparql-patterns-guide.md#chapter-28--five-rules-and-how-they-are-enforced) discipline to the compiler itself

**Doc delta (performed in this slice, per the mandatory slice shape):**
- `docs/architecture/ontology-architecture.md` gains a section describing `ontology/persistence` as a cross-cutting substrate, per [ADR-A78](../../architecture/decisions/ADR-A78-persistence-profile-substrate-and-aggregate-boundaries.md)'s first consequence
- root `README.md` gains an entry for `ontology/persistence` and `tools/persistence`
- `docs/architecture/decisions/README.md` entries for A78/A79 move from Proposed to Accepted once ratified

**Validation pack:**
- Test level: L1 (unit, resolver and encoder) + L2 (determinism) + L4 (SHACL validation of the example fixtures) + L8 (injection corpus)
- Command: `mise check:persistence`
- Expected artifacts: a `dal:CompiledProfile` (the canonical artifact) for every fixture in `ontology/persistence/examples/`, plus `instantiate`d `.rq`/`.ru` files for a representative subset to prove the round trip, an injection-corpus report, a determinism report
- Deliberate non-coverage: no live SPARQL execution against any store (no SPI exists to execute against), no runtime parameter binding (Request Query Mapping, deferred per [Part 5](#part-5--explicitly-out-of-scope)), no store-specific dialect rewriting (Query Execution, deferred)

**Traceability:** `docs/traceability/matrix.csv` gains rows for ADR-A78, ADR-A79, and every guide chapter listed in [sketch Part 8](../sketches/persistence-profile-substrate.md#part-8--traceability), each linked to the test IDs in `tools/persistence`'s test suite.

**Token estimate (planning only, to be checked against actuals):** ontology authoring and shapes, roughly 1.5–2.5M tokens. Compiler implementation including templates and the encoder hierarchy, roughly 4–6M tokens. Injection corpus and determinism tests, roughly 1.5–2.5M tokens. Documentation and doc delta, roughly 1–1.5M tokens. Total order of magnitude 8–12.5M tokens across the slice.

### 1.3 Slice 3 — Housekeeping first cut

**Slice identifier:** `housekeeping-first-cut`

**Objective:** deliver the contracts, configuration model, and generated queries described in [ADR-A80](../../architecture/decisions/ADR-A80-housekeeping-component-boundary.md), with no store-calling execution.

**Deliverables:**

1. **`platform/housekeeping`** Maven module, `org.nebularis.lattice.housekeeping`, added to `platform/pom.xml`'s `<modules>`:
   - `HousekeepingJob`, `JobContext`, `JobResult` interfaces, per [sketch §5.6](../sketches/persistence-profile-substrate.md#56-housekeeping-first-cut)'s contract table, with no implementation that opens a store connection
   - `JobContext` accepts a `dal:CompiledProfile` and `dal:CapabilityRequirement` (the Slice 2 compiler's own output types), read-only, never re-deriving resolution
   - the five job types named in the sketch: `UniquenessReconcilerJob`, `GapCompletenessScanJob`, `ForkDetectionJob`, `RetentionSweepJob`, `BoundaryBudgetJob`, each as an interface implementation stub whose `run()` throws `UnsupportedOperationException("execution engine deferred, see ADR-A80")`, never a silent no-op that could be mistaken for success
   - the operational configuration model (cadence, batch size, dry-run/enforce, alert sink), kept in a Java-native configuration class, explicitly not RDF-backed, with a comment cross-referencing the [data-architecture.md](../../architecture/data-architecture.md) realm split this decision follows

2. **Generated queries**, produced by running the Slice 2 compiler's `instantiate` stage for each job type, checked into `platform/housekeeping/src/main/resources/queries/`, never hand-written inline in Java

3. **Documentation:**
   - `platform/housekeeping/README.md` — configuration split, job taxonomy, the four-stage roadmap from [ADR-A80](../../architecture/decisions/ADR-A80-housekeeping-component-boundary.md), and an explicit statement of what `run()` does today (throws, by design) so no future reader mistakes the stub for a bug
   - `docs/architecture/platform-housekeeping.md` — the architecture-level counterpart, covering the same ground at the level [data-architecture.md](../../architecture/data-architecture.md) and [ontology-architecture.md](../../architecture/ontology-architecture.md) are written at, including a data-flow diagram from compiled profile through `instantiate` to (future) execution engine

**Doc delta (performed in this slice):**
- `docs/architecture/decisions/README.md` entry for A80 moves from Proposed to Accepted once ratified
- root `README.md` gains an entry for `platform/housekeeping`
- `docs/developer/plans/lattice-platform-agentic-development-v0.2.md` Part 6 note (already added by this rewrite's companion edit, see [Part 4](#part-4--integration-with-the-epic-plan)) is checked for continued accuracy once this slice's actual module shape is known

**Validation pack:**
- Test level: L0 (module builds, one no-op test per interface) + L1 (unit tests on the configuration model's parsing and validation) + L3 (contract: the generated query resources parse as valid SPARQL, checked the same way Slice 2's injection corpus checks its own output)
- Command: `mvn -pl platform/housekeeping -am verify`
- Expected artifacts: a build report, the generated query resources, the README and architecture doc
- Deliberate non-coverage: no job actually runs against a store (explicit, by design, per [ADR-A80](../../architecture/decisions/ADR-A80-housekeeping-component-boundary.md)), no scheduler, no alert-sink integration

**Traceability:** `docs/traceability/matrix.csv` gains rows for ADR-A80, linked to the guide's P7/S3/F5 references and to the Slice 2 compiler's generated-query test IDs for the housekeeping templates specifically.

**Token estimate (planning only):** Java module scaffolding and contracts, roughly 1–1.5M tokens. Configuration model and its tests, roughly 1M tokens. README and architecture document, roughly 1–1.5M tokens. Total order of magnitude 3–4M tokens.

---

## Part 2 — Execution plan and dependencies

### Timeline

| Slice | Identifier | Depends on | Estimated tokens |
|---|---|---|---|
| **1. Core patterns** | `rdf-sparql-core-patterns` | — | complete (delivered as the guide) |
| **ADRs A78–A80** | — | Slice 1 (as prior art) | complete (delivered with this rewrite) |
| **2. Substrate and compiler** | `persistence-substrate-and-compiler` | ADR-A78, ADR-A79 ratified | 8–12.5M |
| **3. Housekeeping first cut** | `housekeeping-first-cut` | Slice 2 complete, ADR-A80 ratified | 3–4M |

**Total remaining scope:** order of magnitude 11–16.5M tokens across Slices 2 and 3. These figures are rough planning estimates. Record actual consumption per slice in the status file at completion, so future estimates in this style improve.

### Entry and exit criteria

**Entry (whole plan):**
- Guide complete ✅
- Sketch complete ✅
- ADR-A78, ADR-A79, ADR-A80 ratified (pending)

**Exit (whole plan):**
- `ontology/persistence` authored and self-validating
- `tools/persistence` implemented, injection corpus and determinism tests green
- `platform/housekeeping` scaffolded per [ADR-A80](../../architecture/decisions/ADR-A80-housekeeping-component-boundary.md)
- `ontology-architecture.md`, root `README.md`, and the decisions index updated
- Status record complete
- `docs/traceability/matrix.csv` rows present for every claimed requirement

---

## Part 3 — Success criteria and validation

### Acceptance criteria (5-step gate, per `.github/copilot-instructions.md`)

**Step 1: Review VPs before running.** Confirm the injection corpus in Slice 2 actually attempts the failure modes named in [sketch §5.3](../sketches/persistence-profile-substrate.md#53-templating-and-injection-safety-in-the-instantiate-stage), not a weaker substitute, and that Slice 3's deliberate `UnsupportedOperationException` stubs are not mistaken for missing test coverage.

**Step 2: Run the single command per slice.**
```bash
mise check:persistence
mvn -pl platform/housekeeping -am verify
```

**Step 3: Inspect named artifacts.** Compiled profile reports and generated SPARQL for every example fixture, the injection-corpus and determinism reports, the housekeeping module's generated query resources, both new architecture documents.

**Step 4: Adversarial probe.** Pick one injection-corpus entry and demonstrate the encoder fails open to rejection, not silent pass-through, by temporarily reverting the encoder to naive string interpolation and showing the corpus test catches it. Pick one cross-axis consistency check from [sketch §3.5](../sketches/persistence-profile-substrate.md#35-cross-axis-consistency-checks) and demonstrate the compiler accepts the invalid configuration when the check is disabled.

**Step 5: Sign-off** in `docs/developer/validation/LOG.md`, naming both slice IDs, and the ADR ratification decision.

---

## Part 4 — Integration with the epic plan

[lattice-platform-agentic-development-v0.2.md](lattice-platform-agentic-development-v0.2.md) Part 6 (Phase 2, ingestion and query planes) is marked, in the same edit that accompanies this rewrite, as pending revision once this plan's Slice 2 lands, because P2.1 (mapping plan compiler), P2.3 (ingestion gateway), and P2.4 (query and decision plane) currently assume SPARQL is constructed ad hoc rather than compiled from a `dal:` profile. That revision is not scoped here. Part 13 of the same document gains two new open-question rows for the Request Query Mapping and Query Execution items this plan excludes.

---

## Part 5 — Explicitly out of scope

| Item | Why | Recorded |
|---|---|---|
| Store SPI (proposed A75) | Its shape is undecided, and both excluded items below depend on it | not yet an ADR, referenced throughout the guide and this plan as pending |
| Request Query Mapping library | Needs the SPI to inject, would need redoing once the SPI exists | [lattice-platform-agentic-development-v0.2.md](lattice-platform-agentic-development-v0.2.md) Part 13, row 11 |
| Query Execution component | Same dependency, plus a live-request-time SPARQL rewriting concern this plan does not want to solve twice | [lattice-platform-agentic-development-v0.2.md](lattice-platform-agentic-development-v0.2.md) Part 13, row 12 |
| Store-specific adapter documentation | Covered conceptually by the guide's [Chapter 26](../../architecture/rdf-sparql-patterns-guide.md#chapter-26--store-by-store) already, and concretely blocked on the SPI existing to adapt to | removed from this plan per the commissioning instruction, not rescheduled elsewhere yet |

---

## Appendix: Reference documents

- **Guide:** [rdf-sparql-patterns-guide.md](../../architecture/rdf-sparql-patterns-guide.md)
- **Sketch:** [persistence-profile-substrate.md](../sketches/persistence-profile-substrate.md)
- **ADRs:** [A78](../../architecture/decisions/ADR-A78-persistence-profile-substrate-and-aggregate-boundaries.md), [A79](../../architecture/decisions/ADR-A79-persistence-compiler-toolchain.md), [A80](../../architecture/decisions/ADR-A80-housekeeping-component-boundary.md)
- **Prior notes:** `docs/developer/notes/` (Uniqueness, Ordering, Concurrency, Combined), consolidated into the guide
- **Epic plan:** [lattice-platform-agentic-development-v0.2.md](lattice-platform-agentic-development-v0.2.md)
