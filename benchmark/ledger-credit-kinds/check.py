# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""What a credit's kind and a stepwise credit ceiling cost an ancestor's balance read, on rdflib, Oxigraph and Jena (ADR-A124, STD-176).

The ledger posts a draw or credit once, at the account it names, and an ancestor's balance is a fold over its subtree's postings in the period named graphs. A credit now
carries a kind, and each account declares the kinds that restore it, all kinds by default. Each account also has a ceiling, its stated amount, and a credit never lifts
the account above it (law LD3). The account tree has depth 4: a root, 2 sections, 3 sublimits to a section and 4 contracts to a sublimit. The first section is a cap and
accepts recoveries only. A stream of postings, grouped into passes (a pass position and a micro-position within it), falls on random contracts. Each posting goes into a
named graph keyed by its sublimit and its period of `EVERY_POSITIONS` passes. Every ancestor is read at stated pass positions three ways.

* **plain**. The stated amount plus the signed sum of every posting in the subtree up to the point, every credit counted. Today's design, and the baseline.
* **kind-filtered**. The same, counting a credit only if the ancestor accepts its kind, by a join to the credit's kind. One SPARQL aggregate. The join has two forms, OPTIONAL and a UNION with the debits, and each backend reads the form that is cheaper on it.
* **stepwise**. The ancestor's running balance applied posting by posting in recorded order, each accepted credit clamped at the ceiling. SPARQL cannot clamp a running sum,
  so this is one ordered SELECT (`ORDER BY ?pos ?mp`) of the accepted postings, folded in Python. Its time includes the engine's sort, the transfer of every row and the loop.

**Pass criterion.** Every read on every backend equals the model's balance for that fold, account and read point, so the three folds differ from each other exactly
where the model says. The stored triples have the count the arithmetic gives. The model must itself tell the folds apart (the cap's plain and filtered balances differ,
and at a high credit share a ceiling binds), so a corpus that could not fail a fold is refused. A wrong balance or count fails the check. **Time never does.** The
seconds, the postings folded and the stored triples go to `report.json` and `report.md` here.

Run `mise run check:ledger-credit-kinds`. `LEDGER_KINDS_MAX` caps the number of postings, `LEDGER_KINDS_QUICK=1` runs the smallest size only. The Oxigraph store is a
temporary directory that is removed when the run ends, including on failure. Jena runs when its test kit jar is built (`mise run bootstrap:sparql-testkit`)."""

from __future__ import annotations

import gc
import json
import os
import platform
import random
import sys
import tempfile
import time
import traceback
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import pyoxigraph as ox
import rdflib

HERE = Path(__file__).resolve().parent
L = "https://example.org/ledger-kinds#"
XSD_INT = "http://www.w3.org/2001/XMLSchema#integer"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

SIZES = (1_000, 5_000, 20_000)
SHARES = (0.05, 0.30)
EVERY_POSITIONS = 200  # passes to a period graph
SECTIONS, SUBLIMITS_PER_SECTION, CONTRACTS_PER_SUBLIMIT = 2, 3, 4
STATED = (10**9, 10**5, 3 * 10**5, 10**6)  # ceiling by level, contract first
LEVELS = ("contract", "sublimit", "section", "root")
KINDS = ("Recovery", "Reinstatement", "WriteBack")
FOLDS = ("plain", "kind-filtered", "stepwise")
BACKENDS = ("rdflib", "oxigraph", "jena")
POSTING_TRIPLES = 8  # type, account, owner, key, position, micro-position, direction, amount
SEED = 20261111
DEBIT_MAX, CREDIT_MAX = 500, 1500
STEPWISE_BINDS_FROM = 0.30  # the credit share at and above which a ceiling must bind at some ancestor


class WrongResult(AssertionError):
    """A balance that is not the model's, a stored count that is not the arithmetic's, or a corpus that cannot tell the folds apart. The one way the check fails."""


def release_store() -> None:
    """Let go of an on-disk store before its folder is removed (see `benchmark/ledger-posting-cost/check.py`). A failing run's traceback keeps the finished frames alive, so clear them."""
    traceback.clear_frames(sys.exc_info()[2])
    gc.collect()


@dataclass(frozen=True)
class Account:
    iri: str
    level: int  # 0 contract, 1 sublimit, 2 section, 3 root
    parent: int | None
    accepts: tuple[str, ...] = ()  # kind IRIs. Empty means every kind, the default
    children: tuple[int, ...] = field(default=(), compare=False)

    @property
    def stated(self) -> int:
        return STATED[self.level]


def build_tree() -> list[Account]:
    """The root first, then sections, sublimits and contracts, so a parent precedes its child. The first section accepts recoveries only."""
    accounts = [Account("urn:acct:root", 3, None)]
    for s in range(SECTIONS):
        accounts.append(Account(f"urn:acct:sec{s}", 2, 0, (L + "Recovery",) if s == 0 else ()))
    for s in range(SECTIONS):
        for u in range(SUBLIMITS_PER_SECTION):
            accounts.append(Account(f"urn:acct:sub{s}-{u}", 1, 1 + s))
    first = 1 + SECTIONS
    for index in range(SECTIONS * SUBLIMITS_PER_SECTION):
        for c in range(CONTRACTS_PER_SUBLIMIT):
            accounts.append(Account(f"urn:acct:con{index}-{c}", 0, first + index))
    return accounts


TREE = build_tree()
ANCESTORS = [i for i, a in enumerate(TREE) if a.level > 0]


def chain(index: int) -> list[int]:
    out = [index]
    while TREE[out[-1]].parent is not None:
        out.append(TREE[out[-1]].parent)
    return out


def sublimits_under(index: int) -> list[int]:
    return [i for i, a in enumerate(TREE) if a.level == 1 and index in chain(i)]


@dataclass(frozen=True)
class Posting:
    pos: int
    micro: int
    contract: int
    debit: bool
    amount: int
    kind: str | None  # a kind IRI for a credit, None for a debit


def stream(count: int, credit_share: float) -> list[Posting]:
    """`count` postings in passes of one to three, on random contracts. Credits are split evenly across the three kinds and are larger than debits, so a ceiling binds at a high share."""
    rng = random.Random(SEED)
    contracts = [i for i, a in enumerate(TREE) if a.level == 0]
    out: list[Posting] = []
    pos = 0
    while len(out) < count:
        pos += 1
        for micro in range(min(rng.randint(1, 3), count - len(out))):
            debit = rng.random() >= credit_share
            out.append(Posting(pos, micro, rng.choice(contracts), debit, rng.randint(1, DEBIT_MAX if debit else CREDIT_MAX),
                               None if debit else L + rng.choice(KINDS)))
    return out


def accepted(account: Account, p: Posting) -> bool:
    return p.debit or not account.accepts or p.kind in account.accepts


@dataclass
class Model:
    """The balances by the plainest arithmetic: for each fold, ancestor and read point, independent of any query."""

    balance: dict[tuple[str, int, int], int]  # (fold, account, point) -> balance
    rows: dict[tuple[str, int, int], int]  # postings the fold counts


def run_model(postings: list[Posting], points: list[int]) -> Model:
    plain = {i: TREE[i].stated for i in ANCESTORS}
    kind = dict(plain)
    step = dict(plain)
    rows = {(f, i): 0 for f in FOLDS for i in ANCESTORS}
    model = Model({}, {})

    def snapshot(point: int) -> None:
        for i in ANCESTORS:
            for f, b in (("plain", plain), ("kind-filtered", kind), ("stepwise", step)):
                model.balance[(f, i, point)] = b[i]
                model.rows[(f, i, point)] = rows[(f, i)]

    todo = sorted(points)
    for p in postings:
        while todo and todo[0] < p.pos:
            snapshot(todo.pop(0))
        sign = -p.amount if p.debit else p.amount
        for i in chain(p.contract)[1:]:
            a = TREE[i]
            plain[i] += sign
            rows[("plain", i)] += 1
            if accepted(a, p):
                kind[i] += sign
                rows[("kind-filtered", i)] += 1
                rows[("stepwise", i)] += 1
                step[i] = step[i] - p.amount if p.debit else min(step[i] + p.amount, a.stated)
    while todo:
        snapshot(todo.pop(0))
    return model


def read_points(passes: int) -> list[int]:
    """A fifth and a half of the way through, and the last pass. None is made to fall on a period end, since a graph is filtered by position either way."""
    return sorted({max(1, passes // 5 + 7), max(1, passes // 2 + 3), passes})


def period_graph(sublimit: str, period: int) -> str:
    return f"urn:graph:{sublimit.rsplit(':', 1)[1]}:{period}"


def structure_triples() -> int:
    return sum(2 + (a.parent is not None) + len(a.accepts) for a in TREE)


def expected_stored(postings: list[Posting]) -> int:
    """Postings are 8 triples, plus one for a credit's kind."""
    return structure_triples() + POSTING_TRIPLES * len(postings) + sum(not p.debit for p in postings)


# a quad is (subject IRI, predicate IRI, object, graph IRI or None), an object is ("i", IRI), ("n", int) or ("s", text)
def quads(postings: list[Posting]):
    for a in TREE:
        yield a.iri, RDF_TYPE, ("i", L + "Account"), None
        yield a.iri, L + "statedAmount", ("n", a.stated), None
        if a.parent is not None:
            yield a.iri, L + "partOf", ("i", TREE[a.parent].iri), None
        for k in a.accepts:
            yield a.iri, L + "accepts", ("i", k), None
    for e, p in enumerate(postings, start=1):
        s, c = f"urn:posting:{e}", TREE[p.contract]
        g = period_graph(TREE[c.parent].iri, (p.pos - 1) // EVERY_POSITIONS)
        yield s, RDF_TYPE, ("i", L + "Posting"), g
        yield s, L + "account", ("i", c.iri), g
        yield s, L + "owner", ("i", "urn:owner:1"), g
        yield s, L + "key", ("s", f"k{e}"), g
        yield s, L + "position", ("n", p.pos), g
        yield s, L + "microPosition", ("n", p.micro), g
        yield s, L + "direction", ("i", L + ("Debit" if p.debit else "Credit")), g
        yield s, L + "amount", ("n", p.amount), g
        if not p.debit:
            yield s, L + "kind", ("i", p.kind), g


def jena_version() -> str:
    """The Jena ARQ the test kit's jar was built with, read from the jar the JVM runs."""
    import lattice_testing_jena as j

    with zipfile.ZipFile(j.jar()) as z:
        text = z.read("META-INF/maven/org.apache.jena/jena-arq/pom.properties").decode()
    return next(line.split("=", 1)[1] for line in text.splitlines() if line.startswith("version="))


def jena_available() -> bool:
    try:
        import lattice_testing_jena as j

        return j.available()
    except ImportError:
        return False


def available_backends() -> list[str]:
    return [b for b in BACKENDS if b != "jena" or jena_available()]


def versions() -> dict[str, str]:
    out = {"rdflib": rdflib.__version__, "pyoxigraph": ox.__version__}
    if jena_available():
        out["jena"] = jena_version()
    return out


class RdflibBackend:
    def __init__(self, directory):
        self.form = os.environ.get("LEDGER_KINDS_FORM") or DEFAULT_FORM["rdflib"]
        self.ds = rdflib.Dataset()

    def load(self, items) -> None:
        R = rdflib
        def term(o):
            return R.URIRef(o[1]) if o[0] == "i" else R.Literal(o[1], datatype=R.URIRef(XSD_INT)) if o[0] == "n" else R.Literal(o[1])
        self.ds.addN((R.URIRef(s), R.URIRef(p), term(o), self.ds.graph(R.URIRef(g)) if g else self.ds.default_graph) for s, p, o, g in items)

    def select(self, text: str) -> list[tuple]:
        return [tuple(None if t is None else str(t) for t in row) for row in self.ds.query(text)]

    def count(self) -> int:
        return sum(len(g) for g in self.ds.graphs())

    def close(self) -> None:
        pass


class OxigraphBackend:
    def __init__(self, directory):
        self.form = os.environ.get("LEDGER_KINDS_FORM") or DEFAULT_FORM["oxigraph"]
        self.store = ox.Store(directory)

    def load(self, items) -> None:
        def term(o):
            return ox.NamedNode(o[1]) if o[0] == "i" else ox.Literal(str(o[1]), datatype=ox.NamedNode(XSD_INT)) if o[0] == "n" else ox.Literal(o[1])
        self.store.bulk_extend(ox.Quad(ox.NamedNode(s), ox.NamedNode(p), term(o), ox.NamedNode(g) if g else ox.DefaultGraph()) for s, p, o, g in items)
        self.store.flush()

    def select(self, text: str) -> list[tuple]:
        return [tuple(None if t is None else t.value for t in row) for row in self.store.query(text)]

    def count(self) -> int:
        return len(self.store)

    def close(self) -> None:
        self.store = None


class JenaBackend:
    def __init__(self, directory):
        from lattice_testing_jena import JenaStore

        self.form = os.environ.get("LEDGER_KINDS_FORM") or DEFAULT_FORM["jena"]
        self.store = JenaStore()

    def load(self, items) -> None:
        R = rdflib
        def term(o):
            return R.URIRef(o[1]) if o[0] == "i" else R.Literal(o[1], datatype=R.URIRef(XSD_INT)) if o[0] == "n" else R.Literal(o[1])
        batch = []
        for s, p, o, g in items:
            batch.append((R.URIRef(s), R.URIRef(p), term(o), R.URIRef(g) if g else None))
            if len(batch) >= 20_000:
                self.store.add_all(batch)
                batch = []
        self.store.add_all(batch)

    def select(self, text: str) -> list[tuple]:
        names, rows = self.store.solutions(text)
        return [tuple(None if n not in r else str(r[n]) for n in names) for r in rows]

    def count(self) -> int:
        (row,) = self.select("SELECT (COUNT(*) AS ?n) WHERE { { ?s ?p ?o } UNION { GRAPH ?g { ?s ?p ?o } } }")
        return int(row[0])

    def close(self) -> None:
        self.store.close()


BACKEND_CLASS = {"rdflib": RdflibBackend, "oxigraph": OxigraphBackend, "jena": JenaBackend}

PREFIX = f"PREFIX l: <{L}> "
# a credit counts only if the account declares no kinds (all of them restore it) or declares the credit's kind
KIND_FILTER = "FILTER(?d = l:Debit || NOT EXISTS {{ <{acct}> l:accepts ?z }} || EXISTS {{ <{acct}> l:accepts ?k }})"
# two forms of the join to the credit's kind. Which is cheaper depends on the engine (see the README), so each backend reads the form that suits it, and LEDGER_KINDS_FORM forces one on all
KIND_JOIN = {"optional": "OPTIONAL { ?p l:kind ?k } ", "union": "{ ?p l:direction l:Debit } UNION { ?p l:kind ?k } "}
DEFAULT_FORM = {"rdflib": "optional", "oxigraph": "union", "jena": "optional"}
SIGNED = "BIND(IF(?d = l:Debit, -?a, ?a) AS ?signed)"


def graphs_for(index: int, point: int) -> str:
    """The VALUES list of the period graphs of the account's sublimits that hold passes up to the point."""
    last = (point - 1) // EVERY_POSITIONS
    return " ".join(f"<{period_graph(TREE[u].iri, n)}>" for u in sublimits_under(index) for n in range(last + 1))


def scan(index: int, point: int, with_kind: bool, form: str) -> str:
    """The postings of the subtree up to the point. Every period graph is taken whole, and the position bound is a FILTER inside the graph."""
    kind = KIND_JOIN[form] if with_kind else ""
    return (f"{{ VALUES ?g {{ {graphs_for(index, point)} }} GRAPH ?g {{ ?p l:position ?pos ; l:microPosition ?mp ; l:direction ?d ; l:amount ?a . "
            f"FILTER(?pos <= {point}) {kind}}} }}")


def stated_amount(backend, index: int) -> int:
    (row,) = backend.select(f"{PREFIX}SELECT ?s WHERE {{ <{TREE[index].iri}> l:statedAmount ?s }}")
    return int(row[0])


def apply_credit(balance: int, amount: int, stated: int) -> int:
    """A credit never lifts an account above its stated amount (LD3)."""
    return min(balance + amount, stated)


def read(fold: str, backend, index: int, point: int) -> tuple[int, int]:
    """(the balance of the ancestor as of the point by the fold, how many postings the fold counted or transferred)."""
    base = stated_amount(backend, index)
    kind_filter = KIND_FILTER.format(acct=TREE[index].iri)
    if fold in ("plain", "kind-filtered"):
        with_kind = fold == "kind-filtered"
        text = (f"{PREFIX}SELECT (SUM(?signed) AS ?sum) (COUNT(?p) AS ?folded) WHERE {{ {scan(index, point, with_kind, backend.form)} "
                f"{kind_filter if with_kind else ''} {SIGNED} }}")
        (row,) = backend.select(text)
        return base + (int(row[0]) if row[0] is not None else 0), int(row[1])
    text = (f"{PREFIX}SELECT ?pos ?mp ?d ?a WHERE {{ {scan(index, point, True, backend.form)} {kind_filter} }} ORDER BY ?pos ?mp")
    balance, rows = base, backend.select(text)
    for _, _, d, amount in rows:
        balance = balance - int(amount) if d.endswith("#Debit") else apply_credit(balance, int(amount), base)
    return balance, len(rows)


@dataclass
class LevelRead:
    reads: int = 0
    seconds: float = 0.0
    rows: int = 0


@dataclass
class Measurement:
    backend: str
    events: int
    credit_share: float
    stored_triples: int
    kind_triples: int
    write_seconds: float
    form: str
    reads: dict[tuple[str, str], LevelRead] = field(default_factory=dict)  # (fold, level name) -> totals


def check_discriminates(model: Model, share: float, point: int) -> None:
    """Refuses a corpus on which a broken fold could not fail: the cap's plain and filtered balances must differ, and at a high credit share a ceiling must bind somewhere."""
    cap = next(i for i, a in enumerate(TREE) if a.accepts)
    if share > 0 and model.balance[("plain", cap, point)] == model.balance[("kind-filtered", cap, point)]:
        raise WrongResult(f"share {share}: the cap's plain and kind-filtered balances are equal at {point}, so a filter that ignores the kind could not be told")
    if share >= STEPWISE_BINDS_FROM and all(model.balance[("stepwise", i, point)] == model.balance[("kind-filtered", i, point)] for i in ANCESTORS):
        raise WrongResult(f"share {share}: no ceiling binds at any ancestor by {point}, so a fold that ignores the ceiling could not be told")


def run_backend(name: str, count: int, share: float, directory: str | None = None) -> Measurement:
    """Loads the history into the backend, reads every ancestor at every point by each fold, and checks each against the model."""
    postings = stream(count, share)
    points = read_points(postings[-1].pos)
    model = run_model(postings, points)
    check_discriminates(model, share, points[-1])
    with tempfile.TemporaryDirectory(prefix="ledger-credit-kinds-", dir=directory) as tmp:
        backend = BACKEND_CLASS[name](tmp)
        try:
            begin = time.perf_counter()
            backend.load(quads(postings))
            write = time.perf_counter() - begin
            stored = backend.count()
            if stored != expected_stored(postings):
                raise WrongResult(f"{name} {count}: stored {stored} triples, expected {expected_stored(postings)}")
            m = Measurement(name, count, share, stored, sum(not p.debit for p in postings), write, backend.form,
                            {(f, LEVELS[lv]): LevelRead() for f in FOLDS for lv in (1, 2, 3)})
            for point in points:
                for i in ANCESTORS:
                    for fold in FOLDS:
                        begin = time.perf_counter()
                        balance, rows = read(fold, backend, i, point)
                        seconds = time.perf_counter() - begin
                        if balance != model.balance[(fold, i, point)]:
                            raise WrongResult(f"{name} {count} share {share} {fold}: {TREE[i].iri} as of {point} reads {balance}, the model gives {model.balance[(fold, i, point)]}")
                        if rows != model.rows[(fold, i, point)]:
                            raise WrongResult(f"{name} {count} share {share} {fold}: {TREE[i].iri} as of {point} counts {rows} postings, the model gives {model.rows[(fold, i, point)]}")
                        r = m.reads[(fold, LEVELS[TREE[i].level])]
                        r.reads, r.seconds, r.rows = r.reads + 1, r.seconds + seconds, r.rows + rows
        finally:
            backend.close()
            backend = None
            release_store()
    return m


def run(sizes=SIZES, shares=SHARES, backends=None) -> list[Measurement]:
    out = []
    for count in sizes:
        for share in shares:
            for name in backends or available_backends():
                m = run_backend(name, count, share)
                out.append(m)
                print(f"{name:9} events {count:6} credits {share:4.0%} stored {m.stored_triples:7} write {m.write_seconds:6.2f} s  " + "  ".join(
                    f"{f} root {1000 * m.reads[(f, 'root')].seconds / m.reads[(f, 'root')].reads:8.2f} ms" for f in FOLDS), flush=True)
    return out


def environment() -> dict[str, str]:
    return {"date": time.strftime("%Y-%m-%d"), "python": platform.python_version(), "machine": f"{platform.system()} {platform.machine()}", **versions(),
            "depth": "4", "contracts": str(SECTIONS * SUBLIMITS_PER_SECTION * CONTRACTS_PER_SUBLIMIT), "passes_per_period": str(EVERY_POSITIONS), "seed": str(SEED),
            "jena_note": "" if jena_available() else "jena not run: the test kit jar is not built or there is no java"}


def _ms(r: LevelRead) -> float:
    return 1000 * r.seconds / r.reads


def write_report(measurements: list[Measurement], directory: Path = HERE) -> None:
    rows = [{"backend": m.backend, "events": m.events, "credit_share": m.credit_share, "stored_triples": m.stored_triples, "kind_triples": m.kind_triples, "kind_join": m.form,
             "write_seconds": m.write_seconds,
             "reads": {f"{f}/{lv}": {"reads": r.reads, "mean_ms": _ms(r), "mean_rows": r.rows / r.reads} for (f, lv), r in m.reads.items()},
             "factor_vs_plain": {f: sum(r.seconds for (g, _), r in m.reads.items() if g == f) / sum(r.seconds for (g, _), r in m.reads.items() if g == "plain")
                                 for f in FOLDS}} for m in measurements]
    data = {"environment": environment(), "measurements": rows}
    (directory / "report.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    levels = LEVELS[1:]
    head = "| backend | kind join | events | credits | fold | stored | " + " | ".join(f"{lv} ms | {lv} rows" for lv in levels) + " | time vs plain |"
    lines = ["# Ledger credit kinds (generated)", "", "```", json.dumps(data["environment"]), "```", "", head, "|---|---|---|---|---|---|" + "---|---|" * len(levels) + "---|"]
    for r in rows:
        for f in FOLDS:
            cells = " | ".join(f"{r['reads'][f'{f}/{lv}']['mean_ms']:.2f} | {r['reads'][f'{f}/{lv}']['mean_rows']:.0f}" for lv in levels)
            lines.append(f"| {r['backend']} | {r['kind_join']} | {r['events']} | {r['credit_share']:.0%} | {f} | {r['stored_triples']} | {cells} | {r['factor_vs_plain'][f]:.2f} |")
    (directory / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    cap = int(os.environ.get("LEDGER_KINDS_MAX", SIZES[-1]))
    sizes = [s for s in SIZES if s <= cap] or [cap]
    if os.environ.get("LEDGER_KINDS_QUICK"):
        sizes = sizes[:1]
    try:
        measurements = run(sizes)
    except WrongResult as error:
        print(f"WRONG RESULT: {error}", file=sys.stderr)
        return 1
    write_report(measurements)
    print(json.dumps(environment()))
    print(f"report written to {HERE / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
