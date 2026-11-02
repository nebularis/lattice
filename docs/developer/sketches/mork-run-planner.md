<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# A planner for running MORK mappings — Sketch

**Unit ID:** `mork-run-planner`
**Status:** Sketch. Options A and B built, MP-Q1 to MP-Q3 ruled 2026-10-29, option G built. It follows a study of SDM-RDFizer and of the maintainer's paused `rml-pipeline`, and asks what of theirs a MORK run should take.
**Date:** 2026-10-29
**Bears on:** [`tools/mork_rdf`](../../../tools/mork_rdf/README.md) §12 and §14, PDD-06 (a SPARQL IR), ADR-A124 (benchmarks measure and never fail on time), ADR-A128 (efficient queries).

---

## 1. Why

`mork_rdf` now runs a compiled scheme in strata (README §12). Each mapping's output is kept in a graph named for it, so a later stratum can read it, and every triple written is also held in a Python set until the run ends. That is correct and small for the studio's imports. It holds the whole output in memory twice, once in the store and once in the set, and it keeps every mapping's graph until the end even when no later stratum reads it. A deployment that maps a large source, such as a source of a million records, needs a plan that bounds memory. SDM-RDFizer is the engine in the literature that addressed exactly that, and `rml-pipeline` began a typed version of its ideas.

## 2. What SDM-RDFizer does

Read from the source at version 4.7.5.15.4.1 (`rdfizer/rdfizer/functions.py` and `rdfizer/rdfizer/__init__.py`) and from its README. Its papers are the CIKM 2020 resource paper and the Semantic Web Journal article it links. Version 4.0 added the planning and compression this sketch is about.

### 2.1 The structures

| Structure | In the code | Holds | Freed |
|---|---|---|---|
| PTT, predicate tuple table | `g_triples`, keyed by a predicate's id, each a set of `subject_object` id pairs | the triples already written for one predicate, so a duplicate is not written twice | when the last triples map that writes the predicate is done (`release_PTT`) |
| dictionary | `dic_table`, every term written to a base-36 id (`dictionary_table_update`, `base36encode`) | short keys for the PTTs, so a PTT holds ids, not IRIs | never |
| PJTT, predicate join tuple table | `join_table`, keyed by parent map and join condition, from the parent's key value to its subjects (`hash_maker`) | a referencing object map's join, built once from the parent source and probed per child row | not freed in the code read |
| subject cache | `generated_subjects`, per triples map, from the subject template's attribute values to the subject (`mappings_expansion`) | the subject one row makes, shared by the partitions of its map | when the map's last partition is done (`release_subjects`) |

The dictionary is the "compression". It does not shrink the output, which is written to the file as it is made. It shrinks the deduplication state, the part that grows with the output.

### 2.2 The plan

`files_sort` groups the triples maps by source and counts how many maps write each predicate. `source_sort` then orders the sources greedily. It takes the source with the fewest predicates, adds every source that shares a predicate with it, and repeats on what is left. So the maps that write a predicate run close together, the predicate's count reaches zero early, and its PTT is freed early. A predicate such as `rdfs:subClassOf` or `owl:sameAs` that many maps write is counted per predicate and object (`general_predicates`), so it does not hold one PTT for the whole run.

With mapping partitions on, `mappings_expansion` splits each triples map into one map per predicate-object map, as Morph-KGC does. Each partition then writes one predicate, and the subject cache spares re-forming the subject per partition.

### 2.3 What the evaluation says

The README reports that version 4.0 completes every testbed of the SDM-Genomic datasets (10k to 1M records, 25% and 75% duplicates) and GTFS-Madrid (scales 1 to 50), and has the smallest peak memory of the versions and engines compared. We have not reproduced it.

## 3. What `rml-pipeline` began

An F# library, paused. Its `docs/Architecture.md` and `src/RMLPipeline/Planner.fs` take RDFizer's planning to compile time and add a typed runtime:

- **Planning at compile time.** String extraction and interning, dependency analysis, join pre-computation and an index strategy per map, done once.
- **Dependency groups.** `groupByDependencies` takes the transitive closure of each map's join dependencies, so independent groups run in parallel with no coordination and every synchronisation point is known before the run.
- **Overlap.** `detectOverlaps` scores each pair of maps by a shared iterator path and the share of predicate tuples they have in common, keeping pairs above 0.1.
- **Index strategy.** `chooseIndexStrategy` picks no index, a hash index or a full index from a map's estimated complexity, its dependency count and the memory mode, with presets of 64, 256 and 1,024 MB.
- **String pools in three tiers.** A global pool of planning strings, immutable after planning so reads need no lock, a pool per dependency group behind a reader-writer lock, and a small pool per worker sized for L1 and L2 cache. Strings are 32-bit `StringId`s from fixed ranges, so no counter is contended, and a string can be promoted from local to group to global.
- **Cache-sized tuples.** A predicate tuple of four `StringId`s, a hash and flags, 24 to 32 bytes, so two fit a cache line.

Its own list of what is outstanding includes releasing strings and ids, which is the step RDFizer's counts provide.

## 4. Where a MORK run differs

| | RDFizer and `rml-pipeline` | a MORK run |
|---|---|---|
| what executes | the engine's own loop over rows, writing triples | SPARQL on a store, so the store's own join, index and term encoding |
| joins | a referencing object map joins two sources on a condition | a child runs in its parent's context, so most joins are along the chain of one focus node. The cross-source join is a lookup, into reference data or into an earlier mapping's output |
| order | any order gives the same output, and the plan chooses one for memory | strata are required, since a later stratum reads what an earlier one made (§12) |
| deduplication | the engine's PTTs | the store's set semantics within a graph, plus the runner's set |
| what is kept | nothing after the run but the output file | a T-Box graph returned apart, and a regulator's need to trace each triple to the mapping that wrote it |

Two consequences. First, string pooling is a store's job while we run on a store. We believe Oxigraph encodes terms to ids in its storage, but we have not read it (TSD-Q5 is near this), so a planner should not rebuild it until a measurement shows the runner's own copies are the cost. Second, the plan's main lever moves from "which order frees memory soonest" to "which graphs can be dropped, and which queries can share a scan".

## 5. What a run costs now

Measured 2026-10-29 on the maintainer's laptop, with the catalogue fixture's mapping (`tools/mork_rdf/tests/fixtures`) over synthetic book records of ten source triples each, one process per size, peak resident memory from `getrusage`.

| Records | Source triples | Output triples | Before the run | Peak | Run time |
|---|---|---|---|---|---|
| 2,000 | 20,000 | 18,000 | 77 MB | 207 MB | 0.6 s |
| 8,000 | 80,000 | 72,000 | 163 MB | 509 MB | 2.6 s |
| 32,000 | 320,000 | 288,000 | 529 MB | 1,269 MB | 12.3 s |

The peak grows by about 35 KB a record, about 1.9 KB for each source or output triple. About 15 KB a record is the rdflib graph the source arrives in, before the run starts. The rest is the copies the runner makes: the source serialised and canonicalised to skolemise it, the store, each mapping's output graph, the set of every triple written and the rdflib graph returned. Time grows by about 0.38 ms a record.

With options A and B built and the source loaded by Oxigraph from its file, with no rdflib graph on the way, benchmark `check:mork-rdf-run-cost` measured, on 2026-10-29: 10,000 records peaking at 425 MB in memory and 339 MB streamed, and 100,000 records at 1,447 MB and 1,514 MB, in 43 s and 23 s. At 100,000 records the peak is set before any query runs, by skolemising: a plain load of the same file peaks at 558 MB, and canonicalising its 100,000 blank nodes with RDFC-1.0 at 1,699 MB. So the 10⁶ tier needs about 15 GB, not the 35 GB the first estimate gave, and the next lever is option G.

Before them, extrapolated linearly, which the checks' `GROUP BY` may not be:

| Records | Peak | Run time |
|---|---|---|
| 10⁴ | 0.4 GB | 4 s |
| 10⁵ | 3.6 GB | 40 s |
| 10⁶ | 35 GB | 7 min |

## 6. Options

Each is independent, and they are listed cheapest first. The figures are estimates for a source of N focus nodes, Q queries and an output of T triples, to be measured by the benchmark of §8 before any is built.

| Option | Takes from | What it does | Space | Time | Ruling |
|---|---|---|---|---|---|
| A. Release by count | RDFizer's PTT counts | count, per mapping, the queries of later strata that read its graph, and drop the graph when the count reaches zero | peak falls from every mapping's output to the outputs some later stratum still needs | none | agreed and built 2026-10-29 |
| B. Stream to a sink | RDFizer's file output | hand each construct's triples to a sink as the store yields them, and keep in the store only the graphs a later stratum reads | the set of every triple written and the returned graph go, about half of what the run adds today | none, and the first triples reach the sink before the run ends | agreed and built 2026-10-29, with a pluggable sink (§7) |
| C. Share a scan | RDFizer's grouping by source, Morph-KGC's partitions | evaluate a chain of frames once for every construct that shares it (§6.1) | unchanged | the chain's work is done once, not once per construct | to measure |
| D. Hash a lexical lookup | RDFizer's PJTT | for a `mork:LexicalComparison` lookup, write each reference value's `STR()` to a key once, then join on the key | one key per reference value | from N × M comparisons to N + M, for example 2.5 million to 10,250 for 10,000 values and 250 codes | later, if a lexical lookup over a large scheme is real |
| E. Partition the source | Morph-KGC, `rml-pipeline`'s chunks | run stratum 0 per partition of the root classes, the partitions independent | bounded by the largest partition | parallel across partitions | on the roadmap, after PDD-06 |
| G. Skolemise without full canonicalisation | none of them, since RML engines never skolemise | label a blank node from its position, the named node and predicates that reach it and its own triples, and fall back to RDFC-1.0 only where two blank nodes cannot be told apart, such as two authors both named Anon | about 1.1 GB less at 10⁵ blank nodes | less, canonicalisation being the dearest step | built 2026-10-29 as a new rule, version 1, in `tools/mork_rdf` README §12.2 and ADR-A147 (Proposed), because RDFC-1.0's whole-source labels also renumbered nodes when unrelated data was added. Skolemising 100,000 records fell from 1,699 MB to 857 MB, and a streamed run to 1,041 MB in 13.4 s |
| F. An engine of our own | `rml-pipeline` | compile the IR of PDD-06 to a physical plan executed in process, with interned ids and cache-sized tuples | the lowest | the highest, and a second evaluator to keep equal to the SPARQL one | on the roadmap, after PDD-06 |

A further saving needs no option. A source given as N-Triples can be loaded into the store directly, skipping the rdflib graph that holds about 40% of the peak today.

### 6.1 What sharing a scan buys

Today each construct beneath a root repeats the root's chain: the type scan, the identity's paths and the `BIND` that forms the target IRI. A root with k constructs beneath it does that work k times. Sharing the scan does it once, so the time a run spends forming targets falls by up to (k − 1)/k, and the rest, each construct's own patterns, is unchanged. The catalogue's item has eight constructs beneath one chain, so if the chain is about half of each query's work, the run's time would fall by about 40%. That is a hypothesis for the benchmark.

How the constructs are merged decides whether it pays. Making each construct's own patterns `OPTIONAL` beside the chain multiplies rows when two of them are multi-valued, two authors and three titles giving six rows, so the work rises. Writing them as one join of the chain with a `UNION` of their own patterns gives each its own rows, evaluates the chain once, and keeps a group to two operands (STD-027). Merging also removes a query's fixed cost, its parse and plan, which matters most for many small mappings. Space is unchanged, because the store holds the same graphs.

## 7. A pluggable sink

A run hands each construct's triples, with its stratum and mapping, to a sink, and the sink decides where they go. The runner keeps a stratum's output in its working store only while a later stratum reads it (option A), and never reads from the sink, so the sink never has to be queryable.

- **In memory**, an rdflib graph, which is what the studio and the tests use today.
- **N-Triples to a file or standard output**, written as the triples arrive. Standard output keeps the runner's contract to a stream of lines, so a separate listener can read it and publish to a broker such as RabbitMQ, for a consumer that loads the triples into Jena or another store.
- **A queue** with a bound, for a sink in another process, so a slow consumer slows the run instead of filling memory.

A broker client inside the runner is not proposed. The listener keeps the runner free of a dependency each deployment would choose differently.

`Flux.IO`, the maintainer's F# library that `rml-pipeline` was to be built on, has the shape a streaming runner needs: stages typed as sources, transforms, accumulators, branches, merges and sinks, envelopes that carry a sequence number, trace context and a cost in bytes, batches with windows, and effect handles over several concurrency backends. Its own notes leave backpressure, cancellation and a non-blocking scheduler to do. It belongs with option F, if a runtime of our own is ever built.

## 8. Rulings and answers

| ID | Question | Ruling |
|---|---|---|
| MP-Q1 | Is a benchmark of `mork_rdf` on synthetic sources of 10⁴, 10⁵ and 10⁶ records, measuring peak memory and time per stratum, the first step? | yes, 2026-10-29. By §5 the 10⁴ and 10⁵ tiers fit a laptop, and the 10⁶ tier needs about 35 GB before options A and B and the direct load, so it is opt-in, for a cloud run |
| MP-Q2 | Should the output graph of a mapping that no later stratum reads be kept for traceability anyway? | no, 2026-10-29. The input and the mapping reconstruct every intermediate step, so the construct's mapping in `text()` is enough. Keeping the input is the deployment's choice, and LATTICE takes no position on it |
| MP-Q3 | Where does the planner belong? | as §9 proposes, ratified 2026-10-29: the logical plan with the shared MORK reader, the SPARQL rewrites with PDD-06's IR, the sink as egress |

## 9. Where the planner belongs

Planning a mapping graph has three parts, and only the middle one depends on the backend.

1. **The logical plan** says which mappings read which others' outcomes, the strata that follow, and when each output can be released. It is a property of MORK's DAG, `mork:deferredMapping`, `mork:dependentMapping` and the deferred references, and every backend needs it: the SPARQL runner, `mork2rml`, and a later backend that generates a transform such as XSLT or JOLT, or an endpoint that consumes JSON or XML and writes to the graph SPI. It belongs with the shared MORK reader (MR-Q5, TD-124).
2. **The physical plan** is the backend's own. For SPARQL it is rewrites of queries, such as sharing a scan, which are rewrites of PDD-06's algebra and can live with that IR, beside the persistence compiler's. For RML the engine plans its own joins, partitions and deduplication, as SDM-RDFizer does, so `mork2rml` should emit triples maps in the logical plan's order and leave the rest to the engine. For a generated transform it is the order of its templates.
3. **The sink** is egress. The plan hands batches to it and never reads them back (§7).

So putting the planner in PDD-06's unit would couple MORK's ingress semantics to the persistence compiler, whose queries are writes governed by persistence profiles. Putting the logical plan in the MORK reader, and only the SPARQL rewrites in the IR's unit, keeps ingress and egress apart. The one dependency left is that a SPARQL backend's rewrites are written against the IR.
