<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# lattice-testing-oxigraph

An in-memory [Oxigraph](https://github.com/oxigraph/oxigraph) quad store for LATTICE's tests, checks and benchmarks
([ADR-A125](../../../docs/architecture/decisions/ADR-A125-test-support-tooling.md)). It gives the persistence compiler's generated
SPARQL a second, independent engine to run on, so that what a test shows about a generated update does not rest on rdflib alone.

It is **not a store SPI** ([ADR-A75](../../../docs/architecture/decisions/ADR-A75-three-tier-store-spi.md) describes the tiers and none
is defined) and **not a runtime backend**. Its methods carry no promise to adopters, and only tests, checks and benchmarks import it.

## What it does

`OxigraphStore` loads quads, runs a SPARQL 1.1 update or query, and reads quads back. The generated operations leave the
caller's parameters as `$name` variables, and Oxigraph has no initial-binding API, so `update` and `select` fill each parameter
by putting its term text in the query, which is what a caller with no such API does. A name left out stays an unbound variable,
which is how a caller's omission is reproduced. With `strict` (the default for `bind_parameters`) a name that never appears is
an error, since a misspelt name would otherwise leave the real variable unbound.

The substitution is textual and does not look inside string literals, IRIs or comments. The generated operations have none that
hold a parameter name.

## Behaviour that changed between versions

The package requires `pyoxigraph>=0.5.13,<0.6` (TSD-40). Where a release changed what a
test asserts, the test reads a flag instead of the version number. Each flag is derived from `VERSION`, the installed version, and
`test_ox_t6` holds it to what the installed version does.

| Flag | True from | Means | Finding |
|---|---|---|---|
| `SNAPSHOT_UPDATES` | 0.5.12 | a `DELETE`/`INSERT WHERE` removes every deletion before it adds any insertion | [TSD-01](../../../docs/architecture/triple-store-discovery.md#tsd-01-the-order-in-which-a-deleteinsertwhere-is-applied) |
| `LEFT_GROUPED_ARITHMETIC` | 0.5.12 | `a - b + c` and `a / b / c` are grouped from the left | [TSD-17](../../../docs/architecture/triple-store-discovery.md#tsd-17-a-chain-of-additions-and-subtractions) |
| `CONSTANT_GRAPH_INLINED_IN_OPTIONAL` | below 0.5.13 | a `GRAPH ?g` inside an `OPTIONAL`, with `?g` bound to a constant IRI by the enclosing group, reads only that graph. A computed `?g` is read as every graph on all three versions | [TSD-45](../../../docs/architecture/triple-store-discovery.md) |

## Install and run

```bash
mise run bootstrap:testing-oxigraph
mise run check:persistence              # the default engine of the persistence tests, with this package's own tests
mise run check:persistence-conformance  # every engine we have, and the conformance tests (on demand and before a merge)
```

Oxigraph is the default engine of the persistence tests (ADR-A125, addendum of 2026-10-21), so `check:persistence` depends on this
package. The engines a test marked `each_engine` runs on come from `PERSISTENCE_ENGINES` (for example `rdflib,oxigraph`), and are
Oxigraph alone when it is unset. The Oxigraph cases skip where this package is absent.
