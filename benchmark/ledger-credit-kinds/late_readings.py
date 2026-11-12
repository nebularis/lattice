# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The readings of a balance by effective day (LG-18 part two, LG-Q26, ADR-A124).

A posting may be recorded after the day it takes effect. `writes.py` showed that the writer's records are right in recorded order. This asks what a report shows for a day D, **as known at a recording R**, so only the
postings effective by D and recorded by R count. Three readings are taken at every ancestor.

- **A**, the recorded amounts: the stated amount, less debits, plus credits at the amount applied, less cuts. A sum.
- **B**, settled again: the same postings put through the benchmark's writer in effective order. An ordered read folded by the caller (TSD-72).
- **C**, flows and no balance: the debits, and the credits offered that the account accepts. Two sums.

It checks four things about them and times the reads.

1. *Reproducible.* A reading as known at R, read from a store that holds only what was recorded by R, equals the same reading from the whole store. A read that forgets R fails this.
2. *Possible.* How many readings lie below zero or above the account's ceiling, which no account ever held.
3. *The head.* With D equal to R, reading A is the ledger's recorded balance, always (STD-294), and reading B is counted where it is not.
4. *Restatement.* How far a day's figure, as known at R, has moved by the end of history.

**Cost.** A and C are read from the start of history and from the checkpoint at the close before the day. The checkpoint is sound because no posting is effective after it is recorded (STD-294), so everything recorded by
that close is effective by the day. B has no such start, since settling again in effective order may change every amount before it. C's read from the close is the flows since that close. A checkpoint that carried the
two totals would make it whole.

**Pass criterion.** Every engine read equals the model, the checkpointed reads equal the reads from the start, the early store agrees with the whole one, A equals the recorded balance at the head, and with no late
posting A and B agree and nothing is restated. A corpus in which a read that forgets R could not be told is refused. A wrong result raises `WrongResult`. **Time never fails the run.** Counts 2, 3 and 4 are reported.

Run `mise run check:ledger-credit-kinds-late-readings`. `LEDGER_WRITES_QUICK=1` runs the smallest size and `LEDGER_WRITES_REPORT_DIR` writes `late-readings-report.md` and `late-readings-report.json` elsewhere."""

from __future__ import annotations

import json
import os
import statistics
import sys
import time
from pathlib import Path

import check as ck
import writes as w
from check import WrongResult

HERE = Path(__file__).resolve().parent
EFF = w.STORED_EFFECTIVE
AGES = ("the day itself", "the close before", "two closes earlier")  # the day D against the recording R, by which a checkpointed read's cost is expected to grow
READS = ("recorded", "A from the start", "A from the close", "C from the start", "C since the close", "B")
FIGURES = ("A", "B", "debits", "offered")


def days_for(known: int) -> list[int]:
    """The days read as known at `known`: the recording's own position, the last close before it, and the close two periods before that, where they exist."""
    last = ck.EVERY_POSITIONS * ((known - 1) // ck.EVERY_POSITIONS)
    return [d for d in (known, last, last - 2 * ck.EVERY_POSITIONS) if d >= 1]


def chosen(postings: list[ck.Posting], effective: list[int], day: int, known: int) -> list[int]:
    """The postings, by index, effective by the day and recorded by the recording."""
    return [e for e, p in enumerate(postings) if effective[e] <= day and p.pos <= known]


def model_a(postings: list[ck.Posting], picked: list[int]) -> list[int]:
    out = [a.stated for a in ck.TREE]
    for e in picked:
        p = postings[e]
        cuts = dict(p.cuts)
        for i in ck.chain(p.contract):
            if p.debit:
                out[i] -= p.amount
            elif ck.accepts_kind(ck.TREE[i], p.kind):
                out[i] += p.applied - cuts.get(i, 0)
    return out


def model_b(postings: list[ck.Posting], effective: list[int], picked: list[int]) -> list[int]:
    return w.replay(w.Item(postings[e].contract, postings[e].debit, postings[e].amount, postings[e].kind) for e in sorted(picked, key=lambda e: (effective[e], e)))


def model_flows(postings: list[ck.Posting], picked: list[int]) -> tuple[list[int], list[int]]:
    """(the debits, the credits offered that the account accepts), at every account."""
    debits, offered = [0] * len(ck.TREE), [0] * len(ck.TREE)
    for e in picked:
        p = postings[e]
        for i in ck.chain(p.contract):
            if p.debit:
                debits[i] += p.amount
            elif ck.accepts_kind(ck.TREE[i], p.kind):
                offered[i] += p.amount
    return debits, offered


def number(x) -> int:
    return int(x) if x is not None else 0


def start(backend, index: int, day: int, checkpointed: bool) -> tuple[int, int]:
    """(the first period graph to read, the balance to start from): the checkpoint at the last close at or before the day, or the stated amount."""
    k = day // ck.EVERY_POSITIONS - 1
    if checkpointed and k >= 0:
        return k + 1, ck.checkpoint(backend, index, k)["stepwise"]
    return 0, ck.TREE[index].stated


def scan(index: int, day: int, known: int, first: int, amount: str) -> str:
    """The debits and credits of the subtree effective by the day and recorded by the recording, from period graph `first`, as `ck.postings_scan` reads them, with no OPTIONAL in the graph block (TSD-71)."""
    head = f"?p l:{EFF} ?eff ; l:position ?pos ; l:direction"
    bound = f"FILTER(?eff <= {day} && ?pos <= {known})"
    return (f"{{ VALUES ?g {{ {ck.graphs_for(index, known, first, True)} }} GRAPH ?g {{ "
            f"{{ {head} l:Debit ; l:amount ?v . BIND(l:Debit AS ?d) {bound} }} UNION "
            f"{{ {head} l:Credit ; l:{amount} ?v ; l:kind ?k . BIND(l:Credit AS ?d) {bound} }} UNION "
            f"{{ {head} l:Credit ; l:{amount} ?v . BIND(l:Credit AS ?d) {bound} FILTER NOT EXISTS {{ ?p l:kind ?z2 }} }} }} }}")


def read_a(backend, index: int, day: int, known: int, checkpointed: bool = False) -> int:
    a = ck.TREE[index]
    first, base = start(backend, index, day, checkpointed)
    (row,) = backend.select(f"{ck.PREFIX}SELECT (SUM(?signed) AS ?sum) WHERE {{ {scan(index, day, known, first, 'applied')} {ck.KIND_FILTER.format(acct=a.iri)} {ck.SIGNED.replace('?a', '?v')} }}")
    (cut,) = backend.select(f"{ck.PREFIX}SELECT (SUM(?cv) AS ?cut) WHERE {{ VALUES ?g {{ {ck.graphs_for(index, known, first, True)} }} GRAPH ?g {{ ?c l:cutAt <{a.iri}> ; l:cutValue ?cv ; l:cutOf ?p . "
                            f"?p l:{EFF} ?eff ; l:position ?pos . FILTER(?eff <= {day} && ?pos <= {known}) }} }}")
    return base + number(row[0]) - number(cut[0])


def read_flows(backend, index: int, day: int, known: int, since_close: bool = False) -> tuple[int, int]:
    """(the debits, the credits offered). With `since_close`, only what was recorded after the last close at or before the day."""
    first = max(day // ck.EVERY_POSITIONS, 0) if since_close else 0
    (row,) = backend.select(f"{ck.PREFIX}SELECT (SUM(IF(?d = l:Debit, ?v, 0)) AS ?debits) (SUM(IF(?d = l:Debit, 0, ?v)) AS ?offered) WHERE {{ {scan(index, day, known, first, 'amount')} "
                            f"{ck.KIND_FILTER.format(acct=ck.TREE[index].iri)} }}")
    return number(row[0]), number(row[1])


def in_effective_order(rows: list[tuple]) -> list[tuple]:
    """The rows of `read_b` in effective order, and within an effective position in the order recorded, which is the order the postings are numbered in."""
    return sorted(rows, key=lambda r: (int(r[1]), int(r[0].rsplit(":", 1)[1])))


def read_b(backend, index: int, day: int, known: int) -> int:
    """The postings of the account's subtree, fetched and settled again in effective order by the caller. An account above this one takes no part in what this one holds, so its subtree is enough."""
    common = f"?p l:{EFF} ?eff ; l:position ?pos ; l:account ?acct ; l:direction ?d ; l:amount ?v ."
    bound = f"FILTER(?eff <= {day} && ?pos <= {known})"
    rows = backend.select(f"{ck.PREFIX}SELECT ?p ?eff ?acct ?d ?v ?k WHERE {{ VALUES ?g {{ {ck.graphs_for(index, known, 0, True)} }} GRAPH ?g {{ "
                          f"{{ {common} ?p l:kind ?k . {bound} }} UNION {{ {common} {bound} FILTER NOT EXISTS {{ ?p l:kind ?z2 }} }} }} }}")
    step = [a.stated for a in ck.TREE]
    for _, _, acct, d, v, k in in_effective_order(rows):
        at = ck.BY_IRI[acct]
        ck.settle_debit(step, at, int(v)) if d.endswith("#Debit") else ck.settle_credit(step, at, int(v), k)
    return step[index]


def load(postings: list[ck.Posting], cps: dict, effective: list[int], known: int):
    """An in-memory store holding the postings recorded by `known`, their effective positions, and the checkpoints of the closes by then."""
    count = sum(p.pos <= known for p in postings)
    backend = w.LiveOxigraph(None)
    backend.upper = True
    backend.load(w.ledger_quads(postings[:count], {key: v for key, v in cps.items() if ck.EVERY_POSITIONS * (key[0] + 1) <= known}, known, effective[:count]))
    return backend


def run_readings(count: int, share: float, corpus: ck.Corpus | None = None) -> dict:
    corpus = corpus or ck.build_cut_corpus(count, w.SHARE)
    postings, model = corpus.postings, corpus.model
    effective, horizon = w.late_positions(postings, share), postings[-1].pos
    seconds = {r: [] for r in READS}
    by_age = {age: {"A from the start": [], "A from the close": []} for age in AGES}
    out = {"postings": count, "late_share": share, "late_postings": sum(x < p.pos for x, p in zip(effective, postings)), "readings": 0, "A impossible": 0, "B impossible": 0, "heads": 0, "B differs at the head": 0}
    moved = {f: [] for f in FIGURES}
    whole = load(postings, corpus.cps, effective, horizon)
    try:
        for known in corpus.points:
            if share and known < horizon and not any(effective[e] <= known < p.pos for e, p in enumerate(postings)):
                raise WrongResult(f"late {count} share {share}: no posting effective by {known} is recorded after it, so a read that forgets the recording could not be told")
            early = load(postings, corpus.cps, effective, known) if known < horizon else None
            try:
                for age, day in zip(AGES, days_for(known)):
                    picked, later = chosen(postings, effective, day, known), chosen(postings, effective, day, horizon)
                    a, b, (debits, offered) = model_a(postings, picked), model_b(postings, effective, picked), model_flows(postings, picked)
                    at_end = dict(zip(FIGURES, (model_a(postings, later), model_b(postings, effective, later), *model_flows(postings, later))))
                    close = ck.EVERY_POSITIONS * (day // ck.EVERY_POSITIONS)
                    before = model_flows(postings, [e for e, p in enumerate(postings) if p.pos <= close])
                    for i in ck.ANCESTORS:
                        where = f"late {count} share {share}: {ck.TREE[i].iri} for day {day} as known at {known}"
                        t = [time.perf_counter()]
                        recorded = ck.read_with_cuts(whole, i, known, True)[0]
                        t.append(time.perf_counter())
                        a_start = read_a(whole, i, day, known)
                        t.append(time.perf_counter())
                        a_close = read_a(whole, i, day, known, True)
                        t.append(time.perf_counter())
                        flows = read_flows(whole, i, day, known)
                        t.append(time.perf_counter())
                        since = read_flows(whole, i, day, known, True)
                        t.append(time.perf_counter())
                        b_read = read_b(whole, i, day, known)
                        t.append(time.perf_counter())
                        for name, x, y in zip(READS, t, t[1:]):
                            seconds[name].append(y - x)
                        by_age[age]["A from the start"].append(t[2] - t[1])
                        by_age[age]["A from the close"].append(t[3] - t[2])
                        if recorded != model.balance[("sum-with-cuts", i, known)]:
                            raise WrongResult(f"{where}: the recorded balance reads {recorded}, the model gives {model.balance[('sum-with-cuts', i, known)]}")
                        if not a_start == a_close == a[i]:
                            raise WrongResult(f"{where}: reading A is {a_start} from the start and {a_close} from the close, the model gives {a[i]}")
                        if flows != (debits[i], offered[i]):
                            raise WrongResult(f"{where}: the flows read {flows}, the model gives {(debits[i], offered[i])}")
                        if since != (debits[i] - before[0][i], offered[i] - before[1][i]):
                            raise WrongResult(f"{where}: the flows since the close read {since}, the model gives {(debits[i] - before[0][i], offered[i] - before[1][i])}")
                        if b_read != b[i]:
                            raise WrongResult(f"{where}: reading B is {b_read} through the engine, the model gives {b[i]}")
                        if early is not None and (read_a(early, i, day, known), read_flows(early, i, day, known), read_b(early, i, day, known)) != (a[i], (debits[i], offered[i]), b[i]):
                            raise WrongResult(f"{where}: a store holding only what was recorded by then reads differently from the whole store")
                        if share == 0 and a[i] != b[i]:
                            raise WrongResult(f"{where}: with no late posting reading A is {a[i]} and reading B is {b[i]}")
                        if day == known:
                            out["heads"] += 1
                            if a[i] != recorded:
                                raise WrongResult(f"{where}: reading A at the head is {a[i]}, the recorded balance is {recorded}")
                            out["B differs at the head"] += b[i] != recorded
                        out["readings"] += 1
                        out["A impossible"] += not 0 <= a[i] <= ck.TREE[i].ceiling
                        out["B impossible"] += not 0 <= b[i] <= ck.TREE[i].ceiling
                        for f, now in zip(FIGURES, (a[i], b[i], debits[i], offered[i])):
                            moved[f].append(abs(at_end[f][i] - now))
            finally:
                if early is not None:
                    early.close()
    finally:
        whole.close()
        whole = early = None
        ck.release_store()
    if share == 0 and any(any(m) for m in moved.values()):
        raise WrongResult(f"late {count}: with no late posting a figure was restated")
    out["restated"] = {f: {"moved": sum(x > 0 for x in m), "max": max(m), "mean": statistics.mean(m)} for f, m in moved.items()}
    out["mean_ms"] = {r: 1000 * statistics.mean(s) for r, s in seconds.items()}
    out["by_age_ms"] = {age: {r: 1000 * statistics.mean(s) for r, s in reads.items()} for age, reads in by_age.items() if reads["A from the start"]}
    return out


def render(data: dict) -> list[str]:
    out = ["# The readings of a balance by effective day (LG-18 part two)", "", "Environment: " + ", ".join(f"{k} {v}" for k, v in data["environment"].items() if v), "",
           "Every reading is for a day as known at a recording, at each of the 9 ancestors. A is the recorded amounts, B the postings settled again in effective order, C the flows. "
           "Impossible is a balance below zero or above the ceiling. The head is a day read at its own recording, where A is the recorded balance.", ""]
    out += w.table(["postings", "late share", "late postings", "readings", "A impossible", "B impossible", "heads", "B differs from the ledger at the head"],
                   [[r["postings"], f"{r['late_share']:.0%}", r["late_postings"], r["readings"], r["A impossible"], r["B impossible"], r["heads"], r["B differs at the head"]] for r in data["readings"]])
    out += ["", "Restatement, how far a figure as known at the recording has moved by the end of history: the readings that moved, then the largest and the mean movement.", ""]
    out += w.table(["postings", "late share"] + [f"{f} moved, max, mean" for f in FIGURES],
                   [[r["postings"], f"{r['late_share']:.0%}"] + [f"{r['restated'][f]['moved']}, {r['restated'][f]['max']}, {r['restated'][f]['mean']:.1f}" for f in FIGURES] for r in data["readings"]])
    out += ["", "Mean ms a read. Recorded is the ledger's balance at the recording, from its checkpoint. C since the close is the flows after the close before the day, which a checkpoint carrying the two totals would complete.", ""]
    out += w.table(["postings", "late share"] + list(READS), [[r["postings"], f"{r['late_share']:.0%}"] + [f"{r['mean_ms'][x]:.2f}" for x in READS] for r in data["readings"]])
    out += ["", "Reading A by the age of the day, mean ms from the start of history and from the close before the day.", ""]
    out += w.table(["postings", "late share", "day", "A from the start", "A from the close"],
                   [[r["postings"], f"{r['late_share']:.0%}", age, f"{v['A from the start']:.2f}", f"{v['A from the close']:.2f}"] for r in data["readings"] for age, v in r["by_age_ms"].items()])
    return out + [""]


def main() -> int:
    fast = w.quick()
    try:
        data: dict = {"environment": {**ck.environment(), "cpus": str(os.cpu_count()), "quick": "yes" if fast else ""}, "readings": []}
        for count in w.LATE_SIZES[:1] if fast else w.LATE_SIZES:
            corpus = ck.build_cut_corpus(count, w.SHARE)
            for share in w.LATE_SHARES:
                data["readings"].append(run_readings(count, share, corpus))
                print(f"readings {count} late {share:.0%} done", flush=True)
    except WrongResult as error:
        print(f"WRONG RESULT: {error}", file=sys.stderr)
        return 1
    directory = Path(os.environ.get("LEDGER_WRITES_REPORT_DIR") or HERE)
    (directory / "late-readings-report.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (directory / "late-readings-report.md").write_text("\n".join(render(data)), encoding="utf-8")
    print(f"report written to {directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
