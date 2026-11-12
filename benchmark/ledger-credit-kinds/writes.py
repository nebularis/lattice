# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""What a write costs the ledger's account tree, whether a guard closes the race between two writers, and what late postings do to a balance (ADR-A124, STD-278, STD-294).

`check.py` loads a history and reads it. The design it measures has the writer read the balances on the posting account's path and then write the posting, its applied amount and its cuts. Two writers that both
read and then both write can each act on a stale balance. This module measures the write and tests the guard that closes that race. It reuses the tree, the writer's arithmetic (`settle_debit`, `settle_credit`),
the vocabulary, the quads and the reads of `check.py`.

**Piece A, the live writer.** One posting against a store that holds history. The writer reads the ledger's revision and the balance of every account on the path (each a sum with cuts from the last checkpoint),
settles the posting in the application, and writes the posting, its applied amount, its kind, its cuts and the new revision in one SPARQL update request. The guard is one triple in the default graph,
`<urn:ledger:owner> l:revision N`, moved by `DELETE { revision N } INSERT { revision N+1 and the posting } WHERE { revision N }` (PAT-21, PAT-04). The committed revision N+1 is the posting's recorded position.
SPARQL update returns no count, so the writer asks afterwards whether its own posting exists. The posting's IRI is unique to the writer and the attempt, so a stale writer that wrote nothing finds nothing, reads again and retries.
The same writer with the guard left out replaces the guarded request with `DELETE DATA { revision N } ; INSERT DATA { revision N+1 and the posting }` and does not confirm, so the cost of the guard is visible.

**Piece B, concurrent writers.** Threads in one process against one `pyoxigraph.Store`. This is not a test over HTTP. The fixed interleavings step two writers by hand, with no threads, and are tests. The stress runs
2, 4 and 8 threads, each with its own seeded requests, and compares every committed record with a replay of the commits in revision order through `settle_debit` and `settle_credit`.

**Piece C, late postings.** A late posting has a recorded position and an earlier effective position (STD-294). It is stored in the period graph of its recorded position, with its effective position as one more triple,
which is a choice of this benchmark and not a decision (PDD-14 is open). At every ancestor and read point the module compares four numbers: the recorded sum (the sum with cuts over postings recorded by the point), the
effective sum (the same amounts and cuts over postings effective by the point, folded from the start, STD-278), and two fresh replays of only the postings effective by the point, one in recorded order and one in
effective order.

**Pass criterion.** A guarded run's records equal the replay of its commits, its revisions are dense, nothing is overdrawn, the engine's sums equal the model's, the recorded sum equals the stepwise replay, and the
effective sum equals the model's. A wrong result raises `WrongResult`. **Time never fails the run**, and neither does the number of retries. What the unguarded writer gets wrong, and where the four late numbers differ, are reported and not asserted.

Run `mise run check:ledger-credit-kinds-writes`. `LEDGER_WRITES_QUICK=1` runs the smallest sizes and `LEDGER_WRITES_REPORT_DIR` writes `writes-report.md` and `writes-report.json` elsewhere.

**The native caller (LG-17 part three).** `writes.py --emit-jvm <dir>` writes the preloads, the request lists and the plan of the runs for `benchmark/ledger-credit-kinds-jvm`, which runs the same writer on Jena called from Java and
exports each store as N-Quads. `writes.py --audit-jvm <dir>` loads each export into an in-memory Oxigraph and runs `audit` on it, so the replay is this module's and none is written in Java. A guarded run on a store is audited
strictly only if the Java probe of the store (a counter and a guarded update, as TSD-73) kept the guard, and an unguarded run never is. Run `mise run check:ledger-credit-kinds-jvm-writes`."""

from __future__ import annotations

import gzip
import json
import math
import os
import random
import statistics
import sys
import tempfile
import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from itertools import chain as chained
from pathlib import Path

import check as ck
from check import L, WrongResult

HERE = Path(__file__).resolve().parent
LEDGER = "urn:ledger:owner"
REVISION = L + "revision"
POSTING_BASE = "urn:posting:1"  # the name `ck.quads` gives the one posting it is handed, replaced by the live posting's own
STORED_EFFECTIVE = "effectivePosition"  # the predicate a late posting's effective position is stored under, one more triple on every posting
READ_EFFECTIVE = STORED_EFFECTIVE  # the predicate the effective fold reads. Only a test changes it
SHARE = 0.30  # credits, in every piece
WRITE_SIZES, WRITES = ck.SIZES, 500
STRESS_PRELOAD, STRESS_TOTAL, STRESS_THREADS = 5_000, 1_000, (2, 4, 8)
STRICT_STORE = "oxigraph memory"  # the store whose guarded runs must equal the replay. The on-disk store is audited and reported, since it does not isolate the guard (see the README)
ISOLATION_RUNS = 3
LATE_SIZES, LATE_SHARES = (5_000, 20_000), (0.0, 0.05, 0.20)  # 0.05 is `LATE_SHARE`, 0.20 the second share, and 0 the control in which the four numbers must agree
LATE_SHARE = 0.05
LATE_PERIODS = (1, 3)  # a late posting is effective one to three periods before it is recorded
MAX_ATTEMPTS = 20_000  # a writer that lost this many times in a row has starved, and the run fails
CLASSES = ("debit", "credit", "credit with a cut")
PARTS = ("reads", "settle", "update", "confirm")


@contextmanager
def seeded(seed: int):
    """Runs `ck.stream_two_level` with another seed and puts the module's back. Not for threads, so every request list is made before the threads start."""
    saved, ck.SEED = ck.SEED, seed
    try:
        yield
    finally:
        ck.SEED = saved


@dataclass(frozen=True)
class Request:
    at: int  # the account the posting is drawn on or credited to
    debit: bool
    amount: int
    kind: str | None


def requests(count: int, share: float, seed: int) -> list[Request]:
    """`count` postings drawn as the two-level stream draws them, with the writer's own settlement discarded, since the live writer settles each against the store."""
    with seeded(seed):
        return [Request(p.contract, p.debit, p.amount, p.kind) for p in ck.stream_two_level(count, share)]


class LiveOxigraph(ck.OxigraphBackend):
    def update(self, text: str) -> None:
        self.store.update(text)


class LiveJena(ck.JenaBackend):
    def update(self, text: str) -> None:
        self.store.update(text)


LIVE = {"oxigraph memory": lambda directory: LiveOxigraph(None), "oxigraph disk": LiveOxigraph, "jena": LiveJena}


def term(o) -> str:
    return f"<{o[1]}>" if o[0] == "i" else str(o[1]) if o[0] == "n" else json.dumps(o[1])


def ledger_quads(postings, cps, revision: int, effective: list[int] | None = None):
    """The benchmark's quads plus the revision triple of the owner's ledger and, if `effective` is given, one more triple on every posting, its effective position in the posting's graph."""
    for q in ck.quads(postings, cps):
        yield q
        if effective is not None and q[1] == L + "position" and q[0].startswith("urn:posting:"):
            yield q[0], L + STORED_EFFECTIVE, ("n", effective[int(q[0].rsplit(":", 1)[1]) - 1]), q[3]
    yield LEDGER, REVISION, ("n", revision), None


@dataclass
class Plan:
    """A request read and settled, not yet written."""
    request: Request
    tag: str
    revision: int
    refused: bool = False
    applied: int = 0
    cuts: tuple[tuple[int, int], ...] = ()
    seconds: dict = field(default_factory=dict)
    queries: int = 0
    path: int = 0


class Live:
    """The live writer. `checkpoints` is the number of checkpoints the store holds, whose balances are read once, since a checkpoint is immutable. The writer writes no checkpoint, so its reads fold every period after the last one."""

    def __init__(self, backend, checkpoints: int = 0, guarded: bool = True):
        self.b, self.guarded, self.k, self.cp, self.queries = backend, guarded, checkpoints - 1, {}, 0

    def select(self, text: str) -> list[tuple]:
        self.queries += 1
        return self.b.select(text)

    def revision(self) -> int:
        (row,) = self.select(f"SELECT (MAX(?r) AS ?m) WHERE {{ <{LEDGER}> <{REVISION}> ?r }}")
        return int(row[0])

    def start(self, i: int) -> tuple[int, int]:
        """(the first period graph to fold, the balance it starts from): the last checkpoint's, or the stated amount."""
        if self.k < 0:
            return 0, ck.TREE[i].stated
        if i not in self.cp:
            self.cp[i] = ck.checkpoint(self.b, i, self.k)["stepwise"]
            self.queries += 1
        return self.k + 1, self.cp[i]

    def balance(self, i: int, point: int) -> int:
        """The sum with cuts of account `i` as of the point, from the last checkpoint. An ancestor is read as `ck.read_with_cuts` reads it. A contract has no cut and no kind filter, and its own postings are in its sublimit's graphs."""
        first, base = self.start(i)
        a = ck.TREE[i]
        if a.level > 0:
            (row,) = self.select(f"{ck.PREFIX}SELECT (SUM(?signed) AS ?sum) WHERE {{ {ck.postings_scan(i, point, first)} {ck.KIND_FILTER.format(acct=a.iri)} {ck.SIGNED.replace('?a', '?v')} }}")
            (cut,) = self.select(f"{ck.PREFIX}SELECT (SUM(?cv) AS ?cut) WHERE {{ {ck.cuts_scan(i, point, first)} }}")
            return base + (int(row[0]) if row[0] is not None else 0) - (int(cut[0]) if cut[0] is not None else 0)
        if a.accepts:
            raise WrongResult(f"{a.iri} is a contract that restricts kinds, which the contract read does not handle")
        owner = ck.TREE[ck.graph_owner(i)].iri
        graphs = " ".join(f"<{ck.period_graph(owner, n)}>" for n in range(first, (point - 1) // ck.EVERY_POSITIONS + 1))
        head = f"?p l:account <{a.iri}> ; l:position ?pos ; l:direction"
        (row,) = self.select(f"{ck.PREFIX}SELECT (SUM(?signed) AS ?sum) WHERE {{ VALUES ?g {{ {graphs} }} GRAPH ?g {{ {{ {head} l:Debit ; l:amount ?v . BIND(l:Debit AS ?d) FILTER(?pos <= {point}) }} UNION "
                             f"{{ {head} l:Credit ; l:applied ?v . BIND(l:Credit AS ?d) FILTER(?pos <= {point}) }} {ck.SIGNED.replace('?a', '?v')} }} }}")
        return base + (int(row[0]) if row[0] is not None else 0)

    def prepare(self, request: Request, tag: str) -> Plan:
        """Reads the revision and the balance of every account on the path, then settles the request with the benchmark's own arithmetic. A debit larger than the balance of any account on its path is refused."""
        queries = self.queries
        begin = time.perf_counter()
        revision = self.revision()
        path = ck.chain(request.at)
        step = [0] * len(ck.TREE)
        for i in path:
            step[i] = self.balance(i, revision)
        read = time.perf_counter()
        plan = Plan(request, tag, revision, path=len(path))
        if request.debit:
            if any(step[i] < request.amount for i in path):
                plan.refused = True
            else:
                ck.settle_debit(step, request.at, request.amount)
        else:
            plan.applied, plan.cuts = ck.settle_credit(step, request.at, request.amount, request.kind)
        plan.seconds, plan.queries = {"reads": read - begin, "settle": time.perf_counter() - read}, self.queries - queries
        return plan

    def text(self, plan: Plan) -> tuple[str, str]:
        """(the update request, the posting's graph). The posting and its cuts are `ck.quads`' own, renamed to the attempt's."""
        r = plan.request
        posting = ck.Posting(plan.revision + 1, 0, r.at, r.debit, r.amount, r.kind, plan.applied, plan.cuts)
        rename = lambda s: s.replace(POSTING_BASE, f"urn:posting:{plan.tag}").replace("urn:cut:1:", f"urn:cut:{plan.tag}:")
        lines, graph = [], None
        for s, p, o, g in ck.quads([posting], {}):
            if g is not None:
                graph = g
                o = ("i", rename(o[1])) if o[0] == "i" else ("s", f"k{plan.tag}") if p == L + "key" else o
                lines.append(f"<{rename(s)}> <{p}> {term(o)} .")
        old, new = f"<{LEDGER}> <{REVISION}> {plan.revision}", f"<{LEDGER}> <{REVISION}> {plan.revision + 1}"
        body = f"{new} . GRAPH <{graph}> {{ {' '.join(lines)} }}"
        if self.guarded:
            return f"DELETE {{ {old} }} INSERT {{ {body} }} WHERE {{ {old} }}", graph
        return f"DELETE DATA {{ {old} }} ; INSERT DATA {{ {body} }}", graph

    def commit(self, plan: Plan) -> bool:
        """Writes the plan. A guarded write learns whether it won by asking for its own posting. An unguarded write does not ask, and reports success."""
        text, graph = self.text(plan)
        begin = time.perf_counter()
        self.b.update(text)
        done = time.perf_counter()
        won = True
        if self.guarded:
            won = bool(self.select(f"SELECT ?x WHERE {{ GRAPH <{graph}> {{ <urn:posting:{plan.tag}> a <{L}Posting> . BIND(1 AS ?x) }} }} LIMIT 1"))
        plan.seconds["update"], plan.seconds["confirm"] = done - begin, time.perf_counter() - done if self.guarded else 0.0
        return won


def write_one(live: Live, request: Request, tag: str, retry: bool = True) -> tuple[Plan, int]:
    """Prepares and commits one request, preparing again after a lost race. Returns the last plan and the attempts. A refused debit is not written."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        plan = live.prepare(request, f"{tag}.{attempt}")
        if plan.refused or live.commit(plan):
            return plan, attempt
        if not retry:
            raise WrongResult(f"{tag}: lost a race with no other writer")
    raise WrongResult(f"{tag}: lost {MAX_ATTEMPTS} races in a row")


@dataclass
class Stored:
    iri: str
    pos: int
    micro: int
    at: int
    debit: bool
    amount: int
    applied: int | None
    kind: str | None
    cuts: dict


def read_history(backend) -> list[Stored]:
    rows = backend.select(f"{ck.PREFIX}SELECT ?p ?pos ?mp ?acct ?d ?v ?ap ?k WHERE {{ GRAPH ?g {{ ?p a l:Posting ; l:position ?pos ; l:microPosition ?mp ; l:account ?acct ; l:direction ?d ; l:amount ?v . "
                          f"OPTIONAL {{ ?p l:applied ?ap }} OPTIONAL {{ ?p l:kind ?k }} }} }}")
    cuts: dict = defaultdict(dict)
    for p, at, cv in backend.select(f"{ck.PREFIX}SELECT ?p ?at ?cv WHERE {{ GRAPH ?g {{ ?c l:cutOf ?p ; l:cutAt ?at ; l:cutValue ?cv }} }}"):
        cuts[p][ck.BY_IRI[at]] = int(cv)
    out = [Stored(p, int(pos), int(mp), ck.BY_IRI[acct], d.endswith("#Debit"), int(v), None if ap is None else int(ap), k, cuts.get(p, {})) for p, pos, mp, acct, d, v, ap, k in rows]
    return sorted(out, key=lambda s: (s.pos, s.micro, s.iri))


def replay(items) -> list[int]:
    """The stepwise balance of every account after `items` (anything with `.at`, `.debit`, `.amount` and `.kind`) settled in the order given, by the benchmark's own writer."""
    step = [a.stated for a in ck.TREE]
    for s in items:
        ck.settle_debit(step, s.at, s.amount) if s.debit else ck.settle_credit(step, s.at, s.amount, s.kind)
    return step


def audit(backend, base: int, strict: bool = True, expect: int | None = None) -> dict:
    """Reads every record back and compares it with the replay, in recorded order, of the whole history through the benchmark's writer. Counts the postings whose stored applied amount or cuts differ, the accounts whose
    stored balance (the sum with cuts folded from the stored records) differs, the live debits that drew more than an account on their path held when the replay reached them (the history before `base` is not held to this, since the corpus does not refuse debits and overdraws the cap), and whether the live revisions (those after `base`) are dense, with no gap and no duplicate. The engine's sum
    with cuts at every ancestor must equal the stored balance, always. With `strict` any other difference raises `WrongResult`."""
    stored = read_history(backend)
    step, applied_differ, cuts_differ, overdrawn = [a.stated for a in ck.TREE], 0, 0, 0
    for s in stored:
        if s.debit:
            overdrawn += s.pos > base and any(step[i] < s.amount for i in ck.chain(s.at))
            ck.settle_debit(step, s.at, s.amount)
        else:
            applied, cuts = ck.settle_credit(step, s.at, s.amount, s.kind)
            applied_differ += applied != s.applied
            cuts_differ += dict(cuts) != s.cuts
    balance = [a.stated for a in ck.TREE]
    for s in stored:
        for i in ck.chain(s.at):
            if s.debit:
                balance[i] -= s.amount
            elif ck.accepts_kind(ck.TREE[i], s.kind):
                balance[i] += s.applied - s.cuts.get(i, 0)
    last = max((s.pos for s in stored), default=0)
    for i in ck.ANCESTORS:
        read = ck.read_with_cuts(backend, i, last)[0]
        if read != balance[i]:
            raise WrongResult(f"the engine reads {read} at {ck.TREE[i].iri}, the stored records give {balance[i]}")
    live = [s.pos for s in stored if s.pos > base]
    (revision,) = backend.select(f"SELECT (MAX(?r) AS ?m) WHERE {{ <{LEDGER}> <{REVISION}> ?r }}")
    result = {"postings": len(stored), "live": len(live), "applied_differ": applied_differ, "cuts_differ": cuts_differ, "balances_differ": sum(x != y for x, y in zip(balance, step)),
              "overdrawn": overdrawn, "dense": sorted(live) == list(range(base + 1, base + len(live) + 1)), "revision": int(revision[0]), "duplicate_positions": len(live) - len(set(live))}
    if strict:
        wrong = [k for k in ("applied_differ", "cuts_differ", "balances_differ", "overdrawn") if result[k]]
        if wrong or not result["dense"] or result["revision"] != base + len(live) or (expect is not None and len(live) != expect):
            raise WrongResult(f"the records differ from the replay of the commits: {result}, expected {expect} live postings")
    return result


def p95(xs: list[float]) -> float:
    xs = sorted(xs)
    return xs[max(0, math.ceil(0.95 * len(xs)) - 1)]


@contextmanager
def opened(name: str, directory: str | None = None):
    with tempfile.TemporaryDirectory(prefix="ledger-writes-", dir=directory) as tmp:
        backend = LIVE[name](tmp)
        backend.upper = True
        try:
            yield backend
        finally:
            backend.close()
            backend = None
            ck.release_store()


def preload(backend, count: int, share: float = SHARE) -> tuple[ck.Corpus, int]:
    """Loads the two-level corpus and the ledger's revision, which is the last pass. Returns the corpus and that revision."""
    corpus = ck.build_cut_corpus(count, share)
    revision = corpus.postings[-1].pos
    backend.load(ledger_quads(corpus.postings, corpus.cps, revision))
    if backend.count() != ck.expected_stored(corpus.postings) + 1:
        raise WrongResult(f"stored {backend.count()} triples, expected {ck.expected_stored(corpus.postings) + 1}")
    return corpus, revision


def posting_triples(plan: Plan) -> int:
    r = plan.request
    return ck.POSTING_TRIPLES + (0 if r.debit else 1 + (r.kind is not None) + ck.CUT_TRIPLES * len(plan.cuts))


def run_writes(name: str, count: int, guarded: bool, writes: int = WRITES) -> dict:
    """Piece A. `writes` further postings, one writer, on a store holding `count` postings. Splits each write into the path reads, the settle, the update and the confirmation, by the kind of posting."""
    with opened(name) as backend:
        corpus, base = preload(backend, count)
        live, before = Live(backend, len(corpus.positions), guarded), backend.count()
        seconds, meta, refused, added = {c: {p: [] for p in PARTS} for c in CLASSES}, {c: [] for c in CLASSES}, 0, 0
        for n, request in enumerate(requests(writes, SHARE, ck.SEED + 7)):
            plan, _ = write_one(live, request, f"W{n}", retry=False)
            if plan.refused:
                refused += 1
                continue
            cls = CLASSES[0] if request.debit else CLASSES[2] if plan.cuts else CLASSES[1]
            for p in PARTS:
                seconds[cls][p].append(plan.seconds.get(p, 0.0))
            meta[cls].append((plan.path, plan.queries, posting_triples(plan)))
            added += posting_triples(plan)
        if backend.count() - before != added:
            raise WrongResult(f"{name} {count}: the store grew by {backend.count() - before} triples, the writes add {added}")
        result = audit(backend, base, expect=writes - refused)
    classes = {}
    for c in CLASSES:
        if seconds[c]["reads"]:
            total = [sum(x) for x in zip(*seconds[c].values())]
            classes[c] = {"writes": len(total), "path_reads": statistics.mean(m[0] for m in meta[c]), "queries": statistics.mean(m[1] for m in meta[c]), "triples": statistics.mean(m[2] for m in meta[c]),
                          **{p: {"mean_ms": 1000 * statistics.mean(seconds[c][p]), "p95_ms": 1000 * p95(seconds[c][p])} for p in PARTS}, "total": {"mean_ms": 1000 * statistics.mean(total), "p95_ms": 1000 * p95(total)}}
    return {"backend": name, "postings": count, "guarded": guarded, "writes": writes, "refused": refused, "classes": classes, "audit": result}


# piece B

@contextmanager
def small_ledger(guarded: bool):
    """An empty ledger on the sketch's tree (a cap of 20 that accepts recoveries only, an aggregate of 10, and contracts S and T of 10), in memory, and two writers on it. Enters the tree in the calling thread."""
    with ck.using_tree(ck.sketch_tree(), ck.SKETCH_STATED):
        with opened("oxigraph memory") as backend:
            backend.load(ledger_quads([], {}, 0))
            yield backend, Live(backend, 0, guarded), Live(backend, 0, guarded)


CAP, AGG, S, T = range(4)
RECOVERY, REINSTATEMENT = L + "Recovery", L + "Reinstatement"


def interleave(case: str, guarded: bool) -> dict:
    """Two writers stepped by hand. Both read, then one writes, then the other writes, and a refused writer reads again and writes. Returns what the records are against the replay, and how often the second writer retried."""
    setups = {"recoveries": [Request(S, True, 6, None), Request(T, True, 4, None), Request(AGG, False, 3, REINSTATEMENT)],
              "debits": [Request(S, True, 6, None)],
              "disjoint": [Request(T, True, 2, None)]}
    pair = {"recoveries": (Request(S, False, 6, RECOVERY), Request(T, False, 4, RECOVERY)),
            "debits": (Request(S, True, 4, None), Request(T, True, 4, None)),
            "disjoint": (Request(S, True, 3, None), Request(T, False, 2, RECOVERY))}[case]
    with small_ledger(guarded) as (backend, one, two):
        for n, r in enumerate(setups[case]):
            if write_one(one, r, f"s{n}", retry=False)[0].refused:
                raise WrongResult(f"{case}: the setup was refused")
        first, second = one.prepare(pair[0], "a"), two.prepare(pair[1], "b")
        if one.revision() != two.revision() or first.revision != second.revision:
            raise WrongResult(f"{case}: the two writers did not read the same revision")
        if first.refused or second.refused:
            raise WrongResult(f"{case}: a writer was refused before the race")
        one.commit(first)
        retries, refused = 0, False
        if not two.commit(second):
            retries, (plan, _) = 1, write_one(two, pair[1], "b2")
            refused = plan.refused
        return {"case": case, "guarded": guarded, "retries": retries, "second_refused_on_retry": refused, **audit(backend, 0, strict=False)}


# stress

@dataclass
class Tally:
    commits: int = 0
    refused: int = 0
    lost: int = 0
    retries: list = field(default_factory=list)


def worker(backend, checkpoints: int, guarded: bool, asked: list[Request], w: int, tally: Tally, barrier: threading.Barrier, errors: list) -> None:
    try:
        live = Live(backend, checkpoints, guarded)
        barrier.wait()
        for n, request in enumerate(asked):
            plan, attempts = write_one(live, request, f"L{w}.{n}")
            tally.lost += attempts - 1
            tally.retries.append(attempts - 1)
            tally.refused += plan.refused
            tally.commits += not plan.refused
    except BaseException as error:  # a worker's failure must reach the run, not die in its thread
        errors.append(error)
        barrier.abort()


def run_stress(threads: int, guarded: bool, preload_count: int = STRESS_PRELOAD, total: int = STRESS_TOTAL, name: str = "oxigraph memory") -> dict:
    """Piece B. `threads` writers, each with its own seeded requests, so `total` further postings in all, on a store holding `preload_count` postings. A guarded run on `STRICT_STORE` must have records equal to the replay
    of its commits and dense revisions. Any other run is audited and the differences reported."""
    with opened(name) as backend:
        corpus, base = preload(backend, preload_count)
        lists = [requests(total // threads, SHARE, ck.SEED + 100 + w) for w in range(threads)]
        tallies, errors, barrier = [Tally() for _ in range(threads)], [], threading.Barrier(threads + 1)
        pool = [threading.Thread(target=worker, args=(backend, len(corpus.positions), guarded, lists[w], w, tallies[w], barrier, errors)) for w in range(threads)]
        for t in pool:
            t.start()
        try:
            barrier.wait()
        except threading.BrokenBarrierError:
            pass
        begin = time.perf_counter()
        for t in pool:
            t.join()
        wall = time.perf_counter() - begin
        if errors:
            raise errors[0]
        commits, refused = sum(t.commits for t in tallies), sum(t.refused for t in tallies)
        result = audit(backend, base, strict=guarded and name == STRICT_STORE, expect=commits)
    retries = [r for t in tallies for r in t.retries]
    return {"backend": name, "threads": threads, "guarded": guarded, "preload": preload_count, "requests": sum(len(x) for x in lists), "commits": commits, "refused": refused, "lost_races": sum(t.lost for t in tallies),
            "retries_mean": sum(t.lost for t in tallies) / max(commits + refused, 1), "retries_max": max(retries), "wall_s": wall, "commits_per_s": commits / wall, "audit": result}


def gil_probe(seconds: float = 1.0) -> dict:
    """Whether pyoxigraph releases the GIL in a query and in an update. A thread counts in pure Python while another runs queries (or updates) back to back. Its rate against its rate alone is near 1 if the GIL is
    released and near 0.5 if the other thread holds it, which a thread of pure Python gives as the control."""
    corpus = ck.build_cut_corpus(5_000, SHARE)
    backend = LiveOxigraph(None)
    backend.load(ck.quads(corpus.postings, corpus.cps))
    query = f"{ck.PREFIX}SELECT (SUM(?a) AS ?s) WHERE {{ GRAPH ?g {{ ?p l:amount ?a ; l:position ?x ; l:direction ?d . FILTER(?x > 0) }} }}"
    update = f"DELETE {{ <urn:t> <urn:p> ?o }} INSERT {{ <urn:t> <urn:p> 1 }} WHERE {{ OPTIONAL {{ <urn:t> <urn:p> ?o }} {{ SELECT (COUNT(*) AS ?n) WHERE {{ GRAPH ?g {{ ?p <{L}position> ?x }} }} }} }}"

    def spin(stop, out):
        n = 0
        while not stop.is_set():
            n += 1
        out.append(n)

    def rate(work=None):
        stop, spun, done, out = threading.Event(), threading.Event(), [], []
        busy = threading.Thread(target=lambda: [work() for _ in iter(stop.is_set, True)] if work else None)
        counter = threading.Thread(target=spin, args=(spun, out))
        busy.start(), counter.start()
        time.sleep(seconds)
        spun.set(), counter.join(), stop.set(), busy.join()
        return out[0] / seconds

    def pure():
        x = 0
        for i in range(100_000):
            x += i

    alone = rate()
    figures = {"query": rate(lambda: list(backend.store.query(query))) / alone, "update": rate(lambda: backend.store.update(update)) / alone, "pure python control": rate(pure) / alone}
    backend.close()
    return {"rate_against_alone": figures, "gil_enabled": sys._is_gil_enabled() if hasattr(sys, "_is_gil_enabled") else True, "cpus": os.cpu_count(),
            "reading": "a rate near 1 means the call released the GIL and a rate near 0.5 means it held it"}


# piece C

def late_positions(postings: list[ck.Posting], share: float, seed: int = ck.SEED + 5) -> list[int]:
    """The effective position of each posting. A fraction `share` are late, effective one to `LATE_PERIODS[1]` periods before they are recorded, and never before position 1. Both draws are made for every posting, so
    the late postings at a lower share are among those at a higher one. Asserts STD-294: no posting is effective after it is recorded."""
    rng, out = random.Random(seed), []
    for p in postings:
        late, periods = rng.random(), rng.randint(*LATE_PERIODS)
        periods = min(periods, (p.pos - 1) // ck.EVERY_POSITIONS)
        out.append(p.pos - periods * ck.EVERY_POSITIONS if late < share and periods else p.pos)
    if any(not 1 <= x <= p.pos for x, p in zip(out, postings)):
        raise WrongResult("a posting is effective after it is recorded")
    return out


@dataclass(frozen=True)
class Item:
    """A posting as the replays see it."""
    at: int
    debit: bool
    amount: int
    kind: str | None


def effective_sum(postings: list[ck.Posting], effective: list[int], point: int) -> list[int]:
    """The model's effective sum at every account: the stated amount, less debits, plus applied credits, less cuts, over the postings effective by the point, with amounts and cuts as recorded."""
    out = [a.stated for a in ck.TREE]
    for p, x in zip(postings, effective):
        if x <= point:
            cuts = dict(p.cuts)
            for i in ck.chain(p.contract):
                if p.debit:
                    out[i] -= p.amount
                elif ck.accepts_kind(ck.TREE[i], p.kind):
                    out[i] += p.applied - cuts.get(i, 0)
    return out


def read_effective(backend, index: int, point: int, horizon: int) -> int:
    """The effective sum of an ancestor read through the engine, folded from the start of history with no checkpoint (STD-278), over every period graph to the end of history, since a posting recorded long after the point
    can be effective by it."""
    a, first = ck.TREE[index], 0
    graphs = ck.graphs_for(index, horizon, first, True)
    head = f"?p l:{READ_EFFECTIVE} ?pos ; l:direction"
    bound = f"FILTER(?pos <= {point})"
    postings = (f"{{ VALUES ?g {{ {graphs} }} GRAPH ?g {{ {{ {head} l:Debit ; l:amount ?v . BIND(l:Debit AS ?d) {bound} }} UNION {{ {head} l:Credit ; l:applied ?v ; l:kind ?k . BIND(l:Credit AS ?d) {bound} }} UNION "
                f"{{ {head} l:Credit ; l:applied ?v . BIND(l:Credit AS ?d) {bound} FILTER NOT EXISTS {{ ?p l:kind ?z2 }} }} }} }}")
    cuts = f"{{ VALUES ?g {{ {graphs} }} GRAPH ?g {{ ?c l:cutAt <{a.iri}> ; l:cutValue ?cv ; l:cutOf ?p . ?p l:{READ_EFFECTIVE} ?pos . {bound} }} }}"
    (row,) = backend.select(f"{ck.PREFIX}SELECT (SUM(?signed) AS ?sum) WHERE {{ {postings} {ck.KIND_FILTER.format(acct=a.iri)} {ck.SIGNED.replace('?a', '?v')} }}")
    (cut,) = backend.select(f"{ck.PREFIX}SELECT (SUM(?cv) AS ?cut) WHERE {{ {cuts} }}")
    return a.stated + (int(row[0]) if row[0] is not None else 0) - (int(cut[0]) if cut[0] is not None else 0)


def run_late(count: int, share: float, corpus: ck.Corpus | None = None) -> dict:
    """Piece C. The two-level corpus with a seeded `share` of late postings, in memory on Oxigraph. At every ancestor and read point, the recorded sum, the effective sum, replay R and replay E."""
    corpus = corpus or ck.build_cut_corpus(count, SHARE)
    postings, model = corpus.postings, corpus.model
    effective, horizon = late_positions(postings, share), postings[-1].pos
    items = [Item(p.contract, p.debit, p.amount, p.kind) for p in postings]
    order = sorted(range(len(postings)), key=lambda e: (effective[e], e))
    rows = {"R": [], "E": []}
    seconds = {"recorded": 0.0, "effective": 0.0}
    out = {"late_postings": sum(x < p.pos for x, p in zip(effective, postings)), "reads": 0, "impossible": 0}
    diffs = {"eff vs R": [], "eff vs E": [], "R vs E": []}
    backend = LiveOxigraph(None)
    try:
        backend.load(ledger_quads(postings, corpus.cps, horizon, effective))
        if backend.count() != ck.expected_stored(postings) + len(postings) + 1:
            raise WrongResult(f"late {count}: stored {backend.count()} triples, expected {ck.expected_stored(postings) + len(postings) + 1}")
        for point in corpus.points:
            by_recorded = replay(it for it, p in zip(items, postings) if p.pos <= point)
            by_r = replay(it for it, x in zip(items, effective) if x <= point)
            by_e = replay(items[e] for e in order if effective[e] <= point)
            mine = effective_sum(postings, effective, point)
            for i in ck.ANCESTORS:
                begin = time.perf_counter()
                recorded = ck.read_with_cuts(backend, i, point, False)[0]
                middle = time.perf_counter()
                eff = read_effective(backend, i, point, horizon)
                seconds["recorded"] += middle - begin
                seconds["effective"] += time.perf_counter() - middle
                where = f"late {count} share {share}: {ck.TREE[i].iri} as of {point}"
                if not recorded == model.balance[("sum-with-cuts", i, point)] == by_recorded[i]:
                    raise WrongResult(f"{where}: the recorded sum reads {recorded}, the model gives {model.balance[('sum-with-cuts', i, point)]} and the replay {by_recorded[i]}")
                if eff != mine[i]:
                    raise WrongResult(f"{where}: the effective sum reads {eff} through the engine, the model gives {mine[i]}")
                if share == 0 and not eff == by_r[i] == by_e[i] == recorded:
                    raise WrongResult(f"{where}: with no late posting the four numbers differ: {recorded}, {eff}, {by_r[i]}, {by_e[i]}")
                out["reads"] += 1
                out["impossible"] += not 0 <= eff <= ck.TREE[i].ceiling
                for key, x, y in (("eff vs R", eff, by_r[i]), ("eff vs E", eff, by_e[i]), ("R vs E", by_r[i], by_e[i])):
                    diffs[key].append(abs(x - y))
    finally:
        backend.close()
        backend = None
        ck.release_store()
    for key, d in diffs.items():
        out[key] = {"differs": sum(x > 0 for x in d), "max": max(d), "mean": statistics.mean(d)}
    return {"postings": count, "late_share": share, **out, "recorded_s": seconds["recorded"], "effective_s": seconds["effective"]}


# the native Jena caller (LG-17 part three)

JVM_DIR = HERE.parent / "ledger-credit-kinds-jvm"
JVM_STORES = ("memory", "tdb2")


def nt(o) -> str:
    return f"<{o[1]}>" if o[0] == "i" else f'"{o[1]}"^^<{ck.XSD_INT}>' if o[0] == "n" else f'"{o[1]}"'


def prefix(index: int) -> str:
    return f"urn:graph:{ck.TREE[index].iri.rsplit(':', 1)[1]}:"


def asked(items: list[Request]) -> list:
    return [[r.at, int(r.debit), r.amount, r.kind] for r in items]


def emit_jvm(directory: Path, sizes=WRITE_SIZES, preload_count: int = STRESS_PRELOAD, threads=STRESS_THREADS, stores: dict | None = None) -> None:
    """Writes what the native caller needs: the account tree, a preload of the two-level corpus with the ledger's revision for each size (as `preload` loads it) as N-Quads, the request lists of the single writer and of
    the stress (the same seeds as `run_writes` and `run_stress`, long enough for the largest store) and the plan of the runs. `stores` gives, for each store, the probe (the counter it counts up to, the increments a thread
    makes and the runs a cell), the writes of the single writer, and the stress (the requests in all and the guarded runs a cell by number of threads). Each store has its own sizes, since a commit on TDB2 costs tens of ms."""
    stores = stores or JVM_PLAN
    directory.mkdir(parents=True, exist_ok=True)
    tree = [{"iri": a.iri, "level": a.level, "stated": a.stated, "ceiling": a.ceiling, "parent": -1 if a.parent is None else a.parent, "accepts": list(a.accepts),
             "graphPrefixes": [prefix(u) for u in ck.sublimits_under(i)], "upperPrefixes": [prefix(u) for u in ck.sections_under(i)], "ownPrefix": prefix(ck.graph_owner(i))} for i, a in enumerate(ck.TREE)]
    preloads = {}
    for count in sorted(set(sizes) | {preload_count}):
        corpus = ck.build_cut_corpus(count, SHARE)
        base = corpus.postings[-1].pos
        name = f"preload-{count}.nq"
        with open(directory / name, "w", encoding="utf-8", newline="\n") as out:
            for s, p, o, g in ledger_quads(corpus.postings, corpus.cps, base):
                out.write(f"<{s}> <{p}> {nt(o)}{' <' + g + '>' if g else ''} .\n")
        preloads[str(count)] = {"file": name, "postings": count, "base": base, "checkpoints": len(corpus.positions), "stored": ck.expected_stored(corpus.postings) + 1}
    writes, total = max(v["single"]["writes"] for v in stores.values()), max(v["stress"]["total"] for v in stores.values())
    lists = {str(t): [asked(requests(total // t, SHARE, ck.SEED + 100 + w)) for w in range(t)] for t in (1,) + tuple(threads)}
    plan = {"stores": stores, "threads": [1] + list(threads), "sizes": list(sizes), "stressPreload": preload_count}
    data = {"every": ck.EVERY_POSITIONS, "ns": L, "tree": tree, "preloads": preloads, "plan": plan, "single": asked(requests(writes, SHARE, ck.SEED + 7)), "stress": lists}
    (directory / "writes-input.json").write_text(json.dumps(data), encoding="utf-8", newline="\n")


def store_plan(probe: tuple[int, int, int], writes: int, total: int, runs: int) -> dict:
    return {"probe": {"target": probe[0], "increments": probe[1], "runs": probe[2]}, "single": {"writes": writes}, "stress": {"total": total, "guardedRuns": {"1": 1, **{str(t): runs for t in STRESS_THREADS}}}}


# Jena in memory takes the sizes of the Python benchmark. TDB2 fsyncs every commit, at tens of ms, and a lost race commits too, so it takes smaller counts and the same runs a cell.
JVM_PLAN = {"memory": store_plan((1000, 500, ISOLATION_RUNS), WRITES, STRESS_TOTAL, ISOLATION_RUNS), "tdb2": store_plan((100, 50, ISOLATION_RUNS), 100, 200, ISOLATION_RUNS)}
JVM_PLAN_QUICK = {"memory": store_plan((200, 100, 1), 100, 200, 1), "tdb2": store_plan((200, 100, 1), 100, 200, 1)}


def audit_export(path: Path, base: int, strict: bool, expect: int | None = None) -> dict:
    """Loads an export (N-Quads, gzipped if the name says so) into an in-memory Oxigraph and audits it as `audit` does any store."""
    backend = LiveOxigraph(None)
    backend.upper = True
    try:
        with (gzip.open(path, "rb") if str(path).endswith(".gz") else open(path, "rb")) as handle:
            backend.store.bulk_load(handle, format=ck.ox.RdfFormat.N_QUADS)
        return audit(backend, base, strict, expect)
    finally:
        backend.close()
        backend = None
        ck.release_store()


def probe_keeps_guard(report: dict, store: str) -> bool:
    """Whether the probe's guarded runs on the store, at two threads or more, each ended with every revision carrying exactly one marker and the target number of markers."""
    cells = [g for g in report["probe"]["guarded"] if g["store"] == store and g["threads"] > 1]
    return bool(cells) and all(g["markers"] == g["target"] and g["multi_marker_revisions"] == 0 for g in cells)


def audit_jvm(directory: Path) -> int:
    """Audits every export of a native run and writes `writes-report.md` and `writes-report.json`. A guarded run is strict on a store whose probe kept the guard, and a single writer's guarded run is strict always."""
    report = json.loads((directory / "writes-java.json").read_text(encoding="utf-8"))
    held = {store: probe_keeps_guard(report, store) for store in JVM_STORES}
    report["guard_kept"] = held
    try:
        for r in report["single"]:
            r["audit"] = audit_export(directory / r["export"], r["base"], r["guarded"], r["commits"])
            print(f"audited {r['export']}", flush=True)
        for r in report["stress"]:
            r["audit"] = audit_export(directory / r["export"], r["base"], r["guarded"] and held[r["store"]], r["commits"])
            r["asserted"] = r["guarded"] and held[r["store"]]
            print(f"audited {r['export']}", flush=True)
    except WrongResult as error:
        print(f"WRONG RESULT: {error}", file=sys.stderr)
        return 1
    out = Path(os.environ.get("LEDGER_WRITES_REPORT_DIR") or JVM_DIR)
    (out / "writes-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out / "writes-report.md").write_text("\n".join(render_jvm(report)), encoding="utf-8")
    print(f"report written to {out}")
    return 0


STORE_NAME = {"memory": "jena-memory (java)", "tdb2": "jena-tdb2 (java)"}


def render_jvm(data: dict) -> list[str]:
    env = data["environment"]
    out = ["# The write benchmark on native Jena (LG-17 part three)", "", "Environment: " + ", ".join(f"{k} {v}" for k, v in env.items() if v), ""]
    out += ["## C1, the probe of TSD-73 on Jena", "", "A counter triple. Each thread reads the counter N, sends the guarded update with its own marker and asks whether its marker exists, until the counter reaches the target. Markers confirmed, where the target is correct. "
            "Revisions with more than one marker is the loss the guard is there to stop. Lost races is the confirmations that found no marker.", ""]
    out += table(["store", "threads", "run", "target", "markers", "revisions with more than one marker", "lost races", "counter triples", "wall s"],
                 [[STORE_NAME[g["store"]], g["threads"], g["run"], g["target"], g["markers"], g["multi_marker_revisions"], g["lost_races"], g["counter_triples"], f"{g['wall_s']:.2f}"] for g in data["probe"]["guarded"]])
    out += ["", "The increment in the store, a thread's updates being `DELETE { ?n } INSERT { ?m } WHERE { ... BIND(?n + 1 AS ?m) }`.", ""]
    out += table(["store", "threads", "run", "expected", "final", "counter triples", "wall s"],
                 [[STORE_NAME[i["store"]], i["threads"], i["run"], i["expected"], i["final"], i["counter_triples"], f"{i['wall_s']:.2f}"] for i in data["probe"]["increment"]])
    out += [""] + [f"- {STORE_NAME[s]}: the guard was {'kept' if kept else 'not kept'} in every guarded probe run at two threads or more. Its guarded stress runs are {'asserted against the replay' if kept else 'audited and reported, not asserted'}."
                   for s, kept in data["guard_kept"].items()]
    out += ["", "## C2, what a write costs", "", "Mean and p95 ms per write by kind of posting, one writer. Writes is the further postings of the kind. Accounts is the accounts read on the path, queries the SPARQL requests a write makes, triples the triples the write adds. "
            "The path reads are made in one read transaction. The unguarded writer replaces the guarded request with `DELETE DATA ; INSERT DATA` and does not confirm.", ""]
    rows = []
    for r in data["single"]:
        for c, v in r["classes"].items():
            rows.append([STORE_NAME[r["store"]], r["postings"], "guarded" if r["guarded"] else "unguarded", c, v["writes"], f"{v['path_reads']:.1f}", f"{v['queries']:.1f}", f"{v['triples']:.1f}"]
                        + [f"{v[p]['mean_ms']:.2f} / {v[p]['p95_ms']:.2f}" for p in PARTS] + [f"{v['total']['mean_ms']:.2f} / {v['total']['p95_ms']:.2f}"])
    out += table(["store", "postings", "writer", "kind", "writes", "accounts", "queries", "triples", "reads ms", "settle ms", "update ms", "confirm ms", "total ms"], rows)
    out += ["", "Debits refused for lack of availability, and the audit of the store against the replay of its writes.", ""]
    out += table(["store", "postings", "writer", "writes", "refused", "applied differ", "cuts differ", "balances differ", "overdrawing debits", "dense"],
                 [[STORE_NAME[r["store"]], r["postings"], "guarded" if r["guarded"] else "unguarded", r["writes"], r["refused"], r["audit"]["applied_differ"], r["audit"]["cuts_differ"], r["audit"]["balances_differ"],
                   r["audit"]["overdrawn"], r["audit"]["dense"]] for r in data["single"]])
    out += ["", "## C2, concurrent writers", "", "Threads in one JVM against one dataset, each with its own seeded requests, on a store holding the preload. Retries is the lost races a request had before it committed or was refused. "
            "Asserted is whether the audit was held to the replay. The last columns are the audit against the replay of the commits in revision order.", ""]
    out += table(["store", "threads", "writer", "run", "asserted", "commits", "refused", "lost races", "retries mean", "retries max", "wall s", "commits/s", "applied differ", "cuts differ", "balances differ", "overdrawing debits",
                  "dense", "duplicate positions"],
                 [[STORE_NAME[s["store"]], s["threads"], "guarded" if s["guarded"] else "unguarded", s["run"], "yes" if s["asserted"] else "no", s["commits"], s["refused"], s["lost_races"], f"{s['retries_mean']:.2f}",
                   s["retries_max"], f"{s['wall_s']:.2f}", f"{s['commits_per_s']:.0f}", s["audit"]["applied_differ"], s["audit"]["cuts_differ"], s["audit"]["balances_differ"], s["audit"]["overdrawn"], s["audit"]["dense"],
                   s["audit"]["duplicate_positions"]] for s in data["stress"]])
    return out + [""]


# the run

def quick() -> bool:
    return bool(os.environ.get("LEDGER_WRITES_QUICK"))


def table(head: list[str], rows: list[list]) -> list[str]:
    return ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]


def render(data: dict) -> list[str]:
    out = ["# The write benchmark (LG-17 part two)", "", "Environment: " + ", ".join(f"{k} {v}" for k, v in data["environment"].items() if v), ""]
    out += ["## Piece A, what a write costs", "", "Mean and p95 ms per write by kind of posting. Accounts is the accounts read on the path, queries the SPARQL requests a write makes (the revision read, one or two per account, and the confirmation of a guarded write), triples the triples the write adds. "
            "The unguarded writer replaces the guarded request with `DELETE DATA ; INSERT DATA` and does not confirm.", ""]
    rows = []
    for r in data["writes"]:
        for c, v in r["classes"].items():
            rows.append([r["backend"], r["postings"], "guarded" if r["guarded"] else "unguarded", c, v["writes"], f"{v['path_reads']:.1f}", f"{v['queries']:.1f}", f"{v['triples']:.1f}"]
                        + [f"{v[p]['mean_ms']:.2f} / {v[p]['p95_ms']:.2f}" for p in PARTS] + [f"{v['total']['mean_ms']:.2f} / {v['total']['p95_ms']:.2f}"])
    out += table(["backend", "postings", "writer", "kind", "writes", "accounts", "queries", "triples", "reads ms", "settle ms", "update ms", "confirm ms", "total ms"], rows)
    out += ["", "Debits refused for lack of availability, of the writes made.", ""] + table(["backend", "postings", "writer", "refused", "writes"], [[r["backend"], r["postings"], "guarded" if r["guarded"] else "unguarded", r["refused"], r["writes"]] for r in data["writes"]])
    out += ["", "## Piece B, concurrent writers", "", f"Threads in one process against one store. The GIL probe, the rate of a counting thread beside the call against its rate alone: {json.dumps({k: round(v, 3) for k, v in data['gil']['rate_against_alone'].items()})}, "
            f"on {data['gil']['cpus']} CPUs with the GIL {'enabled' if data['gil']['gil_enabled'] else 'disabled'}. {data['gil']['reading']}.", "", "The fixed interleavings. Retries is the second writer's.", ""]
    out += table(["case", "writer", "retries", "second refused on retry", "applied differ", "cuts differ", "balances differ", "overdrawing debits", "dense", "duplicate positions"],
                 [[i["case"], "guarded" if i["guarded"] else "unguarded", i["retries"], i["second_refused_on_retry"], i["applied_differ"], i["cuts_differ"], i["balances_differ"], i["overdrawn"], i["dense"], i["duplicate_positions"]] for i in data["interleavings"]])
    out += ["", f"The stress, {STRESS_TOTAL if not quick() else data['stress'][0]['requests']} further postings on a store holding {data['stress'][0]['preload']}. Retries is the lost races a request had before it committed or was refused. The last four columns are the audit against the replay of the commits in revision order.", ""]
    out += table(["backend", "threads", "writer", "commits", "refused", "lost races", "retries mean", "retries max", "wall s", "commits/s", "applied differ", "cuts differ", "balances differ", "overdrawing debits", "dense", "duplicate positions"],
                 [[s["backend"], s["threads"], "guarded" if s["guarded"] else "unguarded", s["commits"], s["refused"], s["lost_races"], f"{s['retries_mean']:.2f}", s["retries_max"], f"{s['wall_s']:.2f}", f"{s['commits_per_s']:.0f}",
                   s["audit"]["applied_differ"], s["audit"]["cuts_differ"], s["audit"]["balances_differ"], s["audit"]["overdrawn"], s["audit"]["dense"], s["audit"]["duplicate_positions"]] for s in data["stress"]])
    out += ["", f"The guard on each store, {ISOLATION_RUNS} guarded runs a cell. A duplicate position is two commits at one revision, which the guard is there to stop. Only the in-memory store is asserted.", ""]
    out += table(["store", "threads", "run", "commits", "lost races", "dense", "duplicate positions", "applied differ", "cuts differ", "balances differ", "overdrawing debits"],
                 [[s["backend"], s["threads"], s["run"], s["commits"], s["lost_races"], s["audit"]["dense"], s["audit"]["duplicate_positions"], s["audit"]["applied_differ"], s["audit"]["cuts_differ"], s["audit"]["balances_differ"], s["audit"]["overdrawn"]]
                  for s in data["isolation"]])
    out += ["", "## Piece C, late postings", "", "Counts are of the ancestor reads (9 ancestors at 3 points). Differences are absolute, in the unit of the balance, over all reads. The effective sum is read from the start of history, over every period graph.", ""]
    out += table(["postings", "late share", "late postings", "reads", "eff vs R", "eff vs E", "R vs E", "max diff eff/R, eff/E, R/E", "mean diff eff/R, eff/E, R/E", "eff impossible", "recorded sum s", "effective sum s", "effective / recorded"],
                 [[r["postings"], f"{r['late_share']:.0%}", r["late_postings"], r["reads"], r["eff vs R"]["differs"], r["eff vs E"]["differs"], r["R vs E"]["differs"],
                   " / ".join(str(r[k]["max"]) for k in ("eff vs R", "eff vs E", "R vs E")), " / ".join(f"{r[k]['mean']:.1f}" for k in ("eff vs R", "eff vs E", "R vs E")), r["impossible"],
                   f"{r['recorded_s']:.2f}", f"{r['effective_s']:.2f}", f"{r['effective_s'] / r['recorded_s']:.2f}"] for r in data["late"]])
    return out + [""]


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "--emit-jvm":
        if quick():
            emit_jvm(Path(sys.argv[2]), WRITE_SIZES[:1], 1_000, stores=JVM_PLAN_QUICK)
        else:
            emit_jvm(Path(sys.argv[2]))
        print(f"preloads, requests and the plan written to {sys.argv[2]}")
        return 0
    if len(sys.argv) == 3 and sys.argv[1] == "--audit-jvm":
        return audit_jvm(Path(sys.argv[2]))
    fast = quick()
    sizes = WRITE_SIZES[:1] if fast else WRITE_SIZES
    try:
        data: dict = {"environment": {**ck.environment(), "cpus": str(os.cpu_count()), "late_share": str(LATE_SHARE), "quick": "yes" if fast else ""}, "writes": [], "interleavings": [], "stress": [], "late": []}
        names = ["oxigraph memory", "oxigraph disk"] + (["jena"] if ck.jena_available() else [])
        for name in names:
            for count in sizes:
                for guarded in (True, False):
                    data["writes"].append(run_writes(name, count, guarded, 100 if fast else WRITES))
                    print(f"piece A {name} {count} {'guarded' if guarded else 'unguarded'} done", flush=True)
        data["gil"] = gil_probe()
        for case in ("recoveries", "debits", "disjoint"):
            data["interleavings"] += [interleave(case, True), interleave(case, False)]
        preload_count, total = (1_000, 200) if fast else (STRESS_PRELOAD, STRESS_TOTAL)
        for threads in (1,) + STRESS_THREADS:
            for guarded in (True, False):
                data["stress"].append(run_stress(threads, guarded, preload_count, total))
                print(f"piece B {threads} threads {'guarded' if guarded else 'unguarded'} done", flush=True)
        data["isolation"] = []
        for name in (STRICT_STORE, "oxigraph disk"):
            for threads in STRESS_THREADS:
                for run in range(1, ISOLATION_RUNS + 1):
                    data["isolation"].append({"run": run, **run_stress(threads, True, preload_count, total, name)})
                print(f"isolation {name} {threads} threads done", flush=True)
        for count in LATE_SIZES[:1] if fast else LATE_SIZES:
            corpus = ck.build_cut_corpus(count, SHARE)
            for share in LATE_SHARES:
                data["late"].append(run_late(count, share, corpus))
                print(f"piece C {count} late {share:.0%} done", flush=True)
    except WrongResult as error:
        print(f"WRONG RESULT: {error}", file=sys.stderr)
        return 1
    directory = Path(os.environ.get("LEDGER_WRITES_REPORT_DIR") or HERE)
    (directory / "writes-report.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (directory / "writes-report.md").write_text("\n".join(render(data)), encoding="utf-8")
    print(f"report written to {directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
