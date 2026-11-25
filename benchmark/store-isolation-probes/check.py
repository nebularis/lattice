#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""What PostgreSQL and Fuseki over TDB2 do with the store behaviours the multi-store protocol models assume (ADR-A124, MSA-I6).

Each probe states one assumption of a model in `tools/models/multi-store-protocols` and runs the smallest workload that shows
whether a store keeps it, with two or more clients interleaved on purpose. **The PostgreSQL arm** runs here, on the server of the
PostgreSQL test fixture (`tools/testing/postgres`), under each isolation level the probe names. One thread drives every connection
step by step, and a statement that has to wait on a lock runs on a thread of its own until the server shows it waiting. **The Jena
arm** is the Maven project beside this file. It runs Fuseki over a TDB2 dataset on disk in its own JVM, driven by concurrent HTTP
clients that meet at a barrier, and TDB2 called in process for the two probes that hold a transaction open. It runs once for each
Jena version in `JENA_VERSIONS`, 5.1.0 (the platform's) and 6.2.0 (the Fuseki the studio's stack runs), and writes what it
observed to `target/jena-<version>/results.json`, which this script judges.

**Pass criterion.** `EXPECTED` says, for every probe, store, form and mode, whether the anomaly the probe looks for appears in no
repetition (`never`) or in every one (`always`). A row passes where the store did that. A control is a form expected to show the
anomaly every time, which shows that the interleaving happened. A row with no expectation, an expected row that no run produced,
a row with no repetitions, and a row whose counted reads beside the writes or races lost are 0, so that no other client acted
beside it, fail. **Time never fails it.** The report is `report.md` and `report.json` here, generated and git-ignored.

`STORE_ISOLATION_QUICK=1` runs fewer repetitions. `STORE_ISOLATION_PG_REPS` and `STORE_ISOLATION_JENA_REPS` set them,
`STORE_ISOLATION_JENA_VERSIONS` (a comma list) the Jena versions, and `STORE_ISOLATION_ARMS` (`postgresql`, `jena` or both) the
arms. An arm whose server or tool is absent is skipped with the reason."""

from __future__ import annotations

import importlib
import json
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
QUICK = os.environ.get("STORE_ISOLATION_QUICK") == "1"
PG_REPS = int(os.environ.get("STORE_ISOLATION_PG_REPS", "10" if QUICK else "50"))
JENA_REPS = int(os.environ.get("STORE_ISOLATION_JENA_REPS", "5" if QUICK else "20"))
PG_STRESS = 50 if QUICK else 200
JENA_STRESS = 10 if QUICK else 40
STRESS_THREADS = 4
JENA_VERSIONS = tuple(v.strip() for v in os.environ.get("STORE_ISOLATION_JENA_VERSIONS", "5.1.0,6.2.0").split(",") if v.strip())
ARMS = tuple(a.strip() for a in os.environ.get("STORE_ISOLATION_ARMS", "postgresql,jena").split(",") if a.strip())
WAIT_TIMEOUT = 20.0

RU, RC, RR, SER = "read uncommitted", "read committed", "repeatable read", "serializable"
LEVEL_SQL = {RU: "READ UNCOMMITTED", RC: "READ COMMITTED", RR: "REPEATABLE READ", SER: "SERIALIZABLE"}
NEVER, ALWAYS = "never", "always"
PG, FUSEKI, TDB2 = "postgresql", "fuseki", "tdb2"

# Each probe: the assumption it checks, and the models and configurations whose conclusions rest on it.
ASSUMPTIONS = {
    "ISO-01": ("A guarded compare-and-set request is one atomic step: of two writers that read the same version, one applies and the other changes nothing",
               "Model A (`ModelA_Atomic`), the guard in each store of X1 (`X1_Applied*`), X5's per-step guards, Protocol A's pass (`PA_OnRead*`), each pass of X6 (`X6_Closed`)"),
    "ISO-02": ("The same, for four writers that loop until the version reaches a target",
               "Model A with three writers (`ModelA_Atomic`), X1 with a zombie (`X1_AppliedZombie*`)"),
    "ISO-03": ("A store answers a command that has a receipt and applies any other in one step, so two deliveries of one command apply it once",
               "X1 with receipts only (`X1R_Applied`, `X1R_AppliedZombie2`), X1's `Duplicate` answer, X5's receipts"),
    "ISO-04": ("A request is applied all or nothing, and a reader never sees a request that is later rolled back",
               "Model A's atomic step, X5's one request (`X5_Whole*`, `X5_Fenced*`), Protocol A's pass written in one request (`PA_*`)"),
    "ISO-05": ("Two requests that write the same two rows are each applied whole, never interleaved step by step",
               "X5 (`X5_Whole*`, `X5_Fenced*`, `X5_BuiltStream*`), Protocol A (`PA_OnRead*`)"),
    "ISO-06": ("A reader of one store sees a request's effects together or not at all. Two separate reads may see two states",
               "X1's reader (`X1_Torn*`), which is torn only across stores, X5's read of a plan in one step, X2's read set (`ReadSetTrue`)"),
    "ISO-07": ("A write whose reply has come is seen by the next read from any client",
               "X1's `Duplicate` answer from a receipt, X5's read of the receipt after its request, X3's relay reading committed receipts"),
    "ISO-08": ("Positions are committed in the order they are taken, or the relay follows each stream: a relay that has published up to a position never finds a lower one committed later",
               "X2's watermark (`X2_Watermark*`, which assumes commits in position order), X3 (`X3_ByPosition*` shows the skip, `X3_PerStream*` the fix)"),
    "ISO-09": ("A fenced store refuses every write that commits after the fence, so a copy taken after the fence holds every acknowledged write",
               "X4's fenced cutover (`X4_Fenced`, `X4_FencedTimeouts` and their wide instances)"),
    "ISO-10": ("A refused guarded write can return the version it found, which differs from the one the writer expected",
               "X6 with the refusal returning the revision (`X6_Closed`, `X6_StartOpen*`), Protocol A's refusal (`PA_OnRead*`)"),
    "ISO-11": ("A check of another row and a write made on it are not interleaved with another writer's, so two writers cannot each take one of the last two rows",
               "Model A's `Atomic` against `SnapshotNoWWDetect`, the single-store transaction row of the catalogue, \"isolated to the store's level\""),
    "ISO-12": ("A unit of several operations in one request, its receipt written first under a guard over every row, applies whole or not at all",
               "X5's and X7's `WholeAnswer` and `FencedAnswer` guards, and the unit of ADR-A123's addendum of 2026-11-25 (TSD-80 in memory)"),
}

# What each store does, by probe, store, form and mode. A form expected `always` is a control unless the store's documentation
# says the anomaly is allowed at that level, which the README's table says for each.
EXPECTED: dict[tuple[str, str, str, str], str] = {}


def _expect(probe: str, store: str, form: str, modes: dict[str, str]) -> None:
    for mode, outcome in modes.items():
        EXPECTED[(probe, store, form, mode)] = outcome


_expect("ISO-01", PG, "guarded", {RC: NEVER, RR: NEVER, SER: NEVER})
_expect("ISO-01", PG, "unguarded", {RC: ALWAYS, RR: NEVER, SER: NEVER})
_expect("ISO-01", FUSEKI, "guarded", {"two clients": NEVER})
_expect("ISO-01", FUSEKI, "unguarded", {"two clients": ALWAYS})
_expect("ISO-02", PG, "guarded", {RC: NEVER, SER: NEVER})
_expect("ISO-02", FUSEKI, "guarded", {"four clients": NEVER})
_expect("ISO-03", PG, "receipt checked by an earlier read", {RC: ALWAYS, RR: ALWAYS, SER: NEVER})
_expect("ISO-03", PG, "receipt with a unique key", {RC: NEVER, RR: NEVER, SER: NEVER})
_expect("ISO-03", PG, "receipt inserted first, on conflict do nothing", {RC: NEVER, RR: NEVER, SER: NEVER})
_expect("ISO-03", FUSEKI, "receipt checked by an earlier read", {"two clients": ALWAYS})
_expect("ISO-03", FUSEKI, "receipt checked in the request", {"two clients": NEVER})
_expect("ISO-04", PG, "reader during the transaction, which then fails", {RU: NEVER, RC: NEVER})
_expect("ISO-04", FUSEKI, "reader polling while the request runs", {"two clients": NEVER})
_expect("ISO-04", TDB2, "reader transaction during the write transaction", {"in process": NEVER})
_expect("ISO-05", PG, "per-step guards", {RC: NEVER, RR: NEVER, SER: NEVER})
_expect("ISO-05", FUSEKI, "per-step guards", {"two clients": NEVER})
_expect("ISO-06", PG, "two reads in one transaction", {RC: ALWAYS, RR: NEVER, SER: NEVER})
_expect("ISO-06", PG, "two reads in two transactions", {RC: ALWAYS})
_expect("ISO-06", FUSEKI, "one query", {"two clients": NEVER})
_expect("ISO-06", FUSEKI, "two queries", {"two clients": ALWAYS})
_expect("ISO-06", TDB2, "one read transaction", {"in process": NEVER})
_expect("ISO-06", TDB2, "two read transactions", {"in process": ALWAYS})
_expect("ISO-07", PG, "a new transaction", {RC: NEVER})
_expect("ISO-07", PG, "a transaction begun before the commit", {RC: NEVER, RR: ALWAYS, SER: ALWAYS})
_expect("ISO-07", FUSEKI, "a new request from another client", {"two clients": NEVER})
_expect("ISO-08", PG, "position from a sequence", {RC: ALWAYS, SER: ALWAYS})
_expect("ISO-08", PG, "position from a counter row the transaction locks", {RC: NEVER})
_expect("ISO-08", FUSEKI, "position computed in the request", {"four clients": NEVER})
_expect("ISO-08", FUSEKI, "position taken by a request of its own", {"two clients": ALWAYS})
_expect("ISO-09", PG, "fence read in the write's transaction", {RC: ALWAYS, RR: ALWAYS, SER: NEVER})
_expect("ISO-09", PG, "fence row read FOR SHARE in the write's transaction", {RC: NEVER})
_expect("ISO-09", FUSEKI, "fence checked by an earlier read", {"three clients": ALWAYS})
_expect("ISO-09", FUSEKI, "fence checked in the write's request", {"three clients": NEVER})
_expect("ISO-10", PG, "one statement, version from its snapshot", {RC: ALWAYS, RR: NEVER, SER: NEVER})
_expect("ISO-10", PG, "locking read before the guard", {RC: NEVER})
_expect("ISO-10", PG, "version read by a later statement", {RC: NEVER})
_expect("ISO-10", FUSEKI, "version read after the refusal", {"two clients": NEVER})
_expect("ISO-11", PG, "check by an earlier read", {RC: ALWAYS, RR: ALWAYS, SER: NEVER})
_expect("ISO-11", PG, "check in the write's statement", {RC: ALWAYS, RR: ALWAYS, SER: NEVER})
_expect("ISO-11", FUSEKI, "check by an earlier read", {"two clients": ALWAYS})
_expect("ISO-11", FUSEKI, "check in the request", {"two clients": NEVER})
_expect("ISO-12", FUSEKI, "every row as planned", {"one client": NEVER})
_expect("ISO-12", FUSEKI, "one row moved", {"one client": NEVER})
_expect("ISO-12", FUSEKI, "one row moved, members without the receipt", {"one client": ALWAYS})


@dataclass
class Row:
    probe: str
    store: str
    version: str
    form: str
    mode: str
    reps: int = 0
    anomalies: int = 0
    outcomes: dict[str, int] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)

    def add(self, outcome: str, anomaly: bool) -> None:
        self.reps += 1
        self.anomalies += 1 if anomaly else 0
        self.outcomes[outcome] = self.outcomes.get(outcome, 0) + 1

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (self.probe, self.store, self.form, self.mode)


def verdict(row: Row) -> tuple[bool, str]:
    """Whether the row is what `EXPECTED` says of its store, and why not where it is not."""
    expected = EXPECTED.get(row.key)
    if expected is None:
        return False, "no expectation is recorded for this row"
    if row.reps == 0:
        return False, "no repetition ran"
    idle = [name for name, n in row.counts.items() if (name.startswith("reads while") or name == "races lost") and n == 0]
    if idle:
        return False, f"{idle[0]} is 0, so the probe never ran beside another client"
    if expected == NEVER and row.anomalies != 0:
        return False, f"expected never, the anomaly appeared in {row.anomalies} of {row.reps}"
    if expected == ALWAYS and row.anomalies != row.reps:
        return False, f"expected always, the anomaly appeared in {row.anomalies} of {row.reps}"
    return True, f"{row.anomalies} of {row.reps}, expected {expected}"


def missing(rows: list[Row], store: str, version: str) -> list[tuple[str, str, str, str]]:
    """The expected rows of one store that a run of one version did not produce."""
    produced = {r.key for r in rows if r.store == store and r.version == version}
    return sorted(k for k in EXPECTED if k[1] == store and k not in produced)


# ---- the PostgreSQL arm ---------------------------------------------------------------------------------------------------

class Refused(str):
    """A statement the server refused with one of the errors a probe expects, named by the error."""


def attempt(call, *args):
    """Run a call and return its result, or a `Refused` naming a serialization failure, a deadlock, a unique violation or a division by zero."""
    import psycopg.errors as e

    try:
        return call(*args)
    except e.SerializationFailure:
        return Refused("serialization failure")
    except e.DeadlockDetected:
        return Refused("deadlock detected")
    except e.UniqueViolation:
        return Refused("unique violation")
    except e.DivisionByZero:
        return Refused("division by zero")


class Session:
    """One connection in autocommit, so that a transaction begins and ends only where a probe says."""

    def __init__(self, conninfo: str) -> None:
        import psycopg

        self.conn = psycopg.connect(conninfo, autocommit=True)
        self.pid = self.conn.info.backend_pid

    def begin(self, level: str) -> None:
        from psycopg import sql

        self.conn.execute(sql.SQL("BEGIN ISOLATION LEVEL {}").format(sql.SQL(LEVEL_SQL[level])))

    def value(self, query: str, params: tuple = ()):
        row = self.conn.execute(query, params).fetchone()
        return None if row is None else row[0]

    def one(self, query: str, params: tuple = ()):
        return self.conn.execute(query, params).fetchone()

    def x(self, query: str, params: tuple = ()) -> int:
        return self.conn.execute(query, params).rowcount

    def commit(self) -> None:
        self.conn.execute("COMMIT")

    def rollback(self) -> None:
        self.conn.execute("ROLLBACK")

    def close(self) -> None:
        self.conn.close()


SCHEMA = (
    "CREATE TABLE ver (id int PRIMARY KEY, v int NOT NULL)",
    "CREATE TABLE marker (id int NOT NULL, v int NOT NULL, writer text NOT NULL)",
    "CREATE TABLE effect (cmd int NOT NULL, writer text NOT NULL)",
    "CREATE TABLE receipt_nokey (cmd int NOT NULL, writer text NOT NULL)",
    "CREATE TABLE receipt_key (cmd int PRIMARY KEY, writer text NOT NULL)",
    "CREATE TABLE row2 (id int, k text, rev int NOT NULL, by_w text, PRIMARY KEY (id, k))",
    "CREATE TABLE relay (id int, pos bigint, PRIMARY KEY (id, pos))",
    "CREATE SEQUENCE pos_seq",
    "CREATE TABLE counter (id int PRIMARY KEY, n bigint NOT NULL)",
    "CREATE TABLE authority (id int PRIMARY KEY, fenced boolean NOT NULL)",
    "CREATE TABLE writes (id int NOT NULL, w text NOT NULL)",
    "CREATE TABLE ledger (id int PRIMARY KEY, rev int NOT NULL)",
    "CREATE TABLE oncall (id int, k text, on_call boolean NOT NULL, PRIMARY KEY (id, k))",
)


class PgArm:
    """The probes on one database of the fixture's server. Each repetition uses ids of its own."""

    def __init__(self, server, dbname: str) -> None:
        self.conninfo = server.conninfo(dbname)
        self.version = server.server_version
        self.admin = Session(self.conninfo)
        for statement in SCHEMA:
            self.admin.x(statement)
        self.s = [Session(self.conninfo) for _ in range(3)]
        self.pool = ThreadPoolExecutor(max_workers=2)
        self._id = 0

    def close(self) -> None:
        self.pool.shutdown(wait=True)
        for session in [*self.s, self.admin]:
            session.close()

    def nid(self) -> int:
        self._id += 1
        return self._id

    def wait_waiting(self, session: Session) -> None:
        """Return once the server shows the session waiting on a lock, so the next step is taken while it waits."""
        deadline = time.monotonic() + WAIT_TIMEOUT
        while time.monotonic() < deadline:
            if self.admin.value("SELECT wait_event_type FROM pg_stat_activity WHERE pid = %s", (session.pid,)) == "Lock":
                return
            time.sleep(0.002)
        raise RuntimeError(f"the session {session.pid} did not wait on a lock within {WAIT_TIMEOUT} s")

    @staticmethod
    def finish(session: Session, result=None):
        """Roll back after a refused statement, and otherwise commit, returning a `Refused` where the commit is refused."""
        if isinstance(result, Refused):
            session.rollback()
            return result
        committed = attempt(session.commit)
        return committed if isinstance(committed, Refused) else result

    @staticmethod
    def or_rollback(session: Session, query: str, params: tuple):
        """Run a statement, and roll the transaction back at once where it is refused, so its locks go. For a statement run on a thread of its own."""
        result = attempt(session.x, query, params)
        if isinstance(result, Refused):
            session.rollback()
        return result

    # ISO-01
    def cas(self, form: str, level: str) -> tuple[str, bool]:
        a, b, _ = self.s
        i = self.nid()
        self.admin.x("INSERT INTO ver VALUES (%s, 0)", (i,))
        a.begin(level)
        b.begin(level)
        ra = a.value("SELECT v FROM ver WHERE id = %s", (i,))
        rb = b.value("SELECT v FROM ver WHERE id = %s", (i,))

        def update(session: Session, read: int):
            if form == "guarded":
                return session.x("UPDATE ver SET v = %s WHERE id = %s AND v = %s", (read + 1, i, read))
            return session.x("UPDATE ver SET v = %s WHERE id = %s", (read + 1, i))

        if update(a, ra) == 1:
            a.x("INSERT INTO marker VALUES (%s, %s, 'a')", (i, ra + 1))
        waiting = self.pool.submit(attempt, update, b, rb)
        self.wait_waiting(b)
        a.commit()
        nb = waiting.result()
        if nb == 1:
            b.x("INSERT INTO marker VALUES (%s, %s, 'b')", (i, rb + 1))
        nb = self.finish(b, nb)
        markers = self.admin.value("SELECT count(*) FROM marker WHERE id = %s AND v = 1", (i,))
        if markers == 2:
            return "both applied from the same version", True
        return ("the second refused by its guard" if nb == 0 else f"the second refused: {nb}"), markers != 1

    # ISO-02
    def stress(self, level: str) -> Row:
        row = Row("ISO-02", PG, self.version, "guarded", level)
        i = self.nid()
        self.admin.x("INSERT INTO ver VALUES (%s, 0)", (i,))
        lost = [0] * STRESS_THREADS
        start = threading.Barrier(STRESS_THREADS)

        def writer(t: int) -> None:
            s = Session(self.conninfo)
            try:
                start.wait(WAIT_TIMEOUT)
                while True:
                    n = s.value("SELECT v FROM ver WHERE id = %s", (i,))
                    if n >= PG_STRESS:
                        return
                    s.begin(level)
                    r = attempt(s.x, "UPDATE ver SET v = %s WHERE id = %s AND v = %s", (n + 1, i, n))
                    if r == 1:
                        s.x("INSERT INTO marker VALUES (%s, %s, %s)", (i, n + 1, f"w{t}"))
                    r = self.finish(s, r)
                    if r != 1:
                        lost[t] += 1
            finally:
                s.close()

        with ThreadPoolExecutor(max_workers=STRESS_THREADS) as pool:
            for future in [pool.submit(writer, t) for t in range(STRESS_THREADS)]:
                future.result()
        markers = self.admin.value("SELECT count(*) FROM marker WHERE id = %s", (i,))
        doubled = self.admin.value("SELECT count(*) FROM (SELECT v FROM marker WHERE id = %s GROUP BY v HAVING count(*) > 1) d", (i,))
        row.counts = {"target": PG_STRESS, "markers": markers, "versions with more than one marker": doubled, "races lost": sum(lost)}
        row.add("one marker at each version" if markers == PG_STRESS and doubled == 0 else f"markers {markers}, versions with more than one {doubled}",
                markers != PG_STRESS or doubled != 0)
        return row

    # ISO-03
    def duplicate(self, form: str, level: str) -> tuple[str, bool]:
        a, b, _ = self.s
        cmd = self.nid()
        a.begin(level)
        b.begin(level)
        if form == "receipt checked by an earlier read":
            seen = [s.value("SELECT count(*) FROM receipt_nokey WHERE cmd = %s", (cmd,)) for s in (a, b)]

            def deliver(session: Session, tag: str) -> int:
                session.x("INSERT INTO effect VALUES (%s, %s)", (cmd, tag))
                return session.x("INSERT INTO receipt_nokey VALUES (%s, %s)", (cmd, tag))

            ra = attempt(deliver, a, "a") if seen[0] == 0 else 0
            rb = attempt(deliver, b, "b") if seen[1] == 0 else 0
            ra, rb = self.finish(a, ra), self.finish(b, rb)
        elif form == "receipt with a unique key":
            for s in (a, b):
                s.value("SELECT count(*) FROM receipt_key WHERE cmd = %s", (cmd,))
            a.x("INSERT INTO effect VALUES (%s, 'a')", (cmd,))
            a.x("INSERT INTO receipt_key VALUES (%s, 'a')", (cmd,))
            b.x("INSERT INTO effect VALUES (%s, 'b')", (cmd,))
            waiting = self.pool.submit(attempt, b.x, "INSERT INTO receipt_key VALUES (%s, 'b')", (cmd,))
            self.wait_waiting(b)
            ra = self.finish(a, 1)
            rb = self.finish(b, waiting.result())
        else:
            if a.x("INSERT INTO receipt_key VALUES (%s, 'a') ON CONFLICT DO NOTHING", (cmd,)) == 1:
                a.x("INSERT INTO effect VALUES (%s, 'a')", (cmd,))
            waiting = self.pool.submit(attempt, b.x, "INSERT INTO receipt_key VALUES (%s, 'b') ON CONFLICT DO NOTHING", (cmd,))
            self.wait_waiting(b)
            ra = self.finish(a, 1)
            rb = waiting.result()
            if rb == 1:
                b.x("INSERT INTO effect VALUES (%s, 'b')", (cmd,))
            rb = self.finish(b, rb)
        effects = self.admin.value("SELECT count(*) FROM effect WHERE cmd = %s", (cmd,))
        if effects == 1:
            return ("the second wrote nothing" if rb in (0, None) else f"the second refused: {rb}"), False
        return f"applied {effects} times", True

    # ISO-04
    def failed_request(self, form: str, level: str) -> tuple[str, bool]:
        w, r, _ = self.s
        i = self.nid()
        self.admin.x("INSERT INTO ver VALUES (%s, 0)", (i,))
        w.begin(RC)
        w.x("UPDATE ver SET v = 1 WHERE id = %s", (i,))
        w.x("INSERT INTO marker VALUES (%s, 1, 'w')", (i,))
        r.begin(level)
        during = r.value("SELECT v FROM ver WHERE id = %s", (i,))
        r.commit()
        failed = attempt(w.value, "SELECT 1 / 0")
        w.rollback()
        after = self.admin.value("SELECT v FROM ver WHERE id = %s", (i,))
        markers = self.admin.value("SELECT count(*) FROM marker WHERE id = %s", (i,))
        anomaly = during != 0 or after != 0 or markers != 0 or not isinstance(failed, Refused)
        return ("the reader saw nothing, and nothing was left" if not anomaly else f"read {during} during, {after} after, {markers} markers left"), anomaly

    # ISO-05
    def two_rows(self, form: str, level: str) -> tuple[str, bool]:
        a, b, _ = self.s
        i = self.nid()
        self.admin.x("INSERT INTO row2 VALUES (%s, 'a', 0, NULL), (%s, 'b', 0, NULL)", (i, i))
        step = "UPDATE row2 SET rev = 1, by_w = %s WHERE id = %s AND k = %s AND rev = 0"
        a.begin(level)
        b.begin(level)
        a.x(step, ("a", i, "a"))
        b.x(step, ("b", i, "b"))
        second_a = self.pool.submit(self.or_rollback, a, step, ("a", i, "b"))
        self.wait_waiting(a)
        second_b = self.pool.submit(self.or_rollback, b, step, ("b", i, "a"))
        ra, rb = second_a.result(), second_b.result()
        ra = ra if isinstance(ra, Refused) else self.finish(a, ra)
        rb = rb if isinstance(rb, Refused) else self.finish(b, rb)
        by = dict(self.admin.conn.execute("SELECT k, by_w FROM row2 WHERE id = %s", (i,)).fetchall())
        whole = by.get("a") is not None and by.get("a") == by.get("b")
        refused = ra if isinstance(ra, Refused) else rb if isinstance(rb, Refused) else None
        return (f"one request applied both steps, the other {refused}" if whole and refused else "the rows were moved by different requests" if not whole else "both applied"), not whole

    # ISO-06
    def read_beside_commit(self, form: str, level: str) -> tuple[str, bool]:
        w, r, _ = self.s
        i = self.nid()
        self.admin.x("INSERT INTO ver VALUES (%s, 0)", (i,))
        w.begin(RC)
        w.x("UPDATE ver SET v = 1 WHERE id = %s", (i,))
        w.x("INSERT INTO marker VALUES (%s, 1, 'w')", (i,))
        if form == "two reads in one transaction":
            r.begin(level)
        v = r.value("SELECT v FROM ver WHERE id = %s", (i,))
        w.commit()
        m = r.value("SELECT count(*) FROM marker WHERE id = %s AND v = 1", (i,))
        if form == "two reads in one transaction":
            r.commit()
        torn = (v == 1) != (m == 1)
        return ("the version read first and the receipt read second differ" if torn else "the two reads agree"), torn

    # ISO-07
    def visible(self, form: str, level: str) -> tuple[str, bool]:
        w, r, _ = self.s
        i = self.nid()
        if form == "a transaction begun before the commit":
            r.begin(level)
            r.value("SELECT 1")
        w.x("INSERT INTO marker VALUES (%s, 1, 'w')", (i,))
        seen = r.value("SELECT count(*) FROM marker WHERE id = %s", (i,))
        if form == "a transaction begun before the commit":
            r.commit()
        return ("seen" if seen == 1 else "not seen"), seen != 1

    # ISO-08
    def positions(self, form: str, level: str) -> tuple[str, bool]:
        t1, t2, _ = self.s
        i = self.nid()
        if form == "position from a sequence":
            t1.begin(level)
            p1 = t1.value("SELECT nextval('pos_seq')")
            t2.begin(level)
            p2 = t2.value("SELECT nextval('pos_seq')")
            t2.x("INSERT INTO relay VALUES (%s, %s)", (i, p2))
            self.finish(t2)
            mark = self.admin.value("SELECT max(pos) FROM relay WHERE id = %s", (i,))
            t1.x("INSERT INTO relay VALUES (%s, %s)", (i, p1))
            self.finish(t1)
        else:
            self.admin.x("INSERT INTO counter VALUES (%s, 0)", (i,))
            take = "UPDATE counter SET n = n + 1 WHERE id = %s RETURNING n"
            t1.begin(level)
            p1 = t1.value(take, (i,))
            t2.begin(level)
            waiting = self.pool.submit(t2.value, take, (i,))
            self.wait_waiting(t2)
            t1.x("INSERT INTO relay VALUES (%s, %s)", (i, p1))
            self.finish(t1)
            mark = self.admin.value("SELECT max(pos) FROM relay WHERE id = %s", (i,))
            p2 = waiting.result()
            t2.x("INSERT INTO relay VALUES (%s, %s)", (i, p2))
            self.finish(t2)
        below = self.admin.value("SELECT count(*) FROM relay WHERE id = %s AND pos < %s", (i, mark))
        return ("a position below the relay's mark appeared after it" if below else "no position appeared below the mark"), below > 0

    # ISO-09
    def fence(self, form: str, level: str) -> tuple[str, bool]:
        w, f, c = self.s
        i = self.nid()
        self.admin.x("INSERT INTO authority VALUES (%s, false)", (i,))
        fence_sql = "UPDATE authority SET fenced = true WHERE id = %s"
        w.begin(level)
        if form == "fence read in the write's transaction":
            fenced = w.value("SELECT fenced FROM authority WHERE id = %s", (i,))
            f.begin(level)
            self.finish(f, attempt(f.x, fence_sql, (i,)))
            c.begin(level)
            c.value("SELECT fenced FROM authority WHERE id = %s", (i,))
            copied = c.value("SELECT count(*) FROM writes WHERE id = %s", (i,))
            self.finish(c)
            result = attempt(w.x, "INSERT INTO writes VALUES (%s, 'w')", (i,)) if not fenced else 0
            result = self.finish(w, result)
        else:
            fenced = w.value("SELECT fenced FROM authority WHERE id = %s FOR SHARE", (i,))
            f.begin(level)
            waiting = self.pool.submit(f.x, fence_sql, (i,))
            self.wait_waiting(f)
            result = self.finish(w, w.x("INSERT INTO writes VALUES (%s, 'w')", (i,)) if not fenced else 0)
            waiting.result()
            self.finish(f)
            c.begin(level)
            copied = c.value("SELECT count(*) FROM writes WHERE id = %s", (i,))
            self.finish(c)
        applied = self.admin.value("SELECT count(*) FROM writes WHERE id = %s", (i,))
        lost = applied == 1 and copied == 0
        if lost:
            return "acknowledged after the fence and missing from the copy", True
        return ("in the copy" if applied else f"refused: {result}" if isinstance(result, Refused) else "refused"), False

    # ISO-10
    def refusal(self, form: str, level: str) -> tuple[str, bool]:
        t1, t2, _ = self.s
        i = self.nid()
        self.admin.x("INSERT INTO ledger VALUES (%s, 0)", (i,))
        t1.begin(RC)
        t1.x("UPDATE ledger SET rev = 1 WHERE id = %s AND rev = 0", (i,))
        t2.begin(level)
        if form == "one statement, version from its snapshot":
            cte = ("WITH u AS (UPDATE ledger SET rev = rev + 1 WHERE id = %s AND rev = %s RETURNING rev) "
                   "SELECT (SELECT rev FROM u), (SELECT rev FROM ledger WHERE id = %s)")
            waiting = self.pool.submit(attempt, t2.one, cte, (i, 0, i))
            self.wait_waiting(t2)
            t1.commit()
            result = waiting.result()
            if isinstance(result, Refused):
                t2.rollback()
                return f"refused: {result}", False
            self.finish(t2)
            applied, found = result
        elif form == "locking read before the guard":
            waiting = self.pool.submit(t2.value, "SELECT rev FROM ledger WHERE id = %s FOR UPDATE", (i,))
            self.wait_waiting(t2)
            t1.commit()
            found = waiting.result()
            applied = t2.value("UPDATE ledger SET rev = rev + 1 WHERE id = %s AND rev = 0 RETURNING rev", (i,)) if found == 0 else None
            self.finish(t2)
        else:
            waiting = self.pool.submit(attempt, t2.value, "UPDATE ledger SET rev = rev + 1 WHERE id = %s AND rev = 0 RETURNING rev", (i,))
            self.wait_waiting(t2)
            t1.commit()
            applied = waiting.result()
            if isinstance(applied, Refused):
                t2.rollback()
                return f"refused: {applied}", False
            found = t2.value("SELECT rev FROM ledger WHERE id = %s", (i,))
            self.finish(t2)
        if applied is not None:
            return "applied over the other writer's move", True
        return (f"refused, and the version returned is {found}, the one expected" if found == 0 else f"refused, and the version returned is {found}"), found == 0

    # ISO-11
    def write_skew(self, form: str, level: str) -> tuple[str, bool]:
        t1, t2, _ = self.s
        i = self.nid()
        self.admin.x("INSERT INTO oncall VALUES (%s, 'a', true), (%s, 'b', true)", (i, i))
        t1.begin(level)
        t2.begin(level)
        if form == "check by an earlier read":
            counts = [t.value("SELECT count(*) FROM oncall WHERE id = %s AND on_call", (i,)) for t in (t1, t2)]
            r1 = attempt(t1.x, "UPDATE oncall SET on_call = false WHERE id = %s AND k = 'a'", (i,)) if counts[0] >= 2 else 0
            r2 = attempt(t2.x, "UPDATE oncall SET on_call = false WHERE id = %s AND k = 'b'", (i,)) if counts[1] >= 2 else 0
        else:
            guarded = "UPDATE oncall SET on_call = false WHERE id = %s AND k = %s AND (SELECT count(*) FROM oncall WHERE id = %s AND on_call) >= 2"
            r1 = attempt(t1.x, guarded, (i, "a", i))
            r2 = attempt(t2.x, guarded, (i, "b", i))
        r1, r2 = self.finish(t1, r1), self.finish(t2, r2)
        left = self.admin.value("SELECT count(*) FROM oncall WHERE id = %s AND on_call", (i,))
        if left == 0:
            return "both taken off", True
        refused = r2 if isinstance(r2, Refused) else r1 if isinstance(r1, Refused) else None
        return (f"one taken off, the other {refused}" if refused else f"{left} left on"), False


# The method of `PgArm` that runs one repetition of each probe. ISO-02 runs once, as `PgArm.stress`.
PG_RUNNERS = {"ISO-01": "cas", "ISO-03": "duplicate", "ISO-04": "failed_request", "ISO-05": "two_rows", "ISO-06": "read_beside_commit",
              "ISO-07": "visible", "ISO-08": "positions", "ISO-09": "fence", "ISO-10": "refusal", "ISO-11": "write_skew"}


def pg_probes(arm: PgArm, reps: int = PG_REPS) -> list[Row]:
    """Every PostgreSQL probe in every form and mode `EXPECTED` names, each repeated `reps` times."""
    rows = []
    for probe, store, form, mode in sorted(k for k in EXPECTED if k[1] == PG):
        if probe == "ISO-02":
            rows.append(arm.stress(mode))
            continue
        row = Row(probe, PG, arm.version, form, mode)
        for _ in range(reps):
            row.add(*getattr(arm, PG_RUNNERS[probe])(form, mode))
        rows.append(row)
        print(f"  {probe} {form}, {mode}: {row.anomalies} of {row.reps}", flush=True)
    return rows


def postgres_absent() -> str | None:
    """Why the PostgreSQL arm cannot run here, or None where it can."""
    for name in ("psycopg", "lattice_testing_postgres", "postgresql_binaries"):
        try:
            module = importlib.import_module(name)
        except ImportError:
            return f"needs {name}, which cannot be imported here (mise run bootstrap:testing-postgres)"
    if not hasattr(module, "bin"):
        return "needs postgresql_binaries, of which only an unpacked directory is left here (mise run bootstrap:testing-postgres)"
    return None


def run_postgres() -> tuple[list[Row], dict]:
    from lattice_testing_postgres import PostgresServer

    import psycopg

    # A deadlock is found after deadlock_timeout, which is 1 s by default. ISO-05 meets one in every repetition.
    with PostgresServer(settings={"deadlock_timeout": "50ms"}) as server:
        arm = PgArm(server, server.create_database())
        try:
            rows = pg_probes(arm)
        finally:
            arm.close()
        return rows, {"postgresql": server.server_version, "psycopg": psycopg.__version__}


# ---- the Jena arm ---------------------------------------------------------------------------------------------------------

def jena_absent() -> str | None:
    for tool in ("mvn", "java"):
        if shutil.which(tool) is None:
            return f"needs {tool} on the path, which mise gives a task"
    return None


def read_jena(path: Path, version: str) -> tuple[list[Row], dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = [Row(r["probe"], r["store"], version, r["form"], r["mode"], r["reps"], r["anomalies"], dict(r["outcomes"]), dict(r["counts"])) for r in data["rows"]]
    return rows, data["environment"]


def run_jena(version: str) -> tuple[list[Row], dict]:
    out = HERE / "target" / f"jena-{version}" / "results.json"
    if out.exists():
        out.unlink()
    command = [shutil.which("mvn"), "-q", "-f", str(HERE / "pom.xml"), "compile", "exec:exec", f"-Djena.version={version}", f"-Disolation.out={out}",
               f"-Disolation.reps={JENA_REPS}", f"-Disolation.stress={JENA_STRESS}"]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0 or not out.exists():
        raise RuntimeError(f"the Jena arm at {version} exited with {result.returncode}:\n{(result.stdout + result.stderr)[-3000:]}")
    return read_jena(out, version)


# ---- the run --------------------------------------------------------------------------------------------------------------

def report(rows: list[Row], env: dict, skipped: list[str], failures: list[str]) -> None:
    lines = [
        "# Store isolation probes",
        "",
        f"Run {env['date']}: Python {env['python']} on {env['machine']}. " + ", ".join(f"{k} {v}" for k, v in env.items() if k not in ("date", "python", "machine")) + ".",
        "",
        "| Probe | Store | Version | Form | Mode | Anomalies | Expected | Verdict | Outcomes | Counts |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        ok, why = verdict(r)
        outcomes = "; ".join(f"{k} ({n})" for k, n in r.outcomes.items())
        counts = "; ".join(f"{k} {n}" for k, n in r.counts.items())
        lines.append(f"| {r.probe} | {r.store} | {r.version} | {r.form} | {r.mode} | {r.anomalies} of {r.reps} | {EXPECTED.get(r.key, 'none')} | "
                     f"{'pass' if ok else 'FAIL: ' + why} | {outcomes} | {counts} |")
    lines += ["", *[f"Skipped: {s}" for s in skipped], *[f"Failed: {f}" for f in failures]]
    (HERE / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (HERE / "report.json").write_text(json.dumps({"environment": env, "skipped": skipped, "failures": failures,
                                                  "rows": [r.__dict__ | {"expected": EXPECTED.get(r.key), "pass": verdict(r)[0]} for r in rows]}, indent=2) + "\n",
                                      encoding="utf-8")


def main() -> int:
    env = {"date": time.strftime("%Y-%m-%d"), "python": platform.python_version(), "machine": f"{platform.system()} {platform.machine()}"}
    rows: list[Row] = []
    skipped: list[str] = []
    failures: list[str] = []
    started = time.monotonic()
    if PG in ARMS:
        reason = postgres_absent()
        if reason:
            skipped.append(f"postgresql: {reason}")
        else:
            print(f"postgresql arm, {PG_REPS} repetitions a row", flush=True)
            pg_rows, pg_env = run_postgres()
            rows += pg_rows
            env |= pg_env
            failures += [f"postgresql {k[0]} {k[2]}, {k[3]}: expected and not produced" for k in missing(rows, PG, pg_env["postgresql"])]
    if "jena" in ARMS:
        reason = jena_absent()
        if reason:
            skipped.append(f"fuseki and tdb2: {reason}")
        else:
            for version in JENA_VERSIONS:
                print(f"jena arm at {version}, {JENA_REPS} repetitions a row", flush=True)
                jena_rows, jena_env = run_jena(version)
                rows += jena_rows
                env[f"jena {version}"] = f"{jena_env['tdb2']}, {jena_env['fuseki']}, java {jena_env['java']}, {jena_env['seconds']} s"
                for store in (FUSEKI, TDB2):
                    failures += [f"{store} {version} {k[0]} {k[2]}, {k[3]}: expected and not produced" for k in missing(rows, store, version)]
    for r in rows:
        ok, why = verdict(r)
        print(f"{'PASS' if ok else 'FAIL'} {r.probe} {r.store} {r.version} | {r.form} | {r.mode}: {why}")
        if not ok:
            failures.append(f"{r.probe} {r.store} {r.version} {r.form}, {r.mode}: {why}")
    for s in skipped:
        print(f"SKIP {s}")
    for f in failures:
        if not f.startswith("ISO"):
            print(f"FAIL {f}")
    report(rows, env, skipped, failures)
    passed = sum(1 for r in rows if verdict(r)[0])
    print(f"isolation probes: {passed} as expected, {len(failures)} failed, {len(skipped)} skipped, {time.monotonic() - started:.1f} s")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
