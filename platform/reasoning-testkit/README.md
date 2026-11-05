<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Reasoning Testkit

**Test-only.** No product module may depend on this module outside Maven
`test` scope, and no Python package may declare a reasoner, rules engine or
JVM bridge ([ADR-A83](../../docs/architecture/decisions/ADR-A83-test-only-reasoning-engine-isolation.md)).
`mise run check:reasoning-isolation` enforces this.

The module wraps HermiT 1.4.5 (LGPL-3.0) and the OWL API 5 in a library and a
shaded command-line jar. Java tests add it as a `test`-scope dependency.
Python tests call the jar as a subprocess through
`tools/mork_compilers/src/mork_compilers/reasoning.py`.

```bash
java -jar target/reasoning-testkit.jar consistent FILE...
java -jar target/reasoning-testkit.jar satisfiable CLASS FILE...
java -jar target/reasoning-testkit.jar subsumes SUB SUP FILE...
java -jar target/reasoning-testkit.jar values PROPERTY FILE...
```

Each prints one JSON line, `{"result": ...}`. `values` prints the entailed
subject and object pairs of an object property.

```bash
java -jar target/reasoning-testkit.jar serve
```

keeps one JVM for many requests. Each line on standard input is a command and its arguments separated by tabs, for example
`satisfiable<TAB>IRI<TAB>FILE`. Each is answered by one line, `{"result": ...}` or `{"error": "..."}`, and a failed request does
not end the server. The server holds the reasoners for its last four distinct closures, by file content. It ends when standard
input does. `mork_compilers.reasoning.run` uses it by default (ADR-A83, addendum of 2026-10-17).

Limits, recorded in ADR-A83's implementation notes: imports are ignored, so
pass the merged closure. SWRL rules parse only on anonymous `swrl:Imp` nodes.
Rules bind named individuals only. `swrlb` builtins are not evaluated.

```bash
mise run bootstrap:reasoning-testkit
mise run check:reasoning-testkit
```
