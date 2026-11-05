# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""What a `GRAPH ?g` inside an `OPTIONAL` costs on rdflib and Oxigraph, and what that makes the generated named-graph replace cost (ADR-A124, TSD-04, TSD-42).

Two measurements.

**Forms.** `SELECT (COUNT(*) AS ?n) WHERE { BIND(<g> AS ?g) OPTIONAL { GRAPH ?g { ?s ?p ?o } } }` and its neighbours, over 100 graphs of 3,000 triples against 1
graph, the best of three, as a ratio. A ratio near 1 means the store passed the binding of `?g` into the graph pattern and read one graph. A ratio near 100 means it
read every graph. The forms vary how `?g` is bound (a constant `BIND`, a constant `VALUES`, an expression computed as the compiler computes it), and whether the
pattern is inside an `OPTIONAL` or in the enclosing group.

**Replace.** The generated `cas-replace-named-graph`, from `persistence.builders.build`, run with the default `graph_names="query"` (the compiler computes `?g` from `$root`) and
with `graph_names="caller"` (the caller passes `$g`), against a store that also holds ballast: aggregates of 100 triples each in other graphs. The cost of the default is
read against the size of the ballast.

**Pass criterion.** A wrong result fails the check. In the forms, the count is the triples of the one graph in every cell. In the replace, each run leaves exactly
the payload in the root's graph, every ballast graph untouched and the version row at the next sequence. **Time never fails it.** No budget exists before H5, and a
check that fails on time depends on the machine. The timings and the fitted slope go to `report.json` and `report.md` in this directory, which are generated and git-ignored.

`check.py --emit <file>` writes the forms and the rendered operations for a runtime other than Python (`benchmark/persistence-graph-naming-cost-jvm`). Run `mise run check:persistence-graph-naming-cost`. `GRAPH_NAMING_MAX` caps the ballast in quads (default 1,000,000, and rdflib stops at 100,000), `GRAPH_NAMING_QUICK=1`
runs the smallest sizes. The guards are off for every run, so both engines run the same query (Oxigraph cannot pass the guard's datatype test, probe P5)."""

from __future__ import annotations

import json
import os
import platform
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
PER_GRAPH = 100
BALLAST = (0, 10_000, 100_000, 1_000_000)
RDFLIB_MAX = 100_000
XSD_LONG = "http://www.w3.org/2001/XMLSchema#long"
PAT = "https://www.nebularis.org/neuro-semantic/lattice/persistence-store#"
ROOT = "urn:root:1"
LOG = "urn:g:txlog/"
COMPUTED_G = 'IRI(CONCAT("urn:g:", ENCODE_FOR_URI(STR("0")), ""))'
"""A graph name built by an expression, as the compiler builds the root's from `$root`."""

FORMS = {
    "constant BIND, OPTIONAL": "BIND(<urn:g:0> AS ?g) OPTIONAL { GRAPH ?g { ?s ?p ?o } }",
    "constant VALUES, OPTIONAL": "VALUES ?g { <urn:g:0> } OPTIONAL { GRAPH ?g { ?s ?p ?o } }",
    "constant BIND, one group": "BIND(<urn:g:0> AS ?g) GRAPH ?g { ?s ?p ?o }",
    "constant VALUES, one group": "VALUES ?g { <urn:g:0> } GRAPH ?g { ?s ?p ?o }",
    "computed BIND, OPTIONAL (the compiler's)": "BIND(" + COMPUTED_G + " AS ?g) OPTIONAL { GRAPH ?g { ?s ?p ?o } }",
    "computed BIND, one group": "BIND(" + COMPUTED_G + " AS ?g) GRAPH ?g { ?s ?p ?o }",
    "constant graph in the text": "GRAPH <urn:g:0> { ?s ?p ?o }",
    "nothing bound (reads every graph, for scale)": "GRAPH ?g { ?s ?p ?o }",
}
"""The `WHERE` of each form. The last reads every graph by definition and is the scale for the others."""


class WrongResult(AssertionError):
    """A run did not leave what it should. This is the one way the check fails."""


# ---- the engines ---------------------------------------------------------------------------------------------------------


class RdflibEngine:
    name = "rdflib"

    def __init__(self) -> None:
        import warnings

        from rdflib import Dataset

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            self.ds = Dataset()

    def add_graph(self, graph: str, triples) -> None:
        from rdflib import Literal, URIRef

        target = self.ds.graph(URIRef(graph))
        for s, p, o in triples:
            target.add((URIRef(s), URIRef(p), Literal(o)))

    def select_count(self, where: str) -> int:
        rows = list(self.ds.query("SELECT (COUNT(*) AS ?n) WHERE { " + where + " }"))
        return int(rows[0][0])

    def update(self, text: str, parameters: dict) -> None:
        from rdflib import Literal, URIRef

        terms = {k: URIRef(v) if kind == "iri" else Literal(v, datatype=URIRef(XSD_LONG)) if kind == "long" else Literal(v) for k, (kind, v) in parameters.items()}
        self.ds.update(text, initBindings=terms)

    def triples(self, graph: str) -> set:
        from rdflib import URIRef

        return {(str(s), str(p), str(o)) for s, p, o in self.ds.graph(URIRef(graph))}

    def quad_count(self, prefix: str) -> int:
        return sum(len(g) for g in self.ds.graphs() if str(g.identifier).startswith(prefix))


class OxigraphEngine:
    name = "oxigraph"

    def __init__(self) -> None:
        import pyoxigraph
        from lattice_testing_oxigraph import OxigraphStore

        self.ox = pyoxigraph
        self.store = OxigraphStore()

    def add_graph(self, graph: str, triples) -> None:
        ox = self.ox
        self.store.store.bulk_extend(ox.Quad(ox.NamedNode(s), ox.NamedNode(p), ox.Literal(o), ox.NamedNode(graph)) for s, p, o in triples)

    def select_count(self, where: str) -> int:
        rows = list(self.store.store.query("SELECT (COUNT(*) AS ?n) WHERE { " + where + " }"))
        return int(rows[0]["n"].value)

    def update(self, text: str, parameters: dict) -> None:
        ox = self.ox
        terms = {k: ox.NamedNode(v) if kind == "iri" else ox.Literal(v, datatype=ox.NamedNode(XSD_LONG)) if kind == "long" else ox.Literal(v) for k, (kind, v) in parameters.items()}
        self.store.update(text, terms, strict=False)

    def triples(self, graph: str) -> set:
        ox = self.ox
        return {(q.subject.value, q.predicate.value, q.object.value) for q in self.store.store.quads_for_pattern(None, None, None, ox.NamedNode(graph))}

    def quad_count(self, prefix: str) -> int:
        return sum(1 for q in self.store.store if isinstance(q.graph_name, self.ox.NamedNode) and q.graph_name.value.startswith(prefix))


def available_engines() -> list:
    engines = [RdflibEngine]
    try:
        import lattice_testing_oxigraph  # noqa: F401
    except ImportError:
        return engines
    return [OxigraphEngine, *engines]


# ---- the forms -----------------------------------------------------------------------------------------------------------


def _loaded(engine_class, graphs: int, triples: int):
    engine = engine_class()
    for i in range(graphs):
        engine.add_graph(f"urn:g:{i}", ((f"urn:s{j}", "urn:p", str(j)) for j in range(triples)))
    return engine


def form_ratio(engine_class, where: str, *, graphs: int = 100, triples: int = 3000) -> tuple[float, int]:
    """(the ratio of the best of three timings over `graphs` graphs to that over 1 graph, the count of the larger store). Raises WrongResult if the count of the
    one-graph store is not its triples. The form that reads every graph returns every triple of the larger store by definition, so it is checked against that."""
    reads_all = where == "GRAPH ?g { ?s ?p ?o }"
    best = {}
    count = 0
    for n in (graphs, 1):
        engine = _loaded(engine_class, n, triples)
        times = []
        for _ in range(3):
            start = time.perf_counter()
            count = engine.select_count(where)
            times.append(time.perf_counter() - start)
        expected = triples * (n if reads_all else 1)
        if count != expected:
            raise WrongResult(f"{engine_class.name}: {where!r} counted {count} over {n} graph(s), not {expected}")
        best[n] = min(times)
    return best[graphs] / best[1], count


# ---- the replace ---------------------------------------------------------------------------------------------------------


def operations() -> dict:
    """The rendered create and replace, for each way of naming the graph, with the payload slot still in the text."""
    from persistence.builders import build
    from persistence.ir_render import render
    from persistence.terms import Iri, Literal

    context = {
        "metaGraphPrefix": Iri.encode("urn:g:meta"), "txnGraph": Iri.encode("urn:g:txn"), "logGraphPrefix": Iri.encode(LOG),
        "graphPrefix": Literal.encode("urn:g:orders/"), "graphSuffix": Literal.encode(""),
        "eventGraphPrefix": Iri.encode("urn:g:events/order/"), "datasetGraph": Iri.encode("urn:g:dataset"), "datasetNode": Iri.encode("urn:g:dataset-node"),
    }
    out = {"create": render(build("create-if-absent-named-graph", context, guards=False))}
    for names in ("query", "caller"):
        out[names] = render(build("cas-replace-named-graph", context, guards=False, graph_names=names))
    return out


def root_graph() -> str:
    import urllib.parse

    return "urn:g:orders/" + urllib.parse.quote(ROOT, safe="-_.~")


def _row(payload: str) -> str:
    return f'<{ROOT}> <urn:p> "{payload}" .'


def run_replace(engine_class, names: str, ballast_quads: int, ops: dict, *, repeats: int = 3) -> float:
    """Create the root, add `ballast_quads` quads in other graphs, replace the root's payload `repeats` times and return the best time. Raises WrongResult."""
    engine = engine_class()
    graphs = ballast_quads // PER_GRAPH
    for g in range(graphs):
        engine.add_graph(f"urn:g:ballast/{g}", ((f"urn:s{g}:{j}", "urn:p", str(j)) for j in range(PER_GRAPH)))
    slot = "{{{payloadTriples}}}"
    parameters = {"root": ("iri", ROOT), "epoch": ("long", "3"), "newRev": ("iri", f"urn:rev:{ROOT}/1"), "txnId": ("iri", "urn:txn:create"), "requestDigest": ("str", "cd" * 32)}
    engine.update(ops["create"].replace(slot, _row("v1")), parameters)
    best = float("inf")
    for expected in range(1, repeats + 1):
        parameters = {
            "root": ("iri", ROOT), "epoch": ("long", "3"), "expectedSeq": ("long", str(expected)), "nextSeq": ("long", str(expected + 1)),
            "newRev": ("iri", f"urn:rev:{ROOT}/{expected + 1}"), "txnId": ("iri", f"urn:txn:replace{expected}"), "requestDigest": ("str", "ef" * 32),
        }
        if names == "caller":
            parameters["g"] = ("iri", root_graph())
        start = time.perf_counter()
        engine.update(ops[names].replace(slot, _row(f"v{expected + 1}")), parameters)
        best = min(best, time.perf_counter() - start)
        if engine.triples(root_graph()) != {(ROOT, "urn:p", f"v{expected + 1}")}:
            raise WrongResult(f"{engine_class.name}/{names}: the root's graph is {sorted(engine.triples(root_graph()))} after replace {expected}")
        if engine.quad_count("urn:g:ballast/") != graphs * PER_GRAPH:
            raise WrongResult(f"{engine_class.name}/{names}: the ballast changed")
        if (ROOT, PAT + "seq", str(expected + 1)) not in engine.triples("urn:g:meta"):
            raise WrongResult(f"{engine_class.name}/{names}: the version row is not at sequence {expected + 1}")
    return best


# ---- the operations for another runtime ---------------------------------------------------------------------------------


def substitute(text: str, parameters: dict) -> str:
    """The operation with each `$name` replaced by its term as N-Triples, which is how a runtime with no initial bindings for updates runs it (TSD-12)."""
    for name, (kind, value) in sorted(parameters.items(), key=lambda item: -len(item[0])):
        term = f"<{value}>" if kind == "iri" else f'"{value}"^^<{XSD_LONG}>' if kind == "long" else f'"{value}"'
        text = text.replace("$" + name, term)
    return text


def replace_parameters(expected: int, names: str) -> dict:
    parameters = {
        "root": ("iri", ROOT), "epoch": ("long", "3"), "expectedSeq": ("long", str(expected)), "nextSeq": ("long", str(expected + 1)),
        "newRev": ("iri", f"urn:rev:{ROOT}/{expected + 1}"), "txnId": ("iri", f"urn:txn:replace{expected}"), "requestDigest": ("str", "ef" * 32),
    }
    if names == "caller":
        parameters["g"] = ("iri", root_graph())
    return parameters


def count_query(pattern: str) -> str:
    """A `COUNT(*)` over `pattern`, which must bind a variable. RDF4J 6.1.0 counts 0 for a pattern with no variable that matches (TSD-48)."""
    return "SELECT (COUNT(*) AS ?n) WHERE { " + pattern + " }"


def emit_operations(repeats: int = 3) -> dict:
    """Everything a runtime other than Python needs to repeat this benchmark on its own store: the forms, the ballast sizes, the create and the replaces with
    their parameters substituted into the text, and the checks that say each replace did what it should. The runtime asserts the checks and never judges time."""
    ops = operations()
    slot = "{{{payloadTriples}}}"
    steps = {}
    for names in ("query", "caller"):
        create = substitute(ops["create"].replace(slot, _row("v1")), {"root": ("iri", ROOT), "epoch": ("long", "3"), "newRev": ("iri", f"urn:rev:{ROOT}/1"), "txnId": ("iri", "urn:txn:create"), "requestDigest": ("str", "cd" * 32)})
        replaces = []
        for expected in range(1, repeats + 1):
            text = substitute(ops[names].replace(slot, _row(f"v{expected + 1}")), replace_parameters(expected, names))
            checks = [
                {"query": count_query(f"GRAPH <{root_graph()}> {{ ?s ?p ?o }}"), "expect": 1},
                {"query": count_query(f'GRAPH <{root_graph()}> {{ <{ROOT}> <urn:p> ?o FILTER(STR(?o) = "v{expected + 1}") }}'), "expect": 1},
                {"query": count_query(f'GRAPH <urn:g:meta> {{ <{ROOT}> <{PAT}seq> ?q FILTER(STR(?q) = "{expected + 1}") }}'), "expect": 1},
            ]
            replaces.append({"text": text, "checks": checks})
        steps[names] = {"create": create, "replaces": replaces}
    return {
        "forms": {name: count_query(where) for name, where in FORMS.items() if where != "GRAPH ?g { ?s ?p ?o }"},
        "readsEveryGraph": count_query("GRAPH ?g { ?s ?p ?o }"),
        "formGraphs": 100, "formTriples": 3000, "perGraph": PER_GRAPH, "ballast": [b for b in BALLAST], "rootGraph": root_graph(),
        "ballastQuery": count_query('GRAPH ?g { ?s ?p ?o } FILTER(STRSTARTS(STR(?g), "urn:g:ballast/"))'),
        "steps": steps,
    }


# ---- the report ----------------------------------------------------------------------------------------------------------


@dataclass
class Report:
    forms: list = field(default_factory=list)  # (engine, form, ratio)
    replaces: list = field(default_factory=list)  # (engine, names, ballast_quads, seconds)

    def slope_ms_per_1000_quads(self, engine: str, names: str) -> float | None:
        """Least squares through the replace timings of the largest ballast and the smallest, in ms per 1,000 quads."""
        points = sorted((q, s) for e, n, q, s in self.replaces if e == engine and n == names)
        if len(points) < 2 or points[-1][0] == points[0][0]:
            return None
        return (points[-1][1] - points[0][1]) * 1000 / ((points[-1][0] - points[0][0]) / 1000)


def environment() -> dict:
    versions = {}
    for module in ("rdflib", "pyoxigraph"):
        try:
            versions[module] = __import__(module).__version__
        except ImportError:
            pass
    return {"python": platform.python_version(), "machine": platform.machine(), "system": platform.system(), **versions}


def measure(maximum: int, quick: bool) -> Report:
    report = Report()
    ops = operations()
    for engine_class in available_engines():
        shapes = {"graphs": 10, "triples": 300} if quick else {}
        for form, where in FORMS.items():
            ratio, _ = form_ratio(engine_class, where, **shapes)
            report.forms.append((engine_class.name, form, ratio))
        for ballast in BALLAST:
            if ballast > maximum or (engine_class is RdflibEngine and ballast > RDFLIB_MAX) or (quick and ballast > 10_000):
                continue
            for names in ("query", "caller"):
                report.replaces.append((engine_class.name, names, ballast, run_replace(engine_class, names, ballast, ops)))
    return report


def write_report(report: Report, directory: Path = HERE) -> None:
    env = environment()
    (directory / "report.json").write_text(json.dumps({"environment": env, "forms": report.forms, "replaces": report.replaces}, indent=2), encoding="utf-8", newline="\n")
    lines = [f"Run {time.strftime('%Y-%m-%d')}: " + ", ".join(f"{k} {v}" for k, v in env.items()), "", "## Forms, ratio of 100 graphs to 1", "", "| Engine | Form | Ratio |", "|---|---|---|"]
    lines += [f"| {e} | {f} | {r:.1f} |" for e, f, r in report.forms]
    lines += ["", "## Generated replace, best of three", "", "| Engine | Graph naming | Ballast quads | ms |", "|---|---|---|---|"]
    lines += [f"| {e} | {n} | {q:,} | {s * 1000:.1f} |" for e, n, q, s in report.replaces]
    lines += ["", "## Slope, ms per 1,000 quads of ballast", "", "| Engine | Graph naming | ms per 1,000 quads |", "|---|---|---|"]
    for e, n in sorted({(e, n) for e, n, _, _ in report.replaces}):
        slope = report.slope_ms_per_1000_quads(e, n)
        lines.append(f"| {e} | {n} | {'' if slope is None else f'{slope:.3f}'} |")
    (directory / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "--emit":
        Path(sys.argv[2]).write_text(json.dumps(emit_operations(), indent=2), encoding="utf-8", newline="\n")
        print(f"wrote {sys.argv[2]}")
        return 0
    maximum = int(os.environ.get("GRAPH_NAMING_MAX", "1000000"))
    quick = os.environ.get("GRAPH_NAMING_QUICK") == "1"
    try:
        report = measure(maximum, quick)
    except WrongResult as error:
        print(f"WRONG RESULT: {error}", file=sys.stderr)
        return 1
    write_report(report)
    print((HERE / "report.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
