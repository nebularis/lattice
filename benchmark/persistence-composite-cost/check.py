# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The cost of a composite replace as shipped (R0), on rdflib and Oxigraph (ADR-A124, technical debt TD-42).

The replace sweeps the root and every member of an aggregate (M stored triples) and writes the payload (N triples). Its
`INSERT` template holds the payload and is filled once per sweep solution, so a store builds M x N triples before the
union removes the copies. This check runs it with M = N from 10 to 10,000, on each engine that is installed.

**Pass criterion.** At every size, on every engine, the replace leaves exactly the payload where the aggregate was, the
bystander aggregate and the references untouched, the version row at the next sequence with the new head, and one receipt.
A wrong result fails the check. **Time never fails it, and neither does memory.** No budget exists before H5, and a check that fails on time depends
on the machine. Each run is a child process under a memory cap (`COMPOSITE_COST_MEMORY_GB`, default 8). A run that does not finish, because it needs more
memory than that, is recorded as "did not finish" with the exit status, and is not a wrong result. The timings, those records and the
fitted growth of each engine go to `report.json` and `report.md` in this directory, which are generated and git-ignored.

Run `mise run check:persistence-composite-cost`. `COMPOSITE_COST_MAX` caps the size (default 10000), for a quick run.
The guards are off for every run, so both engines run the same query (Oxigraph cannot pass the guard's datatype test, probe P5)."""

from __future__ import annotations

import json
import math
import os
import platform
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIZES = (10, 100, 1000, 3000, 10000)
MEMORY_GB = 8  # the cap of one run, so that a run that needs more is recorded and does not take the machine down
EX = "https://example.org/projects#"
PAT = "https://example.org/lattice/patterns#"
XSD_LONG = "http://www.w3.org/2001/XMLSchema#long"
ROOT = EX + "p1"
BYSTANDER = EX + "p2"
DATA_GRAPH_KEY = "dataGraph"


class WrongResult(AssertionError):
    """The replace did not leave what it should. This is the one way the check fails."""


@dataclass
class Measurement:
    engine: str
    size: int
    stored_triples: int
    payload_triples: int
    seconds: float | None
    repeats: int
    outcome: str = "ok"  # or "did not finish: ..." when a run exceeded the memory cap or died


@dataclass
class Report:
    measurements: list[Measurement] = field(default_factory=list)

    def growth(self, engine: str) -> float | None:
        """The exponent k in time ~ size^k, fitted by least squares on log-log over the sizes of 100 and above."""
        points = [(math.log(m.size), math.log(m.seconds)) for m in self.measurements if m.engine == engine and m.size >= 100 and m.seconds and m.seconds > 0]
        if len(points) < 2:
            return None
        n = len(points)
        mean_x = sum(x for x, _ in points) / n
        mean_y = sum(y for _, y in points) / n
        denominator = sum((x - mean_x) ** 2 for x, _ in points)
        return sum((x - mean_x) * (y - mean_y) for x, y in points) / denominator if denominator else None


# ---- the aggregate ---------------------------------------------------------------------------------------------------


def stored_data(size: int) -> list[tuple[str, str, str, str]]:
    """About ``size`` triples in the aggregate of p1, as (subject, predicate, kind, object) where kind is `iri` or `str`.
    The root has a name and K milestones, and each milestone a type and a due date, so M = 3K + 2."""
    k = max((size - 2) // 3, 1)
    rdf_type = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
    triples = [(ROOT, rdf_type, "iri", EX + "Project"), (ROOT, EX + "name", "str", "Apollo")]
    for i in range(k):
        milestone = f"{EX}m{i}"
        triples += [(ROOT, EX + "hasMilestone", "iri", milestone), (milestone, rdf_type, "iri", EX + "Milestone"), (milestone, EX + "due", "str", f"2026-{i}")]
    return triples


def bystanders() -> list[tuple[str, str, str, str]]:
    """What a replace of p1 must leave alone: a second aggregate and a reference outside both."""
    return [
        (BYSTANDER, EX + "name", "str", "Gemini"), (BYSTANDER, EX + "hasMilestone", "iri", EX + "m-other"),
        (EX + "m-other", EX + "due", "str", "2027-01-01"), (EX + "acme", EX + "name", "str", "Acme"),
    ]


def payload(size: int) -> list[tuple[str, str, str, str]]:
    return [(ROOT, EX + "tag", "str", f"t{j}") for j in range(size)]


def nt(triples) -> str:
    def term(kind: str, value: str) -> str:
        return f"<{value}>" if kind == "iri" else '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'

    return "".join(f"<{s}> <{p}> {term(kind, o)} . " for s, p, kind, o in triples)


# ---- the engines -----------------------------------------------------------------------------------------------------


class RdflibEngine:
    name = "rdflib"

    def __init__(self) -> None:
        import warnings

        from rdflib import Dataset

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            self.ds = Dataset()

    def add(self, graph: str, triples, longs=()):
        from rdflib import Literal, URIRef

        target = self.ds.graph(URIRef(graph))
        for s, p, kind, o in triples:
            target.add((URIRef(s), URIRef(p), URIRef(o) if kind == "iri" else Literal(o)))

    def add_long(self, graph: str, subject: str, predicate: str, value: int):
        from rdflib import Literal, URIRef

        self.ds.graph(URIRef(graph)).add((URIRef(subject), URIRef(predicate), Literal(value, datatype=URIRef(XSD_LONG))))

    def update(self, text: str, parameters: dict[str, tuple[str, str]]):
        import warnings

        from rdflib import Literal, URIRef

        terms = {k: (URIRef(v) if kind == "iri" else Literal(v, datatype=URIRef(XSD_LONG)) if kind == "long" else Literal(v)) for k, (kind, v) in parameters.items()}
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            self.ds.update(text, initBindings=terms)

    def graph_triples(self, graph: str) -> set[tuple[str, str, str]]:
        from rdflib import URIRef

        return {(str(s), str(p), str(o)) for s, p, o in self.ds.graph(URIRef(graph))}


class OxigraphEngine:
    name = "oxigraph"

    def __init__(self) -> None:
        from lattice_testing_oxigraph import OxigraphStore

        self.store = OxigraphStore()

    def add(self, graph: str, triples, longs=()):
        import pyoxigraph as ox

        g = ox.NamedNode(graph)
        for s, p, kind, o in triples:
            self.store.add(ox.NamedNode(s), ox.NamedNode(p), ox.NamedNode(o) if kind == "iri" else ox.Literal(o), g)

    def add_long(self, graph: str, subject: str, predicate: str, value: int):
        import pyoxigraph as ox

        # Oxigraph keeps an integer-derived literal as xsd:integer (probe P5), so this is what its own update would store too
        self.store.add(ox.NamedNode(subject), ox.NamedNode(predicate), ox.Literal(str(value), datatype=ox.NamedNode(XSD_LONG)), ox.NamedNode(graph))

    def update(self, text: str, parameters: dict[str, tuple[str, str]]):
        import pyoxigraph as ox

        terms = {k: (ox.NamedNode(v) if kind == "iri" else ox.Literal(v, datatype=ox.NamedNode(XSD_LONG)) if kind == "long" else ox.Literal(v)) for k, (kind, v) in parameters.items()}
        self.store.update(text, terms, strict=False)

    def graph_triples(self, graph: str) -> set[tuple[str, str, str]]:
        import pyoxigraph as ox

        return {(q.subject.value, q.predicate.value, q.object.value) for q in self.store.quads(ox.NamedNode(graph))}


def available_engines() -> list[type]:
    engines = [RdflibEngine]
    try:
        import lattice_testing_oxigraph  # noqa: F401
    except ImportError:
        return engines
    return [*engines, OxigraphEngine]


# ---- the operation -----------------------------------------------------------------------------------------------------


def replace_operation() -> tuple[str, dict[str, str]]:
    """The composite replace as `instantiate` writes it with the guards off, and the names of its graphs."""
    from rdflib import Graph

    from persistence import witness
    from persistence.compiler import compile_to_graph
    from persistence.instantiate import instantiate_by_target
    from persistence.namespaces import DAL

    example = Path(witness.EXAMPLES_DIR) / "composite-project-ownership.ttl"
    compiled, _ = compile_to_graph(witness._load_fixture(example), guards=False)
    (by_target,) = instantiate_by_target(compiled).values()
    text = by_target["cas-replace"]
    import re

    graphs = {
        "data": re.search(r"GRAPH <(urn:g:projects)>", text).group(1),
        "meta": re.search(r"GRAPH <(urn:g:meta/\d+)>", text).group(1),
    }
    return text, graphs


def run_once(engine_class, size: int, text: str, graphs: dict[str, str]) -> tuple[float, int]:
    engine = engine_class()
    stored = stored_data(size)
    engine.add(graphs["data"], [*stored, *bystanders()])
    engine.add_long(graphs["meta"], ROOT, PAT + "epoch", 1)
    engine.add_long(graphs["meta"], ROOT, PAT + "seq", 1)
    new_payload = payload(size)
    parameters = {
        "root": ("iri", ROOT), "epoch": ("long", "1"), "expectedSeq": ("long", "1"), "nextSeq": ("long", "2"),
        "newRev": ("iri", "urn:rev:2"), "txnId": ("iri", "urn:txn:a"), "requestDigest": ("str", "d"),
    }
    start = time.perf_counter()
    engine.update(text.replace("{{{payloadTriples}}}", nt(new_payload)), parameters)
    elapsed = time.perf_counter() - start
    verify(engine, graphs, new_payload, len(stored))
    return elapsed, len(stored)


def verify(engine, graphs: dict[str, str], new_payload, stored_count: int) -> None:
    """The pass criterion. Raises WrongResult."""
    data = engine.graph_triples(graphs["data"])
    expected_payload = {(s, p, o) for s, p, _, o in new_payload}
    expected_kept = {(s, p, o) for s, p, _, o in bystanders()}
    if data != expected_payload | expected_kept:
        extra = sorted(data - expected_payload - expected_kept)[:3]
        missing = sorted((expected_payload | expected_kept) - data)[:3]
        raise WrongResult(f"{engine.name}: the data graph holds {len(data)} triples, expected {len(expected_payload | expected_kept)}. Extra {extra}, missing {missing}")
    meta = engine.graph_triples(graphs["meta"])
    seqs = {o for s, p, o in meta if s == ROOT and p == PAT + "seq"}
    heads = {o for s, p, o in meta if s == ROOT and p == PAT + "head"}
    if seqs != {"2"} or heads != {"urn:rev:2"}:
        raise WrongResult(f"{engine.name}: the version row has seq {sorted(seqs)} and head {sorted(heads)}, expected 2 and urn:rev:2")


def _child(engine_name: str, size: int, text: str, graphs: dict[str, str], memory_bytes: int, queue) -> None:
    """One run in its own process, under a memory cap. Puts ("ok", seconds, stored) or ("wrong", message) on the queue."""
    import resource

    resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
    engine_class = next(c for c in (RdflibEngine, OxigraphEngine) if c.name == engine_name)
    try:
        run_once(engine_class, 10, text, graphs)  # a warm-up, so the first parse of the query is not in the timing
        seconds, stored = run_once(engine_class, size, text, graphs)
        queue.put(("ok", seconds, stored))
    except WrongResult as error:
        queue.put(("wrong", str(error)))
    except MemoryError:
        queue.put(("dnf", "out of memory"))


def run_isolated(engine_class, size: int, text: str, graphs: dict[str, str], memory_gb: float) -> tuple[str, object, object]:
    """As :func:`run_once`, in a child process capped at ``memory_gb``. Returns ("ok", seconds, stored), ("wrong", message, None)
    or ("dnf", reason, None). A child that dies without a result, as a Rust allocation failure does, is a "dnf" with its status."""
    import multiprocessing

    context = multiprocessing.get_context("spawn")
    queue = context.Queue()
    process = context.Process(target=_child, args=(engine_class.name, size, text, graphs, int(memory_gb * 2**30), queue))
    process.start()
    outcome = None
    while process.is_alive() or not queue.empty():
        try:
            outcome = queue.get(timeout=1)
            break
        except Exception:
            continue
    process.join()
    if outcome is None:
        return "dnf", f"the process ended with status {process.exitcode} and no result (the cap is {memory_gb} GB)", None
    kind = outcome[0]
    if kind == "ok":
        return "ok", outcome[1], outcome[2]
    return kind, outcome[1], None


def run(max_size: int = SIZES[-1], engine_classes=None, isolated: bool = False, memory_gb: float = MEMORY_GB) -> Report:
    text, graphs = replace_operation()
    report = Report()
    for engine_class in engine_classes or available_engines():
        for size in SIZES:
            if size > max_size:
                continue
            repeats = 3 if size <= 100 else 1
            runs = []
            for _ in range(repeats):
                if isolated:
                    kind, seconds, stored = run_isolated(engine_class, size, text, graphs, memory_gb)
                    if kind == "wrong":
                        raise WrongResult(str(seconds))
                    if kind == "dnf":
                        runs = []
                        report.measurements.append(Measurement(engine_class.name, size, 0, size, None, 1, f"did not finish: {seconds}"))
                        print(f"{engine_class.name:9} size {size:6}  did not finish: {seconds}", flush=True)
                        break
                    runs.append((seconds, stored))
                else:
                    runs.append(run_once(engine_class, size, text, graphs))
            if not runs:
                continue
            seconds = min(t for t, _ in runs)
            report.measurements.append(Measurement(engine_class.name, size, runs[0][1], size, seconds, repeats))
            print(f"{engine_class.name:9} size {size:6}  M {runs[0][1]:6}  {seconds:10.4f} s", flush=True)
    return report


def environment() -> dict[str, str]:
    """The run, stated as ADR-A124 decision 5 asks: the date, the engines and their versions, Python and the kind of machine."""
    versions = {}
    from importlib.metadata import PackageNotFoundError, version

    for package in ("rdflib", "pyoxigraph"):
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = "not installed"
    return {"date": time.strftime("%Y-%m-%d"), "python": platform.python_version(), "machine": f"{platform.system()} {platform.machine()}", **versions}


def write_report(report: Report, directory: Path = HERE) -> None:
    growth = {m.engine: report.growth(m.engine) for m in report.measurements}
    data = {
        "environment": environment(),
        "measurements": [m.__dict__ for m in report.measurements],
        "growth_exponent": growth,
    }
    (directory / "report.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    lines = ["# Composite replace cost (generated, not committed)", "", "```", json.dumps(data["environment"]), "```", "", "| engine | size (M = N) | stored triples | seconds |", "|---|---|---|---|"]
    lines += [
        f"| {m.engine} | {m.size} | {m.stored_triples} | {m.seconds:.4f} |" if m.seconds is not None else f"| {m.engine} | {m.size} | | {m.outcome} |"
        for m in report.measurements
    ]
    lines += ["", "Fitted growth, time ~ size^k over the sizes of 100 and above:", ""]
    lines += [f"- {engine}: k = {k:.2f}" if k is not None else f"- {engine}: too few sizes" for engine, k in growth.items()]
    (directory / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    max_size = int(os.environ.get("COMPOSITE_COST_MAX", SIZES[-1]))
    try:
        report = run(max_size, isolated=True, memory_gb=float(os.environ.get("COMPOSITE_COST_MEMORY_GB", MEMORY_GB)))
    except WrongResult as error:
        print(f"WRONG RESULT: {error}", file=sys.stderr)
        return 1
    write_report(report)
    for engine in sorted({m.engine for m in report.measurements}):
        k = report.growth(engine)
        print(f"{engine}: growth exponent {k:.2f}" if k is not None else f"{engine}: too few sizes to fit")
    print(f"report written to {HERE / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
