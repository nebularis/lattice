## Plan: Phased MORK and Surface Delivery

Build a shared semantic platform around the existing ontology and Python implementation. Keep Surface and MORK as separate applications with shared infrastructure. Start with **Surface Promotion and Index authoring**, because existing compiler, parity, extraction, and conformance code makes it the lowest-risk real vertical slice.

**Confirmed decisions**
- Java 21 control plane uses **Maven**.
- React applications use **Yarn workspaces**.
- First vertical slice is **Surface Promotion and Index**.
- Existing ontology layers and compiler source remain in place. No migration into a generic `contracts/` ontology directory.
- RabbitMQ remains the cross-runtime boundary. PostgreSQL is operational state. RDF remains semantic source of truth.
- `mise` is the repository-level toolchain manager, environment loader, and task runner. It does not replace Maven, Yarn, Python package tooling, or Mix.
- VS Code Dev Containers plus Docker Compose are the canonical reproducible environment. Windows contributors use WSL2 with the repository stored in the Linux filesystem.
- LATTICE owns semantic release intent, graph lineage, semantic gates, and release evidence. Generic release management remains the responsibility of an external release stack.
- Phase 3 defines a release-stack-neutral integration contract. Its reference implementation uses OCI artifacts, without selecting OCI as the required production release stack.

**Implementation status**

| Phase | Status | Outstanding work |
|---|---|---|
| Phase 0: Repository and Delivery Foundation | Authoring complete | Validate in a network-enabled environment. |
| Phase 1: Shared Semantic Platform | Authoring complete | Add Testcontainers, PostgreSQL outbox persistence, and end-to-end AMQP validation. |
| Phase 2: Surface Promotion and Index | Authoring complete | Lifecycle, graph families, worker boundaries, Studio UI, fixtures, E2E definitions, documentation, and handoff are present. Network-enabled validation remains required. |
| Phase 3: Release-Stack-Neutral Integration | Authoring complete | Semantic contracts, coordinator, ledger, provenance projection, OCI reference, export/restore fixtures, command adapters, documentation, and handoff are present. Network-enabled validation remains required. |
| Phase 4: Surface Projection to MORK | Authoring complete | Typed Projection DTOs, staging-only lower jobs, ARR fixture, governance policy, Technical Inspector, tests, documentation, and handoff are present. Network-enabled validation remains required. |
| Phase 5: MORK Review Workbench | Authoring complete | Immutable snapshots, decision semantics, scope-restricted workers, durable review ledger, Bench UI, E2E, tests, documentation, and handoff are present. Network-enabled validation remains required. |
| Phase 6: MORK Queue, Calibration, and Governance | Authoring complete | Replayable queue and governance ledger, calibration bulk gates, minting, challenge, and template-exception workflows, Atlas/Boundary/Ledger/Pack fixtures, tests, documentation, and handoff are present. Network-enabled validation remains required. |
| Phase 7 | Not started | Remains sequenced after Phase 6. |

**Delivery Model for a Network-Restricted Authoring Environment**

Implementation agents work in an environment where proxy restrictions prevent dependency resolution, container pulls, and therefore reliable builds or test execution. They must still deliver a complete phase: source, package descriptors, lockfile updates where possible, configuration, tests, fixtures, CI wiring, documentation, and an explicit validation handoff. They must not state or imply that an unrun build, test, container, package installation, or external tool invocation passed.

Each phase has two completion states:

1. **Authoring complete**: the implementation, configuration, tests, test fixtures, documentation, CI jobs, and handoff manifest are present and internally consistent by static inspection.
2. **Validated complete**: a network-enabled validation environment resolves dependencies, runs the defined commands, records results, and either accepts the phase or returns a bounded defect list to the authoring environment.

The offline authoring workflow is:

```text
implement one bounded phase
  -> add tests and CI configuration without executing unavailable tools
  -> static review of paths, versions, contracts, and generated-file rules
  -> produce phase handoff manifest and validation command matrix
  -> validate the entire phase in a network-enabled environment
  -> return only concrete defects for a repair iteration
```

Every phase handoff contains:

- commit or immutable source revision;
- changed-module inventory and ownership;
- exact `mise` task, Maven, Yarn, Python, Mix, Docker Compose, and CI commands to run;
- expected successful outcomes, expected generated files, and known unverified assumptions;
- required services, ports, environment variables, fixture data, and seeded identities;
- dependency and lockfile changes, including any lockfiles that could not be regenerated offline;
- API, event, graph-schema, and migration compatibility notes;
- rollback and cleanup instructions where the phase changes persistent state;
- a statement that validation has not been executed in the restricted environment.

The validation environment validates one whole phase at a time. It must not silently add unrelated changes, regenerate lockfiles without reporting them, or advance to the next phase before the current handoff passes its command matrix. Validation results are committed as release or CI evidence, not copied into architecture prose as informal claims.

**Architecture Decisions and Documentation Discipline**

Every phase and every material implementation decision must leave an auditable documentation trail. This applies equally to code, schemas, deployment configuration, test fixtures, and operational procedures.

- Record a decision in `docs/adr/` whenever it establishes a durable boundary, dependency direction, data ownership rule, security model, compatibility commitment, operational responsibility split, or technology-selection constraint. ADRs use the repository convention of Status, Context, Decision, and Consequences, and cross-reference the relevant plan phase, code modules, contracts, and prior ADRs.
- Write comprehensive explanatory material in `docs/architecture/` for each delivered capability. Architecture guides explain the components, data and control flows, state transitions, trust boundaries, contracts, extension points, operational assumptions, failure handling, and known limitations. They explain how the implementation works, not only why it was chosen.
- Keep normative ontology semantics in layer READMEs and decision rationale in ADRs. Architecture documents must link to these sources rather than restating normative content in a second authority.
- Update user, developer, operator, security, recovery, and migration documentation whenever a capability reaches the relevant audience boundary. Architecture documentation is the source material for later user-guide generation.
- Add documentation and ADR review to each phase's authoring-complete checklist. A handoff manifest must inventory new or updated ADRs and architecture documents, state their ownership, and identify any decisions intentionally deferred.
- Do not claim unrun validation in ADRs or architecture guides. Record validation evidence in CI, release records, and the phase handoff. Documentation must distinguish implemented, authoring-complete, validated, and deferred work.

**Toolchain, Package Management, and Developer Environments**

Use `mise` from committed root `mise.toml` for tool-version pinning, shared environment variables, and repository tasks. Use it to invoke ecosystem-native package managers, not as a replacement for them.

| Concern | Authoritative mechanism | `mise` responsibility |
|---|---|---|
| Java platform | Maven Wrapper, reactor `pom.xml`, Maven dependency management | Java 21 and Maven availability, `mise run check:java` |
| React applications | Yarn workspaces, committed `yarn.lock`, Corepack | Node availability, `mise run check:frontend` |
| Root ontology validation | root `pyproject.toml`, `requirements-lock.txt` | Python availability, `mise run check:python-root` |
| MORK Python package | `mork/pyproject.toml` | Python availability, package-scoped tasks |
| SPC Python package | `spc/src/python/pyproject.toml` | Python availability, package-scoped tasks |
| Python workers | `workers/pyproject.toml` and a dedicated lock | Python availability, `mise run check:workers` |
| SPC Erlang and Elixir | `spc/src/erlang/mix.exs`, `mix.lock` when introduced | Erlang and Elixir availability, `mise run check:spc` |
| Infrastructure services | Docker Compose files under `deployment/` | `mise run services:up`, `services:down`, and smoke-test tasks |

The initial `mise.toml` pins Java 21, Maven 3.9, Node 22, Python 3.11, Erlang 27, and Elixir 1.17. Add .NET only when a committed .NET project or local tool manifest needs it. Python 3.11 satisfies the MORK and SPC packages while remaining compatible with the root package's Python 3.9 minimum. Exact patch versions, image digests, and package-manager versions are pinned in their ecosystem-specific files and lockfiles.

Use Corepack for Yarn. The root `package.json` declares a pinned Yarn version, workspaces `apps/*` and `apps/packages/*`, and is private. Commit `.yarnrc.yml` and `yarn.lock`. Maven Wrapper is committed under `platform/.mvn/` and `platform/mvnw` or at the repository root if it is intentionally shared by future JVM projects. Do not execute Maven Wrapper generation in the restricted environment unless its required artefacts are already available.

Support two developer modes:

1. **Native mode** for macOS and Linux, and limited frontend, Java, or .NET work on Windows: `mise install`, then scoped `mise run` tasks.
2. **Canonical Dev Container mode** for local-service, Python-worker, AMQP, and CI-parity work. `.devcontainer/devcontainer.json` builds from a pinned Dockerfile and uses `deployment/compose/` services for Fuseki, PostgreSQL, RabbitMQ, and Keycloak.

On Windows, document WSL2 plus Docker Desktop's WSL backend as the supported path. Clone and open the repository from `~/src/lattice` inside WSL, not from `C:\Users\...`, to avoid filesystem, symlink, watcher, and container-mount issues. Native Windows support remains best effort until every required tool backend is demonstrated there.

The initial repository tasks are `mise run bootstrap`, `mise run check`, `mise run test`, `mise run services:up`, `mise run services:down`, and phase-scoped variants. In the restricted authoring environment these commands are recorded and wired but are not run when they need network access or unavailable tooling.

**Repository Shape**
- Add `platform/`: Maven reactor for the shared Java control plane.
  - Semantic dataset SPI and Jena, RDF4J, generic-SPARQL adapters.
  - Authentication and graph-scope policy.
  - Transactional outbox, job orchestration, API contracts, test kit.
  - Surface and MORK workflow modules stay separate within this reactor.
- Add `apps/`: Yarn workspace.
  - `apps/surface-contract-studio`
  - `apps/mork-review-workbench`
  - `packages/ui-foundation`
  - `packages/api-clients`
- Add `workers/`: Python 3.11+ deployable worker distribution.
  - Wrap existing code in `tools/surface`, `tools/mork_compilers`, `mork/src/python/mork_communities`, and `tools/mork2rml.py`.
  - Do not rewrite semantic algorithms in Java.
- Add `contracts/` only for OpenAPI, AsyncAPI, CloudEvents JSON Schema, and compatibility fixtures.
- Add `deployment/` for Docker Compose, reference Fuseki, RabbitMQ, PostgreSQL, Keycloak, container builds, and later Kubernetes or Helm assets.
- Add root `mise.toml`, private root `package.json`, `.yarnrc.yml`, and `.devcontainer/`. `mise.toml` owns tool versions and task aliases only. Maven, Yarn, pip or virtual environments, and Mix remain dependency authorities.
- Preserve the current ontology structure, layer READMEs, Surface and MORK documentation, and independent SPC Mix and Python projects.

**Phase 0: Repository and Delivery Foundation**
1. Bootstrap root `mise.toml`, the Maven reactor, Yarn workspace, worker Python package, Dev Container, deployment skeleton, and API/event contract directories.
2. Add developer onboarding, local-environment, WSL guidance, package-management, testing, offline-handoff, and architecture overview guides.
3. Convert the manual-only `phase8-conformance.yml` into reusable PR-gated jobs.
4. Gate PRs on SPDX, literate extraction, existing Python tests, worker tests, Maven verification, Yarn typecheck/test/build, and documentation links.
5. Add a phase-handoff manifest template and a validation command matrix under `docs/developer/` for every phase to complete before external validation.

Authoring-complete criteria:
- `mise.toml`, Maven, Yarn, Python-worker, Mix, Docker Compose, and Dev Container configuration name one authoritative task or command path for each project.
- The bootstrap, check, test, and service tasks have documented preconditions and do not conflate tool installation with project dependency authority.
- CI workflows, test fixtures, and validation commands are present but marked unverified when unavailable in the restricted environment.

Validation-environment exit criteria:
- A clean clone has one documented local bootstrap path.
- Python, Maven, Yarn, and SPC environments remain independently installable.
- CI detects deliberate extraction drift, licence violations, schema incompatibility, Java failures, and frontend type failures.

**Phase 1: Shared Semantic Platform**
1. Implement scoped dataset access, graph revisions, capability discovery, and exports in `platform/semantic-dataset-spi`.
2. Implement Fuseki first, with adapter contract tests before RDF4J and generic SPARQL adapters.
3. Implement OIDC-derived tenant, project, role, and named-graph policy.
4. Implement transactional outbox, RabbitMQ publishing, CloudEvents schemas, retries, dead-letter queues, idempotency, and correlation propagation.
5. Add a Python worker wrapper that handles a graph-reference validation job.

Authoring-complete criteria:
- Dataset SPI, adapter contract tests, outbox tests, AMQP fixture messages, worker wrapper, Testcontainers configuration, API schemas, and a Phase 1 handoff manifest are complete.
- Static inspection confirms all job payloads use graph references, revision hashes, profile identifiers, and opaque job identifiers rather than RDF payloads, credentials, or browser tokens.

Validation-environment exit criteria:
- A Java command reaches a Python worker through RabbitMQ and records its result exactly once despite a forced retry.
- Fuseki adapter tests pass and unsupported capabilities fail explicitly.
- Testcontainers exercises PostgreSQL, Fuseki, and RabbitMQ.

**Phase 2: Surface Promotion and Index**
1. Implement Surface contract revisions, drafts, review requests, approvals, generation, supersession, and releases.
2. Add immutable Surface graph families for contracts, profiles, previews, generated output, lowering records, and invalidation plans.
3. Wrap current Surface validation, generation, parity, and invalidation algorithms as AMQP jobs.
4. Build Surface Contract Studio:
   - Portfolio
   - Typed Promotion and Index editors
   - Path builder
   - Population and closure controls
   - Profile picker
   - Law checklist
   - Read-set and impact preview
   - Generated-output diff
   - Technical Turtle view
5. Add Surface user, developer, release, and regeneration documentation using current SaaS currency, clinical crosswalk, and employment job-family examples.

Authoring-complete criteria:
- Contract-revision state transitions, typed API schemas, Surface graph scopes, Python worker wrappers, UI flows, Surface fixtures, E2E test definitions, and a Phase 2 handoff manifest are complete.
- The implementation preserves Surface's current literate README, examples, parity fixtures, extraction rules, and existing Python compiler sources.

Validation-environment exit criteria:
- An author creates and validates a contract without editing Turtle.
- Existing Surface parity and Phase 8 tests pass through the worker path.
- Changed inputs produce an explainable, dependency-scoped regeneration plan.

**Phase 3: Release-Stack-Neutral Integration**

LATTICE does not implement a generic release pipeline, registry, deployment manager, signing service, GitOps controller, workflow engine, object store, telemetry backend, or backup system. It exposes semantic release information through a versioned integration contract. A release stack implements storage, signing, promotion, rollback, retention, credentials, deployment, and workflow scheduling using its own native capabilities.

1. Define versioned `ReleaseIntent`, `ReleaseReceipt`, adapter capability, environment-binding, semantic-gate evidence, release-inventory, export, restore, and retention JSON Schemas under `contracts/release/`.
2. Define an adapter port that supports capability negotiation and asynchronous `plan`, `publish`, `promote`, `rollback`, `export`, `restore`, and `retire` operations. The contract uses opaque operation and correlation IDs and immutable digests.
3. Implement LATTICE semantic-release assembly. It verifies immutable graph and generated-output references, semantic gate completeness, approval state, graph lineage, and estate-impact evidence before calling an adapter.
4. Add release ledger and RDF provenance records for intent, receipt, supersession, promotion, rollback, export, restore, retention, and correlated failure. Do not duplicate generic stack internals.
5. Add an OCI reference adapter. It packages canonical release metadata and inventory as an OCI-compatible artifact, returns immutable manifest digests, and uses a signing abstraction with a deterministic test double and a Cosign-compatible production implementation.
6. Add fixture-driven tests that package, inspect, verify, export, and restore OCI layouts without a live registry. Add an optional Compose OCI registry profile for network-enabled integration validation.
7. Add OpenTelemetry-compatible trace and correlation fields around intent assembly and adapter calls. The release stack provides telemetry storage and dashboards.
8. Publish the integration contract, Docker plus CI reference guide, Kubernetes/GitOps guide for Argo CD or Flux, workflow-engine guide, operator runbooks, recovery guide, authorization guide, migration guide, and retention guide.

The `ReleaseIntent` supplied by LATTICE contains an opaque release ID, tenant and project IDs, requester, correlation ID, requested environment, immutable graph references, generated-output digests, semantic profile and canonicalisation revisions, gate evidence, environment requirements, retention class, legal-hold state, and optional rollback target. It must not contain RDF payloads, raw credentials, browser tokens, mutable tags, endpoint credentials, or executable deployment instructions.

The `ReleaseReceipt` returned by a release stack contains the release and adapter identities, lifecycle state, immutable artifact locations and digests, signature and provenance references, environment-binding and promotion evidence, rollback locator, export and restore evidence, retention acknowledgement, and an operator-safe diagnostic reference. It cannot assert semantic validity. LATTICE retains and verifies semantic gate evidence.

The integration supports three deployment models:

- **Docker plus CI:** CI runs LATTICE gates and invokes the OCI reference adapter. Docker Compose or equivalent uses immutable digests.
- **Kubernetes and GitOps:** CI or Argo Workflows runs LATTICE gates. The adapter publishes immutable artifacts and proposes a Git digest binding. Argo CD or Flux reconciles the environment and reports the Git and deployment revision in the receipt.
- **Workflow-centric:** A durable engine such as Temporal invokes the same adapter operations and manages waits, retries, approvals, and compensation without redefining semantic release identity or evidence.

Authoring-complete criteria:
- Release schemas, fixtures, adapter capability model, semantic-release assembly, OCI reference adapter, signing abstraction, fixture tests, optional registry profile, CI wiring, documentation, runbooks, and a Phase 3 handoff manifest are present.
- Published receipts reference immutable artifact and graph digests.
- Semantic gate evidence and release-stack verification evidence remain distinct and cannot substitute for one another.
- No generic release-stack component becomes a LATTICE runtime dependency.

Validation-environment exit criteria:
- The OCI reference packages a Surface release bundle, signs it, publishes it to an OCI-compatible registry, verifies it by digest, and returns a schema-valid receipt.
- An exported bundle restores into a clean reference environment and verifies every graph and generated-output digest.
- Rollback promotes a previously verified immutable receipt while preserving release-ledger history.
- A stale profile or canonicalisation revision is rejected by a LATTICE impact gate before the adapter is called.
- Fixture tests run without external network access. Registry, signing, and Compose integration tests run only in the network-enabled validation environment.

**Phase 4: Surface Projection to MORK**
1. Add Projection authoring with typed role bindings, backend policy, deterministic-only default, and bounded-LLM policy.
2. Wrap existing Surface lowering in a Python worker.
3. Lower into immutable MORK staging graphs only. Never write active mappings directly.
4. Define the Surface-to-MORK handoff policy and the Projection kinds requiring engineering or mapping review.
5. Show lowered mapping, MCN, dependencies, and backend capability in the Technical Inspector.

Authoring-complete criteria:
- Projection DTOs, role-binding validation, lower-job schemas, immutable MORK staging policy, worker wrapper, ARR fixtures, technical-inspector views, governance tests, and a Phase 4 handoff manifest are complete.

Validation-environment exit criteria:
- The ARR example is authored, validated, lowered through RabbitMQ, and traceable from Surface revision to MORK graph.
- Repeated lowering produces stable identifiers and dependency order.
- Mapping activation cannot bypass the defined governance transition.

**Phase 5: MORK Review Workbench**
1. Implement review snapshots, typed decisions, evidence projection, graph lifecycle, audit, and role-specific DTOs.
2. Wrap Python MORK validation and community analysis as scope-restricted workers.
3. Build the section-level Bench with source context, token ribbon, witnesses, challenges, coverage, alternatives, and six decisions.
4. Implement decision-to-learning rules so `RESHAPE` never changes projection statistics.
5. Add MORK reviewer, engineering, governance, and MCN documentation.

Authoring-complete criteria:
- MORK review snapshots, typed commands, role-specific DTOs, evidence-projection fixtures, Python worker wrappers, Bench UI flows, decision-to-learning tests, security tests, and a Phase 5 handoff manifest are complete.

Validation-environment exit criteria:
- Confirm, Retarget, Reshape, Decline, Teach, and Defer each have distinct semantic and learning effects.
- Stale review snapshots conflict safely.
- Domain Stewards cannot retrieve MORK syntax, lint diagnostics, pack internals, or unrelated tenant content.

**Phase 6: MORK Queue, Calibration, and Governance**
1. Add Atlas, yield-ordered queue, boundary workflow, template-by-exception, Ledger, and engineering MCN views.
2. Add calibrated bulk-action gates stratified by pack, profile, and model identity.
3. Add ontology minting and retrospective challenge workflows.
4. Add Pack Studio only after typed decision and calibration data exists.

Authoring-complete criteria:
- Queue and calibration projection definitions, Atlas and Boundary UI test fixtures, bulk-gate policy tests, minting and retrospective-challenge command models, privacy tests for Pack Studio, and a Phase 6 handoff manifest are complete.

Validation-environment exit criteria:
- Queue ordering is replayable.
- Bulk confirmation is impossible until calibration passes.
- Ontology changes reopen affected approvals with a named axiom and immutable prior history.

**Phase 7: Compiler Breadth and SPC Readiness**
1. Extend compiler workers only through ADR-A19 stages and proven intermediate models.
2. Add RDF4J and generic-SPARQL adapter conformance suites.
3. Define an explicit MORK-to-SPC bridge contract with separate RabbitMQ exchanges and no active-mapping write capability.
4. Keep SPC independently deployable until namespace and projection contracts are approved.

Authoring-complete criteria:
- Compiler capability contracts, adapter test matrices, bridge schemas, AMQP-isolation tests, SPC-absent deployment fixtures, cross-runtime documentation, and a Phase 7 handoff manifest are complete.

Validation-environment exit criteria:
- Every supported compiler backend produces deterministic manifests and provenance.
- AMQP bridge tests prove message isolation, retry, replay, and capability failures.
- SPC runs unchanged when the bridge is absent.

**Package Management**
- `mise`: top-level tool version pinning, environment loading, and task orchestration. It has no dependency lock and does not replace ecosystem package managers.
- Python: retain root validation dependencies and lockfile, retain independent MORK and SPC packages, add a dedicated `workers/pyproject.toml` and lock. Use common RDF constraints only for cross-runtime integration tests.
- Java: Maven Wrapper, Java 21 toolchain, central dependency management, Maven Enforcer, CycloneDX SBOMs, ports separated from adapters.
- Frontend: Yarn workspace with checked-in lockfile, Corepack-pinned Yarn, strict TypeScript project references, shared package versioning.
- Erlang and Elixir: retain SPC’s independent Mix project and `mix.lock`.
- Containers: pin image digests and produce SBOMs per deployable image.

**Documentation and GitHub Pages**
- Keep normative ontology documentation in layer READMEs.
- Keep decisions in `docs/adr`.
- Add developer, operator, and security guides under `docs/developer`, `docs/operator`, and `docs/security`.
- Keep application-specific guides under `mork/docs` and `surface/docs`.
- Add `docs/developer/toolchain.md`, `docs/developer/windows-wsl.md`, `docs/developer/offline-phase-handoff.md`, and a phase-validation record template. Document `mise` as the entry point and each ecosystem's native package manager as the dependency authority.
- Evolve `docs/index.html` into the Pages entry point and `docs/book.html` into the long-form guide.
- Add generated site metadata rather than duplicating normative content manually in HTML.
- Create a Pages pipeline with link validation, static-site build, protected-branch deployment, and PR preview artefacts.
- Update README, issue templates, and PR templates with component ownership, test layer, documentation impact, schema compatibility impact, and AI-provenance requirements.

**Scope Boundaries**
- Included: platform foundation, `mise` and Dev Container adoption, Surface authoring, MORK review, Python worker wrapping, CI, documentation, GitHub Pages, release operations, adapter conformance, offline phase handoff, and SPC readiness.
- Deferred: ontology-semantic changes, moving layer directories, unrestricted Projection backends, native execution IR, production SPC integration, commercial dependencies, synchronous unrestricted OWL DL reasoning, and bulk migration of legacy assets.
