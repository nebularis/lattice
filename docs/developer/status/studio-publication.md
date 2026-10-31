<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Publication from the Configuration Studio - Status

**Unit ID:** `studio-publication`
**Status:** 🟡 PB1 and PB2 built 2026-10-31, PB3 next
**Last updated:** 2026-10-31
**Plan:** [studio-publication.md](../plans/studio-publication.md)
**Sketch:** [studio-publication.md](../sketches/studio-publication.md)
**ADR:** [A-149](../../architecture/decisions/ADR-A149-publication-from-the-studio.md), Proposed
**Branch:** `claude/config-authoring-studio`

## Current position

The maintainer answered PB-Q1 to PB-Q3, PB-Q6 and PB-Q7 on 2026-10-31, asked for pluggable authentication with a simple default now, and left PB-Q4's timing of workspace modes and PB-Q5 to the unit. The unit chose modes with authentication in phase B, and the studio's own store on persistence profiles after publication, in phase D. The maintainer asked for the whole plan to be built in order, with a Sonnet subagent for mechanical work.

**Decisions taken alone, for ratification:** PB-D1 to PB-D5 in the plan's §2, and ADR-A149 decisions 9 and 11.

PB1 was built on 2026-10-31. A validation, compilation or dry run names the workspace's other parts as context graphs, which the worker reads like the baseline, reporting only on the target part. A concept goes with its scheme when the scheme went to mapping, in the browser and the service. TD-133 is closed. The `policies` sample's `Peril` writes both covers' perils live. Checks run 2026-10-31, all passing: `check:config-studio`, `check:workers` (163), `check:knowledge`, `check:identifiers`. The Java side was written by a Sonnet subagent and reviewed.

One Validation Pack holds every slice, each a section, as the `config-studio` unit's does.

PB2 was built on 2026-10-31. The service authenticates every request but `/api/health` and `/api/session` through a pluggable `Authenticator`: `local`, the default, which offers the developer principals `developer`, who administers, and `reviewer`, and refuses any address but loopback, and `oidc`, which validates a provider's bearer tokens with `nimbus-jose-jwt` 10.3 against its published keys, for any provider such as Okta, Microsoft Entra ID or AWS Cognito. Every command carries its principal, which the writer records on its receipt. The browser signs in through `/api/session`, with a principal picker under `local` and the authorization code flow with PKCE under `oidc`. TD-134 records that the Word add-in sends no credentials. Checks run 2026-10-31, all passing: `check:config-studio`, `check:knowledge`, `check:identifiers`, and the service module's 101 tests. The tests were written by a Sonnet subagent and reviewed. Checked live under `local`: the header shows the principal, switching to `reviewer` signs in as reviewer, and an unknown name is refused.

**Next action:** build PB3.

## Log

- 2026-10-31: the maintainer challenged the part rule (MEC-94) and set out publication. Sketch, plan and ADR-A149 written. BL-08 added for uploaded files that are not graph data.
- 2026-10-31: PB1 built. TD-133 closed. MEC-94 now says where a subject is saved, and MEC-97 records a job's context.
- 2026-10-31: PB2 built. `nimbus-jose-jwt` 10.3 added to the service for token validation. TD-134 added.
