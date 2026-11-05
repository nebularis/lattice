# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""What it costs to record the draws on an account tree, held five ways on Oxigraph (ADR-A124).

The account tree has depth 3, mirroring a placement: a contract account, the layer it sits on, and the programme the layer belongs to. There are 2 programmes,
5 layers to a programme and 10 contracts to a layer. A stream of N events (mostly draws, some credits) falls on random contract accounts. The same history is held in several ways.

* **every-level**. Each event writes a posting to the contract and to each ancestor. An account's balance is its stated amount less its own debits plus its own credits.
* **post-once**. Each event writes one posting, at the contract. An ancestor's balance is a fold over the postings of its whole subtree, reached by `partOf*`.
* **post-once-checkpointed**. As post-once, and every K events each account gets a checkpoint holding its balance. A read takes the latest checkpoint at or before the
  point, then folds the postings after it.
* **post-once-balance-after**. As post-once, and each posting carries `balanceAfter`. A contract is read from its latest posting. An ancestor is a fold.
* **post-once-period-graphs**. As post-once-checkpointed, and each posting goes into a named graph keyed by its layer and its period (K events). A read takes the
  latest checkpoint, then folds exactly the graphs of the periods after it, so the postings before the checkpoint are never visited.

**Pass criterion.** For every account and every read point, all the strategies report the balance the model gives, so they report the same balance as each other.
The stored triples have the count each strategy's arithmetic gives (`expected_stored`). A checkpointed read never folds more postings than the same read without
checkpoints. A wrong balance or count fails the check. **Time never fails it.** The seconds, the triples and the postings folded per read go to `report.json` and
`report.md` here, which are generated and git-ignored.

Run `mise run check:ledger-posting-cost`. `LEDGER_COST_MAX` caps the number of events (default 20000), and `LEDGER_COST_QUICK=1` runs the smallest size only. The store is
a temporary directory that is removed when the run ends, including on failure."""

from __future__ import annotations

import json
import os
import platform
import random
import sys
import tempfile
import time
from functools import cache
from dataclasses import dataclass, field
from pathlib import Path

import pyoxigraph as ox

HERE = Path(__file__).resolve().parent
L = "https://example.org/ledger-cost#"
RDF_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
INTEGER = ox.NamedNode("http://www.w3.org/2001/XMLSchema#integer")
STRING = ox.NamedNode("http://www.w3.org/2001/XMLSchema#string")

SIZES = (1_000, 5_000, 20_000)
CHECKPOINT_EVERY = 500
PROGRAMMES, LAYERS_PER_PROGRAMME, CONTRACTS_PER_LAYER = 2, 5, 10
DEPTH = 3
STATED = (10**9, 10**10, 10**11)  # by level, contract first
STRATEGIES = ("every-level", "post-once", "post-once-checkpointed", "post-once-balance-after", "post-once-period-graphs")
LEVELS = ("contract", "layer", "programme")
POSTING_TRIPLES = 8  # type, account, owner, key, position, micro-position, direction, amount
CHECKPOINT_TRIPLES = 4  # type, account, position, balance
SEED = 20261024


class WrongResult(AssertionError):
    """A balance that is not the model's, or a stored count that is not the strategy's arithmetic. The one way the check fails."""


def n(name: str) -> ox.NamedNode:
    return ox.NamedNode(L + name)


def num(value: int) -> ox.Literal:
    return ox.Literal(str(value), datatype=INTEGER)


@dataclass(frozen=True)
class Account:
    iri: ox.NamedNode
    level: int  # 0 contract, 1 layer, 2 programme
    parent: int | None  # index in the account list


def build_tree() -> list[Account]:
    """Programmes first, then layers, then contracts, so a parent always precedes its child."""
    accounts: list[Account] = []
    for a in range(PROGRAMMES):
        accounts.append(Account(ox.NamedNode(f"urn:acct:prog{a}"), 2, None))
    for a in range(PROGRAMMES):
        for p in range(LAYERS_PER_PROGRAMME):
            accounts.append(Account(ox.NamedNode(f"urn:acct:lyr{a}-{p}"), 1, a))
    first_layer = PROGRAMMES
    for index in range(PROGRAMMES * LAYERS_PER_PROGRAMME):
        for contract in range(CONTRACTS_PER_LAYER):
            accounts.append(Account(ox.NamedNode(f"urn:acct:con{index}-{contract}"), 0, first_layer + index))
    return accounts


def ancestors(accounts: list[Account], index: int) -> list[int]:
    """The account and every ancestor, contract first."""
    chain = [index]
    while accounts[chain[-1]].parent is not None:
        chain.append(accounts[chain[-1]].parent)
    return chain


def events(count: int, accounts: list[Account]) -> list[tuple[int, bool, int]]:
    """(contract index, is a debit, amount) for events 1 to count. One in five is a credit."""
    rng = random.Random(SEED)
    contracts = [i for i, a in enumerate(accounts) if a.level == 0]
    return [(rng.choice(contracts), rng.random() >= 0.2, rng.randint(1, 1000)) for _ in range(count)]


@dataclass
class Model:
    """The balances by the plainest arithmetic, independent of any strategy."""

    at_points: dict[int, list[int]]  # read point -> balance of each account
    at_checkpoints: dict[int, list[int]]  # checkpoint position -> balance of each account
    after: dict[int, int]  # event -> balance of its contract after it


def run_model(count: int, every: int, points: list[int], accounts: list[Account], stream) -> Model:
    balance = [STATED[a.level] for a in accounts]
    model = Model({}, {}, {})
    if 0 in points:
        model.at_points[0] = list(balance)
    for e, (contract, debit, amount) in enumerate(stream, start=1):
        for i in ancestors(accounts, contract):
            balance[i] += -amount if debit else amount
        model.after[e] = balance[contract]
        if e in points:
            model.at_points[e] = list(balance)
        if e % every == 0:
            model.at_checkpoints[e] = list(balance)
    return model


def read_points(count: int, every: int) -> list[int]:
    """Before any event, early, on a checkpoint, just after one, mid-stream, and the last two events."""
    candidates = {0, 1, count // 3, count // 2, every, every + 1, count - 1, count}
    return sorted(p for p in candidates if 0 <= p <= count)


def structure_triples(accounts: list[Account]) -> int:
    return sum(2 + (a.parent is not None) for a in accounts)


def expected_stored(strategy: str, count: int, every: int = CHECKPOINT_EVERY) -> int:
    """The triples in the store after count events, by the strategy's arithmetic."""
    accounts = build_tree()
    per_event = {"every-level": DEPTH * POSTING_TRIPLES, "post-once": POSTING_TRIPLES, "post-once-checkpointed": POSTING_TRIPLES,
                 "post-once-balance-after": POSTING_TRIPLES + 1, "post-once-period-graphs": POSTING_TRIPLES}[strategy]
    total = structure_triples(accounts) + count * per_event
    if strategy in ("post-once-checkpointed", "post-once-period-graphs"):
        total += len(accounts) * (count // every) * CHECKPOINT_TRIPLES
    return total


def period_graph(layer: ox.NamedNode, period: int) -> ox.NamedNode:
    """The named graph holding the postings of one layer's contracts in one period of `every` events."""
    return ox.NamedNode(f"urn:graph:{layer.value.rsplit(':', 1)[1]}:{period}")


def posting(e: int, acct: Account, debit: bool, amount: int, after: int | None, graph=ox.DefaultGraph()):
    s = ox.NamedNode(f"urn:posting:{e}:{acct.iri.value.rsplit(':', 1)[1]}")
    yield ox.Quad(s, RDF_TYPE, n("Posting"), graph)
    yield ox.Quad(s, n("account"), acct.iri, graph)
    yield ox.Quad(s, n("owner"), ox.NamedNode("urn:owner:1"), graph)
    yield ox.Quad(s, n("key"), ox.Literal(f"k{e}"), graph)
    yield ox.Quad(s, n("position"), num(e), graph)
    yield ox.Quad(s, n("microPosition"), num(0), graph)
    yield ox.Quad(s, n("direction"), n("Debit" if debit else "Credit"), graph)
    yield ox.Quad(s, n("amount"), num(amount), graph)
    if after is not None:
        yield ox.Quad(s, n("balanceAfter"), num(after), graph)


def quads_for(strategy: str, accounts: list[Account], stream, model: Model, every: int):
    for i, a in enumerate(accounts):
        yield ox.Quad(a.iri, RDF_TYPE, n("Account"))
        yield ox.Quad(a.iri, n("statedAmount"), num(STATED[a.level]))
        if a.parent is not None:
            yield ox.Quad(a.iri, n("partOf"), accounts[a.parent].iri)
    for e, (contract, debit, amount) in enumerate(stream, start=1):
        if strategy == "every-level":
            for i in ancestors(accounts, contract):
                yield from posting(e, accounts[i], debit, amount, None)
        elif strategy == "post-once-period-graphs":
            graph = period_graph(accounts[accounts[contract].parent].iri, (e - 1) // every)
            yield from posting(e, accounts[contract], debit, amount, None, graph)
        else:
            after = model.after[e] if strategy == "post-once-balance-after" else None
            yield from posting(e, accounts[contract], debit, amount, after)
    if strategy in ("post-once-checkpointed", "post-once-period-graphs"):
        for position, balances in model.at_checkpoints.items():
            for i, a in enumerate(accounts):
                c = ox.NamedNode(f"urn:checkpoint:{position}:{a.iri.value.rsplit(':', 1)[1]}")
                yield ox.Quad(c, RDF_TYPE, n("Checkpoint"))
                yield ox.Quad(c, n("account"), a.iri)
                yield ox.Quad(c, n("position"), num(position))
                yield ox.Quad(c, n("balance"), num(balances[i]))


PREFIX = f"PREFIX l: <{L}> "
FOLD = ("SELECT (SUM(?signed) AS ?sum) (COUNT(?p) AS ?folded) WHERE {{ {scope} ?p l:position ?pos ; l:direction ?d ; l:amount ?a . "
        "FILTER(?pos > {after} && ?pos <= {point}) BIND(IF(?d = l:Debit, -?a, ?a) AS ?signed) }}")
OWN = "?p l:account <{acct}> ."
SUBTREE = "?acc l:partOf* <{acct}> . ?p l:account ?acc ."


def _integer(term) -> int:
    return int(term.value)


def stated(store: ox.Store, account: ox.NamedNode) -> int:
    (row,) = store.query(f"{PREFIX}SELECT ?s WHERE {{ <{account.value}> l:statedAmount ?s }}")
    return _integer(row["s"])


def fold(store, account, after: int, point: int, scope: str) -> tuple[int, int]:
    """(the sum of the signed amounts of the postings in scope after `after` and up to `point`, how many postings that folded)."""
    text = PREFIX + FOLD.format(scope=scope.format(acct=account.value), after=after, point=point)
    (row,) = store.query(text)
    return (_integer(row["sum"]) if row["sum"] is not None else 0), _integer(row["folded"])


@cache
def tree() -> list[Account]:
    return build_tree()


def layers_of(account: Account) -> list[ox.NamedNode]:
    """The layers whose contracts lie in the account's subtree, read from the tree structure."""
    accounts = tree()
    if account.level == 0:
        return [accounts[account.parent].iri]
    if account.level == 1:
        return [account.iri]
    return [a.iri for a in accounts if a.level == 1 and accounts[a.parent].iri == account.iri]


def graph_block(names: list[ox.NamedNode], scope: str, bound: str) -> str:
    """A fold over exactly the named graphs. VALUES ?g with GRAPH ?g was no slower than a union of GRAPH <name> blocks and is shorter (see the README)."""
    values = " ".join(f"<{g.value}>" for g in names)
    return f"{{ VALUES ?g {{ {values} }} GRAPH ?g {{ {scope} ?p l:position ?pos ; l:direction ?d ; l:amount ?a . {bound} }} }}"


def fold_graphs(store, account: Account, after: int, point: int, every: int) -> tuple[int, int]:
    """The fold for post-once-period-graphs: only the graphs of the periods holding events after `after` and up to `point`.

    Layer and programme reads take every posting in their graphs, with no join to the account tree. A contract read adds its own account, since a graph holds the
    layer's ten contracts. A graph is taken whole unless the bound falls inside its period, the one place a position FILTER is left. The lower bound is a checkpoint
    and closes on a period end, so only the period of the read point is usually filtered, and a bound that does not fall on a period end filters its own period."""
    first, last = max(after, 0) // every, (point - 1) // every
    by_bound: dict[str, list[ox.NamedNode]] = {}
    for period in range(first, last + 1):
        low = period == first and max(after, 0) % every != 0
        high = period == last and point % every != 0
        bound = "FILTER(" + " && ".join(([f"?pos > {after}"] if low else []) + ([f"?pos <= {point}"] if high else [])) + ")" if low or high else ""
        by_bound.setdefault(bound, []).extend(period_graph(g, period) for g in layers_of(account))
    if not by_bound:
        return 0, 0
    scope = OWN.format(acct=account.iri.value) if account.level == 0 else ""
    blocks = " UNION ".join(graph_block(names, scope, bound) for bound, names in by_bound.items())
    text = f"{PREFIX}SELECT (SUM(?signed) AS ?sum) (COUNT(?p) AS ?folded) WHERE {{ {blocks} BIND(IF(?d = l:Debit, -?a, ?a) AS ?signed) }}"
    (row,) = store.query(text)
    return (_integer(row["sum"]) if row["sum"] is not None else 0), _integer(row["folded"])


def checkpoint(store: ox.Store, account: Account, point: int, every: int, base: int) -> tuple[int, int]:
    """(the position of the latest checkpoint at or before the point, the balance it holds), or (-1, base) before the first close.

    A closing recurrence fixes the positions at which checkpoints exist, so the latest one at or before a point is computed rather
    than searched for, and its IRI is derived from the account and that position. Searching for it by its properties costs an order
    more and grows with the number of closes, even with the position bound, which is TSD-36."""
    position = (point // every) * every
    if position < every:
        return -1, base
    name = f"urn:checkpoint:{position}:{account.iri.value.rsplit(':', 1)[1]}"
    (row,) = store.query(f"{PREFIX}SELECT ?b WHERE {{ <{name}> l:balance ?b }}")
    return position, _integer(row["b"])


def read(strategy: str, store: ox.Store, account: Account, point: int, every: int = CHECKPOINT_EVERY) -> tuple[int, int]:
    """(the balance of the account as of the point, how many postings the read folded)."""
    base = stated(store, account.iri)
    if strategy == "every-level":
        total, folded = fold(store, account.iri, -1, point, OWN)
        return base + total, folded
    if strategy == "post-once-balance-after" and account.level == 0:
        rows = list(store.query(f"{PREFIX}SELECT ?b WHERE {{ ?p l:account <{account.iri.value}> ; l:position ?pos ; l:balanceAfter ?b . "
                                f"FILTER(?pos <= {point}) }} ORDER BY DESC(?pos) LIMIT 1"))
        return (_integer(rows[0]["b"]), 1) if rows else (base, 0)
    after, start = -1, base
    if strategy in ("post-once-checkpointed", "post-once-period-graphs"):
        after, start = checkpoint(store, account, point, every, base)
    if strategy == "post-once-period-graphs":
        total, folded = fold_graphs(store, account, after, point, every)
    else:
        total, folded = fold(store, account.iri, after, point, SUBTREE)
    return start + total, folded


@dataclass
class LevelRead:
    reads: int = 0
    seconds: float = 0.0
    folded: int = 0


@dataclass
class Measurement:
    strategy: str
    events: int
    stored_triples: int
    triples_per_event: float
    write_seconds: float
    reads: dict[str, LevelRead] = field(default_factory=dict)


def run_strategy(strategy: str, count: int, every: int = CHECKPOINT_EVERY, directory: str | None = None) -> tuple[Measurement, dict]:
    """Writes the history, reads every account at every read point, and returns the measurement and the postings folded by (account, point)."""
    accounts = build_tree()
    stream = events(count, accounts)
    points = read_points(count, every)
    model = run_model(count, every, points, accounts, stream)
    with tempfile.TemporaryDirectory(prefix="ledger-posting-cost-", dir=directory) as tmp:
        store = ox.Store(tmp)
        start = time.perf_counter()
        store.bulk_extend(quads_for(strategy, accounts, stream, model, every))
        store.flush()
        write = time.perf_counter() - start
        stored = len(store)
        if stored != expected_stored(strategy, count, every):
            raise WrongResult(f"{strategy} {count}: stored {stored} triples, expected {expected_stored(strategy, count, every)}")
        m = Measurement(strategy, count, stored, stored / count, write, {name: LevelRead() for name in LEVELS})
        folded_by: dict[tuple[int, int], int] = {}
        for point in points:
            for i, account in enumerate(accounts):
                begin = time.perf_counter()
                balance, folded = read(strategy, store, account, point, every)
                seconds = time.perf_counter() - begin
                if balance != model.at_points[point][i]:
                    raise WrongResult(f"{strategy} {count}: {account.iri.value} as of {point} reads {balance}, the model gives {model.at_points[point][i]}")
                r = m.reads[LEVELS[account.level]]
                r.reads, r.seconds, r.folded = r.reads + 1, r.seconds + seconds, r.folded + folded
                folded_by[(i, point)] = folded
        del store
    return m, folded_by


def run(sizes=SIZES, every: int = CHECKPOINT_EVERY) -> list[Measurement]:
    out = []
    for count in sizes:
        folds = {}
        for strategy in STRATEGIES:
            m, folded_by = run_strategy(strategy, count, every)
            folds[strategy] = folded_by
            out.append(m)
            print(f"{strategy:24} events {count:6}  stored {m.stored_triples:8}  write {m.write_seconds:7.2f} s  " + "  ".join(
                f"{name} {1000 * r.seconds / r.reads:7.2f} ms {r.folded / r.reads:8.1f} folded" for name, r in m.reads.items()), flush=True)
        worse = [k for k, v in folds["post-once-checkpointed"].items() if v > folds["post-once"][k]]
        if worse:
            raise WrongResult(f"{count}: a checkpointed read folded more postings than the read without checkpoints, first at (account, point) {worse[0]}")
        wider = [k for k, v in folds["post-once-period-graphs"].items() if v > folds["post-once-checkpointed"][k]]
        if wider:
            raise WrongResult(f"{count}: a period-graph read folded more postings than the checkpointed read, first at (account, point) {wider[0]}")
    return out


def environment() -> dict[str, str]:
    return {"date": time.strftime("%Y-%m-%d"), "python": platform.python_version(), "machine": f"{platform.system()} {platform.machine()}",
            "pyoxigraph": ox.__version__, "depth": str(DEPTH), "contracts": str(PROGRAMMES * LAYERS_PER_PROGRAMME * CONTRACTS_PER_LAYER),
            "checkpoint_every": str(CHECKPOINT_EVERY), "seed": str(SEED)}


def write_report(measurements: list[Measurement], directory: Path = HERE) -> None:
    rows = [{"strategy": m.strategy, "events": m.events, "stored_triples": m.stored_triples, "triples_per_event": m.triples_per_event,
             "write_seconds": m.write_seconds, "reads": {k: {"reads": r.reads, "mean_ms": 1000 * r.seconds / r.reads, "mean_folded": r.folded / r.reads}
                                                          for k, r in m.reads.items()}} for m in measurements]
    data = {"environment": environment(), "measurements": rows}
    (directory / "report.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    head = "| strategy | events | stored triples | per event | write s |" + "".join(f" {name} ms | {name} folded |" for name in LEVELS)
    lines = ["# Ledger posting cost (generated, not committed)", "", "```", json.dumps(data["environment"]), "```", "", head,
             "|---|---|---|---|---|" + "---|---|" * len(LEVELS)]
    for r in rows:
        cells = "".join(f" {r['reads'][name]['mean_ms']:.2f} | {r['reads'][name]['mean_folded']:.1f} |" for name in LEVELS)
        lines.append(f"| {r['strategy']} | {r['events']} | {r['stored_triples']} | {r['triples_per_event']:.2f} | {r['write_seconds']:.2f} |{cells}")
    (directory / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    probe = os.environ.get("LEDGER_COST_PROBE")
    if probe:
        sizes = [int(probe)]
    else:
        cap = int(os.environ.get("LEDGER_COST_MAX", SIZES[-1]))
        sizes = [s for s in SIZES if s <= cap] or [cap]
        if os.environ.get("LEDGER_COST_QUICK"):
            sizes = sizes[:1]
    try:
        measurements = run(sizes)
    except WrongResult as error:
        print(f"WRONG RESULT: {error}", file=sys.stderr)
        return 1
    write_report(measurements)
    print(f"report written to {HERE / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
