# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""What an as-of read costs on the effective axis when postings are recorded after the time they take effect (ADR-A124).

`check.py` holds one axis, the position an event is recorded at. A posting also has an **effective position**, where its fact sits in the world the arrangement describes, and a fact may be recorded after
the time it takes effect (a correction, a backdated adjustment). The period graphs and the checkpoints are keyed on the recorded axis, so a checkpoint cannot serve a read as of an effective position.
This measures what that read costs.

**The ratified bound.** A posting's effective position never exceeds the recorded position of the pass that wrote it. Backdating happens and forward-dating does not. So every posting recorded at or before
a close has an effective position at or before it. A read as of effective P takes the checkpoint at the latest close C at or before P, which already holds every posting recorded up to C, then folds the
later periods filtered on effective position. The generator asserts the bound for every posting it emits, and a violation fails the run.

**What the bound does not give.** It bounds a posting's effective position by its recorded position, and says nothing about how far apart they can be. A posting recorded long after P can still be effective
at or before P, so without a limit on how far back a posting may reach, the later periods to fold run to the end of the recorded history. This module measures that read (**no reach cap**, the one the
ratified bound alone supports) and a read that stops at P plus a **declared reach cap**, which is not ratified and holds here only because the generator never reaches back further (it asserts that).
Under the cap the periods folded are those from C to the period holding P plus the cap.

**Cases.** For each history size, late-posting rate and reach (the farthest back a late posting is drawn, in periods of `CHECKPOINT_EVERY` events), three read points (recent, mid and old in the history) and
four reads each. The as-of-effective read without a cap, the as-of-effective read with the cap, the as-of-recorded read at the same point (the cheap control, which answers a different question and misses the
postings recorded after P), and the unpartitioned fold filtered on effective position (the floor, with no checkpoint and no graph named). A rate of 0 has no late postings and so no reach.

**Pass criterion.** Every account's balance equals the model's at every read point, on the effective axis for the effective reads and the floor and on the recorded axis for the recorded read. The stored
triples have the count the arithmetic gives. The postings folded by every read equal the events the range holds, counted from the stream and not from a query. No posting is forward-dated, and none reaches
back further than the reach. A wrong result fails the run. **Time never does.** The seconds, folded postings, periods folded, graphs named and postings scanned go to `late_posting.json` and
`late_posting.md` here, which are generated. The folded and scanned counts are engine-independent and the time is not. `scanned` is the postings in the graphs a read names, and for the floor every posting in
the account's subtree.

Run `mise exec -- python benchmark/ledger-posting-cost/late_posting.py`. `LEDGER_LATE_MAX` caps the events (default 50000), `LEDGER_LATE_QUICK=1` runs the smallest size only. The store is a temporary
directory removed when the run ends, including on failure."""

from __future__ import annotations

import json
import os
import random
import statistics
import sys
import tempfile
import time
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path

import pyoxigraph as ox

import check as c

HERE = Path(__file__).resolve().parent
EVERY = c.CHECKPOINT_EVERY
SIZES = (5_000, 20_000, 50_000)
RATES = (0.0, 0.01, 0.05, 0.20)
REACHES = (1, 10, 40)  # periods
REPS = 15
FLOOR_REPS = 5
POSTING_TRIPLES = c.POSTING_TRIPLES + 1  # and the effective position
READS = ("as-of-effective, no reach cap", "as-of-effective, declared reach cap", "as-of-recorded", "unpartitioned fold on effective")


def assert_never_forward(effective: list[int]) -> None:
    """The ratified bound, as a model rule. The posting recorded at position e takes effect at a position from 1 to e."""
    for e, x in enumerate(effective, start=1):
        if not 1 <= x <= e:
            raise c.WrongResult(f"the posting recorded at {e} takes effect at {x}, which is not between 1 and its recorded position")


def effective_positions(count: int, rate: float, reach_events: int) -> list[int]:
    """The effective position of events 1 to count. A fraction `rate` are late, taking effect 1 to `reach_events` events before they are recorded, and the rest take effect where they are recorded.

    Both random draws are made for every event, so the late events at a lower rate are among those at a higher rate and the distance depends only on the reach."""
    rng = random.Random(c.SEED + 1)
    out = []
    for e in range(1, count + 1):
        late, distance = rng.random(), rng.random()
        if e > 1 and reach_events > 0 and late < rate:
            out.append(e - 1 - int(distance * min(reach_events, e - 1)))
        else:
            out.append(e)
    assert_never_forward(out)
    if any(e - x > reach_events for e, x in enumerate(out, start=1)):
        raise c.WrongResult(f"a posting reaches back further than {reach_events}")
    return out


def period_of(position: int) -> int:
    return (position - 1) // EVERY


def expected_stored(count: int) -> int:
    accounts = c.build_tree()
    return c.structure_triples(accounts) + count * POSTING_TRIPLES + len(accounts) * (count // EVERY) * c.CHECKPOINT_TRIPLES


def quads(accounts, stream, effective: list[int], model: c.Model):
    for a in accounts:
        yield ox.Quad(a.iri, c.RDF_TYPE, c.n("Account"))
        yield ox.Quad(a.iri, c.n("statedAmount"), c.num(c.STATED[a.level]))
        if a.parent is not None:
            yield ox.Quad(a.iri, c.n("partOf"), accounts[a.parent].iri)
    for e, (contract, debit, amount) in enumerate(stream, start=1):
        graph = c.period_graph(accounts[accounts[contract].parent].iri, period_of(e))
        yield from c.posting(e, accounts[contract], debit, amount, None, graph)
        subject = ox.NamedNode(f"urn:posting:{e}:{accounts[contract].iri.value.rsplit(':', 1)[1]}")
        yield ox.Quad(subject, c.n("effectivePosition"), c.num(effective[e - 1]), graph)
    for position, balances in model.at_checkpoints.items():
        for i, a in enumerate(accounts):
            cp = ox.NamedNode(f"urn:checkpoint:{position}:{a.iri.value.rsplit(':', 1)[1]}")
            yield ox.Quad(cp, c.RDF_TYPE, c.n("Checkpoint"))
            yield ox.Quad(cp, c.n("account"), a.iri)
            yield ox.Quad(cp, c.n("position"), c.num(position))
            yield ox.Quad(cp, c.n("balance"), c.num(balances[i]))


def balances_as_of(accounts, stream, axis: list[int], point: int) -> list[int]:
    """Every account's balance with every posting whose position on the axis is at or before the point, by the plainest arithmetic and with no checkpoint."""
    balance = [c.STATED[a.level] for a in accounts]
    for e, (contract, debit, amount) in enumerate(stream, start=1):
        if axis[e - 1] <= point:
            for i in c.ancestors(accounts, contract):
                balance[i] += -amount if debit else amount
    return balance


def counts_in(accounts, stream, axis: list[int], after: int, upto: int, limit: int) -> list[int]:
    """For every account, the events in its subtree recorded after `after` and up to `upto` whose position on the axis is at or before `limit`, counted from the stream."""
    out = [0] * len(accounts)
    for e in range(max(after, 0) + 1, upto + 1):
        if axis[e - 1] <= limit:
            for i in c.ancestors(accounts, stream[e - 1][0]):
                out[i] += 1
    return out


def graphs_for(account: c.Account, first: int, last: int) -> list[ox.NamedNode]:
    return [c.period_graph(layer, period) for period in range(first, last + 1) for layer in c.layers_of(account)]


def covered(upto: int, events: int) -> int:
    """The last recorded position of the last graph a read to `upto` names, since a graph is taken whole."""
    return min(events, -(-upto // EVERY) * EVERY)


def fold_effective(store, account, after: int, point: int, upto: int) -> tuple[int, int, list[ox.NamedNode]]:
    """(the signed sum, the postings folded, the graphs named) for the graphs of the periods holding postings recorded after `after` and up to `upto`, filtered on effective position at or before the point."""
    names = graphs_for(account, max(after, 0) // EVERY, period_of(upto))
    own = c.OWN.format(acct=account.iri.value) if account.level == 0 else ""
    block = c.graph_block(names, f"{own} ?p l:effectivePosition ?eff .", f"FILTER(?eff <= {point})")
    (row,) = store.query(f"{c.PREFIX}SELECT (SUM(?signed) AS ?sum) (COUNT(?p) AS ?folded) WHERE {{ {block} BIND(IF(?d = l:Debit, -?a, ?a) AS ?signed) }}")
    return (c._integer(row["sum"]) if row["sum"] is not None else 0), c._integer(row["folded"]), names


def read_effective(store, account, point: int, events: int, cap: int | None) -> tuple[int, int, list[ox.NamedNode], int]:
    """(the balance as of the effective position, the postings folded, the graphs named, the checkpoint position used). The checkpoint at the latest close at or before the point, then the later periods.

    With no cap the periods run to the end of the history, which is all the ratified bound supports. With a cap they stop at the period holding the point plus the cap."""
    after, start = c.checkpoint(store, account, point, EVERY, c.stated(store, account.iri))
    upto = events if cap is None else min(events, point + cap)
    total, folded, names = fold_effective(store, account, after, point, upto)
    return start + total, folded, names, after


def read_recorded(store, account, point: int) -> tuple[int, int, list[ox.NamedNode], int]:
    """The existing as-of-recorded read, as `check.read` does it for period graphs."""
    after, start = c.checkpoint(store, account, point, EVERY, c.stated(store, account.iri))
    total, folded = c.fold_graphs(store, account, after, point, EVERY)
    return start + total, folded, graphs_for(account, max(after, 0) // EVERY, period_of(point)), after


def read_floor(store, account, point: int) -> tuple[int, int]:
    """The fold of the whole history filtered on effective position, with no checkpoint and no graph named."""
    text = (f"{c.PREFIX}SELECT (SUM(?signed) AS ?sum) (COUNT(?p) AS ?folded) WHERE {{ ?acc l:partOf* <{account.iri.value}> . "
            f"GRAPH ?g {{ ?p l:account ?acc ; l:effectivePosition ?eff ; l:direction ?d ; l:amount ?a . FILTER(?eff <= {point}) }} BIND(IF(?d = l:Debit, -?a, ?a) AS ?signed) }}")
    (row,) = store.query(text)
    return c.stated(store, account.iri) + (c._integer(row["sum"]) if row["sum"] is not None else 0), c._integer(row["folded"])


def read_points(events: int) -> dict[str, int]:
    """Recent, mid and old in the history, each half a period past a close so none is itself a close."""
    return {"recent": events - EVERY // 2, "mid": events // 2 + EVERY // 2, "old": events // 10 + EVERY // 2}


@dataclass
class Row:
    events: int
    rate: float
    reach_periods: int
    late: int
    observed_reach_periods: int
    age: str
    point: int
    read: str
    after: int
    periods: int
    graphs: int
    scanned: int
    folded: int
    stragglers: int
    read_ms: float


def measure(events: int, rate: float, reach_periods: int, directory: str | None = None) -> list[Row]:
    accounts = c.tree()
    stream = c.events(events, accounts)
    reach = reach_periods * EVERY if rate > 0 else 0
    effective = effective_positions(events, rate, reach)
    recorded = list(range(1, events + 1))
    late = sum(1 for e, x in enumerate(effective, start=1) if x != e)
    observed = max((period_of(e) - period_of(x) for e, x in enumerate(effective, start=1)), default=0)
    points = read_points(events)
    model = c.run_model(events, EVERY, [], accounts, stream)
    programme = next(i for i, a in enumerate(accounts) if a.level == 2)
    sizes = Counter(c.period_graph(accounts[accounts[contract].parent].iri, period_of(e)) for e, (contract, _, _) in enumerate(stream, start=1))
    where = f"{events} events, rate {rate}, reach {reach_periods}"

    with tempfile.TemporaryDirectory(prefix="ledger-late-posting-", dir=directory) as tmp:
        store = ox.Store(tmp)
        store.bulk_extend(quads(accounts, stream, effective, model))
        store.flush()
        stored = len(store)
        if stored != expected_stored(events):
            raise c.WrongResult(f"{where}: stored {stored} triples, expected {expected_stored(events)}")
        (row,) = store.query("SELECT (COUNT(DISTINCT ?g) AS ?n) WHERE { GRAPH ?g { ?s ?p ?o } }")
        if int(row["n"].value) != len(sizes):
            raise c.WrongResult(f"{where}: {row['n'].value} graphs in the store, {len(sizes)} by the arithmetic")

        plans = {}
        for age, point in points.items():
            want_effective = balances_as_of(accounts, stream, effective, point)
            want_recorded = balances_as_of(accounts, stream, recorded, point)
            after_close = max((p for p in model.at_checkpoints if p <= point), default=0)
            upto = {"no reach cap": events, "declared reach cap": min(events, point + reach)}
            held = {"no reach cap": counts_in(accounts, stream, effective, after_close, covered(upto["no reach cap"], events), point),
                    "declared reach cap": counts_in(accounts, stream, effective, after_close, covered(upto["declared reach cap"], events), point)}
            held_recorded = counts_in(accounts, stream, recorded, after_close, point, point)
            for i, account in enumerate(accounts):
                for label, cap in (("no reach cap", None), ("declared reach cap", reach)):
                    balance, folded, _, _ = read_effective(store, account, point, events, cap)
                    if balance != want_effective[i]:
                        raise c.WrongResult(f"{where}: {account.iri.value} as of effective {point} with {label} reads {balance}, the model gives {want_effective[i]}")
                    if folded != held[label][i]:
                        raise c.WrongResult(f"{where}: {account.iri.value} as of effective {point} with {label} folded {folded}, the range holds {held[label][i]}")
                balance, folded, _, _ = read_recorded(store, account, point)
                if balance != want_recorded[i]:
                    raise c.WrongResult(f"{where}: {account.iri.value} as of recorded {point} reads {balance}, the model gives {want_recorded[i]}")
                if folded != held_recorded[i]:
                    raise c.WrongResult(f"{where}: {account.iri.value} as of recorded {point} folded {folded}, the range holds {held_recorded[i]}")
                if account.level >= 1:  # the floor is slow, so the layers and programmes only
                    balance, folded = read_floor(store, account, point)
                    whole = counts_in(accounts, stream, effective, 0, events, point)[i]
                    if balance != want_effective[i]:
                        raise c.WrongResult(f"{where}: the unpartitioned fold of {account.iri.value} as of effective {point} reads {balance}, the model gives {want_effective[i]}")
                    if folded != whole:
                        raise c.WrongResult(f"{where}: the unpartitioned fold of {account.iri.value} as of effective {point} folded {folded}, the stream holds {whole}")

        measured = []
        for age, point in points.items():
            account = accounts[programme]
            by_read = {}
            for label, cap in (("as-of-effective, no reach cap", None), ("as-of-effective, declared reach cap", reach)):
                _, folded, names, after = read_effective(store, account, point, events, cap)
                upto = events if cap is None else min(events, point + cap)
                by_read[label] = (after, folded, names, counts_in(accounts, stream, effective, point, covered(upto, events), point)[programme])
            _, folded, names, after = read_recorded(store, account, point)
            by_read["as-of-recorded"] = (after, folded, names, 0)
            whole = counts_in(accounts, stream, effective, 0, events, point)[programme]
            by_read["unpartitioned fold on effective"] = (-1, whole, [], counts_in(accounts, stream, effective, point, events, point)[programme])
            if any(v[1] > whole for k, v in by_read.items() if k != "as-of-recorded" and k != "unpartitioned fold on effective"):
                raise c.WrongResult(f"{where}: a partitioned effective read as of {point} folded more than the unpartitioned fold of {whole}")
            measured.append((age, point, by_read))

        times = {(age, label): [] for age, _, by_read in measured for label in by_read}
        for _ in range(REPS):  # interleaved, so drift in the machine falls on every read alike
            for age, point, _ in measured:
                account = accounts[programme]
                for label, run in (("as-of-effective, no reach cap", lambda p: read_effective(store, account, p, events, None)),
                                   ("as-of-effective, declared reach cap", lambda p: read_effective(store, account, p, events, reach)),
                                   ("as-of-recorded", lambda p: read_recorded(store, account, p))):
                    begin = time.perf_counter()
                    run(point)
                    times[(age, label)].append(time.perf_counter() - begin)
        for _ in range(FLOOR_REPS):
            for age, point, _ in measured:
                begin = time.perf_counter()
                read_floor(store, accounts[programme], point)
                times[(age, "unpartitioned fold on effective")].append(time.perf_counter() - begin)
        del store

    rows = []
    for age, point, by_read in measured:
        for label in READS:
            after, folded, names, stragglers = by_read[label]
            periods = len(names) // len(c.layers_of(accounts[programme])) if names else 0
            scanned = sum(sizes[g] for g in names) if names else sum(1 for contract, _, _ in stream if programme in c.ancestors(accounts, contract))
            rows.append(Row(events, rate, reach_periods if rate > 0 else 0, late, observed, age, point, label, after, periods, len(names), scanned, folded, stragglers,
                            1000 * statistics.median(times[(age, label)])))
    return rows


def run(sizes=SIZES, directory: str | None = None) -> list[Row]:
    rows: list[Row] = []
    print(f"{'events':>6} {'rate':>5} {'reach':>5} {'late':>5} {'age':6} {'point':>6} {'read':36} {'after':>6} {'periods':>7} {'scanned':>7} {'folded':>6} {'strag':>5} {'read ms':>8}")
    for events in sizes:
        for rate in RATES:
            for reach in (REACHES if rate > 0 else (0,)):
                for r in measure(events, rate, reach, directory):
                    rows.append(r)
                    print(f"{r.events:>6} {r.rate:>5} {r.reach_periods:>5} {r.late:>5} {r.age:6} {r.point:>6} {r.read:36} {r.after:>6} {r.periods:>7} {r.scanned:>7} {r.folded:>6} "
                          f"{r.stragglers:>5} {r.read_ms:>8.3f}", flush=True)
    return rows


def write_report(rows: list[Row], directory: Path = HERE) -> None:
    data = {"environment": c.environment() | {"reps": str(REPS), "floor_reps": str(FLOOR_REPS), "rates": str(RATES), "reaches_periods": str(REACHES)}, "rows": [asdict(r) for r in rows]}
    (directory / "late_posting.json").write_text(json.dumps(data, indent=2), encoding="utf-8", newline="\n")
    lines = ["# Ledger as-of-effective read (generated, not committed)", "", "```", json.dumps(data["environment"]), "```", "",
             "| events | rate | reach periods | late | observed reach periods | age | point | read | after | periods folded | graphs | scanned | folded | stragglers | read ms | ms per 1000 scanned |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r.events} | {r.rate} | {r.reach_periods} | {r.late} | {r.observed_reach_periods} | {r.age} | {r.point} | {r.read} | {r.after} | {r.periods} | {r.graphs} | {r.scanned} | "
                     f"{r.folded} | {r.stragglers} | {r.read_ms:.3f} | {1000 * r.read_ms / r.scanned if r.scanned else 0:.3f} |")
    (directory / "late_posting.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    cap = int(os.environ.get("LEDGER_LATE_MAX", SIZES[-1]))
    sizes = [s for s in SIZES if s <= cap] or [cap]
    if os.environ.get("LEDGER_LATE_QUICK"):
        sizes = sizes[:1]
    try:
        rows = run(sizes)
    except c.WrongResult as error:
        print(f"WRONG RESULT: {error}", file=sys.stderr)
        return 1
    write_report(rows)
    print(f"report written to {HERE / 'late_posting.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
