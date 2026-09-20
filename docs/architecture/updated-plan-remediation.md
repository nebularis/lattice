I’ll compare the proposed topology and plan against the repository’s actual build, tooling, documentation, and instruction surfaces, then separate confirmed incompatibilities from decisions that are merely costly.

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/mise.toml)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/package.json)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/pom.xml)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/README.md)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/pyproject.toml)

Read memory

The current repository is a mixed Maven, Yarn, Python, Erlang, and Compose workspace. The proposed topology would rename or replace several active roots, so I’m now tracing those paths and the governing ADR/document rules to distinguish harmless additions from breaking moves.

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/adr)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/developer)

Searched for regex `deployment/compose|apps/(mork-review-workbench|surface-contract-studio)|platform/(semantic-dataset|surface-workflow|release-integration)|workers/|mork/|spc/` (`**/{mise.toml,package.json,README.md,docs/**/*.md,.github/**/*.md,platform/**/*.xml}`), 204 results

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/architecture/data-architecture.md)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/.github/copilot-instructions.md)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/adr/README.md)

The main compatibility risks are concrete, not speculative: the new plan names `deploy/`, `pnpm`, and renamed applications, while the checked-in orchestration contract uses compose, Yarn 4, and the current application names. I’m checking the accepted toolchain ADR and build/development configuration next, then I’ll assess the deeper architectural contradictions.

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/adr/ADR-A29-repository-toolchain-and-environment-boundary.md)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/adr/ADR-A30-shared-semantic-platform-cross-runtime-boundary.md)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/adr/ADR-A31-release-stack-neutral-integration-contract.md)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/developer/toolchain.md)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/.devcontainer/devcontainer.json)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/workers/pyproject.toml)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/deployment/compose/docker-compose.yml)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/apps/surface-contract-studio/package.json)

The existing accepted ADRs make `mise` the sole task and tool-version entry point, while native Maven, Yarn, pip, and Mix retain dependency ownership. The updated plan can preserve that model, but its proposed `pnpm` workspace and a second `make`/`just` runner would violate it unless the plan is amended. I’m doing one final targeted pass for line-level evidence on topology, lifecycle ownership, and plan sequencing.

Searched for regex `ontology/|deploy/|pnpm|make|just|Nothing writes durable|Maven or Gradle|graph-primary|graph-spi|semantic-dataset|surface-studio|mork-bench|platform-outbox|coordination` (`**/docs/developer/current/Updated-Plan.md`), 54 results

Searched for regex `PostgreSQL|sole writer|One JVM process|in-process|provenance|async from the caller|Polling|single-tenant|Control Plane` (`**/docs/architecture/solution-design-specification.md`), 89 results

Searched for regex `PostgreSQL|authoritative|single writer|GraphReference|Fuseki|outbox|provenance` (`**/docs/architecture/data-architecture.md`), 27 results

Searched for regex `docs/validation|traceability|Validation Pack|Phase 0|human validation|run build|test|Default mode|Design First|ADR` (`**/.github/copilot-instructions.md`), 10 results

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/architecture/implementation-map.md)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/developer/current/README.md)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/adr/ADR-A33-surface-revision-ledger-and-optimistic-concurrency.md)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/adr/ADR-A34-surface-graph-family-registry-and-immutable-identity.md)

**Findings**

1. **The graph-primary decision is a deliberate architectural replacement, not an additive plan.**  
   Updated-Plan.md makes RDF the system of record and PostgreSQL disposable coordination. This directly contradicts the current three-realm model in data-architecture.md, the PostgreSQL lifecycle ledger in ADR-A33, and the graph registry in ADR-A34. It is viable, but ADR-A74 must explicitly supersede or amend those decisions before implementation begins. The plan correctly places that in P0.1.1, but it cannot be treated as already aligned.

2. **“Nothing writes durable data until Phase 0 exit” needs a narrower definition.**  
   The plan also creates durable source artifacts, ontology files, golden fixtures, and tests against real stores during Phase 0. Its own P0.3, P0.5, P0.8, and P0.9 depend on this. Amend the rule to: *no persistent tenant or production semantic dataset, nor irreversible business/runtime record, before the exit gate*. Disposable Testcontainers, checked-in source files, and reproducible fixtures should be expressly allowed.

3. **The “no new authoritative store” guardrail conflicts with required artifact and document storage.**  
   Updated-Plan.md permits only coordination or derived persistence outside the graph, while the plan still needs OCI packs, exported bundles, document blobs, and compiler artifacts. These are authoritative byte stores, even where graph records are authoritative for their semantics. Define an explicit **artifact realm exception**: graph facts are authoritative for identity, provenance, and lifecycle, while immutable artifact bytes are authoritative for their content addressed by digest.

4. **The proposed toolchain changes are inconsistent with the accepted repository contract.**  
   P0.2.1 proposes `make` or `just`, and P0.2.3 proposes `pnpm` (Updated-Plan.md). Accepted ADR-A29 assigns orchestration to `mise`, with Maven, Yarn, pip, and Mix as dependency authorities. The root mise.toml and package.json implement that decision today. Do not introduce both a second task runner and a second JavaScript package manager.

5. **The proposed physical topology is incomplete and costly to apply as written.**  
   It omits current top-level areas including applied, surface, tools, examples, and the existing root ontology layers. It also renames active paths:
   - deployment to `deploy/`
   - surface-contract-studio to `apps/surface-studio/`
   - mork-review-workbench to `apps/mork-bench/`
   - `semantic-dataset-*` to `graph-*`

   The repository has at least 200 path references across documentation and configuration. implementation-map.md and README.md are only a visible fraction. The move creates churn without an equivalent runtime benefit.

6. **There is one naming inconsistency inside the new plan.**  
   Its module topology calls the conformance project `graph-spi-tck`, while M1 requires `semantic-dataset-tck` (Updated-Plan.md, Updated-Plan.md). Choose one public module and report name before code or CI references it.

7. **The current solution specification already has a known internal contradiction that the review identifies correctly.**  
   Release publishing is described as async in solution-design-specification.md, but P3 returns the receipt synchronously and performs an unprotected PostgreSQL then Fuseki dual write. The review’s transaction-boundary catalogue and outbox proposal are directionally correct. Make the replacement rule normative before retaining or migrating the release ledger.

**1. Folder structure**

The structure helps conceptually, especially the separation of graph SPI, coordination SPI, pack activation, runtime host, and generated client artifacts. I would adopt it as a **logical/module topology**, not a wholesale filesystem relocation.

Recommended approach:

- Keep existing roots: foundation, vocabulary, quantification, party, eligibility, instrument, behaviour, surface, mork, spc, applied, tools, workers, platform, apps, contracts, and deployment.
- Add the new Java modules under the existing platform Maven reactor.
- Add `packages/` and `clients/` without moving existing apps.
- Preserve surface-contract-studio and mork-review-workbench. Package names can evolve independently of directory names.
- Preserve compose. Do not rename it to `deploy/` unless there is a strong operational reason.
- Treat `ontology/platform/` as an open design choice. Moving all existing ontology layers under an `ontology/` wrapper offers little value and would break many imports and documentation links. A dedicated platform vocabulary can instead have an explicitly agreed home consistent with the existing layer architecture.

Before any move, create a migration table containing old path, new path, owner, compatibility alias period, affected manifests, and affected documentation. That turns an expensive broad rewrite into controlled migration slices.

**2. `mise` and local tools**

`mise` will continue to work with additive modules because it dispatches to native tools. The risk is hard-coded paths and competing authorities.

- The Java reactor is explicitly pom.xml. New Java modules work once added to that reactor.
- `apps/*` and `packages/*` are already Yarn workspaces, so adding `packages/ui-kit` and `packages/client-ts` is compatible. Each new workspace must provide the `check`, build, and test scripts expected by the root Yarn commands.
- workers remains compatible with the existing bootstrap and test tasks.
- docker-compose.yml is hard-coded in mise.toml and devcontainer.json. A rename to `deploy/` requires both changes plus the numerous documentation references.
- Replacing Yarn with pnpm requires changing `packageManager`, lockfile, bootstrap, CI, editor guidance, and `mise` tasks. It offers no demonstrated benefit here.
- A `make` or `just` command may be added only as a thin compatibility wrapper around `mise`, but it should not become another source of task definitions. Prefer `mise run verify-slice -- P1.3`.

**3. Internal consistency**

The target architecture has a coherent direction: canonical identity before graph writes, capability-gated store SPI, graph-primary version history, scoped access, content-addressed packs, write-side change feeds, and runtime planes ordered behind activation and mapping compilation.

It is not yet internally consistent enough to start implementation without an architecture ratification pass. The necessary amendments are:

- Define the artifact realm exception to graph-primary authority.
- Define durable-data scope during Phase 0.
- Decide the canonical names for graph SPI and its TCK.
- Specify the migration from `GraphReference(tenant, project, graphIri, revisionHash)` to separate authored and runtime references.
- State exactly which current ADRs A74 supersedes, particularly A30, A33, A34, and the PostgreSQL portions of A39.
- Replace the direct release provenance write with a named saga or commit-marker/outbox mechanism.
- Preserve the distinction between design-time authoring graphs and runtime tenant/environment graphs before the new `environmentId` model is implemented.

**4. Copilot instructions**

The updated plan is broadly compatible with copilot-instructions.md:

- Both require design and ADR work before implementation.
- Both require human validation rather than agent-run integration validation by default.
- Both require documentation changes in the same slice.
- The plan’s Validation Pack and human-gate model strengthen the existing contract.

The instructions should be updated after the plan is ratified to make the new process enforceable:

- Require a `docs/validation/<slice-id>.md` Validation Pack for implementation slices.
- Require a traceability row and explicit non-coverage statement.
- State that `mise` remains the only task-runner authority unless ADR-A29 is superseded.
- Add the graph-primary authority rule and the artifact-realm exception once A74 is accepted.
- Require agents to stop for human architectural guidance at each decision slice, which the existing instructions already require in principle.
- Replace the blanket “all listed architecture documents must be updated” wording with a requirement to update each affected normative document, while retaining the existing minimum set for cross-cutting changes.

No repository files were changed and no validation commands were run.