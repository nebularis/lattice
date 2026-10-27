# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""What a graph variable bound outside an `OPTIONAL` costs, per engine and engine version (ADR-A124, TSD-04, TSD-42, TSD-Q22).

The named-graph replace's sweep reads one root's graph, with the graph IRI bound outside a left join. Whether an engine passes that
binding into the `GRAPH ?g` pattern decides if the sweep reads one graph or all of them. Four forms count the triples of one graph.

| Form | Query |
|---|---|
| bind-optional | `BIND(<g> AS ?g) OPTIONAL { GRAPH ?g { ?s ?p ?o } }` |
| values-optional | `VALUES ?g { <g> } OPTIONAL { GRAPH ?g { ?s ?p ?o } }` |
| join | `BIND(<g> AS ?g) GRAPH ?g { ?s ?p ?o }` |
| constant | `GRAPH <g> { ?s ?p ?o }` |

Each runs against a store of one graph and a store of 100 graphs of the same size (3,000 triples), best of five. The **ratio** is the
time over 100 graphs divided by the time over one. About 1 means the engine reads one graph. About 100 means it reads every graph.

**Pass criterion.** Every form returns the triple count of the graph, on every engine and size. A wrong count fails the check.
**Time never fails it.** The ratios go to `report.md` and `report.json` here, which are generated and git-ignored.

Engines: rdflib and Oxigraph, plus Jena when `tools/testing/jena` is importable and `available()`. TSD-40's path forms are not here,
since they need the ledger store.

Run `mise run check:persistence-store-probes`. `STORE_PROBES_QUICK=1` uses 20 graphs of 500 triples."""

from __future__ import annotations

import json
import os
import platform
import sys
import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))  # ponytail: the reader is found by its place in the tree, since it is what finds the root
import lattice_repo_catalogue as catalogue  # noqa: E402

CATALOGUE = catalogue.load(catalogue.root_above(HERE))

TRIPLES, GRAPHS, BEST_OF = 3000, 100, 5
QUICK = (500, 20)
GRAPH = "urn:g:0"
COUNT = "SELECT (COUNT(*) AS ?n) WHERE { "
FORMS = {
    "bind-optional": COUNT + f"BIND(<{GRAPH}> AS ?g) OPTIONAL {{ GRAPH ?g {{ ?s ?p ?o }} }} }}",
    "values-optional": COUNT + f"VALUES ?g {{ <{GRAPH}> }} OPTIONAL {{ GRAPH ?g {{ ?s ?p ?o }} }} }}",
    "join": COUNT + f"BIND(<{GRAPH}> AS ?g) GRAPH ?g {{ ?s ?p ?o }} }}",
    "constant": COUNT + f"GRAPH <{GRAPH}> {{ ?s ?p ?o }} }}",
}


class WrongResult(AssertionError):
    """A count that is not the triples of the graph. The one way the check fails."""


@dataclass
class Measurement:
    engine: str
    version: str
    form: str
    one_seconds: float
    many_seconds: float

    @property
    def ratio(self) -> float:
        return self.many_seconds / self.one_seconds


@dataclass
class Report:
    run_record: str
    measurements: list[Measurement] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


# ---- the engines: a store of `graphs` graphs of `triples` triples, and a count of a query ----------------------------------


class RdflibEngine:
    name = "rdflib"

    @staticmethod
    def version() -> str:
        import rdflib

        return rdflib.__version__

    def __init__(self, graphs: int, triples: int) -> None:
        import warnings

        from rdflib import Dataset, Literal, URIRef

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            self.ds = Dataset()
        for i in range(graphs):
            g = self.ds.graph(URIRef(f"urn:g:{i}"))
            for j in range(triples):
                g.add((URIRef(f"urn:s{j}"), URIRef("urn:p"), Literal(j)))

    def count(self, query: str) -> int:
        return int(next(iter(self.ds.query(query)))[0])


class OxigraphEngine:
    name = "oxigraph"

    @staticmethod
    def version() -> str:
        import pyoxigraph

        return pyoxigraph.__version__

    def __init__(self, graphs: int, triples: int) -> None:
        import pyoxigraph as ox

        self.store = ox.Store()
        p = ox.NamedNode("urn:p")
        self.store.extend(
            ox.Quad(ox.NamedNode(f"urn:s{j}"), p, ox.Literal(str(j), datatype=ox.NamedNode("http://www.w3.org/2001/XMLSchema#integer")), ox.NamedNode(f"urn:g:{i}"))
            for i in range(graphs)
            for j in range(triples)
        )

    def count(self, query: str) -> int:
        return int(next(iter(self.store.query(query)))["n"].value)


class JenaEngine:
    """Jena through `tools/testing/jena` (MSC-1), loaded and queried with the SPARQL its `JenaStore` runs. Not yet exercised here, since the
    package is built in a parallel slice. Whoever lands it runs this benchmark once and corrects the two calls below if its names differ."""

    name = "jena"

    @staticmethod
    def version() -> str:
        import lattice_testing_jena as jena

        return getattr(jena, "VERSION", "5.1.0")

    def __init__(self, graphs: int, triples: int) -> None:
        import lattice_testing_jena as jena

        self.store = jena.JenaStore()
        for i in range(graphs):
            for start in range(0, triples, 1000):
                rows = " ".join(f'<urn:s{j}> <urn:p> {j} .' for j in range(start, min(start + 1000, triples)))
                self.store.update(f"INSERT DATA {{ GRAPH <urn:g:{i}> {{ {rows} }} }}")

    def count(self, query: str) -> int:
        return int(self.store.select(query)[0]["n"].value)


def available_engines(notes: list[str] | None = None) -> list[type]:
    engines: list[type] = [RdflibEngine]
    try:
        import pyoxigraph  # noqa: F401

        engines.append(OxigraphEngine)
    except ImportError:
        pass
    try:
        sys.path.insert(0, str(catalogue_jena_src()))
        import lattice_testing_jena as jena

        if jena.available():
            engines.append(JenaEngine)
        elif notes is not None:
            notes.append("jena skipped, lattice_testing_jena.available() is false")
    except Exception as error:  # an absent or half-built package is a skip, never a failure
        if notes is not None:
            notes.append(f"jena skipped, {type(error).__name__}")
    return engines


def catalogue_jena_src() -> Path:
    return CATALOGUE.root / CATALOGUE.area("tools") / "testing" / "jena" / "src"


# ---- running ---------------------------------------------------------------------------------------------------------------


def best(engine, query: str, expected: int) -> float:
    fastest = float("inf")
    for _ in range(BEST_OF):
        start = time.perf_counter()
        got = engine.count(query)
        fastest = min(fastest, time.perf_counter() - start)
        if got != expected:
            raise WrongResult(f"{engine.name}: the query returned {got}, and the graph holds {expected}: {query}")
    return fastest


def run(quick: bool = False, engine_classes: list[type] | None = None, forms: dict[str, str] | None = None) -> Report:
    notes: list[str] = []
    engine_classes = engine_classes or available_engines(notes)
    triples, graphs = QUICK if quick else (TRIPLES, GRAPHS)
    versions = ", ".join(f"{c.name} {c.version()}" for c in engine_classes)
    record = f"{date.today().isoformat()}, {versions}, {graphs} graphs of {triples} triples, Python {platform.python_version()}, {platform.system()} {platform.machine()}, {os.cpu_count()} logical cores"
    report = Report(run_record=record, notes=notes)
    for cls in engine_classes:
        one, many = cls(1, triples), cls(graphs, triples)
        for form, query in (forms or FORMS).items():
            report.measurements.append(Measurement(cls.name, cls.version(), form, best(one, query, triples), best(many, query, triples)))
    return report


def render(report: Report) -> str:
    lines = [f"Run: {report.run_record}", "", "The ratio is the time over many graphs divided by the time over one. About 1 reads one graph.", ""]
    engines = sorted({(m.engine, m.version) for m in report.measurements})
    lines += ["| Form | " + " | ".join(f"{e} {v}" for e, v in engines) + " |", "|---|" + "---|" * len(engines)]
    for form in FORMS:
        cells = []
        for e, v in engines:
            m = next((m for m in report.measurements if (m.engine, m.version, m.form) == (e, v, form)), None)
            cells.append("" if m is None else f"{m.ratio:.1f} ({1000 * m.one_seconds:.1f} ms to {1000 * m.many_seconds:.1f} ms)")
        lines.append(f"| {form} | " + " | ".join(cells) + " |")
    return "\n".join(lines + [""] + [f"Note: {n}" for n in report.notes])


def write(report: Report, directory: Path = HERE) -> None:
    (directory / "report.json").write_text(json.dumps({"run": report.run_record, "notes": report.notes, "measurements": [{**m.__dict__, "ratio": m.ratio} for m in report.measurements]}, indent=2))
    (directory / "report.md").write_text(render(report))


def main() -> int:
    try:
        report = run(quick=os.environ.get("STORE_PROBES_QUICK") == "1")
    except WrongResult as failure:
        print(f"WRONG RESULT: {failure}", file=sys.stderr)
        return 1
    write(report)
    print(render(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
