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
| PB2-09 | the studio in a browser under `local` / switch from `developer` to `reviewer` in the header / the page reloads signed in as `reviewer` | L6 | + | see the status record |

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
