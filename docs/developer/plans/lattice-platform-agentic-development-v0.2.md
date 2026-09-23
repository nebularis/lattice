# LATTICE Platform — Agentic Development Epic (v0.2, for decomposition)

**Unit type:** Epic
**Epic:** `lattice-platform-development`
**Epic status:** Decomposed into phase plans (2026-09-22). Phase 0 and Phase 1 are ready to execute at full slice detail. Phases 2–4 are rolling-wave placeholders per §0.5, expanded at P1.11.3/P2.11.4/P3.6.4 respectively.
**Epic review:** Deferred until all phase plans and acceptance tests are finalized

**Purpose of this document.** A dependency-ordered, slice-by-slice development epic that defines the scope, milestones, tracks, and hard orderings for the LATTICE platform delivery. This epic has been decomposed into individual phase plans per the Epic Decomposition model in [copilot-instructions](../../.github/copilot-instructions.md). Each plan is authored, reviewed, and accepted separately before its implementation begins. The final epic review will be created only after all phase plans are complete and their acceptance tests pass.

**Decomposition index:**

| Phase | Plan | Status | Sketch | Detail |
|---|---|---|---|---|
| 0 — Decisions and foundations | [phase-0-plan.md](phase-0-plan.md) | [phase-0-status.md](../status/phase-0-status.md) | [phase-0-sketch.md](../sketches/phase-0-sketch.md) | Full (Part 4) |
| 1 — Graph-primary core and deployment plane | [phase-1-plan.md](phase-1-plan.md) | [phase-1-status.md](../status/phase-1-status.md) | [phase-1-sketch.md](../sketches/phase-1-sketch.md) | Full (Part 5) |
| 2 — Ingestion and query planes | [phase-2-plan.md](phase-2-plan.md) | [phase-2-status.md](../status/phase-2-status.md) | [phase-2-sketch.md](../sketches/phase-2-sketch.md) | Rolling-wave (Part 6), expands at P1.11.3 |
| 3 — Operation plane | [phase-3-plan.md](phase-3-plan.md) | [phase-3-status.md](../status/phase-3-status.md) | [phase-3-sketch.md](../sketches/phase-3-sketch.md) | Rolling-wave (Part 7), expands at P2.11.4 |
| 4 — Maturity | [phase-4-plan.md](phase-4-plan.md) | [phase-4-status.md](../status/phase-4-status.md) | [phase-4-sketch.md](../sketches/phase-4-sketch.md) | Placeholder (Part 8), expands at P3.6.4 |

Each phase plan cross-references its Part below for slice-level detail rather than duplicating it, and adds the `docs/architecture`, README, and `solution-design-specification.md` obligations the epic's own slice tables name but do not tabulate.

**Governing model.** Epic decomposition, phase plans, and slice validation follow the Epic Decomposition model in [copilot-instructions](../../.github/copilot-instructions.md). See that document for the standard approach to units of work, validation packs, traceability, and review gates.

**Source of truth for scope.** `docs/architecutre/Architecture Review.md` (G-nn gaps, C-nn components, A-nn decisions), plus the three existing design documents it critiques. Every slice below carries traceability IDs back to those, recorded in `docs/traceability/matrix.csv`.

**Two structural commitments this plan makes, which you must ratify first:**

1. The review's **Addendum 1 (A74, graph-primary)** and **Addendum 2 (A75, three-tier store SPI)** are accepted. This changes Phase 0 fundamentally — it is not "add a Postgres outbox and carry on", it is "establish the graph as system of record and reduce the relational realm to a disposable coordination store". If you do *not* accept A74, stop and tell me; roughly 40% of this plan reorders.
2. **Nothing writes durable data until the Phase 0 exit gate passes.** The irreversible decisions (A82, which superseded A51, and A54, A63, A65, A67, A68, A74) shape every triple the system will ever write. We build a *walking skeleton* with volatile stores early (to unlock UI/CI infrastructure), but no persistent dataset is created until the identity, provenance, and temporal conventions are ratified and TCK-enforced.

### v0.2 topology and documentation-governance override

This v0.2 plan is amended for repository topology and implementation-document governance by [ADR-A77](../../architecture/decisions/ADR-A77-repository-topology-and-documentation-governance.md) and the [Repository Topology and Documentation Governance Plan](repository-topology-and-documentation-governance.md). Where this document's Part 1, P0.1, P0.2, P0.3, or developer-document references conflict with that decision and plan, ADR-A77 controls.

The repository retains `mise` as the sole orchestration entry point and retains Maven, Yarn 4, Python project tooling, and Mix as dependency authorities. The relocation affects semantic and documentation ownership only. It does not change ontology namespace IRIs, application names, or runtime component ownership.

Before any implementation slice in this plan begins, the `repository-topology-a77` unit must be accepted. Its current state is recorded in [Repository Topology A77 Status](../status/repository-topology-a77.md), and its human decision request is [Repository Topology A77 Review](../review/repository-topology-a77-review.md).

---

## Part 0 — Plan mechanics and validation model

### 0.1 Note: Units of work hierarchy

The hierarchy of units (Epic → Phase → Slice → Milestone) and their validation model are now defined in the [copilot-instructions Epic Decomposition section](../../.github/copilot-instructions.md). See that document for the authoritative definitions and required validation pack structure. This section retains the specific hierarchy for the LATTICE platform epic only.

**Slice sizing rule.** If a slice's Validation Pack contains more than ~15 test cases, or touches more than two modules, split it. If it contains fewer than 3, merge it. Skeleton slices are exempt (they contain 1 test: the build smokes).

### 0.2 Slice validation model

The mandatory shape of every slice, validation pack requirements, and human validation gate protocol are defined in the [copilot-instructions Epic Decomposition section](../../.github/copilot-instructions.md). See that document for the authoritative requirements.

### 0.3 Test taxonomy (referenced as L0–L8 throughout)

| Level | Name | Runs where | Introduced |
|---|---|---|---|
| **L0** | Build smoke (compiles, runs, no-op test passes) | Local + CI | P0.2 |
| **L1** | Unit / pure-function | Local + CI | P0.2 |
| **L2** | Property & determinism (same input → same digest; permutation invariance; law checks) | Local + CI | P0.4 |
| **L3** | Contract (JSON Schema validation both directions; Java↔Python cross-runtime fixtures; OpenAPI conformance) | CI | P0.2 |
| **L4** | Component integration with real infrastructure (Testcontainers: TDB2/Fuseki, broker, coordination store) | CI | P0.5 |
| **L5** | System E2E over the local compose stack via HTTP/AMQP only | CI nightly + on demand | M0 |
| **L6** | UI E2E (Playwright) against the compose stack, seeded by the synthetic data generator | CI nightly | M0 |
| **L7** | Non-functional: SLO benchmark harness, capability/benchmark report generation, load shape | CI weekly + gated releases | P0.5 |
| **L8** | Hostile / security suites: cross-tenant probe, SPARQL injection, prompt injection corpus, scoping escape (`SERVICE`/`LOAD`/`DESCRIBE`) | CI nightly | P0.5 (scoping), P2 (prompt) |

**Non-weakening rule.** No slice may delete, skip, `@Disabled`, or loosen a test from a previous slice without an ADR-grade justification recorded in the VP and countersigned at the gate.

### 0.4 Guardrails the agents must operate under (enforced, not advisory)

| # | Guardrail | Enforcement |
|---|---|---|
| G1 | No component reads or writes the RDF store except through `ScopedDataset` | ArchUnit rule + Python import lint; L8 test attempts a bypass |
| G2 | No new authoritative store. Anything persisted outside the graph realm must be annotated `@Coordination` or `@Derived` and be provably reconstructible | ArchUnit + review checklist |
| G3 | Contract-first: Java and Python wire types are **generated** from `contracts/**/*.schema.json`; hand-written duplicates are a build failure | codegen task + drift check |
| G4 | Every write carries `CommitMetadata` (cause, principal, packDigest, profileId, transactionTime, provenance scope) | SPI makes it a required constructor arg; TCK asserts rejection without it |
| G5 | No string concatenation into SPARQL; `PreparedQuery` + `Params` only | Lint + L8 injection suite |
| G6 | No `now()` inside guards, effects, or canonicalisation; time is an input | ArchUnit ban on clock access in named packages |
| G7 | Every result-returning store method returns a `Cursor`, never a materialised collection | SPI shape + review |
| G8 | Determinism: any function claiming determinism has an L2 permutation + repeat test | CI gate |
| G9 | No TODO/FIXME/`throw new UnsupportedOperationException` in merged code outside an explicitly declared "Extended-tier not implemented" pattern | Lint |
| G10 | Feature flags require an owner and expiry date; expired flags fail the build | Lint |
| G11 | Any write path governed by an `ontology/persistence` (`dal:`) profile is generated from `tools/persistence`'s `instantiate` output, never hand-constructed, even where G5's `PreparedQuery` form is used | Lint (reserved at P0.2.7); ArchUnit fixture added once the write surface exists (P0.5.2); enforced in full at P2.3.1 |

### 0.5 Rolling-wave detail

Phase 0 and Phase 1 are specified at slice granularity below and are ready to execute. Phases 2–4 are specified at slice granularity but with lighter test enumeration; each is expanded to full VP-level detail **in the last two slices of the preceding phase** (an explicit planning slice). This is deliberate: Phase 2's ingestion design will be better informed by what Phase 1 learns about the store SPI.

---

## Part 1 — Target module topology

Agreeing this early prevents the agents from inventing five layouts.

```
contracts/                     # normative JSON Schema + OpenAPI; source of all generated types
  events/ ontology/surface/ mork/ pack/ plan/ projection/ query/ lineage/ openapi/
ontology/                      # existing layers, unchanged in role
  ontology/foundation/ ontology/vocabulary/ ontology/quantification/ ontology/party/ ontology/eligibility/ ontology/instrument/ ontology/behaviour/
  platform/                    # NEW: lattice: namespace (authority, commitSeq, lifecycle, provenance)
  ontology/governance/shapes/           # NEW content: authority + provenance governance shapes
mork/
platform/
  lattice-bom/
  canonical-hash/              # C-11  (+ CLI)
  graph-spi/                   # A75 Core + Extended interfaces, Capabilities, CommitMetadata
  graph-spi-tck/               # conformance + benchmark kit
  graph-adapter-tdb2/          # reference, in-process
  graph-adapter-fuseki/        # reference, remote
  coordination-spi/            # leases, sequences, idempotency, counters, outbox
  coordination-h2/             # embedded default (single node, no Postgres)
  coordination-postgres/       # multi-node option
  semantic-policy/             # existing; extended Principal (A66)
  platform-outbox/             # existing; re-based on commit-marker + coordination
  partitioned-queue-spi/       # A59 abstraction
  partitioned-queue-rabbit/  partitioned-queue-pg/
  surface-workflow/            # existing; re-based graph-primary
  release-integration/         # existing; ledger → graph
  mork-review/                 # snapshots + decision nodes (graph)
  governance-ledger/           # graph, hash-chained
  tenancy/                     # C-17
  pack-builder/                # C-01
  activation-controller/        # C-02
  change-feed/                 # C-08
  reasoning-validation/        # C-13
  plan-ir/                     # shared IR types (C-04/C-05 boundary)
  ingestion-gateway/           # C-04
  query-plane/                 # C-12
  lineage/                     # C-19
  metering/                    # C-16
  push-gateway/                # C-18
  feedback-router/             # C-15
  projection-engine/           # C-07 (+ sink adapters)
  behaviour-engine/            # C-09
  writeback/                   # C-10
  runtime-host/                # single artifact, LATTICE_ROLE=control|edge|projection|behaviour
  testkit/                     # harnesses, fixtures, compose orchestration helpers
  synth/                       # synthetic data generator (CLI)
workers/                       # Python
  lattice_workers/             # existing
  mapping_plan_compiler/       # C-05 design-time
  content_pipeline/            # C-06
  agent_orchestrator/          # C-14
apps/
  surface-studio/ mork-bench/ ops-console/
packages/
  ui-kit/ client-ts/
clients/
  client-java/ client-python/
deployment/
  compose/ images/ seeds/
docs/
  architecture/decisions/ (ADRs, canonical location per copilot-instructions — never `docs/adr/`)
  developer/{sketches,plans,status,validation,review}/ (per-unit documentation lifecycle)
  traceability/ (existing)
  operator/ (existing — runbooks referenced from P3.5.3 etc. land here unless a phase plan says otherwise)
```

---

## Part 2 — Epic map and dependency DAG

| Epic | Owns | Primary components |
|---|---|---|
| **T-DEC** | ADRs, normative doc rewrites | A44–A75 |
| **T-BUILD** | Repo, build, CI, codegen, compose, DevEx | — |
| **T-ONT** | Platform ontology, governance shapes, lifecycle vocabulary | G-34, A74 vocab |
| **T-HASH** | Canonicalisation & hash identity | C-11 |
| **T-STORE** | Graph SPI, TCK, adapters, coordination realm | C-03, A75 |
| **T-ID** | Principal, policy, graph visibility, OIDC | A66, C-17 partly |
| **T-HOST** | HTTP runtime, role profiles, deadlines, push | A44, A50, C-18 |
| **T-MSG** | Outbox, topology, partitioned queues, schema governance | A57, A59, G-17 |
| **T-GPM** | Graph-primary migration of existing relational entities | A74 / A1.4 |
| **T-DEP** | Pack, activation, tenancy, change feed | C-01, C-02, C-08, C-17 |
| **T-ING** | Plan compiler, ingestion gateway, content pipeline, agents | C-04, C-05, C-06, C-14 |
| **T-QRY** | Query/decision/explain, lineage, metering | C-12, C-19, C-16 |
| **T-RUN** | Projection engine, behaviour engine, write-back, reasoning | C-07, C-09, C-10, C-13 |
| **T-FB** | Runtime feedback, drift | C-15 |
| **T-UX** | UI kit, SDKs, Studio/Bench/Ops surfaces, Playwright | C-20, Part 6 |
| **T-DATA** | Synthetic data, fixture corpora, cassettes, golden files | testkit/synth |
| **T-SEC** | Threat model, hostile suites, PII strategy | §5.7 |

### Dependency DAG (coarse)

```
T-DEC ──► T-ONT ──┐
   │              ├──► T-HASH ──► T-STORE ──► T-GPM ──► T-DEP ──► T-ING ──► T-RUN
   ├──► T-BUILD ──┤                  │           │         │         │
   │              └──► T-ID ──► T-HOST ──► T-UX   │         ├──► T-QRY┤
   └──► T-MSG ──────────────────────────────────► │         └──► T-FB ┘
        T-DATA ──► (feeds every integration level from M0 onward)
        T-SEC  ──► (adds L8 suites from P0.5 onward, never a trailing phase)
```

**Hard orderings you cannot violate:**

- `T-HASH` before `T-STORE` write paths (hashes are in `CommitMetadata` and in revision IRIs).
- `T-ONT` platform vocabulary before `T-GPM` (the graph form of a revision needs terms to exist).
- `T-STORE` Core tier + TCK before any durable write anywhere.
- `C-08` change feed before `C-07`; `C-07` reconciling cleanly before `C-09` (review §9: a behaviour engine over a silently-corrupt projection is the worst failure mode).
- `C-05` before `C-04` runtime interpretation and before `C-06` stage 6.
- `C-19` provenance conventions before *any* durable A-Box write (A65).
- `C-11` before pack determinism, idempotency digests, projection invalidation.

---

## Part 3 — Milestones

| ID | Milestone | Phase | Demonstrable outcome | Test levels |
|---|---|---|---|---|
| **M0** | Walking skeleton | P0 | Compose stack up; Studio (browser) → control-plane HTTP → in-memory domain → response rendered; correlation ID traceable through logs; Playwright smoke passes | L5, L6 |
| **M1** | Store conformance | P0 | `semantic-dataset-tck` produces a signed capability + benchmark report for TDB2 in-process and Fuseki remote; hostile scoping suite passes | L4, L7, L8 |
| **M2** | Graph-primary lifecycle | P1 | A Surface revision is authored, reviewed, approved entirely in the graph; version chain is the history; `fnd:hasGovernanceState` is real; no relational ledger exists | L4, L5, L6 |
| **M3** | Pack + activation | P1 | Approved ontology + mappings → signed pack → activated into tenant/env with diff, SHADOW divergence report, promote, rollback; Activation Console drives it | L5, L6 |
| **M4** | Ingestion | P2 | Deterministic mapping plan compiled at design time; JSON payload lands in the A-Box through staging + admission; a bad payload quarantines and routes an open question; replay-by-digest fixes it after a steward teaches a synonym | L4, L5, L6, L8 |
| **M5** | Query + lineage | P2 | Typed read, governed SPARQL, and a Decision/Explain call answering a capacity question with witness/challenge; lineage from a value back to the source JSON pointer / PDF span | L5, L6, L7 |
| **M6** | Content pipeline | P2 | A generated contract PDF is extracted to Intent, aligned, staged, gated, and committed; Intent Bench API structurally cannot carry an ontology IRI; prompt-injection corpus defeated | L4, L6, L8 |
| **M7** | Projections live | P3 | Capacity projection maintained incrementally within its declared freshness contract; scheduled reconciliation detects an injected divergence | L4, L5, L7 |
| **M8** | Tanks respond | P3 | Claim sequence drives tank decrements as new versions; authored contract value unchanged; deterministic replay reproduces the runtime state hash; Tank Inspector shows not-fired transitions with reasons | L5, L6, L7 |
| **M9** | Write-back | P3 | A fund-tracked value written in the capacity layer lands in the contract-layer A-Box as a new version with evidence; lens laws discharged at pack build; loop cap proven | L4, L5, L6 |

---

## Part 4 — PHASE 0: Decisions and non-retrofittable foundations

**Decomposed into** [phase-0-plan.md](phase-0-plan.md) / [phase-0-status.md](../status/phase-0-status.md) / [phase-0-sketch.md](../sketches/phase-0-sketch.md). This Part remains the authoritative slice-level detail the phase plan references; it is not duplicated there.

**Phase goal.** Make every irreversible decision, ratify it as an ADR, encode it as a machine-checked invariant, and stand up the build/test/deploy machinery — while proving the whole chain works end to end on a volatile stack (M0).

**Phase exit gate (hard).** No slice in Phase 1+ starts until: all Phase 0 ADRs are ratified; M0 and M1 pass; `docs/traceability/matrix.csv` has zero untested claimed requirements; `data-architecture.md` has been rewritten for A74 and signed off.

> **Persistence-pattern coherence (optional, non-blocking — completes the "Phase 0.2–0.4 Integration" item from [COORDINATION_REORG_HANDOFF.md](../COORDINATION_REORG_HANDOFF.md)).** `ontology/persistence` and `tools/persistence` (Slice 2 of `rdf-sparql-patterns-phase`, already complete) formalise the same K/O/C/T patterns this phase's foundations independently establish under different names. Phase 0 does **not** depend on `tools/persistence` — the compiler is Phase 2 machinery, and nothing in P0.1–P0.9 requires it to exist — but the vocabulary and primitives minted here should be nameable in `dal:` terms from day one, so Phase 1–2 never has to reconcile two competing stories for the same concept. Concretely:
>
> - **Pattern C (CAS)** ↔ `dal:ConcurrencyProfile`/`dal:ConcurrencyStrategy` (`dal:ProvidedConcurrency`, `dal:Optimistic`, `dal:AppendOnly`, `dal:LockingConcurrency`). The SPI's own `conditionalWrite(Precondition, WriteUnit)` and `WriteResult.guardSatisfied` (P0.5.2, TCK at P0.5.6) **is** the mechanism `dal:Optimistic` ultimately compiles to — cross-referenced below so nothing needs renaming when Phase 2 wires the compiler to it.
> - **Pattern T (named-graph-per-batch / provenance)** ↔ `dal:MetaTopologyProfile` (`dal:SharedSharded`, `dal:PerAggregate`) and `dal:ReceiptModel` (`dal:ReceiptOnly`, `dal:PatchLog`, `dal:SnapshotPerRevision`). ADR-A65's provenance-homogeneous, one-cause-per-graph convention (P0.1.5, shaped at P0.3.6) is the same idea `dal:`'s meta-topology and receipt-model dimensions assume — cross-referenced below so a future `dal:` value never silently contradicts A65.
> - **Pattern K (uniqueness)** ↔ `dal:UniquenessConstraint` (`dal:keyProperty`, `dal:scopeProperty`, `dal:normalizePipeline`, `dal:onViolation`, `dal:minEnforcementLevel`). [IRI and Identity Patterns](../../architecture/iri-identity-patterns.md) and ADR-A82 make the selected minting and claim strategy explicit per resource role. A profile can require structural derivation, a claim registry, or an external allocator, rather than assuming one Core-tier identity policy everywhere.
> - **Pattern O (dense ordering)** ↔ `dal:OrderingProfile`/`dal:OrderingGrain` (`dal:CommitGrain`, `dal:EventGrain`) and `dal:DatasetTierModel`. The `CommitSequence` primitive and its TCK ordering suite (P0.5.7), and the canonicalisation profile's ordered-collection indexing (P0.4.4), are cross-referenced below against the matching `dal:` terms.
>
> A new slice, **P0.3.9**, produces the single artefact proving these four alignments hold: a mapping table, not new code. This closes the handoff's optional item by adding documentation cross-references and one new guardrail (**G11**, §0.4) — it introduces no new Phase 0 dependency or scope beyond that.

### P0.1 — Decision pack (T-DEC)

Decisions are *slices* here, because agents can draft ADRs and humans validate them. Each slice = draft ADR + affected normative doc edits + (where applicable) an executable consequence.

| Slice | Deliverable | Human validation focus | Executable consequence in later slice |
|---|---|---|---|
| **P0.1.1** | ADR-A74 graph-primary realm model; full rewrite of `data-architecture.md` §1–§3, §5–§7 | Is the "where does a fact belong" test (A1.2) applied correctly to every existing table in A1.4? Is anything mis-assigned? | ArchUnit G2 |
| **P0.1.2** | ADR-A75 three-tier store SPI; Core/Extended/Native split; capability list | Is every Extended capability paired with a Core fallback *or* an activation gate? | TCK (P0.5) |
| **P0.1.3** | ADR-A82 framework-neutral identity-pattern selection + `docs/architecture/iri-identity-patterns.md`. Covers adopter-selected entity, aggregate, component, lineage, revision, graph-locator, claim, and event patterns, and defines the future `ontology/persistence` identity-profile extension. | Does each selected pattern have explicit derivation bytes, privacy, concurrency, lifecycle, and restore behavior? Can tooling refuse incompatible selections? | P0.4 + P1.2 tests |
| **P0.1.4** | ADR-A54 dataset topology + named-graph layout convention | Dataset-per-tenant default agreed? Graph name grammar complete for every family we will ever write? | Graph-name validator (P0.3) |
| **P0.1.5** | ADR-A65 provenance: named-graph-per-batch, provenance-homogeneous batches, `ProvenanceAssertion` opt-in. Cross-references `dal:MetaTopologyProfile`/`dal:ReceiptModel` (Pattern T): the meta-topology and receipt-model dimensions `ontology/persistence` later resolves per target assume exactly this graph-per-batch convention, not a competing one | Is "one cause per graph" achievable for every write in the T1–T12 catalogue? | `CommitMetadata` required (P0.5) |
| **P0.1.6** | ADR-A67 bi-temporal: valid time via `fnd:TemporalScope`, `lattice:transactionTime` per assertion graph, two-path query design | Is the materialised-current / analytic-as-of split acceptable, with its SLO consequences? | P2 query tests |
| **P0.1.7** | ADR-A68 PII & erasure: per-subject graphs, erasure as drop + tombstone, pseudonymous ledger refs | Legal/DPO review recommended here, not later | P0.3 shapes; P1.7 tenancy |
| **P0.1.8** | ADR-A63 `projectId` vs `environmentId`; `AuthoredGraphReference` / `RuntimeGraphReference` | Does the vendor-ships-pack-to-customer case work? | Types in P0.5 |
| **P0.1.9** | ADR-A48 (replace) transaction boundary catalogue T1–T12; "no unprotected dual write"; "every saga has a named reaper"; edits to `solution-design-specification.md §7` | Is any operation in the system missing from the catalogue? Does each saga have a named reaper and detector? | Reaper registry test (P1.x) |
| **P0.1.10** | ADR-A50 role-profiled deployment (`control`/`edge`/`projection`/`behaviour`); ADR-A44 amended (virtual threads, minimal server, deadline propagation, generated types) | Is the role split right, and is the deadline object mandatory in every downstream call? | P0.7 host |
| **P0.1.11** | ADR-A57 change feed via write-side emission + reconciliation; direct store access banned (new `data-architecture` rule 8) | Is the reconciliation safety net specified concretely enough to build? | G1 enforcement |
| **P0.1.12** | ADR-A59 `PartitionedWorkQueue` abstraction + phase-1 impl choice; ADR-A66 principal model; ADR-A71 platform licence MPL-2.0 + SPI seam; ADR-A62 SPC namespace harmonisation (execute the one-line namespace change now) | Abstraction shape before impl choice; licence headers enforced | P0.6, P0.8 |
| **P0.1.13** | ADR-A69 pack trust model + safe SPARQL subset (no `SERVICE`, `LOAD`, writes outside declared targets) | Is the safe subset statically checkable? | Pack lint (P1.8), L8 |
| **P0.1.14** | Threat model document (S-1…S-12) with owner per control; hostile-suite backlog | Is any control listed that has no test owner? | L8 suites |
| **P0.1.15** | NFR/SLO catalogue + reference load profile (§5.4) committed as `docs/architecture/nfr.md`, machine-readable `nfr.yaml` | Are the numbers ones you are willing to be held to? They drive store choice and partition counts | L7 harness reads `nfr.yaml` |

> **Validation note for the humans:** P0.1 slices produce *documents*, so Step 4 (adversarial probe) becomes "name one scenario the decision does not cover". Expect to reject and re-run at least P0.1.1 and P0.1.3.

### P0.2 — Repo, build, CI, codegen (T-BUILD)

| Slice | Scope | Tests / validation |
|---|---|---|
| **P0.2.1** | Multi-module build skeleton per Part 1 (Maven or Gradle — decide in this slice, record as ADR-A76); BOM; Java 21 toolchain; one no-op test per module; new `mise.toml` tasks `verify`, `verify-slice`, `up`, `seed`, `e2e` (per the existing toolchain rule — `mise` is the sole task-orchestration entry point, ADR-A29 not superseded; no `make`/`just` layer) | **L0**: clean build from scratch on a clean container; every module has a passing no-op test; task runner discoverable via `mise tasks` |
| **P0.2.2** | Python workspace: uv/poetry lock, `pytest`, `ruff`, `mypy` strict on new packages; no-op test | **L0** |
| **P0.2.3** | Frontend workspace: pnpm workspace, `packages/ui-kit` + `packages/client-ts` + three app shells; Vitest + Playwright installed; no-op tests | **L0** |
| **P0.2.4** | **Contract codegen pipeline** (G3): JSON Schema → Java records (Jackson) + Python pydantic + TS types; OpenAPI → server route stubs + TS client; drift check task that fails if generated code is stale or hand-edited | **L3**: round-trip a fixture through Java→JSON→Python→JSON→Java, byte-identical; drift check fails on a deliberately edited generated file |
| **P0.2.5** | **Cross-runtime contract test harness**: Java produces fixture corpus to `contracts/fixtures/`, Python validates and vice versa, per event/message type; wired as a CI job | **L3**: at least one existing event type (surface job request/result) proven both directions; a deliberately incompatible field addition fails |
| **P0.2.6** | **Schema governance CI** (G-17): `specversion`/`dataschema` required; backward-compat schema diff gate (additive optional only within a major); enum-removal and required-field-addition rejected | **L3**: a breaking schema edit fails CI with a named reason; an additive optional field passes |
| **P0.2.7** | **ArchUnit + lint guardrail suite** (G1, G2, G5, G6, G7, G9, G10, **G11 reserved**) and Python equivalents; `reuse lint` licence headers incl. new MPL-2.0 platform code | **L1**: each guardrail has a positive fixture (allowed) and a violating fixture (build fails). This is the slice that makes guardrails real — validate it hard. G11's own fixture pair lands once the write surface exists (P0.5.2); this slice only reserves its lint category |
| **P0.2.8** | Traceability tooling: `matrix.csv` schema, CI check that every requirement claimed in a VP has ≥1 test ID that exists and ran; coverage report of G-nn/C-nn/A-nn | **L1**: a VP claiming an untested requirement fails CI |
| **P0.2.9** | Observability skeleton: structured JSON logging, `correlationId` MDC propagation (HTTP→outbox→broker→worker→result), OpenTelemetry trace context, `/healthz` `/readyz` conventions as a shared library | **L4**: one correlation ID greps a full synthetic request lifecycle across Java and Python logs |

### P0.3 — Platform ontology & governance shapes (T-ONT)

| Slice | Scope | Tests / validation |
|---|---|---|
| **P0.3.1** | Declare `fnd:GovernanceState` individuals (`Draft`/`Reviewed`/`Active`/`Superseded`) in `ontology/foundation/vocab/foundation-vocab.ttl` + `shapes/constraints.ttl` `sh:in`; closes G-34 part 1 | **L1**: SHACL rejects an unknown governance state; Vocabulary's worked example no longer forward-references |
| **P0.3.2** | Run **every** existing compiled `.ttl` through Jena `riot` + SHACL in CI (the long-outstanding validation step from `ontology-architecture §11.3`) | **L1**: parser gate on all layers; a deliberately malformed fixture fails |
| **P0.3.3** | `ontology/platform/` literate spec + `spec/platform.ttl`: `lattice:authority` (5 values), `lattice:commitSeq`, `lattice:transactionTime`, `lattice:ProvenanceScope`, `lattice:cause`, `lattice:packDigest`, `lattice:generationProfileId`, `lattice:derivedFrom` alignment to `fnd:derivedFrom`, `lattice:writeBackState`, `lattice:version`, `lattice:lifecycleState` | **L1**: parses; SHACL self-tests; DL encoding documented per repo convention (turtle-spec fences) |
| **P0.3.4** | **Platform lifecycle → `fnd:GovernanceState` mapping** (G-34 part 2): normative table + shapes asserting a released Surface contract graph carries `fnd:hasGovernanceState fnd:Active` | **L1**: every platform state maps; an unmapped state fails the shape |
| **P0.3.5** | `ontology/governance/shapes/authority.ttl`: any graph containing inferred/materialised triples without an authority annotation + `fnd:derivedFrom` + `(semanticHash, profileId)` is a governance failure (G-28, §4.13) | **L1**: positive/negative graph fixtures |
| **P0.3.6** | `ontology/governance/shapes/provenance.ttl`: every assertion graph has exactly one `ProvenanceScope` with one `cause` (provenance homogeneity, A65); `lattice:transactionTime` present (A67). Cross-references `ontology/persistence`'s `dal:MetaTopology`/`dal:ReceiptModel` values (Pattern T) — same graph-per-batch convention, different vocabulary for a different purpose (aggregate conflict detection vs. audit) | **L1**: multi-cause graph rejected |
| **P0.3.7** | **Graph-name validator** library + grammar tests for the A54 layout convention (`urn:lattice:{tenant}:{env}:...`), including the lineage/revision/alias forms of the identity profile selected under A82 ([iri-identity-patterns.md](../../architecture/iri-identity-patterns.md); A51, which first defined them, is superseded). Also validates that `dal:graphIriTemplate`/`dal:graphPrefix` values (used by `ontology/persistence`'s `GraphPatternScope`/`NamedGraphBoundary`) are well-formed instances of this same grammar, not a second one | **L1/L2**: grammar accepts the full family table, rejects malformed, round-trips parse/format; a `dal:graphIriTemplate` fixture from the Slice 2 examples round-trips through this grammar |
| **P0.3.8** | PII data-model shapes (A68): per-subject graph convention, tombstone form, ledger pseudonymity constraint | **L1**: a ledger fixture containing personal data fails |
| **P0.3.9** | **`dal:` vocabulary alignment note** (`ontology/persistence/docs/platform-vocabulary-alignment.md`): a mapping table from each `dal:` dimension (the original six: aggregate boundary, concurrency, ordering, receipt model, meta topology, uniqueness; plus the identity, epoch and privacy profiles and the extension properties added to `ontology/persistence` on 2026-09-23) to the platform/governance terms defined in P0.3.3–P0.3.6, proving zero namespace or semantic collision. Documentation only — introduces no code and no Phase 0→Phase 2 dependency | **L1**: every `dal:` term referenced in the P0.1.3/P0.1.5/P0.3.6/P0.3.7/P0.4.4/P0.5.2/P0.5.6/P0.5.7 cross-references resolves in `ontology/persistence/spec/persistence.ttl`; a markdown-link check on the new document passes |

### P0.4 — Canonicalisation & hash identity, C-11 (T-HASH)

This is the single most load-bearing library in the system. Slice it finely.

| Slice | Scope | Tests / validation |
|---|---|---|
| **P0.4.1** | Module skeleton + `CanonicalisationProfile` schema (`contracts/hash/canonicalisation-profile.schema.json`) + typed `SemanticHash(profileVersion, digest)` where equality requires both | **L0/L1**: two hashes with different profile versions are not equal and cannot be compared (compile-time or typed failure) |
| **P0.4.2** | Steps 1–3: RDFC-1.0 blank-node canonicalisation (delegate to Jena where available, wrap behind an interface), N-Quads byte ordering, literal normalisation | **L2**: `"1.0"^^decimal ≡ "1.00"^^decimal`; `xsd:string` datatype dropped; language tags lowercased; permuted input order → identical digest; blank-node relabelling → identical digest |
| **P0.4.3** | Steps 4–5: annotation stripping by profile (`rdfs:comment`, `fnd:utility`, editorial provenance); `owl:imports` pinning to `(lineage, semanticHash)` pairs | **L2**: editing a `rdfs:comment` does not change the hash; changing an imported graph's hash *does* |
| **P0.4.4** | Steps 6–9: wildcard elision with `elg:Unsourced` retained; optional-value normalisation; ordered-collection indexing; legacy IRI override application. Ordered-collection indexing follows the same dense-position convention as `dal:OrderingGrain` (Pattern O: `dal:CommitGrain`/`dal:EventGrain`), so a canonicalised ordered collection and a `dal:`-profiled event sequence share one indexing scheme, not two | **L2**: adding an unused dimension leaves an existing profile's hash unchanged (the payoff test — mark it as a headline case in the VP); `elg:Unsourced` changes the hash; a deployment-specific IRI rebinding does not |
| **P0.4.5** | `generationProfileId`, `artefactHash`, `runtimeStateHash(state, projection)` with declared exclusions (wall clock, storage addresses) | **L2**: excluded fields do not affect the hash; queue order and final state *do* |
| **P0.4.6** | `explain()` → `CanonicalisationTrace` (which normalisations fired) + CLI (`lattice-hash canonicalise|hash|explain`) | **L1**: trace names each firing step; CLI golden-file output for a fixture corpus |
| **P0.4.7** | Cost controls: cache by `(inputByteDigest, profileVersion)` behind a `HashCache` port; blank-node ceiling (default 10 000) with a diagnostic naming the offending structure; per-named-graph only | **L2/L7**: ceiling breach produces the named diagnostic, not an OOM; benchmark: throughput on the fixture corpus recorded as a baseline |
| **P0.4.8** | Profile-version migration story: `rehash` CLI, profile-change = `breaking` classification hook | **L1**: a profile change produces a rehash plan listing affected graphs (against fixtures) |

> **Human validation focus for P0.4:** ask the agent to produce a table of "these two graphs are semantically identical and hash equal" vs "these two look similar but must hash differently". If that table is thin, the suite is thin.

### P0.5 — Graph store SPI, TCK, adapters, C-03/A75 (T-STORE)

| Slice | Scope | Tests / validation |
|---|---|---|
| **P0.5.1** | `graph-spi` skeleton: `GraphBackend`, `DatasetHandle`, `ScopedDataset` Core read surface (`prepare/select/construct/ask/getGraph/catalogue`), `Cursor`, `ReadOptions(Deadline, Consistency, regime, maxRows, maxBytes)`, `Capabilities` record | **L0/L1**: interface compiles; no method returns a materialised unbounded collection (ArchUnit); `ReadOptions` without a deadline is unconstructable |
| **P0.5.2** | Core write surface: `WriteUnit`, `CommitMetadata` (mandatory), `apply`, `conditionalWrite(Precondition, WriteUnit)`, `putGraph`, `dropGraph(DropPolicy)`, `WriteResult(CommitSequence, transactionTime, guardSatisfied, stats)`. `conditionalWrite`'s `Precondition`/`guardSatisfied` is the mechanism `dal:ConcurrencyStrategy` values (`dal:Optimistic`, `dal:ProvidedConcurrency`) compile to (Pattern C) — the persistence compiler (Phase 2) targets this primitive directly, not a parallel one | **L1**: a `WriteUnit` without `CommitMetadata` does not compile/constructs to failure; `guardSatisfied=false` leaves the dataset byte-identical |
| **P0.5.3** | **TDB2 in-process adapter**, Core tier only | **L4**: Core semantics suite (below) passes |
| **P0.5.4** | **TCK: semantics suite** — SPARQL 1.1 Query/Update subset actually used; GSP round-trip; N-Quads round-trip with blank-node preservation; datatype canonical forms | **L4**: suite runs against an adapter by SPI; a deliberately broken adapter stub fails named tests |
| **P0.5.5** | **TCK: atomicity suite** — single-request Update atomicity under injected failure; guarded-write correctness; `putGraph` idempotency by revision IRI | **L4**: injected failure mid-unit leaves no partial state |
| **P0.5.6** | **TCK: concurrency suite** (R-14) — N concurrent `conditionalWrite`s on one subject yield exactly one winner, N−1 clean conflicts; lost-update probe. Exercises the same primitive `dal:Optimistic` resolves to (P0.5.2); no separate concurrency mechanism is introduced for `dal:`-profiled writes | **L4**: run at N=32 with repeat count; flakiness is a failure, not a retry |
| **P0.5.7** | **`CommitSequence`** primitive (A1.5 rule 3): store-native where available, coordination fallback; written as `lattice:commitSeq` on every assertion graph; **TCK: ordering suite** (monotonicity under concurrent commits). `dal:OrderingGrain` (`dal:CommitGrain`/`dal:EventGrain`) and `dal:DatasetTierModel` (Pattern O) are defined against this exact primitive — a `dal:`-profiled target's ordering dimension resolves to `CommitSequence`, never a second ordering mechanism | **L4**: no two commits share a sequence; replay ordered by sequence never uses wall clock |
| **P0.5.8** | **`Principal` scoping at `scope()`** + gateway-constructed graph visibility; **TCK: scoping / hostile suite** (L8): a `ScopedDataset` cannot read or write outside its visibility set via `SERVICE`, `LOAD`, `DESCRIBE`, federated forms, or `GRAPH ?g` enumeration | **L8**: each escape vector is a named failing-then-passing test. This is the cross-tenant leakage control (S-3, R-08) — validate adversarially |
| **P0.5.9** | `PreparedQuery` + `Params` with plan cache keyed by query digest; complexity pre-check (no unbounded property paths, `OPTIONAL` depth ≤2, no cross products over unbound subjects) | **L1/L8**: injection attempts through `Params` are inert; a non-conforming platform-authored query fails CI (rule 7 of A2.5) |
| **P0.5.10** | Extended tier interfaces + capability gating: `TransactionalDataset`, `ChangeFeedSource`, `BulkLoader`, `ShaclEngine`, `ReasoningEngine`, `TextIndex`, `VectorIndex`, `SnapshotSupport`; `Capabilities` probe at bind | **L1/L4**: calling an unsupported Extended interface yields a typed `CapabilityUnavailable`, never a runtime cast failure |
| **P0.5.11** | TDB2 Extended implementations: multi-request txn, MVCC observation, journal-derived change feed, native-ish SHACL via Jena, bulk load, snapshot/restore | **L4**: Extended suites (isolation probes for read-skew/write-skew; snapshot/restore round-trip with digest verification) |
| **P0.5.12** | **Fuseki remote adapter** (Core + declared Extended subset) + capability report showing the *difference* from in-process | **L4**: identical TCK run, different capability report; a pack requiring an absent capability is refusable (asserted in P1.9) |
| **P0.5.13** | **Capability report format** (signed, versioned, machine-readable) + publication task | **L3**: report validates against schema; consumed by a stub activation validator |
| **P0.5.14** | **TCK benchmark suite** (L7) reading `nfr.yaml`: typed read, decision-shaped query, single-record ingest write unit, incremental key-batch update, bulk load rate, canonicalisation throughput; result appended to the capability report | **L7**: baseline numbers recorded for both adapters; regression threshold configured |
| **P0.5.15** | Connection/session pooling with per-tenant fairness at the SPI (A2.5 rule 10) | **L4**: one tenant's long analytic query cannot starve another's short write (measured) |

### P0.6 — Coordination realm (T-STORE)

| Slice | Scope | Tests |
|---|---|---|
| **P0.6.1** | `coordination-spi`: `Lease`, `Sequence`, `IdempotencyKeys(ttl)`, `Counter`, `Outbox`, `Mutex`; explicit "never authoritative, must be reconstructible or safely lossy" contract in Javadoc + ArchUnit tag | **L1**: interface + a conformance kit (`coordination-tck`) |
| **P0.6.2** | `coordination-h2` embedded default (single-node, no Postgres) | **L4**: coordination TCK passes; lease expiry and fencing tokens correct under clock skew injection |
| **P0.6.3** | `coordination-postgres` adapter + relay leadership via advisory lock, held per shard (G-25) | **L4**: two relay instances → exactly one publishes; lock loss mid-batch does not double-publish (idempotency proven) |
| **P0.6.4** | Reconstruction proof: drop the entire coordination store, restart, system converges (leases re-acquired, idempotency window lost but safe, queue projections rebuilt) | **L5**: documented as a runbook + automated chaos test. This is the slice that proves A74's central claim — validate it personally |

### P0.7 — Identity, policy, HTTP host, walking skeleton (T-ID, T-HOST) → **M0**

| Slice | Scope | Tests |
|---|---|---|
| **P0.7.1** | Extended `Principal` (A66): kind human/service/agent, organisation/tenant, scope{projects, environments}, scoped roles, `graphVisibility` (derived, never client-supplied), entitlements, delegation chain, deadline, correlationId | **L1**: a `Principal` constructed from a client-supplied `graphVisibility` is rejected; role sets for service vs human principals are disjoint (typed) |
| **P0.7.2** | OIDC token verifier (JWKS, issuer, expiry, clock skew) + claim→Principal mapping; dev issuer for local stack | **L1/L4**: forged signature, wrong issuer, expired, `alg=none`, missing tenant claim — each rejected with distinct diagnostics |
| **P0.7.3** | `runtime-host` skeleton: minimal HTTP server (per amended A44), virtual-thread-per-request, `LATTICE_ROLE` router mounting, Jackson at the edge only, JSON Schema validation from `contracts/`, `Deadline` in the call context propagated to every downstream call, `/healthz` `/readyz` | **L0/L4**: a request with an expired deadline is refused downstream, not executed; role profile mounts only its routes (asserted per role) |
| **P0.7.4** | Error contract: `400/401/403/404/409/413/422/429/503` semantics, machine-readable problem details, `IllegalArgument/IllegalState` translation (extend the `SurfaceRevisionApi` pattern) | **L3**: every status has a fixture and an OpenAPI-documented shape |
| **P0.7.5** | **Walking-skeleton vertical**: wire existing in-memory `SurfaceRevisionApi` behind HTTP; Studio calls it (real fetch, not fixture); one create + one transition + one 409 path | **L5**: E2E over HTTP; **L6**: Playwright renders the created revision and the conflict banner |
| **P0.7.6** | Compose stack v1 (`deployment/compose`, the existing repo-root name — see Part 1): control-plane image, Fuseki, broker, coordination (H2 file), dev OIDC, static app hosting; `mise run up` / `mise run down` / `mise run logs` | **L5**: cold start to green healthchecks under a stated time budget; readiness reflects dependency reachability |
| **P0.7.7** | Playwright harness: base config, auth helper (dev token), page objects, axe accessibility check wired, trace/screenshot artifacts on failure | **L6**: smoke suite green; a deliberately broken selector fails with a useful artifact |

> **M0 gate.** Browser → HTTP → domain → response, in compose, with one correlation ID traceable across services, plus a Playwright + axe smoke. Explicitly *no durable data*.

### P0.8 — Messaging foundations (T-MSG)

| Slice | Scope | Tests |
|---|---|---|
| **P0.8.1** | `partitioned-queue-spi` (A59): `PartitionedWorkQueue` with declared `orderingClass ∈ {none, per-key, global}` and named partition key; ordering class is a required declaration per family | **L1**: a family declaring `per-key` without a key fails at wiring time |
| **P0.8.2** | RabbitMQ impl: existing topology plus the extended family table (§5.3) incl. ordering classes, priority classes, separate pools/connections for runtime vs maintenance families | **L4**: per-key ordering held under concurrent producers; maintenance flood does not starve a runtime family (measured) |
| **P0.8.3** | Alternative impl: PostgreSQL `FOR UPDATE SKIP LOCKED` per key (kept behind the SPI so A59's choice stays a config change) | **L4**: same ordering suite passes against both impls |
| **P0.8.4** | Poison-message policy per family: dead-letter-and-wait for design-time families; **block-partition-and-page** for strict per-key families | **L4**: a poison message on a strict family blocks its partition and raises the alert, and does **not** skip |
| **P0.8.5** | Durable outbox via commit-marker technique (A1.5 rule 4 form (a)): intent written inside the single-request graph update with `lattice:publishPending`, relay claims by commit sequence, publishes, clears idempotently; plus coordination-outbox form (b) | **L4**: broker down → nothing lost, nothing published that was not committed; relay restart mid-publish → no duplicate side effects (idempotent consumer proven) |
| **P0.8.6** | Retry budgets per family; result-event correlation; the four missing failure modes from G-25 given tests: result lost, result applied twice with different content, two relays, clock skew vs `recordedAt` ordering | **L4**: each of the four has a named test proving the designed containment |

### P0.9 — Synthetic data and test data foundations (T-DATA)

| Slice | Scope | Tests |
|---|---|---|
| **P0.9.1** | `synth` CLI skeleton: deterministic seeded generator, output manifest with digests, `--seed` reproducibility | **L2**: same seed → byte-identical output; different seed → different but schema-valid |
| **P0.9.2** | Ontology/contract fixtures: a demo applied ontology derived from `ontology/examples/insure-o`, Surface Promotion/Index/Projection contracts, Eligibility profiles, Behaviour declarations incl. a capacity-tank aggregate | **L1**: all generated TTL parses and passes layer shapes |
| **P0.9.3** | Golden-file infrastructure: expected semantic hashes, expected canonical forms, expected pack digests, with an approved-diff workflow (`mise run approve-goldens`) | **L2**: golden drift fails with a readable diff; approval requires an explicit command (never automatic) |
| **P0.9.4** | Fixture corpora for the hostile suites: malformed graphs, adversarial blank-node structures, oversized payloads, injection strings | **L8** inputs |
| **P0.9.5** | Seeding API/CLI for the compose stack (`mise run seed SCENARIO=...`), idempotent, digest-verified | **L5/L6**: UI tests can assume a named scenario; re-seeding is a no-op |

### P0.10 — Phase 1 planning slices

| Slice | Scope |
|---|---|
| **P0.10.1** | Expand Phase 1 to VP-level detail based on what P0.5 learned about adapter capabilities; confirm which write units genuinely collapse to a single SPARQL Update request (A2.2 table) |
| **P0.10.2** | Reaper registry: enumerate every saga from the T1–T12 catalogue that Phase 1 will introduce, with its named reaper and detector, as a code-level registry with a CI check that each saga has one |

---

## Part 5 — PHASE 1: Graph-primary core and the deployment plane

**Decomposed into** [phase-1-plan.md](phase-1-plan.md) / [phase-1-status.md](../status/phase-1-status.md) / [phase-1-sketch.md](../sketches/phase-1-sketch.md). This Part remains the authoritative slice-level detail the phase plan references; it is not duplicated there.

**Phase goal.** Move all existing operational state into the graph; stand up tenancy, packs, activation, and the change feed; deliver the first operational-register UI. **Milestones M2, M3.**

### P1.1 — Surface lifecycle → graph (T-GPM) → **M2**

| Slice | Scope | Tests |
|---|---|---|
| **P1.1.1** | `surface:Revision` graph model: node per state, `⊑ fnd:Version ⊓ fnd:Governable ⊓ fnd:Evidenced`, `fnd:supersededBy` chaining, `fnd:hasGovernanceState` per the P0.3.4 mapping | **L1/L4**: a revision's full history is the version chain (closes `data-architecture §7` gap 5); shapes enforce the mapping |
| **P1.1.2** | `conditionalWrite`-based lifecycle transitions preserving the exact `expectedVersion` → `409` semantics of `data-architecture §5.1`; API contract unchanged | **L4**: 32 concurrent conflicting transitions → one winner, 31 clean 409s; API fixtures from P0.7.5 still pass unmodified |
| **P1.1.3** | Approval evidence as `fnd:Evidence` on the new version (who approved, when, against which hash) | **L4**: "what did the revision look like when approval X was granted" is answerable by position — write this as a named acceptance test |
| **P1.1.4** | Delete the JDBC ledger and its migrations; remove the relational system-of-record path entirely | **L4**: no remaining code path writes lifecycle state outside the graph (ArchUnit); `data-architecture.md` updated |
| **P1.1.5** | Studio wired to the graph-backed API; history/version timeline surfaced | **L6**: Playwright walks draft→review→approve, shows the version chain, triggers and renders a 409 |

### P1.2 — Graph catalogue & lineage registry (T-GPM)

| Slice | Scope | Tests |
|---|---|---|
| **P1.2.1** | `graph_lineage` as a graph structure: lineage IRI → ordered revision IRIs with `fnd:supersededBy`; alias graph repointing primitive | **L4**: the selected identity profile's lineage and revision forms (A82) validated; alias repoint is atomic |
| **P1.2.2** | Replace `SurfaceGraphFamilyRegistry` conflict-rejection with structural uniqueness (content-addressed revision IRIs) | **L2/L4**: two different contents cannot collide on one IRI **by construction**; the old conflict path is provably unreachable (deleted, with the test asserting the new behaviour on the old scenarios) — closes G-05 |
| **P1.2.3** | `AuthoredGraphReference` / `RuntimeGraphReference` types (A63) replacing the single `GraphReference`; `revisionHash` demoted to a verification field; `GraphMaterializer` hash check now verifies exactly what it claims | **L1/L4**: a mismatched revision hash raises `GraphMaterializationError` before any compiler invocation; a runtime reference cannot be used where an authored one is required (type-level) |

### P1.3 — Change feed, C-08 (T-DEP)

| Slice | Scope | Tests |
|---|---|---|
| **P1.3.1** | `ChangeEvent` contract + Stream realm abstraction (broker + segment storage), ordered by `commitSeq`, replayable `since(seq)` | **L3/L4**: completeness against a known write set; no reordering within a partition |
| **P1.3.2** | Write-side emission inside `ScopedDataset` (A57), with `cause` (kind, batchId/stimulusId/journalId, principal), packDigest, profileId, and the **cause-chain depth counter** (needed later by C-10; build it now per review §4.10) | **L4**: every write produces exactly one event; depth counter increments across derived writes |
| **P1.3.3** | Store-level audit reconciliation job detecting out-of-band writes; break-glass writes tagged `cause.kind=admin` | **L4/L8**: an out-of-band write (via admin credentials) is detected and reported within the stated window |
| **P1.3.4** | Change-feed consumer library (cursor, at-least-once, idempotency contract) for C-07/C-15/C-18/C-19 | **L4**: consumer restart resumes exactly at the cursor; duplicates are inert |

### P1.4 — Release ledger → graph (T-GPM)

| Slice | Scope | Tests |
|---|---|---|
| **P1.4.1** | Release intent/receipt/event as an append-only release provenance graph; receipt-requires-intent enforced by a guarded write; ordering by `commitSeq` | **L4**: receipt without intent rejected; out-of-causal-order recording impossible |
| **P1.4.2** | `ReleaseProvenanceProjector` becomes the **writer**, not a projector; T5's dual write deleted (closes G-06 at source) | **L4**: there is no code path that records a receipt without provenance in the same write unit — assert by construction, then delete the G-06 alert as an "expected race" and re-add it as a genuine anomaly detector |
| **P1.4.3** | Release API surface + Studio Release view wired to graph ledger | **L5/L6** |

### P1.5 — MORK review snapshots & decisions → graph (T-GPM)

| Slice | Scope | Tests |
|---|---|---|
| **P1.5.1** | Immutable, content-addressed snapshot graphs; `snapshotHash` = semantic hash from C-11 | **L2/L4**: staleness rule becomes "is this the current revision of the lineage"; a decision against a stale hash is rejected |
| **P1.5.2** | MORK decision nodes co-resident with the mappings they decide (`userDeclined`, `mappingNote`, provenance) — restores the design the brief describes | **L4**: "who decided what about this mapping" is **one SPARQL pattern**; write that query as the acceptance test |
| **P1.5.3** | Role-restricted evidence projection enforced server-side at the API type level (Domain Steward response type structurally cannot carry MCN/syntax/pack internals) | **L1/L8**: a reflection-based test asserts the response type has no field capable of carrying a forbidden channel |
| **P1.5.4** | Bench wired to graph-backed review API; six-verb decisioning end to end | **L5/L6** |

### P1.6 — Governance ledger → graph (T-GPM)

| Slice | Scope | Tests |
|---|---|---|
| **P1.6.1** | Append-only governance graph; replay ordered by `commitSeq` then `fnd:recordedAt` | **L4** |
| **P1.6.2** | Hash-chained segments with chain head exported to the artifact realm (S-10); DB/store grants preventing update/delete for the application role | **L4/L8**: a tampered segment is detected; a gap is detected |
| **P1.6.3** | Calibration gate as a graph node per `(pack, profile, model)` stratum with version chaining as history (closes `data-architecture §7` gap 3 part 2); running counters in coordination, promoted on recalculation | **L4**: calibration history is queryable by position; bulk-confirm gate check refuses with `CalibrationRequiredError` and shows current precision |
| **P1.6.4** | Review queue as a **derived** coordination projection, replayable from snapshots + open questions | **L4**: drop the queue, rebuild, identical ordering |

### P1.7 — Tenancy, C-17 (T-DEP)

| Slice | Scope | Tests |
|---|---|---|
| **P1.7.1** | Entity model: Organisation → Tenant → {Project, Environment} → {DatasetBinding, ActivationBinding}; `projectId` scopes authoring, `environmentId` scopes running (A63) | **L1/L4** |
| **P1.7.2** | Provision tenant / provision environment sagas (dataset creation per A54 topology, capability report registration, authority annotations seeded), each with its named reaper | **L4**: interrupted provisioning is resolved by the reaper, leaving no orphan dataset |
| **P1.7.3** | Clone environment with environment-segment IRI rewriting (the 2 a.m. discovery from §4.17) | **L4**: cloned dataset contains no source-environment IRIs; a deliberately un-rewritten fixture fails |
| **P1.7.4** | Suspend (routes fail closed, typed reason, no deletion) and Deprovision (export → verify → drop → **ledgers survive**) | **L4/L8**: post-deprovision, ledger queries still resolve; dataset is gone; export bundle verifies by digest |
| **P1.7.5** | Service-principal credential lifecycle (rotation, expiry, per-route scoping) with role sets disjoint from human roles (A66 rule 2) | **L8**: an ingestion credential cannot read the review queue — named test |

### P1.8 — Pack builder & registry, C-01 (T-DEP)

| Slice | Scope | Tests |
|---|---|---|
| **P1.8.1** | `pack-manifest.schema.json` covering all nine sections (ontology, shapes, projections, mappings, pedagogy, profile, provenance, compatibility) with hash identity per section | **L3** |
| **P1.8.2** | `assemble(PackIntent) → PackManifest`, deterministic | **L2**: assemble twice → identical digest; input permutation → identical digest; **CI gate** |
| **P1.8.3** | **Closure completeness gate**: a pack whose `owl:imports` closure is not fully pinned by digest is rejected; no network resolution ever | **L1/L8**: a pack with an unpinned import fails with a named diagnostic; a runtime attempt to resolve an import over the network is impossible (no code path) |
| **P1.8.4** | **Safe SPARQL subset lint** (A69): no `SERVICE`, no `LOAD`, no writes outside declared target graphs, anywhere in pack content | **L8**: each forbidden construct has a rejection test |
| **P1.8.5** | Signing + `verify(PackDigest) → VerificationReport` (signature + every member digest + closure completeness), tenant-configured trust root | **L4/L8**: tampered member blob detected; wrong trust root rejected |
| **P1.8.6** | Reuse `OciLayoutBundleService` with a new media type; publish/resolve/export/restore | **L4**: export → restore → verify round-trip |

### P1.9 — Activation controller, C-02 (T-DEP) → **M3**

| Slice | Scope | Tests |
|---|---|---|
| **P1.9.1** | Activation records as graph facts (`activation_binding`/`activation_event` → graph per A1.4) + route table cached in coordination for hot reads | **L4**: "what was in force when" answerable from the graph by position |
| **P1.9.2** | State machine REQUESTED→VALIDATING→PREPARING→SHADOW→PROMOTING→ACTIVE with REJECTED/FAILED/ROLLED_BACK; one activation per environment at a time (per-key ordering) | **L4**: every illegal transition rejected; concurrent activations serialised |
| **P1.9.3** | **VALIDATING**: signature + closure verification; **store capability gate** against the P0.5.13 report; **benchmark envelope gate** (A2.6 final point: a pack whose declared SLOs exceed the measured envelope fails activation with a named reason) | **L4**: pack requiring `MULTI_GRAPH_ATOMIC_WRITE` refused on Fuseki-without-it, accepted on TDB2 — this is the headline portability test |
| **P1.9.4** | **Compatibility classing**: `additive` / `projection-affecting` / `abox-affecting` / `breaking`, computed from semantic hashes + profile identity (uses C-11 wildcard elision) | **L2/L4**: adding an unused dimension classes `additive` and triggers no re-materialisation; a canonicalisation-profile change classes `breaking` |
| **P1.9.5** | **PREPARING**: load T-Box/shapes/projection defs into a new named-graph generation; warm caches; shape self-tests against a fixture corpus | **L4**: non-zero shape violations block promotion |
| **P1.9.6** | **SHADOW**: parallel run against a live traffic sample, divergence report, explicit acceptance with recorded reason | **L4/L5**: an injected divergence is reported and blocks; accepted divergence records the reason |
| **P1.9.7** | **PROMOTING**: atomic alias repoint + route-table version publication with **quorum acknowledgement** from all `edge` instances; drain in-flight | **L5**: a non-acknowledging instance prevents completion; partial promotion cannot be reached |
| **P1.9.8** | **Rollback** within window for `additive`/`projection-affecting`; explicit refusal + forward-migration guidance for `abox-affecting`/`breaking`, stated *before* the operator commits | **L5/L6**: UI states the limitation pre-commit (assert on the rendered text) |
| **P1.9.9** | Activation saga reaper + stuck-in-PROMOTING alert | **L4** |

### P1.10 — Operations UX v1 (T-UX)

| Slice | Scope | Tests |
|---|---|---|
| **P1.10.1** | `@lattice/ui-kit` skeleton: token set, two density presets (expert/operational), status vocabulary (`pending/running/succeeded/failed/quarantined/blocked/stale/diverged/superseded`) as a single typed enum, freshness badge, Storybook, axe in CI | **L1/L6**: status vocabulary is the only source (lint bans literal status strings in apps); axe clean |
| **P1.10.2** | `@lattice/client-ts` generated from OpenAPI + deadline propagation + idempotency-key handling + retry policy | **L3** |
| **P1.10.3** | **Activation Console**: pack diff (which graphs changed hash, which projections invalidate, compatibility class, affected node counts), phase progress, SHADOW divergence report, promote/rollback with limits stated | **L6**: full activation walked in Playwright against a seeded scenario, incl. a refused rollback |
| **P1.10.4** | **Register model** documented in `ux-design.md` (G-18): expert / operational / task, with the five cross-cutting principles declared non-negotiable in all three | Human review of the doc; lint that operational surfaces do not import expert-only primitives |
| **P1.10.5** | Tenant/Environment Admin surface v1 (provisioning, dataset binding + capability report, suspend/deprovision with stated data consequences) | **L6** |

### P1.11 — Phase 1 close-out

| Slice | Scope |
|---|---|
| **P1.11.1** | Update `solution-design-specification.md` §1 (NFR/tenancy/OSS columns + runtime rows), §2.2 (G-21 publish deadline), §4.1, §4.5 (extended topology), §4.6 (four missing failure modes), §7.2 (three transaction rules) |
| **P1.11.2** | SPI seam publication (A71): SPI inventory table, TCK coverage per SPI, OSS/commercial boundary doc |
| **P1.11.3** | Expand Phase 2 to VP-level detail; confirm `C-05` resourcing (it gates Phases 2 and 3 entirely) |

---

## Part 6 — PHASE 2: Ingestion and query planes

**Decomposed into** [phase-2-plan.md](phase-2-plan.md) / [phase-2-status.md](../status/phase-2-status.md) / [phase-2-sketch.md](../sketches/phase-2-sketch.md) — a rolling-wave placeholder, per §0.5, full VP-level expansion scheduled at P1.11.3. This Part remains the authoritative slice-level detail until then.

**Phase goal.** Data gets in, questions get answered, lineage is provable. **Milestones M4, M5, M6.**

> **Sequencing rule restated:** `C-05` is the largest single piece of missing implementation and gates everything else here. Start it on day one of Phase 2 with the heaviest allocation, and run `C-13` and `C-12` foundations in parallel.

> **Persistence compiler integration (supersedes the earlier "ad hoc SPARQL" design).** `rdf-sparql-patterns-phase` Slices 1–2 are complete: the `ontology/persistence` substrate and `tools/persistence` compiler ([rdf-sparql-patterns-phase-plan.md](rdf-sparql-patterns-phase-plan.md), [persistence-profile-substrate.md](../sketches/persistence-profile-substrate.md), [rdf-sparql-patterns-guide.md](../../architecture/rdf-sparql-patterns-guide.md)) are available and tested (570 passing tests as of 2026-09-23; the compiler's re-sync with the extended vocabulary is still in progress in [`persistence-compiler-iri-sync`](../status/persistence-compiler-iri-sync.md), and identity profiles, which P2.1.5 depends on, are resolved per resource role since its Slice 3). P2.1, P2.3, and P2.4 below are revised accordingly. The caller contract every step below relies on is documented once in `tools/persistence/README.md`, "Using the generated SPARQL directly":
>
> - **P2.1 (mapping plan compiler, C-05)** resolves, validates, and instantiates a `dal:CompiledProfile` for every write target as part of `compile()` (new slice P2.1.4a). This is a design-time step with no live-backend dependency (ADR-A78/A79); its output — a compiled profile graph plus instantiated SPARQL Update text that still carries its SPARQL variables and its Mustache request-time slots (`{{{payloadTriples}}}`, `{{{logGraphs}}}`) — is the artefact P2.3 executes. No mapping hand-authors SPARQL.
> - **P2.3 (ingestion gateway, C-04)** never constructs SPARQL at request time. Its `assert` step binds request-scoped parameters into the pre-instantiated templates from P2.1.4a (P2.3.1), and its commit step (P2.3.6) *is* the template selected by the target's resolved concurrency/aggregate-boundary/receipt-model dimensions. This satisfies guardrail G5 (no string concatenation into SPARQL) for every profile-governed write without introducing the general-purpose Request Query Mapping library (Part 13, open question 11), which stays deferred pending A75 — C-04's binding responsibility here is deliberately narrower than that library's scope.
> - **P2.4 (query plane, C-12)** reuses the same resolved profile on the read side (P2.4.1): ordering grain and receipt model shape the generated read query, keeping read and write semantics consistent by construction rather than by convention. Governed `FROM`/`FROM NAMED` scoping (P2.4.2) remains a separate, Principal-derived concern composed with this.
>
> See [docs/developer/INDEX.md](../INDEX.md) for current status. The "Optional (but useful): Phase 0.2–0.4 Integration" step in [COORDINATION_REORG_HANDOFF.md](../COORDINATION_REORG_HANDOFF.md) (walking-skeleton pattern adoption) is not part of this revision and remains open.

### P2.1 — Mapping plan compiler, C-05 (T-ING, Python + shared IR)

| Slice | Scope | Tests |
|---|---|---|
| **P2.1.1** | `plan-ir` contract: `ingestion-plan.schema.json` (route, transport, requestSchema, idempotency, steps bind/mint/assert/reference/validate, admission, provenance, writeTarget) + generated Java/Python types. `writeTarget` is a `(class, deployment)` pair per `ontology/persistence`'s `Target` model (`tools/persistence/src/persistence/scopes.py`), not a bare class or a hand-described write shape | **L3** |
| **P2.1.2** | Pre-compilation gates: MORK lint, GCI/disjointness consistency, Meta-SHACL, type compatibility against the target closure, template round-trip proof per `templateMapping` | **L1/L4**: each gate has a failing fixture with a named diagnostic |
| **P2.1.3** | Box-stratified ordering derivation (T→A→R), never manually specified | **L2**: **precedence completeness** — permuted mapping input yields identical ordering |
| **P2.1.4** | `compile(MappingGraph, TargetClosure, GenerationProfile) → CompiledMappingSet`; digest = f(mappingSemanticHash, targetClosureHash, profileId, persistenceProfileHash) | **L2**: determinism, idempotence, termination (bounded on a pathological fixture) — the four `§8.4` claims become CI-asserted platform properties |
| **P2.1.4a** | **Persistence profile resolution and compiled-template emission** (new — closes the ad hoc SPARQL gap): for every `writeTarget`, run `tools/persistence`'s `compile` (resolve → validate → select against the deployment's `ontology/persistence` configuration) then `instantiate` the winning operation template(s). Embed the resulting `dal:CompiledProfile` graph and the instantiated SPARQL Update text (genuine SPARQL variables plus the Mustache request-time slots `{{{payloadTriples}}}`/`{{{logGraphs}}}` — no ad hoc string construction) into `CompiledMappingSet` as the write artefact for that target, including any `bootstrap-version-row` operation the profile requires. A `writeTarget` whose resolved profile carries an `ERROR`-severity `dal:Diagnostic`, or that raises `ProfileAmbiguityError`, is a **compile** failure, never a runtime admission failure or a silent default | **L2/L4**: compiling the same mapping graph twice, and the same graph with its `ontology/persistence` triples reordered, produces byte-identical (`rdflib.compare.isomorphic`) `dal:CompiledProfile` output and identical instantiated template text; an unresolvable or `ERROR`-diagnosed target fails compile with the named reason; reuses `tools/persistence`'s own test suite as the correctness oracle for resolution/validation rather than re-testing it here |
| **P2.1.5** | IRI minting per the target's `dal:IdentityProfile` ([iri-identity-patterns.md](../../architecture/iri-identity-patterns.md) §6, ADR-A82: natural-key, derived-hash, surrogate, surrogate-claimed, external allocator, content-addressed), with an unclaimed `surrogate` requiring explicit declaration + recorded justification. Reads the per-role identity dimensions (`identity:<Role>`) the compiled profile carries since `persistence-compiler-iri-sync` Slice 3; minting itself happens here, not in the compiler. (Corrected 2026-09-23: this row previously cited an "Appendix A" this plan does not have, from the superseded ADR-A51 policy) | **L2**: re-ingesting the same payload converges (no duplicates); `surrogate` in a convergence-required position is a compile error |
| **P2.1.6** | SKOS resolution as **lookup, never inference**; unknown code → admission violation, never an LLM call | **L1/L8**: a compiled plan has no path to a model call at resolution time |
| **P2.1.7** | RML/SHACL/SWRL artefact emission with provenance compositionality: every emitted element back-references mapping node → intent node. Covers entailment and validation artefacts only — write execution artefacts are produced by P2.1.4a | **L2**: sampled emitted elements all resolve to a source; a missing back-reference fails the build |
| **P2.1.8** | Request JSON Schema derivation from MORK Representation/Entity/Attribute structure | **L3**: generated schema validates the synth payload corpus; rejects corrupted variants |
| **P2.1.9** | Reverse plan generation where a mapping is declared invertible (input to C-10) | **L2**: round-trip on fixtures |
| **P2.1.10** | `explainPlan(planDigest) → PlanExplanation` for Technical Inspector + lineage | **L1**: golden explanation for a fixture plan |

### P2.2 — Reasoning & validation, C-13 (T-RUN)

| Slice | Scope | Tests |
|---|---|---|
| **P2.2.1** | Validation profile model (entailment regime, strategy, SHACL engine + version, severity policy, explanation depth) pinned in the generation profile | **L3** |
| **P2.2.2** | Four caller budgets with enforced deadlines: admission, materialisation, guard, query-time | **L4/L7**: each caller's budget enforced; exceeding produces a typed failure, not a hang |
| **P2.2.3** | Guard-relevant entailment restricted to rule-based materialisation with **logged firings and bindings** (A61) | **L4**: an explanation names each firing rule and its bindings |
| **P2.2.4** | Materialisation authority: every inferred triple written to a graph with `lattice:authority` + `fnd:derivedFrom` + `(semanticHash, profileId)`; governance shape from P0.3.5 enforced in CI *and* at runtime | **L4/L8**: an unannotated materialisation is rejected at write time |
| **P2.2.5** | SHACL report equivalence across engines on a shared corpus (TCK tie-in) | **L4** |

### P2.3 — Ingestion gateway, C-04 (T-ING) → **M4**

| Slice | Scope | Tests |
|---|---|---|
| **P2.3.1** | Plan interpreter core (bind/mint/assert/reference), pooled frames, no per-triple store calls. The `assert` step executes the pre-instantiated `PreparedQuery` text produced by P2.1.4a with request-scoped `Params` bound at execution time (values encoded via the same `SparqlTerm` discipline `tools/persistence.terms` uses, or the store SPI's own equivalent safe binding), renders the `{{{payloadTriples}}}` request-time slot with the skolemized payload, and binds `$requestDigest` computed per guide §15.2 — it never constructs SPARQL text itself. For a target the compiled profile gives `bootstrap-version-row` (every append stream, every `dal:PreCreatedRow` aggregate), the row is created when the id is minted, before the first write. This is a narrow, C-04-local binding responsibility, not the general-purpose Request Query Mapping library (Part 13, open question 11), which remains deferred pending A75 | **L2/L7**: identical output to the Python compiler's reference execution on the fixture corpus; allocation budget respected; a plan whose template requires a parameter the request lifecycle does not supply is a route-wiring failure caught at cache-warm time (P2.3.2), never a request-time string-building fallback |
| **P2.3.2** | Route table resolution from the active binding; **fail closed** if no active binding or plan not in cache (never lazy-load on the request path) | **L4/L8**: unknown route → typed refusal; cold cache → refusal, not a slow success |
| **P2.3.3** | Request lifecycle steps 1–5: auth (service principal), route resolve, quota check stub, request-schema validation with JSON-pointer errors, idempotency `(routeId, key, payloadDigest)` with same-key/different-digest → `409` | **L4**: each numbered step has a negative test; replayed request returns the cached result without re-execution |
| **P2.3.4** | **Staging is non-negotiable**: `INGEST_STAGING` graph family (immutable, content-addressed, short-retained); never queried by consumers | **L4/L8**: no consumer-visible query path can read staging |
| **P2.3.5** | Admission gate (C-13) + severity policy: `reject` / `quarantine` / `partial` (partial only if declared) | **L4**: whole-graph constraint violations are caught **before** commit; reject rolls staging back atomically |
| **P2.3.6** | Commit: staging → A-Box batch graph + provenance + commit marker inside the store transaction (T6); reaper for `INTERRUPTED` batches. The commit operation *is* the instantiated write template selected by the target's resolved `dal:` profile (concurrency + aggregate boundary + receipt model dimensions, from P2.1.4a) — e.g. a `dal:CompositePropertyBoundary` + `dal:Optimistic` target commits via `cas-replace-composite-property`, a `dal:NamedGraphBoundary` + `dal:AppendOnly` target via `append-event` — executed as the store SPI's single `WriteUnit` (G5, G7), followed by the confirmation read of the txn claim and its request digest on the primary, with outcomes classified per guide §15.2 (transport failures are `Unknown` and resolved by resending the identical request) | **L4**: kill mid-commit → reaper resolves by commit-marker presence; client retry is safe; a batch commit's bound SPARQL, replayed through `tools/persistence`'s own `instantiate` for the same resolved profile and parameters, is byte-identical (no drift between design-time compilation and request-time execution) |
| **P2.3.7** | Batch-file transport (chunked, per-chunk commit, batch manifest) and stream transport, both on the same interpreter | **L4/L7**: ≥ the `nfr.yaml` throughput target per worker; duplicate stream delivery inert |
| **P2.3.8** | Hard limits before parse (size, depth, array cardinality) → `413` | **L8**: malicious payload corpus |
| **P2.3.9** | Change-feed + usage-event emission; response shape (batchId, accepted/rejected counts, per-item diagnostics) | **L3/L5** |

### P2.4 — Query & decision plane, C-12 (T-QRY) → **M5**

| Slice | Scope | Tests |
|---|---|---|
| **P2.4.1** | Typed read API generated per projection from the Projection contract at pack build. Where the projection's source data is `dal:`-profiled, the read query shape draws on the same resolved profile that governs its writes (ordering grain → pagination/sort-key shape; receipt model → whether a read targets current-state materialisation directly or must fold an event log) — generated once at pack build from the same `dal:CompiledProfile` (P2.1.4a), not re-derived ad hoc per read | **L3/L7**: one indexed pattern per read (asserted via query plan/complexity check); meets the typed-read SLO; a projection over a `dal:AppendOnly` (event-stream) target generates a fold-the-log read shape, one over a whole-graph-replace target (`dal:Optimistic` with `dal:ReceiptOnly` or `dal:PatchLog`) generates a direct read of current state — asserted against the `ontology/persistence` example fixtures. (Corrected 2026-09-23: this row previously named `dal:AppendOnly` as a receipt model and cited `dal:CurrentStateOnly`, which does not exist) |
| **P2.4.2** | Governed SPARQL: **gateway-constructed** `FROM`/`FROM NAMED` from `Principal` (never client-supplied); a query naming an invisible graph is rejected, not filtered. A Principal-scoping concern, orthogonal to and composed with the `dal:`-profile-derived query shape from P2.4.1 | **L8**: extends P0.5.8 to the HTTP boundary |
| **P2.4.3** | Cost governance: timeouts per class, cardinality cap + pagination, complexity pre-check, per-tenant concurrency semaphore with separate analytic pool | **L7/L8**: an abusive query is refused, not absorbed; one tenant cannot starve another |
| **P2.4.4** | **Decision/Explain API** with `verdict ∈ {admit, deny, indeterminate}`, witness/challenge reason structure, evidence refs, freshness block, `identity{packDigest, profileId, decisionRecordId}` | **L4/L7**: `indeterminate` is first-class and never collapsed to `deny` (named test); explain-minimal meets its SLO |
| **P2.4.5** | Freshness contract propagation: every projection read returns observed `appliedThrough` + lag + contract | **L4**: a stale read is distinguishable from a fresh one at the API level |

### P2.4 — Query & decision plane, C-12 (T-QRY) → **M5** *(continued)*

| Slice | Scope | Tests |
|---|---|---|
| **P2.4.6** | Consistency contract: `consistency ∈ {strong, bounded, any}`; `strong` pins to primary; any read feeding a write-back or a behaviour decision is `strong` **by construction** (type-level, not by convention) | **L1/L4**: a decision path cannot be compiled against a `bounded` read (typed); a `bounded` read against a lagging replica returns its observed lag rather than pretending to be current |
| **P2.4.7** | Saved governed queries: registration, review, versioning by digest, per-query cost class; ad-hoc permitted at a lower limit | **L4**: a saved query's digest pins its text; editing it creates a new version, never mutates |
| **P2.4.8** | Authorization granularity (A60): graph-level scoping only; role-scoped **projections** as the sanctioned finer-grained mechanism; instance-level ACLs explicitly absent | **L8**: no per-triple ACL evaluation exists on the read path (asserted by absence + a documented rejection test); a role-scoped projection returns exactly the permitted subset |
| **P2.4.9** | `query_audit` emission (who asked what, cost, freshness, verdict) into the Stream realm, indexed for the four operator queries (by subject / principal / time range / verdict) | **L4/L7**: audit write is off the hot path (asynchronous, bounded buffer, never blocks the response) |
| **P2.4.10** | **Decision records** (§5.6, A72): full record content (both time axes, pack + profile + canonicalisation profile versions, input digests, evidence, delegation chain, observed freshness, output refs); Stream realm for bulk, graph node for referenceability, coordination index for operator queries | **L2/L4**: **re-derivation test** — replay a recorded decision from its record and assert the same verdict and witness set; a deliberately drifted pack produces a *detected* divergence rather than a silent difference. This is the audit mechanism, so validate it adversarially |

### P2.5 — Lineage & provenance service, C-19 (T-QRY)

| Slice | Scope | Tests |
|---|---|---|
| **P2.5.1** | `ProvenanceScope` record writer enforcing **provenance homogeneity** (one cause per graph, A65) across every write path introduced so far | **L4/L8**: an attempt to accumulate two causes into one graph is rejected at the SPI; every existing write path audited by a test that enumerates graphs and asserts exactly one cause |
| **P2.5.2** | Backward lineage: `GET /lineage/backward?node&property&depth` → runtime node → version → batch graph → ingest batch / extraction run → mapping node → intent node → source pointer (JSON pointer or document span) | **L4/L5**: a seeded ingested value resolves to its exact JSON pointer; a synthetic multi-hop chain resolves in order |
| **P2.5.3** | Forward lineage: `GET /lineage/forward?node` → every derived product, projection, decision record, downstream write | **L4**: used by C-02 invalidation planning and §5.12 archival safety — assert that a node with three dependents returns all three, and that adding a fourth is detected |
| **P2.5.4** | `GET /lineage/decision/{decisionRecordId}` → the full evidence set **as it stood, by hash, at decision time** | **L4**: evidence resolves even after the live graph has moved on (the test must mutate the graph between decision and query) |
| **P2.5.5** | Opt-in `ProvenanceAssertion` nodes for declared high-scrutiny properties (no RDF-star dependency) | **L4**: a monetary limit extracted from a clause carries per-value provenance; the store capability report is not consulted (proving the portability claim) |
| **P2.5.6** | **Lineage survives archival** (§5.12 rule 2): a backward-lineage query hitting archived content returns the archive reference, never "not found" | **L4**: archive a generation, re-run the lineage query, assert the archive reference resolves to a verifiable digest |

### P2.6 — Metering & quota, C-16 (T-QRY)

| Slice | Scope | Tests |
|---|---|---|
| **P2.6.1** | `usage_event` contract + emission **on the same path as the work** (never log-derived), carrying tenant, environment, packDigest, principal, correlationId | **L3/L4**: every metered dimension from §4.16 has an emitting call site and a test; a code path doing metered work without emitting fails an ArchUnit-style check |
| **P2.6.2** | Counter promotion pattern (A1.5 rule 5): hot counters in coordination, promoted to versioned graph measurement nodes at a declared granularity | **L4**: counter loss bounded by the promotion interval (chaos test: drop coordination mid-window, assert bounded inaccuracy and no lost decisions) |
| **P2.6.3** | Quota pre-check at the two enforcement points only (gateway, C-14): `429` + `Retry-After` + machine-readable reason (`quota: documents_per_month`); soft warning at 80% | **L4/L8**: never a 500, never a silent slow-down; a quota-exhausted tenant gets a typed refusal while another tenant is unaffected |
| **P2.6.4** | Metering/billing seam (§5.11): emission is OSS, rating is not; documented interface + reference `UsageSink` | Human review of the seam doc + **L3** sink contract test |

### P2.7 — Push / subscription gateway, C-18 (T-HOST)

| Slice | Scope | Tests |
|---|---|---|
| **P2.7.1** | SSE transport on the existing HTTP surface, subjects `job.status`, `queue.entry`, `activation.progress`, `ingestion.batch`, `projection.freshness`, `graph.change`, `writeback.state` | **L4/L6**: subscription established, events delivered, connection survives a proxy-style idle timeout |
| **P2.7.2** | Server-side filtering derived from `Principal` using the **same** graph-visibility mechanism as C-12; a subscription is a query (same authorization, same cost accounting, same fail-closed posture) | **L8**: a subscriber cannot receive an event about a graph it may not read — named cross-tenant test |
| **P2.7.3** | At-least-once with `lastEventId` cursor resume; consumer idempotency contract documented and exercised | **L4**: reconnect with cursor loses nothing and duplicates are inert |
| **P2.7.4** | Backpressure: bounded per-connection buffer; on overflow emit `resync` and drop the buffer (never grow it) | **L4/L7**: a slow consumer under a flood receives `resync` and the server's memory stays bounded — this is the routinely-omitted control, test it explicitly |
| **P2.7.5** | Polling equivalent for **every** subject + SDK automatic degradation; deployment flag to disable push entirely and remain fully functional | **L5/L6**: run the full UI E2E suite twice — once with push enabled, once disabled — both green. Make this a standing CI matrix dimension, not a one-off |

### P2.8 — Runtime feedback router, C-15 (T-FB)

| Slice | Scope | Tests |
|---|---|---|
| **P2.8.1** | `runtime_uncertainty` model as graph nodes co-resident with what they are uncertain about; the nine runtime states from §4.15 with owner, route, and affordance | **L4**: each state has a fixture and routes to the declared owner |
| **P2.8.2** | **Same queue, same verbs, same yield function**: runtime uncertainty enters the MORK review queue ordered by yield, with the cross-**batch** yield figure ("answering this unblocks N quarantined records") | **L4**: yield ordering computed over mixed design-time and runtime items; the unblock count is exact against a seeded corpus |
| **P2.8.3** | Metric naming discipline (R-10): `open_questions_total` and `admission_rejections_total` are **separate**; no metric name in the codebase conflates uncertainty with error | **L1**: a lint rule over metric names with an explicit deny-list; a PR adding `ingestion_errors_total` including uncertainty fails |
| **P2.8.4** | **Replay-not-repair**: teaching a synonym / extending a scheme produces a governance ledger entry + a new pack (or scheme update where declared externally mutable) + **replay of quarantined batches by digest**; the original batch is never edited | **L5**: the M4 headline scenario — quarantine 4 000 records, teach one synonym, replay by digest, all 4 000 admit, and "what fixed these records" is one query |
| **P2.8.5** | Drift monitor: per `(packDigest, profileId, modelId)` stratum — unmapped rate, confidence distribution, confident-tail approval rate, admission violation rate by shape, projection divergence count; alarm on distribution shift | **L4/L7**: an injected payload-shape change is detected as drift before it becomes a data-quality collapse |

### P2.9 — Content ingestion pipeline, C-06 + agent orchestrator, C-14 (T-ING) → **M6**

> **Build C-14 first.** Every LLM call in C-06 must go through it, so that model pinning, budgets, caching, egress policy, and the audit record exist before the first completion is requested. Building C-06 first and retrofitting C-14 is how those controls end up partial.

| Slice | Scope | Tests |
|---|---|---|
| **P2.9.1** | `LlmProvider` SPI + C-14 supervisor: model pinning `(modelId, promptTemplateHash, packHash, temperature, seed)` recorded on **every** call; structured-output validation; typed parse-failure signature routed to Pack Maintainer (never retry-until-it-parses) | **L1/L4**: a call without full pinning is unconstructable; a malformed model response produces a typed failure signature, and the test asserts no retry loop occurs |
| **P2.9.2** | Cache keyed `(spanDigest, promptTemplateHash, modelId, packHash)`; **no cross-tenant prompt caching, ever** (S-2) | **L4/L8**: cache hit avoids the call; a second tenant with an identical span does **not** hit the first tenant's cache — named security test |
| **P2.9.3** | Budgets: per-tenant, per-run token and currency caps enforced **before** dispatch; exhaustion degrades to the non-LLM strata (recognition → community → projection) rather than failing | **L4**: with the LLM disabled entirely, the pipeline still produces results at the documented 60–85% coverage on the fixture corpus. **This is the degradation claim — validate it as a first-class scenario, not a fallback footnote** |
| **P2.9.4** | Egress policy per tenant (provider, region, redaction, local-only); functional with local models only | **L8**: a `local-only` tenant's content provably never leaves the deployment (network assertion in the test harness) |
| **P2.9.5** | Cassette recording/replay harness for deterministic CI (record once, replay always; live-call tests quarantined to a manual job) | **L4**: full C-06 suite runs with zero live calls; cassette drift is detected |
| **P2.9.6** | Pipeline stages 1–3: acquire (blob to artifact realm, encrypted, PII-classified, `documentId` + content digest), layout/text extraction with span geometry, segmentation | **L2/L4**: deterministic given pinned engine versions; span coordinates round-trip |
| **P2.9.7** | Stage 4 — extract intent: `IntentNode` graph in **general vocabularies only**, `hasNaturalLanguageSource` span + page + bbox, `extractionConfidence`; output recorded as the durable artefact (never recomputed on read) | **L1/L8**: the stage-4 output type is **structurally incapable** of carrying an ontology IRI (reflection test); re-running produces a new `extraction_run`, never an overwrite |
| **P2.9.8** | Stage 5 — align: LLM selects **from a deterministically computed candidate set** derived from the active pack; cannot invent an IRI; minting remains a separate human-gated path | **L8**: prompt-injection corpus (a clause instructing a favourable mapping) cannot produce an out-of-candidate-set result; anomaly detection flags outputs diverging sharply from section consensus |
| **P2.9.9** | **Three confidence channels kept separate** as a data-contract rule: `extractionConfidence`, `notationConfidence`, `domainConfidence`; no API or pipeline stage may combine them | **L1/L3**: no type anywhere exposes a combined score; a schema field named like a composite score fails a lint rule |
| **P2.9.10** | **Two-bench layer separation as an API constraint**: the intent-review response type has no field capable of carrying an ontology IRI (server-enforced, so a UI bug cannot violate layer independence) | **L1/L8**: reflection test over the response type; a deliberate field addition fails the build |
| **P2.9.11** | Stages 6–9: compile candidate A-Box via the C-05 plan → staging → admission gate (shapes + confidence thresholds + calibration gate) → route (auto-admit / HITL / quarantine) → commit with provenance | **L4/L5**: each route has an end-to-end test; a below-threshold extraction lands in HITL and appears in the C-15 queue |
| **P2.9.12** | Run comparison as a first-class operation (drift detection input): compare two `extraction_run`s by id | **L4**: a changed model id produces a comparable, non-overwriting second run |
| **P2.9.13** | Full prompt-injection threat suite (S-1): structured prompt boundaries, no tool-calling capability, admission shapes authored from pack only, plus a corpus of adversarial clauses | **L8**: the suite is the acceptance criterion for M6 — run it in the human gate, not just CI |

### P2.10 — Operational and task-register UX (T-UX)

| Slice | Scope | Tests |
|---|---|---|
| **P2.10.1** | `@lattice/ui-kit` expert primitives extracted as real, tested, documented components: token ribbon, **witness/challenge checklist**, two-sided coverage meter, evidence-channel availability display, yield-ordered queue, keyboard verb bar, provenance chain renderer, conflict/diff panel | **L1/L6**: Storybook + axe per component; the witness/challenge component renders **both** a MORK feasibility panel and a C-12 decision explanation from the same props (the architectural economy — assert it with one shared fixture) |
| **P2.10.2** | **Ingestion Monitor**: route list with accept/quarantine/reject rates and trend; per batch payload digest, plan digest, JSON-pointer diagnostics; three actions — **replay by digest**, quarantine to queue, download original payload | **L6**: a failed batch is re-driven to success **entirely from the UI**, with no curl and no developer. That is the pass criterion |
| **P2.10.3** | **Explain / Decision viewer** (task register, embeddable): satisfied/unsatisfied checklist in domain language, excluding axiom named on exclusion, `✓ / ✗ / ⊘` semantics, copy discipline (never *valid*, never *verified*) | **L6**: copy-discipline lint over UI strings; rendering an `indeterminate` verdict is visually distinct from `deny` |
| **P2.10.4** | **Lineage viewer** (task register, embeddable): value → version → batch graph → extraction run / ingest batch → mapping node → intent node → **highlighted PDF span or JSON pointer** | **L6**: the click-through from a seeded value to the highlighted span in the source PDF. Prioritise this: it is the most commercially persuasive screen and it is nearly free once P2.5 exists |
| **P2.10.5** | Embedding contract: iframe/web-component packaging for Explain and Lineage viewers, token exchange, theming inputs | **L6**: embedded in a bare host page, authenticated by exchanged token, themed |
| **P2.10.6** | `clients/client-java` + `clients/client-python` generated SDKs with SSE + polling fallback, deadline propagation, idempotency keys, retry policy | **L3**: the Python worker tier's calls back to the control plane use the generated client (no hand-rolled HTTP anywhere) |
| **P2.10.7** | White-label surface: CSS custom properties from tokens, brand/logo/colour/optional density lock, documented | **L6**: a second theme applied in CI screenshots without touching app code |

### P2.11 — Phase 2 close-out

| Slice | Scope |
|---|---|
| **P2.11.1** | Anti-pattern lint pass (§6.5): a projected value cannot render without its freshness state; no single environment "health" score exists; not-fired transitions cannot be hidden (component contract); raw SPARQL is not reachable from business-user surfaces |
| **P2.11.2** | Observability extension (§5.8): the six operator questions each mapped to concrete signals; correlation identity chain `correlationId → batchId/stimulusId → decisionRecordId → txnId → journalId` proven end to end |
| **P2.11.3** | **The one-minute acceptance criterion**: given a policy number and a date, an operator retrieves every event, decision, and write that touched it, in order, in under a minute, without a developer. Automated as an L5 test with a stopwatch assertion and rehearsed by a human at the gate |
| **P2.11.4** | Expand Phase 3 to VP-level detail; confirm reconciliation design for C-07 before any C-09 work is scheduled |

---

## Part 7 — PHASE 3: Operation plane

**Decomposed into** [phase-3-plan.md](phase-3-plan.md) / [phase-3-status.md](../status/phase-3-status.md) / [phase-3-sketch.md](../sketches/phase-3-sketch.md) — a rolling-wave placeholder, per §0.5, full VP-level expansion scheduled at P2.11.4. This Part remains the authoritative slice-level detail until then.

**Phase goal.** Projections stay fresh, tanks respond, values flow back. **Milestones M7, M8, M9.**

> **Hard gate:** no C-09 slice starts until C-07 reconciliation (P3.1.7) has been green for a full week of nightly runs against the synthetic load, including an injected-divergence scenario. A behaviour engine over a silently-corrupt projection produces wrong decisions that look right.

### P3.1 — Projection maintenance engine, C-07 (T-RUN) → **M7**

| Slice | Scope | Tests |
|---|---|---|
| **P3.1.1** | Projection strategy taxonomy declared in the Surface contract (A56): `virtual`, `materialised-full`, `materialised-incremental`, `hybrid`, `entailed`; each with its declared **freshness contract** (`exact` / `bounded(Δ)` / `eventual`) | **L3**: a projection without a declared strategy + freshness contract fails pack build |
| **P3.1.2** | `virtual` strategy: SPARQL rewrite at query time over source layers | **L4/L7**: correct results; latency measured and compared against materialised for the same query (produces the evidence for strategy choice) |
| **P3.1.3** | `materialised-full`: periodic rebuild into a new generation + alias flip | **L4**: alias flip atomic; consumers never see a partially built generation |
| **P3.1.4** | **Dependency index** compiled at pack build: a function from source predicate/class to projection key-extraction query, derived from the Surface read-set (reuse, do not reinvent) | **L2**: for a fixture corpus, every source change maps to the correct affected key set; a missing mapping is a **build** failure, not a runtime surprise |
| **P3.1.5** | `materialised-incremental`: change-feed subscription filtered by read-set → affected keys → per-key recompute → watermark advance (`appliedThrough`) | **L4/L7**: watermark reported to C-12 matches reality; meets the incremental-lag SLO under the synthetic claim rate |
| **P3.1.6** | `hybrid`: materialised base + virtual overlay for the current open period | **L4**: exactness for hot data, bounded staleness for cold; a boundary-crossing record is correct in both paths |
| **P3.1.7** | **Scheduled full reconciliation**: full rebuild digest compared against incremental state; divergence alarms and is classified **S1** | **L4/L7**: an injected divergence (a deliberately dropped dependency-index entry) is caught within one reconciliation cycle and never auto-healed. **This is the R-03 control — the highest-likelihood risk in the register. Validate it by breaking the index yourself at the gate** |
| **P3.1.8** | Invalidation across activation: generation graphs annotated with `(semanticHash, generationProfileId)`; C-02 re-materialises exactly those whose pair changed; wildcard elision means an unused added dimension triggers nothing | **L2/L4**: the payoff test from P0.4.4 now demonstrated end to end at activation |
| **P3.1.9** | Concurrency: one maintainer per `(tenant, projection)` via advisory lease, standby failover | **L4**: two maintainers → one active; lease loss mid-batch does not corrupt the watermark |
| **P3.1.10** | `entailed` strategy gated on store capability (`REASONING` + profile coverage), refused at activation otherwise | **L4**: refusal carries a named reason |
| **P3.1.11** | **`ProjectionSink`** as a declared target type (G-36 / A1.6): `kind ∈ {relational, columnar, vector, graph}`, per-environment binding, projection-owned schema, key extraction + row construction SPARQL, `writability: read-only`; sink migration participates in activation compatibility classing; full rebuild from graph mandatory | **L4**: reference relational sink (coverage-span sweep case) rebuilt from the graph is byte-identical to the incrementally maintained state; a sink holding a fact absent from the graph is detected by reconciliation; a sink schema change classes `projection-affecting` and is shadowed before promotion |

### P3.2 — Behaviour execution engine, C-09 (T-RUN) → **M8**

| Slice | Scope | Tests |
|---|---|---|
| **P3.2.1** | Aggregate model: `aggregateRoot` + key-extraction query declared in the Behaviour projection contract; aggregate = transitive closure of nodes one transition may write | **L1/L3**: an effect writing outside its declared aggregate is a **compile** failure |
| **P3.2.2** | Aggregate lease with fencing token via `PartitionedWorkQueue` + coordination lease; strict per-key ordering | **L4/L7**: 32 partitions, concurrent stimuli, strict per-aggregate ordering held; lease acquisition cost under the §5.4-derived 5 ms budget |
| **P3.2.3** | **Time as an input**: every stimulus carries `decisionTime`; `now()` banned in guards and effects; random and external calls forbidden | **L1/L8**: ArchUnit/lint ban proven with a violating fixture; a guard attempting a network call fails at compile or load time |
| **P3.2.4** | Guard evaluation against compiled Eligibility artefacts (C-13, rule-based, logged firings) over aggregate state + projected context; no LLM, no network beyond the store | **L4**: verdict plus a named witness/challenge set per evaluation |
| **P3.2.5** | Decision outcomes: `fire` / `not-fired (with reason)` / `blocked (unresolved question → C-15)` | **L4**: not-fired reasons are durable and queryable — the most frequently asked operational question must be answerable without a log grep |
| **P3.2.6** | Effects as a proposed delta: **new versions only**, never mutation of authored nodes; shape validation of the delta before commit | **L4/L8**: an effect attempting in-place mutation of an authored `ins:` node is rejected at the SPI |
| **P3.2.7** | **Single-write-unit commit** (T7): new versions + `supersededBy` + stimulus log entry at position P+1 + emitted stimuli + runtime state hash, in one atomic request | **L4**: killed mid-commit → no partial state; next load detects nothing anomalous. On a store lacking multi-graph ACID, the declared per-aggregate saga path is exercised instead, with the stimulus log as the recovery point |
| **P3.2.8** | Idempotency by position: `stimulusId <= appliedPosition` returns the recorded outcome | **L4**: duplicate delivery replays, never re-applies |
| **P3.2.9** | Cross-aggregate effects **emitted as new stimuli, never applied inline**; cross-aggregate invariants handled by a declared parent aggregate or a declared compensating saga | **L1/L4**: an inline cross-aggregate write is a compile failure; the treaty-level-cap scenario works through a parent aggregate |
| **P3.2.10** | **Capacity-tank semantics**: the authored `ins:` capacity node is immutable; current capacity is a versioned runtime node in the capacity projection linked by `fnd:derivedFrom` and by provenance to the causing stimulus | **L4/L5**: "what capacity did this layer have on date D under claim sequence S" is answered **by position**; the authored contract value is byte-identical before and after 10 000 claims (headline test) |
| **P3.2.11** | **Deterministic replay**: same pack + same start state + same ordered stimuli → same runtime state hash; wall clock and storage addresses excluded from the hash projection | **L2/L7**: replay 10 000 stimuli twice and across two processes → identical hash; a backdated claim inserted mid-sequence replays correctly (the insurance complication most likely to be found late) |
| **P3.2.12** | Poison stimulus policy: **block the partition and page**, never skip | **L4/L8**: skipping is not reachable in code; blocked partition raises the alert and exposes operator replay tooling |
| **P3.2.13** | Operator replay tooling: replay a partition from a position, dry-run mode producing a divergence report before committing | **L5**: dry run detects a deliberate divergence without writing |

### P3.3 — Write-back / reverse projection, C-10 (T-RUN) → **M9**

| Slice | Scope | Tests |
|---|---|---|
| **P3.3.1** | Writability classification in the Projection contract: `read-only` (default), `pass-through`, `unit-converted`, `lens`; `writeBack` block in `projection-contract.schema.json` | **L3**: absent declaration means `read-only`; `rejected` is the default behaviour |
| **P3.3.2** | **Lens laws discharged at pack build**: PutGet and GetPut structurally for `pass-through` and `unit-converted`; for `lens`, property-based testing over a generated instance corpus with the corpus and **seed pinned into the pack manifest** | **L2**: a law-violating `lens` is a **pack build failure naming the violated property**, not a runtime surprise. Include a deliberately non-invertible fixture that must fail. Optional `PutPut` only where declared |
| **P3.3.3** | Transaction modes: `same-transaction`, `journalled`, `proposal`, `rejected`; `same-transaction` **refused at activation** if the store lacks multi-graph ACID | **L4**: capability gate exercised on both adapters |
| **P3.3.4** | `same-transaction` mode (T8): projected write + source write + projection generation update in one write unit | **L4/L7**: reader never observes divergence; meets the in-request SLO |
| **P3.3.5** | `journalled` mode (T9): journal entry as a graph node, applier worker idempotent by `journalId`, `lattice:writeBackState ∈ {pending, applied, failed, compensated}` returned by C-12 **alongside the value** | **L4/L6**: an operator can always answer "is the source layer consistent with what I am looking at, right now?" — asserted at both API and UI level |
| **P3.3.6** | Conflict handling: apply only if the source node's current version digest equals `priorValueDigest`; otherwise `CONFLICTED` → C-15 with the three facts (intended, current, what changed it). **Never last-write-wins** | **L4**: a concurrent source change produces a conflict, not an overwrite — extends the §5.1 optimistic-concurrency rule across realms |
| **P3.3.7** | Write-back target discipline: never writes to a `derived-*` graph; always creates a **new version** of the source node with `fnd:supersededBy` and the projection write/stimulus recorded as `fnd:Evidence` | **L4/L8**: the source layer's history records *why* it changed (the auditor-defensibility property); a write targeting a derived graph is rejected at the SPI |
| **P3.3.8** | Compensation: `compensate` (default — revert the projected runtime node to its prior version as its own versioned change, never a deletion) or `hold` (declared, with an alert route) | **L4**: terminal applier failure leaves no silently-changed projected value |
| **P3.3.9** | **Write-back loop cap**: cause-chain depth counter on `ChangeEvent.cause` (built in P1.3.2) with a hard cap (default 1); exceeded → circuit break + alarm | **L4/L8**: a deliberately mis-declared `lens` produces a **named defect**, not an infinite loop. R-02 control — validate personally |
| **P3.3.10** | `listDivergent(tenant, env, projectionId)` operability API + stale-journal detection (projection re-materialised while a journal was pending → `STALE` → review) | **L4** |

### P3.4 — Tank Inspector and runtime UX (T-UX)

| Slice | Scope | Tests |
|---|---|---|
| **P3.4.1** | **Tank / Aggregate Inspector**: current state + position + runtime state hash, **with the authored source value shown alongside** (structural, not optional) | **L6**: the "contract says 10M, tank holds 6.2M" distinction is impossible to miss; a component test asserts the authored value cannot be omitted from the props |
| **P3.4.2** | Stimulus history ledger incl. **not-fired transitions with reasons**; verdict → Explain viewer (same witness/challenge component) | **L6**: not-fired rows are present and reason-bearing |
| **P3.4.3** | Time travel: as-of valid time and as-of transaction time selectors, side by side, in business language ("as things stood on…" / "as we knew them on…") | **L6**: both axes independently varied; a backdated endorsement scenario reads correctly on each |
| **P3.4.4** | Write-back state per projected property (mode, journal state, divergence age, target source node) | **L6** |
| **P3.4.5** | **Operations Console** (§6.2): activation in force, ingestion rates and admission outcomes by route, extraction backlog, projection freshness vs contract, behaviour partition health, write-back divergence, open questions by owner, cost vs quota — one screen, six independent facts, **no single health score**, every number drills down | **L6**: no number is a dead end (asserted by crawling every rendered metric for a drill-down target) |

### P3.5 — Runtime availability posture and storage lifecycle

| Slice | Scope | Tests |
|---|---|---|
| **P3.5.1** | Role-profiled HA deployment (A70, §5.9): ≥2 `control`, ≥3 `edge`, partition-assigned `behaviour` with lease failover, one active `projection` maintainer with standby; relay leadership via advisory lock | **L5/L7**: rolling restart of each role with zero lost work and stated latency impact; behaviour partition failover measured |
| **P3.5.2** | Read-replica routing for `bounded`/`any` consistency; `strong` pinned to primary; documented store failover procedure per adapter | **L4/L7**: a stale replica cannot serve a decision path (typed, per P2.4.6) |
| **P3.5.3** | Backup/restore per adapter with stated RPO/RTO (R-13), plus content-addressed export bundles as the store-independent second line | **L5**: restore-from-backup and restore-from-bundle both verified by digest; documented as a runbook and rehearsed at the gate |
| **P3.5.4** | **Generation retirement** (§5.12): superseded projection generation outside its rollback window → export to artifact realm as digest-addressed N-Quads → verify → drop; export digest recorded so lineage still resolves | **L4**: export-verify-drop as a saga with a named reaper; nothing is dropped without a verified export |
| **P3.5.5** | Valid-time cold partitioning: closed periods move to an archive dataset, queryable via federation with relaxed SLOs | **L4/L7**: an as-of query spanning live and archived data returns correct results; lineage into archived content resolves (re-runs P2.5.6) |
| **P3.5.6** | Ledger and decision-record partitioning by month, compressed and exported with **hash-chain continuity preserved** | **L4/L8**: chain verification across a partition boundary |
| **P3.5.7** | Reaper registry completeness check: every saga in the T1–T12 catalogue plus every saga added in Phases 1–3 has a named reaper with its own alarm | **L1**: CI fails if a saga is registered without a reaper |

### P3.6 — Phase 3 close-out

| Slice | Scope |
|---|---|
| **P3.6.1** | Full SLO benchmark run against the §5.4 reference load profile on the reference store; publish the benchmark section of the capability report; reconcile measured vs declared and amend `nfr.yaml` where the numbers were wrong (amending is fine; leaving them unmeasured is not) |
| **P3.6.2** | Catastrophe-peak load test (10× claim rate) exercising per-aggregate ordering, partition count, and lease contention; produce the partition-count sizing recommendation |
| **P3.6.3** | Capacity and cost model published per tenant tier (store nodes/RAM, coordination size, broker throughput, LLM spend per 1 000 pages, worker counts) |
| **P3.6.4** | Expand Phase 4 to VP-level detail |

---

## Part 8 — PHASE 4: Maturity

**Decomposed into** [phase-4-plan.md](phase-4-plan.md) / [phase-4-status.md](../status/phase-4-status.md) / [phase-4-sketch.md](../sketches/phase-4-sketch.md) — a placeholder, full expansion scheduled at P3.6.4. This Part remains the authoritative detail until then.

Deliberately lighter: each item is a sub-programme sized after Phase 3 measurement.

| Slice group | Scope | Gate focus |
|---|---|---|
| **P4.1** Agent orchestration full | Retrieval over confirmed mappings, community/FCA stratum, calibration stratum boundaries rendered as boundaries (never smoothed), cost analytics | Does the cheapest-first stratum ordering actually reduce LLM spend against the P3.6.3 baseline? Measure, do not assert |
| **P4.2** Drift analytics | Per-stratum distribution monitoring, confident-tail approval rate, decision re-derivation divergence rate, calibration curves | Alarms fire on injected drift before data quality degrades |
| **P4.3** Second store adapter | GraphDB (or chosen commercial store) to Core + declared Extended; TCK pass + benchmark report; **admission by TCK, never by assertion** | The adapter admission rule holds: no "supported" claim without a published passing run |
| **P4.4** RDF4J embedded adapter | Broadens standards validation of the SPI | Finds SPI assumptions that were accidentally TDB2-specific — expect some |
| **P4.5** SPC integration (A62, if adopted) | Namespace already harmonised in P0.1.12; author `spc/projection/party.ttl` + `behaviour.ttl`; lift the uniformly-documented workflow state machines from C-02/C-06/C-10 into session types | Mechanical lift is only possible if the Phase 1–3 state machines were documented in the uniform shape — audit that at the P3 gate, not here |
| **P4.6** Commercial packaging | SPI seam hardening, licensee onboarding kit, teaching packs/cassette corpora, rating/billing integration against the `usage_event` stream | Does a commercial extension require **zero** patches to OSS classes? Prove with a sample adapter in a separate repo |
| **P4.7** Multi-region (explicitly deferred) | Not built. Re-stated as a non-goal with the reason, reviewed annually | — |

---

## Part 9 — Continuous Epics (run across all phases, never a trailing phase)

These are not phases; they are standing obligations with per-phase slices.

| Epic | Per-phase obligation | Enforcement |
|---|---|---|
| **T-DATA** | Every new component contributes generator coverage + a named scenario before its first L5 test | CI: an L5 test referencing an unseeded scenario fails |
| **T-SEC** | Every slice touching a threat-model control adds or extends its L8 suite in the same slice | Traceability: an S-nn control without a passing test blocks the phase gate |
| **T-DEC** | Every "Decided here" item becomes a ratified ADR before the code that depends on it merges | CI: a module referencing an unratified ADR tag fails |
| **T-UX** | Every API introduced in a phase gets its operational or task surface in the same phase (never "UI later") | Phase gate checklist |
| **Docs** | Normative document deltas ship in the slice that causes them | Review checklist; doc-drift detector comparing claimed sections to changed code |
| **Perf** | L7 baselines recorded at each component's first integration; regressions beyond threshold fail CI | Benchmark harness in CI |
| **Accessibility** | axe clean on every new surface; WCAG 2.2 AA audit at each phase gate | CI + gate |

---

## Part 10 — Parallelisation plan

Assumes multiple agent teams working concurrently with one human validator per Epic (validators may hold two Epics).

| Phase | Parallel streams | Serialisation points |
|---|---|---|
| **P0** | (a) T-DEC decisions; (b) T-BUILD build/CI/codegen; (c) T-ONT ontology+shapes; (d) T-DATA synth | P0.4 (hash) needs P0.3.3 vocabulary; P0.5 (SPI) needs P0.4 signatures; P0.7 (host) needs P0.2.4 codegen; P0.8 (outbox commit-marker) needs P0.5.2 write surface |
| **P1** | (a) T-GPM migrations P1.1/P1.4/P1.5/P1.6 in parallel — independent entity families; (b) T-DEP P1.7→P1.8→P1.9 serial; (c) T-UX P1.10 | P1.3 change feed before P1.9.6 SHADOW; P1.2 IRI/lineage before all T-GPM slices |
| **P2** | (a) C-05 (heaviest, start first); (b) C-13; (c) C-12+C-19; (d) C-16+C-18; (e) C-14 then C-06; (f) T-UX | C-04 needs C-05 plan IR + C-13 admission; C-19 needs P2.5.1 across all existing write paths; C-06 stage 6 needs C-05 |
| **P3** | (a) C-07 (must stabilise first); (b) C-10 lens-law compiler work *can* start in parallel since it is a pack-build concern; (c) HA + storage lifecycle; (d) T-UX | **C-09 gated on C-07 reconciliation green for one week**; C-10 apply path needs C-09 for the stimulus-caused case |

**Anti-pattern to avoid:** parallelising C-07 and C-09 to "save time". The review is explicit and the risk register agrees (R-03 likelihood **High**). Do not.

---

## Part 11 — Risk-to-slice traceability

Every register risk must have a slice that owns its control, or it is unmitigated.

| Risk | Owning slices | Validation evidence |
|---|---|---|
| R-01 canonicalisation change post-data | P0.4.1, P0.4.8, P1.9.4 | Typed profile-versioned hashes; rehash plan; `breaking` classification |
| R-02 mis-declared `lens` corrupts authored data | P3.3.2, P3.3.7, P3.3.9 | Law failure = build failure; depth cap; `proposal` default for authored targets |
| R-03 incremental projection divergence (**High**) | P3.1.4, P3.1.7, P2.4.5 | Mandatory reconciliation; injected-divergence test; freshness on every read |
| R-04 behaviour partition poisoned | P3.2.12, P3.2.13, P0.8.4 | Block-and-page; replay tooling; skip unreachable |
| R-05 LLM cost (**High**) | P2.9.2, P2.9.3, P3.6.3 | Cache hit rates; budget enforcement; LLM-disabled coverage measurement |
| R-06 prompt injection | P2.9.7, P2.9.8, P2.9.13 | Intent-only types; candidate-set restriction; adversarial corpus |
| R-07 store cannot meet Decision SLO | P0.5.14, P1.9.3, P3.6.1 | Benchmark in capability report; activation refusal on envelope breach |
| R-08 cross-tenant leakage | P0.5.8, P2.4.2, P2.7.2, P1.7 | Hostile suites at SPI, query, subscription; continuous production canary (P3.5.1) |
| R-09 uncontrolled growth (**High**) | P3.5.4–P3.5.6 | Export-verify-drop saga; cold partitioning; ledger partitioning |
| R-10 uncertainty becomes log noise (**High**) | P2.8.1–P2.8.4 | Same queue/verbs/yield; metric-naming lint; replay-not-repair |
| R-11 two lifecycles drift | P0.3.1, P0.3.4, P1.1.1 | Mapping shapes; single lifecycle in graph |
| R-12 OSS/commercial seam discovered late | P1.11.2, P4.6 | SPI inventory + TCK coverage + sample external adapter |
| R-13 RDF backup weaker than relational | P3.5.3 | Per-adapter RPO/RTO; bundle second line; rehearsed restore |
| R-14 per-store optimistic concurrency subtly wrong | P0.5.2, P0.5.6 | Single `conditionalWrite` primitive; concurrency TCK at N=32 |

---

## Part 12 — Phase gate checklists

**Every phase gate requires all of:**

1. All slice gates in the phase signed off in `docs/validation/LOG.md`.
2. Phase milestone demo executed by a human against a freshly built compose stack from a clean checkout.
3. `docs/traceability/matrix.csv` shows zero claimed-but-untested requirements for the phase's G-nn/C-nn/A-nn set.
4. Every phase ADR ratified; every normative document delta merged.
5. L7 baselines recorded; no unexplained regression.
6. L8 suites for the phase's threat controls green.
7. **Non-weakening audit**: diff the test inventory against the previous phase; any removed, skipped, or loosened test is accounted for in writing.
8. **Cold-start test**: clean machine → clone → one command → stack up → seeded → E2E green. If this takes more than 30 minutes of wall clock or more than one command, the DevEx debt is the gate blocker.

---

## Part 13 — Open questions for you before we start

These genuinely change the plan and I do not want to assume answers.

| # | Question | Impact if the answer differs from my assumption |
|---|---|---|
| 1 | **Do you accept A74 (graph-primary)?** I have assumed yes. | If no: P0.1.1 changes, T-GPM (P1.1, P1.4, P1.5, P1.6) mostly disappears and is replaced by durable-Postgres slices plus the outbox/saga machinery for T5/T6/T9, and roughly 40% of the plan reorders. Decide this first. |
| 2 | **Build tool: Maven (existing) or Gradle?** I put the decision inside P0.2.1. | Affects every module slice trivially, but the agents need one answer, not a debate per slice. |
| 3 | **Reference store binding for the hot path: embedded TDB2 in-process, or Fuseki over HTTP?** The review recommends in-process for the SLOs; the existing Compose stack is remote. | I have planned both adapters in P0.5, with in-process as the reference. If remote-only is a hard operational constraint, the §5.4 SLOs need renegotiating in P0.1.15. |
| 4 | **Coordination default: embedded H2, or Postgres from the start?** | Embedded proves the "no Postgres needed" claim (a real product simplification) but adds an adapter. I have planned both. |
| 5 | **Is the insurance applied ontology (`ontology/examples/insure-o`) an acceptable basis for the synthetic corpus**, or do we need a neutral second domain to prevent domain drift (per `GENAI_CONTRIBUTION.md`'s stated concern)? | If a second domain is required, P0.9.2 roughly doubles and every L5/L6 scenario runs in a matrix. |
| 6 | **Which LLM providers must be supported at M6, and is a local-model-only path a launch requirement or a later tier?** | Drives P2.9.4 scope and the cassette strategy. |
| 7 | **Phase 1 partitioned-queue impl: RabbitMQ consistent-hash plugin or Postgres `SKIP LOCKED`?** I have planned the abstraction plus both, but the agents will want a default. | Low reversibility cost behind the SPI, which is why I planned the abstraction first. |
| 8 | **How many concurrent agent teams and human validators will we actually have?** Part 10 assumes 4–6 streams with 3–4 validators. | Validation throughput is the binding constraint in this process, not agent throughput. If you have one validator, the plan must serialise and phases roughly double in wall-clock time. |
| 9 | **Is `ux-design.md`'s register model (P1.10.4) contentious?** The review flags the MORK UXD Part 12 tension explicitly. | If there is disagreement between UX stakeholders, resolve it in P0.1 as an ADR rather than discovering it at P2.10. |
| 10 | **Do we need a formal DPO/legal review gate on A68 (PII/erasure)?** I have flagged it as recommended in P0.1.7. | If yes, it is an external dependency with lead time and should be initiated on day one, since it blocks the Phase 0 exit gate. |
| 11 | **Request Query Mapping library — deferred until A75 ratification.** A *general-purpose, reusable* runtime library binding an arbitrary live request, a compiled `dal:` template (from `ontology/persistence`), and a store SPI implementation, for any caller. Not designed in `rdf-sparql-patterns-phase` because it needs the SPI (proposed A75) first. See [docs/developer/INDEX.md](../INDEX.md) Part V for current status. | Blocks nothing in Phase 0 or Slice 2 of the patterns phase. **Narrowed by the Phase 2 plan revision (P2.3.1):** C-04's own ingestion write path binds request-scoped parameters into P2.1.4a's pre-instantiated templates itself, without waiting for this library — that is a scoped, C-04-local mechanism, not an instance of this library. This question remains open only for callers *other than* C-04 that would need the same capability (e.g. a future push-gateway-triggered write). Design the general library once A75 is ratified, not before. |
| 12 | **Query Execution component — deferred until A75 ratification.** A component rewriting a compiled `dal:` template's SPARQL dialect for a specific backend at request time, needed because [rdf-sparql-patterns-guide.md](../../architecture/rdf-sparql-patterns-guide.md) Chapter 26 documents real per-backend dialect variance. Deferred for the same reason as row 11, plus the injection-safety question it would reopen if built without the same template discipline `tools/persistence` uses. See [docs/developer/INDEX.md](../INDEX.md) Part V for current status. | Same as row 11, and **unaffected by the Phase 2 plan revision**: P2.3/P2.4 assume the reference store adapters only (TDB2/Fuseki, per P0.5) and perform no dialect rewriting. Design a Query Execution component once A75 is ratified, and design it against the same template and encoder discipline as `tools/persistence`, not as a fresh string-construction path. |

---

## Part 14 — Summary of the critical path

```
P0.1.1/3/4/5/6/8 (irreversible ADRs)
   └─► P0.3.3 (platform vocabulary)
         └─► P0.4.2–P0.4.5 (canonicalisation + hashes)
               └─► P0.5.2/5.7/5.8 (write surface, commit sequence, scoping)
                     └─► P0.5.4–P0.5.6 + P0.5.14 (TCK + benchmark)  ──► M1
                           └─► P1.2 (IRI/lineage) ─► P1.1 (lifecycle in graph) ──► M2
                                 └─► P1.3 (change feed)
                                       └─► P1.8 (pack) ─► P1.9 (activation) ──► M3
                                             └─► P2.1 (C-05 mapping compiler)   ◄── longest pole
                                                   └─► P2.3 (ingestion) ──► M4
                                                         └─► P2.4/P2.5 ──► M5
                                                               └─► P2.9 ──► M6
                                                                     └─► P3.1 (projections) ──► M7
                                                                           └─► P3.2 (tanks) ──► M8
                                                                                 └─► P3.3 ──► M9
```

**Three things on this path deserve disproportionate attention:** P0.4 (canonicalisation — everything downstream is wrong without it), P0.5.8 (scoping hostile suite — the existential security control), and P2.1 (the mapping plan compiler — the largest single piece of missing implementation, which gates Phases 2 and 3 entirely and should be resourced first and most heavily).
