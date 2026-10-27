# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""What a finer graph partition costs (ADR-A124, MS-Q9).

`check.py` fixes the closing period at 500 events and compares five ways of recording a draw. This asks the other question: hold the events fixed, shorten the closing
period, and watch the number of named graphs rise while the postings stay the same. A shorter period also shrinks the fold, so the read should get faster before any
cost of holding many graphs makes it slower again. The event count at which it stops falling, if it does, is the ceiling on how fine a partition may be.

**Pass criterion.** At every interval the programme's balance equals the model's, and the store holds no more graphs than layers times periods, which is the arithmetic
the partition gives. A wrong balance or an impossible graph count fails the run. **Time never does.** The reported figures go to `sweep.md` and `sweep.json` here, which
are generated and git-ignored.

Run `mise run check:ledger-graph-partition`. `LEDGER_SWEEP_EVENTS` sets the event count (default 20000) and `LEDGER_SWEEP_QUICK=1` runs the three coarsest intervals.
The store is a temporary directory removed when the run ends, including on failure."""

from __future__ import annotations

import json
import os
import statistics
import sys
import tempfile
import time
from dataclasses import dataclass, asdict
from pathlib import Path

import pyoxigraph as ox

import check as c

HERE = Path(__file__).resolve().parent
INTERVALS = (5000, 1000, 500, 200, 100, 50, 20, 10)
REPS = 15
STRATEGY = "post-once-period-graphs"


@dataclass
class Point:
    """One closing interval, measured."""

    every: int
    graphs: int
    quads: int
    sst_files: int
    megabytes: float
    write_seconds: float
    folded: int
    read_ms: float
    open_ms: float


def store_files(directory: str) -> tuple[int, float]:
    """(SST files, megabytes on disk). TSD-39 made the file count worth watching on Oxigraph, where many separate bulk loads fragment the store."""
    entries = list(Path(directory).rglob("*"))
    return (sum(1 for f in entries if f.suffix == ".sst"),
            sum(f.stat().st_size for f in entries if f.is_file()) / 1e6)


def measure(every: int, events: int) -> Point:
    accounts = c.tree()
    stream = c.events(events, accounts)
    # read mid-period: on a close the checkpoint answers alone and the graph fold is never exercised
    point = events - max(1, every // 2)
    points = sorted(set(c.read_points(events, every)) | {point})
    model = c.run_model(events, every, points, accounts, stream)
    programme = next(i for i, a in enumerate(accounts) if a.level == 2)

    with tempfile.TemporaryDirectory(prefix="ledger-graph-partition-") as tmp:
        start = time.perf_counter()
        store = ox.Store(tmp)
        store.bulk_extend(c.quads_for(STRATEGY, accounts, stream, model, every))
        store.flush()
        store.optimize()
        write = time.perf_counter() - start
        quads = len(store)
        (row,) = store.query("SELECT (COUNT(DISTINCT ?g) AS ?n) WHERE { GRAPH ?g { ?s ?p ?o } }")
        graphs = int(row["n"].value)
        sst, megabytes = store_files(tmp)

        ceiling = len(c.layers_of(accounts[programme])) * c.PROGRAMMES * -(-events // every)
        if graphs > ceiling:
            raise c.WrongResult(f"every={every}: {graphs} graphs, more than the {ceiling} layers times periods allow")

        balance, folded = c.read(STRATEGY, store, accounts[programme], point, every)
        expected = model.at_points[point][programme]
        if balance != expected:
            raise c.WrongResult(f"every={every}: programme reads {balance}, the model gives {expected}")

        times = []
        for _ in range(REPS):
            begin = time.perf_counter()
            c.read(STRATEGY, store, accounts[programme], point, every)
            times.append(time.perf_counter() - begin)
        del store

        opens = []
        for _ in range(3):
            begin = time.perf_counter()
            reader = ox.Store.read_only(tmp)
            opens.append(time.perf_counter() - begin)
            del reader

    return Point(every, graphs, quads, sst, megabytes, write, folded,
                 1000 * statistics.median(times), 1000 * statistics.median(opens))


def write_report(points: list[Point], events: int, directory: Path = HERE) -> None:
    data = {"environment": c.environment() | {"events": str(events), "strategy": STRATEGY},
            "points": [asdict(p) for p in points]}
    (directory / "sweep.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    lines = ["# Ledger graph partition (generated, not committed)", "", "```", json.dumps(data["environment"]), "```", "",
             "| period | graphs | quads | SST | MB | write s | folded | read ms | open ms |",
             "|---|---|---|---|---|---|---|---|---|"]
    for p in points:
        lines.append(f"| {p.every} | {p.graphs} | {p.quads} | {p.sst_files} | {p.megabytes:.1f} | "
                     f"{p.write_seconds:.2f} | {p.folded} | {p.read_ms:.3f} | {p.open_ms:.1f} |")
    (directory / "sweep.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    events = int(os.environ.get("LEDGER_SWEEP_EVENTS", 20_000))
    intervals = INTERVALS[:3] if os.environ.get("LEDGER_SWEEP_QUICK") else INTERVALS
    print(f"{events} events, {STRATEGY}, shortening the closing period\n")
    head = f"{'period':>7} {'graphs':>7} {'quads':>9} {'SST':>5} {'MB':>7} {'write s':>8} {'folded':>7} {'read ms':>8} {'open ms':>8}"
    print(head)
    print("-" * len(head))
    points = []
    try:
        for every in intervals:
            p = measure(every, events)
            points.append(p)
            print(f"{p.every:>7} {p.graphs:>7} {p.quads:>9} {p.sst_files:>5} {p.megabytes:>7.1f} "
                  f"{p.write_seconds:>8.2f} {p.folded:>7} {p.read_ms:>8.3f} {p.open_ms:>8.1f}", flush=True)
    except c.WrongResult as error:
        print(f"WRONG RESULT: {error}", file=sys.stderr)
        return 1
    write_report(points, events)
    print(f"report written to {HERE / 'sweep.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
