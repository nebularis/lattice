<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Validation Pack: studio-publication PB1 to PB11

**Plan:** [studio-publication](../plans/studio-publication.md)
**Status record:** [studio-publication](../status/studio-publication.md)

One pack for the unit, each slice a section, as the `config-studio` unit's is, since the slices are built in sequence on one branch and reviewed together.

## Invariant

What a workspace refers to is read, never copied, and what leaves the studio is a version anyone can name. A part decides only where a statement is saved, and every job reads the workspace around it (ADR-A149 decision 7). A published version is immutable and named under ADR-A51's IRIs, a reference from it is pinned (ADR-A142), and every command carries an authenticated principal (PRI-54), whose workspace mode the service and the writer both check (PRI-75).

## One command

```bash
mise run check:config-studio
```

It stages the assets, then runs the stage and worker tests, the service's Maven build and tests, and the browser code's type check and unit tests. A pass is exit status 0. The worker's own suite runs with `mise run check:workers`.

## PB1: what a job reads

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| PB1-01 | a graph with a representation scheme and a concept in it, and a concept scheme with a concept / sorted in the browser / the first concept goes to mapping, the second to vocabulary | L1 | + | pass |
| PB1-02 | the same graph / sorted by the service / the same parts, and saving the first concept with its scheme as the mapping part is accepted | L3 | + | pass |
| PB1-03 | a validation of the vocabulary part / submitted / its job names every other configuration part as a context graph and not its own | L3 | + | pass |
| PB1-04 | a job naming another workspace's part as context / submitted to the writer / refused | L8 | − | pass |
| PB1-05 | a job naming a graph outside its workspace's parts as context / run by the worker / fails without reading it | L8 | − | pass |
| PB1-06 | the `policies` XML scheme with its codes moved out / compiled alone / refused with `CorrespondenceKey`, and compiled with the codes as context / not refused | L4 | + | pass |
| PB1-07 | an invalid concept scheme / validated as the target / reported and not conforming, and held only as context / not reported and conforming | L4 | + | pass |
| PB1-08 | the sample "Policies from XML and JSON" in a running studio / its XML example run / `Peril` writes `tgt:peril` for both covers | L5 | + | pass, 2026-10-31 |

`apps/config-studio/src/rdf/rdf.test.ts`, `StudioApiTest`, `WritesTest`, `workers/tests/test_config_studio_worker.py` and `workers/tests/test_config_studio_mork_tools.py`. PB1-08 was run by hand in the browser pane.

**Not covered.** A job reads the other parts as saved, so an unsaved edit elsewhere is unseen until it is saved (MEC-97). The browser's cached compilation is keyed on the other parts' revisions, which PB1-08 exercises only through the first compilation.

## PB2: who a request is from

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| PB2-01 | `local` / a request naming no principal, then one naming `reviewer` / `developer`, an administrator, then `reviewer`, not one | L3 | + | pass |
| PB2-02 | `local` / a request naming an unknown principal / `401` with `WWW-Authenticate`, while `/api/health` and `/api/session` answer | L8 | − | pass |
| PB2-03 | `local` / configured to bind `0.0.0.0` / the service refuses to start, and an unknown `LATTICE_STUDIO_AUTH` too | L8 | − | pass |
| PB2-04 | `oidc` / an RS256 token with the issuer, audience and an unexpired `sub` / accepted as that name, an administrator when `groups` holds the value | L3 | + | pass |
| PB2-05 | `oidc` / an expired token, another issuer, another audience, another key, HS256, an unsigned token, a malformed or missing header / `401` | L8 | − | pass |
| PB2-06 | `oidc` with the audience in `client_id` / a matching token without `aud`, and one with another `client_id` / accepted, then `401` | L3 | ± | pass |
| PB2-07 | a save made as `reviewer` / committed / its receipt's `cst:principal` is `reviewer` | L4 | + | pass |
| PB2-08 | `oidc` / `/mcp` without a token / `401` | L8 | − | pass |
| PB2-09 | the studio in a browser under `local` / switch from `developer` to `reviewer` in the header / the page reloads signed in as `reviewer` | L6 | + | pass |

`platform/config-studio-service/src/test/java/org/nebularis/lattice/studio/AuthTest.java`, written by a Sonnet subagent and reviewed.

**Not covered.** The browser's sign-in at a real OpenID Connect provider, by the authorization code flow with PKCE, which needs a provider and a registered client. The Word add-in under `oidc` (TD-134).

## PB3: a workspace's owner and mode

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| PB3-01 | each mode / the owner, another principal and an administrator / read, write and manage as the sketch's §6 table says | L1 | ± | pass |
| PB3-02 | a read-only workspace of `developer` / `reviewer` reads it, saves a part, deletes it / reads, then `403`, `403` | L4 | ± | pass |
| PB3-03 | a locked workspace of `developer` / `reviewer` asks for it, its graphs, its export, a job of it, and the list / `404` each, and it is absent from the list | L8 | − | pass |
| PB3-04 | a locked workspace of `reviewer` / `developer`, an administrator, lists and reads it / visible | L4 | + | pass |
| PB3-05 | `reviewer` / changes the access of `developer`'s workspace, or names another owner of their own / `403` | L8 | − | pass |
| PB3-06 | a workspace from before modes / read / shared with no owner, and locking it without an owner is refused | L3 | ± | pass |
| PB3-07 | the worker's job update, with no principal / on a locked workspace / applied | L4 | + | pass |
| PB3-08 | `reviewer` over MCP / `list_workspaces` / omits `developer`'s locked workspace | L8 | − | pass |

`platform/config-studio-service/src/test/java/org/nebularis/lattice/studio/AccessTest.java`, written by a Sonnet subagent and reviewed.

**Not covered.** The browser does not disable editing in a workspace its principal may only read. A save is refused by the writer and the refusal shown. An administrator gives an ownerless workspace an owner through the API, not the browser.

## PB4: a version, its event and its pointer

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| PB4-01 | a concept scheme with two concepts, a concept minted under it and another scheme / its publish job / a version `{lineage}/rev/1-{16 hex}` naming the lineage, holding the scheme's concepts in the version and nothing of the other scheme | L1 | + | pass |
| PB4-02 | the same content twice, a change inside the aggregate, a change outside it / prepared / the same version, another, the same | L2 | ± | pass |
| PB4-03 | a mapping scheme / prepared / its mappings and their blank nodes, each naming the version | L1 | + | pass |
| PB4-04 | a root of no unit, or one the studio names / prepared / the job fails | L1 | − | pass |
| PB4-05 | a publish job / run by the worker / succeeds naming the version, and one naming no unit fails | L4 | ± | pass |
| PB4-06 | a publish job / submitted / its input is the part as saved and its description names the unit, and a reader of a read-only workspace or a malformed unit is refused | L3 | ± | pass |
| PB4-07 | a finished publish job / published / the lineage graph holds the version as current with an event of sequence 1, its principal and workspace, and the version graph its content | L4 | + | pass |
| PB4-08 | the same version again, then another / published / no second event and `200`, then the first superseded, current moved, sequence 2 | L4 | ± | pass |
| PB4-09 | a version not under its lineage, content without its identity, a studio lineage, an unfinished job, another workspace's job / published / refused | L8 | − | pass |

`workers/tests/test_config_studio_publish.py`, `workers/tests/test_config_studio_worker.py` and `PublicationTest`.

**Not covered.** The writer does not recompute a version's digest (PB-D1). Two workspaces may publish one lineage, and both events record where they came from. Reading the registry is PB5.

## PB5: reading the registry, and publishing from the browser

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| PB5-01 | the staged assets / staged / the units table, every unit with a root class and a part, which `GET /api/publication-units` serves | L1 | + | pass |
| PB5-02 | a published lineage / `GET /api/registry/lineage?iri=…` by a principal of another workspace / its graph, and an unknown lineage `404` | L3 | ± | pass |
| PB5-03 | a published version / `GET /api/registry/version?iri=…` / its content, unchanged by later publications, and a version of no lineage `404` | L3 | ± | pass |
| PB5-04 | `GET /api/registry` / listed / every lineage with its current version | L3 | + | pass |
| PB5-05 | the studio in a browser / a concept scheme published from the Publish view, then republished unchanged / one version and one event, shown as current, holding the scheme's six concepts | L6 | + | pass, 2026-10-31, by hand in the browser pane |

`PublicationTest.theRegistryIsReadByAnyPrincipalByLineageAndVersion` and `tools/test_config_studio_stage.py`.

**Not covered.** A lineage whose IRI has a fragment, such as `…/employment#JobFamilyScheme`, names its versions inside the fragment, `…#JobFamilyScheme/rev/1-…`, which a deployment that dereferences IRIs cannot fetch apart from the lineage. The registry has no deletion, by design, so a live check removes its test lineage from the store by hand.

## PB6: depending on published versions

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| PB6-01 | a binding that refers to a followed scheme's lineage and one of its concepts / published / the lineage rewritten to the scheme's current version, which the binding's version names with `cst:pins` | L1 | + | pass |
| PB6-02 | a new edition of the scheme / the binding prepared again / a new version of the binding | L2 | + | pass |
| PB6-03 | a lineage no context holds / prepared / found in the registry and pinned | L1 | + | pass |
| PB6-04 | a reference to an unpublished unit / prepared / the job fails | L1 | − | pass |
| PB6-05 | a dependency's version as context / read by the worker / under the version's IRI and the lineage's | L4 | + | pass |
| PB6-06 | dependencies on a lineage and a version / set / stored and returned, an IRI the registry lacks `422`, another triple refused, a reader of a read-only workspace `403` | L3 | ± | pass |
| PB6-07 | a workspace following a lineage, another pinning its first version / jobs submitted before and after a second version / the follower's jobs name the current version, the pinner's the first | L4 | + | pass |
| PB6-08 | a context graph named under the registry but malformed / submitted / refused by the writer | L8 | − | pass |

`workers/tests/test_config_studio_publish.py`, `workers/tests/test_config_studio_worker.py` and `DependenciesTest`.

| PB6-09 | a scheme published in one workspace, a binding in another that follows it / the binding published in a running studio / its version's `voc:boundScheme` names the scheme's version, which it pins | L5 | + | pass, 2026-10-31 |

**Not covered.** A job reads its dependencies as resolved when it is submitted, so a version published while it runs is read by the next job.

**Found live.** The writer refused the publish job's update, since `cst:pins` was not among the predicates a worker may write, and the job stayed running. The unit tests had written job results without pins. `PublicationTest`'s finished job now carries one.

## PB7: fenced imports

| ID | Given / When / Then | Level | +/− | Result |
|---|---|---|---|---|
| PB7-01 | the same import twice, and an empty one / fenced by the worker / one digest, then the job fails | L1 | ± | pass |
| PB7-02 | a fence job / submitted with a body / queued with the body as its input, and a reader of a read-only workspace refused | L3 | ± | pass |
| PB7-03 | the same content fenced from two workspaces / held / one graph, held by both | L4 | + | pass |
| PB7-04 | a held import / read by its workspace, and by one that does not hold it / its graph, then `404` | L3 | ± | pass |
| PB7-05 | an import released by one workspace / read by the other / still there | L4 | + | pass |
| PB7-06 | a workspace holding an import / a validation submitted / the import is a context graph, and a job naming an import the workspace does not hold is refused | L8 | ± | pass |
| PB7-07 | a publish job with `target=import` / submitted / its input is the import's content | L3 | + | pass |
| PB7-08 | a SKOS scheme imported into two workspaces in a running studio / fenced, published from the first, released by the second / one graph, a version, and still held by the first | L5 | + | pass, 2026-10-31 |

`workers/tests/test_config_studio_publish.py` and `ImportsTest`.

**Not covered.** A workspace's export omits its imports' content, and nothing removes an import no workspace holds (TD-135). The browser's other imports, such as an ODRL policy or a proposer's source vocabulary, still copy what they read into a part.
