<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# SPARQL Testkit

**Test-only.** No product module may depend on this module outside Maven `test` scope, and no runtime code may reach Jena through it. It is the engine behind `tools/testing/jena`, the third engine of the conformance runs ([ADR-A125](../../docs/architecture/decisions/ADR-A125-test-support-tooling.md)), and follows the pattern of the reasoning kit ([ADR-A83](../../docs/architecture/decisions/ADR-A83-test-only-reasoning-engine-isolation.md)).

The module wraps Apache Jena ARQ, at the platform's `jena.version`, over Jena's transactional in-memory dataset (no TDB), in a shaded command-line jar.

```bash
java -jar target/sparql-testkit.jar serve
```

keeps one JVM for many requests. Each line on standard input is one JSON request and each is answered by one line on standard output. A request that fails is answered `{"error": "..."}` and does not end the server, which ends when standard input does. Anything a library prints goes to standard error.

| Request | Answer |
|---|---|
| `{"op": "load", "format": "nquads" or "trig", "data": "..."}` | `{"result": "ok"}`. A blank node label is the same node in every load |
| `{"op": "query", "text": "..."}` | `{"form": "select" or "ask", "result": {...}}` in SPARQL 1.1 JSON results, or `{"form": "graph", "result": "..."}` in N-Triples for CONSTRUCT and DESCRIBE |
| `{"op": "update", "text": "..."}` | `{"result": "ok"}` |
| `{"op": "reset"}` | `{"result": "ok"}`, every graph emptied |
| `{"op": "drop"}` | `{"result": "ok"}`, the dataset forgotten |

A request may add `"dataset": "name"` for a dataset of its own, created empty on first use. Without it the request is for the dataset `default`.

A load and an update each run in one write transaction, so one that fails, including an update whose later operation fails, leaves the dataset as it was. A query runs in a read transaction. The default graph is the dataset's own default graph, not the union of the named graphs.

```bash
mise run bootstrap:sparql-testkit
mise run check:sparql-testkit
```
