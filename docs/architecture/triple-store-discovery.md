<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Triple-store discovery

**What this is.** The project's record of how each triple store we run actually behaves: its features, its limits, and how it
reads the standards it implements, SPARQL 1.1 Query and Update above all. Each entry says what we were doing, how we found out,
what the store does, why, what follows for LATTICE, and how to see it again.

**Status:** a living document, begun 2026-10-13 from formal-methods Track H's persistence work (slices H2.1 to H2.4b). It is a
source of truth for the project. Read it before relying on how a store behaves, and add to it when you find something. The
skill `lattice-triple-stores` has the procedure.

**Stores covered:** rdflib 7.6.0 and Oxigraph 0.5.11 (through `pyoxigraph`), and Oxigraph 0.5.12 for the findings the test suite probes, of which
TSD-01 and TSD-17 changed (R-H). Each finding names the versions it was seen on.
A finding holds for those versions only, until it is checked again. **Tools above a store covered:** pySHACL 0.40.1, which validates
shapes on rdflib (TSD-23, TSD-24, TSD-31). TSD-22 to TSD-33 are about the cost of running queries and shapes, and
[Efficient queries and shapes](efficient-queries-and-shapes.md) says which of them are properties of rdflib or pySHACL and which hold anywhere.

## Contents

1. [How to read and write this document](#1-how-to-read-and-write-this-document)
2. [Why we started looking](#2-why-we-started-looking)
3. [How we reach each store](#3-how-we-reach-each-store)
4. [A short primer on how SPARQL evaluates an update](#4-a-short-primer-on-how-sparql-evaluates-an-update)
5. [The findings at a glance](#5-the-findings-at-a-glance)
6. [The findings](#6-the-findings)
7. [Corrections, and what they taught us](#7-corrections-and-what-they-taught-us)
8. [Open questions](#8-open-questions)

## 1. How to read and write this document

Every finding has an identifier, `TSD-nn`, that other documents cite. It is never reused. A finding that turns out wrong is
corrected in place, with a dated note, and the story goes in §7.

Each finding states its evidence, as one or more of these.

| Evidence | Means | Example |
|---|---|---|
| **Source** | we read the store's code, at a named version and path | rdflib's `plugins/sparql/evaluate.py`, `evalJoin` |
| **Observed** | we ran a probe and saw the result, and the probe is a test or a script named here | `tools/persistence/tests/test_store_probes.py` |
| **Documented** | the store's own documentation says so | a page of the store's manual |
| **Reasoned** | it follows from the specification or from other findings, and is not yet observed | marked as a hypothesis until it is |

A finding is only as strong as its evidence. Source tells us the mechanism, Observed tells us it really happens on this
version, and the two together are what we aim for. A finding built only on Documented or Reasoned evidence says so in its
first line.

**A run record** goes with every Observed finding: the date, the store and its version, the Python version, and the kind of
machine, never the machine or person (ADR-A124 decision 5). Seven run records appear below.

| Run | Machine | Python | Stores |
|---|---|---|---|
| **R-A** | a Linux x86_64 container, 15 GB, used by an agent for H2.4b, 2026-10-12 | 3.14.8 | rdflib 7.6.0, pyoxigraph 0.5.11 |
| **R-B** | a macOS arm64 workstation, used for the H2 reviews and for this document, 2026-10-10 to 2026-10-13 | 3.14.7 | rdflib 7.6.0, pyoxigraph 0.5.11 |
| **R-C** | a Linux x86_64 container, 15 GB, used by an agent for H2.5, 2026-10-13 | 3.14.8 | rdflib 7.6.0, pyoxigraph 0.5.11 |
| **R-D** | a Linux x86_64 container, 4 logical cores, 15 GB, used by an agent for the ontology test-suite speed work, 2026-10-16 to 2026-10-17 | 3.14.8 | rdflib 7.6.0, pyoxigraph 0.5.11, pySHACL 0.40.1 |
| **R-E** | a macOS arm64 laptop with four performance and four efficiency cores and 8 GB, used by the maintainer to repeat R-D's runs, 2026-10-16 to 2026-10-17 | 3.14.7 | rdflib 7.6.0, pyoxigraph 0.5.11, pySHACL 0.40.1 |
| **R-F** | a macOS arm64 laptop, used by an agent for H2.6f's `members` read, 2026-10-20 | 3.14.7 | rdflib 7.6.0, pyoxigraph 0.5.11 |
| **R-G** | a macOS arm64 laptop, used by an agent for TSD-34's upstream report, 2026-10-20 | 3.14.7 | rdflib 7.6.0, rdflib `main` at `62bf240` (7.7.0a0), rdflib `next` at `0fdac39` (8.0.0a0) |
| **R-H** | a Linux x86_64 container, 4 logical cores, used by an agent for H2.8c, 2026-10-20, where a fresh bootstrap installed pyoxigraph 0.5.12 | 3.14.8 | rdflib 7.6.0, pyoxigraph 0.5.11 and 0.5.12 |

**How to add a finding** is in §6.0 and in the skill. In short: say what you were testing, how you found it, the smallest
SPARQL that shows it, the result on each store you have, the reason if you can find it in the source, what it means for
LATTICE, and how to reproduce it. If reproducing it takes more than one query, write a short plan for a script.

## 2. Why we started looking

LATTICE's persistence layer (`ontology/persistence`, ADR-A78) describes how an application stores its data in an RDF store:
which graph an aggregate lives in, how two writers are kept from overwriting each other, what receipt each write leaves. The
persistence compiler (`tools/persistence`, ADR-A79) turns that description into SPARQL 1.1 Update operations, guarded writes
of the kind the [RDF and SPARQL patterns guide](rdf-sparql-patterns-guide.md) sets out. For example, a compare-and-set replace
deletes an aggregate's old state and writes its new state only if the version row still says the sequence the caller read.

Until formal-methods Track H, nothing executed those operations. Track H's plan was to prove things about them, and proving
things about a query means knowing what the query does. Three questions turned that into store discovery.

1. **Does the generated SPARQL do what the configuration intends?** Slices H2.1 to H2.4 rebuilt the compiler's output as a
   typed intermediate representation ([ADR-A123](decisions/ADR-A123-typed-operation-ir.md)), and every rule of its checker is a
   claim about SPARQL. Two of those claims were wrong when first written (§7), and only running the queries showed it.
2. **What does a write cost?** A composite aggregate's replace was suspected, then shown, to cost time or memory quadratic in
   the aggregate's size (TD-42). The cost depends on how the store applies an update, which is not fixed by the standard.
3. **What may the compiler assume about a store?** The persistence layer's later work (H5 of the formal methods Track H) models each store's concurrency and gives the compiler a *capability
   record* to choose the right form of an operation for a store. The probes in this document are that record's first
   entries.

```mermaid
flowchart LR
  P["persistence profile<br/>(configuration)"] --> C["compile"]
  C --> CP["compiled profile"]
  CP --> I["instantiate<br/>builders, typed IR"]
  I --> Q["SPARQL Update text"]
  Q --> R["rdflib 7.6.0"]
  Q --> O["Oxigraph 0.5.11"]
  R --> D["what each store did"]
  O --> D
  D --> T["this document"]
  T --> CR["H5 capability record<br/>and the compiler's choices"]
```

## 3. How we reach each store

The two stores are reached in different ways, and the difference matters to several findings.

```mermaid
flowchart TB
  subgraph tests["tools/persistence/tests"]
    E["engines.py<br/>the engine fixture<br/>each_engine marker"]
  end
  E -->|"rdflib"| RD["rdflib Dataset<br/>in process"]
  E -->|"oxigraph"| OX["OxDataset facade<br/>rdflib-shaped API"]
  OX --> AD["lattice_testing_oxigraph<br/>OxigraphStore<br/>tools/testing/oxigraph"]
  AD --> PY["pyoxigraph.Store<br/>in memory"]
  RD -.->|"parameters as<br/>initBindings"| RD
  AD -.->|"parameters substituted<br/>into the text"| PY
```

- **rdflib** runs in the test process. An update is `Dataset.update(text, initBindings={...})`, so a request-time parameter
  such as `$root` is an *initial binding*, a value the engine starts from, and never text.
- **Oxigraph** runs through `tools/testing/oxigraph` ([ADR-A125](decisions/ADR-A125-test-support-tooling.md)), whose
  `OxigraphStore` wraps `pyoxigraph.Store`. Its `bind_parameters` writes each parameter into the query text as an encoded
  term, as a caller with no initial-binding API would. The tests reach it through `OxDataset` in
  `tools/persistence/tests/engines.py`, which offers the part of rdflib's `Dataset` API the tests use.
- **A test opts in to both engines** with `@engines.each_engine`. The Oxigraph cases carry the `oxigraph` marker and skip where
  the package is absent. `mise run check:persistence-oxigraph` installs it and runs only them.
- **The benchmark** `benchmark/persistence-composite-cost` ([ADR-A124](decisions/ADR-A124-benchmark-root.md)) runs each size in a
  child process under a memory cap, on both engines.

So "the store" in a finding means the store as reached this way. A finding that depends on initial bindings, for example,
says which mechanism it used.

## 4. A short primer on how SPARQL evaluates an update

Most findings below are about where a store departs from, or interprets, a part of SPARQL 1.1 that few people need to think
about. This section sets out those parts once.

### 4.1 `DELETE … INSERT … WHERE`, by the specification

SPARQL 1.1 Update (§3.1.3) defines `DELETE { D } INSERT { I } WHERE { P }` in three steps. Evaluate `P` once, against the
dataset as it was before the operation, giving a sequence of solutions. Fill `D` and `I` with each solution, skipping any triple
with an unbound variable. Remove every filled deletion, then add every filled insertion. The result does not depend on the order
of the solutions.

```mermaid
flowchart LR
  D0["dataset before"] --> W["WHERE, evaluated once"]
  W --> S["solutions"]
  S --> FD["fill DELETE<br/>for each solution"]
  S --> FI["fill INSERT<br/>for each solution"]
  FD --> UD["all deletions"]
  FI --> UI["all insertions"]
  UD --> A["remove all deletions,<br/>then add all insertions"]
  UI --> A
  A --> D1["dataset after"]
```

We call a store that does exactly this **snapshot**, and the capability record will carry it as `snapshotUpdateSemantics`.
A store may instead take the solutions one at a time and, for each, remove its deletions and add its insertions. Then a triple
one solution inserts can be removed by a later solution, and the order of solutions decides the result. TSD-01 is about exactly
this.

### 4.2 Groups are evaluated bottom-up

A `WHERE` clause is a group, and it may hold inner groups: `{ … }`, `OPTIONAL { … }`, a `UNION` branch, a `GRAPH g { … }`. The
specification translates the query into an algebra (§18.2) in which each inner group is evaluated on its own and then joined
with what came before it. So an inner group cannot *see* a variable bound outside it, although its result is *joined* with it.
`FILTER NOT EXISTS { … }` is the exception. It is evaluated once per outer solution, with that solution's values substituted.

```mermaid
flowchart TB
  O["outer group<br/>BIND(1 AS ?a)"] --> J["join, on shared variables"]
  N["inner group, evaluated alone<br/>BIND(?a + 1 AS ?b)<br/>?a is unknown here"] --> J
  J --> R["?a = 1, ?b unbound"]
  O2["outer solution ?a = 1"] --> NE["NOT EXISTS, per outer solution<br/>FILTER(?a = 1) sees ?a"]
```

This decides two things that matter here: what a `BIND` inside an inner group computes (TSD-03), and how much a `GRAPH ?g`
inside an inner group reads (TSD-04).

### 4.3 A `FILTER` applies to its whole group

A `FILTER` is not a step in a sequence. It applies to every solution of the group it is written in, after all the group's
patterns have matched, wherever in the group it is written. A filter that tests whether a variable is bound, written at the top
of a group whose patterns also bind that variable, therefore sees it bound by the data. TSD-13 shows what this did to a guard.

### 4.4 Request-time parameters: initial bindings or text

A generated operation leaves its request-time values as variables, written `$root`, `$epoch` and so on. A caller fills them in
one of two ways.

| Way | How | Example |
|---|---|---|
| initial bindings | the engine starts evaluation with the variable bound | rdflib's `initBindings`, a prepared query's parameters |
| text substitution | the caller writes the value into the query text before sending it | the SPARQL 1.1 Protocol, which has no binding parameters, and our Oxigraph adapter |

The two are not interchangeable. Some functions accept only a variable (`BOUND`), so substituted text can stop a query parsing
(TSD-11).

## 5. The findings at a glance

`✔` means the store does what SPARQL 1.1 says, `✘` that it departs from it, and a word where the specification leaves the choice
to the store or where it is a matter of capacity.

| # | Finding | Specification | rdflib 7.6.0 | Oxigraph 0.5.11 (and 0.5.12 where it differs) | Evidence |
|---|---|---|---|---|---|
| [TSD-01](#tsd-01-the-order-in-which-a-delete-insert-where-is-applied) | applying a `DELETE`/`INSERT` | all deletions, then all insertions | ✘ one solution at a time, in hash order | ✘ one solution at a time, in solution order. ✔ from 0.5.12 | Source, Observed, Documented |
| [TSD-02](#tsd-02-what-filling-a-template-once-per-solution-costs) | filling a template once per solution | not specified | quadratic in time | quadratic in time and memory | Source, Observed |
| [TSD-03](#tsd-03-what-a-bind-inside-an-inner-group-can-see) | a `BIND` in an inner group | sees only its group | ✔ | ✔ | Observed |
| [TSD-04](#tsd-04-a-graph-variable-bound-outside-an-inner-group) | `GRAPH ?g` inside an inner group, `?g` bound outside | joined afterwards | passes the binding in, reads one graph | passes the binding in, reads one graph | Observed |
| [TSD-05](#tsd-05-a-template-quad-whose-graph-variable-is-unbound) | template quad, graph variable unbound | skipped | ✘ written to a new blank-node graph | ✔ skipped | Source (rdflib), Observed |
| [TSD-06](#tsd-06-a-request-whose-second-operation-fails-and-graph-management) | a request whose second operation fails | should be atomic | keeps the first operation | rolls the first back | Observed |
| [TSD-07](#tsd-07-numeric-datatypes-are-not-kept-by-oxigraph) | `"1"^^xsd:long` stored and read | the term is kept | ✔ kept | ✘ becomes `xsd:integer` | Observed |
| [TSD-08](#tsd-08-a-zero-length-path-from-a-term-that-is-in-no-triple) | zero-length path from a term in no triple | our reading: matches the term | matches it | matches nothing | Observed |
| [TSD-09](#tsd-09-unicode-escapes-and-an-escaped-backslash) | `\u` escapes and an escaped backslash | processed before parsing (§19.2) | whole-text pre-pass | inside string tokens | Source (rdflib), Observed |
| [TSD-10](#tsd-10-a-result-row-whose-projected-variables-are-all-unbound) | a result row with every projected variable unbound | kept | ✘ dropped | ✔ kept | Observed |
| [TSD-11](#tsd-11-bound-and-text-substitution) | `BOUND(<iri>)` after text substitution | a syntax error | syntax error | syntax error | Observed |
| [TSD-12](#tsd-12-initial-bindings-are-visible-inside-inner-groups-on-rdflib) | initial bindings inside an inner group | not specified | visible | not tested, the adapter substitutes text | Observed |
| [TSD-13](#tsd-13-a-filter-at-the-top-of-a-group-sees-what-the-groups-patterns-bound) | a top-level `FILTER(BOUND(?x))` with `?x` in the group's patterns | sees `?x` bound by the data | ✔ | ✔ | Observed |
| [TSD-14](#tsd-14-graph-management-operations-on-rdflib) | `CREATE GRAPH`, `DROP GRAPH` of an absent graph | defined | `CREATE` not implemented, `DROP` succeeds | `DROP` fails | Observed |
| [TSD-15](#tsd-15-a-sub-select-and-the-variables-around-it) | a sub-select and the variables around it | evaluated on its own, only its projections leave it | ✘ an outer binding leaks in | ✔ | Observed |
| [TSD-16](#tsd-16-min-and-max-over-iris) | `MIN` and `MAX` over IRIs | the lowest or highest IRI | ✘ a plain literal of the IRI text | ✔ an IRI | Observed |
| [TSD-17](#tsd-17-a-chain-of-additions-and-subtractions) | `a - b + c` and `a / b / c` | grouped from the left | ✔ | ✘ grouped from the right. ✔ from 0.5.12 | Observed, Documented |
| [TSD-18](#tsd-18-count-distinct-over-xsdlong-and-xsdinteger-terms) | `COUNT(DISTINCT)` over `xsd:long` and `xsd:integer` | two terms, so two | counts them apart | counts them together, since it stores both as `xsd:integer` | Observed |
| [TSD-19](#tsd-19-the-order-of-group_concat) | the order of `GROUP_CONCAT` | not specified | the order the data was stored in, whatever the hash seed (this query shape) | the order of the solutions | Observed |
| [TSD-20](#tsd-20-a-filter-inside-not-exists-and-a-parameter) | a `FILTER` inside `NOT EXISTS` and a parameter or a sub-select's projection | sees them by substitution | ✔ by initial binding and by text | ✔ by text | Observed |
| [TSD-21](#tsd-21-an-empty-values-block-in-an-update) | an empty `VALUES` block in an update `WHERE` | no solution | ✘ raises `AttributeError`, before changing anything | ✔ no solution, nothing written | Observed |
| [TSD-22](#tsd-22-rdflib-parses-and-translates-a-querys-text-on-every-call) | parsing a query's text | not specified | ✘ costs 20 ms for a 20-line query, 0.5 ms when prepared | 0.17 ms, parse and run | Source, Observed |
| [TSD-23](#tsd-23-pyshacl-runs-a-sparql-constraint-once-per-focus-node) | how often a SPARQL-based constraint is run | defined per focus node | pySHACL: once per focus node | pySHACL runs on rdflib only | Source, Observed |
| [TSD-24](#tsd-24-the-prefix-block-pyshacl-writes-changes-order-between-validations) | the order of the `PREFIX` lines pySHACL writes | not specified | varies between validations | not applicable | Source, Observed |
| [TSD-25](#tsd-25-rdflib-fixes-the-order-of-a-groups-patterns-before-it-knows-the-initial-bindings) | the order of a group's patterns | not specified | ✘ fixed at translation, ignores initial bindings | ✔ no sensitivity seen | Source, Observed |
| [TSD-26](#tsd-26-a-chain-of-three-or-more-groups-is-joined-by-evaluating-the-later-ones-whole) | joining a chain of groups | not specified | evaluates the later groups whole | not tested | Source, Observed |
| [TSD-27](#tsd-27-a-filter-is-applied-after-its-groups-patterns-and-rdflib-does-not-move-it-earlier) | when a `FILTER` runs | after the group's patterns (scope) | ✘ after all of them | 1.3 to 1.5 times between forms | Source, Observed |
| [TSD-28](#tsd-28-presence-and-absence-tests-the-forms-differ-little) | forms of a presence or absence test | equal | 1.0 to 1.4 times | 1.1 to 1.2 times | Observed |
| [TSD-29](#tsd-29-two-parses-of-one-document-never-give-equal-triple-sets) | two parses of one document | blank nodes are fresh | fresh labels | fresh labels | Observed |
| [TSD-30](#tsd-30-a-querys-undeclared-prefixes-resolve-from-the-data-graphs-bindings) | a prefix the query does not declare | an error | resolved from the graph's bindings | not tested | Source, Observed |
| [TSD-31](#tsd-31-pyshacl-copies-the-data-graph-on-every-validation-unless-told-not-to) | copying the data graph for a validation | not specified | pySHACL copies it, 0.09 s for 5,000 to 14,000 triples | not applicable | Source, Observed |
| [TSD-32](#tsd-32-a-constant-filter-whose-value-is-false-is-dropped-by-rdflib) | `FILTER (false)` | removes every solution | ✘ removes none | ✔ | Source, Observed |
| [TSD-33](#tsd-33-on-oxigraph-count-over-a-statically-false-filter-returns-no-row) | `COUNT(*)` over a filter that is statically false | one row, 0 | ✔ except TSD-32 | ✘ no row | Observed |
| [TSD-34](#tsd-34-rdflib-evaluates-a-filter-not-exists-in-a-graph-block-against-the-wrong-graph-for-some-solutions) | `FILTER NOT EXISTS` without its own `GRAPH`, inside a `GRAPH` block that holds a sub-select and a `UNION` | tests the block's graph | ✘ sometimes tests the default graph, by hash seed | ✔ | Source, Observed |

## 6. The findings

### 6.0 The shape of an entry

Each entry has the same parts, so a reader can find what they need.

- **Context.** What we were building or testing when it came up, and why it mattered then.
- **How we found it.** The steps, in order, and the evidence each gave.
- **What the store does.** The smallest SPARQL that shows it, and the result on each store.
- **Why.** The mechanism, from the source where we read it.
- **What it means for LATTICE.** The decisions, debt and tests it touches.
- **Reproduce it.** A query to run, or a short plan for a script when the setup has layers.

---

### TSD-01. The order in which a `DELETE`/`INSERT`/`WHERE` is applied

**Evidence:** Source and Observed, on both stores. Runs R-A and R-B. **Corrected 2026-10-13**, see §7.1. **Oxigraph 0.5.12 (2026-10-20, R-H):**
Documented, Source and Observed. It applies the specification's order (step 7).

**Context.** A composite aggregate's replace, `cas-replace-composite-property`, deletes every triple of the aggregate and inserts
the new state. A cheaper form of it (R2 of the Track H typed IR design)
would put the payload in `VALUES` rows beside the sweep's rows, so each payload triple is filled once. That form is right only
if the store removes every deletion before it adds any insertion, because a payload often repeats a triple the aggregate
already holds, an unchanged name for example. So we needed to know how each store applies an update.

**How we found it.**

1. *Source, rdflib.* We read `rdflib/plugins/sparql/update.py`, `evalModify`, in 7.6.0. After evaluating the `WHERE` it loops
   `for c in list(res):` and, inside the loop, does `dg -= _fillTemplate(u.delete.triples, c)` and then
   `dg += _fillTemplate(u.insert.triples, c)` (and the same for each graph's quads). So it removes and adds per solution.
2. *A first probe, H2.4b.* The probe P1 stores one triple, then runs an update whose two solutions, written as `VALUES` rows,
   respectively insert and delete that triple. Under the specification the triple survives in either row order. In run R-A
   rdflib kept it in both orders, and the slice concluded that rdflib is snapshot. That conclusion was wrong.
3. *The contradiction.* In run R-B the same probe lost the triple on rdflib. A trace of the order of solutions, and then the
   same probe run with `PYTHONHASHSEED` fixed to each of 0 to 11, showed the result changing with the seed: lost in both
   orders for 6 seeds, kept in both for 4, and dependent on the row order for 2. The probe's test, which asserted "kept", failed
   in 2 of 3 runs of `check:persistence` with no seed set.
4. *Source again.* rdflib translates the probe's `WHERE { VALUES … }` to `Join(BGP{}, ToMultiSet(Values))`, and the join is
   not marked lazy. `evaluate.py`, `evalJoin`, then does `b = set(evalPart(ctx, join.p2))`. A Python `set` of solutions iterates
   in an order that follows the hash of each solution, and string hashes change with `PYTHONHASHSEED` per process. So the order
   of solutions, and with it the result of the update, can change from one process to the next.
5. *Source, Oxigraph.* In Oxigraph 0.5.11, `lib/oxigraph/src/sparql/update.rs`, `eval_delete_insert` does
   `prepared.execute(...).collect::<Result<Vec<_>, _>>()?` to gather every computed `DeleteInsertQuad`, then
   `for mutation in mutations` applies each `Delete` or `Insert` in turn. The reads happen before any write. The order inside the
   `Vec` is the order of solutions, deletions then insertions for each, which the probe confirms.
6. *Observed, Oxigraph.* P1 on Oxigraph loses the triple when the inserting row comes first and keeps it when the deleting row
   comes first, every time.
7. *Oxigraph 0.5.12, 2026-10-20.* A fresh bootstrap installed pyoxigraph 0.5.12, which `tools/testing/oxigraph` allows
   (`>=0.5.11,<0.6`), and the P1 tests failed on Oxigraph. P1 kept the triple in both row orders. The release notes of 0.5.12 say
   "SPARQL Update: apply all deletions before insertions", and in `lib/oxigraph/src/sparql/update.rs` at the tag `0.5.12`,
   `eval_delete_insert` still collects every mutation into a `Vec`, then loops over it twice, removing each `Delete` in the first loop
   and adding each `Insert` in the second. With 0.5.11 reinstalled, P1 behaved as in step 6 again.

**What the store does.**

```sparql
# stored beforehand: GRAPH <urn:g> { <urn:s> <urn:p> <urn:o> }
DELETE { GRAPH <urn:g> { ?d <urn:p> <urn:o> } }
INSERT { GRAPH <urn:g> { ?i <urn:p> <urn:o> } }
WHERE  { VALUES (?i ?d) { (<urn:s> UNDEF) (UNDEF <urn:s>) } }
```

| Store | Row order as written | Is `<urn:s> <urn:p> <urn:o>` still there? |
|---|---|---|
| specification | either | yes |
| rdflib 7.6.0 | either | depends on the process's hash seed |
| Oxigraph 0.5.11 | inserting row first | no |
| Oxigraph 0.5.11 | deleting row first | yes |
| Oxigraph 0.5.12 | either | yes |

```mermaid
sequenceDiagram
  participant W as WHERE
  participant R as rdflib evalModify
  participant G as graph
  W->>R: solutions, from a set, in hash order
  loop each solution in turn
    R->>G: remove this solution's deletions
    R->>G: add this solution's insertions
  end
  Note over R,G: insert row then delete row, the triple is lost
  Note over R,G: delete row then insert row, the triple survives
```

```mermaid
sequenceDiagram
  participant W as WHERE
  participant X as Oxigraph eval_delete_insert
  participant G as store
  W->>X: solutions, in evaluation order
  X->>X: collect every Delete and Insert into one Vec
  loop each mutation in the Vec
    X->>G: apply it
  end
  Note over X,G: the Vec keeps solution order, so the last word on a triple wins
```

**Why.** rdflib 7.6.0 and Oxigraph 0.5.11 do not keep the specification's two phases. rdflib interleaves per solution, and its
solution order for a non-lazy join comes from a Python `set`. Oxigraph separates reading from writing, which protects the `WHERE` from
the update's own changes, and 0.5.11 then applied the collected mutations in solution order rather than all deletions first. 0.5.12
applies all the deletions and then all the insertions, which is the specification's order.

**What it means for LATTICE.**

- **R0, the replace as shipped, stays right on both.** It puts the whole payload in the `INSERT` template, so every solution adds
  every payload triple again, and the last solution restores anything an earlier one removed. Its redundancy is what makes it
  correct here, and that redundancy is what TSD-02 measures.
- **R2, the linear form, is unsafe on rdflib 7.6.0 and Oxigraph 0.5.11.** The sketch's §4.3 expected it to be safe where
  `snapshotUpdateSemantics` holds, and neither has it. H5's capability record carries `snapshotUpdateSemantics = false` for both, and
  `true` for Oxigraph 0.5.12. Since rdflib still lacks it, and an adopter may run an older Oxigraph, R2 stays unused.
- **Any generated update must be right whatever the solution order.** On rdflib a wrong assumption would not fail reliably, it
  would fail in some processes. A test of order-dependent behaviour on rdflib must fix the hash seed or sweep it.
- **The P1 test was corrected** on 2026-10-13 (`test_store_probes.py`, H2.4b-T1 and T2). On rdflib it runs the probe in child
  processes under seeds 0 to 11 and requires both outcomes to occur. On Oxigraph it keeps the row-order expectations up to 0.5.11
  and expects the triple kept in both orders from 0.5.12, reading `SNAPSHOT_UPDATES` from `lattice_testing_oxigraph` (changed
  2026-10-20). A machine that cannot install 0.5.12 still passes. `test_ox_t6` in `tools/testing/oxigraph` holds the flag to the
  installed version's behaviour, so a later release that changes it again fails there.

**Reproduce it.**

A script, in four steps.

1. Write a file `p1.py` that creates an rdflib `Dataset`, adds `<urn:s> <urn:p> <urn:o>` to graph `<urn:g>`, runs the update
   above with the `VALUES` rows taken from `sys.argv[1]`, and prints whether the triple is still there.
2. Run it twelve times per row order, each with a different `PYTHONHASHSEED`:

   ```bash
   for seed in 0 1 2 3 4 5 6 7 8 9 10 11; do PYTHONHASHSEED=$seed mise exec -- python p1.py '(<urn:s> UNDEF) (UNDEF <urn:s>)'; done
   ```

3. Expect a mix of `True` and `False`. A store that applied the specification's order would print `True` every time.
4. For Oxigraph, run the same update through `pyoxigraph.Store().update(...)` in both row orders. On 0.5.11 expect `False` with the
   inserting row first and `True` with the deleting row first, whatever the seed. On 0.5.12 expect `True` in both orders.

To see the order itself, wrap `rdflib.plugins.sparql.update._fillTemplate` with a function that records, for each call, whether
`c.get(Variable("i"))` is bound, and then calls the original. Keep the wrapper this small. A wrapper that iterated the whole
solution gave a misleading result in one run, which we did not explain, see §7.1.

---

### TSD-02. What filling a template once per solution costs

**Evidence:** Source and Observed, on both stores. Run R-A for the benchmark, R-B for the first measurement.

**Context.** The composite replace R0 sweeps the root and every member of an aggregate in one `OPTIONAL` pattern, which gives
one solution per stored triple, M of them. Its `INSERT` template holds the N payload triples, and none of them uses a sweep
variable. So, by the definition in §4.1, the payload is filled M times before the union removes the copies. Whether a store
does that literally was the question behind TD-42.

```sparql
DELETE { GRAPH <data> { ?s ?p ?o } … }
INSERT { GRAPH <data> { …N payload triples… } … }
WHERE  {
  … the version-row guard, one solution …
  OPTIONAL { GRAPH <data> { $root <ownedPath> ?s . ?s ?p ?o } }   # M solutions
}
```

```mermaid
flowchart TB
  G["guards<br/>1 solution"] --> J["join"]
  SW["sweep<br/>M stored triples"] --> J
  J --> SOL["M solutions"]
  SOL --> DEL["DELETE fills: M"]
  SOL --> INS["INSERT fills: M x N<br/>the whole payload each time"]
```

**How we found it.**

1. *Source, rdflib.* `evalModify`'s per-solution loop (TSD-01) calls `_fillTemplate` on the whole `INSERT` template for every
   solution, and `Graph.__iadd__` adds each filled triple.
2. *Observed, rdflib, R-B.* A scratch script reduced the replace to its essentials and timed it at M = N: 0.007 s at 10,
   0.077 s at 100, 5.6 s at 1000. Ten times the size took about seventy times as long.
3. *Source, Oxigraph.* `eval_delete_insert` collects every filled quad into a `Vec` before applying any (TSD-01), so the M × N
   filled quads exist in memory at once.
4. *Observed, both, R-A.* The benchmark `benchmark/persistence-composite-cost` ran M = N from 10 to 10,000, each size in a child
   process capped at 8 GB.

**What the store does.**

| M = N | rdflib 7.6.0 | Oxigraph 0.5.11 |
|---|---|---|
| 10 | 0.03 s | 0.0005 s |
| 100 | 0.17 s | 0.0056 s |
| 1,000 | 9.2 s | 0.59 s |
| 3,000 | 83 s | 14.4 s |
| 10,000 | 983 s | did not finish |
| fitted growth k, 100 and up | 1.87 | 2.26 |

At 10,000 Oxigraph tried to allocate about 7 GB and failed under the cap, and an uncapped run was killed at 14 GB on a 15 GB
machine. Separately, a run at 2,000 used 1.5 GB and one at 4,000 used 5.8 GB, so memory grows as the square of the size, and
10,000 would need about 36 GB. Every finished run left exactly the payload, the bystander aggregate untouched and the version
row at the next sequence.

**Why.** Both stores fill the template once per solution, as the specification's definition reads. rdflib pays in time,
adding the same triples again and again. Oxigraph is fast per quad but holds every filled quad at once.

**What it means for LATTICE.**

- R0 is correct and quadratic on both, in time on rdflib and in time and memory on Oxigraph (TD-42).
- R2 is unsafe on both (TSD-01). R1, two operations in one request, is safe only where a failing request rolls back (TSD-06),
  which Oxigraph does and rdflib does not. So no single linear form fits both, which is what the capability record exists to
  decide. H5 chooses.
- The benchmark fails on a wrong result and never on time or memory (ADR-A124). A run that does not finish is recorded with its
  exit status.

**Reproduce it.** `mise run check:persistence-composite-cost`, about 25 minutes, most of it rdflib at 10,000.
`COMPOSITE_COST_MAX=1000` gives a quick run. The report is written to `benchmark/persistence-composite-cost/report.md`.

---

### TSD-03. What a `BIND` inside an inner group can see

**Evidence:** Observed on both stores, R-B. rdflib is also covered by tests.

**Context.** The typed IR's checker tracks, for each point of a `WHERE`, which variables are bound in every solution, so it can
refuse a template variable tagged `Bound` that might not be (ADR-A123). Its first version let an inner group see the enclosing
group's variables. A review then "fixed" the `GRAPH` block the same way. Both were wrong, and only running queries showed it
(§7.2).

**How we found it.** We ran the same six queries on each store, each binding `?a` outside and computing `?b` from it inside.

**What the store does.**

| Query | rdflib | Oxigraph | Specification |
|---|---|---|---|
| `BIND(1 AS ?a) { BIND(?a + 1 AS ?b) }` | `?b` unbound | `?b` unbound | unbound |
| `BIND(1 AS ?a) GRAPH <g> { ?s ?p ?o BIND(?a + 1 AS ?b) }` | unbound | unbound | unbound |
| `BIND(1 AS ?a) OPTIONAL { BIND(?a + 1 AS ?b) }` | unbound | unbound | unbound |
| `BIND(1 AS ?a) { BIND(?a + 1 AS ?b) } UNION { BIND(5 AS ?b) }` | unbound and 5 | not run | unbound and 5 |
| `BIND(1 AS ?a) BIND(?a + 1 AS ?b)` | 2 | 2 | 2 |
| `BIND(1 AS ?a) FILTER NOT EXISTS { FILTER(?a = 1) }` | no row, so `?a` is seen | no row | no row |

**Why.** The algebra of §4.2. Both stores follow it.

**What it means for LATTICE.** The checker's scope starts empty in a nested group, an `OPTIONAL`, a `UNION` branch and a `GRAPH`
block, and starts from the enclosing scope only in `NOT EXISTS` (FMH-H2-1, F4, and H2.3). Tests H2.1-T29 and T29b check the rule
against rdflib.

**Reproduce it.** Each row is one `SELECT ?a ?b WHERE { … }` over any dataset with one triple in `<g>`. Select `?a` as well as
`?b`, or rdflib drops the row (TSD-10).

---

### TSD-04. A graph variable bound outside an inner group

**Evidence:** Observed on both stores, R-A and R-B.

**Context.** The named-graph replace sweeps the root's graph with `OPTIONAL { GRAPH ?g { ?s ?p ?o } }`, where `?g` is bound by a
`BIND` at the top of the `WHERE`. By §4.2 the inner group is evaluated on its own, so `GRAPH ?g` there ranges over every graph
until the join narrows it. The result is right either way. The question was the cost, and whether the typed IR should refuse
the form (H2.3-Q2).

**How we found it.**

1. *Reasoned.* rdflib's translation of the template and of the form the checker already accepted, `BIND(… AS ?g) GRAPH ?g { … }`,
   differ only in `LeftJoin` against `Join`. Both are `Extend[?g]` beside an independent `Graph[?g]`, so neither is cheaper by the
   specification.

   ```mermaid
   flowchart TB
     subgraph accepted["same group"]
       J1["Join"] --> E1["Extend ?g"]
       J1 --> G1["Graph ?g"]
     end
     subgraph template["inside OPTIONAL"]
       J2["LeftJoin"] --> E2["Extend ?g"]
       J2 --> G2["Graph ?g"]
     end
   ```

2. *Observed, rdflib, R-B.* On 50 graphs of 200 triples, both forms returned the 200 triples of the bound graph in about 10 ms,
   against 237 ms for `GRAPH ?g { ?s ?p ?o }` with nothing bound.
3. *Observed, both, R-A.* Probe P3 timed the `OPTIONAL` form over 100 graphs of 3,000 triples against 1 graph. The ratio was 1.1
   on both stores.

**What the store does.** Both pass the outer binding of `?g` into the graph pattern, so they read one graph. A store that
followed the algebra literally would read every graph and then discard most of what it read.

**Why.** Not read for either store. The timings show both pass the left side's bindings into the right side, as an engine does
when it evaluates a join lazily (rdflib has `evalLazyJoin` for that, and TSD-Q1 asks when it is used).

**What it means for LATTICE.** The scope rule accepts a `GRAPH ?g` inside an inner group when an enclosing group binds `?g` in
every solution before it (ADR-A123, second addendum). A caller-named graph, `GRAPH $g`, is available as an override for a store
that does scan (H2.3-Q2 (c)). H2.4b's T4 fails if either store starts to scan.

**Reproduce it.** Load 100 graphs of 3,000 triples, then time
`SELECT (COUNT(*) AS ?n) WHERE { BIND(<urn:g:0> AS ?g) OPTIONAL { GRAPH ?g { ?s ?p ?o } } }` against the same with one graph
loaded. Take the best of three. A ratio near 1 means the binding is passed in.

---

### TSD-05. A template quad whose graph variable is unbound

**Evidence:** Source (rdflib) and Observed, both stores, R-A and R-B.

**Context.** H2.3 tested what an unguarded `unconditional-write` does when the caller leaves out `$root`. The graph name `?g` is
computed from `$root`, so it is unbound.

**How we found it.** Test H2.3-T8 expected nothing to be written and found a new graph. A direct probe confirmed it, and probe
P4 now checks both stores.

**What the store does.**

```sparql
INSERT { GRAPH ?g { <urn:s> <urn:p> <urn:o> } } WHERE { }
```

| Store | Result |
|---|---|
| specification | skipped, since the quad has an unbound variable |
| rdflib 7.6.0 | the triple is written into a new graph named by a blank node |
| Oxigraph 0.5.11 | skipped, nothing written |

**Why.** rdflib's `evalModify` does `cg = ctx.dataset.get_context(c.get(g))` for each graph of the template (Source). With `?g`
unbound, `c.get(g)` is `None`, and the observed result is a graph with a fresh blank-node name, so `get_context(None)` must create
one. We did not read `get_context` itself.

**What it means for LATTICE.** With the parameter guards on, a missing `$root` is refused before this point. With
`--no-parameter-guards`, on rdflib, a missing `$root` leaves an orphan graph that no audit names (TD-44). The README's guards
paragraph says so.

**Reproduce it.** Run the update above on an empty `Dataset` and list `ds.graphs()` with at least one triple.

---

### TSD-06. A request whose second operation fails, and graph management

**Evidence:** Observed on both stores, R-A and R-B.

**Context.** R1, the two-operation form of the composite replace, is safe only if a request whose second operation fails leaves
no trace of its first. SPARQL 1.1 Update says a request *should* be atomic. Probe P2 asks each store.

**How we found it.** P2 sends `INSERT DATA { … } ; <a failing operation>` and reads back. Finding a failing operation took two
tries on rdflib (TSD-14).

**What the store does.**

| Store | Failing second operation | The request | The first insert |
|---|---|---|---|
| rdflib 7.6.0 | `LOAD <urn:no-such>` | fails | kept |
| Oxigraph 0.5.11 | `DROP GRAPH <urn:absent>` | fails with `RuntimeError` | rolled back |

```mermaid
sequenceDiagram
  participant C as caller
  participant S as store
  C->>S: INSERT DATA t, then a failing operation, in one request
  alt rdflib
    S-->>C: error
    Note over S: t is stored
  else Oxigraph
    S-->>C: error
    Note over S: t is not stored
  end
```

**Why.** We did not read either store's transaction code. Oxigraph applies an update inside a transaction (TSD-01's source shows
`self.transaction`), which is consistent with the rollback.

**What it means for LATTICE.** R1 is a candidate on Oxigraph and not on rdflib. This is only the failure half of
`atomicUpdateRequest`. Its isolation half, what a concurrent writer sees between the two operations, needs concurrent writers
and is H5's.

**Other stores, from their documentation (Documented, not probed, gathered 2026-10-14).** SPARQL 1.1 Update says a request
*should* be treated atomically, a recommendation the working group chose not to make a requirement
([working draft of October 2010](https://www.w3.org/TR/2010/WD-sparql11-update-20101014/),
[a comment on the list](https://lists.w3.org/Archives/Public/public-rdf-dawg-comments/2011May/0012.html)). So it is each store's choice.

| Store | What its documentation says | Reading |
|---|---|---|
| Apache Jena, TDB2 (which `platform/semantic-dataset-fuseki` targets) | TDB2 is transactional only, with serializable transactions that cover SPARQL Update ([TDB transactions](https://jena.apache.org/documentation/tdb/tdb_transactions.html), [Jena transactions](https://jena.apache.org/documentation/txn)) | atomic per request, by inference. The documentation does not name the request as the transaction's scope |
| Amazon Neptune | a community answer says the operations of one request run as one transaction and roll back together ([Repost](https://www.repost.aws/questions/QUE09h4w48RFOW6I8RrId6SQ/are-multiple-sparl-update-queries-in-same-post-message-one-transaction)). The official page states strict isolation without that detail ([transaction semantics](https://docs.aws.amazon.com/neptune/latest/userguide/transactions.html)) | atomic per request, unconfirmed |
| Virtuoso | SPARQL updates "are generally not meant to be transactional", and the recommended mode, `log_enable(2)`, commits every operation as it is done. One mode autocommits per triple inserted or deleted ([tip](https://docs.openlinksw.com/virtuoso/virtuosotipsandtrickssparulupdatestrl), [`log_enable`](https://docs.openlinksw.com/virtuoso/fn_log_enable)) | **not atomic per request** in its recommended mode, and possibly not atomic within one operation (TSD-Q13) |

So atomicity is a property of the store and, on Virtuoso, of its configuration. A generated operation that needs two operations to commit
together cannot assume it, and H5's capability record carries it per deployment, not per product.

**Reproduce it.** On each store, run the request above and then check whether `<urn:s> <urn:p> <urn:o>` is in `<urn:g>`.

---

### TSD-07. Numeric datatypes are not kept by Oxigraph

**Evidence:** Observed on both stores, R-A and R-B.

**Context.** The persistence profile pins every sequence, epoch and position to `xsd:long` (patterns guide Chapter 13), because
`"1"^^xsd:long` and `"1"^^xsd:integer` are different RDF terms and a pattern that matches by term will not match one with the
other. The parameter guard tests `DATATYPE($epoch) = xsd:long` for that reason (ADR-A123, first addendum). On Oxigraph every
guarded operation wrote nothing, and probe P5 found why.

**What the store does.**

```sparql
INSERT DATA { GRAPH <urn:g> { <urn:s> <urn:p> "1"^^<http://www.w3.org/2001/XMLSchema#long> } }
SELECT (DATATYPE(?o) AS ?d) WHERE { GRAPH <urn:g> { ?s ?p ?o } }
```

| Store | Stored object's datatype | `DATATYPE(?o)` |
|---|---|---|
| rdflib 7.6.0 | `xsd:long` | `xsd:long` |
| Oxigraph 0.5.11 | `xsd:integer` | `xsd:integer` |

**Why.** Not read. The observation is that Oxigraph stores an integer-derived literal as `xsd:integer`, and reports it so in every
expression.

**What it means for LATTICE.** The guard's first datatype test, `DATATYPE($p) = xsd:long`, could never pass on Oxigraph, so every
guarded write there wrote nothing (TD-45, FMH-H2-4b decision 1). Guard D replaced it in H2.5 with `DATATYPE($p) = DATATYPE("0"^^xsd:long)`
(ADR-A123, addendum of 2026-10-13), which compares the parameter with what the store makes of a constant. Probe P5 now asserts that
a constant, a substituted parameter, a `VALUES` row and a stored value report one datatype on each store
(`test_h2_5_t1_p5_a_long_has_one_datatype_in_every_form_on_each_engine_so_guard_d_can_pass`), and that a simple literal stays
`xsd:string` in every form. Because every number on Oxigraph is an `xsd:integer`, requests and stored rows match each other, so the
hazard the test guards against cannot arise there. What stays is that the profile's `xsd:long` pinning cannot be checked on Oxigraph.

**Reproduce it.** The two operations above, on each store.

---

### TSD-08. A zero-length path from a term that is in no triple

**Evidence:** Observed on both stores, R-A and R-B. The specification's reading is ours and is not yet checked against the text.

**Context.** The composite sweep starts with `$root <ownedPath> ?s`, and the owned path can take zero steps, so `?s` includes the
root itself. Test H2.4a-T6 asked what happens when the root is in no triple of the data graph.

**What the store does.**

```sparql
# the graph <urn:g> holds only <urn:a> <urn:p> <urn:b>
SELECT ?x WHERE { GRAPH <urn:g> { <urn:lonely> <urn:p>* ?x } }
```

| Store | `?x` |
|---|---|
| rdflib 7.6.0 | `<urn:lonely>` |
| Oxigraph 0.5.11 | no rows |

**What it means for LATTICE.** Nothing changes for the sweep, since `?s ?p ?o` must also match and a term in no triple has none.
H2.8's `payload-check` query starts a path at `$root` over the payload alone, so it must not depend on which reading a store
takes. Its tests run on both.

**Reproduce it.** The query above on each store.

---

### TSD-09. Unicode escapes and an escaped backslash

**Evidence:** Observed on both stores, R-B. Found by H2.1's property test.

**Context.** `persistence.terms.Literal.encode` escapes a backslash as `\\`. A value holding a backslash followed by `u0041`
therefore became the text `"\\u0041"`. SPARQL 1.1 §19.2 says `\u` escapes are processed before the rest of the grammar.

**What the store does.**

| Query text | rdflib 7.6.0 | Oxigraph 0.5.11 |
|---|---|---|
| `"\\u0041"` | syntax error | the five characters `A` |
| `"A"` | `A` | `A` |

```mermaid
flowchart LR
  T["query text<br/>backslash backslash u0041"] --> RP["rdflib: a pre-pass over<br/>the whole text replaces<br/>backslash u0041 first"]
  RP --> RE["leaves a lone backslash<br/>before A: syntax error"]
  T --> OP["Oxigraph: escapes read<br/>inside the string token"]
  OP --> OE["escaped backslash, then u0041:<br/>the value keeps them"]
```

**What it means for LATTICE.** `Literal.encode` now writes the `u` of such a pair, and the hex digits after it, as escapes
themselves, so neither reading changes the value (FMH-H2-1 decision 1). The literal is correct on both stores. Any code that
writes SPARQL text must assume the stricter rdflib reading.

**Reproduce it.** `INSERT DATA { GRAPH <urn:e> { <urn:s> <urn:p> "\\u0041" } }` on each store, then read the value back.

---

### TSD-10. A result row whose projected variables are all unbound

**Evidence:** Observed on both stores, R-A and R-B. Found while making H2.1-T29 pass.

**What the store does.** `SELECT ?b WHERE { BIND(1 AS ?a) { BIND(?a + 1 AS ?b) } }` has one solution, with `?b` unbound.
Oxigraph returns one row with `?b` empty. rdflib returns no rows.

**What it means for LATTICE.** A test that counts rows on rdflib must project at least one variable it knows is bound. T29
selects `?a ?b` for that reason.

---

### TSD-11. `BOUND` and text substitution

**Evidence:** Observed on both stores, R-B.

**Context.** The first parameter guard was `FILTER(BOUND($root) && …)`. A caller that substitutes text writes
`FILTER(BOUND(<urn:x>) && …)`.

**What the store does.** Both refuse it as a syntax error (rdflib `ParseException`, Oxigraph `SyntaxError`), as the grammar
requires, since `BOUND` takes a variable. A type test such as `isIRI(<urn:x>)` parses, and `isIRI(?root)` with `?root` unbound is
an error, which fails the filter.

**What it means for LATTICE.** The guard is a type test per parameter, never `BOUND` (ADR-A123, first addendum). H2.1-T28 and
H2.3-T25 run guarded operations after text substitution.

---

### TSD-12. Initial bindings are visible inside inner groups on rdflib

**Evidence:** Observed on rdflib, R-B. Oxigraph not tested, since our adapter substitutes text.

**What the store does.** With `initBindings={"root": <urn:a>}`, `{ FILTER(isIRI(?root)) }` in its own inner group passes on
rdflib, so the initial binding is seen inside the group. An engine that joined initial bindings in only at the end would make the
guard fail every time, which would fail closed.

**What it means for LATTICE.** The guard in its own group works for an initial-binding caller on rdflib and for a
text-substituting caller anywhere. Another engine's initial-binding API must be probed before it is relied on.

---

### TSD-13. A filter at the top of a group sees what the group's patterns bound

**Evidence:** Observed on both stores, R-B.

**Context.** The H2.1 review's F1. The first guard was a `FILTER` at the top of the `WHERE`, whose patterns also matched `$root`.

**What the store does.**

```sparql
# <urn:a> and <urn:b> each have <urn:seq> 0 in <urn:m>, and ?root is not bound by the caller
INSERT { GRAPH <urn:m> { ?root <urn:w> true } }
WHERE  { FILTER(BOUND(?root)) GRAPH <urn:m> { ?root <urn:seq> ?s } }
```

| Form | rdflib | Oxigraph |
|---|---|---|
| `FILTER` at the top of the group | writes both `<urn:a>` and `<urn:b>` | writes both |
| `{ FILTER(…) }` as its own group | writes nothing | writes nothing |

```mermaid
flowchart TB
  subgraph top["FILTER at the top of the group"]
    P1["patterns bind ?root<br/>from the data"] --> F1["FILTER applied after,<br/>?root is bound"]
    F1 --> W1["every aggregate written"]
  end
  subgraph own["FILTER in its own group"]
    F2["inner group alone:<br/>?root unbound, FILTER fails"] --> J2["join with nothing"]
    J2 --> W2["nothing written"]
  end
```

**What it means for LATTICE.** The guard is its own group (ADR-A123 decision 5). It runs once per request, where the top-level
form ran once per solution and cost about 60% on a 20,000-triple sweep on rdflib.

---

### TSD-14. Graph management operations on rdflib

**Evidence:** Observed, R-A.

**What the store does.** On rdflib 7.6.0, `CREATE GRAPH` is not implemented, and `DROP GRAPH` of a graph that does not exist
succeeds. On Oxigraph 0.5.11, `DROP GRAPH` of an absent graph fails, as the specification says it should without `SILENT`.

**What it means for LATTICE.** A probe or a test that needs an operation to fail at run time on rdflib uses `LOAD` of a source
that does not exist.

---

### TSD-15. A sub-select and the variables around it

**Evidence:** Observed on both stores, R-C. Answers TSD-Q9.

**Context.** The merge and quarantine operations join a sub-select, `{ SELECT ?claim ... GROUP BY ?claim HAVING ... }`, to the
patterns around it. The checker (H2.5) treats a sub-select as evaluated on its own, so it starts with nothing in scope and only its
projections leave it, and it refuses an inner variable that is also used outside without being projected (`SubSelectLeak`).

**What the store does.**

```sparql
# <urn:g2> holds three subjects, <urn:s1> to <urn:s3>
SELECT ?c WHERE { VALUES ?s { <urn:s1> } { SELECT (COUNT(*) AS ?c) WHERE { GRAPH <urn:g2> { ?s <urn:p> ?o } } } }
SELECT ?c WHERE { GRAPH <urn:g1> { { SELECT (COUNT(*) AS ?c) WHERE { ?s ?p ?o } } } }   # <urn:g1> holds two triples
```

| Query | Specification | rdflib | Oxigraph |
|---|---|---|---|
| the count with `?s` bound outside the sub-select | 3, since `?s` inside is another variable | **1**, the outer binding is let in | 3 |
| the count inside `GRAPH <urn:g1>` | 2, the sub-select reads the active graph | 2 | 2 |

**What it means for LATTICE.** A sub-select that reuses an outer variable's name without projecting it gives different results on the
two stores. The `SubSelectLeak` rule makes that a refusal, so no operation the IR builds can depend on it. A sub-select inside a `GRAPH`
block reads that graph on both, so the checker passes the enclosing graph to its patterns. Tests `test_h2_5_t12` and `test_h2_5_t13`.

**Reproduce it.** The two queries on each store.

---

### TSD-16. `MIN` and `MAX` over IRIs

**Evidence:** Observed on both stores, R-C. Answers TSD-Q6.

**Context.** Merge-rewrite picks a claim's canonical owner with `MIN(?owner)` over the owners' IRIs, then compares it with each owner
and writes a link from every other owner to it.

**What the store does.**

```sparql
INSERT DATA { GRAPH <urn:g> { <urn:c> <urn:p> <urn:o:2> , <urn:o:10> , <urn:o:1> } }
SELECT (MIN(?o) AS ?l) (MAX(?o) AS ?h) WHERE { GRAPH <urn:g> { <urn:c> <urn:p> ?o } }
```

| Store | `MIN` | `MAX` |
|---|---|---|
| rdflib 7.6.0 | the literal `"urn:o:1"` | the literal `"urn:o:2"` |
| Oxigraph 0.5.11 | the IRI `<urn:o:1>` | the IRI `<urn:o:2>` |

Both choose by the IRI's text, so `urn:o:10` sorts before `urn:o:2`. `IRI(MIN(STR(?o)))` gives the IRI on both.

**What it means for LATTICE.** The first port of merge-rewrite equalled its template, so on rdflib it wrote a plain literal as the link's object, and because
an IRI is never equal to a literal, `?other != ?canonical` also held for the canonical owner, which got a link to itself. On Oxigraph it wrote IRIs and no
self-link. Decided 2026-10-13 (FMH-H2-5, decision 1): the template and the builder project `IRI(MIN(STR(?owner)))`, which gives an IRI on both
(`test_h2_5_t30`). The `MIN` itself is still different on the two stores and `test_h2_5_t41` keeps the probe.

**Reproduce it.** The two operations above on each store.

---

### TSD-17. A chain of additions and subtractions

**Evidence:** Observed on Oxigraph, R-C, directly through `pyoxigraph`, and on rdflib. **Oxigraph 0.5.12 (2026-10-20, R-H):** Observed and
Documented. It groups from the left. The release notes of 0.5.12 say "group operators of equal precedence from left to right".

**Context.** The gap scan compares `COUNT(DISTINCT ?seq)` with `?S - ?L + 1`. On Oxigraph every audit row for a complete stream was reported
as a gap.

**What the store does.**

```sparql
SELECT (10 - 3 + 2 AS ?x) WHERE {}      SELECT (10 - 3 - 2 AS ?x) WHERE {}      SELECT (8 / 4 / 2 AS ?x) WHERE {}
```

| Query | Specification (from the left) | rdflib | Oxigraph 0.5.11 | Oxigraph 0.5.12 |
|---|---|---|---|---|
| `10 - 3 + 2` | 9 | 9 | **5**, as `10 - (3 + 2)` | 9 |
| `10 - 3 - 2` | 5 | 5 | **9**, as `10 - (3 - 2)` | 5 |
| `8 / 4 / 2` | 1 | 1 | **4**, as `8 / (4 / 2)` | 1 |
| `(10 - 3) + 2` | 9 | 9 | 9 | 9 |

**What it means for LATTICE.** The gap scan's template, written as a chain, counted wrongly on Oxigraph. The renderer therefore always writes the
parentheses of a nested arithmetic operand, and the template now says `(?S - ?L) + 1` (FMH-H2-5, decision 2), both correct on either store. Test
`test_h2_5_t44`, and the harness mutation `test_h2_5_t47`, which fails a builder that groups the sum from the right. The parentheses stay,
since an adopter may run 0.5.11. Since 2026-10-20 `test_h2_5_t44` expects the grouping of the installed version, reading
`LEFT_GROUPED_ARITHMETIC` from `lattice_testing_oxigraph`, and `test_ox_t6` holds the flag to the installed version's behaviour.

**Reproduce it.** The three queries on each store.

---

### TSD-18. `COUNT(DISTINCT)` over `xsd:long` and `xsd:integer` terms

**Evidence:** Observed on both stores, R-C. Answers TSD-Q10 for the counts.

**What the store does.** Three triples with the objects `"1"^^xsd:long`, `"1"^^xsd:integer` and `"2"^^xsd:long`, counted with
`COUNT(DISTINCT ?o)`.

| Count | rdflib | Oxigraph |
|---|---|---|
| over the stored objects | 3 | 2, since it stores both `1`s as `xsd:integer` (TSD-07) |
| over a `VALUES` row of `"1"^^xsd:long` and `"1"^^xsd:integer` | 2 | 1 |

**What it means for LATTICE.** The gap scan counts distinct `seq` terms. A receipt whose `seq` was written with another integer type adds a
term on rdflib and none on Oxigraph, so a duplicate `seq` written that way is reported on rdflib only (`test_h2_5_t43`). Comparisons with `>=` and
`<=` work across numeric types on both. The profile pins positions to `xsd:long`, so this arises only from data written outside the
generated operations.

---

### TSD-19. The order of `GROUP_CONCAT`

**Evidence:** Observed on rdflib, R-C. Answers TSD-Q7 for the query shape of the duplicate audit.

**What the store does.** Six owners stored in a fixed order and concatenated by the duplicate audit's query, run in child processes under
`PYTHONHASHSEED` 0 to 5 (12 seeds in the exploration), gave the same string every time, in the order the owners were stored. Unlike the update of
TSD-01, this query does not go through a hash-ordered join.

**What it means for LATTICE.** The order is the store's scan order and no guarantee. A different query shape or store could differ, so the
audit tests compare owners as a set. Test `test_h2_5_t45`.

---

### TSD-20. A `FILTER` inside `NOT EXISTS` and a parameter

**Evidence:** Observed on both stores, R-C. Answers TSD-Q8.

**What the store does.** `FILTER NOT EXISTS { GRAPH <g> { ?claim <claimedBy> ?other . FILTER(?other != $owner) } }`, after a sub-select that
projects `?claim`, keeps a claim held by the owner or by nobody and drops one held by someone else. The result is the same when `$owner` is
put in the text and when it is an initial binding (rdflib).

**What it means for LATTICE.** `key-claim-write` and merge-rewrite rely on this, and it holds on both stores for both ways of binding.
Test `test_h2_5_t14`.

### TSD-21. An empty `VALUES` block in an update

**Evidence:** Observed on both stores, rdflib 7.6.0 and Oxigraph 0.5.x, probe run for H2.6b.

**What the store does.** `VALUES (?a ?b) { }` as the first element of an update's `WHERE`, with a `DELETE`/`INSERT` template after it, gives no
solution on Oxigraph, so nothing is written. rdflib raises an `AttributeError` while evaluating the block. It does so before it changes
anything, so the store is left as it was.

**What it means for LATTICE.** An append with an empty `eventRows` slot writes nothing on either store, and on rdflib it raises. H2.8's caller
check refuses an empty slot before sending, so the generated operation never meets the difference. Test `test_h2_6b_t6`.

---

### TSD-22. rdflib parses and translates a query's text on every call

**Evidence:** Source (rdflib 7.6.0) and Observed, R-D and R-E. A property of rdflib. Oxigraph was timed from text only.

**Context.** `check:ontology-catalog` validates the ontology shapes with pySHACL on rdflib, and took 427 s. One validation of the exposure fixture took 13 s, and
we wanted to know where.

**How we found it.**

1. `cProfile` of that one test. Under the profiler, which inflates figures two to three times, the pySHACL call took 34 s of 36 s, and 26.6 s of it was
   `pyparsing`, the library rdflib's SPARQL grammar is written in.
2. The profile's callers table. 937 calls of `Processor.query`, each calling `parseQuery`, and `translateQuery` another 3.9 s.
3. A probe that counted the texts: 937 calls, 30 distinct texts.
4. A prototype that translated each distinct text once. The test went from 13.2 s to 1.8 s with the same result, and the whole suite from 427 s to 128 s.

**What the store does.** The same twenty-line constraint query, run for one focus node (benchmark experiment E5).

| Way of running it | Milliseconds per run |
|---|---|
| rdflib, text each time | 20.4 |
| rdflib, prepared once with `prepareQuery` | 0.48 |
| Oxigraph, text each time (parse and run) | 0.17 |

**Why.** `rdflib/plugins/sparql/processor.py`, `SPARQLProcessor.query` (line 144). For a `str` it evaluates `translateQuery(parseQuery(strOrQuery), base,
initNs)`, and for an already translated query it skips both. The grammar is `pyparsing`, in Python. We did not read Oxigraph's parser. Its figure is
consistent with a compiled one.

**What it means for LATTICE.** Parsing and translating is most of what a SHACL-SPARQL validation costs on rdflib (TSD-23 says why it happens so often).
`tools/conftest.py` translates each distinct text once while `ValidationCache` runs pySHACL (`_sparql_translated_once`), keyed on the text, the base and the
prefixes the text uses without declaring (TSD-24, TSD-30). This is not a property of SPARQL or of SHACL, and a different engine or validator may not have
the cost. [Efficient queries and shapes](efficient-queries-and-shapes.md) draws the line.

**Reproduce it.** `mise run check:sparql-constraint-query-cost`, experiment E5.

### TSD-23. pySHACL runs a SPARQL constraint once per focus node

**Evidence:** Source (pySHACL 0.40.1) and Observed, R-D. A property of pySHACL.

**Context.** TSD-22 asked why a validation issued 937 queries.

**What the tool does.** One constraint, 40 focus nodes, a shapes graph with a single `sh:sparql` constraint: 40 calls of `Graph.query`, all with one text.

**Why.** `pyshacl/constraints/sparql/sparql_based_constraints.py`, `_evaluate_sparql_constraint` (line 113), loops over the focus nodes. For each it calls
`sparql_query_helper.py`, `pre_bind_variables` (line 280), which runs `check_invalid_sparql` (a set of regular-expression checks of the text, about 0.4 ms
a call in the profile of TSD-22) and returns `$this` as an initial binding, and then `_validate_sparql_query` (line 169) calls `Graph.query(text,
initBindings=...)`. The SHACL specification defines a SPARQL-based constraint by its result for one focus node, with `$this` pre-bound, and says nothing
about batching. Running once per node is pySHACL's choice.

**What it means for LATTICE.** The cost of a node shape is the number of its focus nodes times the cost of one run, and a shape that targets a common class
has one focus node per instance of that class in the data. Exposure's documentation rule targeted `skos:Concept` and ran 15,713 times over 21 validations.
Whether Jena SHACL or another validator also runs once per node is not tested (TSD-Q14).

**Reproduce it.** A shapes graph with one `sh:sparql` constraint, 40 focus nodes, and `Graph.query` wrapped to count calls. The script is in
[efficient-queries-and-shapes.md](efficient-queries-and-shapes.md#96-reproductions).

### TSD-24. The PREFIX block pySHACL writes changes order between validations

**Evidence:** Source (pySHACL 0.40.1) and Observed, R-D. A property of pySHACL.

**Context.** After TSD-22's cache went in, the wording tests still made 512 parses, and 511 of the texts were distinct.

**What the tool does.** pySHACL writes the constraint's `PREFIX` declarations in front of its `sh:select` text. Twelve validations of one shapes document, parsed
afresh each time, wrote the same five prefixes in two different orders (nine times and three times).

**Why.** `pyshacl/helper/sparql_query_helper.py`, `__init__` (line 57), starts a dict with `rdf`, `rdfs` and `owl`, and adds each `sh:declare` it finds by
iterating the shapes graph. `apply_prefixes` (line 200) writes the dict in that order. We did not trace why the order changes. The likely cause is that
the declarations are blank nodes, whose labels differ between parses, and that the graph yields triples in the order of its indexes (Reasoned).

**What it means for LATTICE.** Text is not a stable cache key. `_canonical_query` in `tools/conftest.py` sorts the leading declarations before keying, and
leaves a text alone that declares a prefix twice, since the later declaration may be the one that applies.

**Reproduce it.** The script in [efficient-queries-and-shapes.md](efficient-queries-and-shapes.md#96-reproductions).

### TSD-25. rdflib fixes the order of a group's patterns before it knows the initial bindings

**Evidence:** Source (rdflib 7.6.0) and Observed on both stores, R-D. A property of rdflib's evaluator. Oxigraph showed no sensitivity.

**Context.** Two shape queries cost far more than the work they did. The peril vocabulary's reference-code uniqueness query took 2.0 s over 405 focus nodes,
and exposure's documentation rule spent 0.7 ms of its 1.4 ms on a single type test.

**What the store does.** A uniqueness test on nodes of one scheme, in two forms with the same solutions (benchmark E2). Milliseconds per focus node, with
`$this` as the focus.

```sparql
# naive: join every other node of the scheme
SELECT … WHERE { $this ex:inScheme ex:S ; ex:code ?c .
                 ?o ex:inScheme ex:S ; ex:code ?c . FILTER (?o != $this) }
# improved: look the other node up by the value, then test its scheme
SELECT … WHERE { $this ex:inScheme ex:S ; ex:code ?c .
                 FILTER EXISTS { ?o ex:code ?c . FILTER (?o != $this) FILTER EXISTS { ?o ex:inScheme ex:S } } }
```

| Nodes | rdflib naive | rdflib improved | Oxigraph naive | Oxigraph improved |
|---|---|---|---|---|
| 200 | 3.5 | 0.21 | 0.058 | 0.063 |
| 400 | 7.2 | 0.21 | 0.052 | 0.067 |
| 800 | 13.8 | 0.22 | 0.058 | 0.065 |

Doubling the nodes doubles the naive form's cost per focus node on rdflib, so its total is quadratic. Neither the improved form nor either form on Oxigraph grows.
A second case (E1) types a variable bound by an earlier pattern. Its cost on rdflib grows with the number of nodes of that type, and `FILTER EXISTS` removes it.

| Schemes (400 focus nodes) | rdflib pattern | rdflib `FILTER EXISTS` | Oxigraph pattern | Oxigraph `FILTER EXISTS` |
|---|---|---|---|---|
| 16 | 0.23 | 0.21 | 0.061 | 0.062 |
| 64 | 0.61 | 0.14 | 0.038 | 0.039 |
| 256 | 2.26 | 0.14 | 0.038 | 0.039 |

**Why.** `rdflib/plugins/sparql/algebra.py`, `simplify` (line 779) calls `reorderTriples` (line 122) on each basic graph pattern when the query is translated.
It sorts the patterns by `_knownTerms` (line 104), the number of variable terms not yet bound by the patterns before it. At translation `$this` is an ordinary
variable, because initial bindings arrive only when the query runs, so `?s a ex:Scheme` (one unknown term) sorts before `$this ex:inScheme ?s` (two). Then
`evalBGP` (`evaluate.py`, line 77) runs the patterns in that order as nested loops, and the first one scans every node of the type. `FILTER EXISTS` is
evaluated for each solution of its group with that solution's values substituted (`operators.py`, `Builtin_EXISTS`, line 580), so inside it `?s` is bound and
the same pattern is a lookup. The two forms mean the same by the specification, which defines `EXISTS` by substitution (SPARQL 1.1 Query §8.1, and the evaluation of `EXISTS` in §18).

SPARQL does not fix the order in which an engine matches the patterns of a group. Oxigraph, which showed no difference, orders them itself. We did not read its
planner. That its naive forms are already fast is Observed.

**What it means for LATTICE.** Rule R1 of [efficient-queries-and-shapes.md](efficient-queries-and-shapes.md). Three shapes changed: peril 0.3.1 (two queries, 2.0 s and
2.3 s down to 0.11 s and 0.13 s over 405 focus nodes), exposure 0.1.1 (the documentation rule, 1.4 ms to 0.19 ms) and wording 0.4.1 (TSD-26, TSD-27). The benefit is
specific to rdflib. The rewrite is harmless elsewhere, since it means the same, but on an optimising engine it buys nothing we measured.

**Reproduce it.** `mise run check:sparql-constraint-query-cost`, experiments E1 and E2.

### TSD-26. A chain of three or more groups is joined by evaluating the later ones whole

**Evidence:** Source (rdflib 7.6.0) and Observed, R-D. A property of rdflib's evaluator. Not measured on Oxigraph.

**Context.** The peril parent-code query joined `?parent skos:notation ?parentCode` after a `UNION` group, and cost as much as the uniqueness join of TSD-25
although it never named another node of the scheme.

**What the store does.** A two-part group passes the left side's bindings into the right side. A group of three or more parts does not. Counting
`Graph.triples` lookups over 300 `ex:has` edges:

| Query | Lookups | Scans with an unbound subject |
|---|---|---|
| `ex:root ex:has ?a . ?a ex:name ?n . ?n ex:kind ?k` (one pattern) | 601 | 0 |
| `ex:root ex:has ?a . { ?a ex:name ?n . ?n ex:kind ?k }` (two parts) | 601 | 0 |
| `ex:root ex:has ?a . { ?a ex:name ?n } { ?n ex:kind ?k }` (three parts) | 302 | 1 |

**Why.** `algebra.py`, `analyse` (line 792) marks a `Join` lazy only when none of its operands is itself a join. `evaluate.py`, `evalJoin` (line 156) then
either pushes the left side's bindings into the right (`evalLazyJoin`, line 141) or evaluates the right side whole into a set and hash-joins (`_join`). A chain
of three parts is left-deep, so its outer join has a join for an operand and is not lazy. Evaluating an operand whole is cheaper than one lookup per left row
when the left side is large. It is expensive when the left side is one row, as it is for every constraint query, because `$this` is pre-bound: the operand's
whole extent (here, every notation of the scheme) is built for each focus node.

What this does not explain. Moving W8's identity lookup ahead of its pair enumeration took that query from 67 ms to 32 ms per wording, and by this mechanism the
join stays non-lazy either way. We did not isolate why it helped (TSD-Q15).

**What it means for LATTICE.** Rule R2: keep a group to two operands, or put the dependent operand in `FILTER EXISTS`, where the substituted solution reaches it.
TSD-Q1 asks about the order of a lazy join's solutions, which this finding does not answer.

**Reproduce it.** The script in [efficient-queries-and-shapes.md](efficient-queries-and-shapes.md#96-reproductions).

### TSD-27. A `FILTER` is applied after its group's patterns, and rdflib does not move it earlier

**Evidence:** Source (rdflib 7.6.0) and Observed on both stores, R-D. The scope is the specification's (§4.3). The cost is the evaluator's.

**Context.** The wording slot-overlap query put three cheap guards (every variant has a condition, every condition is an interval condition, no variant has two)
in the group that then enumerates candidate points. It took 266 ms per slot.

**What the store does.** Guards that reject 90% of the focus nodes, in the group of an enumeration or in a group of their own (benchmark E3). Milliseconds per
focus node, 200 focus nodes.

| Values per node | rdflib same group | rdflib own group | Oxigraph same group | Oxigraph own group |
|---|---|---|---|---|
| 10 | 9.6 | 0.51 | 0.090 | 0.069 |
| 20 | 38.4 | 1.4 | 0.103 | 0.072 |
| 30 | 81.9 | 3.5 | 0.127 | 0.099 |

On the real wording slots the gain was 266 ms to 132 ms for overlap and 119 ms to 82 ms for coverage, smaller than the synthetic gain, which rejects 90% of the
nodes. The gain follows the share of focus nodes the guards reject, so it is large only when they reject most.

**Why.** A `FILTER` applies to the whole group it is written in (§4.3). rdflib wraps the whole group in one `Filter` node (`algebra.py`,
`translateGroupGraphPattern`, around line 343), and `evalFilter` (`evaluate.py`, line 208) tests each solution of `evalPart(ctx, part.p)`, so every solution is
built before any guard runs. In the synthetic case a guard in its own group is the left operand of a lazy join (TSD-26), so a node it rejects never reaches the right operand. We did not
establish that every real query meets that condition, and the wording gain is smaller. Oxigraph orders filters itself, and its two forms differ by 1.3 to 1.5 times.

**What it means for LATTICE.** Rule R3. The sub-group is exactly equivalent when the guards read only variables the sub-group binds, so the change is safe to
make and to check by replay.

**Reproduce it.** `mise run check:sparql-constraint-query-cost`, experiment E3.

### TSD-28. Presence and absence tests: the forms differ little

**Evidence:** Observed on both stores, R-D. Not explained from source.

**Context.** Exposure's documentation rule counted English notes with `OPTIONAL`, `GROUP BY` and `HAVING (COUNT(DISTINCT ?n) < 1)`. We asked whether another form
was cheaper.

**What the store does.** The three forms, over 600 focus nodes with a note on five in six, in milliseconds per focus node. Only rdflib was timed, since Oxigraph rejects the
`GROUP BY` form when the adapter substitutes `$this`.

| Form | rdflib |
|---|---|
| `OPTIONAL`, `GROUP BY`, `HAVING (COUNT(DISTINCT ?n) < 1)` | 0.178 |
| `OPTIONAL`, `FILTER (!BOUND(?n))` | 0.130 |
| `FILTER NOT EXISTS` | 0.126 |

Benchmark E4 compares the last two on both stores: 1.0 to 1.2 times on rdflib and 1.1 to 1.2 times on Oxigraph, which is noise. On the exposure fixture the first
form cost 1.19 ms and `FILTER NOT EXISTS` 0.85 ms (29% less). Turning two pure existence patterns of the instrument word-use query into `FILTER EXISTS` saved 12%.

**What it means for LATTICE.** These are worth taking when a query is being rewritten for another reason, and not worth a shapes release alone. We reverted the
instrument change for that reason. Choose by clarity.

**Reproduce it.** `mise run check:sparql-constraint-query-cost`, experiment E4.

### TSD-29. Two parses of one document never give equal triple sets

**Evidence:** Observed, R-D. Not a store property. A parser mints blank nodes (the RDF 1.1 Turtle and N-Triples specifications scope blank-node labels to a
document), so this holds for any parser.

**Context.** Exposure's test fixture is seven Turtle files, parsed afresh for each of twenty tests. Two tests that validated the same unchanged fixture never
shared a validation, although `ValidationCache` keys on a graph's content.

**What happens.** The fixture has 768 blank-node terms. Two parses compared as sets differ, and they are isomorphic. A copy of one parse (`Graph() + graph`)
keeps the labels, so two copies compare equal as sets.

**What it means for LATTICE.** A cache keyed on triple content cannot hit across parses. Build a fixture once with `graph_cache` and give each test a copy
(`tools/test_exposure_ontology.py`, `_fixture`). The copy cost 0.14 s against 0.28 s to parse.

**Reproduce it.** The script in [efficient-queries-and-shapes.md](efficient-queries-and-shapes.md#96-reproductions).

### TSD-30. A query's undeclared prefixes resolve from the data graph's bindings

**Evidence:** Source (rdflib 7.6.0) and Observed, R-D. A property of rdflib.

**Context.** The first version of the translation cache of TSD-22 keyed on all of a graph's namespace bindings, and missed: 1,258 parses for 94 distinct texts in one
test file.

**What the store does.** `g.query("SELECT ?s WHERE { ?s ex:p ?o }")` on a graph with `ex` bound gives its rows, and without the binding raises `Unknown namespace
prefix : ex`.

**Why.** `rdflib/graph.py`, `Graph.query` (line 1716): `initNs = initNs or dict(self.namespaces())`. So a translation depends on the text and on the graph's
bindings for the prefixes the text uses and does not declare. A prefix the text declares itself wins over the graph's.

**What it means for LATTICE.** A cache key holds the text, the base and the bindings of the undeclared prefixes the text uses (`_sparql_translated_once`). Replaying
a recorded validation needs the data graph's bindings restored. Whether Oxigraph has a fallback was not tested.

**Reproduce it.** The script in [efficient-queries-and-shapes.md](efficient-queries-and-shapes.md#96-reproductions).

### TSD-31. pySHACL copies the data graph on every validation unless told not to

**Evidence:** Source (pySHACL 0.40.1) and Observed, R-D. A property of pySHACL.

**What the tool does.** `validate(..., inplace=False)` (`pyshacl/entrypoints.py`, line 40) clones the data graph (`rdfutil/load.py`, `clone_graph`). In a profile of
24 validations of a 5,000 to 14,000 triple graph, the clones took 2.2 s, about 0.09 s each.

**What it means for LATTICE.** A fixed cost per validation that grows with the size of the data, about 9% of a validation in that profile. `inplace=True` would remove
it, and pySHACL then may change the graph (inference, rules). Our caches share graphs between tests, and a guard fails the run when one changes
(`_graph_cache_not_mutated`), so we did not adopt it (TSD-Q16).

### TSD-32. A constant `FILTER` whose value is false is dropped by rdflib

**Evidence:** Source (rdflib 7.6.0) and Observed on both stores, R-D. A defect in rdflib. Oxigraph is correct.

**Context.** The benchmark's test of its own pass criterion used `FILTER (false)` for a deliberately wrong query, and the check did not fail.

**What the store does.** Rows returned by `SELECT ?s WHERE { ?s ex:p ?o FILTER (<constant>) }` over two triples.

| Constant | rdflib | Oxigraph | Correct |
|---|---|---|---|
| `false`, `0`, `""`, `0.0` | 2 | 0 | 0 |
| `true`, `1`, `"x"` | 2 | 2 | 2 |
| `!true`, `1 = 2`, `true && false`, `false || false` | 0 | 0 | 0 |

The same drop occurs inside a `UNION` branch and a sub-group, and it inverts `EXISTS` and `NOT EXISTS`: `FILTER NOT EXISTS { ?s ex:p ?x FILTER (false) }` returns
0 rows on rdflib where 2 are correct.

**Why.** `rdflib/plugins/sparql/algebra.py`, `collectAndRemoveFilters` (line 278) returns `and_(*filters)`, which for one filter is that filter itself
(`operators.py`, `and_`, line 975). `translateGroupGraphPattern` then tests `if filters:` and builds the `Filter` node only when that is true. A lone constant
whose Python truth value is false (`Literal(False)`, `Literal(0)`, `Literal("")`) fails the test, and the algebra has no `Filter` node. A compound expression is
an object that is always true, which is why `true && false` works.

**What it means for LATTICE.** Never write a constant false filter to make a probe fail, on any engine, since rdflib ignores it. Break a triple pattern instead.
The authoring skill said so for pySHACL (`FILTER (false)` is reported for every focus node), and this is the reason.

**Reproduce it.** `SELECT ?s WHERE { ?s ?p ?o FILTER (false) }` over a graph with a triple.

### TSD-33. On Oxigraph, `COUNT(*)` over a statically false filter returns no row

**Evidence:** Observed, R-D. Not explained from source. A probable defect in Oxigraph 0.5.11.

**What the store does.** `SELECT (COUNT(*) AS ?n) WHERE { ?s ex:p ?o FILTER (<constant>) }`.

| Filter | rdflib | Oxigraph | Correct |
|---|---|---|---|
| `FILTER (1 = 2)`, a pattern that matches nothing, `FILTER (?o = ex:zz)` | one row, `n = 0` | one row, `n = 0` | one row, `n = 0` |
| `FILTER (false)` | one row, `n = 2` (TSD-32) | no row | one row, `n = 0` |
| `FILTER (true && false)` | one row, `n = 0` | no row | one row, `n = 0` |

An aggregate query without `GROUP BY` always has exactly one solution (SPARQL 1.1 Query §11, Aggregates), so no row is wrong. It happens when the engine can decide the
filter is false before it runs, and not when it has to evaluate it.

**What it means for LATTICE.** Code that reads the first row of a `COUNT` from `OxigraphStore.select` should expect none (the benchmark's pass criterion never
writes such a filter). The mechanism is open (TSD-Q17).

### TSD-34. rdflib evaluates a `FILTER NOT EXISTS` in a `GRAPH` block against the wrong graph for some solutions

**Evidence:** Source (rdflib 7.6.0) and Observed on both stores, R-F and R-G. A defect in rdflib. Oxigraph is correct. FMH-H2-6f and TD-68 first put this down to initial bindings, which this finding corrects. Reported upstream as [RDFLib/rdflib#3585](https://github.com/RDFLib/rdflib/issues/3585). The Why was corrected 2026-10-20 (§7.5).

**Context.** The `members` read (H2.6f) is slow on rdflib over a long chain (TD-68). A form with the nearest-checkpoint test moved into a sub-select took 0.15 s where the original took about 100 s,
but its result kept members that a later version had dropped. We took the cause to be rdflib ignoring `initBindings` inside the sub-select, and recorded that as the reason the form was not used.

**How we found it.**

1. *Initial bindings in a sub-select.* We ran `SELECT ?m WHERE { GRAPH <g> { { SELECT ?m WHERE { $v <p> ?m } } } }` with `v` as an initial binding on rdflib and as text on Oxigraph, and variants with the variable projected, unprojected, under `LIMIT`,
   under an aggregate, and inside `FILTER NOT EXISTS { SELECT ... }`. Every variant applied the value on both stores. The first cause was wrong.
2. *The members query.* We rebuilt the sub-select form on a six version chain. rdflib kept a dropped member and Oxigraph did not, with the checkpoint test in the sub-select. Moving the drop test into a sub-select instead gave the right answer on both. Replacing the sub-select by a pattern that returns the same rows also gave the right answer.
3. *Bisecting.* Cutting the query down, the wrong answer needed all of a sub-select, a `UNION` and a `FILTER NOT EXISTS` with no `GRAPH` of its own, in one `GRAPH` block. Dropping any one gave the right answer.
4. *The seed.* The same query gave a different answer in different runs. Sweeping `PYTHONHASHSEED` (skill `lattice-triple-stores`) over 32 child processes gave the wrong answer for 13 seeds and the right one for 19, with a constant in place of the parameter,
   and 15 and 17 with the parameter. So a parameter plays no part.
5. *The graph.* We traced the `NOT EXISTS` body. For the wrong solution its context's graph was the `Dataset` and not the named graph, so the body, which has no `GRAPH`, searched the default graph and found nothing.
6. *The line.* Replacing the two lines of `evalGraph` that reset the graph with `pass` gave the right answer for all 8 seeds we tried, where the stock code gave the wrong answer for 6 of them.
   **Corrected 2026-10-20 (R-G):** it gives the right answer on all 32 seeds, but it is not a fix. It breaks a `FILTER EXISTS` outside the block on every seed (Why).

**What the store does.** Data in `<g>` is a chain `v3 prev v2 prev v1` where `v1` has members `a` and `b`, `v2` drops `a` and adds `c`. The members of `v3` are `b` and `c`.

```sparql
SELECT ?m WHERE { GRAPH <g> {
  { SELECT ?cp WHERE { ?cp <cp> ?t } }
  <v3> <prev>* ?w . ?w <prev>* ?cp .
  { ?w <has> ?m } UNION { ?w <adds> ?m }
  FILTER NOT EXISTS { ?x <drops> ?m ; <prev> ?z . ?z <prev>* ?w . <v3> <prev>* ?x }
} }
```

| Form | rdflib, over 32 seeds | Oxigraph | Correct |
|---|---|---|---|
| as written, constant `<v3>` | `b c` for 19 seeds, `a b c` for 13 | `b c` | `b c` |
| as written, `$v` as an initial binding (text on Oxigraph) | `b c` for 17, `a b c` for 15 | `b c` | `b c` |
| the sub-select replaced by `?cp <cp> ?t .` | `b c` for all 32 | `b c` | `b c` |
| the sub-select kept, no `UNION` (`?w <has> ?m`) | `b` for every seed we tried | `b` | `b` |

**Why.** *Corrected 2026-10-20 (R-G, §7.5). The first text had `evalGraph` reset the graph after it yields a solution, and took step 6's change for the fix.*
`rdflib/plugins/sparql/evaluate.py`, `evalGraph` (line 220), evaluates the block's pattern in a context whose graph is the named graph. Before it yields each solution it sets `x.ctx.graph = prev_graph` (lines 242 and 251), the enclosing graph.
`Builtin_EXISTS` (`operators.py`, line 580) is the only code that reads a solution's own context. It thaws that context and evaluates the body in it. The reset makes an `EXISTS` outside the block read the enclosing graph, and for the solution being yielded it does.
A solution's `ctx` is the context object it was made in, and solutions made without a new binding scope share one, so the reset also reaches solutions the block has not yet produced. `evalFilter` (line 208) evaluates a filter inside the block on each solution as the generator produces it.
Once the first solution has left the block, the shared context's graph is the dataset, which here reads the default graph (`default_union` is false), so the next `NOT EXISTS` body finds nothing and keeps the member.
Which solution comes first decides how many are affected. A sub-select joined to a `UNION` is a non-lazy join (`evalJoin`, line 156), whose right side is built in a Python `set`, so the order follows the hash seed (TSD-01).
`Dataset` is created with `default_union` false. A body that has a `GRAPH` of its own does not depend on the context's graph, and putting one in the body gave the right answer for all 32 seeds. We did not isolate why the sub-select matters and the `UNION` alone does not (TSD-Q19).
A plain `FILTER EXISTS` is affected too. `GRAPH <g1> { { SELECT ?o WHERE { ?a <p> ?o } LIMIT 1 } { ?s <p> ?o } UNION { ?s <r> ?o } FILTER EXISTS { ?s <q> ?x } }` gave 15 different wrong answers over 32 seeds and the right one for none, both adding and dropping rows.

**The fix (R-G).** Removing the reset (step 6) is not one. It gives the right answer inside the block, and the wrong one on every seed for an `EXISTS` outside it, after `GRAPH <iri>`, after `GRAPH ?g` and after a nested `GRAPH`.
Yielding `FrozenBindings(ctx, x.items())`, a new solution on `evalGraph`'s own context, whose graph is already the enclosing one, mutates no shared context and was right in every case on every seed. With that change, rdflib's own SPARQL, W3C, dataset and conjunctive-graph tests at `main` `62bf240` give the same result as without it, with the same W3C outcomes test by test.
None of them covers the defect. It reproduces on 7.6.0, on `main` (7.7.0a0, `62bf240`) and on `next` (8.0.0a0, `0fdac39`), and [RDFLib/rdflib#3585](https://github.com/RDFLib/rdflib/issues/3585) reports it with a standalone harness of these cases and proposes the change.

**What it means for LATTICE.**

- Initial bindings inside a sub-select work on both stores. TD-68's account of the fast form of the `members` read is wrong, and the note on it should say so and cite this finding. The form is still not usable on rdflib.
- **Added 2026-10-20 (H2.8c).** The sub-select form with a `GRAPH` inside each `NOT EXISTS` body is right. It read every version of 24 random histories (checkpoint every 2, 3 and 4 versions, stray adds) as the reference model gives, on rdflib under 16 hash seeds in child processes and on Oxigraph, and the existing histories of `test_membership.py` on both engines with and without guards. It is the `members` read since H2.8c. The read of version 100 of a set of 500 took 1.28 s on rdflib, where the form without a sub-select took 98.6 s, and 0.005 s on Oxigraph, where it took 1.7 s (`benchmark/persistence-membership`).
- The `members` read had no sub-select, and no history we built exposed the defect in it on 192 runs over 16 seeds (FMH-H2-6g). Its two `NOT EXISTS` bodies depend on solution variables, so it is the one generated operation where the defect could change an outcome. Since H2.6g each body names its graph, and a sweep holds it to the reference model.
- A fast form of `members` on rdflib should put a `GRAPH` inside each `FILTER [NOT] EXISTS` body, which the audits (`key-claim-quarantine`, `key-claim-merge-rewrite`) already do, or avoid a sub-select beside a `UNION` in one `GRAPH` block, and be tested on a sweep of hash seeds against the reference model of `test_membership.py`.
- Which generated operations had the shape, and what it could change (H2.6g, TSD-Q19), is in the next subsection. Every builder now states a `GRAPH` inside such a body, and the IR checker refuses a `NOT EXISTS` inside a `GRAPH` block whose body has none (`NotExistsWithoutGraph`).
- A test of a `FILTER [NOT] EXISTS` inside `GRAPH` on rdflib must sweep seeds in child processes, as the probe for this finding does. One run in the test process measures luck.
- The probe is `test_tsd_34_*` in `tools/persistence/tests/test_store_probes.py`. It asserts the defect on rdflib, so a fix in rdflib fails it and this entry is then updated.

**Which generated operations had the shape (FMH-H2-6g, answering TSD-Q19 in part).** A scan of the rendered text of every operation the examples generate found 29 builders (operation ids) with a `FILTER NOT EXISTS`
with no `GRAPH` of its own inside a `GRAPH` block. `FILTER EXISTS` is not used by any builder, and the audits and key claims already named their graph.

| Builders | The body | Solutions in the block | Can the defect change the outcome |
|---|---|---|---|
| `append-version`, `append-version-delta`, the six `cas-replace-*` and six `tombstone-delete-*` variants, each with its dataset-guard variant (28 operations) | `$root pat:deleted true` in the row's graph | one per head and per current version of the row | No |
| `members` | the nearest-checkpoint test and the drop test, on `?cp`, `?w` and `?member` | one per candidate checkpoint, version and member | Possibly. Not exposed by any history we built |

The solutions of a row block do share one context on rdflib. We counted the contexts of the yielded solutions with a row of three heads and three current versions, and `cas-replace-composite-property` yielded three solutions in one context, `append-version` three in each of three. The OPTIONAL that
reads `pat:head` does it, so a sub-select is not needed for the sharing (the sub-select's own part in TSD-34 stays open). The write guards still cannot be wrong, for a reason that does not depend on how many solutions share a context. `evalGraph` resets the context's graph only when a solution leaves the block (wording corrected 2026-10-20, §7.5), and a body that mentions only `$root`, one value in every solution,
gives the same answer for every solution. If the first is dropped nothing is yielded and nothing is reset. If the first is kept, all are kept, and the wrong graph keeps what the right graph keeps. The defect can only keep a solution wrongly after another was kept rightly, which needs a body that depends on a solution variable. The test on 28
operations has a tombstoned row, three heads and three current versions, 16 seeds in child processes and Oxigraph once, and a live row as the control. The tombstoned row is never written.
The same sweep still passes when the `GRAPH` is taken out of a template, so only the text scan, the equivalence harness and the checker rule guard against that. `members` has bodies that depend on solution variables, and a sweep of 192 random histories (checkpoint every 2, 3 and 4 versions, 16 seeds) and the nine version history with stray adds were right on the text
that had no `GRAPH`. In that read the solutions did not share a context. We put the `GRAPH` in anyway, so the checker rule has no exception and a later rdflib cannot expose it.

**Reproduce it.** Run the query above over the data of the table's caption, once for each `PYTHONHASHSEED` from 0 to 31, in a child process with `rdflib.Dataset`, and once on Oxigraph.
`mise exec -- python -m pytest tools/persistence/tests/test_store_probes.py -q -k tsd_34` runs it on rdflib, and `mise run check:persistence-oxigraph` on both.

## 7. Corrections, and what they taught us

### 7.1 rdflib and the order of an update (TSD-01)

The typed IR sketch first said, from reading `evalModify`, that rdflib applies an update one solution at a time. H2.4b's probe
then reported that rdflib keeps the specification's order, and a dated note in the sketch said the first statement was wrong.
The first statement was right. The probe had happened to run in processes whose hash seeds put the deleting row first. While
checking, one of our own traces, which read every binding of each solution, also gave a result we did not reproduce later. We
note it rather than explain it.

What we take from it. A probe on rdflib whose answer depends on the order of solutions must fix or sweep `PYTHONHASHSEED`, or it
measures luck. A conclusion that contradicts the source needs the source re-read before it is recorded. And a trace should touch
as little of the engine's state as it can.

### 7.2 Variable scope (TSD-03)

The checker first let every inner group see the enclosing group's variables. The H2.1 review then changed the `GRAPH` block to do
the same, calling it a fix. A probe on rdflib showed the opposite: no inner group but `NOT EXISTS` sees them. Planning H2.3 then
found that a pattern's solutions *are* joined with the enclosing group, which is a different question from what a `BIND` can see.
The checker now tracks both. Each step was a claim about SPARQL written from memory, and each was settled only by running a query.
That is why every semantic rule the checker encodes now has an engine test (Track H plan §5.1).

### 7.3 The retry on rdflib

The spike `spikes/persistence-oxigraph` once reported that rdflib and Oxigraph disagreed on a retried append. The cause was two
bugs in the first scratch scripts. rdflib does materialise the solutions of a `WHERE` before it changes anything, as its
`list(res)` shows. That is a different property from applying the changes in the specification's order, which TSD-01 shows it
does not.

### 7.4 Cost claims, and what the first versions got wrong

Four statements about cost were wrong or incomplete when first written, and a probe corrected each.

- We first called a chain of groups "slower unless lazy". A probe that counted lookups (TSD-26) showed that evaluating an operand whole can be cheaper than one
  lookup per row. It is expensive only when the left side is one row, which is the case for a constraint query, and the record now says that.
- The first reproduction of the guard group (TSD-27) came out backwards, 0.6 times where we expected a gain. The guard group we wrote bound a variable with 25
  values, so it multiplied the rows. The real guard group binds one variable. A reproduction has to be checked against the thing it stands for, as the gain
  is a property of the rejection rate and the group's cardinality.
- "Move the existence check into `FILTER EXISTS`" was first measured on the exposure documentation rule as 1.4 times, from rewriting the count as `NOT EXISTS`.
  The real cost was the type pattern (TSD-25), found only by removing the query's parts one at a time.
- `FILTER (false)` (TSD-32) was found because a test of the benchmark's own pass criterion did not fail. The authoring skill had warned against it without a
  reason.

What we take from it. State what a mechanism does not explain, as TSD-26 does for W8. Time the parts of a slow query separately before rewriting it. And test
that a check can fail.

### 7.5 The mechanism of TSD-34

TSD-34 first said that `evalGraph` resets a solution's graph after yielding it, and its step 6 found that removing the reset gave the right answer on 8 seeds.
Read that way, the reset looked like the mistake and removing it like the fix. Writing a fix for the upstream report, we re-read the source. The reset comes
before the yield, and it is there so that an `EXISTS` outside the block reads the enclosing graph. A probe of `EXISTS` outside a `GRAPH` block confirmed it.
Without the reset every such case was wrong on every seed. The defect is that the context being reset is shared, not that it is reset.

What we take from it. A change that makes a failing case pass is not a fix until the cases the changed code exists for have been run. Before calling a line
wrong, find out why it is there.

## 8. Open questions

| # | Question | Why it matters | Next step |
|---|---|---|---|
| TSD-Q1 | does rdflib order a lazy join's solutions deterministically | only non-lazy joins go through a `set`, so some updates may have a fixed order | read `evalLazyJoin` and probe a lazy form |
| TSD-Q2 | what Oxigraph does with initial bindings, if `pyoxigraph` offers them for updates | TSD-12 holds for rdflib only | probe it |
| TSD-Q3 | whether the specification's zero-length path includes a constant endpoint in no triple | TSD-08 names one store as right without checking the text | re-read SPARQL 1.1 §18.4 |
| TSD-Q4 | the isolation half of request atomicity, and whether inserting an identical statement conflicts | H5's models branch on both | H5, with concurrent writers |
| TSD-Q5 | why Oxigraph turns `xsd:long` into `xsd:integer` | TSD-07 is observed, not explained | read Oxigraph's literal encoding |
| TSD-Q11 | whether Oxigraph groups a chain of same-precedence operators from the right in a later version, and why in 0.5.11 | TSD-17 is observed, not explained, and the renderer works around it | read the parser, try the newer releases, and report it upstream if it still holds |
| TSD-Q12 | whether Fuseki, which `platform/semantic-dataset-fuseki` targets, shows TSD-15 to TSD-18 | they are measured on two in-process stores only | run the same probes against it |
| TSD-Q13 | whether Virtuoso applies even one `DELETE`/`INSERT` atomically under `log_enable(2)` or `(2,1)`, and whether Jena TDB2 and Neptune make a multi-operation request one transaction | the guarded writes assume a single operation is atomic, and a two-operation form assumes the request is (TSD-06) | probe each store, with a failing operation and with a large update interrupted, starting with Fuseki (TSD-Q12) |
| TSD-Q14 | whether Jena SHACL, TopBraid or another validator runs a SPARQL constraint once per focus node, and what a node shape costs there | TSD-23 and the choice of targets (rule R6) are measured on pySHACL only | run the same shapes on another validator |
| TSD-Q15 | why moving W8's identity lookup ahead of its pair enumeration halved its cost | TSD-26 does not explain it | trace the join order and the sizes of the operands |
| TSD-Q16 | what `inplace=True` saves, and whether it is safe with shared graphs | TSD-31's 9% is a fixed cost per validation | run the suite with a copy per test and `inplace=True`, and with the mutation guard on |
| TSD-Q17 | why Oxigraph returns no row for `COUNT(*)` over a statically false filter | TSD-33 is observed, not explained | read Oxigraph's query optimiser |
| TSD-Q18 | whether Fuseki or Jena ARQ shows the sensitivity of TSD-25 to TSD-27 | the rules in ADR-A128 assume only rdflib is sensitive | run benchmark `sparql-constraint-query-cost` against a Fuseki endpoint |
| TSD-Q19 | why the sub-select decides TSD-34 when a `UNION` alone does not, and whether Fuseki or Jena ARQ shows the defect | TSD-34 is isolated on a non-lazy join of a sub-select and a `UNION`. The part of TSD-Q19 about the generated operations is answered under TSD-34 (FMH-H2-6g) | trace which solution comes first and which are kept in TSD-34's query, and run the query on Fuseki. The defect was reported upstream 2026-10-20 ([RDFLib/rdflib#3585](https://github.com/RDFLib/rdflib/issues/3585)) |
