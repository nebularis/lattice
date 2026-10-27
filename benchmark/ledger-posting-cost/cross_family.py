# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""What an as-of read costs when its range crosses a change of closing recurrence (ADR-A124).

`check.py` and `sweep.py` hold one closing interval for the whole history. If an account partition's closing recurrence changes, a new graph family starts, so books
before and after the change sit in different families with different intervals. An as-of read takes the latest checkpoint and folds the graphs after it. When the change
falls between two closes, the old family's last period is cut short at the change and records no close, so the range from the latest checkpoint to the read point
names graphs of two families. This measures whether that read stays flat, or degrades toward the cost of folding the whole history without partition. A flat read
supports a graph name derived from the position, a degraded one supports a recorded name.

A **schedule** is a tuple of `(start, interval)`, one per family. Family `f` holds events after `start` up to the next family's start, closes every `interval` events counted
from its own start, and names its graphs `urn:graph:f{f}:{layer}:{period}`. The partitioned unit stays the layer subtree, as in `check.py`.

**Cases per history size.** Two scenarios, refining (500 then 100) and coarsening (100 then 500), with the change in the middle of an old period. Each has a cross read (latest
checkpoint in the old family, read point in the new one), a control wholly inside the coarse family with the same range width, a control wholly inside the fine family, and
the unpartitioned fold of the whole history up to the cross read's point.

**Pass criterion.** Every account's balance equals the model's at every read point. The stored triples have the count the schedule's arithmetic gives. The postings folded
by each partitioned read equal the events that lie in its range. A cross read names two families and a control names one. A partitioned read folds no more than the
unpartitioned fold. A wrong result fails the run. **Time never does.** The seconds, folded postings, graphs named and postings scanned go to `cross_family.json` and
`cross_family.md` here, which are generated. The folded count is engine-independent and the time is not.

Run `mise exec -- python benchmark/ledger-posting-cost/cross_family.py`. `LEDGER_CROSS_MAX` caps the events (default 50000), `LEDGER_CROSS_QUICK=1` runs the smallest size
only. The store is a temporary directory removed when the run ends, including on failure."""

from __future__ import annotations

import json
import math
import os
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
SIZES = (5_000, 20_000, 50_000)
SCENARIOS = (("refining", 500, 100), ("coarsening", 100, 500))
REPS = 15
UNPARTITIONED_REPS = 5

Schedule = tuple[tuple[int, int], ...]


def family_end(schedule: Schedule, family: int) -> int | None:
    """The last event position of the family, or None for the last family, which is open."""
    return schedule[family + 1][0] if family + 1 < len(schedule) else None


def family_of(schedule: Schedule, position: int) -> int:
    """The family holding the event at the position (1 or more)."""
    return max(f for f, (start, _) in enumerate(schedule) if start < position)


def position_to_period(schedule: Schedule, position: int) -> tuple[int, int]:
    """(family, period) of the event at the position."""
    family = family_of(schedule, position)
    start, interval = schedule[family]
    return family, (position - start - 1) // interval


def latest_close(schedule: Schedule, point: int) -> int:
    """The position of the latest close at or before the point, or -1 before the first. Computed, never searched for."""
    for family in reversed(range(len(schedule))):
        start, interval = schedule[family]
        end = family_end(schedule, family)
        reach = point if end is None else min(point, end)
        if reach - start >= interval:
            return start + ((reach - start) // interval) * interval
    return -1


def closes(schedule: Schedule, count: int) -> list[int]:
    """Every close position up to count, across the families."""
    out = []
    for family, (start, interval) in enumerate(schedule):
        end = family_end(schedule, family)
        out.extend(range(start + interval, min(count, end if end is not None else count) + 1, interval))
    return out


def graph_name(schedule: Schedule, layer: ox.NamedNode, position: int) -> ox.NamedNode:
    family, period = position_to_period(schedule, position)
    return named(family, layer, period)


def named(family: int, layer: ox.NamedNode, period: int) -> ox.NamedNode:
    return ox.NamedNode(f"urn:graph:f{family}:{layer.value.rsplit(':', 1)[1]}:{period}")


def families_in(names: list[ox.NamedNode]) -> set[int]:
    return {int(g.value.split(":")[2][1:]) for g in names}


def expected_stored(count: int, schedule: Schedule) -> int:
    accounts = c.build_tree()
    return c.structure_triples(accounts) + count * c.POSTING_TRIPLES + len(accounts) * len(closes(schedule, count)) * c.CHECKPOINT_TRIPLES


def run_model(closing: set[int], points: set[int], accounts, stream) -> c.Model:
    balance = [c.STATED[a.level] for a in accounts]
    model = c.Model({}, {}, {})
    if 0 in points:
        model.at_points[0] = list(balance)
    for e, (contract, debit, amount) in enumerate(stream, start=1):
        for i in c.ancestors(accounts, contract):
            balance[i] += -amount if debit else amount
        if e in points:
            model.at_points[e] = list(balance)
        if e in closing:
            model.at_checkpoints[e] = list(balance)
    return model


def quads(accounts, stream, model: c.Model, schedule: Schedule):
    for a in accounts:
        yield ox.Quad(a.iri, c.RDF_TYPE, c.n("Account"))
        yield ox.Quad(a.iri, c.n("statedAmount"), c.num(c.STATED[a.level]))
        if a.parent is not None:
            yield ox.Quad(a.iri, c.n("partOf"), accounts[a.parent].iri)
    for e, (contract, debit, amount) in enumerate(stream, start=1):
        yield from c.posting(e, accounts[contract], debit, amount, None, graph_name(schedule, accounts[accounts[contract].parent].iri, e))
    for position, balances in model.at_checkpoints.items():
        for i, a in enumerate(accounts):
            cp = ox.NamedNode(f"urn:checkpoint:{position}:{a.iri.value.rsplit(':', 1)[1]}")
            yield ox.Quad(cp, c.RDF_TYPE, c.n("Checkpoint"))
            yield ox.Quad(cp, c.n("account"), a.iri)
            yield ox.Quad(cp, c.n("position"), c.num(position))
            yield ox.Quad(cp, c.n("balance"), c.num(balances[i]))


def checkpoint(store, account, point: int, schedule: Schedule, base: int) -> tuple[int, int]:
    position = latest_close(schedule, point)
    if position < 0:
        return -1, base
    (row,) = store.query(f"{c.PREFIX}SELECT ?b WHERE {{ <urn:checkpoint:{position}:{account.iri.value.rsplit(':', 1)[1]}> l:balance ?b }}")
    return position, c._integer(row["b"])


def fold_graphs(store, account, after: int, point: int, schedule: Schedule) -> tuple[int, int, list[ox.NamedNode]]:
    """(the signed sum, the postings folded, the graphs named) for events after `after` and up to `point`, naming the graphs of every family the range touches.

    As in `check.fold_graphs`, a graph is taken whole unless a bound cuts its period. A period ends at its interval or at the end of its family, whichever is first."""
    by_bound: dict[str, list[ox.NamedNode]] = {}
    names: list[ox.NamedNode] = []
    for family, (start, interval) in enumerate(schedule):
        end = family_end(schedule, family)
        lo, hi = max(after, start) + 1, point if end is None else min(point, end)
        if lo > hi:
            continue
        first, last = (lo - 1 - start) // interval, (hi - 1 - start) // interval
        for period in range(first, last + 1):
            period_end = start + (period + 1) * interval
            period_end = period_end if end is None else min(period_end, end)
            low = period == first and lo - 1 != start + first * interval
            high = period == last and hi != period_end
            bound = "FILTER(" + " && ".join(([f"?pos > {after}"] if low else []) + ([f"?pos <= {point}"] if high else [])) + ")" if low or high else ""
            graphs = [named(family, layer, period) for layer in c.layers_of(account)]
            by_bound.setdefault(bound, []).extend(graphs)
            names.extend(graphs)
    if not by_bound:
        return 0, 0, []
    scope = c.OWN.format(acct=account.iri.value) if account.level == 0 else ""
    blocks = " UNION ".join(c.graph_block(g, scope, bound) for bound, g in by_bound.items())
    text = f"{c.PREFIX}SELECT (SUM(?signed) AS ?sum) (COUNT(?p) AS ?folded) WHERE {{ {blocks} BIND(IF(?d = l:Debit, -?a, ?a) AS ?signed) }}"
    (row,) = store.query(text)
    return (c._integer(row["sum"]) if row["sum"] is not None else 0), c._integer(row["folded"]), names


def read(store, account, point: int, schedule: Schedule) -> tuple[int, int, list[ox.NamedNode]]:
    """(the balance as of the point, the postings folded, the graphs named)."""
    base = c.stated(store, account.iri)
    after, start = checkpoint(store, account, point, schedule, base)
    total, folded, names = fold_graphs(store, account, after, point, schedule)
    return start + total, folded, names


def read_unpartitioned(store, account, point: int) -> tuple[int, int]:
    """The fold of the whole history up to the point, with no checkpoint and no graph named. This is the cost the partition is meant to avoid."""
    text = (f"{c.PREFIX}SELECT (SUM(?signed) AS ?sum) (COUNT(?p) AS ?folded) WHERE {{ ?acc l:partOf* <{account.iri.value}> . "
            f"GRAPH ?g {{ ?p l:account ?acc ; l:position ?pos ; l:direction ?d ; l:amount ?a . FILTER(?pos <= {point}) }} BIND(IF(?d = l:Debit, -?a, ?a) AS ?signed) }}")
    (row,) = store.query(text)
    return c.stated(store, account.iri) + (c._integer(row["sum"]) if row["sum"] is not None else 0), c._integer(row["folded"])


@dataclass
class Case:
    scenario: str
    name: str
    point: int
    crossing: bool


def cases_for(scenario: str, old: int, new: int, events: int) -> tuple[Schedule, list[Case]]:
    """The schedule and the read points. The change falls half an old period past a close, so it is not itself a close."""
    lcm = math.lcm(old, new)
    base = (events // 2 // lcm) * lcm  # a close of both intervals
    change = base + old // 2
    schedule: Schedule = ((0, old), (change, new))
    cross = change + new // 2
    width = cross - latest_close(schedule, cross)
    first_new_close = change + new
    if old >= new:  # the old family is the coarse one
        coarse = base - old + width
        fine = first_new_close + new // 2
    else:
        coarse = first_new_close + width
        fine = base - old + old // 2
    return schedule, [Case(scenario, "cross", cross, True), Case(scenario, "control, coarse family, same width", coarse, False),
                      Case(scenario, "control, fine family", fine, False)]


def events_in(stream, accounts, subtree: int, after: int, point: int) -> int:
    """The events after `after` and up to `point` that fall in the account's subtree, counted from the stream and not from any query."""
    inside = set(c.layers_of(accounts[subtree]))
    own = [e for e in range(max(after, 0) + 1, point + 1)]
    if accounts[subtree].level == 0:
        return sum(1 for e in own if stream[e - 1][0] == subtree)
    return sum(1 for e in own if accounts[accounts[stream[e - 1][0]].parent].iri in inside)


@dataclass
class Row:
    scenario: str
    events: int
    change: int
    case: str
    point: int
    after: int
    families: int
    graphs: int
    scanned: int
    folded: int
    read_ms: float


def measure(scenario: str, old: int, new: int, events: int, directory: str | None = None) -> list[Row]:
    accounts = c.tree()
    stream = c.events(events, accounts)
    schedule, cases = cases_for(scenario, old, new, events)
    points = {0, events} | {case.point for case in cases}
    model = run_model(set(closes(schedule, events)), points, accounts, stream)
    programme = next(i for i, a in enumerate(accounts) if a.level == 2)
    sizes = Counter(graph_name(schedule, accounts[accounts[contract].parent].iri, e) for e, (contract, _, _) in enumerate(stream, start=1))

    with tempfile.TemporaryDirectory(prefix="ledger-cross-family-", dir=directory) as tmp:
        store = ox.Store(tmp)
        store.bulk_extend(quads(accounts, stream, model, schedule))
        store.flush()
        stored = len(store)
        if stored != expected_stored(events, schedule):
            raise c.WrongResult(f"{scenario} {events}: stored {stored} triples, expected {expected_stored(events, schedule)}")
        (row,) = store.query("SELECT (COUNT(DISTINCT ?g) AS ?n) WHERE { GRAPH ?g { ?s ?p ?o } }")
        if int(row["n"].value) != len(sizes):
            raise c.WrongResult(f"{scenario} {events}: {row['n'].value} graphs in the store, {len(sizes)} by the schedule")

        for case in cases:  # every account, so the balance is checked beyond the one timed
            for i, account in enumerate(accounts):
                balance, folded, _ = read(store, account, case.point, schedule)
                if balance != model.at_points[case.point][i]:
                    raise c.WrongResult(f"{scenario} {events}: {account.iri.value} as of {case.point} reads {balance}, the model gives {model.at_points[case.point][i]}")
                held = events_in(stream, accounts, i, latest_close(schedule, case.point), case.point)
                if folded != held:
                    raise c.WrongResult(f"{scenario} {events}: {account.iri.value} as of {case.point} folded {folded}, the range holds {held}")

        cross = cases[0]
        measured = []
        for case in cases:
            balance, folded, names = read(store, accounts[programme], case.point, schedule)
            families = families_in(names)
            if case.crossing != (len(families) > 1) or (not case.crossing and len(families) != 1):
                raise c.WrongResult(f"{scenario} {events}: {case.name} names families {sorted(families)}")
            measured.append((case, folded, names, latest_close(schedule, case.point)))
        balance, whole = read_unpartitioned(store, accounts[programme], cross.point)
        if balance != model.at_points[cross.point][programme]:
            raise c.WrongResult(f"{scenario} {events}: the unpartitioned fold reads {balance}, the model gives {model.at_points[cross.point][programme]}")
        if any(folded > whole for _, folded, _, _ in measured):
            raise c.WrongResult(f"{scenario} {events}: a partitioned read folded more than the unpartitioned fold of {whole}")

        times = {case.name: [] for case in cases}
        unpartitioned = []
        for _ in range(REPS):  # interleaved, so drift in the machine falls on every case alike
            for case in cases:
                begin = time.perf_counter()
                read(store, accounts[programme], case.point, schedule)
                times[case.name].append(time.perf_counter() - begin)
        for _ in range(UNPARTITIONED_REPS):
            begin = time.perf_counter()
            read_unpartitioned(store, accounts[programme], cross.point)
            unpartitioned.append(time.perf_counter() - begin)
        del store

    change = schedule[1][0]
    rows = [Row(scenario, events, change, case.name, case.point, after, len(families_in(names)), len(names), sum(sizes[g] for g in names), folded,
                1000 * statistics.median(times[case.name])) for case, folded, names, after in measured]
    rows.append(Row(scenario, events, change, "unpartitioned fold of the whole history", cross.point, -1, 0, 0, whole, whole, 1000 * statistics.median(unpartitioned)))
    return rows


def run(sizes=SIZES, directory: str | None = None) -> list[Row]:
    rows: list[Row] = []
    print(f"{'scenario':11} {'events':>6} {'change':>6} {'case':40} {'point':>6} {'after':>6} {'fam':>3} {'graphs':>6} {'scanned':>7} {'folded':>6} {'read ms':>8}")
    for events in sizes:
        for scenario, old, new in SCENARIOS:
            for r in measure(scenario, old, new, events, directory):
                rows.append(r)
                print(f"{r.scenario:11} {r.events:>6} {r.change:>6} {r.case:40} {r.point:>6} {r.after:>6} {r.families:>3} {r.graphs:>6} {r.scanned:>7} {r.folded:>6} {r.read_ms:>8.3f}", flush=True)
    return rows


def write_report(rows: list[Row], directory: Path = HERE) -> None:
    data = {"environment": c.environment() | {"reps": str(REPS), "unpartitioned_reps": str(UNPARTITIONED_REPS)}, "rows": [asdict(r) for r in rows]}
    (directory / "cross_family.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    lines = ["# Ledger cross-family read (generated, not committed)", "", "```", json.dumps(data["environment"]), "```", "",
             "| scenario | events | change | case | point | after | families | graphs | scanned | folded | read ms |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r.scenario} | {r.events} | {r.change} | {r.case} | {r.point} | {r.after} | {r.families} | {r.graphs} | {r.scanned} | {r.folded} | {r.read_ms:.3f} |")
    (directory / "cross_family.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    cap = int(os.environ.get("LEDGER_CROSS_MAX", SIZES[-1]))
    sizes = [s for s in SIZES if s <= cap] or [cap]
    if os.environ.get("LEDGER_CROSS_QUICK"):
        sizes = sizes[:1]
    try:
        rows = run(sizes)
    except c.WrongResult as error:
        print(f"WRONG RESULT: {error}", file=sys.stderr)
        return 1
    write_report(rows)
    print(f"report written to {HERE / 'cross_family.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
