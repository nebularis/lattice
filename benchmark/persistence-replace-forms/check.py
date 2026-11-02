# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""What the persistence compiler's named-graph replace costs against candidate linear forms and the generated rows replace on rdflib and Oxigraph, and what each store does with the update (ADR-A124, TSD-01, TSD-42, TD-42).

The generated `cas-replace-named-graph` (patch-log receipt, caller-named graph) sweeps the aggregate's graph with `OPTIONAL { GRAPH $g { ?s ?p ?o } }`. Its `WHERE` gives one
solution per stored triple (M) and a store that fills the whole `INSERT` template for every solution pays M times the payload (N). Six forms are measured.

| Form | What it is |
|---|---|
| `R0` | the generated replace, as the compiler renders it |
| `R0-nodelta` | `R0` with empty `assertTriples` and `retractTriples`, to separate the payload's cost from the delta blocks' cost |
| `R1-candidate` | a candidate the compiler does not generate yet, two operations in one request, a delete that sweeps and then an insert with no sweep |
| `R2-candidate` | a candidate the compiler does not generate yet, one operation whose sweep is a `UNION` with one extra solution that alone binds every graph the `INSERT` writes to |
| `R3-delta` | the generated delta replace (`cas-replace-named-graph-delta-patch-log`, `cas-replace-composite-property-delta-patch-log`, `dal:ChangedTriples`), one operation with no sweep, whose `DELETE` holds the triples the caller retracted and whose `INSERT` holds the triples it asserted, so it is linear in the change on every engine. It runs a workload of one changed triple per revision (k = 1) at each M and needs no snapshot semantics |
| `R2-values-candidate` | the generated rows replace (`cas-replace-named-graph-rows-patch-log`, `cas-replace-composite-property-rows-patch-log`), one operation whose `WHERE` carries the payload and the delta as `VALUES` rows in `UNION` branches, so the `INSERT` template holds three single quads and the payload is carried by the solutions. Its three payload slots are filled as rows `(s p o)` |

**Workload.** For each size M the stored state at revision r holds M triples, the first half unchanged across revisions (the kept half) and the second half carrying the revision. The
payload of revision r+1 has the same shape, so N equals M and half of the payload is already stored. Three replaces per size, the best time kept.

**Probe P1.** TSD-01's update, in both row orders, on each engine. An engine that keeps the triple in both orders is `snapshot` and one that does not is `per-solution`. `R2-candidate` and `R2-values-candidate` are run only on a `snapshot` engine,
because they are right only if the store removes every deletion before it adds any insertion. rdflib's answer follows the process's hash seed, so P1 runs there in child processes under seeds 0 to 11, and a **witness**
runs `R2-candidate` on rdflib under each seed to record which seeds go wrong. The witness is evidence and never fails the run.

**Pass criterion.** After every replace the checks run, and a wrong result from `R0`, `R0-nodelta` or the generated rows replace fails the run. A candidate that is wrong is recorded in the report as `wrong: <reason>`. **Time never fails it.** A measurement runs in a child
process with a wall-clock limit (`REPLACE_FORMS_TIMEOUT`, default 900 seconds), and one that does not finish is recorded as such, which is not a wrong result.

**Two families.** `named-graph` replaces the aggregate held in a graph of its own. `composite` replaces a root and the members its owned path reaches, in one data graph shared with a bystander aggregate that no replace may touch.
`--family named-graph|composite|both` (default both, or `REPLACE_FORMS_FAMILY`) selects them. The composite family has no `R2-candidate`, which is refuted for it.

**Edge cases.** For each family and for `R0`, `R1-candidate` and `R2-values-candidate`, small cases on a fresh store with no timing, each checked by the same `verify` as the sized runs. E1 is an empty aggregate replaced by 50 triples, E2 is 50 triples replaced by nothing,
E3 is an empty aggregate replaced by nothing, E4 is a replace by the identical 50 triples, and E5 (composite only) is E1 after checking that the root is in no triple, recording how many solutions the bare sweep gives. Every case is reported as `pass`, `wrong: <reasons>` or `error: <message>`.

**Bare sweep.** For the composite family at M = 3,000 and 10,000 the time of the sweep pattern alone, best of three, so the path's cost can be separated from the form's.

`check.py --emit <file>` writes every form's text per size and replace for a runtime other than Python (`benchmark/persistence-replace-forms-jvm`). Run `mise run check:persistence-replace-forms`.
`REPLACE_FORMS_MAX_R0` caps the size at which `R0` and `R0-nodelta` run (default 3,000, since TD-42 recorded `R0` at 10,000 not finishing on Oxigraph in 8 GB), and `REPLACE_FORMS_QUICK=1` runs sizes up to 1,000 (or `REPLACE_FORMS_QUICK=<family>[,<family>]` for those families only).
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
FAMILIES = ("named-graph", "composite")
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
    "R2-values-candidate": "R2 (generated rows)",
    "R3-delta": "R3 (generated delta, k = 1)",
}
CANDIDATES = ("R1-candidate", "R2-candidate")
NEEDS_SNAPSHOT = ("R2-candidate", "R2-values-candidate")
"""The forms that are right only on an engine that removes every deletion before it adds any insertion (P1)."""
GENERATED = ("R0", "R0-nodelta", "R2-values-candidate", "R3-delta")
"""The forms whose wrong result fails the run. A candidate that is wrong is a finding, so it is recorded."""
ROWS_FORMS = ("R2-values-candidate",)
"""The forms whose payload slots are filled as rows `(s p o)` (`dal:TripleRows`) and not as N-Triples."""
DELTA_FORMS = ("R3-delta",)
"""The forms that send the triples retracted and asserted against the state read and sweep nothing (`dal:ChangedTriples`, persistence-delta-replace DR1). They run the workload with one changed triple per revision (k = 1), need no snapshot
semantics, are linear in the change and so are not held to `REPLACE_FORMS_MAX_R0`."""


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

    def count(self, query: str) -> int:
        return int(list(self.ds.query(query))[0][0])

    def listed(self, graph: str) -> bool:
        """Whether the dataset lists the graph, with no triple of it asked for first (reading a graph here creates it)."""
        return any(str(g.identifier) == graph for g in self.ds.graphs())

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

    def count(self, query: str) -> int:
        return int(list(self.store.store.query(query))[0]["n"].value)

    def listed(self, graph: str) -> bool:
        return self.store.store.contains_named_graph(self.ox.NamedNode(graph))

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


NAMED_SWEEP = "  OPTIONAL { GRAPH $g { ?s ?p ?o } }\n"
COMPOSITE_SWEEP = re.compile(r"  OPTIONAL \{\n    GRAPH <([^>]+)> \{\n      \$root (.+?) \?s \.\n      \?s \?p \?o\n    \}\n  \}\n")
"""The composite replace's sweep as the renderer writes it. The data graph and the owned path are grabbed from the rendered text and never typed here."""


def candidate_r1(r0: str, sweep: str = NAMED_SWEEP, sweep_quad: str = "  GRAPH $g { ?s ?p ?o }\n") -> str:
    """A candidate the compiler does not generate yet. Two operations in one request. The first deletes the aggregate's graph (or its members) under `R0`'s whole `WHERE`, including its sweep. The second is `R0` without the sweep
    and without the sweep's quad in its `DELETE`, so its `WHERE` gives one solution."""
    header = r0[: r0.index("\nDELETE {") + 1]
    where_body = r0[r0.index("\nWHERE {\n") + len("\nWHERE {\n"):]
    first = header + "DELETE {\n" + sweep_quad + "}\nWHERE {\n" + where_body
    second = _once(_once(r0, sweep_quad, ""), sweep, "")
    # The second operation takes the prefixes of the first, which carry over in a request. Oxigraph's parser refuses a prologue after the `;`.
    return first.rstrip("\n") + " ;\n" + second[len(header):]


def candidate_r2(r0: str) -> str:
    """A candidate the compiler does not generate yet. One operation. The sweep becomes a `UNION` of the sweep and one solution that binds every graph the `INSERT` writes to, so the `INSERT` is
    instantiated for that one solution and the sweep's solutions bind only `?s ?p ?o`, for the `DELETE`. Right only on a store that removes every deletion before it adds any insertion (P1). Named-graph family only."""
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
    text = _once(text, NAMED_SWEEP, union)
    text = _once(text, "GRAPH $g { {{{payloadTriples}}} }", "GRAPH ?w { {{{payloadTriples}}} }")
    text = _once(text, f"GRAPH <{meta}> {{ $root pat:epoch $epoch ;", "GRAPH ?metaW { $root pat:epoch $epoch ;")
    text = _once(text, f"GRAPH <{txn}> {{ $txnId pat:rev $newRev ;", "GRAPH ?txnW { $txnId pat:rev $newRev ;")
    return text


# ---- the families --------------------------------------------------------------------------------------------------------

IRI_PREFIXES = ("urn:", "http://", "https://")
EX = "https://example.org/projects#"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
COMPOSITE_ROOT = EX + "p1"
BYSTANDER = frozenset({
    (EX + "p2", EX + "name", "Gemini"), (EX + "p2", EX + "hasMilestone", EX + "m-other"), (EX + "m-other", EX + "due", "2027-01-01"), (EX + "acme", EX + "name", "Acme"),
})
"""What a replace of the composite root must leave alone, as `benchmark/persistence-composite-cost` keeps it: a second aggregate and a reference outside both."""


def is_iri(value: str) -> bool:
    """Whether an object of the workload is an IRI. The workload's literals are short words that never start with a scheme, so the value alone says which it is."""
    return value.startswith(IRI_PREFIXES)


def term(value: str) -> str:
    return f"<{value}>" if is_iri(value) else f'"{value}"'


def named_state(m: int, revision: int) -> set:
    """The M triples stored at `revision` in the named-graph family. The first half is `"k"` at every revision, the second half carries the revision."""
    half = m // 2
    return {(f"{SUBJECT}{i}", PREDICATE, "k" if i < half else f"r{revision}") for i in range(m)}


def composite_state(m: int, revision: int) -> set:
    """The aggregate of the composite family at `revision`, M triples: the root's type and name, and K members reached by `hasMilestone`, each with a link and a due date, M = 2 + 2K. About half the members are kept
    at every revision and the others are new members per revision, so the delta moves about half the triples."""
    if m == 0:
        return set()
    k = max((m - 2) // 2, 1)
    kept = k // 2
    out = {(COMPOSITE_ROOT, RDF_TYPE, EX + "Project"), (COMPOSITE_ROOT, EX + "name", "k")}
    for i in range(k):
        member = f"{EX}m{i}" if i < kept else f"{EX}m{i}-r{revision}"
        out |= {(COMPOSITE_ROOT, EX + "hasMilestone", member), (member, EX + "due", "k" if i < kept else "d")}
    return out


def state(m: int, revision: int) -> set:
    return named_state(m, revision)


def changed(m: int, revision: int) -> set:
    """The half of the named-graph state that carries the revision."""
    return {t for t in state(m, revision) if t[2] != "k"}


def root_graph() -> str:
    return GRAPH_PREFIX + urllib.parse.quote(ROOT, safe="-_.~")


def rev_iri(seq: int, root: str = ROOT) -> str:
    return f"urn:rev:{root}/{seq}"


def nt(triples) -> str:
    """The triples as N-Triples text, in a fixed order, for a payload slot."""
    return " ".join(f'<{s}> <{p}> {term(o)} .' for s, p, o in sorted(triples))


def rows(triples) -> str:
    """The triples as `VALUES` rows, `(<s> <p> "o")`, in the order `nt` writes them, for a row slot."""
    return " ".join(f'(<{s}> <{p}> {term(o)})' for s, p, o in sorted(triples))


@dataclass
class Family:
    """One kind of aggregate and the forms that replace it. `graph` holds the aggregate (the data graph, shared with the bystander, for the composite family), and `state(m, r)` is what the aggregate holds at revision r."""

    name: str
    root: str
    graph: str
    meta: str
    txn: str
    log: str
    texts: dict
    forms: tuple
    state: object
    bystander: frozenset = frozenset()
    sweep: str | None = None
    """The bare sweep pattern with `$root` still in the text, for the composite family."""

    @property
    def preload(self) -> str:
        """The update that stores the bystander, or nothing."""
        return f"INSERT DATA {{ GRAPH <{self.graph}> {{ {nt(self.bystander)} }} }}" if self.bystander else ""

    @property
    def edge_cases(self) -> tuple:
        return EDGE_CASES if self.name == "composite" else EDGE_CASES[:4]

    def sweep_query(self, with_spo: bool = True) -> str:
        pattern = self.sweep if with_spo else self.sweep.replace(" . ?s ?p ?o", "")
        return f"SELECT (COUNT(*) AS ?n) WHERE {{ {pattern.replace('$root', '<' + self.root + '>')} }}"


def _rendered(context: dict, create: str, replace: str) -> tuple:
    from persistence.builders import build
    from persistence.ir_render import render

    return render(build(create, context, guards=False, graph_names="caller")), render(build(replace, context, guards=False, graph_names="caller"))


def _generated(context: dict, template: str) -> str:
    """The text of a replace the compiler generates, rendered as `R0` is."""
    from persistence.builders import build
    from persistence.ir_render import render

    return render(build(template, context, guards=False, graph_names="caller"))


def named_family() -> Family:
    """The rendered create and the text of each form, with the payload slots still in the text. `R0` is rendered by the compiler from the template `cas-replace-named-graph-patch-log` with `graph_names="caller"`
    and no guards, and the candidates are derived from it by text. (`persistence.builders.build` has no `receipt` keyword in this checkout, the receipt is part of the template's name.)"""
    from persistence.terms import Iri, Literal

    context = {
        "metaGraphPrefix": Iri.encode(META), "txnGraph": Iri.encode(TXN), "logGraphPrefix": Iri.encode(LOG),
        "graphPrefix": Literal.encode(GRAPH_PREFIX), "graphSuffix": Literal.encode(""),
        "eventGraphPrefix": Iri.encode("urn:g:events/order/"), "datasetGraph": Iri.encode("urn:g:dataset"), "datasetNode": Iri.encode("urn:g:dataset-node"),
    }
    create, r0 = _rendered(context, "create-if-absent-named-graph-patch-log", "cas-replace-named-graph-patch-log")
    texts = {"create": create, "R0": r0, "R0-nodelta": r0, "R1-candidate": candidate_r1(r0), "R2-candidate": candidate_r2(r0), "R2-values-candidate": _generated(context, "cas-replace-named-graph-rows-patch-log"), "R3-delta": _generated(context, "cas-replace-named-graph-delta-patch-log")}
    return Family("named-graph", ROOT, root_graph(), META, TXN, LOG, texts, ("R0", "R0-nodelta", "R1-candidate", "R2-candidate", "R2-values-candidate", "R3-delta"), named_state)


WHOLE_STATE = f"""@prefix dal: <https://www.nebularis.org/neuro-semantic/lattice/persistence#> .
@prefix ex: <https://example.org/projects#> .
ex:ProjectEncoding a dal:WriteDisciplineProfile ; dal:appliesTo ex:ProjectClass ; dal:replaceEncoding dal:WholeState ."""


def composite_context() -> dict:
    """The bindings of the composite replace of the project example, which `benchmark/persistence-composite-cost` also renders. The owned path and the data graph are the example's."""
    from rdflib import RDF

    from persistence import witness
    from persistence.compiler import compile_to_graph
    from persistence.instantiate import operation_context
    from persistence.namespaces import DAL

    config = witness._load_fixture(Path(witness.EXAMPLES_DIR) / "composite-project-ownership.ttl")
    # the example now gets the delta replace, which has no owned path, and R0 sweeps it, so the family declares the whole-state encoding (DR1)
    config.parse(data=WHOLE_STATE, format="turtle")
    compiled, _ = compile_to_graph(config, guards=False)
    for profile in compiled.subjects(RDF.type, DAL.CompiledProfile):
        for node in compiled.objects(profile, DAL.generatedOperation):
            if str(compiled.value(compiled.value(node, DAL.usesTemplate), DAL.templateId)).startswith("cas-replace-composite"):
                return operation_context(compiled, node)
    raise RuntimeError("the project example has no composite replace")


def composite_family() -> Family:
    """The composite family: the rendered create and replace of the project example, and the candidates derived from the replace by text. The sweep to move, the data graph and the owned path are grabbed from the
    rendered text. There is no `R2-candidate` here, which is refuted for the composite family."""
    create, r0 = _rendered(composite_context(), "create-if-absent-composite-patch-log", "cas-replace-composite-property-patch-log")
    match = COMPOSITE_SWEEP.search(r0)
    if not match:
        raise RuntimeError("the rendered composite replace has no sweep of the expected shape")
    sweep, data, path = match.group(0), match.group(1), match.group(2)
    meta = _grab(r"GRAPH <([^>]+)> \{ \$root pat:epoch \$epoch", r0)
    txn = _grab(r"GRAPH <([^>]+)> \{ \$txnId pat:rev \$newRev ;", r0)
    log = _grab(r"STR\(<([^>]+)>\), SUBSTR", r0)
    texts = {
        "create": create, "R0": r0, "R0-nodelta": r0, "R1-candidate": candidate_r1(r0, sweep, f"  GRAPH <{data}> {{ ?s ?p ?o }}\n"),
        "R2-values-candidate": _generated(composite_context(), "cas-replace-composite-property-rows-patch-log"),
        "R3-delta": _generated(composite_context(), "cas-replace-composite-property-delta-patch-log"),
    }
    return Family("composite", COMPOSITE_ROOT, data, meta, txn, log, texts, ("R0", "R0-nodelta", "R1-candidate", "R2-values-candidate", "R3-delta"), composite_state, BYSTANDER, f"GRAPH <{data}> {{ $root {path} ?s . ?s ?p ?o }}")


def family_named(name: str) -> Family:
    return {"named-graph": named_family, "composite": composite_family}[name]()


def templates() -> dict:
    """The named-graph family's texts, kept for the callers that want only these."""
    return named_family().texts


# ---- the workload --------------------------------------------------------------------------------------------------------


def substitute(text: str, parameters: dict) -> str:
    """The operation with each `$name` replaced by its term as N-Triples, which is how a runtime with no initial bindings for updates runs it (TSD-12). Every engine here runs the substituted text."""
    for name, (kind, value) in parameters.items():
        replacement = f"<{value}>" if kind == "iri" else f'"{value}"^^<{XSD_LONG}>' if kind == "long" else f'"{value}"'
        text = re.sub(r"\$" + name + r"\b", lambda _: replacement, text)
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
    root: str
    root_graph: str  # the graph that holds the aggregate
    add_graph: str
    del_graph: str
    meta: str
    txn_graph: str
    log: str
    expect_root: set  # what that graph must hold, the bystander included
    expect_add: set
    expect_del: set
    bystander: frozenset = frozenset()

    @property
    def graphs(self) -> set:
        return {self.root_graph, self.add_graph, self.del_graph, self.meta, self.txn_graph}


@dataclass
class Run:
    create: str
    steps: list = field(default_factory=list)
    preload: str = ""


def delta_states(family: Family, m: int, repeats: int = REPEATS) -> list:
    """The states of revisions 1 to `repeats` + 1 at size M for a delta form: the family's first state, and then one literal-valued triple changed per revision (k = 1), always the same one, so each replace retracts one triple and asserts one."""
    states = [family.state(m, 1)]
    for revision in range(2, repeats + 2):
        old = states[-1]
        literals = sorted(t for t in old if not is_iri(t[2]))
        states.append(old - {literals[0]} | {(literals[0][0], literals[0][1], f"r{revision}")} if literals else set(old))
    return states


def sized_states(family: Family, m: int, repeats: int = REPEATS, form: str | None = None) -> list:
    """The states of revisions 1 to `repeats` + 1 at size M. Revision 1 is the create."""
    if form in DELTA_FORMS:
        return delta_states(family, m, repeats)
    return [family.state(m, r) for r in range(1, repeats + 2)]


def build_run(family: Family, form: str, states: list) -> Run:
    """The create of the first state and a replace from each state to the next, with every parameter and slot filled. The delta of a replace is the difference of the two states, which for the sized workload is the changed half
    (and for the edge cases the whole payload, or nothing)."""
    texts, root, g = family.texts, family.root, family.graph
    create_params = {"root": ("iri", root), "epoch": ("long", "3"), "newRev": ("iri", rev_iri(1, root)), "txnId": ("iri", "urn:txn:create"), "requestDigest": ("str", digest("urn:txn:create")), "g": ("iri", g)}
    create = substitute(texts["create"].replace(SLOT % "payloadTriples", nt(states[0])), create_params)
    run = Run(create=create, preload=family.preload)
    for index in range(1, len(states)):
        seq, old, new = index, states[index - 1], states[index]
        txn = f"urn:txn:replace{seq}"
        new_rev = rev_iri(seq + 1, root)
        params = {
            "root": ("iri", root), "epoch": ("long", "3"), "expectedSeq": ("long", str(seq)), "nextSeq": ("long", str(seq + 1)), "newRev": ("iri", new_rev),
            "txnId": ("iri", txn), "requestDigest": ("str", digest(txn)), "g": ("iri", g),
        }
        delta = form != "R0-nodelta"
        assert_set, retract_set = (new - old, old - new) if delta else (set(), set())
        fill = rows if form in ROWS_FORMS else nt
        text = texts[form].replace(SLOT % "payloadTriples", fill(new)).replace(SLOT % "assertTriples", fill(assert_set)).replace(SLOT % "retractTriples", fill(retract_set))
        run.steps.append(Step(
            text=substitute(text, params), seq=seq + 1, new_rev=new_rev, txn=txn, root=root, root_graph=g, add_graph=new_rev + "/add", del_graph=new_rev + "/del",
            meta=family.meta, txn_graph=family.txn, log=family.log, expect_root=set(new) | set(family.bystander), expect_add=assert_set, expect_del=retract_set, bystander=family.bystander))
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
    """What is wrong after a replace, as a list of reasons, empty when nothing is. The aggregate's graph holds exactly the payload (as a set, and the bystander beside it), the version row is at the next sequence with the new head
    and not at the expected sequence, the add and delete graphs hold exactly the delta, the txn graph holds the claim, and no other graph changed."""
    issues = []
    label = "the data graph" if step.bystander else "the root's graph"
    got = engine.triples(step.root_graph)
    problem = _differs(label, got, step.expect_root)
    if problem:
        issues.append(problem)
        if step.bystander and not step.bystander <= got:
            issues.append(f"the bystander lost {len(step.bystander - got)} triples")
    for name, graph, expected in (("the add graph", step.add_graph, step.expect_add), ("the delete graph", step.del_graph, step.expect_del)):
        problem = _differs(name, engine.triples(graph), expected)
        if problem:
            issues.append(problem)
    row = {(p, o) for s, p, o in engine.triples(step.meta) if s == step.root}
    seq = step.seq
    if (PAT + "seq", str(seq)) not in row:
        issues.append(f"the version row is not at sequence {seq}")
    if (PAT + "seq", str(seq - 1)) in row:
        issues.append(f"the version row still holds sequence {seq - 1}")
    heads = sorted(o for p, o in row if p == PAT + "head")
    if heads != [step.new_rev]:
        issues.append(f"the version row's heads are {heads}, not [{step.new_rev}]")
    if (step.txn, PAT + "rev", step.new_rev) not in engine.triples(step.txn_graph):
        issues.append("the txn graph does not hold the claim")
    outside = engine.outside(step.graphs, step.log)
    if outside != outside_before:
        issues.append(f"graphs outside the replace's own changed from {outside_before} to {outside} quads")
    return issues


def start(engine_class, run: Run):
    """A fresh store with the bystander (if any) stored and the first state created."""
    engine = engine_class()
    if run.preload:
        engine.update(run.preload)
    engine.update(run.create)
    return engine


def run_form(engine_class, family: Family, form: str, m: int, repeats: int = REPEATS) -> float:
    """The best time in milliseconds of `repeats` replaces. Raises WrongResult."""
    run = build_run(family, form, sized_states(family, m, repeats, form))
    engine = start(engine_class, run)
    best = float("inf")
    for number, step in enumerate(run.steps, 1):
        before = engine.outside(step.graphs, step.log)
        begin = time.perf_counter()
        engine.update(step.text)
        best = min(best, time.perf_counter() - begin)
        issues = verify(engine, step, before)
        if issues:
            raise WrongResult(f"{engine_class.name}/{family.name}/{form}/M={m} replace {number}: " + "; ".join(issues))
    return best * 1000


# ---- the edge cases ------------------------------------------------------------------------------------------------------

EDGE_PAYLOAD = 50
EDGE_CASES = (
    ("E1", "M = 0 then N = 50"), ("E2", "M = 50 then N = 0"), ("E3", "M = 0 then N = 0"), ("E4", "M = 50 then the identical 50"),
    ("E5", "E1 with the root in no triple, and the bare sweep counted"),
)
EDGE_FORMS = ("R0", "R1-candidate", "R2-values-candidate")
FULL_EDGE_ENGINES = ("oxigraph",)
"""The engines that run the candidates in the edge cases. Another engine runs `R0` only."""


def edge_states(family: Family, case: str) -> list:
    full = family.state(EDGE_PAYLOAD, 1)
    return {"E1": [set(), full], "E2": [full, set()], "E3": [set(), set()], "E4": [full, set(full)], "E5": [set(), full]}[case]


MENTIONS_ROOT = "SELECT (COUNT(*) AS ?n) WHERE {{ GRAPH <{g}> {{ {{ <{r}> ?p ?o }} UNION {{ ?s ?p <{r}> }} }} }}"
"""The triples of the data graph that mention the root, as subject or object."""


def run_edge(engine_class, family: Family, case: str, form: str, *, detail: list | None = None) -> str:
    """One edge case on a fresh store, checked by `verify`: `pass`, `wrong: <reasons>` or `error: <message>`. An update the store refuses is an error and not worked around. `detail` collects what the engine reports about the
    aggregate's graph after an empty replace (TSD-50)."""
    run = build_run(family, form, edge_states(family, case))
    try:
        engine = start(engine_class, run)
        if case == "E5":
            mentions = engine.count(MENTIONS_ROOT.format(r=family.root, g=family.graph))
            if mentions:
                return f"wrong: the root is in {mentions} triples of the data graph before the replace"
        for step in run.steps:
            before = engine.outside(step.graphs, step.log)
            engine.update(step.text)
            if detail is not None and not step.expect_root - set(step.bystander):
                detail.append(f"graph listed after: {'yes' if engine.listed(step.root_graph) else 'no'}")
            issues = verify(engine, step, before)
            if issues:
                return "wrong: " + "; ".join(issues)
    except Exception as error:
        return f"error: {type(error).__name__}: {' '.join(str(error).split())[:300]}"
    return "pass" + (f" ({'; '.join(detail)})" if detail else "")


def edge_cell(engine_class, family: Family, case: str, form: str, snapshot: bool) -> str:
    if form != "R0" and engine_class.name not in FULL_EDGE_ENGINES:
        return "not run: per-solution store (P1)" if form == "R2-values-candidate" else "not run: R0 only on this engine"
    if form == "R2-values-candidate" and not snapshot:
        return "not run: per-solution store (P1)"
    return run_edge(engine_class, family, case, form, detail=[] if case == "E2" else None)


def bare_sweep(engine_class, family: Family) -> tuple | str:
    """With the root in no triple, how many solutions the bare sweep gives, with and without `?s ?p ?o`. Returns (with, without) or `error: <message>`."""
    run = build_run(family, "R0", edge_states(family, "E5"))
    try:
        engine = start(engine_class, run)
        return engine.count(family.sweep_query(True)), engine.count(family.sweep_query(False))
    except Exception as error:
        return f"error: {type(error).__name__}: {' '.join(str(error).split())[:300]}"


def sweep_time(engine_class, family: Family, m: int) -> str:
    """The best of three timings of the bare sweep over the aggregate at size M, with the count it gave, which must be M."""
    run = build_run(family, "R0", sized_states(family, m, 1))
    engine = start(engine_class, run)
    query, best, seen = family.sweep_query(True), float("inf"), 0
    for _ in range(3):
        begin = time.perf_counter()
        seen = engine.count(query)
        best = min(best, time.perf_counter() - begin)
    if seen != m:
        raise WrongResult(f"{engine_class.name}/{family.name}: the bare sweep counted {seen} at M={m}")
    return f"{best * 1000:.1f} (count {seen})"


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
    family = named_family()
    run = build_run(family, "R2-candidate", sized_states(family, m))
    engine = start(RdflibEngine, run)
    for number, step in enumerate(run.steps, 1):
        before = engine.outside(step.graphs, step.log)
        engine.update(step.text)
        issues = verify(engine, step, before)
        if issues:
            return f"wrong at replace {number}: " + "; ".join(issues)
    return "right"


def witness() -> list:
    with ThreadPoolExecutor(max_workers=len(SEEDS)) as pool:
        return list(zip(SEEDS, pool.map(lambda seed: _child(["--witness-child"], seed), SEEDS)))


# ---- the operations for another runtime ---------------------------------------------------------------------------------

SWEEP_SIZES = (3000, 10000)


def count_query(pattern: str) -> str:
    """A `COUNT(*)` over `pattern`, which must bind a variable. RDF4J 6.1.0 counts 0 for a pattern with no variable that matches (TSD-48)."""
    return "SELECT (COUNT(*) AS ?n) WHERE { " + pattern + " }"


def _nt_lines(triples: set) -> list:
    return [f'<{s}> <{p}> {term(o)} .' for s, p, o in sorted(triples)]


def outside_query(step: Step) -> str:
    names = ", ".join(f"<{g}>" for g in sorted(step.graphs))
    return count_query(f'GRAPH ?g {{ ?s ?p ?o }} FILTER(?g NOT IN ({names}) && !STRSTARTS(STR(?g), "{step.log}"))')


def _emit_steps(run: Run) -> list:
    steps = []
    for step in run.steps:
        row = f"GRAPH <{step.meta}> {{ <{step.root}> <{PAT}%s> ?q FILTER(%s) }}"
        steps.append({
            "text": step.text, "rootGraph": step.root_graph, "addGraph": step.add_graph, "delGraph": step.del_graph,
            "expect": {"root": _nt_lines(step.expect_root), "add": _nt_lines(step.expect_add), "del": _nt_lines(step.expect_del)},
            "counts": [
                {"query": count_query(row % ("seq", f'STR(?q) = "{step.seq}"')), "expect": 1},
                {"query": count_query(row % ("seq", f'STR(?q) = "{step.seq - 1}"')), "expect": 0},
                {"query": count_query(row % ("head", f"?q = <{step.new_rev}>")), "expect": 1},
                {"query": count_query(f"GRAPH <{step.meta}> {{ <{step.root}> <{PAT}head> ?q }}"), "expect": 1},
                {"query": count_query(f"GRAPH <{step.txn_graph}> {{ <{step.txn}> <{PAT}rev> ?q FILTER(?q = <{step.new_rev}>) }}"), "expect": 1},
            ],
            "outsideQuery": outside_query(step),
        })
    return steps


def emit_family(family: Family, sizes=SIZES, repeats: int = REPEATS) -> dict:
    runs = {}
    for m in sizes:
        built = {form: build_run(family, form, sized_states(family, m, repeats, form)) for form in family.forms}
        runs[str(m)] = {"create": built["R0"].create, "forms": {form: _emit_steps(run) for form, run in built.items()}}
    edges = {}
    for case, title in family.edge_cases:
        built = {form: build_run(family, form, edge_states(family, case)) for form in EDGE_FORMS}
        edges[case] = {"title": title, "create": built["R0"].create, "forms": {form: _emit_steps(run) for form, run in built.items()}}
    return {
        "root": family.root, "rootGraph": family.graph, "preload": family.preload, "sizes": list(sizes),
        "forms": [{"id": f, "label": FORMS[f], "candidate": f in CANDIDATES, "generated": f in GENERATED, "needsSnapshot": f in NEEDS_SNAPSHOT} for f in family.forms],
        "runs": runs, "edges": edges, "mentionsRoot": MENTIONS_ROOT.format(r=family.root, g=family.graph), "edgeForms": list(EDGE_FORMS),
        "sweep": {"with": family.sweep_query(True), "without": family.sweep_query(False), "sizes": list(SWEEP_SIZES)} if family.sweep else None,
    }


def emit_operations(sizes=SIZES, repeats: int = REPEATS, families=FAMILIES) -> dict:
    """Everything a runtime other than Python needs to repeat this benchmark on its own store, for each family: for each size the create and, for each form, the replaces with their parameters substituted and their slots
    filled, and the checks that say each replace did what it should. A check is a count query with its expected count, or a graph with the expected triples as N-Triples lines to compare as a set. The edge cases are
    scenarios of the same shape, and the composite family carries its bare sweep queries. The runtime asserts the checks and never judges time."""
    return {"repeats": repeats, "families": {name: emit_family(family_named(name), sizes, repeats) for name in families}}


def write_operations(path: Path, doc: dict) -> None:
    """Writes the index to `path` and each sized run to a file of its own in `operations/` beside it, which the index names. All the sizes in one file came to 100 MB, which every measurement in the JVM runner would parse again."""
    folder = path.parent / "operations"
    folder.mkdir(exist_ok=True)
    for name, family in doc["families"].items():
        for m, run in list(family["runs"].items()):
            relative = f"operations/{name}-{m}.json"
            (path.parent / relative).write_text(json.dumps(run), encoding="utf-8", newline="\n")
            family["runs"][m] = relative
    path.write_text(json.dumps(doc, indent=1), encoding="utf-8", newline="\n")


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
    cells: list = field(default_factory=list)  # (family, engine, form, m, cell)
    edges: list = field(default_factory=list)  # (family, case, form, engine, cell)
    sweeps: list = field(default_factory=list)  # (engine, with, without), or (engine, error)
    sweep_times: list = field(default_factory=list)  # (engine, m, cell)
    witness: list = field(default_factory=list)  # (seed, outcome)
    generated_wrong: list = field(default_factory=list)


def job(kind: str, engine_name: str, family_name: str, form: str, m: int) -> str:
    """The child's side: one measurement. Prints `RESULT<tab>cell`, `WRONG<tab>reason` or `ERROR<tab>message`."""
    try:
        if kind == "sweep":
            return "RESULT\t" + sweep_time(engine_named(engine_name), family_named(family_name), m)
        return f"RESULT\t{run_form(engine_named(engine_name), family_named(family_name), form, m):.1f}"
    except WrongResult as error:
        return "WRONG\t" + str(error).replace("\n", " ")
    except Exception as error:
        return f"ERROR\t{type(error).__name__}: {' '.join(str(error).split())[:300]}"


def in_child(kind: str, engine_name: str, family_name: str, form: str, m: int, timeout: float) -> str:
    """One measurement in a child process with a wall-clock limit. Returns the cell, which is the milliseconds, `wrong: <reason>`, `error: <message>` or `did not finish: <reason>`."""
    try:
        done = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--job", f"{kind}|{engine_name}|{family_name}|{form}|{m}"], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return f"did not finish: no result within {timeout:.0f} s"
    for line in done.stdout.splitlines():
        if line.startswith("WRONG\t"):
            return "wrong: " + line[6:]
        if line.startswith("ERROR\t"):
            return "error: " + line[6:]
        if line.startswith("RESULT\t"):
            return line[7:]
    tail = " ".join(done.stderr.strip().splitlines()[-1:])
    return f"did not finish: the child exited {done.returncode}" + (f" ({tail})" if tail else "")


def quick_families(setting: str) -> set:
    """`REPLACE_FORMS_QUICK`: `1` for every family, or a comma list of the families to run quick."""
    return set(FAMILIES) if setting == "1" else {name for name in setting.split(",") if name}


def measure(families: list, max_r0: int, quick: set, timeout: float) -> Report:
    report = Report()
    engines = available_engines()
    snapshot = {}
    for engine_class in engines:
        report.p1[engine_class.name] = p1(engine_class)
        snapshot[engine_class.name] = is_snapshot(report.p1[engine_class.name])
    for name in families:
        family = family_named(name)
        for engine_class in engines:
            for case, _ in family.edge_cases:
                for form in EDGE_FORMS:
                    report.edges.append((name, case, form, engine_class.name, edge_cell(engine_class, family, case, form, snapshot[engine_class.name])))
            if family.sweep:
                report.sweeps.append((engine_class.name, bare_sweep(engine_class, family)))
        for engine_class in engines:
            sizes = [m for m in SIZES if name not in quick or m <= 1000]
            for form in family.forms:
                stopped = False
                for m in sizes:
                    if form in GENERATED and form not in DELTA_FORMS and m > max_r0:
                        cell = f"not run: above REPLACE_FORMS_MAX_R0 ({max_r0})"
                    elif form in NEEDS_SNAPSHOT and not snapshot[engine_class.name]:
                        cell = "not run: per-solution store (P1)"
                    elif stopped:
                        cell = "not run: a smaller size did not finish"
                    else:
                        print(f"progress: {name} {engine_class.name} {form} {m}", file=sys.stderr, flush=True)
                        cell = in_child("form", engine_class.name, name, form, m, timeout)
                        stopped = cell.startswith("did not finish")
                        if cell.startswith(("wrong:", "error:")) and form in GENERATED:
                            report.generated_wrong.append(f"{name}/{engine_class.name}/{form}/M={m}: {cell}")
                    report.cells.append((name, engine_class.name, form, m, cell))
            if family.sweep:
                for m in SWEEP_SIZES:
                    print(f"progress: {name} {engine_class.name} bare sweep {m}", file=sys.stderr, flush=True)
                    report.sweep_times.append((engine_class.name, m, in_child("sweep", engine_class.name, name, "sweep", m, timeout)))
    if "named-graph" in families:
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
    engines = list(report.p1)
    for name in FAMILIES:
        if not any(e[0] == name for e in report.edges):
            continue
        lines += ["", f"## Edge cases, {name} family", "", "| Case | Form | " + " | ".join(engines) + " |", "|---|---|" + "---|" * len(engines)]
        for case, title in family_named_cases(name):
            for form in EDGE_FORMS:
                cells = {e: c for n, cs, f, e, c in report.edges if n == name and cs == case and f == form}
                lines.append(f"| {case} {title} | {FORMS[form]} | " + " | ".join(cells.get(e, "") for e in engines) + " |")
    if report.sweeps:
        lines += ["", "## Composite family, the bare sweep with the root in no triple", "", "| Engine | Solutions of the sweep | Solutions without `?s ?p ?o` |", "|---|---|---|"]
        lines += [f"| {e} | {r[0]} | {r[1]} |" if isinstance(r, tuple) else f"| {e} | {r} | |" for e, r in report.sweeps]
    for name in FAMILIES:
        for engine in engines:
            body = [(form, m, cell) for n, e, form, m, cell in report.cells if n == name and e == engine]
            if body:
                lines += ["", f"## {name} family, {engine}, best of {REPEATS} replaces, milliseconds", "", "| Form | M (N equals M) | ms |", "|---|---|---|"]
                lines += [f"| {FORMS[form]} | {m:,} | {cell} |" for form, m, cell in body]
    if report.sweep_times:
        lines += ["", "## Composite family, the bare sweep alone, best of three, milliseconds", "", "| Engine | M | ms |", "|---|---|---|"]
        lines += [f"| {e} | {m:,} | {cell} |" for e, m, cell in report.sweep_times]
    if report.witness:
        lines += ["", "## Witness, R2 candidate on rdflib at M = 100 under each hash seed", "", "| PYTHONHASHSEED | Outcome |", "|---|---|"]
        lines += [f"| {seed} | {outcome} |" for seed, outcome in report.witness]
    return "\n".join(lines) + "\n"


def family_named_cases(name: str) -> tuple:
    return EDGE_CASES if name == "composite" else EDGE_CASES[:4]


def main() -> int:
    argv = sys.argv[1:]
    selected = os.environ.get("REPLACE_FORMS_FAMILY", "both")
    if "--family" in argv:
        at = argv.index("--family")
        selected = argv[at + 1]
        argv = argv[:at] + argv[at + 2:]
    families = list(FAMILIES) if selected == "both" else [selected]
    if len(argv) == 2 and argv[0] == "--emit":
        write_operations(Path(argv[1]), emit_operations(families=families))
        print(f"wrote {argv[1]}")
        return 0
    if len(argv) == 2 and argv[0] == "--job":
        kind, name, family, form, m = argv[1].split("|")
        print(job(kind, name, family, form, int(m)))
        return 0
    if len(argv) == 3 and argv[0] == "--p1-child":
        print(p1_kept(engine_named(argv[1]), argv[2]))
        return 0
    if argv == ["--witness-child"]:
        print(witness_outcome())
        return 0
    max_r0 = int(os.environ.get("REPLACE_FORMS_MAX_R0", "3000"))
    quick = quick_families(os.environ.get("REPLACE_FORMS_QUICK", ""))
    timeout = float(os.environ.get("REPLACE_FORMS_TIMEOUT", "900"))
    report = measure(families, max_r0, quick, timeout)
    text = render_report(report)
    (HERE / "report.md").write_text(text, encoding="utf-8", newline="\n")
    print(text)
    if report.generated_wrong:
        print("WRONG RESULT from a generated form:\n" + "\n".join(report.generated_wrong), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
