User: Please execute phase 0 and phase 1 of the plan (attached) to introduce `mise` to manage this large mono-repo AND build the initial shared semantic platform.

Note from the plan that you won't necessarily be able to run things locally (ALTHOUGH - docker desktop is installed and running locally and therefore WSL is available in this envorinment - BUT the proxy doesn't allow traffic so dependency fetching will fail) - just build everything and we'll ship a patch offsite to run the build and tests once you've completely phases 0 and 1.

GitHub Copilot: I’ll anchor this against the repository’s existing Python validation and CI surfaces, then add the Phase 0 foundation and Phase 1 platform as a bounded, statically coherent implementation. Dependency resolution will remain unverified here, and I’ll produce an explicit offline validation handoff rather than claiming builds passed.

Read skill [project-setup-info-local](file:///c%3A/Program%20Files/Microsoft%20VS%20Code/1b6a188127/resources/app/extensions/copilot/assets/prompts/skills/project-setup-info-local/SKILL.md?vscodeLinkType%3Dskill)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/pyproject.toml)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/.github/workflows/phase8-conformance.yml)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/mork/pyproject.toml)

Read memory

The repository already has the root ontology test configuration and a manual-only Phase 8 workflow. The controlling implementation path for Phase 1 does not exist yet, so I’ll add an isolated Maven reactor and Python worker package without moving existing semantic sources, then validate the available static configuration and Python syntax.

Searched for files matching `**/spc/**/pyproject.toml`, 1 match

Searched for files matching `**/tools/surface/**/*.py`, 14 matches

Searched for files matching `**/tools/mork_compilers/**/*.py`, 9 matches

Searched for files matching `**/.github/workflows/*`, 1 match

Searched for files matching `**/requirements*.txt`, 1 match

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/requirements-lock.txt)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/.github)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/spc/src/python/pyproject.toml)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/tools/surface/cli.py#1-1), lines 1 to 300

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/tools/mork2rml.py#1-1), lines 1 to 260

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/README.md)

I have a concrete implementation boundary: Phase 0 will establish the committed orchestration, container, CI, documentation, and handoff contract. Phase 1 will provide a compilable Java SPI and Fuseki adapter, an in-memory transactional-outbox model, versioned job schemas, and a Python worker that rejects inline RDF and credentials before invoking a graph-reference validator. I’ll now add those artifacts as separate modules so existing ontology tooling stays untouched.

Created 5 todos

Generating patch (188 lines) in [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/mise.toml), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/package.json), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/.yarnrc.yml), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/.devcontainer/devcontainer.json), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/.devcontainer/Dockerfile), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/deployment/compose/docker-compose.yml), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/developer/toolchain.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/developer/windows-wsl.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/developer/offline-phase-handoff.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/developer/phase-handoff-template.md)


```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```
The Phase 0 configuration is now in place. I’m checking its parsability before expanding into the platform modules, since malformed task or container metadata would invalidate every later validation path.

Ran terminal command: import json, pathlib, tomllib; tomllib.loads(pathlib.Path('mise.toml').read_text()); json.loads(pathlib.Path('package.json').read_text()); json.loads(pathlib.Path('.devcontainer/devcontainer.json').read_text()); print('Phase 0 TOML and JSON parse successfully')
Completed with input: import json, pathlib, tomllib; tomllib.loads(pathlib.Path('mise.toml').read_text()); json.loads(pathlib.Path('package.json').read_text()); json.loads(pathlib.Path('.devcontainer/devcontainer.json').read_text()); print('Phase 0 TOML and JSON parse successfully')

The parse check is blocked because this Windows environment has no `python` executable on `PATH`, which is consistent with the restricted setup and does not evaluate the files themselves. I’m proceeding with the Phase 1 source and unit tests, keeping Maven and Python execution explicitly deferred to the offsite validation matrix.

Generating patch (244 lines) in [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/pom.xml), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/semantic-dataset-spi/pom.xml), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/semantic-dataset-spi/src/main/java/org/nebularis/lattice/semantic/DatasetCapability.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/semantic-dataset-spi/src/main/java/org/nebularis/lattice/semantic/GraphReference.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/semantic-dataset-spi/src/main/java/org/nebularis/lattice/semantic/DatasetSnapshot.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/semantic-dataset-spi/src/main/java/org/nebularis/lattice/semantic/ScopedDataset.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/semantic-dataset-spi/src/test/java/org/nebularis/lattice/semantic/GraphReferenceTest.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/semantic-dataset-fuseki/pom.xml), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/semantic-dataset-fuseki/src/main/java/org/nebularis/lattice/semantic/fuseki/FusekiScopedDataset.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/semantic-policy/pom.xml), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/semantic-policy/src/main/java/org/nebularis/lattice/policy/GraphAccessPolicy.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/semantic-policy/src/main/java/org/nebularis/lattice/policy/Principal.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/semantic-policy/src/main/java/org/nebularis/lattice/policy/TenantProjectGraphAccessPolicy.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/semantic-policy/src/test/java/org/nebularis/lattice/policy/TenantProjectGraphAccessPolicyTest.java)


```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```
The Java Phase 1 core now defines graph references, capability discovery, Fuseki read access, and tenant/project authorization, with tests for invalid scopes and cross-tenant access. I’m checking whether a local JDK or Maven is available to compile this slice before adding the outbox and worker boundary.

Ran terminal command: $maven = Get-Command mvn -ErrorAction SilentlyContinue; $java = Get-Command java -ErrorAction SilentlyContinue; if ($null -eq $maven -and $null -eq $java) { Write-Output 'No Maven or Java executable is available on PATH'; exit 1 }; $maven, $java | Where-Object { $null -ne $_ } | Select-Object Name, Source | Format-Table -AutoSize

Only Java 8 is available and Maven is absent, while the reactor requires Java 21. I’ve recorded that validation blocker and will continue with static coherence. Next I’m adding the outbox, CloudEvents contract fixtures, and Python worker boundary that implements Phase 1’s graph-reference-only messaging rule.

Generating patch (283 lines) in [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/semantic-dataset-fuseki/src/main/java/org/nebularis/lattice/semantic/fuseki/FusekiScopedDataset.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/platform-outbox/pom.xml), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/platform-outbox/src/main/java/org/nebularis/lattice/outbox/CloudEvent.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/platform-outbox/src/main/java/org/nebularis/lattice/outbox/OutboxRecord.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/platform-outbox/src/main/java/org/nebularis/lattice/outbox/TransactionalOutbox.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/platform-outbox/src/main/java/org/nebularis/lattice/outbox/InMemoryTransactionalOutbox.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/platform-outbox/src/test/java/org/nebularis/lattice/outbox/InMemoryTransactionalOutboxTest.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/contracts/events/graph-validation-request.schema.json), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/contracts/events/graph-validation-result.schema.json), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/workers/pyproject.toml), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/workers/src/lattice_workers/__init__.py), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/workers/src/lattice_workers/graph_validation.py), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/workers/tests/test_graph_validation.py)


```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```
The Phase 1 messaging boundary is present now: schemas accept only graph references and profile identifiers, the outbox coalesces retries by idempotency key, and the worker has tests proving that inline Turtle is rejected. I’m checking whether the Windows Python launcher can execute the worker tests, which is the cheapest direct behavior check available here.

Ran terminal command: $launcher = Get-Command py -ErrorAction SilentlyContinue; if ($null -eq $launcher) { Write-Output 'The Python launcher is not available'; exit 1 }; py -3.11 -m pytest workers/tests
Completed with input: $launcher = Get-Command py -ErrorAction SilentlyContinue; if ($null -eq $launcher) { Write-Output 'The Python launcher is not available'; exit 1 }; py -3.11 -m pytest workers/tests

The Python launcher is also absent, so worker tests cannot execute locally. I’m finishing the authoring-complete boundary now: CI task wiring, static workspace metadata, an architecture note, and a Phase 0/1 handoff that names every command and unverified dependency resolution explicitly.

Generating patch (158 lines) in [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/mise.toml), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/package.json), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/.github/workflows/phase8-conformance.yml), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/README.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/yarn.lock), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/.github/workflows/platform.yml), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/architecture/semantic-platform.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/developer/phase-0-1-handoff.md)


```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```
The final authoring artifacts are in place, including PR-gated CI and the explicit handoff. I’m running non-network static checks that Docker and the local Node runtime can perform, then I’ll inspect the resulting change set for missing Phase 0 or 1 artifacts.

Ran terminal command: docker compose -f deployment/compose/docker-compose.yml config --quiet
Completed with input: docker compose -f deployment/compose/docker-compose.yml config --quiet

Ran terminal command: $node = Get-Command node -ErrorAction SilentlyContinue; if ($null -eq $node) { Write-Output 'Node is not available on PATH'; exit 1 }; node -e "JSON.parse(require('fs').readFileSync('package.json', 'utf8')); JSON.parse(require('fs').readFileSync('.devcontainer/devcontainer.json', 'utf8')); JSON.parse(require('fs').readFileSync('contracts/events/graph-validation-request.schema.json', 'utf8')); JSON.parse(require('fs').readFileSync('contracts/events/graph-validation-result.schema.json', 'utf8')); console.log('JSON metadata parses successfully')"

The JSON metadata parses successfully. Docker is not on this PowerShell `PATH` despite Docker Desktop being available through WSL, so the Compose check must run offsite or from a configured WSL shell. I found one remaining Phase 1 gap in the current source: the outbox models retries but lacks a transport relay and deployment-facing adapter, so I’m completing that bounded implementation before the final static review.

Generating patch (130 lines) in [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/platform-outbox/pom.xml), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/platform-outbox/src/test/java/org/nebularis/lattice/outbox/InMemoryTransactionalOutboxTest.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/architecture/semantic-platform.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/developer/phase-0-1-handoff.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/platform-outbox/src/main/java/org/nebularis/lattice/outbox/EventPublisher.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/platform-outbox/src/main/java/org/nebularis/lattice/outbox/OutboxRelay.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/platform-outbox/src/main/java/org/nebularis/lattice/outbox/RabbitMqEventPublisher.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/semantic-dataset-fuseki/src/test/java/org/nebularis/lattice/semantic/fuseki/FusekiScopedDatasetTest.java)


```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```
The outbox now has a durable RabbitMQ publishing shape, dead-letter topology declaration, and a retry-preserving relay test. I’m using the editor’s diagnostics next, followed by whitespace and changed-file inspection, since runtime compilers remain unavailable on this host.

Ran terminal command: git diff --check; git status --short

Checked [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/mise.toml), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/deployment/compose/docker-compose.yml), no problems found

Static diagnostics found no configuration errors, and `git diff --check` found no whitespace errors. The worktree already contains unrelated deletions and generated files, which I have left untouched. I caught one Java import omission during source review and am correcting that before the final handoff check.

Generating patch (7 lines) in [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/platform-outbox/src/main/java/org/nebularis/lattice/outbox/CloudEvent.java)


```

```
The Java import is corrected. I’ll now recheck the touched class through editor diagnostics and probe WSL availability, which may be the only local route to the toolchains the Phase 1 modules require.

Ran terminal command: $wsl = Get-Command wsl.exe -ErrorAction SilentlyContinue; if ($null -eq $wsl) { Write-Output 'WSL is not available from this terminal'; exit 1 }; wsl.exe --status

Checked [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/platform-outbox/src/main/java/org/nebularis/lattice/outbox/CloudEvent.java), no problems found

WSL is present only as the `docker-desktop` distribution, with no developer Linux distribution installed, so it cannot run the documented WSL workflow. The authoring work is complete and the handoff records this local limitation. I’m marking the implementation and static checks complete, with runtime validation intentionally deferred to the network-enabled environment.

Completed: *Add Phase 0 foundation* (1/5)

Completed Phase 0 and the authoring-complete Phase 1 foundation. The resulting handoff defines the exact offsite commands and clearly marks all unrun network, container, Java, and Python validation.



Implemented Phase 0 and an authoring-complete Phase 1 foundation.

Phase 0 adds mise.toml, Yarn/Corepack metadata, Dev Container and reference Compose services, PR CI, developer environment guidance, and reusable phase-handoff documentation.

Phase 1 adds:
- A Java Maven reactor under platform with semantic graph references, capability SPI, a Fuseki adapter, tenant/project graph authorization, transactional outbox, RabbitMQ publisher, relay retry behavior, and unit tests.
- Versioned graph-validation request/result schemas in events.
- An isolated Python worker package in workers that enforces graph-reference-only jobs and rejects inline RDF or credentials.
- Architecture and offsite command matrix in phase-0-1-handoff.md.

Static checks passed for JSON metadata, mise.toml, Compose diagnostics, the corrected Java class, and `git diff --check`. Runtime validation could not run locally: `python`, `py`, Maven, and Java 21 are unavailable on `PATH`; WSL only has the `docker-desktop` distribution, and Docker is not exposed to PowerShell. The handoff explicitly records these limits and commands for a network-enabled validation environment.

Made changes.

User: Let's proceed with phase 3.

GitHub Copilot: Phase 3 depends on Phase 2’s Surface contract revisions, immutable graph families, generation jobs, and releaseable outputs. Those artifacts do not exist yet because we implemented Phases 0 and 1 only.

Choose one path:

1. Implement Phase 2 first, then Phase 3 against its real contract and release model.
2. Build Phase 3 as a generic release-operations skeleton, with Surface-specific integration deferred until Phase 2.

User: We will go for path 2 HOWEVER PLEASE PAUSE NOW - to ask why are we building a release-operations pipeline? There must be more than a dozen great open source solutions to this problem. List the options we have on the table and let's work through the options together before we continue to cut code.

GitHub Copilot: Yes. Building a custom release-operations pipeline before evaluating established tools would create avoidable operational surface, especially for signing, promotion, rollback, retention, provenance, and recovery.

The key question is which parts are domain-specific. LATTICE needs immutable semantic release manifests, graph-aware compatibility and impact checks, and governed promotion decisions. It probably does **not** need to recreate generic artifact storage, deployment orchestration, cryptographic signing, SBOM/provenance, observability, or rollback primitives.

**Options on the table**

| Concern | Strong open-source options | Fit for LATTICE |
|---|---|---|
| GitOps promotion and rollback | Argo CD, Flux CD | Strong fit for deploying platform services and worker versions. Git commits provide auditability and rollbacks. |
| Release orchestration | Argo Workflows, Tekton Pipelines, Jenkins, Woodpecker CI | Good for multi-step release jobs such as generate, validate, sign, export, promote, and verify. Argo Workflows pairs naturally with Argo CD. |
| Artifact registry | Harbor, OCI registry, GitHub Container Registry | Store worker/control-plane images and signed release bundles. Harbor adds retention, replication, scanning, and RBAC. |
| Object storage for immutable bundles | MinIO | Strong fit for signed exports, generated Surface outputs, snapshots, and restore inputs. S3-compatible and self-hostable. |
| Artifact metadata and lineage | OCI manifests plus in-toto attestations, ORAS | Good fit for associating generated RDF exports, manifest JSON, SBOMs, signatures, and provenance without inventing a bespoke package format. |
| Signing and provenance | Sigstore Cosign, in-toto, SLSA provenance | Strong fit. Cosign signs container images and OCI artifacts. in-toto supplies verifiable statements about generation and approval steps. |
| SBOM and vulnerability scanning | Syft, Grype, Trivy | Strong fit for deployable images and release bundles. Syft emits SBOMs, while Grype or Trivy can scan them. |
| Secrets and environment binding | OpenBao, External Secrets Operator, SOPS + age | Strong fit. OpenBao is a Vault-compatible open-source option. SOPS works well for GitOps-managed encrypted configuration. |
| Database schema migration | Flyway, Liquibase | Good fit for PostgreSQL operational state. They should not attempt to migrate RDF semantic content. |
| RDF graph versioning and publication | Git-backed Turtle snapshots, MinIO exports, Fuseki dataset backup, RDF Delta | Needs a LATTICE-specific decision. RDF Delta is relevant if live graph replication and history become necessary. Git plus immutable release bundles is simpler for authored graph families. |
| Semantic release validation | Existing Surface compiler, PySHACL, RDFLib tooling, Phase 8 conformance | Domain-specific. Keep this in LATTICE workers. It becomes a release gate, not a release platform. |
| API versioning and compatibility | OpenAPI diff, AsyncAPI tooling, JSON Schema compatibility checks | Strong fit for platform contracts and CloudEvents schemas. |
| Observability | OpenTelemetry, Prometheus, Grafana, Loki, Tempo, Jaeger | Strong fit. Instrument Java, Python, browser, and AMQP paths with OpenTelemetry. Grafana handles dashboards. |
| Incident and audit trails | Grafana Loki, OpenSearch, PostgreSQL audit tables | Use standard telemetry for runtime traces and logs. Keep LATTICE-specific approval and graph lifecycle audit data in PostgreSQL and RDF provenance. |
| Policy enforcement | Open Policy Agent, Kyverno, Conftest | Strong fit for CI and Kubernetes policy. Useful for blocking unsigned images, mutable tags, missing SBOMs, or unapproved environments. |
| Backup and recovery | Velero, PostgreSQL native backups or pgBackRest, MinIO versioning | Strong fit for infrastructure and operational state. Graph exports need a LATTICE-aware restore procedure layered on top. |
| Feature flags and progressive delivery | Argo Rollouts, Flagger | Useful later for worker/control-plane rollout. Less relevant to semantic content promotion. |
| Workflow scheduling | Temporal, Dagster, Prefect | Consider only when semantic generation and regeneration become long-running, resumable business workflows. Temporal is powerful but adds a substantial platform dependency. |

**Pragmatic compositional approach**

For the future Phase 3 skeleton, I would not build a generic pipeline. I would define a narrow LATTICE release domain model and integrate it with standard tools:

```text
LATTICE release intent and semantic gates
  -> CI or Argo Workflow executes validation and generation
  -> Cosign and in-toto attest bundle provenance
  -> OCI registry or MinIO stores immutable release bundle
  -> Argo CD promotes deployable services/configuration by environment
  -> OpenTelemetry traces generation through publication
  -> PostgreSQL + RDF record domain approval, graph lineage, and release state
```

This leaves only these LATTICE-specific responsibilities:

- Identify the immutable graph revisions and generated artifacts in a release.
- Run Surface parity, canonicalization, invalidation, and compatibility gates.
- Bind a signed manifest to semantic revisions and approved environment policy.
- Define semantic rollback as restoring an earlier immutable graph bundle, subject to authorization.
- Calculate graph-aware estate impact before profile or canonicalization changes.
- Record release, supersession, approval, and recovery provenance.

**Three viable stacks**

1. **Kubernetes-oriented**
   - Argo CD + Argo Workflows + Harbor + MinIO + Cosign + OpenTelemetry + Prometheus/Grafana + OpenBao
   - Best when the deployment target is Kubernetes and GitOps is desired.
   - Highest operational footprint.

2. **Docker Compose and CI-oriented**
   - GitHub Actions or Forgejo Actions + MinIO + Cosign + OpenTelemetry + Prometheus/Grafana + SOPS
   - Best for early phases and a small operator team.
   - Can later adopt Argo CD without changing the LATTICE release manifest model.

3. **Workflow-centric**
   - Temporal + MinIO or Harbor + Cosign + OpenTelemetry + Grafana
   - Best when release and regeneration logic must support durable waits, manual approvals, retries, and multi-day recovery.
   - Temporal should be justified by actual workflow complexity, not added preemptively.

My initial preference is **option 2**, with release bundles as OCI artifacts or MinIO objects, because it establishes immutable, signed, recoverable releases without forcing a Kubernetes platform decision. Keep the LATTICE manifest independent of the storage backend, and add Argo CD only when production deployment topology warrants it.

The next decision is whether release bundles should be **OCI artifacts** or **MinIO/S3 objects**. OCI gives strong native signing and provenance workflows. S3 objects are simpler for RDF bundles and large exports. A hybrid is reasonable: OCI for deployable images and signed manifests, MinIO for the graph/export payloads referenced by content digest.

User: I like your thinking, the 'Pragmatic compositional approach' means we don't have to pin a particular design! What we should do instead is define an interaction interface between LATTICE (which holds those specific responsibilities) and the release stack. This should support the K8s, Docker + CI, or Workflow-centric models, but now actually implement them, because release management is not a LATTICE responsibility! We just need to 

a. make sure that LATTICE can plug into one of these really easily 
b. write excellent documentation about how this works
c. do a 'reference implementation' based on your option 2 (with release bundles as OCI artefacts)

The reference implementation shows how this can be made to work with OCI artefacts, the documentation explains what a K8s implementation would need to do, and we don't have to build this at all. Our tests, if necessary, can leverage the reference implementation.

Please update the plan accordingly AND put a status in there so we know what is finished and what is outstanding. MAKE SURE all of it is in the one plan file please.

GitHub Copilot: I’ll revise the delivery plan to make LATTICE release-aware but release-stack-neutral, record Phase 0 and Phase 1 as authoring-complete, and replace bespoke Phase 3 operations with an OCI-based reference integration plus deployment-model guidance.

Read memory [](file:///c%3A/Users/U1287595/AppData/Roaming/Code/User/workspaceStorage/a3dd988cad41e14de563dacee728a5d1/GitHub.copilot-chat/memory-tool/memories/YTYyMjE3N2ItNTFjNS00ZWFiLTkyNGMtZWNjZDRmYTU3YzRj/plan.md)

The session plan file does not yet exist, so I’m creating it as the single source of truth. It will preserve the agreed long-term phases while distinguishing completed authoring work from validation and future implementation.

Created memory file [](file:///c%3A/Users/U1287595/AppData/Roaming/Code/User/workspaceStorage/a3dd988cad41e14de563dacee728a5d1/GitHub.copilot-chat/memory-tool/memories/YTYyMjE3N2ItNTFjNS00ZWFiLTkyNGMtZWNjZDRmYTU3YzRj/plan.md)

Updated the single plan file at `/memories/session/plan.md`.

The revised plan:

- Records Phase 0 and Phase 1 as **authoring complete**, with their validation gaps explicitly listed.
- Marks Phase 2, revised Phase 3, and Phases 4-7 as outstanding.
- Replaces custom release-pipeline implementation with a release-stack-neutral LATTICE integration contract.
- Defines LATTICE-owned `ReleaseIntent`, stack-owned `ReleaseReceipt`, capability negotiation, and publish, promote, rollback, export, restore, and retention operations.
- Supports Docker plus CI, Kubernetes GitOps, and workflow-centric implementations without coupling the LATTICE domain model to any one stack.
- Defines an OCI artifact reference integration using digest-addressed releases, ORAS-compatible artifact operations, and a Cosign-compatible signing abstraction.
- Includes Phase 3A, 3B, and 3C implementation steps, authoring-complete criteria, validation-environment exit criteria, documentation requirements, handoff requirements, and explicit exclusions.

User: Start implementation

GitHub Copilot: I’ll start with the revised Phase 3 contract and OCI reference adapter, while keeping it independent of Surface Phase 2 objects. First I’ll confirm the existing platform module layout and update the actual repository plan file, which was intended to be the single source of truth.

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/.github/prompts/plan-morkSurfaceImplementation.prompt.md#1-1), lines 1 to 120

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/pom.xml)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/platform-outbox/pom.xml)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/contracts/events/graph-validation-request.schema.json)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/deployment/compose/docker-compose.yml)

The repository plan was not updated by the prior planning step, so I’ve confirmed the correction needed before code can safely proceed. The platform already has a Maven reactor and event-schema convention, which supports a focused new `release-integration` module and `contracts/release` schemas.

Searched for regex `\*\*Phase 3:|\*\*Phase 4:|\*\*Package Management|\*\*Documentation` (`**/.github/prompts/plan-morkSurfaceImplementation.prompt.md`), 4 results

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/semantic-dataset-spi/src/main/java/org/nebularis/lattice/semantic/GraphReference.java)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/architecture/semantic-platform.md)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/mise.toml)

I’ll make the plan correction first, adding a status table and replacing Phase 3 with the release-stack-neutral contract, OCI reference adapter, and documentation scope. The implementation that follows will be constrained to those interfaces and fixtures, rather than a deployment pipeline.

Generating patch (68 lines) in [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/.github/prompts/plan-morkSurfaceImplementation.prompt.md)


```

```
The repository plan now contains the agreed status and Phase 3 boundary. I’m checking the edited plan for diagnostics before adding the release contract code, then I’ll implement the smallest framework-independent slice: typed intent/receipt models, capability port, and deterministic in-memory OCI-layout adapter.

Checked [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/.github/prompts/plan-morkSurfaceImplementation.prompt.md), no problems found

The plan check is clean. I’m adding a self-contained `release-integration` platform module and JSON Schema contract package. The adapter will write a standards-shaped OCI image layout locally, which keeps fixture tests offline while allowing an ORAS or registry transport to be added outside LATTICE’s semantic model.

Generating patch (215 lines) in [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/pom.xml), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/release-integration/pom.xml), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/contracts/release/release-intent.schema.json), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/contracts/release/release-receipt.schema.json), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/contracts/release/adapter-capabilities.schema.json), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/release-integration/src/main/java/org/nebularis/lattice/release/ReleaseCapability.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/release-integration/src/main/java/org/nebularis/lattice/release/ContentReference.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/release-integration/src/main/java/org/nebularis/lattice/release/SemanticGateEvidence.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/release-integration/src/main/java/org/nebularis/lattice/release/ReleaseIntent.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/release-integration/src/main/java/org/nebularis/lattice/release/ReleaseReceipt.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/release-integration/src/main/java/org/nebularis/lattice/release/ReleaseStackAdapter.java)


```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```
The first implementation slice is now present: the release contract rejects mutable or malformed digests and requires gate evidence plus tenant/project-consistent graph references. I’m checking diagnostics now, which should expose any Java API or schema mistakes before I add OCI layout packaging.

Ran terminal command: $node = Get-Command node -ErrorAction SilentlyContinue; if ($null -eq $node) { Write-Output 'Node is not available on PATH'; exit 1 }; node -e "for (const p of ['contracts/release/release-intent.schema.json','contracts/release/release-receipt.schema.json','contracts/release/adapter-capabilities.schema.json']) JSON.parse(require('fs').readFileSync(p, 'utf8')); console.log('Release schemas parse successfully')"

Checked , no problems found

The schema parsing check passed. The release adapter interface needs the complete operation set promised in the plan, so I’m extending it with default unsupported operations and implementing only the OCI-compatible `plan` and `publish` capabilities in the reference adapter. This keeps unimplemented release-stack functions explicitly external rather than silently implied.

Generating patch (198 lines) in [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/release-integration/src/main/java/org/nebularis/lattice/release/ReleaseReceipt.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/release-integration/src/main/java/org/nebularis/lattice/release/ReleaseStackAdapter.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/release-integration/src/main/java/org/nebularis/lattice/release/ReleaseSigner.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/release-integration/src/main/java/org/nebularis/lattice/release/OciLayoutReleaseAdapter.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/release-integration/src/test/java/org/nebularis/lattice/release/OciLayoutReleaseAdapterTest.java)


```

```

```

```

```

```

```

```

```

```
The OCI reference adapter now creates `oci-layout`, `index.json`, and content-addressed blobs, then returns an immutable manifest digest with optional signing evidence. I’m checking the module for editor diagnostics and reviewing the generated test surface before adding reference documentation and CI-only registry wiring.

Ran terminal command: $java = Get-Command java -ErrorAction SilentlyContinue; $maven = Get-Command mvn -ErrorAction SilentlyContinue; if ($null -eq $java -or $null -eq $maven) { Write-Output 'Java 21 and Maven are required for release-integration tests and are unavailable on PATH'; exit 1 }; mvn -f platform/pom.xml -pl release-integration test
Completed with input: $java = Get-Command java -ErrorAction SilentlyContinue; $maven = Get-Command mvn -ErrorAction SilentlyContinue; if ($null -eq $java -or $null -eq $maven) { Write-Output 'Java 21 and Maven are required for release-integration tests and are unavailable on PATH'; exit 1 }; mvn -f platform/pom.xml -pl release-integration test

Checked , no problems found

The Java editor diagnostics are clean, but the focused Maven test cannot run because Maven and Java 21 remain unavailable on this host. I’ll now complete the reference’s operational boundary: fixture data, optional registry configuration, and documentation that describes Docker plus CI, Kubernetes GitOps, and workflow-engine integrations without prescribing any of them.

Generating patch (168 lines) in [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/deployment/compose/docker-compose.yml), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/contracts/release/fixtures/release-intent-valid.json), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/contracts/release/fixtures/release-intent-missing-gate.json), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/architecture/release-stack-integration.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/operator/release-stack-reference.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/security/release-integration.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/developer/phase-3-handoff.md)


```

```

```

```

```

```

```

```

```

```

```

```

```

```
The reference now has local fixtures, an opt-in registry profile, architecture guidance, operator recovery guidance, security boundaries, and an explicit Phase 3 validation handoff. I’m doing final static checks for configuration and JSON integrity, then I’ll report exactly what remains pending behind Phase 2 and the network-enabled validation environment.

Ran terminal command: $node = Get-Command node -ErrorAction SilentlyContinue; if ($null -eq $node) { Write-Output 'Node is not available on PATH'; exit 1 }; Get-ChildItem contracts/release -Recurse -Filter *.json | ForEach-Object { [void][System.Text.Json.JsonDocument]::Parse((Get-Content $_.FullName -Raw)) }; Write-Output 'All release JSON files parse successfully'

Ran terminal command: git diff --check; git diff -- .github/prompts/plan-morkSurfaceImplementation.prompt.md platform/release-integration contracts/release deployment/compose/docker-compose.yml docs/architecture/release-stack-integration.md docs/operator/release-stack-reference.md docs/security/release-integration.md docs/developer/phase-3-handoff.md | Select-Object -First 240

Checked [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/deployment/compose/docker-compose.yml), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/.github/prompts/plan-morkSurfaceImplementation.prompt.md), no problems found

The editor diagnostics and whitespace review are clean. The first all-files JSON command was invalid because this PowerShell host lacks `System.Text.Json`, so I’m rerunning that check with the available Node runtime rather than treating its misleading success message as validation.

Ran terminal command: $node = Get-Command node -ErrorAction SilentlyContinue; if ($null -eq $node) { Write-Output 'Node is not available on PATH'; exit 1 }; node -e "for (const path of require('fs').readdirSync('contracts/release', {recursive:true}).filter(path => path.endsWith('.json'))) JSON.parse(require('fs').readFileSync('contracts/release/' + path, 'utf8')); console.log('All release JSON files parse successfully')"

Implemented the initial Phase 3 reference slice: the release-stack-neutral contract, offline OCI layout adapter, fixtures, optional registry profile, and operational documentation are now in the repository. The Phase 3 plan remains correctly marked in progress because the Surface-specific semantic-release assembly depends on Phase 2’s immutable revision and gate-evidence model.



Started the revised Phase 3 implementation.

The actual repository plan at plan-morkSurfaceImplementation.prompt.md now records Phase 0 and 1 as authoring-complete, marks Phase 3 in progress, and defines the release-stack-neutral contract and OCI reference approach.

Added a framework-independent `release-integration` Maven module with:

- `ReleaseIntent`, `ReleaseReceipt`, immutable content references, semantic gate evidence, adapter capabilities, and a complete release-stack adapter interface.
- An offline [OCI Image Layout](https://github.com/opencontainers/image-spec/blob/main/image-layout.md)-compatible reference adapter that emits `oci-layout`, `index.json`, and digest-addressed blobs.
- An optional signer port, so Cosign-compatible signing remains an external deployment adapter.
- A focused JUnit test for artifact packaging and digest-addressed receipts.

Added versioned schemas and fixtures in release, an opt-in local OCI registry profile in docker-compose.yml, and documentation for the contract, Docker plus CI reference, Kubernetes/GitOps and workflow compatibility, security boundaries, recovery, and the Phase 3 offsite validation handoff.

Validation:
- Release schemas and fixtures parse successfully with Node.
- Editor diagnostics and `git diff --check` are clean.
- Maven tests remain unrun because Java 21 and Maven are unavailable on this host. The limitation and offsite commands are documented in phase-3-handoff.md.

The remaining Phase 3 work is deliberately Surface-specific: semantic-release assembly, graph lineage and ledger integration, and impact-gate enforcement once Phase 2 supplies immutable Surface revision and approval contracts.

Made changes.

User: Please continue with the plan.

GitHub Copilot: I’ll continue with Phase 2, beginning at the control boundary that Phase 3 needs: immutable Surface contract revisions and semantic gate evidence. I’ll keep the existing Surface compiler untouched, add a dedicated workflow module around it, and defer the Studio UI until the underlying revision contract is stable.

Searched for files matching `**/surface/examples/**/*`, 4 matches

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/release-integration/src/main/java/org/nebularis/lattice/release/ReleaseIntent.java)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/surface/README.md#1-1), lines 1 to 220

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/surface/examples/employment-job-family.ttl#1-1), lines 1 to 80

The existing Surface layer already has the semantic contracts and worked fixtures needed for Phase 2. The local hypothesis is that the missing control surface is lifecycle ownership, not compiler logic, so I’ll add a `surface-workflow` module that models revision transitions and immutable release candidates while leaving surface as the semantic implementation.

Generating patch (6 lines) in [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/.github/prompts/plan-morkSurfaceImplementation.prompt.md)


```

```
Phase 2 is now marked in progress in the canonical plan. I’m checking that small status edit before creating the lifecycle module, then I’ll add only the revision state machine and release-candidate boundary needed by Phase 3.

Checked [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/.github/prompts/plan-morkSurfaceImplementation.prompt.md), no problems found

The plan status validation is clean. I’m adding the workflow slice now: explicit allowed transitions from draft through release or supersession, graph-family references for contract/profile/generated output, and conversion of a generated, approved revision into the release-stack-neutral intent already implemented in Phase 3.

Generating patch (226 lines) in [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/pom.xml), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/surface-workflow/pom.xml), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/contracts/surface/surface-revision.schema.json), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/contracts/surface/surface-release-candidate.schema.json), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/surface-workflow/src/main/java/org/nebularis/lattice/surface/SurfaceRevisionState.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/surface-workflow/src/main/java/org/nebularis/lattice/surface/SurfaceRevision.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/surface-workflow/src/main/java/org/nebularis/lattice/surface/SurfaceReleaseCandidate.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/surface-workflow/src/test/java/org/nebularis/lattice/surface/SurfaceRevisionTest.java)


```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```
The Phase 2 workflow boundary is implemented. A candidate can only be assembled from a generated, approved revision, and it carries contract, profile, and generated graph revisions into the Phase 3 release intent. I’m validating the new module and schemas before extending it with worker job contracts.

Ran terminal command: $node = Get-Command node -ErrorAction SilentlyContinue; if ($null -eq $node) { Write-Output 'Node is not available on PATH'; exit 1 }; node -e "for (const path of require('fs').readdirSync('contracts/surface', {recursive:true}).filter(path => path.endsWith('.json'))) JSON.parse(require('fs').readFileSync('contracts/surface/' + path, 'utf8')); console.log('Surface schemas parse successfully')"

Ran terminal command: $java = Get-Command java -ErrorAction SilentlyContinue; $maven = Get-Command mvn -ErrorAction SilentlyContinue; if ($null -eq $java -or $null -eq $maven) { Write-Output 'Java 21 and Maven are required for surface-workflow tests and are unavailable on PATH'; exit 1 }; mvn -f platform/pom.xml -pl surface-workflow test
Completed with input: $java = Get-Command java -ErrorAction SilentlyContinue; $maven = Get-Command mvn -ErrorAction SilentlyContinue; if ($null -eq $java -or $null -eq $maven) { Write-Output 'Java 21 and Maven are required for surface-workflow tests and are unavailable on PATH'; exit 1 }; mvn -f platform/pom.xml -pl surface-workflow test

Checked , no problems found

The Surface schemas parse and editor diagnostics are clean. Maven execution remains blocked by the missing Java 21 and Maven toolchain. Next I’m adding the AMQP-facing Surface job contract and worker boundary, preserving the existing compiler as the implementation invoked behind a graph-reference job rather than translating compiler semantics into Java.

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/workers/src/lattice_workers/graph_validation.py)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/workers/tests/test_graph_validation.py)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/tools/surface/__main__.py)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/tools/surface/cli.py#300-300), lines 300 to 366

The worker already enforces graph-reference-only input, and the existing Surface CLI gives us compilation, parity, and invalidation operations. I’m adding a generic Surface job envelope that validates scoped references and dispatches an injected adapter, keeping the transport and graph materialization outside the worker contract.

Generating patch (117 lines) in [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/contracts/events/surface-job-request.schema.json), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/contracts/events/surface-job-result.schema.json), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/workers/src/lattice_workers/surface_jobs.py), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/workers/tests/test_surface_jobs.py)


```

```

```

```

```

```

```

```
The new worker envelope now accepts generation, parity, and invalidation jobs only as scoped graph references, and it explicitly rejects raw compiler commands. I’m checking the Python and JSON surfaces now, then I’ll add the Phase 2 handoff and preserve a clear boundary between the current control plane and the later Studio UI.

Ran terminal command: $node = Get-Command node -ErrorAction SilentlyContinue; if ($null -eq $node) { Write-Output 'Node is not available on PATH'; exit 1 }; node -e "for (const path of require('fs').readdirSync('contracts/events', {recursive:true}).filter(path => path.endsWith('.json'))) JSON.parse(require('fs').readFileSync('contracts/events/' + path, 'utf8')); console.log('Event schemas parse successfully')"

Ran terminal command: $python = Get-Command python -ErrorAction SilentlyContinue; $launcher = Get-Command py -ErrorAction SilentlyContinue; if ($null -eq $python -and $null -eq $launcher) { Write-Output 'Python is unavailable, so Surface worker tests cannot run locally'; exit 1 }; if ($null -ne $python) { python -m pytest workers/tests/test_surface_jobs.py } else { py -3.11 -m pytest workers/tests/test_surface_jobs.py }
Completed with input: $python = Get-Command python -ErrorAction SilentlyContinue; $launcher = Get-Command py -ErrorAction SilentlyContinue; if ($null -eq $python -and $null -eq $launcher) { Write-Output 'Python is unavailable, so Surface worker tests cannot run locally'; exit 1 }; if ($null -ne $python) { python -m pytest workers/tests/test_surface_jobs.py } else { py -3.11 -m pytest workers/tests/test_surface_jobs.py }

Checked [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/workers/src/lattice_workers/surface_jobs.py), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/workers/tests/test_surface_jobs.py), no problems found

Event schemas parse successfully and Python diagnostics are clean. The worker test cannot execute because `python` resolves to the Windows Store alias rather than an interpreter, so I’m documenting the Phase 2 validation matrix and the existing SaaS, clinical, and employment fixtures as the canonical inputs for offsite worker-path testing.

Generating patch (62 lines) in [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/surface/README.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/surface/docs/revision-lifecycle.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/developer/phase-2-handoff.md)


```

```

```

```

```

```
The Phase 2 lifecycle and handoff documentation now make the current implementation boundary explicit and point validation at the existing Surface fixtures. I’m running the final static review for this slice, including whitespace and all newly added contract JSON, while leaving unavailable compiler and worker execution clearly unverified.

Ran terminal command: $node = Get-Command node -ErrorAction SilentlyContinue; if ($null -eq $node) { Write-Output 'Node is not available on PATH'; exit 1 }; node -e "for (const base of ['contracts/events','contracts/surface']) for (const path of require('fs').readdirSync(base, {recursive:true}).filter(path => path.endsWith('.json'))) JSON.parse(require('fs').readFileSync(base + '/' + path, 'utf8')); console.log('Surface and event contract JSON parse successfully')"

Ran terminal command: git diff --check; git diff --stat; git status --short

Checked [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/surface/README.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/surface/docs/revision-lifecycle.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/developer/phase-2-handoff.md), no problems found

This implementation slice is statically coherent: all Surface and event contract JSON parses, editor diagnostics are clean, and `git diff --check` reports no whitespace failures. The accumulated worktree has pre-existing unrelated deletions and generated files, which remain untouched. Phase 2 stays in progress because the persistent graph-store adapter, AMQP runtime, Contract Studio UI, and end-to-end validation remain outstanding.



Continued Phase 2 with the control-plane foundation required by the revised Phase 3 release integration.

Added surface-workflow, which models immutable Surface revision transitions:

`DRAFT -> REVIEW_REQUESTED -> APPROVED -> GENERATED -> RELEASED`, with explicit supersession.

A generated revision now requires approval evidence and an immutable generated graph reference. A `SurfaceReleaseCandidate` carries contract, profile, and generated graph families, output digests, and semantic gate evidence into the Phase 3 `ReleaseIntent`.

Added contracts for revisions and release candidates in surface, plus graph-reference-only worker contracts for generation, parity, and invalidation in events. The worker dispatcher rejects RDF, credentials, browser tokens, and raw shell commands, and ensures all graph references use the same tenant and project scope.

Documented the lifecycle in revision-lifecycle.md and added the offsite command matrix and outstanding work in phase-2-handoff.md. The canonical plan now marks Phase 2 as **in progress**.

Validation:
- Surface and event contract JSON parses successfully.
- Editor diagnostics and `git diff --check` are clean.
- Maven and Python tests remain unrun because Java 21, Maven, and a usable Python interpreter are unavailable on this host.

The next Phase 2 work is the persistent revision and graph-family adapter, AMQP consumer runtime that invokes surface, fixture-driven integration tests, and the Surface Contract Studio UI.

Made changes.

User: Before we continue, I want you to update the plan with a really important clarification: along the way, with all the code we implement, all the design decisions should be logged as ADRs and COMPREHENSIVE documentation in the architecture folder should be written to explain how everthing works, so that we can later on generate user guides and so on.

Please update the plan accordingly AND please go back over all the phases you've implemented thus far and backfil the documentation with plenty of detail for future readers. (This will also help other coding agents understand what you've built so far)

GitHub Copilot: I’ll make the plan’s documentation and ADR requirement explicit first, then backfill architecture material for Phases 0, 1, the current Phase 2 control-plane slice, and the Phase 3 release integration. I’ll use focused ADRs for decisions that constrain later work and architecture guides for the operational shape, so future agents have both rationale and a coherent map.

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/adr)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/architecture)

Searched for regex `ADR-|Architecture|documentation|Phase 0|Phase 1|Phase 2|Phase 3` (`**/.github/prompts/plan-morkSurfaceImplementation.prompt.md`), 27 results

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/architecture/semantic-platform.md)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/architecture/release-stack-integration.md)

The repository already has an ADR catalogue and a small amount of architecture material, but the new platform work is only lightly described. I’ll add a documentation governance section to the plan, then create an architecture index, Phase 0 and Phase 2 guides, and decision records that connect the implemented code to existing ADRs rather than repeating ontology-level design rationale.

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/adr/README.md)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/adr/ADR-A27-invalidation-and-minimal-scope-regeneration-policy.md)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/architecture/technology-options.md)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/architecture/solution-architecture.md#1-1), lines 1 to 220

The existing ADR convention is clear, and the current architecture guides lack the detailed Phase 0-3 map needed for safe extension. I’ll add a universal documentation-discipline section to the plan rather than duplicating the rule under every phase, then validate that single plan update before backfilling the ADR and architecture set.

Generating patch (16 lines) in [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/.github/prompts/plan-morkSurfaceImplementation.prompt.md)


```

```
The plan now makes ADRs and architecture documentation mandatory artifacts for every material decision and phase handoff. I’m checking that update before adding the detailed documentation set, then I’ll link each guide and ADR to the modules and contracts it governs.

Checked [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/.github/prompts/plan-morkSurfaceImplementation.prompt.md), no problems found

I’m now backfilling four ADRs and four architecture guides: toolchain and environment ownership, the semantic-platform boundary, the Surface revision workflow, and the release-stack-neutral contract. The guides will be implementation-facing and cross-link contracts, code, operational docs, and existing ontology ADRs.

Generating patch (220 lines) in [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/adr/ADR-A29-repository-toolchain-and-environment-boundary.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/adr/ADR-A30-shared-semantic-platform-cross-runtime-boundary.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/adr/ADR-A31-release-stack-neutral-integration-contract.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/adr/ADR-A32-surface-revision-lifecycle-and-release-candidates.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/architecture/implementation-map.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/architecture/repository-delivery-foundation.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/architecture/surface-workflow.md)


```

```

```

```

```

```

```

```

```

```

```

```

```

```
The new ADRs and architecture map are in place, covering the implemented responsibility boundaries and the parts still deliberately deferred. I’m checking the documentation set for diagnostics and patch hygiene before enriching the existing semantic-platform and release-integration guides and registering the ADRs in the catalogue.

Ran terminal command: git diff --check

Checked [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/architecture/implementation-map.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/architecture/repository-delivery-foundation.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/architecture/surface-workflow.md), no problems found

The new documentation passes editor checks and `git diff --check`. I’m now bringing the earlier Phase 1 and Phase 3 guides up to the same standard, adding control-flow, trust, failure, and validation detail, and indexing the four new ADRs so future readers can discover them from the existing catalogue.

Generating patch (176 lines) in [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/architecture/semantic-platform.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/architecture/release-stack-integration.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/adr/README.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/developer/toolchain.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/developer/windows-wsl.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/developer/offline-phase-handoff.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/developer/phase-handoff-template.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/developer/phase-0-1-handoff.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/developer/phase-2-handoff.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/developer/phase-3-handoff.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/operator/release-stack-reference.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/security/release-integration.md)


```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```

```
The Phase 1 and Phase 3 guides now document their control flow, ownership, trust boundaries, extension points, and recovery behavior, and the new ADRs are indexed. I’m doing a documentation integrity pass next: editor diagnostics, local relative-link resolution, SPDX headers on the newly introduced guides, and whitespace review.

Ran terminal command: const fs=require('fs'),path=require('path'); const files=['docs/architecture/implementation-map.md','docs/architecture/repository-delivery-foundation.md','docs/architecture/semantic-platform.md','docs/architecture/surface-workflow.md','docs/architecture/release-stack-integration.md','docs/adr/ADR-A29-repository-toolchain-and-environment-boundary.md','docs/adr/ADR-A30-shared-semantic-platform-cross-runtime-boundary.md','docs/adr/ADR-A31-release-stack-neutral-integration-contract.md','docs/adr/ADR-A32-surface-revision-lifecycle-and-release-candidates.md']; let failures=[]; for(const file of files){const text=fs.readFileSync(file,'utf8'); if(!text.startsWith('<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->')) failures.push(file+' lacks SPDX header'); for(const match of text.matchAll(/\]\(([^)#]+)(?:#[^)]*)?\)/g)){const target=match[1]; if(!/^[a-z]+:///i.test(target)&&!fs.existsSync(path.resolve(path.dirname(file),target))) failures.push(file+' has missing link '+target);}} if(failures.length){console.error(failures.join('\n')); process.exit(1)} console.log('Architecture ADR headers and local links validate successfully')

Ran terminal command: git diff --check

Checked , no problems found

The ADR and architecture documentation checks are clean. One remaining consistency task is to add the repository’s SPDX header convention to the Surface lifecycle guide and link the new implementation map from the root README so future agents can find the documentation without knowing the new paths.

Generating patch (13 lines) in [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/surface/docs/revision-lifecycle.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/README.md)


```

```

```

```
The implementation map is now discoverable from the root README, and the Surface lifecycle guide follows the repository’s documentation licence convention. I’m running the final focused checks for those edits and the complete documentation backfill.

Ran terminal command: node -e "const fs=require('fs'),path=require('path'); const files=['README.md','surface/docs/revision-lifecycle.md','.github/prompts/plan-morkSurfaceImplementation.prompt.md']; let failures=[]; for(const file of files){const text=fs.readFileSync(file,'utf8'); for(const match of text.matchAll(/\]\(([^)#]+)(?:#[^)]*)?\)/g)){const target=match[1]; if(!/^[a-z]+:///i.test(target)&&!fs.existsSync(path.resolve(path.dirname(file),target))) failures.push(file+' has missing link '+target);}} if(failures.length){console.error(failures.join('\n')); process.exit(1)} console.log('Updated documentation links validate successfully')"; git diff --check

Checked [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/README.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/surface/docs/revision-lifecycle.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/.github/prompts/plan-morkSurfaceImplementation.prompt.md), no problems found

The plan, ADR catalogue, architecture guides, SPDX headers, local documentation links, and whitespace checks are all clean. The documentation now distinguishes authoring-complete work from deferred or unvalidated work, so it can guide future implementation without overstating runtime verification.



Updated the canonical plan with a mandatory documentation discipline: every durable design decision requires an ADR, every delivered capability requires an architecture guide, and every phase handoff must inventory documentation, ownership, deferrals, and actual validation status.

Backfilled the implementation documentation:

- Implementation map provides the reading order, code-to-contract map, dependency direction, and current validation state.
- Repository delivery foundation explains `mise`, native dependency ownership, CI, Dev Container, Compose, and extension rules.
- Shared semantic platform now documents ownership, graph-reference rules, event flow, retry behavior, trust boundaries, and known deployment gaps.
- Surface workflow control plane explains graph families, revision transitions, worker dispatch, release handoff, and Phase 2 limitations.
- Release-stack integration now explains contract lifecycle, adapter capabilities, OCI layout contents, promotion, recovery, retention, and operational evidence.

Added and indexed these ADRs:

- ADR-A29: repository toolchain and environment boundary.
- ADR-A30: scoped graph references and cross-runtime platform boundary.
- ADR-A31: release-stack-neutral contract and OCI reference.
- ADR-A32: Surface lifecycle and immutable release candidates.

I also added SPDX headers to the new documentation and linked the architecture map from README.md.

Validation passed for editor diagnostics, local Markdown links, SPDX header checks on the new ADR and architecture documents, and `git diff --check`. Runtime tests remain unrun because this host still lacks Java 21, Maven, and a usable Python interpreter.

Made changes.

User: Excellent. Now plese continue with the phase/plan.

GitHub Copilot: I’ll continue Phase 2 with the next missing control-plane component: a durable revision-ledger boundary with optimistic concurrency. The current lifecycle rules are pure values, so the local hypothesis is that a repository port plus PostgreSQL-ready migration will let later API and AMQP code enforce those rules without embedding storage mechanics into the domain model.

Searched for files matching `**/platform/surface-workflow/**/*`, 5 matches

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/surface-workflow/src/main/java/org/nebularis/lattice/surface/SurfaceRevision.java)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/surface-workflow/src/main/java/org/nebularis/lattice/surface/SurfaceReleaseCandidate.java)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/surface-workflow/src/test/java/org/nebularis/lattice/surface/SurfaceRevisionTest.java)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/.github/prompts/plan-morkSurfaceImplementation.prompt.md#1-1), lines 1 to 210

The next implementation slice is now defined: persistence must enforce optimistic concurrency, while semantic transitions stay in `SurfaceRevision`. I’m adding a repository port, an in-memory contract-test adapter, a PostgreSQL JDBC adapter with a migration, and tests that prove stale updates cannot overwrite a newer revision.

Generating patch (271 lines) in [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/surface-workflow/src/main/java/org/nebularis/lattice/surface/VersionedSurfaceRevision.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/surface-workflow/src/main/java/org/nebularis/lattice/surface/StaleSurfaceRevisionException.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/surface-workflow/src/main/java/org/nebularis/lattice/surface/SurfaceRevisionRepository.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/surface-workflow/src/main/java/org/nebularis/lattice/surface/InMemorySurfaceRevisionRepository.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/surface-workflow/src/main/java/org/nebularis/lattice/surface/JdbcSurfaceRevisionRepository.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/surface-workflow/src/main/resources/db/migration/V1__surface_revision_ledger.sql), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/surface-workflow/src/test/java/org/nebularis/lattice/surface/InMemorySurfaceRevisionRepositoryTest.java)


```

```

```

```

```

```

```

```

```

```

```

```

```

```
The ledger boundary is now implemented with immutable semantic references kept out of PostgreSQL, an optimistic version column for workflow state, and a test double that makes stale-write behavior deterministic. I’m validating diagnostics and the migration shape next. Maven tests remain the preferred executable check, but the host toolchain has not yet provided Java 21 or Maven.

Ran terminal command: $sql = Get-Content 'platform/surface-workflow/src/main/resources/db/migration/V1__surface_revision_ledger.sql' -Raw; if ($sql -notmatch 'revision_version bigint not null' -or $sql -notmatch 'generated_graph_iri text') { Write-Error 'Surface ledger migration is missing required immutable graph or optimistic concurrency fields'; exit 1 }; Write-Output 'Surface ledger migration contains graph and concurrency fields'

Ran terminal command: $java = Get-Command java -ErrorAction SilentlyContinue; $maven = Get-Command mvn -ErrorAction SilentlyContinue; if ($null -eq $java -or $null -eq $maven) { Write-Output 'Java 21 and Maven are required for surface-workflow tests and are unavailable on PATH'; exit 1 }; mvn -f platform/pom.xml -pl surface-workflow test
Completed with input: $java = Get-Command java -ErrorAction SilentlyContinue; $maven = Get-Command mvn -ErrorAction SilentlyContinue; if ($null -eq $java -or $null -eq $maven) { Write-Output 'Java 21 and Maven are required for surface-workflow tests and are unavailable on PATH'; exit 1 }; mvn -f platform/pom.xml -pl surface-workflow test

Checked , no problems found

The ledger migration’s required fields are present and the Java sources have no editor diagnostics. The Maven test remains blocked by the missing toolchain. Because this introduces a durable concurrency and operational-state decision, I’m recording it in an ADR and expanding the Surface workflow architecture and handoff before taking the next implementation slice.

Generating patch (62 lines) in [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/adr/README.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/architecture/surface-workflow.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/developer/phase-2-handoff.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/adr/ADR-A33-surface-revision-ledger-and-optimistic-concurrency.md)


```

```

```

```

```

```

```

```
The persistence decision is now recorded as ADR-A33, and the architecture guide explains what is operational state versus RDF semantic state, including conflict behavior. I’m validating the new ADR and documentation links before deciding the next Phase 2 implementation hop.

Ran terminal command: node -e "const fs=require('fs'),path=require('path'); const files=['docs/adr/ADR-A33-surface-revision-ledger-and-optimistic-concurrency.md','docs/architecture/surface-workflow.md','docs/developer/phase-2-handoff.md']; let failures=[]; for(const file of files){const text=fs.readFileSync(file,'utf8'); if(!text.startsWith('<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->')) failures.push(file+' lacks SPDX header'); for(const m of text.matchAll(/\]\(([^)#]+)(?:#[^)]*)?\)/g)){if(!/^[a-z]+:///i.test(m[1])&&!fs.existsSync(path.resolve(path.dirname(file),m[1]))) failures.push(file+' has missing link '+m[1]);}} if(failures.length){console.error(failures.join('\n'));process.exit(1)} console.log('Surface ledger documentation validates successfully')"; git diff --check

Checked [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/adr/ADR-A33-surface-revision-ledger-and-optimistic-concurrency.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/architecture/surface-workflow.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/developer/phase-2-handoff.md), no problems found

The ledger documentation checks pass. The next Phase 2 dependency is a typed command boundary over that ledger, so the Studio and an eventual HTTP adapter do not manipulate lifecycle state directly. I’ll add a service that applies explicit transitions under an expected version, plus JSON and OpenAPI contracts that describe that boundary without committing to a web framework.

Generating patch (154 lines) in [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/surface-workflow/src/test/java/org/nebularis/lattice/surface/InMemorySurfaceRevisionRepositoryTest.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/surface-workflow/src/main/java/org/nebularis/lattice/surface/SurfaceRevisionAction.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/surface-workflow/src/main/java/org/nebularis/lattice/surface/SurfaceRevisionTransition.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/surface-workflow/src/main/java/org/nebularis/lattice/surface/SurfaceRevisionService.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/contracts/surface/surface-revision-transition.schema.json), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/contracts/openapi/surface-workflow.openapi.json)


```

```

```

```

```

```

```

```

```

```

```

```
The typed command boundary and OpenAPI contract are now present. I’m checking the schemas and Java diagnostics before refining any behavior, with the focused test intended to confirm that the service returns a stale-version conflict before it evaluates a transition against newer state.

Ran terminal command: for (const file of ['contracts/surface/surface-revision-transition.schema.json','contracts/openapi/surface-workflow.openapi.json']) JSON.parse(require('fs').readFileSync(file,'utf8')); console.log('Surface transition and OpenAPI contracts parse successfully')

Ran terminal command: $java = Get-Command java -ErrorAction SilentlyContinue; $maven = Get-Command mvn -ErrorAction SilentlyContinue; if ($null -eq $java -or $null -eq $maven) { Write-Output 'Java 21 and Maven are required for surface-workflow tests and are unavailable on PATH'; exit 1 }; mvn -f platform/pom.xml -pl surface-workflow test
Completed with input: $java = Get-Command java -ErrorAction SilentlyContinue; $maven = Get-Command mvn -ErrorAction SilentlyContinue; if ($null -eq $java -or $null -eq $maven) { Write-Output 'Java 21 and Maven are required for surface-workflow tests and are unavailable on PATH'; exit 1 }; mvn -f platform/pom.xml -pl surface-workflow test

Checked [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/contracts/surface/surface-revision-transition.schema.json), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/contracts/openapi/surface-workflow.openapi.json), no problems found

The JSON contracts parse and diagnostics are clean, while Maven execution is still unavailable. Static review exposed a concurrency edge case: a stale command could evaluate against current state before returning a conflict. I’m correcting the service to reject a mismatched version immediately and strengthening the focused test to lock that behavior in.

Generating patch (16 lines) in [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/surface-workflow/src/main/java/org/nebularis/lattice/surface/SurfaceRevisionService.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/surface-workflow/src/test/java/org/nebularis/lattice/surface/InMemorySurfaceRevisionRepositoryTest.java)


```

```

```

```
The service now checks the expected version before any state transition is evaluated, and the test covers a stale command whose action would otherwise be invalid against the newer state. I’m rerunning the focused static diagnostics and Maven availability check for this repaired slice.

Ran terminal command: $java = Get-Command java -ErrorAction SilentlyContinue; $maven = Get-Command mvn -ErrorAction SilentlyContinue; if ($null -eq $java -or $null -eq $maven) { Write-Output 'Java 21 and Maven are required for surface-workflow tests and are unavailable on PATH'; exit 1 }; mvn -f platform/pom.xml -pl surface-workflow test
Completed with input: $java = Get-Command java -ErrorAction SilentlyContinue; $maven = Get-Command mvn -ErrorAction SilentlyContinue; if ($null -eq $java -or $null -eq $maven) { Write-Output 'Java 21 and Maven are required for surface-workflow tests and are unavailable on PATH'; exit 1 }; mvn -f platform/pom.xml -pl surface-workflow test

Checked [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/surface-workflow/src/main/java/org/nebularis/lattice/surface/SurfaceRevisionService.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/surface-workflow/src/test/java/org/nebularis/lattice/surface/InMemorySurfaceRevisionRepositoryTest.java), no problems found

The repaired command service is clean under editor diagnostics, but runtime Maven tests remain blocked by the host toolchain. I’m documenting the versioned command boundary and API semantics now, including the distinction between stale-version conflicts and invalid lifecycle transitions, so a later HTTP adapter and Studio do not recreate that logic.

Generating patch (33 lines) in [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/architecture/surface-workflow.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/developer/phase-2-handoff.md)


```

```

```

```
The Surface architecture and handoff now describe the command service, evidence requirements, conflict semantics, and the framework-neutral HTTP contract. I’m performing the final static check for this continuation slice, including schema parsing and patch hygiene.

Ran terminal command: node -e "const fs=require('fs'),path=require('path'); for(const file of ['contracts/surface/surface-revision-transition.schema.json','contracts/openapi/surface-workflow.openapi.json']) JSON.parse(fs.readFileSync(file,'utf8')); for(const file of ['docs/architecture/surface-workflow.md','docs/developer/phase-2-handoff.md']) for(const m of fs.readFileSync(file,'utf8').matchAll(/\]\(([^)#]+)(?:#[^)]*)?\)/g)) if(!/^[a-z]+:///i.test(m[1])&&!fs.existsSync(path.resolve(path.dirname(file),m[1]))) throw new Error(file+' has missing link '+m[1]); console.log('Surface command contracts and documentation validate successfully')"; git diff --check

Checked [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/architecture/surface-workflow.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/developer/phase-2-handoff.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/contracts/openapi/surface-workflow.openapi.json), no problems found

Completed the next Phase 2 control-plane slice: a PostgreSQL-ready revision ledger boundary, optimistic concurrency, typed lifecycle commands, and a framework-neutral API contract. Static validation is clean. Maven execution remains deferred because this host still lacks Java 21 and Maven.



Continued Phase 2 with the concurrency-safe revision control boundary that the future Studio, AMQP consumer, and release assembly need.

Added to surface-workflow:

- `SurfaceRevisionRepository` storage port.
- `InMemorySurfaceRevisionRepository` for deterministic lifecycle and stale-write tests.
- `JdbcSurfaceRevisionRepository` plus a PostgreSQL migration at V1__surface_revision_ledger.sql.
- `VersionedSurfaceRevision` and `StaleSurfaceRevisionException`.
- `SurfaceRevisionService`, `SurfaceRevisionTransition`, and closed transition actions.

The service now rejects a stale expected version before it evaluates any lifecycle action, preventing an old client or worker from acting on newer state. The database ledger stores operational lifecycle state, approval evidence, immutable graph references, and optimistic version data. RDF content remains in the semantic dataset.

Added typed contracts:

- Surface transition schema
- Framework-neutral OpenAPI contract

Documented the decision and behavior in ADR-A33, Surface workflow architecture, and the Phase 2 handoff.

Validation passed for editor diagnostics, JSON parsing, local documentation links, and `git diff --check`. Maven tests remain unrun because Java 21 and Maven are unavailable on this host.

Made changes.

User: Excellent. Please continue.

GitHub Copilot: I’ll continue Phase 2 by defining the immutable Surface graph-family boundary that sits between lifecycle state and physical graph storage. The current workflow only carries raw graph references, so the next focused addition is a typed family registry for contract, profile, preview, generated output, lowering, and invalidation-plan references, with uniqueness enforced by immutable revision hashes.

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/semantic-dataset-spi/src/main/java/org/nebularis/lattice/semantic/ScopedDataset.java)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/semantic-dataset-spi/src/main/java/org/nebularis/lattice/semantic/DatasetSnapshot.java)

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/surface-workflow/pom.xml)

Searched for regex `generatedGraph|profileGraph|contractGraph|GraphReference` (`**/platform/surface-workflow/**`), 57 results

Read [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/architecture/surface-workflow.md)

The current control plane has a lifecycle and ledger but no typed catalogue for the other immutable graph families named in the plan. I’m adding that catalogue now as an operational registry, deliberately separate from the graph store, so it can prevent one graph IRI from being reused with a different content hash while keeping RDF storage behind a later adapter.

Generating patch (145 lines) in [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/surface-workflow/src/main/java/org/nebularis/lattice/surface/SurfaceGraphFamily.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/surface-workflow/src/main/java/org/nebularis/lattice/surface/SurfaceGraphArtifact.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/surface-workflow/src/main/java/org/nebularis/lattice/surface/ImmutableGraphConflictException.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/surface-workflow/src/main/java/org/nebularis/lattice/surface/SurfaceGraphFamilyRegistry.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/surface-workflow/src/main/java/org/nebularis/lattice/surface/InMemorySurfaceGraphFamilyRegistry.java), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/platform/surface-workflow/src/test/java/org/nebularis/lattice/surface/InMemorySurfaceGraphFamilyRegistryTest.java)


```

```

```

```

```

```

```

```

```

```

```

```
The graph-family registry now recognizes all six Phase 2 families and makes registration idempotent only for the same family, owner revision, IRI, and hash. Reusing a graph IRI with different immutable content is rejected. I’m checking this slice now before documenting its storage boundary.

Ran terminal command: $java = Get-Command java -ErrorAction SilentlyContinue; $maven = Get-Command mvn -ErrorAction SilentlyContinue; if ($null -eq $java -or $null -eq $maven) { Write-Output 'Java 21 and Maven are required for surface-workflow tests and are unavailable on PATH'; exit 1 }; mvn -f platform/pom.xml -pl surface-workflow test
Completed with input: $java = Get-Command java -ErrorAction SilentlyContinue; $maven = Get-Command mvn -ErrorAction SilentlyContinue; if ($null -eq $java -or $null -eq $maven) { Write-Output 'Java 21 and Maven are required for surface-workflow tests and are unavailable on PATH'; exit 1 }; mvn -f platform/pom.xml -pl surface-workflow test

Ran terminal command: $files = Get-ChildItem 'platform/surface-workflow/src/main/java/org/nebularis/lattice/surface' -Filter '*Graph*.java'; if ($files.Count -lt 4) { Write-Error 'Expected immutable graph-family implementation files were not found'; exit 1 }; Write-Output "Found $($files.Count) graph-family implementation files"

Checked , no problems found

The graph-family sources have clean editor diagnostics and the expected implementation files are present. Maven tests remain blocked by the unavailable toolchain. I’m recording the immutability and physical-storage split in an ADR and updating the Surface architecture and handoff so future adapters know the registry is not a second graph store.

Generating patch (58 lines) in [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/adr/README.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/architecture/surface-workflow.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/developer/phase-2-handoff.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/adr/ADR-A34-surface-graph-family-registry-and-immutable-identity.md)


```

```

```

```

```

```

```

```
ADR-A34 now makes the graph-family identity rule explicit, and the architecture guide distinguishes the metadata registry from future Fuseki-backed content storage. I’m checking the updated documentation and patch hygiene now.

Ran terminal command: node -e "const fs=require('fs'),path=require('path'); const files=['docs/adr/ADR-A34-surface-graph-family-registry-and-immutable-identity.md','docs/architecture/surface-workflow.md','docs/developer/phase-2-handoff.md']; for(const file of files){const text=fs.readFileSync(file,'utf8'); if(!text.startsWith('<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->')) throw new Error(file+' lacks SPDX header'); for(const m of text.matchAll(/\]\(([^)#]+)(?:#[^)]*)?\)/g)) if(!/^[a-z]+:///i.test(m[1])&&!fs.existsSync(path.resolve(path.dirname(file),m[1]))) throw new Error(file+' has missing link '+m[1]);} console.log('Graph-family documentation validates successfully')"; git diff --check

Checked [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/adr/ADR-A34-surface-graph-family-registry-and-immutable-identity.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/architecture/surface-workflow.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/developer/phase-2-handoff.md), no problems found

The graph-family registry documentation validates cleanly. The next Phase 2 gap is the trusted worker execution adapter: the existing envelope validates inputs but does not yet turn scoped graph references into fixed compiler invocations. I’ll implement that adapter with injected graph materialization and compiler execution ports, so request payloads still cannot choose paths or commands.

Generating patch (125 lines) in [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/workers/src/lattice_workers/surface_executor.py), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/workers/tests/test_surface_executor.py)


```

```

```

```
The executor constructs fixed argument vectors for the existing compiler and only accepts file paths produced by a trusted materializer. It returns content digests rather than generated RDF. I’m checking the Python sources now. The focused tests remain the first executable check when a usable interpreter is available.

Ran terminal command: $python = Get-Command python -ErrorAction SilentlyContinue; $launcher = Get-Command py -ErrorAction SilentlyContinue; if ($null -eq $python -and $null -eq $launcher) { Write-Output 'Python is unavailable, so Surface executor tests cannot run locally'; exit 1 }; if ($null -ne $python) { python -m pytest workers/tests/test_surface_executor.py } else { py -3.11 -m pytest workers/tests/test_surface_executor.py }
Completed with input: $python = Get-Command python -ErrorAction SilentlyContinue; $launcher = Get-Command py -ErrorAction SilentlyContinue; if ($null -eq $python -and $null -eq $launcher) { Write-Output 'Python is unavailable, so Surface executor tests cannot run locally'; exit 1 }; if ($null -ne $python) { python -m pytest workers/tests/test_surface_executor.py } else { py -3.11 -m pytest workers/tests/test_surface_executor.py }

Ran terminal command: $executor = Get-Content 'workers/src/lattice_workers/surface_executor.py' -Raw; if ($executor -notmatch '"--verify-determinism"' -or $executor -notmatch '"--parity"' -or $executor -notmatch 'unsupported Surface job type') { Write-Error 'Surface executor is missing required fixed-operation safeguards'; exit 1 }; Write-Output 'Surface executor fixed-operation safeguards are present'

Checked [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/workers/src/lattice_workers/surface_executor.py), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/workers/tests/test_surface_executor.py), no problems found

Static safeguards are present, but the invalidation input deserves a stronger contract than “first source graph.” I’m tightening the envelope to name `manifestGraph` explicitly for invalidation, then passing that separately into the executor so source content and generated-manifest evidence cannot be confused.

Generating patch (86 lines) in [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/contracts/events/surface-job-request.schema.json), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/workers/src/lattice_workers/surface_jobs.py), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/workers/src/lattice_workers/surface_executor.py), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/workers/tests/test_surface_jobs.py), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/workers/tests/test_surface_executor.py)


```

```

```

```

```

```

```

```

```

```
The invalidation contract is now explicit: the manifest has its own scoped graph reference and cannot be smuggled into a positional source list. I’m revalidating the repaired worker slice now, including schema parsing and static safeguards, before documenting this execution boundary.

Ran terminal command: node -e "JSON.parse(require('fs').readFileSync('contracts/events/surface-job-request.schema.json','utf8')); console.log('Surface job request schema parses successfully')"; $executor = Get-Content 'workers/src/lattice_workers/surface_executor.py' -Raw; $job = Get-Content 'workers/src/lattice_workers/surface_jobs.py' -Raw; if ($executor -notmatch 'manifest_graph' -or $job -notmatch 'manifestGraph is only valid') { Write-Error 'Invalidation manifest separation is incomplete'; exit 1 }; Write-Output 'Invalidation manifest separation is present'

Ran terminal command: $python = Get-Command python -ErrorAction SilentlyContinue; $launcher = Get-Command py -ErrorAction SilentlyContinue; if ($null -eq $python -and $null -eq $launcher) { Write-Output 'Python is unavailable, so Surface worker tests cannot run locally'; exit 1 }; if ($null -ne $python) { python -m pytest workers/tests/test_surface_jobs.py workers/tests/test_surface_executor.py } else { py -3.11 -m pytest workers/tests/test_surface_jobs.py workers/tests/test_surface_executor.py }

Checked [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/workers/src/lattice_workers/surface_jobs.py), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/workers/src/lattice_workers/surface_executor.py), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/workers/tests/test_surface_jobs.py), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/workers/tests/test_surface_executor.py), no problems found

The repaired worker contract parses and the Python editor diagnostics are clean. Python test execution is still blocked by the Windows Store alias. I’m recording the trusted-execution and explicit-manifest decision in an ADR, then updating the architecture and validation handoff so later AMQP consumers preserve the same boundary.

Generating patch (53 lines) in [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/adr/README.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/architecture/surface-workflow.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/developer/phase-2-handoff.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/adr/ADR-A35-trusted-surface-worker-execution-boundary.md)


```

```

```

```

```

```

```

```
ADR-A35 and the architecture guide now specify fixed compiler invocation, graph materialization, output-digest-only results, and explicit invalidation manifests. I’m running the final documentation and patch-integrity checks for this continuation slice.

Ran terminal command: node -e "const fs=require('fs'),path=require('path'); const files=['docs/adr/ADR-A35-trusted-surface-worker-execution-boundary.md','docs/architecture/surface-workflow.md','docs/developer/phase-2-handoff.md']; for(const file of files){const text=fs.readFileSync(file,'utf8'); if(!text.startsWith('<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->')) throw new Error(file+' lacks SPDX header'); for(const m of text.matchAll(/\]\(([^)#]+)(?:#[^)]*)?\)/g)) if(!/^[a-z]+:///i.test(m[1])&&!fs.existsSync(path.resolve(path.dirname(file),m[1]))) throw new Error(file+' has missing link '+m[1]);} console.log('Surface worker documentation validates successfully')"; git diff --check

Checked [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/adr/ADR-A35-trusted-surface-worker-execution-boundary.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/architecture/surface-workflow.md), [](file:///c%3A/Users/U1287595/Downloads/lattice-run/lattice/docs/developer/phase-2-handoff.md), no problems found

Completed this next Phase 2 slice: immutable graph-family registration and trusted Surface compiler execution boundaries, with corresponding contracts, tests, ADRs, architecture updates, and handoff guidance. Static checks are clean. Python runtime tests remain deferred because the host only exposes the Windows Store alias, not an interpreter.



Continued Phase 2 with two connected implementation slices.

Added an immutable Surface graph-family registry in surface-workflow. It recognizes `CONTRACT`, `PROFILE`, `PREVIEW`, `GENERATED_OUTPUT`, `LOWERING_RECORD`, and `INVALIDATION_PLAN` artifacts. A scoped graph IRI can only be registered again when the family, owner revision, and revision hash are identical. Reuse with different content is rejected.

Added a trusted worker execution adapter in surface_executor.py. It materializes authorized graph references through an injected resolver, constructs fixed Surface compiler arguments, always enables determinism and parity for generation, and returns only output digests and safe diagnostics.

Invalidation jobs now require a distinct `manifestGraph` reference in surface-job-request.schema.json. It cannot be overloaded into the source graph list. This keeps generated-manifest evidence separate from source graphs.

Recorded the decisions in:

- ADR-A34
- ADR-A35

Updated Surface workflow architecture and the Phase 2 handoff.

Validation passed for editor diagnostics, event-schema JSON parsing, documentation headers and links, static executor safeguards, and `git diff --check`. Python tests remain unrun because the host has no usable interpreter on `PATH`.

Made changes.