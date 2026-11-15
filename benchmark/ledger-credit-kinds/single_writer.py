# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""One writer per ledger, against the guarded writers of `writes.py` (LG-18 part one, ADR-A124).

LG-17's writers each read the balances on a posting's path, write under a guard on the ledger's revision and try again when they lose a race. Here producers hand their requests to one writer through a queue, so no race is lost.
Three writers are compared on the same stores, preloads and seeded request lists as `writes.run_stress`:

- **reads**, `writes.Live`, which reads its path for every posting, as a guarded writer does.
- **keeps**, `Keeper`, which reads every account once and then settles from the balances it holds, so a posting costs its update alone.
- **keeps, batched**, `Keeper` with several postings in one update request and one move of the revision.

The load has two shapes. In a **closed** run each producer waits for its answer before it asks again, which gives the time a request waits. In a **backlog** run every request is queued before the writer starts, which gives
the writer's rate with nothing else in the way, and lets a batch fill.

**Pass criterion.** A single writer's records equal the replay of its commits on every store, the on-disk one included, since nothing races it. Its revisions are dense, and it never loses a race, which `write_one` raises on.
A wrong result raises `WrongResult`. **Time never fails the run.** The guarded writers are run beside it for comparison and asserted as `writes.py` asserts them.

Run `mise run check:ledger-credit-kinds-single-writer`. `LEDGER_WRITES_QUICK=1` runs the smallest sizes and `LEDGER_WRITES_REPORT_DIR` writes `single-writer-report.md` and `single-writer-report.json` elsewhere."""

from __future__ import annotations

import json
import os
import queue
import statistics
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import check as ck
import writes as w
from check import WrongResult

HERE = Path(__file__).resolve().parent
PRODUCERS = (1, 2, 4, 8)
BATCHES = (10, 100)
UTILISATION = 0.7  # the share of a writer's rate the capacity table plans for, so a request's wait stays near three times its service time


class Keeper(w.Live):
    """A writer that keeps the balances it has settled. It reads the revision and every account's balance once, when it is made, and after that settles from what it holds and reads nothing. It is right only while it is the
    ledger's one writer, which the guard on the revision still checks when it is on."""

    def __init__(self, backend, checkpoints: int = 0, guarded: bool = True):
        super().__init__(backend, checkpoints, guarded)
        begin = time.perf_counter()
        self.at = w.Live.revision(self)
        self.held = [w.Live.balance(self, i, self.at) for i in range(len(ck.TREE))]
        self.warm_s = time.perf_counter() - begin

    def revision(self) -> int:
        return self.at

    def balance(self, i: int, point: int) -> int:
        return self.held[i]

    def keep(self, plan: w.Plan) -> None:
        """Moves the balances held, and the revision, by a plan that was written."""
        r = plan.request
        if r.debit:
            ck.settle_debit(self.held, r.at, r.amount)
        elif ck.settle_credit(self.held, r.at, r.amount, r.kind) != (plan.applied, plan.cuts):
            raise WrongResult(f"{plan.tag}: the balances held settle the credit differently from the plan that was written")
        self.at += 1

    def commit(self, plan: w.Plan) -> bool:
        won = super().commit(plan)
        if won:
            self.keep(plan)
        return won


def write_batch(live: Keeper, items: list[tuple[w.Request, str]]) -> list[w.Plan]:
    """Settles the requests in order from the balances held and writes those not refused in one update request, which moves the revision by their number. A guarded batch is confirmed by asking for its last posting.
    Returns a plan for every request."""
    base, plans = live.at, []
    for request, tag in items:
        plan = live.prepare(request, tag)
        plans.append(plan)
        if not plan.refused:
            live.keep(plan)
    written = [p for p in plans if not p.refused]
    if not written:
        return plans
    by_graph: dict[str, list[str]] = {}
    for plan in written:
        lines, graph = live.lines(plan)
        by_graph.setdefault(graph, []).extend(lines)
    old, new = f"<{w.LEDGER}> <{w.REVISION}> {base}", f"<{w.LEDGER}> <{w.REVISION}> {base + len(written)}"
    body = f"{new} . " + " ".join(f"GRAPH <{g}> {{ {' '.join(lines)} }}" for g, lines in by_graph.items())
    begin = time.perf_counter()
    live.b.update(f"DELETE {{ {old} }} INSERT {{ {body} }} WHERE {{ {old} }}" if live.guarded else f"DELETE DATA {{ {old} }} ; INSERT DATA {{ {body} }}")
    done = time.perf_counter()
    if live.guarded:
        last, graph = written[-1], live.lines(written[-1])[1]
        if not live.select(f"SELECT ?x WHERE {{ GRAPH <{graph}> {{ <urn:posting:{last.tag}> a <{w.L}Posting> . BIND(1 AS ?x) }} }} LIMIT 1"):
            raise WrongResult(f"{last.tag}: a batch lost a race with no other writer")
    for plan in written:
        plan.seconds["update"], plan.seconds["confirm"] = (done - begin) / len(written), (time.perf_counter() - done) / len(written)
    return plans


@dataclass
class Ask:
    request: w.Request
    tag: str
    asked: float = 0.0
    waited: float = 0.0
    refused: bool = False
    done: threading.Event = field(default_factory=threading.Event)


def serve(live: w.Live, inbox: queue.Queue, batch: int, sizes: list[int], errors: list) -> None:
    """The one writer. Takes a request, and up to `batch` that are already waiting, writes them and answers each. `None` ends it."""
    try:
        while True:
            first = inbox.get()
            if first is None:
                return
            items, ended = [first], False
            while len(items) < batch and not ended:
                try:
                    more = inbox.get_nowait()
                except queue.Empty:
                    break
                ended = more is None
                if not ended:
                    items.append(more)
            if batch > 1:
                plans = write_batch(live, [(a.request, a.tag) for a in items])
            else:
                plans = [w.write_one(live, items[0].request, items[0].tag, retry=False)[0]]
            now = time.perf_counter()
            sizes.append(len(items))
            for ask, plan in zip(items, plans):
                ask.refused, ask.waited = plan.refused, now - ask.asked
                ask.done.set()
            if ended:
                return
    except BaseException as error:  # the writer's failure must reach the run, not die in its thread
        errors.append(error)


def produce(asks: list[Ask], inbox: queue.Queue, errors: list) -> None:
    """A producer of a closed run: asks, waits for its answer, asks again."""
    for ask in asks:
        ask.asked = time.perf_counter()
        inbox.put(ask)
        while not ask.done.wait(0.2):
            if errors:
                return


def run_queue(name: str, producers: int, writer: str = "reads", batch: int = 1, guarded: bool = True, backlog: bool = False, preload_count: int = w.STRESS_PRELOAD, total: int = w.STRESS_TOTAL) -> dict:
    """`producers` lists of seeded requests, the lists of `writes.run_stress`, handed to one writer. `writer` is "reads" or "keeps". In a backlog run the requests are queued in turn from each list before the writer starts."""
    if writer not in ("reads", "keeps") or (batch > 1 and writer != "keeps"):
        raise ValueError(f"no writer {writer} with a batch of {batch}")
    with w.opened(name) as backend:
        corpus, base = w.preload(backend, preload_count)
        lists = [[Ask(r, f"Q{p}.{n}") for n, r in enumerate(w.requests(total // producers, w.SHARE, ck.SEED + 100 + p))] for p in range(producers)]
        asks = [a for group in zip(*lists) for a in group]
        live = (Keeper if writer == "keeps" else w.Live)(backend, len(corpus.positions), guarded)
        inbox, errors, sizes = queue.Queue(), [], []
        server = threading.Thread(target=serve, args=(live, inbox, batch, sizes, errors))
        begin = time.perf_counter()
        if backlog:
            for ask in asks:
                ask.asked = begin
                inbox.put(ask)
            inbox.put(None)
            server.start()
        else:
            server.start()
            pool = [threading.Thread(target=produce, args=(group, inbox, errors)) for group in lists]
            for t in pool:
                t.start()
            for t in pool:
                t.join()
            inbox.put(None)
        server.join()
        wall = time.perf_counter() - begin
        if errors:
            raise errors[0]
        if not all(a.done.is_set() for a in asks):
            raise WrongResult(f"{name}: {sum(not a.done.is_set() for a in asks)} requests were never answered")
        commits = sum(not a.refused for a in asks)
        result = w.audit(backend, base, strict=True, expect=commits)
    waited = [1000 * a.waited for a in asks]
    return {"backend": name, "producers": producers, "writer": writer, "batch": batch, "guarded": guarded, "load": "backlog" if backlog else "closed", "preload": preload_count, "requests": len(asks),
            "commits": commits, "refused": len(asks) - commits, "wall_s": wall, "commits_per_s": commits / wall, "waited_mean_ms": statistics.mean(waited), "waited_p95_ms": w.p95(waited),
            "batches": len(sizes), "batch_mean": statistics.mean(sizes), "warm_s": getattr(live, "warm_s", 0.0), "audit": result}


def capacity(rate: float) -> dict:
    """What a writer's rate allows if it is planned at `UTILISATION` of it: postings a second, and a day of 86,400 seconds."""
    return {"planned_per_s": UTILISATION * rate, "planned_per_day": UTILISATION * rate * 86_400}


def label(r: dict) -> str:
    return f"{r['writer']}{f', batches of {r['batch']}' if r['batch'] > 1 else ''}{'' if r['guarded'] else ', no guard'}"


def render(data: dict) -> list[str]:
    out = ["# One writer per ledger (LG-18 part one)", "", "Environment: " + ", ".join(f"{k} {v}" for k, v in data["environment"].items() if v), ""]
    out += ["## The guarded writers, for comparison", "", "`writes.run_stress`, threads that each read, write under the guard and try again. Only the in-memory store is held to the replay.", ""]
    out += w.table(["backend", "threads", "commits", "lost races", "retries max", "wall s", "commits/s", "duplicate positions"],
                   [[s["backend"], s["threads"], s["commits"], s["lost_races"], s["retries_max"], f"{s['wall_s']:.2f}", f"{s['commits_per_s']:.0f}", s["audit"]["duplicate_positions"]] for s in data["guarded"]])
    out += ["", "## One writer, producers that wait for their answer", "", "Waited is the time from asking to the answer, queueing included. Every run equals the replay of its commits, on every store.", ""]
    head = ["backend", "producers", "writer", "commits", "refused", "wall s", "commits/s", "waited mean ms", "waited p95 ms", "batches", "postings a batch"]
    row = lambda r: [r["backend"], r["producers"], label(r), r["commits"], r["refused"], f"{r['wall_s']:.2f}", f"{r['commits_per_s']:.0f}", f"{r['waited_mean_ms']:.2f}", f"{r['waited_p95_ms']:.2f}", r["batches"], f"{r['batch_mean']:.1f}"]
    out += w.table(head, [row(r) for r in data["queue"] if r["load"] == "closed"])
    out += ["", "## One writer, a backlog", "", "Every request is queued before the writer starts, so commits a second is the writer's rate. Against guarded is that rate over the best rate of the guarded writers on the store. "
            f"Planned is {UTILISATION:.0%} of the rate, as postings a second and a day, for one ledger.", ""]
    best = {}
    for s in data["guarded"]:
        best[s["backend"]] = max(best.get(s["backend"], 0.0), s["commits_per_s"])
    rows = []
    for r in data["queue"]:
        if r["load"] == "backlog":
            plan = capacity(r["commits_per_s"])
            rows.append(row(r)[:7] + [f"{r['commits_per_s'] / best[r['backend']]:.1f}" if best.get(r["backend"]) else "", f"{plan['planned_per_s']:.0f}", f"{plan['planned_per_day']:,.0f}", f"{r['batch_mean']:.1f}", f"{r['warm_s']:.2f}"])
    out += w.table(head[:7] + ["against guarded", "planned a second", "planned a day", "postings a batch", "first read of the balances s"], rows)
    return out + [""]


def main() -> int:
    fast = w.quick()
    preload_count, total = (1_000, 200) if fast else (w.STRESS_PRELOAD, w.STRESS_TOTAL)
    names = ["oxigraph memory", "oxigraph disk"] + (["jena"] if ck.jena_available() else [])
    try:
        data: dict = {"environment": {**ck.environment(), "cpus": str(os.cpu_count()), "utilisation": str(UTILISATION), "quick": "yes" if fast else ""}, "guarded": [], "queue": []}
        for name in names:
            for threads in (1,) if name == "jena" else PRODUCERS:  # the test kit's Jena is driven by one thread at a time
                data["guarded"].append(w.run_stress(threads, True, preload_count, total, name))
                print(f"guarded {name} {threads} threads done", flush=True)
            for producers in PRODUCERS:
                for writer in ("reads", "keeps"):
                    data["queue"].append(run_queue(name, producers, writer, preload_count=preload_count, total=total))
                    print(f"closed {name} {producers} producers {writer} done", flush=True)
            for writer, batch, guarded in (("reads", 1, True), ("keeps", 1, True), ("keeps", 1, False)) + tuple(("keeps", b, True) for b in BATCHES):
                data["queue"].append(run_queue(name, PRODUCERS[-1], writer, batch, guarded, True, preload_count, total))
                print(f"backlog {name} {writer} batch {batch} {'guarded' if guarded else 'unguarded'} done", flush=True)
    except WrongResult as error:
        print(f"WRONG RESULT: {error}", file=sys.stderr)
        return 1
    directory = Path(os.environ.get("LEDGER_WRITES_REPORT_DIR") or HERE)
    (directory / "single-writer-report.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (directory / "single-writer-report.md").write_text("\n".join(render(data)), encoding="utf-8")
    print(f"report written to {directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
