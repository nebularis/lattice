# Amendment 1 to the LATTICE Platform Agentic Development Plan

**Status:** Amendment to *LATTICE Platform — Agentic Development Plan (v0.1)*. Read alongside it; this document replaces the named passages and adds the named slices. It does not restate unchanged material.

**Trigger:** repository compatibility review (`updated-plan-remediation.md`), findings 1–7 plus its four recommendation sections.

**Effect on plan version:** v0.1 → **v0.2**. Plan structure, phase boundaries, milestones M0–M9, and slice ordering are unchanged except where AM-01, AM-07, AM-08, and AM-09 add or relocate work.

---

## 0. Amendment index

| ID | Amends | Closes review finding | Nature |
|---|---|---|---|
| **AM-01** | New Phase 0 gate **P0.0** before all other work | 1, §3 | **Addition** — architecture ratification gate |
| **AM-02** | Part 0, structural commitment #2 | 2 | Restatement |
| **AM-03** | Part 0.4, guardrail **G2** | 3 | Restatement |
| **AM-04** | Part 0.2 slice shape; slices P0.2.1–P0.2.4, P0.9.3, P0.9.5; Part 12 item 8 | 4, §2 | **Toolchain correction** — `mise` sole orchestrator, Maven, Yarn 4 |
| **AM-05** | Part 1 in full | 5, §1 | **Replacement** — logical topology, no filesystem relocation |
| **AM-06** | Part 1 module names; M1; P0.5.3/.11/.12; P0.1.10 | 6 | Naming resolution |
| **AM-07** | P0.3.3; new slice **P0.1.16** | 5 (last bullet) | **Addition** — platform-vocabulary home becomes a decision |
| **AM-08** | P0.1.1 | 1 | Scope extension — explicit ADR supersession |
| **AM-09** | P0.1.9; P1.4; P1.11.1 | 7 | **Relocation** — release/provenance rule made normative earlier |
| **AM-10** | P1.2.3 | §3 | Scope extension — reference migration with alias period |
| **AM-11** | P0.7.6 | 5, §2 | Replacement — extend existing Compose, do not rename |
| **AM-12** | New slice **P0.2.10** | §4 | **Addition** — Copilot instructions update |
| **AM-13** | Part 13 open questions | 4, 5, 6 | Replacement of Q2; three new questions |
| **AM-14** | Editorial sweep list | 4, 5, 6 | Housekeeping |

**New ADR identifiers introduced by this amendment:** A76 (platform ontology vocabulary home), A77 (module naming and path-migration policy). **ADR-A29 is not superseded and must not be.** The Gradle/`make`/`just`/`pnpm` decision previously assigned to ADR-A76 in P0.2.1 is withdrawn, not renumbered.

---

## AM-01 — Add Phase 0 gate P0.0: architecture ratification

**Where.** New slice group inserted at the head of Part 4 (PHASE 0), before P0.1. Renumbering is not required; P0.1 onward keep their identifiers, but **no P0.1+ slice may start until P0.0 is signed off.**

**Why.** The review's §3 conclusion is that the target architecture has a coherent direction but "is not yet internally consistent enough to start implementation without an architecture ratification pass", and lists seven specific amendments required. My plan assumed those could be settled inside the individual ADR slices. Several of them are cross-ADR consistency questions that will otherwise be answered differently in three places.

**Replacement text — insert as the first slice group of Part 4.**

> ### P0.0 — Architecture ratification (T-DEC) — **blocking gate**
>
> **Purpose.** Resolve the seven cross-cutting inconsistencies the repository compatibility review identified, as one coherent pass, before any ADR slice fixes them locally. This group produces documents only. Its exit is a signed architecture ratification record at `docs/architecture/ratification-v1.md`.
>
> | Slice | Scope | Human validation focus |
> |---|---|---|
> | **P0.0.1** | **Realm authority reconciliation.** State the graph-primary authority rule *together with* the artifact-realm exception (AM-03) and the Phase 0 durable-data scope (AM-02) in one section, so the three are mutually consistent. Produce the "where does a fact belong" decision table applied to every entity in `data-architecture.md §2.1` *and* every new entity in the review's A1.4 table, with the chosen realm and the authority class (`authoritative` / `derived-cache` / `derived-operational` / `external-synchronised` / `advisory`) for each | Is any entity assigned a realm that contradicts its authority class? Is any byte-store product (pack, bundle, document blob, compiled artefact) mis-assigned to the graph realm? |
> | **P0.0.2** | **ADR supersession map.** For every accepted ADR A29–A43, state: unaffected / amended / superseded, by which new ADR, and with what migration consequence. Minimum expected entries per the review: A30 (cross-runtime boundary), A33 (revision ledger and optimistic concurrency), A34 (graph-family registry and immutable identity), A39 (PostgreSQL portions), A31 (unaffected — the boundary restatement in the review's §1.1 is an *addition* to §4.4, not a reversal), A29 (**explicitly unaffected**) | Is any ADR left in an ambiguous state? Does any new ADR silently contradict an accepted one without saying so? |
> | **P0.0.3** | **Reference-model and naming resolution.** Settle: (a) the `GraphReference` → `AuthoredGraphReference`/`RuntimeGraphReference` migration shape and its compatibility alias period (AM-10); (b) the design-time authoring graph vs runtime tenant/environment graph distinction, stated *before* `environmentId` exists in code; (c) canonical module and report names (AM-06); (d) the path-migration policy and migration table format (AM-05), as ADR-A77 | Can an implementer read this and produce the same names and the same reference types as another implementer working from it independently? |
>
> **P0.0 exit gate.** `docs/architecture/ratification-v1.md` merged and signed; the supersession map merged into `docs/adr/README.md`; no P0.1 slice references an unresolved item. This gate is cheap in effort and expensive to skip: every finding it resolves is one that would otherwise surface as contradictory code in three modules.

---

## AM-02 — Restate the durable-data commitment

**Where.** Part 0, "Two structural commitments this plan makes", commitment **#2**.

**Why.** Review finding 2. As written, the commitment forbids what Phase 0 itself requires: checked-in ontology files, golden fixtures, Testcontainers-backed L4 tests, and a seeded Compose stack for M0.

**Replacement text — replace commitment #2 in full.**

> 2. **No irreversible semantic record exists before the Phase 0 exit gate.** Precisely: before the gate passes, the system must not create (a) a persistent tenant or environment dataset, (b) any A-Box, provenance, ledger, activation, or runtime-state graph intended to outlive a test run, or (c) any business record whose loss or rewrite would be a data-integrity incident rather than a test-fixture regeneration.
>
>    Expressly **permitted** during Phase 0, because Phase 0 depends on them: checked-in source artefacts (ontology `.ttl`, shapes, contracts, schemas); deterministic, regenerable golden files and fixture corpora; ephemeral stores created and destroyed by Testcontainers or by `mise run up` / `mise run down`; and the seeded, disposable Compose dataset used by M0, which is recreated from `mise run seed` on every run and is never migrated forward.
>
>    The test for "irreversible": *if this artefact were deleted, would it be regenerated by a command, or would it be lost?* Only the second category is gated.

---

## AM-03 — Guardrail G2: add the artifact-realm exception

**Where.** Part 0.4, guardrails table, row **G2**.

**Why.** Review finding 3. As written, G2 forbids the artifact realm, which the plan itself requires for OCI packs (P1.8), export bundles (P1.7.4, P3.5.3), document blobs (P2.9.6), compiled plan artefacts (P2.1), and archived N-Quads generations (P3.5.4).

**Replacement text — replace the G2 row, and add G2a immediately after it.**

| # | Guardrail | Enforcement |
|---|---|---|
| **G2** | **Graph-primary authority with a bounded artifact-realm exception.** The graph realm is authoritative for identity, semantics, provenance, lifecycle, governance, and decision facts. The **artifact realm is authoritative for immutable byte content addressed by digest** (generated output bytes, OCI pack and bundle layouts, source document blobs, archived N-Quads generations, compiler artefacts). The graph is authoritative for *what a digest means, where it came from, and whether it is in force*; the artifact realm is authoritative for *the bytes that digest names*. No third authoritative realm may be introduced: anything persisted in the coordination, stream, or projection-sink realms must be annotated `@Coordination`, `@Stream`, or `@Derived` and be provably reconstructible or safely lossy | ArchUnit annotation check; review checklist; P0.6.4 reconstruction proof; artifact-realm entries must carry a graph-side record (asserted by P2.5.1 provenance-homogeneity audit) |
| **G2a** | **Every artifact-realm object has exactly one graph-resident record** naming its digest, its cause, and its authority class. An artifact with no graph record is an orphan and is reclaimed by the relevant reaper | P3.5.7 reaper registry; orphan-detection test per producing component |

---

## AM-04 — Toolchain: `mise` is the sole orchestrator; Maven and Yarn 4 retained

**Why.** Review finding 4 and §2. ADR-A29 is accepted and implemented: `mise` is the only task/tool-version entry point, with Maven, Yarn, pip/uv, and Mix retaining dependency ownership. The plan proposed a second task runner (`make`/`just`), a second JavaScript package manager (`pnpm`), and left the Java build tool open. All three are withdrawn.

### AM-04.1 — Part 0.2, slice shape, item 2

**Where.** Part 0.2, "The mandatory shape of every slice", bullet 2, sub-bullet *"One command to run everything"*.

**Replacement text.**

> - *One command to run everything*: **`mise run verify-slice -- <slice-id>`**. `mise` is the only task-runner authority in this repository (ADR-A29). A slice that requires a second command, a raw `mvn`/`yarn`/`pytest` invocation, or a task defined anywhere other than `mise.toml` is rejected on process grounds. `mise` tasks contain **dispatch only** — no build logic, no conditionals beyond tool selection; the logic lives in the Maven reactor, the Yarn workspace scripts, or the Python project.

### AM-04.2 — Part 0.3, level L0 description

**Where.** Part 0.3 test taxonomy, row L0.

**Replacement text for the L0 row's Name column.**

> **L0** | Build smoke: `mise run bootstrap` on a clean checkout, then `mise run verify` green, including a no-op test per module

### AM-04.3 — Slices P0.2.1, P0.2.2, P0.2.3

**Where.** Part 4, P0.2 table, first three rows.

**Replacement text — replace all three rows.**

| Slice | Scope | Tests / validation |
|---|---|---|
| **P0.2.1** | **Extend the existing Maven reactor.** Add the new Java modules of AM-05 to `platform/pom.xml` as reactor members; add or extend `platform/lattice-bom` for shared dependency management; confirm the Java 21 toolchain; one no-op test per new module. **No build-tool change: Maven is settled by ADR-A29 and the existing reactor, and the Gradle question is withdrawn.** Add `mise` tasks `verify`, `verify-slice`, `bootstrap`, `bench`, `approve-goldens` as dispatch-only wrappers, and document them in `mise run help` output | **L0**: `mise run bootstrap && mise run verify` green from a clean container; every new module has a passing no-op test; a task defined outside `mise.toml` fails a lint check |
| **P0.2.2** | **Extend the existing `workers/` Python project.** New Python components land as sub-packages of `lattice_workers` (see AM-05) unless a separate deployment unit justifies a separate distribution, in which case it is added to the existing workspace and to the existing bootstrap/test tasks. Enforce `ruff` and `mypy --strict` on new packages only; no-op test | **L0**: existing `mise` Python tasks unchanged and still green; new package discovered by the existing test task without a new runner |
| **P0.2.3** | **Extend the existing Yarn 4 workspace.** Add `packages/ui-kit`, `packages/client-ts`, and `apps/ops-console` as workspaces. **Yarn 4 is retained; `pnpm` is withdrawn.** Every new workspace must expose the `check`, `build`, and `test` scripts the root Yarn commands already invoke. Install Vitest and Playwright at the workspace root | **L0**: root `check`/`build`/`test` fan out to the new workspaces without editing the root commands; `packageManager` and the lockfile are unchanged in kind; a workspace missing a required script fails the root command with a named error |

### AM-04.4 — P0.2.4 codegen slice

**Where.** P0.2.4, Scope column, after "…OpenAPI → server route stubs + TS client".

**Insert.**

> Codegen is wired as a Maven plugin execution (Java), a Yarn workspace script (TS), and a step in the existing Python task (Python), each reachable only through `mise run codegen` / `mise run verify`. No standalone generator script and no second task graph.

### AM-04.5 — P0.9.3 and P0.9.5 command names

**Where.** P0.9.3 Tests column and P0.9.5 Scope column.

**Replacements.**

- P0.9.3: `make approve-goldens` → **`mise run approve-goldens`**.
- P0.9.5: `make seed SCENARIO=...` → **`mise run seed -- SCENARIO=...`**.

### AM-04.6 — Part 12, gate checklist item 8

**Replacement text.**

> 8. **Cold-start test**: clean machine → clone → `mise run bootstrap` → `mise run up` → `mise run seed` → `mise run e2e` green. Four `mise` invocations, no other tooling installed by hand beyond `mise` itself. If this exceeds 30 minutes wall clock, the DevEx debt is the gate blocker.

### AM-04.7 — Optional convenience wrapper

**Where.** New note at the end of Part 0.2.

**Insert.**

> **Convenience wrappers.** A `Makefile` or `justfile` may exist **only** as a thin alias layer that forwards to `mise run <task>` verbatim, adds no task definitions, and is excluded from the VP "one command" requirement (which always names the `mise` form). If a wrapper ever contains logic, it is deleted. Default position: do not add one.

---

## AM-05 — Part 1 replaced: logical module topology, not filesystem relocation

**Where.** Part 1, "Target module topology", in full.

**Why.** Review finding 5 and §1. The proposed tree omitted current top-level areas (`applied/`, `surface/`, `tools/`, `examples/`, `governance/`, and the root ontology layers), and renamed four active path families with ~200 documentation and configuration references behind them, for no runtime benefit. The conceptual separation it expressed (graph SPI, coordination SPI, pack/activation, runtime host, generated clients) is retained as a **module topology** mapped onto existing roots.

**Replacement text — replace Part 1 in full.**

> ## Part 1 — Target module topology (logical, mapped onto existing roots)
>
> **Rule 1 — additive by default.** This plan adds modules and workspaces. It does not relocate or rename existing roots, applications, or Maven modules. Where a name reads oddly after the architecture change (e.g. `semantic-dataset-*` now carrying the system of record), the name is retained and its *documentation* is updated. Package names, artifact IDs, and public report names may evolve independently of directory names.
>
> **Rule 2 — no move without a migration slice.** If a rename or relocation is later judged necessary, it is its own slice, gated on ADR-A77, and must ship a migration table with: old path, new path, owner, compatibility alias period, affected manifests (`mise.toml`, `.devcontainer/devcontainer.json`, `platform/pom.xml`, root `package.json`, workers project, CI workflows), and affected documentation files enumerated exhaustively. No mixed move-and-feature slices.
>
> **Rule 3 — the four withdrawn renames.** `deployment/` stays `deployment/`. `apps/surface-contract-studio` and `apps/mork-review-workbench` keep their directory names. `platform/semantic-dataset-*` keeps its prefix. Root ontology layers are **not** moved under an `ontology/` wrapper.
>
> ### 1.1 Preserved roots (unchanged in role and path)
>
> `foundation/`, `vocabulary/`, `quantification/`, `party/`, `eligibility/`, `instrument/`, `behaviour/` — ontology layers, per the existing layer template.
> `surface/`, `mork/`, `spc/`, `applied/`, `examples/`, `governance/`, `tools/` — unchanged in role; `governance/shapes/` gains content (P0.3.5, P0.3.6).
> `contracts/`, `platform/`, `workers/`, `apps/`, `packages/`, `deployment/`, `docs/`, `.devcontainer/`, `.github/`.
>
> ### 1.2 Java modules to add to the existing `platform/pom.xml` reactor
>
> | Module | Component | Status |
> |---|---|---|
> | `platform/lattice-bom` | Shared dependency management | Add or extend |
> | `platform/canonical-hash` | C-11 + CLI | New |
> | `platform/semantic-dataset-spi` | A75 Core + Extended interfaces, `Capabilities`, `CommitMetadata` | **Extend existing** |
> | `platform/semantic-dataset-tck` | Conformance + benchmark kit | New |
> | `platform/semantic-dataset-tdb2` | Reference in-process adapter | New |
> | `platform/semantic-dataset-fuseki` | Reference remote adapter | **Extend existing** |
> | `platform/coordination-spi`, `-h2`, `-postgres` | Coordination realm | New |
> | `platform/semantic-policy` | A66 extended `Principal` | **Extend existing** |
> | `platform/platform-outbox` | Commit-marker + coordination outbox | **Extend existing** |
> | `platform/partitioned-queue-spi`, `-rabbit`, `-pg` | A59 | New |
> | `platform/surface-workflow`, `platform/release-integration` | Re-based graph-primary | **Extend existing** |
> | `platform/mork-review`, `platform/governance-ledger` | Graph-resident review and governance | New |
> | `platform/tenancy` (C-17), `platform/pack-builder` (C-01), `platform/activation-controller` (C-02), `platform/change-feed` (C-08) | Deployment plane | New |
> | `platform/reasoning-validation` (C-13), `platform/plan-ir`, `platform/ingestion-gateway` (C-04) | Ingestion plane | New |
> | `platform/query-plane` (C-12), `platform/lineage` (C-19), `platform/metering` (C-16), `platform/push-gateway` (C-18), `platform/feedback-router` (C-15) | Query and feedback planes | New |
> | `platform/projection-engine` (C-07), `platform/behaviour-engine` (C-09), `platform/writeback` (C-10) | Operation plane | New |
> | `platform/runtime-host` | Single artifact, `LATTICE_ROLE=control\|edge\|projection\|behaviour` (A50); supersedes the never-created `platform/surface-control-plane` named in `solution-design-specification.md §4.2`, which is renamed in the same slice as the A44 amendment | New |
> | `platform/testkit`, `platform/synth` | Harnesses, fixtures, Compose helpers, synthetic data CLI | New |
> | `platform/client-java` | Java SDK (C-20) | New |
>
> ### 1.3 Python
>
> All new Python components land **inside the existing `workers/` project** as sub-packages — `lattice_workers.mapping_plan_compiler` (C-05), `lattice_workers.content_pipeline` (C-06), `lattice_workers.agent_orchestrator` (C-14), `lattice_workers.client` (Python SDK) — so the existing bootstrap and test tasks keep working unchanged. A separate distribution is created only where a separate deployment unit and release cadence genuinely require it, decided per component at its skeleton slice and recorded in its VP.
>
> ### 1.4 Frontend
>
> `apps/surface-contract-studio` (existing), `apps/mork-review-workbench` (existing), `apps/ops-console` (new) — all Yarn 4 workspaces.
> `packages/ui-kit` (C-20), `packages/client-ts` (C-20) — new workspaces in the existing `packages/` root.
>
> ### 1.5 Contracts, deployment, docs
>
> `contracts/` gains `pack/`, `plan/`, `projection/`, `query/`, `lineage/`, `hash/`, `fixtures/` alongside existing `events/`, `surface/`, `mork/`, `openapi/`.
> `deployment/compose/docker-compose.yml` is **extended in place**; `deployment/images/` and `deployment/seeds/` are added as siblings.
> `docs/` gains `validation/`, `traceability/`, `runbooks/`; `docs/architecture/` gains `iri-policy.md`, `nfr.md`, `nfr.yaml`, `ratification-v1.md`.
>
> ### 1.6 Ontology home for the platform vocabulary
>
> **Open — decided by ADR-A76 in slice P0.1.16 (AM-07).** No directory is created for it until that ADR is ratified.

---

## AM-06 — Canonical module and report names

**Where.** Part 1 (handled by AM-05); milestone **M1**; slices **P0.5.3**, **P0.5.11**, **P0.5.12**; slice **P0.1.10**.

**Why.** Review finding 6: the plan's topology said `graph-spi-tck` while M1 said `semantic-dataset-tck`. Combined with finding 5, the resolution is to keep the existing prefix everywhere.

**Replacements.**

| Plan location | Old | New |
|---|---|---|
| Part 1, M1, P0.5.* | `graph-spi` | **`semantic-dataset-spi`** (existing module, extended) |
| Part 1 | `graph-spi-tck` | **`semantic-dataset-tck`** — also the public, published report name |
| Part 1, P0.5.3, P0.5.11 | `graph-adapter-tdb2` | **`semantic-dataset-tdb2`** |
| Part 1, P0.5.12 | `graph-adapter-fuseki` | **`semantic-dataset-fuseki`** (existing module, extended) |
| Part 1 | `runtime-host` | **`platform/runtime-host`** — confirmed, with the `surface-control-plane` rename handled in P0.1.10 |

**P0.1.10 scope addition.** Append to the Scope cell:

> Also resolves module naming: A44's amendment renames the never-created `platform/surface-control-plane` to `platform/runtime-host` and edits `solution-design-specification.md §4.2` in the same slice, since A50 makes the module role-profiled rather than Surface-specific. The canonical names of AM-06 are recorded here so CI and documentation never reference a withdrawn name.

**Validation addition for P0.1.10.** Add to the Tests column: *a grep-based CI check fails on any occurrence of `graph-spi`, `graph-spi-tck`, `graph-adapter-*`, or `surface-control-plane` outside this ADR's own history section.*

---

## AM-07 — Platform vocabulary home becomes an explicit decision

**Where.** (a) New slice **P0.1.16** appended to the P0.1 decision table. (b) Slice **P0.3.3**, Scope column.

**Why.** Review finding 5, last bullet: moving all ontology layers under an `ontology/` wrapper offers little value and breaks many imports and documentation links; the platform vocabulary needs "an explicitly agreed home consistent with the existing layer architecture". My P0.3.3 assumed `ontology/platform/` and must not.

**Replacement text — new row in the P0.1 table.**

| Slice | Deliverable | Human validation focus | Executable consequence |
|---|---|---|---|
| **P0.1.16** | **ADR-A76: home for the platform vocabulary** (`lattice:authority`, `lattice:commitSeq`, `lattice:transactionTime`, `lattice:ProvenanceScope`, `lattice:cause`, `lattice:packDigest`, `lattice:generationProfileId`, `lattice:writeBackState`, `lattice:version`, `lattice:lifecycleState`). Three named options, one chosen: **(i) a Foundation extension module** — `foundation/spec/foundation-derivation.ttl` plus an optional import, which is the direction `ontology-architecture.md §10` already anticipates (`fnd:DerivedArtefact`, `fnd:derivedFrom`, `fnd:GenerationProfile`) and which keeps the layer count stable; **(ii) a new root-level substrate layer** following the per-layer template, named to avoid collision with the `platform/` Maven root (e.g. `provenance/`); **(iii) split** — hash/derivation terms into Foundation per (i), operational terms (`commitSeq`, `cause`, `writeBackState`, `lifecycleState`) into (ii). Recommendation: **(iii)**, because hash and derivation identity are genuinely Foundation-level and demanded by `§10`, whereas commit sequence and write-back state are platform mechanics that should not enter the ontology substrate every adopter imports | Does the chosen home respect the strict downward-dependency rule? Does any platform term leak into a layer that must not depend on platform mechanics? Does the layer dependency diagram in `ontology-architecture.md §1` still hold? | P0.3.3 directory creation; layer dependency test |

**P0.3.3 Scope replacement (first clause only).**

> Author the platform vocabulary **in the home decided by ADR-A76 (P0.1.16)** — literate spec with `turtle-spec` fences plus mechanically extracted compiled Turtle, per the repository's existing convention — declaring: `lattice:authority` (5 values), `lattice:commitSeq`, … *(remainder of the original scope unchanged)*.

**P0.3.3 dependency note.** Add: *blocked by P0.1.16; may not create a directory speculatively.*

---

## AM-08 — P0.1.1 must state ADR supersession explicitly

**Where.** Slice **P0.1.1**, Deliverable and Human-validation-focus cells.

**Why.** Review finding 1: graph-primary is a deliberate replacement of the accepted three-realm model, ADR-A33's PostgreSQL lifecycle ledger, and ADR-A34's registry. The plan placed the rewrite correctly but did not require the supersession to be named, which would leave two accepted-and-contradictory ADR sets in the catalogue.

**Replacement text for the P0.1.1 row.**

| Slice | Deliverable | Human validation focus | Executable consequence |
|---|---|---|---|
| **P0.1.1** | **ADR-A74 graph-primary realm model**, which must contain an explicit supersession section naming, at minimum: **ADR-A33** (surface revision ledger and optimistic concurrency) — superseded as to storage realm, **preserved as to the `expectedVersion`/`409` contract**, which P1.1.2 must not change; **ADR-A34** (graph-family registry and immutable identity) — superseded as to enforcement mechanism, preserved as to intent, with uniqueness becoming structural per A51; **ADR-A30** (cross-runtime boundary) — amended where it assumes a PostgreSQL system of record; **ADR-A39** — PostgreSQL portions superseded; **ADR-A31** — **unaffected**, with the review's boundary restatement added to `§4.4` as an addition, not a reversal; **ADR-A29** — **unaffected**. Plus the rewrite of `data-architecture.md §1–§3, §5–§7` incorporating the artifact-realm exception (AM-03) and the Phase 0 durable-data scope (AM-02) as ratified in P0.0.1 | Is every contradicted ADR named? Is A33's concurrency contract preserved verbatim while its storage realm changes? Does the rewritten `§5` still contain the seven original concurrent-access rules in equivalent form, plus new rule 8 (no direct store access)? | ArchUnit G2/G2a; `docs/adr/README.md` supersession map updated in the same slice |

---

## AM-09 — Release publish classification and the T5 rule become normative in Phase 0

**Where.** (a) Slice **P0.1.9**, Deliverable cell — extend. (b) Slice group **P1.4** — add a dependency note. (c) Slice **P1.11.1** — remove one item.

**Why.** Review finding 7: `solution-design-specification.md §2.2` and process map P3 contradict each other on release publish, and P3 shows an unprotected PostgreSQL→Fuseki dual write. The review's instruction is to make the replacement rule normative **before** the release ledger is retained or migrated. My plan put the §2.2 fix in P1.11.1, a close-out documentation slice that runs *after* P1.4 migrates the ledger.

**P0.1.9 Deliverable replacement.**

> **ADR-A48 (replace): transaction boundary catalogue.** T1–T12 enumerated with mechanism, residual risk, and detector; the three rules stated normatively in `solution-design-specification.md §7.2` — *no unprotected dual write*, *content addressing is what makes sagas safe*, *every saga has a named reaper*. **Additionally, and in this slice:** (a) resolve G-21 by reclassifying release publish in `§2.2` as **synchronous with a bounded deadline** (30 s soft, 120 s hard), deleting the "background operation" language, and making P3 in `§2.4` agree with the table; (b) state that if signing or registry push is enabled, that specific step becomes a job on `lattice.release.publish` with the receipt recorded on completion; (c) state the T5 rule normatively — **every PostgreSQL→RDF-store write, and under A74 every operation spanning the graph and any other realm, goes through the outbox or a named saga**, and the `§5.3` provenance alert is redefined from an expected race into a genuine anomaly detector.

**P1.4 dependency note — insert above the P1.4 table.**

> **Blocked by P0.1.9.** No release-ledger migration slice may start until the publish classification and the T5 rule are ratified, because P1.4.2 deletes the dual write and must delete it *against a normative rule*, not against an inference from a review document.

**P1.11.1 replacement.** Remove `§2.2 (G-21 publish deadline)` from the list, since AM-09 moves it to P0.1.9. The remaining scope is:

> Update `solution-design-specification.md` §1 (NFR/tenancy/OSS columns + runtime rows), §4.1, §4.5 (extended topology with ordering classes), §4.6 (four missing failure modes from G-25), and confirm §7.2 matches what P0.1.9 ratified and what Phase 1 actually built.

---

## AM-10 — P1.2.3 expanded: reference migration with a compatibility alias period

**Where.** Slice **P1.2.3**.

**Why.** Review §3 requires the `GraphReference` → `AuthoredGraphReference`/`RuntimeGraphReference` migration to be *specified*, and requires the design-time vs runtime graph distinction to be preserved before `environmentId` lands. A one-line "replace the type" slice is not sufficient for a type that appears across two runtimes and every contract.

**Replacement text for the P1.2.3 row, plus a new P1.2.4.**

| Slice | Scope | Tests |
|---|---|---|
| **P1.2.3** | **Reference type migration, per the ADR-A77 alias policy ratified in P0.0.3.** Introduce `AuthoredGraphReference(tenant, project, revisionIri, verificationHash)` and `RuntimeGraphReference(tenant, environment, graphIri, generation)`. `GraphReference` is retained as a **deprecated alias** for the authored form for one declared phase (through end of Phase 1), annotated `@Deprecated(forRemoval)` with the removal slice named in the annotation. Wire contracts carry both shapes during the window, with the schema-compatibility gate (P0.2.6) proving the addition is backward-compatible. `revisionHash` is demoted to a verification field; `GraphMaterializer`'s SHA-256 check now verifies exactly what it claims | **L1/L3/L4**: a mismatched revision hash raises `GraphMaterializationError` before any compiler invocation; a runtime reference cannot be used where an authored one is required (type-level); the deprecated alias is used by **zero** new call sites (CI check); the cross-runtime fixture corpus validates in both directions during the window |
| **P1.2.4** | **Authoring/runtime graph separation stated and enforced before `environmentId` exists in tenancy code.** Design-time authoring graphs are `project`-scoped and never carry an environment segment; runtime graphs are `environment`-scoped per the A54 layout convention. A graph name carrying both, or neither, is rejected by the P0.3.7 validator | **L1/L8**: every family in the layout table is classified authoring or runtime, exhaustively; a cross-classified name is rejected; an authoring graph cannot be written through a runtime write path (typed) |

**Dependency note.** P1.7 (tenancy) is blocked by P1.2.4, not merely sequenced after it.

---

## AM-11 — P0.7.6 replaced: extend the existing Compose stack

**Where.** Slice **P0.7.6**.

**Why.** Review finding 5 and §2: `deployment/compose/docker-compose.yml` is hard-coded in both `mise.toml` and `.devcontainer/devcontainer.json`, plus numerous documentation references. Renaming it to `deploy/compose` buys nothing.

**Replacement text for the P0.7.6 row.**

| Slice | Scope | Tests |
|---|---|---|
| **P0.7.6** | **Extend `deployment/compose/docker-compose.yml` in place.** Add the control-plane (`platform/runtime-host`) service and the worker service as containerised units with health checks — the step `solution-design-specification.md §5.1` already identifies as required before the pilot can run end to end. Add the dev OIDC issuer and static app hosting. Keep existing service names, volumes, and the file path unchanged; keep `mise.toml` and `devcontainer.json` references unedited. New images are built from `deployment/images/`. Lifecycle is `mise run up` / `mise run down` / `mise run logs`, extending the existing tasks rather than adding new ones | **L5**: cold start to green health checks inside a stated time budget; readiness reflects dependency reachability (PostgreSQL/coordination, broker, Fuseki); `.devcontainer` still opens and runs the stack with no edits; a `git grep` for `deploy/compose` returns nothing |

---

## AM-12 — New slice P0.2.10: update the Copilot instructions

**Where.** New final row of the P0.2 table.

**Why.** Review §4: the plan is broadly compatible with `.github/copilot-instructions.md`, but the instructions must be updated *after ratification* to make the new process enforceable — otherwise agents will follow the older, weaker contract.

**Replacement text — new row.**

| Slice | Scope | Tests / validation |
|---|---|---|
| **P0.2.10** | **Update `.github/copilot-instructions.md`** to make the v0.2 process enforceable. Required edits: (1) an implementation slice must ship `docs/validation/<slice-id>.md` in the prescribed Validation Pack shape; (2) it must ship a `docs/traceability/matrix.csv` row and an explicit *deliberate non-coverage* statement; (3) **`mise` remains the only task-runner authority unless ADR-A29 is superseded** — agents must not introduce `make`, `just`, Gradle, or `pnpm`; (4) once A74 is accepted, add the graph-primary authority rule **and** the G2a artifact-realm exception; (5) agents must stop for human architectural guidance at every decision slice (already required in principle — made explicit); (6) replace the blanket "all listed architecture documents must be updated" wording with "update each *affected* normative document", retaining the existing minimum set for cross-cutting changes. **Blocked by P0.0 and by P0.1.1** — the instructions must not encode an unratified rule | Human review against the ratification record; a deliberate probe: ask a fresh agent session to add a `justfile` task and confirm it refuses and cites A29 |

---

## AM-13 — Part 13 open questions revised

**Where.** Part 13, question **2** (replaced) and three additions.

**Q2 is withdrawn.** Replacement text for the row:

| # | Question | Impact |
|---|---|---|
| 2 | ~~Build tool: Maven or Gradle?~~ **Closed.** Maven, per ADR-A29 and the existing `platform/pom.xml` reactor. Yarn 4 for the JS workspace, `mise` as the sole orchestrator. No further decision required | — |

**New questions to append.**

| # | Question | Impact if the answer differs from my assumption |
|---|---|---|
| 11 | **Do you accept AM-05's additive-topology rule, or do you want a renaming programme?** I have assumed additive, with ADR-A77 governing any later move. | If you want the renames (`deployment`→`deploy`, app shortnames, `semantic-dataset-*`→`graph-*`), each becomes its own migration slice with the full migration table, and roughly 200 path references must be swept. That is a phase's worth of churn with no runtime benefit; I recommend against it, but it is your call and it is cheaper now than in Phase 3. |
| 12 | **Which ADR-A76 option for the platform vocabulary home?** I recommend option (iii), the split. | Option (ii) adds an eighth root layer and changes the layer dependency diagram every downstream document cites. Option (i) puts operational mechanics into the substrate every adopter imports. Decide in P0.1.16, not later. |
| 13 | **What is the compatibility alias period for `GraphReference`?** I have assumed "through end of Phase 1". | A longer window means the dual-shape wire contract lives longer and the Python side carries both types into Phase 2; a shorter one means P1.2.3 must land before any Phase 1 consumer is written. |
| 14 | **Is ADR-A31 genuinely unaffected by A74?** I have assumed yes — the review's boundary restatement is an addition to `§4.4`. | If A31 is read as also owning the *artifact realm's* lifecycle, then AM-03's exception needs A31's explicit endorsement, and retention of packs/bundles becomes a LATTICE concern rather than the release stack's. Settle in P0.0.2. |

---

## AM-14 — Editorial sweep (mechanical, one slice)

**Where.** Fold into **P0.2.10** as a second deliverable, or run as a standalone slice **P0.2.11** if you prefer a clean separation.

**Why.** Findings 4, 5, and 6 leave withdrawn names scattered through v0.1. These must be corrected in the plan document itself before agents read it, or they will be implemented.

**Sweep list — every occurrence in the plan document to be corrected.**

| Withdrawn token | Occurs in | Replace with |
|---|---|---|
| `./gradlew …`, `make …`, `just …` | Part 0.2 item 2; P0.9.3; P0.9.5; P0.7.6; Part 12 item 8 | `mise run …` per AM-04 |
| `pnpm` | P0.2.3 | Yarn 4 workspace |
| "Maven or Gradle — decide in this slice, record as ADR-A76" | P0.2.1 | Deleted; A76 reassigned by AM-07 |
| `deploy/compose`, `deploy/images`, `deploy/seeds` | Part 1; P0.7.6 | `deployment/compose`, `deployment/images`, `deployment/seeds` |
| `apps/surface-studio`, `apps/mork-bench` | Part 1 | `apps/surface-contract-studio`, `apps/mork-review-workbench` |
| `graph-spi`, `graph-spi-tck`, `graph-adapter-tdb2`, `graph-adapter-fuseki` | Part 1; M1; P0.5.1/.3/.10/.11/.12/.13; Part 14 | `semantic-dataset-spi`, `-tck`, `-tdb2`, `-fuseki` |
| `ontology/` wrapper containing existing layers | Part 1 | Layers stay at root (AM-05 §1.1) |
| `ontology/platform/` | Part 1; P0.3.3 | Home decided by ADR-A76 (AM-07) |
| `workers/mapping_plan_compiler/` etc. as sibling roots | Part 1 | `lattice_workers.*` sub-packages (AM-05 §1.3) |
| `clients/client-java`, `clients/client-python` as a new root | Part 1 | `platform/client-java`; `lattice_workers.client` |
| `platform/surface-control-plane` (implied by spec §4.2) | Part 1 | `platform/runtime-host`, renamed in P0.1.10 |

**Validation for the sweep.** A CI grep gate over `docs/developer/current/Updated-Plan.md` and all VPs failing on any withdrawn token. This is the cheapest possible guard against the plan itself being the source of the drift.

---

## 1. Net effect on schedule and ordering

| Change | Effect |
|---|---|
| AM-01 adds P0.0 (3 document slices) | ~3–5 validation-days added at the front. Bought back immediately by AM-04 and AM-05, which delete the build-tool decision and the entire path-migration workstream |
| AM-05 withdraws the relocation | Removes a large, invisible cost that v0.1 had not budgeted at all (≈200 path references across manifests, CI, devcontainer, and docs) |
| AM-07 adds P0.1.16 and blocks P0.3.3 | Half a day of decision work; P0.3.3 was not on the critical path ahead of P0.4 by more than that |
| AM-09 moves the G-21/T5 rule earlier | No net change to effort; changes ordering so P1.4 is no longer built against an unratified rule |
| AM-10 splits P1.2.3 and adds P1.2.4 | One slice added; P1.7 now blocked by P1.2.4 |
| AM-12 adds P0.2.10 | One slice; must run after P0.0 and P0.1.1 |

**Critical path (Part 14) is unchanged in shape.** It now begins one gate earlier:

```
P0.0 (ratification) ─► P0.1.1/3/4/5/6/8/16 (ADRs) ─► P0.3.3 ─► P0.4 ─► P0.5 ─► M1 ─► …
```

The three slices deserving disproportionate attention are unchanged: **P0.4** (canonicalisation), **P0.5.8** (scoping hostile suite), **P2.1** (mapping plan compiler). **P0.0** now joins them as the cheapest high-leverage gate in the plan.