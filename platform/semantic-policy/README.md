<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Semantic policy

Tenant, project and role checks applied before a graph reference reaches a dataset adapter. See [Semantic platform](../../docs/architecture/semantic-platform.md) and [ADR-A30](../../docs/architecture/decisions/ADR-A30-shared-semantic-platform-cross-runtime-boundary.md).

## What it provides

| Type | Role |
|---|---|
| `Principal` | A record of subject, tenant ID, project ID and a set of roles. |
| `GraphAccessPolicy` | The interface, with one method, `requireRead(Principal, GraphReference)`. It throws when access is refused. |
| `TenantProjectGraphAccessPolicy` | The implementation. It allows a read only when the principal's tenant and project equal the reference's and the principal holds the `graph-reader` role. Otherwise it throws `SecurityException`. |

The module does not parse tokens or talk to an identity provider. The caller builds the `Principal` from claims it has already verified.

## Build and test

```bash
mise run check:java
mise exec -- mvn -f platform/pom.xml -pl semantic-policy -am verify
```

The first command builds and tests every platform module. The second builds this module and the SPI it depends on. A pass is a Maven `BUILD SUCCESS`.

## Depends on

`semantic-dataset-spi`, for `GraphReference`.
