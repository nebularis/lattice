# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""What the persistence compiler's named-graph replace costs against a candidate linear form on rdflib and Oxigraph, and what each store does with the update (ADR-A124, TSD-01, TSD-42, TD-42).

The generated `cas-replace-named-graph` (patch-log receipt, caller-named graph) sweeps the aggregate's graph with `OPTIONAL { GRAPH $g { ?s ?p ?o } }`. Its `WHERE` gives one
solution per stored triple (M) and a store that fills the whole `INSERT` template for every solution pays M times the payload (N). Four forms are measured.

| Form | What it is |
|---|---|
| `R0` | the generated replace, as the compiler renders it |
| `R0-nodelta` | `R0` with empty `assertTriples` and `retractTriples`, to separate the payload's cost from the delta blocks' cost |
| `R1-candidate` | a candidate the compiler does not generate yet, two operations in one request, a delete that sweeps and then an insert with no sweep |
| `R2-candidate` | a candidate the compiler does not generate yet, one operation whose sweep is a `UNION` with one extra solution that alone binds every graph the `INSERT` writes to |
| `R2-values-candidate` | a candidate the compiler does not generate yet, one operation whose `WHERE` carries the payload and the delta as `VALUES` rows in `UNION` branches, so the `INSERT` template holds three single quads and the payload is carried by the solutions |

**Workload.** For each size M the stored state at revision r holds M triples, the first half unchanged across revisions (the kept half) and the second half carrying the revision. The
payload of revision r+1 has the same shape, so N equals M and half of the payload is already stored. Three replaces per size, the best time kept.

**Probe P1.** TSD-01's update, in both row orders, on each engine. An engine that keeps the triple in both orders is `snapshot` and one that does not is `per-solution`. `R2-candidate` and `R2-values-candidate` are run only on a `snapshot` engine,
because they are right only if the store removes every deletion before it adds any insertion. rdflib's answer follows the process's hash seed, so P1 runs there in child processes under seeds 0 to 11, and a **witness**
runs `R2-candidate` on rdflib under each seed to record which seeds go wrong. The witness is evidence and never fails the run.

**Pass criterion.** After every replace the checks run, and a wrong result from `R0` or `R0-nodelta` fails the run. A candidate that is wrong is recorded in the report as `wrong: <reason>`. **Time never fails it.** A measurement runs in a child
process with a wall-clock limit (`REPLACE_FORMS_TIMEOUT`, default 900 seconds), and one that does not finish is recorded as such, which is not a wrong result.

`check.py --emit <file>` writes every form's text per size and replace for a runtime other than Python (`benchmark/persistence-replace-forms-jvm`). Run `mise run check:persistence-replace-forms`.
`REPLACE_FORMS_MAX_R0` caps the size at which `R0` and `R0-nodelta` run (default 3,000, since TD-42 recorded `R0` at 10,000 not finishing on Oxigraph in 8 GB), and `REPLACE_FORMS_QUICK=1` runs sizes up to 1,000.
The guards are off for every run, so both engines run the same query (Oxigraph cannot pass the guard's datatype test, probe P5)."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIZES = (100, 300, 1000, 3000, 10000)
REPEATS = 3
XSD_LONG = "http://www.w3.org/2001/XMLSchema#long"
PAT = "https://www.nebularis.org/neuro-semantic/lattice/persistence-store#"
ROOT = "urn:root:1"
META = "urn:g:meta"
TXN = "urn:g:txn"
LOG = "urn:g:txlog/"
GRAPH_PREFIX = "urn:g:parts/"
SUBJECT = "urn:x:s/"
PREDICATE = "urn:x:p"
SLOT = "{{{%s}}}"
SEEDS = range(12)

FORMS = {
    "R0": "R0 (generated)",
    "R0-nodelta": "R0 with empty delta slots",
    "R1-candidate": "R1 candidate (two operations)",
    "R2-candidate": "R2 candidate (one operation, UNION)",
    "R2-values-candidate": "R2 candidate (one operation, VALUES rows)",
}
CANDIDATES = ("R1-candidate", "R2-candidate", "R2-values-candidate")
NEEDS_SNAPSHOT = ("R2-candidate", "R2-values-candidate")
"""The forms that are right only on an engine that removes every deletion before it adds any insertion (P1)."""
GENERATED = ("R0", "R0-nodelta")
"""The forms whose wrong result fails the run. A candidate that is wrong is a finding, so it is recorded."""


class WrongResult(AssertionError):
    """A run did not leave what it should. For a generated form this is the one way the check fails."""


# ---- the engines ---------------------------------------------------------------------------------------------------------


class RdflibEngine:
    name = "rdflib"

    def __init__(self) -> None:
        import warnings

        from rdflib import Dataset

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            self.ds = Dataset()

    def update(self, text: str) -> None:
        self.ds.update(text)

    def triples(self, graph: str) -> set:
        from rdflib import URIRef

        return {(str(s), str(p), str(o)) for s, p, o in self.ds.graph(URIRef(graph))}

    def outside(self, graphs: set, prefix: str) -> int:
        """The quads in graphs other than `graphs` and those whose name starts with `prefix`, the default graph included."""
        return sum(len(g) for g in self.ds.graphs() if str(g.identifier) not in graphs and not str(g.identifier).startswith(prefix))


class OxigraphEngine:
    name = "oxigraph"

    def __init__(self) -> None:
        import pyoxigraph
        from lattice_testing_oxigraph import OxigraphStore

        self.ox = pyoxigraph
        self.store = OxigraphStore()

    def update(self, text: str) -> None:
        self.store.update(text)

    def triples(self, graph: str) -> set:
        ox = self.ox
        return {(q.subject.value, q.predicate.value, q.object.value) for q in self.store.store.quads_for_pattern(None, None, None, ox.NamedNode(graph))}

    def outside(self, graphs: set, prefix: str) -> int:
        count = 0
        for q in self.store.store:
            name = q.graph_name.value if isinstance(q.graph_name, self.ox.NamedNode) else ""
            if name not in graphs and not (name and name.startswith(prefix)):
                count += 1
        return count


def available_engines() -> list:
    engines = [RdflibEngine]
    try:
        import lattice_testing_oxigraph  # noqa: F401
    except ImportError:
        return engines
    return [OxigraphEngine, *engines]


def engine_named(name: str):
    return next(e for e in available_engines() if e.name == name)


# ---- the forms -----------------------------------------------------------------------------------------------------------


def _once(text: str, old: str, new: str) -> str:
    """`text` with `old` replaced by `new`, which must occur exactly once. The candidates are derived from the rendered `R0` by text, so a change in what the compiler renders stops here and not in a wrong result."""
    if text.count(old) != 1:
        raise RuntimeError(f"the rendered replace holds {text.count(old)} copies of {old!r}, not 1, so the candidate forms must be rederived")
    return text.replace(old, new)


def _grab(pattern: str, text: str) -> str:
    match = re.search(pattern, text)
    if not match:
        raise RuntimeError(f"the rendered replace does not match {pattern!r}")
    return match.group(1)


def candidate_r1(r0: str) -> str:
    """A candidate the compiler does not generate yet. Two operations in one request. The first deletes the aggregate's graph under `R0`'s whole `WHERE`, including its sweep. The second is `R0` without the sweep
    and without the sweep's quad in its `DELETE`, so its `WHERE` gives one solution."""
    header = r0[: r0.index("\nDELETE {") + 1]
    where_body = r0[r0.index("\nWHERE {\n") + len("\nWHERE {\n"):]
    first = header + "DELETE {\n  GRAPH $g { ?s ?p ?o }\n}\nWHERE {\n" + where_body
    second = _once(_once(r0, "  GRAPH $g { ?s ?p ?o }\n", ""), "  OPTIONAL { GRAPH $g { ?s ?p ?o } }\n", "")
    # The second operation takes the prefixes of the first, which carry over in a request. Oxigraph's parser refuses a prologue after the `;`.
    return first.rstrip("\n") + " ;\n" + second[len(header):]


def candidate_r2(r0: str) -> str:
    """A candidate the compiler does not generate yet. One operation. The sweep becomes a `UNION` of the sweep and one solution that binds every graph the `INSERT` writes to, so the `INSERT` is
    instantiated for that one solution and the sweep's solutions bind only `?s ?p ?o`, for the `DELETE`. Right only on a store that removes every deletion before it adds any insertion (P1)."""
    meta = _grab(r"GRAPH <([^>]+)> \{ \$root pat:epoch \$epoch", r0)
    txn = _grab(r"GRAPH <([^>]+)> \{ \$txnId pat:rev \$newRev ;", r0)
    log = _grab(r"STR\(<([^>]+)>\), SUBSTR", r0)
    log_bind = f'BIND(IRI(CONCAT(STR(<{log}>), SUBSTR(STR(NOW()), 1, 7))) AS ?logGraph)'
    add_bind = 'BIND(IRI(CONCAT(STR($newRev), "/add")) AS ?addGraph)'
    del_bind = 'BIND(IRI(CONCAT(STR($newRev), "/del")) AS ?delGraph)'
    text = r0
    for bind in (log_bind, add_bind, del_bind):
        text = _once(text, f"  {bind}\n", "")
    union = (f"  {{ GRAPH $g {{ ?s ?p ?o }} }} UNION {{ BIND($g AS ?w) BIND(<{meta}> AS ?metaW) BIND(<{txn}> AS ?txnW) {log_bind} {add_bind} {del_bind} }}\n")
    text = _once(text, "  OPTIONAL { GRAPH $g { ?s ?p ?o } }\n", union)
    text = _once(text, "GRAPH $g { {{{payloadTriples}}} }", "GRAPH ?w { {{{payloadTriples}}} }")
    text = _once(text, f"GRAPH <{meta}> {{ $root pat:epoch $epoch ;", "GRAPH ?metaW { $root pat:epoch $epoch ;")
    text = _once(text, f"GRAPH <{txn}> {{ $txnId pat:rev $newRev ;", "GRAPH ?txnW { $txnId pat:rev $newRev ;")
    return text


def candidate_r2_values(r0: str) -> str:
    """A candidate the compiler does not generate yet. One operation. `R0`'s `DELETE`, its three top-level binds and its `INSERT` blocks for the version row, the claim and the log stay as they are. The sweep becomes a `UNION` of the sweep,
    the payload as `VALUES` rows, the assertions as `VALUES` rows, the retractions as `VALUES` rows and an empty group (one solution, so a replace of an empty aggregate by an empty payload still moves the row). The three
    payload quads of the `INSERT` become single quads over the row variables. Right only on a store that removes every deletion before it adds any insertion (P1)."""
    union = ("  { GRAPH $g { ?s ?p ?o } } UNION { VALUES (?ps ?pp ?po) { {{{payloadRows}}} } } UNION { VALUES (?as ?ap ?ao) { {{{assertRows}}} } }"
             " UNION { VALUES (?ds ?dp ?do) { {{{retractRows}}} } } UNION { }\n")
    text = _once(r0, "  OPTIONAL { GRAPH $g { ?s ?p ?o } }\n", union)
    text = _once(text, "GRAPH $g { {{{payloadTriples}}} }", "GRAPH $g { ?ps ?pp ?po }")
    text = _once(text, "GRAPH ?addGraph { {{{assertTriples}}} }", "GRAPH ?addGraph { ?as ?ap ?ao }")
    return _once(text, "GRAPH ?delGraph { {{{retractTriples}}} }", "GRAPH ?delGraph { ?ds ?dp ?do }")


def templates() -> dict:
    """The rendered create and the text of each form, with the payload slots still in the text. `R0` is rendered by the compiler from the template `cas-replace-named-graph-patch-log` with `graph_names="caller"`
    and no guards, and the candidates are derived from it by text. (`persistence.builders.build` has no `receipt` keyword in this checkout, the receipt is part of the template's name.)"""
    from persistence.builders import build
    from persistence.ir_render import render
    from persistence.terms import Iri, Literal

    context = {
        "metaGraphPrefix": Iri.encode(META), "txnGraph": Iri.encode(TXN), "logGraphPrefix": Iri.encode(LOG),
        "graphPrefix": Literal.encode(GRAPH_PREFIX), "graphSuffix": Literal.encode(""),
        "eventGraphPrefix": Iri.encode("urn:g:events/order/"), "datasetGraph": Iri.encode("urn:g:dataset"), "datasetNode": Iri.encode("urn:g:dataset-node"),
    }
    create = render(build("create-if-absent-named-graph-patch-log", context, guards=False, graph_names="caller"))
    r0 = render(build("cas-replace-named-graph-patch-log", context, guards=False, graph_names="caller"))
    return {"create": create, "R0": r0, "R0-nodelta": r0, "R1-candidate": candidate_r1(r0), "R2-candidate": candidate_r2(r0), "R2-values-candidate": candidate_r2_values(r0)}


# ---- the workload --------------------------------------------------------------------------------------------------------


def state(m: int, revision: int) -> set:
    """The M triples stored at `revision`. The first half is `"k"` at every revision, the second half carries the revision."""
    half = m // 2
    return {(f"{SUBJECT}{i}", PREDICATE, "k" if i < half else f"r{revision}") for i in range(m)}


def changed(m: int, revision: int) -> set:
    """The half of the state that carries the revision."""
    return {t for t in state(m, revision) if t[2] != "k"}


def root_graph() -> str:
    return GRAPH_PREFIX + urllib.parse.quote(ROOT, safe="-_.~")


def rev_iri(seq: int) -> str:
    return f"urn:rev:{ROOT}/{seq}"


def nt(triples) -> str:
    """The triples as N-Triples text, in a fixed order, for a payload slot."""
    return " ".join(f'<{s}> <{p}> "{o}" .' for s, p, o in sorted(triples))


def rows(triples) -> str:
    """The triples as `VALUES` rows, `(<s> <p> "o")`, in the order `nt` writes them, for a row slot."""
    return " ".join(f'(<{s}> <{p}> "{o}")' for s, p, o in sorted(triples))


def substitute(text: str, parameters: dict) -> str:
    """The operation with each `$name` replaced by its term as N-Triples, which is how a runtime with no initial bindings for updates runs it (TSD-12). Every engine here runs the substituted text."""
    for name, (kind, value) in parameters.items():
        term = f"<{value}>" if kind == "iri" else f'"{value}"^^<{XSD_LONG}>' if kind == "long" else f'"{value}"'
        text = re.sub(r"\$" + name + r"\b", lambda _: term, text)
    return text


def digest(txn: str) -> str:
    return hashlib.sha256(txn.encode("utf-8")).hexdigest()


@dataclass
class Step:
    """One replace: the text to run and what it must leave."""

    text: str
    seq: int  # the sequence the replace moves to
    new_rev: str
    txn: str
    root_graph: str
    add_graph: str
    del_graph: str
    expect_root: set
    expect_add: set
    expect_del: set

    @property
    def graphs(self) -> set:
        return {self.root_graph, self.add_graph, self.del_graph, META, TXN}


@dataclass
class Run:
    create: str
    steps: list = field(default_factory=list)


def build_run(texts: dict, form: str, m: int, repeats: int = REPEATS) -> Run:
    """The create of revision 1 and `repeats` replaces of the form, each moving the changed half on by one revision, with every parameter and slot filled."""
    g = root_graph()
    create_params = {"root": ("iri", ROOT), "epoch": ("long", "3"), "newRev": ("iri", rev_iri(1)), "txnId": ("iri", "urn:txn:create"), "requestDigest": ("str", digest("urn:txn:create")), "g": ("iri", g)}
    create = substitute(texts["create"].replace(SLOT % "payloadTriples", nt(state(m, 1))), create_params)
    run = Run(create=create)
    for seq in range(1, repeats + 1):
        txn = f"urn:txn:replace{seq}"
        new_rev = rev_iri(seq + 1)
        params = {
            "root": ("iri", ROOT), "epoch": ("long", "3"), "expectedSeq": ("long", str(seq)), "nextSeq": ("long", str(seq + 1)), "newRev": ("iri", new_rev),
            "txnId": ("iri", txn), "requestDigest": ("str", digest(txn)), "g": ("iri", g),
        }
        delta = form != "R0-nodelta"
        assert_set, retract_set = (changed(m, seq + 1), changed(m, seq)) if delta else (set(), set())
        text = texts[form].replace(SLOT % "payloadTriples", nt(state(m, seq + 1))).replace(SLOT % "assertTriples", nt(assert_set)).replace(SLOT % "retractTriples", nt(retract_set))
        text = text.replace(SLOT % "payloadRows", rows(state(m, seq + 1))).replace(SLOT % "assertRows", rows(assert_set)).replace(SLOT % "retractRows", rows(retract_set))
        run.steps.append(Step(
            text=substitute(text, params), seq=seq + 1, new_rev=new_rev, txn=txn, root_graph=g, add_graph=new_rev + "/add", del_graph=new_rev + "/del",
            expect_root=state(m, seq + 1), expect_add=assert_set, expect_del=retract_set))
    return run


# ---- the checks ----------------------------------------------------------------------------------------------------------


def _differs(label: str, got: set, expected: set) -> str | None:
    if got == expected:
        return None
    missing, extra = expected - got, got - expected
    kept = sorted(t for t in missing if t[2] == "k")
    lost = f", {len(kept)} of them kept triples (first lost {kept[0][0]})" if kept else ""
    return f"{label} is missing {len(missing)} expected triples{lost} and holds {len(extra)} unexpected"


def verify(engine, step: Step, outside_before: int) -> list:
    """What is wrong after a replace, as a list of reasons, empty when nothing is. The root's graph holds exactly the payload (as a set), the version row is at the next sequence with the new head and not at the expected
    sequence, the add and delete graphs hold exactly the delta, the txn graph holds the claim, and no other graph changed."""
    issues = []
    for label, graph, expected in (("the root's graph", step.root_graph, step.expect_root), ("the add graph", step.add_graph, step.expect_add), ("the delete graph", step.del_graph, step.expect_del)):
        problem = _differs(label, engine.triples(graph), expected)
        if problem:
            issues.append(problem)
    row = {(p, o) for s, p, o in engine.triples(META) if s == ROOT}
    seq = step.seq
    if (PAT + "seq", str(seq)) not in row:
        issues.append(f"the version row is not at sequence {seq}")
    if (PAT + "seq", str(seq - 1)) in row:
        issues.append(f"the version row still holds sequence {seq - 1}")
    heads = sorted(o for p, o in row if p == PAT + "head")
    if heads != [step.new_rev]:
        issues.append(f"the version row's heads are {heads}, not [{step.new_rev}]")
    if (step.txn, PAT + "rev", step.new_rev) not in engine.triples(TXN):
        issues.append("the txn graph does not hold the claim")
    outside = engine.outside(step.graphs, LOG)
    if outside != outside_before:
        issues.append(f"graphs outside the replace's own changed from {outside_before} to {outside} quads")
    return issues


def run_form(engine_class, texts: dict, form: str, m: int, repeats: int = REPEATS) -> float:
    """The best time in milliseconds of `repeats` replaces. Raises WrongResult."""
    run = build_run(texts, form, m, repeats)
    engine = engine_class()
    engine.update(run.create)
    best = float("inf")
    for number, step in enumerate(run.steps, 1):
        before = engine.outside(step.graphs, LOG)
        start = time.perf_counter()
        engine.update(step.text)
        best = min(best, time.perf_counter() - start)
        issues = verify(engine, step, before)
        if issues:
            raise WrongResult(f"{engine_class.name}/{form}/M={m} replace {number}: " + "; ".join(issues))
    return best * 1000


# ---- probe P1 ------------------------------------------------------------------------------------------------------------

P1_ROWS = {"insert row first": "(<urn:s> UNDEF) (UNDEF <urn:s>)", "delete row first": "(UNDEF <urn:s>) (<urn:s> UNDEF)"}
P1_STORED = "INSERT DATA { GRAPH <urn:g> { <urn:s> <urn:p> <urn:o> } }"
P1_UPDATE = "DELETE { GRAPH <urn:g> { ?d <urn:p> <urn:o> } } INSERT { GRAPH <urn:g> { ?i <urn:p> <urn:o> } } WHERE { VALUES (?i ?d) { %s } }"


def p1_kept(engine_class, rows: str) -> bool:
    """TSD-01's update. The specification removes every deletion and then adds every insertion, so the triple survives in either order."""
    engine = engine_class()
    engine.update(P1_STORED)
    engine.update(P1_UPDATE % rows)
    return ("urn:s", "urn:p", "urn:o") in engine.triples("urn:g")


def _child(arguments: list, seed: int | None = None) -> str:
    env = {**os.environ, **({"PYTHONHASHSEED": str(seed)} if seed is not None else {})}
    return subprocess.run([sys.executable, str(Path(__file__).resolve()), *arguments], env=env, capture_output=True, text=True, check=True).stdout.strip()


def p1(engine_class) -> dict:
    """For each row order, (the runs that kept the triple, the runs). rdflib's answer follows the process's hash seed (TSD-01), so it runs in child processes under seeds 0 to 11. Another engine runs once."""
    if engine_class is not RdflibEngine:
        return {order: (int(p1_kept(engine_class, rows)), 1) for order, rows in P1_ROWS.items()}
    out = {}
    with ThreadPoolExecutor(max_workers=len(SEEDS)) as pool:
        for order, rows in P1_ROWS.items():
            kept = list(pool.map(lambda seed: _child(["--p1-child", engine_class.name, rows], seed) == "True", SEEDS))
            out[order] = (sum(kept), len(kept))
    return out


def is_snapshot(result: dict) -> bool:
    return all(kept == total for kept, total in result.values())


# ---- the witness ---------------------------------------------------------------------------------------------------------


def witness_outcome(m: int = 100) -> str:
    """`R2-candidate` on rdflib in this process, as the words for the report: `right`, or the first replace that went wrong and why."""
    texts = templates()
    run = build_run(texts, "R2-candidate", m)
    engine = RdflibEngine()
    engine.update(run.create)
    for number, step in enumerate(run.steps, 1):
        before = engine.outside(step.graphs, LOG)
        engine.update(step.text)
        issues = verify(engine, step, before)
        if issues:
            return f"wrong at replace {number}: " + "; ".join(issues)
    return "right"


def witness() -> list:
    with ThreadPoolExecutor(max_workers=len(SEEDS)) as pool:
        return list(zip(SEEDS, pool.map(lambda seed: _child(["--witness-child"], seed), SEEDS)))


# ---- the operations for another runtime ---------------------------------------------------------------------------------


def count_query(pattern: str) -> str:
    """A `COUNT(*)` over `pattern`, which must bind a variable. RDF4J 6.1.0 counts 0 for a pattern with no variable that matches (TSD-48)."""
    return "SELECT (COUNT(*) AS ?n) WHERE { " + pattern + " }"


def _nt_lines(triples: set) -> list:
    return [f'<{s}> <{p}> "{o}" .' for s, p, o in sorted(triples)]


def outside_query(step: Step) -> str:
    names = ", ".join(f"<{g}>" for g in sorted(step.graphs))
    return count_query(f'GRAPH ?g {{ ?s ?p ?o }} FILTER(?g NOT IN ({names}) && !STRSTARTS(STR(?g), "{LOG}"))')


def emit_operations(sizes=SIZES, repeats: int = REPEATS) -> dict:
    """Everything a runtime other than Python needs to repeat this benchmark on its own store: for each size the create and, for each form, the replaces with their parameters substituted and their slots filled, and the
    checks that say each replace did what it should. A check is a count query with its expected count, or a graph with the expected triples as N-Triples lines to compare as a set. The runtime asserts them and never judges time."""
    texts = templates()
    runs = {}
    for m in sizes:
        forms = {}
        create = None
        for form in FORMS:
            run = build_run(texts, form, m, repeats)
            create = run.create
            steps = []
            for step in run.steps:
                row = f"GRAPH <{META}> {{ <{ROOT}> <{PAT}%s> ?q FILTER(%s) }}"
                steps.append({
                    "text": step.text, "rootGraph": step.root_graph, "addGraph": step.add_graph, "delGraph": step.del_graph,
                    "expect": {"root": _nt_lines(step.expect_root), "add": _nt_lines(step.expect_add), "del": _nt_lines(step.expect_del)},
                    "counts": [
                        {"query": count_query(row % ("seq", f'STR(?q) = "{step.seq}"')), "expect": 1},
                        {"query": count_query(row % ("seq", f'STR(?q) = "{step.seq - 1}"')), "expect": 0},
                        {"query": count_query(row % ("head", f"?q = <{step.new_rev}>")), "expect": 1},
                        {"query": count_query(f"GRAPH <{META}> {{ <{ROOT}> <{PAT}head> ?q }}"), "expect": 1},
                        {"query": count_query(f"GRAPH <{TXN}> {{ <{step.txn}> <{PAT}rev> ?q FILTER(?q = <{step.new_rev}>) }}"), "expect": 1},
                    ],
                    "outsideQuery": outside_query(step),
                })
            forms[form] = steps
        runs[str(m)] = {"create": create, "forms": forms}
    return {
        "sizes": list(sizes), "repeats": repeats, "root": ROOT, "rootGraph": root_graph(),
        "forms": [{"id": f, "label": label, "candidate": f in CANDIDATES, "generated": f in GENERATED, "needsSnapshot": f in NEEDS_SNAPSHOT} for f, label in FORMS.items()],
        "runs": runs,
    }


# ---- the report ----------------------------------------------------------------------------------------------------------


def environment() -> dict:
    versions = {}
    for module in ("rdflib", "pyoxigraph"):
        try:
            versions[module] = __import__(module).__version__
        except ImportError:
            pass
    return {"python": platform.python_version(), "machine": platform.machine(), "system": platform.system(), **versions}


@dataclass
class Report:
    p1: dict = field(default_factory=dict)  # engine -> {order: (kept, total)}
    cells: list = field(default_factory=list)  # (engine, form, m, cell)
    witness: list = field(default_factory=list)  # (seed, outcome)
    generated_wrong: list = field(default_factory=list)


def job(engine_name: str, form: str, m: int) -> str:
    """The child's side: one measurement. Prints `RESULT<tab>ms` or `WRONG<tab>reason`."""
    try:
        ms = run_form(engine_named(engine_name), templates(), form, m)
    except WrongResult as error:
        return "WRONG\t" + str(error).replace("\n", " ")
    return f"RESULT\t{ms:.1f}"


def in_child(engine_name: str, form: str, m: int, timeout: float) -> str:
    """One measurement in a child process with a wall-clock limit. Returns the cell, which is the milliseconds, `wrong: <reason>` or `did not finish: <reason>`."""
    try:
        done = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--job", f"{engine_name}|{form}|{m}"], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return f"did not finish: no result within {timeout:.0f} s"
    for line in done.stdout.splitlines():
        if line.startswith("WRONG\t"):
            return "wrong: " + line[6:]
        if line.startswith("RESULT\t"):
            return line[7:]
    tail = " ".join(done.stderr.strip().splitlines()[-1:])
    return f"did not finish: the child exited {done.returncode}" + (f" ({tail})" if tail else "")


def measure(max_r0: int, quick: bool, timeout: float) -> Report:
    report = Report()
    sizes = [m for m in SIZES if not quick or m <= 1000]
    for engine_class in available_engines():
        report.p1[engine_class.name] = p1(engine_class)
        snapshot = is_snapshot(report.p1[engine_class.name])
        for form in FORMS:
            stopped = False
            for m in sizes:
                if form in GENERATED and m > max_r0:
                    cell = f"not run: above REPLACE_FORMS_MAX_R0 ({max_r0})"
                elif form in NEEDS_SNAPSHOT and not snapshot:
                    cell = "not run: per-solution store (P1)"
                elif stopped:
                    cell = "not run: a smaller size did not finish"
                else:
                    print(f"progress: {engine_class.name} {form} {m}", file=sys.stderr, flush=True)
                    cell = in_child(engine_class.name, form, m, timeout)
                    stopped = cell.startswith("did not finish")
                    if cell.startswith("wrong:") and form in GENERATED:
                        report.generated_wrong.append(f"{engine_class.name}/{form}/M={m}: {cell}")
                report.cells.append((engine_class.name, form, m, cell))
    print("progress: witness", file=sys.stderr, flush=True)
    report.witness = witness()
    return report


def render_report(report: Report) -> str:
    env = environment()
    lines = [f"Run {time.strftime('%Y-%m-%d')}: " + ", ".join(f"{k} {v}" for k, v in env.items()), ""]
    lines += ["## P1, does TSD-01's update keep the triple in both row orders", "", "| Engine | Row order | Runs that kept the triple | Verdict |", "|---|---|---|---|"]
    for engine, result in report.p1.items():
        verdict = "snapshot" if is_snapshot(result) else "per-solution"
        for order, (kept, total) in result.items():
            lines.append(f"| {engine} | {order} | {kept} of {total} | {verdict} |")
    for engine in report.p1:
        lines += ["", f"## {engine}, best of {REPEATS} replaces, milliseconds", "", "| Form | M (N equals M) | ms |", "|---|---|---|"]
        lines += [f"| {FORMS[form]} | {m:,} | {cell} |" for e, form, m, cell in report.cells if e == engine]
    lines += ["", "## Witness, R2 candidate on rdflib at M = 100 under each hash seed", "", "| PYTHONHASHSEED | Outcome |", "|---|---|"]
    lines += [f"| {seed} | {outcome} |" for seed, outcome in report.witness]
    return "\n".join(lines) + "\n"


def main() -> int:
    argv = sys.argv[1:]
    if len(argv) == 2 and argv[0] == "--emit":
        Path(argv[1]).write_text(json.dumps(emit_operations(), indent=1), encoding="utf-8", newline="\n")
        print(f"wrote {argv[1]}")
        return 0
    if len(argv) == 2 and argv[0] == "--job":
        name, form, m = argv[1].split("|")
        print(job(name, form, int(m)))
        return 0
    if len(argv) == 3 and argv[0] == "--p1-child":
        print(p1_kept(engine_named(argv[1]), argv[2]))
        return 0
    if argv == ["--witness-child"]:
        print(witness_outcome())
        return 0
    max_r0 = int(os.environ.get("REPLACE_FORMS_MAX_R0", "3000"))
    quick = os.environ.get("REPLACE_FORMS_QUICK") == "1"
    timeout = float(os.environ.get("REPLACE_FORMS_TIMEOUT", "900"))
    report = measure(max_r0, quick, timeout)
    text = render_report(report)
    (HERE / "report.md").write_text(text, encoding="utf-8", newline="\n")
    print(text)
    if report.generated_wrong:
        print("WRONG RESULT from a generated form:\n" + "\n".join(report.generated_wrong), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
