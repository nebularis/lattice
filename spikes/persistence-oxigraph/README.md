<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Spike: running the persistence compiler's updates on Oxigraph

**Status:** a spike, not production. It names no interface. In particular it is **not a store SPI**,
which has not been defined ([ADR-A75](../../docs/architecture/decisions/ADR-A75-three-tier-store-spi.md)
describes the tiers, and nothing here implements them). Nothing in `tools/` or `platform/` imports it.
**Origin:** formal-methods track H, slices H1.3 and H1.4a, where the generated SPARQL had to be
shown to do something to data, and not only read as text.

## What it is for

The persistence compiler generates SPARQL updates, and until track H nothing executed them. Two
questions needed a running engine.

1. What does a composite-boundary replace leave behind when the shape reaches more than one other
   node ([FMH-H1.4a](../../docs/developer/validation/FMH-H1-4a.md))?
2. What does the append update do when the caller leaves out a `$parameter`
   ([plan §13.4](../../docs/developer/plans/formal-methods-track-h.md), TD-34)?

The project's own tests answer both on **rdflib**. This spike adds **Oxigraph**, an independent
Rust implementation, so the answer does not rest on one engine. They agree on every scenario.

## Contents

| File | Role |
|---|---|
| `oxigraph_backend.py` | `OxigraphBackend`: an in-memory quad store with `update`, `select`, `quads` and `count`, and `bind_parameters`, which fills a template's `$name` parameters with SPARQL term text, as a caller's client would |
| `scenarios.py` | the two experiments as functions that return data |
| `run.py` | prints both experiments on Oxigraph |
| `rdflib_comparison.py` | runs the same scenarios on rdflib and on Oxigraph and compares |
| `test_spike.py` | seven checks, including that the two engines agree. Skipped without `pyoxigraph` |
| `requirements.txt` | `pyoxigraph`, for this spike only |

## Running it

From the repository root, after `mise run bootstrap` for the persistence packages.

```bash
mise exec -- python -m pip install -r spikes/persistence-oxigraph/requirements.txt
mise exec -- python spikes/persistence-oxigraph/run.py
mise exec -- python spikes/persistence-oxigraph/rdflib_comparison.py
mise exec -- python -m pytest spikes/persistence-oxigraph -q
```

It is not wired into any `mise` task or into `check`, on purpose.

## What it showed

Composite boundary, subjects that still have triples after one replace (an order with a line item,
and optionally a payment, each a separate node):

| Shape | Property the update follows | Left behind |
|---|---|---|
| one node property | `lineItem` | nothing |
| two node properties | `lineItem` | the payment |
| two node properties | `payment` | the line item |

Append, one stream, three runs. No run raises an error.

| Run | Sequence counter | Revision records | Head pointers |
|---|---|---|---|
| A. every parameter supplied | 1 | 1 | 1 |
| B. the caller forgets `$revBase` | 1 | **0** | **0** |
| C. a retry with the same transaction id and every parameter | 2 | 1 | 1 |

After C, sequence 1 has no revision record.

## Limits to know

- `bind_parameters` is textual. It does not look inside string literals, IRIs or comments. The
  generated templates have none that contain a parameter name. It replaces `?name` as well as
  `$name`, since SPARQL treats them as one variable.
- The scenarios use tiny hand-built stores. They show what an update does, and say nothing about
  performance, concurrency or transactions across requests.
- Oxigraph is a single-writer embedded store. A conclusion about interleaved writers (the protocol
  models of track H, H5 onward) cannot come from here.
- A name passed to `update` that does not appear in the text is an error by default, since a
  misspelt name would otherwise leave the real variable silently unbound.

## A correction worth keeping

An earlier version of the H-D12 walkthrough said rdflib disagreed with Oxigraph on the retry, and
attributed it to rdflib applying deletes lazily. Both were wrong. The disagreement came from two
bugs in the first scratch scripts: one counted revision records in the default graph only, and one
loaded an IRI object as a literal so a property path could not reach it. rdflib materialises the
solutions of a `WHERE` clause before it applies any change. With the scripts fixed the engines
agree, which is what `test_spike.py` now asserts.
