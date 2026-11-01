# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The cost of the forms of a SHACL-SPARQL constraint query, on rdflib and Oxigraph (ADR-A124, ADR-A128).

A SHACL-SPARQL constraint runs once per focus node, with `$this` bound to the node, and a node shape that targets a
common class has hundreds of focus nodes. How the query is written decides what each run costs. This check holds the
forms that mattered when we made the ontology tests faster, each as a pair of queries that return the same rows, a
naive form and an improved one, and measures both on rdflib (initial bindings, a prepared query) and on Oxigraph (the
parameter substituted into the text, as a client without initial bindings would).

| Experiment | The naive form | The improved form |
|---|---|---|
| E1 | a pattern that types a variable `?s` bound by an earlier pattern | the same test as `FILTER EXISTS`, once `?s` is bound |
| E2 | a uniqueness test that joins every other node of the scheme | the same test as a lookup by the value, in `FILTER EXISTS` |
| E3 | cheap guards in the same group as an enumeration | the guards in a group of their own, ahead of it |
| E4 | an absence test as `OPTIONAL` and `FILTER(!BOUND)` | the same test as `FILTER NOT EXISTS` |
| E5 | a constraint query handed to the engine as text on every run | the same query parsed once (rdflib only) |

**Pass criterion.** In every experiment, at every size, on every engine, the naive and the improved form return the same
number of solutions for every focus node, and the engines agree with each other. A wrong result fails the check.
**Time never fails it.** What each form costs is the point of the check, and the cost depends on the machine and on the
engine. The timings go to `report.json` and `report.md` in this directory, which are generated and git-ignored.

Run `mise run check:sparql-constraint-query-cost`. `SPARQL_COST_QUICK=1` runs the two smallest sizes of each experiment.
Each query projects `COUNT(*)` and not `$this`, since the Oxigraph adapter substitutes the parameter as text and
`SELECT <iri>` is not SPARQL. The count also makes the engine enumerate every solution, as a constraint does when it
reports."""

from __future__ import annotations

import json
import math
import os
import platform
import sys
import time
from dataclasses import dataclass, field
from datetime import date
from functools import partial
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
EX = "http://example.org/"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
PREFIX = f"PREFIX ex: <{EX}> "
COUNT = "SELECT (COUNT(*) AS ?n) WHERE "

Triple = tuple[str, str, str, str]  # subject, predicate, kind ("iri", "str", "int" or "en"), object


class WrongResult(AssertionError):
    """Two forms, or two engines, returned different solutions. This is the one way the check fails."""


@dataclass
class Experiment:
    key: str
    title: str
    size_label: str
    sizes: tuple[int, ...]
    build: Callable[[int], tuple[list[Triple], list[str]]]  # size -> (triples, focus nodes)
    naive: str
    improved: str
    fit_growth: bool = True  # False where the size is not meant to change the cost, so a fit would only describe noise


@dataclass
class Measurement:
    experiment: str
    engine: str
    size: int
    focus_nodes: int
    naive_seconds: float
    improved_seconds: float


@dataclass
class Report:
    run_record: str = ""
    measurements: list[Measurement] = field(default_factory=list)
    parse: dict[str, float] = field(default_factory=dict)  # seconds per run, by way of running the same query

    def growth(self, experiment: str, engine: str, form: str) -> float | None:
        """The exponent k in (time per focus node) ~ size^k, fitted by least squares on log-log."""
        points = [
            (math.log(m.size), math.log(getattr(m, f"{form}_seconds") / m.focus_nodes))
            for m in self.measurements
            if m.experiment == experiment and m.engine == engine and getattr(m, f"{form}_seconds") > 0
        ]
        if len(points) < 2:
            return None
        n = len(points)
        mean_x = sum(x for x, _ in points) / n
        mean_y = sum(y for _, y in points) / n
        denominator = sum((x - mean_x) ** 2 for x, _ in points)
        return sum((x - mean_x) * (y - mean_y) for x, y in points) / denominator if denominator else None


# ---- the data of each experiment -------------------------------------------------------------------------------------


def e1_data(schemes: int) -> tuple[list[Triple], list[str]]:
    """400 concepts, each in one of `schemes` schemes, every scheme typed `ex:Scheme`."""
    triples = [(f"{EX}s{i}", RDF_TYPE, "iri", f"{EX}Scheme") for i in range(schemes)]
    focus = []
    for i in range(400):
        concept = f"{EX}c{i}"
        focus.append(concept)
        triples.append((concept, f"{EX}inScheme", "iri", f"{EX}s{i % schemes}"))
    return triples, focus


def e2_data(n: int) -> tuple[list[Triple], list[str]]:
    """n nodes of one scheme, each with its own code, so that no node has a duplicate."""
    triples, focus = [], []
    for i in range(n):
        node = f"{EX}u{i}"
        focus.append(node)
        triples += [(node, f"{EX}inScheme", "iri", f"{EX}S"), (node, f"{EX}code", "str", f"code{i}")]
    return triples, focus


def e3_data(values: int) -> tuple[list[Triple], list[str]]:
    """200 nodes with `values` values each. Every tenth passes the guard (`ex:kind ex:Interval`)."""
    triples, focus = [], []
    for i in range(200):
        node = f"{EX}f{i}"
        focus.append(node)
        triples += [(node, f"{EX}kind", "iri", f"{EX}Interval" if i % 10 == 0 else f"{EX}Other"), (node, f"{EX}variable", "iri", f"{EX}v")]
        triples += [(node, f"{EX}value", "int", str(j)) for j in range(values)]
    return triples, focus


def e4_data(n: int) -> tuple[list[Triple], list[str]]:
    """n concepts, five in six with a note in English."""
    triples, focus = [], []
    for i in range(n):
        concept = f"{EX}c{i}"
        focus.append(concept)
        triples.append((concept, RDF_TYPE, "iri", f"{EX}Concept"))
        if i % 6:
            triples.append((concept, f"{EX}note", "en", "n"))
    return triples, focus


EXPERIMENTS = (
    Experiment(
        "E1", "A pattern that types a variable bound earlier, or the same test as FILTER EXISTS", "schemes", (16, 64, 256), e1_data,
        COUNT + "{ $this ex:inScheme ?s . ?s a ex:Scheme }",
        COUNT + "{ $this ex:inScheme ?s . FILTER EXISTS { ?s a ex:Scheme } }",
    ),
    Experiment(
        "E2", "Uniqueness by joining every other node, or by a lookup on the value", "nodes", (200, 400, 800), e2_data,
        COUNT + "{ $this ex:inScheme ex:S ; ex:code ?c . ?o ex:inScheme ex:S ; ex:code ?c . FILTER (?o != $this) }",
        COUNT + "{ $this ex:inScheme ex:S ; ex:code ?c . FILTER EXISTS { ?o ex:code ?c . FILTER (?o != $this) FILTER EXISTS { ?o ex:inScheme ex:S } } }",
    ),
    Experiment(
        "E3", "Guards in the group of an enumeration, or in a group of their own", "values per node", (10, 20, 30), e3_data,
        COUNT + "{ $this ex:variable ?g . $this ex:value ?a . $this ex:value ?b . FILTER (?a < ?b) FILTER EXISTS { $this ex:kind ex:Interval } }",
        COUNT + "{ { $this ex:variable ?g . FILTER EXISTS { $this ex:kind ex:Interval } } $this ex:value ?a . $this ex:value ?b . FILTER (?a < ?b) }",
    ),
    Experiment(
        "E4", "An absence test as OPTIONAL and FILTER(!BOUND), or as FILTER NOT EXISTS", "nodes", (600, 1200), e4_data,
        COUNT + "{ $this a ex:Concept . OPTIONAL { $this ex:note ?x . FILTER (LANG(?x) = 'en') } FILTER (!BOUND(?x)) }",
        COUNT + "{ $this a ex:Concept . FILTER NOT EXISTS { $this ex:note ?x . FILTER (LANG(?x) = 'en') } }",
        fit_growth=False,
    ),
)

# E5. About twenty lines, with unions, an optional, a filter that tests absence and several that test values.
PARSE_QUERY = COUNT + """{
  $this ex:value ?a . $this ex:value ?b . FILTER (?a < ?b)
  { $this ex:kind ?k } UNION { $this ex:other ?k }
  OPTIONAL { ?k ex:label ?l }
  FILTER NOT EXISTS { $this ex:note ?x . FILTER (LANG(?x) = 'en') }
  BIND (COALESCE(?l, 1) AS ?step) FILTER (?step > 0)
  { $this ex:p1 ?p . ?p ex:p2 ?q } UNION { $this ex:p3 ?p . ?p ex:p4 ?q }
  FILTER (STRSTARTS(STR(?k), "http://example.org/")) FILTER (?a != ?b) FILTER (BOUND(?step))
}"""
PARSE_DATA = [(f"{EX}f", f"{EX}value", "int", "1"), (f"{EX}f", f"{EX}value", "int", "2"), (f"{EX}f", f"{EX}kind", "iri", f"{EX}K")]


# ---- the engines -----------------------------------------------------------------------------------------------------


class RdflibEngine:
    """rdflib 7.6: the focus node is an initial binding, and the query is prepared once, as pySHACL's caller could."""

    name = "rdflib"

    def __init__(self) -> None:
        from rdflib import Graph

        self.graph = Graph()

    @staticmethod
    def version() -> str:
        import rdflib

        return rdflib.__version__

    def load(self, triples: list[Triple]) -> None:
        from rdflib import Literal, URIRef

        for s, p, kind, o in triples:
            term = URIRef(o) if kind == "iri" else Literal(int(o)) if kind == "int" else Literal(o, lang="en") if kind == "en" else Literal(o)
            self.graph.add((URIRef(s), URIRef(p), term))

    def prepare(self, text: str):
        from rdflib.plugins.sparql import prepareQuery

        return prepareQuery(PREFIX + text)

    def run(self, prepared, focus: str) -> int:
        from rdflib import URIRef

        return int(next(iter(self.graph.query(prepared, initBindings={"this": URIRef(focus)})))[0])

    def run_text(self, text: str, focus: str) -> int:
        from rdflib import URIRef

        return int(next(iter(self.graph.query(PREFIX + text, initBindings={"this": URIRef(focus)})))[0])


class OxigraphEngine:
    """Oxigraph 0.5 through `tools/testing/oxigraph` (ADR-A125): the focus node is substituted into the text."""

    name = "oxigraph"

    def __init__(self) -> None:
        sys.path.insert(0, str(HERE.parents[1] / "tools" / "testing" / "oxigraph" / "src"))
        from lattice_testing_oxigraph import OxigraphStore

        self.store = OxigraphStore()

    @staticmethod
    def version() -> str:
        import pyoxigraph

        return getattr(pyoxigraph, "__version__", "?")

    def load(self, triples: list[Triple]) -> None:
        import pyoxigraph as ox

        for s, p, kind, o in triples:
            if kind == "iri":
                term = ox.NamedNode(o)
            elif kind == "int":
                term = ox.Literal(o, datatype=ox.NamedNode("http://www.w3.org/2001/XMLSchema#integer"))
            elif kind == "en":
                term = ox.Literal(o, language="en")
            else:
                term = ox.Literal(o)
            self.store.add(ox.NamedNode(s), ox.NamedNode(p), term)

    def prepare(self, text: str):
        return PREFIX + text  # pyoxigraph parses on every call and has no prepared query

    def run(self, prepared, focus: str) -> int:
        import pyoxigraph as ox

        return int(self.store.select(prepared, {"this": ox.NamedNode(focus)})[0]["n"].value)

    run_text = None


class JenaEngine:
    """Apache Jena ARQ 5.1 in memory through `tools/testing/jena` (ADR-A125, MSC-5): the focus node is substituted into the text, as for
    Oxigraph. Each call crosses a pipe to the JVM, about 0.3 ms, which is added to every focus node. The JVM runs with its full compiler
    unless `LATTICE_SPARQL_TESTKIT_JVM_OPTIONS` is already set, since the kit's default stops at C1 for a fast start."""

    name = "jena"

    def __init__(self) -> None:
        sys.path.insert(0, str(HERE.parents[1] / "tools" / "testing" / "jena" / "src"))
        os.environ.setdefault("LATTICE_SPARQL_TESTKIT_JVM_OPTIONS", "-XX:+UseSerialGC -Xlog:disable")
        from lattice_testing_jena import JenaStore

        self.store = JenaStore()

    @staticmethod
    def version() -> str:
        return "5.1.0"  # ponytail: the package states no version, so this is the platform POM's Jena

    def load(self, triples: list[Triple]) -> None:
        from rdflib import Literal, URIRef

        self.store.add_all(
            (URIRef(s), URIRef(p), URIRef(o) if kind == "iri" else Literal(int(o)) if kind == "int" else Literal(o, lang="en") if kind == "en" else Literal(o))
            for s, p, kind, o in triples
        )

    def prepare(self, text: str):
        return PREFIX + text  # the text is parsed on every call

    def run(self, prepared, focus: str) -> int:
        from rdflib import URIRef

        return int(self.store.select(prepared, {"this": URIRef(focus)})[0]["n"])

    run_text = None


def available_engines() -> list[type]:
    engines = [RdflibEngine]
    try:
        import pyoxigraph  # noqa: F401

        engines.append(OxigraphEngine)
    except ImportError:
        pass
    try:
        sys.path.insert(0, str(HERE.parents[1] / "tools" / "testing" / "jena" / "src"))
        import lattice_testing_jena

        if lattice_testing_jena.available():
            engines.append(JenaEngine)
    except ImportError:  # an absent package is a skip, never a failure
        pass
    return engines


# ---- running ---------------------------------------------------------------------------------------------------------


def measure(engine, text: str, focus: list[str]) -> tuple[float, list[int]]:
    prepared = engine.prepare(text)
    counts = []
    start = time.perf_counter()
    for node in focus:
        counts.append(engine.run(prepared, node))
    return time.perf_counter() - start, counts


def run_experiment(experiment: Experiment, size: int, engine_class: type) -> tuple[Measurement, list[int]]:
    """Both forms on one engine at one size. A difference in their solutions is a wrong result."""
    triples, focus = experiment.build(size)
    engine = engine_class()
    engine.load(triples)
    naive_seconds, naive = measure(engine, experiment.naive, focus)
    improved_seconds, improved = measure(engine, experiment.improved, focus)
    if naive != improved:
        first = next(i for i, (a, b) in enumerate(zip(naive, improved)) if a != b)
        raise WrongResult(f"{experiment.key} at {size} on {engine.name}: the forms differ for {focus[first]}, {naive[first]} solutions against {improved[first]}")
    return Measurement(experiment.key, engine.name, size, len(focus), naive_seconds, improved_seconds), naive


def run_parse_cost(engine_classes: list[type]) -> dict[str, float]:
    """E5. Seconds per run of one query: from text each time and prepared on rdflib, from text on Oxigraph."""
    runs, seconds, answers = 100, {}, {}
    focus = f"{EX}f"
    for engine_class in engine_classes:
        engine = engine_class()
        engine.load(PARSE_DATA)
        if engine.run_text is not None:
            ways = [
                (f"{engine.name} from text", partial(engine.run_text, PARSE_QUERY, focus)),
                (f"{engine.name} prepared", partial(engine.run, engine.prepare(PARSE_QUERY), focus)),
            ]
        else:
            ways = [(f"{engine.name} from text", lambda: engine.run(engine.prepare(PARSE_QUERY), focus))]
        for way, call in ways:
            start = time.perf_counter()
            for _ in range(runs):
                answers[way] = call()
            seconds[way] = (time.perf_counter() - start) / runs
    if len(set(answers.values())) > 1:
        raise WrongResult(f"E5: the ways of running the query disagree: {answers}")
    return seconds


def run(quick: bool = False, engine_classes: list[type] | None = None) -> Report:
    engine_classes = engine_classes or available_engines()
    report = Report(run_record=run_record(engine_classes))
    for experiment in EXPERIMENTS:
        for size in experiment.sizes[:2] if quick else experiment.sizes:
            by_engine: dict[str, list[int]] = {}
            for engine_class in engine_classes:
                measurement, counts = run_experiment(experiment, size, engine_class)
                report.measurements.append(measurement)
                by_engine[measurement.engine] = counts
            distinct = {tuple(c) for c in by_engine.values()}
            if len(distinct) > 1:
                raise WrongResult(f"{experiment.key} at {size}: the engines disagree: {sorted(by_engine)}")
    report.parse = run_parse_cost(engine_classes)
    return report


def run_record(engine_classes: list[type]) -> str:
    """The date, the engines and their versions, Python, and the kind of machine, never the machine or person (ADR-A124)."""
    engines = ", ".join(f"{c.name} {c.version()}" for c in engine_classes)
    return f"{date.today().isoformat()}, {engines}, Python {platform.python_version()}, {platform.system()} {platform.machine()}, {os.cpu_count()} logical cores"


# ---- the report ------------------------------------------------------------------------------------------------------


def render(report: Report) -> str:
    lines = [f"Run: {report.run_record}", "", "Milliseconds per focus node. The ratio is the naive form over the improved form.", ""]
    engines = sorted({m.engine for m in report.measurements})
    for experiment in EXPERIMENTS:
        rows = [m for m in report.measurements if m.experiment == experiment.key]
        if not rows:
            continue
        lines += [f"## {experiment.key}. {experiment.title}", "", "| " + experiment.size_label + " | engine | naive | improved | ratio |", "|---|---|---|---|---|"]
        for m in rows:
            naive, improved = 1000 * m.naive_seconds / m.focus_nodes, 1000 * m.improved_seconds / m.focus_nodes
            lines.append(f"| {m.size} | {m.engine} | {naive:.3f} | {improved:.3f} | {naive / improved:.1f}x |")
        for engine in engines if experiment.fit_growth else []:
            exponents = [report.growth(experiment.key, engine, form) for form in ("naive", "improved")]
            if all(e is not None for e in exponents):
                lines.append(f"\nGrowth of the time per focus node with {experiment.size_label} on {engine}: naive k = {exponents[0]:.2f}, improved k = {exponents[1]:.2f}.")
        lines.append("")
    if report.parse:
        lines += ["## E5. Handing the engine a constraint query as text on every run", "", "| way of running it | milliseconds per run |", "|---|---|"]
        lines += [f"| {way} | {1000 * seconds:.3f} |" for way, seconds in report.parse.items()]
        lines.append("")
    return "\n".join(lines)


def write(report: Report, directory: Path = HERE) -> None:
    (directory / "report.json").write_text(json.dumps({"run": report.run_record, "measurements": [m.__dict__ for m in report.measurements], "parse": report.parse}, indent=2))
    (directory / "report.md").write_text(render(report))


def main() -> int:
    quick = os.environ.get("SPARQL_COST_QUICK") == "1"
    try:
        report = run(quick=quick)
    except WrongResult as failure:
        print(f"WRONG RESULT: {failure}", file=sys.stderr)
        return 1
    write(report)
    print(render(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
