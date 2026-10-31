<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Persistence Caller Libraries

Libraries for whoever runs the SPARQL operations the persistence compiler generates ([ADR-A132](../../docs/architecture/decisions/ADR-A132-persistence-caller-library.md)).
They build the values the store cannot check (a payload, event rows, a request digest) from typed terms, and they read what an operation expects from the compiled profile.
They make no store call. The SPARQL client is the caller's.

You do not need these libraries to call a generated operation. The compiled profile and the vectors in
[`contracts/persistence/`](../../contracts/persistence/README.md) are enough to write your own and prove it conformant.

| Directory | What it is |
|---|---|
| [`python/`](python/README.md) | `lattice-persistence` for Python 3.14 or later. Standard library and rdflib only |
| [`java/`](java/README.md) | `lattice-persistence` for JDK 25 or later. Apache Jena ARQ only, to read a compiled profile |

## Checks

```bash
mise run check:persistence-library   # the vectors, recomputed with openssl, and the library's tests
mise run check:persistence-vectors   # the vectors alone
```

## Licence

MPL-2.0.
