# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""What a credit's kind, a stepwise credit ceiling, checkpoints and a shortcut cost an ancestor's balance read, on rdflib, Oxigraph and Jena (ADR-A124, STD-176).

The ledger posts a draw or credit once, at the account it names, and an ancestor's balance is a fold over its subtree's postings in the period named graphs. A credit may
carry a kind, and each account declares the kinds that restore it, all kinds by default. Each account also has a ceiling, its stated amount, and a credit never lifts the
account above it (law LD3). A credit is clamped at the account it is posted to, and the clamped amount, the credit as applied there, is stored on the credit (`l:applied`)
and is what an ancestor folds. The account tree has depth 4: a root, 2 sections, 3 sublimits to a section and 4 contracts to a sublimit. The first section is a cap and
accepts recoveries only. A credit with no kind is posted only on a path where no account restricts kinds. A stream of postings, grouped into passes (a pass position and a
micro-position within it), falls on random contracts. Each posting goes into a named graph keyed by its sublimit and its period of `EVERY_POSITIONS` passes. At each period
close a checkpoint is written as data, the balance of every account by each of the three folds, in the graph `urn:graph:checkpoint:<period>`. Every ancestor is read at
stated pass positions, each read from the start of history and from the last checkpoint at or before the point.

* **plain**. The stated amount plus the signed sum of every posting's offered amount in the subtree up to the point, every credit counted. Today's design, and the baseline.
* **kind-filtered**. The same, counting a credit only if the ancestor accepts its kind, by a join to the credit's kind. One SPARQL aggregate. The join has two forms, OPTIONAL
  and a UNION with the debits and the credits that carry no kind, and each backend reads the form that is cheaper on it.
* **stepwise**. The ancestor's running balance applied posting by posting in recorded order, each accepted credit as applied at its drawn account and clamped at the ceiling.
  SPARQL cannot clamp a running sum, so this is one ordered SELECT (`ORDER BY ?pos ?mp`) of the accepted postings, folded in Python. Its time is split into the ordered query
  with the transfer of its rows, and the loop.
* **shortcut**. The kind-filtered aggregate from the stepwise checkpoint, then a check, and the stepwise fold only where the check fails. See `shortcut_sound`.

**Pass criterion.** Every read on every backend, from the start and from the checkpoint, equals the model's balance for that fold, account and read point, so the folds differ
from each other exactly where the model says. The shortcut equals the model's stepwise balance. The stored triples have the count the arithmetic gives. The model must itself
tell the folds apart (the cap's plain and filtered balances differ, a kindless credit exists, and at a high credit share a clamp binds at a contract), so a corpus that could
not fail a fold is refused. A wrong balance or count fails the check. **Time never does.**

Run `mise run check:ledger-credit-kinds`. `LEDGER_KINDS_MAX` caps the number of postings, `LEDGER_KINDS_QUICK=1` runs the smallest size only, `LEDGER_KINDS_FORM` forces a kind
join form and `LEDGER_KINDS_REPORT_DIR` writes the report elsewhere. `check.py --emit <dir>` writes the corpora and the expected balances for the native Jena caller
(`benchmark/ledger-credit-kinds-jvm`), and `check.py --merge` adds that caller's timings to the report. The Oxigraph store is a temporary directory that is removed when the
run ends, including on failure. Jena runs when its test kit jar is built (`mise run bootstrap:sparql-testkit`)."""

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
JVM_REPORT = HERE.parent / "ledger-credit-kinds-jvm" / "report.json"
L = "https://example.org/ledger-kinds#"
XSD_INT = "http://www.w3.org/2001/XMLSchema#integer"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

SIZES = (1_000, 5_000, 20_000)
SHARES = (0.05, 0.30)
EVERY_POSITIONS = 200  # passes to a period graph, and between checkpoints
SECTIONS, SUBLIMITS_PER_SECTION, CONTRACTS_PER_SUBLIMIT = 2, 3, 4
STATED = (10**9, 10**5, 3 * 10**5, 10**6)  # ceiling by level, contract first
LEVELS = ("contract", "sublimit", "section", "root")
KINDS = ("Recovery", "Reinstatement", "WriteBack")
FOLDS = ("plain", "kind-filtered", "stepwise")
MODEL_FOLDS = FOLDS + ("applied", "sum-with-cuts")  # applied: the kind-filtered sum of applied amounts with no cuts. sum-with-cuts: that less the cuts recorded at the account
MODES = ("full", "checkpointed")
BACKENDS = ("rdflib", "oxigraph", "jena")
POSTING_TRIPLES = 8  # type, account, owner, key, position, micro-position, direction, amount
CHECKPOINT_TRIPLES = 5  # account, position and the three balances
CP_GRAPH = "urn:graph:checkpoint:{k}"
SEED = 20261111
DEBIT_MAX, CREDIT_MAX = 500, 1500
KINDLESS_SHARE = 0.25  # of the credits on a path where no account restricts kinds
STEPWISE_BINDS_FROM = 0.30  # the credit share at and above which a clamp must bind at some contract
UPPER_SHARE = 0.5  # two-level corpus: the share of credits posted at a sublimit or section on the drawn contract's path, where it accepts the kind, instead of at the contract
CUT_TRIPLES = 3  # a cut: the posting it belongs to, the ancestor it is at, its value
CUT_FOLDS = ("kind-filtered", "stepwise", "sum-with-cuts")
CORPUS_ONE, CORPUS_TWO = "one-level", "two-level"


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
CONTRACTS = [i for i, a in enumerate(TREE) if a.level == 0]
BY_IRI = {a.iri: i for i, a in enumerate(TREE)}


def chain(index: int) -> list[int]:
    out = [index]
    while TREE[out[-1]].parent is not None:
        out.append(TREE[out[-1]].parent)
    return out


def sublimits_under(index: int) -> list[int]:
    return [i for i, a in enumerate(TREE) if a.level == 1 and index in chain(i)]


def contracts_under(index: int) -> list[int]:
    return [i for i in CONTRACTS if index in chain(i)]


def unrestricted(contract: int) -> bool:
    """True where no account on the contract's path restricts the kinds, the only place a credit may carry no kind."""
    return all(not TREE[i].accepts for i in chain(contract))


@dataclass(frozen=True)
class Posting:
    pos: int
    micro: int
    contract: int  # the account posted to. In the two-level corpus a credit may be posted at a sublimit or section, and then it is not a contract
    debit: bool
    amount: int
    kind: str | None  # a kind IRI for a credit, None for a debit or a credit with no kind
    applied: int = 0  # for a credit, the amount as applied at its drawn account
    cuts: tuple[tuple[int, int], ...] = ()  # for a credit, (ancestor, value) where an accepting ancestor had less room than `applied`


def clamp_at_drawn(balance: int, amount: int, stated: int) -> int:
    """The credit as applied at the account it is posted to. It never lifts the account above its stated amount (LD3)."""
    return min(amount, stated - balance)


def stream(count: int, credit_share: float) -> list[Posting]:
    """`count` postings in passes of one to three, on random contracts. Credits are split evenly across the three kinds, a quarter of those on an unrestricted path carry no kind, and
    credits are larger than debits, so a ceiling binds at a high share. A credit's applied amount is clamped at the contract it is posted to."""
    rng, kind_rng = random.Random(SEED), random.Random(SEED + 1)
    out: list[Posting] = []
    balance = {c: TREE[c].stated for c in CONTRACTS}
    pos = 0
    while len(out) < count:
        pos += 1
        for micro in range(min(rng.randint(1, 3), count - len(out))):
            debit = rng.random() >= credit_share
            contract, amount = rng.choice(CONTRACTS), 0
            amount = rng.randint(1, DEBIT_MAX if debit else CREDIT_MAX)
            kind = None if debit else L + rng.choice(KINDS)
            applied = amount
            if debit:
                balance[contract] -= amount
            else:
                if kind_rng.random() < KINDLESS_SHARE and unrestricted(contract):
                    kind = None
                applied = clamp_at_drawn(balance[contract], amount, TREE[contract].stated)
                balance[contract] += applied
            out.append(Posting(pos, micro, contract, debit, amount, kind, applied))
    return out


def accepts_kind(account: Account, kind: str | None) -> bool:
    return not account.accepts or kind in account.accepts


def accepted(account: Account, p: Posting) -> bool:
    return p.debit or accepts_kind(account, p.kind)


def settle_debit(step: list[int], contract: int, amount: int) -> None:
    for i in chain(contract):
        step[i] -= amount


def settle_credit(step: list[int], at: int, amount: int, kind: str | None) -> tuple[int, tuple[tuple[int, int], ...]]:
    """The writer's step for a credit posted at account `at`, which holds the stepwise balance `step` of every account. The credit is applied at `at` up to its room. Each accepting ancestor then
    takes up to its own room, stepwise in the law, and where it takes less than was applied the difference is a cut at that ancestor. Returns (applied, cuts) and moves `step`."""
    applied = clamp_at_drawn(step[at], amount, TREE[at].stated)
    cuts = []
    for i in chain(at):
        if accepts_kind(TREE[i], kind):
            take = min(applied, TREE[i].stated - step[i])
            step[i] += take
            if take < applied:
                cuts.append((i, applied - take))
    return applied, tuple(cuts)


def stream_two_level(count: int, credit_share: float) -> list[Posting]:
    """The same draws as `stream` (same passes, debits, contracts, amounts and kinds), but a share `UPPER_SHARE` of the credits is posted at the sublimit or section on the drawn contract's path,
    chosen at random among those that accept its kind, and the rest at the contract. The writer holds the stepwise balance of every account and records the applied amount and the cuts."""
    rng, kind_rng, place_rng = random.Random(SEED), random.Random(SEED + 1), random.Random(SEED + 2)
    out: list[Posting] = []
    step = [a.stated for a in TREE]
    pos = 0
    while len(out) < count:
        pos += 1
        for micro in range(min(rng.randint(1, 3), count - len(out))):
            debit = rng.random() >= credit_share
            contract = rng.choice(CONTRACTS)
            amount = rng.randint(1, DEBIT_MAX if debit else CREDIT_MAX)
            kind = None if debit else L + rng.choice(KINDS)
            if debit:
                settle_debit(step, contract, amount)
                out.append(Posting(pos, micro, contract, True, amount, None))
                continue
            if kind_rng.random() < KINDLESS_SHARE and unrestricted(contract):
                kind = None
            candidates = [i for i in chain(contract)[1:3] if accepts_kind(TREE[i], kind)]
            at = place_rng.choice(candidates) if candidates and place_rng.random() < UPPER_SHARE else contract
            applied, cuts = settle_credit(step, at, amount, kind)
            out.append(Posting(pos, micro, at, False, amount, kind, applied, cuts))
    return out


@dataclass
class Model:
    """The balances by the plainest arithmetic: for each fold, account and read point, independent of any query."""

    balance: dict[tuple[str, int, int], int]  # (fold, account, point) -> balance
    rows: dict[tuple[str, int, int], int]  # postings the fold counts
    ancestor_binds: int = 0  # credits an ancestor's ceiling reduced, after the drawn account's clamp
    cuts: list = field(default_factory=list)  # (posting number from 1, ancestor, value) for each cut the stepwise law gives


def run_model(postings: list[Posting], points: list[int]) -> Model:
    n = len(TREE)
    plain = [a.stated for a in TREE]
    kind, step, applied = list(plain), list(plain), list(plain)
    cut = [0] * n
    rows = {(f, i): 0 for f in MODEL_FOLDS for i in range(n)}
    model = Model({}, {})

    def snapshot(point: int) -> None:
        for i in range(n):
            for f, b in (("plain", plain), ("kind-filtered", kind), ("stepwise", step), ("applied", applied), ("sum-with-cuts", [x - y for x, y in zip(applied, cut)])):
                model.balance[(f, i, point)] = b[i]
                model.rows[(f, i, point)] = rows[(f, i)]

    todo = sorted(set(points))
    for e, p in enumerate(postings, start=1):
        while todo and todo[0] < p.pos:
            snapshot(todo.pop(0))
        sign = -p.amount if p.debit else p.amount
        restored = 0 if p.debit else min(p.amount, TREE[p.contract].stated - step[p.contract])  # the account's clamp where it is posted, by the model's own arithmetic
        for i in chain(p.contract):
            a = TREE[i]
            plain[i] += sign
            rows[("plain", i)] += 1
            if accepted(a, p):
                kind[i] += sign
                for f in ("kind-filtered", "stepwise", "applied", "sum-with-cuts"):
                    rows[(f, i)] += 1
                if p.debit:
                    step[i] -= p.amount
                    applied[i] -= p.amount
                else:
                    applied[i] += restored
                    if step[i] + restored > a.stated:
                        model.ancestor_binds += 1
                        model.cuts.append((e, i, step[i] + restored - a.stated))
                        cut[i] += step[i] + restored - a.stated
                        rows[("sum-with-cuts", i)] += 1
                    step[i] = min(step[i] + restored, a.stated)
    while todo:
        snapshot(todo.pop(0))
    return model


def read_points(passes: int) -> list[int]:
    """A fifth and a half of the way through, and the last pass. None is made to fall on a period end, since a graph is filtered by position either way."""
    return sorted({max(1, passes // 5 + 7), max(1, passes // 2 + 3), passes})


def closes(passes: int) -> list[int]:
    """The pass position of each period close that falls within the history. Checkpoint k is at close k + 1."""
    return [EVERY_POSITIONS * j for j in range(1, passes // EVERY_POSITIONS + 1)]


def graph_owner(contract: int) -> int:
    """The account whose name keys the period graphs a posting goes in. A contract's postings go in its sublimit's graphs, and a credit posted at a sublimit or a section goes in that account's own."""
    return TREE[contract].parent if TREE[contract].level == 0 else contract


def sections_under(index: int) -> list[int]:
    return [i for i, a in enumerate(TREE) if a.level == 2 and index in chain(i)]


def period_graph(sublimit: str, period: int) -> str:
    return f"urn:graph:{sublimit.rsplit(':', 1)[1]}:{period}"


def checkpoint_balances(model: Model, positions: list[int]) -> dict[tuple[int, int], tuple[int, int, int]]:
    """The checkpoint written at each close: (period, account) -> (plain, kind-filtered, stepwise) balance, the last two already reflecting the filter and the clamp."""
    return {(j, i): tuple(model.balance[(f, i, pos)] for f in FOLDS) for j, pos in enumerate(positions) for i in range(len(TREE))}


def structure_triples() -> int:
    return sum(2 + (a.parent is not None) + len(a.accepts) for a in TREE)


def expected_stored(postings: list[Posting]) -> int:
    """Postings are 8 triples. A credit adds one for what was applied and, if it has a kind, one for the kind, and each cut it carries adds 3. A checkpoint is 5 triples per account."""
    credits = [p for p in postings if not p.debit]
    return (structure_triples() + POSTING_TRIPLES * len(postings) + len(credits) + sum(p.kind is not None for p in credits) + CUT_TRIPLES * sum(len(p.cuts) for p in credits)
            + CHECKPOINT_TRIPLES * len(TREE) * len(closes(postings[-1].pos)))


# a quad is (subject IRI, predicate IRI, object, graph IRI or None), an object is ("i", IRI), ("n", int) or ("s", text)
def quads(postings: list[Posting], cps: dict):
    for a in TREE:
        yield a.iri, RDF_TYPE, ("i", L + "Account"), None
        yield a.iri, L + "statedAmount", ("n", a.stated), None
        if a.parent is not None:
            yield a.iri, L + "partOf", ("i", TREE[a.parent].iri), None
        for k in a.accepts:
            yield a.iri, L + "accepts", ("i", k), None
    for e, p in enumerate(postings, start=1):
        s = f"urn:posting:{e}"
        g = period_graph(TREE[graph_owner(p.contract)].iri, (p.pos - 1) // EVERY_POSITIONS)
        yield s, RDF_TYPE, ("i", L + "Posting"), g
        yield s, L + "account", ("i", TREE[p.contract].iri), g
        yield s, L + "owner", ("i", "urn:owner:1"), g
        yield s, L + "key", ("s", f"k{e}"), g
        yield s, L + "position", ("n", p.pos), g
        yield s, L + "microPosition", ("n", p.micro), g
        yield s, L + "direction", ("i", L + ("Debit" if p.debit else "Credit")), g
        yield s, L + "amount", ("n", p.amount), g
        if not p.debit:
            yield s, L + "applied", ("n", p.applied), g
            if p.kind is not None:
                yield s, L + "kind", ("i", p.kind), g
            for i, value in p.cuts:
                cut = f"urn:cut:{e}:{i}"
                yield cut, L + "cutOf", ("i", s), g
                yield cut, L + "cutAt", ("i", TREE[i].iri), g
                yield cut, L + "cutValue", ("n", value), g
    for (j, i), (pl, kd, st) in cps.items():
        s, g = f"urn:checkpoint:{j}:{i}", CP_GRAPH.format(k=j)
        yield s, L + "account", ("i", TREE[i].iri), g
        yield s, L + "position", ("n", EVERY_POSITIONS * (j + 1)), g
        yield s, L + "plainBalance", ("n", pl), g
        yield s, L + "kindBalance", ("n", kd), g
        yield s, L + "stepBalance", ("n", st), g


@dataclass
class Corpus:
    postings: list[Posting]
    points: list[int]
    positions: list[int]
    model: Model
    cps: dict


def build_corpus(count: int, share: float) -> Corpus:
    postings = stream(count, share)
    passes = postings[-1].pos
    points, positions = read_points(passes), closes(passes)
    model = run_model(postings, points + positions)
    return Corpus(postings, points, positions, model, checkpoint_balances(model, positions))


def expected(model: Model, fold: str, index: int, point: int, checkpointed: bool) -> tuple[int, int]:
    """(the balance, the postings folded). A checkpointed read folds only what comes after the last close at or before the point."""
    start = EVERY_POSITIONS * (point // EVERY_POSITIONS) if checkpointed else 0
    return model.balance[(fold, index, point)], model.rows[(fold, index, point)] - (model.rows[(fold, index, start)] if start else 0)


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
    upper = False  # whether the history holds credits posted at sections, so their graphs are read

    def __init__(self, directory):
        self.form = os.environ.get("LEDGER_KINDS_FORM") or DEFAULT_FORM["rdflib"]
        self.parts = (0.0, 0.0)
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
    upper = False  # whether the history holds credits posted at sections, so their graphs are read

    def __init__(self, directory):
        self.form = os.environ.get("LEDGER_KINDS_FORM") or DEFAULT_FORM["oxigraph"]
        self.parts = (0.0, 0.0)
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
    upper = False  # whether the history holds credits posted at sections, so their graphs are read

    def __init__(self, directory):
        from lattice_testing_jena import JenaStore

        self.form = os.environ.get("LEDGER_KINDS_FORM") or DEFAULT_FORM["jena"]
        self.parts = (0.0, 0.0)
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
# a credit counts only if the account declares no kinds (all of them restore it) or declares the credit's kind. A credit with no kind is posted only where no account restricts kinds
KIND_FILTER = "FILTER(?d = l:Debit || NOT EXISTS {{ <{acct}> l:accepts ?z }} || EXISTS {{ <{acct}> l:accepts ?k }})"
# two forms of the join to the credit's kind. Which is cheaper depends on the engine (see the README), so each backend reads the form that suits it, and LEDGER_KINDS_FORM forces one on all three.
# The union keeps a credit with no kind in its third branch. Without it such a credit matches neither of the first two and drops out of the fold.
KIND_JOIN = {"optional": "OPTIONAL { ?p l:kind ?k } ",
             "union": "{ ?p l:direction l:Debit } UNION { ?p l:kind ?k } UNION { ?p l:direction l:Credit . FILTER NOT EXISTS { ?p l:kind ?z2 } } "}
UNCORRECTED_UNION = "{ ?p l:direction l:Debit } UNION { ?p l:kind ?k } "  # kept for the test that shows the check catches it
DEFAULT_FORM = {"rdflib": "optional", "oxigraph": "union", "jena": "optional"}
SIGNED = "BIND(IF(?d = l:Debit, -?a, ?a) AS ?signed)"


def graphs_for(index: int, point: int, first: int = 0, upper: bool = False) -> str:
    """The VALUES list of the period graphs of the account's sublimits that hold passes after period `first - 1` up to the point. Where credits are posted at sections too (`upper`), the graphs keyed by
    the sections in the account's subtree are listed as well, so a section's credit is read by that section and the root and by no sublimit."""
    last = (point - 1) // EVERY_POSITIONS
    owners = sublimits_under(index) + (sections_under(index) if upper else [])
    return " ".join(f"<{period_graph(TREE[u].iri, n)}>" for u in owners for n in range(first, last + 1))


def scan(index: int, point: int, with_kind: bool, form: str, first: int = 0, extra: str = "", upper: bool = False) -> str:
    """The postings of the subtree up to the point, from period `first`. Every period graph is taken whole, and the position bound is a FILTER inside the graph."""
    kind = KIND_JOIN[form] if with_kind else ""
    return (f"{{ VALUES ?g {{ {graphs_for(index, point, first, upper)} }} GRAPH ?g {{ ?p l:position ?pos ; l:microPosition ?mp ; l:direction ?d ; l:amount ?a . {extra}"
            f"FILTER(?pos <= {point}) {kind}}} }}")


def stated_amount(backend, index: int) -> int:
    (row,) = backend.select(f"{PREFIX}SELECT ?s WHERE {{ <{TREE[index].iri}> l:statedAmount ?s }}")
    return int(row[0])


def apply_credit(balance: int, amount: int, stated: int) -> int:
    """A credit never lifts an account above its stated amount (LD3)."""
    return min(balance + amount, stated)


def checkpoint(backend, index: int, k: int) -> dict[str, int]:
    """The balances the checkpoint of period k holds for the account, by fold."""
    (row,) = backend.select(f"{PREFIX}SELECT ?pl ?kd ?st WHERE {{ GRAPH <{CP_GRAPH.format(k=k)}> {{ ?c l:account <{TREE[index].iri}> ; "
                            f"l:plainBalance ?pl ; l:kindBalance ?kd ; l:stepBalance ?st }} }}")
    return dict(zip(FOLDS, map(int, row)))


def start_of(backend, index: int, point: int, checkpointed: bool, base: int) -> tuple[int, dict[str, int]]:
    """(the first period graph to fold, the balances the fold starts from). From the last checkpoint at or before the point, or from the stated amount."""
    k = point // EVERY_POSITIONS - 1
    if checkpointed and k >= 0:
        return k + 1, checkpoint(backend, index, k)
    return 0, {f: base for f in FOLDS}


def aggregate(backend, index: int, point: int, first: int, with_kind: bool) -> tuple[int, int]:
    kind_filter = KIND_FILTER.format(acct=TREE[index].iri)
    text = (f"{PREFIX}SELECT (SUM(?signed) AS ?sum) (COUNT(?p) AS ?folded) WHERE {{ {scan(index, point, with_kind, backend.form, first, upper=backend.upper)} "
            f"{kind_filter if with_kind else ''} {SIGNED} }}")
    (row,) = backend.select(text)
    return (int(row[0]) if row[0] is not None else 0), int(row[1])


def read(fold: str, backend, index: int, point: int, checkpointed: bool = False) -> tuple[int, int]:
    """(the balance of the ancestor as of the point by the fold, how many postings the fold counted or transferred). The stepwise fold leaves its two times in `backend.parts`."""
    backend.parts = (0.0, 0.0)
    base = stated_amount(backend, index)
    first, start = start_of(backend, index, point, checkpointed, base)
    if fold in ("plain", "kind-filtered"):
        total, folded = aggregate(backend, index, point, first, fold == "kind-filtered")
        return start[fold] + total, folded
    text = (f"{PREFIX}SELECT ?pos ?mp ?d ?a ?ap WHERE {{ {scan(index, point, True, backend.form, first, 'OPTIONAL { ?p l:applied ?ap } ', backend.upper)} "
            f"{KIND_FILTER.format(acct=TREE[index].iri)} }} ORDER BY ?pos ?mp")
    begin = time.perf_counter()
    balance, rows = start[fold], backend.select(text)
    fetched = time.perf_counter()
    for _, _, d, amount, applied in rows:
        balance = balance - int(amount) if d.endswith("#Debit") else apply_credit(balance, int(applied), base)
    backend.parts = (fetched - begin, time.perf_counter() - fetched)
    return balance, len(rows)


def shortcut_sound(balance: int, base: int, credits: dict[str, int], outstanding: dict[str, int]) -> bool:
    """Whether the kind-filtered aggregate is the stepwise balance. A credit is clamped only where it exceeds what is outstanding at its drawn contract, and a contract's outstanding draw
    at the start of the range bounds what its credits in the range can restore, since debits only add to it. So if each contract's credits of any kind in the range total no more than its outstanding
    draw at the start (from the stepwise checkpoint, and nothing from the start of history), no credit in the range was clamped at its drawn contract, the applied amounts are the offered
    ones the aggregate summed, and the ancestor cannot be lifted above its stated amount, since its outstanding draw is at least its contracts' together. The balance is also checked
    against the ceiling. Sufficient, not necessary, so the stepwise fold is still run where this fails."""
    return balance <= base and all(total <= outstanding.get(c, 0) for c, total in credits.items())


def read_shortcut(backend, index: int, point: int, checkpointed: bool = False) -> tuple[int, int, bool]:
    """(the balance, the postings folded, whether the stepwise fold was needed)."""
    base = stated_amount(backend, index)
    first, start = start_of(backend, index, point, checkpointed, base)
    total, folded = aggregate(backend, index, point, first, True)
    balance = start["stepwise"] + total
    credit_text = (f"{PREFIX}SELECT ?c (SUM(?a) AS ?cr) WHERE {{ {scan(index, point, False, backend.form, first, '?p l:account ?c . ', backend.upper)} FILTER(?d = l:Credit) }} GROUP BY ?c")
    credits = {c: int(t) for c, t in backend.select(credit_text)}
    outstanding: dict[str, int] = {}
    k = point // EVERY_POSITIONS - 1
    if checkpointed and k >= 0:
        stepped = backend.select(f"{PREFIX}SELECT ?c ?st WHERE {{ GRAPH <{CP_GRAPH.format(k=k)}> {{ ?x l:account ?c ; l:stepBalance ?st }} }}")
        outstanding = {c: TREE[BY_IRI[c]].stated - int(st) for c, st in stepped}
    if shortcut_sound(balance, base, credits, outstanding):
        return balance, folded, False
    balance, rows = read("stepwise", backend, index, point, checkpointed)
    return balance, folded + rows, True


@dataclass
class LevelRead:
    reads: int = 0
    seconds: float = 0.0
    rows: int = 0
    fetch_seconds: float = 0.0  # stepwise: the ordered query and the transfer of its rows
    loop_seconds: float = 0.0  # stepwise: the clamping loop
    fallbacks: int = 0  # shortcut: reads that needed the stepwise fold
    postings_seconds: float = 0.0  # sum-with-cuts: the aggregate over the postings
    cuts_seconds: float = 0.0  # sum-with-cuts: the aggregate over the cuts


@dataclass
class Measurement:
    backend: str
    events: int
    credit_share: float
    stored_triples: int
    kind_triples: int
    write_seconds: float
    form: str
    reads: dict[tuple[str, str], LevelRead] = field(default_factory=dict)  # (fold, level name) -> totals, read from the start of history
    cp_reads: dict[tuple[str, str], LevelRead] = field(default_factory=dict)  # the same, read from the last checkpoint
    shortcut: dict[tuple[str, str], LevelRead] = field(default_factory=dict)  # (mode, level name) -> totals
    notes: dict[str, int] = field(default_factory=dict)  # what the model expects, so a report says where the folds differ
    corpus: str = CORPUS_ONE


def check_discriminates(model: Model, share: float, point: int, postings: list[Posting] | None = None) -> None:
    """Refuses a corpus on which a broken fold could not fail: the cap's plain and filtered balances must differ, a credit with no kind must exist, and at a high credit share a clamp must
    bind at a contract, so the plain and stepwise balances differ there and the stepwise one differs from the filtered one at an ancestor."""
    cap = next(i for i, a in enumerate(TREE) if a.accepts)
    if share > 0 and model.balance[("plain", cap, point)] == model.balance[("kind-filtered", cap, point)]:
        raise WrongResult(f"share {share}: the cap's plain and kind-filtered balances are equal at {point}, so a filter that ignores the kind could not be told")
    if postings is not None and share > 0 and not any(not p.debit and p.kind is None for p in postings):
        raise WrongResult(f"share {share}: no credit has no kind, so a join that drops a credit with no kind could not be told")
    if share >= STEPWISE_BINDS_FROM:
        if all(model.balance[("plain", c, point)] == model.balance[("stepwise", c, point)] for c in CONTRACTS):
            raise WrongResult(f"share {share}: no clamp binds at any contract by {point}, so a missing clamp at the drawn account could not be told")
        if all(model.balance[("stepwise", i, point)] == model.balance[("kind-filtered", i, point)] for i in ANCESTORS):
            raise WrongResult(f"share {share}: no clamp reaches any ancestor by {point}, so a fold that ignores the applied amount could not be told")


def run_backend(name: str, count: int, share: float, directory: str | None = None) -> Measurement:
    """Loads the history and its checkpoints into the backend, reads every ancestor at every point by each fold, from the start and from the checkpoint, and checks each against the model."""
    corpus = build_corpus(count, share)
    postings, points, model = corpus.postings, corpus.points, corpus.model
    check_discriminates(model, share, points[-1], postings)
    last = points[-1]
    with tempfile.TemporaryDirectory(prefix="ledger-credit-kinds-", dir=directory) as tmp:
        backend = BACKEND_CLASS[name](tmp)
        try:
            begin = time.perf_counter()
            backend.load(quads(postings, corpus.cps))
            write = time.perf_counter() - begin
            stored = backend.count()
            if stored != expected_stored(postings):
                raise WrongResult(f"{name} {count}: stored {stored} triples, expected {expected_stored(postings)}")
            notes = {"contracts_clamped": sum(model.balance[("plain", c, last)] != model.balance[("stepwise", c, last)] for c in CONTRACTS),
                     "ancestors_where_stepwise_differs": sum(model.balance[("stepwise", i, last)] != model.balance[("kind-filtered", i, last)] for i in ANCESTORS),
                     "ancestors_where_filter_differs": sum(model.balance[("plain", i, last)] != model.balance[("kind-filtered", i, last)] for i in ANCESTORS),
                     "ancestor_clamps_binding": model.ancestor_binds, "credits_with_no_kind": sum(not p.debit and p.kind is None for p in postings),
                     "checkpoints": len(corpus.positions)}
            keys = [(f, LEVELS[lv]) for f in FOLDS for lv in (1, 2, 3)]
            m = Measurement(name, count, share, stored, sum(not p.debit and p.kind is not None for p in postings), write, backend.form,
                            {k: LevelRead() for k in keys}, {k: LevelRead() for k in keys}, {(mode, LEVELS[lv]): LevelRead() for mode in MODES for lv in (1, 2, 3)}, notes)
            for point in points:
                for i in ANCESTORS:
                    level = LEVELS[TREE[i].level]
                    for mode in MODES:
                        cp = mode == "checkpointed"
                        for fold in FOLDS:
                            begin = time.perf_counter()
                            balance, rows = read(fold, backend, i, point, cp)
                            seconds = time.perf_counter() - begin
                            want, want_rows = expected(model, fold, i, point, cp)
                            where = f"{name} {count} share {share} {mode} {fold}: {TREE[i].iri} as of {point}"
                            if balance != want:
                                raise WrongResult(f"{where} reads {balance}, the model gives {want}")
                            if rows != want_rows:
                                raise WrongResult(f"{where} counts {rows} postings, the model gives {want_rows}")
                            r = (m.cp_reads if cp else m.reads)[(fold, level)]
                            r.reads, r.seconds, r.rows = r.reads + 1, r.seconds + seconds, r.rows + rows
                            r.fetch_seconds, r.loop_seconds = r.fetch_seconds + backend.parts[0], r.loop_seconds + backend.parts[1]
                        begin = time.perf_counter()
                        balance, rows, fell_back = read_shortcut(backend, i, point, cp)
                        seconds = time.perf_counter() - begin
                        want = model.balance[("stepwise", i, point)]
                        if balance != want:
                            raise WrongResult(f"{name} {count} share {share} {mode} shortcut: {TREE[i].iri} as of {point} reads {balance}, the model gives {want}")
                        r = m.shortcut[(mode, level)]
                        r.reads, r.seconds, r.rows, r.fallbacks = r.reads + 1, r.seconds + seconds, r.rows + rows, r.fallbacks + fell_back
        finally:
            backend.close()
            backend = None
            release_store()
    return m


def postings_scan(index: int, point: int, first: int) -> str:
    """The debits, and the credits at the amount applied, of the subtree up to the point, as three branches of a UNION with no OPTIONAL inside the graph block (TSD-71). A debit, a credit with a kind
    and a credit with no kind are one branch each, so none is dropped. The account's kind filter is outside the graph block, where the account's own declarations are in the default graph."""
    head = "?p l:position ?pos ; l:direction"
    return (f"{{ VALUES ?g {{ {graphs_for(index, point, first, True)} }} GRAPH ?g {{ "
            f"{{ {head} l:Debit ; l:amount ?v . BIND(l:Debit AS ?d) FILTER(?pos <= {point}) }} UNION "
            f"{{ {head} l:Credit ; l:applied ?v ; l:kind ?k . BIND(l:Credit AS ?d) FILTER(?pos <= {point}) }} UNION "
            f"{{ {head} l:Credit ; l:applied ?v . BIND(l:Credit AS ?d) FILTER(?pos <= {point}) FILTER NOT EXISTS {{ ?p l:kind ?z2 }} }} }} }}")


def cuts_scan(index: int, point: int, first: int) -> str:
    """The cuts recorded at the account by credits up to the point, in the graphs the account reads. Only an accepting ancestor has a cut, so there is no kind filter. A cut has no position of its
    own, so it joins to the posting it belongs to, in the same graph."""
    return (f"{{ VALUES ?g {{ {graphs_for(index, point, first, True)} }} GRAPH ?g {{ ?c l:cutAt <{TREE[index].iri}> ; l:cutValue ?cv ; l:cutOf ?p . ?p l:position ?pos . FILTER(?pos <= {point}) }} }}")


def read_with_cuts(backend, index: int, point: int, checkpointed: bool = False) -> tuple[int, int, int]:
    """(the balance, the postings and cuts folded, the balance the postings alone give, which is the sum with no cuts). The stated amount, or the checkpoint's balance, plus the debits and the
    accepted credits at their applied amounts, less the cuts recorded at the account. Two aggregates, and `backend.parts` is the time of each."""
    base = stated_amount(backend, index)
    first, start = start_of(backend, index, point, checkpointed, base)
    begin = time.perf_counter()
    (row,) = backend.select(f"{PREFIX}SELECT (SUM(?signed) AS ?sum) (COUNT(?p) AS ?folded) WHERE {{ {postings_scan(index, point, first)} {KIND_FILTER.format(acct=TREE[index].iri)} {SIGNED.replace('?a', '?v')} }}")
    mid = time.perf_counter()
    (cut_row,) = backend.select(f"{PREFIX}SELECT (SUM(?cv) AS ?cut) (COUNT(?c) AS ?cuts) WHERE {{ {cuts_scan(index, point, first)} }}")
    backend.parts = (mid - begin, time.perf_counter() - mid)
    uncut = start["stepwise"] + (int(row[0]) if row[0] is not None else 0)
    cut = int(cut_row[0]) if cut_row[0] is not None else 0
    return uncut - cut, int(row[1]) + int(cut_row[1]), uncut


def check_discriminates_cuts(model: Model, share: float, point: int, postings: list[Posting]) -> None:
    """Refuses a two-level corpus that could not fail the sum with cuts. At a high credit share an ancestor's ceiling must bind, so a cut exists, and the sum of applied amounts with no cuts must
    differ from the stepwise balance at some ancestor, which is the defect the cut repairs."""
    check_discriminates(model, share, point, postings)
    if share >= STEPWISE_BINDS_FROM:
        if model.ancestor_binds == 0 or not any(p.cuts for p in postings):
            raise WrongResult(f"share {share}: no ancestor's ceiling binds in the two-level corpus, so a missing cut could not be told")
        if all(model.balance[("applied", i, point)] == model.balance[("stepwise", i, point)] for i in ANCESTORS):
            raise WrongResult(f"share {share}: the sum of applied amounts equals the stepwise balance at every ancestor by {point}, so the defect the cut repairs is not in the corpus")
    if [(e, i, v) for e, p in enumerate(postings, start=1) for i, v in p.cuts] != model.cuts:
        raise WrongResult(f"share {share}: the cuts the writer recorded are not the cuts the stepwise law gives")
    for i in range(len(TREE)):
        if model.balance[("sum-with-cuts", i, point)] != model.balance[("stepwise", i, point)]:
            raise WrongResult(f"share {share}: the model's sum with cuts is not its stepwise balance at {TREE[i].iri}")


def build_cut_corpus(count: int, share: float) -> Corpus:
    postings = stream_two_level(count, share)
    passes = postings[-1].pos
    points, positions = read_points(passes), closes(passes)
    model = run_model(postings, points + positions)
    return Corpus(postings, points, positions, model, checkpoint_balances(model, positions))


def run_backend_cuts(name: str, count: int, share: float, directory: str | None = None) -> Measurement:
    """The two-level corpus. Loads it into the backend and reads every ancestor at every point by the kind-filtered, stepwise and sum-with-cuts folds, from the start and from the checkpoint, and checks
    each against the model. The sum with cuts must equal the stepwise balance, and the postings alone, with no cuts, must equal the model's sum of applied amounts, which differs from it somewhere."""
    corpus = build_cut_corpus(count, share)
    postings, points, model = corpus.postings, corpus.points, corpus.model
    check_discriminates_cuts(model, share, points[-1], postings)
    last = points[-1]
    with tempfile.TemporaryDirectory(prefix="ledger-credit-kinds-", dir=directory) as tmp:
        backend = BACKEND_CLASS[name](tmp)
        backend.upper = True
        try:
            begin = time.perf_counter()
            backend.load(quads(postings, corpus.cps))
            write = time.perf_counter() - begin
            stored = backend.count()
            if stored != expected_stored(postings):
                raise WrongResult(f"{name} {count}: stored {stored} triples, expected {expected_stored(postings)}")
            credits, cut_credits = [p for p in postings if not p.debit], [p for p in postings if p.cuts]
            notes = {"credits": len(credits), "credits_posted_above_a_contract": sum(TREE[p.contract].level > 0 for p in credits), "credits_with_a_cut": len(cut_credits),
                     "cuts": sum(len(p.cuts) for p in postings), "cut_triples": CUT_TRIPLES * sum(len(p.cuts) for p in postings), "ancestor_clamps_binding": model.ancestor_binds,
                     "ancestors_where_uncut_differs": sum(model.balance[("applied", i, last)] != model.balance[("stepwise", i, last)] for i in ANCESTORS),
                     "ancestors_where_uncut_differs_engine": 0, "ancestors_where_filtered_differs": sum(model.balance[("kind-filtered", i, last)] != model.balance[("stepwise", i, last)] for i in ANCESTORS),
                     "credits_with_no_kind": sum(p.kind is None for p in credits), "checkpoints": len(corpus.positions)}
            keys = [(f, LEVELS[lv]) for f in CUT_FOLDS for lv in (1, 2, 3)]
            m = Measurement(name, count, share, stored, sum(p.kind is not None for p in credits), write, backend.form, {k: LevelRead() for k in keys}, {k: LevelRead() for k in keys}, {}, notes, CORPUS_TWO)
            for point in points:
                for i in ANCESTORS:
                    level = LEVELS[TREE[i].level]
                    for mode in MODES:
                        cp = mode == "checkpointed"
                        for fold in CUT_FOLDS:
                            begin = time.perf_counter()
                            if fold == "sum-with-cuts":
                                balance, rows, uncut = read_with_cuts(backend, i, point, cp)
                            else:
                                balance, rows = read(fold, backend, i, point, cp)
                            seconds = time.perf_counter() - begin
                            want, want_rows = expected(model, fold, i, point, cp)
                            where = f"{name} {count} share {share} {mode} {fold}: {TREE[i].iri} as of {point}"
                            if balance != want:
                                raise WrongResult(f"{where} reads {balance}, the model gives {want}")
                            if rows != want_rows:
                                raise WrongResult(f"{where} counts {rows} postings, the model gives {want_rows}")
                            if fold == "sum-with-cuts" and not cp:
                                if uncut != model.balance[("applied", i, point)]:
                                    raise WrongResult(f"{where}: the postings alone read {uncut}, the model's sum of applied amounts is {model.balance[('applied', i, point)]}")
                                if point == last and uncut != model.balance[("stepwise", i, point)]:
                                    m.notes["ancestors_where_uncut_differs_engine"] += 1
                            r = (m.cp_reads if cp else m.reads)[(fold, level)]
                            r.reads, r.seconds, r.rows = r.reads + 1, r.seconds + seconds, r.rows + rows
                            if fold == "sum-with-cuts":
                                r.postings_seconds, r.cuts_seconds = r.postings_seconds + backend.parts[0], r.cuts_seconds + backend.parts[1]
                            elif fold == "stepwise":
                                r.fetch_seconds, r.loop_seconds = r.fetch_seconds + backend.parts[0], r.loop_seconds + backend.parts[1]
            if share >= STEPWISE_BINDS_FROM and m.notes["ancestors_where_uncut_differs_engine"] == 0:
                raise WrongResult(f"{name} {count} share {share}: no ancestor's postings-only sum differs from its stepwise balance, so the engine does not show the defect the cut repairs")
            if m.notes["ancestors_where_uncut_differs_engine"] != m.notes["ancestors_where_uncut_differs"]:
                raise WrongResult(f"{name} {count} share {share}: the engine's uncut sum differs at {m.notes['ancestors_where_uncut_differs_engine']} ancestors, the model's at {m.notes['ancestors_where_uncut_differs']}")
        finally:
            backend.close()
            backend = None
            release_store()
    return m


def run_cuts(sizes=SIZES, shares=SHARES, backends=None) -> list[Measurement]:
    out = []
    for count in sizes:
        for share in shares:
            for name in backends or available_backends():
                m = run_backend_cuts(name, count, share)
                out.append(m)
                print(f"{name:9} two-level events {count:6} credits {share:4.0%} stored {m.stored_triples:7} cuts {m.notes['cuts']:5} write {m.write_seconds:6.2f} s  " + "  ".join(
                    f"{f} root {1000 * m.reads[(f, 'root')].seconds / m.reads[(f, 'root')].reads:8.2f} ms" for f in CUT_FOLDS), flush=True)
    return out


def run(sizes=SIZES, shares=SHARES, backends=None) -> list[Measurement]:
    out = []
    for count in sizes:
        for share in shares:
            for name in backends or available_backends():
                m = run_backend(name, count, share)
                out.append(m)
                sc = [r for (mode, _), r in m.shortcut.items() if mode == "checkpointed"]
                print(f"{name:9} events {count:6} credits {share:4.0%} stored {m.stored_triples:7} write {m.write_seconds:6.2f} s  " + "  ".join(
                    f"{f} root {1000 * m.reads[(f, 'root')].seconds / m.reads[(f, 'root')].reads:8.2f} ms" for f in FOLDS)
                    + f"  checkpointed stepwise root {1000 * m.cp_reads[('stepwise', 'root')].seconds / m.cp_reads[('stepwise', 'root')].reads:7.2f} ms"
                    + f"  shortcut fallbacks {sum(r.fallbacks for r in sc)}/{sum(r.reads for r in sc)}", flush=True)
    return out


def environment() -> dict[str, str]:
    return {"date": time.strftime("%Y-%m-%d"), "python": platform.python_version(), "machine": f"{platform.system()} {platform.machine()}", **versions(),
            "depth": "4", "contracts": str(len(CONTRACTS)), "passes_per_period": str(EVERY_POSITIONS), "seed": str(SEED), "kindless_share": str(KINDLESS_SHARE), "upper_share": str(UPPER_SHARE),
            "jena_note": "" if jena_available() else "jena not run: the test kit jar is not built or there is no java"}


def _entry(r: LevelRead) -> dict:
    n = r.reads
    return {"reads": n, "mean_ms": 1000 * r.seconds / n, "mean_rows": r.rows / n, "fetch_ms": 1000 * r.fetch_seconds / n, "loop_ms": 1000 * r.loop_seconds / n, "fallbacks": r.fallbacks,
            "postings_ms": 1000 * r.postings_seconds / n, "cuts_ms": 1000 * r.cuts_seconds / n}


def _total(reads: dict, prefix: str, fold: str) -> float:
    return sum(v["mean_ms"] * v["reads"] for k, v in reads.items() if k.startswith(f"{prefix}{fold}/"))


def measurement_row(m: Measurement) -> dict:
    reads = {f"{f}/{lv}": _entry(r) for (f, lv), r in m.reads.items()}
    reads.update({f"cp:{f}/{lv}": _entry(r) for (f, lv), r in m.cp_reads.items()})
    reads.update({f"shortcut:{mode}/{lv}": _entry(r) for (mode, lv), r in m.shortcut.items()})
    return {"corpus": m.corpus, "backend": m.backend, "events": m.events, "credit_share": m.credit_share, "stored_triples": m.stored_triples, "kind_triples": m.kind_triples, "kind_join": m.form,
            "write_seconds": m.write_seconds, "model_expects": m.notes, "reads": reads}


def render(rows: list[dict], title: str) -> list[str]:
    """The tables of a run, from report rows. Python and the native Jena caller write the same row shape."""
    levels = LEVELS[1:]

    def total(r, key):
        return sum(v["mean_ms"] * v["reads"] for k, v in r["reads"].items() if k.startswith(key + "/"))

    out = [f"## {title}", "", "Full reads, from the start of history. Mean ms and mean rows per read, by the level of the account read.", "",
           "| backend | kind join | events | credits | fold | " + " | ".join(f"{lv} ms | {lv} rows" for lv in levels) + " | time vs plain |", "|---|---|---|---|---|" + "---|---|" * len(levels) + "---|"]
    for r in rows:
        for f in FOLDS:
            cells = " | ".join(f"{r['reads'][f'{f}/{lv}']['mean_ms']:.2f} | {r['reads'][f'{f}/{lv}']['mean_rows']:.0f}" for lv in levels)
            out.append(f"| {r['backend']} | {r['kind_join']} | {r['events']} | {r['credit_share']:.0%} | {f} | {cells} | {total(r, f) / total(r, 'plain'):.2f} |")
    out += ["", "The stepwise fold's time split, at the root, mean ms per read. Fetch is the ordered query and the transfer of its rows, loop is the clamping.", "",
            "| backend | kind join | events | credits | read from | stepwise ms | fetch ms | loop ms | kind-filtered ms |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        for mode, prefix in (("start", ""), ("checkpoint", "cp:")):
            s, k = r["reads"][f"{prefix}stepwise/root"], r["reads"][f"{prefix}kind-filtered/root"]
            out.append(f"| {r['backend']} | {r['kind_join']} | {r['events']} | {r['credit_share']:.0%} | {mode} | {s['mean_ms']:.2f} | {s['fetch_ms']:.2f} | {s['loop_ms']:.2f} | {k['mean_ms']:.2f} |")
    out += ["", "Checkpointed reads against full reads, at the root (mean ms and mean rows per read) and over all 27 ancestor reads (time ratio).", "",
            "| backend | events | credits | fold | full ms | full rows | checkpointed ms | checkpointed rows | all reads, checkpointed / full |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        for f in FOLDS:
            a, b = r["reads"][f"{f}/root"], r["reads"][f"cp:{f}/root"]
            out.append(f"| {r['backend']} | {r['events']} | {r['credit_share']:.0%} | {f} | {a['mean_ms']:.2f} | {a['mean_rows']:.0f} | {b['mean_ms']:.2f} | {b['mean_rows']:.0f} "
                       f"| {total(r, 'cp:' + f) / total(r, f):.2f} |")
    out += ["", "The shortcut, over all ancestor reads of a run. Total time against the stepwise fold read the same way.", "",
            "| backend | events | credits | read from | reads | fallbacks | fallback rate | shortcut s | stepwise s | shortcut / stepwise |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        for mode, prefix in (("start", ""), ("checkpoint", "cp:")):
            key = "full" if mode == "start" else "checkpointed"
            parts = [v for k, v in r["reads"].items() if k.startswith(f"shortcut:{key}/")]
            n, fb = sum(v["reads"] for v in parts), sum(v["fallbacks"] for v in parts)
            sc, st = total(r, f"shortcut:{key}") / 1000, total(r, prefix + "stepwise") / 1000
            out.append(f"| {r['backend']} | {r['events']} | {r['credit_share']:.0%} | {mode} | {n} | {fb} | {fb / n:.0%} | {sc:.2f} | {st:.2f} | {sc / st:.2f} |")
    return out + [""]


def write_report(measurements: list[Measurement], directory: Path | None = None) -> None:
    directory = directory or Path(os.environ.get("LEDGER_KINDS_REPORT_DIR") or HERE)
    data = {"environment": environment(), "measurements": [measurement_row(m) for m in measurements]}
    (directory / "report.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    write_markdown(data, directory)


def render_cuts(rows: list[dict]) -> list[str]:
    """The tables of the two-level corpus, from report rows. Reads are of the ancestors only, times are means per read, and the ratios are of the time of all 27 ancestor reads."""
    def total(r, key):
        return sum(v["mean_ms"] * v["reads"] for k, v in r["reads"].items() if k.startswith(key + "/"))

    out = ["## Credits at two levels of a path (sum with cuts)", "",
           "Credits posted at a contract, a sublimit or a section on the drawn contract's path, with the cuts a writer records. What the corpus holds, and where the folds differ.", "",
           "| backend | events | credits | credits above a contract | credits with a cut | cuts | cut triples | stored triples | ancestor clamps binding | ancestors where the uncut sum is wrong (model / engine) | ancestors where the offered sum is wrong |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        n = r["model_expects"]
        out.append(f"| {r['backend']} | {r['events']} | {r['credit_share']:.0%} | {n['credits_posted_above_a_contract']} of {n['credits']} | {n['credits_with_a_cut']} ({n['credits_with_a_cut'] / n['credits']:.1%}) | {n['cuts']} "
                   f"| {n['cut_triples']} | {r['stored_triples']} | {n['ancestor_clamps_binding']} | {n['ancestors_where_uncut_differs']} / {n['ancestors_where_uncut_differs_engine']} of 9 | {n['ancestors_where_filtered_differs']} of 9 |")
    for mode, prefix in (("Full reads, from the start of history", ""), ("Checkpointed reads, from the last checkpoint", "cp:")):
        out += ["", f"{mode}. Mean ms per read of the root, then the time of all 27 ancestor reads of the sum with cuts against the kind-filtered and the stepwise folds.", "",
                "| backend | events | credits | kind-filtered ms | stepwise ms | sum-with-cuts ms | of which postings ms | of which cuts ms | sum-with-cuts / kind-filtered | sum-with-cuts / stepwise |", "|---|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            k, st, c = (r["reads"][f"{prefix}{f}/root"] for f in CUT_FOLDS)
            out.append(f"| {r['backend']} | {r['events']} | {r['credit_share']:.0%} | {k['mean_ms']:.2f} | {st['mean_ms']:.2f} | {c['mean_ms']:.2f} | {c['postings_ms']:.2f} | {c['cuts_ms']:.2f} "
                       f"| {total(r, prefix + 'sum-with-cuts') / total(r, prefix + 'kind-filtered'):.2f} | {total(r, prefix + 'sum-with-cuts') / total(r, prefix + 'stepwise'):.2f} |")
    out += ["", "Rows per root read, full and checkpointed.", "", "| backend | events | credits | kind-filtered | stepwise | sum-with-cuts | checkpointed sum-with-cuts |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['backend']} | {r['events']} | {r['credit_share']:.0%} | " + " | ".join(f"{r['reads'][f'{p}{f}/root']['mean_rows']:.0f}" for p, f in (("", "kind-filtered"), ("", "stepwise"), ("", "sum-with-cuts"), ("cp:", "sum-with-cuts"))) + " |")
    return out + [""]


def write_markdown(data: dict, directory: Path, jvm_report: Path = JVM_REPORT) -> None:
    one = [m for m in data["measurements"] if m.get("corpus", CORPUS_ONE) == CORPUS_ONE]
    two = [m for m in data["measurements"] if m.get("corpus", CORPUS_ONE) == CORPUS_TWO]
    lines = ["# Ledger credit kinds (generated)", "", "```", json.dumps(data["environment"]), "```", ""]
    lines += render(one, "Python callers")
    if two:
        lines += render_cuts(two)
    if jvm_report.exists():
        jvm = json.loads(jvm_report.read_text(encoding="utf-8"))
        lines += ["```", json.dumps(jvm["environment"]), "```", ""] + render(jvm["measurements"], "Native Jena (Java)")
    (directory / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def emit(directory: Path, sizes=SIZES, shares=SHARES) -> None:
    """Writes each corpus as N-Quads and every read's expected balance and posting count as JSON, for the native Jena caller (`benchmark/ledger-credit-kinds-jvm`)."""
    directory.mkdir(parents=True, exist_ok=True)

    def nt(o):
        return f"<{o[1]}>" if o[0] == "i" else f'"{o[1]}"^^<{XSD_INT}>' if o[0] == "n" else f'"{o[1]}"'

    tree = [{"iri": a.iri, "level": a.level, "stated": a.stated,
             "graphPrefixes": [f"urn:graph:{TREE[u].iri.rsplit(':', 1)[1]}:" for u in sublimits_under(i)],
             "contracts": [TREE[c].iri for c in contracts_under(i)]} for i, a in enumerate(TREE)]
    corpora = []
    for count in sizes:
        for share in shares:
            corpus = build_corpus(count, share)
            check_discriminates(corpus.model, share, corpus.points[-1], corpus.postings)
            name = f"corpus-{count}-{round(100 * share)}.nq"
            with open(directory / name, "w", encoding="utf-8", newline="\n") as out:
                for s, p, o, g in quads(corpus.postings, corpus.cps):
                    out.write(f"<{s}> <{p}> {nt(o)}{' <' + g + '>' if g else ''} .\n")
            reads = [{"fold": f, "checkpointed": cp, "account": TREE[i].iri, "level": TREE[i].level, "point": point,
                      "balance": expected(corpus.model, f, i, point, cp)[0], "rows": expected(corpus.model, f, i, point, cp)[1]}
                     for point in corpus.points for i in ANCESTORS for cp in (False, True) for f in FOLDS]
            shortcut = [{"checkpointed": cp, "account": TREE[i].iri, "level": TREE[i].level, "point": point, "balance": corpus.model.balance[("stepwise", i, point)]}
                        for point in corpus.points for i in ANCESTORS for cp in (False, True)]
            corpora.append({"events": count, "credit_share": share, "file": name, "stored": expected_stored(corpus.postings), "points": corpus.points,
                            "reads": reads, "shortcut": shortcut})
    data = {"every": EVERY_POSITIONS, "ns": L, "tree": tree, "corpora": corpora}
    (directory / "expected.json").write_text(json.dumps(data, indent=1), encoding="utf-8", newline="\n")


def sizes_from_env() -> list[int]:
    cap = int(os.environ.get("LEDGER_KINDS_MAX", SIZES[-1]))
    sizes = [s for s in SIZES if s <= cap] or [cap]
    return sizes[:1] if os.environ.get("LEDGER_KINDS_QUICK") else sizes


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "--emit":
        emit(Path(sys.argv[2]), sizes_from_env())
        print(f"corpora and expected balances written to {sys.argv[2]}")
        return 0
    if len(sys.argv) == 2 and sys.argv[1] == "--merge":
        saved = HERE / "report.json"
        data = json.loads(saved.read_text(encoding="utf-8")) if saved.exists() else {"environment": environment(), "measurements": []}
        write_markdown(data, HERE)
        print(f"native Jena timings merged into {HERE / 'report.md'}")
        return 0
    try:
        measurements = run(sizes_from_env()) + run_cuts(sizes_from_env())
    except WrongResult as error:
        print(f"WRONG RESULT: {error}", file=sys.stderr)
        return 1
    write_report(measurements)
    print(json.dumps(environment()))
    print(f"report written to {os.environ.get('LEDGER_KINDS_REPORT_DIR') or HERE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
