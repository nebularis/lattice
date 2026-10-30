<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->

# Upstream reports on SPARQL engines

Each engine departure from the SPARQL 1.1 specification that the store-discovery record (`docs/architecture/triple-store-discovery.md`) finds is written up here as a report ready to file with the engine's project, with its reproduction in full, so it can be filed from this file alone. Filing is the maintainer's decision (TSD-Q32). A report's text was written on 2026-10-27 against the versions it names, so rerun its reproduction on the current release before filing it, and search the tracker again.

## Reproducing

- **A Python reproduction** (rdflib or pyoxigraph). Save the test as a file outside the repository and run it with `mise exec -- python -m pytest <file>` from this checkout, which has rdflib and pyoxigraph installed. In a clean environment `pip install rdflib pyoxigraph pytest` is enough.
- **A Java reproduction** (Apache Jena ARQ). Build the test kit with `mise run bootstrap:sparql-testkit`, which writes `platform/sparql-testkit/target/sparql-testkit.jar` with Jena ARQ and its dependencies in it. Save the class as `Repro.java` and run `java -cp platform/sparql-testkit/target/sparql-testkit.jar Repro.java` (Java 11 or later runs a single source file). Each exits 1 while the departure holds.
- The same behaviours are checked per engine by `mise run check:sparql-probes-conformance`, so a release that changes one fails that task and points back here.

## Reports

| Report | Engine | Finding | State |
|---|---|---|---|
| [oxigraph-left-join-reads-every-graph](#oxigraph-left-join-reads-every-graph) | Oxigraph | TSD-42 | filed 2026-10-27 as [oxigraph/oxigraph#2008](https://github.com/oxigraph/oxigraph/issues/2008) |
| [oxigraph-count-error](#oxigraph-count-error) | Oxigraph | TSD-43 | filed 2026-10-27 as [oxigraph/oxigraph#2009](https://github.com/oxigraph/oxigraph/issues/2009) |
| [oxigraph-avg-all-unbound](#oxigraph-avg-all-unbound) | Oxigraph | TSD-43 | not filed |
| [jena-avg-all-unbound](#jena-avg-all-unbound) | Apache Jena ARQ | TSD-43 | not filed |
| [jena-str-of-blank-node](#jena-str-of-blank-node) | Apache Jena ARQ | TSD-43 | not filed |
| [jena-clear-graph-of-a-store-without-empty-graphs](#jena-clear-graph-of-a-store-without-empty-graphs) | Apache Jena ARQ | TSD-50 | not filed |
| [jena-group-concat-distinct-empty-group](#jena-group-concat-distinct-empty-group) | Apache Jena ARQ | TSD-43 | already reported upstream as [apache/jena#4240](https://github.com/apache/jena/issues/4240), fix proposed in [apache/jena#4243](https://github.com/apache/jena/pull/4243), so nothing to file |
| [rdflib-aggregate-skips-error-rows](#rdflib-aggregate-skips-error-rows) | rdflib | TSD-43 | not filed |
| [rdflib-sum-over-iri-raises](#rdflib-sum-over-iri-raises) | rdflib | TSD-43 | not filed |
| [rdflib-aggregate-over-erroring-if](#rdflib-aggregate-over-erroring-if) | rdflib | TSD-60 | not filed |
| [rdflib-string-number-ordering](#rdflib-string-number-ordering) | rdflib | TSD-61 | not filed |
| [rdflib-str-of-blank-node](#rdflib-str-of-blank-node) | rdflib | TSD-43 | not filed |
| [rdflib-grouped-query-over-no-rows](#rdflib-grouped-query-over-no-rows) | rdflib | TSD-43 | covered by the open pull request [RDFLib/rdflib#3498](https://github.com/RDFLib/rdflib/pull/3498), to be checked against the constant-projection case before anything is filed |

### oxigraph-left-join-reads-every-graph

**0.5.13: `OPTIONAL { GRAPH ?g { ... } }` with `?g` bound outside reads every graph, where 0.5.11 and 0.5.12 read one**

Oxigraph, TSD-42, filed 2026-10-27 as [oxigraph/oxigraph#2008](https://github.com/oxigraph/oxigraph/issues/2008).

**Version:** pyoxigraph 0.5.13 (regression from 0.5.12). Python 3.14, macOS arm64.

**Query:**

```sparql
SELECT (COUNT(*) AS ?n) WHERE { BIND(<urn:g:0> AS ?g) OPTIONAL { GRAPH ?g { ?s ?p ?o } } }
```

`VALUES ?g { <urn:g:0> }` in place of `BIND` behaves the same.

**What we measured.** 100 named graphs of 3,000 triples against 1 graph of 3,000, best of five:

| Form | 0.5.11 | 0.5.12 | 0.5.13 |
|---|---|---|---|
| `BIND(<g> AS ?g) OPTIONAL { GRAPH ?g {...} }` | 1.0 | 1.0 | 73 to 82 |
| `VALUES ?g { <g> } OPTIONAL { GRAPH ?g {...} }` | 1.0 | 1.0 | 73 to 82 |
| `BIND(<g> AS ?g) GRAPH ?g {...}` (a join) | 1.0 | 1.0 | 1.0 |
| `GRAPH <g> {...}` (a constant) | 1.0 | 1.0 | 1.0 |

The value is the time over 100 graphs divided by the time over one. The result is the same on every version, only the cost moves. On 0.5.13 the left join no longer passes the outer binding of `?g` into its right side, so the inner `GRAPH ?g` is evaluated over every graph and the join discards all but one.

**Why it matters.** A sweep that clears one root's graph, with the graph IRI bound outside an `OPTIONAL`, now costs in proportion to the number of graphs in the store.

**Possibly related.** #1733 (merged 2026-06-04) re-optimises the right side of a `LeftJoin` using the variables the left side provides, and #1980 reports slow `VALUES ?g` and `OPTIONAL` plans on many named graphs on 0.5.11. Neither says what changed between 0.5.12 and 0.5.13, and we have not bisected the commits.

Reproduce with the test below.

#### Tracker search

Searched with the GitHub search API on 2026-10-27. `repo:oxigraph/oxigraph OPTIONAL GRAPH slow` gave 9 results. Related and open, not the same: #1980 (VALUES ?g after GRAPH ?g and OPTIONAL as a for-loop, slow on many named graphs, reported on 0.5.11). Also #1883 (open, GROUP BY over OPTIONAL) and the merged #1733. `repo:oxigraph/oxigraph left join performance 0.5.13` gave 0. No existing report of the 0.5.12 to 0.5.13 change, so a new issue would be needed, and it could link #1980.

#### Reproduction, `test_issue.py`

```python
"""Standalone. Fails on pyoxigraph 0.5.13, passes on 0.5.11 and 0.5.12. Run: python -m pytest test_issue.py

A timing test, so it compares two sizes of the same query on one machine and allows a wide margin (the observed ratio on 0.5.13 is 70 to 80)."""
import time

import pyoxigraph as ox

QUERY = "SELECT (COUNT(*) AS ?n) WHERE { BIND(<urn:g:0> AS ?g) OPTIONAL { GRAPH ?g { ?s ?p ?o } } }"
TRIPLES = 3000


def store(graphs):
    s = ox.Store()
    p = ox.NamedNode("urn:p")
    s.extend(ox.Quad(ox.NamedNode(f"urn:s{j}"), p, ox.Literal(str(j)), ox.NamedNode(f"urn:g:{i}")) for i in range(graphs) for j in range(TRIPLES))
    return s


def best(s):
    fastest = float("inf")
    for _ in range(5):
        start = time.perf_counter()
        n = int(next(iter(s.query(QUERY)))["n"].value)
        fastest = min(fastest, time.perf_counter() - start)
        assert n == TRIPLES
    return fastest


def test_a_graph_variable_bound_outside_an_optional_reads_one_graph():
    ratio = best(store(100)) / best(store(1))
    assert ratio < 10, f"100 graphs cost {ratio:.0f} times one graph"
```

### oxigraph-count-error

**`COUNT(expr)` returns no value when `expr` errors on one row, instead of counting the rows where it does not**

Oxigraph, TSD-43, filed 2026-10-27 as [oxigraph/oxigraph#2009](https://github.com/oxigraph/oxigraph/issues/2009).

**Version:** pyoxigraph 0.5.13 (also 0.5.11). Python 3.14, macOS arm64.

**Query** (empty store):

```sparql
SELECT (COUNT(STR(?x)) AS ?n) WHERE { VALUES ?x { <urn:a> UNDEF } }
```

**Expected:** `?n` = `1`.

**Actual:** `?n` is unbound.

**Why 1.** SPARQL 1.1 Query §18.5.1.2 defines `Count` as counting "the number of times a given expression has a bound, and non-error value". Its definition removes the error elements from `Flatten(M)` before taking the cardinality. `STR(?x)` is an error on the row where `?x` is unbound, so that row is dropped and the other is counted.

**Controls** (same data):

| Query | Oxigraph | Expected |
|---|---|---|
| `COUNT(?x)` | 1 | 1 |
| `COUNT(*)` | 2 | 2 |
| `COUNT(STR(?x))` | unbound | 1 |
| `COUNT(DISTINCT STR(?x))` | unbound | 1 |
| `COUNT(?x + 0)` | unbound | 1 |

`COUNT(?x)` is right because a bare variable takes the internal `CountInternal` path. Any other expression falls back to `AccumulatorWrapper::Expression` or `DistinctExpression` in `lib/spareval/src/eval.rs`, whose `accumulate` sets the accumulator to `None` when the evaluator returns `None`, so the whole group's result is unbound. That suits `SUM`, `AVG` and `GROUP_CONCAT`, where §18.5.1 keeps the error, but `Count` removes it.

**Possible fix.** For `COUNT` through the expression path, skip a tuple whose evaluation returns `None` instead of failing the accumulator.

**Failing test** (`pip install pyoxigraph pytest`, then `pytest test_count_error.py`):

```python
import pyoxigraph
import pytest

ROWS = "VALUES ?x { <urn:a> UNDEF }"


def count(expression):
    [solution] = list(pyoxigraph.Store().query(f"SELECT (COUNT({expression}) AS ?n) WHERE {{ {ROWS} }}"))
    return None if solution["n"] is None else int(solution["n"].value)


@pytest.mark.parametrize("expression", ["STR(?x)", "DISTINCT STR(?x)", "?x + 0", "LCASE(STR(?x))"])
def test_count_removes_error_elements(expression):
    assert count(expression) == 1
```

#### Tracker search

Searched with the GitHub search API on 2026-10-27. `repo:oxigraph/oxigraph COUNT error` gave 31 results, of which the first 14 were read (cancellation, HTTP server, decimal `*` and `/` #1975, ORDER BY, GROUP BY with HAVING #646, and similar), and none is about `COUNT` of an expression that errors. `repo:oxigraph/oxigraph COUNT unbound expression aggregate` gave 3 (#2000, #1789, #208), none relevant. The remaining 17 results of the first search were not read. Nothing to link, so a new issue would be needed.

#### Reproduction, `test_count_error.py`

```python
"""COUNT(expr) must drop rows where expr errors (SPARQL 1.1 Query, section 18.5.1.2).

Run with:  pip install pyoxigraph pytest && pytest test_count_error.py
"""

import pyoxigraph
import pytest

# One row binds ?x, the other leaves it unbound, so STR(?x) is an error on that row.
ROWS = "VALUES ?x { <urn:a> UNDEF }"


def count(expression: str) -> object:
    store = pyoxigraph.Store()
    [solution] = list(store.query(f"SELECT (COUNT({expression}) AS ?n) WHERE {{ {ROWS} }}"))
    return None if solution["n"] is None else int(solution["n"].value)


@pytest.mark.parametrize("expression", ["?x", "*"])
def test_controls(expression):
    assert count(expression) == (1 if expression == "?x" else 2)


@pytest.mark.parametrize("expression", ["STR(?x)", "DISTINCT STR(?x)", "?x + 0", "LCASE(STR(?x))"])
def test_count_removes_error_elements(expression):
    # Count(M) removes error elements from Flatten(M), then takes its cardinality, so the answer is 1.
    assert count(expression) == 1, f"pyoxigraph {pyoxigraph.__version__}: COUNT({expression}) is unbound"
```

### oxigraph-avg-all-unbound

**`AVG` over a group where every row has no value is unbound, and the specification gives 0**

Oxigraph, TSD-43, not filed.

**Version:** pyoxigraph 0.5.13. Python 3.14, macOS arm64.

**Query** (empty store):

```sparql
SELECT (AVG(?x) AS ?a) WHERE { VALUES ?x { UNDEF UNDEF } }
```

**Expected:** `?a` = `0` (`xsd:integer`).

**Actual:** `?a` is unbound.

**Why 0.** SPARQL 1.1 Query section 18.5.1.4 defines `Avg(M) = "0"^^xsd:integer, where Count(M) = 0` and `Sum(M) / Count(M)` otherwise. Section 18.5.1.2 defines `Count` by removing the error elements, and an unbound `?x` is an error element, so `Count(M)` is 0 here and the first clause applies. rdflib returns `0`. Apache Jena ARQ 5.1.0 returns unbound as Oxigraph does (reported separately).

**Controls** (same engine): `AVG` over `1` and `2` is `1.5`. `AVG` over `1`, `2` and an unbound row is unbound, which is right, since `Count` is 2 and `Sum` is an error. `SUM` over the all-unbound group is unbound, which is also right (the error propagates through `op:numeric-add`).

**Likely cause.** The accumulator is set to `None` on the first argument that evaluates to nothing, so the group never reaches the `Count = 0` clause. A fix would count the non-error elements and return 0 when there are none, while still returning unbound for a mix of values and errors.

Reproduce with the test below.

#### Tracker search

Searched with the GitHub search API on 2026-10-27. `repo:oxigraph/oxigraph AVG aggregate` gave 1 result, #533 (closed, 2023, "Makes SPARQL AVG aggregate function simpler"), which is a code change and not this behaviour. `repo:oxigraph/oxigraph AVG unbound` gave 0. Nothing to link, so a new issue would be needed.

#### Reproduction, `test_issue.py`

```python
"""Standalone. Fails on pyoxigraph 0.5.13. Run: python -m pytest test_issue.py"""
import pyoxigraph


def test_avg_over_a_group_with_no_value_is_zero():
    # SPARQL 1.1 section 18.5.1.4: Avg(M) = "0"^^xsd:integer where Count(M) = 0
    [solution] = list(pyoxigraph.Store().query("SELECT (AVG(?x) AS ?a) WHERE { VALUES ?x { UNDEF UNDEF } }"))
    assert solution["a"] is not None and solution["a"].value == "0"
```

### jena-avg-all-unbound

**`AVG` over a group where every row has no value is unbound, and the specification gives 0**

Apache Jena ARQ, TSD-43, not filed.

Apache Jena ARQ 5.1.0, OpenJDK 25.0.2, `ModelFactory.createDefaultModel()`.

```sparql
SELECT (AVG(?x) AS ?a) WHERE { VALUES ?x { UNDEF UNDEF } }
```

Expected `0` (`xsd:integer`). Actual: `?a` is unbound.

SPARQL 1.1 Query section 18.5.1.4: `Avg(M) = "0"^^xsd:integer, where Count(M) = 0`. Section 18.5.1.2 removes error elements before `Count`, and an unbound `?x` is an error element, so `Count(M)` is 0. `COUNT(?x)` over the same rows is 0 on Jena, so the engine agrees with the specification on the count and not on the average. `AVG` over `1`, `2` and an unbound row is unbound on Jena, which is right.

Reproduce with `java -cp <jena-arq with its dependencies> Repro.java`. It prints the value and exits 1 while it is unbound.

#### Tracker search

Searched with the GitHub search API on 2026-10-27. `repo:apache/jena AVG aggregate unbound` gave 0 results and `repo:apache/jena AVG empty group` gave 0. Nothing to link, so a new issue would be needed.

#### Reproduction, `Repro.java`

```java
import org.apache.jena.query.*;
import org.apache.jena.rdf.model.*;

/** Run: java -cp <jena-arq with its dependencies> Repro.java. Exits 1 while AVG over an all-unbound group is unbound. */
public class Repro {
    public static void main(String[] args) {
        String q = "SELECT (AVG(?x) AS ?a) WHERE { VALUES ?x { UNDEF UNDEF } }";
        try (QueryExecution qe = QueryExecutionFactory.create(q, ModelFactory.createDefaultModel())) {
            QuerySolution s = qe.execSelect().next();
            RDFNode a = s.get("a");
            System.out.println("AVG = " + a + "  (SPARQL 1.1 section 18.5.1.4 gives 0)");
            if (a == null) System.exit(1);
        }
    }
}
```

### jena-str-of-blank-node

**`STR` of a blank node returns the label**

Apache Jena ARQ, TSD-43, not filed.

Apache Jena ARQ 5.1.0, OpenJDK 25.0.2.

```sparql
SELECT (STR(?b) AS ?s) WHERE { BIND(BNODE() AS ?b) }
```

SPARQL 1.1 Query section 17.4.2.5 defines `STR(term)` for an IRI or a literal. A blank node is neither, so the call is a type error and `?s` is unbound. Jena returns the node's label. pyoxigraph 0.5.13 returns unbound, rdflib 7.6.0 returns the label.

Jena's label is useful and a change may break users, so this may be better handled as documented behaviour. We report it as a departure.

Reproduce with `java -cp <jena-arq with its dependencies> Repro.java`. It exits 1 while a value is returned.

#### Tracker search

Searched with the GitHub search API on 2026-10-27. `repo:apache/jena STR blank node SPARQL` gave 1 result, #1315 (closed, 2022, SERVICE clause), and `repo:apache/jena str bnode label error` was refused with HTTP 403 (rate limit) and not repeated. Nothing relevant found.

#### Reproduction, `Repro.java`

```java
import org.apache.jena.query.*;
import org.apache.jena.rdf.model.*;

/** Run: java -cp <jena-arq with its dependencies> Repro.java. Exits 1 while STR of a blank node returns a value. */
public class Repro {
    public static void main(String[] args) {
        String q = "SELECT (STR(?b) AS ?s) WHERE { BIND(BNODE() AS ?b) }";
        try (QueryExecution qe = QueryExecutionFactory.create(q, ModelFactory.createDefaultModel())) {
            RDFNode s = qe.execSelect().next().get("s");
            System.out.println("STR(bnode) = " + s + "  (SPARQL 1.1 section 17.4.2.5: an error, so unbound)");
            if (s != null) System.exit(1);
        }
    }
}
```

### jena-clear-graph-of-a-store-without-empty-graphs

**CLEAR GRAPH of a graph that is not there fails on an in-memory dataset, DROP GRAPH of the same graph succeeds**

Apache Jena ARQ, TSD-50, not filed.

Observed with Apache Jena ARQ 5.1.0 on OpenJDK 25.0.2, `DatasetFactory.createTxnMem()`.

#### What happens

On a transactional in-memory dataset, which does not keep an empty graph, `CLEAR GRAPH <g>` of a graph with no triples fails with "No such graph". `DROP GRAPH <g>` of the same graph succeeds. So does `CREATE GRAPH <g>` followed by `DROP GRAPH <g>`. `CREATE GRAPH <g> ; CLEAR GRAPH <g>` fails.

#### What SPARQL 1.1 Update says

Section 3.2.1 (CLEAR) and 3.2.2 (DROP) both say that a store that records empty graphs SHOULD return failure by default if the named graph does not exist, and that stores that do not record empty graphs will always return success.

#### Expected

If the dataset does not record empty graphs, `CLEAR GRAPH <g>` succeeds, as `DROP GRAPH <g>` does. If it records them, `CREATE GRAPH <g> ; DROP GRAPH <g>` and `CREATE GRAPH <g> ; CLEAR GRAPH <g>` should agree with each other.

#### Reproduce

`java -cp <jena-arq with its dependencies> Repro.java`. It prints the three outcomes and exits 1 while CLEAR fails.

#### Why it matters

A caller that sends a request with several operations, of which one is `CLEAR GRAPH <g>` of a graph the request may or may not have written to, gets a failure that rolls back the whole request, on this dataset and not on a store that treats the two operations alike.

#### Reproduction, `Repro.java`

```java
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.sparql.core.DatasetGraph;
import org.apache.jena.update.UpdateAction;
import org.apache.jena.update.UpdateFactory;

/** Run: java -cp <jena-arq and its dependencies> Repro.java. Exit 1 when CLEAR GRAPH fails where DROP GRAPH succeeds on a graph that is not there. */
public class Repro {
    static String run(String update) {
        DatasetGraph dsg = DatasetFactory.createTxnMem().asDatasetGraph();
        try {
            UpdateAction.execute(UpdateFactory.create(update), dsg);
            return "success";
        } catch (RuntimeException e) {
            return "failure: " + e.getMessage();
        }
    }

    public static void main(String[] args) {
        String drop = run("DROP GRAPH <urn:absent>");
        String clear = run("CLEAR GRAPH <urn:absent>");
        String createThenClear = run("CREATE GRAPH <urn:new> ; CLEAR GRAPH <urn:new>");
        System.out.println("DROP GRAPH <urn:absent>                      " + drop);
        System.out.println("CLEAR GRAPH <urn:absent>                     " + clear);
        System.out.println("CREATE GRAPH <urn:new> ; CLEAR GRAPH <urn:new> " + createThenClear);
        // SPARQL 1.1 Update 3.2.1 and 3.2.2: a store that does not record empty graphs always returns success, for CLEAR as for DROP.
        System.exit(clear.equals("success") && createThenClear.equals("success") ? 0 : 1);
    }
}
```

### jena-group-concat-distinct-empty-group

**`GROUP_CONCAT(DISTINCT ...)` over an empty group is unbound, and the specification gives the empty string**

Apache Jena ARQ, TSD-43, already reported upstream as [apache/jena#4240](https://github.com/apache/jena/issues/4240), fix proposed in [apache/jena#4243](https://github.com/apache/jena/pull/4243), so nothing to file.

Apache Jena has [apache/jena#4240](https://github.com/apache/jena/issues/4240) (open, 2026-09-20, "GROUP_CONCAT(DISTINCT ...) over an empty group returns an unbound value instead of the empty string") and a pull request [apache/jena#4243](https://github.com/apache/jena/pull/4243) (open). We confirmed the behaviour on Jena ARQ 5.1.0 with the class below, which prints the two results and exits 1 while the `DISTINCT` form is unbound. The non-distinct form returns the empty string on 5.1.0, as the specification asks.

Nothing to file. Re-run `Repro.java` and `mise run check:sparql-probes-conformance` (cell `GROUP_CONCAT(DISTINCT expr) | empty`) on each Jena release after that pull request lands.

#### Reproduction, `Repro.java`

```java
import org.apache.jena.query.*;
import org.apache.jena.rdf.model.*;

/** Run: java -cp <jena-arq with its dependencies> Repro.java. Exits 1 while GROUP_CONCAT(DISTINCT) over an empty group is unbound. */
public class Repro {
    public static void main(String[] args) {
        String q = "SELECT (GROUP_CONCAT(DISTINCT ?x) AS ?g) (GROUP_CONCAT(?x) AS ?h) WHERE { ?s <urn:p> ?x }";
        try (QueryExecution qe = QueryExecutionFactory.create(q, ModelFactory.createDefaultModel())) {
            QuerySolution s = qe.execSelect().next();
            System.out.println("DISTINCT: " + s.get("g") + "   plain: " + s.get("h") + "   (SPARQL 1.1 section 18.5.1.7 gives the empty string for both)");
            if (s.get("g") == null) System.exit(1);
        }
    }
}
```

### rdflib-aggregate-skips-error-rows

**`SUM`, `AVG`, `MIN` and `GROUP_CONCAT` skip a row whose argument has no value, and `COUNT(expr)` counts it**

rdflib, TSD-43, not filed.

rdflib 7.6.0. Python 3.14.

SPARQL 1.1 Query section 18.5.1 defines `Sum`, `Avg` (with a non-zero count) and `GroupConcat` over the flattened multiset, where an error element makes the result an error, so the aggregate is unbound. `Count` is the exception, which removes error elements before counting (18.5.1.2).

```sparql
SELECT (SUM(?x) AS ?s) (1 AS ?k) WHERE { VALUES ?x { 1 2 UNDEF } }
SELECT (COUNT(STR(?x)) AS ?n) WHERE { VALUES ?x { <urn:a> UNDEF } }
```

Expected: `?s` unbound, `?n` 1. Actual on rdflib: `?s` is `3` and `?n` is `2`. In `aggregates.py`, `Sum.update` catches `NotBoundError` and passes ("skip UNDEF"), and `Counter.update` counts any error other than `NotBoundError`. The cause is deliberate in the code, so this may be a design choice. pyoxigraph 0.5.13 and Apache Jena ARQ 5.1.0 return an unbound `?s`. For `COUNT(expr)` Jena returns 1, and pyoxigraph is unbound (reported separately).

We could not tell from the project's documentation whether skipping is intended. If it is, a note in the SPARQL conformance page would help callers who move between engines.

Reproduce with the test below.

#### Tracker search

Searched with the GitHub search API on 2026-10-27. `repo:RDFLib/rdflib aggregate GROUP BY` gave 15 results, and the nearest is #563 (closed, 2015, "aggregate operators COUNT and SAMPLE should ignore NULL values"), which asked for the behaviour that `Sum.update` still has. `repo:RDFLib/rdflib COUNT unbound error expression` gave 1 (#3612, translateAlgebra, closed). The skip is deliberate in the code and may have been requested by #563, so a new issue should ask rather than assert.

#### Reproduction, `test_issue.py`

```python
"""Standalone. Both tests fail on rdflib 7.6.0. Run: python -m pytest test_issue.py"""
from rdflib import Graph


def one(query):
    [row] = list(Graph().query(query))
    return row[0]


def test_sum_over_a_group_with_a_row_that_has_no_value_is_unbound():
    # SPARQL 1.1 section 18.5.1.3: the unbound row is an error element, op:numeric-add of an error is an error
    assert one("SELECT (SUM(?x) AS ?s) (1 AS ?k) WHERE { VALUES ?x { 1 2 UNDEF } }") is None


def test_count_of_an_expression_does_not_count_the_row_where_it_errors():
    # SPARQL 1.1 section 18.5.1.2: Count removes error elements. STR(?x) is an error where ?x is unbound
    assert int(one("SELECT (COUNT(STR(?x)) AS ?n) WHERE { VALUES ?x { <urn:a> UNDEF } }")) == 1
```

### rdflib-sum-over-iri-raises

**`SUM` over a group that holds an IRI raises `AttributeError` when the result is read**

rdflib, TSD-43, not filed.

rdflib 7.6.0. Python 3.14.

```sparql
SELECT (SUM(?x) AS ?s) WHERE { VALUES ?x { 1 <urn:a> } }
```

Expected (SPARQL 1.1 Query section 18.5.1.3): `Sum` applies `op:numeric-add`, which is a type error for an IRI, so the aggregate is an error and `?s` is unbound. Apache Jena ARQ 5.1.0 and pyoxigraph 0.5.13 return an unbound `?s`.

Actual: `AttributeError` (`SPARQLResult` has no attribute `bindings`, since the evaluator's generator failed inside it) raised while the result is iterated, not when `query()` returns. In `rdflib/plugins/sparql/aggregates.py`, `Sum.update` catches `NotBoundError` and passes, and does not catch the `SPARQLTypeError` that `numeric()` raises for an IRI. `AVG` over the same rows skips the IRI instead of raising, so the two aggregates disagree. A blank node behaves like the IRI.

See also the separate report on `SUM(IF(...))`.

Reproduce with the test below.

#### Tracker search

Searched with the GitHub search API on 2026-10-27. `repo:RDFLib/rdflib SUM non-numeric aggregate` gave 0 and `repo:RDFLib/rdflib SUM aggregate AttributeError` gave 0. The 15 results of `aggregate GROUP BY` included none about SUM over a non-numeric term (the nearest is #563, closed in 2015, COUNT and SAMPLE should ignore NULL). A new issue would be needed.

#### Reproduction, `test_issue.py`

```python
"""Standalone. Fails on rdflib 7.6.0 with AttributeError. Run: python -m pytest test_issue.py"""
from rdflib import Graph

QUERY = "SELECT (SUM(?x) AS ?s) WHERE { VALUES ?x { 1 <urn:a> } }"


def test_sum_over_an_iri_is_unbound_and_does_not_raise():
    # SPARQL 1.1 section 18.5.1.3: op:numeric-add of an IRI is a type error, so the sum is an error and ?s is unbound
    rows = list(Graph().query(QUERY))
    assert all(row.s is None for row in rows)
```

### rdflib-aggregate-over-erroring-if

**SUM over IF(...) whose condition errors on one row raises AttributeError**

rdflib, TSD-60, not filed.

rdflib 7.6.0. `?d` is unbound for the row `"abc"`, because `"abc" + 1` is a type error and `BIND` leaves it unbound. `SUM(IF(?d = "P", 1, 0))` then evaluates `IF` over an unbound `?d`.

Expected (SPARQL 1.1 section 18.5.1): the aggregate argument errors on that row, so `SUM` is an error and `?r` is unbound. Apache Jena ARQ 5.1.0 and pyoxigraph 0.5.13 both return an unbound `?r`.

Actual: `AttributeError: 'SPARQLTypeError' object has no attribute 'datatype'`, raised from `Sum.update` at `rdflib/plugins/sparql/aggregates.py` line 133 (`type_promotion(dt, value.datatype)`), when the result is read, not when `query()` returns. The evaluated `IF` hands the exception object back as a value and `Sum` treats it as a literal. `MAX(IF(...))` over the same rows returns no row instead of an unbound one.

Reproduce with the test below.

#### Reproduction, `test_issue.py`

```python
"""Standalone. Fails on rdflib 7.6.0 with AttributeError. Run: python -m pytest test_issue.py"""
from rdflib import Graph

QUERY = """SELECT (SUM(IF(?d = "P", 1, 0)) AS ?r) WHERE {
  VALUES ?c { 7 "abc" }
  BIND(IF(?c + 1 > 5, "P", "D") AS ?d)
}"""


def test_aggregate_over_an_expression_that_errors_does_not_crash():
    # SPARQL 1.1 section 18.5.1: the error makes the SUM an error, so ?r is unbound. It must not raise a Python error.
    rows = list(Graph().query(QUERY))
    assert all(row.r is None for row in rows)
```

### rdflib-string-number-ordering

**Ordering a string against a number returns a boolean where the specification gives a type error**

rdflib, TSD-61, not filed.

rdflib 7.6.0. `"abc" >= 5` is `true`, `"abc" < 5` is `false` and `5 < "abc"` is `true`. SPARQL 1.1 section 17.3 defines the ordering operators for pairs of the same kind, so the others are a type error and the result is unbound. Apache Jena ARQ 5.1.0 and pyoxigraph 0.5.13 return an unbound result for all three. `"abc" = 5` is `false` on all three, as the specification says.

It matters where a filter or an `IF` decides on a value of the wrong type: rdflib takes a branch where the other engines raise the error that drops the row.

Reproduce with the test below.

#### Reproduction, `test_issue.py`

```python
"""Standalone. Fails on rdflib 7.6.0. Run: python -m pytest test_issue.py"""
from rdflib import Graph


def value(expression):
    rows = list(Graph().query(f"SELECT ?r WHERE {{ BIND(({expression}) AS ?r) }}"))
    return rows[0].r


def test_ordering_a_string_against_a_number_is_a_type_error():
    # SPARQL 1.1 section 17.3 operator mapping: <, >, <=, >= are defined for numerics, simple literals, xsd:string, boolean and dateTime
    # pairs of the same kind only. Any other pair is a type error, so ?r is unbound. = and != do not error.
    for expression in ('"abc" >= 5', '"abc" < 5', '5 < "abc"'):
        assert value(expression) is None, expression
```

### rdflib-str-of-blank-node

**`STR` of a blank node returns the label**

rdflib, TSD-43, not filed.

rdflib 7.6.0. Python 3.14.

```sparql
SELECT (STR(?b) AS ?s) WHERE { BIND(BNODE() AS ?b) }
```

SPARQL 1.1 Query section 17.4.2.5 defines `STR(term)` for an IRI or a literal. A blank node is neither, so the call is a type error and `?s` is unbound. pyoxigraph 0.5.13 returns unbound. rdflib returns the node's label. Apache Jena ARQ 5.1.0 returns the label too (reported separately).

Reproduce with the test below.

#### Tracker search

Searched with the GitHub search API on 2026-10-27. `repo:RDFLib/rdflib str bnode BNode SPARQL` gave 15 results, of which 12 were read (#3609 on `||` and `&&` three-valued logic is the nearest, closed) and none is about `STR` of a blank node. The last 3 were not read. A new issue would be needed.

#### Reproduction, `test_issue.py`

```python
"""Standalone. Fails on rdflib 7.6.0. Run: python -m pytest test_issue.py"""
from rdflib import Graph

QUERY = "SELECT (STR(?b) AS ?s) (1 AS ?k) WHERE { BIND(BNODE() AS ?b) }"


def test_str_of_a_blank_node_is_an_error():
    # SPARQL 1.1 section 17.4.2.5 defines STR for IRIs and literals only, so STR of a blank node is an error and ?s is unbound
    [row] = list(Graph().query(QUERY))
    assert row.s is None
```

### rdflib-grouped-query-over-no-rows

**A `GROUP BY` query over no rows returns one row**

rdflib, TSD-43, covered by the open pull request [RDFLib/rdflib#3498](https://github.com/RDFLib/rdflib/pull/3498), to be checked against the constant-projection case before anything is filed.

rdflib 7.6.0. Python 3.14.

```sparql
SELECT (COUNT(*) AS ?n) (1 AS ?k) WHERE { ?s a <urn:T> } GROUP BY ?s
```

on an empty graph returns one row, with `?n` unbound and `?k` 1. The row is an empty solution that the projection extends. Without the constant `(1 AS ?k)` rdflib drops a row whose projected variables are all unbound, so the query appears to return nothing (a separate behaviour). SPARQL 1.1 Query section 18.2.4.1 forms one group per distinct key, so with no solutions there is no group and no row. Only a query with no `GROUP BY` has the single implicit group, and returns a row for `COUNT(*)`. Apache Jena ARQ 5.1.0 and pyoxigraph 0.5.13 return no row.

In `rdflib/plugins/sparql/evaluate.py`, `evalAggregateJoin` ends with a "there were no matches" branch that yields one empty row whether or not the query has a `GROUP BY`. The branch should apply only when there is no `GROUP BY`.

Reproduce with the test below.

#### Tracker search

Searched with the GitHub search API on 2026-10-27. `repo:RDFLib/rdflib aggregate GROUP BY` gave 15 results. Already addressed by an open pull request, [RDFLib/rdflib#3498](https://github.com/RDFLib/rdflib/pull/3498), "fix(sparql): return no solutions for a GROUP BY with no matches" (opened 2026-07-30). Not merged at 7.6.0. So no new issue, and we should check #3498 against the constant-projection case above before filing anything.

#### Reproduction, `test_issue.py`

```python
"""Standalone. Fails on rdflib 7.6.0. Run: python -m pytest test_issue.py"""
from rdflib import Graph

QUERY = "SELECT (COUNT(*) AS ?n) (1 AS ?k) WHERE { ?s a <urn:T> } GROUP BY ?s"


def test_a_grouped_query_over_no_rows_returns_no_row():
    # SPARQL 1.1 section 18.2.4.1: with GROUP BY there is a group per distinct key, so no row gives no group
    assert list(Graph().query(QUERY)) == []
```
