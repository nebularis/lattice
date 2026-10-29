<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# A planner for running MORK mappings — Sketch

**Unit ID:** `mork-run-planner`
**Status:** Sketch. Nothing here is decided. It follows a study of SDM-RDFizer and of the maintainer's paused `rml-pipeline`, and asks what of theirs a MORK run should take.
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

## 5. Options

Each is independent, and they are listed cheapest first. The figures are estimates for a source of N focus nodes, Q queries and an output of T triples, to be measured by a benchmark under ADR-A124 before any is built.

| Option | Takes from | What it does | Space | Time |
|---|---|---|---|---|
| A. Release by count | RDFizer's PTT counts | count, per mapping, the queries of later strata that read its graph, and drop the graph when the count reaches zero | peak falls from every mapping's output to the outputs some later stratum still needs | none |
| B. Stream the output | RDFizer's file output | write each stratum's triples to a sink as they come, and keep in the store only what a later stratum reads | the runner's set, O(T) Python objects, goes | none, and the first triples arrive before the run ends |
| C. Share a scan | RDFizer's grouping by source, Morph-KGC's partitions | merge the constructs that share a chain of frames into one CONSTRUCT with several template triples | unchanged | Q scans of the root class become one per distinct chain. MR-5 accepted the repetition, and this repays it |
| D. Hash a lexical lookup | RDFizer's PJTT | for a `mork:LexicalComparison` lookup, write each reference value's `STR()` to a key once, then join on the key | one key per reference value | from N × M comparisons to N + M, for example 2.5 million to 10,250 for 10,000 values and 250 codes |
| E. Partition the source | Morph-KGC, `rml-pipeline`'s chunks | run stratum 0 per partition of the root classes, the partitions independent | bounded by the largest partition | parallel across partitions, at the cost of a dependency analysis like `groupByDependencies` |
| F. An engine of our own | `rml-pipeline` | compile the IR of PDD-06 to a physical plan executed in process, with interned ids and cache-sized tuples | the lowest | the highest, and a second evaluator to keep equal to the SPARQL one |

## 6. A recommendation, to be tested

A and B first, since they change the runner only and every query keeps its meaning. C next, once the benchmark shows the repeated scans cost. D when a lexical lookup over a large scheme is real, which MR-Q2's default comparison makes rarer. E and F wait for PDD-06's IR, because a plan that merges and partitions queries is a rewrite of the algebra, and doing it on text would repeat the work.

## 7. Questions for the maintainer

| ID | Question |
|---|---|
| MP-Q1 | Is a benchmark of `mork_rdf` on a synthetic source of 10⁴, 10⁵ and 10⁶ records, measuring peak memory and time per stratum, the first step? |
| MP-Q2 | Should the output graph of a mapping that no later stratum reads be kept for traceability anyway, or is the CONSTRUCT's mapping, in `text()`, enough? |
| MP-Q3 | Does the planner belong to `tools/mork_rdf`, or to the unit that builds PDD-06's IR, so that the persistence compiler's queries share it? |
